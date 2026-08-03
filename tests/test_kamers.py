"""Offline test van custom_templates/kamers.jinja met nagebootste HA-functies.

Draaien:  python3 -m venv .venv && .venv/bin/pip install jinja2
          .venv/bin/python tests/test_kamers.py

Net als test_klimaat.py: de stubs hieronder doen de Home Assistant-functies na
zodat de grenzen te testen zijn zonder te herstarten. Extra ten opzichte van dat
bestand zijn `area_entities` (de kamers worden per area opgehaald, niet met de
hand gekoppeld) en een `states` die zowel aanroepbaar als indexeerbaar is,
omdat de macro `states[id].last_updated` gebruikt om verouderde metingen te
herkennen.
"""
import json
import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATES = {}
AREAS = {}
LEEFTIJD = {}  # entity_id -> minuten geleden veranderd
NOW = dt.datetime(2026, 8, 3, 14, 0, 0)


class _Entity:
    def __init__(self, eid):
        self.entity_id = eid
        d = NOW - dt.timedelta(minutes=LEEFTIJD.get(eid, 0))
        self.last_changed = d
        self.last_updated = d
        self.state = STATES.get(eid, "unknown")


class _States:
    """states('x') geeft de state, states['x'] het object met tijdstempels."""

    def __call__(self, eid):
        v = STATES.get(eid, "unknown")
        return v if isinstance(v, str) else str(v)

    def __getitem__(self, eid):
        return _Entity(eid)


def ha_state_attr(eid, attr):
    return STATES.get(f"{eid}.{attr}")


def ha_is_state(eid, val):
    return _States()(eid) == val


def ha_area_entities(area):
    return list(AREAS.get(area, []))


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def f_as_datetime(value):
    try:
        return dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


env = Environment(loader=FileSystemLoader(f"{CONFIG}/custom_templates"))
env.filters["float"] = f_float
env.filters["as_datetime"] = f_as_datetime
env.filters["to_json"] = lambda v, **k: json.dumps(v)
env.filters["from_json"] = json.loads
env.globals.update(states=_States(), state_attr=ha_state_attr, is_state=ha_is_state,
                   area_entities=ha_area_entities, now=lambda: NOW)

MOD = env.get_template("kamers.jinja").module


def kamers():
    return {k["slug"]: k for k in json.loads(MOD.kamers_json().strip())["kamers"]}


# ---------------------------------------------------------------------------
# Wereldopbouw
# ---------------------------------------------------------------------------

def sensor(eid, waarde, device_class, area, naam=None, minuten=0):
    STATES[eid] = str(waarde)
    STATES[f"{eid}.device_class"] = device_class
    STATES[f"{eid}.friendly_name"] = naam or eid
    LEEFTIJD[eid] = minuten
    AREAS.setdefault(area, []).append(eid)


def binair(eid, aan, device_class, area, naam=None, minuten=0):
    STATES[eid] = "on" if aan else "off"
    STATES[f"{eid}.device_class"] = device_class
    STATES[f"{eid}.friendly_name"] = naam or eid
    LEEFTIJD[eid] = minuten
    AREAS.setdefault(area, []).append(eid)


def wereld(**kw):
    """Basiswereld: HA draait al een dag, buiten is 21 graden."""
    STATES.clear()
    AREAS.clear()
    LEEFTIJD.clear()
    STATES.update({
        "sensor.knmi_temperatuur": "21",
        "sensor.home_assistant_gestart": (NOW - dt.timedelta(days=1)).isoformat(),
    })
    STATES.update(kw)


FOUTEN = []


def check(naam, slug, veld, verwacht):
    k = kamers()[slug]
    gekregen = k
    for deel in veld.split("."):
        # "metingen.temp.oud" zoekt de meting met sleutel temp op, zodat de test
        # niet omvalt als de volgorde in METINGEN verandert.
        if isinstance(gekregen, list):
            gekregen = next(x for x in gekregen if x["k"] == deel)
        else:
            gekregen = gekregen[deel]
    ok = gekregen == verwacht
    print(f"{'PASS' if ok else 'FAIL'}  {naam:52} {slug:17} {veld:10} "
          f"-> {str(gekregen):34} {k['reden']}")
    if not ok:
        FOUTEN.append(f"{naam} / {slug}.{veld}: kreeg {gekregen!r}, verwachtte {verwacht!r}")


# ---------------------------------------------------------------------------
# CO2 weegt zwaarder dan comfort, en het advies kijkt naar de ramen
# ---------------------------------------------------------------------------
wereld()
sensor("sensor.kantoor_temp", 26, "temperature", "Kantoor")
sensor("sensor.kantoor_co2", 1340, "carbon_dioxide", "Kantoor")
binair("binary_sensor.kantoor_raam", False, "window", "Kantoor", "Raam links")
check("CO2 boven 1200 is slecht", "kantoor", "status", "slecht")
check("lucht gaat voor temperatuur", "kantoor", "reden", "CO₂ 1340 ppm")
check("er is een raam, dus zet het open", "kantoor", "advies", "zet een raam open")

wereld()
sensor("sensor.kantoor_co2", 1340, "carbon_dioxide", "Kantoor")
binair("binary_sensor.kantoor_raam", True, "window", "Kantoor", "Raam links")
check("raam staat al open", "kantoor", "advies", "raam staat al open, even geduld")
check("open contact wordt geteld", "kantoor", "contacten.open", 1)

# ---------------------------------------------------------------------------
# Dezelfde meting, ander soort ruimte, ander oordeel
# ---------------------------------------------------------------------------
wereld()
sensor("sensor.slaapkamer_temp", 17, "temperature", "Slaapkamer")
sensor("sensor.woonkamer_temp", 17, "temperature", "Woonkamer")
check("17 graden is prima in een slaapkamer", "slaapkamer", "status", "goed")
check("17 graden is fris in de woonkamer", "woonkamer", "status", "let op")

wereld()
sensor("sensor.badkamer_rv", 72, "humidity", "Badkamer")
sensor("sensor.woonkamer_rv", 72, "humidity", "Woonkamer")
check("badkamer mag vochtig zijn", "badkamer", "status", "goed")
check("woonkamer van 72% is te vochtig", "woonkamer", "status", "let op")

wereld()
sensor("sensor.garage_temp", 3, "temperature", "Garage")
sensor("sensor.woonkamer_temp", 3, "temperature", "Woonkamer")
check("3 graden in de garage: bijna vorst", "garage", "status", "let op")
check("3 graden in de woonkamer: mis", "woonkamer", "status", "slecht")

# ---------------------------------------------------------------------------
# Warm, met en zonder koelte buiten: het advies moet meebewegen
# ---------------------------------------------------------------------------
wereld(**{"sensor.knmi_temperatuur": "19"})
sensor("sensor.woonkamer_temp", 26, "temperature", "Woonkamer")
check("warm binnen, koeler buiten", "woonkamer", "advies", "buiten is 19°, spuien kan")

wereld(**{"sensor.knmi_temperatuur": "33"})
sensor("sensor.woonkamer_temp", 26, "temperature", "Woonkamer")
check("warm binnen, heter buiten", "woonkamer", "advies", "zonwering dicht houden")

# ---------------------------------------------------------------------------
# Gaten zichtbaar maken: geen sensor is iets anders dan geen oordeel
# ---------------------------------------------------------------------------
wereld()
check("kamer zonder sensoren", "keuken", "status", "geen meting")
check("en dat wordt ook zo genoemd", "keuken", "reden", "geen sensoren in deze ruimte")

wereld()
sensor("sensor.voortuin_lux", 12000, "illuminance", "Voortuin")
check("buiten wordt gemeten", "voortuin", "aantal_metingen", 1)
check("maar niet beoordeeld", "voortuin", "reden", "buitenwaarden, niet beoordeeld")

# ---------------------------------------------------------------------------
# Een kapotte sensor mag de kamer niet meenemen
# ---------------------------------------------------------------------------
wereld(**{"sensor.woonkamer_woonkamer_multisensor_temperatuur": "unavailable"})
STATES["sensor.woonkamer_woonkamer_multisensor_temperatuur.device_class"] = "temperature"
AREAS.setdefault("Woonkamer", []).append("sensor.woonkamer_woonkamer_multisensor_temperatuur")
sensor("sensor.woonkamer_reserve_temp", 21, "temperature", "Woonkamer")
check("valt terug op de tweede thermometer", "woonkamer", "status", "goed")

# ---------------------------------------------------------------------------
# Verouderde meting: wel tonen, maar gemerkt - en niet vlak na een herstart
# ---------------------------------------------------------------------------
wereld()
sensor("sensor.zolder_temp", 22, "temperature", "Zolder", minuten=300)
check("5 uur niets gehoord", "zolder", "metingen.temp.oud", True)

wereld(**{"sensor.home_assistant_gestart": (NOW - dt.timedelta(minutes=20)).isoformat()})
sensor("sensor.zolder_temp", 22, "temperature", "Zolder", minuten=300)
check("vlak na herstart telt leeftijd niet", "zolder", "metingen.temp.oud", False)

# ---------------------------------------------------------------------------
# Een apparaat dat zichzelf meet is geen kamermeting
#
# Dit ging op 2026-08-03 op het dashboard mis: zigbee2mqtt geeft bijna elk
# apparaat een `device_temperature` met device_class temperature, en die won van
# de echte thermometer. Het halve huis stond op 27 tot 40 graden terwijl het
# buiten 22 was.
# ---------------------------------------------------------------------------
wereld()
sensor("sensor.kantoor_stekker_apparaattemperatuur", 38, "temperature", "Kantoor")
sensor("sensor.kantoor_kantoor_temperatuur_temperatuur", 22.4, "temperature", "Kantoor")
check("printplaat telt niet mee", "kantoor", "metingen.temp.w", 22.4)
check("en de kamer is dus gewoon goed", "kantoor", "status", "goed")

# De volgorde uit de registry is willekeurig, dus de echte thermometer mag niet
# afhangen van wie er toevallig eerst staat.
wereld()
sensor("sensor.badkamer_badkamer_temperatuur_temperatuur", 23.1, "temperature", "Badkamer")
sensor("sensor.badkamer_iets_anders", 31, "temperature", "Badkamer")
check("voorkeur wint van volgorde", "badkamer", "metingen.temp.w", 23.1)

wereld()
sensor("sensor.woonkamer_aquarium_temp", 26, "temperature", "Woonkamer")
check("aquarium is de kamer niet", "woonkamer", "aantal_metingen", 0)
check("en dat is geen meting", "woonkamer", "status", "geen meting")

# Een ruimte met alleen een lichtsensor in de bewegingsmelder is geen storing.
wereld()
sensor("sensor.toilet_beweging_lux", 53, "illuminance", "Toilet")
check("alleen licht", "toilet", "reden", "alleen licht, geen thermometer")

# ---------------------------------------------------------------------------
# Beweging
# ---------------------------------------------------------------------------
wereld()
binair("binary_sensor.toilet_beweging_occupancy", True, "occupancy", "Toilet")
check("beweging nu", "toilet", "beweging.actief", True)

wereld()
binair("binary_sensor.toilet_beweging_occupancy", False, "occupancy", "Toilet", minuten=42)
check("42 minuten geleden", "toilet", "beweging.minuten", 42)

# Zigbee2mqtt zet niet overal een device_class; de naamgeving van dit huis is
# het vangnet. Zonder deze regel zou de halve begane grond "geen melder" tonen.
wereld()
binair("binary_sensor.entree_beweging_occupancy", True, None, "Entree")
check("herkend op naam, zonder device_class", "entree", "beweging.gemeten", True)

# ---------------------------------------------------------------------------
print()
if FOUTEN:
    print(f"{len(FOUTEN)} FOUT(EN):")
    for f in FOUTEN:
        print("  -", f)
    raise SystemExit(1)
print("Alle scenario's kloppen.")
