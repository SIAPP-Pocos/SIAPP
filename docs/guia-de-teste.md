# Guia de teste

Roteiro para validar o SIAPP no Windows, aba por aba. Marque o que funcionou; se algo
falhar, envie a mensagem da barra inferior **e** o arquivo `ambiente_teste\siapp.log`.

## Como rodar

1. Dê **dois cliques em `iniciar.bat`**. Na primeira vez (e quando a lista de dependências
   muda, como agora), ele instala o que falta no ambiente `.venv`: `dlisio` e `lasio` são
   novos na 0.9. Leva um ou dois minutos.
   *Se mover a pasta do SIAPP de lugar, apague a `.venv` — ela é recriada sozinha.*
2. A janela abre na aba **Início**. Clique em **Abrir o projeto** e confirme a pasta
   `ambiente_teste` (o diálogo já abre nela).

Alternativa pelo terminal: `.venv\Scripts\python.exe siapp.py --debug` (F12 abre o inspetor).

## 0.7 — banco do projeto e comunidade

Na primeira abertura, o SIAPP cria `ambiente_teste\projeto.sqlite`, registra os arquivos que
você já tinha baixado (com SHA-256) e refaz o índice de busca uma vez.

- [ ] **Início**: os números do projeto aparecem (3 arquivos baixados, 2 documentos com texto).
- [ ] **Documentos**: a busca continua achando `barreiras`, `cimento`, `calha`.
- [ ] Corrigir uma palavra (clique nela no texto da página) continua funcionando.
- [ ] **Comunidade**: preencher nome e instituição e **Salvar**.
- [ ] **Exportar pacote**: aparece `contribuicoes\AAAA-MM-DD_nobre_siapp.json`; **Abrir a pasta** abre o Explorer.
- [ ] Exportar de novo com "só o que é novo" marcado: avisa que não há nada novo.
- [ ] **Escolher pacote…** com o arquivo exportado: a prévia mostra autor, itens e o que você já tem.
- [ ] Depois de importar, o pacote aparece em "Pacotes importados"; **Desfazer** remove.
- [ ] **Atualizar pela internet**: enquanto o SIAPP-dados for privado, deve dizer que a base
      ainda não foi publicada (é o comportamento certo).
- [ ] `siapp.log` existe em `ambiente_teste`.

## 0.8 — poços, cadastro da ANP e mapa

- [ ] **Mapa** → **Baixar da ANP**: baixa a Tabela de Poços (~12 MB) e diz quantos poços importou.
      *É o primeiro contato do SIAPP com o site de dados abertos da ANP a partir do seu computador.*
      Se falhar, baixe o CSV pelo navegador em
      [dados abertos da ANP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/acervo-de-dados-tecnicos)
      e use **Importar CSV…**.
- [ ] O mapa mostra a bacia Potiguar; os poços que você já listou no Catálogo aparecem em verde-escuro,
      os com arquivos baixados em laranja (1-AURI-12-RN, 3-BRSA-1151-RN, 7-GMR-13-RN).
- [ ] O fundo do mapa carrega (precisa de internet); "Satélite" troca a imagem.
- [ ] Filtrar por nome (`GMR`), campo ou operador; terra/mar; categoria.
- [ ] Clicar num poço abre a **ficha**: cadastro (campo, operador, datas, profundidade, mesa rotativa,
      coordenadas, nº de cadastro), pastas no REATE, arquivos baixados.
- [ ] **Ver arquivos** na ficha leva à árvore do poço na aba Catálogo.
- [ ] Catálogo → conectar Potiguar → Mapa → **Catalogar a bacia conectada**: lista todas as categorias
      (leva alguns minutos na Potiguar: são mais de 7 mil poços só na categoria 7) e marca no mapa.

## 0.9 — perfis

- [ ] **Perfis**: aparece o `1-AURI-12-RN_AIT_P.DLIS`. Clicar: o SIAPP lê o arquivo (10–30 s na
      primeira vez) e mostra **354 curvas, 23,5 a 2.155,2 m**, cadastro ANP 72100021414.
- [ ] O gráfico mostra trilhas de GR/SP/cáliper, resistividades (escala log), densidade/neutrão,
      fotoelétrico e sônico.
- [ ] Roda do mouse rola; Ctrl + roda aproxima; "de/até" + **Ir** vai a um intervalo; **Tudo** volta.
- [ ] Passar o mouse mostra profundidade e valores.
- [ ] Marcar e desmarcar curvas na lista à esquerda muda o gráfico.
- [ ] Arrastar na vertical sobre o gráfico preenche topo e base; dar um nome e **Salvar** — a faixa
      amarela aparece no gráfico e o dado aparece na ficha do poço (Mapa).
- [ ] **LAS** e **CSV** gravam em `ambiente_teste\exportacoes\1-AURI-12-RN\`. Abrir o LAS num
      programa de perfis (ou no Bloco de Notas) e o CSV no Excel.
- [ ] Reabrir o arquivo é instantâneo (cache em `ambiente_teste\pocos\`).

## 0.10 — transcrição assistida

- [ ] **Documentos** → 7GMR_0013 → página 28 (teste de formação).
- [ ] Abrir **Transcrever um dado desta página**, escolher "Teste de formação".
- [ ] Desenhar uma caixa na imagem em volta de `INT.: 590,0-610.5`: o SIAPP mostra o que o OCR leu e
      sugere topo 590,0 e base 610.5 (campos em amarelo = sugestão).
- [ ] **Conferir os números na imagem**, dar um nome e **Salvar**: a caixa fica marcada na imagem
      com o rótulo, e o dado aparece na lista da página.
- [ ] O dado aparece na ficha do 7-GMR-13-RN (Mapa) e entra no próximo **Exportar pacote**.
- [ ] Tentar salvar topo de formação sem profundidade, ou base acima do topo: o SIAPP recusa e explica.

## 0.11 — abrir qualquer arquivo

- [ ] **Documentos**: um PDF ou TIF ainda não processado aparece como "sem texto — clique
      para ver". Clicar abre a página na hora, com o aviso amarelo e o botão
      **Processar este documento**.
- [ ] TIF de várias páginas: **‹ ›** passam as páginas.
- [ ] **Ampliar** (ou duplo clique na imagem): tela cheia. Ctrl + roda aproxima no ponto do
      mouse; arrastar move; **Largura** e **1:1**; **Esc** fecha.
- [ ] Com um perfil escaneado em TIF (pasta de perfis do poço): rolar até o fim no visor —
      as faixas vão aparecendo, sem travar a janela.
- [ ] **Processar este documento**: quando termina, o texto aparece na mesma página.
- [ ] Buscar `barreiras` e abrir o resultado de um TIF já processado: o destaque amarelo
      aparece (antes dava erro).
- [ ] **Catálogo** → abrir um poço: os arquivos baixados têm o botão **Ver** (PDF/TIF),
      **Ver perfil** (DLIS/LAS) ou **Abrir** (outros: abre no programa do Windows).
- [ ] **Mapa** → ficha do poço → **Arquivos baixados**: os mesmos botões.
- [ ] Transcrever num documento ainda não processado: desenhar a caixa avisa que não há
      texto; digitar os valores e salvar funciona.

## 0.12 — levantamento do acervo

Precisa de internet. Comece por uma categoria pequena para ver o tempo.

- [ ] **Mapa → Levantamento do acervo**: bacia **Potiguar**, **Escolher categorias…**, marcar só
      **Cat. 1**, **Levantar**. A barra mostra "1/2 · Listando…" e depois "2/2 · Conferindo
      arquivos pelo conteúdo".
- [ ] No fim: painel com a fração de poços com perfil digital, só imagem e sem perfil, e a
      tabela **O nome engana** (deve aparecer `.tif → LIS`).
- [ ] O mapa troca para **Cor dos poços: levantamento do acervo**; o filtro **No acervo: perfil
      digital** deixa só os verdes.
- [ ] Ficha de um poço levantado: seção **No acervo do REATE** com o formato real de cada arquivo
      (ex.: "LIS em fita" num `.tif`).
- [ ] **Cancelar** no meio e **Levantar** de novo: continua sem reler o que já foi lido.
- [ ] Com **Listar as curvas** marcado (mais lento): a ficha mostra "N curva(s)"; passando o
      mouse, a lista. O filtro **Com a curva: RHOB** funciona.
- [ ] **Exportar CSV** → **Abrir a pasta**: dois CSV que abrem no Excel (`;`).
- [ ] O `5PX__0011__RN_5PX__0011__RN.tif` continua na aba Perfis; um `.tif` LIS baixado também
      vai para Perfis (não para Documentos) e abre o gráfico.
- [ ] Para o artigo: levantar a bacia inteira (sem marcar categorias) e anotar o tempo.

## 0.13 — avaliação de formação

- [ ] **Perfis** → `1-AURI-12-RN_AIT_P.DLIS`. Marque um intervalo-alvo arrastando sobre o gráfico
      (ou digitando topo e base) e **Salvar**: ele aparece em **Avaliação de formação → Intervalos-alvo**.
- [ ] As curvas sugeridas: GR, RHOZ, NPHI, DT, AHT90 (Rt), HCAL, BS, HDRA. Troque uma e volte.
- [ ] Informe um **Rw** (o padrão 0,05 é só ponto de partida) e **Calcular**: tabela com bruto,
      reservatório, net pay, N/G, φ e Sw médios no pay, Vsh, HPV e QC.
- [ ] GR limpo e argila ficam como "auto: …" (estimados); "Estimado automaticamente" explica como.
- [ ] O gráfico ganha as trilhas VSH, PHI, SW e as faixas Reservatório / Net pay / Qualidade.
- [ ] Trocar para **Simandoux**: o Rsh é estimado e o Sw cai em trechos argilosos.
- [ ] Mudar um corte (ex.: φ ≥ 0,12) e calcular de novo: o net pay muda; as duas execuções
      aparecem em **Avaliações anteriores**, e clicar numa volta os parâmetros dela.
- [ ] `ambiente_teste\execucoes\avaliacao_1-AURI-12-RN_….json` tem os parâmetros e o resumo.
- [ ] **Exportar CSV** e **LAS**: arquivos em `exportacoes\1-AURI-12-RN\`.
- [ ] Sem intervalo marcado, **Calcular** explica que precisa de um intervalo-alvo.
- [ ] Repetir no `5PX__0011__RN_5PX__0011__RN.tif` (DLIS de 2020).

## 0.14 — AGP (dados gerais do poço)

- [ ] **Mapa → Levantamento do acervo**: Potiguar, **Escolher categorias…** → só **Cat. 1**,
      **Ler os AGPs** marcado, **Levantar**. A barra passa por 1/3, 2/3 e **3/3 · Lendo os AGPs**.
- [ ] No fim, o resumo mostra quantos AGPs existem, quantos foram lidos, quantos têm topos e
      quantos estavam na pasta de outro poço.
- [ ] Ficha do **1-FL-1-RN** (ou outro pioneiro): seção **AGP — dados gerais do poço** com
      mesa rotativa, tabela de unidades (Jandaíra, Açu, Embasamento…), corrida com Rm/Rmf em °F
      e **Abrir o AGP** abrindo o texto.
- [ ] Ficha do **3-AP-10-RN**: aviso de que o AGP da pasta é de outro poço.
- [ ] **Perfis** → um perfil de poço com AGP: linhas tracejadas verdes nos topos, nome da
      unidade no eixo, trilha **Litol. (AGP)** colorida; o mouse mostra a rocha.
- [ ] **Avaliação de formação**: "Do AGP" lista as formações e zonas (desmarcadas); marcar
      uma e **Calcular** funciona como um intervalo seu. A caixa cinza mostra Rm/Rmf/BHT.
- [ ] **Exportar CSV** do levantamento: aparece também `Potiguar_topos.csv`.
- [ ] Repetir o levantamento: os AGPs já lidos não são baixados de novo.
- [ ] Opcional (para o artigo): levantar a Potiguar inteira com AGP e anotar tempo e totais.

## O que continua valendo das versões anteriores

- Catálogo em tempo real das 24 bacias, junção das subpastas "parte", árvore do poço com tamanhos.
- Download retomável (cancelar no meio e pedir de novo continua de onde parou), registro de procedência.
- OCR de documentos escaneados, busca tolerante a erro de OCR, atalhos de palavras-chave.
- Correção global de número é recusada ("87" → "83" estragaria valores certos em outras páginas).
