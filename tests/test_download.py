"""Download com retomada, contra um servidor local que se comporta mal de propósito."""
import http.server
import os
import re
import threading
import time
from urllib.parse import parse_qs, urlparse

import pytest

from motor import reate
from motor.downloads import FilaDownloads

PASTA = "/POCO/C7/7-ANB-9-AL/Perfis_digitais/"
DADOS = {"sft.dlis": os.urandom(3_000_000), "raw.dlis": os.urandom(700_000)}


class Servidor(http.server.BaseHTTPRequestHandler):
    modo = "normal"
    log: list = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        Servidor.log.append({"path": q.get("path", [""])[0], "files": q.get("files", [""])[0],
                             "range": self.headers.get("Range")})
        dados = DADOS.get(q.get("files", [""])[0]) if q.get("path", [""])[0] == PASTA else None
        if dados is None:
            self.send_response(404)
            self.end_headers()
            return
        m = re.match(r"bytes=(\d+)-", self.headers.get("Range") or "")
        ini = int(m.group(1)) if m and Servidor.modo != "ignora_range" else 0
        corpo = dados[ini:]
        if Servidor.modo == "curto":
            corpo = corpo[: len(corpo) // 2]
        self.send_response(206 if ini else 200)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        if Servidor.modo == "corta":            # manda 1/3 e derruba (só na 1ª vez)
            Servidor.modo = "normal"
            self.wfile.write(corpo[: len(corpo) // 3])
            self.wfile.flush()
            self.connection.shutdown(2)
            return
        if Servidor.modo == "lento":
            for i in range(0, len(corpo), 65536):
                try:
                    self.wfile.write(corpo[i:i + 65536])
                    self.wfile.flush()
                except OSError:
                    return
                time.sleep(0.01)
            return
        self.wfile.write(corpo)


@pytest.fixture
def cliente(monkeypatch):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(reate, "URL_DOWNLOAD", f"http://127.0.0.1:{srv.server_address[1]}/index.php/s/{{token}}/download")
    Servidor.modo, Servidor.log = "normal", []
    yield reate.ClienteREATE("TOKEN", pausa_s=0)
    srv.shutdown()


def _baixar(cliente, destino, **kw):
    return cliente.baixar(PASTA + "sft.dlis", str(destino), len(DADOS["sft.dlis"]), **kw)


def _ok(destino):
    return destino.read_bytes() == DADOS["sft.dlis"] and not os.path.exists(str(destino) + ".part")


def test_download_normal_e_parametros(cliente, tmp_path):
    d = tmp_path / "a" / "sft.dlis"
    assert _baixar(cliente, d)["status"] == "baixado" and _ok(d)
    assert Servidor.log[0]["path"] == PASTA and Servidor.log[0]["files"] == "sft.dlis"


def test_arquivo_ja_existente_nao_conecta(cliente, tmp_path):
    d = tmp_path / "sft.dlis"
    _baixar(cliente, d)
    Servidor.log.clear()
    assert _baixar(cliente, d)["status"] == "ja_existia" and not Servidor.log


def test_retoma_de_arquivo_parcial(cliente, tmp_path):
    d = tmp_path / "sft.dlis"
    (tmp_path / "sft.dlis.part").write_bytes(DADOS["sft.dlis"][:1_000_000])
    _baixar(cliente, d)
    assert _ok(d) and Servidor.log[0]["range"] == "bytes=1000000-"


def test_servidor_que_ignora_range_nao_corrompe(cliente, tmp_path):
    d = tmp_path / "sft.dlis"
    (tmp_path / "sft.dlis.part").write_bytes(DADOS["sft.dlis"][:1_000_000])
    Servidor.modo = "ignora_range"
    _baixar(cliente, d)
    assert _ok(d)


def test_conexao_cai_e_retoma(cliente, tmp_path):
    d = tmp_path / "sft.dlis"
    Servidor.modo = "corta"
    _baixar(cliente, d)
    assert _ok(d) and len(Servidor.log) == 2 and Servidor.log[1]["range"]


def test_cancelar_guarda_parcial_e_depois_retoma(cliente, tmp_path):
    d = tmp_path / "sft.dlis"
    Servidor.modo = "lento"
    cancelar = threading.Event()
    with pytest.raises(reate.DownloadCancelado):
        _baixar(cliente, d, cancelar=cancelar,
                progresso=lambda feito, total: feito > 500_000 and cancelar.set())
    assert os.path.getsize(str(d) + ".part") > 500_000 and not d.exists()
    Servidor.modo = "normal"
    _baixar(cliente, d)
    assert _ok(d)


def test_tamanho_errado_e_404_viram_erro(cliente, tmp_path):
    Servidor.modo = "curto"
    with pytest.raises(reate.ErroREATE, match="recebidos"):
        _baixar(cliente, tmp_path / "sft.dlis", tentativas=2)
    Servidor.modo = "normal"
    with pytest.raises(reate.ErroREATE, match="não encontrado"):
        cliente.baixar(PASTA + "nao_existe.dlis", str(tmp_path / "n"), 10)


def test_fila_baixa_registra_e_ignora_repetidos(cliente, tmp_path):
    eventos, registros = [], []

    class Proj:
        def registrar_download(self, *a):
            registros.append(a)

    fila = FilaDownloads(eventos.append)
    tarefas = [{"cliente": cliente, "projeto": Proj(), "bacia": "Alagoas", "poco": "7-ANB-9-AL",
                "caminho": PASTA + n, "nome": n, "tamanho": len(DADOS[n]), "destino": str(tmp_path / n)}
               for n in ("sft.dlis", "raw.dlis")]
    assert fila.adicionar(tarefas)["enfileirados"] == 2
    assert fila.adicionar(tarefas[:1])["ignorados_repetidos"] == 1
    t0 = time.time()
    while not any(e["tipo"] == "ocioso" for e in eventos) and time.time() - t0 < 20:
        time.sleep(0.05)
    tipos = [e["tipo"] for e in eventos if e["tipo"] != "progresso"]
    assert tipos == ["inicio", "fim", "inicio", "fim", "ocioso"]
    assert eventos[-1]["baixados"] == 2 and len(registros) == 2
