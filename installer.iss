[Setup]
AppName=CafaproRecetas
AppVersion=1.0.11-beta
DefaultDirName={pf}\CafaproRecetas
DefaultGroupName=CafaproRecetas
OutputDir=output
OutputBaseFilename=CafaproRecetasSetup-{#SetupSetting("AppVersion")}
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=resources\logo.ico

[Files]
Source: "dist\CafaproRecetas\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Crear ícono en el Escritorio"; Flags: unchecked

[Icons]
Name: "{group}\CafaproRecetas"; Filename: "{app}\CafaproRecetas.exe"
Name: "{commondesktop}\CafaproRecetas"; Filename: "{app}\CafaproRecetas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CafaproRecetas.exe"; Description: "Ejecutar CafaproRecetas"; Flags: nowait postinstall skipifsilent

[Code]
var
  DbPage: TWizardPage;
  DbEdit: TNewEdit;

procedure InitializeWizard();
begin
  DbPage := CreateCustomPage(wpSelectDir, 'Base de Datos', 'Ingresá la URL de la base de datos');

  DbEdit := TNewEdit.Create(DbPage);
  DbEdit.Parent := DbPage.Surface;
  DbEdit.Left := 0;
  DbEdit.Top := 16;
  DbEdit.Width := DbPage.SurfaceWidth;

  // opcional: dejalo vacío o poné un ejemplo
  DbEdit.Text := '';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = DbPage.ID then
  begin
    if Trim(DbEdit.Text) = '' then
    begin
      MsgBox('La DATABASE_URL no puede estar vacía.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath: string;
  EnvContent: string;
begin
  // ssDone: ya copió archivos y está finalizando
  if CurStep = ssDone then
  begin
    EnvPath := ExpandConstant('{app}\.env');
    EnvContent := 'DATABASE_URL=' + Trim(DbEdit.Text) + #13#10;

    if not SaveStringToFile(EnvPath, EnvContent, False) then
    begin
      MsgBox('No se pudo crear el archivo .env en:' + #13#10 + EnvPath, mbError, MB_OK);
    end;
  end;
end;
