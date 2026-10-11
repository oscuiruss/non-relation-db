# Отчёт по лабораторной работе №1

## Стенд

- Host: macOS, Apple Silicon M3
- Hypervisor: VMware Fusion
- Guest: Ubuntu Server 24.04 ARM64
- MongoDB: <!-- вставить вывод mongod --version -->

## Часть 1. Базовая настройка

### Установка и автозапуск

Команды и результаты:

```text
<!-- systemctl is-enabled mongod; systemctl is-active mongod -->
```

### Start, stop, restart и healthcheck

```text
<!-- вставить вывод -->
```

## Часть 2. Ролевая модель

### Пользователи и собственные роли

```text
<!-- rolesInfo/usersInfo без паролей -->
```

### Назначение и отзыв роли

```text
<!-- вывод 03-grant-revoke-role.js -->
```

### Изменение разрешений роли

```text
<!-- вывод 04-update-role.js -->
```

### Доступ только к collection university.grades

```text
<!-- успешное чтение grades и Unauthorized для students -->
```

### Удаление пользователя и роли

```text
<!-- вывод 06-delete-temp-user-role.js -->
```

## Часть 3. Резервное копирование и восстановление

### Одна база и все учебные базы

```text
<!-- пути к backup-файлам и find backups -->
```

### Восстановление university.students

```text
<!-- count до удаления, после удаления и после restore -->
```

## Часть 4. Мониторинг

### Exporter и Prometheus target

```text
<!-- mongodb_up и состояние target=UP -->
```

### Выбранные метрики

- доступность MongoDB;
- операции в секунду по типу;
- текущие и доступные соединения;
- resident memory;
- uptime.

### Влияние нагрузки

<!-- Вставить скриншоты Grafana до нагрузки и во время нагрузки. -->

## Вывод

<!-- Кратко описать полученные навыки. -->

