"""Klikken in button-card-HTML komt aan, op elk dashboard. 7 november 2026.

Draaien:  python3 tests/test_button_card_klikbaar.py      (nodig: PyYAML)

button-card zet op een kaart zonder eigen actie (tap, hold en double tap
allemaal `none`) de class `disabled`, en die is `pointer-events: none`. Elke
`onclick` in de HTML van zo'n kaart (more-info, een pop-up openen) doet dan
stilletjes niets. Dat zat op het Server-dashboard, de Omvormer-pagina en het
template `ov_uitlegtabel`.

De oplossing is `- pointer-events: auto` in `styles: card:` (inline wint van
de class), of `pointer-events:auto` op het klikbare element zelf zoals
dashboards/home/systeem.yaml doet. Deze test loopt alle dashboards na, met de
templates uit dashboards/home/overzicht_templates.yaml erbij, en faalt op
een kaart met een onclick zonder een van beide.
"""
import glob
import os

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARDS = os.path.join(CONFIG, "dashboards")
TEMPLATES = os.path.join(DASHBOARDS, "home", "overzicht_templates.yaml")


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def laad(pad):
    with open(pad, encoding="utf-8") as f:
        return yaml.load(f, Loader=HALoader)


TPL = laad(TEMPLATES)


def keten(kaart):
    """De kaart en zijn templates (ook geneste), kaart eerst."""
    uit, todo = [kaart], kaart.get("template")
    todo = [todo] if isinstance(todo, str) else list(todo or [])
    while todo:
        t = TPL.get(todo.pop(0))
        if not t:
            continue
        uit.append(t)
        sub = t.get("template")
        todo += [sub] if isinstance(sub, str) else list(sub or [])
    return uit


def veld(kaart, sleutel):
    for k in keten(kaart):
        if sleutel in k:
            return k[sleutel]
    return None


def heeft_actie(kaart):
    for a in ("tap_action", "hold_action", "double_tap_action"):
        w = veld(kaart, a)
        # Geen tap_action = button-card kiest zelf toggle of more-info.
        if a == "tap_action" and w is None:
            return True
        if w and w.get("action", "none") != "none":
            return True
    return False


def klikken_aan(kaart):
    for k in keten(kaart):
        for d in (k.get("styles") or {}).get("card") or []:
            if isinstance(d, dict) and d.get("pointer-events") == "auto":
                return True
    return False


def html(kaart):
    return "".join(str(k.get("custom_fields") or "") for k in keten(kaart))


def button_cards(knoop):
    if isinstance(knoop, dict):
        if knoop.get("type") == "custom:button-card" or (knoop is not None and "custom_fields" in knoop):
            yield knoop
        for w in knoop.values():
            yield from button_cards(w)
    elif isinstance(knoop, list):
        for w in knoop:
            yield from button_cards(w)


def test_onclick_komt_aan():
    fout = []
    gezien = 0
    for pad in sorted(glob.glob(os.path.join(DASHBOARDS, "**", "*.yaml"), recursive=True)):
        doc = laad(pad)
        bron = [doc] if pad != TEMPLATES else []   # templates zelf via de kaarten die ze gebruiken
        for kaart in (k for b in bron for k in button_cards(b)):
            h = html(kaart)
            if "onclick" not in h or heeft_actie(kaart):
                continue
            gezien += 1
            # Uitzondering: elk klikbaar element zet het zelf aan (systeem.yaml).
            elementen = h.count("onclick")
            if klikken_aan(kaart) or h.count("pointer-events:auto") >= elementen:
                continue
            fout.append(f"{os.path.relpath(pad, CONFIG)}: {kaart.get('template') or (kaart.get('variables') or {}).get('kaart') or kaart.get('entity')}")
    assert gezien, "geen enkele kaart gevonden: test kijkt verkeerd"
    assert not fout, "onclick zonder pointer-events: auto:\n  " + "\n  ".join(fout)


def test_detectie():
    # De test zelf: een kaart zoals het Server-dashboard vóór de fix valt op.
    kapot = {"type": "custom:button-card", "tap_action": {"action": "none"},
             "styles": {"card": [{"background": "none"}]},
             "custom_fields": {"x": "[[[ return '<div onclick=\"x\">'; ]]]"}}
    assert not heeft_actie(kapot) and not klikken_aan(kapot)
    goed = {**kapot, "styles": {"card": [{"pointer-events": "auto"}]}}
    assert klikken_aan(goed)
    # Template-overerving: ov_uitlegtabel moet het voor zijn gebruikers regelen.
    assert klikken_aan({"type": "custom:button-card", "template": "ov_uitlegtabel"})
    assert heeft_actie({"type": "custom:button-card"})   # standaard toggle/more-info


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
