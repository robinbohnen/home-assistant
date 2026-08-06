"""Offline test van de spraak-intents met nagebootste HA-functies.

Draaien:  python3 -m venv .venv && .venv/bin/pip install jinja2 pyyaml
          .venv/bin/python tests/test_spraak.py

Twee dingen worden hier bewaakt.

1. De zinnen in custom_sentences/nl/huis.yaml en de intents in
   `packages/0 - Ground Floor/Kitchen/Voice.yaml` horen bij elkaar. Een zin
   zonder intent geeft in Home Assistant een lege reactie, een intent zonder
   zin is onbereikbaar - allebei zonder foutmelding.

2. Wat de satelliet zegt. De `speech`-teksten zijn Jinja over sensoren die
   lang niet altijd gevuld zijn (de brandweer-webhook vuurt alleen bij een
   statuswissel, Zonneplan valt weleens weg). Die randgevallen zijn hier te
   testen zonder te herstarten en zonder te wachten tot het toevallig gebeurt.

Net als test_klimaat.py doen de stubs de Home Assistant-functies na.
"""
import os
import re

import yaml
from jinja2 import Environment

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAKKET = f"{CONFIG}/packages/0 - Ground Floor/Kitchen/Voice.yaml"
ZINNEN = f"{CONFIG}/custom_sentences/nl/huis.yaml"

STATES = {}
FOUTEN = []


def ha_states(eid):
    v = STATES.get(eid, "unknown")
    return v if isinstance(v, str) else str(v)


def ha_state_attr(eid, attr):
    return STATES.get(f"{eid}.{attr}")


def ha_is_state(eid, val):
    return ha_states(eid) == val


def ha_has_value(eid):
    return ha_states(eid) not in ("unknown", "unavailable", "")


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


env = Environment()
env.filters["float"] = f_float
env.globals.update(states=ha_states, state_attr=ha_state_attr,
                   is_state=ha_is_state, has_value=ha_has_value)

with open(PAKKET, encoding="utf-8") as fh:
    PACKAGE = yaml.safe_load(fh)["keuken_voice_package"]
with open(ZINNEN, encoding="utf-8") as fh:
    SENTENCES = yaml.safe_load(fh)

INTENTS = PACKAGE["intent_script"]


def zeg(intent):
    """Rendert de speech-tekst van een intent tot één regel, zoals TTS hem leest."""
    tekst = INTENTS[intent]["speech"]["text"]
    return " ".join(env.from_string(tekst).render().split())


def check(naam, waarde, verwacht):
    """`verwacht` is een substring, of een lijst substrings die er allemaal in moeten."""
    for v in ([verwacht] if isinstance(verwacht, str) else verwacht):
        if v not in waarde:
            FOUTEN.append(f"{naam}: '{v}' zit niet in '{waarde}'")
            return
    print(f"  ok  {naam}: {waarde}")


def wereld(**kw):
    STATES.clear()
    STATES.update(kw)


# ---------------------------------------------------------------------------
# 1. Zinnen en intents horen bij elkaar
# ---------------------------------------------------------------------------
print("Zinnen en intents")

met_zin = set(SENTENCES["intents"])
met_antwoord = set(INTENTS)

for naam in sorted(met_zin - met_antwoord):
    FOUTEN.append(f"zin voor intent '{naam}', maar die staat niet in intent_script")
for naam in sorted(met_antwoord - met_zin):
    FOUTEN.append(f"intent '{naam}' heeft geen enkele zin in custom_sentences")
if met_zin == met_antwoord:
    print(f"  ok  {len(met_zin)} intents, allemaal met zinnen")

# Een intent zonder speech zegt niets terug, en dat is op een satelliet niet te
# onderscheiden van "hij heeft me niet verstaan".
for naam, spec in sorted(INTENTS.items()):
    if "speech" not in spec:
        FOUTEN.append(f"intent '{naam}' geeft geen speech terug")

# Zinnen mogen geen hoofdletters of leestekens bevatten: Home Assistant matcht
# op de genormaliseerde tekst en een vraagteken in de lijst matcht dus nooit.
for naam, spec in sorted(SENTENCES["intents"].items()):
    for blok in spec["data"]:
        for zin in blok["sentences"]:
            if re.search(r"[A-Z?.,!]", zin):
                FOUTEN.append(f"zin van '{naam}' heeft hoofdletters of leestekens: {zin}")

# ---------------------------------------------------------------------------
# 2. Kazerne
# ---------------------------------------------------------------------------
print("\nBrandweerbezetting")

wereld(**{
    "sensor.brandweer_bezetting": "onderbezet",
    "sensor.brandweer_bezetting.ploeg": "A",
    "sensor.brandweer_bezetting.aantal": "5",
    "sensor.brandweer_bezetting.tekort": "2",
    "sensor.brandweer_bezetting.samenvatting": "Manschap 3/4 · Chauffeur 1/2",
    "binary_sensor.brandweer_ik_heb_dienst": "off",
})
check("onderbezet", zeg("BrandweerBezetting"),
      ["A-ploeg is onderbezet", "5 man", "2 personen tekort",
       "Manschap 3/4, Chauffeur 1/2"])

# Eén persoon tekort is geen "1 personen".
STATES["sensor.brandweer_bezetting.tekort"] = "1"
check("enkelvoud", zeg("BrandweerBezetting"), "1 persoon tekort")

# Heb ik dienst, dan hoort dat erbij: dat is de reden dat je het vraagt.
STATES["binary_sensor.brandweer_ik_heb_dienst"] = "on"
check("eigen dienst", zeg("BrandweerBezetting"), "Jij hebt deze week dienst")

wereld(**{
    "sensor.brandweer_bezetting": "ok",
    "sensor.brandweer_bezetting.ploeg": "B",
    "sensor.brandweer_bezetting.aantal": "9",
    "sensor.brandweer_bezetting.samenvatting": "Op orde",
    "binary_sensor.brandweer_ik_heb_dienst": "off",
})
check("op orde", zeg("BrandweerBezetting"), "B-ploeg is op orde met 9 man")

# De webhook vuurt alleen bij een statuswissel. Na een herstart zonder wissel is
# `sensor.brandweer_bezetting` leeg en moet het antwoord uit de REST-sensor
# komen - anders staat de satelliet dagenlang met zijn mond vol tanden.
wereld(**{
    "sensor.brandweer_bezetting": "unavailable",
    "input_select.brandweer_dienstdoende_ploeg": "C Ploeg",
    "sensor.bezetting_ploeg_c": "7",
    "binary_sensor.brandweer_ik_heb_dienst": "off",
})
check("terugval op REST", zeg("BrandweerBezetting"), ["7 man", "C Ploeg"])

wereld(**{"sensor.brandweer_bezetting": "unavailable",
          "input_select.brandweer_dienstdoende_ploeg": "C Ploeg",
          "sensor.bezetting_ploeg_c": "unavailable"})
check("niets bekend", zeg("BrandweerBezetting"), "nog geen bezetting binnengekregen")

# ---------------------------------------------------------------------------
# 3. Stroomprijs
# ---------------------------------------------------------------------------
print("\nStroomprijs")

# De vijfdeling van Zonneplan: 'very_low' is óók goedkoop. Testen op de hele
# waarde (== 'low') is precies de fout die op 1 augustus 2026 het hele huis
# door liep; vandaar dit scenario. Zie packages/9 - Other/Stroomprijs.yaml.
wereld(**{
    "sensor.slimhuys_zonneplan_huidige_prijs": "0.087",
    "sensor.slimhuys_zonneplan_tariefniveau_nu": "very_low",
    "sensor.stroomprijs_niveau_volgend_uur": "medium",
})
check("very_low telt als goedkoop", zeg("StroomprijsNu"), ["8,7 cent", "goedkoop"])

wereld(**{
    "sensor.slimhuys_zonneplan_huidige_prijs": "0.34",
    "sensor.slimhuys_zonneplan_tariefniveau_nu": "very_high",
    "sensor.stroomprijs_niveau_volgend_uur": "low",
})
check("duur, maar straks beter", zeg("StroomprijsNu"),
      ["34,0 cent", "duur", "volgende uur is goedkoper"])

wereld(**{
    "sensor.slimhuys_zonneplan_huidige_prijs": "0.19",
    "sensor.slimhuys_zonneplan_tariefniveau_nu": "medium",
    "sensor.stroomprijs_niveau_volgend_uur": "high",
})
check("gemiddeld, straks duurder", zeg("StroomprijsNu"),
      ["gemiddeld", "volgende uur wordt duurder"])

wereld(**{"sensor.slimhuys_zonneplan_huidige_prijs": "unavailable"})
check("geen prijs", zeg("StroomprijsNu"), "krijg de stroomprijs even niet binnen")

# ---------------------------------------------------------------------------
# 4. Zonnescherm
# ---------------------------------------------------------------------------
print("\nZonnescherm")

# Omgekeerde cover: `closed` = ingetrokken, advies 'dicht' = zonwering dicht,
# dus scherm eruit. Een tip die deze twee door elkaar haalt zegt het
# omgekeerde van wat er moet gebeuren.
wereld(**{
    "sensor.zonwering_advies_zonnescherm": "dicht",
    "sensor.zonwering_advies_zonnescherm.reden": "zon op de achtergevel en 26 graden binnen",
    "cover.achtertuin_zonnescherm": "closed",
})
check("mag eruit", zeg("ZonneschermAdvies"),
      ["scherm staat ingetrokken", "mag eruit", "zet het zonnescherm uit"])

wereld(**{
    "sensor.zonwering_advies_zonnescherm": "open",
    "sensor.zonwering_advies_zonnescherm.reden": "de zon is van de achtergevel af",
    "cover.achtertuin_zonnescherm": "open",
})
check("mag terug", zeg("ZonneschermAdvies"),
      ["scherm staat uit", "mag terug naar binnen"])

check("uitzetten waarschuwt", zeg("ZonneschermUit"),
      ["scherm gaat eruit", "Let op"])

wereld(**{"sensor.zonwering_advies_zonnescherm": "dicht",
          "sensor.zonwering_advies_zonnescherm.reden": "zon op de achtergevel",
          "cover.achtertuin_zonnescherm": "closed"})
check("uitzetten zonder gemopper", zeg("ZonneschermUit"), "scherm gaat eruit")
if "Let op" in zeg("ZonneschermUit"):
    FOUTEN.append("ZonneschermUit waarschuwt terwijl het advies het ermee eens is")

wereld(**{"sensor.zonwering_advies_zonnescherm": "unavailable"})
check("geen advies", zeg("ZonneschermAdvies"), "advies even niet lezen")

# ---------------------------------------------------------------------------
# 5. Het huis
# ---------------------------------------------------------------------------
print("\nHuis")


def kamer(naam, score=0, reden="", open_namen=()):
    return {"naam": naam, "score": score, "reden": reden,
            "contacten": {"gemeten": True, "open": len(open_namen),
                          "totaal": 2, "namen": list(open_namen)}}


wereld(**{"sensor.kamers.kamers": [
    kamer("Keuken"), kamer("Woonkamer"), kamer("Kantoor")]})
check("alles dicht", zeg("HuisOpen"), "Alles is dicht")

wereld(**{"sensor.kamers.kamers": [
    kamer("Keuken", open_namen=["Achterdeur"]), kamer("Woonkamer")]})
check("één open", zeg("HuisOpen"), "Er staat er één open: Achterdeur")

wereld(**{"sensor.kamers.kamers": [
    kamer("Keuken", open_namen=["Achterdeur", "Keukenraam"]),
    kamer("Kantoor", open_namen=["Kantoorraam"])]})
check("drie open", zeg("HuisOpen"),
      "Er staan er 3 open: Achterdeur, Keukenraam en Kantoorraam")

# De sensor draait één keer per minuut en is er na een herstart even niet.
wereld()
check("kamers onbekend", zeg("HuisOpen"), "kamerstatus even niet lezen")

wereld(**{"sensor.kamers.kamers": [kamer("Keuken"), kamer("Woonkamer")]})
check("niks aan de hand", zeg("HuisAandacht"), "Alles staat goed")

wereld(**{"sensor.kamers.kamers": [
    kamer("Keuken", score=1, reden="warm, 24°"),
    kamer("Slaapkamer", score=2, reden="CO₂ 1400 ppm"),
    kamer("Kantoor", score=1, reden="vochtig, 68%"),
    kamer("Badkamer", score=1, reden="vochtig, 71%")]})
# Ergste eerst, hoogstens drie, en de rest als getal: een opsomming van zeven
# kamers is op een speaker niet te volgen.
check("ergste eerst", zeg("HuisAandacht"),
      ["Slaapkamer: CO₂ 1400 ppm", "En nog 1 andere"])

# ---------------------------------------------------------------------------
# 6. Antwoorden
# ---------------------------------------------------------------------------
print("\nAntwoorden")

# `action_response` bestaat hier niet (dat vult Home Assistant pas na het
# uitvoeren van de actie). De tekst moet dan terugvallen, niet ontploffen.
check("ja valt netjes terug", zeg("AntwoordJa"), "Oké")
check("nee valt netjes terug", zeg("AntwoordNee"), "Oké")

# ---------------------------------------------------------------------------
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
    print("Alle scenario's kloppen.")
