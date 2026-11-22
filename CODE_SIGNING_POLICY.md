# Política de assinatura de código (Code signing policy)

**Situação:** o SIAPP **ainda não tem assinatura digital**. Esta política diz como vai ser quando tiver, e a seção de
privacidade já vale hoje. Enquanto isso, se o Windows bloquear o programa, veja
[como liberar](docs/instalador.md#uma-política-de-controle-de-aplicativo-bloqueou-este-arquivo-código-4551).

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

O SIAPP não coleta dados de uso, não tem telemetria e não envia informação sobre quem o usa. Ele se conecta à
internet quando a pessoa pede uma ação que precisa disso, só aos serviços públicos dessa ação, e numa única consulta
automática (veja a última linha da tabela):

| Serviço | Quando |
|---|---|
| Portal REATE da ANP (`reate.cprm.gov.br`) e páginas da ANP (`gov.br`) | Catálogo, levantamento do acervo, downloads |
| EPE, IBGE e INDE | Camadas de mapa e de infraestrutura (Viabilidade) |
| Banco Central (`api.bcb.gov.br`) | Índices de preço e câmbio (Viabilidade) |
| OpenStreetMap e Esri | Fundo dos mapas |
| GitHub (`github.com`, `api.github.com`) | Modelos de OCR do Tesseract; base comunitária (botão Atualizar); desde a 1.4, **Enviar para a comunidade**: entrada com a conta do GitHub (por código) e envio do pacote que a pessoa confirmou, como issue no repositório Comunidade. O acesso fica cifrado no computador (proteção de dados do Windows) e sai com "Sair" |
| GitHub (`api.github.com`), sozinho ao abrir | Desde a 1.3, no máximo uma vez por dia: pergunta qual é a última versão do SIAPP e da base comunitária (nada é enviado além do pedido). Desliga em Configurações e em Comunidade › "Procurar sozinho" |

Os projetos, arquivos baixados e dados transcritos ficam só no computador de quem usa. O que vai para a base
comunitária sai apenas quando a pessoa exporta um pacote e escolhe compartilhá-lo, com o nome que ela mesma informa.

This program will not transfer any information to other networked systems unless specifically requested by the user
or the person installing or operating it. The only exception is the once-a-day check for a newer version of SIAPP and
of the community database (a plain request to `api.github.com`, carrying no user data), which can be turned off.
