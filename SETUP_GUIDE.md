# Руководство по настройке и публикации

## Шаг 1: Установка зависимостей

```bash
pip install -r requirements.txt
```

## Шаг 2: Настройка API ключей

### Получение API ключей

1. **OpenAI API Key**
   - Перейдите на https://platform.openai.com/api-keys
   - Создайте новый API ключ
   - Скопируйте его (он показывается только один раз!)

2. **Telegram Bot Token**
   - Найдите @BotFather в Telegram
   - Отправьте команду `/newbot`
   - Следуйте инструкциям и получите токен
   - Токен выглядит так: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

3. **Telegram Channel ID**
   - Создайте канал в Telegram
   - Добавьте бота в канал как администратора
   - ID канала: `@channelname` или `-100xxxxxxxxxx`
   - Для получения числового ID можно использовать @userinfobot

### Сохранение ключей в БД

```bash
python setup_config.py
```

Скрипт попросит ввести:
- OpenAI API Key (ввод скрыт)
- Telegram Bot Token (ввод скрыт)
- Telegram Channel ID

### Просмотр текущей конфигурации

```bash
python setup_config.py show
```

## Шаг 3: Парсинг новостей

Если вы еще не спарсили новости:

```bash
# Парсинг заголовков и полного текста
python parse_fragrantica_news.py
```

Если новости уже есть, но нет полного текста:

```bash
# Добавить колонку news_full
python add_full_news_column.py

# Спарсить полный текст
python parse_full_news.py
```

## Шаг 4: Публикация новости

### Вариант 1: Интерактивный режим

```bash
python publish_news.py
```

Скрипт попросит ввести ID новости.

### Вариант 2: С указанием ID

```bash
python publish_news.py 3
```

### Вариант 3: Принудительная перезапись

Если новость уже была переписана ChatGPT, но вы хотите переписать заново:

```bash
python publish_news.py 3 --force
```

## Процесс публикации

Скрипт выполнит:

1. ✓ Проверит наличие API ключей
2. ✓ Загрузит новость из БД
3. ✓ Отправит текст в ChatGPT для переписывания (модель gpt-4o)
4. ✓ Сохранит переписанный текст в БД
5. ✓ Покажет превью текста
6. ✓ Опубликует в Telegram канал

## Примеры использования

```bash
# Посмотреть список новостей
python view_full_news.py

# Посмотреть конкретную новость
python view_full_news.py 5

# Опубликовать новость
python publish_news.py 5

# Переписать и опубликовать заново
python publish_news.py 5 --force
```

## Структура БД после настройки

**Таблица: news**
- `id` - уникальный идентификатор
- `title` - заголовок новости
- `url` - ссылка на новость
- `news_full` - полный текст (оригинал)
- `news_rewritten` - переписанный текст для Telegram
- `parsed_at` - дата парсинга

**Таблица: config**
- `key` - название параметра
- `value` - значение (API ключи)
- `updated_at` - дата обновления

## Безопасность

⚠️ **ВАЖНО:**
- Файл `fragrantica_news.db` содержит API ключи
- Не публикуйте его в открытый доступ
- Добавьте в `.gitignore`:
  ```
  fragrantica_news.db
  *.db
  ```

## Устранение проблем

### Ошибка: "OpenAI API Key не настроен"
```bash
python setup_config.py
```

### Ошибка: "Новость с ID X не найдена"
```bash
# Проверьте список новостей
python view_full_news.py
```

### Ошибка: "Полный текст новости отсутствует"
```bash
# Спарсите полный текст
python parse_full_news.py
```

### Ошибка при публикации в Telegram
- Убедитесь, что бот добавлен в канал как администратор
- Проверьте правильность Channel ID
- Для публичного канала: `@channelname`
- Для приватного канала: `-100xxxxxxxxxx`



