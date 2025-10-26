import sqlite3
import sys
import io
import json
import os

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def view_images(news_id=None):
    """Показывает изображения новости"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    if news_id:
        cursor.execute('SELECT id, title, images FROM news WHERE id = ?', (news_id,))
        news = cursor.fetchone()
        
        if news:
            news_id, title, images_json = news
            print(f"ID: {news_id}")
            print(f"Заголовок: {title}")
            print(f"\n{'='*80}\n")
            
            if images_json:
                try:
                    images = json.loads(images_json)
                    print(f"📸 Изображений: {len(images)}\n")
                    
                    for i, img_path in enumerate(images, 1):
                        exists = "✓" if os.path.exists(img_path) else "✗"
                        size = ""
                        if os.path.exists(img_path):
                            size_kb = os.path.getsize(img_path) / 1024
                            size = f" ({size_kb:.1f} KB)"
                        
                        print(f"{i}. {exists} {img_path}{size}")
                    
                except json.JSONDecodeError:
                    print("✗ Ошибка чтения данных изображений")
            else:
                print("⊘ Изображений нет")
        else:
            print(f"✗ Новость с ID {news_id} не найдена")
    else:
        # Показываем список всех новостей с количеством изображений
        cursor.execute('''
            SELECT id, title, images
            FROM news 
            ORDER BY id DESC
        ''')
        
        print("=== Изображения в новостях ===\n")
        
        total_news = 0
        total_images = 0
        
        for row in cursor.fetchall():
            news_id, title, images_json = row
            total_news += 1
            
            count = 0
            if images_json:
                try:
                    images = json.loads(images_json)
                    count = len(images)
                    total_images += count
                except:
                    pass
            
            status = f"{count} изобр." if count > 0 else "нет изобр."
            print(f"ID: {news_id:2d} | {status:15s} | {title[:60]}")
        
        print(f"\n{'='*80}")
        print(f"Всего новостей: {total_news}")
        print(f"Всего изображений: {total_images}")
        print(f"Средне на новость: {total_images/total_news:.1f}")
        print(f"\nДля просмотра: python view_images.py <ID>")
    
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            news_id = int(sys.argv[1])
            view_images(news_id)
        except ValueError:
            print("✗ ID должен быть числом")
    else:
        view_images()



