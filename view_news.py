import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_all_news():
    """Показывает все новости из базы данных"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM news')
    total = cursor.fetchone()[0]
    
    print(f"=== Всего новостей в базе: {total} ===\n")
    
    cursor.execute('SELECT id, title, url, parsed_at FROM news ORDER BY id DESC')
    
    for row in cursor.fetchall():
        news_id, title, url, parsed_at = row
        print(f"ID: {news_id}")
        print(f"Заголовок: {title}")
        print(f"URL: {url}")
        print(f"Добавлено: {parsed_at}")
        print("-" * 80)
    
    conn.close()

if __name__ == '__main__':
    view_all_news()



