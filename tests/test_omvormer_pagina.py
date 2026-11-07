"""Offline test van de Omvormer-pagina (dashboards/home/omvormer.yaml), 4 november 2026.

Draaien:  python3 tests/test_omvormer_pagina.py      (nodig: PyYAML en node)

Sinds 7 november 2026 in Server-stijl (docs/dashboard-stijl.md): de JS van de
panelen draait via tests/sv_render.py met www/sv-kit.js en de templates uit
overzicht_templates.yaml. Bewaakt de omzetting van MarkeDroid naar Solarman:
- de ZON-tegel toont de twee strings (ZW · O);
- IN ORDE? leest spanning en frequentie van de Deye (`inverter_grid_*`),
  de omvormertemperatuur en de meldingen (`binary_sensor.omvormer_storing`);
- de verbinding noemt welke bron stil is (Solarman en/of MarkeDroid);
- in de hele pagina staat geen MarkeDroid-meetwaarde meer, alleen regie,
  exportbegrenzer, flex en verbinding.
En de Server-stijl:
- de ruwe tabellen (sv_uitlegtabel) tonen elke regel, filteren leesfouten,
  tellen weggevallen waarden in de badge en escapen state-tekst;
- elke klik-hash heeft een pop-up met 4 en 24 uur en dezelfde reeksen;
- geen bediening: geen tap-acties die iets uitvoeren;
- (als /tmp/states.json er is) elke gebruikte entiteit bestaat en elk paneel
  rendert zonder undefined/NaN.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, Dashboard, st  # noqa: E402

PAGINA = os.path.join(CONFIG, "dashboards", "home", "omvormer.yaml")
with open(PAGINA, encoding="utf-8") as f:
    RUW = f.read()
D = Dashboard(PAGINA)

BASIS = {
    "sensor.zon_vermogen_nu": st(1433, unit_of_measurement="W"),
    "sensor.zon_vermogen_zw": st(1008, unit_of_measurement="W", piekvermogen=5406),
    "sensor.zon_vermogen_o": st(425, unit_of_measurement="W", piekvermogen=4054),
    "sensor.meterkast_slimhuys_zonneplan_netto_vermogen": st(1065, unit_of_measurement="W"),
    "sensor.accu_vermogen": st(-58, unit_of_measurement="W"),
    "sensor.accu_status": st("ontladen"),
    "sensor.accu_lading": st(74, unit_of_measurement="%"),
    "sensor.huis_verbruik": st(2.55, unit_of_measurement="kW"),
    "sensor.markedroid_regie": st("vasthouden", omschrijving="vasthouden, alleen laden"),
    "binary_sensor.markedroid_verbinding": st("on"),
    "binary_sensor.inverter_connection": st("on"),
    "binary_sensor.huis_op_accu": st("off", oorzaak="stroomstoring"),
    "sensor.inverter_grid_l1_voltage": st(230.5, unit_of_measurement="V"),
    "sensor.inverter_grid_l2_voltage": st(231.7, unit_of_measurement="V"),
    "sensor.inverter_grid_l3_voltage": st(228.9, unit_of_measurement="V"),
    "sensor.inverter_grid_frequency": st(50.01, unit_of_measurement="Hz"),
    "sensor.accu_temperatuur": st(20.6, unit_of_measurement="°C"),
    "sensor.inverter_temperature": st(50.7, unit_of_measurement="°C"),
    "binary_sensor.omvormer_storing": st("off", omschrijving="geen"),
}


def render(naam="nu", **extra):
    states = dict(BASIS)
    for k, v in extra.items():
        k = k.replace("__", ".", 1)
        if v is None:
            states.pop(k, None)
        else:
            states[k] = v
    return D.render(naam, states)


def tekst(html):
    return re.sub(r"<[^>]+>", "", html)


def schoon(h):
    assert h and "undefined" not in h and "NaN" not in h, h[:300]
    return h


# ------------------------------------------------------------- NU + IN ORDE?
def test_zon_per_string():
    assert "ZW 1 kW · O 425 W" in tekst(render())


def test_zon_zonder_strings():
    assert "alle panelen" in tekst(render(sensor__zon_vermogen_zw=None, sensor__zon_vermogen_o=None))


def test_net_van_de_deye():
    assert "229–232 V · 50,01 Hz" in tekst(render())


def test_temperatuur_omvormer_erbij():
    assert "accu 20,6 °C · omvormer 51 °C" in tekst(render())


def test_omvormer_te_warm_is_waarschuwing():
    html = render(sensor__inverter_temperature=st(70, unit_of_measurement="°C"))
    assert "var(--ov-warn)" in html and ">temperatuur<" in html


def test_storing_in_rood():
    html = render(binary_sensor__omvormer_storing=st("on", omschrijving="melding: Fan failure"))
    assert "var(--ov-bad)\">melding: Fan failure" in html


def test_verbinding_beide():
    h = render()
    assert "Solarman · MarkeDroid" in tekst(h) and ">in orde<" in h


def test_verbinding_solarman_stil():
    assert "Solarman stil" in tekst(render(binary_sensor__inverter_connection=st("off")))


def test_verbinding_beide_stil():
    t = tekst(render(binary_sensor__inverter_connection=st("off"), binary_sensor__markedroid_verbinding=st("off")))
    assert "Solarman en MarkeDroid stil" in t


def test_leesfout_wordt_gefilterd():
    # 65.286 W = -250 W zonder teken; 2e9 = onzin.
    h = tekst(render(sensor__accu_vermogen=st(65286, unit_of_measurement="W"),
                     sensor__zon_vermogen_nu=st(2e9, unit_of_measurement="W")))
    assert "250 W" in h and "ZON—" in h.replace(" ", "")


def test_alles_weg_geen_exception():
    schoon(D.render("nu", {}))
    schoon(D.render("per_fase", {}))
    for naam in ("markedroid", "zon", "accu", "net", "omvormer"):
        schoon(D.render(naam, {}))


def test_nu_klikt_naar_popups():
    h = render()
    for hsh in ("#omv-zon", "#omv-net", "#omv-accu", "#omv-huis", "#omv-temp"):
        assert "navigation_path:'%s'" % hsh in h, hsh
    assert "entityId:'sensor.markedroid_regie'" in h


# ------------------------------------------------------------------ tabellen
def test_tabel_twee_kolommen_en_alle_regels():
    k = D.kaart("net")
    h = D.render("net", {
        "sensor.inverter_grid_l1_power": st(871, unit_of_measurement="W"),
        "sensor.inverter_grid_l2_power": st(65286, unit_of_measurement="W"),
        "sensor.inverter_grid_l3_power": st(3e9, unit_of_measurement="W"),
        "sensor.inverter_grid_frequency": st(50, unit_of_measurement="Hz"),
        "sensor.inverter_load_ups_power": st("unavailable", unit_of_measurement="W"),
    })
    assert "repeat(2,minmax(0,1fr))" in h
    assert h.count("border-top:1px solid") >= len(k["variables"]["rijen"])
    t = tekst(h)
    assert "871 · -250 · leesfout W" in t and "50,00 Hz" in t and "P1 loopt ~10 s achter" in t
    # Weg en leesfout tellen in de badge.
    assert ">2 meldingen<" in h and "bestaat niet" in t
    assert "repeat(1,minmax(0,1fr))" in D.render("markedroid", {})


def test_tabel_vertaling_en_escaping():
    kwaad = "<img src=x onerror=alert(1)>"
    h = D.render("accu", {"sensor.inverter_battery_state": st("charging")})
    assert ">laden<" in h or "laden</span>" in h
    h = D.render("omvormer", {"select.inverter_work_mode": st(kwaad), "sensor.inverter_device_alarm": st(kwaad)})
    assert "<img" not in h and "&lt;img" in h
    h = D.render("markedroid", {"sensor.markedroid_regie": st("x", omschrijving=kwaad)})
    assert "<img" not in h


def test_state_tekst_in_nu_wordt_ge_escaped():
    kwaad = "<img src=x onerror=alert(1)>"
    h = render(sensor__markedroid_regie=st(kwaad, omschrijving=kwaad),
               binary_sensor__omvormer_storing=st("on", omschrijving=kwaad))
    assert "<img" not in h and "&lt;img" in h


# ------------------------------------------------------------ pop-ups, opbouw
def popups():
    return {k["hash"]: k for k in D.alle if k.get("type") == "custom:bubble-card" and k.get("card_type") == "pop-up"}


def test_elke_klik_hash_heeft_een_popup():
    pp = popups()
    gebruikt = set(re.findall(r"#omv-[a-z-]+", RUW))
    assert gebruikt == set(pp), (gebruikt, set(pp))
    for h, p in pp.items():
        assert [c["graph_span"] for c in p["cards"]] == ["4h", "24h"], h
        assert p["cards"][0]["series"] == p["cards"][1]["series"], h
        func = p["cards"][1]["all_series_config"]["group_by"]["func"]
        assert func == ("max" if h == "#omv-temp" else "avg"), h


def test_schil_en_pad():
    assert D.doc["path"] == "omvormer" and D.doc["panel"] is True
    rij = D.doc["cards"][0]["cards"][0]
    assert rij["type"] == "horizontal-stack" and len(rij["cards"]) == 3


def test_alleen_lezen():
    acties = [k.get("tap_action", {}).get("action") for k in D.alle]
    assert not [a for a in acties if a in ("perform-action", "call-service", "toggle")]


def test_geen_markedroid_meetwaarden_meer():
    toegestaan = {"sensor.markedroid_regie", "sensor.markedroid_exportbegrenzer",
                  "sensor.markedroid_flex_vermogen", "binary_sensor.markedroid_verbinding",
                  "binary_sensor.markedroid_flex_actief", "binary_sensor.markedroid_negatieve_prijs"}
    gevonden = set(re.findall(r"(?:binary_)?sensor\.markedroid_[a-z0-9_]+", RUW))
    assert gevonden <= toegestaan, gevonden - toegestaan


def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    for naam in D.namen():
        schoon(D.render(naam, states))
    ids = set(re.findall(r"\b(?:sensor|binary_sensor|number|select)\.[a-z0-9_]+[a-z0-9]\b", RUW))
    # Opgebouwde id's (l' + f + '_voltage) vallen af; die staan voluit in triggers_update.
    ids = {i for i in ids if not re.search(r"_l$|_$", i)}
    ontbreekt = sorted(i for i in ids if i not in states)
    assert not ontbreekt, ontbreekt


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
