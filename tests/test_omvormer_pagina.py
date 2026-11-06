"""Offline test van de Omvormer-pagina (dashboards/home/omvormer.yaml), 4 november 2026.

Draaien:  .venv/bin/python tests/test_omvormer_pagina.py      (nodig: PyYAML en node)

Haalt de button-card-JS van de NU- en de IN ORDE?-kaart letterlijk uit de YAML
en draait die in node met nagebootste `states`. Bewaakt de omzetting van
MarkeDroid naar Solarman:
- de ZON-tegel toont de twee strings (ZW · O);
- IN ORDE? leest spanning en frequentie van de Deye (`inverter_grid_*`),
  de omvormertemperatuur en de meldingen (`binary_sensor.omvormer_storing`);
- de verbinding noemt welke bron stil is (Solarman en/of MarkeDroid);
- in de hele pagina staat geen MarkeDroid-meetwaarde meer, alleen regie,
  exportbegrenzer, flex en verbinding.
"""
import json
import os
import re
import subprocess

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGINA = os.path.join(CONFIG, "dashboards", "home", "omvormer.yaml")

with open(PAGINA, encoding="utf-8") as f:
    RUW = f.read()
    DOC = yaml.safe_load(RUW)


def _kaart_js(kop):
    for sectie in DOC["sections"]:
        for kaart in sectie.get("cards", []):
            x = (kaart.get("custom_fields") or {}).get("x", "")
            if f">{kop}</div>" in x:
                x = x.strip()
                assert x.startswith("[[[") and x.endswith("]]]")
                return x[3:-3]
    raise AssertionError(f"kaart {kop} niet gevonden")


NU = _kaart_js("NU")
IN_ORDE = _kaart_js("IN ORDE?")


def st(state, **attrs):
    return {"state": str(state), "attributes": attrs}


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


def render(js, **extra):
    states = dict(BASIS)
    for k, v in extra.items():
        k = k.replace("__", ".", 1)
        if v is None:
            states.pop(k, None)
        else:
            states[k] = v
    prog = ("const states = " + json.dumps(states) + ";\n"
            "process.stdout.write((function(){" + js + "})());")
    return subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True).stdout


def tekst(html):
    return re.sub(r"<[^>]+>", "", html)


def test_zon_per_string():
    assert "ZW 1 kW · O 425 W" in tekst(render(NU))


def test_zon_zonder_strings():
    assert "alle panelen" in tekst(render(NU, sensor__zon_vermogen_zw=None, sensor__zon_vermogen_o=None))


def test_net_van_de_deye():
    t = tekst(render(IN_ORDE))
    assert "229–232 V · 50,01 Hz" in t


def test_temperatuur_omvormer_erbij():
    t = tekst(render(IN_ORDE))
    assert "accu 20,6 °C · omvormer 51 °C" in t


def test_omvormer_te_warm_is_waarschuwing():
    html = render(IN_ORDE, sensor__inverter_temperature=st(70, unit_of_measurement="°C"))
    assert "var(--ov-warn)" in html


def test_storing_in_rood():
    html = render(IN_ORDE, binary_sensor__omvormer_storing=st("on", omschrijving="melding: Fan failure"))
    assert "var(--ov-bad)\">melding: Fan failure" in html


def test_verbinding_beide():
    assert "Solarman · MarkeDroid" in tekst(render(IN_ORDE))


def test_verbinding_solarman_stil():
    t = tekst(render(IN_ORDE, binary_sensor__inverter_connection=st("off")))
    assert "Solarman stil" in t


def test_verbinding_beide_stil():
    t = tekst(render(IN_ORDE, binary_sensor__inverter_connection=st("off"),
                     binary_sensor__markedroid_verbinding=st("off")))
    assert "Solarman en MarkeDroid stil" in t


def test_geen_markedroid_meetwaarden_meer():
    toegestaan = {"sensor.markedroid_regie", "sensor.markedroid_exportbegrenzer",
                  "sensor.markedroid_flex_vermogen", "binary_sensor.markedroid_verbinding",
                  "binary_sensor.markedroid_flex_actief", "binary_sensor.markedroid_negatieve_prijs"}
    gevonden = set(re.findall(r"(?:binary_)?sensor\.markedroid_[a-z0-9_]+", RUW))
    assert gevonden <= toegestaan, gevonden - toegestaan


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
