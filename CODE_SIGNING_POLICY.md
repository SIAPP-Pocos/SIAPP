# Política de assinatura de código (Code signing policy)

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by
[SignPath Foundation](https://signpath.org/).

Assinatura de código gratuita oferecida pela SignPath.io, com certificado da SignPath Foundation.

## O que é assinado

- `SIAPP.exe`, o programa;
- `SIAPP-<versão>-instalador.exe`, o instalador publicado em
  [Releases](https://github.com/SIAPP-Pocos/SIAPP/releases).

As bibliotecas de terceiros que vão no pacote (Python, NumPy, pywebview e as outras listadas em
`AVISOS-DE-TERCEIROS.txt`) **não** são assinadas pelo SIAPP: seguem com a assinatura de quem as publica, quando há.

Os arquivos assinados são montados pelo GitHub Actions a partir do código deste repositório
([`.github/workflows/instalador.yml`](.github/workflows/instalador.yml)), sem passar pelo computador de ninguém. Cada
versão só é assinada depois de aprovada à mão por um aprovador.

## Equipe e papéis

| Papel | Quem |
|---|---|
| Autores (*committers*) e revisores (*reviewers*) | [Ruan da Silva Nobre](https://github.com/nobrenadja9-jpg) |
| Aprovadores (*approvers*) | [Ruan da Silva Nobre](https://github.com/nobrenadja9-jpg) |

Contribuições de quem não faz parte da equipe (pull requests) são revisadas por um membro da equipe antes de entrar.
Todos os membros usam autenticação em dois fatores no GitHub e no SignPath.

## Privacidade (Privacy policy)

O SIAPP não coleta dados de uso, não tem telemetria e não envia informação sobre quem o usa. Ele só se conecta à
internet quando a pessoa pede uma ação que precisa disso, e só aos serviços públicos dessa ação:

| Serviço | Quando |
|---|---|
| Portal REATE da ANP (`reate.cprm.gov.br`) e páginas da ANP (`gov.br`) | Catálogo, levantamento do acervo, downloads |
| EPE, IBGE e INDE | Camadas de mapa e de infraestrutura (Viabilidade) |
| Banco Central (`api.bcb.gov.br`) | Índices de preço e câmbio (Viabilidade) |
| OpenStreetMap e Esri | Fundo dos mapas |
| GitHub (`github.com`, `api.github.com`) | Modelos de OCR do Tesseract; base comunitária (botão Atualizar) |

Os projetos, arquivos baixados e dados transcritos ficam só no computador de quem usa. O que vai para a base
comunitária sai apenas quando a pessoa exporta um pacote e escolhe compartilhá-lo, com o nome que ela mesma informa.

This program will not transfer any information to other networked systems unless specifically requested by the user
or the person installing or operating it.
