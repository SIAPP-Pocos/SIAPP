"""Dados do poço lidos de documentos (bloco 9): o arcabouço comum dos leitores.

Cada **leitor** é um módulo com:

- `VERSAO` (int) e `NOME`;
- `reconhece(rel) -> bool`: pelo caminho do arquivo no projeto (nome e pasta), barato — decide o
  que tentar ler;
- `DOCUMENTOS` (tipo → nome por extenso) e `PRIORIDADE` (tipo → ordem, quando dois documentos
  trazem o mesmo dado: o de menor número vale na ficha e nos intervalos);
- `ler(caminho) -> dict`: os dados do documento, com a chave `documento` (tipo do formulário);
  levanta `ValueError` quando o arquivo não é do formato;
- `itens(dados) -> list[dict]`: uma linha por dado com profundidade — tipo, nome, prof_topo,
  prof_base, cota, valor, unidade, texto, extra, pagina — para a tabela `dados_poco`;
- opcional `apelidos(dados) -> list[str]`: outros nomes do poço declarados no documento.

O que é lido fica em duas tabelas (migração 10): `leituras` (um documento lido, com a versão
do leitor, os dados completos em JSON e o erro, se houve) e `dados_poco` (os itens, para
consultas por poço e por tipo). Ler de novo **substitui** a leitura daquele arquivo. Um leitor
melhor (VERSAO maior) faz os documentos já lidos entrarem de novo em `pendentes`.

São dados da operadora/ANP, não do usuário: ficam fora dos pacotes de contribuição.
"""

from __future__ import annotations

import json
import os

from . import pocos as mpo
from . import pag, pressoes, pvt, rfp
from .banco import Banco, agora

LEITORES = {"cdpe": rfp, "pressoes": pressoes, "pvt": pvt, "pag": pag}

TIPOS = {
    "topo": "Topo estratigráfico", "indicio": "Indício de petróleo/gás", "testemunho": "Testemunho",
    "amostra_lateral": "Amostra lateral", "analise_perfil": "Intervalo da análise de perfis",
    "teste_formacao": "Teste de formação", "temperatura": "Temperatura", "calha": "Amostragem de calha",
    "revestimento": "Revestimento de produção", "canhoneado": "Intervalo canhoneado",
    "teste_completacao": "Teste na completação", "fase": "Fase da perfuração",
    "nao_conformidade": "Não conformidade", "perfilagem": "Perfilagem realizada",
    "pressao_formacao": "Pressão da formação (teste a cabo)", "teste_tfr": "Teste de formação (relatório)",
    "manometro": "Registro de manômetro", "pvt": "Análise PVT (liberação diferencial)",
    "composicao": "Composição do fluido (liberação flash)",
    "gas_lama": "Zona de gás na lama (PAG)", "salinidade_lama": "Salinidade da lama (PAG)",
    "litologia_calha": "Litologia da calha (PAG)", "indicio_calha": "Fluorescência na calha (PAG)",
    "topo_calha": "Topo pela calha (PAG)",
}


def prioridade(leitor: str | None, documento: str | None) -> int:
    mod = LEITORES.get(leitor or "")
    return getattr(mod, "PRIORIDADE", {}).get(documento or "", 50) + (0 if leitor == "cdpe" else 100)


def leitor_para(rel: str) -> str | None:
    """Leitor que reconhece o arquivo pelo caminho (nome e pasta)."""
    for chave, mod in LEITORES.items():
        if mod.reconhece(rel):
            return chave
    return None


def gravar(banco: Banco, rel: str, *, poco_id: str | None, leitor: str, dados: dict | None,
           erro: str | None = None, sha256: str | None = None) -> dict:
    """Grava (substituindo) a leitura de um arquivo e os itens. Devolve o resumo."""
    mod = LEITORES[leitor]
    lista = mod.itens(dados) if dados else []
    poco_doc = ((dados or {}).get("gerais") or {}).get("poco")
    confere = None
    if poco_doc and poco_id:
        confere = int(mpo.chave(poco_doc) == mpo.chave(poco_id) or mpo.resolver(banco, poco_doc) == poco_id)
    with banco.conexao() as c:
        c.execute("DELETE FROM dados_poco WHERE rel = ?", (rel,))
        c.execute("INSERT OR REPLACE INTO leituras VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (rel, poco_id, leitor, mod.VERSAO, (dados or {}).get("documento"), sha256, poco_doc, confere,
                   len(lista), json.dumps(dados, ensure_ascii=False) if dados else None, erro, agora()))
        c.executemany("INSERT INTO dados_poco VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      [(rel, poco_id, i["tipo"], k, i.get("nome"), i.get("prof_topo"), i.get("prof_base"),
                        i.get("cota"), i.get("valor"), i.get("unidade"), i.get("texto"),
                        json.dumps(i.get("extra") or {}, ensure_ascii=False), i.get("pagina"))
                       for k, i in enumerate(lista)])
        # outros nomes do poço que o documento declara (ex.: sigla antiga na base da operadora)
        if dados and poco_id and confere != 0 and hasattr(mod, "apelidos"):
            for nome in dados.get("apelidos") or mod.apelidos(dados):
                k = mpo.chave(nome)
                if not k or k == poco_id:
                    continue
                if c.execute("SELECT 1 FROM pocos WHERE id = ? AND id <> ?", (k, poco_id)).fetchone():
                    continue           # é o nome de outro poço do cadastro: não sequestrar
                c.execute("INSERT OR IGNORE INTO apelidos VALUES (?, ?, ?, '')", (k, poco_id, leitor))
    return {"rel": rel, "documento": (dados or {}).get("documento"), "n": len(lista), "erro": erro,
            "confere": confere}


def ler_arquivo(banco: Banco, pasta_projeto: str, rel: str, *, poco_id: str | None = None,
                sha256: str | None = None) -> dict | None:
    """Lê um arquivo do projeto com o leitor que o reconhece pelo nome. None = nenhum leitor."""
    leitor = leitor_para(rel)
    if leitor is None:
        return None
    caminho = os.path.join(pasta_projeto, rel)
    try:
        dados = LEITORES[leitor].ler(caminho)
    except ImportError as e:
        # falta uma biblioteca (ex.: xlrd para .xls): não grava, para ler de novo quando ela for instalada
        return {"rel": rel, "documento": None, "n": 0, "confere": None,
                "erro": f"falta a biblioteca Python {e.name or e} (o iniciar.bat instala ao abrir o SIAPP)"}
    except (ValueError, OSError) as e:
        return gravar(banco, rel, poco_id=poco_id, leitor=leitor, dados=None, erro=str(e), sha256=sha256)
    return gravar(banco, rel, poco_id=poco_id, leitor=leitor, dados=dados, sha256=sha256)


def pendentes(banco: Banco) -> list[dict]:
    """Arquivos baixados que algum leitor reconhece e que ainda não foram lidos — ou foram
    por uma versão anterior do leitor, ou mudaram (hash diferente)."""
    with banco.conexao() as c:
        lidos = {r["rel"]: dict(r) for r in c.execute("SELECT rel, leitor, versao, sha256 FROM leituras")}
        arquivos = [dict(r) for r in c.execute("SELECT rel, poco_id, sha256 FROM arquivos ORDER BY rel")]
    saida = []
    for a in arquivos:
        leitor = leitor_para(a["rel"])
        if leitor is None:
            continue
        lido = lidos.get(a["rel"])
        if (lido is None or lido["leitor"] != leitor or lido["versao"] < LEITORES[leitor].VERSAO
                or (a["sha256"] and lido["sha256"] and a["sha256"] != lido["sha256"])):
            saida.append(a)
    return saida


def ler_pendentes(banco: Banco, pasta_projeto: str, progresso=None) -> list[dict]:
    saida = []
    lista = pendentes(banco)
    for k, a in enumerate(lista, 1):
        if not os.path.isfile(os.path.join(pasta_projeto, a["rel"])):
            continue
        if progresso:
            progresso(k, len(lista), a["rel"])
        r = ler_arquivo(banco, pasta_projeto, a["rel"], poco_id=a["poco_id"], sha256=a["sha256"])
        if r:
            saida.append(r)
    return saida


def _item(r) -> dict:
    d = dict(r)
    d["extra"] = json.loads(d.get("extra") or "{}")
    return d


def _sem_repeticao(itens: list[dict]) -> list[dict]:
    """O mesmo dado em dois formulários (ex.: indício no Relatório de Descoberta e no RFP): fica o
    do documento de maior prioridade; o outro vai para `tambem_em`."""
    melhor = {}
    for i in itens:
        if i["tipo"] in ("pressao_formacao", "manometro", "perfilagem", "calha", "revestimento", "fase",
                         "nao_conformidade", "teste_completacao", "pvt", "composicao"):
            k = (i["tipo"], i["rel"], i["ordem"])          # dados que não se repetem entre documentos
        else:
            k = (i["tipo"], None if i["prof_topo"] is None else round(i["prof_topo"], 1),
                 None if i["prof_base"] is None else round(i["prof_base"], 1),
                 (i.get("nome") or "") if i["tipo"] in ("temperatura", "teste_formacao") else "")
        atual = melhor.get(k)
        if atual is None:
            melhor[k] = i
        elif i["_prio"] < atual["_prio"]:
            i.setdefault("tambem_em", []).extend([atual["documento"], *atual.get("tambem_em", [])])
            melhor[k] = i
        else:
            atual.setdefault("tambem_em", []).append(i["documento"])
    saida = list(melhor.values())
    for i in saida:
        i.pop("_prio", None)
    saida.sort(key=lambda i: (i["tipo"], i["prof_topo"] if i["prof_topo"] is not None else
                              (i["prof_base"] if i["prof_base"] is not None else 1e12), i["ordem"]))
    return saida


def _consultar(banco: Banco, poco_id: str, tipo: str | None = None, *, so_confere: bool = False) -> list[dict]:
    cond, args = "d.poco_id = ?", [poco_id]
    if tipo:
        cond += " AND d.tipo = ?"
        args.append(tipo)
    if so_confere:
        cond += " AND coalesce(l.confere, 1) = 1"
    with banco.conexao() as c:
        linhas = [_item(r) for r in c.execute(
            f"""SELECT d.*, l.documento, l.leitor FROM dados_poco d JOIN leituras l ON l.rel = d.rel
                WHERE {cond}""", args)]
    for i in linhas:
        i["_prio"] = prioridade(i.pop("leitor"), i["documento"])
    return _sem_repeticao(linhas)


def do_poco(banco: Banco, poco_id: str) -> dict:
    """Leituras do poço (com os dados completos), em ordem de prioridade, e itens agrupados por
    tipo, sem repetição."""
    with banco.conexao() as c:
        leituras = [dict(r) for r in c.execute("SELECT * FROM leituras WHERE poco_id = ?", (poco_id,))]
    for le in leituras:
        le["dados"] = json.loads(le["dados"]) if le["dados"] else None
    leituras.sort(key=lambda le: (prioridade(le["leitor"], le["documento"]), le["rel"]))
    por_tipo = {}
    for i in _consultar(banco, poco_id):
        por_tipo.setdefault(i["tipo"], []).append(i)
    return {"leituras": leituras, "itens": por_tipo}


def itens_do_poco(banco: Banco, poco_id: str, tipo: str) -> list[dict]:
    """Itens de um tipo, só dos documentos que conferem com o poço, sem repetição."""
    return _consultar(banco, poco_id, tipo, so_confere=True)


def gerais(banco: Banco, poco_id: str) -> dict:
    """Campos gerais dos formulários do poço, juntos (o RFP prevalece sobre RFCP e Perfuração)."""
    saida = {}
    leituras = [le for le in do_poco(banco, poco_id)["leituras"] if le["dados"] and le.get("confere") != 0]
    for le in leituras:                      # já em ordem de prioridade
        for k, v in (le["dados"].get("gerais") or {}).items():
            if v not in (None, "", {}) and k not in saida:
                saida[k] = v
    return saida


def resumo(banco: Banco) -> dict:
    with banco.conexao() as c:
        por_doc = {r[0] or "erro": r[1] for r in c.execute(
            "SELECT documento, count(*) FROM leituras GROUP BY documento")}
        por_tipo = {r[0]: r[1] for r in c.execute("SELECT tipo, count(*) FROM dados_poco GROUP BY tipo")}
        pocos = c.execute("SELECT count(DISTINCT poco_id) FROM leituras WHERE dados IS NOT NULL").fetchone()[0]
    return {"documentos": por_doc, "itens": por_tipo, "pocos": pocos}
