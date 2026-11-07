"""Offline test van de School-weergave in Server-stijl (dashboards/home/school.yaml
en school/logan.yaml). 7 november 2026.

Draaien:  python3 tests/test_school_pagina.py      (nodig: pyyaml en node)

De Magister-macro's zelf test tests/test_school.py; dit bestand test de weergave:
1. path/title/icon zijn gebleven; panel-weergave; het kind-blok is een include
   en de gedeelde kolom is de laatste kaart (het raster herkent hem daaraan);
2. NIETS IS VERDWENEN: elke macro-aanroep en elke entiteit van de oude weergave
   (commit bb9c07a) staat er nog, de week-planner met zijn kalenders en
   vakcodes ook, en de voorwaarden (vandaag-rooster, opdrachten, cijfers,
   absenties, onderhoud) zitten nog op dezelfde tellers;
3. de JS van elk paneel in node: normaal, vrije dag, onvoldoende, ongeoorloofd,
   weg van huis, lege batterij, onderhoud nodig, lege states en ge-escapete
   state-tekst;
4. tegen /tmp/states.json (als die er is): elke gebruikte entiteit bestaat.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, Dashboard, kaarten, st  # noqa: E402

SCHOOL = os.path.join(CONFIG, "dashboards", "home", "school.yaml")
LOGAN = os.path.join(CONFIG, "dashboards", "home", "school", "logan.yaml")
S, L = Dashboard(SCHOOL), Dashboard(LOGAN)
TEKST = open(SCHOOL, encoding="utf-8").read() + open(LOGAN, encoding="utf-8").read()
K = "sensor.magister_logan_veen"

# Wat de oude weergave toonde (sections met markdown/entities; commit bb9c07a).
OUD_ENTITEITEN = """
binary_sensor.magister_haalt_niets_meer_op calendar.magister_logan_veen_kalender calendar.maxi
sensor.magister_logan_veen_afspraken sensor.magister_logan_veen_roosterwijzigingen update.magister_school_update
person.logan_veen sensor.iphone_battery_level sensor.logan_reistijd_naar_huis sensor.logan_veen_geo
sensor.magister_logan_veen_absenties sensor.magister_logan_veen_afspraken_vandaag sensor.magister_logan_veen_cijfers
sensor.magister_logan_veen_opdrachten sensor.magister_data
""".split()
OUD_MACROS = ["overzicht_alle()", "weektaken_alle(14)", "nu(kind)", "klas(kind)",
              "rooster('sensor.magister_logan_veen', 'vandaag')", "rooster(kind, 'volgende')",
              "werk('sensor.magister_logan_veen', 14)", "opdrachten('sensor.magister_logan_veen')",
              "cijfers('sensor.magister_logan_veen', 10)", "voortgang('sensor.magister_logan_veen')",
              "absenties('sensor.magister_logan_veen')"]


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def basis():
    morgen = time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400))
    return {
        K: st("3"),
        K + "_school_start_vandaag": st("08:45"), K + "_school_einde_vandaag": st("15:30"),
        K + "_volgende_schooldag": st(morgen), K + "_volgende_schooldag_start": st("09:35"),
        K + "_volgende_schooldag_einde": st("14:40"),
        K + "_cijfers": st(2, cijfers=[
            {"vak": "EN", "omschrijving": "Woordenschat", "waarde": "8,4", "ingevoerd_op": "2026-10-14 15:23:35"},
            {"vak": "WI", "omschrijving": "Getallen", "waarde": "7,0", "ingevoerd_op": "2026-10-26 16:38:55"}]),
        K + "_opdrachten": st(2, open_opdrachten=[]),
        K + "_huiswerk": st(8),
        K + "_afspraken": st(81, aantal_uitval=0), K + "_roosterwijzigingen": st(0),
        K + "_absenties": st(2, absenties=[{"geoorloofd": True}, {"geoorloofd": True}]),
        "sensor.magister_data": st(iso(time.time() - 600)),
        "binary_sensor.magister_haalt_niets_meer_op": st("off"),
        "update.magister_school_update": st("off", installed_version="v2.3.1", latest_version="v2.3.1"),
        "person.logan_veen": st("home"), "sensor.logan_veen_geo": st("Thuis"),
        "sensor.logan_reistijd_naar_huis": st(0.6), "sensor.iphone_battery_level": st(64),
    }


def schoon(h):
    for fout in ("undefined", "NaN", "[object", "null"):
        assert fout not in h, f"{fout} in de HTML"
    return h


def alle_namen():
    return [(S, n) for n in S.namen()] + [(L, n) for n in L.namen()]


# ------------------------------------------------------------------ 1. vorm
def test_vorm():
    assert S.doc["path"] == "school" and S.doc["title"] == "School" and S.doc["icon"] == "mdi:school"
    assert S.doc["panel"] is True
    raster = S.doc["cards"][0]["cards"][0]
    assert "!include school/logan.yaml" in open(SCHOOL, encoding="utf-8").read()
    # De include laadt hier als None; de gedeelde kolom is de laatste kaart.
    assert raster["cards"][0] is None and raster["cards"][-1]["type"] == "vertical-stack"
    stijl = raster["card_mod"]["style"]
    assert "#root > *:not(:last-child) { grid-column: span 2" in stijl and "grid-auto-flow: dense" in stijl
    assert L.doc["type"] == "horizontal-stack" and len(L.doc["cards"]) == 2


# ------------------------------------------------- 2. niets is verdwenen
def test_niets_verdwenen():
    for e in OUD_ENTITEITEN:
        assert e in TEKST, e
    for m in OUD_MACROS:
        assert m in TEKST, m
    planner = next(k for k in S.alle if k.get("type") == "custom:week-planner-card")
    assert [c["entity"] for c in planner["calendars"]] == ["calendar.magister_logan_veen_kalender", "calendar.maxi"]
    assert planner["calendars"][0]["replaceTitleText"]["WI"] == "Wiskunde"
    assert planner["calendars"][0]["filter"] == "^(?!.+ - .+ - )"
    assert planner["hideWeekend"] is True and planner["days"] == 14


def voorwaarden():
    uit = {}
    for d in (S, L):
        for k in d.alle:
            if k.get("type") == "conditional":
                for c in k["conditions"]:
                    for cc in c.get("conditions", [c]):
                        uit[cc["entity"]] = cc.get("state_not", cc.get("state"))
    return uit


def test_voorwaarden():
    v = voorwaarden()
    for teller in ("afspraken_vandaag", "opdrachten", "cijfers", "absenties"):
        assert v[f"{K}_{teller}"] == "0", teller
    assert v["binary_sensor.magister_haalt_niets_meer_op"] == "on" and v["update.magister_school_update"] == "on"
    # Een template-voorwaarde verbergt stil de hele kaart: niet gebruiken.
    assert "condition: template" not in TEKST


# --------------------------------------------------------------- 3. de JS
def test_normaal():
    s = basis()
    h = schoon(L.render("kind", s))
    assert ">LOGAN<" in h and "school 08:45–15:30" in h and "09:35" in h and "morgen" in h
    assert "7,0" in h and "WI" in h and "var(--ov-ok)" in h, "nieuwste cijfer op ingevoerd_op, voldoende = groen"
    assert ">geen wijzigingen<" in schoon(L.render("rooster", s))
    assert ">geen onvoldoendes<" in schoon(L.render("cijfers", s))
    assert ">2 dit jaar<" in schoon(L.render("absenties", s))
    assert ">14 dagen<" in schoon(L.render("werk", s))
    h = schoon(L.render("onderweg", s))
    assert ">thuis<" in h and "64%" in h and "is thuis" in h
    assert "10 min geleden" in schoon(S.render("kort", s))
    assert ">in orde<" in schoon(S.render("onderhoud", s))


def test_bijzonder():
    s = {**basis(), K + "_school_start_vandaag": st("Geen"), K + "_school_einde_vandaag": st("Geen")}
    h = L.render("kind", s)
    assert ">vrij vandaag<" in h and "geen lessen" in h
    s = {**basis(), K + "_cijfers": st(1, cijfers=[{"vak": "WI", "waarde": "4,8", "ingevoerd_op": "2026-11-01 10:00:00"}])}
    assert ">1 onvoldoende<" in L.render("cijfers", s) and "var(--ov-bad)" in L.render("kind", s)
    s = {**basis(), K + "_absenties": st(3, absenties=[{"geoorloofd": False}, {"geoorloofd": True}])}
    assert ">1 ongeoorloofd<" in L.render("absenties", s)
    s = {**basis(), K + "_opdrachten": st(3, open_opdrachten=[{"titel": "x"}])}
    assert ">1 opdracht open<" in L.render("werk", s)
    s = {**basis(), K + "_afspraken": st(81, aantal_uitval=2)}
    assert ">2 uitval<" in L.render("rooster", s)
    s = {**basis(), "person.logan_veen": st("not_home"), "sensor.logan_veen_geo": st("Stationsplein"),
         "sensor.logan_reistijd_naar_huis": st(12.4), "sensor.iphone_battery_level": st(15)}
    h = L.render("onderweg", s)
    assert ">weg<" in h and "Stationsplein" in h and "12 min" in h and "var(--ov-bad)" in h
    s = {**basis(), "sensor.magister_data": st(iso(time.time() - 3 * 3600)),
         "binary_sensor.magister_haalt_niets_meer_op": st("on"),
         "update.magister_school_update": st("on", installed_version="v2.3.1", latest_version="v2.4.0")}
    h = S.render("onderhoud", s)
    assert ">2 meldingen<" in h and "3,0 uur geleden" in h and "v2.3.1 → v2.4.0" in h
    assert ">haalt niets meer op<" in S.render("kort", s)


def test_lege_states():
    for d, n in alle_namen():
        schoon(d.render(n, {}))
        schoon(d.render(n, {e: st("unavailable") for e in basis()}))
    assert "nog niets opgehaald" in S.render("kort", {})
    assert ">geen data<" in L.render("kind", {})


def test_escaping():
    kwaad = "<img src=x onerror=alert(1)>"
    s = {**basis(),
         K + "_cijfers": st(1, cijfers=[{"vak": kwaad, "omschrijving": kwaad, "waarde": kwaad, "ingevoerd_op": "2026-11-01"}]),
         K + "_school_start_vandaag": st(kwaad),
         "person.logan_veen": st(kwaad), "sensor.logan_veen_geo": st(kwaad),
         "update.magister_school_update": st("on", installed_version=kwaad, latest_version=kwaad)}
    for d, n in alle_namen():
        assert "<img" not in d.render(n, s), n


def test_klikbaar():
    # Elke HTML-kaart heeft een sv-template (pointer-events: auto) en klikt alleen
    # naar more-info: er zijn hier geen pop-ups.
    for d, n in alle_namen():
        assert d.kaart(n)["template"] in ("sv_html", "sv_paneel"), n
    assert "#" not in "".join(re.findall(r"navigation_path:'([^']*)'", "".join(d.render(n, basis()) for d, n in alle_namen())))


# ------------------------------------------------------------ 4. live
def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    gebruikt = set(re.findall(r"\b((?:sensor|binary_sensor|person|update|calendar)\.[a-z0-9_]+)\b", TEKST))
    gebruikt = {e for e in gebruikt if not e.endswith("_") and e not in ("sensor.magister_logan_veen_", "sensor.time")}
    # Voorbeeld voor een tweede kind in de commentaren.
    gebruikt -= {"calendar.mini", "calendar.magister_"}
    weg = sorted(e for e in gebruikt if e not in states and "<" not in e)
    assert not weg, f"bestaat niet (meer): {weg}"
    for d, n in alle_namen():
        schoon(d.render(n, states))


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
