"""
Pasta de projeto do SIAPP.

A pasta de projeto é o contrato entre o motor e o visualizador: tudo o que
o SIAPP produz fica nela, em formatos abertos, e qualquer peça (a janela,
um script, um HTML aberto no navegador) pode ler sem depender das outras.

Estrutura:
    <projeto>/
    ├── siapp.json                      configuração do projeto
    ├── historico.jsonl                 histórico do projeto, um evento por linha (0.60)
    ├── projeto.sqlite                  banco do projeto (ver motor/banco.py)
    ├── siapp.log                       registro de erros (para relatar problemas)
    ├── catalogo/<bacia>/               o que existe no portal (só listagem)
    │   ├── categorias.json
    │   ├── <categoria>.json
    │   └── arvores/<poço>.json         pastas e arquivos de cada poço explorado
    ├── bruto/                          arquivos baixados, intocados (.dlis/.lis)
    │   ├── <bacia>/<poço>/<pastas do portal>/<arquivo>
    │   └── registro_downloads.json     procedência de cada arquivo baixado (+ .mudancas.jsonl, 0.61)
    ├── texto/                          texto dos documentos (embutido ou OCR)
    │   ├── <mesmo caminho de bruto>.json   texto + posição das palavras, por página
    │   ├── resumo.json                 situação de cada documento processado (+ .mudancas.jsonl, 0.61)
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
from . import formatos  # noqa: E402
ARQUIVO_CONFIG = "siapp.json"
ARQUIVO_HISTORICO = "historico.jsonl"
NOME_PASTA_PADRAO = "ambiente_teste"
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


def tipo_arquivo(caminho: str) -> str:
    """'documento', 'perfil' ou 'outro' — pelo conteúdo, quando o arquivo existe
    (o REATE tem DLIS com extensão .tif; ver motor/formatos.py)."""
    return formatos.tipo(caminho)


def acrescentar_linhas(caminho: str, objetos: list) -> None:
    """Acrescenta um JSON por linha. Se a última linha ficou cortada (o app fechou no meio), começa numa linha nova,
    para ela não engolir a primeira das novas."""
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    texto = "".join(json.dumps(o, ensure_ascii=False, default=str) + "\n" for o in objetos)
    with open(caminho, "a+b") as f:
        if f.tell() > 0:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                texto = "\n" + texto
        f.write(texto.encode("utf-8"))


def ler_json(caminho: str, padrao=None):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


class MapaEmDisco:
    """Um dicionário guardado em JSON que cresce sem ser regravado inteiro (0.61).

    O JSON base (`<nome>.json`, o mesmo formato de antes) fica como está; cada mudança vira uma linha no arquivo
    `<nome>.mudancas.jsonl` ({"k": chave, "v": valor} ou {"k": chave, "apagar": true}). Ler = base + mudanças na ordem.
    Quando as mudanças passam de `LIMITE` linhas, tudo volta para o JSON base e o arquivo de mudanças some. Uma linha
    quebrada (o app fechou no meio) é ignorada; as outras valem.
    """

    LIMITE = 500

    def __init__(self, caminho: str):
        self.caminho = caminho
        self.caminho_mudancas = caminho[:-5] + ".mudancas.jsonl" if caminho.endswith(".json") else caminho + ".mudancas"
        self._cache = None          # (assinatura dos arquivos, dicionário, nº de linhas de mudança)

    def _assinatura(self):
        r = []
        for c in (self.caminho, self.caminho_mudancas):
            try:
                st = os.stat(c)
                r.append((st.st_mtime_ns, st.st_size))
            except OSError:
                r.append(None)
        return tuple(r)

    def _carregar(self):
        ass = self._assinatura()
        if self._cache is not None and self._cache[0] == ass:
            return self._cache[1], self._cache[2]
        dados = ler_json(self.caminho, {})
        if not isinstance(dados, dict):
            dados = {}
        n = 0
        try:
            with open(self.caminho_mudancas, encoding="utf-8") as f:
                for linha in f:
                    try:
                        m = json.loads(linha)
                    except json.JSONDecodeError:
                        continue
                    n += 1
                    if m.get("apagar"):
                        dados.pop(m.get("k"), None)
                    else:
                        dados[m.get("k")] = m.get("v")
        except FileNotFoundError:
            pass
        self._cache = (ass, dados, n)
        return dados, n

    def ler(self) -> dict:
        with _TRAVA_ESCRITA:
            return dict(self._carregar()[0])

    def _anotar(self, linhas: list[dict]):
        if not linhas:
            return
        _, n = self._carregar()
        if n + len(linhas) > self.LIMITE:
            dados = dict(self._carregar()[0])
            for m in linhas:
                if m.get("apagar"):
                    dados.pop(m["k"], None)
                else:
                    dados[m["k"]] = m["v"]
            self.substituir(dados)
            return
        acrescentar_linhas(self.caminho_mudancas, linhas)

    def definir(self, chave: str, valor) -> None:
        with _TRAVA_ESCRITA:
            self._anotar([{"k": chave, "v": valor}])

    def apagar(self, chaves) -> int:
        with _TRAVA_ESCRITA:
            dados, _ = self._carregar()
            existem = [k for k in chaves if k in dados]
            self._anotar([{"k": k, "apagar": True} for k in existem])
            return len(existem)

    def substituir(self, dados: dict) -> None:
        """Grava tudo no JSON base e apaga as mudanças (compactação)."""
        with _TRAVA_ESCRITA:
            salvar_json(self.caminho, dados)
            try:
                os.remove(self.caminho_mudancas)
            except FileNotFoundError:
                pass
            self._cache = None


_MAPAS: dict[str, MapaEmDisco] = {}


def _mapa(caminho: str) -> MapaEmDisco:
    with _TRAVA_ESCRITA:
        m = _MAPAS.get(caminho)
        if m is None:
            m = _MAPAS[caminho] = MapaEmDisco(caminho)
        return m


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
            })
        p._migrar_historico()
        return p

    # ------------------------------------------------------------ marca de mudança
    IGNORAR_NA_MARCA = ("preferencias.json", "siapp.log", "atualizacao.json")

    def marca(self) -> str:
        """Uma "impressão" barata do estado da pasta do projeto (0.61): data e tamanho de cada arquivo e pasta dos dois
        primeiros níveis (o banco, o histórico, os registros, `bruto/<bacia>`…). A janela compara a marca ao trocar de
        aba e só recarrega a aba se ela mudou. Criar, apagar ou regravar um JSON (temporário + troca) no terceiro nível
        muda a data da pasta onde ele está (e, se for novo, o número de itens dela), então aparece também. Os downloads e
        os textos, mais fundos, entram pelos registros (`registro_downloads`, `resumo`). Preferências e registros de erro
        não contam."""
        partes = []

        def anotar(caminho, nivel):
            try:
                with os.scandir(caminho) as it:
                    for e in it:
                        if e.name in self.IGNORAR_NA_MARCA or e.name.endswith((".log", ".tmp", ".part")):
                            continue
                        try:
                            # 1.0.2: no Windows, o stat() de um DirEntry vem da listagem da pasta-mãe, e o NTFS só
                            # atualiza ali a data de uma subpasta mais tarde: arquivo novo no 3º nível não mudava a
                            # marca. Para pastas, os.stat() lê a data de verdade.
                            st = os.stat(e.path) if e.is_dir() else e.stat()
                        except OSError:
                            continue
                        extra = st.st_size if e.is_file() else ""
                        if nivel == 2 and e.is_dir():
                            # 1.2: e quantos itens há na pasta do 2º nível. No Windows, dois arquivos criados na
                            # mesma pasta dentro do mesmo "tique" do relógio (~16 ms) deixam a data da pasta igual.
                            try:
                                extra = len(os.listdir(e.path))
                            except OSError:
                                pass
                        partes.append(f"{e.name}:{st.st_mtime_ns}:{extra}")
                        if nivel < 2 and e.is_dir():
                            anotar(e.path, nivel + 1)
            except OSError:
                pass

        anotar(self.pasta, 1)
        return hashlib.blake2b("|".join(partes).encode("utf-8", "replace"), digest_size=8).hexdigest()

    # ------------------------------------------------------------ configuração
    @property
    def config(self) -> dict:
        return ler_json(self.caminho_config, {})

    @property
    def caminho_historico(self) -> str:
        return os.path.join(self.pasta, ARQUIVO_HISTORICO)

    def _migrar_historico(self):
        """Até a 0.59, o histórico ficava dentro do siapp.json e o arquivo inteiro era regravado a cada evento
        (o do Ruan passava de 200 KB). Desde a 0.60, cada evento é uma linha acrescentada a historico.jsonl."""
        with _TRAVA_ESCRITA:
            cfg = ler_json(self.caminho_config, {}) or {}
            antigo = cfg.pop("historico", None)
            if antigo is None:
                return
            if antigo:
                acrescentar_linhas(self.caminho_historico, antigo)
            salvar_json(self.caminho_config, cfg)

    def registrar(self, evento: str, **dados) -> dict:
        """Atualiza a configuração e anota o evento no histórico do projeto (uma linha em historico.jsonl).
        O histórico é a base da rastreabilidade: todo número futuro terá uma
        execução identificável por trás."""
        with _TRAVA_ESCRITA:
            acrescentar_linhas(self.caminho_historico, [{"quando": agora(), "evento": evento, **dados}])
            cfg = self.config
            cfg.update({k: v for k, v in dados.items() if k in ("bacia",)})
            cfg["atualizado"] = agora()
            salvar_json(self.caminho_config, cfg)
            return cfg

    def historico(self, ultimos: int | None = None) -> list[dict]:
        """Os eventos do projeto, do mais antigo ao mais novo (linhas estragadas são puladas)."""
        try:
            with open(self.caminho_historico, encoding="utf-8") as f:
                linhas = f.readlines()
        except OSError:
            return []
        if ultimos:
            linhas = linhas[-ultimos:]
        out = []
        for linha in linhas:
            try:
                out.append(json.loads(linha))
            except ValueError:
                continue
        return out

    def definir_config(self, **valores) -> dict:
        """Grava chaves de configuração (ex.: autor) sem passar pelo histórico."""
        with _TRAVA_ESCRITA:
            cfg = self.config
            cfg.update(valores)
            cfg["atualizado"] = agora()
            salvar_json(self.caminho_config, cfg)
            return cfg

    def pasta_de(self, nome: str) -> str:
        """Subpasta do projeto, criada se não existir (contribuicoes, comunidade…)."""
        caminho = os.path.join(self.pasta, nome)
        os.makedirs(caminho, exist_ok=True)
        return caminho

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
        return self.mapa_registro.ler()

    @property
    def mapa_registro(self) -> "MapaEmDisco":
        return _mapa(self.caminho_registro)

    @property
    def caminho_registro(self) -> str:
        return os.path.join(self.pasta, "bruto", "registro_downloads.json")

    def registrar_download(self, bacia: str, poco: str, caminho_remoto: str,
                           destino: str, bytes_: int) -> None:
        """Procedência: para cada arquivo em bruto/, de onde veio e quando."""
        self.mapa_registro.definir(f"{bacia}:{caminho_remoto}", {
            "bacia": bacia, "poco": poco, "caminho_remoto": caminho_remoto,
            "arquivo_local": self.rel(destino),
            "bytes": bytes_, "baixado_em": agora(),
        })

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

    @property
    def mapa_resumo_texto(self) -> "MapaEmDisco":
        return _mapa(self.caminho_resumo_texto)

    def resumo_texto(self) -> dict:
        """Situação de cada documento processado (chaves sempre com "/")."""
        return {rel_padrao(k): v for k, v in self.mapa_resumo_texto.ler().items()}

    def salvar_texto(self, rel: str, resultado: dict) -> None:
        rel = rel_padrao(rel)
        salvar_json(self.caminho_texto(rel), {"arquivo": rel, **resultado})
        metodos = [p["metodo"] for p in resultado["paginas"]]
        self.mapa_resumo_texto.definir(rel, {"n_paginas": resultado["n_paginas"],
                                             "embutido": metodos.count("embutido"), "ocr": metodos.count("ocr"),
                                             "processado_em": resultado["processado_em"],
                                             "bytes_origem": resultado["bytes_origem"]})

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
                if tipo_arquivo(caminho) != "documento":   # ex.: DLIS com extensão .tif
                    continue
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
