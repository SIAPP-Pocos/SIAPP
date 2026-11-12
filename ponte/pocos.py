"""Ponte: cadastro de poços da ANP, catálogo do REATE no banco, mapa e ficha."""

from __future__ import annotations

import json
import os

import webview

from motor import producao as mprod
from motor import agp as magp
from motor import dados_poco as mdp
from motor import pressoes as mpr
from motor import levantamento as mlv
from motor import pocos as mpo
from motor import projeto as mp

from .base import ErroUsuario, resposta_segura


class PocosAPI:
    # ------------------------------------------------------- id dos poços
    def _id_poco(self, nome_pasta: str) -> str:
        return mpo.resolver(self._banco, nome_pasta) if nome_pasta else ""

    def _ao_listar_pocos(self, bacia, categoria, pocos):
        mpo.registrar_reate(self._banco, bacia, categoria, pocos, substituir=True)

    def _migrar_pocos(self):
        """Listas de poços salvas antes do banco (catalogo/*.json) entram na
        tabela reate; arquivos ganham o id canônico do poço."""
        if not self._banco.meta("migrou_catalogo_json"):
            n = mpo.importar_catalogo_json(self._banco, os.path.join(self._projeto.pasta, "catalogo"))
            self._banco.definir_meta("migrou_catalogo_json", str(n))
        if not self._banco.meta("reparou_reate_bacias"):
            r = mpo.reparar_reate_bacias(self._banco)
            self._banco.definir_meta("reparou_reate_bacias", str(r["apagados"]))
            if r["apagados"]:
                self._projeto.registrar("reparou_catalogo", apagados=r["apagados"], bacias=r["bacias"])
        with self._banco.conexao() as c:
            for rel, poco in c.execute("SELECT rel, poco_id FROM arquivos").fetchall():
                novo = mpo.chave(poco or "")
                if novo and novo != poco:
                    c.execute("UPDATE arquivos SET poco_id = ? WHERE rel = ?", (novo, rel))

    # ------------------------------------------------------------ cadastro
    @resposta_segura
    def cadastro_info(self):
        self._exigir_projeto()
        import json
        info = self._banco.meta("cadastro_anp")
        return {"cadastro": json.loads(info) if info else None,
                "bacias": mpo.bacias(self._banco),
                "pagina_anp": mpo.PAGINA_CADASTRO}

    @resposta_segura
    def atualizar_cadastro_anp(self):
        """Baixa a Tabela de Poços dos dados abertos da ANP (~12 MB) e importa."""
        self._exigir_projeto()
        self._status("Baixando a Tabela de Poços da ANP (~12 MB)…")
        dados = mpo.baixar_cadastro()
        destino = os.path.join(self._projeto.pasta_de("cadastro"), "tabela-pocos.csv")
        with open(destino, "wb") as f:
            f.write(dados)
        return self._importar_cadastro(dados, "anp:dados-abertos")

    @resposta_segura
    def importar_cadastro_arquivo(self):
        self._exigir_projeto()
        escolha = self._janela.create_file_dialog(
            webview.FileDialog.OPEN, directory=self._projeto.pasta,
            file_types=("Tabela de Poços (*.csv)", "Todos os arquivos (*.*)"))
        if not escolha:
            return {"cancelado": True}
        caminho = escolha[0] if isinstance(escolha, (list, tuple)) else escolha
        with open(caminho, "rb") as f:
            return self._importar_cadastro(f.read(), "anp:arquivo:" + os.path.basename(caminho))

    def _importar_cadastro(self, dados: bytes, fonte: str) -> dict:
        self._status("Lendo o cadastro…")
        linhas = mpo.ler_cadastro(dados)
        r = mpo.importar_cadastro(self._banco, linhas, fonte)
        self._migrar_pocos()
        self._projeto.registrar("importou_cadastro_anp", fonte=fonte, **r)
        return {"resumo": r, "bacias": mpo.bacias(self._banco)}

    # --------------------------------------------------------- mapa e ficha
    @resposta_segura
    def pocos_mapa(self, filtros: dict | None = None):
        self._exigir_projeto()
        f = filtros or {}
        return mpo.pocos_mapa(self._banco, bacia=f.get("bacia", ""), texto=f.get("texto", ""),
                              terra_mar=f.get("terra_mar", ""), tipo=f.get("tipo") or None,
                              so_reate=bool(f.get("so_reate")), so_baixados=bool(f.get("so_baixados")),
                              acervo=f.get("acervo", ""), familia=f.get("familia", ""))

    @resposta_segura
    def buscar_pocos(self, texto: str):
        """Busca de poço da barra do topo (Ctrl+K): nome em qualquer grafia."""
        self._exigir_projeto()
        return {"pocos": mpo.buscar(self._banco, str(texto or "")[:60])}

    @resposta_segura
    def ficha_poco(self, poco: str):
        self._exigir_projeto()
        pid = mpo.resolver(self._banco, poco)
        d = mpo.ficha(self._banco, pid)
        if d is None:
            raise ErroUsuario(f"Poço {poco} não está no cadastro nem no catálogo deste projeto.")
        d["acervo"] = mlv.arquivos_do_poco(self._banco, pid)
        d["esquemas"] = self._esquemas(pid)
        d["producao"] = mprod.do_poco(self._banco, pid, (d.get("poco") or {}).get("campo"))
        d["agp"] = [{"caminho": g["caminho"], "poco_pasta": g["poco_pasta"], "confere": g["confere"],
                     "arquivo_local": g["arquivo_local"], "lido_em": g["lido_em"], **g["dados"]}
                    for g in magp.do_poco(self._banco, pid)]
        d["dados_poco"] = self._dados_poco_ficha(pid)
        d["topos"] = self._topos_comparar(pid)
        return d

    def _topos_comparar(self, pid: str) -> dict:
        from motor import topos as mtp
        from .bloco import CAMINHO_ESTRATIGRAFIA
        return mtp.comparar(self._banco, pid, magp.ler_estratigrafia(CAMINHO_ESTRATIGRAFIA))

    @resposta_segura
    def topos_escolher(self, poco: str, chave: str, fonte: str | None):
        """Fonte do topo de uma unidade neste poço (None/"padrao" = a precedência do projeto)."""
        from motor import topos as mtp
        self._exigir_projeto()
        pid = mpo.resolver(self._banco, poco)
        try:
            mtp.escolher(self._banco, pid, str(chave), fonte, autor=self._autor())
        except ValueError as e:
            raise ErroUsuario(str(e)) from e
        self._projeto.registrar("escolheu_topo", poco=pid, unidade=chave, fonte=fonte or "padrão")
        return self._topos_comparar(pid)

    @resposta_segura
    def topos_precedencia(self, ordem: list | None = None):
        """Ordem das fontes de topo no projeto (lê; com `ordem`, grava)."""
        from motor import topos as mtp
        self._exigir_projeto()
        if ordem:
            atual = mtp.definir_precedencia(self._banco, [str(x) for x in ordem])
            self._projeto.registrar("definiu_precedencia_topos", ordem=atual)
        return {"ordem": mtp.precedencia(self._banco), "fontes": mtp.FONTES}

    def _dados_poco_ficha(self, pid: str) -> dict:
        """O que os formulários da ANP (RFP, RFCP, Perfuração) trouxeram, para a ficha."""
        dp = mdp.do_poco(self._banco, pid)
        docs = [{"rel": le["rel"], "documento": le["documento"], "n": le["n"], "erro": le["erro"],
                 "confere": le["confere"], "poco_documento": le["poco_documento"], "lido_em": le["lido_em"],
                 "observacoes": (le["dados"] or {}).get("observacoes") or "",
                 "titulo": mdp.LEITORES[le["leitor"]].DOCUMENTOS.get(le["documento"] or "", "")
                 if hasattr(mdp.LEITORES.get(le["leitor"]), "DOCUMENTOS") else ""}
                for le in dp["leituras"]]
        for d, le in zip(docs, dp["leituras"]):
            dados = le["dados"] or {}
            if dados.get("secoes_texto"):
                d["secoes_texto"] = dados["secoes_texto"]
            if dados.get("campos"):
                d["campos"] = dados["campos"]
            if dados.get("avisos") and isinstance(dados["avisos"], list):
                d["avisos"] = [a for a in dados["avisos"] if isinstance(a, str)]
            if dados.get("documento") == "cdpe":
                d["titulo"] = dados.get("titulo_formulario") or d["titulo"]
        itens = {k: v for k, v in dp["itens"].items() if k not in ("manometro",)}
        pvts = [{"rel": le["rel"], "amostra": le["dados"].get("amostra") or {}, "saturacao": le["dados"].get("saturacao"),
                 "tabela": le["dados"].get("tabela") or []}
                for le in dp["leituras"] if (le["dados"] or {}).get("documento") == "pvt_diferencial" and le["confere"] != 0]
        comps = [{"rel": le["rel"], "amostra": le["dados"].get("amostra") or {},
                  "componentes": le["dados"].get("componentes") or []}
                 for le in dp["leituras"] if (le["dados"] or {}).get("documento") == "pvt_flash" and le["confere"] != 0]
        cks = [{"rel": le["rel"], "niveis": le["dados"].get("niveis") or [], "referencia": le["dados"].get("referencia") or {},
                "cabecalho": le["dados"].get("cabecalho") or {}}
               for le in dp["leituras"] if (le["dados"] or {}).get("documento") == "checkshot" and le["confere"] != 0]
        itens.pop("checkshot", None)
        return {"checkshot": cks, "documentos": docs, "gerais": mdp.gerais(self._banco, pid), "itens": itens,
                "tipos": mdp.TIPOS, "pressoes": mpr.painel(dp), "pvt": pvts, "composicao": comps}

    @resposta_segura
    def serie_pressao(self, rel: str, qual: str):
        """Pressão × tempo de uma estação do teste a cabo ou de um manômetro do TFR."""
        self._exigir_projeto()
        with self._banco.conexao() as c:
            r = c.execute("SELECT dados FROM leituras WHERE rel = ?", (rel,)).fetchone()
        if not r or not r[0]:
            raise ErroUsuario("Leitura não encontrada: leia os dados do poço de novo.")
        try:
            return mpr.serie(json.loads(r[0]), qual)
        except mpr.ErroPressao as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def gradiente_pressoes(self, grupos: dict):
        """Gradiente de cada grupo de pontos ({"A": [[prof, pressão], …], "B": …}) e o contato entre eles."""
        saida = {}
        for nome, pts in (grupos or {}).items():
            if pts:
                try:
                    saida[nome] = mpr.gradiente([(float(z), float(p)) for z, p in pts])
                except mpr.ErroPressao as e:
                    raise ErroUsuario(f"Grupo {nome}: {e}") from e
        if not saida:
            raise ErroUsuario("Marque os pontos de cada grupo (A, e B se quiser o contato).")
        if "A" in saida and "B" in saida:
            saida["contato"] = mpr.contato(saida["A"], saida["B"])
        return saida

    @resposta_segura
    def consolidado_projeto(self):
        """Cada tipo de dado: de onde vem, onde fica no banco, onde é usado e quantos poços o têm."""
        from motor import consolidado as mco
        self._exigir_projeto()
        return mco.projeto(self._banco)

    @resposta_segura
    def consolidado_poco(self, poco: str):
        """Os valores de cada fonte, lado a lado, para um poço (qualquer grafia do nome)."""
        from motor import consolidado as mco
        self._exigir_projeto()
        if not str(poco or "").strip():
            raise ErroUsuario("Informe o poço.")
        return mco.poco(self._banco, mpo.resolver(self._banco, poco))

    @resposta_segura
    def exportar_checkshot(self, poco: str):
        """Tabela tempo × profundidade do checkshot em CSV (exportacoes/<poço>/), para levar à sísmica."""
        from motor import checkshot as mck
        self._exigir_projeto()
        pid = mpo.resolver(self._banco, poco)
        cks = self._dados_poco_ficha(pid)["checkshot"]
        if not cks:
            raise ErroUsuario("Este poço não tem checkshot lido (SEG-Y da pasta Sismica de Poco).")
        pasta = os.path.join(self._projeto.pasta_de("exportacoes"), mp.nome_seguro(pid))
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, "checkshot_tempo_profundidade.csv")
        with open(saida, "w", encoding="utf-8", newline="\n") as f:
            f.write(mck.csv(cks[0]["niveis"], pid))
        self._projeto.registrar("exportou_checkshot", poco=pid, saida=self._projeto.rel(saida))
        return {"arquivo": self._projeto.rel(saida).replace(os.sep, "/"), "niveis": len(cks[0]["niveis"])}

    @resposta_segura
    def reler_dados_poco(self, poco: str):
        """Lê de novo os formulários do poço (ex.: depois de um leitor melhor)."""
        self._exigir_projeto()
        pid = mpo.resolver(self._banco, poco)
        lidos = [r for a in self._banco.arquivos(pid)
                 if (r := self._ler_dados_poco(a["rel"], pid, a.get("sha256")))]
        return {"lidos": len(lidos), "itens": sum(r["n"] for r in lidos),
                "erros": [r["rel"] for r in lidos if r["erro"]], "dados_poco": self._dados_poco_ficha(pid)}

    @resposta_segura
    def pocos_posicoes(self, ids: list):
        """Coordenadas de poços pelo nome (qualquer grafia): para destacar no mapa mesmo fora do filtro."""
        self._exigir_projeto()
        saida, faltam = [], []
        with self._banco.conexao() as c:
            for nome in ids[:200]:
                pid = mpo.resolver(self._banco, str(nome).strip())
                r = c.execute("SELECT id, lat, lon, campo FROM pocos WHERE id = ?", (pid,)).fetchone()
                if r and r["lat"] is not None:
                    saida.append(dict(r))
                else:
                    faltam.append(str(nome).strip())
        return {"pocos": saida, "faltam": faltam}

    @resposta_segura
    def catalogar_bacia(self):
        """Lista TODAS as categorias da bacia conectada e registra cada pasta de
        poço no banco (sem baixar nada). Permite marcar no mapa o que tem dado."""
        cliente, _, bacia, base = self._conexao_reate()   # retrato: trocar de bacia no meio não mistura
        _, categorias = cliente.descobrir_categorias()
        total = 0
        for i, cat in enumerate(categorias, 1):
            self._status(f"Catalogando {bacia}: {cat['nome']} ({i} de {len(categorias)})…")
            r = cliente.listar_pocos(base + cat["nome"], progresso=self._status)
            self._projeto.salvar_pocos(bacia, cat["nome"], r["pocos"], r["arquivos_soltos"],
                                       partes=r["partes"], duplicados=r["duplicados"])
            total += mpo.registrar_reate(self._banco, bacia, cat["nome"], r["pocos"], substituir=True)
        self._projeto.registrar("catalogou_bacia", bacia=bacia, pocos=total)
        return {"bacia": bacia, "categorias": len(categorias), "pocos": total}
