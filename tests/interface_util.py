"""
Janela de teste: abre ui/index.html num Chromium sem tela (Playwright) ligado
à API Python de verdade — o mesmo caminho da janela pywebview, sem o pywebview.

  - window.pywebview.api.<f>(...) no JavaScript chama API.<f>(...) no Python;
  - API._janela.evaluate_js(...) (eventos de download/OCR, status) é enfileirado
    e executado na página por `JanelaTeste.descarregar()`, porque o Playwright só
    aceita comandos da thread principal.

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
  for (const n of nomes) api[n] = (...args) => window.__siapp_chamar(n, JSON.stringify(args)).then(JSON.parse);
  window.pywebview = { api };
  window.dispatchEvent(new Event("pywebviewready"));
}
"""


class _Servidor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        manip = functools.partial(http.server.SimpleHTTPRequestHandler, directory=UI)
        manip.log_message = lambda *a, **k: None
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
    def __init__(self, api, page):
        self.api, self.page = api, page
        self.erros_js: list[str] = []
        page.on("pageerror", lambda e: self.erros_js.append(str(e)))
        page.on("console", lambda m: m.type == "error" and self.erros_js.append(m.text))

    def descarregar(self):
        """Executa na página os eventos que a API mandou (downloads, OCR, status)."""
        while True:
            try:
                codigo = self.api._janela.js.get_nowait()
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


def abrir(api, browser):
    srv = _Servidor()
    srv.start()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    jt = JanelaTeste(api, page)

    def chamar(nome, args_json):
        r = getattr(api, nome)(*json.loads(args_json))
        return json.dumps(r)

    page.expose_function("__siapp_chamar", chamar)
    page.goto(srv.url)
    nomes = [n for n in dir(api) if not n.startswith("_") and callable(getattr(api, n))]
    page.evaluate(PONTE_JS, nomes)
    jt.esperar("document.getElementById('versao').textContent.startsWith('v')")
    return jt, srv
