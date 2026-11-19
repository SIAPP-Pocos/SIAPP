"""Tela "Apoie o projeto" (0.67): leitura de recursos/doacao.json e o Pix "copia e cola" (BR Code estático)."""
import json

from motor import doacao as mdo

# Exemplo de BR Code estático do Manual de Padrões para Iniciação do Pix (Banco Central)
EXEMPLO_BCB = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR"
               "5913Fulano de Tal6008BRASILIA62070503***63041D3D")


def _grava(tmp_path, dados):
    p = tmp_path / "doacao.json"
    p.write_text(json.dumps(dados) if not isinstance(dados, str) else dados, encoding="utf-8")
    return str(p)


def test_br_code_igual_ao_exemplo_do_banco_central():
    assert mdo.pix_copia_e_cola("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", "BRASILIA") == EXEMPLO_BCB


def test_br_code_tira_acentos_e_corta_nome_e_cidade():
    s = mdo.pix_copia_e_cola("a@b.com", "José da Conceição Nogueira Albuquerque", "Maceió")
    assert "59" + "25" + "Jose da Conceicao Nogueir" in s and "6006Maceio" in s
    assert s[-8:-4] == "6304" and s[-4:] == mdo._crc16(s[:-4])


def test_repositorio_com_a_chave_do_autor():
    r = mdo.ler()                                       # recursos/doacao.json do repositório (0.67.2: chave aleatória)
    assert r["ativo"] and r["pix"]["tipo"] == "aleatória" and r["pix"]["nome"] == "Ruan da Silva Nobre"
    s = r["pix"]["copia_e_cola"]
    assert s.startswith("000201") and "br.gov.bcb.pix" in s and s[-4:] == mdo._crc16(s[:-4])


def test_tipo_da_chave():
    assert [mdo.tipo_da_chave(c) for c in ("+5582999999999", "a@b.com", "12345678909", "12345678000199",
                                           "123e4567-e12b-12d1-a456-426655440000")] == \
        ["celular", "e-mail", "CPF", "CNPJ", "aleatória"]


def test_ligado_com_pix_e_link(tmp_path):
    r = mdo.ler(_grava(tmp_path, {"pix": {"chave": "a@b.com", "nome": "Fulano", "cidade": "Maceio"},
                                  "links": [{"rotulo": "Apoia", "url": "https://exemplo.org/siapp"},
                                            {"rotulo": "ruim", "url": "http://exemplo.org"}]}))
    assert r["ativo"] and r["pix"]["copia_e_cola"].startswith("000201") and r["titulo"] == mdo.TITULO_PADRAO
    assert [l["rotulo"] for l in r["links"]] == ["Apoia"] and any("https" in a for a in r["avisos"])


def test_pix_incompleto_ou_desligado_nao_mostra(tmp_path):
    r = mdo.ler(_grava(tmp_path, {"pix": {"chave": "a@b.com"}}))           # sem nome e cidade
    assert not r["ativo"] and r["avisos"]
    assert not mdo.ler(_grava(tmp_path, {"ativo": False, "links": [{"url": "https://exemplo.org"}]}))["ativo"]
    assert not mdo.ler(_grava(tmp_path, "{quebrado"))["ativo"]
    assert not mdo.ler(str(tmp_path / "nao-existe.json"))["ativo"]


def test_api_doacao(api):
    assert api.doacao()["ok"] and api.doacao()["ativo"] is True


# ---------------------------------------------------------------- 1.3: quem faz o SIAPP, valores e QR Code
def test_pix_com_valor_tem_o_campo_54_e_crc_certo():
    r = mdo.pix_com_valor(mdo.ler(), 15)
    s = r["copia_e_cola"]
    assert r["valor"] == 15.0 and "540515.00" in s and s[-4:] == mdo._crc16(s[:-4])
    sem = mdo.pix_com_valor(mdo.ler(), None)
    assert sem["valor"] is None and "5405" not in sem["copia_e_cola"] and sem["copia_e_cola"] == mdo.ler()["pix"]["copia_e_cola"]


def test_valor_digitado():
    assert mdo.valor_valido("12,5") == 12.5 and mdo.valor_valido(" 7 ") == 7.0
    for ruim in ("", "abc", "0", "-3", "100000", None):
        assert mdo.valor_valido(ruim) is None
    import pytest
    with pytest.raises(ValueError):
        mdo.pix_com_valor(mdo.ler(), "-1")


def test_qr_code_em_svg():
    svg = mdo.qr_svg("teste")
    assert svg.startswith("<svg") and 'xmlns="http://www.w3.org/2000/svg"' in svg     # sem xmlns a tela não desenha


def test_repositorio_tem_quem_faz_e_valores():
    r = mdo.ler()
    assert len(r["sobre"]) >= 3 and r["sobre"][0].startswith("Olá! Meu nome é Ruan da Silva Nobre")
    assert [v["rotulo"] for v in r["valores"]] == ["Um cafezinho", "Um lanche", "Uma tarde de código"]
    assert [v["valor"] for v in r["valores"]] == [5.0, 15.0, 30.0]
    assert "opcional" in r["texto"]


def test_linkedin_e_valores_validados(tmp_path):
    base = {"pix": {"chave": "a@b.com", "nome": "Fulano", "cidade": "Maceio"}}
    r = mdo.ler(_grava(tmp_path, {**base, "linkedin": "https://www.linkedin.com/in/fulano-de-tal/"}))
    assert r["linkedin"] == "https://www.linkedin.com/in/fulano-de-tal/" and not r["avisos"]
    r = mdo.ler(_grava(tmp_path, {**base, "linkedin": "http://exemplo.com/fulano",
                                  "valores": [{"rotulo": "Ok", "valor": 3}, {"rotulo": "", "valor": 2},
                                              {"rotulo": "Ruim", "valor": -1}]}))
    assert r["linkedin"] == "" and any("LinkedIn" in a for a in r["avisos"])
    assert r["valores"] == [{"rotulo": "Ok", "valor": 3.0}]
    assert [v["valor"] for v in mdo.ler(_grava(tmp_path, base))["valores"]] == [5.0, 15.0, 30.0]    # sem "valores": os padrões


def test_api_doacao_pix(api):
    r = api.doacao_pix(30)
    assert r["ok"] and "540530.00" in r["copia_e_cola"] and r["qr_svg"].startswith("<svg")
    assert api.doacao_pix("xyz")["ok"] is False


def test_publicacoes_dos_pibics(tmp_path):
    r = mdo.ler()
    assert r["publicacoes"] and all(p["url"].startswith("https://") for p in r["publicacoes"])
    base = {"pix": {"chave": "a@b.com", "nome": "Fulano", "cidade": "Maceio"}}
    r = mdo.ler(_grava(tmp_path, {**base, "publicacoes": [{"titulo": "A", "evento": "X 2024", "url": "ftp://x"},
                                                          {"titulo": ""}, "lixo"]}))
    assert r["publicacoes"] == [{"titulo": "A", "evento": "X 2024", "url": ""}] and r["avisos"]
