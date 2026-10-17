# Bloco 3D

Os poços no espaço, as **superfícies de topo** das unidades e o **bloco fechado** (0.20), a partir dos topos que a
operadora registrou no AGP. Código: `motor/bloco.py` (modelo) e `ui/js/bloco3d.js`
(visor, com [three.js](https://threejs.org/) em `ui/vendor/three/`, licença MIT).

> **O bloco é contexto espacial, não resultado.** Entre os poços, a superfície é
> interpolação; com poços quase alinhados, a direção transversal não tem dado nenhum. O
> resultado quantitativo continua sendo a seção (aba Seção) e a avaliação (aba Perfis).
> (Especificação Funcional, M4.)

## Escolha dos poços

Só entram poços com topos litoestratigráficos no AGP lido e coordenadas no cadastro da ANP:

- **um campo** (do cadastro): margem fica 0 — margem infla a área de um campo delimitado;
- **em volta de um poço**, num raio em km;
- **todos da bacia**: bloco regional (na Potiguar, Cat. 1 lida: 429 poços, 12.395 km²);
- **os poços da aba Seção**; e mais um a um.

Um poço muito longe de todos os outros (mais de 100 km e 5× a distância mediana ao centro)
fica de fora, com aviso — na Potiguar, o AGP do `1-BRSA-264-ES` está na pasta de um poço do RN.

## Como as superfícies são feitas

| Passo | Regra |
|---|---|
| Plano | lat/lon → km num plano local (equiretangular na latitude média; 111,2 km por grau de latitude) |
| Contorno | contorno convexo dos poços que têm a unidade (cadeia monótona); **área pela fórmula do shoelace**, mostrada no resumo e na figura |
| Dentro do contorno | **interpolação linear** nos triângulos de Delaunay dos poços (Bowyer–Watson) |
| Margem (opcional) | na faixa entre o contorno e o contorno + margem: valor do **poço mais próximo** |
| Fora | nulo (NaN, de propósito): nada é desenhado nem exportado |
| Distância máxima (opcional) | esconde a superfície onde o poço mais próximo com a unidade está além dela — útil no bloco regional |
| Poucos poços | menos de 3, ou poços quase alinhados (largura do contorno < 4% do comprimento): sem superfície, só os topos nos poços, com aviso |

Sem margem nem corte por distância, a janela desenha a própria malha de triângulos (a
interpolação linear exata, com a borda reta no contorno). Com margem ou corte, desenha a
grade (resolução escolhida; 160 células no lado maior por padrão).

A **ordem das unidades** é a estratigráfica (posição média da unidade dentro de cada poço),
a mesma da seção, e a **cor** é a mesma da seção (`slot` em `recursos/estratigrafia.json`).

### Avisos

- **Superfícies que se cruzam**: onde a superfície de uma unidade mais funda passa acima da
  mais rasa em mais de 1% da área. Acontece quando as duas vêm de conjuntos diferentes de
  poços — pouco controle ali.
- **Poço desviado**: com os *Dados Direcionais* lidos (0.19), segue a trajetória e cada topo
  fica na posição real; sem eles, vertical na posição da cabeça, com aviso. A **cota** dos
  topos é sempre a do AGP.

## Visor

- Arrastar gira; roda do mouse aproxima; botão direito desloca. Vistas prontas: oblíqua,
  de cima (mapa), do sul, do oeste.
- **Exagero vertical** (1–60×; o inicial faz o relevo ocupar ~1/4 da largura), opacidade,
  nomes dos poços (desligados de saída com mais de 40 poços), caixa com eixos (distância em
  km a partir do canto SW; cota em m), seta do norte.
- Cada unidade liga e desliga (superfície e marcas nos poços). Passar o mouse num poço ou
  num topo mostra o poço, a unidade, a profundidade e a cota.

## Saídas

- **Registro** de cada bloco em `ambiente_teste/execucoes/bloco_<data-hora>.json`: poços,
  topos usados, superfícies (grade), contorno, área e parâmetros. **Blocos anteriores**
  reabre sem recalcular.
- **PNG** da vista atual em ~2,5× a resolução da tela, com rótulos, norte, legenda das
  unidades e carimbo (poços, área do contorno, exagero, canto SW, fonte AGP/ANP, versão do
  SIAPP, autor, data), em `exportacoes/blocos/`.
- **CSV** (`;` e vírgula decimal): `<id>_topos.csv` (poço, lat, lon, x, y, unidade, topo,
  cotas) e `<id>_superficies.csv` (cada nó da grade com valor: x, y, lat, lon e a cota do
  topo de cada unidade).

## Trajetórias (0.19)

Os arquivos da pasta *Dados Direcionais* (`motor/direcionais.py`) vêm em cinco leiautes; de
todos, o SIAPP usa prof. medida, inclinação, azimute e prof. vertical, e calcula os
afastamentos pela **curvatura mínima** (conferido em 36 arquivos da Potiguar: afastamentos
iguais aos do próprio arquivo, ao centímetro). Arquivo de outro poço na pasta (o do
`7-FP-46D-BA` está na pasta do `7-FP-406-RN`) é reconhecido pelo cabeçalho e descartado.
Afastamento menor que 5 m: tratado como vertical.

## Ao longo dos poços (0.19)

- **Pay (avaliação de formação)**: a avaliação mais recente de cada poço (aba Perfis), nas
  classes do requisito 7.3 — não reservatório, reservatório sem pay, pay e **pay com indício
  de gás** (pay dentro de um intervalo de indício de gás do AGP; o SIAPP não infere gás pelas
  curvas). Em blocos de 2 m, cada bloco com a classe mais prioritária presente: um pay de 40
  cm continua aparecendo (decimação não pode ser cega).
- **Indícios (AGP)**: óleo e gás, como registrados pela operadora.

## Propriedade no topo (0.19)

HPV, net pay, N/G, φ média no pay ou Sw média no pay, do intervalo avaliado que corresponde
à unidade (mesmo nome, ou metade do intervalo dentro do topo–base da unidade no poço).
Interpolação linear entre os poços avaliados (3 ou mais, não alinhados), dentro do contorno
deles e da superfície; fora, cinza. Escala azul de um tom (claro = menor); com uma
propriedade no topo, as outras superfícies ficam translúcidas. É contexto: um mapa de HPV com
poucos poços não é um mapa de reservas.

## Figura estilo artigo (0.19)

`motor/bloco_figura.py`: a vista atual do visor (azimute, elevação, exagero, unidades
ligadas, trilha, propriedade) em **projeção ortográfica**, pelo algoritmo do pintor, com
sombreamento por face, fonte serifada, moldura, legenda, escala de cor, seta do norte e as
notas de método e fonte. SVG (editável), PDF (vetorial) e PNG 300 ppp em
`exportacoes/blocos/<id>_figura.*`.

## Bloco fechado (0.20)

`motor/bloco_solido.py`. A mesma montagem faz os dois modos — **Superfícies** e **Bloco
fechado** —, trocados pelos botões em cima do visor, sem montar de novo. O bloco fechado é o
volume inteiro dentro do contorno convexo dos poços (mais a margem), do **terreno** a uma
**base plana**, fatiado nas unidades, com **paredes retas** (a malha recorta as células da
grade pelo contorno).

| Passo | Regra |
|---|---|
| Limite *k* | o topo da unidade *k* na ordem estratigráfica; o último é a base da última unidade |
| Num poço | o limite *k* é observado se o poço chegou a uma unidade de índice ≥ *k*: é o topo da primeira delas. **Unidade ausente = espessura 0** (o poço passou pela posição dela) |
| Espessura | limite *k* − limite *k*+1, quando os dois foram observados; poço que parou antes, ou base não atingida na última unidade: **desconhecida** (não entra como zero) |
| Empilhamento | um **limite de referência** (o mais fundo observado em ≥ 90% dos poços) é interpolado direto; os de cima somam espessuras, os de baixo subtraem. Espessura ≥ 0: **as camadas nunca se cruzam**, e passam pelos topos do AGP nos poços |
| Interpolação | linear nos triângulos de Delaunay dos poços com o dado; fora do contorno deles, o valor do ponto mais próximo da borda (linear entre os dois poços da aresta: contínuo) — **extrapolado, mais claro** |
| Terreno | cota altimétrica do cadastro da ANP (0,0 = não informada); sem ela, a mesa rotativa menos a diferença mediana mesa − terreno dos outros poços (sem nenhum, 5 m). O que estiver acima é cortado |
| Camadas cinza | *sem descrição no AGP*: entre o terreno e o primeiro topo (se passar de 5 m) e abaixo da base da última unidade, quando atingida |
| Base | plana: abaixo do ponto mais fundo dos dados (folga de 5% do relevo), ou a cota pedida em **Base do bloco fechado**. A última unidade sem base atingida vai até ela |

Por camada, a lista mostra área, espessura máxima, **volume de rocha** (km³, pela malha:
área × espessura média de cada triângulo) e a fração extrapolada. Na Potiguar (Cat. 1, 429
poços), 14 camadas em ~7 s.

> O volume é da camada inteira entre os limites interpolados — não é volume de reservatório
> nem de óleo. Onde há poucos poços, a espessura vem do poço mais próximo da borda.

### No visor

- **Opaco de saída** (a opacidade é guardada por modo).
- **Corte**: tira um quadrante (sudoeste, sudeste, nordeste, noroeste); **O–L** e **S–N**
  movem o canto. As tampas do corte mostram as camadas por dentro; os poços no quadrante
  tirado aparecem inteiros.
- **Afastar as camadas**: separa as camadas na vertical para ver o topo de cada uma (os poços
  somem: não casariam com nenhuma).
- **Seção A–A′ (poços da aba Seção)**: parede vertical pela linha dos poços da aba Seção (na
  ordem de lá), prolongada até a borda do bloco; o bloco fica translúcido.
- Passar o mouse numa camada: nome, cota, espessura máxima e se ali é interpolado ou
  extrapolado.
- A **figura estilo artigo** e o **PNG** saem no modo da tela (com corte, camadas afastadas ou
  a parede). Na figura, com as camadas juntas, só a superfície exposta é desenhada, em pedaços
  que não se sobrepõem (o algoritmo do pintor não erra no topo).

## Validação cruzada (0.21)

`motor/bloco_validacao.py`, botão **Deixar um poço de fora**. Cada poço sai do bloco, um de
cada vez; o bloco é refeito sem ele e prevê a cota de cada topo daquele poço, que se compara
com a do AGP (erro = previsto − AGP). É o número que diz quanto o bloco erra a uma certa
distância do poço mais próximo — o que transforma o "contexto espacial" em algo medido.

- **Os dois modos, com as regras da montagem**: o bloco fechado (referência + espessuras,
  cortado no terreno e na base; fora do contorno dos outros poços, o valor da borda — conta
  como *extrapolado*) e as superfícies (só dentro do contorno dos outros poços com a unidade;
  fora, não prevê).
- **Por unidade**: comparações, viés (média do erro), mediana do |erro|, o erro que **68%**
  das previsões não passam, máximo e o poço do máximo; erro médio da espessura.
- **Por faixa de distância** ao poço mais próximo com a unidade (0–1, 1–2, 2–5, 5–10, > 10 km).
- **Mediana e 68%, não a raiz do erro quadrático**: um poço com o AGP errado (ou numa falha)
  dispara a raiz do erro quadrático; a mediana e o percentil 68 descrevem o grosso dos poços.
  A raiz continua no registro.
- Fica no registro do bloco (`execucoes/bloco_….json`, chave `validacao`); reabrir o bloco
  traz a validação. **CSV** (uma linha por topo) e **figura estilo artigo**: (a) previsto ×
  AGP, com a linha 1:1; (b) |erro| × distância, com o erro de 68% por faixa nos dois modos;
  (c) tabela por unidade.
- Os maiores erros aparecem no resumo: ou o AGP daquele poço tem problema, ou há uma
  mudança brusca real entre os poços (uma falha). Os dois valem uma olhada.

**Rápido mesmo no regional.** Refazer a triangulação de Delaunay de cada campo para cada poço
seria lento (429 poços × 15 campos). Tirar um ponto de uma triangulação só muda a *estrela*
dele: os triângulos que o tocam viram a triangulação dos vizinhos. O `Interpolador` faz isso
(e os testes conferem, em milhares de consultas, que dá o mesmo que refazer tudo). Na
Potiguar (Cat. 1, 429 poços, 1.867 topos): ~12 s.

**O que a Potiguar mostrou** (Cat. 1, depois de tirar os topos abaixo do fundo): metade dos
topos com erro até ~15 m e 68% até ~31 m no bloco fechado; a 0–1 km do poço mais próximo,
68% até ~14 m; a 5–10 km, ~69 m. O Embasamento é o que mais erra (68% até ~175 m: o rifte
muda de profundidade de um bloco de falha para outro). As superfícies erram um pouco menos
nos topos (o empilhamento acumula o erro das espessuras), mas não preveem fora do contorno.

### Topos abaixo do fundo do poço

O AGP às vezes traz um topo mais fundo que o próprio poço — estimativa da operadora (sísmica,
poço vizinho), não o que o poço atravessou: o `1-JD-2-RN` (1.865 m) tem o Embasamento a
6.134 m. Esses topos ficam **fora do bloco** (com aviso), e uma base abaixo do fundo conta
como não atingida. Na Potiguar, 64 poços da Cat. 1. Foi a validação que mostrou: eram os
maiores erros.

## Prognóstico num ponto (0.21)

**Clicar no bloco** (o botão liga o modo; arrastar continua girando) ou escrever **lat, lon**
em graus decimais. O SIAPP calcula, no ponto, a coluna do bloco fechado com as mesmas regras
da montagem (sem a grade):

- cada camada: **topo** (cota e profundidade abaixo do terreno), **espessura**, base;
  "ausente" onde a espessura é zero; interpolado ou extrapolado (mais claro no visor);
- a distância ao poço mais próximo com a unidade e os três poços mais próximos;
- com a validação feita, a **incerteza (±)** de cada topo: o erro que 68% das previsões da
  validação não passaram, da unidade na mesma faixa de distância (com menos de 5 comparações,
  a faixa com todas as unidades; depois, a unidade inteira);
- um **pino** no visor, com uma esfera no topo de cada camada (a dica mostra os valores);
  **CSV** em `exportacoes/blocos/`.

> A profundidade é a partir do terreno; a mesa rotativa de um poço novo ficaria alguns metros
> acima. O prognóstico é o que o bloco prevê, com o erro que ele mostrou ter — não substitui
> a interpretação sísmica.
