"""Offline test van de MarkeDroid-regel onder de prijsstrook op de Nest Hub
(dashboards/home/nest_hub.yaml, kaart ENERGIE · NU, `custom_fields.strook`).

Draaien:  .venv/bin/python tests/test_nest_hub_markedroid.py      (nodig: PyYAML en node)

Haalt de button-card-JS letterlijk uit de YAML en draait die in node met
nagebootste `states`, net als tests/test_energie_nu.py. Bewaakt (29-10-2026):
dezelfde woorden en kleuren als op het Overzicht, rood bij "stil", weglaten
zonder regie-veld, en dat de regel er ook staat als er geen prijzen zijn.

Daarnaast de batterijtegel in de cijfers-rij (`custom_fields.cijfers`): groot
het accuvermogen in kW zonder teken, de lading klein erachter.

Sinds 31-10-2026 ook de veelgebruikers onder de MarkeDroid-regel (zelfde
indeling als "in huis" op het Overzicht) en dat de koppen van de vier
kwadranten op één hoogte staan (`align-content: space-between`).
"""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAART = os.path.join(CONFIG, "dashboards", "home", "nest_hub.yaml")


def _vind_veld(knoop, veld):
    """Zoek de ENERGIE · NU-kaart (die heeft een `strook`) en geef `veld` terug."""
    if isinstance(knoop, dict):
        velden = knoop.get("custom_fields") or {}
        if isinstance(velden.get("strook"), str):
            return velden[veld]
        knoop = list(knoop.values())
    if isinstance(knoop, list):
        for k in knoop:
            gevonden = _vind_veld(k, veld)
            if gevonden:
                return gevonden
    return None


with open(KAART, encoding="utf-8") as f:
    _DOC = yaml.safe_load(f)


def _js(veld):
    tekst = _vind_veld(_DOC, veld).strip()
    assert tekst.startswith("[[[") and tekst.endswith("]]]"), f"{veld} is geen button-card-JS meer"
    return tekst[3:-3]


JS = _js("strook")
CIJFERS = _js("cijfers")


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


def render(_js=None, **extra):
    states = dict(BASIS)
    for k, v in extra.items():
        states[k.replace("__", ".", 1)] = v
    prog = (
        "const states = " + json.dumps(states) + ";\n"
        "const variables = {laadvenster_uren: 3};\n"
        "const entity = states['sensor.live_energieverbruik_totaal'];\n"
        "process.stdout.write((function(){" + (_js or JS) + "})());"
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


def batterij(vermogen, lading=44, status="ontladen"):
    return render(CIJFERS,
                  sensor__accu_vermogen=st(vermogen),
                  sensor__accu_lading=st(lading),
                  sensor__accu_status=st(status),
                  sensor__live_energieverbruik_totaal=st(0.67),
                  sensor__zon_vermogen_nu=st(0, unit_of_measurement="W"))


def test_batterij_toont_kw_en_lading_klein():
    html = batterij(-120)
    # Ontladen is negatief (positief = laden), maar het label zegt al welke kant.
    assert ">0,12 <span" in html
    assert ">44%</span>" in html
    assert "batterij · ontlaadt" in html


def test_batterij_laden():
    html = batterij(2350, lading=61, status="laden")
    assert ">2,35 <span" in html and ">61%</span>" in html
    assert "batterij · laadt" in html


def test_batterij_zonder_vermogen():
    html = batterij("unavailable", lading=44)
    assert ">— <span" in html
    assert ">44%</span>" in html


def test_batterij_zonder_lading():
    html = batterij(-120, lading="unavailable")
    assert ">0,12</span>" in html
    assert "%</span>" not in html


def vg(totaal, top):
    return st(totaal, top=[{"naam": n, "watt": w} for n, w in top])


def test_veelgebruikers_onder_markedroid():
    html = render(sensor__markedroid_regie=regie("vasthouden"),
                  sensor__veelgebruikers_gemiddeld=vg(600, [("Koffiezetapparaat", 284), ("Serverrack", 46)]),
                  sensor__huis_verbruik_gemiddeld=st(700))
    assert html.index(">vasthouden</span>") < html.index("Koffiezetapparaat")
    assert "Koffiezetapparaat</span> <span" in html and ">284 W</span>" in html
    assert ">andere stekkers</span>" in html and ">270 W</span>" in html
    assert ">niet gemeten</span>" in html and ">100 W</span>" in html
    # Afkappen op twee regels, en afbreken mag (button-card zet nowrap).
    assert "-webkit-line-clamp:2" in html and "white-space:normal" in html


def test_veelgebruikers_drempel_en_maximaal_vijf():
    top = [("Stekker %d" % i, 100 - i) for i in range(7)] + [("Sluimer", 3)]
    html = render(sensor__veelgebruikers_gemiddeld=vg(700, top), sensor__huis_verbruik_gemiddeld=st(700))
    assert "Stekker 4" in html and "Stekker 5" not in html
    assert "Sluimer" not in html
    # Stekkers lopen voor op het huis: geen negatief "niet gemeten".
    assert "niet gemeten" not in html


def test_veelgebruikers_kw_en_terugval_op_ruwe_sensor():
    html = render(sensor__veelgebruikers_gemiddeld=st("unavailable"),
                  sensor__veelgebruikers=vg(1400, [("Waterkoker", 1360)]),
                  sensor__huis_verbruik=st(1500))
    assert ">1,4 kW</span>" in html
    assert ">100 W</span>" in html  # niet gemeten via de terugval huis_verbruik


def test_veelgebruikers_ook_zonder_prijzen():
    html = render(sensor__slimhuys_zonneplan_prijzen_vandaag=st("unavailable"),
                  sensor__veelgebruikers_gemiddeld=vg(300, [("Serverrack", 46)]))
    assert "geen prijsvoorspelling" in html and "Serverrack" in html


def test_zonder_stekkersensor_geen_regel():
    html = render(sensor__markedroid_regie=regie("vasthouden"))
    assert "stekkers" not in html and "line-clamp" not in html


def test_vier_koppen_op_dezelfde_hoogte():
    # space-evenly gaf elke kop een eigen gat erboven (31-10-2026); de kop moet
    # in elk kwadrant tegen de bovenpadding staan.
    with open(KAART, encoding="utf-8") as f:
        tekst = f.read()
    assert "align-content: space-evenly" not in tekst
    assert tekst.count("- align-content: space-between") == 4


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
