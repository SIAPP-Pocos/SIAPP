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

## Duas "gerações" de arquivo

| | Geração antiga | Geração nova |
|---|---|---|
| Padrão de nome | `7CS__0016__AL_7CS__0016__AL.tif` (maiúsculas, zeros à esquerda, nome duplicado) | `7-anb-9-al_brsa_raw.dlis` · `1-AURI-12-RN_AIT_P.DLIS` |
| Conteúdo da pasta de perfis | **`.tif`** — que pode ser imagem escaneada **ou DLIS com extensão trocada** (ver abaixo) | **`.dlis`** — curvas digitais |
| Serve para petrofísica? | Depende do conteúdo: imagem, não sem digitalização; DLIS, sim | Sim |

> [!IMPORTANT]
> **O `.tif` da geração antiga pode ser um DLIS.** Conferido em 16/10/2026:
> `5-PX-11-RN/Perfil Convencional/5PX__0011__RN_5PX__0011__RN.tif` (20 MB) começa com
> `V1.00RECORD … RECALL TO DLIS DATA TRANSFER` — rótulo de DLIS, não de TIFF. É uma
> recuperação digital da Petrobras (2020, conjunto `SPEP-RN-01V1`, ferramentas
> HRI/FWS/MSFL/SDL/DSN/GR) com 156–1.795 m e GR, SP, cáliper, resistividades, RHOB, NPHI, DT.
> O dlisio lê normalmente. O SIAPP decide o formato pelos primeiros bytes
> (`motor/formatos.py`), não pela extensão.

> [!WARNING]
> **Impacto direto no tamanho do acervo utilizável**
> Em 10 poços abertos, **5 tinham só `.tif`** na pasta de perfis, e 2 não tinham perfil nenhum. O número de poços listados numa categoria **não é** o número de poços com dado digital. Quantificar isso por bacia é um resultado relevante para o artigo.
>
> **Revisão (16/10/2026):** "só `.tif`" não quer dizer "só imagem" — pelo menos um desses `.tif` é DLIS. O levantamento precisa baixar (ou ler o começo de) cada `.tif` e classificar pelo conteúdo antes de contar.
>
> O padrão de nome antigo é o mesmo dos arquivos `.lis` de Carmópolis (`7CP__0010__SE_7CP__0010__SE.lis`) — a geração antiga pode ter LIS em alguns casos, não só TIF. A verificar.

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
- [ ] Diferença entre **DLIS / LIS** (dado digital) e **TIF / PDF** (imagem)
- [ ] Passada principal × repetida — quando usar cada uma
- [ ] Teste de formação a cabo — o que contém e para que serve
- [ ] Recomendações por finalidade:
  - petrofísica / avaliação de formação → passada principal
  - controle de qualidade da curva → principal + repetida
  - pressão de formação / gradiente de fluido → RFT
  - contexto geológico / descrição → perfil composto, pasta do poço

## Próximos levantamentos

- [ ] Confirmar as hipóteses de sufixo abrindo os DLIS
- [ ] Levantamento sistemático: amostrar poços de cada categoria em várias bacias e medir a fração com DLIS/LIS × só TIF × sem perfil
