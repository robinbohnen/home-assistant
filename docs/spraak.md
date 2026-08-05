# Spraak

Home Assistant Voice PE in de keuken. Dit stuk beschrijft wat er is, waarom het
zo staat en wat je aan moet zetten voor het werkt.

| Waar | Wat |
| ---- | --- |
| `packages/0 - Ground Floor/Kitchen/Voice.yaml` | De intents, het vraag/antwoord-mechanisme en de omroep-scripts |
| `custom_sentences/nl/huis.yaml` | De zinnen die bij die intents horen |
| `configuration.yaml` | `assist_pipeline` / `conversation` / `intent` (zitten normaal in `default_config`, en die staat uit) |
| `tests/test_spraak.py` | Rendert elke gesproken tekst offline |

## Waarom de keuken

Het is de enige ruimte zonder bewegingssensor, het is de plek waar je handen
vol zitten, en de Sonos die er al hangt kan de langere teksten overnemen. Het
speakertje van de satelliet is prima voor één zin, niet voor een mededeling aan
het hele huis — vandaar het veld `sonos` op `script.spraak_omroepen`.

## De ketting

```
wakewoord (op het apparaat)  →  Whisper (Wyoming)  →  conversation  →  Piper (Wyoming)
```

Whisper en Piper draaien al als Wyoming-dienst; deze installatie draait in een
container, dus die staan náást Home Assistant en niet als add-on.

**De Azure-stem kun je hier niet voor gebruiken.** Die staat als klassiek
`tts:`-platform in `configuration.yaml`, en zulke platforms leveren alleen de
dienst `tts.microsoft_say` — geen entiteit. Een pipeline en `tts.speak` willen
juist een entiteit. Voor spraak is de keuze dus Piper (lokaal, en het past bij
de rest van de keten) of `tts.google_translate_nl_nl`, de stem die het alarm en
de brandweermelding al gebruiken.

## Na het koppelen

1. De satelliet is `assist_satellite.home_assistant_voice_09a3f2_assist_satellite`
   — de naam die ESPHome zelf meegeeft, met het serienummer erin. Dat id staat
   op twee plekken in de YAML: als `default` van het veld `satelliet` van
   `script.spraak_vraag_stellen` en `script.spraak_omroepen`. Hernoem je het
   apparaat later (het wordt dan `assist_satellite.<nieuwe naam>`), dan zijn dat
   de enige twee regels die mee moeten.
2. Maak een pipeline (Instellingen → Spraakassistenten) met Whisper als STT en
   Piper als TTS, en hang die aan de satelliet.
3. Stel entiteiten **expliciet** bloot aan Assist. Net als op de dashboards
   geldt hier: aanwijzen wat er wél in hoort, geen alles-behalve-lijst. Een
   verkeerd blootgestelde entiteit is hier vervelender dan op een dashboard,
   want spraak raadt: "doe het licht uit" kiest zelf welke lamp het meest lijkt
   op wat je zei.
4. **Stel `cover.achtertuin_zonnescherm` niet bloot.** Die cover is omgekeerd
   bedraad (HA-stand `open` = scherm uitgeschoven), dus de ingebouwde
   cover-intent doet bij "doe het zonnescherm dicht" het omgekeerde van wat je
   bedoelt. Daarvoor zijn `ZonneschermUit` en `ZonneschermIn`, in de woorden
   die je in de tuin gebruikt.
5. Herstart volledig. Nieuwe pakketbestanden én nieuwe zinnen worden allebei
   niet met een reload ingelezen.

## Wat je kunt vragen

| Intent | Bijvoorbeeld | Antwoord uit |
| ------ | ------------ | ------------ |
| `BrandweerBezetting` | "hoeveel man staat er op de kazerne" | `sensor.brandweer_bezetting`, met terugval op de REST-sensor |
| `StroomprijsNu` | "is de stroom nu goedkoop" | Zonneplan + `sensor.stroomprijs_niveau_volgend_uur` |
| `ZonneschermAdvies` | "moet het zonnescherm eruit" | `sensor.zonwering_advies_zonnescherm` |
| `ZonneschermUit` / `ZonneschermIn` | "zet het zonnescherm uit" | doet het, en zegt het als de regie het er niet mee eens is |
| `HuisOpen` | "staat er nog iets open" | `sensor.kamers` |
| `HuisAandacht` | "hoe staat het huis ervoor" | `sensor.kamers`, hoogstens drie ruimtes |
| `LichtenUit` | "alle lichten uit" | dezelfde lampgroepen als de nachtelijke auto-uit |
| `AntwoordJa` / `AntwoordNee` | "ja" / "laat maar" | de vraag die op dat moment open staat |

De zinnen worden **letterlijk** gematcht; er zit geen taalmodel tussen. Wat niet
in `custom_sentences/nl/huis.yaml` staat, wordt niet herkend. Een formulering
die je jezelf twee keer hoort gebruiken hoort er dus gewoon bij.

## Het huis dat zelf begint

`assist_satellite.start_conversation` laat de satelliet een vraag stellen en
daarna luisteren. Alleen: "ja" is een zin als alle andere en zou zonder context
ook morgenochtend nog ergens op slaan. Daarom:

- `input_text.spraak_openstaande_vraag` bevat de **sleutel** van de vraag die
  open staat (`zonnescherm`), niet de vraagtekst — dan mag de tekst veranderen
  zonder dat de afhandeling meeverandert.
- `timer.spraak_antwoordvenster` bepaalt hoe lang een antwoord nog telt. Loopt
  hij af, dan ruimt `automation.spraak_vraag_opruimen` de vraag op.
- Een antwoord komt naar buiten als event `spraak_antwoord` met `vraag` en
  `antwoord` in de data. Dat is dezelfde opzet als het `virtual_button`-event:
  de vragensteller hoeft niets van spraak te weten, en blijft werken als de
  satelliet er niet is.

Zo hangt het zonnescherm eraan:

```
Klimaat - Zonnescherm vragen
  ├── notify.mobile_devices_adults      (knoppen Ja / Nee)
  └── script.spraak_vraag_stellen       (alleen als er iemand thuis is)
        └── event spraak_antwoord       ← AntwoordJa / AntwoordNee
              → wait_for_trigger in dezelfde automation, trigger-id ja / nee
```

Wie het eerst antwoordt wint; daarna sluit de automation de openstaande vraag.
Antwoordt niemand, dan gebeurt er niets — precies zoals het al werkte.

Een nieuwe vraag toevoegen:

1. Roep `script.spraak_vraag_stellen` aan met een eigen `vraag`-sleutel en de
   tekst die de satelliet moet stellen.
2. Zet in de automation die de vraag stelt twee event-triggers op
   `spraak_antwoord` met die sleutel, met dezelfde trigger-id's als de knoppen
   van je notificatie.
3. Wil je een specifieke bevestiging horen ("Doe ik, het zonnescherm gaat
   eruit"), zet die dan in de mapping in `AntwoordJa` / `AntwoordNee`. Zonder
   mapping antwoordt het huis "Doe ik."

## Testen

```bash
.venv/bin/pip install jinja2 pyyaml
.venv/bin/python tests/test_spraak.py
```

De test rendert elke gesproken tekst met nagebootste sensoren en bewaakt de
randgevallen die je anders pas hoort als het misgaat: een brandweer-webhook die
sinds de herstart niets gestuurd heeft, `very_low` als tariefniveau (testen op
`== 'low'` is precies de fout die dit huis al eens gemaakt heeft), een
`sensor.kamers` die er even niet is, en het omgekeerde zonnescherm. Ook bewaakt
hij dat elke zin een intent heeft en elke intent een zin — die twee lopen
anders geruisloos uit elkaar.

## Wat hier nog niet staat

- **Een taalmodel als vangnet.** De laag hierboven: alles wat niet in de
  zinnenlijst staat naar een LLM, met "probeer eerst lokale intents" aan. Dan
  blijft dit bestand de baas over wat het huis over zichzelf zegt en vangt het
  model de rest ("zet het wat gezelliger hier").
- **De LED-ring als statuslamp.** De ring is een gewone light-entity; als er
  niet gepraat wordt kan hij het tariefniveau, het alarm of de bezetting op de
  kazerne laten zien.
- **"Welterusten"** als zin bij `LichtenUit`. Bewust nog niet toegevoegd: het
  is een woord dat hier ook zonder bedoeling valt, en dan gaat het licht uit
  terwijl er nog iemand zit.
