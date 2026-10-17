"""Dados direcionais: os cinco leiautes (textos sintéticos no formato dos arquivos do
REATE), curvatura mínima, poço trocado, banco e leitura pelo levantamento."""
import math

import pytest

from motor import direcionais as md
from motor.banco import Banco

ANTIGO = """ SIGLA 7-XX -0001D -RN
 ==========================
                         VISUALIZACAO DE DADOS DE POCOS DIRECIONAIS/DESVIADOS
                    - PROFUNDIDADE   -  PROFUNDIDADE  -
                    -    MEDIDA      -    VERTICAL    -  INCLINACAO   -  DIRECAO  -

                    -       100.0    -      100.00    -         .00   -  N0 .00E  -
                    -       200.0    -      199.00    -       10.00   -  N90.00E  -
1
                    - PROFUNDIDADE   -  PROFUNDIDADE  -
                    -    MEDIDA      -    VERTICAL    -  INCLINACAO   -  DIRECAO  -
                    -       300.0    -      296.00    -       20.00   -  S45.00W  -
"""

NOVO = """ _______________________________________________
 WELL NAME (Sigla Anp)        :    7-xx-2d-rn
 CADASTRO ANP                 :      72100099999
 DATUM                        :      SIRGAS 2000
 DEPTH REFERENCE              :               MR
 DEPTH REFERENCE ELEV (m)     :            40.00
 _______________________________________________

PROFUNDIDADE  INCLINACAO  PROFUNDIDADE  AZIMUTE  RUMO      AFAST N/S  AFAST E/W  LATITUDE       LONGITUDE      UTM NORTE    UTM ESTE
MEDIDA (m)     (graus)    VERTICAL (m)                        (m)        (m)       (GMS)          (GMS)           (m)         (m)

0.00          0.00        0.00          0.00     (N00.00E) 0.00       0.00       -05:23:50,782  -36:56:20,388  9403016.60   728376.70
100.00        0.00        100.00        0.00     (N00.00E) 0.00       0.00       -05:23:50,782  -36:56:20,388  9403016.60   728376.70
400.00        30.00       386.48        90.00    (N90.00E) 0.00       76.76      -05:23:50,782  -36:56:17,900  9403016.60   728453.46
"""

TABULADO = ("_______________________________________________\n\nNome do poço:   7XX  0003  RN\n"
            "Cadastro do poço: 721000999990\nElevação de referência (m): 42.90\n"
            "_______________________________________________\n"
            "Profundidade\tInclinação\tProfundidade\tAzimute\tN\\S\tE\\W\tLatitude\tLongitude\tInstrumento\n"
            "Medida(m)\t(graus)\tVertical(m)\t(m)\n"
            "0.00\t0.00\t0.00\t0.00\t9403296.20\t732982.80\t-05:23:41,170\t-36:53:50,842\t-999.25\n"
            "274.00\t0.00\t274.00\t0.00\t9403296.18\t732982.78\t-05:23:41,170\t-36:53:50,842\t-999.25\n")

COORDENADAS = """ Sigla:    7XX 0004D RN
- COORDENADAS - COORDENADAS -     COORDENADAS     -     COORDENADAS      - PROFUNDIDADE - PROFUNDIDADE - INCLINACAO -       DIRECAO       -
   UTM ESTE      UTM NORTE          GMS LAT              GMS LONG             MEDIDA        VERTICAL
-   766720.93 -  9431219.74 -  05º 08' 28.447" S  -   36º 35' 38.897" W  -     0.00     -     0.00     -     0.00   -     0.00  (N00.00E) -
-   766720.61 -  9431219.35 -  05º 08' 28.460" S  -   36º 35' 38.907" W  -   229.00     -   228.99     -     2.00   -   219.00  (S39.00W) -
"""

DEVIATION = """                                                DEVIATION DATA
WELL: 1-XX-5-RN
 Depth    Dev    AvgDev IntervalDev.Dir.Displac.Interval  TVD    Acum.  Depart. Azimuth Azimuth Partial Displ.(m)Acum. Displ.(m)  Dog
 (mbdf)  (deg)   (deg)    (m)     (m)     (m)   TVD (m)  (mbdf) Displ (m  (m)    (deg)    Avg.   N+/S-   E+/W-   N+/S-   E+/W -   Leg
  0.0     0.0     0.00    0.0     0.00    0.00    0.0     0.0     0.00    0.0    360.0    0.0     0.0     0.0     0.0     0.0     0.0
 142.0    0.5     0.25   142.0    0.62   -0.14   -142.0  -142.0  -0.14    0.6    347.0   173.5    -0.6    0.1     -0.6    0.1     0.1
"""


@pytest.mark.parametrize("q1, graus, q2, az", [("N", 58, "W", 302), ("S", 13.41, "E", 166.59), ("N", 0, "E", 0),
                                               ("S", 42, "W", 222), ("N", 37, "E", 37)])
def test_rumo_para_azimute(q1, graus, q2, az):
    assert md.rumo_para_azimute(q1, graus, q2) == pytest.approx(az)


@pytest.mark.parametrize("texto, leiaute, n, poco", [
    (ANTIGO, "antigo", 4, "7-XX -0001D -RN"), (NOVO, "novo", 3, "7-xx-2d-rn"), (TABULADO, "tabulado", 2, "7XX 0003 RN"),
    (COORDENADAS, "coordenadas", 2, "7XX 0004D RN"), (DEVIATION, "deviation", 2, "1-XX-5-RN")])
def test_leiautes(texto, leiaute, n, poco):
    d = md.ler(texto)
    assert d["leiaute"] == leiaute and len(d["md"]) == n and d["poco_arquivo"] == poco


def test_curvatura_minima_trecho_reto_inclinado():
    # 100 m vertical, depois ganho de ângulo até 30° para leste em 300 m: o afastamento é
    # 300·(1 − cos 30°)/(30° em rad) e a vertical 300·sen 30°/(30° em rad) (arco de círculo)
    d = md.ler(NOVO)
    arco = math.radians(30)
    assert d["leste"][-1] == pytest.approx(300 * (1 - math.cos(arco)) / arco, abs=0.05)
    assert d["norte"][-1] == pytest.approx(0, abs=1e-6)
    assert d["tvd"][-1] == pytest.approx(100 + 300 * math.sin(arco) / arco, abs=0.05)
    assert d["dif_tvd_max"] < 0.05                       # confere com a vertical do arquivo
    assert d["elevacao_ref"] == 40.0 and d["cadastro"] == "72100099999"


def test_antigo_rumo_e_posicao_abaixo_da_ultima_estacao():
    d = md.ler(ANTIGO)
    assert d["azimute"][-1] == pytest.approx(225)        # S45W
    n, l, t = md.posicao(d, [150, 300, 400])
    assert t[1] == pytest.approx(d["tvd"][-1]) and t[2] > t[1]   # prolonga a última direção
    assert n[2] < n[1] and l[2] < l[1]                   # segue para sudoeste


def test_nao_reconhecido():
    with pytest.raises(md.ErroDirecional):
        md.ler("cabeçalho de perfis\n153 01 SDL HALLIBURTON 215.00( -164.01)\n")


def test_eh_direcional():
    assert md.eh_direcional("7-xx-1-rn_direc.txt", "Dados Direcionais")
    assert md.eh_direcional("x_dd.txt", "Dados_direcionais")
    assert not md.eh_direcional("7XX_pasta_poco_pub.pdf", "Dados_direcionais")
    assert not md.eh_direcional("7-xx-1-rn_cabecalho.txt", "Dados_direcionais")


class Portal:
    def __init__(self, arquivos):
        self.arquivos, self.lidos = arquivos, []

    def ler_inicio(self, caminho, n=1024):
        self.lidos.append(caminho)
        return self.arquivos[caminho][:n]


def test_banco_poco_trocado_e_reaproveitamento(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    P = "/POCO/Categoria-7/7-XX-2D-RN/"
    with b.conexao() as c:
        c.execute("INSERT INTO acervo_pocos (bacia, caminho, poco_id, categoria) VALUES ('Potiguar', ?, '7-XX-2D-RN', "
                  "'Categoria-7')", (P,))
        for nome, dados in (("7-xx-2d-rn_direcionais.txt", NOVO), ("7-yy-9-ba_direcional.txt", ANTIGO)):
            c.execute("INSERT INTO acervo_arquivos (bacia, caminho, poco_caminho, nome, pasta, tamanho) "
                      "VALUES ('Potiguar', ?, ?, ?, 'Dados Direcionais', ?)", (P + "Dados Direcionais/" + nome, P, nome,
                                                                               len(dados.encode("cp1252"))))
    portal = Portal({P + "Dados Direcionais/7-xx-2d-rn_direcionais.txt": NOVO.encode("cp1252"),
                     P + "Dados Direcionais/7-yy-9-ba_direcional.txt": ANTIGO.encode("cp1252")})
    fila = md.pendentes(b, "Potiguar", ["Categoria-7"])
    assert len(fila) == 2
    assert md.ler_do_portal(b, portal, "Potiguar", fila, pasta_projeto=str(tmp_path)) == 2
    traj = md.do_poco(b, "7-XX-2D-RN")
    # o arquivo antigo é do 7-XX-1D-RN (cabeçalho): não é usado, mesmo tendo mais estações
    assert traj["leiaute"] == "novo" and traj["confere"] is True
    assert md.pendentes(b, "Potiguar") == []
    with b.conexao() as c:
        c.execute("UPDATE direcionais SET leitor = 0")
    portal.lidos.clear()
    md.ler_do_portal(b, portal, "Potiguar", md.pendentes(b, "Potiguar"), pasta_projeto=str(tmp_path))
    assert portal.lidos == []                            # relê da cópia local
    r = md.resumo(b, "Potiguar")
    assert r == {"direcionais_disponiveis": 2, "direcionais_lidos": 2, "direcionais_com_trajetoria": 2}


def test_levantamento_le_os_direcionais(tmp_path):
    from test_levantamento import SUL_DLIS, ClienteFalso, rodar
    b = Banco(str(tmp_path / "p.sqlite"))
    P = "/POCO/Categoria-7/7-XX-2D-RN/"
    falso = ClienteFalso({P + "Perfil Convencional/x.dlis": SUL_DLIS,
                          P + "Dados Direcionais/7-xx-2d-rn_direcionais.txt": NOVO.encode("cp1252")})
    r, ev = rodar(b, falso, ["Categoria-7"], direcionais=True, pasta_projeto=str(tmp_path))
    assert r["direcionais_lidos"] == 1 and any(e["tipo"] == "direcional" for e in ev)
    assert md.do_poco(b, "7-XX-2D-RN")["afastamento_max"] > 70
