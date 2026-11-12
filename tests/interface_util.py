"""
Janela de teste: abre ui/index.html num Chromium sem tela (Playwright) ligado
à API Python de verdade — o mesmo caminho da janela pywebview, sem o pywebview.

  - window.pywebview.api.<f>(...) no JavaScript chama API.<f>(...) no Python;
  - API._janela.evaluate_js(...) (eventos de download/OCR, status) é enfileirado. O que chega durante uma
    chamada volta junto com a resposta e roda na página ANTES de a promessa resolver, na ordem do pywebview;
    o que chega depois (linhas de execução em segundo plano) roda em `JanelaTeste.descarregar()`, porque o
    Playwright só aceita comandos da thread principal.

Usado pelos testes marcados com @pytest.mark.interface (pulados se o
Playwright ou o Chromium não estiverem instalados).
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import queue
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(RAIZ, "ui")

PONTE_JS = """
(nomes) => {
  const api = {};
  // Como no pywebview: o que o motor mandou para a página DURANTE a chamada (evaluate_js) roda antes de a
  // promessa resolver (0.59; antes ia para uma fila e rodava depois, o que escondeu o erro E1 da revisão)
  for (const n of nomes) api[n] = (...args) => window.__siapp_chamar(n, JSON.stringify(args)).then((t) => {
    const o = JSON.parse(t);
    for (const c of o.eventos) {
      try { (0, eval)(c); } catch (e) { console.error(`evento do motor falhou: ${e}`); }
    }
    return o.r;
  });
  window.pywebview = { api };
  window.dispatchEvent(new Event("pywebviewready"));
}
"""


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass


class _Servidor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        manip = functools.partial(_Silencioso, directory=UI)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manip)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/index.html"

    def run(self):
        self.httpd.serve_forever()


class JanelaFalsa:
    """Substitui a janela do pywebview dentro da API."""

    def __init__(self, pasta_dialogo):
        self.pasta_dialogo = pasta_dialogo
        self.escolha = None
        self.js: queue.Queue = queue.Queue()

    def create_file_dialog(self, tipo, directory="", **kw):
        if self.escolha is not None:
            return self.escolha
        return (self.pasta_dialogo,)

    def evaluate_js(self, codigo):
        self.js.put(codigo)


class JanelaTeste:
    def __init__(self, api, page, falsa=None):
        self.api, self.page = api, page
        self.falsa = falsa          # a JanelaFalsa desta página (padrão: a principal da API)
        self.erros_js: list[str] = []
        page.on("pageerror", lambda e: self.erros_js.append(str(e)))
        page.on("console", lambda m: m.type == "error" and self.erros_js.append(m.text))

    def descarregar(self):
        """Executa na página os eventos que a API mandou (downloads, OCR, status)."""
        while True:
            try:
                codigo = (self.falsa or self.api._janela).js.get_nowait()
            except queue.Empty:
                return
            self.page.evaluate(f"() => {{ {codigo}; }}")

    def esperar(self, condicao_js: str, timeout_s: float = 20):
        fim = time.time() + timeout_s
        while time.time() < fim:
            self.descarregar()
            if self.page.evaluate(f"() => Boolean({condicao_js})"):
                return
            self.page.wait_for_timeout(100)
        raise AssertionError(f"Condição não atingida em {timeout_s}s: {condicao_js}\n"
                             f"status: {self.page.text_content('#status')}")

    def status(self) -> str:
        return self.page.text_content("#status") or ""


def abrir(api, browser, srv=None, consulta="", falsa=None):
    """Abre a interface num Chromium sem tela. `consulta` ("?janela=docs") e `falsa`
    abrem uma janela destacada, ligada à mesma API (o pywebview faria o mesmo)."""
    if srv is None:
        srv = _Servidor()
        srv.start()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    jt = JanelaTeste(api, page, falsa)
    jt.srv, jt.navegador = srv, browser

    def chamar(nome, args_json):
        r = getattr(api, nome)(*json.loads(args_json))
        fila = (jt.falsa or api._janela).js
        eventos = []
        while True:
            try:
                eventos.append(fila.get_nowait())
            except queue.Empty:
                break
        return json.dumps({"r": r, "eventos": eventos})

    page.expose_function("__siapp_chamar", chamar)
    # mapas de fundo e qualquer outro endereço externo: resposta vazia (sem internet nos testes)
    page.route(lambda url: not url.startswith("http://127.0.0.1"),
               lambda rota: rota.fulfill(status=204, body=""))
    page.goto(srv.url + consulta)
    nomes = [n for n in dir(api) if not n.startswith("_") and callable(getattr(api, n))]
    page.evaluate(PONTE_JS, nomes)
    jt.esperar("document.getElementById('versao').textContent.startsWith('v')")
    # iniciar() termina sempre com uma mensagem: espera a janela acabar de se montar
    jt.esperar("typeof historicoStatus !== 'undefined' && historicoStatus.length > 0")
    return jt, srv


class JanelaDestacadaFalsa(JanelaFalsa):
    """Uma aba em janela própria: o que o motor manda para ela fica na fila desta página."""

    def __init__(self, pasta_dialogo):
        super().__init__(pasta_dialogo)
        self.destruida = False
        self.focada = 0

    def destroy(self):
        self.destruida = True

    def restore(self):
        self.focada += 1

    def show(self):
        pass


def abrir_destacada(jt_principal, aba):
    """Abre a aba `aba` como janela destacada (outra página, mesma API e servidor)."""
    api = jt_principal.api
    falsa = JanelaDestacadaFalsa(api._janela.pasta_dialogo)
    api._janelas[aba] = falsa
    jt, _ = abrir(api, jt_principal.navegador, srv=jt_principal.srv, consulta=f"?janela={aba}", falsa=falsa)
    return jt


def foto(jt, nome: str):
    """Captura da tela em $SIAPP_FOTOS/<nome>.png (para conferir o visual; sem a variável, nada)."""
    pasta = os.environ.get("SIAPP_FOTOS")
    if pasta:
        os.makedirs(pasta, exist_ok=True)
        jt.page.screenshot(path=os.path.join(pasta, nome + ".png"))
