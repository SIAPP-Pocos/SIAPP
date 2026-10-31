"""Janelinha de carregamento do SIAPP (tkinter). Só desenha: a lógica está em `passos.py`."""

from __future__ import annotations

import os
import queue
import sys
import threading

from lancador import passos

APP_ID = "SIAPP.Pocos.SIAPP"        # o mesmo de ponte/icone.py: janelinha e janela principal se agrupam
LARGURA, ALTURA = 460, 250


def definir_identidade() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID) == 0
    except Exception:
        return False


def main(argumentos=()) -> None:
    import tkinter as tk
    from tkinter import ttk

    pasta = passos.pasta_do_app()
    ico = os.path.join(pasta, "recursos", "icone", "siapp.ico")
    versao = passos.ler_versao(pasta)
    definir_identidade()

    raiz = tk.Tk()
    raiz.title("SIAPP")
    raiz.resizable(False, False)
    x, y = (raiz.winfo_screenwidth() - LARGURA) // 2, (raiz.winfo_screenheight() - ALTURA) // 3
    raiz.geometry(f"{LARGURA}x{ALTURA}+{x}+{y}")
    try:
        raiz.iconbitmap(ico)
    except tk.TclError:
        pass

    cabeca = ttk.Frame(raiz, padding=(20, 18, 20, 4))
    cabeca.pack(fill="x")
    png = passos.png_do_ico(ico, 64)
    if png:
        try:
            raiz._img = tk.PhotoImage(data=png)           # guarda a referência, senão some
            if raiz._img.width() > 64:
                raiz._img = raiz._img.subsample(raiz._img.width() // 64)
            ttk.Label(cabeca, image=raiz._img).pack(side="left", padx=(0, 14))
        except tk.TclError:
            pass
    textos = ttk.Frame(cabeca)
    textos.pack(side="left", fill="x")
    ttk.Label(textos, text="SIAPP", font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(textos, text=f"Versão {versao}" if versao else "").pack(anchor="w")

    corpo = ttk.Frame(raiz, padding=(20, 8, 20, 10))
    corpo.pack(fill="both", expand=True)
    passo = tk.StringVar(value=passos.PASSOS[0])
    ttk.Label(corpo, textvariable=passo, wraplength=LARGURA - 40).pack(anchor="w", pady=(0, 8))
    barra = ttk.Progressbar(corpo, length=LARGURA - 40, maximum=len(passos.PASSOS), mode="determinate")
    barra.pack(fill="x")
    erro_txt = tk.StringVar()
    erro_lbl = ttk.Label(corpo, textvariable=erro_txt, wraplength=LARGURA - 40, foreground="#b00020")
    botoes = ttk.Frame(corpo)

    estado = {"detalhe": ""}
    fila: queue.Queue = queue.Queue()

    def copiar():
        raiz.clipboard_clear()
        raiz.clipboard_append(estado["detalhe"])
        raiz.update()
        botao_copiar.config(text="Copiado")

    botao_copiar = ttk.Button(botoes, text="Copiar detalhes", command=copiar)
    botao_copiar.pack(side="left")
    ttk.Button(botoes, text="Fechar", command=raiz.destroy).pack(side="right")

    def progresso(indice, texto, indeterminado):
        fila.put(("passo", indice, texto, indeterminado))

    def trabalho():
        try:
            passos.executar(pasta, progresso, argumentos)
            fila.put(("fim",))
        except BaseException as e:                       # noqa: BLE001 — qualquer falha vira mensagem na janelinha
            detalhe = passos.detalhe_completo(pasta, e)
            passos.registrar(pasta, detalhe)
            msg = e.mensagem if isinstance(e, passos.ErroLancador) else \
                "Algo inesperado aconteceu ao abrir o SIAPP."
            fila.put(("erro", msg, detalhe))

    def vigiar():
        try:
            while True:
                ev = fila.get_nowait()
                if ev[0] == "passo":
                    _, indice, texto, indeterminado = ev
                    passo.set(texto)
                    if indeterminado:
                        barra.config(mode="indeterminate")
                        barra.start(12)
                    else:
                        barra.stop()
                        barra.config(mode="determinate", value=indice)
                elif ev[0] == "fim":
                    raiz.destroy()
                    return
                elif ev[0] == "erro":
                    barra.stop()
                    barra.config(mode="determinate", value=0)
                    passo.set("Não foi possível abrir o SIAPP")
                    erro_txt.set(ev[1])
                    estado["detalhe"] = ev[2]
                    erro_lbl.pack(anchor="w", pady=(10, 6))
                    botoes.pack(fill="x")
                    return
        except queue.Empty:
            pass
        raiz.after(100, vigiar)

    threading.Thread(target=trabalho, name="siapp-lancador", daemon=True).start()
    raiz.after(100, vigiar)
    raiz.mainloop()
