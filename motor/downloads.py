"""
Fila de downloads do SIAPP.

Roda numa thread separada, para a janela continuar respondendo durante
downloads longos. Baixa UM arquivo por vez, com pausa entre eles — o portal
pede explicitamente que não se baixem vários grupos ao mesmo tempo.

Não conhece interface: comunica tudo por eventos, chamando emitir(dict):
    {"tipo": "inicio",    "caminho", "nome", "poco", "indice", "total"}
    {"tipo": "progresso", "caminho", "feito", "total", "velocidade"}  (bytes/s)
    {"tipo": "fim",       "caminho", "status", "bytes", "arquivo_local"}
    {"tipo": "erro",      "caminho", "nome", "erro"}
    {"tipo": "cancelado", "caminho"}
    {"tipo": "ocioso",    "baixados", "ja_existiam", "erros", "cancelados", "bytes"}
"""

from __future__ import annotations

import queue
import threading
import time

from . import reate

INTERVALO_PROGRESSO_S = 0.25    # no máximo 4 atualizações de barra por segundo
PAUSA_ENTRE_ARQUIVOS_S = 0.5    # cortesia com o servidor


class FilaDownloads:
    def __init__(self, emitir):
        self._emitir = emitir
        self._fila: queue.Queue = queue.Queue()
        self._cancelar = threading.Event()
        self._trava = threading.Lock()
        self._thread: threading.Thread | None = None
        self._lote = self._lote_vazio()
        self._na_fila: set[str] = set()     # evita enfileirar o mesmo arquivo duas vezes

    @staticmethod
    def _lote_vazio():
        return {"total": 0, "indice": 0, "baixados": 0, "ja_existiam": 0,
                "erros": 0, "cancelados": 0, "bytes": 0}

    # ----------------------------------------------------------- uso externo
    @property
    def ativa(self) -> bool:
        return self._thread is not None

    def adicionar(self, tarefas: list[dict]) -> dict:
        """
        Cada tarefa: {"cliente": ClienteREATE, "caminho", "nome", "tamanho",
                      "destino", "bacia", "poco", "projeto": Projeto}
        """
        novas = 0
        with self._trava:
            for t in tarefas:
                chave = f"{t['bacia']}:{t['caminho']}"
                if chave in self._na_fila:
                    continue
                self._na_fila.add(chave)
                self._fila.put(t)
                self._lote["total"] += 1
                novas += 1
            if novas and self._thread is None:
                self._cancelar.clear()
                self._thread = threading.Thread(target=self._trabalhar, daemon=True,
                                                name="siapp-downloads")
                self._thread.start()
        return {"enfileirados": novas, "ignorados_repetidos": len(tarefas) - novas}

    def cancelar(self) -> None:
        """Interrompe o arquivo atual (o .part fica para retomar) e esvazia a fila."""
        self._cancelar.set()

    # -------------------------------------------------------------- trabalho
    def _trabalhar(self):
        while True:
            try:
                t = self._fila.get(timeout=0.5)
            except queue.Empty:
                # Decide encerrar SOB A TRAVA: assim, um adicionar() simultâneo
                # ou vê esta thread ainda ativa (e o item é pego no próximo
                # giro), ou vê _thread = None e inicia outra. Nunca fica órfão.
                with self._trava:
                    if not self._fila.empty():
                        continue
                    resumo, self._lote = self._lote, self._lote_vazio()
                    self._cancelar.clear()
                    self._thread = None
                self._emitir({"tipo": "ocioso", **{k: resumo[k] for k in
                              ("baixados", "ja_existiam", "erros", "cancelados", "bytes")}})
                return
            if self._cancelar.is_set():
                self._contar("cancelados")
                self._emitir({"tipo": "cancelado", "caminho": t["caminho"]})
                self._liberar(t)
                continue
            self._baixar_um(t)
            self._liberar(t)
            time.sleep(PAUSA_ENTRE_ARQUIVOS_S)

    def _liberar(self, t):
        with self._trava:
            self._na_fila.discard(f"{t['bacia']}:{t['caminho']}")

    def _contar(self, campo, n=1):
        with self._trava:
            self._lote[campo] += n

    def _baixar_um(self, t):
        with self._trava:
            self._lote["indice"] += 1
            indice, total = self._lote["indice"], self._lote["total"]
        self._emitir({"tipo": "inicio", "caminho": t["caminho"], "nome": t["nome"],
                      "poco": t["poco"], "indice": indice, "total": total,
                      "tamanho": t["tamanho"]})

        inicio = time.monotonic()
        ultimo = [0.0]
        base = [None]

        def progresso(feito, total_bytes):
            agora = time.monotonic()
            if base[0] is None:
                base[0] = feito                       # bytes que já estavam no .part
            if agora - ultimo[0] < INTERVALO_PROGRESSO_S:
                return
            ultimo[0] = agora
            vel = (feito - base[0]) / max(agora - inicio, 1e-6)
            self._emitir({"tipo": "progresso", "caminho": t["caminho"], "feito": feito,
                          "total": total_bytes, "velocidade": vel})

        try:
            r = t["cliente"].baixar(t["caminho"], t["destino"], t["tamanho"],
                                    progresso=progresso, cancelar=self._cancelar)
        except reate.DownloadCancelado:
            self._contar("cancelados")
            self._emitir({"tipo": "cancelado", "caminho": t["caminho"]})
            return
        except reate.ErroREATE as e:
            self._contar("erros")
            self._emitir({"tipo": "erro", "caminho": t["caminho"], "nome": t["nome"], "erro": str(e)})
            return
        except OSError as e:                       # disco cheio, permissão, caminho longo…
            self._contar("erros")
            self._emitir({"tipo": "erro", "caminho": t["caminho"], "nome": t["nome"],
                          "erro": f"Erro ao gravar no disco: {e}"})
            return

        if r["status"] == "baixado":
            self._contar("baixados")
            self._contar("bytes", r["bytes"])
        else:
            self._contar("ja_existiam")
        t["projeto"].registrar_download(t["bacia"], t["poco"], t["caminho"],
                                        t["destino"], r["bytes"])
        self._emitir({"tipo": "fim", "caminho": t["caminho"], "status": r["status"],
                      "bytes": r["bytes"],
                      "arquivo_local": t["destino"]})
