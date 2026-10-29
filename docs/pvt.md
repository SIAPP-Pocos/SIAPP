# Análise PVT do laboratório

*SIAPP 0.39 — bloco 9, item 3.* Código: `motor/pvt.py`; uso na viabilidade em `motor/fluidos.py` e
`motor/economia.py`.

## De onde vem

Pasta "Dados De Rochas e Fluidos/PVT" do REATE. São planilhas `.xls` (às vezes `.xlsx`) no formato
Petrobras/ANP, com uma linha por estágio.

As primeiras colunas repetem a **amostra** em toda linha:

- o poço, pela sigla da operadora e pela da ANP;
- o tipo de amostragem e o intervalo;
- a temperatura;
- do tanque: densidade do gás, grau API e RGO;
- a densidade do gás e o grau API da liberação diferencial;
- o fluido.

As colunas são reconhecidas pelo título, não pela posição. "-" ou vazio quer dizer sem dado.

| Planilha | O que traz |
|---|---|
| Liberação diferencial | por pressão (kgf/cm²): Bo, Rs, viscosidade e massa específica do óleo, Bg, densidade do gás, Z, viscosidade do gás |
| Liberação flash | composição (% molar) do óleo estabilizado, do gás e do fluido do reservatório: N₂, CO₂, C1 … C20+, com a densidade e a massa molar do último componente |

A **pressão de saturação** é a do estágio de maior Bo. Acima dela o óleo só se expande; abaixo, libera gás. Acima
da saturação, o SIAPP também calcula a compressibilidade do óleo: co = −(1/Bo)·ΔBo/Δp.

Conferido em 29/10/2026 no 1-BRSA-1304-BA (amostra de fundo, 1.680–1.684 m, 83,7 °C):

- saturação a **155,4 kgf/cm²** (152,4 bar), com **Bo 1,4013** e **Rs 125,37 m³/m³**;
- 38,6 °API e RGO de 117,8 m³/m³ no tanque;
- 36,0 % de C1 no fluido do reservatório.

A estática do TFR, 168,9 kgf/cm², está acima da saturação: o óleo é **subsaturado** no reservatório.

## Onde é usado

| Dado | Onde |
|---|---|
| Amostra, saturação, tabela e gráficos de Bo, Rs e viscosidade × pressão | Ficha › "Análise PVT — liberação diferencial" |
| Composição | Ficha › "Composição do fluido — liberação flash" |
| Grau API do tanque, densidade do gás da liberação diferencial | Viabilidade: valem antes dos dados transcritos e da leitura automática |
| Bo, Rs, Bg | Viabilidade: valores da tabela **interpolados na pressão do reservatório**, no lugar das correlações (Standing, Sutton + Papay), quando o usuário não informa |
| Sigla do poço na operadora | Outras grafias do poço |

Como a viabilidade escolhe:

- **Sem a pressão do reservatório**, Bo e Rs são os da saturação.
- **Bg** só sai da tabela quando a pressão do reservatório está na faixa medida, isto é, abaixo da saturação, onde
  há gás livre. Fora dela, a correlação continua.
- **Um valor informado** pelo usuário sempre vale sobre o medido.
- **Mais de uma análise no campo**: o SIAPP usa a de mais estágios e lista as outras.

## Petrofísica básica

A planilha de petrofísica básica (porosidade e permeabilidade de testemunho) não veio no 1-BRSA-1304-BA. O leitor
fica para quando houver um exemplo baixado.
