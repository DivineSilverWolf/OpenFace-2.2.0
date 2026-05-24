# Windows: проверка для диссертации / реинжиниринга

Краткий чеклист того, что можно показать **воспроизводимо** на Windows: скрипты скачивания ассетов и нативный build-flow на vcpkg.

## 1. Скрипты скачивания (PowerShell)

### Быстро, офлайн (только AST-проверка синтаксиса)

Из **корня репозитория**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1
```

### Проверка URI-логики (без больших скачиваний)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\asset_download_uri.tests.ps1
```

### Полная интеграционная проверка (сеть, большие файлы)

Скачивает реальные `cen_patches_*.dat` (десятки/сотни МБ) и DLL OpenCV в изолированный каталог **`tests/download_assets_integration/workdir/`** (в gitignore).

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1
```

Ожидайте **несколько минут** и **сотни МБ** трафика. Для отладки можно уменьшить число повторов и таймаут:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 -MaxRetriesPerUri 2 -TimeoutSec 90
```

Подробности: **`tests/download_assets_integration/README.md`**; документация по mirror: **[ASSET_DOWNLOAD.md](ASSET_DOWNLOAD.md)**.

### Логи для приложения к диссертации

Используйте корневой каталог **`log/`**: под версионным контролем только **`log/README.md`**, всё остальное в `log/` игнорируется git. Складывайте логи туда, чтобы не захламлять корень и не закоммитить их случайно.

```powershell
New-Item -ItemType Directory -Force -Path .\log | Out-Null
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1 2>&1 | Tee-Object -FilePath .\log\parse_tests.log
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 2>&1 | Tee-Object -FilePath .\log\integration_download.log
```

Можно переименовать `parse_tests.log` / `integration_download.log`; для диссертации используйте сырые файлы из **`log/`** (их не нужно коммитить).

## 2. Нативная сборка Windows + vcpkg (CMake Presets)

Локальные инструкции: **[NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md)** (`cmake --preset windows-msvc-vcpkg`, `VCPKG_ROOT`, первый configure может быть долгим).

На GitHub: workflow **Windows native vcpkg proof** поддерживает ручной запуск и автозапуск на `push` в `reengineering`, когда меняются пути из этого документа. После сборки он выполняет **те же Python-проверки**, что Linux job `native-manifest-presets` в `ci.yml`, затем запускает **native smoke** (без Docker) и compare против `baseline_manifest_ci.json`.

## 3. Те же gate-проверки, что в Docker CI, но нативно (PowerShell)

После успешной `cmake --build --preset windows-msvc-vcpkg-release` и одноразового запуска **`download_models.ps1`**:

```powershell
# Те же Python-проверки, что и в Linux CI + smoke + compare (тот же gate-контракт из ci.yml / baseline_manifest_ci.json)
.\tools\windows\Run-WindowsNativeTestSuite.ps1 -WithSmoke
```

Только Python-проверки (без бинарников OpenFace):

```powershell
.\tools\windows\Run-WindowsNativeTestSuite.ps1
```

Только smoke + compare (если Python-проверки уже выполнялись):

```powershell
.\tools\windows\Run-NativeSmokeAndCompare.ps1
```

Краткое описание сценария: **`tools/windows/README.md`**. Полные `*.csv` / `*.hog` в Windows обычно **не совпадают** с Linux baseline; merge-CI контракт — это **`*_of_details.txt`** в tolerant-режиме (см. [BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md)).

## 4. Связь с Linux CI

Docker smoke + baseline compare остаются в **[BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md)** и `.github/workflows/ci.yml` как эталонный Linux-путь. Нативные скрипты из раздела 3 дают **паритет Python-проверок + паритет smoke-gate** (`*_of_details.txt`) без запуска Docker Desktop на Windows.

Полная карта автотестов и скриптов: **[tests/README.md](../../tests/README.md)**.
