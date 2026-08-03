"""Offline test van custom_templates/kamers.jinja met nagebootste HA-functies.

Draaien:  python3 -m venv .venv && .venv/bin/pip install jinja2
          .venv/bin/python tests/test_kamers.py

Net als test_klimaat.py doen de stubs hieronder de Home Assistant-functies na
zodat de grenzen te testen zijn zonder te herstarten.

Sinds 2026-08-03 meet een kamer alleen nog wat in de tabel in kamers.jinja is
AANGEWEZEN (het apparaat achter `klimaat`, plus wat in `voorkeur`/`extra`
staat). De area wordt alleen nog gebruikt voor beweging, ramen en deuren. De
tests hieronder gebruiken daarom de echte entity-id's uit die tabel: een sensor
met de juiste device_class in de juiste area is niet meer genoeg, en dat is
precies wat een paar van deze scenario's bewaken.
"""
import json
import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATES = {}
AREAS = {}
LEEFTIJD = {}  # entity_id -> minuten geleden veranderd
DEVICES = {}   # entity_id -> device_id
NOW = dt.datetime(2026, 8, 3, 14, 0, 0)

# De aangewezen thermometers uit KAMERS in kamers.jinja. Wijzigt die tabel, dan
# wijzigt deze mee - de tests draaien tegen de echte koppeling, niet tegen een
# eigen fantasie ervan.
ANKER = {
    "woonkamer": "sensor.woonkamer_woonkamer_multisensor_temperatuur",
    "speelkamer": "sensor.speelkamer_speelkamer_temperatuur_temperatuur",
    "garage": "sensor.garage_garage_temperatuur_temperatuur",
    "meterkast": "sensor.meterkast_temperatuur_temperature",
    "slaapkamer": "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur",
    "slaapkamer_logan": "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur",
    "badkamer": "sensor.badkamer_badkamer_temperatuur_temperatuur",
    "kantoor": "sensor.kantoor_kantoor_temperatuur_temperatuur",
    "slaapkamer_emma": "sensor.slaapkamer_emma_slaapkamer_mini_temperatuur_temperatuur",
    "schuur": "sensor.achtertuin_schuur_temperatuur_temperature",
}


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


def ha_device_id(entity_id):
    return DEVICES.get(entity_id)


def ha_device_entities(device):
    return [e for e, d in DEVICES.items() if d == device]


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
                   area_entities=ha_area_entities, device_id=ha_device_id,
                   device_entities=ha_device_entities, now=lambda: NOW)

MOD = env.get_template("kamers.jinja").module


def kamers():
    return {k["slug"]: k for k in json.loads(MOD.kamers_json().strip())["kamers"]}


def ongekoppeld():
    return json.loads(MOD.ongekoppeld_json().strip())["sensoren"]


# ---------------------------------------------------------------------------
# Wereldopbouw
# ---------------------------------------------------------------------------

def sensor(eid, waarde, device_class, area=None, naam=None, minuten=0, apparaat=None):
    """Een sensor die bestaat. `area` is alleen nog decor voor meetsensoren."""
    STATES[eid] = str(waarde)
    STATES[f"{eid}.device_class"] = device_class
    STATES[f"{eid}.friendly_name"] = naam or eid
    LEEFTIJD[eid] = minuten
    if apparaat:
        DEVICES[eid] = apparaat
    if area:
        AREAS.setdefault(area, []).append(eid)


def meet(slug, waarde, device_class="temperature", **kw):
    """De aangewezen thermometer van een kamer, of iets aan hetzelfde apparaat.

    Voor een tweede meetwaarde (RV, CO2) geef je hetzelfde `apparaat` mee als de
    thermometer; zo komt hij via `device_entities()` mee, precies zoals in huis.
    """
    eid = kw.pop("eid", None) or ANKER[slug]
    sensor(eid, waarde, device_class, **kw)


def binair(eid, aan, device_class, area, naam=None, minuten=0, apparaat=None):
    STATES[eid] = "on" if aan else "off"
    STATES[f"{eid}.device_class"] = device_class
    STATES[f"{eid}.friendly_name"] = naam or eid
    LEEFTIJD[eid] = minuten
    if apparaat:
        DEVICES[eid] = apparaat
    AREAS.setdefault(area, []).append(eid)


def wereld(**kw):
    """Basiswereld: HA draait al een dag, buiten is 21 graden."""
    STATES.clear()
    AREAS.clear()
    LEEFTIJD.clear()
    DEVICES.clear()
    STATES.update({
        "sensor.knmi_temperatuur": "21",
        # De achtertuin leest deze sensor via `extra`, en dat werkt alleen als
        # hij een device_class heeft - hand-aangewezen entiteiten worden op
        # device_class ingedeeld, net als de rest.
        "sensor.knmi_temperatuur.device_class": "temperature",
        "sensor.home_assistant_gestart": (NOW - dt.timedelta(days=1)).isoformat(),
    })
    STATES.update(kw)


FOUTEN = []


def gelijk(naam, gekregen, verwacht):
    """Voor wat niet uit `kamers()` komt, zoals de onderhoudslijst."""
    ok = gekregen == verwacht
    print(f"{'PASS' if ok else 'FAIL'}  {naam:52} {'':28} -> {gekregen}")
    if not ok:
        FOUTEN.append(f"{naam}: kreeg {gekregen!r}, verwachtte {verwacht!r}")


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
# Alleen wat is aangewezen telt mee
#
# Dit is de kern van de omzetting van 2026-08-03. Alle drie de scenario's
# hieronder gaven vóór die datum een fout getal op de tegel, en alle drie
# zagen ze er op het dashboard volkomen normaal uit.
# ---------------------------------------------------------------------------

# 1. De spa. De achtertuin heeft geen thermometer; er stond een climate-entiteit
#    in de area en die werd de "buitentemperatuur" - 38 graden in de tuin.
wereld()
STATES["climate.intex_purespa.current_temperature"] = 38
AREAS.setdefault("Achtertuin", []).append("climate.intex_purespa")
check("de spa is de achtertuin niet", "achtertuin", "metingen.temp.id",
      "sensor.knmi_temperatuur")
check("en KNMI staat er wel", "achtertuin", "metingen.temp.w", 21.0)
check("buiten wordt niet beoordeeld", "achtertuin", "reden",
      "buitenwaarden, niet beoordeeld")

# 2. Een willekeurige sensor met de juiste device_class in de juiste area komt
#    er niet meer in. Vroeger hield een uitsluitlijst van veertig patronen dit
#    tegen; wat er niet op stond werd stilzwijgend een kamermeting.
wereld()
sensor("sensor.keuken_koelkast_temp", 4, "temperature", "Keuken")
sensor("sensor.keuken_espresso_temp", 93, "temperature", "Keuken")
sensor("sensor.keuken_zomaar_iets", 31, "temperature", "Keuken")
check("niet aangewezen telt niet mee", "keuken", "aantal_metingen", 0)
check("en dat wordt zo genoemd", "keuken", "reden", "geen sensor gekoppeld")

# 3. De printplaat van het aangewezen apparaat zelf. Die hangt aan hetzelfde
#    device en is dus het enige dat nog uitgesloten moet worden.
wereld()
sensor("sensor.kantoor_kantoor_temperatuur_device_temperature", 39, "temperature",
       apparaat="dev_kantoor")
meet("kantoor", 22.8, apparaat="dev_kantoor")
check("eigen printplaat telt niet mee", "kantoor", "metingen.temp.w", 22.8)
check("en de kamer is dus gewoon goed", "kantoor", "status", "goed")

# ---------------------------------------------------------------------------
# ...maar wat er niet in zit moet je wél kunnen zien
#
# Dit is de tegenhanger van hierboven en de reden dat aanwijzen mag: een sensor
# die nergens gekoppeld is verdwijnt niet stilletjes, hij komt op de
# onderhoudslijst onderaan het dashboard.
# ---------------------------------------------------------------------------
wereld()
meet("badkamer", 22.4, apparaat="dev_bad", area="Badkamer")
meet("badkamer", 55, "humidity", apparaat="dev_bad", area="Badkamer",
     eid="sensor.badkamer_badkamer_temperatuur_luchtvochtigheid")
sensor("sensor.badkamer_vloer_temperatuur", 24, "temperature", "Badkamer",
       "Vloerverwarming badkamer")
sensor("sensor.badkamer_raam_device_temperature", 31, "temperature", "Badkamer")
sensor("sensor.badkamer_raam_batterij", 88, "battery", "Badkamer")
los = ongekoppeld()
# De vloersensor is de enige die overblijft: de twee van het aangewezen apparaat
# zitten er al in, de printplaat telt niet mee en een batterijpercentage is geen
# meetwaarde voor dit overzicht.
gelijk("niet-gekoppelde meetsensor wordt gemeld",
       [s["id"] for s in los], ["sensor.badkamer_vloer_temperatuur"])
gelijk("en met kamer erbij", [s["kamer"] for s in los], ["Badkamer"])

# ---------------------------------------------------------------------------
# Eén apparaat levert meerdere meetwaarden
# ---------------------------------------------------------------------------
wereld()
meet("slaapkamer_logan", 23.5, apparaat="dev_melder")
meet("slaapkamer_logan", 50.37, "humidity", apparaat="dev_melder",
     eid="sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_luchtvochtigheid")
# 23,5° valt boven de slaapband (goed tot 21°) maar onder de alarmgrens.
check("warm voor een slaapkamer, niet alarmerend", "slaapkamer_logan", "status", "let op")
# De luchtvochtigheid staat nergens in de tabel; hij komt mee omdat hij aan
# hetzelfde apparaat hangt als de aangewezen thermometer.
check("zelfde apparaat levert ook de RV", "slaapkamer_logan", "metingen.rv.w", 50.37)
check("en die bron klopt", "slaapkamer_logan", "metingen.rv.id",
      "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_luchtvochtigheid")

# ---------------------------------------------------------------------------
# CO2 weegt zwaarder dan comfort, en het advies kijkt naar de ramen
# ---------------------------------------------------------------------------
wereld()
meet("kantoor", 26, apparaat="dev_kantoor")
meet("kantoor", 1340, "carbon_dioxide", apparaat="dev_kantoor",
     eid="sensor.kantoor_co2")
binair("binary_sensor.kantoor_raam", False, "window", "Kantoor", "Raam links")
check("CO2 boven 1200 is slecht", "kantoor", "status", "slecht")
check("lucht gaat voor temperatuur", "kantoor", "reden", "CO₂ 1340 ppm")
check("er is een raam, dus zet het open", "kantoor", "advies", "zet een raam open")

wereld()
meet("kantoor", 1340, "carbon_dioxide")
binair("binary_sensor.kantoor_raam", True, "window", "Kantoor", "Raam links")
check("raam staat al open", "kantoor", "advies", "raam staat al open, even geduld")
check("open contact wordt geteld", "kantoor", "contacten.open", 1)

# ---------------------------------------------------------------------------
# Dezelfde meting, ander soort ruimte, ander oordeel
# ---------------------------------------------------------------------------
wereld()
meet("slaapkamer", 17)
meet("woonkamer", 17)
check("17 graden is prima in een slaapkamer", "slaapkamer", "status", "goed")
check("17 graden is fris in de woonkamer", "woonkamer", "status", "let op")

wereld()
meet("badkamer", 72, "humidity")
meet("woonkamer", 72, "humidity")
check("badkamer mag vochtig zijn", "badkamer", "status", "goed")
check("woonkamer van 72% is te vochtig", "woonkamer", "status", "let op")

wereld()
meet("garage", 3)
meet("woonkamer", 3)
check("3 graden in de garage: bijna vorst", "garage", "status", "let op")
check("3 graden in de woonkamer: mis", "woonkamer", "status", "slecht")

# ---------------------------------------------------------------------------
# Warm, met en zonder koelte buiten: het advies moet meebewegen
# ---------------------------------------------------------------------------
wereld(**{"sensor.knmi_temperatuur": "19"})
meet("woonkamer", 26)
check("warm binnen, koeler buiten", "woonkamer", "advies", "buiten is 19°, spuien kan")

wereld(**{"sensor.knmi_temperatuur": "33"})
meet("woonkamer", 26)
check("warm binnen, heter buiten", "woonkamer", "advies", "zonwering dicht houden")

# ---------------------------------------------------------------------------
# Drie manieren om "geen cijfer" te zijn, en ze moeten uit elkaar te houden zijn
# ---------------------------------------------------------------------------
wereld()
check("keuken heeft geen thermometer", "keuken", "status", "geen meting")
check("en dat is geen storing", "keuken", "reden", "geen sensor gekoppeld")

# Wél aangewezen, maar de sensor doet het niet. Dat is een storing, en die zag
# je vroeger niet: dan nam een willekeurige andere sensor uit de area het over.
wereld()
meet("badkamer", "unavailable")
check("kapotte thermometer valt op", "badkamer", "reden", "sensor geeft niets door")
check("met iets om te doen", "badkamer", "advies", "batterij of verbinding controleren")

# Eén stukke meetwaarde neemt de rest van het apparaat niet mee: de RV van
# dezelfde melder blijft gewoon staan.
wereld()
meet("woonkamer", "unknown", apparaat="dev_multi")
meet("woonkamer", 45.5, "humidity", apparaat="dev_multi",
     eid="sensor.woonkamer_woonkamer_multisensor_luchtvochtigheid")
check("lege temperatuur telt niet als meting", "woonkamer", "metingen.temp.w", None)
check("maar de RV van hetzelfde apparaat wel", "woonkamer", "metingen.rv.w", 45.5)

# Alleen een lichtsensor is wél een sensor, maar geen oordeel.
wereld()
meet("woonkamer", 53, "illuminance")
check("alleen licht", "woonkamer", "reden", "alleen licht, geen thermometer")

# ---------------------------------------------------------------------------
# Verouderde meting: wel tonen, maar gemerkt - en niet vlak na een herstart
# ---------------------------------------------------------------------------
wereld()
meet("garage", 22, minuten=300)
check("5 uur niets gehoord", "garage", "metingen.temp.oud", True)

wereld(**{"sensor.home_assistant_gestart": (NOW - dt.timedelta(minutes=20)).isoformat()})
meet("garage", 22, minuten=300)
check("vlak na herstart telt leeftijd niet", "garage", "metingen.temp.oud", False)

# ---------------------------------------------------------------------------
# Beweging, ramen en deuren: die gaan nog wél per area
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

# Een deurcontact op de koelkast is geen keukendeur. Dat is het enige gat dat de
# area-aanpak nog heeft, en `negeer` is er het gereedschap voor - zodra er zo'n
# contact hangt hoort hij daar. Hier alleen getest dat contacten geteld worden.
wereld()
binair("binary_sensor.keuken_achterdeur_contact", True, "door", "Keuken", "Achterdeur")
check("open deur wordt geteld", "keuken", "contacten.open", 1)
check("en met naam", "keuken", "contacten.namen", ["Achterdeur"])

# ---------------------------------------------------------------------------
print()
if FOUTEN:
    print(f"{len(FOUTEN)} FOUT(EN):")
    for f in FOUTEN:
        print("  -", f)
    raise SystemExit(1)
print("Alle scenario's kloppen.")
