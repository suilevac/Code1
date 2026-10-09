/* =============================================================
   build.mjs — Fabrique les versions autonomes du site
     node tools/build.mjs
   Produit :
     dist/lire-en-couleurs.html   un seul fichier, à ouvrir par double-clic
     dist/artefact.html           la même chose pour une publication en ligne
   ============================================================= */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const racine = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const lire = (f) => readFileSync(resolve(racine, f), 'utf8');

/* --- rassemble les modules en un seul script --- */
const MODULES = ['data', 'gestures', 'numbers', 'tableau', 'engine', 'render', 'app'];

function bundle() {
  const vus = new Set();
  const morceaux = MODULES.map((nom) => {
    let code = lire(`assets/js/${nom}.js`)
      .replace(/^\s*import[^;]*;\s*$/gm, '')
      .replace(/^\s*export\s*\{[^}]*\}\s*;\s*$/gm, '')
      .replace(/^export\s+/gm, '');
    for (const m of code.matchAll(/^(?:const|let|function|class)\s+([A-Za-z_$][\w$]*)/gm)) {
      if (vus.has(m[1])) throw new Error(`Nom déclaré deux fois entre modules : ${m[1]} (${nom}.js)`);
      vus.add(m[1]);
    }
    return `/* ---- ${nom}.js ---- */\n${code.trim()}`;
  });
  return morceaux.join('\n\n');
}

/* --- enlève un élément HTML par son id ou sa classe --- */
function enleve(html, motifs) {
  for (const motif of motifs) {
    const re = new RegExp(`\\s*<(\\w+)[^>]*${motif}[^>]*>[\\s\\S]*?</\\1>`, 'g');
    html = html.replace(re, '');
  }
  return html;
}

function construire({ artefact }) {
  const css = lire('assets/css/app.css');
  const js = bundle();
  let html = lire('index.html');

  html = html.replace(
    /<link rel="stylesheet" href="assets\/css\/app\.css">/,
    `<style>\n${css}\n</style>`
  );
  html = html.replace(
    /<script type="module" src="assets\/js\/app\.js"><\/script>/,
    `<script type="module">\n${js}\n</script>`
  );
  // le lien vers tableau.html n'existe pas dans un fichier unique
  html = enleve(html, ['class="bouton horsfichier"']);

  if (!artefact) return html;

  // Version en ligne : pas de doctype ni de <head>, et l'impression
  // n'est pas possible dans une page publiée.
  html = enleve(html, ['id="btn-imprimer"', 'id="btn-exporter"']);
  html = html.replace(
    '<p><strong>Imprimer.</strong>',
    '<p><strong>Imprimer.</strong> Cette version en ligne ne peut pas lancer l\'impression : ' +
    'utilisez <em>Copier</em>, collez dans un document, puis imprimez depuis le document. ' +
    'La version à télécharger, elle, imprime directement.</p><p hidden>'
  );
  const tete = html.slice(html.indexOf('<head>') + 6, html.indexOf('</head>'))
    .replace(/<meta charset[^>]*>/, '')
    .replace(/<meta name="viewport"[^>]*>/, '')
    .replace(/<link rel="icon"[^>]*>/, '')
    .trim();
  const corps = html.slice(html.indexOf('<body>') + 6, html.indexOf('</body>')).trim();
  return `${tete}\n\n${corps}\n`;
}

mkdirSync(resolve(racine, 'dist'), { recursive: true });
writeFileSync(resolve(racine, 'dist/lire-en-couleurs.html'), construire({ artefact: false }));
writeFileSync(resolve(racine, 'dist/artefact.html'), construire({ artefact: true }));
console.log('dist/lire-en-couleurs.html et dist/artefact.html écrits');
