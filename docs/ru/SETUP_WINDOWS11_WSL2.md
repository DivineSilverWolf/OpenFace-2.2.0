# Быстрая настройка smoke/regression в Windows 11 + WSL2

Для **нативной сборки на Windows** (декларативные зависимости через vcpkg + CMake Presets, без исторических скриптов скачивания DLL) см. [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md). После Release-сборки **`tools/windows/Run-WindowsNativeTestSuite.ps1 -WithSmoke`** запускает те же Python-проверки, что и Linux CI, плюс нативный smoke и сравнение по `baseline_manifest_ci.json` (без Docker). Проверки PowerShell-скриптов `download_*.ps1` (parse / integration) и сохранение логов в **`log/`** описаны в [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md). Ниже — именно **Docker-путь** (тот же runtime-контур, что в CI smoke).

Запускайте эти команды из **WSL bash** в корне репозитория, чтобы `DATA_MOUNT` оставался Linux-путём, понятным Docker.

## Рекомендуемый вариант (нормализация `DATA_MOUNT` до Docker)

`./tools/smoke_docker_up.sh` применяет те же правила Windows→Unix для путей, что и `run_smoke.sh`, затем пересоздаёт контейнер `openface`. Предпочитайте его «чистому» `docker compose up`, когда `DATA_MOUNT` потенциально может быть путём вида `C:\...`.

```bash
export DOCKERUSER=local
export DOCKERTAG=2.2.0
export DATA_MOUNT="$(pwd)/smoke_test"
./tools/smoke_docker_up.sh
./smoke_test/run_smoke.sh
./tools/regression/bootstrap_smoke_baseline.sh
./tools/run_smoke_and_compare.sh
```

## `DATA_MOUNT`: bash-пути и Windows-пути

Общая логика находится в `tools/smoke_data_mount.sh` (подключается из `smoke_test/run_smoke.sh` и `tools/run_smoke_and_compare.sh`).

- **WSL / Linux**: достаточно `export DATA_MOUNT="$(pwd)/smoke_test"`.
- **Буква диска Windows** (`C:\...`, `C:/...` или смешанный путь с `/smoke_test`): конвертируется через `wslpath -u` (WSL) или `cygpath -u` (Git Bash / MSYS), если доступно.
- **PowerShell вызывает WSL**: не позволяйте PowerShell раскрывать `$(pwd)` в двойных кавычках до старта bash. Лучше:
  - открыть **WSL** и запустить блок выше; или
  - заключить весь аргумент `bash -lc '...'` в одинарные кавычки, чтобы `$(pwd)` вычислялся **внутри** bash, например:

```powershell
wsl -e bash -lc 'cd "/mnt/c/Users/YOU/path/OpenFace-2.2.0" && export DOCKERUSER=local DOCKERTAG=2.2.0 DATA_MOUNT="$(pwd)/smoke_test" && ./tools/smoke_docker_up.sh && ./smoke_test/run_smoke.sh'
```

Примечания:

- Используйте одинаковый `DATA_MOUNT` при создании контейнера и в `run_smoke.sh` (или применяйте `smoke_docker_up.sh` с дефолтами, тогда значения совпадут автоматически).
- Если `run_smoke.sh` сообщает `DATA_MOUNT mismatch`, пересоздайте контейнер, например: `./tools/smoke_docker_up.sh`.
