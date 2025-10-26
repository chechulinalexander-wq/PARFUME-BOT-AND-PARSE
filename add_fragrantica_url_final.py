import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
import sys
import io
import time
from urllib.parse import urljoin
import re
import unicodedata
from rapidfuzz import fuzz

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def add_fragrantica_url_column():
    """Добавляет колонку fragrantica_url в таблицу"""
    conn = sqlite3.connect('fragrantica_news.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE randewoo_products ADD COLUMN fragrantica_url TEXT')
        conn.commit()
        print("✓ Колонка fragrantica_url добавлена")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print("⊘ Колонка fragrantica_url уже существует")
        else:
            raise
    
    return conn

def normalize_text(text):
    """
    Нормализует текст для сравнения с правильной обработкой диакритических знаков
    é → e, ñ → n, ü → u и т.д.
    """
    # Удаляем диакритические знаки (é → e)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Оставляем только буквы и цифры
    text = re.sub(r'[^a-z0-9]', '', text.lower())
    
    return text

def search_fragrantica_final(scraper, brand, name, brand_cache):
    """
    Финальная версия поиска с fuzzy matching
    """
    
    # Стратегия 1: Проверяем кеш бренда
    brand_key = brand.lower().strip()
    if brand_key in brand_cache:
        perfume_links = brand_cache[brand_key]
        
        # Нормализуем название для поиска
        name_normalized = normalize_text(name)
        name_lower = name.lower().strip()
        
        best_match = None
        best_match_score = 0
        
        for plink in perfume_links:
            ptext_normalized = normalize_text(plink['text'])
            ptext_lower = plink['text'].lower().strip()
            
            # Точное совпадение
            if name_normalized == ptext_normalized:
                return plink['url']
            
            # Fuzzy matching с несколькими методами
            # 1. Token sort ratio (игнорирует порядок слов)
            fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
            
            # 2. Partial ratio (частичное совпадение)
            partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
            
            # 3. Token set ratio (игнорирует дубликаты слов)
            token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
            
            # Берем максимальный score
            max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
            
            # Если совпадение достаточно хорошее
            if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:  # Порог 70%
                best_match = plink['url']
                best_match_score = max_fuzzy_score
            
            # Дополнительная проверка: все слова из короткого названия есть в длинном
            if len(name_normalized) > 5:
                name_words = set(name_lower.split())
                ptext_words = set(ptext_lower.split())
                
                # Считаем сколько слов совпадает
                common_words = name_words & ptext_words
                if len(name_words) > 0:
                    word_match_ratio = len(common_words) / len(name_words) * 100
                    
                    if word_match_ratio > best_match_score and word_match_ratio >= 70:
                        best_match = plink['url']
                        best_match_score = word_match_ratio
        
        # Возвращаем лучшее совпадение если оно достаточно хорошее
        if best_match and best_match_score >= 70:
            return best_match
        
        return None
    
    # Стратегия 2: Формируем прямой URL страницы бренда
    # Пробуем только самые вероятные варианты для скорости
    brand_variants = [
        brand.replace(' ', '-'),  # Самый распространенный вариант
        brand,  # Исходное название
    ]
    
    brand_page_url = None
    perfume_links = []
    
    for brand_variant in brand_variants:
        test_url = f"https://www.fragrantica.ru/designers/{brand_variant}.html"
        
        try:
            # Используем GET вместо HEAD
            response = scraper.get(test_url, timeout=10)
            
            if response.status_code == 200:
                brand_page_url = test_url
                break
        except Exception as e:
            continue
        
        time.sleep(0.5)  # Небольшая пауза между попытками
    
    # Если нашли страницу бренда - парсим её
    if brand_page_url:
        try:
            time.sleep(1)
            response = scraper.get(brand_page_url, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все ароматы
            perfume_links_raw = soup.find_all('a', href=lambda x: x and '/perfume/' in x)
            
            name_normalized = normalize_text(name)
            name_lower = name.lower().strip()
            result_url = None
            best_match_score = 0
            
            for plink in perfume_links_raw:
                purl = urljoin('https://www.fragrantica.ru', plink.get('href'))
                ptext = plink.get_text(strip=True)
                perfume_links.append({'url': purl, 'text': ptext})
                
                # Проверяем совпадение с улучшенной нормализацией
                ptext_normalized = normalize_text(ptext)
                ptext_lower = ptext.lower().strip()
                
                # Точное совпадение
                if name_normalized == ptext_normalized:
                    result_url = purl
                    break
                
                # Fuzzy matching
                fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
                partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
                token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
                
                max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
                
                if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:
                    result_url = purl
                    best_match_score = max_fuzzy_score
                
                # Проверка по словам
                if len(name_normalized) > 5:
                    name_words = set(name_lower.split())
                    ptext_words = set(ptext_lower.split())
                    common_words = name_words & ptext_words
                    
                    if len(name_words) > 0:
                        word_match_ratio = len(common_words) / len(name_words) * 100
                        if word_match_ratio > best_match_score and word_match_ratio >= 70:
                            result_url = purl
                            best_match_score = word_match_ratio
            
            # Кешируем бренд
            brand_cache[brand_key] = perfume_links
            
            if result_url:
                return result_url
                
        except Exception as e:
            pass
    
    # Стратегия 3: Поиск через форму (точный запрос)
    try:
        search_url = "https://www.fragrantica.ru/search/"
        
        # Пробуем разные комбинации
        search_queries = [
            f"{brand} {name}",
            name,
            f"{name} {brand}",
        ]
        
        for query in search_queries:
            params = {'query': query}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://www.fragrantica.ru/'
            }
            
            response = scraper.get(search_url, params=params, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            perfume_links_search = soup.find_all('a', href=lambda x: x and '/perfume/' in x)
            
            brand_normalized = normalize_text(brand)
            name_normalized = normalize_text(name)
            
            for link in perfume_links_search:
                href = link.get('href')
                text = link.get_text(strip=True)
                text_normalized = normalize_text(text)
                
                # Проверяем, что есть оба: бренд и название
                if brand_normalized in text_normalized and name_normalized in text_normalized:
                    return urljoin('https://www.fragrantica.ru', href)
            
            time.sleep(0.5)
            
    except Exception as e:
        pass
    
    # Стратегия 4: Поиск через каталог всех брендов (если не нашли прямым URL)
    if not brand_page_url:
        try:
            designers_url = "https://www.fragrantica.ru/designers/"
            response = scraper.get(designers_url, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            brand_links = soup.find_all('a', href=lambda x: x and ('/designers/' in x or '/designer/' in x))
            
            brand_normalized = normalize_text(brand)
            
            for link in brand_links:
                link_text = link.get_text(strip=True)
                link_text_normalized = normalize_text(link_text)
                
                if brand_normalized == link_text_normalized or brand_normalized in link_text_normalized:
                    brand_page_url = urljoin('https://www.fragrantica.ru', link.get('href'))
                    
                    # Парсим страницу бренда
                    time.sleep(1)
                    response = scraper.get(brand_page_url, timeout=30)
                    response.encoding = 'utf-8'
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    perfume_links_raw = soup.find_all('a', href=lambda x: x and '/perfume/' in x)
                    
                    name_normalized = normalize_text(name)
                    name_lower = name.lower().strip()
                    best_match = None
                    best_score = 0
                    
                    for plink in perfume_links_raw:
                        purl = urljoin('https://www.fragrantica.ru', plink.get('href'))
                        ptext = plink.get_text(strip=True)
                        ptext_normalized = normalize_text(ptext)
                        ptext_lower = ptext.lower().strip()
                        
                        if name_normalized == ptext_normalized:
                            return purl
                        
                        # Fuzzy matching
                        fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
                        partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
                        token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
                        
                        max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
                        
                        if max_fuzzy_score > best_score and max_fuzzy_score >= 70:
                            best_match = purl
                            best_score = max_fuzzy_score
                        
                        # Проверка по словам
                        if len(name_normalized) > 5:
                            name_words = set(name_lower.split())
                            ptext_words = set(ptext_lower.split())
                            common_words = name_words & ptext_words
                            
                            if len(name_words) > 0:
                                word_match_ratio = len(common_words) / len(name_words) * 100
                                if word_match_ratio > best_score and word_match_ratio >= 70:
                                    best_match = purl
                                    best_score = word_match_ratio
                    
                    if best_match and best_score >= 70:
                        return best_match
                    
                    break
                    
        except Exception as e:
            pass
    
    return None

def process_all_products():
    """Обрабатывает все товары и добавляет URL Fragrantica с пакетной обработкой"""
    conn = add_fragrantica_url_column()
    cursor = conn.cursor()
    
    # Получаем все товары без URL Fragrantica
    cursor.execute('''
        SELECT id, brand, name 
        FROM randewoo_products 
        WHERE fragrantica_url IS NULL
        ORDER BY id
    ''')
    products = cursor.fetchall()
    
    if not products:
        print("✓ Все товары уже обработаны")
        conn.close()
        return
    
    print(f"\nНайдено товаров для обработки: {len(products)}\n")
    
    # Статистика
    found = 0
    not_found = 0
    total_time = 0
    times = []
    
    # ПАКЕТНАЯ ОБРАБОТКА
    BATCH_SIZE = 10
    BATCH_PAUSE = 2  # секунды между пакетами
    
    total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(0, len(products), BATCH_SIZE):
        batch_products = products[batch_num:batch_num + BATCH_SIZE]
        current_batch = batch_num // BATCH_SIZE + 1
        
        print(f"{'='*80}")
        print(f"ПАКЕТ {current_batch}/{total_batches} (товары {batch_num + 1}-{min(batch_num + BATCH_SIZE, len(products))})")
        print(f"{'='*80}\n")
        
        # Создаем НОВЫЙ scraper для каждого пакета (свежая сессия)
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # Новый кеш для каждого пакета
        brand_cache = {}
        
        for idx_in_batch, (product_id, brand, name) in enumerate(batch_products, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(products)}] {brand} - {name}")
            
            start_time = time.time()
            
            try:
                fragrantica_url = search_fragrantica_final(scraper, brand, name, brand_cache)
                
                elapsed = time.time() - start_time
                times.append(elapsed)
                total_time += elapsed
                
                if fragrantica_url:
                    cursor.execute('''
                        UPDATE randewoo_products 
                        SET fragrantica_url = ? 
                        WHERE id = ?
                    ''', (fragrantica_url, product_id))
                    conn.commit()
                    
                    found += 1
                    print(f"  ✓ Найдено за {elapsed:.2f}с: {fragrantica_url}")
                else:
                    not_found += 1
                    print(f"  ✗ Не найдено за {elapsed:.2f}с")
                
                # Статистика
                if times:
                    avg_time = sum(times) / len(times)
                    print(f"  Среднее: {avg_time:.2f}с | Найдено: {found}/{len(times)} ({found/len(times)*100:.1f}%)")
                
                # Небольшая пауза между товарами
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n\n⚠ Прервано пользователем")
                conn.close()
                return
            except Exception as e:
                elapsed = time.time() - start_time
                times.append(elapsed)
                print(f"  ✗ Ошибка за {elapsed:.2f}с: {e}")
                not_found += 1
                time.sleep(0.5)
        
        # ПАУЗА МЕЖДУ ПАКЕТАМИ
        if current_batch < total_batches:
            print(f"\n⏸  Пауза {BATCH_PAUSE} сек перед следующим пакетом...\n")
            time.sleep(BATCH_PAUSE)
    
    conn.close()
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ:")
    print(f"  Обработано: {len(times)}")
    print(f"  Найдено: {found} ({found/len(times)*100:.1f}%)")
    print(f"  Не найдено: {not_found} ({not_found/len(times)*100:.1f}%)")
    print(f"  Общее время: {total_time:.2f}с")
    if times:
        print(f"  Среднее время на 1 товар: {sum(times)/len(times):.2f}с")
        print(f"  Мин. время: {min(times):.2f}с")
        print(f"  Макс. время: {max(times):.2f}с")
    print(f"{'='*80}")

if __name__ == '__main__':
    process_all_products()

