"""Offline test van het Server-dashboard (dashboards/server.yaml), 6 november 2026.

Draaien:  .venv/bin/python tests/test_server_dashboard.py      (nodig: pyyaml, jinja2 en node)

Bewaakt wordt:
1. het dashboard is ingehaakt in configuration.yaml (YAML-modus, url met
   streepje, alleen beheerders) en het bestand bestaat;
2. de ventileerknoppen roepen het handbedieningsscript aan met `stand: aan`
   en een aantal uren dat het script accepteert, en "Auto" het script dat
   de automatisering terugzet; alle helpers die het dashboard leest bestaan;
3. het script kiest de juiste kant: `aan`/`uit` expliciet, zonder `stand`
   omklappen zoals de knop op het overzicht altijd deed (Jinja gerenderd);
4. het script begrenst `uren` zelf (0,5-12): de selector geldt alleen in de UI;
5. de JS van elk paneel, in node gedraaid met nagebootste `states`: kleuren
   en oordelen bij normaal, warm, kritiek en weggevallen sensoren, en tekst
   uit een state wordt ge-escaped voor hij de HTML in gaat;
6. (7 november 2026) het NAS-paneel op de UNAS-integratie: opslag in TB ongeacht
   de eenheid, RAID-, schijf- en temperatuurproblemen in de badge, probleemregels
   alleen bij een probleem, en de back-uptaken van de NAS als chips;
7. het hele dashboard tegen een live /api/states-dump als die in
   /tmp/states.json staat (overgeslagen als het bestand er niet is);
8. (7 november 2026) de compacte opbouw die het dashboard op één scherm houdt:
   Ventileren in het rackpaneel, lage grafieken, detailregels in twee kolommen;
9. (7 november 2026) elke temperatuur opent een pop-up met grafieken over 4 en
   24 uur: elke gebruikte hash heeft een pop-up, elke pop-up dezelfde reeksen
   in beide grafieken, en (live) elke schijf van de NAS staat erin.
"""
import json
import os
import re
import subprocess
import time

import jinja2
import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD = os.path.join(CONFIG, "dashboards", "server.yaml")
CONFIGURATION = os.path.join(CONFIG, "configuration.yaml")
VENTILATIE = os.path.join(CONFIG, "packages", "9 - Other", "Ventilation.yaml")


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def laad(pad):
    with open(pad, encoding="utf-8") as f:
        return yaml.load(f, Loader=HALoader)


DOC = laad(DASHBOARD)
PAKKET = laad(VENTILATIE)["ventilation_cooling_package"]


def kaarten(knoop):
    """Alle kaarten in de boom, ook die in stacks, mod-cards en grids."""
    if isinstance(knoop, dict):
        if "type" in knoop:
            yield knoop
        for waarde in knoop.values():
            yield from kaarten(waarde)
    elif isinstance(knoop, list):
        for item in knoop:
            yield from kaarten(item)


ALLE = list(kaarten(DOC["views"]))


def kaart(naam):
    for k in ALLE:
        if (k.get("variables") or {}).get("kaart") == naam:
            return k
    raise AssertionError(f"kaart {naam} niet gevonden")


# ------------------------------------------------------------------ 1. inhaken
def test_dashboard_ingehaakt():
    with open(DASHBOARD, encoding="utf-8") as f:
        assert f.read().count("button_card_templates: !include home/overzicht_templates.yaml") == 1
    db = laad(CONFIGURATION)["lovelace"]["dashboards"]
    assert "server-dashboard" in db
    d = db["server-dashboard"]
    assert d["mode"] == "yaml"
    assert d["filename"] == "dashboards/server.yaml"
    assert d["require_admin"] is True
    for url in db:
        assert "-" in url, f"HA eist een streepje in de url van een dashboard: {url}"


# ------------------------------------------------------- 2. knoppen en helpers
def knoppen():
    return [k for k in ALLE if (k.get("tap_action") or {}).get("action") == "perform-action"]


def test_ventileerknoppen():
    script = PAKKET["script"]["ventilation_serverrack_handbediening"]
    veld = script["fields"]["uren"]["selector"]["number"]
    uren = []
    for k in knoppen():
        actie = k["tap_action"]
        naam = actie["perform_action"].split(".", 1)[1]
        assert naam in PAKKET["script"], f"onbekend script {naam}"
        if naam == "ventilation_serverrack_handbediening":
            assert actie["data"]["stand"] == "aan", "een tweede tik mag de ventilatoren niet uitzetten"
            u = actie["data"]["uren"]
            assert veld["min"] <= u <= veld["max"], f"{u} uur valt buiten het script"
            uren.append(u)
    assert uren == [1, 2, 4, 8]
    assert any(k["tap_action"]["perform_action"] == "script.ventilation_serverrack_automatisch" for k in knoppen())
    # restart: een nieuwe keuze terwijl het script nog loopt mag niet stil wegvallen.
    assert script["mode"] == "restart"
    assert script["fields"]["stand"]["default"] == "wissel"


def test_helpers_bestaan():
    with open(DASHBOARD, encoding="utf-8") as f:
        tekst = f.read()
    for domein in ("input_number", "input_datetime"):
        for naam in set(re.findall(rf"{domein}\.([a-z0-9_]+)", tekst)):
            assert naam in PAKKET[domein], f"{domein}.{naam} bestaat niet in Ventilation.yaml"


# --------------------------------------------------------------- 3. het script
def nieuwe_stand(stand, schakelaar):
    script = PAKKET["script"]["ventilation_serverrack_handbediening"]
    sjabloon = next(s for s in script["sequence"] if "variables" in s)["variables"]["nieuw"]
    env = jinja2.Environment()
    ctx = {"is_state": lambda e, s: schakelaar == s}
    if stand is not None:
        ctx["stand"] = stand
    return env.from_string(sjabloon).render(**ctx)


def test_script_stand():
    for schakelaar in ("on", "off"):
        assert nieuwe_stand("aan", schakelaar) == "on"
        assert nieuwe_stand("uit", schakelaar) == "off"
        assert nieuwe_stand("AAN", schakelaar) == "on"
    # Zonder stand (de knop op het overzicht) en met `wissel`: omklappen.
    assert nieuwe_stand(None, "on") == "off"
    assert nieuwe_stand(None, "off") == "on"
    assert nieuwe_stand("wissel", "on") == "off"


def duur(uren):
    script = PAKKET["script"]["ventilation_serverrack_handbediening"]
    sjabloon = next(s for s in script["sequence"] if "variables" in s)["variables"]["duur"]
    ctx = {} if uren is None else {"uren": uren}
    return float(jinja2.Environment().from_string(sjabloon).render(**ctx))


def test_script_duur_begrensd():
    # Via de API gelden de selectorgrenzen niet: het script klemt zelf.
    assert duur(None) == 2
    assert duur(4) == 4
    assert duur(1000) == 12
    assert duur(0) == 0.5
    assert duur("onzin") == 2


# ------------------------------------------------------------ 4. JS in node
def js(naam):
    x = kaart(naam)["custom_fields"]["x"].strip()
    assert x.startswith("[[[") and x.endswith("]]]")
    return x[3:-3]


def render(naam, states, entity_id=None):
    k = kaart(naam)
    entity_id = entity_id or k.get("entity")
    # De states gaan via stdin: met een volledige /api/states-dump als invoer
    # wordt een opdrachtregel te lang.
    prog = (
        "const states = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "const variables = %s; const entity = states[%s];"
        "const out = (function(){ %s })(); process.stdout.write(out);"
        % (json.dumps(k.get("variables") or {}), json.dumps(entity_id), js(naam))
    )
    r = subprocess.run(["node", "-e", prog], input=json.dumps(states),
                       capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    return r.stdout


def st(state, **attrs):
    return {"state": str(state), "attributes": attrs}


RACK = {
    "sensor.garage_serverrack_temperatuur_temperature": st(27.3),
    "sensor.garage_serverrack_temperatuur_humidity": st(35),
    "sensor.garage_garage_temperatuur_temperatuur": st(20.2),
    "sensor.ventilatie_serverrack_temp_verandering_1u": st(-0.6),
    "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("off"),
    "input_number.ventilation_serverrack_warm_threshold": st(28),
    "input_number.ventilation_serverrack_critical_threshold": st(35),
}


def test_rack():
    h = render("rack", RACK)
    assert "koel genoeg" in h and "27,3°" in h and "var(--ov-ok)" in h
    assert "−0,6 °C" in h and "20,2 °C" in h
    h = render("rack", {**RACK, "sensor.garage_serverrack_temperatuur_temperature": st(29.1)})
    assert ">warm<" in h and "var(--ov-warn)" in h
    h = render("rack", {**RACK, "sensor.garage_serverrack_temperatuur_temperature": st(36)})
    assert "kritiek</span>" in h
    h = render("rack", {**RACK, "sensor.garage_serverrack_temperatuur_temperature": st("unavailable")})
    assert "geen meting" in h
    # Helper even weg (reload): terugvallen op de standaarddrempels.
    h = render("rack", {**RACK, "input_number.ventilation_serverrack_warm_threshold": st("unavailable")})
    assert "warm 28°" in h
    h = render("rack", {**RACK, "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("on")})
    assert "draaien" in h


def test_ventileren():
    nu = time.time()
    basis = {
        "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("on"),
        "input_datetime.ventilation_serverrack_handbediening_tot": st("x", timestamp=nu + 80 * 60),
        "input_datetime.ventilation_serverrack_lockout_until": st("x", timestamp=nu - 60),
    }
    h = render("ventileren", basis)
    assert "Handmatig aan tot" in h and "nog 1 u 20 min" in h and ">aan<" in h
    h = render("ventileren", {**basis,
        "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("off"),
        "input_datetime.ventilation_serverrack_handbediening_tot": st("x", timestamp=nu - 60),
        "input_datetime.ventilation_serverrack_lockout_until": st("x", timestamp=nu + 3600)})
    assert "Blazen hielp niet meer" in h and ">uit<" in h
    h = render("ventileren", {**basis, "input_datetime.ventilation_serverrack_handbediening_tot": st("x", timestamp=nu - 60)})
    assert h.count("Automatisch:") == 1
    h = render("ventileren", {**basis, "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("unavailable")})
    assert "geen verbinding" in h


NUC = {
    "sensor.proxmox_nuc_intel_cpu_temperatuur": st(62),
    "sensor.proxmox_nuc_intel_nvme_temperatuur": st(48),
    "sensor.proxmox_nuc_intel_cpu_verbruik": st(9),
    "sensor.node_intel_cpu_used": st(23.4),
    "sensor.node_intel_memory_used_percentage": st(71.3),
    "sensor.node_intel_status": st("online"),
}


def test_nuc():
    h = render("nuc", NUC)
    assert "in orde" in h and "62°" in h and "9 W" in h and "71%" in h
    h = render("nuc", {**NUC, "sensor.proxmox_nuc_intel_cpu_temperatuur": st(90)})
    assert ">warm<" in h
    h = render("nuc", {**NUC, "sensor.proxmox_nuc_intel_cpu_temperatuur": st(93)})
    assert "kritiek heet" in h
    # expire_after: na vijf minuten stilte is de sensor unavailable.
    h = render("nuc", {**NUC, "sensor.proxmox_nuc_intel_cpu_temperatuur": st("unavailable")})
    assert "stuurt niets" in h
    h = render("nuc", {**NUC, "sensor.node_intel_status": st("offline")})
    assert "Proxmox offline" in h


def test_nuc_details():
    s = {
        "sensor.node_intel_disk_used": st(33.0), "sensor.node_intel_disk_total": st(100.9),
        "sensor.node_intel_memory_used": st(47.8), "sensor.node_intel_memory_total": st(67.1),
        "sensor.proxmox_nuc_intel_load_average": st(6.9),
        "sensor.proxmox_nuc_intel_throttle_events": st(10),
        "sensor.node_intel_io_delay": st(0.5), "sensor.node_intel_swap_used": st(49.5),
        "sensor.node_intel_virtual_machines_running": st(8), "sensor.node_intel_containers_running": st(6),
        "sensor.proxmox_nuc_intel_uptime": st(188155),
        "sensor.node_intel_failed_tasks": st(0),
        "binary_sensor.node_intel_backup_running": st("off"),
        "sensor.node_intel_version": st("9.2.26"), "update.proxmox_ve_update": st("off"),
    }
    h = render("nuc_details", s)
    assert "33 van 101 GB" in h and "6,9 op 8 threads" in h
    assert "10× sinds opstart" in h and "2 d 4 u" in h and "8 VM's · 6 containers" in h
    assert "Mislukte taken" not in h and "update klaar" not in h
    h = render("nuc_details", {**s, "sensor.node_intel_failed_tasks": st(2), "update.proxmox_ve_update": st("on"),
                                "sensor.proxmox_nuc_intel_throttle_events": st(0)})
    assert "Mislukte taken" in h and "update klaar" in h and "nooit" in h


U = "sensor.garage_unas_garage_"


def nas_states():
    """De UNAS zoals hij op 7 november 2026 live stond (UNAS-integratie)."""
    s = {
        "device_tracker.unas_pro_8": st("home"),
        U + "storage_pool_1_size": st(23.983, unit_of_measurement="TB"),
        U + "storage_pool_1_used": st(1.116, unit_of_measurement="TB"),
        U + "storage_pool_1_available": st(22.867, unit_of_measurement="TB"),
        U + "storage_pool_1_usage": st(5),
        U + "storage_pool_1_status": st("fullyOperational"),
        U + "storage_pool_1_raid_level": st("raid6"),
        U + "cpu_temperature": st(68), U + "cpu_usage": st(11),
        U + "memory_usage": st(14.5), U + "memory_used": st(2.296875), U + "memory_total": st(15.861328125),
        U + "fan_speed_percent": st(24), "select.garage_unas_garage_fan_mode": st("UNAS Managed"),
        U + "disk_read": st(9.09, unit_of_measurement="MB/s"), U + "disk_write": st(29.22, unit_of_measurement="MB/s"),
        U + "smb_connections": st(14), U + "nfs_mounts": st(2),
        U + "uptime": st(time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - (1 * 86400 + 5 * 3600 + 60)))),
        U + "unifi_os_version": st("6.0.11"), U + "unifi_drive_version": st("4.4.30"),
        "update.unifi_unas": st("off"),
        "binary_sensor.immich_nas": st("on"),
        "binary_sensor.garage_unas_garage_monitor_service": st("on"),
        "binary_sensor.garage_unas_garage_fan_control_service": st("on"),
        U + "share_media_usage": st(0.49296, unit_of_measurement="TB", friendly_name="UNAS Garage Share: Media Usage"),
        U + "share_media_quota": st(5000, unit_of_measurement="GB"),
        U + "share_data_usage": st(0.0187, unit_of_measurement="TB", friendly_name="UNAS Garage Share: Data Usage"),
        U + "share_data_quota": st("Unlimited"),
    }
    for i in range(1, 5):
        s[U + f"hdd_{i}_temperature"] = st(38 + i % 2)
        s[U + f"hdd_{i}_status"] = st("Optimal")
        s[U + f"hdd_{i}_bad_sectors"] = st(0)
        s[U + f"hdd_{i}_total_size"] = st(12.0, unit_of_measurement="TB")
    return s


def test_nas():
    s = nas_states()
    h = render("nas", s)
    assert ">in orde<" in h and "23" in h and "TB vrij" in h
    assert "RAID 6" in h and "gezond" in h and "1,1 TB gebruikt · 5%" in h and "van 24,0 TB" in h
    assert "68°" in h and "11% belast" in h and "2,3 van 16 GB" in h and "automatisch" in h
    assert "4 van 8 vakken" in h and h.count("12 TB") == 4 and h.count("border:1px dashed") == 4
    assert "↓ 9,1 · ↑ 29 MB/s" in h and "14 SMB · 2 NFS" in h and "1 d 5 u" in h and "6.0.11 · Drive 4.4.30" in h
    # Probleemregels staan er alleen als er een probleem is.
    for niet in ("Gekoppeld aan Immich", "Monitorscript", "Share ", "UNAS-integratie"):
        assert niet not in h, niet


def test_nas_problemen():
    s = nas_states()
    h = render("nas", {**s, "device_tracker.unas_pro_8": st("not_home")})
    assert ">onbereikbaar<" in h
    h = render("nas", {**s, U + "storage_pool_1_status": st("degraded")})
    assert ">RAID degraded<" in h and "var(--ov-bad)\">degraded" in h
    h = render("nas", {**s, U + "storage_pool_1_status": st("rebuilding")})
    assert "var(--ov-warn)" in h and "RAID rebuilding" in h
    h = render("nas", {**s, U + "hdd_3_status": st("Failed")})
    assert "schijf 3 Failed" in h
    h = render("nas", {**s, U + "hdd_2_bad_sectors": st(8)})
    assert "schijf 2: 8 slechte sectoren" in h
    h = render("nas", {**s, U + "hdd_1_temperature": st(51), U + "cpu_temperature": st(85)})
    assert "2 meldingen" in h and "var(--ov-bad)\">51°" in h and "var(--ov-warn)\">85°" in h
    # Bijna vol: 92% kleurt de balk en het getal rood.
    h = render("nas", {**s, U + "storage_pool_1_used": st(22.1), U + "storage_pool_1_available": st(1.88)})
    assert "92% vol" in h and "1,9" in h
    # Share boven 90% van zijn quota: regel erbij. Unlimited telt nooit.
    h = render("nas", {**s, U + "share_media_usage": st(4.7, unit_of_measurement="TB", friendly_name="UNAS Garage Share: Media Usage")})
    assert "Share Media" in h and "94% van quota" in h and "share vol" in h
    h = render("nas", {**s, "binary_sensor.immich_nas": st("off"), "binary_sensor.garage_unas_garage_monitor_service": st("off")})
    assert "Gekoppeld aan Immich" in h and "Monitorscript" in h and "2 meldingen" in h
    h = render("nas", {**s, "update.unifi_unas": st("on")})
    assert "UNAS-integratie" in h and ">in orde<" in h, "een integratie-update is geen probleem van de NAS"


def test_nas_zonder_integratie():
    # Integratie weg of nog aan het opstarten: geen exceptions, wel een melding.
    h = render("nas", {"device_tracker.unas_pro_8": st("home")})
    assert "geen data" in h and "SCHIJVEN" not in h and "—" in h
    s = {k: st("unavailable") for k in nas_states()}
    s["device_tracker.unas_pro_8"] = st("home")
    h = render("nas", s)
    assert "geen data" in h


def test_nas_eenheden():
    # Kiest de integratie GB of TiB, dan blijft het paneel in TB rekenen.
    s = {**nas_states(),
         U + "storage_pool_1_size": st(23983, unit_of_measurement="GB"),
         U + "storage_pool_1_used": st(1116, unit_of_measurement="GB"),
         U + "storage_pool_1_available": st(20.8, unit_of_measurement="TiB")}
    h = render("nas", s)
    assert "van 24,0 TB" in h and "1,1 TB gebruikt" in h and ">23<" in h


def test_gasten():
    s = {}
    for g in kaart("gasten")["variables"]["gasten"]:
        s[f"sensor.{g['p']}_status"] = st("running")
        s[f"sensor.{g['p']}_cpu_used"] = st(3.2)
        s[f"sensor.{g['p']}_memory_used_percentage"] = st(96)
        s[f"sensor.{g['p']}_disk_used_percentage"] = st(40)
    h = render("gasten", s)
    assert "alles draait" in h and h.count("var(--ov-ok)\"></span>") == len(kaart("gasten")["variables"]["gasten"])
    # Geheugen kleurt nooit (paginacache, zie de kop van het dashboard).
    assert "96%" in h and "var(--ov-warn)\">96%" not in h and "var(--ov-bad)\">96%" not in h
    h = render("gasten", {**s, "sensor.qemu_windows_107_status": st("stopped"),
                          "sensor.qemu_tools_110_disk_used_percentage": st(97)})
    assert "1 uit" in h and "· stopped" in h and "var(--ov-bad)\">97%" in h


def test_gasten_uniek():
    lijst = kaart("gasten")["variables"]["gasten"]
    for veld in ("naam", "id", "p"):
        waarden = [g[veld] for g in lijst]
        assert len(waarden) == len(set(waarden)), f"dubbele {veld}"


def test_backups():
    nu = time.time()
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(t))
    s = {
        "sensor.backup_last_successful_automatic_backup": st(iso(nu - 10 * 3600)),
        "sensor.backup_last_successful_automatic_backup_size": st(6653.2),
        "sensor.backup_next_scheduled_automatic_backup": st(iso(nu + 14 * 3600)),
        "sensor.immich_backup": st("ok"),
        "sensor.immich_backup_leeftijd": st(10.5),
    }
    h = render("backups", s)
    assert ">bij<" in h and "10 uur geleden" in h and "6,5 GB" in h and "Volgende HA-back-up" in h
    h = render("backups", {**s, "sensor.backup_last_successful_automatic_backup": st(iso(nu - 50 * 3600)),
                           "sensor.immich_backup": st("mislukt")})
    assert "2 problemen" in h and "mislukt" in h


def nas_taak(naam, status="succeeded", uur_geleden=10, duur=52, schema="on"):
    b = "sensor.garage_unas_garage_backup_" + naam.lower().replace(" ", "_")
    t = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - uur_geleden * 3600))
    return {
        b + "_status": st(status), b + "_last_run": st(t), b + "_last_run_duration": st(duur),
        b + "_task_name": st(naam),
        "switch." + b[len("sensor."):] + "_schedule_enabled": st(schema),
    }


def test_backups_nas():
    nu = time.time()
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(t))
    basis = {"sensor.backup_last_successful_automatic_backup": st(iso(nu - 3600))}
    taken = {**nas_taak("Data backup"), **nas_taak("Robin backup", duur=3528), **nas_taak("Development Backup", duur=12275, uur_geleden=9)}
    h = render("backups", {**basis, **taken})
    assert ">bij<" in h and "alle 3 gelukt · 9 uur geleden" in h
    assert ">Data<" in h and ">Robin<" in h and ">Development<" in h and "backup<" not in h.lower().replace("back-up", "")
    assert "52 s" in h and "59 min" in h and "3,4 u" in h
    # Mislukt, te oud en schema uit tellen alle drie als probleem.
    h = render("backups", {**basis, **taken, **nas_taak("Data backup", status="failed")})
    assert "1 probleem" in h and "1 van 3 niet gelukt" in h and "failed" in h
    h = render("backups", {**basis, **taken, **nas_taak("Robin backup", uur_geleden=50)})
    assert "1 probleem" in h and "2 dagen geleden" in h
    h = render("backups", {**basis, **taken, **nas_taak("Development Backup", schema="off")})
    assert "1 probleem" in h and "schema uit" in h and "var(--ov-warn)" in h
    h = render("backups", {**basis, **taken, **nas_taak("Data backup", status="running")})
    assert ">bij<" in h and "loopt nu" in h
    # Geen UNAS-taken: geen NAS-regel.
    assert "NAS" not in render("backups", basis)


def test_state_tekst_wordt_ge_escaped():
    kwaad = "<img src=x onerror=alert(1)>"
    h = render("backups", {"sensor.immich_backup": st(kwaad)})
    assert "<img" not in h and "&lt;img" in h
    h = render("nuc_details", {"sensor.node_intel_version": st(kwaad)})
    assert "<img" not in h
    h = render("nuc", {**NUC, "sensor.node_intel_status": st(kwaad)})
    assert "<img" not in h
    h = render("nas", {**nas_states(), U + "storage_pool_1_status": st(kwaad), U + "hdd_1_status": st(kwaad),
                       U + "unifi_os_version": st(kwaad), "select.garage_unas_garage_fan_mode": st(kwaad),
                       U + "share_media_usage": st(4.9, unit_of_measurement="TB", friendly_name="UNAS Garage Share: " + kwaad + " Usage")})
    assert "<img" not in h and "&lt;img" in h
    h = render("backups", {**nas_taak("Data backup", status=kwaad), "sensor.garage_unas_garage_backup_data_backup_task_name": st(kwaad)})
    assert "<img" not in h
    g = kaart("gasten")["variables"]["gasten"][0]["p"]
    h = render("gasten", {f"sensor.{g}_status": st(kwaad)})
    assert "<img" not in h


def test_past_op_een_scherm():
    # Ventileren staat in hetzelfde paneel als het rack, niet in een eigen paneel.
    panelen = [k for k in ALLE if k.get("type") == "custom:mod-card"]
    def namen(p):
        return {(k.get("variables") or {}).get("kaart") for k in kaarten(p["card"])}
    rackpaneel = next(p for p in panelen if "rack" in namen(p))
    assert "ventileren" in namen(rackpaneel)
    assert len(panelen) == 5, "rack+ventileren, NAS, NUC, gasten, back-ups"
    # Grafieken op de panelen laag genoeg (die in de pop-ups mogen hoger).
    for g in (k for k in kaarten(DOC["views"][0]["cards"][0]["cards"][0]) if k.get("type") == "custom:apexcharts-card"):
        assert g["apex_config"]["chart"]["height"] <= 140
    # Detailregels in twee kolommen; balken van de NUC over de volle breedte.
    for naam in ("nas", "nuc_details"):
        assert "grid-template-columns:repeat(2,minmax(0,1fr))" in js(naam), naam
    h = render("nuc_details", {"sensor.node_intel_disk_used": st(33), "sensor.node_intel_disk_total": st(101),
                               "sensor.node_intel_swap_used": st(53)})
    assert h.count("grid-column:1/-1") == 1


# ------------------------------------------------- 9. temperatuur-pop-ups
def popups():
    return {k["hash"]: k for k in ALLE if k.get("type") == "custom:bubble-card" and k.get("card_type") == "pop-up"}


def reeksen(popup):
    return [s["entity"] for s in popup["cards"][0]["series"]]


def test_popups_bestaan():
    pp = popups()
    assert set(pp) == {"#temp-rack", "#temp-nuc", "#temp-nas"}
    for h, p in pp.items():
        # De hash gaat letterlijk een onclick in: alleen veilige tekens.
        assert re.fullmatch(r"#[a-z-]+", h), h
        spans = [c["graph_span"] for c in p["cards"]]
        assert spans == ["4h", "24h"], h
        assert p["cards"][0]["series"] == p["cards"][1]["series"], f"{h}: 4 en 24 uur tonen verschillende reeksen"
        assert all("temperat" in e for e in reeksen(p)), h
        # 24 uur: max per 10 min, een piek mag niet wegmiddelen.
        assert p["cards"][1]["all_series_config"]["group_by"]["func"] == "max"
    # Elke verwijzing vanaf een paneel heeft een pop-up.
    assert kaart("rack")["tap_action"] == {"action": "navigate", "navigation_path": "#temp-rack"}
    assert kaart("nuc")["variables"]["grafiek"] in pp
    assert kaart("nas")["variables"]["grafiek"] in pp
    assert "sensor.garage_serverrack_temperatuur_temperature" in reeksen(pp["#temp-rack"])
    assert "sensor.proxmox_nuc_intel_nvme_temperatuur" in reeksen(pp["#temp-nuc"])


def test_klikken_komt_aan():
    # button-card: kaart zonder eigen actie = class `disabled` = pointer-events: none,
    # en dan doet geen enkele onclick in de HTML iets. Elke HTML-kaart met onclicks
    # moet dat dus zelf weer aanzetten.
    for k in ALLE:
        x = (k.get("custom_fields") or {}).get("x", "")
        if "onclick" not in x:
            continue
        stijl = {kk: v for d in (k.get("styles") or {}).get("card", []) for kk, v in d.items()}
        assert stijl.get("pointer-events") == "auto", (k.get("variables") or {}).get("kaart")


N = "sensor.unas_garage_nvme_"   # eigen prefix, niet U (7-11-2026)


def test_nas_nvme():
    # NVMe-sloten (7-11-2026): naast de vakken, zelf gevonden, met eigen grenzen.
    s = nas_states()
    h = render("nas", s)
    assert "NVMe" not in h and "M.2" not in h   # zonder NVMe-sensoren niets extra
    for n in (0, 1):
        s[N + f"{n}_available_spare"] = st(100)
        s[N + f"{n}_available_spare_threshold"] = st(10)
        s[N + f"{n}_percentage_used"] = st(1)
    s[N + "0_temperature"] = st(41)
    s[N + "1_temperature"] = st(44)
    s[N + "1_total_size"] = st(500, unit_of_measurement="GB")
    h = render("nas", s)
    assert "4 van 8 vakken · 2× NVMe" in h and ">in orde<" in h
    assert "41°" in h and "44°" in h and "500 GB" in h and "M.2 0" in h and "reserve 100%" in h
    assert h.count("'#temp-nas'") == 1 + 4 + 2
    h = render("nas", {**s, N + "0_temperature": st(65)})
    assert ">NVMe 0 65°<" in h and "var(--ov-warn)" in h
    assert ">NVMe 1 72°<" in render("nas", {**s, N + "1_temperature": st(72)})
    assert ">NVMe 0 reserve 5%<" in render("nas", {**s, N + "0_available_spare": st(5)})
    assert ">NVMe 1 85% versleten<" in render("nas", {**s, N + "1_percentage_used": st(85)})
    h = render("nas", {**s, N + "0_status": st("<b>Failed</b>")})
    assert "NVMe 0 &lt;b&gt;Failed&lt;/b&gt;" in h and "<b>" not in h
    # Zonder temperatuur: slot blijft, tik = more-info van de reserve.
    zonder = {k: v for k, v in s.items() if k != N + "0_temperature"}
    h = render("nas", zonder)
    assert "2× NVMe" in h and "entityId:'" + N + "0_available_spare'" in h
    assert "undefined" not in h and "NaN" not in h
    h = render("nas", {**s, N + "0_temperature": st("unavailable")})
    assert "undefined" not in h and "NaN" not in h and "—" in h
    # Ook in de pop-up, 4 en 24 uur.
    assert {N + "0_temperature", N + "1_temperature"} <= set(reeksen(popups()["#temp-nas"]))


def test_temperaturen_klikbaar():
    # NUC: CPU- en NVMe-tegel openen de pop-up, belasting en geheugen nog more-info.
    h = render("nuc", NUC)
    assert h.count("'#temp-nuc'") == 2 and "hass-action" in h and "action:'navigate'" in h
    assert "entityId:'sensor.node_intel_memory_used_percentage'" in h
    # NAS: CPU-tegel en elk gevuld schijfvak (4), lege vakken niet.
    h = render("nas", nas_states())
    assert h.count("'#temp-nas'") == 1 + 4
    assert "entityId:'" + U + "memory_usage'" in h


def test_live_states():
    """Alle panelen tegen een echte dump (curl .../api/states > /tmp/states.json)."""
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    for naam in ("rack", "ventileren", "nas", "nuc", "nuc_details", "gasten", "backups"):
        h = render(naam, states)
        assert h and "undefined" not in h and "NaN" not in h, naam
    # Pop-ups: elke reeks bestaat, en elke schijf van de NAS staat erin.
    pp = popups()
    nvme_re = re.escape(N) + r"\d+_temperature"
    nvme_live = {e for e in states if re.fullmatch(nvme_re, e)}
    for h, p in pp.items():
        for e in reeksen(p):
            # Een dump van vóór de NVMe-sloten (7-11-2026) kent ze nog niet.
            if not nvme_live and re.fullmatch(nvme_re, e):
                print(f"let op: {e} niet te controleren, de dump heeft nog geen NVMe")
                continue
            assert e in states, f"{h}: {e} bestaat niet"
    schijven = {e for e in states if re.fullmatch(re.escape(U) + r"hdd_\d+_temperature", e)}
    assert schijven and schijven <= set(reeksen(pp["#temp-nas"])), "nieuwe schijf: zet hem bij #temp-nas"
    assert nvme_live <= set(reeksen(pp["#temp-nas"])), "nieuwe NVMe: zet hem bij #temp-nas"
    # De NVMe-temperaturen bestaan als er NVMe-sensoren zijn (anders lege lijnen in de pop-up).
    if any(e.startswith(N) for e in states):
        assert nvme_live, "geen " + N + "<n>_temperature: pas de reeksen van #temp-nas aan"


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
