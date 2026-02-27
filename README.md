# CafaproRecetas

Sistema de gestión y auditoría de recetas médicas.

------------------------------------------------------------------------

## 🏗 Arquitectura General

**Desktop** - PySide6 - PyInstaller - Inno Setup

**Backend / Datos** - SQLAlchemy - Alembic - PostgreSQL - API de
versionado (NestJS)

**Infraestructura** - AWS S3 - CloudFront - Railway

------------------------------------------------------------------------

# 🚀 Sistema de Auto‑Update

## Flujo de actualización

1.  La aplicación inicia.
2.  Consulta el endpoint `/app/version`.
3.  Si existe una versión superior:
    -   Descarga el instalador desde CloudFront.
    -   Cierra la aplicación.
    -   Ejecuta el instalador.
4.  El instalador reemplaza la versión anterior.

------------------------------------------------------------------------

# 🔢 Versionado

Formato:

    MAJOR.MINOR.PATCH

Ejemplos:

-   1.0.35 → Corrección menor
-   1.1.0 → Nueva funcionalidad
-   2.0.0 → Cambio estructural importante

------------------------------------------------------------------------

# 📦 PROCESO OFICIAL DE RELEASE

Este procedimiento debe seguirse estrictamente en cada nueva versión.

------------------------------------------------------------------------

## 1️⃣ Actualizar versión del código

Archivo:

    core/version.py

Modificar:

    APP_VERSION = "1.0.36"

Debe coincidir exactamente con el instalador.

------------------------------------------------------------------------

## 2️⃣ Actualizar versión en Inno Setup

Archivo:

    CafaproRecetas.iss

Modificar:

    AppVersion=1.0.36
    OutputBaseFilename=CafaproRecetasSetup-{#SetupSetting("AppVersion")}

------------------------------------------------------------------------

## 3️⃣ Migraciones de Base de Datos (si corresponde)

Si hubo cambios en modelos SQLAlchemy:

### Generar migración

    py -m alembic revision --autogenerate -m "descripcion"

### Probar en desarrollo

    alembic -x env=dev upgrade head

### Probar en producción

    alembic -x env=prod upgrade head

⚠ Nunca publicar una versión si las migraciones fallan.

------------------------------------------------------------------------

## 4️⃣ Build del ejecutable

Desde PowerShell:

    Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue
    .\.venv\Scripts\python.exe -m PyInstaller --clean -y .\CafaproRecetas.spec
    .\.venv\Scripts\python.exe .\postbuild_copy_resources.py

Se genera:

    dist\CafaproRecetas\

------------------------------------------------------------------------

## 5️⃣ Generar instalador

Abrir Inno Setup y compilar.

Se genera:

    output\CafaproRecetasSetup-1.0.36.exe

------------------------------------------------------------------------

## 6️⃣ Subir a AWS S3

Ruta obligatoria:

    releases/1.0.36/CafaproRecetasSetup-1.0.36.exe

Reglas:

-   Nunca sobrescribir versiones anteriores.
-   Siempre usar carpeta nueva por versión.
-   Nunca reutilizar número de versión.

------------------------------------------------------------------------

## 7️⃣ Actualizar API de Versionado

El endpoint `/app/version` debe devolver:

``` json
{
  "latest_version": "1.0.36",
  "min_required_version": "1.0.35",
  "mandatory": false,
  "download_url": "https://TU_CLOUDFRONT/releases/1.0.36/CafaproRecetasSetup-1.0.36.exe",
  "release_notes": "Descripción de cambios",
  "file_hash": null
}
```

------------------------------------------------------------------------

## 8️⃣ Prueba completa de actualización

1.  Instalar versión anterior (ej. 1.0.35).
2.  Ejecutar aplicación.
3.  Verificar:
    -   Detecta nueva versión.
    -   Descarga correctamente.
    -   Cierra la aplicación.
    -   Ejecuta instalador.
4.  Reabrir aplicación.
5.  Confirmar que ya no intenta actualizar.

------------------------------------------------------------------------

# 📋 Checklist rápido de Release

-   [ ] Cambiar APP_VERSION
-   [ ] Cambiar AppVersion en Inno
-   [ ] Generar migraciones (si aplica)
-   [ ] Probar migraciones
-   [ ] Rebuild PyInstaller
-   [ ] Generar instalador
-   [ ] Subir a S3
-   [ ] Actualizar API
-   [ ] Probar actualización real

------------------------------------------------------------------------

# 📁 Estructura S3 Recomendada

    releases/
     ├── 1.0.35/
     │   └── CafaproRecetasSetup-1.0.35.exe
     ├── 1.0.36/
     │   └── CafaproRecetasSetup-1.0.36.exe

------------------------------------------------------------------------

# 🔐 Reglas Obligatorias

-   `APP_VERSION` debe coincidir con `AppVersion`.
-   No reutilizar números de versión.
-   No sobrescribir releases anteriores.
-   Probar actualización real antes de publicar.
-   Validar migraciones antes de publicar.

------------------------------------------------------------------------

Documento oficial de release --- CafaproRecetas
