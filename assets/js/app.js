/* =============================================================
   app.js — Interface
   ============================================================= */

import { codeText, makeToken } from './engine.js';
import { nombresEnLettres } from './numbers.js';
import { render } from './render.js';
import { FAMILIES, SOUNDS } from './data.js';

const $ = (s) => document.querySelector(s);
const PREFS = 'aloe.prefs.v1';
const FIXES = 'aloe.corrections.v1';

const EXEMPLE = `Dans la cour de l'école, Léa joue au ballon avec son chien.
Il fait beau : le soleil brille au-dessus des maisons.
Quatre-vingt-dix élèves mangent à la cantine aujourd'hui.
Papa a acheté dix-sept pommes rouges et une tarte au citron.`;

/* ---------- préférences ---------- */
const parDefaut = {
  police: "'Andika', Verdana, sans-serif",
  taille: 34, interligne: 2, espacement: 0.01,
  couleurs: true, contraste: false, gestes: false,
  muettes: true, verifier: true, nombres: false,
  texte: EXEMPLE,
};
let prefs = { ...parDefaut, ...lire(PREFS, {}) };
let fixes = lire(FIXES, {});

function lire(cle, defaut) {
  try { return JSON.parse(localStorage.getItem(cle)) ?? defaut; } catch { return defaut; }
}
function ecrire(cle, valeur) {
  try { localStorage.setItem(cle, JSON.stringify(valeur)); } catch { /* navigation privée */ }
}

/* ---------- rendu ---------- */
let lignes = [];

function options() {
  return {
    colors: prefs.couleurs, contrast: prefs.contraste, gestures: prefs.gestes,
    greyMute: prefs.muettes, check: prefs.verifier,
  };
}

function appliquerCorrections(lines) {
  for (const ligne of lines) {
    for (const item of ligne) {
      if (item.type !== 'word') continue;
      const mot = item.src.toLowerCase();
      item.tokens = item.tokens.map((tk, i) => {
        const cle = fixes[`${mot}#${i}`];
        if (!cle) return tk;
        return makeToken(tk.src, cle === 'noir' ? 'noir' : cle, { manual: true });
      });
    }
  }
}

function majTexte() {
  const brut = prefs.nombres ? nombresEnLettres(prefs.texte) : prefs.texte;
  lignes = codeText(brut);
  appliquerCorrections(lignes);
  const sortie = $('#sortie');
  if (!prefs.texte.trim()) {
    sortie.innerHTML = '<p class="vide">Écrivez un texte à gauche : il s\'affichera ici, codé.</p>';
    return;
  }
  render(sortie, lignes, options());
}

function majStyle() {
  const r = document.documentElement.style;
  r.setProperty('--police-sortie', prefs.police);
  r.setProperty('--taille-sortie', prefs.taille + 'px');
  r.setProperty('--interligne', prefs.interligne);
  r.setProperty('--espace-lettres', prefs.espacement + 'em');
  r.setProperty('--espace-mots', Math.max(0.1, prefs.espacement * 3) + 'em');
}

function majBoutonCorrections() {
  $('#btn-corrections').textContent = `Mes corrections (${Object.keys(fixes).length})`;
}

/* ---------- menu de correction ---------- */
const GROUPES = [
  { titre: 'Son-voyelle', forme: 'rect', cles: ['a', 'o', 'i', 'e2', 'u', 'oi', 'ou', 'e'] },
  { titre: 'Nasale (entourée)', forme: 'rond', cles: ['an', 'en', 'on', 'in', 'ein', 'un', 'oin'] },
  { titre: 'Avec yod (triangle)', forme: 'tri', cles: ['il', 'ian', 'ion', 'ien', 'ay', 'oy', 'uy'] },
];

let cible = null;

function ouvrirMenu(tk) {
  cible = tk;
  const menu = $('#menu');
  const lettres = tk.querySelector('.tk__t').textContent;
  let html = `<h3>« ${lettres} » se lit…</h3>`;
  for (const g of GROUPES) {
    html += `<div class="rangee">`;
    for (const k of g.cles) {
      const fam = FAMILIES[SOUNDS[k].fam];
      html += `<button class="puce puce--${g.forme}" data-cle="${k}" title="${SOUNDS[k].name}">
        <i style="background:${fam.color}"></i>${SOUNDS[k].gr[0]}</button>`;
    }
    html += `</div>`;
  }
  html += `<div class="rangee">
      <button class="puce" data-cle="noir">consonne noire</button>
      <button class="puce" data-cle="_">lettre muette</button>
      <button class="puce" data-cle="s2">fait [s]</button>
      <button class="puce" data-cle="auto">automatique</button>
    </div>`;
  menu.innerHTML = html;
  menu.hidden = false;

  const r = tk.getBoundingClientRect();
  const largeur = menu.offsetWidth;
  const x = Math.min(Math.max(8, r.left + window.scrollX), window.scrollX + window.innerWidth - largeur - 8);
  menu.style.left = x + 'px';
  menu.style.top = (r.bottom + window.scrollY + 8) + 'px';
}

function fermerMenu() { $('#menu').hidden = true; cible = null; }

/* ---------- sérialisation (copier / exporter) ---------- */
function styleEnLigne(tk) {
  const s = [];
  if (tk.kind === 'vowel' && prefs.couleurs) {
    const fam = FAMILIES[tk.fam];
    if (fam) s.push(`color:${prefs.contraste ? fam.strong : fam.color}`);
    if (tk.shape === 'circle') s.push(`border:2px solid currentColor;border-radius:50%;padding:0 4px`);
    if (tk.shape === 'tri') s.push(`border-left:2px solid currentColor;border-bottom:2px solid currentColor;padding:0 3px`);
  } else if (tk.kind === 'vowel') {
    if (tk.shape === 'circle') s.push('border:2px solid #000;border-radius:50%;padding:0 4px');
    if (tk.shape === 'tri') s.push('border-left:2px solid #000;border-bottom:2px solid #000;padding:0 3px');
  }
  if (tk.mark === 'single') {
    s.push('text-decoration:underline');
    if (prefs.muettes) s.push('color:#9aa1ad');
  }
  if (tk.mark === 'double') s.push('border-bottom:3px double currentColor');
  return s.join(';');
}

function enHtml() {
  const esc = (t) => t.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const corps = lignes.map((ligne) => {
    const contenu = ligne.map((item) => {
      if (item.type === 'raw') return esc(item.src);
      return '<span style="white-space:nowrap">' + item.tokens.map((tk) => {
        const st = styleEnLigne(tk);
        return st ? `<span style="${st}">${esc(tk.src)}</span>` : esc(tk.src);
      }).join('') + '</span>';
    }).join('');
    return `<p style="margin:0 0 .25em">${contenu || '&nbsp;'}</p>`;
  }).join('\n');
  return `<div style="font-family:${prefs.police};font-size:${prefs.taille}px;line-height:${prefs.interligne};` +
    `letter-spacing:${prefs.espacement}em">\n${corps}\n</div>`;
}

async function copier() {
  const html = enHtml();
  const texte = prefs.texte;
  try {
    await navigator.clipboard.write([new ClipboardItem({
      'text/html': new Blob([html], { type: 'text/html' }),
      'text/plain': new Blob([texte], { type: 'text/plain' }),
    })]);
    signaler('#btn-copier', 'Copié ✓');
  } catch {
    const zone = document.createElement('div');
    zone.contentEditable = 'true';
    zone.innerHTML = html;
    zone.style.cssText = 'position:fixed;left:-9999px;top:0';
    document.body.appendChild(zone);
    const sel = window.getSelection(); const rg = document.createRange();
    rg.selectNodeContents(zone); sel.removeAllRanges(); sel.addRange(rg);
    document.execCommand('copy');
    sel.removeAllRanges(); zone.remove();
    signaler('#btn-copier', 'Copié ✓');
  }
}

function exporter() {
  const page = `<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Texte codé</title>
<style>body{margin:0;padding:24px;background:#fff;color:#15161a}@page{margin:16mm}</style>
</head><body>
${enHtml()}
</body></html>`;
  const url = URL.createObjectURL(new Blob([page], { type: 'text/html' }));
  const a = document.createElement('a');
  a.href = url; a.download = 'texte-code.html';
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function signaler(sel, texte) {
  const b = $(sel); const avant = b.textContent;
  b.textContent = texte;
  setTimeout(() => { b.textContent = avant; }, 1400);
}

/* ---------- liste des corrections ---------- */
function ouvrirCorrections() {
  const liste = $('#liste-corrections');
  const entrees = Object.entries(fixes);
  if (!entrees.length) liste.innerHTML = '<p style="color:var(--doux)">Aucune correction enregistrée.</p>';
  else liste.innerHTML = entrees.map(([k, v]) => {
    const [mot, i] = k.split('#');
    return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--trait)">
      <strong style="min-width:9em">${mot}</strong>
      <span style="color:var(--doux)">lettre ${Number(i) + 1} → ${v === '_' ? 'muette' : v === 's2' ? 'fait [s]' : v === 'noir' ? 'consonne' : v}</span>
      <button class="bouton" data-suppr="${k}" style="margin-left:auto;padding:3px 9px">Retirer</button>
    </div>`;
  }).join('');
  $('#dlg-corrections').showModal();
}

/* ---------- branchements ---------- */
function brancher() {
  const saisie = $('#saisie');
  saisie.value = prefs.texte;

  $('#police').value = prefs.police;
  $('#taille').value = prefs.taille;
  $('#interligne').value = prefs.interligne;
  $('#espacement').value = prefs.espacement;
  $('#opt-couleurs').checked = prefs.couleurs;
  $('#opt-contraste').checked = prefs.contraste;
  $('#opt-gestes').checked = prefs.gestes;
  $('#opt-muettes').checked = prefs.muettes;
  $('#opt-verifier').checked = prefs.verifier;
  $('#opt-nombres').checked = prefs.nombres;

  let minuteur;
  saisie.addEventListener('input', () => {
    prefs.texte = saisie.value;
    clearTimeout(minuteur);
    minuteur = setTimeout(() => { majTexte(); ecrire(PREFS, prefs); }, 120);
  });

  const lie = (sel, champ, transforme = (v) => v, style = false) => {
    $(sel).addEventListener('input', (e) => {
      prefs[champ] = transforme(e.target.type === 'checkbox' ? e.target.checked : e.target.value);
      ecrire(PREFS, prefs);
      if (style) majStyle(); else majTexte();
    });
  };
  lie('#police', 'police', (v) => v, true);
  lie('#taille', 'taille', Number, true);
  lie('#interligne', 'interligne', Number, true);
  lie('#espacement', 'espacement', Number, true);
  lie('#opt-couleurs', 'couleurs');
  lie('#opt-contraste', 'contraste');
  lie('#opt-gestes', 'gestes');
  lie('#opt-muettes', 'muettes');
  lie('#opt-verifier', 'verifier');
  lie('#opt-nombres', 'nombres');

  $('#btn-exemple').addEventListener('click', () => {
    saisie.value = prefs.texte = EXEMPLE; ecrire(PREFS, prefs); majTexte();
  });
  $('#btn-effacer').addEventListener('click', () => {
    saisie.value = prefs.texte = ''; ecrire(PREFS, prefs); majTexte(); saisie.focus();
  });
  $('#btn-imprimer').addEventListener('click', () => window.print());
  $('#btn-copier').addEventListener('click', copier);
  $('#btn-exporter').addEventListener('click', exporter);

  $('#btn-corrections').addEventListener('click', ouvrirCorrections);
  $('#btn-fermer-corrections').addEventListener('click', () => $('#dlg-corrections').close());
  $('#btn-vider').addEventListener('click', () => {
    fixes = {}; ecrire(FIXES, fixes); majBoutonCorrections(); majTexte(); $('#dlg-corrections').close();
  });
  $('#liste-corrections').addEventListener('click', (e) => {
    const k = e.target.dataset?.suppr;
    if (!k) return;
    delete fixes[k]; ecrire(FIXES, fixes); majBoutonCorrections(); majTexte(); ouvrirCorrections();
  });

  $('#lien-aide').addEventListener('click', (e) => { e.preventDefault(); $('#dlg-aide').showModal(); });
  $('#btn-fermer-aide').addEventListener('click', () => $('#dlg-aide').close());

  $('#sortie').addEventListener('click', (e) => {
    const tk = e.target.closest('.tk');
    if (!tk) { fermerMenu(); return; }
    e.stopPropagation();
    ouvrirMenu(tk);
  });

  $('#menu').addEventListener('click', (e) => {
    const b = e.target.closest('.puce');
    if (!b || !cible) return;
    const mot = cible.closest('.mot').dataset.mot;
    const i = cible.dataset.t;
    const cle = b.dataset.cle;
    if (cle === 'auto') delete fixes[`${mot}#${i}`];
    else fixes[`${mot}#${i}`] = cle;
    ecrire(FIXES, fixes); majBoutonCorrections(); fermerMenu(); majTexte();
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#menu') && !e.target.closest('#sortie')) fermerMenu();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') fermerMenu(); });
}

majStyle();
brancher();
majBoutonCorrections();
majTexte();
