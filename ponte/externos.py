"""Dados de fora do REATE: produção da ANP por campo e camadas geográficas (IBGE, EPE, ANP)."""

from __future__ import annotations

import csv
import os
from datetime import date

from motor import camadas as mca
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
    @resposta_segura
    def viabilidade_relatorio(self, campo: str):
        self._exigir_projeto()
        campo = (campo or "").strip()
        if not campo:
            raise ErroUsuario("Escolha o campo.")
        try:
            rel = mvi.relatorio(self._banco, self._projeto.pasta, campo)
        except mvi.ErroViabilidade as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("mediu_distancias", campo=campo,
                                camadas=sum(1 for d in rel["distancias"] if d.get("distancia_km") is not None))
        return {"relatorio": rel}

    @resposta_segura
    def viabilidade_csv(self, campo: str):
        self._exigir_projeto()
        try:
            rel = mvi.relatorio(self._banco, self._projeto.pasta, (campo or "").strip())
        except mvi.ErroViabilidade as e:
            raise ErroUsuario(str(e)) from e
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
