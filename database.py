import sqlite3
import os

# Railway uchun doimiy xotira (Volume) yo'lini Environment Variables orqali berish mumkin
DB_DIR = os.getenv('DB_DIR', os.path.dirname(__file__))
DB_PATH = os.path.join(DB_DIR, 'users.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            voice_balance INTEGER DEFAULT 0
        )
    ''')
    
    # Xavfsiz tarzda yangi ustunlarni qo'shamiz (eski ma'lumotlar o'chib ketmaydi)
    new_columns = [
        ("total_translations", "INTEGER DEFAULT 0"),
        ("referred_by", "INTEGER DEFAULT NULL"),
        ("referral_count", "INTEGER DEFAULT 0"),
        ("interface_lang", "VARCHAR DEFAULT 'uz'")
    ]
    
    for col_name, col_type in new_columns:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass # Ustun allaqachon mavjud bo'lsa xato bermaslik uchun
            
    conn.commit()
    conn.close()

def register_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_voice_balance(user_id):
    register_user(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT voice_balance FROM users WHERE user_id=?', (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0

def add_voice_balance(user_id, amount):
    register_user(user_id)
    balance = get_voice_balance(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET voice_balance=? WHERE user_id=?', (balance + amount, user_id))
    conn.commit()
    conn.close()

def use_voice_balance(user_id):
    balance = get_voice_balance(user_id)
    if balance > 0:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET voice_balance=? WHERE user_id=?', (balance - 1, user_id))
        conn.commit()
        conn.close()
        return True
    return False

def increment_translations(user_id):
    register_user(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET total_translations = total_translations + 1 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    register_user(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT voice_balance, total_translations, referral_count, interface_lang FROM users WHERE user_id=?', (user_id,))
    res = c.fetchone()
    conn.close()
    return res if res else (0, 0, 0, 'uz')

def set_interface_lang(user_id, lang_code):
    register_user(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET interface_lang=? WHERE user_id=?', (lang_code, user_id))
    conn.commit()
    conn.close()

def get_interface_lang(user_id):
    register_user(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT interface_lang FROM users WHERE user_id=?', (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res and res[0] else 'uz'

def set_referrer(user_id, referrer_id):
    register_user(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Faqat birinchi marta kiritish mumkin
    c.execute('SELECT referred_by FROM users WHERE user_id=?', (user_id,))
    res = c.fetchone()
    if not res or res[0] is None:
        c.execute('UPDATE users SET referred_by=? WHERE user_id=?', (referrer_id, user_id))
        c.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?', (referrer_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    res = c.fetchall()
    conn.close()
    return [r[0] for r in res]

def get_total_user_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0

# Bazani fayl chaqirilganda ishga tushirib yuboramiz
init_db()
