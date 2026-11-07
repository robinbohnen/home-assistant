"""Gedeelde hulp voor de tests van de dashboards in Server-stijl (7 november 2026).

Laadt een dashboardbestand (HA-tags genegeerd), lost button-card-templates op
uit dashboards/home/overzicht_templates.yaml, en draait de JS van een kaart in
node met www/sv-kit.js geladen en nagebootste `states`.

    from sv_render import Dashboard, st
    D = Dashboard("dashboards/home/klimaat.yaml")
    html = D.render("klimaat_nu", {"sensor.x": st(21.5)})

Een kaart wordt gevonden op `variables.kaart` (zelfde afspraak als server.yaml).
"""
import json
import os
import subprocess

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(CONFIG, "www", "sv-kit.js")
TEMPLATES = os.path.join(CONFIG, "dashboards", "home", "overzicht_templates.yaml")


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def laad(pad):
    with open(pad, encoding="utf-8") as f:
        return yaml.load(f, Loader=HALoader)


def st(state, **attrs):
    return {"state": str(state), "attributes": attrs}


def kaarten(knoop):
    """Alle kaarten in de boom, ook in stacks, mod-cards, grids en pop-ups."""
    if isinstance(knoop, dict):
        if "type" in knoop:
            yield knoop
        for waarde in knoop.values():
            yield from kaarten(waarde)
    elif isinstance(knoop, list):
        for item in knoop:
            yield from kaarten(item)


TPL = laad(TEMPLATES)


def met_templates(kaart):
    """Kaart met de velden van zijn templates eronder (kaart wint)."""
    keten, todo = [], kaart.get("template")
    todo = [todo] if isinstance(todo, str) else list(todo or [])
    while todo:
        t = TPL.get(todo.pop(0))
        if t:
            keten.append(t)
            sub = t.get("template")
            todo += [sub] if isinstance(sub, str) else list(sub or [])
    uit = {}
    for laag in reversed(keten):
        for k, v in laag.items():
            if isinstance(v, dict) and isinstance(uit.get(k), dict):
                uit[k] = {**uit[k], **v}
            else:
                uit[k] = v
    for k, v in kaart.items():
        if isinstance(v, dict) and isinstance(uit.get(k), dict):
            uit[k] = {**uit[k], **v}
        else:
            uit[k] = v
    return uit


def js_van(tekst):
    x = tekst.strip()
    assert x.startswith("[[[") and x.endswith("]]]"), x[:40]
    return x[3:-3]


def run_js(code, states, variables=None, entity_id=None, hass=None):
    """Draai een button-card-template (zonder [[[ ]]]) in node met sv-kit geladen.

    `hass`: extra velden voor het hass-object (bv. entities, devices, areas);
    `hass.states` is altijd `states`.
    """
    prog = (
        "globalThis.window = globalThis;"
        "require(%s);"
        "const states = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "const variables = %s; const entity = states[%s];"
        "const hass = Object.assign(%s, {states: states}); const user = {name: 'Test'};"
        "const out = (function(){ %s })(); process.stdout.write(String(out));"
        % (json.dumps(KIT), json.dumps(variables or {}), json.dumps(entity_id), json.dumps(hass or {}), code)
    )
    r = subprocess.run(["node", "-e", prog], input=json.dumps(states),
                       capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    return r.stdout


class Dashboard:
    def __init__(self, pad):
        self.pad = pad if os.path.isabs(pad) else os.path.join(CONFIG, pad)
        self.doc = laad(self.pad)
        self.alle = list(kaarten(self.doc))

    def kaart(self, naam):
        for k in self.alle:
            if (k.get("variables") or {}).get("kaart") == naam:
                return met_templates(k)
        raise AssertionError(f"kaart {naam} niet gevonden in {self.pad}")

    def namen(self):
        return [(k.get("variables") or {}).get("kaart") for k in self.alle
                if (k.get("variables") or {}).get("kaart")]

    def render(self, naam, states, veld="x", hass=None):
        k = self.kaart(naam)
        return run_js(js_van(k["custom_fields"][veld]), states, k.get("variables"), k.get("entity"), hass)
