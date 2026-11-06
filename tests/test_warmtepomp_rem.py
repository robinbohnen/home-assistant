"""Offline test van de warmtepomp-rem (29 oktober 2026).

Draaien:  .venv/bin/python tests/test_warmtepomp_rem.py      (nodig: jinja2, pyyaml)

Haalt de template van `binary_sensor.warmtepomp_rem_gewenst` en de
automatisering `warmtepomp_rem_bij_vasthouden` letterlijk uit
packages/9 - Other/Warmtepomp.yaml, dus geen kopie die kan afwijken.
Bewaakt wordt:
1. aan alleen bij `vasthouden` én een duur tarief (high, very_high, peak);
2. uit bij elke andere bekende regie of een tarief dat niet duur is;
3. `unavailable` (en dus: limiet blijft staan) als de beslissing niet te
   nemen is - stille MarkeDroid, `niet_geleverd`, geen tarief;
4. de automatisering: eerst 250 W, dan de schakelaar; niets sturen als hij
   er al op staat; uitzetten alleen op de overgang naar `off`.
"""
import os

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAKKET = f"{CONFIG}/packages/9 - Other/Warmtepomp.yaml"

STATES = {}


def ha_states(eid):
    return str(STATES.get(eid, "unknown"))


def ha_is_state(eid, state):
    return ha_states(eid) == state


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


env = Environment()
env.filters["float"] = f_float
env.globals.update(states=ha_states, is_state=ha_is_state)


def _zoek(pad, sleutel, waarde):
    with open(pad, encoding="utf-8") as f:
        knopen = [yaml.safe_load(f)]
    while knopen:
        k = knopen.pop()
        if isinstance(k, dict):
            if k.get(sleutel) == waarde:
                return k
            knopen.extend(k.values())
        elif isinstance(k, list):
            knopen.extend(k)
    raise AssertionError(f"{sleutel}={waarde} niet gevonden in {pad}")


SENSOR = _zoek(PAKKET, "unique_id", "warmtepomp_rem_gewenst")
AUTO = _zoek(PAKKET, "id", "warmtepomp_rem_bij_vasthouden")
SENSOR_ID = "binary_sensor.warmtepomp_rem_gewenst"
SCHAKELAAR = "switch.vaillant_vr940_power_limit_active"
LIMIET = "number.vaillant_vr940_power_limit"


def _bool(tekst):
    uit = env.from_string(tekst).render().strip()
    assert uit in ("True", "False"), f"geen boolean: {uit!r}"
    return uit == "True"


def rem(regie="vasthouden", niveau="high"):
    """'on', 'off' of 'unavailable', zoals HA de sensor zou zetten."""
    STATES.clear()
    STATES.update({"sensor.markedroid_regie": regie,
                   "sensor.slimhuys_zonneplan_tariefniveau_nu": niveau})
    if not _bool(SENSOR["availability"]):
        return "unavailable"
    return "on" if _bool(SENSOR["state"]) else "off"


# ---------------------------------------------------------------- de sensor

def test_vasthouden_en_duur_is_aan():
    for niveau in ("high", "very_high", "peak"):
        assert rem(niveau=niveau) == "on", niveau


def test_peak_telt_als_duur():
    # `peak` bevat het woord 'high' niet; daar zijn de dashboardpillen al eens
    # op stukgelopen (zie Stroomprijs.yaml).
    assert rem(niveau="peak") == "on"


def test_niet_duur_is_uit():
    for niveau in ("very_low", "low", "medium"):
        assert rem(niveau=niveau) == "off", niveau


def test_andere_regie_is_uit():
    for regie in ("eigen_verbruik", "geforceerd_laden", "flex", "geblokkeerd",
                  "geen_regie", "teruglevering_voorrang", "max_terugleveren",
                  "onbekend_9"):
        assert rem(regie=regie) == "off", regie


def test_onbekende_regie_bij_duur_beslist_niets():
    for regie in ("unavailable", "unknown", "niet_geleverd"):
        assert rem(regie=regie, niveau="peak") == "unavailable", regie


def test_onbekende_regie_bij_goedkoop_is_gewoon_uit():
    assert rem(regie="unavailable", niveau="low") == "off"


def test_onbekend_tarief_bij_vasthouden_beslist_niets():
    for niveau in ("unavailable", "unknown"):
        assert rem(niveau=niveau) == "unavailable", niveau


def test_onbekend_tarief_bij_eigen_verbruik_is_uit():
    assert rem(regie="eigen_verbruik", niveau="unavailable") == "off"


def test_alles_onbekend_beslist_niets():
    assert rem(regie="unavailable", niveau="unavailable") == "unavailable"


# ----------------------------------------------------- de automatisering

def _takken():
    keuze = [a for a in AUTO["actions"] if "choose" in a]
    assert len(keuze) == 1, "verwacht precies één choose"
    return keuze[0]["choose"]


def _tak_voldaan(tak, trigger_id, rem_stand, schakelaar, limiet):
    STATES.clear()
    STATES.update({SENSOR_ID: rem_stand, SCHAKELAAR: schakelaar, LIMIET: limiet})
    for c in tak["conditions"]:
        soort = c["condition"]
        if soort == "state":
            if not ha_is_state(c["entity_id"], c["state"]):
                return False
        elif soort == "template":
            if not _bool(c["value_template"]):
                return False
        elif soort == "trigger":
            if trigger_id != c["id"]:
                return False
        else:
            raise AssertionError(f"onbekende conditie {soort}")
    return True


def acties(trigger_id, rem_stand, schakelaar="off", limiet="250"):
    """De service-calls die de automatisering zou doen (eerste ware tak)."""
    for tak in _takken():
        if _tak_voldaan(tak, trigger_id, rem_stand, schakelaar, limiet):
            return [(s["action"], s["target"]["entity_id"], (s.get("data") or {}).get("value"))
                    for s in tak["sequence"]]
    return []


AAN = [("number.set_value", LIMIET, 250), ("switch.turn_on", SCHAKELAAR, None)]
UIT = [("switch.turn_off", SCHAKELAAR, None)]


def test_triggers():
    ids = {(t["trigger"], t.get("to"), t["id"]) for t in AUTO["triggers"]}
    assert ("state", "on", "aan") in ids
    assert ("state", "off", "uit") in ids
    assert any(t["trigger"] == "time_pattern" and t["id"] == "controle" for t in AUTO["triggers"])
    assert all(t.get("entity_id", SENSOR_ID) == SENSOR_ID for t in AUTO["triggers"])


def test_eerst_250_w_dan_de_schakelaar():
    # De add-on weigert de schakelaar onder 500 W als die waarde niet in
    # dezelfde run uit HA kwam; de volgorde is dus geen smaak.
    assert acties("aan", "on", schakelaar="off", limiet="1000") == AAN


def test_staat_er_al_goed_op_dan_niets():
    assert acties("controle", "on", schakelaar="on", limiet="250") == []
    assert acties("controle", "on", schakelaar="on", limiet="250.0") == []


def test_controle_zet_een_vervallen_limiet_terug():
    assert acties("controle", "on", schakelaar="off") == AAN
    assert acties("controle", "on", schakelaar="on", limiet="1000") == AAN
    assert acties("controle", "on", schakelaar="unavailable", limiet="unknown") == AAN


def test_uit_op_de_overgang():
    assert acties("uit", "off", schakelaar="on") == UIT


def test_uit_niet_als_hij_al_uit_staat():
    assert acties("uit", "off", schakelaar="off") == []


def test_controle_haalt_een_handmatige_limiet_niet_weg():
    assert acties("controle", "off", schakelaar="on") == []


def test_onbeslist_doet_niets():
    for trigger_id in ("controle", "uit", "aan"):
        assert acties(trigger_id, "unavailable", schakelaar="on") == [], trigger_id
        assert acties(trigger_id, "unavailable", schakelaar="off") == [], trigger_id


if __name__ == "__main__":
    import sys
    fouten = 0
    for naam, f in sorted(globals().items()):
        if naam.startswith("test_") and callable(f):
            try:
                f()
                print(f"ok    {naam}")
            except AssertionError as e:
                fouten += 1
                print(f"FOUT  {naam}: {e}")
    sys.exit(1 if fouten else 0)
