import sqlite3
import sys
import io

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_rewritten(news_id=None):
    """Показывает переписанный текст новости"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    if news_id:
        cursor.execute('SELECT id, title, news_full, news_rewritten FROM news WHERE id = ?', (news_id,))
        news = cursor.fetchone()
        
        if news:
            news_id, title, original, rewritten = news
            print(f"ID: {news_id}")
            print(f"Заголовок: {title}")
            print(f"\n{'='*80}\n")
            
            if original:
                print("ОРИГИНАЛЬНЫЙ ТЕКСТ:")
                print(f"\n{original[:300]}...")
                print(f"\n(Всего {len(original)} символов)\n")
                print(f"{'='*80}\n")
            
            if rewritten:
                print("ПЕРЕПИСАННЫЙ ТЕКСТ (для Telegram):")
                print(f"\n{rewritten}\n")
                print(f"{'='*80}\n")
                print(f"Размер: {len(rewritten)} символов")
            else:
                print("⊘ Переписанный текст отсутствует")
                print("Запустите: python publish_news.py", news_id)
        else:
            print(f"✗ Новость с ID {news_id} не найдена")
    else:
        # Показываем список всех новостей со статусом переписывания
        cursor.execute('''
            SELECT id, title, 
                   LENGTH(news_full) as original_length,
                   LENGTH(news_rewritten) as rewritten_length
            FROM news 
            ORDER BY id DESC
        ''')
        
        print("=== Статус переписывания новостей ===\n")
        
        total = 0
        rewritten_count = 0
        
        for row in cursor.fetchall():
            news_id, title, orig_len, rew_len = row
            total += 1
            
            if rew_len:
                status = f"✓ Переписано ({rew_len} симв.)"
                rewritten_count += 1
            else:
                status = "⊘ Не переписано"
            
            print(f"ID: {news_id:2d} | {status:30s} | {title[:50]}")
        
        print(f"\n{'='*80}")
        print(f"Переписано: {rewritten_count}/{total}")
        print(f"Осталось: {total - rewritten_count}")
        print(f"\nДля просмотра: python view_rewritten_news.py <ID>")
    
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            news_id = int(sys.argv[1])
            view_rewritten(news_id)
        except ValueError:
            print("✗ ID должен быть числом")
    else:
        view_rewritten()



