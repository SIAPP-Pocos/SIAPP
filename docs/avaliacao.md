# Avaliação de formação

Aba **Perfis → Avaliação de formação no intervalo-alvo**. Calcula argilosidade, porosidade,
saturação de água e net pay **só dentro dos intervalos-alvo** do poço (marcados arrastando
sobre o gráfico ou transcritos de um documento). Código: `motor/avaliacao.py`.

## Curvas

| Papel | Famílias | |
|---|---|---|
| GR | GR | obrigatória |
| Rt | resistividade profunda (AT90, ILD, LLD, HDRS…) | obrigatória |
| RHOB, NPHI, DT | densidade, nêutron, sônico | pelo menos uma, conforme o método de φ |
| Cáliper, Broca, DRHO | | controle de qualidade |

O SIAPP sugere a curva de cada papel pela visão padrão (a de maior preferência da família;
empate: a com mais dados) e você pode trocar. Todas vão para uma grade comum com o passo do
GR (`perfis.reamostrar`; falhas maiores que 2,5 passos ficam nulas). Unidades: NPHI em % vira
fração; densidade em kg/m³ vira g/cm³; Δt em µs/m vira µs/pé; cáliper em mm/cm vira polegada.

## Fórmulas

| Grandeza | Método | Fórmula |
|---|---|---|
| Índice de GR | — | IGR = (GR − GR_limpo) / (GR_argila − GR_limpo), entre 0 e 1 |
| Vsh | linear | Vsh = IGR |
| | Larionov, rochas terciárias | Vsh = 0,083 · (2^(3,7·IGR) − 1) |
| | Larionov, rochas mais antigas | Vsh = 0,33 · (2^(2·IGR) − 1) |
| φ | densidade | φD = (ρma − ρb) / (ρma − ρf) |
| | densidade-nêutron | (φD + φN)/2; com efeito de gás (φN < φD): √((φD² + φN²)/2) |
| | sônico (Wyllie) | φS = (Δt − Δtma) / (Δtf − Δtma) |
| | correção de argila (opcional) | φe = φ − Vsh · φsh |
| Sw | Archie | Sw = (a·Rw / (φ^m · Rt))^(1/n) |
| | Simandoux (n = 2) | Sw = a·Rw/(2φ^m) · [√((Vsh/Rsh)² + 4φ^m/(a·Rw·Rt)) − Vsh/Rsh] |

**Cortes:** reservatório = Vsh ≤ corte e φ ≥ corte; **net pay** = reservatório e Sw ≤ corte.
**HPV** (coluna de hidrocarboneto) = Σ φ·(1 − Sw)·Δh no net pay, em metros.

**Controle de qualidade:** arrombamento quando cáliper − broca passa do limite (padrão 1 pol;
sem curva de broca, informe o diâmetro); densidade suspeita quando |DRHO| > 0,15 g/cm³. As
amostras suspeitas **não são excluídas** — o resumo mostra quantos metros do net pay caem nelas.

## Parâmetros automáticos

Deixados em branco, o SIAPP estima e registra como estimou:

| Parâmetro | Estimativa |
|---|---|
| GR limpo / GR argila | percentis 5 e 95 do GR dentro dos intervalos |
| método de φ | densidade-nêutron se houver RHOB e NPHI; senão densidade; senão sônico |
| Rsh (Simandoux) | mediana de Rt onde Vsh ≥ 0,8 nos intervalos |
| passo | o do GR |

**Rw não tem estimativa automática**: depende da água de formação (análise de água, SP ou
Pickett) — o padrão 0,05 ohm·m é só um ponto de partida e deve ser trocado.

## Registro

Cada cálculo grava em `ambiente_teste/execucoes/`:

- `avaliacao_<poço>_<data-hora>.json` — arquivo de origem (com SHA-256), curvas usadas,
  métodos, **todos os parâmetros** (e quais foram automáticos), passo, resumo por intervalo,
  versão do SIAPP e as fórmulas;
- `avaliacao_<…>.npz` — as curvas calculadas (VSH, PHI, SW, RES, PAY, QC).

As avaliações anteriores ficam listadas no painel; clicar numa delas mostra o resultado no
gráfico e retoma os parâmetros. **Exportar** grava CSV ou LAS 2.0 em `exportacoes/<poço>/`
(só as profundidades dentro dos intervalos).

**Compartilhar na biblioteca** (0.35) leva a avaliação para Comunidade › Biblioteca de
interpretações, com título e comentário: o arquivo (hash), as curvas, os métodos, os parâmetros e
o resumo de cada intervalo — sem as curvas calculadas. De lá, colegas comparam com as deles e
refazem o cálculo no mesmo arquivo. Ver `docs/comunidade.md`.

## Limites desta versão

- Uma litologia por cálculo (ρma e Δtma únicos): intervalos com arenito e carbonato pedem
  cálculos separados.
- Nêutron tratado como porosidade na matriz informada (sem correção de matriz calcária).
- Sem correção ambiental nem de invasão (Rt = resistividade profunda medida).
- Simandoux só na forma fechada com n = 2.
