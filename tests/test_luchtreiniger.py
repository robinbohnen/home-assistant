"""Offline test van de nachtregel in de luchtreiniger-blueprint.

Draaien:  python3 -m venv .venv && .venv/bin/pip install pyyaml
          .venv/bin/python tests/test_luchtreiniger.py

Bewaakt punt 6 uit `blueprints/automation/robin/luchtreiniger_kamer.yaml`
(27 oktober 2026): wordt de reiniger bij Logan of Emma aangezet tijdens de
avondrust of de slaaptijd, dan gaat hij meteen weer uit en volgt een melding.

Drie dingen worden hier bewaakt.

1. De trigger op de stekker zelf bestaat, en alleen vanaf 'off' - een stekker
   die na een stroomonderbreking terugkomt hoort geen "aangezet"-melding te
   geven.
2. Welke tak er wint bij het aanzetten. De twee nieuwe takken staan vóór de
   bestaande regel en worden hier echt doorgerekend met een kleine
   conditie-evaluator: 's nachts met iemand thuis uit + melding, met een leeg
   huis niets (dat aan-commando kwam van de blueprint zelf), overdag niets.
   Andere triggers mogen in geen van beide takken vallen.
3. Beide kamers geven een melding mee. Zonder `melding` werkt het uitzetten
   wel, maar hoort niemand ervan.
"""
import datetime as dt
import os

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUEPRINT = f"{CONFIG}/blueprints/automation/robin/luchtreiniger_kamer.yaml"
PAKKETTEN = {
    "maxi": f"{CONFIG}/packages/1 - First Floor/Bedroom Maxi/Aircleaner.yaml",
    "mini": f"{CONFIG}/packages/2 - Second Floor/Bedroom Mini/Aircleaner.yaml",
}

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


# --- Kleine evaluator voor de conditietypes in de nachttakken ---------------

INPUTS = {
    "reiniger": "switch.reiniger",
    "avondrust": "input_datetime.avondrust",
    "slaaptijd": "binary_sensor.slaaptijd",
}


def waarde(x):
    return INPUTS[x] if isinstance(x, Input) else x


def evalueer(cond, st):
    t = cond["condition"]
    if t == "trigger":
        return st["trigger"] == cond["id"]
    if t == "numeric_state":
        v = float(st["states"][cond["entity_id"]])
        if "above" in cond and not v > cond["above"]:
            return False
        if "below" in cond and not v < cond["below"]:
            return False
        return True
    if t == "state":
        return st["states"][waarde(cond["entity_id"])] == cond["state"]
    if t == "time":
        nu = st["nu"]
        if "after" in cond:
            grens = st["states"][waarde(cond["after"])]
            if not nu >= dt.time.fromisoformat(grens):
                return False
        if "before" in cond:
            grens = st["states"][waarde(cond["before"])]
            if not nu < dt.time.fromisoformat(grens):
                return False
        return True
    if t == "or":
        return any(evalueer(c, st) for c in cond["conditions"])
    if t == "and":
        return all(evalueer(c, st) for c in cond["conditions"])
    raise ValueError(f"conditie {t} niet nagebootst")


BP = laad(BLUEPRINT)
TAKKEN = BP["actions"][0]["choose"]
NACHT, OVERDAG = TAKKEN[0], TAKKEN[1]


def tak(trigger, nu, thuis, slaaptijd):
    """Geeft 'nacht', 'overdag' of 'regel' (= de bestaande takken eronder)."""
    st = {
        "trigger": trigger,
        "nu": dt.time.fromisoformat(nu),
        "states": {
            "zone.home": str(thuis),
            INPUTS["avondrust"]: "20:30:00",
            INPUTS["slaaptijd"]: slaaptijd,
        },
    }
    for naam, t in (("nacht", NACHT), ("overdag", OVERDAG)):
        if all(evalueer(c, st) for c in t["conditions"]):
            return naam
    return "regel"


# 1. De trigger
trig = [t for t in BP["triggers"] if t.get("id") == "reiniger_aan"]
check("trigger reiniger_aan bestaat precies één keer", len(trig) == 1)
if trig:
    t = trig[0]
    check("trigger kijkt naar de reiniger zelf",
          t["entity_id"] == "reiniger" and isinstance(t["entity_id"], Input))
    check("trigger alleen van off naar on",
          t.get("from") == "off" and t.get("to") == "on")

# 2. De takken
check("nachttak zet de reiniger uit vóór de melding",
      NACHT["sequence"][0]["action"] == "switch.turn_off"
      and NACHT["sequence"][0]["target"]["entity_id"] == "reiniger"
      and NACHT["sequence"][1]["sequence"] == "melding")
check("overdag-tak doet niets met de stekker",
      all("action" not in s for s in OVERDAG["sequence"]))

SCENARIO = [
    # trigger, tijd, personen thuis, slaaptijd, verwacht
    ("reiniger_aan", "22:15:00", 4, "on", "nacht", "na bedtijd, iedereen thuis"),
    ("reiniger_aan", "03:00:00", 4, "on", "nacht", "midden in de nacht"),
    ("reiniger_aan", "20:45:00", 4, "off", "nacht", "in de avondrust, voor bedtijd"),
    ("reiniger_aan", "06:30:00", 1, "on", "nacht", "ochtend, slaaptijd loopt nog"),
    ("reiniger_aan", "22:15:00", 0, "on", "overdag",
     "leeg huis: eigen aan-commando, geen melding"),
    ("reiniger_aan", "14:00:00", 4, "off", "overdag", "overdag aangezet"),
    ("reiniger_aan", "20:29:00", 4, "off", "overdag", "minuut voor de avondrust"),
    ("vangnet", "22:30:00", 4, "on", "regel", "halfuurronde 's nachts"),
    ("licht_aan", "22:30:00", 4, "on", "regel", "licht aan 's nachts"),
    ("avondrust", "20:30:00", 4, "off", "regel", "begin avondrust"),
]
for trigger, nu, thuis, slaap, verwacht, uitleg in SCENARIO:
    uit = tak(trigger, nu, thuis, slaap)
    check(f"{uitleg}: {verwacht} (kreeg {uit})", uit == verwacht)

# 3. De kamers
for kamer, pad in PAKKETTEN.items():
    pakket = next(iter(laad(pad).values()))
    inp = pakket["automation"][0]["use_blueprint"]["input"]
    melding = inp.get("melding") or []
    check(f"{kamer}: melding is een notify-actie",
          len(melding) > 0 and melding[0]["action"].startswith("notify."))
    check(f"{kamer}: melding heeft een eigen tag",
          bool(melding) and f"_{kamer}_" in melding[0]["data"]["data"]["tag"])

print()
if FOUTEN:
    print(f"{len(FOUTEN)} fout(en)")
    raise SystemExit(1)
print("Alles goed")
