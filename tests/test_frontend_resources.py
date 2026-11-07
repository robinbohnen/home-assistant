"""Offline test van de frontend-resources (dashboards/resources.yaml en
`frontend.extra_module_url` in configuration.yaml).

Draaien:  .venv/bin/python tests/test_frontend_resources.py      (nodig: pyyaml)

Bewaakt wordt:
1. geen enkele resource laadt nog van `/hacsfiles/`. Sinds de overstap van HACS
   naar de Marketplace (november 2026) staan de bestanden onder
   `/local/community/`; `/hacsfiles/` wordt alleen nog uit compatibiliteit
   geserveerd en levert een reparatiemelding op;
2. elke module in `extra_module_url` staat met exact dezelfde URL (inclusief
   `?v=`) in resources.yaml. Wijkt één teken af, dan ziet de browser twee
   modules en voert hij card-mod of kiosk-mode dubbel uit;
3. elke resource heeft `type: module` en geen URL komt twee keer voor.
"""
import os

import yaml

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = f"{CONFIG}/dashboards/resources.yaml"
CONFIGURATION = f"{CONFIG}/configuration.yaml"


class HALoader(yaml.SafeLoader):
    """SafeLoader die HA-tags als !include en !secret negeert."""


HALoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def laad(pad):
    with open(pad, encoding="utf-8") as f:
        return yaml.load(f, Loader=HALoader)


def resources():
    return laad(RESOURCES)


def extra_modules():
    return laad(CONFIGURATION)["frontend"]["extra_module_url"]


def test_geen_hacsfiles():
    oud = [r["url"] for r in resources() if r["url"].startswith("/hacsfiles/")]
    oud += [u for u in extra_modules() if u.startswith("/hacsfiles/")]
    assert not oud, f"nog op het oude HACS-pad, wordt /local/community/: {oud}"


def test_extra_modules_gelijk_aan_resources():
    urls = {r["url"] for r in resources()}
    los = [u for u in extra_modules() if u not in urls]
    assert not los, f"extra_module_url wijkt af van resources.yaml (dubbel geladen): {los}"


def test_eigen_modules_gaan_mee_naar_de_server():
    # .gitignore negeert alles behalve een allowlist. Een eigen module in www/
    # zonder `!www/<bestand>` komt nooit op de server: sv-kit.js liet zo op
    # 7-11-2026 elk paneel van zes weergaven leeg. HACS-bestanden
    # (/local/community/) en bestanden die hier lokaal niet bestaan (de
    # handmatige F1-kaart) vallen erbuiten.
    import subprocess
    urls = {r["url"] for r in resources()} | set(extra_modules())
    eigen = []
    for url in urls:
        if not url.startswith("/local/") or url.startswith("/local/community/"):
            continue
        rel = "www/" + url[len("/local/"):].split("?")[0]
        if os.path.exists(os.path.join(CONFIG, rel)):
            eigen.append(rel)
            r = subprocess.run(["git", "check-ignore", "-q", rel], cwd=CONFIG)
            assert r.returncode == 1, f"{rel} wordt door .gitignore genegeerd: zet `!{rel}` erbij"
    assert "www/sv-kit.js" in eigen and "www/ov-tokens.js" in eigen


def test_resources_type_en_uniek():
    lijst = resources()
    assert all(r.get("type") == "module" for r in lijst)
    urls = [r["url"] for r in lijst]
    assert len(urls) == len(set(urls)), "dubbele resource-URL"


if __name__ == "__main__":
    for naam, fn in list(globals().items()):
        if naam.startswith("test_"):
            fn()
            print(f"ok  {naam}")
