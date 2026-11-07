"""Offline test van www/sv-kit.js, de bouwstenen van de Server-stijl. 7 november 2026.

Draaien:  python3 tests/test_sv_kit.py      (nodig: pyyaml en node)

Bewaakt wordt:
1. `klik` maakt alleen een onclick van een entity-id, een pop-up-hash of een
   pad; al het andere (aanhalingstekens, javascript:, spaties) wordt genegeerd;
2. `esc` maakt state-tekst onschadelijk;
3. de bouwstenen leveren de markup van server.yaml (zelfde maten en kleuren),
   zodat elke weergave er hetzelfde uitziet;
4. de module staat in `frontend.extra_module_url` én in resources.yaml;
5. de templates `sv_html` en `sv_paneel` zetten pointer-events: auto.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sv_render import CONFIG, TPL, laad, run_js, st  # noqa: E402


def k(code, states=None):
    return run_js("var S = window.svKit(states); " + code, states or {})


def test_klik_alleen_veilige_doelen():
    assert "hass-more-info" in k("return S.klik('sensor.cpu_temp');")
    assert "navigation_path:'#temp-nas'" in k("return S.klik('#temp-nas');")
    assert "navigation_path:'/lovelace/accu'" in k("return S.klik('/lovelace/accu');")
    for slecht in ["sensor.x'); alert(1); ('", "javascript:alert(1)", "#a b", "sensor.X",
                   "/pad\" onmouseover=\"x", "", "#<img>"]:
        assert k("return S.klik(%r);" % slecht) == "", slecht
    # Een onveilige klik geeft ook geen cursor:pointer.
    assert "cursor:pointer" not in k("return S.rij({klik: 'x\"y', naam: 'a', waarde: 'b'});")


def test_esc():
    assert k("return S.esc('<img src=x onerror=alert(1)>');") == "&lt;img src=x onerror=alert(1)&gt;"
    assert k("return S.esc(\"a'b\\\"c&\");") == "a&#39;b&quot;c&amp;"


def test_zelfde_markup_als_server():
    h = k("return S.pil('ok', 'in orde');")
    assert "font-size:11.5px;font-weight:600;padding:3px 11px;border-radius:20px" in h and "var(--ov-ok-15)" in h
    h = k("return S.kop('NAS', S.pil('ok','x'));")
    assert "font-size:12px;font-weight:700;letter-spacing:1.2px;color:var(--ov-ink-55)" in h and ">NAS<" in h
    assert "border-top" in k("return S.kop('VENTILEREN', '', {eerste: false});")
    h = k("return S.tegel({klik: 'sensor.a', label: 'CPU', waarde: '60°', k: 'ok', sub: '5 W'});")
    assert "border-radius:12px;padding:6px 11px" in h and "font-size:20px" in h and "var(--ov-ok)" in h
    assert ">5 W<" in h and "hass-more-info" in h
    h = k("return S.rijen([{naam: 'A', waarde: '1'}, {naam: 'B', waarde: '2', extra: S.balk(50)}], 2);")
    assert "repeat(2,minmax(0,1fr))" in h and h.count("grid-column:1/-1") == 1 and "width:50%" in h
    assert k("return S.rijen([null, false], 2);") == ""


def test_states_helpers():
    s = {"sensor.a": st(21.46), "sensor.b": st("unavailable"), "sensor.c": st("x", unit_of_measurement="°C")}
    assert k("return S.waarde('sensor.a', 1, ' °C');", s) == "21,5 °C"
    assert k("return S.waarde('sensor.b', 1);", s) == "—"
    assert k("return S.waarde('sensor.zz', 1);", s) == "—"
    assert k("return [S.weg('sensor.b'), S.weg('sensor.a'), S.weg('sensor.zz')].join();", s) == "true,false,true"
    assert k("return S.attr('sensor.c', 'unit_of_measurement');", s) == "°C"


def test_oordeel_en_drempel():
    assert ">in orde<" in k("return S.oordeel([]);")
    assert ">warm<" in k("return S.oordeel([{k: 'warn', t: 'warm'}]);")
    h = k("return S.oordeel([{k: 'warn', t: 'a'}, {k: 'bad', t: 'b'}]);")
    assert ">2 meldingen<" in h and "var(--ov-bad)" in h
    assert k("return [S.drempel(80, 85, 92), S.drempel(86, 85, 92), S.drempel(93, 85, 92), S.drempel(null, 1, 2)].join();") == "ok,warn,bad,ink-35"
    assert k("return [S.drempel(50, 20, 10, true), S.drempel(15, 20, 10, true), S.drempel(5, 20, 10, true)].join();") == "ok,warn,bad"
    assert k("return [S.duur(5*60000), S.duur(3*3600000), S.duur(72*3600000)].join('|');") == "5 min|3 uur|3 dagen"


def test_geladen_voor_lovelace():
    res = [r["url"] for r in laad(os.path.join(CONFIG, "dashboards", "resources.yaml"))]
    extra = laad(os.path.join(CONFIG, "configuration.yaml"))["frontend"]["extra_module_url"]
    kit = [u for u in extra if u.startswith("/local/sv-kit.js")]
    assert len(kit) == 1 and kit[0] in res


def test_templates():
    for naam in ("sv_html", "sv_paneel"):
        stijl = {kk: v for d in TPL[naam]["styles"]["card"] for kk, v in d.items()}
        assert stijl["pointer-events"] == "auto", naam
    assert TPL["sv_paneel"]["template"] == "sv_html"
    assert TPL["sv_html"]["tap_action"]["action"] == "none"


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
