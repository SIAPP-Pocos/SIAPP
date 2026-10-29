"""SEG-Y sintético de sísmica de poço (checkshot), no leiaute Halliburton: o mapa dos campos no cabeçalho textual."""
import struct

MAPA = ["SeismicDatumElev@57,Microseconds@205",
        "Receiver:MD@173,TVD@181,RefElev@185,RCX@81,RCY@85",
        "Source:SCX@73,SCY@77,SD@193,RefElev@189,S2Monitor@197",
        "Times(us):pick@209,ref@213,DatumCorr@225,ExtDelay@221,1stSamp@217",
        "SEG Y REV1", "END EBCDIC"]


def gerar(caminho, niveis, *, poco="1-SIAPP-1-RN", operador="1-ABC-1-RN", elev_mesa=50.0, datum=50.0,
          elev_fonte=50.0, prof_fonte=0.0, fonte_xy=(0.0, 0.0), ts_us=0, ebcdic=True, com_mapa=True, ns=10):
    """`niveis`: [(md, tvd, pick_s, rx, ry)]; 4 componentes por nível, como no stack da Halliburton."""
    linhas = ["CLIENTE/OPERADORA: TESTE", "COMPANHIA: SINTETICA", f"POCO (SIGLA ANP): {poco}",
              f"POCO (SIGLA OPERADORA): {operador}", "CADASTRO ANP: 99999999999", "DATA: 01/02/2010"]
    linhas += [""] * (34 - len(linhas)) + (MAPA if com_mapa else ["", "", "", "", "SEG Y REV1", "END EBCDIC"])
    texto = "".join(f"C{k + 1:02d} {t}".ljust(80) for k, t in enumerate(linhas[:40]))
    texto = texto.ljust(3200)
    cab = texto.encode("cp037" if ebcdic else "ascii")
    binario = bytearray(400)
    struct.pack_into(">H", binario, 16, 1000)        # intervalo (µs)
    struct.pack_into(">H", binario, 20, ns)          # amostras
    struct.pack_into(">H", binario, 24, 5)           # IEEE float
    with open(caminho, "wb") as f:
        f.write(cab + bytes(binario))
        k = 0
        for nivel, (md, tvd, pick, rx, ry) in enumerate(niveis, 1):
            for comp in (12, 13, 9, 14):
                h = bytearray(240)
                k += 1
                struct.pack_into(">i", h, 0, k)
                struct.pack_into(">i", h, 20, nivel)
                struct.pack_into(">h", h, 28, comp)
                struct.pack_into(">h", h, 68, -10)              # escalar das elevações
                struct.pack_into(">h", h, 70, -10)              # escalar das coordenadas

                def i4(pos, v):
                    struct.pack_into(">i", h, pos - 1, int(round(v)))
                i4(57, datum * 10)
                i4(173, md * 10); i4(181, tvd * 10); i4(185, elev_mesa * 10)
                i4(81, rx * 10); i4(85, ry * 10)
                i4(73, fonte_xy[0] * 10); i4(77, fonte_xy[1] * 10)
                i4(193, prof_fonte * 10); i4(189, elev_fonte * 10)
                i4(209, pick * 1e6); i4(225, ts_us)
                f.write(bytes(h) + struct.pack(f">{ns}f", *([0.0] * ns)))
    return caminho
