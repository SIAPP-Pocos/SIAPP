"""Dados sintéticos de pressão: estação de teste a cabo, DLIS falso (objetos no formato do dlisio),
relatório de TFR (PDF com o leiaute do formulário) e registros de manômetro (.TPR), num ZIP com
ZIP dentro, como no REATE. Valores inventados; poço fictício 1-SIAPP-1-RN."""
import io
import zipfile

import numpy as np
import pymupdf


def estacao(p_form=2500.0, hidro=3000.0, dt=0.25, pretestes=2, fechada=False, sem_vedacao=False, ruido=0.05,
            semente=1):
    """Tempo (s) e pressão (psi) de uma estação: lama, assentamento, pré-testes, patamar, lama."""
    rng = np.random.default_rng(semente)
    t, p = [], []

    def trecho(dur, f):
        t0 = t[-1] + dt if t else 0.0
        for k in range(int(dur / dt)):
            t.append(t0 + k * dt)
            p.append(f(k * dt))

    trecho(40, lambda s: hidro)
    trecho(20, lambda s: hidro + 50 * min(1, s / 10))                # aperto do assentamento
    if sem_vedacao:
        trecho(120, lambda s: hidro + 2)
    else:
        for i in range(pretestes):
            base = p[-1]
            trecho(5, lambda s, b=base: b - (b - (p_form - 400)) * s / 5)       # queda do pré-teste
            if fechada:
                trecho(90, lambda s: (p_form - 400) + 300 * (1 - np.exp(-s / 400)))
            else:
                trecho(70, lambda s: p_form - 400 * np.exp(-s / 4))
        fim = p[-1]
        trecho(8, lambda s, b=fim: b + 2.5 * s)                          # sonda começando a soltar
        trecho(4, lambda s, b=fim + 20: b + (hidro + 60 - b) * s / 4)    # solta: volta para a lama
    trecho(40, lambda s: hidro)
    p = np.array(p) + rng.normal(0, ruido, len(p))
    return np.array(t), p


class _Canal:
    def __init__(self, nome, unidade):
        self.name, self.units = nome, unidade


class _Param:
    def __init__(self, nome, valor):
        self.name, self.values = nome, np.array([valor])


class _Origem:
    well_name = "1-SIAPP-1-RN"


class _Quadro:
    index_type = "TIME"

    def __init__(self, t_ms, p_psi, prof):
        self._d = np.zeros(len(t_ms), dtype=[("FRAMENO", "i4"), ("ETIM", "f8"), ("FPRE", "f8"), ("HYDP", "f8"),
                                              ("DEPT", "f8")])
        self._d["ETIM"], self._d["FPRE"], self._d["HYDP"], self._d["DEPT"] = t_ms, p_psi, 4000.0, prof
        self.channels = [_Canal("ETIM", "ms"), _Canal("FPRE", "psia"), _Canal("HYDP", "psia"), _Canal("DEPT", "m")]

    def curves(self):
        return self._d


class _ArquivoLogico:
    def __init__(self, quadros, params):
        self.frames, self.parameters, self.origins = quadros, params, [_Origem()]


def dlis_falso(estacoes=((1500.0, 2130.0), (1510.0, 2137.0), (1540.0, 2180.0), (1560.0, 2209.0))):
    """Lista de arquivos lógicos (um por estação) como o dlisio devolve."""
    params = [_Param("LNAM", "SFT/GR"), _Param("TOOL", "SFT/GR"), _Param("TTL1", "1-ABC-1-RN"), _Param("DFD", "10.0"),
              _Param("DFT", "BASE AGUA"), _Param("MRT", "160.0"), _Param("BHT", "-999.25"), _Param("R1", "1.NOTA DE TESTE")]
    saida = []
    for k, (prof, pf) in enumerate(estacoes):
        t, p = estacao(p_form=pf, hidro=pf + 500, semente=k + 1)
        saida.append(_ArquivoLogico([_Quadro(t * 1000.0, p, prof)], params))
    return saida


TPR = """# # POM-GO PETROBRAS: 1-ABC-1-RN
# # TESTE: TFR-1
# # REGISTRADOR No: {reg} - 20Kpsi
# # POSIÇÃO NA COLUNA: {pos}
# # PROFUNDIDADE (MD): {prof} m
# # TIPO DE SENSOR: QUARTZO

;   DATA   \t  HORA   \t  D.TIME   \t  PRESSÃO   \tTEMPERATURA
;(dd/mm/aaaa)\t(hh:mm:ss)   \t  (h)   \t  (kgf/cm2)\t(degC)
"""


def tpr(reg="11111", pos="INTERNO", prof="1.398,0", n=400, p_max=150.0):
    linhas = [TPR.format(reg=reg, pos=pos, prof=prof)]
    for k in range(n):
        h = k * 10 / 3600
        pr = 1.0 + p_max * min(1, k / 50) - (20 if 150 < k < 250 else 0)
        linhas.append(f"01/04/2010\t10:{k // 60 % 60:02d}:{k % 60:02d}\t{h:10.6f}\t{pr:10.3f}\t{30 + k * 0.1:.3f}")
    return "\r\n".join(linhas).encode("cp1252")


RELATORIO = [
    [  # capa
        (101, 189, "RELATÓRIO DE INTERPRETAÇÃO DE TESTE EM POÇO"),
        (106, 298, "NÚMERO DO RELATÓRIO:"), (354, 298, "001/2010 - TESTE"),
        (106, 323, "SIGLA DO POÇO - ANP:"), (356, 323, "1-SIAPP-1-RN"),
        (106, 348, "SIGLA DO POÇO - PETROBRAS:"), (369, 348, "1-ABC-1-RN"),
        (106, 398, "IDENTIFICAÇÃO DO TESTE:"), (381, 398, "TFR-01"),
        (106, 423, "INTERVALO TESTADO - TOPO:"), (377, 423, "1.395 (m)"),
        (106, 448, "INTERVALO TESTADO - BASE:"), (377, 448, "1.400 (m)"),
        (106, 473, "DATA DE INÍCIO DO TESTE:"), (374, 473, "01/04/2010"),
        (106, 498, "DATA DO FIM DO TESTE:"), (374, 498, "05/04/2010"),
    ],
    [  # identificação e conclusões
        (166, 76, "Sigla do poço ANP:"), (261, 76, "1-SIAPP-1-RN"),
        (269, 162, "Identificação"),
        (65, 276, "Cia. executante"), (165, 276, "CIA FICTÍCIA"), (307, 276, "Formação"), (407, 276, "AÇU"),
        (60, 478, "1. Conclusividade do Teste em Relação aos Objetivos"),
        (65, 509, "Conclusivo"), (65, 521, "Intervalo portador de óleo, produtividade média."),
        (60, 592, "2. Parâmetros da Formação"),
        (65, 621, "Fluido do Intervalo e Propriedades"), (70, 640, "Óleo de 2,1 cp."),
        (65, 663, "Parâmetros da Formação e Modelo Utilizado"), (70, 682, "Fluxo radial homogêneo."),
        (497, 778, "2 /4"),
    ],
    [  # resultados
        (166, 76, "Sigla do poço ANP:"), (261, 76, "1-SIAPP-1-RN"),
        (70, 140, "Primeiro período:    pfi1  =  120,5 kg/cm2    pff1  = 128,0 kg/cm2      pest1  = 141,70 kg/cm2"),
        (70, 152, "Segundo período    pfi2  =  118,2   \"            pff2  =  130,4   \"             pest2  =  141,52 kg/cm2"),
        (65, 170, "Registrador utilizado na interpretação: 11111 CGM5"),
        (208, 283, "Resultados Obtidos da Interpretação"),
        (176, 355, "Medida (m)"), (464, 355, "1.398,00"),
        (65, 409, "Pressão estática EXTRAPOLADA (kgf/cm²)"), (467, 409, "141,70"),
        (65, 427, "Pressão de fluxo FINAL (kgf/cm²)"), (470, 427, "130,4"),
        (65, 445, "Vazão (m³/dia) - abt 16/64 SURGENTE"), (472, 445, "45,5"),
        (65, 484, "°API do óleo (60°F)"), (472, 484, "31,2"),
        (65, 520, "Temperatura máxima registrada (°C)"), (472, 520, "71,5"),
        (65, 592, "IP (pseudo-permanente) (m³/D)/(kgf/cm²)"), (475, 592, "4,1"),
        (65, 610, "Transmissibilidade do óleo (mD.m/cP)"), (466, 610, "1.250,0"),
        (65, 628, "Mobilidade do óleo (mD/cP)"), (470, 628, "250,0"),
        (65, 646, "Permeabilidade efetiva ao óleo (mD)"), (474, 646, "525"),
        (65, 664, "Efeito de película total"), (478, 664, "-1,5"),
        (65, 682, "Raio de investigação (m)"), (474, 682, "310"),
        (65, 700, "Profundidade de referência de pressão nos canhoneados (m)"), (464, 700, "1.398,00"),
    ],
    [  # fluidos e períodos
        (166, 76, "Sigla do poço ANP:"), (261, 76, "1-SIAPP-1-RN"),
        (153, 162, "Identificação e Medição dos Fluidos Recuperados no Teste"),
        (65, 194, "Período:"), (238, 194, "F1"), (316, 194, "F2"),
        (65, 210, "Duração (hh:mm):"), (238, 210, "0:30"), (316, 210, "20:00"),
        (65, 226, "Fluido:"), (238, 226, "ÓLEO"), (316, 226, "ÓLEO"),
        (65, 306, "Vazão de líquido corrigida (m³/d):"), (238, 306, "50,0"), (316, 306, "45,5"),
        (65, 338, "Abertura (1/64''):"), (316, 338, "16"),
        (65, 466, "Pressão de fluxo final (kgf/cm²):"), (238, 466, "128,0"), (316, 466, "130,4"),
        (65, 640, "Vazão de gás estimada pela RGO do segundo fluxo."),
    ],
]


def relatorio_pdf() -> bytes:
    doc = pymupdf.open()
    for linhas in RELATORIO:
        pg = doc.new_page(width=595, height=842)
        for x, y, t in linhas:
            pg.insert_text((x, y + 7.5), t, fontsize=7, fontname="helv")
    b = doc.tobytes()
    doc.close()
    return b


def tfr_zip() -> bytes:
    regs = io.BytesIO()
    with zipfile.ZipFile(regs, "w") as z:
        z.writestr("1-SIAPP-1-RN-TFR-1#11111-INT.TPR", tpr("11111", "INTERNO", "1.398,0"))
        z.writestr("1-SIAPP-1-RN-TFR-1#22222-FUN.TPR", tpr("22222", "FUNDO", "1.402,5", p_max=151.0))
        z.writestr("leia-me.txt", "registros")
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("Anexo/1-SIAPP-1-RN_TFR-01_Relatório Final.pdf", relatorio_pdf())
        z.writestr("Anexo/1-SIAPP-1-RN-TFR-1_Regs.zip", regs.getvalue())
    return saida.getvalue()
