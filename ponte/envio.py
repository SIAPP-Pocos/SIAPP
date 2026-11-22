"""Ponte: enviar a contribuição para a base comunitária pelo GitHub, direto do SIAPP (1.4)."""

from __future__ import annotations

import json
import time

from motor import comunidade as mc
from motor import envio as me
from motor import projeto as mp
from motor.cofre import Cofre

from .base import ErroUsuario, resposta_segura

PASTA_CONTRIBUICOES = "contribuicoes"
PASTA_COFRE = None                 # None: %LOCALAPPDATA%\SIAPP (os testes trocam por uma pasta temporária)
INTERVALO_SITUACAO = 120           # segundos entre duas consultas da situação de um mesmo envio


def _erro(e: Exception) -> ErroUsuario:
    return ErroUsuario(str(e))


class EnvioAPI:
    _login_github = None
    _login_cancelado = False

    # ------------------------------------------------------------ conta do GitHub
    def _cofre_github(self) -> Cofre:
        return Cofre(PASTA_COFRE)

    def _token_github(self) -> str | None:
        """O acesso guardado, renovado se venceu (vale 8 h; a renovação, 6 meses). None se precisa entrar de novo."""
        cofre = self._cofre_github()
        d = cofre.ler()
        if not d or not d.get("access_token"):
            return None
        agora = time.time()
        if d.get("expira_em", 0) > agora:
            return d["access_token"]
        if d.get("refresh_token") and d.get("renovar_ate", 0) > agora:
            try:
                novo = me.renovar(d["refresh_token"])
            except me.ErroEnvio:
                return None
            cofre.gravar({**d, **novo})
            return novo["access_token"]
        return None

    @resposta_segura
    def github_conta(self):
        d = self._cofre_github().ler() or {}
        return {"conectado": bool(d.get("access_token")), "login": d.get("login", ""), "nome": d.get("nome", "")}

    @resposta_segura
    def github_entrar(self):
        """Passo 1 da entrada: o código que a pessoa digita em github.com/login/device."""
        try:
            self._login_github = me.iniciar_login()
        except me.ErroEnvio as e:
            raise _erro(e) from e
        self._login_cancelado = False
        return {"codigo": self._login_github["codigo"], "url": self._login_github["url"],
                "expira_em_s": self._login_github["expira_em_s"]}

    @resposta_segura
    def github_aguardar(self):
        """Passo 2: espera a autorização (a interface chama logo depois de mostrar o código)."""
        info = self._login_github
        if not info:
            raise ErroUsuario("Clique em Entrar com o GitHub de novo.")
        try:
            tokens = me.aguardar_login(info["device_code"], info["intervalo"], info["expira_em_s"],
                                       cancelado=lambda: self._login_cancelado)
            conta = me.usuario(tokens["access_token"])
        except me.ErroEnvio as e:
            raise _erro(e) from e
        finally:
            self._login_github = None
        self._cofre_github().gravar({**tokens, **conta})
        return {"login": conta["login"], "nome": conta["nome"]}

    @resposta_segura
    def github_cancelar(self):
        self._login_cancelado = True
        return {}

    @resposta_segura
    def github_sair(self):
        self._cofre_github().apagar()
        return {}

    # ------------------------------------------------------------ envio
    def _pacote_para_envio(self, apenas_novos: bool) -> dict:
        self._exigir_projeto()
        try:
            pacote = mc.montar_pacote(self._banco, self._projeto.config.get("autor") or {}, mp.VERSAO_SIAPP,
                                      apenas_novos=bool(apenas_novos))
        except mc.ErroComunidade as e:
            raise _erro(e) from e
        if mc.pacote_vazio(pacote):
            raise ErroUsuario("Nada novo para enviar desde a última vez." if apenas_novos
                              else "Ainda não há correções nem dados feitos neste computador.")
        return pacote

    @staticmethod
    def _pocos(pacote: dict) -> list[str]:
        return sorted({x["poco"] for x in pacote.get("fatos", []) + pacote.get("interpretacoes", []) if x.get("poco")})

    @resposta_segura
    def previa_envio(self, apenas_novos: bool = True):
        """O que vai, de quem e por qual conta, antes de confirmar (nada é enviado)."""
        pacote = self._pacote_para_envio(apenas_novos)
        return {"itens": mc.contar_itens(pacote), "pocos": self._pocos(pacote), "autor": pacote["autor"],
                "conta": self.github_conta()}

    def _envios(self) -> list[dict]:
        try:
            v = json.loads(self._banco.meta("envios_comunidade") or "[]")
            return v if isinstance(v, list) else []
        except ValueError:
            return []

    def _guardar_envios(self, envios: list[dict]) -> None:
        self._banco.definir_meta("envios_comunidade", json.dumps(envios[:100], ensure_ascii=False))

    @resposta_segura
    def enviar_comunidade(self, apenas_novos: bool = True):
        token = self._token_github()
        if not token:
            raise ErroUsuario("Entre com a conta do GitHub primeiro.")
        pacote = self._pacote_para_envio(apenas_novos)
        itens, pocos = mc.contar_itens(pacote), self._pocos(pacote)
        try:
            r = me.enviar(token, pacote, itens, pocos,
                          progresso=lambda i, n: self._status(f"Enviando para a comunidade… parte {i} de {n}"))
        except me.ErroEnvio as e:
            raise _erro(e) from e
        # uma cópia fica na pasta, e o que foi enviado não vai de novo no próximo pacote
        caminho = mc.gravar_pacote(self._banco, pacote, self._projeto.pasta_de(PASTA_CONTRIBUICOES))
        registro = {"numero": r["numero"], "url": r["url"], "pacote": pacote["id"], "enviado_em": pacote["criado_em"],
                    "itens": itens, "pocos": pocos[:50], "estado": "conferindo", "rotulo": "Recebido, sendo conferido",
                    "verificado_em": time.time()}                # acabou de sair: confere depois
        self._guardar_envios([registro, *self._envios()])
        self._projeto.registrar("enviou_contribuicao", pacote=pacote["id"], issue=r["numero"], **itens)
        return {"numero": r["numero"], "url": r["url"], "itens": itens, "arquivo": self._projeto.rel(caminho)}

    @resposta_segura
    def envios_comunidade(self, atualizar: bool = True):
        """Os envios deste projeto e onde cada um está (pergunta ao GitHub os que ainda não terminaram)."""
        self._exigir_projeto()
        envios, mudou = self._envios(), []
        pendentes = [e for e in envios if e.get("estado") not in me.FINAIS]
        if atualizar and pendentes:
            token, agora = self._token_github(), time.time()
            for e in pendentes:
                if agora - e.get("verificado_em", 0) < INTERVALO_SITUACAO:
                    continue
                try:
                    s = me.situacao(e["numero"], token)
                except me.ErroEnvio:
                    break                          # sem internet ou limite do GitHub: tenta na próxima
                if s["estado"] != e.get("estado"):
                    mudou.append({"numero": e["numero"], **s})
                e.update(s)
                e["verificado_em"] = agora
            self._guardar_envios(envios)
        return {"envios": envios[:20], "mudou": mudou}
