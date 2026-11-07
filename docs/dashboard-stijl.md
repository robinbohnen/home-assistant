# Dashboardstijl ("Server-stijl")

Sinds 7 november 2026 zien deze weergaven er hetzelfde uit als het Server-dashboard
(`dashboards/server.yaml`): **Kamers, School, Klimaat, Accu, Omvormer en Systeem**.
Bewust NIET in deze stijl: **Overzicht** (het wandpaneel, eigen vormtaal), **Nest Hub**
(Cast: geen card-mod, eigen hoogtebegroting), **Kalender** en **Camera's** (één kaart van
een andere maker op een volle pagina).

## Het idee

Eerst wat er nu speelt, groot en in kleur; details compact eronder. Eén blik op de pagina
moet zeggen of er iets mis is: elk paneel heeft rechtsboven een badge (`in orde`, `warm`,
`2 meldingen`). Alles wat een getal is, is klikbaar: naar more-info, of voor een
temperatuur/vermogen naar een pop-up met een grafiek over 4 en 24 uur.

## Opbouw van een pagina

- `panel: true` met één `vertical-stack` als wortel, daarin een `horizontal-stack` die met
  card-mod een **raster van 3 kolommen** wordt (2 onder 1500 px, 1 onder 1000 px).
  Kopieer de schil letterlijk uit `dashboards/server.yaml` (de eerste ~40 regels van
  `cards:`), inclusief `gap: 0` op de wortel (anders scrollt de pagina door de verborgen
  pop-ups).
- Elke kolom is een `vertical-stack` van **panelen**. Doel: de pagina past op één
  1080p-scherm; de langste kolom blijft onder ~950 px.
- Pop-ups (Bubble Card, `card_type: pop-up`) staan ná de `horizontal-stack` in de wortel.
  Hash in kleine letters met streepjes, uniek per pagina (bv. `#accu-lading`).

## Een paneel

- **Alleen HTML** → één `custom:button-card` met `template: sv_paneel` (de kaart is het paneel).
- **HTML + grafiek** → een `custom:mod-card` met de paneelstijl (`&paneel` uit server.yaml),
  daarin een `vertical-stack` met een `custom:button-card` `template: sv_html` en een
  `custom:apexcharts-card` (instellingen als in server.yaml: hoogte 135, geen toolbar,
  legenda boven, `var(--ov-…)`-kleuren).
- Geef elke HTML-kaart `variables: kaart: <naam>`: zo vinden de tests hem.
- `triggers_update`: de entiteiten die het paneel leest, of `sensor.time` (één render per
  minuut) als het er veel zijn of als er tijden ("4 uur geleden") in staan.

## De HTML: `window.svKit` (www/sv-kit.js)

```js
[[[
  var S = window.svKit && window.svKit(states);
  if(!S) return '';
  var t = S.num('sensor.binnen_temperatuur');
  var k = S.drempel(t, 25, 28);
  return S.kop('BINNEN', S.oordeel(t >= 25 ? [{k: k, t: 'warm'}] : []))
    + S.grootMetRegels({klik: '#klimaat-temp', waarde: t === null ? '—' : S.nl(t, 1) + '°', k: k, sub: 'gemiddeld'},
        [{naam: 'Vocht', waarde: S.waarde('sensor.vocht', 0, '%')}])
    + S.tegels([{klik: 'sensor.co2', label: 'CO₂', waarde: S.waarde('sensor.co2', 0), sub: 'ppm'}])
    + S.rijen([{klik: 'sensor.x', naam: 'Iets', waarde: '12'}], 2);
]]]
```

| Bouwsteen | Wat |
|---|---|
| `kop(titel, badge, {klik, eerste:false})` | kopregel; `eerste:false` = tweede blok in hetzelfde paneel (lijn erboven) |
| `pil(k, tekst)` / `oordeel(problemen, 'in orde')` | badge; `oordeel` kiest zelf `in orde` / de ene melding / `n meldingen` |
| `groot({waarde, eenheid, k, sub, klik})` | het grote getal (38 px) |
| `grootMetRegels(groot, [{naam, waarde, k, klik}])` | groot getal links, korte regels rechts (zoals het rackpaneel) |
| `tegels([{label, waarde, k, sub, klik, breed}])` | rij tegels (CPU/GEHEUGEN/…); `breed` = minimale breedte in px |
| `rijen([{naam, waarde, k, klik, extra, vol}], kolommen)` | regels met lijntje erboven; `kolommen: 2` voor compact; `extra` (bv. `balk(pct, k)`) of `vol` = volle breedte |
| `subkop(titel, rechts)` | kleine tussenkop (SCHIJVEN) |
| `tabel({stip, koppen, breedtes, rijen:[{k, klik, cellen}]})` | tabel zoals VM'S EN CONTAINERS |
| `chips([{naam, toel, k, klik, titel}])` | chips zoals de back-uptaken |
| `tekst(t)`, `voet(t)` | uitlegregel / kleine grijze voetnoot |
| `num(id)`, `waarde(id, dec, eenheid)`, `weg(id)`, `attr(id, a)`, `st(id)` | states lezen |
| `nl(n, dec)`, `duur(ms)`, `drempel(v, warm, heet, laag)`, `esc(tekst)` | opmaak |

**Kleuren** (tokens uit `www/ov-tokens.js`): `ok` groen = goed, `warn` oranje = let op,
`bad` rood = mis, `info` blauw = neutraal meetwaarde/balk, `accent` paars = MarkeDroid,
`clip` geel = zon, `ink-NN` = grijstinten. Een getal is alleen gekleurd als de kleur iets
betekent (temperatuur tegen een drempel); anders tekstkleur of `ink-80`.

**Veiligheid.** Tekst uit een state gaat ALTIJD door `S.esc()` voor hij in de HTML komt.
`klik` hoeft niet: sv-kit accepteert alleen een entity-id, `#hash` of `/pad`.

## Klikken

- Getal of regel van één entiteit → `klik: '<entity_id>'` (more-info).
- Temperatuur, vermogen, lading → `klik: '#<pop-up>'` met twee `apexcharts-card`s:
  `graph_span: 4h` (ruw, `update_interval: 1min`) en `24h` (`group_by` 10 min, `max` voor
  temperaturen, `avg` voor vermogen), dezelfde reeksen. Zie de pop-ups onderaan server.yaml.
- Naar een andere pagina → `klik: '/lovelace/<pad>'`.
- Bedienen (schakelaar, knop) → een gewone `custom:button-card` met een `tap_action`, in de
  stijl van de ventileerknoppen in server.yaml (`&knop`). Geen bediening in HTML-onclicks.

## Tests

Elke weergave heeft een test in `tests/` die de JS van zijn panelen in node draait met
`tests/sv_render.py` (laadt sv-kit en de templates): normale waarden, een warme/kapotte
sensor, een verdwenen entiteit (geen exception, geen `undefined`/`NaN`), en ge-escapete
state-tekst. `tests/test_button_card_klikbaar.py` controleert dat klikken overal aankomt.
