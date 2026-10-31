"""Lógica do lançador silencioso do SIAPP (0.47).

O lançador roda no Python do sistema, antes de a `.venv` existir, por isso aqui só entra a biblioteca padrão.
Tudo que é decisão (qual Python serve, a `.venv` funciona, o que mostrar quando algo falha) está neste módulo e é
testado fora do Windows; a janelinha (`janela.py`) só desenha o que este módulo informa.

Lições herdadas do `iniciar.bat` (Vault, "Decisões e Armadilhas" 2.13):
- neste computador, "python" no PATH é uma cópia quebrada do MySQL Shell: nunca se chama "python" puro;
- o Python 3.13 da Microsoft Store funciona pelo "py";
- se a pasta foi movida ou renomeada, a `.venv` antiga deixa de funcionar e é recriada.
"""

from __future__ import annotations

import glob
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import traceback
from datetime import datetime

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PASSOS = ("Conferindo os arquivos", "Preparando os componentes", "Abrindo o projeto")
DICA_PRIMEIRA_VEZ = "Preparando os componentes — na primeira vez leva alguns minutos"
VARIAVEL_SINAL = "SIAPP_SINAL"
ARQUIVOS_OBRIGATORIOS = ("siapp.py", "requirements.txt", os.path.join("motor", "__init__.py"),
                         os.path.join("ui", "index.html"))
# O que um Python precisa ter para criar a .venv do SIAPP.
VERIFICACAO_PYTHON = "import sys, venv, ensurepip; sys.exit(0 if sys.version_info >= (3, 9) else 1)"


class ErroLancador(Exception):
    """Falha esperada: `mensagem` vai para a janelinha em português simples; `detalhe` vai para o log."""

    def __init__(self, mensagem: str, detalhe: str = ""):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhe = detalhe


# ---------------------------------------------------------------------------------------------- arquivos e log

def pasta_do_app() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ler_versao(pasta: str) -> str:
    try:
        with open(os.path.join(pasta, "motor", "__init__.py"), encoding="utf-8") as f:
            m = re.search(r'__version__\s*=\s*"([^"]+)"', f.read())
        return m.group(1) if m else ""
    except OSError:
        return ""


def caminho_log(pasta: str) -> str:
    return os.path.join(pasta, "ambiente_teste", "lancador.log")


def caminho_saida_app(pasta: str) -> str:
    return os.path.join(pasta, "ambiente_teste", "siapp-saida.log")


def caminho_sinal(pasta: str) -> str:
    return os.path.join(pasta, "ambiente_teste", ".abriu")


def registrar(pasta: str, texto: str) -> None:
    """Acrescenta ao log do lançador. Nunca levanta exceção: o log não pode impedir nada."""
    try:
        caminho = caminho_log(pasta)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {texto}\n")
    except OSError:
        pass


def conferir_arquivos(pasta: str) -> None:
    faltam = [a for a in ARQUIVOS_OBRIGATORIOS if not os.path.isfile(os.path.join(pasta, a))]
    if faltam:
        raise ErroLancador("Faltam arquivos do SIAPP nesta pasta. Baixe o SIAPP de novo (ou rode git pull).",
                           "Arquivos ausentes: " + ", ".join(faltam))


# ------------------------------------------------------------------------------------------ subprocessos ocultos

def ambiente_limpo() -> dict:
    """Variáveis que fazem qualquer Python procurar a biblioteca no lugar errado ficam de fora."""
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def rodar(cmd, cwd=None, timeout=None):
    """Roda um comando sem abrir janela de console e devolve o resultado com a saída em texto."""
    return subprocess.run(cmd, cwd=cwd, timeout=timeout, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ambiente_limpo(), creationflags=SEM_JANELA)


# ------------------------------------------------------------------------------------------------- achar Python

def _windowsapps() -> str:
    base = os.environ.get("LOCALAPPDATA", "")
    return os.path.normcase(os.path.join(base, "Microsoft", "WindowsApps")) if base else ""


def python_serve(caminho: str, executar=None) -> bool:
    """True se o executável existe, não é o MySQL Shell nem o atalho da loja, e consegue criar uma .venv."""
    executar = executar or rodar
    if not caminho or not os.path.isfile(caminho) or "mysql" in caminho.lower():
        return False
    pasta = os.path.normcase(os.path.dirname(os.path.abspath(caminho)))
    if _windowsapps() and pasta == _windowsapps():            # o atalho da loja só abre a loja
        return False
    try:
        return executar([caminho, "-c", VERIFICACAO_PYTHON]).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def candidatos_python(executar=None):
    """Caminhos de Python para tentar, do mais confiável ao menos (sem repetir)."""
    executar = executar or rodar
    vistos, saida = set(), []

    def somar(c):
        c = (c or "").strip().strip('"')
        chave = os.path.normcase(c)
        if c and chave not in vistos:
            vistos.add(chave)
            saida.append(c)

    pasta_exe = os.path.dirname(sys.executable or "")
    somar(os.path.join(pasta_exe, "python.exe"))               # o Python que está rodando o lançador
    try:
        r = executar(["py", "-3", "-c", "import sys; print(sys.executable)"])
        if r.returncode == 0:
            for linha in r.stdout.splitlines():
                somar(linha)
    except (OSError, subprocess.SubprocessError):
        pass
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        for padrao in (os.path.join(local, "Programs", "Python", "Python3*", "python.exe"),
                       os.path.join(local, "Microsoft", "WindowsApps", "PythonSoftwareFoundation.Python.3*",
                                    "python.exe")):
            for c in sorted(glob.glob(padrao), reverse=True):
                somar(c)
    try:
        r = executar(["where", "python"])
        if r.returncode == 0:
            for linha in r.stdout.splitlines():
                somar(linha)
    except (OSError, subprocess.SubprocessError):
        pass
    return saida


def achar_python(candidatos, serve=python_serve):
    """Primeiro candidato que serve. Devolve (caminho ou None, lista de "ok/falhou  caminho")."""
    tentativas = []
    for c in candidatos:
        if serve(c):
            tentativas.append(f"ok        {c}")
            return c, tentativas
        tentativas.append(f"falhou    {c}")
    return None, tentativas


# ------------------------------------------------------------------------------------------------------ .venv

def _subpasta_scripts() -> str:
    return "Scripts" if sys.platform == "win32" else "bin"


def venv_dir(pasta: str) -> str:
    return os.path.join(pasta, ".venv")


def venv_python(pasta: str) -> str:
    return os.path.join(venv_dir(pasta), _subpasta_scripts(), "python.exe" if sys.platform == "win32" else "python")


def venv_pythonw(pasta: str) -> str:
    """O pythonw.exe não abre console. Fora do Windows (só testes) cai no python comum."""
    w = os.path.join(venv_dir(pasta), _subpasta_scripts(), "pythonw.exe")
    return w if os.path.isfile(w) or sys.platform == "win32" else venv_python(pasta)


def venv_funciona(pasta: str, executar=None) -> bool:
    """A .venv existe e o pip dela roda (se a pasta foi movida ou renomeada, não roda)."""
    executar = executar or rodar
    py = venv_python(pasta)
    if not os.path.isfile(py):
        return False
    try:
        return executar([py, "-m", "pip", "--version"]).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _marca_requisitos(pasta: str) -> str:
    with open(os.path.join(pasta, "requirements.txt"), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def _arquivo_marca(pasta: str) -> str:
    return os.path.join(venv_dir(pasta), ".requisitos")


def requisitos_em_dia(pasta: str) -> bool:
    try:
        with open(_arquivo_marca(pasta), encoding="utf-8") as f:
            return f.read().strip() == _marca_requisitos(pasta)
    except OSError:
        return False


def _cauda(texto: str, linhas: int = 30) -> str:
    return "\n".join((texto or "").strip().splitlines()[-linhas:])


def preparar_ambiente(pasta: str, progresso, executar=None, candidatos=None) -> None:
    """Garante uma .venv que funciona e com as dependências em dia. `progresso(texto, indeterminado)`."""
    executar = executar or rodar
    if not venv_funciona(pasta, executar):
        primeira_vez = not os.path.exists(venv_dir(pasta))
        progresso(DICA_PRIMEIRA_VEZ if primeira_vez else "Refazendo os componentes — leva alguns minutos", True)
        if os.path.exists(venv_dir(pasta)):
            registrar(pasta, ".venv existente não funciona; será recriada")
            shutil.rmtree(venv_dir(pasta), ignore_errors=True)
            if os.path.exists(venv_dir(pasta)):
                raise ErroLancador("Não consegui apagar a pasta .venv antiga. Feche outros programas do SIAPP e "
                                   "tente de novo.", venv_dir(pasta))
        lista = candidatos if candidatos is not None else candidatos_python(executar)
        base, tentativas = achar_python(lista, lambda c: python_serve(c, executar))
        registrar(pasta, "Procura de Python:\n  " + "\n  ".join(tentativas or ["(nenhum candidato)"]))
        if not base:
            raise ErroLancador("Não encontrei um Python 3.9 ou mais novo neste computador. Instale o Python "
                               "(Microsoft Store ou python.org) e abra o SIAPP de novo.",
                               "Candidatos testados:\n" + "\n".join(tentativas))
        r = executar([base, "-m", "venv", venv_dir(pasta)])
        if r.returncode != 0 or not os.path.isfile(venv_python(pasta)):
            raise ErroLancador("Não consegui criar o ambiente do SIAPP.",
                               f"Python usado: {base}\n{_cauda(r.stdout)}\n{_cauda(r.stderr)}")
    if not requisitos_em_dia(pasta):
        progresso(DICA_PRIMEIRA_VEZ, True)
        r = executar([venv_python(pasta), "-m", "pip", "install", "-r", "requirements.txt",
                      "--disable-pip-version-check", "--no-input"], cwd=pasta)
        if r.returncode != 0:
            raise ErroLancador("Não consegui instalar os componentes do SIAPP. Confira a internet e tente de "
                               "novo; se persistir, use \"Copiar detalhes\" e envie para análise.",
                               f"Python da .venv: {venv_python(pasta)}\n{_cauda(r.stdout)}\n{_cauda(r.stderr)}")
        try:
            with open(_arquivo_marca(pasta), "w", encoding="utf-8") as f:
                f.write(_marca_requisitos(pasta))
        except OSError:
            pass


# ----------------------------------------------------------------------------------------------- abrir o app

def abrir_app(pasta: str, argumentos=()):
    """Abre o siapp.py com o pythonw da .venv (sem console). Devolve (processo, caminho do arquivo-sinal)."""
    sinal = caminho_sinal(pasta)
    try:
        os.remove(sinal)
    except OSError:
        pass
    env = ambiente_limpo()
    env[VARIAVEL_SINAL] = sinal
    saida_log = caminho_saida_app(pasta)
    os.makedirs(os.path.dirname(saida_log), exist_ok=True)
    with open(saida_log, "w", encoding="utf-8") as saida:           # o que o app imprimir/errar fica aqui
        proc = subprocess.Popen([venv_pythonw(pasta), os.path.join(pasta, "siapp.py"), *argumentos], cwd=pasta,
                                env=env, stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT,
                                creationflags=SEM_JANELA)
    return proc, sinal


def esperar_abertura(proc, sinal: str, pasta: str, limite: float = 180.0, dormir=time.sleep,
                     agora=time.monotonic) -> bool:
    """Espera o SIAPP avisar que a janela principal abriu. True = abriu; False = fechou sem erro."""
    fim = agora() + limite
    while agora() < fim:
        if os.path.exists(sinal):
            return True
        codigo = proc.poll()
        if codigo is not None:
            if os.path.exists(sinal):
                return True
            if codigo == 0:
                return False
            try:
                with open(caminho_saida_app(pasta), encoding="utf-8", errors="replace") as f:
                    saida = _cauda(f.read())
            except OSError:
                saida = ""
            raise ErroLancador("O SIAPP fechou ao abrir. Use \"Copiar detalhes\" e envie para análise.",
                               f"Código de saída: {codigo}\n{saida}")
        dormir(0.2)
    raise ErroLancador("O SIAPP está demorando demais para abrir.", f"Sem sinal de abertura em {limite:.0f} s.")


def avisar_abertura() -> bool:
    """Chamado pelo próprio SIAPP quando a janela principal aparece: avisa o lançador. Nunca falha."""
    caminho = os.environ.get(VARIAVEL_SINAL)
    if not caminho:
        return False
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("ok")
        return True
    except OSError:
        return False


# -------------------------------------------------------------------------------------------------- orquestra

def executar(pasta: str, progresso, argumentos=(), executar_cmd=None, candidatos=None) -> bool:
    """Roda os três passos. `progresso(indice, texto, indeterminado)`; levanta ErroLancador se algo falhar."""
    total = len(PASSOS)
    progresso(0, PASSOS[0], False)
    conferir_arquivos(pasta)
    progresso(1, PASSOS[1], True)
    preparar_ambiente(pasta, lambda texto, ind: progresso(1, texto, ind), executar_cmd, candidatos)
    progresso(2, PASSOS[2], True)
    proc, sinal = abrir_app(pasta, argumentos)
    abriu = esperar_abertura(proc, sinal, pasta)
    progresso(total, "Pronto", False)
    return abriu


def detalhe_completo(pasta: str, erro: BaseException) -> str:
    """Texto para o log e para "Copiar detalhes"."""
    partes = [f"SIAPP {ler_versao(pasta) or '?'} — {datetime.now():%Y-%m-%d %H:%M:%S}",
              f"Windows/plataforma: {sys.platform}", f"Python do lançador: {sys.version.split()[0]} ({sys.executable})",
              f"Pasta: {pasta}"]
    if isinstance(erro, ErroLancador):
        partes += ["", erro.mensagem]
        if erro.detalhe:
            partes += ["", erro.detalhe]
    else:
        partes += ["", "Erro inesperado: " + repr(erro), "", "".join(traceback.format_exception(type(erro), erro, erro.__traceback__)).strip()]
    partes += ["", f"Mais detalhes: {caminho_log(pasta)}"]
    return "\n".join(partes)


# --------------------------------------------------------------------------------------------------- ícone

def png_do_ico(caminho: str, lado: int = 64) -> bytes | None:
    """PNG de uma das entradas do .ico (a menor com pelo menos `lado` px; senão a maior)."""
    try:
        with open(caminho, "rb") as f:
            dados = f.read()
        _, tipo, n = struct.unpack_from("<HHH", dados, 0)
        if tipo != 1:
            return None
        entradas = []
        for i in range(n):
            w, _h, _, _, _, _, tam, off = struct.unpack_from("<BBBBHHII", dados, 6 + 16 * i)
            png = dados[off:off + tam]
            if png[:8] == b"\x89PNG\r\n\x1a\n":
                entradas.append((w or 256, png))
        if not entradas:
            return None
        maiores = sorted(e for e in entradas if e[0] >= lado)
        return (maiores[0] if maiores else max(entradas))[1]
    except (OSError, struct.error):
        return None
