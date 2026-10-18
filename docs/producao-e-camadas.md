# Produção da ANP, camadas geográficas e viabilidade de injeção (0.24–0.26)

Dados públicos de **fora do REATE** para comparar a distância de um campo à infraestrutura com
o espaço que a produção liberou no reservatório — a viabilidade de injetar CO₂, H₂… (0.24 baixa
e guarda; 0.25 mede distâncias e depleção; 0.26 calcula custo ÷ capacidade).

Código: `motor/producao.py`, `motor/camadas.py`, `motor/viabilidade.py`, `motor/economia.py`,
`ponte/externos.py`, `ui/js/externos.js`.

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

## Viabilidade econômica (0.26)

Depois de medir as distâncias, o quadro **Viabilidade econômica** dá, para cada infraestrutura
medida, o custo do duto até ela e o indicador do PIBIC: **investimento no duto ÷ capacidade de
injeção do campo**. Menor = mais viável. Código: `motor/economia.py`.

**Custo do duto** = distância × fator de traçado × custo por km, com custo por km = (R$ por
polegada·km) × diâmetro × fator do fluido.

| Referência (EPE, Plano Indicativo de Gasodutos) | Projeto | R$ mil por pol·km |
|---|---|---|
| PIG 2024 (padrão), data-base jun/2024 | Porto Murtinho–Campo Grande: 392 km, 32″, R$ 6.119 mi | 488 |
| PIG 2022 | Brasil Central (São Carlos–Brasília): 893 km, 18–20″, R$ 11.152 mi (contado a 18″) | 694 |
| PIG 2019, jun/2019, relevo plano | Uruguaiana–Triunfo: 594 km, 24″, R$ 4.634 mi | 325 |
| PIG 2019, jun/2019, Serra do Mar | Siderópolis–Porto Alegre: 249 km, 16″, R$ 1.819 mi | 457 |

- Conta do SIAPP: CAPEX total ÷ (extensão × diâmetro). A EPE estima com precisão de −20/−50% a
  +30/+100% (classe conceitual, AACEI). Entre 2019 e 2022 os custos subiram 52–61%. Gasodutos curtos
  ficam mais caros por km (ramais de terminais de GNL chegaram a ~US$ 140 mil/pol·km).
- Literatura brasileira (GESEL/UFRJ, 2020): US$ 50 a 150 mil por pol·km, conforme o terreno.
- **Fator do fluido**: CO₂ ×1,20 — em fase densa o duto trabalha a ~150 bar contra ~100 do gás e
  pede ~50% mais aço; a tubulação é ~45% do CAPEX no PIG 2024 (estimativa do SIAPP). H₂ ×1,05 —
  aço ~10% mais caro, +1,4 a 4,6% por pol·milha (EPRI, 2023).
- **Fator de traçado**: 1 = a distância em linha reta (como no PIBIC); um traçado real costuma ser
  10–30% mais longo.
- O modelo é linear no diâmetro: para dutos finos (< 6″) tende a subestimar.

**Capacidade de injeção** — três níveis, do que funciona para todo campo ao mais específico:

| Método | Espaço | Precisa de | Indicador |
|---|---|---|---|
| Simples (PIBIC) | volume produzido em m³ de óleo equivalente: óleo + condensado + gás ÷ 1.000 | só a produção | R$/m³ oe |
| Espaço poroso | Np·Bo + (Gp − Np·Rs)·Bg + Wp − Wi − Gi·Bg (m³ de reservatório) | Bo e/ou Bg; Rs opcional | R$/m³ res |
| Pela molécula | espaço poroso × ρ(P, T) × eficiência (× (1 − colchão) para H₂ e CH₄) | o anterior + P e T (ou a profundidade) | R$/t, R$/MWh (H₂) |

- **Produção acumulada**: a série mensal da ANP quando cobre todo o histórico sem meses
  faltando (só aí entram água produzida e fluidos injetados); senão a acumulada do sumário do PD,
  somando a produção mensal que vem logo depois; senão o período baixado, com aviso de que
  subestima.
- Sem Rs, todo o gás produzido conta como gás livre (superestima num campo de óleo). Sem influxo
  de aquífero: com aquífero ativo, o espaço real é menor. É o método "baseado na produção" de
  Bachu et al. (CSLF, 2007) para capacidade de CO₂ em campos depletados.
- **Densidade**: Peng-Robinson com translação de volume (Peneloux). Contra as equações de
  referência (NIST/CoolProp): CO₂ dentro de ~7% (o pior perto do ponto crítico, 100 bar e 40 °C),
  H₂ e CH₄ dentro de ~4%. P e T: informados, ou hidrostática (0,1 bar/m) e 25 °C + 30 °C/km sobre a
  profundidade — a informada ou a mediana da profundidade final dos poços do campo.
- **Eficiência** (padrão 1 = teórica) e **gás de colchão** (padrão 0,5, usual em armazenamento
  de gás em campo depletado) ficam para o usuário calibrar.
- Guamaré (PD 2023, BAR/2021): 1,65 milhão de m³ oe produzidos. Com valores de exemplo (Bo 1,1,
  Bg 0,012, Rs 30, 80 bar e 35 °C): 4,06 milhões de m³ de reservatório e 1,68 Mt de CO₂.

É triagem para comparar campos e rotas: pressão e injetividade só a simulação responde.

## Auditoria: memória de cálculo, constantes e equações (0.27)

**Memória de cálculo.** Cada "Calcular a viabilidade" grava em `execucoes\viabilidade\` um
`AAAAMMDD-HHMMSS_<campo>.json` (tudo: parâmetros, entradas, passos, resultados) e um `.html`
legível, com:

1. **dados de entrada e de onde vieram** — símbolo, o que é, valor, unidade e fonte (arquivo da
   ANP e data do PD, camada e feição, "informado pelo usuário", "padrão — <fonte>" ou "alterada
   pelo usuário (padrão X)"); dado ausente aparece como tal ("indisponível — usado 0", "não
   informado");
2. **passo a passo** — para cada equação: o texto da fórmula, a fórmula com os números
   substituídos e o resultado com unidade; a equação de estado com cada valor intermediário;
3. **por infraestrutura** — comprimento, custo do duto e cada indicador, com a fonte da distância;
4. **diferenças em relação ao padrão** — equações e constantes alteradas.

Com o .html dá para refazer qualquer número à mão ou no Excel. O histórico do projeto
(`siapp.json`) registra cada execução, o arquivo da memória e o que foi alterado.

**Constantes** (quadro "Constantes"): cada uma com padrão, fonte e faixa aceita.

| Constante | Padrão | Fonte |
|---|---|---|
| gás por m³ de óleo equivalente | 1.000 m³/m³ | ANP |
| Bw | 1,0 | aproximação usual |
| pressão na superfície; condição padrão | 1,01325 bar; 1,01325 bar e 20 °C | 1 atm; ANP |
| PCI do H₂ | 33,33 kWh/kg | 120 MJ/kg |
| fator de custo CO₂ / H₂ / CH₄ | 1,20 / 1,05 / 1,00 | estimativa do SIAPP / EPRI 2023 / referência |
| Tc, Pc, ω, M, Z_RA de CO₂, H₂, CH₄ | — | NIST, DIPPR, Reid-Prausnitz-Poling |

**Equações** (quadro "Equações"): cada passo é uma fórmula em texto. O seletor traz o padrão, as
alternativas prontas e "a minha fórmula".

| Passo | Resultado | Padrão | Alternativas |
|---|---|---|---|
| Custo do duto por km | custo_km (R$/km) | `custo_pol_km * 1000 * D * f_fluido` | afim `(custo_fixo_km + custo_pol_km * D) * 1000 * f_fluido`; por km `custo_fixo_km * 1000 * f_fluido` |
| Comprimento | L (km) | `dist * f_tracado` | |
| Custo do duto | custo (R$) | `L * custo_km` | |
| Espaço simples (PIBIC) | oe (m³ oe) | `Np + Gp / gas_por_oe` | `Np`; `Np + Gp / gas_por_oe + max(0, Wp - Wi)` |
| Gás livre | Gl (m³) | `max(0, Gp - Np * Rs)` | |
| Espaço poroso | V (m³ res) | `Np * Bo + Gl * Bg + (Wp - Wi) * Bw - Gi * Bg` | `Np * Bo + Gl * Bg` |
| Pressão | P (bar) | `p_atm + grad_p * prof` | |
| Temperatura | T (°C) | `t_sup + grad_t * prof / 1000` | |
| Massa | m (t) | `V * rho * ef / 1000` | |
| Massa útil | m_util (t) | `m * (1 - colchao)` | |
| Volume padrão | Vp (m³) | `m_util * 1000 / rho_padrao` | |
| Energia (H₂) | E (MWh) | `m_util * pci_h2` | |
| Indicador | ind | `custo / capacidade` | |

- A fórmula do usuário pode usar qualquer símbolo já conhecido naquele passo (a lista "Símbolos"
  diz o que é cada um e a unidade), números, `+ − * / ^`, parênteses e `min, max, abs, sqrt, exp,
  ln, log10`. O leitor é próprio (árvore sintática com lista do que é permitido): não executa
  código, não acessa arquivos.
- Erros dizem onde: "Equação «Espaço poroso…»: variável desconhecida Zz" (com a lista do que está disponível quando o símbolo existe mas ainda não foi calculado naquele passo),
  divisão por zero com a conta substituída, escrita inválida.
- A unidade do resultado é a do passo: quem escreve a fórmula responde pela coerência das unidades.
- A equação de estado (Peng-Robinson + Peneloux) não é uma fórmula editável; dá para trocar as
  suas constantes ou informar a densidade diretamente.
- Equações, constantes e parâmetros ficam guardados no campo e voltam quando ele é medido de novo.

Unidades de conservação (ICMBio) e terras indígenas (FUNAI) não estão na BC250 2025;
podem entrar depois como restrição ambiental.
