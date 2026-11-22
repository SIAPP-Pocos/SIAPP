"""
Enviar um pacote para a base comunitária direto do SIAPP (1.4).

Conta do GitHub, entrada por código ("device flow" do aplicativo SIAPP Comunidade, instalado só no repositório
SIAPP-Pocos/Comunidade, com permissão de abrir issues e ler pull requests):
  1. iniciar_login() pede um código ao GitHub (ex.: ABCD-1234); a pessoa abre github.com/login/device, digita o
     código e autoriza;
  2. aguardar_login() pergunta ao GitHub, no intervalo que ele pede, até a autorização sair;
  3. o acesso vale 8 horas e se renova sozinho por até 6 meses (renovar()).

Envio: enviar() abre uma issue no repositório Comunidade com um resumo legível e a marca
<!-- siapp-pacote id=… partes=n sha256=… -->, e põe o pacote (JSON → gzip → base64) em n comentários
(<!-- siapp-parte i/n -->). Lá, o workflow "receber pacote" (ferramentas/receber_pacote.py) junta, confere o
SHA-256, valida e abre o pull request no nome de quem enviou. situacao() acompanha: em conferência, em revisão,
mudança pedida, aceito, recusado.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import time

import requests

CLIENT_ID = "Iv23li7rXpFQ6QDmTudr"        # aplicativo "SIAPP Comunidade" da organização SIAPP-Pocos (público)
REPOSITORIO = "SIAPP-Pocos/Comunidade"
API = "https://api.github.com"
URL_CODIGO = "https://github.com/login/device/code"
URL_TOKEN = "https://github.com/login/oauth/access_token"
TAMANHO_PARTE = 60_000                     # um comentário aceita até 65.536 caracteres
MAX_PARTES = 200


class ErroEnvio(ValueError):
    """Falha esperada, com mensagem para o usuário."""


def _post(url: str, dados: dict, timeout: float = 20) -> dict:
    try:
        r = requests.post(url, data=dados, headers={"Accept": "application/json"}, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise ErroEnvio(f"Sem conexão com o GitHub ({type(e).__name__}).") from e
    try:
        return r.json()
    except ValueError as e:
        raise ErroEnvio(f"O GitHub respondeu HTTP {r.status_code}.") from e


def _api(metodo: str, caminho: str, token: str | None = None, json_: dict | None = None, timeout: float = 30):
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        r = requests.request(metodo, API + caminho, headers=h, json=json_, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise ErroEnvio(f"Sem conexão com o GitHub ({type(e).__name__}).") from e
    if r.status_code == 401:
        raise ErroEnvio("A conta do GitHub precisa entrar de novo.", ) from None
    if r.status_code == 403 and "rate limit" in r.text.lower():
        raise ErroEnvio("O GitHub pediu uma pausa (limite de consultas). Tente daqui a pouco.")
    if r.status_code == 403 and "not accessible by integration" in r.text.lower():
        raise ErroEnvio("O GitHub ainda não deixa o SIAPP abrir pedidos na base comunitária (falta uma permissão do "
                        "lado do mantenedor). Nada foi enviado; o seu trabalho continua aqui. Tente de novo mais tarde "
                        "ou use Exportar pacote.")
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", "")
        except ValueError:
            msg = ""
        raise ErroEnvio(f"O GitHub recusou ({r.status_code}{': ' + msg if msg else ''}).")
    return r.json() if r.content else {}


# ------------------------------------------------------------------ conta
def _tokens(r: dict, agora: float) -> dict:
    return {"access_token": r["access_token"], "refresh_token": r.get("refresh_token", ""),
            "expira_em": agora + int(r.get("expires_in") or 8 * 3600) - 120,
            "renovar_ate": agora + int(r.get("refresh_token_expires_in") or 0) if r.get("refresh_token") else 0}


def iniciar_login() -> dict:
    r = _post(URL_CODIGO, {"client_id": CLIENT_ID})
    if "device_code" not in r:
        raise ErroEnvio("O GitHub não deu o código de entrada. " + str(r.get("error_description") or ""))
    return {"device_code": r["device_code"], "codigo": r["user_code"],
            "url": r.get("verification_uri") or "https://github.com/login/device",
            "expira_em_s": int(r.get("expires_in") or 900), "intervalo": int(r.get("interval") or 5)}


def aguardar_login(device_code: str, intervalo: int = 5, expira_em_s: int = 900, cancelado=lambda: False,
                   dormir=None, relogio=None) -> dict:
    """Pergunta ao GitHub até a pessoa autorizar. Devolve os tokens; ErroEnvio se negou, expirou ou cancelou."""
    dormir, relogio = dormir or time.sleep, relogio or time.time
    limite = relogio() + expira_em_s
    while relogio() < limite:
        dormir(intervalo)
        if cancelado():
            raise ErroEnvio("Entrada cancelada.")
        r = _post(URL_TOKEN, {"client_id": CLIENT_ID, "device_code": device_code,
                              "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        if "access_token" in r:
            return _tokens(r, relogio())
        erro = r.get("error")
        if erro == "authorization_pending":
            continue
        if erro == "slow_down":
            intervalo = int(r.get("interval") or intervalo + 5)
            continue
        if erro == "access_denied":
            raise ErroEnvio("A autorização foi negada no GitHub.")
        if erro == "expired_token":
            break
        raise ErroEnvio(f"O GitHub não autorizou ({erro or 'resposta inesperada'}).")
    raise ErroEnvio("O código expirou. Clique em Entrar com o GitHub de novo.")


def renovar(refresh_token: str, relogio=time.time) -> dict:
    r = _post(URL_TOKEN, {"client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": refresh_token})
    if "access_token" not in r:
        raise ErroEnvio("O acesso ao GitHub venceu. Entre de novo.")
    return _tokens(r, relogio())


def usuario(token: str) -> dict:
    u = _api("GET", "/user", token)
    return {"login": u.get("login", ""), "nome": u.get("name") or "", "id": u.get("id")}


# ------------------------------------------------------------------ envio
def codificar(pacote: dict) -> tuple[str, list[str]]:
    """(sha256 do JSON, partes em base64 do JSON compactado)."""
    dados = json.dumps(pacote, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(gzip.compress(dados, mtime=0)).decode("ascii")
    partes = [b64[i:i + TAMANHO_PARTE] for i in range(0, len(b64), TAMANHO_PARTE)] or [""]
    if len(partes) > MAX_PARTES:
        raise ErroEnvio("O pacote é grande demais para um envio só. Exporte em partes menores.")
    return hashlib.sha256(dados).hexdigest(), partes


def comentario_parte(i: int, n: int, parte: str) -> str:
    """O formato que o robô do repositório Comunidade lê (ferramentas/receber_pacote.py, RE_PARTE)."""
    return f"<!-- siapp-parte {i}/{n} -->\n```\n{parte}\n```"


def texto_issue(pacote: dict, itens: dict, pocos: list[str], sha: str, n_partes: int) -> tuple[str, str]:
    a = pacote.get("autor") or {}
    quem = a.get("nome", "") + (f" ({a['instituicao']})" if a.get("instituicao") else "")
    def n(q, um, varios):
        return f"{q} {um if q == 1 else varios}"
    partes = [n(itens.get("correcoes", 0), "correção", "correções") if itens.get("correcoes") else "",
              n(itens.get("palavras", 0), "palavra", "palavras") if itens.get("palavras") else "",
              n(itens.get("fatos", 0), "dado transcrito", "dados transcritos") if itens.get("fatos") else "",
              n(itens.get("interpretacoes", 0), "interpretação", "interpretações") if itens.get("interpretacoes") else ""]
    titulo = f"[pacote] {a.get('nome', 'SIAPP')}: {', '.join(p for p in partes if p) or 'vocabulário'}"
    linhas = [f"Pacote de contribuição enviado pelo SIAPP {pacote.get('siapp_versao', '')} por **{quem}**.", "",
              "| Vai na base | Quantidade |", "|---|---|",
              f"| Correções de OCR | {itens.get('correcoes', 0)} |", f"| Palavras do vocabulário | {itens.get('palavras', 0)} |",
              f"| Dados transcritos (fatos) | {itens.get('fatos', 0)} |",
              f"| Interpretações de perfil | {itens.get('interpretacoes', 0)} |", "",
              f"Poços: {', '.join(pocos[:40]) or '—'}{' …' if len(pocos) > 40 else ''}", "",
              "O conteúdo vem nos comentários abaixo. O robô do repositório confere, valida e abre o pull request "
              "para revisão; nada precisa ser feito aqui.", "",
              f"<!-- siapp-pacote id={pacote['id']} partes={n_partes} sha256={sha} -->"]
    return titulo[:250], "\n".join(linhas)


def enviar(token: str, pacote: dict, itens: dict, pocos: list[str], progresso=lambda i, n: None) -> dict:
    sha, partes = codificar(pacote)
    titulo, corpo = texto_issue(pacote, itens, pocos, sha, len(partes))
    issue = _api("POST", f"/repos/{REPOSITORIO}/issues", token, {"title": titulo, "body": corpo})
    numero = issue["number"]
    try:
        for i, p in enumerate(partes, 1):
            _api("POST", f"/repos/{REPOSITORIO}/issues/{numero}/comments", token,
                 {"body": comentario_parte(i, len(partes), p)})
            progresso(i, len(partes))
    except ErroEnvio as e:
        try:                                  # não deixa um envio pela metade aberto
            _api("PATCH", f"/repos/{REPOSITORIO}/issues/{numero}", token, {"state": "closed"})
        except ErroEnvio:
            pass
        raise ErroEnvio(f"O envio parou no meio ({e}). Nada foi para a base; tente de novo.") from e
    return {"numero": numero, "url": issue.get("html_url") or f"https://github.com/{REPOSITORIO}/issues/{numero}",
            "partes": len(partes), "sha256": sha}


RE_PR = re.compile(r"<!--\s*siapp-pr:\s*(\d+)\s*-->")


def situacao(numero: int, token: str | None = None) -> dict:
    """Onde está o envio: conferindo, recusado (com o motivo), em revisão, mudança pedida, aceito ou não aceito."""
    issue = _api("GET", f"/repos/{REPOSITORIO}/issues/{int(numero)}", token)
    comentarios = _api("GET", f"/repos/{REPOSITORIO}/issues/{int(numero)}/comments?per_page=100", token) \
        if issue.get("comments") else []
    robo = [c for c in comentarios if (c.get("user") or {}).get("type") == "Bot"
            or (c.get("user") or {}).get("login", "").endswith("[bot]")]
    for c in reversed(robo):
        corpo = c.get("body") or ""
        if "<!-- siapp-erro -->" in corpo:
            motivo = corpo.split("O pacote não pôde ser recebido:", 1)[-1].split("Nada foi gravado.", 1)[0].strip()
            return {"estado": "recusado", "rotulo": "Não passou na conferência", "detalhe": motivo[:1500],
                    "url": issue.get("html_url")}
        m = RE_PR.search(corpo)
        if m:
            pr = _api("GET", f"/repos/{REPOSITORIO}/pulls/{m.group(1)}", token)
            url = pr.get("html_url")
            if pr.get("merged_at"):
                return {"estado": "aceito", "rotulo": "Aceito: entra na próxima base", "url": url,
                        "aceito_em": pr["merged_at"]}
            if pr.get("state") == "closed":
                return {"estado": "nao_aceito", "rotulo": "Não aceito (veja o comentário do revisor)", "url": url}
            revisoes = _api("GET", f"/repos/{REPOSITORIO}/pulls/{m.group(1)}/reviews", token)
            if revisoes and revisoes[-1].get("state") == "CHANGES_REQUESTED":
                return {"estado": "mudanca", "rotulo": "O revisor pediu uma mudança", "url": url}
            return {"estado": "revisao", "rotulo": "Em revisão", "url": url}
    if issue.get("state") == "closed":
        return {"estado": "nao_aceito", "rotulo": "Fechado sem virar pull request", "url": issue.get("html_url")}
    return {"estado": "conferindo", "rotulo": "Recebido, sendo conferido", "url": issue.get("html_url")}


FINAIS = ("aceito", "nao_aceito", "recusado")
