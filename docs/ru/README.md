# Документация (Русский)

Этот индекс собирает все темы документации на русском языке (навигация и краткие пояснения).

## Сборка и настройка платформы

- [Нативная сборка (vcpkg + CMake Presets) и Docker](NATIVE_BUILD_VCPKG.md) - руководство по нативной сборке на Windows/WSL и сравнению с Docker-контуром CI.
- [Быстрая настройка smoke/regression на Windows 11 + WSL2](SETUP_WINDOWS11_WSL2.md) - практический запуск smoke и compare через Docker.
- [Проверки на Windows для диплома / реинжиниринга](WINDOWS_VERIFICATION.md) - воспроизводимые шаги, логи и проверочные команды.

## Ассеты и загрузки

- [Загрузка Windows-ассетов OpenFace (модели + OpenCV DLL)](ASSET_DOWNLOAD.md) - сценарии зеркал, таймауты, ретраи и тесты скриптов загрузки.

## Smoke baseline и регрессия

- [Smoke Baseline and Regression](BASELINE_AND_REGRESSION.md) - политика baseline, CI-контракт и режимы строгого/толерантного сравнения.

## Инструменты Experiment

- [Детекция длительного открытия/закрытия глаз (`Experiment/`)](EXPERIMENT_EYE_TRANSITIONS.md)

## Интеграция LSL и BIDS

- [OpenFace и Lab Streaming Layer (LSL)](LSL_OPENFACE.md) - потоковая реплей-интеграция CSV в LSL.
- [OpenFace как BIDS-derivatives (`of2bids`)](BIDS_OPENFACE_DERIVATIVES.md) - экспорт TSV/JSON для BIDS-структуры.
- [Единая модель времени для LSL + BIDS](INTEGRATION_LSL_BIDS.md) - согласование временных шкал и best practices.

> Примечание: тематические файлы остаются каноническими и находятся уровнем выше (`docs/*.md`), а этот индекс помогает читать их без смешения навигации по языкам.
