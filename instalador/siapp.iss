; SIAPP — instalador do Windows (Inno Setup 6), desde a 0.67.
; Instala só para o usuário (sem pedir administrador) em %LOCALAPPDATA%\Programs\SIAPP.
; 1.0: pergunta a "Pasta dos projetos" (padrão Documentos\SIAPP; sem perguntas: /PASTADADOS="C:\...") e grava a
; escolha em {app}\pasta_dados.txt, que o SIAPP lê ao abrir. A pasta dos projetos NÃO é apagada ao desinstalar.
; Compilar:  ISCC.exe /DVersao=1.0.0 instalador\siapp.iss   (depois do PyInstaller)

#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{F4F6F833-F505-4AD4-B653-E4EC7C95B921}
AppName=SIAPP
AppVersion={#Versao}
AppVerName=SIAPP {#Versao}
AppPublisher=Ruan da Silva Nobre
AppPublisherURL=https://github.com/SIAPP-Pocos
AppComments=Sistema Integrado de Aquisição e Processamento de Perfis — software livre (AGPL-3.0)
; Nome e versão gravados no instalador (Propriedades › Detalhes); a assinatura do SignPath confere o nome do produto
VersionInfoVersion={#Versao}
VersionInfoProductName=SIAPP
VersionInfoProductVersion={#Versao}
VersionInfoCompany=Ruan da Silva Nobre
VersionInfoDescription=Instalador do SIAPP
VersionInfoCopyright=© 2026 Ruan da Silva Nobre — software livre (AGPL-3.0)
DefaultDirName={localappdata}\Programs\SIAPP
DefaultGroupName=SIAPP
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SIAPP-{#Versao}-instalador
SetupIconFile=..\recursos\icone\siapp.ico
UninstallDisplayIcon={app}\SIAPP.exe
LicenseFile=..\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[InstallDelete]
; numa atualização, apaga as bibliotecas da versão anterior antes de copiar as novas (nada de arquivo velho misturado)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\SIAPP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SIAPP"; Filename: "{app}\SIAPP.exe"; AppUserModelID: "SIAPP.Pocos.SIAPP"
Name: "{group}\Pasta dos projetos do SIAPP"; Filename: "{code:PastaDados}"
Name: "{userdesktop}\SIAPP"; Filename: "{app}\SIAPP.exe"; AppUserModelID: "SIAPP.Pocos.SIAPP"; Tasks: atalho

[Dirs]
Name: "{code:PastaDados}"; Flags: uninsneveruninstall

[Run]
Filename: "{app}\SIAPP.exe"; Description: "Abrir o SIAPP agora"; Flags: nowait postinstall skipifsilent

[Messages]
pt.FinishedLabel=O SIAPP foi instalado. Os seus projetos ficam na pasta escolhida e continuam lá mesmo se você desinstalar.

[Code]
var
  PaginaDados: TInputDirWizardPage;

function ParametroPastaDados(): String;
var
  I: Integer;
  P: String;
begin
  Result := '';
  for I := 1 to ParamCount do
  begin
    P := ParamStr(I);
    if CompareText(Copy(P, 1, 12), '/PASTADADOS=') = 0 then
      Result := RemoveQuotes(Copy(P, 13, Length(P)));
  end;
end;

procedure InitializeWizard();
var
  Inicial: String;
begin
  PaginaDados := CreateInputDirPage(wpSelectDir, 'Pasta dos projetos',
    'Onde o SIAPP vai guardar os projetos, os arquivos baixados e os resultados?',
    'Escolha uma pasta com espaço livre (os arquivos do portal REATE podem somar alguns GB). Dentro dela o SIAPP cria ' +
    'a pasta Projetos, com o Projeto principal. Se você já usa o SIAPP, escolha a mesma pasta de antes: os seus ' +
    'projetos continuam de onde pararam. Esta pasta não é apagada ao desinstalar.', False, 'SIAPP');
  PaginaDados.Add('');
  Inicial := ParametroPastaDados();
  if Inicial = '' then
    Inicial := GetPreviousData('PastaDados', ExpandConstant('{userdocs}\SIAPP'));
  PaginaDados.Values[0] := Inicial;
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  SetPreviousData(PreviousDataKey, 'PastaDados', PaginaDados.Values[0]);
end;

function PastaDados(Param: String): String;
begin
  Result := PaginaDados.Values[0];
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Linhas: TArrayOfString;
begin
  if CurStep = ssPostInstall then
  begin
    ForceDirectories(PaginaDados.Values[0]);
    SetArrayLength(Linhas, 1);
    Linhas[0] := PaginaDados.Values[0];
    SaveStringsToUTF8File(ExpandConstant('{app}\pasta_dados.txt'), Linhas, False);
  end;
end;
