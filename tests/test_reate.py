"""Cliente do portal REATE: listagem WebDAV, categorias, partes, árvore do poço."""
import threading
import time
from urllib.parse import quote

import pytest
import requests

from motor import reate
from tests.conftest import ArvoreFalsa, item


class Resp:
    def __init__(self, codigo, conteudo=b""):
        self.status_code, self.content = codigo, conteudo


def xml_propfind(caminho, itens):
    def resp(href, pasta, tam=0):
        rt = "<d:collection/>" if pasta else ""
        cl = "" if pasta else f"<d:getcontentlength>{tam}</d:getcontentlength>"
        return (f"<d:response><d:href>{href}</d:href><d:propstat><d:prop><d:resourcetype>{rt}"
                f"</d:resourcetype>{cl}</d:prop></d:propstat></d:response>")
    base = "/arquivos/public.php/webdav"
    corpo = resp(base + caminho, True) + "".join(
        resp(base + quote(caminho + n) + ("/" if p else ""), p, t) for n, p, t in itens)
    return f'<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">{corpo}</d:multistatus>'.encode()


def test_listagem_decodifica_nomes_e_usa_depth_1():
    c = reate.ClienteREATE("T", pausa_s=0)
    chamadas = []

    def falso(metodo, url, **kw):
        chamadas.append((metodo, kw["headers"]["Depth"]))
        return Resp(207, xml_propfind("/", [("POCO", True, 0), ("índice.csv", False, 99)]))

    c.sessao.request = falso
    itens = c.listar("/")
    assert [(i["nome"], i["pasta"], i["tamanho"]) for i in itens] == [("POCO", True, 0), ("índice.csv", False, 99)]
    assert chamadas == [("PROPFIND", "1")]
    assert c.sessao.headers["Authorization"].startswith("Basic ")


@pytest.mark.parametrize("codigo,trecho", [(401, "recusou o token"), (404, "não encontrada"), (500, "HTTP 500")])
def test_erros_http_viram_mensagem_legivel(codigo, trecho):
    c = reate.ClienteREATE("T", pausa_s=0)
    c.sessao.request = lambda *a, **k: Resp(codigo)
    with pytest.raises(reate.ErroREATE, match=trecho):
        c.listar("/")


def test_queda_de_conexao_vira_mensagem_legivel():
    c = reate.ClienteREATE("T", pausa_s=0)

    def cai(*a, **k):
        raise requests.exceptions.ConnectionError("x")

    c.sessao.request = cai
    with pytest.raises(reate.ErroREATE, match="Sem conexão"):
        c.listar("/")


def test_bacia_desconhecida():
    with pytest.raises(reate.ErroREATE):
        reate.ClienteREATE.da_bacia("Atlântida")


def test_categorias_com_e_sem_pasta_poco():
    c = reate.ClienteREATE("T", pausa_s=0)
    c.listar = ArvoreFalsa({"/": [item("POCO", True)], "/POCO/": [item("Categoria-7", True), item("Categoria-1", True)]})
    base, cats = c.descobrir_categorias()
    assert base == "/POCO/" and [x["nome"] for x in cats] == ["Categoria-1", "Categoria-7"]
    c.listar = ArvoreFalsa({"/": [item("Cat A", True), item("x.txt", False, 1)]})
    assert c.descobrir_categorias()[0] == "/"


@pytest.mark.parametrize("nome,esperado", [
    ("Categoria-7_parte1", True), ("Categoria-7-parte3", True), ("Parte 2", True), ("PARTE_10", True),
    ("7-PT-1-AL", False), ("1-PARTE-AL", False), ("Categoria-7", False), ("parte", False)])
def test_reconhece_subpastas_parte(nome, esperado):
    assert reate.eh_pasta_parte(nome) is esperado


def test_listar_pocos_junta_partes_e_registra_repetidos():
    B = "/POCO/Categoria-7/"
    c = reate.ClienteREATE("T", pausa_s=0)
    c.listar = ArvoreFalsa({
        B: [item("Categoria-7_parte1", True), item("Categoria-7_parte2", True), item("indice.pdf", False, 10)],
        B + "Categoria-7_parte1/": [item("7-CP-10-SE", True), item("7-CP-108-SE", True)],
        B + "Categoria-7_parte2/": [item("7-CP-109-SE", True), item("7-CP-10-SE", True)],
    })
    r = c.listar_pocos(B)
    assert [p["nome"] for p in r["pocos"]] == ["7-CP-10-SE", "7-CP-108-SE", "7-CP-109-SE"]
    assert r["duplicados"] == [{"nome": "7-CP-10-SE", "parte": "Categoria-7_parte2", "mantido_de": "Categoria-7_parte1"}]
    assert next(p for p in r["pocos"] if p["nome"] == "7-CP-10-SE")["caminho"] == B + "Categoria-7_parte1/7-CP-10-SE/"


@pytest.mark.parametrize("nome,esperado", [
    ("PERFIS CONVENCIONAIS", True), ("Perfil Convencional", True), ("Perfis_digitais", True),
    ("Esquema_de_ferramentas", False), ("Pasta_poco", False)])
def test_pasta_de_perfis(nome, esperado):
    assert reate.eh_pasta_de_perfis(nome) is esperado


def test_mapear_poco_soma_tamanhos_e_respeita_travas():
    B = "/POCO/C/7-ANB-9-AL/"
    arv = ArvoreFalsa({
        B: [item("Perfis_digitais", True), item("Esquema", True), item("ficha.pdf", False, 200)],
        B + "Perfis_digitais/": [item("raw.dlis", False, 1_700_000), item("sft.dlis", False, 7_100_000)],
        B + "Esquema/": [item("tsc_raw.pdf", False, 300)],
    })
    c = reate.ClienteREATE("T", pausa_s=0)
    c.listar = arv
    m = c.mapear_poco(B, "7-ANB-9-AL")
    assert m["resumo"]["n_arquivos"] == 4 and m["resumo"]["tamanho_total"] == 8_800_500
    perfis = next(f for f in m["arvore"]["filhos"] if f["nome"] == "Perfis_digitais")
    assert perfis["preferida"] and perfis["n_arquivos"] == 2
    assert {a["nome"]: a["pasta_relativa"] for a in m["arquivos"]}["raw.dlis"] == "Perfis_digitais"
    c.listar = ArvoreFalsa({"/F/": [item("a", True)], "/F/a/": [item("b", True)], "/F/a/b/": []})
    assert c.mapear_poco("/F/", max_profundidade=1)["incompleto"]


def test_uma_requisicao_por_vez_mesmo_com_varias_threads():
    c = reate.ClienteREATE("T", pausa_s=0)
    ativo, pico = [0], [0]

    def lenta(*a, **k):
        ativo[0] += 1
        pico[0] = max(pico[0], ativo[0])
        time.sleep(0.03)
        ativo[0] -= 1
        return Resp(207, xml_propfind("/", []))

    c.sessao.request = lenta
    ts = [threading.Thread(target=c.listar, args=("/",)) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert pico[0] == 1


def test_listar_arvore_usa_depth_infinity_e_caminhos_aninhados():
    c = reate.ClienteREATE("T", pausa_s=0)
    pedidos = []

    def falso(metodo, url, **kw):
        pedidos.append(kw["headers"]["Depth"])
        return Resp(207, xml_propfind("/POCO/Cat/", [("1-A-1-RN", True, 0), ("1-A-1-RN/Perfil Convencional", True, 0),
                                                       ("1-A-1-RN/Perfil Convencional/a b.tif", False, 10)]))
    c.sessao.request = falso
    itens = c.listar_arvore("/POCO/Cat/")
    assert pedidos == ["infinity"]
    assert [i["caminho"] for i in itens] == ["/POCO/Cat/1-A-1-RN/", "/POCO/Cat/1-A-1-RN/Perfil Convencional/",
                                             "/POCO/Cat/1-A-1-RN/Perfil Convencional/a b.tif"]
    assert itens[-1]["nome"] == "a b.tif" and itens[-1]["tamanho"] == 10


class RespFluxo:
    def __init__(self, codigo, dados):
        self.status_code, self.dados, self.lidos = codigo, dados, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_content(self, n):
        for i in range(0, len(self.dados), n):
            self.lidos += 1
            yield self.dados[i:i + n]


def test_ler_inicio_pede_range_e_para_nos_n_bytes():
    c = reate.ClienteREATE("T", pausa_s=0)
    vistos = {}

    def get(url, headers=None, **kw):
        vistos["range"] = headers["Range"]
        vistos["url"] = url
        vistos["resp"] = RespFluxo(200, b"x" * 1_000_000)   # servidor que ignora o Range
        return vistos["resp"]
    c.sessao.get = get
    dados = c.ler_inicio("/POCO/Cat/1-A-1-RN/Perfil Convencional/a b.tif", 1024)
    assert len(dados) == 1024 and vistos["range"] == "bytes=0-1023"
    assert vistos["url"].endswith("/webdav/POCO/Cat/1-A-1-RN/Perfil%20Convencional/a%20b.tif")
    assert vistos["resp"].lidos == 1                         # não leu o resto do arquivo
