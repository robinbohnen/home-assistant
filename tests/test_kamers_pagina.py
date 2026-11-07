"""Offline test van de Kamers-pagina (dashboards/home/kamers.yaml), 7 november 2026.

Draaien:  python3 tests/test_kamers_pagina.py      (nodig: pyyaml en node)

De jinja erachter (welke kamer welke status krijgt) test tests/test_kamers.py;
deze test draait de JS van de panelen (templates `kamer_verdieping`,
`kamer_detail`, `kamer_onderhoud`, `kamer_onderhoud_lijst` in
overzicht_templates.yaml) in node met www/sv-kit.js. Bewaakt wordt:
1. elke verdieping uit de KAMERS-tabel in kamers.jinja heeft een paneel, en
   elke kamer een pop-up met dezelfde slug (`_` in de hash wordt `-`);
2. het paneel per verdieping: kamers van die verdieping, badge (in orde / de
   ene kamer / n kamers), temperatuur alleen gekleurd als hij de uitschieter
   is, alleen gemeten waarden in de strip, de klik naar de pop-up;
3. de pop-up noemt per waarde de bron (klikbaar) en wat er niet gemeten wordt;
4. zonder sensor.kamers: geen exception, een duidelijke melding;
5. state-tekst wordt ge-escaped;
6. (live) alles tegen /tmp/states.json als die er is.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, Dashboard, js_van, met_templates, run_js, st  # noqa: E402

D = Dashboard("dashboards/home/kamers.yaml")
JINJA = os.path.join(CONFIG, "custom_templates", "kamers.jinja")
POPUPS = {k["hash"]: k for k in D.alle if k.get("card_type") == "pop-up"}


def kamer(slug, verdieping, status="goed", temp=21.3, tscore=0, **extra):
    m = [
        {"k": "co2", "label": "CO₂", "w": extra.pop("co2", None), "eenheid": "", "score": extra.pop("co2score", 0), "id": "sensor.co2_" + slug, "oud": False},
        {"k": "temp", "label": "temp", "w": temp, "eenheid": "°", "score": tscore, "id": "sensor.temp_" + slug, "oud": False},
        {"k": "rv", "label": "RV", "w": extra.pop("rv", 48.0), "eenheid": "%", "score": 0, "id": "sensor.rv_" + slug, "oud": False},
        {"k": "lux", "label": "licht", "w": None, "eenheid": "", "score": -1, "id": "", "oud": False},
    ]
    k = {"slug": slug, "naam": slug.replace("_", " ").title(), "icoon": "mdi:sofa-outline", "verdieping": verdieping,
         "status": status, "reden": "fris" if status == "goed" else "te warm", "advies": "" if status == "goed" else "raam open",
         "metingen": m, "gekoppeld": 3, "beweging": {"gemeten": True, "actief": False, "minuten": 12},
         "contacten": {"gemeten": True, "open": 0, "totaal": 2, "namen": []}}
    k.update(extra)
    return k


def states(*kamers, los=None):
    s = {"sensor.kamers": st("ok", kamers=list(kamers))}
    s["sensor.kamers_niet_gekoppeld"] = st(len(los or []), sensoren=los or [])
    return s


def detail(slug, s):
    k = met_templates({"type": "custom:button-card", "template": "kamer_detail", "variables": {"slug": slug}})
    return run_js(js_van(k["custom_fields"]["x"]), s, k["variables"], k.get("entity"))


def onderhoud_lijst(s):
    k = met_templates({"type": "custom:button-card", "template": "kamer_onderhoud_lijst"})
    return run_js(js_van(k["custom_fields"]["x"]), s, k.get("variables"), k.get("entity"))


def jinja_kamers():
    """(slug, verdieping) uit de KAMERS-tabel in kamers.jinja."""
    with open(JINJA, encoding="utf-8") as f:
        t = f.read()
    return re.findall(r"\{'slug': '([a-z_]+)'.*?'verdieping': '([^']+)'", t, re.S)


# ------------------------------------------------------------ 1. opbouw
def test_verdiepingen_en_popups():
    panelen = {D.kaart(n)["variables"]["verdieping"] for n in D.namen()
               if D.kaart(n).get("template") == "kamer_verdieping"}
    tabel = jinja_kamers()
    assert len(tabel) >= 17
    assert {v for _, v in tabel} == panelen, "elke verdieping uit kamers.jinja heeft precies één paneel"
    for slug, _ in tabel:
        h = "#kamer-" + slug.replace("_", "-")
        assert h in POPUPS, f"{slug}: geen pop-up {h}"
        assert POPUPS[h]["cards"][0]["variables"]["slug"] == slug
    assert "#kamers-onderhoud" in POPUPS
    for h in POPUPS:
        assert re.fullmatch(r"#[a-z0-9-]+", h), f"sv-kit opent alleen hashes van a-z0-9-: {h}"
    # De paden waar meldingen en de header naar wijzen.
    assert D.doc["path"] == "kamers" and D.doc["title"] == "Kamers"


# ------------------------------------------------------ 2. paneel per verdieping
def test_verdieping_normaal():
    s = states(kamer("woonkamer", "Begane grond", co2=612), kamer("keuken", "Begane grond"),
               kamer("zolder", "Tweede verdieping"))
    h = D.render("begane_grond", s)
    assert "BEGANE GROND" in h and ">in orde<" in h
    assert ">Woonkamer<" in h and ">Keuken<" in h and "Zolder" not in h
    assert "21,3°" in h and "612" in h and "CO₂" in h and "48%" in h
    assert "lx" not in h, "licht wordt niet gemeten en hoort niet in de strip"
    assert "navigation_path:'#kamer-woonkamer'" in h and "12 min geleden" in h and "alles dicht" in h
    # Temperatuur zonder uitschieter in tekstkleur, niet groen.
    assert "var(--primary-text-color)\">21,3°" in h


def test_verdieping_problemen():
    s = states(kamer("slaapkamer_logan", "Eerste verdieping", status="let op", temp=24.8, tscore=1),
               kamer("kantoor", "Eerste verdieping"))
    h = D.render("eerste_verdieping", s)
    assert ">slaapkamer logan<" in h and "var(--ov-warn)\">24,8°" in h and "te warm · raam open" in h
    assert "navigation_path:'#kamer-slaapkamer-logan'" in h
    s = states(kamer("slaapkamer_logan", "Eerste verdieping", status="slecht"),
               kamer("kantoor", "Eerste verdieping", status="let op"))
    h = D.render("eerste_verdieping", s)
    assert ">2 kamers<" in h and "var(--ov-bad-15)" in h
    # "geen meting" is geen probleem voor de badge, wel grijs op de regel.
    s = states(kamer("kantoor", "Eerste verdieping", status="geen meting", temp=None))
    h = D.render("eerste_verdieping", s)
    assert ">in orde<" in h and "var(--ov-ink-25)" in h and "NaN" not in h


def test_kamer_zonder_sensor_en_beweging():
    k = kamer("schuur", "Buiten", temp=None, rv=None, gekoppeld=0,
              beweging={"gemeten": True, "actief": True, "minuten": 0},
              contacten={"gemeten": True, "open": 2, "totaal": 3, "namen": ["Deur", "Raam"]})
    h = D.render("buiten", states(k))
    assert "nu aanwezig" in h and "2 open" in h and "—" not in h, "zonder sensor geen streepje"
    k = kamer("voortuin", "Buiten", beweging={"gemeten": False}, contacten={"gemeten": False})
    h = D.render("buiten", states(k))
    assert "geen melder" in h and "geen contact" in h


def test_zonder_sensor_kamers():
    for s in ({}, {"sensor.kamers": st("unavailable")}):
        h = D.render("begane_grond", s)
        assert "geen data" in h and "sensor.kamers heeft nog geen waarde" in h
        assert "geen data" in detail("woonkamer", s)
        h = D.render("onderhoud", s)
        assert "undefined" not in h and "NaN" not in h


# ------------------------------------------------------------- 3. pop-up
def test_detail():
    k = kamer("woonkamer", "Begane grond", status="let op", co2=1450, co2score=2)
    h = detail("woonkamer", states(k))
    assert "METINGEN" in h and ">let op<" in h and "te warm" in h and "raam open" in h
    assert "sensor.co2_woonkamer" in h and "entityId:'sensor.co2_woonkamer'" in h
    assert "var(--ov-bad)\"><span>1.450" in h
    assert "Niet gemeten: licht." in h and "alles dicht (2)" in h
    leeg = kamer("zolder", "Tweede verdieping", temp=None, rv=None, gekoppeld=0)
    assert "geen sensor gekoppeld" in detail("zolder", states(leeg))
    stil = kamer("zolder", "Tweede verdieping", temp=None, rv=None)
    assert "batterij of verbinding" in detail("zolder", states(stil))


def test_onderhoud():
    los = [{"kamer": "Woonkamer", "id": "sensor.airco_woonkamer_buiten", "naam": "Airco buiten"},
           {"kamer": "Woonkamer", "id": "sensor.tv_temp", "naam": "TV"},
           {"kamer": "Garage", "id": "sensor.vriezer", "naam": "Vriezer"}]
    h = D.render("onderhoud", states(los=los))
    assert ">3 niet gekoppeld<" in h and "navigation_path:'#kamers-onderhoud'" in h and ">Woonkamer<" in h
    h = onderhoud_lijst(states(los=los))
    assert "WOONKAMER" in h and "entityId:'sensor.vriezer'" in h and "Airco buiten" in h
    assert ">alles gekoppeld<" in D.render("onderhoud", states())


# ---------------------------------------------------------- 5. escaping
def test_state_tekst_wordt_ge_escaped():
    kwaad = "<img src=x onerror=alert(1)>"
    k = kamer("woonkamer", "Begane grond", status="let op", naam=kwaad, reden=kwaad, advies=kwaad, icoon='x" onmouseover="alert(1)',
              contacten={"gemeten": True, "open": 1, "totaal": 1, "namen": [kwaad]})
    k["metingen"][1]["id"] = "sensor.x'); alert(1); ('"
    for h in (D.render("begane_grond", states(k)), detail("woonkamer", states(k))):
        assert "<img" not in h and "&lt;img" in h and 'onmouseover="' not in h
        # Een id die geen entity-id is, wordt geen onclick (sv-kit weigert hem).
        assert "entityId:'sensor.x'" not in h and "alert(1); ('" not in h
    h = onderhoud_lijst(states(los=[{"kamer": kwaad, "id": "sensor.a\"b", "naam": kwaad}]))
    assert "<img" not in h and 'entityId:\'sensor.a"b' not in h


# ----------------------------------------------------------------- 6. live
def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        s = {e["entity_id"]: e for e in json.load(f)}
    for naam in D.namen():
        h = D.render(naam, s)
        assert h and "undefined" not in h and "NaN" not in h, naam
    for k in (s.get("sensor.kamers", {}).get("attributes", {}).get("kamers") or []):
        assert "#kamer-" + k["slug"].replace("_", "-") in POPUPS, f"{k['slug']}: zet een pop-up in kamers.yaml"
        h = detail(k["slug"], s)
        assert "undefined" not in h and "NaN" not in h, k["slug"]
    assert "undefined" not in onderhoud_lijst(s)


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
