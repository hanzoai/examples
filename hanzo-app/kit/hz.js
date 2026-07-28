/* hz.js — the ONE runtime every Hanzo example ships.
 *
 * It is deliberately small: DOM helpers, a persisted store, deterministic demo
 * data, four inline-SVG chart marks, and the ONE backend call every example
 * uses — POST /v1/base/collections/submissions/records on the page's OWN origin.
 * That endpoint is @hanzo/base (HIP-0014 host-as-project-ref): a published
 * <slug>.hanzo.app host serves the org's Base, so an anonymous page persists
 * real records without a bespoke backend and without a credential.
 */
(function (g) {
  'use strict';

  // ---- DOM ----------------------------------------------------------------
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /** h('div.card', {onclick}, ...children) — the one element constructor. */
  function h(sel, props, ...kids) {
    const [tag, ...cls] = String(sel).split('.');
    const el = document.createElement(tag || 'div');
    if (cls.length) el.className = cls.join(' ');
    if (props && (props.nodeType || Array.isArray(props) || typeof props !== 'object')) {
      kids.unshift(props); props = null;
    }
    for (const k in props || {}) {
      const v = props[k];
      if (v == null || v === false) continue;
      if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (k === 'html') el.innerHTML = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k in el && k !== 'list' && k !== 'form') el[k] = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    const add = (c) => {
      if (c == null || c === false) return;
      if (Array.isArray(c)) return c.forEach(add);
      el.append(c.nodeType ? c : document.createTextNode(c));
    };
    kids.forEach(add);
    return el;
  }
  const frag = (...k) => { const f = document.createDocumentFragment(); k.flat().forEach(c => c && f.append(c)); return f; };
  const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };
  const fill = (el, ...k) => { clear(el).append(frag(...k)); return el; };

  // ---- state --------------------------------------------------------------
  /** store(key, initial) — localStorage-persisted value + subscribers.
   *  ONE state primitive; every example's data lives in one of these. */
  function store(key, initial) {
    const k = 'hz:' + key, subs = new Set();
    let val = initial;
    try { const raw = localStorage.getItem(k); if (raw != null) val = JSON.parse(raw); } catch (e) { }
    const save = () => { try { localStorage.setItem(k, JSON.stringify(val)); } catch (e) { } };
    if (val === initial) save();
    return {
      get: () => val,
      set(v) { val = typeof v === 'function' ? v(val) : v; save(); subs.forEach(f => f(val)); return val; },
      sub(f) { subs.add(f); f(val); return () => subs.delete(f); },
      reset() { return this.set(structuredClone(initial)); },
    };
  }

  // ---- @hanzo/base --------------------------------------------------------
  const BASE = '/v1/base/collections/submissions/records';
  /** submit(form, data) — persist a record to this site's Base space. */
  async function submit(form, data) {
    const r = await fetch(BASE, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form: String(form).slice(0, 128), data }),
    });
    if (!r.ok) throw new Error('base ' + r.status);
    return r.json();
  }
  /** wire(formEl, name, after) — submit a <form> to Base, no page reload. */
  function wire(formEl, name, after) {
    formEl.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(formEl).entries());
      const btn = $('button[type=submit]', formEl);
      if (btn) btn.disabled = true;
      try { await submit(name, data); toast('Saved to @hanzo/base'); formEl.reset(); after && after(data); }
      catch (err) { toast('Offline demo — kept locally'); after && after(data); }
      finally { if (btn) btn.disabled = false; }
    });
    return formEl;
  }

  // ---- feedback -----------------------------------------------------------
  let tq;
  function toast(msg) {
    clearTimeout(tq); $('.toast')?.remove();
    const t = h('div.toast', msg); document.body.append(t);
    tq = setTimeout(() => t.remove(), 2400);
  }
  /** modal(title, bodyNode, onOk) — one <dialog>, reused by every example. */
  function modal(title, body, onOk, okLabel) {
    const d = h('dialog', h('form', { method: 'dialog' },
      h('h2', title), body,
      h('div.row', { style: { justifyContent: 'flex-end', marginTop: '14px' } },
        h('button.g', { type: 'button', onclick: () => d.close() }, 'Cancel'),
        onOk && h('button.p', { type: 'submit' }, okLabel || 'Save'))));
    d.addEventListener('submit', () => onOk && onOk());
    d.addEventListener('close', () => d.remove());
    document.body.append(d); d.showModal();
    return d;
  }

  // ---- deterministic demo data -------------------------------------------
  /** rng(seed) — mulberry32. Demo data is generated, stable and obviously
   *  synthetic; nothing here imitates a real person or a real metric. */
  function rng(seed) {
    let a = seed >>> 0 || 1;
    return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  const range = (n, f) => Array.from({ length: n }, (_, i) => (f ? f(i) : i));
  const pick = (r, arr) => arr[Math.floor(r() * arr.length)];
  const uid = () => Math.random().toString(36).slice(2, 10);
  const HUES = [214, 268, 158, 38, 4, 190, 320, 96];
  const hue = (s) => HUES[[...String(s)].reduce((a, c) => a + c.charCodeAt(0), 0) % HUES.length];
  /** avatar(name) — initials on a name-derived colour. Never a photograph. */
  const avatar = (name, size) => h('div.av', {
    style: {
      background: `hsl(${hue(name)} 62% 46%)`,
      width: (size || 30) + 'px', height: (size || 30) + 'px', fontSize: (size || 30) / 2.6 + 'px',
    }, title: name,
  }, String(name).split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase());

  // ---- format -------------------------------------------------------------
  const fmt = {
    n: (v, d = 0) => Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }),
    money: (v, c = 'USD') => Number(v).toLocaleString('en-US', { style: 'currency', currency: c, maximumFractionDigits: Number(v) % 1 ? 2 : 0 }),
    pct: (v, d = 1) => (v >= 0 ? '+' : '') + Number(v).toFixed(d) + '%',
    kb: (b) => b < 1024 ? b + ' B' : b < 1048576 ? (b / 1024).toFixed(1) + ' KB' : (b / 1048576).toFixed(1) + ' MB',
    date: (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    time: (d) => new Date(d).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
    ago(d) {
      const s = (Date.now() - new Date(d)) / 1000;
      for (const [u, n] of [['d', 86400], ['h', 3600], ['m', 60]]) if (s >= n) return Math.floor(s / n) + u + ' ago';
      return 'just now';
    },
  };

  // ---- charts (inline SVG; accessible, theme-aware, no library) -----------
  const SVG = 'http://www.w3.org/2000/svg';
  function svg(tag, attrs, ...kids) {
    const el = document.createElementNS(SVG, tag);
    for (const k in attrs || {}) if (attrs[k] != null) el.setAttribute(k, attrs[k]);
    kids.flat().forEach(c => c && el.append(c));
    return el;
  }
  const PAL = ['#5b8cff', '#8b5cf6', '#3ecf8e', '#f6b73c', '#f4685e', '#22b8cf', '#e879f9', '#94a3b8'];
  const path = (vals, w, hh, pad) => {
    const mn = Math.min(...vals), mx = Math.max(...vals), sp = mx - mn || 1;
    return vals.map((v, i) => `${i ? 'L' : 'M'}${(i / (vals.length - 1 || 1)) * w},${hh - pad - ((v - mn) / sp) * (hh - pad * 2)}`).join('');
  };
  /** spark(values) — a 120x32 trend line, for stat tiles and table rows. */
  function spark(vals, color, w = 120, hh = 32) {
    return svg('svg', { viewBox: `0 0 ${w} ${hh}`, width: w, height: hh, role: 'img', 'aria-label': 'trend' },
      svg('path', { d: path(vals, w, hh, 3), fill: 'none', stroke: color || PAL[0], 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
  }
  /** area(series, labels) — one filled line chart with axis + hover readout. */
  function area(vals, labels, color) {
    const w = 620, hh = 200, p = 8, c = color || PAL[0], d = path(vals, w, hh, p);
    const mx = Math.max(...vals), mn = Math.min(...vals);
    const box = h('div');
    const out = h('div.small.muted', { style: { textAlign: 'right', marginTop: '4px' } }, '');
    const s = svg('svg', { viewBox: `0 0 ${w} ${hh}`, preserveAspectRatio: 'none', style: 'width:100%;height:200px', role: 'img', 'aria-label': 'time series' },
      svg('defs', svg('linearGradient', { id: 'hzg', x1: 0, y1: 0, x2: 0, y2: 1 },
        svg('stop', { offset: '0%', 'stop-color': c, 'stop-opacity': .34 }),
        svg('stop', { offset: '100%', 'stop-color': c, 'stop-opacity': 0 }))),
      ...[0, .25, .5, .75, 1].map(f => svg('line', { x1: 0, x2: w, y1: p + f * (hh - p * 2), y2: p + f * (hh - p * 2), stroke: 'currentColor', 'stroke-opacity': .1 })),
      svg('path', { d: `${d}L${w},${hh}L0,${hh}Z`, fill: 'url(#hzg)' }),
      svg('path', { d, fill: 'none', stroke: c, 'stroke-width': 2.2, 'stroke-linejoin': 'round' }));
    s.addEventListener('mousemove', (e) => {
      const i = Math.round((e.offsetX / s.clientWidth) * (vals.length - 1));
      out.textContent = `${(labels && labels[i]) || i} · ${fmt.n(vals[i], vals[i] % 1 ? 1 : 0)}`;
    });
    s.addEventListener('mouseleave', () => { out.textContent = `max ${fmt.n(mx)} · min ${fmt.n(mn)}`; });
    out.textContent = `max ${fmt.n(mx)} · min ${fmt.n(mn)}`;
    box.append(s, out); return box;
  }
  /** bars(items) — horizontal ranked bars, the honest default for categories. */
  function bars(items, color) {
    const mx = Math.max(...items.map(i => i.v)) || 1;
    return h('div.col', { style: { gap: '9px' } }, items.map((it, n) =>
      h('div', { style: { display: 'grid', gridTemplateColumns: '1fr auto', gap: '4px 10px' } },
        h('span.small', it.k), h('span.small.num.muted', it.f || fmt.n(it.v)),
        h('div.bar', { style: { gridColumn: '1/3' } },
          h('i', { style: { width: (it.v / mx * 100).toFixed(1) + '%', background: color || PAL[n % PAL.length] } })))));
  }
  /** donut(items) — part-to-whole for <=6 slices, with a legend. */
  function donut(items, size = 160) {
    const tot = items.reduce((a, b) => a + b.v, 0) || 1; let off = 0;
    const R = 54, C = 2 * Math.PI * R;
    return h('div.row', { style: { gap: '18px', alignItems: 'center' } },
      svg('svg', { viewBox: '0 0 140 140', width: size, height: size, role: 'img', 'aria-label': 'breakdown' },
        items.map((it, i) => {
          const len = it.v / tot * C, el = svg('circle', {
            cx: 70, cy: 70, r: R, fill: 'none', 'stroke-width': 20, stroke: PAL[i % PAL.length],
            'stroke-dasharray': `${len} ${C - len}`, 'stroke-dashoffset': -off, transform: 'rotate(-90 70 70)',
          }); off += len; return el;
        })),
      h('div.col', { style: { gap: '6px' } }, items.map((it, i) =>
        h('div.row', { style: { gap: '7px' } },
          h('span', { style: { width: '9px', height: '9px', borderRadius: '3px', background: PAL[i % PAL.length] } }),
          h('span.small', it.k), h('span.small.muted.num', ((it.v / tot) * 100).toFixed(0) + '%')))));
  }

  // ---- data grid ----------------------------------------------------------
  /** grid(cols, rows, opts) — the ONE table: sortable headers, live filter,
   *  optional row click. cols: [{k, t, w?, cell?(row), num?}]. */
  function grid(cols, rows, opts = {}) {
    let sort = opts.sort || cols[0].k, dir = opts.dir || 1, q = '';
    const body = h('tbody');
    const head = h('thead', h('tr', cols.map(c => h('th', {
      style: { cursor: 'pointer', width: c.w }, onclick: () => { dir = sort === c.k ? -dir : 1; sort = c.k; draw(); },
    }, c.t, sort === c.k ? (dir > 0 ? ' ▲' : ' ▼') : ''))));
    function draw() {
      const list = rows
        .filter(r => !q || cols.some(c => String(r[c.k] ?? '').toLowerCase().includes(q)))
        .sort((a, b) => (a[sort] > b[sort] ? 1 : a[sort] < b[sort] ? -1 : 0) * dir);
      fill(body, list.length ? list.map(r => h('tr', {
        style: opts.onRow ? { cursor: 'pointer' } : null,
        onclick: opts.onRow ? () => opts.onRow(r) : null,
      }, cols.map(c => h('td' + (c.num ? '.num' : ''), c.cell ? c.cell(r) : String(r[c.k] ?? ''))))
      ) : h('tr', h('td', { colspan: cols.length }, h('div.empty', opts.empty || 'Nothing matches'))));
      opts.onCount && opts.onCount(list.length);
    }
    const search = h('input', {
      placeholder: opts.placeholder || 'Search…', style: { maxWidth: '240px' },
      oninput: e => { q = e.target.value.toLowerCase(); draw(); },
    });
    draw();
    const el = h('div', opts.noSearch ? null :
      h('div.row', { style: { padding: '10px 12px', borderBottom: '1px solid var(--line)' } },
        search, opts.actions || null),
      h('div.scroll-x', h('table', head, body)));
    el.refresh = (next) => { if (next) rows = next; draw(); };
    return el;
  }

  // ---- routing ------------------------------------------------------------
  /** route(map, render) — hash router; map is {'': fn, 'detail/:id': fn}. */
  function route(map) {
    const go = () => {
      const p = location.hash.replace(/^#\/?/, '');
      for (const k in map) {
        const ks = k.split('/'), ps = p ? p.split('/') : [];
        if (ks.length !== ps.length && k !== '*') continue;
        const args = {}; let ok = true;
        ks.forEach((seg, i) => { if (seg[0] === ':') args[seg.slice(1)] = decodeURIComponent(ps[i]); else if (seg !== ps[i]) ok = false; });
        if (ok) return map[k](args);
      }
      map['*'] && map['*']({});
    };
    addEventListener('hashchange', go); go();
    return go;
  }
  /** tabs(names, onPick) — the one segmented control. */
  function tabs(names, onPick, active) {
    const el = h('div.row', { style: { gap: '2px' }, role: 'tablist' });
    const set = (n) => { $$('button', el).forEach(b => b.classList.toggle('p', b.textContent === n)); onPick(n); };
    names.forEach(n => el.append(h('button.sm', { onclick: () => set(n), role: 'tab' }, n)));
    set(active || names[0]); return el;
  }

  // ---- theme --------------------------------------------------------------
  function theme() {
    const r = document.documentElement, k = 'hz:theme';
    const set = (t) => { r.dataset.theme = t; try { localStorage.setItem(k, t); } catch (e) { } };
    try { const s = localStorage.getItem(k); if (s) set(s); } catch (e) { }
    return h('button.g.sm', {
      title: 'Toggle theme', 'aria-label': 'Toggle theme',
      onclick: () => set(r.dataset.theme === 'light' ? 'dark' : 'light'),
    }, '◐');
  }

  g.hz = {
    $, $$, h, esc, frag, fill, clear, store, submit, wire, toast, modal, rng, range, pick,
    uid, avatar, hue, fmt, spark, area, bars, donut, grid, tabs, route, theme, svg, PAL,
  };
})(window);
