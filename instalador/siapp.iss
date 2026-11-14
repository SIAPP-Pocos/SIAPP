; SIAPP — instalador do Windows (Inno Setup 6), 0.67.
; Instala só para o usuário (sem pedir administrador) em %LOCALAPPDATA%\Programs\SIAPP.
; Os dados ficam em Documentos\SIAPP e NÃO são apagados ao desinstalar.
; Compilar:  ISCC.exe /DVersao=0.67.0 instalador\siapp.iss   (depois do PyInstaller)

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
Name: "{group}\Pasta de dados do SIAPP"; Filename: "{userdocs}\SIAPP"
Name: "{userdesktop}\SIAPP"; Filename: "{app}\SIAPP.exe"; AppUserModelID: "SIAPP.Pocos.SIAPP"; Tasks: atalho

[Dirs]
Name: "{userdocs}\SIAPP"; Flags: uninsneveruninstall

[Run]
Filename: "{app}\SIAPP.exe"; Description: "Abrir o SIAPP agora"; Flags: nowait postinstall skipifsilent

[Messages]
pt.FinishedLabel=O SIAPP foi instalado. Os seus projetos ficam em Documentos\SIAPP e continuam lá mesmo se você desinstalar.
