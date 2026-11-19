# Interface: Início, projetos, abas, menus, busca, atalhos e avisos

Desde a 0.57 (Início e projetos: 0.58). Código em `ui/js/interface.js` (menus, diálogo, ajuda, busca, atalhos, avisos), `ui/js/janelas.js` (abas e
layout) e `ui/estilo.css` (seção "interface (0.57)").

## Abas pelo fluxo do trabalho

| Aba | O que tem | Antes da 0.57 |
|---|---|---|
| Início | abrir o projeto, números, últimas mensagens | Projeto |
| 1 Acervo | catálogo e levantamento do REATE, busca por tipo, meus arquivos; em **Mais**: cadastro e produção da ANP, camadas, dados consolidados | Dados |
| 2 Documentos | ler, buscar, corrigir o OCR, transcrever | Documentos |
| 3 Perfis | curvas, intervalo-alvo, avaliação | Perfis |
| 4 Poços | mapa, filtros, ficha do poço | Mapa |
| 5 Correlação | seção estratigráfica | Interpretação › Seção |
| 6 Modelo 3D | bloco 3D | Interpretação › Bloco 3D |
| Mais ▾ | Viabilidade, Comunidade | abas soltas |

Por dentro, Correlação e Modelo 3D continuam sendo a mesma aba (`interp`, com `ui.subInterp`): a divisão da janela, as janelas
destacadas e as preferências não mudaram. Cada botão do topo tem `data-sub-interp` e só fica marcado com a sua sub-aba.

As subabas do Acervo e da Comunidade ficam no topo da área principal. Quando a subaba do Acervo não tem nada na lateral, a lateral
some (classe `sem-lateral`).

## Barra do alto

- **Nome do projeto** (a pasta): leva ao Início.
- **Buscar poço** (Ctrl+K): nome em qualquer grafia — `7-GMR-0013`, `gmr13`, nome do operador, apelido. Procura no cadastro da
  ANP, nos apelidos e nas pastas do REATE fora do cadastro (`motor/pocos.py`, `buscar`; API `buscar_pocos`). Enter abre a ficha.
- **⋯**: Dividir a janela, Abrir em janela.
- **Exportações**, **Ajuda** e **Configurações**.
- Cabe numa linha até 1.180 px de largura: primeiro somem os rótulos dos botões, depois a tecla da busca e o nome "SIAPP".

Menu **Ajuda**: Como usar o SIAPP (1.2), Guia do REATE (saiu do Início), Limites e confiabilidade (idem), Atalhos de
teclado, Diagnóstico, Novidades, Sobre (com a versão, que saiu da barra) e Apoie o projeto.

## Atalhos de teclado

| Ação | Padrão |
|---|---|
| Buscar poço | Ctrl+K |
| Início | Ctrl+0 |
| Abas 1 a 6 | Ctrl+1 … Ctrl+6 |
| Ação principal da tela (Conectar, Processar, Calcular, Montar…) | Ctrl+Enter |
| Exportações | Ctrl+E |
| Configurações | Ctrl+, |
| Menu Ajuda | F1 |
| Recolher ou abrir a barra lateral | Ctrl+B |
| Buscar no documento (Documentos) | Ctrl+F |
| Página anterior e próxima (Documentos, página aberta) | ← → |
| Próximo e anterior achado da busca (fixo) | F3, Shift+F3 |
| Fechar janela, menu ou painel (fixo) | Esc |

Ajuda › Atalhos de teclado › **Alterar**: aperte a nova combinação. Se ela já for de outra ação, as duas trocam. Só o que
mudou fica nas preferências (`"atalhos": {"m3": "Ctrl+Alt+P"}`); **Restaurar os padrões** apaga tudo. Dentro de um campo de
texto, teclas sem Ctrl ou Alt (as setas) ficam com o campo.

## Avisos de primeira vez

Antes de três ações em que o limite muda o que você faz, aparece um aviso curto:

| Ação | Botão | O aviso |
|---|---|---|
| Processar documentos (OCR) | `btn-processar` | OCR acha a página, não fornece números (6 de 18 profundidades erradas num teste real); número só entra transcrito e conferido |
| Calcular a avaliação | `av-calcular` | Rw sem estimativa automática (0,05 é ponto de partida); comparar com o referencial teórico e com a operadora; caliper e DRHO ruins ficam marcados |
| Montar o modelo 3D | `bl-montar` | Entre os poços é interpolação; conferir o erro em Validar; com menos de 8 poços a krigagem vira linear |

Aparece uma vez por sessão até você marcar **Não mostrar de novo** (preferência `avisos_vistos`). Para ver de novo, apague a
chave em `preferencias.json`. Os mesmos limites ficam sempre em Ajuda › Limites e confiabilidade.

## Avisos no canto e explicações

- **Erro** aparece também no canto superior direito por 7 s. **Concluído** só aparece lá quando encerra um trabalho de mais de 3 s
  (download, levantamento, OCR…). Clique para fechar. O rodapé e o Histórico continuam com todas as mensagens.
- Textos de ajuda longos da lateral (90 caracteres ou mais, sem botão dentro) ficam atrás de um **?** ao lado do título.
- Estados vazios: uma frase e, quando há, o botão da ação. O resto em **Saiba mais**.
- Correlação: "Achar poços ao longo de uma linha", "Desenho" e "Seções anteriores" vêm recolhidos; **Montar a seção** fica
  sempre à vista no pé da lateral.

## Início e projetos (0.58)

O Início mostra o **projeto aberto** (nome, bacias, pasta), os **projetos** em cartões e os **módulos** com o estado de cada um.

- **Projeto** é uma pasta com o seu banco (`projeto.sqlite`), arquivos baixados, textos e execuções. O principal continua
  sendo `ambiente_teste\`; os novos ficam em `projetos\<nome>\`, ao lado do SIAPP, fora do git. Uma pasta de projeto
  copiada para `projetos\` aparece sozinha.
- **Cartão**: nome (renomear muda só o nome, não a pasta), bacias, poços levantados, arquivos, documentos e perfis, e um
  minimapa com até 300 poços do projeto. Os números vêm do banco de cada projeto, lido em modo somente leitura
  (`motor/projetos.py`, `resumo`).
- **Novo projeto**: nome e bacias. Depois de criar, o SIAPP oferece abrir.
- **Abrir outro projeto**: com um projeto aberto, o SIAPP fecha e abre de novo já no outro (pelo lançador, quando existe):
  tudo começa limpo, sem dado de um projeto vazando para o outro. Com downloads ou OCR em andamento, recusa e explica.
  O escolhido fica em `projeto_atual` (preferências) e é o que abre da próxima vez.
- **Módulos**: uma ou duas linhas com números do projeto (API `inicio_resumo`) e o botão do próximo passo. O ponto antes da
  linha marca o que está esperando você (documentos sem texto, cadastro da ANP não baixado).

As preferências (cores, atalhos, arranjo, lista de projetos) são do computador, não do projeto: ficam em
`ambiente_teste\preferencias.json` para todos os projetos.

Ajuda › **Novidades desta versão** mostra as três últimas versões do `CHANGELOG.md`.

## Largura da barra lateral (0.59)

Arraste a borda direita de qualquer barra lateral (o cursor vira ↔) para alargar ou estreitar, de 240 a 720 px. Fica
guardado por aba (preferência `larguras`); dois cliques na borda voltam ao padrão.

## Ficha do poço em página inteira (0.60)

Na ficha (aba Poços), **Página inteira** põe a ficha no lugar do mapa, com as seções em colunas de ~460 px; **Ao lado do
mapa** volta à gaveta. A escolha fica nas preferências (`ficha_cheia`). Com a ficha fechada, o mapa aparece sempre.

## Trocar de aba (0.61)

Mostrar uma aba relê os dados só se algo mudou na pasta do projeto desde a última vez (ou depois de 5 minutos). Clicar na
aba que já está à frente, ou **F5** ("Reler a aba", trocável em Ajuda › Atalhos de teclado), relê na hora. Início e Comunidade
relêem sempre.

## Mapa com o cadastro inteiro (0.62)

`pocos_mapa` (motor/pocos.py) devolve só `id, lat, lon, campo, situacao, reate, baixados, fatos, acervo`, com lat/lon
arredondadas em 5 casas, e `dicionarios` para campo, situação e acervo (a linha leva o número; `linhas_mapa` desfaz no
Python). Na janela, `marcadores` (id → marcador) é reaproveitado entre consultas e trocas de cor ou legenda: só se cria
o que é novo e só se tira o que saiu. Um só ouvinte no `L.featureGroup` abre a ficha; o rótulo é criado no primeiro
`mouseover`. Medição (32 mil poços sintéticos, navegador dos testes): todas as bacias 0,75 s; uma bacia de 12 mil,
0,29 s; trocar a cor, 0,10 s.

## Navegação (0.64)

- **Roda do mouse**: em perfis e mapas, a roda rola a página; o gráfico só a usa depois de clicado (perfil) ou com Ctrl
  (zoom). Assim, rolar a página nunca fica preso num gráfico.
- **Perfis** (`ui/js/perfis.js`): navegador do poço inteiro (`#pf-nav`, miniatura de uma curva com 600 pontos), faixa
  buscada 3× maior que a vista (`pf.buf`; `grafico_perfil` aceita `max_pontos`), altura das trilhas pela janela,
  escala vertical (96 ppp), teclado com o perfil ativo.
- **Caixas que abrem** (`acompanharAbertura`, interface.js): numa coluna que rola, a coluna desce até mostrar a caixa
  inteira, acima do pé fixo, sem passar do título dela.
- **Mapa 2D do bloco** (`ui/js/bloco.js`): o SVG do motor é ampliado e arrastado por CSS (sem refazer o desenho); o
  motor manda junto a posição da área do mapa e a grade reduzida (≤ 160 × 160) para a leitura sob o mouse.

## "Ver arquivos" da ficha (0.65)

`mostrarPocoNoCatalogo` (mapa.js) chama `catalogo_abrir_poco` (ponte/catalogo.py) com bacia, categoria, nome e caminho
da pasta (tabela `reate`). A ponte conecta se a bacia não está conectada, lê `catalogo/<bacia>/<categoria>.json` se
existir (senão devolve só este poço, `parcial`), e a janela desenha conexão e lista com as mesmas funções do clique
manual (`desenharConexao`, `desenharListaPocos`, catalogo.js) e abre a gaveta (`explorarPoco`).

## Mascote, "Como usar o SIAPP" e doação à vista (1.2)

- **Mascote**: o guaxinim de capacete, no canto de baixo à direita do Início (`#mascote-ajuda`, fora do fluxo da página;
  o Início ganha espaço embaixo para nada ficar atrás dele). Em janela estreita (até 1.000 px), fica menor e sem o
  balão. Só aparece no Início.
- **Como usar o SIAPP** (`ui/js/ajuda.js`): clicar no mascote ou em Ajuda › Como usar o SIAPP. Dez assuntos, um por
  etapa do trabalho; cada um com uma pose do mascote, uma fala curta, os passos e, quando cabe, um botão que fecha a
  ajuda e leva à aba (`trocarAba`). Os rótulos de botão aparecem entre `**` no texto e saem em negrito;
  `tests/test_ajuda.py` confere que cada um existe na tela, então renomear um botão sem atualizar a ajuda quebra o teste.
- **Poses** em `ui/img/mascote/` (acenando, apontando, pensando, joinha, lupa, ops): PNG com fundo transparente, 320 px
  de altura e 256 cores (menos de 25 KB cada). Desenhadas no Masko a partir do mascote do autor, com o S do SIAPP em
  pixel no capacete.
- **Doe**: a xícara à direita dos projetos (`#ini-doe`) abre a mesma tela de Ajuda › Apoie o projeto
  (`abrirDoacao`). Aparece e some junto com o item do menu: só quando `recursos/doacao.json` tem chave Pix ou link.
- **Setas no visor**: com a página em tela cheia, ← → (os mesmos atalhos de "Página anterior/Próxima página") trocam a
  página do visor (`paginaVisor`, visor.js), a não ser que a página ampliada passe da largura da tela: aí as setas rolam.

## Tela "Apoie o SIAPP" (1.3)

`ui/js/apoio.js`, aberta por Ajuda › Apoie o projeto, pela xícara "Doe" do Início e pelo botão do "Sobre". Tudo o que
ela mostra vem de `recursos/doacao.json` (lido por `motor/doacao.py`); sem chave Pix nem link, a tela fica escondida.

- **Abertura**: o mascote acenando e a fala (`texto`), que deixa claro que doar é opcional.
- **Quem faz o SIAPP** (`sobre`, uma lista de parágrafos) e o link **Fale comigo no LinkedIn** (`linkedin`; só aceita
  `https://www.linkedin.com/in/...`, e sem ele o link não aparece). Sem foto: o mascote representa o autor. Logo abaixo,
  **Trabalhos publicados nos PIBICs** (`publicacoes`: título, evento e link para os anais).
- **Apoie com um Pix**: os botões de `valores` (padrão: Um cafezinho R$ 5, Um lanche R$ 15, Uma tarde de código R$ 30) e
  "Outro valor". Cada escolha pede ao motor (`doacao_pix`) o "copia e cola" com o valor (campo 54 do BR Code) e o **QR
  Code** em SVG, feito pelo `segno` (BSD-3-Clause, sem internet). A tela abre sem valor escolhido: o QR e o código são
  os de sempre, e o valor fica para o app do banco.
- **Outras formas de ajudar, sem dinheiro**: estrela no GitHub, citar o SIAPP ("Cite this repository"), compartilhar
  correções pela Comunidade (botão que leva à aba), relatar um problema e indicar a um colega.
- **Fim**: o mascote fazendo joinha e "Doar é opcional: o SIAPP é gratuito e continua igual para todos."
- Não há mural de apoiadores (talvez no futuro, só com nomes autorizados).
