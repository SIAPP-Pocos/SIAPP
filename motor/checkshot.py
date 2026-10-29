"""Sísmica de poço — checkshot e VSP em SEG-Y (bloco 9, item 6): a relação tempo × profundidade.

Pasta "Sismica de Poco" do REATE: `<poço>_asr-3_stack.sgy` (um traço por componente em cada nível, já
empilhado), `<poço>_asr-3_raw.sgy` (cada tiro) e o relatório de campo em PDF. O que interessa ao SIAPP não está
nas amostras (o sinal), e sim no **cabeçalho de cada traço**: profundidade do receptor, posição da fonte e o
tempo da primeira chegada (pick). Com eles sai a tabela tempo × profundidade — a ponte entre o poço (metros)
e a sísmica de superfície (milissegundos).

O SEG-Y de sísmica de poço guarda esses campos em posições que **não são as do padrão**: o cabeçalho textual
diz onde estão (Halliburton, conferido no 1-BRSA-1304-BA, 29/10/2026)::

    C35 SeismicDatumElev@57,Microseconds@205
    C36 Receiver:MD@173,TVD@181,RefElev@185,RCX@81,RCY@85
    C37 Source:SCX@73,SCY@77,SD@193,RefElev@189,S2Monitor@197
    C38 Times(us):pick@209,ref@213,DatumCorr@225,ExtDelay@221,1stSamp@217

Cada campo é um inteiro de 4 bytes (big-endian); profundidades e elevações com o escalar de elevação
(bytes 69–70), coordenadas com o de coordenadas (71–72), tempos em microssegundos. Sem esse mapa no cabeçalho, o
arquivo é recusado (não dá para adivinhar onde está o tempo).

Cálculo de cada nível (o mesmo do relatório "FULL PROFILE DATA" da Halliburton):

- elevação da fonte = elevação de referência da fonte − profundidade da fonte (SD);
- dz = distância vertical fonte → receptor = TVD − (elevação da mesa − elevação da fonte);
- SGO = afastamento horizontal fonte → receptor;
- Tt = pick + atraso externo; **Tv = Tt × dz / √(dz² + SGO²)** (raio reto: tempo vertical);
- Ts = correção estática da fonte ao datum sísmico (campo DatumCorr; sem ele, 0);
- **Tcorr = Tv + Ts** (tempo vertical simples, do datum ao receptor); **TWT = 2 × Tcorr**;
- TVDSD = TVD abaixo do datum sísmico; Vméd = TVDSD / Tcorr; Vint entre níveis vizinhos.

No 1-BRSA-1304-BA (23 níveis, 90,6 a 1.944 m), a tabela confere com a do relatório: a 1.944 m, Tcorr 0,6385 s,
Vméd 3.032 m/s, Vint 4.264 m/s, TWT 1,277 s.

O arquivo "raw" (tiro a tiro) é registrado, mas a tabela vem do "stack": os picks do bruto não têm as mesmas
correções.
"""

from __future__ import annotations

import math
import os
import re
import struct
import unicodedata

VERSAO = 1
NOME = "Sísmica de poço (checkshot/VSP em SEG-Y)"
DOCUMENTOS = {"checkshot": "Sísmica de poço — tempo × profundidade (checkshot)",
              "vsp_bruto": "Sísmica de poço — registro de campo (tiro a tiro)"}
PRIORIDADE = {"checkshot": 0, "vsp_bruto": 1}

BYTES_AMOSTRA = {1: 4, 2: 4, 3: 2, 5: 4, 6: 8, 8: 1, 9: 8, 10: 4, 11: 2, 12: 8, 16: 1}


class ErroCheckshot(ValueError):
    pass


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return s.upper()


def reconhece(rel: str) -> bool:
    """SEG-Y da sísmica de poço: na pasta "Sismica de Poco" ou com nome de checkshot/VSP (um SEG-Y de sísmica
    de superfície, de milhões de traços, não entra)."""
    r = _norm(str(rel or "").replace("\\", "/"))
    if not r.endswith((".SGY", ".SEGY", ".SEG")):
        return False
    nome = r.rsplit("/", 1)[-1]
    return "SISMICA DE POCO" in r or "SISMICA_DE_POCO" in r or bool(re.search(r"CHECKSHOT|VSP|ASR|VSI|ZVSP", nome))


def tipo_pelo_nome(rel: str) -> str:
    return "vsp_bruto" if "RAW" in _norm(os.path.basename(rel)) else "checkshot"


# ---------------------------------------------------------------- cabeçalhos
def texto_cabecalho(b: bytes) -> str:
    """Cabeçalho textual (3200 bytes): ASCII ou EBCDIC, em 40 linhas de 80."""
    asc = b[:3200].decode("latin-1", "replace")
    if not asc.lstrip().startswith("C"):
        asc = b[:3200].decode("cp037", "replace")
    return "\n".join(asc[i:i + 80].rstrip() for i in range(0, 3200, 80))


def mapa_bytes(texto: str) -> dict[str, int]:
    """'Receiver:MD@173,TVD@181,RefElev@185' → {'receiver_md': 173, …} (posições de 1 a 240)."""
    mapa = {}
    for linha in texto.splitlines():
        corpo = linha[3:] if re.match(r"C\s*\d+", linha) else linha
        grupo = ""
        m = re.match(r"\s*([A-Za-z]+)(?:\([^)]*\))?:", corpo)
        if m:
            grupo = m.group(1).lower()
            corpo = corpo[m.end():]
        for nome, pos in re.findall(r"([A-Za-z0-9_]+)@(\d+)", corpo):
            chave = f"{grupo}_{nome.lower()}" if grupo else nome.lower()
            mapa[chave] = int(pos)
    return mapa


def campos_texto(texto: str) -> dict:
    saida = {}
    for rotulo, chave in (("POCO (SIGLA ANP)", "poco"), ("POCO (SIGLA OPERADORA)", "poco_operador"),
                          ("CADASTRO ANP", "cadastro"), ("CADASTRP ANP", "cadastro"), ("COMPANHIA", "companhia"),
                          ("DATA", "data"), ("BLOCO OU CAMPO", "bloco")):
        m = re.search(rf"{re.escape(rotulo)}\s*:\s*(.+)", _norm(texto))
        if m and chave not in saida:
            saida[chave] = m.group(1).strip() or None
    return saida


def _i4(h: bytes, pos: int) -> int:
    return struct.unpack(">i", h[pos - 1:pos + 3])[0]


def _i2(h: bytes, pos: int) -> int:
    return struct.unpack(">h", h[pos - 1:pos + 1])[0]


def _escala(v: int, esc: int) -> float:
    if esc < 0:
        return v / -esc
    if esc > 0:
        return float(v * esc)
    return float(v)


def ler_cabecalhos(caminho: str) -> tuple[str, dict, list[dict]]:
    """Texto, binário (amostras, intervalo, formato) e, de cada traço, os campos do mapa — sem ler o sinal."""
    tam = os.path.getsize(caminho)
    with open(caminho, "rb") as f:
        cab = f.read(3600)
        if len(cab) < 3600:
            raise ErroCheckshot("Arquivo curto demais para SEG-Y.")
        texto = texto_cabecalho(cab)
        ns, dt_us, fmt = struct.unpack(">H", cab[3220:3222])[0], struct.unpack(">H", cab[3216:3218])[0], \
            struct.unpack(">H", cab[3224:3226])[0]
        bps = BYTES_AMOSTRA.get(fmt)
        if not bps or not ns:
            raise ErroCheckshot(f"Cabeçalho binário do SEG-Y inválido (formato {fmt}, {ns} amostras).")
        passo = 240 + ns * bps
        n = (tam - 3600) // passo
        mapa = mapa_bytes(texto)
        if not any(k.startswith("receiver_") for k in mapa):
            raise ErroCheckshot("O cabeçalho textual do SEG-Y não diz onde estão a profundidade do receptor e o "
                                "tempo (ex.: 'Receiver:MD@173' e 'Times(us):pick@209'); este leiaute não é lido.")
        tracos = []
        for k in range(n):
            f.seek(3600 + k * passo)
            h = f.read(240)
            if len(h) < 240:
                break
            t = {"esc_elev": _i2(h, 69), "esc_coord": _i2(h, 71), "componente": _i2(h, 29), "cdp": _i4(h, 21)}
            for nome, pos in mapa.items():
                if 1 <= pos <= 237:
                    t[nome] = _i4(h, pos)
            tracos.append(t)
    return texto, {"amostras": ns, "intervalo_us": dt_us, "formato": fmt, "tracos": n}, tracos


# ---------------------------------------------------------------- tabela tempo × profundidade
def niveis(tracos: list[dict]) -> list[dict]:
    """Um nível por profundidade do receptor, com os tempos e as velocidades (ver o cálculo no topo)."""
    req = ("receiver_md", "receiver_tvd", "receiver_refelev", "times_pick")
    if not tracos or any(k not in tracos[0] for k in req):
        raise ErroCheckshot("O cabeçalho textual do SEG-Y não diz onde estão a profundidade do receptor e o "
                            "tempo (ex.: 'Receiver:MD@173' e 'Times(us):pick@209'); este leiaute não é lido.")
    vistos = {}
    for t in tracos:
        ee, ec = t["esc_elev"], t["esc_coord"]
        md = round(_escala(t["receiver_md"], ee), 2)
        if md in vistos or t["times_pick"] <= 0:
            continue
        vistos[md] = {
            "md": md, "tvd": _escala(t["receiver_tvd"], ee),
            "elev_mesa": _escala(t["receiver_refelev"], ee),
            "elev_fonte_ref": _escala(t.get("source_refelev", t["receiver_refelev"]), ee),
            "prof_fonte": _escala(t.get("source_sd", 0), ee),
            "datum": _escala(t.get("seismicdatumelev", t.get("source_refelev", t["receiver_refelev"])), ee),
            "sx": _escala(t.get("source_scx", 0), ec), "sy": _escala(t.get("source_scy", 0), ec),
            "rx": _escala(t.get("receiver_rcx", 0), ec), "ry": _escala(t.get("receiver_rcy", 0), ec),
            "pick_s": t["times_pick"] / 1e6, "atraso_s": t.get("times_extdelay", 0) / 1e6,
            "ts_s": t.get("times_datumcorr", 0) / 1e6,
        }
    saida = []
    for n in sorted(vistos.values(), key=lambda x: x["tvd"]):
        elev_fonte = n["elev_fonte_ref"] - n["prof_fonte"]
        dz = n["tvd"] - (n["elev_mesa"] - elev_fonte)
        sgo = math.hypot(n["sx"] - n["rx"], n["sy"] - n["ry"])
        tt = n["pick_s"] + n["atraso_s"]
        tv = tt * dz / math.hypot(dz, sgo) if dz > 0 else tt
        tcorr = tv + n["ts_s"]
        tvdsd = n["tvd"] - (n["elev_mesa"] - n["datum"])
        saida.append({"md": n["md"], "tvd": round(n["tvd"], 2), "tvdsd": round(tvdsd, 2), "tpick_s": round(n["pick_s"], 5),
                      "sgo_m": round(sgo, 2), "tv_s": round(tv, 5), "ts_s": round(n["ts_s"], 6), "tcorr_s": round(tcorr, 5),
                      "twt_ms": round(2000 * tcorr, 2), "vmed_m_s": round(tvdsd / tcorr) if tcorr > 0 else None})
    for k, n in enumerate(saida):
        if k == 0:
            n["vint_m_s"] = n["vmed_m_s"]
        else:
            a = saida[k - 1]
            dt = n["tcorr_s"] - a["tcorr_s"]
            n["vint_m_s"] = round((n["tvdsd"] - a["tvdsd"]) / dt) if dt > 0 else None
    return saida


def ler(caminho: str) -> dict:
    texto, binario, tracos = ler_cabecalhos(caminho)
    campos = campos_texto(texto)
    doc = tipo_pelo_nome(caminho)
    dados = {"documento": doc, "titulo": DOCUMENTOS[doc], "binario": binario, "cabecalho": campos,
             "gerais": {"poco": campos.get("poco")},
             "apelidos": [campos["poco_operador"]] if campos.get("poco_operador") else []}
    if doc == "vsp_bruto":
        try:
            mds = sorted({n["md"] for n in niveis(tracos)})
        except ErroCheckshot:
            mds = []
        dados.update({"tiros": len(tracos), "profundidades": mds})
        return dados
    tab = niveis(tracos)
    if not tab:
        raise ErroCheckshot("Nenhum traço com tempo de chegada (pick).")
    t0 = tracos[0]
    ee = t0["esc_elev"]
    dados.update({"niveis": tab,
                  "referencia": {"elev_mesa_m": _escala(t0["receiver_refelev"], ee),
                                 "datum_sismico_m": _escala(t0["seismicdatumelev"], ee) if "seismicdatumelev" in t0 else None,
                                 "prof_fonte_m": _escala(t0["source_sd"], ee) if "source_sd" in t0 else None,
                                 "afastamento_m": tab[0]["sgo_m"]}})
    return dados


def apelidos(dados: dict) -> list[str]:
    return dados.get("apelidos") or []


def itens(dados: dict) -> list[dict]:
    if dados.get("documento") != "checkshot":
        return []
    return [{"tipo": "checkshot", "nome": None, "prof_topo": n["md"], "cota": None, "valor": n["twt_ms"],
             "unidade": "ms (TWT)", "texto": None,
             "extra": {k: n[k] for k in ("tvd", "tvdsd", "tpick_s", "tv_s", "tcorr_s", "vmed_m_s", "vint_m_s", "sgo_m")}}
            for n in dados.get("niveis", [])]


def twt_em(niveis_: list[dict], md: float) -> float | None:
    """TWT (ms) numa profundidade medida, por interpolação linear entre os níveis (fora deles: None)."""
    pts = sorted((n["md"], n["twt_ms"]) for n in niveis_ if n.get("md") is not None and n.get("twt_ms") is not None)
    if len(pts) < 2 or md < pts[0][0] or md > pts[-1][0]:
        return None
    for (a, ta), (b, tb) in zip(pts, pts[1:]):
        if a <= md <= b:
            return ta if b == a else round(ta + (tb - ta) * (md - a) / (b - a), 2)
    return None


def csv(niveis_: list[dict], poco: str) -> str:
    """Tabela para levar à sísmica: profundidade medida, vertical e abaixo do datum, tempos e velocidades."""
    linhas = [f"# checkshot do poço {poco} (lido pelo SIAPP do cabeçalho do SEG-Y)",
              "MD_m;TVD_m;TVDSD_m;Tcorr_s;TWT_ms;Vmed_m_s;Vint_m_s"]
    for n in niveis_:
        linhas.append(";".join(str(x if x is not None else "") for x in (
            n["md"], n["tvd"], n["tvdsd"], n["tcorr_s"], n["twt_ms"], n["vmed_m_s"], n["vint_m_s"])))
    return "\n".join(linhas) + "\n"
