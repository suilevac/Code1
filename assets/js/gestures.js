/* =============================================================
   gestures.js — Les gestes du tableau, dessinés en SVG
   (affichés au-dessus des lettres quand l'option est cochée)
   ============================================================= */

const D = (cx, cy) => `<circle cx="${cx}" cy="${cy}" r="1.7" fill="currentColor" stroke="none"/>`;

export const GESTURES = {
  s:  '<path d="M4 12h16"/><path d="M4 20h16"/>',
  t:  '<path d="M12 4v24"/>',
  ch: '<path d="M8 4v22h11"/>',
  z:  '<path d="M6 8h12L6 24h12"/>',
  l:  '<path d="M12 28V5"/><path d="M7 10l5-5 5 5"/>',
  p:  '<path d="M4 16h16"/>',
  b:  '<circle cx="12" cy="16" r="5"/><path d="M3 16h18"/>',
  m:  `<path d="M6 16h12"/>${D(5, 16)}${D(12, 16)}${D(19, 16)}`,
  k:  '<path d="M7 7v8a5 5 0 0 0 10 0V7"/>',
  v:  '<path d="M7 8l5 16 5-16"/>',
  f:  '<path d="M9 6v20"/><path d="M15 6v20"/>',
  d:  '<circle cx="10" cy="20" r="5"/><path d="M15 5v20"/>',
  n:  `<path d="M12 7v19"/>${D(6, 16)}${D(18, 16)}`,
  r:  '<path d="M3 23c-1-7 6-7 5 0"/><path d="M8 23c-1-7 6-7 5 0"/><path d="M13 23c-1-7 6-7 5 0"/>',
  j:  '<path d="M17 5v13a5 5 0 0 1-10 0"/>',
  g:  '<circle cx="12" cy="16" r="7"/>',
  gn: `<path d="M13 5v13a5 5 0 0 1-9 3"/>${D(16, 11)}${D(20, 11)}`,
};

/* Le geste d'une voyelle, c'est sa forme coloriée */
export function shapeSvg(shape, color, filled = true) {
  const f = filled ? color : 'none';
  if (shape === 'circle') return svg(`<circle cx="12" cy="16" r="10" fill="${f}" stroke="${color}" stroke-width="2"/>`);
  if (shape === 'tri') return svg(`<path d="M4 6v20h16z" fill="${f}" stroke="${color}" stroke-width="2"/>`);
  return svg(`<rect x="4" y="5" width="16" height="22" fill="${f}" stroke="${color}" stroke-width="2"/>`);
}

export function gestureSvg(key) {
  const d = GESTURES[key];
  return d ? svg(d) : '';
}

function svg(inner) {
  return `<svg class="gst" viewBox="0 0 24 32" aria-hidden="true" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}
