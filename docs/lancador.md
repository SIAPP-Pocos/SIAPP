# Lançador silencioso (0.47)

Faz o SIAPP abrir como um programa: sem janela de prompt, com uma janelinha de carregamento.

## Fluxo

1. `SIAPP.lnk` (ou `iniciar.bat`) abre o **`SIAPP.vbs`** pelo `wscript`, que não cria console.
2. O `.vbs` limpa `PYTHONHOME`/`PYTHONPATH` e chama `pyw -3 SIAPP.pyw` (o Python Launcher sem console). Se não
   houver `pyw`, tenta o `pythonw.exe` da `.venv`; se nenhum funcionar, mostra uma caixa de mensagem.
3. O **`SIAPP.pyw`** abre a janelinha (`lancador/janela.py`, tkinter) no Python do sistema, porque a `.venv` pode
   ainda não existir. Por isso o pacote `lancador/` usa só a biblioteca padrão.
4. Em segundo plano (`lancador/passos.py`), três passos: **Conferindo os arquivos** → **Preparando os
   componentes** → **Abrindo o projeto**.
5. O app abre com o `pythonw.exe` da `.venv` (`siapp.py`). Quando a janela principal aparece, o `siapp.py` grava
   `ambiente_teste/.abriu` (caminho em `SIAPP_SINAL`); o lançador vê o arquivo e fecha a janelinha.

## Preparar os componentes

- Procura um Python que sirva (3.9+, com `venv` e `ensurepip`), nesta ordem: o Python que roda o lançador; `py -3`;
  `%LOCALAPPDATA%\Programs\Python\Python3*`; Python da Microsoft Store; `where python`. Ignora o MySQL Shell e o atalho
  da loja em `WindowsApps\`. Nunca chama "python" puro.
- A `.venv` é testada com `python -m pip --version`; se não roda (pasta movida ou renomeada), é apagada e recriada.
- `pip install -r requirements.txt` só roda quando o `requirements.txt` mudou (marca em `.venv/.requisitos`).
- Todos os subprocessos usam `CREATE_NO_WINDOW`.

## Quando algo falha

A janelinha mostra a mensagem em português simples, com **Copiar detalhes** e **Fechar**. O detalhe completo vai
para `ambiente_teste/lancador.log`; o que o app imprimir ou errar vai para `ambiente_teste/siapp-saida.log`. Se o app
fechar logo ao abrir, o fim desse arquivo entra no detalhe.

## Atalho

`ponte/icone.py` cria `SIAPP.lnk` (destino `wscript.exe //nologo "…\SIAPP.vbs"`, ícone do SIAPP) e o **recria** quando
o `.lnk` existente não cita o `SIAPP.vbs` e a pasta atuais (é o que acontece ao renomear a pasta ou vir da 0.46).

## Diagnóstico

`SIAPP - diagnóstico.bat` faz o que o `iniciar.bat` fazia até a 0.46: console visível, cada candidato de Python e
cada passo do `pip`. Use para investigar quando a janelinha não bastar.

## Identidade na barra de tarefas

O Windows agrupa os botões pelo **AppUserModelID**. Tudo do SIAPP usa `SIAPP.Pocos.SIAPP` (`lancador/identidade.py`):

- o **processo** (`SetCurrentProcessExplicitAppUserModelID`), na janelinha e na janela principal;
- o **arquivo `SIAPP.lnk`** (propriedade `System.AppUserModel.ID` do atalho, gravada depois que o PowerShell o cria);
- **cada janela** (principal, de aba, janelinha): além do ID, o `RelaunchCommand` (`wscript.exe //nologo "…\SIAPP.vbs"`), o
  `RelaunchIconResource` (o `siapp.ico`) e o `RelaunchDisplayNameResource` ("SIAPP").

Efeito: o atalho fixado e a janela aberta são um botão só; o grupo se chama SIAPP (não "Python"); e se você fixar a janela
aberta, o atalho criado pelo Windows abre o SIAPP pelo lançador, não o `pythonw.exe`. Atalhos já fixados antes da 0.53.1 são
cópias do Windows: desafixe e fixe de novo.

Tudo via `ctypes` (COM: `IShellLink` → `IPropertyStore`; `SHGetPropertyStoreForWindow`). Falha silenciosa: identidade é cosmética.

## Testes

`tests/test_lancador.py` simula Python, `.venv`, `pip` e o app (sem criar nada de verdade) e roda em qualquer
sistema. O que só se vê no Windows (console ausente, ícone, janelinha, atalho) está no guia de teste, seção 0.47.
