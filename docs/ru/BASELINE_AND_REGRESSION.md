# Smoke Baseline и Regression

В этом документе описан воспроизводимый workflow smoke-регрессии с нуля.

**См. также:** [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md) (PowerShell-тесты скачивания ассетов, `log/` для диссертации), [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md) (нативная сборка Windows CMake + vcpkg), [tests/README.md](../../tests/README.md) (индекс тестов).

## Роли каталогов

- `smoke_test/data/` - входные данные smoke (изображения/видео).
- `smoke_test/baseline_output/` - **CI / git baseline:** компактные файлы регрессии в репозитории; GitHub Actions сравнивает **подмножество** через `tools/regression/baseline_manifest_ci.json` (сейчас только `*_of_details.txt`, см. ниже).
- `smoke_test/baseline_output_local/` - **локальный golden** для конкретной машины: тот же layout, что у `baseline_output/`, но **не коммитится** (см. `.gitignore`). Нужен для локального сравнения без перезаписи CI baseline.
- `smoke_test/output/` - результаты текущего прогона.
- `smoke-output-for-baseline/` (опционально, в корне репозитория) - распакованный артефакт workflow **Smoke baseline capture**; в **gitignore**, чтобы не коммитить тяжёлые медиа.

`tools/run_smoke_and_compare.sh` всегда очищает `smoke_test/output/{img,video}` перед запуском.  
`smoke_test/baseline_output/` и `smoke_test/baseline_output_local/` этим скриптом не изменяются (только читаются для сравнения).

## Baseline в git и CI (предпочтительная политика)

Регрессия сравнивает только типы файлов из `smoke_test/baseline_manifest.json` (сейчас: `*.csv`, `*.hog`, `*_of_details.txt`). Этого достаточно для `compare_smoke_outputs.py`; выровненные bitmap-файлы, preview-картинки и рендер-видео **не** входят в regression gate.

**Рекомендуемый подход:** хранить в репозитории **lean**-версию `smoke_test/baseline_output/` (пути как у `output/`, но только сравниваемые артефакты). Это даёт воспроизводимый GitHub Actions без внешних загрузок и не раздувает историю тяжёлыми медиа.

### Двойной baseline (CI и локальная машина)

| Путь | Назначение | В git |
|------|---------|--------|
| `smoke_test/baseline_output/` | Gate для **merge / GitHub Actions** (синхронизируется с `ubuntu-latest` capture при обновлении) | да (lean) |
| `smoke_test/baseline_output_local/` | Опциональный **developer golden** на вашем CPU/Docker-хосте | нет |

- **Тот же gate, что в CI, локально:** `./tools/run_smoke_and_compare.sh` с теми же `MODE`, `MANIFEST`, `ABS_TOL`, что и в `.github/workflows/ci.yml` (по умолчанию работает с `baseline_output/`).
- **Сравнение с вашим сохранённым golden:** `./tools/run_smoke_compare_local_baseline.sh` (по умолчанию: `BASELINE_DIR=smoke_test/baseline_output_local`, полный `baseline_manifest.json`, tolerant). После успешного локального прогона обновите локальный baseline:

```bash
SRC=smoke_test/output DST=smoke_test/baseline_output_local ./tools/regression/sync_smoke_baseline_git.sh
```

Если вы переносите CI-артефакт в `baseline_output/`, сначала можно сохранить предыдущий lean baseline в `baseline_output_local/`:

```bash
SRC=smoke_test/baseline_output DST=smoke_test/baseline_output_local ./tools/regression/sync_smoke_baseline_git.sh
SRC=smoke-output-for-baseline DST=smoke_test/baseline_output ./tools/regression/sync_smoke_baseline_git.sh
```

(Или используйте `./tools/regression/refresh_git_baseline_from_ci_output.sh` только для второй строки.)

- **Полный локальный snapshot** (всё из `output/`, для визуальной проверки): `./tools/regression/bootstrap_smoke_baseline.sh`
- **Baseline для git/CI** (только сравниваемые файлы): `./tools/regression/sync_smoke_baseline_git.sh` после golden-прогона `./smoke_test/run_smoke.sh`

Если выходы изменились осознанно (toolchain, модель, поведение OpenFace), перегенерируйте smoke-output, выполните `sync_smoke_baseline_git.sh` и закоммитьте обновлённый `smoke_test/baseline_output/`.

**Примечание про дрейф:** если в ветке для удобства отслеживается большой `smoke_test/output/`, его regression-файлы могут устаревать относительно текущего Docker-образа. Gate сравнивает **свежий** `output/` после `run_smoke.sh` с `baseline_output/`. После обновления baseline один раз запустите `./tools/run_smoke_and_compare.sh` в strict-режиме и убедитесь, что всё проходит.

## CI-aligned baseline (`ubuntu-latest`)

Lean-файлы из `smoke_test/baseline_output/` сравниваются в GitHub Actions через `tools/regression/baseline_manifest_ci.json` и tolerant-режим (см. `.github/workflows/ci.yml`).

### Windows native (MSVC + vcpkg)

Workflow **Windows native vcpkg proof** (`.github/workflows/windows-native-vcpkg-proof.yml`) запускает **те же Python static/unit checks**, что и Linux job `native-manifest-presets`, затем нативные `FaceLandmarkImg` / `FeatureExtraction` на `smoke_test/data/` и тот же вызов `compare_smoke_outputs.py` с **`baseline_manifest_ci.json`** (без Docker). Плотные `*.csv` / `*.hog` в Windows обычно **отличаются от Linux baseline**; **контракт** такой же, как в merge-CI: summary `*_of_details.txt` в пределах **`ABS_TOL`**. Точки входа: `tools/windows/Run-NativeSmokeAndCompare.ps1` и `tools/windows/Run-WindowsNativeTestSuite.ps1` (см. [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md), [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md)).

### Почему `*.csv` убрали из сравнения в GitHub Actions

Docker smoke job **уже подтверждает**, что образ собирается, контейнер стартует и OpenFace проходит end-to-end на `smoke_test/data/` (изображения + короткие видео). Проблемной оказалась **следующая** часть: трактовать плотные **`*.csv`** как байт-стабильный или `1e-5`-стабильный контракт **между разными машинами пула `ubuntu-latest`**.

На практике мы видели:

- **Smoke-лог зелёный** (модели загружены, трекинг выполнен, файлы записаны), но **compare красный** только на `*.csv`: тысячи числовых токенов отличаются, `max_abs` заметно выше `1e-5` (включая видео), даже после обновления baseline из артефакта **Smoke baseline capture** на GitHub. Это не «забыли обновить baseline», а **run-to-run / runner-to-runner числовой дрейф**.
- При тех же падениях **`*_of_details.txt` проходил** tolerant-сравнение: summary-часть оставалась в пределах `ABS_TOL`, а большие per-frame CSV-потоки нет.

Поэтому сохранение **`*.csv`** в `baseline_manifest_ci.json` означает либо **постоянные ложные падения** CI, либо **слишком большой `ABS_TOL`**, при котором gate теряет смысл для mixed-scale столбцов (см. [Tolerance knob (ABS_TOL)](#tolerance-knob-abstol)).

**Текущий CI-контракт:** в `tools/regression/baseline_manifest_ci.json` перечислены только **`**/*_of_details.txt`** — CI всё ещё контролирует **числовую регрессию** по summary-файлам (это стабильно между раннерами), а полная регрессия по **`*.csv` (+ `.hog` при необходимости)** остаётся **локальной**: `smoke_test/baseline_manifest.json`, `./tools/run_smoke_compare_local_baseline.sh` и/или `smoke_test/baseline_output_local/` (см. [Dual baseline](#dual-baseline-ci-vs-local-machine)).

**Строки путей в `*_of_details.txt` (tolerant mode):** первые строки содержат абсолютные `Input:` / `Input full path:`. Git baseline с GitHub (`/home/runner/...`) не совпадает байт-в-байт с запуском на ноутбуке или WSL (`/mnt/c/...`), и поток числовых токенов раньше включал разное число цифр внутри этих путей. В **tolerant** режиме `tools/regression/compare_smoke_outputs.py` **заменяет каждую такую строку на тот же префикс + только basename пути** перед извлечением чисел; это позволяет чисто сравнивать локальный Docker-smoke с закоммиченным CI baseline. **`strict` режим не меняется** (полный SHA256 файла), поэтому path-dependent baseline по дизайну остаётся машинозависимым в strict.

Baseline, снятый на **другой** машине, всё равно может не пройти локально CSV strict/tolerant; когда вы осознанно меняете выходы, обновляйте baseline из GA-артефакта.

**Предпочтительный сценарий, если CI compare падает, но pipeline корректен:** считать GitHub runner источником истины для baseline в репозитории.

1. Запустите на GitHub **Smoke baseline capture** (`.github/workflows/smoke-baseline-artifact.yml`) вручную: **Actions → Smoke baseline capture → Run workflow** (`workflow_dispatch` only; не запускается на push). Кнопка видна только если workflow-файл есть в **default branch**. Workflow собирает тот же Docker image, что и CI, поднимает `openface`, запускает `./smoke_test/run_smoke.sh` и публикует артефакт **`smoke-output-for-baseline`** с деревом `smoke_test/output/` (`img/`, `video/` в корне zip).

2. **Скачайте артефакт:** откройте успешный запуск workflow → внизу страницы блок **Artifacts** → клик по **`smoke-output-for-baseline`** (скачается zip). Распакуйте локально; должны быть папки `img/` и `video/`.

3. Из корня репозитория примените артефакт к git-oriented baseline (копируются только `*.csv`, `*.hog`, `*_of_details.txt` в `smoke_test/baseline_output/`):

```bash
./tools/regression/refresh_git_baseline_from_ci_output.sh /path/to/unzipped/dir
# If the artifact is unpacked at repo root as ./smoke-output-for-baseline/ (gitignored):
#   SRC=smoke-output-for-baseline DST=smoke_test/baseline_output ./tools/regression/sync_smoke_baseline_git.sh
```

   Эквивалентно: `SRC=/path/to/unzipped/dir ./tools/regression/sync_smoke_baseline_git.sh`

4. Проверьте `git diff smoke_test/baseline_output`, затем закоммитьте обновлённые файлы.

5. Опциональная локальная sanity-проверка с **теми же** настройками, что в CI:

```bash
export MODE=tolerant ABS_TOL=1e-5
export MANIFEST="$(pwd)/tools/regression/baseline_manifest_ci.json"
./tools/run_smoke_and_compare.sh
```

   Локальный pass не гарантирован после CI-only refresh (ваш Docker-хост может немного отличаться), но **GitHub Actions** должен стать зелёным, когда baseline совпадает с раннером, который создал артефакт.

## Native toolchain (vcpkg / MSVC) vs Docker baseline

Если вы пересобираете OpenFace **нативно** на Windows через **vcpkg** (см. [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md)), работайте с регрессией так же, как после любой смены компилятора/OpenCV: запустите smoke, сравните с **`ABS_TOL`** и обновите **`baseline_output_local/`** (или git baseline, если осознанно принимаете новые golden-значения). Плотные **`*.csv`** могут слегка дрейфовать, тогда как **`*_of_details.txt`** остаётся в допуске; **`compare_smoke_outputs.py`** сравнивает CSV как **поток числовых токенов** (пока без привязки к заголовкам столбцов). Для **`*_of_details.txt`** tolerant-режим также **нормализует `Input:` / `Input full path:`** до basename, чтобы различия путей CI/WSL не давали ложные падения.

## Что происходит до compare (важно)

`./tools/run_smoke_and_compare.sh` делает не только compare:

1. нормализует `DATA_MOUNT` через `tools/smoke_data_mount.sh` (Windows-path → Docker-совместимый путь при наличии `cygpath`/`wslpath`);
2. проверяет, что baseline существует и содержит regression-файлы;
3. проверяет `ACTUAL_DIR != BASELINE_DIR`;
4. очищает `smoke_test/output/img` и `smoke_test/output/video`;
5. выполняет `docker compose build`;
6. выполняет `docker compose up -d --force-recreate openface`;
7. запускает `./smoke_test/run_smoke.sh`;
8. запускает `compare_smoke_outputs.py`.

То есть необходимые шаги до compare есть намеренно — ради воспроизводимости.

## Шаг 0: Подготовьте baseline один раз (до реинжиниринга, когда baseline пуст)

Используйте входы из `smoke_test/data/`, чтобы получить golden-run и зафиксировать его в `baseline_output`.

1) Соберите/поднимите контейнер и один раз прогоните smoke (записывает в `smoke_test/output/`):

```bash
export DATA_MOUNT="$(pwd)/smoke_test"
./tools/smoke_docker_up.sh
./smoke_test/run_smoke.sh
```

`DATA_MOUNT` должен совпадать при создании контейнера и запуске `run_smoke.sh`. Использование `./tools/smoke_docker_up.sh` (вместо «сырого» `docker compose up`) применяет ту же нормализацию пути, что и `run_smoke.sh`, и помогает избежать **invalid volume specification**, когда shell случайно передаёт путь вида `C:\...` (например, если PowerShell разворачивает `$(pwd)` раньше bash).

Если значения всё же различаются (например, контейнер поднят с другим `.env`), `run_smoke.sh` завершится с явной ошибкой mismatch.

Подробнее (включая PowerShell + WSL): `docs/SETUP_WINDOWS11_WSL2.md`.

2) Зафиксируйте `output/` в baseline:

```bash
./tools/regression/bootstrap_smoke_baseline.sh
```

Если baseline нужно обновить намеренно (например, после смены toolchain/build), используйте:

```bash
FORCE=1 ./tools/regression/bootstrap_smoke_baseline.sh
```

`bootstrap_smoke_baseline.sh` копирует всё текущее дерево `output/` в `baseline_output/` (тяжёлый вариант, удобен локально).

Для коммитов и CI лучше использовать `./tools/regression/sync_smoke_baseline_git.sh` (см. [Baseline в git и CI](#baseline-в-git-и-ci-предпочтительная-политика)).

## Шаг 1: Внесите изменения в код

Сделайте реинжиниринг в разрешённых зонах.

## Шаг 2: Проверьте baseline после изменений

Запустите полный pipeline:

```bash
./tools/run_smoke_and_compare.sh
```

Он выполняет:
- `docker compose build`
- smoke-прогон на `smoke_test/data/` в `smoke_test/output/`
- сравнение `smoke_test/output/` с `smoke_test/baseline_output/`

## Реальный пример «из пустого baseline»

Если `smoke_test/baseline_output/` пуст, первый запуск падает сразу:

- `ERROR: baseline has no *.csv under .../smoke_test/baseline_output`

Это ожидаемо. Корректный порядок:

1) создать baseline из `smoke_test/data/` через `run_smoke.sh`, затем `bootstrap_smoke_baseline.sh` (полное дерево) или `sync_smoke_baseline_git.sh` (только сравниваемые файлы, для git/CI);
2) внести изменения;
3) запустить `run_smoke_and_compare.sh`.

## Режимы сравнения

### Strict (байт-в-байт)

Режим по умолчанию (`MODE=strict`):

```bash
MODE=strict ./tools/run_smoke_and_compare.sh
```

### Tolerant numeric mode

Для микродрейфа из-за компилятора/библиотек:

```bash
MODE=tolerant ABS_TOL=1e-6 ./tools/run_smoke_and_compare.sh
```

В tolerant-режиме:
- `.csv` и `*_of_details.txt` сравниваются численно с `abs(a-b) <= ABS_TOL`.
- `.hog` остаётся strict (бинарный файл).

### Порог допуска (ABS_TOL)

`compare_smoke_outputs.py` в tolerant-режиме проходит по каждому файлу, извлекает **все числовые токены** (целые и float) в **порядке файла**, сопоставляет их с потоком токенов baseline и требует `abs(actual - baseline) <= ABS_TOL` (есть исключение для парных NaN). Для файла действует **один** порог для **всех** токенов — per-column логики пока нет. Переменная окружения `ABS_TOL` прокидывается из `run_smoke_and_compare.sh` в `compare_smoke_outputs.py --abs-tol` (в GitHub Actions задаётся в `.github/workflows/ci.yml`).

**Когда повышение `ABS_TOL` помогает:** небольшой платформенный дрейф (например, `1e-6` vs `1e-5` vs `1e-4`) для **малых по масштабу** значений или summary-файлов, где величины лежат в близком диапазоне.

**Когда большой `ABS_TOL` — плохое решение для полных CSV `FeatureExtraction` / `FaceLandmarkImg`:** в таких CSV смешаны **очень разные масштабы** в одном потоке (например, AU-значения около 0…1, координаты в сотнях пикселей, pose translation в сотнях и больше). Один абсолютный порог либо слишком строгий и **падает на «больших» колонках**, либо слишком большой и **перестаёт защищать «малые» колонки**.

Эмпирически на **GitHub-hosted `ubuntu-latest`** два запуска с **тем же** Docker-образом могут давать **большой** `max_abs` в плотном CSV (например, порядка **1** на статичных изображениях и **10+** на видеостроках) из-за вариативности **runner/CPU/math library**, а не из-за поломки smoke.

**Политика репозитория:** в CI используется `tools/regression/baseline_manifest_ci.json`, который сравнивает только **`*_of_details.txt`** с `ABS_TOL=1e-5` (см. `.github/workflows/ci.yml`). Так gate остаётся осмысленным в пуле раннеров. **Полная регрессия CSV (+ опционально `.hog`)** остаётся **локальной** задачей: используйте `smoke_test/baseline_manifest.json` и/или `./tools/run_smoke_compare_local_baseline.sh` против `smoke_test/baseline_output_local/`.

**Если CI флейкует даже на `*_of_details.txt`:** повышайте `ABS_TOL` небольшими шагами (например, `1e-4`, затем `1e-3`) в `ci.yml` и зеркальте те же значения в локальной sanity-команде. Не стоит ожидать, что один большой `ABS_TOL` сделает плотные per-frame CSV надёжными в CI без изменения логики сравнения (например, column-aware/relative tolerance — пока не реализовано).

## `baseline_manifest.json`: что это и как использовать

Файл: `smoke_test/baseline_manifest.json`

Назначение:
- управляет **какие типы файлов/паттерны** входят в regression compare;
- опционально фиксирует хэши baseline-файлов (`sha256`) для защиты от незаметной подмены baseline.

Текущая схема:

```json
{
  "version": 1,
  "description": "Smoke regression baseline manifest.",
  "patterns": ["**/*.csv", "**/*.hog", "**/*_of_details.txt"],
  "sha256": {}
}
```

Как работают поля:
- `patterns` - glob-паттерны целевых файлов для сравнения.
- `sha256` - опциональная map `relative/path -> sha256`.
  - пустой `{}` означает «hash pinning не включён».
  - непустая map требует совпадения baseline-файлов с объявленными хэшами до старта compare.

## Параметры `compare_smoke_outputs.py`

Скрипт: `tools/regression/compare_smoke_outputs.py`

Обязательные:
- `--actual-dir PATH` - тестируемый output (обычно `smoke_test/output`).
- `--baseline-dir PATH` - baseline output (обычно `smoke_test/baseline_output`).
- `--manifest PATH` - JSON-манифест (`smoke_test/baseline_manifest.json`).

Опциональные:
- `--mode strict|tolerant` (по умолчанию: `strict`).
- `--abs-tol FLOAT` (по умолчанию: `1e-6`, используется в tolerant-режиме).

Примеры:

```bash
python3 ./tools/regression/compare_smoke_outputs.py \
  --actual-dir ./smoke_test/output \
  --baseline-dir ./smoke_test/baseline_output \
  --manifest ./smoke_test/baseline_manifest.json \
  --mode strict
```

```bash
python3 ./tools/regression/compare_smoke_outputs.py \
  --actual-dir ./smoke_test/output \
  --baseline-dir ./smoke_test/baseline_output \
  --manifest ./smoke_test/baseline_manifest.json \
  --mode tolerant \
  --abs-tol 1e-6
```
