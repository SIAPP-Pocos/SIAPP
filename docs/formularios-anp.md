# Formulários da ANP na pasta de poço (RFP, RFCP, Perfuração)

*SIAPP 0.37 — bloco 9, item 1.* Código: `motor/rfp.py` (o leitor) e `motor/dados_poco.py` (o arcabouço comum
dos leitores de dados do poço).

## O que são

Na "Pasta de Poço" do REATE vêm PDFs gerados pelo sistema da ANP (SDT — Superintendência de Dados Técnicos),
o CDPE, com nomes como:

| Arquivo | Formulário | O que traz de útil |
|---|---|---|
| `<poço>_CDPE_1_Perfuracao.pdf` | Notificação e Relatório de Perfuração | sonda, categoria, profundidade prevista, coordenadas previstas, **fases** (diâmetro, profundidade, revestimento, topo do cimento, **tipo e peso do fluido de perfuração**), tempos e não conformidades |
| `<poço>_CDPE_<n>_RFP.pdf` | Relatório Final de Poço | datas, profundidade final do sondador e do perfil, mesa rotativa, coordenadas da base/alvo/fundo, resultado (descobridor, fluido, abandono), **topos previstos × constatados**, **indícios**, testemunhos, amostras laterais, **análise de perfis**, **testes de formação**, **temperaturas**, amostragem de calha, observações |
| `<poço>_CDPE_<n>_RFCP_1.pdf` | Relatório Final de Completação | revestimento de produção, **intervalos canhoneados**, coluna de produção, teste (vazão, °API, BSW, pressão de fluxo) e a **sigla antiga do poço na base da operadora** |
| `<poço>_CDPE_<n>_ND_1.pdf` (0.38) | Relatório de Descoberta | data da descoberta e fluidos, indícios, intervalos da interpretação de perfis, testes, estado atual do poço — muitos poços têm só este, sem RFP |
| `<poço>_CDPE_<n>_NPR_1.pdf` (0.38) | Relatório de Perfilagens Realizadas | cada perfilagem (data, companhia, perfis, intervalo); as especiais com a profundidade de cada ponto (estações do teste a cabo, níveis do checkshot) e o resultado (pré-testes conclusivos e falhos, níveis sísmicos) |
| `<poço>_CDPE_<n>_Reentrada_<k>.pdf` (0.38) | Relatório de Reentrada | nº, datas, sonda, profundidade final, estado atual e os textos: motivo, operações previstas, resultado, dados adquiridos |
| outro `CDPE` (0.38) | título desconhecido | o título e o texto todo, sem erro ("Formulário CDPE") |

Ao contrário dos relatórios escaneados, esses PDFs têm **texto embutido** e **leiaute fixo** (A4, cada campo sempre
na mesma posição). Por isso o SIAPP os lê pela posição do texto, sem OCR — sem os erros de leitura do OCR.

## Como a leitura funciona

1. O texto de cada página sai com a posição (x, y). O cabeçalho da ANP e o rodapé ficam de fora.
2. As páginas viram uma faixa contínua; cada **seção** começa no seu título ("Topos Estratigráficos",
   "Teste de Formação"…) e vai até o próximo. Uma tabela que continua na página seguinte, sem título, continua na
   mesma seção.
3. **Campos** ("Poço:", "Mesa Rotativa(m):"…): o valor é o texto logo abaixo do rótulo, na faixa de x entre ele e o
   próximo rótulo da linha.
4. **Tabelas**: cada coluna ocupa uma faixa fixa de x. Uma linha existe onde a coluna de referência (em geral o topo)
   tem um número; uma célula de duas linhas ("FILTRADO/ ÁGUA" + "FORMAÇÃO") junta-se à linha de cima.

Convenções do formulário respeitadas:

- números em pt-BR: `1.948,50` = 1948,5; `-1.854,40` = −1854,4;
- **"0,0" é o campo vazio**: profundidade 0,0 com cota 0,0, °API 0, pressão 0, vazão 0 não viram zero. Uma
  profundidade 0,0 com cota preenchida (o topo da formação de superfície) vale;
- coordenadas em graus:minutos:segundos (`-12:04:45,845`) viram graus decimais; latitude e longitude se distinguem
  pelo valor (no Brasil |longitude| > |latitude|);
- unidades como o formulário traz: profundidade medida em m, temperatura em °F, pressão em kgf/cm²
  (1 kgf/cm² = 14,2233 psi), peso da lama em lb/gal. A ficha mostra °C e psi ao lado, só para leitura;
- siglas (ocorrência C/D, fluorescência PL/EP, corte LT/MD/IM…, tipo de teste TFR/PT/TC/TCA) ficam como estão: o
  formulário não traz a legenda.

O que não está na posição esperada é ignorado, nunca inventado. Um PDF sem texto (imagem) ou que não é um
formulário CDPE fica registrado como "não lido", com o motivo.

**Título de seção fica sozinho na linha**: assim o título de coluna "Perfis" do NPR não é tomado pela seção "Perfis"
do Relatório de Descoberta.

**O mesmo dado em dois formulários** (o intervalo da análise de perfis no ND e no RFP, por exemplo) aparece uma
vez: vale o do formulário de maior prioridade — RFP, RFCP, Perfuração, Descoberta, Perfilagens, Reentrada — e o
outro fica anotado ("também em"). Profundidades diferentes contam como dados diferentes.

Leiaute conferido em 29/10/2026 em formulários de três poços: 1-AURI-12-RN e 3-BRSA-1151-RN (Potiguar) e
1-BRSA-1304-BA (Recôncavo). Alguns RFP não trazem o nome das unidades nos topos, só as profundidades: a ficha avisa.

## Onde cada dado é usado

| Dado | Onde aparece |
|---|---|
| Tudo | Ficha do poço › "Formulários da ANP — RFP, completação e perfuração" |
| Análise de perfis, canhoneados, testes com intervalo | Avaliação de formação: intervalos candidatos ("Dos formulários da ANP") |
| Temperaturas; fluido e peso de cada fase | Avaliação de formação: referência para o Rw (o SIAPP não converte) |
| Topos constatados | Perfis: linha marrom pontilhada; nome no eixo quando o poço não tem AGP |
| Canhoneados | Perfis: faixa vermelha na borda direita das trilhas |
| Sigla na base da operadora, nome para o operador | Outras grafias do poço (busca, mapa, ficha) |
| Pressões dos testes | Ficha; o gráfico pressão × profundidade fica para o leitor de pressões (bloco 9, item 2) |

## Onde fica guardado

Migração 10 do banco do projeto:

- `leituras` — um documento lido: arquivo, poço, leitor e **versão do leitor**, tipo do formulário, hash do arquivo,
  o poço que o formulário declara e se confere com a pasta, os dados completos (JSON) e o erro, se houve;
- `dados_poco` — uma linha por dado com profundidade: tipo (topo, indício, teste_formacao, temperatura, canhoneado,
  fase…), nome, topo, base, cota, valor, unidade, texto, extras, página.

Ler de novo substitui. Quando o leitor melhora (`VERSAO` maior), os documentos lidos pela versão anterior são lidos
de novo ao abrir o projeto; um arquivo que mudou (hash diferente) também. Um formulário que declara **outro poço**
(arquivo na pasta errada do portal) é lido, mas os dados não entram no poço da pasta e nenhum apelido é criado.

São dados da operadora/ANP, como o AGP: **não entram nos pacotes de contribuição** — qualquer um que baixe o mesmo
arquivo obtém a mesma leitura.

## Para os próximos leitores (bloco 9)

Um leitor novo é um módulo com `VERSAO`, `NOME`, `DOCUMENTOS`, `PRIORIDADE`, `reconhece(rel)` (pelo caminho:
nome e pasta), `ler(caminho)` e `itens(dados)` (e, opcional, `apelidos(dados)`), registrado em
`dados_poco.LEITORES`. Os outros leitores: pressões ([`pressoes.md`](pressoes.md)) e PVT ([`pvt.md`](pvt.md)). A leitura no download, na abertura do projeto, a
gravação, as versões e a ficha já funcionam para ele.
