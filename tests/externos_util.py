"""Servidor falso da ANP, do IBGE e da EPE para os testes (dados sintéticos, nos formatos reais)."""

from __future__ import annotations

import io
import json
import struct
import zipfile
from urllib.parse import urlencode

from motor import camadas as mca
from motor import producao as mpr

ARQ = mpr.BASE_ANP + "centrais-de-conteudo/dados-abertos/arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
NAC = ARQ + "arquivos-producao-de-petroleo-e-gas-natural-nacional/"
URL_PT_ANTIGO = NAC + "pt/1988-1983/producao-terra-1983.csv"
URL_PT_SEM = NAC + "pt/2015/producao-terra-2015-2sem.csv"
URL_PT_NOVO = NAC + "pt/2026/producao_por_poco_terra_2026_2_trim.csv"
URL_PM = NAC + "pm/producao-mar-2026.csv"
URL_ZONA = ARQ + "producao-por-zona/producao_zona_05-2026.csv"
URL_ZONA_2 = ARQ + "producao-por-zona/Produo_Zona_042026.csv"
URL_PD = mpr.BASE_ANP + "assuntos/exploracao-e-producao-de-oleo-e-gas/desenvolvimento-e-producao/pd/campo_teste.pdf"

# cabeçalho antigo (sem colchetes) e novo ([Ano]…), como nos arquivos da ANP
CAB = ("Ano,Mês/Ano,Estado,Bacia,Campo,Poço,Ambiente,Instalação,Produção de Óleo (m³),Produção de Condensado (m³),"
       "Produção de Gás Associado (Mm³),Produção de Gás Não Associado (Mm³),Produção de Água (m³),Injeção de Gás (Mm³),"
       "Injeção de Água para Recuperação Secundária (m³),Injeção de Água para Descarte (m³),Injeção de Gás Carbônico (Mm³),"
       "Injeção de Nitrogênio (Mm³),Injeção de Vapor de Água (t),Injeção de Polímeros (m³),Injeção de Outros Fluidos (m³)")
CAB_NOVO = ",".join(f"[{c}]" for c in CAB.split(","))

PT_ANTIGO = ("﻿" + CAB + "\n"
             '1983,01/1983,Rio Grande do Norte,Potiguar,CAMPO TESTE,1-AA-1-RN,Terra,Não Informado,"858,1",0,"0,021",0,"16,1",,,,,,,,\n'
             "1983,01/1983,Alagoas,Alagoas,OUTRO CAMPO,7-OC-1-AL,Terra,Não Informado,372,0,\"5,538\",0,\"967,8\",,,,,,,,\n")
PT_SEM = ("﻿" + CAB + "\n"
          '2015,07/2015,Rio Grande do Norte,Potiguar,CAMPO TESTE,1-AA-1-RN,Terra,Não Informado,"100,5",0,"1,5",0,"200",,,,,,,,\n')
PT_NOVO = ("﻿" + CAB_NOVO + "\n"
           '2026,05/2026,Rio Grande do Norte,Potiguar,CAMPO TESTE,1-AA-1-RN,TERRA,Estação Coletora A,"186,18","0,00","0,230","0,000","2.619,83",,,,,,,,\n'
           '2026,05/2026,Rio Grande do Norte,Potiguar,CAMPO TESTE,1-AA-2-RN,TERRA,Estação Coletora A,"36,08","0,00","0,045","0,000","696,65",,,,,,,,\n'
           '2026,06/2026,Rio Grande do Norte,Potiguar,Campo Teste,1-AA-1-RN,TERRA,Estação Coletora A,"180,00","0,00","0,220","0,000","2.700,00",,,,,,,,\n'
           '2026,06/2026,Rio Grande do Norte,Potiguar,CAMPO TESTE,8-AA-9-RN,TERRA,Estação Coletora A,,,,,,"0,000","1.500,00","8,90","0,000","0,000","0,00","0,00","0,00"\n'
           '2026,06/2026,Sergipe,Sergipe,TIGRE,7-TG-9-SE,TERRA,Estação Coletora de Tigre,"1,00","0,00","0,000","0,000","1,00",,,,,,,,\n')
ZONA_CAB = ("Zona,Nome poço ANP,Campo,Bacia,Ambiente,Data,Óleo (m³/d),Condensado (m³/d),Petróleo (m³/d),Gás associado (Mil m³/d),"
            "Gás não associado (Mil m³/d),Gás total (Mil m³/d),Água (m³/d),Água injetada para descarte (m³/d),"
            "Água injetada para rec. secundária (m³/d),Vapor injetado (t/d),Gás injetado (Mil m³/d),CO2 injetado (Mil m³/d),"
            "N2 injetado (Mil m³/d),Outros fluidos injetados (m³/d)")
ZONA = ("﻿" + ZONA_CAB + "\n"
        'AÇU0250 FSP-2,1-AA-1-RN,CAMPO TESTE,Potiguar,TERRA,01/05/2026,"2,00","0,00","2,00","0,01","0,00","0,01","10,00","0,00","0,00","0,00","0,00","0,00","0,00","0,00"\n'
        'ALG,1-AA-2-RN,CAMPO TESTE,Potiguar,TERRA,01/05/2026,"1,00","0,00","1,00","0,00","0,00","0,00","5,00","0,00","0,00","0,00","0,00","0,00","0,00","0,00"\n'
        '3874,7-ATL-2HP-RJS,ATLANTA,Santos,MAR,01/05/2026,"417,26","0,00","417,26","19,43","0,00","19,43","182,87","0,00","0,00","0,00","0,00","0,00","0,00","0,00"\n')
ZONA_ABR = ZONA.replace("01/05/2026", "01/04/2026")
CAMPOS = ("﻿CODIGO_CAMPO,CAMPO,SIGLA_CAMPO,BACIA,ESTADO,OPERADOR,AMBIENTE,RODADA,NOME_CONTRATO,NUMERO_CONTRATO,"
          "SITUACAO_CAMPO,DATA_ASSINATURA,TERMINO_FASE,DATA_INICIO_PRODUCAO,DATA_TERMINO_PRODUCAO\n"
          "999,CAMPO TESTE,CT,Potiguar,Rio Grande do Norte,OPERADORA X,Terra,BID0,CT,480000000000000,Produção,06/08/1998,"
          "31/12/2044,31/01/1983,2044\n"
          "998,CAMPO MAR,CM,Campos,Rio de Janeiro,OPERADORA Y,Mar,BID0,CM,480000000000001,Produção,06/08/1998,"
          "31/12/2044,01/01/2020,2044\n")
VERTICES = ("﻿CODIGO_CAMPO,CAMPO,BACIA,AMBIENTE,OPERADOR,NUM_VERTICE,LATITUDE,LONGITUDE\n"
            '999,CAMPO TESTE,Potiguar,TERRA,OP,2,"-05:00:00,000","-36:57:00,000"\n'
            '999,CAMPO TESTE,Potiguar,TERRA,OP,1,"-05:00:00,000","-37:00:00,000"\n'
            '999,CAMPO TESTE,Potiguar,TERRA,OP,3,"-05:03:00,000","-36:57:00,000"\n'
            '1,OUTRO,Potiguar,TERRA,OP,1,"-04:00:00,000","-36:00:00,000"\n')


def pagina_producao(com_mar=True) -> str:
    links = [("1983", URL_PT_ANTIGO), ("2015 - 2º semestre", URL_PT_SEM), ("2026 - 2º trimestre", URL_PT_NOVO),
             ("Maio", URL_ZONA), ("Abril", URL_ZONA_2), ("Metadados", NAC + "metadados-terra.docx")]
    if com_mar:
        links.append(("2026", URL_PM))
    rel = lambda u: u.replace("https://www.gov.br", "")      # a página usa caminhos absolutos sem domínio
    return "<html><body>" + "".join(f'<a href="{rel(u)}">{t}</a>' for t, u in links) + "</body></html>"


PAGINA_PD = ('<a href="https://www.gov.br/anp/x/pd/abalone.pdf">Abalone</a>'
             f'<a href="{URL_PD}">Campo Teste</a>')


def pdf_pd() -> bytes:
    """Um sumário de PD no leiaute da ANP (rótulo numa linha, valor na seguinte)."""
    import fitz
    doc = fitz.open()
    pg = doc.new_page()
    linhas = ["Campo Teste 2023", "Plano de Desenvolvimento Aprovado",
              "Resolução de Diretoria (RD) nº 0030/2023, de 26/01/2023", "Nº do Contrato:", "48000.003800/97-51",
              "Operador do Contrato:", "Operadora X", "Estado:", "Rio Grande do Norte", "Bacia:", "Potiguar",
              "Fluido Principal:", "Óleo", "Área:", "70,17 km²", "Situação:", "Em produção", "Descoberta:", "12/1982",
              "Início de Produção:", "01/1983", "Término da Produção:", "2044 (Prorrogação contratual)",
              "Geologia da Área e Reservatórios: Arenitos fluviais da Formação Açu,",
              "porosidade em torno de 24%.", "Fonte: BAR/2021", "Poços:", "12/2022", "Perfurados:", "148",
              "Produtores:", "77", "Injetores:", "5", "Volume “in place”", "31/12/2021", "Óleo (milhões de m³)", "13,80",
              "Gás Total (milhões de m³)", "596,38", "Produção Acumulada:", "31/12/2021", "Óleo (milhões de m³)", "1,40",
              "Gás Total (milhões de m³):", "251,72"]
    y = 40
    for linha in linhas:
        pg.insert_text((40, y), linha, fontsize=9, fontname="helv")
        y += 16
    return doc.tobytes()


# ------------------------------------------------------------------ shapefile sintético
def _dbf(campos: list[tuple[str, str, int]], registros: list[dict], ldid: int = 0x57, enc="cp1252") -> bytes:
    hl = 32 + 32 * len(campos) + 1
    rl = 1 + sum(t for _, _, t in campos)
    out = bytearray(struct.pack("<BBBBIHH20x", 3, 126, 1, 1, len(registros), hl, rl))
    out[29] = ldid
    for nome, tipo, tam in campos:
        out += struct.pack("<11sc4xBB14x", nome.encode("latin1"), tipo.encode(), tam, 0)
    out += b"\r"
    for r in registros:
        out += b" "
        for nome, tipo, tam in campos:
            v = r.get(nome, "")
            s = (f"{v:>{tam}}" if tipo == "N" else f"{v:<{tam}}").encode(enc)[:tam]
            out += s.ljust(tam)
    out += b"\x1a"
    return bytes(out)


def _shp(tipo: int, geometrias: list) -> bytes:
    recs = bytearray()
    for k, g in enumerate(geometrias, 1):
        if tipo == 1:
            corpo = struct.pack("<i2d", 1, *g)
        else:
            partes = g
            pts = [p for parte in partes for p in parte]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            corpo = struct.pack("<i4d2i", tipo, min(xs), min(ys), max(xs), max(ys), len(partes), len(pts))
            i = 0
            for parte in partes:
                corpo += struct.pack("<i", i)
                i += len(parte)
            for x, y in pts:
                corpo += struct.pack("<2d", x, y)
        recs += struct.pack(">2i", k, len(corpo) // 2) + corpo
    cab = struct.pack(">7i", 9994, 0, 0, 0, 0, 0, (100 + len(recs)) // 2) + struct.pack("<2i4d4d", 1000, tipo, 0, 0, 0, 0, 0, 0, 0, 0)
    return cab + bytes(recs)


def shapefile_campos() -> dict[str, bytes]:
    externo = [(-37.0, -5.0), (-36.95, -5.0), (-36.95, -5.05), (-37.0, -5.05), (-37.0, -5.0)]     # horário
    buraco = [(-36.99, -5.01), (-36.99, -5.02), (-36.98, -5.02), (-36.98, -5.01), (-36.99, -5.01)]  # anti-horário
    return {"CAMPOS.shp": _shp(5, [[externo, buraco]]), "CAMPOS.shx": b"",
            "CAMPOS.dbf": _dbf([("NOM_CAMPO", "C", 32), ("AREA", "N", 10)], [{"NOM_CAMPO": "CAMPO TESTE", "AREA": 70}]),
            "CAMPOS.prj": b'GEOGCS["SIRGAS 2000"]'}


def shapefile_dutos() -> dict[str, bytes]:
    return {"dut_trecho_duto_l.shp": _shp(3, [[[(-37.0, -5.0), (-36.5, -5.1)]], [[(-36.0, -5.0), (-35.9, -5.0)], [(-35.8, -5.0), (-35.7, -5.1)]]]),
            "dut_trecho_duto_l.dbf": _dbf([("nome", "C", 40), ("mattransp", "C", 20)],
                                          [{"nome": "Gasoduto Nordestão", "mattransp": "Gás"},
                                           {"nome": "Oleoduto", "mattransp": "Petróleo"}], ldid=0, enc="utf-8"),
            "dut_trecho_duto_l.cpg": b"UTF-8", "dut_trecho_duto_l.prj": b'GEOGCS["SIRGAS 2000"]',
            "dut_trecho_duto_l.shx": b""}


def zipar(arquivos: dict[str, bytes], prefixo: str = "") -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in arquivos.items():
            z.writestr(prefixo + n, d)
    return b.getvalue()


# ------------------------------------------------------------------ sessão falsa
class Resposta:
    def __init__(self, status=200, conteudo=b"", headers=None):
        self.status_code, self.content, self.headers = status, conteudo, headers or {}

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content)

    def iter_content(self, n):
        for i in range(0, len(self.content), n):
            yield self.content[i:i + n]


class SessaoFalsa:
    """Responde como os servidores reais: ANP (páginas, CSV, PDF, zip), IBGE (Range), EPE (páginas)."""

    def __init__(self, com_mar=True):
        self.pedidos: list[str] = []
        bc = mca.IBGE_BC250 + "versao2025/shapefiles/bc_250_shapefiles_2026_03_03.zip"
        self.zip_ibge_url = bc
        self.arquivos = {
            mpr.PAGINA_PRODUCAO: pagina_producao(com_mar).encode(), mpr.PAGINA_PD: PAGINA_PD.encode(),
            mpr.URL_CAMPOS: CAMPOS.encode("utf-8"), mpr.URL_VERTICES: VERTICES.encode("utf-8"),
            URL_PT_ANTIGO: PT_ANTIGO.encode("utf-8"), URL_PT_SEM: PT_SEM.encode("utf-8"),
            URL_PT_NOVO: PT_NOVO.encode("utf-8"), URL_PM: PT_NOVO.replace("CAMPO TESTE", "CAMPO MAR").encode("utf-8"),
            URL_ZONA: ZONA.encode("utf-8"), URL_ZONA_2: ZONA_ABR.encode("utf-8"), URL_PD: pdf_pd(),
            mca.ANP_GEO + "campos-producao.zip": zipar(shapefile_campos()),
            mca.ANP_GEO + "blocos-exploratorios.zip": b"isto nao e um zip",
            mca.IBGE_BC250: b'<a href="versao2023/">versao2023/</a><a href="versao2025/">versao2025/</a>',
            mca.IBGE_BC250 + "versao2025/shapefiles/": b'<a href="bc_250_shapefiles_2026_03_03.zip">zip</a>',
            bc: zipar({**shapefile_dutos(), "lml_cidade_p.dbf": b"x" * 5000}, prefixo="bc250/"),
        }
        self.epe = {55: [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-37, -5], [-36.9, -5.1]]},
                          "properties": {"Nome_Dut_1": f"Trecho {i}", "Diam_Pol_x": "14", "OBJECTID": i,
                                         "Shape.STLength()": 0.1}} for i in range(1500)]}

    def _get(self, url, params=None, headers=None):
        if url.startswith(mca.EPE_SERVICO):
            camada = int(url[len(mca.EPE_SERVICO):].split("/")[0])
            feats = self.epe.get(camada, [])
            ini, n = int(params["resultOffset"]), int(params["resultRecordCount"])
            lote = feats[ini:ini + n]
            corpo = {"type": "FeatureCollection", "features": lote}
            if ini + n < len(feats):
                corpo["properties"] = {"exceededTransferLimit": True}
            return Resposta(200, json.dumps(corpo).encode())
        if url not in self.arquivos:
            return Resposta(404, b"nao achado")
        dados = self.arquivos[url]
        rng = (headers or {}).get("Range")
        if rng:
            a, b = (int(x) for x in rng.split("=")[1].split("-"))
            return Resposta(206, dados[a:b + 1])
        return Resposta(200, dados)

    def get(self, url, timeout=None, headers=None, stream=False, params=None):
        self.pedidos.append(url + ("?" + urlencode(params) if params else "") + (f" [{headers.get('Range')}]" if headers and headers.get("Range") else ""))
        return self._get(url, params, headers)

    def head(self, url, timeout=None, headers=None, allow_redirects=True):
        self.pedidos.append("HEAD " + url)
        if url not in self.arquivos:
            return Resposta(404)
        return Resposta(200, b"", {"content-length": str(len(self.arquivos[url]))})
