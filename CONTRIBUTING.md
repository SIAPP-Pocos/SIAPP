# Como contribuir

Obrigado pelo interesse. Há duas formas de contribuir:

## 1. Com dados (a mais valiosa)

Correções de texto, palavras do dicionário e transcrições conferidas vão para o
repositório **`siapp-dados`**, não para este. O SIAPP gera o pacote de contribuição;
as instruções estão no README daquele repositório.

## 2. Com código

1. Abra uma *issue* descrevendo o problema ou a proposta antes de começar algo grande.
2. Crie um ramo a partir de `main` (`git switch -c minha-melhoria`).
3. Rode os testes: `pytest`. Todo comportamento novo do motor deve vir com teste.
4. Abra um *pull request* explicando **o que** mudou e **por quê**.

### Princípios do projeto

- **O motor não conhece a interface.** Toda lógica fica em `motor/`; `ponte/` só traduz
  chamadas da janela (uma parte por aba) e `ui/js/` tem um script por aba.
- **Nenhum dado sem procedência.** Todo arquivo e todo número precisa apontar para a origem.
- **Nada é apagado em silêncio.** Correções são camadas por cima do original; o QC marca, não remove.
- **Limitação declarada vale mais do que limitação escondida.** Se algo não é confiável
  (ex.: números lidos por OCR), a interface diz.
- **Testes não acessam a internet.** O portal, a ANP e o GitHub são simulados em `tests/`.
  Mudou a interface? Rode também os testes de interface (`tests/test_interface.py`, com Playwright).
- **O banco evolui por migração.** Mudança de tabela = novo item em `motor/banco.py:MIGRACOES`,
  nunca edição de um item publicado.

### Mensagens de commit

Use o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/):
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`. Ex.: `fix: retomar download quando o servidor ignora Range`.

### Ramos e versões

- `main` está sempre funcionando; ninguém envia direto para ela — tudo entra por *pull request*.
- Nome do ramo: `tipo/descricao-curta` (ex.: `feat/exportar-contribuicao`, `fix/retomada-download`).
- Versões seguem [SemVer](https://semver.org/lang/pt-BR/) com etiqueta `vX.Y.Z`; cada versão
  tem sua seção no `CHANGELOG.md`.

### Etiquetas das issues

`tipo:` (erro, funcionalidade, documentação, manutenção) · `área:` (catálogo, download,
ocr, busca, interface, instalação) · `prioridade: alta` · `triagem` (ainda não avaliada) ·
`bom primeiro issue` (bom para quem está começando).

Ao participar, você concorda com o [Código de conduta](CODE_OF_CONDUCT.md).
