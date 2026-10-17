"""Ponte: bloco 3D dos poços e das superfícies de topo (aba Bloco 3D)."""

from __future__ import annotations

import base64
import csv
import os
import re
from datetime import datetime

from motor import agp as magp
from motor import bloco as mbl
from motor import bloco_figura as mbf
from motor import bloco_eclipse as mbe
from motor import bloco_glb as mbg
from motor import bloco_mapas as mbm
from motor import bloco_solido as mbs
from motor import bloco_validacao as mbv
from motor import bloco_volumetria as mbvol
from motor import direcionais as mdi
from motor import interpolacao as mint
from motor import reate
from motor import secao as msc

from .base import PASTA_RECURSOS, ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

CAMINHO_ESTRATIGRAFIA = os.path.join(PASTA_RECURSOS, "estratigrafia.json")
PASTA_EXPORTACAO = os.path.join("exportacoes", "blocos")
MAX_PNG = 40 * 1024 * 1024


class BlocoAPI:
    def _num(self, v, padrao=None):
        if v in (None, ""):
            return padrao
        try:
            return float(str(v).replace(",", "."))
        except ValueError as e:
            raise ErroUsuario(f"Valor inválido: {v}") from e

    def _ident_bloco(self, ident: str) -> str:
        if not ident or not ident.startswith("bloco_") or "/" in ident or "\\" in ident or ".." in ident:
            raise ErroUsuario("Bloco inválido.")
        return ident

    @resposta_segura
    def bloco_opcoes(self):
        """Bacias, campos e poços com topos no AGP (para escolher os poços do bloco)."""
        self._exigir_projeto()
        pocos = mbl.pocos_disponiveis(self._banco)
        with self._banco.conexao() as c:
            bacias = [r[0] for r in c.execute(
                "SELECT bacia, count(DISTINCT poco_id) FROM agp_unidades WHERE tip = 'L' AND topo IS NOT NULL "
                "GROUP BY bacia ORDER BY 2 DESC")]
        return {"bacias": bacias, "campos": mbl.campos(self._banco),
                "pocos": [{"id": p["id"], "campo": p["campo"], "n_unidades": p["n_unidades"]} for p in pocos],
                "total": len(pocos), "interpolacao": self._info_interpolacao()}

    @staticmethod
    def _info_interpolacao() -> dict:
        """Textos e pontos de partida da interpolação (uma fonte só: motor/interpolacao.py)."""
        return {"metodos": mint.INFO, "parametros": mint.PARAMETROS_INFO, "escalas": mint.ESCALAS,
                "padrao": mint.PADRAO, "min_krigagem": mint.MIN_KRIGAGEM}

    @resposta_segura
    def bloco_selecionar(self, modo: str, campo: str = "", poco: str = "", raio_km=5.0, bacia: str = ""):
        self._exigir_projeto()
        try:
            ids = mbl.selecionar(self._banco, modo=modo, campo=campo or "",
                                 poco=self._id_poco(poco) if poco else "",
                                 raio_km=self._num(raio_km, 5.0), bacia=bacia or None)
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        return {"pocos": ids, "isolado": modo == "campo"}

    @resposta_segura
    def bloco_ler_direcionais(self, pocos: list):
        """Baixa e lê os dados direcionais dos poços (só os que faltam; ~5 KB cada)."""
        self._exigir_projeto()
        ids = [self._id_poco(p) for p in pocos if str(p).strip()]
        with self._banco.conexao() as c:
            bacias = [r[0] for r in c.execute("SELECT DISTINCT bacia FROM acervo_pocos")]
        lidos = 0
        for bacia in bacias:
            fila = mdi.pendentes(self._banco, bacia, pocos=ids)
            if fila:
                lidos += mdi.ler_do_portal(
                    self._banco, reate.ClienteREATE.da_bacia(bacia), bacia, fila, pasta_projeto=self._projeto.pasta,
                    progresso=lambda k, n, nome: self._status(f"Dados direcionais {k} de {n}: {nome}"))
        com = sum(1 for p in ids if mdi.do_poco(self._banco, p))
        self._projeto.registrar("leu_direcionais", pocos=len(ids), arquivos=lidos)
        return {"lidos": lidos, "com_trajetoria": com}

    @resposta_segura
    def bloco_montar(self, pocos: list, opcoes: dict | None = None):
        self._exigir_projeto()
        op = opcoes or {}
        ids = [self._id_poco(p) for p in pocos if str(p).strip()]
        try:
            modelo = mbl.montar(
                self._banco, ids, nivel=op.get("nivel", "formacoes"), margem_km=self._num(op.get("margem"), 0.0),
                celulas=int(self._num(op.get("celulas"), mbl.CELULAS_PADRAO)),
                dist_max_km=self._num(op.get("dist_max")),
                nomes=magp.ler_estratigrafia(CAMINHO_ESTRATIGRAFIA), slots=msc.ler_slots(CAMINHO_ESTRATIGRAFIA),
                pasta_execucoes=self._projeto.pasta_de("execucoes"), base_cota=self._num(op.get("base")),
                interpolacao=op.get("interpolacao") or None,
                escala=op.get("escala") if op.get("escala") in mint.ESCALAS else None)
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        modelo["titulo"] = (op.get("titulo") or "").strip()
        ident, _ = mbl.registrar(self._projeto.pasta_de("execucoes"), modelo, autor=self._autor())
        self._projeto.registrar("montou_bloco", execucao=ident, pocos=len(modelo["pocos"]),
                                area_km2=modelo["area_km2"], parametros=modelo["parametros"])
        return {"id": ident, "modelo": modelo, "autor": self._autor()}

    @resposta_segura
    def bloco_execucoes(self):
        self._exigir_projeto()
        return {"execucoes": mbl.execucoes(self._projeto.pasta_de("execucoes"))[:20]}

    @resposta_segura
    def bloco_abrir(self, ident: str):
        """Um bloco já montado (do histórico), sem recalcular."""
        self._exigir_projeto()
        try:
            reg = mbl.abrir(self._projeto.pasta_de("execucoes"), self._ident_bloco(ident))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        return {"id": ident, "modelo": reg, "autor": reg.get("autor", "")}

    @resposta_segura
    def bloco_exportar_csv(self, ident: str):
        self._exigir_projeto()
        try:
            reg = mbl.abrir(self._projeto.pasta_de("execucoes"), self._ident_bloco(ident))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        arquivos = mbl.exportar_csv(reg, os.path.join(self._projeto.pasta, PASTA_EXPORTACAO), ident)
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="csv")
        return {"arquivos": [os.path.relpath(a, self._projeto.pasta).replace(os.sep, "/") for a in arquivos]}

    # ------------------------------------------------ validação cruzada e prognóstico
    def _registro_bloco(self, ident: str) -> dict:
        try:
            return mbl.abrir(self._projeto.pasta_de("execucoes"), self._ident_bloco(ident))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e

    def _empilhamento(self, ident: str, reg: dict):
        """O bloco fechado por ponto (guardado: refazer as triangulações custa ~2 s no regional)."""
        cache = getattr(self, "_cache_empilhamento", None)
        if cache is None:
            cache = self._cache_empilhamento = {}
        if ident not in cache:
            if len(cache) > 4:
                cache.clear()
            cache[ident] = mbv.Empilhamento(reg)
        return cache[ident]

    @resposta_segura
    def bloco_validar(self, ident: str):
        """Validação cruzada (deixar um poço de fora); guardada no registro do bloco."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        try:
            val = mbv.validar(reg)
        except mbv.ErroValidacao as e:
            raise ErroUsuario(str(e)) from e
        mbl.atualizar(self._projeto.pasta_de("execucoes"), ident, validacao=val)
        self._projeto.registrar("validou_bloco", execucao=ident, comparacoes=val["n_comparacoes"],
                                mediana_fechado=val["global"]["fechado"].get("mediana"),
                                mediana_superficie=val["global"]["superficie"].get("mediana"))
        return {"validacao": val}

    @resposta_segura
    def bloco_comparar(self, ident: str, parametros: dict | None = None):
        """Validação cruzada com cada método de interpolação; guardada no registro do bloco."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        if parametros is None:      # os parâmetros avançados do bloco (variograma, IDW…); a suavidade fica automática
            est = ((reg.get("parametros") or {}).get("interpolacao") or {}).get("estrutura") or {}
            parametros = {k: est[k] for k in ("potencia", "vizinhos", "modelo", "alcance_km", "azimute", "razao", "grau")
                          if est.get(k) is not None}
        try:
            cmp = mbv.comparar(reg, parametros=parametros or None,
                               progresso=lambda k, n, nome: self._status(f"Comparando os métodos: {k + 1} de {n} — {nome}…"))
        except (mbv.ErroValidacao, mint.ErroInterpolacao) as e:
            raise ErroUsuario(str(e)) from e
        mbl.atualizar(self._projeto.pasta_de("execucoes"), ident, comparacao=cmp)
        m = next(c for c in cmp["candidatos"] if c["id"] == cmp["melhor"])
        self._projeto.registrar("comparou_metodos", execucao=ident, melhor=cmp["melhor"],
                                mediana=m["global"][cmp["criterio"]].get("mediana"))
        return {"comparacao": cmp}

    @resposta_segura
    def bloco_exportar_comparacao(self, ident: str, formato: str = "csv"):
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        cmp = reg.get("comparacao")
        if not cmp:
            raise ErroUsuario("Compare os métodos deste bloco primeiro.")
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        if formato == "csv":
            saida = os.path.join(pasta, f"{ident}_metodos.csv")
            with open(saida, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(mbv.COLUNAS_CSV_COMPARACAO)
                for linha in mbv.linhas_csv_comparacao(cmp):
                    w.writerow(["" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v
                                for v in linha])
        elif formato in ("svg", "pdf", "png"):
            from motor import __version__
            svg = mbv.figura_comparacao(cmp, titulo=(reg.get("titulo") or "").strip() or "Comparação dos métodos de interpolação",
                                        autor=self._autor(), data=datetime.now().strftime("%d/%m/%Y"), versao=__version__)
            saida = mbf.exportar(svg, os.path.join(pasta, f"{ident}_metodos.{formato}"), formato)
        else:
            raise ErroUsuario(f"Formato desconhecido: {formato}")
        self._projeto.registrar("exportou_bloco", execucao=ident, formato=f"metodos_{formato}")
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    def _ponto(self, reg: dict, ponto: dict) -> tuple[float, float]:
        if ponto.get("x") is not None and ponto.get("y") is not None:
            return float(ponto["x"]), float(ponto["y"])
        nums = re.findall(r"-?\d+(?:[.,]\d+)?", str(ponto.get("latlon") or ""))
        if len(nums) != 2:
            raise ErroUsuario("Escreva a latitude e a longitude em graus decimais, ex.: -5,02; -36,98")
        lat, lon = (float(v.replace(",", ".")) for v in nums)
        if not (-35 <= lat <= 6 and -75 <= lon <= -30):
            raise ErroUsuario(f"Coordenada fora do Brasil: {lat}, {lon} (latitude primeiro, depois longitude).")
        x, y, _, _ = mbl.plano([lat], [lon], reg["origem"]["lat"], reg["origem"]["lon"])
        return float(x[0]), float(y[0])

    @resposta_segura
    def bloco_prognostico(self, ident: str, ponto: dict):
        """Coluna prevista num ponto ({x, y} em km do bloco, ou {latlon: "lat, lon"})."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        x, y = self._ponto(reg, ponto or {})
        try:
            return mbv.prognostico(reg, x, y, reg.get("validacao"), self._empilhamento(ident, reg))
        except mbv.ErroValidacao as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def bloco_exportar_validacao(self, ident: str, formato: str = "csv"):
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        val = reg.get("validacao")
        if not val:
            raise ErroUsuario("Rode a validação deste bloco primeiro.")
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        if formato == "csv":
            saida = os.path.join(pasta, f"{ident}_validacao.csv")
            with open(saida, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(mbv.COLUNAS_CSV)
                for linha in mbv.linhas_csv(val):
                    w.writerow(["" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v
                                for v in linha])
        elif formato in ("svg", "pdf", "png"):
            from motor import __version__
            svg = mbv.figura(val, titulo=(reg.get("titulo") or "").strip() or "Validação cruzada do bloco",
                             autor=self._autor(), data=datetime.now().strftime("%d/%m/%Y"), versao=__version__)
            saida = mbf.exportar(svg, os.path.join(pasta, f"{ident}_validacao.{formato}"), formato)
        else:
            raise ErroUsuario(f"Formato desconhecido: {formato}")
        self._projeto.registrar("exportou_bloco", execucao=ident, formato=f"validacao_{formato}")
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    @resposta_segura
    def bloco_exportar_prognostico(self, ident: str, ponto: dict):
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        x, y = self._ponto(reg, ponto or {})
        try:
            p = mbv.prognostico(reg, x, y, reg.get("validacao"), self._empilhamento(ident, reg))
        except mbv.ErroValidacao as e:
            raise ErroUsuario(str(e)) from e
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        nome = f"{ident}_prognostico_{p['lat']:.4f}_{p['lon']:.4f}.csv".replace("-", "m")
        saida = os.path.join(pasta, nome)

        def n(v, c=1):
            return "" if v is None else f"{v:.{c}f}".replace(".", ",")
        with open(saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["# prognóstico do bloco", ident, "lat", n(p["lat"], 6), "lon", n(p["lon"], 6),
                        "terreno_m", n(p["terreno"])])
            w.writerow(["camada", "cota_topo_m", "prof_topo_abaixo_terreno_m", "cota_base_m", "espessura_m",
                        "incerteza_topo_m", "interpolado", "dist_poco_mais_proximo_km", "fonte_incerteza"])
            for c in p["camadas"]:
                w.writerow([c["nome"], n(c["topo"]), n(c["prof_topo"]), n(c["base"]), n(c["espessura"]),
                            n(c["incerteza_m"]), "sim" if c["interpolado"] else "não", n(c["dist_km"], 3),
                            c["incerteza_fonte"]])
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="prognostico_csv",
                                lat=p["lat"], lon=p["lon"])
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/"), "prognostico": p}

    # ------------------------------------------------ saídas: mapas, simulador, volumetria, 3D
    def _rel(self, caminho: str) -> str:
        return os.path.relpath(caminho, self._projeto.pasta).replace(os.sep, "/")

    @resposta_segura
    def bloco_exportar_mapas(self, ident: str, passo_m=None):
        """GeoTIFF + XYZ em SIRGAS 2000 / UTM: terreno, topo e isópaca de cada camada."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        try:
            r = mbm.exportar(reg, os.path.join(self._projeto.pasta, PASTA_EXPORTACAO), ident, self._num(passo_m))
        except mbm.ErroMapa as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="mapas", epsg=r["epsg"], passo_m=r["passo_m"])
        return {"pasta": self._rel(r["pasta"]), "mapas": r["mapas"], "epsg": r["epsg"], "passo_m": r["passo_m"],
                "nx": r["nx"], "ny": r["ny"]}

    def _opcoes_eclipse(self, op: dict) -> dict:
        nz = self._num(op.get("nz"))
        return {"camadas": op.get("camadas"), "nz": int(nz) if nz else None, "dx_m": self._num(op.get("dx")),
                "max_celulas": int(self._num(op.get("max_celulas"), mbe.MAX_CELULAS_PADRAO))}

    @resposta_segura
    def bloco_eclipse_previa(self, ident: str, opcoes: dict | None = None):
        """Formações (com as do padrão marcadas) e o tamanho da grade que sairia."""
        self._exigir_projeto()
        reg = self._registro_bloco(self._ident_bloco(ident))
        sol = reg.get("solido") or {}
        if not sol.get("ok"):
            raise ErroUsuario("O deck sai do bloco fechado, que este bloco não tem.")
        op = self._opcoes_eclipse(opcoes or {})
        todas = [c for c in sol["camadas"] if c["chave"] not in (mbs.CHAVE_COBERTURA, mbs.CHAVE_ABAIXO)]
        try:
            p = mbe.planejar(reg, **op)
        except mbe.ErroEclipse as e:
            return {"erro": str(e), "camadas": [{"chave": c["chave"], "nome": c["nome"]} for c in todas]}
        escolhidas = {c["chave"] for c in p["camadas"]}
        return {"camadas": [{"chave": c["chave"], "nome": c["nome"], "marcada": c["chave"] in escolhidas,
                             "nk": dict(zip([q["chave"] for q in p["camadas"]], p["nk"])).get(c["chave"], 0)}
                            for c in todas],
                "nx": p["nx"], "ny": p["ny"], "nz": p["nz"], "dx": p["dx"], "celulas": p["celulas"],
                "max_celulas": p["max_celulas"], "epsg": p["epsg"]}

    @resposta_segura
    def bloco_exportar_eclipse(self, ident: str, opcoes: dict | None = None):
        """Deck ECLIPSE (.DATA + .GRDECL + .inc) do bloco fechado."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        try:
            r = mbe.exportar(reg, os.path.join(self._projeto.pasta, PASTA_EXPORTACAO), ident,
                             titulo=(reg.get("titulo") or "").strip(), **self._opcoes_eclipse(opcoes or {}))
        except mbe.ErroEclipse as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="eclipse", celulas=r["celulas"],
                                ativas=r["ativas"], camadas=[c["chave"] for c in r["camadas"]])
        return {"pasta": self._rel(r["pasta"]), "deck": r["deck"], "nx": r["nx"], "ny": r["ny"], "nz": r["nz"],
                "dx": r["dx"], "celulas": r["celulas"], "ativas": r["ativas"], "pocos": r["pocos"],
                "camadas": r["camadas"], "notas": r["notas"], "epsg": r["epsg"]}

    @resposta_segura
    def bloco_volumetria(self, ident: str, informados: dict | None = None, co2: dict | None = None):
        self._exigir_projeto()
        reg = self._registro_bloco(self._ident_bloco(ident))
        try:
            return mbvol.calcular(reg, informados, co2)
        except mbvol.ErroVolumetria as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def bloco_exportar_volumetria(self, ident: str, informados: dict | None = None, co2: dict | None = None):
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        try:
            v = mbvol.calcular(reg, informados, co2)
        except mbvol.ErroVolumetria as e:
            raise ErroUsuario(str(e)) from e
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, f"{ident}_volumetria.csv")
        with open(saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(mbvol.COLUNAS_CSV)
            for linha in mbvol.linhas_csv(v):
                w.writerow(["" if x is None else (f"{x:.6g}".replace(".", ",") if isinstance(x, float) else x)
                            for x in linha])
            w.writerow([])
            for n_ in v["notas"]:
                w.writerow([n_])
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="volumetria")
        return {"arquivo": self._rel(saida), "volumetria": v}

    @resposta_segura
    def bloco_exportar_glb(self, ident: str, vista: dict | None = None):
        """Modelo 3D (.glb) do bloco fechado, com o exagero e as camadas da tela."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        reg = self._registro_bloco(ident)
        vi = vista or {}
        saida = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO, f"{ident}.glb")
        try:
            r = mbg.exportar(reg, saida, exagero=float(vi.get("exagero") or 10), camadas=vi.get("camadas"),
                             pocos=vi.get("pocos", True) is not False, titulo=(reg.get("titulo") or "").strip())
        except ValueError as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="glb", triangulos=r["triangulos"])
        return {"arquivo": self._rel(saida), "triangulos": r["triangulos"], "bytes": r["bytes"]}

    @resposta_segura
    def bloco_figura(self, ident: str, vista: dict | None = None, formato: str = "pdf"):
        """Figura estática no estilo artigo da vista atual (svg | pdf | png 300 ppp)."""
        self._exigir_projeto()
        if formato not in ("svg", "pdf", "png"):
            raise ErroUsuario(f"Formato desconhecido: {formato}")
        try:
            reg = mbl.abrir(self._projeto.pasta_de("execucoes"), self._ident_bloco(ident))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        vi = vista or {}
        dr = vi.get("drape") or None
        try:
            svg = mbf.desenhar(
                reg, azimute=float(vi.get("azimute", -0.61)), elevacao=float(vi.get("elevacao", 0.61)),
                exagero=float(vi.get("exagero", 10)), visiveis=vi.get("visiveis"),
                trilha=vi.get("trilha") or "nenhuma",
                drape={"chave": dr.get("chave"), "prop": dr.get("prop")} if dr and dr.get("chave") else None,
                titulo=(vi.get("titulo") or reg.get("titulo") or "").strip(), autor=self._autor(),
                data=datetime.now().strftime("%d/%m/%Y"), nomes=vi.get("nomes", True) is not False,
                opacidade=float(vi.get("opacidade", 0.7)), modo=vi.get("modo") or "superficies",
                camadas=vi.get("camadas"), corte=vi.get("corte") or None, afastar=float(vi.get("afastar") or 0),
                parede=vi.get("parede") or None)
        except mbf.ErroFigura as e:
            raise ErroUsuario(str(e)) from e
        saida = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO, f"{ident}_figura.{formato}")
        mbf.exportar(svg, saida, formato)
        self._projeto.registrar("exportou_bloco", execucao=ident, formato=f"figura_{formato}",
                                vista={k: vi.get(k) for k in ("azimute", "elevacao", "exagero", "trilha", "drape",
                                                                     "modo", "corte", "afastar", "parede")})
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    @resposta_segura
    def bloco_salvar_png(self, ident: str, dados_url: str):
        """Grava a imagem que a janela desenhou (data:image/png;base64,…)."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        prefixo = "data:image/png;base64,"
        if not isinstance(dados_url, str) or not dados_url.startswith(prefixo) or len(dados_url) > MAX_PNG:
            raise ErroUsuario("Imagem inválida.")
        dados = base64.b64decode(dados_url[len(prefixo):])
        if not dados.startswith(b"\x89PNG"):
            raise ErroUsuario("Imagem inválida.")
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, f"{ident}.png")
        with open(saida + ".tmp", "wb") as f:
            f.write(dados)
        os.replace(saida + ".tmp", saida)
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="png")
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    @resposta_segura
    def abrir_pasta_blocos(self):
        self._exigir_projeto()
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        _abrir_no_sistema(pasta)
        return {}
