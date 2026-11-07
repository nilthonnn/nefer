; Instalador de LadderLab para Windows 10 y 11.
;
; LadderLab ya es una app completa en UN archivo HTML
; (docs/ladder/descargas/LadderLab.html, que arma herramientas/empaquetar-ladder.py).
; El instalador no la reescribe ni la envuelve en un navegador propio de 100 MB:
; la copia a la carpeta del usuario y crea accesos directos que la abren con
; Microsoft Edge en MODO APLICACION (--app): ventana propia, sin barra de
; direcciones, con su icono. Edge viene con Windows 10 y 11.
;
; Si no hay Edge ni Chrome, los accesos abren el HTML con el navegador
; predeterminado: funciona igual, solo que en una pestaña.
;
; No pide permisos de administrador (se instala para el usuario actual) y no
; necesita internet para funcionar.
;
; Se compila en la integracion (.github/workflows/windows-ladderlab.yml):
;   iscc /DVersion=1.N LadderLab.iss

#ifndef Version
  #define Version "1.0"
#endif

[Setup]
; Identidad fija: con la misma AppId una version nueva se instala encima.
AppId={{8C5E2B1A-4F3D-4C8E-9A61-3B7D2E5F1A90}
AppName=LadderLab
AppVersion={#Version}
AppVerName=LadderLab {#Version}
AppPublisher=LadderLab - herramienta de estudio
AppComments=Curso y simulador de Ladder (LAD) para TIA Portal, con ruta de grupos electrogenos y mineria
DefaultDirName={localappdata}\Programs\LadderLab
DefaultGroupName=LadderLab
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
MinVersion=10.0
OutputDir=salida
OutputBaseFilename=LadderLab-Setup
SetupIconFile=ladderlab.ico
UninstallDisplayIcon={app}\ladderlab.ico
UninstallDisplayName=LadderLab
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\..\docs\ladder\descargas\LadderLab.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\ladder\descargas\Manual-de-uso-LadderLab.pdf"; DestDir: "{app}"; Flags: ignoreversion
Source: "ladderlab.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\LadderLab"; Filename: "{code:Programa}"; Parameters: "{code:Parametros}"; WorkingDir: "{app}"; IconFilename: "{app}\ladderlab.ico"; Comment: "Curso y simulador de Ladder para TIA Portal"
Name: "{group}\Manual de uso de LadderLab"; Filename: "{app}\Manual-de-uso-LadderLab.pdf"
Name: "{group}\Desinstalar LadderLab"; Filename: "{uninstallexe}"
Name: "{userdesktop}\LadderLab"; Filename: "{code:Programa}"; Parameters: "{code:Parametros}"; WorkingDir: "{app}"; IconFilename: "{app}\ladderlab.ico"; Tasks: escritorio

[Run]
Filename: "{code:Programa}"; Parameters: "{code:Parametros}"; Description: "Abrir LadderLab ahora"; Flags: postinstall nowait skipifsilent shellexec

[Code]
var
  NavegadorEncontrado: String;
  YaBuscado: Boolean;

{ Edge primero (viene con Windows); Chrome si no. Vacio si no hay ninguno. }
function BuscarNavegador(): String;
var
  Candidatos: array of String;
  I: Integer;
begin
  if YaBuscado then begin
    Result := NavegadorEncontrado;
    exit;
  end;
  SetArrayLength(Candidatos, 6);
  Candidatos[0] := ExpandConstant('{commonpf32}\Microsoft\Edge\Application\msedge.exe');
  Candidatos[1] := ExpandConstant('{commonpf64}\Microsoft\Edge\Application\msedge.exe');
  Candidatos[2] := ExpandConstant('{localappdata}\Microsoft\Edge\Application\msedge.exe');
  Candidatos[3] := ExpandConstant('{commonpf64}\Google\Chrome\Application\chrome.exe');
  Candidatos[4] := ExpandConstant('{commonpf32}\Google\Chrome\Application\chrome.exe');
  Candidatos[5] := ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe');
  NavegadorEncontrado := '';
  for I := 0 to GetArrayLength(Candidatos) - 1 do
    if FileExists(Candidatos[I]) then begin
      NavegadorEncontrado := Candidatos[I];
      break;
    end;
  YaBuscado := True;
  Result := NavegadorEncontrado;
end;

{ La app como direccion file:/// (barras normales, espacios codificados). }
function DireccionApp(): String;
var
  Ruta: String;
begin
  Ruta := ExpandConstant('{app}\LadderLab.html');
  StringChangeEx(Ruta, '\', '/', True);
  StringChangeEx(Ruta, ' ', '%20', True);
  Result := 'file:///' + Ruta;
end;

function Programa(Param: String): String;
begin
  if BuscarNavegador() <> '' then
    Result := BuscarNavegador()
  else
    Result := ExpandConstant('{app}\LadderLab.html');
end;

function Parametros(Param: String): String;
begin
  if BuscarNavegador() <> '' then
    Result := '--app="' + DireccionApp() + '"'
  else
    Result := '';
end;
