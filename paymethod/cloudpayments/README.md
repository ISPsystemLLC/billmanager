# CloudPayments

## Структура проекта

```
cloudpayments/
├── cloudpayments
│   ├── __init__.py
│   └── api.py
├── dist
│   ├── etc
│   │   └── paymethods
|   |       ├── cloudpayments_404.html
│   │       └── cloudpayments_widget.html
│   └── skins
│       └── common
│           └── plugin-logo
│               └── billmanager-plugin-pmcloudpaymentswidget.png
├── xml
    └── billmgr_mod_pmpaypalcheckout.xml
├── Makefile
├── pmcloudpaymentswidget.py
├── cpwidgetpayment.py 
├── cpwidgetrecurring.py
├── cpwidgetrecurringresult.py
└── cpwidgetresult.py
```

⇨ ./cloudpayments - Директория со вспомогательными функциями по работе с api CloudPayments

⇨ ./dist - Директория содержит внутри себя html форму для оплаты, страницу 404 и изображение в формате png для метода оплаты

⇨ ./xml - Директория содержит xml файл с описанием внешнего вида формы

⇨ ./Makefile - Скрипт для копирования файлов в нужные директории

⇨ ./pmcloudpaymentswidget.py - Основной модуль обработчика платежной системы

⇨ ./cpwidgetpayment.py - Cgi для перехода в платежную систему для обычного платежа

⇨ ./cpwidgetrecurring.py - Cgi для перехода в платежную систему для установочного платежа для рекуррентных платежей

⇨ ./cpwidgetrecurringresult.py - Cgi для обработки подтверждения рекуррентных платежей

⇨ ./cpwidgetresult.py - Cgi для обработки подтверждения обычных платежей

## Установка

Для работы модуля необходим BILLmanager версии 6.103.0 и выше.

Выполните команду

```sh
sh install.sh
```

Скрипт скопирует модуль в `/usr/local/mgr5/src` и выполнит `make install`.

После чего панель перезапустится и метод оплаты станет доступен для настройки.

## Логирование

- /usr/local/mgr5/var/cpwidgetpayment.log - лог Cgi скрипта создания платежной формы

- /usr/local/mgr5/var/cpwidgetrecurring.log - лог Cgi скрипта создания автоплатежа или сохраненного способа оплаты

- /usr/local/mgr5/var/cpwidgetresult.log - лог Cgi скрипта обработки статуса платежа

- /usr/local/mgr5/var/cpwidgetrecurringresult.log - лог Cgi скрипта обработки статуса создания автоплатежа или сохраненного способа оплаты

- /usr/local/mgr5/var/pmcloudpaymentswidget.log - лог основного модуля оплаты

## Документация

- [Написание платёжного модуля для BILLmanager](https://docs.ispsystem.ru/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-plateyonyh-sistem)

- [Структура базы данных](https://docs.ispsystem.ru/bc/razrabotchiku/struktura-bazy-dannyh)

- [Документация интернет-эквайринга CloudPayments](https://developers.cloudpayments.ru/)
