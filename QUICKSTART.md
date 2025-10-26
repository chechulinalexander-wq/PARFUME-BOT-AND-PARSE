# 🚀 Быстрый старт

## Для пользователя (публикация новостей)

### 1. Первая настройка (делается один раз)

```bash
# Установка библиотек
pip install -r requirements.txt

# Настройка API ключей
python setup_config.py
```

Вам понадобятся:
- **OpenAI API Key** → https://platform.openai.com/api-keys
- **Telegram Bot Token** → @BotFather в Telegram
- **Telegram Channel ID** → @channelname или -100xxxxxxxxxx

### 2. Ежедневная работа

```bash
# Посмотреть список новостей
python view_full_news.py

# Опубликовать новость по ID
python publish_news.py 5
```

Скрипт автоматически:
1. ✓ Отправит текст в ChatGPT для переписывания
2. ✓ Сохранит переписанный текст в БД
3. ✓ Опубликует в Telegram канал

### 3. Дополнительные команды

```bash
# Посмотреть статус переписывания
python view_rewritten_news.py

# Посмотреть переписанный текст конкретной новости
python view_rewritten_news.py 5

# Переписать новость заново (если нужно)
python publish_news.py 5 --force

# Посмотреть настройки (ключи будут скрыты)
python setup_config.py show
```

---

## Для разработчика (парсинг новостей)

### 1. Парсинг новых новостей

```bash
# Спарсить заголовки и полный текст всех новостей
python parse_fragrantica_news.py
```

### 2. Дополнительные команды парсинга

```bash
# Добавить колонку для полного текста (если нужно)
python add_full_news_column.py

# Спарсить только полный текст для существующих новостей
python parse_full_news.py

# Скачать изображения из новостей
python parse_images.py

# Посмотреть список новостей
python view_news.py

# Посмотреть изображения
python view_images.py
```

---

## Структура проекта

```
📁 PARFUME BOT AND PARSE/
├── 🗄️ fragrantica_news.db          # База данных (содержит API ключи!)
│
├── 🔧 Настройка:
│   ├── setup_config.py              # Настройка API ключей
│   └── add_rewritten_column.py      # Обновление БД
│
├── 📥 Парсинг:
│   ├── parse_fragrantica_news.py    # Парсер новостей
│   ├── parse_full_news.py           # Парсинг полного текста
│   └── add_full_news_column.py      # Добавление колонки
│
├── 📤 Публикация:
│   ├── publish_news.py              # ⭐ Главный скрипт
│   └── view_rewritten_news.py       # Просмотр переписанных
│
├── 👁️ Просмотр:
│   ├── view_news.py                 # Список новостей
│   └── view_full_news.py            # Полный текст
│
└── 📚 Документация:
    ├── README.md                    # Основная документация
    ├── SETUP_GUIDE.md               # Подробное руководство
    └── QUICKSTART.md                # Этот файл
```

---

## Примеры использования

### Пример 1: Публикация одной новости

```bash
$ python view_full_news.py
# Смотрим список, выбираем ID, например 3

$ python publish_news.py 3
# Новость переписывается ChatGPT и публикуется в Telegram
```

### Пример 2: Публикация нескольких новостей подряд

```bash
$ python publish_news.py 1
$ python publish_news.py 2
$ python publish_news.py 3
```

### Пример 3: Проверка результата

```bash
$ python view_rewritten_news.py 3
# Смотрим оригинал и переписанный вариант
```

---

## ⚠️ Важные замечания

1. **База данных содержит API ключи** - не публикуйте файл `fragrantica_news.db`
2. **Повторная публикация** - если новость уже переписана, используйте `--force`
3. **Лимиты OpenAI** - проверьте баланс на https://platform.openai.com/usage
4. **Telegram бот** - должен быть администратором канала

---

## 🆘 Решение проблем

| Проблема | Решение |
|----------|---------|
| "OpenAI API Key не настроен" | `python setup_config.py` |
| "Новость с ID X не найдена" | `python view_full_news.py` |
| "Полный текст отсутствует" | `python parse_full_news.py` |
| Ошибка Telegram | Проверьте права бота в канале |
| Хочу изменить промпт | Отредактируйте переменную `PROMPT` в `publish_news.py` |

---

## 📞 Контакты

Подробная документация: [SETUP_GUIDE.md](SETUP_GUIDE.md)

