"""Nome canônico de poço, cadastro da ANP, catálogo do REATE e mapa."""
import json

import pytest

from motor import banco as mb
from motor import pocos as mpo


@pytest.mark.parametrize("entrada, esperado", [
    ("7-GMR-13-RN", "7-GMR-13-RN"),
    ("7GMR_0013__RN", "7-GMR-13-RN"),           # geração antiga de arquivos
    ("7CS__0016__AL", "7-CS-16-AL"),
    ("7gmr13rn", "7-GMR-13-RN"),
    ("7-GVR-26D-MA", "7-GVR-26D-MA"),
    ("7GVR26DMA", "7-GVR-26D-MA"),               # nome do operador, sem separadores
    ("7-PRG-59H-RJS", "7-PRG-59H-RJS"),          # poço no mar
    ("1-RJS-628A-RJ", "1-RJS-628A-RJ"),
    ("6-BRSA-1349-RJS", "6-BRSA-1349-RJS"),
    ("3-BRSA-1151-RN", "3-BRSA-1151-RN"),
    ("7-PIR-174D-AL", "7-PIR-174D-AL"),
    ("Pasta de Poco", None),
    ("", None),
    ("7-GMR-13-XX", None),                       # UF inexistente
])
def test_canonico(entrada, esperado):
    assert mpo.canonico(entrada) == esperado


CABECALHO = ("POCO;CADASTRO;OPERADOR;POCO_OPERADOR;ESTADO;BACIA;BLOCO;SIG_CAMPO;CAMPO;TERRA_MAR;"
             "POCO_POS_ANP;TIPO;CATEGORIA;RECLASSIFICACAO;SITUACAO;INICIO;TERMINO;CONCLUSAO;"
             "TITULARIDADE;LATITUDE_BASE_4C;LONGITUDE_BASE_4C;LATITUDE_BASE_DD;LONGITUDE_BASE_DD;"
             "DATUM_HORIZONTAL;TIPO_DE_COORDENADA_DE_BASE;DIRECAO;PROFUNDIDADE_VERTICAL_M;"
             "PROFUNDIDADE_SONDADOR_M;PROFUNDIDADE_MEDIDA_M;REFERENCIA_DE_PROFUNDIDADE;MESA_ROTATIVA;"
             "COTA_ALTIMETRICA_M;LAMINA_D_AGUA_M;DATUM_VERTICAL;UNIDADE_ESTRATIGRAFICA;"
             "GEOLOGIA_GRUPO_FINAL;GEOLOGIA_FORMACAO_FINAL;GEOLOGIA_MEMBRO_FINAL;CDPE;AGP;PC;PAG;"
             "PERFIS_CONVENCIONAIS;DURANTE_PERFURACAO;PERFIS_DIGITAIS;PERFIS_PROCESSADOS;"
             "PERFIS_ESPECIAIS;AMOSTRA_LATERAL;SISMICA;TABELA_TEMPO_PROFUNDIDADE;DADOS_DIRECIONAIS;"
             "TESTE_A_CABO;TESTE_DE_FORMACAO;CANHONEIO;TESTEMUNHO;GEOQUIMICA;SIG_SONDA;NOM_SONDA;"
             "DHA_ATUALIZACAO;ATINGIU_PRESAL")


def linha(**v):
    cols = CABECALHO.split(";")
    return ";".join(str(v.get(c, "")) for c in cols)


def csv_exemplo(cod="cp1252"):
    linhas = [CABECALHO,
              linha(POCO="1-AURI-12-RN", CADASTRO="72100021414", OPERADOR="Petrobras",
                    POCO_OPERADOR="1AURI12RN", ESTADO="RN", BACIA="Potiguar", CAMPO="AURIZÔNIA",
                    TERRA_MAR="T", TIPO="1 ", CATEGORIA="Pioneiro", SITUACAO="ABANDONADO",
                    INICIO="01/07/2005 00:00", LATITUDE_BASE_DD="-5,1234", LONGITUDE_BASE_DD="-36,98",
                    PROFUNDIDADE_SONDADOR_M="2150", MESA_ROTATIVA="12,5", PERFIS_DIGITAIS="S"),
              linha(POCO="7-GMR-13-RN", CADASTRO="72100000013", ESTADO="RN", BACIA="Potiguar",
                    CAMPO="GUAMARÉ", TERRA_MAR="T", TIPO="7", LATITUDE_BASE_DD="-5.11",
                    LONGITUDE_BASE_DD="-36.33"),
              linha(POCO="7-PRG-59H-RJS", BACIA="Campos", TERRA_MAR="M", TIPO="7",
                    LATITUDE_BASE_DD="-23,29", LONGITUDE_BASE_DD="-41,20"),
              linha(POCO="9-SEM-1-SE", BACIA="Sergipe", TERRA_MAR="T", LATITUDE_BASE_DD="999")]
    return ("\r\n".join(linhas) + "\r\n").encode(cod)


def test_ler_cadastro_converte_formatos():
    ps = {p["id"]: p for p in mpo.ler_cadastro(csv_exemplo())}
    a = ps["1-AURI-12-RN"]
    assert a["campo"] == "AURIZÔNIA" and a["tipo"] == 1 and a["inicio"] == "2005-07-01"
    assert a["lat"] == pytest.approx(-5.1234) and a["mesa_rotativa"] == 12.5
    assert json.loads(a["dados_anp"])["PERFIS_DIGITAIS"] == "S"
    assert ps["7-GMR-13-RN"]["lat"] == pytest.approx(-5.11)          # ponto também vale
    assert ps["9-SEM-1-SE"]["lat"] is None                              # fora do Brasil
    assert {p["id"] for p in mpo.ler_cadastro(csv_exemplo("utf-8"))} == set(ps)


def test_arquivo_que_nao_e_cadastro():
    with pytest.raises(mpo.ErroCadastro):
        mpo.ler_cadastro(b"a;b;c\n1;2;3\n")


@pytest.fixture
def banco(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    mpo.importar_cadastro(b, mpo.ler_cadastro(csv_exemplo()), "anp:teste")
    return b


def test_resolver_pelo_apelido_do_operador(banco):
    assert mpo.resolver(banco, "1AURI12RN") == "1-AURI-12-RN"
    assert mpo.resolver(banco, "7GMR_0013__RN") == "7-GMR-13-RN"
    assert mpo.resolver(banco, "poço estranho") == "POCOESTRANHO"


def test_reimportar_substitui(banco):
    r = mpo.importar_cadastro(banco, mpo.ler_cadastro(csv_exemplo())[:1], "anp:teste2")
    assert r["pocos"] == 1 and banco.contar("pocos") == 1


def test_mapa_filtros_e_ficha(banco):
    mpo.registrar_reate(banco, "Potiguar", "Categoria-7",
                        [{"nome": "7-GMR-13-RN", "caminho": "/POCO/C7/7-GMR-13-RN/", "parte": "C7_parte28"}])
    banco.registrar_arquivo("bruto/Potiguar/1-AURI-12-RN/a.dlis", poco_id="1-AURI-12-RN", bytes_=10)
    m = mpo.pocos_mapa(banco, bacia="Potiguar")
    linhas = {l[0]: dict(zip(m["colunas"], l)) for l in m["linhas"]}
    assert set(linhas) == {"1-AURI-12-RN", "7-GMR-13-RN"}
    assert linhas["7-GMR-13-RN"]["reate"] == 1 and linhas["1-AURI-12-RN"]["baixados"] == 1
    assert [l[0] for l in mpo.pocos_mapa(banco, so_reate=True)["linhas"]] == ["7-GMR-13-RN"]
    assert [l[0] for l in mpo.pocos_mapa(banco, texto="aurizô")["linhas"]] == ["1-AURI-12-RN"]
    assert [l[0] for l in mpo.pocos_mapa(banco, terra_mar="M")["linhas"]] == ["7-PRG-59H-RJS"]
    f = mpo.ficha(banco, "7-GMR-13-RN")
    assert f["no_cadastro"] and f["reate"][0]["parte"] == "C7_parte28"
    assert mpo.ficha(banco, "X-NADA") is None
    assert {b["bacia"]: b["no_reate"] for b in mpo.bacias(banco)}["Potiguar"] == 1


def test_catalogo_json_antigo_entra_no_banco(tmp_path, banco):
    pasta = tmp_path / "catalogo" / "Potiguar"
    pasta.mkdir(parents=True)
    (pasta / "categorias.json").write_text("{}")
    (pasta / "Categoria-7.json").write_text(json.dumps({
        "bacia": "Potiguar", "categoria": "Categoria-7",
        "pocos": [{"nome": "7-GMR-13-RN", "caminho": "/POCO/x/7-GMR-13-RN/", "parte": None}]}))
    assert mpo.importar_catalogo_json(banco, str(tmp_path / "catalogo")) == 1


def test_ponte_id_canonico_nos_arquivos(api, tmp_path):
    api.escolher_pasta()
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7GMR_0013__RN" / "Pasta"
    pasta.mkdir(parents=True)
    (pasta / "x.pdf").write_bytes(b"%PDF-1.4")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    assert api._banco.arquivos()[0]["poco_id"] == "7-GMR-13-RN"
    assert api.ficha_poco("7-GMR-13-RN")["arquivos"][0]["rel"].endswith("x.pdf")


def test_catalogar_bacia_inteira(api):
    from conftest import ArvoreFalsa, item
    api.escolher_pasta()
    arvore = ArvoreFalsa({
        "/": [item("POCO", True)],
        "/POCO/": [item("Categoria-1", True), item("Categoria-7", True)],
        "/POCO/Categoria-1/": [item("1-AURI-12-RN", True)],
        "/POCO/Categoria-7/": [item("Categoria-7_parte1", True)],
        "/POCO/Categoria-7/Categoria-7_parte1/": [item("7-GMR-13-RN", True), item("7GMR_0027__RN", True)],
    })

    class Cliente:
        listar = staticmethod(arvore)
    from motor.reate import ClienteREATE
    c = ClienteREATE("x", pausa_s=0)
    c.listar = arvore
    api._cliente, api._bacia, api._base_remota = c, "Potiguar", "/POCO/"
    r = api.catalogar_bacia()
    assert r["ok"] and r["pocos"] == 3 and r["categorias"] == 2
    with api._banco.conexao() as cx:
        ids = sorted(x[0] for x in cx.execute("SELECT poco_id FROM reate"))
    assert ids == ["1-AURI-12-RN", "7-GMR-13-RN", "7-GMR-27-RN"]
