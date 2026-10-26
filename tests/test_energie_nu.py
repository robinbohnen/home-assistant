"""Offline test van de ENERGIE · NU-kaart (dashboards/home/overzicht/kolom_midden.yaml).

Draaien:  python3 tests/test_energie_nu.py      (nodig: PyYAML en node)

Haalt de button-card-JS (`custom_fields.flow`) letterlijk uit de YAML en draait
die in node met nagebootste `states`, net zoals button-card dat in de browser
doet. Zo testen we de echte code en geen kopie ervan.

Bewaakt vooral de MarkeDroid-stand achteraan de accuregel (26-10-2026):
korte woorden per stand, accentkleur bij ingrijpen, rood bij "stil", en
weglaten als er geen regie-veld is.
"""
import json
import os
import subprocess

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAART = os.path.join(CONFIG, "dashboards", "home", "overzicht", "kolom_midden.yaml")


def _vind_flow(knoop):
    """Zoek de button-card met entity sensor.huis_verbruik en een flow-veld."""
    if isinstance(knoop, dict):
        if knoop.get("entity") == "sensor.huis_verbruik" and "flow" in (knoop.get("custom_fields") or {}):
            return knoop["custom_fields"]["flow"]
        knoop = list(knoop.values())
    if isinstance(knoop, list):
        for k in knoop:
            gevonden = _vind_flow(k)
            if gevonden:
                return gevonden
    return None


with open(KAART, encoding="utf-8") as f:
    FLOW = _vind_flow(yaml.safe_load(f)).strip()
assert FLOW.startswith("[[[") and FLOW.endswith("]]]"), "flow is geen button-card-JS meer"
JS = FLOW[3:-3]


def st(state, **attrs):
    return {"state": str(state), "attributes": attrs}


BASIS = {
    "sensor.huis_verbruik": st(2.564, unit_of_measurement="kW"),
    "sensor.zon_vermogen_nu": st(1220, unit_of_measurement="W"),
    "sensor.live_energieverbruik_totaal": st(0.803),
    "sensor.accu_vermogen": st(1047),
    "sensor.accu_lading": st(68),
    "sensor.accu_status": st("ontladen"),
    "sensor.accu_capaciteit": st(51.2, afslag_procent=10),
    "binary_sensor.markedroid_verbinding": st("on"),
    "sensor.markedroid_exportbegrenzer": st("uit"),
}


def render(**extra):
    states = dict(BASIS)
    for k, v in extra.items():
        states[k.replace("__", ".", 1)] = v
    prog = (
        "const states = " + json.dumps(states) + ";\n"
        "const entity = states['sensor.huis_verbruik'];\n"
        "const hass = {states};\n"
        "process.stdout.write((function(){" + JS + "})());"
    )
    uit = subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True)
    return uit.stdout


def regie(state, **attrs):
    attrs.setdefault("flex_w", None)
    return st(state, **attrs)


def test_eigen_verbruik_in_inkt():
    html = render(sensor__markedroid_regie=regie("eigen_verbruik"))
    assert "MarkeDroid" in html
    assert "eigen verbruik</span>" in html
    assert "var(--primary-text-color)\">eigen verbruik" in html


def test_ingrijpen_in_accentkleur():
    html = render(sensor__markedroid_regie=regie("geforceerd_laden"))
    assert "var(--ov-accent)\">laadt van net" in html


def test_flex_met_vermogen():
    html = render(sensor__markedroid_regie=regie("flex", flex_w=3000))
    assert "flex-opdracht 3000 W" in html


def test_flex_zonder_vermogen():
    html = render(sensor__markedroid_regie=regie("flex"))
    assert "flex-opdracht</span>" in html


def test_exportbegrenzer_dicht():
    html = render(sensor__markedroid_regie=regie("eigen_verbruik"),
                  sensor__markedroid_exportbegrenzer=st("actief"))
    assert "eigen verbruik · teruglevering dicht" in html


def test_niet_geleverd_weggelaten():
    html = render(sensor__markedroid_regie=regie("niet_geleverd"))
    assert "MarkeDroid" not in html


def test_verlopen_weggelaten():
    html = render(sensor__markedroid_regie=regie("unavailable"))
    assert "MarkeDroid" not in html


def test_stil_in_rood():
    html = render(sensor__markedroid_regie=regie("unavailable"),
                  binary_sensor__markedroid_verbinding=st("off"))
    assert "var(--ov-bad)\">stil" in html


def test_zonder_markedroid_sensoren_geen_fout():
    states_zonder = {k: v for k, v in BASIS.items() if "markedroid" not in k}
    BASIS_OUD = dict(BASIS)
    BASIS.clear()
    BASIS.update(states_zonder)
    try:
        html = render()
    finally:
        BASIS.clear()
        BASIS.update(BASIS_OUD)
    assert "MarkeDroid" not in html
    assert "ontlaadt" in html  # de rest van de kaart blijft werken


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print("ok ", naam)
    print(f"{len(tests)} tests geslaagd")
