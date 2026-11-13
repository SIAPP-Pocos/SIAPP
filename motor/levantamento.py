"""Levantamento do acervo REATE: o que cada poço tem, pelo conteúdo dos arquivos.

Para cada categoria de uma bacia:

1. **Lista** cada pasta "parte" inteira numa requisição (PROPFIND Depth infinity)
   e separa os arquivos por poço.
2. **Classifica** os arquivos que podem ser perfil lendo só o começo de cada um
   (1 KB; ver motor/formatos.py). Opcionalmente lê mais (até 256 KB) para listar
   as curvas sem baixar o arquivo.
3. Resume o poço: **digital** (tem DLIS, LIS ou LAS), **só imagem** (só TIFF/PDF
   na pasta de perfis), **sem perfil**, ou **pendente** (falta ler algum arquivo).

Nada é baixado inteiro. Tudo fica no banco do projeto (tabelas acervo_*), e
rodar de novo continua de onde parou: arquivo já lido, com o mesmo tamanho, não
é lido outra vez.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import tempfile
import threading
from collections import Counter

from . import agp as magp
from . import direcionais as mdi
from . import ferramentas as mfe
from . import formatos
from .banco import Banco, agora
from .pocos import chave
from .reate import ClienteREATE, ErroREATE, eh_pasta_de_perfis, eh_pasta_parte

EXT_PERFIL = (".dlis", ".lis", ".las", ".tif", ".tiff", ".lti")
# extensões em que o nome não engana (na amostra de 16/10/2026): nos outros
# casos — sobretudo .tif — só o conteúdo diz o que é
EXT_CONFIAVEIS = (".dlis", ".lis", ".las", ".pdf")
BYTES_FORMATO = formatos.BYTES_NECESSARIOS
BYTES_CURVAS = {"dlis": 256 * 1024, "lis": 256 * 1024, "las": 32 * 1024}

SITUACOES = {
    "digital": "perfil digital (DLIS, LIS ou LAS)",
    "imagem": "só imagem (TIFF, PDF)",
    "sem_perfil": "sem perfil",
    "pendente": "falta conferir",
}
# índice de profundidade e canais de enchimento não são curvas medidas
RE_NAO_CURVA = re.compile(r"^(DEPT|DEPTH|TDEP|INDEX\d*|DUMM|DUMMY)$", re.IGNORECASE)
FAMILIAS_RESUMO = ("GR", "SP", "CALI", "RES_PROF", "RHOB", "NPHI", "DT", "PE")
# curvas interpretadas pela operadora (perfil processado): ver motor/operador.py
FAMILIAS_INTERP = ("VSH", "PHIE", "PHIT", "SW", "PERM")


class Cancelado(Exception):
    pass


# ================================================================ listagem
def agrupar_por_poco(container: str, itens: list[dict]) -> dict[str, dict]:
    """Itens de uma listagem recursiva de `container` (categoria ou parte) →
    {caminho da pasta do poço: {nome, arquivos: [...]}}."""
    container = container.rstrip("/") + "/"
    pocos: dict[str, dict] = {}
    for i in itens:
        if not i["caminho"].startswith(container):
            continue
        partes = i["caminho"][len(container):].strip("/").split("/")
        if not partes or not partes[0]:
            continue
        cam_poco = container + partes[0] + "/"
        p = pocos.setdefault(cam_poco, {"nome": partes[0], "caminho": cam_poco, "arquivos": []})
        if i["pasta"] or len(partes) == 1:
            if not i["pasta"]:          # arquivo solto na categoria (não é poço)
                pocos.pop(cam_poco, None)
            continue
        pastas = partes[1:-1]
        ext = os.path.splitext(i["nome"])[1].lower()
        na_pasta = any(eh_pasta_de_perfis(x) for x in pastas)
        p["arquivos"].append({
            "caminho": i["caminho"], "nome": i["nome"], "pasta": "/".join(pastas),
            "ext": ext, "tamanho": i["tamanho"],
            "candidato": int(na_pasta or ext in EXT_PERFIL),
        })
    return pocos


def gravar_listagem(banco: Banco, bacia: str, categoria: str, parte: str | None,
                    pocos: dict[str, dict]) -> int:
    """Grava poços e arquivos listados. Arquivo com o mesmo tamanho mantém a
    classificação anterior; arquivo que sumiu do portal sai do banco."""
    quando = agora()
    with banco.conexao() as c:
        for cam, p in pocos.items():
            c.execute("""INSERT INTO acervo_pocos (bacia, caminho, nome_pasta, poco_id, categoria, parte,
                                                   n_arquivos, bytes, listado_em)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                         ON CONFLICT (bacia, caminho) DO UPDATE SET
                           nome_pasta = excluded.nome_pasta, poco_id = excluded.poco_id,
                           categoria = excluded.categoria, parte = excluded.parte,
                           n_arquivos = excluded.n_arquivos, bytes = excluded.bytes,
                           listado_em = excluded.listado_em""",
                      (bacia, cam, p["nome"], chave(p["nome"]), categoria, parte,
                       len(p["arquivos"]), sum(a["tamanho"] for a in p["arquivos"]), quando))
            antigos = {r["caminho"]: r for r in c.execute(
                "SELECT caminho, tamanho FROM acervo_arquivos WHERE bacia = ? AND poco_caminho = ?",
                (bacia, cam))}
            for a in p["arquivos"]:
                velho = antigos.pop(a["caminho"], None)
                if velho is not None and velho["tamanho"] == a["tamanho"]:
                    c.execute("UPDATE acervo_arquivos SET candidato = ?, pasta = ? WHERE bacia = ? AND caminho = ?",
                              (a["candidato"], a["pasta"], bacia, a["caminho"]))
                    continue
                c.execute("INSERT OR REPLACE INTO acervo_arquivos "
                          "(bacia, caminho, poco_caminho, nome, pasta, ext, tamanho, candidato, formato, verificado) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (bacia, a["caminho"], cam, a["nome"], a["pasta"], a["ext"], a["tamanho"],
                           a["candidato"], formatos.pela_extensao(a["nome"]), ""))
            for sumiu in antigos:
                c.execute("DELETE FROM acervo_arquivos WHERE bacia = ? AND caminho = ?", (bacia, sumiu))
        # também alimenta o catálogo de pastas do REATE (mapa, ficha)
        c.executemany("INSERT OR REPLACE INTO reate VALUES (?, ?, ?, ?, ?, ?, ?)",
                      [(bacia, cam, p["nome"], chave(p["nome"]), categoria, parte, quando)
                       for cam, p in pocos.items()])
    return len(pocos)


# ============================================================ curvas
def _arquivo_temporario(dados: bytes) -> str:
    f = tempfile.NamedTemporaryFile(prefix="siapp_inicio_", delete=False)
    with f:
        f.write(dados)
    return f.name


def curvas_do_inicio(dados: bytes, fmt: str, completo: bool) -> list[str]:
    """Mnemônicos das curvas que aparecem no começo do arquivo. DLIS e LIS
    guardam a descrição das curvas antes dos dados; arquivos com várias
    corridas repetem isso mais adiante, então a lista pode estar incompleta
    (quem chama sabe pelo `completo`)."""
    if fmt == "las":
        return _curvas_las(dados.decode("latin-1", "replace"))
    if fmt not in ("dlis", "lis"):
        return []
    from dlisio.common import Actions, ErrorHandler   # importa só quando precisa
    caminho = _arquivo_temporario(dados)
    tratador = ErrorHandler(critical=Actions.LOG_ERROR)   # arquivo cortado: lê até onde der
    nomes: list[str] = []
    nivel = logging.root.manager.disable
    logging.disable(logging.ERROR)                   # o corte proposital gera erros esperados
    try:
        if fmt == "dlis":
            from dlisio import dlis
            with dlis.load(caminho, error_handler=tratador) as arquivos:
                for lf in arquivos:
                    canais = [c for fr in lf.frames for c in fr.channels] or list(lf.channels)
                    nomes += [str(c.name).strip() for c in canais]
        else:
            from dlisio import lis
            with lis.load(caminho, error_handler=tratador) as arquivos:
                for lf in arquivos:
                    for spec in lf.data_format_specs():
                        nomes += [str(e.mnemonic).strip() for e in spec.specs]
    except Exception:   # noqa: BLE001 — começo ilegível: fica sem lista de curvas
        return []
    finally:
        logging.disable(nivel)
        try:
            os.remove(caminho)
        except OSError:
            pass
    vistos, saida = set(), []
    for n in nomes:
        if n and n.upper() not in vistos and not RE_NAO_CURVA.match(n):
            vistos.add(n.upper())
            saida.append(n)
    return saida


def _curvas_las(texto: str) -> list[str]:
    saida, na_secao = [], False
    for linha in texto.splitlines():
        s = linha.strip()
        if s.startswith("~"):
            na_secao = s[1:2].upper() == "C"
            continue
        if na_secao and s and not s.startswith("#"):
            mn = re.split(r"[.\s]", s, maxsplit=1)[0]
            if mn and not RE_NAO_CURVA.match(mn):
                saida.append(mn)
    return saida


# ============================================================ classificação
def precisa_ler(arq: dict, conferir_todos: bool, curvas: bool) -> bool:
    if not arq["candidato"]:
        return False
    if arq["verificado"] == "conteudo":
        if curvas:   # já conferido: só falta a lista de curvas, e só para perfil
            return arq["formato"] in BYTES_CURVAS and arq["curvas"] is None
        return False
    return curvas or conferir_todos or arq["ext"] not in EXT_CONFIAVEIS


def classificar(cliente: ClienteREATE, arq: dict, curvas: bool, familia=None) -> dict:
    """Lê o começo do arquivo no portal e devolve as colunas a gravar."""
    if not arq["tamanho"]:
        return {"formato": "", "envelope": "", "verificado": "conteudo", "erro": "arquivo vazio"}
    dados = cliente.ler_inicio(arq["caminho"], BYTES_FORMATO)
    r = formatos.pelos_bytes(dados)
    saida = {"formato": r["formato"], "envelope": r["envelope"], "verificado": "conteudo", "erro": ""}
    if curvas and r["formato"] in BYTES_CURVAS:
        n = min(arq["tamanho"], BYTES_CURVAS[r["formato"]])
        dados = dados if n <= len(dados) else cliente.ler_inicio(arq["caminho"], n)
        completo = n >= arq["tamanho"]
        lista = curvas_do_inicio(dados, r["formato"], completo)
        saida["curvas"] = json.dumps(lista, ensure_ascii=False)
        saida["curvas_completas"] = int(completo or r["formato"] == "las")
        if familia:
            saida["familias"] = json.dumps(sorted({f for f in map(familia, lista) if f}))
    return saida


def situacao_do_poco(arquivos: list[dict]) -> tuple[str, list[str]]:
    cand = [a for a in arquivos if a["candidato"]]
    fmts = []
    for a in cand:
        f = a["formato"] or formatos.pela_extensao(a["nome"])
        if a["verificado"] != "conteudo" and a["ext"] not in EXT_CONFIAVEIS:
            f = ""                                   # .tif ainda não conferido: não se sabe
        fmts.append(f)
    if any(f in formatos.PERFIL for f in fmts):
        sit = "digital"
    elif not cand:
        sit = "sem_perfil"
    elif any(f == "" for f in fmts):
        sit = "pendente"
    elif all(f in formatos.DOCUMENTO for f in fmts):
        sit = "imagem"
    else:
        sit = "sem_perfil"                           # só outros arquivos (txt, zip…) na pasta
    return sit, sorted({f for f in fmts if f})


def atualizar_pocos(banco: Banco, bacia: str, caminhos: list[str] | None = None) -> None:
    with banco.conexao() as c:
        if caminhos is None:
            caminhos = [r[0] for r in c.execute("SELECT caminho FROM acervo_pocos WHERE bacia = ?", (bacia,))]
        for cam in caminhos:
            arqs = [dict(r) for r in c.execute(
                "SELECT * FROM acervo_arquivos WHERE bacia = ? AND poco_caminho = ?", (bacia, cam))]
            sit, fmts = situacao_do_poco(arqs)
            fams = sorted({f for a in arqs if a.get("familias") for f in json.loads(a["familias"])})
            c.execute("""UPDATE acervo_pocos SET situacao = ?, formatos = ?, familias = ?,
                                n_perfil = ?, classificado_em = ? WHERE bacia = ? AND caminho = ?""",
                      (sit, ",".join(fmts), ",".join(fams) if fams else None,
                       sum(1 for a in arqs if a["candidato"]), agora(), bacia, cam))


# ================================================================ execução
class Levantamento:
    """Roda numa thread. `emitir(evento)` recebe o progresso:
    {"tipo": "etapa"|"listagem"|"arquivo"|"fim"|"erro"|"cancelado", ...}."""

    def __init__(self, banco: Banco, bacia: str, categorias: list[str], *, emitir,
                 curvas: bool = False, conferir_todos: bool = False, familia=None,
                 cliente: ClienteREATE | None = None, agp: bool = False,
                 pasta_agp: str | None = None, estratigrafia: dict | None = None,
                 esquemas: bool = False, pasta_projeto: str | None = None, tessdata: str | None = None,
                 ferramentas: dict | None = None, direcionais: bool = False):
        self.banco, self.bacia, self.categorias = banco, bacia, list(categorias)
        self.emitir, self.curvas, self.conferir_todos, self.familia = emitir, curvas, conferir_todos, familia
        self.agp, self.pasta_agp, self.estratigrafia = agp, pasta_agp, estratigrafia or {}
        self.esquemas, self.pasta_projeto, self.tessdata = esquemas, pasta_projeto, tessdata
        self.ferramentas = ferramentas
        self.direcionais = direcionais
        self.cliente = cliente or ClienteREATE.da_bacia(bacia)
        self.cancelar = threading.Event()
        self.thread: threading.Thread | None = None
        self.resultado: dict | None = None

    terminado = False

    def iniciar(self) -> None:
        self.thread = threading.Thread(target=self._rodar, name="levantamento", daemon=True)
        self.thread.start()

    @property
    def ativo(self) -> bool:
        return self.thread is not None and self.thread.is_alive() and not self.terminado

    def _checar(self):
        if self.cancelar.is_set():
            raise Cancelado()

    def _rodar(self):
        # `terminado` antes de avisar a janela: ela pergunta logo em seguida se
        # ainda há levantamento ativo
        try:
            self.resultado = self.executar()
            self.terminado = True
            self.emitir({"tipo": "fim", **self.resultado})
        except Cancelado:
            atualizar_pocos(self.banco, self.bacia)
            self.terminado = True
            self.emitir({"tipo": "cancelado", "resumo": resumo(self.banco, self.bacia)})
        except ErroREATE as e:
            atualizar_pocos(self.banco, self.bacia)
            self.terminado = True
            self.emitir({"tipo": "erro", "erro": str(e)})
        except Exception as e:  # noqa: BLE001 — a thread nunca morre calada
            logging.getLogger("siapp.levantamento").exception("levantamento falhou")
            self.terminado = True
            self.emitir({"tipo": "erro", "erro": f"{type(e).__name__}: {e}"})

    def executar(self) -> dict:
        base, cats = self.cliente.descobrir_categorias()
        nomes = {c["nome"] for c in cats}
        alvo = [c for c in self.categorias if c in nomes] or sorted(nomes)
        # 1. listagem
        containers = []
        for cat in alvo:
            self._checar()
            self.emitir({"tipo": "etapa", "texto": f"Lendo a estrutura de {cat}…"})
            itens = self.cliente.listar(base + cat)
            partes = [i for i in itens if i["pasta"] and eh_pasta_parte(i["nome"])]
            if partes:
                containers += [(cat, p["nome"], p["caminho"]) for p in partes]
            else:
                containers.append((cat, None, base + cat + "/"))
        n_pocos = 0
        for k, (cat, parte, cam) in enumerate(containers, 1):
            self._checar()
            self.emitir({"tipo": "listagem", "feito": k - 1, "total": len(containers),
                         "texto": f"Listando {cat}{' / ' + parte if parte else ''}"})
            pocos = agrupar_por_poco(cam, self._listar_tudo(cam))
            n_pocos += gravar_listagem(self.banco, self.bacia, cat, parte, pocos)
            atualizar_pocos(self.banco, self.bacia, list(pocos))
        self.emitir({"tipo": "listagem", "feito": len(containers), "total": len(containers),
                     "texto": f"{n_pocos} poço(s) listado(s)"})
        # 2. classificação pelo conteúdo
        with self.banco.conexao() as c:
            marcadas = ",".join("?" * len(alvo))
            arqs = [dict(r) for r in c.execute(
                f"""SELECT a.* FROM acervo_arquivos a JOIN acervo_pocos p
                      ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                    WHERE a.bacia = ? AND a.candidato = 1 AND p.categoria IN ({marcadas})
                    ORDER BY a.poco_caminho, a.caminho""", (self.bacia, *alvo))]
        fila = [a for a in arqs if precisa_ler(a, self.conferir_todos, self.curvas)]
        tocados: set[str] = set()
        for k, a in enumerate(fila, 1):
            self._checar()
            try:
                col = classificar(self.cliente, a, self.curvas, self.familia)
            except ErroREATE as e:
                col = {"erro": str(e)}
            col["lido_em"] = agora()
            with self.banco.conexao() as c:
                c.execute(f"UPDATE acervo_arquivos SET {', '.join(k2 + ' = ?' for k2 in col)} "
                          "WHERE bacia = ? AND caminho = ?", (*col.values(), self.bacia, a["caminho"]))
            tocados.add(a["poco_caminho"])
            if k % 10 == 0 or k == len(fila):
                atualizar_pocos(self.banco, self.bacia, list(tocados))
                tocados.clear()
                self.emitir({"tipo": "arquivo", "feito": k, "total": len(fila),
                             "texto": f"Conferindo arquivos pelo conteúdo: {a['nome']}"})
        n_agp = self._ler_agps(alvo) if self.agp else 0
        n_dir = self._ler_direcionais(alvo) if self.direcionais and self.pasta_projeto else 0
        n_esq = self._ler_esquemas(alvo) if self.esquemas and self.ferramentas and self.pasta_projeto else 0
        return {"pocos": n_pocos, "arquivos_lidos": len(fila), "agps_lidos": n_agp, "esquemas_lidos": n_esq,
                "direcionais_lidos": n_dir, "resumo": resumo(self.banco, self.bacia)}

    def _ler_direcionais(self, alvo: list[str]) -> int:
        """3b. Dados direcionais (~1–10 KB por poço): a trajetória, para o bloco 3D."""
        fila = mdi.pendentes(self.banco, self.bacia, alvo)

        def progresso(k, n, nome):
            self._checar()
            if k % 5 == 1 or k == n:
                self.emitir({"tipo": "direcional", "feito": k - 1, "total": n,
                             "texto": f"Lendo os dados direcionais: {nome}"})
        return mdi.ler_do_portal(self.banco, self.cliente, self.bacia, fila, pasta_projeto=self.pasta_projeto,
                                 progresso=progresso, cancelar=self.cancelar)

    def _ler_esquemas(self, alvo: list[str]) -> int:
        """4. Esquemas de ferramentas (opcional; ~200 KB e ~2 s de OCR cada): só os ainda não lidos."""
        fila = mfe.pendentes(self.banco, self.bacia, alvo)

        def progresso(k, n, nome):
            self._checar()
            if k % 2 == 1 or k == n:
                self.emitir({"tipo": "esquema", "feito": k - 1, "total": n,
                             "texto": f"Lendo os esquemas de ferramentas: {nome}"})
        return mfe.ler_do_portal(self.banco, self.cliente, self.bacia, fila, self.ferramentas,
                                 pasta_projeto=self.pasta_projeto, tessdata=self.tessdata,
                                 progresso=progresso, cancelar=self.cancelar)

    def _ler_agps(self, alvo: list[str]) -> int:
        """3. AGP de cada poço (~20–160 KB): só os novos, os que mudaram de tamanho e os
        lidos por um leitor mais antigo — estes, da cópia local, sem baixar de novo."""
        with self.banco.conexao() as c:
            marcadas = ",".join("?" * len(alvo))
            cands = [dict(r) for r in c.execute(
                f"""SELECT a.caminho, a.nome, a.pasta, a.tamanho, a.poco_caminho, p.poco_id,
                           g.arquivo_local AS local_antigo, g.tamanho AS tamanho_antigo
                    FROM acervo_arquivos a JOIN acervo_pocos p
                      ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                    LEFT JOIN agp g ON g.bacia = a.bacia AND g.caminho = a.caminho
                    WHERE a.bacia = ? AND p.categoria IN ({marcadas}) AND lower(a.nome) LIKE '%.txt'
                      AND (g.caminho IS NULL OR g.tamanho IS NOT a.tamanho OR coalesce(g.leitor, 1) < ?)
                    ORDER BY a.caminho""", (self.bacia, *alvo, magp.VERSAO_LEITOR))]
        fila = [a for a in cands if magp.eh_agp(a["nome"], a["pasta"])]
        for k, a in enumerate(fila, 1):
            self._checar()
            copia = self._copia_local(a)
            texto, local, erro = self._texto_local(copia) if copia else self._baixar_agp(a)
            magp.gravar(self.banco, bacia=self.bacia, caminho=a["caminho"], poco_caminho=a["poco_caminho"],
                        poco_pasta=a["poco_id"], tamanho=a["tamanho"], texto=texto,
                        estratigrafia=self.estratigrafia, arquivo_local=local, erro=erro)
            if k % 5 == 0 or k == len(fila):
                self.emitir({"tipo": "agp", "feito": k, "total": len(fila),
                             "texto": f"Lendo os AGPs (topos de formação): {a['nome']}"})
        return len(fila)

    def _baixar_agp(self, a: dict) -> tuple[str | None, str, str]:
        """(texto, cópia local relativa ao projeto, erro)."""
        try:
            dados = self.cliente.ler_inicio(a["caminho"], max(1, min(a["tamanho"] or 1, 4 * 1024 * 1024)))
        except ErroREATE as e:
            return None, "", str(e)
        local = ""
        if self.pasta_agp:
            destino = os.path.join(self.pasta_agp, re.sub(r"[^\w .-]+", "_", self.bacia), a["nome"])
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "wb") as f:
                f.write(dados)
            # guardado relativo à pasta do projeto: o projeto pode mudar de lugar
            local = os.path.relpath(destino, os.path.dirname(os.path.abspath(self.pasta_agp))).replace(os.sep, "/")
        return magp.decodificar(dados), local, ""

    @staticmethod
    def _texto_local(copia: tuple[str, str]) -> tuple[str, str, str]:
        with open(copia[0], "rb") as f:
            return magp.decodificar(f.read()), copia[1], ""

    def _copia_local(self, a: dict) -> tuple[str, str] | None:
        """(caminho absoluto, relativo) da cópia guardada, se ainda for o mesmo arquivo."""
        if not (self.pasta_agp and a.get("local_antigo") and a.get("tamanho_antigo") == a["tamanho"]):
            return None
        absoluto = os.path.join(os.path.dirname(os.path.abspath(self.pasta_agp)), a["local_antigo"])
        if not os.path.isfile(absoluto) or os.path.getsize(absoluto) != a["tamanho"]:
            return None
        return absoluto, a["local_antigo"]

    def _listar_tudo(self, cam: str) -> list[dict]:
        """Listagem recursiva numa requisição; se o portal recusar, poço a poço."""
        try:
            return self.cliente.listar_arvore(cam)
        except ErroREATE:
            itens = []
            for p in self.cliente.listar(cam):
                self._checar()
                itens.append(p)
                if p["pasta"]:
                    itens += self.cliente.listar_arvore(p["caminho"])
            return itens


# ================================================================== resumo
def resumo(banco: Banco, bacia: str) -> dict:
    with banco.leitura() as c:
        pocos = [dict(r) for r in c.execute("SELECT * FROM acervo_pocos WHERE bacia = ?", (bacia,))]
        arqs = c.execute("""SELECT ext, formato, envelope, verificado, count(*) AS n, sum(tamanho) AS b
                            FROM acervo_arquivos WHERE bacia = ? AND candidato = 1
                            GROUP BY ext, formato, envelope, verificado""", (bacia,)).fetchall()
    if not pocos:
        return {"bacia": bacia, "pocos": 0}
    por_sit = Counter(p["situacao"] or "pendente" for p in pocos)
    por_cat: dict[str, Counter] = {}
    for p in pocos:
        por_cat.setdefault(p["categoria"] or "—", Counter())[p["situacao"] or "pendente"] += 1
    fam = Counter(f for p in pocos if p["familias"] for f in p["familias"].split(","))
    com_curvas = sum(1 for p in pocos if p["familias"])
    enganos = Counter()
    formatos_cont = Counter()
    for r in arqs:
        if r["verificado"] == "conteudo" and r["formato"]:
            formatos_cont[r["formato"] + ("-em-tif" if r["envelope"] == "tif" else "")] += r["n"]
            por_nome = formatos.pela_extensao("x" + r["ext"])
            if por_nome and por_nome != r["formato"]:
                enganos[f"{r['ext']} → {formatos.NOMES.get(r['formato'], r['formato'])}"] += r["n"]
    from .fontes import criterio
    digitais = {p["poco_id"] or p["nome_pasta"] or p["caminho"] for p in pocos if p["situacao"] == "digital"}
    return {
        "bacia": bacia, "pocos": len(pocos),
        "pocos_distintos": len({p["poco_id"] or p["nome_pasta"] or p["caminho"] for p in pocos}),
        # 0.63 (A13): as situações contam PASTAS do portal; este número conta POÇOS, com o critério ao lado
        "perfil_digital": {"n": len(digitais), **criterio("conteudo")},
        "situacoes": {s: por_sit.get(s, 0) for s in SITUACOES},
        "por_categoria": {k: {s: v.get(s, 0) for s in SITUACOES} for k, v in sorted(por_cat.items())},
        "familias": {f: fam.get(f, 0) for f in FAMILIAS_RESUMO}, "pocos_com_curvas": com_curvas,
        "pocos_com_interpretacao": sum(1 for p in pocos if p["familias"]
                                       and set(p["familias"].split(",")) & set(FAMILIAS_INTERP)),
        "formatos": dict(formatos_cont.most_common()),
        "extensao_enganosa": dict(enganos.most_common()),
        "arquivos_conferidos": sum(r["n"] for r in arqs if r["verificado"] == "conteudo"),
        "arquivos_candidatos": sum(r["n"] for r in arqs),
        "atualizado_em": max((p["classificado_em"] or p["listado_em"] or "") for p in pocos),
        **_resumo_agp(banco, bacia),
        **mfe.resumo(banco, bacia),
        **mdi.resumo(banco, bacia),
    }


def _resumo_agp(banco: Banco, bacia: str) -> dict:
    with banco.conexao() as c:
        lidos, outro, com_topos = c.execute(
            """SELECT count(*), sum(confere = 0),
                      sum(EXISTS (SELECT 1 FROM agp_unidades u WHERE u.bacia = g.bacia AND u.caminho = g.caminho))
               FROM agp g WHERE bacia = ? AND dados IS NOT NULL""", (bacia,)).fetchone()
        # os dois leiautes: <poço>_agp.txt e, na pasta AGP, <poço>_dados.txt / _cabecalho.txt
        disp = sum(magp.eh_agp(n, pa) for n, pa in c.execute(
            "SELECT nome, pasta FROM acervo_arquivos WHERE bacia = ? AND lower(nome) LIKE '%.txt'", (bacia,)))
    return {"agp_disponiveis": disp, "agp_lidos": lidos or 0, "agp_com_topos": com_topos or 0,
            "agp_de_outro_poco": outro or 0}


def arquivos_do_poco(banco: Banco, poco_id: str) -> list[dict]:
    with banco.conexao() as c:
        return [dict(r) for r in c.execute(
            """SELECT a.bacia, a.caminho, a.nome, a.pasta, a.ext, a.tamanho, a.formato, a.envelope,
                      a.verificado, a.curvas, a.curvas_completas, a.familias, a.erro, p.categoria
               FROM acervo_arquivos a JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
               WHERE p.poco_id = ? AND a.candidato = 1 ORDER BY a.caminho""", (poco_id,))]


def exportar_csv(banco: Banco, bacia: str, pasta: str, coordenadas: bool = True) -> list[str]:
    """Dois CSV (';' e vírgula decimal, para o Excel em português): um por poço
    e um por arquivo de perfil. Devolve os caminhos."""
    os.makedirs(pasta, exist_ok=True)
    data = agora()[:10]
    with banco.conexao() as c:
        pocos = [dict(r) for r in c.execute(
            """SELECT a.*, p.lat, p.lon, p.campo, p.terra_mar, p.tipo AS categoria_anp
               FROM acervo_pocos a LEFT JOIN pocos p ON p.id = a.poco_id
               WHERE a.bacia = ? ORDER BY a.categoria, a.nome_pasta""", (bacia,))]
        arqs = [dict(r) for r in c.execute(
            """SELECT p.poco_id, a.* FROM acervo_arquivos a JOIN acervo_pocos p
                 ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
               WHERE a.bacia = ? AND a.candidato = 1 ORDER BY a.caminho""", (bacia,))]

    def num(v, casas=6):
        return "" if v is None else f"{v:.{casas}f}".replace(".", ",")

    saidas = []
    nome_base = f"levantamento_{re.sub(r'[^A-Za-z0-9]+', '_', bacia)}_{data}"
    cam = os.path.join(pasta, nome_base + "_pocos.csv")
    with open(cam, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["bacia", "categoria_reate", "parte", "poco", "pasta_reate", "situacao",
                    "arquivos_de_perfil", "formatos", *[f"tem_{x}" for x in FAMILIAS_RESUMO],
                    "familias", "arquivos_no_poco", "mb_no_poco", "campo", "terra_mar", "lat", "lon",
                    "levantado_em"])
        for p in pocos:
            fams = set((p["familias"] or "").split(",")) - {""}
            w.writerow([p["bacia"], p["categoria"], p["parte"] or "", p["poco_id"], p["caminho"],
                        p["situacao"] or "pendente", p["n_perfil"] or 0, p["formatos"] or "",
                        *[("sim" if x in fams else ("não" if p["familias"] else "")) for x in FAMILIAS_RESUMO],
                        " ".join(sorted(fams)), p["n_arquivos"], num((p["bytes"] or 0) / 1e6, 1),
                        p["campo"] or "", p["terra_mar"] or "",
                        num(p["lat"]) if coordenadas else "", num(p["lon"]) if coordenadas else "",
                        p["classificado_em"] or p["listado_em"]])
    saidas.append(cam)
    cam = os.path.join(pasta, nome_base + "_arquivos.csv")
    with open(cam, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["poco", "caminho_reate", "pasta", "nome", "extensao", "bytes", "formato_real",
                    "envelope", "conferido_pelo_conteudo", "curvas", "lista_de_curvas_completa", "erro"])
        for a in arqs:
            w.writerow([a["poco_id"], a["caminho"], a["pasta"], a["nome"], a["ext"], a["tamanho"],
                        a["formato"] or "", a["envelope"] or "", "sim" if a["verificado"] == "conteudo" else "não",
                        " ".join(json.loads(a["curvas"])) if a["curvas"] else "",
                        "" if a["curvas"] is None else ("sim" if a["curvas_completas"] else "não (só o começo)"),
                        a["erro"] or ""])
    saidas.append(cam)
    with banco.conexao() as c:
        topos = [dict(r) for r in c.execute(
            """SELECT u.*, g.poco_agp, g.confere FROM agp_unidades u JOIN agp g
                 ON g.bacia = u.bacia AND g.caminho = u.caminho
               WHERE u.bacia = ? ORDER BY u.poco_id, u.topo, u.ordem""", (bacia,))]
    if topos:
        cam = os.path.join(pasta, nome_base + "_topos.csv")
        with open(cam, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["poco", "tipo", "nivel", "sigla", "codigo", "nome", "topo_m", "cota_topo_m",
                        "desc_topo", "base_m", "cota_base_m", "desc_base", "fonte_interpretacao", "data",
                        "agp_do_proprio_poco", "arquivo_agp"])
            for u in topos:
                w.writerow([u["poco_id"], u["tip"], u["nivel"], u["sigla"], u["codigo"], u["nome"],
                            num(u["topo"], 2), num(u["cota_topo"], 2), u["desc_topo"], num(u["base"], 2),
                            num(u["cota_base"], 2), u["desc_base"], u["fonte"], u["data"],
                            "sim" if u["confere"] else "não", u["caminho"]])
        saidas.append(cam)
    return saidas
