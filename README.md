# SIAPP — Sistema Integrado de Aquisição e Processamento de Perfis

[![testes](https://github.com/SIAPP-Pocos/siapp/actions/workflows/testes.yml/badge.svg)](https://github.com/SIAPP-Pocos/siapp/actions/workflows/testes.yml)
[![licença: AGPL-3.0](https://img.shields.io/badge/licen%C3%A7a-AGPL--3.0-blue)](LICENSE)
![versão](https://img.shields.io/badge/vers%C3%A3o-0.25.0-informational)

Ferramenta aberta para transformar o acervo **público** de dados de poços da ANP
(portal [REATE](https://reate.cprm.gov.br/anp/TERRESTRE), ANP/CPRM) em dados
organizados, pesquisáveis e prontos para análise — sem software comercial.

> **Estado:** em desenvolvimento ativo (v0.25). A interface e os formatos ainda
> podem mudar entre versões; a 1.0 sai no lançamento público.

---

## Por que existe

O acervo do REATE é público e gratuito, mas difícil de usar na prática:
formatos binários legados (DLIS, LIS), documentos escaneados, nomes de pasta
sem padrão e nenhum índice do que existe em cada poço. O SIAPP reduz esse
custo de entrada, e o repositório irmão
[`siapp-dados`](https://github.com/SIAPP-Pocos/SIAPP-dados) reúne as correções feitas pela comunidade para
que cada usuário receba os dados já tratados.

## O que já faz

| Aba | Funcionalidade |
|---|---|
| **Início** | O que é cada pasta e sufixo do REATE, qual arquivo baixar para cada finalidade, limites do OCR e os números do projeto |
| **Catálogo** | Categorias e poços de qualquer uma das 24 bacias terrestres do REATE, em tempo real; árvore de pastas e arquivos de cada poço; download em segundo plano com retomada e registro de procedência |
| **Mapa** | Cadastro oficial de poços da ANP (dados abertos) no mapa, com filtros, e a **ficha do poço**: cadastro, pastas no REATE, arquivos baixados, curvas e dados transcritos. **Levantamento do acervo**: para uma bacia inteira, quais poços têm perfil digital, só imagem ou nada — pelo conteúdo dos arquivos, lendo 1 KB de cada (o `.tif` do REATE costuma ser LIS de fita), com lista de curvas opcional e exportação CSV. Lê o **AGP** da ANP (topos de formação, lama, testes, litologia de calha) de cada poço que o tiver. **Esquemas de ferramentas**: o que é cada arquivo de perfil do poço (perfilagem convencional, teste de formação a cabo, imagem, RMN, cimentação…), pelo nome e pela leitura do PDF (texto ou OCR), com as ferramentas reconhecidas **Camadas geográficas** de fontes oficiais (gasodutos de transporte e escoamento e termelétricas da EPE, **unidades e projetos de hidrogênio verde**, campos e blocos exploratórios da ANP, dutos, portos e cidades do IBGE), guardadas para o QGIS e **desenhadas no mapa**; **campo × infraestrutura**: distância do campo ao gasoduto, à UPGN, ao projeto de H₂ e à fonte de CO₂ mais próximos, e a depleção pelo Plano de Desenvolvimento |
| **Documentos** | Qualquer PDF, TIF (de várias páginas) ou imagem baixada abre na hora, com **visor ampliado** (zoom e arraste; perfil escaneado longo carrega em faixas). Texto embutido ou OCR local, busca sem acento e tolerante a erro de OCR, correção de palavras com um clique e **transcrição assistida**: caixa na imagem, sugestão do OCR, dado salvo com página e caixa como fonte |
| **Perfis** | DLIS, LIS e LAS em metros, curvas classificadas por família, gráfico em trilhas, intervalo-alvo e topos marcados no perfil, exportação LAS 2.0 e CSV. **Avaliação de formação** no intervalo-alvo: Vsh (linear/Larionov), φ (densidade, densidade-nêutron, sônico), Sw (Archie/Simandoux), cortes, net pay, N/G, HPV e controle de qualidade, com cada cálculo registrado com seus parâmetros. Topos e litologia do AGP no gráfico; formações do AGP como intervalos candidatos |
| **Seção** | **Seção estratigráfica** pelos topos de formação do AGP: até 20 poços, escolhidos um a um ou ao longo de uma linha; em cota ou nivelada num datum; litologia de calha e curva GR; avisos de saltos entre vizinhos; figura em dois estilos — **clássico** (padrões de rocha, carimbo, mapa de localização) e moderno — exportada em SVG, PNG 300 ppp, PDF e CSV |
| **Bloco 3D** | Poços no espaço e **superfícies de topo** das formações pelos topos do AGP: por campo, em volta de um poço, a bacia inteira ou os poços da seção; interpolação **linear, IDW, spline, krigagem ou tendência + krigagem** (um método para topos, espessuras e propriedades, com explicação de cada parâmetro), escala **reservatório ou bacia**, **comparação dos métodos** pela validação cruzada e mapa de incerteza da krigagem; só dentro do contorno dos poços (área calculada), margem opcional; visor 3D com exagero vertical, unidades liga/desliga, norte e eixos; **trajetória real** dos poços desviados (dados direcionais); **pay da avaliação** ou indícios do AGP ao longo dos poços; **HPV, net pay, N/G, φ ou Sw** no topo da unidade; **bloco fechado** (do terreno a uma base plana, camadas topo a topo ou por espessura, com corte, seção A–A′ e camadas afastadas); **validação cruzada** (quanto o bloco erra sem cada poço) e **prognóstico num ponto** com incerteza; **figura estilo artigo** (SVG, PDF, PNG 300 ppp) e CSV; **saídas**: mapas de topo e isópaca em GeoTIFF/XYZ (SIRGAS 2000 / UTM) para o QGIS, deck **ECLIPSE (.DATA)** para tNavigator/OPM, volumetria preliminar por formação e modelo 3D **.glb** para o PowerPoint; **um clique monta o bloco de um campo**; **produção do campo pela ANP** (por poço e por zona, mês a mês, e o sumário do Plano de Desenvolvimento). É contexto espacial, não resultado |
| **Comunidade** | Exportar as próprias correções e transcrições como pacote assinado, importar pacotes de colegas com prévia de conflitos e atualizar a base comunitária ([SIAPP-dados](https://github.com/SIAPP-Pocos/SIAPP-dados)) |

Tudo fica num **banco do projeto** (`ambiente_teste/projeto.sqlite`) com o mesmo modelo
da base comunitária: cada dado sabe se foi feito aqui, veio de um pacote ou da base, e
qual documento, página e trecho o sustentam.

## Como usar (Windows)

1. Instale o Python 3.10 ou mais novo ([python.org](https://www.python.org/downloads/)).
2. Baixe ou clone este repositório.
3. Dê dois cliques em **`iniciar.bat`**.

Na primeira execução, o `iniciar.bat` encontra um Python válido, cria um ambiente
isolado (`.venv`) e instala as dependências. No primeiro documento escaneado, o
SIAPP baixa o modelo de português do OCR (~8 MB); na aba Mapa, a Tabela de Poços da
ANP (~12 MB).

Os dados ficam sempre em `ambiente_teste/`, ao lado do aplicativo. O guia de teste
passo a passo está em [`docs/guia-de-teste.md`](docs/guia-de-teste.md).

## Como funciona

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
  viabilidade.py  campo × infraestrutura: polígono, distâncias geodésicas, depleção
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
  projeto.py      pasta de projeto: configuração, procedência, escrita atômica
  registro.py     siapp.log
ui/               HTML, CSS e JavaScript puros (ui/js/: um script por aba; ui/vendor/: Leaflet, three.js)
recursos/         dicionário de domínio, famílias de curvas (editáveis) e modelo do OCR
```

A **pasta de projeto** (`ambiente_teste/`) é o contrato entre as partes: tudo o que o
SIAPP baixa e produz fica nela, em formatos abertos (JSON, SQLite, LAS, CSV), com o
histórico de cada ação em `siapp.json`. Detalhes em [`docs/arquitetura.md`](docs/arquitetura.md),
[`docs/comunidade.md`](docs/comunidade.md), [`docs/perfis.md`](docs/perfis.md),
[`docs/levantamento.md`](docs/levantamento.md), [`docs/avaliacao.md`](docs/avaliacao.md),
[`docs/agp.md`](docs/agp.md), [`docs/secao.md`](docs/secao.md), [`docs/ferramentas.md`](docs/ferramentas.md) e [`docs/bloco.md`](docs/bloco.md).

## Dados e procedência

- **Nenhum arquivo original do REATE é redistribuído** por este repositório. O SIAPP
  baixa direto do portal público.
- Todo arquivo baixado é registrado com o caminho de origem no portal e a data
  (`bruto/registro_downloads.json`).
- Texto obtido por **OCR serve para encontrar páginas, não para fornecer números**:
  em teste com documento real, 6 de 18 profundidades foram lidas erradas. A
  correção automática nunca altera números; números entram no banco só por
  transcrição conferida na imagem. Ver [`docs/ocr.md`](docs/ocr.md).
- Todo dado transcrito guarda a fonte: SHA-256 e caminho do documento no REATE,
  página e a caixa desenhada sobre a imagem.

## Desenvolvimento

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Os testes não acessam a internet: o portal REATE, o GitHub e a ANP são simulados,
inclusive com falhas (conexão caindo, servidor que ignora retomada, arquivo truncado).
Os testes da interface abrem `ui/` num Chromium sem tela, ligado à API Python de verdade;
rodam se o Playwright estiver instalado (`pip install playwright && playwright install chromium`).
Para conferir a leitura de um DLIS real: `SIAPP_DLIS_REAL=caminho/do/arquivo.dlis pytest -k real`. Contribuições:
[`CONTRIBUTING.md`](CONTRIBUTING.md). Histórico: [`CHANGELOG.md`](CHANGELOG.md).

## Licença

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

## Como citar

Ver [`CITATION.cff`](CITATION.cff) — o GitHub mostra o botão "Cite this repository".

## Autoria

Desenvolvido por **Ruan da Silva Nobre** (Engenharia de Petróleo, UFAL) no âmbito
do Programa Institucional de Bolsas de Iniciação Científica (PIBIC), sob
orientação da Profa. Zenilda Vieira Batista.
