# Модуль OAuth авторизации

При авторизации в BILLmanager используется **Authorization Code Flow** из спецификации OAuth 2.0.

## Основные шаги Authorization Code Flow

- Пользователь инициирует процесс авторизации или регистрации в BILLmanager через OAuth-сервис.
- BILLmanager перенаправляет пользователя на страницу авторизации стороннего сервиса.
- Пользователь проходит процедуру аутентификации в стороннем сервисе.
- Сторонний сервис перенаправляет пользователя обратно в BILLmanager вместе с временным кодом.
- BILLmanager обменивает полученный временной код на токены доступа и запрашивает профиль пользователя из сторонней службы.

## Структура модуля

1. **XML-файл описания плагина (`xml/billmgr_mod_omyandex.xml`)**, содержащий метаинформацию и элементы формы для конфигурации метода авторизации:
   - Секция `<plugin>` включает название метода авторизации и группу — `oauth`. Эта секция регистрирует метод авторизации внутри системы.
     ```xml
       <plugin name="yandex">
         <group>oauth</group>
       </plugin>
     ```
   
   - Метаданные содержат поля настроек метода авторизации на формах провайдеров и пользователей:
     ```xml
       <!-- Настройки провайдера -->
       <metadata name="project.edit" type="form" mgr="billmgr">
         <form>
           <page name="auth">
             <field name="auth_method_yandex" after="custom_methods">
               <input type="toggle" name="auth_method_yandex"/>
             </field>
           </page>
         </form>
       </metadata>
       
       <!-- Параметры пользователя -->
       <metadata name="usrparam" type="form">
         <form>
           <page name="socnetwork">
             <field name="yandex_status">
               <input type="checkbox" name="yandex_status">
                 <if value="on" hide="yandex_signup"/>
                 <if value="off" hide="yandex_status"/>
               </input>
             </field>
             <field name="yandex_signup">
               <link name="yandex_signup_link" target="_self" referrer="yes"/>
             </field>
           </page>
         </form>
       </metadata>
     ```

2. **Python-скрипт (`oauth/omyandex.py`), реализующий две ключевые команды**:
   - `make_url`: Формирует URL для перенаправления клиента при входе через внешний метод авторизации.
   - `get_user_data`: Запрашивает и обрабатывает данные пользователя на основе полученного временного кода.
     
   Обязательными параметрами являются: `firstname`, `lastname`, `realname`, `email`, `id` (полученный из внешней системы).

   Важно! Имя файла должно начинаться с префикса `om`, а оставшаяся часть имени должна соответствовать внутреннему названию метода авторизации из XML. Расширение `.py` автоматически отбрасывается системой.

3. **Иконки методов авторизации**: Файлы иконок размещаются в папке изображений интерфейса. Имя файла совпадает с внутренним названием метода авторизации из XML:
   ```
   dist/skins/common/img/yandex.svg
   dist/skins/dragon/default/yandex.svg
   ```

## Пример реализации модуля

### Настройка

Для демонстрации рассмотрим реализацию авторизации через Яндекс ID ([Документация](https://yandex.ru/dev/id/doc/ru/codes/code-url)).

#### Регистрация приложения:
- Тип приложения: **Веб-сервис**
- Redirect URI:
  ```
  https://domain.com/billmgr?func=oauth.save.userdata&network=yandex
  ```
- Запрошенные права доступа:
  * Доступ к электронному адресу
  * Доступ к логину, имени и фамилии, полу

Получив CLIENT_ID и CLIENT_SECRET, их нужно прописать в файле `oauth/omyandex.py`.

### Установка и сборка

1. Установите необходимые dev-пакеты:
   - Для Debian-подобных ОС:
     ```
     apt install coremanager-dev billmanager-dev billmanager-plugin-python-libs
     ```
   - Для RedHat-подобных ОС:
     ```
     yum install coremanager-dev billmanager-dev billmanager-plugin-python-libs
     ```

2. Разместите исходники модуля по пути `/usr/local/mgr5/src/`.

3. Соберите и установите модуль командой:
   ```
   make install
   ```
