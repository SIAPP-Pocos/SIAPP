"""Ponte: janelas, preferências, diagnóstico e pastas de exportação.

Janelas
    A janela principal tem as abas. Qualquer aba pode ir para uma janela própria do
    Windows (`abrir_janela`), que o usuário põe em outro monitor, maximiza e encaixa
    como qualquer programa. Todas as janelas falam com o MESMO motor (esta API): os
    eventos de download, OCR e status vão para todas (`BaseAPI._js`), e uma janela pede
    a outra que mostre algo com `janela_chamar` (ex.: o Mapa manda a janela de
    Documentos abrir os documentos de um poço). Fechar a janela devolve a aba.
    Posição, tamanho e quais abas estavam destacadas ficam nas preferências e voltam
    na próxima vez (se a tela ainda existir; senão a janela abre na tela principal).
"""

from __future__ import annotations

import json
import os
import platform
import re
import threading
from datetime import datetime

from motor import preferencias as mpf
from motor import projeto as mp

from . import base, icone
from .base import ErroUsuario, resposta_segura

NOMES_ABAS = {"projeto": "Projeto", "dados": "Dados", "mapa": "Mapa", "docs": "Documentos",
              "perfis": "Perfis", "interp": "Interpretação", "viab": "Viabilidade",
              "comunidade": "Comunidade"}
_FUNCAO_JS = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,60}$")

# Pastas que o SIAPP preenche com o que exporta (aba Projeto e botão Exportações).
PASTAS_EXPORTACAO = [
    ("exportacoes", "CSV, LAS e figuras das abas (curvas, levantamento, produção, seções, blocos)"),
    ("execucoes", "cada seção, bloco 3D e viabilidade calculados, com a memória de cálculo"),
    ("sig", "camadas geográficas em GeoJSON e shapefile, para o QGIS"),
    ("contribuicoes", "pacotes para a base comunitária"),
]


class JanelasAPI:
    _janelas: dict = {}
    _prefs = None
    _salvar_depois: dict = {}

    # ------------------------------------------------------------ preferências
    def _preferencias(self) -> mpf.Preferencias:
        if self._prefs is None or os.path.dirname(self._prefs.caminho) != base.PASTA_PROJETO:
            self._prefs = mpf.Preferencias(base.PASTA_PROJETO)
        return self._prefs

    @resposta_segura
    def marca_dados(self):
        """Marca de mudança da pasta do projeto: a janela só recarrega uma aba quando ela muda (0.61)."""
        p = getattr(self, "_projeto", None)
        return {"marca": p.marca() if p is not None else ""}

    @resposta_segura
    def preferencias(self):
        return {"preferencias": self._preferencias().ler(), "paletas": list(mpf.PALETAS),
                "abertas": sorted(self._janelas)}

    @resposta_segura
    def salvar_preferencias(self, mudancas: dict):
        if not isinstance(mudancas, dict):
            raise ErroUsuario("Preferências em formato inválido.")
        p = self._preferencias().atualizar(mudancas)
        if any(k in mudancas for k in ("paleta", "tema", "fonte")):
            self._js("preferenciasMudaram", p)     # todas as janelas mudam de cor juntas
        return {"preferencias": p}

    # ------------------------------------------------------------ janelas

    def _telas(self) -> list:
        try:
            import webview
            telas = getattr(webview, "screens", None)
            telas = telas() if callable(telas) else telas
            return [(s.x, s.y, s.width, s.height) for s in (telas or [])]
        except Exception:
            return []

    def _kwargs_geometria(self, g: dict, padrao=(1100, 720)) -> dict:
        kw = {"width": g.get("largura", padrao[0]), "height": g.get("altura", padrao[1])}
        if mpf.visivel(g, self._telas()):
            kw["x"], kw["y"] = g["x"], g["y"]
        if g.get("maximizada"):
            kw["maximized"] = True
        return kw

    def _vigiar_geometria(self, janela, chave: str):
        """Guarda posição e tamanho da janela (com atraso: arrastar gera dezenas de eventos)."""
        estado = {}

        def gravar():
            g = dict(estado)
            if chave == "principal":
                self._preferencias().atualizar({"principal": g})
            else:
                self._preferencias().atualizar({"janelas": {chave: g}})

        def agendar():
            t = self._salvar_depois.get(chave)
            if t:
                t.cancel()
            t = threading.Timer(0.8, gravar)
            t.daemon = True
            self._salvar_depois[chave] = t
            t.start()

        def movida(x, y):
            estado.update(x=int(x), y=int(y), maximizada=False)
            agendar()

        def redimensionada(largura, altura):
            estado.update(largura=int(largura), altura=int(altura))
            agendar()

        def maximizada():
            estado["maximizada"] = True
            agendar()

        def restaurada():
            estado["maximizada"] = False
            agendar()
        try:
            janela.events.moved += movida
            janela.events.resized += redimensionada
            janela.events.maximized += maximizada
            janela.events.restored += restaurada
        except AttributeError:
            pass

    def _url_base(self) -> str:
        """Endereço da interface que a janela principal está mostrando (servidor local)."""
        url = ""
        try:
            url = self._janela.get_current_url() or ""
        except Exception:
            pass
        if not url.startswith("http"):
            url = os.path.join(base.PASTA_APP, "ui", "index.html")
        return url.split("?")[0].split("#")[0]

    @resposta_segura
    def abrir_janela(self, aba: str):
        """Abre a aba numa janela própria (ou traz a janela para a frente, se já existe)."""
        if aba not in NOMES_ABAS or aba == "projeto":
            raise ErroUsuario("Esta aba não abre em janela própria.")
        if aba in self._janelas:
            self._focar(self._janelas[aba])
            return {"aba": aba, "ja_aberta": True}
        import webview
        g = self._preferencias().ler()["janelas"].get(aba, {})
        janela = webview.create_window(
            f"SIAPP — {NOMES_ABAS[aba]}", url=f"{self._url_base()}?janela={aba}", js_api=self,
            min_size=(640, 420), **self._kwargs_geometria(g))
        self._janelas[aba] = janela
        self._vigiar_geometria(janela, aba)
        from ponte import icone
        icone.aplicar(janela)
        try:
            janela.events.closed += lambda: self._janela_fechou(aba)
        except AttributeError:
            pass
        self._salvar_abertas()
        self._js("janelasMudaram", sorted(self._janelas))
        return {"aba": aba}

    def _janela_fechou(self, aba: str):
        if self._janelas.pop(aba, None) is None:
            return
        if not getattr(self, "_saindo", False):
            self._salvar_abertas()
        self._js("janelasMudaram", sorted(self._janelas))

    def _salvar_abertas(self):
        self._preferencias().atualizar({"abertas": sorted(self._janelas)})

    @resposta_segura
    def fechar_janela(self, aba: str):
        j = self._janelas.get(aba)
        if j is not None:
            try:
                j.destroy()
            finally:
                self._janela_fechou(aba)
        return {"aba": aba}

    @resposta_segura
    def janelas_abertas(self):
        return {"abertas": sorted(self._janelas)}

    @resposta_segura
    def restaurar_janelas(self):
        """Reabre as abas que estavam em janela própria (se "lembrar o arranjo" estiver ligado)."""
        p = self._preferencias().ler()
        abertas = []
        if p["lembrar_arranjo"]:
            for aba in p["abertas"]:
                if aba not in self._janelas and self.abrir_janela(aba).get("ok"):
                    abertas.append(aba)
        return {"abertas": abertas}

    def _focar(self, janela):
        for metodo in ("restore", "show"):
            try:
                getattr(janela, metodo)()
            except Exception:
                pass

    @resposta_segura
    def janela_chamar(self, alvo: str, funcao: str, args: list | None = None):
        """Executa uma função da interface em outra janela e traz essa janela para a frente.
        `alvo`: a aba destacada, ou "principal"."""
        if not _FUNCAO_JS.match(funcao or ""):
            raise ErroUsuario("Função inválida.")
        janela = self._janelas.get(alvo) if alvo != "principal" else self._janela
        if janela is None:
            raise ErroUsuario(f"A janela {NOMES_ABAS.get(alvo, alvo)} não está aberta.")
        args = list(args or [])
        janela.evaluate_js(f"{funcao}(...{json.dumps(args)})")
        self._focar(janela)
        return {"alvo": alvo}

    def _ao_fechar_principal(self):
        """Fechar a janela principal fecha o SIAPP inteiro (e lembra o que estava destacado)."""
        self._saindo = True
        self._salvar_abertas()
        for j in list(self._janelas.values()):
            try:
                j.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------ projeto
    @resposta_segura
    def estado(self):
        """O que uma janela recém-aberta precisa saber para se montar."""
        return {"projeto_aberto": self._projeto is not None,
                "pasta": self._projeto.pasta if self._projeto else "",
                "existe_projeto": os.path.isfile(os.path.join(self._projeto_inicial(), mp.ARQUIVO_CONFIG)),
                "abertas": sorted(self._janelas)}

    @resposta_segura
    def abrir_projeto_padrao(self):
        """Abre a pasta do projeto sem o diálogo (preferência "abrir ao iniciar")."""
        if self._projeto is not None:
            return {"pasta": self._projeto.pasta, "ja_aberto": True}
        pasta = self._projeto_inicial()        # o último projeto escolhido (0.58), ou o ambiente_teste
        os.makedirs(pasta, exist_ok=True)
        return self._abrir_projeto(pasta)

    def _progresso_abertura(self, passo: int, total: int, texto: str):
        self._js("progressoAbertura", {"passo": passo, "total": total, "texto": texto})

    # ------------------------------------------------------------ exportações
    @resposta_segura
    def pastas_exportacao(self):
        self._exigir_projeto()
        out = []
        for nome, desc in PASTAS_EXPORTACAO:
            caminho = os.path.join(self._projeto.pasta, nome)
            n, recente = 0, 0.0
            if os.path.isdir(caminho):
                for raiz, _, arqs in os.walk(caminho):
                    for a in arqs:
                        n += 1
                        try:
                            recente = max(recente, os.path.getmtime(os.path.join(raiz, a)))
                        except OSError:
                            pass
            out.append({"nome": nome, "descricao": desc, "existe": os.path.isdir(caminho), "arquivos": n,
                        "atualizado": datetime.fromtimestamp(recente).isoformat(timespec="minutes") if recente else ""})
        return {"pastas": out}

    @resposta_segura
    def abrir_pasta_exportacao(self, nome: str):
        self._exigir_projeto()
        if nome not in dict(PASTAS_EXPORTACAO):
            raise ErroUsuario("Pasta desconhecida.")
        caminho = os.path.join(self._projeto.pasta, nome)
        os.makedirs(caminho, exist_ok=True)
        from .comunidade import _abrir_no_sistema
        _abrir_no_sistema(caminho)
        return {"pasta": self._projeto.rel(caminho)}

    # ------------------------------------------------------------ diagnóstico
    def _caminho_log(self) -> str:
        return os.path.join(self._projeto.pasta if self._projeto else base.PASTA_PROJETO, "siapp.log")

    @resposta_segura
    def diagnostico(self):
        versoes = {"SIAPP": mp.VERSAO_SIAPP, "Python": platform.python_version(),
                   "Sistema": f"{platform.system()} {platform.release()}"}
        for pacote in ("pywebview", "pymupdf", "numpy", "dlisio", "lasio", "requests"):
            versoes[pacote] = _versao(pacote)
        pasta = self._projeto.pasta if self._projeto else base.PASTA_PROJETO
        banco = os.path.join(pasta, "projeto.sqlite")
        chamadas = list(base.CHAMADAS)
        lentas = sorted((c for c in chamadas if c["ok"]), key=lambda c: -c["ms"])[:8]
        erros = [c for c in chamadas if not c["ok"]][-10:][::-1]
        return {"versoes": versoes, "pasta": pasta,
                "banco_bytes": os.path.getsize(banco) if os.path.isfile(banco) else 0,
                "ocr_instalado": os.path.isdir(base.PASTA_TESSDATA) and bool(os.listdir(base.PASTA_TESSDATA)),
                "janelas": ["principal", *sorted(self._janelas)],
                "lentas": lentas, "erros_sessao": erros, "erros_log": _erros_do_log(self._caminho_log()),
                "barra_de_tarefas": icone.atalhos_fixados(), "atualizacao": _ultima_atualizacao()}

    @resposta_segura
    def corrigir_atalho_fixado(self):
        """Grava a identidade do SIAPP no botão fixado na barra de tarefas (0.58). Ver ponte/icone.py."""
        feitos = icone.corrigir_fixados()
        if not feitos:
            raise ErroUsuario("Nenhum botão fixado do SIAPP precisava (ou pôde) ser corrigido.")
        return {"corrigidos": feitos}

    @resposta_segura
    def novidades(self, n: int = 3):
        """As últimas versões do CHANGELOG.md, em itens curtos (Ajuda › Novidades)."""
        return {"versoes": ler_changelog(os.path.join(base.PASTA_APP, "CHANGELOG.md"), int(n or 3))}

    @resposta_segura
    def doacao(self):
        """Ajuda › Apoie o projeto (0.67): o que está em recursos/doacao.json. `ativo` False = a tela fica escondida."""
        from motor import doacao as mdo
        return mdo.ler(os.path.join(base.PASTA_RECURSOS, "doacao.json"))

    @resposta_segura
    def doacao_pix(self, valor=None):
        """1.3: o Pix da tela de apoio com o valor escolhido ("copia e cola" e QR Code em SVG)."""
        from motor import doacao as mdo
        return mdo.pix_com_valor(mdo.ler(os.path.join(base.PASTA_RECURSOS, "doacao.json")), valor)

    @resposta_segura
    def aviso_atualizacao(self):
        """O lançador atualizou o SIAPP ao abrir? Mostra uma vez ("SIAPP atualizado: 0.57.0 → 0.58.0")."""
        caminho = os.path.join(base.PASTA_PROJETO, "atualizacao.json")      # gravado pelo lançador
        try:
            with open(caminho, encoding="utf-8") as f:
                aviso = json.load(f)
            os.remove(caminho)
        except (OSError, ValueError):
            return {"aviso": None}
        return {"aviso": aviso}

    @resposta_segura
    def abrir_log(self):
        caminho = self._caminho_log()
        if not os.path.isfile(caminho):
            raise ErroUsuario("Ainda não há siapp.log.")
        from .comunidade import _abrir_no_sistema
        _abrir_no_sistema(caminho)
        return {}


def _versao(pacote: str) -> str:
    try:
        from importlib import metadata
        return metadata.version(pacote)
    except Exception:
        return "—"


_LINHA_LOG = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+\s+(ERROR|WARNING|CRITICAL)\s+(\S+):\s*(.*)$")


def ler_changelog(caminho: str, n: int = 3) -> list[dict]:
    """As `n` primeiras versões do CHANGELOG (formato Keep a Changelog), sem a marcação do Markdown."""
    try:
        with open(caminho, encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except OSError:
        return []
    limpar = lambda t: re.sub(r"\*\*|`", "", t).strip()       # noqa: E731
    versoes, atual, secao = [], None, None
    for linha in linhas:
        m = re.match(r"## \[(\d[^\]]*)\](?:\s+[—-]\s+(\S+))?", linha)
        if m:
            if len(versoes) == n:
                break
            atual = {"versao": m.group(1), "data": m.group(2) or "", "resumo": "", "secoes": []}
            versoes.append(atual)
            secao = None
        elif atual is None:
            continue
        elif linha.startswith("### "):
            secao = {"titulo": linha[4:].strip(), "itens": []}
            atual["secoes"].append(secao)
        elif linha.startswith("- ") and secao is not None:
            secao["itens"].append(limpar(linha[2:]))
        elif linha.startswith("  ") and secao is not None and secao["itens"]:
            secao["itens"][-1] += " " + limpar(linha)
        elif linha.strip() and secao is None and not atual["resumo"]:
            atual["resumo"] = limpar(linha)
    return versoes


def _ultima_atualizacao() -> str:
    """A última linha "atualização: …" do log do lançador (o que o atalho fez ao abrir)."""
    try:
        with open(os.path.join(base.PASTA_PROJETO, "lancador.log"), encoding="utf-8", errors="replace") as f:
            linhas = [l.strip() for l in f if "atualização:" in l]
    except OSError:
        return ""
    return linhas[-1] if linhas else ""


def _erros_do_log(caminho: str, n: int = 12) -> list[dict]:
    """Últimos erros do siapp.log, cada um com a última linha do traceback (a causa)."""
    if not os.path.isfile(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            linhas = f.readlines()[-4000:]
    except OSError:
        return []
    erros, atual = [], None
    for linha in linhas:
        m = _LINHA_LOG.match(linha.rstrip("\n"))
        if m:
            atual = {"quando": m.group(1), "nivel": m.group(2), "texto": m.group(4), "causa": ""}
            erros.append(atual)
        elif re.match(r"^\d{4}-\d{2}-\d{2} ", linha):
            atual = None
        elif atual is not None and linha.strip() and not linha.startswith((" ", "\t", "Traceback")):
            atual["causa"] = linha.strip()[:300]
    return erros[-n:][::-1]
