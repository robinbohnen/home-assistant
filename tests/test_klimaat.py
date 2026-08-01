"""Offline test van custom_templates/klimaat.jinja met nagebootste HA-functies.

Draaien:  python3 -m venv .venv && .venv/bin/pip install jinja2
          .venv/bin/python tests/test_klimaat.py

De stubs hieronder doen states/state_attr/is_state/today_at/now en de
float/to_json/from_json-filters na, zodat de beslistabel te testen is zonder
Home Assistant te herstarten.
"""
import json
import re
import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATES = {}
NOW = dt.datetime(2026, 8, 1, 14, 0, 0)


def ha_states(eid):
    v = STATES.get(eid, "unknown")
    return v if isinstance(v, str) else str(v)


def ha_state_attr(eid, attr):
    return STATES.get(f"{eid}.{attr}")


def ha_is_state(eid, val):
    return ha_states(eid) == val


def ha_today_at(t="00:00"):
    parts = [int(p) for p in t.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return NOW.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


env = Environment(loader=FileSystemLoader(f"{CONFIG}/custom_templates"))
env.filters["float"] = f_float
env.filters["to_json"] = lambda v, **k: json.dumps(v)
env.filters["from_json"] = json.loads
env.globals.update(states=ha_states, state_attr=ha_state_attr, is_state=ha_is_state,
                   today_at=ha_today_at, now=lambda: NOW)

MOD = env.get_template("klimaat.jinja").module


def advies(zone):
    return json.loads(MOD.advies(zone).strip())


def scenario(naam, tijd, **kw):
    """Zet een basiswereld neer en overschrijf per scenario."""
    global NOW
    NOW = dt.datetime(2026, 8, 1, *[int(x) for x in tijd.split(":")])
    STATES.clear()
    STATES.update({
        "input_select.klimaat_regime": "Neutraal",
        "input_number.klimaat_kamer_warm": "22",
        "input_number.klimaat_hittedag_vanaf": "28",
        "input_number.klimaat_verwachte_max": "20",
        "input_number.klimaat_spui_delta": "1",
        "input_number.klimaat_kier_positie": "15",
        "input_boolean.klimaat_nachtspui": "on",
        "input_boolean.klimaatregie_actief": "on",
        "sensor.knmi_temperatuur": "18",
        "group.all_adults": "home",
        "binary_sensor.knmi_waarschuwing": "off",
        "sun.sun.elevation": 40.0,
        "binary_sensor.zon_op_voorgevel": "off",
        "binary_sensor.zon_op_zijgevel": "off",
        "binary_sensor.zon_op_achtergevel": "off",
        "binary_sensor.zon_richting_voorgevel": "off",
        "binary_sensor.zon_richting_zijgevel": "off",
        "binary_sensor.zon_richting_achtergevel": "off",
        "climate.airco_zolder": "off",
        "climate.airco_woonkamer": "off",
        # kamertemperaturen
        "sensor.woonkamer_temperatuur": "20",
        "sensor.kantoor_kantoor_temperatuur_temperatuur": "20",
        "sensor.badkamer_badkamer_temperatuur_temperatuur": "20",
        "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur": "20",
        "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "20",
        "sensor.slaapkamer_mini_temperatuur_temperature": "20",
    })
    for z in json.loads(MOD.zone_lijst()):
        STATES[f"input_boolean.zonwering_handmatig_{z}"] = "off"
        STATES[f"timer.override_{z}"] = "idle"
    STATES.update(kw)
    return naam


FOUTEN = []


def check(naam, zone, verwacht_advies, verwacht_uitvoeren=None):
    a = advies(zone)
    ok = a["advies"] == verwacht_advies
    if verwacht_uitvoeren is not None:
        ok = ok and a["uitvoeren"] == verwacht_uitvoeren
    print(f"{'PASS' if ok else 'FAIL'}  {naam:52} {zone:15} -> {a['advies']:6} "
          f"pos={a['positie']:4} uitvoeren={str(a['uitvoeren']):5}  {a['reden']}")
    if not ok:
        FOUTEN.append(f"{naam} / {zone}: kreeg {a['advies']}, verwachtte {verwacht_advies}")


# --- zomer, zon op de voorgevel -------------------------------------------
scenario("hete dag, zon op voorgevel", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("hete dag, zon voor", "kantoor_links", "dicht")
check("hete dag, zon voor", "keuken_screens", "dicht")
# Het kantoor heeft zelf een voorgevelraam, dus dat rolluik gaat mee dicht.
check("kantoor ligt ook op de voorgevel", "kantoor_rechts", "dicht")
# De achtergevel blijft open zolang de zon daar niet naartoe draait; anders
# zit je op elke warme dag de hele dag in het donker.
check("hete dag, achterzijde blijft licht", "badkamer", "open")

# --- preventief: zon draait naar de achtergevel, schijnt er nog niet --------
scenario("hittedag, zon draait naar achteren", "16:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("preventief dimmen voor de zon er is", "badkamer", "kier")
check("voorgevel is klaar, weer open", "kantoor_links", "open")

# --- zomer, niemand thuis --------------------------------------------------
scenario("hete dag, niemand thuis", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "group.all_adults": "not_home",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("niemand thuis op hittedag", "badkamer", "dicht")

# --- zomer, gewone koeldag, kamer koel ------------------------------------
scenario("koeldag, geen zon, kamer koel", "10:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "24"})
check("koeldag, schaduwzijde koel", "kantoor_rechts", "open")

# --- winter ----------------------------------------------------------------
scenario("winterdag met zon", "12:00",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "6",
            "sensor.knmi_temperatuur": "3",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("winter: zon binnenhalen", "kantoor_links", "open")
check("winter: screens moeten in bij vorst", "keuken_screens", "open")

scenario("winteravond", "19:30",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "6",
            "sun.sun.elevation": -12.0})
check("winter: isolatie na zonsondergang", "kantoor_links", "dicht")
check("winter: kind slaapt", "slaapkamer_logan", "dicht")

# --- nacht -----------------------------------------------------------------
scenario("zomernacht, buiten flink koeler", "21:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sun.sun.elevation": -6.0,
            "sensor.knmi_temperatuur": "19",
            "sensor.kantoor_kantoor_temperatuur_temperatuur": "25"})
check("nachtspui kantoor", "kantoor_rechts", "kier")
check("kind slaapt op hittedag -> kier", "slaapkamer_logan", "kier")

scenario("zomernacht binnen stille uren, warme kamer", "23:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sun.sun.elevation": -20.0,
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur": "25",
            "sensor.badkamer_badkamer_temperatuur_temperatuur": "20"})
check("stille uren: spuien mag nog wel", "slaapkamer", "kier", True)
check("stille uren: koele kamer blijft met rust", "badkamer", "rust", False)

scenario("nacht, nachtspui uit", "23:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_boolean.klimaat_nachtspui": "off",
            "input_number.klimaat_verwachte_max": "31",
            "sun.sun.elevation": -20.0,
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur": "25"})
check("nachtspui uit", "slaapkamer", "rust", False)

# --- airco koelt -----------------------------------------------------------
scenario("airco koelt, geen zon op de gevel", "11:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "26",
            "climate.airco_zolder": "cool"})
check("airco koelt: niet de straat koelen", "badkamer", "kier")
check("airco woonkamer staat uit", "keuken_screens", "open")

scenario("airco verwarmt in de winter", "11:00",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "5",
            "sensor.knmi_temperatuur": "2",
            "climate.airco_zolder": "heat",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("verwarmen: zon mag gewoon naar binnen", "badkamer", "open")

# --- screens veiligheid ----------------------------------------------------
scenario("storm op een hete dag", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("storm: screen in", "keuken_screens", "open")
check("storm: rolluik blijft gewoon dicht", "kantoor_links", "dicht")

# --- blokkades -------------------------------------------------------------
scenario("handbediening actief", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on",
            "timer.override_kantoor_links": "active"})
check("handbediening blokkeert", "kantoor_links", "dicht", False)

scenario("klimaatregie uit", "14:00",
         **{"input_boolean.klimaatregie_actief": "off",
            "input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "binary_sensor.zon_op_voorgevel": "on"})
check("master uit", "kantoor_links", "dicht", False)

# --- ontbrekende sensor ----------------------------------------------------
scenario("temperatuursensor weg", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "24",
            "sensor.kantoor_kantoor_temperatuur_temperatuur": "unavailable"})
check("kapotte sensor mag niet ontploffen", "kantoor_links", "open")

# --- drie gevels: middagzon op de zijgevel ---------------------------------
scenario("hete middag, zon op de zijgevel", "13:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sensor.knmi_temperatuur": "29",
            "binary_sensor.zon_op_zijgevel": "on",
            "binary_sensor.zon_richting_zijgevel": "on",
            # zon op ~180 graden: de achtergevel (260) valt al binnen 85 graden
            "binary_sensor.zon_richting_achtergevel": "on"})
check("zijgevel: kantoor dicht", "kantoor_links", "dicht")
check("zijgevel: keuken screens dicht", "keuken_screens", "dicht")
check("zijgevel: Emma ligt er ook aan", "slaapkamer_emma", "dicht")
check("achter krijgt de zon zo, dus preventief", "badkamer", "kier")
check("voorgevel is klaar, Logan mag open", "slaapkamer_logan", "open")

# --- avondzon op de achtergevel -------------------------------------------
scenario("avondzon achter", "18:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sensor.knmi_temperatuur": "28",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("achtergevel: slaapkamer dicht", "slaapkamer", "dicht")
check("achtergevel: Emma ligt er ook aan", "slaapkamer_emma", "dicht")
check("voor- en zijgevel zijn klaar, mag open", "slaapkamer_logan", "open")
check("kantoor krijgt geen zon meer", "kantoor_links", "open")

# --- consistentiecheck: slug == entity_id dat HA van de sensornaam maakt -----
# Home Assistant leidt het entity_id van een template-sensor af uit de NAAM,
# niet uit unique_id. Loopt dat uit de pas met de zoneslug, dan slaat de
# uitvoerder die zone stilzwijgend over. Precies dat ging een keer mis met
# 'maxi' vs 'slaapkamer_logan'.
def slugify(naam):
    uit = "".join(c.lower() if c.isalnum() else "_" for c in naam)
    while "__" in uit:
        uit = uit.replace("__", "_")
    return uit.strip("_")


pakket = open(f"{CONFIG}/packages/9 - Other/Klimaat Zonwering.yaml").read()
namen = re.findall(r'- name: "(Zonwering advies [^"]+)"', pakket)
verwacht = {f"sensor.zonwering_advies_{z}" for z in json.loads(MOD.zone_lijst())}
gevonden = {f"sensor.{slugify(n)}" for n in namen}
if verwacht == gevonden:
    print(f"PASS  {'slug komt overeen met entity_id van elke sensornaam':52} "
          f"({len(verwacht)} zones)")
else:
    print("FAIL  slug en sensornaam lopen uit de pas")
    FOUTEN.append(f"zones zonder sensor: {verwacht - gevonden}; "
                  f"sensoren zonder zone: {gevonden - verwacht}")

# Ook de helpers volgen de slug.
for domein, prefix in [("timer", "override_"),
                       ("input_boolean", "zonwering_handmatig_")]:
    ontbreekt = [z for z in json.loads(MOD.zone_lijst())
                 if f"{prefix}{z}:" not in pakket]
    if ontbreekt:
        print(f"FAIL  {domein}.{prefix}<slug> ontbreekt voor {ontbreekt}")
        FOUTEN.append(f"{domein}: {ontbreekt}")
    else:
        print(f"PASS  {domein + '.' + prefix + '<slug> bestaat voor elke zone':52}")

print()
if FOUTEN:
    print(f"{len(FOUTEN)} FOUT(EN):")
    for f in FOUTEN:
        print("  -", f)
    raise SystemExit(1)
print("Alle scenario's zoals bedoeld.")
