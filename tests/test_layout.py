"""Texto remontado das caixas do OCR, dicionário, revisão de página e busca com filtro (0.31).
Caixas sintéticas: nenhum arquivo original do REATE entra nos testes."""
import os

from motor import dicionario as mdic
from motor import layout as ml


def linha(y, *pecas, h=0.012, letra=0.006):
    """Palavras de uma linha do OCR: mesma caixa vertical; cada peça é (x0, texto)."""
    return [[x, y, x + letra * len(t), y + h, t] for x, t in pecas]


def caixas(y, x, texto, h=0.012, letra=0.006, espaco=0.006):
    """Uma linha de texto corrido a partir de x."""
    out = []
    for w in texto.split():
        out.append([x, y, x + letra * len(w), y + h, w])
        x += letra * len(w) + espaco
    return out


def test_pedacos_da_mesma_linha_em_blocos_diferentes_viram_uma_linha():
    # o Tesseract leu "Setor", "de" e "Avaliação" em blocos separados (caixas diferentes)
    ws = [[0.10, 0.100, 0.13, 0.112, "Setor"], [0.136, 0.101, 0.148, 0.113, "de"],
          [0.154, 0.099, 0.208, 0.111, "Avaliação"]]
    assert ml.reconstruir(ws) == "Setor de Avaliação"


def test_formulario_fica_em_colunas_e_linhas_separadas():
    ws = (linha(0.10, (0.10, "POÇO:"), (0.14, "7-GMR-13-RN"), (0.55, "CAMPO:"), (0.59, "GUAMARÉ"))
          + linha(0.13, (0.10, "Sonda:"), (0.15, "SC-71")))
    assert ml.reconstruir(ws) == "POÇO: 7-GMR-13-RN    CAMPO: GUAMARÉ\nSonda: SC-71"


def test_texto_corrido_vira_paragrafo_e_hifen_some():
    frase1 = "O revestimento foi descido sem problemas e a cimen-"
    frase2 = "tação ocorreu com retorno de pasta na superfície."
    frase3 = "Novo parágrafo depois de um espaço grande."
    ws = caixas(0.10, 0.10, frase1) + caixas(0.115, 0.10, frase2) + caixas(0.16, 0.10, frase3)
    t = ml.reconstruir(ws)
    assert t == ("O revestimento foi descido sem problemas e a cimentação ocorreu com retorno de pasta "
                 "na superfície.\n\nNovo parágrafo depois de um espaço grande.")


def test_sujeira_e_letras_soltas_saem():
    ws = (linha(0.10, (0.02, "|"), (0.10, "RELATÓRIO"), (0.17, "GEOLÓGICO"), (0.90, "i"))
          + linha(0.13, (0.50, "—"))          # risco sozinho numa linha
          + linha(0.16, (0.95, "s")))         # letra solta na borda
    assert ml.reconstruir(ws) == "RELATÓRIO GEOLÓGICO"


def test_palavra_partida_junta_so_quando_faz_sentido():
    conhecida = ml.conhecida_por(["Avaliação", "aponta", "ponta", "a", "Avalia"])
    letra = 0.006
    # "Avalia" + "ção" com um espaço pequeno: "ção" não é palavra → junta
    ws = [[0.10, 0.1, 0.10 + 6 * letra, 0.112, "Avalia"], [0.10 + 6 * letra + 0.004, 0.1, 0.10 + 9 * letra + 0.004, 0.112, "ção"]]
    assert ml.reconstruir(ws, conhecida) == "Avaliação"
    # "a" + "ponta": as duas são palavras → continuam separadas, mesmo "aponta" existindo
    ws = [[0.10, 0.1, 0.106, 0.112, "a"], [0.110, 0.1, 0.140, 0.112, "ponta"],
          [0.146, 0.1, 0.170, 0.112, "fina"]]
    assert ml.reconstruir(ws, conhecida) == "a ponta fina"
    # peças coladas (espaço ~0) juntam mesmo sem vocabulário
    ws = [[0.10, 0.1, 0.13, 0.112, "PERFU"], [0.1302, 0.1, 0.154, 0.112, "RAÇÃO"]]
    assert ml.reconstruir(ws) == "PERFURAÇÃO"


def test_linhas_vizinhas_com_caixas_altas_nao_se_misturam():
    # caixas do OCR mais altas que a letra: as de duas linhas vizinhas se sobrepõem
    ws = linha(0.100, (0.1, "PRIMEIRA"), (0.16, "LINHA"), h=0.03) + linha(0.118, (0.1, "SEGUNDA"), (0.16, "LINHA"), h=0.03)
    assert ml.reconstruir(ws).replace("\n", " ") == "PRIMEIRA LINHA SEGUNDA LINHA"   # não "PRIMEIRA SEGUNDA…"


def test_vocabulario_do_corpus():
    v = ml.vocabulario_do_corpus(["folhelho cinza", "folhelho", "Folhelho e arenito", "arenito"], minimo=3)
    assert v == {"FOLHELHO"}


# ------------------------------------------------------------ dicionário
def test_dicionario_conhece_sugere_e_respeita_maiusculas():
    d = mdic.padrao()
    assert d.conhece("avaliação") and d.conhece("AVALIACAO") and not d.conhece("revestimcnto")
    assert d.forma("AVALIACAO") == "AVALIAÇÃO"
    assert d.sugerir("revestimcnto")[0] == "revestimento"
    assert d.sugerir("Sondagern")[0] == "Sondagem"         # rn lido no lugar de m
    assert d.sugerir("Perfura1ção")[0] == "Perfuração"     # 1 no lugar de l/i... ou sobrando
    assert d.sugerir("avaliação") == []


def test_dicionario_sem_arquivo_nao_quebra(tmp_path):
    d = mdic.Dicionario(str(tmp_path / "nao_existe.txt.gz"))
    assert not d.conhece("casa") and d.sugerir("casa") == [] and len(d) == 0


def test_possiveis_erros_ignora_siglas_codigos_e_palavras_conhecidas():
    texto = ("POÇO 7-GMR-13-RN GMR revestimcnto revestimcnto Perfura1ção folhelho cimentação "
             "Wireline sondagern")
    conhecida = ml.conhecida_por(["folhelho"])
    erros = mdic.possiveis_erros(texto, conhecida, mdic.padrao(), ignorar=lambda w: w == "Wireline")
    por = {e["palavra"]: e for e in erros}
    assert list(por) == ["revestimcnto", "Perfura1ção", "sondagern"]
    assert por["revestimcnto"]["vezes"] == 2 and por["revestimcnto"]["sugestoes"][0] == "revestimento"


# ------------------------------------------------------------ ponte: revisão, filtro, erros
def _documento(api, tmp_path, poco, nome, linhas, bacia="Potiguar"):
    import pymupdf
    from motor import documentos as md
    pasta = os.path.join(api._projeto.pasta, "bruto", bacia, poco, "Pasta de Poco")
    os.makedirs(pasta, exist_ok=True)
    doc = pymupdf.open()
    for texto in linhas:
        doc.new_page().insert_text((72, 100), texto, fontsize=11)
    doc.save(os.path.join(pasta, nome))
    rel = f"bruto/{bacia}/{poco}/Pasta de Poco/{nome}"
    r = md.processar_arquivo(os.path.join(pasta, nome), tessdata=str(tmp_path))
    api._projeto.salvar_texto(rel, r)
    api._reindexar_documento(rel)
    return rel


def test_revisar_o_texto_da_pagina_vale_na_pagina_e_na_busca(api, tmp_path):
    api.escolher_pasta()
    rel = _documento(api, tmp_path, "7-GMR-13-RN", "a.pdf", ["SAPATA DO REVESTIMENTO revestimcnto NO amanheccr",
                                                              "outra pagina do relatorio diario de perfuracao"])
    v = api.ver_pagina(rel, 1)
    assert v["modo_texto"] in ("remontado", "ocr") and v["revisao"] is None
    assert any(e["palavra"] == "amanheccr" for e in v["possiveis_erros"])
    assert "SAPATA" in v["texto_editavel"] and v["texto_ocr"]
    r = api.salvar_texto_pagina(rel, 1, "Sapata do revestimento a 1234 m.\r\n\r\nCimentação com retorno.  ")
    assert r["ok"]
    v = api.ver_pagina(rel, 1)
    assert v["modo_texto"] == "revisado" and v["revisao"]["criado_em"]
    assert v["texto_editavel"] == "Sapata do revestimento a 1234 m.\n\nCimentação com retorno."
    assert api.buscar_documentos("retorno")["resultados"][0]["pagina"] == 1
    assert api.buscar_documentos("revestimcnto", tolerante=False)["resultados"]   # o que o OCR leu também acha
    assert api.documentos()["documentos"][0]["revisadas"] == 1
    assert not api.salvar_texto_pagina(rel, 1, "   ")["ok"]
    assert not api.salvar_texto_pagina(rel, 9, "x")["ok"]
    assert api.descartar_texto_pagina(rel, 1)["removida"]
    assert api.ver_pagina(rel, 1)["revisao"] is None
    assert not api.buscar_documentos("retorno")["resultados"]
    # a revisão sobrevive a refazer o índice inteiro (ex.: mudança no vocabulário)
    api.salvar_texto_pagina(rel, 2, "Página revisada com perfilagem")
    assert api.corrigir_palavra("outra", "Outra")["ok"]
    assert api.buscar_documentos("perfilagem")["resultados"][0]["pagina"] == 2


def test_busca_dentro_de_documentos_escolhidos_e_campo_na_lista(api, tmp_path):
    api.escolher_pasta()
    a = _documento(api, tmp_path, "7-GMR-13-RN", "a.pdf", ["perda de circulacao no poco durante a perfuracao"])
    b = _documento(api, tmp_path, "3-PIA-12-AL", "b.pdf", ["perda de circulacao severa na fase de 12 1/4"], bacia="Alagoas")
    with api._banco.conexao() as c:
        c.execute("INSERT INTO pocos (id, campo, bacia) VALUES ('7-GMR-13-RN', 'GUAMARÉ', 'Potiguar')")
    assert api.buscar_documentos("circulacao")["documentos"] == 2
    so_b = api.buscar_documentos("circulacao", True, [b])
    assert so_b["escopo"] == 1 and {x["doc"] for x in so_b["resultados"]} == {b}
    assert api.buscar_documentos("circulacao", True, [])["resultados"] == []
    docs = {d["rel"]: d for d in api.documentos()["documentos"]}
    assert docs[a]["campo"] == "GUAMARÉ" and docs[b]["campo"] == "" and docs[b]["bacia"] == "Alagoas"
