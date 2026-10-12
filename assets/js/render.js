/* =============================================================
   render.js — Affichage du texte codé

   Une lettre muette n'est pas codée à part : elle appartient au son
   qui la précède. Elle est donc dans la même unité (même couleur,
   à l'intérieur du rond ou du triangle), avec son trait simple.
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

/* Rassemble chaque lettre muette avec le son qui la précède. */
export function grouper(tokens) {
  const groupes = [];
  tokens.forEach((tk, i) => {
    const dernier = groupes[groupes.length - 1];
    const porteur = dernier && (dernier.tete.kind === 'vowel' || dernier.tete.kind === 'cons');
    if (tk.kind === 'mute' && porteur) dernier.suite.push({ tk, i });
    else groupes.push({ tete: tk, i, suite: [] });
  });
  return groupes;
}

function lettreEl(tk, i, opts) {
  const span = document.createElement('span');
  span.className = 'tk tk--' + tk.kind;
  span.dataset.t = String(i);
  if (tk.mark === 'single') span.classList.add('tk--muette');
  if (tk.mark === 'double') span.classList.add('tk--sifflante');
  if (tk.check && opts.check) span.classList.add('tk--verifier');
  if (tk.manual) span.classList.add('tk--manuel');

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

function uniteEl(groupe, opts) {
  const { tete } = groupe;
  const unite = document.createElement('span');
  unite.className = 'unite unite--' + tete.kind;
  if (tete.kind === 'vowel') {
    const fam = FAMILIES[tete.fam];
    if (fam) unite.style.setProperty('--c', opts.contrast ? fam.strong : fam.color);
    unite.dataset.fam = tete.fam;
    if (tete.shape === 'circle') unite.classList.add('unite--circle');
    if (tete.shape === 'tri') unite.classList.add('unite--tri');
    if (tete.shape === 'circle' || tete.shape === 'tri') unite.appendChild(shapeOverlay(tete.shape));
  }
  unite.appendChild(lettreEl(tete, groupe.i, opts));
  for (const m of groupe.suite) unite.appendChild(lettreEl(m.tk, m.i, opts));
  return unite;
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
      for (const groupe of grouper(item.tokens)) w.appendChild(uniteEl(groupe, opts));
      p.appendChild(w);
    }
    container.appendChild(p);
  }
}
