"""
OCR num processo separado (0.59).

O OCR do PyMuPDF (Tesseract) não solta a trava global do Python enquanto lê uma página: rodando numa linha de
execução do próprio app, ele parava a janela por segundos a cada página ("Não respondendo"; medido na revisão de
11/11: até 5,4 s). Aqui a leitura roda num processo à parte, do mesmo Python do app (no Windows, o `pythonw.exe` da
`.venv`, sem console): a janela continua respondendo e **Cancelar** é imediato (o processo é encerrado).

Um processo serve a fila inteira (abrir um por documento custaria ~1 s de importações cada) e é encerrado quando a
fila esvazia. Se o processo não puder ser criado, a fila volta a ler na linha de execução, como antes.
"""

from __future__ import annotations

import itertools
import multiprocessing
import queue

from . import registro

_contador = itertools.count(1)


def _trabalhar(entrada, saida):
    """Corpo do processo: lê tarefas (ident, caminho, tessdata, segunda) até receber None."""
    from . import documentos as md
    while True:
        t = entrada.get()
        if t is None:
            return
        ident, caminho, tessdata, segunda = t
        try:
            r = md.processar_arquivo(caminho, tessdata, segunda_passada=segunda,
                                     progresso=lambda p, n, i=ident: saida.put(("pagina", i, p, n)))
            saida.put(("ok", ident, r))
        except md.ErroDocumento as e:
            saida.put(("erro", ident, str(e)))
        except Exception as e:  # noqa: BLE001 — qualquer falha volta como erro do documento, não derruba o processo
            saida.put(("erro", ident, f"{type(e).__name__}: {e}"))


class ProcessoOCR:
    """Um processo trabalhador, criado na primeira tarefa e reaproveitado até `encerrar()`."""

    def __init__(self):
        self._ctx = multiprocessing.get_context("spawn")      # igual no Windows e no Linux (sem fork)
        self._proc = None
        self._entrada = self._saida = None

    @property
    def vivo(self) -> bool:
        return self._proc is not None and self._proc.is_alive()

    def _garantir(self):
        if self.vivo:
            return
        self._entrada, self._saida = self._ctx.Queue(), self._ctx.Queue()
        self._proc = self._ctx.Process(target=_trabalhar, args=(self._entrada, self._saida),
                                       daemon=True, name="siapp-ocr")
        self._proc.start()

    def processar(self, caminho: str, tessdata: str, segunda_passada: bool = True, progresso=None, cancelar=None) -> dict:
        from . import documentos as md
        self._garantir()
        ident = next(_contador)
        self._entrada.put((ident, caminho, tessdata, segunda_passada))
        while True:
            if cancelar is not None and cancelar.is_set():
                self.encerrar(forcar=True)                 # para no meio da página, sem esperar
                raise md.ProcessamentoCancelado()
            try:
                msg = self._saida.get(timeout=0.2)
            except queue.Empty:
                if not self.vivo:
                    self._proc = None
                    raise md.ErroDocumento("O processo do OCR parou no meio do documento (falta de memória?).")
                continue
            tipo, de = msg[0], msg[1]
            if de != ident:                                 # sobra de uma tarefa cancelada
                continue
            if tipo == "pagina":
                if progresso:
                    progresso(msg[2], msg[3])
            elif tipo == "ok":
                return msg[2]
            else:
                raise md.ErroDocumento(msg[2])

    def encerrar(self, forcar: bool = False):
        if self._proc is None:
            return
        try:
            if forcar or not self._proc.is_alive():
                self._proc.terminate()
            else:
                self._entrada.put(None)
            self._proc.join(timeout=5)
            if self._proc.is_alive():
                self._proc.kill()
                self._proc.join(timeout=2)
        except (OSError, ValueError, AttributeError):
            registro.log.exception("OCR: falha ao encerrar o processo")
        finally:
            self._proc = None
