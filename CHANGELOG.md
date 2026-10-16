# Histórico de versões

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versões seguem [Versionamento Semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x, a interface e os formatos de arquivo podem mudar.

## [Não lançado]

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
