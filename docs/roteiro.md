# Roteiro

Decidido em 16/10/2026: primeiro as **funcionalidades novas**; as melhorias do que já
existe e a validação científica ficam **para o final**, antes do lançamento (1.0).

## Agora — funcionalidades novas

- [x] **Esquema de ferramentas** (0.17): ler os PDFs da pasta "Esquema de Ferramentas",
      reconhecer as ferramentas da coluna e rotular os perfis do poço (passada principal,
      repetida, testador de formação, imagem, RMN…). Ver `docs/ferramentas.md`.
- [x] **Bloco 3D** (0.18): poços e superfícies de topo pelos topos do AGP, dentro do
      contorno dos poços; visor 3D; PNG e CSV. Ver `docs/bloco.md`.
- [x] Bloco 3D, etapa 2 (0.19): trajetória real dos poços desviados (Dados Direcionais);
      pay e indícios ao longo dos poços; HPV/net pay/N/G/φ/Sw sobre o topo (requisito 7.4);
      figura estática no estilo artigo.
- [x] **Bloco fechado** (0.20): o volume do terreno a uma base plana, camadas por espessura,
      corte, seção A–A′, camadas afastadas; figura dos dois modos.
- [x] **Validação cruzada e prognóstico** (0.21): quanto o bloco erra sem cada poço, por
      unidade e por distância; coluna prevista num ponto com incerteza.
- [x] **Saídas do bloco** (0.22): `.DATA`/`.GRDECL` no formato ECLIPSE (grade corner-point,
      uma região por formação, poços com a trajetória), para tNavigator e afins; mapas de topo
      e isópaca (XYZ, GeoTIFF) para o QGIS; volumetria preliminar por formação; modelo `.glb`.
- [x] **Interpolação e escala** (0.23): linear, IDW, spline, krigagem, tendência + krigagem, um método
      por campo, com explicação; bloco fechado topo a topo; mapa de incerteza; comparação dos métodos
      pela validação cruzada (tabela, figura, "usar o melhor"); escala reservatório ou bacia.
- [x] **Dados de fora do REATE** (0.24): produção da ANP por campo (por poço, por zona, sumário do PD,
      polígono); camadas da EPE, ANP e IBGE (gasodutos, campos, blocos…) guardadas em `sig/`; um clique
      monta o bloco de um campo.
- [x] **Camadas no mapa e campo × infraestrutura** (0.25): distâncias do campo ao gasoduto, UPGN, H₂, fonte
      de CO₂; depleção pelo PD.
- [x] **Viabilidade econômica** (0.26): custo do duto pelos PIGs da EPE, capacidade de injeção em três métodos
      (simples/PIBIC, espaço poroso com Bo/Bg, pela molécula CO₂/H₂/CH₄), indicador investimento ÷ capacidade.
- [x] **Viabilidade auditável** (0.27): memória de cálculo de cada execução (entradas com fonte, equação,
      números substituídos, resultado) em JSON e HTML; constantes com padrão e fonte; equações trocáveis por
      alternativas prontas ou por fórmula do usuário.
- [x] **API e densidade do gás das pastas de poço** (0.29): dados transcritos (tipo propriedade_fluido) e leitura
      automática do texto dos documentos dos poços do campo, com a página como fonte.
- [x] Viabilidade — refinamentos (0.52): diâmetro pela vazão, correção do custo pela inflação (IPCA/INCC) e restrições
      ambientais (UCs federais e terras indígenas importadas). Ver `docs/viabilidade.md`. Falta transcrever API e densidade de Guamaré
      (depende dos documentos dos poços baixados: ver o guia, seção 0.52).
- [x] **Gasodutos e blocos exploratórios** (0.28): distância de cada bloco exploratório (ou campo) à feição mais
      próxima da camada escolhida e o custo do duto; mapa colorido por distância; CSV com fórmulas e entradas.
- [x] **Bo, Rs e Bg estimados por correlação** (0.28): Standing (pede o API) e Sutton + Papay, com aviso de faixa.
- [x] **Painel de preenchimento e biblioteca de interpretações** (0.35): quanto do acervo está preenchido e
      quem contribuiu; avaliações de formação compartilhadas, comparadas e refeitas com os mesmos parâmetros.
- [x] **Abrir como um software** (0.47): dois cliques no atalho abrem uma janelinha de carregamento, sem console.
      Ver `docs/lancador.md`.

## Em aberto — o que falta (atualizado na 0.47)

- [ ] **Validar no Windows as versões 0.37–0.46** pelo `docs/guia-de-teste.md` (o Ruan testa; o Claude corrige).
- [x] **Bloco 9 — petrofísica básica** (0.48): plugs (porosidade, permeabilidade, densidade) e gama do testemunho
      (planilhas `_COREGAMA.xls` / `Petrofisica Basica.xls`; 162 poços). Visto só no 1-ALG-1-RN; ver `docs/petrofisica.md`.
      Falta comparar plug × perfil (próximo passo, a combinar).
- [ ] **Dados › Arquivos baixados** (pedido de 31/10, "achar e abrir o que já existe"): tudo o que foi baixado, de
      qualquer formato (CSV, XLS, ZIP, SEG-Y…), em níveis bacia › poço › pasta, com tipo, formato, tamanho, data, se
      algum leitor leu e onde o dado aparece; botões **Abrir**, **Mostrar na pasta** (Explorer com o arquivo selecionado)
      e **Ver na ficha**; busca e filtro. O usuário não deve precisar fuçar as pastas do projeto. **Mostrar o desenho
      ao Ruan antes de programar.**
- [ ] **Bloco 4 — leitura do OCR**: mais resolução e segunda passada nas páginas ruins.
- [ ] **Viabilidade**: diâmetro do duto pela vazão; custo corrigido pela inflação (IPCA/INCC); restrições
      ambientais (unidades de conservação, terras indígenas); transcrever API e densidade de Guamaré.
- [ ] **Pendências que dependem do Ruan**: Rw de referência por formação; conferir os números antigos do
      relatório (LIS convertidos); disponibilidade de RHOB/NPHI/DT pelo levantamento do acervo.

## No final — melhorias do que já existe

- [x] **Procurar por tipo de dado** (0.49): em quais poços há petrofísica, PVT, etc., pelo levantamento; ver no mapa,
      baixar só os arquivos do tipo e exportar CSV. Ver `docs/tipos-de-dado.md`.
- [x] **Download em lote** (0.49 por tipo de dado; 0.51 por seção, campo e mapa): baixar os perfis dos poços de uma seção, de um campo ou do filtro
      do mapa, com uma tabela por poço (nada pré-marcado; atalhos só para marcar) e leitura
      automática ao terminar. Os rótulos de corrida da 0.17 ajudam a escolher (ex.: só a
      perfilagem convencional, passada principal).
- [x] **Seção pelo mapa** (0.34): a linha desenhada no mapa (A, pontos intermediários, B) escolhe os
      poços e abre a seção nessa ordem.
- [ ] **Instalador para Windows** (.exe que roda sem instalar Python). A 0.47 (lançador silencioso) é um passo
      nessa direção.
- [ ] Ajustes finos do estilo clássico da seção a partir de uma figura de referência
      (ex.: Boletim de Geociências da Petrobras).
- [ ] Esquemas: ampliar o dicionário de ferramentas (Halliburton, Baker, Weatherford) com
      esquemas reais desses fabricantes.

## No final — validação científica

- [ ] Avaliação de formação contra valores publicados (poço com Rw conhecido).
- [ ] Seções estratigráficas conferidas com a carta estratigráfica e a geologia do campo.
- [ ] Avaliação em lote por formação (tabela poço × formação) — depende do download em lote.
- [ ] Esquemas: conferir uma amostra maior (ex.: 100 esquemas sorteados) contra o PDF.

## No final — por último (decidido em 28/10/2026)

- [ ] **Análise de um perfil no SIAPP × feita à mão**: escolher o poço juntos e comparar os
      resultados da avaliação de formação com a análise manual (validação científica).
- [ ] **Revisão guiada da pasta do projeto** (pedido de 31/10; junto com a análise à mão do 1-BRSA-1304-BA, Recôncavo,
      arenito de 1.679–1.693,5 m, Fm Água Grande): explicar o que é cada pasta, arquivo, extensão e nome, e para que
      serve; **glossário** dos termos da interface e do código (ex.: "árvore"). O resultado também vira
      `docs/estrutura-da-pasta.md`.
- [ ] **Bibliografia de tudo**: métodos (Archie, Larionov, krigagem, RBF de Hardy, Rippa,
      Dubrule, Clark e Evans…), fontes de dados (ANP/REATE, EPE, IBGE) e softwares e
      bibliotecas usados, com as referências completas.

## Antes do lançamento

- [ ] Termos de uso dos dados da ANP; DOI (Zenodo); publicar no GitHub (SIAPP-Pocos).
