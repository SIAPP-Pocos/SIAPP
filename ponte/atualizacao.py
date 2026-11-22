"""Ponte: versão nova do SIAPP (1.3) — procurar uma vez por dia, baixar, instalar e reabrir sozinho."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from datetime import date

from motor import atualizacao as mat
from motor import projeto as mp

from . import base
from .base import ErroUsuario, resposta_segura

NOME_ESTADO = "versao-nova.json"     # na pasta do projeto principal, como atualizacao.json (fora da marca do projeto)


class AtualizacaoAPI:
    _info_versao = None               # a última consulta ao GitHub (dict de motor.atualizacao.consultar)
    _instalador_baixado = None        # caminho do instalador conferido, pronto para abrir

    # ------------------------------------------------------------ estado guardado
    def _caminho_estado_versao(self) -> str:
        return os.path.join(base.PASTA_PROJETO, NOME_ESTADO)

    def _estado_versao(self) -> dict:
        try:
            with open(self._caminho_estado_versao(), encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _guardar_estado_versao(self, **mudancas) -> None:
        d = {**self._estado_versao(), **mudancas}
        try:
            os.makedirs(base.PASTA_PROJETO, exist_ok=True)
            with open(self._caminho_estado_versao(), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def _pode_instalar(self, info: dict | None) -> bool:
        return bool(base.INSTALADO and sys.platform == "win32" and info and info.get("instalador"))

    def _resposta_versao(self, info: dict | None, consultado_em: str) -> dict:
        if not info:
            return {"publicada": False, "nova": False, "atual": mp.VERSAO_SIAPP, "consultado_em": consultado_em}
        pulada = self._estado_versao().get("pulada") == info["versao"]
        inst = info.get("instalador") or {}
        return {"publicada": True, "nova": bool(info.get("nova")), "pulada": pulada, "versao": info["versao"],
                "atual": mp.VERSAO_SIAPP, "publicada_em": info.get("publicada_em", ""), "notas": info.get("notas", ""),
                "pagina": info.get("pagina") or mat.PAGINA_VERSOES, "bytes": inst.get("bytes", 0),
                "pode_instalar": self._pode_instalar(info), "instalado": base.INSTALADO,
                "de_teste": bool(info.get("de_teste")),
                "consultado_em": consultado_em}

    # ------------------------------------------------------------------ API
    @resposta_segura
    def verificar_versao(self, forcar: bool = False):
        """Há versão nova do SIAPP? Ao abrir, no máximo uma consulta por dia (e nenhuma se a pessoa desligou em
        Configurações); `forcar` (Ajuda › Procurar versão nova) consulta na hora."""
        prefs = self._preferencias().ler()
        if not forcar and prefs.get("avisar_versao_nova") is False:
            return {"desligado": True}
        teste = bool(prefs.get("versoes_de_teste"))
        hoje = date.today().isoformat()
        estado = self._estado_versao()
        cache = estado.get("consulta") or {}
        if (forcar or cache.get("dia") != hoje or cache.get("atual") != mp.VERSAO_SIAPP
                or bool(cache.get("teste")) != teste):
            try:
                info = mat.consultar(mp.VERSAO_SIAPP, teste=teste)
            except mat.ErroAtualizacao as e:
                raise ErroUsuario(str(e)) from e
            cache = {"dia": hoje, "atual": mp.VERSAO_SIAPP, "teste": teste, "info": info}
            self._guardar_estado_versao(consulta=cache)
        self._info_versao = cache.get("info")
        return self._resposta_versao(self._info_versao, cache["dia"])

    @resposta_segura
    def pular_versao(self, versao: str):
        """"Pular esta versão": não avisa mais desta (avisa da próxima)."""
        self._guardar_estado_versao(pulada=str(versao or ""))
        return {}

    @resposta_segura
    def baixar_versao(self):
        """Baixa o instalador da versão nova (conferido pelo SHA-256 do GitHub). O progresso vai para a barra de baixo."""
        info = self._info_versao
        if not info or not info.get("nova"):
            raise ErroUsuario("Procure a versão nova de novo (Ajuda › Procurar versão nova).")
        if not self._pode_instalar(info):
            raise ErroUsuario("Daqui só dá para atualizar o SIAPP instalado. Baixe pela página da versão.")
        total_mb = max(1, round((info["instalador"].get("bytes") or 0) / 1e6))
        ultimo = [-1]

        def progresso(feito, total):
            pct = int(100 * feito / total) if total else 0
            if pct != ultimo[0]:
                ultimo[0] = pct
                self._status(f"Baixando o SIAPP {info['versao']}… {pct}% de {total_mb} MB")
        pasta = os.path.join(tempfile.gettempdir(), "SIAPP-atualizacao")
        try:
            self._instalador_baixado = mat.baixar(info, pasta, progresso)
        except mat.ErroAtualizacao as e:
            raise ErroUsuario(str(e)) from e
        return {"pronto": True, "versao": info["versao"]}

    @resposta_segura
    def instalar_versao(self):
        """Abre o instalador baixado (sem perguntas) e fecha o SIAPP; o instalador abre o SIAPP de novo no fim."""
        caminho, info = self._instalador_baixado, self._info_versao
        if not caminho or not os.path.isfile(caminho) or not info:
            raise ErroUsuario("Baixe a versão nova primeiro.")
        if not self._pode_instalar(info):
            raise ErroUsuario("Daqui só dá para atualizar o SIAPP instalado.")
        self._guardar_estado_versao(instalando={"de": mp.VERSAO_SIAPP, "para": info["versao"]})
        extra = {"creationflags": 0x00000008 | 0x00000200} if sys.platform == "win32" else {}   # desligado do SIAPP
        subprocess.Popen(mat.comando_instalar(caminho), cwd=os.path.dirname(caminho), close_fds=True, **extra)

        def fechar():            # fechar a principal fecha as destacadas e lembra quais eram (_ao_fechar_principal)
            try:
                self._janela.destroy()
            except Exception:  # noqa: BLE001
                pass
        threading.Timer(1.5, fechar).start()
        return {"fechando": True}

    @resposta_segura
    def trabalho_em_andamento(self):
        """Downloads do REATE ou leitura de documentos rodando agora (antes de fechar para instalar)."""
        downloads = bool(self._fila.ativa) if getattr(self, "_fila", None) else False
        leitura = getattr(getattr(self, "_fila_docs", None), "_thread", None) is not None
        return {"downloads": downloads, "leitura": leitura}

    def _aviso_pos_atualizacao(self) -> dict | None:
        """Depois que o instalador trocou a versão: "SIAPP atualizado: 1.3.0 → 1.4.0" uma vez."""
        estado = self._estado_versao()
        vista = estado.get("ultima_aberta")
        aviso = None
        if vista and mat.mais_nova(mp.VERSAO_SIAPP, vista):
            aviso = {"de": vista, "para": mp.VERSAO_SIAPP}
        if vista != mp.VERSAO_SIAPP or "instalando" in estado:
            estado.pop("instalando", None)
            estado["ultima_aberta"] = mp.VERSAO_SIAPP
            try:
                with open(self._caminho_estado_versao(), "w", encoding="utf-8") as f:
                    json.dump(estado, f, ensure_ascii=False, indent=1)
            except OSError:
                pass
        return aviso
