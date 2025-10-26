import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
import sys
import io
import time

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def get_news_without_full_text():
    """Получает все новости, у которых ещё нет полного текста"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, url FROM news WHERE news_full IS NULL')
    news_list = cursor.fetchall()
    
    conn.close()
    return news_list

def parse_full_news(url):
    """Парсит полный текст новости со страницы"""
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
        
        # Ищем div с классом card и style="width: 100%; position: relative;"
        card_div = soup.find('div', class_='card', style=lambda value: value and 'width: 100%' in value and 'position: relative' in value)
        
        if not card_div:
            # Если не найден точный div, попробуем найти любой card на странице новости
            card_div = soup.find('div', class_='card')
        
        if card_div:
            # Извлекаем только текст без HTML разметки
            text = card_div.get_text(separator='\n', strip=True)
            return text
        else:
            print(f"  ⚠ Не найден блок card на странице")
            return None
                
    except Exception as e:
        print(f"  ✗ Ошибка при парсинге: {e}")
        return None

def update_news_full_text(news_id, full_text):
    """Обновляет полный текст новости в базе"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE news SET news_full = ? WHERE id = ?', (full_text, news_id))
    conn.commit()
    conn.close()

def main():
    print("=== Парсинг полного текста новостей ===\n")
    
    # Получаем новости без полного текста
    news_list = get_news_without_full_text()
    
    if not news_list:
        print("✓ Все новости уже имеют полный текст")
        return
    
    print(f"Найдено новостей для парсинга: {len(news_list)}\n")
    
    processed = 0
    failed = 0
    
    for news_id, title, url in news_list:
        print(f"[{processed + failed + 1}/{len(news_list)}] {title[:50]}...")
        
        full_text = parse_full_news(url)
        
        if full_text:
            update_news_full_text(news_id, full_text)
            processed += 1
            print(f"  ✓ Сохранено ({len(full_text)} символов)")
        else:
            failed += 1
            print(f"  ✗ Не удалось получить текст")
        
        # Небольшая задержка между запросами
        time.sleep(2)
    
    print(f"\n=== Результат ===")
    print(f"Обработано успешно: {processed}")
    print(f"Ошибок: {failed}")
    print(f"Всего: {len(news_list)}")

if __name__ == '__main__':
    main()

