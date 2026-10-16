# SIAPP — Sistema Integrado de Aquisição e Processamento de Perfis

[![testes](https://github.com/SIAPP-Pocos/siapp/actions/workflows/testes.yml/badge.svg)](https://github.com/SIAPP-Pocos/siapp/actions/workflows/testes.yml)
[![licença: AGPL-3.0](https://img.shields.io/badge/licen%C3%A7a-AGPL--3.0-blue)](LICENSE)
![versão](https://img.shields.io/badge/vers%C3%A3o-0.14.1-informational)

Ferramenta aberta para transformar o acervo **público** de dados de poços da ANP
(portal [REATE](https://reate.cprm.gov.br/anp/TERRESTRE), ANP/CPRM) em dados
organizados, pesquisáveis e prontos para análise — sem software comercial.

> **Estado:** em desenvolvimento ativo (v0.14). A interface e os formatos ainda
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
| **Mapa** | Cadastro oficial de poços da ANP (dados abertos) no mapa, com filtros, e a **ficha do poço**: cadastro, pastas no REATE, arquivos baixados, curvas e dados transcritos. **Levantamento do acervo**: para uma bacia inteira, quais poços têm perfil digital, só imagem ou nada — pelo conteúdo dos arquivos, lendo 1 KB de cada (o `.tif` do REATE costuma ser LIS de fita), com lista de curvas opcional e exportação CSV. Lê o **AGP** da ANP (topos de formação, lama, testes, litologia de calha) de cada poço que o tiver |
| **Documentos** | Qualquer PDF, TIF (de várias páginas) ou imagem baixada abre na hora, com **visor ampliado** (zoom e arraste; perfil escaneado longo carrega em faixas). Texto embutido ou OCR local, busca sem acento e tolerante a erro de OCR, correção de palavras com um clique e **transcrição assistida**: caixa na imagem, sugestão do OCR, dado salvo com página e caixa como fonte |
| **Perfis** | DLIS, LIS e LAS em metros, curvas classificadas por família, gráfico em trilhas, intervalo-alvo e topos marcados no perfil, exportação LAS 2.0 e CSV. **Avaliação de formação** no intervalo-alvo: Vsh (linear/Larionov), φ (densidade, densidade-nêutron, sônico), Sw (Archie/Simandoux), cortes, net pay, N/G, HPV e controle de qualidade, com cada cálculo registrado com seus parâmetros. Topos e litologia do AGP no gráfico; formações do AGP como intervalos candidatos |
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
  comunidade.py   pacotes de contribuição e base comunitária
  projeto.py      pasta de projeto: configuração, procedência, escrita atômica
  registro.py     siapp.log
ui/               HTML, CSS e JavaScript puros (ui/js/: um script por aba; ui/vendor/: Leaflet)
recursos/         dicionário de domínio, famílias de curvas (editáveis) e modelo do OCR
```

A **pasta de projeto** (`ambiente_teste/`) é o contrato entre as partes: tudo o que o
SIAPP baixa e produz fica nela, em formatos abertos (JSON, SQLite, LAS, CSV), com o
histórico de cada ação em `siapp.json`. Detalhes em [`docs/arquitetura.md`](docs/arquitetura.md),
[`docs/comunidade.md`](docs/comunidade.md), [`docs/perfis.md`](docs/perfis.md),
[`docs/levantamento.md`](docs/levantamento.md), [`docs/avaliacao.md`](docs/avaliacao.md) e
[`docs/agp.md`](docs/agp.md).

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
| [dlisio](https://github.com/equinor/dlisio) | leitura de DLIS e LIS | LGPL-3.0 |
| [lasio](https://github.com/kinverarity1/lasio) | leitura e escrita de LAS | MIT |
| [Tesseract `por.traineddata`](https://github.com/tesseract-ocr/tessdata_best) | modelo de português (baixado na 1ª vez) | Apache-2.0 |

## Como citar

Ver [`CITATION.cff`](CITATION.cff) — o GitHub mostra o botão "Cite this repository".

## Autoria

Desenvolvido por **Ruan da Silva Nobre** (Engenharia de Petróleo, UFAL) no âmbito
do Programa Institucional de Bolsas de Iniciação Científica (PIBIC), sob
orientação da Profa. Zenilda Vieira Batista.
