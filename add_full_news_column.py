import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def add_column():
    """Добавляет колонку news_full в таблицу news"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE news ADD COLUMN news_full TEXT')
        conn.commit()
        print("✓ Колонка news_full успешно добавлена")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⊘ Колонка news_full уже существует")
        else:
            print(f"✗ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_column()



