"""Offline test van de Klimaat-weergave in Server-stijl (dashboards/home/klimaat.yaml).

7 november 2026. Draaien:  python3 tests/test_klimaat_pagina.py   (nodig: pyyaml en node)

De logica van de klimaatregie zelf test tests/test_klimaat.py; dit bestand test
de weergave:
1. path/title/icon zijn gebleven, het is een panel-weergave met drie kolommen;
2. NIETS IS VERDWENEN: elke entiteit die de oude weergave (vóór 7-11-2026)
   toonde staat er nog, en alles wat je kon bedienen kan nog: elke schakelaar
   (input_boolean/switch) heeft een button-card met tap_action toggle, elk
   input_number een button-card of regel die more-info opent, en het regime
   een knop per optie;
3. de JS van elk paneel in node (tests/sv_render.py): normaal, problemen
   (storing, kwam niet vooruit, CO2, blokkade, regie uit, KNMI-code), lege
   states (geen exception, geen undefined/NaN) en ge-escapete state-tekst;
4. elke pop-up-hash waarnaar geklikt wordt bestaat als pop-up;
5. tegen /tmp/states.json (als die er is): elke gebruikte entiteit bestaat.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, Dashboard, kaarten, laad, st  # noqa: E402

PAD = os.path.join(CONFIG, "dashboards", "home", "klimaat.yaml")
D = Dashboard(PAD)
TEKST = open(PAD, encoding="utf-8").read()
REGIME = laad(os.path.join(CONFIG, "packages", "9 - Other", "Klimaat Regime.yaml"))["klimaat_regime_package"]

# Wat de oude weergave (sections, entities-kaarten; commit bb9c07a) toonde.
OUD = """
binary_sensor.knmi_waarschuwing binary_sensor.slaapkamer_logan_slaapkamer_maxi_beweging_bezetting
binary_sensor.slaapkamer_maxi_slaaptijd binary_sensor.zon_op_achtergevel binary_sensor.zon_op_voorgevel
binary_sensor.zon_op_zijgevel binary_sensor.zon_richting_achtergevel binary_sensor.zon_richting_voorgevel
binary_sensor.zon_richting_zijgevel climate.airco_woonkamer climate.airco_zolder
counter.airco_storingen_woonkamer counter.airco_storingen_zolder cover.achtertuin_zonnescherm
cover.badkamer_rolluik_langzaam cover.covers_bedroom_maxi cover.covers_kitchen_screens
cover.kantoor_links_langzaam cover.kantoor_rechts_langzaam cover.rollerblind_0001 cover.rollerblind_0002
cover.slaapkamer_mini cover.slaapkamer_rolluik_langzaam input_boolean.airco_handmatig_woonkamer
input_boolean.airco_handmatig_zolder input_boolean.airco_storing_woonkamer input_boolean.airco_storing_zolder
input_boolean.aircoregie_actief input_boolean.klimaat_nachtspui input_boolean.klimaat_regime_handmatig
input_boolean.klimaat_wakker input_boolean.klimaatregie_actief input_boolean.zonwering_handmatig_badkamer
input_boolean.zonwering_handmatig_kantoor_links input_boolean.zonwering_handmatig_kantoor_rechts
input_boolean.zonwering_handmatig_keuken_rolgordijn_groot input_boolean.zonwering_handmatig_keuken_rolgordijn_klein
input_boolean.zonwering_handmatig_keuken_screens input_boolean.zonwering_handmatig_slaapkamer
input_boolean.zonwering_handmatig_slaapkamer_emma input_boolean.zonwering_handmatig_slaapkamer_logan
input_boolean.zonwering_handmatig_zonnescherm input_number.airco_start_temp_woonkamer
input_number.airco_start_temp_zolder input_number.klimaat_airco_aan_delta input_number.klimaat_airco_uit_delta
input_number.klimaat_airco_voorkoelen_min input_number.klimaat_gevel_breedte input_number.klimaat_hittedag_vanaf
input_number.klimaat_kamer_koud input_number.klimaat_kamer_warm input_number.klimaat_kier_positie
input_number.klimaat_koelen_vanaf input_number.klimaat_override_uren input_number.klimaat_screen_max_regen
input_number.klimaat_screen_max_wind input_number.klimaat_spui_delta input_number.klimaat_verwachte_max
input_number.klimaat_verwarmen_tot input_number.klimaat_voorgevel_richting input_number.klimaat_zijgevel_richting
input_number.klimaat_zon_lux_drempel input_number.klimaat_zon_min_elevatie input_select.klimaat_regime
sensor.achtertuin_zon_luminance sensor.airco_advies_woonkamer sensor.airco_advies_zolder
sensor.klimaat_zon_azimut sensor.klimaat_zon_elevatie sensor.knmi_temperatuur sensor.robin_reistijd_naar_huis
sensor.samantha_reistijd_naar_huis sensor.slaapkamer_logan_slaapkamer_maxi_beweging_licht
sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_kooldioxide
sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_luchtkwaliteit
sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_luchtvochtigheid
sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_pm2_5
sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_temperatuur
sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur sensor.temperatuur_boven_gemiddeld
sensor.voortuin_zon_luminance sensor.woonkamer_woonkamer_multisensor_temperatuur sensor.zonwering_advies_badkamer
sensor.zonwering_advies_kantoor_links sensor.zonwering_advies_kantoor_rechts
sensor.zonwering_advies_keuken_rolgordijn_groot sensor.zonwering_advies_keuken_rolgordijn_klein
sensor.zonwering_advies_keuken_screens sensor.zonwering_advies_slaapkamer sensor.zonwering_advies_slaapkamer_emma
sensor.zonwering_advies_slaapkamer_logan sensor.zonwering_advies_zonnescherm
switch.slaapkamer_logan_slaapkamer_maxi_multisensor_display timer.airco_kansloos_woonkamer
timer.airco_kansloos_zolder timer.airco_minimaal_aan_woonkamer timer.airco_minimaal_aan_zolder
timer.airco_override_woonkamer timer.airco_override_zolder timer.airco_rust_woonkamer timer.airco_rust_zolder
timer.airco_voortgang_woonkamer timer.airco_voortgang_zolder timer.override_badkamer timer.override_kantoor_links
timer.override_kantoor_rechts timer.override_keuken_rolgordijn_groot timer.override_keuken_rolgordijn_klein
timer.override_keuken_screens timer.override_slaapkamer timer.override_slaapkamer_emma
timer.override_slaapkamer_logan timer.override_zonnescherm timer.zonnescherm_vraag weather.knmi_thuis
""".split()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(t))


def basis():
    """Een rustige winterdag, zoals live op 7-11-2026."""
    s = {e: st("off") for e in OUD if e.split(".")[0] in ("input_boolean", "binary_sensor", "switch")}
    s.update({e: st("idle", duration="0:30:00") for e in OUD if e.startswith("timer.")})
    for z in ("keuken_screens", "keuken_rolgordijn_groot", "keuken_rolgordijn_klein", "kantoor_links",
              "kantoor_rechts", "badkamer", "slaapkamer", "slaapkamer_logan", "slaapkamer_emma", "zonnescherm"):
        s[f"sensor.zonwering_advies_{z}"] = st("rust", positie=-1, reden="nog niemand wakker gemeld", blokkade="advies is rust")
    for c in [e for e in OUD if e.startswith("cover.")]:
        s[c] = st("closed", current_position=0)
    s.update({
        "input_boolean.klimaatregie_actief": st("on"),
        "input_select.klimaat_regime": st("Verwarmen", options=["Neutraal", "Koelen", "Verwarmen"]),
        "input_number.klimaat_verwachte_max": st(10.0),
        "sensor.knmi_temperatuur": st(0.7),
        "weather.knmi_thuis": st("partlycloudy", wind_speed=12.6, wind_speed_unit="km/h"),
        "binary_sensor.knmi_waarschuwing": st("off", title="Er zijn geen waarschuwingen", description="-", code="groen"),
        "sensor.klimaat_zon_azimut": st(124.5), "sensor.klimaat_zon_elevatie": st(5.3),
        "sensor.voortuin_zon_luminance": st(804), "sensor.achtertuin_zon_luminance": st(1013),
        "sensor.airco_advies_woonkamer": st("rust", doel=21.5, reden="kamer in de band", blokkade=""),
        "sensor.airco_advies_zolder": st("off", doel=23.0, reden="raam open (Badkamer Raam)", blokkade="aircoregie staat uit"),
        "climate.airco_woonkamer": st("off", temperature=21), "climate.airco_zolder": st("cool", temperature=23.0),
        "sensor.woonkamer_woonkamer_multisensor_temperatuur": st(21.2), "sensor.temperatuur_boven_gemiddeld": st(17.4),
        "input_number.airco_start_temp_woonkamer": st(-20.0), "input_number.airco_start_temp_zolder": st(24.3),
        "counter.airco_storingen_woonkamer": st(0), "counter.airco_storingen_zolder": st(0),
        "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_temperatuur": st(17.35),
        "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_kooldioxide": st(850),
        "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_luchtvochtigheid": st(57.6),
        "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_pm2_5": st(6.0),
        "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_luchtkwaliteit": st("good"),
        "sensor.slaapkamer_logan_slaapkamer_maxi_beweging_licht": st(1.0),
        "sensor.slaapkamer_logan_slaapkamer_maxi_temperatuur_temperatuur": st(16.88),
        "binary_sensor.slaapkamer_maxi_slaaptijd": st("on", bedtijd_vandaag="21:30:00"),
    })
    return s


def schoon(h):
    for fout in ("undefined", "NaN", "[object", "null"):
        assert fout not in h, f"{fout} in de HTML"
    return h


# ------------------------------------------------------------------ 1. vorm
def test_vorm():
    assert D.doc["path"] == "klimaat" and D.doc["title"] == "Klimaat" and D.doc["icon"] == "mdi:home-thermometer"
    assert D.doc["panel"] is True
    raster = D.doc["cards"][0]["cards"][0]
    assert raster["type"] == "horizontal-stack" and len(raster["cards"]) == 3
    assert "grid-template-columns: 1fr 1fr 1fr" in raster["card_mod"]["style"]


# ------------------------------------------------- 2. niets is verdwenen
def klik_ids():
    ids = set()
    for n in D.namen():
        ids |= set(re.findall(r"entityId:'([a-z_]+\.[a-z0-9_]+)'", D.render(n, basis())))
    return ids


def test_niets_verdwenen():
    ids = klik_ids()
    weg = [e for e in OUD if e not in TEKST and e not in ids]
    assert not weg, f"verdwenen van de Klimaat-weergave: {weg}"


def bediening():
    """{entity: [tap_action, ...]} van alle button-cards met een entiteit."""
    uit = {}
    for k in D.alle:
        if k.get("type") == "custom:button-card" and k.get("entity"):
            uit.setdefault(k["entity"], []).append(k)
    return uit


def test_alles_nog_bedienbaar():
    b, ids = bediening(), klik_ids()
    for e in OUD:
        domein = e.split(".")[0]
        if domein in ("input_boolean", "switch"):
            assert any((k.get("tap_action") or {}).get("action") == "toggle" for k in b.get(e, [])), f"{e} niet om te zetten"
        elif domein == "input_number":
            assert e in ids or any((k.get("tap_action") or {}).get("action") == "more-info" for k in b.get(e, [])), f"{e} niet in te stellen"
        elif domein in ("climate", "cover", "timer"):
            assert e in ids, f"{e}: geen more-info (bediening/annuleren)"
    opties = REGIME["input_select"]["klimaat_regime"]["options"]
    gekozen = [k["tap_action"]["data"]["option"] for k in b["input_select.klimaat_regime"]
               if (k.get("tap_action") or {}).get("perform_action") == "input_select.select_option"]
    assert sorted(gekozen) == sorted(opties), gekozen
    for k in b["input_select.klimaat_regime"]:
        if (k.get("tap_action") or {}).get("perform_action"):
            assert k["tap_action"]["target"]["entity_id"] == "input_select.klimaat_regime"


# --------------------------------------------------------------- 3. de JS
def test_normaal():
    s = basis()
    h = schoon(D.render("regelaar", s))
    assert ">regie aan<" in h and "Verwarmen" in h and "10,0 °C" in h and "regime automatisch" in h
    h = schoon(D.render("zonwering", s))
    assert ">volgt advies<" in h and h.count("Keuken screens") == 1 and "niet uitgevoerd" not in h
    assert "event.stopPropagation()" in h, "klik op de stand mag niet ook het advies openen"
    h = schoon(D.render("airco_woonkamer", s))
    assert "21,2°" in h and "doel 21,5°" in h and ">rust<" in h and "Temp. bij start" in h and "kwam niet vooruit" in h
    h = schoon(D.render("airco_zolder", s))
    assert "cool · 23,0°" in h and "24,3 °C" in h and "aircoregie staat uit" in h
    h = schoon(D.render("maxi", s))
    assert ">fris<" in h and "17,4°" in h and "850 ppm" in h and ">goed<" in h and "21:30" in h
    h = schoon(D.render("zon", s))
    assert ">geen waarschuwing<" in h and "0,7°" in h and "half bewolkt" in h and "13 km/h" in h and "geen zon" in h
    h = schoon(D.render("uitzonderingen", s))
    assert ">geen<" in h and h.count("timer.override_") == 10


def test_problemen():
    nu = time.time()
    s = {**basis(),
         "input_boolean.airco_storing_woonkamer": st("on"),
         "timer.airco_kansloos_zolder": st("active", finishes_at=iso(nu + 100 * 60)),
         "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_kooldioxide": st(2557),
         "sensor.zonwering_advies_kantoor_links": st("dicht", positie=0, reden="zon op voorgevel", blokkade="raam staat open"),
         "timer.override_badkamer": st("active", finishes_at=iso(nu + 2 * 3600)),
         "input_boolean.zonwering_handmatig_slaapkamer": st("on"),
         "binary_sensor.knmi_waarschuwing": st("on", title="Code oranje: storm", description="Zware windstoten", code="oranje")}
    assert ">storing<" in D.render("airco_woonkamer", s)
    h = D.render("airco_zolder", s)
    assert ">kwam niet vooruit<" in h and "nog 2 uur" in h
    h = D.render("maxi", s)
    assert "CO₂ 2.557" in h and "var(--ov-bad)" in h
    h = D.render("zonwering", s)
    assert ">1 niet uitgevoerd<" in h and "niet uitgevoerd: raam staat open" in h
    assert "hand · nog 2 uur" in h and ">handmatig<" in h and "2 zones met de hand" in h
    assert ">code oranje<" in D.render("zon", s) and "Zware windstoten" in D.render("zon", s)
    assert ">1 actief<" in D.render("uitzonderingen", s)
    assert ">regie uit<" in D.render("zonwering", {**s, "input_boolean.klimaatregie_actief": st("off")})
    assert ">regie uit<" in D.render("regelaar", {**s, "input_boolean.klimaatregie_actief": st("off")})


def test_lege_states():
    for n in D.namen():
        schoon(D.render(n, {}))
        schoon(D.render(n, {e: st("unavailable") for e in OUD}))
    assert ">geen meting<" in D.render("maxi", {})
    assert ">3 meldingen<" not in D.render("zonwering", {}) and "10 zonder advies" in D.render("zonwering", {})


def test_escaping():
    kwaad = "<img src=x onerror=alert(1)>"
    s = {**basis(),
         "sensor.zonwering_advies_badkamer": st(kwaad, positie=-1, reden=kwaad, blokkade=kwaad),
         "sensor.airco_advies_woonkamer": st(kwaad, doel=21, reden=kwaad, blokkade=kwaad),
         "climate.airco_woonkamer": st(kwaad),
         "input_select.klimaat_regime": st(kwaad),
         "weather.knmi_thuis": st(kwaad, wind_speed_unit=kwaad, wind_speed=3),
         "binary_sensor.knmi_waarschuwing": st("on", title=kwaad, description=kwaad, code=kwaad),
         "sensor.slaapkamer_logan_slaapkamer_maxi_multisensor_luchtkwaliteit": st(kwaad),
         "binary_sensor.slaapkamer_maxi_slaaptijd": st("on", bedtijd_vandaag=kwaad)}
    for n in D.namen():
        h = D.render(n, s)
        assert "<img" not in h, n


# ------------------------------------------------------------ 4. pop-ups
def test_popups():
    pp = {k["hash"] for k in D.alle if k.get("type") == "custom:bubble-card" and k.get("card_type") == "pop-up"}
    doelen = set(re.findall(r"#klimaat-[a-z-]+", TEKST))
    assert doelen and doelen <= pp, f"klik naar een pop-up die er niet is: {doelen - pp}"
    for k in D.alle:
        if k.get("type") == "custom:bubble-card" and any(c.get("type") == "custom:apexcharts-card" for c in k["cards"]):
            spans = [c["graph_span"] for c in k["cards"]]
            assert spans == ["4h", "24h"], k["hash"]
            assert k["cards"][0]["series"] == k["cards"][1]["series"], k["hash"]


def test_zones_en_units_compleet():
    # Zelfde lijst als variables.zones van het zonweringpaneel en de pop-up.
    zones = [z["z"] for z in D.kaart("zonwering")["variables"]["zones"]]
    assert zones == [z["z"] for z in D.kaart("uitzonderingen")["variables"]["zones"]]
    for z in zones:
        assert f"input_boolean.zonwering_handmatig_{z}" in TEKST and f"sensor.zonwering_advies_{z}" in TEKST


# ------------------------------------------------------------ 5. live
def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    gebruikt = set(re.findall(r"\b((?:sensor|binary_sensor|input_boolean|input_number|input_select|switch|climate|cover|timer|counter|weather)\.[a-z0-9_]+)\b", TEKST))
    gebruikt |= klik_ids()
    gebruikt -= {"sensor.time"} if "sensor.time" not in states else set()
    # Prefixen (`p: sensor.x_`) en acties (`perform_action: x.y`) zijn geen entiteiten.
    acties = set(re.findall(r"perform_action: (\S+)", TEKST))
    gebruikt = {e for e in gebruikt if not e.endswith("_") and e not in acties}
    weg = sorted(e for e in gebruikt if e not in states)
    assert not weg, f"bestaat niet (meer): {weg}"
    for n in D.namen():
        schoon(D.render(n, states))


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
