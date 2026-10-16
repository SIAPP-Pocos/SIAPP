# Guia de teste

Arquitetura escolhida: **motor Python + interface HTML numa janela nativa (pywebview)**,
com uma **pasta de projeto** como contrato entre as partes. Mais tarde, o mesmo HTML
poderá abrir uma pasta de projeto direto no navegador, sem o motor.

## Como rodar

1. Dê **dois cliques em `iniciar.bat`**.
   Na primeira vez ele procura um Python válido (ignorando o do MySQL Shell), cria um
   ambiente isolado `.venv` dentro desta pasta e instala `pywebview` e `requests`.
   Leva um minuto; das próximas vezes abre direto.
   *Se mover a pasta `siapp.vf` de lugar, apague a `.venv` — ela é recriada sozinha.*
2. Na janela: **Escolher pasta**. O diálogo já abre na pasta `ambiente_teste`
   (dentro da `siapp.vf`); é só confirmar. **Por enquanto só essa pasta é aceita**:
   assim os dados ficam sempre ao lado do aplicativo e vão junto quando a pasta
   for compactada para outra pessoa.
3. Escolha a bacia (já vem **Sergipe**) → **Conectar**.
4. Clique numa categoria para listar os poços.
5. Clique num poço para ver, ao lado, todas as pastas e arquivos dele no portal,
   com tamanhos. Nenhum arquivo vem marcado: cada tipo serve a uma finalidade.
6. Marque os arquivos que quiser e clique em **Baixar selecionados**. O progresso
   aparece no rodapé; **Cancelar** interrompe e guarda o que já foi baixado.
7. Aba **Documentos**: lista os PDFs e TIFs baixados. **Processar pendentes** extrai o texto
   (direto, se o PDF tiver texto; por OCR, se for escaneado). Depois é só **buscar**: clicar
   num resultado mostra a página com o termo destacado.
8. **Palavras-chave**: atalhos de busca prontos (operações, fluidos, rochas, formações), com o
   número de páginas de cada um. A busca **tolera erros de OCR** e mostra as variações usadas.
9. **Corrigir o OCR**: no texto da página, clique numa palavra lida errado e digite a forma
   certa — vale para todos os documentos. Em verde, o que o dicionário corrigiu sozinho (clique
   e use "O OCR estava certo" se a correção estiver errada); em azul, o que você corrigiu.
   O OCR original nunca é apagado.

Alternativa pelo terminal: `python siapp.py` (ou `python siapp.py --debug`,
que habilita o inspetor do navegador com F12/botão direito).

## Passo 1 — o que validar

- [ ] A janela abre.
- [ ] O diálogo abre em `ambiente_teste` e, ao confirmar, cria `siapp.json` e as
      subpastas `catalogo`, `bruto`, `pocos`, `execucoes`.
- [ ] Escolher qualquer outra pasta (ou entrar numa subpasta) mostra o aviso de recusa.
- [ ] **Conectar** traz as categorias da bacia. *Esta é a primeira vez que o código novo
      fala com o REATE a partir do seu computador — é o teste mais importante.*
- [ ] Clicar numa categoria lista os poços e grava `catalogo\<Bacia>\<Categoria>.json`.
- [ ] Testar uma segunda bacia (ex.: Potiguar ou Alagoas).
- [ ] Fechar e reabrir escolhendo a mesma pasta: deve lembrar a última bacia.

## Passo 2 — o que validar

- [ ] Clicar num poço abre o painel lateral com a árvore de pastas e arquivos.
- [ ] Os tamanhos fazem sentido (compare um ou dois com o site do REATE).
- [ ] A pasta de perfis (`Perfis_digitais`, `Perfil Convencional`…) aparece com o selo **pasta de perfis**.
- [ ] Clicar em outro poço com o painel aberto troca o conteúdo; `Esc` ou `×` fecha.
- [ ] A árvore fica salva em `ambiente_teste\catalogo\<Bacia>\arvores\<poço>.json`.
- [ ] Testar poços de 2 ou 3 bacias diferentes: a estrutura de pastas muda entre elas?

## Passo 3 — o que validar

- [ ] Um DLIS marcado baixa e aparece em `ambiente_teste\bruto\<Bacia>\<poço>\<pasta do portal>\`.
- [ ] O arquivo baixado tem o mesmo tamanho mostrado no painel.
- [ ] Reabrir o poço mostra o arquivo com o selo **baixado** (caixa desativada).
- [ ] **Cancelar** no meio de um arquivo grande; depois pedir de novo: ele **continua** de onde
      parou (selo "parcial — retoma") em vez de começar do zero.
- [ ] Fechar a janela no meio de um download; reabrir e pedir de novo: também continua.
- [ ] `bruto\registro_downloads.json` lista cada arquivo com origem no portal e data.
- [ ] Baixar arquivos de 2 poços seguidos (o segundo entra na fila do primeiro).

## Passo 3c — o que validar

- [ ] Na primeira vez que houver documento escaneado, o rodapé mostra o download do idioma
      português do OCR (~15 MB) e o arquivo aparece em `recursos\tessdata\por.traineddata`.
- [ ] O PDF novo (CDPE) processa em segundos e aparece como "2 pág · 2 com texto".
- [ ] A pasta de poço antiga (7-GMR-13-RN, 55 pág.) processa em segundo plano, com
      "processando N/55" na lista e barra no rodapé. *Leva alguns minutos* (~4 s por página).
- [ ] Buscar `cimento`, `calha`, `completacao`, `pressao`: os resultados abrem a página certa,
      com o termo destacado em amarelo.
- [ ] O aviso "confira qualquer número na imagem" aparece nas páginas lidas por OCR.
- [ ] **Abrir arquivo** abre o PDF no leitor do computador.
- [ ] Comparar o texto reconhecido (em "Texto reconhecido nesta página") com a imagem:
      com o idioma português, os acentos devem sair (DESCRIÇÃO, COMPLETAÇÃO).

## Passo 3c+ — o que validar

- [ ] Os atalhos de palavras-chave aparecem com o número de páginas; clicar busca.
- [ ] Buscar `Barreiras` e `amostras contaminadas`: com "Tolerar erros de OCR" marcado, acha a
      pág. 1 e mostra as variações ("barigiras", "contlmindas"); desmarcado, não acha.
- [ ] No texto da pág. 1: BARREIRAS em verde. Clicar em `T-GRMAA3-RN`, corrigir para
      `7-GRM-13-RN` → aparece em azul e em "Correções" no painel da esquerda.
- [ ] Tentar corrigir um número (ex.: `87`): o SIAPP recusa e explica por quê.
- [ ] Adicionar uma palavra própria: ela vira atalho em "Minhas palavras".
- [ ] Desfazer uma correção pelo × do painel: o texto volta ao que o OCR leu.

Se algo falhar, envie a mensagem da barra inferior **e** o texto do terminal.

## Estrutura

```
siapp.vf/
├── iniciar.bat          atalho: instala dependências e abre a janela
├── siapp.py             janela + ponte JS ↔ Python (camada fina)
├── ambiente_teste/      PASTA DE PROJETO (dados) — fixa, ao lado do aplicativo
├── recursos/
│   ├── tessdata/        idioma português do OCR (baixado na 1ª vez)
│   └── vocabulario_base.json   dicionário de domínio (editável)
├── motor/               toda a lógica; não sabe nada de interface
│   ├── reate.py         cliente do portal REATE: listar, mapear poço, baixar
│   ├── downloads.py     fila de downloads em segundo plano
│   ├── documentos.py    texto de PDF/TIF (embutido ou OCR), índice de busca
│   ├── vocabulario.py   dicionário e correção do texto de OCR
│   └── projeto.py       pasta de projeto: siapp.json, catálogo, registro de downloads
└── ui/                  interface (HTML/CSS/JS puros, sem framework)
```

Pasta de projeto (`ambiente_teste/`):

```
ambiente_teste/
├── siapp.json                         configuração + histórico de cada ação
├── catalogo/<Bacia>/
│   ├── categorias.json
│   ├── <Categoria>.json               poços listados (nada baixado ainda)
│   └── arvores/<poço>.json            pastas e arquivos de cada poço explorado
├── bruto/                             arquivos baixados, intocados
│   ├── <Bacia>/<poço>/<pastas do portal>/<arquivo>
│   └── registro_downloads.json        de onde veio cada arquivo e quando
├── texto/                             texto extraído dos documentos
│   ├── <mesmo caminho de bruto>.json  texto + posição das palavras, por página
│   ├── resumo.json                    situação de cada documento
│   ├── vocabulario_projeto.json       suas palavras, correções e exceções
│   └── indice.sqlite                  índice de busca
├── pocos/                             (passo 5) curvas padronizadas
└── execucoes/                         (passo 7) processamentos + parâmetros
```

## Próximos passos (um de cada vez, validando entre eles)

1. ✅ Esqueleto + catálogo por categoria
2. ✅ Explorar um poço: árvore de arquivos e tamanhos
3. ✅ **Download selecionado**, retomável, com barra de progresso (este passo)
3b. ✅ Abrir os PDFs do poço (botão "Abrir arquivo" na aba Documentos)
3c. ✅ Texto dos documentos (embutido ou OCR) + busca
3c+. ✅ **Palavras-chave, busca tolerante a erro de OCR, correção pelo usuário** (este passo)
3d. Transcrição assistida de tabelas escaneadas (imagem ao lado do texto editável)
4. Cruzar com o cadastro de poços da ANP → **mapa** do catálogo
5. Conversão DLIS/LIS → Parquet padronizado
6. Visualizador de perfis + intervalo-alvo
7. Avaliação de formação, seção estratigráfica, bloco 3D
8. Empacotar em `.exe`

Documentação técnica: [arquitetura](arquitetura.md) · [acervo REATE](acervo-reate.md) · [documentos e OCR](ocr.md).

## Dependências e licenças

| Pacote | Para quê | Licença |
|---|---|---|
| pywebview | janela | BSD |
| requests | portal REATE | Apache 2.0 |
| PyMuPDF | PDF, imagem e OCR (motor Tesseract embutido) | **AGPL-3.0** — exige que o SIAPP seja distribuído com código aberto |
| numpy | limpeza da imagem antes do OCR | BSD |
| `por.traineddata` | modelo de português do Tesseract | Apache 2.0 |
