# Petrofísica básica de testemunho (0.48)

Lê as planilhas da pasta `Dados de Rochas e Fluidos/PETROFISICA_BASICA` do REATE e põe os dados na ficha do poço.
Código: `motor/petrofisica.py`.

## O que o REATE traz (visto no 1-ALG-1-RN)

| Arquivo | Conteúdo |
|---|---|
| `1ALG 0001  RN-Petrofisica Basica.xls` | Uma linha por plug: unidade, poço Petrobras, poço ANP, tipo de amostra, direção, número, profundidade, porosidade (%), densidade, permeabilidade longitudinal (mD), pressão (psi). Valores em **texto com vírgula decimal** (`"2021,1"`, `"206,39"`). |
| `00610.119452.xls` | A mesma tabela, com a coluna extra "Data Análise". O nome é um número de protocolo: o SIAPP reconhece pela **pasta**. |
| `1-ALG-0001-RN_COREGAMA.xls` | Gama do testemunho: poço, número do testemunho (`TEST`), topo e base do testemunho e, em cada profundidade analisada (de 0,2 em 0,2 m), `RAIOS_GAMA_API`. |

## Como é lido

- `tipo_pelo_nome`: `.xls`/`.xlsx` na pasta `PETROFISICA_BASICA`; com `COREGAMA` no nome é gama, senão plugs.
- As colunas dos plugs são achadas pelo **cabeçalho** (sem acento, sem pontuação); a ordem e as colunas extras podem
  variar entre poços. Uma coluna que o SIAPP não conhece fica em `extra.colunas` com o nome original.
- Números: `206,39` → 206,39; `1.234,5` → 1234,5; célula vazia → sem dado.
- Itens gravados em `dados_poco`:
  - `plug_testemunho`: `prof_topo` = profundidade, `valor` = porosidade (%), `nome` = "número direção" (ex.: "1 VH1"),
    `texto` = tipo de amostra; em `extra`: permeabilidade, densidade, pressão, direção, número, unidade da operadora, data.
  - `gama_testemunho`: `prof_topo` = profundidade analisada, `valor` = gama (API), `nome` = número do testemunho; em
    `extra`: testemunho, topo e base.
- Duas planilhas com os mesmos plugs (como as duas do 1-ALG-1-RN) ficam **uma vez** na ficha, com a outra em "também em".
  Plugs na mesma profundidade, mas de amostras diferentes (ex.: VH1 e VV), continuam separados.

## Limites (o que o SIAPP não afirma)

- **A unidade da densidade não vem na planilha.** Valores perto de 2,65 sugerem densidade de grãos em g/cm³, mas isso
  é leitura nossa; a ficha avisa e o dado fica sem unidade.
- É medida de **plug**, não de perfil: serve de referência para conferir a porosidade do perfil, não a substitui.
  Comparar plug × perfil (profundidade, escala de amostragem) é um passo à parte, ainda não feito.
- O gama do testemunho serve para **casar a profundidade** do testemunho com a do perfil; o SIAPP mostra os dados,
  mas ainda não calcula o deslocamento.
- Só um poço foi visto (1-ALG-1-RN, com um único plug); outros poços (são 162 com esse tipo de planilha) podem trazer
  colunas ou formatos diferentes. Se algum não abrir, mande a planilha para o leitor ser ajustado.

## Testes

`tests/test_petrofisica.py` usa planilhas **sintéticas** (`tests/petrofisica_util.py`): cabeçalhos e formatos como os
do REATE, valores inventados. Os arquivos originais do REATE não entram no git.
