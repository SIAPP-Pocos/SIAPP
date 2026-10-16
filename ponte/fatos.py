"""Ponte: dados transcritos ("fatos") — cada valor com poço, tipo e fonte."""

from __future__ import annotations

from motor import comunidade as mc
from motor import projeto as mp

from .base import ErroUsuario, resposta_segura


def _numero(v, campo):
    if v in (None, ""):
        return None
    try:
        x = float(str(v).replace(",", "."))
    except ValueError:
        raise ErroUsuario(f"{campo}: use um número (ex.: 1234,5).") from None
    if not -100 <= x <= mc.PROF_MAX_M:
        raise ErroUsuario(f"{campo}: {x} m está fora do intervalo aceito (−100 a {mc.PROF_MAX_M} m).")
    return x


class FatosAPI:
    @resposta_segura
    def tipos_fato(self):
        return {"tipos": mc.TIPOS_FATO}

    def _salvar_fato(self, dados: dict, *, fonte_rel: str | None = None) -> dict:
        """Valida e grava um fato local. `fonte_rel`: arquivo de onde o dado saiu."""
        tipo = dados.get("tipo")
        if tipo not in mc.TIPOS_FATO:
            raise ErroUsuario("Escolha o tipo do dado.")
        poco = " ".join(str(dados.get("poco") or "").split())
        if not poco:
            raise ErroUsuario("Informe o poço.")
        topo = _numero(dados.get("prof_topo"), "Topo")
        base = _numero(dados.get("prof_base"), "Base")
        if topo is not None and base is not None and base < topo:
            raise ErroUsuario("A base está acima do topo.")
        if tipo in ("topo_formacao", "intervalo_alvo") and not (dados.get("nome") or "").strip():
            raise ErroUsuario("Informe o nome (formação ou intervalo).")
        if tipo in ("topo_formacao", "profundidade_final", "revestimento") and topo is None:
            raise ErroUsuario("Informe a profundidade.")
        if tipo == "intervalo_alvo" and (topo is None or base is None):
            raise ErroUsuario("Informe topo e base do intervalo.")
        fato = {k: (" ".join(str(dados.get(k) or "").split()) or None)
                for k in ("nome", "valor", "unidade", "observacao")}
        fato.update({"id": dados.get("id"), "poco_id": self._id_poco(poco), "tipo": tipo,
                     "prof_topo": topo, "prof_base": base, "autor": self._autor(), "origem": "local"})
        if fonte_rel:
            rel = mp.rel_padrao(fonte_rel)
            arq = self._banco.arquivo(rel) or {}
            fato.update({"fonte_rel": rel, "fonte_sha256": arq.get("sha256"),
                         "fonte_caminho": arq.get("caminho_remoto"), "fonte_bacia": arq.get("bacia"),
                         "pagina": dados.get("pagina"), "caixa": dados.get("caixa")})
        if fato["id"]:
            antigo = self._banco.fato(fato["id"])
            if not antigo or antigo["origem"] != "local":
                raise ErroUsuario("Só dá para editar dados feitos neste computador.")
            fato["criado_em"] = antigo["criado_em"]
        id_ = self._banco.salvar_fato(fato)
        self._projeto.registrar("salvou_fato", fato=id_, poco=fato["poco_id"], tipo=tipo)
        return self._banco.fato(id_)

    @resposta_segura
    def remover_fato(self, id_fato: str):
        self._exigir_projeto()
        if not self._banco.remover_fato(id_fato):
            raise ErroUsuario("Só dá para apagar dados feitos neste computador.")
        self._projeto.registrar("removeu_fato", fato=id_fato)
        return {}

    @resposta_segura
    def fatos_poco(self, poco: str):
        self._exigir_projeto()
        return {"fatos": self._banco.fatos(self._id_poco(poco))}
