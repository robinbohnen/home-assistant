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

## De vijf lagen

| Laag | Wat | Waar |
|---|---|---|
| 1. Regime | Wat voor dag wordt het? | `packages/9 - Other/Klimaat Regime.yaml` |
| 2. Gevelzon | Waar staat de zon nu? | idem |
| 3. Advies | Wat wil elke zone? | `packages/9 - Other/Klimaat Zonwering.yaml` |
| 4. Uitvoeren | Doen, tenzij… | idem |
| 5. Airco's | Actief koelen en bijverwarmen | `packages/9 - Other/Klimaat Airco.yaml` |
| Beslistabel | De regels zelf | `custom_templates/klimaat.jinja` |

Laag 1 tot en met 4 verplaatsen warmte die er al is: zon buiten houden, koelte
binnenlaten. Laag 5 maakt koelte (en warmte). Die twee delen bewust dezelfde
drempels en dezelfde beslistabel — twee bronnen voor "het is te warm" is precies
hoe ze uit elkaar gaan lopen.

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

Het huis heeft drie gevels met ramen. Kroon 18 staat aan de westkant van de
straat, dus:

| Gevel | Kijkt op | Krijgt zon | Lichtsensor |
|---|---|---|---|
| Voorgevel | oost (80°) | ochtend | `sensor.voortuin_zon_luminance` |
| Zijgevel | zuid (170°) | midden op de dag | geen eigen sensor |
| Achtergevel | west (260°) | middag en avond | `sensor.achtertuin_zon_luminance` |

Per gevel twee sensoren:

- `binary_sensor.zon_richting_<gevel>` — de zon staat geometrisch aan die kant:
  hoog genoeg, en minder dan `klimaat_gevel_breedte` (85°) van recht-voor-de-
  gevel af. Loopt vóór op het licht, dus bruikbaar om preventief te sluiten.
- `binary_sensor.zon_op_<gevel>` — hij schijnt er nu echt op: richting **en**
  genoeg licht.

Je stelt maar twee richtingen in, `klimaat_voorgevel_richting` en
`klimaat_zijgevel_richting`; de achtergevel wordt afgeleid (voorgevel + 180°).
De zijgevel heeft geen eigen lichtsensor, daar geldt de hoogste van de twee
tuinsensoren als maat voor "het is echt zonnig" — de richting doet daar het
onderscheid.

De lux-drempel heeft hysterese (aan bij 20.000, uit pas onder 14.000) plus
`delay_on` van 2 en `delay_off` van 10 minuten. Anders staat de zonwering te
klepperen bij overdrijvende wolken.

### Laag 3 — Advies per zone

Tien zones, elk met een sensor `sensor.zonwering_advies_<zone>`:

| Zone (slug) | Cover | Gevels | Bijzonder |
|---|---|---|---|
| `keuken_screens` | `cover.covers_kitchen_screens` | voor | screen: geen kier, in bij storm |
| `keuken_rolgordijn_groot` | `cover.rollerblind_0001` | voor | binnenzonwering; alleen als het screen er niet staat; stil vanaf de kinderbedtijd |
| `keuken_rolgordijn_klein` | `cover.rollerblind_0002` | voor | idem, eigen raamcontact |
| `kantoor_links` | `cover.kantoor_links_low_speed` | voor + zij | |
| `kantoor_rechts` | `cover.kantoor_rechts_low_speed` | voor + zij | |
| `badkamer` | `cover.badkamer_rolluik_low_speed` | achter | stille uren |
| `slaapkamer` | `cover.slaapkamer_rolluik_low_speed` | achter | stille uren |
| `slaapkamer_logan` | `cover.covers_bedroom_maxi` | voor | slaapvenster vanaf 19:00 |
| `slaapkamer_emma` | `cover.slaapkamer_mini` | zij + achter | slaapvenster vanaf 19:00 |
| `zonnescherm` | `cover.achtertuin_zonnescherm` | achter | screen; **omgekeerd bedraad**; **vraagt eerst** |

> **Het zonnescherm is andersom bedraad.** Voor die cover betekent de HA-stand
> `open` *uitgeschoven* (zon tegenhouden) en `closed` *ingetrokken*. De hele
> beslistabel blijft in gewone zonweringstermen denken — `dicht` is en blijft
> "zon buiten houden". De vertaling gebeurt op precies één plek: onderaan
> `klimaat.jinja`, waar `positie` voor een zone met `'omgekeerd': true` wordt
> gespiegeld. De uitvoerder en de handbediening-herkenning weten daar niets
> van en vergelijken gewoon `positie` met `current_position`.
>
> Reken bij twijfel de veilige kant na: bij storm zet de veiligheidsregel het
> advies op `open` (zon mag erdoor), dat wordt positie 100, en na spiegeling 0
> — waarop de uitvoerder `close_cover` stuurt en het scherm dus intrekt. Er
> staan zes scenario's in `tests/test_klimaat.py` die dit hard narekenen.

Hoekkamers staan op twee gevels: de zon telt zodra hij op één ervan staat.
Van de twee kantoorrolluiken is niet bekend welke op de voorgevel zit en welke
op de zijgevel, dus reageren ze allebei op beide. Weet je het wel, zet dan bij
dat rolluik in `klimaat.jinja` `'gevels': ['voor']` of `['zij']`; dan blijft
het andere raam langer licht.

> **Een gevel er "voor de zekerheid" bij zetten kost je een halve dag licht.**
> De keukenscreens stonden op voor + zij en bleven daardoor tot een uur of zes
> omlaag, terwijl de zon voor de keuken (oost) al rond het middaguur weg is.
> Dat komt van twee kanten: `zon_richting_zijgevel` telt met een gevelbreedte
> van 85° door tot een azimut van 255° — bijna west — en `zon_op_zijgevel`
> heeft geen eigen lichtsensor en pakt dan de meting uit de áchtertuin. De
> zijgevel stond dus nog "aan" op de avondzon van de andere kant van het huis.
> Ze staan nu op alleen `['voor']`, net zoals de oude `covers_sun_protection`
> puur naar `sensor.voortuin_zon_luminance` keek.

De slug bepaalt de naam van de bijbehorende helpers:
`sensor.zonwering_advies_<slug>`, `timer.override_<slug>` en
`input_boolean.zonwering_handmatig_<slug>`. Voeg je een zone toe, geef hem dan
een slug die gelijk is aan het entity_id dat Home Assistant van de sensornaam
maakt — anders vindt de uitvoerder de zone niet.

De staat van zo'n sensor is `open`, `kier`, `dicht` of `rust` (= niet bewegen).
Attributen: `positie` (0–100 of −1), `uitvoeren`, `vraagt`, `reden` en
`blokkade`.
`reden` is bewust in gewone taal geschreven, dat is wat je op het dashboard
leest als je je afvraagt waarom een rolluik doet wat het doet.

De beslistabel, van hoog naar laag:

1. **Stille uren** (22:00–07:00, voor slaapkamers en badkamer): niet bewegen.
   Enige uitzondering is openen naar een kier om te spuien als het binnen echt
   te warm is.
   Dat venster loopt door tot het huis **wakker** is. 07:00 is een klok en zegt
   niets over of er iemand op is; in de zomer stond de zon dan allang op en
   gingen de slaapkamerrolluiken omhoog terwijl er nog geslapen werd. De eerste
   druk op de slaapkamerknop zet `input_boolean.klimaat_wakker` aan
   (`automation.klimaat_wakker_bijhouden`). Dezelfde knop start 's avonds de
   naar-bed-routine, dus het tijdstip bepaalt de betekenis: een druk tussen
   **06:00 en 17:00** meldt wakker, daarbuiten zet hij de vlag juist uit.
   Datzelfde venster staat op de kaart "Slaapkamer knop" in
   `dashboards/home/overzicht.yaml`; die twee horen gelijk te blijven. Om 22:00
   valt de vlag sowieso terug, zodat een vergeten avonddruk de rolluiken de
   volgende ochtend niet alsnog opent. Drukt niemand, dan zet de automatisering
   de vlag om 10:00 zelf aan (`WAKKER_UITERLIJK` in `klimaat.jinja` en de
   trigger van 10:00 horen gelijk te blijven). Ventileren
   blijft ondertussen gewoon toegestaan: de spui-kier valt niet onder deze
   rem, alleen omhóóg gaan. Behalve in een kinderkamer: die blijft tijdens het
   slaapvenster helemaal omlaag, zie punt 2.
2. **Slaapvenster kinderkamer** (vanaf 19:00): helemaal dicht, zonder
   uitzonderingen. Er stond hier een kier op hittedagen, maar in juni is het om
   19:00 nog volop licht en daar blijven ze wakker van; donker weegt hier
   zwaarder dan die paar graden. Dat geldt ook 's nachts: de spui-kier van punt
   1 slaat een kinderkamer over. Koelen gebeurt in deze kamers dus overdag
   (vóór bedtijd) en met de airco.
   Het venster stopt niet om 07:00 maar loopt door zolang het huis niet wakker
   is gemeld (dus uiterlijk tot 10:00). Anders viel de spui-uitzondering van
   punt 1 daar 's ochtends weer aan en gingen de kinderrolluiken op een warme
   ochtend alsnog een stukje open. Zolang niemand wakker is, verandert er in een
   kinderkamer dus níéts: dicht blijft dicht, een kier blijft een kier.
3. **Nacht**: dicht, of een kier bij nachtspui in het koelregime.
4. **Overdag per regime**:
   - *Koelen*: zon op de gevel → dicht. Niemand thuis op een warme dag → dicht.
     Hittedag met de zon in aantocht → kier. Kamer boven de comfortgrens →
     kier. Anders open.
   - *Verwarmen*: zon → open (gratis warmte), tenzij de kamer al te warm is.
     Anders open voor het daglicht.
   - *Neutraal*: open, tenzij zon én een warme kamer.
5. **Airco koelt** in die zone → geen open rolluik; anders koel je de straat.
   Wel pas als hij het vijf minuten volhoudt (`AIRCO_KIER_NA` in
   `klimaat.jinja`). Op 19 augustus 2026 viel de zolderairco steeds na een
   kwartier uit op zijn eigen beveiliging, en omdat alle zes zones boven aan
   `climate.airco_zolder` hangen trok elke koelpoging de hele verdieping naar
   een kier en daarna weer omhoog. Een airco die net is aangeslagen zegt nog
   niets; een kier wint in die paar minuten toch niets, want het rolluik doet
   er veertig seconden over en de rustpauze van de uitvoerder houdt hem daarna
   een kwartier vast. Direct na een herstart van Home Assistant telt de
   huidige stand wél meteen — dan is `last_changed` van álles vers en zou een
   airco die al uren draait onterecht als "net aan" gelden.
6. **Screens** (de keukenscreens en het zonnescherm) beslissen opnieuw en
   overschrijven stap 4 en 5. Een screen houdt namelijk *straling* tegen en
   geen warmte die er al is, dus hij heeft alleen zin zolang de zon echt op de
   gevel staat: omlaag bij zon op de gevel, of preventief op een hittedag als
   de zon die kant op draait — en verder omhoog. In het verwarmregime blijft
   hij altijd omhoog, want dan is de zon juist welkom.
   Voorheen erfde een screen de uitkomst van stap 4, en die laat een rolluik
   ook zakken bij een warme kamer, een leeg huis of een koelende airco. Voor
   een rolluik klopt dat (dat dempt ook licht), voor een screen niet: hij bleef
   daardoor de hele warme avond omlaag terwijl de zon allang weg was.
   Screens kennen geen kier en gaan 's nachts omhoog. Ze gaan in bij harde
   wind, verwachte regen of vorst (< 4 °C); die veiligheidsregel staat als
   laatste en overschrijft al het bovenstaande — ook de vraag uit stap 8, want
   binnenhalen doe je niet in overleg.

> **Wanneer moet een screen in?** Bij wind en regen, niet bij hitte. Voor wind
> twee bronnen: `wind_speed` uit `weather.knmi_thuis` (boven
> `klimaat_screen_max_wind`, standaard 45 km/u) en de KNMI-waarschuwing. Die
> laatste is dubbel onbetrouwbaar: hij staat ook op `on` ("Onveilig") als er
> niets aan de hand is, én hij gaat net zo goed af voor een hitteplan of
> gladheid. Daarom telt hij alleen mee als de tekst in het
> `description`-attribuut over wind, storm, onweer of hagel gaat. Zou je op de
> staat afgaan, dan gaan de keukenscreens nooit meer omlaag — precies op de
> dagen dat je ze nodig hebt.
>
> Voor regen telt `sensor.neerslag_komende_30_minuten` (echte millimeters)
> boven `klimaat_screen_max_regen`, standaard 0,1 mm. Een onbereikbare sensor
> telt als droog: niets doen is dan beter dan de hele dag alles binnenhalen.
> Hiervóór liep binnenhalen bij regen alleen via een pushmelding uit de oude
> zonnescherm-automatisering, die een tik op je telefoon nodig had; die
> automatisering is inmiddels verwijderd.

7. **Binnenzonwering** (de twee keukenrolgordijnen) beslist net als een screen
   opnieuw en overschrijft stap 4 en 5. Een rolgordijn hangt aan de warme kant
   van het glas: de zon is er dan al doorheen en de warmte al in huis. Het doek
   warmt op en geeft die warmte gewoon weer aan de keuken af, dus hij haalt
   grofweg een derde van wat het screen ervóór doet — en kost wél het uitzicht
   en het daglicht. Meelopen met de screens levert dus vooral een donkere keuken
   op. Hij gaat daarom alleen omlaag als:
   - de zon op de gevel staat terwijl het screen ervoor **niet** omlaag staat.
     Dat is de situatie na stap 6: wind, regen of vorst hebben de screens
     ingetrokken (en het geldt net zo goed bij handbediening of een storing).
     Dan is het rolgordijn de enige zonwering die er nog is;
   - het een hittedag is of de kamer te warm terwijl er niemand thuis is —
     donker kost dan niets.

   Staat het screen wél omlaag, dan blijft het rolgordijn omhoog: achter een
   screen blijft het glas koel en levert een tweede laag vrijwel niets meer op.
   Dat geldt ook met de airco aan; een dicht rolgordijn helpt daar een beetje,
   maar niet genoeg om de keuken de hele ochtend donker voor te maken.

   Buiten het dagvenster adviseert deze zone `rust`. Dat venster begint bij het
   wakker-signaal en eindigt bij de vroegste van deze twee:

   - **het begin van de naar-bed-routine van de kinderen.** Een rolgordijn is
     door het hele huis te horen en de kinderkamers liggen erboven. In juni
     staat de zon om 20:00 nog ruim boven `AVOND_ELEVATIE` en de stille uren
     beginnen pas om 22:00, dus lag daar een gat van een paar uur waarin de
     klimaatregie ze op een warme avond alsnog omhoog stuurde — precies tijdens
     het in slaap vallen. De tijd komt uit
     `input_datetime.bedtime_maxi_1h_off` en `…_mini_1h_off` (`BEDTIJDEN`),
     dezelfde helpers als de rest van het huis gebruikt; de vroegste van de twee
     telt en de rust schuift dus mee met een latere weekendbedtijd. Geeft geen
     van beide een bruikbare avondtijd, dan geldt `BEDTIJD_TERUGVAL` (18:00, een
     uur voor `slaap_van` in de kinderkamers). Een tijd vóór `BEDTIJD_VROEGST`
     (17:00) wordt genegeerd — anders zou een verkeerd gezette helper de zone de
     hele dag platleggen;
   - **een half uur voor zonsondergang** (`AVOND_ELEVATIE`, 5°).

   Vanaf dat moment zijn de rolgordijnen van `kitchen_covers_close` en
   `covers_lock_alarm_events`: die gaan over inkijk en niet over warmte. Zou de
   klimaatregie daar doorheen blijven adviseren, dan trok de uitvoerder ze een
   kwartier later weer omhoog. In de zomer komt de bedtijd ruim eerst, in de
   winter de zonsondergang — en `kitchen_covers_close` gebruikt precies
   diezelfde twee momenten, zodat er geen gat tussen kan vallen. Er is een
   consistentiecheck in `tests/test_klimaat.py` die dat bewaakt.

   Aan de ochtendkant is er niets bijzonders nodig: dat venster loopt al tot het
   huis wakker is gemeld (`nog_slapen`, uiterlijk `WAKKER_UITERLIJK`).

   Om dezelfde reden gaat er **niets omhoog als het alarm scherp staat
   (`armed_*`) of er niemand thuis is**: dan heeft de inkijk-routine ze net
   dichtgetrokken. Omláág mag in die situatie wél gewoon — dat is dezelfde
   richting. Zonder die rem haalde de uitvoerder ze op een milde dag binnen een
   kwartier weer omhoog, en zette hij er daarna ook nog vier uur handbediening
   op omdat hij zijn eigen tegenwerking als handbediening herkent.

   Tot slot het **raamcontact**: staat het raam open, dan wordt `dicht`
   alsnog `rust`. Je rolt geen gordijn tegen een openstaand raam aan. Een
   contact op `unknown` of `unavailable` telt daarbij als open. Dat contact
   hoort bij één raam, en daarom staan de twee rolgordijnen als aparte zones in
   de tabel en niet als groep — anders houdt een openstaand klein raam ook het
   grote rolgordijn tegen.

### Laag 4 — Uitvoeren

`automation.klimaat_zonwering_uitvoeren` loopt de tien zones langs en beweegt
alleen als het advies mag worden uitgevoerd én de huidige stand meer dan 5%
afwijkt. Er is dus geen beweging als er niets te winnen valt. Zones die eerst
toestemming vragen slaat hij over zolang het advies "naar buiten" is (zie
hieronder).

`automation.klimaat_handbediening_herkennen` is de tegenhanger: elke beweging
die 90 seconden stil ligt op een *andere* stand dan het advies telt als
handbediening — via de app, een knop, een wandschakelaar of een van de oude
automatiseringen. Die zone wordt dan 4 uur met rust gelaten
(`timer.override_<zone>`). Zet je hem terug op de geadviseerde stand, dan
vervalt de uitzondering meteen weer.

Onze eigen bewegingen eindigen per definitie op het advies en worden daarom
nooit als handbediening gezien. Dat is de hele truc: geen contextgegoochel,
gewoon kijken waar de cover uiteindelijk blijft staan.

#### Het zonnescherm vraagt eerst

Het zonnescherm gaat **niet uit zichzelf naar buiten**. Het is het enige stuk
zonwering waar je in de tuin tegenaan loopt en het enige dat kapot waait als je
het vergeet, dus daar hoort een mens aan te pas te komen.
`automation.klimaat_zonnescherm_vragen` stuurt in plaats van een beweging een
melding naar de telefoons van de volwassenen — met de reden erbij, dus je weet
waarom hij het vraagt. Is er iemand thuis, dan stelt de spraaksatelliet in de
keuken dezelfde vraag hardop (`script.spraak_vraag_stellen`); "ja" en "nee"
komen binnen als het event `spraak_antwoord` en doen precies hetzelfde als de
knoppen op de telefoon. Zie [spraak.md](spraak.md).

- **Ja** → het scherm rolt uit.
- **Nee** → `timer.override_zonnescherm` gaat lopen en de klimaatregie laat het
  scherm de hele overridetijd (standaard 4 uur) met rust, precies zoals bij
  handbediening.
- **Geen antwoord** → er gebeurt niets. Na twee uur
  (`timer.zonnescherm_vraag`) mag hij het opnieuw vragen.

**Binnenhalen blijft wél automatisch.** Op het intrekken bij wind, vorst, regen
of een weggedraaide zon moet niemand hoeven wachten; dat doet de gewone
uitvoerder. In de beslistabel is dat het attribuut `vraagt`: dat staat alleen
op `true` als het advies `dicht` of `kier` is voor een zone met
`'vraagt': true`. Zowel de uitvoerder als de handbediening-herkenning slaat de
zone dan over — die laatste omdat een scherm dat nog binnen staat terwijl het
advies "uit" is geen handbediening is maar een openstaande vraag. Op het
dashboard zie je dat terug als blokkade *"wacht op je akkoord"*.

> Met de klimaatregie **uit** beweegt het zonnescherm helemaal niet meer uit
> zichzelf: de oude lux-automatisering (`backyard_sunscreen`) is verwijderd.
> Bediening gaat dan via de overkappingsknop, het dashboard of de spraakassistent.

> **Let op de ochtendknop.** Druk je 's ochtends op de slaapkamerknop, dan
> gaan de rolluiken open en telt dat als handbediening: die zones liggen dan
> vier uur stil. Op een hete ochtend blijft de zonwering daardoor open terwijl
> de zon al op de gevel staat. Merk je dat, zet `klimaat_override_uren` dan
> lager (2 uur is een prima waarde). De knop-automatisering kijkt zelf al naar
> de lichtsterkte en laat de zonzijde met rust als het al fel is.

### Laag 5 — De airco's

De vier lagen hierboven schuiven warmte rond. Deze laag maakt koelte: staat het
huis vol en is het te warm, dan mag de airco aan — en hij mag alvast beginnen
als er iemand bijna thuis is. In de winter werkt hij dezelfde kant op als
bijverwarming.

Twee units, elk met een eigen adviessensor:

| Unit (slug) | Entiteit | Regelt op | Bijzonder |
|---|---|---|---|
| `woonkamer` | `climate.airco_woonkamer` | `sensor.woonkamer_woonkamer_multisensor_temperatuur` | halve graden, ventilator op stand 2 |
| `zolder` | `climate.airco_zolder` | `sensor.temperatuur_boven_gemiddeld` | hele graden, minimaal 18°, uitzetten via `script.script_attic_ac_off` |

De zolderunit blaast op de overloop en bedient de hele bovenverdieping, dus die
regelt op het gemiddelde van de vijf kamersensoren en niet op één kamer.

De slug bepaalt weer de namen van de helpers: `sensor.airco_advies_<unit>`,
`timer.airco_override_<unit>`, `timer.airco_minimaal_aan_<unit>`,
`timer.airco_rust_<unit>`, `timer.airco_gestart_<unit>`,
`input_boolean.airco_handmatig_<unit>`, `input_boolean.airco_storing_<unit>` en
`counter.airco_storingen_<unit>`.

De staat van zo'n sensor is `cool`, `heat`, `off` of `rust` (= niets sturen).
Attributen: `doel`, `fan`, `uitvoeren`, `spoed`, `reden` en `blokkade`.

#### Niet pendelen is de hele opgave

Een airco die om de vijf minuten aan- en uitgaat koelt niets, kost stroom en
sloopt zijn compressor. Vijf remmen over elkaar, elk tegen een andere manier
van stuiteren:

1. **Dode zone.** Aan bij `kamer_warm + aan_delta` (23,5°), uit pas bij
   `kamer_warm - uit_delta` (21,5°). Twee graden ertussen. Eén drempel met een
   beetje hysterese is niet genoeg: een kamertemperatuur schommelt een halve
   graad op een zonnestraal. Bij 23,4° zegt de tabel daarom niet "uit" maar
   "doorkoelen tot het doel".
2. **Minimale looptijd** (`timer.airco_minimaal_aan_<unit>`, 30 min). De eerste
   minuten koelt een airco vooral de thermometer: de koude luchtstroom komt
   langs de sensor voordat hij de muren heeft gehad. Zet je dan uit, dan kruipt
   de meting binnen tien minuten terug omhoog.
3. **Minimale rust** (`timer.airco_rust_<unit>`, 20 min). Andersom hetzelfde:
   vlak na het uitschakelen loopt de meting juist op omdat de kamer zich
   herverdeelt.
4. **Rustpauze van de uitvoerder** (10 min na de laatste standswijziging),
   precies zoals bij de covers.
5. **Het setpoint gaat één keer mee** bij het aanzetten en wordt daarna niet
   meer bijgesteld. De inverter moduleert zelf; hem elke ronde een nieuw
   streefgetal geven is dé manier om een warmtepomp aan het stuiteren te
   krijgen.

Rem 4 doet nog iets tweeds, en dat is de reden dat hij op tien minuten staat en
de handbediening-herkenning op vijf: zet iemand de airco met de hand aan terwijl
het advies `off` is, dan staat er een override op vóórdat de uitvoerder hem kan
terugzetten. Zonder die volgorde zou de knop "niets doen": de uitvoerder
zet hem binnen vijf minuten weer uit en niemand begrijpt waarom.

#### Thuis, en bijna thuis

`thuis` is `group.all_adults` op `home`, dezelfde definitie die de zonwering
gebruikt (dus: mínstens één volwassene thuis, niet iedereen).

`bijna thuis` is de kleinste reistijd van de volwassenen onder
`klimaat_airco_voorkoelen_min` (20 minuten). Bewust niet
`binary_sensor.iemand_onderweg_naar_huis`: die staat al aan zodra iemand het
huis uit is, en dan koel je een uur voor niets. Twee guards:

- de persoon moet aantoonbaar niet thuis zijn;
- de reistijdsensor moet nog ververst hebben (30 minuten). Blijft de telefoon
  van iemand in het buitenland op "twintig minuten" staan, dan zou het huis
  eindeloos voorkoelen voor iemand die niet komt.

Loopt de reistijd door de file weer op boven de 20 minuten, dan vervalt het
voorkoelen vanzelf — de reistijdsensor ís de begrenzing, daar is geen aparte
timer voor nodig.

#### De beslistabel, van hoog naar laag

1. **Raam open** in het gebied van die unit → uit. Alleen een *aantoonbaar*
   open contact telt.

   > **Dit is bewust andersom dan bij de rolgordijnen.** Daar telt een contact
   > op `unavailable` als open, want een gordijn tegen een openstaand raam is
   > duur. Hier zou diezelfde keuze betekenen dat één lege batterij de airco de
   > hele zomer blokkeert — precies wat er een keer twee weken lang met het
   > keukenrolgordijn gebeurde zonder dat iemand zag waarom. Een onbereikbaar
   > contact blokkeert hier dus niet, maar wordt wél in de `reden` genoemd.

2. **Storing gemeld** → niet automatisch starten. Zie hieronder.
3. **Kwam niet vooruit** → twee uur uit. Zie hieronder.
4. **Niemand thuis en niemand vlakbij** → uit.
5. **Stille uren** (22:00–07:00) → niet uit zichzelf aanslaan. Uitgaan mag wel.
   De zolderunit hangt op de overloop naast de slaapkamers; de woonkamerunit
   zou 's nachts een lege kamer koelen.
6. **Kamertemperatuur onbekend** → `rust`. Niet uitzetten: dat zou een
   draaiende airco stilleggen op een lege batterij.
7. **Koelen** bij `kamer_warm + aan_delta`, behalve in het verwarmregime. Ook
   op een neutrale dag: het regime komt uit de verwachting van vanochtend, en
   een kamer van 23,5° is warm ongeacht wat het KNMI dacht.
8. **Bijverwarmen** bij `kamer_koud - aan_delta` (17,5°), behalve in het
   koelregime. De cv doet het gewone werk; de airco springt pas bij als een
   ruimte er echt onder zakt.
9. **Draait al en het doel is nog niet gehaald** → doorgaan. Dit is de tak die
   de dode zone maakt.
10. Daarna de twee timers uit rem 2 en 3.

De eerste vier redenen staan op `spoed`: die breken de minimale looptijd af en
slaan de rustpauze van de uitvoerder over. Doorkoelen met een openstaand raam of
in een leeg huis is geen comfort maar een rekening.

#### Handbediening

Net als bij de covers: onze eigen commando's eindigen per definitie op het
advies, dus alles wat vijf minuten lang op iets ánders staat is een mens (of de
afstandsbediening, of de Intesis-app). Die unit wordt dan `klimaat_override_uren`
met rust gelaten.

Vijf minuten en niet anderhalve, want een climate-entiteit doet er via de cloud
soms een minuut over voordat hij de nieuwe stand terugmeldt. En een advies van
`rust` telt hier niet mee: zodra wij een unit aanzetten slaat het advies binnen
een paar minuten om naar `rust` (minimale looptijd, of "koelt door"), en dan zou
een draaiende airco zijn eigen start als handbediening zien.

#### Als het doel niet gehaald wordt

Dit is geen randgeval maar het normale geval op een hete dag, en het heeft twee
heel verschillende oorzaken die van buiten identiek lijken.

**De unit doet zijn werk maar wint het niet.** Dan is doordraaien het juiste
antwoord: zonder hem zou het warmer zijn. De regeling laat hem dus lopen — het
advies blijft `rust` ("koelt door") tot de stille uren, tot iedereen weg is of
tot er een raam opengaat. Er is bewust geen maximale looptijd.

**De unit draait ergens tegenop.** Een deur die openstaat naar een ruimte zonder
raamcontact, een unit die het niet meer doet, of een doel dat op deze sensor
simpelweg niet te halen is. Dan kost het 550 W voor niets.

Het verschil is meetbaar, dus wordt het gemeten in plaats van aangenomen.
`timer.airco_voortgang_<unit>` loopt vanaf het aanzetten; de temperatuur van dat
moment staat in `input_number.airco_start_temp_<unit>`. Elke 45 minuten:

- **minstens `AIRCO_VOORTGANG_MIN` (0,3 °C) opgeschoven** → hij wint. Het venster
  begint opnieuw vanaf de huidige stand, zodat de volgende controle over de
  vólgende drie kwartier gaat. Anders zou een unit die alleen in het eerste half
  uur iets deed de rest van de dag als "in orde" blijven gelden.
- **minder dan dat** → `timer.airco_kansloos_<unit>` gaat twee uur lopen, de unit
  gaat uit, en je krijgt een melding met de gemeten cijfers. Na die twee uur
  probeert hij het gewoon opnieuw; tegen die tijd staat de zon ergens anders of
  is dat raam dicht.

0,3 °C op drie kwartier is bewust laag. Een airco die het echt wint doet in die
tijd een halve tot anderhalve graad; alles daaronder is ruis op een sensor die op
een tiende meet.

Dit is nadrukkelijk **geen storingsvlag**. De unit is waarschijnlijk in orde en
vecht tegen iets anders; daarom blokkeert het ook niet tot de volgende ochtend
maar twee uur, en daarom staat het los van `airco_storing_<unit>`.

> **Waarom de unit boven een eigen band heeft.** Op 20 augustus 2026 stond de
> zolderairco vier uur op 18°/high. Het gemiddelde boven ging van 22,4 naar 22,2
> — en twee van de vijf kamers werden in die tijd wármer:
>
> | Kamer | Start | Na 4 uur | Δ |
> |---|---|---|---|
> | Emma (deur open) | 22,47 | 21,69 | −0,78 |
> | Kantoor | 23,07 | 22,86 | −0,21 |
> | Badkamer | 22,93 | 22,90 | −0,03 |
> | Logan | 22,26 | 22,46 | +0,20 |
> | Slaapkamer | 20,93 | 21,17 | +0,24 |
>
> Acht van de negen ramen boven stonden open — daar zou de regie hem dus
> überhaupt niet hebben aangezet. Maar het patroon eronder blijft staan ook met
> alles dicht: die unit hangt op de overloop en blaast niet door een dichte
> slaapkamerdeur, terwijl hij wél wordt afgerekend op het gemiddelde van vijf
> kamers. Een doel dat voor één kamer normaal is, is op dat gemiddelde
> onhaalbaar — en een onhaalbaar doel betekent een unit die nooit uit zichzelf
> stopt.
>
> Daarom heeft elke unit in `AIRCOS` een `band`: die schuift `kamer_warm` én
> `kamer_koud` voor die unit op. De zolder staat op `+1` (aan vanaf 24,5°, doel
> 23°), de woonkamer op `0`. Beide kanten schuiven mee, want zou alleen het doel
> opschuiven, dan komt de aanzetgrens er vlak boven te liggen en pendelt hij
> alsnog.
>
> Het koeldoel rondt af **naar boven** naar wat de unit kan (de zolderunit doet
> hele graden), het verwarmdoel naar beneden. Met gewoon afronden zou 22,5 daar
> 22 worden — een halve graad méér vragen van precies de unit die zijn doel toch
> al niet haalt.

#### Een unit die zichzelf uitschakelt

`automation.klimaat_airco_storing_herkennen` telt hoe vaak een unit binnen een
kwartier ná onze start weer uitvalt. Bij de tweede keer op een dag gaat
`input_boolean.airco_storing_<unit>` om, start de regie hem niet meer, en krijg
je een melding. Elke nacht om 04:00 gaan teller en vlag terug op nul, zodat één
hik niet permanent blokkeert en een echte storing zich de volgende dag opnieuw
meldt. Met de hand aanzetten kan altijd.

Dit bestaat vanwege 19 augustus 2026: de zolderairco viel toen tien tot
vijfentwintig minuten na elke start vanzelf uit op foutcode **E48** (de
buitenventilator draaide niet, dus de condensor kon zijn warmte niet kwijt).
Handmatig is dat vervelend, automatisch is het schadelijk — dan blijft het huis
het de hele dag opnieuw proberen terwijl de compressor telkens op zijn
beveiliging klapt.

> Wat deze detectie **niet** kan zien: een lege context in het logboek betekent
> "niet via Home Assistant", niet "het apparaat deed het zelf". De fabrikant-app,
> de afstandsbediening en een stroomonderbreking komen alle drie contextloos
> binnen. De melding vraagt daarom om te kijken en presenteert niets als bewezen.

#### Wat er met de rolluiken gebeurt

Blok 4b van de zonwering zet een zone op een kier zodra de airco in die zone
vijf minuten koelt (`AIRCO_KIER_NA`). Nu de airco vaker uit zichzelf aangaat,
gebeurt dat ook vaker — dat is de bedoeling, want koelen met de zon op het glas
is dweilen met de kraan open. De minimale looptijd van een half uur zorgt dat
het bij één beweging blijft; vóór die rem gingen er op één middag zes rolluiken
vier keer op en neer omdat de airco steeds uitviel.

De regie stuurt de covers **niet** zelf. Het `script_attic_ac` van de handmatige
"het is snikheet boven"-vraag doet dat wel (`cover.close_cover` op alle
rolluiken boven), en dat vecht met blok 4b: die adviseert 15% en een volledig
gesloten rolluik telt anderhalve minuut later als handbediening. Dat script is
hier bewust ongemoeid gelaten — het is een gebruikersactie met een mens erbij —
maar het is wel de plek om te kijken als er boven vier uur lang niets meer
beweegt na een handmatige airco-vraag.

## Aanzetten en terugdraaien

De zonwering hangt aan één schakelaar: **`input_boolean.klimaatregie_actief`**.
De airco's hangen aan een eigen schakelaar, **`input_boolean.aircoregie_actief`**,
zodat je ze los van elkaar kunt aanzetten en terugdraaien.

- **Uit**: hier beweegt niets, en de zonwering doet dan ook niets meer uit
  zichzelf. De oude automatiseringen die dat vroeger deden
  (`covers_sun_protection`, `covers_morning_routine`, `covers_bedtime`,
  `bedroom_maxi_covers`, `bedroom_mini_covers`, `backyard_sunscreen` en de
  cover-acties in Temperature Control) zijn verwijderd — er is geen
  terugvallaag meer, alleen handbediening. De ramen-adviezen
  (`packages/9 - Other/Temperature Control.yaml`) sturen alleen nog meldingen
  en staan los van deze schakelaar.
- **Aan**: de klimaatregie stuurt.

Ongemoeid gelaten, omdat het gebruikersacties zijn die de handbediening-laag
netjes afvangt: de knop-automatiseringen (slaapkamer, kantoor, badkamer) en het
sluiten van de rolluiken door `script_attic_ac` voordat de airco aangaat.

Ook ongemoeid, maar om een andere reden: `kitchen_covers_close` (rolgordijnen
dicht voor de avond) en `covers_lock_alarm_events` (open bij ontgrendelen, dicht
bij inschakelen van het alarm). Die gaan over inkijk en niet over warmte, en de
klimaatregie houdt zich daar bewust buiten: buiten het dagvenster adviseert ze
`rust` voor de rolgordijnen. Zie stap 7 hierboven.

`kitchen_covers_close` is wel op twee punten aangepast, allebei omdat hij het
enige was dat zich er niet aan hield:

- hij liep op zonsondergang −30 min, in juni dus 21:35 — twee uur nadat de
  kinderen naar bed waren. Hij sluit nu op wat het eerst komt: die zonsondergang
  of het begin van de naar-bed-routine, precies de twee momenten waarop de
  klimaatregie deze zone loslaat;
- hij sloot de rolgordijnengroep zonder naar de raamcontacten te kijken en rolde
  dus tegen een openstaand keukenraam aan. Hij gaat nu per rolgordijn en slaat er
  een over waarvan het contact niet aantoonbaar dicht is — dezelfde regel als in
  `covers_lock_alarm_events` en in de klimaatregie zelf.

## Uitrollen

1. **Herstart Home Assistant.** Nieuwe packages én `custom_templates/` worden
   alleen bij het opstarten ingelezen.
2. **Meekijken met de hoofdschakelaar uit.** Ga naar de weergave *Klimaat*
   (`/lovelace/klimaat`) en vergelijk een week lang de kolommen "Advies" en
   "Werkelijke stand". Er beweegt nog niets. Klopt een advies niet, dan pas je
   `klimaat.jinja` of de drempels aan.
3. **Gevelrichtingen controleren.** Ze staan al ingevuld op oost (80°) voor de
   voorgevel en zuid (170°) voor de zijgevel, afgeleid uit de ligging aan de
   Kroon. Kijk op een zonnige dag of `Zon op voorgevel` 's ochtends aan gaat,
   `Zon op zijgevel` rond het middaguur en `Zon op achtergevel` in de middag.
   Loopt het een uur voor of achter, dan draai je de richting een graad of
   tien bij; klopt de volgorde niet, dan staan voor- en zijgevel verwisseld.
4. **Aanzetten.** `input_boolean.klimaatregie_actief` aan. Wil je voorzichtig
   beginnen, zet dan eerst `zonwering_handmatig_*` aan voor de slaapkamers, zodat
   alleen kantoor, badkamer en de keukenscreens meedoen.

Terugdraaien is altijd één schakelaar, op elk moment.

### De airco's erbij (laag 5)

Aparte schakelaar, dus een aparte ronde:

1. **Meekijken met `aircoregie_actief` uit.** De adviessensoren rekenen gewoon
   door. Op de Klimaat-weergave staat onder *Airco's* wat elke unit zou doen en
   waarom. Let vooral op hoe vaak het advies wisselt: blijft `Wat wil elke unit`
   op één warme middag heen en weer springen tussen `cool` en `off`, dan staat
   de dode zone te krap en gaat `klimaat_airco_aan_delta` omhoog.
2. **Eén unit tegelijk.** Zet `airco_handmatig_zolder` aan en begin met de
   woonkamer. Die unit is niet stuk en je hoort hem in dezelfde ruimte waar je
   zit, dus je merkt meteen of het gedrag klopt.
3. **De zolderunit pas als E48 weg is.** Zolang die foutcode er staat, is
   automatisch starten schadelijk. De storingsdetectie vangt het op — twee
   afgebroken starts en hij blokkeert zichzelf — maar dat is een vangnet en geen
   toestemming.
4. **Kijk na een week naar de looptijden.** In de recorder-geschiedenis van
   `climate.airco_woonkamer` horen blokken van een half uur of langer te staan.
   Zie je reeksen van precies dertig minuten, dan is de minimale looptijd de
   enige reden dat hij nog draait en mag `klimaat_airco_uit_delta` omhoog.
5. **Let op de meldingen "komt niet vooruit".** Eén op een tropische dag is
   informatie. Elke dag dezelfde unit betekent dat zijn doel niet te halen is;
   dan gaat de `band` van die unit in `klimaat.jinja` omhoog, niet de drempel
   omlaag.

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
| `klimaat_voorgevel_richting` | 80 ° | kompasrichting van de voorgevel (oost) |
| `klimaat_zijgevel_richting` | 170 ° | kompasrichting van de zijgevel (zuid) |
| `klimaat_gevel_breedte` | 85 ° | hoe schuin de zon nog op een gevel telt |
| `klimaat_screen_max_wind` | 45 km/u | hierboven gaan de screens in |
| `klimaat_screen_max_regen` | 0,1 mm | zoveel verwachte neerslag haalt de screens in |
| `klimaat_zon_lux_drempel` | 20.000 lx | wanneer de zon "op de gevel staat" |
| `klimaat_zon_min_elevatie` | 8 ° | lager dan dit telt de zon niet mee |
| `klimaat_nachtspui` | uit | mag er 's nachts een kier open voor koelte |
| `klimaat_wakker` | uit | staat aan zodra het huis wakker is; uit houdt de slaapzones dicht |
| `aircoregie_actief` | uit | mogen de airco's automatisch aan en uit (laag 5) |
| `klimaat_kamer_koud` | 19 °C | onderkant van de comfortband; daaronder mag de airco bijverwarmen |
| `klimaat_airco_aan_delta` | 1,5 °C | zoveel boven `kamer_warm` gaat hij aan (en zoveel onder `kamer_koud`) |
| `klimaat_airco_uit_delta` | 0,5 °C | zoveel onder `kamer_warm` is het doel bereikt |
| `klimaat_airco_voorkoelen_min` | 20 min | vanaf deze reistijd telt iemand als "bijna thuis" |
| `airco_handmatig_<unit>` | uit | uit = deze unit doet mee |
| `airco_storing_<unit>` | uit | aan = niet automatisch starten (gaat vanzelf om en om 04:00 weer uit) |

Twee getallen die niet als helper bestaan maar in `custom_templates/klimaat.jinja`:
`band` per unit (zolder +1, woonkamer 0) en `AIRCO_VOORTGANG_MIN` (0,3 °C). Die
horen bij het gedrag en niet bij de bediening, dus staan ze bij de rest van de
beslistabel.

Beide schakelaars (`klimaatregie_actief` en `klimaat_nachtspui`) staan na de
eerste start uit; die zet je zelf aan. De tien
`input_boolean.zonwering_handmatig_<slug>` staan dan óók uit, en dat betekent
hier "doet mee" — bewust omgekeerd, want een verse helper staat altijd uit en
dat mag geen zone stilzwijgend blokkeren. De drempels hierboven worden ingevuld door
`automation.klimaat_standaardwaarden`, maar alleen als ze nog exact op hun
minimum staan — dat is de waarde die Home Assistant zelf invult als er niets
is opgeslagen. Een `input_number` zonder opgeslagen waarde start namelijk
**niet** op `unknown` maar op zijn `min:`. Alles wat jij hebt bijgesteld blijft
dus staan, ook na een herstart.

Voeg je later een drempel toe, zet hem dan in de lijst in die automatisering
én verhoog `config_versie` daar met één. Zonder die verhoging draait de
automatisering niet meer en blijft de nieuwe drempel op zijn minimum hangen.
`input_number.klimaat_config_versie` op 0 zetten en herstarten geeft alle
onaangeraakte drempels hun standaardwaarde terug.

## De beslistabel wijzigen

`custom_templates/klimaat.jinja` aanpassen en Home Assistant herstarten
(templates herladen is niet genoeg).

Er is een offline test die de tabel doorrekent zonder herstart:

```bash
python3 -m venv .venv && .venv/bin/pip install jinja2
.venv/bin/python tests/test_klimaat.py
```

Die dekt inmiddels ruim vijftig situaties: hete dag met zon voor, preventief dimmen, niemand thuis,
winterzon, nachtspui, stille uren, storm op de screens, airco aan, geblokkeerde
zones, een kapotte temperatuursensor en de zon die over alle drie de gevels
draait. Hij controleert ook of elke zoneslug nog overeenkomt met het entity_id
dat Home Assistant van de sensornaam maakt. Bouw je een regel om, voeg dan een
scenario toe — dat is sneller dan wachten op de volgende hittegolf.

## Wat dit bewust niet doet

- **Ramen en deuren openzetten** blijft een melding, geen actie. Daar zit een
  mens tussen.
- **De keuken-rolgordijnen mee laten lopen met de screens.** Ze springen alleen
  bij als het screen er niet kan staan (stap 7). Achter een neergelaten screen
  levert een tweede laag vrijwel niets op, en het kost je wel het daglicht in de
  keuken. Avond en nacht blijven van de inkijk-routine.
- **Bewegingen begrenzen per uur** doen we niet met een teller, maar met
  hysterese en `delay_off` op de zonsensoren. Blijkt een cover in de praktijk
  toch te vaak te lopen, dan is de lux-hysterese de plek om aan te draaien.
- **De airco's op stroomprijs of zonoverschot laten draaien.** Kan later een
  extra laag worden ("mag alvast koelen als er overschot is"), maar niet in de
  eerste versie: dan zijn er twee redenen waarom hij aan staat en is er geen
  zinnig antwoord meer op de vraag waarom hij nú draait.
- **De rolluiken sluiten vóór de airco aangaat.** Dat doet blok 4b al, met een
  kier in plaats van helemaal dicht. Zelf `close_cover` sturen levert een
  gevecht met de handbediening-herkenning op — zie het slot van laag 5.
