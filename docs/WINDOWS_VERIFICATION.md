# Windows: проверки для диплома / реинжиниринга

Краткий чеклист того, что можно **воспроизводимо** показать: скрипты скачивания ассетов и нативная сборка через vcpkg.

## 1. Скрипты скачивания (PowerShell)

### Быстро, без сети (только синтаксис AST)

Из **корня репозитория**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1
```

### URI-логика (без больших загрузок)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\asset_download_uri.tests.ps1
```

### Полная интеграция (сеть, большие файлы)

Скачивает реальные `cen_patches_*.dat` (десятки / сотни МБ) и OpenCV DLL в изолированный **`tests/download_assets_integration/workdir/`** (в `.gitignore`).

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1
```

Ожидайте **несколько минут** и **сотни МБ** трафика. Для отладки можно сузить ретраи и таймаут:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 -MaxRetriesPerUri 2 -TimeoutSec 90
```

Подробности: **`tests/download_assets_integration/README.md`**, общая дока по зеркалам: **[ASSET_DOWNLOAD.md](ASSET_DOWNLOAD.md)**.

### Лог для приложения к диплому

Каталог **`log/`** в корне репозитория: в git попадает только **`log/README.md`**; всё остальное в `log/` в **`.gitignore`** — пишите логи туда, чтобы не засорять корень и случайно не закоммитить вывод.

```powershell
New-Item -ItemType Directory -Force -Path .\log | Out-Null
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1 2>&1 | Tee-Object -FilePath .\log\parse_tests.log
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 2>&1 | Tee-Object -FilePath .\log\integration_download.log
```

Имена `parse_tests.log` / `integration_download.log` можно заменить своими; для диплома приложите файлы из **`log/`** как есть (в git они не должны попадать).

## 2. Нативная сборка Windows + vcpkg (CMake Presets)

Локально: см. **[NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md)** (`cmake --preset windows-msvc-vcpkg`, `VCPKG_ROOT`, первый configure долгий).

На GitHub: workflow **Windows native vcpkg proof** — ручной запуск и автозапуск на `push` в `reengineering` при изменении путей из той же доки.

## 3. Связь с Linux CI

Docker smoke и сравнение с baseline по-прежнему в **[BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md)** и `.github/workflows/ci.yml` — это **другой** контур (Linux-образ), не заменяет проверки из пунктов 1–2.
