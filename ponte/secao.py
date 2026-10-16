"""Ponte: seção estratigráfica a partir dos topos do AGP (aba Seção)."""

from __future__ import annotations

import json
import os

from motor import agp as magp
from motor import perfis as mpf
from motor import secao as msc

from .base import PASTA_RECURSOS, ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

CAMINHO_ESTRATIGRAFIA = os.path.join(PASTA_RECURSOS, "estratigrafia.json")
PASTA_EXPORTACAO = os.path.join("exportacoes", "secoes")
FORMATOS = ("svg", "png", "pdf", "csv")


class SecaoAPI:
    @resposta_segura
    def secao_pocos(self, bacia: str = ""):
        """Poços com topos de formação no AGP e coordenadas (para escolher)."""
        self._exigir_projeto()
        pocos = msc.pocos_com_topos(self._banco, bacia or None)
        return {"pocos": pocos, "total": len(pocos)}

    @resposta_segura
    def secao_corredor(self, poco_a: str, poco_b: str, largura_km=2.0):
        self._exigir_projeto()
        try:
            r = msc.corredor(self._banco, self._id_poco(poco_a), self._id_poco(poco_b), float(largura_km))
        except (msc.ErroSecao, ValueError) as e:
            raise ErroUsuario(str(e)) from e
        return r

    @resposta_segura
    def secao_unidades(self, pocos: list):
        """Unidades litoestratigráficas dos poços (para escolher o datum)."""
        self._exigir_projeto()
        nomes = magp.ler_estratigrafia(CAMINHO_ESTRATIGRAFIA)
        cont: dict[str, dict] = {}
        for pid in [self._id_poco(p) for p in pocos]:
            g = magp.do_poco(self._banco, pid)
            for u in magp.unidades_do_poco(self._banco, pid):
                if u["tip"] != "L" or u["topo"] is None or (g and u["caminho"] != g[0]["caminho"]):
                    continue
                n = msc._normalizar(u, nomes)
                item = cont.setdefault(n["sigla"].upper(), {"chave": n["sigla"].upper(),
                                                           "nome": msc._rotulo_unidade(n), "pocos": set()})
                item["pocos"].add(pid)
        lst = sorted(({**v, "pocos": len(v["pocos"])} for v in cont.values()), key=lambda v: -v["pocos"])
        return {"unidades": lst}

    def _gr_de(self, poco_id: str):
        """GR do perfil já lido do poço com maior cobertura (None se não houver)."""
        melhor = None
        for a in self._banco.arquivos(poco_id):
            if a["tipo"] != "perfil":
                continue
            nome = os.path.basename(a["rel"])
            cache = self._cache(poco_id)
            inv = mpf.ler_inventario(cache, nome)
            if not inv:
                continue
            for s in mpf.curvas_padrao(inv, self._cl()):
                if s["familia"] != "GR":
                    continue
                q = next((q for q in inv["quadros"] if q["nome"] == s["quadro"]), None)
                c = next((c for c in (q or {}).get("curvas", []) if c["mnemonico"] == s["mnemonico"]), None)
                cob = (c["base_m"] - c["topo_m"]) if c and c["topo_m"] is not None else 0
                if melhor is None or cob > melhor[0]:
                    melhor = (cob, cache, nome, s, a["rel"])
        if melhor is None:
            return None
        _, cache, nome, s, rel = melhor
        d = mpf.dados_grafico(cache, nome, [s], max_pontos=1600)
        if not d:
            return None
        return {"arquivo": rel, "mnemonico": s["mnemonico"], "prof": d[0]["prof"], "valores": d[0]["valores"]}

    @resposta_segura
    def secao_montar(self, pocos: list, opcoes: dict | None = None):
        self._exigir_projeto()
        op = opcoes or {}
        ids = [self._id_poco(p) for p in pocos if str(p).strip()]

        def num(k):
            v = op.get(k)
            if v in (None, ""):
                return None
            try:
                return float(str(v).replace(",", "."))
            except ValueError as e:
                raise ErroUsuario(f"Valor inválido: {v}") from e
        janela = (num("y_topo"), num("y_base"))
        try:
            modelo = msc.montar(
                self._banco, ids, ordem=op.get("ordem", "linha"), nivel=op.get("nivel", "formacoes"),
                eixo=op.get("eixo", "cota"), datum=op.get("datum") or None,
                espacamento=op.get("espacamento", "proporcional"), litologia=bool(op.get("litologia", True)),
                gr=bool(op.get("gr", True)), gr_de=self._gr_de, slots=msc.ler_slots(CAMINHO_ESTRATIGRAFIA),
                nomes=magp.ler_estratigrafia(CAMINHO_ESTRATIGRAFIA),
                limiar_salto_m=num("limiar") or msc.LIMIAR_SALTO_M,
                janela=janela if any(v is not None for v in janela) else None)
        except msc.ErroSecao as e:
            raise ErroUsuario(str(e)) from e
        svg = msc.desenhar(modelo, (op.get("titulo") or "").strip())
        ident, _ = msc.registrar(self._projeto.pasta_de("execucoes"), modelo, svg, autor=self._autor())
        self._projeto.registrar("montou_secao", execucao=ident, pocos=[p["id"] for p in modelo["pocos"]],
                                parametros=modelo["parametros"])
        return {"id": ident, "svg": svg, "avisos": modelo["avisos"], "saltos": modelo["saltos"],
                "legenda": modelo["legenda"], "pontas": modelo["pontas"],
                "comprimento_km": modelo["comprimento_km"],
                "pocos": [{"id": p["id"], "x_km": p["x_km"], "dist_linha_km": p["dist_linha_km"], "mesa": p["mesa"],
                           "prof_final": p["prof_final"], "desviado": p["desviado"], "campo": p["campo"],
                           "gr": (p["gr"] or {}).get("mnemonico"),
                           "unidades": [{k: u[k] for k in ("chave", "nome", "topo", "base", "cota_topo", "cota_base",
                                                           "base_atingida", "fonte", "data", "qualidade")}
                                        for u in p["unidades"]]} for p in modelo["pocos"]]}

    @resposta_segura
    def secao_execucoes(self):
        self._exigir_projeto()
        return {"execucoes": msc.execucoes(self._projeto.pasta_de("execucoes"))[:20]}

    @resposta_segura
    def secao_abrir(self, ident: str):
        """Uma seção já montada (do histórico), sem recalcular."""
        self._exigir_projeto()
        if not ident or not ident.startswith("secao_") or "/" in ident or "\\" in ident:
            raise ErroUsuario("Seção inválida.")
        base = os.path.join(self._projeto.pasta_de("execucoes"), ident)
        try:
            with open(base + ".json", encoding="utf-8") as f:
                reg = json.load(f)
            with open(base + ".svg", encoding="utf-8") as f:
                svg = f.read()
        except OSError as e:
            raise ErroUsuario("Seção não encontrada.") from e
        return {"id": ident, "svg": svg, "avisos": reg.get("avisos", []), "parametros": reg.get("parametros", {}),
                "pocos": [p["id"] for p in reg.get("pocos", [])]}

    @resposta_segura
    def secao_exportar(self, ident: str, formato: str = "svg"):
        self._exigir_projeto()
        if formato not in FORMATOS:
            raise ErroUsuario(f"Formato desconhecido: {formato}")
        if not ident or "/" in ident or "\\" in ident or not ident.startswith("secao_"):
            raise ErroUsuario("Seção inválida.")
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        saida = os.path.join(pasta, f"{ident}.{formato}")
        try:
            msc.exportar(self._projeto.pasta_de("execucoes"), ident, saida, formato)
        except msc.ErroSecao as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("exportou_secao", execucao=ident, formato=formato)
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    @resposta_segura
    def abrir_pasta_secoes(self):
        self._exigir_projeto()
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        _abrir_no_sistema(pasta)
        return {}
