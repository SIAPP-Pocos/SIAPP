"""Preferências, janelas destacadas, diagnóstico e pastas de exportação (0.30)."""
import os
import sys
import types

from motor import preferencias as mpf


# ------------------------------------------------------------ preferências
def test_normalizar_aceita_so_o_que_vale():
    p = mpf.normalizar({"paleta": "neon", "tema": "escuro", "fonte": "XL", "abrir_ao_iniciar": "sim",
                        "recolhidas": {"mapa": True, "x": True, "docs": "s"},
                        "layout": {"ativa": "mapa", "direita": "mapa", "dividida": True, "razao": 3},
                        "janelas": {"docs": {"x": 10, "y": 20, "largura": 900, "altura": 600}, "zz": {"x": 1}},
                        "abertas": ["docs", "docs", "projeto", "nada"]})
    assert p["paleta"] == "marinho" and p["tema"] == "escuro" and p["fonte"] == "M"
    assert p["abrir_ao_iniciar"] is True and p["recolhidas"] == {"mapa": True}
    assert p["layout"]["razao"] == 0.8 and p["layout"]["dividida"] is False     # direita = ativa: sem divisão
    assert p["janelas"] == {"docs": {"x": 10, "y": 20, "largura": 900, "altura": 600}}
    assert p["abertas"] == ["docs"]
    assert mpf.normalizar("lixo") == mpf.PADRAO


def test_preferencias_gravam_e_mesclam(tmp_path):
    pr = mpf.Preferencias(str(tmp_path))
    pr.atualizar({"layout": {"ativa": "docs"}, "janelas": {"mapa": {"x": 5, "y": 6}}})
    pr.atualizar({"layout": {"dividida": True, "direita": "mapa"}, "janelas": {"perfis": {"x": 1, "y": 2}}})
    lido = mpf.Preferencias(str(tmp_path)).ler()
    assert lido["layout"]["ativa"] == "docs" and lido["layout"]["dividida"] is True
    assert set(lido["janelas"]) == {"mapa", "perfis"}
    (tmp_path / "preferencias.json").write_text("{quebrado", encoding="utf-8")
    assert mpf.Preferencias(str(tmp_path)).ler()["paleta"] == "marinho"


def test_atalhos_e_avisos_vistos():
    p = mpf.normalizar({"atalhos": {"busca": "Ctrl+K", "inicio": "Ctrl+K", "sobre": "Ctrl+Alt+S", "ruim": "zz",
                                    "Com Espaco": "Ctrl+1", "ajuda": "F1", "lateral": ""},
                        "avisos_vistos": {"ocr": True, "bloco": False, "x y": True},
                        "layout": {"sub_dados": "baixados"}})
    assert p["atalhos"] == {"busca": "Ctrl+K", "sobre": "Ctrl+Alt+S", "ajuda": "F1", "lateral": ""}
    assert p["avisos_vistos"] == {"ocr": True}
    assert p["layout"]["sub_dados"] == "baixados"            # 0.56 gravava e a 0.56 mesma descartava
    m = mpf.mesclar(p, {"atalhos": {"inicio": "Ctrl+0"}, "avisos_vistos": {"bloco": True}})
    assert m["atalhos"]["inicio"] == "Ctrl+0" and m["atalhos"]["busca"] == "Ctrl+K"
    assert m["avisos_vistos"] == {"ocr": True, "bloco": True}
    m = mpf.mesclar(m, {"atalhos": {"busca": None, "inicio": None}, "avisos_vistos": {"ocr": None}})
    assert "busca" not in m["atalhos"] and m["avisos_vistos"] == {"bloco": True}     # volta ao padrão


def test_janela_fora_das_telas_nao_volta_la():
    telas = [(0, 0, 1920, 1080), (1920, 0, 1280, 1024)]
    assert mpf.visivel({"x": 2000, "y": 100, "largura": 900}, telas)          # no monitor 2
    assert not mpf.visivel({"x": 3500, "y": 100, "largura": 900}, telas)      # monitor desligado
    assert not mpf.visivel({"x": 100, "y": 1070, "largura": 900}, telas)      # barra de título abaixo da tela
    assert mpf.visivel({"x": 100, "y": 100}, [])                              # sem saber as telas: confia
    assert not mpf.visivel({}, telas)


# ------------------------------------------------------------ janelas destacadas
class _Evento:
    def __init__(self):
        self.funcs = []

    def __iadd__(self, f):
        self.funcs.append(f)
        return self

    def disparar(self, *a):
        for f in self.funcs:
            f(*a)


class _JanelaPywebview:
    def __init__(self, titulo, url, kw):
        self.titulo, self.url, self.kw = titulo, url, kw
        self.js, self.destruida, self.focos = [], False, 0
        self.events = types.SimpleNamespace(moved=_Evento(), resized=_Evento(), maximized=_Evento(),
                                            restored=_Evento(), closed=_Evento())

    def evaluate_js(self, codigo):
        self.js.append(codigo)

    def destroy(self):
        self.destruida = True
        self.events.closed.disparar()

    def restore(self):
        self.focos += 1

    def show(self):
        pass


def _webview_com_janelas(monkeypatch, telas=None):
    criadas = []
    m = sys.modules["webview"]

    def create_window(titulo, url=None, js_api=None, **kw):
        j = _JanelaPywebview(titulo, url, kw)
        criadas.append(j)
        return j
    monkeypatch.setattr(m, "create_window", create_window, raising=False)
    monkeypatch.setattr(m, "screens", lambda: [types.SimpleNamespace(x=x, y=y, width=w, height=h)
                                               for x, y, w, h in (telas or [(0, 0, 1920, 1080)])], raising=False)
    return criadas


def test_abrir_janela_destacada_e_devolver(api, monkeypatch):
    criadas = _webview_com_janelas(monkeypatch)
    api._janela.get_current_url = lambda: "http://127.0.0.1:5555/index.html"
    api.escolher_pasta()
    r = api.abrir_janela("docs")
    assert r["ok"] and len(criadas) == 1
    j = criadas[0]
    assert j.url == "http://127.0.0.1:5555/index.html?janela=docs" and "Documentos" in j.titulo
    assert api.preferencias()["abertas"] == ["docs"]
    assert api.abrir_janela("docs")["ja_aberta"] and j.focos == 1 and len(criadas) == 1   # já aberta: só foca
    assert not api.abrir_janela("projeto")["ok"]
    # eventos do motor vão para todas as janelas
    api._js("eventoDownload", {"x": 1})
    assert any("eventoDownload" in c for c in j.js) and any("eventoDownload" in c for c in api._janela.eventos)
    # uma janela pede à outra que mostre algo, e a traz para a frente
    assert api.janela_chamar("docs", "irPara", ["docs", "abrirPagina", "bruto/a.pdf", 3, ""])["ok"]
    assert j.js[-1] == 'irPara(...["docs", "abrirPagina", "bruto/a.pdf", 3, ""])' and j.focos == 2
    assert not api.janela_chamar("docs", "alert(1);x", [])["ok"]                # só nome de função
    assert not api.janela_chamar("mapa", "irPara", [])["ok"]                   # não está aberta
    # mover e redimensionar: a geometria é guardada (com atraso)
    j.events.moved.disparar(2000, 50)
    j.events.resized.disparar(1000, 700)
    api._salvar_depois["docs"].join(3)
    import time
    time.sleep(1.0)
    assert api._preferencias().ler()["janelas"]["docs"] == {"x": 2000, "y": 50, "largura": 1000, "altura": 700,
                                                         "maximizada": False}
    # fechar a janela devolve a aba (e avisa a principal)
    assert api.fechar_janela("docs")["ok"] and j.destruida
    assert api.janelas_abertas()["abertas"] == [] and api.preferencias()["abertas"] == []
    assert any("janelasMudaram([])" in c for c in api._janela.eventos)


def test_reabrir_o_arranjo_e_fechar_tudo_com_a_principal(api, monkeypatch):
    criadas = _webview_com_janelas(monkeypatch, telas=[(0, 0, 1920, 1080)])
    api._janela.get_current_url = lambda: "http://127.0.0.1:5555/index.html"
    api.salvar_preferencias({"abertas": ["mapa", "perfis"],
                             "janelas": {"mapa": {"x": 100, "y": 80, "largura": 900, "altura": 650},
                                         "perfis": {"x": 4000, "y": 80, "largura": 900, "altura": 650}}})
    r = api.restaurar_janelas()
    assert r["abertas"] == ["mapa", "perfis"] and len(criadas) == 2
    assert criadas[0].kw["x"] == 100 and criadas[0].kw["width"] == 900
    assert "x" not in criadas[1].kw            # o monitor de x = 4000 não existe mais: abre na tela principal
    api._ao_fechar_principal()
    assert all(j.destruida for j in criadas)
    assert api._preferencias().ler()["abertas"] == ["mapa", "perfis"]      # lembra para a próxima vez
    api.salvar_preferencias({"lembrar_arranjo": False})
    api._janelas = {}
    assert api.restaurar_janelas()["abertas"] == []


def test_cores_mudam_em_todas_as_janelas(api, monkeypatch):
    criadas = _webview_com_janelas(monkeypatch)
    api._janela.get_current_url = lambda: "http://127.0.0.1:5555/index.html"
    api.abrir_janela("mapa")
    r = api.salvar_preferencias({"tema": "escuro", "paleta": "arenito"})
    assert r["ok"] and r["preferencias"]["tema"] == "escuro"
    assert any("preferenciasMudaram" in c and '"arenito"' in c for c in criadas[0].js)
    criadas[0].js.clear()
    api.salvar_preferencias({"layout": {"ativa": "docs"}})
    assert not any("preferenciasMudaram" in c for c in criadas[0].js)      # arranjo: não repinta as outras


# ------------------------------------------------------------ abertura, diagnóstico, exportações
def test_abrir_projeto_sozinho_avisa_cada_passo(api):
    assert api.estado()["projeto_aberto"] is False
    r = api.abrir_projeto_padrao()
    assert r["ok"] and api.estado()["projeto_aberto"] and api.estado()["existe_projeto"]
    passos = [c for c in api._janela.eventos if c.startswith("progressoAbertura(")]
    assert len(passos) >= 5 and '"passo": 5' in passos[-1]
    assert api.abrir_projeto_padrao()["ja_aberto"]


def test_diagnostico_com_erros_do_log_e_da_sessao(api, monkeypatch):
    api.escolher_pasta()
    log = os.path.join(api._projeto.pasta, "siapp.log")
    with open(log, "a", encoding="utf-8") as f:
        f.write("2026-10-16 10:44:08,060 ERROR   siapp.ponte: erro inesperado em ver_pagina\n"
                "Traceback (most recent call last):\n  File \"x.py\", line 1\n"
                "pymupdf.mupdf.FzErrorFormat: code=7: unknown image file format\n"
                "2026-10-16 10:45:00,000 INFO    siapp: tudo bem\n")
    api.conectar("Bacia que não existe")
    d = api.diagnostico()
    assert d["ok"] and d["versoes"]["SIAPP"].startswith("0.") and "Python" in d["versoes"]
    assert d["erros_log"][0]["causa"].startswith("pymupdf.mupdf.FzErrorFormat")
    assert any(e["funcao"] == "conectar" for e in d["erros_sessao"])
    assert d["janelas"] == ["principal"]


def test_pastas_de_exportacao(api, monkeypatch):
    abertas = []
    monkeypatch.setattr("ponte.comunidade._abrir_no_sistema", abertas.append)
    api.escolher_pasta()
    os.makedirs(os.path.join(api._projeto.pasta, "exportacoes", "secoes"))
    with open(os.path.join(api._projeto.pasta, "exportacoes", "secoes", "a.csv"), "w") as f:
        f.write("x")
    r = api.pastas_exportacao()
    por = {p["nome"]: p for p in r["pastas"]}
    assert por["exportacoes"]["arquivos"] == 1 and por["exportacoes"]["atualizado"]
    assert not por["sig"]["existe"]
    assert api.abrir_pasta_exportacao("sig")["ok"] and abertas[-1].endswith("sig")
    assert not api.abrir_pasta_exportacao("../fora")["ok"]
