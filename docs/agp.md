# AGP — Dados Gerais de Poço

O **AGP** (arquivo geral de poço, ANP/SDT/BDEP) é um texto de largura fixa que acompanha
parte dos poços do REATE, na pasta `AGP` ou `Arquivo_geral_de_poco` (`<poço>_agp.txt`,
~20–160 KB). É o resumo oficial do poço: cabeçalho, revestimentos, **topos das unidades
estratigráficas**, indícios de hidrocarboneto, **dados de lama de cada corrida de perfilagem**,
temperatura, zonas-reservatório, testes de formação e litologia das amostras de calha.

O SIAPP 0.14 lê o AGP durante o **Levantamento do acervo** (aba Mapa) e usa o conteúdo na
ficha do poço, na avaliação de formação e no gráfico de perfis.

## Onde existe

Levantamento da Bacia Potiguar (16/10/2026, parcial):

| Categoria | Poços com AGP |
|---|---|
| 1 (pioneiro) | 366 de 581 (63%) |
| 3 (extensão) | 218 de 400 |
| 4 | 70 de 92 |
| 7 (desenvolvimento) | 557 de 7.257 (8%) |
| 8 | 15 de 94 |
| 9 | 71 de 130 |
| **Total** | **1.310 poços, 54 MB** — 897 deles também têm perfil digital |

O AGP cobre bem os pioneiros e as extensões e pouco os poços de desenvolvimento.

## Como o SIAPP lê

- **Etapa 3/3 do levantamento** (opção *Ler os AGPs*, marcada por padrão): para cada AGP novo
  ou que mudou de tamanho, baixa o texto inteiro (`Range`, até 4 MB), guarda uma cópia em
  `ambiente_teste/agp/<bacia>/` e grava o resultado nas tabelas `agp` e `agp_unidades`.
  Cancelar e recomeçar não relê o que já foi lido.
- **Codificação**: UTF-8, cp1252 ou latin-1, o que decodificar primeiro.
- **Formato pelo conteúdo**: um `.txt` que não tem as seções de um AGP é registrado com
  erro ("Não parece um AGP") e não entra em nada.
- **AGP de outro poço**: o portal às vezes guarda na pasta de um poço o AGP de outro (ex.: a
  pasta do 3-AP-10-RN contém o `3SG0010BA`). O SIAPP associa os dados ao poço **do próprio
  AGP** (cabeçalho), marca `confere = 0` e mostra o aviso na ficha.

### O que é extraído

| Seção do AGP | Campos |
|---|---|
| Cabeçalho | identificador, bacia, classificação, mesa rotativa, prof. final, formação na prof. final, coordenadas, datum, direcional… (todos os pares `CHAVE: valor`, também guardados crus) |
| REVESTIMENTOS | tipo, profundidade, cota, diâmetro |
| UNID.VERTICALIZADAS | tipo (TIP), qualidade, nome/sigla, código, topo e base (m e cota), descrição do contato, método, fonte, data |
| INDICIOS DE HIDROCARBONETOS | óleo/gás, origem, amostra, topo, base |
| PERFIS: REGISTRO DE CABECALHO | por corrida: Rm, Rmf, Rmc com as temperaturas, BHT, tipo e densidade da lama, salinidade, prof. alcançada, data |
| PERFIS: AQUISICAO/PROCESSAMENTO | perfis corridos (IEL, CDL, …) e intervalo |
| TEMPERATURA EXTRAPOLADA | temperatura, profundidade, gradiente |
| ZONAS RESERVATORIO | código, topo, base, fonte |
| TESTES DE FORMACAO | intervalo, resultado, observações; salinidade quando escrita como `SAL= 20.000 PPM` |
| LITOLOGIA | camadas (topo, base, rocha, descrição) |

### Dicionário de códigos (do próprio AGP)

- **TIP**: L litoestratigrafia, D discordância, C cronoestratigrafia, E crono especial,
  S crono-sísmica, M marco, N nanofóssil, P palinologia, O ostracodes, F foraminífero,
  X estéril, T ambiente, G dinoflagelados.
- **Qualidade**: B bom, R regular, Q questionável, I inferido, X dado não revisto.
- **Nível** (letra antes do nome, só em TIP L): F formação, M membro, G grupo, S supergrupo.

As siglas viram nomes por `recursos/estratigrafia.json` — **só as 15 vistas em AGPs reais**
(Jandaíra, Açu, Alagamar, Pendência, Embasamento, Barreiras, Coqueiro Seco, Morro do Chaves,
Penedo, Barra de Itiúba, Serraria, Bananeiras, Massacará, São Sebastião, Pojuca). Sigla fora
da tabela aparece como está no AGP. Acrescentar uma é editar o JSON (sigla, código, nome).

## Onde aparece

- **Ficha do poço** (Mapa): seção *AGP — dados gerais do poço* com cabeçalho, tabela de
  unidades (topo, base, fonte; o mouse mostra qualidade e método), corridas com Rm/Rmf/BHT,
  testes com salinidade e o botão **Abrir o AGP** (abre a cópia local).
- **Avaliação de formação** (Perfis): as unidades com topo e base e as zonas-reservatório
  viram **intervalos candidatos** ("Do AGP: topos interpretados pela operadora"),
  desmarcados por padrão. O painel mostra Rm, Rmf, BHT e gradiente do AGP como
  **referência para escolher o Rw** — o SIAPP não converte.
- **Gráfico de perfis**: topos do AGP como linhas tracejadas verdes, com o nome no eixo de
  profundidade, e a trilha **Litol. (AGP)** com a litologia das amostras de calha
  (arenito amarelo, folhelho/argilito verde-acinzentado, carbonato azul, evaporito rosa,
  embasamento marrom, outras cinza).
- **Exportar CSV** do levantamento: também `<bacia>_topos.csv` com todas as unidades lidas.

## Limites

- **Temperaturas em °F** e profundidades em metros, como no AGP. Não há conversão.
- Os topos são a **interpretação registrada pela operadora** (fonte e data na tabela), não
  uma verdade: a qualidade X ("dado não revisto") é comum em poços antigos.
- A profundidade do AGP é a do sondador; o perfil pode ter deslocamento de alguns metros.
- Leiaute de largura fixa: as expressões regulares foram conferidas em 40 AGPs reais
  (Potiguar, Alagoas e Sergipe; 194 linhas de unidade). 4 desses não tinham a seção de
  unidades; 11 tinham dados de lama. Um leiaute novo pode deixar uma seção vazia — a cópia
  local fica sempre disponível para conferir.
- A salinidade do teste só é lida no padrão `SAL= … PPM`.
