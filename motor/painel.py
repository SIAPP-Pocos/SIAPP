"""
Painel de preenchimento e contribuição (SIAPP 0.35).

Responde três perguntas sobre o banco do projeto — que inclui o que veio da base
comunitária e dos pacotes importados:

1. **Quanto já está preenchido?** Dos poços que têm pasta no REATE, quantos têm topos
   (do AGP ou transcritos), dados transcritos, páginas revisadas, interpretações de
   perfil… em número e em porcentagem, no total e por bacia.
2. **Quem contribuiu?** Cada autor com o que fez (dados, topos, correções do OCR,
   páginas revisadas, interpretações), em quantos poços, quando, e de onde veio
   (deste computador, de um pacote ou da base).
3. **Onde ajudar?** Poços com perfil e sem topo; poços com documentos baixados e
   nenhum dado transcrito.

Só leitura: nada aqui grava no banco.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .banco import Banco

# (chave, nome, explicação) — a ordem é a da tela
INDICADORES = (
    ("documentos", "Documentos baixados", "Algum documento do poço (pasta de poço, relatórios) baixado neste projeto."),
    ("perfil", "Perfil digital", "Critério: perfil digital baixado OU conferido no portal pelo levantamento (DLIS, LIS ou LAS "
               "pelo conteúdo). Os outros critérios estão em Configurações › Fontes e prioridade."),
    ("topos", "Topos de formação", "Topos interpretados pela operadora (AGP da ANP) ou transcritos por alguém."),
    ("topos_transcritos", "Topos transcritos", "Topos de formação transcritos à mão (por você ou pela comunidade)."),
    ("transcricoes", "Dados transcritos", "Qualquer dado transcrito com fonte: topo, revestimento, teste, fluido, trecho…"),
    ("revisadas", "Páginas revisadas", "Texto de alguma página do poço corrigido à mão."),
    ("interpretacoes", "Interpretações de perfil", "Avaliação de formação compartilhada na biblioteca."),
    ("producao", "Produção", "Produção mensal da ANP ligada ao poço."),
)
TIPOS_CONTRIB = ("fatos", "topos", "correcoes", "palavras", "paginas", "interpretacoes")
NOMES_CONTRIB = {"fatos": "Dados transcritos", "topos": "Topos", "correcoes": "Correções do OCR",
                 "palavras": "Palavras", "paginas": "Páginas revisadas", "interpretacoes": "Interpretações"}
MAX_AJUDAR = 15
MESES = 24


def _mes(iso: str | None) -> str | None:
    return iso[:7] if iso and len(iso) >= 7 and iso[4] == "-" else None


def _conjuntos(c) -> tuple[dict, dict, dict]:
    """bacia de cada poço conhecido, conjuntos de poços por indicador e números auxiliares."""
    bacia: dict[str, str] = {}
    no_portal: set = set()
    for tabela in ("acervo_pocos", "reate", "arquivos"):
        for r in c.execute(f"SELECT poco_id, bacia FROM {tabela} WHERE poco_id IS NOT NULL AND poco_id != ''"):
            bacia.setdefault(r[0], r[1] or "")
            if tabela != "arquivos":
                no_portal.add(r[0])
    q = lambda sql: {r[0] for r in c.execute(sql) if r[0]}   # noqa: E731
    s = {
        "documentos": q("SELECT DISTINCT poco_id FROM arquivos WHERE tipo = 'documento'"),
        "perfil": q("SELECT DISTINCT poco_id FROM arquivos WHERE tipo = 'perfil'")
                  | q("SELECT DISTINCT poco_id FROM acervo_pocos WHERE situacao = 'digital'"),   # 0.63: era n_perfil > 0,
                                                                                    # que contava pasta só com imagem
        "topos_agp": q("SELECT DISTINCT poco_id FROM agp_unidades WHERE topo IS NOT NULL"),
        "topos_transcritos": q("SELECT DISTINCT poco_id FROM fatos WHERE tipo = 'topo_formacao'"),
        "transcricoes": q("SELECT DISTINCT poco_id FROM fatos"),
        "revisadas": q("SELECT DISTINCT a.poco_id FROM paginas_revisadas p JOIN arquivos a ON a.rel = p.rel"),
        "interpretacoes": q("SELECT DISTINCT poco_id FROM interpretacoes"),
        "producao": q("SELECT DISTINCT poco_id FROM producao_poco"),
    }
    s["topos"] = s["topos_agp"] | s["topos_transcritos"]
    for k in list(s):
        for p in s[k]:
            bacia.setdefault(p, "")
    # bacia pelo cadastro quando o poço só aparece num indicador
    sem = [p for p, b in bacia.items() if not b]
    for i in range(0, len(sem), 500):
        lote = sem[i:i + 500]
        for r in c.execute(f"SELECT id, bacia FROM pocos WHERE id IN ({','.join('?' * len(lote))})", lote):
            if r[1]:
                bacia[r[0]] = r[1]
    aux = {"no_portal": no_portal,
           "n_docs": Counter(r[0] for r in c.execute(
               "SELECT poco_id FROM arquivos WHERE tipo = 'documento' AND poco_id IS NOT NULL")),
           "n_perfis": Counter(r[0] for r in c.execute(
               "SELECT poco_id FROM arquivos WHERE tipo = 'perfil' AND poco_id IS NOT NULL"))}
    return bacia, s, aux


def _contribuicoes(c, autor_local: str) -> list[dict]:
    """Cada contribuição como (autor, origem, tipo, poço, quando)."""
    def nome(a, origem):
        a = (a or "").strip()
        return a or (autor_local or "Você (sem nome)" if origem == "local" else "sem autor")
    saida = []
    for r in c.execute("SELECT autor, origem, tipo, poco_id, criado_em FROM fatos"):
        saida.append((nome(r[0], r[1]), r[1], "topos" if r[2] == "topo_formacao" else "fatos", r[3], r[4]))
    for r in c.execute("SELECT autor, origem, tipo, criado_em FROM vocab WHERE tipo IN ('correcao', 'palavra')"):
        saida.append((nome(r[0], r[1]), r[1], "correcoes" if r[2] == "correcao" else "palavras", None, r[3]))
    for r in c.execute("SELECT p.autor, a.poco_id, p.criado_em FROM paginas_revisadas p "
                       "LEFT JOIN arquivos a ON a.rel = p.rel"):
        saida.append((nome(r[0], "local"), "local", "paginas", r[1], r[2]))
    for r in c.execute("SELECT autor, origem, poco_id, criado_em FROM interpretacoes"):
        saida.append((nome(r[0], r[1]), r[1], "interpretacoes", r[2], r[3]))
    return saida


def indicadores(banco: Banco, autor_local: str = "", bacia: str | None = None) -> dict:
    with banco.conexao() as c:
        bacias_de, s, aux = _conjuntos(c)
        contrib = _contribuicoes(c, autor_local)
        n_cadastro = dict(c.execute("SELECT COALESCE(bacia, ''), count(*) FROM pocos GROUP BY bacia").fetchall())
    universo = set(aux["no_portal"]) or set(bacias_de)
    universo |= s["documentos"] | s["perfil"]
    if bacia:
        universo = {p for p in universo if bacias_de.get(p) == bacia}
    total = len(universo)

    def pct(n):
        return round(100 * n / total, 1) if total else None
    cards = []
    for chave, nome_, expl in INDICADORES:
        n = len(s[chave] & universo)
        cards.append({"chave": chave, "nome": nome_, "explicacao": expl, "n": n, "pct": pct(n)})

    # por bacia
    por_bacia = []
    grupos = defaultdict(set)
    for p in (set(aux["no_portal"]) or set(bacias_de)) | s["documentos"] | s["perfil"]:
        grupos[bacias_de.get(p) or "sem bacia"].add(p)
    for b, pocos in sorted(grupos.items(), key=lambda t: (-len(t[1]), t[0])):
        por_bacia.append({"bacia": b, "total": len(pocos), "cadastro": n_cadastro.get(b if b != "sem bacia" else ""),
                          **{k: len(s[k] & pocos) for k, _, _ in INDICADORES}})

    # contribuidores (só contribuições no universo filtrado, quando há poço)
    def conta(x):
        return not bacia or (x[3] is not None and bacias_de.get(x[3]) == bacia)
    autores: dict[str, dict] = {}
    for a, origem, tipo, poco, quando in filter(conta, contrib):
        d = autores.setdefault(a, {"autor": a, **{t: 0 for t in TIPOS_CONTRIB}, "pocos": set(),
                                   "origens": set(), "primeira": None, "ultima": None})
        d[tipo] += 1
        if poco:
            d["pocos"].add(poco)
        d["origens"].add(origem)
        if quando:
            d["primeira"] = min(d["primeira"] or quando, quando)
            d["ultima"] = max(d["ultima"] or quando, quando)
    lista = []
    for d in autores.values():
        d["total"] = sum(d[t] for t in TIPOS_CONTRIB)
        d["pocos"] = len(d["pocos"])
        d["origens"] = sorted(d["origens"], key=["local", "pacote", "base"].index)
        d["voce"] = bool(autor_local) and d["autor"] == autor_local or d["origens"] == ["local"]
        lista.append(d)
    lista.sort(key=lambda d: (-d["total"], d["autor"].lower()))

    # atividade por mês
    por_mes: dict[str, Counter] = defaultdict(Counter)
    for a, origem, tipo, poco, quando in filter(conta, contrib):
        m = _mes(quando)
        if m:
            por_mes[m][tipo] += 1
    meses = sorted(por_mes)[-MESES:]
    atividade = [{"mes": m, **{t: por_mes[m][t] for t in TIPOS_CONTRIB},
                  "total": sum(por_mes[m].values())} for m in meses]

    # onde ajudar
    def lista_pocos(cands, chave_n):
        ordem = sorted(cands, key=lambda p: (-aux[chave_n].get(p, 0), p))
        return [{"poco": p, "bacia": bacias_de.get(p, ""), "n": aux[chave_n].get(p, 0)} for p in ordem[:MAX_AJUDAR]]
    sem_topo = (s["perfil"] - s["topos"]) & universo
    sem_dado = (s["documentos"] - s["transcricoes"]) & universo
    ajudar = [
        {"chave": "perfil_sem_topo", "titulo": "Têm perfil e nenhum topo",
         "explicacao": "Transcrever os topos (do relatório final ou do perfil composto) libera a seção e o bloco 3D.",
         "total": len(sem_topo), "pocos": lista_pocos(sem_topo, "n_perfis"), "unidade": "perfil(s) baixado(s)"},
        {"chave": "docs_sem_dado", "titulo": "Têm documentos e nenhum dado transcrito",
         "explicacao": "Documentos já baixados esperando alguém transcrever revestimento, testes, topos…",
         "total": len(sem_dado), "pocos": lista_pocos(sem_dado, "n_docs"), "unidade": "documento(s)"},
    ]
    return {"bacia": bacia or "", "total": total, "indicadores": cards, "por_bacia": por_bacia,
            "bacias": sorted(b for b in grupos if b != "sem bacia"),
            "contribuidores": lista, "tipos": NOMES_CONTRIB, "atividade": atividade, "ajudar": ajudar,
            "global": {"correcoes": sum(1 for x in contrib if x[2] == "correcoes"),
                       "palavras": sum(1 for x in contrib if x[2] == "palavras"),
                       "autores": len(lista)},
            "levantamento": bool(aux["no_portal"])}
