import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import io
import time
import unicodedata
import re
from rapidfuzz import fuzz

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# НАСТРОЙКИ SMARTPROXY
# ============================================================================

SMARTPROXY_HOST = "proxy.smartproxy.net"
SMARTPROXY_PORT = 3120
SMARTPROXY_USER = "smart-qad2gx6xmehj"
SMARTPROXY_PASS = "twYMsn3pEJ4DqZqk"

# Формируем URL прокси
PROXY_URL = f"http://{SMARTPROXY_USER}:{SMARTPROXY_PASS}@{SMARTPROXY_HOST}:{SMARTPROXY_PORT}"

def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return text.strip()

def search_fragrantica(scraper, brand, name, brand_cache):
    """Проверенная функция поиска"""
    
    brand_key = brand.lower().strip()
    if brand_key in brand_cache:
        perfume_links = brand_cache[brand_key]
        
        name_normalized = normalize_text(name)
        name_lower = name.lower().strip()
        
        best_match = None
        best_match_score = 0
        
        for plink in perfume_links:
            purl = plink['url']
            ptext = plink['text']
            
            ptext_normalized = normalize_text(ptext)
            ptext_lower = ptext.lower().strip()
            
            if name_normalized == ptext_normalized:
                return purl
            
            fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
            partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
            token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
            
            max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
            
            if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:
                best_match = purl
                best_match_score = max_fuzzy_score
            
            if len(name_normalized) > 5:
                name_words = set(name_lower.split())
                ptext_words = set(ptext_lower.split())
                common_words = name_words & ptext_words
                
                if len(name_words) > 0:
                    word_match_ratio = len(common_words) / len(name_words) * 100
                    
                    if word_match_ratio > best_match_score and word_match_ratio >= 70:
                        best_match = purl
                        best_match_score = word_match_ratio
        
        if best_match and best_match_score >= 70:
            return best_match
        
        return None
    
    brand_variants = [
        brand.replace(' ', '-'),
        brand,
    ]
    
    brand_page_url = None
    perfume_links = []
    
    for brand_variant in brand_variants:
        test_url = f"https://www.fragrantica.ru/designers/{brand_variant}.html"
        
        try:
            response = scraper.get(test_url, timeout=10)
            
            if response.status_code == 200:
                brand_page_url = test_url
                break
        except:
            continue
        
        time.sleep(2)  # Пауза между проверками URL бренда
    
    if brand_page_url:
        try:
            time.sleep(1)
            response = scraper.get(brand_page_url, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            perfume_links_raw = soup.find_all('a', href=lambda x: x and '/perfume/' in x)
            
            name_normalized = normalize_text(name)
            name_lower = name.lower().strip()
            result_url = None
            best_match_score = 0
            
            for plink in perfume_links_raw:
                purl = urljoin('https://www.fragrantica.ru', plink.get('href'))
                ptext = plink.get_text(strip=True)
                perfume_links.append({'url': purl, 'text': ptext})
                
                ptext_normalized = normalize_text(ptext)
                ptext_lower = ptext.lower().strip()
                
                if name_normalized == ptext_normalized:
                    result_url = purl
                    break
                
                fuzzy_score = fuzz.token_sort_ratio(name_lower, ptext_lower)
                partial_score = fuzz.partial_ratio(name_lower, ptext_lower)
                token_set_score = fuzz.token_set_ratio(name_lower, ptext_lower)
                
                max_fuzzy_score = max(fuzzy_score, partial_score, token_set_score)
                
                if max_fuzzy_score > best_match_score and max_fuzzy_score >= 70:
                    result_url = purl
                    best_match_score = max_fuzzy_score
                
                if len(name_normalized) > 5:
                    name_words = set(name_lower.split())
                    ptext_words = set(ptext_lower.split())
                    common_words = name_words & ptext_words
                    
                    if len(name_words) > 0:
                        word_match_ratio = len(common_words) / len(name_words) * 100
                        if word_match_ratio > best_match_score and word_match_ratio >= 70:
                            result_url = purl
                            best_match_score = word_match_ratio
            
            brand_cache[brand_key] = perfume_links
            
            if result_url:
                return result_url
        
        except Exception as e:
            pass
    
    brand_cache[brand_key] = []
    return None

def main():
    print("="*80)
    print("ИСПРАВЛЕНИЕ ПОИСКА НА FRAGRANTICA")
    print("="*80 + "\n")
    
    print(f"🌐 Прокси: {SMARTPROXY_HOST}:{SMARTPROXY_PORT}")
    print(f"👤 User: {SMARTPROXY_USER}\n")
    
    conn = sqlite3.connect('fragrantica_news.db', timeout=30)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, brand, name FROM randewoo_products WHERE fragrantica_url IS NULL')
    products = cursor.fetchall()
    
    if not products:
        print("✓ Все товары уже имеют Fragrantica URL")
        conn.close()
        return
    
    print(f"Товаров для обработки: {len(products)}\n")
    
    BATCH_SIZE = 10
    BATCH_PAUSE = 5  # Увеличена пауза между пакетами
    
    found = 0
    not_found = 0
    
    total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(0, len(products), BATCH_SIZE):
        batch_products = products[batch_num:batch_num + BATCH_SIZE]
        current_batch = batch_num // BATCH_SIZE + 1
        
        print(f"{'='*80}")
        print(f"ПАКЕТ {current_batch}/{total_batches}")
        print(f"{'='*80}\n")
        
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        # Настраиваем прокси Smartproxy
        scraper.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        brand_cache = {}
        
        for idx_in_batch, (product_id, brand, name) in enumerate(batch_products, 1):
            global_idx = batch_num + idx_in_batch
            
            print(f"[{global_idx}/{len(products)}] {brand} - {name}")
            print(f"  🔍 Ищу на Fragrantica...", end=" ", flush=True)
            
            try:
                fragrantica_url = search_fragrantica(scraper, brand, name, brand_cache)
                
                if fragrantica_url:
                    cursor.execute('UPDATE randewoo_products SET fragrantica_url = ? WHERE id = ?', 
                                 (fragrantica_url, product_id))
                    conn.commit()
                    found += 1
                    print(f"✓ Найдено")
                else:
                    not_found += 1
                    print(f"✗ Не найдено")
                
                time.sleep(2)  # Увеличена пауза между запросами
                
            except Exception as e:
                not_found += 1
                print(f"✗ Ошибка: {e}")
        
        if current_batch < total_batches:
            print(f"\n⏸  Пауза {BATCH_PAUSE} сек...\n")
            time.sleep(BATCH_PAUSE)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"РЕЗУЛЬТАТЫ ПОИСКА:")
    print(f"  Найдено: {found} ({found/len(products)*100:.1f}%)")
    print(f"  Не найдено: {not_found}")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()

