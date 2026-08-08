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


def ha_has_value(eid):
    return ha_states(eid) not in ("unknown", "unavailable", "")


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
                   has_value=ha_has_value, today_at=ha_today_at, now=lambda: NOW)

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
        # Basiswereld = huis is wakker, zodat de bestaande scenario's over de
        # dag-logica gaan. De wakker-gate heeft eigen scenario's onderaan.
        "input_boolean.klimaat_wakker": "on",
        "sensor.knmi_temperatuur": "18",
        "weather.knmi_thuis.wind_speed": 12.0,
        "input_number.klimaat_screen_max_wind": "45",
        "sensor.neerslag_komende_30_minuten": "0",
        "input_number.klimaat_screen_max_regen": "0.1",
        "group.all_adults": "home",
        "binary_sensor.knmi_waarschuwing": "off",
        "binary_sensor.knmi_waarschuwing.description":
            "Er zijn momenteel geen waarschuwingen van kracht.",
        "sun.sun.elevation": 40.0,
        "binary_sensor.zon_op_voorgevel": "off",
        "binary_sensor.zon_op_zijgevel": "off",
        "binary_sensor.zon_op_achtergevel": "off",
        "binary_sensor.zon_richting_voorgevel": "off",
        "binary_sensor.zon_richting_zijgevel": "off",
        "binary_sensor.zon_richting_achtergevel": "off",
        "climate.airco_zolder": "off",
        "climate.airco_woonkamer": "off",
        # Basiswereld voor de binnenzonwering: ramen dicht en de keukenscreens
        # ingetrokken (er is in de basiswereld ook geen zon).
        "binary_sensor.keuken_raam_groot_contact": "off",
        "binary_sensor.keuken_raam_klein_contact": "off",
        "cover.covers_kitchen_screens": "open",
        "alarm_control_panel.alarmo": "disarmed",
        # Begin van de naar-bed-routine (een uur voor lichten uit); de vroegste
        # (18:00) is vanaf wanneer de keukenrolgordijnen stil moeten blijven.
        "input_datetime.bedtime_maxi_1h_off": "19:00:00",
        "input_datetime.bedtime_mini_1h_off": "18:00:00",
        # kamertemperaturen
        "sensor.woonkamer_woonkamer_multisensor_temperatuur": "20",
        "sensor.kantoor_kantoor_temperatuur_temperatuur": "20",
        "sensor.badkamer_badkamer_temperatuur_temperatuur": "20",
        "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur": "20",
        "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "20",
        "sensor.slaapkamer_emma_slaapkamer_mini_temperatuur_temperatuur": "20",
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

# --- gevelsensor zonder waarde: adviseren mag, uitvoeren niet ---------------
# Op 2026-08-08 flikkerden de gevelsensoren tijdens een YAML-reload een paar
# seconden door `unavailable`. `is_state(..., 'on')` leest dat als "geen zon",
# waardoor het advies voor kantoor omsloeg van dicht (0%) naar kier (15%) en de
# rolgordijnen opengingen om 39 seconden later weer dicht te gaan. Het advies
# mag best omslaan - de macro kan met een halve wereld nu eenmaal niets beters -
# maar `uitvoeren` hoort dan false te zijn, zodat er niets beweegt.
scenario("gezonde wereld, zon op voorgevel", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("sensoren gezond, gewoon uitvoeren", "kantoor_links", "dicht", True)

scenario("reload: gevelsensor even unavailable", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "binary_sensor.zon_op_voorgevel": "unavailable",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("gevelsensor weg, zonwering blijft staan", "kantoor_links", "kier", False)
# Een zone op een andere gevel heeft er geen last van: die leest zijn eigen
# sensoren en die zijn nog gewoon in orde.
check("andere gevel blijft normaal werken", "badkamer", "open", True)

# Zelfde fout, andere bron. Bij de reload van 12:10 was niet de gevelsensor weg
# maar `group.all_adults`: `thuis` werd false, het advies luidde "niemand thuis
# op een warme dag" en het keukenrolgordijn ging omlaag. De eerste guard keek
# alleen naar de gevelsensoren en ving dit niet - vandaar dat de controle nu
# over alle bronnen gaat die bij een reload kunnen verdwijnen.
scenario("reload: group.all_adults even weg", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "group.all_adults": "unknown"})
check("thuis-groep weg, rolgordijn blijft staan", "keuken_rolgordijn_groot",
      "dicht", False)
# Ander advies (zonder zon op de voorgevel helpt een screen niet), maar het
# gaat hier om het vlaggetje: ook deze zone komt niet in beweging.
check("en de screens ook", "keuken_screens", "open", False)

# Een handbediening-timer die tijdens de reload verdwijnt mag een lopende
# override niet stilzwijgend opheffen; ook dan blijft de zone staan.
scenario("reload: override-timer even weg", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "timer.override_kantoor_links": "unavailable"})
check("override-timer weg, zone blijft staan", "kantoor_links", "open", False)

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
# Een kinderkamer gaat met bedtijd helemaal omlaag en blijft dat, ook op een
# hittedag: donker weegt hier zwaarder dan die paar graden.
check("kind slaapt op hittedag -> toch dicht", "slaapkamer_logan", "dicht")

scenario("zomernacht binnen stille uren, warme kamer", "23:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sun.sun.elevation": -20.0,
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur": "25",
            "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "25",
            "sensor.badkamer_badkamer_temperatuur_temperatuur": "20"})
check("stille uren: spuien mag nog wel", "slaapkamer", "kier", True)
check("stille uren: koele kamer blijft met rust", "badkamer", "rust", False)
# De spui-kier geldt niet in een kinderkamer: die is met bedtijd dichtgegaan en
# gaat er 's nachts niet alsnog een stukje uit.
check("kinderkamer spuit niet, blijft dicht", "slaapkamer_logan", "rust", False)

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
            "binary_sensor.knmi_waarschuwing.description":
                "Code geel: kans op zware windstoten.",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("storm: screen in", "keuken_screens", "open")
check("storm: rolluik blijft gewoon dicht", "kantoor_links", "dicht")

# De KNMI-sensor staat vaak op 'on' terwijl er niets is; alleen de tekst telt.
scenario("sensor staat aan, maar er is geen waarschuwing", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.knmi_waarschuwing.description":
                " Er zijn momenteel geen waarschuwingen van kracht.",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("loze waarschuwing blokkeert de screens niet", "keuken_screens", "dicht")

# Een hitteplan is geen reden om screens in te trekken - juist andersom.
scenario("hitteplan actief", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "29",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.knmi_waarschuwing.description":
                "Het Nationaal Hitteplan van het RIVM is actief voor het "
                "zuidoosten van het land. Vandaag is het tijdelijk minder warm.",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("hitteplan: screens juist omlaag", "keuken_screens", "dicht")

# ECHTE tekst van 3 augustus 2026. Hierin staat "ook onweersbuien brengen
# plaatselijk enige verkoeling", en 'onweer' zit in 'onweersbuien'. Daardoor
# telde dit hitteplan als stormalarm en gingen de screens in op een dag die
# naar de 37 graden liep. De omschrijving is een verhaal over het weer, geen
# onderwerp - vandaar dat de titel nu leidend is.
HITTEPLAN_3AUG = (
    "Het Nationaal Hitteplan van het RIVM is vanaf vandaag actief voor het hele "
    "land. In het zuidoosten is het aanhoudend warm. Tot en met dinsdag wordt "
    "het in het hele land zeer warm, met temperaturen tussen 29 en 36°C en "
    "hittekracht van 7-8. Maandag en dinsdag wordt het overal zeer warm. In de "
    "loop van de middag koelt het van het westen uit wat af en ook onweersbuien "
    "brengen plaatselijk enige verkoeling."
)
scenario("hitteplan met onweer in de tekst", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "37",
            "sensor.knmi_temperatuur": "30",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.knmi_waarschuwing.title": "Nationaal Hitteplan",
            "binary_sensor.knmi_waarschuwing.description": HITTEPLAN_3AUG,
            "binary_sensor.zon_richting_voorgevel": "on"})
check("hitteplan met onweer: screens blijven omlaag", "keuken_screens", "dicht")

# Zonder titel valt hij terug op de omschrijving; ook dan mag een hitteplan de
# screens niet intrekken.
scenario("hitteplan met onweer, geen titel", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "37",
            "sensor.knmi_temperatuur": "30",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.knmi_waarschuwing.description": HITTEPLAN_3AUG,
            "binary_sensor.zon_richting_voorgevel": "on"})
check("hitteplan zonder titel: nog steeds omlaag", "keuken_screens", "dicht")

# Een echte onweerswaarschuwing moet de screens wél intrekken.
scenario("echte onweerswaarschuwing", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.knmi_waarschuwing.title": "Code geel: onweer",
            "binary_sensor.knmi_waarschuwing.description":
                "Er trekken onweersbuien over het land met kans op hagel.",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("echt onweer: screen in", "keuken_screens", "open")

# Titel is leidend: staat daar niets over wind, dan telt een losse opmerking in
# de omschrijving niet mee.
scenario("gladheidswaarschuwing die wind noemt", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "binary_sensor.knmi_waarschuwing": "on",
            "binary_sensor.knmi_waarschuwing.title": "Code geel: gladheid",
            "binary_sensor.knmi_waarschuwing.description":
                "Door de wind kan de gevoelstemperatuur lager liggen.",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("gladheid is geen storm", "keuken_screens", "dicht")

# Harde wind uit de verwachting telt ook zonder KNMI-waarschuwing.
scenario("harde wind zonder waarschuwing", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "weather.knmi_thuis.wind_speed": 52.0,
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("wind boven de grens: screen in", "keuken_screens", "open")
check("rolluiken hebben geen last van wind", "kantoor_links", "dicht")

# Regen. Nat doek is net zo goed een reden om in te halen als wind, en het mag
# niet afhangen van of iemand op een melding tikt.
scenario("regen op komst terwijl de zon schijnt", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "sensor.neerslag_komende_30_minuten": "0.4",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("regen: screen in ondanks zon", "keuken_screens", "open")
check("rolluiken hebben geen last van regen", "kantoor_links", "dicht")

# De sensor rondt op 2 decimalen af, dus droog is exact 0. Een spoor onder de
# ingestelde grens mag de screens niet de hele zomer binnenhouden.
scenario("een spoortje regen onder de grens", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "sensor.neerslag_komende_30_minuten": "0.05",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("onder de regengrens blijft het screen omlaag", "keuken_screens", "dicht")

scenario("regensensor onbereikbaar", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "sensor.neerslag_komende_30_minuten": "unavailable",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("kapotte regensensor telt als droog", "keuken_screens", "dicht")

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
# De keukenscreens hangen aan de voorgevel en trekken zich niets aan van de
# zijgevel: die staat 's middags nog uren "aan" terwijl de zon voor de keuken
# allang weg is.
check("zijgevel: keuken screens juist omhoog", "keuken_screens", "open")
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

# --- screens werken alleen tegen directe zon -------------------------------
# Een screen houdt straling tegen, geen warmte die er al is. Hiervoor erfde hij
# de uitkomst van de regime-tak en ging hij dus ook omlaag om redenen die niets
# met zon te maken hebben; daardoor bleef hij de hele warme avond hangen.
scenario("warme avond, zon van de gevel af", "20:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sensor.knmi_temperatuur": "26",
            "sensor.woonkamer_woonkamer_multisensor_temperatuur": "25",
            "sun.sun.elevation": 5.0})
check("screen omhoog zodra de zon weg is", "keuken_screens", "open")

scenario("warme kamer, maar geen zon", "15:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "26",
            "sensor.woonkamer_woonkamer_multisensor_temperatuur": "25",
            "sensor.kantoor_kantoor_temperatuur_temperatuur": "25"})
check("warme kamer alleen is geen reden", "keuken_screens", "open")
# Het rolluik dempt wél licht en gaat daarom wel op een kier: dat is precies
# het verschil tussen een screen en een rolluik.
check("rolluik dempt wel bij een warme kamer", "kantoor_links", "kier")

scenario("niemand thuis op een hete dag, zon elders", "11:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "group.all_adults": "not_home",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("screen dicht hoeft niet zonder zon op zijn gevel", "keuken_screens", "open")
check("het rolluik aan de zonzijde gaat wel dicht", "badkamer", "dicht")

scenario("airco koelt, geen zon op de keukengevel", "11:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "26",
            "climate.airco_woonkamer": "cool"})
check("airco is geen reden voor een screen", "keuken_screens", "open")

scenario("zon staat er wel echt op", "12:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "29",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("met zon gaat het screen gewoon omlaag", "keuken_screens", "dicht")

scenario("hittedag, zon draait naar de keukengevel", "09:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("preventief blijft overeind op een hittedag", "keuken_screens", "dicht")

# --- de keukenscreens volgen alleen de voorgevel ---------------------------
# Ze hangen voor de keukenramen aan de straatkant (oost). Stond de zijgevel er
# ook bij, dan bleven ze tot een uur of zes omlaag: die sensor telt tot een
# azimut van 255° en gebruikt daarbij het licht uit de achtertuin.
scenario("middag, zon staat inmiddels op zij en achter", "16:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sensor.knmi_temperatuur": "28",
            "sensor.woonkamer_woonkamer_multisensor_temperatuur": "25",
            "binary_sensor.zon_op_zijgevel": "on",
            "binary_sensor.zon_richting_zijgevel": "on",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("zon weg bij de voorgevel: screens omhoog", "keuken_screens", "open")
# Het zonnescherm hoort in diezelfde situatie juist uit te willen.
check("achtertuin krijgt de zon nu wel", "zonnescherm", "dicht")

# --- rolluiken blijven dicht tot het huis wakker is ------------------------
# STIL_TOT is 07:00, maar in de zomer staat de zon dan allang op. Zonder deze
# gate gingen de slaapkamerrolluiken om 07:00 omhoog terwijl er nog geslapen
# werd.
scenario("zomerochtend, nog niemand op", "08:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "27",
            "input_boolean.klimaat_wakker": "off"})
check("slaapkamer blijft staan", "slaapkamer", "rust", False)
check("badkamer blijft staan", "badkamer", "rust", False)
check("kinderkamer blijft staan", "slaapkamer_emma", "rust", False)
# Kantoor en keuken slapen niet en gaan gewoon hun gang.
check("kantoor trekt zich er niets van aan", "kantoor_links", "open")

scenario("zelfde ochtend, knop ingedrukt", "08:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "27",
            "input_boolean.klimaat_wakker": "on"})
check("na de knop mag het rolluik omhoog", "slaapkamer", "open")

scenario("niemand drukte, maar het is al laat", "10:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "27",
            "input_boolean.klimaat_wakker": "off"})
check("noodrem: na 10:00 toch omhoog", "slaapkamer", "open")

scenario("warme ochtend, nog niemand op, spuien mag", "08:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_slaapkamer_temperatuur_temperatuur": "25",
            "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "25",
            "sensor.slaapkamer_emma_slaapkamer_mini_temperatuur_temperatuur": "25",
            "input_boolean.klimaat_wakker": "off"})
check("ventileren mag wel, omhoog niet", "slaapkamer", "kier")
# ...maar niet in een kinderkamer. `kind_slaapt` liep tot 07:00, dus daarna
# gold de spui-uitzondering ook daar en gingen de rolluiken op 1 augustus 2026
# 's ochtends alsnog een stukje open terwijl de kinderen sliepen. Wat er staat
# blijft staan tot het huis wakker is: dicht blijft dicht, kier blijft kier.
check("kinderkamer ventileert niet mee (Logan)", "slaapkamer_logan", "rust", False)
check("kinderkamer ventileert niet mee (Emma)", "slaapkamer_emma", "rust", False)

scenario("zelfde warme ochtend, maar het huis is wakker", "08:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "25",
            "input_boolean.klimaat_wakker": "on"})
check("na het wakker-signaal mag de kinderkamer weer", "slaapkamer_logan", "kier")

scenario("warme ochtend, niemand drukte, na de noodrem", "10:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "25",
            "input_boolean.klimaat_wakker": "off"})
check("na 10:00 doet de kinderkamer weer mee", "slaapkamer_logan", "kier")

scenario("kinderkamer, nacht met warme kamer", "02:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "19",
            "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": "25",
            "sun.sun.elevation": -20.0,
            "input_boolean.klimaat_wakker": "off"})
check("blijft 's nachts gewoon dicht", "slaapkamer_logan", "rust", False)

scenario("winterochtend, nog donker", "07:30",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "6",
            "sun.sun.elevation": -8.0,
            "input_boolean.klimaat_wakker": "off"})
check("nog donker en nog niemand op", "slaapkamer", "rust", False)

# --- zonnescherm: omgekeerd bedrade cover ---------------------------------
# HA-stand `open` = uitgeschoven = zon tegenhouden. De beslistabel denkt in
# zonwerings-termen ('dicht' = zon buiten houden), dus `positie` moet precies
# omgekeerd zijn aan die van een gewoon rolluik. Een tekenfout hier zet het
# scherm uit tijdens een storm, dus dit wordt hard nagerekend.
def check_positie(naam, zone, verwacht_advies, verwacht_positie):
    a = advies(zone)
    ok = a["advies"] == verwacht_advies and a["positie"] == verwacht_positie
    print(f"{'PASS' if ok else 'FAIL'}  {naam:52} {zone:15} -> {a['advies']:6} "
          f"pos={a['positie']:4} uitvoeren={str(a['uitvoeren']):5}  {a['reden']}")
    if not ok:
        FOUTEN.append(f"{naam} / {zone}: kreeg {a['advies']}/{a['positie']}, "
                      f"verwachtte {verwacht_advies}/{verwacht_positie}")


scenario("middagzon op de achtergevel", "17:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "29",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
# 'dicht' = zon tegenhouden = scherm UIT = cover open = positie 100
check_positie("zon achter: scherm uitschuiven", "zonnescherm", "dicht", 100)

scenario("zon is van de achtergevel af", "11:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "29",
            "sensor.woonkamer_woonkamer_multisensor_temperatuur": "25",
            "binary_sensor.zon_op_voorgevel": "on"})
# geen zon achter -> scherm heeft geen functie -> intrekken -> positie 0
check_positie("geen zon achter: scherm intrekken", "zonnescherm", "open", 0)

scenario("storm terwijl de zon er vol op staat", "17:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on",
            "weather.knmi_thuis.wind_speed": 60.0})
# DE belangrijkste: harde wind moet het scherm INTREKKEN, dus positie 0.
check_positie("storm: scherm intrekken ondanks zon", "zonnescherm", "open", 0)

scenario("regen terwijl de zon er vol op staat", "17:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on",
            "sensor.neerslag_komende_30_minuten": "0.3"})
# Net als bij storm: regen moet het scherm INTREKKEN, dus positie 0.
check_positie("regen: scherm intrekken ondanks zon", "zonnescherm", "open", 0)

scenario("vorst met winterzon achter", "13:00",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "3",
            "sensor.knmi_temperatuur": "1",
            "binary_sensor.zon_op_achtergevel": "on"})
check_positie("vorst: scherm ingetrokken", "zonnescherm", "open", 0)

scenario("winterzon achter, geen vorst", "13:00",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "10",
            "sensor.knmi_temperatuur": "7",
            "binary_sensor.zon_op_achtergevel": "on"})
check_positie("winter: gratis warmte binnenlaten", "zonnescherm", "open", 0)

scenario("zomernacht", "23:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sun.sun.elevation": -12.0})
check_positie("nacht: scherm ingetrokken", "zonnescherm", "open", 0)

# Een gewoon rolluik in dezelfde situatie moet juist NIET omgekeerd zijn.
scenario("controle: rolluik blijft normaal", "17:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "29",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check_positie("rolluik: dicht is gewoon 0", "badkamer", "dicht", 0)

# --- het zonnescherm vraagt eerst -----------------------------------------
# Uitschuiven is een vraag, binnenhalen niet: op het intrekken bij wind, vorst
# of een weggedraaide zon mag niemand hoeven wachten. `vraagt` is het vlaggetje
# waar zowel de uitvoerder als de handbediening-herkenning op afgaat, dus een
# fout hier laat het scherm óf uit zichzelf uitrollen óf bij storm buiten staan.
def check_vraagt(naam, zone, verwacht):
    a = advies(zone)
    ok = a["vraagt"] == verwacht
    print(f"{'PASS' if ok else 'FAIL'}  {naam:52} {zone:15} -> {a['advies']:6} "
          f"vraagt={str(a['vraagt']):5} blokkade={a['blokkade'] or '-'}")
    if not ok:
        FOUTEN.append(f"{naam} / {zone}: vraagt={a['vraagt']}, verwachtte {verwacht}")


scenario("zon vol op de achtergevel", "17:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "29",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check_vraagt("uitschuiven gaat via een vraag", "zonnescherm", True)
check_vraagt("een gewoon screen vraagt niets", "keuken_screens", False)

scenario("zon van de achtergevel af", "11:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "29",
            "binary_sensor.zon_op_voorgevel": "on"})
check_vraagt("binnenhalen gebeurt zonder vragen", "zonnescherm", False)

scenario("storm terwijl het scherm uit staat", "17:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on",
            "weather.knmi_thuis.wind_speed": 60.0})
check_vraagt("bij storm niet eerst overleggen", "zonnescherm", False)

# --- binnenzonwering: de keukenrolgordijnen -------------------------------
# Een rolgordijn hangt aan de warme kant van het glas en haalt maar een fractie
# van wat het screen ervoor doet, terwijl hij het hele daglicht kost. Hij hoort
# dus NIET mee te lopen met de screens, maar bij te springen zodra die er niet
# kunnen staan.
scenario("zon op de keukengevel, screen staat gewoon omlaag", "10:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sensor.knmi_temperatuur": "26",
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on",
            "cover.covers_kitchen_screens": "closed"})
check("screen vangt de zon al op", "keuken_rolgordijn_groot", "open")
check("screen vangt de zon al op", "keuken_rolgordijn_klein", "open")

# DE reden om ze te koppelen: bij wind, regen of vorst gaan de screens in, en
# dan is het rolgordijn de enige zonwering die er nog is.
scenario("harde wind: screens ingetrokken terwijl de zon erop staat", "10:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "weather.knmi_thuis.wind_speed": 52.0,
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on",
            "cover.covers_kitchen_screens": "open"})
check("screen in bij wind", "keuken_screens", "open")
check("rolgordijn neemt het over", "keuken_rolgordijn_groot", "dicht")
check("rolgordijn neemt het over", "keuken_rolgordijn_klein", "dicht")

# Een openstaand raam gaat voor: daar rol je niets tegenaan. Per raam, want
# daarom zijn het twee zones en niet de groep.
scenario("zelfde wind, maar het grote raam staat open", "10:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "weather.knmi_thuis.wind_speed": 52.0,
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on",
            "cover.covers_kitchen_screens": "open",
            "binary_sensor.keuken_raam_groot_contact": "on"})
check("open raam blokkeert dit rolgordijn", "keuken_rolgordijn_groot", "rust", False)
check("het andere raam is dicht en gaat gewoon", "keuken_rolgordijn_klein", "dicht")

# Een onbereikbaar raamcontact telt als open: niet dichtrollen op een gok.
scenario("raamcontact onbereikbaar", "10:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "28",
            "weather.knmi_thuis.wind_speed": 52.0,
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on",
            "cover.covers_kitchen_screens": "open",
            "binary_sensor.keuken_raam_klein_contact": "unavailable"})
check("kapot contact telt als open raam", "keuken_rolgordijn_klein", "rust", False)

scenario("hittedag, niemand thuis, geen zon op de keukengevel", "15:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "group.all_adults": "not_home",
            "binary_sensor.zon_op_achtergevel": "on",
            "binary_sensor.zon_richting_achtergevel": "on"})
check("leeg huis op een hete dag: donker kost niets", "keuken_rolgordijn_groot", "dicht")
check("het screen zelf hoeft niet zonder zon", "keuken_screens", "open")

# Een leeg of afgesloten huis is óók van de inkijk-routine. `covers_lock_alarm_
# events` trekt de rolgordijnen dicht zodra het alarm scherp gaat; zonder deze
# rem haalde de uitvoerder ze op een milde dag binnen een kwartier weer omhoog.
scenario("alarm scherp op een milde dag", "14:00",
         **{"input_number.klimaat_verwachte_max": "18",
            "group.all_adults": "not_home",
            "alarm_control_panel.alarmo": "armed_away"})
check("alarm scherp: rolgordijn blijft staan", "keuken_rolgordijn_groot", "rust", False)
check("alarm scherp: en de andere ook", "keuken_rolgordijn_klein", "rust", False)

# Omlaag mag wél gewoon: dat is dezelfde richting als de inkijk-routine wil.
scenario("alarm scherp op een hete dag", "14:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "31",
            "sensor.knmi_temperatuur": "30",
            "group.all_adults": "not_home",
            "alarm_control_panel.alarmo": "armed_away"})
check("warmte mag hem wel omlaag sturen", "keuken_rolgordijn_groot", "dicht")

# Ook zonder alarm: is er niemand thuis, dan gaat er niets omhoog.
scenario("niemand thuis, alarm staat uit", "14:00",
         **{"input_number.klimaat_verwachte_max": "18",
            "group.all_adults": "not_home"})
check("leeg huis: geen rolgordijn omhoog", "keuken_rolgordijn_groot", "rust", False)

# Thuis met het alarm op 'thuis' overdag: dan hoort hij gewoon mee te doen...
scenario("alarm op thuis-stand, iedereen is er", "14:00",
         **{"input_number.klimaat_verwachte_max": "18",
            "alarm_control_panel.alarmo": "armed_home"})
check("armed_home telt ook als scherp", "keuken_rolgordijn_groot", "rust", False)

scenario("gewone dag, alarm uit, mensen thuis", "14:00",
         **{"input_number.klimaat_verwachte_max": "18"})
check("gewoon thuis: rolgordijn omhoog", "keuken_rolgordijn_groot", "open")

# Avond en nacht zijn van de inkijk-routine (kitchen_covers_close om
# zonsondergang -30 min). Zou de klimaatregie daar 'open' blijven adviseren,
# dan trok de uitvoerder de rolgordijnen een kwartier later weer omhoog.
scenario("zomeravond, tegen zonsondergang", "21:15",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sensor.woonkamer_woonkamer_multisensor_temperatuur": "25",
            "sun.sun.elevation": 3.0})
check("avond: rolgordijn is van de inkijk-routine", "keuken_rolgordijn_groot", "rust", False)

scenario("zomernacht", "02:00",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sun.sun.elevation": -20.0})
check("nacht: blijft staan waar hij staat", "keuken_rolgordijn_klein", "rust", False)

# In juni staat de zon om 20:00 nog ruim boven AVOND_ELEVATIE en de stille uren
# beginnen pas om 22:00. Daar zat een gat van een paar uur waarin dit ding op
# een warme avond alsnog omhoog werd gestuurd - precies tijdens het in slaap
# vallen. Vanaf het begin van de naar-bed-routine blijft hij nu staan; op
# datzelfde moment laat `kitchen_covers_close` hem zakken voor de avond.
zomeravond = {"input_select.klimaat_regime": "Koelen",
              "input_number.klimaat_verwachte_max": "30",
              "sensor.woonkamer_woonkamer_multisensor_temperatuur": "24",
              "sun.sun.elevation": 12.0}

scenario("zomeravond, kinderen gaan naar bed", "20:00", **zomeravond)
check("na bedtijd geen rolgordijn meer", "keuken_rolgordijn_groot", "rust", False)
check("na bedtijd geen rolgordijn meer", "keuken_rolgordijn_klein", "rust", False)
# De screens buiten hangen niet onder een kinderkamer en blijven gewoon meedoen.
check("de screens gaan wel gewoon door", "keuken_screens", "open")

# Vóór de naar-bed-routine is er niets aan de hand: dan mag hij gewoon bewegen.
scenario("zelfde avond, maar de kinderen zijn nog op", "17:30", **zomeravond)
check("voor bedtijd gewoon daglicht", "keuken_rolgordijn_groot", "open")

# Het venster hangt aan de bedtijd-helpers, niet aan een vast uur: schuift de
# bedtijd op, dan schuift de rust mee.
scenario("late bedtijd in het weekend", "20:00",
         **dict(zomeravond, **{"input_datetime.bedtime_maxi_1h_off": "21:00:00",
                               "input_datetime.bedtime_mini_1h_off": "20:30:00"}))
check("bedtijd later: mag nog bewegen", "keuken_rolgordijn_groot", "open")

# Zijn de helpers niet uit te lezen, dan geldt BEDTIJD_TERUGVAL (18:00). Stil
# blijven is hier de veilige kant.
scenario("bedtijd-helpers onbereikbaar", "20:00",
         **dict(zomeravond, **{"input_datetime.bedtime_maxi_1h_off": "unavailable",
                               "input_datetime.bedtime_mini_1h_off": "unknown"}))
check("terugval op 18:00", "keuken_rolgordijn_groot", "rust", False)

# Een helper die per ongeluk op een ochtenduur staat mag de zone niet de hele
# dag platleggen. Die wordt genegeerd, en de andere helper (19:00) telt gewoon -
# dus om 18:30 mag hij nog bewegen. Zou de terugval hier alsnog toeslaan, dan
# stond hij om 18:00 al stil.
scenario("bedtijd staat per ongeluk op de ochtend", "18:30",
         **dict(zomeravond, **{"input_datetime.bedtime_mini_1h_off": "07:30:00"}))
check("ochtendtijd telt niet als bedtijd", "keuken_rolgordijn_groot", "open")

# Ze gaan ook niet uit zichzelf omhoog voordat het huis wakker is.
scenario("vroege zomerochtend, nog niemand op", "07:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sun.sun.elevation": 15.0,
            "input_boolean.klimaat_wakker": "off"})
check("wacht op het wakker-signaal", "keuken_rolgordijn_groot", "rust", False)

scenario("zelfde ochtend, huis is wakker", "07:30",
         **{"input_select.klimaat_regime": "Koelen",
            "input_number.klimaat_verwachte_max": "30",
            "sun.sun.elevation": 15.0,
            "input_boolean.klimaat_wakker": "on"})
check("na het wakker-signaal gewoon omhoog", "keuken_rolgordijn_groot", "open")

# In het verwarmregime is de zon juist welkom; dan blijft hij omhoog, ook als de
# screens ingetrokken staan.
scenario("winterzon op de keukengevel", "12:00",
         **{"input_select.klimaat_regime": "Verwarmen",
            "input_number.klimaat_verwachte_max": "6",
            "sensor.knmi_temperatuur": "3",
            "sun.sun.elevation": 14.0,
            "binary_sensor.zon_op_voorgevel": "on",
            "binary_sensor.zon_richting_voorgevel": "on"})
check("winter: gratis warmte binnenlaten", "keuken_rolgordijn_groot", "open")

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

# De twee ankerlijsten in het package worden met de hand bijgehouden. Staat een
# zone er niet in, dan werkt hij nog steeds - maar pas bij de kwartierronde, en
# handbediening wordt er nooit voor herkend. Dat is precies wat er met het
# zonnescherm gebeurde: de sensor bestond, alleen keek niemand ernaar.
def anker_lijst(naam):
    """De entiteiten onder `entity_id: &<naam>` tot de eerste andere regel."""
    uit, verzamelen = [], False
    for regel in pakket.splitlines():
        if f"&{naam}" in regel:
            verzamelen = True
            continue
        if verzamelen:
            m = re.match(r"^\s*- (\S+)", regel)
            if m:
                uit.append(m.group(1))
            elif not re.match(r"^\s*#", regel):
                break
    return set(uit)


for anker, hoort_bij in [("advies_sensoren", lambda z, cfg: f"sensor.zonwering_advies_{z}"),
                         ("beheerde_covers", lambda z, cfg: cfg["cover"])]:
    verwacht_anker = {hoort_bij(z, cfg) for z, cfg in json.loads(MOD.zones_json()).items()}
    gevonden_anker = anker_lijst(anker)
    if verwacht_anker == gevonden_anker:
        print(f"PASS  {'elke zone staat in &' + anker:52} "
              f"({len(verwacht_anker)} zones)")
    else:
        print(f"FAIL  &{anker} loopt uit de pas met de zones")
        FOUTEN.append(f"&{anker}: mist {verwacht_anker - gevonden_anker}; "
                      f"onbekend {gevonden_anker - verwacht_anker}")

# Het moment waarop de klimaatregie de keukenrolgordijnen loslaat (BEDTIJDEN) en
# het moment waarop `kitchen_covers_close` ze laat zakken horen hetzelfde te
# zijn. Lopen ze uit elkaar, dan zit er weer een gat waarin de uitvoerder ze
# omhoog trekt - en zet hij er daarna vier uur handbediening op omdat hij zijn
# eigen tegenwerking als handbediening herkent.
keuken = open(f"{CONFIG}/packages/0 - Ground Floor/Kitchen/Covers.yaml").read()
mist_trigger = [e for e in MOD.BEDTIJDEN if e not in keuken]
if mist_trigger:
    print("FAIL  kitchen_covers_close mist een bedtijd-trigger")
    FOUTEN.append(f"kitchen_covers_close: {mist_trigger} staat niet in de triggers")
else:
    print(f"PASS  {'kitchen_covers_close sluit op dezelfde bedtijd':52} "
          f"({len(MOD.BEDTIJDEN)} helpers)")

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

# De Klimaat-weergave somt de zones met de hand op. Voeg je een zone toe en
# vergeet je die kaarten, dan stuurt de regie wél maar zie je er niets van --
# precies wat er met het zonnescherm gebeurde.
dashboard = open(f"{CONFIG}/dashboards/home/klimaat.yaml").read()
zones_cfg = json.loads(MOD.zones_json())

zonder_advies = [z for z in zones_cfg if f"sensor.zonwering_advies_{z}" not in dashboard]
if zonder_advies:
    print(f"FAIL  zones ontbreken op de Klimaat-weergave: {zonder_advies}")
    FOUTEN.append(f"dashboard mist adviessensor voor: {zonder_advies}")
else:
    print(f"PASS  {'elke zone staat op de Klimaat-weergave':52} "
          f"({len(zones_cfg)} zones)")

# Elke rij op die weergave hoort een eigen `name:` te hebben. Ontbreekt er een,
# dan valt die rij terug op zijn ruwe friendly_name ("Zonwering handmatig -
# Slaapkamer Emma") en pikt de rij eronder de naam in die eigenlijk bij zijn
# voorganger hoorde. Dat gebeurt zodra je een regel tussen een entiteit en zijn
# naam invoegt, en het is aan de YAML zelf niet te zien: het blijft geldig.
kaarten, kaart = [], None
for regel in dashboard.splitlines():
    # Een kaart loopt tot de volgende `- type:`. Zonder dat afsluiten belanden
    # de entiteiten van een grafiekkaart erna in de vorige entities-kaart, en
    # die staan daar bewust zonder naam.
    soort = re.match(r"^\s*- type: (\S+)", regel)
    if soort:
        kaart = {"titel": "?", "rijen": []} if soort.group(1) == "entities" else None
        if kaart is not None:
            kaarten.append(kaart)
    if kaart is None:
        continue
    kop = re.match(r"^\s*title: (.+)$", regel)
    if kop and kaart["titel"] == "?":
        kaart["titel"] = kop.group(1).strip()
    ent = re.match(r"^\s*- entity: (\S+)", regel)
    if ent:
        kaart["rijen"].append({"entity": ent.group(1), "naam": None})
    nm = re.match(r"^\s*name: (.+)$", regel)
    if nm and kaart["rijen"] and kaart["rijen"][-1]["naam"] is None:
        kaart["rijen"][-1]["naam"] = nm.group(1).strip()

naamloos, dubbel = [], []
for k in kaarten:
    for r in k["rijen"]:
        if r["naam"] is None:
            naamloos.append(f"{k['titel']} / {r['entity']}")
    namen = [r["naam"] for r in k["rijen"] if r["naam"]]
    for naam in sorted(set(namen)):
        if namen.count(naam) > 1:
            dubbel.append(f"{k['titel']}: '{naam}' staat {namen.count(naam)}x")

if naamloos or dubbel:
    for f in naamloos:
        print(f"FAIL  rij zonder naam op de Klimaat-weergave: {f}")
    for f in dubbel:
        print(f"FAIL  dubbele naam op de Klimaat-weergave: {f}")
    FOUTEN.extend([f"rij zonder naam: {f}" for f in naamloos]
                  + [f"dubbele naam: {f}" for f in dubbel])
else:
    rijen = sum(len(k["rijen"]) for k in kaarten)
    print(f"PASS  {'elke rij heeft een eigen, unieke naam':52} "
          f"({rijen} rijen in {len(kaarten)} kaarten)")

zonder_cover = [z for z, cfg in zones_cfg.items() if cfg["cover"] not in dashboard]
if zonder_cover:
    print(f"FAIL  covers ontbreken bij 'Werkelijke stand': {zonder_cover}")
    FOUTEN.append(f"dashboard mist cover voor: {zonder_cover}")
else:
    print(f"PASS  {'elke cover staat bij Werkelijke stand':52}")

# Als pytest dit bestand importeert draait alles hierboven al; deze functie
# geeft pytest alleen iets om te verzamelen. Zonder haar meldde `pytest
# tests/` "no tests ran" met exitcode 5, wat makkelijk voor groen doorgaat.
def test_scenarios():
    assert not FOUTEN, "\n".join(FOUTEN)


if __name__ == "__main__":
    print()
    if FOUTEN:
        print(f"{len(FOUTEN)} FOUT(EN):")
        for f in FOUTEN:
            print("  -", f)
        raise SystemExit(1)
    print("Alle scenario's zoals bedoeld.")
