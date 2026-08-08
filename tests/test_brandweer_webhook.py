"""Offline test van de `variables:` van automation `brandweer_webhook_main`.

Die automatisering moet uit een P2000-webhook drie dingen afleiden: welke body
er opgeslagen wordt, welke tekst er omgeroepen wordt, en of het om een
na-alarmering gaat (extra materieel op een uitruk die al loopt). Dat laatste
bepaalt of `brandweer_count_teams` een uitruk bijtelt, dus een fout hier kost
stilletjes een verkeerde jaarstand.

De templates worden hier UIT HET YAML-BESTAND gelezen, niet overgetypt: anders
test dit een kopie die na de eerste wijziging niet meer klopt.

Draaien:  python3 -m pytest tests/test_brandweer_webhook.py
"""

import os
import re

import yaml
from jinja2.nativetypes import NativeEnvironment

PAKKET = os.path.join(
    os.path.dirname(__file__), "..", "packages", "9 - Other", "Brandweer Automations.yaml"
)


class _Loader(yaml.SafeLoader):
    pass


# !secret e.d. hoeven we hier niet op te lossen.
_Loader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _webhook_variables():
    with open(PAKKET, encoding="utf-8") as fh:
        pakket = yaml.load(fh, Loader=_Loader)
    for automatisering in pakket["brandweer_package"]["automation"]:
        if automatisering["id"] == "brandweer_webhook_main":
            return automatisering["variables"]
    raise AssertionError("automation brandweer_webhook_main niet gevonden")


ENV = NativeEnvironment()
# HA's regex_replace; de rest van de gebruikte filters zit al in Jinja zelf.
ENV.filters["regex_replace"] = lambda waarde, zoek="", vervang="": re.sub(
    zoek, vervang, str(waarde)
)


def render(payload, opgeslagen, leeftijd_seconden):
    """Bootst na wat HA doet: variabelen op volgorde renderen, elk met de
    voorgaande in de context. `now()` en de state-machine worden vervangen door
    vaste waarden, zodat de test niet van de klok afhangt."""
    context = {
        "trigger": {"json": payload},
        "states": lambda _entiteit: opgeslagen,
    }
    for naam, template in _webhook_variables().items():
        bron = template
        # De twee plekken die de state-machine aanraken op iets vaststaands
        # zetten; de rest van de template blijft letterlijk zoals in de config.
        bron = bron.replace(
            "(now() - states.input_text.brandweer_laatste_melding.last_changed).total_seconds()",
            str(leeftijd_seconden),
        )
        context[naam] = ENV.from_string(bron).render(**context)
    context["dedup_door"] = (
        context["melding_body"] != "" and context["melding_body"] != opgeslagen
    )
    return context


BODY_TS = "P 2 BOB-01 BR berm/bosschage Hoge Randweg Volkel 213831"
BODY_WATERWAGEN = "P 2 BOB-01 BR berm/bosschage Hoge Randweg Volkel 213861"
BODY_HEIDE = "P 1 BR heide (Uitbr.: hoog) Goordreef Erp 210093 210091 213861 214131 222841"
BODY_HEIDE_NA = "P 1 BR heide (Uitbr.: hoog) Goordreef Erp 222841"
BODY_ANDERE_STRAAT = "P 2 BOB-02 OMS brandmelding Industrielaan Uden 213831"
TTS_TS = "Prio 2, Brand berm bosschage Hoge Randweg Volkel, 1e Tankautospuit van Uden."
TTS_WATERWAGEN = "Prio 2, Brand berm bosschage Hoge Randweg Volkel, Waterwagen van Uden."


def payload(incident, trigger_bericht=None, tts=None, trigger_tts=None):
    """`trigger_bericht=None` bootst de oude verzender na, die het veld niet stuurt."""
    json = {"incident": {"body": incident}, "tts_text": tts}
    if trigger_bericht is not None:
        json["trigger_message"] = {"body": trigger_bericht}
        json["trigger_tts_text"] = trigger_tts
    return json


# (naam, payload, opgeslagen melding, leeftijd, verwacht na_alarmering, verwacht doorgelaten, verwachte tts)
SCENARIOS = [
    (
        "eerste bericht op after_enrichment",
        payload(BODY_TS, BODY_TS, TTS_TS, TTS_TS),
        "een oude melding van gisteren",
        90000,
        False,
        True,
        TTS_TS,
    ),
    (
        # Delivery 119023: de waterwagen zat alleen in trigger_message, terwijl
        # incident.body en tts_text nog de tankautospuit beschreven.
        "na-alarmering op after_enrichment",
        payload(BODY_TS, BODY_WATERWAGEN, TTS_TS, TTS_WATERWAGEN),
        BODY_TS,
        30,
        True,
        True,
        TTS_WATERWAGEN,
    ),
    (
        # Hier zijn trigger_message en incident gelijk; het verschil tussen die
        # twee velden kan een na-alarmering dus niet aanwijzen.
        "na-alarmering op after_type_enrichment met elk bericht",
        payload(BODY_WATERWAGEN, BODY_WATERWAGEN, TTS_WATERWAGEN, TTS_WATERWAGEN),
        BODY_TS,
        30,
        True,
        True,
        TTS_WATERWAGEN,
    ),
    (
        "oude verzender zonder trigger_message",
        payload(BODY_TS, None, TTS_TS),
        "een oude melding van gisteren",
        90000,
        False,
        True,
        TTS_TS,
    ),
    (
        "dubbele webhook met dezelfde body wordt geweigerd",
        payload(BODY_TS, BODY_TS, TTS_TS, TTS_TS),
        BODY_TS,
        5,
        None,
        False,
        None,
    ),
    (
        "na-alarmering op een melding met een rij eenheden",
        payload(BODY_HEIDE_NA, BODY_HEIDE_NA, TTS_WATERWAGEN, TTS_WATERWAGEN),
        BODY_HEIDE,
        45,
        True,
        True,
        TTS_WATERWAGEN,
    ),
    (
        "nieuwe uitruk naar een andere straat telt gewoon mee",
        payload(BODY_ANDERE_STRAAT, BODY_ANDERE_STRAAT, TTS_TS, TTS_TS),
        BODY_TS,
        600,
        False,
        True,
        TTS_TS,
    ),
    (
        # Buiten het venster van 2 uur: dit is een nieuwe uitruk naar dezelfde
        # straat, geen na-alarmering, en moet dus wel geteld worden.
        "zelfde straat vijf uur later is een nieuwe uitruk",
        payload(BODY_WATERWAGEN, BODY_WATERWAGEN, TTS_WATERWAGEN, TTS_WATERWAGEN),
        BODY_TS,
        18000,
        False,
        True,
        TTS_WATERWAGEN,
    ),
]


def test_webhook_scenarios():
    fouten = []
    for naam, json, opgeslagen, leeftijd, na_alarm, doorgelaten, tts in SCENARIOS:
        c = render(json, opgeslagen, leeftijd)
        if c["dedup_door"] != doorgelaten:
            fouten.append(f"{naam}: doorgelaten={c['dedup_door']}, verwacht {doorgelaten}")
        if na_alarm is not None and c["na_alarmering"] != na_alarm:
            fouten.append(f"{naam}: na_alarmering={c['na_alarmering']}, verwacht {na_alarm}")
        if tts is not None and c["melding_tts"] != tts:
            fouten.append(f"{naam}: tts={c['melding_tts']!r}, verwacht {tts!r}")
    assert not fouten, "\n".join(fouten)


def test_na_alarmering_is_een_echte_boolean():
    """HA rendert met native types; wordt dit een string, dan is
    `input_boolean.turn_{{ 'on' if na_alarmering else 'off' }}` altijd `on`,
    want een niet-lege string is waar."""
    c = render(payload(BODY_TS, BODY_TS, TTS_TS, TTS_TS), "iets anders", 90000)
    assert isinstance(c["na_alarmering"], bool), type(c["na_alarmering"])
    assert isinstance(c["gebruik_trigger_bericht"], bool)
