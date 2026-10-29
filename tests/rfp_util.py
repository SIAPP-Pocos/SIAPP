"""Formulários CDPE sintéticos (RFP, RFCP, Perfuração) com o leiaute da ANP.

As posições (x, y do topo do texto, em pt, página A4 595 × 841) copiam as dos formulários reais;
os valores são inventados (poço fictício 1-SIAPP-1-RN). Nenhum documento original vai para o git.
"""
import pymupdf

CABECALHO = [(194, 25, "ANP - Agência Nacional do Petróleo,"), (480, 29, "Data:"), (516, 30, "13/09/2019"),
             (210, 39, "Gás Natural e Biocombustíveis"), (480, 66, "Hora:"), (516, 66, "17:51"), (272, 68, "CDPE")]


def _rodape(n):
    return [(564, 787, str(n)), (23, 788, "SDT - SUPERINTENDÊNCIA DE OBTENÇÃO E GESTÃO DE DADOS TÉCNICOS")]


RFP = [
    [  # página 1
        (202, 107, "RELATÓRIO FINAL DE POÇO EXPLORATÓRIO"), (258, 141, "DADOS DO POÇO"),
        (17, 163, "Poço:"), (209, 163, "Bloco:"), (389, 163, "Bacia:"),
        (17, 175, "1-SIAPP-1-RN"), (209, 175, "POT-T-999"), (389, 175, "Potiguar"),
        (17, 193, "Data Término da Perfuração:"), (209, 193, "Data Conclusão:"),
        (389, 193, "Profundidade Final do Sondador (m):"),
        (17, 205, "02/03/2010"), (209, 205, "20/03/2010"), (389, 205, "1.850,00"),
        (17, 223, "Unidade Estratigráfica"), (209, 223, "Profundidade Final por Perfil -"),
        (389, 223, "Profundidade Final por Perfil -"),
        (17, 235, "na Profundidade Final:"), (209, 235, "medida (m) :"), (389, 235, "em cota (m):"),
        (17, 247, "FM PENDÊNCIA"), (209, 247, "1.852,50"), (389, 247, "-1.740,30"),
        (17, 265, "Elevação BAP:"), (209, 265, "Lâmina d'água(m):"), (389, 265, "Mesa Rotativa(m):"),
        (19, 277, "106,20"), (209, 277, "0,00"), (389, 277, "112,20"),
        (72, 310, "COORDENADAS"), (261, 310, "COORDENADAS"), (450, 310, "COORDENADAS"),
        (59, 322, "DEFINITIVAS DA BASE"), (248, 322, "DEFINITIVAS DO ALVO"), (434, 322, "DEFINITIVAS DO FUNDO"),
        (17, 340, "Latitude:"), (113, 340, "Longitude:"), (209, 340, "Latitude:"), (305, 340, "Longitude:"),
        (401, 340, "Latitude:"), (491, 340, "Longitude:"),
        (17, 352, "-05:30:00,000"), (113, 352, "-37:15:36,000"), (209, 352, "-05:30:01,800"),
        (305, 352, "-37:15:36,000"),
        (248, 376, "RESULTADO DO POÇO"),
        (17, 397, "Poço Descobridor de Campo:"), (209, 397, "Tipo de Fluido Descoberto:"), (389, 397, "Tipo de Abandono:"),
        (17, 409, "S"), (209, 409, "ÓLEO"),
        (17, 433, "Razão do Abandono:"), (209, 433, "Justificativas do Abandono:"),
        (251, 487, "Topos Estratigráficos"), (337, 505, "Profundidades (m)"), (17, 516, "Unidades"),
        (254, 517, "Previstas"), (451, 517, "Constatadas"),
        (206, 529, "Medida"), (306, 529, "Em Cota"), (410, 529, "Medida"), (510, 529, "Em Cota"),
        (17, 546, "FM BARREIRAS"), (214, 546, "0,0"), (310, 546, "106,0"), (418, 546, "0,0"), (514, 546, "106,2"),
        (17, 564, "FM JANDAÍRA"), (208, 564, "150,0"), (310, 564, "-37,8"), (412, 564, "162,0"), (514, 564, "-49,8"),
        (17, 582, "FM AÇU"), (208, 582, "780,0"), (310, 582, "-667,8"), (412, 582, "801,5"), (514, 582, "-689,3"),
        (17, 599, "FM PENDÊNCIA"), (214, 599, "0,0"), (316, 599, "0,0"), (409, 599, "1.402,0"), (510, 599, "-1.289,8"),
        (17, 617, "FM SEM DADO"), (214, 617, "0,0"), (316, 617, "0,0"), (418, 617, "0,0"), (517, 617, "0,0"),
        (235, 662, "Indícios de Petróleo e/ou Gás"),
        (32, 679, "Intervalos (m)"), (105, 679, "Unidade"), (242, 679, "Ocorr."), (280, 679, "Tipo"),
        (320, 679, "Flúor"), (369, 679, "Cort."), (458, 679, "Detetor de Gás"),
        (28, 691, "Topo"), (70, 691, "Base"), (105, 691, "Estratigráfica"), (425, 691, "GT"), (482, 691, "GP"),
        (540, 691, "CR"),
        (24, 706, "812,0"), (66, 706, "815,0"), (105, 706, "FM AÇU"), (252, 706, "C"), (325, 706, "PL"),
        (372, 706, "MD"),
        (20, 724, "1.390,0"), (62, 724, "1.410,0"), (105, 724, "FM"), (252, 724, "C"), (325, 724, "EP"),
        (374, 724, "LT"),
        (105, 736, "AÇU/PENDÊNCIA"),
    ],
    [  # página 2: a tabela de indícios continua sem título
        (20, 112, "1.500,0"), (62, 112, "1.501,0"), (105, 112, "FM PENDÊNCIA"), (252, 112, "D"),
        (412, 112, "UGT-40,0"),
        (268, 150, "Testemunhos"),
        (21, 168, "Ordem"), (100, 168, "Intervalo (m)"), (213, 168, "Recup."), (263, 168, "Unidade"),
        (365, 168, "Litologia"),
        (31, 180, "nº"), (82, 180, "Topo"), (148, 180, "Base"), (220, 180, "(%)"), (263, 180, "Estratigráfica"),
        (31, 196, "1"), (82, 196, "1.395,0"), (148, 196, "1.404,0"), (222, 196, "88,0"), (263, 196, "FM AÇU"),
        (365, 196, "ARENITO MÉDIO"),
        (258, 240, "Amostras Laterais"),
        (22, 258, "Ordem nº"), (75, 258, "Profundidade (m)"), (155, 258, "Unidade Estratigráfica"),
        (293, 258, "Litologia"),
        (261, 300, "Análise de Perfis"),
        (47, 318, "Intervalos (m)"), (323, 318, "Perfis Corridos"),
        (38, 330, "Topo"), (88, 330, "Base"), (131, 330, "Unidade Estratigráfica"), (449, 330, "Litologia"),
        (31, 346, "1.392,0"), (82, 346, "1.406,5"), (131, 346, "FM AÇU"), (449, 346, "ARENITO"),
    ],
    [  # página 3
        (256, 107, "Teste de Formação"),
        (110, 124, "Intervalos (m)"), (218, 124, "Vazão"), (450, 124, "Depl."), (496, 124, "Pressão"),
        (548, 124, "Prof."),
        (35, 136, "Tipo"), (218, 136, "Estim."), (317, 136, "Fluido"), (409, 136, "API"), (443, 136, "(kgf/cm²)"),
        (495, 136, "Estática"), (542, 136, "Regist."),
        (97, 142, "Topo"), (157, 142, "Base"), (214, 147, "(m³/dia)"), (494, 147, "(kgf/cm²)"), (550, 147, "(m)"),
        (35, 163, "TFR"), (91, 163, "1.395,0"), (151, 163, "1.400,0"), (220, 163, "45,5"), (320, 163, "ÓLEO"),
        (412, 163, "31,2"), (460, 163, "0,0"), (502, 163, "141,7"), (541, 163, "1.398,0"),
        (38, 199, "PT"), (91, 199, "1.420,0"), (160, 199, "0,0"), (222, 199, "0,0"), (414, 199, "0,0"),
        (460, 199, "0,0"), (502, 199, "143,9"), (550, 199, "0,0"),
        (294, 233, "FILTRADO/ ÁGUA"),
        (31, 234, "TCA-1"), (91, 234, "1.460,5"), (160, 234, "0,0"), (222, 234, "0,0"), (414, 234, "0,0"),
        (460, 234, "0,0"), (502, 234, "148,0"), (550, 234, "0,0"),
        (306, 245, "FORMAÇÃO"),
        (267, 291, "Temperaturas"),
        (61, 309, "Temperatura"), (198, 309, "Profundidade (m)"), (319, 309, "Extrapolada ou Lida"),
        (458, 309, "Origem do Dado"),
        (43, 321, "Valor"), (105, 321, "Unidade"), (182, 321, "Medida"), (252, 321, "em Cota"),
        (43, 337, "80,0"), (119, 337, "F"), (190, 337, "0,0"), (256, 337, "106,2"), (356, 337, "L"), (488, 337, "P"),
        (40, 352, "158,0"), (119, 352, "F"), (181, 352, "1.850,0"), (252, 352, "-1.737,8"), (356, 352, "E"),
        (448, 352, "PERFILAGEM FINAL"),
        (250, 397, "Amostragem de Calha"),
        (82, 412, "Intervalo do Poço (m)"), (239, 412, "Padrão da Amostragem (m)"),
        (58, 424, "Topo"), (169, 424, "Base"),
        (60, 440, "9,0"), (166, 440, "600,0"), (239, 440, "9 em 9 metros"),
        (56, 456, "600,0"), (163, 456, "1.850,0"), (239, 456, "3 em 3 metros"),
        (262, 482, "OBSERVAÇÕES"),
        (22, 499, "Poço fictício para os testes do SIAPP."),
        (22, 510, "Segunda linha da observação."),
    ],
]

RFCP = [
    [
        (208, 107, "RELATÓRIO FINAL COMPLETAÇÃO"), (262, 138, "DADOS GERAIS"),
        (29, 158, "Poço:"), (209, 158, "Bloco:"), (425, 158, "Bacia:"),
        (210, 172, "POT-T-999"), (426, 172, "Potiguar"), (29, 173, "1-SIAPP-1-RN"),
        (29, 189, "Ínício da Completação:"), (209, 189, "Término da Completação:"), (425, 189, "Unidade Completação:"),
        (29, 200, "01/04/2010"), (209, 200, "10/04/2010"), (425, 200, "SPT-00"),
        (29, 219, "Mesa Rotativa (m):"), (209, 219, "Cota Altimétrica-Poço Terrestre (m):"),
        (425, 219, "Lâmina D'água (m):"),
        (29, 230, "112,20"), (209, 230, "106,20"), (425, 230, "0,00"),
        (237, 265, "Revestimentos de Produção"), (113, 282, "BUTTRESS (API)"), (23, 283, "Tipo de Conexão:"),
        (28, 299, "Diâmetro (pol)"), (124, 299, "Intervalo (m)"), (221, 299, "Peso (lb/pé)"), (316, 299, "Intervalo (m)"),
        (421, 299, "Grau"), (496, 299, "Intervalo (m)"),
        (115, 311, "Topo"), (163, 311, "Base"), (307, 311, "Topo"), (355, 311, "Base"), (487, 311, "Topo"),
        (535, 311, "Base"),
        (54, 326, "5 1/2"), (114, 326, "4,0"), (157, 326, "1.840,0"), (235, 326, "15,5"), (310, 326, "4,0"),
        (349, 326, "1.840,0"), (421, 326, "J-55"), (489, 326, "4,0"), (528, 326, "1.840,0"),
        (248, 403, "Intervalos de Produção"),
        (17, 420, "Unidade Litoestratigráfica"), (283, 420, "Intervalo (m)"), (448, 420, "Canhoneados"),
        (265, 432, "Topo"), (331, 432, "Base"), (383, 432, "Tipo de Canhão"), (468, 432, "Densidade de Disparos"),
        (18, 448, "FM. AÇU"), (259, 448, "1.396,0"), (325, 448, "1.401,0"), (404, 448, "HSD"), (509, 448, "6,0"),
    ],
    [
        (253, 104, "Coluna de Produção"),
        (17, 121, "Equipamento"), (355, 121, "O.D. (pol)"), (451, 121, "I.D. (pol)"), (527, 121, "Topo (m)"),
        (17, 142, "ÚNICA: TUBING: SIMPLES 2.7/8¿¿ EU"), (364, 142, "2 7/8"), (456, 142, "2,441"), (538, 142, "4,0"),
        (236, 411, "Dados de Teste de Formação"),
        (26, 429, "Tipo de"), (75, 429, "Abertura"), (131, 429, "Vazão"), (186, 429, "Pressão"), (250, 429, "RGO"),
        (30, 441, "Teste"), (83, 441, "(pol)"), (126, 441, "(m3/dia)"),
        (32, 495, "TFR"), (87, 495, "16"), (130, 495, "45,50"), (196, 495, "0,0"), (252, 495, "0,0"),
        (298, 495, "1,0"), (340, 495, "0,0"), (382, 495, "O"), (409, 495, "31,2"), (445, 495, "0,0"),
        (480, 495, "1.397,0"), (536, 495, "120,4"),
        (262, 521, "OBSERVAÇÕES"),
        (23, 538, "Sigla do Poço na base do E&P: 1-ABC-1-RN | 12345 * * *"),
    ],
]

PERFURACAO = [
    [
        (289, 103, "POÇO"),
        (23, 120, "Bloco:"), (239, 120, "Bacia:"), (431, 120, "Estado:"),
        (23, 131, "POT-T-999"), (239, 131, "Potiguar"), (431, 131, "Rio Grande do Norte"),
        (23, 150, "Operador:"), (239, 150, "Nº Contrato:"),
        (23, 161, "Operadora Fictícia"), (239, 161, "48610000000000000"),
        (23, 180, "Poço:"), (239, 180, "Cadastro do Poço:"), (431, 180, "Nome Poço para o Operador:"),
        (23, 191, "1-SIAPP-1-RN"), (239, 191, "99999999999"), (431, 191, "1ABC1RN"),
        (187, 239, "NOTIFICAÇÃO DE PERFURAÇÃO DE POÇO"),
        (24, 269, "Data de Remessa da Notificação:"), (282, 269, "Data Prevista para Início da Perfuração:"),
        (24, 281, "01/01/2010"), (282, 281, "15/01/2010"),
        (259, 371, "DADOS DO POÇO"),
        (24, 395, "Categoria do Poço:"), (264, 395, "Tipo do Poço:"), (24, 407, "Pioneiro"), (264, 407, "Vertical"),
        (262, 461, "COORDENADAS"),
        (239, 473, "Coordenadas de Base"), (414, 473, "Coordenadas do Alvo"),
        (24, 485, "Latitude:"), (204, 485, "-05:30:00,000"), (378, 485, "-05:30:01,800"),
        (24, 503, "Longitude:"), (204, 503, "-37:15:36,000"), (378, 503, "-37:15:36,000"),
        (217, 527, "PROFUNDIDADES FINAIS PREVISTAS"),
        (24, 545, "Medida (m):"), (264, 545, "Cota (m):"), (24, 557, "1.800,00"), (264, 557, "1.690,00"),
    ],
    [
        (193, 115, "RELATÓRIO DE PERFURAÇÃO DE POÇO"), (263, 150, "DADOS GERAIS"),
        (24, 174, "Ínício da Perfuração:"), (222, 174, "Término da Perfuração:"),
        (24, 186, "01/02/2010"), (222, 186, "02/03/2010"),
        (237, 256, "Fases e Demais Informações"),
        (85, 280, "Fases"), (224, 280, "Revestimentos"), (356, 280, "Topo do"), (458, 280, "Fluido de Perfuração"),
        (24, 292, "Nº"), (48, 292, "Diâmetro"), (100, 292, "Profundidade (m)"), (547, 292, "Peso"),
        (423, 303, "Tipo de Fluido"), (544, 303, "(lb/gal)"),
        (21, 326, "1,0"), (61, 326, "17 1/2"), (344, 326, "4,0"),
        (104, 327, "60,0"), (146, 327, "60,0"), (197, 327, "13 3/8"), (248, 327, "58,0"), (291, 327, "58,0"),
        (21, 342, "2,0"), (53, 342, "12 1/4"), (102, 342, "1.850,0"), (144, 342, "1.849,0"), (288, 342, "1.840,0"),
        (344, 342, "900,0"), (423, 342, "CATIÔNICO"), (548, 342, "9,60"),
        (207, 343, "5 1/2"), (246, 343, "1.840,0"),
        (84, 381, "Fases"), (243, 381, "Tempo de Perfuração (dias)"), (462, 381, "Teste de Absorção"),
        (23, 393, "Nº"), (210, 393, "Útil"), (375, 393, "TOTAL"),
        (20, 426, "1,0"), (103, 426, "60,0"), (210, 426, "2,0"), (275, 426, "0,5"), (332, 426, "0,0"),
        (382, 426, "2,5"), (451, 426, "0,0"), (528, 426, "0,0"),
        (60, 427, "17 1/2"),
        (254, 481, "Não Conformidades"),
        (17, 502, "Unidade"), (195, 502, "Intervalo (m)"), (323, 502, "Peso do Fluido"),
        (151, 526, "De"), (195, 526, "A"), (322, 526, "Antes"), (360, 526, "Depois"),
    ],
]


def gerar(caminho: str, paginas: list) -> str:
    doc = pymupdf.open()
    for n, linhas in enumerate(paginas, 1):
        p = doc.new_page(width=595, height=841)
        for x, y, t in CABECALHO + linhas + _rodape(n):
            # insert_text recebe a linha de base; o topo do texto fica ~7 pt acima
            p.insert_text((x, y + 7.5), t, fontsize=7, fontname="helv")
    doc.save(caminho)
    doc.close()
    return caminho
