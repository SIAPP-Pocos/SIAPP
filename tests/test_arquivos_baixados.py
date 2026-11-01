"""Arquivos baixados (0.54): lista do disco cruzada com o banco, abrir, mostrar na pasta, apagar para a Lixeira."""
import json
import os
import subprocess
import sys

import pytest

import petrofisica_util as pu
from motor import arquivos_baixados as mab
from ponte import arquivos as ponte_arquivos

POCO = "1-SIAPP-1-RN"
BASE = f"bruto/Potiguar/{POCO}"


def montar(api):
    """Projeto com arquivos de vários formatos; a planilha de petrofísica é lida ao abrir o projeto."""
    api.escolher_pasta()
    raiz = api._projeto.pasta
    pasta_pb = os.path.join(raiz, *BASE.split("/"), "Dados de Rochas e Fluidos", "PETROFISICABASICA")
    os.makedirs(pasta_pb)
    pu.plugs(os.path.join(pasta_pb, "1SIAPP 0001  RN-Petrofisica Basica.xlsx"))
    pu.coregama(os.path.join(pasta_pb, f"{POCO}_COREGAMA.xlsx"))
    outras = os.path.join(raiz, *BASE.split("/"), "Pasta de Poco")
    os.makedirs(outras)
    for nome, dados in (("relatorio.pdf", b"%PDF-1.4 vazio"), ("notas.txt", b"anotacoes"), ("dados.zip", b"PK\x05\x06" + b"\0" * 18),
                        ("instalar.exe", b"MZ"), ("baixando.pdf.part", b"%PDF"), ("imagem.tif", b"II*\x00\x08\x00\x00\x00")):
        with open(os.path.join(outras, nome), "wb") as f:
            f.write(dados)
    with open(os.path.join(raiz, "bruto", "registro_downloads.json"), "w") as f:
        json.dump({}, f)
    api._abrir_projeto(raiz)
    return raiz


def por_nome(r):
    return {a["nome"]: a for a in r["arquivos"]}


def test_extensoes_e_formatos():
    assert mab.pode_abrir("a.pdf") and mab.pode_abrir("a.xls") and mab.pode_abrir("a.sgy")
    for ruim in ("a.exe", "A.BAT", "x.vbs", "x.ps1", "x.lnk", "x.js", "x.msi", "x.dll", "x.iso"):
        assert not mab.pode_abrir(ruim)
    assert mab.rotulo_formato(".dlis", "dlis") == "DLIS" and mab.rotulo_formato(".tif", "lis") == "LIS (em .tif)"
    assert mab.rotulo_formato(".sgy") == "SEG-Y" and mab.rotulo_formato(".xyz") == "arquivo .xyz"
    assert mab.categoria(".xls", None, None) == "planilha" and mab.categoria(".sgy", "outro", None) == "sismica"
    assert mab.categoria(".tif", "perfil", "lis") == "perfil" and mab.categoria(".tif", "documento", None) == "documento"
    assert mab.categoria(".zip", None, None) == "compactado" and mab.categoria(".bin", None, None) == "outro"


def test_lista_o_disco_com_formato_situacao_e_onde_aparece(api):
    montar(api)
    r = api.arquivos_baixados()
    assert r["ok"] and r["bacias"] == ["Potiguar"] and "registro_downloads.json" not in por_nome(r)
    a = por_nome(r)
    plugs = a["1SIAPP 0001  RN-Petrofisica Basica.xlsx"]
    assert (plugs["bacia"], plugs["poco"], plugs["pasta"]) == ("Potiguar", POCO, "Dados de Rochas e Fluidos/PETROFISICABASICA")
    assert plugs["categoria"] == "planilha" and plugs["formato"] == "Excel (.xlsx)"
    assert plugs["estado"] == "lido" and "Plug de testemunho" in plugs["situacao"] and "Petrofísica de testemunho" in plugs["onde"]
    assert plugs["poco_id"] == POCO and plugs["pode_abrir"] is True
    assert a[f"{POCO}_COREGAMA.xlsx"]["estado"] == "lido" and "Gama do testemunho" in a[f"{POCO}_COREGAMA.xlsx"]["situacao"]
    assert a["notas.txt"]["estado"] == "sem_leitor" and a["notas.txt"]["categoria"] == "texto"
    assert a["dados.zip"]["categoria"] == "compactado"
    assert a["relatorio.pdf"]["categoria"] == "documento" and a["relatorio.pdf"]["estado"] == "pendente"
    assert "Processar" in a["relatorio.pdf"]["situacao"]
    assert a["imagem.tif"]["categoria"] == "documento"                                   # lido pelo 1 KB inicial
    assert a["baixando.pdf.part"]["estado"] == "incompleto"
    assert a["instalar.exe"]["pode_abrir"] is False
    assert r["n"] == len(r["arquivos"]) and r["bytes"] == sum(x["bytes"] for x in r["arquivos"])
    assert all(x["rel"].startswith("bruto/") and "\\" not in x["rel"] for x in r["arquivos"])


def test_agp_e_direcionais_lidos_pelo_levantamento_nao_aparecem_como_sem_leitor(api):
    raiz = montar(api)
    pasta = os.path.join(raiz, *BASE.split("/"), "AGP")
    os.makedirs(pasta)
    with open(os.path.join(pasta, "x_agp.txt"), "w") as f:
        f.write("agp")
    remoto = "/POCO/Categoria-1/1-SIAPP-1-RN/AGP/x_agp.txt"
    with api._banco.conexao() as c:
        c.execute("INSERT OR REPLACE INTO arquivos(rel, bacia, poco_id, caminho_remoto, bytes, tipo, baixado_em) VALUES (?,?,?,?,?,?,?)",
                  (f"{BASE}/AGP/x_agp.txt", "Potiguar", POCO, remoto, 3, "outro", "2026-10-31T10:00:00"))
        c.execute("INSERT INTO agp(bacia, caminho, poco_id, dados) VALUES (?,?,?,?)", ("Potiguar", remoto, POCO, "{}"))
    a = por_nome(api.arquivos_baixados())["x_agp.txt"]
    assert a["estado"] == "lido" and "AGP" in a["situacao"] and "Seção" in a["onde"] and a["data"].startswith("2026-10-31")


def test_abrir_recusa_programas_e_caminhos_de_fora_e_usa_o_programa_padrao(api, monkeypatch):
    raiz = montar(api)
    abertos = []
    monkeypatch.setattr(ponte_arquivos, "_abrir_no_sistema", lambda c: abertos.append(c))
    ok = api.abrir_arquivo_baixado(f"{BASE}/Pasta de Poco/notas.txt")
    assert ok["ok"] and abertos == [os.path.join(raiz, *BASE.split("/"), "Pasta de Poco", "notas.txt")]
    assert "não abre programas" in api.abrir_arquivo_baixado(f"{BASE}/Pasta de Poco/instalar.exe")["erro"]
    assert "fora" in api.abrir_arquivo_baixado("../projeto.sqlite")["erro"] or "não está" in api.abrir_arquivo_baixado("../projeto.sqlite")["erro"]
    assert "não está" in api.abrir_arquivo_baixado("bruto/../../x.txt")["erro"]
    assert "não está mais no disco" in api.abrir_arquivo_baixado(f"{BASE}/Pasta de Poco/sumiu.txt")["erro"]
    assert len(abertos) == 1


def test_mostrar_na_pasta_seleciona_o_arquivo_no_explorer(api, monkeypatch):
    montar(api)
    chamadas = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, *a, **k: chamadas.append(cmd))
    monkeypatch.setattr(ponte_arquivos, "_abrir_no_sistema", lambda c: chamadas.append(("pasta", c)))
    monkeypatch.setattr(sys, "platform", "win32")
    r = api.mostrar_arquivo_na_pasta(f"{BASE}/Pasta de Poco/notas.txt")
    assert r["ok"] and chamadas[0].startswith('explorer /select,"') and chamadas[0].endswith('notas.txt"')
    monkeypatch.setattr(sys, "platform", "linux")
    api.mostrar_arquivo_na_pasta(f"{BASE}/Pasta de Poco/notas.txt")
    assert chamadas[1][0] == "pasta" and chamadas[1][1].endswith("Pasta de Poco")
    assert not api.mostrar_arquivo_na_pasta("../x")["ok"]


def _trabalho_do_usuario(api, rel):
    with api._banco.conexao() as c:
        c.execute("INSERT INTO fatos(id, poco_id, tipo, fonte_rel, criado_em, origem) VALUES (?,?,?,?,?,?)",
                  ("f1", POCO, "topo_formacao", rel, "2026-10-31T10:00:00", "local"))
        c.execute("INSERT INTO paginas_revisadas(rel, pagina, texto, autor, criado_em) VALUES (?,?,?,?,?)",
                  (rel, 1, "texto corrigido", "eu", "2026-10-31T10:00:00"))


def test_impacto_separa_o_que_sai_do_que_fica(api):
    montar(api)
    rel = f"{BASE}/Dados de Rochas e Fluidos/PETROFISICABASICA/1SIAPP 0001  RN-Petrofisica Basica.xlsx"
    _trabalho_do_usuario(api, rel)
    r = api.impacto_apagar_arquivo(rel)
    assert r["ok"] and r["nome"].endswith(".xlsx") and r["bytes"] > 0
    assert r["sai"]["dados_do_poco"] == 3 and r["sai"]["leitura"] == 1 and r["sai"]["perfil_inventariado"] == 0
    assert r["fica"] == {"transcricoes": 1, "paginas_corrigidas": 1}


def test_apagar_manda_para_a_lixeira_limpa_o_derivado_e_preserva_o_trabalho(api, monkeypatch):
    raiz = montar(api)
    rel = f"{BASE}/Dados de Rochas e Fluidos/PETROFISICABASICA/1SIAPP 0001  RN-Petrofisica Basica.xlsx"
    _trabalho_do_usuario(api, rel)
    api._projeto.registrar_download("Potiguar", POCO, "/POCO/x/y.xlsx", os.path.join(raiz, *rel.split("/")), 10)
    enviados = []

    def lixeira_falsa(caminho):
        enviados.append(caminho)
        os.remove(caminho)
        return "lixeira"
    monkeypatch.setattr(mab, "enviar_para_lixeira", lixeira_falsa)
    r = api.apagar_arquivo_baixado(rel)
    assert r["ok"] and r["destino"] == "lixeira" and len(enviados) == 1 and not os.path.exists(enviados[0])
    assert r["sai"]["dados_do_poco"] == 3
    with api._banco.conexao() as c:
        assert c.execute("SELECT COUNT(*) FROM dados_poco WHERE rel = ?", (rel,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM leituras WHERE rel = ?", (rel,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM arquivos WHERE rel = ?", (rel,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM fatos WHERE fonte_rel = ?", (rel,)).fetchone()[0] == 1          # trabalho do usuário
        assert c.execute("SELECT COUNT(*) FROM paginas_revisadas WHERE rel = ?", (rel,)).fetchone()[0] == 1
    assert not any(v.get("arquivo_local") == rel for v in api._projeto.registro_downloads().values())
    assert "1SIAPP 0001  RN-Petrofisica Basica.xlsx" not in por_nome(api.arquivos_baixados())
    # o outro arquivo de petrofísica continua lido
    assert por_nome(api.arquivos_baixados())[f"{POCO}_COREGAMA.xlsx"]["estado"] == "lido"


def test_apagar_recusa_o_registro_pastas_e_fora_do_projeto(api, monkeypatch):
    raiz = montar(api)
    monkeypatch.setattr(mab, "enviar_para_lixeira", lambda c: pytest.fail("não podia apagar nada"))
    assert "registro de procedência" in api.apagar_arquivo_baixado("bruto/registro_downloads.json")["erro"]
    assert "pasta" in api.apagar_arquivo_baixado(f"{BASE}/Pasta de Poco")["erro"]
    assert not api.apagar_arquivo_baixado("projeto.sqlite")["ok"] and os.path.exists(os.path.join(raiz, "projeto.sqlite"))
    assert not api.apagar_arquivo_baixado("../fora.txt")["ok"]


def test_apagar_arquivo_que_ja_sumiu_ainda_limpa_o_banco(api, monkeypatch):
    raiz = montar(api)
    rel = f"{BASE}/Dados de Rochas e Fluidos/PETROFISICABASICA/{POCO}_COREGAMA.xlsx"
    os.remove(os.path.join(raiz, *rel.split("/")))
    monkeypatch.setattr(mab, "enviar_para_lixeira", lambda c: pytest.fail("não há o que enviar"))
    r = api.apagar_arquivo_baixado(rel)
    assert r["ok"] and r["destino"] == "ausente"
    with api._banco.conexao() as c:
        assert c.execute("SELECT COUNT(*) FROM dados_poco WHERE rel = ?", (rel,)).fetchone()[0] == 0


@pytest.mark.skipif(sys.platform != "win32", reason="Lixeira do Windows")
def test_lixeira_de_verdade_no_windows(tmp_path):
    import uuid
    alvo = tmp_path / f"siapp_teste_lixeira_{uuid.uuid4().hex}.txt"
    alvo.write_text("pode apagar")
    assert mab.enviar_para_lixeira(str(alvo)) == "lixeira"
    assert not alvo.exists()
    with pytest.raises(OSError):
        mab.enviar_para_lixeira(str(tmp_path / "nao_existe_mesmo.txt"))
