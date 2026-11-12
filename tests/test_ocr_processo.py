"""OCR num processo separado (0.59): a fila lê em outro processo, sem travar a janela, e o cancelar é imediato."""
import threading
import time

import pymupdf

from motor import documentos as md


def _pdf(caminho, paginas, texto="Relatório final de poço: perfuração em arenito com óleo. " * 3):
    doc = pymupdf.open()
    for i in range(paginas):
        doc.new_page().insert_text((50, 72), f"Página {i + 1}. {texto}")
    doc.save(str(caminho))
    return str(caminho)


def _fila(tmp_path, em_processo=True):
    eventos, salvos, fim = [], {}, threading.Event()

    def emitir(e):
        eventos.append(e)
        if e["tipo"] == "ocioso":
            fim.set()
    return md.FilaDocumentos(str(tmp_path / "tessdata"), emitir, em_processo=em_processo), eventos, salvos, fim


def test_fila_le_em_outro_processo(tmp_path):
    fila, eventos, salvos, fim = _fila(tmp_path)
    tarefas = [{"doc": f"d{i}", "caminho": _pdf(tmp_path / f"d{i}.pdf", 3), "nome": f"d{i}.pdf",
                "salvar": (lambda r, i=i: salvos.__setitem__(f"d{i}", r))} for i in range(2)]
    assert fila.adicionar(tarefas) == 2
    assert fim.wait(60)
    assert set(salvos) == {"d0", "d1"} and salvos["d0"]["n_paginas"] == 3
    assert "perfuração" in salvos["d1"]["paginas"][2]["texto"]
    tipos = [e["tipo"] for e in eventos]
    assert tipos.count("fim") == 2 and tipos.count("pagina") == 6 and tipos[-1] == "ocioso"
    assert fila._processo is not None and not fila._processo.vivo          # encerrado quando a fila esvaziou


def test_erro_num_documento_nao_para_a_fila(tmp_path):
    fila, eventos, salvos, fim = _fila(tmp_path)
    ruim = tmp_path / "ruim.pdf"
    ruim.write_bytes(b"isto nao e um pdf")
    fila.adicionar([{"doc": "ruim", "caminho": str(ruim), "nome": "ruim.pdf", "salvar": lambda r: None},
                    {"doc": "bom", "caminho": _pdf(tmp_path / "bom.pdf", 1), "nome": "bom.pdf",
                     "salvar": lambda r: salvos.__setitem__("bom", r)}])
    assert fim.wait(60)
    assert [e["doc"] for e in eventos if e["tipo"] == "erro"] == ["ruim"] and "bom" in salvos
    assert eventos[-1] == {"tipo": "ocioso", "processados": 1, "erros": 1, "cancelados": 0}


def test_cancelar_encerra_o_processo_na_hora(tmp_path):
    fila, eventos, salvos, fim = _fila(tmp_path)
    grande = _pdf(tmp_path / "grande.pdf", 3000)
    fila.adicionar([{"doc": "g", "caminho": grande, "nome": "grande.pdf", "salvar": lambda r: salvos.__setitem__("g", r)}])
    t0 = time.time()
    while not any(e["tipo"] == "pagina" for e in eventos):
        assert time.time() - t0 < 60
        time.sleep(0.05)
    fila.cancelar()
    assert fim.wait(10)
    assert "g" not in salvos and any(e["tipo"] == "cancelado" for e in eventos)
    assert not fila._processo.vivo


def test_modo_antigo_na_linha_de_execucao(tmp_path):
    fila, eventos, salvos, fim = _fila(tmp_path, em_processo=False)
    fila.adicionar([{"doc": "a", "caminho": _pdf(tmp_path / "a.pdf", 2), "nome": "a.pdf",
                     "salvar": lambda r: salvos.__setitem__("a", r)}])
    assert fim.wait(30) and salvos["a"]["n_paginas"] == 2 and fila._processo is None


def test_leitura_nao_espera_a_escrita(tmp_path):
    """0.59: a tela lê enquanto um trabalho longo grava (banco em WAL)."""
    import sqlite3
    import pytest
    from motor.banco import Banco
    b = Banco(str(tmp_path / "p.sqlite"))
    b.definir_meta("x", "1")
    pronto, solta, lido = threading.Event(), threading.Event(), []

    def escrever():
        with b.conexao() as c:
            c.execute("INSERT OR REPLACE INTO meta VALUES ('y', '2')")
            pronto.set()
            solta.wait(10)
    t = threading.Thread(target=escrever)
    t.start()
    assert pronto.wait(5)
    t0 = time.time()
    with b.leitura() as c:
        lido.append(c.execute("SELECT valor FROM meta WHERE chave = 'x'").fetchone()[0])
    assert lido == ["1"] and time.time() - t0 < 1          # não esperou a escrita terminar
    solta.set()
    t.join()
    with pytest.raises(sqlite3.OperationalError):
        with b.leitura() as c:
            c.execute("INSERT INTO meta VALUES ('z', '3')")


def test_sumario_do_pdf(tmp_path):
    doc = pymupdf.open()
    for i in range(4):
        doc.new_page().insert_text((50, 72), f"Capítulo {i + 1}")
    doc.set_toc([[1, "Introdução", 1], [1, "Geologia", 2], [2, "Formação  Açu", 3], [1, "Conclusão", 4]])
    doc.save(str(tmp_path / "com.pdf"))
    s = md.sumario(str(tmp_path / "com.pdf"))
    assert [x["titulo"] for x in s] == ["Introdução", "Geologia", "Formação Açu", "Conclusão"]
    assert s[2] == {"nivel": 2, "titulo": "Formação Açu", "pagina": 3}
    assert md.sumario(_pdf(tmp_path / "sem.pdf", 2)) == []
    assert md.sumario(str(tmp_path / "nao-existe.pdf")) == []
