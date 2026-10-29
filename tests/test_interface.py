"""Interface de verdade num navegador sem tela (pulado sem Playwright)."""
import os

import pytest

pytestmark = pytest.mark.interface


def abrir_projeto(janela):
    janela.page.click("#ini-pasta")
    janela.esperar("document.getElementById('ini-pasta').disabled")


def ir(p, aba, sub=None):
    """Vai até uma aba (e uma sub-aba de Dados ou de Interpretação)."""
    p.click(f"#aba-{aba}")
    if sub and aba == "dados":
        p.click(f".sub-nav [data-sub='{sub}']")
    elif sub and aba == "interp":
        p.locator(f"[data-interp='{sub}'] >> visible=true").first.click()


def test_abre_no_inicio_e_abre_projeto(janela):
    p = janela.page
    assert p.text_content("#versao").startswith("v0.")
    assert p.is_visible("#vista-projeto") and not p.is_visible("#vista-dados")
    abrir_projeto(janela)
    janela.esperar("!document.getElementById('panorama').hidden")
    assert "arquivo(s) baixado(s)" in p.text_content("#panorama")
    p.click("#aba-dados")
    assert not p.is_visible("#etapa-bacia.bloqueada")
    assert not janela.erros_js, janela.erros_js


def test_abas_trocam_de_vista(janela):
    p = janela.page
    p.click("#aba-docs")
    assert p.is_visible("#vista-docs") and not p.is_visible("#vista-projeto")
    assert "Abra primeiro o projeto" in p.text_content("#docs-resumo")
    p.click(".fluxo button[data-ir='comunidade']") if p.is_visible(".fluxo") else p.click("#aba-comunidade")
    p.click("#aba-comunidade")
    assert p.is_visible("#vista-comunidade")
    assert not janela.erros_js, janela.erros_js


def test_comunidade_autor_exportar_importar(janela):
    p = janela.page
    abrir_projeto(janela)
    api = janela.api
    api.corrigir_palavra("BARIGIRAS", "BARREIRAS")
    p.click("#aba-comunidade")
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
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas').length === 3", 30)
    assert "7-GMR-13-RN" in p.text_content("#pf-titulo")
    # arrastar na trilha marca um intervalo
    cv = p.locator("#pf-trilhas canvas").nth(1)
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
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas').length >= 3", 30)
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
    # pelas pontas da linha
    p.fill("#sec-a", "1-OES-1-RN")
    p.fill("#sec-b", "1-LES-1-RN")
    p.click("#sec-corredor")
    janela.esperar("document.querySelectorAll('#sec-lista li').length === 3")
    assert "3 poço(s)" in p.text_content("#sec-corredor-res")
    # nivelado no topo do Açu
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
    p.click("#bl-png")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('.png')", 30)
    pngs = list((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("bloco_*.png"))
    assert len(pngs) == 1 and pngs[0].read_bytes()[:4] == b"\x89PNG" and pngs[0].stat().st_size > 20000
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
    p.click("[data-figura='pdf']")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_figura.pdf')", 30)
    pdfs = list((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("*_figura.pdf"))
    assert len(pdfs) == 1 and pdfs[0].read_bytes()[:4] == b"%PDF"
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
    p.click("[data-figura='svg']")
    janela.esperar("document.getElementById('bl-exportado').textContent.includes('_figura.svg')", 30)
    svg = next((tmp_path / "ambiente_teste" / "exportacoes" / "blocos").glob("*_figura.svg")).read_text("utf-8")
    assert "Bloco fechado (AGP)" in svg and "Seção A–A′" in svg
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
    p.click("#bl-validar")
    janela.esperar("!document.getElementById('bl-val').hidden", 60)
    assert "previstos sem o próprio poço" in p.text_content("#bl-val-resumo")
    assert "Açu" in p.text_content("#bl-val-tabela") or "ACU" in p.text_content("#bl-val-tabela")
    assert p.locator("#bl-val-faixas tbody tr").count() >= 1
    # prognóstico pelo clique no bloco
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
    p.click("#bl-saidas summary")
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
    p.click("#aba-viab")
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
    assert "ambiente_teste/execucoes/viabilidade/" in p.text_content("#vb-mem-arquivo")
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
    p.click("#btn-dividir")
    assert p.is_visible("#vista-mapa") and p.is_visible("#vista-docs") and p.is_visible("#divisor")
    assert "direita" in p.get_attribute("#aba-docs", "class")
    # a área da direita troca de aba; os lados trocam
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
    # ordem do painel: poços → interpolação → grade → montar
    passos = p.evaluate("[...document.querySelectorAll('#vista-bloco .lateral h2')].map(h => h.textContent.trim())")
    assert [x[:1] for x in passos[:4]] == ["1", "2", "3", "4"] and "Montar" in passos[3]
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
    p.click("#bl-explica summary")
    assert "erro = previsto − AGP" in p.text_content("#bl-explica")
    # a figura usa a mesma aparência
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
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas').length === 3", 30)
    # cabeçalhos da mesma altura: as trilhas começam todas na mesma linha
    alturas = p.evaluate("[...document.querySelectorAll('.pf-cab-trilha')].map(c => c.offsetHeight)")
    assert len(set(alturas)) == 1
    topos = p.evaluate("[...document.querySelectorAll('#pf-trilhas canvas')].map(c => Math.round(c.getBoundingClientRect().top))")
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
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas').length === 3", 30)
    cv = p.locator("#pf-trilhas canvas").nth(1)
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
    p.click("#aba-comunidade")
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
    p.click("#aba-comunidade")
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
    assert "Seção estratigráfica e bloco 3D: só os topos do AGP" in p.text_content("#co-resultado")
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
