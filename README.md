[![GitHub stars](https://img.shields.io/github/stars/robinbohnen/home-assistant.svg?style=plasticr)](https://github.com/robinbohnen/home-assistant/stargazers)
[![GitHub last commit](https://img.shields.io/github/last-commit/robinbohnen/home-assistant.svg?style=plasticr)](https://github.com/robinbohnen/home-assistant/commits/master)
[![HA Version](https://img.shields.io/github/v/release/home-assistant/core?logo=github&label=Running%20Home-Assistant&color=darkblue)](https://github.com/home-assistant/home-assistant/releases/latest)
[![HA Community](https://img.shields.io/badge/HA%20community-forum-orange)](https://community.home-assistant.io/u/robinbohnen/summary)


# Overview
My personal [Home Assistant Container](https://home-assistant.io) configurations with a lot of automations. These are my active automations and configurations that I use every day. Updated frequently as I add more devices and come up with more and more complicated ways to do simple tasks.

# <a name="menu">Menu</a>
 | Menu |
 | ------------- |
 | [Hubs](#hubs) |
 | [Lights](#lights) |
 | [Locks](#locks) |
 | [Media](#media) |
 | [Network](#network) |
 | [Cameras](#cameras) |
 | [Climate](#climate) |
 | [Other Hardware](#other) |
 | [Virtual Machines](#vms) |
 | [Home Assistant Integrations](#haintegrations) |
 | [HACS Integrations](#hacsintegrations) |

## <a name="hubs">Hubs</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [SLZB-MR3](https://smlight.tech/product/slzb-mr3/) | 1 | Ethernet | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Used to control all Zigbee smart bulbs and Blinds. |
| [Somfy Tahoma](https://amzn.to/4fkzKee) | 1 | Ethernet | [Somfy](https://www.home-assistant.io/integrations/somfy/) | Used to control Somfy accessories like rollerblinds and sunscreens. |

## <a name="lights">Lights</a>
| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Ikea Tradfri bulb GU10](https://www.ikea.com/nl/en/p/tradfri-led-bulb-gu10-345-lumen-wireless-dimmable-colour-and-white-spectrum-70547474/) | 46 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Led spots GU10 with colour |
| [Ikea Tradfri bulb E27](https://www.ikea.com/nl/en/p/tradfri-led-bulb-e27-806-lumen-wireless-dimmable-colour-and-white-spectrum-globe-opal-white-30547471/) | 10 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Led bulb E27 with colour |
| [Ikea Tradfri Driver with ledstrip](https://www.ikea.com/nl/en/p/tradfri-driver-for-wireless-control-smart-grey-60342656/) | 1 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Led driver for strip |
| [Humble One Smart](https://amzn.to/40JOj6z) | 1 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Wireless light |
| Ikea Leptiter downlight (discontinued) | 8 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Led spots |
| [Aqara T1 Led Strip](https://amzn.to/4esbV2R) | 2 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Color led strip with possible extensions |

## <a name="locks">Locks</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Loqed Smartlock](https://amzn.to/3NYma4e) | 1 | Gateway | [Loqed](https://www.home-assistant.io/integrations/loqed/) | Smart locks used in automations to auto lock / unlock doors |

Locks are used mostly as a way to lock / unlock doors based on locations or time

## <a name="media">Media</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Apple TV 4k](https://amzn.to/4hJRnWe) | 1 | Wi-Fi | [Apple TV](https://www.home-assistant.io/components/apple_tv/) | Used for media playback on 4k TVs |
| [Sonos Arc](https://amzn.to/4hL4uXx) | 1 | Ethernet |  [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | TV Soundbar for audio playback and Home Assistant TTS. |
| [Sonos Sub](https://amzn.to/4hSzxke) | 1 | Ethernet | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Audio playback and Home Assistant TTS |
| [Sonos One](https://amzn.to/4hAFClb) | 4 | Wi-Fi | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Audio playback and Home Assistant TTS |
| [Sonos Move](https://amzn.to/48NwCVF) | 2 | Wi-Fi | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Portable Audio playback and Home Assistant TTS |
| [Sonos Roam](https://amzn.to/48L7YVH) | 1 | Wi-Fi | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Portable Audio playback and Home Assistant TTS |
| [Sonos Roam SL](https://amzn.to/48L7YVH) | 1 | Wi-Fi | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Portable Audio playback and Home Assistant TTS |
| [SYMFONISK Bookshelf](https://amzn.to/3YKagzW) | 4 | Wi-Fi | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Portable Audio playback and Home Assistant TTS |
| [SYMFONISK Floor lamp](https://www.ikea.com/nl/nl/p/symfonisk-vloerlamp-met-wifi-speaker-bamboe-smart-50528278/) | 1 | Wi-Fi | [Sonos](https://www.home-assistant.io/components/media_player.sonos/) | Portable Audio playback and Home Assistant TTS |
| [Samsung QE77S95C](https://amzn.to/3Z0CDuU) | 1 | Wi-Fi | [Samsung Smart TV](https://www.home-assistant.io/integrations/samsungtv/) | 4k OLED Samsung TV |
| [Samsung QE55Q74B](https://amzn.to/3AymSCa) | 1 | Wi-Fi | [Samsung Smart TV](https://www.home-assistant.io/integrations/samsungtv/) | 4k QLED Samsung TV |
| [Google Nest Hub](https://store.google.com/nl/product/nest_hub_2nd_gen?hl=nl) | 1 | Wi-Fi | [Google Cast](https://www.home-assistant.io/integrations/cast/) | Google Nest Hub to display Home Assistant Dashboards |

## <a name="network">Network</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Ubiquiti UniFi Dream Machine SE](https://amzn.to/4fFOTGD) | 1 | Ethernet | [UniFi Network](https://www.home-assistant.io/integrations/unifi/) | Dream Machine SE for controlling the network, also acts as primairy router |
| [Ubiquiti UniFi USW Flex Mini](https://amzn.to/48Jn2TI) | 4 | Ethernet | [UniFi Network](https://www.home-assistant.io/integrations/unifi/)  | Mini switches (5port) for linking wired networks |
| [Ubiquiti UniFi Switch Ultra](https://amzn.to/4emDIBJ) | 2 | Ethernet | [UniFi Network](https://www.home-assistant.io/integrations/unifi/)  | Switch for linking wired networks |
| [Ubiquiti UniFi Switch Flex](https://amzn.to/4fl1eQK) | 1 | Ethernet | [UniFi Network](https://www.home-assistant.io/integrations/unifi/)  | Switch for linking wired networks |
| [Ubiquiti UniFi U6+ Access Point](https://amzn.to/4ffxxka) | 3 | Ethernet | [UniFi Network](https://www.home-assistant.io/integrations/unifi/)  | Access point wireless networks |

## <a name="cameras">Cameras</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Ubiquiti UniFi G5 Ultra Turret](https://amzn.to/4hICDqL) | 3 | Ethernet | [Ubiquiti UniFi Video](https://www.home-assistant.io/integrations/uvc/) | Turret camera for overviewing outside |
| [Ubiquiti UniFi G4 Instant](https://amzn.to/48I7EXK) | 2 | Ethernet | [Ubiquiti UniFi Video](https://www.home-assistant.io/integrations/uvc/) | Indoor camera for overviewing inside |

## <a name="climate">Climate</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Tado Gateway](https://amzn.to/3ApEIY5) | 1 | Ethernet | [Tado](https://www.home-assistant.io/integrations/tado/) | Wi-Fi bridge for Tado thermostat |
| [Tado Thermostaat](https://amzn.to/40AsCG5) | 1 | Wi-Fi | [Tado](https://www.home-assistant.io/integrations/tado/) | Thermostat for Tado ecosystem |
| [Tado Radiator Thermostat](https://amzn.to/3CmZAj6) | 1 | Wi-Fi | [Tado](https://www.home-assistant.io/integrations/tado/) | Radiator thermostat for Tado ecosystem |
| [Mitsubishi Electric MSZ-EF50VGKB](https://aircoplazazwolle.nl/airconditioners/msz-ef50vgkb-serie-black-50kw18000btu-r32-coolheat-wifi-a) | 1 | Wi-Fi | [Melcloud](https://www.home-assistant.io/integrations/melcloud) | Airconditioning Unit for the livingroom; cooling / heating downstairs |
| [Mitsubishi Heavy Indusries 80ZR-S](https://www.klimaatshop.nl/mitsubishi-srk80zr-singlesplit-airco-8-0kw.html) | 1 | Wi-Fi | [IntesisHome](https://www.home-assistant.io/integrations/intesishome/) | Airconditioning Unit on our Stairways to the Attic; cools upper floors |

## <a name="other">Other Hardware</a>
| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Home Assistant Voice Preview](https://www.home-assistant.io/voice-pe/) | 1 | ESPHome | [ESPHome](https://www.home-assistant.io/integrations/esphome) | Advanced local voice assistant |
| [HP Smart Tank 7300 series](https://amzn.to/3O3s9EK) | 1 | Ethernet | [Internet Printing Protocol (IPP)](https://www.home-assistant.io/integrations/ipp/) | HP Printer for printing all kinds of information |
| [Ulanzi Awtrix Smart Pixel Clock](https://amzn.to/4fnTLAK) | 1 | Wi-Fi | [MQTT](https://www.home-assistant.io/integrations/mqtt/)| 8x32 RGB LED panel used to display time and various notifications / status.  Using the [Awtrix Light](https://github.com/Blueforcer/awtrix-light) project to integrate with MQTT and Home Assistant.  It also looks super cool. |
| [La Marzocco Linea Micra](https://www.lamarzocco.com/fr/en/home-products/home-espresso-machines/linea-micra/) | 1 | Wi-Fi | [La Marzocco](https://www.home-assistant.io/integrations/lamarzocco/) | Coffee machine controllable by HA |
| [Ikea INSPELNING Smart Plug](https://www.ikea.com/nl/nl/p/inspelning-stekker-smart-stroommonitor-00569836/) | 5 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Control outlet with metering to turn devices on/off |
| [Ikea Tradfri Control Outlet](https://www.ikea.com/nl/en/p/tradfri-control-outlet-kit-smart-40364748/) | 8 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Control outlet without metering to turn devices on/off |
| [Tuya Zigbee Smart Power Meter Socket](https://amzn.to/3O7eJYs) | 6 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Control outlet with metering to turn devices on/off and meter them |
| [Aqara Door and Window magnet sensor](https://amzn.to/3UNSCdd) | 24 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Magnetic sensor for doors and windows |
| [Aqara Motion Sensor P1](https://amzn.to/3AF04R9) | 15 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Motion sensor to control lighting and alarm |
| [Aqara Temperature Sensor](https://amzn.to/3CnNmqB) | 8 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Temperature and humidity sensor for indoor use |
| [Aqara Wireless Mini Switch](https://amzn.to/3AJqMYM) | 6 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Mini button to control things that can't be automated (for now) |
| [Marstek Venus E 5kWh](https://amzn.to/44bh5OF) | 1 | ESPHome | [ESPHome](https://www.home-assistant.io/integrations/esphome) | The Marstek Venus EnergyCube is a compact plug-in battery with modular capacity, perfect for sustainable energy storage and easy to install |

## <a name="vms">Virtual Machines</a>
| [Menu](#menu) |

| Device | Location | Home Assistant | Notes |
| ------------- | ------------- | ------------- | ------------- |
| Paperless | Proxmox VE | N/A | Paperless setup for storing documents |
| Scrypted | Proxmox VE | [Proxmox VE](https://www.home-assistant.io/integrations/proxmoxve/) | Hosts all Proxmox vitual machines (even the Home Assistant one) |
| Zigbee2MQTT | Proxmox VE | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Virtual Machine with Zigbee2MQTT seperated from Home Assistant |
| MQTT | Proxmox VE | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Virtual Machine with Mosquitto MQTT server seperated from Zigbee2MQTT |
| Nginx Proxy Manager | Proxmox VE | N/A | Proxy for ssl-ing Home-Assistant and other Proxmox Virtual Machines |


## <a name="haintegrations">Home Assistant Integrations</a>
| [Menu](#menu) |

| Integration | Home Assistant | Notes |
| ------------- | ------------- | ------------- |
| Acaia | [Link](https://www.home-assistant.io/integrations/acaia) | Integration with a scale for making coffee |
| Afvalinfo | [Link](https://github.com/heyajohnny/afvalinfo) | For dutchies to check when garbage is collected |
| Alarmo | [Link](https://github.com/nielsfaber/alarmo) | Create your own alarm |
| Apple TV | [Link](https://www.home-assistant.io/integrations/apple_tv) | Control your Apple TV Device |
| Backup | [Link](https://www.home-assistant.io/integrations/backup) | For making backups of the home assistant setup |
| Bitcoin | [Link](https://www.home-assistant.io/integrations/bitcoin/) | Fetch information about the Bitcoin price to display on dashboard |
| Bluetooth | [Link](https://www.home-assistant.io/integrations/bluetooth) | Locate local Bluetooth devices  |
| Buienradar | [Link](https://www.home-assistant.io/integrations/buienradar) | Monitor our dutch rainy weather |
| CalDAV | [Link](https://www.home-assistant.io/integrations/caldav) | Integrate calendars to add appointments |
| Chihiros | [Link](https://github.com/TheMicDiet/chihiros-led-control) | Integrate aquarium lights to ha |
| Command Line | [Link](https://www.home-assistant.io/integrations/command_line) | To check and operate thing in commandline |
| CPU-Snelheid | [Link](https://www.home-assistant.io/integrations/cpuspeed) | Add sensors for monitoring CPU speed |
| DLNA Digital Media Renderer | [Link](https://www.home-assistant.io/integrations/dlna_dmr) | Control DLNA enabled devices |
| DSMR Smart Meter | [Link](https://www.home-assistant.io/integrations/dsmr) | Monitoring power and gas usage |
| Eheim digital | [Link](https://www.home-assistant.io/integrations/eheimdigital) | Aquarium heater integration |
| Electricity Maps | [Link](https://www.home-assistant.io/integrations/co2signal) | Add CO2 sensor |
| ENTSO-e Transparency Platform | [Link](https://github.com/JaccoR/hass-entso-e) | Check ultra flexibel energy prices |
| ESPHome | [Link](https://www.home-assistant.io/integrations/esphome) | For controlling ESPhome devices |
| Feestdag | [Link](https://www.home-assistant.io/integrations/holiday) | Add holiday sensors |
| Forecast.Solar | [Link](https://www.home-assistant.io/integrations/forecast_solar) | Create a forecast of solar power |
| GoodWe Inverter | [Link](https://www.home-assistant.io/integrations/goodwe) | Local communication with GoodWe inverter |
| GoodWe SEMS API | [Link](https://github.com/TimSoethout/goodwe-sems-home-assistant) | Cloud communication with GoodWe inverter |
| Google Cast | [Link](https://www.home-assistant.io/integrations/cast) | Cast dashboard to Google Nest Hub devices |
| Google Translate Text-to-Speech | [Link](https://www.home-assistant.io/integrations/google_translate) | Speak messages to media players |
| HACS | [Link](https://hacs.xyz/docs/use/) | Use non-official Home Assistant Plugins |
| Home Assistant Supervisor | [Link](https://www.home-assistant.io/integrations/hassio) | Easy for Home Assistant operation |
| Home Connect | [Link](https://www.home-assistant.io/integrations/home_connect) | Insights for Bosch washers and dryers |
| iBeacon Tracker | [Link](https://www.home-assistant.io/integrations/ibeacon) | Track devices with Bluetooth |
| Internet Printing Protocol (IPP) | [Link](https://www.home-assistant.io/integrations/ipp) | Monitor local printer |
| IntesisHome | [Link](https://www.home-assistant.io/integrations/intesishome) | Control Mitsubishi Airco |
| Intex Spa | [Link](https://github.com/mathieu-mp/homeassistant-intex-spa) | Control spa bubble bath |
| KNMI | [Link](https://github.com/golles/ha-knmi/blob/main/README.md) | Monitor Dutch Weather and alarms |
| La Marzocco | [Link](https://www.home-assistant.io/integrations/lamarzocco) | Control the delicious coffee machine |
| LOQED Touch Smart Lock | [Link](https://www.home-assistant.io/integrations/loqed) | Control the smartlock |
| Matter (BETA) | [Link](https://www.home-assistant.io/integrations/matter) | Not used yet |
| Melcloud | [Link](https://www.home-assistant.io/integrations/melcloud) | Integration for Mitsubushi Electric Airco |
| Meteorologisk institutt (Met.no) | [Link](https://www.home-assistant.io/integrations/met) | Check local weather |
| Microsoft 365 - Calendar | [Link](https://github.com/RogerSelwyn/MS365-Calendar) | Microsoft 365 plugin for calendar integration |
| Microsoft 365 - Mail | [Link](https://github.com/RogerSelwyn/MS365-Mail) | Microsoft 365 plugin for mail integration |
| Microsoft 365 - Teams | [Link](https://github.com/RogerSelwyn/MS365-Teams) | Microsoft 365 plugin for teams integration |
| Microsoft 365 - To Do | [Link](https://github.com/RogerSelwyn/MS365-ToDo) | Microsoft 365 plugin for ToDo integration |
| Microsoft TTS | [Link](https://www.home-assistant.io/integrations/microsoft) | Microsoft Text-To-Speech integration for local HA Voice |
| Miele | [Link](https://github.com/astrandb/miele) | Our oven and dishwasher are smart and can be monitored and controlled with this plugin |
| Mobiele app | [Link](https://www.home-assistant.io/integrations/mobile_app) | Check all sensors of your mobile device |
| Motionblinds | [Link](https://www.home-assistant.io/integrations/motion_blinds) | Smart blinds to stop sun |
| MQTT | [Link](https://www.home-assistant.io/integrations/mqtt) | Integrate Zigbee2MQTT with Home Assistant |
| Neerslag App (Buienalarm / Buienradar) | [Link](hhttps://github.com/aex351/home-assistant-neerslag-app) | Display rain forecast using Buienalarm and/or Buienradar sensor data |
| Nest Protect | [Link](https://github.com/imicknl/ha-nest-protect) | Check the status of smoke and CO sensors |
| OneDrive | [Link](https://www.home-assistant.io/integrations/onedrive) | Add Microsoft Onedrive as storage for backups |
| Open Exchange Rates | [Link](https://www.home-assistant.io/integrations/openexchangerates/) | Add currency convertor for USD to EUR |
| OpenAI Conversation | [Link](https://www.home-assistant.io/integrations/openai_conversation) | The OpenAI integration adds a conversation agent powered by OpenAI in Home Assistant |
| Overkiz | [Link](https://www.home-assistant.io/integrations/overkiz) | Control your Somfy devices |
| Parcel | [Link](https://github.com/jmdevita/parcel-ha/blob/main/README.md) | Status of Parcels to display on dashboards |
| Ping (ICMP) | [Link](https://www.home-assistant.io/integrations/ping) | Check the status of local network devices |
| Places | [Link](https://github.com/custom-components/places) | Check translated location of persons |
| Playstation Network | [Link](https://www.home-assistant.io/integrations/playstation_network/) | Fetch information about playstation profile to HomeAssistant |
| Powercalc | [Link](https://docs.powercalc.nl) | Powercalc is a custom component for Home Assistant to estimate the power consumption (as virtual meters) of lights, fans, smart speakers and other devices, which don't have a built-in power meter |
| Proxmox VE | [Link](https://www.home-assistant.io/integrations/proxmoxve) | Monitor status of Proxmox VM's |
| Pushover | [Link](https://www.home-assistant.io/integrations/pushover) | Send messages outside of HomeAssistant (to be able to mure sometimes) |
| Radio Browser | [Link](https://www.home-assistant.io/integrations/radio_browser) | Play music on Sonos or other devices |
| Renault | [Link](https://www.home-assistant.io/integrations/renault/) | Integrate the car (Renault Megane E-Tech Espirit Alpine) to Home Assistant |
| RESTful | [Link](https://www.home-assistant.io/integrations/rest) | The rest sensor platform is consuming a given endpoint which is exposed by a RESTful API of a device, an application, or a web service |
| RESTful command | [Link](https://www.home-assistant.io/integrations/rest_command) | Send commands to non-local stuff |
| Samsung Smart TV | [Link](https://www.home-assistant.io/integrations/samsungtv) | Check and interact with TVs |
| Scrape | [Link](https://www.home-assistant.io/integrations/scrape) | Get some information from the WWW |
| SMLight SLZB | [Link](https://www.home-assistant.io/integrations/smlight/) | Integrate the SLZB-MR03 into Home Assistant and fetch information (firmware etc.) |
| Sonos | [Link](https://www.home-assistant.io/integrations/sonos) | Control media players of Sonos |
| Speedtest.net | [Link](https://www.home-assistant.io/integrations/speedtestdotnet) | Monitor local network |
| Spotify | [Link](https://www.home-assistant.io/integrations/spotify) | The Spotify media player integration lets you control your Spotify account playback and browse the Spotify media library |
| System Monitor | [Link](https://www.home-assistant.io/integrations/systemmonitor) | Check all sensors of the system |
| Tado | [Link](https://www.home-assistant.io/integrations/tado) | Control the temperature inside |
| Thread | [Link](https://www.home-assistant.io/integrations/thread) | Not used yet |
| UniFi Network | [Link](https://www.home-assistant.io/integrations/unifi) | Monitor network devices |
| UniFi Protect | [Link](https://www.home-assistant.io/integrations/unifiprotect) | Integrate cameras to Home Assistant |
| Waze Reistijd | [Link](https://www.home-assistant.io/integrations/waze_travel_time) | Calculate time to travel home or work |
| Werkdag | [Link](https://www.home-assistant.io/integrations/workday) | Check if I have to work today |
| Withings | [Link](https://www.home-assistant.io/integrations/withings/) | Integrate Withings Body Scale to Home Assistant |
| Wyoming Protocol | [Link](https://www.home-assistant.io/integrations/wyoming) | The Wyoming integration connects external voice services to Home Assistant |
| Zon | [Link](https://www.home-assistant.io/integrations/sun) | Check sun to automate things |
| Zonneplan | [Link](https://github.com/fsaris/home-assistant-zonneplan-one) | Our power and gas provider |

## <a name="hacsintegrations">HACS Integrations</a>
| [Menu](#menu) |

| Integration | GitHub URL | Notes |
| ------------- | ------------- | ------------- |
| Advanced Camera Card | [Link](https://github.com/dermotduffy/advanced-camera-card) | For showing cameras in a single overview |
| Afvalinfo | [Link](https://github.com/heyajohnny/afvalinfo) | Garbage collection information for the Netherlands |
| Alarmo | [Link](https://github.com/nielsfaber/alarmo) | Create my own alarm system with all sensors used for other stuff |
| ApexCharts Card | [Link](https://github.com/RomRider/apexcharts-card) | Display ApexCharts in Home Assistant |
| Auto-Entities | [Link](https://github.com/thomasloven/lovelace-auto-entities) | Auto include entities |
| Bubble Card | [Link](https://github.com/Clooos/Bubble-Card) | Theme I currently use for my dashboards |
| Button Card | [Link](https://github.com/custom-cards/button-card) | Some buttons I need to use this card for |
| Card-mod | [Link](https://github.com/thomasloven/lovelace-card-mod) | To modify existing cards with thing normally won't be possible |
| Chihiros | [Link](https://github.com/TheMicDiet/chihiros-led-control) | Integration to integrate aquarium lights to HA |
| Digital Clock | [Link](https://github.com/wassy92x/lovelace-digital-clock) | Integration to display a digital clock in a Dashboard |
| ENTSO-e | [Link](https://github.com/JaccoR/hass-entso-e) | Custom component for Home Assistant to fetch energy prices of all European countries from the ENTSO-e Transparency Platform |
| GOODWE Sems API | [Link](https://github.com/TimSoethout/goodwe-sems-home-assistant) | Integration for Home Assistant that retrieves PV data from GoodWe SEMS API. |
| HACS | [Link](https://github.com/hacs/integration) | Manage (Install, track, upgrade) and discover custom elements for Home Assistant directly from the UI. |
| Intex Spa | [Link](https://github.com/mathieu-mp/homeassistant-intex-spa) | This integration allows connection with the spas made to be used with the 'Intex Link - Spa Management' app |
| Kiosk Mode | [Link](https://github.com/NemesisRE/kiosk-mode) | Hides the header and/or sidebar drawer in Home Assistant lovelace dashboards. |
| KNMI | [Link](https://github.com/golles/ha-knmi) | KNMI custom component for Home Assistant. Weather data provided by KNMI |
| Logbook Card | [Link](https://github.com/royto/logbook-card) | 2 customs Lovelace cards for displaying history of an entity or multiple entities for Home Assistant. |
| M365-Calender | [Link](https://github.com/RogerSelwyn/MS365-Calendar) | Microsoft 365 Calendar Integration for Home Assistant |
| M365-Mail | [Link](https://github.com/RogerSelwyn/MS365-Mail) | Microsoft 365 Mail Integration for Home Assistant |
| M365-Teams | [Link](https://github.com/RogerSelwyn/MS365-Teams) | Microsoft 365 Teams Integration for Home Assistant |
| M365-Todo | [Link](https://github.com/RogerSelwyn/MS365-ToDo) | Microsoft 365 To Do Integration for Home Assistant |
| Mini Media Player | [Link](https://github.com/kalkih/mini-media-player) | A minimalistic yet customizable media player card for Home Assistant Lovelace UI. |
| Mini Graph Card | [Link](https://github.com/kalkih/mini-graph-card) | A minimalistic and customizable graph card for Home Assistant Lovelace UI. |
| Mushroom | [Link](https://github.com/piitaya/lovelace-mushroom) | Mushroom is a collection of cards for Home Assistant Dashboard UI. |
| Neerslag App | [Link](https://github.com/aex351/home-assistant-neerslag-app) | Neerslag app for Home Assistant. All-in-one package (Sensors + Card). |
| Nest Protect | [Link](https://github.com/iMicknl/ha-nest-protect) | Custom component for Home Assistant to interact with Nest Protect devices via an undocumented and unofficial Nest API. |
| Parcel App | [Link](https://github.com/jmdevita/parcel-ha) | This is an integration for Home Assistant that allows you to track your parcels using the Parcel REST API. |
| Places | [Link](https://github.com/custom-components/places) | Component to integrate with OpenStreetMap Reverse Geocode and create a sensor with numerous address and place attributes from a device_tracker, person, or sensor |
| Power Flow Card Plus | [Link](https://github.com/flixlix/power-flow-card-plus) | Understand and visualize way of displaying the current Power Distribution coming from and to different sources |
| PowerCalc | [Link](https://github.com/bramstroker/homeassistant-powercalc) | PowerCalc is a versatile custom component for Home Assistant that estimates power consumption for devices like lights, fans, smart speakers, and more |
| Timer Bar Card | [Link](https://github.com/rianadon/timer-bar-card) | A progress bar display for Home Assistant timers. |
| Week Planner Card | [Link](https://github.com/FamousWolf/week-planner-card) | Custom Home Assistant card displaying a responsive overview of multiple days with events from one or multiple calendars |
| Zonneplan | [Link](https://github.com/fsaris/home-assistant-zonneplan-one) | Unofficial integration for Zonneplan. This integration uses the official Zonneplan API to pull the same data available in the Zonneplan app into your Home Assistant instance. |
