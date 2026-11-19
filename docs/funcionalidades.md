# O que o SIAPP faz

A lista completa, aba por aba. O resumo está no [README](../README.md); o passo a passo de cada módulo, nos outros
documentos desta pasta ([índice](README.md)).

| Aba | Funcionalidade |
|---|---|
| **Início** | Os **projetos** (cada um numa pasta, com bacias, números e minimapa; novo, abrir, renomear) e os **módulos** com o estado de cada um e o próximo passo. O **mascote** no canto abre a ajuda **Como usar o SIAPP**, e a xícara **Doe** fica ao lado dos projetos. O guia do REATE e os limites do OCR ficam no menu **Ajuda** |
| **1 Acervo** | Tudo o que se baixa, em sub-abas. **Catálogo do REATE**: Categorias e poços de qualquer uma das 24 bacias terrestres do REATE, em tempo real; árvore de pastas e arquivos de cada poço; download em segundo plano com retomada e registro de procedência. **Cadastro da ANP** (Tabela de Poços dos dados abertos). **Levantamento do acervo**: para uma bacia inteira, quais poços têm perfil digital, só imagem ou nada — pelo conteúdo dos arquivos, lendo 1 KB de cada (o `.tif` do REATE costuma ser LIS de fita), AGP, dados direcionais e esquemas de ferramentas. **Produção da ANP** por poço e por zona, mês a mês, e o sumário do Plano de Desenvolvimento. **Camadas geográficas** oficiais (EPE, ANP, IBGE), guardadas para o QGIS |
| **4 Poços** | Cadastro de poços da ANP no mapa, com filtros e cores pelo acervo, as camadas baixadas e a **ficha do poço**: cadastro, pastas no REATE, arquivos baixados, curvas, AGP, esquemas de ferramentas e dados transcritos |
| **2 Documentos** | Qualquer PDF, TIF (de várias páginas) ou imagem baixada abre na hora, com **visor ampliado** (zoom e arraste; perfil escaneado longo carrega em faixas). Texto embutido ou OCR local, busca sem acento e tolerante a erro de OCR, correção de palavras com um clique e **transcrição assistida**: caixa na imagem, sugestão do OCR, dado salvo com página e caixa como fonte |
| **3 Perfis** | DLIS, LIS e LAS em metros, curvas classificadas por família, gráfico em trilhas, intervalo-alvo e topos marcados no perfil, exportação LAS 2.0 e CSV. **Avaliação de formação** no intervalo-alvo: Vsh (linear/Larionov), φ (densidade, densidade-nêutron, sônico), Sw (Archie/Simandoux), cortes, net pay, N/G, HPV e controle de qualidade, com cada cálculo registrado com seus parâmetros. Topos e litologia do AGP no gráfico; formações do AGP como intervalos candidatos |
| **5 Correlação · 6 Modelo 3D** | **Seção**: **Seção estratigráfica** pelos topos de formação do AGP: até 20 poços, escolhidos um a um ou ao longo de uma linha; em cota ou nivelada num datum; litologia de calha e curva GR; avisos de saltos entre vizinhos; figura em dois estilos — **clássico** (padrões de rocha, carimbo, mapa de localização) e moderno — exportada em SVG, PNG 300 ppp, PDF e CSV. **Bloco 3D**: Poços no espaço e **superfícies de topo** das formações pelos topos do AGP: por campo, em volta de um poço, a bacia inteira ou os poços da seção; interpolação **linear, IDW, spline, krigagem ou tendência + krigagem** (um método para topos, espessuras e propriedades, com explicação de cada parâmetro), escala **reservatório ou bacia**, **comparação dos métodos** pela validação cruzada e mapa de incerteza da krigagem; só dentro do contorno dos poços (área calculada), margem opcional; visor 3D com exagero vertical, unidades liga/desliga, norte e eixos; **trajetória real** dos poços desviados (dados direcionais); **pay da avaliação** ou indícios do AGP ao longo dos poços; **HPV, net pay, N/G, φ ou Sw** no topo da unidade; **bloco fechado** (do terreno a uma base plana, camadas topo a topo ou por espessura, com corte, seção A–A′ e camadas afastadas); **validação cruzada** (quanto o bloco erra sem cada poço) e **prognóstico num ponto** com incerteza; **figura estilo artigo** (SVG, PDF, PNG 300 ppp) e CSV; **saídas**: mapas de topo e isópaca em GeoTIFF/XYZ (SIRGAS 2000 / UTM) para o QGIS, deck **ECLIPSE (.DATA)** para tNavigator/OPM, volumetria preliminar por formação e modelo 3D **.glb** para o PowerPoint; **um clique monta o bloco de um campo**; **produção do campo pela ANP** (por poço e por zona, mês a mês, e o sumário do Plano de Desenvolvimento). É contexto espacial, não resultado |
| **Viabilidade** (Mais) | **Campo × infraestrutura**: distância do campo ao gasoduto, à UPGN, ao projeto de H₂ e à fonte de CO₂ mais próximos e a depleção pelo Plano de Desenvolvimento, num mapa próprio; **viabilidade econômica** auditável (custo do duto ÷ capacidade, três métodos de capacidade, constantes e equações editáveis, memória de cálculo, API e densidade do gás lidos nas pastas de poço); **blocos e campos × infraestrutura** para todas as áreas de uma vez |
| **Comunidade** (Mais) | Exportar as próprias correções, transcrições e interpretações como pacote assinado, importar pacotes de colegas com prévia de conflitos e atualizar a base comunitária ([SIAPP-dados](https://github.com/SIAPP-Perfis/SIAPP-dados)); painel de quanto do acervo está preenchido e de quem contribuiu; biblioteca de interpretações de perfil para comparar e refazer com os mesmos parâmetros |

Tudo fica num **banco do projeto** (`projeto.sqlite`, na pasta do projeto) com o mesmo modelo da base comunitária: cada
dado sabe se foi feito aqui, veio de um pacote ou da base, e qual documento, página e trecho o sustentam.

## Como o código está organizado

```
siapp.py          abre a janela (pywebview) — só isso
ponte/            API da janela, uma parte por aba: valida, chama o motor, devolve dicionários
motor/            toda a lógica, sem nenhuma dependência de interface
  reate.py        cliente do portal REATE (WebDAV): listar, mapear poço, baixar com retomada
  downloads.py    fila de downloads em segundo plano
  banco.py        banco do projeto (SQLite): vocabulário, poços, arquivos, perfis, fatos, pacotes
  pocos.py        nome canônico de poço e cadastro da ANP
  documentos.py   texto de PDF/TIF (embutido ou OCR) e índice de busca (SQLite FTS5)
  vocabulario.py  dicionário de domínio e correção de texto de OCR
  perfis.py       DLIS/LIS/LAS → curvas em metros, famílias, gráfico, exportação
  formatos.py     formato do arquivo pelo conteúdo (DLIS, LIS em fita, TIFF, PDF…)
  levantamento.py acervo de uma bacia sem baixar os arquivos
  avaliacao.py    Vsh, φ, Sw, net pay no intervalo-alvo
  agp.py          AGP da ANP: topos, lama, testes, litologia de calha
  secao.py        seção estratigráfica pelos topos do AGP
  bloco.py        bloco 3D: contorno, triangulação e superfícies de topo pelos topos do AGP
  bloco_solido.py bloco fechado: camadas topo a topo ou por espessura, do terreno à base plana
  interpolacao.py linear, IDW, spline, krigagem, tendência + krigagem; variograma; tirar um poço
  producao.py     produção da ANP por campo: por poço, por zona, ficha, polígono, sumário do PD
  camadas.py      camadas geográficas (EPE, ANP, IBGE BC250 por Range); leitor de shapefile
  viabilidade.py  campo × infraestrutura: polígono, distâncias geodésicas, depleção; blocos/campos em lote
  fluidos.py      grau API e densidade do gás nas pastas de poço (dados transcritos e leitura automática)
  economia.py     custo do duto ÷ capacidade de injeção (simples/PIBIC, espaço poroso, pela molécula), com memória de cálculo
  bloco_validacao.py validação cruzada (deixar um poço de fora) e prognóstico num ponto
  bloco_mapas.py  mapas de topo e isópaca: GeoTIFF e XYZ em SIRGAS 2000 / UTM
  bloco_eclipse.py deck ECLIPSE (.DATA + .GRDECL) do bloco fechado para simuladores
  bloco_volumetria.py volumetria preliminar por formação
  bloco_glb.py    modelo 3D do bloco em glTF binário (.glb)
  utm.py          UTM no SIRGAS 2000 (séries de Krüger)
  bloco_figura.py figura do bloco no estilo artigo (projeção ortográfica, SVG/PDF/PNG)
  direcionais.py  dados direcionais: trajetória do poço (curvatura mínima)
  ferramentas.py  esquemas de ferramentas: tipo de cada corrida e ferramentas (nome + texto/OCR)
  comunidade.py   pacotes de contribuição e base comunitária
  painel.py       preenchimento do acervo e contribuidores
  biblioteca.py   interpretações de perfil compartilhadas
  projeto.py      pasta de projeto: configuração, procedência, escrita atômica
  registro.py     siapp.log
ui/               HTML, CSS e JavaScript puros (ui/js/: um script por aba; ui/vendor/: Leaflet, three.js)
recursos/         dicionário de domínio, famílias de curvas (editáveis) e modelo do OCR
```

A **pasta de projeto** (`Projetos\Projeto principal` para quem instala; `ambiente_teste/` no desenvolvimento) é o contrato entre as partes: tudo o que o
SIAPP baixa e produz fica nela, em formatos abertos (JSON, SQLite, LAS, CSV), com o
histórico de cada ação em `siapp.json`. Detalhes em [`arquitetura.md`](arquitetura.md) e nos documentos de cada módulo ([índice](README.md)).

## Licenças das bibliotecas

Código sob **GNU AGPL-3.0** (ver [`LICENSE`](LICENSE)) — exigência do PyMuPDF,
usado para PDF e OCR.

| Dependência | Uso | Licença |
|---|---|---|
| [pywebview](https://pywebview.flowrl.com/) | janela | BSD-3-Clause |
| [requests](https://requests.readthedocs.io/) | portal REATE | Apache-2.0 |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF, imagem e OCR (motor Tesseract embutido) | AGPL-3.0 |
| [NumPy](https://numpy.org/) | limpeza de imagem antes do OCR | BSD-3-Clause |
| [Leaflet](https://leafletjs.com/) (em `ui/vendor/`) | mapa dos poços | BSD-2-Clause |
| [three.js](https://threejs.org/) 0.160 (em `ui/vendor/three/`) | visor do bloco 3D | MIT |
| [dlisio](https://github.com/equinor/dlisio) | leitura de DLIS e LIS | LGPL-3.0 |
| [lasio](https://github.com/kinverarity1/lasio) | leitura e escrita de LAS | MIT |
| [Tesseract `por.traineddata`](https://github.com/tesseract-ocr/tessdata_best) | modelo de português (baixado na 1ª vez) | Apache-2.0 |
| Lista de palavras do [pyspellchecker](https://github.com/barrust/pyspellchecker) (em `recursos/palavras_pt.txt.gz`) | dicionário de português do texto dos documentos | MIT |
