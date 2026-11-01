# Zonas produtoras (net pay) no bloco 3D (0.55)

Interpola o **topo e a base de cada reservatório** (a zona produtora), poço a poço, em vez dos topos de formação do AGP.
Código: `motor/zonas.py`, `motor/bloco.py` (nível `zonas`), `ponte/bloco.py`, `ui/js/bloco_zonas.js`.

## Como usar

1. Aba **Bloco 3D**: escolha os poços (passos 1 e 2) e, em **Unidades**, "zonas produtoras (net pay)". Aparece o passo **3b**.
2. **Fontes dos intervalos**: marque as que valem e dê prioridade com ↑ (a de cima vence). Escolha a regra:
   *usar a de maior prioridade* ou *envelope*. Ajuste a tolerância (m) que junta intervalos no mesmo reservatório.
3. **Ler os intervalos dos poços**: a tela mostra os **reservatórios** achados e, poço a poço, **todos os intervalos candidatos**,
   com a fonte, a descrição, topo e base (editáveis), se a página foi lida por **OCR**, o reservatório (automático, outro ou
   ignorar) e se foi usado.
4. Marque **só os reservatórios** que quer no bloco; renomeie se quiser.
5. **Montar** (passo 4). O bloco tem, para cada reservatório marcado, a superfície de **topo** e a de **base**.

## Como funciona

- **Intervalos candidatos** (profundidade medida): canhoneados (RFCP); testes de formação (RFP/TFR); análise de perfis do operador
  (RFP); amostra de fluido (topo e base da amostra do PVT); zonas-reservatório do AGP; intervalos que você marcou na aba Perfis;
  e a sua tabela. Cada um guarda o documento e a página de onde veio. Intervalos com base menor ou igual ao topo são descartados.
- **Cota**: a profundidade medida vira cota pela mesa rotativa; poços desviados usam a trajetória (dados direcionais) ou os pontos
  de controle do AGP. Poço sem mesa rotativa no cadastro nem nos formulários fica de fora, com aviso.
- **Reservatórios**: todos os intervalos (de todos os poços) são ordenados pela cota; um novo reservatório começa quando o topo do
  próximo está mais fundo que o fim do grupo atual **mais a tolerância** (padrão 20 m). Numerados do mais raso ao mais fundo
  (`ZP1`, `ZP2`…; no máximo 8). Mover um intervalo para outro reservatório ou ignorá-lo é por intervalo.
- **Um intervalo por poço e reservatório**: a fonte de maior prioridade (todos os intervalos dela naquele reservatório, em envelope)
  ou o envelope de todas as fontes.
- **Superfícies**: cada reservatório vira duas unidades do bloco: `ZPn` (topo→base) e `ZPn_B` ("Base do reservatório n": da base até
  o próximo reservatório ou o fundo do poço). A superfície de `ZPn_B` é a **base** do reservatório; a isópaca de `ZPn` é a espessura.
  Os mesmos métodos de interpolação do bloco (linear, IDW, spline, krigagem…) valem.
- **Net pay da avaliação**: onde há avaliação de formação salva, as propriedades (HPV, net pay, N/G, φ e Sw médias) são ligadas ao
  reservatório que contém o intervalo avaliado, como já era com as formações.

## Sua tabela

CSV (`;`, `,` ou tab) ou Excel com cabeçalho. Colunas reconhecidas (sem acento, maiúsculas ou minúsculas): **poço**, **topo**, **base**;
opcionais **reservatório/zona/camada**, **lat** e **lon** (graus) ou **X** e **Y** (UTM; informe a zona, ex.: 24 para Guamaré, hemisfério sul).
Números com vírgula decimal funcionam. Escolha se topo e base são **profundidade medida** ou **cota** (negativa abaixo do nível do mar).
Fica guardada no projeto (`ambiente_teste/zonas/`). Marcada como fonte, o SIAPP interpola a sua tabela com os mesmos métodos; com
"Usar as coordenadas da minha tabela", os poços ficam nas coordenadas dela. A tabela **Sua tabela × o que o SIAPP escolheu** mostra,
por poço, topo e base dos dois lados e a diferença (SIAPP − tabela, em metros), usando as outras fontes.

## Saídas

Valem as do bloco: mapas GeoTIFF e XYZ (topo, base e isópaca de cada reservatório), `_topos.csv`, `_superficies.csv`, ECLIPSE, modelo 3D,
validação cruzada. Novo: `<bloco>_zonas.csv`, um intervalo por linha (poço, reservatório, fonte, topo/base em profundidade medida e cota,
espessura, lat/lon, UTM leste/norte e zona).

## Limites

- Agrupar por profundidade não é interpretar geologia: um reservatório com falhas pode ser dividido; use a tolerância e a reatribuição.
- Zona produtora aqui é o que os documentos **indicam**; não é o net pay por cortes (Vsh, φ, Sw), que continua na Avaliação de formação.
- **OCR:** números lidos por reconhecimento de imagem erram (profundidades inclusive). A tela marca esses intervalos; confira no documento.
- Com 2 poços ou menos num reservatório não há superfície (precisa de 3).
- Se o SIAPP e o trabalho à mão usam os mesmos pontos, concordar mostra que a **interpolação** bate, não que a **zona escolhida** está certa.
