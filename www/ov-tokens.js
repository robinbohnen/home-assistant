/*
 * ov-tokens.js - de kleurtokens van de dashboards, licht en donker.
 *
 * WAAROM DIT EEN JS-MODULE IS EN GEEN CARD-MOD-BLOK
 * De tokens moeten op ALLE weergaven gelden, en drie daarvan gebruiken bewust
 * geen card-mod: `kamers` en `accu` (tegels brengen hun eigen stijl mee, zodat
 * ze leesbaar blijven als card-mod niet laadt) en `nest_hub` (in een
 * Cast-sessie draait card-mod helemaal niet - gemeten 2026-07-30). Eén
 * definitie op :root erft door alle shadow-DOM-grenzen heen en haalt dus ook
 * de Hub. Een thema zou ook kunnen, maar themes/ komt uit HACS en staat niet
 * in deze repo.
 *
 * WAAROM GEEN color-mix() EN GEEN light-dark()
 * Beide zijn nettere CSS, maar ze vragen Chrome 111+ / Safari 16.2+ (en
 * light-dark() nog veel nieuwer). De Cast-receiver van de Nest Hub is de ene
 * omgeving die hier niet te testen valt, en een niet-ondersteunde
 * kleurfunctie is geen degradatie maar een onzichtbaar element. Daarom rekent
 * dit bestand alles uit tot gewone rgba() - dat werkt op elke engine.
 *
 * WAAROM NIET prefers-color-scheme
 * Dat is de voorkeur van het BESTURINGSSYSTEEM. Home Assistant kantelt daarop
 * mee in auto-modus, maar niet als je in je profiel een vast thema kiest -
 * dan zouden de tokens en het thema het oneens zijn. Dit leest daarom de
 * werkelijk gerenderde achtergrondkleur en beslist op helderheid, zodat het
 * altijd klopt met wat je ziet.
 */
(() => {
  const ATTR = 'data-ov-scheme';
  const root = document.documentElement;

  /* Basisaccenten. Donker is wat er stond (Tailwind 400/500); licht is een
     donkerdere trap uit hetzelfde palet, want 400-tinten halen op wit geen
     leesbaar contrast. */
  const ACCENT = {
    dark:  { 'ok': '#4ade80', 'warn': '#f59e0b', 'bad': '#ef4444',
             'info': '#38bdf8', 'info-strong': '#3b82f6', 'accent': '#a78bfa',
             'clip': '#ffd60a', 'ok-wash': '#34a878',
             /* Tekst DIRECT op een accentvlak. In donkere modus zijn de
                accenten licht (Tailwind 400), dus daar hoort donkere tekst op;
                in lichte modus zijn ze donker (700) en draait dat om. Zonder
                dit token stond er straks zwarte tekst op donkergroen. */
             'on-accent': 'rgba(0,0,0,0.72)', 'on-surface-blue': '#e0f2fe' },
    light: { 'ok': '#15803d', 'warn': '#b45309', 'bad': '#b91c1c',
             'info': '#0369a1', 'info-strong': '#1d4ed8', 'accent': '#6d28d9',
             'clip': '#a16207', 'ok-wash': '#0f766e',
             'on-accent': 'rgba(255,255,255,0.95)', 'on-surface-blue': '#0c4a6e' },
  };

  /* Oppervlakken. In lichte modus leunen ze op de kaartkleur van het thema in
     plaats van op een vaste donkere waarde. */
  const SURFACE = {
    dark: {
      'panel-bg': 'rgba(22,24,31,0.72)', 'panel-bg-2': 'rgba(30,33,42,0.72)',
      'surface': '#161920', 'surface-2': '#1b1f27', 'surface-deep': '#0e1015',
      'surface-blue': 'rgba(8,25,45,0.92)', 'scrim-soft': 'rgba(10,12,18,0.55)',
    },
    light: {
      'panel-bg': 'rgba(255,255,255,0.72)', 'panel-bg-2': 'rgba(255,255,255,0.86)',
      'surface': '#f4f5f7', 'surface-2': '#eceef2', 'surface-deep': '#e4e7ec',
      'surface-blue': 'rgba(224,236,250,0.92)', 'scrim-soft': 'rgba(240,242,246,0.55)',
    },
  };

  const INKS = [3, 4, 5, 6, 7, 8, 10, 12, 14, 18, 20, 25, 28, 30, 32, 34, 35, 36, 38, 40, 42, 45, 50, 52, 55, 58, 60, 62, 65, 68, 70, 72, 75, 80, 85, 88, 90];
  const TINTS = {'bad': [0, 12, 14, 15, 16, 20, 30, 35, 45, 55], 'info': [12, 14, 15, 32, 35], 'ok': [14, 15, 16, 75], 'ok-wash': [14, 15, 16, 28], 'warn': [12, 14, 15, 16, 30, 35]};

  const hex = (h) => {
    h = h.trim().replace('#', '');
    if (h.length === 3) h = h.split('').map((c) => c + c).join('');
    return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
  };
  const rgbOf = (v) => {
    v = (v || '').trim();
    if (!v) return null;
    if (v[0] === '#') return hex(v);
    const m = v.match(/(-?[0-9.]+)[,\s]+(-?[0-9.]+)[,\s]+(-?[0-9.]+)/);
    return m ? [+m[1], +m[2], +m[3]] : null;
  };
  const lum = (c) => (0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]) / 255;

  let vorige = '';
  const update = () => {
    const cs = getComputedStyle(root);
    const bgRaw = cs.getPropertyValue('--primary-background-color') ||
                  (document.body && getComputedStyle(document.body).backgroundColor);
    const inkRaw = cs.getPropertyValue('--primary-text-color');
    const bg = rgbOf(bgRaw) || [11,13,18];
    const ink = rgbOf(inkRaw) || (lum(bg) > 0.5 ? [17,17,17] : [255,255,255]);
    const licht = lum(bg) > 0.5;
    /* Zonder deze vergelijking zou het zetten van de properties de observer
       opnieuw laten vuren en had je een oneindige lus. */
    const sleutel = licht + '|' + ink.join(',') + '|' + bg.join(',');
    if (sleutel === vorige) return;
    vorige = sleutel;

    root.setAttribute(ATTR, licht ? 'light' : 'dark');
    const st = root.style;
    const acc = ACCENT[licht ? 'light' : 'dark'];
    const surf = SURFACE[licht ? 'light' : 'dark'];

    /* Inkt: wit-op-donker was, inkt-op-licht wordt - dezelfde dekking. */
    for (const a of INKS) {
      st.setProperty('--ov-ink-' + String(a).replace('.', '_'),
                     'rgba(' + ink[0] + ',' + ink[1] + ',' + ink[2] + ',' + (a/100) + ')');
    }
    for (const [naam, kleur] of Object.entries(acc)) {
      st.setProperty('--ov-' + naam, kleur);
      if (kleur[0] !== '#') continue;   /* on-accent is al rgba, geen tinten */
      const c = hex(kleur);
      for (const a of (TINTS[naam] || [])) {
        st.setProperty('--ov-' + naam + '-' + String(a).replace('.', '_'),
                       'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + (a/100) + ')');
      }
    }
    for (const [naam, kleur] of Object.entries(surf)) st.setProperty('--ov-' + naam, kleur);
  };

  update();
  new MutationObserver(update).observe(root, { attributes: true, attributeFilter: ['style', 'class'] });
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    (mq.addEventListener ? mq.addEventListener.bind(mq, 'change') : mq.addListener.bind(mq))(update);
  }
  document.addEventListener('visibilitychange', update);
})();
