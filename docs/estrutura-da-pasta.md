# Estrutura da pasta do SIAPP

Este documento é o mapa da pasta: o que é cada pasta, cada arquivo, cada extensão e cada nome, e o que querem dizer os
termos da interface e do código. Revisão guiada feita em 16/11/2026 (0.68), olhando a pasta do Ruan
(`PIBIC.26\SIAPP`) e o repositório.

## Os três lugares

| Onde | O que é | Vai para o GitHub? |
|---|---|---|
| `SIAPP\` (o clone) | o programa: código, interface, recursos, documentação e testes | sim (tudo, menos o que o `.gitignore` exclui) |
| `SIAPP\ambiente_teste\` | o **projeto principal**: tudo o que o SIAPP baixa e produz | não, nunca (arquivos do REATE não entram no git) |
| `SIAPP\projetos\<nome>\` | outros projetos (desde a 0.58), ao lado do `ambiente_teste`, cada um com a mesma estrutura | não |

Isso é o desenvolvimento. **Quem instala o SIAPP** (0.67; pastas com nome de usuário desde a 1.1) vê outra coisa:

```
%LOCALAPPDATA%\Programs\SIAPP\      o programa (o instalador cuida dele)
Documentos\SIAPP\                   a "pasta dos projetos", escolhida na instalação
  Projetos\
    Projeto principal\              o que aqui se chama ambiente_teste
    <outros projetos>\
  recursos\tessdata\                modelo de português do OCR
```

Não há `ambiente_teste` para quem instala: é nome de desenvolvimento. Quem veio da 1.0 tem as pastas renomeadas
sozinhas na primeira abertura da 1.1. Ver [`instalador.md`](instalador.md).

Uma regra resume a separação: **o programa pode ser apagado e baixado de novo; o projeto é o trabalho de quem usa.**

## A raiz do programa (`SIAPP\`)

| Nome | O que é | Pode apagar? |
|---|---|---|
| `SIAPP.lnk` | atalho que abre o SIAPP (criado na primeira abertura; o que você fixa na barra de tarefas) | sim, o SIAPP recria |
| `SIAPP.vbs` | lançador silencioso: abre sem janela de console, procura versão nova e chama o `SIAPP.pyw` | não |
| `SIAPP.pyw` | abre a janelinha de carregamento (`lancador/`) com o Python sem console (`pythonw`) | não |
| `siapp.py` | o programa de verdade: cria a janela (pywebview) e liga a interface ao motor. `--verificar` e `--verificar-janela` conferem o pacote | não |
| `iniciar.bat` | atalho antigo; hoje só chama o `SIAPP.vbs` | pode, se usar o `SIAPP.lnk` |
| `SIAPP - diagnóstico.bat` | abre com console, para ver erros quando algo não abre | não (é o socorro) |
| `requirements.txt` | bibliotecas que o SIAPP usa (dlisio, lasio, pymupdf…) | não |
| `requirements-dev.txt` | bibliotecas só para os testes (pytest, playwright) | não |
| `pyproject.toml` | configuração do projeto Python (nome, versão do Python, marcas dos testes) | não |
| `README.md` | apresentação do projeto (o que aparece na página do GitHub) | não |
| `CHANGELOG.md` | o que mudou em cada versão (Ajuda › Novidades lê daqui) | não |
| `CITATION.cff` | como citar o SIAPP (o Zenodo lê, quando o repositório for público) | não |
| `LICENSE` | texto da licença AGPL-3.0 | não |
| `CLAUDE.md` | contexto e regras do projeto para o Claude | não |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | arquivos padrão de projeto aberto: como contribuir, conduta, como avisar falha de segurança | não |
| `.gitignore`, `.gitattributes` | o que o git ignora (dados, `.venv`…) e como trata fim de linha | não |
| `.git\` | o histórico do git (cada versão) | **não** (sem ele não há atualização pelo atalho) |
| `.github\workflows\` | robôs do GitHub: `testes.yml` (testes a cada envio) e `instalador.yml` (monta o .exe) | não |
| `.venv\` | o Python do SIAPP com as bibliotecas (criado na primeira abertura) | sim: o lançador recria (demora alguns minutos) |
| `.pytest_cache\`, `__pycache__\` | sobras dos testes e do Python (cache) | sim, sempre |
| `_backup_git\` | um pacote (`.bundle`) do histórico na 0.6, guardado antes de ir para o GitHub (30/10) | sim, o GitHub já tem tudo |
| `_publicar\` | pacotes usados para publicar os repositórios em 30–31/10 (`siapp.bundle`, `siapp-dados.bundle`, `COMO-PUBLICAR.md`) | sim, já foi publicado |
| `ambiente_teste\` | o projeto principal (seção abaixo) | não |
| `projetos\` | outros projetos, se você criar (Início › Novo projeto) | não |

### As pastas do programa

| Pasta | O que tem |
|---|---|
| `motor\` | **toda a lógica**, em Python, sem nada de interface: ler AGP, perfis, OCR, montar seção, bloco 3D, viabilidade… (um arquivo por assunto; lista abaixo) |
| `ponte\` | a **ponte** entre a janela e o motor: cada função que a interface chama (`window.pywebview.api.<função>`) |
| `ui\` | a **janela**: `index.html` (as telas), `estilo.css` (cores, letras, tamanhos), `js\` (um arquivo por tela) e `vendor\` (Leaflet do mapa, three.js do 3D) |
| `lancador\` | a janelinha de carregamento e os passos da abertura (conferir arquivos, procurar versão nova, preparar o Python) |
| `instalador\` | receitas do instalador do Windows: `siapp.spec` (PyInstaller), `siapp.iss` (Inno Setup), `AVISOS-DE-TERCEIROS.txt` |
| `recursos\` | dados fixos que o programa usa (lista abaixo) |
| `docs\` | documentação: um arquivo por módulo, o guia de teste e o roteiro |
| `tests\` | 67 arquivos de teste, só com dados sintéticos (`*_util.py` fabricam os arquivos falsos) |

### `recursos\`

| Arquivo | O que é |
|---|---|
| `estratigrafia.json` | unidades estratigráficas (sigla → nome) e a cor de cada uma na seção |
| `ferramentas.json` | dicionário de ferramentas dos esquemas (código → o que mede, fabricante, fonte) |
| `litologias.json` | legenda de litologias da Petrobras (cor e desenho de 95 rochas), usada na seção (0.68) |
| `mnemonicos.json` | mnemônicos das curvas de perfil (GR, RHOB, NPHI…) e a família de cada um |
| `guia_interpolacao.json` | regras da sugestão de método de interpolação do bloco 3D |
| `vocabulario_base.json`, `palavras_pt.txt.gz` | palavras do português para corrigir o texto do OCR |
| `doacao.json` | dados da tela "Apoie o projeto": chave Pix, texto "Quem faz o SIAPP", LinkedIn do autor e botões de valor |
| `icone\` | o ícone do SIAPP em vários tamanhos (`siapp.ico` é o do Windows) |
| `tessdata\` | modelos de idioma do OCR (`por.traineddata`, `eng.traineddata`), baixados na primeira vez; não vão para o git |

### `motor\`, arquivo por arquivo

| Arquivo | Assunto |
|---|---|
| `reate.py` | cliente do portal REATE (listar pastas, baixar) |
| `downloads.py` | fila de downloads, retomável |
| `projeto.py`, `projetos.py`, `banco.py` | a pasta do projeto, a lista de projetos e o banco `projeto.sqlite` |
| `pocos.py` | identificador canônico do poço e o cadastro da ANP |
| `levantamento.py`, `tipos_dado.py` | o que cada poço tem no portal, sem baixar; procurar poços por tipo de dado |
| `formatos.py` | o formato real do arquivo pelo conteúdo, não pela extensão |
| `documentos.py`, `ocr_processo.py`, `layout.py`, `vocabulario.py`, `dicionario.py`, `texto.py` | texto de PDFs e imagens (OCR), índice de busca, correção de palavras |
| `perfis.py` | DLIS, LIS e LAS → curvas padronizadas |
| `ferramentas.py` | esquemas de ferramentas (tool strings) |
| `agp.py`, `rfp.py`, `pag.py` | leitores dos formulários da ANP: AGP, RFP/CDPE, PAG |
| `dados_poco.py`, `pressoes.py`, `pvt.py`, `geoquimica.py`, `petrofisica.py`, `testemunho.py`, `checkshot.py`, `direcionais.py`, `operador.py`, `fluidos.py` | outros dados do poço (bloco 9): pressões, PVT, geoquímica, testemunho, sísmica de poço, trajetória, perfis da operadora, API e densidade |
| `topos.py`, `fontes.py`, `zonas.py` | topos de formação de várias fontes, prioridade das fontes, zonas produtoras |
| `avaliacao.py`, `biblioteca.py` | avaliação de formação (argilosidade, porosidade, saturação, net pay) e biblioteca de interpretações |
| `secao.py`, `secao_classica.py` | seção estratigráfica (estilo moderno e clássico) |
| `bloco*.py`, `interpolacao.py`, `guia_interpolacao.py`, `utm.py` | Modelo 3D: superfícies, bloco fechado, mapas, volumetria, validação, exportação (ECLIPSE, glb) |
| `producao.py`, `camadas.py`, `viabilidade.py`, `economia.py`, `indices.py` | produção da ANP, camadas do mapa, viabilidade técnica e econômica, correção pela inflação |
| `comunidade.py`, `painel.py` | contribuições e base comunitária (repositório Comunidade) |
| `consolidado.py`, `arquivos_baixados.py` | tudo o que foi lido e tudo o que foi baixado, com a procedência |
| `preferencias.py`, `registro.py`, `doacao.py` | preferências, registro de erros (`siapp.log`), tela de doação |

## O projeto (`ambiente_teste\`)

| Nome | O que é | Pode apagar? |
|---|---|---|
| `projeto.sqlite` | o **banco do projeto**: poços, arquivos, curvas, topos, dados transcritos, correções, esquemas | não (é o trabalho; apagar = recomeçar) |
| `siapp.json` | configuração do projeto (nome, versão que criou) | não |
| `historico.jsonl` | histórico do projeto, uma ação por linha | não (é a memória do que foi feito) |
| `preferencias.json` | preferências de tela (cores, tamanho do texto, avisos já vistos) | sim, volta ao padrão |
| `siapp.log` | registro de erros: o que mandar quando algo falha | sim |
| `lancador.log`, `siapp-saida.log` | registro da abertura e saída do console | sim |
| `.abriu` | sinal que a janela deixa para o lançador saber que ela abriu (e fechar a janelinha) | sim |
| `LEIA-ME.txt` | explica a pasta | sim |
| `catalogo\<bacia>\` | o que existe no portal: categorias, listas de poços e a **árvore** de cada poço explorado | sim: o SIAPP lista de novo (demora) |
| `bruto\<bacia>\<poço>\<pasta do portal>\` | os **arquivos baixados, intocados**, com os mesmos nomes do portal | só se quiser baixar de novo |
| `bruto\registro_downloads.json` (+ `.mudancas.jsonl`) | procedência de cada arquivo baixado (endereço, tamanho, data, hash) | não |
| `texto\` | texto de cada documento (embutido ou OCR), por página, `resumo.json` e `indice.sqlite` (busca) | sim: refaz o OCR (demora horas) |
| `pocos\` | cópia rápida das curvas de cada perfil já lido | sim: relê dos DLIS/LIS |
| `agp\` | AGPs baixados para os topos e a litologia de calha | sim: baixa de novo |
| `cadastro\` | Tabela de Poços da ANP (dados abertos) | sim: baixa de novo |
| `direcionais\` | trajetórias lidas | sim |
| `execucoes\` | cada processamento salvo com os parâmetros: `avaliacao_<poço>_<data>`, `secao_<data>`, `bloco_<data>`, `viabilidade\` | sim, mas perde o histórico de resultados |
| `exportacoes\` | o que você exportou (LAS, CSV, PNG, PDF, ECLIPSE) | é seu |
| `fontes\anp\producao\` | produção por poço e por zona da ANP (`.csv.gz`) e os planos de desenvolvimento (PD) | sim: baixa de novo |
| `sig\` | camadas do mapa (ANP, EPE, IBGE), em GeoJSON e shapefile | sim: baixa de novo (a de rodovias tem ~140 MB) |

Sobras de diagnóstico no seu `ambiente_teste` (de 28/10, testes de acesso ao portal REATE):
`diagnostico_reate.py`, `diagnostico_reate_ip.py`, os `.txt` de resultado e os `rodar_diagnostico_*.bat`. Não fazem parte
do SIAPP; podem ir para outra pasta ou para a Lixeira.

## Fora do SIAPP, em `PIBIC.26\`

Encontrado na revisão; nada foi apagado:

| Nome | O que parece ser | Sugestão |
|---|---|---|
| `SIAPP - ANTIGO\` | a pasta anterior ao GitHub | guardar fora da área de trabalho ou apagar: o GitHub tem o histórico |
| `SIAPP.zip` (1,28 GB) | cópia compactada da pasta antiga, com dados | idem |
| `Código\`, `Dados\`, `Resultados\`, `Backup\`, `__pycache__\` | a fase anterior do PIBIC (scripts, dados e figuras do relatório) | manter enquanto o relatório for referência |
| `PIBIC H2\` | a frente irmã (PIBITI H₂) | manter |
| `Relatório Final - PIBIC.26 - RUAN.docx`, `newplot.png`, `secao_*.html/png` | relatório e figuras de outubro | manter junto do relatório |

## Extensões

| Extensão | O que é | Quem abre |
|---|---|---|
| `.dlis` | perfil digital no padrão DLIS (RP66 v1): várias curvas, vários quadros | SIAPP (dlisio) |
| `.lis` | perfil digital no padrão LIS, mais antigo | SIAPP (dlisio) |
| `.tif` / `.tiff` no REATE | **cuidado**: quase sempre é *Tape Image Format* (fita com LIS dentro), não imagem; o SIAPP olha o conteúdo | SIAPP |
| `.las` | perfil em texto (Log ASCII Standard) | SIAPP, Excel, qualquer editor |
| `.pdf` | documentos do poço (AGP, RFP, PAG, esquemas, perfil composto) | SIAPP, leitor de PDF |
| `.xls`, `.xlsx` | planilhas do portal (petrofísica, testemunho) | SIAPP, Excel |
| `.segy`, `.sgy` | sísmica de poço (checkshot, VSP) | SIAPP |
| `.sqlite` | banco de dados num arquivo só | SIAPP, DB Browser for SQLite |
| `.json` | dados em texto estruturado | qualquer editor |
| `.jsonl` | uma linha JSON por evento (histórico, `.mudancas.jsonl`) | qualquer editor |
| `.npz` | curvas em formato do NumPy (resultado da avaliação) | Python |
| `.svg` | figura vetorial (seção, bloco) | navegador, Inkscape |
| `.glb` | modelo 3D (glTF binário) | visualizadores 3D, Blender |
| `.DATA`, `.GRDECL` | deck de simulação no formato ECLIPSE | simuladores (ECLIPSE, OPM, tNavigator) |
| `.geojson`, `.shp` (+ `.dbf`, `.shx`, `.prj`, `.cpg`) | camadas geográficas; o shapefile é um conjunto de arquivos com o mesmo nome | SIAPP, QGIS |
| `.csv.gz` | tabela em texto, compactada | SIAPP, 7-Zip + Excel |
| `.bundle` | histórico do git num arquivo só | git |
| `.traineddata` | modelo de idioma do Tesseract (OCR) | SIAPP |
| `.lnk`, `.vbs`, `.pyw`, `.bat` | atalho, script do Windows, Python sem console, script de console | Windows |
| `.spec`, `.iss`, `.cff`, `.toml` | receita do PyInstaller, do Inno Setup, citação e configuração do Python | ferramentas de desenvolvimento |

## Nomes

**Poço** (`1-BRSA-1041D-AL`): o primeiro número é a categoria do poço na classificação da ANP (1 = pioneiro,
7 = desenvolvimento são as mais comuns no acervo); depois a sigla (campo, prospecto ou operador), o número, uma letra
quando há (D = direcional) e a UF. O REATE escreve o mesmo poço de vários jeitos (`7-ANB-9-AL`, `7ANB__0009__AL`,
`7-anb-9-al`); o SIAPP guarda um **identificador canônico** e trata todas as grafias como o mesmo poço.

**Arquivos do portal**: `<poço>_<operadora>_<corrida>.<ext>`, ex.: `7-anb-9-al_brsa_raw.dlis`.

| Pedaço | O que diz |
|---|---|
| `brsa` | Petrobras (BR S.A.) |
| `raw` | dado de campo, sem processamento (a corrida principal) |
| `sft`, `rft`, `rci`, `mft`, `rdt` | teste de formação a cabo (pressão e amostra de fluido) |
| `mril`, `cmr`, `mrex` | ressonância magnética |
| `cmi`, `xrmi`, `fmi`, `cast` | perfil de imagem |
| `rsct`, `hrsct`, `swc` | amostragem lateral (testemunho lateral) |
| `cbl`, `vdl` | cimentação |
| `asr`, `vsp` | sísmica de poço |
| `_P` | passada principal |
| `tools`, `toolstring`, `toolsketch`, `diagram`, `tsc` | esquema de ferramentas |
| `_PC` | perfil composto |

**Pastas de poço no portal**: `Perfis digitais`, `Esquema de Ferramentas`, `Perfil Composto`, `Dados Direcionais`,
`Pasta de poço` (documentos)… A grafia muda entre bacias (`Esquema_de_ferramentas`, `PERFIL_DIGITAL`); o SIAPP aceita
as variações. Ver [`acervo-reate.md`](acervo-reate.md).

**Execuções**: `<tipo>_<poço>_<AAAAMMDD-HHMMSS>.json` (ou sem o poço, para seção e bloco): o nome é a hora do
processamento.

## Glossário da interface e do código

| Termo | Quer dizer |
|---|---|
| **acervo** | tudo o que o portal REATE tem de uma bacia |
| **AGP** | "Dados Gerais de Poços" da ANP: cabeçalho, topos de formação e litologia de calha |
| **apoio** (ferramenta) | peça do esquema que não mede nada (cabeça do cabo, centralizador, telemetria) |
| **árvore** | a lista em níveis bacia › poço › pasta › arquivo (Catálogo e Documentos) |
| **bacia**, **categoria**, **parte** | os níveis do portal: a categoria é a do poço; categorias grandes são divididas em partes |
| **base comunitária** | o repositório Comunidade: valores transcritos por quem usa, cada um com a fonte |
| **bloco** (Modelo 3D) | as superfícies de topo interpoladas entre os poços; **bloco fechado** = o volume fatiado nas unidades |
| **bruto** | o arquivo como veio do portal, sem mudar nada |
| **calha** | amostras de rocha que a lama traz durante a perfuração; a litologia de calha é a descrição delas |
| **catálogo** | a lista do que existe no portal, guardada para não listar de novo |
| **corrida** | uma descida da coluna de ferramentas no poço (raw, sft…); **passada** = cada registro dentro da corrida |
| **curva** | uma medida ao longo da profundidade (GR, RHOB, NPHI…); **família** = o tipo de medida |
| **datum** | a superfície de referência da seção nivelada (ex.: topo da Formação Açu) |
| **esquema de ferramentas** | o desenho da coluna de ferramentas de uma corrida |
| **fato** / **dado transcrito** | um valor tirado de um documento, com poço, página e caixa na imagem |
| **fonte** e **prioridade** | de onde vem um topo ou uma zona (AGP, RFP, transcrito, calha…) e qual ganha quando duas trazem o mesmo dado |
| **intervalo-alvo** | o trecho de profundidade que a avaliação usa |
| **journal** (`.mudancas.jsonl`) | registro só de acréscimos, para não regravar um arquivo grande a cada ação (0.60) |
| **ladrilho** | o quadradinho da legenda de litologias repetido na coluna da seção (0.68) |
| **lançador** | a janelinha que abre o SIAPP sem console e procura versão nova |
| **levantamento** | ler 1 KB de cada arquivo do portal para saber o que cada poço tem, sem baixar |
| **marca** | a impressão digital do projeto: diz às abas se algo mudou e se precisam reler (0.61) |
| **motor**, **ponte**, **interface** | as três camadas do código: lógica (Python), ligação, janela (HTML/JS) |
| **net pay** / **zona produtora** | o trecho do reservatório que passa nos cortes de argilosidade, porosidade e saturação |
| **nivelado** | eixo vertical medido a partir do datum, em vez da cota |
| **OCR** | reconhecimento de texto em imagem (Tesseract, dentro do PyMuPDF) |
| **PAG** | Perfil de Acompanhamento Geológico: lama, gás e descrição de calha |
| **perfil composto** | a folha-resumo do poço (curvas, litologia, topos, legenda) |
| **procedência** | de onde veio cada número: arquivo, página, data |
| **projeto** | uma pasta com o seu banco e os seus arquivos; `ambiente_teste` é o principal |
| **receita** (Modelo 3D) | a sequência poços → interpolar → método → grade → Montar |
| **RFP** / **CDPE** | Relatório Final de Poço, nos formulários da ANP |
| **slot** | a posição de cor de uma unidade na seção, que vem de `estratigrafia.json` |
| **tool string** | nome em inglês do esquema de ferramentas |
