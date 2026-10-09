/* =============================================================
   numbers.js — Écrire un nombre en lettres (numération de classe)
   ============================================================= */

const U = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf',
  'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize',
  'dix-sept', 'dix-huit', 'dix-neuf'];
const T = ['', '', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 'soixante', 'quatre-vingt', 'quatre-vingt'];

function sousCent(n) {
  if (n < 20) return U[n];
  const d = Math.floor(n / 10), u = n % 10;
  if (d === 7 || d === 9) {
    const reste = U[10 + u];
    return (d === 7 && u === 1) ? 'soixante et onze' : `${T[d]}-${reste}`;
  }
  if (u === 0) return d === 8 ? 'quatre-vingts' : T[d];
  if (u === 1 && d !== 8) return `${T[d]} et un`;
  return `${T[d]}-${U[u]}`;
}

function sousMille(n) {
  if (n < 100) return sousCent(n);
  const c = Math.floor(n / 100), r = n % 100;
  const tete = c === 1 ? 'cent' : `${U[c]} cent${r === 0 ? 's' : ''}`;
  return r === 0 ? tete : `${tete} ${sousCent(r)}`;
}

export function enLettres(n) {
  n = Math.trunc(Math.abs(Number(n)));
  if (!Number.isFinite(n)) return '';
  if (n < 1000) return sousMille(n);
  if (n < 1000000) {
    const m = Math.floor(n / 1000), r = n % 1000;
    const tete = m === 1 ? 'mille' : `${sousMille(m)} mille`;
    return r === 0 ? tete : `${tete} ${sousMille(r)}`;
  }
  return String(n);
}

/* Remplace les nombres écrits en chiffres par leur écriture en lettres */
export function nombresEnLettres(texte) {
  return String(texte).replace(/\d+/g, (m) => (m.length <= 6 ? enLettres(m) : m));
}
