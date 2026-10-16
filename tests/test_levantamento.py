"""Levantamento do acervo: listagem recursiva, classificação pelo começo do arquivo."""
import csv
import json
import os

import pytest

from motor import levantamento as lv
from motor.banco import Banco
from motor.reate import ErroREATE

SUL_DLIS = b"   1V1.00RECORD16384RECALL TO DLIS DATA TRANSFER STORAGE SET ID " + b" " * 16
TIF_LIS = bytes.fromhex("000000000000000090000000008400008400") + b"RECALL      27/ 2/20" + b" " * 40
TIFF = b"II*\x00" + b"\x00" * 60
PDF = b"%PDF-1.4\n" + b"x" * 60
LAS = (b"~VERSION INFORMATION\n VERS. 2.0:\n~WELL\n STRT.M 100:\n~CURVE INFORMATION\n"
       b" DEPT.M  :\n GR  .GAPI :\n RHOB.G/C3 :\n NPHI.V/V :\n~ASCII\n100 50 2.3 0.2\n")


class ClienteFalso:
    """Portal em memória: {caminho: bytes} para arquivos; pastas implícitas."""

    def __init__(self, arquivos: dict, aceita_infinity=True):
        self.arquivos = arquivos
        self.aceita_infinity = aceita_infinity
        self.lidos: list[tuple[str, int]] = []
        self.arvores: list[str] = []

    def _itens(self, base, recursivo):
        base = base.rstrip("/") + "/"
        vistos = {}
        for cam, dados in self.arquivos.items():
            if not cam.startswith(base):
                continue
            partes = cam[len(base):].split("/")
            alcance = len(partes) if recursivo else 1
            for k in range(1, alcance + 1):
                sub = base + "/".join(partes[:k])
                eh_pasta = k < len(partes)
                vistos[sub + ("/" if eh_pasta else "")] = (partes[k - 1], eh_pasta, 0 if eh_pasta else len(dados))
        return [{"nome": n, "pasta": p, "tamanho": t, "modificado": "", "caminho": c}
                for c, (n, p, t) in sorted(vistos.items())]

    def descobrir_categorias(self):
        return "/POCO/", [i for i in self._itens("/POCO/", False) if i["pasta"]]

    def listar(self, caminho):
        return self._itens(caminho, False)

    def listar_arvore(self, caminho):
        self.arvores.append(caminho)
        if not self.aceita_infinity and caminho.count("/") <= 4:
            raise ErroREATE("Depth infinity recusado")
        return self._itens(caminho, True)

    def ler_inicio(self, caminho, n=1024):
        self.lidos.append((caminho, n))
        return self.arquivos[caminho][:n]


def portal():
    p = "/POCO/Categoria-7/Categoria-7_parte1/"
    return {
        p + "7-CS-16-AL/Perfis_digitais/7CS__0016__AL_7CS__0016__AL.tif": TIF_LIS,       # LIS de fita
        p + "7-CS-16-AL/Pasta de Poco/7CS_pasta.pdf": PDF,
        p + "7-FU-1-AL/Perfil Convencional/7-fu-1-al.dlis": SUL_DLIS + b"\x00" * 100,
        p + "7-FU-1-AL/Perfil Convencional/7-fu-1-al.las": LAS,
        p + "7-XX-2-AL/Perfil Convencional/7XX_scan.tif": TIFF,                          # imagem de verdade
        p + "7-XX-3-AL/Pasta de Poco/relatorio.pdf": PDF,                                # sem perfil
        "/POCO/Categoria-1/1-PX-11-AL/Perfil Convencional/1PX.tif": SUL_DLIS + b"\x00" * 50,  # DLIS sem envelope
    }


@pytest.fixture
def banco(tmp_path):
    return Banco(str(tmp_path / "projeto.sqlite"))


def rodar(banco, cliente, categorias=(), **kw):
    eventos = []
    lev = lv.Levantamento(banco, "Alagoas", list(categorias), emitir=eventos.append, cliente=cliente, **kw)
    return lev.executar(), eventos


def test_agrupar_por_poco_separa_pastas_e_marca_candidatos():
    c = ClienteFalso(portal())
    base = "/POCO/Categoria-7/Categoria-7_parte1/"
    pocos = lv.agrupar_por_poco(base, c.listar_arvore(base))
    assert set(p["nome"] for p in pocos.values()) == {"7-CS-16-AL", "7-FU-1-AL", "7-XX-2-AL", "7-XX-3-AL"}
    cs = pocos[base + "7-CS-16-AL/"]["arquivos"]
    assert {(a["nome"], a["candidato"]) for a in cs} == {("7CS__0016__AL_7CS__0016__AL.tif", 1), ("7CS_pasta.pdf", 0)}


def test_levantamento_classifica_pelo_conteudo(banco):
    c = ClienteFalso(portal())
    r, eventos = rodar(banco, c)
    assert r["pocos"] == 5
    assert c.arvores[0] == "/POCO/Categoria-1/"            # categoria sem partes: uma listagem só
    assert "/POCO/Categoria-7/Categoria-7_parte1/" in c.arvores
    # só os ambíguos foram lidos (.tif); .dlis e .las confiam no nome
    assert sorted(cam.rsplit("/", 1)[1] for cam, _ in c.lidos) == ["1PX.tif", "7CS__0016__AL_7CS__0016__AL.tif",
                                                                    "7XX_scan.tif"]
    assert all(n == 1024 for _, n in c.lidos)
    with banco.conexao() as cx:
        sit = {row["nome_pasta"]: (row["situacao"], row["formatos"])
               for row in cx.execute("SELECT * FROM acervo_pocos")}
    assert sit == {"7-CS-16-AL": ("digital", "lis"), "7-FU-1-AL": ("digital", "dlis,las"),
                   "7-XX-2-AL": ("imagem", "tiff"), "7-XX-3-AL": ("sem_perfil", ""),
                   "1-PX-11-AL": ("digital", "dlis")}
    res = r["resumo"]
    assert res["situacoes"] == {"digital": 3, "imagem": 1, "sem_perfil": 1, "pendente": 0}
    assert res["extensao_enganosa"] == {".tif → LIS": 1, ".tif → DLIS": 1}
    assert res["formatos"]["lis-em-tif"] == 1
    assert eventos[-1]["tipo"] == "arquivo" and eventos[-1]["feito"] == 3
    # o catálogo de pastas do REATE também foi alimentado
    with banco.conexao() as cx:
        assert cx.execute("SELECT count(*) FROM reate WHERE bacia = 'Alagoas'").fetchone()[0] == 5
    # rodar de novo não lê nada outra vez
    c.lidos.clear()
    rodar(banco, c)
    assert c.lidos == []


def test_curvas_pelo_comeco_e_familias(banco):
    c = ClienteFalso(portal())
    familia = {"GR": "GR", "RHOB": "RHOB", "NPHI": "NPHI"}.get
    rodar(banco, c, ["Categoria-7"], curvas=True, familia=familia)
    las = [a for a in lv.arquivos_do_poco(banco, "7-FU-1-AL") if a["ext"] == ".las"][0]
    assert json.loads(las["curvas"]) == ["GR", "RHOB", "NPHI"] and las["curvas_completas"] == 1
    with banco.conexao() as cx:
        fams = cx.execute("SELECT familias FROM acervo_pocos WHERE nome_pasta = '7-FU-1-AL'").fetchone()[0]
    assert fams == "GR,NPHI,RHOB"
    # só a categoria pedida
    with banco.conexao() as cx:
        assert cx.execute("SELECT count(*) FROM acervo_pocos WHERE categoria = 'Categoria-1'").fetchone()[0] == 0


def test_portal_recusa_listagem_recursiva_cai_para_poco_a_poco(banco):
    c = ClienteFalso(portal(), aceita_infinity=False)
    r, _ = rodar(banco, c, ["Categoria-7"])
    assert r["pocos"] == 4
    assert any(cam.endswith("7-CS-16-AL/") for cam in c.arvores)


def test_arquivo_que_sumiu_ou_mudou_e_relido(banco):
    arqs = portal()
    c = ClienteFalso(arqs)
    rodar(banco, c, ["Categoria-7"])
    cam = "/POCO/Categoria-7/Categoria-7_parte1/7-XX-2-AL/Perfil Convencional/7XX_scan.tif"
    arqs[cam] = TIF_LIS + b"mais"                        # mudou de tamanho no portal
    del arqs["/POCO/Categoria-7/Categoria-7_parte1/7-FU-1-AL/Perfil Convencional/7-fu-1-al.las"]
    c.lidos.clear()
    rodar(banco, c, ["Categoria-7"])
    assert [x for x, _ in c.lidos] == [cam]
    assert [a["ext"] for a in lv.arquivos_do_poco(banco, "7-FU-1-AL")] == [".dlis"]
    with banco.conexao() as cx:
        assert cx.execute("SELECT situacao FROM acervo_pocos WHERE nome_pasta = '7-XX-2-AL'").fetchone()[0] == "digital"


def test_cancelar_deixa_pendente_e_continua_depois(banco):
    c = ClienteFalso(portal())
    eventos = []
    lev = lv.Levantamento(banco, "Alagoas", ["Categoria-7"], emitir=eventos.append, cliente=c)
    original = c.ler_inicio

    def ler_e_cancelar(caminho, n=1024):
        lev.cancelar.set()
        return original(caminho, n)
    c.ler_inicio = ler_e_cancelar
    lev._rodar()
    assert eventos[-1]["tipo"] == "cancelado"
    assert eventos[-1]["resumo"]["situacoes"]["pendente"] >= 1
    c.ler_inicio = original
    r, _ = rodar(banco, c, ["Categoria-7"])
    assert r["resumo"]["situacoes"]["pendente"] == 0


def test_exportar_csv(banco, tmp_path):
    rodar(banco, ClienteFalso(portal()))
    pocos_csv, arqs_csv = lv.exportar_csv(banco, "Alagoas", str(tmp_path / "exp"))
    with open(pocos_csv, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    assert {x["poco"]: x["situacao"] for x in linhas}["7-CS-16-AL"] == "digital"
    with open(arqs_csv, encoding="utf-8-sig") as f:
        a = [x for x in csv.DictReader(f, delimiter=";") if x["nome"].startswith("7CS")][0]
    assert a["extensao"] == ".tif" and a["formato_real"] == "lis" and a["envelope"] == "tif"


def test_curvas_do_inicio_de_dlis_real():
    caminho = os.environ.get("SIAPP_DLIS_REAL")
    if not caminho:
        pytest.skip("defina SIAPP_DLIS_REAL com o caminho de um DLIS real")
    with open(caminho, "rb") as f:
        dados = f.read(256 * 1024)
    curvas = lv.curvas_do_inicio(dados, "dlis", completo=False)
    assert len(curvas) > 20 and "GR" in {c.upper() for c in curvas}
