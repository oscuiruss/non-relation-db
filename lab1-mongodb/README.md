# Лабораторная работа №1 — эксплуатация MongoDB

Стенд: Ubuntu Server 24.04 ARM64 в VMware Fusion на Mac с Apple Silicon.

## Состав стенда

- MongoDB Community 8.0, порт `27017`;
- Percona MongoDB Exporter, порт `9216`;
- Prometheus, порт `9090`;
- Grafana, порт `3000`.

MongoDB остаётся привязана к `127.0.0.1`. С Mac наружу открывается только SSH и веб-интерфейс Grafana.

## Порядок выполнения

Все команды ниже выполняются на Ubuntu VM из корня репозитория.

### 1. Установка и служба

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
