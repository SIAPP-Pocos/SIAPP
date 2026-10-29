"""Ponte: autoria, exportar/importar contribuições, base comunitária, painel de
preenchimento e biblioteca de interpretações de perfil."""

from __future__ import annotations

import os
import re
import subprocess
import sys

import webview

from motor import avaliacao as mav
from motor import biblioteca as mbib
from motor import comunidade as mc
from motor import painel as mpainel
from motor import projeto as mp

from .base import ErroUsuario, resposta_segura

PASTA_CONTRIBUICOES = "contribuicoes"   # pacotes exportados por este computador
PASTA_COMUNIDADE = "comunidade"         # base comunitária baixada
_RE_ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


class ComunidadeAPI:
    # ----------------------------------------------------------------- autor
    @resposta_segura
    def definir_autor(self, nome: str, instituicao: str = "", orcid: str = ""):
        self._exigir_projeto()
        nome, instituicao, orcid = (" ".join(str(x or "").split()) for x in (nome, instituicao, orcid))
        if len(nome) < 3:
            raise ErroUsuario("Informe seu nome completo: ele assina as suas contribuições.")
        if orcid and not _RE_ORCID.match(orcid):
            raise ErroUsuario("ORCID no formato 0000-0000-0000-0000 (ou deixe em branco).")
        autor = {"nome": nome, "instituicao": instituicao, "orcid": orcid}
        self._projeto.definir_config(autor=autor)
        return {"autor": autor}

    # --------------------------------------------------------------- resumo
    @resposta_segura
    def comunidade(self):
        self._exigir_projeto()
        b = self._banco
        local = b.vocab_local()
        bases = b.pacotes("base")
        return {
            "autor": self._projeto.config.get("autor") or {},
            "local": {"correcoes": len(local["correcoes"]), "palavras": len(local["palavras"]),
                      "manter_original": len(local["ignorar"]),
                      "fatos": b.contar("fatos", "WHERE origem = 'local'"),
                      "fatos_nao_exportados": b.contar(
                          "fatos", "WHERE origem = 'local' AND exportado_em IS NULL"),
                      "interpretacoes": b.contar("interpretacoes", "WHERE origem = 'local'"),
                      "interpretacoes_nao_exportadas": b.contar(
                          "interpretacoes", "WHERE origem = 'local' AND exportado_em IS NULL")},
            "ultima_exportacao": b.meta("ultima_exportacao"),
            "exportados": b.pacotes("exportado")[:10],
            "importados": b.pacotes("importado"),
            "base": bases[0] if bases else None,
            "pasta_contribuicoes": os.path.join(mp.NOME_PASTA_PADRAO, PASTA_CONTRIBUICOES),
        }

    # -------------------------------------------------------------- exportar
    @resposta_segura
    def exportar_contribuicao(self, apenas_novos: bool = True):
        self._exigir_projeto()
        pacote = mc.montar_pacote(self._banco, self._projeto.config.get("autor") or {},
                                  mp.VERSAO_SIAPP, apenas_novos=bool(apenas_novos))
        if mc.pacote_vazio(pacote):
            raise ErroUsuario("Nada novo para exportar desde a última vez." if apenas_novos
                              else "Ainda não há correções nem fatos feitos neste computador.")
        caminho = mc.gravar_pacote(self._banco, pacote, self._projeto.pasta_de(PASTA_CONTRIBUICOES))
        self._projeto.registrar("exportou_contribuicao", pacote=pacote["id"],
                                arquivo=os.path.basename(caminho), **mc.contar_itens(pacote))
        return {"arquivo": self._projeto.rel(caminho), "itens": mc.contar_itens(pacote)}

    @resposta_segura
    def abrir_pasta_contribuicoes(self):
        self._exigir_projeto()
        _abrir_no_sistema(self._projeto.pasta_de(PASTA_CONTRIBUICOES))
        return {}

    # -------------------------------------------------------------- importar
    def _escolher_arquivo(self, tipos: tuple) -> str | None:
        escolha = self._janela.create_file_dialog(webview.FileDialog.OPEN,
                                                  directory=self._projeto.pasta,
                                                  file_types=tipos)
        if not escolha:
            return None
        return escolha[0] if isinstance(escolha, (list, tuple)) else escolha

    @resposta_segura
    def escolher_contribuicao(self):
        """Abre o diálogo e devolve a PRÉVIA da importação (nada é gravado)."""
        self._exigir_projeto()
        caminho = self._escolher_arquivo(("Contribuição SIAPP (*.json)", "Todos os arquivos (*.*)"))
        if not caminho:
            return {"cancelado": True}
        pacote = mc.ler_pacote(caminho)
        self._pacote_em_previa = (caminho, pacote)
        return {"arquivo": os.path.basename(caminho), "previa": mc.previa(self._banco, pacote)}

    @resposta_segura
    def confirmar_importacao(self, id_pacote: str):
        self._exigir_projeto()
        caminho, pacote = getattr(self, "_pacote_em_previa", (None, None))
        if not pacote or pacote["id"] != id_pacote:
            raise ErroUsuario("Escolha o arquivo de novo: a prévia expirou.")
        resumo = mc.importar(self._banco, pacote, os.path.basename(caminho))
        self._pacote_em_previa = (None, None)
        self._projeto.registrar("importou_contribuicao", pacote=pacote["id"],
                                autor=pacote["autor"].get("nome", ""), **resumo)
        return {"resumo": resumo, **self._aplicar_vocabulario_silencioso()}

    @resposta_segura
    def desfazer_pacote(self, id_pacote: str):
        self._exigir_projeto()
        n = self._banco.desfazer_pacote(id_pacote)
        self._projeto.registrar("desfez_pacote", pacote=id_pacote, **n)
        return {"removidos": n, **self._aplicar_vocabulario_silencioso()}

    # ----------------------------------------------------------------- base
    @resposta_segura
    def atualizar_base(self):
        """Baixa a base mais recente do SIAPP-dados (GitHub Releases) e aplica."""
        self._exigir_projeto()
        destino = os.path.join(self._projeto.pasta_de(PASTA_COMUNIDADE), mc.NOME_ARQUIVO_BASE)
        self._status("Baixando a base comunitária…")
        info = mc.baixar_base(destino)
        return self._aplicar_base(destino, info)

    @resposta_segura
    def importar_base_arquivo(self):
        self._exigir_projeto()
        caminho = self._escolher_arquivo(("Base SIAPP-dados (*.sqlite)", "Todos os arquivos (*.*)"))
        if not caminho:
            return {"cancelado": True}
        return self._aplicar_base(caminho, {})

    def _aplicar_base(self, caminho: str, info: dict) -> dict:
        resumo = mc.aplicar_base(self._banco, caminho)
        self._projeto.registrar("aplicou_base", **resumo)
        return {"resumo": {**resumo, **info}, **self._aplicar_vocabulario_silencioso()}

    # ---------------------------------------------------------------- painel
    @resposta_segura
    def painel_comunidade(self, bacia: str = ""):
        """Quanto está preenchido, quem contribuiu e onde ajudar (só leitura)."""
        self._exigir_projeto()
        r = mpainel.indicadores(self._banco, self._autor(), (bacia or "").strip() or None)
        nao_compart = self._execucoes_nao_compartilhadas()
        r["avaliacoes_nao_compartilhadas"] = len(nao_compart)
        return r

    # ------------------------------------------------------------ biblioteca
    def _execucoes(self) -> list[dict]:
        return mav.execucoes(self._projeto.pasta_de("execucoes"))

    def _execucoes_nao_compartilhadas(self, poco: str | None = None) -> list[dict]:
        publicadas = {i["execucao"] for i in self._banco.interpretacoes(origem="local") if i.get("execucao")}
        return [e for e in self._execucoes()
                if e["id"] not in publicadas and e.get("intervalos") and (poco is None or e.get("poco") == poco)]

    def _arquivo_local(self, sha256: str | None, caminho: str | None, nome: str | None, poco: str | None):
        """O mesmo arquivo de perfil neste computador: pelo hash, pelo caminho no REATE ou pelo nome."""
        arqs = [a for a in self._banco.arquivos() if a["tipo"] == "perfil"]
        for chave, valor in (("sha256", sha256), ("caminho_remoto", caminho)):
            if valor:
                a = next((a for a in arqs if a.get(chave) == valor), None)
                if a:
                    return a, chave
        if nome:
            a = next((a for a in arqs if os.path.basename(a["rel"]) == nome
                      and (not poco or a.get("poco_id") == poco)), None)
            if a:
                return a, "nome"
        return None, None

    @resposta_segura
    def biblioteca(self, filtros: dict | None = None):
        """Interpretações da biblioteca (suas, de pacotes e da base), com filtros:
        texto (poço, título, autor ou comentário), bacia, origem, poco (exato)."""
        self._exigir_projeto()
        f = filtros or {}
        texto = " ".join(str(f.get("texto") or "").split()).lower()
        bacia, origem, poco = (str(f.get(k) or "").strip() for k in ("bacia", "origem", "poco"))
        with self._banco.conexao() as c:
            cad = {r[0]: {"campo": r[1] or "", "bacia": r[2] or ""}
                   for r in c.execute("SELECT id, campo, bacia FROM pocos WHERE id IN "
                                      "(SELECT DISTINCT poco_id FROM interpretacoes)")}
        tem = {a["sha256"] for a in self._banco.arquivos() if a["tipo"] == "perfil" and a.get("sha256")}
        itens, autores, bacias = [], set(), set()
        for row in self._banco.interpretacoes(poco or None):
            r = mbib.resumo(row)
            r.update(cad.get(r["poco"], {"campo": "", "bacia": row.get("arquivo_bacia") or ""}))
            r["tem_arquivo"] = bool(row.get("arquivo_sha256") and row["arquivo_sha256"] in tem) or \
                self._arquivo_local(row.get("arquivo_sha256"), row.get("arquivo_caminho"),
                                    row.get("arquivo_nome"), row["poco_id"])[0] is not None
            autores.add(r["autor"])
            if r["bacia"]:
                bacias.add(r["bacia"])
            if bacia and r["bacia"] != bacia or origem and r["origem"] != origem:
                continue
            if texto and texto not in " ".join([r["poco"], r["titulo"], r["autor"], r["comentario"],
                                                r["campo"]]).lower():
                continue
            itens.append(r)
        itens.sort(key=lambda r: (r["poco"], r["criado_em"]), reverse=False)
        nao = [{"id": e["id"], "poco": e.get("poco"), "arquivo_nome": os.path.basename(e.get("arquivo") or ""),
                "criado_em": e.get("criado_em"), "metodos": mbib.nome_metodos(e.get("metodos") or {}),
                "intervalos": [{"nome": i.get("nome"), "topo": i.get("topo"), "base": i.get("base"),
                                "net_pay_m": i.get("net_pay_m")} for i in e["intervalos"]],
                "totais": mbib.totais({"intervalos": e["intervalos"]})}
               for e in self._execucoes_nao_compartilhadas(poco or None)]
        if texto:
            nao = [e for e in nao if texto in (e["poco"] or "").lower()]
        return {"interpretacoes": itens, "nao_compartilhadas": nao[:50],
                "autores": sorted(a for a in autores if a), "bacias": sorted(bacias),
                "total": self._banco.contar("interpretacoes")}

    @resposta_segura
    def interpretacao(self, id_: str):
        self._exigir_projeto()
        row = self._banco.interpretacao(id_)
        if row is None:
            raise ErroUsuario("Interpretação não encontrada (o pacote pode ter sido desfeito).")
        d = row["dados"]
        arq, como = self._arquivo_local(row.get("arquivo_sha256"), row.get("arquivo_caminho"),
                                        row.get("arquivo_nome"), row["poco_id"])
        par = d.get("parametros") or {}
        auto = d.get("parametros_automaticos") or {}
        return {**mbib.resumo(row), "arquivo_caminho": row.get("arquivo_caminho") or "",
                "arquivo_bacia": row.get("arquivo_bacia") or "",
                "arquivo_local": arq["rel"] if arq else None, "arquivo_conferido_por": como,
                "curvas_usadas": d.get("curvas_usadas") or {}, "intervalos_completos": d.get("intervalos") or [],
                "parametros": [{"chave": k, "nome": mbib.NOMES_PARAM.get(k, k), "valor": par.get(k),
                                "auto": auto.get(k)} for k in mbib.PARAMETROS
                               if not k.endswith("_metodo") and par.get(k) is not None],
                "siapp_versao": d.get("siapp_versao") or "", "passo_m": d.get("passo_m"),
                "pode_remover": row["origem"] == "local"}

    @resposta_segura
    def publicar_interpretacao(self, execucao: str, titulo: str = "", comentario: str = ""):
        """Compartilha uma avaliação de formação na biblioteca (vai no próximo pacote)."""
        self._exigir_projeto()
        autor = self._autor()
        if not autor:
            raise ErroUsuario("Preencha seu nome na aba Comunidade (Contribuir) antes de compartilhar: "
                              "toda interpretação tem autor.")
        reg = next((e for e in self._execucoes() if e["id"] == execucao), None)
        if reg is None:
            raise ErroUsuario("Avaliação não encontrada: calcule de novo.")
        try:
            titulo, comentario = mbib.limpar_texto(titulo, comentario)
            dados = mbib.de_execucao(reg, self._banco.arquivo(reg.get("arquivo") or "") or {})
        except mbib.ErroBiblioteca as e:
            raise ErroUsuario(str(e)) from e
        ja = next((i for i in self._banco.interpretacoes(origem="local") if i.get("execucao") == execucao), None)
        if ja:   # já compartilhada: só o título e o comentário mudam (e volta a ir no pacote)
            ja.update(titulo=titulo, comentario=comentario, exportado_em=None)
            id_ = self._banco.salvar_interpretacao(ja)
        else:
            id_ = self._banco.salvar_interpretacao({**dados, "titulo": titulo, "comentario": comentario,
                                                    "autor": autor, "origem": "local"})
        self._projeto.registrar("compartilhou_interpretacao", interpretacao=id_, execucao=execucao,
                                poco=dados["poco_id"], atualizada=bool(ja))
        return {"id": id_, "atualizada": bool(ja)}

    @resposta_segura
    def remover_interpretacao(self, id_: str):
        self._exigir_projeto()
        row = self._banco.interpretacao(id_)
        if row and row["origem"] != "local":
            raise ErroUsuario("Esta interpretação veio da comunidade: desfaça o pacote inteiro (Contribuir).")
        n = self._banco.remover_interpretacao(id_)
        if n:
            self._projeto.registrar("removeu_interpretacao", interpretacao=id_,
                                    ja_exportada=bool(row and row.get("exportado_em")))
        return {"removidas": n, "ja_exportada": bool(row and row.get("exportado_em"))}

    def _item_comparacao(self, ident: str) -> dict:
        if ident.startswith("exec:"):
            reg = next((e for e in self._execucoes() if e["id"] == ident[5:]), None)
            if reg is None:
                raise ErroUsuario("Avaliação não encontrada: calcule de novo.")
            d = mbib.de_execucao(reg, self._banco.arquivo(reg.get("arquivo") or "") or {})
            iso = reg.get("criado_em") or ""
            quando = f"{iso[8:10]}/{iso[5:7]}/{iso[:4]} {iso[11:16]}" if len(iso) >= 16 else iso
            return {"id": ident, "rotulo": f"Sua avaliação de {quando} (não compartilhada)",
                    "autor": self._autor() or "você", "origem": "não compartilhada", "poco": d["poco_id"],
                    "arquivo_sha256": d["arquivo_sha256"], "arquivo_nome": d["arquivo_nome"],
                    "criado_em": reg["criado_em"], "dados": d["dados"]}
        row = self._banco.interpretacao(ident)
        if row is None:
            raise ErroUsuario("Interpretação não encontrada.")
        return {"id": row["id"], "rotulo": row.get("titulo") or f"{row.get('autor') or 'sem autor'}",
                "autor": row.get("autor") or "", "origem": row["origem"], "poco": row["poco_id"],
                "arquivo_sha256": row.get("arquivo_sha256"), "arquivo_nome": row.get("arquivo_nome"),
                "criado_em": row["criado_em"], "dados": row["dados"]}

    @resposta_segura
    def comparar_interpretacoes(self, ids: list):
        """`ids`: interpretações da biblioteca ou "exec:<id>" (avaliação sua ainda não compartilhada)."""
        self._exigir_projeto()
        itens = [self._item_comparacao(str(i)) for i in dict.fromkeys(ids or [])]
        try:
            return mbib.comparar(itens)
        except mbib.ErroBiblioteca as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def interpretacao_refazer(self, id_: str):
        """Onde está o arquivo para refazer a interpretação na aba Perfis."""
        self._exigir_projeto()
        row = self._banco.interpretacao(id_)
        if row is None:
            raise ErroUsuario("Interpretação não encontrada.")
        arq, como = self._arquivo_local(row.get("arquivo_sha256"), row.get("arquivo_caminho"),
                                        row.get("arquivo_nome"), row["poco_id"])
        if arq is None:
            raise ErroUsuario(f"Você ainda não tem o arquivo {row.get('arquivo_nome') or 'de perfil'} do poço "
                              f"{row['poco_id']}. Baixe-o na aba Dados › Catálogo do REATE"
                              + (f" ({row['arquivo_caminho']})." if row.get("arquivo_caminho") else "."))
        return {"rel": arq["rel"], "nome": os.path.basename(arq["rel"]), "poco": row["poco_id"],
                "conferido_por": como}

    def _aplicar_vocabulario_silencioso(self) -> dict:
        """Depois de mudar o que veio da comunidade: recarrega o corretor e o índice."""
        self._carregar_corretor()
        n = self._reindexar_tudo()
        return {"paginas_atualizadas": n}


def _abrir_no_sistema(caminho: str):
    if sys.platform.startswith("win"):
        os.startfile(caminho)   # noqa: S606 — pasta dentro do projeto
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])
