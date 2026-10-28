# Seção estratigráfica

Aba **Seção**. Poços lado a lado, correlacionados pelos **topos de formação que a operadora
registrou no AGP** da ANP (ver [`agp.md`](agp.md)). A correlação é pela identidade da
unidade (mesma sigla em poços vizinhos), não por semelhança de curvas: o SIAPP desenha o
que o AGP diz e aponta onde dois vizinhos discordam muito.

Pré-requisito: AGPs lidos no **Levantamento do acervo** (aba Mapa, opção *Ler os AGPs*) e o
cadastro da ANP no mapa (coordenadas e mesa rotativa).

## Escolher os poços

- **Um a um**: digite o nome (a lista sugere os poços que têm topos no AGP) ou use
  **Adicionar à seção** na ficha do poço (aba Mapa). Até 20 poços.
- **Ao longo de uma linha**: escolha as pontas A e B e a distância máxima da linha (km).
  Entram os poços com topos que ficam entre A e B e a até essa distância; passando de 20,
  ficam 20 espaçados por igual (sempre com as pontas).
- **Pela linha desenhada no mapa** (0.34): aba Mapa › **Desenhar a linha da seção** (ou o
  atalho "desenhe a linha no mapa" aqui). Cliques marcam A, os pontos intermediários (a linha
  pode fazer curvas) e B; dois cliques ou "Concluir" terminam. A faixa de busca aparece no
  mapa; os poços com topos ficam numerados na ordem ao longo da linha (cada poço vai para o
  trecho mais perto; fora das pontas não entra). **Abrir na Seção** leva a lista, na ordem da
  linha, e monta a seção (`motor/secao.py:corredor_linha`).

## Opções do desenho

| Opção | O que faz |
|---|---|
| Estilo | **clássico (indústria)**, o padrão, ou **moderno (artigo)** — ver abaixo |
| Ordem | **ao longo da linha** do 1º ao último poço da lista (projeção na reta); **direção de maior espalhamento** (componente principal das coordenadas, de oeste para leste — ou de norte para sul, se a direção for mais N–S); **na ordem da lista** (distância acumulada entre vizinhos) |
| Unidades | formações (e unidades sem nível, como o Embasamento); membros e camadas; grupos |
| Eixo vertical | **cota** do AGP (m, nível do mar = 0, positiva para cima), como a operadora calculou; **nivelado** no topo de uma unidade (cota − cota do topo do datum; datum = 0) |
| Espaçamento | proporcional à distância (com um espaço mínimo para as colunas não se sobreporem) ou igual |
| De / até | janela vertical, na unidade do eixo (ex.: 50 a −1500) |
| Curva GR | dos perfis do mesmo poço **já abertos na aba Perfis** (o de maior cobertura de GR) |
| Litologia | faixa estreita à esquerda da coluna, com a litologia das amostras de calha do AGP |
| Avisar quando um topo muda mais que | limiar (m) para a lista de saltos entre vizinhos (padrão 100 m) |

**Nivelado**: y = 0 é local de cada poço — dois poços em y = 0 estão no topo da mesma
unidade, não na mesma profundidade. O nivelamento mostra a geometria relativa de
deposição, sem a estrutura posterior. Poço sem o topo do datum sai da seção (com aviso).

## Dois estilos

| | Clássico (indústria) — padrão | Moderno (artigo) |
|---|---|---|
| Coluna do poço | trilha GR, escala de profundidade medida, **coluna litológica com padrões de rocha** (calha do AGP), faixa da formação, indícios de óleo/gás | coluna colorida pela formação, faixa fina de litologia, GR ao lado |
| Entre poços | corpos das formações em tons pastel com o nome dentro ("Fm. Açu"), linhas de topo, **discordâncias em linha ondulada** | faixas da formação e linha do topo na cor da unidade |
| Cabeçalho | símbolo do poço pela classificação (óleo, gás, óleo e gás, seco), nome, mesa rotativa (MR) e PF; pontas **A–A′** com a direção | nome, mesa, direções |
| Rodapé | legenda (litologia, unidades, símbolos), **mapa de localização** da linha, escala gráfica, **carimbo** (título, bacia, datum, poços, extensão, exagero, fontes, autor, data) | legenda e linha de fonte |
| Fonte | Helvetica/Arial | serifada (Times) |

O clássico segue as convenções usuais das seções de correlação de boletins técnicos e
relatórios de poço. Padrões de rocha, no espírito da convenção FGDC/USGS:

| Rocha (descrição de calha) | Padrão |
|---|---|
| Arenito | pontilhado sobre amarelo |
| Folhelho / argilito | tracejado horizontal sobre verde-acinzentado |
| Siltito | tracejado e pontos alternados |
| Calcário (inclui calcarenito, calcilutito) | tijolo sobre azul |
| Dolomito | tijolo oblíquo |
| Marga | tracejado com juntas |
| Conglomerado / brecha | seixos |
| Evaporito (halita, anidrita) | grade sobre rosa |
| Embasamento (granito, gnaisse, xisto…) | cruzes sobre salmão |
| Ígnea (basalto, diabásio) | "v" sobre lilás |
| Carvão | preto |
| Sem descrição de calha | hachura cinza |

Camadas vizinhas da mesma rocha viram uma só (o tooltip mostra as descrições). O símbolo
do poço vem da (re)classificação do AGP ou do cadastro: preenchido = óleo; com raios = gás;
preenchido com raios = óleo e gás; vazio com quatro traços = seco; vazio = outro.

Os padrões são desenhados como geometria e recortados no Python (o PyMuPDF, que gera o
PNG e o PDF, não entende `<pattern>` nem `clipPath`), então o arquivo exportado é igual ao
que aparece na tela.

## O que o desenho mostra

- Uma coluna por poço com as unidades (cor fixa por unidade, rótulo na coluna, tooltip
  com topo, base, cota, fonte, data, qualidade e método do AGP); base não atingida
  tracejada; linha grossa no fundo do poço (PF).
- Entre vizinhos que têm a mesma unidade: faixa clara de topo a base e linha do topo.
- Cabeçalho: nome, mesa rotativa, distância até o vizinho e as direções nas pontas (W, E…).
- Rodapé: fonte dos topos, número de poços, comprimento e **exagero vertical** (no
  espaçamento proporcional).
- No moderno: estilo de artigo (fundo branco, moldura fechada, marcas para dentro, grade
  fina, fonte serifada, legenda com moldura).

### Cores

Paleta categórica de 8 cores conferida para daltonismo (protan, deutan, tritan) nos pares
vizinhos do empilhamento. A cor **segue a unidade** — vem do campo `slot` de
`recursos/estratigrafia.json` — e não muda quando poços entram ou saem. Na Potiguar:
Barreiras amarelo, Jandaíra azul, Açu laranja, Alagamar verde-água, Pendência violeta,
Embasamento vermelho (Tibau/Guamaré rosa, Macau verde). Unidade sem slot fica cinza e é
identificada pelo rótulo. Como algumas cores têm pouco contraste com o branco, os nomes
estão sempre escritos (coluna e legenda) e a tabela "Topos usados" repete tudo.

## Curva GR em cota

Profundidade medida → cota por `cota = mesa rotativa − profundidade` (poço vertical). Se as
cotas do próprio AGP mostram que o poço é **desviado** (cota ≠ mesa − profundidade em mais de
1,5 m), a conversão usa os pares (profundidade, cota) do AGP como pontos de controle
(interpolação linear; fora deles, prolonga a inclinação da ponta) e a seção avisa.

## Saltos entre vizinhos

Quando o topo de uma mesma unidade muda mais que o limiar entre dois poços vizinhos, a
seção lista: *falha, mergulho forte ou interpretação diferente — confira*. O SIAPP não
decide qual; é um ponto para olhar (no perfil, no AGP, na sísmica).

## Registro e exportação

Cada seção montada grava `execucoes/secao_<data-hora>.json` (poços, ordem, distâncias,
parâmetros, cada topo usado com fonte/data/qualidade e o arquivo AGP de origem, o perfil de
onde veio o GR, avisos) e o `.svg` desenhado. **Seções anteriores** reabre sem recalcular.

Exportar (em `exportacoes/secoes/`): **SVG** (vetorial, editável no Inkscape/Word), **PNG**
a 300 ppp, **PDF** vetorial e **CSV** com os topos usados (`;`, para o Excel).

## Limites

- Os topos são a interpretação registrada pela operadora, muitas vezes com qualidade
  "dado não revisto" em poços antigos. A seção mostra discordâncias; não as resolve.
- Só entram poços com AGP lido (≈15% dos poços da Potiguar; bem mais entre os pioneiros).
- Unidades de níveis diferentes não se misturam numa seção (escolha formações, membros ou
  grupos); um membro pode ser usado como datum mesmo numa seção de formações.
- A ordem por projeção não considera falhas nem a direção do mergulho: escolha a linha
  pensando na geologia (ex.: perpendicular às falhas da bacia).
- GR só de perfis já abertos na aba Perfis; poço direcional sem cotas no AGP fica sem GR.
