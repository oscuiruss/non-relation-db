# Лабораторная работа №1 — эксплуатация MongoDB

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
ansible-playbook playbooks/service-demo.yml --ask-become-pass
```

### 6. Резервное копирование и восстановление

Создать копию `university` и общий архив учебных баз:

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
