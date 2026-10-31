"""Camadas geográficas de fora do REATE: gasodutos, campos, blocos, termelétricas, portos…

Três fontes públicas, todas em SIRGAS 2000 geográfico (EPSG 4674):

- **IBGE — BC250** (Base Cartográfica Contínua 1:250.000, versão mais recente): um zip
  nacional de ~800 MB com todas as camadas. O SIAPP lê só o índice do zip e baixa só as
  camadas escolhidas (pedidos HTTP com *Range*: o duto inteiro são ~100 KB, não 800 MB);
- **EPE — WebMap** (serviço ArcGIS da Empresa de Pesquisa Energética): gasodutos de
  transporte, de escoamento e de distribuição com diâmetro, operador e situação, UPGNs,
  city gates, estações de compressão, terminais de GNL, termelétricas fósseis. Os dutos do
  IBGE são poucos (111 trechos em 2025, sem o Nordestão nem o Gasfor); os da EPE vêm da
  relação de dutos da ANP;
- **ANP** (dados georreferenciados das bacias): campos de produção e blocos exploratórios.

Cada camada fica em `sig/<fonte>/<camada>.geojson` (para o mapa e o QGIS) e, quando veio
como shapefile, também o shapefile original em `sig/<fonte>/<camada>/`. Um índice
(`sig/camadas.json`) diz de onde veio cada uma, quando e quantas feições tem. Este módulo
só traz e guarda; desenhar no mapa e medir distâncias ficam para depois.
"""

from __future__ import annotations

import io
import json
import os
import re
import struct
import zipfile
import zlib
from urllib.parse import urljoin

from .banco import agora
from .producao import AGENTE, links

PASTA_SIG = "sig"
IBGE_BC250 = "https://geoftp.ibge.gov.br/cartas_e_mapas/bases_cartograficas_continuas/bc250/"
EPE_SERVICO = "https://gisepeprd2.epe.gov.br/arcgis/rest/services/WMS_Webmap_EPE_Data/MapServer/"
ANP_GEO = ("https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/"
           "arquivos-dados-georreferenciados-das-bacias-sedimentares-brasileiras/")
EPE_PAGINA = 1000
EPE_REST = "https://gisepeprd2.epe.gov.br/arcgis/rest/services/"
EPE_LOTE_IDS = 500

# id, fonte, onde, nome, tipo, padrão (marcada), descrição
CATALOGO = [
    # EPE — infraestrutura de gás (o mais completo para a distância ao gasoduto)
    {"id": "epe_gasodutos_transporte", "fonte": "EPE", "camada": 55, "nome": "Gasodutos de transporte",
     "tipo": "linha", "padrao": True, "desc": "Malha de transporte (Nordestão, Gasfor, GASBOL…): diâmetro, pressão, transportadora"},
    {"id": "epe_dutos_escoamento", "fonte": "EPE", "camada": 54, "nome": "Dutos de escoamento da produção",
     "tipo": "linha", "padrao": True, "desc": "Dos campos às estações e UPGNs (relação de dutos da ANP): diâmetro, fluido, origem e destino"},
    {"id": "epe_gasodutos_distribuicao", "fonte": "EPE", "camada": 56, "nome": "Gasodutos de distribuição",
     "tipo": "linha", "padrao": False, "desc": "Redes das distribuidoras estaduais (Potigás, Algás…)"},
    {"id": "epe_upgn", "fonte": "EPE", "camada": 51, "nome": "UPGNs (processamento de gás)", "tipo": "ponto",
     "padrao": True, "desc": "Unidades de processamento de gás natural: capacidade (MMm³/d), situação"},
    {"id": "epe_compressao", "fonte": "EPE", "camada": 52, "nome": "Estações de compressão", "tipo": "ponto",
     "padrao": False, "desc": "Estações de compressão da malha de transporte"},
    {"id": "epe_citygates", "fonte": "EPE", "camada": 53, "nome": "City gates", "tipo": "ponto", "padrao": False,
     "desc": "Pontos de entrega do gás às distribuidoras e grandes consumidores"},
    {"id": "epe_terminais_gnl", "fonte": "EPE", "camada": 50, "nome": "Terminais de GNL", "tipo": "ponto",
     "padrao": False, "desc": "Terminais de regaseificação"},
    {"id": "epe_termeletricas_fosseis", "fonte": "EPE", "camada": 20, "nome": "Termelétricas fósseis (existentes)",
     "tipo": "ponto", "padrao": True, "desc": "Fontes estacionárias de CO₂: potência, combustível, proprietário"},
    # EPE — hidrogênio de baixo carbono (mapa de projetos; o SIAPP usa a edição mais recente publicada)
    {"id": "epe_h2_projetos", "fonte": "EPE", "servico": "SEE/H2_PROJETOS_*", "camada": 0,
     "nome": "Hidrogênio verde: unidades e projetos", "tipo": "ponto", "padrao": True,
     "desc": "Plantas piloto, P&D e projetos de H₂ verde e amônia (Pecém, Suape, Açu…): capacidade (t/ano), "
             "finalidade, estágio (piloto, MoU, pré-contrato), investimento (R$ milhões)"},
    # ANP
    {"id": "anp_campos_producao", "fonte": "ANP", "arquivo": "campos-producao.zip", "nome": "Campos de produção",
     "tipo": "poligono", "padrao": True, "desc": "Polígonos dos campos: operador, fluido principal, etapa, início da produção"},
    {"id": "anp_blocos_exploratorios", "fonte": "ANP", "arquivo": "blocos-exploratorios.zip",
     "nome": "Blocos exploratórios sob contrato", "tipo": "poligono", "padrao": True,
     "desc": "Blocos em fase de exploração: operador, rodada, área"},
    # IBGE — BC250
    {"id": "ibge_dutos", "fonte": "IBGE", "shp": "dut_trecho_duto_l", "nome": "Dutos (BC250)", "tipo": "linha",
     "padrao": True, "desc": "Gasodutos, oleodutos e minerodutos da base 1:250.000 (incompleta para gás: use a EPE)"},
    {"id": "ibge_termeletricas", "fonte": "IBGE", "shp": "enc_termeletrica_p", "nome": "Termelétricas (BC250)",
     "tipo": "ponto", "padrao": True, "desc": "Usinas termelétricas: potência e combustível"},
    {"id": "ibge_linhas_transmissao", "fonte": "IBGE", "shp": "enc_trecho_energia_l", "nome": "Linhas de transmissão",
     "tipo": "linha", "padrao": False, "desc": "Trechos de energia elétrica"},
    {"id": "ibge_subestacoes", "fonte": "IBGE", "shp": "enc_subest_transm_distrib_energia_eletrica_p",
     "nome": "Subestações", "tipo": "ponto", "padrao": False, "desc": "Subestações de transmissão e distribuição"},
    {"id": "ibge_portos", "fonte": "IBGE", "shp": "hdv_complexo_portuario_p", "nome": "Portos", "tipo": "ponto",
     "padrao": True, "desc": "Complexos portuários (logística de CO₂ e H₂)"},
    {"id": "ibge_cidades", "fonte": "IBGE", "shp": "lml_cidade_p", "nome": "Cidades (sedes municipais)",
     "tipo": "ponto", "padrao": True, "desc": "Sedes dos municípios"},
    {"id": "ibge_estados", "fonte": "IBGE", "shp": "lml_unidade_federacao_a", "nome": "Estados", "tipo": "poligono",
     "padrao": False, "desc": "Limites das unidades da federação (~7 MB)"},
    {"id": "ibge_ferrovias", "fonte": "IBGE", "shp": "fer_trecho_ferroviario_l", "nome": "Ferrovias", "tipo": "linha",
     "padrao": False, "desc": "Trechos ferroviários (~2 MB)"},
    {"id": "ibge_rodovias", "fonte": "IBGE", "shp": "rod_trecho_rodoviario_l", "nome": "Rodovias", "tipo": "linha",
     "padrao": False, "desc": "Trechos rodoviários (~45 MB)"},
]
# Restrições ambientais (0.52): UCs federais do ICMBio e Terras Indígenas (importadas por você).
CATALOGO += [
    {"id": "icmbio_ucs", "fonte": "ICMBio", "wfs": "ICMBio:limiteucsfederais_a", "tipo": "poligono", "padrao": False,
     "nome": "Unidades de Conservação federais (ICMBio)",
     "desc": "Limites das UCs federais (só as federais: UCs estaduais e municipais não estão aqui). Pode passar de 20 MB"},
    {"id": "terras_indigenas", "fonte": "Importada", "tipo": "poligono", "padrao": False,
     "nome": "Terras indígenas (FUNAI) — você importa o arquivo",
     "desc": "O servidor de mapas da FUNAI não abriu com certificado válido: baixe o shapefile (zip) ou GeoJSON no "
             "site da FUNAI e use “Importar terras indígenas…”"},
]
POR_ID = {c["id"]: c for c in CATALOGO}
FONTES = {"IBGE": "IBGE — Base Cartográfica Contínua 1:250.000 (BC250)",
          "EPE": "EPE — WebMap (Empresa de Pesquisa Energética)",
          "ANP": "ANP — dados georreferenciados das bacias sedimentares",
          "ICMBio": "ICMBio — unidades de conservação (via INDE)",
          "Importada": "Arquivos que você importou"}
ICMBIO_WFS = "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows"


class ErroCamadas(ValueError):
    pass


# ====================================================================== shapefile
def _encoding_dbf(dbf: bytes, cpg: bytes | None) -> str:
    if cpg:
        nome = cpg.decode("ascii", errors="ignore").strip().lower()
        if nome:
            return {"utf8": "utf-8", "utf-8": "utf-8", "1252": "cp1252", "ansi 1252": "cp1252"}.get(nome, nome)
    ldid = dbf[29] if len(dbf) > 29 else 0
    return {0x57: "cp1252", 0x03: "cp1252", 0x01: "cp437", 0x02: "cp850"}.get(ldid, "")


def ler_dbf(dados: bytes, encoding: str = "") -> list[dict]:
    n, hl, rl = struct.unpack("<IHH", dados[4:12])
    campos, p = [], 32
    while dados[p] != 0x0D:
        nome = dados[p:p + 11].split(b"\0")[0].decode("latin1")
        campos.append((nome, chr(dados[p + 11]), dados[p + 16], dados[p + 17]))
        p += 32

    def txt(b: bytes) -> str:
        if encoding:
            return b.decode(encoding, errors="replace")
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            return b.decode("cp1252", errors="replace")
    out = []
    for i in range(n):
        p = hl + i * rl
        if p + rl > len(dados):
            break
        if dados[p:p + 1] == b"*":                      # apagado
            continue
        p += 1
        reg = {}
        for nome, tipo, tam, dec in campos:
            bruto = dados[p:p + tam]
            p += tam
            s = txt(bruto).strip()
            if tipo in "NF":
                try:
                    v = float(s) if s and "*" not in s else None
                    reg[nome] = int(v) if v is not None and dec == 0 and v.is_integer() else v
                except ValueError:
                    reg[nome] = None
            elif tipo == "L":
                reg[nome] = {"T": True, "Y": True, "F": False, "N": False}.get(s.upper()[:1])
            else:
                reg[nome] = s
        out.append(reg)
    return out


def _horario(anel) -> bool:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:]):
        a += (x2 - x1) * (y2 + y1)
    return a > 0


def ler_shp(dados: bytes) -> list[dict | None]:
    """Geometrias GeoJSON de um .shp (ponto, multiponto, linha, polígono, com ou sem Z/M)."""
    out, p = [], 100
    while p + 8 <= len(dados):
        _, tam = struct.unpack(">II", dados[p:p + 8])
        rec = dados[p + 8:p + 8 + tam * 2]
        p += 8 + tam * 2
        if len(rec) < 4:
            break
        tipo = struct.unpack("<i", rec[:4])[0]
        base = tipo % 10 if tipo != 0 else 0
        if base == 0:
            out.append(None)
        elif base == 1:                                   # ponto
            x, y = struct.unpack("<2d", rec[4:20])
            out.append({"type": "Point", "coordinates": [round(x, 7), round(y, 7)]})
        elif base == 8:                                   # multiponto
            n = struct.unpack("<i", rec[36:40])[0]
            pts = struct.unpack(f"<{2 * n}d", rec[40:40 + 16 * n])
            out.append({"type": "MultiPoint", "coordinates": [[round(pts[i], 7), round(pts[i + 1], 7)]
                                                              for i in range(0, 2 * n, 2)]})
        elif base in (3, 5):                              # linha, polígono
            npart, npts = struct.unpack("<2i", rec[36:44])
            partes = list(struct.unpack(f"<{npart}i", rec[44:44 + 4 * npart])) + [npts]
            q = 44 + 4 * npart
            xy = struct.unpack(f"<{2 * npts}d", rec[q:q + 16 * npts])
            aneis = [[[round(xy[2 * k], 7), round(xy[2 * k + 1], 7)] for k in range(partes[i], partes[i + 1])]
                     for i in range(npart)]
            if base == 3:
                out.append({"type": "LineString", "coordinates": aneis[0]} if len(aneis) == 1
                           else {"type": "MultiLineString", "coordinates": aneis})
            else:                                         # anel horário = externo; anti-horário = buraco
                polis: list[list] = []
                for a in aneis:
                    if _horario(a) or not polis:
                        polis.append([a])
                    else:
                        polis[-1].append(a)
                out.append({"type": "Polygon", "coordinates": polis[0]} if len(polis) == 1
                           else {"type": "MultiPolygon", "coordinates": polis})
        else:
            out.append(None)
    return out


def shapefile_geojson(shp: bytes, dbf: bytes, cpg: bytes | None = None) -> dict:
    geos = ler_shp(shp)
    atrs = ler_dbf(dbf, _encoding_dbf(dbf, cpg))
    feats = [{"type": "Feature", "geometry": g, "properties": a} for g, a in zip(geos, atrs) if g is not None]
    return {"type": "FeatureCollection", "features": feats}


def caixa(geojson: dict) -> list[float] | None:
    xs, ys = [], []

    def andar(c):
        if c and isinstance(c[0], (int, float)):
            xs.append(c[0])
            ys.append(c[1])
        else:
            for k in c:
                andar(k)
    for f in geojson.get("features", []):
        if f.get("geometry"):
            andar(f["geometry"]["coordinates"])
    return [round(min(xs), 5), round(min(ys), 5), round(max(xs), 5), round(max(ys), 5)] if xs else None


# ====================================================================== zip remoto (só as partes pedidas)
class ZipRemoto:
    """Lê arquivos de dentro de um zip na internet sem baixá-lo inteiro (HTTP Range)."""

    def __init__(self, url: str, sessao, timeout: float = 120):
        self.url, self.sessao, self.timeout = url, sessao, timeout
        r = sessao.head(url, timeout=(30, timeout), headers=AGENTE, allow_redirects=True)
        self.tamanho = int(r.headers.get("content-length") or 0)
        if r.status_code != 200 or not self.tamanho:
            raise ErroCamadas(f"Não consegui ler o tamanho de {url} (HTTP {r.status_code}).")
        cauda = self._faixa(max(0, self.tamanho - 65558), self.tamanho - 1)
        e = cauda.rfind(b"PK\x05\x06")
        if e < 0:
            raise ErroCamadas("Zip sem índice no fim (ou servidor sem Range).")
        n, cd_tam, cd_ini = struct.unpack("<HII", cauda[e + 10:e + 20])
        if cd_ini == 0xFFFFFFFF:
            raise ErroCamadas("Zip64 não suportado.")
        cd = self._faixa(cd_ini, cd_ini + cd_tam - 1)
        self.entradas, p = {}, 0
        for _ in range(n):
            (_, _, _, flags, metodo, _, _, _, csz, usz, nl, xl, cl, _, _, _, off) = struct.unpack(
                "<IHHHHHHIIIHHHHHII", cd[p:p + 46])
            nome = cd[p + 46:p + 46 + nl].decode("utf-8" if flags & 0x800 else "cp437")
            self.entradas[nome] = (metodo, csz, usz, off)
            p += 46 + nl + xl + cl

    def _faixa(self, ini: int, fim: int) -> bytes:
        r = self.sessao.get(self.url, timeout=(30, self.timeout), headers={**AGENTE, "Range": f"bytes={ini}-{fim}"})
        if r.status_code != 206:
            raise ErroCamadas(f"O servidor não aceitou baixar só um pedaço do arquivo (HTTP {r.status_code}).")
        return r.content

    def procurar(self, final: str) -> str | None:
        final = final.lower()
        return next((n for n in self.entradas if n.lower().endswith(final)), None)

    def ler(self, nome: str) -> bytes:
        metodo, csz, usz, off = self.entradas[nome]
        cab = self._faixa(off, off + 29)
        nl, xl = struct.unpack("<HH", cab[26:30])
        bruto = self._faixa(off + 30 + nl + xl, off + 30 + nl + xl + csz - 1) if csz else b""
        if metodo == 0:
            return bruto
        if metodo == 8:
            return zlib.decompress(bruto, -15)
        raise ErroCamadas(f"Compressão {metodo} não suportada em {nome}.")


def ultimo_zip_bc250(sessao, timeout: float = 60) -> str:
    """O zip de shapefiles da versão mais recente da BC250."""
    r = sessao.get(IBGE_BC250, timeout=(30, timeout), headers=AGENTE)
    versoes = sorted({int(m) for m in re.findall(r'href="versao(\d{4})/?"', r.text)}, reverse=True)
    for v in versoes:
        pasta = f"{IBGE_BC250}versao{v}/shapefiles/"
        r2 = sessao.get(pasta, timeout=(30, timeout), headers=AGENTE)
        if r2.status_code != 200:
            continue
        zips = [u for _, u in links(r2.text, pasta) if u.lower().endswith(".zip")]
        if zips:
            return sorted(zips)[-1]
    raise ErroCamadas("Não achei o zip de shapefiles da BC250 no servidor do IBGE.")


# ====================================================================== EPE (ArcGIS REST)
def servico_epe(padrao: str, sessao, timeout: float = 60) -> str:
    """URL do MapServer da EPE. "SEE/H2_PROJETOS_*" = a edição mais recente (sufixo AAAAMM)."""
    if "*" not in padrao:
        return f"{EPE_REST}{padrao}/MapServer/"
    pasta, nome = padrao.split("/", 1)
    r = sessao.get(f"{EPE_REST}{pasta}", timeout=(30, timeout), headers=AGENTE, params={"f": "json"})
    if r.status_code != 200:
        raise ErroCamadas(f"A EPE respondeu HTTP {r.status_code} ao listar os serviços.")
    prefixo = f"{pasta}/{nome.rstrip('*')}"
    edicoes = sorted(s["name"] for s in r.json().get("services", [])
                     if s.get("type") == "MapServer" and re.fullmatch(re.escape(prefixo) + r"\d{6}", s.get("name", "")))
    if not edicoes:
        raise ErroCamadas(f"Não achei o serviço {padrao} na EPE.")
    return f"{EPE_REST}{edicoes[-1]}/MapServer/"


def _consulta_epe(url: str, sessao, timeout: float, params: dict) -> dict:
    r = sessao.get(url, timeout=(30, timeout), headers=AGENTE, params=params)
    if r.status_code != 200:
        raise ErroCamadas(f"A EPE respondeu HTTP {r.status_code}.")
    return r.json()


def _tem_coordenadas(geo) -> bool:
    def ok(c):
        if isinstance(c, (int, float)):
            return c == c and abs(c) != float("inf")
        return bool(c) and all(ok(k) for k in c)
    return bool(geo) and ok(geo.get("coordinates"))


def epe_feicoes(camada: int, sessao, timeout: float = 120, progresso=None, servico: str = EPE_SERVICO) -> dict:
    """Todas as feições de uma camada do WebMap da EPE (GeoJSON, EPSG 4674): em páginas, ou —
    nos serviços que não paginam — pelos ids, em lotes. Feição sem coordenadas fica de fora (contada)."""
    url = f"{servico}{camada}/query"
    base = {"outFields": "*", "outSR": 4674, "f": "geojson"}
    feats, inicio = [], 0
    while True:
        g = _consulta_epe(url, sessao, timeout, {**base, "where": "1=1", "resultOffset": inicio,
                                                  "resultRecordCount": EPE_PAGINA})
        if "error" in g:
            if "pagination" not in str(g["error"].get("message", "")).lower():
                raise ErroCamadas(f"A EPE recusou a consulta: {g['error'].get('message')}")
            ids = _consulta_epe(url, sessao, timeout, {"where": "1=1", "returnIdsOnly": "true", "f": "json"})
            if "error" in ids:
                raise ErroCamadas(f"A EPE recusou a consulta: {ids['error'].get('message')}")
            lista = sorted(ids.get("objectIds") or [])
            feats = []
            for i in range(0, len(lista), EPE_LOTE_IDS):
                g2 = _consulta_epe(url, sessao, timeout, {**base, "objectIds": ",".join(map(str, lista[i:i + EPE_LOTE_IDS]))})
                if "error" in g2:
                    raise ErroCamadas(f"A EPE recusou a consulta: {g2['error'].get('message')}")
                feats += g2.get("features") or []
                if progresso:
                    progresso(len(feats))
            break
        lote = g.get("features") or []
        feats += lote
        mais = g.get("exceededTransferLimit") or (g.get("properties") or {}).get("exceededTransferLimit")
        if progresso:
            progresso(len(feats))
        if not lote or not mais:
            break
        inicio += len(lote)
    validas = [f for f in feats if _tem_coordenadas(f.get("geometry"))]
    for f in validas:                                     # tira campos internos do ArcGIS
        f.pop("id", None)
        f["properties"] = {k: (v.strip() if isinstance(v, str) else v) for k, v in (f.get("properties") or {}).items()
                           if not k.startswith("Shape") and not k.startswith("OBJECTID") and k != "FID"}
    return {"type": "FeatureCollection", "features": validas, "sem_coordenadas": len(feats) - len(validas)}


# ====================================================================== baixar e guardar
def _salvar_json(caminho: str, dados) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, caminho)


def indice(pasta_projeto: str) -> dict:
    caminho = os.path.join(pasta_projeto, PASTA_SIG, "camadas.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"camadas": {}}


def _guardar(pasta_projeto: str, item: dict, geojson: dict, origem: str, arquivos: dict | None = None) -> dict:
    base = os.path.join(pasta_projeto, PASTA_SIG, item["fonte"].lower())
    caminho = os.path.join(base, item["id"] + ".geojson")
    sem = geojson.pop("sem_coordenadas", 0)
    _salvar_json(caminho, geojson)
    if arquivos:                                          # o shapefile original, para o QGIS
        pasta = os.path.join(base, item["id"])
        os.makedirs(pasta, exist_ok=True)
        for nome, dados in arquivos.items():
            with open(os.path.join(pasta, nome), "wb") as f:
                f.write(dados)
    campos = sorted({k for f in geojson["features"][:200] for k in (f.get("properties") or {})})
    reg = {"id": item["id"], "nome": item["nome"], "fonte": item["fonte"], "tipo": item["tipo"],
           "origem": origem, "baixado_em": agora(), "feicoes": len(geojson["features"]), "sem_coordenadas": sem,
           "caixa": caixa(geojson), "campos": campos,
           "arquivo": os.path.relpath(caminho, pasta_projeto).replace(os.sep, "/"),
           "bytes": os.path.getsize(caminho)}
    idx = indice(pasta_projeto)
    idx.setdefault("camadas", {})[item["id"]] = reg
    idx["atualizado_em"] = agora()
    _salvar_json(os.path.join(pasta_projeto, PASTA_SIG, "camadas.json"), idx)
    return reg


def baixar(pasta_projeto: str, ids: list[str], *, sessao=None, progresso=None, cancelar=None) -> dict:
    """Baixa as camadas pedidas; uma que falha não impede as outras."""
    import requests
    sessao = sessao or requests.Session()
    prog = progresso or (lambda t: None)
    cancelar = cancelar or (lambda: False)
    feitos, erros = [], []
    pedidos = [POR_ID[i] for i in ids if i in POR_ID]
    if not pedidos:
        raise ErroCamadas("Escolha ao menos uma camada.")
    zip_ibge = None
    for k, item in enumerate(pedidos, 1):
        if cancelar():
            erros.append({"id": "-", "erro": "cancelado"})
            break
        prog(f"Camada {k} de {len(pedidos)}: {item['nome']} ({item['fonte']})…")
        try:
            if item["fonte"] == "EPE":
                servico = servico_epe(item["servico"], sessao) if item.get("servico") else EPE_SERVICO
                g = epe_feicoes(item["camada"], sessao, servico=servico,
                                progresso=lambda n: prog(f"Camada {k} de {len(pedidos)}: {item['nome']} — {n} feições"))
                feitos.append(_guardar(pasta_projeto, item, g, f"{servico}{item['camada']}"))
            elif item["fonte"] == "Importada":
                raise ErroCamadas("Esta camada vem de um arquivo seu: use “Importar terras indígenas…”.")
            elif item["fonte"] == "ICMBio":
                g = wfs_geojson(sessao, ICMBIO_WFS, item["wfs"])
                feitos.append(_guardar(pasta_projeto, item, g, f"{ICMBIO_WFS}?typeName={item['wfs']}"))
            elif item["fonte"] == "ANP":
                url = ANP_GEO + item["arquivo"]
                r = sessao.get(url, timeout=(30, 300), headers=AGENTE)
                if r.status_code != 200:
                    raise ErroCamadas(f"A ANP respondeu HTTP {r.status_code}.")
                z = zipfile.ZipFile(io.BytesIO(r.content))
                arqs = {os.path.basename(n): z.read(n) for n in z.namelist()
                        if re.search(r"\.(shp|shx|dbf|prj|cpg)$", n, re.I)}
                shp = next(v for n, v in arqs.items() if n.lower().endswith(".shp"))
                dbf = next(v for n, v in arqs.items() if n.lower().endswith(".dbf"))
                cpg = next((v for n, v in arqs.items() if n.lower().endswith(".cpg")), None)
                feitos.append(_guardar(pasta_projeto, item, shapefile_geojson(shp, dbf, cpg), url, arqs))
            else:
                if zip_ibge is None:
                    prog("IBGE: lendo o índice da BC250 (sem baixar o zip inteiro)…")
                    zip_ibge = ZipRemoto(ultimo_zip_bc250(sessao), sessao)
                arqs = {}
                for ext in ("shp", "shx", "dbf", "prj", "cpg"):
                    nome = zip_ibge.procurar(f"/{item['shp']}.{ext}") or zip_ibge.procurar(f"{item['shp']}.{ext}")
                    if nome:
                        arqs[f"{item['shp']}.{ext}"] = zip_ibge.ler(nome)
                if f"{item['shp']}.shp" not in arqs or f"{item['shp']}.dbf" not in arqs:
                    raise ErroCamadas(f"A camada {item['shp']} não está nesta versão da BC250.")
                g = shapefile_geojson(arqs[f"{item['shp']}.shp"], arqs[f"{item['shp']}.dbf"],
                                      arqs.get(f"{item['shp']}.cpg"))
                feitos.append(_guardar(pasta_projeto, item, g, zip_ibge.url, arqs))
        except zipfile.BadZipFile:
            erros.append({"id": item["id"], "nome": item["nome"], "erro": "o arquivo baixado não é um zip válido"})
        except (ErroCamadas, OSError, ValueError, KeyError, StopIteration) as e:
            erros.append({"id": item["id"], "nome": item["nome"], "erro": str(e) or type(e).__name__})
        except Exception as e:  # requests (sem conexão, tempo esgotado)
            erros.append({"id": item["id"], "nome": item["nome"], "erro": f"{type(e).__name__}: {e}"})
    return {"feitos": feitos, "erros": erros}


def catalogo_com_estado(pasta_projeto: str | None) -> list[dict]:
    idx = indice(pasta_projeto)["camadas"] if pasta_projeto else {}
    return [{**{k: v for k, v in c.items() if k in ("id", "fonte", "nome", "tipo", "padrao", "desc")},
             "baixada": idx.get(c["id"])} for c in CATALOGO]


def wfs_geojson(sessao, url: str, camada: str, timeout: float = 300) -> dict:
    """Todas as feições de uma camada WFS (GeoServer), em WGS84, como GeoJSON."""
    r = sessao.get(url, timeout=(30, timeout), headers=AGENTE,
                   params={"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": camada,
                           "outputFormat": "application/json", "srsName": "EPSG:4326"})
    if r.status_code != 200:
        raise ErroCamadas(f"O servidor respondeu HTTP {r.status_code} para a camada {camada}.")
    try:
        g = r.json()
    except ValueError as e:
        raise ErroCamadas(f"O servidor não devolveu GeoJSON para a camada {camada}.") from e
    if g.get("type") != "FeatureCollection" or not g.get("features"):
        raise ErroCamadas(f"A camada {camada} veio sem feições.")
    return g


def importar(pasta_projeto: str, ident: str, caminho: str) -> dict:
    """Guarda uma camada a partir de um arquivo seu: shapefile em .zip (WGS84 ou SIRGAS 2000, em graus) ou GeoJSON."""
    item = POR_ID.get(ident)
    if not item or item["fonte"] != "Importada":
        raise ErroCamadas("Esta camada não é importada de arquivo.")
    nome = os.path.basename(caminho)
    arqs = None
    try:
        if nome.lower().endswith(".zip"):
            z = zipfile.ZipFile(caminho)
            arqs = {os.path.basename(n): z.read(n) for n in z.namelist() if re.search(r"\.(shp|shx|dbf|prj|cpg)$", n, re.I)}
            shp = next((v for n, v in arqs.items() if n.lower().endswith(".shp")), None)
            dbf = next((v for n, v in arqs.items() if n.lower().endswith(".dbf")), None)
            cpg = next((v for n, v in arqs.items() if n.lower().endswith(".cpg")), None)
            if shp is None or dbf is None:
                raise ErroCamadas("O zip não tem .shp e .dbf.")
            prj = next((v for n, v in arqs.items() if n.lower().endswith(".prj")), b"").decode("latin-1", "ignore").upper()
            if prj and not any(t in prj for t in ("GCS_", "GEOGCS", "SIRGAS", "WGS")) or "PROJCS" in prj:
                raise ErroCamadas("O shapefile está em coordenadas projetadas (metros). Reprojete para graus (WGS84 ou "
                                  "SIRGAS 2000) no QGIS e importe de novo.")
            g = shapefile_geojson(shp, dbf, cpg)
        elif nome.lower().endswith((".geojson", ".json")):
            with open(caminho, encoding="utf-8") as f:
                g = json.load(f)
            if g.get("type") != "FeatureCollection" or not g.get("features"):
                raise ErroCamadas("O GeoJSON precisa ser uma FeatureCollection com feições.")
        else:
            raise ErroCamadas("Use um shapefile em .zip ou um arquivo .geojson/.json.")
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        raise ErroCamadas(f"Não consegui ler {nome}: {e}") from e
    box = caixa(g)
    if not box or not (-180 <= box[0] <= box[2] <= 180 and -90 <= box[1] <= box[3] <= 90):
        raise ErroCamadas("As coordenadas não parecem graus de longitude/latitude (WGS84/SIRGAS 2000).")
    return _guardar(pasta_projeto, item, g, f"arquivo importado: {nome}", arqs)


def url_fonte(item: dict) -> str:
    if item["fonte"] == "EPE":
        if item.get("servico"):
            return f"{EPE_REST}{item['servico'].replace('*', '')}"
        return urljoin(EPE_SERVICO, str(item["camada"]))
    if item["fonte"] == "ANP":
        return ANP_GEO + item["arquivo"]
    if item["fonte"] == "ICMBio":
        return f"{ICMBIO_WFS}?typeName={item['wfs']}"
    if item["fonte"] == "Importada":
        return "arquivo importado por você"
    return IBGE_BC250
