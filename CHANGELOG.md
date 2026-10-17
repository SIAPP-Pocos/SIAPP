# Histórico de versões

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versões seguem [Versionamento Semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x, a interface e os formatos de arquivo podem mudar.

## [Não lançado]

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
