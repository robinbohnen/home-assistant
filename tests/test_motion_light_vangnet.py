"""Offline test van het vangnet in de bewegingslicht-blueprint.

Draaien:  python3 tests/test_motion_light_vangnet.py      (nodig: jinja2, pyyaml)
          of: python3 -m pytest tests/test_motion_light_vangnet.py

Aanleiding (13 november 2026): de lamp op de overloop zolder ging vaak niet
meer vanzelf uit. De blueprint zette een lamp alleen uit na een nette
`on` -> `off` van de bewegingsmelder; ging de lamp anders aan (Mini's deur,
dashboard, stem) of viel de melder tussendoor weg, dan kwam die nooit.

Bewaakt wordt, met de trigger-template letterlijk uit
`blueprints/automation/robin/motion_light.yaml`:
1. de trigger `vangnet` bestaat, is een template-trigger, en zijn variabelen
   staan in `trigger_variables` (een template-trigger ziet `variables` niet);
2. de uit-tak reageert op `vangnet`, en geen andere tak doet dat;
3. de template gaat pas af als de lamp én de melder allebei `vangnet_na` lang
   rustig zijn, telt een weggevallen of verdwenen melder als stil, en zwijgt
   bij `vangnet_na` = 0 (de standaard, zodat andere kamers niets merken);
4. de overloop zolder zet het vangnet aan, ruim na de vijf minuten van Mini's
   deur-automatisering en ruim na `uit_na`.
"""
import os
from datetime import datetime, timedelta, timezone

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUEPRINT = f"{CONFIG}/blueprints/automation/robin/motion_light.yaml"
ZOLDER = f"{CONFIG}/packages/2 - Second Floor/Attic Corridor/Lights.yaml"

FOUTEN = []


class Input(str):
    """`!input naam` blijft herkenbaar als verwijzing naar een blueprint-input."""


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!input", lambda l, n: Input(l.construct_scalar(n)))


def laad(pad):
    with open(pad, encoding="utf-8") as f:
        return yaml.load(f, Loader=Loader)


def check(naam, ok):
    print(("OK   " if ok else "FOUT ") + naam)
    if not ok:
        FOUTEN.append(naam)


BP = laad(BLUEPRINT)
NU = datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc)
PIR = "binary_sensor.melder"
LAMP = "light.lamp"
LAMP2 = "light.lamp2"


class S:
    def __init__(self, state, minuten_geleden):
        self.state = state
        self.last_changed = NU - timedelta(minutes=minuten_geleden)


class StatesObj:
    def __init__(self, toestand):
        self.t = toestand

    def __getitem__(self, e):
        # Zoals HA: een onbekende entiteit levert None op, geen fout.
        return self.t.get(e)


# --- 1. Trigger en trigger_variables ----------------------------------------
vangnet = [t for t in BP["triggers"] if t.get("id") == "vangnet"]
check("trigger vangnet bestaat precies één keer", len(vangnet) == 1)
TRIG = vangnet[0]
check("vangnet is een template-trigger", TRIG.get("trigger") == "template")

tv = BP.get("trigger_variables", {})
check("trigger_variables wijzen naar de juiste inputs",
      tv.get("vangnet_pir") == "bewegingssensor"
      and tv.get("vangnet_lampen") == "lamp"
      and tv.get("vangnet_na") == "vangnet_na"
      and all(isinstance(v, Input) for v in tv.values()))

inp = BP["blueprint"]["input"].get("vangnet_na", {})
standaard = inp.get("default", {})
check("vangnet_na staat standaard uit (0)",
      isinstance(standaard, dict)
      and sum(int(v) for v in standaard.values()) == 0)

# --- 2. Takken --------------------------------------------------------------
TAKKEN = BP["actions"][0]["choose"]


def trigger_ids(tak):
    ids = []
    for c in tak["conditions"]:
        if c.get("condition") == "trigger":
            ids += c["id"] if isinstance(c["id"], list) else [c["id"]]
    return ids


met_vangnet = [i for i, t in enumerate(TAKKEN) if "vangnet" in trigger_ids(t)]
uit_tak = [i for i, t in enumerate(TAKKEN) if "geen_beweging" in trigger_ids(t)]
check("alleen de uit-tak reageert op vangnet",
      met_vangnet == uit_tak and len(uit_tak) == 1)

# --- 3. De template zelf ----------------------------------------------------
env = Environment()
TEMPLATE = env.from_string(TRIG["value_template"])


def vuurt(toestand, na, lampen=(LAMP,)):
    uit = TEMPLATE.render(
        states=StatesObj(toestand), now=lambda: NU,
        vangnet_pir=PIR, vangnet_lampen=list(lampen), vangnet_na=na,
    ).strip()
    assert uit in ("True", "False"), f"template leverde {uit!r}"
    return uit == "True"


TIEN = {"hours": 0, "minutes": 10, "seconds": 0}
NUL = {"hours": 0, "minutes": 0, "seconds": 0}

check("lamp 12 min aan, melder 12 min stil -> uit",
      vuurt({LAMP: S("on", 12), PIR: S("off", 12)}, TIEN))
check("Mini's deur: lamp 10 min aan, melder al uren stil -> uit",
      vuurt({LAMP: S("on", 10), PIR: S("off", 300)}, TIEN))
check("lamp pas 5 min aan -> nog niet",
      not vuurt({LAMP: S("on", 5), PIR: S("off", 300)}, TIEN))
check("melder pas 3 min stil -> nog niet",
      not vuurt({LAMP: S("on", 60), PIR: S("off", 3)}, TIEN))
check("melder ziet iemand -> niet",
      not vuurt({LAMP: S("on", 60), PIR: S("on", 60)}, TIEN))
check("lamp uit -> niet",
      not vuurt({LAMP: S("off", 60), PIR: S("off", 60)}, TIEN))
check("lamp unavailable -> niet",
      not vuurt({LAMP: S("unavailable", 60), PIR: S("off", 60)}, TIEN))
check("melder 30 min unavailable -> telt als stil, uit",
      vuurt({LAMP: S("on", 60), PIR: S("unavailable", 30)}, TIEN))
check("melder net weggevallen -> nog niet",
      not vuurt({LAMP: S("on", 60), PIR: S("unavailable", 2)}, TIEN))
check("melder bestaat niet (hernoemd) -> telt als stil, uit",
      vuurt({LAMP: S("on", 60)}, TIEN))
check("lamp bestaat niet -> niet",
      not vuurt({PIR: S("off", 60)}, TIEN))
check("vangnet_na = 0 -> nooit, ook niet na uren",
      not vuurt({LAMP: S("on", 600), PIR: S("off", 600)}, NUL))
check("vangnet_na als tekst '00:10:00' werkt ook",
      vuurt({LAMP: S("on", 12), PIR: S("off", 12)}, "00:10:00"))
check("tekst '00:00:00' -> nooit",
      not vuurt({LAMP: S("on", 600), PIR: S("off", 600)}, "00:00:00"))
check("twee lampen: één net aan -> nog niet",
      not vuurt({LAMP: S("on", 60), LAMP2: S("on", 2), PIR: S("off", 60)},
                TIEN, lampen=(LAMP, LAMP2)))
check("twee lampen: één lang aan, ander uit -> uit",
      vuurt({LAMP: S("on", 60), LAMP2: S("off", 2), PIR: S("off", 60)},
            TIEN, lampen=(LAMP, LAMP2)))

# --- 4. De overloop zolder --------------------------------------------------
pakket = laad(ZOLDER)
auto = next(a for a in pakket["attic_corridor_lights_package"]["automation"]
            if a["id"] == "lights_movement_attic_corridor")
invoer = auto["use_blueprint"]["input"]
na = invoer.get("vangnet_na") or {}
sec = (int(na.get("hours", 0)) * 3600 + int(na.get("minutes", 0)) * 60
       + int(na.get("seconds", 0)))
uit_na = BP["blueprint"]["input"]["uit_na"]["default"]
uit_na_sec = (int(uit_na["hours"]) * 3600 + int(uit_na["minutes"]) * 60
              + int(uit_na["seconds"]))
check("overloop zolder zet het vangnet aan", sec > 0)
check("vangnet zolder ruim na Mini's vijf minuten", sec > 5 * 60)
check("vangnet zolder ruim na uit_na", sec >= 3 * uit_na_sec)
check("onbekende inputs komen niet voor in de zolder-automatisering",
      set(invoer) <= set(BP["blueprint"]["input"]))


def test_motion_light_vangnet():
    assert not FOUTEN, FOUTEN


if __name__ == "__main__":
    print()
    print(f"{len(FOUTEN)} fout(en)" if FOUTEN else "Alles groen.")
    raise SystemExit(1 if FOUTEN else 0)
