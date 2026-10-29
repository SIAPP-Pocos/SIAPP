# Perfil de Acompanhamento Geológico (PAG)

*SIAPP 0.40 — bloco 9, item 4.* Código: `motor/pag.py` (leitor), famílias de curva novas em
`recursos/mnemonicos.json`.

Na pasta "Perfil de Acompanhamento Geologico" do REATE vêm, além do PDF (`<poço>_PAG_ANP.pdf`, só documento):

| Arquivo | O que é | O que o SIAPP tira |
|---|---|---|
| `<poço>_PAG_curvas.las` | dados registrados durante a perfuração, a cada metro: peso sobre broca, torque, rotação, taxa de penetração (ROP), peso, viscosidade, pH e salinidade da lama, gás total e cromatografia (C1–C5, CO₂, H₂S) | abre na aba **Perfis** com as famílias novas (ROP, gás total, C1…C5, peso e salinidade da lama); o leitor tira as **zonas de gás** e a **salinidade** |
| `<poço>_PAG_DAC.xls` | **descrição das amostras de calha** pelo geólogo de poço: a cada 9 ou 3 m, as rochas e a porcentagem de cada uma, cor, textura, composição, porosidade aparente, fluorescência e corte, observações e a **formação geológica** | litologia por amostra, **topos pela calha**, fluorescência e corte |

## Zonas de gás

Fundo do poço = mediana do gás total. Zona = trecho com gás acima de **3 × o fundo**, com **2 m ou mais**
(uma leitura baixa no meio não parte a zona). Com a cromatografia, cada zona ganha as razões de Haworth et
al. (1985), na média da zona:

- umidade Wh = (C2 + C3 + C4 + C5) / (C1 + … + C5) × 100;
- equilíbrio Bh = (C1 + C2) / (C3 + C4 + C5);
- caráter Ch = (C4 + C5) / C3.

Leitura usual: Wh < 0,5 gás muito seco; 0,5–17,5 gás; 17,5–40 óleo; > 40 óleo residual ou pesado; Bh > Wh
reforça gás, Bh < Wh reforça óleo. É **indício** para escolher intervalos — a confirmação vem do perfil e do teste.
O PAG do 1-BRSA-1304-BA não traz a cromatografia (só o gás total), e a ficha diz "sem cromatografia".

## Salinidade da lama

Cada leitura de salinidade (ppm) vem com a resistividade de uma **solução de NaCl** com essa salinidade a 75 °F
(Bateman e Konen, 1977; outra temperatura pela fórmula de Arps). É referência para o Rw: em **lama base óleo**
(caso do 1-BRSA-1304-BA, emulsão inversa de n-parafina), a salinidade é a da fase aquosa da emulsão e não há Rmf.

## Descrição de calha

As colunas são reconhecidas pelo título das duas linhas de cabeçalho (PROF., TIPO DE ROCHA, PERC. NA AMOSTRA,
TEXTURA › GRAN/ARRED/SEL, FLUORESCÊNCIA › TIPO/PERC./COR/TON, CORTE › VELOC/MD. DISSEM., FORMAÇÃO GEOLÓGICA…).
Uma amostra começa na linha com profundidade e continua nas linhas seguintes (uma rocha por linha); vale da sua
profundidade até a próxima amostra. Códigos de rocha da convenção Petrobras (ARN arenito, FLH folhelho, CLU
calcilutito…) viram o nome; um código desconhecido fica como está.

**Topo pela calha**: a primeira amostra de cada formação. O topo real está entre a última amostra da formação de
cima e essa (9 ou 3 m). No 1-BRSA-1304-BA, os topos pela calha ficam a até 6 m dos topos constatados do RFP — que
não traz o nome das unidades; por isso a ficha põe ao lado de cada topo do RFP o nome da formação da calha a até 10 m.

## Onde cada dado é usado

| Dado | Onde |
|---|---|
| Topos pela calha | ficha (tabela com o RFP ao lado); nome dos topos sem nome do RFP |
| Litologia por amostra | aba Perfis: trilha de litologia "Litol. (calha)" quando o poço não tem a do AGP |
| Zonas de gás | ficha; intervalos candidatos da avaliação ("Gás na lama", origem PAG) |
| Fluorescência e corte | ficha |
| Salinidade | ficha; nota de referência do Rw na avaliação |
| Curvas de perfuração, lama e gás | aba Perfis (famílias novas) |

Famílias com `unidades` em `mnemonicos.json` só valem se a unidade da curva for uma delas: **DENS em lb/gal** é o
peso da lama, não a densidade da rocha. Os inventários antigos são reclassificados ao abrir o arquivo.

As planilhas `.xls` precisam da biblioteca `xlrd` e as `.xlsx` da `openpyxl` (instaladas pelo `iniciar.bat`).
Se faltar uma delas, o arquivo não é marcado como lido e entra de novo na próxima abertura.
