from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from pathlib import Path
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "replace_with_secure_key")

# مسیر دیتابیس
BASE_DIR = Path(__file__).parent.parent
DB_DIR   = BASE_DIR / 'db'
DB_PATH  = DB_DIR / 'database.sqlite'

# اطمینان از وجود پوشه‌ی db
DB_DIR.mkdir(parents=True, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─── ایجاد جدول users در صورت عدم وجود ────────────────────
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER UNIQUE,
            username TEXT,
            subscription TEXT,
            txid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# اجرای init_db در زمان شروع برنامه
init_db()
# ─────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form.get('email','').strip()
        password = request.form.get('password','').strip()
        if (email == os.getenv("ADMIN_EMAIL") 
                and password == os.getenv("ADMIN_PASSWORD")):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = "ایمیل یا رمز عبور اشتباه است."
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn  = get_db()
    users = conn.execute(
        'SELECT uid, username, subscription, txid, created_at '
        'FROM users ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return render_template('dashboard.html', users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    debug = os.getenv("FLASK_DEBUG", "False") == "True"
    app.run(host='0.0.0.0', port=5000, debug=debug)
