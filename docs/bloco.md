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
