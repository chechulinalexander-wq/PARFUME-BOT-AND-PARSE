import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def setup_database():
    """Добавляет колонку для переписанного текста и создает таблицу конфигурации"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    # Добавляем колонку для переписанного текста
    try:
        cursor.execute('ALTER TABLE news ADD COLUMN news_rewritten TEXT')
        print("✓ Колонка news_rewritten добавлена")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⊘ Колонка news_rewritten уже существует")
        else:
            print(f"✗ Ошибка: {e}")
    
    # Создаем таблицу для конфигурации (API ключи)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✓ Таблица config создана")
    
    conn.commit()
    conn.close()
    print("\n✓ База данных готова к работе")

if __name__ == '__main__':
    setup_database()



