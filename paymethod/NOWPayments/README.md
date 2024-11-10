### Зависимости

Для работы необходимо установить пакеты

1. Debian Based: `apt install -y make billmanager-corporate-dev billmanager-plugin-python-libs python3-venv`
2. RHEL: `dnf install -y make billmanager-corporate-devel billmanager-plugin-python-libs`

### Установка папки billmgr/

Так как новая версия BILLmanager еще не вышла, в пакете `billmanager-plugin-python-libs` нет нужных нам либ, которые мы используем в примере
Поставим свежие либы вручную

```
rm -rf /usr/local/mgr5/lib/python/billmgr && tar -xzvf billmgr.tar.gz -C /
```

Здесь содержатся все необходимые зависимости.
Вам не нужно описывать requirements.txt и производить установку зависимостей самостоятельно.
Также здесь есть необходимые инструменты для работы с биллингом, смотрите использование в скриптах примера

### Описание структуры

```
NOWPayments/
├── dist # структура повторяет директорий внутри повторяет /usr/local/mgr5 при установке файлы будут скопированы в указанные места
│   └── skins
│       └── common
│           └── plugin-logo
│               └── billmanager-plugin-pmnowpayments.png # будет находиться в /usr/local/mgr5/skins/common/plugin-logo/
├── Makefile # описание того, что нужно сделать при установке, в этом примере мы просто раскладываем скрипты по папкам
├── nowpayments
│   └── api.py # вспомогательные функции по работе с api
│   └── enums.py # вспомогательные перечисления при работе с api
│   └── __init__.py # предварительные действия перед вызовом api
│   └── exceptions.py # вызов исключений
├── pmnowpayments.py # модуль платежки
├── nowpaymentspayment.py # cgi для обычных платежей
├── nowpaymentspaymentresult.py # cgi для моментальной проверки платежа
└── xml
    └── billmgr_mod_pmnowpayments.xml # описание формы
```

### Установка платежки

```
make install
```

### Создание платежного модуля
При создании платежного модуля нужны данные аккаунта с NOWPayments. 
Внимание! Песочница и сервис никак не связаны друг с другом, нужно создавать отдельные аккаунты.
API ключ можно найти в Settings -> Payments -> API Keys

### Зачисление платежей
Обработка может занимать до 7 дней. Если в указанный период времени транзакция не совершилась, платеж отменяется.
