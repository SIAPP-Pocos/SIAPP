# Instalador do Windows

Desde a 0.67, o SIAPP também sai como um instalador comum do Windows: `SIAPP-<versão>-instalador.exe`. Quem só quer
usar o programa não precisa de Python, git nem do lançador; quem desenvolve continua com o clone e o `SIAPP.vbs`
(ver [`lancador.md`](lancador.md)).

## O que o instalador faz

| Item | Onde fica |
|---|---|
| Programa (`SIAPP.exe` e a pasta `_internal` com Python e bibliotecas) | `%LOCALAPPDATA%\Programs\SIAPP` |
| Atalhos | Menu Iniciar › SIAPP (e na Área de Trabalho, se marcar) |
| Projetos | `<pasta dos projetos>\Projetos\Projeto principal` e os outros projetos ao lado, em `Projetos\` |
| Modelo do OCR | `<pasta dos projetos>\recursos\tessdata` |
| A pasta dos projetos | a escolhida na instalação (padrão `Documentos\SIAPP`; a variável `SIAPP_DADOS` ganha dela) |
| Desinstalar | Configurações do Windows › Aplicativos › SIAPP |

- Instala só para o usuário: não pede administrador.
- **Pasta dos projetos (1.0)**: o instalador pergunta onde guardar os projetos, depois da pasta do programa. Quem já
  usa o SIAPP escolhe a mesma pasta de antes. Dentro dela ficam `Projetos\Projeto principal` e os outros projetos
  (1.1; quem tinha `ambiente_teste` e `projetos\` da 1.0 tem as pastas renomeadas sozinhas na primeira abertura). A escolha fica em `pasta_dados.txt`, ao lado do `SIAPP.exe`,
  e volta marcada na próxima atualização. Sem perguntas: `SIAPP-1.0.0-instalador.exe /VERYSILENT /PASTADADOS="D:\SIAPP"`.
- Ao desinstalar, a pasta dos projetos **fica** (os projetos são seus).
- Numa atualização, a pasta `_internal` da versão anterior é apagada antes de copiar a nova, para não misturar
  bibliotecas de versões diferentes.
- A janela usa o Microsoft Edge WebView2, que já vem no Windows 10 e 11.
- O modelo de português do OCR (~8 MB) é baixado no primeiro documento escaneado, para `<pasta dos projetos>\recursos\tessdata`.
- O Windows pode avisar "editor desconhecido" (SmartScreen): o `.exe` ainda não tem assinatura digital. Clique em
  **Mais informações › Executar assim mesmo**.

### "Uma política de Controle de Aplicativo bloqueou este arquivo" (código 4551)

Aparece ao abrir o `SIAPP.exe` quando o **Controle Inteligente de Aplicativos** (Smart App Control) do Windows 11 está
ligado, ou num computador de empresa ou universidade com política de aplicativos. Enquanto o `.exe` não tiver
assinatura digital, não há como liberar só o SIAPP: o próprio Windows não permite exceção por aplicativo.

- **Computador pessoal:** Segurança do Windows › Controle de aplicativos e navegador › Configurações do Controle
  Inteligente de Aplicativos › Desativado. Isso tira uma proteção do Windows para todos os programas, então a decisão é
  de quem usa o computador; atualizações recentes do Windows permitem ligar de novo sem reinstalar.
- **Computador gerenciado** (empresa, laboratório): só o setor de TI pode liberar.
- **Solução definitiva:** assinar o `.exe` (ver o roteiro). Com assinatura válida, o Controle Inteligente deixa o
  programa abrir.

## Como sai uma versão

Cada versão é publicada por uma pessoa: GitHub › **Releases** › **Draft a new release** › etiqueta `vX.Y.Z` (alvo
`main`) › **Publish release**. A etiqueta dispara o workflow `instalador`, que monta, testa e anexa o instalador e o
código-fonte à versão em uns 5 minutos. Se algum teste falhar, nada é anexado.

## Como é montado

Tudo no GitHub, numa máquina Windows (`.github/workflows/instalador.yml`), à mão (Actions › instalador › Run workflow)
ou ao chegar uma etiqueta `vX.Y.Z`:

1. Instala as bibliotecas de `requirements.txt` e o PyInstaller.
2. Escreve a versão (de `motor/__init__.py`) nas propriedades do `.exe` (`instalador/versao.modelo.txt`).
3. **PyInstaller** (`instalador/siapp.spec`) monta `dist/SIAPP/`: `SIAPP.exe` sem console, a interface (`ui/`),
   `recursos/` (menos o modelo do OCR), `CHANGELOG.md`, `LICENSE` e `AVISOS-DE-TERCEIROS.txt`. Ficam fora bibliotecas que
   o PyMuPDF 2 traz mas o SIAPP não usa (pymupdf4llm, onnxruntime etc.).
4. **Confere o pacote**: `SIAPP.exe --verificar` importa todos os módulos do motor, da ponte e do lançador e as
   bibliotecas, procura os arquivos da interface e grava `verificar.json`; qualquer erro para a montagem.
5. **Confere a janela**: `SIAPP.exe --verificar-janela` abre a janela de verdade, espera a interface pedir a versão ao
   motor (WebView2 → página → scripts → ponte → Python) e fecha sozinho; grava `verificar-janela.json`.
6. **Inno Setup** (`instalador/siapp.iss`) faz o instalador.
7. **Testa o instalador**: instala sem perguntas, confere o `.exe` e o atalho do menu Iniciar, abre a janela do SIAPP
   instalado (`--verificar-janela`) e desinstala.
8. Guarda o instalador e o **código-fonte** (`git archive`) em *Artifacts* da execução, por 30 dias. Com etiqueta
   `vX.Y.Z` (que tem de bater com a versão), anexa os dois à página da versão (Releases).

## Como baixar

- **Uma versão etiquetada**: GitHub › SIAPP › Releases › `vX.Y.Z` › `SIAPP-X.Y.Z-instalador.exe`.
- **Qualquer montagem**: GitHub › Actions › instalador › a execução › Artifacts › `SIAPP-X.Y.Z-instalador` (vem em .zip).

Enquanto o repositório for privado, só quem tem acesso a ele baixa. Ao entregar o instalador a outra pessoa, entregue
junto o `SIAPP-X.Y.Z-codigo-fonte.zip`: a licença (AGPL-3.0) dá a quem recebe o programa o direito ao código.

## Como cada um recebe as versões novas

| | Pelo clone + atalho (quem desenvolve; hoje, o Ruan) | Pelo instalador (quem só usa) |
|---|---|---|
| De onde vem | GitHub, branch `main` | GitHub, página da versão (Releases) |
| Quando atualiza | **a cada abertura pelo atalho**: o lançador faz `git fetch` e avança a pasta para a versão nova (só se nada foi mudado à mão; senão avisa e abre a versão que está); depois instala as bibliotecas novas, se houver | quando a pessoa baixa o instalador novo e instala por cima |
| Aviso | "SIAPP atualizado: 0.67.2 → 0.68.0" na primeira abertura depois da atualização | — |
| Desligar | Configurações › "Atualizar o SIAPP ao abrir" | — |
| Os dados | ficam em `ambiente_teste\` e `projetos\`, que o git não toca | ficam em `<pasta dos projetos>\Projetos\`, que o instalador não toca |
| O que precisa ter | git e internet (sem eles, abre a versão que está) | nada |

Falta, para quem usa o instalador, um aviso de "versão nova disponível" dentro do SIAPP: depende de o repositório ser
público (a consulta às versões do GitHub sem login só funciona em repositório público).

## Modo instalado, no código

`ponte/base.py` sabe se está instalado (`sys.frozen` do PyInstaller):

| | Pelo código | Instalado |
|---|---|---|
| `PASTA_APP` (interface, recursos) | pasta do clone | `_internal` do PyInstaller |
| `PASTA_DADOS` | pasta do clone | a de `SIAPP_DADOS`; senão a de `pasta_dados.txt`; senão `Documentos\SIAPP` |
| Reabrir o SIAPP (trocar de projeto) | `pythonw siapp.py` pelo lançador | o próprio `SIAPP.exe` |
| Atalho `SIAPP.lnk` na pasta | criado na primeira abertura | não (o instalador cria os do menu) |
| Atualizar | `git pull` no lançador | instalar a versão nova por cima |

O processo do OCR (multiprocessing, modo *spawn*) reabre o próprio `SIAPP.exe`; por isso `siapp.py` chama
`multiprocessing.freeze_support()` antes de tudo.
