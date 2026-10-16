# Histórico de versões

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versões seguem [Versionamento Semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x, a interface e os formatos de arquivo podem mudar.

## [Não lançado]

## [0.7.0] — 2026-10-16
### Mudado
- Código reorganizado: `ponte/` (uma parte da API da janela por área), `ui/js/`
  (um script por aba), `pyproject.toml` com versão e dependências num lugar só.
### Adicionado
- Registro de erros em `ambiente_teste/siapp.log` (com rotação), para relatar problemas.
- Testes da interface num navegador sem tela, ligados à API Python de verdade.

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

[Não lançado]: https://github.com/SIAPP-Pocos/siapp/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/SIAPP-Pocos/siapp/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/SIAPP-Pocos/siapp/releases/tag/v0.6.0
