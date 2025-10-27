import cloudscraper
from bs4 import BeautifulSoup
import sys
import io
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Создаем scraper с дополнительными параметрами
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    },
    delay=10  # Добавляем задержку
)

# Дополнительные заголовки
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

url = 'https://randewoo.ru/category/parfyumeriya'

print(f"Загружаю URL: {url}")
print("Ждем 5 секунд...")
time.sleep(5)

try:
    response = scraper.get(url, headers=headers, timeout=30)
    print(f"\nStatus code: {response.status_code}")
    print(f"Response length: {len(response.text)} bytes")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Ищем товары
    products = soup.find_all('li', class_='products__item')
    print(f"\nНайдено товаров: {len(products)}")
    
    if products:
        print("\nПервые 3 товара:")
        for i, product in enumerate(products[:3], 1):
            brand_div = product.find('div', class_='b-catalogItem__brand')
            name_div = product.find('div', class_='b-catalogItem__name')
            
            if brand_div and name_div:
                print(f"{i}. {brand_div.get_text(strip=True)} - {name_div.get_text(strip=True)}")
    else:
        print("\n⚠ Товары не найдены!")
        
        # Ищем признаки блокировки/капчи
        if 'captcha' in response.text.lower():
            print("❌ ОБНАРУЖЕНА КАПЧА!")
        if 'access denied' in response.text.lower():
            print("❌ ДОСТУП ЗАБЛОКИРОВАН!")
        if 'cloudflare' in response.text.lower():
            print("⚠  Обнаружена защита Cloudflare")
        
        # Сохраним ответ для анализа
        with open('randewoo_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\n💾 Ответ сохранен в randewoo_response.html")
        
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

