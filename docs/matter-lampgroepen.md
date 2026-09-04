# Lampgroepen na de overstap naar Matter

De IKEA TRADFRI-lampen (Zigbee, via zigbee2mqtt) worden vervangen door IKEA
KAJPLATS (Matter). Op 4 september 2026 waren de eerste twee ruimtes aan de
beurt: de twee hanglampen boven de eettafel en de vier plafondspots in de
woonkamer. Dit stuk legt vast waar dat aan raakt, want het is niet alleen een
lamp verwisselen.

## De kern: een Zigbee2MQTT-groep kan geen Matter-lamp bevatten

Bijna alle `light.*_lampen` in dit huis zijn **groepen in zigbee2mqtt**, geen
helpers in Home Assistant. Ze leven in het Zigbee-netwerk zelf: HA stuurt één
commando en de coördinator zet het als multicast op de lucht, zodat alle
lampen tegelijk aangaan. Precies daarom kan er niets in wat niet op Zigbee zit.

Het verschil is aan het groepsattribuut te zien:

| Soort groep | Waar gemaakt | Attribuut met de leden |
| --- | --- | --- |
| Zigbee2MQTT-groep | z2m → Groups | `group_entities` |
| HA-groephelper | Instellingen → Helpers | `entity_id` |
| YAML-groep (`platform: group`) | een package | `entity_id` |

`expand()` werkt alleen op de tweede en derde soort; op een Z2M-groep krijg je
de groep zelf terug, niet zijn leden. Templates die de samenstelling van een
groep uitlezen (`script.woonkamer_media_licht`) vragen daarom om **allebei** de
attributen met een `or`, zodat ze blijven werken als een ruimte van soort
wisselt.

## Wat er per ruimte gebeurt

Er zijn twee uitkomsten, en welke je krijgt hangt ervan af of de hele ruimte
overgaat.

**Alle lampen van de ruimte gaan over (eettafel).** De Z2M-groep verdwijnt en
daarmee komt de entity-id vrij. Maak dan een HA-groephelper met **dezelfde
naam** (`eettafel_lampen`), dan ontstaat `light.eettafel_lampen` opnieuw en
hoeft er in de config geen letter te veranderen — de twintig verwijzingen naar
die groep blijven kloppen.

**Maar een deel gaat over (woonkamer).** De Z2M-groep blijft bestaan voor wat
er nog op Zigbee zit, dus de naam is bezet en de ruimte heeft vanaf dan twee
groepen:

| Entiteit | Soort | Inhoud |
| --- | --- | --- |
| `light.woonkamer_lampen` | Z2M-groep 7 | Hue Signe, 2 Play bars, Hue tafellamp |
| `light.woonkamer_spots` | HA-groephelper | de 4 Matter-plafondspots |

Die twee horen overal samen genoemd te worden. De plekken die dat sinds
4 september doen:

| Bestand | Wat |
| --- | --- |
| `packages/0 - Ground Floor/Livingroom/Lights.yaml` | thuiskomst/vertrek (blueprint), aanvullicht humble + ledstrip, kleur terug naar 2600 K |
| `packages/0 - Ground Floor/Livingroom/Media.yaml` | `plafond` in `script.woonkamer_media_licht`, de terugzet-tak, de humble-check |
| `packages/0 - Ground Floor/Livingroom/Cast.yaml` | opnieuw casten zodra er licht aangaat |
| `packages/0 - Ground Floor/Hallway/Alarm.yaml` | de vertrekronde |
| `packages/0 - Ground Floor/Kitchen/Voice.yaml` | intent "doe de lichten uit" |
| `packages/9 - Other/Lights.yaml` | poortwachter van de slaapronde én `&binnen_lampen` (dus ook de nachtsweep) |
| `packages/9 - Other/Alarm.yaml` | donkertest, waarschuwing, momentopname, alles-aan, flitslus |
| `packages/9 - Other/Firealarm.yaml` | `light.all_lights` |
| `packages/9 - Other/Music.yaml` | ochtendmuziek bij licht aan |
| `packages/9 - Other/Klokken.yaml` | `klok_aan` en zijn trigger |
| `packages/9 - Other/Brandweer Automations.yaml` | "brandden de lampen al vóór de melding" |
| `dashboards/home/overzicht.yaml` | "Alles uit" op de begane grond + een eigen lichtkaart |
| `dashboards/home/overzicht/kolom_links.yaml` | de RUIMTES-regel van de begane grond |

`dashboards/home/dashboard.yaml` is bewust overgeslagen: die view staat sinds
14 augustus 2026 uit in `ui-lovelace.yaml`. Zet je hem ooit terug, dan moeten
de spots daar alsnog bij.

## Drie dingen die geen probleem blijken

- **`effect` en `flash`.** De KAJPLATS meldt alleen `TRANSITION`
  (`supported_features: 32`) en heeft geen effectlijst. Toch mogen de spots in
  aanroepen mét `effect: breathe` of `flash: long` staan: de light-integratie
  gooit per entiteit de parameters weg die die lamp niet kent
  (`filter_turn_on_params`). De spots gaan dan gewoon aan zonder mee te ademen.
- **Kleurtemperatuur.** De spots kunnen 1801–6535 K, ruimer dan de Hue-lampen
  (2000–6535 K). Alle vaste waarden in dit huis (2200, 2600, 3984 K) vallen
  binnen allebei.
- **Kleur.** De spots kunnen `hs`/`xy`, dus de terug-naar-2600 K-regel bij
  binnenkomst kan ook op hen slaan.

## Wat je bij een volgende ruimte niet moet vergeten

1. **De oude lampen uit z2m halen.** Blijft er een retained
   `homeassistant/.../config` op de broker staan, dan komt de dode entiteit na
   elke herstart terug en blijft hij op zijn laatste stand (`on`) hangen. Op
   4 september was dat `light.eettafel_hanglamp_rechts`, terwijl de linker wél
   netjes was opgeruimd.
2. **Powercalc.** De schattingssensoren hangen aan de oude apparaten en
   verdwijnen mee; `sensor.<ruimte>_verlichting_power` telt daarna te weinig,
   of telt een `unavailable` bron mee. Nieuwe entries aanmaken voor de
   Matter-lampen.
3. **`light.all_lights`** in `packages/9 - Other/Firealarm.yaml` en
   **`&binnen_lampen`** in `packages/9 - Other/Lights.yaml` zijn de twee
   lijsten waar een ruimte stilletjes uit kan vallen zonder dat iets een fout
   geeft — een `light.turn_off` naar een lege of niet-bestaande groep is geen
   fout, gewoon een commando dat niets doet.
4. **Namen.** De Matter-integratie zet de ruimte vóór de apparaatnaam, dus een
   apparaat "Woonkamer Spots Voor" in ruimte Woonkamer wordt
   `light.woonkamer_woonkamer_spots_voor`. Wil je de huisconventie
   (`light.keuken_spot_links`) aanhouden, hernoem de entity-id dan meteen na
   het koppelen — daarna staat hij in de config.
