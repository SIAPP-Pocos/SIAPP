"""
Banco do projeto: <projeto>/projeto.sqlite.

É o mesmo modelo de dados da base comunitária (repositório SIAPP-dados):
o banco local = base comunitária baixada + pacotes importados + o que o
próprio usuário fez. Cada linha diz de onde veio (`origem`):

    local    criado neste computador (exportável como contribuição)
    pacote   veio de um pacote de contribuição importado (desfazível pelo id)
    base     veio da base comunitária publicada (substituída a cada atualização)

Precedência quando duas origens discordam: local > pacote > base.

Tabelas:
    meta       versão do esquema e marcas de migração
    vocab      palavras, correções de OCR e exceções ("o OCR estava certo")
    pocos      cadastro de poços (ANP) — uma linha por poço, id = nome canônico
    apelidos   outras grafias do nome do poço → id canônico
    reate      pastas de poço vistas no portal REATE
    arquivos   arquivos baixados, com procedência e hash SHA-256
    perfis     arquivos de perfil inventariados (DLIS/LIS/LAS)
    curvas     curvas de cada perfil, com família, unidade e intervalo
    fatos      dados com procedência: topo de formação, revestimento, intervalo-alvo…
    pacotes    contribuições exportadas/importadas e bases aplicadas

O texto dos documentos continua em texto/*.json (grande demais para o banco)
e o índice de busca em texto/indice.sqlite (derivado, pode ser refeito).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime

from .vocabulario import normalizar

ARQUIVO = "projeto.sqlite"
ORIGENS = ("local", "pacote", "base")
_PRIORIDADE = {"base": 0, "pacote": 1, "local": 2}

# Cada item é aplicado uma vez, em ordem. Nunca edite um item já publicado:
# acrescente outro (o banco de quem já usa o SIAPP é atualizado sozinho).
MIGRACOES: list[str] = [
    # 1 — esquema inicial (SIAPP 0.7)
    """
    CREATE TABLE vocab(
        id INTEGER PRIMARY KEY,
        tipo TEXT NOT NULL CHECK (tipo IN ('palavra', 'correcao', 'ignorar')),
        de TEXT NOT NULL,
        chave TEXT NOT NULL,
        para TEXT,
        origem TEXT NOT NULL CHECK (origem IN ('local', 'pacote', 'base')),
        pacote TEXT NOT NULL DEFAULT '',
        autor TEXT,
        criado_em TEXT NOT NULL,
        UNIQUE (tipo, chave, origem, pacote)
    );
    CREATE TABLE pocos(
        id TEXT PRIMARY KEY,
        nome_anp TEXT, cadastro TEXT, operador TEXT, estado TEXT, bacia TEXT, bloco TEXT,
        campo TEXT, terra_mar TEXT, tipo INTEGER, categoria TEXT, reclassificacao TEXT,
        situacao TEXT, inicio TEXT, termino TEXT, conclusao TEXT, titularidade TEXT,
        lat REAL, lon REAL, datum TEXT, direcao TEXT,
        prof_vertical REAL, prof_sondador REAL, prof_medida REAL,
        mesa_rotativa REAL, cota_altimetrica REAL, lamina_agua REAL,
        formacao_final TEXT, dados_anp TEXT, fonte TEXT, atualizado_em TEXT
    );
    CREATE INDEX pocos_cadastro ON pocos(cadastro);
    CREATE INDEX pocos_bacia ON pocos(bacia);
    CREATE TABLE apelidos(
        chave TEXT PRIMARY KEY,
        poco_id TEXT NOT NULL,
        origem TEXT NOT NULL,
        pacote TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE reate(
        bacia TEXT NOT NULL, caminho TEXT NOT NULL, nome_pasta TEXT NOT NULL,
        poco_id TEXT, categoria TEXT, parte TEXT, visto_em TEXT,
        PRIMARY KEY (bacia, caminho)
    );
    CREATE INDEX reate_poco ON reate(poco_id);
    CREATE TABLE arquivos(
        rel TEXT PRIMARY KEY, bacia TEXT, poco_id TEXT, caminho_remoto TEXT,
        bytes INTEGER, sha256 TEXT, tipo TEXT, baixado_em TEXT
    );
    CREATE INDEX arquivos_poco ON arquivos(poco_id);
    CREATE INDEX arquivos_sha ON arquivos(sha256);
    CREATE TABLE perfis(
        rel TEXT PRIMARY KEY, poco_id TEXT, formato TEXT, n_quadros INTEGER,
        n_curvas INTEGER, topo_m REAL, base_m REAL, cabecalho TEXT,
        inventariado_em TEXT, erro TEXT
    );
    CREATE TABLE curvas(
        rel TEXT NOT NULL, quadro TEXT NOT NULL, mnemonico TEXT NOT NULL,
        familia TEXT, unidade TEXT, descricao TEXT, topo_m REAL, base_m REAL,
        passo_m REAL, n_amostras INTEGER, n_validas INTEGER, dimensao INTEGER,
        PRIMARY KEY (rel, quadro, mnemonico)
    );
    CREATE INDEX curvas_familia ON curvas(familia);
    CREATE TABLE fatos(
        id TEXT PRIMARY KEY,
        poco_id TEXT NOT NULL,
        tipo TEXT NOT NULL,
        nome TEXT, valor TEXT, unidade TEXT, prof_topo REAL, prof_base REAL,
        fonte_sha256 TEXT, fonte_caminho TEXT, fonte_bacia TEXT, fonte_rel TEXT,
        pagina INTEGER, caixa TEXT,
        observacao TEXT, autor TEXT, criado_em TEXT NOT NULL,
        origem TEXT NOT NULL CHECK (origem IN ('local', 'pacote', 'base')),
        pacote TEXT NOT NULL DEFAULT '',
        exportado_em TEXT
    );
    CREATE INDEX fatos_poco ON fatos(poco_id);
    CREATE TABLE pacotes(
        id TEXT PRIMARY KEY,
        tipo TEXT NOT NULL CHECK (tipo IN ('exportado', 'importado', 'base')),
        autor TEXT, arquivo TEXT, criado_em TEXT, aplicado_em TEXT, resumo TEXT
    );
    """,
    # 2 — levantamento do acervo (SIAPP 0.12): o que existe no portal, pelo conteúdo
    """
    CREATE TABLE acervo_pocos(
        bacia TEXT NOT NULL, caminho TEXT NOT NULL, nome_pasta TEXT, poco_id TEXT,
        categoria TEXT, parte TEXT, n_arquivos INTEGER, bytes INTEGER,
        n_perfil INTEGER, situacao TEXT, formatos TEXT, familias TEXT,
        listado_em TEXT, classificado_em TEXT,
        PRIMARY KEY (bacia, caminho)
    );
    CREATE INDEX acervo_pocos_id ON acervo_pocos(poco_id);
    CREATE TABLE acervo_arquivos(
        bacia TEXT NOT NULL, caminho TEXT NOT NULL, poco_caminho TEXT NOT NULL,
        nome TEXT, pasta TEXT, ext TEXT, tamanho INTEGER, candidato INTEGER,
        formato TEXT, envelope TEXT, verificado TEXT, curvas TEXT,
        curvas_completas INTEGER, familias TEXT, erro TEXT, lido_em TEXT,
        PRIMARY KEY (bacia, caminho)
    );
    CREATE INDEX acervo_arquivos_poco ON acervo_arquivos(bacia, poco_caminho);
    """,
    # 3 — AGP da ANP (Dados Gerais de Poços): topos, cabeçalho de perfilagem… (SIAPP 0.14)
    """
    CREATE TABLE agp(
        bacia TEXT NOT NULL, caminho TEXT NOT NULL, poco_caminho TEXT, poco_pasta TEXT,
        poco_id TEXT, poco_agp TEXT, confere INTEGER, tamanho INTEGER, arquivo_local TEXT,
        lido_em TEXT, dados TEXT, erro TEXT,
        PRIMARY KEY (bacia, caminho)
    );
    CREATE INDEX agp_poco ON agp(poco_id);
    CREATE TABLE agp_unidades(
        bacia TEXT NOT NULL, caminho TEXT NOT NULL, poco_id TEXT, ordem INTEGER,
        tip TEXT, ql TEXT, nivel TEXT, sigla TEXT, codigo TEXT, nome TEXT,
        topo REAL, cota_topo REAL, desc_topo TEXT, base REAL, cota_base REAL, desc_base TEXT,
        metodo TEXT, fonte TEXT, data TEXT
    );
    CREATE INDEX agp_unidades_poco ON agp_unidades(poco_id);
    CREATE INDEX agp_unidades_codigo ON agp_unidades(codigo);
    """,
    # 4 — versão do leitor que leu cada AGP: leitura melhor relê da cópia local (SIAPP 0.14.1)
    """
    ALTER TABLE agp ADD COLUMN leitor INTEGER;
    CREATE INDEX agp_unidades_sigla ON agp_unidades(sigla);
    """,
]


def agora() -> str:
    """Data e hora com fuso (2026-10-16T10:05:00-03:00), como pede o formato de contribuição."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def com_fuso(iso: str | None) -> str | None:
    """Acrescenta o fuso local a uma data sem fuso (gravada pelo SIAPP 0.6/0.7)."""
    if not iso or iso[-6] in "+-" or iso.endswith("Z"):
        return iso
    try:
        return datetime.fromisoformat(iso).astimezone().isoformat(timespec="seconds")
    except ValueError:
        return iso


def novo_id() -> str:
    return str(uuid.uuid4())


class Banco:
    def __init__(self, caminho: str):
        self.caminho = caminho
        os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
        # Downloads e OCR gravam de outras threads: uma escrita por vez.
        self._trava = threading.RLock()
        with self.conexao() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT)")
            versao = int(self.meta("versao_esquema", "0", c))
            for n, sql in enumerate(MIGRACOES[versao:], start=versao + 1):
                c.executescript(sql)
                self.definir_meta("versao_esquema", str(n), c)

    @contextmanager
    def conexao(self):
        with self._trava:
            c = sqlite3.connect(self.caminho, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys=ON")
            try:
                yield c
                c.commit()
            except Exception:
                c.rollback()
                raise
            finally:
                c.close()

    # ------------------------------------------------------------------ meta
    def meta(self, chave: str, padrao=None, c=None):
        if c is None:
            with self.conexao() as c:
                return self.meta(chave, padrao, c)
        r = c.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
        return r[0] if r else padrao

    def definir_meta(self, chave: str, valor: str, c=None):
        if c is None:
            with self.conexao() as c:
                return self.definir_meta(chave, valor, c)
        c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (chave, valor))

    @property
    def versao_esquema(self) -> int:
        return int(self.meta("versao_esquema", "0"))

    # ============================================================ vocabulário
    def vocab_definir(self, tipo: str, de: str, para: str | None = None, *, origem: str = "local",
                      pacote: str = "", autor: str | None = None, c=None) -> None:
        """Cria ou substitui (mesmo tipo + mesma palavra + mesma origem/pacote)."""
        if c is None:
            with self.conexao() as c:
                return self.vocab_definir(tipo, de, para, origem=origem, pacote=pacote,
                                          autor=autor, c=c)
        c.execute("""INSERT INTO vocab (tipo, de, chave, para, origem, pacote, autor, criado_em)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                     ON CONFLICT (tipo, chave, origem, pacote)
                     DO UPDATE SET de = excluded.de, para = excluded.para,
                                   autor = excluded.autor, criado_em = excluded.criado_em""",
                  (tipo, de, normalizar(de), para, origem, pacote, autor, agora()))

    def vocab_remover(self, tipo: str, de: str, origem: str = "local") -> int:
        with self.conexao() as c:
            return c.execute("DELETE FROM vocab WHERE tipo = ? AND chave = ? AND origem = ?",
                             (tipo, normalizar(de), origem)).rowcount

    def vocab_linhas(self, origem: str | None = None) -> list[dict]:
        with self.conexao() as c:
            if origem:
                q = c.execute("SELECT * FROM vocab WHERE origem = ? ORDER BY tipo, chave", (origem,))
            else:
                q = c.execute("SELECT * FROM vocab ORDER BY tipo, chave")
            return [dict(r) for r in q]

    def vocab_local(self) -> dict:
        """O que o usuário fez neste computador, no formato antigo do JSON."""
        v = {"palavras": [], "correcoes": {}, "ignorar": []}
        for r in self.vocab_linhas("local"):
            if r["tipo"] == "palavra":
                v["palavras"].append(r["de"])
            elif r["tipo"] == "ignorar":
                v["ignorar"].append(r["de"])
            else:
                v["correcoes"][r["de"]] = r["para"]
        return v

    def vocab_efetivo(self) -> dict:
        """Vocabulário que o corretor usa, juntando as origens com precedência
        local > pacote > base. Devolve também a origem de cada correção, para a
        interface pintar de cores diferentes o que veio da comunidade."""
        palavras: dict[str, str] = {}
        ignorar: dict[str, str] = {}
        correcoes: dict[str, tuple[int, str, str, str]] = {}   # chave -> (prio, de, para, origem)
        for r in self.vocab_linhas():
            prio = _PRIORIDADE[r["origem"]]
            if r["tipo"] == "palavra":
                palavras.setdefault(r["chave"], r["de"])
            elif r["tipo"] == "ignorar":
                ignorar.setdefault(r["chave"], r["de"])
            else:
                atual = correcoes.get(r["chave"])
                if atual is None or prio > atual[0]:
                    correcoes[r["chave"]] = (prio, r["de"], r["para"], r["origem"])
        # "O OCR estava certo" dito AQUI vale também contra correções da comunidade.
        locais_ignorar = {r["chave"] for r in self.vocab_linhas("local") if r["tipo"] == "ignorar"}
        ef = {k: v for k, v in correcoes.items() if not (k in locais_ignorar and v[3] != "local")}
        return {"palavras": list(palavras.values()),
                "ignorar": list(ignorar.values()),
                "correcoes": {de: para for _, de, para, _ in ef.values()},
                "origens": {k: v[3] for k, v in ef.items()}}

    def migrar_vocab_json(self, caminho_json: str) -> int:
        """Traz o vocabulario_projeto.json (SIAPP ≤ 0.6) para o banco, uma vez só.
        O JSON fica no lugar, intocado, como cópia de segurança."""
        if self.meta("migrou_vocab_json") or not os.path.isfile(caminho_json):
            return 0
        try:
            with open(caminho_json, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            d = {}
        n = 0
        with self.conexao() as c:
            for p in d.get("palavras", []):
                self.vocab_definir("palavra", p, c=c)
                n += 1
            for de, para in d.get("correcoes", {}).items():
                if de.strip():
                    self.vocab_definir("correcao", de, para, c=c)
                    n += 1
            for p in d.get("ignorar", []):
                self.vocab_definir("ignorar", p, c=c)
                n += 1
            self.definir_meta("migrou_vocab_json", agora(), c)
        return n

    # ============================================================== arquivos
    def registrar_arquivo(self, rel: str, *, bacia: str = "", poco_id: str | None = None,
                          caminho_remoto: str = "", bytes_: int = 0, sha256: str | None = None,
                          tipo: str = "", baixado_em: str | None = None) -> None:
        with self.conexao() as c:
            c.execute("""INSERT INTO arquivos VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                         ON CONFLICT (rel) DO UPDATE SET
                           bacia = excluded.bacia, poco_id = COALESCE(excluded.poco_id, arquivos.poco_id),
                           caminho_remoto = COALESCE(NULLIF(excluded.caminho_remoto, ''), arquivos.caminho_remoto),
                           bytes = excluded.bytes, sha256 = COALESCE(excluded.sha256, arquivos.sha256),
                           tipo = excluded.tipo, baixado_em = COALESCE(excluded.baixado_em, arquivos.baixado_em)""",
                      (rel, bacia, poco_id, caminho_remoto, bytes_, sha256, tipo, baixado_em or agora()))

    def arquivo(self, rel: str) -> dict | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM arquivos WHERE rel = ?", (rel,)).fetchone()
            return dict(r) if r else None

    def arquivos(self, poco_id: str | None = None) -> list[dict]:
        with self.conexao() as c:
            if poco_id:
                q = c.execute("SELECT * FROM arquivos WHERE poco_id = ? ORDER BY rel", (poco_id,))
            else:
                q = c.execute("SELECT * FROM arquivos ORDER BY rel")
            return [dict(r) for r in q]

    def definir_tipo(self, rel: str, tipo: str) -> None:
        with self.conexao() as c:
            c.execute("UPDATE arquivos SET tipo = ? WHERE rel = ?", (tipo, rel))

    def definir_sha(self, rel: str, sha: str) -> None:
        with self.conexao() as c:
            c.execute("UPDATE arquivos SET sha256 = ? WHERE rel = ?", (sha, rel))

    # ================================================================ perfis
    def salvar_inventario(self, rel: str, poco_id: str, inv: dict) -> None:
        """Perfil inventariado: uma linha em perfis e uma por curva em curvas."""
        with self.conexao() as c:
            c.execute("DELETE FROM curvas WHERE rel = ?", (rel,))
            n = 0
            for q in inv["quadros"]:
                for cv in q["curvas"]:
                    c.execute("INSERT OR REPLACE INTO curvas VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                              (rel, q["nome"], cv["mnemonico"], cv["familia"], cv["unidade"],
                               cv["descricao"], cv["topo_m"], cv["base_m"], q["passo_m"],
                               q["n_amostras"], cv["n_validas"], cv["dimensao"]))
                    n += 1
            c.execute("INSERT OR REPLACE INTO perfis VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (rel, poco_id, inv["formato"], len(inv["quadros"]), n, inv["topo_m"],
                       inv["base_m"], json.dumps(inv["cabecalho"], ensure_ascii=False, default=str),
                       inv["inventariado_em"], None))

    def perfil(self, rel: str) -> dict | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM perfis WHERE rel = ?", (rel,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["cabecalho"] = json.loads(d["cabecalho"] or "{}")
        return d

    # ================================================================= fatos
    CAMPOS_FATO = ("id", "poco_id", "tipo", "nome", "valor", "unidade", "prof_topo", "prof_base",
                   "fonte_sha256", "fonte_caminho", "fonte_bacia", "fonte_rel", "pagina", "caixa",
                   "observacao", "autor", "criado_em", "origem", "pacote", "exportado_em")

    def salvar_fato(self, fato: dict, c=None) -> str:
        """Cria (sem id) ou substitui (com id) um fato. Devolve o id."""
        if c is None:
            with self.conexao() as c:
                return self.salvar_fato(fato, c)
        f = {k: fato.get(k) for k in self.CAMPOS_FATO}
        f["id"] = f["id"] or novo_id()
        f["criado_em"] = f["criado_em"] or agora()
        f["origem"] = f["origem"] or "local"
        f["pacote"] = f["pacote"] or ""
        if isinstance(f["caixa"], (list, tuple)):
            f["caixa"] = json.dumps([round(float(x), 4) for x in f["caixa"]])
        c.execute(f"INSERT OR REPLACE INTO fatos ({', '.join(self.CAMPOS_FATO)}) "
                  f"VALUES ({', '.join('?' for _ in self.CAMPOS_FATO)})",
                  [f[k] for k in self.CAMPOS_FATO])
        return f["id"]

    @staticmethod
    def _fato(r) -> dict:
        d = dict(r)
        if d.get("caixa"):
            try:
                d["caixa"] = json.loads(d["caixa"])
            except (TypeError, json.JSONDecodeError):
                d["caixa"] = None
        return d

    def fatos(self, poco_id: str | None = None, *, tipo: str | None = None,
              fonte_rel: str | None = None, pagina: int | None = None,
              origem: str | None = None) -> list[dict]:
        cond, args = [], []
        for campo, valor in (("poco_id", poco_id), ("tipo", tipo), ("fonte_rel", fonte_rel),
                             ("pagina", pagina), ("origem", origem)):
            if valor is not None:
                cond.append(f"{campo} = ?")
                args.append(valor)
        where = ("WHERE " + " AND ".join(cond)) if cond else ""
        with self.conexao() as c:
            q = c.execute(f"SELECT * FROM fatos {where} "
                          f"ORDER BY poco_id, COALESCE(prof_topo, 1e12), tipo, criado_em", args)
            return [self._fato(r) for r in q]

    def fato(self, id_: str) -> dict | None:
        with self.conexao() as c:
            r = c.execute("SELECT * FROM fatos WHERE id = ?", (id_,)).fetchone()
            return self._fato(r) if r else None

    def remover_fato(self, id_: str) -> int:
        """Só fatos locais podem ser apagados; os da comunidade se desfazem pelo pacote."""
        with self.conexao() as c:
            return c.execute("DELETE FROM fatos WHERE id = ? AND origem = 'local'", (id_,)).rowcount

    # =============================================================== pacotes
    def registrar_pacote(self, id_: str, tipo: str, *, autor: str = "", arquivo: str = "",
                         criado_em: str = "", resumo: dict | None = None, c=None) -> None:
        if c is None:
            with self.conexao() as c:
                return self.registrar_pacote(id_, tipo, autor=autor, arquivo=arquivo,
                                             criado_em=criado_em, resumo=resumo, c=c)
        c.execute("INSERT OR REPLACE INTO pacotes VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (id_, tipo, autor, arquivo, criado_em, agora(),
                   json.dumps(resumo or {}, ensure_ascii=False)))

    def pacotes(self, tipo: str | None = None) -> list[dict]:
        with self.conexao() as c:
            q = (c.execute("SELECT * FROM pacotes WHERE tipo = ? ORDER BY aplicado_em DESC", (tipo,))
                 if tipo else c.execute("SELECT * FROM pacotes ORDER BY aplicado_em DESC"))
            saida = []
            for r in q:
                d = dict(r)
                d["resumo"] = json.loads(d["resumo"] or "{}")
                saida.append(d)
            return saida

    def desfazer_pacote(self, id_: str) -> dict:
        """Remove tudo o que um pacote importado trouxe."""
        with self.conexao() as c:
            n = {t: c.execute(f"DELETE FROM {t} WHERE origem = 'pacote' AND pacote = ?",
                              (id_,)).rowcount for t in ("vocab", "fatos", "apelidos")}
            c.execute("DELETE FROM pacotes WHERE id = ? AND tipo = 'importado'", (id_,))
        return n

    def contar(self, tabela: str, where: str = "", args=()) -> int:
        assert tabela.isidentifier()
        with self.conexao() as c:
            return c.execute(f"SELECT count(*) FROM {tabela} {where}", args).fetchone()[0]
