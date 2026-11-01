# Histórico de versões

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versões seguem [Versionamento Semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x, a interface e os formatos de arquivo podem mudar.

## [Não lançado]

## [0.55.0] — 2026-11-01
Zonas produtoras (net pay) no bloco 3D.
### Adicionado
- **Bloco 3D › Unidades › "zonas produtoras (net pay)"**: em vez dos topos de formação do AGP, o bloco usa o **topo e a base de cada
  reservatório**, poço a poço. Cada reservatório gera uma superfície de **topo** e outra de **base**; a espessura (isópaca) sai da
  diferença. Os mapas (GeoTIFF e XYZ), o CSV, o bloco fechado, a validação cruzada, o ECLIPSE e o modelo 3D funcionam com elas.
- **Intervalos de várias fontes**: canhoneados (RFCP), testes de formação (RFP/TFR), análise de perfis do operador (RFP), amostra de
  fluido (PVT), zonas-reservatório do AGP, intervalos que você marcou e a **sua tabela**. A ordem das fontes é a prioridade, e dá para
  usar a de maior prioridade ou o **envelope** (do menor topo ao maior fim).
- **Mais de um reservatório**: os intervalos de todos os poços são agrupados pela profundidade (tolerância editável, 20 m) e numerados do
  mais raso ao mais fundo. Dá para **escolher quais reservatórios mostrar** (por exemplo, só o raso), renomeá-los e **mover, ignorar ou
  corrigir** cada intervalo.
- **Aviso de OCR**: cada intervalo diz se veio de página com texto digital ou lida por **OCR (conferir)**, com o documento e a página, e o
  resumo conta quantos dos intervalos usados vêm de OCR.
- **Sua tabela** (CSV ou Excel: poço, topo, base, reservatório opcional, lat/lon ou X/Y em UTM com zona): vira fonte, pode fornecer as
  coordenadas dos poços e é **comparada** com o que o SIAPP escolheu (diferença de topo e de base por poço).
- **CSV de zonas** (`<bloco>_zonas.csv`): um intervalo por linha (poço, reservatório, fonte, topo e base em profundidade medida e cota,
  espessura, lat/lon e UTM), no desenho da tabela que se faz à mão.
- `docs/zonas-produtoras.md`; testes (motor, saídas e interface).
### Limites
- O agrupamento é pela profundidade, não pela geologia: falhas podem dividir um reservatório. Aumente a tolerância ou mova os intervalos.
- "Zona produtora" aqui é o intervalo que os documentos indicam, não o net pay por corte de Vsh, φ e Sw (esse continua na avaliação).
- Os números de OCR erram: confira cada profundidade na imagem do documento.

## [0.54.0] — 2026-10-31
Dados › Arquivos baixados.
### Adicionado
- **Arquivos baixados**: tudo o que está em `ambiente_teste\bruto`, de qualquer formato (planilhas, SEG-Y, ZIP, textos… e não só
  PDF e perfis), em **árvore** (bacia › poço › pasta) e **lista**. Cada arquivo mostra formato, tamanho, data do download, **o que o
  SIAPP fez com ele** (lido, texto extraído, perfil inventariado, ainda não lido, sem leitor, com erro, incompleto) e **onde o
  dado aparece** (ficha do poço, Perfis, Documentos, Seção, Bloco 3D…). O AGP, os dados direcionais e os esquemas de
  ferramentas, lidos pelo levantamento, também aparecem como lidos.
- Busca por nome, poço ou pasta; filtros por tipo, "lido?" e bacia.
- **Abrir** (programa padrão do Windows; programas e scripts como `.exe`, `.bat`, `.vbs`, `.ps1`, `.lnk` **nunca** abrem pelo
  SIAPP), **Mostrar na pasta** (Explorer com o arquivo selecionado), **Ver na ficha** (ficha do poço no Mapa) e **Apagar**.
- **Apagar manda para a Lixeira do Windows** (dá para restaurar; se a Lixeira falhar, não apaga). Antes, a tela mostra o que sai do
  SIAPP (dados lidos do arquivo, perfil inventariado, texto extraído e a busca nele) e o que **fica** (suas transcrições e
  páginas corrigidas continuam no banco; só perdem o arquivo de origem). O registro de procedência dos downloads não pode ser apagado.
### Corrigido
- Na nova tela, a busca só reage ao digitar (não ao sair do campo): clicar num botão logo depois de digitar não perde mais o clique.

## [0.53.1] — 2026-10-31
### Corrigido
- **O atalho e a janela do SIAPP agora são o mesmo botão na barra de tarefas.** Antes, o `SIAPP.lnk` (que abre o `wscript` e
  o `SIAPP.vbs`) não tinha identidade (AppUserModelID), e as janelas tinham a `SIAPP.Pocos.SIAPP`: o Windows via dois programas.
  O atalho fixado ficava de um lado e a janela aberta, rotulada "Python" (o nome do `pythonw.exe`), do outro.
  Agora o atalho recebe a mesma identidade, e cada janela do SIAPP (principal, de aba e a janelinha de carregamento) recebe
  também o nome **SIAPP**, o ícone e o comando de reabertura pelo lançador silencioso. Fixar a janela aberta na barra cria um
  atalho que abre o SIAPP, não o `pythonw.exe`.
- O `SIAPP.lnk` da 0.47 (sem identidade) é refeito sozinho na próxima abertura.
### Para quem já fixou o SIAPP na barra
- O atalho **já fixado** é uma cópia que o Windows guardou: ele não ganha a correção. Desafixe (botão direito › Desafixar) e
  fixe de novo, a partir da janela aberta ou do `SIAPP.lnk` novo.

## [0.53.0] — 2026-10-31
Segunda leitura (OCR) das páginas ruins.
### Adicionado
- **Segunda passada do OCR**: nas páginas escaneadas em que a primeira leitura (300 dpi) tem menos de 60 % das palavras
  conhecidas pelo dicionário, o SIAPP lê de novo a 450 dpi com outro limiar de preto/branco (Otsu) e **fica com a leitura
  de mais palavras de verdade**, desde que ganhe pelo menos 3 pontos. As duas leituras ficam registradas na página
  (`ocr.passadas`, `ocr.escolhida`). Caixa "Segunda leitura das páginas ruins (mais lento)" em Documentos, ligada por padrão.
- Medido em 9 páginas escaneadas reais de uma pasta de poço: a segunda leitura melhorou 6 páginas (+7 a +15 pontos de
  legibilidade), piorou 2 (mantida a primeira) e empatou 1. Custo: uma página ruim leva cerca de 2× mais tempo.
### Alterado
- `VERSAO_EXTRACAO` passa a 2. Documentos já lidos **não são relidos sozinhos**: para aplicar a segunda leitura, processe-os
  de novo (Processar este documento).
### Observação
- Legibilidade é palavras conhecidas, não exatidão: números (profundidades, datas) continuam pouco confiáveis no OCR e
  seguem entrando no banco só por transcrição conferida na imagem.

## [0.52.0] — 2026-10-31
Viabilidade: diâmetro pela vazão, correção pela inflação e restrições ambientais.
### Adicionado
- **Diâmetro do duto pela vazão**: informando vazão (m³ padrão/dia), pressão e temperatura do duto e a velocidade máxima, o
  SIAPP calcula o diâmetro interno mínimo (continuidade, com a vazão levada da condição padrão à do duto pela densidade de
  Peng-Robinson) e, se quiser, sobe para o tamanho comercial (NPS) seguinte. Entra no custo e na memória de cálculo. A
  velocidade de 15 m/s é só um ponto de partida do SIAPP, declarado como tal; não considera queda de pressão nem parede.
- **Correção do custo pela inflação**: IPCA ou INCC-M, da data-base da referência de custo até o mês escolhido (padrão: o
  último da série). As séries vêm do Banco Central (SGS 433 e 192), são baixadas na hora e guardadas em
  `ambiente_teste/indices/`; sem internet, usa a cópia. O fator, o período e a data do download vão para a memória.
- **Restrições ambientais**: camada de **UCs federais** (ICMBio, via INDE) em Dados › Camadas geográficas e botão
  **Importar terras indígenas…** (shapefile em zip ou GeoJSON da FUNAI, porque o servidor da FUNAI não abriu com
  certificado válido). Na Viabilidade, **Restrições ambientais no traçado** lista as áreas atravessadas pela linha reta
  até cada infraestrutura, com o trecho dentro (amostrado de 0,1 em 0,1 km). É triagem, não traçado nem licenciamento.
- `docs/viabilidade.md`; testes com sessão falsa (sem rede) e uma conferência ao vivo da série do Banco Central.

## [0.51.0] — 2026-10-31
Download em lote por seção, campo e mapa.
### Adicionado
- **Procurar por tipo de dado, restrito a um grupo de poços**: pelo **campo** (caixa "Só os poços do campo", pelo
  cadastro da ANP), pelos **poços da Seção** (botão "Dados destes poços") ou pelos **poços destacados no Mapa** (mesmo
  botão). Os tipos mostram quantos poços *desse grupo* têm cada dado; dali se marca, vê no mapa, exporta CSV e **baixa
  só os arquivos do tipo** (nada vem marcado; confirmação com o total). A restrição aparece como uma etiqueta que se tira.
- Com isso o download em lote cobre seção, campo e mapa; o filtro por tipo evita baixar o poço inteiro.

## [0.50.0] — 2026-10-31
Testemunho × perfil.
### Adicionado
- **Avaliação de formação › Comparação com o testemunho**: a porosidade dos plugs (laboratório) ao lado da porosidade da
  avaliação, na mesma profundidade, com a diferença em pontos percentuais, erro médio, RMSE e correlação. Só aparece
  quando o poço tem plugs lidos (0.48). Diz o quanto diferem, não qual está certo.
- **Deslocamento do testemunho pelo gama**: com o gama do testemunho (COREGAMA), o SIAPP procura o deslocamento de
  profundidade (até ±5 m) que mais aproxima o gama do testemunho do gama do perfil (correlação de Pearson) e mostra a
  segunda comparação já com ele. Só dá o deslocamento como confiável com correlação ≥ 0,6, pico destacado e fora da
  borda da busca; senão avisa e não sugere aplicar.
- `motor/testemunho.py`; testes com dados sintéticos de deslocamento conhecido.

## [0.49.0] — 2026-10-31
Procurar poços por tipo de dado.
### Adicionado
- **Dados › Procurar por tipo de dado**: marque os tipos que procura (petrofísica básica e avançada, PVT, geoquímica,
  sísmica de poço, teste de formação, perfis, direcionais, AGP, PAG, esquemas, fotos de rocha…) e veja em quais poços
  há **todos** ou **pelo menos um** deles, com a quantidade e o tamanho dos arquivos de cada tipo. Responde pelo
  levantamento do acervo já feito: **não baixa nem pede nada ao portal**. Nada vem marcado.
- O tipo vem do nome da pasta, juntando as várias grafias que o REATE usa para a mesma pasta (inclusive a com erro
  `Petrofica_basica`).
- Com os poços que você marcar: **ver no mapa** (até 300), **baixar só os arquivos dos tipos procurados** (com total
  e confirmação, pela fila de downloads de sempre) e **exportar a busca em CSV** (um arquivo do portal por linha).
- `docs/tipos-de-dado.md`; testes de motor, de ponte e de interface.

## [0.48.1] — 2026-10-31
### Corrigido
- **Petrofísica básica: a pasta tem várias grafias no acervo.** O leitor da 0.48 só reconhecia `PETROFISICA_BASICA`
  (3 poços do acervo); o levantamento mostra 162 poços, a maioria em `PETROFISICABASICA`, e ainda `Petrofisica_basica`,
  `Petrofisicabasica` e `Petrofica_basica` (com erro de grafia). Agora todas são reconhecidas; a `PETROFISICAAVANCADA`
  (permeabilidade relativa, pressão capilar) continua fora, por ser outro tipo de dado.

## [0.48.0] — 2026-10-31
Petrofísica básica de testemunho (fecha o Bloco 9).
### Adicionado
- **Leitor de petrofísica básica** (`motor/petrofisica.py`), para a pasta `PETROFISICA_BASICA` do REATE:
  plugs (profundidade, porosidade, densidade, permeabilidade longitudinal, pressão, tipo, direção e número da
  amostra) e **gama do testemunho** (`*_COREGAMA.xls`). Lê `.xls` e `.xlsx`, acha as colunas pelo cabeçalho,
  entende números em texto com vírgula decimal ("206,39"; "1.234,5") e guarda colunas desconhecidas em
  `extra.colunas`, sem perder nada. Testado com as planilhas do 1-ALG-1-RN.
- **Ficha do poço**: blocos "Petrofísica de testemunho — plugs" (tabela, faixas de porosidade e permeabilidade) e
  "Gama do testemunho (COREGAMA)". Os mesmos plugs vindos em duas planilhas aparecem uma vez, com a outra em
  "também em".
- **Dados consolidados**: tema "Petrofísica de testemunho" com as duas fontes.
- `docs/petrofisica.md`; testes com planilhas sintéticas (`tests/petrofisica_util.py`).
### Observação
- A planilha não declara a unidade da **densidade**; o SIAPP a mostra como vem, sem unidade, e avisa na ficha.

## [0.47.0] — 2026-10-31
O SIAPP abre como um programa, sem a janela de prompt.
### Adicionado
- **Lançador silencioso** (`lancador/`, `SIAPP.pyw`, `SIAPP.vbs`): dois cliques no atalho abrem uma janelinha de
  carregamento com o ícone, o nome, a versão e uma barra de progresso, com os passos "Conferindo os arquivos",
  "Preparando os componentes" e "Abrindo o projeto". Ela some quando a janela principal aparece (o SIAPP avisa o
  lançador por um arquivo-sinal). Nenhum console aparece, nem na tela nem na barra de tarefas.
- A primeira abertura (sem `.venv`, ou com a `.venv` quebrada, por exemplo depois de renomear ou mover a pasta)
  passa pela janelinha: o ambiente é criado e as dependências instaladas escondidas; as dependências só são
  reinstaladas quando o `requirements.txt` muda.
- **Erros na própria janelinha**, em português simples, com **Copiar detalhes**; o detalhe vai para
  `ambiente_teste/lancador.log` (e o que o app imprimir, para `ambiente_teste/siapp-saida.log`).
- **`SIAPP - diagnóstico.bat`**: o antigo `iniciar.bat`, com console e cada passo, para investigar problemas.
- A janelinha e a janela principal usam o mesmo ícone e a mesma identidade na barra de tarefas
  (`SIAPP.Pocos.SIAPP`).
- Testes de unidade do lançador (`tests/test_lancador.py`), que rodam fora do Windows.
- `CLAUDE.md` com as regras do projeto e as fontes de contexto; `docs/roteiro.md` com o que falta.
### Alterado
- `iniciar.bat` não mostra mais o prompt: só chama o `SIAPP.vbs`.
- `SIAPP.lnk` abre o lançador silencioso e é **recriado** quando o destino ou a pasta não batem com a pasta atual.
- A pasta do app passa a se chamar **SIAPP** (era `siapp.vf`); as menções foram trocadas.

## [0.46.0] — 2026-10-30
O ícone do SIAPP.
### Adicionado
- **Ícone próprio**: um "S" formado pelas curvas de raios gama (verde) e resistividade (vermelho), com o amarelo do
  crossover entre elas, sobre papel de perfil com grade log e cortado por um marcador de topo de formação.
- `recursos/icone/siapp.ico` com 8 tamanhos (16 a 256 px), **cada faixa com o seu desenho**: a 16 e 20 px, sem
  grade, com borda e topo encaixados na grade de pixels e cores mais fortes; a 24–40 px, só as linhas principais
  da grade, cada uma numa coluna de pixel inteira. Fontes em SVG e um LEIA-ME na mesma pasta.
- No Windows, a janela principal e as janelas de aba mostram o ícone na barra de título, na barra de tarefas e no
  Alt+Tab (antes, o do `python.exe`). O SIAPP ganha identidade própria na barra de tarefas e não se agrupa mais com
  outros programas em Python.
- **Atalho com o ícone**: na primeira abertura no Windows, o SIAPP cria `SIAPP.lnk` na própria pasta (abre pelo
  `iniciar.bat`); dá para copiar para a Área de Trabalho ou fixar no Iniciar e na barra de tarefas.
- O ícone aparece também ao lado do nome SIAPP no topo da janela.

## [0.45.0] — 2026-10-29
Topos de várias fontes: ver as diferenças, saber de onde vem e escolher.
### Adicionado
- **Ficha › "Topos de formação — compare as fontes e escolha"**: por unidade, o topo do AGP, do transcrito, do RFP e
  da calha, a diferença entre eles (em vermelho acima de 5 m), o documento de cada valor e o topo usado; um seletor
  escolhe a fonte daquela unidade no poço ("padrão", uma fonte ou "não usar").
- **Ordem das fontes do projeto** (Dados › Dados consolidados): vale onde você não escolheu. Padrão: AGP →
  transcrito → RFP → calha.
- Migração 11: tabela `escolhas`. Toda escolha vai para o histórico do projeto.
### Mudado
- **Seção estratigráfica e bloco 3D usam o topo efetivo**, não só o do AGP: um poço sem AGP (como o 1-BRSA-1304-BA)
  entra na seção pelos topos do RFP nomeados pela calha, ou pelos transcritos. A coluna "fonte" diz de onde veio cada
  unidade. Onde há AGP e você não escolheu outra coisa, nada muda.
- O topo do RFP sem nome ganha o nome da formação da calha mais perto, um para um (antes, dois topos do RFP podiam
  receber o mesmo nome).

## [0.44.0] — 2026-10-29
O leitor final dos dados consolidados.
### Adicionado
- **Dados › Dados consolidados**: por tema (topos, intervalos de interesse, temperatura, pressão, fluidos, lama,
  litologia, curvas, interpretações, tempo × profundidade, trajetória, produção, outros nomes), cada fonte com
  quantos poços e registros tem no projeto, a tabela do banco onde fica e onde é usada; e os documentos lidos por
  leitor, com os que não foram lidos e os de outro poço.
- **Um poço**: os valores de cada fonte lado a lado (pelo nome em qualquer grafia), também pelo botão "Dados
  consolidados" da ficha.
- `docs/dados-consolidados.md`: o mesmo catálogo, e as lacunas que ele mostra (a seção e o bloco 3D só usam os topos
  do AGP; temperatura e lama são referência, não viram Rw sozinhas).

## [0.43.0] — 2026-10-29
Bloco 9, item 7: geoquímica e apelidos. Com ele, o bloco 9 está completo.
### Adicionado
- **Geoquímica**: a planilha da pasta GEOQUIMICADEFLUIDO (XML 2003 do Excel, xls ou xlsx) é lida pelo título das
  colunas — δ¹³C do metano, etano e propano por intervalo, com a leitura da origem do gás (termogênico, biogênico,
  misto; ordem normal ou invertida) — e, se houver, a geoquímica de rocha (COT, S1, S2, S3, Tmax, IH, IO, Ro).
  Um δ¹³C positivo por sinal duplo na fórmula (caso do 1-BRSA-1304-BA) é corrigido, com aviso.
- **Ficha**: seção de geoquímica; os avisos de cada documento aparecem na lista de documentos; "Também escrito como"
  diz de onde veio cada grafia do poço.
- A sigla da operadora na planilha de geoquímica vira apelido (os demais leitores já faziam).

## [0.42.0] — 2026-10-29
Bloco 9, item 6: sísmica de poço (checkshot).
### Adicionado
- **Checkshot do SEG-Y**: o cabeçalho de cada traço da sísmica de poço é lido (sem o sinal), pelas posições que o
  próprio cabeçalho textual declara. Sai a tabela tempo × profundidade: tempo vertical corrigido pelo afastamento da
  fonte e pela correção ao datum, TWT, velocidade média e intervalar. No 1-BRSA-1304-BA confere com o relatório da
  empresa.
- **Ficha**: tabela, gráficos TWT × profundidade e velocidade intervalar, e exportação da tabela em CSV para a
  sísmica de superfície.
- **Perfis**: a leitura do mouse mostra o TWT da profundidade.
- O registro de campo (tiro a tiro) aparece na lista de documentos; a sigla do poço na operadora vira apelido.

## [0.41.0] — 2026-10-29
Bloco 9, item 5: perfis já processados pela operadora.
### Adicionado
- **Famílias das curvas interpretadas** pela operadora: argilosidade (VSH, VCL…), porosidade efetiva e total (PHIE,
  PHIT), saturação de água (SW, SWE…) e permeabilidade (PERM, KINT…).
- **Pesquisa sem baixar**: o levantamento guarda a lista de curvas de cada arquivo, e as famílias são refeitas ao
  abrir o projeto quando o arquivo de mnemônicos muda. Em Dados › Levantamento, "Perfis já processados pela
  operadora" conta os poços e lista arquivos e curvas; no Mapa, o filtro "Com a curva" ganha "interpretação da
  operadora (Vsh, φ ou Sw)" e cada uma delas.
- **Avaliação × operadora**: com o perfil processado do poço aberto, cada avaliação mostra as médias de Vsh, φ e Sw do
  SIAPP e da operadora no intervalo e no net pay, com as diferenças grandes em destaque.

## [0.40.0] — 2026-10-29
Bloco 9, item 4: Perfil de Acompanhamento Geológico (PAG).
### Adicionado
- **Curvas do PAG** (`_PAG_curvas.las`): famílias novas na aba Perfis — taxa de penetração, gás total e
  cromatografia (C1…C5, CO₂, H₂S), peso, viscosidade e salinidade da lama, peso sobre broca, torque, rotação.
  O leitor tira as **zonas de gás** (acima de 3 × o fundo, com as razões de Haworth quando há cromatografia) e a
  **salinidade da lama**, com o Rw de uma solução de NaCl equivalente.
- **Descrição das amostras de calha** (`_PAG_DAC.xls`): rochas e porcentagens de cada amostra, fluorescência e corte,
  e a formação anotada pelo geólogo de poço → **topos pela calha**.
- **Ficha**: topos pela calha (com o topo constatado do RFP ao lado), gás na lama, fluorescência na calha,
  salinidade e o resumo da litologia. Os topos sem nome do RFP ganham o nome da formação da calha a até 10 m
  (no 1-BRSA-1304-BA: Pojuca, Marfim, Maracangalha, Candeias, Água Grande, Itaparica, Sergi, Aliança, Embasamento).
- **Perfis**: sem a litologia do AGP, a da calha faz a trilha "Litol. (calha)", com legenda.
- **Avaliação**: as zonas de gás entram como intervalos candidatos; a salinidade da lama entra na nota do Rw.
### Mudado
- Uma família de curva pode exigir unidades: DENS em lb/gal é o peso da lama, não a densidade da rocha. Os arquivos
  já inventariados são reclassificados ao abrir.
### Corrigido
- As planilhas do PVT (0.39) precisavam das bibliotecas `xlrd` e `openpyxl`, que não estavam na lista de
  dependências: num computador sem elas, a análise PVT não aparecia. Elas entraram no `requirements.txt` (o
  `iniciar.bat` instala ao abrir) e, se faltarem, o arquivo fica para ser lido na próxima abertura.

## [0.39.0] — 2026-10-29
Bloco 9, item 3: PVT.
### Adicionado
- **Análise PVT do laboratório**: as planilhas de liberação diferencial e de liberação flash da pasta "Dados De
  Rochas e Fluidos/PVT" são lidas, e a pressão de saturação é tomada como a do maior Bo. Acima dela, o SIAPP
  calcula a compressibilidade do óleo. As colunas são reconhecidas pelo título.
- **Ficha › Análise PVT**: amostra, saturação, dados do tanque, gráficos de Bo, Rs e viscosidade × pressão e a
  tabela dos estágios. **Composição** do fluido, de N₂ a C20+.
- **Viabilidade**: com uma análise PVT num poço do campo, o grau API e a densidade do gás vêm dela, antes do dado
  transcrito e da leitura automática. Bo, Rs e Bg vêm da tabela, interpolados na pressão do reservatório, no
  lugar de Standing e Sutton + Papay; a memória de cálculo diz de que poço veio cada valor. Bg sai da tabela só
  abaixo da saturação. O valor informado pelo usuário continua valendo sobre o medido.
- A sigla do poço na operadora, que vem na planilha, vira apelido.
### Mudado
- A seção da ficha passou a se chamar "Formulários da ANP, testes e análises de laboratório".

## [0.38.0] — 2026-10-29
Bloco 9, item 2: pressões.
### Adicionado
- **Teste de formação a cabo** (SFT, RFT, MDT…): o DLIS indexado por tempo é lido estação por estação. Para cada
  uma, o SIAPP tira a hidrostática da lama, a pressão da formação no último patamar, o patamar anterior, os
  pré-testes e a inclinação do fim do patamar, e diz se a pressão estabilizou. No 1-BRSA-1304-BA, a diferença para
  o RFP ficou em até 0,1 kgf/cm² nas 8 estações.
- **Teste de formação (TFR)**: o ZIP é lido por dentro, inclusive ZIPs dentro do ZIP. Do relatório de
  interpretação saem a estática, a pressão de fluxo, a vazão, o °API, a temperatura, o IP, a permeabilidade
  efetiva, o skin, o raio de investigação, o modelo, a conclusão, os fluxos e os parâmetros adotados. Dos
  manômetros (.TPR) saem a série e os extremos de cada um, com o registrador usado na interpretação marcado.
- **Ficha › Pressões × profundidade**:
  - gráfico com os pontos do teste a cabo, dos formulários e do TFR, e a lama;
  - tabela em que cada ponto vai para o grupo A ou B;
  - **gradiente** de cada grupo, com a densidade e o fluido compatível;
  - **contato** entre os dois grupos;
  - curva pressão × tempo de cada estação e de cada manômetro.

  No 1-BRSA-1304-BA, os grupos dão óleo (0,70 g/cm³) e água (1,05 g/cm³), com contato a 1.694 m.
- **Ficha › relatório do TFR**: tabela dos resultados e dos fluxos.
- Formulários CDPE novos: **Relatório de Descoberta**, **Relatório de Perfilagens Realizadas** e **Relatório de
  Reentrada**. Um CDPE de título desconhecido é guardado com o título e o texto, sem erro.
- O intervalo do TFR e as temperaturas do TFR e da sonda a cabo entram na avaliação de formação.
- A sigla do poço na operadora vira apelido. Ela vem do relatório do TFR, dos manômetros e do título do DLIS.
### Mudado
- O mesmo dado em dois formulários aparece uma vez, o do formulário de maior prioridade, com a anotação "também
  em" para o outro.
- Os leitores reconhecem o arquivo pelo caminho (nome e pasta), não só pelo nome.
- Leitor dos formulários na versão 2: os formulários já lidos são lidos de novo ao abrir o projeto.
### Corrigido
- Abrir o DLIS do teste a cabo na aba Perfis dava o erro "índice ETIM em unidade desconhecida". Agora a mensagem
  explica que o arquivo é indexado por tempo e indica onde ver os dados.

## [0.37.0] — 2026-10-29
Bloco 9, item 1: os formulários da ANP na pasta de poço.
### Adicionado
- **Leitura dos formulários CDPE da ANP** — Relatório Final de Poço (RFP), Relatório Final de Completação (RFCP) e
  Notificação/Relatório de Perfuração. São PDFs com texto e leiaute fixo; o SIAPP lê pela posição do texto, sem OCR,
  assim que o arquivo é baixado (e, ao abrir o projeto, os que já estavam baixados). Traz dados gerais e
  coordenadas, topos previstos × constatados, indícios, testemunhos, amostras laterais, análise de perfis, testes
  de formação (°API, vazão, pressão estática), temperaturas lidas e extrapoladas, amostragem de calha, revestimento
  e intervalos canhoneados, coluna de produção, teste na completação, fases da perfuração com o fluido e o peso
  da lama, e as observações.
- **Ficha do poço › Formulários da ANP**: tudo isso em tabelas, com °C e psi ao lado, e o botão "Ler os formulários
  de novo".
- **Avaliação de formação**: os intervalos da análise de perfis (RFP), os canhoneados (RFCP) e os testes com
  intervalo entram como intervalos candidatos; as temperaturas do RFP e o fluido/peso de cada fase aparecem como
  referência para o Rw, ao lado das do AGP.
- **Perfis**: topos constatados do RFP (marrom pontilhado; dão nome às unidades no eixo quando não há AGP) e faixa
  vermelha nos intervalos canhoneados.
- **Apelido automático**: a "sigla do poço na base do E&P" do RFCP (ex.: 1-BRSA-1304-BA = 1-FPA-1-BA) e o nome do
  poço para o operador viram outras grafias do poço — sem tomar o nome de outro poço do cadastro.
- Arcabouço comum dos leitores de dados do poço (`motor/dados_poco.py`, migração 10: `leituras` e `dados_poco`),
  com versão do leitor: um leitor melhorado relê sozinho os documentos lidos pelo anterior.

## [0.36.0] — 2026-10-29
Anotações de 29/10, antes do Bloco 9.
### Adicionado
- **Onde procurar o GR limpo e o da argila** (avaliação de formação): no arquivo inteiro, numa janela (topo e base)
  ou só nos intervalos; com P5 e P95 ou com mínimo e máximo. As duas linhas aparecem tracejadas na trilha do GR, o
  resultado mostra os valores e uma explicação na tela diz como cada opção funciona.
- **Legenda da litologia** dos perfis, com as classes de rocha do trecho visível.
### Mudado
- O GR limpo e o da argila automáticos passam a ser procurados **no arquivo inteiro** (antes: só nos intervalos).
  Num intervalo-alvo todo de arenito, o P95 dos intervalos não era folhelho e o Vsh saía alto demais. Avaliações
  antigas são refeitas do jeito antigo. Avisos quando o contraste entre os dois é pequeno.
### Corrigido
- O selo do arquivo ficava em "baixando" depois de terminar o download (o fim chegava, mas com o nome do evento
  trocado pelo tipo do arquivo). O arquivo já baixava certo; agora o selo vira "baixado" e o botão de abrir aparece.

## [0.35.1] — 2026-10-28
### Corrigido
- **"Resposta inesperada do portal: HTTP 503" ao conectar uma bacia**, enquanto o portal abria no navegador. O
  REATE tem dois servidores (200.237.2.133 e .134) e um deles estava respondendo 503 a tudo; o SIAPP caía sempre
  nele. Agora, diante de 502/503/504 ou de falha de conexão, tenta o outro servidor e fica no que responde. Se
  nenhum responder, a mensagem diz que o REATE está fora do ar e o que cada servidor respondeu.

## [0.35.0] — 2026-10-28
Bloco 8 do teste da 0.29: Comunidade.
### Adicionado
- **Painel de preenchimento e contribuição** (Comunidade › Painel): dos poços com pasta no REATE, quantos têm
  documentos, perfil, topos (AGP ou transcritos), dados transcritos, páginas revisadas, interpretações e
  produção — em número e porcentagem, no total e por bacia; quem contribuiu (dados, topos, correções do OCR,
  palavras, páginas, interpretações; poços; origem; período); atividade por mês; e onde ajudar (poços com
  perfil e sem topo, com documentos e sem dado transcrito).
- **Biblioteca de interpretações de perfil** (Comunidade › Biblioteca): a avaliação de formação calculada na
  aba Perfis pode ser compartilhada (título e comentário) com o arquivo (hash), as curvas, os métodos, os
  parâmetros e o resumo de cada intervalo — sem as curvas calculadas. Buscar por poço, autor, bacia e origem;
  ver os parâmetros; **comparar** de 2 a 6 lado a lado (intervalos casados pela profundidade, diferenças
  destacadas), inclusive com avaliações suas ainda não compartilhadas; **refazer nos Perfis** com os mesmos
  intervalos, curvas e parâmetros, e comparar o resultado com o original.
- **Formato de contribuição v3**: as interpretações vão no pacote e na base comunitária (tabela opcional
  `interpretacoes`), com autor e origem; importar, desfazer e aplicar a base valem para elas como para os
  dados transcritos. Os formatos 1 e 2 continuam aceitos. O SIAPP-dados (em `_publicar`) foi atualizado junto:
  esquema v3 (que também passa a aceitar o tipo `trecho`), validador e compilador.
- Na aba Perfis, uma nota avisa quando a biblioteca tem interpretações do poço aberto.
### Corrigido
- Duas avaliações de formação calculadas no mesmo segundo gravavam o mesmo registro em `execucoes/` (a segunda
  apagava a primeira). Agora a segunda ganha um sufixo.
- No modo escuro, os selos verdes ("ok") e vermelhos ficavam com fundo claro.

## [0.34.0] — 2026-10-28
Bloco 6 do teste da 0.29: Mapa e Seção.
### Adicionado
- **Legenda do mapa clicável**: um clique esconde ou mostra a categoria (só no cadastro, pasta no REATE, arquivos
  baixados; ou as do levantamento do acervo), dois cliques mostram só ela; "com dados transcritos" filtra só esses.
  A legenda mostra quantos poços há em cada categoria, e a lista avisa quantos estão escondidos.
- **Destacar poços**: um ou vários (pela barra lateral ou "Destacar no mapa" na ficha), com a cor escolhida,
  maiores e com o nome sempre à vista — mesmo fora do filtro. Enquadrar e limpar.
- **Produção na ficha do poço** (dados abertos da ANP já baixados do campo): período, primeiro e último mês
  produzindo, acumulados de óleo, gás, água e condensado, injeção, último mês, zonas e uma linha mensal de cada
  fluido. Sem a produção do campo, a ficha leva a Dados › Produção da ANP já no campo.
- **Seção pela linha desenhada no mapa**: cliques marcam A, os pontos intermediários (com curvas) e B; o mapa mostra
  a faixa de busca e numera os poços com topos no AGP ao longo da linha; "Abrir na Seção" monta a seção nessa ordem.
  Atalho também na aba Seção.

## [0.33.0] — 2026-10-28
Bloco 5 do teste da 0.29 (Perfis) e as cores do modo escuro.
### Adicionado
- **Sugerir curvas para um objetivo** (aba Perfis): litologia e correlação, porosidade, saturação de água,
  avaliação de formação, qualidade do poço, geomecânica. Marca a melhor curva de cada família que o arquivo
  tem, diz o porquê do conjunto e o que falta.
- **Buscar curva** por mnemônico, descrição, unidade ou família.
- **Faixa visível ao arrastar** sobre os perfis, em todas as trilhas, com topo, base e espessura.
- **"Fonte" e "qualidade" dos topos do AGP** explicadas na tela ("AGP antigo", "questionável"): na aba Perfis,
  na tabela da seção e na ficha do poço (que ganha a coluna Qualidade, com "questionável" em destaque). No
  eixo de profundidade dos perfis, o mouse num topo do AGP mostra nome, fonte e qualidade.
### Corrigido
- **Modo escuro**: textos e legendas dentro do visor do bloco 3D, da figura da seção, dos perfis, da página do
  documento e da legenda do mapa ficavam claros sobre fundo branco. Essas áreas agora são "papel": fundo branco
  e texto escuro em qualquer tema, como as figuras exportadas.
- **Cabeçalhos cortados nos perfis**: o nome da curva quebra a linha em vez de ser cortado, e todos os cabeçalhos
  têm a mesma altura (com cabeçalhos de alturas diferentes, as trilhas começavam em alturas diferentes e a
  profundidade não batia entre elas).

## [0.32.0] — 2026-10-28
Bloco 7 do teste da 0.29: Bloco 3D.
### Adicionado
- **Interpolação RBF** (funções de base radial): multiquádrica, multiquádrica inversa e gaussiana, com o
  plano de tendência. Raio (parâmetro de forma) e suavidade automáticos pela validação cruzada, ou fixos em
  Parâmetros avançados. Deixar um poço de fora atualiza os coeficientes sem refazer o sistema, como na spline.
  Entra na comparação dos métodos (multiquádrica e inversa).
- **Qual método usar?** no passo de interpolação: escolha o ambiente do reservatório (leque, fluvial,
  costeiro, carbonato, rifte com falhas, dobra suave ou "não sei") e a lista mostra cada método como
  indicado, possível ou evitar, com o motivo de cada um — pelo ambiente, pelos dados (quantos poços,
  espaçamento, agrupamento, mergulho regional) e, depois de "Comparar métodos", pelo erro nos seus poços
  (pesa mais que as regras). "Usar o indicado" preenche o formulário. As regras ficam em
  `recursos/guia_interpolacao.json`, editável.
- **Aparência dos poços** no visor: marcador da cabeça (forma, cor, tamanho), cor da linha, espessura e cores
  da trilha, discos nos topos, legenda e "poços por cima do bloco". Vale na hora, fica guardada e a figura
  estilo artigo usa a mesma.
- **O que é "deixar um poço de fora" e "comparar métodos"**: explicação na tela, passo a passo e com exemplo.
### Mudado
- Painel do bloco em quatro passos, na ordem do trabalho: 1 Poços → 2 Interpolação → 3 Grade e unidades →
  4 Montar ("Trazer o campo e montar" saiu do meio da escolha dos poços).
- No bloco fechado, os poços e as trilhas (pay, indícios) aparecem por cima do bloco: antes ficavam
  escondidos dentro dele, e trocar "Nos poços" parecia não fazer nada.
- A escolha de "Nos poços" (só a linha, pay, indícios) continua ao montar de novo.
- Legenda das trilhas no canto de baixo (cobria o nome de um poço).
### Corrigido
- A legenda das trilhas não sumia quando devia (o atributo `hidden` era ignorado pelo CSS).

## [0.31.0] — 2026-10-27
Blocos 3 e 4 do teste da 0.29: navegação nos documentos e texto do OCR.
### Adicionado
- **Texto arrumado das páginas** (`motor/layout.py`): o texto é remontado pelas posições das palavras
  na página, em vez de sair na ordem dos blocos do OCR (três palavras, quebra, uma letra, quebra…).
  - Pedaços da mesma linha voltam para a mesma linha ("Setor⏎de⏎Avaliação" → "Setor de Avaliação").
  - Formulários ficam em linhas e colunas ("POÇO: 7-GMR-13-RN    CAMPO: GUAMARÉ").
  - Texto corrido vira parágrafo; "cimen-⏎tação" vira "cimentação".
  - Palavra partida em duas peças é juntada quando a palavra inteira existe e uma das peças não
    ("Avalia ção" → "Avaliação"; "a ponta" continua separado).
  - Riscos, manchas e letras soltas na borda saem do texto (o original continua guardado).
  - Vale na página, na busca e nos trechos dos resultados. O índice é refeito sozinho na primeira
    abertura (estrutura nova).
- **"Como o OCR leu"**: alterna com o texto arrumado, para comparar.
- **Editar o texto da página** à mão (parágrafos, quebras, palavras): o texto revisado passa a valer na
  página e na busca, com selo "revisado", autor e data. O que o OCR leu continua guardado e também é
  achado pela busca. "Voltar ao texto automático" apaga a revisão (dois cliques). Não dá para trocar de
  página com uma edição por salvar. Tabela nova `paginas_revisadas` no banco.
- **Possíveis erros** de cada página: palavras fora de um dicionário de português (~385 mil palavras,
  com flexões), do vocabulário técnico e das palavras que o próprio acervo repete, com sugestão
  (letra trocada, faltando, sobrando e as confusões típicas do OCR: rn↔m, cl↔d, 1↔l…). Um clique abre o
  editor de correção já preenchido; a correção vale em todos os documentos, como antes.
- **Aviso de página pouco legível** quando menos de 40% das palavras são palavras conhecidas
  (manuscrito, gráfico, carimbo): o texto serve de pista, vale a imagem.
- **Transcrever um trecho de texto** (tipo novo "Trecho do texto (citação)"): a caixa desenhada na
  imagem traz o texto remontado e corrigido daquele pedaço; guarda as quebras de linha, até 4000
  caracteres.
- **Lista de documentos agrupada** por bacia › poço (com o campo do cadastro da ANP) ou bacia › poço
  › pasta, com filtro por texto, bacia, campo e situação (com texto, pendentes, com páginas revisadas).
- **Buscar em**: todos os documentos, só os do filtro da lista (ex.: um campo ou uma bacia) ou só o
  documento aberto (resultados em ordem de página).
- **Andar pelos achados**: "‹ anterior · achado 2 de 14 · próximo ›" no painel da página, de documento
  em documento (também F3 e Shift+F3).
- **Ir à página**: campo para pular direto para uma página do documento.

## [0.30.0] — 2026-10-27
Bloco 2 do teste da 0.29 (organização geral, navegação e configurações), pela maquete aprovada.
### Mudado
- **Abas pelo fluxo de trabalho**: Projeto · Dados · Mapa · Documentos · Perfis · Interpretação ·
  Viabilidade · Comunidade.
  - **Projeto** (era Início): abrir o projeto, números, últimas mensagens, etapas do trabalho; o guia do
    REATE fica recolhido.
  - **Dados** junta tudo o que se baixa, em sub-abas: Catálogo do REATE (com "Catalogar a bacia
    conectada"), Cadastro da ANP, Levantamento do acervo, Produção da ANP e Camadas geográficas. Saíram
    do Mapa e do Bloco 3D.
  - **Mapa** fica só para ver: filtros, camadas no mapa e a ficha do poço.
  - **Interpretação** reúne Seção e Bloco 3D (botões no alto da barra lateral).
  - **Viabilidade** ganha aba e mapa próprios (campo × infraestrutura, viabilidade econômica, blocos e
    campos × infraestrutura).
- O passo "Pasta do projeto" do Catálogo saiu (é o "Abrir o projeto" da aba Projeto).
### Adicionado
- **Abas em janelas próprias** ("Abrir em janela"): a aba vira uma janela do Windows, para outro monitor,
  maximizar ou encaixar (Win+setas). Todas as janelas usam o mesmo motor: downloads, OCR e mensagens
  aparecem em todas, e um pedido de uma aba que está noutra janela vai para lá (ex.: "Ver" um documento
  na ficha do Mapa abre na janela de Documentos). Fechar a janela (ou "Voltar para a principal") devolve
  a aba. Fechar a principal fecha o SIAPP.
- **Dividir** a janela principal em duas áreas lado a lado, com divisória arrastável (dois cliques:
  metade), escolha da aba da direita e troca de lados.
- **Arranjo lembrado** (pode desligar): posição, tamanho e monitor de cada janela, divisão, sub-abas e
  quais abas estavam destacadas voltam ao abrir. Janela cujo monitor não existe mais abre na tela
  principal.
- **Configurações** (engrenagem nova):
  - sete paletas, cada uma em claro e escuro — **Marinho e lima** é a padrão; as outras são Petróleo,
    Oceano, Arenito, Grafite, Floresta e Alto contraste;
  - tamanho do texto (pequeno, médio, grande);
  - abrir o projeto sozinho ao iniciar;
  - lembrar o arranjo das janelas.

  Ficam em `ambiente_teste/preferencias.json`. Mudar as cores muda todas as janelas juntas.
- **Diagnóstico**: versões (SIAPP, Python, pywebview, PyMuPDF…), tamanho do banco, OCR instalado, erros
  desta sessão, últimos erros do `siapp.log` com a causa, ações mais demoradas, e **Copiar para enviar**.
- **Exportações** no alto: as pastas `exportacoes`, `execucoes`, `sig` e `contribuicoes`, com quantos
  arquivos e o último, e "Abrir".
- **Barra lateral recolhível** em todas as abas (o estado fica guardado).
- **Histórico de mensagens**: clicar na mensagem do rodapé (ou em "Histórico") mostra todas as da
  sessão, inteiras, com a hora.
- **Abrindo o projeto**: tela com cada passo (pasta, banco, arquivos, catálogo, índice de texto) e o
  progresso.
### Corrigido
- O levantamento do acervo passa a colorir o Mapa pelo acervo mesmo quando termina com o Mapa fechado.
- A caixa "Filtrar" dos blocos × infraestrutura aparecia antes de medir.

## [0.29.1] — 2026-10-26
Bloco 1 das mudanças do teste da 0.29 (erros que afetam dados).
### Corrigido
- **Poço aparecendo em duas bacias na ficha** (ex.: 7-GMR-13-RN em "Alagoas · Categoria-7_parte28"
  e em "Potiguar"). Causa: a lista de uma categoria era gravada na bacia conectada no momento
  em que a listagem *terminava*. Listar a Categoria-7 da Potiguar (36 partes, alguns segundos)
  e conectar em Alagoas nesse meio-tempo gravava as 7.198 pastas da Potiguar como Alagoas — e a
  janela mostrava essa lista sob Alagoas, com "Pasta não encontrada" ao clicar. Agora cada
  ação do catálogo (listar, catalogar, abrir um poço, baixar) usa um retrato da conexão do
  começo, grava na bacia que foi listada, e recusa um pedido feito para a bacia anterior; a
  janela descarta a lista que chega depois da troca.
- **Reparo automático** dos projetos afetados, uma vez ao abrir: sai o registro repetido (mesma
  pasta, mesmo caminho, em duas bacias) quando o cadastro da ANP põe o poço na outra bacia — ou,
  sem o poço no cadastro, quando a leva listada é quase toda de poços de outra bacia. Pasta que
  só existe numa bacia nunca é apagada. Fica registrado no histórico (`reparou_catalogo`).
- Listar uma categoria de novo agora **substitui** o que estava guardado dela (pastas que sumiram
  do portal saem do catálogo).
- **Correções de OCR coloridas à vista.** As cores já eram aplicadas, mas depois de corrigir o
  texto voltava ao topo e a palavra (já azul) ficava fora da vista. Agora a página volta ao mesmo
  ponto, a palavra corrigida pisca, e **a imagem da página contorna as palavras corrigidas** nas
  mesmas cores (verde = dicionário, azul = você, roxo = comunidade).
- Corrigir para a mesma palavra lida não some mais num aviso cortado no rodapé: o editor explica;
  numa palavra corrigida pelo dicionário ou pela comunidade, isso vale como "o OCR estava certo".
### Adicionado
- A ficha avisa quando uma pasta do REATE está num compartilhamento de bacia diferente da do
  cadastro da ANP.

## [0.29.0] — 2026-10-18
### Adicionado
- **Grau API e densidade do gás a partir das pastas de poço** (`motor/fluidos.py`): para o
  campo da viabilidade, o SIAPP procura no texto (embutido ou OCR) dos documentos dos poços
  do campo valores como "28,5 °API", "Grau API: 30" e "densidade do gás 0,70", e lista as
  páginas que citam API, densidade do gás ou análise de óleo/gás sem número legível (formulários
  manuscritos). Cada leitura mostra poço, arquivo, página e trecho, e pode ser aberta,
  **confirmada** (vira dado transcrito com a página como fonte) ou **descartada**.
- Ordem de uso na viabilidade: o que o usuário digita → dados transcritos (mediana) → leitura
  automática (mediana, com aviso de que o OCR erra números) → nada (API) ou 0,65 (densidade).
  A memória de cálculo diz de qual poço, documento e página veio cada valor.
- Tipo de dado transcrito **Propriedade de fluido** (`propriedade_fluido`), com nomes
  sugeridos (Grau API do óleo, Densidade relativa do gás, RGO, Bo, viscosidade, BSW); "abrir e
  transcrever" leva à página com o tipo, o nome, o poço e a unidade já preenchidos. O esquema v2
  do SIAPP-dados aceita o tipo novo.
- "Processar os documentos pendentes" põe na fila de texto/OCR os documentos baixados dos
  poços do campo que ainda não têm texto.

## [0.28.0] — 2026-10-18
### Adicionado
- **Bo, Rs e Bg estimados por correlação** quando não informados (pode desligar): Rs e Bo por
  Standing (1947), a partir do grau API, da densidade do gás e de P e T do reservatório; Bg pelo Z
  de Papay (1968) com as pseudocríticas de Sutton (1985). Cada correlação é um passo da memória de
  cálculo (com as conversões de unidade à vista) e pode ser trocada como qualquer equação. Aviso
  quando o caso sai da faixa original da correlação. Campo de gás precisa só de Bg, que sai da
  profundidade dos poços e da densidade do gás (padrão 0,65, constante editável).
- **Blocos e campos × infraestrutura** (aba Mapa): para cada bloco exploratório (ou campo de
  produção), a distância geodésica até a feição mais próxima da camada escolhida (gasoduto de
  transporte por padrão) e o custo do duto pelos parâmetros da viabilidade. Mapa colorido por
  classe de distância (toca, até 10, 10–50, 50–100, mais de 100 km), tabela das 40 mais próximas
  com filtro, CSV com todas, as fórmulas e as entradas; cada medição gravada em
  `execucoes\viabilidade\`. Os 274 blocos contra o gasoduto: ~8 s.
### Alterado
- Na memória de cálculo, as condições do reservatório (P, T) vêm antes do espaço poroso, porque
  as correlações dependem delas.

## [0.27.0] — 2026-10-18
### Adicionado
- **Memória de cálculo** da viabilidade econômica: cada execução grava em
  `execucoes\viabilidade\` um JSON completo e uma página HTML (abre no navegador, imprime em PDF) com
  os dados de entrada e a fonte de cada um (arquivo da ANP, PD, camada, valor informado, constante
  padrão ou alterada), cada passo com a equação, a equação com os números e o resultado, a equação de
  estado com todos os valores intermediários (κ, α, a, b, A, B, raízes, Z, translação, volume
  molar) e o cálculo por infraestrutura. Na tela, "Memória de cálculo — passo a passo"; no CSV, a
  mesma memória em linhas.
- **Constantes editáveis**, cada uma com valor padrão, fonte e faixa aceita: fator de custo por
  fluido, gás por m³ de óleo equivalente, Bw, PCI do H₂, condição padrão, pressão na superfície e
  as propriedades críticas de CO₂, H₂ e CH₄.
- **Equações editáveis**: cada passo (custo por km, comprimento, custo do duto, espaço simples,
  gás livre, espaço poroso, pressão, temperatura, massa, massa útil, volume padrão, energia,
  indicador) é uma fórmula em texto. Dá para escolher uma alternativa pronta (custo afim ou por km
  informado; espaço só com óleo ou com a água; espaço poroso sem água) ou escrever a própria, com
  os símbolos listados e + − * / ^, min, max, abs, sqrt, exp, ln, log10. O leitor de fórmulas não
  executa código; variável desconhecida, divisão por zero ou erro de escrita dão mensagem clara.
  Equação ou constante alterada fica marcada na memória e nos avisos.
- Parâmetros novos: parcela fixa do custo (R$ mil/km) e densidade informada (no lugar de
  Peng-Robinson).

## [0.26.0] — 2026-10-18
### Adicionado
- **Viabilidade econômica** (`motor/economia.py`, aba Mapa, depois de medir as distâncias): para
  cada infraestrutura medida, o custo do duto até ela e o indicador **investimento ÷ capacidade de
  injeção** do campo, em três métodos:
  - **Simples (PIBIC)** — o espaço é o volume produzido, em m³ de óleo equivalente (óleo +
    condensado + gás ÷ 1.000). Vale para todo campo com produção baixada.
  - **Espaço poroso** — o volume liberado no reservatório, Np·Bo + (Gp − Np·Rs)·Bg + Wp − Wi − Gi·Bg.
    Pede Bo (campo com óleo) e Bg (campo com gás); Rs opcional. Água e injeção entram só com a
    série mensal completa.
  - **Pela molécula** — esse espaço cheio de CO₂, H₂ ou CH₄ nas condições do reservatório (Peng-Robinson
    com translação de volume; P e T informados ou por gradiente sobre a profundidade dos poços);
    em t de CO₂, t de H₂ útil (descontado o gás de colchão) e MWh, ou m³ de gás natural.
- Custo do duto: R$ por polegada·km de projetos reais dos Planos Indicativos de Gasodutos da EPE
  (PIG 2024 por padrão: R$ 488 mil/pol·km, jun/2024; PIG 2022 e 2019 como alternativas, ou valor
  próprio), × diâmetro × fator do fluido (CO₂ ×1,20; H₂ ×1,05) × fator de traçado.
- Produção acumulada: a série mensal se cobre todo o histórico sem buracos; senão a acumulada do
  PD (+ a produção mensal logo depois dela); senão o período baixado, avisando que subestima.
- Os parâmetros ficam guardados por campo; CSV em `exportacoes\producao\viabilidade_<campo>.csv`.

## [0.25.0] — 2026-10-18
### Adicionado
- **Camadas no mapa** (aba Mapa, "Mostrar no mapa"): cada camada baixada liga e desliga no
  mapa, com cor por tipo (gasoduto de transporte em vermelho, escoamento em laranja tracejado,
  hidrogênio verde em verde, campos em azul…) e os atributos ao clicar. Funciona mesmo sem o
  cadastro de poços.
- **Campo e infraestrutura** (`motor/viabilidade.py`, aba Mapa): para um campo, a distância do
  polígono da ANP até o gasoduto de transporte, o duto de escoamento, a UPGN, o city gate, o
  projeto de hidrogênio, a termelétrica (fonte de CO₂), o porto e a cidade mais próximos
  ("no campo" quando a feição atravessa o campo), com linhas tracejadas no mapa; e a
  **depleção** pelo sumário do PD (óleo e gás produzidos ÷ in place), atualizada com a
  produção mensal da ANP quando a série baixada começa logo depois da data do PD. CSV.
  Distância geodésica entre os pontos mais próximos (projeção azimutal equidistante centrada
  no campo para achá-los).

## [0.24.1] — 2026-10-17
### Adicionado
- Camada **Hidrogênio verde: unidades e projetos** (EPE, mapa de projetos de hidrogênio, edição
  mais recente publicada — out/2024): plantas piloto, P&D e projetos de H₂ verde e amônia
  (Pecém, Suape, Açu, Camaçari…) com capacidade (t/ano), finalidade, estágio e investimento.
  Marcada por padrão no quadro "Camadas geográficas".
### Corrigido
- Camadas da EPE de serviços que não paginam: consulta pelos ids, em lotes; feições sem
  coordenadas na fonte ficam de fora e são contadas.

## [0.24.0] — 2026-10-17
### Adicionado
- **Produção do campo pela ANP** (`motor/producao.py`, quadro "Produção do campo (ANP)" na aba
  Bloco 3D): produção e injeção mês a mês **por poço** (1941 até ~2 meses atrás), **por zona
  produtora** (2014 em diante), a ficha e o **polígono** do campo e o **sumário do Plano de
  Desenvolvimento** (volume in place, produção acumulada, poços, reservatórios). Os arquivos
  nacionais da ANP ficam numa cópia compactada e servem para os próximos campos; CSV.
  Tabelas `producao_poco`, `producao_zona`, `campos_anp` (migração 7). Só traz e guarda: as
  contas (depleção) ficam para a próxima versão.
- **Camadas geográficas** (`motor/camadas.py`, quadro "Camadas geográficas" na aba Mapa):
  gasodutos de transporte, de escoamento e de distribuição, UPGNs, city gates, compressão,
  GNL e termelétricas fósseis (EPE); campos de produção e blocos exploratórios (ANP); dutos,
  termelétricas, linhas de transmissão, subestações, portos, cidades, estados, ferrovias e
  rodovias (IBGE BC250, baixando só as camadas escolhidas de dentro do zip de 800 MB). GeoJSON
  e o shapefile original em `sig/`, para o QGIS. Leitor de shapefile próprio (sem GDAL).
- **Montar este campo**: um clique traz os poços do campo e monta o bloco com a escala de
  reservatório; escolher o campo já traz os poços.

## [0.23.0] — 2026-10-17
### Adicionado
- **Vários métodos de interpolação** (`motor/interpolacao.py`), um por campo — topos
  (estrutura), espessuras e propriedades: **linear** (o de antes), **inverso da distância**,
  **spline de placa fina** (suavidade 0–1 ou automática pela validação cruzada), **krigagem
  ordinária** (variograma esférico/exponencial/gaussiano ajustado nos poços, alcance, pepita,
  anisotropia) e **tendência + krigagem** (plano ou superfície de 2º grau + krigagem do
  resíduo). Na janela, cada método e cada parâmetro com uma explicação curta e "bom para".
- **Bloco fechado topo a topo**: cada limite interpolado direto dos poços, cortado para não
  passar acima do de cima — o erro não se acumula como no empilhamento por espessuras (que
  continua disponível). É o que faz spline e krigagem funcionarem no bloco fechado.
- **Mapa de incerteza da krigagem**: o σ de cada topo para colorir a superfície.
- **Comparar métodos**: a validação cruzada com seis combinações, tabela por unidade, o
  sugerido e **Usar o melhor e montar de novo**; CSV e figura estilo artigo (símbolos, escala
  log). Tirar um poço da spline/krigagem atualiza os coeficientes (Dubrule), sem refazer o sistema.
- **Escala: reservatório ou bacia** — ponto de partida para poços, margem, grade e métodos
  (reservatório: spline topo a topo; bacia: tendência + krigagem, 15 km, mapa de incerteza),
  escolhido pela comparação no Estreito e na Potiguar. Guia por tipo de reservatório em `docs/bloco.md`.
### Mudado
- Espessuras por métodos lisos multiplicadas pela presença interpolada linear (zeros onde a
  unidade falta); krigagem com menos de 8 poços vira linear, com aviso.
- O registro do bloco guarda a interpolação e a escala; blocos anteriores reabrem como
  linear por espessuras.
### Corrigido
- Bloco 3D: os campos dos outros modos de escolha (poço e raio, bacia) apareciam todos juntos.

## [0.22.0] — 2026-10-17
### Adicionado
- **Saídas do bloco** (quadro "Saídas do bloco", embaixo do visor):
  - **Mapas para SIG** (`motor/bloco_mapas.py`): terreno, topo e espessura (isópaca) de cada
    camada em **GeoTIFF** (um por mapa, float32, sem dado = −9999) e um **XYZ** com todos, em
    SIRGAS 2000 / UTM (fuso do centro do bloco, EPSG 31977–31985). GeoTIFF escrito pelo
    SIAPP (sem GDAL); conferido com o rasterio.
  - **Simulador** (`motor/bloco_eclipse.py`): deck no formato **ECLIPSE** (.DATA + .GRDECL +
    .inc) para tNavigator, OPM, Petrel. Grade corner-point em UTM, formações escolhidas (o
    embasamento fica de fora por padrão) divididas em camadas proporcionais à espessura;
    ACTNUM (fora do contorno ou mais fina que 0,1 m) com PINCH; **FIPNUM por formação**;
    **PORO e NTG da avaliação de formação**; poços com o caminho real, fechados.
    Permeabilidade, PVT, curvas relativas e contatos saem **provisórios**, marcados nos
    arquivos e no LEIA-ME. Teto de 275.625 células (licença acadêmica do tNavigator),
    ajustável; prévia do tamanho da grade antes de exportar. Conferido com o parser do OPM.
  - **Volumetria preliminar** (`motor/bloco_volumetria.py`): por formação, volume de rocha,
    N/G, φ, Sw (da avaliação ou digitados — cada valor diz de onde veio), volume poroso,
    hidrocarboneto, óleo in place (com Bo) e capacidade teórica de CO₂ (com E e ρ). CSV.
  - **Modelo 3D (.glb)** (`motor/bloco_glb.py`): o bloco fechado com as camadas ligadas, o
    exagero da tela e os poços, para o PowerPoint (Inserir → Modelos 3D) ou o Blender.
- `motor/utm.py`: UTM no SIRGAS 2000 (séries de Krüger), ida e volta; confere com o pyproj
  ao milímetro.

## [0.21.0] — 2026-10-17
### Adicionado
- **Validação cruzada do bloco** (`motor/bloco_validacao.py`), botão **Deixar um poço de
  fora**: cada poço sai do bloco, o bloco é refeito sem ele e prevê a cota de cada topo
  daquele poço, comparada com a do AGP. Nos dois modos (bloco fechado e superfícies), com as
  mesmas regras da montagem. Por unidade: viés, mediana do erro, erro que 68% não passam,
  máximo (e o poço); por faixa de distância ao poço mais próximo com a unidade; erro da
  espessura. Guardada no registro do bloco (reabre junto); CSV e **figura estilo artigo**
  (previsto × AGP, erro × distância, tabela). Tirar um ponto da triangulação só refaz a
  estrela dele (conferido igual a refazer tudo): 429 poços em ~12 s.
- **Prognóstico num ponto**: clicar no bloco (ou escrever lat, lon) mostra a coluna prevista
  — topo (cota e profundidade abaixo do terreno), espessura e base de cada camada,
  interpolado ou extrapolado, distância ao poço mais próximo com a unidade e, com a validação
  feita, a **incerteza** de cada topo (o erro que 68% das previsões não passaram, da unidade
  na mesma faixa de distância). Pino no visor; CSV.
- Na dica de cada topo dos poços: a cota prevista sem aquele poço e o erro.
### Corrigido
- **Topos abaixo do fundo do poço** (estimativas da operadora, não perfuradas — ex.:
  Embasamento a 6.134 m no 1-JD-2-RN, de 1.865 m) ficam fora do bloco, com aviso; base abaixo
  do fundo conta como não atingida. Na Potiguar (Cat. 1), 64 poços; a base automática do
  bloco regional subiu de −6.310 para −4.690 m.
- Base automática do bloco fechado pelo dado (fundos e limites observados), não pela
  interpolação.
- Pontos repetidos (poços do mesmo pad) entram uma vez, com a média.

## [0.20.0] — 2026-10-17
### Adicionado
- **Bloco fechado** (`motor/bloco_solido.py`): da mesma montagem do bloco, o volume inteiro
  — contorno convexo dos poços (+ margem), do **terreno** a uma **base plana** — fatiado nas
  unidades, com **paredes retas**. Os dois modos (*Superfícies* e *Bloco fechado*) trocam
  num clique, sem montar de novo.
  - Camadas **empilhadas por espessura** (isópacas): unidade ausente num poço que passou pela
    posição dela = espessura 0; poço que parou antes = desconhecida. Um limite de referência
    é interpolado direto e os outros somam/subtraem espessuras ≥ 0 — **as camadas nunca se
    cruzam** e passam pelos topos do AGP nos poços.
  - Terreno pela cota altimétrica do cadastro (0,0 = não informada → mesa rotativa menos a
    diferença mediana dos outros poços); camada cinza entre o terreno e o primeiro topo do AGP
    e abaixo da última unidade com base atingida. Base automática (abaixo do poço mais fundo)
    ou a cota pedida.
  - **Fora do contorno dos poços com a espessura, mais claro** (extrapolado: valor da borda
    mais próxima, contínuo). Por camada: área, espessura máxima, volume (km³) e % extrapolada.
  - **Corte**: tira um quadrante (sudoeste, sudeste, nordeste ou noroeste), com controles
    O–L e S–N; o corte é fechado por tampas com as camadas.
  - **Seção A–A′** como parede ao longo dos poços da aba Seção, prolongada até a borda; o
    bloco fica translúcido.
  - **Camadas afastadas** na vertical.
  - **Figura estilo artigo** do bloco fechado (com corte, camadas afastadas ou parede A–A′).
- Campo "Base do bloco fechado" nas opções do bloco.

## [0.19.0] — 2026-10-17
### Adicionado
- **Dados direcionais** (`motor/direcionais.py`): leitor dos 5 leiautes da pasta "Dados
  Direcionais" (antigo da Petrobras, novo com cabeçalho, tabulado, por coordenadas, relatório
  "Deviation data"); trajetória pela **curvatura mínima** a partir de prof. medida, inclinação
  e azimute (confere com a prof. vertical do arquivo); arquivo de outro poço na pasta é
  reconhecido pelo cabeçalho e não é usado. Tabela `direcionais` (migração 6), cópias em
  `ambiente_teste/direcionais/`. Lidos no levantamento (opção marcada) e pelo botão **Ler as
  trajetórias** da aba Bloco 3D.
- **Bloco 3D, etapa 2** (requisito 7.4 da Especificação):
  - poço desviado com trajetória: desenhado pelo caminho real, e **cada topo na posição real**
    (x, y na prof. medida do topo) — as superfícies usam essas posições;
  - **trilhas nos poços**: classes da avaliação de formação mais recente de cada poço
    (não reservatório · reservatório sem pay · pay · **pay com indício de gás** do AGP), em
    blocos de 2 m com prioridade de classe (um pay fino nunca some); ou os **indícios de
    óleo e gás** do AGP;
  - **propriedade no topo** de uma unidade: HPV, net pay, N/G, φ média ou Sw média da
    avaliação, interpolada entre os poços avaliados (3 ou mais), com escala de cor; as outras
    superfícies ficam translúcidas;
  - **figura estática no estilo artigo** da vista atual: projeção ortográfica, serifa,
    moldura, legenda, escala de cor, norte, notas de fonte e método; SVG, PDF e PNG 300 ppp.

## [0.18.0] — 2026-10-17
### Adicionado
- **Aba Bloco 3D**: poços no espaço e superfícies de topo das unidades pelos topos do AGP.
  - Poços de um campo (margem 0), em volta de um poço, todos da bacia (bloco regional) ou os
    da aba Seção; poço muito longe dos demais fica de fora, com aviso.
  - Superfícies por **interpolação linear** nos triângulos de Delaunay, só **dentro do
    contorno convexo** dos poços que têm a unidade; margem opcional preenchida pelo poço mais
    próximo; fora, nulo. **Área do contorno** pelo shoelace. Corte opcional por distância
    ao poço mais próximo. Sem superfície com menos de 3 poços ou poços quase alinhados.
  - Avisos de superfícies que se cruzam e de poços desviados (desenhados na vertical).
  - Visor 3D (three.js 0.160, em `ui/vendor/three/`): exagero vertical, opacidade, unidades
    liga/desliga, nomes, caixa com eixos (km e cota), norte, vistas prontas, dados do poço
    ao passar o mouse.
  - Registro em `execucoes/bloco_<data-hora>.json`, blocos anteriores, **PNG** com legenda e
    carimbo, **CSV** dos topos e da grade das superfícies. `docs/bloco.md`.
### Alterado
- A coluna de cada poço (unidades em cota, mesa, fundo) saiu de `secao.montar` para
  `secao.dados_poco` / `secao.coluna_poco`, usadas pela seção e pelo bloco.

## [0.17.0] — 2026-10-16
### Adicionado
- **Esquemas de ferramentas**: o SIAPP diz o que é cada arquivo de perfil do poço —
  perfilagem convencional, teste de formação a cabo, imagem, RMN, cimentação, correlação…
  — com nº da corrida, passada (principal/repetida) e fase.
  - Pelo **nome** (sem baixar nada): o esquema se liga aos perfis da mesma corrida
    (`raw1_toolstring.pdf` ↔ `raw1-10028.dlis`, `RFT_tool.pdf` ↔ `RFT1..8.DLIS`); 84% dos
    perfis da Potiguar ficam ligados só assim.
  - Pela **leitura do PDF**: texto embutido ou OCR (modelo inglês, baixado uma vez, ~4 MB;
    imagem de baixa resolução ampliada; página girada tratada). Ferramentas reconhecidas
    pelo dicionário `recursos/ferramentas.json` tolerando os erros típicos do OCR,
    fabricante, carimbo (data, poço, cadastro, operadora), diâmetro máximo.
- Ficha do poço: seção **Esquemas de ferramentas** (tipo, ferramentas, o que medem,
  perfis da corrida, abrir o PDF) e botão **Ler os esquemas**; rótulo da corrida em cada
  arquivo de perfil do acervo.
- Aba Perfis: rótulo da corrida na lista e no cabeçalho do perfil aberto, com as ferramentas.
- Levantamento: etapa 4 opcional, **ler os esquemas de ferramentas**; resumo por tipo.
- Tabela `esquemas` no banco (migração 5); cópias em `ambiente_teste/esquemas/`.
  `docs/ferramentas.md`. `docs/roteiro.md` com o que fica para o final.

## [0.16.0] — 2026-10-16
### Adicionado
- Seção estratigráfica no **estilo clássico (indústria)**, agora o padrão: coluna
  litológica com **padrões de rocha** a partir da calha do AGP, trilha GR e escala de
  profundidade medida em cada poço, corpos das formações em pastel com o nome, linhas de
  topo, **discordâncias** onduladas, indícios de óleo/gás, símbolo do poço pela
  classificação, pontas A–A′, escala gráfica, **mapa de localização** e **carimbo**.
- Opção **Estilo** na aba Seção (clássico / moderno); o estilo fica no registro e volta ao
  reabrir uma seção.
### Corrigido
- Duas seções montadas no mesmo segundo gravavam o mesmo registro.

## [0.15.0] — 2026-10-16
### Adicionado
- **Aba Seção — seção estratigráfica** a partir dos topos do AGP: poços lado a lado (até 20),
  correlacionados pela unidade registrada pela operadora; faixa de cada unidade entre
  vizinhos e linha do topo.
- Escolha dos poços um a um, pela ficha (**Adicionar à seção**) ou **ao longo de uma linha**
  A–B com distância máxima.
- Ordem ao longo da linha, pela direção de maior espalhamento (componente principal) ou
  na ordem da lista; espaçamento proporcional à distância ou igual.
- Eixo em **cota** (do AGP) ou **nivelado** no topo de uma unidade (datum); janela vertical.
- Formações, membros e camadas ou grupos; litologia de calha; **curva GR** dos perfis já
  lidos, convertida para cota (mesa − prof; poço desviado pelos pontos do AGP).
- Aviso de **saltos** do mesmo topo entre vizinhos acima de um limiar.
- Desenho no estilo de artigo (serifa, moldura, marcas para dentro, legenda com moldura,
  exagero vertical); cor fixa por unidade (`slot` em `recursos/estratigrafia.json`, paleta
  conferida para daltonismo).
- Registro em `execucoes/secao_<data-hora>.json` + `.svg`; reabrir seções anteriores;
  exportar **SVG, PNG 300 ppp, PDF e CSV** dos topos usados. `docs/secao.md`.

## [0.14.1] — 2026-10-16
### Corrigido
- **AGP no leiaute novo do BDEP** (`<poço>_dados.txt`, poços mais novos) era recusado como
  "Não parece um AGP" — 72 de 438 na Categoria 1 da Potiguar. Agora lê cabeçalho (com o nome
  antigo da Petrobras), unidades lito e cronoestratigráficas, sequências, discordâncias e
  marcos, lama e BHT por corrida, temperatura extrapolada, perfis corridos, indícios,
  litologia interpretada e revestimentos. Também o `_cabecalho.txt` (só perfilagem).
- Letra de nível **C (Camadas)**: "C PONTUB" (142 poços) virava uma unidade sem nível.
- Siglas com espaços repetidos ("ACU  4", "BFL  PEN") são normalizadas.
- Perfis corridos com colunas depois da base (amostras, níveis) eram ignorados.
- Contagem de AGPs no portal considerava só `*_agp*.txt`.
### Adicionado
- Levantar de novo relê os AGPs lidos por um leitor mais antigo **da cópia local**, sem baixar
  (coluna `leitor`, migração 4 do banco).
- Dicionário estratigráfico: 16 unidades da Potiguar (Apodi, Areia Branca, Agulha, Macau,
  Tibau, Guamaré, Ponta do Mel, Quebradas, Porto do Mangue, Upanema, Galinhos, Ponta do
  Tubarão, Açu 1 a 4).
- Ficha do poço: cota altimétrica e nome antigo (Petrobras) quando o AGP traz.

## [0.14.0] — 2026-10-16
### Adicionado
- **Leitura do AGP (Dados Gerais de Poço, ANP)** como 3ª etapa do Levantamento do acervo
  (opção *Ler os AGPs*): cabeçalho, revestimentos, topos das unidades estratigráficas,
  indícios de hidrocarboneto, dados de lama por corrida (Rm, Rmf, Rmc, BHT), temperatura
  extrapolada, zonas-reservatório, testes de formação (com salinidade) e litologia de calha.
  Cópia local em `agp/<bacia>/`; tabelas `agp` e `agp_unidades` (migração 3 do banco).
- AGP guardado na pasta de **outro poço** é associado ao poço do próprio AGP e sinalizado.
- Ficha do poço: seção *AGP — dados gerais do poço* e botão **Abrir o AGP**.
- Avaliação de formação: unidades e zonas do AGP como intervalos candidatos; Rm/Rmf/BHT do
  AGP como referência para o Rw.
- Gráfico de perfis: topos do AGP (linhas tracejadas) e trilha **Litol. (AGP)**.
- Exportação `<bacia>_topos.csv`; `recursos/estratigrafia.json` (siglas → nomes);
  `docs/agp.md`.

## [0.13.0] — 2026-10-16
### Adicionado
- **Avaliação de formação no intervalo-alvo** (aba Perfis): Vsh pelo GR (linear ou Larionov
  para rochas terciárias ou mais antigas), porosidade (densidade, densidade-nêutron com
  correção de gás, sônico de Wyllie; correção de argila opcional), Sw (Archie ou Simandoux),
  cortes de Vsh, φ e Sw, **reservatório, net pay, N/G e HPV** por intervalo.
- Controle de qualidade: arrombamento (cáliper − broca) e densidade suspeita (|DRHO|); o
  resumo mostra quanto do net pay cai em trechos suspeitos.
- Parâmetros automáticos quando deixados em branco (GR limpo e argila pelos percentis 5/95,
  Rsh, método de φ, passo), sempre registrados como automáticos.
- Cada cálculo grava `execucoes/avaliacao_<poço>_<data-hora>.json` (arquivo de origem com
  SHA-256, curvas, métodos, parâmetros, resumo, fórmulas) e as curvas calculadas; histórico no
  painel; exportação CSV e LAS 2.0.
- Trilhas calculadas no gráfico (Vsh, φ, Sw e faixas de reservatório, net pay e QC).
- `docs/avaliacao.md`: fórmulas, estimativas automáticas e limites.

## [0.12.0] — 2026-10-16
### Adicionado
- **Levantamento do acervo** (aba Mapa): para uma bacia — inteira ou algumas categorias —
  classifica cada poço em *perfil digital*, *só imagem*, *sem perfil* ou *falta conferir*,
  **pelo conteúdo** dos arquivos e sem baixá-los: lista cada pasta "parte" numa requisição
  (WebDAV `Depth: infinity`) e lê só o primeiro 1 KB de cada arquivo ambíguo (HTTP `Range`).
  Roda em segundo plano, com progresso; cancelar guarda o que já foi lido e a próxima vez
  continua de onde parou. Ver `docs/levantamento.md`.
- Opção **Listar as curvas**: lê até 256 KB de cada DLIS/LIS e lista os canais com o `dlisio`
  (famílias GR, RHOB, NPHI, DT…), sem baixar o arquivo.
- Mapa: cor dos poços pelo levantamento, filtros **No acervo** e **Com a curva**; ficha do
  poço com os arquivos de perfil do portal e o formato real de cada um.
- **Exportar CSV** do levantamento (um por poço, um por arquivo), para tabelas do artigo.
- `ClienteREATE.listar_arvore` (listagem recursiva) e `ClienteREATE.ler_inicio` (começo do
  arquivo com `Range`; se o servidor ignorar, para nos N bytes e fecha a conexão).
### Corrigido
- **`.tif` do REATE é LIS, não imagem**: o reconhecimento de formato da 0.11.1 tratava o
  envelope de fita (*Tape Image Format*) como TIFF. Agora reconhece o envelope (e o LIS ou
  DLIS dentro dele) e o LIS sem envelope. Esses arquivos saem da aba Documentos e vão para
  Perfis — conferido com o leitor de LIS num arquivo de exemplo no mesmo formato (38 curvas).
### Documentação
- `docs/acervo-reate.md`: corrigida a conclusão de que a geração antiga seria "só imagem".

## [0.11.1] — 2026-10-16
### Corrigido
- **"Não está abrindo o TIF"**: o `5PX__0011__RN_5PX__0011__RN.tif` do 5-PX-11-RN não é
  imagem — é um **DLIS** com extensão `.tif` (recuperação digital da Petrobras de 2020).
  O SIAPP agora reconhece o formato **pelo conteúdo** (`motor/formatos.py`: TIFF, PDF, PNG,
  JPEG, DLIS e LAS pelos primeiros bytes; LIS pela extensão), e um arquivo assim vai para a
  aba **Perfis**, com o selo "conteúdo DLIS". Arquivos já registrados no banco têm o tipo
  corrigido ao abrir o projeto.
- Um arquivo que o leitor de imagens não reconhece dá uma mensagem clara (e a sugestão de
  "No computador") em vez de "erro inesperado".
- Quadros só com curva de enchimento (`DUMM`, 0–3 m) não contam mais para o intervalo de
  profundidade do arquivo.
### Documentação
- `docs/acervo-reate.md`: o `.tif` da geração antiga pode ser DLIS; a contagem de poços
  "só com imagem" precisa ser refeita pelo conteúdo.

## [0.11.0] — 2026-10-16
### Adicionado
- **Abrir qualquer arquivo baixado.** PDF, TIF e imagens (PNG, JPG) abrem na aba
  Documentos **sem processar antes**: dá para ler, folhear, ampliar e transcrever olhando
  a imagem. "Processar este documento" extrai o texto quando a pessoa quiser, e a página
  aberta mostra o texto assim que o processamento termina.
- **Visor ampliado** (botão Ampliar ou duplo clique na página): tela cheia, Ctrl + roda
  para zoom no ponto do cursor, arrastar para mover, ajuste à largura e 1:1, páginas
  anteriores e seguintes. A página chega em faixas, só as que aparecem na tela: um perfil
  escaneado em TIF de dezenas de metros de papel abre sem travar.
- Botões **Ver / Ver perfil / Abrir** nos arquivos baixados — na árvore do poço (Catálogo)
  e na ficha do poço (Mapa). Documentos e imagens abrem no SIAPP, DLIS/LIS/LAS na aba
  Perfis, e o resto (planilhas, texto, ZIP…) no programa do computador.
### Corrigido
- Destaque da busca em **TIF já processado** falhava ("is no PDF"): o PyMuPDF só desenha
  em PDF. O destaque agora é pintado na imagem.
- A imagem da página no painel tem limite de pixels: um TIF muito comprido não pesa mais
  na janela.

## [0.10.0] — 2026-10-16
### Adicionado
- **Transcrição assistida** na página do documento: desenhe uma caixa em volta do valor
  na imagem e o SIAPP sugere o que o OCR leu ali (ignorando o nome do poço, priorizando
  números com decimal). Você confere na imagem, completa e salva.
- Cada dado transcrito guarda **a fonte inteira**: documento (SHA-256 e caminho no
  REATE), página e a caixa desenhada. A caixa fica marcada na imagem para quem conferir
  depois — inclusive outras pessoas, quando o dado vem pela base comunitária.
- Tipos de dado: topo de formação, intervalo-alvo, profundidade final, revestimento
  (sapata), teste de formação, canhoneio, mesa rotativa, contato de fluido, observação.
  Validação de profundidade (faixa, base abaixo do topo, campos obrigatórios por tipo).
- Os dados transcritos aparecem na ficha do poço (Mapa), no gráfico de perfis e entram
  no pacote de contribuição.
- Documentação: `docs/comunidade.md`, `docs/perfis.md`, arquitetura e guia de teste
  atualizados para as versões 0.7 a 0.10.
### Corrigido
- Datas do pacote de contribuição com fuso horário (exigência do formato RFC 3339 do
  esquema do SIAPP-dados).

## [0.9.0] — 2026-10-16
### Adicionado
- Aba **Perfis**: lê **DLIS, LIS e LAS** (dlisio e lasio). Cada quadro com seu passo, a
  profundidade convertida para metros (inclusive o índice em décimos de polegada dos
  DLIS da Schlumberger), nulos `-999.25` tratados como falha.
- **Famílias de curvas** (`recursos/mnemonicos.json`, editável): GR, SP, cáliper,
  resistividades profunda/média/rasa, densidade, neutrão, fotoelétrico, sônicos.
  A "visão padrão" escolhe uma curva por família.
- **Gráfico em trilhas** com escalas convencionais (resistividade em log, neutrão
  invertido), rolagem, aproximação, leitura dos valores sob o mouse e marcação de
  intervalo arrastando o mouse.
- **Intervalo-alvo, topo de formação e contato de fluido** salvos como dados do poço,
  com o arquivo de origem; aparecem no gráfico, na ficha do poço e na exportação.
- **Exportação em LAS 2.0 e CSV**: curvas escolhidas numa grade comum, em metros, sem
  inventar dado em falhas do original. O cabeçalho leva poço, campo e cadastro ANP.
- O inventário vai para o banco (perfis e curvas): a ficha do poço mostra que curvas
  existem e em que intervalo. Se o nº de cadastro gravado no DLIS não bater com o poço
  da pasta, o SIAPP avisa.
### Conferido com dado real
- `1-AURI-12-RN_AIT_P.DLIS` (192 MB): 9 quadros, 354 curvas, 23,5 a 2.155,2 m, cadastro
  ANP 72100021414, ferramentas HAIT/HILTD/DSLT-H. `_P` é a passada principal.

## [0.8.0] — 2026-10-16
### Adicionado
- **Identificador único de poço**: `7GMR_0013__RN`, `7GMR13RN` e `7-GMR-13-RN` passam a ser
  o mesmo poço (nome ANP, Resolução 699/2017), inclusive poços no mar (`-RJS`) e com sufixo
  (`26D`, `59H`). Arquivos já baixados ganham o id canônico.
- **Cadastro da ANP**: a Tabela de Poços dos dados abertos (~30 mil poços) é baixada e
  importada para o banco — coordenadas, campo, operador, categoria, situação, datas,
  profundidades, mesa rotativa e o número de cadastro. Importação de arquivo se o
  download falhar. O nome do poço no operador vira apelido.
- **Catálogo do REATE no banco**: toda lista de poços vista no portal fica registrada
  (inclusive as listadas no 0.6); "Catalogar a bacia conectada" lista todas as categorias.
- Aba **Mapa** (Leaflet, mapa ou satélite): poços coloridos pelo que existe — só no
  cadastro, com pasta no REATE, com arquivos baixados, com dados transcritos. Filtros
  por bacia, nome/campo/operador, terra/mar e categoria.
- **Ficha do poço**: cadastro, pastas no REATE (com atalho para os arquivos no Catálogo),
  arquivos baixados, curvas disponíveis e dados transcritos, num lugar só.

## [0.7.0] — 2026-10-16
### Adicionado
- **Banco do projeto** (`projeto.sqlite`), com o mesmo modelo da base comunitária. Cada
  dado guarda sua origem: feito aqui (local), de um pacote importado ou da base.
- **Exportar contribuição**: pacote JSON (formato v2) com autoria, correções, palavras e
  dados transcritos. Nenhum arquivo do REATE vai junto: documentos são citados pelo
  SHA-256 e pelo caminho no portal.
- **Importar contribuição** com prévia: o que entra, o que já existe e as correções que
  discordam das suas (as suas continuam valendo). Cada pacote pode ser desfeito inteiro.
- **Base comunitária**: atualizar pelas Releases do SIAPP-dados ou a partir de um arquivo.
- Correções da comunidade aparecem em roxo; "o OCR estava certo" também as desfaz localmente.
- Aba **Início**: o que é cada pasta e sufixo do REATE, qual arquivo baixar para cada
  finalidade, limites do OCR e números do projeto.
- Aba **Comunidade**: autoria (nome, instituição, ORCID), exportar, importar, base.
- Registro de erros em `ambiente_teste/siapp.log` (com rotação), para relatar problemas.
- Arquivos baixados entram no banco com SHA-256 (inclusive os baixados no 0.6).
- Testes da interface num navegador sem tela, ligados à API Python de verdade.
### Mudado
- Código reorganizado: `ponte/` (uma parte da API da janela por área), `ui/js/`
  (um script por aba), `pyproject.toml` com versão e dependências num lugar só.
- Caminhos relativos sempre com "/": a pasta de projeto funciona em qualquer sistema.
  O índice de busca é refeito uma vez, automaticamente.
- O vocabulário do projeto sai de `texto/vocabulario_projeto.json` para o banco
  (migrado na primeira abertura; o JSON fica como cópia).

## [0.6.0] — 2026-10-15
### Adicionado
- Repositório organizado: licença AGPL-3.0, testes automáticos (Windows e Linux),
  modelos de issue e pull request, revisão obrigatória (CODEOWNERS), Dependabot,
  política de segurança e código de conduta.
- Dicionário de domínio (`recursos/vocabulario_base.json`): ~110 termos em 7 categorias
  (operações de poço, fluidos, rochas, medições, formações das bacias Potiguar e
  Sergipe-Alagoas, tipos de documento), exibidos como atalhos de busca com contagem de páginas.
- Busca tolerante a erros de OCR: cada termo também procura palavras com 1–2 letras
  diferentes; a interface mostra as variações usadas.
- Correção de texto pelo usuário: clicar numa palavra e corrigir vale para todos os
  documentos; palavras próprias entram no dicionário; tudo é reversível.
- Correção automática pelo dicionário, auditada em 55 páginas reais (33 correções, todas legítimas).
### Alterado
- Índice de busca guarda texto corrigido e original; é recriado automaticamente quando
  sua estrutura muda.
- Títulos de página com cara de ruído de OCR deixam de ser exibidos.
### Segurança
- Correções globais de números isolados são bloqueadas (trocariam valores certos em outras páginas).

## [0.5.0] — 2026-10-15
### Adicionado
- Aba **Documentos**: texto de PDFs e TIFs baixados — direto quando há texto embutido,
  OCR local quando a página é imagem (Tesseract embutido no PyMuPDF; modelo de português
  baixado na primeira vez).
- Limpeza da grade das tabelas antes do OCR.
- Índice de busca (SQLite FTS5) sem acento; página exibida com o termo destacado.
- Botão para abrir o arquivo no leitor do sistema.

## [0.4.0] — 2026-10-15
### Adicionado
- Download dos arquivos escolhidos em segundo plano, com barra de progresso e cancelamento.
- Retomada por `Range` HTTP após cancelamento, queda de conexão ou janela fechada.
- Registro de procedência de cada arquivo (`bruto/registro_downloads.json`).
### Alterado
- Nenhum arquivo vem pré-selecionado: cada tipo (passada principal, repetida, teste de
  formação) serve a uma finalidade diferente.

## [0.3.0] — 2026-10-15
### Adicionado
- Painel do poço: árvore de pastas e arquivos com tamanhos, antes de baixar.

## [0.2.0] — 2026-10-15
### Adicionado
- Pasta de projeto fixa (`ambiente_teste/`) com estrutura padronizada.
- Categorias divididas em subpastas "parte" passam a ser lidas como uma lista única.

## [0.1.0] — 2026-10-14
### Adicionado
- Primeira versão da nova arquitetura: janela HTML (pywebview) + motor Python.
- Catálogo em tempo real das 24 bacias terrestres do REATE.
- `iniciar.bat` que encontra um Python válido e cria ambiente isolado.

[Não lançado]: https://github.com/SIAPP-Pocos/siapp/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/SIAPP-Pocos/siapp/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/SIAPP-Pocos/siapp/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/SIAPP-Pocos/siapp/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/SIAPP-Pocos/siapp/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/SIAPP-Pocos/siapp/releases/tag/v0.6.0
