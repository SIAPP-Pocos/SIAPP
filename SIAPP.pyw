"""Lançador silencioso do SIAPP: dois cliques abrem a janelinha de carregamento e, depois, o programa.

Roda com o pythonw (sem console), pelo SIAPP.vbs. O console só aparece no "SIAPP - diagnóstico.bat".
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _avisar(texto):
    """Último recurso quando nem a janelinha abre: caixa de mensagem do Windows."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, texto, "SIAPP", 0x10)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from lancador.janela import main
        main(sys.argv[1:])
    except Exception as e:                                # noqa: BLE001
        _avisar("Não foi possível abrir o SIAPP.\n\n" + repr(e) +
                "\n\nUse o \"SIAPP - diagnóstico.bat\" para ver o detalhe.")
