# Bloco 3D

> **0.55:** o bloco também aceita **zonas produtoras (net pay)** no lugar dos topos de formação: ver [`zonas-produtoras.md`](zonas-produtoras.md).

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

Num campo, escolher o campo já traz os poços, e **Montar este campo** (0.24) traz, põe a escala de
reservatório e o título e monta — um clique. A produção do campo pela ANP fica no quadro logo abaixo
(ver [`producao-e-camadas.md`](producao-e-camadas.md)).

Um poço muito longe de todos os outros (mais de 100 km e 5× a distância mediana ao centro)
fica de fora, com aviso — na Potiguar, o AGP do `1-BRSA-264-ES` está na pasta de um poço do RN.

## Como as superfícies são feitas

| Passo | Regra |
|---|---|
| Plano | lat/lon → km num plano local (equiretangular na latitude média; 111,2 km por grau de latitude) |
| Contorno | contorno convexo dos poços que têm a unidade (cadeia monótona); **área pela fórmula do shoelace**, mostrada no resumo e na figura |
| Dentro do contorno | **interpolação linear** nos triângulos de Delaunay dos poços (Bowyer–Watson); desde a 0.23, ou spline, IDW, krigagem, tendência + krigagem (ver [Interpolação e escala](#interpolação-e-escala-023)) |
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
- **Aparência dos poços** (0.32): forma do marcador da cabeça (bolinha, cubo, losango, cone,
  cilindro ou nenhum), cor e tamanho; cor da linha do poço; espessura da trilha e a cor de
  cada classe (pay, reservatório sem pay, indício de óleo…); discos nos topos; legenda; e
  **poços por cima do bloco** (só no bloco fechado, sempre ou nunca) — no bloco fechado, os
  poços de dentro ficam visíveis. Tudo vale na hora, sem montar de novo, fica nas preferências
  (`preferencias.json › bloco.aparencia`) e a figura estilo artigo usa a mesma aparência. A
  escolha de "Nos poços" continua ao montar de novo.

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
| Empilhamento | **por espessuras**: um **limite de referência** (o mais fundo observado em ≥ 90% dos poços) é interpolado direto; os de cima somam espessuras, os de baixo subtraem. Espessura ≥ 0: **as camadas nunca se cruzam**, e passam pelos topos do AGP nos poços. **Topo a topo** (0.23): cada limite interpolado direto dos poços e cortado para não passar acima do de cima (onde se cruzariam, a camada acunha); um limite sem nenhum poço sai da espessura de cima |
| Interpolação | o método escolhido (linear por padrão até a 0.22) nos poços com o dado; fora do contorno deles, o valor do ponto mais próximo da borda (linear entre os dois poços da aresta: contínuo) — **extrapolado, mais claro**. Os métodos lisos, fora do contorno, ficam presos à faixa dos dados ± 10% |
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

## Interpolação e escala (0.23)

`motor/interpolacao.py`. Cada campo do bloco tem o seu método — **topos** (estrutura: as
superfícies e o bloco fechado), **espessuras** e **propriedades** (φ, N/G, Sw sobre o topo) —,
escolhidos no quadro **Interpolação** da montagem. Os textos de ajuda da janela vêm do
próprio motor (uma fonte só).

| Método | O que faz | Bom para |
|---|---|---|
| **Linear** (triângulos) | passa exatamente nos poços, nunca inventa alto ou baixo além dos dados; facetada | poucos poços, campos densos, controle de qualidade, rifte com falhas |
| **Inverso da distância** (IDW) | média dos vizinhos pesada por 1/dᵖ; exata nos poços, "olhos de boi" | olhada rápida, propriedades; fraco para topo |
| **Spline de placa fina** (mínima curvatura) | a superfície mais lisa pelos poços; com **suavidade**, aceita errar no poço para ficar lisa (filtra topo mal marcado) | estruturas contínuas, dobras suaves, leques |
| **Funções de base radial** (RBF, 0.32) | soma de "montes" φ(r) em volta de cada poço + plano: multiquádrica √(1+(r/c)²) (Hardy, 1971), multiquádrica inversa 1/√(1+(r/c)²) ou gaussiana exp(−(r/c)²); raio c e suavidade automáticos pela validação cruzada | superfícies lisas com poços irregulares; leques e lobos com poucos poços; a inversa e a gaussiana voltam ao plano longe dos poços |
| **Krigagem ordinária** | correlação espacial medida nos poços (variograma: alcance, pepita, patamar; anisotropia); dá o **mapa de incerteza** (σ) | muitos poços (20+), sistemas com direção (fluvial, leque), bacia |
| **Tendência + krigagem** | tira o mergulho regional (plano ou superfície de 2º grau) e kriga o resto | bacia com mergulho para o depocentro, carbonato de plataforma |

| Parâmetro | Efeito |
|---|---|
| Suavidade (0–1, ou automática) | spline: λ = escala·10^(−5+5s); automática = a que menos erra deixando um poço de fora. Krigagem: fração de pepita (0,9·s); automática = a do variograma ajustado |
| Potência, vizinhos | IDW: potência maior = cada poço domina em volta; vizinhos 0 = todos |
| Variograma, alcance | esférico, exponencial ou gaussiano; automático = o melhor entre esférico e exponencial, ajustado por mínimos quadrados (pares/distância) até 15× o espaçamento típico dos poços |
| Azimute, razão | anisotropia: direção de maior continuidade e alcance perpendicular ÷ alcance no azimute |
| Grau | tendência: 1 = plano; 2 = superfície curva |
| Função, raio (RBF) | forma do "monte" e a distância em que ela muda (1/ε); vazio = automático: entre 0,5× e 20× o espaçamento típico dos poços, com suavidade 0–0,6, o par com a menor mediana do erro deixando cada poço de fora (fórmula de Rippa, 1999) |

Regras comuns:

- **Espessuras com zeros**: spline, krigagem e IDW espalham um pouco de espessura entre poços
  onde a unidade falta; a espessura do método é multiplicada pela **presença** interpolada
  linear (onde ela é 0, a espessura é 0; a linha de acunhamento fica onde a presença vale ½).
- **Krigagem com menos de 8 poços** com o dado: sem variograma que se sustente → linear, com aviso.
- **Mapa de incerteza**: com krigagem ou tendência nos topos, o σ da krigagem de cada topo vira
  uma "propriedade" em **Colorir o topo de … por incerteza do topo** — claro perto dos poços,
  escuro longe.
- **Validação cruzada com cada método**: tirar um poço da spline e da krigagem não refaz o
  sistema — atualiza os coeficientes (`coef − coefᵢ/(M⁻¹)ᵢᵢ · M⁻¹[:, i]`, Dubrule 1983),
  com os hiperparâmetros (λ, variograma) fixos; os testes conferem com o ajuste refeito do
  zero. A tendência fica a de todos os poços.

### Qual método usar? (0.32)

Quadro no passo **2 Interpolação** (`motor/guia_interpolacao.py`). Cada método recebe pontos
de três fontes, e cada ponto aparece na tela com o motivo:

1. **Ambiente do reservatório** — regras práticas em `recursos/guia_interpolacao.json`
   (editável, por exemplo com o orientador): leque → RBF, spline, krigagem com anisotropia
   (evitar IDW); fluvial → krigagem com azimute na paleocorrente (evitar spline e RBF, que
   espalham areia entre canais); costeiro e carbonato → tendência + krigagem; rifte → linear
   (o SIAPP não modela falhas: os lisos suavizam o degrau); dobra suave → spline, RBF.
2. **Os dados** — menos de 8 poços: sem krigagem; 8–19: variograma pouco confiável; 20+:
   krigagem com mapa de incerteza; poços agrupados (índice de Clark e Evans < 0,6): IDW faz
   olhos de boi; um plano explica 70%+ da variação do topo de referência: mergulho regional
   forte, tendência.
3. **A comparação dos métodos** nos poços do bloco, se já feita: o que menos errou ganha
   mais pontos que qualquer regra; empate (até 10% + 1 m) também soma; 50% pior perde.

Soma ≥ 3 = **indicado**, ≥ 0 = possível, < 0 = evitar. **Usar o indicado** só preenche o
formulário (com os parâmetros sugeridos pelo ambiente); montar continua sendo do usuário. O
ambiente escolhido fica guardado nas preferências e no registro do bloco (`ambiente`).

As regras do ambiente são ponto de partida, não lei: a evidência é a comparação nos seus
poços. Ex.: "RBF em leque" vale para a superfície lisa de um lobo com poucos poços; a
espessura de um leque tem tendência radial (afina do ápice para a borda), e com o ápice dentro
da área a tendência + krigagem (grau 2) pode errar menos — a comparação diz.

### Comparar métodos

Botão **Comparar métodos** (num bloco montado): a validação cruzada com oito combinações —
linear por espessuras, linear, IDW, spline, RBF multiquádrica, RBF multiquádrica inversa,
krigagem e tendência + krigagem topo a topo —, com
os parâmetros avançados do bloco. Tabela por unidade (mediana / 68% do erro, o menor de cada
unidade em negrito), o **sugerido** (menor mediana no bloco fechado; sem bloco fechado, nas
superfícies) e **Usar o melhor e montar de novo** (troca topos, espessuras e empilhamento;
as propriedades ficam). CSV e figura estilo artigo: mediana do erro por unidade em escala log,
um símbolo por método (sem depender de cor), cheio = o menor erro da linha. Guardada no
registro do bloco.

Dois casos reais (mediana / 68% do erro, m; F = bloco fechado, S = superfícies):

| Combinação | Estreito (14 poços) F | S | Potiguar Cat. 1 (≈430 poços) F | S |
|---|---|---|---|---|
| Linear, por espessuras | 14,8 / 21,3 | 15,2 / 19,9 | **15,4 / 30,6** | 14,5 / 26,2 |
| Linear, topo a topo | 14,8 / 21,3 | 15,2 / 19,9 | 15,4 / 30,8 | 14,5 / 26,2 |
| IDW, topo a topo | 23,9 / 32,2 | 14,5 / 18,3 | 21,2 / 41,8 | 19,8 / 37,2 |
| Spline (automática), topo a topo | 10,9 / 19,1 | 17,9 / 23,7 | 16,2 / 32,0 | **14,4 / 26,5** |
| Krigagem, topo a topo | 18,5 / 28,5 | **9,3 / 15,0** | 18,8 / 34,6 | 14,6 / 27,0 |
| Tendência + krigagem, topo a topo | **9,3 / 18,4** | 16,6 / 23,6 | 18,6 / 34,4 | 14,4 / 26,4 |

O que se aprendeu:

- **Topo a topo** é o que faz os métodos lisos funcionarem no bloco fechado. Por espessuras,
  o erro de uma referência lisa e o das espessuras se somam: spline por espessuras errou 22 m
  na Potiguar, topo a topo 16 m. Com a linear, os dois empatam.
- Num **campo** com poucos poços, os métodos lisos ganham (a linear facetada erra entre os
  poços); no **regional** denso e falhado, a linear continua difícil de bater no bloco
  fechado, e nas superfícies todos empatam perto de 14,5 m.
- Diferenças de poucos metros estão dentro do ruído dos topos do AGP (a interpretação da
  operadora) — por isso a comparação mostra o erro de 68% junto da mediana.

### Escala: reservatório ou bacia (0.23)

O seletor **Escala** preenche o formulário com um ponto de partida; tudo continua editável
(mexer em qualquer campo vira "personalizada"). Fica registrada no bloco.

| | Reservatório (um campo) | Bacia (regional) |
|---|---|---|
| Poços | os de um campo | todos da bacia |
| Margem / corte por distância | 0 / sem | 0 / 15 km |
| Grade | 160 células | 120 células |
| Topos | spline (automática) | tendência (grau 1) + krigagem |
| Espessuras | spline (com presença) | krigagem (com presença) |
| Propriedades | IDW | krigagem |
| Bloco fechado | topo a topo | topo a topo |

Por quê: num campo, a spline topo a topo errou 26% menos que a linear no bloco fechado e
funciona com 3 poços (a krigagem pede 8); na bacia, tendência + krigagem separa o mergulho
regional da variação local, empata nas superfícies e dá o mapa de incerteza — mas no bloco
fechado regional a linear ainda erra menos: rode **Comparar métodos**.

Guia rápido por tipo de reservatório (ponto de partida, a comparação decide):

| Reservatório | Topos | Espessuras | Por quê |
|---|---|---|---|
| Carbonato de plataforma (Jandaíra) | tendência + krigagem, ou spline | krigagem | camadas extensas, mergulho suave e contínuo |
| Fluvial / canais (Açu) | krigagem com anisotropia na direção do aporte | krigagem anisotrópica, ou linear | corpos alongados; espessura muda rápido na transversal |
| Leque / turbidito | spline ou krigagem anisotrópica | krigagem | geometria lobada e contínua |
| Rifte com falhas (Pendência, Alagamar) | linear | linear | os métodos lisos "alisam" os rejeitos; o SIAPP ainda não modela falhas |
| Poucos poços (< 8) | linear ou spline | linear | sem variograma; a linear não inventa |

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

## Saídas do bloco (0.22)

O quadro **Saídas do bloco**, embaixo do visor, leva o bloco para outros programas. Tudo vai
para `exportacoes/blocos/`.

### Coordenadas: SIRGAS 2000 / UTM

`motor/utm.py`: projeção transversa de Mercator pelas séries de Krüger (6ª ordem), no
elipsoide GRS80 do SIRGAS 2000 — confere com o pyproj ao milímetro e com o UTM escrito nos
próprios arquivos de dados direcionais. O fuso é o do centro do bloco (EPSG 31977–31985 no
hemisfério sul; 31972–31976 no norte). Um bloco que atravessa dois fusos fica todo no do
centro, como é costume.

### Mapas para SIG

`motor/bloco_mapas.py`. Uma grade UTM regular (pixel padrão: o passo da grade do bloco,
arredondado — 200 m no Estreito), cada pixel levado ao plano do bloco e amostrado por
interpolação bilinear; fora do contorno do bloco, sem dado.

- **GeoTIFF**, um por mapa: `terreno`, `topo_<unidade>` (cota, só onde a camada tem
  espessura) e `isopaca_<unidade>` (espessura). Float32, sem dado = −9999, com o EPSG nas
  chaves GeoTIFF — o QGIS abre já no lugar certo. Escrito pelo SIAPP (TIFF sem compressão),
  sem GDAL.
- **XYZ**: um CSV com leste, norte, lat, lon e todos os mapas em colunas (`;`, vírgula
  decimal), mais o `.prj`. Abre no Excel, Surfer, Petrel, QGIS (texto delimitado).
- Sem bloco fechado, saem os topos das superfícies.

### Mapa 2D com curvas de nível (0.56)

Quadro "Mapa 2D com curvas de nível" (abaixo da validação): vista de cima do terreno, do topo ou da espessura de cada camada
ou zona produtora. Usa os mesmos valores dos mapas para SIG (grade UTM do bloco, só dentro do contorno dos poços mais a margem
pedida na montagem) e desenha em SVG, sem biblioteca de gráficos: as curvas de nível saem de um *marching squares* próprio
(`motor/bloco_mapa2d.py`). Cores por faixa (48 níveis), curvas rotuladas, poços em círculos brancos e eixos em metros a partir
do centro do bloco. O intervalo das curvas é automático (cerca de 12 curvas) ou o que se digitar. "Profundidade" troca a cota
(negativa abaixo do mar) pela profundidade positiva; com "inverter as cores", o raso fica claro. Salva em SVG, PNG (300 ppp) e PDF.
Limites: não extrapola além do contorno (use a margem do bloco); o pixel segue o passo da grade do bloco (no máximo 200 células
por lado).

### Simulador (.DATA, formato ECLIPSE)

`motor/bloco_eclipse.py`. Deck que o tNavigator, o OPM Flow, o Petrel e o ResInsight leem.

| Do dado (SIAPP) | Provisório (o SIAPP não tem; troque antes de simular) |
|---|---|
| Geometria: grade corner-point em UTM, pilares verticais, profundidade = −cota | Permeabilidade (100 mD; PERMZ = 0,1 × PERMX) |
| Formações escolhidas, cada uma em camadas iguais entre o topo e a base | PVT: óleo morto e água genéricos |
| ACTNUM: fora do contorno do bloco ou mais fina que 0,1 m, inativa; PINCH | Curvas relativas: Corey genérico |
| FIPNUM: uma região por formação | Contato e pressão inicial (EQUIL) |
| PORO e NTG da avaliação de formação (grade com 3+ poços, senão a média) — sem avaliação, 0,20 e 1,0 **marcados** | |
| Poços com o caminho real (trajetória), WELSPECS/COMPDAT, fechados; nomes de 8 caracteres (1-AURI-12-RN → AURI12) | |

- **Tamanho**: o teto padrão é **275.625 células** (licença acadêmica do tNavigator). O
  SIAPP escolhe as camadas (≥ 1 por formação, proporcionais à espessura média) e a célula
  (múltiplo de 10 m) para caber; a **prévia** mostra a grade antes de exportar. Dá para fixar
  camadas, célula e teto.
- **Formações**: todas menos o embasamento, de saída; marque e desmarque.
- **Arquivos**: `<NOME>.DATA` (o deck), `.GRDECL` (geometria), `_PORO_NTG.inc`,
  `_PERM.inc`, `_FIPNUM.inc`, `_PVT.inc`, `_SCAL.inc`, `_SOLUCAO.inc`, `_POCOS.inc` e o
  `LEIA-ME.txt` (o que é dado, o que é provisório, a lista de poços, o volume poroso).
- Conferido com o parser do OPM (o deck abre, a grade e os poços batem) e com o resdata
  (volumes de célula positivos, coordenadas certas).

> O deck é a geometria do bloco com o que se sabe pelos poços. Simular de verdade pede
> permeabilidade, PVT, curvas relativas e contatos do campo — o SIAPP deixa o lugar pronto e
> marcado.

### Volumetria preliminar

`motor/bloco_volumetria.py`. Por formação: área, espessura média, **volume de rocha** (da
malha do bloco fechado), N/G, φ e Sw — da avaliação de formação (média dos poços avaliados na
formação) ou **digitados** (a origem de cada valor fica registrada) —, **volume poroso**,
**hidrocarboneto** (condições de reservatório), **óleo in place** (com Bo) e **capacidade
teórica de CO₂** (volume poroso × E × ρ, com E e ρ digitados). Sem N/G ou φ, a formação fica
sem conta: o SIAPP não inventa parâmetro. CSV com tudo e as notas.

> Preliminar: o volume de rocha inclui a parte extrapolada do bloco, e uma média de poucos
> poços avaliados não representa a formação inteira. Afira com um volume oficial (Plano de
> Desenvolvimento da ANP) — foi assim que o caso de Carmópolis mostrou um net pay 5× inflado.

### Modelo 3D (.glb)

`motor/bloco_glb.py`. glTF binário do bloco fechado: uma malha por camada (a parte
extrapolada num material mais claro), os poços como tubos finos, o exagero vertical da tela e
só as camadas ligadas. Abre no **PowerPoint** (Inserir → Modelos 3D, e gira no slide), no
Visualizador 3D do Windows e no Blender. Unidades em km; ~3 MB num campo, ~12 MB na bacia.
