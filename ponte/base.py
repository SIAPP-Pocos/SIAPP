"""
Peças comuns da ponte entre a janela (JavaScript) e o motor (Python).

Regras da ponte:
  - toda função pública devolve um dicionário simples, nunca levanta exceção
    para o JavaScript (decorador `resposta_segura`);
  - nada de lógica de negócio aqui: validar a entrada, chamar o motor,
    devolver o resultado;
  - atributos e métodos que começam com "_" não são expostos à janela.
"""

from __future__ import annotations

import collections
import functools
import json
import ntpath
import os
import sys
import time
from datetime import datetime

from motor import documentos as md
from motor import reate
from motor.registro import filho

log = filho("ponte")

# 0.67: "instalado" = o SIAPP.exe do instalador (PyInstaller). Aí o programa fica numa pasta própria e os dados vão
# para Documentos\SIAPP (ou a pasta de SIAPP_DADOS), que sobrevivem a desinstalar e reinstalar.
INSTALADO = bool(getattr(sys, "frozen", False))
PASTA_APP = getattr(sys, "_MEIPASS", None) if INSTALADO else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pasta_documentos() -> str:
    """Documentos do usuário (a de verdade, mesmo quando o OneDrive a mudou de lugar)."""
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:   # CSIDL_PERSONAL
                return buf.value
        except Exception:  # noqa: BLE001
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


# 1.0: o instalador pergunta onde ficam os projetos e grava a resposta em pasta_dados.txt, ao lado do SIAPP.exe.
ARQUIVO_PASTA_DADOS = "pasta_dados.txt"


def _pasta_escolhida_no_instalador() -> str:
    try:
        with open(os.path.join(os.path.dirname(sys.executable), ARQUIVO_PASTA_DADOS), encoding="utf-8-sig") as f:
            return f.read().strip()
    except OSError:
        return ""


def resolver_pasta_dados(variavel: str, instalado: bool, escolhida: str, documentos: str, pasta_app: str) -> str:
    """Onde ficam os projetos, nesta ordem: a variável SIAPP_DADOS; instalado, a pasta escolhida no instalador (se for
    um caminho completo) ou Documentos\\SIAPP; pelo código, a pasta do clone."""
    if variavel:
        return variavel
    if not instalado:
        return pasta_app
    if escolhida and (os.path.isabs(escolhida) or ntpath.isabs(escolhida)):
        return escolhida
    return os.path.join(documentos, "SIAPP")


PASTA_DADOS = resolver_pasta_dados(os.environ.get("SIAPP_DADOS", ""), INSTALADO,
                                   _pasta_escolhida_no_instalador() if INSTALADO else "",
                                   _pasta_documentos() if INSTALADO else "", PASTA_APP)

# O projeto principal mora SEMPRE nesta pasta: ao lado do aplicativo (pasta clonada do GitHub) ou, instalado, na pasta
# escolhida no instalador (padrão: Documentos\SIAPP). Outros projetos ficam em <PASTA_DADOS>\projetos.
# 1.1: instalado, o usuário vê pastas com nome de usuário: <pasta dos projetos>\Projetos\Projeto principal (e os outros
# projetos ao lado, em Projetos\). Pelo código (desenvolvimento e testes), continua ambiente_teste\ e projetos\.
PASTA_PROJETOS_INSTALADO = "Projetos"
NOME_PRINCIPAL_INSTALADO = "Projeto principal"
NOME_PASTA_PROJETO = NOME_PRINCIPAL_INSTALADO if INSTALADO else "ambiente_teste"
PASTA_PROJETO = (os.path.join(PASTA_DADOS, PASTA_PROJETOS_INSTALADO, NOME_PRINCIPAL_INSTALADO) if INSTALADO
                 else os.path.join(PASTA_DADOS, NOME_PASTA_PROJETO))


def migrar_pastas_antigas(dados: str = PASTA_DADOS) -> list[str]:
    """1.1: quem instalou a 1.0 (ou escolheu uma pasta de antes) tem <dados>\\ambiente_teste e <dados>\\projetos\\*.
    Passa para <dados>\\Projetos\\Projeto principal e <dados>\\Projetos\\* e corrige os caminhos guardados nas
    preferências. Só move o que não colide; devolve o que fez. Erro (arquivo aberto, sem permissão) = deixa como está."""
    feito = []
    raiz = os.path.join(dados, PASTA_PROJETOS_INSTALADO)
    antigo = os.path.join(dados, "ambiente_teste")
    novo = os.path.join(raiz, NOME_PRINCIPAL_INSTALADO)
    trocas = []
    try:
        if os.path.isfile(os.path.join(antigo, "siapp.json")) and not os.path.exists(novo):
            os.makedirs(raiz, exist_ok=True)
            os.rename(antigo, novo)
            trocas.append((antigo, novo))
            feito.append(f"{antigo} → {novo}")
        velhos = os.path.join(dados, "projetos")
        if os.path.isdir(velhos):
            for nome in sorted(os.listdir(velhos)):
                de, para = os.path.join(velhos, nome), os.path.join(raiz, nome)
                if os.path.isdir(de) and not os.path.exists(para):
                    os.makedirs(raiz, exist_ok=True)
                    os.rename(de, para)
                    trocas.append((de, para))
                    feito.append(f"{de} → {para}")
            if not os.listdir(velhos):
                os.rmdir(velhos)
    except OSError:
        return feito
    if trocas:
        _corrigir_preferencias(os.path.join(novo, "preferencias.json"), trocas)
    return feito


def _corrigir_preferencias(caminho: str, trocas: list) -> None:
    import json
    try:
        with open(caminho, encoding="utf-8") as f:
            prefs = json.load(f)
    except (OSError, ValueError):
        return

    def trocar(p):
        if not isinstance(p, str) or not p:
            return p
        for de, para in trocas:
            if os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(de)):
                return "" if para.endswith(NOME_PRINCIPAL_INSTALADO) else para
        return p
    prefs["projeto_atual"] = trocar(prefs.get("projeto_atual", ""))
    prefs["projetos"] = [x for x in (trocar(p) for p in prefs.get("projetos", []) or []) if x]
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
PASTA_RECURSOS = os.path.join(PASTA_APP, "recursos")
# Modelo de idioma do OCR: baixado uma vez (instalado: junto dos dados, para não se perder ao reinstalar).
PASTA_TESSDATA = os.path.join(PASTA_DADOS if INSTALADO else PASTA_APP, "recursos", "tessdata")
# Dicionário de domínio que vem com o SIAPP (editável; ver motor/vocabulario.py).
CAMINHO_VOCAB_BASE = os.path.join(PASTA_RECURSOS, "vocabulario_base.json")


class ErroUsuario(ValueError):
    """Pedido inválido vindo da janela: a mensagem vai direto para a tela."""


def mesma_pasta(a: str, b: str) -> bool:
    """Compara caminhos ignorando maiúsculas/minúsculas e barras (Windows)."""
    def norm(p):
        return os.path.normcase(os.path.normpath(os.path.abspath(p)))
    return norm(a) == norm(b)


# Erros esperados: a mensagem já foi escrita para o usuário.
ERROS_ESPERADOS = (reate.ErroREATE, md.ErroDocumento, NotADirectoryError, ValueError)


# Últimas chamadas da janela (nome, duração, resultado), para a tela de Diagnóstico.
CHAMADAS: collections.deque = collections.deque(maxlen=300)


def _anotar(nome: str, inicio: float, ok: bool, erro: str = ""):
    CHAMADAS.append({"quando": datetime.now().isoformat(timespec="seconds"), "funcao": nome,
                     "ms": round((time.perf_counter() - inicio) * 1000), "ok": ok, "erro": erro[:300]})


def resposta_segura(func):
    """Toda chamada vinda da interface devolve {"ok": True, ...} ou
    {"ok": False, "erro": "..."} — nunca deixa uma exceção estourar no JS.
    Erros inesperados vão completos para o siapp.log."""
    @functools.wraps(func)
    def envelope(*args, **kwargs):
        inicio = time.perf_counter()
        try:
            r = {"ok": True, **(func(*args, **kwargs) or {})}
            _anotar(func.__name__, inicio, True)
            return r
        except ERROS_ESPERADOS as e:
            log.info("%s recusado: %s", func.__name__, e)
            _anotar(func.__name__, inicio, False, str(e))
            return {"ok": False, "erro": str(e)}
        except Exception as e:  # erro inesperado: mensagem curta na tela, detalhe no log
            log.exception("erro inesperado em %s", func.__name__)
            _anotar(func.__name__, inicio, False, f"{type(e).__name__}: {e}")
            return {"ok": False, "erro": f"Erro inesperado ({type(e).__name__}): {e}. "
                                         f"Detalhes em ambiente_teste\\siapp.log."}
    return envelope


def _carregada(janela) -> bool:
    eventos = getattr(janela, "events", None)
    carregou = getattr(eventos, "loaded", None)
    return carregou is None or not hasattr(carregou, "is_set") or carregou.is_set()


class BaseAPI:
    """Estado compartilhado por todas as partes da ponte."""

    _janela = None
    _projeto = None

    def _janelas_abertas(self) -> list:
        """A principal e as abas destacadas que já carregaram (evaluate_js numa janela que
        ainda carrega esperaria até 15 s e travaria quem chamou)."""
        extras = [j for j in (getattr(self, "_janelas", None) or {}).values() if _carregada(j)]
        return [j for j in [self._janela, *extras] if j is not None]

    def _js(self, funcao: str, dados) -> None:
        """Chama uma função global em TODAS as janelas (a principal e as abas destacadas):
        cada uma mostra o que lhe cabe. Janela que já fechou é ignorada — o trabalho em
        segundo plano nunca quebra por causa da interface."""
        codigo = f"{funcao}({json.dumps(dados)})"
        for janela in self._janelas_abertas():
            try:
                janela.evaluate_js(codigo)
            except Exception:
                pass

    def _status(self, texto: str):
        """Atualiza a barra de status das janelas durante operações longas."""
        self._js_status(texto, "trab")

    def _js_status(self, texto: str, tipo: str):
        codigo = f"status({json.dumps(texto)}, {json.dumps(tipo)})"
        for janela in self._janelas_abertas():
            try:
                janela.evaluate_js(codigo)
            except Exception:
                pass

    def _autor(self) -> str:
        """Nome de quem usa este computador (aba Comunidade), para a autoria
        de correções e fatos. Vazio se não preenchido."""
        if self._projeto is None:
            return ""
        return (self._projeto.config.get("autor") or {}).get("nome", "")

    def _exigir_projeto(self):
        if self._projeto is None:
            raise ErroUsuario("Abra primeiro o projeto (Início).")
