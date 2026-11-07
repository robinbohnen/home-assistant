"""Offline test van de deurbel-triggers.

Draaien:  .venv/bin/python tests/test_deurbel.py      (nodig: pyyaml)

UniFi Protect haalt `binary_sensor.g4_doorbell_voortuin_doorbell` weg in HA
2027.1; de bel komt nu van de event-entiteit `event.g4_doorbell_voortuin_doorbell`
via de trigger `event.received`. Bewaakt wordt:
1. nergens in de config staat de oude binary_sensor nog;
2. de drie dingen die op een bel reageren (Sonos-gong, slaapkamerlampen en de
   pil `binary_sensor.deurbel_recent`) triggeren met `event.received` op de
   event-entiteit en `event_type: ring`. Een gewone state-trigger op een
   event-entiteit zou ook vuren als hij na een herstart terugkomt uit
   unavailable, en dan gaat midden in de nacht de gong;
3. de bel-popup op het oude dashboard opent op `binary_sensor.deurbel_recent`.
"""
import os

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUD = "binary_sensor.g4_doorbell_voortuin_doorbell"
EVENT = "event.g4_doorbell_voortuin_doorbell"
VERWACHTE_TRIGGER = {
    "trigger": "event.received",
    "target": {"entity_id": EVENT},
    "options": {"event_type": "ring"},
}


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def laad(rel):
    with open(f"{CONFIG}/{rel}", encoding="utf-8") as f:
        return next(iter(yaml.load(f, Loader=HALoader).values()))


def automatisering(rel, auto_id):
    return next(a for a in laad(rel)["automation"] if a.get("id") == auto_id)


def test_oude_binary_sensor_nergens_meer():
    resten = []
    for map_, mappen, bestanden in os.walk(CONFIG):
        mappen[:] = [m for m in mappen if not m.startswith(".") and m != "tests"]
        for b in bestanden:
            # README.md legt de overstap uit en noemt de oude id dus bewust.
            if b.endswith((".yaml", ".jinja", ".md")) and b != "README.md":
                pad = os.path.join(map_, b)
                with open(pad, encoding="utf-8") as f:
                    if OUD in f.read():
                        resten.append(os.path.relpath(pad, CONFIG))
    assert not resten, f"{OUD} nog in gebruik: {resten}"


def test_sonos_gong():
    a = automatisering("packages/0 - Ground Floor/Livingroom/Doorbell.yaml", "livingroom_doorbell")
    assert a["triggers"] == [VERWACHTE_TRIGGER]


def test_slaapkamerlampen():
    a = automatisering("packages/1 - First Floor/Bedroom/Lights.yaml", "bedroom_lights_doorbell")
    assert a["triggers"] == [VERWACHTE_TRIGGER]


def test_deurbel_recent():
    blokken = laad("packages/9 - Other/Dashboard Context.yaml")["template"]
    (blok,) = [
        b for b in blokken
        if any(s.get("unique_id") == "deurbel_recent" for s in b.get("binary_sensor", []))
    ]
    assert blok["trigger"] == [VERWACHTE_TRIGGER]


def test_popup_oude_dashboard():
    with open(f"{CONFIG}/dashboards/home/dashboard.yaml", encoding="utf-8") as f:
        tekst = f.read()
    blok = tekst[tekst.index('hash: "#doorbell"'):]
    blok = blok[:blok.index("card_type: pop-up")]
    assert "entity: binary_sensor.deurbel_recent" in blok


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
