/* =============================================================
   tableau.js — Construit le tableau des codes à partir des données
   (utilisé par la page tableau.html et par la fenêtre du site)
   ============================================================= */

import { SOUNDS, CONSONANTS, FAMILIES, BLENDS } from './data.js';
import { shapeSvg, gestureSvg } from './gestures.js';

const section = (titre, note, cases) => `
  <h2>${titre}</h2>
  ${note ? `<p class="note">${note}</p>` : ''}
  <div class="grille">${cases}</div>`;

const caseVoyelle = (cle) => {
  const s = SOUNDS[cle];
  const c = FAMILIES[s.fam].color;
  return `<div class="case">
    <div class="forme">${shapeSvg(s.shape, c, true)}</div>
    <div class="graphies" style="color:${c}">${s.gr.join('<br>')}</div>
    <div class="nom">${s.name}${s.extra ? ' *' : ''}</div>
  </div>`;
};

const caseConsonne = (cle) => {
  const k = CONSONANTS[cle];
  return `<div class="case case--cons">
    <div class="forme">${k.g ? gestureSvg(k.g) : ''}</div>
    <div class="graphies">${k.gr.join('<br>')}</div>
    <div class="nom">${k.name}</div>
  </div>`;
};

const par = (f) => (l) => l.map(f).join('');

export function buildTableau() {
  return section('Les sons-voyelles', 'Une couleur par son. Le rectangle est la forme du son simple.',
      par(caseVoyelle)(['a', 'o', 'i', 'e2', 'u', 'oi', 'ou', 'e'])) +
    section('Les sons nasaux', 'Entourés d\'un rond, dans la couleur de leur voyelle.',
      par(caseVoyelle)(['an', 'en', 'on', 'in', 'ein', 'un', 'oin'])) +
    section('Les sons avec yod', 'Dans un triangle, dans la couleur de leur voyelle.',
      par(caseVoyelle)(['il', 'ian', 'ion', 'ien', 'ay', 'oy', 'uy'])) +
    section('Les consonnes', 'Elles restent noires. Le dessin est le geste du tableau de classe.',
      par(caseConsonne)(Object.keys(CONSONANTS))) +
    section('Les attaques', 'Consonne + l ou r : les deux gestes s\'enchaînent.',
      BLENDS.map((b) => `<div class="case case--cons"><div class="graphies">${b}</div></div>`).join('')) +
    `<h2>Les traits</h2>
     <p class="note">
       <strong>Trait simple</strong> sous une lettre : elle ne se dit pas
       (le <em>p</em> de sept, le <em>s</em> de quatre-vingts).<br>
       <strong>Double trait</strong> : la lettre fait le son [s] (cinq, six, dix, soixante, cent).<br>
       <em>* Les cases marquées d'une étoile ne sont pas sur l'affichage de la classe :
       elles ont été ajoutées pour que le site sache coder tous les mots (oin, ay, oy, uy).</em>
     </p>`;
}
