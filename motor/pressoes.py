"""Pressões do poço (bloco 9, item 2): teste de formação a cabo e teste de formação (TFR).

**Teste a cabo** (SFT/RFT/MDT…, pasta "Teste de Formacao a Cabo", `<poço>_sft-2.dlis`): um
arquivo lógico do DLIS por **estação**; o quadro é indexado por **tempo** (ETIM em ms), não por
profundidade — por isso o leitor de perfis o recusa. Em cada estação a sonda encosta na parede,
faz um ou mais pré-testes (puxa um pouco de fluido) e registra a pressão subindo de volta até a
pressão da formação. O canal da sonda (FPRE, na Halliburton) mostra, em ordem:

    lama (hidrostática) → assentamento → queda do pré-teste → recuperação → patamar → lama de novo

O SIAPP toma, em cada estação: a **hidrostática da lama** antes e depois (mediana dos primeiros e
dos últimos 15 s), a **pressão da formação** (mediana dos 20 s do último patamar, antes de a sonda
soltar), a menor pressão do pré-teste, quantos pré-testes, a pressão do patamar anterior (para
conferir a repetição) e a **inclinação** dos últimos 30 s do patamar (psi/min). Inclinação pequena = pressão
estabilizada; grande = formação fechada ou pouco tempo de espera. Estação em que a pressão nunca cai
abaixo da hidrostática = sem vedação ou sem pré-teste. Conferido em 29/10/2026 no 1-BRSA-1304-BA
(SFT, Halliburton, 8 estações): diferença de até 0,1 kgf/cm² para os valores do RFP em 7 delas; na
de 1.717 m o RFP registra o primeiro patamar (171,1) e o SIAPP mostra os dois.

**Teste de formação** (TFR/DST, pasta "Teste de Formacao", `<poço>_TFR.zip`): o ZIP traz o
relatório de interpretação (PDF de texto, formulário padrão da Petrobras) e os registros dos
manômetros (`.TPR`: data, hora, tempo em h, pressão em kgf/cm², temperatura em °C, a cada
alguns segundos), às vezes em ZIPs dentro do ZIP. O SIAPP lê tudo **dentro do ZIP**, sem extrair:
do relatório, pressão estática extrapolada, pressão de fluxo, vazão, °API, temperatura máxima,
IP, transmissibilidade, mobilidade, **permeabilidade efetiva**, efeito de película (skin), raio de
investigação, modelo, conclusões, parâmetros de fluido e de rocha adotados, os períodos de fluxo e
estática; dos manômetros, a série de cada um (reduzida para o gráfico) e os extremos.

Tudo em kgf/cm² (como os formulários brasileiros), com psi ao lado: 1 kgf/cm² = 14,2233 psi.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile

import numpy as np

VERSAO = 1
NOME = "Pressões: teste de formação a cabo (DLIS) e teste de formação (TFR)"
DOCUMENTOS = {"wft": "Teste de formação a cabo", "tfr": "Teste de formação (TFR)"}
PRIORIDADE = {"tfr": 0, "wft": 1}

KGF_PSI = 14.2233
PSI_FT_POR_G_CM3 = 0.43353      # gradiente da água doce: 0,433 psi/ft = 1 g/cm³

_PRESSAO_PSI = {"psi": 1.0, "psia": 1.0, "psig": 1.0, "kpa": 0.1450377, "mpa": 145.0377, "bar": 14.50377,
                "kgf/cm2": KGF_PSI, "kgf/cm²": KGF_PSI, "kg/cm2": KGF_PSI, "atm": 14.69595}
_TEMPO_S = {"ms": 0.001, "msec": 0.001, "s": 1.0, "sec": 1.0, "min": 60.0, "h": 3600.0, "hr": 3600.0,
            "us": 1e-6, "0.1ms": 1e-4, "0.5ms": 5e-4}
# canal da sonda, em ordem de preferência (quartzo antes de strain gauge)
CANAIS_PRESSAO = ("FPRE", "BQP1", "BQP", "QPRE", "QP", "PQ", "PRES", "PRESS", "FPRES", "SGP1", "SGP", "SGP2", "PSG")


class ErroPressao(ValueError):
    pass


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return " ".join(_sem_acento(str(s or "")).upper().split())


# ---------------------------------------------------------------- reconhecimento
_RE_WFT = re.compile(r"(?:^|[_\-\s.])(SFT|RFT|MDT|RCI|XPT|FRT|RDT|WFT|FMT)(?:[_\-\s.]|\d|$)")
_RE_TFR = re.compile(r"(?:^|[_\-\s.])(TFR|TFA|DST|TF)(?:[_\-\s.]|\d|$)")


def tipo_pelo_nome(rel: str) -> str | None:
    r = _norm(str(rel or "").replace("\\", "/"))
    nome = r.rsplit("/", 1)[-1]
    ext = nome.rsplit(".", 1)[-1] if "." in nome else ""
    if ext in ("DLIS", "DLS") and ("TESTE DE FORMACAO A CABO" in r or _RE_WFT.search(nome)):
        return "wft"
    if ext == "ZIP" and (("TESTE DE FORMACAO" in r and "A CABO" not in r) or _RE_TFR.search(nome)):
        return "tfr"
    if ext == "TPR":
        return "tfr"
    return None


def reconhece(rel: str) -> bool:
    return tipo_pelo_nome(rel) is not None


# ---------------------------------------------------------------- estação do teste a cabo
def analisar_estacao(t, p) -> dict:
    """Uma estação: tempo (s) e pressão (psi) → hidrostática, pressão da formação, qualidade."""
    t = np.asarray(t, dtype=float)
    p = np.asarray(p, dtype=float)
    ok = np.isfinite(t) & np.isfinite(p) & (p > 0)
    t, p = t[ok], p[ok]
    if len(p) < 20:
        return {"qualidade": "poucos dados", "pressao_psi": None}
    ordem = np.argsort(t, kind="stable")
    t, p = t[ordem], p[ordem]
    dt = float(np.median(np.diff(t))) or 1.0
    n0 = max(3, int(15 / dt))
    h_antes, h_depois = float(np.median(p[:n0])), float(np.median(p[-n0:]))
    href = min(h_antes, h_depois)
    tol = max(20.0, 0.01 * href)
    saida = {"hidrostatica_antes_psi": round(h_antes, 2), "hidrostatica_depois_psi": round(h_depois, 2),
             "duracao_s": round(float(t[-1] - t[0]), 1), "pressao_psi": None, "pressao_min_psi": None,
             "n_pretestes": 0, "pressao_patamar_anterior_psi": None, "inclinacao_psi_min": None}
    abaixo = np.where(p < href - tol)[0]
    if not len(abaixo):
        saida["qualidade"] = "sem vedação ou sem pré-teste"
        return saida
    i0, i1 = int(abaixo[0]), int(abaixo[-1])
    # fim do patamar: anda para trás enquanto a pressão ainda muda (> 1 psi em 5 s) — é a subida
    # quando a sonda solta; no máximo 30 s
    k5 = max(1, int(5 / dt))
    j = i1
    while j - k5 > i0 and abs(p[j] - p[j - k5]) > 1.0 and t[i1] - t[j] < 30:
        j -= 1
    sel = (t >= t[j] - 20) & (t <= t[j])
    pf = float(np.median(p[sel]))
    sel30 = (t >= t[j] - 30) & (t <= t[j])
    incl = float(np.polyfit(t[sel30] / 60.0, p[sel30], 1)[0]) if sel30.sum() > 5 else None
    pmin = float(p[i0:i1 + 1].min())
    # pré-testes: quedas rápidas (> 2 % da hidrostática em 5 s), separadas por mais de 10 s
    thr = max(30.0, 0.02 * href)
    quedas = np.where(p[k5:] - p[:-k5] < -thr)[0]
    inicios = []
    for q in quedas:
        if not inicios or t[q] - t[ultimo] > 10:
            inicios.append(int(q))
        ultimo = q
    anterior = None
    if len(inicios) >= 2:
        s = inicios[-1]
        sel_a = (t >= t[s] - 15) & (t <= t[s] - 1)
        if sel_a.sum():
            anterior = float(np.median(p[sel_a]))
            if anterior >= href - tol:       # antes do último pré-teste ainda era lama: não é patamar
                anterior = None
    saida.update(pressao_psi=round(pf, 2), pressao_min_psi=round(pmin, 2), n_pretestes=len(inicios),
                 pressao_patamar_anterior_psi=round(anterior, 2) if anterior is not None else None,
                 inclinacao_psi_min=round(incl, 3) if incl is not None else None)
    if pmin < 0.15 * href and incl is not None and abs(incl) > 2:
        saida["qualidade"] = "não estabilizou (formação fechada?)"
    elif incl is None or abs(incl) <= 0.5:
        saida["qualidade"] = "estabilizada"
    elif abs(incl) <= 2:
        saida["qualidade"] = "quase estável"
    else:
        saida["qualidade"] = "não estabilizou"
    return saida


def _canal_pressao(canais: list[tuple[str, str]]) -> tuple[str, float] | None:
    """(nome, fator para psi) do canal da sonda."""
    unid = {n.upper(): (u or "").strip().lower().replace(" ", "") for n, u in canais}
    for nome in CANAIS_PRESSAO:
        if nome in unid and unid[nome] in _PRESSAO_PSI:
            return nome, _PRESSAO_PSI[unid[nome]]
    for n, u in canais:                       # qualquer canal com unidade de pressão (fora a hidráulica)
        uu = (u or "").strip().lower().replace(" ", "")
        if uu in _PRESSAO_PSI and not n.upper().startswith("HYD"):
            return n.upper(), _PRESSAO_PSI[uu]
    return None


def _val(p):
    v = p.values
    if v is None or len(v) == 0:
        return None
    v = v[0]
    try:
        v = v.item()
    except AttributeError:
        pass
    if isinstance(v, (int, float)) and v <= -999:
        return None
    return v if not isinstance(v, str) or v.strip() not in ("", "-999.25") else None


CABECALHO_WFT = {"LNAM": "nome", "TOOL": "ferramenta", "TTL1": "titulo", "DFD": "peso_lama_lb_gal",
                 "DFT": "tipo_lama", "BHT": "bht_f", "MRT": "temp_max_f", "STEM": "temp_superficie_f",
                 "LDAT": "data", "TST": "n_testes", "EDF": "mesa_rotativa", "CN": "empresa_poco", "RIG": "sonda"}


def estacoes_dlis(arquivos) -> dict:
    """Estações de um DLIS já aberto (lista de arquivos lógicos do dlisio)."""
    estacoes, cab, avisos = [], {}, []
    for k, lf in enumerate(arquivos):
        params = {p.name: p for p in lf.parameters}
        if lf.origins and "poco" not in cab:
            nome_poco = str(lf.origins[0].well_name or "").strip()
            if nome_poco:
                cab["poco"] = nome_poco
        if len(cab) <= 1:
            cab.update({nome: _val(params[m]) for m, nome in CABECALHO_WFT.items() if m in params and _val(params[m])})
            notas = [str(_val(params[f"R{i}"])) for i in range(1, 13) if f"R{i}" in params and _val(params[f"R{i}"])]
            if notas:
                cab["observacoes"] = notas
        for fr in lf.frames:
            canais = [(c.name, c.units) for c in fr.channels]
            if not canais:
                continue
            idx_nome, idx_unid = canais[0]
            fator_t = _TEMPO_S.get((idx_unid or "").strip().lower().replace(" ", ""))
            if fator_t is None and str(getattr(fr, "index_type", "")).upper() != "TIME":
                continue                          # quadro por profundidade: não é estação
            escolha = _canal_pressao(canais[1:])
            if escolha is None:
                avisos.append(f"arquivo lógico {k}: sem canal de pressão")
                continue
            try:
                dados = fr.curves()
            except Exception as e:  # noqa: BLE001 — quadro corrompido
                avisos.append(f"arquivo lógico {k}: {e}")
                continue
            nomes = {n.upper(): n for n in dados.dtype.names}
            t = np.asarray(dados[nomes[idx_nome.upper()]], dtype=float) * (fator_t or 1.0)
            p = np.asarray(dados[nomes[escolha[0]]], dtype=float)
            p[p <= -999] = np.nan
            r = analisar_estacao(t, p * escolha[1])
            prof = None
            for cand in ("DEPT", "DEPTH", "TDEP", "MD"):
                if cand in nomes:
                    d = np.asarray(dados[nomes[cand]], dtype=float)
                    d = d[np.isfinite(d) & (d > -999)]
                    if len(d):
                        u = dict(canais).get(cand) or dict((n.upper(), u) for n, u in canais).get(cand, "m")
                        prof = float(np.median(d)) * (0.3048 if (u or "").lower().startswith("f") else 1.0)
                    break
            r.update(estacao=len(estacoes) + 1, arquivo_logico=k, canal=escolha[0],
                     prof=round(prof, 2) if prof is not None else None)
            for chave in ("pressao_psi", "pressao_min_psi", "hidrostatica_antes_psi", "hidrostatica_depois_psi",
                          "pressao_patamar_anterior_psi"):
                v = r.get(chave)
                r[chave.replace("_psi", "_kgf_cm2")] = round(v / KGF_PSI, 3) if v is not None else None
            # série reduzida para o gráfico da estação (≤ 400 pontos)
            passo = max(1, -(-len(t) // 400))
            ok = np.isfinite(p)
            r["serie"] = {"t_s": [round(float(x - t[0]), 1) for x in t[ok][::passo]],
                          "p_psi": [round(float(x), 1) for x in (p * escolha[1])[ok][::passo]]}
            estacoes.append(r)
    if not estacoes:
        raise ErroPressao("Nenhuma estação de teste a cabo no arquivo (quadro indexado por tempo, com pressão).")
    return {"cabecalho": cab, "estacoes": estacoes, "avisos": avisos}


def ler_wft(caminho: str) -> dict:
    from dlisio import dlis
    try:
        with dlis.load(caminho) as arquivos:
            r = estacoes_dlis(arquivos)
    except ErroPressao:
        raise
    except Exception as e:  # noqa: BLE001 — DLIS que o dlisio não abre
        raise ErroPressao(f"Não consegui abrir o DLIS: {type(e).__name__}: {e}") from e
    return {"documento": "wft", "titulo": DOCUMENTOS["wft"], **r,
            "gerais": {"poco": r["cabecalho"].get("poco")}, "apelidos": _apelidos_wft(r["cabecalho"])}


def _apelidos_wft(cab: dict) -> list[str]:
    t = str(cab.get("titulo") or "").strip()
    return [t] if re.fullmatch(r"\d-[A-Z0-9]{2,6}-\d{1,4}[A-Z]?-[A-Z]{2}", t) else []


# ---------------------------------------------------------------- manômetros (.TPR)
def _num(s) -> float | None:
    t = str(s or "").strip().replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _num_br(s) -> float | None:
    """Número do relatório (pt-BR): '1.680' = 1680; '2.948,6' = 2948,6; '0,0004'."""
    t = str(s or "").strip().replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?", t):
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def ler_tpr(texto: str, nome: str = "") -> dict:
    """Registro de manômetro: cabeçalho ('# CHAVE: valor') e colunas DATA HORA D.TIME PRESSÃO TEMP."""
    cab, linhas = {}, []
    unidade_p = "kgf/cm2"
    for bruta in texto.splitlines():
        ln = bruta.strip()
        if not ln:
            continue
        if ln.startswith("#"):
            m = re.match(r"#\s*#?\s*([^:]+):\s*(.*)", ln)
            if m:
                cab.setdefault(_norm(m[1]), m[2].strip())
            continue
        if ln.startswith(";"):
            if "PSI" in ln.upper():
                unidade_p = "psi"
            continue
        partes = ln.split()
        if len(partes) >= 4:
            h, pr = _num(partes[2]), _num(partes[3])
            te = _num(partes[4]) if len(partes) > 4 else None
            if h is not None and pr is not None:
                linhas.append((h, pr, te))
    if not linhas:
        raise ErroPressao(f"{nome or 'registro'}: nenhuma linha de dados (DATA HORA TEMPO PRESSÃO TEMPERATURA).")
    a = np.array([(h, p, np.nan if te is None else te) for h, p, te in linhas], dtype=float)
    fator = 1 / KGF_PSI if unidade_p == "psi" else 1.0
    pk = a[:, 1] * fator
    prof = None
    for k, v in cab.items():
        if k.startswith("PROFUNDIDADE"):
            m = re.search(r"-?\d[\d.,]*", v)
            prof = _num(m[0]) if m else None
    reg = next((v for k, v in cab.items() if k.startswith("REGISTRADOR")), "")
    passo = max(1, -(-len(a) // 1500))
    return {"arquivo": nome, "registrador": reg.split(" ")[0] if reg else "", "registrador_desc": reg,
            "profundidade": prof, "sensor": cab.get("TIPO DE SENSOR") or "",
            "posicao": next((v for k, v in cab.items() if k.startswith("POSI")), ""),
            "poco_operadora": next((v for k, v in cab.items() if "PETROBRAS" in k or k.startswith("POCO")), ""),
            "teste": cab.get("TESTE") or "", "n_amostras": len(a), "duracao_h": round(float(a[-1, 0] - a[0, 0]), 3),
            "pressao_max_kgf_cm2": round(float(np.nanmax(pk)), 3),
            "temperatura_max_c": round(float(np.nanmax(a[:, 2])), 2) if np.isfinite(a[:, 2]).any() else None,
            "serie": {"h": [round(float(x), 4) for x in a[::passo, 0]],
                      "p_kgf_cm2": [round(float(x), 3) for x in pk[::passo]],
                      "t_c": [None if not np.isfinite(x) else round(float(x), 2) for x in a[::passo, 2]]}}


def _decodificar(b: bytes) -> str:
    for cod in ("utf-8", "cp1252", "latin-1"):
        try:
            return b.decode(cod)
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1", errors="replace")


# ---------------------------------------------------------------- relatório do TFR (PDF)
_ROTULOS_TFR = {
    # capa e identificação
    "NUMERO DO RELATORIO": "relatorio", "SIGLA DO POCO - ANP": "poco", "SIGLA DO POCO - PETROBRAS": "sigla_operadora",
    "IDENTIFICACAO DO TESTE": "teste", "INTERVALO TESTADO - TOPO": "topo", "INTERVALO TESTADO - BASE": "base",
    "DATA DE INICIO DO TESTE": "inicio", "DATA DO FIM DO TESTE": "fim", "DATA DE EMISSAO": "emissao",
    "REVESTIMENTO": "revestimento", "CIA. EXECUTANTE": "companhia", "FORMACAO": "formacao", "ZONA": "zona",
    "SONDA DA INTERVENCAO": "sonda",
    # resultados
    "PRESSAO ESTATICA EXTRAPOLADA": "pressao_estatica_kgf_cm2", "PRESSAO DE FLUXO FINAL (": "pressao_fluxo_kgf_cm2",
    "VAZAO (M": "vazao_m3_dia", "°API DO OLEO": "api", "TEMPERATURA MAXIMA REGISTRADA": "temp_max_c",
    "COEFICIENTE DE ESTOCAGEM": "estocagem", "IP (PSEUDO": "ip", "TRANSMISSIBILIDADE": "transmissibilidade",
    "MOBILIDADE": "mobilidade", "PERMEABILIDADE EFETIVA": "permeabilidade_md", "EFEITO DE PELICULA": "skin",
    "RAZAO DE DANO": "razao_dano", "RAIO DE INVESTIGACAO": "raio_investigacao_m",
    "PRESSAO ESTATICA NOS CANHONEADOS": "pressao_canhoneados_kgf_cm2",
    "PROFUNDIDADE DE REFERENCIA": "prof_referencia",
    # outros parâmetros adotados
    "ESPESSURA EFETIVA": "espessura_m", "POROSIDADE": "porosidade_pct", "SATURACAO DE AGUA": "sw_pct",
    "RAIO DO POCO": "raio_poco_m",
}
_ROTULOS_TFR_LINHA = {"MEDIDA (M)": "prof_registro_medida", "VERTICAL (M)": "prof_registro_vertical",
                      "COTA (M)": "prof_registro_cota"}
_NUMERICOS_TFR = {"pressao_estatica_kgf_cm2", "pressao_fluxo_kgf_cm2", "vazao_m3_dia", "api", "temp_max_c",
                  "estocagem", "ip", "transmissibilidade", "mobilidade", "permeabilidade_md", "skin", "razao_dano",
                  "raio_investigacao_m", "pressao_canhoneados_kgf_cm2", "prof_referencia", "espessura_m",
                  "porosidade_pct", "sw_pct", "raio_poco_m", "prof_registro_medida", "prof_registro_vertical",
                  "prof_registro_cota"}
_FLUIDOS_TFR = {"MASSA ESPECIFICA": "massa_especifica_g_cm3", "VISCOSIDADE": "viscosidade_cp",
                "FATOR VOLUME FORMACAO": "fator_volume", "FATOR Z": "fator_z", "DENSIDADE": "densidade",
                "COMPRESSIBILIDADE": "compressibilidade_1e6", "°API (STD)": "api"}
_VAZOES_TFR = {"PERIODO": "periodo", "DURACAO": "duracao", "FLUIDO": "fluido", "VOLUME RECUPERADO": "volume_m3",
               "BSW": "bsw_pct", "VAZAO DE LIQUIDO CORRIGIDA": "vazao_liquido_m3_dia", "VAZAO DE GAS": "vazao_gas_mil_m3_dia",
               "ABERTURA": "abertura_64", "RAZAO GAS-OLEO": "rgo_m3_m3", "PRESSAO DE FLUXO FINAL": "pressao_fluxo_kgf_cm2",
               "TEMPERATURA DE FLUXO FINAL": "temp_fluxo_c"}


def _linhas_pdf(pagina) -> list[list[tuple[float, str]]]:
    por = {}
    for b in pagina.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                t = s["text"].strip()
                if t:
                    y = round(s["bbox"][1] / 3)        # mesma linha: até ~3 pt
                    por.setdefault(y, []).append((s["bbox"][0], t))
    return [sorted(por[y]) for y in sorted(por)]


def _casa(rotulos: dict, texto: str) -> str | None:
    n = _norm(texto)
    for r, k in rotulos.items():
        if n.startswith(r):
            return k
    return None


def ler_relatorio_tfr(doc) -> dict:
    """Relatório de interpretação de teste (PDF de texto, formulário Petrobras)."""
    campos, fluidos, vazoes, periodos, textos = {}, {}, {}, {}, []
    colunas_vazao = []
    todo = []
    for pagina in doc:
        txt = pagina.get_text()
        todo.append(txt)
        n_txt = _norm(txt)
        tabela_vazoes = "IDENTIFICACAO E MEDICAO DOS FLUIDOS" in n_txt
        tabela_operacao = "INFORMACOES DA OPERACAO" in n_txt
        tabela_fluidos = "PARAMETROS DE FLUIDO ADOTADOS" in n_txt
        for linha in _linhas_pdf(pagina):
            x0, t0 = linha[0]
            if tabela_vazoes and (k := _casa(_VAZOES_TFR, t0)) and x0 < 120 and len(linha) > 1 and k not in vazoes:
                if k == "periodo":
                    colunas_vazao = [x for x, _ in linha[1:]]
                if colunas_vazao:
                    vals = {}
                    for x, t in linha[1:]:
                        i = int(np.argmin([abs(x - c) for c in colunas_vazao]))
                        vals[i] = t
                    vazoes[k] = [vals.get(i) for i in range(len(colunas_vazao))]
                continue
            if tabela_operacao and x0 < 120 and _casa({"PERIODO": "p", "DURACAO": "d"}, t0):
                periodos[_casa({"PERIODO": "periodo", "DURACAO": "duracao"}, t0)] = [t for _, t in linha[1:]]
                continue
            if tabela_fluidos and x0 < 120 and (k := _casa(_FLUIDOS_TFR, t0)):
                vals = {"oleo": None, "gas": None, "agua": None}
                for x, t in linha[1:]:
                    col = "oleo" if x < 290 else "gas" if x < 340 else "agua" if x < 390 else None
                    if col and t not in ("-", "—") and _num_br(t) is not None:
                        vals[col] = _num_br(t)
                fluidos[k] = vals
                continue
            # pares rótulo → valor (uma ou duas colunas de pares por linha)
            i = 0
            while i < len(linha):
                x, t = linha[i]
                k = _casa(_ROTULOS_TFR, t) or (_casa(_ROTULOS_TFR_LINHA, t) if x > 150 else None)
                if k and i + 1 < len(linha) and not (_casa(_ROTULOS_TFR, linha[i + 1][1])):
                    campos.setdefault(k, linha[i + 1][1])
                    i += 2
                else:
                    i += 1
    texto = "\n".join(todo)
    for k in list(campos):
        if k in _NUMERICOS_TFR or k in ("topo", "base"):
            m = re.search(r"-?\d[\d.,]*", campos[k])
            campos[k] = _num_br(m[0]) if m else None
    if not campos.get("pressao_estatica_kgf_cm2") and not campos.get("permeabilidade_md") and not campos.get("poco"):
        raise ErroPressao("PDF sem os campos do relatório de interpretação de teste.")
    m = re.search(r"Intervalo \(m\)\s*\n\s*([\d.,]+)\s*-\s*([\d.,]+)", texto)
    if m and campos.get("topo") is None:
        campos["topo"], campos["base"] = _num_br(m[1]), _num_br(m[2])
    est = re.findall(r"pest(\d)\s*=\s*([\d.,]+)", texto)
    if est:
        campos["pressoes_estaticas"] = [{"periodo": int(n), "kgf_cm2": _num_br(v)} for n, v in est]
    pfi = re.findall(r"pf([if])(\d)\s*=\s*([\d.,]+)", texto)
    if pfi:
        campos["pressoes_fluxo"] = [{"tipo": "inicial" if a == "i" else "final", "periodo": int(n), "kgf_cm2": _num_br(v)}
                                    for a, n, v in pfi]
    m = re.search(r"Registrador utilizado na interpreta\w+:\s*(\d+)", texto)
    if m:
        campos["registrador_interpretacao"] = m[1]
    campos.update(_textos_tfr(texto))
    if fluidos:
        campos["fluidos_adotados"] = fluidos
    if vazoes.get("periodo"):
        campos["fluxos"] = [{k: (v[i] if k in ("periodo", "duracao", "fluido") else _num(v[i]))
                             for k, v in vazoes.items() if i < len(v)} for i in range(len(vazoes["periodo"]))]
    if periodos.get("periodo"):
        campos["periodos"] = [{"periodo": p, "duracao": (periodos.get("duracao") or [None] * 9)[i]}
                              for i, p in enumerate(periodos["periodo"])]
    return campos


_TITULOS_TEXTO_TFR = {
    "1. CONCLUSIVIDADE DO TESTE EM RELACAO AOS OBJETIVOS": "conclusao", "FLUIDO DO INTERVALO E PROPRIEDADES": "fluido_desc",
    "PARAMETROS DA FORMACAO E MODELO UTILIZADO": "modelo", "PARAMETROS DE LIMITE E MODELO UTILIZADO": "limites",
    "DADOS CARACTERISTICOS DE PRODUCAO": "producao", "AMOSTRAGEM": "amostragem",
}
_PARA_TEXTO_TFR = ("2. PARAMETROS DA FORMACAO", "PRESSOES CARACTERISTICAS", "INDICE DE PRODUTIVIDADE", "3. OPERACOES",
                   "4. CONSIDERACOES", "TESTE", "OBJETIVOS", "RESULTADOS OBTIDOS")


def _textos_tfr(texto: str) -> dict:
    """Parágrafos que vêm depois de um título conhecido, até o próximo título (cabeçalho de página fora)."""
    saida, atual, cab = {}, None, set()
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    # o cabeçalho de cada página (poço, intervalo, relatório) se repete: o que aparece em todas sai
    from collections import Counter
    cont = Counter(linhas)
    n_pag = max(1, cont.get("Sigla do poço ANP:", 1))
    cab = {ln for ln, n in cont.items() if n >= n_pag and n_pag > 2}
    for ln in linhas:
        n = _norm(ln)
        if n in _TITULOS_TEXTO_TFR:
            atual = _TITULOS_TEXTO_TFR[n]
            saida.setdefault(atual, [])
            continue
        if atual is None:
            continue
        if any(n.startswith(t) for t in _PARA_TEXTO_TFR) or n in _TITULOS_TEXTO_TFR or re.fullmatch(r"\d+ /\d+", ln):
            atual = None
            continue
        if ln in cab:
            continue
        saida[atual].append(ln)
    def juntar(ls):
        # linha curta ou que fecha frase ("Conclusivo", "…reservatório.") quebra; o resto é o mesmo parágrafo
        texto = ""
        for ln in ls:
            if texto:
                ant = texto.rsplit("\n", 1)[-1]
                texto += "\n" if ant.endswith((".", ";", ":", "!", "?")) or len(ant) < 30 else " "
            texto += ln
        return texto[:800]
    return {k: juntar(v) for k, v in saida.items() if v}


def ler_tfr_zip(dados_zip: bytes, nome: str = "") -> dict:
    """ZIP do teste de formação: relatório(s) PDF e registros .TPR, inclusive em ZIPs internos."""
    import pymupdf
    relatorio, manometros, outros, avisos = None, [], [], []

    def percorrer(z: zipfile.ZipFile, prefixo: str, nivel: int):
        nonlocal relatorio
        for info in z.infolist():
            if info.is_dir():
                continue
            caminho = prefixo + info.filename
            base = info.filename.rsplit("/", 1)[-1]
            ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
            if info.file_size > 300e6:
                avisos.append(f"{caminho}: grande demais, ignorado")
                continue
            try:
                conteudo = z.read(info)
            except (RuntimeError, zipfile.BadZipFile, NotImplementedError) as e:
                avisos.append(f"{caminho}: {e}")
                continue
            if ext == "zip" and nivel < 3:
                try:
                    percorrer(zipfile.ZipFile(io.BytesIO(conteudo)), caminho + "/", nivel + 1)
                except zipfile.BadZipFile as e:
                    avisos.append(f"{caminho}: {e}")
            elif ext == "tpr":
                try:
                    manometros.append(ler_tpr(_decodificar(conteudo), base))
                except ErroPressao as e:
                    avisos.append(str(e))
            elif ext == "pdf":
                eh_rel = False
                try:
                    with pymupdf.open(stream=conteudo, filetype="pdf") as doc:
                        if "INTERPRETA" in _norm(doc[0].get_text()) and relatorio is None:
                            relatorio = ler_relatorio_tfr(doc)
                            relatorio["arquivo"] = caminho
                            eh_rel = True
                except ErroPressao:
                    pass
                except Exception as e:  # noqa: BLE001 — PDF estranho dentro do ZIP
                    avisos.append(f"{caminho}: {e}")
                if not eh_rel:
                    outros.append({"arquivo": caminho, "bytes": info.file_size})
            else:
                outros.append({"arquivo": caminho, "bytes": info.file_size})

    try:
        percorrer(zipfile.ZipFile(io.BytesIO(dados_zip)), "", 0)
    except zipfile.BadZipFile as e:
        raise ErroPressao(f"ZIP inválido: {e}") from e
    if relatorio is None and not manometros:
        raise ErroPressao("O ZIP não tem relatório de interpretação nem registros de manômetro (.TPR).")
    rel = relatorio or {}
    interp = rel.get("registrador_interpretacao")
    for m in manometros:
        m["interpretacao"] = bool(interp) and m["registrador"] == interp
    manometros.sort(key=lambda m: (not m["interpretacao"], m["profundidade"] or 0))
    apel = [a for a in {rel.get("sigla_operadora"), *(m["poco_operadora"] for m in manometros)} if a]
    return {"documento": "tfr", "titulo": DOCUMENTOS["tfr"], "arquivo_zip": nome, "relatorio": relatorio,
            "manometros": manometros, "outros_arquivos": outros, "avisos": avisos,
            "gerais": {"poco": rel.get("poco")},
            "apelidos": sorted(a for a in apel if re.fullmatch(r"\d-[A-Z0-9]{2,6}-\d{1,4}[A-Z]?-[A-Z]{2}", a))}


def ler(caminho: str) -> dict:
    tipo = tipo_pelo_nome(caminho)
    if tipo == "wft":
        return ler_wft(caminho)
    if caminho.lower().endswith(".tpr"):
        with open(caminho, "rb") as f:
            m = ler_tpr(_decodificar(f.read()), caminho.replace("\\", "/").rsplit("/", 1)[-1])
        return {"documento": "tfr", "titulo": DOCUMENTOS["tfr"], "relatorio": None, "manometros": [m],
                "outros_arquivos": [], "avisos": [], "gerais": {}, "apelidos": []}
    with open(caminho, "rb") as f:
        return ler_tfr_zip(f.read(), caminho.replace("\\", "/").rsplit("/", 1)[-1])


def apelidos(dados: dict) -> list[str]:
    return list(dados.get("apelidos") or [])


# ---------------------------------------------------------------- itens para o banco
def itens(dados: dict) -> list[dict]:
    saida = []
    if dados.get("documento") == "wft":
        cab = dados.get("cabecalho") or {}
        for e in dados.get("estacoes", []):
            extra = {k: v for k, v in e.items() if k != "serie"}
            saida.append({"tipo": "pressao_formacao", "nome": f"estação {e['estacao']}", "prof_topo": e["prof"],
                          "valor": e.get("pressao_kgf_cm2"), "unidade": "kgf/cm²", "texto": e["qualidade"],
                          "extra": {**extra, "ferramenta": cab.get("ferramenta") or cab.get("nome")}})
        if cab.get("temp_max_f"):
            saida.append({"tipo": "temperatura", "nome": f"{cab.get('ferramenta') or 'teste a cabo'} (máxima registrada)",
                          "prof_topo": max((e["prof"] or 0) for e in dados.get("estacoes", [])) or None,
                          "valor": float(cab["temp_max_f"]), "unidade": "°F", "texto": "lida", "extra": {}})
        return saida
    rel = dados.get("relatorio") or {}
    if rel:
        extra = {k: v for k, v in rel.items() if k not in ("fluidos_adotados", "fluxos", "periodos")}
        saida.append({"tipo": "teste_tfr", "nome": rel.get("teste") or "TFR", "prof_topo": rel.get("topo"),
                      "prof_base": rel.get("base"), "valor": rel.get("pressao_estatica_kgf_cm2"),
                      "unidade": "kgf/cm²", "texto": rel.get("fluido_desc") or None, "extra": extra})
        if rel.get("temp_max_c") is not None:
            saida.append({"tipo": "temperatura", "nome": f"{rel.get('teste') or 'TFR'} (máxima registrada)",
                          "prof_topo": rel.get("prof_registro_medida") or rel.get("prof_referencia"),
                          "valor": rel["temp_max_c"], "unidade": "°C", "texto": "lida", "extra": {}})
    for m in dados.get("manometros", []):
        saida.append({"tipo": "manometro", "nome": m["registrador"] or m["arquivo"], "prof_topo": m["profundidade"],
                      "valor": m["pressao_max_kgf_cm2"], "unidade": "kgf/cm²", "texto": m["posicao"] or None,
                      "extra": {k: v for k, v in m.items() if k != "serie"}})
    return saida


# ---------------------------------------------------------------- gradiente
def gradiente(pontos: list[tuple[float, float]]) -> dict:
    """Reta pressão × profundidade (kgf/cm² × m) pelos mínimos quadrados → gradiente e densidade."""
    a = np.array([(z, p) for z, p in pontos if z is not None and p is not None], dtype=float)
    if len(a) < 2 or np.ptp(a[:, 0]) < 0.5:
        raise ErroPressao("Escolha ao menos dois pontos em profundidades diferentes.")
    b, c = np.polyfit(a[:, 0], a[:, 1], 1)                 # p = b·z + c
    prev = b * a[:, 0] + c
    ss = float(((a[:, 1] - a[:, 1].mean()) ** 2).sum())
    r2 = 1 - float(((a[:, 1] - prev) ** 2).sum()) / ss if ss > 0 else 1.0
    dens = b * 10.0                                         # 0,1 kgf/cm²/m = 1 g/cm³
    if dens < 0.4:
        fluido = "gás"
    elif dens < 0.95:
        fluido = "óleo"
    elif dens <= 1.25:
        fluido = "água"
    else:
        fluido = "acima da água (confira os pontos)"
    return {"n": len(a), "gradiente_kgf_cm2_m": round(float(b), 5), "gradiente_psi_ft": round(float(b) * KGF_PSI * 0.3048, 4),
            "densidade_g_cm3": round(float(dens), 3), "fluido_compativel": fluido,
            "intercepto_kgf_cm2": round(float(c), 3), "r2": round(r2, 4),
            "topo": float(a[:, 0].min()), "base": float(a[:, 0].max()),
            "residuo_max_kgf_cm2": round(float(np.abs(a[:, 1] - prev).max()), 3)}


def contato(g1: dict, g2: dict) -> float | None:
    """Profundidade em que duas retas de gradiente se cruzam (ex.: óleo × água)."""
    db = g1["gradiente_kgf_cm2_m"] - g2["gradiente_kgf_cm2_m"]
    if abs(db) < 1e-6:
        return None
    return round((g2["intercepto_kgf_cm2"] - g1["intercepto_kgf_cm2"]) / db, 1)


# ---------------------------------------------------------------- painel do poço (ficha)
def painel(dp: dict) -> dict:
    """Pontos de pressão × profundidade do poço, de todas as fontes, para o gráfico e o gradiente.
    `dp`: saída de dados_poco.do_poco. Cada ponto tem um id estável."""
    it = dp.get("itens") or {}
    pontos, series = [], []
    for e in it.get("pressao_formacao", []):
        x = e["extra"]
        pontos.append({"id": f"wft:{e['rel']}:{x.get('estacao')}", "origem": "teste a cabo", "prof": e["prof_topo"],
                       "pressao_kgf_cm2": e["valor"], "hidrostatica_kgf_cm2": x.get("hidrostatica_antes_kgf_cm2"),
                       "qualidade": e["texto"], "rotulo": f"{x.get('ferramenta') or 'cabo'} · estação {x.get('estacao')}",
                       "anterior_kgf_cm2": x.get("pressao_patamar_anterior_kgf_cm2"),
                       "inclinacao_psi_min": x.get("inclinacao_psi_min"), "n_pretestes": x.get("n_pretestes"),
                       "serie": {"rel": e["rel"], "qual": f"estacao:{x.get('estacao')}"}})
    for t in it.get("teste_formacao", []):
        if t["valor"] is None or t["prof_topo"] is None:
            continue
        prof = t["extra"].get("prof_registrador") or t["prof_topo"]
        pontos.append({"id": f"form:{t['rel']}:{t['ordem']}", "origem": (t["documento"] or "").upper() or "formulário",
                       "prof": prof, "pressao_kgf_cm2": t["valor"], "hidrostatica_kgf_cm2": None,
                       "qualidade": None, "rotulo": f"{t['nome'] or 'teste'}" + (f" · {t['texto']}" if t["texto"] else "")})
    for t in it.get("teste_tfr", []):
        x = t["extra"]
        prof = x.get("prof_referencia") or x.get("prof_registro_medida") or t["prof_topo"]
        if t["valor"] is not None and prof is not None:
            pontos.append({"id": f"tfr:{t['rel']}", "origem": "TFR", "prof": prof, "pressao_kgf_cm2": t["valor"],
                           "hidrostatica_kgf_cm2": None, "qualidade": "extrapolada",
                           "rotulo": f"{t['nome']} · estática extrapolada"})
    for m in it.get("manometro", []):
        series.append({"rel": m["rel"], "qual": f"manometro:{m['nome']}", "interpretacao": m["extra"].get("interpretacao"),
                       "rotulo": f"manômetro {m['nome']} · {m['texto'] or ''} · {m['prof_topo'] or '—'} m".replace(" ·  ·", " ·")})
    pontos.sort(key=lambda p: (p["prof"] or 0))
    lama = []
    for le in dp.get("leituras", []):
        d = le.get("dados") or {}
        if d.get("documento") == "wft" and (d.get("cabecalho") or {}).get("peso_lama_lb_gal"):
            lama.append({"rel": le["rel"], "peso_lb_gal": float(d["cabecalho"]["peso_lama_lb_gal"]),
                         "tipo": d["cabecalho"].get("tipo_lama")})
    tfr = [{"rel": t["rel"], "nome": t["nome"], "topo": t["prof_topo"], "base": t["prof_base"],
            "pressao_estatica_kgf_cm2": t["valor"], **{k: v for k, v in t["extra"].items()}}
           for t in it.get("teste_tfr", [])]
    for le in dp.get("leituras", []):
        d = le.get("dados") or {}
        rel = d.get("relatorio") or {}
        for t in tfr:
            if t["rel"] == le["rel"]:
                t["fluxos"] = rel.get("fluxos") or []
                t["periodos"] = rel.get("periodos") or []
                t["fluidos_adotados"] = rel.get("fluidos_adotados") or {}
                t["outros_arquivos"] = d.get("outros_arquivos") or []
    return {"pontos": pontos, "series": series, "lama": lama, "tfr": tfr}


def serie(dados: dict, qual: str) -> dict:
    """Série de uma estação ('estacao:3') ou de um manômetro ('manometro:30768') de uma leitura."""
    tipo, _, chave = str(qual).partition(":")
    if tipo == "estacao":
        for e in dados.get("estacoes", []):
            if str(e.get("estacao")) == chave:
                return {"x": e["serie"]["t_s"], "y": [round(v / KGF_PSI, 3) for v in e["serie"]["p_psi"]],
                        "x_rotulo": "tempo (s)", "y_rotulo": "pressão (kgf/cm²)",
                        "linhas": {k: e.get(k) for k in ("pressao_kgf_cm2", "hidrostatica_antes_kgf_cm2",
                                                          "pressao_patamar_anterior_kgf_cm2")},
                        "titulo": f"estação {chave} · {e.get('prof')} m · {e.get('qualidade')}"}
    if tipo == "manometro":
        for m in dados.get("manometros", []):
            if m["registrador"] == chave or m["arquivo"] == chave:
                return {"x": m["serie"]["h"], "y": m["serie"]["p_kgf_cm2"], "t": m["serie"]["t_c"],
                        "x_rotulo": "tempo (h)", "y_rotulo": "pressão (kgf/cm²)", "linhas": {},
                        "titulo": f"manômetro {m['registrador']} · {m['posicao']} · {m['profundidade']} m"}
    raise ErroPressao(f"Série {qual} não encontrada.")
