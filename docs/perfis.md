# Perfis de poço (DLIS, LIS, LAS)

## Leitura

| Formato | Leitor | Observação |
|---|---|---|
| DLIS | [dlisio](https://github.com/equinor/dlisio) (LGPL-3.0) | vários arquivos lógicos e quadros por arquivo |
| LIS | dlisio | blocos com taxas de amostragem diferentes usam a menor |
| LAS | [lasio](https://github.com/kinverarity1/lasio) (MIT) | um quadro |

Cada **quadro** (frame) tem seu próprio passo de amostragem e continua separado: no
`1-AURI-12-RN_AIT_P.DLIS`, o quadro 60B tem passo de 6 polegadas e o 10B, de 1 polegada.
As curvas só são reamostradas numa grade comum na **exportação**.

## Profundidade em metros

`motor/perfis.py:fator_metros()` entende `m`, `ft`/`F`, `in`, `cm`, `mm` e múltiplos
como `0.1 in` (ou `.1IN`, como aparece em LIS). Índice em unidade de tempo ou
desconhecida é recusado com mensagem clara. Valores `-999.25`, `-9999`, `-999` viram
falha (NaN), nunca zero.

> **Armadilha:** os DLIS da Schlumberger gravam a profundidade em **décimos de
> polegada**. 848520 nesse índice são 2.155,2 m. Ler esse número como metro ou pé
> produz um poço de 848 km.

## Famílias de curvas

`recursos/mnemonicos.json` (editável) agrupa os mnemônicos que medem a mesma grandeza:

| Família | Exemplos | Escala padrão |
|---|---|---|
| GR | GR, ECGR, HGR, SGR | 0–150 gAPI |
| SP | SP, SPC | automática |
| CALI / BS | HCAL, CALI, C1 / BS | 6–16 pol. |
| RES_PROF / RES_MED / RES_RASA | AT90, AHT90, ILD, LLD / AT30, ILM / RXOZ, MSFL, AT10 | 0,2–2.000 ohm·m (log) |
| RHOB | RHOB, RHOZ | 1,95–2,95 g/cm³ |
| NPHI | NPHI, TNPH, NPOR | 0,45 a −0,15 (invertida) |
| PE | PEFZ, PEF | 0–10 |
| DT / DTS | DT, DTCO / DTSM | 140–40 / 240–40 µs/pé |

A **visão padrão** escolhe uma curva por família, pela ordem de `preferencia` (a curva
medida antes da calculada: `AT90` antes de `RT`) e, no empate, a com mais dados.

## Na tela (0.33)

- **Sugerir para** um objetivo: marca a melhor curva de cada família do objetivo que o arquivo
  tem (mesma escolha da visão padrão), diz o porquê e o que falta (`motor/perfis.py:OBJETIVOS`):

| Objetivo | Famílias, em ordem |
|---|---|
| Litologia e correlação | GR, SP, PE, RHOB, NPHI, CALI |
| Porosidade | RHOB, NPHI, DT, PE, DRHO, CALI |
| Saturação de água (Sw) | RES_PROF, RES_MED, RES_RASA, GR, RHOB, NPHI |
| Avaliação de formação | GR, RES_PROF, RHOB, NPHI, DT, CALI, BS, DRHO |
| Qualidade do poço | CALI, BS, DRHO, GR |
| Geomecânica | DT, DTS, RHOB, CALI |

- **Buscar curva** por mnemônico, descrição, unidade ou nome da família ("densidade" acha RHOB).
- **Cabeçalhos**: o nome da curva quebra a linha em vez de ser cortado, a escala fica embaixo, e
  todos os cabeçalhos têm a mesma altura — as trilhas começam na mesma linha e a profundidade
  fica alinhada entre elas.
- **Arrastar** na vertical mostra a faixa sendo marcada, em todas as trilhas, com topo, base e
  espessura.
- **Topos do AGP** (linhas verdes tracejadas): passar o mouse no eixo mostra o nome, a fonte e
  a qualidade. "Fonte" e "qualidade" são do próprio AGP (ver a nota "O que são fonte e
  qualidade" na tela): a qualidade é a nota do intérprete da ANP — bom, regular,
  questionável, inferido, não revisto.

## Cache

Na primeira leitura, cada quadro vai para `ambiente_teste/pocos/<poço>/<arquivo>__<quadro>.npz`
e o inventário para `<arquivo>.inventario.json`. As próximas aberturas e o gráfico usam o
cache. Apagar a pasta `pocos/` só obriga a ler os arquivos de novo.

## Exportação

LAS 2.0 ou CSV (`;` e vírgula decimal, para abrir no Excel em português), profundidade em
metros, grade comum com o passo escolhido. A interpolação é linear, mas **falhas maiores
que 2,5 passos da curva original continuam como nulo**: o SIAPP não inventa dado onde a
ferramenta não mediu. O cabeçalho do LAS leva poço, campo, empresa e o cadastro ANP (UWI).

## Conferido com arquivo real

`1-AURI-12-RN_AIT_P.DLIS` (Bacia Potiguar, 192 MB, perfilagem Schlumberger de 2005):
9 quadros, 354 curvas, 23,5 a 2.155,2 m, ferramentas HAIT, HILTD, DSLT-H e DTCH,
cadastro ANP 72100021414. Traz GR, SP, cáliper, resistividades de indução, densidade,
neutrão, fotoelétrico e sônico — confirma que `_P` é a **passada principal**.
Para repetir a conferência: `SIAPP_DLIS_REAL=<caminho> pytest -k real`.
