"""Dados de fora do REATE: produção da ANP por campo e camadas geográficas (IBGE, EPE, ANP)."""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime

from motor import camadas as mca
from motor import documentos as mdoc
from motor import economia as mec
from motor import fluidos as mfl
from motor import indices as mix
from motor import producao as mpr
from motor import viabilidade as mvi

from .base import ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

PASTA_EXPORTACAO = os.path.join("exportacoes", "producao")


class ExternosAPI:
    # ------------------------------------------------------------ produção da ANP
    def _cancelar_externos(self) -> bool:
        return bool(getattr(self, "_cancela_externos", False))

    @resposta_segura
    def producao_cancelar(self):
        self._cancela_externos = True
        return {}

    @resposta_segura
    def producao_baixar(self, campo: str, periodo: str = "5", zona: bool = True):
        """Produção do campo pela ANP. periodo: "tudo", ou quantos anos para trás ("1", "5", "10"),
        ou "AAAA-AAAA"."""
        self._exigir_projeto()
        campo = (campo or "").strip()
        if not campo:
            raise ErroUsuario("Escolha o campo.")
        hoje = date.today().year
        ano_ini = ano_fim = None
        p = str(periodo or "5").strip()
        if p != "tudo":
            if "-" in p:
                try:
                    ano_ini, ano_fim = (int(x) for x in p.split("-", 1))
                except ValueError as e:
                    raise ErroUsuario("Período: escreva AAAA-AAAA, ex.: 2010-2020.") from e
            else:
                try:
                    ano_ini = hoje - max(1, int(p)) + 1
                except ValueError as e:
                    raise ErroUsuario("Período inválido.") from e
        self._cancela_externos = False
        try:
            feito = mpr.baixar(self._banco, self._projeto.pasta, campo, ano_ini=ano_ini, ano_fim=ano_fim,
                               zona=bool(zona), progresso=self._status, cancelar=self._cancelar_externos)
        except mpr.Cancelado:
            raise ErroUsuario("Download da produção cancelado (o que já veio ficou guardado).") from None
        except mpr.ErroProducao as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("baixou_producao", **{k: v for k, v in feito.items() if k != "avisos"})
        return {"feito": feito, "resumo": mpr.resumo(self._banco, campo)}

    @resposta_segura
    def producao_campos(self):
        """Campos do cadastro da ANP (para escolher qual produção baixar)."""
        self._exigir_projeto()
        with self._banco.conexao() as c:
            campos = [r[0] for r in c.execute(
                "SELECT campo FROM pocos WHERE campo IS NOT NULL AND campo <> '' GROUP BY campo ORDER BY campo")]
            guardados = [r[0] for r in c.execute("SELECT nome FROM campos_anp ORDER BY nome")]
        return {"campos": campos, "guardados": guardados}

    @resposta_segura
    def producao_resumo(self, campo: str):
        self._exigir_projeto()
        return {"resumo": mpr.resumo(self._banco, campo or "")}

    @resposta_segura
    def producao_exportar_csv(self, campo: str):
        self._exigir_projeto()
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        nome = mpr.chave_campo(campo).replace(" ", "_").lower()
        if not nome:
            raise ErroUsuario("Escolha o campo.")
        arquivos = []
        for sufixo, (cols, linhas) in (("poco", mpr.linhas_csv(self._banco, campo)),
                                       ("zona", mpr.linhas_csv_zona(self._banco, campo))):
            if not linhas:
                continue
            saida = os.path.join(pasta, f"producao_{nome}_por_{sufixo}.csv")
            with open(saida, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(cols)
                for linha in linhas:
                    w.writerow(["" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v
                                for v in linha])
            arquivos.append(os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/"))
        if not arquivos:
            raise ErroUsuario("Nada guardado deste campo: baixe a produção primeiro.")
        self._projeto.registrar("exportou_producao", campo=campo, arquivos=arquivos)
        return {"arquivos": arquivos}

    # ------------------------------------------------------------ camadas geográficas
    @resposta_segura
    def camadas_catalogo(self):
        pasta = self._projeto.pasta if self._projeto is not None else None
        return {"camadas": mca.catalogo_com_estado(pasta), "fontes": mca.FONTES}

    @resposta_segura
    def camadas_baixar(self, ids: list):
        self._exigir_projeto()
        self._cancela_externos = False
        try:
            r = mca.baixar(self._projeto.pasta, [str(i) for i in ids or []], progresso=self._status,
                           cancelar=self._cancelar_externos)
        except mca.ErroCamadas as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("baixou_camadas", camadas=[f["id"] for f in r["feitos"]],
                                erros=[e["id"] for e in r["erros"]])
        return {**r, "camadas": mca.catalogo_com_estado(self._projeto.pasta)}

    @resposta_segura
    def camadas_importar(self, ident: str = "terras_indigenas"):
        """Escolhe um shapefile (.zip) ou GeoJSON seu e guarda como a camada pedida (ex.: terras indígenas da FUNAI)."""
        self._exigir_projeto()
        import webview
        escolha = self._janela.create_file_dialog(webview.FileDialog.OPEN, directory=self._projeto.pasta,
                                                  file_types=("Shapefile em zip ou GeoJSON (*.zip;*.geojson;*.json)",
                                                              "Todos os arquivos (*.*)"))
        if not escolha:
            return {"cancelado": True}
        caminho = escolha[0] if isinstance(escolha, (list, tuple)) else escolha
        try:
            reg = mca.importar(self._projeto.pasta, str(ident), caminho)
        except mca.ErroCamadas as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("importou_camada", camada=ident, arquivo=os.path.basename(caminho), feicoes=reg["feicoes"])
        return {"camada": reg, "camadas": mca.catalogo_com_estado(self._projeto.pasta)}

    @resposta_segura
    def viabilidade_restricoes(self, campo: str):
        """Áreas protegidas (UCs federais, terras indígenas) que a linha reta do campo até cada infraestrutura cruza."""
        self._exigir_projeto()
        campo = (campo or "").strip()
        if not campo:
            raise ErroUsuario("Escolha o campo.")
        rel = self._relatorio_vb(campo)
        return {"campo": campo, "linhas": mvi.restricoes_do_relatorio(self._projeto.pasta, rel["distancias"]),
                "camadas": [{"id": i, "rotulo": r} for i, r, _ in mvi.CAMADAS_AMBIENTAIS]}

    @resposta_segura
    def abrir_pasta_sig(self):
        self._exigir_projeto()
        _abrir_no_sistema(self._projeto.pasta_de(mca.PASTA_SIG))
        return {}

    @resposta_segura
    def sig_camada(self, ident: str):
        """Uma camada guardada em sig/ (GeoJSON), para desenhar no mapa."""
        self._exigir_projeto()
        reg = mca.indice(self._projeto.pasta)["camadas"].get(str(ident))
        if not reg:
            raise ErroUsuario("Camada não baixada ainda.")
        caminho = os.path.join(self._projeto.pasta, reg["arquivo"])
        import json
        with open(caminho, encoding="utf-8") as f:
            return {"camada": reg, "geojson": json.load(f)}

    # ------------------------------------------------------------ campo × infraestrutura
    def _relatorio_vb(self, campo: str) -> dict:
        """Distâncias do campo (guardadas enquanto o polígono e as camadas não mudam)."""
        try:
            poli, _ = mvi.poligono_campo(self._banco, self._projeto.pasta, campo)
        except mvi.ErroViabilidade as e:
            raise ErroUsuario(str(e)) from e
        caminho = os.path.join(self._projeto.pasta, mca.PASTA_SIG, "camadas.json")
        chave = (mpr.chave_campo(campo), os.path.getmtime(caminho) if os.path.exists(caminho) else 0, str(poli))
        cache = getattr(self, "_cache_vb", None)
        if cache and cache[0] == chave:
            return cache[1]
        rel = mvi.relatorio(self._banco, self._projeto.pasta, campo)
        self._cache_vb = (chave, rel)
        return rel

    def _parametros_guardados(self, campo: str) -> dict:
        return (mpr.campo_guardado(self._banco, campo) or {}).get("viabilidade") or {}

    @resposta_segura
    def viabilidade_relatorio(self, campo: str):
        self._exigir_projeto()
        campo = (campo or "").strip()
        if not campo:
            raise ErroUsuario("Escolha o campo.")
        rel = self._relatorio_vb(campo)
        self._projeto.registrar("mediu_distancias", campo=campo,
                                camadas=sum(1 for d in rel["distancias"] if d.get("distancia_km") is not None))
        return {"relatorio": rel, "parametros": self._parametros_guardados(campo)}

    @resposta_segura
    def viabilidade_opcoes(self):
        """Tudo que a tela precisa para mostrar e editar: referências, constantes (com fonte),
        equações (padrão, alternativas, explicação) e o significado de cada símbolo."""
        return {"fontes_custo": mec.FONTES_CUSTO, "padroes": mec.PADROES,
                "fluidos": [{"id": k, "rotulo": v["rotulo"], "fator": mec.CONSTANTES[f"f_{k}"]["valor"],
                             "motivo": mec.CONSTANTES[f"f_{k}"]["fonte"], "armazenado": v["armazenado"]}
                            for k, v in mec.FLUIDOS.items()],
                "constantes": [{"id": k, **{c: v for c, v in d.items() if c != "faixa"}, "faixa": list(d["faixa"])}
                               for k, d in mec.CONSTANTES.items()],
                "equacoes": [{"id": k, "titulo": d["titulo"], "resultado": d["resultado"], "unidade": d["unidade"],
                              "padrao": d["padrao"], "explicacao": d["explicacao"],
                              "alternativas": [{"nome": n, "formula": f} for n, f in d["alternativas"].items()],
                              "variaveis": sorted(mec.nomes(mec.compilar(d["padrao"])),
                                                  key=lambda n: d["padrao"].find(n))}
                             for k, d in mec.EQUACOES.items()],
                "simbolos": {k: {"descricao": d, "unidade": u} for k, (d, u) in mec.SIMBOLOS.items()},
                "funcoes": ["min", "max", "abs", "sqrt", "exp", "ln", "log10"]}

    def _com_inflacao(self, parametros: dict | None) -> dict:
        """Parâmetros com o fator de correção pela inflação calculado (série oficial do Banco Central)."""
        pr = dict(parametros or {})
        pr.pop("inflacao", None)
        try:
            p0 = mec.parametros(pr)
        except mec.ErroEconomia as e:
            raise ErroUsuario(str(e)) from e
        if p0["corrigir_inflacao"] == "nao":
            pr["fator_inflacao"] = 1.0
            return pr
        ref = next((f for f in mec.FONTES_CUSTO if f["id"] == p0["fonte_custo"]), None)
        data_base = ref["data_base"] if ref else p0["data_base_custo"]
        self._status("Buscando a série de inflação no Banco Central…")
        try:
            info = mix.corrigir(self._projeto.pasta, p0["corrigir_inflacao"], data_base, p0["data_ref"])
        except mix.ErroIndices as e:
            raise ErroUsuario(str(e)) from e
        pr["fator_inflacao"], pr["inflacao"] = info["fator"], info
        return pr

    def _avaliar(self, campo: str, parametros) -> dict:
        self._exigir_projeto()
        parametros = self._com_inflacao(parametros)
        campo = (campo or "").strip()
        if not campo:
            raise ErroUsuario("Escolha o campo.")
        rel = self._relatorio_vb(campo)
        sugeridos = self._resumo_fluidos(campo)["escolha"]
        try:
            av = mec.avaliar(self._banco, campo, rel["distancias"], parametros or {}, sugeridos)
        except mec.ErroEconomia as e:
            raise ErroUsuario(str(e)) from e
        inf = (parametros or {}).get("inflacao") or {}
        av["avisos"] = list(av.get("avisos") or []) + list(inf.get("avisos") or [])
        return av

    @resposta_segura
    def viabilidade_economia(self, campo: str, parametros: dict | None = None):
        """Custo do duto ÷ capacidade de injeção, nos três métodos; guarda os parâmetros do campo."""
        av = self._avaliar(campo, parametros)
        guardar = {k: v for k, v in (parametros or {}).items() if k in mec.PADROES and v not in (None, "")}
        for k in ("constantes", "equacoes"):
            if av["parametros"][k]:
                guardar[k] = av["parametros"][k]
        mpr.guardar_campo(self._banco, campo.strip(), viabilidade=guardar)
        arquivos = mec.salvar_memoria(self._projeto.pasta, av)
        self._projeto.registrar("avaliou_viabilidade", campo=campo.strip(), fluido=av["parametros"]["fluido"],
                                metodos=[k for k, m in av["metodos"].items() if m.get("valor")],
                                memoria=arquivos["json"],
                                equacoes_alteradas=list(av["parametros"]["equacoes"]),
                                constantes_alteradas=list(av["parametros"]["constantes"]))
        return {"avaliacao": av, "memoria": arquivos}

    @resposta_segura
    def viabilidade_abrir_memoria(self, rel: str):
        """Abre no navegador a memória de cálculo (HTML) gravada em execucoes/viabilidade/."""
        self._exigir_projeto()
        base = os.path.realpath(os.path.join(self._projeto.pasta, "execucoes", "viabilidade"))
        caminho = os.path.realpath(os.path.join(self._projeto.pasta, str(rel or "")))
        if not caminho.startswith(base + os.sep) or not os.path.exists(caminho):
            raise ErroUsuario("Memória de cálculo não encontrada.")
        _abrir_no_sistema(caminho)
        return {}

    @resposta_segura
    def viabilidade_economia_csv(self, campo: str, parametros: dict | None = None):
        av = self._avaliar(campo, parametros)
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, f"viabilidade_{mpr.chave_campo(campo).replace(' ', '_').lower()}.csv")
        fmt = lambda v: "" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v  # noqa: E731
        p, c = av["parametros"], av["custo"]
        with open(saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["# campo", campo.strip(), "fluido", mec.FLUIDOS[p["fluido"]]["rotulo"]])
            w.writerow(["# custo do duto (R$/km)", fmt(round(c["r_por_km"], 2)), "referência", c["referencia"],
                        "data-base", c["data_base"] or "", "diâmetro (pol)", fmt(p["diametro_pol"]),
                        "fator do fluido", fmt(c["fator_fluido"]), "fator de traçado", fmt(p["fator_tracado"])])
            w.writerow(["# produção acumulada", av["acumulados"]["fonte"]])
            for m in av["metodos"].values():
                w.writerow(["# capacidade — " + m["rotulo"], fmt(m.get("valor")), m.get("unidade") or "",
                            m.get("formula") or "", ("falta: " + ", ".join(m["falta"])) if m.get("falta") else ""])
            w.writerow(mec.COLUNAS_CSV)
            for linha in mec.linhas_csv(av):
                w.writerow([fmt(v) for v in linha])
            for a in av["avisos"]:
                w.writerow(["# aviso", a])
            w.writerow([])
            w.writerow(["# memória de cálculo"])
            for linha in mec.linhas_csv_memoria(av):
                w.writerow([fmt(v) for v in linha])
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    @resposta_segura
    def viabilidade_csv(self, campo: str):
        self._exigir_projeto()
        rel = self._relatorio_vb((campo or "").strip())
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, f"distancias_{mpr.chave_campo(campo).replace(' ', '_').lower()}.csv")
        with open(saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["# campo", campo, "polígono", rel["fonte_poligono"]])
            w.writerow(mvi.COLUNAS_CSV)
            for linha in mvi.linhas_csv(rel):
                w.writerow(["" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v for v in linha])
            dep = rel["deplecao"]
            if dep:
                w.writerow([])
                w.writerow(["# depleção (sumário do PD)", dep.get("fonte"), dep.get("data_pd")])
                w.writerow(["fluido", "in_place_milhoes_m3", "produzido_pd_milhoes_m3", "fracao_pd",
                            "produzido_depois_milhoes_m3", "ate", "fracao_atual_estimada"])
                for nome in ("oleo", "gas"):
                    d = dep.get(nome)
                    if d:
                        w.writerow([nome] + [("" if d.get(k) is None else str(d.get(k)).replace(".", ","))
                                             for k in ("in_place_milhoes_m3", "produzido_pd_milhoes_m3", "fracao_pd",
                                                       "produzido_depois_milhoes_m3", "ate", "fracao_atual_estimada")])
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    # ------------------------------------------------------------ áreas em lote (blocos × infraestrutura)
    @resposta_segura
    def areas_opcoes(self):
        idx = mca.indice(self._projeto.pasta)["camadas"] if self._projeto is not None else {}
        return {"areas": [{"id": a[0], "rotulo": a[1], "baixada": a[0] in idx} for a in mvi.AREAS],
                "alvos": [{"id": a[0], "rotulo": a[1], "baixada": a[0] in idx} for a in mvi.ALVOS]}

    @resposta_segura
    def areas_distancias(self, ident_areas: str, ident_alvo: str, parametros: dict | None = None):
        """Cada bloco exploratório (ou campo) contra a feição mais próxima da camada escolhida, com o
        custo do duto; a execução fica gravada em execucoes/viabilidade/."""
        self._exigir_projeto()
        self._cancela_externos = False
        parametros = self._com_inflacao(parametros)
        try:
            r = mvi.distancias_areas(self._projeto.pasta, str(ident_areas), str(ident_alvo), progresso=self._status,
                                     cancelar=self._cancelar_externos)
            custos = mec.custos_duto(parametros or {}, [l.get("distancia_km") for l in r["linhas"]])
        except (mvi.ErroViabilidade, mec.ErroEconomia) as e:
            raise ErroUsuario(str(e)) from e
        for l, (L, c) in zip(r["linhas"], custos["linhas"]):
            l["comprimento_km"], l["custo_r"] = L, c
        r.update(custo=custos["custo"], memoria=custos["memoria"], formulas=custos["formulas"],
                 parametros=custos["parametros"], quando=datetime.now().isoformat(timespec="seconds"))
        pasta = os.path.join(self._projeto.pasta, "execucoes", "viabilidade")
        os.makedirs(pasta, exist_ok=True)
        nome = f"{r['quando'].replace(':', '').replace('-', '').replace('T', '-')}_areas_{ident_areas}_{ident_alvo}.json"
        with open(os.path.join(pasta, nome), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1, default=float)
        r["arquivo"] = f"execucoes/viabilidade/{nome}"
        self._ultimo_areas = r
        self._projeto.registrar("mediu_areas", areas=ident_areas, alvo=ident_alvo, n=len(r["linhas"]), memoria=r["arquivo"])
        return {"resultado": r}

    @resposta_segura
    def areas_csv(self):
        self._exigir_projeto()
        r = getattr(self, "_ultimo_areas", None)
        if not r:
            raise ErroUsuario("Meça as áreas primeiro.")
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, f"distancias_{r['areas']}_{r['alvo']}.csv")
        fmt = lambda v: "" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v  # noqa: E731
        attrs = sorted({k for l in r["linhas"] for k in l["atributos"]})
        with open(saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["# áreas", r["rotulo_areas"], r.get("fonte_areas") or ""])
            w.writerow(["# até", r["rotulo_alvo"], r.get("fonte_alvo") or ""])
            w.writerow(["# distância", "geodésica entre os pontos mais próximos (0 = toca ou atravessa a área)"])
            for k, fm in r["formulas"].items():
                w.writerow(["# fórmula", fm])
            for e in r["memoria"]["entradas"]:
                w.writerow(["# entrada", e["simbolo"], fmt(e["valor"]), e["unidade"], e["fonte"]])
            for ps in r["memoria"]["passos"]:
                w.writerow(["# passo", f"{ps['resultado_simbolo']} = {ps['equacao']}", ps["substituida"],
                            fmt(ps["resultado"]), ps["unidade"]])
            w.writerow(["nome", *attrs, "distancia_km", "toca", "comprimento_km", "custo_r", "lat_area", "lon_area",
                        "lat_feicao", "lon_feicao", "feicao"])
            for l in sorted(r["linhas"], key=lambda x: (x.get("distancia_km") is None, x.get("distancia_km") or 0)):
                pa, pf = l.get("ponto_area") or ["", ""], l.get("ponto_feicao") or ["", ""]
                w.writerow([l["nome"], *[fmt(l["atributos"].get(k)) for k in attrs], fmt(l.get("distancia_km")),
                            "sim" if l.get("toca") else "não", fmt(l.get("comprimento_km")), fmt(l.get("custo_r")),
                            fmt(pa[0]), fmt(pa[1]), fmt(pf[0]), fmt(pf[1]),
                            "; ".join(f"{k}={v}" for k, v in (l.get("feicao") or {}).items())])
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    # ------------------------------------------------------------ API e densidade do gás nos documentos
    def _resumo_fluidos(self, campo: str) -> dict:
        indice = getattr(self, "_indice", None)
        caminho = getattr(indice, "caminho", None)
        docs = self._projeto.listar_documentos(mdoc.EXTENSOES)
        return mfl.resumo(self._banco, caminho if caminho and os.path.exists(caminho) else None, campo, docs)

    @resposta_segura
    def fluidos_campo(self, campo: str):
        """O que os documentos dos poços do campo dizem sobre API e densidade do gás."""
        self._exigir_projeto()
        campo = (campo or "").strip()
        if not campo:
            raise ErroUsuario("Escolha o campo.")
        return {"fluidos": self._resumo_fluidos(campo), "grandezas": mfl.GRANDEZAS, "tipo_fato": mfl.TIPO_FATO,
                "nomes": mfl.NOMES_SUGERIDOS}

    @resposta_segura
    def fluido_confirmar(self, campo: str, leitura: dict):
        """Uma leitura automática conferida pelo usuário vira dado transcrito (com a página como fonte)."""
        self._exigir_projeto()
        g = mfl.GRANDEZAS.get(str(leitura.get("grandeza")))
        if not g:
            raise ErroUsuario("Leitura inválida.")
        valor = str(leitura.get("valor")).replace(".", ",")
        fato = self._salvar_fato({"tipo": mfl.TIPO_FATO, "poco": leitura.get("poco"), "nome": g["rotulo"],
                                  "valor": valor, "unidade": g["unidade"], "pagina": int(leitura.get("pagina") or 0) or None,
                                  "observacao": "confirmado de leitura automática: " + str(leitura.get("lido") or "")[:120]},
                                 fonte_rel=leitura.get("doc"))
        return {"fato": fato, "fluidos": self._resumo_fluidos(campo)}

    @resposta_segura
    def fluido_descartar(self, campo: str, chave: str, desfazer: bool = False):
        self._exigir_projeto()
        ficha = mpr.campo_guardado(self._banco, campo) or {}
        lista = [c for c in (ficha.get("fluidos_descartados") or []) if c != chave]
        if not desfazer:
            lista.append(str(chave))
        mpr.guardar_campo(self._banco, campo, fluidos_descartados=lista)
        self._projeto.registrar("descartou_leitura_fluido" if not desfazer else "voltou_leitura_fluido",
                                campo=campo, leitura=chave)
        return {"fluidos": self._resumo_fluidos(campo)}

    @resposta_segura
    def fluido_processar_campo(self, campo: str):
        """Põe na fila de texto/OCR os documentos baixados dos poços do campo que ainda não têm texto."""
        self._exigir_projeto()
        pend = self._resumo_fluidos(campo)["documentos"]["pendentes"]
        if not pend:
            raise ErroUsuario("Nenhum documento pendente dos poços deste campo (baixe as pastas de poço na aba Dados › Catálogo do REATE).")
        r = self.processar_documentos(pend)
        if not r.get("ok", True):
            raise ErroUsuario(r.get("erro") or "Falha ao enfileirar.")
        return {"enfileirados": r.get("enfileirados", len(pend))}
