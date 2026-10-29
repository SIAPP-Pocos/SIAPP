"""Leitor dos formulários CDPE da ANP (RFP, RFCP, Perfuração), com PDFs sintéticos."""
import pymupdf
import pytest

import rfp_util as u
from motor import rfp


@pytest.fixture(scope="module")
def pdfs(tmp_path_factory):
    d = tmp_path_factory.mktemp("cdpe")
    return {nome: rfp.ler(u.gerar(str(d / f"1-SIAPP-1-RN_CDPE_{k}_{nome}.pdf"), getattr(u, nome.upper())))
            for k, nome in ((7, "RFP"), (8, "RFCP"), (1, "Perfuracao"))}


def test_numeros_coordenadas_e_nomes():
    assert rfp.numero("1.948,50") == 1948.5 and rfp.numero("-1.854,40") == -1854.4
    assert rfp.numero("88,5") == 88.5 and rfp.numero("4") == 4.0
    assert rfp.numero("12 1/4") is None and rfp.numero("08/06/2015") is None and rfp.numero("UGT-35,0") is None
    assert rfp.grau_decimal("-12:04:45,845") == pytest.approx(-12.0794014, abs=1e-6)
    assert rfp.grau_decimal("-38:01:29,412") == pytest.approx(-38.0248367, abs=1e-6)
    assert rfp.reconhece_nome("1-BRSA-1304-BA_CDPE_7_RFP.pdf")
    assert rfp.reconhece_nome("3-BRSA-1151-RN_CDPE_7_RFCP_1.pdf")
    assert rfp.reconhece_nome("1-BRSA-1304-BA_CDPE_1_Perfuracao.pdf")
    assert not rfp.reconhece_nome("1-BRSA-1304-BA_agp.txt") and not rfp.reconhece_nome("perfil_RFP.las")
    assert not rfp.reconhece_nome("relatorio_geologico.pdf")


def test_rfp_dados_gerais_e_coordenadas(pdfs):
    d = pdfs["RFP"]
    assert d["documento"] == "rfp" and d["paginas"] == 3
    g = d["gerais"]
    assert g["poco"] == "1-SIAPP-1-RN" and g["bacia"] == "Potiguar" and g["bloco"] == "POT-T-999"
    assert g["prof_sondador"] == 1850.0 and g["prof_perfil_medida"] == 1852.5 and g["prof_perfil_cota"] == -1740.3
    assert g["mesa_rotativa"] == 112.2 and g["elevacao"] == 106.2 and g["lamina_agua"] == 0.0
    assert g["unidade_prof_final"] == "FM PENDÊNCIA" and g["descobridor"] == "S" and g["fluido_descoberto"] == "ÓLEO"
    assert g["termino_perfuracao"] == "02/03/2010" and g["conclusao"] == "20/03/2010"
    assert "prof_prevista" not in g          # "medida (m) :" do perfil não é a profundidade prevista
    assert g["coordenadas"]["base"] == {"lat": -5.5, "lon": -37.26}
    assert g["coordenadas"]["alvo"]["lat"] == pytest.approx(-5.5005) and "fundo" not in g["coordenadas"]


def test_rfp_topos_com_vazio_do_formulario(pdfs):
    topos = pdfs["RFP"]["topos"]
    assert [t["unidade"] for t in topos] == ["FM BARREIRAS", "FM JANDAÍRA", "FM AÇU", "FM PENDÊNCIA"]
    assert topos[0]["prof"] == 0.0 and topos[0]["cota"] == 106.2       # 0 m com cota: superfície, vale
    assert topos[2]["prev_medida"] == 780.0 and topos[2]["prof"] == 801.5 and topos[2]["cota"] == -689.3
    assert topos[3]["prev_medida"] is None and topos[3]["prof"] == 1402.0  # sem previsão (0,0 e 0,0)


def test_rfp_indicios_continuam_na_pagina_seguinte_e_celula_de_duas_linhas(pdfs):
    ind = pdfs["RFP"]["indicios"]
    assert [(i["topo"], i["base"]) for i in ind] == [(812.0, 815.0), (1390.0, 1410.0), (1500.0, 1501.0)]
    assert ind[1]["unidade"] == "FM AÇU/PENDÊNCIA" and ind[1]["fluorescencia"] == "EP" and ind[1]["corte"] == "LT"
    assert ind[2]["pagina"] == 2 and ind[2]["ocorrencia"] == "D" and ind[2]["gas_total"] == "UGT-40,0"


def test_rfp_testes_temperaturas_calha_e_observacoes(pdfs):
    d = pdfs["RFP"]
    tfr, pt, tca = d["testes"]
    assert tfr["tipo"] == "TFR" and (tfr["topo"], tfr["base"]) == (1395.0, 1400.0) and tfr["api"] == 31.2
    assert tfr["vazao_m3_dia"] == 45.5 and tfr["pressao_estatica_kgf_cm2"] == 141.7 and tfr["prof_registrador"] == 1398.0
    assert pt["base"] is None and pt["api"] is None and pt["vazao_m3_dia"] is None and pt["pressao_estatica_kgf_cm2"] == 143.9
    assert tca["fluido"] == "FILTRADO/ ÁGUA FORMAÇÃO"
    t0, t1 = d["temperaturas"]
    assert (t0["valor"], t0["prof"], t0["tipo"]) == (80.0, 0.0, "lida")
    assert (t1["valor"], t1["prof"], t1["tipo"], t1["origem"]) == (158.0, 1850.0, "extrapolada", "PERFILAGEM FINAL")
    assert [(c["topo"], c["base"], c["padrao"]) for c in d["calha"]] == [(9.0, 600.0, "9 em 9 metros"),
                                                                         (600.0, 1850.0, "3 em 3 metros")]
    assert d["testemunhos"][0]["recuperacao_pct"] == 88.0 and d["testemunhos"][0]["litologia"] == "ARENITO MÉDIO"
    assert d["analise_perfis"] == [{"topo": 1392.0, "base": 1406.5, "unidade": "FM AÇU", "litologia": "ARENITO",
                                    "pagina": 2}]
    assert d["laterais"] == [] and d["observacoes"].splitlines()[1] == "Segunda linha da observação."


def test_rfcp_canhoneados_teste_e_sigla_antiga(pdfs):
    d = pdfs["RFCP"]
    assert d["documento"] == "rfcp" and d["gerais"]["termino_completacao"] == "10/04/2010"
    assert d["canhoneados"][0] == {"unidade": "FM. AÇU", "topo": 1396.0, "base": 1401.0, "canhao": "HSD",
                                   "densidade_tiros_pe": 6.0, "pagina": 1}
    assert d["revestimentos"][0]["diametro"] == "5 1/2" and d["revestimentos"][0]["grau"] == "J-55"
    assert d["coluna"][0]["equipamento"] == 'ÚNICA: TUBING: SIMPLES 2.7/8" EU'
    t = d["testes_completacao"][0]
    assert t["vazao_m3_dia"] == 45.5 and t["bsw_pct"] == 1.0 and t["pressao_fluxo_kgf_cm2"] == 120.4
    assert t["densidade_gas"] is None and d["apelidos"] == ["1-ABC-1-RN"]


def test_perfuracao_fases_com_fluido_e_coordenadas_em_linha(pdfs):
    d = pdfs["Perfuracao"]
    g = d["gerais"]
    assert d["documento"] == "perfuracao" and g["cadastro"] == "99999999999" and g["nome_operador"] == "1ABC1RN"
    assert g["prof_prevista"] == 1800.0 and g["cota_prevista"] == 1690.0 and g["categoria"] == "Pioneiro"
    assert g["coordenadas"]["alvo"]["lat"] == pytest.approx(-5.5005) and g["coordenadas"]["base"]["lon"] == -37.26
    f1, f2 = d["fases"]
    assert f1["rev_diametro"] == "13 3/8" and f1["rev_prof"] == 58.0 and f1["fluido"] is None
    assert f2["fluido"] == "CATIÔNICO" and f2["peso_lb_gal"] == 9.6 and f2["cimento_topo"] == 900.0
    assert d["tempos"][0]["total_d"] == 2.5


def test_itens_para_o_banco(pdfs):
    its = rfp.itens(pdfs["RFP"])
    tipos = [i["tipo"] for i in its]
    assert tipos.count("topo") == 4 and tipos.count("indicio") == 3 and tipos.count("teste_formacao") == 3
    temp = [i for i in its if i["tipo"] == "temperatura"]
    assert temp[1]["unidade"] == "°F" and temp[1]["valor"] == 158.0 and temp[1]["texto"] == "extrapolada"
    fase = [i for i in rfp.itens(pdfs["Perfuracao"]) if i["tipo"] == "fase"][1]
    assert fase["valor"] == 9.6 and fase["unidade"] == "lb/gal" and fase["prof_base"] == 1850.0


def test_pdf_que_nao_e_formulario(tmp_path):
    vazio = tmp_path / "x_CDPE_1_RFP.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(vazio))
    with pytest.raises(rfp.ErroRFP, match="texto embutido"):
        rfp.ler(str(vazio))
    outro = tmp_path / "y_RFP.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 200), "Relatório geológico qualquer", fontsize=10)
    doc.save(str(outro))
    with pytest.raises(rfp.ErroRFP, match="não é um formulário|Não é um formulário"):
        rfp.ler(str(outro))
    (tmp_path / "z_RFP.pdf").write_bytes(b"isto nao e pdf")
    with pytest.raises(rfp.ErroRFP):
        rfp.ler(str(tmp_path / "z_RFP.pdf"))


def test_descoberta_perfilagens_e_reentrada(tmp_path):
    nd = rfp.ler(u.gerar(str(tmp_path / "x_CDPE_3_ND_1.pdf"), u.ND))
    assert nd["documento"] == "nd" and nd["campos"] == {"data_notificacao": "05/03/2010",
                                                         "data_descoberta": "01/03/2010", "fluidos": "Petróleo"}
    assert [(i["topo"], i["ocorrencia"], i["fluorescencia"], i["gas_total"]) for i in nd["indicios"]] == [
        (812.0, "C", "R", None), (1450.0, "D", None, "UGT - 20,0")]
    assert nd["analise_perfis"][0]["litologia"] == "ARENITO" and nd["testes"][0]["api"] == 30.0
    assert nd["secoes_texto"] == [{"titulo": "Estado atual do poço", "texto": "Aguardando a perfilagem final."}]
    npr = rfp.ler(u.gerar(str(tmp_path / "x_CDPE_2_NPR_1.pdf"), u.NPR))
    assert npr["documento"] == "npr" and "analise_perfis" not in npr     # "Perfis" de coluna não é seção
    assert [(p["tipo"], p["perfis"], p["topo"], p["base"]) for p in npr["perfilagens"]] == [
        ("convencional", "GR", 60.0, 1845.0), ("convencional", "SDL (CAL)", 60.0, 1848.0),
        ("especial", "SFT/GR", 1420.0, None)]
    assert npr["perfilagens_resultado"] == [{"n": 3, "perfis": "SFT/GR", "pretestes_conclusivos": 4.0,
                                             "pretestes_falhos": 1.0, "pagina": 1}]
    assert npr["campos"]["conclusao_perfilagem"] == "02/03/2010"
    re_ = rfp.ler(u.gerar(str(tmp_path / "x_CDPE_4_Reentrada_1.pdf"), u.REENTRADA))
    assert re_["documento"] == "reentrada" and re_["campos"]["prof_final"] == 1850.0
    assert re_["campos"]["sonda"] == "SPT-00" and re_["campos"]["estado_atual"] == "Poço Equipado."
    assert [s["titulo"] for s in re_["secoes_texto"]] == ["Motivo da reentrada", "Operações previstas",
                                                          "Resultado", "Dados adquiridos"]
    assert "sonda" not in re_["gerais"] and re_["gerais"]["poco"] == "1-SIAPP-1-RN"


def test_cdpe_de_titulo_desconhecido(tmp_path):
    outro = [[(200, 110, "COMUNICAÇÃO DE ABANDONO DE POÇO"), (262, 136, "DADOS GERAIS"),
              (23, 163, "Poço:"), (23, 176, "1-SIAPP-1-RN"), (23, 300, "Texto livre do formulário.")]]
    d = rfp.ler(u.gerar(str(tmp_path / "x_CDPE_9_Abandono.pdf"), outro))
    assert d["documento"] == "cdpe" and d["titulo_formulario"] == "COMUNICAÇÃO DE ABANDONO DE POÇO"
    assert "Texto livre do formulário." in d["texto"] and d["gerais"]["poco"] == "1-SIAPP-1-RN"
