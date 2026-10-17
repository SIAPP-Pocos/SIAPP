"""Interface de verdade num navegador sem tela (pulado sem Playwright)."""
import os

import pytest

pytestmark = pytest.mark.interface


def abrir_projeto(janela):
    janela.page.click("#ini-pasta")
    janela.esperar("document.getElementById('ini-pasta').disabled")


def test_abre_no_inicio_e_abre_projeto(janela):
    p = janela.page
    assert p.text_content("#versao").startswith("v0.")
    assert p.is_visible("#vista-inicio") and not p.is_visible("#vista-catalogo")
    abrir_projeto(janela)
    janela.esperar("!document.getElementById('panorama').hidden")
    assert "arquivo(s) baixado(s)" in p.text_content("#panorama")
    p.click("#aba-catalogo")
    assert not p.is_visible("#etapa-bacia.bloqueada")
    assert not janela.erros_js, janela.erros_js


def test_abas_trocam_de_vista(janela):
    p = janela.page
    p.click("#aba-docs")
    assert p.is_visible("#vista-docs") and not p.is_visible("#vista-inicio")
    assert "pasta do projeto" in p.text_content("#docs-resumo")
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
    p.click("#aba-inicio")
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
    p.select_option("#lv-bacia", "Potiguar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('Ainda não levantada')")
    p.click("#lv-carregar")
    janela.esperar("document.querySelectorAll('.lv-cat').length === 2")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('2 pasta(s) de poço')", 30)
    assert "Levantamento concluído" in janela.status()
    texto = p.text_content("#lv-resumo")
    assert ".tif → LIS" in texto and "perfil digital" in texto
    assert p.is_visible("#legenda-acervo") and p.input_value("#f-cor") == "acervo"
    p.select_option("#f-acervo", "digital")
    janela.esperar("document.querySelectorAll('#lista-mapa button').length === 1")
    p.click("#lista-mapa button")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('No acervo do REATE')")
    assert "LIS em fita" in p.text_content("#fi-corpo")
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
    assert not janela.erros_js, janela.erros_js


def test_aba_secao(janela):
    from test_secao import poco
    p = janela.page
    abrir_projeto(janela)
    b = janela.api._banco
    poco(b, "1-OES-1-RN", -5.30, -36.80, 50.0, [("F", "JANDAI", 10, 300), ("F", "ACU", 300, 700)], prof_final=750)
    poco(b, "1-MEI-1-RN", -5.30, -36.75, 40.0, [("F", "JANDAI", 8, 320), ("F", "ACU", 320, 760)], prof_final=800)
    poco(b, "1-LES-1-RN", -5.30, -36.70, 30.0, [("F", "JANDAI", 5, 330), ("F", "ACU", 330, 900)], prof_final=950)
    p.click("#aba-secao")
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
    p.select_option("#lv-bacia", "Potiguar")
    assert not p.is_checked("#lv-esquemas")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('Esquemas de ferramentas')", 30)
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
    p.click("#aba-bloco")
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
    p.click("#aba-bloco")
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
    p.click("#aba-bloco")
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
    p.click("#aba-bloco")
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
    p.click("#aba-bloco")
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
    p.click("#aba-bloco")
    janela.esperar("document.getElementById('bl-disponiveis').textContent.includes('9 poço')")
    # escala: reservatório preenche o formulário (spline topo a topo, sem margem)
    janela.esperar("document.getElementById('bl-m-estrutura').options.length === 5")
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
    p.click("#bl-montar")
    janela.esperar("window.BlocoVisor && window.BlocoVisor.estado().superficies === 2", 60)
    assert "krigagem" in p.text_content("#bl-resumo")
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
    assert p.locator("#bl-cmp-tabela thead th").count() == 2 + 6
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
