/* =============================================================
   data.js — Les données du code de lecture (méthode Aloé)
   Relevé sur l'affichage de classe : une couleur par son-voyelle,
   consonnes en noir, nasales entourées, sons avec yod en triangle.
   ============================================================= */

/* --- Les 8 familles de couleur (une par son-voyelle de base) --- */
export const FAMILIES = {
  a:  { label: 'a',  color: '#D1282E', strong: '#A3161B' },
  o:  { label: 'o',  color: '#1878B4', strong: '#0E5887' },
  i:  { label: 'i',  color: '#D9BE00', strong: '#9C8800' },
  e2: { label: 'é',  color: '#1E9D4F', strong: '#136E36' },
  u:  { label: 'u',  color: '#C1884B', strong: '#8C5C2A' },
  oi: { label: 'oi', color: '#4C3D93', strong: '#322665' },
  ou: { label: 'ou', color: '#E0A116', strong: '#A37200' },
  e:  { label: 'e',  color: '#D45C96', strong: '#A32F68' },
};

/* --- Les sons-voyelles -------------------------------------
   fam   : famille de couleur
   shape : 'rect' (son simple) | 'circle' (nasale) | 'tri' (yod)
   gr    : graphies du tableau de classe
   ----------------------------------------------------------- */
export const SOUNDS = {
  a:   { fam: 'a',  shape: 'rect',   name: '[a]',   gr: ['a', 'à', 'â'] },
  o:   { fam: 'o',  shape: 'rect',   name: '[o]',   gr: ['o', 'ô', 'au', 'eau'] },
  i:   { fam: 'i',  shape: 'rect',   name: '[i]',   gr: ['i', 'î', 'ï', 'y'] },
  e2:  { fam: 'e2', shape: 'rect',   name: '[é] [è]', gr: ['é', 'è', 'ê', 'ei', 'ai'] },
  u:   { fam: 'u',  shape: 'rect',   name: '[u]',   gr: ['u', 'û'] },
  oi:  { fam: 'oi', shape: 'rect',   name: '[oi]',  gr: ['oi'] },
  ou:  { fam: 'ou', shape: 'rect',   name: '[ou]',  gr: ['ou', 'où', 'oû'] },
  e:   { fam: 'e',  shape: 'rect',   name: '[e] [eu]', gr: ['e', 'eu', 'œu', 'oeu'] },

  an:  { fam: 'a',  shape: 'circle', name: '[an]',  gr: ['an', 'am'] },
  en:  { fam: 'e',  shape: 'circle', name: '[an] (en)', gr: ['en', 'em'] },
  on:  { fam: 'o',  shape: 'circle', name: '[on]',  gr: ['on', 'om'] },
  in:  { fam: 'i',  shape: 'circle', name: '[in]',  gr: ['in', 'im'] },
  ein: { fam: 'e2', shape: 'circle', name: '[in] (ein)', gr: ['ein', 'ain', 'aim'] },
  un:  { fam: 'u',  shape: 'circle', name: '[un]',  gr: ['un', 'um'] },
  oin: { fam: 'oi', shape: 'circle', name: '[oin]', gr: ['oin'], extra: true },

  il:  { fam: 'i',  shape: 'tri',    name: '[ill]', gr: ['il', 'ill', 'y'] },
  ian: { fam: 'a',  shape: 'tri',    name: '[ian]', gr: ['ian'] },
  ion: { fam: 'o',  shape: 'tri',    name: '[ion]', gr: ['ion'] },
  ien: { fam: 'e2', shape: 'tri',    name: '[ien]', gr: ['ien'] },
  ay:  { fam: 'e2', shape: 'tri',    name: '[ay]',  gr: ['ay', 'ey'], extra: true },
  oy:  { fam: 'oi', shape: 'tri',    name: '[oy]',  gr: ['oy'], extra: true },
  uy:  { fam: 'u',  shape: 'tri',    name: '[uy]',  gr: ['uy'], extra: true },
};

/* --- Les consonnes (noires) + leur geste --------------------
   g  : clé du geste dessiné dans gestures.js
   gr : graphies du tableau de classe
   ----------------------------------------------------------- */
export const CONSONANTS = {
  s:  { name: '[s]',  g: 's',  gr: ['s', 'ss', 'c', 'ce', 'ç'] },
  t:  { name: '[t]',  g: 't',  gr: ['t', 'tt'] },
  ch: { name: '[ch]', g: 'ch', gr: ['ch'] },
  z:  { name: '[z]',  g: 'z',  gr: ['z', 's'] },
  l:  { name: '[l]',  g: 'l',  gr: ['l', 'll'] },
  p:  { name: '[p]',  g: 'p',  gr: ['p', 'pp'] },
  b:  { name: '[b]',  g: 'b',  gr: ['b'] },
  m:  { name: '[m]',  g: 'm',  gr: ['m', 'mm'] },
  k:  { name: '[k]',  g: 'k',  gr: ['c', 'qu', 'k'] },
  v:  { name: '[v]',  g: 'v',  gr: ['v'] },
  f:  { name: '[f]',  g: 'f',  gr: ['f', 'ff', 'ph'] },
  d:  { name: '[d]',  g: 'd',  gr: ['d'] },
  n:  { name: '[n]',  g: 'n',  gr: ['n', 'nn'] },
  r:  { name: '[r]',  g: 'r',  gr: ['r', 'rr'] },
  j:  { name: '[j]',  g: 'j',  gr: ['j', 'ge'] },
  g:  { name: '[g]',  g: 'g',  gr: ['g', 'gu'] },
  gn: { name: '[gn]', g: 'gn', gr: ['gn'] },
  ks: { name: '[ks]', g: null, gr: ['x'] },
};

/* --- Les attaques du bas du tableau (consonne + l / r) ------ */
export const BLENDS = ['pl', 'pr', 'tr', 'dr', 'cr', 'cl', 'fr', 'fl', 'vr', 'br', 'bl', 'gr', 'gl'];

/* --- Mots dont le code ne se déduit pas des règles -----------
   Format : groupes séparés par « | ».
   Un groupe = les lettres, puis « = » et la clé du son.
   Sans « = », le son est déduit de la graphie.
   Clés spéciales :  _  lettre muette
                     s2 lettre qui fait [s] (double trait)
                     z  lettre qui fait [z]
   ----------------------------------------------------------- */
export const LEXICON = {
  // nombres et mots de la numération
  'six':      's|i|x=s2',
  'dix':      'd|i|x=s2',
  'soixante': 's|oi|x=s2|an|t|e=_',
  'sept':     's|e=e2|p=_|t',
  'huit':     'h=_|u|i|t',
  'neuf':     'n|eu|f',
  'cinq':     'c=s2|in|q=k',
  'vingt':    'v|in|g=_|t=_',
  'vingts':   'v|in|g=_|t=_|s=_',
  'cent':     'c=s2|en|t=_',
  'cents':    'c=s2|en|t=_|s=_',
  'mille':    'm|i|ll|e=_',
  'onze':     'on|z|e=_',
  'cents':    'c=s2|en|t=_|s=_',

  // mots outils irréguliers
  'est':      'e=e2|s=_|t=_',
  'es':       'e=e2|s=_',
  'et':       'e=e2|t=_',
  'les':      'l|e=e2|s=_',
  'des':      'd|e=e2|s=_',
  'mes':      'm|e=e2|s=_',
  'tes':      't|e=e2|s=_',
  'ses':      's|e=e2|s=_',
  'ces':      'c=s2|e=e2|s=_',
  'ils':      'i|l|s=_',
  'elles':    'e=e2|ll|e=_|s=_',
  'fils':     'f|i|l|s',
  'eu':       'e=_|u',
  'eue':      'e=_|u|e=_',
  'eut':      'e=_|u|t=_',
  'plus':     'p|l|u|s',
  'tous':     't|ou|s=_',
  'bus':      'b|u|s',
  'ours':     'ou|r|s',
  'mars':     'm|a|r|s',
  'sens':     's|en|s',
  'os':       'o|s',
  'sud':      's|u|d',
  'but':      'b|u|t',
  'net':      'n|e=e2|t',
  'ouest':    'ou|e=e2|s|t',
  'août':     'a=_|oû=ou|t',
  'hier':     'h=_|i=il|e=e2|r',
  'monsieur': 'm|o=e|n=_|s|i=il|eu|r=_',
  'messieurs':'m|e=e2|ss|i=il|eu|r=_|s=_',
  'femme':    'f|e=a|mm|e=_',
  'femmes':   'f|e=a|mm|e=_|s=_',
  'oignon':   'o|i=_|gn|on',
  'oignons':  'o|i=_|gn|on|s=_',
  'automne':  'au|t|o|m=_|n|e=_',
  'second':   's|e=e2|c=g|on|d=_',
  'seconde':  's|e=e2|c=g|on|d|e=_',
  'examen':   'e=e2|x|a|m|en',
  'yeux':     'y=il|eu|x=_',
  'oeil':     'oe=e|il',
  'œil':      'œ=e|il',
  'paon':     'p|aon=an',
  'faon':     'f|aon=an',
  'pays':     'p|ay=e2|s=_',
  'ville':    'v|i|ll|e=_',
  'villes':   'v|i|ll|e=_|s=_',
  'village':  'v|i|ll|a|g=j|e=_',
  'villages': 'v|i|ll|a|g=j|e=_|s=_',
  'tranquille':'t|r|an|qu|i|ll|e=_',
  'chorale':  'ch=k|o|r|a|l|e=_',
  'écho':     'é|ch=k|o',
  'chœur':    'ch=k|œu=e|r',
  'orchestre':'o|r|ch=k|e=e2|s|t|r|e=_',
  'technique':'t|e=e2|ch=k|n|i|qu|e=_',
  'aujourd\'hui': "au|j|ou|r|d|'|h=_|u=_|i",
  'gentil':   'j=j|en|t|i|l=_',
  'outil':    'ou|t|i|l=_',
  'fusil':    'f|u|s=z|i|l=_',
  'blanc':    'b|l|an|c=_',
  'blancs':   'b|l|an|c=_|s=_',
  'banc':     'b|an|c=_',
  'franc':    'f|r|an|c=_',
  'tabac':    't|a|b|a|c=_',
  'estomac':  'e=e2|s|t|o|m|a|c=_',
  'nez':      'n|e=e2|z=_',
  'clef':     'c=k|l|e=e2|f=_',
  'faisait':  'f|ai=e|s=z|ai=e2|t=_',
  'faisons':  'f|ai=e|s=z|on|s=_',
  'monsieur': 'm|o=e|n=_|s|i=il|eu|r=_',

  // verbes fréquents en -ent (terminaison muette après consonne)
  'aiment':   'ai=e2|m|ent=_',
  'arrivent': 'a|rr|i|v|ent=_',
  'cherchent':'ch|e=e2|r|ch|ent=_',
  'chantent': 'ch|an|t|ent=_',
  'courent':  'c=k|ou|r|ent=_',
  'disent':   'd|i|s=z|ent=_',
  'donnent':  'd|o|nn|ent=_',
  'dorment':  'd|o|r|m|ent=_',
  'écoutent': 'é|c=k|ou|t|ent=_',
  'entendent':'en|t|en|d|ent=_',
  'habitent': 'h=_|a|b|i|t|ent=_',
  'lisent':   'l|i|s=z|ent=_',
  'marchent': 'm|a|r|ch|ent=_',
  'mangent':  'm|an|g=j|ent=_',
  'parlent':  'p|a|r|l|ent=_',
  'partent':  'p|a|r|t|ent=_',
  'passent':  'p|a|ss|ent=_',
  'pensent':  'p|en|s|ent=_',
  'portent':  'p|o|r|t|ent=_',
  'prennent': 'p|r|e=e2|nn|ent=_',
  'regardent':'r|e|g|a|r|d|ent=_',
  'restent':  'r|e=e2|s|t|ent=_',
  'sortent':  's|o|r|t|ent=_',
  'tombent':  't|on=on|b|ent=_',
  'trouvent': 't|r|ou|v|ent=_',
  'veulent':  'v|eu|l|ent=_',
  'viennent': 'v|i=il|e=e2|nn|ent=_',
  'vivent':   'v|i|v|ent=_',
  'voient':   'v|oi|ent=_',
};

/* --- Mots où la consonne finale se prononce ----------------- */
export const FINAL_SOUNDED = new Set([
  'fils', 'bus', 'ours', 'mars', 'sens', 'os', 'sud', 'but', 'net', 'ouest',
  'est', 'sept', 'huit', 'août', 'plus', 'tennis', 'autobus', 'cactus', 'virus',
  'bus', 'index', 'sac', 'avec', 'lac', 'bec', 'chef', 'actif', 'neuf', 'oeuf',
]);

/* --- Petits mots où le « e » final se prononce -------------- */
export const KEEP_FINAL_E = new Set(['le', 'je', 'me', 'te', 'se', 'ce', 'de', 'ne', 'que']);

/* --- Mots en -er où le r se prononce ------------------------ */
export const ER_SOUNDED = new Set([
  'hier', 'mer', 'fer', 'ver', 'cher', 'fier', 'hiver', 'amer', 'enfer',
  'cuiller', 'super', 'aster', 'ter', 'per', 'over',
]);
