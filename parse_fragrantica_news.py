import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import io
import time
import os

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def create_database():
    """Создает базу данных и таблицу для новостей"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            news_full TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

def parse_news():
    """Парсит новости с главной страницы Fragrantica"""
    url = 'https://www.fragrantica.ru/'
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    print(f"Загружаю страницу {url}...")
    time.sleep(1)
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Находим все блоки с новостями
    news_cards = soup.find_all('div', class_='card')
    print(f"Найдено блоков card: {len(news_cards)}")
    
    news_list = []
    
    for card in news_cards:
        # Ищем div с классом card-divider, который содержит заголовок и ссылку
        divider = card.find('div', class_='card-divider')
        if not divider:
            continue
            
        # Находим ссылку на новость
        link = divider.find('a', href=lambda href: href and '/news/' in href)
        if not link:
            continue
        
        title = link.get_text(strip=True)
        news_url = urljoin(url, link['href'])
        
        news_list.append({
            'title': title,
            'url': news_url
        })
    
    return news_list

def parse_full_news(url, scraper):
    """Парсит полный текст новости со страницы"""
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
            return None
                
    except Exception as e:
        print(f"    ✗ Ошибка при парсинге полного текста: {e}")
        return None

def save_to_database(conn, news_list, parse_full_text=True):
    """Сохраняет новости в базу данных"""
    cursor = conn.cursor()
    
    added = 0
    skipped = 0
    
    scraper = None
    if parse_full_text:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
    
    for idx, news in enumerate(news_list, 1):
        try:
            full_text = None
            
            if parse_full_text:
                print(f"  [{idx}/{len(news_list)}] Парсинг полного текста: {news['title'][:50]}...")
                full_text = parse_full_news(news['url'], scraper)
                if full_text:
                    print(f"    ✓ Получено {len(full_text)} символов")
                time.sleep(2)  # Задержка между запросами
            
            cursor.execute('''
                INSERT INTO news (title, url, news_full)
                VALUES (?, ?, ?)
            ''', (news['title'], news['url'], full_text))
            added += 1
            print(f"✓ Добавлено: {news['title'][:60]}...")
        except sqlite3.IntegrityError:
            skipped += 1
            print(f"⊘ Пропущено (дубликат): {news['title'][:60]}...")
    
    conn.commit()
    return added, skipped

def main():
    print("=== Парсер новостей Fragrantica ===\n")
    
    # Создаем БД
    conn = create_database()
    print("✓ База данных создана/открыта\n")
    
    # Парсим новости
    try:
        news_list = parse_news()
        print(f"\n✓ Спарсено новостей: {len(news_list)}\n")
        
        if news_list:
            # Сохраняем в БД
            added, skipped = save_to_database(conn, news_list)
            print(f"\n=== Результат ===")
            print(f"Добавлено: {added}")
            print(f"Пропущено (дубликаты): {skipped}")
            print(f"Всего в базе: {added + skipped}")
        else:
            print("⚠ Новости не найдены")
    
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()

