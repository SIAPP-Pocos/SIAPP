"""Regras da janela: pasta de projeto fixa e travas de segurança."""
import os
import sys



def test_pasta_fixa_recusa_outras(api, tmp_path):
    api._janela.escolha = (str(tmp_path),)
    assert not api.escolher_pasta()["ok"]
    api._janela.escolha = (str(tmp_path / "ambiente_teste" / "catalogo"),)
    assert not api.escolher_pasta()["ok"]
    api._janela.escolha = None
    assert api.escolher_pasta()["ok"]


def test_cancelar_dialogo_nao_e_erro(api):
    api._janela.escolha = ()
    assert api.escolher_pasta() == {"ok": True, "cancelado": True}


def test_acoes_exigem_projeto_e_conexao(api):
    assert "pasta do projeto" in api.conectar("Sergipe")["erro"]
    api.escolher_pasta()
    assert "Conecte-se" in api.listar_pocos("Categoria-7")["erro"]


def test_correcao_global_de_numero_e_bloqueada(api):
    api.escolher_pasta()
    r = api.corrigir_palavra("87", "83")
    assert not r["ok"] and "Números" in r["erro"]
    assert api.corrigir_palavra("BARIGIRAS", "BARREIRAS")["ok"]
    assert api.dicionario()["correcoes"] == {"BARIGIRAS": "BARREIRAS"}


def test_caminho_fora_da_bacia_e_recusado(api):
    api.escolher_pasta()
    api._cliente, api._cliente_dl, api._base_remota, api._bacia = object(), object(), "/POCO/", "X"
    assert not api.explorar_poco("x", "/OUTRA/x/")["ok"]
    assert not api.baixar("x", [{"caminho": "/OUTRA/a", "nome": "a"}])["ok"]


def test_documento_nao_processado_abre_so_a_imagem(api, monkeypatch):
    from PIL import Image
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", "1-AURI-12-RN", "Perfil Convencional")
    os.makedirs(pasta)
    folhas = [Image.new("RGB", (600, 6000), "white"), Image.new("RGB", (600, 800), "gray")]
    folhas[0].save(os.path.join(pasta, "perfil.tif"), save_all=True, append_images=folhas[1:])
    open(os.path.join(pasta, "notas.txt"), "w").write("x")
    rel = "bruto/Potiguar/1-AURI-12-RN/Perfil Convencional/perfil.tif"
    assert [d["situacao"] for d in api.documentos()["documentos"]] == ["pendente"]
    r = api.ver_pagina(rel, 2)
    assert r["ok"] and not r["processado"] and r["n_paginas"] == 2 and r["pagina"] == 2
    assert r["segmentos"] == [] and r["imagem"].startswith("data:image/png")
    assert api.ver_pagina(rel, 99)["pagina"] == 2          # página além do fim vai para a última
    v = api.visor_pagina(rel, 1)
    assert v["ok"] and v["faixas"] == 10 and v["n_paginas"] == 2
    assert api.visor_faixa(rel, 1, 9)["imagem"].startswith("data:image/jpeg")
    # Windows: o caminho pode vir com barra invertida
    assert api.ver_pagina(rel.replace("/", "\\"), 1)["ok"]
    # abrir no programa do computador: só dentro de bruto/, e só o que existe
    abertos = []
    monkeypatch.setattr("subprocess.Popen", lambda args: abertos.append(args))
    monkeypatch.setattr(sys, "platform", "linux")
    assert api.abrir_arquivo(rel.replace("perfil.tif", "notas.txt"))["ok"]
    assert abertos and abertos[0][1].endswith("notas.txt")
    assert not api.abrir_arquivo("bruto/../siapp.json")["ok"]
    assert not api.abrir_arquivo(rel.replace("perfil.tif", "nao-existe.pdf"))["ok"]


def test_arvore_do_poco_traz_caminho_local_dos_baixados(api):
    api.escolher_pasta()
    baixado = {"nome": "a.pdf", "pasta": False, "tamanho": 3, "caminho": "/POCO/X/P/a.pdf", "pasta_relativa": "P"}
    falta = {"nome": "b.pdf", "pasta": False, "tamanho": 3, "caminho": "/POCO/X/P/b.pdf", "pasta_relativa": "P"}

    class Cliente:
        def mapear_poco(self, caminho, nome, progresso=None):
            return {"arvore": {"nome": nome, "pasta": True, "filhos": [baixado, falta]},
                    "arquivos": [baixado, falta], "resumo": {"n_arquivos": 2, "tamanho_total": 6}}

    api._cliente, api._base_remota, api._bacia = Cliente(), "/POCO/", "Potiguar"
    destino = api._projeto.destino_bruto("Potiguar", "X", "P", "a.pdf")
    os.makedirs(os.path.dirname(destino))
    open(destino, "wb").write(b"abc")
    r = api.explorar_poco("X", "/POCO/X/")
    assert r["ok"]
    a, b = r["arvore"]["filhos"]
    assert a["baixado"] and a["rel"] == "bruto/Potiguar/X/P/a.pdf"
    assert not b["baixado"] and "rel" not in b


def test_pagina_diz_quais_palavras_da_imagem_foram_corrigidas(api, tmp_path):
    import pymupdf
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", "7-GMR-13-RN", "Pasta")
    os.makedirs(pasta)
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "SONDA iReline FORMACAO BARIGIRAS RELATORIO DO POCO", fontsize=10)
    doc.save(os.path.join(pasta, "p.pdf"))
    rel = "bruto/Potiguar/7-GMR-13-RN/Pasta/p.pdf"
    from motor import documentos as md
    r = md.processar_arquivo(os.path.join(pasta, "p.pdf"), tessdata=str(tmp_path))
    api._projeto.salvar_texto(rel, r)
    assert api.corrigir_palavra("iReline", "Wireline")["ok"]
    v = api.ver_pagina(rel, 1)
    tipos = [s["tipo"] for s in v["segmentos"] if isinstance(s, dict)]
    assert tipos == ["usuario", "auto"] and v["n_corrigidas_imagem"] == 2
