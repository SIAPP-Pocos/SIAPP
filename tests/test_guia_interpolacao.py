"""Guia de qual método de interpolação usar (motor/guia_interpolacao.py) e as preferências do bloco."""
import numpy as np

from motor import guia_interpolacao as mg
from motor import preferencias as mpf


def _pts(n, semente=1):
    return np.random.default_rng(semente).uniform(0, 10, (n, 2))


def _nota(r, metodo):
    return next(m for m in r["metodos"] if m["id"] == metodo)


def test_leque_com_poucos_pocos_indica_rbf_e_desaconselha_krigagem():
    r = mg.recomendar("leque", mg.diagnostico(_pts(9)))
    assert r["indicado"]["metodo"] == "rbf" and r["indicado"]["parametros"] == {"funcao": "multiquadrica"}
    assert _nota(r, "idw")["nota"] == "evitar"
    k = _nota(r, "krigagem")
    assert any("pouco confiável" in m["texto"] for m in k["motivos"])
    r5 = mg.recomendar("leque", mg.diagnostico(_pts(5)))
    assert _nota(r5, "krigagem")["nota"] == "evitar" and _nota(r5, "tendencia")["nota"] == "evitar"


def test_outros_ambientes():
    d = mg.diagnostico(_pts(30))
    assert _nota(mg.recomendar("fluvial", d), "spline")["nota"] == "evitar"
    assert mg.recomendar("fluvial", d)["indicado"]["metodo"] == "krigagem"
    assert mg.recomendar("rifte", mg.diagnostico(_pts(5)))["indicado"]["metodo"] == "linear"
    assert _nota(mg.recomendar("rifte", d), "rbf")["nota"] == "evitar"
    # ambiente desconhecido = "não sei": decide pelos dados
    assert mg.recomendar("xyz", d)["ambiente"]["id"] == "nao_sei"


def test_mergulho_regional_forte_puxa_a_tendencia():
    pts = _pts(25)
    v = -800 - 20 * pts[:, 0] + np.random.default_rng(2).normal(0, 3, 25)
    d = mg.diagnostico(pts, v)
    assert d["r2_plano"] > 0.9 and d["n"] == 25 and d["espacamento_km"] > 0
    assert any("mergulho regional" in m["texto"] for m in _nota(mg.recomendar("nao_sei", d), "tendencia")["motivos"])


def test_a_comparacao_nos_pocos_pesa_mais_que_o_ambiente():
    d = mg.diagnostico(_pts(12))
    cmp = {"criterio": "fechado", "candidatos": [
        {"id": "linear", "nome": "Linear, por espessuras", "interpolacao": {"estrutura": {"metodo": "linear"}},
         "global": {"fechado": {"mediana": 4.0}}},
        {"id": "rbf", "nome": "RBF multiquádrica", "interpolacao": {"estrutura": {"metodo": "rbf"}},
         "global": {"fechado": {"mediana": 12.0}}},
        {"id": "spline", "nome": "Spline", "interpolacao": {"estrutura": {"metodo": "spline"}},
         "global": {"fechado": {"mediana": 4.5}}}]}
    r = mg.recomendar("leque", d, cmp)
    assert r["com_comparacao"] and r["indicado"]["metodo"] in ("linear", "spline")
    assert any(m["fonte"] == "comparacao" and "errou menos" in m["texto"] for m in _nota(r, "linear")["motivos"])
    assert any("bem mais" in m["texto"] for m in _nota(r, "rbf")["motivos"])


def test_guia_quebrado_nao_quebra(tmp_path):
    f = tmp_path / "g.json"
    f.write_text("{quebrado", encoding="utf-8")
    g = mg.ler_guia(str(f))
    assert g["ambientes"][0]["id"] == "nao_sei"
    f.write_text('{"ambientes": [{"id": "x", "nome": "X", "recomendados": ["rbf", "magica"]}]}', encoding="utf-8")
    g = mg.ler_guia(str(f))
    assert [a["id"] for a in g["ambientes"]] == ["nao_sei", "x"] and g["ambientes"][1]["recomendados"] == ["rbf"]
    r = mg.recomendar("x", {"n": 10}, guia=g)
    assert r["indicado"]["metodo"] == "rbf"


def test_preferencias_do_bloco():
    p = mpf.normalizar({"bloco": {"ambiente": "leque", "aparencia": {
        "marcador": {"forma": "cubo", "cor": "#FF0000", "tamanho": 9}, "linha": {"cor": "vermelho"},
        "trilha": {"espessura": 0.1, "cores": {"classe:2": "#00ff00", "x": "nada"}}, "topos": False,
        "por_cima": "sempre", "lixo": 1}}})
    ap = p["bloco"]["aparencia"]
    assert p["bloco"]["ambiente"] == "leque"
    assert ap["marcador"] == {"forma": "cubo", "cor": "#ff0000", "tamanho": 4.0} and "linha" not in ap
    assert ap["trilha"] == {"espessura": 0.3, "cores": {"classe:2": "#00ff00"}}
    assert ap["topos"] is False and ap["por_cima"] == "sempre" and "lixo" not in ap
    assert mpf.normalizar({"bloco": {"ambiente": "../x"}})["bloco"] == {}
    novo = mpf.mesclar(p, {"bloco": {"ambiente": "fluvial"}})
    assert novo["bloco"]["ambiente"] == "fluvial" and novo["bloco"]["aparencia"]["topos"] is False
