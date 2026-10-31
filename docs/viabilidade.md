# Viabilidade: diâmetro, inflação e restrições ambientais (0.52)

Complementa a viabilidade econômica (`motor/economia.py`, `motor/viabilidade.py`; ver também `docs/producao-e-camadas.md`).
Tudo entra na **memória de cálculo** (entradas com fonte, equação, números substituídos).

## Diâmetro pela vazão

Escolha, em "Diâmetro pela vazão e correção pela inflação": *calculado pela vazão* ou *pela vazão, no tamanho comercial acima*.

1. Vazão na condição padrão (m³/d, informada), pressão e temperatura do duto (informadas).
2. Densidade do fluido na condição padrão (1 atm e 20 °C, ANP) e nas condições do duto, por Peng-Robinson com translação
   de Peneloux (a mesma da capacidade "pela molécula").
3. `Qop = Qstd · ρstd / ρop` (conserva a massa).
4. `D = √(4·Qop / (π·v·86400))` (continuidade, v em m/s) e `Dpol = D / 0,0254`.
5. Tamanho comercial: primeiro NPS da lista usual (2, 3, 4, 6, 8, 10, 12, 14 … 48 pol) igual ou maior. Tamanho nominal não
   é diâmetro interno: confira com o fornecedor.

**Limites:** não calcula queda de pressão ao longo do duto, espessura da parede, compressão nem normas; é o diâmetro interno
mínimo para não passar da velocidade. A velocidade padrão (15 m/s) é um ponto de partida do SIAPP, **não** uma norma: use a
do seu projeto (a memória diz se foi a padrão).

## Correção pela inflação

- Índices: **IPCA** (variação mensal, IBGE, via Banco Central/SGS série 433) e **INCC-M** (FGV, SGS série 192).
- Convenção: custo de data-base *jun/2024* está nos preços de junho de 2024; leva-se a um mês Z multiplicando
  (1 + variação) de julho/2024 até Z. O padrão de Z é o último mês da série.
- Data-base vem da referência de custo escolhida. Referência só com o ano (ex.: "2022") assume junho e avisa. Custo
  informado por você pede a "Data-base do custo".
- A série é baixada quando você pede a correção e fica em `ambiente_teste/indices/<índice>.json` com a data do download. Sem
  internet usa a cópia (e avisa). Falta de mês na série é erro: o SIAPP nunca completa a série sozinho.
- Passo extra na memória: `custo_km_corrigido = custo_km · f_infl`. Sem pedir a correção, nada muda.
- Exemplo medido em 31/10/2026: de jun/2024 a set/2026, IPCA ×1,1087 e INCC-M ×1,162 (27 meses). São valores da série
  naquela data, não constantes do SIAPP.
- INCC-M mede o custo da construção civil; um gasoduto tem aço, terraplenagem e montagem: nenhum índice é "o certo". A
  escolha e a data ficam registradas para quem for auditar.

## Restrições ambientais

- **UCs federais**: Dados › Camadas geográficas › "Unidades de Conservação federais (ICMBio)" (WFS do ICMBio publicado na
  INDE; camada `limiteucsfederais_a`). Só as federais: **UCs estaduais e municipais não estão**. Pode passar de 20 MB.
- **Terras indígenas**: o servidor de mapas da FUNAI não abriu com certificado válido neste computador, e o SIAPP não
  desliga a verificação do certificado. Baixe o shapefile (zip) ou GeoJSON no site da FUNAI e use **Importar terras
  indígenas…** (coordenadas em graus, WGS84 ou SIRGAS 2000; em metros, reprojete no QGIS antes).
- **Viabilidade › Restrições ambientais no traçado**: para cada infraestrutura medida, a linha reta do ponto do campo ao ponto
  mais próximo da feição, amostrada de 0,1 em 0,1 km; lista as áreas atravessadas e os km dentro (erro de até ~0,1 km por
  entrada). Camada não baixada/importada não entra na conta, e a tela avisa.
- **Não é** traçado nem licenciamento: o duto real contorna, e há outras restrições (APP, quilombolas, patrimônio, zonas
  de amortecimento) que não estão aqui.
