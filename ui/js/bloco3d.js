// SIAPP — visor 3D do bloco (three.js, em ui/vendor/three). O modelo vem pronto do motor
// (motor/bloco.py): poços em km num plano local e superfícies de topo numa grade.
// Eixos da cena: X = leste (km), Z = −norte (km), Y = cota (m) × exagero / 1000.
import * as THREE from "three";
import { OrbitControls } from "../vendor/three/OrbitControls.js";

const v = {
  renderer: null, scene: null, camera: null, controls: null, caixa: null, modelo: null,
  mundo: null,          // grupo escalado no Y (superfícies, linhas dos poços, caixa)
  marcas: [],           // {obj, cota} — esferas e discos, posicionados à mão (não esticam)
  rotulos: [],          // {el, pos: Vector3 em coordenadas do mundo sem exagero (Y em m), tipo}
  superficies: {},      // chave → Mesh
  topos: {},            // chave → [Mesh]
  exagero: 10, opacidade: 0.85, mostrarNomes: true, mostrarCaixa: true,
  centro: { x: 0, y: 0, cota: 0 }, lado: 1, overlay: null, norte: null, dica: null, raio: null,
};

function cenaDeY(cota) { return (cota - v.centro.cota) * v.exagero / 1000; }

function limparCena() {
  if (!v.scene) return;
  v.scene.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
  });
  while (v.scene.children.length) v.scene.remove(v.scene.children[0]);
  v.marcas = []; v.rotulos = []; v.superficies = {}; v.topos = {};
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
  v.centro = { x: g.x0 + (g.nx - 1) * g.passo / 2, y: g.y0 + (g.ny - 1) * g.passo / 2,
               cota: (m.cota_max + m.cota_min) / 2 };
  v.lado = Math.max((g.nx - 1) * g.passo, (g.ny - 1) * g.passo, 0.5);
  const X = (x) => x - v.centro.x, Z = (y) => -(y - v.centro.y);

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
  desenharPocosECaixa(m, g, X, Z);
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

function desenharPocosECaixa(m, g, X, Z) {

  // poços: linha da mesa ao fundo; esfera na cabeça; disco em cada topo
  const r = v.lado * 0.006;
  const geoCabeca = new THREE.SphereGeometry(r * 1.3, 12, 8);
  const geoTopo = new THREE.CylinderGeometry(r * 1.6, r * 1.6, r * 0.5, 16);
  const matCabeca = new THREE.MeshLambertMaterial({ color: 0x1c2227 });
  const matLinha = new THREE.LineBasicMaterial({ color: 0x3a4148 });
  for (const p of m.pocos) {
    const cotas = p.unidades.flatMap((u) => [u.cota_topo, u.cota_base]);
    const topo = p.mesa ?? Math.max(...cotas, 0);
    const fundo = p.cota_fundo ?? Math.min(...cotas, topo - 10);
    const lg = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(X(p.x), topo - v.centro.cota, Z(p.y)), new THREE.Vector3(X(p.x), fundo - v.centro.cota, Z(p.y))]);
    v.mundo.add(new THREE.Line(lg, matLinha));
    const cab = new THREE.Mesh(geoCabeca, matCabeca);
    cab.userData = { tipo: "poco", poco: p };
    v.scene.add(cab);
    v.marcas.push({ obj: cab, x: X(p.x), cota: topo, z: Z(p.y) });
    rotulo(p.id, X(p.x), topo, Z(p.y), "poco");
    for (const u of p.unidades) {
      const disco = new THREE.Mesh(geoTopo, new THREE.MeshLambertMaterial({ color: u.cor }));
      disco.userData = { tipo: "topo", poco: p, unidade: u };
      v.scene.add(disco);
      v.marcas.push({ obj: disco, x: X(p.x), cota: u.cota_topo, z: Z(p.y) });
      (v.topos[u.chave] = v.topos[u.chave] || []).push(disco);
    }
  }

  // caixa com marcas: distância (km) a partir do canto SW e cota (m)
  v.caixa = new THREE.Group();
  v.mundo.add(v.caixa);
  const x0 = X(g.x0), x1 = X(g.x0 + (g.nx - 1) * g.passo);
  const z0 = Z(g.y0), z1 = Z(g.y0 + (g.ny - 1) * g.passo);        // z0 = sul (frente), z1 = norte
  const passoC = passoBonito(m.cota_max - m.cota_min || 100);
  const c0 = Math.floor(m.cota_min / passoC) * passoC, c1 = Math.ceil(m.cota_max / passoC) * passoC;
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
  aplicarExagero();
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
    const oculto = (r.tipo === "poco" && !v.mostrarNomes) || (r.tipo !== "poco" && !v.mostrarCaixa);
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
  const d = v.lado * 1.45, t = v.controls.target.set(0, 0, 0);
  const el = { obliqua: 35, cima: 89.9, sul: 6, oeste: 6 }[qual] ?? 35;
  const az = { obliqua: -35, cima: 0, sul: 0, oeste: -90 }[qual] ?? -35;   // graus a partir do sul
  const e = el * Math.PI / 180, a = az * Math.PI / 180;
  v.camera.position.set(t.x + d * Math.cos(e) * Math.sin(a), t.y + d * Math.sin(e), t.z + d * Math.cos(e) * Math.cos(a));
  v.camera.near = v.lado / 1000;
  v.camera.far = v.lado * 100;
  v.camera.updateProjectionMatrix();
  v.controls.update();
  desenhar();
}

function passarMouse(ev) {
  const c = v.renderer.domElement, rc = c.getBoundingClientRect();
  const mouse = new THREE.Vector2(((ev.clientX - rc.left) / rc.width) * 2 - 1, -((ev.clientY - rc.top) / rc.height) * 2 + 1);
  v.raio.setFromCamera(mouse, v.camera);
  const alvos = v.marcas.map((m) => m.obj).filter((o) => o.visible);
  const hit = v.raio.intersectObjects(alvos, false)[0];
  if (!hit) { v.dica.hidden = true; return; }
  const d = hit.object.userData, p = d.poco;
  const linhas = [p.id + (p.campo ? ` · ${p.campo}` : "")];
  if (d.tipo === "topo") {
    linhas.push(`${d.unidade.nome}: topo ${fmt(d.unidade.topo, 1)} m · cota ${fmt(d.unidade.cota_topo, 1)} m`);
  } else {
    if (p.mesa != null) linhas.push(`mesa rotativa ${fmt(p.mesa, 1)} m`);
    if (p.prof_final) linhas.push(`prof. final ${fmt(p.prof_final, 0)} m` + (p.desviado ? " · desviado" : ""));
    linhas.push(`${p.unidades.length} topo(s) no AGP`);
  }
  v.dica.textContent = linhas.join("\n");
  v.dica.style.left = (ev.clientX - rc.left + 12) + "px";
  v.dica.style.top = (ev.clientY - rc.top + 12) + "px";
  v.dica.hidden = false;
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
  g.fillText("Topos das unidades (AGP)", x, y);
  y += 16;
  g.font = "11px Segoe UI, sans-serif";
  for (const u of v.modelo.legenda) {
    const vis = (v.topos[u.chave] || []).some((o) => o.visible);
    if (!vis) continue;
    if (x > w - 160) { x = 14; y += 16; }
    g.fillStyle = u.cor; g.fillRect(x, y - 9, 12, 10);
    g.fillStyle = "#1c2227"; g.fillText(u.nome, x + 17, y);
    x += 22 + g.measureText(u.nome).width + 14;
  }
  const m = v.modelo;
  g.fillStyle = "#5f6b73"; g.font = "10.5px Segoe UI, sans-serif";
  const notas = [
    `${m.pocos.length} poços · contorno dos poços ${fmt(m.area_km2, 1)} km² · exagero vertical ${v.exagero}× · ` +
      `canto SW das distâncias: ${fmt(v.cantoSW.lat, 4)}°, ${fmt(v.cantoSW.lon, 4)}°`,
    "Contexto espacial: entre os poços, superfícies interpoladas (linear, só dentro do contorno dos poços que têm a unidade).",
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
    montarCena(modelo);
    redimensionar();
    vista("obliqua");
  },
  exagero(n) { v.exagero = n; if (v.modelo) aplicarExagero(); },
  opacidade(o) {
    v.opacidade = o;
    for (const m of Object.values(v.superficies)) { m.material.opacity = o; m.material.transparent = o < 1; m.material.needsUpdate = true; }
    desenhar();
  },
  unidade(chave, visivel) {
    if (v.superficies[chave]) v.superficies[chave].visible = visivel;
    for (const d of v.topos[chave] || []) d.visible = visivel;
    desenhar();
  },
  nomes(sim) { v.mostrarNomes = sim; desenhar(); },
  caixa(sim) { v.mostrarCaixa = sim; if (v.caixa) v.caixa.visible = sim; desenhar(); },
  vista,
  imagem,
  estado() {
    return { superficies: Object.keys(v.superficies).length, pocos: v.modelo ? v.modelo.pocos.length : 0,
             rotulos: v.rotulos.filter((r) => !r.el.hidden).length, exagero: v.exagero };
  },
};
