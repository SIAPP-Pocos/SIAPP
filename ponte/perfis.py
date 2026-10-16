"""Ponte: perfis de poço (DLIS/LIS/LAS) — inventário, gráfico, exportação, intervalo-alvo."""

from __future__ import annotations

import os
from datetime import datetime

from motor import agp as magp
from motor import avaliacao as mav
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
                "topos_agp": [{"sigla": u["sigla"], "nome": u["nome"], "nivel": u["nivel"], "tip": u["tip"],
                               "topo": u["topo"], "base": u["base"]}
                              for u in magp.unidades_do_poco(self._banco, poco) if u["topo"] is not None],
                "litologia_agp": [c for g in magp.do_poco(self._banco, poco)[:1]
                                  for c in g["dados"].get("litologia", [])],
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

    # ------------------------------------------------- avaliação de formação
    def _pasta_execucoes(self) -> str:
        return self._projeto.pasta_de("execucoes")

    def _intervalos_agp(self, poco: str) -> list[dict]:
        """Unidades (com topo e base) e zonas-reservatório do AGP, como intervalos
        candidatos. id estável: agp:u:<código> / agp:z:<código da zona>."""
        saida, vistos = [], set()
        for u in magp.unidades_do_poco(self._banco, poco):
            if u["topo"] is None or u["base"] is None or u["base"] <= u["topo"] or u["tip"] not in ("L", "C"):
                continue
            ident = f"agp:u:{u['codigo']}"
            if ident in vistos:
                continue
            vistos.add(ident)
            rotulo = "Crono ·" if u["tip"] == "C" else magp.NIVEIS.get(u["nivel"], "")
            saida.append({"id": ident, "nome": f"{rotulo} {u['nome']}".strip(), "prof_topo": u["topo"],
                          "prof_base": u["base"], "origem": "AGP"})
        for g in magp.do_poco(self._banco, poco)[:1]:
            for z in g["dados"].get("zonas", []):
                ident = f"agp:z:{z['codigo']}"
                if ident not in vistos and z["topo"] is not None and z["base"] and z["base"] > z["topo"]:
                    vistos.add(ident)
                    saida.append({"id": ident, "nome": f"Zona {z['codigo']}", "prof_topo": z["topo"],
                                  "prof_base": z["base"], "origem": "AGP"})
        return saida

    @resposta_segura
    def avaliacao_info(self, rel: str):
        """Curvas candidatas a cada papel, intervalos-alvo do poço, parâmetros
        padrão (ou os da última avaliação deste arquivo) e o histórico."""
        _, arq = self._arquivo_perfil(rel)
        rel = mp.rel_padrao(rel)
        poco = arq.get("poco_id", "")
        inv = mpf.ler_inventario(self._cache(poco), os.path.basename(rel))
        if inv is None:
            raise ErroUsuario("Leia o arquivo primeiro (clique nele na lista).")
        padrao = {c["familia"]: c for c in mpf.curvas_padrao(inv, self._cl())}
        papeis = {}
        for papel, (fams, obrig) in mav.PAPEIS.items():
            opcoes = [{"quadro": q["nome"], "mnemonico": c["mnemonico"], "unidade": c["unidade"],
                       "familia": c["familia"], "n_validas": c["n_validas"]}
                      for q in inv["quadros"] for c in q["curvas"]
                      if c["familia"] in fams and c["dimensao"] == 1 and c["n_validas"]]
            escolhida = next((padrao[f] for f in fams if f in padrao), None)
            papeis[papel] = {"obrigatorio": obrig, "opcoes": opcoes, "padrao": escolhida}
        historico = mav.execucoes(self._pasta_execucoes(), rel)
        return {"papeis": papeis, "padrao": mav.PADRAO, "nomes": mav.NOMES_METODO,
                "intervalos": [f for f in self._banco.fatos(poco, tipo="intervalo_alvo")
                               if f["prof_topo"] is not None and f["prof_base"] is not None],
                "intervalos_agp": self._intervalos_agp(poco),
                "lama_agp": [c for g in magp.do_poco(self._banco, poco)[:1] for c in g["dados"].get("corridas", [])],
                "temperaturas_agp": [t for g in magp.do_poco(self._banco, poco)[:1]
                                     for t in g["dados"].get("temperaturas", [])],
                "ultima": historico[0] if historico else None,
                "historico": [{"id": h["id"], "criado_em": h["criado_em"], "metodos": h["metodos"],
                               "intervalos": h["intervalos"], "parametros": h["parametros"],
                               "parametros_automaticos": h.get("parametros_automaticos", {})}
                              for h in historico[:10]]}

    @resposta_segura
    def avaliar_formacao(self, rel: str, curvas: dict, intervalos: list, parametros: dict):
        """`intervalos`: ids dos fatos intervalo_alvo do poço."""
        _, arq = self._arquivo_perfil(rel)
        rel = mp.rel_padrao(rel)
        poco = arq.get("poco_id", "")
        fatos = {f["id"]: f for f in self._banco.fatos(poco, tipo="intervalo_alvo")}
        fatos.update({i["id"]: i for i in self._intervalos_agp(poco)})
        escolhidos = [{"id": fid, "nome": fatos[fid]["nome"], "topo": fatos[fid]["prof_topo"],
                       "base": fatos[fid]["prof_base"], "origem": fatos[fid].get("origem", "SIAPP")}
                      for fid in intervalos if fid in fatos]
        if not escolhidos:
            raise ErroUsuario("Escolha ao menos um intervalo-alvo. Marque-o arrastando sobre o gráfico.")
        self._status("Calculando a avaliação de formação…")
        try:
            r = mav.avaliar(self._cache(poco), os.path.basename(rel), curvas or {}, escolhidos, parametros)
        except mav.ErroAvaliacao as e:
            raise ErroUsuario(str(e)) from e
        ident, caminho = mav.registrar(self._pasta_execucoes(), poco=poco, rel=rel,
                                       sha256=arq.get("sha256"), resultado=r, autor=self._autor())
        self._projeto.registrar("avaliou_formacao", execucao=ident, arquivo=rel, poco=poco,
                                intervalos=[i["nome"] for i in escolhidos],
                                net_pay_m=sum(i["net_pay_m"] for i in r["intervalos"]))
        return {"id": ident, "registro": self._projeto.rel(caminho).replace(os.sep, "/"),
                "intervalos": r["intervalos"], "parametros": r["parametros"],
                "automaticos": r["automaticos"], "passo": r["passo"]}

    @resposta_segura
    def grafico_avaliacao(self, ident: str, topo=None, base=None):
        self._exigir_projeto()
        try:
            return {"curvas": mav.dados_grafico(self._pasta_execucoes(), ident,
                                                None if topo is None else float(topo),
                                                None if base is None else float(base))}
        except mav.ErroAvaliacao as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def exportar_avaliacao(self, ident: str, formato: str = "csv"):
        self._exigir_projeto()
        reg = next((h for h in mav.execucoes(self._pasta_execucoes()) if h["id"] == ident), None)
        if reg is None:
            raise ErroUsuario("Avaliação não encontrada.")
        pasta = os.path.join(self._projeto.pasta_de("exportacoes"), mp.nome_seguro(reg["poco"] or "sem_poco"))
        saida = os.path.join(pasta, f"{ident}.{formato}")
        try:
            r = mav.exportar(self._pasta_execucoes(), ident, saida, formato, reg["poco"])
        except mav.ErroAvaliacao as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("exportou_avaliacao", execucao=ident, saida=self._projeto.rel(saida))
        return {"arquivo": self._projeto.rel(saida).replace(os.sep, "/"), **r}
