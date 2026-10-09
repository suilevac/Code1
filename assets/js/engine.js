/* =============================================================
   engine.js — Découpage d'un texte en graphèmes codés
   Chaque graphème reçoit :
     kind  : 'vowel' | 'cons' | 'mute' | 'other'
     key   : la clé du son (voir data.js)
     fam   : famille de couleur (voyelles)
     shape : 'rect' | 'circle' | 'tri'  (voyelles)
     mark  : 'none' | 'single' (muette) | 'double' (fait [s])
   ============================================================= */

import { SOUNDS, CONSONANTS, LEXICON, FINAL_SOUNDED, KEEP_FINAL_E, ER_SOUNDED } from './data.js';

const VOWEL_LETTERS = 'aeiouyàâäéèêëîïôöûüùœ';
const LETTER_RE = /[a-zàâäéèêëîïôöûüùçœA-ZÀÂÄÉÈÊËÎÏÔÖÛÜÙÇŒ]/;

const isVowel = (ch) => !!ch && VOWEL_LETTERS.includes(ch);
const isLetter = (ch) => !!ch && LETTER_RE.test(ch);
const isCons = (ch) => isLetter(ch) && !isVowel(ch);

/* ---------- conditions utilisées par les règles ---------- */

// une nasale n'en est une que si le n/m n'est ni doublé ni suivi d'une voyelle
const nasal = (c) => {
  const next = c.next;
  if (!next) return true;
  if (isVowel(next)) return false;
  if (next === c.w[c.i + c.len - 1]) return false; // ann..., omm...
  return true;
};
const consBefore   = (c) => isCons(c.prev);
const beforeVowel  = (c) => isVowel(c.next);
const beforeEIY    = (c) => !!c.next && 'eiyéèêë'.includes(c.next);
const beforeAOU    = (c) => !!c.next && 'aouâôû'.includes(c.next);
const between      = (c) => isVowel(c.prev) && isVowel(c.next);
const yodEnd       = (c) => isVowel(c.prev) && (!c.next || c.next === 's');
const yodY         = (c) => (isVowel(c.prev) && isVowel(c.next)) || (c.i === 0 && isVowel(c.next));
const tiSound      = (c) => c.prev !== 's' &&
  (c.w.slice(c.i + 1, c.i + 4) === 'ion' || /^ie(nt|l|ux)/.test(c.w.slice(c.i + 1)));
// « ai », « ei » ne prennent pas le i d'un -ail / -eil final (travail, soleil)
const notYodIl     = (c) => !(c.next === 'l' && !isLetter(c.w[c.i + c.len + 1]));

// « e » qui se lit [è] : devant une consonne double, un groupe de consonnes,
// ou une consonne finale prononcée  (elle, merci, sec, cette)
const eGrave = (c) => {
  const n1 = c.next, n2 = c.w[c.i + 2];
  if (!isCons(n1)) return false;
  if (c.mute.has(c.i + 1)) return false;
  if (!n2) return true;                      // sec, bec
  if (isCons(n2) && !c.mute.has(c.i + 2)) return true;  // elle, merci, espace
  if (c.lastSounded(c.i + 1)) return true;   // ...er prononcé
  return false;
};

/* ---------- la table des règles, dans l'ordre ---------- */
const R = (p, key, cond) => ({ p, key, cond });

const RULES = [
  // sons avec yod (triangle)
  R('ill', 'il'),
  R('il', 'il', yodEnd),
  R('ay', 'ay', beforeVowel),
  R('ey', 'ay', beforeVowel),
  R('oy', 'oy', beforeVowel),
  R('uy', 'uy', beforeVowel),
  R('ian', 'ian', (c) => consBefore(c) && nasal(c)),
  R('ien', 'ien', (c) => consBefore(c) && nasal(c)),
  R('ion', 'ion', (c) => consBefore(c) && nasal(c)),

  // nasales (rond)
  R('aim', 'ein', nasal), R('ain', 'ein', nasal),
  R('eim', 'ein', nasal), R('ein', 'ein', nasal),
  R('oin', 'oin', nasal),
  R('aon', 'an', nasal),
  R('yn', 'in', nasal), R('ym', 'in', nasal),
  R('an', 'an', nasal), R('am', 'an', nasal),
  R('en', 'en', nasal), R('em', 'en', nasal),
  R('on', 'on', nasal), R('om', 'on', nasal),
  R('in', 'in', nasal), R('im', 'in', nasal),
  R('un', 'un', nasal), R('um', 'un', nasal),

  // voyelles à plusieurs lettres
  R('eau', 'o'), R('au', 'o'),
  R('œu', 'e'), R('oeu', 'e'), R('œ', 'e'), R('eu', 'e'),
  R('ou', 'ou'), R('où', 'ou'), R('oû', 'ou'),
  R('oi', 'oi'), R('oî', 'oi'), R('oy', 'oi'),
  R('ai', 'e2', notYodIl), R('aî', 'e2'), R('ei', 'e2', notYodIl),

  // consonnes à plusieurs lettres
  R('ch', 'ch'), R('ph', 'f'), R('gn', 'gn'), R('th', 't'),
  R('qu', 'k'), R('gu', 'g', beforeEIY), R('ge', 'j', beforeAOU),
  R('sc', 's2', beforeEIY),
  R('ss', 's'), R('ll', 'l'), R('tt', 't'), R('mm', 'm'), R('nn', 'n'),
  R('rr', 'r'), R('pp', 'p'), R('ff', 'f'), R('cc', 'k'), R('dd', 'd'),
  R('bb', 'b'), R('gg', 'g'), R('zz', 'z'),

  // voyelles simples
  R('é', 'e2'), R('è', 'e2'), R('ê', 'e2'), R('ë', 'e2'),
  R('à', 'a'), R('â', 'a'), R('a', 'a'),
  R('ô', 'o'), R('o', 'o'),
  R('î', 'i'), R('ï', 'i'), R('i', 'i'),
  R('û', 'u'), R('ù', 'u'), R('u', 'u'),
  R('y', 'il', yodY), R('y', 'i'),
  R('e', 'e2', (c) => c.next === 'i' && c.w[c.i + 2] === 'l'),  // soleil, abeille
  R('e', 'e2', eGrave), R('e', 'e'),

  // consonnes simples
  R('ç', 's2'), R('c', 's2', beforeEIY), R('c', 'k'),
  R('g', 'j', beforeEIY), R('g', 'g'),
  R('s', 'z', between), R('s', 's'),
  R('t', 's2', tiSound), R('t', 't'),
  R('x', 'ks'), R('h', '_'),
  R('b', 'b'), R('d', 'd'), R('f', 'f'), R('j', 'j'), R('k', 'k'),
  R('l', 'l'), R('m', 'm'), R('n', 'n'), R('p', 'p'), R('q', 'k'),
  R('r', 'r'), R('v', 'v'), R('w', 'v'), R('z', 'z'),
];

/* clé par défaut d'une graphie (sert au lexique) */
const DEFAULT_KEY = {};
for (const r of RULES) if (!r.cond && !(r.p in DEFAULT_KEY)) DEFAULT_KEY[r.p] = r.key;
for (const r of RULES) if (!(r.p in DEFAULT_KEY)) DEFAULT_KEY[r.p] = r.key;

/* ---------- fabrication d'un jeton ---------- */
export function makeToken(src, key, extra = {}) {
  const t = { src, key, kind: 'other', fam: null, shape: null, mark: 'none', gesture: null, ...extra };
  if (key === '_') {
    t.kind = 'mute'; t.mark = 'single';
  } else if (key === 'noir') {
    t.kind = 'cons';
  } else if (key === 's2') {
    t.kind = 'cons'; t.key = 's'; t.mark = 'double'; t.gesture = 's';
  } else if (SOUNDS[key]) {
    t.kind = 'vowel'; t.fam = SOUNDS[key].fam; t.shape = SOUNDS[key].shape;
  } else if (CONSONANTS[key]) {
    t.kind = 'cons'; t.gesture = CONSONANTS[key].g;
  }
  return t;
}

/* ---------- lettres finales muettes et terminaisons ---------- */
const SILENT_FINALS = 'stdxzpg';

function endingPass(w) {
  const forced = {};                 // index -> { len, key }
  const mute = new Set();            // index des lettres muettes
  const n = w.length;
  const put = (i, len, key) => {
    forced[i] = { len, key };
    if (key === '_') for (let k = i; k < i + len; k++) mute.add(k);
  };
  if (n === 0) return { forced, mute };

  // ils jouent, ils créent : -ent muet après une voyelle
  if (n >= 4 && w.endsWith('ent') && isVowel(w[n - 4])) {
    put(n - 3, 3, '_');
    return { forced, mute };
  }
  // chanter, nager : -er = [é] + r muet
  if (n >= 3 && w.endsWith('er') && !ER_SOUNDED.has(w)) {
    put(n - 2, 1, 'e2'); put(n - 1, 1, '_');
    return { forced, mute };
  }
  // chez, nez : -ez = [é] + z muet
  if (n >= 3 && w.endsWith('ez')) {
    put(n - 2, 1, 'e2'); put(n - 1, 1, '_');
    return { forced, mute };
  }
  // paquet, et : -et final = [é] + t muet
  if (n >= 2 && w.endsWith('et') && !FINAL_SOUNDED.has(w)) {
    put(n - 2, 1, 'e2'); put(n - 1, 1, '_');
    return { forced, mute };
  }
  // pommes : -es final = deux lettres muettes
  if (n >= 3 && w.endsWith('es')) {
    put(n - 2, 2, '_');
    return { forced, mute };
  }
  // jaune : e final muet
  if (n >= 2 && w.endsWith('e') && !KEEP_FINAL_E.has(w)) {
    put(n - 1, 1, '_');
    return { forced, mute };
  }
  // petit, grand, temps : consonnes finales muettes
  if (!FINAL_SOUNDED.has(w)) {
    let i = n - 1;
    while (i > 0 && SILENT_FINALS.includes(w[i]) && isLetter(w[i - 1])) {
      // on garde au moins une lettre prononcée dans le mot
      if (i === 0) break;
      put(i, 1, '_');
      i--;
    }
  }
  return { forced, mute };
}

/* ---------- lecture du lexique ---------- */
function fromLexicon(entry, original) {
  const tokens = [];
  let pos = 0;
  for (const part of entry.split('|')) {
    const [letters, key] = part.split('=');
    const src = original.substr(pos, letters.length);
    pos += letters.length;
    tokens.push(makeToken(src, key || DEFAULT_KEY[letters] || letters, { fromLexicon: true }));
  }
  return tokens;
}

/* ---------- découpage d'un mot ---------- */
export function codeWord(word) {
  const lower = word.toLowerCase();
  if (LEXICON[lower]) return fromLexicon(LEXICON[lower], word);

  const { forced, mute } = endingPass(lower);
  const lastSounded = (j) => {
    for (let k = j + 1; k < lower.length; k++) if (!mute.has(k)) return false;
    return true;
  };

  const tokens = [];
  let i = 0;
  while (i < lower.length) {
    if (forced[i]) {
      const f = forced[i];
      tokens.push(makeToken(word.substr(i, f.len), f.key));
      i += f.len;
      continue;
    }
    let hit = null;
    for (const r of RULES) {
      if (!lower.startsWith(r.p, i)) continue;
      const end = i + r.p.length;
      if (mute.has(end - 1) || mute.has(i)) continue;   // ne pas manger une finale muette
      const ctx = { w: lower, i, len: r.p.length, prev: lower[i - 1], next: lower[end], mute, lastSounded };
      if (r.cond && !r.cond(ctx)) continue;
      hit = { len: r.p.length, key: r.key };
      break;
    }
    if (!hit) hit = { len: 1, key: null };
    const tk = makeToken(word.substr(i, hit.len), hit.key);
    // mots à vérifier : -ent après consonne, ill
    if (hit.key === 'il' && lower.startsWith('ill', i)) tk.check = true;
    tokens.push(tk);
    i += hit.len;
  }
  // « -ent » gardé en nasale après une consonne : c'est peut-être un verbe
  if (lower.endsWith('ent') && lower.length >= 4 && isCons(lower[lower.length - 4])) {
    const last = tokens[tokens.length - 1];
    if (last && last.key === 't') {
      const nas = tokens[tokens.length - 2];
      if (nas && nas.key === 'en') nas.check = true;
    }
  }
  return tokens;
}

/* ---------- découpage d'un texte ---------- */
const WORD_RE = /[a-zàâäéèêëîïôöûüùçœA-ZÀÂÄÉÈÊËÎÏÔÖÛÜÙÇŒ]+(?:['’\-][a-zàâäéèêëîïôöûüùçœA-ZÀÂÄÉÈÊËÎÏÔÖÛÜÙÇŒ]+)*/g;

export function codeText(text) {
  const lines = String(text).split('\n');
  return lines.map((line) => {
    const items = [];
    let last = 0;
    for (const m of line.matchAll(WORD_RE)) {
      if (m.index > last) items.push({ type: 'raw', src: line.slice(last, m.index) });
      items.push(codeComposite(m[0]));
      last = m.index + m[0].length;
    }
    if (last < line.length) items.push({ type: 'raw', src: line.slice(last) });
    return items;
  });
}

/* un « mot » peut contenir une apostrophe ou un trait d'union :
   chaque morceau est analysé séparément (l'arbre, quatre-vingt-dix) */
function codeComposite(word) {
  const lower = word.toLowerCase();
  if (LEXICON[lower]) return { type: 'word', src: word, tokens: fromLexicon(LEXICON[lower], word) };
  const tokens = [];
  let buf = '';
  const flush = () => { if (buf) { tokens.push(...codeWord(buf)); buf = ''; } };
  for (const ch of word) {
    if (ch === "'" || ch === '’' || ch === '-') {
      flush();
      tokens.push(makeToken(ch, null, { kind: 'other' }));
    } else buf += ch;
  }
  flush();
  return { type: 'word', src: word, tokens };
}

export { isVowel, isCons };
