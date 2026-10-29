"""Offline test van de MarkeDroid-regel onder de prijsstrook op de Nest Hub
(dashboards/home/nest_hub.yaml, kaart ENERGIE · NU, `custom_fields.strook`).

Draaien:  .venv/bin/python tests/test_nest_hub_markedroid.py      (nodig: PyYAML en node)

Haalt de button-card-JS letterlijk uit de YAML en draait die in node met
nagebootste `states`, net als tests/test_energie_nu.py. Bewaakt (29-10-2026):
dezelfde woorden en kleuren als op het Overzicht, rood bij "stil", weglaten
zonder regie-veld, en dat de regel er ook staat als er geen prijzen zijn.
"""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAART = os.path.join(CONFIG, "dashboards", "home", "nest_hub.yaml")


def _vind_strook(knoop):
    if isinstance(knoop, dict):
        if "strook" in (knoop.get("custom_fields") or {}) and isinstance(knoop["custom_fields"]["strook"], str):
            return knoop["custom_fields"]["strook"]
        knoop = list(knoop.values())
    if isinstance(knoop, list):
        for k in knoop:
            gevonden = _vind_strook(k)
            if gevonden:
                return gevonden
    return None


with open(KAART, encoding="utf-8") as f:
    STROOK = _vind_strook(yaml.safe_load(f)).strip()
assert STROOK.startswith("[[[") and STROOK.endswith("]]]"), "strook is geen button-card-JS meer"
JS = STROOK[3:-3]


def st(state, **attrs):
    return {"state": str(state), "attributes": attrs}


def prijzen():
    """Uurblokken van een uur geleden tot morgen, zodat de strook tekent."""
    nu = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return [{"start": (nu + timedelta(hours=h)).isoformat(), "value": 0.30 + h / 100, "level": "high"}
            for h in range(-2, 14)]


BASIS = {
    "binary_sensor.markedroid_verbinding": st("on"),
    "sensor.markedroid_exportbegrenzer": st("uit"),
    "sensor.slimhuys_zonneplan_prijzen_vandaag": st("ok", raw_today=prijzen()),
}


def render(**extra):
    states = dict(BASIS)
    for k, v in extra.items():
        states[k.replace("__", ".", 1)] = v
    prog = (
        "const states = " + json.dumps(states) + ";\n"
        "const variables = {laadvenster_uren: 3};\n"
        "const entity = states['sensor.live_energieverbruik_totaal'];\n"
        "process.stdout.write((function(){" + JS + "})());"
    )
    uit = subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True)
    return uit.stdout


def regie(state, **attrs):
    attrs.setdefault("flex_w", None)
    return st(state, **attrs)


def test_vasthouden_in_accent():
    html = render(sensor__markedroid_regie=regie("vasthouden"))
    assert "MarkeDroid" in html
    assert ">vasthouden</span>" in html
    assert "var(--ov-accent)" in html


def test_eigen_verbruik_in_tekstkleur():
    html = render(sensor__markedroid_regie=regie("eigen_verbruik"))
    assert "eigen verbruik" in html
    assert "var(--ov-accent)" not in html


def test_flex_met_vermogen():
    assert "flex-opdracht 3,0 kW" in render(sensor__markedroid_regie=regie("flex", flex_w=3000))
    assert "flex-opdracht 800 W" in render(sensor__markedroid_regie=regie("flex", flex_w=800))
    assert "flex-opdracht</span>" in render(sensor__markedroid_regie=regie("flex"))


def test_teruglevering_dicht():
    html = render(sensor__markedroid_regie=regie("eigen_verbruik"),
                  sensor__markedroid_exportbegrenzer=st("actief"))
    assert "eigen verbruik · teruglevering dicht" in html


def test_stil_is_rood():
    html = render(sensor__markedroid_regie=regie("unavailable"),
                  binary_sensor__markedroid_verbinding=st("off"))
    assert ">stil</span>" in html
    assert "var(--ov-bad)" in html


def test_zonder_regie_veld_geen_regel():
    for stand in ("niet_geleverd", "unavailable"):
        assert "MarkeDroid" not in render(sensor__markedroid_regie=regie(stand)), stand


def test_strook_blijft_staan():
    html = render(sensor__markedroid_regie=regie("vasthouden"))
    assert "goedkoopst laden" in html
    assert ":00</div>" in html


def test_ook_zonder_prijzen():
    html = render(sensor__markedroid_regie=regie("vasthouden"),
                  sensor__slimhuys_zonneplan_prijzen_vandaag=st("unavailable"))
    assert "geen prijsvoorspelling" in html
    assert ">vasthouden</span>" in html


if __name__ == "__main__":
    import sys
    fouten = 0
    for naam, f in sorted(globals().items()):
        if naam.startswith("test_") and callable(f):
            try:
                f()
                print(f"ok    {naam}")
            except (AssertionError, subprocess.CalledProcessError) as e:
                fouten += 1
                print(f"FOUT  {naam}: {e}")
    sys.exit(1 if fouten else 0)
