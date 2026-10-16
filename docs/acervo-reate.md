# Estrutura do acervo REATE

_O que o acervo realmente contém, observado com o SIAPP em poços reais. Separa o que foi **observado** do que ainda é **hipótese**._

> [!NOTE]
> **Para que serve esta nota**
> Registro do que o acervo do REATE **realmente contém**, observado com o SIAPP v0.4 explorando poços reais. É a base para:
> - a explicação de cada tipo de arquivo na **tela inicial** do SIAPP (planejada);
> - qualquer regra futura de seleção de arquivos (ex.: download em lote).
>
> Separa o que foi **observado** do que ainda é **hipótese**. Hipótese só vira fato depois de abrir o arquivo e conferir.
>
> Contexto: *SIAPP — README* · *SIAPP — Decisões e Armadilhas*

---

## Decisão: a escolha do arquivo é do usuário

> [!IMPORTANT]
> **Revisão de decisão (15/10/2026)**
> O SIAPP anterior escolhia automaticamente **1 arquivo por poço** (o maior DLIS da pasta de perfil convencional). Isso foi **abandonado**.
>
> **Motivo:** um mesmo poço tem arquivos de natureza diferente — passada principal, passada repetida, testes de formação. Cada um serve a uma finalidade (petrofísica, controle de qualidade, pressão de formação). Qualquer regra fixa escolhe errado para algum usuário — e a regra "maior arquivo" já escolhia errado no 7-ANB-9-AL (pegava o `sft`, provável testador de formação, em vez do `raw`).
>
> **Como ficou:** nenhum arquivo vem pré-marcado. A tela inicial vai explicar cada tipo e dar recomendações por finalidade.

---

## Estrutura de pastas

```
POCO/
└── Categoria-N/
    ├── Categoria-N_parte1/        ← categorias grandes são divididas em "partes"
    │   └── <poço>/
    │       ├── <pasta de perfis>/
    │       ├── <pasta de documentos>/
    │       └── ...
    └── Categoria-N_parte2/ ...
```

| Observação | Exemplo |
|---|---|
| Categorias grandes vêm em subpastas `parte` | Potiguar Cat-7: **7.198 poços em 36 partes**; Alagoas Cat-7: 510 em 5 |
| Um mesmo poço pode aparecer em duas partes | Potiguar Cat-7: **59 nomes repetidos** entre partes |

### Nomes de pasta encontrados

O nome **não é padronizado** — muda entre poços, até na mesma bacia.

| Conteúdo | Variantes vistas |
|---|---|
| Perfis | `Perfis_digitais` · `Perfil Convencional` |
| Teste de formação | `Teste de Formacao a Cabo` |
| Perfil composto | `Perfil Composto` |
| Esquema de ferramenta | `Esquema_de_ferramentas` · `Esquema de Ferramentas` |
| Documentação do poço | `Pasta_poco` · `Pasta de Poco` |
| Outros | `Dados_direcionais` · `Geoquimica_de_fluido` |

---

## Duas "gerações" de arquivo — e o que `.tif` quer dizer

| | Geração antiga | Geração nova |
|---|---|---|
| Padrão de nome | `7CS__0016__AL_7CS__0016__AL.tif` (maiúsculas, zeros à esquerda, nome duplicado) | `7-anb-9-al_brsa_raw.dlis` · `1-AURI-12-RN_AIT_P.DLIS` |
| Conteúdo da pasta de perfis | `.tif` e `.lis` — **LIS** (curvas digitais) dentro de um envelope de fita | `.dlis` — curvas digitais |
| Serve para petrofísica? | **Sim** | Sim |

> [!IMPORTANT]
> **`.tif` no REATE não é imagem.** Na perfilagem, TIF é o **Tape Image Format**: a cópia
> de uma fita magnética, com um cabeçalho de 12 bytes antes de cada bloco (tipo, posição do
> bloco anterior, posição do próximo). Dentro vem um **LIS** — o formato de curvas digitais
> anterior ao DLIS. Conferido em 16/10/2026 lendo o começo dos arquivos no portal:
>
> | Arquivo | Começo | Conteúdo |
> |---|---|---|
> | `7CS__0016__AL_7CS__0016__AL.tif` (pasta `Perfis_digitais`) | `00 00 00 00 00 00 00 00 90 00 00 00 00 84 00 00 84 00 RECALL…` | LIS em envelope TIF |
> | `1FL__0001__RN_1FL__0001__RN.tif` | idem | LIS em envelope TIF |
> | `1FJ__0001__RN_1FJ__0001__RN.lis` | idem | o `.lis` também vem no envelope |
> | `5PX__0011__RN_5PX__0011__RN.tif` (20 MB) | `   1V1.00RECORD… RECALL TO DLIS DATA TRANSFER` | **DLIS** sem envelope (recuperação Petrobras, 2020) |
>
> `RECALL` é o serviço de recuperação de dados da Petrobras que gerou esses arquivos a partir
> das fitas originais. O `dlisio` lê o LIS com ou sem o envelope (a própria documentação
> cita `.TIF` como extensão comum de LIS). O SIAPP decide o formato pelos primeiros bytes
> (`motor/formatos.py`), nunca pela extensão.

> [!WARNING]
> **Correção de uma conclusão anterior.** Em 10 poços abertos à mão, 5 tinham "só `.tif`" na
> pasta de perfis, e isso foi lido como "só imagem escaneada, não serve para petrofísica sem
> digitalização". **Estava errado**: o exemplo citado (`7CS__0016__AL`) é LIS. Numa amostra de
> 27 poços (Potiguar e Alagoas, 16/10/2026), **nenhum** arquivo de perfil era imagem — todos
> DLIS ou LIS; só 1 poço não tinha pasta de perfis.
>
> A contagem por bacia (quantos poços têm perfil digital, quantos só imagem, quantos nada)
> passa a ser feita pelo **levantamento do acervo** do SIAPP (aba Mapa), que classifica cada
> arquivo pelo conteúdo — ver [levantamento.md](levantamento.md).

---

## Tipos de arquivo de perfil

### Observado

| Poço | Pasta | Arquivos |
|---|---|---|
| 7-ANB-9-AL | Perfis_digitais | `_brsa_raw.dlis` (1,8 MB) · `_brsa_sft.dlis` (7,2 MB) |
| 7-ANB-9-AL | Esquema_de_ferramentas | `_tsc_raw.pdf` · `_tsc_sft.pdf` |
| 7-PIR-174D-AL | Esquema_de_ferramentas | `_tsc_raw.pdf` · `_tsc_rft.pdf` |
| 7-GMR-83-RN | Perfil Convencional | `_raw.dlis` (383 KB) |
| 1-AURI-12-RN | Perfil Convencional | `_AIT_P.DLIS` (192 MB) · `_AIT_R.DLIS` (9,4 MB) |
| 1-AURI-12-RN | Teste de Formacao a Cabo | `_RFT1.DLIS` … `_RFT8.DLIS` (0,4–2,9 MB cada) |
| 1-AURI-12-RN | Esquema de Ferramentas | `_AIT_tool.pdf` · `_RFT_tool.pdf` |

### Hipóteses — a confirmar abrindo os arquivos

| Sufixo | Hipótese | Base da hipótese | Status |
|---|---|---|---|
| `_raw` | Corrida principal de perfilagem (GR, resistividade, porosidade…) | Único DLIS em `Perfil Convencional` no 7-GMR-83 | ⏳ abrir e listar curvas |
| `_sft`, `_rft` | Corrida de **testador de formação** (pressões pontuais), não perfil contínuo | RFT = *Repeat Formation Tester*; pasta `Teste de Formacao a Cabo` contém `RFT1…8` | ⏳ abrir e listar curvas |
| `_RFT1…N` | Uma tomada de pressão por arquivo | 8 arquivos pequenos numerados | ⏳ |
| `AIT` | Ferramenta de indução em arranjo (*Array Induction Imager Tool*, Schlumberger) — nome da ferramenta principal da corrida | O DLIS lista a ferramenta HAIT, junto de HILTD, DSLT-H e DTCH | ✅ conferido (16/10/2026) |
| `_P` / `_R` | Passada **principal** / passada **repetida** (seção de repetição para controle de qualidade) | `_AIT_P` do 1-AURI-12-RN: 354 curvas de 23,5 a 2.155,2 m (poço todo), com GR, resistividades, densidade, neutrão, PE e sônico | ✅ `_P` conferido · ⏳ `_R` |
| `tsc` / `toolstring` / `_tool` (PDF) | Esquema da coluna de ferramentas daquela corrida | Mesmo sufixo do DLIS correspondente | provável |

**Como confirmar:** baixar pelo SIAPP os dois DLIS do 7-ANB-9-AL, o `raw` do 7-GMR-83-RN e o par `AIT_P`/`AIT_R` mais um `RFT` do 1-AURI-12-RN, e listar curvas, unidades e intervalo de profundidade de cada um (`dlisio`).

---

## Rascunho — o que a tela inicial deve explicar

- [ ] O que é cada pasta (perfis, teste de formação, perfil composto, esquema de ferramenta, pasta do poço)
- [ ] Diferença entre **DLIS / LIS** (dado digital, inclusive `.tif` de fita) e **PDF / TIFF** (imagem)
- [ ] Passada principal × repetida — quando usar cada uma
- [ ] Teste de formação a cabo — o que contém e para que serve
- [ ] Recomendações por finalidade:
  - petrofísica / avaliação de formação → passada principal
  - controle de qualidade da curva → principal + repetida
  - pressão de formação / gradiente de fluido → RFT
  - contexto geológico / descrição → perfil composto, pasta do poço

## AGP (dados gerais do poço)

Pasta `AGP` ou `Arquivo_geral_de_poco`, um `<poço>_agp.txt` de largura fixa. Na Potiguar
(levantamento parcial de 16/10/2026): **1.310 poços com AGP** (54 MB) — 63% dos pioneiros
(Cat. 1), 8% dos de desenvolvimento (Cat. 7); 897 deles também têm perfil digital. Às vezes
a pasta de um poço guarda o AGP de outro (3-AP-10-RN → `3SG0010BA`). Formato, dicionário de
códigos e o que o SIAPP extrai: [`agp.md`](agp.md).

## Próximos levantamentos

- [ ] Confirmar as hipóteses de sufixo abrindo os DLIS
- [ ] Levantamento sistemático: amostrar poços de cada categoria em várias bacias e medir a fração com DLIS/LIS × só TIF × sem perfil
