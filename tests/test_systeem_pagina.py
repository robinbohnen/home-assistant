"""Offline test van de Systeem-weergave (dashboards/home/systeem.yaml), 7 november 2026.

Draaien:  python3 tests/test_systeem_pagina.py      (nodig: pyyaml en node)

Sinds 7 november 2026 in Server-stijl (sv-kit, zie docs/dashboard-stijl.md).
De JS van de vier panelen (storingen, batterijen, waakhond, matter) draait in
node met nagebootste `states` en een nagebootst entiteiten-, apparaten- en
gebiedenregister (`hass.entities/devices/areas`). Bewaakt wordt:
1. de schil en maten zijn die van server.yaml, path/title/icon ongewijzigd;
2. storingen: vier bakken (storing, wees, afgeleid, ruis), alleen storing in
   de badge; per apparaat gegroepeerd; herstartcorrectie ("sinds herstart");
   zonder register een waarschuwing en groeperen op domein;
3. batterijen: bijna leeg en stil apart geteld, per apparaat; accu's en
   instellingen (number.) genegeerd; stil krijgt "hoe lang";
4. waakhond: kritieke sensoren en back-upleeftijd in de badge;
5. matter: oudste eerst, onbereikbaar in de badge, zonder register een melding;
6. klikken: apparaat -> apparaatpagina, losse entiteit -> more-info;
7. namen uit register en states worden ge-escaped; nergens undefined/NaN;
8. tegen een live dump in /tmp/states.json (overgeslagen als die er niet is).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import Dashboard, met_templates, st  # noqa: E402

D = Dashboard("dashboards/home/systeem.yaml")
NU = time.time()


def iso(sec_geleden):
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(NU - sec_geleden))


def ent(state, geleden=600, updated=None, **attrs):
    s = st(state, **attrs)
    s["last_changed"] = iso(geleden)
    s["last_updated"] = iso(updated if updated is not None else geleden)
    return s


GESTART = {"sensor.home_assistant_gestart": st(iso(5 * 3600))}

REG = {
    "entities": {
        "sensor.deur_temp": {"platform": "zha", "device_id": "dev1"},
        "sensor.deur_vocht": {"platform": "zha", "device_id": "dev1"},
        "light.oud": {"platform": "hue"},
        "sensor.lamp_power": {"platform": "powercalc"},
        "device_tracker.gast": {"platform": "unifi"},
        "sensor.verborgen": {"platform": "zha", "hidden_by": "user"},
        "sensor.knop_batterij": {"platform": "zha", "device_id": "dev2"},
        "binary_sensor.knop_batterij_laag": {"platform": "zha", "device_id": "dev2"},
        "sensor.sensor_batterij": {"platform": "zha", "device_id": "dev3"},
        "sensor.inverter_battery": {"platform": "solarman"},
        "number.auto_min_lading": {"platform": "renault"},
        "sensor.matter_a": {"platform": "matter", "device_id": "m1", "area_id": "keuken"},
        "light.matter_a": {"platform": "matter", "device_id": "m1"},
        "sensor.matter_b": {"platform": "matter", "device_id": "m2"},
    },
    "devices": {
        "dev1": {"name": "Deursensor", "area_id": "hal"},
        "dev2": {"name": "Knop", "name_by_user": "Knop bank"},
        "dev3": {"name": "Bewegingssensor"},
        "m1": {"name": "Matter stekker"},
        "m2": {"name": "Matter deur"},
    },
    "areas": {"hal": {"name": "Hal"}, "keuken": {"name": "Keuken"}},
}


def states_normaal():
    return {
        **GESTART,
        "sensor.time": st("10:00"),
        # storingen
        "sensor.deur_temp": ent("unavailable", 3 * 86400),
        "sensor.deur_vocht": ent("unavailable", 2 * 86400),
        "light.oud": ent("unavailable", 600, restored=True),
        "sensor.lamp_power": ent("unavailable"),
        "device_tracker.gast": ent("unavailable"),
        "sensor.verborgen": ent("unavailable"),
        # batterijen
        "sensor.knop_batterij": ent(18, device_class="battery", friendly_name="Knop batterij"),
        "binary_sensor.knop_batterij_laag": ent("on", device_class="battery"),
        "sensor.sensor_batterij": ent("unavailable", 2 * 3600, device_class="battery"),
        "sensor.inverter_battery": ent(5, device_class="battery"),
        "number.auto_min_lading": ent(20, device_class="battery"),
        "sensor.ok_batterij": ent(90, device_class="battery"),
        # matter
        "sensor.matter_a": ent(21, 30 * 3600),
        "light.matter_a": ent("on", 30 * 3600),
        "sensor.matter_b": ent("unavailable", 600),
        # waakhond
        "sensor.watchdog_kritieke_sensoren": st(0, namen=""),
        "sensor.watchdog_backup_leeftijd": st(0.4, laatste_backup="2026-11-07 05:29:04+01:00"),
    }


def schoon(h):
    assert h and "undefined" not in h and "NaN" not in h, h[:300]
    return h


# ------------------------------------------------------------------ 1. schil
def test_schil_zoals_server():
    doc = D.doc
    assert (doc["path"], doc["title"], doc["icon"]) == ("systeem", "Systeem", "mdi:heart-pulse")
    wortel = doc["cards"][0]["card_mod"]["style"]
    assert "gap: 0 !important" in wortel and "padding: 12px 16px !important" in wortel
    raster = doc["cards"][0]["cards"][0]["card_mod"]["style"]
    assert "gap: 12px !important" in raster and "1fr 1fr 1fr" in raster
    assert sorted(D.namen()) == ["batterijen", "matter", "storingen", "waakhond"]
    for naam in D.namen():
        k = met_templates(next(x for x in D.alle if (x.get("variables") or {}).get("kaart") == naam))
        stijl = {kk: v for d in k["styles"]["card"] for kk, v in d.items()}
        assert stijl["border-radius"] == "16px" and stijl["padding"] == "12px 16px", naam
    # Geen entities-kaart meer onder het raster: de waakhond is een paneel.
    assert not [k for k in D.alle if k.get("type") == "entities"]


# -------------------------------------------------------------- 2. storingen
def test_storingen():
    h = schoon(D.render("storingen", states_normaal(), hass=REG))
    # Storing: deursensor (2 entiteiten), de stille batterijsensor en de
    # onbereikbare Matter-deur = 4 entiteiten op 3 apparaten.
    assert ">4 entiteiten<" in h and ">3<" in h and "Deursensor" in h and " · Hal" in h and " · 2 entiteiten" in h
    assert "3 dagen" in h and "var(--ov-warn)" in h
    assert "1 apparaat · 1 entiteit<" in h
    # Langst weg bovenaan: zha (3 dagen) voor matter (10 min).
    assert h.index(">zha<") < h.index(">matter<")
    # wees, afgeleid en ruis staan als telling, niet in de lijst.
    assert "Weesentiteiten" in h and ">hue</span> 1" in h and ">powercalc</span> 1" in h and ">unifi</span> 1" in h
    assert "7 onbeschikbaar totaal" in h, "verborgen telt niet mee"
    # Klik: apparaat -> apparaatpagina.
    assert "navigation_path:'/config/devices/device/dev1'" in h


def test_storingen_herstart_en_leeg():
    s = states_normaal()
    s["sensor.deur_temp"] = ent("unavailable", 5 * 3600)
    s["sensor.deur_vocht"] = ent("unavailable", 5 * 3600 - 30)
    assert "sinds herstart" in D.render("storingen", s, hass=REG)
    s = {**GESTART, "sensor.ok": ent(1)}
    h = schoon(D.render("storingen", s, hass=REG))
    assert "geen storingen" in h and "Geen storingen." in h


def test_storingen_zonder_register():
    h = schoon(D.render("storingen", states_normaal()))
    assert "Entiteitenregister niet beschikbaar" in h
    # Op domein: sensor, light, device_tracker; restored blijft wees.
    assert ">sensor<" in h and ">light</span> 1" in h
    assert "hass-more-info" in h and "entityId:'sensor.deur_temp'" in h


# ------------------------------------------------------------- 3. batterijen
def test_batterijen():
    h = schoon(D.render("batterijen", states_normaal(), hass=REG))
    assert "1 onder 25%" in h and "1 stil" in h
    assert "Knop bank" in h and "18%" in h, "percentage wint van het laag-signaal"
    assert "Bewegingssensor" in h and "2 uur niets gehoord" in h
    assert "inverter" not in h and "auto_min" not in h, "accu en instelling horen er niet in"
    assert "/config/devices/device/dev2" in h


def test_batterijen_alles_goed():
    s = {**GESTART, "sensor.a_batterij": ent(80, device_class="battery")}
    h = schoon(D.render("batterijen", s, hass=REG))
    assert "alles in orde" in h and "Geen bijna lege of stille batterijen." in h


def test_batterijen_zonder_register():
    h = schoon(D.render("batterijen", states_normaal()))
    # Zonder register vallen de accu's alleen via de naam weg; de rest blijft.
    assert "Knop" in h


# ------------------------------------------------------------- 4. waakhond
def test_waakhond():
    h = schoon(D.render("waakhond", states_normaal()))
    assert ">in orde<" in h and "vandaag" in h and "2026-11-07 05:29" in h
    s = {**states_normaal(),
         "sensor.watchdog_kritieke_sensoren": st(2, namen="Lux zuid, Wind"),
         "sensor.watchdog_backup_leeftijd": st(4.2, laatste_backup="2026-11-03 05:29:04+01:00")}
    h = schoon(D.render("waakhond", s))
    assert "2 meldingen" in h and "Lux zuid, Wind" in h and "4,2 dagen geleden" in h
    h = schoon(D.render("waakhond", {"sensor.watchdog_backup_leeftijd": st("onbekend")}))
    assert "2 meldingen" in h and "onbekend" in h


# ---------------------------------------------------------------- 5. matter
def test_matter():
    h = schoon(D.render("matter", states_normaal(), hass=REG))
    assert "1 niet bereikbaar" in h and "niet bereikbaar" in h
    # Oudste eerst: Matter stekker (30 uur) voor Matter deur (10 min).
    assert h.index("Matter stekker") < h.index("Matter deur")
    assert "30 uur" in h and " · Keuken" in h and "2 entiteiten" in h
    assert "/config/devices/device/m1" in h


def test_matter_zonder_register():
    h = schoon(D.render("matter", states_normaal()))
    assert "Entiteitenregister niet beschikbaar" in h


# ------------------------------------------------------------ 7. escaping
def test_escaping():
    kwaad = "<img src=x onerror=alert(1)>"
    reg = json.loads(json.dumps(REG))
    reg["devices"]["dev1"]["name"] = kwaad
    reg["devices"]["dev2"]["name_by_user"] = kwaad
    reg["devices"]["m1"]["name"] = kwaad
    reg["areas"]["hal"]["name"] = kwaad
    reg["entities"]["light.oud"]["platform"] = kwaad
    s = states_normaal()
    s["sensor.watchdog_kritieke_sensoren"] = st(1, namen=kwaad)
    s["sensor.watchdog_backup_leeftijd"] = st(1, laatste_backup=kwaad)
    s["sensor.los"] = ent("unavailable", friendly_name=kwaad)
    for naam in ("storingen", "batterijen", "matter"):
        h = D.render(naam, s, hass=reg)
        assert "<img" not in h and "&lt;img" in h, naam
    h = D.render("waakhond", s)
    assert "<img" not in h and "&lt;img" in h
    # Een device-id dat geen veilig pad is, wordt geen onclick.
    reg["entities"]["sensor.deur_temp"]["device_id"] = "x');alert(1);('"
    h = D.render("storingen", s, hass=reg)
    onclicks = re.findall(r'onclick="([^"]*)"', h)
    assert onclicks and not any("alert" in o for o in onclicks)
    assert "navigation_path:'/config/devices/device/x" not in h


# ------------------------------------------------------------- 8. live dump
def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    for naam in D.namen():
        schoon(D.render(naam, states))


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
