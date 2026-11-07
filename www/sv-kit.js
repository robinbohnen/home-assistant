/*
 * sv-kit.js - de bouwstenen van de "Server-stijl" voor de dashboards.
 *
 * Sinds 7 november 2026 zien Server (dashboards/server.yaml), Kamers, School,
 * Klimaat, Accu, Omvormer en Systeem er hetzelfde uit: panelen met een kop in
 * kleine hoofdletters en een badge, één groot getal in kleur, tegels, en
 * compacte regels. De stijlgids staat in docs/dashboard-stijl.md.
 *
 * GEBRUIK in een button-card (template `sv_paneel` of `sv_html`):
 *
 *   [[[
 *     var S = window.svKit && window.svKit(states);
 *     if(!S) return '';
 *     return S.kop('KLIMAAT', S.pil('ok', 'in orde'))
 *       + S.tegels([{klik: 'sensor.x', label: 'BINNEN', waarde: '21°', k: 'ok', sub: 'gemiddeld'}])
 *       + S.rijen([{klik: 'sensor.y', naam: 'Vocht', waarde: '48%'}], 2);
 *   ]]]
 *
 * WAAROM EEN MODULE en geen gekopieerde helpers per kaart (zoals server.yaml
 * nog doet): zes weergaven met elk vijf panelen = dertig kopieën van `pil`,
 * `tegel` en `rij`. Eén plek houdt de stijl gelijk. Hij staat in
 * `frontend.extra_module_url` (laadt vóór Lovelace) én in resources.yaml,
 * met dezelfde URL - zie tests/test_frontend_resources.py.
 *
 * VEILIGHEID. Alles wat als TEKST binnenkomt (`naam`, `waarde`, `sub`, `label`,
 * de tekst van een pil) is HTML: de aanroeper escapet tekst uit een state zelf
 * met S.esc(). `klik` wordt hier gecontroleerd: alleen een entity-id, een
 * pop-up-hash (#a-z0-9-) of een pad (/a-z0-9-/#) wordt een onclick; al het
 * andere wordt genegeerd, zodat een vreemde id nooit JavaScript kan worden.
 *
 * Bump `?v=` in beide URL's na een wijziging (Safari-cache).
 */
(function (root) {
  'use strict';

  var ID = /^[a-z_]+\.[a-z0-9_]+$/;
  var HASH = /^#[a-z0-9-]+$/;
  var PAD = /^\/[a-z0-9_\/-]*(#[a-z0-9-]+)?$/;

  function esc(v) {
    return String(v).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  function nl(n, d) {
    d = d || 0;
    return Number(n).toLocaleString('nl-NL', {minimumFractionDigits: d, maximumFractionDigits: d});
  }

  /* Onclick-attribuut (met spatie ervoor) voor een entity (more-info), een
     pop-up (#hash) of een andere pagina (/pad). Leeg als `klik` niet deugt. */
  function klik(doel) {
    if (!doel) return '';
    doel = String(doel);
    var js;
    if (ID.test(doel)) {
      js = "this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:'" + doel + "'},bubbles:true,composed:true}))";
    } else if (HASH.test(doel) || PAD.test(doel)) {
      // Dezelfde navigate-actie als een tap_action: Bubble Card reageert hier
      // wel op, op een eigen pushState niet (gemeten op 07-11-2026).
      js = "this.dispatchEvent(new CustomEvent('hass-action',{detail:{action:'tap',config:{tap_action:{action:'navigate',navigation_path:'" + doel + "'}}},bubbles:true,composed:true}))";
    } else {
      return '';
    }
    return ' onclick="' + js + '"';
  }

  function cursor(doel) { return klik(doel) ? 'cursor:pointer;' : ''; }

  /* Kleur: een token-naam (ok, warn, bad, info, ink-55 ...) of null = tekstkleur. */
  function kleur(k) { return k ? 'var(--ov-' + k + ')' : 'var(--primary-text-color)'; }

  function pil(k, t) {
    if (!k || k === 'grijs') {
      return '<span style="font-size:11.5px;font-weight:600;padding:3px 11px;border-radius:20px;white-space:nowrap;color:var(--ov-ink-50);background:var(--ov-ink-6)">' + t + '</span>';
    }
    return '<span style="font-size:11.5px;font-weight:600;padding:3px 11px;border-radius:20px;white-space:nowrap;color:var(--ov-' + k + ');background:var(--ov-' + k + '-15)">' + t + '</span>';
  }

  /* Kop van een paneel: TITEL links (klein, hoofdletters), badge rechts.
     `opts.klik` maakt de titel klikbaar, `opts.eerste: false` zet er een lijn
     boven (een tweede blok binnen hetzelfde paneel, zoals Ventileren). */
  function kop(titel, badge, opts) {
    opts = opts || {};
    var lijn = opts.eerste === false ? 'padding:8px 0 4px 0;border-top:1px solid var(--ov-ink-6);' : 'padding:0 0 6px 0;';
    return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;' + lijn + '">'
      + '<span' + klik(opts.klik) + ' style="' + cursor(opts.klik) + 'font-size:12px;font-weight:700;letter-spacing:1.2px;color:var(--ov-ink-55)">' + titel + '</span>'
      + (badge || '') + '</div>';
  }

  /* Subkop binnen een paneel (zoals SCHIJVEN bij de NAS), met tekst rechts. */
  function subkop(titel, rechts) {
    return '<div style="display:flex;justify-content:space-between;font-size:10.5px;font-weight:700;letter-spacing:1px;color:var(--ov-ink-45);margin:10px 0 5px 0">'
      + '<span>' + titel + '</span><span style="font-weight:600;letter-spacing:0">' + (rechts || '') + '</span></div>';
  }

  /* Het grote getal: waarde in kleur k, eenheid klein erachter, sub eronder. */
  function groot(o) {
    return '<div' + klik(o.klik) + ' style="' + cursor(o.klik) + 'min-width:0">'
      + '<div style="font-size:38px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums;white-space:nowrap;color:' + kleur(o.k) + '">' + o.waarde
      + (o.eenheid ? '<span style="font-size:16px;font-weight:600;color:var(--ov-ink-55);margin-left:5px">' + o.eenheid + '</span>' : '') + '</div>'
      + (o.sub ? '<div style="font-size:12px;color:var(--ov-ink-50);margin-top:6px">' + o.sub + '</div>' : '') + '</div>';
  }

  /* Groot getal links, korte regels (label - waarde) rechts: de kop van het rackpaneel. */
  function grootMetRegels(o, regels) {
    return '<div style="display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:22px;align-items:center">'
      + groot(o) + '<div style="min-width:0">' + (regels || []).map(regel).join('') + '</div></div>';
  }

  function regel(r) {
    return '<div' + klik(r.klik) + ' style="' + cursor(r.klik) + 'display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:1px 0">'
      + '<span style="color:var(--ov-ink-55)">' + r.naam + '</span>'
      + '<span style="font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap;color:' + kleur(r.k) + '">' + r.waarde + '</span></div>';
  }

  function tegel(t) {
    return '<div' + klik(t.klik) + ' style="' + cursor(t.klik) + 'flex:1 1 ' + (t.breed || 76) + 'px;min-width:0;background:var(--ov-ink-4);border-radius:12px;padding:6px 11px">'
      + '<div style="font-size:10.5px;font-weight:700;letter-spacing:1px;color:var(--ov-ink-55);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + t.label + '</div>'
      + '<div style="font-size:20px;font-weight:700;line-height:1.2;margin-top:1px;white-space:nowrap;font-variant-numeric:tabular-nums;color:' + kleur(t.k || 'ink-80') + '">' + t.waarde + '</div>'
      + (t.sub !== undefined && t.sub !== '' ? '<div style="font-size:11.5px;color:var(--ov-ink-58);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + t.sub + '</div>' : '')
      + '</div>';
  }

  function tegels(lijst, opts) {
    opts = opts || {};
    return '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:' + (opts.marge === undefined ? 10 : opts.marge) + 'px">'
      + (lijst || []).map(tegel).join('') + '</div>';
  }

  function balk(pct, k, dik) {
    var h = dik || 6;
    return '<div style="height:' + h + 'px;border-radius:' + h / 2 + 'px;background:var(--ov-ink-6);margin-top:5px;overflow:hidden"><div style="height:' + h + 'px;border-radius:' + h / 2 + 'px;min-width:' + (pct > 0 ? 3 : 0) + 'px;width:'
      + Math.max(0, Math.min(100, Number(pct) || 0)) + '%;background:var(--ov-' + (k || 'info') + ')"></div></div>';
  }

  /* Eén regel: naam links, waarde rechts (vet, kleur k), optioneel iets
     eronder (`extra`, bv. een balk). `vol: true` = over alle kolommen. */
  function rij(r) {
    return '<div' + klik(r.klik) + ' style="' + cursor(r.klik) + (r.vol || r.extra ? 'grid-column:1/-1;' : '') + 'padding:4px 0;border-top:1px solid var(--ov-ink-6);min-width:0">'
      + '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;font-size:13px">'
      + '<span style="color:var(--ov-ink-80);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + r.naam + '</span>'
      + '<span style="font-weight:600;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;color:' + kleur(r.k) + '">' + r.waarde + '</span></div>'
      + (r.extra || '') + '</div>';
  }

  /* Regels onder elkaar (kolommen = 1) of in een raster van 2 kolommen. */
  function rijen(lijst, kolommen, marge) {
    lijst = (lijst || []).filter(Boolean);
    if (!lijst.length) return '';
    var n = kolommen || 1;
    return '<div style="margin-top:' + (marge === undefined ? 6 : marge) + 'px;display:grid;grid-template-columns:repeat(' + n + ',minmax(0,1fr));column-gap:20px">'
      + lijst.map(rij).join('') + '</div>';
  }

  function stip(k, maat) {
    var m = maat || 8;
    return '<span style="display:inline-block;flex:none;width:' + m + 'px;height:' + m + 'px;border-radius:50%;background:var(--ov-' + k + ')"></span>';
  }

  /* Chip (zoals de back-uptaken): stip, vette naam, grijze toelichting. */
  function chip(c) {
    var fout = c.k === 'bad' || c.k === 'warn';
    return '<span' + klik(c.klik) + (c.titel ? ' title="' + c.titel + '"' : '') + ' style="' + cursor(c.klik) + 'display:inline-flex;align-items:center;gap:6px;font-size:11.5px;padding:3px 9px;border-radius:20px;white-space:nowrap;background:'
      + (fout ? 'var(--ov-' + c.k + '-15)' : 'var(--ov-ink-6)') + '">' + stip(c.k || 'ink-25', 6)
      + '<span style="font-weight:600;color:' + (fout ? 'var(--ov-' + c.k + ')' : 'var(--primary-text-color)') + '">' + c.naam + '</span>'
      + (c.toel ? '<span style="color:var(--ov-ink-50)">' + c.toel + '</span>' : '') + '</span>';
  }

  function chips(lijst) {
    return '<div style="display:flex;flex-wrap:wrap;gap:5px;padding:4px 0 2px 0">' + (lijst || []).map(chip).join('') + '</div>';
  }

  /* Tabel zoals VM'S EN CONTAINERS: kolombreedtes, kopregel, rijen van cellen.
     `rijen` = [{klik, k (stip), cellen: [html, ...]}]. Eerste kolom = naam. */
  function tabel(o) {
    var kol = 'display:grid;grid-template-columns:' + (o.stip ? '10px ' : '') + 'minmax(0,1fr) ' + (o.breedtes || []).map(function (b) { return b + 'px'; }).join(' ') + ';column-gap:10px;align-items:center';
    var kopregel = (o.koppen || []).length
      ? '<div style="' + kol + ';font-size:10.5px;font-weight:700;letter-spacing:.8px;color:var(--ov-ink-45);padding-bottom:4px">'
        + (o.stip ? '<span></span>' : '') + '<span>' + (o.koppen[0] || '') + '</span>'
        + o.koppen.slice(1).map(function (k) { return '<span style="text-align:right">' + k + '</span>'; }).join('') + '</div>'
      : '';
    return kopregel + (o.rijen || []).map(function (r) {
      return '<div' + klik(r.klik) + ' style="' + cursor(r.klik) + kol + ';padding:4px 0;border-top:1px solid var(--ov-ink-6);font-size:13px">'
        + (o.stip ? stip(r.k || 'ink-25') : '')
        + '<span style="min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + r.cellen[0] + '</span>'
        + r.cellen.slice(1).map(function (c) { return '<span style="text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums">' + c + '</span>'; }).join('')
        + '</div>';
    }).join('');
  }

  /* Kleine grijze toelichting onder een paneel. */
  function voet(t) {
    return '<div style="font-size:11.5px;color:var(--ov-ink-45);padding-top:8px;line-height:1.4">' + t + '</div>';
  }

  function tekst(t) {
    return '<div style="font-size:12.5px;line-height:1.4;color:var(--ov-ink-70);padding-bottom:6px">' + t + '</div>';
  }

  /* "4 min", "3 uur", "2 dagen" voor een duur in milliseconden. */
  function duur(ms) {
    var u = ms / 3600000;
    return u < 1 ? Math.max(1, Math.round(u * 60)) + ' min' : (u < 48 ? Math.round(u) + ' uur' : Math.round(u / 24) + ' dagen');
  }

  /* Drempelkleur: waarde v tegen warm/heet (hoger = erger; omgekeerd met laag: true). */
  function drempel(v, warm, heet, laag) {
    if (v === null || v === undefined || isNaN(v)) return 'ink-35';
    if (laag) return v <= heet ? 'bad' : (v <= warm ? 'warn' : 'ok');
    return v >= heet ? 'bad' : (v >= warm ? 'warn' : 'ok');
  }

  /* Badge van een paneel uit een lijst problemen [{k: 'bad'|'warn', t}]. */
  function oordeel(problemen, goed) {
    problemen = (problemen || []).filter(Boolean);
    if (!problemen.length) return pil('ok', goed || 'in orde');
    if (problemen.length === 1) return pil(problemen[0].k, problemen[0].t);
    var ergste = problemen.some(function (p) { return p.k === 'bad'; }) ? 'bad' : 'warn';
    return pil(ergste, problemen.length + ' meldingen');
  }

  root.svKit = function (states) {
    states = states || {};
    var st = function (id) { return states[id]; };
    var weg = function (s) {
      if (typeof s === 'string') s = states[s];
      return !s || ['unavailable', 'unknown'].indexOf(s.state) !== -1;
    };
    var num = function (id) {
      var s = states[id]; if (!s) return null;
      var n = parseFloat(s.state); return isNaN(n) ? null : n;
    };
    var attr = function (id, a) { var s = states[id]; return s && s.attributes ? s.attributes[a] : undefined; };
    /* Getal met eenheid of '—': S.waarde('sensor.x', 1, ' °C'). */
    var waarde = function (id, d, eh) { var n = num(id); return n === null ? '—' : nl(n, d) + (eh || ''); };
    return {
      esc: esc, nl: nl, klik: klik, pil: pil, kop: kop, subkop: subkop, groot: groot,
      grootMetRegels: grootMetRegels, regel: regel, tegel: tegel, tegels: tegels, balk: balk,
      rij: rij, rijen: rijen, stip: stip, chip: chip, chips: chips, tabel: tabel, voet: voet,
      tekst: tekst, duur: duur, drempel: drempel, oordeel: oordeel,
      st: st, weg: weg, num: num, attr: attr, waarde: waarde
    };
  };
  root.svKit.versie = 1;
})(typeof window !== 'undefined' ? window : globalThis);
