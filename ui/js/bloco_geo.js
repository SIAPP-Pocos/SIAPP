// SIAPP — geometria do bloco fechado no visor: a mesma de motor/bloco_solido.py (malha do
// contorno pelas células da grade recortadas, borda, bilinear), para a janela e a figura
// mostrarem exatamente o mesmo bloco. Sem estado; sem three.js.

// Semiplanos (a, b, c) de um polígono convexo anti-horário: dentro = a·x + b·y + c ≥ 0.
export function semiplanos(pol) {
  const out = [];
  for (let k = 0; k < pol.length; k++) {
    const [x1, y1] = pol[k], [x2, y2] = pol[(k + 1) % pol.length];
    let a = -(y2 - y1), b = x2 - x1;
    const n = Math.hypot(a, b);
    if (n > 0) { a /= n; b /= n; out.push([a, b, -(a * x1 + b * y1)]); }
  }
  return out;
}

export function dentro(planos, x, y, tol = 1e-9) {
  return planos.every(([a, b, c]) => a * x + b * y + c >= -tol);
}

// Sutherland–Hodgman: recorta um polígono convexo pelos semiplanos.
export function recortar(pol, planos) {
  let p = pol.slice();
  for (const [a, b, c] of planos) {
    if (!p.length) break;
    const novo = [];
    for (let k = 0; k < p.length; k++) {
      const P = p[k], Q = p[(k + 1) % p.length];
      const fp = a * P[0] + b * P[1] + c, fq = a * Q[0] + b * Q[1] + c;
      if (fp >= 0) novo.push(P);
      if ((fp >= 0) !== (fq >= 0)) {
        const s = fp / (fp - fq);
        novo.push([P[0] + s * (Q[0] - P[0]), P[1] + s * (Q[1] - P[1])]);
      }
    }
    p = novo;
  }
  return p;
}

function area(p) {
  let s = 0;
  for (let k = 0; k < p.length; k++) {
    const [x1, y1] = p[k], [x2, y2] = p[(k + 1) % p.length];
    s += x1 * y2 - x2 * y1;
  }
  return Math.abs(s) / 2;
}

// Triângulos que cobrem o polígono: células inteiras viram dois triângulos; as da borda
// são recortadas pelo polígono (borda reta). {pts: [[x, y]], tris: [[a, b, c]]}.
export function malhaContorno(g, pol) {
  const { x0, y0, passo: p, nx, ny } = g;
  const planos = semiplanos(pol);
  const tol = 1e-9 * Math.max(1, Math.abs(x0) + Math.abs(y0) + p * Math.max(nx, ny));
  const dentroNo = new Uint8Array(nx * ny);
  for (let j = 0; j < ny; j++) {
    for (let i = 0; i < nx; i++) dentroNo[j * nx + i] = dentro(planos, x0 + p * i, y0 + p * j, tol) ? 1 : 0;
  }
  const pts = [], indice = new Map(), tris = [];
  const ponto = (x, y) => {
    const k = `${x.toFixed(7)},${y.toFixed(7)}`;
    let id = indice.get(k);
    if (id === undefined) { id = pts.length; indice.set(k, id); pts.push([x, y]); }
    return id;
  };
  const xs = pol.map((q) => q[0]), ys = pol.map((q) => q[1]);
  const i0 = Math.max(0, Math.floor((Math.min(...xs) - x0) / p) - 1), i1 = Math.min(nx - 2, Math.floor((Math.max(...xs) - x0) / p) + 1);
  const j0 = Math.max(0, Math.floor((Math.min(...ys) - y0) / p) - 1), j1 = Math.min(ny - 2, Math.floor((Math.max(...ys) - y0) / p) + 1);
  for (let j = j0; j <= j1; j++) {
    for (let i = i0; i <= i1; i++) {
      const a = j * nx + i;
      const xa = x0 + p * i, ya = y0 + p * j;
      if (dentroNo[a] && dentroNo[a + 1] && dentroNo[a + nx] && dentroNo[a + nx + 1]) {
        const A = ponto(xa, ya), B = ponto(xa + p, ya), C = ponto(xa + p, ya + p), D = ponto(xa, ya + p);
        tris.push([A, B, C], [A, C, D]);
        continue;
      }
      const r = recortar([[xa, ya], [xa + p, ya], [xa + p, ya + p], [xa, ya + p]], planos);
      if (r.length < 3 || area(r) < 1e-9 * p * p) continue;
      let ids = r.map(([x, y]) => ponto(x, y));
      ids = ids.filter((v, k) => v !== ids[(k + ids.length - 1) % ids.length]);
      for (let k = 1; k < ids.length - 1; k++) tris.push([ids[0], ids[k], ids[k + 1]]);
    }
  }
  return { pts, tris };
}

// Pontos ao longo do polígono fechado: vértices e cruzamentos com as linhas da grade.
export function borda(g, pol) {
  const { x0, y0, passo: p } = g;
  const out = [];
  for (let k = 0; k < pol.length; k++) {
    const a = pol[k], b = pol[(k + 1) % pol.length];
    const ts = new Set([0]);
    for (const [e, orig] of [[0, x0], [1, y0]]) {
      const lo = Math.min(a[e], b[e]), hi = Math.max(a[e], b[e]);
      if (hi - lo < 1e-12) continue;
      for (let n = Math.ceil((lo - orig) / p); n <= Math.floor((hi - orig) / p); n++) {
        const t = (orig + n * p - a[e]) / (b[e] - a[e]);
        if (t > 1e-9 && t < 1 - 1e-9) ts.add(t);
      }
    }
    for (const t of [...ts].sort((u, w) => u - w)) out.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
  }
  out.push(pol[0].slice());
  return out;
}

export function bilinear(z, g, x, y) {
  const fx = Math.min(Math.max((x - g.x0) / g.passo, 0), g.nx - 1);
  const fy = Math.min(Math.max((y - g.y0) / g.passo, 0), g.ny - 1);
  const i = Math.min(Math.floor(fx), g.nx - 2), j = Math.min(Math.floor(fy), g.ny - 2);
  const u = fx - i, w = fy - j;
  return (1 - u) * (1 - w) * z[j][i] + u * (1 - w) * z[j][i + 1] + (1 - u) * w * z[j + 1][i] + u * w * z[j + 1][i + 1];
}

// Trecho [t0, t1] do segmento a→b dentro do polígono convexo (Cyrus–Beck), ou null.
export function trechoDentro(a, b, planos) {
  let t0 = 0, t1 = 1;
  const dx = b[0] - a[0], dy = b[1] - a[1];
  for (const [pa, pb, pc] of planos) {
    const f = pa * a[0] + pb * a[1] + pc, d = pa * dx + pb * dy;
    if (Math.abs(d) < 1e-15) { if (f < 0) return null; continue; }
    const t = -f / d;
    if (d > 0) t0 = Math.max(t0, t); else t1 = Math.min(t1, t);
    if (t0 > t1) return null;
  }
  return [t0, t1];
}

// Linha (lista de [x, y]) amostrada a cada `passo` km, só dentro do polígono, com os pontos
// exatos onde entra e sai. {pts, dist} (dist = distância ao longo da linha original).
export function amostrarLinha(linha, passo, planos) {
  const pts = [], dist = [];
  let acum = 0;
  for (let k = 0; k < linha.length - 1; k++) {
    const a = linha[k], b = linha[k + 1];
    const comp = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const tr = comp > 0 ? trechoDentro(a, b, planos) : null;
    if (tr) {
      const n = Math.max(1, Math.ceil(((tr[1] - tr[0]) * comp) / passo));
      for (let s = 0; s <= n; s++) {
        const t = tr[0] + (tr[1] - tr[0]) * s / n;
        if (s === 0 && pts.length && Math.abs(dist[dist.length - 1] - (acum + t * comp)) < 1e-9) continue;
        pts.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
        dist.push(acum + t * comp);
      }
    }
    acum += comp;
  }
  return { pts, dist };
}

// Prolonga a linha nas duas pontas até a borda do polígono (a parede atravessa o bloco).
export function prolongar(linha, pol) {
  if (linha.length < 2) return linha;
  const planos = semiplanos(pol);
  const xs = pol.map((q) => q[0]), ys = pol.map((q) => q[1]);
  const L = 4 * Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) + 1;
  const ponta = (a, b) => {         // de b, na direção a→b, até sair do polígono
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    const fim = [b[0] + (b[0] - a[0]) / d * L, b[1] + (b[1] - a[1]) / d * L];
    const tr = trechoDentro(b, fim, planos);
    return tr ? [b[0] + tr[1] * (fim[0] - b[0]), b[1] + tr[1] * (fim[1] - b[1])] : b;
  };
  const ini = ponta(linha[1], linha[0]), fim = ponta(linha[linha.length - 2], linha[linha.length - 1]);
  return [ini, ...linha, fim];
}
