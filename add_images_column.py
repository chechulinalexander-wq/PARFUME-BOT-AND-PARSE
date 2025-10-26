import sqlite3
import sys
import io
import os

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def setup_images():
    """Добавляет колонку для изображений и создает папку"""
    
    # Создаем папку для изображений
    if not os.path.exists('images'):
        os.makedirs('images')
        print("✓ Папка images создана")
    else:
        print("⊘ Папка images уже существует")
    
    # Добавляем колонку в БД
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE news ADD COLUMN images TEXT')
        print("✓ Колонка images добавлена")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⊘ Колонка images уже существует")
        else:
            print(f"✗ Ошибка: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Готово к скачиванию изображений")

if __name__ == '__main__':
    setup_images()



