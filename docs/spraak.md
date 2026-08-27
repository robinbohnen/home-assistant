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
wakewoord (op het apparaat)  →  Microsoft STT  →  conversation  →  Microsoft TTS
```

Zo staat de pipeline "Home Assistant" ingesteld (peildatum 2026-08-05). Whisper
en Piper draaien er als Wyoming-dienst naast en zijn de lokale alternatieven;
deze installatie draait in een container, dus die staan náást Home Assistant en
niet als add-on.

De Azure-stem is dus gewoon te kiezen in een pipeline. Of `tts.speak` hem ook
kan aansturen is een andere vraag: dat vraagt een `tts.`-entiteit, en een
klassiek `tts:`-platform uit `configuration.yaml` levert alleen de dienst
`tts.microsoft_say`. Kijk in Toestanden welke `tts.`-entiteiten er zijn; staat
de Microsoft-stem er tussen, dan is dat de betere default voor het veld `stem`
van `script.spraak_omroepen` (nu `tts.google_translate_nl_nl`, de stem die het
alarm en de brandweermelding al gebruiken).

## Na het koppelen

1. De satelliet is `assist_satellite.home_assistant_voice_09a3f2_assist_satellite`
   — de naam die ESPHome zelf meegeeft, met het serienummer erin. Dat id staat
   op twee plekken in de YAML: als `default` van het veld `satelliet` van
   `script.spraak_vraag_stellen` en `script.spraak_omroepen`. Hernoem je het
   apparaat later (het wordt dan `assist_satellite.<nieuwe naam>`), dan zijn dat
   de enige twee regels die mee moeten.
2. Controleer welke pipeline het apparaat gebruikt (Instellingen → Apparaten →
   het apparaat → **Assistent**) en zet in díe pipeline de conversatieagent.
   Staat het apparaat op "Voorkeur", dan pakt hij de standaard-pipeline en niet
   per se degene die je net hebt aangepast — dat is de makkelijkste manier om
   een uur te zoeken naar niets.
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
| `ThuisAccu` | "hoe vol zit de accu" | de Marstek-sensoren, met de laad/ontlaad-logica van de klokken-app |
| `Zonnepanelen` | "wat leveren de panelen nu" | `sensor.zon_vermogen_nu` + `sensor.zon_opgewekt_vandaag` + de capacity-sensoren |
| `AutoStatus` | "kan ik weg met de auto" | de Mégane-sensoren: percentage, actieradius, stekker en laadtijd |
| `ReistijdWerk` | "hoe druk is het naar het werk" | `sensor.robin_reistijd_naar_werk` (Waze) |
| `WieThuis` | "wie is er allemaal thuis" | de leden van `group.all_adults` + `group.all_children`, voornamen uit de friendly name |
| `Afval` | "welke bak moet aan de straat" | `sensor.afvalinfo_home_trash_type_today/_tomorrow` |
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

Het huis vraagt met **`assist_satellite.ask_question`**: die stelt de vraag,
luistert, en matcht je antwoord tegen een lijstje zinnen dat je in dezelfde
aanroep meegeeft. Het antwoord komt terug in een `response_variable`.

**Niet met `start_conversation`** — dat is de voor de hand liggende keuze en hij
werkt hier niet:

```
Built-in conversation agent does not support starting conversations
```

Dat ligt niet aan het apparaat (`supported_features` van de Voice PE stond op 3,
dus die kan het prima), maar aan de gespreksagent: alleen een agent die een
gesprek kan vóórtzetten — een taalmodel — mag er een beginnen. `ask_question`
gaat om de agent heen en werkt daarom ook met de ingebouwde. Voor een
ja/nee-vraag is dat bovendien beter: geen model, geen kosten, geen wachttijd.

Die fout kwam nergens terecht: de spreek-actie staat op `continue_on_error`, dus
de automatisering meldde "met succes uitgevoerd" en de keuken bleef stil. Zoiets
zie je alleen in de trace van het script zelf, niet in die van de automatisering
die hem aanroept.

**Een aanroeper die op het antwoord wacht, moet het script met `script.turn_on`
starten.** Een gewone scriptaanroep wacht tot het script klaar is — en dat
script staat te wachten op jouw antwoord. Het `spraak_antwoord`-event zou dan
gevuurd zijn vóór de `wait_for_trigger` begint te luisteren, en spoorloos
verdwijnen. Met `script.turn_on` loopt het script ernaast.

`ask_question` luistert één keer. Zeg je niets, of iets dat er niet op lijkt,
dan is dat moment weg — precies wanneer je twee minuten later alsnog "ja" roept.
Daarom blijft de vraag daarna nog even open staan:

- `input_text.spraak_openstaande_vraag` bevat de **sleutel** van de vraag die
  open staat (`zonnescherm`, `spa_gratis`, `spa_warm`), niet de vraagtekst — dan
  mag de tekst veranderen zonder dat de afhandeling meeverandert.
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
  └── script.turn_on → spraak_vraag_stellen   (alleen als er iemand thuis is)
        ├── ask_question: vraagt en luistert  → event spraak_antwoord
        └── geen bruikbaar antwoord? vraag blijft open
              → "Okay Nabu, ja"  → AntwoordJa / AntwoordNee → hetzelfde event
                    → wait_for_trigger in dezelfde automation, trigger-id ja / nee
```

Wie het eerst antwoordt wint — de satelliet, de telefoon of een laat "ja";
daarna sluit de automation de openstaande vraag. Antwoordt niemand, dan gebeurt
er niets — precies zoals het al werkte.

Een nieuwe vraag toevoegen:

1. Start `script.spraak_vraag_stellen` (via `script.turn_on`, zie hierboven) met
   een eigen `vraag`-sleutel en de tekst die de satelliet moet stellen.
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
  model de rest ("zet het wat gezelliger hier"). Voor de ja/nee-vragen is het
  niet nodig — `ask_question` doet dat zonder model.
- **De LED-ring als statuslamp.** De ring is een gewone light-entity; als er
  niet gepraat wordt kan hij het tariefniveau, het alarm of de bezetting op de
  kazerne laten zien.
- **"Welterusten"** als zin bij `LichtenUit` of `RoutineAvond`. Bewust nog
  steeds niet toegevoegd, ook nu de routines er wél zijn: het is een woord dat
  hier ook zonder bedoeling valt, en tijdens een open antwoordvenster luistert
  de satelliet zonder wake word. Een welterusten tegen de kinderen zou dan het
  huis op slot doen. Vandaar `ik ga slapen` en `start de avondroutine`, en om
  dezelfde reden geen kaal `goedemorgen`.

## Acties (sinds 14 augustus 2026)

De intents hierboven lezen af; deze groep grijpt in.

| Intent | Doet | Rem |
| --- | --- | --- |
| `RoutineAvond` / `RoutineOchtend` | Vuurt het event `huis_routine` | Geen eigen logica: de router in `packages/1 - First Floor/Bedroom/Buttons.yaml` blijft de enige plek waar staat wát een routine inhoudt, dus dit is per definitie gelijk aan de knop naast het bed |
| `AutoAirco` | Drukt `button.hrh85f_start_air_conditioner` | Weigert onder de SoC-drempel die de auto zélf meldt (`sensor.hrh85f_hvac_soc_threshold`), en zegt het als de stekker er niet in zit |
| `AlarmAan` | `alarmo.arm`, thuis of afwezig op basis van `group.all_adults` | — |

**Het alarm kan met de stem alleen aan en nooit uit.** Een gesproken commando
is niet te onderscheiden van iemand die door de brievenbus roept, en een
satelliet hoort ook wat er op tv gebeurt. Uitzetten blijft aan het slot, de app
en de code.
