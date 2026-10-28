"""Offline test van het leesfout-filter op de zon (28 oktober 2026).

Draaien:  .venv/bin/python tests/test_zon_filter.py      (nodig: jinja2, pyyaml)

Haalt twee templates letterlijk uit de YAML, dus geen kopie die kan afwijken:
- `sensor.zon_vermogen_nu`        (packages/2 - Second Floor/Attic/Solarpanels.yaml)
- `sensor.markedroid_zon_energie` (packages/9 - Other/Battery.yaml)

Sinds 26-10 ~23:20 stuurt MarkeDroid in `public/realtimedata/solar` af en toe
onzin als 263.457 W, met een `TotWhInc` die net zo kapot is (~350 Wh in tien
seconden), ook 's nachts. De berichten hieronder komen uit de echte historie.
Bewaakt wordt:
1. 's nachts (zon < -3 graden) is het vermogen 0 en telt de teller niets,
   ook bij een glitch onder het plafond (5100 W om 23:20);
2. boven het plafond (1,3 x piekvermogen) of onder 0 blijft de vorige stand;
3. de teller vervangt een te groot increment door het gefilterde vermogen;
4. gewone waarden en het oude 0 W-filter werken zoals voorheen.
"""
import os

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZON = f"{CONFIG}/packages/2 - Second Floor/Attic/Solarpanels.yaml"
ACCU = f"{CONFIG}/packages/9 - Other/Battery.yaml"

STATES = {}


def ha_states(eid):
    v = STATES.get(eid, "unknown")
    return v if isinstance(v, str) else str(v)


def ha_state_attr(eid, attr):
    return STATES.get(f"{eid}.{attr}")


def ha_is_number(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


env = Environment()
env.filters["float"] = f_float
env.globals.update(states=ha_states, state_attr=ha_state_attr, is_number=ha_is_number)


def _sensor(pad, unique_id):
    """Zoek een template-sensor op unique_id, waar hij ook in het pakket zit."""
    with open(pad, encoding="utf-8") as f:
        knopen = [yaml.safe_load(f)]
    while knopen:
        k = knopen.pop()
        if isinstance(k, dict):
            if k.get("unique_id") == unique_id and "state" in k:
                return k
            knopen.extend(k.values())
        elif isinstance(k, list):
            knopen.extend(k)
    raise AssertionError(f"{unique_id} niet gevonden in {pad}")


ZON_SENSOR = _sensor(ZON, "zon_vermogen_nu")
TELLER = _sensor(ACCU, "markedroid_zon_energie")
PIEK = ZON_SENSOR["attributes"]["piekvermogen"]


def wereld(elevatie=30, zon_nu="2000"):
    STATES.clear()
    STATES.update({
        "sun.sun.elevation": elevatie,
        "sensor.zon_vermogen_nu": zon_nu,
        "sensor.zon_vermogen_nu.piekvermogen": PIEK,
        "sensor.markedroid_zon_vermogen": zon_nu,
    })


def bericht(w, inc=None, sl=10.0):
    if inc is None:
        inc = w * sl / 3600
    return {"platform": "mqtt", "payload_json": {"W": w, "TotWhInc": inc, "SinceLast": sl}}


def vermogen(trigger, vorige):
    uit = env.from_string(ZON_SENSOR["state"]).render(trigger=trigger, this={"state": str(vorige)})
    return float(uit.strip())


def teller(trigger, vorige=1000.0):
    uit = env.from_string(TELLER["state"]).render(trigger=trigger, this={"state": str(vorige)})
    return round(float(uit.strip()) - vorige, 2)


# --- vermogen ---------------------------------------------------------------

def test_gewone_waarde_gaat_door():
    wereld()
    assert vermogen(bericht(3456.7), 3000) == 3456.7


def test_glitch_boven_plafond_houdt_vorige_vast():
    wereld()
    assert vermogen(bericht(263457, inc=343.0), 3000) == 3000


def test_negatief_houdt_vorige_vast():
    wereld()
    assert vermogen(bericht(-137), 2500) == 2500


def test_plafond_is_1_3_maal_piek():
    wereld()
    assert PIEK == 9460
    assert vermogen(bericht(12290), 3000) == 12290
    assert vermogen(bericht(12310), 3000) == 3000


def test_nacht_is_nul_ook_onder_plafond():
    wereld(elevatie=-40)
    assert vermogen(bericht(5100), 0) == 0
    assert vermogen(bericht(263626), 0) == 0


def test_schemer_laat_echte_opwek_door():
    wereld(elevatie=-1)
    assert vermogen(bericht(35), 40) == 35


def test_vorige_glitch_wordt_niet_vastgehouden():
    # Na de deploy kan de oude stand zelf nog een glitch zijn.
    wereld()
    assert vermogen(bericht(198034), 263281) == 0


def test_oude_nulfilter_werkt_nog():
    wereld()
    assert vermogen(bericht(0, inc=5.0), 2500) == 2500   # leesfout: teller zegt 1,8 kW
    assert vermogen(bericht(0, inc=0.0), 2500) == 0      # echt weg


def test_zonder_sun_niet_alles_nul():
    wereld()
    del STATES["sun.sun.elevation"]
    assert vermogen(bericht(1500), 1400) == 1500


def test_terug_van_unavailable_ook_gefilterd():
    wereld(zon_nu="263457")
    assert vermogen({"platform": "state"}, 2000) == 2000


# --- teller -----------------------------------------------------------------

def test_teller_gewoon_increment():
    wereld()
    assert teller(bericht(3600, inc=10.0)) == 10.0


def test_teller_glitch_wordt_gefilterd_vermogen():
    wereld(zon_nu="1800")
    # 343 Wh in 10 s is 123 kW; in plaats daarvan 1800 W x 10 s = 5 Wh.
    assert teller(bericht(263457, inc=343.0)) == 5.0


def test_teller_nacht_telt_niets():
    wereld(elevatie=-30, zon_nu="0")
    assert teller(bericht(5100, inc=14.2)) == 0
    assert teller(bericht(263457, inc=343.0)) == 0


def test_teller_negatief_en_ontbrekend_veld_is_nul():
    wereld()
    assert teller(bericht(100, inc=-3.0)) == 0
    assert teller({"platform": "mqtt", "payload_json": {"W": 0}}) == 0


def test_teller_eenheid_blijft_wh():
    # SlimHuys deelt door 1000 op basis van deze eenheid (zie Battery.yaml).
    assert TELLER["unit_of_measurement"] == "Wh"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print("OK  ", naam)
