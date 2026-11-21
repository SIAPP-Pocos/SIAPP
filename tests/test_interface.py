"""Interface de verdade num navegador sem tela (pulado sem Playwright)."""
import json
import os
import re

import pytest

pytestmark = pytest.mark.interface


def abrir_projeto(janela):
    janela.page.click("#ini-pasta")
    janela.esperar("document.getElementById('ini-pasta').disabled")


def ir(p, aba, sub=None):
    """Vai até uma aba (e uma sub-aba do Acervo). Correlação e Modelo 3D são abas próprias no topo
    (ir(p, "interp", "bloco") clica em "6 Modelo 3D"); a Viabilidade fica no menu "Mais" e, desde a 1.3, a Comunidade
    é aba própria no topo."""
    if aba == "interp":
        p.click("#aba-modelo" if sub == "bloco" else "#aba-interp")
        if sub == "bloco":       # 0.59: os passos vêm recolhidos (receita); os testes mexem em tudo
            p.evaluate("document.querySelectorAll('#vista-bloco details.passo').forEach(d => d.open = true)")
        return
    if aba == "viab":
        p.click("#aba-mais")
    p.click(f"#aba-{aba}")
    if sub and aba == "dados":
        item = p.locator(f".sub-nav [data-sub='{sub}']")
        if not item.is_visible():
            p.click(".sub-mais > .sub-btn")        # Cadastro, Produção, Camadas, Consolidados: em "Mais"
        item.click()


def aba_bloco(p, nome):
    """Aba sobre o visor do Modelo 3D: ver, validar, mapa2d ou exportar (0.59)."""
    p.click(f"#bl-aba-{nome}")


def menu_janela(p):
    """Abre o menu "⋯" do topo (Dividir a janela, Abrir em janela)."""
    p.click("#btn-janelas")


def abrir_avancado(p, ident):
    """Abre uma seção recolhida (<details class="avancado">) da barra lateral."""
    p.eval_on_selector(f"#{ident}", "d => d.open = true")


def test_abre_no_inicio_e_abre_projeto(janela):
    p = janela.page
    assert re.match(r"v\d+\.\d+\.\d+", p.text_content("#versao"))
    assert p.is_visible("#vista-projeto") and not p.is_visible("#vista-dados")
    abrir_projeto(janela)
    janela.esperar("document.querySelectorAll('#ini-modulos .mod').length === 6")     # 0.58: módulos com estado
    assert "Nenhum documento baixado" in p.text_content("#ini-modulos [data-modulo=docs]")
    assert p.text_content("#ini-nome") == "Projeto principal"
    p.click("#aba-dados")
    assert not p.is_visible("#etapa-bacia.bloqueada")
    assert not janela.erros_js, janela.erros_js


def test_abas_trocam_de_vista(janela):
    p = janela.page
    p.click("#aba-docs")
    assert p.is_visible("#vista-docs") and not p.is_visible("#vista-projeto")
    assert "Abra primeiro o projeto" in p.text_content("#docs-resumo")
    ir(p, "comunidade")
    assert p.is_visible("#vista-comunidade")
    assert not janela.erros_js, janela.erros_js


def test_comunidade_autor_exportar_importar(janela):
    p = janela.page
    abrir_projeto(janela)
    api = janela.api
    api.corrigir_palavra("BARIGIRAS", "BARREIRAS")
    ir(p, "comunidade")
    janela.esperar("document.getElementById('com-local').textContent.includes('1 correção')")
    p.click("#btn-exportar")
    janela.esperar("document.querySelector('.rodape').classList.contains('erro')")
    assert "nome" in janela.status()
    p.fill("#autor-nome", "Ruan da Silva Nobre")
    p.fill("#autor-inst", "UFAL")
    p.click("#btn-autor")
    janela.esperar("document.getElementById('status').textContent.includes('Autoria salva')")
    p.click("#btn-exportar")
    janela.esperar("document.getElementById('com-exportado').textContent.includes('contribuicoes/')")
    rel = p.text_content("#com-exportado").split("em ")[1].split(" (")[0]
    # importar o próprio pacote como se fosse de outra pessoa
    api.remover_correcao("BARIGIRAS")
    api._janela.escolha = None
    original = api._janela.create_file_dialog
    api._janela.create_file_dialog = lambda tipo, **kw: (os.path.join(api._projeto.pasta, rel),)
    p.click("#btn-importar")
    janela.esperar("!document.getElementById('previa').hidden")
    assert "1 correção" in p.text_content("#previa")
    p.click("#previa .btn:not(.secundario)")
    janela.esperar("document.querySelectorAll('#lista-pacotes li button').length === 1")
    api._janela.create_file_dialog = original
    p.click("#aba-docs")
    janela.esperar("document.getElementById('n-com').textContent === '1'")
    assert not janela.erros_js, janela.erros_js


def test_mapa_com_cadastro_e_ficha(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    p.click("#aba-mapa")
    janela.esperar("!document.getElementById('mapa-vazio').hidden")
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-projeto")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('2 poço')")
    assert p.is_hidden("#mapa-vazio")
    p.select_option("#f-bacia", "")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('3 poço')")
    p.fill("#f-texto", "AURI")
    janela.esperar("document.querySelectorAll('#lista-mapa button').length === 1")
    p.click("#lista-mapa button")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('72100021414')")
    assert "Pioneiro" in p.text_content("#fi-corpo")
    p.keyboard.press("Escape")
    assert p.is_hidden("#ficha")
    assert not janela.erros_js, janela.erros_js


def test_perfis_inventario_grafico_intervalo_exportar(janela, tmp_path):
    from test_perfis import las_exemplo
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Perfis"
    pasta.mkdir(parents=True)
    las_exemplo(pasta / "7gmr13.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas:not(#pf-nav)').length === 3", 30)
    assert "7-GMR-13-RN" in p.text_content("#pf-titulo")
    # arrastar na trilha marca um intervalo
    cv = p.locator("#pf-trilhas canvas:not(#pf-nav)").nth(1)
    caixa = cv.bounding_box()
    p.mouse.move(caixa["x"] + 30, caixa["y"] + 100)
    p.mouse.down()
    p.mouse.move(caixa["x"] + 30, caixa["y"] + 200)
    p.mouse.up()
    assert p.input_value("#pf-int-topo") and p.input_value("#pf-int-base")
    p.fill("#pf-int-nome", "Reservatório A")
    p.click("#pf-form-int button")
    janela.esperar("document.getElementById('pf-fatos').textContent.includes('Reservatório A')")
    p.click("#pf-las")
    janela.esperar("document.getElementById('pf-exportado').textContent.includes('exportacoes/')")
    assert not janela.erros_js, janela.erros_js


def test_transcricao_com_caixa_e_sugestao(janela, tmp_path):
    import pymupdf
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    doc = pymupdf.open()
    pg = doc.new_page()
    pg.insert_text((72, 100), "RELATORIO DE REVESTIMENTO - POCO 7-GMR-13-RN", fontsize=12)
    pg.insert_text((300, 200), "SAPATA: 1234,5 m", fontsize=14)
    doc.save(str(pasta / "rev.pdf"))
    api = janela.api
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    rel = "bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/rev.pdf"
    from motor import documentos as md
    r = md.processar_arquivo(str(pasta / "rev.pdf"), tessdata=str(tmp_path))
    api._projeto.salvar_texto(rel, r)
    api._indice.substituir_documento(rel, "Potiguar", "7-GMR-13-RN", "rev.pdf", r["paginas"], api._corretor)
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 1")
    p.click("#lista-docs button")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 1')")
    p.click("#tr-box summary")
    assert p.input_value("#tr-poco") == "7-GMR-13-RN"
    p.select_option("#tr-tipo", "revestimento")
    p.locator("#painel-pagina").evaluate("e => e.scrollTop = 0")
    img = p.locator("#pg-img").bounding_box()
    largura, altura = 595, 842                      # página A4 em pontos
    x0, y0 = img["x"] + img["width"] * 290 / largura, img["y"] + img["height"] * 180 / altura
    x1, y1 = img["x"] + img["width"] * 470 / largura, img["y"] + img["height"] * 210 / altura
    p.mouse.move(x0, y0)
    p.mouse.down()
    p.mouse.move(x1, y1)
    p.mouse.up()
    assert p.input_value("#tr-topo") == "1234,5"
    assert "SAPATA" in p.text_content("#tr-caixa-info")
    p.fill("#tr-nome", "Sapata 9 5/8 pol")
    p.click("#tr-form button[type=submit]")
    janela.esperar("document.getElementById('tr-n').textContent === '1'")
    f = api._banco.fatos("7-GMR-13-RN")[0]
    assert f["prof_topo"] == 1234.5 and f["pagina"] == 1 and len(f["caixa"]) == 4 and f["fonte_sha256"]
    assert p.locator("#pg-caixas .pg-caixa.salva").count() == 1
    assert not janela.erros_js, janela.erros_js


def test_tif_sem_processar_abre_amplia_e_arquivo_qualquer_abre_fora(janela, tmp_path, monkeypatch):
    from PIL import Image
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-AURI-12-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    folhas = [Image.new("RGB", (500, 7000), "white"), Image.new("RGB", (500, 700), "gray")]
    folhas[0].save(str(pasta / "perfil.tif"), save_all=True, append_images=folhas[1:])
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 1")
    assert "sem texto" in p.text_content("#lista-docs")
    p.click("#lista-docs button")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 2')")
    assert p.is_visible("#pg-pendente") and not p.is_visible("#pg-texto-box")
    p.click("#pg-prox")
    janela.esperar("document.getElementById('pg-num').textContent.includes('2 de 2')")
    p.click("#pg-ant")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 2')")
    # visor ampliado: faixas sob demanda, zoom e Esc
    p.click("#pg-ampliar")
    janela.esperar("document.querySelectorAll('#v-folha .v-faixa').length === 14")
    janela.esperar("document.querySelectorAll('#v-folha .v-faixa img').length >= 1")
    carregadas = p.locator("#v-folha .v-faixa img").count()
    assert carregadas < 14                         # só o que está perto da tela
    # 1.2: as setas trocam a página também em tela cheia
    p.keyboard.press("ArrowRight")
    janela.esperar("document.getElementById('v-num').textContent === '2 / 2'")
    p.keyboard.press("ArrowLeft")
    janela.esperar("document.getElementById('v-num').textContent === '1 / 2'")
    janela.esperar("document.querySelectorAll('#v-folha .v-faixa').length === 14")
    antes = p.text_content("#v-zoom")
    p.click("#v-mais")
    assert p.text_content("#v-zoom") != antes
    p.locator("#v-area").evaluate("e => e.scrollTop = e.scrollHeight")
    janela.esperar("document.querySelector('#v-folha .v-faixa:last-child img') !== null")
    p.keyboard.press("Escape")
    assert not p.is_visible("#visor") and p.is_visible("#painel-pagina")
    # outro tipo de arquivo: programa do computador
    (pasta / "notas.txt").write_text("x")
    abertos = []
    monkeypatch.setattr("ponte.documentos.subprocess.Popen", lambda args: abertos.append(args))
    monkeypatch.setattr("ponte.documentos.sys.platform", "linux")
    p.evaluate("abrirBaixado('bruto/Potiguar/1-AURI-12-RN/Perfil Convencional/notas.txt')")
    janela.descarregar()
    janela.esperar("document.getElementById('status').textContent.includes('programa do computador')")
    assert abertos and abertos[0][1].endswith("notas.txt")
    assert not janela.erros_js, janela.erros_js


def test_levantamento_do_acervo_no_mapa(janela, monkeypatch):
    from test_levantamento import TIF_LIS, PDF, ClienteFalso
    from test_pocos import csv_exemplo
    from motor import reate
    falso = ClienteFalso({
        "/POCO/Categoria-1/1-AURI-12-RN/Perfil Convencional/1AURI.tif": TIF_LIS,
        "/POCO/Categoria-7/Categoria-7_parte1/7-GMR-13-RN/Pasta de Poco/pasta.pdf": PDF,
    })
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia", classmethod(lambda cls, bacia, **kw: falso))
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('2 poço')")
    ir(p, "dados", "levantamento")
    p.select_option("#lv-bacia", "Potiguar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('Ainda não levantada')")
    p.click("#lv-carregar")
    janela.esperar("document.querySelectorAll('.lv-cat').length === 2")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('2 pasta(s) de poço')", 30)
    assert "Levantamento concluído" in janela.status()
    texto = p.text_content("#lv-resumo")
    assert ".tif → LIS" in texto and "perfil digital" in texto
    p.click("#aba-mapa")
    assert p.is_visible("#legenda-acervo") and p.input_value("#f-cor") == "acervo"
    p.select_option("#f-acervo", "digital")
    janela.esperar("document.querySelectorAll('#lista-mapa button').length === 1")
    p.click("#lista-mapa button")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('No acervo do REATE')")
    assert "LIS em fita" in p.text_content("#fi-corpo")
    ir(p, "dados", "levantamento")
    p.click("#lv-exportar")
    janela.esperar("document.getElementById('status').textContent.includes('_pocos.csv')")
    assert not janela.erros_js, janela.erros_js


def test_avaliacao_de_formacao_no_intervalo(janela, tmp_path):
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-TST-1-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "tst.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas:not(#pf-nav)').length >= 3", 30)
    janela.esperar("document.querySelectorAll('.av-curva').length === 8")
    assert "Nenhum intervalo-alvo" in p.text_content("#av-intervalos")
    # sem intervalo, o cálculo é recusado com explicação
    p.click("#av-calcular")
    janela.esperar("document.getElementById('status').textContent.includes('intervalo-alvo')")
    # marca o intervalo pelo formulário (o arraste já é testado em outro teste)
    p.fill("#pf-int-nome", "Açu")
    p.fill("#pf-int-topo", "1005")
    p.fill("#pf-int-base", "1035")
    p.click("#pf-form-int button")
    janela.esperar("document.querySelectorAll('.av-int').length === 1")
    p.fill("#av-gr_limpo", "30")
    p.fill("#av-gr_argila", "120")
    p.fill("#av-rw", "0,05")
    p.click("#av-calcular")
    janela.esperar("document.querySelector('#av-resultado table') !== null", 30)
    linha = p.text_content("#av-resultado tbody tr")
    assert "Açu" in linha and "10" in p.text_content("#av-resultado td.destaque")
    # trilhas calculadas aparecem no gráfico
    janela.esperar("document.getElementById('pf-trilhas').textContent.includes('Net pay')")
    assert "SW" in p.text_content("#pf-trilhas")
    registros = list((tmp_path / "ambiente_teste" / "execucoes").glob("avaliacao_*.json"))
    assert len(registros) == 1
    p.click("#av-csv")
    janela.esperar("document.getElementById('status').textContent.includes('Avaliação exportada')")
    assert not p.is_hidden("#av-historico")
    assert not janela.erros_js, janela.erros_js


def test_agp_na_ficha_e_na_avaliacao(janela, monkeypatch, tmp_path):
    from test_avaliacao import las_reservatorio
    from test_levantamento import SUL_DLIS, ClienteFalso
    from test_pocos import csv_exemplo
    from motor import reate
    with open(os.path.join(os.path.dirname(__file__), "dados", "agp_sintetico.txt"), "rb") as f:
        agp = f.read().replace(b"7TST 0001  RN", b"1AURI0012  RN")
    falso = ClienteFalso({
        "/POCO/Categoria-1/1-AURI-12-RN/Perfil Convencional/1AURI.dlis": SUL_DLIS,
        "/POCO/Categoria-1/1-AURI-12-RN/AGP/1AURI0012RN_agp.txt": agp,
    })
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia", classmethod(lambda cls, bacia, **kw: falso))
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('poço')")
    ir(p, "dados", "levantamento")
    p.select_option("#lv-bacia", "Potiguar")
    assert p.is_checked("#lv-agp")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('com topos de formação')", 30)
    assert "AGP(s) lidos" in janela.status()
    p.evaluate("abrirFicha('1-AURI-12-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('AGP — dados gerais')")
    corpo = p.text_content("#fi-corpo")
    assert "Formação Açu" in corpo and "Rmf 0,162 a 74,8 °F" in corpo and "salinidade 20.000 ppm" in corpo
    # perfil do mesmo poço: as unidades do AGP viram intervalos candidatos na avaliação
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-AURI-12-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "auri.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length >= 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('.av-int').length >= 3", 30)
    assert "Formação Açu · 300–700 m" in p.text_content("#av-intervalos")
    assert "Rmf 0,162" in p.text_content("#av-lama")
    # litologia das amostras de calha vira uma trilha estreita no gráfico
    janela.esperar("document.querySelectorAll('.pf-trilha-lito canvas').length == 1")
    assert "Litol. (AGP)" in p.text_content(".pf-trilha-lito")
    # legenda da litologia (0.36): só as classes que aparecem no trecho visível
    p.evaluate("pf.litoAgp = [{topo: 1000, base: 1020, rocha: 'ARENITO FINO'}, {topo: 1020, base: 1030, rocha: 'FOLHELHO'},"
               " {topo: 1030, base: 1040, rocha: 'MARGA'}, {topo: 5000, base: 5100, rocha: 'HALITA'}]; desenharTrilhas()")
    janela.esperar("!document.getElementById('pf-lito-legenda').hidden")
    leg = p.text_content("#pf-lito-legenda")
    assert "Litologia (AGP)" in leg and "Arenito" in leg and "Folhelho" in leg and "Evaporito" not in leg
    assert p.locator("#pf-lito-legenda span").count() == 2          # folhelho e marga na mesma classe
    assert not janela.erros_js, janela.erros_js


def test_aba_secao(janela):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    poco(b, "1-OES-1-RN", -5.30, -36.80, 50.0, [("F", "JANDAI", 10, 300), ("F", "ACU", 300, 700)], prof_final=750)
    poco(b, "1-MEI-1-RN", -5.30, -36.75, 40.0, [("F", "JANDAI", 8, 320), ("F", "ACU", 320, 760)], prof_final=800)
    poco(b, "1-LES-1-RN", -5.30, -36.70, 30.0, [("F", "JANDAI", 5, 330), ("F", "ACU", 330, 900)], prof_final=950)
    ir(p, "interp", "secao")
    janela.esperar("document.getElementById('sec-disponiveis').textContent.includes('3 poço')")
    # pelas pontas da linha (seção recolhida na lateral)
    abrir_avancado(p, "sec-av-linha")
    p.fill("#sec-a", "1-OES-1-RN")
    p.fill("#sec-b", "1-LES-1-RN")
    p.click("#sec-corredor")
    janela.esperar("document.querySelectorAll('#sec-lista li').length === 3")
    assert "3 poço(s)" in p.text_content("#sec-corredor-res")
    # nivelado no topo do Açu
    abrir_avancado(p, "sec-av-desenho")
    p.select_option("#sec-eixo", "nivelado")
    janela.esperar("document.querySelectorAll('#sec-datum option').length >= 2")
    p.select_option("#sec-datum", "ACU")
    p.click("#sec-montar")
    janela.esperar("document.querySelector('#sec-figura svg') !== null", 30)
    assert "DATUM: topo da Formação Açu" in p.inner_html("#sec-figura")     # estilo clássico (padrão)
    assert "SEÇÃO ESTRATIGRÁFICA A–A′" in p.inner_html("#sec-figura")
    p.select_option("#sec-estilo", "moderno")
    p.click("#sec-montar")
    janela.esperar("document.getElementById('sec-figura').innerHTML.includes('Distância ao topo — Formação Açu')", 30)
    assert p.locator("#sec-tabela tr").count() == 7
    p.click("#sec-painel [data-formato=csv]")
    janela.esperar("document.getElementById('sec-exportado').textContent.includes('.csv')")
    janela.esperar("document.querySelectorAll('#sec-historico button').length === 2")
    # tirar um poço e reabrir a anterior pelo histórico
    p.click("#sec-lista li:nth-child(2) .sec-mini >> nth=2")
    assert p.locator("#sec-lista li").count() == 2
    abrir_avancado(p, "sec-av-historico")
    p.click("#sec-historico button >> nth=1")       # a mais antiga: estilo clássico
    janela.esperar("document.querySelectorAll('#sec-lista li').length === 3")
    assert p.input_value("#sec-estilo") == "classico"
    assert not janela.erros_js, janela.erros_js


def test_secao_com_gr_do_perfil_lido(janela, tmp_path):
    """A seção pega o GR de um perfil já lido do poço e o põe em cota (mesa − prof)."""
    from test_avaliacao import las_reservatorio
    from test_secao import poco
    abrir_projeto(janela)
    api = janela.api
    poco(api._banco, "1-OES-1-RN", -5.30, -36.80, 50.0, [("F", "ACU", 900, 1015), ("F", "ALAGAM", 1015, 1040)],
         prof_final=1040)
    poco(api._banco, "1-LES-1-RN", -5.30, -36.70, 30.0, [("F", "ACU", 880, 1000), ("F", "ALAGAM", 1000, 1050)],
         prof_final=1050)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-OES-1-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "oes.las")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    rel = "bruto/Potiguar/1-OES-1-RN/Perfil Convencional/oes.las"
    assert api.inventariar_perfil(rel)["ok"]
    r = api.secao_montar(["1-OES-1-RN", "1-LES-1-RN"], {"ordem": "lista"})
    assert r["ok"], r
    oes, les = r["pocos"]
    assert oes["gr"] == "GR" and les["gr"] is None
    assert "<polyline" in r["svg"] and "GR 0–150" in r["svg"]
    e = api.secao_exportar(r["id"], "pdf")
    assert e["ok"] and os.path.isfile(tmp_path / "ambiente_teste" / e["arquivo"])
    assert not api.secao_exportar("../x", "svg")["ok"]


def test_esquemas_de_ferramentas_na_ficha_e_na_aba_perfis(janela, monkeypatch, tmp_path):
    from test_avaliacao import las_reservatorio
    from test_ferramentas import esquema_pdf
    from test_levantamento import LAS, ClienteFalso
    from test_pocos import csv_exemplo
    from motor import documentos as md
    from motor import reate
    pdf = open(esquema_pdf(tmp_path / "e.pdf", carimbo=["DATA: 10/05/2008", "POCO: 1-AURI-12-RN"]), "rb").read()
    base = "/POCO/Categoria-1/1-AURI-12-RN/"
    falso = ClienteFalso({
        base + "Perfil Convencional/1-auri-12-rn_raw.las": LAS,
        base + "Esquema de Ferramentas/1-auri-12-rn_raw_toolstring.pdf": pdf,
    })
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia", classmethod(lambda cls, bacia, **kw: falso))
    # sem internet no teste: o modelo de OCR não é baixado (o PDF sintético tem texto)
    monkeypatch.setattr("ponte.ferramentas.PASTA_TESSDATA", str(tmp_path / "tessdata"))

    def sem_rede(*a, **k):
        raise md.ErroDocumento("sem rede")
    monkeypatch.setattr("ponte.ferramentas.md.baixar_idioma", sem_rede)
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('poço')")
    ir(p, "dados", "levantamento")
    p.select_option("#lv-bacia", "Potiguar")
    assert not p.is_checked("#lv-esquemas")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('Esquemas de ferramentas')", 30)
    p.click("#aba-mapa")
    p.evaluate("abrirFicha('1-AURI-12-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Esquemas de ferramentas (1)')")
    # antes de ler: o tipo da corrida pelo nome, e o perfil já rotulado
    assert "Perfilagem convencional" in p.text_content(".esq-cartao")
    assert "Perfilagem convencional" in p.text_content(".acervo-lista")
    assert "1-auri-12-rn_raw.las" in p.text_content(".esq-perfis")
    p.click(".esq-ficha + .linha .btn-abrir")
    janela.esperar("document.querySelectorAll('.esq-chips .chip').length >= 5", 30)
    p.evaluate("lerEsquemasPoco(null, '1-AURI-12-RN')")     # já lido: nada a baixar, só o aviso
    janela.esperar("document.getElementById('status').textContent.includes('já foram lidos')")
    chips = p.text_content(".esq-chips")
    assert "HILTB" in chips and "DSLT" in chips and "HAIT" in chips and "LEH" not in chips
    cartao = p.text_content(".esq-cartao")
    assert "Schlumberger" in cartao and "10/05/2008" in cartao and "Abrir o PDF" in cartao
    assert (tmp_path / "ambiente_teste" / "esquemas" / "Potiguar" / "1-AURI-12-RN" /
            "1-auri-12-rn_raw_toolstring.pdf").is_file()
    # o perfil baixado com o mesmo nome mostra a corrida na aba Perfis
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-AURI-12-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "1-auri-12-rn_raw.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    assert "Perfilagem convencional" in p.text_content("#lista-perfis")
    p.click("#lista-perfis button")
    janela.esperar("!document.getElementById('pf-corrida').hidden", 30)
    texto = p.text_content("#pf-corrida")
    assert "Perfilagem convencional" in texto and "HILTB" in texto
    assert not janela.erros_js, janela.erros_js


def test_aba_bloco_3d(janela, tmp_path):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)],
             prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    assert p.input_value("#bl-campo") == "CAMPO TESTE"
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.fill("#bl-titulo", "Campo teste")
    p.click("#bl-montar")
    janela.esperar("!document.getElementById('bl-painel').hidden", 30)
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 30)
    est = p.evaluate("window.BlocoVisor.estado()")
    assert est["pocos"] == 5 and est["rotulos"] >= 5
    assert "contorno dos poços 19,7 km²" in p.text_content("#bl-resumo")
    assert "Formação Açu" in p.text_content("#bl-unidades")
    # controles: exagero, desligar uma unidade, vista de cima
    p.fill("#bl-exagero", "30")
    p.dispatch_event("#bl-exagero", "input")
    assert p.evaluate("window.BlocoVisor.estado().exagero") == 30
    p.click("#bl-unidades input[data-chave='ACU']")
    p.click("[data-vista3d='cima']")
    aba_bloco(p, "exportar")
    p.click("#bl-png")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('.png')", 30)
    pngs = list((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("bloco_*.png"))
    assert len(pngs) == 1 and pngs[0].read_bytes()[:4] == b"\x89PNG" and pngs[0].stat().st_size > 20000
    aba_bloco(p, "exportar")
    p.click("#bl-csv")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_superficies.csv')")
    # reabrir do histórico
    janela.esperar("document.querySelectorAll('#bl-historico button').length === 1")
    p.click("#bl-limpar")
    p.click("#bl-historico button")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    assert "reaberto" in janela.status()
    assert not janela.erros_js, janela.erros_js


def test_bloco_3d_trilhas_propriedade_e_figura(janela, tmp_path):
    import numpy as np
    from test_bloco import _avaliacao
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    ex = str(tmp_path / "ambiente_teste" / "execucoes")
    pocos = [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
             ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]
    for k, (pid, la, lo) in enumerate(pocos):
        leste = (lo + 37.00) * 111.0
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)],
             prof_final=900)
        if k < 4:
            prof = np.arange(320, 700, 0.5)
            _avaliacao(ex, pid, f"avaliacao_{pid}_1", prof, (prof > 400).astype(float), (prof > 500).astype(float),
                       [{"nome": "Açu", "topo": 320, "base": 700, "hpv_m": 2.0 + 3 * k, "net_pay_m": 20.0,
                         "ntg": 0.6, "phi_media_pay": 0.2, "sw_media_pay": 0.35}])
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 30)
    # avaliados → trilha de pay de saída
    assert p.input_value("#bl-trilha") == "avaliacao"
    janela.esperar("window.BlocoVisor.estado().trilhas >= 8")
    assert "pay" in p.text_content(".bl-leg-trilha")
    p.select_option("#bl-drape-unidade", "ACU")
    janela.esperar("window.BlocoVisor.estado().drape === 'ACU'")
    assert "HPV (m)" in p.evaluate("window.BlocoVisor.estado().escala")
    p.select_option("#bl-drape-prop", "ntg")
    janela.esperar("window.BlocoVisor.estado().escala.includes('N/G')")
    p.select_option("#bl-trilha", "indicios")
    janela.esperar("window.BlocoVisor.estado().trilhas === 0")
    aba_bloco(p, "exportar")
    p.click("[data-figura='pdf']")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_figura.pdf')", 30)
    pdfs = list((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("*_figura.pdf"))
    assert len(pdfs) == 1 and pdfs[0].read_bytes()[:4] == b"%PDF"
    aba_bloco(p, "exportar")
    p.click("[data-figura='svg']")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_figura.svg')", 30)
    svg = next((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("*_figura.svg")).read_text("utf-8")
    assert "N/G" in svg and "Formação Açu" in svg
    assert not janela.erros_js, janela.erros_js


def test_bloco_fechado_corte_camadas_e_secao(janela, tmp_path):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0
        un = [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)]
        if pid != "1-AA-4-RN":
            un.append(("F", "ALAGAM", 700, 850))
        poco(b, pid, la, lo, 50.0, un, prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.fill("#bl-base", "-1000")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 3", 30)
    assert p.locator("#bl-fechado-ctl").is_hidden()
    # mesmo modelo, outro modo: o bloco fechado
    p.click("[data-modo3d='fechado']")
    janela.esperar("window.BlocoVisor.estado().modo === 'fechado'")
    est = p.evaluate("window.BlocoVisor.estado()")
    assert est["camadas"] >= 3
    assert p.locator("#bl-fechado-ctl").is_visible() and p.locator("#bl-drape-unidade").is_hidden()
    assert "base plana em -1.000 m" in p.text_content("#bl-resumo")
    assert "km³" in p.text_content("#bl-unidades") and "sem descrição no AGP" in p.text_content("#bl-unidades")
    assert p.input_value("#bl-opacidade") == "1"                      # opaco de saída
    # corte: tampas em todas as camadas
    p.check("#bl-corte")
    janela.esperar("window.BlocoVisor.estado().tampas >= 3")
    p.select_option("#bl-corte-quad", "NE")
    p.fill("#bl-corte-x", "0.3")
    p.dispatch_event("#bl-corte-x", "input")
    janela.esperar("window.BlocoVisor.estado().tampas >= 3")
    # camadas afastadas: poços somem
    p.fill("#bl-afastar", "0.5")
    p.dispatch_event("#bl-afastar", "input")
    assert p.evaluate("window.BlocoVisor.vistaAtual().afastar") == 0.5
    # seção A–A′ pelos poços da aba Seção
    p.evaluate("sec.pocos = ['1-AA-1-RN', '1-AA-5-RN', '1-AA-4-RN']")
    p.check("#bl-parede")
    janela.esperar("window.BlocoVisor.estado().paredes >= 3")
    assert "Seção A–A′ por 3 poço(s)" in janela.status()
    p.click("#bl-unidades input[data-chave='ALAGAM']")
    assert "ALAGAM" not in p.evaluate("window.BlocoVisor.vistaAtual().camadas")
    aba_bloco(p, "exportar")
    p.click("[data-figura='svg']")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_figura.svg')", 30)
    svg = next((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("*_figura.svg")).read_text("utf-8")
    assert "Bloco fechado (AGP)" in svg and "Seção A–A′" in svg
    aba_bloco(p, "exportar")
    p.click("#bl-png")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('.png')", 30)
    # de volta às superfícies
    p.click("[data-modo3d='superficies']")
    janela.esperar("window.BlocoVisor.estado().modo === 'superficies'")
    assert p.input_value("#bl-opacidade") == "0.85"
    assert not janela.erros_js, janela.erros_js


def test_bloco_validacao_e_prognostico(janela, tmp_path):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)],
             prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 30)
    assert p.locator("#bl-val").is_hidden() and p.locator("#bl-prog").is_hidden()
    # validação cruzada
    aba_bloco(p, "validar")
    p.click("#bl-validar")
    janela.esperar("!document.getElementById('bl-val').hidden", 60)
    assert "previstos sem o próprio poço" in p.text_content("#bl-val-resumo")
    assert "Açu" in p.text_content("#bl-val-tabela") or "ACU" in p.text_content("#bl-val-tabela")
    assert p.locator("#bl-val-faixas tbody tr").count() >= 1
    # prognóstico pelo clique no bloco
    aba_bloco(p, "validar")
    p.click("#bl-prog-clique")
    assert p.evaluate("window.BlocoVisor.estado().escolhendo")
    p.click("[data-vista3d='cima']")
    caixa = p.locator("#bl-visor canvas").bounding_box()
    p.mouse.click(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
    janela.esperar("!document.getElementById('bl-prog').hidden", 30)
    assert p.evaluate("window.BlocoVisor.estado().pino") >= 2
    assert not p.evaluate("window.BlocoVisor.estado().escolhendo")
    assert "Prognóstico em" in p.text_content("#bl-prog-titulo")
    assert "±" in p.text_content("#bl-prog-tabela") and "interpolado" in p.text_content("#bl-prog-tabela")
    # por coordenadas
    aba_bloco(p, "validar")
    p.fill("#bl-prog-latlon", "-5,02; -36,98")
    p.press("#bl-prog-latlon", "Enter")
    janela.esperar("document.getElementById('bl-prog-titulo').textContent.includes('-5,02')", 30)
    p.fill("#bl-prog-latlon", "abc")
    p.click("#bl-prog-ir")
    janela.esperar("document.getElementById('status').textContent.includes('graus decimais')")
    # exportações
    for f in ("csv", "svg"):
        p.click(f"[data-validacao='{f}']")
        janela.esperar(f"document.getElementById('bl-exportado').textContent.includes('_validacao.{f}')", 30)
    p.click("#bl-prog-csv")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_prognostico_')", 30)
    pasta = tmp_path / "ambiente_teste" / "exportacoes" / "blocos"
    assert next(pasta.glob("*_validacao.csv")).read_text("utf-8-sig").startswith("poco;unidade")
    assert "Formação" in next(pasta.glob("*_prognostico_*.csv")).read_text("utf-8-sig") or \
        "JANDAI" in next(pasta.glob("*_prognostico_*.csv")).read_text("utf-8-sig")
    p.click("#bl-prog-limpar")
    assert p.evaluate("window.BlocoVisor.estado().pino") == 0
    # reabrir do histórico: a validação vem junto
    p.click("#bl-historico button")
    janela.esperar("!document.getElementById('bl-val').hidden", 30)
    assert not janela.erros_js, janela.erros_js


def test_bloco_saidas(janela, tmp_path):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)],
             prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 30)
    aba_bloco(p, "exportar")          # abre "Saídas do bloco" sozinho
    janela.esperar("document.querySelectorAll('#bl-vol-tabela tbody tr').length >= 2", 30)
    janela.esperar("document.getElementById('bl-ecl-previa').textContent.includes('células')", 30)
    assert p.locator("#bl-ecl-camadas input").count() >= 2
    # menos camadas → a prévia muda
    p.fill("#bl-ecl-nz", "4")
    p.dispatch_event("#bl-ecl-nz", "change")
    janela.esperar("document.getElementById('bl-ecl-previa').textContent.includes('× 4 =')", 30)
    # volumetria com valores digitados
    p.fill("#bl-vol-tabela input[data-chave='ACU'][data-par='ntg']", "0,5")
    p.fill("#bl-vol-tabela input[data-chave='ACU'][data-par='phi']", "0,2")
    p.fill("#bl-vol-tabela input[data-chave='ACU'][data-par='sw']", "0,3")
    p.click("#bl-vol-calc")
    janela.esperar("document.querySelector('#bl-vol-tabela tfoot').textContent.match(/\\d/)", 30)
    pasta = tmp_path / "ambiente_teste" / "exportacoes" / "blocos"
    for botao, texto in (("#bl-mapas", "_mapas"), ("#bl-ecl", ".DATA"), ("#bl-vol-csv", "_volumetria.csv"),
                         ("#bl-glb", ".glb")):
        p.click(botao)
        janela.esperar(f"document.getElementById('bl-exportado').textContent.includes('{texto}')", 60)
    assert any(pasta.glob("*_mapas/terreno.tif")) and any(pasta.glob("*_eclipse/*.GRDECL"))
    assert next(pasta.glob("*.glb")).read_bytes()[:4] == b"glTF"
    assert "informado" in next(pasta.glob("*_volumetria.csv")).read_text("utf-8-sig")
    assert not janela.erros_js, janela.erros_js


def test_bloco_escala_interpolacao_e_comparacao(janela, tmp_path):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    pos = [(-5.00, -37.00), (-5.00, -36.96), (-5.04, -37.00), (-5.04, -36.96), (-5.02, -36.98),
           (-5.01, -36.99), (-5.03, -36.97), (-5.01, -36.97), (-5.03, -36.99)]
    for k, (la, lo) in enumerate(pos):
        leste = (lo + 37.00) * 111.0
        poco(b, f"1-AA-{k + 1}-RN", la, lo, 50.0,
             [("F", "JANDAI", 20, 300 + 10 * leste + 3 * k), ("F", "ACU", 300 + 10 * leste + 3 * k, 700)],
             prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('9 poço')")
    # escala: reservatório preenche o formulário (spline topo a topo, sem margem)
    janela.esperar("document.getElementById('bl-m-estrutura').options.length === 6")
    assert p.input_value("#bl-escala") == "reservatorio"
    assert p.input_value("#bl-m-estrutura") == "spline" and p.input_value("#bl-empilhamento") == "topos"
    assert "spline" in p.text_content("#bl-escala-ajuda")
    assert "Spline" in p.text_content("#bl-metodo-ajuda") and "Bom para" in p.text_content("#bl-metodo-ajuda")
    # bacia: tendência + krigagem, 15 km, regional; aparecem os parâmetros do variograma
    p.select_option("#bl-escala", "bacia")
    assert p.input_value("#bl-m-estrutura") == "tendencia" and p.input_value("#bl-distmax") == "15"
    assert p.input_value("#bl-modo") == "todos"
    assert p.locator("[data-param='grau']").get_attribute("hidden") is None
    # mexer à mão: personalizada
    p.select_option("#bl-escala", "reservatorio")
    p.select_option("#bl-m-estrutura", "krigagem")
    assert p.input_value("#bl-escala") == ""
    assert "Krigagem" in p.text_content("#bl-metodo-ajuda")
    assert p.locator("[data-param='grau']").get_attribute("hidden") is not None       # sem tendência
    assert p.locator("[data-param='potencia']").get_attribute("hidden") is None       # propriedades por IDW
    p.uncheck("#bl-suavidade-auto")
    p.fill("#bl-suavidade", "0.3")
    p.dispatch_event("#bl-suavidade", "input")
    assert p.text_content("#bl-suavidade-v") in ("0,3", "0,30")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '9'")
    # qual método usar: leque, 9 poços → RBF indicada; krigagem com poucos poços para o variograma
    p.select_option("#bl-ambiente", "leque")
    janela.esperar("document.querySelector('#bl-guia-lista > li .g-cab strong') && "
                   "document.querySelector('#bl-guia-lista > li .g-cab strong').textContent.includes('RBF')")
    assert "indicado" in p.text_content("#bl-guia-lista > li:first-child .g-selo")
    assert "9 poço(s)" in p.text_content("#bl-guia-fontes") and "sem comparação" in p.text_content("#bl-guia-fontes")
    assert "variograma ainda é pouco confiável" in p.text_content("#bl-guia-lista")
    p.select_option("#bl-m-estrutura", "krigagem")
    p.uncheck("#bl-suavidade-auto")
    p.fill("#bl-suavidade", "0.3")
    p.dispatch_event("#bl-suavidade", "input")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 60)
    assert "krigagem" in p.text_content("#bl-resumo")
    assert janela.api.bloco_abrir(p.evaluate("bl.ultimo"))["modelo"]["ambiente"] == "leque"
    reg = janela.api.bloco_abrir(p.evaluate("bl.ultimo"))["modelo"]["parametros"]["interpolacao"]
    assert reg["estrutura"]["metodo"] == "krigagem" and reg["estrutura"]["suavidade"] == 0.3
    # σ da krigagem para colorir o topo
    opcoes = p.evaluate("[...document.getElementById('bl-drape-unidade').options].map(o => o.value)")
    assert "ACU" in opcoes
    p.select_option("#bl-drape-unidade", "ACU")
    assert "sigma_m" in p.evaluate("[...document.getElementById('bl-drape-prop').options].map(o => o.value)")
    # comparar os métodos
    aba_bloco(p, "validar")
    p.click("#bl-comparar")
    janela.esperar("!document.getElementById('bl-cmp').hidden", 120)
    assert "Errou menos" in p.text_content("#bl-cmp-resumo")
    assert p.locator("#bl-cmp-tabela thead th").count() == 2 + 8
    # o guia passa a contar a comparação: o melhor método ganha "seus poços"
    janela.esperar("document.getElementById('bl-guia-fontes').textContent.includes('com a comparação')", 20)
    assert "seus poços" in p.text_content("#bl-guia-lista")
    assert p.locator("#bl-cmp-tabela td.melhor").count() >= 2
    for f in ("csv", "svg"):
        p.click(f"[data-comparacao='{f}']")
        janela.esperar(f"document.getElementById('bl-exportado').textContent.includes('_metodos.{f}')", 30)
    pasta = tmp_path / "ambiente_teste" / "exportacoes" / "blocos"
    assert next(pasta.glob("*_metodos.csv")).read_text("utf-8-sig").startswith("metodo;nome")
    # usar o melhor e montar de novo: o formulário fica com o método sugerido e o bloco novo o usa
    melhor = p.evaluate("bl.modelo.comparacao.candidatos.find(c => c.id === bl.modelo.comparacao.melhor)")
    if not p.locator("#bl-cmp-usar").is_disabled():
        antes = p.evaluate("bl.ultimo")
        p.click("#bl-cmp-usar")
        janela.esperar(f"bl.ultimo && bl.ultimo !== '{antes}'", 60)
        assert p.input_value("#bl-m-estrutura") == melhor["interpolacao"]["estrutura"]["metodo"]
        assert p.input_value("#bl-m-propriedades") == "idw"            # a comparação não mexe nas propriedades
    # reabrir um bloco: o formulário volta com a interpolação dele
    p.select_option("#bl-m-estrutura", "idw")
    p.locator("#bl-historico button").last.click()
    janela.esperar("document.getElementById('bl-m-estrutura').value === 'krigagem'", 30)
    janela.esperar("!document.getElementById('bl-cmp').hidden", 30)
    assert not janela.erros_js, janela.erros_js


def test_campo_um_clique_producao_e_camadas(janela, tmp_path, monkeypatch):
    import requests
    from externos_util import SessaoFalsa
    from test_secao import poco
    falsa = SessaoFalsa()
    monkeypatch.setattr(requests, "Session", lambda: falsa)
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300), ("F", "ACU", 300, 700)], prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    # escolher o campo já traz os poços; "Montar este campo" traz e monta, com título
    assert p.locator("#bl-montar-campo").is_visible()
    p.dispatch_event("#bl-campo", "change")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.click("#bl-limpar")
    p.click("#bl-montar-campo")
    janela.esperar("!document.getElementById('bl-painel').hidden", 60)
    assert p.input_value("#bl-titulo") == "Campo de Campo Teste" and p.text_content("#bl-n") == "5"
    p.select_option("#bl-modo", "raio")
    assert not p.locator("#bl-montar-campo").is_visible() and not p.locator("#bl-bacia-box").is_visible()
    # produção da ANP: o campo do bloco já vem preenchido
    assert p.input_value("#pr-campo") == "CAMPO TESTE"
    ir(p, "dados", "producao")
    p.select_option("#pr-periodo", "tudo")
    p.click("#pr-baixar")
    janela.esperar("document.getElementById('pr-resumo').textContent.includes('Plano de Desenvolvimento')", 60)
    texto = p.text_content("#pr-resumo")
    assert "01/1983 a 06/2026" in texto and "13,8" in texto and "Por zona produtora: 2 zona(s)" in texto
    assert "Formação Açu" in texto and "polígono com 3 vértices" in texto
    p.click("#pr-csv")
    janela.esperar("document.getElementById('status').textContent.includes('producao_campo_teste_por_poco.csv')", 30)
    assert (tmp_path / "ambiente_teste" / "exportacoes" / "producao" / "producao_campo_teste_por_zona.csv").exists()
    # camadas (aba Dados): marcadas as padrão; uma que falha aparece na lista de erros
    ir(p, "dados", "camadas")
    janela.esperar("document.querySelectorAll('#cm-lista input').length > 10", 30)
    assert p.locator("#cm-lista input[value='epe_gasodutos_transporte']").is_checked()
    assert not p.locator("#cm-lista input[value='ibge_rodovias']").is_checked()
    p.click("#cm-baixar")
    janela.esperar("document.getElementById('cm-lista').textContent.includes('1.500 feições')", 60)
    assert p.locator("#cm-erros li").count() >= 1 and "Blocos" in p.text_content("#cm-erros")
    assert (tmp_path / "ambiente_teste" / "sig" / "camadas.json").exists()
    assert not janela.erros_js, janela.erros_js


def test_camadas_no_mapa_e_distancias_do_campo(janela, tmp_path, monkeypatch):
    import requests
    from externos_util import SessaoFalsa
    falsa = SessaoFalsa()
    monkeypatch.setattr(requests, "Session", lambda: falsa)
    p = janela.page
    abrir_projeto(janela)
    from motor import producao as mpr
    mpr.baixar(janela.api._banco, janela.api._projeto.pasta, "Campo Teste", sessao=falsa)
    ir(p, "dados", "camadas")
    janela.esperar("document.querySelectorAll('#cm-lista input').length > 10", 30)
    for cb in p.locator("#cm-lista input").all():
        cb.uncheck()
    for ident in ("epe_gasodutos_transporte", "anp_campos_producao", "ibge_dutos", "epe_h2_projetos"):
        p.check(f"#cm-lista input[value='{ident}']")
    p.click("#cm-baixar")
    janela.esperar("document.querySelectorAll('#cm-mapa input').length === 4", 60)
    # liga uma camada no mapa (aba Mapa): os traços aparecem
    p.click("#aba-mapa")
    p.check("#cm-mapa input[data-camada='ibge_dutos']")
    janela.esperar("sig.camadas.ibge_dutos && mapa.hasLayer(sig.camadas.ibge_dutos)", 30)
    assert p.evaluate("sig.camadas.ibge_dutos.getLayers().length") == 2
    p.uncheck("#cm-mapa input[data-camada='ibge_dutos']")
    janela.esperar("!sig.camadas.ibge_dutos", 30)
    # campo × infraestrutura (aba Viabilidade)
    ir(p, "viab")
    p.fill("#vb-campo", "CAMPO TESTE")
    p.click("#vb-medir")
    janela.esperar("document.getElementById('vb-resultado').textContent.includes('Gasoduto de transporte')", 30)
    texto = p.text_content("#vb-resultado")
    assert "ANP — vértices" in texto and "Depleção" in texto and "10,1%" in texto
    assert "Sem a camada" in texto and "Porto" in texto
    p.click("#vb-csv")
    janela.esperar("document.getElementById('status').textContent.includes('distancias_campo_teste.csv')", 30)
    # viabilidade econômica: só com a produção, o método simples (PIBIC)
    janela.esperar("!document.getElementById('vb-eco').hidden", 30)
    assert p.input_value("#vb-custo") == "488" and p.input_value("#vb-diametro") == "8"
    p.click("#vb-avaliar")
    janela.esperar("document.getElementById('vb-eco-resultado').textContent.includes('Custo do duto')", 30)
    t = p.text_content("#vb-eco-resultado")
    assert "Simples (PIBIC)" in t and "m³ de óleo equivalente" in t and "falta: Bo (ou o grau API" in t
    assert "Gasoduto de transporte" in t and "R$/m³ oe" in t and "Plano de Desenvolvimento" in t
    # com Bo, Bg, Rs, P e T: os três métodos
    p.click("summary:has-text('Espaço poroso')")
    p.fill("[data-vb='bo']", "1,2")
    p.fill("[data-vb='bg']", "0,006")
    p.fill("[data-vb='rs']", "100")
    p.click("summary:has-text('Pela molécula')")
    p.fill("[data-vb='pressao_bar']", "80")
    p.fill("[data-vb='temperatura_c']", "35")
    p.click("#vb-avaliar")
    janela.esperar("document.getElementById('vb-eco-resultado').textContent.includes('Mt de CO₂')", 30)
    assert "sem dados" not in p.text_content("#vb-eco-resultado")
    p.select_option("#vb-fluido", "h2")
    assert "×1,05" in p.text_content("#vb-custo-ajuda")
    p.click("#vb-avaliar")
    janela.esperar("document.getElementById('vb-eco-resultado').textContent.includes('R$/MWh')", 30)
    assert "★ Hidrogênio verde" in p.text_content("#vb-eco-resultado")
    # memória de cálculo, equações e constantes editáveis
    janela.esperar("!document.getElementById('vb-mem-caixa').hidden", 30)
    assert "pasta do projeto: execucoes/viabilidade/" in p.text_content("#vb-mem-arquivo")
    mem = p.text_content("#vb-memoria")
    assert "oe = Np + Gp / gas_por_oe" in mem and "Peng-Robinson" in mem and "Plano de Desenvolvimento" in mem
    pasta_mem = os.path.join(janela.api._projeto.pasta, "execucoes", "viabilidade")
    assert any(n.endswith(".html") for n in os.listdir(pasta_mem))
    p.click("summary:has-text('Equações')")
    p.select_option("[data-vbe-sel='espaco_simples']", "0")
    assert p.input_value("[data-vbe='espaco_simples']") == "Np"
    p.click("summary:has-text('Constantes')")
    p.fill("[data-vbc='f_h2']", "1,3")
    assert "×1,3" in p.text_content("#vb-custo-ajuda")
    p.click("#vb-avaliar")
    janela.esperar("document.getElementById('vb-memoria').textContent.includes('alternativa: só óleo e condensado')", 30)
    assert "constante(s) alterada(s)" in p.text_content("#vb-eco-resultado")
    p.fill("[data-vbe='espaco_poroso']", "Np * Bo + Zz")
    assert p.input_value("[data-vbe-sel='espaco_poroso']") == "__propria"
    p.click("#vb-avaliar")
    janela.esperar("document.getElementById('status').textContent.includes('variável desconhecida Zz')", 30)
    p.select_option("[data-vbe-sel='espaco_poroso']", "__padrao")
    p.click("#vb-eco-csv")
    janela.esperar("document.getElementById('status').textContent.includes('viabilidade_campo_teste.csv')", 30)
    # os parâmetros ficam guardados no campo
    p.fill("[data-vb='bo']", "")
    p.click("#vb-medir")
    janela.esperar("document.querySelector(\"[data-vb='bo']\").value === '1,2'", 30)
    assert p.input_value("#vb-fluido") == "h2"
    # API e densidade nos documentos dos poços do campo
    poco = "7-TT-1-RN"
    with janela.api._banco.conexao() as c:
        c.execute("INSERT INTO pocos (id, nome_anp, campo) VALUES (?, ?, 'CAMPO TESTE')", (poco, poco))
    janela.api._indice.substituir_documento("bruto/Potiguar/x/teste.pdf", "Potiguar", poco, "teste.pdf",
                                            [{"pagina": 2, "texto": "óleo de 27,5 °API", "metodo": "ocr", "titulo": ""}])
    p.click("#vb-fl-buscar")
    janela.esperar("document.getElementById('vb-fl-resultado').textContent.includes('Grau API do óleo: 27,5')", 30)
    assert "lido automaticamente" in p.text_content("#vb-fl-resultado")
    p.click("#vb-fl-resultado button:has-text('confirmar')")
    janela.esperar("document.getElementById('vb-fl-resultado').textContent.includes('dado transcrito')", 30)
    assert "Dados transcritos" in p.text_content("#vb-fl-resultado")
    assert "transcrito" in p.get_attribute("[data-vb='api']", "placeholder")
    # blocos e campos × infraestrutura: os campos de produção contra o gasoduto
    janela.esperar("[...document.querySelectorAll('#ba-areas option')].some(o => o.value === 'anp_campos_producao' && !o.disabled)", 30)
    p.select_option("#ba-areas", "anp_campos_producao")
    assert p.input_value("#ba-alvo") == "epe_gasodutos_transporte"
    p.click("#ba-medir")
    janela.esperar("document.getElementById('ba-resultado').textContent.includes('Campos de produção até Gasoduto')", 60)
    texto = p.text_content("#ba-resultado")
    assert "CAMPO TESTE" in texto and "execucoes/viabilidade/" in texto and "R$" in texto
    janela.esperar("ba.camada && mapaVb.hasLayer(ba.camada)", 30)
    p.fill("#ba-filtro", "nada-assim")
    assert "0 área(s) no filtro" in p.text_content("#ba-resultado")
    p.click("#ba-csv")
    janela.esperar("document.getElementById('status').textContent.includes('distancias_anp_campos_producao')", 30)
    assert not janela.erros_js, janela.erros_js


def test_correcao_fica_colorida_a_vista_no_texto_e_na_imagem(janela, tmp_path):
    """0.29.1: depois de corrigir, o texto não volta ao topo, a palavra pisca na cor
    nova, e a imagem contorna as palavras corrigidas. Igual ao lido = aviso no editor."""
    import pymupdf
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    doc = pymupdf.open()
    pg = doc.new_page()
    for i in range(45):                                   # texto longo: a caixa rola
        pg.insert_text((72, 60 + 16 * i), f"LINHA {i} RELATORIO DE PERFURACAO DO POCO", fontsize=9)
    pg.insert_text((72, 60 + 16 * 46), "Sonda Plataforma ww iReline", fontsize=9)
    doc.save(str(pasta / "p.pdf"))
    api = janela.api
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    rel = "bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/p.pdf"
    from motor import documentos as md
    r = md.processar_arquivo(str(pasta / "p.pdf"), tessdata=str(tmp_path))
    api._projeto.salvar_texto(rel, r)
    api._indice.substituir_documento(rel, "Potiguar", "7-GMR-13-RN", "p.pdf", r["paginas"], api._corretor)
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 1")
    p.click("#lista-docs button")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 1')")
    img_antes = p.get_attribute("#pg-img", "src")
    p.locator("#pg-texto .pal", has_text="iReline").scroll_into_view_if_needed()
    rolagem = p.evaluate("document.getElementById('pg-texto').scrollTop")
    assert rolagem > 0
    p.locator("#pg-texto .pal", has_text="iReline").click()
    p.click("#ed-form button[type=submit]")               # sem mudar nada
    assert p.is_visible("#ed-msg") and "igual ao que o OCR leu" in p.text_content("#ed-msg")
    p.fill("#ed-para", "Wireline")
    p.click("#ed-form button[type=submit]")
    janela.esperar("!!document.querySelector('#pg-texto .corr.usuario')")
    assert p.text_content("#pg-texto .corr.usuario") == "Wireline"
    assert "piscar" in p.get_attribute("#pg-texto .corr.usuario", "class")
    assert p.evaluate("document.getElementById('pg-texto').scrollTop") > 0
    assert p.get_attribute("#pg-img", "src") != img_antes  # a imagem foi repintada com o contorno
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.30: layout, cores, janelas
def test_dividir_recolher_e_guardar_o_arranjo(janela):
    p = janela.page
    abrir_projeto(janela)
    p.click("#aba-mapa")
    menu_janela(p)
    p.click("#btn-dividir")
    assert p.is_visible("#vista-mapa") and p.is_visible("#vista-docs") and p.is_visible("#divisor")
    assert "direita" in p.get_attribute("#aba-docs", "class")
    # a área da direita troca de aba; os lados trocam
    menu_janela(p)
    p.select_option("#div-dir", "perfis")
    assert p.is_visible("#vista-perfis") and not p.is_visible("#vista-docs")
    p.click("#div-trocar")
    assert "ativa" in p.get_attribute("#aba-perfis", "class") and "direita" in p.get_attribute("#aba-mapa", "class")
    # arrastar a divisória muda a proporção
    caixa = p.locator("#divisor").bounding_box()
    p.mouse.move(caixa["x"] + 3, caixa["y"] + 200)
    p.mouse.down()
    p.mouse.move(1000, caixa["y"] + 200, steps=5)
    p.mouse.up()
    flex = p.evaluate("getComputedStyle(document.getElementById('vista-perfis')).flexGrow")
    assert 0.65 < float(flex) < 0.75
    # clicar na aba da direita a traz para a esquerda
    p.click("#aba-mapa")
    assert "ativa" in p.get_attribute("#aba-mapa", "class")
    # recolher a barra lateral do Mapa
    p.locator("#vista-mapa > .lateral > .recolher").click()
    assert "recolhida" in p.get_attribute("#vista-mapa", "class")
    assert p.is_visible("#vista-mapa .rotulo-vertical") and not p.is_visible("#etapa-filtros")
    janela.page.wait_for_timeout(600)          # o arranjo é gravado com um pequeno atraso
    pref = janela.api._preferencias().ler()
    assert pref["recolhidas"] == {"mapa": True}
    assert pref["layout"]["dividida"] and pref["layout"]["ativa"] == "mapa" and pref["layout"]["direita"] == "perfis"
    menu_janela(p)
    p.click("#btn-dividir")
    assert not p.is_visible("#divisor") and not p.is_visible("#vista-perfis")
    assert not janela.erros_js, janela.erros_js


def test_configuracoes_cores_diagnostico_exportacoes_historico(janela, monkeypatch):
    abertas = []
    monkeypatch.setattr("ponte.comunidade._abrir_no_sistema", abertas.append)
    p = janela.page
    assert p.get_attribute("html", "data-paleta") == "marinho"
    abrir_projeto(janela)
    p.click("#btn-config")
    assert p.is_visible("#config") and p.locator("#cfg-paletas .paleta").count() == 7
    assert "ativa" in p.get_attribute("#cfg-paletas .paleta >> nth=0", "class")
    p.click("#cfg-paletas .paleta:has-text('Arenito')")
    p.select_option("#cfg-tema", "escuro")
    p.select_option("#cfg-fonte", "G")
    assert p.get_attribute("html", "data-paleta") == "arenito" and p.get_attribute("html", "data-tema") == "escuro"
    janela.esperar("document.documentElement.dataset.fonte === 'G'")
    pref = janela.api._preferencias().ler()
    assert (pref["paleta"], pref["tema"], pref["fonte"]) == ("arenito", "escuro", "G")
    fundo = p.evaluate("getComputedStyle(document.body).backgroundColor")
    assert fundo == "rgb(23, 20, 15)"                 # fundo escuro do Arenito
    p.uncheck("#cfg-abrir")
    # diagnóstico: versões e erros
    p.click("[data-cfg='diag']")
    janela.esperar("document.getElementById('dg-conteudo').textContent.includes('Python')")
    p.click("#dg-copiar")
    janela.esperar("document.getElementById('status').textContent.includes('copi')")
    p.keyboard.press("Escape")
    assert p.is_hidden("#config")
    assert janela.api._preferencias().ler()["abrir_ao_iniciar"] is False
    # exportações
    p.click("#btn-exportacoes")
    janela.esperar("document.querySelectorAll('#exp-lista .pasta-linha').length === 4")
    p.click("#exp-lista .pasta-linha:has-text('sig') button")
    janela.esperar("document.getElementById('status').textContent.includes('aberta no Explorador')")
    assert abertas and abertas[-1].endswith("sig")
    # histórico: a mensagem inteira, mesmo a que o rodapé corta
    p.click("#status")
    assert p.is_visible("#historico") and p.is_hidden("#exportacoes")
    assert "aberta no Explorador" in p.text_content("#hist-lista")
    assert "Projeto criado" in p.text_content("#hist-lista")
    p.keyboard.press("Escape")
    assert p.is_hidden("#historico")
    assert not janela.erros_js, janela.erros_js


def test_abre_o_projeto_sozinho_com_progresso(janela, tmp_path):
    from interface_util import abrir
    api = janela.api
    api.abrir_projeto_padrao()                    # cria siapp.json (o projeto "já existe")
    api._projeto = None
    api._janela.js.queue.clear()
    jt, _ = abrir(api, janela.navegador, srv=janela.srv)
    jt.esperar("document.getElementById('ini-pasta').disabled")
    assert "Abre sozinho ao iniciar" in jt.status() or "Projeto aberto" in jt.status()
    assert jt.page.is_hidden("#abertura")
    # a tela "Abrindo o projeto" (no pywebview, os passos chegam durante a abertura)
    jt.page.evaluate("inicioAbertura(); progressoAbertura({passo: 1, total: 5, texto: 'Abrindo a pasta'});"
                     "progressoAbertura({passo: 2, total: 5, texto: 'Lendo o banco do projeto (134 MB)'})")
    assert jt.page.is_visible("#abertura") and jt.page.locator("#ab-passos li").count() == 2
    assert "134 MB" in jt.page.text_content("#ab-passos li.atual")
    jt.page.evaluate("fimAbertura()")
    assert jt.page.is_hidden("#abertura")
    assert not jt.erros_js, jt.erros_js
    jt.page.close()


def test_aba_em_janela_propria_e_conversa_entre_janelas(janela, tmp_path):
    import pymupdf

    from interface_util import abrir_destacada
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    doc = pymupdf.open()
    for i in range(3):
        doc.new_page().insert_text((72, 100), f"PAGINA {i + 1} RELATORIO DE PERFURACAO DO POCO 7-GMR-13-RN", fontsize=10)
    doc.save(str(pasta / "p.pdf"))
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    # a aba Documentos vai para uma janela própria
    docs = abrir_destacada(janela, "docs")
    docs.esperar("!document.getElementById('vista-docs').hidden")
    assert docs.page.is_hidden("#abas") and docs.page.text_content("#janela-nome") == "Documentos"
    assert "Voltar para a principal" in docs.page.text_content("#btn-janela")
    assert docs.page.is_hidden("#vista-projeto") and docs.page.is_hidden("#btn-dividir")
    docs.esperar("document.querySelectorAll('#lista-docs button').length === 1")
    # a principal fica sabendo: a aba aparece marcada e sai da área visível
    p.evaluate("janelasMudaram(['docs'])")
    assert "fora" in p.get_attribute("#aba-docs", "class")
    # um pedido da principal para Documentos vai para a janela própria
    p.evaluate("abrirBaixado('bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/p.pdf', null, 'documento')")
    docs.esperar("document.getElementById('pg-num').textContent.includes('1 de 3')")
    assert p.is_hidden("#vista-docs")
    assert docs.falsa.focada >= 1
    # "Voltar para a principal" fecha a janela própria
    menu_janela(docs.page)
    docs.page.click("#btn-janela")
    assert docs.falsa.destruida
    assert not docs.erros_js and not janela.erros_js, (docs.erros_js, janela.erros_js)
    docs.page.close()


# ---------------------------------------------------------------- 0.31: documentos e texto
def _docs_de_teste(janela, tmp_path):
    """Três documentos em duas bacias (texto embutido: não precisa do OCR)."""
    import pymupdf
    from motor import documentos as md
    api = janela.api
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    feitos = []
    for bacia, poco, nome, paginas in [
            ("Potiguar", "7-GMR-13-RN", "pasta.pdf", ["perda de circulacao na fase de 12 1/4 pol", "relatorio diario de perfuracao sem ocorrencias", "perda de circulacao severa no fundo do poco"]),
            ("Potiguar", "7-GMR-14-RN", "rfp.pdf", ["relatorio final com perda de circulacao parcial"]),
            ("Alagoas", "3-PIA-12-AL", "pasta.pdf", ["perda de circulacao total na formacao Muribeca", "o amanheccr do relatorio diario de perfuracao"])]:
        pasta = tmp_path / "ambiente_teste" / "bruto" / bacia / poco / "Pasta de Poco"
        pasta.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open()
        for t in paginas:
            doc.new_page().insert_text((72, 100), t, fontsize=11)
        doc.save(str(pasta / nome))
        rel = f"bruto/{bacia}/{poco}/Pasta de Poco/{nome}"
        api._projeto.salvar_texto(rel, md.processar_arquivo(str(pasta / nome), tessdata=str(tmp_path)))
        api._reindexar_documento(rel)
        feitos.append(rel)
    with api._banco.conexao() as c:
        c.execute("INSERT INTO pocos (id, campo, bacia) VALUES ('7-GMR-13-RN', 'GUAMARÉ', 'Potiguar'), "
                  "('7-GMR-14-RN', 'GUAMARÉ', 'Potiguar'), ('3-PIA-12-AL', 'PILAR', 'Alagoas')")
    return feitos


def test_lista_agrupada_filtro_e_busca_no_escopo(janela, tmp_path):
    p = janela.page
    abrir_projeto(janela)
    rels = _docs_de_teste(janela, tmp_path)
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 3")
    # agrupado por bacia › poço, com o campo do cadastro
    assert p.locator(".grupo-docs.bacia").count() == 2
    assert "GUAMARÉ" in p.text_content(".grupo-docs.poco[data-chave='p:Potiguar/7-GMR-13-RN'] summary")
    p.select_option("#df-campo", "GUAMARÉ")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 2")
    assert "2 de 3" in p.text_content("#df-resumo")
    # buscar só nos documentos do filtro
    p.select_option("#busca-escopo", "filtrados")
    p.fill("#busca", "circulacao")
    p.click("#btn-buscar")
    janela.esperar("document.querySelectorAll('#resultados button').length === 3")
    assert "do filtro" in p.text_content("#busca-resumo")
    # andar pelos achados de documento em documento
    p.click("#resultados button >> nth=0")
    janela.esperar("document.getElementById('ac-num').textContent.includes('achado 1 de 3')")
    p.click("#ac-prox")
    janela.esperar("document.getElementById('ac-num').textContent.includes('achado 2 de 3')")
    assert "ativo" in p.get_attribute("#resultados button >> nth=1", "class")
    p.keyboard.press("F3")
    janela.esperar("document.getElementById('ac-num').textContent.includes('achado 3 de 3')")
    assert p.is_disabled("#ac-prox")
    # só no documento aberto: em ordem de página
    p.click("#df-limpar")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 3")
    p.click(f"#lista-docs button[data-rel='{rels[0]}']")
    janela.esperar("document.getElementById('pg-num').textContent.includes('de 3')")
    p.select_option("#busca-escopo", "este")
    p.click("#btn-buscar")
    janela.esperar("document.querySelectorAll('#resultados button').length === 2")
    assert [p.text_content(f"#resultados button >> nth={i} >> .r-cab") .split("pág ")[1][:1] for i in range(2)] == ["1", "3"]
    # pular para a página
    p.fill("#pg-ir", "2")
    p.press("#pg-ir", "Enter")
    janela.esperar("document.getElementById('pg-num').textContent === 'pág 2 de 3'")
    assert "não está entre eles" in p.text_content("#ac-termo")
    assert not janela.erros_js, janela.erros_js


def test_editar_texto_da_pagina_e_possiveis_erros(janela, tmp_path):
    p = janela.page
    abrir_projeto(janela)
    rels = _docs_de_teste(janela, tmp_path)
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 3")
    p.evaluate(f"abrirPagina({rels[2]!r}, 2, '')")
    janela.esperar("document.getElementById('pg-num').textContent === 'pág 2 de 2'")
    # possível erro com sugestão: abre o editor de correção já preenchido
    assert p.is_visible("#pg-erros-box")
    p.click("#pg-erros-box summary")
    p.locator(".chip-erro", has_text="amanheccr").click()
    assert p.is_visible("#editor") and p.input_value("#ed-para") == "amanhecer"
    assert p.locator("#ed-sugestoes .chip-busca").count() >= 1
    p.click("#ed-fechar")
    # como o OCR leu × texto arrumado
    p.click("#pg-ver-ocr")
    assert "ocr" in p.get_attribute("#pg-texto", "class") and p.is_hidden("#pg-erros-box")
    p.click("#pg-ver-final")
    # editar e salvar: vale na página e na busca
    p.click("#pg-editar")
    assert p.is_visible("#pg-edicao") and "amanheccr" in p.input_value("#pg-edicao-texto")
    p.fill("#pg-edicao-texto", "O amanhecer do relatório.\n\nSegundo parágrafo com testemunhagem.")
    p.click("#pg-ant")                                       # não sai com edição por salvar
    assert p.is_visible("#pg-edicao-msg") and "Salve ou cancele" in p.text_content("#pg-edicao-msg")
    p.click("#pg-edicao-salvar")
    janela.esperar("document.getElementById('pg-modo').textContent === 'revisado'")
    assert "Segundo parágrafo" in p.inner_text("#pg-texto")
    assert p.is_hidden("#pg-erros-box")
    assert "1 revisada" in p.text_content(f"#lista-docs button[data-rel='{rels[2]}']")
    p.fill("#busca", "testemunhagem")
    p.select_option("#busca-escopo", "todos")
    p.click("#btn-buscar")
    janela.esperar("document.querySelectorAll('#resultados button').length === 1")
    # voltar ao texto automático: dois cliques
    p.click("#pg-editar")
    p.click("#pg-edicao-auto")
    assert "Confirmar" in p.text_content("#pg-edicao-auto")
    p.click("#pg-edicao-auto")
    janela.esperar("document.getElementById('pg-modo').textContent !== 'revisado'")
    assert "amanheccr" in p.inner_text("#pg-texto")
    assert not janela.erros_js, janela.erros_js


def test_transcrever_trecho_de_texto_livre(janela, tmp_path):
    p = janela.page
    abrir_projeto(janela)
    rels = _docs_de_teste(janela, tmp_path)
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 3")
    p.evaluate(f"abrirPagina({rels[0]!r}, 1, '')")
    janela.esperar("document.getElementById('pg-num').textContent === 'pág 1 de 3'")
    p.click("#tr-box summary")
    p.select_option("#tr-tipo", "trecho")
    assert p.is_visible("#tr-trecho") and p.is_hidden("#tr-valor")
    p.evaluate("sugerirDoOCR([0, 0, 1, 0.2])")
    janela.esperar("document.getElementById('tr-trecho').value.includes('circulacao')")
    p.fill("#tr-nome", "Perda de circulação")
    p.fill("#tr-trecho", "perda de circulacao\nna fase de 12 1/4 pol")
    p.click("#tr-form button[type=submit]")
    janela.esperar("document.querySelectorAll('#tr-lista td.trecho').length === 1")
    f = janela.api._banco.fatos(fonte_rel=rels[0], pagina=1)[0]
    assert f["tipo"] == "trecho" and f["observacao"] == "perda de circulacao\nna fase de 12 1/4 pol"
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.32: bloco 3D
def test_bloco_aparencia_dos_pocos_vale_na_hora(janela, tmp_path):
    import numpy as np
    from test_bloco import _avaliacao
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    ex = str(tmp_path / "ambiente_teste" / "execucoes")
    pocos = [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
             ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]
    for pid, la, lo in pocos:
        leste = (lo + 37.00) * 111.0
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)],
             prof_final=900)
        prof = np.arange(320, 700, 0.5)
        _avaliacao(ex, pid, f"avaliacao_{pid}_1", prof, (prof > 400).astype(float), (prof > 500).astype(float),
                   [{"nome": "Açu", "topo": 320, "base": 700, "hpv_m": 3.0, "net_pay_m": 20.0,
                     "ntg": 0.6, "phi_media_pay": 0.2, "sw_media_pay": 0.35}])
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    # ordem da receita (0.59): poços → método → unidades e grade, e Montar no pé
    passos = p.evaluate("[...document.querySelectorAll('#vista-bloco details.passo > summary')].map(h => h.textContent.trim())")
    assert [x[:1] for x in passos[:3]] == ["1", "2", "3"] and passos[0].startswith("1Poços")
    assert p.evaluate("document.querySelector('#vista-bloco .lateral').lastElementChild.querySelector('#bl-montar') !== null")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 30)
    assert p.evaluate("window.BlocoVisor.estado().marcadores") == 5
    # marcador, cores da trilha e legenda mudam sem montar de novo
    p.click("#bl-aparencia summary")
    p.select_option("#bl-ap-forma", "cubo")
    janela.esperar("window.BlocoVisor.estado().forma === 'cubo'")
    assert p.evaluate("window.BlocoVisor.estado().superficies") == 2           # mesmo bloco
    assert p.locator("#bl-ap-cores input[type=color]").count() >= 2
    p.locator("#bl-ap-cores input[type=color]").first.evaluate(
        "e => { e.value = '#ff0000'; e.dispatchEvent(new Event('input')); }")
    p.select_option("#bl-ap-forma", "nenhum")
    janela.esperar("window.BlocoVisor.estado().marcadores === 0")
    p.uncheck("#bl-ap-legenda")
    assert p.locator(".bl-leg-trilha").is_hidden()
    # a escolha fica guardada nas preferências
    janela.esperar("bl.aparencia && bl.aparencia.marcador.forma === 'nenhum'")
    for _ in range(50):
        p.wait_for_timeout(100)                 # a gravação é adiada 0,4 s (várias mudanças seguidas = uma)
        ap = janela.api._preferencias().ler().get("bloco", {}).get("aparencia", {})
        if ap.get("legenda") is False:
            break
    assert ap["marcador"]["forma"] == "nenhum" and ap["legenda"] is False
    assert "#ff0000" in ap["trilha"]["cores"].values()
    # no bloco fechado, os poços ficam por cima (aparecem dentro do bloco)
    p.click("[data-modo3d='fechado']")
    assert p.evaluate("window.BlocoVisor.estado().porCima") is True
    p.select_option("#bl-ap-porcima", "nunca")
    assert p.evaluate("window.BlocoVisor.estado().porCima") is False
    # a trilha escolhida continua ao montar de novo
    p.select_option("#bl-trilha", "nenhuma")
    janela.esperar("window.BlocoVisor.estado().trilhas === 0")
    antes = p.evaluate("bl.ultimo")
    p.click("#bl-montar")
    janela.esperar(f"bl.ultimo && bl.ultimo !== '{antes}'", 30)
    assert p.input_value("#bl-trilha") == "nenhuma"
    aba_bloco(p, "validar")
    p.click("#bl-explica summary")
    assert "erro = previsto − AGP" in p.text_content("#bl-explica")
    # a figura usa a mesma aparência
    aba_bloco(p, "exportar")
    p.click("[data-figura='svg']")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_figura.svg')", 30)
    svg = next((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("*_figura.svg")).read_text("utf-8")
    assert "poço (cabeça)" not in svg
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.33: perfis e modo escuro
def test_perfis_busca_sugestao_cabecalho_e_faixa(janela, tmp_path):
    from test_perfis import las_exemplo
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Perfis"
    pasta.mkdir(parents=True)
    las_exemplo(pasta / "7gmr13.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas:not(#pf-nav)').length === 3", 30)
    # cabeçalhos da mesma altura: as trilhas começam todas na mesma linha
    alturas = p.evaluate("[...document.querySelectorAll('.pf-cab-trilha')].map(c => c.offsetHeight)")
    assert len(set(alturas)) == 1
    topos = p.evaluate("[...document.querySelectorAll('#pf-trilhas canvas:not(#pf-nav)')].map(c => Math.round(c.getBoundingClientRect().top))")
    assert len(set(topos)) == 1
    # buscar curva por descrição da família
    p.fill("#pf-busca", "resistividade")
    janela.esperar("document.querySelectorAll('#pf-curvas li').length === 1")
    assert "ILD" in p.text_content("#pf-curvas") and "1 curva(s)" in p.text_content("#pf-busca-n")
    p.fill("#pf-busca", "nada disso")
    janela.esperar("document.querySelectorAll('#pf-curvas li').length === 0")
    assert "Nenhuma curva" in p.text_content("#pf-busca-n")
    # sugerir para um objetivo
    p.select_option("#pf-objetivo", "saturacao")
    janela.esperar("!document.getElementById('pf-sugestao').hidden")
    assert "Archie" in p.text_content("#pf-sugestao") and "não tem" in p.text_content("#pf-sugestao")
    assert p.evaluate("pf.selecao.map(s => s.mnemonico)") == ["ILD", "GR"]
    assert p.input_value("#pf-busca") == ""
    # arrastar: a faixa aparece com as profundidades enquanto arrasta
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas:not(#pf-nav)').length === 3", 30)
    cv = p.locator("#pf-trilhas canvas:not(#pf-nav)").nth(1)
    caixa = cv.bounding_box()
    p.mouse.move(caixa["x"] + 30, caixa["y"] + 100)
    p.mouse.down()
    p.mouse.move(caixa["x"] + 30, caixa["y"] + 180)
    assert p.is_visible("#pf-faixa-sel") and " m" in p.text_content("#pf-faixa-sel")
    p.mouse.up()
    assert p.is_hidden("#pf-faixa-sel") and p.input_value("#pf-int-topo")
    assert not janela.erros_js, janela.erros_js


def test_modo_escuro_texto_escuro_nas_figuras(janela, tmp_path):
    p = janela.page
    abrir_projeto(janela)
    p.evaluate("document.documentElement.dataset.tema = 'escuro'")
    cor = lambda sel: p.evaluate(f"getComputedStyle(document.querySelector('{sel}')).color")
    claro = "rgb(28, 34, 39)"                                   # --tinta do papel
    assert cor(".mapa-legenda") == claro
    assert p.evaluate("getComputedStyle(document.body).color") != claro       # fora das figuras, o tema escuro
    for sel in ("#bl-visor", "#sec-figura", "#pf-trilhas", "#pg-quadro"):
        assert cor(sel) == claro, sel


# ---------------------------------------------------------------- 0.34: mapa e seção
def test_mapa_legenda_destaque_producao_e_secao_pela_linha(janela):
    from test_pocos import csv_exemplo
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    b = janela.api._banco
    for pid, lon in [("1-OES-1-RN", -36.80), ("1-MEI-1-RN", -36.75), ("1-LES-1-RN", -36.70)]:
        poco(b, pid, -5.30, lon, 40.0, [("F", "JANDAI", 10, 300), ("F", "ACU", 300, 700)], prof_final=900)
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('poço')")
    p.select_option("#f-bacia", "")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('6 poço')")
    assert p.evaluate("camadaPocos.getLayers().length") == 6
    # legenda: um clique esconde a categoria; a lista diz quantos ficaram escondidos
    assert "(6)" in p.text_content("#legenda-pasta [data-cat='cad']")
    p.click("#legenda-pasta [data-cat='cad']")
    janela.esperar("camadaPocos.getLayers().length === 0")
    assert "desligado" in p.get_attribute("#legenda-pasta [data-cat='cad']", "class")
    assert "escondido" in p.text_content("#lista-mapa")
    p.click("#legenda-pasta [data-cat='cad']")
    janela.esperar("camadaPocos.getLayers().length === 6")
    # destacar poços
    p.fill("#dq-poco", "1-OES-1-RN, 1-NAO-9-XX")
    p.click("#dq-form button[type=submit]")
    janela.esperar("camadaDestaques.getLayers().length === 1")
    assert "1-OES-1-RN" in p.text_content("#dq-chips") and "1-NAO-9-XX" in janela.status()
    # ficha: produção (campo ainda não baixado → atalho para Dados › Produção)
    p.evaluate("abrirFicha('1-OES-1-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Produção (ANP)')")
    assert "ainda não foi baixada" in p.text_content("#fi-corpo")
    p.click("#fi-fechar")
    # seção por uma linha desenhada no mapa
    p.click("#btn-mapa-linha")
    assert p.is_visible("#mapa-linha")
    p.evaluate("mapa.fire('click', {latlng: L.latLng(-5.30, -36.81)}); mapa.fire('click', {latlng: L.latLng(-5.30, -36.69)})")
    p.click("#ml-concluir")
    janela.esperar("document.getElementById('ml-resumo').textContent.includes('3 poço')")
    assert p.locator("#ml-lista li").count() == 3 and not p.is_disabled("#ml-abrir")
    p.click("#ml-abrir")
    janela.esperar("!document.getElementById('sec-painel').hidden", 30)
    assert p.evaluate("sec.pocos") == ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"]
    assert "linha desenhada no mapa" in p.text_content("#sec-corredor-res")
    assert not janela.erros_js, janela.erros_js


def test_comunidade_painel_biblioteca_compartilhar_comparar_e_refazer(janela, tmp_path):
    from interface_util import foto
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    api = janela.api
    api.definir_autor("Ruan da Silva Nobre", "UFAL")
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-TST-1-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "tst.las")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    rel = "bruto/Potiguar/7-TST-1-RN/Perfil Convencional/tst.las"
    assert api.inventariar_perfil(rel)["ok"]
    assert api.salvar_intervalo(rel, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "1005",
                                      "prof_base": "1035"})["ok"]
    # aba Perfis: calcular e compartilhar
    p.click("#aba-perfis")
    janela.esperar("document.querySelector('#lista-perfis button')")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('.av-curva').length === 8")
    p.fill("#av-gr_limpo", "30")
    p.fill("#av-gr_argila", "120")
    p.click("#av-calcular")
    janela.esperar("!document.getElementById('av-acoes').hidden")
    assert p.is_hidden("#av-compartilhada")
    p.click("#av-compartilhar")
    p.fill("#av-form-compart input", "Açu com Archie, Rw 0,05")
    p.fill("#av-form-compart textarea", "Rw estimado da lama do AGP.")
    p.click("#av-form-compart .btn:not(.secundario)")
    janela.esperar("!document.getElementById('av-compartilhada').hidden")
    assert "Editar" in p.text_content("#av-compartilhar")
    p.locator("#av-acoes").scroll_into_view_if_needed()
    foto(janela, "com_1_perfis_compartilhada")
    # uma segunda avaliação, com outro Rw, fica sem compartilhar
    p.fill("#av-rw", "0,02")
    p.click("#av-calcular")
    janela.esperar("document.getElementById('av-compartilhada').hidden")
    # Comunidade › Biblioteca
    ir(p, "comunidade")
    p.click(".sub-nav [data-com='biblioteca']")
    janela.esperar("document.querySelectorAll('#bib-lista .bib-item').length === 1")
    assert "Açu com Archie" in p.text_content("#bib-lista") and "7-TST-1-RN" in p.text_content("#bib-lista")
    assert p.is_visible("#bib-nao") and p.locator("#bib-nao-lista .bib-item").count() == 1
    p.click("#bib-lista .bib-item .bib-marca")
    p.click("#bib-nao-lista .bib-marca")
    assert not p.is_disabled("#bib-comparar")
    p.click("#bib-comparar")
    janela.esperar("!document.getElementById('bib-comparacao').hidden")
    comp = p.text_content("#bib-comparacao")
    assert "Diferem em: Rw" in comp and "não compartilhada" in comp
    assert p.locator("#bib-comparacao tr.difere").count() >= 1
    foto(janela, "com_2_comparacao")
    # detalhe e "refazer"
    p.click("#bib-lista .bib-item strong")
    janela.esperar("document.getElementById('bib-detalhe').textContent.includes('Rw estimado')")
    assert "mesmo hash" in p.text_content("#bib-detalhe")
    p.locator("#bib-detalhe").scroll_into_view_if_needed()
    foto(janela, "com_3_biblioteca_detalhe")
    p.click("#bib-detalhe >> text=Refazer nos Perfis")
    janela.esperar("!document.getElementById('av-bib-refazer').hidden")
    assert "Ruan da Silva Nobre" in p.text_content("#av-bib-refazer")
    assert p.evaluate("[...document.querySelectorAll('.av-int:checked')].map(c => c.value)")[0].startswith("bib:")
    assert p.input_value("#av-rw") == "0,05"
    p.click("#av-calcular")
    janela.esperar("!document.getElementById('av-comparar-bib').hidden")
    p.locator("#pf-av").scroll_into_view_if_needed()
    foto(janela, "com_4_refazer")
    # Painel
    ir(p, "comunidade")
    p.click(".sub-nav [data-com='painel']")
    janela.esperar("document.querySelectorAll('#pn-kpis .pn-kpi').length === 8")
    assert "Ruan da Silva Nobre" in p.text_content("#pn-contrib")
    assert "1" in p.text_content("#pn-kpis [data-ind='interpretacoes'] strong")
    assert "Têm perfil e nenhum topo" in p.text_content("#pn-ajudar")
    assert p.locator("#pn-atividade svg rect").count() >= 1
    foto(janela, "com_5_painel")
    # Contribuir conta a interpretação; a sub-aba fica lembrada
    p.click(".sub-nav [data-com='contribuir']")
    janela.esperar("document.getElementById('com-local').textContent.includes('interpretação')")
    assert "1 interpretação" in p.text_content("#com-local")
    assert not janela.erros_js, janela.erros_js


def test_referencia_do_gr_na_avaliacao_e_selo_do_download(janela, tmp_path):
    """0.36: onde procurar o GR limpo e o da argila (linhas no GR) e o selo que não saía de "baixando"."""
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    api = janela.api
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-TST-1-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "tst.las")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    rel = "bruto/Potiguar/7-TST-1-RN/Perfil Convencional/tst.las"
    assert api.salvar_intervalo(rel, {"tipo": "intervalo_alvo", "nome": "Arenito", "prof_topo": "1012",
                                      "prof_base": "1018"})["ok"]
    p.click("#aba-perfis")
    janela.esperar("document.querySelector('#lista-perfis button')")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('.av-curva').length === 8", 30)
    assert p.input_value("#av-gr_referencia") == "arquivo" and p.is_hidden("#av-gr-janela")
    p.select_option("#av-gr_referencia", "janela")
    assert not p.is_hidden("#av-gr-janela")
    p.fill("#av-gr_ref_topo", "1005")
    p.fill("#av-gr_ref_base", "1025")
    p.click("#av-calcular")
    janela.esperar("document.querySelector('#av-resultado table') !== null", 30)
    texto = p.text_content("#av-resultado")
    assert "GR limpo 30 API" in texto and "GR da argila 120 API" in texto and "1005,0–1025,0 m" in texto
    assert p.evaluate("pf.grRef.limpo") == 30 and p.evaluate("pf.grRef.topo") == 1005
    # só o intervalo de arenito: sem folhelho na janela, o cálculo explica por quê
    p.select_option("#av-gr_referencia", "intervalos")
    p.click("#av-calcular")
    janela.esperar("historicoStatus.some((m) => m.texto.includes('precisa ser maior'))")
    # selo do download: "baixando" vira "baixado" quando o motor avisa o fim
    p.evaluate("""() => {
      const li = document.createElement('li'), cb = document.createElement('input'), selo = document.createElement('span');
      cb.type = 'checkbox'; li.append(cb, selo); document.body.appendChild(li);
      arquivosGaveta.set('/POCO/x/tst.las', { no: { nome: 'tst.las', tamanho: 10 }, cb, linha: li, selo });
      window.__item = arquivosGaveta.get('/POCO/x/tst.las'); }""")
    api._emitir_download({"tipo": "inicio", "caminho": "/POCO/x/tst.las", "nome": "tst.las", "poco": "7-TST-1-RN",
                          "indice": 1, "total": 1, "tamanho": 10})
    janela.esperar("__item.selo.textContent === 'baixando'")
    api._emitir_download({"tipo": "fim", "caminho": "/POCO/x/tst.las", "status": "baixado", "bytes": 10,
                          "bacia": "Potiguar", "poco": "7-TST-1-RN", "arquivo_local": str(pasta / "tst.las")})
    janela.esperar("__item.selo.textContent === 'baixado'")
    assert p.evaluate("__item.no.tipo") == "perfil" and p.evaluate("__item.cb.disabled")
    assert not janela.erros_js, janela.erros_js


def test_formularios_da_anp_na_ficha_nos_perfis_e_na_avaliacao(janela, tmp_path):
    """0.37: RFP, RFCP e Perfuração lidos ao abrir o projeto aparecem na ficha, viram intervalos
    candidatos e referência de temperatura/fluido na avaliação."""
    import rfp_util as u
    from interface_util import foto
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-SIAPP-1-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    for k, nome in enumerate(("RFP", "RFCP", "Perfuracao"), 1):
        u.gerar(str(pasta / f"1-SIAPP-1-RN_CDPE_{k}_{nome}.pdf"), getattr(u, nome.upper()))
    perfis = pasta.parent / "Perfil Convencional"
    perfis.mkdir()
    las_reservatorio(perfis / "siapp.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.evaluate("abrirFicha('1-SIAPP-1-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Formulários da ANP')")
    corpo = p.text_content("#fi-dados-poco")
    assert "Relatório Final de Poço" in corpo and "Relatório Final de Completação" in corpo
    assert "Prof. final (sondador)1.850 m" in corpo and "FM JANDAÍRA" in corpo
    assert "FM AÇU780801,5-689,3+21,5" in corpo                       # prevista × constatada
    assert "141,7 kgf/cm² (2.015 psi)" in corpo and "158 °F (70 °C)" in corpo
    assert "canhoneado1.396–1.401FM. AÇUHSD · 6 tiros/pé" in corpo and "CATIÔNICO9,6" in corpo
    assert "Sigla do Poço na base do E&P: 1-ABC-1-RN" in corpo
    p.click("#aba-mapa")
    p.locator("#fi-dados-poco h3").scroll_into_view_if_needed()
    foto(janela, "dp_1_ficha")
    p.locator("#fi-dados-poco .dp-bloco").first.scroll_into_view_if_needed()
    foto(janela, "dp_1b_ficha_tabelas")
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length >= 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('.av-int').length >= 3", 30)
    ints = p.text_content("#av-intervalos")
    assert "Dos formulários da ANP" in ints and "Canhoneado · FM. AÇU · 1.396–1.401 m" in ints
    assert "Teste TFR · ÓLEO" in ints
    lama = p.text_content("#av-lama")
    assert "No RFP: 80 °F lida a 0 m (origem P) · 158 °F extrapolada a 1.850 m (perfilagem final)" in lama
    assert "fase 2 (12 1/4\") catiônico 9,6 lb/gal até 1.850 m" in lama
    assert p.evaluate("pf.form.canhoneados.length") == 1 and p.evaluate("pf.form.topos.length") == 4
    foto(janela, "dp_2_avaliacao")
    assert not janela.erros_js, janela.erros_js


def test_pressoes_gradiente_contato_e_tfr_na_ficha(janela, tmp_path):
    """0.38: pontos do teste a cabo, do RFP e do TFR no gráfico; gradiente de dois grupos com o
    contato; curva da estação e do manômetro; relatório do TFR."""
    import pressoes_util as pu
    import rfp_util as u
    from interface_util import foto
    from test_pressoes import _wft
    p = janela.page
    abrir_projeto(janela)
    base = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-SIAPP-1-RN"
    (base / "Pasta de Poco").mkdir(parents=True)
    u.gerar(str(base / "Pasta de Poco" / "1-SIAPP-1-RN_CDPE_7_RFP.pdf"), u.RFP)
    u.gerar(str(base / "Pasta de Poco" / "1-SIAPP-1-RN_CDPE_3_ND_1.pdf"), u.ND)
    (base / "Teste de Formacao").mkdir()
    (base / "Teste de Formacao" / "1SIAPP1RN_TFR.zip").write_bytes(pu.tfr_zip())
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    _wft(janela.api._banco, "bruto/Potiguar/1-SIAPP-1-RN/Teste de Formacao a Cabo/1-siapp-1-rn_sft.dlis")
    p.click("#aba-mapa")
    p.evaluate("abrirFicha('1-SIAPP-1-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Pressões × profundidade')")
    assert p.locator(".dp-pressoes svg circle[fill]").count() == 4            # estações do teste a cabo
    corpo = p.text_content("#fi-dados-poco")
    assert "Teste de formação TFR-01 — relatório" in corpo and "525 mD" in corpo and "-1,5" in corpo
    assert "Relatório de Descoberta" in corpo and "Aguardando a perfilagem final." in corpo
    assert "Lama na perfilagem: 10 lb/gal (base agua)" in corpo
    sel = p.locator(".dp-tab-pressoes select")
    origens = p.locator(".dp-tab-pressoes tr td:nth-child(5)").all_text_contents()
    cabo = [i for i, o in enumerate(origens) if o == "teste a cabo"]
    for i in cabo[:2]:
        sel.nth(i).select_option("A")
    for i in cabo[2:]:
        sel.nth(i).select_option("B")
    p.click("text=Calcular gradiente")
    janela.esperar("document.querySelector('.dp-grad-res') && document.querySelector('.dp-grad-res').textContent.includes('Grupo B')")
    res = p.text_content(".dp-grad-res")
    assert "Grupo A:" in res and "compatível com" in res and "contato provável" in res
    assert p.locator(".dp-reta").count() == 2 and p.locator(".dp-contato").count() == 1
    p.locator(".dp-tab-pressoes button", has_text="curva").first.click()
    janela.esperar("document.querySelector('.dp-serie-box polyline') !== null")
    assert "estação 1 · 1500.0 m" in p.text_content(".dp-serie-box")
    p.locator("#fi-dados-poco .dp-pressoes svg").first.scroll_into_view_if_needed()
    foto(janela, "pr_1_gradiente")
    p.locator(".dp-tfr button", has_text="11111").click()
    janela.esperar("document.querySelector('.dp-tfr .dp-serie-box polyline') !== null")
    assert "manômetro 11111" in p.text_content(".dp-tfr .dp-serie-box")
    p.locator(".dp-tfr").scroll_into_view_if_needed()
    foto(janela, "pr_2_tfr")
    assert not janela.erros_js, janela.erros_js


def test_pvt_na_ficha(janela, tmp_path):
    """0.39: análise PVT (liberação diferencial e flash) na ficha do poço."""
    from interface_util import foto
    from test_pvt import diferencial, flash, xlsx
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-SIAPP-1-RN" / "Dados De Rochas e Fluidos" / "PVT"
    pasta.mkdir(parents=True)
    xlsx(str(pasta / "1-SIAPP-1-RN-PVT Liberação Diferencial .xlsx"), diferencial())
    xlsx(str(pasta / "1-SIAPP-1-RN-PVT Liberação Flash .xlsx"), flash())
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-mapa")
    p.evaluate("abrirFicha('1-SIAPP-1-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Análise PVT')")
    corpo = p.text_content("#fi-dados-poco")
    assert "Pressão de saturação120 kgf/cm² (117,7 bar, 1.707 psi)" in corpo
    assert "Bo 1,22 · Rs 70 m³/m³" in corpo and "31,2 °API" in corpo
    assert p.locator(".dp-pvt svg polyline").count() == 3 and p.locator(".dp-tab-pvt tr").count() == 7
    assert "Composição do fluido — liberação flash (6)" in corpo
    p.locator(".dp-pvt").scroll_into_view_if_needed()
    foto(janela, "pvt_1_ficha")
    assert not janela.erros_js, janela.erros_js


def test_pag_na_ficha_e_litologia_da_calha_nos_perfis(janela, tmp_path):
    """0.40: PAG (curvas e descrição de calha) na ficha; sem AGP, a calha faz a trilha de litologia."""
    import test_pag as tp
    from interface_util import foto
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    raiz = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / tp.POCO
    pag_dir = raiz / "Perfil de Acompanhamento Geologico"
    pag_dir.mkdir(parents=True)
    tp.las_pag(pag_dir / f"{tp.POCO}_PAG_curvas.las")
    # descrição de calha no intervalo do perfil sintético (1000–1040 m)
    linhas = tp.linhas_dac()[:3] + [tp._linha(str(1000 + 3 * k), "ARN" if 4 <= k < 10 else "FLH", "100",
                                              formacao="Acu" if k >= 4 else "Jandaira") for k in range(14)]
    tp.xlsx(str(pag_dir / f"{tp.POCO}_PAG_DAC.xlsx"), linhas)
    (raiz / "Perfil Convencional").mkdir()
    las_reservatorio(raiz / "Perfil Convencional" / "siapp.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.evaluate(f"abrirFicha('{tp.POCO}')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Gás na lama (PAG)')")
    corpo = p.text_content("#fi-dados-poco")
    assert "Topos pela descrição de calha (PAG)" in corpo and "Jandaira1.000" in corpo and "Acu1.0121.009" in corpo
    assert "100–1108.000" in corpo and "8,0 × o fundo" in corpo and "Salinidade da lama (PAG)" in corpo
    assert "Litologia da calha (PAG)" in corpo
    p.click("#aba-mapa")
    p.locator("#fi-dados-poco h3").scroll_into_view_if_needed()
    foto(janela, "pag_1_ficha")
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length >= 2")
    p.locator("#lista-perfis button", has_text="siapp.las").click()
    janela.esperar("document.querySelectorAll('.pf-trilha-lito canvas').length == 1", 30)
    assert "Litol. (calha)" in p.text_content(".pf-trilha-lito")
    janela.esperar("!document.getElementById('pf-lito-legenda').hidden")
    assert "Litologia (calha)" in p.text_content("#pf-lito-legenda")
    janela.esperar("document.querySelectorAll('.av-int').length >= 1", 30)
    assert "Gás na lama · 8,0 × o fundo" in p.text_content("#av-intervalos")
    assert "Salinidade da lama (PAG): 150.000 ppm a 50 m · 200.000 ppm a 150 m" in p.text_content("#av-lama")
    foto(janela, "pag_2_perfis")
    assert not janela.erros_js, janela.erros_js


def test_perfil_processado_comparado_e_pesquisa_no_levantamento(janela, tmp_path):
    """0.41: com o perfil processado da operadora aberto, a avaliação mostra a comparação; o levantamento
    lista os poços com curvas interpretadas."""
    import test_operador as to
    from interface_util import foto
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    base = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / to.POCO
    (base / "Perfil Convencional").mkdir(parents=True)
    (base / "Perfil Digital Processado").mkdir()
    las_reservatorio(base / "Perfil Convencional" / "tst.las")
    to.las_operador(base / "Perfil Digital Processado" / "tst_adic.las")
    api = janela.api
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    assert api.inventariar_perfil(to.REL_OP)["ok"] and api.inventariar_perfil(to.REL)["ok"]
    api.salvar_intervalo(to.REL, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "1010", "prof_base": "1020"})
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length >= 2")
    p.locator("#lista-perfis button", has_text="tst.las").first.click()
    janela.esperar("document.querySelectorAll('.av-curva').length === 8", 30)
    p.fill("#av-gr_limpo", "30")
    p.fill("#av-gr_argila", "120")
    p.fill("#av-rw", "0,05")
    p.click("#av-calcular")
    janela.esperar("document.querySelector('#av-operador table') !== null", 30)
    op = p.text_content("#av-operador")
    assert "Comparação com a interpretação da operadora" in op and "PHIE (tst_adic.las)" in op
    assert "0,21" in op and "0,1" in op
    p.locator("#av-operador").scroll_into_view_if_needed()
    foto(janela, "op_1_comparacao")
    # levantamento: a pesquisa dos poços com perfil processado
    to._acervo(api._banco)
    api._banco.definir_meta("mnemonicos_versao", "2")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    ir(p, "dados", "levantamento")
    p.evaluate("desenharResumoLevantamento(Object.assign({bacia: 'Potiguar', pocos: 3, situacoes: {}, familias: {}}, "
               "{pocos_com_interpretacao: 2}))")
    p.click("#lv-processados")
    janela.esperar("document.querySelectorAll('.lv-processados tr').length === 3")
    assert "1-A-1-RN" in p.text_content(".lv-processados") and "PHIE, SW, VSH" in p.text_content(".lv-processados")
    assert not janela.erros_js, janela.erros_js


def test_checkshot_na_ficha_e_twt_nos_perfis(janela, tmp_path):
    """0.42: tabela tempo × profundidade do SEG-Y da sísmica de poço na ficha; TWT na leitura do mouse."""
    import test_checkshot as tc
    from interface_util import foto
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    raiz = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / tc.POCO
    (raiz / "Sismica de Poco").mkdir(parents=True)
    tc.vertical(str(raiz / "Sismica de Poco" / f"{tc.POCO}_asr-3_stack.sgy"))
    (raiz / "Perfil Convencional").mkdir()
    las_reservatorio(raiz / "Perfil Convencional" / "siapp.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.evaluate(f"abrirFicha('{tc.POCO}')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('tempo × profundidade (checkshot)')")
    corpo = p.text_content("#fi-dados-poco")
    assert "1.4001.4000,61.2002.3334.000" in corpo                         # MD, TVDSD, Tv, TWT, Vméd, Vint
    assert p.locator("#fi-dados-poco .dp-checkshot svg polyline").count() == 2
    p.click("#aba-mapa")
    p.locator("#fi-dados-poco .dp-checkshot").scroll_into_view_if_needed()
    foto(janela, "ck_1_ficha")
    p.locator("#fi-dados-poco .dp-checkshot button").click()
    janela.esperar("historicoStatus.some((m) => m.texto.includes('checkshot_tempo_profundidade.csv'))")
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length >= 1")
    p.click("#lista-perfis button")
    janela.esperar("pf.form && pf.form.checkshot && pf.form.checkshot.length === 3", 30)
    assert p.evaluate("Math.round(twtNaProf(1020))") == 1010 and p.evaluate("twtNaProf(50)") is None
    assert not janela.erros_js, janela.erros_js


def test_geoquimica_e_apelidos_com_origem_na_ficha(janela, tmp_path):
    """0.43: isótopos do gás na ficha, aviso do sinal duplo e de onde veio cada grafia do poço."""
    import test_geoquimica as tg
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / tg.PASTA
    pasta.mkdir(parents=True)
    tg.xml_geoquimica(str(pasta / "Envio de Resultados_ANP_d13C.xml"))
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.evaluate(f"abrirFicha('{tg.POCO}')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('isótopos de carbono do gás')")
    corpo = p.text_content("#fi-dados-poco")
    assert "-47,39-31,61-27,38gás termogênico; ordem normal" in corpo and "sinal duplo" in corpo
    assert "Geoquímica de rocha (2)" in corpo
    assert "(geoquímica)" in p.text_content("#fi-apelidos")
    assert not janela.erros_js, janela.erros_js


def test_dados_consolidados(janela, tmp_path):
    """0.44: Dados › Dados consolidados — o projeto e um poço, também a partir da ficha."""
    import rfp_util as u
    from interface_util import foto
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-SIAPP-1-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    u.gerar(str(pasta / "1-SIAPP-1-RN_CDPE_7_RFP.pdf"), u.RFP)
    u.gerar(str(pasta / "1-SIAPP-1-RN_CDPE_8_RFCP_1.pdf"), u.RFCP)
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    ir(p, "dados", "consolidado")
    janela.esperar("document.querySelectorAll('#co-resultado .co-tabela tr').length > 10")
    assert "RFP (topos constatados): 1 · 4" in p.text_content("#co-resultado")
    assert "Seção estratigráfica e bloco 3D: o topo efetivo" in p.text_content("#co-resultado")
    foto(janela, "co_1_projeto")
    p.fill("#co-poco", "1-ABC-1-RN")
    p.click("#co-ver")
    janela.esperar("document.getElementById('co-resultado').textContent.includes('Poço 1-SIAPP-1-RN')")
    assert "Canhoneados (RFCP)1.396–1.401FM. AÇU" in p.text_content("#co-resultado")
    foto(janela, "co_2_poco")
    # da ficha do poço
    p.evaluate("abrirFicha('1-SIAPP-1-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('Formulários da ANP')")
    p.evaluate("limpar($('co-resultado'))")
    p.click("#aba-mapa")
    p.locator("#fi-corpo button", has_text="Dados consolidados").click()
    janela.esperar("document.getElementById('co-resultado').textContent.includes('Poço 1-SIAPP-1-RN')")
    assert p.is_visible("#co-resultado")
    assert not janela.erros_js, janela.erros_js


def test_topos_comparar_e_escolher_na_ficha(janela, tmp_path):
    """0.45: a ficha mostra o topo de cada fonte, a diferença e deixa escolher; a ordem do projeto se edita."""
    import rfp_util as u
    from interface_util import foto
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-SIAPP-1-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    u.gerar(str(pasta / "1-SIAPP-1-RN_CDPE_7_RFP.pdf"), u.RFP)
    api = janela.api
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    api._banco.salvar_fato({"poco_id": "1-SIAPP-1-RN", "tipo": "topo_formacao", "nome": "Açu", "prof_topo": 812.0})
    p.evaluate("abrirFicha('1-SIAPP-1-RN')")
    janela.esperar("document.getElementById('fi-topos') !== null")
    t = p.text_content("#fi-topos")
    assert "TranscritoRFP" in t.replace(" ", "") and "10,5" in t           # Açu: 812 × 801,5
    assert p.locator("#fi-topos td.tp-diverge").count() == 1
    p.click("#aba-mapa")
    sel = p.locator("#fi-topos select[data-chave='ACU']")
    assert sel.input_value() == "padrao"
    sel.select_option("rfp")
    janela.esperar("document.querySelector(\"#fi-topos select[data-chave='ACU']\").value === 'rfp'")
    linha = p.locator("#fi-topos tr", has=p.locator("select[data-chave='ACU']"))
    assert linha.locator("td.tp-usada").text_content() == "801,5"
    p.locator("#fi-topos").scroll_into_view_if_needed()
    foto(janela, "tp_1_ficha")
    # a ordem do projeto: desde a 0.63, em Configurações › Fontes e prioridade (Dados consolidados mostra o resumo)
    ir(p, "dados", "consolidado")
    janela.esperar("document.getElementById('co-precedencia').textContent.includes('1. AGP')")
    p.locator("#co-precedencia button", has_text="Fontes e prioridade").click()
    janela.esperar("document.querySelectorAll('#fp-topos li').length === 4")
    p.locator("#fp-topos li").nth(2).locator("button", has_text="↑").click()       # RFP sobe (grava na hora)
    janela.esperar("historicoStatus.some((m) => m.texto.includes('Fontes de topo: AGP → RFP'))")
    assert api.topos_precedencia()["ordem"] == ["agp", "rfp", "transcrito", "calha"]
    janela.esperar("document.getElementById('co-precedencia').textContent.includes('2. RFP')")
    assert not janela.erros_js, janela.erros_js


def test_procurar_por_tipo_de_dado_nada_marcado_e_busca_no_levantamento(janela, tmp_path):
    """0.49: Dados › Procurar por tipo de dado: os tipos vêm do levantamento, nada vem marcado, a busca lista os
    poços e os arquivos só dos tipos pedidos."""
    import test_tipos_dado as tt
    p = janela.page
    abrir_projeto(janela)
    with janela.api._banco.conexao() as c:
        for bacia, cam, nome, cat in tt.POCOS:
            c.execute("INSERT INTO acervo_pocos(bacia, caminho, nome_pasta, poco_id, categoria) VALUES (?,?,?,?,?)",
                      (bacia, cam, nome, nome, cat))
        for i, pasta, nome, tam in tt.ARQS:
            bacia, cam, _, _ = tt.POCOS[i]
            c.execute("INSERT INTO acervo_arquivos(bacia, caminho, poco_caminho, nome, pasta, tamanho) VALUES (?,?,?,?,?,?)",
                      (bacia, f"{cam}{pasta}/{nome}", cam, nome, pasta, tam))
    ir(p, "dados", "tipos")
    janela.esperar("document.querySelectorAll('#tp-tipos input[type=checkbox]').length > 5")
    assert p.evaluate("[...document.querySelectorAll('#tp-tipos input[type=checkbox]')].every((c) => !c.checked)")
    txt = p.text_content("#tp-tipos")
    assert "Petrofísica básica" in txt and "4 poço(s)" in txt and "levantado(s)" in txt
    p.click("#tp-procurar")
    assert "Marque pelo menos um tipo" in janela.status()
    p.locator("#tp-tipos label", has_text="Petrofísica básica").locator("input").check()
    p.locator("#tp-tipos label", has_text="PVT").locator("input").check()
    p.select_option("#tp-modo", "algum")
    p.click("#tp-procurar")
    janela.esperar("document.querySelectorAll('#tp-resultado tr').length === 5")
    assert "4 poço(s) com Petrofísica básica ou PVT" in p.text_content("#tp-resultado")
    assert p.evaluate("[...document.querySelectorAll('#tp-resultado td input[type=checkbox]')].every((c) => !c.checked)")
    assert "nenhum marcado" in p.text_content("#tp-resultado")
    p.locator("#tp-resultado td input[type=checkbox]").first.check()
    janela.esperar("document.getElementById('tp-resultado').textContent.includes('1 marcado')")
    p.click("#tp-resultado button:has-text(\"Baixar os arquivos dos marcados\")")
    assert "Confirmar e baixar" in p.text_content("#tp-resultado")
    p.click("#tp-resultado button:has-text(\"Cancelar\")")
    assert "Confirmar e baixar" not in p.text_content("#tp-resultado")
    p.select_option("#tp-bacia", "Alagoas")
    p.select_option("#tp-modo", "todos")
    janela.esperar("document.querySelector('#tp-tipos').textContent.includes('1 poço(s) levantado(s)')")


def test_dados_destes_pocos_vindo_da_secao_restringe_a_busca(janela):
    """0.51: o botão da Seção abre a busca por tipo restrita aos poços da seção; a restrição pode ser tirada."""
    import test_tipos_dado as tt
    p = janela.page
    abrir_projeto(janela)
    with janela.api._banco.conexao() as c:
        for bacia, cam, nome, cat in tt.POCOS:
            c.execute("INSERT INTO acervo_pocos(bacia, caminho, nome_pasta, poco_id, categoria) VALUES (?,?,?,?,?)",
                      (bacia, cam, nome, nome, cat))
        for i, pasta, nome, tam in tt.ARQS:
            bacia, cam, _, _ = tt.POCOS[i]
            c.execute("INSERT INTO acervo_arquivos(bacia, caminho, poco_caminho, nome, pasta, tamanho) VALUES (?,?,?,?,?,?)",
                      (bacia, f"{cam}{pasta}/{nome}", cam, nome, pasta, tam))
    p.evaluate("sec.pocos = ['1-AAA-1-RN', '1-BBB-2-RN']")
    ir(p, "interp", "secao")
    p.click("#sec-dados")
    janela.esperar("document.getElementById('tp-restricao').textContent.includes('2 poço(s) da seção')")
    janela.esperar("document.getElementById('tp-tipos').textContent.includes('2 poço(s) levantado(s)')")
    p.locator("#tp-tipos label", has_text="Petrofísica básica").locator("input").check()
    p.click("#tp-procurar")
    janela.esperar("document.querySelectorAll('#tp-resultado tr').length === 3")       # cabeçalho + 2 poços
    p.click("#tp-restricao .x")
    janela.esperar("document.getElementById('tp-tipos').textContent.includes('4 poço(s) levantado(s)')")
    p.evaluate("sec.pocos = []")
    ir(p, "interp", "secao")
    p.click("#sec-dados")
    assert "Não há poços para procurar" in janela.status()


def test_viabilidade_052_campos_novos_e_botoes(janela):
    """0.52: diâmetro pela vazão, correção pela inflação, restrições ambientais e importação das terras indígenas."""
    p = janela.page
    abrir_projeto(janela)
    assert p.evaluate("['vb-diametro-modo', 'vb-inflacao', 'vb-restricoes', 'cm-importar-ti'].every((i) => document.getElementById(i))")
    lido = p.evaluate("""() => {
      document.getElementById('vb-diametro-modo').value = 'vazao';
      document.getElementById('vb-inflacao').value = 'ipca';
      document.querySelector('[data-vb=vazao_sm3_d]').value = '2000000';
      return lerParametrosVb();
    }""")
    assert lido["diametro_modo"] == "vazao" and lido["corrigir_inflacao"] == "ipca" and lido["vazao_sm3_d"] == "2000000"
    assert p.evaluate("document.getElementById('vb-restricoes').hidden")                # só aparece depois de medir


def test_arquivos_baixados_arvore_filtros_e_apagar_para_a_lixeira(janela, monkeypatch):
    """0.54: árvore bacia › poço › pasta, lista com situação, filtros, programas sem 'Abrir', apagar com confirmação."""
    import test_arquivos_baixados as tab
    from motor import arquivos_baixados as mab
    p = janela.page
    abrir_projeto(janela)
    raiz = tab.montar(janela.api)
    ir(p, "dados", "baixados")
    janela.esperar("document.querySelectorAll('#ab-lista tr').length > 5")
    assert "arquivo(s)" in p.text_content("#ab-resumo")
    assert p.locator("#ab-arvore .ab-rotulo", has_text="Potiguar").count() == 1
    p.locator("#ab-arvore .ab-rotulo", has_text="Potiguar").click()
    janela.esperar("document.querySelectorAll('#ab-arvore .ab-rotulo').length >= 3")         # a bacia abriu: aparece o poço
    p.locator("#ab-arvore .ab-rotulo", has_text=tab.POCO).click()
    janela.esperar("document.querySelectorAll('#ab-arvore .ab-rotulo').length > 4")          # e as pastas do poço
    p.locator("#ab-arvore .ab-rotulo", has_text="PETROFISICABASICA").click()
    janela.esperar("document.querySelectorAll('#ab-lista tr').length === 3")                 # cabeçalho + 2 planilhas
    assert "Petrofísica de testemunho" in p.text_content("#ab-lista")
    # filtros
    p.locator("#ab-arvore .ab-rotulo", has_text="Todos os arquivos").click()
    p.select_option("#ab-estado", "nao_lidos")
    janela.esperar("!document.getElementById('ab-lista').textContent.includes('COREGAMA')")
    assert "notas.txt" in p.text_content("#ab-lista")
    p.select_option("#ab-estado", "")
    p.fill("#ab-busca", "instalar")
    janela.esperar("document.querySelectorAll('#ab-lista tr').length === 2")
    abrir = p.locator("#ab-lista tr", has_text="instalar.exe").locator("button", has_text="Abrir")
    assert abrir.is_disabled()                                                              # programa: nunca abre pelo SIAPP
    # apagar: confirmação mostra o impacto; cancelar não apaga; confirmar manda para a Lixeira
    enviados = []
    monkeypatch.setattr(mab, "enviar_para_lixeira", lambda c: enviados.append(c) or os.remove(c) or "lixeira")
    p.fill("#ab-busca", "notas.txt")
    janela.esperar("document.querySelectorAll('#ab-lista tr').length === 2")
    p.locator("#ab-lista tr", has_text="notas.txt").locator("button", has_text="Apagar").dispatch_event("click")      # a linha é redesenhada no clique: sem reclique do Playwright
    janela.esperar("document.querySelector('.ab-confirmar') && document.querySelector('.ab-confirmar').textContent.includes('Lixeira')")
    assert "Dá para restaurar" in p.text_content(".ab-confirmar")
    p.click(".ab-confirmar button:has-text('Cancelar')")                                    # clique de verdade, logo depois de digitar
    janela.esperar("!document.querySelector('.ab-confirmar')")
    assert not enviados and os.path.exists(os.path.join(raiz, *tab.BASE.split("/"), "Pasta de Poco", "notas.txt"))
    p.locator("#ab-lista tr", has_text="notas.txt").locator("button", has_text="Apagar").dispatch_event("click")      # a linha é redesenhada no clique: sem reclique do Playwright
    janela.esperar("document.querySelector('.ab-confirmar button.perigo')")
    p.click(".ab-confirmar button.perigo")
    janela.esperar("!document.getElementById('ab-lista').textContent.includes('notas.txt')")
    assert len(enviados) == 1 and enviados[0].endswith("notas.txt") and not os.path.exists(enviados[0])


def test_bloco_zonas_produtoras_reservatorios_ajustes_e_tabela(janela, tmp_path):
    """0.55: nível "zonas produtoras": prévia dos intervalos, escolher um só reservatório, ignorar intervalo, importar a tabela
    e montar o bloco com topo e base de cada reservatório."""
    import test_zonas as tz
    p = janela.page
    abrir_projeto(janela)
    tz.popular(janela.api._banco)
    ir(p, "interp", "bloco")
    p.select_option("#bl-nivel", "zonas")
    assert p.is_visible("#bl-zonas") and "Tabela sua" in p.text_content("#bz-fontes")
    ids = [pid for pid, _, _ in tz.POCOS]
    p.evaluate("(ids) => { bl.pocos = ids; desenharListaBloco(); }", ids)
    p.click("#bz-previa")
    janela.esperar("document.querySelectorAll('#bz-resultado table').length >= 2", 30)
    txt = p.text_content("#bz-resultado")
    assert "Reservatório 1" in txt and "Reservatório 2" in txt and "intervalo(s) candidato(s) em 6 poço(s)" in txt
    # ignorar o canhoneado do primeiro poço: a prévia refaz e mostra "ignorado"
    linha = p.locator("#bz-resultado .bz-tabela tr", has_text="1-ZZ-1-RN").filter(has_text="Canhoneados").first
    linha.locator("select").select_option("ignorar")
    janela.esperar("document.querySelector('#bz-resultado .bz-tabela').textContent.includes('ignorado')", 30)
    # só o reservatório raso
    p.locator("#bz-resultado table").first.locator("input[type=checkbox]").nth(1).uncheck()
    p.click("#bl-montar")
    janela.esperar("!document.getElementById('bl-painel').hidden", 60)
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 60)
    chaves = p.evaluate("bl.modelo.legenda.map((u) => u.chave)")
    assert chaves == ["ZP1", "ZP1_B"] and p.evaluate("bl.modelo.parametros.nivel") == "zonas"
    assert "Reservatório 1" in p.text_content("#bl-unidades")
    # a tabela sua: importar, usar como fonte e comparar
    tab = tmp_path / "manual.csv"
    linhas = ["Poço;Topo;Base;Reservatório"] + [f"{pid};{str(round(tz.topo_raso(pid) + 1, 2)).replace('.', ',')};"
                                                  f"{str(round(tz.topo_raso(pid) + 13, 2)).replace('.', ',')};Raso" for pid in ids]
    tab.write_text("\n".join(linhas), encoding="latin-1")
    janela.api._janela.escolha = (str(tab),)
    p.click("#bz-importar")
    janela.esperar("document.getElementById('bz-tabela-info').textContent.includes('manual.csv')", 30)
    assert "6 linha(s)" in p.text_content("#bz-tabela-info") and p.is_visible("#bz-apagar-tabela")
    p.click("#bz-previa")
    janela.esperar("document.querySelector('#bz-resultado').textContent.includes('Sua tabela × o que o SIAPP escolheu')", 30)
    assert "comparado" in p.text_content("#bz-resultado")
    p.click("#bz-apagar-tabela")
    janela.esperar("document.getElementById('bz-tabela-info').textContent.includes('Nenhuma tabela')", 30)
    assert not janela.erros_js, janela.erros_js


def test_bloco_escolher_varias_bacias_juntas(janela):
    """0.56: no bloco regional dá para marcar mais de uma bacia (ex.: Alagoas e Sergipe) e trazer os poços de todas."""
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-AL", -5.00, -37.00), ("1-AA-2-AL", -5.00, -36.96), ("1-AA-3-SE", -5.04, -37.00),
                        ("1-AA-4-SE", -5.04, -36.96), ("1-AA-5-SE", -5.02, -36.98)]:
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300), ("F", "ACU", 300, 700)], prof_final=900)
    with b.conexao() as c:
        c.execute("UPDATE agp_unidades SET bacia = 'Alagoas' WHERE poco_id LIKE '%-AL'")
        c.execute("UPDATE agp_unidades SET bacia = 'Sergipe' WHERE poco_id LIKE '%-SE'")
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    p.select_option("#bl-modo", "todos")
    janela.esperar("document.querySelectorAll('#bl-bacias input').length === 2")
    assert "Sergipe (3 poços)" in p.text_content("#bl-bacias") and "Alagoas (2 poços)" in p.text_content("#bl-bacias")
    p.click("#bl-selecionar")
    assert "Marque ao menos uma bacia" in janela.status()                                       # nada marcado: avisa
    p.locator("#bl-bacias label", has_text="Alagoas").locator("input").check()
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '2'")
    p.locator("#bl-bacias label", has_text="Sergipe").locator("input").check()
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")                       # as duas juntas
    assert not janela.erros_js, janela.erros_js


def test_bloco_mapa_2d_com_curvas_de_nivel(janela, tmp_path):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0
        poco(b, pid, la, lo, 50.0, [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)],
             prof_final=900)
    ir(p, "interp", "bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('5 poço')")
    p.click("#bl-selecionar")
    janela.esperar("document.getElementById('bl-n').textContent === '5'")
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 30)
    aba_bloco(p, "mapa2d")            # abre o mapa 2D sozinho
    janela.esperar("document.querySelector('#bl-m2d-fig svg') !== null", 30)
    assert p.locator("#bl-m2d-mapa option").count() >= 2 and p.locator("#bl-m2d-fig circle").count() == 5
    assert "curvas a cada" in p.inner_text("#bl-m2d-info")
    p.fill("#bl-m2d-int", "20")
    p.dispatch_event("#bl-m2d-int", "change")
    janela.esperar("document.getElementById('bl-m2d-info').textContent.includes('a cada 20')", 30)
    # 0.64: zoom, arraste e leitura do valor sob o mouse
    p.locator("#bl-m2d-vista").scroll_into_view_if_needed()
    s0 = p.evaluate("bl.m2d.vista.s")
    p.click("#bl-m2d-mais")
    assert p.evaluate("bl.m2d.vista.s") > s0 * 1.4
    p.click("#bl-m2d-ajustar")
    assert abs(p.evaluate("bl.m2d.vista.s") - s0) < 1e-6
    caixa = p.locator("#bl-m2d-vista").bounding_box()
    p.mouse.move(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
    janela.esperar("document.getElementById('bl-m2d-leitura').textContent.includes('Leste')")
    assert " m · Norte " in p.text_content("#bl-m2d-leitura")
    tx0 = p.evaluate("bl.m2d.vista.tx")
    p.mouse.down(); p.mouse.move(caixa["x"] + caixa["width"] / 2 + 60, caixa["y"] + caixa["height"] / 2); p.mouse.up()
    assert abs(p.evaluate("bl.m2d.vista.tx") - tx0 - 60) < 2
    primeiro = p.input_value("#bl-m2d-mapa")
    p.click("#bl-m2d-prox")
    janela.esperar(f"document.getElementById('bl-m2d-mapa').value !== '{primeiro}'")
    p.click("#bl-m2d-ant")
    janela.esperar(f"document.getElementById('bl-m2d-mapa').value === '{primeiro}'")
    p.locator(".bl-m2d-opcoes > summary").click()                               # opções menos usadas, recolhidas
    p.uncheck("#bl-m2d-pocos")
    janela.esperar("document.querySelectorAll('#bl-m2d-fig circle').length === 0", 30)
    pasta = tmp_path / "ambiente_teste" / "exportacoes" / "blocos"
    for f in ("svg", "png", "pdf"):
        p.click(f"#bl-m2d-{f}")
        janela.esperar(f"document.getElementById('bl-exportado').textContent.includes('_mapa_') && "
                       f"document.getElementById('bl-exportado').textContent.includes('.{f}')", 60)
        assert any(pasta.glob(f"*_mapa_*.{f}"))
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.57: interface
def test_abas_pelo_fluxo_menus_e_ajuda(janela):
    p = janela.page
    rotulos = [t.strip() for t in p.locator("#abas > .aba").all_text_contents()]
    assert rotulos == ["Início", "1Acervo", "2Documentos", "3Perfis", "4Poços", "5Correlação", "6Modelo 3D",
                       "Comunidade"]                     # 1.3: a Comunidade saiu do Mais
    assert p.is_hidden("#aba-viab") and p.is_hidden("#btn-dividir") and p.is_hidden("#versao")
    abrir_projeto(janela)
    janela.esperar("document.getElementById('projeto-nome').textContent === 'Projeto principal'")
    # Correlação e Modelo 3D: abas próprias, cada uma marcada sozinha
    ir(p, "interp", "bloco")
    assert p.is_visible("#vista-bloco") and "ativa" in p.get_attribute("#aba-modelo", "class")
    assert "ativa" not in p.get_attribute("#aba-interp", "class")
    ir(p, "interp", "secao")
    assert p.is_visible("#vista-secao") and "ativa" not in p.get_attribute("#aba-modelo", "class")
    # "Mais" leva a Viabilidade e mostra o nome dela
    ir(p, "viab")
    assert p.is_visible("#vista-viab") and p.text_content("#aba-mais-nome") == "Viabilidade"
    assert p.is_hidden("#aba-viab")                       # o menu fechou
    # Acervo: subabas no topo; as menos usadas em "Mais"; sem lateral vazia
    ir(p, "dados", "cadastro")
    assert p.text_content("#sub-mais-nome") == "Cadastro da ANP"
    assert "sem-lateral" in p.get_attribute("#vista-dados", "class") and p.is_hidden("#vista-dados > .lateral")
    ir(p, "dados", "catalogo")
    assert p.is_visible("#vista-dados > .lateral") and p.text_content("#sub-mais-nome") == "Mais"
    # Ajuda: guia, limites, sobre; Esc fecha
    p.click("#btn-ajuda")
    p.click("[data-ajuda='guia']")
    assert "O que tem em cada pasta do REATE" in p.text_content("#dlg-corpo")
    p.keyboard.press("Escape")
    assert p.is_hidden("#dialogo")
    p.click("#btn-ajuda")
    p.click("[data-ajuda='limites']")
    assert "6 de 18 profundidades" in p.text_content("#dlg-corpo")
    p.click("#dlg-fechar")
    p.click("#btn-ajuda")
    p.click("[data-ajuda='sobre']")
    assert re.match(r"SIAPP v\d+\.\d+", p.text_content("#dlg-corpo"))
    p.keyboard.press("Escape")
    p.click("#btn-ajuda")
    p.click("[data-ajuda='diag']")
    assert p.is_visible("#cfg-diag")
    p.keyboard.press("Escape")
    # explicação longa atrás de um "?"
    ir(p, "dados", "catalogo")
    q = p.locator("#vista-dados .lateral .explicar").first
    expl = p.locator("#vista-dados .lateral p.explicacao").first
    assert expl.is_hidden()
    q.click()
    assert expl.is_visible()
    assert not janela.erros_js, janela.erros_js


def test_busca_de_poco_abre_a_ficha(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.keyboard.press("Control+k")
    assert p.is_visible("#busca-poco")
    p.fill("#busca-poco", "7-GMR-0013")              # zeros à esquerda: a mesma coisa
    janela.esperar("document.querySelector('#busca-lista strong') && "
                   "document.querySelector('#busca-lista strong').textContent === '7-GMR-13-RN'")
    p.keyboard.press("Enter")
    assert p.is_hidden("#dialogo")
    janela.esperar("!document.getElementById('vista-mapa').hidden && "
                   "document.getElementById('fi-titulo').textContent === '7-GMR-13-RN'")
    p.click("#btn-busca")
    p.fill("#busca-poco", "zzz9")
    janela.esperar("document.querySelector('#busca-lista .busca-nada') && "
                   "document.querySelector('#busca-lista .busca-nada').textContent.includes('Nenhum poço')")
    assert not janela.erros_js, janela.erros_js


def test_atalhos_de_teclado_editaveis(janela):
    p = janela.page
    abrir_projeto(janela)
    p.keyboard.press("Control+3")
    assert p.is_visible("#vista-perfis")
    p.keyboard.press("Control+6")
    assert p.is_visible("#vista-bloco")
    p.keyboard.press("Control+0")
    assert p.is_visible("#vista-projeto")
    # muda "3 · Perfis" para Ctrl+Alt+P
    p.click("#btn-ajuda")
    p.click("[data-ajuda='atalhos']")
    linha = p.locator(".tabela-atalhos tr", has_text="3 · Perfis")
    linha.locator("button").click()
    p.keyboard.press("Control+Alt+p")
    janela.esperar("prefs.atalhos.m3 === 'Ctrl+Alt+P'")
    # dar a "1 · Acervo" a tecla que já é da busca: as duas trocam
    p.locator(".tabela-atalhos tr", has_text="1 · Acervo").locator("button").click()
    p.keyboard.press("Control+k")
    janela.esperar("prefs.atalhos.m1 === 'Ctrl+K' && prefs.atalhos.busca === 'Ctrl+1'")
    assert "trocaram de tecla" in p.text_content("#status")
    assert janela.api._preferencias().ler()["atalhos"] == {"m3": "Ctrl+Alt+P", "m1": "Ctrl+K", "busca": "Ctrl+1"}
    p.keyboard.press("Escape")
    p.keyboard.press("Control+Alt+p")
    assert p.is_visible("#vista-perfis")
    p.keyboard.press("Control+k")
    assert p.is_visible("#vista-dados") and p.is_hidden("#dialogo")
    assert p.text_content("#btn-busca-tecla") == "Ctrl+1"
    # restaurar os padrões
    p.click("#btn-ajuda")
    p.click("[data-ajuda='atalhos']")
    p.click("#dlg-pe button")
    janela.esperar("Object.keys(prefs.atalhos).length === 0")
    assert janela.api._preferencias().ler()["atalhos"] == {}
    assert not janela.erros_js, janela.erros_js


def test_avisos_de_primeira_vez(janela):
    p = janela.page
    abrir_projeto(janela)
    p.evaluate("prefs.avisos_vistos = {}")          # o arranjo de teste marca todos como vistos
    ir(p, "interp", "bloco")
    p.click("#bl-montar")
    assert p.text_content("#dlg-titulo") == "Antes de montar o modelo 3D"
    assert "krigagem vira interpolação linear" in p.text_content("#dlg-corpo")
    p.click("#dlg-pe .btn.secundario")                # Cancelar: nada acontece
    assert p.is_hidden("#dialogo")
    p.click("#bl-montar")
    assert p.is_visible("#dialogo")                   # cancelou: aparece de novo
    p.check("#aviso-nao-mostrar")
    antes = p.text_content("#status")
    p.click("#dlg-pe .btn:not(.secundario)")         # Entendi, continuar: a ação segue
    janela.esperar(f"document.getElementById('status').textContent !== {antes!r}")
    janela.esperar("prefs.avisos_vistos.bloco === true")
    assert janela.api._preferencias().ler()["avisos_vistos"]["bloco"] is True
    p.click("#bl-montar")
    assert p.is_hidden("#dialogo")                    # não mostra de novo
    assert not janela.erros_js, janela.erros_js


def test_erro_vira_aviso_no_canto(janela):
    p = janela.page
    p.evaluate("status('Algo deu errado de propósito', 'erro')")
    assert p.locator("#avisos .aviso.erro").text_content() == "Algo deu errado de propósito"
    p.evaluate("status('Algo deu errado de propósito', 'erro')")
    assert p.locator("#avisos .aviso").count() == 1          # a mesma mensagem não repete
    p.evaluate("status('Clique simples', 'ok')")
    assert p.locator("#avisos .aviso.ok").count() == 0       # ok rápido fica só no rodapé
    p.evaluate("status('Trabalhando', 'trab'); inicioTrabalho = Date.now() - 5000; status('Terminou', 'ok')")
    assert p.locator("#avisos .aviso.ok").text_content() == "Terminou"   # trabalho longo: avisa
    assert not janela.erros_js, janela.erros_js


def test_projeto_aberto_recarrega_a_aba_visivel(janela, tmp_path):
    """E1 da revisão: o aviso "projeto aberto" chega antes da resposta (como no pywebview) e a aba
    que está na tela tem de recarregar."""
    p = janela.page
    p.click("#aba-docs")
    assert "Abra primeiro o projeto" in p.text_content("#docs-resumo")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))      # só o aviso chega à página
    janela.esperar("!document.getElementById('docs-resumo').textContent.includes('Abra primeiro')")
    janela.esperar("document.getElementById('projeto-nome').textContent === 'Projeto principal'")
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.58: projetos e módulos
def test_projetos_novo_e_trocar(janela, tmp_path, monkeypatch):
    p = janela.page
    abrir_projeto(janela)
    janela.esperar("document.querySelectorAll('#ini-projetos .proj').length === 2")     # principal + "Novo projeto"
    assert "aberto" in p.get_attribute("#ini-projetos .proj >> nth=0", "class")
    # novo projeto, com bacia
    p.click("#ini-novo")
    p.fill("#np-nome", "Guamaré — modelo")
    p.check(".np-bacias input[value='Potiguar']")
    p.click("#dlg-pe .btn:not(.secundario)")
    janela.esperar("document.getElementById('dlg-titulo').textContent.startsWith('Abrir Guamaré')")
    pasta = tmp_path / "projetos" / "guamare-modelo"
    assert (pasta / "siapp.json").is_file()
    # trocar de projeto com um aberto: o SIAPP reabre (aqui, só anotado)
    reaberto = []
    monkeypatch.setattr(type(janela.api), "_reiniciar", lambda self: reaberto.append(1))
    p.click("#dlg-pe .btn:not(.secundario)")
    janela.esperar("document.getElementById('dialogo').hidden")
    assert reaberto == [1]
    assert janela.api._preferencias().ler()["projeto_atual"] == str(pasta)
    # na próxima abertura, é ele que abre
    assert janela.api._projeto_inicial() == str(pasta)
    cartao = p.locator("#ini-projetos .proj", has_text="Guamaré — modelo")
    assert "Potiguar" in cartao.text_content()
    assert not janela.erros_js, janela.erros_js


def test_novidades_e_configuracao_de_atualizar(janela):
    p = janela.page
    p.click("#btn-ajuda")
    p.click("[data-ajuda='novidades']")
    janela.esperar("document.querySelector('#dlg-corpo h2') !== null")
    assert re.match(r"\d+\.\d+", p.text_content("#dlg-corpo h2"))
    p.keyboard.press("Escape")
    p.click("#btn-config")
    assert p.is_checked("#cfg-atualizar")
    p.uncheck("#cfg-atualizar")
    janela.esperar("prefs.atualizar_ao_abrir === false")
    assert janela.api._preferencias().ler()["atualizar_ao_abrir"] is False
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.59: Modelo 3D em receita, lateral ajustável
def test_modelo_3d_em_receita(janela):
    p = janela.page
    abrir_projeto(janela)
    p.click("#aba-modelo")
    # só o passo 1 aberto; os outros com uma linha do que está escolhido; Montar sempre à vista
    assert p.evaluate("[...document.querySelectorAll('#vista-bloco details.passo')].map(d => d.open)") == \
        [True, False, False, False]
    assert p.text_content("#bl-resumo-1") == "nenhum ainda"
    assert "escala" in p.text_content("#bl-resumo-2") and "160 células" in p.text_content("#bl-resumo-3")
    assert p.is_visible("#bl-montar") and p.is_hidden("#bl-m-estrutura")
    p.click("#bl-passo-3 > summary")
    p.fill("#bl-celulas", "90")
    p.dispatch_event("#bl-celulas", "input")
    assert "90 células" in p.text_content("#bl-resumo-3")
    p.select_option("#bl-nivel", "zonas")
    assert p.text_content("#bl-resumo-3").startswith("zonas produtoras")
    assert not janela.erros_js, janela.erros_js


def test_largura_da_barra_lateral(janela):
    p = janela.page
    abrir_projeto(janela)
    p.click("#aba-docs")
    lat = p.locator("#vista-docs > .lateral")
    caixa = lat.bounding_box()
    x, y = caixa["x"] + caixa["width"] - 2, caixa["y"] + 200
    p.mouse.move(x, y)
    p.mouse.down()
    p.mouse.move(x + 120, y, steps=4)
    p.mouse.up()
    janela.esperar("prefs.larguras && prefs.larguras.docs > 400")
    assert abs(lat.bounding_box()["width"] - (caixa["width"] + 120)) < 4
    assert janela.api._preferencias().ler()["larguras"]["docs"] == prefs_larg(p)
    p.mouse.dblclick(lat.bounding_box()["x"] + lat.bounding_box()["width"] - 2, y)
    janela.esperar("!prefs.larguras.docs")
    assert abs(lat.bounding_box()["width"] - caixa["width"]) < 4
    assert not janela.erros_js, janela.erros_js


def prefs_larg(p):
    return p.evaluate("prefs.larguras.docs")


# ---------------------------------------------------------------- 0.59: pedidos pequenos
def test_filtro_de_poco_na_lista_de_perfis(janela, tmp_path):
    from test_perfis import las_exemplo
    p = janela.page
    abrir_projeto(janela)
    for poco, nome in (("7-GMR-13-RN", "7gmr13.las"), ("1-AURI-12-RN", "auri.las")):
        pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / poco / "Perfis"
        pasta.mkdir(parents=True)
        las_exemplo(pasta / nome)
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 2")
    p.fill("#pf-poco-busca", "7-GMR-0013")
    assert p.locator("#lista-perfis > li:not([hidden])").count() == 1
    assert "1 de 2" in p.text_content("#pf-poco-n")
    p.fill("#pf-poco-busca", "zzz")
    assert p.locator("#lista-perfis > li:not([hidden])").count() == 0
    p.fill("#pf-poco-busca", "")
    assert p.locator("#lista-perfis > li:not([hidden])").count() == 2 and p.is_hidden("#pf-poco-n")
    assert not janela.erros_js, janela.erros_js


def test_so_os_destacados_e_arranjo_padrao(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('poço')")
    p.fill("#dq-poco", "7-GMR-13-RN")
    p.click("#dq-form button[type=submit]")
    janela.esperar("!document.getElementById('dq-acoes').hidden")
    p.click("#dq-so")
    janela.esperar("!mapa.hasLayer(camadaPocos)")
    assert p.text_content("#dq-so") == "Mostrar todos"
    p.click("#dq-so")
    janela.esperar("mapa.hasLayer(camadaPocos)")
    assert janela.api._preferencias().ler()["lembrar_arranjo"] is False          # 0.59: reabre no padrão
    assert p.is_hidden("#cm-importar-ti")
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.60: ficha do poço em página inteira
def test_ficha_em_pagina_inteira(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.keyboard.press("Control+k")
    p.fill("#busca-poco", "gmr13")
    janela.esperar("document.querySelector('#busca-lista strong') !== null")
    p.keyboard.press("Enter")
    janela.esperar("document.getElementById('fi-titulo').textContent === '7-GMR-13-RN' && "
                   "!document.getElementById('fi-sub').textContent.includes('carregando')")
    assert p.is_visible("#mapa")
    largura_lado = p.locator("#ficha").bounding_box()["width"]
    p.click("#fi-cheia")
    janela.esperar("prefs.ficha_cheia === true")
    assert p.is_hidden("#mapa") and p.text_content("#fi-cheia") == "Ao lado do mapa"
    assert p.locator("#ficha").bounding_box()["width"] > largura_lado + 300
    p.click("#fi-fechar")
    assert p.is_visible("#mapa")                     # fechou a ficha: o mapa volta
    assert janela.api._preferencias().ler()["ficha_cheia"] is True
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.61: trocar de aba sem recarregar à toa
def test_aba_so_recarrega_quando_o_projeto_muda(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    for _ in range(2):                                         # o projeto acaba de abrir: deixa assentar
        ir(p, "perfis")
        ir(p, "docs")
        p.wait_for_timeout(300)
    p.evaluate("window.__n = 0; const f = AO_ABRIR_ABA.perfis; AO_ABRIR_ABA.perfis = () => { window.__n++; f(); }; 0")
    ir(p, "perfis")
    ir(p, "docs")
    p.wait_for_timeout(400)
    assert p.evaluate("window.__n") == 0                       # nada mudou: não releu
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")  # o projeto mudou
    ir(p, "perfis")
    janela.esperar("window.__n === 1")
    p.keyboard.press("F5")                                    # F5 força
    janela.esperar("window.__n === 2")
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.62: mapa leve com o cadastro inteiro
def test_mapa_reaproveita_marcadores_e_abre_ficha_pelo_grupo(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    ir(p, "mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('poço')")
    p.select_option("#f-bacia", "")
    janela.esperar("camadaPocos.getLayers().length === 3")
    m1 = p.evaluate("marcadores.get('7-GMR-13-RN')._leaflet_id")
    p.select_option("#f-bacia", "Potiguar")
    janela.esperar("camadaPocos.getLayers().length === 2")
    assert p.evaluate("marcadores.get('7-GMR-13-RN')._leaflet_id") == m1          # o mesmo marcador, não um novo
    assert p.evaluate("pocosMapa.find(x => x.id === '1-AURI-12-RN').campo") == "AURIZÔNIA"   # dicionário desfeito
    p.evaluate("mapa.setView([-5.11, -36.33], 12, {animate: false})")
    pt = p.evaluate("(() => { const r = document.getElementById('mapa').getBoundingClientRect(); "
                    "const c = mapa.latLngToContainerPoint([-5.11, -36.33]); return [r.left + c.x, r.top + c.y]; })()")
    p.mouse.move(pt[0], pt[1])
    p.mouse.click(pt[0], pt[1])                                                    # clique de verdade no canvas
    janela.esperar("document.getElementById('fi-titulo').textContent === '7-GMR-13-RN'")
    p.evaluate("marcadores.get('7-GMR-13-RN').fire('mouseover', {}, true)")
    assert p.evaluate("marcadores.get('7-GMR-13-RN').getTooltip().getContent()") == "7-GMR-13-RN · GUAMARÉ"
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.63: fontes e prioridade num lugar só
def test_fontes_e_prioridade_na_configuracao(janela):
    p = janela.page
    abrir_projeto(janela)
    p.click("#btn-config")
    p.click("[data-cfg='fontes']")
    janela.esperar("document.querySelectorAll('#fp-zonas li').length === 7 && "
                   "document.querySelectorAll('#fp-contagens tr').length === 3")
    assert p.is_disabled("#fp-zonas li[data-fonte='tabela'] input")          # sem tabela importada
    p.locator("#fp-zonas li[data-fonte='fluido'] input").uncheck()             # grava na hora
    janela.esperar("historicoStatus.some((m) => m.texto.startsWith('Fontes das zonas'))")
    assert "fluido" not in janela.api.fontes_prioridade()["zonas"]["ligadas"]
    p.locator("#fp-zonas li[data-fonte='agp_zonas'] button", has_text="↑").click()
    janela.esperar("document.querySelectorAll('#fp-zonas li')[5].dataset.fonte === 'agp_zonas'")
    assert janela.api.fontes_prioridade()["zonas"]["ordem"][5] == "agp_zonas"
    p.keyboard.press("Escape")
    # o Modelo 3D mostra o resumo do projeto e manda as fontes ligadas
    ir(p, "interp", "bloco")
    p.select_option("#bl-nivel", "zonas")
    janela.esperar("document.querySelector('#bz-fontes li.fp-desligada') !== null")
    assert "Análise de fluido" in p.text_content("#bz-fontes li.fp-desligada:last-child") or \
        "não usada" in p.text_content("#bz-fontes")
    assert "fluido" not in p.evaluate("lerZonasBloco().fontes")
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.64: navegar no perfil
def test_perfil_roda_so_depois_de_clicar_navegador_e_escala(janela, tmp_path):
    from test_perfis import las_exemplo
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Perfis"
    pasta.mkdir(parents=True)
    las_exemplo(pasta / "7gmr13.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas:not(#pf-nav)').length === 3", 30)
    p.click("#pf-mais")                                                         # janela menor que o poço
    janela.esperar("pf.buf && pf.buf.faixa < (pf.limites[1] - pf.limites[0]) * 0.6")
    cv = p.locator("#pf-trilhas canvas:not(#pf-nav)").nth(1)
    cx = cv.bounding_box()
    topo0 = p.evaluate("pf.topo")
    p.mouse.move(cx["x"] + 30, cx["y"] + 80)
    p.mouse.wheel(0, 300)                                                       # sem clicar: a página rola
    p.wait_for_timeout(300)
    assert p.evaluate("pf.topo") == topo0
    assert p.is_visible("#pf-dica-roda")
    cv.scroll_into_view_if_needed()
    cx = cv.bounding_box()
    p.mouse.click(cx["x"] + 30, cx["y"] + 80)                                  # clicou: a roda anda no perfil
    assert p.evaluate("pf.ativo")
    chamadas = p.evaluate("window.__n = 0; const f = api.grafico_perfil; api.grafico_perfil = (...a) => { window.__n++; return f(...a); }; 0")
    p.mouse.wheel(0, 100)
    janela.esperar(f"pf.topo > {topo0}")
    p.wait_for_timeout(300)
    assert p.evaluate("window.__n") <= 1                                        # anda sem pedir tudo de novo ao motor
    p.keyboard.press("PageDown")
    janela.esperar(f"pf.topo > {topo0} + (pf.base - pf.topo) * 0.5")
    # navegador: clicar perto do topo leva a janela para lá
    p.locator("#pf-nav").scroll_into_view_if_needed()
    nav = p.locator("#pf-nav").bounding_box()
    p.mouse.click(nav["x"] + 10, nav["y"] + 3)
    janela.esperar("Math.abs(pf.topo - pf.limites[0]) < 1e-6")
    p.select_option("#pf-escala", "200")
    janela.esperar("document.getElementById('pf-escala').value === '200'")
    assert not janela.erros_js, janela.erros_js


def test_modelo_3d_caixa_aberta_aparece_acima_do_pe(janela):
    """0.64: abrir uma caixa da lateral do Modelo 3D rola a lateral até ela aparecer, acima do pé fixo (Montar)."""
    p = janela.page
    p.set_viewport_size({"width": 1280, "height": 720})
    abrir_projeto(janela)
    ir(p, "interp", "bloco")
    p.evaluate("document.querySelectorAll('#bl-passo-1, #bl-passo-2').forEach((d) => d.open = true)")
    p.wait_for_timeout(300)
    p.evaluate("document.getElementById('bl-passo-3').closest('.lateral').scrollTop = 0")
    p.locator("#bl-passo-3 > summary").click()
    p.wait_for_timeout(900)
    visivel = p.evaluate("""(() => {
      const d = document.getElementById('bl-passo-3'), col = d.closest('.lateral');
      const pe = col.querySelector('.etapa-montar');
      const fundo = col.getBoundingClientRect().bottom - (pe ? pe.getBoundingClientRect().height : 0);
      const r = d.getBoundingClientRect(), s = d.querySelector('summary').getBoundingClientRect();
      return { titulo: s.top >= col.getBoundingClientRect().top - 1, rolou: col.scrollTop > 0,
               cabe: r.bottom <= fundo + 2 || s.top <= col.getBoundingClientRect().top + 12 };
    })()""")
    assert visivel == {"titulo": True, "rolou": True, "cabe": True}, visivel
    assert not janela.erros_js, janela.erros_js


# ---------------------------------------------------------------- 0.65: "Ver arquivos" da ficha num passo só
def test_ver_arquivos_da_ficha_conecta_e_abre_o_poco(janela, monkeypatch):
    from test_levantamento import PDF, ClienteFalso
    from test_pocos import csv_exemplo
    from motor import pocos as mpo
    from motor import reate

    class Falso(ClienteFalso):
        mapear_poco = reate.ClienteREATE.mapear_poco

    cam = "/POCO/Categoria-7/Categoria-7_parte1/7-GMR-13-RN/"
    falso = Falso({cam + "Pasta de Poco/pasta.pdf": PDF, "/POCO/Categoria-1/1-AURI-12-RN/Perfil/a.las": b"x"})
    conexoes = []
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia",
                        classmethod(lambda cls, bacia, **kw: conexoes.append(bacia) or falso))
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    mpo.registrar_reate(janela.api._banco, "Potiguar", "Categoria-7",
                        [{"nome": "7-GMR-13-RN", "caminho": cam, "parte": "Categoria-7_parte1"}])
    p.click("#aba-mapa")
    p.evaluate("abrirFicha('7-GMR-13-RN')")
    janela.esperar("document.getElementById('fi-titulo').textContent === '7-GMR-13-RN'")
    p.locator("#ficha button", has_text="Ver arquivos").click()       # bacia não conectada, categoria não listada
    janela.esperar("!document.getElementById('gaveta').hidden && "
                   "document.getElementById('g-titulo').textContent === '7-GMR-13-RN'", 30)
    janela.esperar("document.getElementById('g-arvore').textContent.includes('Pasta de Poco')", 30)
    assert p.is_visible("#vista-dados")
    assert "só este poço" in p.text_content("#resumo-pocos")
    assert p.input_value("#sel-bacia") == "Potiguar" and p.locator("#lista-cat button").count() == 2
    assert p.locator("#lista-cat button.ativa").text_content() == "Categoria-7"
    # de novo, já conectado: não reconecta
    n = len(conexoes)
    p.click("#aba-mapa")
    p.locator("#ficha button", has_text="Ver arquivos").click()
    janela.esperar("document.getElementById('g-arvore').textContent.includes('Pasta de Poco')", 30)
    assert len(conexoes) == n
    assert not janela.erros_js, janela.erros_js


def test_apoie_o_projeto_so_quando_configurado(janela, tmp_path, monkeypatch):
    from ponte import base
    p = janela.page
    rec = tmp_path / "recursos"
    rec.mkdir()
    (rec / "doacao.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(base, "PASTA_RECURSOS", str(rec))
    p.evaluate("prepararDoacao().then(() => 0)")
    janela.esperar("document.getElementById('menu-doacao').hidden")      # sem chave nem link: escondida
    assert p.evaluate("document.getElementById('ini-doe').hidden")           # 1.2: nem a xícara do Início
    (rec / "doacao.json").write_text(json.dumps({"pix": {"chave": "a@b.com", "nome": "Fulano", "cidade": "Maceio"},
                                                 "links": [{"rotulo": "Apoia", "url": "https://exemplo.org/siapp"}]}),
                                     encoding="utf-8")
    p.evaluate("prepararDoacao().then(() => 0)")
    janela.esperar("!document.getElementById('menu-doacao').hidden")
    p.click("#btn-ajuda")
    p.click("#menu-doacao")
    janela.esperar("document.getElementById('doacao-pix-codigo') !== null")
    assert p.input_value("#doacao-pix-chave") == "a@b.com"
    assert p.input_value("#doacao-pix-codigo").startswith("000201")
    assert p.get_attribute(".doacao-links a", "href") == "https://exemplo.org/siapp"
    p.keyboard.press("Escape")
    p.click("#btn-ajuda")
    p.click("[data-ajuda='sobre']")
    assert "Apoie o projeto" in p.text_content("#dlg-pe")
    assert not janela.erros_js, janela.erros_js


def test_doacao_a_vista_no_inicio(janela, tmp_path, monkeypatch):
    """1.2: a xícara "Doe" fica ao lado dos projetos, no Início, e abre a mesma tela de doação."""
    from ponte import base
    p = janela.page
    rec = tmp_path / "recursos"
    rec.mkdir()
    (rec / "doacao.json").write_text(json.dumps({"pix": {"chave": "a@b.com", "nome": "Fulano", "cidade": "Maceio"}}),
                                     encoding="utf-8")
    monkeypatch.setattr(base, "PASTA_RECURSOS", str(rec))
    p.evaluate("prepararDoacao().then(() => 0)")
    p.click("#aba-projeto")
    janela.esperar("!document.getElementById('ini-doe').hidden")
    assert p.is_visible("#ini-doe") and "Doe" in p.text_content("#ini-doe")
    # na mesma linha dos projetos, à direita deles
    caixa_doe = p.locator("#ini-doe").bounding_box()
    caixa_proj = p.locator("#ini-projetos").bounding_box()
    assert caixa_doe["x"] >= caixa_proj["x"] + caixa_proj["width"] - 1
    assert abs(caixa_doe["y"] - caixa_proj["y"]) < 2
    p.click("#ini-doe")
    janela.esperar("document.getElementById('doacao-pix-chave') !== null")
    assert p.input_value("#doacao-pix-chave") == "a@b.com"
    assert not janela.erros_js, janela.erros_js


def test_mascote_abre_como_usar(janela):
    """1.2: o mascote no canto do Início abre "Como usar o SIAPP"; cada assunto tem pose, passos e atalho."""
    p = janela.page
    p.click("#aba-projeto")
    assert p.is_visible("#mascote-ajuda")
    assert p.evaluate("document.querySelector('#mascote-ajuda img').naturalWidth") > 0     # a imagem carregou
    p.click("#mascote-ajuda")
    janela.esperar("!document.getElementById('dialogo').hidden")
    assert p.text_content("#dlg-titulo") == "Como usar o SIAPP"
    temas = p.locator(".cu-tema-btn")
    assert temas.count() == p.evaluate("COMO_USAR.length") >= 8
    assert p.get_attribute(".cu-tema-btn[data-tema='inicio']", "aria-current") == "true"
    for i in range(temas.count()):
        temas.nth(i).click()
        assert p.locator(".cu-passos li").count() >= 3
        janela.esperar("document.querySelector('.cu-masc').complete && document.querySelector('.cu-masc').naturalWidth > 0")
    # o atalho fecha a ajuda e leva à aba
    p.click(".cu-tema-btn[data-tema='documentos']")
    p.click(".cu-ir")
    assert p.evaluate("document.getElementById('dialogo').hidden")
    assert p.is_visible("#vista-docs")
    # o mascote só fica no Início
    assert not p.is_visible("#mascote-ajuda")
    # e o menu Ajuda também abre a mesma ajuda
    p.click("#btn-ajuda")
    p.click("#menu-como-usar")
    janela.esperar("document.querySelector('.cu-tema-btn') !== null")
    assert not janela.erros_js, janela.erros_js


def test_tela_de_apoio_com_quem_faz_valores_e_qr(janela):
    """1.3: a tela de apoio do repositório: mascote, quem faz o SIAPP, valores com QR Code e outras formas de ajudar."""
    p = janela.page
    p.evaluate("prepararDoacao().then(() => 0)")
    janela.esperar("!document.getElementById('menu-doacao').hidden")
    p.evaluate("abrirDoacao()")
    janela.esperar("document.getElementById('doacao-qr') !== null && document.getElementById('doacao-qr').naturalWidth > 0")
    assert "opcional" in p.text_content(".apoio-opcional")
    assert "Ruan da Silva Nobre" in p.text_content(".apoio-sobre")
    assert p.locator(".apoio-pub a").count() >= 1 and p.locator(".apoio-linkedin a").count() == 1
    # começa sem valor escolhido; o código é o de sempre
    assert p.locator(".apoio-valor[aria-pressed='true']").count() == 0
    assert "5405" not in p.input_value("#doacao-pix-codigo")
    rotulos = [t.strip() for t in p.locator(".apoio-valor strong").all_text_contents()]
    assert rotulos == ["Um cafezinho", "Um lanche", "Uma tarde de código"]
    p.click(".apoio-valor >> nth=1")
    janela.esperar("document.getElementById('doacao-pix-codigo').value.includes('540515.00')")
    assert p.get_attribute(".apoio-valor >> nth=1", "aria-pressed") == "true"
    assert "15,00" in p.text_content("#doacao-valor")
    p.fill("#doacao-outro", "7,5")
    p.click(".apoio-outro button")
    janela.esperar("document.getElementById('doacao-pix-codigo').value.includes('54047.50')")
    assert p.locator(".apoio-valor[aria-pressed='true']").count() == 0
    # outras formas de ajudar: na aba "Sem dinheiro", com o caminho para a Comunidade
    assert not p.is_visible(".apoio-outras")
    p.click(".apoio-aba[data-aba='outras']")
    assert p.is_visible(".apoio-outras") and not p.is_visible(".apoio-pix")
    assert p.locator(".apoio-outras li").count() == 5
    # numa tela de notebook (1366 × 768), nada fica cortado: as duas abas cabem sem rolar
    p.set_viewport_size({"width": 1366, "height": 768})
    cabe = "(() => { const c = document.getElementById('dlg-corpo'); return c.scrollHeight <= c.clientHeight + 1; })()"
    assert p.evaluate(cabe)
    p.click(".apoio-aba[data-aba='pix']")
    assert p.evaluate(cabe)
    p.click(".apoio-aba[data-aba='outras']")
    p.click(".apoio-outras .link-botao")
    assert p.evaluate("document.getElementById('dialogo').hidden")
    assert not janela.erros_js, janela.erros_js


def test_comunidade_no_topo_avisa_base_nova_e_liga_o_dado_a_pagina(janela, monkeypatch, tmp_path):
    """1.3: a Comunidade é aba do topo; base nova no GitHub aparece com o que entrou; o dado da comunidade abre a
    página do mesmo documento baixado aqui (pelo SHA-256), e o poço ganha a marca da comunidade no mapa."""
    from base_util import montar_base
    from motor import banco as mb
    from motor import comunidade as mc
    p = janela.page
    assert p.is_visible("#aba-comunidade") and p.is_hidden("#aba-comunidade-aviso")
    p.click("#aba-mais")
    assert not p.locator(".menu-pop #aba-comunidade").count()             # saiu do menu Mais
    p.keyboard.press("Escape")
    # alguém transcreveu um dado no documento x.pdf; a base com o pacote foi publicada
    outro = mb.Banco(str(tmp_path / "outro.sqlite"))
    outro.registrar_arquivo("bruto/P/x.pdf", bacia="Potiguar", poco_id="7-GMR-13-RN", sha256="cd" * 32,
                            caminho_remoto="/POCO/C7/7-GMR-13-RN/x.pdf", tipo="documento")
    outro.salvar_fato({"poco_id": "7-GMR-13-RN", "tipo": "topo_formacao", "nome": "Açu", "prof_topo": 512.5,
                       "fonte_rel": "bruto/P/x.pdf", "pagina": 3})
    pacote = mc.montar_pacote(outro, {"nome": "Maria Souza", "instituicao": "UFRN"}, "1.3.0")
    resumo = {"formato": "siapp-dados-resumo", "versao_base": "v2026.11.0", "contagens": {"contribuicoes": 1},
              "pacotes": [{"id": pacote["id"], "autor": "Maria Souza", "instituicao": "UFRN", "correcoes": 0,
                           "palavras": 0, "fatos": 1, "interpretacoes": 0, "pocos": ["7-GMR-13-RN"]}]}
    monkeypatch.setattr(mc, "consultar_base", lambda *a, **k: {"versao": "v2026.11.0", "resumo": resumo,
                                                               "publicada_em": "2026-11-21T10:00:00Z"})
    abrir_projeto(janela)
    janela.esperar("!document.getElementById('aba-comunidade-aviso').hidden")
    assert "base nova da comunidade (v2026.11.0)" in janela.status()
    ir(p, "comunidade")
    janela.esperar("!document.getElementById('com-novidade').hidden")
    texto = p.text_content("#com-novidade")
    assert "v2026.11.0" in texto and "Maria Souza (UFRN)" in texto and "1 dado(s) transcrito(s)" in texto
    assert "7-GMR-13-RN" in texto and p.is_checked("#com-auto")
    # "Atualizar pela internet" aplica a base (o download é trocado por uma cópia local)
    montar_base(str(tmp_path / "pub.sqlite"), [pacote], "v2026.11.0")

    def baixar(destino, *a, **k):
        import shutil
        shutil.copy(tmp_path / "pub.sqlite", destino)
        return {"versao": "v2026.11.0", "publicada_em": "2026-11-21T10:00:00Z"}
    monkeypatch.setattr(mc, "baixar_base", baixar)
    p.click("#btn-base")
    janela.esperar("document.getElementById('com-novidade').hidden")
    assert p.is_hidden("#aba-comunidade-aviso") and "Base v2026.11.0 aplicada" in janela.status()
    # o mesmo documento, baixado aqui noutra pasta: o dado da comunidade aponta para a página
    janela.api._banco.registrar_arquivo("bruto/Potiguar/outra/x.pdf", bacia="Potiguar", poco_id="7-GMR-13-RN",
                                        sha256="cd" * 32, tipo="documento")
    ir(p, "mapa")
    p.evaluate("abrirFicha('7-GMR-13-RN')")
    janela.esperar("document.querySelector('#fi-corpo table.fatos button.link-botao') !== null")
    assert "1 da comunidade" in p.text_content("#fi-corpo")
    assert "Abrir x.pdf, página 3" in p.get_attribute("#fi-corpo table.fatos button.link-botao", "title")
    assert not janela.erros_js, janela.erros_js
