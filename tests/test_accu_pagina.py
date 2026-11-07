"""Offline test van de Accu-pagina (dashboards/home/accu.yaml), 7 november 2026.

Draaien:  python3 tests/test_accu_pagina.py      (nodig: PyYAML en node)

De pagina staat sinds 7 november 2026 in Server-stijl (docs/dashboard-stijl.md).
De JS van elk paneel draait via tests/sv_render.py met www/sv-kit.js en de
templates uit overzicht_templates.yaml. Bewaakt wordt:
1. DE ACCU: lading groot in de kleur van de richting (sensor.accu_status is de
   enige bron), vermogen in W/kW, inhoud in kWh, de dagtellers en het
   dag-rendement pas vanaf 2 kWh aan beide kanten; storing en weggevallen
   lading in de badge;
2. STAAT: temperatuurgrenzen van LFP (5-40 °C oranje, buiten 0-45 rood),
   gezondheid onder 90% oranje, meldingen en MarkeDroid;
3. NOODSTROOM: de vier standen (nog niet actief, net er, stroomstoring,
   omvormer los), de duur zonder "60 min", last_w met het goede teken en het
   herstartpunt alleen tijdens een storing;
4. ontbrekende entiteiten: geen exception, geen undefined/NaN;
5. tekst uit een state wordt ge-escapet;
6. elke klik-hash heeft een pop-up met 4 en 24 uur en dezelfde reeksen, de
   prijsgrafiek staat er nog, en er is geen bediening;
7. (als /tmp/states.json er is) elke gebruikte entiteit bestaat en elk paneel
   rendert.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, Dashboard, st  # noqa: E402

PAGINA = os.path.join(CONFIG, "dashboards", "home", "accu.yaml")
with open(PAGINA, encoding="utf-8") as f:
    RUW = f.read()
D = Dashboard(PAGINA)

KWAAD = "<img src=x onerror=alert(1)>"

ACCU = {
    "sensor.accu_lading": st(74, unit_of_measurement="%"),
    "sensor.accu_vermogen": st(1840, unit_of_measurement="W"),
    "sensor.accu_status": st("laden"),
    "sensor.accu_inhoud": st(24.06, unit_of_measurement="kWh"),
    "sensor.accu_capaciteit": st(51.2, unit_of_measurement="kWh", gezondheid_procent=99.93, cycli=19.62),
    "sensor.accu_vandaag_geladen": st(4.0, unit_of_measurement="kWh"),
    "sensor.accu_vandaag_ontladen": st(3.0, unit_of_measurement="kWh"),
    "sensor.accu_temperatuur": st(19.3, unit_of_measurement="°C"),
    "binary_sensor.omvormer_storing": st("off", omschrijving="geen"),
    "binary_sensor.markedroid_verbinding": st("on"),
    "sensor.markedroid_regie": st("vasthouden", omschrijving="vasthouden, alleen laden", flex_w=None),
    "sensor.markedroid_exportbegrenzer": st("onbekend"),
}


def tekst(h):
    return re.sub(r"<[^>]+>", "", h)


def schoon(h):
    assert h and "undefined" not in h and "NaN" not in h, h[:300]
    return h


# ------------------------------------------------------------------ DE ACCU
def test_accu_laadt():
    h = schoon(D.render("accu", ACCU))
    t = tekst(h)
    assert "74%" in t and "laadt met 1,8 kW" in t and "24,1 / 51,2 kWh" in t
    assert ">laadt<" in h and "var(--ov-ok)" in h
    # Rendement pas met 2 kWh aan beide kanten: 3 van 4 = 75%.
    assert "75% van wat erin ging" in t and "4,0 kWh" in t
    assert "navigation_path:'#accu-lading'" in h and "navigation_path:'#accu-vermogen'" in h


def test_accu_levert_en_rust():
    h = D.render("accu", {**ACCU, "sensor.accu_status": st("ontladen"), "sensor.accu_vermogen": st(-640, unit_of_measurement="W")})
    assert "levert 640 W" in tekst(h) and ">levert<" in h and "var(--ov-warn)" in h
    h = D.render("accu", {**ACCU, "sensor.accu_status": st("rust"), "sensor.accu_vermogen": st(3)})
    assert "staat stil" in tekst(h) and ">rust<" in h


def test_accu_rendement_niet_te_vroeg():
    h = D.render("accu", {**ACCU, "sensor.accu_vandaag_ontladen": st(0.2)})
    assert "van wat erin ging" not in h


def test_accu_problemen():
    h = D.render("accu", {**ACCU, "sensor.accu_lading": st("unavailable")})
    assert ">niet bereikbaar<" in h and "—" in h
    h = D.render("accu", {**ACCU, "binary_sensor.omvormer_storing": st("on", omschrijving="x")})
    assert ">storing<" in h


# -------------------------------------------------------------------- STAAT
def test_staat_normaal():
    h = schoon(D.render("staat", ACCU))
    t = tekst(h)
    assert ">in orde<" in h and "19,3°" in t and "99,9%" in t and "20 cycli" in t
    assert "vasthouden, alleen laden" in t and "Meldingen" in t
    assert "navigation_path:'#accu-temp'" in h


def test_staat_grenzen():
    h = D.render("staat", {**ACCU, "sensor.accu_temperatuur": st(42)})
    assert ">temperatuur<" in h and "var(--ov-warn)\">42,0°" in h
    h = D.render("staat", {**ACCU, "sensor.accu_temperatuur": st(-1)})
    assert "var(--ov-bad)\">-1,0°" in h or "var(--ov-bad)\">−1,0°" in h
    h = D.render("staat", {**ACCU, "sensor.accu_capaciteit": st(51.2, gezondheid_procent=88, cycli=4000)})
    assert ">gezondheid<" in h and "var(--ov-warn)\">88,0%" in h


def test_staat_meldingen_en_markedroid():
    h = D.render("staat", {**ACCU, "binary_sensor.omvormer_storing": st("on", omschrijving="melding: Fan failure"),
                           "binary_sensor.markedroid_verbinding": st("off")})
    assert "melding: Fan failure" in h and "geen berichten meer" in h and ">2 meldingen<" in h
    h = D.render("staat", {**ACCU, "sensor.markedroid_exportbegrenzer": st("actief"),
                           "sensor.markedroid_regie": st("x", omschrijving="laden", flex_w=800)})
    assert "laden · flex 800 W · teruglevering dicht" in tekst(h)


# --------------------------------------------------------------- NOODSTROOM
def nood(op="off", oorzaak="omvormer", geleden=0, **attrs):
    t = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - geleden))
    a = {"bruikbaar_kwh": 18.9, "last_w": 1841, "basis": "huislast_uur", "stand": "loopt_leeg", "herstart_procent": 50}
    a.update(attrs)
    huis = st(op, oorzaak=oorzaak)
    huis["last_changed"] = t
    return {"binary_sensor.accu_geinstalleerd": st("on"), "binary_sensor.huis_op_accu": huis,
            "sensor.noodstroom_resterend": st(a.pop("h", 10.3), **a)}


def test_noodstroom_net_er():
    h = schoon(D.render("noodstroom", nood()))
    t = tekst(h)
    assert ">net is er<" in h and "10 u 18 min" in t and "als het nu uitvalt" in t
    assert "18,9 kWh" in t and "Huis, laatste uur" in t and "1.841 W" in t
    assert "Daarna uit tot" not in t and "laadpaal" in t


def test_noodstroom_storing():
    h = D.render("noodstroom", nood("on", "stroomstoring", geleden=75 * 60))
    t = tekst(h)
    assert ">stroomstoring<" in h and "Stroomstoring · sinds" in t and "(1 u 15 min)" in t
    assert "nog te gaan" in t and "Daarna uit tot50%" in t


def test_noodstroom_omvormer_los_en_niet_actief():
    h = D.render("noodstroom", nood("on", "omvormer"))
    assert ">los van het net<" in h and "netbeveiliging" in h
    s = nood()
    s["binary_sensor.accu_geinstalleerd"] = st("off")
    assert ">nog niet actief<" in D.render("noodstroom", s)


def test_noodstroom_duur_en_teken():
    # 5,995 uur mag geen "5 u 60 min" worden.
    assert "6 u" in tekst(D.render("noodstroom", nood(h=5.995))) and "60 min" not in tekst(D.render("noodstroom", nood(h=5.995)))
    t = tekst(D.render("noodstroom", nood("on", "stroomstoring", basis="accu_kwartier", last_w=-600)))
    assert "Zon laadt op" in t and "600 W" in t
    assert "zon vult bij" in tekst(D.render("noodstroom", nood(stand="laadt_bij")))


# ----------------------------------------------------------------- algemeen
def test_alles_weg_geen_exception():
    for naam in ("accu", "staat", "noodstroom", "prijs"):
        schoon(D.render(naam, {}))


def test_state_tekst_wordt_ge_escaped():
    h = D.render("staat", {**ACCU, "binary_sensor.omvormer_storing": st("on", omschrijving=KWAAD),
                           "sensor.markedroid_regie": st("x", omschrijving=KWAAD, flex_w=KWAAD)})
    assert "<img" not in h and "&lt;img" in h
    h = D.render("accu", {**ACCU, "sensor.accu_status": st(KWAAD)})
    assert "<img" not in h
    h = D.render("noodstroom", nood("on", "stroomstoring", herstart_procent=KWAAD))
    assert "<img" not in h


def popups():
    return {k["hash"]: k for k in D.alle if k.get("type") == "custom:bubble-card" and k.get("card_type") == "pop-up"}


def test_elke_klik_hash_heeft_een_popup():
    pp = popups()
    gebruikt = set(re.findall(r"#accu-[a-z-]+", RUW))
    assert gebruikt == set(pp), (gebruikt, set(pp))
    for h, p in pp.items():
        assert [c["graph_span"] for c in p["cards"]] == ["4h", "24h"], h
        assert p["cards"][0]["series"] == p["cards"][1]["series"], h
        func = p["cards"][1]["all_series_config"]["group_by"]["func"]
        assert func == ("max" if h == "#accu-temp" else "avg"), h


def test_schil_grafiek_en_alleen_lezen():
    assert D.doc["path"] == "accu" and D.doc["title"] == "Accu" and D.doc["icon"] == "mdi:home-battery"
    assert D.doc["panel"] is True and len(D.doc["cards"][0]["cards"][0]["cards"]) == 3
    grafiek = [k for k in D.alle if k.get("type") == "custom:apexcharts-card" and k.get("span", {}).get("start") == "day"]
    assert len(grafiek) == 1 and [s["entity"] for s in grafiek[0]["series"]] == [
        "sensor.slimhuys_zonneplan_prijzen_vandaag_kwartier", "sensor.accu_lading"]
    acties = [k.get("tap_action", {}).get("action") for k in D.alle]
    assert not [a for a in acties if a in ("perform-action", "call-service", "toggle")]


def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    for naam in D.namen():
        schoon(D.render(naam, states))
    ids = set(re.findall(r"\b(?:sensor|binary_sensor|number|select)\.[a-z0-9_]+[a-z0-9]\b", RUW))
    ontbreekt = sorted(i for i in ids if i not in states)
    assert not ontbreekt, ontbreekt


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
