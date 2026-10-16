"""
Pasta de projeto do SIAPP.

A pasta de projeto é o contrato entre o motor e o visualizador: tudo o que
o SIAPP produz fica nela, em formatos abertos, e qualquer peça (a janela,
um script, um HTML aberto no navegador) pode ler sem depender das outras.

Estrutura:
    <projeto>/
    ├── siapp.json                      configuração e histórico do projeto
    ├── projeto.sqlite                  banco do projeto (ver motor/banco.py)
    ├── siapp.log                       registro de erros (para relatar problemas)
    ├── catalogo/<bacia>/               o que existe no portal (só listagem)
    │   ├── categorias.json
    │   ├── <categoria>.json
    │   └── arvores/<poço>.json         pastas e arquivos de cada poço explorado
    ├── bruto/                          arquivos baixados, intocados (.dlis/.lis)
    │   ├── <bacia>/<poço>/<pastas do portal>/<arquivo>
    │   └── registro_downloads.json     procedência de cada arquivo baixado
    ├── texto/                          texto dos documentos (embutido ou OCR)
    │   ├── <mesmo caminho de bruto>.json   texto + posição das palavras, por página
    │   ├── resumo.json                 situação de cada documento processado
    │   ├── vocabulario_projeto.json    palavras e correções do usuário
    │   └── indice.sqlite               índice de busca
    ├── pocos/                          curvas padronizadas, uma tabela por poço
    └── execucoes/                      cada processamento, com seus parâmetros
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime

# Downloads rodam numa thread separada da interface: toda escrita em
# siapp.json e no registro de downloads passa por esta trava.
_TRAVA_ESCRITA = threading.RLock()

from . import __version__ as VERSAO_SIAPP  # noqa: E402  (uma fonte só para a versão)
ARQUIVO_CONFIG = "siapp.json"
SUBPASTAS = ("catalogo", "bruto", "texto", "pocos", "execucoes")


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def nome_seguro(texto: str) -> str:
    """Nome utilizável como pasta/arquivo em qualquer sistema operacional."""
    return re.sub(r'[<>:"/\\|?*\s]+', "_", texto).strip("_") or "sem_nome"


def salvar_json(caminho: str, dados) -> None:
    """Escrita atômica: grava num .tmp e troca. Uma interrupção no meio
    nunca deixa um JSON pela metade."""
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)


def rel_padrao(rel: str) -> str:
    """Caminho relativo sempre com "/" (o Windows aceita), para a pasta de
    projeto funcionar igual em qualquer sistema e os ids não mudarem."""
    return rel.replace("\\", "/")


def sha256_arquivo(caminho: str) -> str:
    """Impressão digital do conteúdo: identifica o MESMO arquivo em qualquer
    computador, mesmo com outro nome ou noutra pasta."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


TIPOS_ARQUIVO = {
    "documento": (".pdf", ".tif", ".tiff"),
    "perfil": (".dlis", ".lis", ".las"),
}


def tipo_arquivo(nome: str) -> str:
    ext = os.path.splitext(nome)[1].lower()
    return next((t for t, exts in TIPOS_ARQUIVO.items() if ext in exts), "outro")


def ler_json(caminho: str, padrao=None):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


class Projeto:
    def __init__(self, pasta: str):
        self.pasta = os.path.abspath(pasta)
        self.caminho_config = os.path.join(self.pasta, ARQUIVO_CONFIG)

    @classmethod
    def abrir_ou_criar(cls, pasta: str) -> "Projeto":
        p = cls(pasta)
        if not os.path.isdir(p.pasta):
            raise NotADirectoryError(f"Não é uma pasta: {p.pasta}")
        for sub in SUBPASTAS:
            os.makedirs(os.path.join(p.pasta, sub), exist_ok=True)
        if ler_json(p.caminho_config) is None:
            salvar_json(p.caminho_config, {
                "siapp_versao": VERSAO_SIAPP,
                "criado": agora(),
                "atualizado": agora(),
                "bacia": None,
                "historico": [],
            })
        return p

    # ------------------------------------------------------------ configuração
    @property
    def config(self) -> dict:
        return ler_json(self.caminho_config, {})

    def registrar(self, evento: str, **dados) -> dict:
        """Atualiza a configuração e anota o evento no histórico do projeto.
        O histórico é a base da rastreabilidade: todo número futuro terá uma
        execução identificável por trás."""
        with _TRAVA_ESCRITA:
            cfg = self.config
            cfg.update({k: v for k, v in dados.items() if k in ("bacia",)})
            cfg["atualizado"] = agora()
            cfg.setdefault("historico", []).append({"quando": agora(), "evento": evento, **dados})
            salvar_json(self.caminho_config, cfg)
            return cfg

    # ---------------------------------------------------------------- catálogo
    def pasta_catalogo(self, bacia: str) -> str:
        return os.path.join(self.pasta, "catalogo", nome_seguro(bacia))

    def salvar_categorias(self, bacia: str, base: str, categorias: list[dict]) -> str:
        caminho = os.path.join(self.pasta_catalogo(bacia), "categorias.json")
        salvar_json(caminho, {"bacia": bacia, "base_remota": base,
                              "listado_em": agora(), "categorias": categorias})
        return caminho

    def salvar_pocos(self, bacia: str, categoria: str, pocos: list[dict],
                     arquivos_soltos: list[dict], partes: list[str] | None = None,
                     duplicados: list[dict] | None = None) -> str:
        caminho = os.path.join(self.pasta_catalogo(bacia), nome_seguro(categoria) + ".json")
        salvar_json(caminho, {"bacia": bacia, "categoria": categoria, "listado_em": agora(),
                              "total_pocos": len(pocos), "partes": partes or [],
                              "pocos": pocos, "arquivos_soltos": arquivos_soltos,
                              "duplicados": duplicados or []})
        return caminho

    # --------------------------------------------------------------- downloads
    def destino_bruto(self, bacia: str, poco: str, pasta_relativa: str, nome: str) -> str:
        """
        Onde um arquivo baixado fica no disco. Reproduz a estrutura de pastas
        do portal dentro do poço, para nunca perder de onde o arquivo veio:
            bruto/<Bacia>/<poço>/<pastas do portal>/<arquivo>
        """
        partes = [bacia, poco] + [p for p in pasta_relativa.split("/") if p] + [nome]
        limpas = []
        for p in partes:
            p = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", p).strip(" .")
            if p and p not in (".", ".."):           # nunca sai da pasta do projeto
                limpas.append(p)
        return os.path.join(self.pasta, "bruto", *limpas)

    @property
    def caminho_banco(self) -> str:
        return os.path.join(self.pasta, "projeto.sqlite")

    def bacia_poco_de(self, rel: str) -> tuple[str, str]:
        """bruto/<bacia>/<poço>/... → (bacia, nome da pasta do poço)."""
        partes = os.path.relpath(self.caminho_seguro(rel), self.pasta_bruto).split(os.sep)
        return (partes[0], partes[1]) if len(partes) > 2 else ("", "")

    def registro_downloads(self) -> dict:
        return ler_json(self.caminho_registro, {})

    @property
    def caminho_registro(self) -> str:
        return os.path.join(self.pasta, "bruto", "registro_downloads.json")

    def registrar_download(self, bacia: str, poco: str, caminho_remoto: str,
                           destino: str, bytes_: int) -> None:
        """Procedência: para cada arquivo em bruto/, de onde veio e quando."""
        with _TRAVA_ESCRITA:
            reg = ler_json(self.caminho_registro, {})
            reg[f"{bacia}:{caminho_remoto}"] = {
                "bacia": bacia, "poco": poco, "caminho_remoto": caminho_remoto,
                "arquivo_local": self.rel(destino),
                "bytes": bytes_, "baixado_em": agora(),
            }
            salvar_json(self.caminho_registro, reg)

    # -------------------------------------------------------------- documentos
    @property
    def pasta_bruto(self) -> str:
        return os.path.join(self.pasta, "bruto")

    def caminho_seguro(self, rel: str) -> str:
        """Caminho absoluto de um arquivo dentro de bruto/, recusando qualquer
        coisa que aponte para fora da pasta do projeto."""
        alvo = os.path.normpath(os.path.join(self.pasta, rel_padrao(rel)))
        if os.path.commonpath([alvo, self.pasta_bruto]) != self.pasta_bruto:
            raise ValueError(f"Caminho fora de bruto/: {rel}")
        return alvo

    def caminho_texto(self, rel: str) -> str:
        sob_bruto = os.path.relpath(self.caminho_seguro(rel), self.pasta_bruto)
        return os.path.join(self.pasta, "texto", sob_bruto + ".json")

    @property
    def caminho_resumo_texto(self) -> str:
        return os.path.join(self.pasta, "texto", "resumo.json")

    def rel(self, caminho: str) -> str:
        """Caminho absoluto → relativo à pasta de projeto, com "/"."""
        return rel_padrao(os.path.relpath(caminho, self.pasta))

    def resumo_texto(self) -> dict:
        """Situação de cada documento processado (chaves sempre com "/")."""
        return {rel_padrao(k): v for k, v in ler_json(self.caminho_resumo_texto, {}).items()}

    def salvar_texto(self, rel: str, resultado: dict) -> None:
        rel = rel_padrao(rel)
        salvar_json(self.caminho_texto(rel), {"arquivo": rel, **resultado})
        metodos = [p["metodo"] for p in resultado["paginas"]]
        with _TRAVA_ESCRITA:
            resumo = self.resumo_texto()
            resumo[rel] = {"n_paginas": resultado["n_paginas"],
                           "embutido": metodos.count("embutido"), "ocr": metodos.count("ocr"),
                           "processado_em": resultado["processado_em"],
                           "bytes_origem": resultado["bytes_origem"]}
            salvar_json(self.caminho_resumo_texto, resumo)

    def ler_texto(self, rel: str) -> dict | None:
        return ler_json(self.caminho_texto(rel))

    def documentos_processados(self):
        """(rel, bacia, poço, nome, páginas) de cada documento com texto extraído."""
        for rel in self.resumo_texto():
            t = self.ler_texto(rel)
            if not t:
                continue
            partes = os.path.relpath(self.caminho_seguro(rel), self.pasta_bruto).split(os.sep)
            bacia, poco = (partes[0], partes[1]) if len(partes) > 2 else ("", "")
            yield rel, bacia, poco, partes[-1], t["paginas"]

    # ------------------------------------------------------------ vocabulário
    @property
    def caminho_vocabulario(self) -> str:
        """Palavras, correções e exceções que o usuário cria pela janela."""
        return os.path.join(self.pasta, "texto", "vocabulario_projeto.json")

    def salvar_vocabulario(self, dados: dict) -> None:
        with _TRAVA_ESCRITA:
            salvar_json(self.caminho_vocabulario, dados)

    def listar_documentos(self, extensoes: tuple) -> list[dict]:
        """Todos os arquivos baixados que são documentos (PDF, TIF), com a
        situação do texto: pendente, processado ou desatualizado (o arquivo
        mudou de tamanho depois de processado)."""
        resumo = self.resumo_texto()
        docs = []
        for raiz, _, arquivos in os.walk(self.pasta_bruto):
            for nome in sorted(arquivos):
                if not nome.lower().endswith(extensoes):
                    continue
                caminho = os.path.join(raiz, nome)
                rel = self.rel(caminho)
                partes = os.path.relpath(caminho, self.pasta_bruto).split(os.sep)
                info = resumo.get(rel)
                tamanho = os.path.getsize(caminho)
                if info is None:
                    situacao = "pendente"
                elif info.get("bytes_origem") != tamanho:
                    situacao = "desatualizado"
                else:
                    situacao = "processado"
                docs.append({"rel": rel, "nome": nome, "tamanho": tamanho,
                             "bacia": partes[0] if len(partes) > 2 else "",
                             "poco": partes[1] if len(partes) > 2 else "",
                             "pasta": "/".join(partes[2:-1]),
                             "situacao": situacao, **(info or {})})
        return docs

    def salvar_arvore(self, bacia: str, poco: str, mapa: dict, **contexto) -> str:
        """Árvore de arquivos de um poço no portal (resultado de mapear_poco)."""
        caminho = os.path.join(self.pasta_catalogo(bacia), "arvores", nome_seguro(poco) + ".json")
        salvar_json(caminho, {"bacia": bacia, **contexto, "listado_em": agora(), **mapa})
        return caminho
