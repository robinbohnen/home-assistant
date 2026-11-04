"""Offline test van de leesfout-filters op de zon en de energietellers.

Draaien:  .venv/bin/python tests/test_zon_filter.py      (nodig: jinja2, pyyaml)

Haalt de templates letterlijk uit de YAML, dus geen kopie die kan afwijken:
- `sensor.zon_vermogen_zw` / `_o`  (packages/2 - Second Floor/Attic/Solarpanels.yaml)
- `sensor.zon_vermogen_nu`         (idem, de som)
- `sensor.zon_energie_totaal`      (idem, de teller voor Energie-dashboard en SlimHuys)
- `sensor.accu_geladen_totaal`     (packages/9 - Other/Battery.yaml, zelfde regels)

Sinds 4 november 2026 komt de zon uit Solarman (`sensor.inverter_pv1_power` /
`_pv2_power`). Bewaakt wordt:
1. 's nachts (zon < -3 graden) is het vermogen 0, ook bij een glitch;
2. boven 1,3 x het piekvermogen van de string of onder 0: de vorige stand;
3. een 0 na > 150 W is een leesfout zolang hij jonger is dan 90 s, en echt
   als hij langer blijft staan (gemeten: ~11% van de samples op 4-11);
4. de tellers dalen nooit en slikken geen sprong die de panelen of de accu
   in die tijd niet hadden kunnen maken, maar nemen na `unknown` alles aan;
5. `sensor.accu_capaciteit` negeert een 0 uit de instelregisters (op 4-11
   vielen capaciteit, afslag en herstart twee keer tegelijk op 0).
"""
import os
from datetime import datetime, timedelta, timezone

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZON = f"{CONFIG}/packages/2 - Second Floor/Attic/Solarpanels.yaml"
ACCU = f"{CONFIG}/packages/9 - Other/Battery.yaml"

NU = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
STATES = {}
CHANGED = {}


class Obj(dict):
    __getattr__ = dict.get


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


def ha_has_value(eid):
    return ha_states(eid) not in ("unknown", "unavailable")


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class StatesObj:
    def __getitem__(self, eid):
        if eid not in STATES:
            return None
        return Obj(state=ha_states(eid), last_changed=CHANGED.get(eid, NU - timedelta(hours=1)))

    def __call__(self, eid):
        return ha_states(eid)


env = Environment()
env.filters["float"] = f_float
env.globals.update(states=StatesObj(), state_attr=ha_state_attr, is_number=ha_is_number,
                   has_value=ha_has_value, now=lambda: NU)


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


ZW = _sensor(ZON, "zon_vermogen_zw")
O = _sensor(ZON, "zon_vermogen_o")
TOTAAL = _sensor(ZON, "zon_vermogen_nu")
TELLER = _sensor(ZON, "zon_energie_totaal")
ACCU_TELLER = _sensor(ACCU, "accu_geladen_totaal")
CAPACITEIT = _sensor(ACCU, "accu_capaciteit")
PIEK_ZW = ZW["attributes"]["piekvermogen"]


def wereld(elevatie=30, pv1="2000", pv1_sinds=5, pv2="800"):
    STATES.clear()
    CHANGED.clear()
    STATES.update({
        "sun.sun.elevation": elevatie,
        "sensor.inverter_pv1_power": pv1,
        "sensor.inverter_pv2_power": pv2,
        "sensor.zon_vermogen_nu.piekvermogen": TOTAAL["attributes"]["piekvermogen"],
    })
    CHANGED["sensor.inverter_pv1_power"] = NU - timedelta(seconds=pv1_sinds)


def zw(vorige):
    this = Obj(state=str(vorige), attributes={"piekvermogen": PIEK_ZW})
    return float(env.from_string(ZW["state"]).render(this=this).strip())


def teller(sjabloon, bron, nieuw, oud, minuten=10):
    STATES[bron] = str(nieuw)
    this = Obj(state=str(oud), last_changed=NU - timedelta(minutes=minuten))
    return float(env.from_string(sjabloon["state"]).render(this=this).strip())


# --- vermogen per string ------------------------------------------------------

def test_gewone_waarde_gaat_door():
    wereld(pv1="3456")
    assert zw(3000) == 3456


def test_glitch_boven_plafond_houdt_vorige_vast():
    wereld(pv1="65535")
    assert zw(3000) == 3000


def test_negatief_houdt_vorige_vast():
    wereld(pv1="-137")
    assert zw(2500) == 2500


def test_nacht_is_nul_ook_bij_glitch():
    wereld(elevatie=-10, pv1="5100")
    assert zw(0) == 0


def test_schemer_gaat_door():
    wereld(elevatie=-2, pv1="35")
    assert zw(40) == 35


def test_verse_nul_na_vermogen_is_leesfout():
    wereld(pv1="0", pv1_sinds=5)
    assert zw(2219) == 2219


def test_nul_die_blijft_staan_is_echt():
    wereld(pv1="0", pv1_sinds=120)
    assert zw(2219) == 0


def test_nul_na_weinig_vermogen_is_echt():
    # Bij schemer zakt een string echt naar 0; onder 150 W houden we niets vast.
    wereld(pv1="0", pv1_sinds=5)
    assert zw(120) == 0


def test_vorige_onzin_wordt_niet_vastgehouden():
    # Stond er (van vóór het filter) onzin, dan niet die vasthouden maar 0.
    wereld(pv1="-50")
    assert zw(263457) == 0


def test_eerste_render_zonder_vorige():
    wereld(pv1="0", pv1_sinds=5)
    assert zw("unknown") == 0


def test_strings_tellen_op():
    STATES.update({"sensor.zon_vermogen_zw": "1008", "sensor.zon_vermogen_o": "425"})
    assert float(env.from_string(TOTAAL["state"]).render().strip()) == 1433


def test_piekvermogen_strings_tellen_op_tot_totaal():
    assert ZW["attributes"]["piekvermogen"] + O["attributes"]["piekvermogen"] == TOTAAL["attributes"]["piekvermogen"]


# --- tellers --------------------------------------------------------------------

def test_teller_loopt_gewoon_op():
    wereld()
    assert teller(TELLER, "sensor.inverter_total_production", 213.4, 213.0) == 213.4


def test_teller_daalt_niet():
    wereld()
    assert teller(TELLER, "sensor.inverter_total_production", 0, 213.4) == 213.4


def test_teller_slikt_geen_onmogelijke_sprong():
    wereld()
    # 10 minuten, 9,46 kWp x 1,3 = ~2,05 kWh + 0,5 marge; 6553 kWh kan niet.
    assert teller(TELLER, "sensor.inverter_total_production", 6766.9, 213.4) == 213.4


def test_teller_na_lange_stilte_mag_veel():
    wereld()
    # Drie uur zonder wijziging (nacht, of Solarman weg): 30 kWh kan.
    assert teller(TELLER, "sensor.inverter_total_production", 243.4, 213.4, minuten=180) == 243.4


def test_teller_na_unknown_neemt_alles_aan():
    wereld()
    assert teller(TELLER, "sensor.inverter_total_production", 213.4, "unknown") == 213.4


def test_accuteller_zelfde_regels():
    wereld()
    assert teller(ACCU_TELLER, "sensor.inverter_total_battery_charge", 890.4, 890.3) == 890.4
    assert teller(ACCU_TELLER, "sensor.inverter_total_battery_charge", 0, 890.3) == 890.3
    assert teller(ACCU_TELLER, "sensor.inverter_total_battery_charge", 9999, 890.3) == 890.3


# --- instelregisters -------------------------------------------------------------

def _cap(ah, afslag, herstart, vorige="51.2", attrs=None):
    STATES.clear()
    STATES.update({"number.inverter_battery_capacity": ah,
                   "number.inverter_battery_shutdown_soc": afslag,
                   "number.inverter_battery_restart_soc": herstart})
    this = Obj(state=vorige, attributes=attrs if attrs is not None else {"afslag_procent": 15, "herstart_procent": 40})
    r = lambda t: env.from_string(t).render(this=this).strip()
    a = CAPACITEIT["attributes"]
    return r(CAPACITEIT["state"]), r(a["afslag_procent"]), r(a["herstart_procent"]), r(a["bruikbaar"])


def test_capaciteit_uit_register():
    assert _cap("1000", "10", "50") == ("51.2", "10", "50", "46.1")


def test_capaciteit_negeert_nul_uit_registers():
    # Het blok viel op 0: alles blijft wat het was.
    assert _cap("0", "0", "0") == ("51.2", "15", "40", "43.5")


def test_capaciteit_nul_zonder_vorige_valt_terug_op_10_en_50():
    st, afslag, herstart, _ = _cap("0", "0", "0", vorige="unknown", attrs={})
    assert (afslag, herstart) == ("10", "50")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
