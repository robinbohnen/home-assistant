"""Offline test van custom_templates/brandweer.jinja met nagebootste HA-functies.

Draaien:  python3 -m venv .venv && .venv/bin/pip install jinja2
          .venv/bin/python tests/test_brandweer.py

Net als test_kamers.py doen de stubs hieronder de Home Assistant-functies na,
zodat de randgevallen te testen zijn zonder te herstarten.

PAYLOAD is letterlijk het voorbeeld uit de spec van de webhook: kwartier 16:15,
A-ploeg onderbezet, met alle rommel die er in het echt in zit ("reserve A" is
geen persoon, "Daan van der  Zanden" heeft een dubbele spatie, iemand staat in
meerdere functies tegelijk), aangevuld met de wijzigingen zoals PreCom die sinds
augustus 2026 stuurt: genest per dag en per ploeg, met periodes in plaats van
kwartieren. De varianten daaronder dekken wat in dat voorbeeld juist NIET zat:
krap (andere sleutelnaam voor de ondergrens), herstel met was_sinds, de oude
vorm van `wijzigingen`, en een ploeg die ontbreekt omdat PreCom onbereikbaar was.
"""
import copy
import json
import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = dt.datetime(2026, 2, 14, 16, 20, 0)


def ha_strptime(value, fmt, default=None):
    try:
        return dt.datetime.strptime(str(value), fmt)
    except (TypeError, ValueError):
        return default


def ha_as_timestamp(value, default=None):
    if isinstance(value, dt.datetime):
        return value.timestamp()
    return default


def ha_bool(value, default=None):
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("true", "yes", "on", "1"):
        return True
    if str(value).lower() in ("false", "no", "off", "0"):
        return False
    return default


env = Environment(loader=FileSystemLoader(f"{CONFIG}/custom_templates"))
env.filters["to_json"] = lambda v, **k: json.dumps(v)
env.filters["from_json"] = json.loads
env.filters["bool"] = ha_bool
env.globals.update(now=lambda: NOW, strptime=ha_strptime, as_timestamp=ha_as_timestamp)

MOD = env.get_template("brandweer.jinja").module


def bezetting(payload):
    return json.loads(MOD.bezetting_json(payload).strip())


def melding(payload):
    return json.loads(MOD.melding_json(payload).strip())


# ---------------------------------------------------------------------------
# De payload uit de spec, ongewijzigd overgenomen
# ---------------------------------------------------------------------------
PAYLOAD = {
    "type": "onderbezet",
    "vorige_status": "krap",
    "ploeg": "A",
    "tijdstip": "2026-02-14 16:20",
    "kwartier": "16:15",
    "bezetting": {
        "Bevelvoerder": {
            "beschikbaar": 1, "nodig": 1, "status": "ok",
            "personen": ["Marco van Dongen"],
            "pager_uit": ["Twan van der Velden"],
            "afwezig": ["Bart van der Velden", "Nick Hermans"],
        },
        "Chauffeur": {
            "beschikbaar": 1, "nodig": 1, "status": "ok",
            "personen": ["Marco van Dongen"],
            "pager_uit": ["Twan van der Velden"],
            "afwezig": ["Bart van der Velden", "Ben Paalman", "Lode van Schadewijk", "Peter Laros"],
        },
        "Chauffeur RV": {
            "beschikbaar": 1, "nodig": 1, "status": "ok",
            "personen": ["Marco van Dongen"],
            "pager_uit": ["Twan van der Velden"],
            "afwezig": ["Bart van der Velden", "Ben Paalman", "Lode van Schadewijk", "Peter Laros"],
        },
        "Bediener RV": {
            "beschikbaar": 3, "nodig": 1, "status": "ok",
            "personen": ["Dennis Haggenburg", "Henry de Kock", "Marco van Dongen"],
            "pager_uit": ["Twan van der Velden"],
            "afwezig": ["Bart van der Velden", "Ben Paalman", "Lode van Schadewijk",
                        "Mike van Herk", "Nick Hermans", "Noah Langenhuijsen",
                        "Peter Laros", "Wietse Mélotte"],
        },
        "Manschap": {
            "beschikbaar": 3, "nodig": 4, "status": "onderbezet", "gewenst": 6,
            "personen": ["Dennis Haggenburg", "Henry de Kock", "Marco van Dongen"],
            "pager_uit": ["reserve A", "Twan van der Velden"],
            "afwezig": ["Bart van der Velden", "Ben Paalman", "Lode van Schadewijk",
                        "Mike van Herk", "Nick Hermans", "Noah Langenhuijsen",
                        "Peter Laros", "Wietse Mélotte"],
        },
        "Asp. Manschap": {
            "beschikbaar": 1, "nodig": 0, "status": "ok",
            "personen": ["Giel Smits"],
            "afwezig": ["Daan van der  Zanden"],
        },
    },
    "ploegen": {
        "A": {
            "dienst": "dienstdoend", "status": "onderbezet", "aantal": 3,
            "personen": ["Dennis Haggenburg", "Henry de Kock", "Marco van Dongen"],
            "aspiranten": ["Giel Smits"],
        },
        "B": {
            "dienst": "volgende_week", "status": "ok", "aantal": 6,
            "personen": ["Bas Boerakker", "Daan Leutscher", "Frank Coumans",
                         "Jurgen Fijneman", "Rik Koenekoop", "Robin Bohnen"],
            "aspiranten": ["Giel Smits"],
        },
        "C": {
            "dienst": "week_erna", "status": "ok", "aantal": 6,
            "personen": ["Danny van de Bungelaar", "Elke Coppens", "Ivo van Wolferen",
                         "Paul Lehmann", "Rick Suijkerbuijk", "Tim van der Burgt"],
            "aspiranten": ["Daan van der  Zanden"],
        },
    },
    "functies": [{"functie": "Manschap", "beschikbaar": 3, "nodig": 4}],
    # Sinds augustus 2026 stuurt PreCom bij ELKE wijziging, en zijn de
    # wijzigingen genest per dag en per ploeg met de periodes erbij.
    "status_veranderd": True,
    "sinds": "2026-02-14 16:20",
    "wijzigingen": {
        "vandaag": {
            "datum": "2026-02-14",
            "ploegen": {
                "A": [
                    {"persoon": "Nick Hermans",
                     "functies": ["Bediener RV", "Bevelvoerder", "Manschap"],
                     "eraf": ["18:00-22:00"]},
                    {"persoon": "Ben  Paalman",
                     "functies": ["Manschap"],
                     "erbij": ["20:00-24:00"]},
                ],
                "B": [
                    {"persoon": "Robin Bohnen",
                     "functies": ["Manschap"],
                     "eraf": ["09:00-12:00", "13:00-17:00"]},
                ],
            },
        },
        "morgen": {
            "datum": "2026-02-15",
            "ploegen": {
                "A": [
                    {"persoon": "Henry de Kock",
                     "functies": ["Chauffeur"],
                     "eraf": ["23:45-24:00"]},
                ],
            },
        },
    },
}

FOUTEN = []


def check(naam, gemeten, verwacht):
    if gemeten != verwacht:
        FOUTEN.append(f"{naam}: {gemeten!r} != {verwacht!r}")
        print(f"  FOUT  {naam}: {gemeten!r} != {verwacht!r}")
    else:
        print(f"  ok    {naam}")


def functie(v, naam):
    return next(f for f in v["functies"] if f["functie"] == naam)


# ---------------------------------------------------------------------------
print("Payload uit de spec (onderbezet, kwartier 16:15)")
v = bezetting(PAYLOAD)

check("alle zes de functies staan erin", len(v["functies"]), 6)
check("in PreCom-volgorde", v["functies"][0]["functie"], "Bevelvoerder")
check("functienaam met punt en spatie overleeft", v["functies"][-1]["functie"], "Asp. Manschap")
check("tekort telt de ontbrekende manschap", v["tekort"], 1)
check("samenvatting noemt het gat", v["samenvatting"], "Manschap 3/4")
check("één gat", len(v["gaten"]), 1)
check("gat kent zijn wens", functie(v, "Manschap")["gewenst"], 6)
check("functie zonder eigen wens erft nodig", functie(v, "Chauffeur")["gewenst"], 1)

# "reserve A" is geen persoon; wie in vier functies met pager uit staat is één man.
check("pager uit ontdubbeld en ontdaan van reserve", v["pager_uit"], ["Twan van der Velden"])
check("dubbele spatie weggepoetst", "Daan van der Zanden" in v["afwezig"], True)
check("afwezigen ontdubbeld over functies heen", len(v["afwezig"]), 9)

# Per functie optellen zou 10 geven; het echte aantal is 3 (dezelfde mensen).
check("aantal komt van de ploeg, niet uit de functies", v["aantal"], 3)
check("alle drie de ploegen", [p["ploeg"] for p in v["ploegen"]], ["A", "B", "C"])
check("ploeg kent zijn dienst", v["ploegen"][1]["dienst"], "volgende_week")
check("aspiranten meegenomen", v["ploegen"][0]["aspiranten"], ["Giel Smits"])
check("geen was_sinds bij een verslechtering", v["was_sinds"], None)
check("statuswissel als bool", v["status_veranderd"], True)

# ---------------------------------------------------------------------------
print("\nWijzigingen: dag -> ploeg -> persoon wordt één platte lijst")

check("alle vier de wijzigingen, beide dagen", len(v["wijzigingen"]), 4)
check("vandaag vóór morgen, daarbinnen op ploeg",
      [(w["dag"], w["ploeg"], w["persoon"]) for w in v["wijzigingen"]],
      [("vandaag", "A", "Nick Hermans"), ("vandaag", "A", "Ben Paalman"),
       ("vandaag", "B", "Robin Bohnen"), ("morgen", "A", "Henry de Kock")])
check("datum van de dag hangt aan elke regel",
      v["wijzigingen"][0]["datum"], "2026-02-14")
check("dubbele spatie ook hier weggepoetst",
      v["wijzigingen"][1]["persoon"], "Ben Paalman")
check("functies blijven staan",
      v["wijzigingen"][0]["functies"], ["Bediener RV", "Bevelvoerder", "Manschap"])
check("periodes, geen namen, in eraf", v["wijzigingen"][0]["eraf"], ["18:00-22:00"])
check("kort leest als een regel",
      v["wijzigingen"][0]["kort"], "Nick Hermans − 18:00-22:00")
check("meerdere periodes op één regel",
      v["wijzigingen"][2]["kort"], "Robin Bohnen − 09:00-12:00, 13:00-17:00")
check("erbij krijgt een plus", v["wijzigingen"][1]["kort"], "Ben Paalman + 20:00-24:00")

# De oude payloadvorm (wijzigingen per functie) mag geen onzin opleveren.
oud = copy.deepcopy(PAYLOAD)
oud["wijzigingen"] = {"Manschap": {"erbij": ["Nick Hermans"], "eraf": ["Ben Paalman"]}}
check("oude vorm levert een lege lijst, geen rommel", bezetting(oud)["wijzigingen"], [])

leeg_w = copy.deepcopy(PAYLOAD)
leeg_w["wijzigingen"] = {"vandaag": {"datum": "2026-02-14", "ploegen": {}},
                         "morgen": {"datum": "2026-02-15", "ploegen": {}}}
check("niets veranderd is een lege lijst", bezetting(leeg_w)["wijzigingen"], [])

zonder = copy.deepcopy(PAYLOAD)
del zonder["wijzigingen"]
del zonder["status_veranderd"]
v_zonder = bezetting(zonder)
check("payload zonder wijzigingen is geen fout", v_zonder["wijzigingen"], [])
check("ontbrekend status_veranderd telt als wissel",
      v_zonder["status_veranderd"], True)

v = bezetting(PAYLOAD)

m = melding(PAYLOAD)
check("titel zegt meteen wat er mis is", m["titel"], "Onderbezet · A-ploeg — Manschap 3/4")
check("eerste regel is het gat", m["tekst"].split("\n")[0], "Manschap 3/4 (gewenst 6)")
check("beschikbaar in de tekst", "3 beschikbaar in A-ploeg · kwartier 16:15" in m["tekst"], True)
check("pager uit met naam", "Pager uit: Twan van der Velden" in m["tekst"], True)

# In de melding alleen vandaag én alleen de dienstdoende ploeg: morgen en de
# ploegen die geen dienst hebben zijn dashboardwerk.
check("wijziging van vandaag in de tekst", "Nick Hermans − 18:00-22:00" in m["tekst"], True)
check("andere ploeg blijft eruit", "Robin Bohnen" in m["tekst"], False)
check("morgen blijft eruit", "Henry de Kock − 23:45-24:00" in m["tekst"], False)

veel = copy.deepcopy(PAYLOAD)
veel["wijzigingen"]["vandaag"]["ploegen"]["A"] = [
    {"persoon": f"Persoon {n}", "functies": ["Manschap"], "eraf": ["18:00-22:00"]}
    for n in range(1, 8)
]
tekst = melding(veel)["tekst"]
check("lange lijst wordt afgekapt", "Persoon 5" in tekst, False)
check("en zegt hoeveel er wegvielen", "en nog 3 wijzigingen" in tekst, True)

# ---------------------------------------------------------------------------
print("\nKrap: de ondergrens is dan de wens, niet het minimum")
krap = copy.deepcopy(PAYLOAD)
krap["type"] = "krap"
krap["vorige_status"] = "ok"
krap["bezetting"]["Manschap"].update(beschikbaar=5, status="krap")
krap["bezetting"]["Chauffeur"].update(beschikbaar=1, nodig=1, gewenst=2, status="krap")
v = bezetting(krap)

check("noemer is de wens", functie(v, "Manschap")["kort"], "Manschap 5/6")
check("ook bij een functie met eigen wens", functie(v, "Chauffeur")["kort"], "Chauffeur 1/2")
check("krap is geen tekort", v["tekort"], 0)
check("beide gaten in de samenvatting", v["samenvatting"], "Chauffeur 1/2 · Manschap 5/6")
check("titel noemt beide", melding(krap)["titel"], "Krap bezet · A-ploeg — Chauffeur 1/2 · Manschap 5/6")

# ---------------------------------------------------------------------------
print("\nHerstel: hoe lang stond het mis")
hersteld = copy.deepcopy(PAYLOAD)
hersteld["type"] = "ok"
hersteld["vorige_status"] = "onderbezet"
hersteld["was_sinds"] = "2026-02-14 13:45"
hersteld["bezetting"]["Manschap"].update(beschikbaar=6, status="ok")
hersteld["ploegen"]["A"].update(status="ok", aantal=6)
v = bezetting(hersteld)

check("geen gaten meer", v["gaten"], [])
check("samenvatting zegt het ook", v["samenvatting"], "Op orde")
check("titel zonder staart", melding(hersteld)["titel"], "Bezetting op orde · A-ploeg")
check("duur van de storing erbij",
      melding(hersteld)["tekst"].split("\n")[0],
      "Weer op orde, was onderbezet sinds 13:45 (2 u 35).")

onbekend = copy.deepcopy(hersteld)
onbekend["was_sinds"] = "onbekend"
check("onbruikbaar tijdstip laat de duur weg",
      melding(onbekend)["tekst"].split("\n")[0], "Weer op orde, was onderbezet.")

# ---------------------------------------------------------------------------
print("\nRandgevallen")
storing = copy.deepcopy(PAYLOAD)
del storing["ploegen"]["C"]  # PreCom onbereikbaar voor die ploeg
check("ontbrekende ploeg is geen fout",
      [p["ploeg"] for p in bezetting(storing)["ploegen"]], ["A", "B"])

kaal = {"type": "ok", "vorige_status": "krap", "ploeg": "B",
        "tijdstip": "2026-02-14 16:20", "kwartier": "16:15",
        "bezetting": {}, "ploegen": {}}
v = bezetting(kaal)
check("lege payload geeft lege lijsten", (v["functies"], v["gaten"], v["pager_uit"]), ([], [], []))
check("en nul in plaats van niets", (v["tekort"], v["aantal"]), (0, 0))

leeg = copy.deepcopy(PAYLOAD)
leeg["bezetting"]["Manschap"].update(beschikbaar=0, personen=[])
check("nul beschikbaar wordt benoemd",
      melding(leeg)["tekst"].split("\n")[0], "Manschap 0/4 (gewenst 6) - nog niemand")

# ---------------------------------------------------------------------------
print()
if FOUTEN:
    print(f"{len(FOUTEN)} FOUT(EN):")
    for f in FOUTEN:
        print("  -", f)
    raise SystemExit(1)
print("Alle scenario's kloppen.")
