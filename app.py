from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me_123456789"

DB = "app_data.db"

# ----------------- قاعدة البيانات -----------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """إنشاء الجداول إذا مش موجودة"""
    conn = get_db()
    c = conn.cursor()

    # جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # جدول الحضور والمغادرة
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            check_in TEXT,
            check_out TEXT,
            date TEXT NOT NULL,
            hours REAL DEFAULT 0,
            location TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------- إضافة مستخدمين افتراضيين -----------------
def seed_default_users():
    default_users = [
        {"id": "5002", "username": "ahmad", "password": "2203"},
        {"id": "5003", "username": "mohammad_wesam", "password": "5042"},
        {"id": "5011", "username": "mohammad_ismail", "password": "9334"},
        {"id": "5008", "username": "omar", "password": "6454"},
        {"id": "5015", "username": "bashar", "password": "7505"},
        {"id": "5020", "username": "ashraf", "password": "8706"},
        {"id": "5021", "username": "maher", "password": "4308"},
        {"id": "5013", "username": "yamin", "password": "9209"},
        {"id": "5006", "username": "amjad", "password": "0661"},
        {"id": "5019", "username": "basel", "password": "1512"},
        {"id": "5007", "username": "rafiq", "password": "1889"},
        {"id": "002", "username": "yara", "password": "2006"},
        {"id": "003", "username": "user", "password": "3332"},
        {"id": "0001", "username": "khaleel", "password": "2026"},

    ]

    conn = get_db()
    c = conn.cursor()
    for user in default_users:
        c.execute(""" 
            INSERT OR IGNORE INTO users (id, username, password)
            VALUES (?, ?, ?)
        """, (user["id"], user["username"], user["password"]))
    conn.commit()
    conn.close()

seed_default_users()

# ----------------- تعريف الإدمن -----------------
def is_admin():

    return 'username' in session and session['username'].lower() == "khaleel"

# ----------------- صفحة تسجيل الدخول -----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']

            if is_admin():
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('att'))
        else:
            return render_template('login.html', error="اسم المستخدم أو كلمة المرور غلط")

    return render_template('login.html')

# ----------------- صفحة تسجيل الحضور والمغادرة -----------------
@app.route('/att', methods=['GET', 'POST'])
def att():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session['username']
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    record = conn.execute(
        "SELECT * FROM attendance WHERE user_id = ? AND date = ?",
        (user_id, today)
    ).fetchone()

    message = ""

    if request.method == 'POST':
        action = request.form['action']
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        location = request.form.get('location', '').strip()
        
        if action == 'check_in':
            if record and record['check_in']:
                message = "لقد سجلت حضورك اليوم بالفعل"
            else:
                conn.execute(
                    "INSERT INTO attendance (user_id, check_in, date, location) VALUES (?, ?, ?, ?)",
                    (user_id, now, today, location)
                )
                conn.commit()
                message = f"{username} سجلت حضورك بنجاح"

        elif action == 'check_out':
            if not record or not record['check_in']:
                message = "لم تسجل حضورك اليوم بعد"
            elif record['check_out']:
                message = "لقد سجلت المغادرة بالفعل"
            else:
                check_in_time = datetime.strptime(record['check_in'], "%Y-%m-%d %H:%M:%S")
                hours_worked = round((datetime.now() - check_in_time).total_seconds() / 3600, 2)

                conn.execute(
                    "UPDATE attendance SET check_out = ?, hours = ?, location = ? WHERE id = ?",
                    (now, hours_worked, location, record['id'])
                )
                conn.commit()
                message = f"{username} سجلت مغادرتك بنجاح. عدد الساعات: {hours_worked} ساعة"

    conn.close()
    return render_template('att.html', username=username, message=message)

# ----------------- صفحة الإدمن -----------------
@app.route('/admin')
def admin():
    if not is_admin():
        return redirect(url_for('login'))

    conn = get_db()
    records = conn.execute('''
        SELECT u.username,
        a.check_in,
        a.check_out,
        a.date,
        a.hours,
        a.location
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.date DESC, a.check_in DESC
    ''').fetchall()
    conn.close()

    return render_template('admin.html', records=records)

# ----------------- حذف كل سجلات الحضور -----------------
@app.route('/delete_all', methods=['POST'])
def delete_all():
    if not is_admin():
        return redirect(url_for('login'))

    conn = get_db()
    conn.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# ----------------- تسجيل الخروج -----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------- تشغيل التطبيق -----------------
if __name__ == '__main__':
    app.run(debug=True)