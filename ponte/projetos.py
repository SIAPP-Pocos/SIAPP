"""Projetos e tela inicial (0.58): lista de projetos, criar, abrir outro, e o estado de cada módulo."""
from __future__ import annotations

import os
import subprocess
import sys
import threading

from motor import projetos as mpj

from . import base
from .base import ErroUsuario, resposta_segura


class ProjetosAPI:
    # ------------------------------------------------------------ lista e cartões
    @staticmethod
    def _raiz_app() -> str:
        """Onde fica a pasta projetos/: ao lado do ambiente_teste (a pasta do app, fora dos testes)."""
        return os.path.dirname(os.path.abspath(base.PASTA_PROJETO))

    def _pastas_projetos(self) -> list[str]:
        prefs = self._preferencias().ler()
        return mpj.conhecidos(base.PASTA_PROJETO, prefs.get("projetos", []), self._raiz_app())

    def _projeto_inicial(self) -> str:
        """A pasta que abre ao iniciar: a última escolhida, se ainda é um projeto; senão, a principal."""
        atual = self._preferencias().ler().get("projeto_atual") or ""
        return atual if atual and mpj.eh_projeto(atual) else base.PASTA_PROJETO

    @resposta_segura
    def projetos(self):
        aberto = self._projeto.pasta if self._projeto else ""
        lista = [mpj.resumo(p, base.PASTA_PROJETO) for p in self._pastas_projetos()]
        for r in lista:
            r["aberto"] = bool(aberto) and os.path.normcase(r["pasta"]) == os.path.normcase(aberto)
        return {"projetos": lista, "aberto": aberto}

    @resposta_segura
    def projeto_criar(self, nome: str, bacias: list | None = None):
        try:
            pasta = mpj.criar(self._raiz_app(), nome, bacias)
        except mpj.ErroProjeto as e:
            raise ErroUsuario(str(e)) from e
        prefs = self._preferencias().ler()
        self._preferencias().atualizar({"projetos": [*prefs.get("projetos", []), pasta]})
        return {"pasta": pasta, "nome": mpj.nome_do_projeto(pasta)}

    @resposta_segura
    def projeto_renomear(self, pasta: str, nome: str):
        if not any(os.path.normcase(pasta) == os.path.normcase(p) for p in self._pastas_projetos()):
            raise ErroUsuario("Projeto desconhecido.")
        try:
            return {"nome": mpj.renomear(pasta, nome)}
        except mpj.ErroProjeto as e:
            raise ErroUsuario(str(e)) from e

    # ------------------------------------------------------------ trocar de projeto
    def _ocupado(self) -> str:
        if self._fila.ativa:
            return "Há downloads em andamento"
        if getattr(self._fila_docs, "_thread", None) is not None:
            return "Há documentos sendo processados (OCR)"
        return ""

    @resposta_segura
    def projeto_abrir(self, pasta: str):
        """Abre outro projeto. Com um projeto já aberto, o SIAPP reabre (tudo começa limpo no projeto novo)."""
        conhecidos = self._pastas_projetos()
        alvo = next((p for p in conhecidos if os.path.normcase(p) == os.path.normcase(os.path.abspath(pasta or ""))), None)
        if alvo is None or not (mpj.eh_projeto(alvo) or alvo == base.PASTA_PROJETO):
            raise ErroUsuario("Esse projeto não foi encontrado (a pasta foi movida ou apagada?).")
        if self._projeto is not None and os.path.normcase(self._projeto.pasta) == os.path.normcase(alvo):
            return {"pasta": alvo, "ja_aberto": True}
        motivo = self._ocupado()
        if motivo:
            raise ErroUsuario(f"{motivo}. Espere terminar (ou cancele) antes de trocar de projeto.")
        self._preferencias().atualizar({"projeto_atual": "" if alvo == base.PASTA_PROJETO else alvo})
        if self._projeto is None:
            os.makedirs(alvo, exist_ok=True)
            return self._abrir_projeto(alvo)
        self._reiniciar()
        return {"pasta": alvo, "reiniciando": True}

    def _reiniciar(self):
        """Fecha esta instância e abre outra (pelo lançador, quando existe: mesma janelinha de carregamento)."""
        vbs = os.path.join(base.PASTA_APP, "SIAPP.vbs")
        if sys.platform == "win32" and os.path.isfile(vbs):
            cmd = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "wscript.exe"), "//nologo", vbs]
        else:
            cmd = [sys.executable, os.path.join(base.PASTA_APP, "siapp.py")]
        extra = {"creationflags": 0x08000000} if sys.platform == "win32" else {}   # CREATE_NO_WINDOW
        subprocess.Popen(cmd, cwd=base.PASTA_APP, close_fds=True, **extra)

        def fechar():
            try:
                self._janela.destroy()
            except Exception:  # noqa: BLE001
                pass
        threading.Timer(0.6, fechar).start()

    # ------------------------------------------------------------ módulos na tela inicial
    @resposta_segura
    def inicio_resumo(self):
        """Uma ou duas linhas por módulo, com números do projeto aberto, e a ação sugerida."""
        self._exigir_projeto()
        b = self._banco

        def um(sql, args=()):
            with b.leitura() as c:
                r = c.execute(sql, args).fetchone()
            return (r[0] if r and r[0] is not None else 0) if r else 0

        bacias = [r[0] for r in self._consultar("SELECT bacia, count(*) n FROM acervo_pocos GROUP BY bacia ORDER BY n DESC")]
        lev = um("SELECT count(DISTINCT poco_id) FROM acervo_pocos WHERE poco_id IS NOT NULL")
        listados = um("SELECT count(*) FROM acervo_arquivos")
        baixados = um("SELECT count(*) FROM arquivos")
        docs = um("SELECT count(*) FROM arquivos WHERE tipo = 'documento'")
        com_texto = len(self._projeto.resumo_texto())
        perfis = um("SELECT count(*) FROM arquivos WHERE tipo = 'perfil'")
        lidos = um("SELECT count(*) FROM perfis WHERE erro IS NULL OR erro = ''")
        cadastro = um("SELECT count(*) FROM pocos")
        com_topos = um("SELECT count(DISTINCT poco_id) FROM agp_unidades WHERE poco_id IS NOT NULL")
        from motor import bloco as mbl
        from motor import secao as msc
        pasta_exec = self._projeto.pasta_de("execucoes")
        secoes, blocos = msc.execucoes(pasta_exec), mbl.execucoes(pasta_exec)
        return {
            "dados": {"bacias": [x for x in bacias if x], "pocos": lev, "listados": listados, "baixados": baixados},
            "docs": {"total": docs, "com_texto": com_texto, "sem_texto": max(0, docs - com_texto)},
            "perfis": {"total": perfis, "lidos": min(lidos, perfis) if perfis else lidos},
            "mapa": {"cadastro": cadastro, "com_topos": com_topos},
            "secao": {"n": len(secoes), "ultima": ({"quando": secoes[0]["criado_em"], "pocos": len(secoes[0]["pocos"])}
                                                   if secoes else None)},
            "bloco": {"n": len(blocos), "ultimo": ({"quando": blocos[0]["criado_em"], "pocos": blocos[0]["n_pocos"]}
                                                   if blocos else None)},
        }

    def _consultar(self, sql: str, args=()):
        with self._banco.leitura() as c:
            return c.execute(sql, args).fetchall()
