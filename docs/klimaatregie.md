# Klimaatregie

Eén regie over de buitenzonwering, zodat het huis 's zomers koel blijft en
's winters warm. Vervangt vijf automatiseringen die onafhankelijk van elkaar
aan dezelfde rolluiken trokken.

## Waarom

De oude opzet had drie problemen:

- **Reactief.** Rolluiken gingen pas dicht als de lux-sensor 15 minuten boven
  de drempel zat. Dan is de warmte al binnen, en eruit krijg je hem niet meer.
- **Geen seizoen.** Zon was altijd de vijand. In de winter is zon op het raam
  juist gratis verwarming en een dicht rolluik 's nachts gratis isolatie.
- **Handbediening verloor.** Zette je een rolluik zelf open, dan draaide de
  volgende trigger het binnen een kwartier terug.

## De vier lagen

| Laag | Wat | Waar |
|---|---|---|
| 1. Regime | Wat voor dag wordt het? | `packages/9 - Other/Klimaat Regime.yaml` |
| 2. Gevelzon | Waar staat de zon nu? | idem |
| 3. Advies | Wat wil elke zone? | `packages/9 - Other/Klimaat Zonwering.yaml` |
| 4. Uitvoeren | Doen, tenzij… | idem |
| Beslistabel | De regels zelf | `custom_templates/klimaat.jinja` |

**Alles wat over gedrag gaat staat in `custom_templates/klimaat.jinja`.** De
packages meten en voeren uit, meer niet. Moet het huis zich anders gedragen,
dan is dat ene bestand de plek.

### Laag 1 — Regime van de dag

`automation.klimaat_regime_bepalen` haalt om 05:30 (en nog eens om 12:00) de
verwachte maximumtemperatuur op bij `weather.knmi_thuis` en zet daarmee
`input_select.klimaat_regime`:

| Regime | Wanneer | Strategie |
|---|---|---|
| Koelen | verwachte max ≥ 23 °C | zon buiten houden, 's nachts spuien |
| Verwarmen | verwachte max ≤ 14 °C | zon binnenhalen, 's nachts isoleren |
| Neutraal | ertussenin | alleen comfort |

Omdat dit op de *verwachting* draait en niet op de gemeten temperatuur, kan de
zonwering op een hete dag al vóór de warmte dicht. Een dag boven
`klimaat_hittedag_vanaf` (28 °C) telt als **hittedag**: dan wordt er ook
preventief gedimd aan de kant waar de zon naartoe draait.

Regime tijdelijk vastzetten: `input_boolean.klimaat_regime_handmatig` aan, dan
laat de automatisering de keuze met rust.

### Laag 2 — Gevelzon

Per gevel twee sensoren:

- `binary_sensor.zon_richting_<gevel>` — de zon staat geometrisch aan die kant
  (azimut + hoogte). Loopt vóór op het licht, dus bruikbaar om preventief te
  sluiten.
- `binary_sensor.zon_op_<gevel>` — hij schijnt er nu echt op: richting **en**
  genoeg licht op de lux-sensor van die tuin.

De lux-drempel heeft hysterese (aan bij 20.000, uit pas onder 14.000) plus
`delay_on` van 2 en `delay_off` van 10 minuten. Anders staat de zonwering te
klepperen bij overdrijvende wolken.

### Laag 3 — Advies per zone

Zeven zones, elk met een sensor `sensor.zonwering_advies_<zone>`:

| Zone (slug) | Cover | Gevel | Bijzonder |
|---|---|---|---|
| `keuken_screens` | `cover.covers_kitchen_screens` | voor | screen: geen kier, in bij storm |
| `kantoor_links` | `cover.kantoor_links_low_speed` | voor | |
| `kantoor_rechts` | `cover.kantoor_rechts_low_speed` | achter | |
| `badkamer` | `cover.badkamer_rolluik_low_speed` | achter | stille uren |
| `slaapkamer` | `cover.slaapkamer_rolluik_low_speed` | achter | stille uren |
| `slaapkamer_logan` | `cover.covers_bedroom_maxi` | voor | slaapvenster vanaf 19:00 |
| `slaapkamer_emma` | `cover.slaapkamer_mini` | achter | slaapvenster vanaf 19:00 |

De slug bepaalt de naam van de bijbehorende helpers:
`sensor.zonwering_advies_<slug>`, `timer.override_<slug>` en
`input_boolean.zonwering_handmatig_<slug>`. Voeg je een zone toe, geef hem dan
een slug die gelijk is aan het entity_id dat Home Assistant van de sensornaam
maakt — anders vindt de uitvoerder de zone niet.

> **Controleer de gevelindeling.** Die is afgeleid uit de oude automatisering
> `covers_morning_routine` (in de tak "Sunny Backyard" gingen badkamer,
> slaapkamer, mini en kantoor-rechts dicht terwijl maxi en kantoor-links open
> gingen). Klopt het niet, wijzig dan `gevel` in `klimaat.jinja`.

De staat van zo'n sensor is `open`, `kier`, `dicht` of `rust` (= niet bewegen).
Attributen: `positie` (0–100 of −1), `uitvoeren`, `reden` en `blokkade`.
`reden` is bewust in gewone taal geschreven, dat is wat je op het dashboard
leest als je je afvraagt waarom een rolluik doet wat het doet.

De beslistabel, van hoog naar laag:

1. **Stille uren** (22:00–07:00, voor slaapkamers en badkamer): niet bewegen.
   Enige uitzondering is openen naar een kier om te spuien als het binnen echt
   te warm is.
2. **Slaapvenster kinderkamer** (vanaf 19:00): dicht. Op een hittedag een kier,
   en dat staat de hele dag vast, zodat het niet midden in de nacht alsnog van
   gedachten verandert.
3. **Nacht**: dicht, of een kier bij nachtspui in het koelregime.
4. **Overdag per regime**:
   - *Koelen*: zon op de gevel → dicht. Niemand thuis op een warme dag → dicht.
     Hittedag met de zon in aantocht → kier. Kamer boven de comfortgrens →
     kier. Anders open.
   - *Verwarmen*: zon → open (gratis warmte), tenzij de kamer al te warm is.
     Anders open voor het daglicht.
   - *Neutraal*: open, tenzij zon én een warme kamer.
5. **Airco koelt** in die zone → geen open rolluik; anders koel je de straat.
6. **Screens**: kennen geen kier, gaan 's nachts omhoog, en gaan altijd in bij
   een KNMI-waarschuwing of vorst. Die veiligheidsregel staat als laatste en
   overschrijft al het bovenstaande.

### Laag 4 — Uitvoeren

`automation.klimaat_zonwering_uitvoeren` loopt de zeven zones langs en beweegt
alleen als het advies mag worden uitgevoerd én de huidige stand meer dan 5%
afwijkt. Er is dus geen beweging als er niets te winnen valt.

`automation.klimaat_handbediening_herkennen` is de tegenhanger: elke beweging
die 90 seconden stil ligt op een *andere* stand dan het advies telt als
handbediening — via de app, een knop, een wandschakelaar of een van de oude
automatiseringen. Die zone wordt dan 4 uur met rust gelaten
(`timer.override_<zone>`). Zet je hem terug op de geadviseerde stand, dan
vervalt de uitzondering meteen weer.

Onze eigen bewegingen eindigen per definitie op het advies en worden daarom
nooit als handbediening gezien. Dat is de hele truc: geen contextgegoochel,
gewoon kijken waar de cover uiteindelijk blijft staan.

> **Let op de ochtendknop.** Druk je 's ochtends op de slaapkamerknop, dan
> gaan de rolluiken open en telt dat als handbediening: die zones liggen dan
> vier uur stil. Op een hete ochtend blijft de zonwering daardoor open terwijl
> de zon al op de gevel staat. Merk je dat, zet `klimaat_override_uren` dan
> lager (2 uur is een prima waarde). De knop-automatisering kijkt zelf al naar
> de lichtsterkte en laat de zonzijde met rust als het al fel is.

## Aanzetten en terugdraaien

Alles hangt aan één schakelaar: **`input_boolean.klimaatregie_actief`**.

- **Uit**: hier beweegt niets, en de oude automatiseringen doen hun oude werk.
- **Aan**: de klimaatregie stuurt, en de oude automatiseringen stappen opzij.

Die laatste hebben daarvoor een conditie gekregen (`state: "off"`):

- `covers_sun_protection`, `covers_morning_routine`, `covers_bedtime`
  (`packages/9 - Other/Covers.yaml`)
- `bedroom_maxi_covers`, `bedroom_mini_covers`
- de vier `cover.close_cover`-acties in `temp_control_automation` — de
  meldingen daar blijven wél gewoon werken

Ongemoeid gelaten, omdat het gebruikersacties zijn die de handbediening-laag
netjes afvangt: de knop-automatiseringen (slaapkamer, kantoor, badkamer), de
keuken-rolgordijnen (binnenzonwering, gaat over inkijk), het achtertuin-
zonnescherm (heeft een eigen bevestigingsvraag) en het sluiten van de rolluiken
door `script_attic_ac` voordat de airco aangaat.

## Uitrollen

1. **Herstart Home Assistant.** Nieuwe packages én `custom_templates/` worden
   alleen bij het opstarten ingelezen.
2. **Meekijken met de hoofdschakelaar uit.** Ga naar de weergave *Klimaat*
   (`/lovelace/klimaat`) en vergelijk een week lang de kolommen "Advies" en
   "Werkelijke stand". Er beweegt nog niets. Klopt een advies niet, dan pas je
   `klimaat.jinja` of de drempels aan.
3. **Gevels kalibreren** (optioneel maar de moeite waard). De azimut-sectoren
   staan standaard op 0–360°, waardoor het systeem puur op de lux-sensoren
   draait. Kijk op een zonnige dag in de grafiek "Zonstand tegen het licht
   buiten" bij welke azimut de voortuin oploopt en weer wegzakt, en vul die twee
   getallen in bij `klimaat_voorgevel_azimut_van/tot`. Idem voor achter. Daarna
   reageert de zonwering eerder en rustiger.
4. **Aanzetten.** `input_boolean.klimaatregie_actief` aan. Wil je voorzichtig
   beginnen, zet dan eerst `zonwering_handmatig_*` aan voor de slaapkamers, zodat
   alleen kantoor, badkamer en de keukenscreens meedoen.

Terugdraaien is altijd één schakelaar, op elk moment.

## Instellingen

| Helper | Standaard | Wat het doet |
|---|---|---|
| `klimaat_koelen_vanaf` | 23 °C | verwachte max waarboven het koelregime geldt |
| `klimaat_verwarmen_tot` | 14 °C | verwachte max waaronder het verwarmregime geldt |
| `klimaat_hittedag_vanaf` | 28 °C | vanaf hier preventief dimmen |
| `klimaat_kamer_warm` | 22 °C | boven deze kamertemperatuur is het "te warm" |
| `klimaat_spui_delta` | 1 °C | zoveel koeler moet het buiten zijn om te spuien |
| `klimaat_kier_positie` | 15 % | wat een "kier" is |
| `klimaat_override_uren` | 4 u | hoe lang handbediening blijft gelden |
| `klimaat_zon_lux_drempel` | 20.000 lx | wanneer de zon "op de gevel staat" |
| `klimaat_zon_min_elevatie` | 8 ° | lager dan dit telt de zon niet mee |
| `klimaat_nachtspui` | uit | mag er 's nachts een kier open voor koelte |

Beide schakelaars (`klimaatregie_actief` en `klimaat_nachtspui`) staan na de
eerste start uit; die zet je zelf aan. De zeven
`input_boolean.zonwering_handmatig_<slug>` staan dan óók uit, en dat betekent
hier "doet mee" — bewust omgekeerd, want een verse helper staat altijd uit en
dat mag geen zone stilzwijgend blokkeren. De drempels hierboven worden bij de
eerste start ingevuld door `automation.klimaat_standaardwaarden` en daarna
nooit meer aangeraakt, dus jouw aanpassingen overleven een herstart.

## De beslistabel wijzigen

`custom_templates/klimaat.jinja` aanpassen en Home Assistant herstarten
(templates herladen is niet genoeg).

Er is een offline test die de tabel doorrekent zonder herstart:

```bash
python3 -m venv .venv && .venv/bin/pip install jinja2
.venv/bin/python tests/test_klimaat.py
```

Die dekt 25 situaties: hete dag met zon voor, preventief dimmen, niemand thuis,
winterzon, nachtspui, stille uren, storm op de screens, airco aan, geblokkeerde
zones en een kapotte temperatuursensor. Bouw je een regel om, voeg dan een
scenario toe — dat is sneller dan wachten op de volgende hittegolf.

## Wat dit bewust niet doet

- **Ramen en deuren openzetten** blijft een melding, geen actie. Daar zit een
  mens tussen.
- **Het achtertuin-zonnescherm** blijft bij zijn eigen bevestigingsvraag.
- **De keuken-rolgordijnen** (binnen) blijven bij inkijk en het raamcontact.
- **Bewegingen begrenzen per uur** doen we niet met een teller, maar met
  hysterese en `delay_off` op de zonsensoren. Blijkt een cover in de praktijk
  toch te vaak te lopen, dan is de lux-hysterese de plek om aan te draaien.
