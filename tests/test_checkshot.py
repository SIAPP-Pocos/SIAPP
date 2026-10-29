"""Checkshot (0.42): SEG-Y sintético, cálculo do tempo vertical, uso na ficha e nos perfis."""
import os

import pytest

import checkshot_util as cu
from motor import checkshot as mck
from motor import dados_poco as mdp
from motor import pocos as mpo

POCO = "1-SIAPP-1-RN"
PASTA = f"bruto/Potiguar/{POCO}/Sismica de Poco"
V = 2000.0


def vertical(caminho, **kw):
    # poço vertical, fonte na boca: tempo vertical = tempo de chegada; V = 2.000 m/s até 1.000 m e 4.000 abaixo
    niveis = [(100.0, 100.0, 100 / V, 0, 0), (1000.0, 1000.0, 1000 / V, 0, 0), (1400.0, 1400.0, 0.5 + 400 / 4000, 0, 0)]
    return cu.gerar(caminho, niveis, **kw)


def test_reconhece():
    assert mck.reconhece(f"{PASTA}/x_asr-3_stack.sgy") and mck.reconhece("a/b/poco_checkshot.segy")
    assert not mck.reconhece("bruto/P/X/Sismica 3D/cubo.sgy") and not mck.reconhece(f"{PASTA}/relatorio.pdf")
    assert mck.tipo_pelo_nome(f"{PASTA}/x_asr-3_raw.sgy") == "vsp_bruto"
    assert mdp.leitor_para(f"{PASTA}/x_asr-3_stack.sgy") == "checkshot"


def test_mapa_do_cabecalho_textual():
    m = mck.mapa_bytes("\n".join(f"C{k} {t}" for k, t in enumerate(cu.MAPA, 35)))
    assert m["receiver_md"] == 173 and m["times_pick"] == 209 and m["source_sd"] == 193 and m["seismicdatumelev"] == 57


def test_vertical_sem_afastamento(tmp_path):
    d = mck.ler(vertical(str(tmp_path / "a_stack.sgy")))
    assert d["documento"] == "checkshot" and d["cabecalho"]["poco"] == POCO and d["apelidos"] == ["1-ABC-1-RN"]
    n = d["niveis"]
    assert [x["md"] for x in n] == [100.0, 1000.0, 1400.0]                  # 4 componentes, um nível
    assert [x["twt_ms"] for x in n] == [100.0, 1000.0, 1200.0]
    assert [x["vmed_m_s"] for x in n] == [2000, 2000, 2333] and [x["vint_m_s"] for x in n] == [2000, 2000, 4000]
    assert mck.twt_em(n, 1200.0) == 1100.0 and mck.twt_em(n, 50.0) is None
    assert d["referencia"] == {"elev_mesa_m": 50.0, "datum_sismico_m": 50.0, "prof_fonte_m": 0.0, "afastamento_m": 0.0}
    assert "MD_m;TVD_m;TVDSD_m;Tcorr_s;TWT_ms;Vmed_m_s;Vint_m_s" in mck.csv(n, POCO)


def test_afastamento_fonte_e_datum(tmp_path):
    # mesa a 55 m, datum e fonte a 50 m, fonte 2 m abaixo, 30 m de afastamento: fonte a 48 m de elevação, receptor a TVD 47 (dz = 47 − 7 = 40) → raio de 50 m
    caminho = cu.gerar(str(tmp_path / "b.sgy"), [(47.0, 47.0, 0.025, 0, 0)], elev_mesa=55.0, datum=50.0,
                       elev_fonte=50.0, prof_fonte=2.0, fonte_xy=(30.0, 0.0), ts_us=1000, ebcdic=False)
    n = mck.ler(caminho)["niveis"][0]
    assert n["sgo_m"] == 30.0 and n["tv_s"] == pytest.approx(0.025 * 40 / 50) and n["tcorr_s"] == pytest.approx(0.021)
    assert n["tvdsd"] == 42.0 and n["twt_ms"] == 42.0


def test_sem_mapa_e_bruto(tmp_path):
    with pytest.raises(mck.ErroCheckshot, match="Receiver:MD"):
        mck.ler(vertical(str(tmp_path / "c.sgy"), com_mapa=False))
    d = mck.ler(vertical(str(tmp_path / "d_raw.sgy")))
    assert d["documento"] == "vsp_bruto" and d["tiros"] == 12 and d["profundidades"] == [100.0, 1000.0, 1400.0]
    assert mck.itens(d) == []
    (tmp_path / "e.sgy").write_bytes(b"curto")
    with pytest.raises(mck.ErroCheckshot):
        mck.ler(str(tmp_path / "e.sgy"))


def test_no_projeto_ficha_perfis_e_csv(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, *PASTA.split("/"))
    os.makedirs(pasta)
    vertical(os.path.join(pasta, f"{POCO}_asr-3_stack.sgy"))
    vertical(os.path.join(pasta, f"{POCO}_asr-3_raw.sgy"))
    api._abrir_projeto(api._projeto.pasta)
    f = api.ficha_poco(POCO)
    ck = f["dados_poco"]["checkshot"]
    assert len(ck) == 1 and len(ck[0]["niveis"]) == 3 and "checkshot" not in f["dados_poco"]["itens"]
    assert {d["documento"] for d in f["dados_poco"]["documentos"]} == {"checkshot", "vsp_bruto"}
    assert mpo.resolver(api._banco, "1-ABC-1-RN") == POCO
    assert api._formularios_perfil(POCO)["checkshot"] == [{"md": 100.0, "twt": 100.0}, {"md": 1000.0, "twt": 1000.0},
                                                         {"md": 1400.0, "twt": 1200.0}]
    r = api.exportar_checkshot(POCO)
    assert r["ok"] and r["niveis"] == 3
    with open(os.path.join(api._projeto.pasta, r["arquivo"]), encoding="utf-8") as fh:
        assert fh.read().splitlines()[2] == "100.0;100.0;100.0;0.05;100.0;2000;2000"
    assert "não tem checkshot" in api.exportar_checkshot("7-OUTRO-1-RN")["erro"]
