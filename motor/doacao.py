"""Tela "Apoie o projeto" (0.67): lê `recursos/doacao.json` e monta o Pix "copia e cola".

O SIAPP é e continua gratuito. A tela de doação só aparece quando o autor preenche `recursos/doacao.json` com uma chave
Pix ou um endereço (link) de doação; vazio ou com `"ativo": false`, nada aparece. Nada aqui é inventado: os dados
vêm só desse arquivo.

O código "copia e cola" segue o BR Code estático do Pix (padrão EMV, Manual de Padrões para Iniciação do Pix, do Banco
Central): campos ID + tamanho + valor, e no fim o CRC16-CCITT (polinômio 0x1021, valor inicial 0xFFFF) do texto todo.
Fonte: https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Regulamento_Pix/II_ManualdePadroesparaIniciacaodoPix.pdf
(o teste usa o exemplo de BR Code estático desse manual).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata

CAMINHO_PADRAO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos", "doacao.json")

TITULO_PADRAO = "Apoie o SIAPP"
TEXTO_PADRAO = ("O SIAPP é gratuito e de código aberto, feito para estudantes e pesquisadores. Se ele foi útil para "
                "você, uma doação ajuda a manter o projeto. Doar é opcional: o SIAPP continua igual para todos.")


def _campo(ident: str, valor: str) -> str:
    if len(valor) > 99:
        raise ValueError(f"campo {ident} grande demais para o BR Code ({len(valor)} caracteres)")
    return f"{ident}{len(valor):02d}{valor}"


def _crc16(texto: str) -> str:
    crc = 0xFFFF
    for byte in texto.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _simples(texto: str, limite: int) -> str:
    """Nome e cidade do recebedor: sem acentos (alguns bancos recusam), no tamanho que o padrão aceita."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t).strip()[:limite]


def pix_copia_e_cola(chave: str, nome: str, cidade: str, valor: float | None = None, txid: str = "***") -> str:
    """BR Code estático do Pix para a chave dada (o doador escolhe o valor, se `valor` for None)."""
    chave = (chave or "").strip()
    nome, cidade = _simples(nome, 25), _simples(cidade, 15)
    if not chave or not nome or not cidade:
        raise ValueError("o Pix precisa de chave, nome e cidade do recebedor")
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", chave)
    partes = [_campo("00", "01"), _campo("26", conta), _campo("52", "0000"), _campo("53", "986")]
    if valor:
        partes.append(_campo("54", f"{float(valor):.2f}"))
    partes += [_campo("58", "BR"), _campo("59", nome), _campo("60", cidade),
               _campo("62", _campo("05", re.sub(r"[^A-Za-z0-9*]", "", txid)[:25] or "***"))]
    texto = "".join(partes) + "6304"
    return texto + _crc16(texto)


def _link_valido(url: str) -> bool:
    return bool(re.match(r"^https://[^\s/]+\.[^\s]+$", url or ""))


def ler(caminho: str = CAMINHO_PADRAO) -> dict:
    """{"ativo", "titulo", "texto", "pix": {chave, nome, cidade, copia_e_cola} | None, "links": [{rotulo, url}],
    "avisos": [...]}. `ativo` só é True se houver chave Pix completa ou ao menos um link https válido."""
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        dados = {}
    if not isinstance(dados, dict):
        dados = {}
    avisos = []
    pix = None
    p = dados.get("pix") or {}
    if isinstance(p, dict) and str(p.get("chave") or "").strip():
        try:
            pix = {"chave": str(p["chave"]).strip(), "nome": str(p.get("nome") or "").strip(),
                   "cidade": str(p.get("cidade") or "").strip()}
            pix["copia_e_cola"] = pix_copia_e_cola(pix["chave"], pix["nome"], pix["cidade"])
        except ValueError as e:
            avisos.append(f"Pix: {e}")
            pix = None
    links = []
    for item in dados.get("links") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if _link_valido(url):
            links.append({"rotulo": str(item.get("rotulo") or url).strip(), "url": url})
        elif url:
            avisos.append(f"link ignorado (precisa começar com https://): {url}")
    ativo = bool(dados.get("ativo", True)) and bool(pix or links)
    return {"ativo": ativo, "titulo": str(dados.get("titulo") or TITULO_PADRAO), "texto": str(dados.get("texto") or TEXTO_PADRAO),
            "pix": pix if ativo else None, "links": links if ativo else [], "avisos": avisos}
