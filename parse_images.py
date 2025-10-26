import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
import sys
import io
import time
import os
import json
from urllib.parse import urljoin
import hashlib

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def get_news_without_images():
    """Получает все новости, у которых ещё нет изображений"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, url FROM news WHERE images IS NULL')
    news_list = cursor.fetchall()
    
    conn.close()
    return news_list

def download_image(url, save_dir='images'):
    """Скачивает изображение и возвращает путь к файлу"""
    try:
        # Создаем имя файла из URL (используем hash для уникальности)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        extension = url.split('.')[-1].split('?')[0][:4]  # Берем расширение
        if extension.lower() not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            extension = 'jpg'
        
        filename = f"{url_hash}.{extension}"
        filepath = os.path.join(save_dir, filename)
        
        # Если уже скачано, пропускаем
        if os.path.exists(filepath):
            return filepath
        
        # Скачиваем
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Сохраняем
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return filepath
        
    except Exception as e:
        print(f"    ✗ Ошибка скачивания {url[:50]}: {e}")
        return None

def parse_images_from_news(url):
    """Парсит изображения со страницы новости"""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    try:
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем основной div с новостью
        card_div = soup.find('div', class_='card', style=lambda value: value and 'width: 100%' in value and 'position: relative' in value)
        
        if not card_div:
            card_div = soup.find('div', class_='card')
        
        if not card_div:
            return []
        
        # Ищем все изображения
        images = []
        for img in card_div.find_all('img'):
            img_url = img.get('src')
            if img_url:
                # Преобразуем относительные URL в абсолютные
                img_url = urljoin(url, img_url)
                
                # Пропускаем маленькие изображения (иконки и т.д.)
                width = img.get('width', '')
                if width and width.isdigit() and int(width) < 100:
                    continue
                
                images.append(img_url)
        
        return images
        
    except Exception as e:
        print(f"  ✗ Ошибка парсинга: {e}")
        return []

def save_images_to_db(news_id, image_paths):
    """Сохраняет пути к изображениям в БД"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    # Сохраняем как JSON
    images_json = json.dumps(image_paths, ensure_ascii=False)
    cursor.execute('UPDATE news SET images = ? WHERE id = ?', (images_json, news_id))
    
    conn.commit()
    conn.close()

def process_news_images(news_id, title, url):
    """Обрабатывает изображения для одной новости"""
    print(f"\n📰 {title[:50]}...")
    print(f"  🔗 {url}")
    
    # Парсим URL изображений
    print("  🔍 Ищу изображения...")
    image_urls = parse_images_from_news(url)
    
    if not image_urls:
        print("  ⊘ Изображений не найдено")
        save_images_to_db(news_id, [])
        return 0
    
    print(f"  📸 Найдено изображений: {len(image_urls)}")
    
    # Скачиваем изображения
    downloaded = []
    for i, img_url in enumerate(image_urls, 1):
        print(f"  [{i}/{len(image_urls)}] Скачиваю: {img_url[:60]}...")
        filepath = download_image(img_url)
        if filepath:
            downloaded.append(filepath)
            print(f"    ✓ Сохранено: {filepath}")
        time.sleep(0.5)  # Небольшая задержка
    
    # Сохраняем в БД
    save_images_to_db(news_id, downloaded)
    print(f"  ✓ Сохранено в БД: {len(downloaded)} изображений")
    
    return len(downloaded)

def main():
    print("=== Парсинг изображений из новостей ===\n")
    
    # Проверяем наличие папки
    if not os.path.exists('images'):
        print("✗ Папка images не найдена")
        print("  Запустите: python add_images_column.py")
        return
    
    # Получаем новости без изображений
    news_list = get_news_without_images()
    
    if not news_list:
        print("✓ У всех новостей уже есть изображения")
        return
    
    print(f"Найдено новостей для обработки: {len(news_list)}\n")
    
    total_images = 0
    processed = 0
    
    for news_id, title, url in news_list:
        processed += 1
        print(f"\n{'='*80}")
        print(f"[{processed}/{len(news_list)}]")
        
        count = process_news_images(news_id, title, url)
        total_images += count
        
        # Задержка между новостями
        if processed < len(news_list):
            time.sleep(2)
    
    print(f"\n{'='*80}")
    print("=== Результат ===")
    print(f"Обработано новостей: {processed}")
    print(f"Скачано изображений: {total_images}")
    print(f"Средне на новость: {total_images/processed:.1f}")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()



