[Setup]
AppName=CafaproRecetas
AppVersion=1.0.21-beta
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

  AwsPage: TWizardPage;

  AwsRegionEdit: TNewEdit;
  AwsBucketEdit: TNewEdit;
  AwsCfBaseUrlEdit: TNewEdit;
  AwsAccessKeyEdit: TNewEdit;
  AwsSecretKeyEdit: TNewEdit;
  AwsCacheControlEdit: TNewEdit;

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

function IsBlank(const S: string): Boolean;
begin
  Result := Trim(S) = '';
end;

procedure InitializeWizard();
begin
  // Página DB
  DbPage := CreateCustomPage(wpSelectDir, 'Base de Datos', 'Ingresá la URL de la base de datos');

  DbEdit := TNewEdit.Create(DbPage);
  DbEdit.Parent := DbPage.Surface;
  DbEdit.Left := 0;
  DbEdit.Top := 16;
  DbEdit.Width := DbPage.SurfaceWidth;
  DbEdit.Text := '';

  // Página AWS (distinta a DB, SIN defaults)
  AwsPage := CreateCustomPage(DbPage.ID, 'AWS / S3', 'Ingresá las variables de AWS necesarias para S3 + CloudFront');

  // Layout vertical (label + edit) por campo
  AddLabeledEdit(AwsPage, 'AWS_REGION', AwsRegionEdit, 0, False);
  AddLabeledEdit(AwsPage, 'S3_BUCKET', AwsBucketEdit, 52, False);
  AddLabeledEdit(AwsPage, 'CLOUDFRONT_BASE_URL (sin https://)', AwsCfBaseUrlEdit, 104, False);
  AddLabeledEdit(AwsPage, 'AWS_ACCESS_KEY_ID', AwsAccessKeyEdit, 156, False);
  AddLabeledEdit(AwsPage, 'AWS_SECRET_ACCESS_KEY', AwsSecretKeyEdit, 208, True);
  AddLabeledEdit(AwsPage, 'S3_CACHE_CONTROL', AwsCacheControlEdit, 260, False);

  AwsRegionEdit.Text := '';
  AwsBucketEdit.Text := '';
  AwsCfBaseUrlEdit.Text := '';
  AwsAccessKeyEdit.Text := '';
  AwsSecretKeyEdit.Text := '';
  AwsCacheControlEdit.Text := '';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  // Validación DB
  if CurPageID = DbPage.ID then
  begin
    if IsBlank(DbEdit.Text) then
    begin
      MsgBox('La DATABASE_URL no puede estar vacía.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;

  // Validación AWS
  if CurPageID = AwsPage.ID then
  begin
    if IsBlank(AwsRegionEdit.Text) or
       IsBlank(AwsBucketEdit.Text) or
       IsBlank(AwsCfBaseUrlEdit.Text) or
       IsBlank(AwsAccessKeyEdit.Text) or
       IsBlank(AwsSecretKeyEdit.Text) or
       IsBlank(AwsCacheControlEdit.Text) then
    begin
      MsgBox(
        'Tenés que completar todas las variables de AWS (no se permiten valores por defecto).',
        mbError, MB_OK
      );
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
  // ssDone: ya copió archivos y está finalizando
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

    // False = sobreescribe si existe
    if not SaveStringToFile(EnvPath, EnvContent, False) then
    begin
      MsgBox('No se pudo crear el archivo .env en:' + #13#10 + EnvPath, mbError, MB_OK);
    end;
  end;
end;

