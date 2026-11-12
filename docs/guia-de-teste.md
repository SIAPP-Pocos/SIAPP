# Guia de teste

Roteiro para validar o SIAPP no Windows, aba por aba. Marque o que funcionou; se algo
falhar, envie a mensagem da barra inferior **e** o arquivo `ambiente_teste\siapp.log`.

## Como rodar

1. Dê **dois cliques em `SIAPP.lnk`** (ou em `iniciar.bat`; sem janela de prompt desde a 0.47; para ver o console, use
   `SIAPP - diagnóstico.bat`). Na primeira vez (e quando a lista de dependências
   muda, como agora), ele instala o que falta no ambiente `.venv`: `dlisio` e `lasio` são
   novos na 0.9. Leva um ou dois minutos.
   *Se mover a pasta do SIAPP de lugar, apague a `.venv` — ela é recriada sozinha.*
2. A janela abre na aba **Projeto**. Clique em **Abrir o projeto** e confirme a pasta
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

## 0.59 — Modelo 3D em receita, OCR sem travar e pedidos pequenos

**Modelo 3D**
- [ ] A lateral mostra 1 Poços, 2 Método, 3 Unidades e grade, cada um com uma linha do que está escolhido e "Alterar".
      **Montar o bloco** fica no pé da lateral, sempre à vista.
- [ ] Mude o método ou o número de células: a linha do passo muda na hora.
- [ ] Monte um bloco: o botão vira **Montar de novo**. Sobre o visor: **Visualizar**, **Validar** (deixar um poço de fora,
      comparar métodos, prognóstico), **Mapa 2D** (abre o mapa sozinho) e **Exportar** (figura, PNG, CSV, SIG, .DATA).

**Janela e barras**
- [ ] Arraste a borda direita de qualquer barra lateral: ela alarga. Feche e abra o SIAPP: a largura continua. Dois cliques
      na borda: volta ao padrão.
- [ ] Feche o SIAPP com a janela dividida e abra de novo: abre no arranjo padrão (Configurações › "Lembrar o arranjo" liga
      de volta).

**OCR**
- [ ] **Documentos › Processar pendentes** num PDF escaneado de muitas páginas. Enquanto roda, troque de aba, abra a ficha
      de um poço, role a lista: a janela responde (antes: "Não respondendo").
- [ ] **Cancelar** no rodapé: para na hora. No Gerenciador de Tarefas, um segundo "Python" aparece durante o OCR e some
      quando a fila termina.
- [ ] Com o levantamento rodando, o mapa e a ficha abrem sem esperar. Abrir o projeto fica mais rápido da segunda vez.

**Pedidos pequenos**
- [ ] Documentos: um PDF com marcadores mostra **Sumário (n)** ao lado das setas; escolher uma seção pula para a página.
- [ ] Documentos: filtre por um poço e use **Reler os N do filtro**.
- [ ] Documentos: numa página que você editou à mão, a legenda explica "texto revisado" e o texto tem uma barra ao lado.
- [ ] Perfis: digite `gmr13` no filtro: só os arquivos desse poço ficam na lista.
- [ ] Poços: destaque dois poços e clique **Só os destacados**: os outros somem; **Mostrar todos** volta.
- [ ] Acervo › Buscar por tipo: preencha um campo e clique **Todos os tipos** › Procurar: aparecem todos os poços do campo
      com algum dado.
- [ ] Acervo › Produção da ANP: passe o mouse em "óleo in place" e "produzido até".

## 0.58 — projetos, módulos no Início e o atalho que se atualiza

Esta é a última vez que você precisa do `git pull`: a partir dela, o atalho traz cada versão nova.

- [ ] Abra pelo **atalho**. A janelinha mostra "Procurando versão nova"; o SIAPP abre normalmente.
- [ ] **Início**: o cartão "Projeto principal" aparece marcado "aberto", com as bacias, os números e o minimapa dos poços.
- [ ] **Módulos**: cada um diz o que tem (ex.: Documentos com "N sem texto"); o botão leva à aba certa.
- [ ] **Novo projeto**: nome "Teste" e uma bacia. Crie e escolha **Abrir este projeto**: o SIAPP fecha e abre de novo já em
      "Teste" (vazio). Feche e abra pelo atalho: abre em "Teste".
- [ ] No Início, clique no cartão "Projeto principal": volta para os seus dados de sempre.
- [ ] **renomear** (passe o mouse no cartão) muda o nome, não a pasta.
- [ ] Com um download em andamento, tente trocar de projeto: aparece o aviso para esperar.
- [ ] **Ajuda › Novidades desta versão** mostra a 0.58 e a 0.57.
- [ ] **Configurações › Diagnóstico**: aparecem "Atalho: atualização: …" e, se o SIAPP estiver fixado na barra de tarefas,
      "Botão fixado na barra de tarefas". Se disser que falta a identidade, clique **Corrigir o botão fixado**. Depois rode a
      sua automação em Python de novo: o prompt dela não deve mais aparecer no ícone do SIAPP. Se ainda aparecer, desafixe o
      SIAPP e fixe de novo o `SIAPP.lnk` da pasta.
- [ ] O log não mostra mais "leitura dos dados do poço na abertura falhou … 136.0000 DEGF".
- [ ] Quando eu publicar a próxima versão: abra pelo atalho e veja "SIAPP atualizado: 0.58.0 → 0.59.0".

## 0.57 — interface pelo fluxo, busca de poço, atalhos e avisos

- [ ] A barra do alto, na janela padrão, fica **numa linha só**: pasta do projeto, Início, 1 Acervo … 6 Modelo 3D, Mais, lupa, ⋯,
      pasta, ?, engrenagem.
- [ ] **Abra o SIAPP com a última aba sendo Documentos** (ou Perfis): ao terminar de abrir o projeto, a lista aparece sozinha,
      sem trocar de aba (era o erro "só atualiza se eu trocar de uma para outra").
- [ ] **5 Correlação** e **6 Modelo 3D** abrem cada um a sua tela; só a aba clicada fica marcada.
- [ ] **Mais ▾** › Viabilidade: a aba "Mais" passa a dizer "Viabilidade".
- [ ] **1 Acervo**: subabas no topo. "Mais ▾" › Cadastro da ANP: a lateral some e o cartão ocupa a largura toda.
- [ ] **Ctrl+K**, digite `7-GMR-0013` (ou `gmr13`): aparece 7-GMR-13-RN; Enter abre a ficha no mapa.
- [ ] **Ctrl+3** vai a Perfis, **Ctrl+0** ao Início, **Ctrl+Enter** em Acervo › Catálogo conecta à bacia.
- [ ] **Ajuda › Atalhos de teclado**: mude "3 · Perfis" para outra tecla e use; dê a uma ação a tecla de outra (as duas trocam);
      **Restaurar os padrões**.
- [ ] **Documentos › Processar pendentes**: aparece "Antes de ler documentos escaneados". **Cancelar** não processa. De novo,
      marque **Não mostrar de novo** e **Entendi**: processa, e não aparece mais (nem depois de fechar e abrir o SIAPP).
- [ ] O mesmo em **Perfis › Calcular** e **Modelo 3D › Montar o bloco**.
- [ ] **Ajuda › Guia do REATE** e **Limites e confiabilidade** abrem numa janela; **Esc** fecha. **Sobre** mostra a versão 0.57.0.
- [ ] Um **?** ao lado de "Pastas do REATE" (Acervo › Catálogo) mostra e esconde a explicação.
- [ ] Um erro qualquer (ex.: Conectar sem internet) aparece também no **canto superior direito** e some sozinho.
- [ ] **Correlação**: "Achar poços ao longo de uma linha", "Desenho" e "Seções anteriores" vêm fechados; **Montar a seção** fica
      no pé da lateral mesmo rolando.
- [ ] **⋯ › Dividir a janela** e **⋯ › Abrir em janela** funcionam como antes.

## 0.56 — várias bacias no bloco 3D e tabela com nomes à mão

- [ ] **Bloco 3D › Poços › "todos os poços da bacia"**: aparecem **caixas de marcação**, uma por bacia, com o número de poços.
- [ ] Sem marcar nada, **Selecionar** avisa "Marque ao menos uma bacia."
- [ ] Marque **Alagoas e Sergipe** juntas: a contagem de poços selecionados é a soma das duas e o bloco monta com poços das duas.
- [ ] **Zonas produtoras › importar tabela**: use `guamare_modelo\dados\pocos_estrutural.csv` (cabeçalho `ID_well`, nomes como
      `7-GMR-8-1`). A tela deve dizer que achou **26 poços** (sem aviso de "não reconheceu") e a coluna `formação` vira o reservatório.
- [ ] **Mapa 2D com curvas de nível** (quadro novo, abaixo da validação): abra com um bloco montado. Aparece o mapa do primeiro
      topo, com cores, curvas rotuladas, poços brancos e eixos em metros.
- [ ] Troque o **mapa** (topo, base, espessura, terreno), o **intervalo das curvas** (ex.: 15), a **paleta** e **inverter as cores**:
      o desenho muda na hora. Marcado "profundidade" + "inverter as cores" + viridis dá o estilo do seu modelo à mão.
- [ ] Marque **contada da mesa rotativa**: o mapa 2A do Guamaré deve ir de ~572 a ~688 m, como o seu modelo à mão.
- [ ] Desligue **poços**, **cores de fundo** e **curvas**; ligue **nomes dos poços**. Rotular "2" mostra um rótulo a cada duas curvas.
- [ ] **Salvar SVG, PNG e PDF**: os três arquivos saem em `exportacoes/blocos/` e abrem certo.
- [ ] Com o bloco de zonas do Guamaré (tabela importada), compare o mapa do topo do reservatório 2A com a figura do seu modelo.
- [ ] Na linha `7-GMR-18-9` a coluna `formação` está vazia (o `O` do fluido ficou no lugar): corrija no CSV antes de importar.

## 0.55 — zonas produtoras (net pay) no bloco 3D

Use o **1-BRSA-1304-BA** (tem canhoneado, teste e análise de perfis lidos) e, para o Guamaré, os poços que você baixar.

- [ ] **Bloco 3D › Unidades › zonas produtoras (net pay)**: aparece o passo 3b com as fontes, a regra e a tolerância.
- [ ] Escolha 3 ou mais poços e **Ler os intervalos dos poços**: a tela mostra os **reservatórios** e todos os **intervalos candidatos**
      (fonte, topo, base, leitura digital ou **OCR: conferir**, reservatório, usado).
- [ ] Confira **2 ou 3 intervalos na imagem do documento** (a coluna Leitura mostra o documento e a página ao passar o mouse). Anote
      quantos números do OCR estavam errados: é o argumento para revisar as profundidades.
- [ ] **Corrija um número** na tabela (topo ou base) e veja o intervalo ficar "(editado)"; **mova** um intervalo para outro
      reservatório; **ignore** outro.
- [ ] **Importe a sua tabela** do Guamaré (poço, topo, base e coordenadas; informe a zona UTM, 24, se for UTM): a seção
      **Sua tabela × o que o SIAPP escolheu** mostra as diferenças poço a poço.
- [ ] Marque a tabela como fonte (e "usar as coordenadas da minha tabela") e **monte só o reservatório raso**: o mapa de topo e o de base
      devem parecer com os que você fez em Python. Compare os valores nos poços.
- [ ] Monte o **reservatório fundo** à parte e o **bloco com os dois**. Confira o aviso de "pouco controle" no fundo.
- [ ] Exporte os mapas (topo, base e isópaca) e o CSV de zonas; abra o `_zonas.csv` no Excel.

## 0.54 — Arquivos baixados

- [ ] **Dados › Arquivos baixados**: a árvore mostra as bacias (Alagoas, Potiguar, Recôncavo, Sergipe) com a quantidade e o tamanho;
      clique numa bacia, depois num poço e numa pasta: a lista à direita mostra só aquilo.
- [ ] A lista traz **todos** os formatos (planilhas, SEG-Y, ZIP, textos), com a situação e **onde o dado aparece**. Confira o
      1-ALG-1-RN: as planilhas de petrofísica aparecem como "lido" com "Ficha do poço › Petrofísica de testemunho".
- [ ] Os `_agp.txt` e `_dados_direcionais.txt` aparecem como lidos pelo levantamento (não como "sem leitor").
- [ ] **Busca** (ex.: `coregama`) e os filtros **Tipo**, **Lido?** e **Bacia** funcionam; "Limpar filtros" volta ao todo.
- [ ] **Abrir** num PDF e numa planilha abre no programa padrão. **Mostrar na pasta** abre o Explorer **com o arquivo selecionado**.
- [ ] **Ver na ficha** abre a ficha do poço no Mapa.
- [ ] **Apagar** (use um arquivo de teste que você possa baixar de novo): a confirmação mostra o que sai e o que fica; **Cancelar** não faz
      nada; **Mandar para a Lixeira** tira da lista e o arquivo está na **Lixeira do Windows** (dá para restaurar). Se o arquivo tinha
      dados na ficha, eles somem da ficha.
- [ ] Digite na busca e, em seguida, clique num botão da lista: o primeiro clique funciona.

## 0.53.1 — atalho e janela são o mesmo botão na barra de tarefas

- [ ] **Desafixe** o SIAPP da barra de tarefas (botão direito › Desafixar da barra de tarefas), se estiver fixado.
- [ ] Abra o SIAPP pelo `SIAPP.lnk` (ele é refeito na primeira abertura; a janelinha e a janela principal devem aparecer sob
      **um** botão chamado **SIAPP**, com o ícone do SIAPP, e **não** "Python").
- [ ] Passe o mouse no botão: o nome é SIAPP. Botão direito no botão › **Fixar na barra de tarefas**.
- [ ] Feche o SIAPP: o botão fixado continua, com o ícone do SIAPP. Clique nele: o SIAPP abre (janelinha e janela) **e o botão
      fixado vira o botão da janela aberta** (fica destacado), sem um segundo botão "Python" ao lado.
- [ ] Abra uma aba em janela própria: ela fica no mesmo grupo SIAPP.
- [ ] Se aparecer um segundo botão, anote: o nome, o ícone e se ele surge só durante a janelinha.

## 0.53 — segunda leitura (OCR) das páginas ruins

- [ ] Em **Documentos**, a caixa **Segunda leitura das páginas ruins (mais lento)** aparece ligada.
- [ ] Escolha um PDF escaneado (ex.: a pasta de poço do 3-FGT-4-AL) e **Processar este documento**: leva mais tempo que
      antes nas páginas ruins, mas termina.
- [ ] Compare o texto de uma página ruim com a imagem: deve estar melhor ou igual ao de antes (números continuam a conferir
      na imagem).
- [ ] Desligue a caixa e processe outro documento: volta a ser rápido (só a primeira leitura).

## 0.52 — viabilidade: diâmetro, inflação e restrições ambientais

Use um campo com produção, camadas e distâncias já medidas (Viabilidade › Medir as distâncias).

- [ ] **Diâmetro pela vazão**: abra "Diâmetro pela vazão e correção pela inflação", escolha *calculado pela vazão*, informe
      vazão (ex.: 2.000.000 m³/d), pressão e temperatura do duto e calcule: o resumo mostra o diâmetro "(pela vazão)" e a
      memória traz os passos (vazão no duto, diâmetro em m e em pol). Troque para *tamanho comercial*: o diâmetro sobe para
      o próximo tamanho e a memória diz isso. Sem vazão/pressão/temperatura, a mensagem diz o que falta.
- [ ] **Inflação**: escolha IPCA e calcule: o resumo diz "corrigido pelo IPCA de 2024-06 a 20xx-xx (×1,xxxx)". Compare com
      INCC-M. Confira com o IPCA acumulado do IBGE no período (deve bater). Em `ambiente_teste\indices\` ficam as séries.
- [ ] Desligue a internet e repita: usa a cópia guardada e avisa.
- [ ] **UCs**: em Dados › Camadas geográficas, marque "Unidades de Conservação federais (ICMBio)" e baixe (demora).
- [ ] **Terras indígenas**: baixe o shapefile no site da FUNAI e use "Importar terras indígenas…".
- [ ] Na Viabilidade, **Restrições ambientais no traçado**: lista as áreas atravessadas pela linha reta até cada
      infraestrutura. Confira uma no mapa/QGIS.
- [ ] **API e densidade de Guamaré**: Dados › Procurar por tipo de dado › campo Guamaré › marque *Pasta de poço* (e *PVT*) ›
      procure › marque os poços › baixe; depois confirme os valores achados em Viabilidade › fluidos do campo.

## 0.51 — download em lote por seção, campo e mapa

- [ ] **Campo**: em Dados › Procurar por tipo de dado, digite um campo (ex.: Guamaré) em "Só os poços do campo": os
      números dos tipos mudam para só os poços do campo. Procure petrofísica básica e confira.
- [ ] **Seção**: monte uma seção com 3 ou 4 poços e clique em **Dados destes poços**: abre a busca com a etiqueta
      "Só os N poço(s) da seção"; **×** na etiqueta volta a mostrar todos.
- [ ] **Mapa**: destaque 2 ou 3 poços e clique em **Dados destes poços** (painel de destaques).
- [ ] Marque um poço do resultado e **Baixar os arquivos dos marcados**: confirma com o total e baixa só os arquivos do tipo.

## 0.50 — testemunho × perfil

Use o 1-ALG-1-RN (1 plug a 2.021,1 m; gama do testemunho de 2.016 a 2.026,8 m).

- [ ] Abra o perfil do 1-ALG-1-RN, marque o intervalo do testemunho (2.016–2.027 m) e **calcule a avaliação**.
- [ ] Abaixo do resultado aparece **Comparação com o testemunho**: 1 plug, φ do plug 20,6 %, φ do perfil e a
      diferença em pontos percentuais.
- [ ] Se o perfil de GR do arquivo cobre o testemunho, aparece o **deslocamento pelo gama**, com a correlação. Confira no
      gráfico se faz sentido (picos de gama do testemunho e do perfil alinham com o deslocamento sugerido). Se vier
      "pouco confiável", o motivo aparece.
- [ ] Um poço sem plugs lidos **não** mostra o bloco (sem mensagem de erro).

## 0.49 — procurar por tipo de dado

Precisa do levantamento do acervo já feito (o seu tem 9.447 poços: Potiguar e Alagoas).

- [ ] **Dados › Procurar por tipo de dado**: a lista de tipos aparece com poços, arquivos e tamanho de cada um
      (ex.: petrofísica básica ≈ 161 poços, PVT ≈ 13, sísmica de poço ≈ 104). **Nenhum tipo vem marcado.**
- [ ] Marque **Petrofísica básica** e clique **Procurar**: lista ≈ 161 poços; **nenhum poço vem marcado**.
- [ ] Marque também **PVT** com "todos os tipos marcados": sobra(m) só o(s) poço(s) com os dois (ex.: 1-BRSA-1034-RN).
      Troque para "pelo menos um": a lista cresce.
- [ ] Troque a bacia para **Alagoas**: os números mudam (petrofísica básica ≈ 11 poços).
- [ ] Marque 2 poços, **Ver os marcados no mapa**: eles ficam destacados no mapa.
- [ ] **Exportar a busca (CSV)**: abre no Excel, um arquivo do portal por linha, em
      `ambiente_teste\exportacoes\tipos_de_dado\`.
- [ ] Marque 1 poço com petrofísica (ex.: 1-ALG-1-RN) e **Baixar os arquivos dos marcados**: mostra o total e pede
      confirmação; **Cancelar** não baixa nada. Confirmando, só os arquivos de PETROFISICA entram na fila e caem em
      `bruto\…\Dados de Rochas e Fluidos\PETROFISICA…`.
- [ ] Depois de baixar, a ficha do poço mostra os blocos de petrofísica (0.48/0.48.1).
- [ ] **Abra um poço de outra grafia da pasta** (ex.: 1-BRSA-1006-RN ou 7-ET-854-RN, pasta `PETROFISICABASICA`/
      `Petrofisica_basica`): confira se as planilhas abrem; se alguma não abrir, mande-a.

## 0.48 — petrofísica básica de testemunho

Use o poço **1-ALG-1-RN** (já baixado: pasta Dados de Rochas e Fluidos › PETROFISICA_BASICA).

- [ ] Abra o projeto; a leitura dos documentos novos roda sozinha. Em **Dados › Dados consolidados**, o tema
      **Petrofísica de testemunho** aparece com as duas fontes e a contagem de itens.
- [ ] Abra a **ficha do 1-ALG-1-RN**: bloco **"Petrofísica de testemunho — plugs"** com 1 plug a 2.021,10 m
      (porosidade 20,6 %, permeabilidade 206,39 mD, densidade 2,65, pressão 2.330 psi, amostra "1 VH1", tipo Plug).
      Os dois arquivos de plugs (`…Petrofisica Basica.xls` e `00610.119452.xls`) aparecem **uma vez**, com a outra
      planilha em "também em".
- [ ] Bloco **"Gama do testemunho (COREGAMA)"**: 55 pontos, de 2.016,00 a 2.026,80 m, gama entre 4,6 e 25,1 API.
- [ ] O aviso da densidade (a planilha não diz a unidade) aparece na ficha.
- [ ] Os valores com vírgula (206,39) saem certos, sem virar 20639 nem erro.
- [ ] Baixe outro poço com `PETROFISICA_BASICA` (162 têm) e confira se abre; se alguma planilha não abrir, mande-a.

## 0.47 — abrir como um programa, sem janela de prompt

Antes: renomeie a pasta do SIAPP para **`SIAPP`** no Explorer (era `siapp.vf`). A `.venv` antiga deixa de funcionar
e o atalho antigo aponta para o caminho velho — os dois são refeitos sozinhos.

- [ ] Dois cliques em **`SIAPP.vbs`** (ou em `iniciar.bat`): **nenhum console** aparece, nem na tela nem na barra de
      tarefas. Surge uma janelinha com o ícone, **SIAPP**, a versão (0.47.0) e uma barra de progresso.
- [ ] Na primeira abertura depois de renomear a pasta, a janelinha mostra "Refazendo os componentes — leva alguns
      minutos" e, depois, "Preparando os componentes". Sem nenhuma janela preta.
- [ ] A janelinha mostra "Conferindo os arquivos", "Preparando os componentes", "Abrindo o projeto" e **some quando
      a janela principal aparece**.
- [ ] Nas aberturas seguintes (nada novo para instalar) o carregamento é rápido.
- [ ] Na barra de tarefas, janelinha e janela principal têm o **mesmo ícone** e ficam no mesmo botão (sem duplicar).
- [ ] Depois da primeira abertura, **`SIAPP.lnk`** é recriado apontando para esta pasta (botão direito ›
      Propriedades: destino `wscript.exe //nologo "…\SIAPP.vbs"`). Dois cliques nele abrem o SIAPP sem console.
      Fixar na barra de tarefas e no Iniciar continua funcionando.
- [ ] **Erro claro**: renomeie `requirements.txt` para `requirements.txt.bak` e abra: a janelinha diz que faltam
      arquivos, com **Copiar detalhes** (cole num bloco de notas para conferir) e **Fechar**; nenhum console pisca.
      Desfaça o nome depois. O detalhe também fica em `ambiente_teste\lancador.log`.
- [ ] **`SIAPP - diagnóstico.bat`** abre o console com cada passo (o que o `iniciar.bat` fazia antes).
- [ ] Se algum antivírus reclamar do `SIAPP.vbs`, anote qual e a mensagem.

## 0.46 — ícone do SIAPP

- [ ] A janela abre com o ícone novo na **barra de título** (canto superior esquerdo) e na **barra de tarefas**,
      não mais o do Python. Passe o mouse e confira que o SIAPP aparece separado de outros programas em Python.
- [ ] **Alt+Tab** mostra o ícone novo.
- [ ] Abra uma aba em janela própria (ex.: Mapa › abrir em janela): a janela nova também tem o ícone.
- [ ] No topo do SIAPP, o ícone aparece à esquerda do nome, alinhado.
- [ ] Depois da primeira abertura aparece **`SIAPP.lnk`** na pasta do SIAPP, com o ícone. Dois cliques nele abrem o
      SIAPP; botão direito › *Fixar em Iniciar* / *Fixar na barra de tarefas* também funciona. Pode copiá-lo para a
      Área de Trabalho.

## 0.45 — topos de várias fontes

- [ ] Ficha do **1-BRSA-1304-BA** › "Topos de formação — compare as fontes e escolha": colunas RFP e Calha (PAG), 10
      unidades; Pojuca em vermelho (453 × 459 m); o RFP em negrito (vale pela ordem do projeto).
- [ ] Mude Pojuca para "Calha (PAG)": o negrito passa para 459. Volte para "padrão".
- [ ] Num poço com AGP, transcreva um topo de uma formação do AGP com outra profundidade: as duas colunas aparecem, com
      a diferença; o AGP continua valendo até você escolher o transcrito.
- [ ] Interpretação › Seção: o 1-BRSA-1304-BA aparece entre os poços com topos (antes ficava de fora por não ter
      AGP). Com outro poço do Recôncavo que tenha topos (AGP ou transcritos), monte a seção: a coluna "fonte" do 1304
      mostra RFP.
- [ ] Dados › Dados consolidados › "Topos: qual fonte vale quando você não escolhe": suba a Calha para o primeiro lugar
      e salve; a ficha do 1304 passa a usar a calha nas unidades sem escolha.

## 0.44 — dados consolidados

- [ ] Dados › Dados consolidados: a tabela "No projeto" lista os 13 temas; confira alguns números (ex.: "AGP da
      ANP" com os poços de AGP lidos; "RFP (topos constatados)" com os 3 poços de formulários do `ambiente_teste`).
- [ ] A coluna "Onde é usado" bate com o que você vê no SIAPP? (ex.: a seção só com os topos do AGP.)
- [ ] Digite **1-FPA-1-BA** e "Ver o poço": abre o 1-BRSA-1304-BA, com RFP, calha, TFR, teste a cabo, PVT,
      checkshot e geoquímica nos temas certos.
- [ ] Na ficha de qualquer poço, o botão "Dados consolidados" leva direto ao poço nessa tela.

## 0.43 — geoquímica e apelidos

- [ ] Ficha do **1-BRSA-1304-BA** › "Geoquímica — isótopos de carbono do gás": 1.680–1.684 m, gás, δ¹³C
      **−47,39 / −31,61 / −27,38 ‰**, "gás termogênico; ordem normal". Na lista de documentos, a planilha traz o
      aviso do sinal duplo (`=--47.39`); confira na nota técnica (PDF da mesma pasta).
- [ ] "Também escrito como": **1-FPA-1-BA**, com a origem (o primeiro documento que gravou; 1FPA1BA e
      1-FPA-0001-BA são a mesma grafia para o SIAPP). Em Mapa › Destacar poços, 1-FPA-0001-BA cai no 1-BRSA-1304-BA.

## 0.42 — sísmica de poço (checkshot)

- [ ] Ficha do **1-BRSA-1304-BA** › "Sísmica de poço — tempo × profundidade (checkshot)": 23 níveis, de 90,6 a
      1.944 m; na última linha TWT **1.276,9 ms**, Vméd **3.032 m/s**, Vint **4.263 m/s**. Confira com a tabela
      "FULL PROFILE DATA" do relatório (`1-brsa-1304-ba_asr-3_field_report.pdf`, págs. 24 e 25).
- [ ] Os dois gráficos (TWT e velocidade intervalar × profundidade) descem com a profundidade.
- [ ] "Exportar a tabela (CSV)": o arquivo `exportacoes\1-BRSA-1304-BA\checkshot_tempo_profundidade.csv` abre no
      Excel com MD, TVD, TVDSD, Tcorr, TWT, Vméd, Vint.
- [ ] Perfis › um perfil do 1-BRSA-1304-BA: o mouse a 1.680 m mostra "TWT ≈ 1.148 ms".
- [ ] Na lista de documentos da ficha, o `_raw.sgy` aparece como "registro de campo (tiro a tiro)".

## 0.41 — perfis já processados pela operadora

- [ ] Abra o projeto (as famílias do levantamento são refeitas nessa abertura). Dados › Levantamento › Potiguar:
      a seção "Perfis já processados pela operadora" diz quantos poços têm Vsh/φ/Sw; "Listar os poços" mostra, entre
      outros, **1-BRSA-1348-RN** (PHIE, SW, VSH no `1-brsa-1348-rn_adic.las`).
- [ ] Mapa › Com a curva › "interpretação da operadora": só esses poços ficam no mapa.
- [ ] Baixe o 1-BRSA-1348-RN (o `_conv.las` e o `_adic.las`). Perfis › abra o `_adic.las` (PHIE, SW e VSH aparecem
      como "interpretação"); depois o `_conv.las` › Avaliação › marque um intervalo e calcule: abaixo do resultado
      aparece "Comparação com a interpretação da operadora", com as médias das duas.
- [ ] Mude o Rw e recalcule: a coluna do SIAPP muda, a da operadora não; diferença grande fica em vermelho.

## 0.40 — PAG (curvas de lama e gás, descrição de calha)

- [ ] Abra o SIAPP pelo `iniciar.bat` (ele instala `xlrd` e `openpyxl`). Confira na ficha do **1-BRSA-1304-BA**
      que a "Análise PVT" aparece (se não aparecia na 0.39, era a falta dessas bibliotecas).
- [ ] Ficha › "Topos pela descrição de calha (PAG)": Sao Sebastiao 9 m, Pojuca 459, Marfim 1.134, Maracangalha
      1.257, Candeias 1.527, Agua Grande 1.680, Itaparica 1.695, Sergi 1.704, Alianca 1.815, Embasamento 1.905,
      cada um com o topo do RFP ao lado (453, 1.132, 1.255…).
- [ ] Ficha › "Topos estratigráficos" (RFP): os topos sem nome mostram "≈ Pojuca (calha, 459 m)" etc.
- [ ] "Gás na lama (PAG)": 9 zonas, entre elas 1.683–1.694 m (8,5 × o fundo) e 874–882 m (50 × o fundo);
      "sem cromatografia". "Fluorescência e corte na calha": amostras da Água Grande com EP 20 %.
- [ ] "Salinidade da lama": 7 leituras (148.000 ppm a 530 m … 211.000 ppm), com o Rw de NaCl.
- [ ] Perfis › `1-BRSA-1304-BA_PAG_curvas.las`: HYDC aparece como gás total, DENS como peso da lama (não como
      densidade), ROP como taxa de penetração.
- [ ] Perfis › um perfil do 1-BRSA-1304-BA (sem AGP lido no projeto): a trilha "Litol. (calha)" aparece com a legenda;
      o mouse mostra a rocha e a formação.
- [ ] Avaliação: os intervalos "Gás na lama · …" (origem PAG) aparecem com os dos formulários; a nota do Rw traz
      a salinidade da lama.

## 0.39 — análise PVT

- [ ] Abra o projeto `ambiente_teste` e a ficha do **1-BRSA-1304-BA** › "Análise PVT — liberação diferencial
      (1.680–1.684 m)". Esperado: saturação **155,4 kgf/cm²** (152,4 bar), **Bo 1,4013**, **Rs 125,37 m³/m³**, µo
      0,79 cP; tanque 38,59 °API, RGO 117,83; três gráficos com a linha tracejada na saturação; 13 estágios.
      Confira contra a planilha.
- [ ] "Composição do fluido — liberação flash": 24 componentes, de N₂ a C20; C1 = 36,03 % no fluido do reservatório.
- [ ] Viabilidade › um campo que tenha um poço com PVT baixado (o 1-BRSA-1304-BA é exploratório: só vale se o
      cadastro da ANP o ligar a um campo): a nota dos fluidos diz "Análise PVT de laboratório…", o grau API vem
      "(PVT)", e na memória de cálculo Bo e Rs aparecem como "medido: PVT do poço…".
- [ ] Informe Bo à mão: a memória passa a dizer "informado pelo usuário".

## 0.38 — pressões (teste a cabo e TFR) e mais formulários

- [ ] Abra o projeto `ambiente_teste`. Na abertura, o SIAPP lê o `1-brsa-1304-ba_sft-2.dlis` e o
      `1BRSA1304BA_TFR.zip` do 1-BRSA-1304-BA, e de novo os formulários (leitor novo).
- [ ] Ficha do **1-BRSA-1304-BA** › "Pressões × profundidade": 8 estações do teste a cabo (círculos azuis), os PT e TC
      do RFP (quadrados laranja) e a estática do TFR (quadrado vermelho); a lama em círculos cinza. Confira na tabela:
      1.681,21 m → **167,70**; 1.754,83 m → **174,98** kgf/cm²; todas "estabilizada" (a de 1.728,5 m "quase estável").
- [ ] Ponha as quatro estações de 1.681–1.688 m no grupo **A** e as de 1.717–1.755 m no **B** → **Calcular
      gradiente**. Esperado: A ≈ **0,70 g/cm³, óleo**; B ≈ **1,05 g/cm³, água**; contato ≈ **1.694 m** (linha
      vermelha no gráfico).
- [ ] Botão "curva" numa estação: o gráfico pressão × tempo mostra a lama, as quedas dos pré-testes e o patamar
      (linha tracejada vermelha).
- [ ] Bloco "Teste de formação TFR-01 — relatório": estática **168,88 kgf/cm²** a 1.683,13 m, **k = 258 mD**,
      skin **7**, IP 8,4, 36,6 °API, 83,5 °C; quatro fluxos (F1 e três aberturas no F2). Botão do manômetro
      **30768 (usado na interpretação)**: curva de ~176 h com os dois fluxos e as duas estáticas.
- [ ] Na mesma ficha: "Relatório de Descoberta", "Relatório de Reentrada 1" (motivo, operações, resultado) e
      "Perfilagens realizadas" (50 linhas: as convencionais com intervalo, as SFT e ASR com a profundidade de cada
      ponto). Nenhum formulário "não lido".
- [ ] Perfis › clique no `1-brsa-1304-ba_sft-2.dlis`: a mensagem diz que o arquivo é indexado por tempo e manda
      para a ficha (antes: erro de "unidade desconhecida").
- [ ] Avaliação num perfil do 1-BRSA-1304-BA: a nota do Rw inclui "83,5 °C" (TFR) e "178 °F" (sonda a cabo).

## 0.37 — formulários da ANP (RFP, RFCP, Perfuração)

- [ ] Abra o projeto `ambiente_teste` (que já tem os formulários de 1-BRSA-1304-BA, 3-BRSA-1151-RN e 1-AURI-12-RN
      baixados). A tela de abertura mostra "Lendo os dados do poço nos formulários da ANP" por um instante.
- [ ] Mapa › ficha de **1-BRSA-1304-BA** › "Formulários da ANP": três documentos lidos (Relatório Final de Poço,
      de Completação e de Perfuração). Confira na tela contra o PDF (botão "Ver"):
      prof. final do sondador **1.944 m**, do perfil **1.948,5 m (cota −1.854,4)**, mesa rotativa **90,6 m**;
      12 topos (sem nome no formulário: aparece o aviso); teste **TFR 1.680–1.684 m, óleo, 36,6 °API,
      88,5 m³/d, 168,9 kgf/cm²**; temperaturas **110, 178 e 191 °F**; canhoneado **FM. AGUA GRANDE
      1.679–1.693,5 m**, HSD, 5 tiros/pé.
- [ ] Na mesma ficha, embaixo: "Também escrito como" inclui **1-FPA-1-BA** (a sigla antiga do RFCP). No mapa, em
      "Destacar poços", digite 1-FPA-1-BA e clique em Destacar: o destacado é o 1-BRSA-1304-BA.
- [ ] Ficha de **1-AURI-12-RN**: os topos têm nome (FM BARREIRAS… FM PENDÊNCIA) e diferença prevista × constatada;
      30 indícios (bloco fechado: clique para abrir); testes TCA-1 e TCA-2 com "FILTRADO/ ÁGUA FORMAÇÃO".
- [ ] Ficha de **3-BRSA-1151-RN**: observações do RFP e do RFCP; amostragem de calha (SEM AMOSTRAGEM, 9 X 9…);
      apelido 3-ARG-790-RN.
- [ ] Perfis › um perfil do 1-BRSA-1304-BA › Avaliação: na lista de intervalos aparece "Dos formulários da ANP"
      com a análise de perfis (1.679–1.693,5 m, ARENITO), o canhoneado e o TFR. Marque um e calcule.
- [ ] Na mesma tela, a nota de referência do Rw traz "No RFP: …" e o fluido de cada fase (quando o formulário de
      perfuração traz).
- [ ] No gráfico dos perfis do 1-BRSA-1304-BA: linhas marrons pontilhadas nos topos do RFP e faixa vermelha
      à direita entre 1.679 e 1.693,5 m.
- [ ] Botão "Ler os formulários de novo" na ficha: a mensagem diz quantos foram lidos.

## 0.36 — referência do GR, legenda da litologia, selo do download

- [ ] Dados › Catálogo: baixe um arquivo pequeno de um poço. O selo vai de "na fila" a "baixando" e termina em
      **"baixado"**, com o botão de abrir.
- [ ] Perfis › `1-brsa-1304-ba_raw-2.dlis` (Recôncavo) › Avaliação: GR limpo e GR argila em branco. "Procurar em"
      = arquivo inteiro, "Usar" = P5 e P95 → **Calcular**: o resultado mostra os dois valores e a trilha do GR
      ganha duas linhas tracejadas (limpo e argila).
- [ ] Troque para "mín. e máx." e calcule: os valores mudam e aparece o aviso dos picos. Troque para "janela" e
      informe topo e base: as linhas ficam só nesse trecho.
- [ ] "Só intervalos" com um intervalo todo de arenito: o SIAPP avisa (ou recusa) por falta de folhelho.
- [ ] Abra "Como o GR limpo e o da argila são escolhidos" e leia: está claro?
- [ ] Num poço com AGP (ex.: 1-AURI-12-RN), a legenda da litologia aparece embaixo dos perfis; o mouse numa classe
      mostra as rochas do AGP.

## 0.35.1 — conexão com o REATE

- [ ] Dados › Catálogo do REATE: conectar o **Recôncavo** (e a Potiguar). Conecta mesmo quando um dos dois servidores
      do portal está com defeito; o `siapp.log` registra "REATE: servidor com defeito … usando 200.237.2.134".
- [ ] Sem internet, conectar diz "Sem conexão com o REATE"; se os dois servidores estiverem fora, "O REATE está
      fora do ar" com o que cada um respondeu.

## 0.35 — comunidade: painel e biblioteca de interpretações

- [ ] Comunidade: a barra lateral tem **Contribuir**, **Painel de preenchimento** e **Biblioteca de interpretações**.
      A parte escolhida fica lembrada ao fechar o SIAPP.
- [ ] **Painel**: os números de poços com documentos, perfil, topos, dados transcritos, páginas revisadas,
      interpretações e produção, com a porcentagem. Escolha a bacia Potiguar no filtro (ou clique nela na tabela).
- [ ] "Quem contribuiu" mostra você (com o selo "você") e, se você aplicou a base ou importou um pacote, os outros
      autores. Passe o mouse nos cabeçalhos curtos: aparece o nome inteiro.
- [ ] "Onde ajudar": clique num poço — abre a ficha no mapa.
- [ ] **Perfis** › `1-AURI-12-RN_AIT_P.DLIS` › Avaliação de formação: **Calcular**, depois **Compartilhar na
      biblioteca…**: escreva um título (ex.: "Açu, Archie, Rw 0,05") e um comentário. Aparece o selo "na biblioteca".
- [ ] Mude o Rw e **Calcular** de novo (esta fica sem compartilhar).
- [ ] **Biblioteca**: a interpretação aparece agrupada pelo poço; embaixo, "Suas avaliações ainda não
      compartilhadas" com a segunda. Marque as duas e **Comparar as marcadas**: "Diferem em: Rw", a linha do Rw
      destacada e o net pay de cada uma no mesmo intervalo.
- [ ] Clique na interpretação: parâmetros (os estimados com "auto"), curvas, intervalos, comentário; "você tem
      este arquivo (mesmo hash)". **Refazer nos Perfis**: abre o arquivo com o intervalo dela marcado e os mesmos
      parâmetros; **Calcular** dá o mesmo net pay; **Comparar com a da biblioteca** põe as duas lado a lado.
- [ ] Buscar por "Archie" e pelo nome do poço; filtrar Origem = "Da base comunitária" (vazio, se não houver base).
- [ ] Contribuir › **Exportar pacote**: o resumo conta a interpretação; o JSON tem `"versao_formato": 3` e a
      lista `interpretacoes` (sem curvas). Importe o pacote em outra pasta de projeto: a interpretação aparece na
      biblioteca como "pacote"; **Desfazer** tira.
- [ ] **Tirar da biblioteca** (só nas suas): avisa se ela já foi num pacote exportado.
- [ ] Modo escuro: painel, biblioteca e comparação legíveis.

## 0.34 — mapa e seção

- [ ] Mapa, bacia Potiguar: clique em "só no cadastro" na legenda — esses poços somem (a legenda fica riscada e a lista
      diz quantos estão escondidos). Clique de novo: voltam. Dois cliques em "pasta no REATE": só esses. Clique em
      "com dados transcritos": só os que têm dados.
- [ ] **Destacar poços**: digite `7-GMR-13-RN, 1-AURI-12-RN`, escolha uma cor e "Destacar": ficam grandes, com o nome.
      Mude o filtro: continuam. "Enquadrar" e "Limpar".
- [ ] Ficha de um poço de Guamaré (com a produção do campo baixada em Dados › Produção da ANP): **Produção (ANP)** com
      acumulados e as linhas mensais de óleo, gás e água. Num poço de campo sem produção baixada: o atalho para baixar.
- [ ] **Desenhar a linha da seção**: clique A, um ponto no meio (faça uma curva) e B; dois cliques terminam. Os poços com
      topos aparecem numerados ao longo da linha. Mude a distância (km): a lista muda. **Abrir na Seção**: a seção monta
      na ordem da linha.
- [ ] Aba Seção › "desenhe a linha no mapa": vai para o Mapa já no modo de desenhar. Esc cancela.

## 0.33 — perfis e modo escuro

- [ ] Configurações › modo **escuro**. Mapa (legenda embaixo), Seção (figura e tabela), Bloco 3D (nomes dos poços,
      eixos, legenda e escala de cor), Perfis (cabeçalhos) e Documentos (página): texto escuro sobre branco, legível.
- [ ] Perfis: abra um DLIS com várias curvas. Os nomes nos cabeçalhos aparecem inteiros (quebram a linha) e as trilhas
      começam todas na mesma altura.
- [ ] **Sugerir para** "Saturação de água (Sw)": as curvas certas ficam marcadas; a explicação diz o porquê e o que falta.
      Teste também "Qualidade do poço".
- [ ] **Buscar curva**: digite "densidade" (acha RHOB/RHOZ) e um mnemônico.
- [ ] Arraste na vertical sobre o gráfico: a faixa amarela aparece enquanto arrasta, com topo, base e espessura.
- [ ] Passe o mouse no eixo de profundidade sobre uma linha verde tracejada: nome, fonte e qualidade do topo do AGP.
      Abra "O que são fonte e qualidade…" (Perfis, tabela da Seção e ficha do poço no Mapa).

## 0.32 — bloco 3D: RBF, qual método usar, aparência dos poços

- [ ] Interpretação › Bloco 3D: o painel tem os passos **1 Poços → 2 Interpolação → 3 Grade e unidades → 4 Montar**.
- [ ] Escolha os poços de um campo. Em **Qual método usar?**, troque o ambiente: em **Leque**, a RBF aparece como
      indicada; em **Fluvial**, a spline e a RBF como "evitar"; em **Rifte**, a linear. Clique num método para ver ou
      esconder os motivos.
- [ ] **Usar o indicado**: os métodos abaixo mudam (sem montar). Monte.
- [ ] **Comparar métodos**: a tabela tem RBF multiquádrica e inversa. Depois, a lista "Qual método usar?" passa a ter
      motivos "seus poços" (o que menos errou sobe).
- [ ] Parâmetros avançados com RBF: **Função** e **Raio**. Vazio = automático (o resumo do bloco diz o raio escolhido).
- [ ] **Aparência dos poços** (abaixo do visor): troque o marcador para cubo, a cor, a espessura e a cor do pay — muda na
      hora. Desligue a legenda. Feche e abra o SIAPP: a aparência continua. Exporte a figura PDF: com a mesma aparência.
- [ ] **Bloco fechado** com "Nos poços: pay": as trilhas dos poços de dentro aparecem por cima do bloco. Em "Poços por
      cima do bloco: nunca", voltam a ficar escondidas.
- [ ] Troque "Nos poços" para "só a linha" e monte de novo: continua "só a linha".
- [ ] Abra **O que é "deixar um poço de fora" e "comparar métodos"?** e confira se a explicação está clara.

## 0.31 — texto arrumado, revisão de página e busca por escopo

- [ ] Ao abrir o projeto, o índice de texto é refeito (passo "Refazendo o índice de texto"). Pode levar alguns segundos.
- [ ] Documentos → `7GMR_0013__RN_pasta_poco_pub.pdf`, pág. 27: o texto mostra "Setor de Avaliação" numa linha e
      "POÇO: …" numa linha. Clique em **Como o OCR leu** para comparar com o texto antigo (uma palavra por linha).
- [ ] Pág. 10 (revestimento/cimentação): campos do formulário na mesma linha. Abra **Possíveis erros**: palavras
      como `POCUMENTO → DOCUMENTO`, `adiiivos → aditivos`. Clique numa: o editor de correção abre com a sugestão.
- [ ] Numa página de gráfico ou manuscrita (ex.: 7AG, pág. 8), aparece o aviso **Texto pouco legível**.
- [ ] **Editar o texto** de uma página: arrume dois parágrafos e salve. Aparece o selo **revisado**, a lista mostra
      "1 revisada(s)" e a busca acha uma palavra que você digitou. Tente mudar de página antes de salvar: o SIAPP
      pede para salvar ou cancelar. **Voltar ao texto automático** (dois cliques) desfaz.
- [ ] Transcrever → tipo **Trecho do texto (citação)**: desenhe uma caixa em volta de um parágrafo; o texto aparece
      já arrumado. Salve e confira na tabela da página.
- [ ] Lista de documentos agrupada por bacia › poço, com o campo ao lado do poço. Filtre por **campo** (GUAMARÉ):
      "N de M documento(s) no filtro".
- [ ] **Buscar em** "só os do filtro ao lado" e busque `revestimento`: só documentos do campo. "Só o documento
      aberto": resultados em ordem de página.
- [ ] Clique num resultado: no painel aparece "achado 1 de N"; **próximo ›** (ou F3) vai ao seguinte, mesmo em outro
      documento; Shift+F3 volta.
- [ ] **ir à** 40 + Enter: vai para a pág. 40.

## 0.30 — abas novas, janelas, divisão, cores e configurações

- [ ] Abra o SIAPP: com o projeto já criado, ele **abre sozinho** e mostra a tela "Abrindo o projeto" com os
      passos. As cores são **Marinho e lima**.
- [ ] Abas: Projeto · Dados · Mapa · Documentos · Perfis · Interpretação · Viabilidade · Comunidade. Em **Dados**,
      as sub-abas Catálogo do REATE, Cadastro da ANP, Levantamento do acervo, Produção da ANP e Camadas geográficas.
      Em **Interpretação**, os botões Seção e Bloco 3D no alto da barra lateral. **Viabilidade** tem mapa próprio.
- [ ] **Dividir**: Mapa à esquerda e Documentos à direita. Arraste a divisória; dois cliques voltam à metade. Troque a
      aba da direita ("à direita") e os lados (⇄). Clique na aba da direita: ela passa para a esquerda.
- [ ] Na aba **Mapa** → **Abrir em janela**: o Mapa vira uma janela própria. Arraste para o outro monitor, maximize,
      encaixe com Win+←/→. Na principal, a aba aparece em itálico com "janela"; clicar nela traz a janela para a frente.
- [ ] Com Documentos numa janela própria, abra a ficha de um poço no Mapa e clique em **Ver** num PDF: o documento abre
      na janela de Documentos.
- [ ] Feche a janela do Mapa (ou "Voltar para a principal"): a aba volta. Deixe uma aba destacada, feche o SIAPP e abra
      de novo: as janelas voltam onde estavam (desligue em Configurações › "Lembrar o arranjo").
- [ ] **Recolher** a barra lateral (seta no canto): fica uma faixa com o nome; abre de novo pela seta. Continua recolhida
      depois de reabrir o SIAPP.
- [ ] **Engrenagem** → Configurações: troque a paleta, o modo (escuro) e o tamanho do texto; com uma aba destacada, as
      duas janelas mudam juntas. → **Diagnóstico**: versões, erros e tempos; **Copiar para enviar** e cole num e-mail.
- [ ] **Exportações** (no alto): as quatro pastas, com quantos arquivos; **Abrir** abre no Explorador.
- [ ] Clique na mensagem do rodapé: o histórico da sessão, com as mensagens inteiras.

## 0.29.1 — bacias misturadas e cores das correções

- [ ] Ao abrir o projeto, a ficha do `7-GMR-13-RN` (Mapa → clique no poço) mostra **só** "Potiguar · Categoria-7 ·
      Categoria-7_parte28" no portal REATE. No `siapp.json`, o histórico tem `reparou_catalogo` com quantos
      registros saíram.
- [ ] Catálogo → Potiguar → **Conectar** → clique em Categoria-7 e, antes de a lista aparecer, troque para Alagoas
      → **Conectar**. A lista da Potiguar não aparece sob Alagoas (o rodapé diz que ela foi guardada na Potiguar).
      Liste a Categoria-7 de Alagoas: ~510 poços, todos `-AL`.
- [ ] Documentos → abra uma página com OCR, role o texto até o meio, clique numa palavra errada, digite a forma
      certa → **Corrigir em todos os documentos**: o texto fica no mesmo ponto, a palavra aparece **azul** e pisca, e
      na imagem a palavra ganha um contorno azul (as corrigidas pelo dicionário, verde).
- [ ] Clique numa palavra e envie sem mudar nada: o editor explica que é igual ao lido (em vez de só o rodapé).

## 0.29 — API e densidade do gás nas pastas de poço

- [ ] Com pastas de poço de Guamaré baixadas (aba Catálogo) → Mapa → `GUAMARÉ` → **Medir as distâncias** → abra
      "Espaço poroso": o quadro **Nos documentos dos poços do campo** diz quantos poços, documentos baixados e com
      texto. Se houver pendentes: **Processar os documentos pendentes** (acompanhe na aba Documentos) e depois
      **Procurar de novo**.
- [ ] Valores lidos: cada um com poço, arquivo, página e o trecho lido. **abrir** leva à página na aba Documentos com
      "Transcrever" aberto e o tipo "Propriedade de fluido" preenchido. **confirmar** vira dado transcrito;
      **descartar** risca a leitura (e **voltar** desfaz).
- [ ] "Páginas que citam sem número legível": no 7-GMR-13-RN aparece a pág. 43 ("análise do óleo produzido", com os
      campos API e DENS.(CNTP) do formulário). **abrir e transcrever**, desenhe a caixa no valor, salve; volte e
      **Procurar de novo**: o API passa a "dado transcrito" e o campo Grau API mostra o valor em cinza.
- [ ] Calcular a viabilidade: na memória, a entrada API diz "dado transcrito: 7-GMR-13-RN (… p. 43) = …".

## 0.28 — Bo, Rs e Bg por correlação; blocos × gasoduto

- [ ] `GUAMARÉ`, sem Bo/Bg/Rs, com o **Grau API** do óleo preenchido (em "Espaço poroso") → Calcular: o espaço
      poroso tem valor e os avisos dizem "Estimados por correlação: Rs (Standing), Bo (Standing), Bg (Sutton +
      Papay)". Na memória, o bloco "Propriedades dos fluidos (correlações)" com cada conta (psia, °F, Rs, Bo, Tpc,
      Ppc, Z, Bg). Sem o API: só o Bg é estimado e falta "Bo (ou o grau API, para estimar)".
- [ ] "Estimar o que faltar" = não: volta a pedir Bo e Bg.
- [ ] **Blocos e campos × infraestrutura**: com Blocos exploratórios e Gasodutos de transporte baixados →
      **Medir todas** (alguns segundos): legenda com quantos blocos em cada faixa, tabela dos mais próximos (POT-T
      cruzados pelo Gasfor aparecem como "toca"), blocos coloridos no mapa. Filtre por `Potiguar`. Clique num nome:
      o mapa vai até ele. **CSV**: todas as áreas, com as fórmulas e as entradas do custo no cabeçalho.
- [ ] Troque Áreas para Campos de produção e Até para Dutos de escoamento: mede de novo.

## 0.27 — memória de cálculo, constantes e equações editáveis

- [ ] `GUAMARÉ` → **Calcular a viabilidade**: aparece **Memória de cálculo — passo a passo**. Abra: cada dado de
      entrada com a fonte (Np e Gp "Plano de Desenvolvimento (BAR/2021…)", custo "EPE PIG 2024…", f_fluido
      "padrão — estimativa do SIAPP…"); cada passo com a equação, a equação com os números e o resultado; a
      densidade do CO₂ com κ, α, a, b, A, B, Z… **Abrir a memória (HTML)**: a mesma página no navegador
      (Ctrl+P → PDF). Em `ambiente_teste\execucoes\viabilidade\` ficam o .html e o .json de cada execução.
- [ ] **Equações** → Custo do duto por km → "afim: parcela fixa + por polegada"; em **Parcela fixa** ponha 500.
      Calcular: o custo por km muda, e a memória marca "alternativa: afim…".
- [ ] Em Espaço — método simples, escreva a sua fórmula (ex.: `Np + 2 * Gp / gas_por_oe`): a caixa fica vermelha
      e o seletor vira "a minha fórmula". Calcular: a memória marca "fórmula do usuário". Escreva `Np * Zz`: a
      barra de status diz "variável desconhecida Zz".
- [ ] **Constantes** → Fator de custo do duto — CO₂ = 1,3: o texto do custo mostra ×1,3; os avisos dizem
      "1 constante(s) alterada(s)". **Voltar tudo ao padrão** limpa equações e constantes.
- [ ] Meça o campo de novo: equações e constantes alteradas voltam preenchidas (ficam guardadas no campo).

## 0.26 — viabilidade econômica

- [ ] **Mapa** → **Campo e infraestrutura** → `GUAMARÉ` → **Medir as distâncias**: abaixo aparece **Viabilidade
      econômica**, com CO₂, custo do PIG 2024 (488) e 8″. O texto embaixo diz "R$ 4,68 milhões por km (×1,2 …)".
- [ ] **Calcular a viabilidade** só com a produção: "Simples (PIBIC)" ≈ 1,65 milhão de m³ de óleo equivalente
      (acumulada do PD, BAR/2021); poroso e molécula dizem o que falta. Na tabela, UPGN a 2,7 km ≈ R$ 13 mi de
      duto, ≈ R$ 7,7 por m³ oe; termelétrica (★, origem do CO₂) a 43 km ≈ R$ 201 mi, ≈ R$ 122 por m³ oe.
- [ ] Abra **Espaço poroso** e **Pela molécula**, preencha Bo, Bg, Rs do campo e P/T (ou só a profundidade) →
      Calcular: os três métodos com valor e a capacidade em Mt de CO₂. Troque o fluido para H₂: aparece R$/MWh e
      o ★ vai para os projetos de hidrogênio (se a camada estiver baixada).
- [ ] Meça de novo o campo: os parâmetros voltam preenchidos. **CSV** → `exportacoes\producao\viabilidade_guamare.csv`.
- [ ] Troque a referência de custo (PIG 2019 — relevo plano): 325; digite outro valor: a referência vira
      "informado por mim".

## 0.25 — camadas no mapa e campo × infraestrutura

- [ ] **Mapa** → em "Camadas geográficas", depois de baixar, aparece **Mostrar no mapa**: marque gasodutos de
      transporte, dutos de escoamento, UPGNs e campos de produção. Clique num gasoduto: diâmetro, transportadora.
- [ ] **Campo e infraestrutura** → `GUAMARÉ` (com a produção baixada no Bloco 3D) → **Medir as distâncias**: polígono
      "ANP — vértices"; Gasfor e escoamento "no campo", UPGN a ~2,7 km, city gate e termelétrica a ~43 km; depleção
      do PD: óleo 10,1%, gás 42,2%. No mapa, o campo em amarelo e linhas tracejadas até cada feição. **CSV**.
- [ ] Um campo sem produção baixada: usa a camada Campos de produção (ou os poços) e avisa que falta o PD.

## 0.24 — produção da ANP, camadas e um campo num clique

- [ ] **Bloco 3D** → Escolher "os poços de um campo" → troque o **Campo** para `ESTREITO`: os poços vêm sozinhos.
      **Montar este campo**: o bloco aparece com o título "Campo de Estreito" e a escala de reservatório.
- [ ] **Produção do campo (ANP)**: o campo já vem preenchido. Período "últimos 5 anos" → **Baixar a produção**
      (a barra de status mostra arquivo por arquivo; ~60 MB na primeira vez). O quadro mostra a soma do período
      (óleo, gás, água, injeção de vapor), o último mês, as zonas (ALG, AÇU…) e o PD 2019 (óleo in place 133,35
      milhões de m³, acumulada 16,26 até 31/12/2018; 2025 poços perfurados).
- [ ] Baixe de novo: termina em segundos (cópia local em `ambiente_teste\fontes\anp\producao\`). Troque para
      `GUAMARÉ` e baixe: só baixa o que faltar (os arquivos nacionais já estão guardados). **CSV**: dois arquivos
      em `exportacoes\producao\`.
- [ ] **Cancelar** no meio de um "todo o histórico": para, e o que já veio fica.
- [ ] **Mapa** → **Camadas geográficas**: as marcadas por padrão (gasodutos de transporte e escoamento, UPGNs,
      termelétricas, campos, blocos, dutos e portos do IBGE…). **Baixar as marcadas**: cada uma diz "baixada em …
      · N feições". **Abrir a pasta** → `sig\epe\epe_gasodutos_transporte.geojson`; no **QGIS**, arraste o
      GeoJSON e o shapefile de `sig\anp\anp_campos_producao\` — caem no lugar (SIRGAS 2000). Nordestão e Gasfor
      aparecem saindo de Guamaré.
- [ ] (0.24.1) **Hidrogênio verde: unidades e projetos** já vem marcada: baixada, diz "29 feições (2 sem coordenadas
      na fonte)"; no QGIS, os pontos se concentram em Pecém (CE), Suape (PE), Açu (RJ) e Rio Grande (RS).

## 0.23 — interpolação e escala

- [ ] **Bloco 3D**: a **Escala** abre em "reservatório": o quadro **Interpolação** mostra spline nos topos e
      nas espessuras, IDW nas propriedades, bloco fechado topo a topo; o texto embaixo explica o método.
      Clique em cada método: a explicação muda ("Bom para: …").
- [ ] Troque para **bacia**: escolha vira "todos da bacia", corte de 15 km, tendência + krigagem; em
      **Parâmetros avançados** aparecem variograma, alcance, azimute, razão e grau (passe o mouse: o que cada
      um faz). Mexa em qualquer campo: a escala vira "personalizada".
- [ ] `ESTREITO`, escala reservatório → Montar: o resumo diz "por spline de placa fina"; **Bloco fechado**:
      "topo a topo · spline de placa fina".
- [ ] **Comparar métodos**: em segundos, a tabela com 6 colunas (mediana / 68%), negrito no menor de cada
      unidade e o sugerido (no Estreito, tendência + krigagem ~9 m contra 15 m da linear). **Figura → PDF**:
      um símbolo por método, cheio = o melhor da linha. **CSV**.
- [ ] **Usar o melhor e montar de novo**: o formulário troca os métodos e o bloco é montado de novo.
- [ ] Monte com tendência + krigagem (escala bacia, mas com os poços do campo) → **Colorir o topo de**
      Jandaíra **por incerteza do topo**: claro nos poços, escuro longe (σ de ~3 a ~17 m).
- [ ] Reabra um bloco em *Blocos anteriores*: a interpolação dele volta para o formulário; um bloco da 0.22
      volta como linear por espessuras.
- [ ] Bacia inteira (Potiguar): **Comparar métodos** leva ~3 min (a barra de status diz qual método está
      rodando); o sugerido é a linear por espessuras (~15 m), a spline topo a topo fica perto (~16 m).
- [ ] Modo de escolha "um campo": os campos de poço/raio e de bacia não aparecem.

## 0.22 — saídas do bloco

Abra **Saídas do bloco** (embaixo do visor) num bloco do `ESTREITO`.

- [ ] **Exportar os mapas** → pasta `exportacoes\blocos\bloco_…_mapas\`: um `.tif` por mapa (terreno,
      topo_…, isopaca_…), o XYZ e o LEIA-ME. No **QGIS**: arraste `topo_acu.tif` — cai no lugar certo
      (SIRGAS 2000 / UTM 24S), cores pela cota; o XYZ abre como texto delimitado (`;`).
- [ ] **Simulador**: a prévia mostra a grade (ex.: 232 × 78 × 15 = 271.440 células, teto 275.625). Desmarque
      uma formação ou mude Camadas/Célula: a prévia muda. **Exportar o .DATA**.
- [ ] No **tNavigator**: abra o `.DATA` da pasta `bloco_…_eclipse\`. A grade aparece no lugar, uma região
      por formação (FIPNUM), os poços (fechados). O deck roda com os valores provisórios (veja o LEIA-ME:
      permeabilidade, PVT, curvas relativas e contatos marcados para trocar).
- [ ] **Volumetria**: a tabela mostra área, espessura média e volume de rocha; onde há avaliação de
      formação, N/G e φ aparecem em cinza (passe o mouse: "da avaliação (n poços)"). Digite Sw e Bo numa
      formação e **Calcular**: volume poroso, hidrocarboneto e óleo in place. Com E = 0,02 e ρ = 650:
      capacidade de CO₂ em Mt. **CSV**.
- [ ] **Exportar o .glb** → `bloco_….glb`. No **PowerPoint**: Inserir → Modelos 3D → Este dispositivo: o bloco
      aparece colorido e gira com o mouse.

## 0.21 — validação cruzada e prognóstico

- [ ] **Bloco 3D** → `ESTREITO` → Montar → **Deixar um poço de fora**: em segundos, o quadro "Validação
      cruzada" com o resumo (metade dos erros até ~15 m), a tabela por unidade e a tabela por distância.
- [ ] Passe o mouse no disco de um topo de um poço: "sem este poço: bloco fechado … (erro …)".
- [ ] **CSV** e **Figura → PDF** da validação em `exportacoes\blocos\bloco_…_validacao.*`.
- [ ] Feche e reabra o bloco em *Blocos anteriores*: a validação volta junto.
- [ ] **Clicar no bloco** → clique num ponto entre os poços (sem arrastar): o quadro "Prognóstico" com a
      coluna prevista (topo, profundidade abaixo do terreno, ±, espessura) e um pino vermelho no visor.
- [ ] Escreva `-5,40; -36,85` e **Prever** (ou Enter). **CSV** do prognóstico. **Limpar** tira o pino.
- [ ] Bacia inteira (Potiguar, Cat. 1): a validação leva ~15 s; o aviso "Topos abaixo do fundo do poço"
      lista os poços com o topo estimado (ex.: 1-JD-2-RN); a base do bloco fica perto de −4.700 m.

## 0.20 — bloco fechado

- [ ] **Bloco 3D** → `ESTREITO` → Montar → botão **Bloco fechado**: um bloco opaco com paredes retas,
      Barreiras (laranja) no topo, Jandaíra aflorando perto do 1-SS-1-RN e do 1-RP-3-RN, embaixo Açu,
      Alagamar e Embasamento até a base em −610 m. O resumo diz a base e a referência.
- [ ] A lista de unidades mostra área, espessura máxima, volume (km³) e % extrapolada.
- [ ] **Corte** → o quadrante sudoeste some e as tampas mostram as camadas por dentro; troque o quadrante
      e mova **O–L** e **S–N**.
- [ ] **Afastar as camadas**: as camadas se separam; os poços somem. Volte a zero.
- [ ] Na aba Seção, ponha 3 poços do Estreito; volte e marque **Seção A–A′**: parede pelos poços, de borda
      a borda, com A e A′; o bloco fica translúcido.
- [ ] Com margem de 2 km: a faixa da margem aparece **mais clara** (extrapolada).
- [ ] **Base do bloco fechado** = −1000 → Montar: o Embasamento vai até −1000 m.
- [ ] **Figura → PDF** no modo bloco fechado, com corte: as tampas e os poços no quadrante tirado.
- [ ] **Superfícies** volta ao modo anterior (opacidade 0,85), sem montar de novo.
- [ ] Um bloco montado na 0.19 (em Blocos anteriores) abre só no modo Superfícies.

## 0.19 — bloco 3D, etapa 2

Antes: levantar a Potiguar de novo (Cat. 1 basta) com **Ler os dados direcionais** marcado
(já vem marcado) — lê só os arquivos de trajetória, ~5 KB por poço.

- [ ] O resumo do levantamento ganha "Dados direcionais (trajetória)": no portal, lidos, com trajetória.
- [ ] **Bloco 3D** → em volta do `1-FG-2D-RN`, 15 km → Montar. O 1-FG-2D-RN aparece curvo (afasta ~1 km
      para o norte); passe o mouse: "trajetória dos dados direcionais · afastamento 1.052 m".
      O aviso lista os poços com trajetória.
- [ ] Sem ter levantado de novo: escolha os poços e **Ler as trajetórias**; depois monte de novo.
- [ ] **Nos poços** → *indícios de óleo e gás (AGP)*: trechos verdes (óleo) e vermelhos (gás) ao
      longo dos poços, com legenda no canto.
- [ ] Faça uma avaliação de formação (aba Perfis) num poço do bloco, no intervalo de uma formação, e
      monte o bloco de novo: **Nos poços** → *pay (avaliação de formação)* mostra não reservatório /
      reservatório / pay / pay com indício de gás.
- [ ] Com 3 ou mais poços avaliados na mesma formação: **Colorir o topo de** → a formação → por HPV:
      superfície em azul claro→escuro com a escala; as outras ficam translúcidas. Troque para N/G, φ, Sw.
      Com menos de 3: só as esferas coloridas nos poços ("só nos poços").
- [ ] **Figura → PDF** (e SVG, PNG): a mesma vista em projeção ortográfica, estilo artigo, em
      `exportacoes\blocos\bloco_…_figura.pdf`. Gire o bloco e exporte de novo: a figura acompanha.

## 0.18 — bloco 3D

Antes: AGPs lidos (Cat. 1 da Potiguar basta).

- [ ] **Bloco 3D** → Escolher *os poços de um campo* → `ESTREITO` → **Trazer os poços** (14) →
      **Montar o bloco**. Aparecem os poços, as superfícies de Barreiras, Jandaíra, Açu, Alagamar
      e Embasamento e o resumo "contorno dos poços 149,4 km²".
- [ ] Girar com o mouse, aproximar com a roda; **De cima** mostra o mapa dos poços; a seta do
      norte acompanha.
- [ ] **Exagero vertical**: de 1× (real) a 60×. **Opacidade**: ver as superfícies de baixo.
- [ ] Desmarcar *Formação Jandaíra* na lista: a superfície e os discos somem.
- [ ] Passar o mouse num disco: poço, unidade, profundidade e cota do topo.
- [ ] Avisos embaixo: Ponta do Mel em 1 poço (sem superfície); onde duas superfícies se cruzam.
- [ ] **PNG**: `exportacoes\blocos\bloco_….png` com legenda e carimbo. **CSV**: topos e grade.
- [ ] *Todos da bacia* → Potiguar, com "Esconder onde o poço mais próximo está a mais de 15 km":
      o bloco regional (429 poços; o `1-BRSA-264-ES` fica de fora com aviso). Os nomes vêm
      desligados (muitos poços).
- [ ] *Em volta de um poço*: `1-BRSA-276-RN`, 10 km. *Os poços da aba Seção*: a lista da Seção.
- [ ] Margem 1 km num campo: a superfície passa um pouco do contorno (valor do poço mais próximo).
- [ ] **Blocos anteriores**: reabre sem recalcular.

## 0.17 — esquemas de ferramentas

Antes: o levantamento da Potiguar já feito (Cat. 1 basta). Sem marcar nada novo.

- [ ] **Mapa** → ficha do `1-AURI-12-RN`: seção **Esquemas de ferramentas (2)** — `AIT_tool`
      como *Perfil de resistividade* e `RFT_tool` como *Teste de formação a cabo*, pelo nome.
- [ ] Em **No acervo do REATE**, embaixo de cada arquivo: `AIT_P` → *passada principal*,
      `AIT_R` → *passada repetida*, `RFT1`…`RFT8` → *Teste de formação a cabo · corrida N*.
- [ ] **Ler os esquemas (OCR)**: na primeira vez baixa o modelo de OCR em inglês (~4 MB).
      Depois de alguns segundos o `AIT_tool` vira *Perfilagem convencional* com as ferramentas
      (HGNS, HILTB, MCFL, HRCC, DSLT, HAIT), "Mede: raios gama, nêutron, densidade…",
      Schlumberger, Ø máx. 4,63". Passe o mouse num código: nome, como foi lido, o que mede.
- [ ] **Abrir o PDF**: abre a cópia em `ambiente_teste\esquemas\Potiguar\1-AURI-12-RN\` —
      confira se as ferramentas batem com o desenho.
- [ ] Outros poços para olhar: `8-PV-14-RN` (Tucker: GRT + FTT = testador), `3-BRSA-590-RN`
      (FMI + GPIT = imagem), `7-CAM-1130-RN` (PDF com texto: lê sem OCR).
- [ ] **Perfis**: um DLIS baixado de um poço com esquema mostra o rótulo na lista e, aberto,
      "Corrida: … · ferramentas: …" embaixo do título.
- [ ] Levantamento com **Ler os esquemas de ferramentas** marcado numa categoria pequena: a
      etapa 4 aparece na barra e o resumo ganha "Esquemas de ferramentas" por tipo.
- [ ] Sem internet: o botão ainda lê os PDFs com texto e avisa que faltou o OCR.

## 0.16 — seção no estilo clássico

- [ ] **Seção** → Estilo **clássico (indústria)** (já vem marcado) → montar a seção de Estreito
      (A = `1-SP-2-RN`, B = `1-FL-1-RN`, 3 km), nivelada no topo do Açu.
- [ ] Cada poço com a coluna litológica em padrões (calcário em tijolo no Jandaíra, arenito
      pontilhado no Açu, embasamento em cruzes), escala de profundidade medida e faixa da formação.
- [ ] Entre poços: corpos em pastel com "Fm. Jandaíra", "Fm. Açu"…; linha vermelha do DATUM.
- [ ] No topo: símbolo de cada poço (óleo / seco), MR e PF, distâncias, A (W) e A′ (E).
- [ ] Embaixo: legenda só com o que aparece, mapa de localização com A–A′ e o carimbo
      (seu nome sai em "Elaboração" se estiver preenchido na aba Comunidade).
- [ ] Estilo **moderno** → montar: a versão anterior, colorida. Em **Seções anteriores**, cada
      uma reabre no seu estilo.
- [ ] **PNG** e **PDF**: os padrões de rocha aparecem iguais à tela.

## 0.15 — seção estratigráfica

Antes: levantar a Potiguar (pelo menos a Cat. 1) com **Ler os AGPs** na 0.14.1.

- [ ] **Seção**: o texto do topo diz quantos poços têm topos no AGP. Digite `1-SP-2-RN` e
      **Adicionar**; depois, pela ficha de outro poço (aba Mapa), **Adicionar à seção**.
- [ ] **Poços ao longo de uma linha**: A = `1-SP-2-RN`, B = `1-FL-1-RN`, 3 km → **Buscar**: ~16
      poços do campo de Estreito, em ordem.
- [ ] **Montar a seção** (cota, formações): colunas Jandaíra (azul), Açu (laranja),
      Alagamar, Embasamento; faixas e linhas entre vizinhos; tooltip com topo, cota e fonte.
- [ ] Eixo **nivelado** no topo da **Formação Açu**: o topo do Açu fica reto em 0.
- [ ] **Unidades: membros e camadas**: aparecem Açu 1–4, Galinhos, Upanema, Ponta do Tubarão
      (nos poços que têm).
- [ ] Um perfil (DLIS/LIS) de um desses poços aberto na aba Perfis → montar de novo: a
      curva GR aparece ao lado da coluna, em cota.
- [ ] Avisos abaixo da figura (saltos de topo entre vizinhos) e tabela **Topos usados**.
- [ ] **SVG / PNG / PDF / CSV** → **Abrir a pasta**: os quatro em `exportacoes\secoes\`; o PNG
      serve para o artigo (300 ppp); o CSV abre no Excel.
- [ ] **Seções anteriores**: clicar reabre a seção sem recalcular.
- [ ] `execucoes\secao_….json` tem os poços, os parâmetros e cada topo com a fonte.

## 0.14.1 — AGP no leiaute novo

- [ ] **Mapa → Levantamento do acervo**: Potiguar, **Cat. 1**, **Ler os AGPs**, **Levantar** de
      novo. A etapa 3/3 passa rápido (relê da cópia local, sem baixar) e o resumo mostra os
      AGPs lidos subindo de ~366 para ~438 e nenhum "Não parece um AGP".
- [ ] Ficha do **1-BRSA-276-RN**: unidades (Jandaíra, Açu, Alagamar, **Camadas Ponta do
      Tubarão**, Pendência), nome antigo **1-TRO-1-RN**, corridas com Rm/Rmf/BHT.
- [ ] Ficha do **1-AE-1-RN** (leiaute antigo): "Camadas Ponta do Tubarão" com nome por extenso.
- [ ] Ficha do **1-BRSA-264-ES**: aviso de que o AGP estava na pasta do 1-BRSA-354-RN.
- [ ] Perfis de um 1-BRSA com DLIS: trilha **Litol. (AGP)** com a litologia interpretada.

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
