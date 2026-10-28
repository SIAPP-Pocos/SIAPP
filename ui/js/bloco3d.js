// SIAPP — visor 3D do bloco (three.js, em ui/vendor/three). O modelo vem pronto do motor
// (motor/bloco.py): poços em km num plano local, superfícies de topo numa grade e o bloco
// fechado (motor/bloco_solido.py: limites das camadas na mesma grade).
// Eixos da cena: X = leste (km), Z = −norte (km), Y = cota (m) × exagero / 1000.
import * as THREE from "three";
import { OrbitControls } from "../vendor/three/OrbitControls.js";
import * as geo from "./bloco_geo.js";

const v = {
  renderer: null, scene: null, camera: null, controls: null, caixa: null, modelo: null,
  mundo: null,          // grupo escalado no Y (superfícies, linhas dos poços, caixa)
  marcas: [],           // {obj, cota} — esferas e discos, posicionados à mão (não esticam)
  rotulos: [],          // {el, pos: Vector3 em coordenadas do mundo sem exagero (Y em m), tipo}
  superficies: {},      // chave → Mesh
  topos: {},            // chave → [Mesh]
  exagero: 10, opacidade: 0.85, mostrarNomes: true, mostrarCaixa: true,
  centro: { x: 0, y: 0, cota: 0 }, lado: 1, overlay: null, norte: null, dica: null, raio: null,
  modo: "superficies",  // ou "fechado"
  camadas: {},          // bloco fechado: chave → {grupo, corpo, k}
  visivel: {},          // chave → a unidade está ligada
  corte: { ativo: false, quadrante: "SW", fx: 0.5, fy: 0.5 },
  afastar: 0,           // 0–1: camadas afastadas na vertical
  parede: null,         // seção A–A′: {linha: [[x, y]], pocos: [ids]}
  validacao: null,      // "poço|unidade" → linha da validação cruzada (para a dica nos topos)
  pino: null,           // prognóstico num ponto: {grupo, marcas, dados}
  escolher: null,       // clique no bloco: função que recebe {x, y}
};
const ESP_MIN = 0.5;    // m: camada mais fina que isso não é desenhada (acunhamento)

// Aparência dos poços (Bloco 7 do teste da 0.29): marcador da cabeça, linha, discos dos topos,
// trilhas (espessura e cor de cada classe), legenda e "por cima do bloco". Guardada nas
// preferências (preferencias.json → bloco.aparencia); a figura (bloco_figura.py) usa a mesma.
const APARENCIA_PADRAO = {
  marcador: { forma: "esfera", cor: "#1c2227", tamanho: 1 },
  linha: { cor: "#3a4148" },
  topos: true,
  trilha: { espessura: 1, cores: {} },     // cores: "classe:2" | "fluido:óleo" → "#rrggbb"
  legenda: true,
  por_cima: "fechado",                     // "fechado" (só no bloco fechado) | "sempre" | "nunca"
};
v.aparencia = JSON.parse(JSON.stringify(APARENCIA_PADRAO));

function aparenciaCompleta(ap) {
  const a = JSON.parse(JSON.stringify(APARENCIA_PADRAO));
  if (!ap) return a;
  Object.assign(a.marcador, ap.marcador || {});
  Object.assign(a.linha, ap.linha || {});
  a.trilha.espessura = (ap.trilha && ap.trilha.espessura) || 1;
  a.trilha.cores = { ...((ap.trilha && ap.trilha.cores) || {}) };
  for (const k of ["topos", "legenda"]) if (typeof ap[k] === "boolean") a[k] = ap[k];
  if (["fechado", "sempre", "nunca"].includes(ap.por_cima)) a.por_cima = ap.por_cima;
  return a;
}

function geometriaMarcador(forma, r) {
  if (forma === "cubo") return new THREE.BoxGeometry(r * 2, r * 2, r * 2);
  if (forma === "cone") return new THREE.ConeGeometry(r * 1.2, r * 2.4, 16).rotateX(Math.PI);   // ponta para baixo
  if (forma === "losango") return new THREE.OctahedronGeometry(r * 1.4);
  if (forma === "cilindro") return new THREE.CylinderGeometry(r, r, r * 2.2, 16);
  return new THREE.SphereGeometry(r * 1.3, 16, 12);
}

// "por cima do bloco": os poços aparecem mesmo dentro do bloco fechado ou atrás das superfícies
function emCima() {
  const pc = v.aparencia.por_cima;
  return pc === "sempre" || (pc === "fechado" && v.modo === "fechado" && !!v.sm);
}

function porCima(obj) {
  const sim = emCima();
  const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
  for (const mt of mats) { if (mt) { mt.depthTest = !sim; mt.needsUpdate = true; } }
  obj.renderOrder = sim ? 10 : 0;
}

function aplicarPorCima() {
  if (v.gPocos) for (const o of v.gPocos.children) porCima(o);
  if (v.trilhas) for (const o of v.trilhas.children) porCima(o);
  for (const mk of v.marcas) if (mk.doPoco) porCima(mk.obj);
}

function cenaDeY(cota) { return (cota - v.centro.cota) * v.exagero / 1000; }

function limparCena() {
  if (!v.scene) return;
  v.scene.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
  });
  while (v.scene.children.length) v.scene.remove(v.scene.children[0]);
  v.marcas = []; v.rotulos = []; v.superficies = {}; v.topos = {}; v.marcasProp = []; v.alvosTrilha = [];
  v.camadas = {}; v.sm = null; v.pino = null;
  if (v.overlay) v.overlay.textContent = "";
}

function passoBonito(faixa, alvo = 5) {
  const bruto = faixa / alvo, p = Math.pow(10, Math.floor(Math.log10(bruto)));
  for (const m of [1, 2, 2.5, 5, 10]) if (bruto <= m * p) return m * p;
  return 10 * p;
}

function fmt(n, casas = 0) {
  return Number(n).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function rotulo(texto, x, cota, z, tipo) {
  const el = document.createElement("div");
  el.className = "bl-rot " + tipo;
  el.textContent = texto;
  v.overlay.appendChild(el);
  v.rotulos.push({ el, x, cota, z, tipo, texto });
  return el;
}

function iniciar(container) {
  if (v.renderer && v.renderer.domElement.parentElement === container) return;
  container.textContent = "";
  v.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  v.renderer.setPixelRatio(window.devicePixelRatio || 1);
  v.renderer.setClearColor(0xffffff, 1);
  v.renderer.localClippingEnabled = true;
  container.appendChild(v.renderer.domElement);
  v.overlay = document.createElement("div");
  v.overlay.className = "bl-overlay";
  container.appendChild(v.overlay);
  v.norte = document.createElement("div");
  v.norte.className = "bl-norte";
  v.norte.innerHTML = '<svg viewBox="-30 -30 60 60" width="56" height="56"><circle r="17" fill="#fff" ' +
    'fill-opacity=".85" stroke="#9aa3a8"/><g class="seta"><polygon points="0,-15 4.5,0 -4.5,0" fill="#1c2227"/>' +
    '<polygon points="0,15 4.5,0 -4.5,0" fill="#fff" stroke="#1c2227" stroke-width="1"/></g><text class="letra" text-anchor="middle" dominant-baseline="central" font-size="11" ' +
    'font-family="sans-serif" font-weight="700">N</text></svg>';
  container.appendChild(v.norte);
  v.dica = document.createElement("div");
  v.dica.className = "bl-dica";
  v.dica.hidden = true;
  container.appendChild(v.dica);
  v.scene = new THREE.Scene();
  v.camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100000);
  v.controls = new OrbitControls(v.camera, v.renderer.domElement);
  v.controls.enableDamping = false;
  v.controls.addEventListener("change", desenhar);
  v.raio = new THREE.Raycaster();
  v.renderer.domElement.addEventListener("mousemove", passarMouse);
  v.renderer.domElement.addEventListener("mouseleave", () => { v.dica.hidden = true; });
  v.renderer.domElement.addEventListener("pointerdown", (ev) => { v.apertou = [ev.clientX, ev.clientY]; });
  v.renderer.domElement.addEventListener("pointerup", soltou);
  new ResizeObserver(() => redimensionar()).observe(container);
}

function redimensionar() {
  const c = v.renderer && v.renderer.domElement.parentElement;
  if (!c) return;
  const w = c.clientWidth || 800, h = c.clientHeight || 520;
  v.renderer.setSize(w, h, false);
  v.renderer.domElement.style.width = w + "px";
  v.renderer.domElement.style.height = h + "px";
  v.camera.aspect = w / h;
  v.camera.updateProjectionMatrix();
  desenhar();
}

function montarCena(m) {
  limparCena();
  const g = m.grade;
  const sol = m.solido && m.solido.ok ? m.solido : null;
  v.cotaMax = Math.max(m.cota_max, sol ? sol.cota_topo_max : -Infinity);
  v.cotaMin = Math.min(m.cota_min, sol ? sol.base : Infinity);
  v.centro = { x: g.x0 + (g.nx - 1) * g.passo / 2, y: g.y0 + (g.ny - 1) * g.passo / 2,
               cota: (v.cotaMax + v.cotaMin) / 2 };
  v.lado = Math.max((g.nx - 1) * g.passo, (g.ny - 1) * g.passo, 0.5);
  const X = (x) => x - v.centro.x, Z = (y) => -(y - v.centro.y);
  v.X = X; v.Z = Z;

  v.scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const luz = new THREE.DirectionalLight(0xffffff, 0.9);
  luz.position.set(-1, 2, 1.5);
  v.scene.add(luz);
  v.mundo = new THREE.Group();
  v.scene.add(v.mundo);

  // superfícies de topo: Y em metros (relativos ao centro), o grupo aplica o exagero
  for (const s of m.superficies) {
    if (!s.z) continue;
    const geo = s.malha ? geometriaMalha(s.malha, X, Z) : geometriaGrade(s, g, X, Z);
    geo.computeVertexNormals();
    const mat = new THREE.MeshLambertMaterial({ color: s.cor, side: THREE.DoubleSide, transparent: v.opacidade < 1,
                                                opacity: v.opacidade, polygonOffset: true,
                                                polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.userData = { tipo: "superficie", nome: s.nome };
    v.mundo.add(mesh);
    v.superficies[s.chave] = mesh;
  }
  montarSolido(m);
  desenharPocosECaixa(m, g, X, Z);
  aplicarModo();
}

// Triângulos entre os poços (sem margem): a interpolação linear exata, borda reta no contorno.
function geometriaMalha(malha, X, Z) {
  const pos = new Float32Array(malha.pts.length * 3);
  malha.pts.forEach(([x, y, c], k) => { pos[3 * k] = X(x); pos[3 * k + 1] = c - v.centro.cota; pos[3 * k + 2] = Z(y); });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setIndex(malha.tris.flat());
  return geo;
}

// Grade (com margem ou corte por distância): cada meio-quadrado entra se os 3 cantos têm valor.
function geometriaGrade(s, g, X, Z) {
  {
    const pos = new Float32Array(g.nx * g.ny * 3);
    for (let j = 0; j < g.ny; j++) {
      for (let i = 0; i < g.nx; i++) {
        const k = (j * g.nx + i) * 3, zz = s.z[j][i];
        pos[k] = X(g.x0 + i * g.passo);
        pos[k + 1] = zz == null ? 0 : zz - v.centro.cota;
        pos[k + 2] = Z(g.y0 + j * g.passo);
      }
    }
    const idx = [];
    const ok = (j, i) => s.z[j][i] != null;
    for (let j = 0; j < g.ny - 1; j++) {
      for (let i = 0; i < g.nx - 1; i++) {
        const a = j * g.nx + i, b = a + 1, c = a + g.nx, d = c + 1;
        const A = ok(j, i), B = ok(j, i + 1), C = ok(j + 1, i), D = ok(j + 1, i + 1);
        if (A && B && C && D) { idx.push(a, c, b, b, c, d); continue; }
        if (A && B && C) idx.push(a, c, b);
        else if (B && C && D) idx.push(b, c, d);
        else if (A && B && D) idx.push(a, d, b);
        else if (A && C && D) idx.push(a, c, d);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setIndex(idx);
    return geo;
  }
}

// poços: linha da mesa ao fundo; marcador na cabeça; disco em cada topo (refeitos ao mudar a aparência)
function desenharPocos(m) {
  const X = v.X, Z = v.Z, ap = v.aparencia;
  if (v.gPocos) {
    v.gPocos.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    v.mundo.remove(v.gPocos);
  }
  for (const mk of v.marcas.filter((q) => q.doPoco)) {
    v.scene.remove(mk.obj);
    mk.obj.geometry.dispose();
    mk.obj.material.dispose();
  }
  v.marcas = v.marcas.filter((q) => !q.doPoco);
  v.topos = {};
  const r = v.lado * 0.006;
  const geoTopo = new THREE.CylinderGeometry(r * 1.6, r * 1.6, r * 0.5, 16);
  const matLinha = new THREE.LineBasicMaterial({ color: ap.linha.cor });
  const matTraj = new THREE.LineBasicMaterial({ color: ap.linha.cor });
  v.gPocos = new THREE.Group();
  v.mundo.add(v.gPocos);
  const forma = ap.marcador.forma;
  for (const p of m.pocos) {
    const cotas = p.unidades.flatMap((u) => [u.cota_topo, u.cota_base]);
    const topo = p.mesa ?? Math.max(...cotas, 0);
    const fundo = p.cota_fundo ?? Math.min(...cotas, topo - 10);
    const caminho = p.caminho && p.caminho.length > 1
      ? p.caminho.map(([, x, y, c]) => new THREE.Vector3(X(x), c - v.centro.cota, Z(y)))
      : [new THREE.Vector3(X(p.x), topo - v.centro.cota, Z(p.y)), new THREE.Vector3(X(p.x), fundo - v.centro.cota, Z(p.y))];
    v.gPocos.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(caminho), p.trajetoria ? matTraj : matLinha));
    if (forma !== "nenhum") {
      const cab = new THREE.Mesh(geometriaMarcador(forma, r * ap.marcador.tamanho),
                                 new THREE.MeshLambertMaterial({ color: ap.marcador.cor }));
      cab.userData = { tipo: "poco", poco: p };
      v.scene.add(cab);
      v.marcas.push({ obj: cab, x: X(p.x), cota: topo, z: Z(p.y), doPoco: true });
    }
    for (const u of p.unidades) {
      const disco = new THREE.Mesh(geoTopo, new THREE.MeshLambertMaterial({ color: u.cor }));
      disco.userData = { tipo: "topo", poco: p, unidade: u };
      disco.visible = ap.topos;
      v.scene.add(disco);
      v.marcas.push({ obj: disco, x: X(u.x ?? p.x), cota: u.cota_topo, z: Z(u.y ?? p.y), chave: u.chave, doPoco: true,
                      topo: true });
      (v.topos[u.chave] = v.topos[u.chave] || []).push(disco);
    }
  }
}

function desenharPocosECaixa(m, g, X, Z) {
  v.X = X; v.Z = Z;
  desenharPocos(m);
  for (const p of m.pocos) {
    const cotas = p.unidades.flatMap((u) => [u.cota_topo, u.cota_base]);
    rotulo(p.id, X(p.x), p.mesa ?? Math.max(...cotas, 0), Z(p.y), "poco");
  }
  // caixa com marcas: distância (km) a partir do canto SW e cota (m)
  v.caixa = new THREE.Group();
  v.mundo.add(v.caixa);
  const x0 = X(g.x0), x1 = X(g.x0 + (g.nx - 1) * g.passo);
  const z0 = Z(g.y0), z1 = Z(g.y0 + (g.ny - 1) * g.passo);        // z0 = sul (frente), z1 = norte
  const passoC = passoBonito(v.cotaMax - v.cotaMin || 100);
  const c0 = Math.floor(v.cotaMin / passoC) * passoC, c1 = Math.ceil(v.cotaMax / passoC) * passoC;
  const y0 = c0 - v.centro.cota, y1 = c1 - v.centro.cota;
  const pts = [];
  const seg = (a, b) => pts.push(new THREE.Vector3(...a), new THREE.Vector3(...b));
  for (const y of [y0, y1]) {
    seg([x0, y, z0], [x1, y, z0]); seg([x1, y, z0], [x1, y, z1]); seg([x1, y, z1], [x0, y, z1]); seg([x0, y, z1], [x0, y, z0]);
  }
  for (const [x, z] of [[x0, z0], [x1, z0], [x1, z1], [x0, z1]]) seg([x, y0, z], [x, y1, z]);
  const passoH = passoBonito(v.lado);
  const tique = v.lado * 0.012;
  for (let d = 0; d <= x1 - x0 + 1e-9; d += passoH) {
    seg([x0 + d, y0, z0], [x0 + d, y0, z0 + tique]);
    rotulo(fmt(d, passoH < 1 ? 1 : 0), x0 + d, c0, z0 + tique * 3, "eixo");
  }
  for (let d = 0; d <= z0 - z1 + 1e-9; d += passoH) {
    seg([x0, y0, z0 - d], [x0 - tique, y0, z0 - d]);
    rotulo(fmt(d, passoH < 1 ? 1 : 0), x0 - tique * 3, c0, z0 - d, "eixo");
  }
  for (let c = c0; c <= c1 + 1e-9; c += passoC) {
    seg([x1, c - v.centro.cota, z0], [x1 + tique, c - v.centro.cota, z0]);
    rotulo(fmt(c), x1 + tique * 4, c, z0, "eixo cota");
  }
  rotulo("leste (km)", (x0 + x1) / 2, c0, z0 + tique * 7, "titulo-eixo");
  rotulo("norte (km)", x0 - tique * 8, c0, (z0 + z1) / 2, "titulo-eixo");
  rotulo("cota (m)", x1 + tique * 10, (c0 + c1) / 2, z0, "titulo-eixo");
  v.caixa.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),
                                     new THREE.LineBasicMaterial({ color: 0x9aa3a8 })));
  v.cantoSW = { lat: m.origem.lat + (g.y0 / 6371) * 180 / Math.PI,
                lon: m.origem.lon + (g.x0 / (6371 * Math.cos(m.origem.lat * Math.PI / 180))) * 180 / Math.PI };
  v.trilhas = new THREE.Group();
  v.mundo.add(v.trilhas);
  desenharTrilhas();
  aplicarDrape();
  aplicarExagero();
}

// ------------------------------------------------ bloco fechado
// Cada camada é uma casca fechada: topo (limite k), fundo (limite k+1) e as paredes ao longo
// do contorno. Onde a camada é extrapolada (fora do contorno dos poços com o dado), a cor
// fica mais clara. O corte tira um quadrante (planos de recorte) e fecha a ferida com
// tampas; a seção A–A′ é uma parede ao longo dos poços da aba Seção.
function clarear(cor, controlado) {
  return controlado ? new THREE.Color(cor) : new THREE.Color(cor).lerp(new THREE.Color(0xffffff), 0.55);
}

// dentro do contorno dos poços com a espessura da camada (borda conta, com folga de 1 m)
function controlado(c, x, y) {
  if (!c.controle) return false;
  if (!c._planos) c._planos = geo.semiplanos(c.controle);
  return geo.dentro(c._planos, x, y, 1e-3);
}

function montarSolido(m) {
  const s = m.solido;
  v.solido = new THREE.Group();
  v.mundo.add(v.solido);
  if (!s || !s.ok) return;
  const g = m.grade;
  const malha = geo.malhaContorno(g, s.contorno);
  const borda = geo.borda(g, s.contorno);
  const val = (pts) => s.limites.map((z) => pts.map(([x, y]) => geo.bilinear(z, g, x, y)));
  v.sm = { malha, borda, planos: geo.semiplanos(s.contorno), limM: val(malha.pts), limB: val(borda),
           xs: s.contorno.map((q) => q[0]), ys: s.contorno.map((q) => q[1]) };
  v.planosCorte = [new THREE.Plane(new THREE.Vector3(1, 0, 0), 1e9), new THREE.Plane(new THREE.Vector3(0, 0, -1), 1e9)];
  s.camadas.forEach((c, k) => {
    const grupo = new THREE.Group();
    const corpo = new THREE.Mesh(geometriaCamada(k, c), new THREE.MeshLambertMaterial({
      vertexColors: true, side: THREE.DoubleSide, clippingPlanes: v.planosCorte, clipIntersection: true,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 + k }));
    corpo.userData = { tipo: "camada", camada: c };
    grupo.add(corpo);
    v.solido.add(grupo);
    v.camadas[c.chave] = { grupo, corpo, k, camada: c };
  });
  desenharTampas();
  desenharParede();
}

// Recorta um polígono de vértices [x, y, topo, fundo] onde a espessura passa de ESP_MIN
// (linha de acunhamento suave, em vez da escada das células).
function recortarEspessura(pol) {
  const f = (p) => p[2] - p[3] - ESP_MIN, out = [];
  for (let i = 0; i < pol.length; i++) {
    const P = pol[i], Q = pol[(i + 1) % pol.length], fp = f(P), fq = f(Q);
    if (fp >= 0) out.push(P);
    if ((fp >= 0) !== (fq >= 0)) { const t = fp / (fp - fq); out.push(P.map((a, j) => a + t * (Q[j] - a))); }
  }
  return out;
}

function geometriaCamada(k, c) {
  const { malha, borda, limM, limB } = v.sm;
  const T = limM[k], B = limM[k + 1];
  const pos = [], cor = [], idx = [];
  const vert = (x, y, cota) => {
    pos.push(v.X(x), cota - v.centro.cota, v.Z(y));
    const c3 = clarear(c.cor, controlado(c, x, y));
    cor.push(c3.r, c3.g, c3.b);
    return pos.length / 3 - 1;
  };
  const n = malha.pts.length;
  malha.pts.forEach(([x, y], i) => vert(x, y, T[i]));
  malha.pts.forEach(([x, y], i) => vert(x, y, B[i]));
  for (const [a, b, d] of malha.tris) {
    const ea = T[a] - B[a], eb = T[b] - B[b], ed = T[d] - B[d];
    if (Math.max(ea, eb, ed) < ESP_MIN) continue;
    if (Math.min(ea, eb, ed) >= ESP_MIN) { idx.push(a, b, d, n + a, n + d, n + b); continue; }
    const r = recortarEspessura([a, b, d].map((i) => [malha.pts[i][0], malha.pts[i][1], T[i], B[i]]));
    if (r.length < 3) continue;
    const tops = r.map((p) => vert(p[0], p[1], p[2])), fundos = r.map((p) => vert(p[0], p[1], p[3]));
    for (let j = 1; j < r.length - 1; j++) idx.push(tops[0], tops[j], tops[j + 1], fundos[0], fundos[j + 1], fundos[j]);
  }
  const Tb = limB[k], Bb = limB[k + 1];
  for (let i = 0; i < borda.length - 1; i++) {
    let P = [borda[i][0], borda[i][1], Tb[i], Bb[i]], Q = [borda[i + 1][0], borda[i + 1][1], Tb[i + 1], Bb[i + 1]];
    const fp = P[2] - P[3] - ESP_MIN, fq = Q[2] - Q[3] - ESP_MIN;
    if (fp < 0 && fq < 0) continue;
    if (fp < 0 || fq < 0) {          // acunha no meio do trecho: só a parte com espessura
      const t = fp / (fp - fq), M = P.map((a, j) => a + t * (Q[j] - a));
      if (fp < 0) P = M; else Q = M;
    }
    const a = vert(P[0], P[1], P[2]), b = vert(Q[0], Q[1], Q[2]);
    const d = vert(Q[0], Q[1], Q[3]), e = vert(P[0], P[1], P[3]);
    idx.push(a, e, d, a, d, b);
  }
  const gg = new THREE.BufferGeometry();
  gg.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  gg.setAttribute("color", new THREE.Float32BufferAttribute(cor, 3));
  gg.setIndex(idx);
  gg.computeVertexNormals();
  return gg;
}

// Parede vertical ao longo de uma linha: uma faixa por camada (geometria por camada, para
// afastar junto). Devolve {chave: BufferGeometry}.
function paredes(linha) {
  const m = v.modelo, s = m.solido, g = m.grade;
  const { pts } = geo.amostrarLinha(linha, g.passo / 2, v.sm.planos);
  const out = {};
  if (pts.length < 2) return out;
  const lims = s.limites.map((z) => pts.map(([x, y]) => geo.bilinear(z, g, x, y)));
  s.camadas.forEach((c, k) => {
    const pos = [], cor = [], idx = [];
    for (let i = 0; i < pts.length; i++) {
      const c3 = clarear(c.cor, controlado(c, pts[i][0], pts[i][1]));
      for (const cota of [lims[k][i], lims[k + 1][i]]) {
        pos.push(v.X(pts[i][0]), cota - v.centro.cota, v.Z(pts[i][1]));
        cor.push(c3.r, c3.g, c3.b);
      }
      if (i && Math.max(lims[k][i] - lims[k + 1][i], lims[k][i - 1] - lims[k + 1][i - 1]) >= ESP_MIN) {
        const a = 2 * (i - 1), b = a + 1, d = a + 2, e = a + 3;
        idx.push(a, b, e, a, e, d);
      }
    }
    if (!idx.length) return;
    const gg = new THREE.BufferGeometry();
    gg.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    gg.setAttribute("color", new THREE.Float32BufferAttribute(cor, 3));
    gg.setIndex(idx);
    gg.computeVertexNormals();
    out[c.chave] = gg;
  });
  return out;
}

function trocarExtra(nome, geos, opcoes = {}) {
  for (const [chave, cam] of Object.entries(v.camadas)) {
    if (cam[nome]) { cam.grupo.remove(cam[nome]); cam[nome].geometry.dispose(); cam[nome].material.dispose(); cam[nome] = null; }
    const gg = geos && geos[chave];
    if (!gg) continue;
    const mesh = new THREE.Mesh(gg, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, ...opcoes }));
    mesh.userData = { tipo: "camada", camada: cam.camada, parede: nome === "parede" };
    cam.grupo.add(mesh);
    cam[nome] = mesh;
  }
}

// x, y (km) do canto do corte e as duas linhas das tampas, conforme o quadrante tirado.
function geometriaCorte() {
  const { xs, ys } = v.sm, c = v.corte;
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const cx = xmin + c.fx * (xmax - xmin), cy = ymin + c.fy * (ymax - ymin);
  const oeste = c.quadrante.includes("W"), sul = c.quadrante.includes("S");
  return { cx, cy, oeste, sul,
           linhas: [[[cx, sul ? ymin - 1 : cy], [cx, sul ? cy : ymax + 1]],
                    [[oeste ? xmin - 1 : cx, cy], [oeste ? cx : xmax + 1, cy]]] };
}

function desenharTampas() {
  if (!v.sm) return;
  const [px, pz] = v.planosCorte;
  if (!v.corte.ativo) {
    px.constant = 1e9; pz.constant = 1e9;
    trocarExtra("tampa", null);
    desenhar();
    return;
  }
  const k = geometriaCorte();
  // o lado negativo de cada plano é recortado; com clipIntersection, só onde os dois são
  // negativos (o quadrante)
  const X = v.X(k.cx), Z = v.Z(k.cy);
  if (k.oeste) px.set(new THREE.Vector3(1, 0, 0), -X); else px.set(new THREE.Vector3(-1, 0, 0), X);
  if (k.sul) pz.set(new THREE.Vector3(0, 0, -1), Z); else pz.set(new THREE.Vector3(0, 0, 1), -Z);
  const geos = {};
  for (const linha of k.linhas) {
    for (const [ch, gg] of Object.entries(paredes(linha))) (geos[ch] = geos[ch] || []).push(gg);
  }
  const unidas = {};
  for (const [ch, lista] of Object.entries(geos)) unidas[ch] = lista.length === 1 ? lista[0] : unir(lista);
  trocarExtra("tampa", unidas);
  desenhar();
}

function unir(lista) {
  const pos = [], cor = [], idx = [];
  for (const gg of lista) {
    const base = pos.length / 3;
    pos.push(...gg.getAttribute("position").array);
    cor.push(...gg.getAttribute("color").array);
    idx.push(...Array.from(gg.getIndex().array, (i) => i + base));
    gg.dispose();
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute("color", new THREE.Float32BufferAttribute(cor, 3));
  out.setIndex(idx);
  out.computeVertexNormals();
  return out;
}

function desenharParede() {
  v.rotulos = v.rotulos.filter((r) => { if (r.tipo === "secao") { r.el.remove(); return false; } return true; });
  if (!v.sm) return;
  if (!v.parede || v.parede.linha.length < 2) { trocarExtra("parede", null); aplicarOpacidade(); return; }
  const linha = geo.prolongar(v.parede.linha, v.modelo.solido.contorno);
  trocarExtra("parede", paredes(linha), { polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
  const topo = v.cotaMax + (v.cotaMax - v.cotaMin) * 0.04;
  rotulo("A", v.X(linha[0][0]), topo, v.Z(linha[0][1]), "secao");
  rotulo("A′", v.X(linha[linha.length - 1][0]), topo, v.Z(linha[linha.length - 1][1]), "secao");
  aplicarOpacidade();
}

function aplicarAfastar() {
  const s = v.modelo && v.modelo.solido;
  if (!s || !s.ok) return;
  const passo = v.afastar * (s.cota_topo_max - s.base) * 0.6 / Math.max(1, s.camadas.length);
  for (const cam of Object.values(v.camadas)) cam.grupo.position.y = -cam.k * passo;
  aplicarVisibilidade();
  desenhar();
}

function aplicarModo() {
  const fechado = v.modo === "fechado" && v.sm;
  for (const [ch, mesh] of Object.entries(v.superficies)) mesh.visible = !fechado && v.visivel[ch] !== false;
  if (v.solido) v.solido.visible = !!fechado;
  aplicarPorCima();
  aplicarVisibilidade();
  aplicarOpacidade(v.drape && v.drape.chave);
  desenhar();
}

// Poços, topos e trilhas: escondidos com as camadas afastadas (não casariam com nenhuma).
function aplicarVisibilidade() {
  const afastado = v.modo === "fechado" && v.sm && v.afastar > 0;
  if (v.gPocos) v.gPocos.visible = !afastado;
  if (v.trilhas) v.trilhas.visible = !afastado;
  for (const mk of v.marcas) {
    mk.obj.visible = !afastado && (mk.chave == null || v.visivel[mk.chave] !== false) && !(mk.topo && !v.aparencia.topos);
  }
  for (const [ch, cam] of Object.entries(v.camadas)) cam.grupo.visible = v.visivel[ch] !== false;
}

// ------------------------------------------------ trilhas ao longo dos poços
function noCaminho(p, md) {
  const c = p.caminho;
  if (!c || !c.length) return [p.x, p.y, null];
  if (md <= c[0][0]) return [c[0][1], c[0][2], c[0][3]];
  for (let k = 1; k < c.length; k++) {
    if (md <= c[k][0]) {
      const t = (md - c[k - 1][0]) / ((c[k][0] - c[k - 1][0]) || 1);
      return [0, 1, 2].map((j) => c[k - 1][j + 1] + t * (c[k][j + 1] - c[k - 1][j + 1]));
    }
  }
  const u = c[c.length - 1];
  return [u[1], u[2], u[3]];
}

function tubo(p, a, b, cor, raio, dados) {
  const mds = [a, ...(p.caminho || []).map((q) => q[0]).filter((m) => m > a && m < b), b];
  const pts = mds.map((m) => { const [x, y, c] = noCaminho(p, m); return new THREE.Vector3(v.X(x), c - v.centro.cota, v.Z(y)); });
  if (pts.length < 2 || pts[0].distanceTo(pts[pts.length - 1]) < 1e-6) return;
  const curva = new THREE.CurvePath();
  for (let k = 1; k < pts.length; k++) curva.add(new THREE.LineCurve3(pts[k - 1], pts[k]));
  const geo = new THREE.TubeGeometry(curva, Math.max(2, pts.length * 2), raio, 8, false);
  const mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: cor }));
  mesh.userData = { tipo: "trilha", poco: p, a, b, ...dados };
  v.trilhas.add(mesh);
  v.alvosTrilha.push(mesh);
}

function desenharTrilhas() {
  for (const o of [...v.trilhas.children]) { o.geometry.dispose(); o.material.dispose(); v.trilhas.remove(o); }
  v.alvosTrilha = [];
  const r = v.lado * 0.0045 * (v.aparencia.trilha.espessura || 1);
  const m = v.modelo;
  for (const p of m.pocos) {
    if (v.trilha === "avaliacao") {
      for (const [a, b, c] of p.classes || []) {
        const cl = m.classes[c] || m.classes[String(c)];
        tubo(p, a, b, corTrilha(`classe:${c}`, cl.cor), r, { rotulo: cl.nome });
      }
    } else if (v.trilha === "indicios") {
      for (const i of p.indicios || []) {
        tubo(p, i.md_topo, i.md_base, corTrilha(`fluido:${i.fluido}`, CORES_FLUIDO[i.fluido] || "#898781"), r,
             { rotulo: `indício de ${i.fluido}` });
      }
    }
  }
  for (const o of v.trilhas.children) porCima(o);
  desenharLegendaTrilha();
}

function corTrilha(chave, padrao) {
  return (v.aparencia.trilha.cores || {})[chave] || padrao;
}

const CORES_FLUIDO = { "óleo": "#008300", "gás": "#e34948", "outro": "#898781" };

// [cor, nome, chave da cor] de cada classe que aparece na trilha
function itensTrilha() {
  const m = v.modelo;
  if (v.trilha === "avaliacao") {
    const usadas = new Set(m.pocos.flatMap((p) => (p.classes || []).map((c) => c[2])));
    return Object.entries(m.classes).filter(([k]) => usadas.has(Number(k)))
      .map(([k, c]) => [corTrilha(`classe:${k}`, c.cor), c.nome, `classe:${k}`]);
  }
  if (v.trilha === "indicios") {
    const usados = new Set(m.pocos.flatMap((p) => (p.indicios || []).map((i) => i.fluido)));
    return [...usados].map((f) => [corTrilha(`fluido:${f}`, CORES_FLUIDO[f] || "#898781"), `indício de ${f} (AGP)`, `fluido:${f}`]);
  }
  return [];
}

function desenharLegendaTrilha() {
  if (!v.legTrilha) {
    v.legTrilha = document.createElement("div");
    v.legTrilha.className = "bl-leg-trilha";
    v.renderer.domElement.parentElement.appendChild(v.legTrilha);
  }
  v.legTrilha.textContent = "";
  const itens = itensTrilha();
  const ap = v.aparencia;
  v.legTrilha.hidden = !ap.legenda || (!itens.length && ap.marcador.forma === "nenhum");
  if (ap.marcador.forma !== "nenhum") {
    const li = document.createElement("div");
    const i = document.createElement("i");
    i.className = "marcador " + ap.marcador.forma;
    i.style.background = ap.marcador.cor;
    li.append(i, document.createTextNode("poço (cabeça)"));
    v.legTrilha.appendChild(li);
  }
  for (const [cor, nome] of itens) {
    const li = document.createElement("div");
    const i = document.createElement("i");
    i.style.background = cor;
    li.append(i, document.createTextNode(nome));
    v.legTrilha.appendChild(li);
  }
}

// ------------------------------------------------ propriedade no topo
const RAMPA = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
               "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];

function corRampa(t) {
  t = Math.min(1, Math.max(0, t));
  const f = t * (RAMPA.length - 1), k = Math.min(RAMPA.length - 2, Math.floor(f));
  const a = new THREE.Color(RAMPA[k]), b = new THREE.Color(RAMPA[k + 1]);
  return a.lerp(b, f - k);
}

function fmtProp(valor, prop) {
  if (valor == null) return "—";
  if (prop === "ntg" || prop === "phi_media_pay" || prop === "sw_media_pay") return fmt(valor, 2);
  return fmt(valor, 1) + " m";
}

function aplicarDrape() {
  const m = v.modelo, g = m.grade;
  // desfaz o anterior: superfície volta à cor da unidade, marcas somem
  if (v.drapeAnterior) {
    const s = m.superficies.find((x) => x.chave === v.drapeAnterior);
    if (s) trocarSuperficie(s, null);
  }
  for (const o of v.marcasProp || []) { v.scene.remove(o); o.geometry.dispose(); o.material.dispose(); }
  v.marcas = v.marcas.filter((mk) => !mk.prop);
  v.marcasProp = [];
  v.drapeAnterior = null;
  if (v.escala) v.escala.hidden = true;
  const d = v.drape;
  aplicarOpacidade(d && d.chave);
  if (!d || !d.chave || !m.propriedades || !m.propriedades[d.chave]) { desenhar(); return; }
  const info = m.propriedades[d.chave], faixa = info.faixas[d.prop];
  if (!faixa) { desenhar(); return; }
  const [lo, hi] = faixa[0] === faixa[1] ? [faixa[0] - 1e-9, faixa[1] + 1e-9] : faixa;
  const s = m.superficies.find((x) => x.chave === d.chave);
  const grade = info.grades[d.prop];
  if (s && s.z) trocarSuperficie(s, grade ? { grade, lo, hi } : null);
  v.drapeAnterior = d.chave;
  // esferas coloridas nos poços que têm o valor
  const r = v.lado * 0.011;
  const unidade = (m.legenda.find((u) => u.chave === d.chave) || {}).nome || d.chave;
  for (const q of info.pocos) {
    if (q[d.prop] == null) continue;
    const esf = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12),
                               new THREE.MeshLambertMaterial({ color: corRampa((q[d.prop] - lo) / (hi - lo)) }));
    esf.userData = { tipo: "prop", poco: m.pocos.find((p) => p.id === q.id) || { id: q.id, unidades: [] },
                     valor: q[d.prop], prop: d.prop, nomeProp: m.nomes_propriedades[d.prop], unidade,
                     intervalo: q.intervalo };
    v.scene.add(esf);
    v.marcasProp.push(esf);
    v.marcas.push({ obj: esf, x: v.X(q.x), cota: q.cota, z: v.Z(q.y), prop: true });
  }
  desenharEscala(`${m.nomes_propriedades[d.prop]} — ${unidade}`, lo, hi, d.prop, !grade);
  aplicarExagero();
}

// Com uma propriedade no topo de uma unidade, as outras superfícies ficam translúcidas
// (a escala é azul, e a Jandaíra também: sem isso, uma se confunde com a outra).
function aplicarOpacidade(destaque) {
  const por = (mat, o) => {
    mat.opacity = o;
    mat.transparent = o < 1;
    mat.depthWrite = o >= 0.5;
    mat.needsUpdate = true;
  };
  for (const [chave, m] of Object.entries(v.superficies)) {
    por(m.material, destaque && chave !== destaque ? Math.min(v.opacidade, 0.22) : v.opacidade);
  }
  // bloco fechado: com a seção A–A′, o bloco fica translúcido e a parede, opaca
  const comParede = !!(v.parede && v.parede.linha.length >= 2);
  for (const cam of Object.values(v.camadas)) {
    const o = comParede ? Math.min(v.opacidade, 0.1) : v.opacidade;
    por(cam.corpo.material, o);
    if (cam.tampa) por(cam.tampa.material, o);
    if (cam.parede) por(cam.parede.material, 1);
  }
}

function trocarSuperficie(s, drape) {
  const antigo = v.superficies[s.chave];
  if (!antigo) return;
  const g = v.modelo.grade;
  let geo;
  if (drape) {
    geo = geometriaGrade(s, g, v.X, v.Z);
    const cores = new Float32Array(g.nx * g.ny * 3);
    const neutro = new THREE.Color("#d5d3cc");
    for (let j = 0; j < g.ny; j++) {
      for (let i = 0; i < g.nx; i++) {
        const val = drape.grade[j][i];
        const c = val == null ? neutro : corRampa((val - drape.lo) / (drape.hi - drape.lo));
        cores.set([c.r, c.g, c.b], (j * g.nx + i) * 3);
      }
    }
    geo.setAttribute("color", new THREE.BufferAttribute(cores, 3));
  } else {
    geo = s.malha ? geometriaMalha(s.malha, v.X, v.Z) : geometriaGrade(s, g, v.X, v.Z);
  }
  geo.computeVertexNormals();
  antigo.geometry.dispose();
  antigo.geometry = geo;
  antigo.material.vertexColors = !!drape;
  antigo.material.color.set(drape ? "#ffffff" : s.cor);
  antigo.material.needsUpdate = true;
}

function desenharEscala(titulo, lo, hi, prop, soPocos) {
  if (!v.escala) {
    v.escala = document.createElement("div");
    v.escala.className = "bl-escala";
    v.renderer.domElement.parentElement.appendChild(v.escala);
  }
  v.escala.hidden = false;
  v.escala.textContent = "";
  const t = document.createElement("div");
  t.className = "bl-escala-titulo";
  t.textContent = titulo;
  const barra = document.createElement("div");
  barra.className = "bl-escala-barra";
  barra.style.background = `linear-gradient(to right, ${RAMPA.join(", ")})`;
  const lim = document.createElement("div");
  lim.className = "bl-escala-lim";
  lim.innerHTML = "";
  const a = document.createElement("span"), b = document.createElement("span");
  a.textContent = fmtProp(lo, prop); b.textContent = fmtProp(hi, prop);
  lim.append(a, b);
  v.escala.append(t, barra, lim);
  if (soPocos) {
    const n = document.createElement("div");
    n.className = "bl-escala-nota";
    n.textContent = "menos de 3 poços avaliados: só nos poços";
    v.escala.appendChild(n);
  }
  v.escalaInfo = { titulo, lo, hi, prop, soPocos };
}

function aplicarExagero() {
  v.mundo.scale.set(1, v.exagero / 1000, 1);
  for (const mk of v.marcas) mk.obj.position.set(mk.x, cenaDeY(mk.cota), mk.z);
  desenhar();
}

function projetar(x, cota, z, w, h) {
  const p = new THREE.Vector3(x, cenaDeY(cota), z).project(v.camera);
  return { x: (p.x + 1) / 2 * w, y: (1 - p.y) / 2 * h, visivel: p.z > -1 && p.z < 1 };
}

function atualizarRotulos() {
  const c = v.renderer.domElement, w = c.clientWidth, h = c.clientHeight;
  for (const r of v.rotulos) {
    const oculto = r.tipo === "pino" ? false : r.tipo === "secao" ? v.modo !== "fechado"
      : (r.tipo === "poco" && (!v.mostrarNomes || (v.modo === "fechado" && v.afastar > 0))) ||
        (r.tipo !== "poco" && !v.mostrarCaixa);
    const p = projetar(r.x, r.cota, r.z, w, h);
    r.el.hidden = oculto || !p.visivel;
    r.el.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px)`;
    r.tela = p;
  }
  // seta do norte: direção de −Z na tela
  const a = projetar(0, v.centro.cota, 0, w, h), b = projetar(0, v.centro.cota, -v.lado * 0.3, w, h);
  const ang = Math.atan2(b.x - a.x, -(b.y - a.y)) * 180 / Math.PI;
  if (!Number.isFinite(ang)) return;      // câmera ainda não posicionada
  const rad = ang * Math.PI / 180;
  v.norte.querySelector(".seta").setAttribute("transform", `rotate(${ang.toFixed(1)})`);
  const letra = v.norte.querySelector(".letra");
  letra.setAttribute("x", (24 * Math.sin(rad)).toFixed(1));
  letra.setAttribute("y", (-24 * Math.cos(rad)).toFixed(1));
  v.anguloNorte = ang;
}

function desenhar() {
  if (!v.renderer || !v.modelo) return;
  v.renderer.render(v.scene, v.camera);
  atualizarRotulos();
}

function vista(qual) {
  // enquadra a caixa inteira: o lado horizontal e a altura (com o exagero atual)
  const altura = v.modelo ? (v.cotaMax - v.cotaMin) * v.exagero / 1000 : 0;
  const d = Math.max(v.lado * 1.45, altura * 2.1), t = v.controls.target.set(0, 0, 0);
  const el = { obliqua: 35, cima: 89.9, sul: 6, oeste: 6 }[qual] ?? 35;
  const az = { obliqua: -35, cima: 0, sul: 0, oeste: -90 }[qual] ?? -35;   // graus a partir do sul
  const e = el * Math.PI / 180, a = az * Math.PI / 180;
  v.camera.position.set(t.x + d * Math.cos(e) * Math.sin(a), t.y + d * Math.sin(e), t.z + d * Math.cos(e) * Math.cos(a));
  v.camera.near = d / 2000;
  v.camera.far = d * 100;
  v.camera.updateProjectionMatrix();
  v.controls.update();
  desenhar();
}

function passarMouse(ev) {
  const c = v.renderer.domElement, rc = c.getBoundingClientRect();
  const mouse = new THREE.Vector2(((ev.clientX - rc.left) / rc.width) * 2 - 1, -((ev.clientY - rc.top) / rc.height) * 2 + 1);
  v.raio.setFromCamera(mouse, v.camera);
  let alvos = v.marcas.map((m) => m.obj).filter((o) => o.visible).concat(v.alvosTrilha || []);
  if (v.modo === "fechado") {
    for (const cam of Object.values(v.camadas)) {
      if (!cam.grupo.visible) continue;
      for (const o of [cam.corpo, cam.tampa, cam.parede]) if (o && o.material.opacity >= 0.5) alvos.push(o);
    }
  }
  // o raio também acerta a parte da camada tirada pelo corte (o recorte é só no desenho)
  const hit = v.raio.intersectObjects(alvos, false).find((h) => h.object.userData.tipo !== "camada" ||
    h.object !== v.camadas[h.object.userData.camada.chave].corpo || !noCorte(h.point));
  if (!hit) { v.dica.hidden = true; return; }
  const d = hit.object.userData, p = d.poco;
  if (d.tipo === "pino") {
    const c = d.camada;
    v.dica.textContent = [`Prognóstico · ${c.nome}`, `topo ${fmt(c.topo, 0)} m (${fmt(c.prof_topo, 0)} m abaixo do terreno)` +
      (c.incerteza_m != null ? ` ± ${fmt(c.incerteza_m, 0)} m` : ""), `espessura ${fmt(c.espessura, 0)} m`].join("\n");
    v.dica.style.left = (ev.clientX - rc.left + 12) + "px";
    v.dica.style.top = (ev.clientY - rc.top + 12) + "px";
    v.dica.hidden = false;
    return;
  }
  if (d.tipo === "camada") {
    const linhasC = dicaCamada(d.camada, hit.point, hit.object.parent.position.y);
    v.dica.textContent = linhasC.join("\n");
    v.dica.style.left = (ev.clientX - rc.left + 12) + "px";
    v.dica.style.top = (ev.clientY - rc.top + 12) + "px";
    v.dica.hidden = false;
    return;
  }
  const linhas = [p.id + (p.campo ? ` · ${p.campo}` : "")];
  if (d.tipo === "trilha") {
    linhas.push(`${d.rotulo}: ${fmt(d.a, 1)}–${fmt(d.b, 1)} m (prof. medida)`);
  } else if (d.tipo === "prop") {
    linhas.push(`${d.nomeProp} em ${d.unidade}: ${fmtProp(d.valor, d.prop)}` + (d.intervalo ? ` (intervalo "${d.intervalo}")` : ""));
  } else if (d.tipo === "topo") {
    linhas.push(`${d.unidade.nome}: topo ${fmt(d.unidade.topo, 1)} m · cota ${fmt(d.unidade.cota_topo, 1)} m`);
    const val = v.validacao && v.validacao[`${p.id}|${d.unidade.chave}`];
    if (val) {
      const partes = [];
      if (val.erro_fechado != null) partes.push(`bloco fechado ${fmt(val.fechado, 0)} m (erro ${sinal(val.erro_fechado)} m)`);
      if (val.erro_superficie != null) partes.push(`superfície ${fmt(val.superficie, 0)} m (erro ${sinal(val.erro_superficie)} m)`);
      if (partes.length) linhas.push(`sem este poço: ${partes.join(" · ")}`);
    }
  } else {
    if (p.mesa != null) linhas.push(`mesa rotativa ${fmt(p.mesa, 1)} m`);
    if (p.prof_final) linhas.push(`prof. final ${fmt(p.prof_final, 0)} m` + (p.desviado ? " · desviado" : ""));
    if (p.trajetoria) linhas.push(`trajetória dos dados direcionais · afastamento ${fmt(p.trajetoria.afastamento_m, 0)} m`);
    if (p.avaliacao) linhas.push(`avaliação: ${p.avaliacao}`);
    linhas.push(`${p.unidades.length} topo(s) no AGP`);
  }
  v.dica.textContent = linhas.join("\n");
  v.dica.style.left = (ev.clientX - rc.left + 12) + "px";
  v.dica.style.top = (ev.clientY - rc.top + 12) + "px";
  v.dica.hidden = false;
}

// O ponto (da cena) está no quadrante tirado pelo corte? (o raio pega a parte invisível)
function noCorte(pt) {
  if (!v.corte.ativo || !v.sm) return false;
  const k = geometriaCorte();
  const x = pt.x + v.centro.x, y = v.centro.y - pt.z;
  return (k.oeste ? x < k.cx - 1e-6 : x > k.cx + 1e-6) && (k.sul ? y < k.cy - 1e-6 : y > k.cy + 1e-6);
}

function sinal(n) { return (n > 0 ? "+" : "") + fmt(n, 0); }

// ------------------------------------------------ clique no bloco e pino do prognóstico
function soltou(ev) {
  if (!v.escolher || !v.apertou) return;
  if (Math.hypot(ev.clientX - v.apertou[0], ev.clientY - v.apertou[1]) > 5) return;   // foi giro, não clique
  const c = v.renderer.domElement, rc = c.getBoundingClientRect();
  const mouse = new THREE.Vector2(((ev.clientX - rc.left) / rc.width) * 2 - 1, -((ev.clientY - rc.top) / rc.height) * 2 + 1);
  v.raio.setFromCamera(mouse, v.camera);
  const alvos = [];
  if (v.modo === "fechado") {
    for (const cam of Object.values(v.camadas)) if (cam.grupo.visible) for (const o of [cam.corpo, cam.tampa]) if (o) alvos.push(o);
  } else {
    for (const m of Object.values(v.superficies)) if (m.visible) alvos.push(m);
  }
  const hit = v.raio.intersectObjects(alvos, false).find((h) => !(h.object.userData.camada &&
    h.object === v.camadas[h.object.userData.camada.chave].corpo && noCorte(h.point)));
  let pt = hit && hit.point;
  if (!pt) {        // fora do bloco desenhado: o plano horizontal na cota do topo
    const plano = new THREE.Plane(new THREE.Vector3(0, 1, 0), -cenaDeY(v.cotaMax));
    pt = v.raio.ray.intersectPlane(plano, new THREE.Vector3());
  }
  if (!pt) return;
  const f = v.escolher;
  f({ x: pt.x + v.centro.x, y: v.centro.y - pt.z });
}

function limparPino() {
  if (!v.pino) return;
  v.mundo.remove(v.pino.linha);
  v.pino.linha.geometry.dispose(); v.pino.linha.material.dispose();
  for (const o of v.pino.marcas) { v.scene.remove(o); o.geometry.dispose(); o.material.dispose(); }
  v.marcas = v.marcas.filter((mk) => !mk.pino);
  v.rotulos = v.rotulos.filter((r) => { if (r.tipo === "pino") { r.el.remove(); return false; } return true; });
  v.pino = null;
}

function desenharPino(p) {
  limparPino();
  if (!p) { desenhar(); return; }
  const X = v.X(p.x), Z = v.Z(p.y);
  const topo = p.terreno + (v.cotaMax - v.cotaMin) * 0.06;
  const linha = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(X, topo - v.centro.cota, Z), new THREE.Vector3(X, p.base - v.centro.cota, Z)]),
    new THREE.LineBasicMaterial({ color: 0xc0262d, depthTest: false }));
  linha.renderOrder = 10;
  v.mundo.add(linha);
  const marcas = [];
  const r = v.lado * 0.009;
  for (const c of p.camadas) {
    if (!c.presente) continue;
    const esf = new THREE.Mesh(new THREE.SphereGeometry(r, 14, 10),
                               new THREE.MeshLambertMaterial({ color: c.cor, depthTest: false }));
    esf.renderOrder = 11;
    esf.userData = { tipo: "pino", camada: c };
    v.scene.add(esf);
    marcas.push(esf);
    v.marcas.push({ obj: esf, x: X, cota: c.topo, z: Z, pino: true });
  }
  rotulo("P", X, topo, Z, "pino");
  v.pino = { linha, marcas, dados: p };
  aplicarExagero();
}

function dicaCamada(c, pt, deslocY) {
  const x = pt.x + v.centro.x, y = v.centro.y - pt.z;
  const cota = pt.y / (v.exagero / 1000) - deslocY + v.centro.cota;
  const linhas = [c.nome, `cota ≈ ${fmt(cota, 0)} m · espessura máx. ${fmt(c.espessura_max_m, 0)} m`];
  linhas.push(controlado(c, x, y) ? `entre os ${c.n_espessuras} poço(s) com a espessura medida`
                                  : "extrapolada (fora do contorno dos poços com o dado): valor da borda mais próxima");
  return linhas;
}

// Imagem para exportar: a vista atual em ~2,5× a resolução, com rótulos, norte, legenda e carimbo.
function imagem(meta = {}) {
  const c = v.renderer.domElement, w = c.clientWidth, h = c.clientHeight;
  const fator = 2.5, antes = v.renderer.getPixelRatio();
  v.renderer.setPixelRatio(fator);
  v.renderer.setSize(w, h, false);
  v.renderer.render(v.scene, v.camera);
  const faixa = 150;                      // legenda e carimbo, embaixo (px de tela)
  const out = document.createElement("canvas");
  out.width = Math.round(w * fator);
  out.height = Math.round((h + faixa) * fator);
  const g = out.getContext("2d");
  g.fillStyle = "#fff";
  g.fillRect(0, 0, out.width, out.height);
  g.drawImage(c, 0, 0, out.width, Math.round(h * fator));
  g.scale(fator, fator);
  atualizarRotulos();
  for (const r of v.rotulos) {
    if (r.el.hidden) continue;
    g.font = r.tipo === "poco" ? "600 11px Segoe UI, sans-serif" : r.tipo === "titulo-eixo" ? "italic 11px Segoe UI, sans-serif"
      : "10px Segoe UI, sans-serif";
    g.fillStyle = r.tipo === "poco" ? "#1c2227" : "#5f6b73";
    g.textAlign = r.tipo === "poco" ? "left" : "center";
    g.fillText(r.texto, r.tela.x + (r.tipo === "poco" ? 6 : 0), r.tela.y + (r.tipo === "poco" ? -4 : 4));
  }
  // norte
  const an = (v.anguloNorte || 0) * Math.PI / 180;
  g.save();
  g.translate(w - 42, 42);
  g.beginPath(); g.arc(0, 0, 17, 0, 2 * Math.PI); g.fillStyle = "rgba(255,255,255,.85)"; g.fill();
  g.strokeStyle = "#9aa3a8"; g.stroke();
  g.font = "700 11px sans-serif"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = "#1c2227";
  g.fillText("N", 24 * Math.sin(an), -24 * Math.cos(an));
  g.rotate(an);
  g.beginPath(); g.moveTo(0, -15); g.lineTo(4.5, 0); g.lineTo(-4.5, 0); g.closePath(); g.fill();
  g.beginPath(); g.moveTo(0, 15); g.lineTo(4.5, 0); g.lineTo(-4.5, 0); g.closePath();
  g.fillStyle = "#fff"; g.fill(); g.lineWidth = 1; g.strokeStyle = "#1c2227"; g.stroke();
  g.restore();
  g.textBaseline = "alphabetic";
  if (meta.titulo) {
    g.font = "600 15px Georgia, serif"; g.fillStyle = "#1c2227"; g.textAlign = "left";
    g.fillText(meta.titulo, 14, 22);
  }
  // legenda
  let x = 14, y = h + 22;
  g.textAlign = "left";
  g.font = "600 11px Segoe UI, sans-serif"; g.fillStyle = "#1c2227";
  const fechado = v.modo === "fechado" && v.sm;
  g.fillText(fechado ? "Bloco fechado: unidades (AGP) · mais claro = extrapolado" : "Topos das unidades (AGP)", x, y);
  y += 16;
  g.font = "11px Segoe UI, sans-serif";
  const itensLeg = fechado ? v.modelo.solido.camadas : v.modelo.legenda;
  for (const u of itensLeg) {
    const vis = fechado ? v.visivel[u.chave] !== false : (v.topos[u.chave] || []).some((o) => o.visible);
    if (!vis) continue;
    if (x > w - 160) { x = 14; y += 16; }
    g.fillStyle = u.cor; g.fillRect(x, y - 9, 12, 10);
    g.fillStyle = "#1c2227"; g.fillText(u.nome, x + 17, y);
    x += 22 + g.measureText(u.nome).width + 14;
  }
  const itens = itensTrilha();
  if (itens.length) {
    x = 14; y += 22;
    g.font = "600 11px Segoe UI, sans-serif"; g.fillStyle = "#1c2227";
    g.fillText(v.trilha === "avaliacao" ? "Ao longo dos poços (avaliação de formação)" : "Ao longo dos poços (AGP)", x, y);
    y += 16; g.font = "11px Segoe UI, sans-serif";
    for (const [cor, nome] of itens) {
      g.fillStyle = cor; g.fillRect(x, y - 9, 12, 10);
      g.fillStyle = "#1c2227"; g.fillText(nome, x + 17, y);
      x += 22 + g.measureText(nome).width + 14;
    }
  }
  if (v.escalaInfo && v.escala && !v.escala.hidden) {
    const e = v.escalaInfo, bx = w - 230, by = h + 18;
    g.font = "600 11px Segoe UI, sans-serif"; g.fillStyle = "#1c2227"; g.textAlign = "left";
    g.fillText(e.titulo, bx, by);
    const grad = g.createLinearGradient(bx, 0, bx + 200, 0);
    RAMPA.forEach((c, k) => grad.addColorStop(k / (RAMPA.length - 1), c));
    g.fillStyle = grad; g.fillRect(bx, by + 6, 200, 10);
    g.font = "10.5px Segoe UI, sans-serif"; g.fillStyle = "#5f6b73";
    g.fillText(fmtProp(e.lo, e.prop), bx, by + 30);
    g.textAlign = "right"; g.fillText(fmtProp(e.hi, e.prop), bx + 200, by + 30); g.textAlign = "left";
  }
  const m = v.modelo;
  g.fillStyle = "#5f6b73"; g.font = "10.5px Segoe UI, sans-serif";
  const notas = [
    `${m.pocos.length} poços · contorno dos poços ${fmt(m.area_km2, 1)} km² · exagero vertical ${v.exagero}× · ` +
      `canto SW das distâncias: ${fmt(v.cantoSW.lat, 4)}°, ${fmt(v.cantoSW.lon, 4)}°`,
    fechado
      ? `Contexto espacial: camadas empilhadas por espessura (linear entre os poços; fora deles, o poço mais próximo), ` +
        `do terreno à base plana em ${fmt(m.solido.base, 0)} m.`
      : "Contexto espacial: entre os poços, superfícies interpoladas (linear, só dentro do contorno dos poços que têm a unidade).",
    `Topos: AGP (ANP), interpretação da operadora · ${meta.versao ? "SIAPP " + meta.versao : "SIAPP"}` +
      (meta.autor ? ` · ${meta.autor}` : "") + ` · ${new Date().toLocaleDateString("pt-BR")}`,
  ];
  notas.forEach((t, k) => g.fillText(t, 14, h + faixa - 46 + k * 15));
  const url = out.toDataURL("image/png");
  v.renderer.setPixelRatio(antes);
  v.renderer.setSize(w, h, false);
  desenhar();
  return url;
}

window.BlocoVisor = {
  mostrar(container, modelo, op = {}) {
    iniciar(container);
    v.modelo = modelo;
    v.exagero = op.exagero || 10;
    v.opacidade = op.opacidade ?? 0.85;
    v.mostrarNomes = op.nomes !== false;
    v.mostrarCaixa = op.caixa !== false;
    v.trilha = op.trilha || "nenhuma";
    if (op.aparencia) v.aparencia = aparenciaCompleta(op.aparencia);
    v.drape = op.drape || null;
    v.drapeAnterior = null;
    v.modo = op.modo || "superficies";
    v.corte = { ativo: false, quadrante: "SW", fx: 0.5, fy: 0.5, ...(op.corte || {}) };
    v.afastar = op.afastar || 0;
    v.parede = null;
    v.visivel = {};
    montarCena(modelo);
    aplicarPorCima();
    if (v.afastar) aplicarAfastar();
    redimensionar();
    vista("obliqua");
  },
  exagero(n) { v.exagero = n; if (v.modelo) aplicarExagero(); },
  opacidade(o) { v.opacidade = o; aplicarOpacidade(v.drape && v.drape.chave); desenhar(); },
  unidade(chave, visivel) {
    v.visivel[chave] = visivel;
    if (v.superficies[chave]) v.superficies[chave].visible = visivel && v.modo !== "fechado";
    aplicarVisibilidade();
    desenhar();
  },
  // "superficies" ou "fechado" (false se o modelo não tem bloco fechado)
  modo(qual) {
    v.modo = qual;
    if (v.modelo) aplicarModo();
    return !!v.sm;
  },
  corte(op) { Object.assign(v.corte, op); if (v.sm) desenharTampas(); },
  afastar(f) { v.afastar = f; aplicarAfastar(); },
  // seção A–A′: ids dos poços (na ordem da seção); devolve quantos estão no bloco
  parede(ids) {
    const pocos = (ids || []).map((id) => v.modelo.pocos.find((p) => p.id === id)).filter(Boolean);
    v.parede = pocos.length >= 2 ? { linha: pocos.map((p) => [p.x, p.y]), pocos: pocos.map((p) => p.id) } : null;
    desenharParede();
    desenhar();
    return pocos.length;
  },
  nomes(sim) { v.mostrarNomes = sim; desenhar(); },
  caixa(sim) { v.mostrarCaixa = sim; if (v.caixa) v.caixa.visible = sim; desenhar(); },
  vista,
  imagem,
  // validação cruzada: as linhas, para a dica nos topos dos poços
  validacao(val) {
    v.validacao = val ? Object.fromEntries(val.linhas.map((l) => [`${l.poco}|${l.chave}`, l])) : null;
  },
  pino: desenharPino,
  // modo clique: chama f({x, y}) no próximo clique (sem arrastar) sobre o bloco; null desliga
  escolherPonto(f) {
    v.escolher = f || null;
    if (v.renderer) v.renderer.domElement.classList.toggle("escolhendo", !!f);
  },
  vistaAtual() {
    const visiveis = v.modelo.legenda.map((u) => u.chave).filter((k) => v.visivel[k] !== false);
    return { azimute: v.controls.getAzimuthalAngle(), elevacao: Math.PI / 2 - v.controls.getPolarAngle(),
             exagero: v.exagero, visiveis, trilha: v.trilha, drape: v.drape, opacidade: v.opacidade,
             aparencia: v.aparencia,
             nomes: v.mostrarNomes, modo: v.modo,
             camadas: Object.keys(v.camadas).filter((k) => v.visivel[k] !== false),
             corte: v.corte.ativo ? { ...v.corte } : null, afastar: v.afastar,
             parede: v.parede ? v.parede.pocos : null };
  },
  trilha(modo) { v.trilha = modo; if (v.modelo) { desenharTrilhas(); desenhar(); } },
  // aparência dos poços: vale na hora, sem montar de novo
  aparencia(ap) {
    v.aparencia = aparenciaCompleta(ap);
    if (!v.modelo) return;
    desenharPocos(v.modelo);
    desenharTrilhas();
    aplicarPorCima();
    aplicarVisibilidade();
    aplicarExagero();
  },
  itensTrilha: () => (v.modelo ? itensTrilha() : []),
  drape(chave, prop) { v.drape = chave ? { chave, prop } : null; if (v.modelo) aplicarDrape(); },
  estado() {
    return { superficies: Object.keys(v.superficies).length, pocos: v.modelo ? v.modelo.pocos.length : 0,
             rotulos: v.rotulos.filter((r) => !r.el.hidden).length, exagero: v.exagero,
             trilhas: (v.alvosTrilha || []).length, drape: v.drapeAnterior, modo: v.modo,
             marcadores: v.marcas.filter((q) => q.doPoco && !q.topo).length,
             forma: v.aparencia.marcador.forma, porCima: emCima(),
             camadas: Object.keys(v.camadas).length,
             tampas: Object.values(v.camadas).filter((c) => c.tampa).length,
             paredes: Object.values(v.camadas).filter((c) => c.parede).length,
             pino: v.pino ? v.pino.marcas.length : 0, escolhendo: !!v.escolher,
             escala: v.escala && !v.escala.hidden ? v.escala.textContent : "" };
  },
};
