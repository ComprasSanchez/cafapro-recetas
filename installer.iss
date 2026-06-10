[Setup]
AppName=CafaproRecetas
AppVersion=4.1.0
DefaultDirName={pf}\CafaproRecetas
DefaultGroupName=CafaproRecetas
OutputDir=output
OutputBaseFilename=CafaproRecetasSetup-{#SetupSetting("AppVersion")}
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=resources\logo.ico
WizardStyle=modern
WizardSizePercent=130
WizardResizable=yes

[Files]
Source: "dist\CafaproRecetas\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: ".env"
Source: "dist\CafaproRecetas\.env"; DestDir: "{app}"; Flags: onlyifdoesntexist skipifsourcedoesntexist

[Tasks]
Name: "desktopicon"; Description: "Crear ícono en el Escritorio"; Flags: unchecked

[Icons]
Name: "{group}\CafaproRecetas"; Filename: "{app}\CafaproRecetas.exe"
Name: "{commondesktop}\CafaproRecetas"; Filename: "{app}\CafaproRecetas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CafaproRecetas.exe"; Description: "Ejecutar CafaproRecetas"; Flags: nowait postinstall skipifsilent

[Code]

var
  ConfigPage: TWizardPage;

  LblApi: TNewStaticText;
  ApiEdit: TNewEdit;

  LblCf: TNewStaticText;
  CfEdit: TNewEdit;


function LoadEnvValue(const FilePath, Key: string): string;
var
  Lines: TArrayOfString;
  I: Integer;
  Line: string;
begin
  Result := '';
  if not FileExists(FilePath) then
    Exit;
  LoadStringsFromFile(FilePath, Lines);
  for I := 0 to GetArrayLength(Lines) - 1 do
  begin
    Line := Trim(Lines[I]);
    if Pos(Key + '=', Line) = 1 then
    begin
      Result := Copy(Line, Length(Key) + 2, MaxInt);
      Exit;
    end;
  end;
end;


procedure InitializeWizard();
begin
  // Crear la página y AMBOS campos siempre.
  // No leemos {app} aquí porque el directorio todavía no fue elegido.
  ConfigPage := CreateCustomPage(
    wpSelectDir,
    'Configuración del Sistema',
    'Complete los datos de conexión faltantes'
  );

  LblApi := TNewStaticText.Create(ConfigPage);
  LblApi.Parent := ConfigPage.Surface;
  LblApi.Left := 0;
  LblApi.Top := 0;
  LblApi.Caption := 'API_CAFAPRO  (ej: http://servidor:3000)';
  LblApi.Visible := False;

  ApiEdit := TNewEdit.Create(ConfigPage);
  ApiEdit.Parent := ConfigPage.Surface;
  ApiEdit.Left := 0;
  ApiEdit.Top := 16;
  ApiEdit.Width := ConfigPage.SurfaceWidth;
  ApiEdit.Visible := False;

  LblCf := TNewStaticText.Create(ConfigPage);
  LblCf.Parent := ConfigPage.Surface;
  LblCf.Left := 0;
  LblCf.Top := 60;
  LblCf.Caption := 'CLOUDFRONT_BASE_URL  (ej: dxxx.cloudfront.net)';
  LblCf.Visible := False;

  CfEdit := TNewEdit.Create(ConfigPage);
  CfEdit.Parent := ConfigPage.Surface;
  CfEdit.Left := 0;
  CfEdit.Top := 76;
  CfEdit.Width := ConfigPage.SurfaceWidth;
  CfEdit.Visible := False;
end;


// ShouldSkipPage se llama DESPUÉS de que el usuario elige directorio,
// así que WizardDirValue() ya tiene valor.
function ShouldSkipPage(PageID: Integer): Boolean;
var
  EnvPath, ApiVal, CfVal: string;
begin
  Result := False;
  if PageID = ConfigPage.ID then
  begin
    EnvPath := WizardDirValue() + '\.env';
    ApiVal  := LoadEnvValue(EnvPath, 'API_CAFAPRO');
    CfVal   := LoadEnvValue(EnvPath, 'CLOUDFRONT_BASE_URL');
    Result  := (Trim(ApiVal) <> '') and (Trim(CfVal) <> '');
  end;
end;


// CurPageChanged se llama cuando la página ya está visible y {app} existe.
procedure CurPageChanged(CurPageID: Integer);
var
  EnvPath, ApiVal, CfVal: string;
  TopPos: Integer;
begin
  if CurPageID = ConfigPage.ID then
  begin
    EnvPath := WizardDirValue() + '\.env';
    ApiVal  := Trim(LoadEnvValue(EnvPath, 'API_CAFAPRO'));
    CfVal   := Trim(LoadEnvValue(EnvPath, 'CLOUDFRONT_BASE_URL'));

    TopPos := 0;

    // API_CAFAPRO
    if ApiVal <> '' then
    begin
      LblApi.Visible := False;
      ApiEdit.Visible := False;
    end else
    begin
      LblApi.Top  := TopPos;
      ApiEdit.Top := TopPos + 16;
      LblApi.Visible  := True;
      ApiEdit.Visible := True;
      TopPos := TopPos + 60;
    end;

    // CLOUDFRONT_BASE_URL
    if CfVal <> '' then
    begin
      LblCf.Visible := False;
      CfEdit.Visible := False;
    end else
    begin
      LblCf.Top  := TopPos;
      CfEdit.Top := TopPos + 16;
      LblCf.Visible  := True;
      CfEdit.Visible := True;
    end;
  end;
end;


function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = ConfigPage.ID then
  begin
    if ApiEdit.Visible and (Trim(ApiEdit.Text) = '') then
    begin
      MsgBox('API_CAFAPRO no puede estar vacía.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if CfEdit.Visible and (Trim(CfEdit.Text) = '') then
    begin
      MsgBox('CLOUDFRONT_BASE_URL no puede estar vacía.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;


procedure SetEnvValue(const FilePath, Key, Value: string);
var
  Lines: TArrayOfString;
  I: Integer;
  Found: Boolean;
  Line, Content: string;
begin
  Found := False;

  if FileExists(FilePath) then
    LoadStringsFromFile(FilePath, Lines);

  // Actualizar línea existente
  for I := 0 to GetArrayLength(Lines) - 1 do
  begin
    Line := Trim(Lines[I]);
    if Pos(Key + '=', Line) = 1 then
    begin
      Lines[I] := Key + '=' + Value;
      Found := True;
      Break;
    end;
  end;

  // Agregar al final si no existía
  if not Found then
  begin
    SetArrayLength(Lines, GetArrayLength(Lines) + 1);
    Lines[GetArrayLength(Lines) - 1] := Key + '=' + Value;
  end;

  // Reconstruir y guardar
  Content := '';
  for I := 0 to GetArrayLength(Lines) - 1 do
    Content := Content + Lines[I] + #13#10;

  SaveStringToFile(FilePath, Content, False);
end;


procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath: string;
begin
  if CurStep = ssDone then
  begin
    EnvPath := ExpandConstant('{app}\.env');

    // Solo modifica los campos que el usuario completó, preserva el resto
    if ApiEdit.Visible and (Trim(ApiEdit.Text) <> '') then
      SetEnvValue(EnvPath, 'API_CAFAPRO', Trim(ApiEdit.Text));

    if CfEdit.Visible and (Trim(CfEdit.Text) <> '') then
      SetEnvValue(EnvPath, 'CLOUDFRONT_BASE_URL', Trim(CfEdit.Text));
  end;
end;
