"""Offline test van indicator 3 (MarkeDroid-regie) op de klokken.

Draaien:  .venv/bin/python tests/test_klok_indicatoren.py      (nodig: jinja2, pyyaml)

Leest packages/9 - Other/Klokken.yaml letterlijk en bewaakt:
1. elke regie-stand heeft de kleur uit de MarkeDroid-app (screenshot 28-10-2026);
   stop beheer, een stille MarkeDroid en onbekende codes doven het stipje;
2. het stipje staat op alle drie de klokken, en een wissel van stand triggert;
3. de zon- en accubalk lopen niet meer onder het stipje door: indicator 3
   pakt (31,6), (30,7) en (31,7), dus niets van een balk voorbij x=29.
"""
import json
import os

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLOKKEN = f"{CONFIG}/packages/9 - Other/Klokken.yaml"
STATES = {}


def ha_states(eid):
    return str(STATES.get(eid, "unknown"))


def ha_state_attr(eid, attr):
    return STATES.get(f"{eid}.{attr}")


def ha_has_value(eid):
    return ha_states(eid) not in ("unknown", "unavailable", "")


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def f_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


env = Environment()
env.filters["float"] = f_float
env.filters["int"] = f_int
env.globals.update(states=ha_states, state_attr=ha_state_attr, has_value=ha_has_value)

with open(KLOKKEN, encoding="utf-8") as fh:
    PAKKET = yaml.safe_load(fh)["klokken_package"]
AUTO = next(a for a in PAKKET["automation"] if a["id"] == "klokken_indicatoren_woonkamer_garage")
VARS = next(s["variables"] for s in AUTO["actions"] if "variables" in s)
STAP3 = next(s for s in AUTO["actions"] if s.get("alias", "").startswith("Indicator 3"))
KLOK_VARS = PAKKET["script"]["klok_zon_en_accu"]["sequence"][0]["variables"]


def regie_kleur(stand):
    STATES.clear()
    STATES["sensor.markedroid_regie"] = stand
    uit = env.from_string(VARS["regie_kleur"]).render().strip()
    return uit if uit == "uit" else json.loads(uit)


def test_kleuren_van_de_app():
    verwacht = {
        "eigen_verbruik": "lichtgroen",
        "geforceerd_laden": "blauw",
        "vasthouden": "grijs",
        "teruglevering_voorrang": "bordeaux",
        "max_terugleveren": "oranje",
        "geblokkeerd": "donkergrijs",
        "flex": "paars",
    }
    kleuren = {stand: regie_kleur(stand) for stand in verwacht}
    for k in kleuren.values():
        assert isinstance(k, list) and len(k) == 3 and all(0 <= c <= 255 for c in k)
    g, b, v, x, o, d, p = (kleuren[s] for s in verwacht)
    assert g[1] > g[0] > g[2]                       # lichtgroen: groen met wat rood
    assert b[2] == max(b) and b[0] < 50             # blauw
    assert v[0] == v[1] == v[2] > d[0] == d[1] == d[2]  # lichtgrijs feller dan donkergrijs
    assert x[0] > x[2] > x[1]                       # bordeaux: rood met wat blauw
    assert o[0] == 255 and 0 < o[1] < 150 and o[2] == 0  # oranje
    assert p[2] == 255 and p[1] == 0                # paars
    assert len({tuple(k) for k in kleuren.values()}) == len(kleuren)  # allemaal anders


def test_uit_als_er_niets_te_zeggen_valt():
    for stand in ("geen_regie", "niet_geleverd", "unavailable", "unknown", "onbekend_9"):
        assert regie_kleur(stand) == "uit", stand


def test_op_alle_drie_de_klokken():
    lampen = {
        "light.awtrix_121d6c_indicator_3",
        "light.awtrix_9c6510_indicator_3",
        "light.awtrix_9bf654_indicator_3",
    }
    assert set(STAP3["then"][0]["target"]["entity_id"]) == lampen
    aan = STAP3["else"][0]
    assert set(aan["target"]["entity_id"]) == lampen
    assert aan["data"]["brightness"] == 255         # zonder blijft het stipje uit


def test_wissel_van_stand_triggert():
    t = [t for t in AUTO["triggers"] if t.get("entity_id") == "sensor.markedroid_regie"]
    assert len(t) == 1 and "to" in t[0] and t[0]["to"] is None


def _rechterrand(payload):
    """Hoogste x die een `df`-vlak in de onderste twee rijen raakt."""
    frame = json.loads(payload)
    return max(d["df"][0] + d["df"][2] - 1 for d in frame["draw"]
               if "df" in d and d["df"][1] + d["df"][3] - 1 >= 6)


def test_balken_blijven_vrij_van_het_stipje():
    STATES.clear()
    STATES.update({
        "sensor.zon_vermogen_nu": "20000",           # ver boven het piekvermogen
        "sensor.zon_vermogen_nu.piekvermogen": 9460,
        "sensor.accu_lading": "80",
        "sensor.accu_vermogen": "-16000",
        "sensor.accu_status": "ontladen",
    })
    zon = env.from_string(KLOK_VARS["zon_payload"]).render().strip()
    accu = env.from_string(KLOK_VARS["accu_payload"]).render().strip()
    assert _rechterrand(zon) == 29
    assert _rechterrand(accu) == 29


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print("OK  ", naam)
