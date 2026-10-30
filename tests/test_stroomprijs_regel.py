"""Offline test van de dagregel onder de STROOMPRIJS-grafiek (dashboards/home/overzicht/kolom_midden.yaml).

Draaien:  python3 tests/test_stroomprijs_regel.py      (nodig: PyYAML en node)

Haalt de button-card-JS (`custom_fields.regel` met het dagniveau) letterlijk uit
de YAML en draait die in node met nagebootste `states`, zoals in test_energie_nu.

Bewaakt het daggemiddelde (30-10-2026): gemiddelde over dezelfde blokken als
laag/hoog, kwartierprijzen gaan voor uurprijzen, en zonder prijzen geen "gem.".
"""
import json
import os
import subprocess

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAART = os.path.join(CONFIG, "dashboards", "home", "overzicht", "kolom_midden.yaml")


def _vind_regel(knoop):
    """Zoek het regel-veld dat het dagniveau van de stroomprijs tekent."""
    if isinstance(knoop, dict):
        regel = (knoop.get("custom_fields") or {}).get("regel")
        if isinstance(regel, str) and "zonneplan_dagniveau_vandaag" in regel:
            return regel
        knoop = list(knoop.values())
    if isinstance(knoop, list):
        for k in knoop:
            gevonden = _vind_regel(k)
            if gevonden:
                return gevonden
    return None


with open(KAART, encoding="utf-8") as f:
    REGEL = _vind_regel(yaml.safe_load(f)).strip()
assert REGEL.startswith("[[[") and REGEL.endswith("]]]"), "regel is geen button-card-JS meer"
JS = REGEL[3:-3]


def st(state, **attrs):
    return {"state": str(state), "attributes": attrs}


def blokken(prijzen, start="2026-10-30T00:00:00+01:00", minuten=60):
    from datetime import datetime, timedelta
    t0 = datetime.fromisoformat(start)
    return [{"start": (t0 + timedelta(minutes=i * minuten)).isoformat(),
             "end": (t0 + timedelta(minutes=(i + 1) * minuten)).isoformat(),
             "value": p, "level": "medium"} for i, p in enumerate(prijzen)]


def render(states):
    prog = (
        "const states = " + json.dumps(states) + ";\n"
        "process.stdout.write((function(){" + JS + "})());"
    )
    return subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True).stdout


def test_gemiddelde_vandaag():
    html = render({"sensor.slimhuys_zonneplan_prijzen_vandaag": st("ok", raw_today=blokken([0.40, 0.50, 0.60]))})
    assert "gem." in html
    assert "€ 0,500" in html
    assert "€ 0,400" in html and "€ 0,600" in html


def test_kwartier_gaat_voor_uur():
    html = render({
        "sensor.slimhuys_zonneplan_prijzen_vandaag": st("ok", raw_today=blokken([0.90, 0.90])),
        "sensor.slimhuys_zonneplan_prijzen_vandaag_kwartier": st("ok", raw_today=blokken([0.20, 0.30], minuten=15)),
    })
    assert "€ 0,250" in html
    assert "€ 0,900" not in html


def test_ongeldige_waarde_telt_niet_mee():
    html = render({"sensor.slimhuys_zonneplan_prijzen_vandaag": st("ok", raw_today=blokken([0.40, "x", 0.60]))})
    assert "€ 0,500" in html


def test_geen_prijzen_geen_gemiddelde():
    html = render({})
    assert "gem." not in html
    assert html.count("nog niet bekend") == 2


def test_morgen_eigen_gemiddelde():
    html = render({
        "sensor.slimhuys_zonneplan_prijzen_vandaag": st("ok", raw_today=blokken([0.40, 0.60])),
        "sensor.slimhuys_zonneplan_prijzen_morgen": st("ok", raw_tomorrow=blokken([0.10, 0.30], start="2026-10-31T00:00:00+01:00")),
    })
    assert html.count("gem.") == 2
    assert "€ 0,500" in html and "€ 0,200" in html


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_") and callable(fn):
            fn()
            print("ok ", naam)
