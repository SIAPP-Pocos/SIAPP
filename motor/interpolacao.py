"""Métodos de interpolação do bloco: linear, inverso da distância, spline de placa fina,
krigagem ordinária e tendência + krigagem.

Todos seguem o mesmo contrato, para o bloco (superfícies, bloco fechado, propriedades), a
validação cruzada e o prognóstico usarem o mesmo método:

    aj = ajustar(cfg, obs)            # obs = [(x km, y km, valor, poço, …)]
    aj.valores(x, y)                  # vetorizado, em qualquer ponto
    aj.grade(grade)                   # (z ny × nx, controle) — controle = dentro do contorno dos dados
    aj.valor(x, y, sem_poco=None)     # (valor, dentro do contorno, distância ao dado mais próximo)

`sem_poco` é o "deixar um poço de fora": cada método sabe tirar um poço sem refazer tudo —
o linear refaz só a estrela do ponto na triangulação; spline e krigagem (forma dual)
atualizam os coeficientes pelo inverso da matriz (Dubrule, 1983; Rippa, 1999), em O(n); o
inverso da distância só ignora o ponto. Os testes conferem cada um com o ajuste refeito do
zero sem o poço.

Fora do contorno dos dados (extrapolado): o linear usa o valor da borda; os outros, o
próprio valor, limitado a 10% além da faixa dos dados (spline extrapolada diverge).

Só numpy. Pontos repetidos (mesma posição ao milímetro) entram uma vez, com a média.
"""

from __future__ import annotations

import math

import numpy as np

from . import bloco as mbl

CAMPOS = ("estrutura", "espessura", "propriedades")
# Como o bloco fechado empilha as camadas:
#  - espessuras: um limite de referência + espessuras (isópacas) — nunca cruza; o erro das
#    espessuras se soma longe da referência;
#  - topos: cada limite interpolado direto dos poços e cortado para não passar acima do de
#    cima — o erro não se acumula; onde dois topos se cruzariam, a camada acunha.
EMPILHAMENTOS = ("espessuras", "topos")
METODOS = ("linear", "idw", "spline", "krigagem", "tendencia")
MODELOS_VARIOGRAMA = ("esferico", "exponencial", "gaussiano")
MIN_KRIGAGEM = 8                # menos poços que isso: variograma sem sentido → linear, com aviso

# Textos da janela (uma fonte só: a ponte manda para a interface)
INFO = [
    {"id": "linear", "nome": "Linear (triângulos)",
     "resumo": "Passa exatamente nos poços e nunca inventa um alto ou um baixo além dos dados; a superfície "
               "fica facetada, com quinas nos poços. O mais honesto com poucos poços.",
     "quando": "poucos poços, campos densos, controle de qualidade, rifte com falhas (o menos ruim)"},
    {"id": "idw", "nome": "Inverso da distância (IDW)",
     "resumo": "Média dos poços vizinhos pesada pela distância: exato nos poços, faz \"olhos de boi\" em volta "
               "de cada um e fica plano entre eles. Potência maior = mais local.",
     "quando": "olhada rápida, propriedades (φ, N/G); fraco para topo estrutural"},
    {"id": "spline", "nome": "Spline de placa fina (mínima curvatura)",
     "resumo": "A superfície mais lisa que passa pelos poços; pode passar do alto ou do baixo entre poços "
               "distantes. Suavidade 0 = exata nos poços; maior = aceita errar no poço para ficar lisa "
               "(filtra topo mal marcado). \"Auto\" escolhe pela validação cruzada.",
     "quando": "estruturas contínuas, dobras suaves, leques; evite na espessura (inventa picos)"},
    {"id": "krigagem", "nome": "Krigagem ordinária",
     "resumo": "Usa a correlação espacial medida nos próprios poços (variograma: alcance = até onde um poço "
               "\"influencia\"; pepita = ruído/suavização) e dá o mapa de incerteza. Anisotropia: direção e "
               "razão de alcance (canais, leques). Precisa de 20+ poços para um variograma confiável.",
     "quando": "muitos poços, sistemas com direção (fluvial, leque), escala de bacia"},
    {"id": "tendencia", "nome": "Tendência + krigagem",
     "resumo": "Tira primeiro o mergulho regional (um plano ou uma superfície de 2º grau) e kriga só o que "
               "sobra. Separa a estrutura regional da variação local.",
     "quando": "bacia, com mergulho regional para o depocentro; carbonato de plataforma"},
]
PARAMETROS_INFO = {
    "empilhamento": "Bloco fechado. Por espessuras: um topo de referência + as espessuras (isópacas) de cada "
                    "camada — nunca cruza, mas o erro das espessuras se soma longe da referência. Topo a topo: "
                    "cada topo direto dos poços, cortado para não passar acima do de cima — o erro não se acumula "
                    "(melhor com spline e krigagem).",
    "suavidade": "0 = passa exatamente nos poços; 1 = bem lisa. Vazio = automático (spline: pela validação "
                 "cruzada; krigagem: a pepita do variograma ajustado).",
    "potencia": "IDW: 1 = suave e regional; 3 ou mais = cada poço domina em volta dele.",
    "vizinhos": "IDW: quantos poços entram em cada ponto (0 = todos).",
    "modelo": "Krigagem: a forma do variograma — esférico (o usual), exponencial (mais irregular), gaussiano "
              "(mais liso, pode oscilar). Auto = o que melhor ajusta entre esférico e exponencial.",
    "alcance_km": "Krigagem: distância a partir da qual dois poços não se parecem mais. Vazio = ajustado.",
    "azimute": "Krigagem: direção de maior continuidade (graus a partir do norte, ex.: a do aporte de "
               "sedimento).",
    "razao": "Krigagem: alcance na direção perpendicular ÷ alcance na direção do azimute (1 = sem "
             "anisotropia; 0,3 = três vezes mais contínuo na direção do azimute).",
    "grau": "Tendência: 1 = plano (mergulho regional); 2 = superfície curva (bacia em forma de prato).",
}
PADRAO = {"metodo": "linear", "suavidade": None, "potencia": 2.0, "vizinhos": 12, "modelo": "auto",
          "alcance_km": None, "azimute": 0.0, "razao": 1.0, "grau": 1}

# Escala do modelo: ponto de partida (a janela preenche o formulário; tudo continua editável).
# Escolhidos pela validação cruzada em dois casos reais (docs/bloco.md, "Interpolação e escala"):
# num campo (14 poços) a spline topo a topo errou 26% menos que a linear no bloco fechado; no
# regional (≈2000 poços) ficou a 5% da linear, e tendência + krigagem empatou nas superfícies e
# dá o mapa de incerteza.
ESCALAS = {
    "reservatorio": {
        "nome": "Reservatório (um campo)",
        "resumo": "Poucos poços, área pequena e fechada: sem margem, grade fina, spline (a superfície mais lisa "
                  "que passa nos poços) topo a topo. Com menos de 8 poços a krigagem não tem variograma.",
        "selecao": "campo", "margem_km": 0.0, "celulas": 160, "dist_max_km": None,
        "interpolacao": {"estrutura": {"metodo": "spline", "suavidade": None},
                         "espessura": {"metodo": "spline", "suavidade": None},
                         "propriedades": {"metodo": "idw"}, "empilhamento": "topos"},
    },
    "bacia": {
        "nome": "Bacia (regional)",
        "resumo": "Muitos poços espalhados: mergulho regional (tendência) + krigagem do resto, com o mapa de "
                  "incerteza; esconde o que está a mais de 15 km de um poço; grade mais grossa.",
        "selecao": "todos", "margem_km": 0.0, "celulas": 120, "dist_max_km": 15.0,
        "interpolacao": {"estrutura": {"metodo": "tendencia", "grau": 1},
                         "espessura": {"metodo": "krigagem"},
                         "propriedades": {"metodo": "krigagem"}, "empilhamento": "topos"},
    },
}


class ErroInterpolacao(Exception):
    pass


# ============================================================== configuração
def configuracao(cfg: dict | None) -> dict:
    """{campo: {metodo, parâmetros}} completo. Aceita {'estrutura': 'krigagem', …} ou com
    parâmetros comuns em `parametros`."""
    cfg = dict(cfg or {})
    comuns = dict(cfg.pop("parametros", {}) or {})
    empilhamento = cfg.pop("empilhamento", None) or comuns.pop("empilhamento", None) or "espessuras"
    if empilhamento not in EMPILHAMENTOS:
        raise ErroInterpolacao(f"Empilhamento desconhecido: {empilhamento}")
    out = {"empilhamento": empilhamento}
    for campo in CAMPOS:
        v = cfg.get(campo) or {}
        if isinstance(v, str):
            v = {"metodo": v}
        c = dict(PADRAO)
        c.update({k: x for k, x in comuns.items() if x not in (None, "")})
        c.update({k: x for k, x in v.items() if x not in (None, "") or k == "suavidade"})
        if c["metodo"] not in METODOS:
            raise ErroInterpolacao(f"Método desconhecido: {c['metodo']}")
        if c["modelo"] not in ("auto",) + MODELOS_VARIOGRAMA:
            raise ErroInterpolacao(f"Modelo de variograma desconhecido: {c['modelo']}")
        for k in ("suavidade", "potencia", "alcance_km", "azimute", "razao"):
            if c.get(k) not in (None, ""):
                c[k] = float(str(c[k]).replace(",", "."))
        c["vizinhos"] = int(float(c.get("vizinhos") or 0))
        c["grau"] = int(float(c.get("grau") or 1))
        if c["suavidade"] is not None and not 0 <= c["suavidade"] <= 1:
            raise ErroInterpolacao("Suavidade entre 0 e 1.")
        if not 0.05 <= c["razao"] <= 1:
            raise ErroInterpolacao("Razão de anisotropia entre 0,05 e 1.")
        if c["grau"] not in (1, 2):
            raise ErroInterpolacao("Grau da tendência: 1 ou 2.")
        out[campo] = c
    return out


def nome(cfg_campo: dict) -> str:
    return next(i["nome"] for i in INFO if i["id"] == cfg_campo["metodo"])


# ============================================================== base comum
def unicos(pts, valores) -> tuple[np.ndarray, np.ndarray]:
    """Pontos repetidos (mesma posição, ao milímetro) viram um só, com a média dos valores."""
    pts, valores = np.asarray(pts, float).reshape(-1, 2), np.asarray(valores, float)
    if len(pts) == 0:
        return pts, valores
    grupos: dict = {}
    for i, (a, b) in enumerate(pts):
        grupos.setdefault((round(float(a), 6), round(float(b), 6)), []).append(i)
    if len(grupos) == len(pts):
        return pts, valores
    ids = list(grupos.values())
    return np.array([pts[g[0]] for g in ids]), np.array([float(np.mean(valores[g])) for g in ids])


def _nos(grade: dict):
    return np.meshgrid(grade["x0"] + grade["passo"] * np.arange(grade["nx"]),
                       grade["y0"] + grade["passo"] * np.arange(grade["ny"]))


def pela_borda(pts, valores, h, x, y) -> np.ndarray:
    """Valor no ponto mais próximo da borda do contorno convexo `h` (linear entre os dois
    pontos da aresta). `pts` sem repetidos."""
    val = {(round(float(a), 9), round(float(b), 9)): v for (a, b), v in zip(pts, valores)}
    vh = np.array([val[(round(float(a), 9), round(float(b), 9))] for a, b in h])
    x, y = np.asarray(x, float), np.asarray(y, float)
    melhor = np.full(x.shape, np.inf)
    out = np.zeros(x.shape)
    for k in range(len(h)):
        a, b = h[k], h[(k + 1) % len(h)]
        d = b - a
        L2 = float(d @ d)
        t = np.clip(((x - a[0]) * d[0] + (y - a[1]) * d[1]) / L2, 0, 1) if L2 > 0 else np.zeros(x.shape)
        dist = np.hypot(a[0] + t * d[0] - x, a[1] + t * d[1] - y)
        m = dist < melhor
        melhor[m] = dist[m]
        out[m] = ((1 - t) * vh[k] + t * vh[(k + 1) % len(h)])[m]
    return out


def linear_grade(pts, valores, grade: dict) -> np.ndarray:
    """Interpolação linear nos triângulos, olhando só os nós da caixa de cada triângulo; NaN fora."""
    x0, y0, p, nx, ny = grade["x0"], grade["y0"], grade["passo"], grade["nx"], grade["ny"]
    tris = mbl.delaunay(pts)
    z = np.full((ny, nx), np.nan)
    for t in tris:
        (ax, ay), (bx, by), (cx, cy) = pts[t]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-15:
            continue
        i0 = max(0, int(math.floor((min(ax, bx, cx) - x0) / p)))
        i1 = min(nx - 1, int(math.ceil((max(ax, bx, cx) - x0) / p)))
        j0 = max(0, int(math.floor((min(ay, by, cy) - y0) / p)))
        j1 = min(ny - 1, int(math.ceil((max(ay, by, cy) - y0) / p)))
        if i1 < i0 or j1 < j0:
            continue
        X, Y = np.meshgrid(x0 + p * np.arange(i0, i1 + 1), y0 + p * np.arange(j0, j1 + 1))
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / det
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / det
        l3 = 1 - l1 - l2
        ok = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        sub = z[j0:j1 + 1, i0:i1 + 1]
        ok &= np.isnan(sub)
        sub[ok] = (l1 * valores[t[0]] + l2 * valores[t[1]] + l3 * valores[t[2]])[ok]
    return z


def no_triangulo(x, y, pts, val, tris) -> float | None:
    """Valor linear no triângulo que contém (x, y), ou None."""
    if len(tris) == 0:
        return None
    a, b, c = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(det) > 1e-15
    det = np.where(ok, det, 1.0)
    l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / det
    l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / det
    l3 = 1 - l1 - l2
    idx = np.flatnonzero(ok & (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9))
    if not len(idx):
        return None
    t = idx[0]
    return float(l1[t] * val[tris[t, 0]] + l2[t] * val[tris[t, 1]] + l3[t] * val[tris[t, 2]])


class _Base:
    """Nós únicos (média dos repetidos), poços por nó, contorno — o comum a todos."""

    metodo = "linear"

    def __init__(self, obs: list, cfg: dict | None = None):
        self.cfg = dict(PADRAO, **(cfg or {}))
        self.obs = list(obs)
        grupos: dict = {}
        for i, o in enumerate(self.obs):
            grupos.setdefault((round(float(o[0]), 6), round(float(o[1]), 6)), []).append(i)
        self.membros = list(grupos.values())
        self.pts = np.array([[self.obs[g[0]][0], self.obs[g[0]][1]] for g in self.membros], float).reshape(-1, 2)
        self.val = np.array([np.mean([self.obs[i][2] for i in g]) for g in self.membros], float)
        self.no_da_obs = {i: k for k, g in enumerate(self.membros) for i in g}
        self.por_poco: dict = {}
        for i, o in enumerate(self.obs):
            self.por_poco.setdefault(o[3], []).append(i)
        m = len(self.pts)
        self.hull = mbl.contorno_convexo(self.pts) if m else np.zeros((0, 2))
        self.espacial = m >= 3 and len(self.hull) >= 3 and mbl.largura_relativa(self.hull) >= mbl.FRACAO_COLINEAR
        chaves = {(round(float(a), 9), round(float(b), 9)) for a, b in self.hull}
        self.no_hull = {k for k, (a, b) in enumerate(self.pts) if (round(float(a), 9), round(float(b), 9)) in chaves}
        if m:
            lo, hi = float(self.val.min()), float(self.val.max())
            folga = 0.1 * (hi - lo)
            self.faixa = (lo - folga, hi + folga)
        self._hull_sem: dict = {}
        self.avisos: list[str] = []
        self.info: dict = {}

    def __len__(self):
        return len(self.obs)

    def descricao(self) -> str:
        return nome({"metodo": self.metodo})

    # ------------------------------------------------ tirar um poço
    def _tirar(self, sem_poco):
        """(nós esvaziados, {nó: novo valor}) sem as observações do poço."""
        tirar = set(self.por_poco.get(sem_poco, [])) if sem_poco is not None else set()
        vazios, novos = [], {}
        for k in {self.no_da_obs[i] for i in tirar}:
            resto = [i for i in self.membros[k] if i not in tirar]
            if resto:
                novos[k] = float(np.mean([self.obs[i][2] for i in resto]))
            else:
                vazios.append(k)
        return vazios, novos

    def _hull_sem_no(self, r):
        if r not in self.no_hull:
            return self.hull
        if r not in self._hull_sem:
            vivos = [k for k in range(len(self.pts)) if k != r]
            self._hull_sem[r] = mbl.contorno_convexo(self.pts[vivos])
        return self._hull_sem[r]

    def _dentro_dist(self, x, y, vivos, hull):
        pts = self.pts[vivos]
        dist = float(np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y))) if len(pts) else math.inf
        dentro = len(hull) >= 3 and bool(mbl.dentro(hull, np.array([x]), np.array([y]))[0])
        return dentro, dist

    def grade(self, grade: dict) -> tuple[np.ndarray, np.ndarray]:
        gx, gy = _nos(grade)
        z = self.valores(gx, gy)
        controle = mbl.dentro(self.hull, gx, gy) if self.espacial else np.zeros(gx.shape, bool)
        return z, controle

    def _limitar(self, z, x, y, hull=None):
        """Fora do contorno, o valor fica dentro da faixa dos dados + 10%."""
        hull = self.hull if hull is None else hull
        z = np.asarray(z, float)
        if len(hull) < 3:
            return np.clip(z, *self.faixa)
        fora = ~mbl.dentro(hull, np.asarray(x, float), np.asarray(y, float))
        return np.where(fora, np.clip(z, *self.faixa), z)


# ============================================================== linear
class Linear(_Base):
    """Linear nos triângulos de Delaunay; fora, o valor da borda (o método da 0.18–0.22)."""

    metodo = "linear"

    def __init__(self, obs, cfg=None):
        super().__init__(obs, cfg)
        self.tris = mbl.delaunay(self.pts) if self.espacial else np.zeros((0, 3), int)
        self.incid: dict = {}
        for t, tri in enumerate(self.tris):
            for v in tri:
                self.incid.setdefault(int(v), []).append(t)
        self._cache: dict = {}

    def valores(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        if not len(self.pts):
            return np.full(x.shape, np.nan)
        if self.espacial:
            if x.ndim == 2:
                g = {"x0": float(x[0, 0]), "y0": float(y[0, 0]), "nx": x.shape[1], "ny": x.shape[0],
                     "passo": float(x[0, 1] - x[0, 0]) if x.shape[1] > 1 else 1.0}
                z = linear_grade(self.pts, self.val, g)
            else:
                z = np.array([v if (v := no_triangulo(a, b, self.pts, self.val, self.tris)) is not None else np.nan
                              for a, b in zip(x.ravel(), y.ravel())]).reshape(x.shape)
            falta = np.isnan(z)
            if falta.any():
                z[falta] = pela_borda(self.pts, self.val, self.hull, x[falta], y[falta])
            return z
        _, k = mbl.distancia_mais_proximo(self.pts, x, y)
        return self.val[k]

    def valor(self, x, y, sem_poco=None):
        if not len(self.pts):
            return None, False, math.inf
        vazios, novos = self._tirar(sem_poco)
        val = self.val.copy()
        for k, v in novos.items():
            val[k] = v
        vivos = [k for k in range(len(self.pts)) if k not in vazios]
        if not vivos:
            return None, False, math.inf
        if not vazios:
            return self._avaliar(x, y, self.pts, val, self.tris, self.hull, self.espacial, vivos)
        if len(vazios) > 1 or not self.espacial:
            return self._refeito(x, y, vivos, val)
        r = vazios[0]
        est = self._sem_no(r)
        if est is None:
            return self._refeito(x, y, vivos, val)
        pts_v, hull_v, manter, viz, tl = est
        dist = float(np.min(np.hypot(pts_v[:, 0] - x, pts_v[:, 1] - y)))
        dentro = bool(mbl.dentro(hull_v, np.array([x]), np.array([y]))[0])
        v = no_triangulo(x, y, self.pts, val, self.tris[manter])
        if v is not None:
            return v, True, dist
        if dentro:
            v = no_triangulo(x, y, self.pts[viz], val[viz], tl)
            if v is not None:
                return v, True, dist
            return self._refeito(x, y, vivos, val)
        return float(pela_borda(pts_v, val[vivos], hull_v, np.array([x]), np.array([y]))[0]), False, dist

    def _sem_no(self, r):
        if r in self._cache:
            return self._cache[r]
        vivos = [k for k in range(len(self.pts)) if k != r]
        pts_v = self.pts[vivos]
        hull_v = self._hull_sem_no(r)
        if len(vivos) < 3 or len(hull_v) < 3 or (r in self.no_hull and
                                                 mbl.largura_relativa(hull_v) < mbl.FRACAO_COLINEAR):
            est = None
        else:
            estrela = self.incid.get(r, [])
            manter = np.ones(len(self.tris), bool)
            manter[estrela] = False
            viz = sorted({int(u) for t in estrela for u in self.tris[t]} - {r})
            est = (pts_v, hull_v, manter, viz, mbl.delaunay(self.pts[viz]))
        self._cache[r] = est
        return est

    def _avaliar(self, x, y, pts, val, tris, hull, linear, nos):
        nos = list(nos)
        dist = float(np.min(np.hypot(pts[nos, 0] - x, pts[nos, 1] - y)))
        if linear:
            v = no_triangulo(x, y, pts, val, tris)
            if v is not None:
                return v, True, dist
            return float(pela_borda(pts[nos], val[nos], hull, np.array([x]), np.array([y]))[0]), False, dist
        k = nos[int(np.argmin(np.hypot(pts[nos, 0] - x, pts[nos, 1] - y)))]
        return float(val[k]), False, dist

    def _refeito(self, x, y, vivos, val):
        pts = self.pts[vivos]
        hull = mbl.contorno_convexo(pts)
        linear = len(pts) >= 3 and len(hull) >= 3 and mbl.largura_relativa(hull) >= mbl.FRACAO_COLINEAR
        tris = mbl.delaunay(pts) if linear else np.zeros((0, 3), int)
        return self._avaliar(x, y, pts, val[vivos], tris, hull, linear, range(len(pts)))


# ============================================================== inverso da distância
class IDW(_Base):
    metodo = "idw"

    def descricao(self):
        k = self.cfg["vizinhos"]
        return f"inverso da distância (potência {self.cfg['potencia']:g}, {'todos os' if not k else k} vizinhos)"

    def _idw(self, x, y, pts, val):
        x, y = np.asarray(x, float).ravel(), np.asarray(y, float).ravel()
        p, k = float(self.cfg["potencia"]), int(self.cfg["vizinhos"])
        out = np.empty(len(x))
        for a in range(0, len(x), 4000):
            dx = x[a:a + 4000, None] - pts[None, :, 0]
            dy = y[a:a + 4000, None] - pts[None, :, 1]
            d = np.hypot(dx, dy)
            if k and k < len(pts):
                idx = np.argpartition(d, k - 1, axis=1)[:, :k]
                d = np.take_along_axis(d, idx, 1)
                v = val[idx]
            else:
                v = np.broadcast_to(val, d.shape)
            exato = d < 1e-9
            w = 1.0 / np.maximum(d, 1e-12) ** p
            z = (w * v).sum(1) / w.sum(1)
            linha_exata = exato.any(1)
            if linha_exata.any():
                z[linha_exata] = (np.where(exato, v, 0).sum(1) / np.maximum(exato.sum(1), 1))[linha_exata]
            out[a:a + 4000] = z
        return out

    def valores(self, x, y):
        x = np.asarray(x, float)
        return self._idw(x, y, self.pts, self.val).reshape(x.shape)

    def valor(self, x, y, sem_poco=None):
        vazios, novos = self._tirar(sem_poco)
        val = self.val.copy()
        for k, v in novos.items():
            val[k] = v
        vivos = [k for k in range(len(self.pts)) if k not in vazios]
        if not vivos:
            return None, False, math.inf
        hull = self._hull_sem_no(vazios[0]) if len(vazios) == 1 else (
            mbl.contorno_convexo(self.pts[vivos]) if vazios else self.hull)
        dentro, dist = self._dentro_dist(x, y, vivos, hull)
        return float(self._idw([x], [y], self.pts[vivos], val[vivos])[0]), dentro, dist


# ============================================================== forma dual (spline, krigagem)
class _Dual(_Base):
    """z(q) = Σ cᵢ k(q, xᵢ) + Σ βⱼ pⱼ(q), com [K + λI, P; Pᵀ, 0] [c; β] = [z; 0].
    Guarda o inverso da matriz: tirar um ponto (ou mudar um valor) é uma atualização O(n)."""

    def _kernel(self, qx, qy, px, py, diagonal=False):
        raise NotImplementedError

    def _poli(self, x, y):
        return np.ones((len(x), 1))

    def _montar(self, lam: float):
        n = len(self.pts)
        x, y = self.pts[:, 0] - self.c0[0], self.pts[:, 1] - self.c0[1]
        K = self._kernel(x, y, x, y, diagonal=True) + lam * np.eye(n)
        P = self._poli(x, y)
        m = P.shape[1]
        M = np.zeros((n + m, n + m))
        M[:n, :n], M[:n, n:], M[n:, :n] = K, P, P.T
        Minv = np.linalg.pinv(M) if np.linalg.cond(M) > 1e13 else np.linalg.inv(M)
        rhs = np.r_[self.val, np.zeros(m)]
        return Minv, Minv @ rhs

    def _preparar(self, lam: float):
        self.c0 = self.pts.mean(0) if len(self.pts) else np.zeros(2)
        self.lam = lam
        self.Minv, self.coef = self._montar(lam)
        self._coef_sem: dict = {}

    def _avaliar_coef(self, x, y, coef):
        x, y = np.asarray(x, float).ravel() - self.c0[0], np.asarray(y, float).ravel() - self.c0[1]
        n = len(self.pts)
        px, py = self.pts[:, 0] - self.c0[0], self.pts[:, 1] - self.c0[1]
        out = np.empty(len(x))
        for a in range(0, len(x), 4000):
            k = self._kernel(x[a:a + 4000], y[a:a + 4000], px, py)
            out[a:a + 4000] = k @ coef[:n] + self._poli(x[a:a + 4000], y[a:a + 4000]) @ coef[n:]
        return out

    def valores(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        if not self.espacial:
            _, k = mbl.distancia_mais_proximo(self.pts, x, y)
            return self.val[k]
        return self._limitar(self._avaliar_coef(x, y, self.coef).reshape(x.shape), x, y)

    def loo_nos(self) -> np.ndarray:
        """Valor de cada nó previsto sem ele (Rippa: zᵢ − cᵢ / (M⁻¹)ᵢᵢ)."""
        n = len(self.pts)
        return self.val - self.coef[:n] / np.diag(self.Minv)[:n]

    def valor(self, x, y, sem_poco=None):
        if not len(self.pts):
            return None, False, math.inf
        vazios, novos = self._tirar(sem_poco)
        vivos = [k for k in range(len(self.pts)) if k not in vazios]
        if not vivos:
            return None, False, math.inf
        if not self.espacial or len(vazios) > 1:
            return self._refeito(x, y, sem_poco)
        chave = (sem_poco, tuple(vazios))
        if chave not in self._coef_sem:
            coef = self.coef.copy()
            for k, v in novos.items():                          # valor do nó mudou (pad): + δ · M⁻¹[:, k]
                coef = coef + (v - self.val[k]) * self.Minv[:, k]
            if vazios:
                r = vazios[0]
                d = self.Minv[r, r]
                if abs(d) < 1e-14:
                    return self._refeito(x, y, sem_poco)
                coef = coef - coef[r] / d * self.Minv[:, r]
                coef[r] = 0.0
            self._coef_sem[chave] = coef
        coef = self._coef_sem[chave]
        hull = self._hull_sem_no(vazios[0]) if vazios else self.hull
        if len(hull) < 3 or mbl.largura_relativa(hull) < mbl.FRACAO_COLINEAR:
            return self._refeito(x, y, sem_poco)
        dentro, dist = self._dentro_dist(x, y, vivos, hull)
        v = float(self._avaliar_coef([x], [y], coef)[0])
        if not dentro:
            v = float(np.clip(v, *self.faixa))
        return v, dentro, dist

    def _refeito(self, x, y, sem_poco):
        obs = [o for o in self.obs if o[3] != sem_poco]
        if not obs:
            return None, False, math.inf
        aj = type(self)(obs, self.cfg)
        v = float(np.ravel(aj.valores(np.array([x]), np.array([y])))[0])
        dentro, dist = aj._dentro_dist(x, y, list(range(len(aj.pts))), aj.hull)
        return v, dentro, dist


class Spline(_Dual):
    """Spline de placa fina: k(r) = r² log r, com o plano (1, x, y)."""

    metodo = "spline"

    def __init__(self, obs, cfg=None):
        super().__init__(obs, cfg)
        if not self.espacial:
            self.avisos.append("poucos poços ou alinhados: valor do poço mais próximo")
            return
        x, y = self.pts[:, 0], self.pts[:, 1]
        r = np.hypot(x[:, None] - x[None], y[:, None] - y[None])
        with np.errstate(divide="ignore", invalid="ignore"):
            k = np.where(r > 0, r * r * np.log(r), 0.0)
        self.escala = float(np.mean(np.abs(k))) or 1.0
        if self.cfg.get("_lambda") is not None:                 # λ fixo (refazer sem um poço, nos testes)
            self.info["suavidade"] = float(self.cfg.get("suavidade") or 0)
            self._preparar(float(self.cfg["_lambda"]))
            return
        s = self.cfg.get("suavidade")
        if s is None:                                           # automático: a melhor validação cruzada
            melhor = None
            for sv in [0.0] + list(np.linspace(0.1, 1.0, 10)):
                self._preparar(self._lambda(sv))
                e = float(np.median(np.abs(self.loo_nos() - self.val)))
                if melhor is None or e < melhor[0] - 1e-9:
                    melhor = (e, sv)
            s = melhor[1]
            self.info["suavidade_auto"] = True
        self.info["suavidade"] = float(s)
        self._preparar(self._lambda(float(s)))

    def _lambda(self, s: float) -> float:
        return 0.0 if s <= 0 else self.escala * 10 ** (-5 + 5 * s)

    def _kernel(self, qx, qy, px, py, diagonal=False):
        r = np.hypot(np.asarray(qx)[:, None] - px[None], np.asarray(qy)[:, None] - py[None])
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(r > 0, r * r * np.log(r), 0.0)

    def _poli(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        return np.column_stack([np.ones(len(x)), x, y])

    def descricao(self):
        if not self.espacial:
            return "spline (poucos poços: poço mais próximo)"
        s = self.info.get("suavidade", 0)
        return f"spline de placa fina (suavidade {s:.1f}{', automática' if self.info.get('suavidade_auto') else ''})"


class Krigagem(_Dual):
    """Krigagem ordinária (média desconhecida), forma dual. Covariância C(h) = patamar·(1 − g(h/a));
    a pepita vai na diagonal (filtra: o valor no poço pode diferir do medido)."""

    metodo = "krigagem"

    def __init__(self, obs, cfg=None):
        super().__init__(obs, cfg)
        if not self.espacial or len(self.pts) < MIN_KRIGAGEM:
            self.espacial = False
            self.avisos.append(f"menos de {MIN_KRIGAGEM} poços: sem variograma, valor do poço mais próximo")
            return
        self.vario = dict(self.cfg["_vario"]) if self.cfg.get("_vario") else \
            ajustar_variograma(self.pts, self.val, self.cfg)
        # pepita mínima: o gaussiano sem pepita deixa a matriz quase singular
        self.vario["pepita"] = max(self.vario["pepita"], 1e-4 * self.vario["patamar"])
        self.info.update(self.vario)
        self._preparar(0.0)

    # distância anisotrópica (eixo maior no azimute)
    def _h(self, qx, qy, px, py):
        dx = np.asarray(qx)[:, None] - px[None]
        dy = np.asarray(qy)[:, None] - py[None]
        return _dist_aniso(dx, dy, self.cfg["azimute"], self.cfg["razao"])

    def _kernel(self, qx, qy, px, py, diagonal=False):
        v = self.vario
        h = self._h(qx, qy, px, py)
        C = v["patamar"] * (1 - _g(v["modelo"], h / v["alcance_km"]))
        if diagonal:
            C = C + v["pepita"] * np.eye(len(px))
        return C

    def sigma(self, x, y):
        """Desvio padrão da krigagem (m) nos pontos (sem a pepita)."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        if not self.espacial:
            return np.full(x.shape, np.nan)
        xs, ys = x.ravel() - self.c0[0], y.ravel() - self.c0[1]
        px, py = self.pts[:, 0] - self.c0[0], self.pts[:, 1] - self.c0[1]
        out = np.empty(len(xs))
        for a in range(0, len(xs), 2000):
            k = np.hstack([self._kernel(xs[a:a + 2000], ys[a:a + 2000], px, py), np.ones((len(xs[a:a + 2000]), 1))])
            var = self.vario["patamar"] - np.einsum("ij,jk,ik->i", k, self.Minv, k)
            out[a:a + 2000] = np.sqrt(np.maximum(var, 0))
        return out.reshape(x.shape)

    def descricao(self):
        if not self.espacial:
            return "krigagem (poucos poços: poço mais próximo)"
        v = self.vario
        tot = v["pepita"] + v["patamar"]
        aniso = f", anisotropia {self.cfg['azimute']:.0f}° × {self.cfg['razao']:.2f}" if self.cfg["razao"] < 1 else ""
        return (f"krigagem ({NOMES_MODELO[v['modelo']]}, alcance {v['alcance_km']:.1f} km, pepita "
                f"{100 * v['pepita'] / tot if tot else 0:.0f}%{aniso})")


class Tendencia(_Base):
    """Polinômio de grau 1 ou 2 (mínimos quadrados) + krigagem do resíduo. Na validação
    cruzada a tendência fica a de todos os poços (3 a 6 coeficientes de centenas de poços)."""

    metodo = "tendencia"

    def __init__(self, obs, cfg=None):
        super().__init__(obs, cfg)
        self.c0 = self.pts.mean(0) if len(self.pts) else np.zeros(2)
        A = self._termos(self.pts[:, 0], self.pts[:, 1]) if len(self.pts) else np.zeros((0, 1))
        if len(self.pts) >= A.shape[1] + 2:
            self.beta = np.linalg.lstsq(A, self.val, rcond=None)[0]
        else:
            self.beta = np.r_[float(np.mean(self.val)) if len(self.val) else 0.0, np.zeros(A.shape[1] - 1)]
        tend = self._tendencia(np.array([o[0] for o in self.obs]), np.array([o[1] for o in self.obs]))
        res = [(o[0], o[1], o[2] - t) + tuple(o[3:]) for o, t in zip(self.obs, tend)]
        self.residuo = Krigagem(res, self.cfg)
        self.info = dict(self.residuo.info, grau=self.cfg["grau"])
        self.avisos = self.residuo.avisos

    def _termos(self, x, y):
        x, y = np.asarray(x, float) - self.c0[0], np.asarray(y, float) - self.c0[1]
        cols = [np.ones(len(x)), x, y] + ([x * x, x * y, y * y] if self.cfg["grau"] == 2 else [])
        return np.column_stack(cols)

    def _tendencia(self, x, y):
        x = np.asarray(x, float)
        return (self._termos(x.ravel(), np.asarray(y, float).ravel()) @ self.beta).reshape(x.shape)

    def valores(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        return self._limitar(self._tendencia(x, y) + self.residuo.valores(x, y), x, y)

    def valor(self, x, y, sem_poco=None):
        v, dentro, dist = self.residuo.valor(x, y, sem_poco)
        if v is None:
            return None, False, dist
        v = v + float(self._tendencia(np.array([x]), np.array([y]))[0])
        if not dentro:
            v = float(np.clip(v, *self.faixa))
        return v, dentro, dist

    def sigma(self, x, y):
        return self.residuo.sigma(x, y)

    def descricao(self):
        return f"tendência de grau {self.cfg['grau']} + " + self.residuo.descricao()


CLASSES = {"linear": Linear, "idw": IDW, "spline": Spline, "krigagem": Krigagem, "tendencia": Tendencia}


class ComPresenca:
    """Espessura com zeros: onde a unidade falta (espessura 0 nos poços em volta), ela é 0.

    Spline, krigagem e IDW espalham um pouco de espessura por todo lado entre poços com 0 —
    somando 10 unidades finas, o bloco erra dezenas de metros. A presença (1 onde a unidade
    tem espessura, 0 onde falta) é interpolada linear: onde ela é 0, a espessura é 0; onde é 1,
    a do método; no meio, uma transição (a linha de acunhamento fica onde a presença vale ½)."""

    def __init__(self, cfg, obs):
        self.aj = _classe(cfg, obs)
        self.pres = Linear([(o[0], o[1], 1.0 if o[2] >= 0.5 else 0.0) + tuple(o[3:]) for o in obs])
        self.metodo, self.cfg, self.info, self.avisos = self.aj.metodo, self.aj.cfg, self.aj.info, self.aj.avisos
        self.hull, self.espacial = self.aj.hull, self.aj.espacial

    def __len__(self):
        return len(self.aj)

    @staticmethod
    def _fator(p):
        return np.clip(2.0 * np.asarray(p, float), 0.0, 1.0)

    def valores(self, x, y):
        return np.maximum(self.aj.valores(x, y), 0.0) * self._fator(self.pres.valores(x, y))

    def grade(self, grade_):
        gx, gy = _nos(grade_)
        z = self.valores(gx, gy)
        controle = mbl.dentro(self.hull, gx, gy) if self.espacial else np.zeros(gx.shape, bool)
        return z, controle

    def valor(self, x, y, sem_poco=None):
        v, dentro, dist = self.aj.valor(x, y, sem_poco)
        if v is None:
            return v, dentro, dist
        p = self.pres.valor(x, y, sem_poco)[0]
        return max(v, 0.0) * float(self._fator(p if p is not None else 1.0)), dentro, dist

    def descricao(self):
        return self.aj.descricao() + " × presença (linear)"


def _classe(cfg: dict, obs: list):
    """O método pedido; krigagem com menos de MIN_KRIGAGEM poços (posições distintas) não tem
    variograma que se sustente → linear, com aviso."""
    if cfg["metodo"] in ("krigagem", "tendencia"):
        n = len({(round(float(o[0]), 6), round(float(o[1]), 6)) for o in obs})
        if n < MIN_KRIGAGEM:
            aj = Linear(obs, cfg)
            if n >= 3:
                aj.avisos.append(f"só {n} poços com o dado: krigagem pede {MIN_KRIGAGEM} ou mais — usada a linear")
            return aj
    return CLASSES[cfg["metodo"]](obs, cfg)


def ajustar(cfg_campo: dict | None, obs: list, campo: str = "estrutura"):
    cfg = dict(PADRAO, **(cfg_campo or {}))
    if campo == "espessura" and cfg["metodo"] != "linear":
        return ComPresenca(cfg, obs)
    return _classe(cfg, obs)


# ============================================================== variograma
NOMES_MODELO = {"esferico": "esférico", "exponencial": "exponencial", "gaussiano": "gaussiano"}


def _g(modelo, t):
    t = np.asarray(t, float)
    if modelo == "esferico":
        return np.where(t < 1, 1.5 * t - 0.5 * t ** 3, 1.0)
    if modelo == "exponencial":
        return 1 - np.exp(-3 * t)
    return 1 - np.exp(-3 * t * t)


def _dist_aniso(dx, dy, azimute, razao):
    if razao >= 1:
        return np.hypot(dx, dy)
    a = math.radians(azimute)
    u = dx * math.sin(a) + dy * math.cos(a)        # ao longo do azimute (a partir do norte)
    v = dx * math.cos(a) - dy * math.sin(a)
    return np.hypot(u, v / razao)


def variograma_experimental(pts, val, azimute=0.0, razao=1.0, n_classes=15, max_pares=200_000, semente=0):
    """Semivariância por classe de distância. O alcance das classes vai até 15× o espaçamento
    típico dos poços (a mediana da distância ao vizinho mais próximo), no máximo metade da maior
    distância: é a escala em que a krigagem interpola de fato."""
    pts, val = np.asarray(pts, float), np.asarray(val, float)
    n = len(pts)
    d_viz = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1]) if n <= 2500 else None
    i, j = np.triu_indices(n, 1)
    if len(i) > max_pares:
        sel = np.random.default_rng(semente).choice(len(i), max_pares, replace=False)
        i, j = i[sel], j[sel]
    h = _dist_aniso(pts[i, 0] - pts[j, 0], pts[i, 1] - pts[j, 1], azimute, razao)
    g = 0.5 * (val[i] - val[j]) ** 2
    hmax = 0.5 * float(h.max()) if len(h) else 1.0
    if d_viz is not None and n >= 3:
        np.fill_diagonal(d_viz, np.inf)
        espac = float(np.median(d_viz.min(1)))
        if espac > 0:
            hmax = min(hmax, 15 * espac)
    bordas = np.linspace(0, hmax, n_classes + 1)
    k = np.digitize(h, bordas) - 1
    centros, gam, cont = [], [], []
    for c in range(n_classes):
        m = k == c
        if m.sum() >= 3:
            centros.append(float(h[m].mean()))
            gam.append(float(g[m].mean()))
            cont.append(int(m.sum()))
    return np.array(centros), np.array(gam), np.array(cont), hmax


def ajustar_variograma(pts, val, cfg: dict) -> dict:
    """Modelo, alcance, pepita e patamar por mínimos quadrados ponderados (pares por classe),
    a partir do variograma experimental; o que o usuário fixou fica fixo."""
    h, g, w, hmax = variograma_experimental(pts, val, cfg.get("azimute", 0.0), cfg.get("razao", 1.0))
    w = w / np.maximum(h, 1e-6)                    # classes curtas pesam mais (é ali que se interpola)
    var = float(np.var(val)) or 1.0
    if len(h) < 3:
        return {"modelo": "esferico" if cfg.get("modelo") in (None, "auto") else cfg["modelo"],
                "alcance_km": float(cfg.get("alcance_km") or hmax), "pepita": 0.0, "patamar": var,
                "ajuste": "poucos pares"}
    # automático: esférico ou exponencial (o gaussiano sem pepita oscila; só se pedido)
    modelos = ("esferico", "exponencial") if cfg.get("modelo") in (None, "auto") else (cfg["modelo"],)
    alcances = [float(cfg["alcance_km"])] if cfg.get("alcance_km") else list(np.geomspace(0.05, 2.0, 40) * hmax)
    suav = cfg.get("suavidade")
    melhor = None
    for mod in modelos:
        for a in alcances:
            f = _g(mod, h / a)
            if suav is not None:                       # pepita fixada pela suavidade: fração do total
                frac = 0.9 * suav
                base = frac + (1 - frac) * f
                tot = max(float((w * base * g).sum() / max((w * base * base).sum(), 1e-12)), 1e-9)
                n_, s_ = frac * tot, (1 - frac) * tot
            else:
                A = np.column_stack([np.ones_like(f), f]) * np.sqrt(w)[:, None]
                sol = np.linalg.lstsq(A, g * np.sqrt(w), rcond=None)[0]
                n_, s_ = float(sol[0]), float(sol[1])
                if n_ < 0:
                    n_, s_ = 0.0, float((w * f * g).sum() / max((w * f * f).sum(), 1e-12))
                if s_ <= 0:
                    s_ = max(var - n_, 1e-9)
            sse = float((w * (n_ + s_ * f - g) ** 2).sum())
            if melhor is None or sse < melhor[0]:
                melhor = (sse, mod, a, n_, s_)
    _, mod, a, n_, s_ = melhor
    return {"modelo": mod, "alcance_km": float(a), "pepita": float(max(n_, 0.0)), "patamar": float(max(s_, 1e-9)),
            "ajuste": "fixado" if cfg.get("alcance_km") and cfg.get("modelo") not in (None, "auto") else "ajustado",
            "experimental": {"h": [round(float(v), 3) for v in h], "gama": [round(float(v), 2) for v in g],
                             "pares": [int(v) for v in w]}}


# ============================================================== grade com as regras do bloco
def grade(cfg_campo: dict | None, obs: list, grade_: dict, campo: str = "estrutura"):
    """(z em toda a grade, controle, ajuste) — o que bloco_solido usa para cada campo."""
    if not obs:
        ny, nx = grade_["ny"], grade_["nx"]
        return np.full((ny, nx), np.nan), np.zeros((ny, nx), bool), None
    aj = ajustar(cfg_campo, obs, campo)
    z, controle = aj.grade(grade_)
    return z, controle, aj
