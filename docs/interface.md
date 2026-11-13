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

Menu **Ajuda**: Guia do REATE (saiu do Início), Limites e confiabilidade (idem), Atalhos de teclado, Diagnóstico e Sobre (com a
versão, que saiu da barra).

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
