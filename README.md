<div align="center">

<img src="recursos/icone/siapp-256.png" alt="Ícone do SIAPP" width="112">

# SIAPP

**Sistema Integrado de Aquisição e Processamento de Perfis**

Transforma o acervo público de poços da ANP em dados organizados, pesquisáveis e prontos para análise.<br>
Gratuito, de código aberto, para Windows.

[![versão](https://img.shields.io/badge/vers%C3%A3o-1.4.0-success)](https://github.com/SIAPP-Pocos/SIAPP/releases/latest)
[![testes](https://github.com/SIAPP-Pocos/SIAPP/actions/workflows/testes.yml/badge.svg)](https://github.com/SIAPP-Pocos/SIAPP/actions/workflows/testes.yml)
[![licença: AGPL-3.0](https://img.shields.io/badge/licen%C3%A7a-AGPL--3.0-blue)](LICENSE)
![Windows 10 e 11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4)

**[Baixar o instalador](https://github.com/SIAPP-Pocos/SIAPP/releases/latest)** ·
[Documentação](docs/README.md) ·
[Novidades](CHANGELOG.md) ·
[Dúvidas](https://github.com/SIAPP-Pocos/SIAPP/discussions) ·
[Como citar](#como-citar)

</div>

---

## Por que existe

O portal [REATE](https://reate.cprm.gov.br/anp/TERRESTRE) da ANP guarda, de graça, os dados de milhares de poços das
bacias terrestres brasileiras. Na prática, usá-los é difícil: formatos binários antigos (DLIS, LIS em fita), documentos
escaneados, nomes de pasta sem padrão e nenhum índice do que existe em cada poço.

O SIAPP faz esse trabalho pesado: encontra, baixa, lê e organiza, guardando de onde veio cada número. Assim, estudantes
e pesquisadores começam pela análise, e não pela garimpagem.

## O que dá para fazer

| | |
|---|---|
| **Acervo** | Navegar pelas 24 bacias terrestres do REATE, ver o que cada poço tem **sem baixar** e baixar em segundo plano, com retomada |
| **Documentos** | Abrir PDFs e TIFs escaneados, buscar texto com OCR e transcrever dados com a página e o trecho como fonte |
| **Perfis** | Ler DLIS, LIS e LAS, ver as curvas em trilhas, avaliar a formação (argilosidade, porosidade, saturação, *net pay*) e exportar LAS e CSV |
| **Poços** | Mapa com o cadastro da ANP, filtros pelo acervo e a ficha completa de cada poço |
| **Correlação** | Seção estratigráfica pelos topos de formação, em cota ou nivelada, com a legenda de litologias dos perfis compostos da Petrobras |
| **Modelo 3D** | Superfícies de topo, bloco fechado, mapas, volumetria e exportação para simuladores (ECLIPSE) |
| **Viabilidade** | Campo × infraestrutura (gasodutos, UPGN, H₂, fontes de CO₂), produção da ANP e custo do duto |
| **Comunidade** | Compartilhar correções e transcrições com a [base comunitária](https://github.com/SIAPP-Pocos/Comunidade) |

A lista completa, aba por aba, está em [O que o SIAPP faz](docs/funcionalidades.md).

## Instalar

1. Baixe **`SIAPP-<versão>-instalador.exe`** na [última versão](https://github.com/SIAPP-Pocos/SIAPP/releases/latest).
2. Dê dois cliques. Não precisa de administrador nem de Python.
3. Escolha onde guardar os projetos (o padrão é **Documentos\SIAPP**) e conclua.

O SIAPP aparece no menu Iniciar. Se o Windows avisar "editor desconhecido", clique em **Mais informações › Executar
assim mesmo**. Para atualizar, instale a versão nova por cima: os projetos continuam onde estão, e desinstalar não os
apaga. Detalhes em [Instalador do Windows](docs/instalador.md).

## Primeiros passos

1. **Início › Abrir o projeto**: o diálogo já abre no *Projeto principal*; é só confirmar.
2. **1 Acervo › Catálogo do REATE**: escolha uma bacia, uma categoria e um poço; marque o que quer e baixe.
3. **2 Documentos** e **3 Perfis**: o que foi baixado abre ali, com busca, OCR e gráfico das curvas.
4. **4 Poços**: veja os poços no mapa e abra a ficha de cada um.
5. **5 Correlação** e **6 Modelo 3D**: monte a seção e o bloco com os topos de formação.

Nada vem marcado para download: você escolhe o que baixar. Na dúvida, clique no **mascote** no canto do Início: ele
abre o passo a passo de cada etapa (também em **Ajuda › Como usar o SIAPP**).

## Dados e procedência

- **Nenhum arquivo original do REATE é redistribuído** aqui. O SIAPP baixa direto do portal público, e cada arquivo é
  registrado com o caminho de origem e a data.
- **OCR serve para encontrar páginas, não para fornecer números.** Números só entram no banco por transcrição
  conferida na imagem, com o documento (SHA-256), a página e a caixa como fonte. Ver [OCR](docs/ocr.md).
- Os dados vêm da ANP, nas condições de uso dela; mapas © colaboradores do OpenStreetMap e Esri.

## Contribuir

- **Achou um erro ou tem uma ideia?** Abra uma [issue](https://github.com/SIAPP-Pocos/SIAPP/issues/new/choose).
- **Dúvida de uso?** Pergunte em [Discussions](https://github.com/SIAPP-Pocos/SIAPP/discussions).
- **Corrigiu um dado ou transcreveu um documento?** Compartilhe pela aba Comunidade: vai para o
  [Comunidade](https://github.com/SIAPP-Pocos/Comunidade).
- **Quer mexer no código?** Veja [Como contribuir](CONTRIBUTING.md).

<details>
<summary><b>Rodar a partir do código</b> (para quem desenvolve)</summary>

<br>

1. Instale o Python 3.10 ou mais novo ([python.org](https://www.python.org/downloads/)).
2. Clone este repositório e dê dois cliques em **`iniciar.bat`**. Na primeira vez, uma janelinha cria o ambiente
   (`.venv`) e instala as dependências; depois, o atalho `SIAPP.lnk` abre direto e traz as versões novas.
3. Os dados do desenvolvimento ficam em `ambiente_teste/` (fora do git).

Testes:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -m "not interface"        # motor e ponte, sem internet (portal, ANP e GitHub simulados)
pytest -m interface              # interface num Chromium sem tela (precisa do Playwright)
```

Arquitetura em [docs/arquitetura.md](docs/arquitetura.md); lançador em [docs/lancador.md](docs/lancador.md).

</details>

## Apoie

O SIAPP é e continuará gratuito. Se ele foi útil para você, há uma opção de doação no próprio aplicativo
(**Ajuda › Apoie o projeto**). Doar é opcional: o SIAPP é igual para todos.

## Como citar

Use o botão **Cite this repository**, no alto desta página (ele lê o [`CITATION.cff`](CITATION.cff)), ou:

> Nobre, R. S. *SIAPP — Sistema Integrado de Aquisição e Processamento de Perfis* (versão 1.4.0). Universidade Federal
> de Alagoas, 2026. Disponível em: https://github.com/SIAPP-Pocos/SIAPP.

## Assinatura digital e privacidade

O instalador do SIAPP **ainda não tem assinatura digital**. Por isso o Windows pode avisar na primeira vez que você
abre ("O Windows protegeu o computador": clique em **Mais informações › Executar assim mesmo**). Se aparecer "Uma
política de Controle de Aplicativo bloqueou este arquivo", veja
[o que fazer](docs/instalador.md#uma-política-de-controle-de-aplicativo-bloqueou-este-arquivo-código-4551).

O que o SIAPP acessa na internet, e quando: [privacidade](CODE_SIGNING_POLICY.md#privacidade-privacy-policy).

## Licença

Código sob a **GNU AGPL-3.0** ([LICENSE](LICENSE)): use, estude, modifique e redistribua à vontade, mantendo o código
aberto. As licenças das bibliotecas usadas estão em [O que o SIAPP faz](docs/funcionalidades.md#licenças-das-bibliotecas)
e, no instalador, em `AVISOS-DE-TERCEIROS.txt`.

## Autoria

Desenvolvido por **Ruan da Silva Nobre** (Engenharia de Petróleo, UFAL) no Programa Institucional de Bolsas de Iniciação
Científica (PIBIC), sob orientação da Profa. Zenilda Vieira Batista.
