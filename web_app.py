from flask import Flask, render_template, request, jsonify
import sqlite3
from openai import OpenAI
import requests
import json
import os
from datetime import datetime
import threading

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

DB_PATH = 'fragrantica_news.db'

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Создает подключение к БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_config(key):
    """Получает конфигурационный параметр из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result['value'] if result else None

def save_config(key, value):
    """Сохраняет конфигурационный параметр в БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Создаем таблицу config если её нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        INSERT OR REPLACE INTO config (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (key, value))
    
    conn.commit()
    conn.close()

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/products')
def get_products():
    """Получить список всех товаров"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, brand, name, product_url, fragrantica_url, parsed_at
            FROM randewoo_products
            ORDER BY id DESC
        ''')
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row['id'],
                'brand': row['brand'],
                'name': row['name'],
                'product_url': row['product_url'],
                'fragrantica_url': row['fragrantica_url'],
                'parsed_at': row['parsed_at']
            })
        
        conn.close()
        
        return jsonify({'success': True, 'products': products})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>')
def get_product(product_id):
    """Получить конкретный товар"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, brand, name, product_url, fragrantica_url
            FROM randewoo_products
            WHERE id = ?
        ''', (product_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            product = {
                'id': row['id'],
                'brand': row['brand'],
                'name': row['name'],
                'product_url': row['product_url'],
                'fragrantica_url': row['fragrantica_url']
            }
            return jsonify({'success': True, 'product': product})
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    """Добавить новый товар"""
    try:
        data = request.json
        
        brand = data.get('brand', '').strip()
        name = data.get('name', '').strip()
        product_url = data.get('product_url', '').strip()
        fragrantica_url = data.get('fragrantica_url', '').strip()
        
        if not brand or not name:
            return jsonify({'success': False, 'error': 'Brand and name are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO randewoo_products (brand, name, product_url, fragrantica_url, parsed_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (brand, name, product_url, fragrantica_url))
        
        product_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': product_id, 'message': 'Product added successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Обновить товар"""
    try:
        data = request.json
        
        brand = data.get('brand', '').strip()
        name = data.get('name', '').strip()
        product_url = data.get('product_url', '').strip()
        fragrantica_url = data.get('fragrantica_url', '').strip()
        
        if not brand or not name:
            return jsonify({'success': False, 'error': 'Brand and name are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE randewoo_products
            SET brand = ?, name = ?, product_url = ?, fragrantica_url = ?
            WHERE id = ?
        ''', (brand, name, product_url, fragrantica_url, product_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Product updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Удалить товар"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM randewoo_products WHERE id = ?', (product_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Product deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings')
def get_settings():
    """Получить настройки"""
    try:
        settings = {
            'openai_key': get_config('openai_api_key') or '',
            'telegram_token': get_config('telegram_bot_token') or '',
            'telegram_channel': get_config('telegram_channel_id') or ''
        }
        
        return jsonify({'success': True, 'settings': settings})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Сохранить настройки"""
    try:
        data = request.json
        
        save_config('openai_api_key', data.get('openai_key', ''))
        save_config('telegram_bot_token', data.get('telegram_token', ''))
        save_config('telegram_channel_id', data.get('telegram_channel', ''))
        
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/publish', methods=['POST'])
def publish():
    """Опубликовать товар в Telegram"""
    try:
        data = request.json
        
        product_id = data.get('product_id')
        prompt_template = data.get('prompt', '')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400
        
        # Получаем товар
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT brand, name, product_url, fragrantica_url
            FROM randewoo_products
            WHERE id = ?
        ''', (product_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        brand = row['brand']
        name = row['name']
        product_url = row['product_url']
        fragrantica_url = row['fragrantica_url']
        
        # Получаем настройки
        openai_key = get_config('openai_api_key')
        tg_token = get_config('telegram_bot_token')
        tg_channel = get_config('telegram_channel_id')
        
        if not openai_key:
            return jsonify({'success': False, 'error': 'OpenAI API Key not configured'}), 400
        
        if not tg_token:
            return jsonify({'success': False, 'error': 'Telegram Bot Token not configured'}), 400
        
        if not tg_channel:
            return jsonify({'success': False, 'error': 'Telegram Channel ID not configured'}), 400
        
        # Формируем промпт
        prompt = prompt_template.replace('{brand}', brand).replace('{name}', name)
        
        # Генерируем текст через GPT
        try:
            client = OpenAI(api_key=openai_key)
            
            text_to_rewrite = f"Бренд: {brand}\nНазвание: {name}"
            if product_url:
                text_to_rewrite += f"\nURL: {product_url}"
            if fragrantica_url:
                text_to_rewrite += f"\nFragrantica: {fragrantica_url}"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text_to_rewrite}
                ],
                temperature=0.7
            )
            
            rewritten_text = response.choices[0].message.content
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'GPT Error: {str(e)}'}), 500
        
        # Добавляем ссылки
        footer = ""
        if product_url:
            footer += f"\n\n🔗 Randewoo: {product_url}"
        if fragrantica_url:
            footer += f"\n🌸 Fragrantica: {fragrantica_url}"
        
        full_text = rewritten_text + footer
        
        # Проверяем длину
        if len(full_text) > 4096:
            full_text = full_text[:4093] + "..."
        
        # Публикуем в Telegram
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            
            response = requests.post(url, json={
                "chat_id": tg_channel,
                "text": full_text,
                "disable_web_page_preview": False
            }, timeout=30)
            
            result = response.json()
            
            if result.get('ok'):
                message_id = result['result']['message_id']
                return jsonify({
                    'success': True,
                    'message': 'Published successfully!',
                    'message_id': message_id,
                    'text_length': len(full_text)
                })
            else:
                error_desc = result.get('description', 'Unknown error')
                return jsonify({'success': False, 'error': f'Telegram Error: {error_desc}'}), 500
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'Telegram Error: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("="*80)
    print("🌸 PERFUME PUBLISHER WEB APP")
    print("="*80)
    print("\n✨ Starting server...")
    print("📍 Open in browser: http://localhost:5000")
    print("\n⚠️  Press CTRL+C to stop\n")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

