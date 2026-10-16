# SIAPP — Sistema Integrado de Aquisição e Processamento de Perfis

[![testes](https://github.com/SIAPP-Pocos/siapp/actions/workflows/testes.yml/badge.svg)](https://github.com/SIAPP-Pocos/siapp/actions/workflows/testes.yml)
[![licença: AGPL-3.0](https://img.shields.io/badge/licen%C3%A7a-AGPL--3.0-blue)](LICENSE)
![versão](https://img.shields.io/badge/vers%C3%A3o-0.6.0-informational)

Ferramenta aberta para transformar o acervo **público** de dados de poços da ANP
(portal [REATE](https://reate.cprm.gov.br/anp/TERRESTRE), ANP/CPRM) em dados
organizados, pesquisáveis e prontos para análise — sem software comercial.

> **Estado:** em desenvolvimento ativo (v0.6). A interface e os formatos ainda
> podem mudar entre versões.

---

## Por que existe

O acervo do REATE é público e gratuito, mas difícil de usar na prática:
formatos binários legados (DLIS, LIS), documentos escaneados, nomes de pasta
sem padrão e nenhum índice do que existe em cada poço. O SIAPP reduz esse
custo de entrada, e o repositório irmão
[`siapp-dados`](https://github.com/SIAPP-Pocos/SIAPP-dados) reúne as correções feitas pela comunidade para
que cada usuário receba os dados já tratados.

## O que já faz

| Etapa | Funcionalidade |
|---|---|
| **Catálogo** | Lista categorias e poços de qualquer uma das 24 bacias terrestres do REATE, em tempo real; junta categorias divididas em subpastas "parte" |
| **Explorar poço** | Mostra a árvore de pastas e arquivos de um poço, com tamanhos, antes de baixar |
| **Download** | Baixa os arquivos escolhidos em segundo plano, com retomada após queda de conexão, cancelamento e registro de procedência |
| **Documentos** | Extrai o texto de PDFs e TIFs — direto, quando o PDF tem texto; por OCR local, quando é escaneado |
| **Busca** | Busca em todos os documentos, sem acento, tolerante a erros de OCR, com a página aberta e o termo destacado |
| **Correção** | Dicionário de domínio corrige erros de OCR; o usuário corrige palavras com um clique; o OCR original nunca é apagado |

## Como usar (Windows)

1. Instale o Python 3.10 ou mais novo ([python.org](https://www.python.org/downloads/)).
2. Baixe ou clone este repositório.
3. Dê dois cliques em **`iniciar.bat`**.

Na primeira execução, o `iniciar.bat` encontra um Python válido, cria um ambiente
isolado (`.venv`) e instala as dependências. No primeiro documento escaneado, o
SIAPP baixa o modelo de português do OCR (~8 MB).

Os dados ficam sempre em `ambiente_teste/`, ao lado do aplicativo. O guia de teste
passo a passo está em [`docs/guia-de-teste.md`](docs/guia-de-teste.md).

## Como funciona

```
siapp.py          janela (pywebview) + ponte JavaScript ↔ Python — camada fina
motor/            toda a lógica, sem nenhuma dependência de interface
  reate.py        cliente do portal REATE (WebDAV): listar, mapear poço, baixar
  downloads.py    fila de downloads em segundo plano
  documentos.py   texto de PDF/TIF (embutido ou OCR) e índice de busca (SQLite FTS5)
  vocabulario.py  dicionário de domínio e correção de texto de OCR
  projeto.py      pasta de projeto: configuração, catálogo, procedência
ui/               interface em HTML, CSS e JavaScript puros
recursos/         dicionário de domínio (editável) e modelo de idioma do OCR
```

A **pasta de projeto** (`ambiente_teste/`) é o contrato entre as partes: tudo o
que o SIAPP baixa e produz fica nela, em formatos abertos (JSON, SQLite), com o
histórico de cada ação em `siapp.json`. Detalhes em
[`docs/arquitetura.md`](docs/arquitetura.md).

## Dados e procedência

- **Nenhum arquivo original do REATE é redistribuído** por este repositório. O SIAPP
  baixa direto do portal público.
- Todo arquivo baixado é registrado com o caminho de origem no portal e a data
  (`bruto/registro_downloads.json`).
- Texto obtido por **OCR serve para encontrar páginas, não para fornecer números**:
  em teste com documento real, 6 de 18 profundidades foram lidas erradas. A
  correção automática nunca altera números. Ver [`docs/ocr.md`](docs/ocr.md).

## Desenvolvimento

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Os testes não acessam a internet: o portal REATE é simulado, inclusive com falhas
(conexão caindo, servidor que ignora retomada, arquivo truncado). Contribuições:
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
| [Tesseract `por.traineddata`](https://github.com/tesseract-ocr/tessdata_best) | modelo de português (baixado na 1ª vez) | Apache-2.0 |

## Como citar

Ver [`CITATION.cff`](CITATION.cff) — o GitHub mostra o botão "Cite this repository".

## Autoria

Desenvolvido por **Ruan da Silva Nobre** (Engenharia de Petróleo, UFAL) no âmbito
do Programa Institucional de Bolsas de Iniciação Científica (PIBIC), sob
orientação da Profa. Zenilda Vieira Batista.
