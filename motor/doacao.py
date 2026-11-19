"""Tela "Apoie o projeto" (0.67; 1.3 com quem faz o SIAPP, valores e QR Code): lê `recursos/doacao.json` e monta o
Pix "copia e cola".

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
# 1.3: botões de valor da tela (o doador também pode digitar outro). Trocáveis em doacao.json › "valores".
VALORES_PADRAO = [{"rotulo": "Um cafezinho", "valor": 5}, {"rotulo": "Um lanche", "valor": 15},
                  {"rotulo": "Uma tarde de código", "valor": 30}]
VALOR_MAXIMO = 10000.0
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


def tipo_da_chave(chave: str) -> str:
    """Rótulo do tipo de chave Pix, só para a tela: celular (+55…), e-mail, CPF, CNPJ ou aleatória."""
    c = (chave or "").strip()
    if re.fullmatch(r"\+55\d{10,11}", c):
        return "celular"
    if "@" in c:
        return "e-mail"
    if re.fullmatch(r"\d{11}", c):
        return "CPF"
    if re.fullmatch(r"\d{14}", c):
        return "CNPJ"
    return "aleatória"


def _link_valido(url: str) -> bool:
    return bool(re.match(r"^https://[^\s/]+\.[^\s]+$", url or ""))


def _linkedin_valido(url: str) -> bool:
    return bool(re.match(r"^https://([a-z]{2,3}\.)?linkedin\.com/in/[^\s/?#]+/?$", url or ""))


def valor_valido(valor) -> float | None:
    """Valor de um Pix da tela: número > 0 e até VALOR_MAXIMO, em centavos ("12,5" vale). Fora disso, None."""
    try:
        v = round(float(str(valor).strip().replace(",", ".")), 2)
    except (TypeError, ValueError):
        return None
    return v if 0 < v <= VALOR_MAXIMO else None


def qr_svg(texto: str) -> str | None:
    """QR Code do Pix em SVG (1.3), para o doador apontar a câmera do celular. Usa o segno (BSD-3-Clause, sem
    internet); sem ele, None e a tela mostra só o "copia e cola"."""
    try:
        import segno
    except ImportError:
        return None
    import io
    saida = io.BytesIO()
    # com o namespace: a tela usa o SVG como imagem (data:image/svg+xml), e sem ele o navegador não desenha
    segno.make(texto, error="m", micro=False).save(saida, kind="svg", scale=6, border=2, dark="#12262A",
                                                    light="#FFFFFF", xmldecl=False, svgns=True)
    return saida.getvalue().decode("utf-8")


def pix_com_valor(config: dict, valor) -> dict:
    """{"valor", "copia_e_cola", "qr_svg"} do Pix da tela com o valor escolhido (None = o doador digita no banco)."""
    pix = (config or {}).get("pix")
    if not pix:
        raise ValueError("a doação por Pix não está configurada")
    v = None
    if valor not in (None, "", 0):
        v = valor_valido(valor)
        if v is None:
            raise ValueError(f"valor inválido (use um número entre 0,01 e {VALOR_MAXIMO:.0f})")
    codigo = pix_copia_e_cola(pix["chave"], pix["nome"], pix["cidade"], v)
    return {"valor": v, "copia_e_cola": codigo, "qr_svg": qr_svg(codigo)}


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
            pix["tipo"] = tipo_da_chave(pix["chave"])
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
    # 1.3: "quem faz o SIAPP" (parágrafos), o LinkedIn do autor e os botões de valor
    sobre = dados.get("sobre") or []
    if isinstance(sobre, str):
        sobre = [sobre]
    sobre = [str(s).strip() for s in sobre if str(s).strip()]
    linkedin = str(dados.get("linkedin") or "").strip()
    if linkedin and not _linkedin_valido(linkedin):
        avisos.append(f"LinkedIn ignorado (use https://www.linkedin.com/in/...): {linkedin}")
        linkedin = ""
    publicacoes = []                 # trabalhos dos PIBICs do autor: {titulo, evento, url}
    for item in dados.get("publicacoes") or []:
        if not isinstance(item, dict) or not str(item.get("titulo") or "").strip():
            continue
        url = str(item.get("url") or "").strip()
        if url and not _link_valido(url):
            avisos.append(f"publicação sem link válido (precisa começar com https://): {item.get('titulo')}")
            url = ""
        publicacoes.append({"titulo": str(item["titulo"]).strip(), "evento": str(item.get("evento") or "").strip(),
                            "url": url})
    valores = []
    for item in dados.get("valores") if isinstance(dados.get("valores"), list) else VALORES_PADRAO:
        if isinstance(item, dict) and valor_valido(item.get("valor")) and str(item.get("rotulo") or "").strip():
            valores.append({"rotulo": str(item["rotulo"]).strip(), "valor": valor_valido(item["valor"])})
    return {"ativo": ativo, "titulo": str(dados.get("titulo") or TITULO_PADRAO), "texto": str(dados.get("texto") or TEXTO_PADRAO),
            "pix": pix if ativo else None, "links": links if ativo else [], "sobre": sobre, "linkedin": linkedin, "publicacoes": publicacoes,
            "valores": valores if ativo and pix else [], "avisos": avisos}
