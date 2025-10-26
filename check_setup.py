import sqlite3
import sys
import io
import os

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_database():
    """Проверяет наличие и структуру базы данных"""
    if not os.path.exists('fragrantica_news.db'):
        print("✗ База данных не найдена")
        print("  Запустите: python parse_fragrantica_news.py")
        return False
    
    print("✓ База данных найдена")
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    # Проверяем таблицу news
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
    if not cursor.fetchone():
        print("✗ Таблица news не найдена")
        conn.close()
        return False
    
    print("✓ Таблица news существует")
    
    # Проверяем колонки
    cursor.execute("PRAGMA table_info(news)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required_columns = {'id', 'title', 'url', 'news_full', 'news_rewritten'}
    missing_columns = required_columns - columns
    
    if missing_columns:
        print(f"✗ Отсутствуют колонки: {', '.join(missing_columns)}")
        if 'news_full' in missing_columns:
            print("  Запустите: python add_full_news_column.py")
        if 'news_rewritten' in missing_columns:
            print("  Запустите: python add_rewritten_column.py")
        conn.close()
        return False
    
    print("✓ Все необходимые колонки присутствуют")
    
    # Проверяем количество новостей
    cursor.execute("SELECT COUNT(*) FROM news")
    count = cursor.fetchone()[0]
    print(f"✓ В базе {count} новостей")
    
    if count == 0:
        print("  ⚠ Новостей нет. Запустите: python parse_fragrantica_news.py")
    
    # Проверяем наличие полного текста
    cursor.execute("SELECT COUNT(*) FROM news WHERE news_full IS NOT NULL")
    full_count = cursor.fetchone()[0]
    print(f"✓ С полным текстом: {full_count}/{count}")
    
    if full_count < count:
        print("  ⚠ Не у всех новостей есть полный текст")
        print("    Запустите: python parse_full_news.py")
    
    # Проверяем наличие переписанных
    cursor.execute("SELECT COUNT(*) FROM news WHERE news_rewritten IS NOT NULL")
    rewritten_count = cursor.fetchone()[0]
    print(f"✓ Переписано: {rewritten_count}/{count}")
    
    # Проверяем наличие изображений
    cursor.execute("SELECT COUNT(*) FROM news WHERE images IS NOT NULL AND images != '[]'")
    images_count = cursor.fetchone()[0]
    print(f"✓ С изображениями: {images_count}/{count}")
    
    if images_count < count:
        print("  ⚠ Не у всех новостей есть изображения")
        print("    Запустите: python parse_images.py")
    
    # Проверяем папку images
    if os.path.exists('images'):
        image_files = len([f for f in os.listdir('images') if os.path.isfile(os.path.join('images', f))])
        print(f"✓ Скачано файлов изображений: {image_files}")
    else:
        print("⚠ Папка images не найдена")
        print("  Запустите: python add_images_column.py")
    
    # Проверяем таблицу config
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config'")
    if not cursor.fetchone():
        print("✗ Таблица config не найдена")
        print("  Запустите: python add_rewritten_column.py")
        conn.close()
        return False
    
    print("✓ Таблица config существует")
    
    conn.close()
    return True

def check_config():
    """Проверяет наличие конфигурации"""
    if not os.path.exists('fragrantica_news.db'):
        return False
    
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT key FROM config")
        keys = {row[0] for row in cursor.fetchall()}
    except:
        conn.close()
        return False
    
    required_keys = {'openai_api_key', 'telegram_bot_token', 'telegram_channel_id'}
    
    print("\n=== Конфигурация ===")
    
    for key in required_keys:
        if key in keys:
            print(f"✓ {key} настроен")
        else:
            print(f"✗ {key} не настроен")
    
    missing_keys = required_keys - keys
    
    if missing_keys:
        print(f"\n⚠ Отсутствуют: {', '.join(missing_keys)}")
        print("  Запустите: python setup_config.py")
        conn.close()
        return False
    
    conn.close()
    return True

def check_dependencies():
    """Проверяет установленные зависимости"""
    print("\n=== Зависимости ===")
    
    dependencies = [
        ('requests', 'requests'),
        ('beautifulsoup4', 'bs4'),
        ('cloudscraper', 'cloudscraper'),
        ('openai', 'openai')
    ]
    
    all_installed = True
    
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            print(f"✗ {package_name} не установлен")
            all_installed = False
    
    if not all_installed:
        print("\n  Запустите: pip install -r requirements.txt")
        return False
    
    return True

def main():
    print("=== Проверка готовности системы ===\n")
    
    # Проверка зависимостей
    deps_ok = check_dependencies()
    
    # Проверка базы данных
    print("\n=== База данных ===")
    db_ok = check_database()
    
    # Проверка конфигурации
    config_ok = check_config()
    
    # Итоги
    print("\n" + "="*50)
    
    if deps_ok and db_ok and config_ok:
        print("✓ БАЗОВАЯ НАСТРОЙКА ЗАВЕРШЕНА!")
        print("\n📝 Рекомендуется протестировать Telegram:")
        print("  python test_telegram.py")
        print("\nИли сразу публикуйте новости:")
        print("  python publish_news.py <ID>")
    else:
        print("⚠ ТРЕБУЕТСЯ НАСТРОЙКА")
        print("\nВыполните необходимые действия выше")
        print("Или смотрите: QUICKSTART.md")
    
    print("="*50)

if __name__ == '__main__':
    main()

