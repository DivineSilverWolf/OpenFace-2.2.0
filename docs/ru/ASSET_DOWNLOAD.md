# Загрузка Windows-ресурсов OpenFace (модели + DLL OpenCV)

**Чеклист валидации на Windows (диссертация / реинжиниринг):** [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md). Полная карта тестов: **[tests/README.md](../../tests/README.md)**.

Скрипты в корне репозитория **`download_models.ps1`** и **`download_libraries.ps1`** скачивают большие бинарные файлы, которые не хранятся в git. Они используют **`Invoke-WebRequest`** с **повторами**, **таймаутами** и **логированием прогресса**.

Общая логика находится в **`tools/asset-download/OpenFaceAssetDownload.ps1`** (подключается в оба скрипта через dot-sourcing).

## Быстрый старт (по умолчанию: Dropbox, затем OneDrive)

Из корня репозитория в **PowerShell** (Windows PowerShell 5.1+ или PowerShell 7+):

```powershell
Set-Location C:\path\to\OpenFace-2.2.0
.\download_models.ps1
.\download_libraries.ps1
```

Уже существующие файлы **пропускаются** (как и в старых скриптах).

## Зеркало / форк (GitHub Releases или любой HTTPS base URL)

Если Dropbox или OneDrive медленные либо недоступны, опубликуйте **те же байты** в своём релизе (или статическом HTTPS-дереве URL), затем укажите скриптам **URL папки**, где каждый файл доступен под **ожидаемым именем**.

### Параметр или переменная среды

- **`-MirrorBaseUrl`** — предпочтительный вариант в командной строке.
- **`OPENFACE_MIRROR_BASE_URL`** — используется, если `-MirrorBaseUrl` не передан (например, в CI или в постоянном профиле shell).

Пример:

```powershell
$env:OPENFACE_MIRROR_BASE_URL = "https://github.com/ORG/OpenFace-2.2.0/releases/download/openface-assets-v1/"
.\download_models.ps1
.\download_libraries.ps1
```

Или:

```powershell
.\download_models.ps1 -MirrorBaseUrl "https://github.com/ORG/OpenFace-2.2.0/releases/download/openface-assets-v1/"
```

Base URL может быть как с завершающим `/`, так и без него.

### Порядок источников

Для каждого файла скрипты пробуют источники **в таком порядке**:

1. **Mirror** — только если задан `MirrorBaseUrl` / `OPENFACE_MIRROR_BASE_URL`.  
2. **Dropbox** — исходные upstream-ссылки (`?dl=1`, где применимо).  
3. **OneDrive** — исходные upstream-ссылки.

Засчитывается первая успешная загрузка.

### Имена файлов на зеркале (должны совпадать точно)

**Модели** (`download_models.ps1`):

| Хвост URL на зеркале (добавляется к базе) | Устанавливаемый относительный путь |
|-----------------------------------|-------------------------|
| `cen_patches_0.25_of.dat` | `lib/local/LandmarkDetector/model/patch_experts/cen_patches_0.25_of.dat` (или без `lib/` в layout сборки из бинарников — скрипт сохраняет исторические правила) |
| `cen_patches_0.35_of.dat` | … `cen_patches_0.35_of.dat` |
| `cen_patches_0.50_of.dat` | … `cen_patches_0.50_of.dat` |
| `cen_patches_1.00_of.dat` | … `cen_patches_1.00_of.dat` |

**Библиотеки** (`download_libraries.ps1`):

| Хвост URL на зеркале | Путь установки |
|-----------------|----------------|
| `opencv_ffmpeg410_64.dll` | `lib/3rdParty/OpenCV/bin/opencv_ffmpeg410_64.dll` |
| `opencv_world410_x64_Release.dll` | `lib/3rdParty/OpenCV/x64/v141/bin/Release/opencv_world410.dll` |
| `opencv_world410_x64_Debug.dll` | `lib/3rdParty/OpenCV/x64/v141/bin/Debug/opencv_world410d.dll` |
| `opencv_ffmpeg410.dll` | `lib/3rdParty/OpenCV/bin/opencv_ffmpeg410.dll` |
| `opencv_world410_x86_Release.dll` | `lib/3rdParty/OpenCV/x86/v141/bin/Release/opencv_world410.dll` |
| `opencv_world410_x86_Debug.dll` | `lib/3rdParty/OpenCV/x86/v141/bin/Debug/opencv_world410d.dll` |

**Почему у `opencv_world410*.dll` разные имена на зеркале:** у x64 и x86 одинаковые **имена файлов на диске**, но лежат они в разных каталогах; в плоской папке релиза нужны **уникальные** названия. После скачивания скрипт всё равно пишет файлы в **оригинальные** пути и имена, ожидаемые Visual Studio-layout.

### Публикация в GitHub Releases (типичный вариант)

1. Создайте **tag** (например, `openface-assets-v1`) или используйте `latest` с отдельным названием релиза.  
2. Загрузите файлы выше как **binary assets** релиза, с точными именами хвостов URL.  
3. Скопируйте URL каталога с asset-файлами (или URL отдельных файлов без имени и используйте как base + leaf).
   Пример URL файла:  
   `https://github.com/ORG/REPO/releases/download/openface-assets-v1/cen_patches_0.25_of.dat`  
   Base:  
   `https://github.com/ORG/REPO/releases/download/openface-assets-v1/`

## Повторы и таймауты

Необязательные параметры (для обоих скриптов):

| Параметр | По умолчанию | Смысл |
|-----------|---------|---------|
| `-MaxRetriesPerUri` | `5` | Количество попыток **на один URL**, прежде чем перейти к Dropbox / OneDrive. |
| `-TimeoutSec` | `120` | Таймаут `Invoke-WebRequest` на одну попытку (в секундах). |

## Логирование

Каждая попытка печатает строку с timestamp (`[try n/N]`, URL, затем `[ok]` или предупреждение). Пропуски показываются как `[skip]`, если целевой файл уже существует.

## Тесты (без сети)

Проверка хелперов склейки URL:

```powershell
pwsh -NoProfile -File .\tests\asset_download_uri.tests.ps1
# or Windows PowerShell:
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\asset_download_uri.tests.ps1
```

**AST parse** (без выполнения) для скриптов загрузки и общего helper-модуля:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1
```

## Интеграционный тест (требуется сеть)

Рекомендуется сначала прогнать **AST parse** (быстро): `tests/download_assets_parse.tests.ps1`.

Для сквозной проверки **`download_models.ps1`** и **`download_libraries.ps1`** по реальным URL используйте изолированную рабочую директорию **`tests/download_assets_integration/workdir/`** (каждый запуск создаёт её заново, директория в **gitignore**):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1
```

Подробности и параметры: **`tests/download_assets_integration/README.md`**.

Ожидайте **несколько минут** и **сотни МБ** трафика (модели из Dropbox). По умолчанию этот сценарий **не** входит в Linux Docker CI.

## Поведение относительно старых скриптов

- Сохранены те же **пути назначения** и **URL Dropbox / OneDrive**, что и раньше.  
- **Mirror** опционален и пробуется первым.  
- **Dropbox-ссылки** для `opencv_world410*.dll` снова активны как средний fallback (в legacy `download_libraries.ps1` они были закомментированы, но upstream-ссылки валидны и полезны при проблемах с OneDrive).  
- Требуется **PowerShell 5.1+** для параметра `-TimeoutSec` в `Invoke-WebRequest` (обычно Windows 10+ / Server 2016+).
