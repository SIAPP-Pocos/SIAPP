"""Dados consolidados: tudo o que o SIAPP leu, de onde veio, onde fica e onde é usado.

Depois do bloco 9, o mesmo tipo de dado chega por vários caminhos: um topo de formação pode vir do AGP, do
RFP, da descrição de calha do PAG ou da transcrição do usuário; uma temperatura, do AGP, do RFP, do teste a cabo ou
do TFR. Este módulo junta, por **tema**, as fontes de cada dado, a tabela do banco onde cada uma fica e os módulos
que as usam — para o projeto (quantos poços têm cada fonte) e para um poço (os valores de cada fonte lado a lado).

É só leitura: nada aqui decide qual fonte vale. A regra de cada módulo está no texto de "usos" (ex.: a seção
estratigráfica e o bloco 3D usam só os topos do AGP).
"""

from __future__ import annotations

import json

from .banco import Banco


def _f(rotulo, onde, tipo, *args):
    return {"rotulo": rotulo, "onde": onde, "tipo": tipo, "args": args}


TEMAS = [
    {"chave": "topos", "nome": "Topos de formação",
     "fontes": [_f("AGP da ANP", "agp_unidades", "agp_unid"),
                _f("RFP (topos constatados)", "dados_poco · topo", "dp", "topo"),
                _f("Descrição de calha (PAG)", "dados_poco · topo_calha", "dp", "topo_calha"),
                _f("Transcritos (você e a comunidade)", "fatos · topo_formacao", "fato", "topo_formacao")],
     "usos": ["Seção estratigráfica e bloco 3D: o topo efetivo de cada unidade — o que você escolheu na ficha do "
              "poço ou o da primeira fonte da ordem do projeto (padrão: AGP → transcrito → RFP → calha)",
              "Perfis: AGP (verde tracejado), RFP (marrom pontilhado), transcritos (roxo)",
              "Ficha do poço: todos; os topos sem nome do RFP ganham o nome da calha a até 10 m",
              "Avaliação: as unidades do AGP como intervalos candidatos"]},
    {"chave": "intervalos", "nome": "Intervalos de interesse",
     "fontes": [_f("Intervalos-alvo marcados", "fatos · intervalo_alvo", "fato", "intervalo_alvo"),
                _f("Zonas-reservatório do AGP", "agp · dados.zonas", "agp_json", "zonas"),
                _f("Análise de perfis (RFP)", "dados_poco · analise_perfil", "dp", "analise_perfil"),
                _f("Canhoneados (RFCP)", "dados_poco · canhoneado", "dp", "canhoneado"),
                _f("Teste de formação (TFR)", "dados_poco · teste_tfr", "dp", "teste_tfr"),
                _f("Gás na lama (PAG)", "dados_poco · gas_lama", "dp", "gas_lama"),
                _f("Indícios (RFP)", "dados_poco · indicio", "dp", "indicio")],
     "usos": ["Avaliação de formação: candidatos (marcados, AGP, formulários, TFR, gás na lama)",
              "Perfis: canhoneados na borda direita; intervalos-alvo em amarelo",
              "Ficha do poço: todos, com os indícios"]},
    {"chave": "temperatura", "nome": "Temperatura",
     "fontes": [_f("AGP — corridas de perfilagem (BHT)", "agp · dados.corridas", "agp_json", "corridas"),
                _f("AGP — temperatura extrapolada e gradiente", "agp · dados.temperaturas", "agp_json", "temperaturas"),
                _f("RFP, teste a cabo e TFR", "dados_poco · temperatura", "dp", "temperatura")],
     "usos": ["Avaliação: nota de referência para o Rw (o SIAPP não converte sozinho)",
              "Ficha do poço"]},
    {"chave": "pressao", "nome": "Pressão",
     "fontes": [_f("Teste a cabo (estações do DLIS)", "dados_poco · pressao_formacao", "dp", "pressao_formacao"),
                _f("Testes do RFP", "dados_poco · teste_formacao", "dp", "teste_formacao"),
                _f("Relatório do TFR", "dados_poco · teste_tfr", "dp", "teste_tfr"),
                _f("Manômetros do TFR", "dados_poco · manometro", "dp", "manometro")],
     "usos": ["Ficha › Pressões × profundidade: gradiente por grupo, fluido compatível e contato",
              "Ficha › relatório do TFR (k, skin, IP, estática)"]},
    {"chave": "fluidos", "nome": "Fluidos (PVT, °API, gás)",
     "fontes": [_f("Análise PVT (liberação diferencial)", "dados_poco · pvt", "dp", "pvt"),
                _f("Composição (liberação flash)", "dados_poco · composicao", "dp", "composicao"),
                _f("Transcritos", "fatos · propriedade_fluido", "fato", "propriedade_fluido"),
                _f("Isótopos do gás", "dados_poco · isotopo_gas", "dp", "isotopo_gas")],
     "usos": ["Viabilidade: °API, densidade do gás, Bo, Rs e Bg do PVT antes das correlações; depois o transcrito "
              "e a leitura automática dos documentos",
              "Ficha do poço: PVT, composição, geoquímica"]},
    {"chave": "lama", "nome": "Lama e filtrado",
     "fontes": [_f("AGP — Rm, Rmf, Rmc por corrida", "agp · dados.corridas", "agp_json", "corridas"),
                _f("Perfuração — fluido e peso por fase", "dados_poco · fase", "dp", "fase"),
                _f("PAG — salinidade", "dados_poco · salinidade_lama", "dp", "salinidade_lama")],
     "usos": ["Avaliação: nota de referência para o Rw e o Rmf", "Ficha do poço"]},
    {"chave": "litologia", "nome": "Litologia",
     "fontes": [_f("AGP — litologia das amostras", "agp · dados.litologia", "agp_json", "litologia"),
                _f("Descrição de calha (PAG)", "dados_poco · litologia_calha", "dp", "litologia_calha"),
                _f("Fluorescência e corte (PAG)", "dados_poco · indicio_calha", "dp", "indicio_calha")],
     "usos": ["Perfis: trilha de litologia (a do AGP; sem ela, a da calha)", "Ficha do poço"]},
    {"chave": "perfis", "nome": "Curvas de perfil",
     "fontes": [_f("Perfis abertos (DLIS, LIS, LAS)", "perfis, curvas", "curvas", None),
                _f("Interpretação da operadora (Vsh, φ, Sw, k)", "curvas · família VSH/PHIE/PHIT/SW/PERM", "curvas",
                   ("VSH", "PHIE", "PHIT", "SW", "PERM"))],
     "usos": ["Perfis e avaliação de formação", "Avaliação × operadora (com o perfil processado aberto)",
              "Levantamento e mapa: quais poços têm cada curva no portal, sem baixar"]},
    {"chave": "avaliacoes", "nome": "Interpretações de perfil",
     "fontes": [_f("Biblioteca de interpretações", "interpretacoes", "tabela", "interpretacoes", "poco_id")],
     "usos": ["Comunidade › Biblioteca: comparar e refazer; pacotes de contribuição"]},
    {"chave": "tempo", "nome": "Tempo × profundidade",
     "fontes": [_f("Checkshot (SEG-Y da sísmica de poço)", "dados_poco · checkshot", "dp", "checkshot")],
     "usos": ["Ficha: tabela, gráficos e CSV para a sísmica", "Perfis: TWT na leitura do mouse"]},
    {"chave": "trajetoria", "nome": "Trajetória do poço",
     "fontes": [_f("Dados direcionais", "direcionais", "tabela", "direcionais", "poco_id")],
     "usos": ["Bloco 3D: poços desviados na posição real"]},
    {"chave": "producao", "nome": "Produção",
     "fontes": [_f("Produção da ANP por poço", "producao_poco", "tabela", "producao_poco", "poco_id")],
     "usos": ["Ficha do poço", "Viabilidade: depleção do campo"]},
    {"chave": "nomes", "nome": "Outros nomes do poço",
     "fontes": [_f("Apelidos (cadastro, formulários, PVT, TFR, SEG-Y, geoquímica)", "apelidos", "tabela", "apelidos",
                   "poco_id")],
     "usos": ["Busca do poço por qualquer grafia (mapa, destaque, ficha, pastas do portal)"]},
]


# ---------------------------------------------------------------- contagens do projeto
def _contar(c, f: dict) -> tuple[int, int]:
    t, a = f["tipo"], f["args"]
    if t == "dp":
        r = c.execute("""SELECT count(DISTINCT d.poco_id), count(*) FROM dados_poco d JOIN leituras l ON l.rel = d.rel
                         WHERE d.tipo = ? AND coalesce(l.confere, 1) = 1""", (a[0],)).fetchone()
    elif t == "fato":
        r = c.execute("SELECT count(DISTINCT poco_id), count(*) FROM fatos WHERE tipo = ?", (a[0],)).fetchone()
    elif t == "agp_unid":
        r = c.execute("SELECT count(DISTINCT poco_id), count(*) FROM agp_unidades WHERE topo IS NOT NULL").fetchone()
    elif t == "agp_json":
        r = c.execute(f"""SELECT count(DISTINCT poco_id), coalesce(sum(json_array_length(dados, '$.{a[0]}')), 0)
                          FROM agp WHERE dados IS NOT NULL AND json_valid(dados)
                          AND json_array_length(dados, '$.{a[0]}') > 0""").fetchone()
    elif t == "curvas":
        if a[0] is None:
            r = c.execute("SELECT count(DISTINCT pf.poco_id), count(*) FROM curvas cv JOIN perfis pf ON pf.rel = cv.rel"
                          ).fetchone()
        else:
            ph = ",".join("?" * len(a[0]))
            r = c.execute(f"""SELECT count(DISTINCT pf.poco_id), count(*) FROM curvas cv JOIN perfis pf ON pf.rel = cv.rel
                              WHERE cv.familia IN ({ph})""", a[0]).fetchone()
    elif t == "tabela":
        r = c.execute(f"SELECT count(DISTINCT {a[1]}), count(*) FROM {a[0]}").fetchone()
    else:
        r = (0, 0)
    return int(r[0] or 0), int(r[1] or 0)


def projeto(banco: Banco) -> dict:
    temas = []
    with banco.conexao() as c:
        for tm in TEMAS:
            fontes = []
            for f in tm["fontes"]:
                try:
                    n_pocos, n = _contar(c, f)
                except Exception:  # noqa: BLE001 — tabela de um módulo ainda vazia ou sem JSON1: zero
                    n_pocos, n = 0, 0
                fontes.append({"rotulo": f["rotulo"], "onde": f["onde"], "pocos": n_pocos, "registros": n})
            temas.append({"chave": tm["chave"], "nome": tm["nome"], "fontes": fontes, "usos": tm["usos"]})
        leituras = [dict(r) for r in c.execute(
            """SELECT leitor, documento, count(*) AS n, sum(erro IS NOT NULL) AS erros, sum(confere = 0) AS de_outro_poco
               FROM leituras GROUP BY leitor, documento ORDER BY leitor, documento""")]
    return {"temas": temas, "leituras": leituras}


# ---------------------------------------------------------------- valores de um poço
LIMITE = 300


def _linhas(c, f: dict, pid: str) -> list[dict]:
    t, a = f["tipo"], f["args"]
    if t == "dp":
        rs = c.execute("""SELECT d.*, l.documento FROM dados_poco d JOIN leituras l ON l.rel = d.rel
                          WHERE d.poco_id = ? AND d.tipo = ? AND coalesce(l.confere, 1) = 1
                          ORDER BY coalesce(d.prof_topo, d.prof_base), d.ordem LIMIT ?""", (pid, a[0], LIMITE))
        saida = []
        for r in rs:
            extra = json.loads(r["extra"] or "{}")
            valor = None if r["valor"] is None else f"{_fmt(r['valor'])} {r['unidade'] or ''}".strip()
            saida.append({"topo": r["prof_topo"], "base": r["prof_base"], "nome": r["nome"] or "",
                          "valor": valor or "", "detalhe": r["texto"] or _resumo_extra(extra), "fonte": r["rel"]})
        return saida
    if t == "fato":
        return [{"topo": r["prof_topo"], "base": r["prof_base"], "nome": r["nome"] or "",
                 "valor": f"{r['valor'] or ''} {r['unidade'] or ''}".strip(),
                 "detalhe": f"{r['origem']}" + (f" · {r['autor']}" if r["autor"] else ""), "fonte": r["fonte_rel"] or ""}
                for r in c.execute("SELECT * FROM fatos WHERE poco_id = ? AND tipo = ? ORDER BY prof_topo LIMIT ?",
                                   (pid, a[0], LIMITE))]
    if t == "agp_unid":
        return [{"topo": r["topo"], "base": r["base"], "nome": r["nome"] or r["sigla"] or "", "valor": "",
                 "detalhe": " · ".join(x for x in (r["fonte"], r["metodo"]) if x), "fonte": r["caminho"]}
                for r in c.execute("""SELECT * FROM agp_unidades WHERE poco_id = ? AND topo IS NOT NULL AND tip = 'L'
                                      ORDER BY topo LIMIT ?""", (pid, LIMITE))]
    if t == "agp_json":
        saida = []
        for r in c.execute("SELECT caminho, dados FROM agp WHERE poco_id = ? AND dados IS NOT NULL", (pid,)):
            for x in (json.loads(r["dados"]).get(a[0]) or [])[:LIMITE]:
                saida.append({**_agp_item(a[0], x), "fonte": r["caminho"]})
        return saida
    if t == "curvas":
        cond, args = "pf.poco_id = ?", [pid]
        if a[0] is not None:
            cond += f" AND cv.familia IN ({','.join('?' * len(a[0]))})"
            args += list(a[0])
        # uma linha por família: quantas curvas, de quantos arquivos, e o intervalo
        return [{"topo": r["topo"], "base": r["base"], "nome": r["familia"] or "sem família",
                 "valor": f"{r['n']} curva(s) em {r['arqs']} arquivo(s)", "detalhe": r["mnems"] or "", "fonte": ""}
                for r in c.execute(f"""SELECT cv.familia, count(*) AS n, count(DISTINCT cv.rel) AS arqs,
                                              min(cv.topo_m) AS topo, max(cv.base_m) AS base,
                                              group_concat(DISTINCT cv.mnemonico) AS mnems
                                       FROM curvas cv JOIN perfis pf ON pf.rel = cv.rel WHERE {cond}
                                       GROUP BY cv.familia ORDER BY cv.familia IS NULL, cv.familia LIMIT ?""",
                                    (*args, LIMITE))]
    if t == "tabela":
        tab = a[0]
        if tab == "apelidos":
            return [{"topo": None, "base": None, "nome": r["chave"], "valor": "", "detalhe": r["origem"], "fonte": ""}
                    for r in c.execute("SELECT * FROM apelidos WHERE poco_id = ?", (pid,))]
        if tab == "producao_poco":
            r = c.execute("""SELECT count(*) AS n, min(periodo) AS de, max(periodo) AS ate, sum(oleo_m3) AS oleo,
                             sum(coalesce(gas_assoc_mil_m3, 0) + coalesce(gas_nassoc_mil_m3, 0)) AS gas, sum(agua_m3) AS agua
                             FROM producao_poco WHERE poco_id = ?""", (pid,)).fetchone()
            if not r["n"]:
                return []
            return [{"topo": None, "base": None, "nome": f"{r['de']} a {r['ate']} ({r['n']} meses)",
                     "valor": f"óleo {_fmt(r['oleo'] or 0)} m³", "detalhe": f"gás {_fmt(r['gas'] or 0)} mil m³ · "
                     f"água {_fmt(r['agua'] or 0)} m³", "fonte": ""}]
        if tab == "direcionais":
            return [{"topo": None, "base": None, "nome": r["nome"] or "", "valor": r["leiaute"] or "",
                     "detalhe": r["erro"] or "", "fonte": r["caminho"]}
                    for r in c.execute("SELECT * FROM direcionais WHERE poco_id = ?", (pid,))]
        if tab == "interpretacoes":
            return [{"topo": None, "base": None, "nome": r["titulo"] or r["id"][:8], "valor": r["origem"],
                     "detalhe": r["autor"] or "", "fonte": r["arquivo_nome"] or ""}
                    for r in c.execute("SELECT * FROM interpretacoes WHERE poco_id = ? ORDER BY criado_em DESC", (pid,))]
    return []


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and abs(v) >= 1000:
        return f"{v:,.0f}".replace(",", ".")
    if isinstance(v, float):
        return f"{v:.4g}".replace(".", ",")
    return str(v)


ROTULOS_EXTRA = {"prev_medida": "prevista", "prev_cota": "cota prevista", "api": "°API", "vazao_m3_dia": "vazão m³/d",
                 "prof_registrador": "registrador a", "vezes_fundo": "× o fundo", "rw75": "Rw (NaCl, 75 °F)",
                 "tvdsd": "TVD abaixo do datum", "vint_m_s": "Vint", "vmed_m_s": "Vméd", "C1": "δ¹³C₁", "C2": "δ¹³C₂",
                 "C3": "δ¹³C₃", "permeabilidade_md": "k (mD)", "skin": "skin", "ip": "IP"}


def _resumo_extra(x: dict) -> str:
    partes = [f"{ROTULOS_EXTRA.get(k, k.replace('_', ' '))} {_fmt(v)}" for k, v in x.items()
              if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "ordem"]
    return " · ".join(partes[:5])


def _agp_item(chave: str, x: dict) -> dict:
    if chave == "corridas":
        val = " · ".join(f"{k.upper()} {_fmt(x[k])}" for k in ("rm", "rmf", "rmc") if x.get(k) is not None)
        return {"topo": None, "base": x.get("prof_alcancada"), "nome": f"corrida {x.get('corrida') or '?'}",
                "valor": val, "detalhe": f"BHT {_fmt(x['bht'])} °F" if x.get("bht") is not None else ""}
    if chave == "temperaturas":
        if x.get("gradiente_f_m") is not None:
            return {"topo": None, "base": None, "nome": f"corrida {x.get('corrida') or '?'}",
                    "valor": f"gradiente {_fmt(x['gradiente_f_m'])} °F/m", "detalhe": ""}
        return {"topo": x.get("prof"), "base": None, "nome": f"corrida {x.get('corrida') or '?'}",
                "valor": f"{_fmt(x.get('temperatura_f'))} °F", "detalhe": "extrapolada"}
    if chave == "litologia":
        return {"topo": x.get("topo"), "base": x.get("base"), "nome": x.get("rocha") or "", "valor": "",
                "detalhe": x.get("descricao") or ""}
    if chave == "zonas":
        return {"topo": x.get("topo"), "base": x.get("base"), "nome": f"zona {x.get('codigo') or ''}".strip(),
                "valor": "", "detalhe": ""}
    return {"topo": x.get("topo"), "base": x.get("base"), "nome": str(x.get("nome") or x.get("numero") or ""),
            "valor": "", "detalhe": str(x.get("resultado") or "")}


def poco(banco: Banco, pid: str) -> dict:
    temas = []
    with banco.conexao() as c:
        for tm in TEMAS:
            fontes = []
            for f in tm["fontes"]:
                try:
                    linhas = _linhas(c, f, pid)
                except Exception:  # noqa: BLE001
                    linhas = []
                fontes.append({"rotulo": f["rotulo"], "onde": f["onde"], "linhas": linhas, "n": len(linhas)})
            temas.append({"chave": tm["chave"], "nome": tm["nome"], "fontes": fontes, "usos": tm["usos"],
                          "com_dado": sum(1 for f in fontes if f["n"])})
    return {"poco": pid, "temas": temas}
