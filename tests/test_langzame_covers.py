"""Offline test van de langzame rolluiken (`cover.*_langzaam`).

Draaien:  .venv/bin/python tests/test_langzame_covers.py      (nodig: pyyaml)

Overkiz haalt de `cover.*_low_speed`-entiteiten weg in HA 2027.5. Hun opvolgers
zijn de template-covers in packages/9 - Other/Covers.yaml, die de gewone
entiteit spiegelen en met `speed: slow` aansturen (waarom eigen entiteiten: zie
de kop daar). Bewaakt wordt:
1. nergens in de config staat nog een `cover.*_low_speed`;
2. elke `cover.*_langzaam` die ergens gebruikt wordt, is ook gedefinieerd;
3. elke langzame cover stuurt de gewone entiteit aan (niet zichzelf), en open,
   dicht en positie gaan alle drie met `speed: slow` - één vergeten regel en
   dat rolluik gaat weer op volle snelheid;
4. stand, positie en beschikbaarheid komen van diezelfde gewone entiteit;
5. de cover-groepen die op dashboards staan bevatten alleen langzame leden,
   want een cover-group geeft `speed` niet door.
"""
import os
import re

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = f"{CONFIG}/packages/9 - Other/Covers.yaml"
GROEPEN = [
    f"{CONFIG}/packages/1 - First Floor/Office/Covers.yaml",
    f"{CONFIG}/packages/1 - First Floor/Bedroom Maxi/Covers.yaml",
]
RAMEN = {
    "kantoor_links", "kantoor_rechts", "badkamer_rolluik",
    "slaapkamer_rolluik", "slaapkamer_maxi_links", "slaapkamer_maxi_rechts",
}


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def laad(pad):
    with open(pad, encoding="utf-8") as f:
        return yaml.load(f, Loader=HALoader)


def config_bestanden():
    for map_, mappen, bestanden in os.walk(CONFIG):
        mappen[:] = [m for m in mappen if not m.startswith(".") and m != "tests"]
        for b in bestanden:
            if b.endswith((".yaml", ".jinja", ".md")):
                yield os.path.join(map_, b)


def alle_tekst():
    for pad in config_bestanden():
        with open(pad, encoding="utf-8") as f:
            yield pad, f.read()


def langzame_covers():
    pakket = next(iter(laad(COVERS).values()))
    return {
        c["default_entity_id"]: c
        for blok in pakket["template"]
        for c in blok.get("cover", [])
        if c["default_entity_id"].endswith("_langzaam")
    }


def test_geen_low_speed_meer():
    resten = [
        f"{os.path.relpath(p, CONFIG)}: {m}"
        for p, t in alle_tekst()
        for m in re.findall(r"cover\.[a-z0-9_]+_low_speed", t)
    ]
    assert not resten, f"Overkiz low_speed-entiteit nog in gebruik: {resten}"


def test_gebruikte_langzame_covers_bestaan():
    gedefinieerd = set(langzame_covers())
    assert gedefinieerd == {f"cover.{r}_langzaam" for r in RAMEN}
    onbekend = {
        m
        for _, t in alle_tekst()
        for m in re.findall(r"cover\.[a-z0-9_]+_langzaam", t)
    } - gedefinieerd
    assert not onbekend, f"gebruikt maar niet gedefinieerd: {onbekend}"


def test_stuurt_gewone_entiteit_langzaam():
    for eid, c in langzame_covers().items():
        gewoon = eid.removesuffix("_langzaam")
        for sleutel, actie in [
            ("open_cover", "cover.open_cover"),
            ("close_cover", "cover.close_cover"),
            ("set_cover_position", "cover.set_cover_position"),
        ]:
            (stap,) = c[sleutel]
            assert stap["action"] == actie, (eid, sleutel)
            assert stap["target"]["entity_id"] == gewoon, (eid, sleutel)
            assert stap["data"]["speed"] == "slow", (eid, sleutel)
        assert c["set_cover_position"][0]["data"]["position"] == "{{ position }}"
        (stop,) = c["stop_cover"]
        assert stop["action"] == "cover.stop_cover"
        assert stop["target"]["entity_id"] == gewoon


def test_spiegelt_gewone_entiteit():
    for eid, c in langzame_covers().items():
        gewoon = eid.removesuffix("_langzaam")
        for sleutel in ("availability", "state", "position"):
            assert f"'{gewoon}'" in c[sleutel], (eid, sleutel)
            assert eid not in c[sleutel], (eid, sleutel, "verwijst naar zichzelf")


def test_cover_groepen_alleen_langzaam():
    for pad in GROEPEN:
        pakket = next(iter(laad(pad).values()))
        for groep in pakket["cover"]:
            for lid in groep["entities"]:
                assert lid.endswith("_langzaam"), (pad, lid)


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
