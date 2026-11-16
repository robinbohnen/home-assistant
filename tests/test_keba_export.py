"""Offline test van het overdraagbare KEBA P40-pakket (export/keba-p40/).

Draaien:  python3 -m pytest tests/test_keba_export.py      (nodig: jinja2, pyyaml)

Leest de templates letterlijk uit export/keba-p40/keba_p40_slim_laden.yaml en
draait ze met nagebootste HA-functies. Bewaakt wordt:
1. er staat niets meer in van DIT huis (Renault, slimhuys-prijzen, eigen
   notify-groep, IP van de paal hier), en elke `VERVANG` staat in een
   adapterregel - niet midden in de logica;
2. elke entiteit waar een template of automatisering naar verwijst wordt in
   het pakket zelf aangemaakt, op de adapter-placeholders na;
3. de modbus-registers zijn gelijk aan die in het origineel (geen stille drift);
4. de prijsadapter maakt van Nord Pool-achtige raw_today/raw_tomorrow een
   gesorteerde lijst en laat lege blokken weg;
5. het laadplan kiest het goedkoopste venster vóór de deadline en geeft 'vol',
   'geen prijzen', 'wacht op prijzen' en 'past niet' op de juiste momenten;
6. de stopregel en de deadline-knoppen (ochtend/middag/later).
"""
import ast
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = f"{CONFIG}/export/keba-p40/keba_p40_slim_laden.yaml"
ORIGINEEL = f"{CONFIG}/packages/3 - Outside/Carport/KEBA P40 Pro.yaml"
TZ = ZoneInfo("Europe/Amsterdam")

with open(EXPORT, encoding="utf-8") as f:
    TEKST = f.read()
PAKKET = yaml.safe_load(TEKST)["keba_p40_slim_laden"]


# --- nagebootste HA-omgeving --------------------------------------------------

STATES = {}
NU = [datetime(2026, 11, 15, 18, 0, tzinfo=TZ)]


def _as_datetime(v, default=None):
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return datetime.fromtimestamp(v, tz=timezone.utc)
    if isinstance(v, str):
        try:
            d = datetime.fromisoformat(v)
        except ValueError:
            return default
        return d
    return default


def _as_timestamp(v, default=None):
    d = _as_datetime(v)
    return d.timestamp() if d is not None else default


def _states(eid):
    return STATES[eid][0] if eid in STATES else "unknown"


def _state_attr(eid, attr):
    return STATES[eid][1].get(attr) if eid in STATES else None


def _has_value(eid):
    return eid in STATES and STATES[eid][0] not in ("unknown", "unavailable")


def _today_at(t):
    h, m = map(int, t.split(":"))
    return NU[0].replace(hour=h, minute=m, second=0, microsecond=0)


def _float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


env = Environment(extensions=["jinja2.ext.loopcontrols"])
env.globals.update(
    states=_states, state_attr=_state_attr, has_value=_has_value,
    is_state=lambda e, s: _states(e) == s, now=lambda: NU[0], today_at=_today_at,
    timedelta=timedelta, as_timestamp=_as_timestamp, as_datetime=_as_datetime,
)
env.filters.update(
    as_datetime=_as_datetime, as_timestamp=_as_timestamp, float=_float, int=_int,
    as_local=lambda d: d.astimezone(TZ),
)


def render(tpl, **vars_):
    """Rendert zoals HA: uitkomst die een Python-literal is wordt native."""
    uit = env.from_string(tpl).render(**vars_).strip()
    try:
        return ast.literal_eval(uit)
    except (ValueError, SyntaxError):
        return uit


def zet(eid, state, **attrs):
    STATES[eid] = (str(state), attrs)


def templates():
    return PAKKET["template"]


def prijs_blok():
    return next(t for t in templates() if any(s.get("unique_id") == "laadpaal_prijzen" for s in t.get("sensor", [])))


def plan_blok():
    return next(t for t in templates() if any(s.get("unique_id") == "charging_station_laadplan" for s in t.get("sensor", [])))


def automatisering(aid):
    return next(a for a in PAKKET["automation"] if a["id"] == aid)


def slug(naam):
    return re.sub(r"[^a-z0-9]+", "_", naam.lower()).strip("_")


# --- 1. niets van dit huis, VERVANG alleen in adapterregels -------------------

def test_geen_verwijzingen_naar_dit_huis():
    for verboden in ["hrh85f", "megane", "slimhuys", "mobile_devices_adults",
                     "home_assistant_gestart", "192.168.30.", "36462996", "Robin"]:
        assert verboden not in TEKST, verboden


def test_vervang_alleen_in_adapter():
    adapter_eind = TEKST.index("# 2. VERTALING")
    toegestaan_later = ["host:", "max: 16", "notify.mobile_app_vervang"]
    for nr, regel in enumerate(TEKST.splitlines(), 1):
        if "VERVANG" in regel or "vervang_door" in regel:
            pos = sum(len(r) + 1 for r in TEKST.splitlines()[:nr - 1])
            if pos > adapter_eind:
                assert any(t in regel for t in toegestaan_later), f"regel {nr}: {regel.strip()}"


# --- 2. elke verwijzing bestaat in het pakket ---------------------------------

def gedefinieerd():
    ids = set()
    for t in templates():
        for s in t.get("sensor", []):
            ids.add("sensor." + slug(s["name"]))
    for s in PAKKET["modbus"][0]["sensors"]:
        ids.add("sensor." + slug(s["name"]))
    for dom in ("input_boolean", "input_number", "input_datetime", "script"):
        ids |= {f"{dom}.{k}" for k in PAKKET[dom]}
    ids |= {"automation." + slug(a["alias"]) for a in PAKKET["automation"]}
    return ids


def test_alle_verwijzingen_bestaan():
    bekend = gedefinieerd()
    patroon = r"\b(sensor|binary_sensor|number|input_boolean|input_number|input_datetime|script|automation)\.([a-z0-9_]+)"
    # `action: input_boolean.turn_on` e.d. zijn acties, geen entiteiten.
    zonder_acties = "\n".join(r for r in TEKST.splitlines() if not r.strip().startswith(("action:", "- action:")))
    for dom, obj in set(re.findall(patroon, zonder_acties)):
        eid = f"{dom}.{obj}"
        if "vervang_door" in obj:
            continue
        assert eid in bekend, f"{eid} wordt gebruikt maar niet aangemaakt"


def test_automatisering_ids_uniek():
    ids = [a["id"] for a in PAKKET["automation"]]
    assert len(ids) == len(set(ids))


# --- 3. modbus gelijk aan het origineel ---------------------------------------

def test_registers_gelijk_aan_origineel():
    with open(ORIGINEEL, encoding="utf-8") as f:
        orig = yaml.safe_load(f)["carport_keba_p40_package"]["modbus"][0]["sensors"]
    orig = {s["unique_id"]: s for s in orig}
    for s in PAKKET["modbus"][0]["sensors"]:
        o = orig[s["unique_id"]]
        for veld in ("name", "address", "data_type", "scale", "slave", "state_class"):
            assert s.get(veld) == o.get(veld), f"{s['unique_id']}.{veld}"


def test_schrijfregisters_gelijk_aan_origineel():
    with open(ORIGINEEL, encoding="utf-8") as f:
        orig = f.read()
    for adres in ("5004", "5018", "5052"):
        assert f"address: {adres}" in orig and f"address: {adres}" in TEKST


# --- 4. prijsadapter ----------------------------------------------------------

def nordpool(dag, prijzen, minuten=15):
    t0 = datetime.combine(dag, datetime.min.time(), tzinfo=TZ)
    return [{"start": (t0 + timedelta(minutes=i * minuten)).isoformat(),
             "end": (t0 + timedelta(minutes=(i + 1) * minuten)).isoformat(),
             "value": p} for i, p in enumerate(prijzen)]


def adapter_blokken(vandaag, morgen):
    STATES.clear()
    zet("sensor.np", "0.3", raw_today=vandaag, raw_tomorrow=morgen)
    return render(prijs_blok()["variables"]["blokken"], bron_vandaag="sensor.np", bron_morgen="sensor.np")


def test_adapter_voegt_samen_en_sorteert():
    d = NU[0].date()
    b = adapter_blokken(nordpool(d, [0.3, 0.2]), nordpool(d + timedelta(days=1), [0.1]))
    assert [x["p"] for x in b] == [0.3, 0.2, 0.1]
    assert b[1]["t"] - b[0]["t"] == 900
    assert all(isinstance(x["t"], int) for x in b)


def test_adapter_laat_lege_blokken_weg():
    d = NU[0].date()
    b = adapter_blokken(nordpool(d, [0.3, None, "x"]), None)
    assert [x["p"] for x in b] == [0.3]


def test_adapter_zonder_bron_is_leeg():
    STATES.clear()
    assert render(prijs_blok()["variables"]["blokken"], bron_vandaag="sensor.x", bron_morgen="sensor.x") == []


# --- 5. laadplan --------------------------------------------------------------

def uurblokken(start, prijzen):
    return [{"t": int((start + timedelta(hours=i)).timestamp()), "p": p} for i, p in enumerate(prijzen)]


def wereld(soc=40, doel=80, prijzen=None, klaar_om=None, sessie="off"):
    STATES.clear()
    if soc is not None:
        zet("sensor.laadpaal_auto_accu", soc)
    zet("sensor.laadpaal_auto_laaddoel", doel)
    zet("sensor.laadpaal_auto_capaciteit", 60)
    zet("sensor.charging_station_max_supported_current", 16)
    zet("sensor.charging_station_phases", 3)
    zet("input_boolean.charging_station_laadsessie", sessie)
    zet("sensor.laadpaal_prijzen", len(prijzen or []), blokken=prijzen or [])
    if klaar_om is not None:
        zet("input_datetime.charging_station_klaar_om", klaar_om.strftime("%Y-%m-%d %H:%M:%S"),
            timestamp=klaar_om.timestamp())


def plan():
    return render(plan_blok()["variables"]["plan"])


def test_kiest_goedkoopste_venster_voor_deadline():
    # 40 -> 80% van 60 kWh = 24 kWh, 11 kW: ~2,8 uur => 3 uurblokken.
    start = NU[0].replace(minute=0)
    prijzen = [0.40] * 6 + [0.10, 0.10, 0.10] + [0.30] * 4 + [0.01] * 3   # die laatste na de deadline
    deadline = start + timedelta(hours=13)
    wereld(prijzen=uurblokken(start, prijzen), klaar_om=deadline)
    p = plan()
    assert p["reden"] == "plan"
    assert datetime.fromisoformat(p["van"]) == start + timedelta(hours=6)
    assert datetime.fromisoformat(p["tot"]) == start + timedelta(hours=9)
    assert p["kwh"] == 24.0
    assert abs(p["gemiddelde"] - 0.10) < 1e-9


def test_bijna_vol_is_vol():
    wereld(soc=77, doel=80, prijzen=uurblokken(NU[0], [0.2] * 10))
    assert plan()["reden"] == "vol"


def test_bijna_vol_tijdens_sessie_laadt_door():
    wereld(soc=77, doel=80, prijzen=uurblokken(NU[0], [0.2] * 10),
           klaar_om=NU[0] + timedelta(hours=9), sessie="on")
    assert plan()["reden"] == "plan"


def test_zonder_prijzen():
    wereld(prijzen=[])
    assert plan()["reden"] == "geen prijzen"


def test_wacht_op_prijzen_als_ze_niet_tot_de_deadline_reiken():
    wereld(prijzen=uurblokken(NU[0], [0.2] * 2), klaar_om=NU[0] + timedelta(hours=14))
    assert plan()["reden"] == "wacht op prijzen"


def test_past_niet_bij_krappe_deadline():
    wereld(prijzen=uurblokken(NU[0], [0.2] * 10), klaar_om=NU[0] + timedelta(hours=1))
    assert plan()["reden"] == "past niet"


def test_zonder_accustand_rekent_op_volle_lading():
    wereld(soc=None, doel=80, prijzen=uurblokken(NU[0], [0.2] * 20), klaar_om=NU[0] + timedelta(hours=12))
    assert plan()["kwh"] == 48.0


def test_deadline_in_verleden_valt_terug_op_0700():
    wereld(prijzen=[], klaar_om=NU[0] - timedelta(days=2))
    dl = datetime.fromisoformat(plan()["deadline"])
    assert (dl.hour, dl.minute) == (7, 0) and dl > NU[0]


# --- 6. stopregel en deadline-knoppen -----------------------------------------

def stop_waar(soc=50, doel=80, kabel="7", slim="on", deadline_over=1):
    STATES.clear()
    zet("input_boolean.charging_station_laadsessie", "on")
    zet("input_boolean.charging_station_smart_charging", slim)
    zet("sensor.laadpaal_auto_accu", soc)
    zet("sensor.laadpaal_auto_laaddoel", doel)
    zet("sensor.charging_station_cable_state_raw", kabel)
    zet("input_datetime.charging_station_sessie_deadline", "x",
        timestamp=(NU[0] + timedelta(hours=deadline_over)).timestamp())
    tpl = automatisering("charging_station_smart_charge_stop")["conditions"][1]["value_template"]
    return render(tpl) is True


def test_stop_laadt_door_als_niets_bereikt():
    assert not stop_waar()


def test_stop_bij_vol_stekker_deadline_of_slim_uit():
    assert stop_waar(soc=80)
    assert stop_waar(kabel="1")
    assert stop_waar(deadline_over=-1)
    assert stop_waar(slim="off")


def test_stop_niet_bij_modbus_hapering():
    assert not stop_waar(kabel="unavailable")


def deadline(wanneer, nu):
    NU[0] = nu
    try:
        tpl = PAKKET["script"]["charging_station_deadline_zetten"]["sequence"][0]["data"]["datetime"]
        return render(tpl, wanneer=wanneer)
    finally:
        NU[0] = datetime(2026, 11, 15, 18, 0, tzinfo=TZ)


def test_deadline_knoppen():
    avond = datetime(2026, 11, 15, 18, 0, tzinfo=TZ)
    assert deadline("ochtend", avond) == "2026-11-16 07:00:00"
    assert deadline("middag", avond) == "2026-11-16 17:00:00"
    assert deadline("later", avond) == "2026-11-17 07:00:00"
    nacht = datetime(2026, 11, 16, 4, 30, tzinfo=TZ)
    assert deadline("ochtend", nacht) == "2026-11-16 07:00:00"
    kwart_voor_vijf = datetime(2026, 11, 16, 16, 45, tzinfo=TZ)
    assert deadline("middag", kwart_voor_vijf) == "2026-11-17 17:00:00"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
