"""
Cliente do portal REATE (ANP/CPRM).

Este módulo só sabe conversar com o portal. Não conhece interface, janela
nem pasta de projeto — pode ser usado por script, notebook ou pela janela
do SIAPP sem mudança.

Como o portal funciona (verificado em versões anteriores do projeto):
  - É um Nextcloud público. Cada bacia é um "compartilhamento" com um token.
  - Não há login, cookie nem CSRF. A única credencial é o token da bacia,
    enviado via Basic Auth (padrão do Nextcloud para compartilhamento público).
  - Listar pastas = verbo WebDAV PROPFIND sobre /public.php/webdav/<caminho>.
  - O nome reate.cprm.gov.br aponta para DOIS servidores (200.237.2.133 e .134,
    conferido em 28/10/2026). Quando um deles fica sem servidor por trás, responde
    "503 — No server is available to handle this request" a tudo, enquanto o outro
    funciona; o Windows entrega sempre o mesmo primeiro, então o SIAPP caía sempre
    no quebrado enquanto o Chrome abria. Por isso, diante de 502/503/504 ou de falha
    de conexão, o cliente tenta os outros endereços e fica no que respondeu
    (ver _Servidores e ClienteREATE._enviar).
"""

from __future__ import annotations

import base64
import logging
import os
import re
import socket
import threading
import time
import unicodedata
from collections import Counter
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote

import requests
import urllib3.util.connection as _u3_conexao

VERSAO_CLIENTE = "0.2"
HOST_PORTAL = "reate.cprm.gov.br"
SERVIDOR_FORA = (502, 503, 504)       # o balanceador do portal sem servidor por trás
log = logging.getLogger("siapp.reate")

URL_BASE = "https://reate.cprm.gov.br/arquivos"
URL_WEBDAV = f"{URL_BASE}/public.php/webdav"
URL_DOWNLOAD = f"{URL_BASE}/index.php/s/{{token}}/download"

# Tokens de compartilhamento das bacias, extraídos de reate.cprm.gov.br/anp/TERRESTRE.
# Observação: Sergipe e Alagoas são compartilhamentos SEPARADOS no portal.
BACIAS = {
    "Acre - Madre de Dios": "1H3Dg7jT4gInGMC",
    "Alagoas": "UIgVZobfQwyLeA1",
    "Amazonas": "IPNA8z7hO1vHsxI",
    "Araripe": "ygv6FS5D91I6mef",
    "Barreirinhas": "WXhrH3KTduh9IVM",
    "Bragança - Vizeu": "Ril60VKtkXRGyE0",
    "Espírito Santo": "MSYSOk8HApYAT7w",
    "Jatobá": "iUEhPczwLZyFhGy",
    "Marajó": "vPEuDaXVoAqLZGx",
    "Pantanal": "HyVBmvQ8rht4u3k",
    "Paraná": "z0XoautAuswCSbf",
    "Parecis - Alto Xingu": "1OivrPY3VNVSoiv",
    "Parnaíba": "zTQ17CWbL2Wvx5f",
    "Potiguar": "mCuF7AzcaAztmoA",
    "Recôncavo": "87Ny6plVJXljL0C",
    "Rio do Peixe": "8J7SFIsDwkxs0r8",
    "São Francisco": "raz73BsTFYy9emP",
    "São Luís": "j2vquXFrz05VzUg",
    "Sergipe": "3JDqGW6H8EtmXOJ",
    "Solimões": "DKD0oj9FsZAU8tI",
    "Tacutu": "Ii5FEOWeLJRw5Qp",
    "Tucano Central": "CsrfPDvjMGmxlEY",
    "Tucano Norte": "1p76hGJhZc2Szae",
    "Tucano Sul": "RjB46l9VOkiKEd7",
}

_NS = {"d": "DAV:"}
_CORPO_PROPFIND = """<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:getcontentlength/>
    <d:getlastmodified/>
    <d:resourcetype/>
  </d:prop>
</d:propfind>"""


# Categorias grandes são divididas pelo portal em subpastas "parte":
# "Categoria-7_parte1", "Categoria-7-parte3", "Parte 2"... Os poços ficam dentro.
_RE_PARTE = re.compile(r"(?:^|[\s_\-])parte[\s_\-]*\d+$", re.IGNORECASE)


def eh_pasta_parte(nome: str) -> bool:
    return bool(_RE_PARTE.search(nome.strip()))


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def eh_pasta_de_perfis(nome: str) -> bool:
    """
    Pasta onde ficam os perfis de poço, preferida na sugestão de download.
    Nomes vistos no portal:
      - 'Perfis_digitais'         (ex.: 7-ANB-9-AL, Bacia de Alagoas)
      - '...CONVENCIONAIS'        (regra herdada do SIAPP anterior)
    O radical 'CONVENCION' cobre singular e plural: 'CONVENCIONAIS' NÃO
    contém 'CONVENCIONAL' (armadilha 2.3 das notas do projeto).
    """
    n = _sem_acento(nome).upper()
    return "CONVENCION" in n or ("PERFI" in n and "DIGITA" in n)


# Formatos de perfil, em ordem de preferência para a sugestão de download.
FORMATOS_PERFIL = (".dlis", ".lis", ".las")


class ErroREATE(Exception):
    """Falha de comunicação com o portal, com mensagem legível para o usuário."""


class _Servidores:
    """Qual dos endereços do portal usar (vale para o processo inteiro, todas as bacias).

    Enquanto nada falha, o sistema escolhe (fixo = None). Quando um endereço responde
    502/503/504 ou não conecta, o cliente tenta os outros e fixa o que funcionou. A
    troca vale para as próximas conexões; o certificado e o cabeçalho Host continuam
    sendo os de reate.cprm.gov.br (só o endereço IP da conexão muda)."""

    VALIDADE_DNS_S = 600

    def __init__(self):
        self.fixo: str | None = None
        self._trava = threading.Lock()
        self._cache: tuple[float, list[str]] = (0.0, [])

    def resolver(self) -> list[str]:
        try:
            infos = socket.getaddrinfo(HOST_PORTAL, 443, proto=socket.IPPROTO_TCP)
        except OSError:
            return []
        return list(dict.fromkeys(i[4][0] for i in infos))

    def enderecos(self) -> list[str]:
        with self._trava:
            quando, ips = self._cache
            if not ips or time.monotonic() - quando > self.VALIDADE_DNS_S:
                ips = self.resolver()
                self._cache = (time.monotonic(), ips)
            return list(ips)

    def alternativas(self, excluir: str | None) -> list[str]:
        return [ip for ip in self.enderecos() if ip != excluir]

    def esquecer(self):
        with self._trava:
            self.fixo, self._cache = None, (0.0, [])


SERVIDORES = _Servidores()
_criar_conexao_original = _u3_conexao.create_connection


def _criar_conexao(endereco, *args, **kwargs):
    """Gancho do urllib3: conexões a reate.cprm.gov.br vão ao endereço fixado, se houver."""
    host, porta = endereco
    if host == HOST_PORTAL and SERVIDORES.fixo:
        endereco = (SERVIDORES.fixo, porta)
    return _criar_conexao_original(endereco, *args, **kwargs)


_u3_conexao.create_connection = _criar_conexao


class DownloadCancelado(Exception):
    """O usuário cancelou. O arquivo .part fica no disco para retomar depois."""


TAMANHO_BLOCO = 256 * 1024   # 256 KB por pedaço no streaming


class ClienteREATE:
    """Conexão com o compartilhamento de UMA bacia."""

    def __init__(self, token: str, pausa_s: float = 0.3, timeout_s: float = 60):
        self.token = token
        self.pausa_s = pausa_s          # cortesia com o servidor entre requisições
        self.timeout_s = timeout_s
        self._ultima_req = 0.0
        # A janela pode disparar duas listagens ao mesmo tempo (ex.: clicar em
        # outro poço antes do anterior terminar). A trava garante uma
        # requisição por vez — e a pausa de cortesia entre elas.
        self._trava = threading.Lock()

        credencial = base64.b64encode(f"{token}:null".encode()).decode("ascii")
        self.sessao = requests.Session()
        self.sessao.headers.update({
            "User-Agent": f"SIAPP/{VERSAO_CLIENTE} (pesquisa academica, UFAL)",
            "Authorization": f"Basic {credencial}",
            "X-Requested-With": "XMLHttpRequest",
        })

    @classmethod
    def da_bacia(cls, nome_bacia: str, **kw) -> "ClienteREATE":
        if nome_bacia not in BACIAS:
            raise ErroREATE(f"Bacia desconhecida: {nome_bacia!r}")
        return cls(BACIAS[nome_bacia], **kw)

    # ------------------------------------------------------------------ listar
    def _aguardar_vez(self):
        espera = self.pausa_s - (time.monotonic() - self._ultima_req)
        if espera > 0:
            time.sleep(espera)
        self._ultima_req = time.monotonic()

    def _uma(self, metodo: str, url: str, kw: dict):
        if metodo == "GET":
            return self.sessao.get(url, **kw)
        return self.sessao.request(metodo, url, **kw)

    def _enviar(self, metodo: str, url: str, **kw):
        """Uma requisição ao portal. Se o servidor responder 502/503/504 ou não conectar,
        tenta os outros endereços do portal e fica no primeiro que responder."""
        usado = SERVIDORES.fixo
        falhas: list[str] = []
        erro_conexao = None
        try:
            resp = self._uma(metodo, url, kw)
            if resp.status_code not in SERVIDOR_FORA:
                return resp
            getattr(resp, "close", lambda: None)()
            falhas.append(f"{usado or 'o endereço padrão'}: HTTP {resp.status_code}")
        except requests.exceptions.ConnectionError as e:
            erro_conexao = e
            falhas.append(f"{usado or 'o endereço padrão'}: sem conexão")
        for ip in SERVIDORES.alternativas(usado):
            SERVIDORES.fixo = ip
            self.sessao.close()                       # conexões abertas iam ao endereço antigo
            try:
                resp = self._uma(metodo, url, kw)
            except requests.exceptions.ConnectionError as e:
                erro_conexao = e
                falhas.append(f"{ip}: sem conexão")
                continue
            if resp.status_code in SERVIDOR_FORA:
                getattr(resp, "close", lambda: None)()
                falhas.append(f"{ip}: HTTP {resp.status_code}")
                continue
            log.info("REATE: servidor com defeito (%s); usando %s", "; ".join(falhas), ip)
            return resp
        SERVIDORES.fixo = usado
        if erro_conexao is not None and not any("HTTP" in f for f in falhas):
            raise erro_conexao
        raise ErroREATE("O REATE está fora do ar: nenhum servidor do portal respondeu "
                        f"({'; '.join(falhas)}). Tente de novo mais tarde.")

    def _propfind(self, caminho: str, profundidade: str, timeout_s: float | None = None) -> list[dict]:
        caminho = "/" + caminho.strip("/") + "/" if caminho.strip("/") else "/"
        url = URL_WEBDAV + quote(caminho, safe="/")
        try:
            with self._trava:
                self._aguardar_vez()
                resp = self._enviar(
                    "PROPFIND", url,
                    headers={"Depth": profundidade, "Content-Type": "application/xml; charset=utf-8"},
                    data=_CORPO_PROPFIND.encode("utf-8"),
                    timeout=timeout_s or self.timeout_s,
                )
        except requests.exceptions.RequestException as e:
            raise ErroREATE(f"Sem conexão com o REATE ({type(e).__name__}). "
                            f"Verifique a internet ou se o portal está no ar.") from e

        if resp.status_code == 401:
            raise ErroREATE("O portal recusou o token da bacia (401). "
                            "O link do compartilhamento pode ter mudado.")
        if resp.status_code == 404:
            raise ErroREATE(f"Pasta não encontrada no portal: {caminho}")
        if resp.status_code not in (200, 207):
            raise ErroREATE(f"Resposta inesperada do portal: HTTP {resp.status_code}")

        try:
            raiz = ET.fromstring(resp.content)
        except ET.ParseError as e:
            raise ErroREATE("O portal respondeu algo que não é uma listagem WebDAV.") from e

        itens = []
        for r in raiz.findall("d:response", _NS):
            href = unquote(r.findtext("d:href", default="", namespaces=_NS))
            if "/webdav" not in href:
                continue
            rel = href.split("/webdav", 1)[1] or "/"
            if rel.rstrip("/") == caminho.rstrip("/"):
                continue                                  # a própria pasta
            prop = r.find("d:propstat/d:prop", _NS)
            if prop is None:
                continue
            eh_pasta = prop.find("d:resourcetype/d:collection", _NS) is not None
            nome = rel.rstrip("/").rsplit("/", 1)[-1]
            if not nome:
                continue
            tamanho = prop.findtext("d:getcontentlength", default="", namespaces=_NS)
            itens.append({
                "nome": nome,
                "pasta": eh_pasta,
                "tamanho": int(tamanho) if tamanho.isdigit() else 0,
                "modificado": prop.findtext("d:getlastmodified", default="", namespaces=_NS),
                "caminho": rel.rstrip("/") + ("/" if eh_pasta else ""),
            })
        return itens

    def listar(self, caminho: str = "/") -> list[dict]:
        """
        Lista o conteúdo imediato de uma pasta remota (PROPFIND, Depth 1).
        Devolve [{"nome", "pasta", "tamanho", "modificado", "caminho"}, ...].
        """
        return self._propfind(caminho, "1")

    def listar_arvore(self, caminho: str) -> list[dict]:
        """Tudo o que há abaixo de `caminho`, em UMA requisição (PROPFIND Depth
        infinity). O portal aceita: uma pasta "parte" com 100 poços (1.739
        itens, 560 KB) volta em ~3 s (conferido em 16/10/2026) — contra ~400
        requisições pasta a pasta."""
        return self._propfind(caminho, "infinity", timeout_s=max(self.timeout_s, 180))

    def descobrir_categorias(self) -> tuple[str, list[dict]]:
        """
        A estrutura de pastas varia entre bacias. Se a raiz tiver uma pasta
        'POCO', as categorias estão dentro dela; senão, estão na própria raiz.
        Devolve (caminho_base, [itens de pasta]).
        """
        raiz = self.listar("/")
        if any(i["pasta"] and i["nome"].upper() == "POCO" for i in raiz):
            base = "/POCO/"
            itens = self.listar(base)
        else:
            base, itens = "/", raiz
        categorias = sorted((i for i in itens if i["pasta"]), key=lambda i: i["nome"])
        return base, categorias

    def listar_pocos(self, caminho_categoria: str, progresso=None) -> dict:
        """
        Lista os poços de uma categoria. Se a categoria estiver dividida em
        subpastas "parte", entra em cada uma e junta tudo numa lista só —
        cada poço guarda de qual parte veio (o caminho é necessário no
        download). Um poço repetido em duas partes entra uma vez só e fica
        registrado em "duplicados".

        progresso(texto), se passado, é chamado a cada parte lida.
        """
        itens = self.listar(caminho_categoria)
        partes = [i for i in itens if i["pasta"] and eh_pasta_parte(i["nome"])]
        diretos = [i for i in itens if not (i["pasta"] and eh_pasta_parte(i["nome"]))]

        pocos, soltos, duplicados, vistos = [], [], [], {}

        def absorver(lista, parte):
            for i in lista:
                if not i["pasta"]:
                    soltos.append({"nome": i["nome"], "tamanho": i["tamanho"], "parte": parte})
                elif i["nome"] in vistos:
                    duplicados.append({"nome": i["nome"], "parte": parte,
                                       "mantido_de": vistos[i["nome"]]})
                else:
                    vistos[i["nome"]] = parte
                    pocos.append({"nome": i["nome"], "caminho": i["caminho"], "parte": parte})

        absorver(diretos, None)
        for n, p in enumerate(partes, 1):
            if progresso:
                progresso(f"Lendo {p['nome']} ({n} de {len(partes)})…")
            absorver(self.listar(p["caminho"]), p["nome"])

        pocos.sort(key=lambda p: p["nome"])
        return {"pocos": pocos, "arquivos_soltos": soltos,
                "partes": [p["nome"] for p in partes], "duplicados": duplicados}

    def mapear_poco(self, caminho_poco: str, nome_poco: str = "", progresso=None,
                    max_profundidade: int = 8, max_pastas: int = 300) -> dict:
        """
        Percorre TODA a árvore de pastas de um poço (só listagem — nada é
        baixado) e devolve:
          arvore    pastas e arquivos aninhados, com o tamanho total de cada pasta
          arquivos  lista plana de todos os arquivos
          resumo    nº de arquivos, tamanho total, contagem por extensão
          sugestao  arquivo que o SIAPP baixaria por padrão, e o porquê

        As travas (profundidade e nº de pastas) protegem contra estruturas
        inesperadas no portal; se forem atingidas, 'incompleto' vem True.
        """
        nome_poco = nome_poco or caminho_poco.rstrip("/").rsplit("/", 1)[-1]
        lidas = [0]
        incompleto = [False]
        arquivos = []

        def visitar(caminho, nome, prof, ancestrais):
            lidas[0] += 1
            if progresso:
                progresso(f"Mapeando {nome_poco}… {lidas[0]} pasta(s) lida(s)")
            dentro_perfis = any(eh_pasta_de_perfis(a) for a in ancestrais)
            filhos = []
            for i in sorted(self.listar(caminho), key=lambda i: (not i["pasta"], i["nome"].lower())):
                if i["pasta"]:
                    if prof + 1 > max_profundidade or lidas[0] >= max_pastas:
                        incompleto[0] = True
                        filhos.append({"nome": i["nome"], "pasta": True, "caminho": i["caminho"],
                                       "tamanho": 0, "n_arquivos": 0, "nao_lida": True,
                                       "preferida": eh_pasta_de_perfis(i["nome"]), "filhos": []})
                    else:
                        filhos.append(visitar(i["caminho"], i["nome"], prof + 1,
                                              ancestrais + [i["nome"]]))
                else:
                    arq = {"nome": i["nome"], "pasta": False, "caminho": i["caminho"],
                           "tamanho": i["tamanho"], "ext": os.path.splitext(i["nome"])[1].lower(),
                           "em_pasta_perfis": dentro_perfis,
                           "pasta_relativa": "/".join(ancestrais)}
                    filhos.append(arq)
                    arquivos.append(arq)
            return {"nome": nome, "pasta": True, "caminho": caminho,
                    "preferida": eh_pasta_de_perfis(nome) and prof > 0,
                    "tamanho": sum(f["tamanho"] for f in filhos),
                    "n_arquivos": sum(f.get("n_arquivos", 1) for f in filhos),
                    "filhos": filhos}

        arvore = visitar(caminho_poco, nome_poco, 0, [])
        sugestao = sugerir_arquivo(arquivos)
        if sugestao:
            for a in arquivos:
                a["sugerido"] = a["caminho"] == sugestao["caminho"]

        por_ext = Counter(a["ext"] or "(sem extensão)" for a in arquivos)
        return {
            "poco": nome_poco, "caminho": caminho_poco, "arvore": arvore,
            "arquivos": arquivos, "sugestao": sugestao, "incompleto": incompleto[0],
            "resumo": {"n_arquivos": len(arquivos), "n_pastas_lidas": lidas[0],
                       "tamanho_total": arvore["tamanho"],
                       "por_extensao": dict(por_ext.most_common())},
        }


    def ler_inicio(self, caminho_remoto: str, n: int = 1024) -> bytes:
        """Os primeiros `n` bytes de um arquivo do portal, sem baixá-lo inteiro.

        Pede com Range (o portal responde 206: conferido em 16/10/2026, 4 KB de
        um DLIS de 192 MB em 0,2 s). Se algum dia ignorar o Range e mandar o
        arquivo todo (200), a leitura para nos `n` bytes e a conexão é fechada —
        o custo continua pequeno."""
        url = URL_WEBDAV + quote(caminho_remoto, safe="/")
        try:
            with self._trava:
                self._aguardar_vez()
                with self._enviar("GET", url, headers={"Range": f"bytes=0-{n - 1}"}, stream=True,
                                  timeout=(30, self.timeout_s)) as resp:
                    if resp.status_code == 401:
                        raise ErroREATE("O portal recusou o token da bacia (401).")
                    if resp.status_code == 404:
                        raise ErroREATE(f"Arquivo não encontrado no portal: {caminho_remoto}")
                    if resp.status_code == 416:          # arquivo vazio
                        return b""
                    if resp.status_code not in (200, 206):
                        raise ErroREATE(f"Resposta inesperada do portal: HTTP {resp.status_code}")
                    pedacos, total = [], 0
                    for bloco in resp.iter_content(min(n, 64 * 1024)):
                        pedacos.append(bloco)
                        total += len(bloco)
                        if total >= n:
                            break
                    return b"".join(pedacos)[:n]
        except requests.exceptions.RequestException as e:
            raise ErroREATE(f"Sem conexão com o REATE ({type(e).__name__}).") from e

    def baixar(self, caminho_remoto: str, destino: str, tamanho_esperado: int = 0,
                progresso=None, cancelar: threading.Event | None = None,
                tentativas: int = 4) -> dict:
        """
        Baixa UM arquivo do portal para `destino`.

        - Grava primeiro em '<destino>.part' e só renomeia no fim: um arquivo com
          o nome final está sempre completo.
        - Retomável: se já existir um .part (download interrompido, cancelado ou
          janela fechada), continua de onde parou com o cabeçalho HTTP Range.
        - Se o servidor ignorar o Range e mandar o arquivo inteiro (HTTP 200 em vez
          de 206), recomeça do zero em vez de anexar — senão o arquivo sairia
          corrompido em silêncio (armadilha 2.4 das notas).
        - Queda de conexão: tenta de novo até `tentativas` vezes, com espera
          crescente, sempre retomando do ponto em que parou.
        - No fim, confere o tamanho com o informado pelo portal.

        progresso(feito, total) é chamado a cada pedaço recebido.
        Devolve {"status": "baixado" | "ja_existia", "bytes": n}.
        """
        pasta_remota, nome = caminho_remoto.rsplit("/", 1)
        if os.path.exists(destino):
            if tamanho_esperado and os.path.getsize(destino) == tamanho_esperado:
                return {"status": "ja_existia", "bytes": tamanho_esperado}
            os.remove(destino)   # tamanho diferente: versão incompleta/antiga
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        parcial = destino + ".part"
        url = URL_DOWNLOAD.format(token=self.token)
        params = {"path": pasta_remota + "/", "files": nome}

        ultimo_erro = None
        for tentativa in range(1, tentativas + 1):
            ja = os.path.getsize(parcial) if os.path.exists(parcial) else 0
            if tamanho_esperado and ja > tamanho_esperado:      # .part inválido
                os.remove(parcial)
                ja = 0
            if tamanho_esperado and ja == tamanho_esperado:     # já estava completo
                break
            cab = {"Range": f"bytes={ja}-"} if ja else {}
            try:
                with self._enviar("GET", url, params=params, headers=cab, stream=True,
                                  timeout=(30, 120)) as resp:
                    if resp.status_code == 401:
                        raise ErroREATE("O portal recusou o token da bacia (401).")
                    if resp.status_code == 404:
                        raise ErroREATE(f"Arquivo não encontrado no portal: {nome}")
                    if resp.status_code == 416:                 # Range inválido
                        os.remove(parcial)
                        continue
                    if resp.status_code not in (200, 206):
                        raise ErroREATE(f"Resposta inesperada do portal ao baixar {nome}: HTTP {resp.status_code}")
                    if ja and resp.status_code == 200:
                        ja = 0                                  # servidor ignorou o Range
                    feito = ja
                    with open(parcial, "ab" if ja else "wb") as f:
                        for bloco in resp.iter_content(TAMANHO_BLOCO):
                            if cancelar is not None and cancelar.is_set():
                                raise DownloadCancelado()
                            if bloco:
                                f.write(bloco)
                                feito += len(bloco)
                                if progresso:
                                    progresso(feito, tamanho_esperado)
                break                                           # stream terminou
            except requests.exceptions.RequestException as e:
                ultimo_erro = e
                if tentativa < tentativas:
                    for _ in range(min(2 ** tentativa, 30) * 10):   # espera, mas atende cancelamento
                        if cancelar is not None and cancelar.is_set():
                            raise DownloadCancelado()
                        time.sleep(0.1)
        else:
            raise ErroREATE(f"Conexão caiu {tentativas} vezes baixando {nome} "
                            f"({type(ultimo_erro).__name__ if ultimo_erro else 'erro'}). "
                            f"O que já foi baixado está salvo; peça de novo para continuar.")

        final = os.path.getsize(parcial) if os.path.exists(parcial) else 0
        if tamanho_esperado and final != tamanho_esperado:
            raise ErroREATE(f"{nome}: recebidos {final} bytes, o portal informa {tamanho_esperado}. "
                            f"Arquivo parcial mantido; peça de novo para continuar.")
        os.replace(parcial, destino)
        return {"status": "baixado", "bytes": final}


def sugerir_arquivo(arquivos: list[dict]) -> dict | None:
    """
    ATENÇÃO (out/2026): a interface NÃO usa mais esta sugestão — a escolha do
    arquivo é do usuário, porque cada tipo serve a uma finalidade (passada
    principal, repetida, testador de formação...). Mantida só como referência
    para um futuro download em lote, onde o critério também deve ser escolhido
    pelo usuário. Ver nota "SIAPP — Estrutura do Acervo REATE".

    Regra herdada do SIAPP anterior (decisão 1.4/1.6 das notas): para cada
    poço, um arquivo de perfil. Prefere a pasta de perfis (eh_pasta_de_perfis); dentro
    dela (ou, se não existir, no poço inteiro), o MAIOR arquivo do formato
    mais preferido disponível (.dlis > .lis > .las).
    """
    for ext in FORMATOS_PERFIL:
        candidatos = [a for a in arquivos if a["ext"] == ext]
        if not candidatos:
            continue
        pref = [a for a in candidatos if a["em_pasta_perfis"]]
        escolhido = max(pref or candidatos, key=lambda a: a["tamanho"])
        onde = (f"na pasta {escolhido['pasta_relativa']}" if pref
                else "no poço (não há pasta de perfis reconhecida)")
        return {"caminho": escolhido["caminho"], "nome": escolhido["nome"],
                "tamanho": escolhido["tamanho"],
                "motivo": f"maior arquivo {ext} {onde}"}
    return None
