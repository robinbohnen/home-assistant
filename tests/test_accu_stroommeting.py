"""Offline test van de melding "stroommeting accu werkt niet goed" (29 oktober 2026).

Draaien:  .venv/bin/python tests/test_accu_stroommeting.py      (nodig: jinja2, pyyaml)

Haalt de template van `binary_sensor.accu_stroommeting_verdacht` en de
automatisering `accu_stroommeting_melding` letterlijk uit
packages/9 - Other/Battery.yaml, dus geen kopie die kan afwijken.
Bewaakt wordt:
1. aan bij `eigen_verbruik` + accu binnen ±100 W + afname van het net;
2. uit bij elke andere regie, een accu die echt werkt, geen afname, of een
   afname die helemaal van de laadpaal komt;
3. uit bij een (bijna) lege accu en bij een stille MarkeDroid;
4. de tien minuten vertraging, de twaalf-uursrem en het bericht zelf.
"""
import os
from datetime import datetime, timedelta

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCU = f"{CONFIG}/packages/9 - Other/Battery.yaml"

STATES = {}


def ha_states(eid):
    v = STATES.get(eid, "unknown")
    return v if isinstance(v, str) else str(v)


def ha_is_state(eid, state):
    return ha_states(eid) == state


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
env.globals.update(states=ha_states, is_state=ha_is_state, state_attr=ha_state_attr,
                   is_number=ha_is_number, timedelta=timedelta)


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


SENSOR = _zoek(ACCU, "unique_id", "accu_stroommeting_verdacht")
AUTO = _zoek(ACCU, "id", "accu_stroommeting_melding")


def wereld(regie="eigen_verbruik", accu="20", net="850", laadpaal="0", lading="60"):
    STATES.clear()
    STATES.update({
        "sensor.markedroid_regie": regie,
        "sensor.markedroid_accu_vermogen": accu,
        "sensor.slimhuys_zonneplan_actief_vermogen": net,
        "sensor.charging_station_active_power": laadpaal,
        "sensor.accu_lading": lading,
        "sensor.accu_capaciteit.afslag_procent": "10",
    })


def verdacht(**kw):
    wereld(**kw)
    uit = env.from_string(SENSOR["state"]).render().strip()
    assert uit in ("True", "False"), f"geen boolean: {uit!r}"
    return uit == "True"


def test_storing_gaat_aan():
    assert verdacht()


def test_ontladen_en_laden_tellen_als_werkend():
    assert not verdacht(accu="-2426")
    assert not verdacht(accu="800")


def test_grens_100_w_beide_kanten():
    assert verdacht(accu="99")
    assert verdacht(accu="-99")
    assert not verdacht(accu="100")
    assert not verdacht(accu="-100")


def test_alleen_bij_eigen_verbruik():
    for regie in ("vasthouden", "geblokkeerd", "flex", "geforceerd_laden",
                  "geen_regie", "niet_geleverd", "unavailable"):
        assert not verdacht(regie=regie), regie


def test_geen_afname_geen_melding():
    assert not verdacht(net="35")
    assert not verdacht(net="200")
    assert verdacht(net="201")


def test_laadpaal_telt_niet_mee():
    # Auto laadt 7,4 kW, huis zelf trekt niets van het net: geen storing.
    assert not verdacht(net="7450", laadpaal="7400")
    # Auto laadt, en het huis trekt er nog 600 W bovenop: wél.
    assert verdacht(net="8000", laadpaal="7400")


def test_lege_accu_mag_stil_staan():
    assert not verdacht(lading="10")
    assert not verdacht(lading="15")
    assert verdacht(lading="16")


def test_stille_bronnen_zijn_geen_storing():
    assert not verdacht(accu="unavailable")
    assert not verdacht(net="unavailable")
    assert not verdacht(lading="unavailable")


def test_vertraging_en_type():
    assert SENSOR["delay_on"] == "00:10:00"
    assert SENSOR["device_class"] == "problem"


def test_automatisering_luistert_naar_de_sensor():
    trig = AUTO["triggers"][0]
    assert trig["entity_id"] == "binary_sensor.accu_stroommeting_verdacht"
    assert trig["to"] == "on"
    assert AUTO["actions"][0]["action"] == "notify.mobile_devices_robin"


class _Dit:
    def __init__(self, laatst):
        self.attributes = {"last_triggered": laatst}


def _rem(laatst):
    t = env.from_string(AUTO["conditions"][0]["value_template"])
    env.globals["now"] = lambda: datetime(2026, 10, 29, 12, 0)
    return t.render(this=_Dit(laatst)).strip() == "True"


def test_twaalf_uursrem():
    assert _rem(None)
    assert not _rem(datetime(2026, 10, 29, 8, 0))
    assert _rem(datetime(2026, 10, 28, 23, 0))


def test_bericht_noemt_de_getallen():
    wereld(accu="-12.4", net="853.6")
    data = AUTO["actions"][0]["data"]
    bericht = env.from_string(data["message"]).render()
    assert "(-12 W)" in bericht, bericht
    assert "854 W" in bericht, bericht
    assert data["title"] == "Stroommeting accu werkt niet goed"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
