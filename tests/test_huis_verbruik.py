"""Offline test van `sensor.huis_verbruik` (packages/9 - Other/Electricity.yaml), 4 november 2026.

Draaien:  .venv/bin/python tests/test_huis_verbruik.py      (nodig: jinja2, pyyaml)

Sinds 4 november een momentopname uit één Solarman-ronde: net (Deye-CT) +
zon - accu, met die drie als attribuut op de sensor zelf, zodat kaarten ze
altijd van hetzelfde moment tonen. Bewaakt wordt:
1. met Solarman: alles uit de Deye, de attributen tellen precies op tot het huis;
2. Solarman weg: terugval op de P1, en dan alleen elke 5 s een nieuw getal
   (state én attributen blijven bij tussentikken staan);
3. een accu-hikje in de terugval houdt de vorige stand vast;
4. de trigger is elke seconde en er staat geen gemiddelde meer tussen.
"""
import os
from datetime import datetime, timedelta, timezone

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAD = f"{CONFIG}/packages/9 - Other/Electricity.yaml"

NU = [datetime(2026, 11, 4, 15, 0, 10, tzinfo=timezone.utc)]
STATES = {}


class Obj(dict):
    __getattr__ = dict.get


def ha_states(eid):
    v = STATES.get(eid, "unknown")
    return v if isinstance(v, str) else str(v)


def ha_has_value(eid):
    return ha_states(eid) not in ("unknown", "unavailable")


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


class StatesObj:
    def __call__(self, eid):
        return ha_states(eid)

    def __getattr__(self, domein):
        class D:
            def __getattr__(_, naam):
                eid = f"{domein}.{naam}"
                if eid not in STATES:
                    return None
                return Obj(state=ha_states(eid), last_changed=STATES.get(eid + ".last_changed", NU[0] - timedelta(hours=1)))
        return D()


env = Environment()
env.filters["float"] = f_float
env.globals.update(states=StatesObj(), is_state=lambda e, s: ha_states(e) == s, has_value=ha_has_value,
                   is_number=ha_is_number, now=lambda: NU[0], timedelta=timedelta)


def _zoek():
    with open(PAD, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    for blok in doc["electricity_package"]["template"]:
        for s in blok.get("sensor", []):
            if s.get("unique_id") == "huis_verbruik":
                return blok, s
    raise AssertionError("huis_verbruik niet gevonden")


BLOK, SENSOR = _zoek()


def wereld(verbinding="on", deye_net="814", zon="653", accu="0", p1="0.9"):
    STATES.clear()
    STATES.update({
        "binary_sensor.inverter_connection": verbinding,
        "sensor.omvormer_net_vermogen": deye_net,
        "sensor.zon_vermogen_nu": zon,
        "sensor.accu_vermogen": accu,
        "sensor.live_energieverbruik_totaal": p1,
    })


def render(trigger_id="snel", seconde=10, vorige="1.111", attrs=None):
    NU[0] = NU[0].replace(second=seconde)
    this = Obj(state=vorige, attributes=attrs if attrs is not None else {})
    r = lambda t: env.from_string(t).render(this=this, trigger={"id": trigger_id}).strip()
    return r(SENSOR["state"]), {k: r(v) for k, v in SENSOR["attributes"].items()}


def test_deye_alles_uit_een_ronde():
    wereld()
    st, a = render()
    assert st == "1.467"
    assert a == {"bron": "deye", "net_w": "814.0", "zon_w": "653.0", "accu_w": "0.0", "huis_w": "1467.0"}


def test_laden_trekt_af_ontladen_telt_op():
    wereld(deye_net="0", zon="3000", accu="2000")
    assert render()[0] == "1.0"
    wereld(deye_net="100", zon="0", accu="-1500")
    assert render()[0] == "1.6"


def test_teruglevering_kapt_niet_onder_nul():
    wereld(deye_net="-5000", zon="1000", accu="0")
    st, a = render()
    assert st == "0" and a["huis_w"] == "0"


def test_terugval_op_p1_als_solarman_weg_is():
    wereld(verbinding="off", p1="0.9")
    st, a = render(seconde=10)
    assert st == "1.553" and a["bron"] == "p1" and a["net_w"] == "900.0"


def test_terugval_houdt_vast_tussen_de_vijf_seconden():
    wereld(verbinding="off", p1="2.5")
    oud = {"bron": "p1", "net_w": 900, "zon_w": 653, "accu_w": 0, "huis_w": 1553}
    st, a = render(seconde=11, vorige="1.553", attrs=oud)
    assert st == "1.553"
    assert a["net_w"] == "900" and a["huis_w"] == "1553"


def test_deye_houdt_niets_vast():
    # Met de Deye-bron elke tik het actuele getal: HA schrijft toch alleen als
    # het verandert, en dat is één keer per ronde.
    wereld(deye_net="500")
    assert render(seconde=11, vorige="9.999")[0] == "1.153"


def test_accu_hikje_in_terugval():
    wereld(verbinding="off", accu="unavailable")
    STATES["sensor.accu_vermogen.last_changed"] = NU[0] - timedelta(seconds=20)
    assert render(seconde=10, vorige="2.2")[0] == "2.2"


def test_elke_seconde_en_geen_gemiddelde_meer():
    tijd = [t for t in BLOK["triggers"] if t["trigger"] == "time_pattern"]
    assert tijd and tijd[0]["seconds"] == "/1"
    with open(PAD, encoding="utf-8") as f:
        assert "unique_id: huis_verbruik_gemiddeld" not in f.read()


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
