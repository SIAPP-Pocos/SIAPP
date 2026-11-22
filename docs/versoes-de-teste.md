# Versões de teste (desde a 1.4.1)

Toda versão nova sai primeiro **como teste**, só para quem marcou em Configurações "Receber também as versões de
teste". Só depois de testada no Windows ela vira a versão de todo mundo. Assim, um erro que os testes automáticos não
pegam (o Windows de verdade, o GitHub de verdade, uma configuração do lado do mantenedor) aparece para o testador, e
não para quem usa.

## O caminho de cada versão

1. **Desenvolvimento** (sessão do Claude): código, testes automáticos (`pytest -m "not interface"` e `-m interface`,
   aqui e no GitHub, Linux e Windows), `CHANGELOG.md`, guia de teste. Push para `main`.
2. **Versão de teste** (Ruan, pelo site): Releases › Draft a new release › etiqueta `vX.Y.Z` › alvo `main` ›
   marcar **Set as a pre-release** › Publish. O GitHub monta o instalador e anexa, como sempre.
   - Quem está com "Receber também as versões de teste" ligado recebe o aviso "Saiu o SIAPP X.Y.Z (versão de teste)" e
     atualiza com um clique. Os outros não veem: a consulta normal (`releases/latest`) ignora as de teste.
3. **Teste no Windows** (Ruan): a seção da versão no `docs/guia-de-teste.md`, que diz o que conferir em poucos minutos.
   - Deu problema: print ou mensagem para o Claude, que corrige e sobe a próxima (`X.Y.Z+1`, de novo como teste). A
     versão de teste que falhou pode ser apagada da página Releases (e a etiqueta, em Tags), para não confundir.
     O `CHANGELOG.md` junta tudo numa seção só, a da versão que vai para todos.
4. **Liberar para todos** (Ruan): na versão testada, Edit › desmarcar **Set as a pre-release** › marcar **Set as the
   latest release** › Update release. A partir daí, todo SIAPP 1.3+ recebe o aviso.

## O que não dá para testar antes, e como reduzir

- **Integrações com configuração do lado de fora** (aplicativo do GitHub, permissões do repositório Comunidade,
  assinatura): o Claude não enxerga essas telas. Quando uma versão depender de uma configuração assim, o guia de teste
  diz qual é e como conferir, antes do primeiro teste.
- **O Windows de verdade** (instalador, atualização, Controle Inteligente de Aplicativos): o GitHub monta e abre o
  `SIAPP.exe` no Windows a cada versão (`verificar.json`), mas a instalação por cima e a reabertura só o testador vê.
