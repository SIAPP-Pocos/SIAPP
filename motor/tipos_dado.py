"""Procurar poços por tipo de dado (0.49): quais poços têm, no portal, petrofísica, PVT, geoquímica…

Usa a lista de arquivos que o **levantamento do acervo** já guardou (`acervo_arquivos`), então não baixa nada
nem pede nada ao portal. O tipo vem do nome da **pasta** do arquivo dentro do poço. O REATE escreve a mesma pasta
de vários jeitos (`PETROFISICABASICA`, `Petrofisica_basica`, `Petrofica_basica`…), por isso a comparação ignora
maiúsculas, acentos, espaços e pontuação.

O nome da pasta diz que **há** arquivos desse tipo, não que estão completos nem que o SIAPP sabe lê-los: cada tipo
informa com o que o SIAPP trabalha (`le_com`).
"""

from __future__ import annotations

import csv
import io
import os
import unicodedata
from datetime import datetime

from .banco import Banco


def _compacto(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return "".join(c for c in s.upper() if c.isalnum())


# chave, rótulo, o que é, com o que o SIAPP trabalha, padrões (sobre o nome compacto de cada pasta do caminho:
# "=X" é igual a X; sem "=" basta conter). Um arquivo pode contar em mais de um tipo.
TIPOS = [
    ("petrofisica_basica", "Petrofísica básica",
     "Porosidade, permeabilidade e densidade de plugs de testemunho; gama do testemunho (COREGAMA).",
     "Ficha do poço (leitor da 0.48)", ["PETROFISICABASICA", "PETROFICABASICA"]),
    ("petrofisica_avancada", "Petrofísica avançada",
     "Permeabilidade relativa, pressão capilar e outras análises especiais de rocha.",
     "ainda não lido pelo SIAPP", ["PETROFISICAAVANCADA", "PETROFISICAESPECIAL"]),
    ("pvt", "PVT", "Análise PVT do fluido (liberação diferencial, composição).", "Ficha do poço, Viabilidade", ["=PVT"]),
    ("geoquimica", "Geoquímica", "Geoquímica de rocha (COT, pirólise) e de fluidos (isótopos do gás).",
     "Ficha do poço", ["GEOQUIMICA"]),
    ("geomecanica", "Geomecânica", "Ensaios geomecânicos de rocha.", "ainda não lido pelo SIAPP", ["GEOMECANICA"]),
    ("petrografia", "Petrografia", "Descrição de lâminas e petrografia.", "ainda não lido pelo SIAPP", ["PETROGRAFIA"]),
    ("laminas_fotos", "Fotos e lâminas de rocha", "Fotos de testemunho, de amostras laterais e de lâminas delgadas.",
     "ainda não lido pelo SIAPP", ["FOTOS", "LAMINAS"]),
    ("amostras_laterais", "Amostras laterais", "Amostradores laterais de parede.", "ainda não lido pelo SIAPP",
     ["AMOSTRASLATERAIS", "AMOSTRADORESLATERAIS"]),
    ("outras_analises", "Outras análises de rocha e fluido", "Análises de rocha e fluido sem pasta própria.",
     "ainda não lido pelo SIAPP", ["OUTROSTIPOSDEANALISES"]),
    ("sismica_poco", "Sísmica de poço (checkshot, VSP)", "Perfis sísmicos de poço em SEG-Y.", "Ficha do poço, Perfis (TWT)",
     ["SISMICADEPOCO"]),
    ("teste_formacao_cabo", "Teste de formação a cabo", "Pressões e amostras do testador a cabo.",
     "Ficha do poço, Pressões", ["TESTEDEFORMACAOACABO"]),
    ("teste_formacao", "Teste de formação (TFR)", "Testes de formação a poço revestido ou aberto.",
     "Ficha do poço, Pressões", ["=TESTEDEFORMACAO"]),
    ("perfis_digitais", "Perfis digitais (DLIS, LIS, LAS)", "Perfis de poço em formato digital.",
     "Perfis, Interpretação", ["PERFISDIGITAIS", "PERFILCONVENCIONAL", "PERFILDIGITAL"]),
    ("perfil_processado", "Perfil digital processado", "Perfis já interpretados pela operadora.",
     "Perfis, Interpretação", ["PERFILDIGITALPROCESSADO"]),
    ("perfil_composto", "Perfil composto", "Perfil composto (PDF) com curvas, litologia e topos.", "Documentos",
     ["PERFILCOMPOSTO"]),
    ("grafico_perfil", "Gráfico de perfil", "Imagens dos perfis.", "Documentos", ["GRAFICODEPERFIL"]),
    ("perfil_perfuracao", "Perfil durante a perfuração", "LWD/MWD.", "Perfis", ["PERFILDURANTE"]),
    ("pag", "Perfil de acompanhamento geológico (PAG)", "Curvas de lama e gás e descrição de calha.",
     "Ficha do poço, Perfis", ["PERFILDEACOMPANHAMENTOGEOLOGICO"]),
    ("direcionais", "Dados direcionais", "Trajetória do poço (MD, inclinação, azimute).", "Bloco 3D",
     ["DADOSDIRECIONAIS"]),
    ("esquema_ferramentas", "Esquema de ferramentas", "Desenho das ferramentas de cada corrida de perfil.",
     "Perfis (rótulos das corridas)", ["ESQUEMADEFERRAMENTAS", "ESQUEMAFERRAMENTAS"]),
    ("agp", "AGP (dados gerais do poço)", "Topos de formação, cabeçalho de perfilagem, litologia.", "Seção, Bloco 3D",
     ["=AGP"]),
    ("pasta_poco", "Pasta de poço", "Documentos da perfuração e do poço (relatórios, formulários).",
     "Documentos, Ficha do poço", ["PASTADEPOCO", "PASTAPOCO"]),
    ("canhoneio", "Dados de canhoneio", "Intervalos canhoneados.", "ainda não lido pelo SIAPP", ["DADOSDECANHONEIO"]),
    ("arquivo_geral", "Arquivo geral de poço", "Arquivos gerais do poço.", "ainda não lido pelo SIAPP",
     ["ARQUIVOGERALDEPOCO"]),
]
_POR_CHAVE = {t[0]: t for t in TIPOS}


def tipos_da_pasta(pasta: str) -> set[str]:
    """Os tipos de dado que uma pasta (caminho relativo dentro do poço) indica."""
    segmentos = [_compacto(s) for s in str(pasta or "").replace("\\", "/").split("/") if s]
    achados = set()
    for chave, _rot, _desc, _le, padroes in TIPOS:
        for p in padroes:
            exato = p.startswith("=")
            alvo = p[1:] if exato else p
            if any((s == alvo) if exato else (alvo in s) for s in segmentos):
                achados.add(chave)
                break
    return achados


def _linhas(banco: Banco, bacia: str | None):
    cond, args = [], []
    if bacia:
        cond.append("a.bacia = ?")
        args.append(bacia)
    onde = ("WHERE " + " AND ".join(cond)) if cond else ""
    with banco.conexao() as c:
        return [dict(r) for r in c.execute(
            f"""SELECT a.bacia, a.poco_caminho, a.caminho, a.nome, a.pasta, a.tamanho,
                       p.nome_pasta, p.poco_id, p.categoria
                FROM acervo_arquivos a LEFT JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                {onde}""", args)]


def contar(banco: Banco, bacia: str | None = None) -> dict:
    """Por tipo: quantos poços e arquivos o levantamento viu. `pocos_levantados` = poços com a lista de arquivos."""
    pocos_por_tipo: dict[str, set] = {t[0]: set() for t in TIPOS}
    arquivos = {t[0]: 0 for t in TIPOS}
    tamanho = {t[0]: 0 for t in TIPOS}
    todos = set()
    for r in _linhas(banco, bacia):
        todos.add((r["bacia"], r["poco_caminho"]))
        for t in tipos_da_pasta(r["pasta"]):
            pocos_por_tipo[t].add((r["bacia"], r["poco_caminho"]))
            arquivos[t] += 1
            tamanho[t] += r["tamanho"] or 0
    tipos = [{"chave": chave, "rotulo": rot, "descricao": desc, "le_com": le, "n_pocos": len(pocos_por_tipo[chave]),
              "n_arquivos": arquivos[chave], "bytes": tamanho[chave]} for chave, rot, desc, le, _p in TIPOS]
    return {"tipos": tipos, "pocos_levantados": len(todos), "bacia": bacia or "",
            "bacias": bacias_levantadas(banco)}


def bacias_levantadas(banco: Banco) -> list[str]:
    with banco.conexao() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT bacia FROM acervo_arquivos ORDER BY bacia")]


def buscar(banco: Banco, tipos: list[str], bacia: str | None = None, modo: str = "todos") -> dict:
    """Poços que têm **todos** (ou **algum**) dos tipos pedidos, com os arquivos desses tipos (para baixar só eles)."""
    pedidos = [t for t in dict.fromkeys(tipos or []) if t in _POR_CHAVE]
    if not pedidos:
        raise ValueError("Escolha pelo menos um tipo de dado.")
    if modo not in ("todos", "algum"):
        raise ValueError("Modo de busca inválido (use 'todos' ou 'algum').")
    por: dict[tuple, dict] = {}
    for r in _linhas(banco, bacia):
        achados = tipos_da_pasta(r["pasta"]) & set(pedidos)
        if not achados:
            continue
        chave = (r["bacia"], r["poco_caminho"])
        nome = r["nome_pasta"] or r["poco_caminho"].rstrip("/").split("/")[-1]
        p = por.setdefault(chave, {"bacia": r["bacia"], "poco": nome, "poco_id": r["poco_id"] or nome,
                                   "categoria": r["categoria"], "tipos": {}, "arquivos": []})
        for t in achados:
            d = p["tipos"].setdefault(t, {"n_arquivos": 0, "bytes": 0})
            d["n_arquivos"] += 1
            d["bytes"] += r["tamanho"] or 0
        p["arquivos"].append({"caminho": r["caminho"], "nome": r["nome"], "tamanho": r["tamanho"] or 0,
                              "pasta_relativa": r["pasta"] or "", "tipos": sorted(achados)})
    pocos = [p for p in por.values() if modo == "algum" or all(t in p["tipos"] for t in pedidos)]
    pocos.sort(key=lambda p: (p["bacia"], p["poco"]))
    return {"pocos": pocos, "n_pocos": len(pocos), "n_arquivos": sum(len(p["arquivos"]) for p in pocos),
            "bytes": sum(a["tamanho"] for p in pocos for a in p["arquivos"]), "tipos": pedidos, "modo": modo,
            "bacia": bacia or "", "rotulos": {t: _POR_CHAVE[t][1] for t in pedidos}}


def csv_da_busca(resultado: dict) -> str:
    """Um arquivo por linha: poço, tipo, pasta, nome, tamanho e o caminho no portal. Separador `;` (Excel pt-BR)."""
    saida = io.StringIO()
    w = csv.writer(saida, delimiter=";", lineterminator="\n")
    w.writerow(["bacia", "poco", "categoria", "tipos_de_dado", "pasta", "arquivo", "tamanho_bytes", "caminho_no_portal"])
    for p in resultado["pocos"]:
        for a in p["arquivos"]:
            w.writerow([p["bacia"], p["poco"], p["categoria"] or "",
                        " | ".join(resultado["rotulos"][t] for t in a["tipos"]), a["pasta_relativa"], a["nome"],
                        a["tamanho"], a["caminho"]])
    return saida.getvalue()


def exportar(resultado: dict, pasta: str) -> str:
    os.makedirs(pasta, exist_ok=True)
    nome = f"busca_{'-'.join(resultado['tipos'])[:60]}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_da_busca(resultado))
    return caminho
