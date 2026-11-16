# KEBA P40 Pro: slim laden voor een andere Home Assistant

Een overdraagbare versie van `packages/3 - Outside/Carport/KEBA P40 Pro.yaml`, de laadlogica van dit huis. Het is één
package-bestand, [`keba_p40_slim_laden.yaml`](keba_p40_slim_laden.yaml), dat je in een andere Home Assistant zet. Alles
wat per huis verschilt staat in een **adapterblok** bovenaan en is gemarkeerd met `VERVANG`.

## Wat het doet

- **Uitlezen en sturen over Modbus TCP** (poort 502): laadstatus, kabelstatus, stroom per fase, vermogen, energie en
  fasen.
- **Slim laden op kwartierprijzen.** Als slim laden aan staat, staat de paal op 0 A en gaat hij alleen open in het
  goedkoopste aaneengesloten venster dat vóór de deadline klaar is.
- **De vraag bij het insteken: "Hoe laat moet hij klaar zijn?"** Op de telefoon verschijnt een melding met het plan
  (van–tot, kWh, geschatte kosten) en drie knoppen: *Ochtend 07:00*, *Middag 17:00* of *Pas een dag later*. Wie niets
  kiest, heeft om 07:00 een volle auto. Een latere deadline maakt de goedkope (zonnige) middag bereikbaar, en dat is
  vaak de helft goedkoper.
- **Doorladen tot vol.** Het laden stopt bij vol, bij de deadline, als de stekker eruit gaat of als slim laden uit
  gaat. Het stopt niet aan het eind van het venster.
- **Veilig bij uitval.** HA herhaalt het setpoint elke 15 seconden. Valt HA weg, dan gaat de paal na de failsafe-tijd
  (standaard 30 s) gewoon weer op vol vermogen laden. Na een herstart wordt een lopende sessie hersteld.
- **Handbediening** (los van slim laden): een vaste laadstroom van 0 tot 16 A, de knop "Nu laden" en een script om
  tussen 1 en 3 fasen te schakelen.

## Vereisten

| Wat | Waarom |
|---|---|
| KEBA KeContact **P40 / P40 Pro** | Op de P30 werken de registers anders (daar is 5014 de aan/uit). |
| **Modbus TCP aan** in de webinterface van de paal | Anders is er geen verbinding. |
| **Vast IP-adres** voor de paal (DHCP-reservering) | Verhuist de paal, dan staat alles stil op `unknown` en logt HA niets. |
| **Geen andere Modbus-client** (evcc, een tweede modbus-config, een los script) | De P40 accepteert maar **één** Modbus-sessie tegelijk. |
| Home Assistant **Companion-app** | Voor de melding met de knoppen. |
| Een **prijssensor** met kwartier- of uurprijzen voor vandaag en morgen | Zie de adapter hieronder. |
| Een sensor met de **accustand** van de auto | Optioneel, maar zonder accustand plant hij altijd een volle lading. |
| Home Assistant **2024.10 of nieuwer** | De package gebruikt de nieuwe `triggers:`/`trigger:`-syntax. |

Optioneel: wil je fasen schakelen, zet dan in de paal de bron voor fasewisseling op *Modbus* (register 1550). Doe je
dat niet, dan negeert de paal het script zonder foutmelding.

## Installatie

1. Zet packages aan in `configuration.yaml` (als dat nog niet zo is):
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Kopieer `keba_p40_slim_laden.yaml` naar de map `packages/`.
3. Vul het **adapterblok** in (zoek op `VERVANG`):

   | Plek | Wat je invult | Voorbeeld |
   |---|---|---|
   | `Laadpaal - Auto accu` | Accu-sensor van de auto (%) | `sensor.tesla_battery_level`, `sensor.<auto>_batterij` (Renault), `sensor.id_4_battery_level` |
   | `Laadpaal - Auto laaddoel` | Laaddoel van de auto (%). Laat staan als de auto dat niet heeft: dan is het 100 | `number.tesla_charge_limit` |
   | `Laadpaal - Auto capaciteit` | Bruikbare (netto) accucapaciteit in kWh | `"77"` |
   | `bron_vandaag` / `bron_morgen` + de twee triggers erboven | Prijssensor met `raw_today`/`raw_tomorrow` | Nord Pool (HACS): twee keer dezelfde entiteit |
   | `host:` onder `modbus:` | IP-adres van de paal | `192.168.1.50` |
   | `notify.mobile_app_…` in script `laadpaal_melding` | Telefoon of notify-groep | `notify.mobile_app_pixel_8` |
   | `max: 16` bij `charging_current` | Maximale stroom van de installatie | `max: 32` |

   **Andere prijsbron** (geen `raw_today`/`raw_tomorrow`)? Pas dan alleen de variabele `blokken` aan. De uitkomst moet
   een lijst `[{'t': unix-tijd, 'p': prijs}, …]` blijven.
4. Kijk de configuratie na (*Ontwikkelhulpmiddelen → YAML → Configuratie controleren*) en herstart Home Assistant.
5. Controleer:
   - `sensor.charging_station_cable_state` toont een tekst en niet `unknown` (dan werkt Modbus);
   - `sensor.laadpaal_prijzen` is groter dan 0 (dan werkt de prijsbron);
   - `sensor.charging_station_laadplan` staat op `vol`, `plan`, `wacht op prijzen` of iets vergelijkbaars.
6. Zet **`input_boolean.charging_station_smart_charging`** aan. Vanaf dat moment laadt de paal alleen in het geplande
   venster.

## Bediening op het dashboard

Een simpele kaart om mee te beginnen:

```yaml
type: entities
title: Laadpaal
entities:
  - entity: input_boolean.charging_station_smart_charging
    name: Slim laden
  - entity: sensor.charging_station_charging_state
    name: Status
  - entity: sensor.charging_station_cable_state
    name: Kabel
  - entity: sensor.charging_station_active_power
    name: Vermogen
  - entity: sensor.charging_station_session_energy
    name: Deze sessie
  - entity: sensor.charging_station_laadplan
    name: Laadplan
    secondary_info: attribute
  - type: attribute
    entity: sensor.charging_station_laadplan
    attribute: van
    name: Laden vanaf
  - type: attribute
    entity: sensor.charging_station_laadplan
    attribute: tot
    name: Laden tot
  - entity: input_datetime.charging_station_klaar_om
    name: Klaar om
  - type: button
    name: Nu laden
    icon: mdi:ev-station
    action_name: Start
    tap_action:
      action: perform-action
      perform_action: script.charging_station_nu_laden
```

## Hoe het werkt (kort)

- **`sensor.charging_station_laadplan`** rekent elke minuut opnieuw uit: tekort (kWh) = (doel − accu) × capaciteit,
  laadtijd = tekort / 90% rendement / (max stroom × fasen × 230 V) × 15% marge. Daarna zoekt hij het goedkoopste
  aaneengesloten venster dat vóór de deadline klaar is. Een nieuwe sessie start pas als de accu minstens 5% onder het
  doel zit.
- **`input_boolean.charging_station_laadsessie`** is de grendel. Eenmaal begonnen blijft de sessie open tot vol,
  deadline of stekker eruit. Zonder grendel zou het venster na elke procent naar later schuiven en zou het laden aan en
  uit gaan.
- **`sensor.charging_station_gewenste_stroom`** is de enige bron voor wat er naar register 5004 gaat: 0 = pauze, 6–16
  = laden. `unavailable` betekent dat HA niet stuurt.
- **Hartslag:** elke 15 s gaat eerst 5018 (failsafe-timeout) en dan 5004 (stroom in mA) naar de paal. Zet de failsafe
  **nooit** uit (0 naar 5018). Een 0 A blijft dan ook staan als HA wegvalt, en dan laadt de auto nooit meer.

## Bewust weggelaten

- De Joulo-koppeling (ERE-certificaten), de dashboard-popups en de oude EVHUB-commando's van dit huis.
- Registers die niets toevoegen: firmware (raw), power factor, fast-charging state en 5014 (doet niets op de P40).

## Bijhouden

Het origineel blijft `packages/3 - Outside/Carport/KEBA P40 Pro.yaml`. Verbeter je de logica daar, neem het dan hier
over. `tests/test_keba_export.py` controleert dat de Modbus-registers gelijk blijven aan het origineel, dat er niets
huisspecifieks in het exportbestand sluipt, en hoe het laadplan, de stopregel en de deadline-knoppen zich gedragen:

```bash
python3 -m pytest tests/test_keba_export.py -q
```
