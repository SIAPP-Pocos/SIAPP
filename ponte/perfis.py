"""Ponte: perfis de poço (DLIS/LIS/LAS) — inventário, gráfico, exportação, intervalo-alvo."""

from __future__ import annotations

import os
from datetime import datetime

from motor import formatos
from motor import perfis as mpf
from motor import pocos as mpo
from motor import projeto as mp

from .base import PASTA_RECURSOS, ErroUsuario, resposta_segura

CAMINHO_FAMILIAS = os.path.join(PASTA_RECURSOS, "mnemonicos.json")


class PerfisAPI:
    _classificador = None

    def _cl(self) -> mpf.Classificador:
        if self._classificador is None:
            self._classificador = mpf.Classificador(mpf.ler_familias(CAMINHO_FAMILIAS))
        return self._classificador

    def _arquivo_perfil(self, rel: str) -> tuple[str, dict]:
        self._exigir_projeto()
        rel = mp.rel_padrao(rel)
        caminho = self._projeto.caminho_seguro(rel)
        if not os.path.isfile(caminho) or mp.tipo_arquivo(caminho) != "perfil":
            raise ErroUsuario(f"Arquivo de perfil não encontrado: {rel}")
        arq = self._banco.arquivo(rel) or {}
        return caminho, arq

    def _cache(self, poco_id: str) -> str:
        return os.path.join(self._projeto.pasta, "pocos", mp.nome_seguro(poco_id or "sem_poco"))

    @resposta_segura
    def perfis(self):
        self._exigir_projeto()
        saida = []
        for a in self._banco.arquivos():
            if a["tipo"] != "perfil":
                continue
            p = self._banco.perfil(a["rel"])
            caminho = os.path.join(self._projeto.pasta, a["rel"])
            saida.append({"rel": a["rel"], "nome": os.path.basename(a["rel"]), "poco": a["poco_id"],
                          "formato": formatos.formato(caminho),
                          "bytes": a["bytes"], "inventariado": bool(p and not p.get("erro")),
                          "n_curvas": p["n_curvas"] if p else 0,
                          "topo_m": p["topo_m"] if p else None, "base_m": p["base_m"] if p else None})
        return {"perfis": saida}

    @resposta_segura
    def inventariar_perfil(self, rel: str):
        caminho, arq = self._arquivo_perfil(rel)
        rel = mp.rel_padrao(rel)
        poco = arq.get("poco_id") or self._id_poco(self._projeto.bacia_poco_de(rel)[1])
        self._status(f"Lendo {os.path.basename(caminho)}… (arquivos grandes levam alguns segundos)")
        inv = mpf.inventariar(caminho, self._cl(), self._cache(poco))
        aviso = ""
        cad = inv["cabecalho"].get("cadastro")
        if cad:   # o DLIS grava o nº de cadastro da ANP: confere com o poço da pasta
            with self._banco.conexao() as c:
                r = c.execute("SELECT id FROM pocos WHERE cadastro = ?", (cad,)).fetchone()
            if r and r[0] != poco:
                aviso = (f"O arquivo diz ser do poço {r[0]} (cadastro {cad}), mas está na pasta "
                         f"de {poco}. Confira no portal.")
        self._banco.salvar_inventario(rel, poco, inv)
        self._projeto.registrar("inventariou_perfil", arquivo=rel, poco=poco,
                                quadros=len(inv["quadros"]), topo=inv["topo_m"], base=inv["base_m"])
        return {**self._curvas(rel, poco, inv), "aviso": aviso}

    def _curvas(self, rel, poco, inv):
        return {"rel": rel, "poco": poco, "inventario": inv,
                "padrao": mpf.curvas_padrao(inv, self._cl()),
                "familias": self._cl().familias,
                "fatos": [f for f in self._banco.fatos(poco)
                          if f["tipo"] in ("topo_formacao", "intervalo_alvo", "revestimento",
                                           "profundidade_final", "contato_fluido", "teste_formacao",
                                           "canhoneio")]}

    @resposta_segura
    def curvas_perfil(self, rel: str):
        _, arq = self._arquivo_perfil(rel)
        rel = mp.rel_padrao(rel)
        poco = arq.get("poco_id", "")
        inv = mpf.ler_inventario(self._cache(poco), os.path.basename(rel))
        if inv is None:
            return {"rel": rel, "poco": poco, "inventario": None}
        return self._curvas(rel, poco, inv)

    @resposta_segura
    def grafico_perfil(self, rel: str, selecao: list, topo=None, base=None):
        _, arq = self._arquivo_perfil(rel)
        rel = mp.rel_padrao(rel)
        dados = mpf.dados_grafico(self._cache(arq.get("poco_id", "")), os.path.basename(rel),
                                  selecao, None if topo is None else float(topo),
                                  None if base is None else float(base))
        return {"curvas": dados}

    @resposta_segura
    def exportar_perfil(self, rel: str, selecao: list, formato: str = "las", passo=None):
        _, arq = self._arquivo_perfil(rel)
        rel = mp.rel_padrao(rel)
        if not selecao:
            raise ErroUsuario("Escolha ao menos uma curva para exportar.")
        poco = arq.get("poco_id", "")
        nome = os.path.basename(rel)
        quando = datetime.now().strftime("%Y%m%d-%H%M")
        pasta = os.path.join(self._projeto.pasta_de("exportacoes"), mp.nome_seguro(poco or "sem_poco"))
        saida = os.path.join(pasta, f"{os.path.splitext(nome)[0]}__{quando}.{formato}")
        inv = mpf.ler_inventario(self._cache(poco), nome) or {"cabecalho": {}}
        passo = float(str(passo).replace(",", ".")) if passo not in (None, "") else None
        if formato == "las":
            r = mpf.exportar_las(saida, self._cache(poco), nome, selecao, inv["cabecalho"], poco, passo)
        elif formato == "csv":
            r = mpf.exportar_csv(saida, self._cache(poco), nome, selecao, passo)
        else:
            raise ErroUsuario("Formato de exportação: las ou csv.")
        self._projeto.registrar("exportou_perfil", arquivo=rel, saida=self._projeto.rel(saida),
                                mnemonicos=[s["mnemonico"] for s in selecao], **r)
        return {"arquivo": self._projeto.rel(saida), **r}

    @resposta_segura
    def salvar_intervalo(self, rel: str, dados: dict):
        """Intervalo-alvo (ou topo de formação) marcado sobre o perfil."""
        _, arq = self._arquivo_perfil(rel)
        dados = {**dados, "poco": arq.get("poco_id") or dados.get("poco")}
        return {"fato": self._salvar_fato(dados, fonte_rel=rel)}
