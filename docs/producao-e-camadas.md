# Produção da ANP e camadas geográficas (0.24)

Dados públicos de **fora do REATE**, trazidos para o projeto para a próxima etapa: comparar a
distância de um campo a um gasoduto com a depleção do reservatório (viabilidade de injetar
CO₂, H₂…). Nesta versão o SIAPP **só baixa, lê e guarda**; contas sobre os dados ficam para depois.

Código: `motor/producao.py`, `motor/camadas.py`, `ponte/externos.py`, `ui/js/externos.js`.

## Produção do campo (aba Bloco 3D)

| Fonte (ANP, dados abertos) | O que vem | Período | Formato |
|---|---|---|---|
| Produção por poço — "Produção de Petróleo e Gás Natural Nacional" | óleo, condensado, gás associado e não associado, água; injeção de água (recuperação e descarte), gás, CO₂, N₂, vapor, polímeros — por poço e mês | 1941 até ~2 meses atrás (terra e mar em arquivos separados) | CSV nacional por ano, semestre ou trimestre (2–7 MB) |
| Produção por zona | o mesmo por **zona produtora** (o reservatório, ex. `AÇU0250 FSP-2`) | 10/2014 em diante | CSV nacional mensal (~2 MB), em m³/d |
| Ficha dos campos e vértices | operador, ambiente, situação, início da produção; **polígono** da área do campo | atual | CSV |
| Sumário executivo do Plano de Desenvolvimento | **volume in place** e **produção acumulada** numa data (do BAR), poços perfurados/produtores/injetores, área, reservatórios, mecanismo de produção | o PD mais recente | PDF de 1–3 páginas |

Como funciona:

- o SIAPP lê a página de dados abertos e pega os arquivos que cobrem o período pedido (não
  há lista fixa de nomes: a ANP muda o padrão — `producao-terra-2015-2sem.csv`,
  `producao_por_poco_terra_2026_2_trim.csv`…);
- cada arquivo é **nacional**: o SIAPP baixa, fica só com as linhas do campo (pelo nome sem
  acento: GUAMARÉ = Guamaré) e guarda uma **cópia compactada** em
  `ambiente_teste\fontes\anp\producao\` — o próximo campo não baixa de novo;
- unidades gravadas: óleo, condensado e água em **m³**; gás em **mil m³** (o "Mm³" da ANP);
  vapor em t. A produção por zona vem em vazão média (m³/d) e é gravada como volume do mês
  (× dias do mês);
- tabelas `producao_poco`, `producao_zona` e `campos_anp` no `projeto.sqlite` (migração 7);
  o poço também é gravado pelo id canônico do SIAPP (`poco_id`), para cruzar com o bloco;
- **CSV** exporta as duas tabelas para `exportacoes\producao\`.

Período: último ano, 5 anos (padrão, ~60 MB na primeira vez), 10 anos ou todo o histórico
(desde o início do campo; até ~550 MB numa primeira vez, porque cada arquivo é do país inteiro).

> A consulta nova da ANP (CDP, 2024 em diante) pede captcha: o SIAPP não a usa. A série
> nacional por poço já cobre até o trimestre mais recente.

O quadro mostra o que foi guardado, sem contas: soma do período por fluido, o último mês
publicado (poços produzindo e injetando), as zonas e os números do PD (in place, acumulada,
poços, reservatórios).

## Um campo, um clique

Em **Poços do bloco**, com "os poços de um campo": escolher o campo já traz os poços, e
**Montar este campo** traz os poços, põe a escala de reservatório e o título ("Campo de
Guamaré") e monta o bloco. O campo da produção acompanha o campo do bloco.

## Camadas geográficas (aba Mapa)

| Fonte | Camadas | Observação |
|---|---|---|
| **EPE** — WebMap (serviço ArcGIS) | gasodutos de transporte (diâmetro, pressão, transportadora), dutos de escoamento da produção (relação de dutos da ANP: diâmetro, fluido, origem e destino), gasodutos de distribuição, UPGNs, estações de compressão, city gates, terminais de GNL, termelétricas fósseis | a melhor fonte para a distância ao gasoduto; baixada em páginas de 1.000 feições |
| **EPE** — mapa de projetos de hidrogênio (0.24.1) | **unidades e projetos de hidrogênio verde e amônia**: nome, capacidade (t/ano), finalidade, estágio (piloto, P&D, MoU, pré-contrato), local, investimento (R$ milhões) | o SIAPP pega a edição mais recente do serviço `SEE/H2_PROJETOS_AAAAMM` (out/2024: 31 registros, 2 sem coordenadas na fonte). É a fonte que a própria página de hidrogênio da ANP indica. São sobretudo **projetos** — as unidades em operação ainda são pilotos (EDP em Pecém, Unifei, USP) |
| **ANP** — dados georreferenciados | campos de produção, blocos exploratórios sob contrato | shapefiles pequenos (0,3–0,5 MB) |
| **IBGE** — BC250 (versão mais recente) | dutos, termelétricas, linhas de transmissão, subestações, portos, cidades, estados, ferrovias, rodovias | o zip nacional tem ~800 MB: o SIAPP lê o índice e baixa **só** as camadas marcadas (HTTP Range). Os dutos do IBGE são poucos (111 trechos, sem o Nordestão nem o Gasfor) |

Cada camada vira `ambiente_teste\sig\<fonte>\<camada>.geojson` (SIRGAS 2000, EPSG 4674) e,
quando veio como shapefile, o shapefile original fica em `sig\<fonte>\<camada>\` (abre direto
no QGIS). `sig\camadas.json` registra a origem, a data, o número de feições e a caixa de cada uma.
O leitor de shapefile é do SIAPP (ponto, multiponto, linha e polígono com buracos; codificação
do `.cpg` ou do byte de idioma do `.dbf`) — sem GDAL.

## No mapa e diante de um campo (0.25)

- **Mostrar no mapa**: as camadas baixadas ligam e desligam no mapa (cor por tipo; clique
  para os atributos).
- **Campo e infraestrutura**: escolha o campo e **Medir as distâncias**. O polígono é o da ANP
  (vértices guardados ao baixar a produção); sem ele, o da camada "Campos de produção"; sem
  ela, o contorno convexo dos poços do cadastro — o quadro diz qual. Para cada camada
  baixada, a feição mais próxima, a distância e os atributos que importam (diâmetro e
  transportadora do gasoduto, capacidade da UPGN, estágio do projeto de H₂, combustível da
  termelétrica). "No campo" = a feição toca ou atravessa o polígono.
- Como mede: projeção azimutal equidistante centrada no campo (exata para distâncias a partir
  do centro) para achar o par de pontos mais próximo; a distância informada é a geodésica
  (haversine, esfera de 6.371 km) entre esses dois pontos.
- **Depleção**: óleo e gás produzidos ÷ in place pelo sumário do PD (data do BAR). Se a
  produção mensal baixada começa no mês seguinte à data do PD, soma o que veio depois e
  mostra a fração atualizada como **estimativa** (o in place é o do PD; não se recalcula).
  Com um buraco na série, não soma.

Guamaré, com os dados reais (camadas da EPE e da ANP, vértices e PD 2023): o Gasfor
(Guamaré–Pecém, 12") e dutos de escoamento atravessam o campo, a UPGN da 3R Potiguar fica a
2,7 km, o city gate e a termelétrica Vale do Açu a 43 km; óleo produzido 10,1% do in place,
gás 42,2% (BAR/2021).

Ainda fora, de propósito: custo do duto (R$/km), capacidade de injeção e o indicador
econômico — dependem de parâmetros a combinar. Unidades de conservação (ICMBio) e terras indígenas (FUNAI) não estão na BC250 2025;
podem entrar depois como restrição ambiental.
