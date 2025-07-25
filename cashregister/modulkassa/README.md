# Модуль онлайн-кассы BILLmanager для фискализации чеков через Модулькасса
МодульКасса — это онлайн-касса позволяющая осуществлять расчеты с учетом требований законодательства РФ.

Данный модуль поддерживает следующие функции:
- [x] Отправка чеков с платежей на фискализацию;
- [x] Получение статусов чеков;
- [x] Запись статусов в БД.

## Структура по файлам
```
crmodulkassa/
├── dist
│   └── skins
│       └── common
│           └── plugin-logo
│               └── billmanager-plugin-crmodulkassa.png
├── modulkassa
│   ├── api.py
│   └── __init__.py
├── xml
│   └── billmgr_mod_crmodulkassa.xml
├── crmodulkassa.py
└── Makefile 
```

## Структура проекта
⇨ ./dist - Директория содержит внутри изображение в формате png для онлайн-кассы

⇨ ./modulkassa - Директория со вспомогательными функциями по работе с api CloudPayments

⇨ ./xml - Директория содержит xml файл с описанием внешнего вида формы

⇨ ./crmodulkassa.py - Основной модуль обработчика онлайн-кассы

⇨ ./Makefile - Скрипт для копирования файлов в нужные директории

## Установка
Для работы модуля необходим BILLmanager версии 6.103.0 и выше.

Выполните команду
```sh
sh install.sh
```
Скрипт скопирует модуль в `/usr/local/mgr5/src` и выполнит `make install`.

После чего панель перезапустится и онлайн-касса станет доступна для настройки.

## Логирование
/usr/local/mgr5/var/crmodulkassa.log - лог основного модуля онлайн-кассы

## Документация
- [Онлайн-кассы BILLmanager](https://www.ispsystem.ru/docs/bc/finansy-i-buhgalteriya/onlajn-kassy)
- [Структура базы данных BILLmanager](https://www.ispsystem.ru/docs/bc/razrabotchiku/struktura-bazy-dannyh)
- [Документация онлайн-кассы ModulKassa](https://modulkassa.github.io/backend-api/fn/)