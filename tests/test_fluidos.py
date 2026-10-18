"""API e densidade do gás a partir dos documentos dos poços (índice de texto e dados transcritos)."""
import pytest

from motor import documentos as md
from motor import economia as mec
from motor import fluidos as mfl
from motor import producao as mpr
from motor.banco import Banco


@pytest.mark.parametrize("texto,esperado", [
    ("Óleo de 32,5 °API e RGO 45", [("api", 32.5)]),
    ("Grau API: 28", [("api", 28.0)]),
    ("API = 31.2", [("api", 31.2)]),
    ("25ºAPI", [("api", 25.0)]),
    ("API gravity 33", [("api", 33.0)]),
    ("densidade api do oleo 19,8", [("api", 19.8)]),
    ("densidade do gás (ar = 1): 0,652", [("densidade_gas", 0.652)]),
    ("Dens. rel. gás 0,71", [("densidade_gas", 0.71)]),
    ("Gás specific gravity 0.68", [("densidade_gas", 0.68)]),
    # não são API: especificação de tubo, frações de polegada, formulário em branco, fora da faixa
    ("revestimento 9 5/8 API 5CT N-80", []), ("5 1/2 API", []), ("API 5L X52", []),
    ("API (para %BSW): DENS.(CNTP)=", []), ("Grau API: 95", []), ("densidade do gás 2,5", []),
])
def test_leitura_de_valores(texto, esperado):
    assert [(x["grandeza"], x["valor"]) for x in mfl.ler_valores(texto)] == esperado


def test_classificar_nome_do_dado_transcrito():
    assert mfl.classificar("Grau API do óleo") == "api"
    assert mfl.classificar("Densidade relativa do gás") == "densidade_gas"
    assert mfl.classificar("RGO") is None


def _projeto(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    with b.conexao() as c:
        for pid, campo in (("7-AA-1-RN", "CAMPO TESTE"), ("7-AA-2-RN", "CAMPO TESTE"), ("1-ZZ-9-RN", "OUTRO")):
            c.execute("INSERT INTO pocos (id, nome_anp, campo) VALUES (?, ?, ?)", (pid, pid, campo))
    ind = md.Indice(str(tmp_path / "texto" / "indice.sqlite"))
    pag = lambda n, t, m="ocr": {"pagina": n, "texto": t, "metodo": m, "titulo": ""}  # noqa: E731
    ind.substituir_documento("bruto/Potiguar/7AA_0001__RN/pasta.pdf", "Potiguar", "7AA_0001__RN", "pasta.pdf",
                             [pag(3, "TESTE DE FORMAÇÃO óleo de 28,5 °API, densidade do gás 0,70"),
                              pag(7, "ANÁLISE DE ÓLEO  API (para %BSW): DENS.(CNTP)=")])
    ind.substituir_documento("bruto/Potiguar/7-AA-2-RN/rfp.pdf", "Potiguar", "7-AA-2-RN", "rfp.pdf",
                             [pag(1, "Grau API: 30", "embutido")])
    ind.substituir_documento("bruto/Potiguar/1-ZZ-9-RN/x.pdf", "Potiguar", "1-ZZ-9-RN", "x.pdf",
                             [pag(1, "óleo de 40 °API")])
    return b, ind.caminho


def test_resumo_leituras_paginas_e_escolha(tmp_path):
    b, caminho = _projeto(tmp_path)
    docs = [{"rel": "bruto/Potiguar/7AA_0001__RN/pasta.pdf", "poco": "7AA_0001__RN", "situacao": "processado"},
            {"rel": "bruto/Potiguar/7-AA-2-RN/novo.pdf", "poco": "7-AA-2-RN", "situacao": "pendente"},
            {"rel": "bruto/Potiguar/1-ZZ-9-RN/x.pdf", "poco": "1-ZZ-9-RN", "situacao": "processado"}]
    r = mfl.resumo(b, caminho, "Campo Teste", docs)
    assert r["pocos"] == ["7-AA-1-RN", "7-AA-2-RN"]                    # o poço de outro campo fica de fora
    assert r["documentos"] == {"total": 2, "processados": 1, "pendentes": ["bruto/Potiguar/7-AA-2-RN/novo.pdf"]}
    lidas = {(x["poco"], x["grandeza"], x["valor"], x["pagina"]) for x in r["leituras"]}
    assert lidas == {("7-AA-1-RN", "api", 28.5, 3), ("7-AA-1-RN", "densidade_gas", 0.70, 3), ("7-AA-2-RN", "api", 30.0, 1)}
    assert [(x["poco"], x["pagina"]) for x in r["paginas"]] == [("7-AA-1-RN", 7)]
    e = r["escolha"]
    assert e["api"]["valor"] == pytest.approx(29.25) and e["api"]["origem"] == "leitura" and e["api"]["ocr"] == 1
    assert "pasta.pdf p. 3" in e["api"]["fonte"] and "confira" in e["api"]["fonte"]
    assert e["densidade_gas"]["valor"] == pytest.approx(0.70)
    # descartar uma leitura
    chave = next(x["chave"] for x in r["leituras"] if x["valor"] == 28.5)
    mpr.guardar_campo(b, "Campo Teste", fluidos_descartados=[chave])
    r = mfl.resumo(b, caminho, "Campo Teste", docs)
    assert r["escolha"]["api"]["valor"] == 30.0 and any(x["descartada"] for x in r["leituras"])
    # dado transcrito vence a leitura automática
    b.salvar_fato({"id": None, "poco_id": "7-AA-1-RN", "tipo": "propriedade_fluido", "nome": "Grau API do óleo",
                   "valor": "26,0", "unidade": "°API", "prof_topo": None, "prof_base": None, "autor": "t",
                   "origem": "local", "fonte_rel": "bruto/Potiguar/7AA_0001__RN/pasta.pdf", "pagina": 3})
    r = mfl.resumo(b, caminho, "Campo Teste", docs)
    assert r["escolha"]["api"] == {"valor": 26.0, "origem": "transcrito", "n": 1,
                                   "fonte": "dado transcrito: 7-AA-1-RN (pasta.pdf p. 3) = 26,0"}
    assert r["escolha"]["densidade_gas"]["origem"] == "leitura"


def test_viabilidade_usa_o_que_veio_dos_documentos(tmp_path):
    b, caminho = _projeto(tmp_path)
    mpr.guardar_campo(b, "Campo Teste", ficha={"nome": "CAMPO TESTE", "inicio_producao": "2010"},
                      pd={"fonte": "BAR", "acumulada": {"data": "31/12/2021", "oleo_milhoes_m3": 1.0,
                                                        "gas_total_milhoes_m3": 100.0}})
    sug = mfl.resumo(b, caminho, "Campo Teste")["escolha"]
    dist = [{"id": "epe_upgn", "rotulo": "UPGN", "baixada": True, "distancia_km": 5.0}]
    av = mec.avaliar(b, "Campo Teste", dist, {"pressao_bar": 61, "temperatura_c": 43}, sug)
    ent = {e["simbolo"]: e for e in av["memoria"]["entradas"]}
    assert ent["API"]["valor"] == pytest.approx(29.25) and "lido automaticamente" in ent["API"]["fonte"]
    assert ent["gg"]["valor"] == pytest.approx(0.70)
    assert av["metodos"]["poroso"]["estimados"] == ["Rs (Standing)", "Bo (Standing)", "Bg (Sutton + Papay)"]
    assert any("leitura automática dos documentos" in a for a in av["avisos"])
    # o que o usuário digita vence
    av = mec.avaliar(b, "Campo Teste", dist, {"pressao_bar": 61, "temperatura_c": 43, "api": 35}, sug)
    ent = {e["simbolo"]: e for e in av["memoria"]["entradas"]}
    assert ent["API"]["valor"] == 35 and ent["API"]["fonte"] == "informado pelo usuário"
