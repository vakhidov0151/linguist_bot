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
    conn.commit()
    conn.close()

def get_voice_balance(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT voice_balance FROM users WHERE user_id=?', (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0

def add_voice_balance(user_id, amount):
    balance = get_voice_balance(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, voice_balance) VALUES (?, ?)', (user_id, balance + amount))
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

# Bazani fayl chaqirilganda ishga tushirib yuboramiz
init_db()
