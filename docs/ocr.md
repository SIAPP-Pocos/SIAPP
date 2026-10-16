# Documentos, OCR e correção de texto

_Como o SIAPP trata cada tipo de arquivo, com os testes em documentos reais e os limites do reconhecimento de texto._

> [!NOTE]
> **Para que serve esta nota**
> Plano de **o que o SIAPP faz com cada tipo de arquivo** do acervo REATE: como mostrar, o que extrair e onde aquilo é usado. O inventário dos tipos está em *SIAPP — Estrutura do Acervo REATE*.
>
> Princípio que vale para todos: **nada extraído automaticamente perde o vínculo com a origem.** Todo número ou texto extraído aponta para o arquivo e a página/profundidade de onde veio, para ser conferido. Ver regra 2 de *SIAPP — Decisões e Armadilhas*.

---

## Visão geral

| Tipo | O que é | Ver | Extrair | Usado em |
|---|---|---|---|---|
| **DLIS / LIS** — passada principal (`_raw`, `_P`) | Perfil digital | Visualizador de perfis (trilhas) | Curvas → Parquet padronizado | Petrofísica, seção, modelo 3D |
| **DLIS** — passada repetida (`_R`) | Perfil digital, trecho curto | Sobreposto à principal | Curvas | Controle de qualidade da curva |
| **DLIS** — testador de formação (`RFT`, `sft`, `rft`) | Pressões pontuais | Gráfico pressão × profundidade | Tabela de pontos | Gradiente de fluido, contatos, pressão de poros |
| **TIF** em `Perfis_digitais` | Imagem escaneada do perfil em papel | Visualizador de imagem com zoom | Cabeçalho via OCR (escalas, ferramentas, data) | Contexto; curva só com digitalização |
| **PDF** — Pasta do poço | Documento escaneado (relatórios antigos) | Visualizador de PDF | **OCR → texto pesquisável** | Busca, topos de formação, eventos de perfuração |
| **PDF** — Perfil composto | Perfil final consolidado | Visualizador de PDF | Texto (direto ou OCR) | Topos, litologia descrita |
| **PDF** — Esquema de ferramentas | Coluna de ferramentas da corrida | Visualizador de PDF | **Nome das ferramentas** | Identificar automaticamente o tipo de cada DLIS |
| **PDF** — Dados direcionais | Tabela de trajetória | Visualizador de PDF | Tabela MD × inclinação × azimute (OCR de tabela) | Trajetória 3D real do poço (TVD) |
| **PDF** — Geoquímica de fluido | Laudos | Visualizador de PDF | OCR → texto pesquisável | Busca |

> [!TIP]
> **Duas conexões que valem ouro**
> - **Esquema de ferramentas → tipo do DLIS.** O PDF da coluna de ferramentas tem o mesmo sufixo do DLIS (`tsc_raw.pdf` ↔ `raw.dlis`) e lista as ferramentas (AIT, RFT…). Ler esse texto permite **rotular cada DLIS automaticamente** e confirmar as hipóteses de sufixo, sem depender do nome.
> - **Dados direcionais → modelo 3D.** O SIAPP anterior tratava todo poço como vertical. Com a trajetória, os poços direcionais (`D` no nome, ex.: 7-PIR-174D-AL) entram com a posição real em profundidade.

---

## OCR — reconhecimento de texto nos documentos escaneados

### Viabilidade — testado em 15/10/2026

| Pergunta | Resposta |
|---|---|
| Precisa instalar programa no computador do usuário? | **Não.** O PyMuPDF traz o motor do Tesseract embutido; só precisa do arquivo de idioma (`por.traineddata`, alguns MB), que pode ir dentro da `siapp.vf` |
| Funciona sem internet? | Sim, é 100% local |
| Velocidade | ~0,6 s por página no teste (página sintética); documentos reais escaneados devem levar mais |
| Dá a posição das palavras? | Sim — permite destacar o termo encontrado na imagem da página |
| Gera PDF pesquisável? | Sim — imagem original + camada de texto invisível (Ctrl+F funciona em qualquer leitor) |
| Licença | PyMuPDF é AGPL-3.0: compatível com distribuir o SIAPP com código aberto |

> [!WARNING]
> **Limites reais — declarar na tela e no artigo**
> - **Manuscrito:** o Tesseract praticamente não lê. Anotações à mão ficam de fora.
> - **Escaneamento ruim** (torto, manchado, baixa resolução, datilografia gasta): erros de caractere. Números são o ponto mais sensível — `8` ↔ `3`, `1` ↔ `l`, vírgula decimal perdida.
> - **Tabelas** saem como texto solto; reconstruir linhas e colunas exige trabalho extra.
> - O teste foi feito com página **sintética** e idioma inglês (o português não pôde ser baixado no ambiente de teste). Validar com uma pasta de poço real e `por` antes de prometer qualidade.

### Teste com documentos reais — 15/10/2026

| Documento | Natureza | Resultado |
|---|---|---|
| `3-BRSA-1151-RN_CDPE_1_Perfuracao.pdf` (geração nova, 2 pág.) | **Nasceu digital** (Crystal Reports) — texto embutido | Texto sai completo **sem OCR**. Porém fora de ordem: todos os rótulos primeiro, depois todos os valores → associar rótulo↔valor exige usar a **posição** das palavras na página |
| `7GMR_0013__RN_pasta_poco_pub.pdf` (geração antiga, 2002, 55 pág.) | **Só imagem escaneada** (~220 dpi), nenhum texto | Precisa OCR |

**Conteúdo da pasta antiga (7-GMR-13-RN):** formulários datilografados — descrição de amostras de calha (litologia a cada 9 m), dados de revestimento e cimentação, tampões, relatórios de completação, testes de formação com cartas de pressão, mapa de contorno estrutural — e muita anotação à mão.

**OCR na página 1 (descrição de amostras de calha):**

| Configuração | Título e palavras comuns | Linhas da tabela | Coluna de profundidade |
|---|---|---|---|
| OCR direto | legíveis | quebradas pelas linhas da grade | perdida no meio do ruído |
| Pré-tratamento (binarizar + apagar grade) + modo bloco | legíveis | **saem inteiras e em ordem** | **erra vários valores**: `09`→`5`, `27`→`37`, `72`→`79`, `81`→`gl`, `297`→`997` |

Outros erros típicos: `CRE`→`ORE`, `QTZ`→`QT2`/`QUZ`, nome do poço `7-GRM-13-RN`→`q@=GRMW13-RN`. Teste feito com idioma **inglês** (acentos perdidos: DESCRICAO); com `por` deve melhorar o texto, não os números.

> [!IMPORTANT]
> **Conclusão do teste**
> - **Busca e classificação de páginas: viável e útil.** Os títulos dos formulários e os termos-chave saem legíveis — dá para saber automaticamente que a página 1 é "Descrição de amostras de calha" e achar "cimento", "revestimento", "completação".
> - **Extração automática de números de tabela: NÃO confiável.** A profundidade — o campo mais importante — erra em várias linhas. Qualquer número vindo de OCR precisa de conferência humana.
> - **Leitura por IA com visão** (ex.: Claude via API) lê esse formulário corretamente, inclusive a tabela — testado lendo a imagem da página 1 nesta conversa. Custo: internet, chave de API, custo por página, e ainda pede conferência.

> [!TIP]
> **Valor científico inesperado**
> A **descrição de amostras de calha** é litologia observada a cada ~9 m. É o "gabarito" para validar a litologia que o SIAPP infere do GR (Vsh) — exatamente a validação que faltava no trabalho anterior.

> [!WARNING]
> **Metadado antigo ≠ nome atual**
> O formulário de 1983 do 7-GMR-13-RN (Campo de Guamaré, RN) diz **"Bacia: CEARÁ"**. Documentos antigos usam nomenclatura da época; nunca usar campo de documento antigo para sobrescrever o cadastro atual da ANP.

### Primeira execução real no SIAPP — 15/10/2026 (idioma português)

Processado no computador do Ruan com o SIAPP v0.5: CDPE (2 pág., texto embutido) + pasta do 7-GMR-13-RN (55 pág., OCR).

| Aspecto | Resultado |
|---|---|
| Download do idioma `por` | funcionou (8,2 MB, ~30 s) |
| Tempo de OCR | ~9,5 s por página (55 pág. em ~9 min) — ~2,4× mais lento que o modelo inglês do teste |
| Acentos | saem: RELATÓRIO GEOLÓGICO, TAMPÕES, COMPLETAÇÃO, CANHONEIO |
| Títulos de página | legíveis em ~40 das 55 páginas; ruído nas páginas de gráfico e manuscritas |
| **Profundidades da pág. 1** (18 valores conferidos na imagem) | **12 certas, 6 erradas** (`09`, `27`, `090`, `243`→`2435`, `252`→`212`, `288`→`268`) |
| Cabeçalho da pág. 1 | GUAMARE, CEARÁ, MARCELO certos; data `30.11.83`→`30.11.87`; poço `7-GRM-13-RN`→`T-GRMAA3-RN` |

**Busca no índice real:** descrição, calha, cimentação, completação, canhoneio, pressão (18 pág.), gradiente, revestimento, perfilagem, Guamaré, Jandaíra — todas encontram as páginas certas. **Falham** quando o OCR deforma a palavra: `Barreiras` (lido BARIGIRAS) e `amostra contaminada` (lido CONTLMINDAS) dão zero.

> [!WARNING]
> **O erro mais perigoso é o plausível**
> `288` → `268` e `30.11.83` → `30.11.87` são valores válidos e errados. Ninguém desconfia lendo só o texto. Confirma a regra: **número de OCR nunca entra em cálculo sem conferência na imagem.**

**Melhorias identificadas:**
1. **Busca tolerante a erro de OCR** — expandir cada termo para as palavras do índice a 1–2 letras de distância (`Barreiras` ↔ `BARIGIRAS`). Barato, alto impacto.
2. **Transcrição assistida (3d)** para as tabelas — o caminho para os números.
3. Esconder o "título provável" quando ele for ruído.

### Vocabulário, busca tolerante e correção pelo usuário — v0.6 (15/10/2026)

**Três camadas de texto por página**, nesta ordem de prioridade — o OCR original nunca é alterado:
1. Correções **do usuário** (clicou na palavra e corrigiu) — valem para todos os documentos
2. Correções **automáticas** pelo dicionário de domínio (`recursos/vocabulario_base.json` + palavras do usuário)
3. Texto **original** do OCR

O índice guarda o texto corrigido **e** o original: uma correção automática errada nunca impede de achar a página.

**Regras da correção automática** (auditadas nos 55 textos reais do 7-GMR-13-RN):

| Regra | Por quê |
|---|---|
| Só palavras feitas de letras, com 6+ letras | **número nunca é corrigido automaticamente** |
| 1 erro em palavras de 6–8 letras, 2 em 9+ | 2 erros em 8 letras trocava RELATIVA→ROTATIVA |
| Mesma inicial, sem empate entre candidatos | evita escolhas arbitrárias |
| **Não corrige flexão** (diferença só na terminação: -S, -IS, -ADO, -O/-A…) | a 1ª versão trocava AMOSTRAS→AMOSTRA, CANHONEADO→CANHONEIO, ESTÁTICO→ESTÁTICA |

Resultado da auditoria: **68 correções na 1ª versão → 33 na final, todas legítimas** (`cimonto`→cimento, `BARIGIRAS`→BARREIRAS, `CECULACÃO`→CIRCULAÇÃO, `Clmantação`→Cimentação…).

**Correção pelo usuário:** bloqueada para números e palavras de 1–2 letras — `87`→`83` trocaria todo "87" de todas as páginas. Números ficam para a transcrição assistida (página a página).

**Busca tolerante:** cada termo também procura palavras do índice com 1 letra de diferença (5–8 letras) ou 2 (9+). `amostras contaminadas`: busca exata 0 páginas → tolerante 1 (achou `contlmindas`).

### Como funcionaria no SIAPP

```
1. Detectar   O PDF já tem texto embutido?  → usa direto (instantâneo, sem erro de OCR)
                                  Não?      → é imagem: segue para OCR
2. Reconhecer OCR página por página, em segundo plano (mesma ideia da fila de downloads)
              Resultado guardado: texto + posição das palavras + confiança por página
3. Indexar    Índice de busca de texto completo (SQLite FTS5) com TODOS os documentos do projeto
4. Buscar     "cimentação", "perda de circulação", "topo Açu" → lista de poços/páginas,
              clique abre a página com o termo destacado na imagem original
```

Saídas na pasta de projeto:

```
ambiente_teste/
└── texto/<Bacia>/<poço>/<arquivo>.json   texto por página + posições + confiança + método (embutido|ocr)
└── texto/indice.sqlite                   busca em todos os documentos
```

### Extração de dados estruturados (fase seguinte)

Três níveis, do mais barato ao mais robusto — o resultado é sempre **candidato a conferir**, com link para a página:

1. **PDF nascido digital** (CDPE e similares): campos extraídos pela posição rótulo↔valor. Confiável.
2. **Transcrição assistida** de tabelas escaneadas: tela com a imagem da página ao lado do texto do OCR, editável; o usuário corrige e confirma. Local e gratuito; trabalho humano reduzido, não eliminado.
3. **IA com visão** (opcional, chave de API do usuário): preenche a transcrição automaticamente; o usuário só confere.

---

## Ordem sugerida de implementação

| Passo | Entrega | Por quê nessa ordem |
|---|---|---|
| 3b | **Abrir** qualquer arquivo baixado (PDF/TIF no visualizador do sistema) | Trivial; destrava o uso imediato |
| 3c | **OCR + busca** nos PDFs | Maior ganho de tempo manual; independente do resto |
| 4 | Mapa do catálogo (cadastro ANP) | Já previsto |
| 5 | **Leitura de DLIS/LIS** → Parquet + rótulo de tipo (principal/repetida/RFT) pelo conteúdo e pelo esquema de ferramentas | Base de toda a petrofísica |
| 6 | Visualizador de perfis + intervalo-alvo | Já previsto |
| — | Pressão × profundidade (RFT), trajetória direcional, digitalização de TIF | Depois do núcleo; digitalização de TIF é um projeto à parte |

## Pendências

- [x] Baixar 1 pasta de poço real e testar OCR (7-GMR-13-RN, 15/10) — ver "Teste com documentos reais"
- [x] PDFs `_pub` antigos têm texto embutido? **Não** — são só imagem. Os CDPE novos sim.
- [ ] Repetir o teste com o idioma `por` no computador do Ruan (o download do arquivo de idioma foi bloqueado no ambiente de teste)
- [ ] Confirmar que o SQLite do Python do Windows tem FTS5 habilitado
