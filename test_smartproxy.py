import cloudscraper
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Настройки Smartproxy
SMARTPROXY_HOST = "proxy.smartproxy.net"
SMARTPROXY_PORT = 3120
SMARTPROXY_USER = "smart-qad2gx6xmehj"
SMARTPROXY_PASS = "twYMsn3pEJ4DqZqk"

PROXY_URL = f"http://{SMARTPROXY_USER}:{SMARTPROXY_PASS}@{SMARTPROXY_HOST}:{SMARTPROXY_PORT}"

print("="*80)
print("ТЕСТ SMARTPROXY")
print("="*80 + "\n")

print(f"🌐 Прокси: {SMARTPROXY_HOST}:{SMARTPROXY_PORT}")
print(f"👤 User: {SMARTPROXY_USER}\n")

# Создаем scraper
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)

# Настраиваем прокси
scraper.proxies = {
    'http': PROXY_URL,
    'https': PROXY_URL
}

# Тест 1: Проверка IP
print("Тест 1: Проверка текущего IP")
print("  Запрашиваю https://api.ipify.org...")
try:
    response = scraper.get('https://api.ipify.org', timeout=10)
    print(f"  ✓ Ваш IP через прокси: {response.text}\n")
except Exception as e:
    print(f"  ✗ Ошибка: {e}\n")

# Тест 2: Доступ к Fragrantica
print("Тест 2: Доступ к Fragrantica")
print("  Запрашиваю https://www.fragrantica.ru/designers/Chanel.html...")
try:
    response = scraper.get('https://www.fragrantica.ru/designers/Chanel.html', timeout=10)
    print(f"  ✓ Status code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"  ✓ Размер ответа: {len(response.text)} символов")
        print(f"  ✓ ДОСТУП ЕСТЬ! Fragrantica доступен через прокси!")
    elif response.status_code == 429:
        print(f"  ⚠ Блокировка 429 (Too Many Requests)")
    else:
        print(f"  ⚠ Неожиданный код: {response.status_code}")
        
except Exception as e:
    print(f"  ✗ Ошибка: {e}")

print("\n" + "="*80)
print("ТЕСТ ЗАВЕРШЕН")
print("="*80)

