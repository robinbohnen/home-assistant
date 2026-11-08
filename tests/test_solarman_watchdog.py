"""Offline test van de Solarman-waakhond.

Draaien:  python3 tests/test_solarman_watchdog.py      (nodig: jinja2, pyyaml)
          of: python3 -m pytest tests/test_solarman_watchdog.py

Leest de macro uit custom_templates/solarman.jinja en de sensor en automatisering
uit packages/9 - Other/Solarman.yaml letterlijk in, dus geen kopie die kan
afwijken. Bewaakt wordt:
1. de macro meldt een storing als de verbinding niet `on` is (uit,
   unavailable, of de entiteit bestaat niet);
2. hij meldt een storing als er vijf minuten geen nieuwe meting is, ook al
   staat de verbinding op `on` (bevroren integratie);
3. één verse bron is genoeg: 's nachts kan het accuvermogen lang gelijk staan;
4. de binary_sensor rendert `True`/`False` en de reden uit dezelfde macro, en
   is tijdgestuurd (een gewone template bevriest bij het herladen);
5. de automatisering wacht tien minuten (korte hikjes van 4-11 tot ~9 min),
   herlaadt via de entiteit, heeft een uurrem en een grens van zes uur, en
   meldt alleen bij mislukken of bij later herstel;
6. dit pakket schrijft nooit naar de registers van de omvormer
   (`number.`/`select.`/`switch.`/`time.inverter_*`): die zijn van MarkeDroid.
"""
import os
import re
from datetime import datetime, timedelta, timezone

import yaml
from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAKKET = f"{CONFIG}/packages/9 - Other/Solarman.yaml"

NU = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
STATES = {}
BRONNEN = [
    "sensor.inverter_grid_l1_voltage",
    "sensor.inverter_grid_frequency",
    "sensor.inverter_battery_voltage",
    "sensor.inverter_battery_power",
]


class Obj(dict):
    __getattr__ = dict.get


class StatesObj:
    """`states(e)` en `states[e]` zoals in HA; STATES[e] = (state, last_reported)."""

    def __getitem__(self, eid):
        if eid not in STATES:
            return None
        state, gemeld = STATES[eid]
        return Obj(state=state, last_reported=gemeld, last_updated=gemeld)

    def __call__(self, eid):
        return STATES[eid][0] if eid in STATES else "unknown"


env = Environment(loader=FileSystemLoader(f"{CONFIG}/custom_templates"))
env.globals.update(states=StatesObj(), now=lambda: NU)
MACRO = env.get_template("solarman.jinja").module.solarman_storing


def laad():
    with open(PAKKET, encoding="utf-8") as f:
        return yaml.safe_load(f)["solarman_package"]


def sensor():
    return laad()["template"][0]["binary_sensor"][0]


def automatisering():
    return laad()["automation"][0]


def wereld(verbinding="on", stil=5, alleen=None):
    """Alle bronnen `stil` seconden geleden gemeld, of alleen de bron `alleen`."""
    STATES.clear()
    if verbinding is not None:
        STATES["binary_sensor.inverter_connection"] = (verbinding, NU)
    for e in BRONNEN:
        if alleen is None or e == alleen:
            STATES[e] = ("230.1", NU - timedelta(seconds=stil))
        else:
            STATES[e] = ("0", NU - timedelta(hours=3))


def reden():
    return str(MACRO()).strip()


# --- de macro -----------------------------------------------------------------

def test_gezond_geeft_lege_reden():
    wereld()
    assert reden() == ""


def test_verbinding_uit_is_storing():
    wereld(verbinding="off")
    assert reden() == "verbinding off"


def test_verbinding_unavailable_is_storing():
    wereld(verbinding="unavailable")
    assert reden() == "verbinding unavailable"


def test_verbinding_bestaat_niet_is_storing():
    wereld(verbinding=None)
    assert reden() == "verbinding unknown"


def test_bevroren_metingen_zijn_storing():
    wereld(stil=12 * 60)
    assert reden() == "12 minuten geen nieuwe metingen"


def test_vier_minuten_stil_is_nog_geen_storing():
    wereld(stil=4 * 60)
    assert reden() == ""


def test_een_verse_bron_is_genoeg():
    # 's Nachts staat het accuvermogen lang op exact 0; de netspanning beweegt wel.
    wereld(alleen="sensor.inverter_grid_l1_voltage")
    assert reden() == ""


def test_alle_bronnen_unavailable_is_storing():
    wereld()
    for e in BRONNEN:
        STATES[e] = ("unavailable", NU)
    assert reden() == "geen metingen"


# --- de sensor ----------------------------------------------------------------

def _render(sjabloon):
    return env.from_string(sjabloon).render().strip()


def test_sensor_state_en_reden_uit_dezelfde_macro():
    s = sensor()
    wereld()
    assert _render(s["state"]) == "False"
    assert _render(s["attributes"]["reden"]) == ""
    wereld(verbinding="off")
    assert _render(s["state"]) == "True"
    assert _render(s["attributes"]["reden"]) == "verbinding off"


def test_sensor_is_tijdgestuurd():
    triggers = laad()["template"][0]["triggers"]
    assert {"trigger": "time_pattern", "minutes": "/1"} in triggers
    assert {"trigger": "homeassistant", "event": "start"} in triggers
    assert sensor()["device_class"] == "problem"


# --- de automatisering --------------------------------------------------------

def _alle_acties(knoop):
    """Elke dict met een `action`-sleutel, hoe diep ook genest."""
    if isinstance(knoop, dict):
        if "action" in knoop:
            yield knoop
        for v in knoop.values():
            yield from _alle_acties(v)
    elif isinstance(knoop, list):
        for v in knoop:
            yield from _alle_acties(v)


def test_wacht_tien_minuten_voor_herladen():
    a = automatisering()
    storing = next(t for t in a["triggers"] if t.get("id") == "storing")
    assert storing["entity_id"] == "binary_sensor.solarman_storing_ruw"
    assert storing["to"] == "on"
    assert storing["for"] == "00:10:00"
    assert a["mode"] == "single"


def test_herlaadt_via_de_entiteit():
    herladen = [x for x in _alle_acties(automatisering()["actions"])
                if x["action"] == "homeassistant.reload_config_entry"]
    assert len(herladen) == 1
    assert herladen[0]["target"] == {"entity_id": "binary_sensor.inverter_connection"}
    # Een mislukte herlaadbeurt mag de ronde (en de melding) niet afbreken.
    assert herladen[0]["continue_on_error"] is True


def test_hooguit_twee_pogingen_per_ronde():
    repeat = next(x["repeat"] for x in automatisering()["actions"] if "repeat" in x)
    assert repeat["count"] == 2


def test_rem_per_uur_en_grens_van_zes_uur():
    tekst = yaml.safe_dump(automatisering()["conditions"])
    assert "timedelta(minutes=55)" in tekst
    assert "timedelta(hours=6)" in tekst
    assert "home_assistant_gestart" in tekst


def test_meldt_alleen_bij_mislukken_of_later_herstel():
    meldingen = [x for x in _alle_acties(automatisering()["actions"])
                 if x["action"].startswith("notify.")]
    titels = sorted(m["data"]["title"] for m in meldingen)
    assert titels == ["Solarman blijft stil", "Solarman werkt weer"]


def test_schrijft_nooit_naar_omvormerregisters():
    with open(PAKKET, encoding="utf-8") as f:
        yaml_zonder_commentaar = "\n".join(
            regel.split("#", 1)[0] for regel in f.read().splitlines())
    verboden = re.findall(r"\b(?:number|select|switch|time)\.inverter_\w+", yaml_zonder_commentaar)
    assert not verboden, f"schrijft naar MarkeDroid-registers: {verboden}"
    for x in _alle_acties(automatisering()["actions"]):
        assert x["action"].split(".")[0] not in ("number", "select", "switch", "time")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
