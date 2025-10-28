import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import sys
import io
from openai import OpenAI
import requests
import json
import os
from datetime import datetime

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class PerfumePublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Perfume Publisher - Telegram Bot Manager")
        self.root.geometry("1400x800")
        
        # Переменные
        self.db_path = 'fragrantica_news.db'
        self.selected_row_id = None
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем данные
        self.load_data()
        
        # Загружаем настройки
        self.load_settings()
    
    def create_widgets(self):
        """Создает все виджеты интерфейса"""
        
        # ==============================================================
        # ВЕРХНЯЯ ПАНЕЛЬ - Таблица товаров
        # ==============================================================
        
        table_frame = ttk.LabelFrame(self.root, text="📦 Товары Randewoo", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Кнопки управления таблицей
        buttons_frame = ttk.Frame(table_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(buttons_frame, text="➕ Добавить", command=self.add_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="✏️ Редактировать", command=self.edit_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🗑️ Удалить", command=self.delete_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🔄 Обновить", command=self.load_data).pack(side=tk.LEFT, padx=5)
        
        # Создаем таблицу с прокруткой
        tree_frame = ttk.Frame(table_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(tree_frame, 
                                 columns=("id", "brand", "name", "product_url", "fragrantica_url"),
                                 show="headings",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set,
                                 height=15)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Настройка колонок
        self.tree.heading("id", text="ID")
        self.tree.heading("brand", text="Бренд")
        self.tree.heading("name", text="Название")
        self.tree.heading("product_url", text="URL Randewoo")
        self.tree.heading("fragrantica_url", text="URL Fragrantica")
        
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("brand", width=150)
        self.tree.column("name", width=300)
        self.tree.column("product_url", width=350)
        self.tree.column("fragrantica_url", width=350)
        
        # Размещение
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Привязка события выбора строки
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)
        
        # ==============================================================
        # НИЖНЯЯ ПАНЕЛЬ - Настройки и публикация
        # ==============================================================
        
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        
        # Левая часть - Промпт GPT
        left_frame = ttk.LabelFrame(bottom_frame, text="🤖 Промпт для GPT", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.prompt_text = scrolledtext.ScrolledText(left_frame, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self.prompt_text.pack(fill=tk.BOTH, expand=True)
        
        # Устанавливаем промпт по умолчанию
        default_prompt = """Представь что ты парфюмерный эксперт и копирайтер. 
Напиши короткий пост для Telegram (максимум 900 символов) о парфюме {brand} {name}.

Стиль:
- Разговорный, теплый, от первого лица
- Короткие абзацы (1-2 строки)
- Сенсорные детали (запахи, ассоциации)
- 2-3 эмодзи максимум
- Закончи вопросом или призывом

Пиши ТОЛЬКО на русском языке."""

        self.prompt_text.insert("1.0", default_prompt)
        
        # Правая часть - Настройки и публикация
        right_frame = ttk.Frame(bottom_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        
        # Информация о выбранном товаре
        info_frame = ttk.LabelFrame(right_frame, text="📋 Выбранный товар", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_info_label = ttk.Label(info_frame, text="Выберите товар в таблице", 
                                            font=("Segoe UI", 10), wraplength=300)
        self.selected_info_label.pack()
        
        # Настройки бота
        settings_frame = ttk.LabelFrame(right_frame, text="⚙️ Настройки", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="OpenAI API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.openai_key_entry = ttk.Entry(settings_frame, width=30, show="•")
        self.openai_key_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Telegram Bot Token:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tg_token_entry = ttk.Entry(settings_frame, width=30, show="•")
        self.tg_token_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Telegram Channel ID:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.tg_channel_entry = ttk.Entry(settings_frame, width=30)
        self.tg_channel_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(settings_frame, text="💾 Сохранить настройки", 
                  command=self.save_settings).grid(row=3, column=0, columnspan=2, pady=10)
        
        # Кнопка публикации
        publish_frame = ttk.Frame(right_frame)
        publish_frame.pack(fill=tk.X)
        
        self.publish_button = ttk.Button(publish_frame, text="📤 ОПУБЛИКОВАТЬ В TELEGRAM", 
                                         command=self.publish_to_telegram, 
                                         style="Accent.TButton")
        self.publish_button.pack(fill=tk.X, ipady=15)
    
    def load_data(self):
        """Загружает данные из БД в таблицу"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Загружаем из БД
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, brand, name, product_url, fragrantica_url 
                FROM randewoo_products 
                ORDER BY id DESC
            ''')
            
            rows = cursor.fetchall()
            
            for row in rows:
                self.tree.insert("", tk.END, values=row)
            
            conn.close()
            
            self.root.title(f"Perfume Publisher - {len(rows)} товаров")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные:\n{e}")
    
    def load_settings(self):
        """Загружает настройки из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # OpenAI API Key
            cursor.execute('SELECT value FROM config WHERE key = ?', ('openai_api_key',))
            result = cursor.fetchone()
            if result:
                self.openai_key_entry.insert(0, result[0])
            
            # Telegram Bot Token
            cursor.execute('SELECT value FROM config WHERE key = ?', ('telegram_bot_token',))
            result = cursor.fetchone()
            if result:
                self.tg_token_entry.insert(0, result[0])
            
            # Telegram Channel ID
            cursor.execute('SELECT value FROM config WHERE key = ?', ('telegram_channel_id',))
            result = cursor.fetchone()
            if result:
                self.tg_channel_entry.insert(0, result[0])
            
            conn.close()
            
        except Exception as e:
            print(f"Не удалось загрузить настройки: {e}")
    
    def save_settings(self):
        """Сохраняет настройки в БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу config если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Сохраняем настройки
            settings = [
                ('openai_api_key', self.openai_key_entry.get()),
                ('telegram_bot_token', self.tg_token_entry.get()),
                ('telegram_channel_id', self.tg_channel_entry.get())
            ]
            
            for key, value in settings:
                cursor.execute('''
                    INSERT OR REPLACE INTO config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Успех", "Настройки сохранены!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{e}")
    
    def on_row_select(self, event):
        """Обработчик выбора строки в таблице"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item['values']
            
            self.selected_row_id = values[0]
            brand = values[1]
            name = values[2]
            
            self.selected_info_label.config(
                text=f"✓ Выбрано:\n{brand} - {name}\n(ID: {self.selected_row_id})"
            )
    
    def add_row(self):
        """Добавляет новую строку в таблицу"""
        dialog = AddEditDialog(self.root, "Добавить товар")
        if dialog.result:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO randewoo_products (brand, name, product_url, fragrantica_url, parsed_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (dialog.result['brand'], dialog.result['name'], 
                      dialog.result['product_url'], dialog.result['fragrantica_url']))
                
                conn.commit()
                conn.close()
                
                self.load_data()
                messagebox.showinfo("Успех", "Товар добавлен!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить товар:\n{e}")
    
    def edit_row(self):
        """Редактирует выбранную строку"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите товар для редактирования")
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        dialog = AddEditDialog(self.root, "Редактировать товар", {
            'id': values[0],
            'brand': values[1],
            'name': values[2],
            'product_url': values[3],
            'fragrantica_url': values[4]
        })
        
        if dialog.result:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE randewoo_products 
                    SET brand = ?, name = ?, product_url = ?, fragrantica_url = ?
                    WHERE id = ?
                ''', (dialog.result['brand'], dialog.result['name'], 
                      dialog.result['product_url'], dialog.result['fragrantica_url'],
                      values[0]))
                
                conn.commit()
                conn.close()
                
                self.load_data()
                messagebox.showinfo("Успех", "Товар обновлен!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось обновить товар:\n{e}")
    
    def delete_row(self):
        """Удаляет выбранную строку"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите товар для удаления")
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        if messagebox.askyesno("Подтверждение", 
                              f"Удалить товар:\n{values[1]} - {values[2]}?"):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM randewoo_products WHERE id = ?', (values[0],))
                
                conn.commit()
                conn.close()
                
                self.load_data()
                messagebox.showinfo("Успех", "Товар удален!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить товар:\n{e}")
    
    def publish_to_telegram(self):
        """Публикует выбранный товар в Telegram"""
        if not self.selected_row_id:
            messagebox.showwarning("Предупреждение", "Выберите товар для публикации")
            return
        
        # Проверяем настройки
        openai_key = self.openai_key_entry.get()
        tg_token = self.tg_token_entry.get()
        tg_channel = self.tg_channel_entry.get()
        
        if not openai_key:
            messagebox.showerror("Ошибка", "Укажите OpenAI API Key в настройках")
            return
        
        if not tg_token:
            messagebox.showerror("Ошибка", "Укажите Telegram Bot Token в настройках")
            return
        
        if not tg_channel:
            messagebox.showerror("Ошибка", "Укажите Telegram Channel ID в настройках")
            return
        
        # Получаем данные товара
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT brand, name, product_url, fragrantica_url 
                FROM randewoo_products 
                WHERE id = ?
            ''', (self.selected_row_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                messagebox.showerror("Ошибка", "Товар не найден в БД")
                return
            
            brand, name, product_url, fragrantica_url = row
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить данные товара:\n{e}")
            return
        
        # Формируем промпт
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        prompt = prompt.replace("{brand}", brand).replace("{name}", name)
        
        # Создаем окно прогресса
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Публикация...")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        status_label = ttk.Label(progress_window, text="🤖 Генерирую текст через GPT...", 
                                font=("Segoe UI", 10))
        status_label.pack(pady=20)
        
        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(fill=tk.X, padx=20)
        progress.start()
        
        def do_publish():
            try:
                # Шаг 1: GPT
                status_label.config(text="🤖 Генерирую текст через GPT...")
                progress_window.update()
                
                text_to_rewrite = f"Бренд: {brand}\nНазвание: {name}\nURL: {product_url}"
                if fragrantica_url:
                    text_to_rewrite += f"\nFragrantica: {fragrantica_url}"
                
                client = OpenAI(api_key=openai_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text_to_rewrite}
                    ],
                    temperature=0.7
                )
                
                rewritten_text = response.choices[0].message.content
                
                # Шаг 2: Telegram
                status_label.config(text="📤 Отправляю в Telegram...")
                progress_window.update()
                
                url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                
                # Добавляем ссылки в конец
                footer = f"\n\n🔗 Randewoo: {product_url}"
                if fragrantica_url:
                    footer += f"\n🌸 Fragrantica: {fragrantica_url}"
                
                full_text = rewritten_text + footer
                
                # Проверяем длину
                if len(full_text) > 4096:
                    full_text = full_text[:4093] + "..."
                
                response = requests.post(url, json={
                    "chat_id": tg_channel,
                    "text": full_text,
                    "disable_web_page_preview": False
                }, timeout=30)
                
                result = response.json()
                
                progress.stop()
                progress_window.destroy()
                
                if result.get('ok'):
                    messagebox.showinfo("Успех", 
                                      f"✅ Пост опубликован!\n\n"
                                      f"Длина текста: {len(full_text)} символов\n"
                                      f"Message ID: {result['result']['message_id']}")
                else:
                    error_desc = result.get('description', 'Unknown error')
                    messagebox.showerror("Ошибка Telegram", f"Не удалось опубликовать:\n{error_desc}")
                
            except Exception as e:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Произошла ошибка:\n{str(e)[:500]}")
        
        # Запускаем публикацию в отдельном потоке (для UI responsiveness)
        import threading
        thread = threading.Thread(target=do_publish)
        thread.start()


class AddEditDialog:
    """Диалог для добавления/редактирования товара"""
    
    def __init__(self, parent, title, initial_values=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Поля
        fields_frame = ttk.Frame(self.dialog, padding=20)
        fields_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(fields_frame, text="Бренд:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.brand_entry = ttk.Entry(fields_frame, width=50)
        self.brand_entry.grid(row=0, column=1, pady=10, padx=10)
        
        ttk.Label(fields_frame, text="Название:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.name_entry = ttk.Entry(fields_frame, width=50)
        self.name_entry.grid(row=1, column=1, pady=10, padx=10)
        
        ttk.Label(fields_frame, text="URL Randewoo:").grid(row=2, column=0, sticky=tk.W, pady=10)
        self.product_url_entry = ttk.Entry(fields_frame, width=50)
        self.product_url_entry.grid(row=2, column=1, pady=10, padx=10)
        
        ttk.Label(fields_frame, text="URL Fragrantica:").grid(row=3, column=0, sticky=tk.W, pady=10)
        self.fragrantica_url_entry = ttk.Entry(fields_frame, width=50)
        self.fragrantica_url_entry.grid(row=3, column=1, pady=10, padx=10)
        
        # Заполняем начальные значения если есть
        if initial_values:
            self.brand_entry.insert(0, initial_values.get('brand', ''))
            self.name_entry.insert(0, initial_values.get('name', ''))
            self.product_url_entry.insert(0, initial_values.get('product_url', ''))
            self.fragrantica_url_entry.insert(0, initial_values.get('fragrantica_url', ''))
        
        # Кнопки
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(buttons_frame, text="💾 Сохранить", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="❌ Отмена", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Центрируем окно
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f'+{x}+{y}')
        
        self.dialog.wait_window()
    
    def save(self):
        """Сохраняет данные и закрывает диалог"""
        brand = self.brand_entry.get().strip()
        name = self.name_entry.get().strip()
        product_url = self.product_url_entry.get().strip()
        fragrantica_url = self.fragrantica_url_entry.get().strip()
        
        if not brand or not name:
            messagebox.showwarning("Предупреждение", "Заполните бренд и название")
            return
        
        self.result = {
            'brand': brand,
            'name': name,
            'product_url': product_url,
            'fragrantica_url': fragrantica_url
        }
        
        self.dialog.destroy()


def main():
    root = tk.Tk()
    
    # Настраиваем стиль (опционально)
    try:
        from ttkbootstrap import Style
        style = Style(theme='cosmo')
    except ImportError:
        # Если ttkbootstrap не установлен, используем стандартный стиль
        pass
    
    app = PerfumePublisherApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

