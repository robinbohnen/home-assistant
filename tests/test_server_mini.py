"""Offline test van de Server-regel op het wandpaneel (KLIMAAT, rechterkolom). 7 november 2026.

Draaien:  python3 tests/test_server_mini.py      (nodig: pyyaml en node)

De regel "Server" (was "Serverrack") vat rack, NUC en NAS samen. Bewaakt wordt:
1. de subregel: racktemperatuur, NUC-CPU, vrije ruimte op de NAS (ook in GB);
2. de badge: "in orde" als alles goed is, anders het ergste probleem (+ aantal),
   met dezelfde drempels als dashboards/server.yaml;
3. een lopende handbediening van de ventilatoren blijft zichtbaar;
4. tikken = het Server-dashboard (dat bestaat, met view-pad `status`),
   vasthouden = handbediening;
5. geen `undefined`/`NaN` als alles weg is; tegen een live dump als die er is.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, Dashboard, laad, st  # noqa: E402

D = Dashboard("dashboards/home/overzicht/kolom_rechts.yaml")
U = "sensor.garage_unas_garage_"
N = "sensor.unas_garage_nvme_"


def goed():
    s = {
        "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("off"),
        "sensor.garage_serverrack_temperatuur_temperature": st(22.7),
        "input_number.ventilation_serverrack_warm_threshold": st(28),
        "input_number.ventilation_serverrack_critical_threshold": st(35),
        "input_datetime.ventilation_serverrack_handbediening_tot": st("x", timestamp=0),
        "sensor.proxmox_nuc_intel_cpu_temperatuur": st(52),
        "sensor.proxmox_nuc_intel_nvme_temperatuur": st(45),
        "sensor.node_intel_status": st("online"),
        "device_tracker.unas_pro_8": st("home"),
        U + "storage_pool_1_status": st("fullyOperational"),
        U + "storage_pool_1_available": st(22.867, unit_of_measurement="TB"),
        U + "storage_pool_1_usage": st(5),
        N + "0_temperature": st(41), N + "0_available_spare": st(100), N + "0_available_spare_threshold": st(10),
        N + "1_temperature": st(43), N + "1_available_spare": st(100),
    }
    for i in range(1, 5):
        s[U + f"hdd_{i}_temperature"] = st(38)
        s[U + f"hdd_{i}_status"] = st("Optimal")
    return s


def sub(s):
    return D.render("server_mini", s, "sub")


def badge(s):
    return D.render("server_mini", s, "badge")


def test_subregel():
    assert sub(goed()) == "rack 22,7° · NUC 52° · NAS 23 TB vrij"
    assert sub({**goed(), U + "storage_pool_1_available": st(4200, unit_of_measurement="GB")}).endswith("NAS 4,2 TB vrij")
    assert sub({}) == "rack — · NUC — · NAS —"


def test_badge_in_orde():
    b = badge(goed())
    assert ">in orde<" in b and "var(--ov-ok)" in b
    assert ">ventileert<" in badge({**goed(), "switch.garage_garage_stopcontact_serverrack_ventilatoren": st("on")})
    hand = st("x", timestamp=time.time() + 3600)
    assert ">hand · uit<" in badge({**goed(), "input_datetime.ventilation_serverrack_handbediening_tot": hand})


def test_badge_problemen():
    g = goed()
    gevallen = [
        ({"sensor.garage_serverrack_temperatuur_temperature": st(30)}, "rack warm", "warn"),
        ({"sensor.garage_serverrack_temperatuur_temperature": st(36)}, "rack heet", "bad"),
        ({"sensor.proxmox_nuc_intel_cpu_temperatuur": st(86)}, "NUC warm", "warn"),
        ({"sensor.proxmox_nuc_intel_cpu_temperatuur": st(93)}, "NUC heet", "bad"),
        ({"sensor.proxmox_nuc_intel_cpu_temperatuur": st("unavailable")}, "NUC stil", "bad"),
        ({"sensor.node_intel_status": st("offline")}, "NUC offline", "bad"),
        ({"sensor.proxmox_nuc_intel_nvme_temperatuur": st(65)}, "NUC NVMe", "warn"),
        ({"device_tracker.unas_pro_8": st("not_home")}, "NAS weg", "bad"),
        ({U + "storage_pool_1_status": st("degraded")}, "NAS RAID", "bad"),
        ({U + "storage_pool_1_status": st("rebuilding")}, "NAS RAID", "warn"),
        ({U + "storage_pool_1_usage": st(85)}, "NAS vol", "warn"),
        ({U + "hdd_3_status": st("Failed")}, "schijf 3", "bad"),
        ({U + "hdd_2_temperature": st(46)}, "schijf 2 warm", "warn"),
        ({N + "1_temperature": st(72)}, "NAS NVMe 1", "bad"),
        ({N + "0_available_spare": st(5)}, "NAS NVMe 0", "bad"),
    ]
    for extra, tekst, k in gevallen:
        b = badge({**g, **extra})
        assert f">{tekst}<" in b and f"var(--ov-{k})" in b, (extra, b)
    # Meerdere: de ergste eerst, plus het aantal andere.
    b = badge({**g, "sensor.garage_serverrack_temperatuur_temperature": st(30), U + "hdd_3_status": st("Failed")})
    assert ">schijf 3 +1<" in b and "var(--ov-bad)" in b
    # Een probleem wint van de handbediening.
    b = badge({**g, "sensor.proxmox_nuc_intel_cpu_temperatuur": st(93),
               "input_datetime.ventilation_serverrack_handbediening_tot": st("x", timestamp=time.time() + 3600)})
    assert ">NUC heet<" in b


def test_alles_weg():
    for s in ({}, {k: st("unavailable") for k in goed()}):
        for veld in ("sub", "badge"):
            h = D.render("server_mini", s, veld)
            assert "undefined" not in h and "NaN" not in h, (veld, h)
    # Statustekst komt niet letterlijk in de badge (vaste teksten).
    assert "<script>" not in badge({**goed(), U + "storage_pool_1_status": st("<script>")})


def test_acties():
    k = D.kaart("server_mini")
    assert k["tap_action"] == {"action": "navigate", "navigation_path": "/server-dashboard/status"}
    assert k["hold_action"]["perform_action"] == "script.ventilation_serverrack_handbediening"
    # Het doel bestaat: dashboard-url in configuration.yaml, view-pad in server.yaml.
    assert "server-dashboard" in laad(os.path.join(CONFIG, "configuration.yaml"))["lovelace"]["dashboards"]
    paden = [v.get("path") for v in laad(os.path.join(CONFIG, "dashboards", "server.yaml"))["views"]]
    assert "status" in paden
    assert "sensor.time" in k["triggers_update"]


def test_live_states():
    pad = "/tmp/states.json"
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        states = {e["entity_id"]: e for e in json.load(f)}
    for veld in ("sub", "badge"):
        h = D.render("server_mini", states, veld)
        assert h and "undefined" not in h and "NaN" not in h, (veld, h)
    for e in ("sensor.garage_serverrack_temperatuur_temperature", "sensor.proxmox_nuc_intel_cpu_temperatuur",
              "sensor.node_intel_status", "device_tracker.unas_pro_8", U + "storage_pool_1_available"):
        assert e in states, e


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
