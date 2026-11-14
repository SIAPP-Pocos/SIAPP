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


def test_repositorio_vem_desligado():
    r = mdo.ler()                                       # recursos/doacao.json do repositório: sem chave nem link
    assert r["ativo"] is False and r["pix"] is None and r["links"] == []


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
    assert api.doacao()["ok"] and api.doacao()["ativo"] is False
