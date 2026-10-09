/* Tests du moteur : node tests/engine.test.mjs */
import { codeWord, codeText } from '../assets/js/engine.js';
import { LEXICON } from '../assets/js/data.js';

const compact = (w) => codeWord(w).map((t) => t.src + ':' + (t.key ?? '·')).join(' ');

const CASES = [
  // voyelles simples et digrammes
  ['chat',      'ch:ch a:a t:_'],
  ['bateau',    'b:b a:a t:t eau:o'],
  ['oiseau',    'oi:oi s:z eau:o'],
  ['beaucoup',  'b:b eau:o c:k ou:ou p:_'],
  ['gâteau',    'g:g â:a t:t eau:o'],
  ['voiture',   'v:v oi:oi t:t u:u r:r e:_'],
  ['heureux',   'h:_ eu:e r:r eu:e x:_'],
  // nasales
  ['grand',     'g:g r:r an:an d:_'],
  ['enfant',    'en:en f:f an:an t:_'],
  ['matin',     'm:m a:a t:t in:in'],
  ['pain',      'p:p ain:ein'],
  ['lundi',     'l:l un:un d:d i:i'],
  ['bonjour',   'b:b on:on j:j ou:ou r:r'],
  ['pointu',    'p:p oin:oin t:t u:u'],
  // pas de nasale : voyelle ou consonne double derrière
  ['ami',       'a:a m:m i:i'],
  ['amour',     'a:a m:m ou:ou r:r'],
  ['année',     'a:a nn:n é:e2 e:_'],
  ['semaine',   's:s e:e m:m ai:e2 n:n e:_'],
  // yod (triangle)
  ['chien',     'ch:ch ien:ien'],
  ['avion',     'a:a v:v ion:ion'],
  ['viande',    'v:v ian:ian d:d e:_'],
  ['famille',   'f:f a:a m:m ill:il e:_'],
  ['travail',   't:t r:r a:a v:v a:a il:il'],
  ['soleil',    's:s o:o l:l e:e2 il:il'],
  ['fauteuil',  'f:f au:o t:t eu:e il:il'],
  ['crayon',    'c:k r:r ay:ay on:on'],
  ['voyage',    'v:v oy:oy a:a g:j e:_'],
  // lettres muettes
  ['petit',     'p:p e:e t:t i:i t:_'],
  ['temps',     't:t em:en p:_ s:_'],
  ['nous',      'n:n ou:ou s:_'],
  ['jouent',    'j:j ou:ou ent:_'],
  ['chanter',   'ch:ch an:an t:t e:e2 r:_'],
  ['chez',      'ch:ch e:e2 z:_'],
  ['paquet',    'p:p a:a qu:k e:e2 t:_'],
  ['pommes',    'p:p o:o mm:m es:_'],
  ['histoire',  'h:_ i:i s:s t:t oi:oi r:r e:_'],
  // [s] signalé par le double trait
  ['nation',    'n:n a:a t:s ion:ion'],
  ['cinq',      'c:s in:in q:k'],
  ['garçon',    'g:g a:a r:r ç:s on:on'],
  ['glace',     'g:g l:l a:a c:s e:_'],
  // c / g durs
  ['avec',      'a:a v:v e:e2 c:k'],
  ['guitare',   'gu:g i:i t:t a:a r:r e:_'],
  ['bague',     'b:b a:a gu:g e:_'],
  // e qui se lit [è]
  ['elle',      'e:e2 ll:l e:_'],
  ['merci',     'm:m e:e2 r:r c:s i:i'],
  ['cheval',    'ch:ch e:e v:v a:a l:l'],
  ['dessin',    'd:d e:e2 ss:s in:in'],
  // lexique
  ['femme',     'f:f e:a mm:m e:_'],
  ['monsieur',  'm:m o:e n:_ s:s i:il eu:e r:_'],
  ['soixante',  's:s oi:oi x:s an:an t:t e:_'],
  ['vingt',     'v:v in:in g:_ t:_'],
  ['sept',      's:s e:e2 p:_ t:t'],
  ['ville',     'v:v i:i ll:l e:_'],
  ['fils',      'f:f i:i l:l s:s'],
];

let ok = 0;
const fails = [];
for (const [word, expected] of CASES) {
  const got = compact(word);
  if (got === expected) ok++;
  else fails.push(`  ${word}\n     attendu : ${expected}\n     obtenu  : ${got}`);
}

// le lexique doit couvrir exactement les lettres de chaque mot
for (const [w, e] of Object.entries(LEXICON)) {
  const n = e.split('|').reduce((a, p) => a + p.split('=')[0].length, 0);
  if (n !== w.length) fails.push(`  lexique « ${w} » : ${n} lettres codées pour ${w.length}`);
  else ok++;
}

// le texte complet ne doit rien perdre
const texte = "L'école est ouverte ; quatre-vingt-dix enfants\njouent dans la cour.";
const reconstruit = codeText(texte)
  .map((l) => l.map((it) => (it.type === 'raw' ? it.src : it.tokens.map((t) => t.src).join(''))).join(''))
  .join('\n');
if (reconstruit !== texte) fails.push(`  texte reconstruit différent :\n     ${reconstruit}`);
else ok++;

console.log(`${ok} vérifications réussies, ${fails.length} échec(s)`);
if (fails.length) { console.log(fails.join('\n')); process.exit(1); }
