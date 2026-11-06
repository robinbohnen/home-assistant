"""Offline test: de garageklok en de pixelwall in de garage gaan samen aan en uit.

Draaien:  .venv/bin/python tests/test_garage_schermen.py      (nodig: pyyaml)

`klokken_garage_matrix_beweging` in packages/9 - Other/Klokken.yaml zet de
Ulanzi TC001 in de garage aan bij beweging en uit na twee minuten stilte, bij
het alarm en na een herstart. De pixelwall in de garage hoort exact dezelfde
momenten te volgen. Bewaakt wordt:
1. elke tak die de garageklok aan- of uitzet, doet dat ook met de pixelwall,
   met dezelfde actie (een tak die de een aanzet en de ander niet, laat een
   scherm branden in een lege garage);
2. de aan-tak geeft geen helderheid mee: beide schermen houden hun eigen stand;
3. de pixelwall wordt nergens anders in de config aan- of uitgezet, zodat er
   geen tweede automatisering tegen deze regel in werkt.
"""
import os
import re

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLOKKEN = f"{CONFIG}/packages/9 - Other/Klokken.yaml"
KLOK = "light.garage_klok_awtrix_garage_matrix"
PIXELWALL = "light.garage_pixelwall_garage"


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def automation():
    with open(KLOKKEN, encoding="utf-8") as f:
        pkg = yaml.load(f, Loader=HALoader)["klokken_package"]
    for a in pkg["automation"]:
        if a.get("id") == "klokken_garage_matrix_beweging":
            return a
    raise AssertionError("klokken_garage_matrix_beweging niet gevonden")


def lijst(x):
    return x if isinstance(x, list) else [x]


def licht_acties(sequence):
    for stap in sequence:
        if str(stap.get("action", "")).startswith("light."):
            yield stap


def test_elke_tak_schakelt_beide_schermen():
    takken = automation()["actions"][-1]["choose"]
    assert len(takken) == 4, [t.get("alias") for t in takken]
    for tak in takken:
        acties = list(licht_acties(tak["sequence"]))
        assert acties, f"{tak['alias']}: geen licht-actie"
        for stap in acties:
            doelen = lijst(stap["target"]["entity_id"])
            assert KLOK in doelen and PIXELWALL in doelen, (tak["alias"], doelen)


def test_aan_zonder_helderheid():
    takken = automation()["actions"][-1]["choose"]
    aan = [s for t in takken for s in licht_acties(t["sequence"])
           if s["action"] == "light.turn_on"]
    assert len(aan) == 1
    assert not aan[0].get("data"), aan[0].get("data")


def test_pixelwall_garage_nergens_anders_geschakeld():
    gevonden = []
    for map_, mappen, bestanden in os.walk(f"{CONFIG}/packages"):
        for b in bestanden:
            if not b.endswith(".yaml"):
                continue
            pad = os.path.join(map_, b)
            with open(pad, encoding="utf-8") as f:
                tekst = f.read()
            gevonden += [pad] * len(re.findall(re.escape(PIXELWALL), tekst))
    # één keer in de kopdocumentatie + vier takken
    assert gevonden.count(KLOKKEN) == 5, gevonden
    assert set(gevonden) == {KLOKKEN}, gevonden


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print("ok", naam)
