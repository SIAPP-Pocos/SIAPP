"""Correção de custos pela inflação (0.52): fatores acumulados do IPCA e do INCC-M, a partir das séries oficiais.

As séries vêm do **Banco Central (SGS)**, que republica a variação mensal do IPCA (IBGE) e do INCC-M (FGV):

- IPCA: série 433;
- INCC-M: série 192.

Nada é digitado no código: a série é baixada quando você pede a correção, fica guardada no projeto
(`ambiente_teste/indices/`, com a data do download) e o fator vem da conta mês a mês, que entra na memória de cálculo.

Convenção: um custo de "data-base jun/2024" está nos preços de junho de 2024; para levá-lo a um mês Z multiplica-se
(1 + variação mensal) de julho/2024 até Z, inclusive.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

SERIES = {
    "ipca": {"codigo": 433, "rotulo": "IPCA (variação mensal; IBGE, via Banco Central/SGS série 433)"},
    "incc": {"codigo": 192, "rotulo": "INCC-M (variação mensal; FGV, via Banco Central/SGS série 192)"},
}
URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10,
         "nov": 11, "dez": 12}
PASTA = "indices"


class ErroIndices(ValueError):
    pass


def ler_mes(texto: str) -> tuple[tuple[int, int], bool]:
    """("jun/2024" | "2024-06" | "06/2024" | "2022") → ((ano, mês), aproximado). Só o ano: assume junho (aproximado)."""
    t = str(texto or "").strip().lower()
    m = re.fullmatch(r"([a-zç]{3})[a-z]*[/\- ]+(\d{4})", t)
    if m and m.group(1) in MESES:
        return (int(m.group(2)), MESES[m.group(1)]), False
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})", t) or None
    if m and 1 <= int(m.group(2)) <= 12:
        return (int(m.group(1)), int(m.group(2))), False
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return (int(m.group(2)), int(m.group(1))), False
    if re.fullmatch(r"\d{4}", t):
        return (int(t), 6), True
    raise ErroIndices(f"Não entendi o mês «{texto}». Use, por exemplo, jun/2024 ou 2024-06.")


def _rotulo_mes(ym: tuple[int, int]) -> str:
    return f"{ym[0]:04d}-{ym[1]:02d}"


def baixar_serie(indice: str, sessao=None, timeout: float = 60) -> list[list]:
    """[[ano, mês, variação %], …] da série oficial. Levanta ErroIndices se o Banco Central não responder."""
    if indice not in SERIES:
        raise ErroIndices(f"Índice desconhecido: {indice} (use ipca ou incc).")
    import requests
    sessao = sessao or requests.Session()
    url = URL.format(codigo=SERIES[indice]["codigo"])
    try:
        r = sessao.get(url, params={"formato": "json", "dataInicial": "01/01/2015"}, timeout=timeout)
    except Exception as e:  # noqa: BLE001 — sem internet, tempo esgotado…
        raise ErroIndices(f"Não consegui falar com o Banco Central ({type(e).__name__}).") from e
    if r.status_code != 200:
        raise ErroIndices(f"O Banco Central respondeu HTTP {r.status_code} para a série {SERIES[indice]['codigo']}.")
    try:
        dados = r.json()
        serie = []
        for d in dados:
            dia, mes, ano = d["data"].split("/")
            serie.append([int(ano), int(mes), float(str(d["valor"]).replace(",", "."))])
    except (ValueError, KeyError, TypeError) as e:
        raise ErroIndices("A resposta do Banco Central não está no formato esperado.") from e
    if not serie:
        raise ErroIndices("O Banco Central devolveu a série vazia.")
    return sorted(serie)


def _caminho(pasta_projeto: str, indice: str) -> str:
    return os.path.join(pasta_projeto, PASTA, f"{indice}.json")


def serie_guardada(pasta_projeto: str, indice: str) -> dict | None:
    try:
        with open(_caminho(pasta_projeto, indice), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def obter_serie(pasta_projeto: str, indice: str, sessao=None, atualizar: bool = False) -> dict:
    """A série guardada; baixa se não há (ou se `atualizar`). Sem internet e com cópia guardada, usa a cópia."""
    guardada = serie_guardada(pasta_projeto, indice)
    if guardada and not atualizar:
        return guardada
    try:
        serie = baixar_serie(indice, sessao)
    except ErroIndices:
        if guardada:
            return {**guardada, "aviso": "sem conexão com o Banco Central: usada a cópia guardada em "
                                         f"{guardada['baixado_em'][:10]}"}
        raise
    reg = {"indice": indice, "rotulo": SERIES[indice]["rotulo"], "baixado_em": datetime.now().isoformat(timespec="seconds"),
           "fonte": URL.format(codigo=SERIES[indice]["codigo"]), "serie": serie}
    os.makedirs(os.path.join(pasta_projeto, PASTA), exist_ok=True)
    with open(_caminho(pasta_projeto, indice), "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False)
    return reg


def fator_acumulado(serie: list[list], de: tuple[int, int], ate: tuple[int, int]) -> tuple[float, int]:
    """Produto de (1 + variação/100) dos meses depois de `de` até `ate`, inclusive. Devolve (fator, nº de meses).
    Falta de algum mês no intervalo é erro (nunca se completa a série por conta própria)."""
    if ate < de:
        raise ErroIndices(f"A data de referência ({_rotulo_mes(ate)}) é anterior à data-base ({_rotulo_mes(de)}).")
    por_mes = {(a, m): v for a, m, v in serie}
    ano, mes = de
    f, n, faltam = 1.0, 0, []
    while (ano, mes) < ate:
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
        if (ano, mes) not in por_mes:
            faltam.append(_rotulo_mes((ano, mes)))
            continue
        f *= 1.0 + por_mes[(ano, mes)] / 100.0
        n += 1
    if faltam:
        raise ErroIndices("A série não tem " + ", ".join(faltam[:6]) + (" …" if len(faltam) > 6 else "") +
                          ": escolha uma data de referência mais antiga ou atualize a série.")
    return f, n


def corrigir(pasta_projeto: str, indice: str, data_base: str, data_ref: str | None = None, sessao=None,
             atualizar: bool = False) -> dict:
    """Fator de correção da `data_base` até `data_ref` (padrão: o último mês da série), com a origem para a memória."""
    if not data_base:
        raise ErroIndices("Informe a data-base do custo (ex.: jun/2024) para corrigir pela inflação.")
    de, aprox = ler_mes(data_base)
    reg = obter_serie(pasta_projeto, indice, sessao, atualizar)
    ultimo = (reg["serie"][-1][0], reg["serie"][-1][1])
    ate = ler_mes(data_ref)[0] if data_ref else ultimo
    f, n = fator_acumulado(reg["serie"], de, ate)
    avisos = []
    if aprox:
        avisos.append(f"A data-base «{data_base}» traz só o ano: assumido junho de {de[0]}. Informe o mês para mais precisão.")
    if reg.get("aviso"):
        avisos.append(reg["aviso"])
    return {"indice": indice, "rotulo": reg["rotulo"], "fator": f, "meses": n, "de": _rotulo_mes(de),
            "ate": _rotulo_mes(ate), "ultimo_mes_da_serie": _rotulo_mes(ultimo), "baixado_em": reg["baixado_em"],
            "fonte": reg["fonte"], "avisos": avisos}
