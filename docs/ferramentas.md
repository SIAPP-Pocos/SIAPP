# Esquemas de ferramentas

Cada corrida de perfilagem tem, na pasta **Esquema de Ferramentas** do poço no REATE, um PDF
com a coluna de ferramentas descida no poço (o *tool string*). Na Potiguar são **5.220
esquemas em 2.935 poços** (levantamento de 16/10/2026), quase todos PDF de uma página,
mediana de 222 KB.

O SIAPP usa esses esquemas para responder **o que é cada arquivo de perfil do poço**:
perfilagem convencional, teste de formação a cabo, imagem, ressonância, cimentação… e com
quais ferramentas foi corrido. Código: `motor/ferramentas.py`; dicionário:
`recursos/ferramentas.json`.

## De onde vem cada informação

| Fonte | O que dá | Custo |
|---|---|---|
| **Nome do arquivo** | tipo da corrida (`raw`, `sft`, `rft`, `xpt`, `fmi`, `mril`, `cbl`…), nº da corrida (`raw1`, `run3`, `sft_1`), passada (`_P` principal, `_R` repetida), fase (`875` = 8 ¾") | nenhum: já está no levantamento |
| **Texto do PDF** (desenho vetorial) | ferramentas, fabricante, carimbo, diâmetro | baixar ~200 KB |
| **OCR da imagem** (a maioria: página escaneada) | o mesmo, com erros de leitura | baixar + ~2 s por esquema |

O nome do esquema e o do perfil seguem o mesmo padrão. É assim que um se liga ao outro:

| Esquema | Perfis |
|---|---|
| `8-pv-14-rn_raw1_toolstring.pdf` | `8-pv-14-rn_raw1-10028.dlis` (o número final é do upload no portal) |
| `1-auri-12-rn_AIT_tool.pdf` | `1-AURI-12-RN_AIT_P.DLIS` (principal) e `_AIT_R.DLIS` (repetida) |
| `1-auri-12-rn_RFT_tool.pdf` | `1-AURI-12-RN_RFT1.DLIS` … `RFT8.DLIS` (sem número no esquema: vale para todas) |
| `1star11rn_sft_run3.pdf` | `1star11rn_sft_gr_875_run3.dlis` |
| `3-brsa-477-rn_raw2_toolstring.pdf` | `raw2.dlis` — e **não** `raw2_fmi-gpit.dlis`, que tem esquema próprio |

Regras (`vincular`):

1. Mesmas palavras no nome (tirando o nome do poço, "toolstring", "esqfer"… e as palavras
   fracas `gr`, `sp`) **e** o mesmo nº de corrida e fase quando os dois têm. Cada perfil vai
   para o esquema de nome mais parecido.
2. O que sobrar, pelo **tipo**: `CONV_PRIN.DLIS` liga com `RAW_ToolString.pdf` se ele for o
   único esquema de perfilagem convencional do poço. Um esquema sem serviço no nome
   (`7et1585rn_esq.pdf`) entra aqui depois de lido, pelo tipo que o conteúdo deu.
3. Poço com um esquema só e perfil sem nada no nome (`7_ARG_640_RN_7_ARG_640_RN.lis`): liga.

Na Potiguar, só pelo nome, **84% dos arquivos de perfil** (4.959 de 5.896, nos poços que têm
os dois) ficam com o esquema da sua corrida. A pasta do perfil também ajuda:
"Teste de Formacao a Cabo" já diz que é testador.

## Leitura do conteúdo

- **Texto embutido** quando há (esquemas da Schlumberger gerados direto em PDF): sem OCR.
- **OCR** com o Tesseract embutido no PyMuPDF e o modelo **inglês "fast"** (4 MB, baixado uma
  vez para `recursos/tessdata/`). Em 13 esquemas reais ele leu mais códigos que o modelo
  "best" (15 MB) e 6× mais rápido.
- Imagem de baixa resolução (≤ 150 ppp; muitos esquemas têm 768 × 793 px) é **ampliada 2×**
  antes do OCR: quase dobrou os códigos lidos. Mais que isso, ou binarizar, piorou.
- Página **girada** (há esquemas deitados): se a leitura sai fraca, tenta 90° e 270° e fica
  com a melhor.
- Arquivo acima de 15 MB não é baixado: não é esquema (há "esquemas" de 86 MB que são o
  perfil de imagem em PDF).

### Códigos das ferramentas

Os códigos (HILTB-FTB, HGNSD-B, DSLT-H, XPT-BA, FTT-CA…) são comparados com o dicionário
tolerando as trocas típicas do OCR em letras pequenas: **O/D/Q/0**, **I/L/1**, **B/E/8**,
**S/5**, **C/G/6** (OTC-H = DTC-H, HILTE-F TE = HILTB-FTB). Com sufixo de peça, aceita uma
letra a mais no fim (HGNSD-B = HGNS) ou, em códigos de 5 letras ou mais, uma letra errada.
**Só entra o que está no dicionário** — nada é inventado. A grafia exata vem antes das trocas
(NCT-B, equipamento de superfície, não vira NGT-D).

Ficam de fora do reconhecimento: o **equipamento de superfície** dos esquemas da Schlumberger
(entre SURFACE e DOWNHOLE EQUIPMENT), as linhas do **carimbo** e os **nomes de poço** (o
`1-STAR-11-RN` não é a ferramenta STAR).

Cada ferramenta do dicionário diz o que mede (raios gama, nêutron, densidade,
microrresistividade, indução, laterolog, sônico, imagem, RMN, testador…). As de **apoio**
(cabeça, telemetria, acelerômetro) aparecem no esquema mas não definem o tipo da corrida.
Os rótulos do desenho ("Gamma-Ray", "Neutron", "Induction", "Hydrostat"…) também contam.

### Tipo da corrida

Pela prioridade: testador > RMN > imagem > amostrador > mergulho > cimentação > LWD;
depois **convencional** (duas ou mais entre indução, laterolog, densidade, nêutron, sônico,
microrresistividade), resistividade, sônico e **correlação** (só GR/CCL). Uma corrida de
testador também leva raios gama — mas é corrida de testador.

### Carimbo e medidas

Do carimbo da Petrobras ou da empresa de perfilagem: **data, poço, cadastro, operadora**
(se o poço do carimbo não é o da pasta, a ficha avisa). Das notas do desenho: **diâmetro
máximo** da coluna (polegadas; o da Tucker vem em mm e é convertido) e comprimento total.

## Conferência (16/10/2026)

13 esquemas reais da Potiguar (cópias fora do repositório): Schlumberger escaneados em
768 px, Schlumberger vetorial, Schlumberger girado, Tucker em CCITT 1728 px. Todos com o
tipo certo; Platform Express + AIT + sônico reconhecidos nas corridas `raw`, FMI + GPIT
nas de imagem, RFT/XPT/FTT nas de testador.

## Halliburton e sísmica de poço (0.63, conferência de 13/11/2026)

O dicionário (versão 2) ganhou 21 verbetes da Halliburton, tirados de 15 esquemas reais do acervo do projeto (Potiguar,
Alagoas, Recôncavo; cópias fora do repositório). Cada verbete novo tem o campo `fonte`, com o arquivo e a linha do
esquema em que o código aparece com o nome — nada saiu de catálogo ou de memória.

- Medição: NGRT (raios gama), SDL e SDLP (densidade), DSN (nêutron), FWS e WTIS (sônico), HRID (indução), MICP
  (microlog), SFT4 (testador), ASR (geofones, sísmica de poço).
- Apoio: DITS, D2TS, D4TS (telemetria), TMAX (temperatura), DKJT e KNUC (juntas), CENT, OBCEN, DCNT (centralizadores),
  FLEX, CBHD.
- Tipo novo de corrida: **sísmica de poço** (checkshot, VSP), pelo código ASR, pelo nome do arquivo (`asr`, `vsp`,
  `checkshot`) ou pelos rótulos `seismic`/`geophone`.
- `DITS-ASR` era lido como DLT (laterolog da Schlumberger) pela regra das trocas do OCR; com DITS no dicionário, a grafia
  exata vence.

Resultado nos 15 esquemas: os 12 da Halliburton saem com o tipo certo (antes, 4 saíam sem tipo ou com tipo errado: SFT
como "correlação", ASR como "resistividade"); os 3 da Schlumberger não mudaram.

Ainda faltam **Baker** e **Weatherford**: não há esquema deles baixado no projeto. Pelos nomes no levantamento,
candidatos: 7-PQO-1-RN, 7-PML-38-RN, 3-GALP-35-SE e 4-GALP-36-SE (Weatherford: MCG, MAI, MSS, MDN, CMI no nome);
1-IMET-17-AL e 8-CP-1502-SE (Baker: RCI, MREX).

## Limites (a interface deixa claro)

- O OCR **erra**. A ficha diz "confira no PDF antes de citar" e guarda o PDF para abrir.
- Fabricantes e ferramentas fora do dicionário não aparecem: o tipo sai só do nome. O
  dicionário é editável — correções são bem-vindas.
- Tempo: ~2 s por esquema. Ler a bacia inteira no levantamento leva horas; o normal é ler
  **poço a poço**, pelo botão da ficha.

## Onde fica

- Tabela `esquemas` do `projeto.sqlite` (migração 5): poço, nome, cópia local, método,
  tipo, dados lidos (JSON), erro, versão do leitor (`VERSAO_LEITOR`: leitor melhor relê da
  cópia local, sem baixar de novo).
- Cópia dos PDFs em `ambiente_teste/esquemas/<bacia>/<poço>/`.
- Na interface: ficha do poço (**Esquemas de ferramentas** e o rótulo de cada arquivo no
  acervo), aba Perfis (lista e cabeçalho do perfil aberto), etapa 4 opcional do levantamento.
