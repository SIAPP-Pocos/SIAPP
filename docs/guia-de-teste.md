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
