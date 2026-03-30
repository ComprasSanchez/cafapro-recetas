[Setup]
AppName=CafaproRecetas
AppVersion=2.2.0-beta
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
  ConfigPage: TWizardPage;

  DbEdit: TNewEdit;
  AwsRegionEdit: TNewEdit;
  AwsBucketEdit: TNewEdit;
  AwsCfBaseUrlEdit: TNewEdit;
  AwsAccessKeyEdit: TNewEdit;
  AwsSecretKeyEdit: TNewEdit;
  AwsCacheControlEdit: TNewEdit;

  EnvLoaded: Boolean;


procedure AddLabeledEdit(Page: TWizardPage; Caption: string; var Edit: TNewEdit; TopPos: Integer; IsPassword: Boolean);
var
  L: TNewStaticText;
begin
  L := TNewStaticText.Create(Page);
  L.Parent := Page.Surface;
  L.Left := 0;
  L.Top := TopPos;
  L.Caption := Caption;

  Edit := TNewEdit.Create(Page);
  Edit.Parent := Page.Surface;
  Edit.Left := 0;
  Edit.Top := TopPos + 16;
  Edit.Width := Page.SurfaceWidth;

  if IsPassword then
    Edit.PasswordChar := '*';
end;


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
  EnvLoaded := False;

  ConfigPage :=
    CreateCustomPage(
      wpSelectDir,
      'Configuración del Sistema',
      'Complete los datos de conexión y almacenamiento'
    );

  AddLabeledEdit(ConfigPage, 'DATABASE_URL', DbEdit, 0, False);
  AddLabeledEdit(ConfigPage, 'AWS_REGION', AwsRegionEdit, 60, False);
  AddLabeledEdit(ConfigPage, 'S3_BUCKET', AwsBucketEdit, 120, False);
  AddLabeledEdit(ConfigPage, 'CLOUDFRONT_BASE_URL (sin https://)', AwsCfBaseUrlEdit, 180, False);
  AddLabeledEdit(ConfigPage, 'AWS_ACCESS_KEY_ID', AwsAccessKeyEdit, 240, False);
  AddLabeledEdit(ConfigPage, 'AWS_SECRET_ACCESS_KEY', AwsSecretKeyEdit, 300, True);
  AddLabeledEdit(ConfigPage, 'S3_CACHE_CONTROL', AwsCacheControlEdit, 360, False);
end;


procedure CurPageChanged(CurPageID: Integer);
var
  EnvPath: string;
begin
  if (CurPageID = ConfigPage.ID) and (not EnvLoaded) then
  begin
    EnvPath := ExpandConstant('{app}\.env');

    if FileExists(EnvPath) then
    begin
      DbEdit.Text := LoadEnvValue(EnvPath, 'DATABASE_URL');
      AwsRegionEdit.Text := LoadEnvValue(EnvPath, 'AWS_REGION');
      AwsBucketEdit.Text := LoadEnvValue(EnvPath, 'S3_BUCKET');
      AwsCfBaseUrlEdit.Text := LoadEnvValue(EnvPath, 'CLOUDFRONT_BASE_URL');
      AwsAccessKeyEdit.Text := LoadEnvValue(EnvPath, 'AWS_ACCESS_KEY_ID');
      AwsSecretKeyEdit.Text := LoadEnvValue(EnvPath, 'AWS_SECRET_ACCESS_KEY');
      AwsCacheControlEdit.Text := LoadEnvValue(EnvPath, 'S3_CACHE_CONTROL');

      EnvLoaded := True;
    end;
  end;
end;


function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = ConfigPage.ID then
  begin
    if Trim(DbEdit.Text) = '' then
    begin
      MsgBox('DATABASE_URL no puede estar vacía.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Trim(AwsRegionEdit.Text) = '' then
    begin
      MsgBox('Debe completar AWS_REGION.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;


procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath: string;
  EnvContent: string;
begin
  if CurStep = ssDone then
  begin
    EnvPath := ExpandConstant('{app}\.env');

    EnvContent :=
      'DATABASE_URL=' + Trim(DbEdit.Text) + #13#10 +
      'AWS_REGION=' + Trim(AwsRegionEdit.Text) + #13#10 +
      'S3_BUCKET=' + Trim(AwsBucketEdit.Text) + #13#10 +
      'CLOUDFRONT_BASE_URL=' + Trim(AwsCfBaseUrlEdit.Text) + #13#10 +
      'AWS_ACCESS_KEY_ID=' + Trim(AwsAccessKeyEdit.Text) + #13#10 +
      'AWS_SECRET_ACCESS_KEY=' + Trim(AwsSecretKeyEdit.Text) + #13#10 +
      'S3_CACHE_CONTROL=' + Trim(AwsCacheControlEdit.Text) + #13#10;

    SaveStringToFile(EnvPath, EnvContent, False);
  end;
end;