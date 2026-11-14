"""Offline test van de rackventilatoren zonder rack-meting (14 november 2026).

Draaien:  python3 tests/test_rackventilatie.py      (nodig: jinja2, pyyaml)
          of: python3 -m pytest tests/test_rackventilatie.py

Leest `binary_sensor.serverrack_apparaten_warm` en de automatisering
`ventilation_cooling_server_rack` letterlijk uit packages/9 - Other/
Ventilation.yaml. Bewaakt wordt:

1. de apparatensensor: aan zodra één apparaat zijn aan-grens haalt, uit pas
   als álles onder de uit-grens zit, daartussen blijft de stand staan; een
   apparaat zonder meting telt niet mee, en zonder één enkele meting is hij
   `unavailable`. Een half uur `delay_off` (stabiel) en vijf minuten
   `delay_on` (geen CPU-piekjes);
2. de aan-grenzen liggen onder de oranje grenzen van het Server-dashboard;
3. de automatisering, tak voor tak doorgerekend: zonder rack-meting gaan de
   ventilatoren alleen aan als de apparaten warm zijn of niets meten, en uit
   als ze stabiel koel zijn - niet binnen het eerste half uur na het wegvallen
   van de rack-sensor, en nooit tijdens handbediening. Met een rack-meting
   blijft alles zoals het was.
"""
import os
from datetime import datetime, timedelta

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAKKET = f"{CONFIG}/packages/9 - Other/Ventilation.yaml"

RACK = "sensor.garage_serverrack_temperatuur_temperature"
GARAGE = "sensor.garage_garage_temperatuur_temperatuur"
FAN = "switch.garage_garage_stopcontact_serverrack_ventilatoren"
WARM = "binary_sensor.serverrack_apparaten_warm"
HAND = "input_datetime.ventilation_serverrack_handbediening_tot"
LOCK = "input_datetime.ventilation_serverrack_lockout_until"
NU = datetime(2026, 11, 14, 12, 0)

NUC_CPU = "sensor.proxmox_nuc_intel_cpu_temperatuur"
NUC_NVME = "sensor.proxmox_nuc_intel_nvme_temperatuur"
HDD = [f"sensor.garage_unas_garage_hdd_{i}_temperature" for i in range(1, 5)]
NAS_NVME = [f"sensor.unas_garage_nvme_{i}_temperature" for i in range(2)]
APPARATEN = [NUC_CPU, NUC_NVME, *HDD, *NAS_NVME]


def _zoek(knoop, sleutel, waarde):
    knopen = [knoop]
    while knopen:
        k = knopen.pop()
        if isinstance(k, dict):
            if k.get(sleutel) == waarde:
                return k
            knopen.extend(k.values())
        elif isinstance(k, list):
            knopen.extend(k)
    raise AssertionError(f"{sleutel}={waarde} niet gevonden")


with open(PAKKET, encoding="utf-8") as f:
    YAML = yaml.safe_load(f)
SENSOR = _zoek(YAML, "unique_id", "serverrack_apparaten_warm")
AUTO = _zoek(YAML, "id", "ventilation_cooling_server_rack")
TAKKEN = AUTO["actions"][0]["choose"]


# --- Nagebootste HA-omgeving -------------------------------------------------

class St:
    def __init__(self, state, minuten_geleden=0, **attrs):
        self.state = str(state)
        self.last_changed = NU - timedelta(minutes=minuten_geleden)
        self.attributes = attrs


WERELD = {}


class Domein:
    def __init__(self, domein):
        self.domein = domein

    def __getattr__(self, naam):
        return WERELD.get(f"{self.domein}.{naam}")


class States:
    def __call__(self, eid):
        s = WERELD.get(eid)
        return s.state if s else "unknown"

    def __getattr__(self, domein):
        return Domein(domein)


def is_number(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def is_state(eid, st):
    s = WERELD.get(eid)
    return s is not None and (s.state in st if isinstance(st, list) else s.state == st)


def state_attr(eid, a):
    s = WERELD.get(eid)
    return s.attributes.get(a) if s else None


env = Environment()
env.tests["is_number"] = is_number
env.filters["states"] = lambda e: States()(e)
env.globals.update(states=States(), is_number=is_number, is_state=is_state,
                   state_attr=state_attr, now=lambda: NU, timedelta=timedelta)


def render(tpl, **kw):
    return env.from_string(tpl).render(**kw).strip()


# --- 1. De apparatensensor ----------------------------------------------------

class This:
    def __init__(self, state):
        self.state = state


def apparaten(temps, vorige="off"):
    """temps: {entity: waarde}; wat ontbreekt is `unavailable`."""
    WERELD.clear()
    for e in APPARATEN:
        WERELD[e] = St(temps.get(e, "unavailable"))
    if render(SENSOR["availability"]) != "True":
        return "unavailable"
    uit = render(SENSOR["state"], this=This(vorige)).lower()
    assert uit in ("true", "false"), repr(uit)
    return "on" if uit == "true" else "off"


KOEL = {NUC_CPU: 55, NUC_NVME: 42, **{h: 34 for h in HDD}, **{n: 40 for n in NAS_NVME}}


def test_alles_koel_is_uit():
    assert apparaten(KOEL) == "off"
    assert apparaten(KOEL, vorige="on") == "off"


def test_een_apparaat_boven_aangrens_is_aan():
    for e, grens in [(NUC_CPU, 80), (NUC_NVME, 55), (HDD[2], 42), (NAS_NVME[1], 55)]:
        assert apparaten({**KOEL, e: grens}) == "on", e
        assert apparaten({**KOEL, e: grens - 0.1}) == "off", e


def test_hysterese_tussen_de_grenzen():
    tussen = {**KOEL, HDD[0]: 41}  # tussen uit 40 en aan 42
    assert apparaten(tussen, vorige="on") == "on"
    assert apparaten(tussen, vorige="off") == "off"
    assert apparaten({**KOEL, HDD[0]: 39.9}, vorige="on") == "off"
    assert apparaten({**KOEL, NUC_CPU: 77}, vorige="on") == "on"
    assert apparaten({**KOEL, NUC_CPU: 74}, vorige="on") == "off"


def test_apparaat_zonder_meting_telt_niet_mee():
    zonder = {k: v for k, v in KOEL.items() if k != NUC_CPU}
    assert apparaten(zonder) == "off"
    assert apparaten({**zonder, HDD[3]: 46}) == "on"


def test_niets_gemeten_is_unavailable():
    assert apparaten({}) == "unavailable"
    assert apparaten({NUC_CPU: "unknown"}) == "unavailable"
    assert apparaten({HDD[0]: 33}) == "off"


def test_vertragingen_en_lijsten_gelijk():
    assert SENSOR["delay_on"] == "00:05:00"
    assert SENSOR["delay_off"] == "00:30:00"
    for e in APPARATEN:
        assert e in SENSOR["availability"], e
        assert e in SENSOR["state"], e
    # De NAS-CPU heeft geen geijkte grens en hoort er dus niet in.
    assert "unas_garage_cpu_temperature" not in SENSOR["state"]


def test_aangrenzen_onder_oranje_van_dashboard():
    oranje = {NUC_CPU: 85, NUC_NVME: 60, **{h: 45 for h in HDD}, **{n: 60 for n in NAS_NVME}}
    for e, o in oranje.items():
        assert apparaten({**KOEL, e: o - 0.5}) == "on", f"{e} pas aan na oranje"


# --- 3. De automatisering, tak voor tak --------------------------------------

def evalueer(c, trigger_id="eval", fan_aan_minuten=0):
    t = c["condition"]
    if t == "template":
        return render(c["value_template"], trigger=None) == "True"
    if t == "state":
        ids = c["entity_id"] if isinstance(c["entity_id"], list) else [c["entity_id"]]
        ok = all(is_state(e, c["state"]) for e in ids)
        if ok and "for" in c:
            ok = fan_aan_minuten >= c["for"].get("hours", 0) * 60 + c["for"].get("minutes", 0)
        return ok
    if t == "trigger":
        return trigger_id in (c["id"] if isinstance(c["id"], list) else [c["id"]])
    raise ValueError(f"conditie {t} niet nagebootst")


def beslis(fan="off", rack="unavailable", rack_weg_min=60, garage="15",
           warm="off", hand_tot=None, lock_tot=None):
    WERELD.clear()
    WERELD.update({
        RACK: St(rack, rack_weg_min),
        GARAGE: St(garage),
        FAN: St(fan, 10),
        WARM: St(warm),
        HAND: St("x", timestamp=(hand_tot or NU - timedelta(hours=1)).timestamp()),
        LOCK: St("x", timestamp=(lock_tot or NU - timedelta(hours=1)).timestamp()),
        "input_number.ventilation_serverrack_critical_threshold": St(35),
        "input_number.ventilation_serverrack_warm_threshold": St(28),
        "input_number.ventilation_serverrack_cool_threshold": St(25),
        "input_number.ventilation_serverrack_delta_on": St(2),
        "input_number.ventilation_serverrack_delta_off": St(0.5),
        "input_number.ventilation_serverrack_stagnation_delta": St(0.2),
        "sensor.ventilatie_serverrack_temp_verandering_1u": St(-1),
    })
    for tak in TAKKEN:
        if all(evalueer(c) for c in tak["conditions"]):
            return tak["sequence"][0]["action"]
    return None


def test_blind_en_apparaten_koel_blijft_uit():
    assert beslis(fan="off", warm="off") is None


def test_blind_en_apparaten_warm_gaat_aan():
    assert beslis(fan="off", warm="on") == "switch.turn_on"


def test_blind_en_apparaten_meten_niets_gaat_aan_zoals_vroeger():
    assert beslis(fan="off", warm="unavailable") == "switch.turn_on"
    assert beslis(fan="off", warm="unknown") == "switch.turn_on"


def test_blind_en_apparaten_stabiel_koel_gaat_uit():
    assert beslis(fan="on", warm="off") == "switch.turn_off"


def test_blind_en_apparaten_nog_warm_blijft_aan():
    assert beslis(fan="on", warm="on") is None
    assert beslis(fan="on", warm="unavailable") is None


def test_eerste_half_uur_na_wegvallen_niets():
    assert beslis(fan="on", warm="off", rack_weg_min=10) is None
    assert beslis(fan="off", warm="on", rack_weg_min=10) is None


def test_handbediening_wint():
    later = NU + timedelta(hours=1)
    assert beslis(fan="on", warm="off", hand_tot=later) is None
    assert beslis(fan="off", warm="on", hand_tot=later) is None


def test_met_rack_meting_verandert_niets():
    # Rack warm en garage koeler: aan, ongeacht de apparaten.
    assert beslis(fan="off", rack="29", garage="20", warm="off") == "switch.turn_on"
    # Rack koel: uit, ook als de apparaten warm zijn (zoals het was).
    assert beslis(fan="on", rack="24", garage="20", warm="on") == "switch.turn_off"
    # Kritiek: aan.
    assert beslis(fan="off", rack="36", garage="40", warm="off") == "switch.turn_on"


def test_trigger_op_apparatensensor():
    trig = [t for t in AUTO["triggers"] if WARM in (t.get("entity_id") or [])]
    assert len(trig) == 1 and trig[0]["id"] == "eval"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
