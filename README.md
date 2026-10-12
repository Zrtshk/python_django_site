# Интернет-магазин на Django

## Требования
- Python 3.8+
- Django 4.2+
- SQLite / PostgreSQL
- pip
- Git

## Установка и запуск

### 1. Клонирование репозитория
```bash
git clone <url-репозитория>
cd python_django_diploma
```

### 2. Создание виртуального окружения
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Установка фронтенд-пакета
```bash
cd diploma-frontend
python setup.py sdist
pip install dist/diploma-frontend-*.tar.gz
cd ..
```

### 5. Настройка .env
Создайте файл .env в корне проекта:
```text
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```
Для продакшена замените DEBUG=True на DEBUG=False и укажите реальные хосты.

### 6. Миграции базы данных
```bash
python manage.py migrate
```

### 7. Создание тестовых данных
```bash
python manage.py setup_test_data
```
Будут созданы:

- Администратор

- 5 покупателей

- Категории товаров

- Товары с изображениями

- Характеристики

- Отзывы

- Настройки доставки

### 8. Запуск сервера
```bash
python manage.py runserver
```
Откройте в браузере: http://127.0.0.1:8000

## Тестовые данные

| Роль | Email | Пароль |
|------|-------|--------|
| Администратор | admin@example.com | admin123 |
| Покупатель 1 | user1@example.com | 123456 |
| Покупатель 2 | user2@example.com | 123456 |
| Покупатель 3 | user3@example.com | 123456 |
| Покупатель 4 | user4@example.com | 123456 |
| Покупатель 5 | user5@example.com | 123456 |

## API Документация
После запуска сервера документация доступна по адресу:

- Swagger UI: http://127.0.0.1:8000/swagger/

## Структура проекта

```text
python_django_diploma/
├── config/              # Настройки проекта
├── shop/                # Основное приложение
│   ├── fixtures/        # Фикстуры данных
│   ├── management/      # Команды управления
│   ├── migrations/      # Миграции БД
│   ├── static/          # Статика приложения
│   ├── __init__.py
│   ├── admin.py         # Админка
│   ├── apps.py          # Конфиг приложения
│   ├── models.py        # Модели данных
│   ├── serializers.py   # Сериализаторы
│   ├── tests.py         # Тесты
│   ├── urls.py          # Маршруты приложения
│   └── views.py         # Представления
├── static/              # Статические файлы
├── staticfiles/         # Собранная статика
├── media/               # Загруженные файлы
├── diploma-frontend/    # Исходники фронтенда и Фронтенд(готовый)
├── requirements.txt     # Зависимости
├── .env                 # Переменные окружения
├── db.sqlite3           # База данных
└── README.md            # Документация
```