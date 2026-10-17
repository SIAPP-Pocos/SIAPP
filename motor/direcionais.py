"""Dados direcionais: a trajetória do poço (pasta "Dados Direcionais" do REATE).

Arquivos de texto pequenos (~1–10 KB), em cinco leiautes conferidos em 36 arquivos da
Potiguar (17/10/2026):

- ``antigo``: "VISUALIZACAO DE DADOS DE POCOS DIRECIONAIS" da Petrobras, colunas separadas
  por " - ": prof. medida, prof. vertical, inclinação, rumo (``N58.00W``); páginas repetem
  o cabeçalho;
- ``novo``: cabeçalho chave: valor (cadastro, datum, elevação da referência…) e colunas
  prof. medida, inclinação, prof. vertical, azimute, (rumo), afastamentos N/S e E/W,
  lat/lon (GMS), UTM;
- ``tabulado`` (``_verticais.txt``, ``_dd.txt`` recentes): prof. medida, inclinação, prof.
  vertical, azimute, UTM N, UTM E, lat, lon, instrumento;
- ``coordenadas``: UTM E, UTM N, lat, lon (GMS), prof. medida, prof. vertical, inclinação,
  azimute (rumo);
- ``deviation``: "DEVIATION DATA" (relatório da empresa de perfilagem).

De todos, o SIAPP usa **prof. medida, inclinação, azimute e prof. vertical**, e calcula os
afastamentos norte e leste pelo método da **curvatura mínima** — o mesmo para todos os
leiautes, sem depender de UTM e datum de cada arquivo. A prof. vertical do arquivo, quando
há, serve de conferência (a diferença máxima fica registrada).
"""

from __future__ import annotations

import json
import math
import os
import re

import numpy as np

from .banco import Banco, agora
from .pocos import chave

VERSAO_LEITOR = 1
MAX_BYTES = 2 * 1024 * 1024
RE_PASTA = re.compile(r"direcion", re.IGNORECASE)
CODIFICACOES = ("utf-8-sig", "cp1252", "latin-1")
_RE_NUM = re.compile(r"(?<![\w:º'])-?\d+(?:[.,]\d+)?(?![\w:º'\"])")
_RE_RUMO = re.compile(r"\(?\s*([NS])\s*(\d{1,2}\s*[.,]?\s*\d*)\s*([EW])\s*\)?")
_RE_GMS = re.compile(r"-?\d{1,3}\s*[:º]\s*\d{1,2}\s*[:']\s*\d{1,2}(?:[.,]\d+)?\"?\s*[NSEW]?")


class ErroDirecional(Exception):
    pass


def eh_direcional(nome: str, pasta: str = "") -> bool:
    n = (nome or "").lower()
    return bool(RE_PASTA.search(pasta or "")) and n.endswith(".txt") and "cabecalho" not in n


def decodificar(dados: bytes) -> str:
    for cod in CODIFICACOES:
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    return dados.decode("latin-1", errors="replace")


def rumo_para_azimute(q1: str, graus: float, q2: str) -> float:
    """N58W → 302; S13.41E → 166.59; N0E → 0."""
    if q1 == "N":
        return (graus if q2 == "E" else 360 - graus) % 360
    return 180 - graus if q2 == "E" else 180 + graus


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _numeros(linha: str) -> list[float]:
    """Números da linha, sem coordenadas em GMS nem o rumo entre parênteses."""
    limpo = _RE_GMS.sub(" ", linha)
    limpo = re.sub(r"\([^)]*\)", " ", limpo)
    return [_num(m) for m in _RE_NUM.findall(limpo)]


_RE_NOME = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in (
    r"WELL NAME \(Sigla Anp\)\s*:\s*(\S.*?)\s*$", r"^\s*WN\b[^:]*:\s*(\S.*?)\s*$",
    r"Nome do po.{1,2}o\s*:\s*(\S.*?)\s*$", r"^\s*SIGLA\s*:?\s+(\S.*?)\s*$", r"^\s*WELL\s*:\s*(\S+)")]


def _cabecalho_kv(texto: str) -> dict:
    out = {}
    for rx in _RE_NOME:
        m = rx.search(texto[:3000])
        if m and re.search(r"\d", m.group(1)):
            out["poco_arquivo"] = " ".join(m.group(1).split())
            break
    for ln in texto.splitlines()[:40]:
        m = re.match(r"\s*([^:]{3,60}?)\s*:\s*(.+?)\s*$", ln)
        if not m:
            continue
        k, v = m.group(1).upper(), m.group(2)
        if "ELEV" in k and ("REF" in k or "DEPTH" in k or "REFER" in k):
            try:
                out["elevacao_ref"] = _num(re.findall(r"-?\d+(?:[.,]\d+)?", v)[0])
            except (IndexError, ValueError):
                pass
        elif re.search(r"CADASTRO|APIN", k):
            d = re.sub(r"\D", "", v)
            if len(d) >= 8:
                out["cadastro"] = d
        elif k.startswith("DATUM") or "COORDINATE SYSTEM" in k:
            out["datum"] = v.strip()
        elif "DECLINA" in k:
            out["declinacao"] = v.strip()
        elif "REFER" in k and "PROF" in k or k == "DEPTH REFERENCE":
            out["referencia"] = v.strip()
    return out


def ler(texto: str) -> dict:
    """Estações [prof. medida, inclinação, azimute, prof. vertical (do arquivo ou None)]."""
    sup = texto.upper()
    estacoes, leiaute = [], None
    if "DEVIATION DATA" in sup:
        leiaute = "deviation"
        for ln in texto.splitlines():
            n = _numeros(ln)
            if len(n) >= 12 and re.match(r"^\s*\d", ln):
                estacoes.append([n[0], n[1], n[10] % 360, abs(n[7])])
    elif "COORDENADAS" in sup and "UTM ESTE" in sup:
        leiaute = "coordenadas"
        for ln in texto.splitlines():
            n = _numeros(ln)
            if len(n) >= 6 and ln.strip().startswith("-"):
                estacoes.append([n[2], n[4], n[5] % 360, n[3]])
    else:
        for ln in texto.splitlines():
            # antigo: "-   32.0  -   31.99  -   3.25  -  N58.00W  -"
            m = re.match(r"^\s*-\s*([\d.,]+)\s*-\s*([\d.,]+)\s*-\s*([\d.,]+)\s*-\s*([NS])\s*([\d .,]+?)\s*([EW])\s*-", ln)
            if m:
                leiaute = "antigo"
                graus = _num(m.group(5).replace(" ", "") or "0")
                estacoes.append([_num(m.group(1)), _num(m.group(3)),
                                 rumo_para_azimute(m.group(4), graus, m.group(6)), _num(m.group(2))])
        if not estacoes and re.search(r"AZIMUT", sup):
            leiaute = "tabulado" if "\t" in texto else "novo"
            achou_cab = False
            for ln in texto.splitlines():
                if re.search(r"PROFUNDIDADE|Profundidade", ln) and re.search(r"(?i)inclina", ln):
                    achou_cab = True
                    continue
                if not achou_cab:
                    continue
                n = _numeros(ln)
                if len(n) >= 4 and re.match(r"^\s*\d", ln):
                    estacoes.append([n[0], n[1], n[3] % 360, n[2]])
    if not estacoes:
        raise ErroDirecional("Leiaute de dados direcionais não reconhecido.")
    # ordena, tira repetidos e valores impossíveis
    vistos, limpas = set(), []
    for md, inc, az, tvd in sorted(estacoes, key=lambda e: e[0]):
        if md in vistos or not (0 <= inc <= 180) or md < 0:
            continue
        vistos.add(md)
        limpas.append([md, inc, az, tvd])
    return {"leiaute": leiaute, **_cabecalho_kv(texto), **trajetoria(limpas)}


def trajetoria(estacoes: list[list[float]]) -> dict:
    """Curvatura mínima a partir da cabeça (md 0 = mesa rotativa).

    Saída: md, tvd (calculada), norte e leste (m) por estação, e a maior diferença entre
    a prof. vertical calculada e a do arquivo."""
    md = [0.0]
    inc = [0.0]
    az = [estacoes[0][2] if estacoes else 0.0]
    tvd_arq = [0.0]
    for e in estacoes:
        if e[0] == 0:
            inc[0], az[0] = e[1], e[2]
            continue
        md.append(e[0])
        inc.append(e[1])
        az.append(e[2])
        tvd_arq.append(e[3] if e[3] is not None else math.nan)
    n, l, t = [0.0], [0.0], [0.0]
    for k in range(1, len(md)):
        dmd = md[k] - md[k - 1]
        i1, i2 = math.radians(inc[k - 1]), math.radians(inc[k])
        a1, a2 = math.radians(az[k - 1]), math.radians(az[k])
        cos_dl = math.cos(i2 - i1) - math.sin(i1) * math.sin(i2) * (1 - math.cos(a2 - a1))
        dl = math.acos(max(-1.0, min(1.0, cos_dl)))
        rf = 1.0 if dl < 1e-9 else 2 / dl * math.tan(dl / 2)
        n.append(n[-1] + dmd / 2 * (math.sin(i1) * math.cos(a1) + math.sin(i2) * math.cos(a2)) * rf)
        l.append(l[-1] + dmd / 2 * (math.sin(i1) * math.sin(a1) + math.sin(i2) * math.sin(a2)) * rf)
        t.append(t[-1] + dmd / 2 * (math.cos(i1) + math.cos(i2)) * rf)
    dif = [abs(a - b) for a, b in zip(t, tvd_arq) if not math.isnan(b)]
    return {"md": [round(v, 2) for v in md], "tvd": [round(v, 2) for v in t],
            "norte": [round(v, 2) for v in n], "leste": [round(v, 2) for v in l],
            "inclinacao": [round(v, 2) for v in inc], "azimute": [round(v, 2) for v in az],
            "dif_tvd_max": round(max(dif), 2) if dif else None,
            "afastamento_max": round(max(math.hypot(a, b) for a, b in zip(n, l)), 2),
            "inclinacao_max": round(max(inc), 2), "md_final": round(md[-1], 2)}


def posicao(traj: dict, md) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(norte, leste, tvd) em metros na profundidade medida `md` (interpolação linear entre
    estações; abaixo da última, prolonga a última direção)."""
    md = np.atleast_1d(np.asarray(md, float))
    m = np.asarray(traj["md"], float)
    sai = []
    for chave in ("norte", "leste", "tvd"):
        v = np.asarray(traj[chave], float)
        r = np.interp(md, m, v)
        if len(m) >= 2:
            inc = (v[-1] - v[-2]) / ((m[-1] - m[-2]) or 1)
            r = np.where(md > m[-1], v[-1] + inc * (md - m[-1]), r)
        sai.append(r)
    return sai[0], sai[1], sai[2]


# =================================================================== banco
def gravar(banco: Banco, *, bacia: str, caminho: str, poco_id: str, nome: str, tamanho: int,
           arquivo_local: str = "", texto: str | None = None, erro: str = "") -> dict | None:
    dados = None
    if texto is not None and not erro:
        try:
            dados = ler(texto)
        except ErroDirecional as e:
            erro = str(e)
    if dados and dados.get("poco_arquivo") and poco_id:
        # há arquivo de outro poço na pasta (7-FP-406-RN tem o do 7-FP-46D-BA): não usa
        dados["confere"] = chave(dados["poco_arquivo"]) == chave(poco_id)
    with banco.conexao() as c:
        c.execute("""INSERT OR REPLACE INTO direcionais (bacia, caminho, poco_id, nome, tamanho, arquivo_local,
                         leitor, leiaute, dados, erro, lido_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (bacia, caminho, poco_id, nome, tamanho, arquivo_local, VERSAO_LEITOR,
                   (dados or {}).get("leiaute"), json.dumps(dados) if dados else None, erro or None, agora()))
    return dados


def do_poco(banco: Banco, poco_id: str) -> dict | None:
    """A trajetória do poço (a do arquivo mais completo), ou None."""
    with banco.conexao() as c:
        linhas = [dict(r) for r in c.execute(
            "SELECT * FROM direcionais WHERE poco_id = ? AND dados IS NOT NULL", (poco_id,))]
    pares = [(json.loads(r["dados"]), r) for r in linhas]
    pares = [(d, r) for d, r in pares if d.get("confere") is not False]
    if not pares:
        return None
    melhores = sorted(pares,
                      key=lambda t: (len(t[0]["md"]), t[0]["md_final"]), reverse=True)
    d, r = melhores[0]
    return {**d, "arquivo": r["caminho"], "arquivo_local": r["arquivo_local"]}


def pendentes(banco: Banco, bacia: str, categorias: list[str] | None = None,
              pocos: list[str] | None = None) -> list[dict]:
    cond, args = ["a.bacia = ?"], [bacia]
    if categorias:
        cond.append(f"p.categoria IN ({','.join('?' * len(categorias))})")
        args += list(categorias)
    if pocos is not None:
        if not pocos:
            return []
        cond.append(f"p.poco_id IN ({','.join('?' * len(pocos))})")
        args += list(pocos)
    with banco.conexao() as c:
        linhas = [dict(r) for r in c.execute(
            f"""SELECT a.caminho, a.nome, a.pasta, a.tamanho, p.poco_id, d.arquivo_local AS local_antigo,
                       d.tamanho AS tamanho_antigo
                FROM acervo_arquivos a JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                LEFT JOIN direcionais d ON d.bacia = a.bacia AND d.caminho = a.caminho
                WHERE {' AND '.join(cond)}
                  AND (d.caminho IS NULL OR d.tamanho IS NOT a.tamanho OR coalesce(d.leitor, 0) < ?)
                ORDER BY a.caminho""", (*args, VERSAO_LEITOR))]
    return [r for r in linhas if eh_direcional(r["nome"], r["pasta"])]


def caminho_local(pasta_projeto: str, bacia: str, nome: str) -> str:
    return os.path.join(pasta_projeto, "direcionais", re.sub(r"[^\w .-]+", "_", bacia), os.path.basename(nome))


def ler_do_portal(banco: Banco, cliente, bacia: str, itens: list[dict], *, pasta_projeto: str,
                  progresso=None, cancelar=None) -> int:
    """Baixa (ou reaproveita a cópia local) e lê cada arquivo de `itens` (de `pendentes`)."""
    feitos = 0
    for k, it in enumerate(itens, 1):
        if cancelar is not None and cancelar.is_set():
            break
        if progresso:
            progresso(k, len(itens), it["nome"])
        destino = caminho_local(pasta_projeto, bacia, it["nome"])
        local = os.path.relpath(destino, pasta_projeto).replace(os.sep, "/")
        texto, erro = None, ""
        try:
            if (it["tamanho"] or 0) > MAX_BYTES:
                raise ErroDirecional("Arquivo grande demais para dados direcionais.")
            if os.path.isfile(destino) and os.path.getsize(destino) == it["tamanho"]:
                with open(destino, "rb") as f:
                    bruto = f.read()
            else:
                bruto = cliente.ler_inicio(it["caminho"], max(1, it["tamanho"] or MAX_BYTES))
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with open(destino, "wb") as f:
                    f.write(bruto)
            texto = decodificar(bruto)
        except ErroDirecional as e:
            erro = str(e)
        except Exception as e:  # noqa: BLE001 — erro do portal não para a fila
            erro = f"{type(e).__name__}: {e}"
        gravar(banco, bacia=bacia, caminho=it["caminho"], poco_id=it["poco_id"] or "", nome=it["nome"],
               tamanho=it["tamanho"] or 0, arquivo_local=local if os.path.isfile(destino) else "",
               texto=texto, erro=erro)
        feitos += 1
    return feitos


def resumo(banco: Banco, bacia: str) -> dict:
    with banco.conexao() as c:
        disp = sum(eh_direcional(n, p) for n, p in c.execute(
            "SELECT nome, pasta FROM acervo_arquivos WHERE bacia = ?", (bacia,)))
        lidos, ok = c.execute("SELECT count(*), sum(dados IS NOT NULL) FROM direcionais WHERE bacia = ?",
                              (bacia,)).fetchone()
    return {"direcionais_disponiveis": disp, "direcionais_lidos": lidos or 0, "direcionais_com_trajetoria": ok or 0}
