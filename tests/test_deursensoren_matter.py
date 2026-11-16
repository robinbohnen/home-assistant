"""Offline test van de overstap van twee deursensoren naar Matter (16 november 2026).

Draaien:  python3 tests/test_deursensoren_matter.py      (nodig: pyyaml)
          of: python3 -m pytest tests/test_deursensoren_matter.py

De magneetcontacten op de badkamerdeur en de deur van Maxi zijn vervangen door
Matter-varianten (waren Zigbee via zigbee2mqtt):

    binary_sensor.badkamer_deur_contact
        -> binary_sensor.badkamer_badkamer_deur_deur
    binary_sensor.slaapkamer_maxi_deur_contact
        -> binary_sensor.slaapkamer_logan_slaapkamer_maxi_deur_deur

Een automatisering op een entity-id die niet meer bestaat, gaat stil kapot:
geen fout, geen trigger. Daarom bewaakt deze test:
1. geen enkel bestand in packages/, blueprints/, dashboards/ en custom_*
   noemt de oude id's nog;
2. de plekken die op deze deuren leunen, gebruiken de nieuwe id's: de
   badkamerverlichting en -media, de bedtijdsensor, de deur-tijdens-bedtijd-
   automatisering van Maxi, Mini's "lichten uit bij deur dicht", Kinderen
   wakker en de deurengroep van het brandalarm;
3. alle YAML-bestanden die ze noemen, zijn nog geldig;
4. (live, als /tmp/states.json er is) beide nieuwe id's bestaan echt. Die
   staat er omdat de eerste versie van deze overstap een GERADEN id voor Maxi
   gebruikte (`slaapkamer_maxi_slaapkamer_maxi_deur_deur`); het apparaat
   staat in HA in de ruimte "Slaapkamer Logan", dus de id begint daarmee.
   Alle offline controles hierboven waren groen terwijl vier automatiseringen
   op een niet-bestaande entiteit hingen.
"""
import os

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPEN = ["packages", "blueprints", "dashboards", "custom_templates", "custom_sentences"]

OUD = ["binary_sensor.badkamer_deur_contact", "binary_sensor.slaapkamer_maxi_deur_contact"]
BADKAMER = "binary_sensor.badkamer_badkamer_deur_deur"
MAXI = "binary_sensor.slaapkamer_logan_slaapkamer_maxi_deur_deur"

VERWACHT = {
    "packages/1 - First Floor/Bathroom/Lights.yaml": [BADKAMER],
    "packages/1 - First Floor/Bathroom/Media.yaml": [BADKAMER],
    "packages/1 - First Floor/Bedroom Maxi/Bedtime.yaml": [MAXI],
    "packages/1 - First Floor/Bedroom Maxi/Door Opened During Bedtime Maxi.yaml": [MAXI],
    "packages/2 - Second Floor/Bedroom Mini/Lights.yaml": [BADKAMER],
    "packages/9 - Other/Kinderen Wakker.yaml": [MAXI],
    "packages/9 - Other/Firealarm.yaml": [BADKAMER, MAXI],
    "dashboards/home/dashboard.yaml": [BADKAMER, MAXI],
    "dashboards/home/overzicht.yaml": [BADKAMER, MAXI],
}


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include, !input en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def bestanden():
    for map_ in MAPPEN:
        for wortel, _, namen in os.walk(os.path.join(CONFIG, map_)):
            for naam in namen:
                if naam.endswith((".yaml", ".yml", ".jinja", ".js")):
                    yield os.path.join(wortel, naam)


def lees(pad):
    with open(pad, encoding="utf-8") as f:
        return f.read()


def test_oude_ids_nergens_meer():
    fout = []
    for pad in bestanden():
        tekst = lees(pad)
        # Uitleg in commentaar mag de oude naam noemen; echte verwijzingen niet.
        for nr, regel in enumerate(tekst.splitlines(), 1):
            code = regel.split("#", 1)[0] if regel.lstrip().startswith("#") else regel
            if any(o in code for o in OUD):
                fout.append(f"{os.path.relpath(pad, CONFIG)}:{nr}: {regel.strip()}")
    assert not fout, "oude Zigbee-id nog in gebruik:\n" + "\n".join(fout)


def test_nieuwe_ids_op_alle_bekende_plekken():
    for rel, ids in VERWACHT.items():
        tekst = lees(os.path.join(CONFIG, rel))
        for e in ids:
            assert e in tekst, f"{e} ontbreekt in {rel}"


def test_bestanden_nog_geldige_yaml():
    for rel in VERWACHT:
        with open(os.path.join(CONFIG, rel), encoding="utf-8") as f:
            yaml.load(f, Loader=HALoader)


def test_deurengroep_brandalarm():
    with open(os.path.join(CONFIG, "packages/9 - Other/Firealarm.yaml"), encoding="utf-8") as f:
        doc = yaml.load(f, Loader=HALoader)
    groepen = [g for g in doc["firealarm_package"]["binary_sensor"] if g.get("unique_id") == "all_doors"]
    assert len(groepen) == 1
    leden = groepen[0]["entities"]
    assert BADKAMER in leden and MAXI in leden
    assert len(leden) == len(set(leden)), "dubbele deur in de groep"


def test_live_ids_bestaan():
    import json
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        live = {e["entity_id"]: e for e in json.load(f)}
    for e in (BADKAMER, MAXI):
        assert e in live, f"{e} bestaat niet in Home Assistant"
        assert live[e]["attributes"].get("device_class") == "door", e
    for e in OUD:
        # De oude Zigbee-entiteiten mogen nog bestaan (tot ze in z2m weg zijn),
        # maar dan alleen als `unavailable`: een levende oude sensor betekent
        # dat de overstap niet is wat we denken.
        if e in live:
            assert live[e]["state"] == "unavailable", f"{e} leeft nog: {live[e]['state']}"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print(f"ok  {naam}")
    print(f"{len(tests)} tests geslaagd")
