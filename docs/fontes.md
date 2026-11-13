# Fontes e prioridade (0.63)

Configurações › **Fontes e prioridade** reúne, numa tela do projeto, o que antes ficava em dois lugares:

| Lista | O que decide | Onde mudava antes | Guardada em |
|---|---|---|---|
| **Topos de formação** (AGP, transcrito, RFP, calha) | qual fonte vale para o topo de cada unidade, quando você não escolheu outra na ficha do poço | Acervo › Dados consolidados | banco do projeto (`meta.precedencia_topos`) |
| **Zonas produtoras** (tabela sua, marcados, canhoneados, testes, análise de perfis, fluido, zonas do AGP) | a ordem e quais fontes o Modelo 3D usa para os intervalos de reservatório | painel do Modelo 3D (só na tela, perdida ao fechar) | banco do projeto (`meta.prioridade_zonas`) |

O cálculo continua separado — topo de formação e intervalo de reservatório são coisas diferentes (`motor/topos.py`,
`motor/zonas.py`) —, mas os rótulos, a ordem e o que está ligado moram em `motor/fontes.py`. Cada mudança grava na hora e
fica no histórico do projeto (`definiu_precedencia_topos`, `definiu_fontes_zonas`). Dados consolidados e o painel de zonas
do Modelo 3D mostram o resumo e um botão para cá. Importar a sua tabela de zonas liga a fonte "tabela"; apagá-la desliga.

## Como o SIAPP conta "perfil digital"

A revisão de 11/11 (A13) achou três critérios no mesmo app, com números diferentes (4.562 × 4.557). Agora cada número vem
com o critério ao lado, e esta tela mostra os três lado a lado (`motor/fontes.py`, `contar_perfil`):

| Critério | Pergunta que responde | Onde aparece |
|---|---|---|
| **conferido no portal** (`conteudo`) | O levantamento abriu os arquivos e achou DLIS, LIS ou LAS pelo conteúdo? | Levantamento, mapa (cor por acervo) |
| **pasta no portal** (`pasta`) | O poço tem uma pasta com nome de perfis digitais? (não abre os arquivos) | Procurar por tipo de dado |
| **baixado** (`baixado`) | Algum DLIS, LIS ou LAS do poço está no projeto? | — |

O painel da Comunidade usa "baixado **ou** conferido no portal" (até a 0.62 contava `n_perfil > 0`, que incluía pasta só
com imagem). Todos contam **poços distintos**: a tabela de situações do levantamento conta **pastas** do portal (um poço
pode estar em duas categorias), e a tela agora diz isso ao lado. No projeto do Ruan (13/11/2026): Potiguar com 8.574
pastas para 8.510 poços; 6.551 pastas com perfil digital para 6.530 poços.
