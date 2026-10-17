# Лабораторная работа №1 — эксплуатация MongoDB

## Как я делала эту работу

Цель работы — развернуть MongoDB без Docker и показать, что я умею не только
запустить базу, но и сопровождать её: управлять службой, пользователями и ролями,
делать резервные копии, восстанавливать данные и смотреть метрики.

Я работаю на MacBook с процессором M3. В VMware Fusion создала виртуальную машину
с Ubuntu Server 24.04 ARM64. MongoDB работает внутри Ubuntu, а Ansible я запускаю
с Mac.

### Почему я решила использовать Ansible

Сначала MongoDB настраивалась вручную через SSH. Для одной команды это нормально,
но вся лабораторная состоит из большого количества связанных действий. Если
выполнять их вручную, легко пропустить шаг, ошибиться в команде или потом не
вспомнить, как был настроен сервер.

Поэтому дальнейшую настройку я решила делать через Ansible. В этой схеме Mac —
control node, а Ubuntu — managed node. Ansible подключается к Ubuntu по SSH и
выполняет сценарии из playbook-файлов.

```text
Mac: Git-репозиторий + Ansible
             |
             | SSH по ключу
             v
Ubuntu VM: MongoDB и службы мониторинга
```

Весь репозиторий копировать на VM не нужно. Ansible сам передаёт только нужные
скрипты и конфигурации. Пароли находятся в зашифрованном `vault.yml` и не
попадают в Git.

### Виртуальная машина и SSH

На Ubuntu создан пользователь `ola` с правами `sudo`. VM получила адрес
`192.168.60.133` в NAT-сети VMware. Сначала вход выполнялся по паролю, затем я
настроила SSH-ключ. Проверка Ansible завершилась ответом:

```text
mongo-lab | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

Это означает, что Mac видит VM, SSH работает и Ansible может выполнять на Ubuntu
свои модули.

### Установка MongoDB

При первой попытке выполнить `sudo apt install mongodb-org` пакет не нашёлся.
Причина была в том, что `mongodb-org` отсутствует в стандартных репозиториях
Ubuntu. Я добавила официальный репозиторий MongoDB 8.0, после чего пакет стал
доступен для APT.

После установки включила автозапуск `mongod` через systemd. При первой проверке
`mongosh` вернул `ECONNREFUSED`, потому что сервер ещё не принимал подключения.
После запуска службы команда `ping` стала выполняться успешно.

Базовую конфигурацию затем закрепила в `playbooks/provision.yml`, чтобы установку
можно было повторить на другой VM.

### Управление службой MongoDB

Работу с системной службой проверила через `playbooks/service-demo.yml`. Сценарий
остановил `mongod` и убедился, что порт `27017` закрылся. Затем он снова запустил
MongoDB, включил автозапуск службы и выполнил перезапуск. После перезапуска порт
снова стал доступен.

Первый запуск сценария завершился ошибкой:

```text
Attempting to decrypt but no vault secrets found
```

Хотя этому сценарию не нужны пароли MongoDB, Ansible автоматически загружает
зашифрованный `vault.yml` из общих переменных inventory. Поэтому я повторила
запуск с параметром `--ask-vault-pass`. После этого все проверки прошли:

```text
mongo-lab : ok=5 changed=3 unreachable=0 failed=0
```

### Что не получилось с первого раза

Первый запуск `provision.yml` не прошёл сразу. Сначала APT сообщил:

```text
Conflicting values set for option Signed-By
```

MongoDB уже устанавливалась вручную, поэтому на VM остался старый файл
репозитория с ключом `.gpg`. Ansible добавил тот же репозиторий в новом формате с
ключом `.asc`. APT увидел две записи и остановился. В playbook добавила удаление
старого `.list` перед созданием новой записи.

После этого сломалась проверка `mongosh`: YAML неправильно разобрал выражение
`{ ping: 1 }`. Я заключила выражение в кавычки, чтобы оно передавалось в MongoDB
как JavaScript, а не как YAML-словарь. После исправления получила:

```text
MongoDB ping returned 1
```

### Авторизация и пароли

Пароли пользователей MongoDB хранятся в зашифрованном Ansible Vault. Отдельно
хранятся пароли администратора, учебных пользователей, backup, restore и
экспортера. Файл с настоящими секретами исключён из Git.

Playbook `secure.yml` включил `authorization: enabled` и должен был создать
первого администратора `lab_admin`. Здесь тоже появилась ошибка. Bootstrap-скрипт
пытался сначала вызвать `getUser()`, но MongoDB в режиме localhost exception
разрешает без авторизации только создать первого пользователя. Я вынесла первый
`createUser()` в отдельный скрипт без предварительного запроса пользователей.

После исправления результат был таким:

```text
mongo-lab : ok=9 changed=2 unreachable=0 failed=0
```

Авторизация включена, администратор создан, вход с его паролем проверен.

### Учебные базы, роли и пользователи

Playbook `configure-lab.yml` создал базы `university` и `library`, добавил
тестовые документы и индексы. Также созданы собственные роли:

- `universityReader` — чтение учебной базы;
- `studentEditor` — работа с коллекцией `students`;
- `gradesOnlyReader` — чтение только коллекции `grades`;
- `temporaryRole` — временная роль для демонстрации удаления.

Для ролей созданы отдельные пользователи. Кроме них появились служебные учётные
записи `backup_user`, `restore_user` и `mongodb_exporter`.

Результат настройки:

```text
mongo-lab : ok=9 changed=7 unreachable=0 failed=0
```

### Проверка ролевой модели

После создания пользователей я запустила `playbooks/role-demo.yml`. Сценарий
назначил пользователю дополнительную роль, отозвал её и изменил разрешения
существующей роли.

Отдельно проверила доступ только к одной коллекции. Пользователь
`grades_reader` смог прочитать документ из `university.grades`, но при попытке
прочитать `university.students` MongoDB отказала в доступе. Ansible подтвердил,
что отказ был ожидаемым:

```text
Access to university.students was denied as expected.
```

В конце сценарий удалил временного пользователя и временную роль:

```text
Deleted user temporary_user
Deleted role temporaryRole
```

Сценарий завершился без ошибок:

```text
mongo-lab : ok=10 changed=3 unreachable=0 failed=0
```

### Резервные копии

Для копирования данных использовала `playbooks/backup.yml`. Сценарий запускает
`mongodump` от отдельного пользователя `backup_user`, а имена копий содержат
дату и время.

Первая попытка прошла только частично: отдельная копия `university` создалась, но
общая копия учебных баз завершилась с `failed=1`. Причиной оказался параметр
`--nsInclude`. Он поддерживается программой `mongorestore`, но не `mongodump`.

Я исправила сценарий: теперь он последовательно копирует базы `university` и
`library` в один общий каталог. После исправления были созданы:

```text
/var/backups/mongodb-lab/20261017T132635Z-university
/var/backups/mongodb-lab/20261017T132635Z-all-study-dbs
```

Повторный запуск завершился успешно:

```text
mongo-lab : ok=9 changed=5 unreachable=0 failed=0
```

Затем я запустила тот же сценарий ещё раз. Вторая полная копия получила другую
метку времени. Команда `ls -1 /var/backups/mongodb-lab` показала:

```text
20261017T132350Z-university
20261017T132635Z-all-study-dbs
20261017T132635Z-university
20261017T132806Z-all-study-dbs
20261017T132806Z-university
```

Каталог `132350Z-university` остался от первой частично успешной попытки. Пары
`132635Z` и `132806Z` — две полные копии. Новая копия не перезаписала старую,
потому что время создания входит в название каждого каталога.

### Восстановление коллекции

Для проверки восстановления запустила `playbooks/restore-demo.yml`. Перед
удалением сценарий нашёл самую свежую копию и проверил, что в ней действительно
есть файл коллекции `students`. После этого он удалил
`university.students`, восстановил только эту коллекцию через `mongorestore` и
посчитал документы.

```text
Restored university.students from
/var/backups/mongodb-lab/20261017T132806Z-university;
document count is 3.
```

Количество документов после восстановления совпало с исходным. Сценарий
завершился с результатом:

```text
mongo-lab : ok=14 changed=5 unreachable=0 failed=0
```

### Мониторинг

Playbook `monitoring.yml` установил Percona MongoDB Exporter, Prometheus и
Grafana. Exporter получает показатели MongoDB, Prometheus сохраняет их, а
Grafana отображает на дашборде.

Для дашборда выбрала следующие показатели:

- доступность MongoDB;
- время работы сервера;
- текущие и доступные подключения;
- количество операций в секунду;
- объём занятой оперативной памяти.

При первой проверке exporter и Prometheus уже отвечали, а Grafana вернула
`Connection refused`. Служба была запущена, но при первом старте ещё не успела
открыть порт `3000`. В playbook добавила ожидание портов `9216`, `9090` и `3000`
до 90 секунд.

После этого HTTP-проверки всех трёх сервисов прошли, но последняя проверка искала
строго строку `mongodb_up 1`. У установленной версии exporter метрика содержит
дополнительную метку:

```text
mongodb_up{cluster_role="mongod"} 1
```

Значение `1` уже означало, что exporter видит MongoDB. Я исправила регулярное
выражение, чтобы оно учитывало метки. Повторная проверка завершилась успешно:

```text
mongo-lab : ok=1 changed=0 unreachable=0 failed=0
```

### Что ещё осталось

На текущем этапе осталось выполнить и записать результаты:

- влияние тестовой нагрузки на графики.

Эти разделы я дополняю после фактического выполнения, а не заранее.

## Инструкция и команды для повторения

Стенд: Ubuntu Server 24.04 ARM64 в VMware Fusion на Mac с Apple Silicon.

## Состав стенда

- MongoDB Community 8.0, порт `27017`;
- Percona MongoDB Exporter, порт `9216`;
- Prometheus, порт `9090`;
- Grafana, порт `3000`.

MongoDB остаётся привязана к `127.0.0.1`. С Mac наружу открывается только SSH и веб-интерфейс Grafana.

## Как устроена работа

Основной сценарий максимально приближен к обычной эксплуатации:

```text
Git-репозиторий и Ansible на Mac
              |
              | SSH по ключу
              v
Ubuntu Server VM: MongoDB + exporter + Prometheus + Grafana
```

Репозиторий остаётся на Mac и в GitHub. Ansible передаёт на VM только нужные
конфигурации и запускает изменения через SSH. Копировать весь проект на сервер
через `rsync` не требуется. Пароли находятся в зашифрованном Ansible Vault и не
попадают в Git.

Это production-подобная организация процесса для одного учебного сервера.
Настоящая отказоустойчивая production-инсталляция MongoDB обычно также требует
несколько узлов, TLS, firewall, централизованное хранение секретов и внешнее
хранилище резервных копий.

## Первый запуск с Mac

Все команды этого раздела выполняются в Terminal на Mac.

### 1. Запустить VM и узнать её адрес

В консоли Ubuntu выполните:

```bash
hostname -I
```

Запишите адрес VM в `inventories/lab/hosts.yml` в поле `ansible_host`.

### 2. Один раз установить SSH-ключ

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub ola@192.168.60.133
```

Замените IP, если он изменился. Пароль пользователя Ubuntu потребуется только
на этом шаге. Проверка:

```bash
ssh ola@192.168.60.133
exit
ansible mongodb -m ping
```

### 3. Создать зашифрованное хранилище паролей

```bash
EDITOR=nano ansible-vault create inventories/lab/group_vars/all/vault.yml
```

Сначала задайте отдельный пароль самого Vault. Затем вставьте структуру из
разные пароли длиной не менее 12 символов, сохраните файл сочетанием `Ctrl+O`,
`Enter`, закройте редактор сочетанием `Ctrl+X`.

Проверить, что файл действительно зашифрован:

```bash
head -n 1 inventories/lab/group_vars/all/vault.yml
```

Ожидаемое начало: `$ANSIBLE_VAULT;...`.

### 4. Применить конфигурацию

```bash
ansible-playbook playbooks/provision.yml --ask-become-pass
ansible-playbook playbooks/secure.yml --ask-become-pass --ask-vault-pass
ansible-playbook playbooks/configure-lab.yml --ask-become-pass --ask-vault-pass
ansible-playbook playbooks/role-demo.yml --ask-become-pass --ask-vault-pass
ansible-playbook playbooks/monitoring.yml --ask-become-pass --ask-vault-pass
ansible-playbook playbooks/healthcheck.yml --ask-become-pass --ask-vault-pass
```

- `BECOME password` — пароль пользователя `ola` на Ubuntu для `sudo`;
- `Vault password` — пароль шифрования, заданный на предыдущем шаге.

Повторный запуск playbook безопасен для установки и конфигурации. Playbook
`configure-lab.yml` намеренно заново создаёт учебные данные, чтобы лабораторная
возвращалась в известное начальное состояние.

### 5. Демонстрация управления службой

Этот playbook специально останавливает, запускает и перезапускает MongoDB, поэтому
его запускают только во время демонстрации лабораторной:

```bash
ansible-playbook playbooks/service-demo.yml --ask-become-pass --ask-vault-pass
```

### 6. Резервное копирование и восстановление

Создать копию `university` и общий каталог с копиями учебных баз:

```bash
ansible-playbook playbooks/backup.yml --ask-become-pass --ask-vault-pass
```

Запустите команду дважды: timestamp в имени не даст новой копии перезаписать
предыдущую. Затем удалите и восстановите коллекцию `university.students` одним
контролируемым демонстрационным playbook:

```bash
ansible-playbook playbooks/restore-demo.yml --ask-become-pass --ask-vault-pass
```

Копии находятся на VM в `/var/backups/mongodb-lab`. В реальной системе их также
нужно выгружать в отдельное защищённое хранилище и регулярно проверять
восстановление.

### 7. Нагрузка и графики

Откройте `http://<VM-IP>:3000`, затем запустите:

```bash
ansible-playbook playbooks/load.yml --ask-become-pass --ask-vault-pass
```

Нагрузка работает в фоне 120 секунд. На дашборде сравните соединения, операции в
секунду и память до запуска, во время нагрузки и после завершения.

## Ручное выполнение и сбор доказательств

Скрипты в каталогах `scripts/` и `mongo/` сохранены для показа преподавателю и
пошаговой проверки отдельных операций. Если запускать их напрямую, команды ниже
выполняются на Ubuntu VM из корня копии репозитория.

### 1. Установка и служба вручную

```bash
sudo ./scripts/01-install-mongodb.sh
./scripts/02-mongodb-service.sh status
./scripts/03-healthcheck.sh
```

Демонстрация управления службой:

```bash
sudo ./scripts/02-mongodb-service.sh stop
./scripts/03-healthcheck.sh || true
sudo ./scripts/02-mongodb-service.sh start
sudo ./scripts/02-mongodb-service.sh restart
```

### 2. Администратор и авторизация

Сначала создаётся администратор, пока MongoDB слушает только localhost:

```bash
read -s -p 'Admin password: ' MONGO_ADMIN_PASSWORD; echo
export MONGO_ADMIN_PASSWORD
mongosh --quiet --file mongo/01-create-admin.js
unset MONGO_ADMIN_PASSWORD
sudo ./scripts/04-enable-auth.sh
```

Подключение администратора выполняется без пароля в истории команд:

```bash
mongosh --username lab_admin --authenticationDatabase admin --password
```

### 3. Учебные данные

```bash
mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/02-seed-data.js
```

Создаются базы `university` и `library`.

### 4. Роли и пользователи

```bash
mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/roles/01-create-roles.js
```

Для создания пользователей задайте пароли только в текущей оболочке:

```bash
read -s -p 'Reader password: ' READER_PASSWORD; echo
read -s -p 'Editor password: ' EDITOR_PASSWORD; echo
read -s -p 'Grades password: ' GRADES_PASSWORD; echo
read -s -p 'Temporary password: ' TEMP_PASSWORD; echo
export READER_PASSWORD EDITOR_PASSWORD GRADES_PASSWORD TEMP_PASSWORD

mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/roles/02-create-users.js

unset READER_PASSWORD EDITOR_PASSWORD GRADES_PASSWORD TEMP_PASSWORD
```

Демонстрационные операции:

```bash
mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/roles/03-grant-revoke-role.js

mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/roles/04-update-role.js

./scripts/roles/05-test-collection-access.sh

mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/roles/06-delete-temp-user-role.js
```

### 5. Backup и восстановление

Сначала создаются отдельные операционные пользователи:

```bash
read -s -p 'Backup password: ' BACKUP_PASSWORD; echo
read -s -p 'Restore password: ' RESTORE_PASSWORD; echo
export BACKUP_PASSWORD RESTORE_PASSWORD
mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/03-create-backup-users.js
unset BACKUP_PASSWORD RESTORE_PASSWORD
```

Создание копий:

```bash
./scripts/backup/01-backup-one-db.sh
./scripts/backup/02-backup-all-study-dbs.sh
./scripts/backup/01-backup-one-db.sh
find backups -maxdepth 2 -print
```

Восстановление удалённой `university.students`:

```bash
mongosh --username lab_admin --authenticationDatabase admin --password \
  --eval 'db.getSiblingDB("university").students.drop()'

./scripts/backup/03-restore-students.sh backups/<timestamp>-university
```

### 6. Мониторинг

```bash
mongosh --username lab_admin --authenticationDatabase admin --password \
  --file mongo/04-create-monitoring-user.js

sudo ./scripts/monitoring/01-install-exporter.sh
sudo ./scripts/monitoring/02-install-prometheus.sh
sudo ./scripts/monitoring/03-install-grafana.sh
```

После установки проверьте:

```bash
curl http://127.0.0.1:9216/metrics | grep mongodb_up
curl http://127.0.0.1:9090/-/ready
```

Grafana открывается на Mac по адресу `http://<VM-IP>:3000`.

### 7. Нагрузка

```bash
./scripts/load/run-load.sh
```

Откройте дашборд с обновлением 5 секунд и сравните показатели до, во время и после нагрузки.

## Безопасность

- Пароли не записываются в репозиторий.
- `.env`, backup-архивы и скриншоты с секретами исключены через `.gitignore`.
- Не меняйте `bindIp: 127.0.0.1` без отдельной настройки firewall и авторизации.
