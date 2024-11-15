[![GitHub stars](https://img.shields.io/github/stars/robinbohnen/home-assistant.svg?style=plasticr)](https://github.com/robinbohnen/home-assistant/stargazers)
[![GitHub last commit](https://img.shields.io/github/last-commit/robinbohnen/home-assistant.svg?style=plasticr)](https://github.com/robinbohnen/home-assistant/commits/master)
[![HA Version](https://img.shields.io/badge/Running%20Home%20Assistant-2024.11.1%20-darkblue)](https://github.com/home-assistant/home-assistant/releases/latest)
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
 | [Other Integrations](#integrations) |

## <a name="hubs">Hubs</a>

| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [SONOFF Zigbee 3.0 USB Dongle Plus-E](https://amzn.to/40G1ENb) | 1 | USB | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Used to control all Zigbee smart bulbs and Blinds. |
| [Somfy Tahoma](https://amzn.to/4fkzKee) | 1 | Ethernet | [Somfy](https://www.home-assistant.io/integrations/somfy/) | Used to control Somfy accessories like rollerblinds and sunscreens. |

## <a name="lights">Lights</a>
| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [Ikea Tradfri bulb GU10](https://www.ikea.com/nl/en/p/tradfri-led-bulb-gu10-345-lumen-wireless-dimmable-colour-and-white-spectrum-70547474/) | 42 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Led spots GU10 with colour |
| [Ikea Tradfri bulb E27](https://www.ikea.com/nl/en/p/tradfri-led-bulb-e27-806-lumen-wireless-dimmable-colour-and-white-spectrum-globe-opal-white-30547471/) | 8 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Led bulb E27 with colour |
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
| [Mitsubishi Heavy Indusries 80ZR-S](https://www.klimaatshop.nl/mitsubishi-srk80zr-singlesplit-airco-8-0kw.html) | 1 | Wi-Fi | [IntesisHome](https://www.home-assistant.io/integrations/intesishome/) | Airconditioning Unit on our Stairways to the Attic; cools upper floors |

## <a name="other">Other Hardware</a>
| [Menu](#menu) |

| Device  | Quantity | Connection | Home Assistant | Notes |
| ------------- | :---: | ------------- | ------------- | ------------- |
| [HP Smart Tank 7300 series](https://amzn.to/3O3s9EK) | 1 | Ethernet | [Internet Printing Protocol (IPP)](https://www.home-assistant.io/integrations/ipp/) | HP Printer for printing all kinds of information |
| [Ulanzi Awtrix Smart Pixel Clock](https://amzn.to/4fnTLAK) | 1 | Wi-Fi | [MQTT](https://www.home-assistant.io/integrations/mqtt/)| 8x32 RGB LED panel used to display time and various notifications / status.  Using the [Awtrix Light](https://github.com/Blueforcer/awtrix-light) project to integrate with MQTT and Home Assistant.  It also looks super cool. |
| [La Marzocco Linea Micra](https://www.lamarzocco.com/fr/en/home-products/home-espresso-machines/linea-micra/) | 1 | Wi-Fi | [La Marzocco](https://www.home-assistant.io/integrations/lamarzocco/) | Coffee machine controllable by HA |
| [Ikea Tradfri Control Outlet](https://www.ikea.com/nl/en/p/tradfri-control-outlet-kit-smart-40364748/) | 6 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Control outlet without metering to turn devices on/off |
| [Tuya Zigbee Smart Power Meter Socket](https://amzn.to/3O7eJYs) | 6 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Control outlet with metering to turn devices on/off and meter them |
| [Aqara Door and Window magnet sensor](https://amzn.to/3UNSCdd) | 24 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Magnetic sensor for doors and windows |
| [Aqara Motion Sensor P1](https://amzn.to/3AF04R9) | 15 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Motion sensor to control lighting and alarm |
| [Aqara Temperature Sensor](https://amzn.to/3CnNmqB) | 8 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Temperature and humidity sensor for indoor use |
| [Aqara Wireless Mini Switch](https://amzn.to/3AJqMYM) | 6 | Zigbee | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Mini button to control things that can't be automated (for now) |

## <a name="vms">Virtual Machines</a>
| [Menu](#menu) |

| Device | Location | Home Assistant | Notes |
| ------------- | ------------- | ------------- | ------------- |
| AdGuard Home | Proxmox VE | [Adguard Home](https://www.home-assistant.io/integrations/adguard/) | To block all advertising and have some Child control |
| Scrypted | Proxmox VE | [Proxmox VE](https://www.home-assistant.io/integrations/proxmoxve/) | Hosts all Proxmox vitual machines (even the Home Assistant one) |
| Zigbee2MQTT | Proxmox VE | [MQTT](https://www.home-assistant.io/integrations/mqtt/) | Virtual Machine with Zigbee2MQTT seperated from Home Assistant |
| Nginx Proxy Manager | Proxmox VE | N/A | Proxy for ssl-ing Home-Assistant and other Proxmox Virtual Machines |

## <a name="integrations">Other Integrations</a>
| [Menu](#menu) |

| Integration | Home Assistant | Notes |
| ------------- | ------------- | ------------- |
| Adguard Home | [Link](https://www.home-assistant.io/integrations/adguard) | Block all advertising |
| Afvalinfo | [Link](https://github.com/heyajohnny/afvalinfo) | For dutchies to check when garbage is collected |
| Alarmo | [Link](https://github.com/nielsfaber/alarmo) | Create your own alarm |
| APC UPS Daemon | [Link](https://www.home-assistant.io/integrations/apcupsd) | Monitor local UPS device |
| Apple TV | [Link](https://www.home-assistant.io/integrations/apple_tv) | Control your Apple TV Device |
| Bluetooth | [Link](https://www.home-assistant.io/integrations/bluetooth) | Locate local Bluetooth devices  |
| Buienradar | [Link](https://www.home-assistant.io/integrations/buienradar) | Monitor our dutch rainy weather |
| CalDAV | [Link](https://www.home-assistant.io/integrations/caldav) | Integrate calendars to add appointments |
| Command Line | [Link](https://www.home-assistant.io/integrations/command_line) | To check and operate thing in commandline |
| CPU-Snelheid | [Link](https://www.home-assistant.io/integrations/cpuspeed) | Add sensors for monitoring CPU speed |
| DLNA Digital Media Renderer | [Link](https://www.home-assistant.io/integrations/dlna_dmr) | Control DLNA enabled devices |
| DSMR Smart Meter | [Link](https://www.home-assistant.io/integrations/dsmr) | Monitoring power and gas usage |
| Electricity Maps | [Link](https://www.home-assistant.io/integrations/co2signal) | Add CO2 sensor |
| ENTSO-e Transparency Platform | [Link](https://github.com/JaccoR/hass-entso-e) | Check ultra flexibel energy prices |
| Feestdag | [Link](https://www.home-assistant.io/integrations/holiday) | Add holiday sensors |
| Forecast.Solar | [Link](https://www.home-assistant.io/integrations/forecast_solar) | Create a forecast of solar power |
| GoodWe Inverter | [Link](https://www.home-assistant.io/integrations/goodwe) | Local communication with GoodWe inverter |
| GoodWe SEMS API | [Link](https://github.com/TimSoethout/goodwe-sems-home-assistant) | Cloud communication with GoodWe inverter |
| Google Cast | [Link](https://www.home-assistant.io/integrations/cast) | Cast dashboard to Google Nest Hub devices |
| Google Translate Text-to-Speech | [Link](https://www.home-assistant.io/integrations/google_translate) | Speak messages to media players |
| HACS | [Link](https://hacs.xyz/docs/use/) | Use non-official Home Assistant Plugins |
| Home Assistant Supervisor | [Link](https://www.home-assistant.io/integrations/hassio) | Easy for Home Assistant operation |
| iBeacon Tracker | [Link](https://www.home-assistant.io/integrations/ibeacon) | Track devices with Bluetooth |
| Internet Printing Protocol (IPP) | [Link](https://www.home-assistant.io/integrations/ipp) | Monitor local printer |
| IntesisHome | [Link](https://www.home-assistant.io/integrations/intesishome) | Control Mitsubishi Airco |
| Intex Spa | [Link](https://github.com/mathieu-mp/homeassistant-intex-spa) | Control spa bubble bath |
| iRobot Roomba and Braava | [Link](https://www.home-assistant.io/integrations/roomba) | Control and monitor iRobot vacuum cleaners |
| KNMI | [Link](https://github.com/golles/ha-knmi/blob/main/README.md) | Monitor Dutch Weather and alarms |
| La Marzocco | [Link](https://www.home-assistant.io/integrations/lamarzocco) | Control the delicious coffee machine |
| LOQED Touch Smart Lock | [Link](https://www.home-assistant.io/integrations/loqed) | Control the smartlock |
| Matter (BETA) | [Link](https://www.home-assistant.io/integrations/matter) | Not used yet |
| Meteorologisk institutt (Met.no) | [Link](https://www.home-assistant.io/integrations/met) | Check local weather |
| Miele | [Link](https://github.com/astrandb/miele) | Our oven and dishwasher are smart and can be monitored and controlled with this plugin |
| Mobiele app | [Link](https://www.home-assistant.io/integrations/mobile_app) | Check all sensors of your mobile device |
| Motionblinds | [Link](https://www.home-assistant.io/integrations/motion_blinds) | Smart blinds to stop sun |
| MQTT | [Link](https://www.home-assistant.io/integrations/mqtt) | Integrate Zigbee2MQTT with Home Assistant |
| Nest Protect | [Link](https://github.com/imicknl/ha-nest-protect) | Check the status of smoke and CO sensors |
| Office 365 | [Link](https://github.com/RogerSelwyn/O365-HomeAssistant) | Integration to control mail, and calendars in M365 |
| Overkiz | [Link](https://www.home-assistant.io/integrations/overkiz) | Control your Somfy devices |
| Ping (ICMP) | [Link](https://www.home-assistant.io/integrations/ping) | Check the status of local network devices |
| Places | [Link](https://github.com/custom-components/places) | Check translated location of persons |
| Proxmox VE | [Link](https://www.home-assistant.io/integrations/proxmoxve) | Monitor status of Proxmox VM's |
| Pushover | [Link](https://www.home-assistant.io/integrations/pushover) | Send messages outside of HomeAssistant (to be able to mure sometimes) |
| Radio Browser | [Link](https://www.home-assistant.io/integrations/radio_browser) | Play music on Sonos or other devices |
| RESTful command | [Link](https://www.home-assistant.io/integrations/rest_command) | Send commands to non-local stuff |
| Ring | [Link](https://www.home-assistant.io/integrations/ring) | Integrate doorbell and some (older) cameras |
| Samsung Smart TV | [Link](https://www.home-assistant.io/integrations/samsungtv) | Check and interact with TVs |
| Scrape | [Link](https://www.home-assistant.io/integrations/scrape) | Get some information from the WWW |
| Sonos | [Link](https://www.home-assistant.io/integrations/sonos) | Control media players of Sonos |
| Speedtest.net | [Link](https://www.home-assistant.io/integrations/speedtestdotnet) | Monitor local network |
| System Monitor | [Link](https://www.home-assistant.io/integrations/systemmonitor) | Check all sensors of the system |
| Tado | [Link](https://www.home-assistant.io/integrations/tado) | Control the temperature inside |
| Thread | [Link](https://www.home-assistant.io/integrations/thread) | Not used yet |
| UniFi Network | [Link](https://www.home-assistant.io/integrations/unifi) | Monitor network devices |
| UniFi Protect | [Link](https://www.home-assistant.io/integrations/unifiprotect) | Integrate cameras to Home Assistant |
| Waze Reistijd | [Link](https://www.home-assistant.io/integrations/waze_travel_time) | Calculate time to travel home or work |
| Werkdag | [Link](https://www.home-assistant.io/integrations/workday) | Check if I have to work today |
| Xiaomi Miio | [Link](https://www.home-assistant.io/integrations/xiaomi_miio) | Interact with Roborock Vacuum robot |
| Zon | [Link](https://www.home-assistant.io/integrations/sun) | Check sun to automate things |
| Zonneplan | [Link](https://github.com/fsaris/home-assistant-zonneplan-one) | Our power and gas provider |
