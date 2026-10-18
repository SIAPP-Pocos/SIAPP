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
- [ ] Viabilidade — próximos refinamentos (com o Ruan): Bo/Bg por campo de fonte pública, diâmetro pela vazão,
      correção do custo pela inflação (IPCA/INCC), restrições ambientais (UCs, terras indígenas).
- [ ] **Gasodutos e blocos exploratórios** (com o Ruan): camadas do IBGE/EPE/ANP, distância
      do bloco exploratório ao gasoduto mais próximo, para a eficiência econômica de injetar CO₂.

## No final — melhorias do que já existe

- [ ] **Download em lote**: baixar os perfis dos poços de uma seção, de um campo ou do filtro
      do mapa, com uma tabela por poço (nada pré-marcado; atalhos só para marcar) e leitura
      automática ao terminar. Os rótulos de corrida da 0.17 ajudam a escolher (ex.: só a
      perfilagem convencional, passada principal).
- [ ] **Seção pelo mapa**: clicar nos poços A e B no mapa, ver a linha da seção desenhada no
      mapa, abrir a seção pela ficha de um campo.
- [ ] **Instalador para Windows** (.exe que roda sem instalar Python).
- [ ] Ajustes finos do estilo clássico da seção a partir de uma figura de referência
      (ex.: Boletim de Geociências da Petrobras).
- [ ] Esquemas: ampliar o dicionário de ferramentas (Halliburton, Baker, Weatherford) com
      esquemas reais desses fabricantes.

## No final — validação científica

- [ ] Avaliação de formação contra valores publicados (poço com Rw conhecido).
- [ ] Seções estratigráficas conferidas com a carta estratigráfica e a geologia do campo.
- [ ] Avaliação em lote por formação (tabela poço × formação) — depende do download em lote.
- [ ] Esquemas: conferir uma amostra maior (ex.: 100 esquemas sorteados) contra o PDF.

## Antes do lançamento

- [ ] Termos de uso dos dados da ANP; DOI (Zenodo); publicar no GitHub (SIAPP-Pocos).
