"""Viabilidade 0.52: diâmetro pela vazão, correção pela inflação (séries do Banco Central), restrições ambientais."""
import json
import math
import os

import pytest

from motor import camadas as mca
from motor import economia as mec
from motor import indices as mix
from motor import viabilidade as mvi


# ---------------------------------------------------------------- índices (sem internet: sessão falsa)
class RespostaFalsa:
    def __init__(self, dados, status=200):
        self.dados, self.status_code = dados, status

    def json(self):
        return self.dados


class SessaoFalsa:
    def __init__(self, dados=None, status=200, erro=None):
        self.dados, self.status, self.erro, self.chamadas = dados, status, erro, []

    def get(self, url, **kw):
        self.chamadas.append((url, kw))
        if self.erro:
            raise self.erro
        return RespostaFalsa(self.dados, self.status)


SERIE_BCB = [{"data": "01/06/2024", "valor": "0.21"}, {"data": "01/07/2024", "valor": "0.38"},
             {"data": "01/08/2024", "valor": "-0.02"}, {"data": "01/09/2024", "valor": "0.44"}]


def test_ler_mes_aceita_varias_formas_e_ano_so_e_aproximado():
    assert mix.ler_mes("jun/2024") == ((2024, 6), False)
    assert mix.ler_mes("Dez/2022") == ((2022, 12), False)
    assert mix.ler_mes("2024-06") == ((2024, 6), False) and mix.ler_mes("06/2024") == ((2024, 6), False)
    assert mix.ler_mes("2022") == ((2022, 6), True)
    for ruim in ("", "abc", "13/2024", "foo/2024"):
        with pytest.raises(mix.ErroIndices, match="Não entendi"):
            mix.ler_mes(ruim)


def test_fator_acumulado_depois_da_data_base_ate_a_referencia():
    serie = [[2024, 6, 0.21], [2024, 7, 0.38], [2024, 8, -0.02], [2024, 9, 0.44]]
    f, n = mix.fator_acumulado(serie, (2024, 6), (2024, 9))                  # jul, ago e set
    assert n == 3 and f == pytest.approx(1.0038 * 0.9998 * 1.0044)
    assert mix.fator_acumulado(serie, (2024, 9), (2024, 9)) == (1.0, 0)
    with pytest.raises(mix.ErroIndices, match="anterior"):
        mix.fator_acumulado(serie, (2024, 9), (2024, 6))
    with pytest.raises(mix.ErroIndices, match="não tem 2024-10"):
        mix.fator_acumulado(serie, (2024, 6), (2024, 10))                    # nunca completa a série sozinho


def test_corrigir_baixa_guarda_e_usa_a_copia_sem_internet(tmp_path):
    pasta = str(tmp_path)
    s = SessaoFalsa(SERIE_BCB)
    r = mix.corrigir(pasta, "ipca", "jun/2024", None, s)
    assert r["fator"] == pytest.approx(1.0038 * 0.9998 * 1.0044) and r["meses"] == 3 and r["ate"] == "2024-09"
    assert r["de"] == "2024-06" and "433" in r["rotulo"] and "bcdata.sgs.433" in s.chamadas[0][0]
    assert os.path.isfile(os.path.join(pasta, "indices", "ipca.json"))
    # segunda vez: usa a cópia (não chama a rede); sem internet e com atualização forçada, avisa que usou a cópia
    s2 = SessaoFalsa(erro=OSError("sem rede"))
    assert mix.corrigir(pasta, "ipca", "jun/2024", "2024-08", s2)["fator"] == pytest.approx(1.0038 * 0.9998)
    assert not s2.chamadas
    r3 = mix.corrigir(pasta, "ipca", "jun/2024", None, s2, atualizar=True)
    assert any("cópia guardada" in a for a in r3["avisos"])
    with pytest.raises(mix.ErroIndices, match="Banco Central"):
        mix.corrigir(str(tmp_path / "outro"), "incc", "jun/2024", None, s2)          # sem cópia e sem rede
    with pytest.raises(mix.ErroIndices, match="data-base"):
        mix.corrigir(pasta, "ipca", "", None, s)
    with pytest.raises(mix.ErroIndices, match="desconhecido"):
        mix.baixar_serie("selic")
    assert any("assumido junho" in a for a in mix.corrigir(pasta, "ipca", "2024", None, s)["avisos"])


def test_resposta_ruim_do_banco_central(tmp_path):
    with pytest.raises(mix.ErroIndices, match="HTTP 500"):
        mix.baixar_serie("ipca", SessaoFalsa([], status=500))
    with pytest.raises(mix.ErroIndices, match="vazia"):
        mix.baixar_serie("ipca", SessaoFalsa([]))
    with pytest.raises(mix.ErroIndices, match="formato"):
        mix.baixar_serie("ipca", SessaoFalsa([{"x": 1}]))


# ---------------------------------------------------------------- economia: diâmetro e inflação
DIST = [10.0, 25.0]


def test_diametro_pela_vazao_bate_com_a_continuidade():
    dados = {"fluido": "ch4", "diametro_modo": "vazao", "vazao_sm3_d": 2e6, "p_duto_bar": 80, "t_duto_c": 30,
             "vel_max_m_s": 12}
    r = mec.custos_duto(dados, DIST)
    p = r["parametros"]
    rho_std = mec.densidade("ch4", mec.CONSTANTES["p_padrao"]["valor"], mec.CONSTANTES["t_padrao"]["valor"])
    rho_op = mec.densidade("ch4", 80, 30)
    qop = 2e6 * rho_std / rho_op
    esperado_pol = math.sqrt(4 * qop / (math.pi * 12 * 86400)) / 0.0254
    assert p["diametro_usado_pol"] == pytest.approx(esperado_pol, rel=1e-9)
    assert r["custo"]["diametro_pol"] == pytest.approx(esperado_pol) and r["custo"]["diametro_modo"] == "vazao"
    ids = [x["id"] for x in r["memoria"]["passos"]]
    assert ids[:4] == ["vazao_operacao", "diametro_vazao", "diametro_pol", "custo_km"]
    assert r["custo"]["r_por_km"] == pytest.approx(488e3 * esperado_pol * 1.0)             # CH4: fator 1,00
    assert 1 < esperado_pol < 30                                                           # ordem de grandeza razoável


def test_diametro_comercial_sobe_para_o_proximo_tamanho_e_avisa_na_memoria():
    base = {"fluido": "ch4", "vazao_sm3_d": 2e6, "p_duto_bar": 80, "t_duto_c": 30, "vel_max_m_s": 12}
    calc = mec.custos_duto({**base, "diametro_modo": "vazao"}, DIST)["parametros"]["diametro_usado_pol"]
    r = mec.custos_duto({**base, "diametro_modo": "vazao_comercial"}, DIST)
    d = r["parametros"]["diametro_usado_pol"]
    assert d == next(x for x in mec.DIAMETROS_COMERCIAIS_POL if x >= calc) and d >= calc
    assert any(x["titulo"] == "Tamanho comercial" for x in r["memoria"]["passos"])
    assert "NPS" in next(x for x in r["memoria"]["passos"] if x["titulo"] == "Tamanho comercial")["explicacao"]


def test_diametro_pela_vazao_pede_o_que_falta_e_recusa_o_gigante():
    with pytest.raises(mec.ErroEconomia, match="Vazão.*Pressão de operação"):
        mec.custos_duto({"diametro_modo": "vazao"}, DIST)
    with pytest.raises(mec.ErroEconomia, match="maior tamanho comercial"):
        mec.custos_duto({"fluido": "ch4", "diametro_modo": "vazao_comercial", "vazao_sm3_d": 5e9, "p_duto_bar": 10,
                         "t_duto_c": 30, "vel_max_m_s": 5}, DIST)
    with pytest.raises(mec.ErroEconomia, match="Diâmetro: use"):
        mec.parametros({"diametro_modo": "magico"})
    with pytest.raises(mec.ErroEconomia, match="fora do intervalo"):
        mec.parametros({"vel_max_m_s": 500})


def test_velocidade_padrao_e_declarada_como_ponto_de_partida():
    r = mec.custos_duto({"fluido": "ch4", "diametro_modo": "vazao", "vazao_sm3_d": 1e6, "p_duto_bar": 80, "t_duto_c": 30}, DIST)
    v = next(e for e in r["memoria"]["entradas"] if e["simbolo"] == "v")
    assert v["valor"] == 15.0 and "não é norma" in v["fonte"]


def test_inflacao_multiplica_o_custo_e_fica_na_memoria():
    inf = {"rotulo": "IPCA", "de": "2024-06", "ate": "2024-09", "meses": 3, "baixado_em": "2026-10-31T10:00:00"}
    sem = mec.custos_duto({"diametro_pol": 8}, DIST)["custo"]["r_por_km"]
    r = mec.custos_duto({"diametro_pol": 8, "corrigir_inflacao": "ipca", "fator_inflacao": 1.25, "inflacao": inf}, DIST)
    assert r["custo"]["r_por_km"] == pytest.approx(sem * 1.25) and r["custo"]["fator_inflacao"] == 1.25
    assert r["custo"]["inflacao"]["ate"] == "2024-09"
    passos = [x["id"] for x in r["memoria"]["passos"]]
    assert passos == ["custo_km", "custo_km_corrigido"]
    f = next(e for e in r["memoria"]["entradas"] if e["simbolo"] == "f_infl")
    assert f["valor"] == 1.25 and "IPCA" in f["fonte"] and "2024-06" in f["fonte"]
    # sem pedir a correção, o fator é ignorado e a memória fica como antes
    ign = mec.custos_duto({"diametro_pol": 8, "fator_inflacao": 1.25}, DIST)
    assert ign["custo"]["r_por_km"] == pytest.approx(sem) and [x["id"] for x in ign["memoria"]["passos"]][0] == "custo_km"
    assert "custo_km_corrigido" not in [x["id"] for x in ign["memoria"]["passos"]]
    with pytest.raises(mec.ErroEconomia, match="Correção pela inflação"):
        mec.parametros({"corrigir_inflacao": "igpm"})


# ---------------------------------------------------------------- camadas ambientais
def test_importar_geojson_e_recusas(tmp_path):
    pasta = str(tmp_path / "proj")
    os.makedirs(pasta)
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"terrai_nom": "Terra X"},
          "geometry": {"type": "Polygon", "coordinates": [[[-36.0, -5.0], [-35.9, -5.0], [-35.9, -4.9], [-36.0, -4.9], [-36.0, -5.0]]]}}]}
    arq = tmp_path / "ti.geojson"
    arq.write_text(json.dumps(gj), encoding="utf-8")
    reg = mca.importar(pasta, "terras_indigenas", str(arq))
    assert reg["feicoes"] == 1 and reg["fonte"] == "Importada" and "arquivo importado" in reg["origem"]
    assert mca.indice(pasta)["camadas"]["terras_indigenas"]["feicoes"] == 1
    fora = tmp_path / "fora.geojson"
    fora.write_text(json.dumps({**gj, "features": [{**gj["features"][0], "geometry": {"type": "Point", "coordinates": [500000, 9000000]}}]}))
    with pytest.raises(mca.ErroCamadas, match="graus"):
        mca.importar(pasta, "terras_indigenas", str(fora))
    (tmp_path / "x.txt").write_text("a")
    with pytest.raises(mca.ErroCamadas, match="zip ou um arquivo"):
        mca.importar(pasta, "terras_indigenas", str(tmp_path / "x.txt"))
    with pytest.raises(mca.ErroCamadas, match="não é importada"):
        mca.importar(pasta, "icmbio_ucs", str(arq))
    r = mca.baixar(pasta, ["terras_indigenas"], sessao=SessaoFalsa({}))
    assert r["erros"] and "Importar" in r["erros"][0]["erro"]


def test_baixar_ucs_do_icmbio_por_wfs(tmp_path):
    pasta = str(tmp_path)
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"nomeuc": "PARQUE X"},
          "geometry": {"type": "MultiPolygon", "coordinates": [[[[-36.0, -5.0], [-35.9, -5.0], [-35.9, -4.9], [-36.0, -5.0]]]]}}]}
    s = SessaoFalsa(gj)
    r = mca.baixar(pasta, ["icmbio_ucs"], sessao=s)
    assert not r["erros"] and r["feitos"][0]["fonte"] == "ICMBio" and r["feitos"][0]["feicoes"] == 1
    url, kw = s.chamadas[0]
    assert "geoservicos.inde.gov.br" in url and kw["params"]["typeName"] == "ICMBio:limiteucsfederais_a"
    assert kw["params"]["srsName"] == "EPSG:4326"
    vazio = mca.baixar(str(tmp_path / "b"), ["icmbio_ucs"], sessao=SessaoFalsa({"type": "FeatureCollection", "features": []}))
    assert "sem feições" in vazio["erros"][0]["erro"]
    assert any(c["id"] == "icmbio_ucs" and c["baixada"] for c in mca.catalogo_com_estado(pasta))


def _projeto_com_uc(tmp_path):
    pasta = str(tmp_path)
    os.makedirs(os.path.join(pasta, "sig", "icmbio"))
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"nomeuc": "PARQUE X", "grupouc": "PI"},
          "geometry": {"type": "Polygon", "coordinates": [[[-35.95, -5.1], [-35.90, -5.1], [-35.90, -4.9], [-35.95, -4.9], [-35.95, -5.1]]]}},
         {"type": "Feature", "properties": {"nomeuc": "LONGE"},
          "geometry": {"type": "Polygon", "coordinates": [[[-30, 0], [-29, 0], [-29, 1], [-30, 0]]]}}]}
    with open(os.path.join(pasta, "sig", "icmbio", "icmbio_ucs.geojson"), "w", encoding="utf-8") as f:
        json.dump(gj, f)
    with open(os.path.join(pasta, "sig", "camadas.json"), "w", encoding="utf-8") as f:
        json.dump({"camadas": {"icmbio_ucs": {"id": "icmbio_ucs", "arquivo": "sig/icmbio/icmbio_ucs.geojson",
                                              "fonte": "ICMBio", "baixado_em": "2026-10-31"}}}, f)
    return pasta


def test_linha_que_atravessa_uma_uc_mede_o_trecho_dentro(tmp_path):
    pasta = _projeto_com_uc(tmp_path)
    # de lon −36,00 a −35,80 em lat −5,0: 0,05° dentro (−35,95 a −35,90) ≈ 5,5 km em 22 km
    r = mvi.cruzamentos_linha(pasta, [-5.0, -36.0], [-5.0, -35.8])
    assert r["comprimento_km"] == pytest.approx(22.2, abs=0.3)
    assert len(r["cruza"]) == 1 and r["cruza"][0]["nome"] == "PARQUE X" and r["cruza"][0]["rotulo"] == "Unidade de Conservação federal"
    assert r["cruza"][0]["km_dentro"] == pytest.approx(5.55, abs=0.25)
    assert r["cruza"][0]["atributos"]["grupouc"] == "PI"
    ui = {c["id"]: c for c in r["camadas"]}
    assert ui["icmbio_ucs"]["baixada"] and ui["terras_indigenas"]["baixada"] is False       # a outra não foi baixada
    livre = mvi.cruzamentos_linha(pasta, [-4.0, -36.0], [-4.0, -35.8])
    assert livre["cruza"] == []


def test_restricoes_do_relatorio_usa_os_dois_pontos_de_cada_medida(tmp_path):
    pasta = _projeto_com_uc(tmp_path)
    d = [{"id": "epe_upgn", "rotulo": "UPGN", "distancia_km": 22.2, "toca_o_campo": False,
          "ponto_campo": [-5.0, -36.0], "ponto_feicao": [-5.0, -35.8]},
         {"id": "epe_gasodutos_transporte", "rotulo": "Gasoduto", "baixada": True, "distancia_km": 0.0, "toca_o_campo": True,
          "ponto_campo": [-5.0, -36.0], "ponto_feicao": [-5.0, -36.0]},
         {"id": "epe_compressao", "rotulo": "Compressão", "baixada": False}]
    r = mvi.restricoes_do_relatorio(pasta, d)
    assert [x["id"] for x in r] == ["epe_upgn"] and r[0]["cruza"][0]["nome"] == "PARQUE X"


def test_pela_ponte_restricoes_e_inflacao(api, tmp_path, monkeypatch):
    api.escolher_pasta()
    pasta = api._projeto.pasta
    # camada de UCs no projeto e um relatório de distâncias fabricado
    os.makedirs(os.path.join(pasta, "sig", "icmbio"))
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"nomeuc": "PARQUE X"},
          "geometry": {"type": "Polygon", "coordinates": [[[-35.95, -5.1], [-35.90, -5.1], [-35.90, -4.9], [-35.95, -4.9], [-35.95, -5.1]]]}}]}
    with open(os.path.join(pasta, "sig", "icmbio", "icmbio_ucs.geojson"), "w", encoding="utf-8") as f:
        json.dump(gj, f)
    with open(os.path.join(pasta, "sig", "camadas.json"), "w", encoding="utf-8") as f:
        json.dump({"camadas": {"icmbio_ucs": {"id": "icmbio_ucs", "arquivo": "sig/icmbio/icmbio_ucs.geojson",
                                              "fonte": "ICMBio", "baixado_em": "x"}}}, f)
    rel = {"campo": "C", "poligono": [], "fonte_poligono": "t", "deplecao": None,
           "distancias": [{"id": "epe_upgn", "rotulo": "UPGN", "baixada": True, "distancia_km": 22.2, "toca_o_campo": False,
                           "ponto_campo": [-5.0, -36.0], "ponto_feicao": [-5.0, -35.8]}]}
    monkeypatch.setattr(api, "_relatorio_vb", lambda campo: rel)
    r = api.viabilidade_restricoes("C")
    assert r["ok"] and r["linhas"][0]["cruza"][0]["nome"] == "PARQUE X"
    assert "Escolha o campo" in api.viabilidade_restricoes("")["erro"]
    # inflação: fator calculado pela série (sessão falsa no lugar da rede)
    monkeypatch.setattr(mix, "baixar_serie", lambda indice, sessao=None, timeout=60:
                        [[2024, 6, 0.21], [2024, 7, 1.0], [2024, 8, 1.0]])
    pr = api._com_inflacao({"corrigir_inflacao": "ipca", "fonte_custo": "pig2024"})
    assert pr["fator_inflacao"] == pytest.approx(1.01 * 1.01) and pr["inflacao"]["de"] == "2024-06"
    assert api._com_inflacao({"corrigir_inflacao": "nao"})["fator_inflacao"] == 1.0
    manual = api._com_inflacao({"corrigir_inflacao": "ipca", "custo_mil_pol_km": "400", "data_base_custo": "2024-07"})
    assert manual["fator_inflacao"] == pytest.approx(1.01) and manual["inflacao"]["de"] == "2024-07"
    with pytest.raises(Exception, match="data-base"):
        api._com_inflacao({"corrigir_inflacao": "ipca", "custo_mil_pol_km": "400"})
