"""Planilhas sintéticas de petrofísica básica (.xlsx) com o formato das do REATE: texto com vírgula decimal nos
plugs, números no COREGAMA. Valores inventados para o teste."""

import openpyxl

POCO_ANP = "1SIAPP 0001  RN"
CAB_PLUGS = ["Unidade", "Poço Petrobras", "Poço Anp", "Tipo Amostra", "Dir. Amostra", "Nr. Amostra", "Profundidade",
             "Porosidade%", "Densidade", "Permeabilidade Long. (mD)", "Pressão(psi)"]
# (profundidade, porosidade, densidade, permeabilidade, direção, número)
PLUGS = [("1000,5", "18,2", "2,66", "1.234,5", "VH1", "1"), ("1001,3", "9,8", "2,71", "0,85", "VH1", "2"),
         ("1001,3", "21,0", "2,65", "310,1", "VV", "3")]


def plugs(caminho, *, com_data=False, linhas=PLUGS, poco=POCO_ANP):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet0"
    cab = (["Data Análise"] if com_data else []) + CAB_PLUGS
    ws.append(cab)
    for p, phi, rho, k, d, n in linhas:
        ln = ["UO-TESTE", poco, poco, "Plug", d, n, p, phi, rho, k, "2330"]
        ws.append((["19/10/2016"] if com_data else []) + ln)
    ws.append([""] * len(cab))
    ws.append([""] * len(cab))
    wb.save(caminho)
    return caminho


def coregama(caminho, *, poco=POCO_ANP, topo=1000.0, base=1002.0, passo=0.5, gr0=20.0):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plan1"
    ws.append(["POCO_ANP", "TEST", "TOPO", "BASE", "PROF_ANALISADA", "RAIOS_GAMA_API"])
    p, k = topo, 0
    while p < base:
        ws.append([poco, 1.0, topo, base, p, gr0 + k])
        p, k = p + passo, k + 1
    wb.save(caminho)
    return caminho
