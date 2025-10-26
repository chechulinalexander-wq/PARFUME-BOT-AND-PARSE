import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_full_news(news_id=None):
    """Показывает полный текст новости"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    if news_id:
        cursor.execute('SELECT id, title, url, news_full FROM news WHERE id = ?', (news_id,))
        news = cursor.fetchone()
        
        if news:
            news_id, title, url, full_text = news
            print(f"ID: {news_id}")
            print(f"Заголовок: {title}")
            print(f"URL: {url}")
            print(f"\n{'='*80}\n")
            print(f"Полный текст новости:")
            print(f"\n{'='*80}\n")
            if full_text:
                print(full_text[:2000])  # Показываем первые 2000 символов
                if len(full_text) > 2000:
                    print(f"\n... (всего {len(full_text)} символов)")
            else:
                print("Полный текст отсутствует")
        else:
            print(f"Новость с ID {news_id} не найдена")
    else:
        # Показываем список всех новостей с размером полного текста
        cursor.execute('SELECT id, title, LENGTH(news_full) as text_length FROM news ORDER BY id DESC')
        
        print("=== Список всех новостей ===\n")
        for row in cursor.fetchall():
            news_id, title, text_length = row
            status = f"{text_length} символов" if text_length else "нет текста"
            print(f"ID: {news_id:2d} | {status:15s} | {title[:60]}")
        
        print(f"\nДля просмотра полного текста запустите: python view_full_news.py <ID>")
    
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            news_id = int(sys.argv[1])
            view_full_news(news_id)
        except ValueError:
            print("Ошибка: ID должен быть числом")
    else:
        view_full_news()



