# Pressões do poço: teste a cabo e teste de formação

*SIAPP 0.38 — bloco 9, item 2.* Código: `motor/pressoes.py`. Os dados entram pelo mesmo arcabouço dos
formulários da ANP (`motor/dados_poco.py`, [`formularios-anp.md`](formularios-anp.md)): lidos no download e ao
abrir o projeto, guardados em `leituras` e `dados_poco`, mostrados na ficha do poço.

## Teste de formação a cabo (SFT, RFT, MDT…)

Pasta "Teste de Formacao a Cabo", arquivo `<poço>_sft-2.dlis` (o nome traz SFT, RFT, MDT, RCI, XPT…).

O DLIS tem **um arquivo lógico por estação**, e o quadro é indexado por **tempo** (`ETIM`, em ms), não por
profundidade. Por isso o leitor de perfis não o abre: ele agora diz isso e aponta para a ficha do poço.

Em cada estação a sonda encosta na parede do poço, faz um ou mais **pré-testes** (retira um pouco de fluido) e
espera a pressão voltar. O canal da sonda (`FPRE` na Halliburton; `BQP`/`PQ`/`SGP`… em outras) registra, em ordem:

1. a **lama** (pressão hidrostática);
2. um aperto ao assentar a sonda;
3. a queda do pré-teste;
4. a recuperação até um **patamar**, que é a pressão da formação;
5. a lama de novo, quando a sonda solta.

O canal `HYDP` dessa ferramenta é a pressão hidráulica da própria sonda e não é usado.

O que o SIAPP calcula em cada estação:

| Valor | Como |
|---|---|
| Hidrostática da lama | mediana dos primeiros e dos últimos 15 s |
| Pressão da formação | mediana dos 20 s do último patamar. O fim do patamar fica antes da subida da sonda soltando: o SIAPP volta no tempo enquanto a pressão muda mais de 1 psi em 5 s (no máximo 30 s) |
| Patamar anterior | quando há mais de um pré-teste: confere a repetição |
| Inclinação | reta dos últimos 30 s do patamar, em psi/min |
| Qualidade | **estabilizada** (até 0,5 psi/min), **quase estável** (até 2), **não estabilizou** (formação fechada ou pouco tempo), **sem vedação ou sem pré-teste** (a pressão nunca cai abaixo da lama) |

Pressão em psi (como o DLIS), convertida para kgf/cm² (como os formulários brasileiros): 1 kgf/cm² = 14,2233 psi.

**Conferência** no 1-BRSA-1304-BA (SFT da Halliburton, 8 estações, 1.681–1.755 m), contra o RFP:

| Prof. (m) | RFP (kgf/cm²) | SIAPP | Inclinação (psi/min) |
|---|---|---|---|
| 1.681,2 | 167,8 | 167,70 | 0,19 |
| 1.684,0 | 167,9 | 167,88 | 0,19 |
| 1.685,8 | 168,1 | 168,03 | 0,41 |
| 1.687,5 | 168,2 | 168,14 | 0,16 |
| 1.717,0 | 171,1 | 171,02 | −0,12 |
| 1.728,5 | 172,3 | 172,22 | 0,52 |
| 1.737,5 | 173,2 | 173,16 | 0,11 |
| 1.754,8 | 175,0 | 174,98 | 0,17 |

## Gradiente, densidade do fluido e contato

Na ficha, cada ponto pode ir para o **grupo A** ou o **grupo B**. Para cada grupo, o SIAPP ajusta a reta
pressão × profundidade (mínimos quadrados) e mostra:

- o gradiente, em kgf/cm²/m e em psi/ft;
- a **densidade equivalente**: 0,1 kgf/cm²/m = 1 g/cm³, e 0,433 psi/ft é a água doce;
- o fluido compatível: gás abaixo de 0,4 g/cm³, óleo até 0,95, água até 1,25;
- R² e o maior resíduo.

Com os dois grupos, o SIAPP mostra a profundidade em que as retas se cruzam, que é o **contato provável** entre os
dois fluidos.

No 1-BRSA-1304-BA, as estações de 1.681–1.688 m (Fm. Água Grande) dão 0,704 g/cm³, compatível com óleo. O
relatório do TFR adota 0,734 g/cm³ para o óleo. As estações de 1.717–1.755 m dão 1,047 g/cm³, compatível com água.
As retas se cruzam a **1.694 m**, logo abaixo da base do arenito que o operador marcou na análise de perfis
(1.693,5 m).

Cuidados:

- profundidade **medida**: em poço desviado o gradiente pede a vertical;
- pontos de unidades sem comunicação hidráulica entre si não devem ir para o mesmo grupo;
- estação "não estabilizou" subestima a pressão.

## Teste de formação (TFR, DST)

Pasta "Teste de Formacao", arquivo `<poço>_TFR.zip`.

O ZIP traz:

- o **relatório de interpretação**, um PDF de texto no formulário padrão da Petrobras;
- os **registros dos manômetros** (`.TPR`: data, hora, tempo em h, pressão em kgf/cm², temperatura em °C, a cada
  10 s);
- às vezes, outros relatórios.

Às vezes esses arquivos estão em ZIPs dentro do ZIP. O SIAPP lê tudo **dentro do ZIP**, sem extrair nada.

Do relatório (rótulo → valor, pela posição na página):

- intervalo, formação e datas;
- pressão estática extrapolada e de fluxo, e as pressões características de cada período;
- vazão, °API e temperatura máxima;
- índice de produtividade, transmissibilidade, mobilidade, **permeabilidade efetiva**, efeito de película (skin)
  e raio de investigação;
- o modelo e os limites;
- a conclusão do intérprete;
- os fluxos, com duração, abertura, vazão, RGO e pressão de fluxo;
- os parâmetros de fluido e de rocha adotados;
- o registrador usado na interpretação.

Dos manômetros: posição, profundidade, sensor, duração, pressão e temperatura máximas. A série é reduzida a
1.500 pontos para o gráfico.

No 1-BRSA-1304-BA: TFR-01 em 1.680–1.684 m, estática de 168,88 kgf/cm² a 1.683,13 m, k = 258 mD, skin 7,
IP 8,4 m³/d/(kgf/cm²), óleo de 36,6 °API, 88,5 m³/d e 83,5 °C. São quatro manômetros de 175 h; o 30768 é o da
interpretação.

## Onde cada dado é usado

| Dado | Onde |
|---|---|
| Pontos de pressão (teste a cabo, RFP e outros formulários, TFR) | Ficha › "Pressões × profundidade": gráfico, tabela, gradiente e contato |
| Curva de cada estação e de cada manômetro | Ficha: botão "curva" e os botões dos manômetros |
| Relatório do TFR | Ficha › "Teste de formação … — relatório" |
| Intervalo do TFR | Avaliação de formação: intervalo candidato (o mesmo do RFP, sem repetir) |
| Temperatura máxima do TFR e da sonda a cabo | Avaliação: referência para o Rw, junto com as do RFP |
| Sigla do poço na operadora (relatório, manômetros, título do DLIS) | Outras grafias do poço |

A pressão e a permeabilidade na viabilidade e na volumetria ficam para o leitor dos dados consolidados.
