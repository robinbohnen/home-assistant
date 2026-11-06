"""Offline test van de klok-app `net`: wat er nu over de P1-meter gaat.

Draaien:  .venv/bin/python tests/test_klok_net.py      (nodig: jinja2, pyyaml)

Rendert de macro uit custom_templates/klok.jinja met nagebootste HA-functies
en leest de bedrading letterlijk uit packages/9 - Other/Klokken.yaml.
Bewaakt wordt:
1. het frame is geldige JSON voor AWTRIX, met pijl en kleur per richting
   (omlaag/blauw = afname, omhoog/groen = teruglevering, geen pijl in rust);
2. het label botst nooit met de mast en de pijl (x 0..7) en blijft links
   van de indicatorstipjes (x 30..31), tot en met 99 kW;
3. een stille meter geeft een lege payload, zodat de app van de klok gaat;
4. het frame lijkt niet op `verbruik` (geen gele bliksem);
5. de lus van elke seconde kent alle drie de klokken, stopt als de app weg
   is en heeft een plafond; het 10 s-script stuurt `net` naar elke klok.
"""
import json
import os

import yaml
from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLOKKEN = f"{CONFIG}/packages/9 - Other/Klokken.yaml"
BRON = "sensor.meterkast_slimhuys_zonneplan_netto_vermogen"
STATES = {}


def ha_states(eid):
    return str(STATES.get(eid, "unknown"))


def ha_has_value(eid):
    return ha_states(eid) not in ("unknown", "unavailable", "")


def f_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


env = Environment(loader=FileSystemLoader(f"{CONFIG}/custom_templates"))
env.filters["float"] = f_float
env.globals.update(states=ha_states, has_value=ha_has_value)
TEMPLATE = "{% from 'klok.jinja' import net_frame %}{{ net_frame() }}"


def frame(watt):
    STATES.clear()
    STATES[BRON] = watt
    uit = env.from_string(TEMPLATE).render().strip()
    return json.loads(uit) if uit else None


def tekst(f):
    return next(d["dt"] for d in f["draw"] if "dt" in d)


def vlakken(f):
    return [d["df"] for d in f["draw"] if "df" in d]


def pijl(f):
    """De gekleurde vlakken naast de mast (x >= 5)."""
    return [v for v in vlakken(f) if v[0] >= 5]


def test_afname_blauw_pijl_omlaag():
    f = frame("1234")
    x, y, label, kleur = tekst(f)
    assert label == "1234W" and kleur == "#0A84FF"
    p = pijl(f)
    assert p and all(v[4] == "#0A84FF" for v in p)
    breedste = max(p, key=lambda v: v[2])
    assert breedste[1] == 4          # punt onderaan: omlaag


def test_teruglevering_groen_pijl_omhoog_zonder_minteken():
    f = frame("-2150.6")
    x, y, label, kleur = tekst(f)
    assert label == "2151W" and kleur == "#32D74B"
    breedste = max(pijl(f), key=lambda v: v[2])
    assert breedste[1] == 3          # punt bovenaan: omhoog


def test_rust_wit_zonder_pijl():
    for w in ("0", "9", "-9"):
        f = frame(w)
        assert tekst(f)[3] == "#FFFFFF"
        assert pijl(f) == []


def test_boven_10_kw_hele_kw():
    assert tekst(frame("11400"))[2] == "11kW"
    assert tekst(frame("-9999.6"))[2] == "10kW"


def test_label_botst_nergens():
    for w in ("5", "999", "9999", "-9999", "10000", "56789", "99000"):
        f = frame(w)
        x, y, label, kleur = tekst(f)
        breedte = sum({".": 2, "W": 6}.get(t, 4) for t in label)
        assert x >= 9, (w, label, x)            # vrij van mast en pijl
        # Een tekenbreedte is inclusief een kolom tussenruimte, dus het laatste
        # getekende pixel ligt op x + breedte - 2 (zie het zonneframe).
        assert x + breedte - 2 <= 29, (w, label)  # vrij van de stipjes
    for v in vlakken(frame("-3000")):
        assert v[0] + v[2] - 1 <= 7 and v[1] + v[3] - 1 <= 7


def test_stille_meter_haalt_app_weg():
    assert frame("unavailable") is None
    assert frame("unknown") is None


def test_niet_te_verwarren_met_verbruik():
    f = frame("800")
    assert all(v[4] != "#FFD60A" for v in vlakken(f))
    assert f["duration"] == 8 and f["lifetime"] == 300


# --- bedrading in Klokken.yaml ----------------------------------------------

with open(KLOKKEN, encoding="utf-8") as fh:
    PAKKET = yaml.safe_load(fh)["klokken_package"]


def test_lus_kent_alle_klokken_en_stopt():
    auto = next(a for a in PAKKET["automation"] if a["id"] == "klokken_net_live")
    assert auto["mode"] == "parallel"
    ids = {t["id"]: t["entity_id"] for t in auto["triggers"]}
    assert ids == {
        "clock_1": "sensor.awtrix_121d6c_current_app",
        "clock_2": "sensor.awtrix_9c6510_current_app",
        "clock_3": "sensor.awtrix_9bf654_current_app",
    }
    assert all(t["to"] == "net" for t in auto["triggers"])
    lus = next(a["repeat"] for a in auto["actions"] if "repeat" in a)
    voorwaarde = lus["while"][0]["value_template"]
    assert "repeat.index <= 30" in voorwaarde
    assert "is_state(trigger.entity_id, 'net')" in voorwaarde
    publish = lus["sequence"][0]["data"]
    assert publish["topic"] == "{{ trigger.id }}/custom/net"
    assert "net_frame()" in publish["payload"]
    assert lus["sequence"][1]["delay"]["seconds"] == 1


def test_script_stuurt_net_naar_elke_klok():
    stappen = PAKKET["script"]["klok_zon_en_accu"]["sequence"]
    variabelen = {k: v for s in stappen for k, v in (s.get("variables") or {}).items()}
    assert "net_frame()" in variabelen["net_payload"]
    lus = next(s["repeat"] for s in stappen if "repeat" in s)
    net = [s for s in lus["sequence"] if s.get("data", {}).get("topic", "").endswith("/custom/net")]
    assert len(net) == 1 and "if" not in net[0]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for naam, f in tests:
        f()
        print("OK  ", naam)
