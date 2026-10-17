"""Métodos de interpolação (motor/interpolacao.py): tirar um poço = refazer sem ele,
variograma, configuração, empilhamento topo a topo, comparação. Pontos sintéticos."""
import math

import numpy as np
import pytest

from motor import bloco as mb
from motor import bloco_figura as mbf
from motor import bloco_validacao as mbv
from motor import interpolacao as mint
from test_bloco_solido import IDS, banco  # noqa: F401  (banco é fixture)


def _obs(n=30, semente=3, repetido=True):
    rng = np.random.default_rng(semente)
    pts = rng.uniform(0, 20, (n, 2))
    if repetido:
        pts[1] = pts[0]                                       # dois poços no mesmo ponto
    val = -800 - 12 * pts[:, 0] + 5 * pts[:, 1] + 30 * np.sin(pts[:, 0] / 3) + rng.normal(0, 4, n)
    return [(float(pts[i, 0]), float(pts[i, 1]), float(val[i]), f"P{i}") for i in range(n)]


def _dentro_de_todos(obs, sem, x, y):
    resto = np.array([[o[0], o[1]] for o in obs if o[3] != sem])
    h = mb.contorno_convexo(resto)
    return bool(mb.dentro(h, np.array([x]), np.array([y]))[0])


@pytest.mark.parametrize("cfg", [
    {"metodo": "idw", "potencia": 2.0, "vizinhos": 8},
    {"metodo": "idw", "potencia": 1.0, "vizinhos": 0},
    {"metodo": "spline", "_lambda": 0.0},
    {"metodo": "spline", "_lambda": 0.5},
    {"metodo": "krigagem", "_vario": {"modelo": "esferico", "alcance_km": 9.0, "patamar": 900.0, "pepita": 20.0}},
    {"metodo": "krigagem", "_vario": {"modelo": "exponencial", "alcance_km": 6.0, "patamar": 700.0, "pepita": 0.0},
     "azimute": 30.0, "razao": 0.5},
])
def test_tirar_um_poco_e_igual_a_refazer_sem_ele(cfg):
    """A atualização dos coeficientes (Dubrule) e o IDW sem o poço dão o mesmo que ajustar
    de novo sem ele — com os hiperparâmetros fixos (no uso real eles também ficam fixos)."""
    obs = _obs()
    c = mint.configuracao({"estrutura": cfg})["estrutura"]
    c.update({k: v for k, v in cfg.items() if k.startswith("_")})
    f = mint.ajustar(c, obs)
    rng = np.random.default_rng(11)
    testados = 0
    for i in range(0, len(obs), 3):
        sem = f"P{i}"
        g = mint.ajustar(c, [o for o in obs if o[3] != sem])
        for q in [(obs[i][0], obs[i][1])] + [tuple(p) for p in rng.uniform(2, 18, (3, 2))]:
            if not _dentro_de_todos(obs, sem, *q):            # fora: a faixa de corte muda sem o poço
                continue
            a, b = f.valor(q[0], q[1], sem), g.valor(q[0], q[1])
            assert a[0] == pytest.approx(b[0], abs=1e-5)
            assert a[1] == b[1] and a[2] == pytest.approx(b[2])
            testados += 1
    assert testados > 10


def test_tendencia_tira_o_mergulho_e_kriga_o_resto():
    obs = _obs(60, repetido=False)
    f = mint.ajustar(mint.configuracao({"estrutura": "tendencia"})["estrutura"], obs)
    # a tendência de grau 1 acha o mergulho (−12 m/km em x, +5 em y), a menos da senoide
    assert f.descricao().startswith("tendência de grau 1")
    v = f.valores(np.array([10.0]), np.array([10.0]))[0]
    assert -800 - 120 + 50 - 40 < v < -800 - 120 + 50 + 40
    # exata nos poços (sem pepita) e σ ≥ 0, crescendo para longe dos poços
    s_perto = f.sigma(np.array([obs[5][0]]), np.array([obs[5][1]]))[0]
    s_longe = f.sigma(np.array([40.0]), np.array([40.0]))[0]
    assert 0 <= s_perto < s_longe


def test_spline_exata_sem_suavidade_e_lisa_com():
    obs = _obs(25, repetido=False)
    exata = mint.ajustar(mint.configuracao({"estrutura": {"metodo": "spline", "suavidade": 0}})["estrutura"], obs)
    lisa = mint.ajustar(mint.configuracao({"estrutura": {"metodo": "spline", "suavidade": 1}})["estrutura"], obs)
    x = np.array([o[0] for o in obs]); y = np.array([o[1] for o in obs]); z = np.array([o[2] for o in obs])
    assert np.abs(exata.valores(x, y) - z).max() < 1e-3
    assert np.abs(lisa.valores(x, y) - z).mean() > 1.0
    auto = mint.ajustar(mint.configuracao({"estrutura": "spline"})["estrutura"], obs)
    assert "automática" in auto.descricao()


def test_variograma_acha_o_alcance():
    # campo aleatório com correlação conhecida (média móvel de ruído): alcance ≈ largura do núcleo
    rng = np.random.default_rng(5)
    n, lado = 400, 60.0
    ruido = rng.normal(0, 1, (240, 240))
    k = np.ones((1, 40)) / 40
    from numpy.lib.stride_tricks import sliding_window_view as sw
    liso = sw(ruido, (40, 40)).mean(axis=(2, 3))             # suavizado com janela de 40 células (10 km)
    pts = rng.uniform(0, lado - 12, (n, 2))
    ij = np.clip((pts / 0.25).astype(int), 0, liso.shape[0] - 1)
    val = liso[ij[:, 1], ij[:, 0]] * 100
    v = mint.ajustar_variograma(pts, val, dict(mint.PADRAO, metodo="krigagem"))
    assert v["modelo"] in ("esferico", "exponencial")
    assert 4.0 < v["alcance_km"] < 25.0                         # janela de 10 km: alcance da ordem de 10 km
    assert v["pepita"] < 0.3 * v["patamar"]
    h, gama, pares, hmax = mint.variograma_experimental(pts, val)
    assert len(h) >= 5 and (gama > 0).all() and h.max() <= hmax
    del k


def test_configuracao_valida_e_aceita_atalhos():
    c = mint.configuracao({"estrutura": "krigagem", "parametros": {"razao": "0,5", "azimute": 45}})
    assert c["estrutura"]["metodo"] == "krigagem" and c["estrutura"]["razao"] == 0.5
    assert c["espessura"]["metodo"] == "linear" and c["empilhamento"] == "espessuras"
    assert mint.configuracao(c) == c                          # idempotente (vai e volta da janela)
    assert mint.configuracao({"empilhamento": "topos"})["empilhamento"] == "topos"
    for ruim in ({"estrutura": "vizinho"}, {"estrutura": {"metodo": "spline", "suavidade": 2}},
                 {"parametros": {"razao": 0}}, {"empilhamento": "camadas"}, {"estrutura": {"metodo": "tendencia", "grau": 3}}):
        with pytest.raises(mint.ErroInterpolacao):
            mint.configuracao(ruim)
    assert set(mint.ESCALAS) == {"reservatorio", "bacia"}
    for e in mint.ESCALAS.values():
        mint.configuracao(e["interpolacao"])                 # os pontos de partida são válidos


def test_poucos_pocos_krigagem_vira_linear_com_aviso():
    obs = _obs(6, repetido=False)
    f = mint.ajustar(mint.configuracao({"estrutura": "krigagem"})["estrutura"], obs)
    assert f.metodo == "linear" and any("krigagem" in a for a in f.avisos)


def test_metodos_lisos_ficam_na_faixa_dos_dados_fora_do_contorno():
    obs = _obs(30, repetido=False)
    zs = [o[2] for o in obs]
    lo, hi = min(zs) - 0.1 * (max(zs) - min(zs)), max(zs) + 0.1 * (max(zs) - min(zs))
    for m in ("spline", "krigagem", "tendencia", "idw"):
        f = mint.ajustar(mint.configuracao({"estrutura": m})["estrutura"], obs)
        v = f.valores(np.array([-60.0, 90.0]), np.array([-60.0, 90.0]))
        assert (v >= lo - 1e-6).all() and (v <= hi + 1e-6).all(), m


@pytest.mark.parametrize("empilhamento", ["espessuras", "topos"])
@pytest.mark.parametrize("metodo", ["linear", "spline"])
def test_bloco_fechado_com_cada_metodo_nao_cruza(banco, metodo, empilhamento):
    m = mb.montar(banco, IDS, interpolacao={"estrutura": metodo, "espessura": metodo, "empilhamento": empilhamento})
    s = m["solido"]
    assert s["ok"] and s["empilhamento"] == empilhamento
    lims = [np.array(z, float) for z in s["limites"]]
    for a, b in zip(lims, lims[1:]):
        ok = ~np.isnan(a) & ~np.isnan(b)
        assert (a[ok] >= b[ok] - 1e-6).all()
    assert m["parametros"]["interpolacao"]["empilhamento"] == empilhamento
    # o ponto e a grade seguem as mesmas regras também topo a topo
    emp = mbv.Empilhamento(m)
    g = m["grade"]
    com_cob = s["camadas"][0]["chave"].startswith("_")
    j, i = g["ny"] // 2, g["nx"] // 2
    L = emp.limites(g["x0"] + i * g["passo"], g["y0"] + j * g["passo"])
    bordas = ([L["terreno"]] if com_cob else []) + L["lim"]
    for k, v in enumerate(bordas):
        assert v == pytest.approx(lims[k][j, i], abs=0.5)


def test_superficies_com_krigagem_dao_o_mapa_de_incerteza(banco):
    m = mb.montar(banco, IDS, interpolacao={"estrutura": "krigagem"})
    # 5 poços: krigagem sem variograma → linear, com aviso, e sem σ
    assert not any("sigma_m" in p.get("grades", {}) for p in (m.get("propriedades") or {}).values())
    assert any("krigagem pede" in a for a in m["avisos"])


def test_comparar_metodos_figura_e_csv(banco, tmp_path):
    m = mb.montar(banco, IDS)
    c = mbv.comparar(m)
    ids = [x["id"] for x in c["candidatos"]]
    assert ids == [x[0] for x in mbv.CANDIDATOS] and c["melhor"] in ids
    assert c["criterio"] == "fechado" and c["melhor_superficie"] in ids
    for x in c["candidatos"]:
        assert mint.configuracao(x["interpolacao"]) == x["interpolacao"]
        assert x["global"]["fechado"]["n"] == c["n_comparacoes"]
    assert set(c["por_unidade"]) <= set(c["candidatos"][0]["unidades"])
    linhas = mbv.linhas_csv_comparacao(c)
    assert len(linhas[0]) == len(mbv.COLUNAS_CSV_COMPARACAO)
    assert sum(1 for l in linhas if l[2] == "(todas)") == len(ids)
    svg = mbv.figura_comparacao(c, titulo="Métodos", autor="Fulano", data="17/10/2026", versao="0.23.0")
    assert "(a)" in svg and "(b)" in svg and "sugerido" in svg and "escala log" in svg
    assert open(mbf.exportar(svg, str(tmp_path / "c.pdf"), "pdf"), "rb").read(4) == b"%PDF"
    # só alguns candidatos, e parâmetros comuns
    c2 = mbv.comparar(m, parametros={"potencia": 3}, candidatos=mbv.CANDIDATOS[:3])
    assert len(c2["candidatos"]) == 3
    assert c2["candidatos"][2]["interpolacao"]["estrutura"]["potencia"] == 3.0
    assert not math.isnan(c2["candidatos"][0]["global"]["fechado"]["mediana"])
