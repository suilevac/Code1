/* =============================================================
   render.js — Affichage du texte codé
   ============================================================= */

import { FAMILIES } from './data.js';
import { gestureSvg } from './gestures.js';

const NS = 'http://www.w3.org/2000/svg';

function shapeOverlay(shape) {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'tk__shape');
  svg.setAttribute('viewBox', '0 0 100 100');
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  let el;
  if (shape === 'circle') {
    el = document.createElementNS(NS, 'ellipse');
    el.setAttribute('cx', '50'); el.setAttribute('cy', '50');
    el.setAttribute('rx', '48'); el.setAttribute('ry', '46');
  } else {
    el = document.createElementNS(NS, 'polygon');
    el.setAttribute('points', '4,4 4,96 96,96');
  }
  el.setAttribute('fill', 'none');
  el.setAttribute('stroke', 'currentColor');
  el.setAttribute('stroke-width', '2');
  el.setAttribute('vector-effect', 'non-scaling-stroke');
  svg.appendChild(el);
  return svg;
}

function tokenEl(tk, opts) {
  const span = document.createElement('span');
  span.className = 'tk tk--' + tk.kind;
  if (tk.kind === 'vowel') {
    const fam = FAMILIES[tk.fam];
    if (fam) span.style.setProperty('--c', opts.contrast ? fam.strong : fam.color);
    span.dataset.fam = tk.fam;
    if (tk.shape === 'circle') span.classList.add('tk--circle');
    if (tk.shape === 'tri') span.classList.add('tk--tri');
  }
  if (tk.mark === 'single') span.classList.add('tk--muette');
  if (tk.mark === 'double') span.classList.add('tk--sifflante');
  if (tk.check && opts.check) span.classList.add('tk--verifier');
  if (tk.manual) span.classList.add('tk--manuel');

  if (tk.shape === 'circle' || tk.shape === 'tri') span.appendChild(shapeOverlay(tk.shape));

  if (opts.gestures && tk.kind === 'cons' && tk.gesture) {
    const g = document.createElement('span');
    g.className = 'tk__geste';
    g.innerHTML = gestureSvg(tk.gesture);
    span.appendChild(g);
  }

  const txt = document.createElement('span');
  txt.className = 'tk__t';
  txt.textContent = tk.src;
  span.appendChild(txt);
  return span;
}

export function render(container, lines, opts = {}) {
  container.textContent = '';
  container.classList.toggle('out--mono', !opts.colors);
  container.classList.toggle('out--gestes', !!opts.gestures);
  container.classList.toggle('out--muettes-grises', !!opts.greyMute);

  let wi = 0;
  for (const line of lines) {
    const p = document.createElement('p');
    p.className = 'ligne';
    if (!line.length) p.innerHTML = '&nbsp;';
    for (const item of line) {
      if (item.type === 'raw') {
        p.appendChild(document.createTextNode(item.src));
        continue;
      }
      const w = document.createElement('span');
      w.className = 'mot';
      w.dataset.mot = item.src.toLowerCase();
      w.dataset.w = String(wi++);
      item.tokens.forEach((tk, ti) => {
        const el = tokenEl(tk, opts);
        el.dataset.t = String(ti);
        w.appendChild(el);
      });
      p.appendChild(w);
    }
    container.appendChild(p);
  }
}
