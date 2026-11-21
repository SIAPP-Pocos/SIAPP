"""
Versão nova do SIAPP (1.3): procurar, baixar e instalar sem sair do programa.

O SIAPP instalado pergunta ao GitHub qual é a última versão publicada em SIAPP-Pocos/SIAPP (Releases), no
máximo uma vez por dia. Se for mais nova que a que está rodando, a interface avisa e, com um clique:

  1. baixa o instalador da versão (SIAPP-X.Y.Z-instalador.exe) para a pasta temporária do Windows e confere o
     tamanho e o SHA-256 que o GitHub publica para o arquivo;
  2. abre o instalador sem perguntas (/SILENT: só a barra de progresso) e fecha o SIAPP;
  3. o instalador troca os arquivos do programa e abre o SIAPP de novo (parâmetro /REABRIR, em siapp.iss).

Os projetos não mudam: ficam na pasta escolhida na primeira instalação (o instalador a reaproveita).
Rodando do código (clone do GitHub), só avisa e mostra a página da versão.
"""

from __future__ import annotations

import hashlib
import os
import re

import requests

REPOSITORIO = "SIAPP-Pocos/SIAPP"
URL_ULTIMA = f"https://api.github.com/repos/{REPOSITORIO}/releases/latest"
PAGINA_VERSOES = f"https://github.com/{REPOSITORIO}/releases/latest"
RE_INSTALADOR = re.compile(r"^SIAPP-(\d+\.\d+\.\d+)-instalador\.exe$")
# /SILENT: sem perguntas, só a barra de progresso; /REABRIR: o instalador abre o SIAPP no fim (siapp.iss)
PARAMETROS_INSTALADOR = ("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/REABRIR")
TAMANHO_MAXIMO = 600 * 1024 * 1024


class ErroAtualizacao(ValueError):
    """Falha esperada, com mensagem para o usuário."""


def versao_tupla(v: str) -> tuple:
    """"v1.10.2" → (1, 10, 2). O que não for número conta como 0 (nunca quebra a comparação)."""
    partes = re.findall(r"\d+", str(v or "").split("-")[0].split("+")[0])
    return tuple(int(x) for x in (partes + ["0", "0", "0"])[:3])


def mais_nova(candidata: str, atual: str) -> bool:
    return versao_tupla(candidata) > versao_tupla(atual)


def notas_limpas(corpo: str, limite: int = 6000) -> str:
    """O texto da versão no GitHub, sem o rodapé de instalação e da assinatura (depois do primeiro "---")."""
    texto = (corpo or "").replace("\r\n", "\n")
    texto = re.split(r"\n-{3,}\s*\n", texto, maxsplit=1)[0].strip()
    return texto[:limite]


def consultar(versao_atual: str, url: str = URL_ULTIMA, timeout: float = 10) -> dict | None:
    """A última versão publicada. None quando ainda não há nenhuma."""
    try:
        r = requests.get(url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
    except requests.exceptions.RequestException as e:
        raise ErroAtualizacao(f"Sem conexão com o GitHub ({type(e).__name__}).") from e
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise ErroAtualizacao(f"O GitHub respondeu HTTP {r.status_code}.")
    rel = r.json()
    versao = str(rel.get("tag_name") or "").lstrip("vV")
    instalador = None
    for a in rel.get("assets", []):
        m = RE_INSTALADOR.match(a.get("name") or "")
        if m and m.group(1) == versao:
            digest = str(a.get("digest") or "")
            instalador = {"nome": a["name"], "url": a.get("browser_download_url") or "",
                          "bytes": int(a.get("size") or 0),
                          "sha256": digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else ""}
            break
    return {"versao": versao, "atual": versao_atual, "nova": bool(versao) and mais_nova(versao, versao_atual),
            "publicada_em": rel.get("published_at") or "", "notas": notas_limpas(rel.get("body") or ""),
            "pagina": rel.get("html_url") or PAGINA_VERSOES, "instalador": instalador}


def _sha256(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _confere(caminho: str, inst: dict) -> bool:
    if not os.path.isfile(caminho):
        return False
    if inst.get("bytes") and os.path.getsize(caminho) != inst["bytes"]:
        return False
    return not inst.get("sha256") or _sha256(caminho) == inst["sha256"]


def baixar(info: dict, pasta: str, progresso=lambda feito, total: None, timeout: float = 60) -> str:
    """Baixa o instalador da versão para `pasta` e confere tamanho e SHA-256. Se já estiver lá, conferido, reaproveita."""
    inst = (info or {}).get("instalador")
    if not inst or not inst.get("url"):
        raise ErroAtualizacao("Esta versão ainda não tem o instalador anexado. Tente de novo daqui a alguns minutos.")
    if inst.get("bytes", 0) > TAMANHO_MAXIMO:
        raise ErroAtualizacao("O instalador anunciado é grande demais; baixe pela página da versão.")
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, inst["nome"])
    if _confere(destino, inst):
        progresso(inst.get("bytes", 0), inst.get("bytes", 0))
        return destino
    parcial = destino + ".part"
    try:
        with requests.get(inst["url"], stream=True, timeout=(30, timeout)) as r:
            r.raise_for_status()
            total = inst.get("bytes") or int(r.headers.get("Content-Length") or 0)
            feito = 0
            with open(parcial, "wb") as f:
                for bloco in r.iter_content(512 * 1024):
                    f.write(bloco)
                    feito += len(bloco)
                    if feito > TAMANHO_MAXIMO:
                        raise ErroAtualizacao("O download passou do tamanho esperado e foi interrompido.")
                    progresso(feito, total)
    except requests.exceptions.RequestException as e:
        raise ErroAtualizacao(f"O download parou ({type(e).__name__}). Tente de novo.") from e
    if not _confere(parcial, inst):
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise ErroAtualizacao("O arquivo baixado não confere com o publicado no GitHub (tamanho ou SHA-256). "
                              "Nada foi instalado; tente de novo.")
    os.replace(parcial, destino)
    return destino


def comando_instalar(caminho: str) -> list[str]:
    return [caminho, *PARAMETROS_INSTALADOR]
