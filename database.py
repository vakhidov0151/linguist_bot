import sqlite3
import os
from contextlib import contextmanager

# Railway uchun doimiy xotira (Volume) yo'lini Environment Variables orqali berish mumkin
DB_DIR = os.getenv('DB_DIR', os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, 'users.db')

if os.getenv('RAILWAY_ENVIRONMENT') and not os.getenv('DB_DIR'):
    print("⚠️ DIQQAT: DB_DIR o'rnatilmagan — users.db har deployda o'chib ketadi! "
          "Railway Volume ulab, DB_DIR ni uning yo'liga (masalan /data) qo'ying.")


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    with _db() as conn:
        c = conn.cursor()
        # WAL: bir nechta thread bir vaqtda o'qiy/yoza oladi, "database is locked" kamayadi
        c.execute('PRAGMA journal_mode=WAL')
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
            ("interface_lang", "VARCHAR DEFAULT 'uz'"),
            ("target_lang", "VARCHAR DEFAULT 'uz'"),
        ]

        for col_name, col_type in new_columns:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Ustun allaqachon mavjud bo'lsa xato bermaslik uchun


def register_user(user_id):
    """Foydalanuvchini qo'shadi. Yangi bo'lsa True, avvaldan bor bo'lsa False."""
    with _db() as conn:
        cur = conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        return cur.rowcount == 1


def get_voice_balance(user_id):
    with _db() as conn:
        res = conn.execute('SELECT voice_balance FROM users WHERE user_id=?', (user_id,)).fetchone()
    return res[0] if res and res[0] else 0


def add_voice_balance(user_id, amount):
    # Atomar: bir vaqtdagi ikki so'rov bir-birining natijasini yo'qotmaydi
    with _db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        conn.execute('UPDATE users SET voice_balance = COALESCE(voice_balance, 0) + ? WHERE user_id=?',
                     (amount, user_id))


def use_voice_balance(user_id):
    """Balansdan 1 ta yechadi. Yetarli bo'lmasa False (atomar tekshiruv)."""
    with _db() as conn:
        cur = conn.execute('UPDATE users SET voice_balance = voice_balance - 1 '
                           'WHERE user_id=? AND voice_balance > 0', (user_id,))
        return cur.rowcount == 1


def increment_translations(user_id):
    with _db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        conn.execute('UPDATE users SET total_translations = COALESCE(total_translations, 0) + 1 WHERE user_id=?',
                     (user_id,))


def get_user_stats(user_id):
    with _db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        res = conn.execute('SELECT voice_balance, total_translations, referral_count, interface_lang '
                           'FROM users WHERE user_id=?', (user_id,)).fetchone()
    if not res:
        return (0, 0, 0, 'uz')
    bal, trans, refs, ui = res
    return (bal or 0, trans or 0, refs or 0, ui or 'uz')


def set_interface_lang(user_id, lang_code):
    with _db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        conn.execute('UPDATE users SET interface_lang=? WHERE user_id=?', (lang_code, user_id))


def get_interface_lang(user_id):
    # Faqat o'qish — har chaqiruvda yozuv (commit) qilmaymiz
    with _db() as conn:
        res = conn.execute('SELECT interface_lang FROM users WHERE user_id=?', (user_id,)).fetchone()
    return res[0] if res and res[0] else 'uz'


def set_target_lang(user_id, lang_code):
    with _db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        conn.execute('UPDATE users SET target_lang=? WHERE user_id=?', (lang_code, user_id))


def get_target_lang(user_id):
    with _db() as conn:
        res = conn.execute('SELECT target_lang FROM users WHERE user_id=?', (user_id,)).fetchone()
    return res[0] if res and res[0] else 'uz'


def set_referrer(user_id, referrer_id):
    """Referalni bog'laydi. Faqat taklif qiluvchi bazada bor va user hali hech kimga bog'lanmagan bo'lsa."""
    if user_id == referrer_id:
        return False
    with _db() as conn:
        exists = conn.execute('SELECT 1 FROM users WHERE user_id=?', (referrer_id,)).fetchone()
        if not exists:
            return False
        cur = conn.execute('UPDATE users SET referred_by=? WHERE user_id=? AND referred_by IS NULL',
                           (referrer_id, user_id))
        if cur.rowcount != 1:
            return False
        conn.execute('UPDATE users SET referral_count = COALESCE(referral_count, 0) + 1 WHERE user_id=?',
                     (referrer_id,))
        return True


def get_all_users():
    with _db() as conn:
        res = conn.execute('SELECT user_id FROM users').fetchall()
    return [r[0] for r in res]


def get_total_user_count():
    with _db() as conn:
        res = conn.execute('SELECT COUNT(*) FROM users').fetchone()
    return res[0] if res else 0


# Bazani fayl chaqirilganda ishga tushirib yuboramiz
init_db()
