from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'SNEHA_ULTIMATE_FINAL_KEY'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database Init
with get_db_connection() as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT, amount REAL, category TEXT, date TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS category_budgets (user_id INTEGER, month TEXT, category TEXT, amount REAL, PRIMARY KEY (user_id, month, category))')

@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    year = datetime.now().strftime('%Y')
    month_val = datetime.now().strftime('%Y-%m')
    
    total = conn.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date LIKE ?", (session['user_id'], f"{month_val}%")).fetchone()[0] or 0
    recent = conn.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 3", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('dashboard.html', total=total, year=year, recent=recent)

@app.route('/budget-status')
def budget_status():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    
    # Get month from URL parameters, default to current month
    month_name = request.args.get('month', datetime.now().strftime('%B'))
    
    # Map month name to YYYY-MM for the SQL query
    months_map = {
        "January": "01", "February": "02", "March": "03", "April": "04", "May": "05", "June": "06",
        "July": "07", "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"
    }
    month_val = f"{datetime.now().year}-{months_map[month_name]}"
    
    data = conn.execute('''
        SELECT b.category, b.amount as budget, IFNULL(SUM(e.amount), 0) as spent 
        FROM category_budgets b 
        LEFT JOIN expenses e ON b.category = e.category AND b.user_id = e.user_id AND e.date LIKE ?
        WHERE b.user_id = ? AND b.month = ?
        GROUP BY b.category''', (f"{month_val}%", session['user_id'], month_name)).fetchall()
    
    total_spent = sum(item['spent'] for item in data)
    conn.close()
    return render_template('budget_status.html', data=data, month=month_name.upper(), total=total_spent)

# Other routes (Add, Set-Budget, History, Login, etc.)
@app.route('/set-budget', methods=['GET', 'POST'])
def set_budget():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        month = request.form['month']
        cat = request.form['category']
        amt = request.form['amount']
        with get_db_connection() as conn:
            conn.execute('INSERT OR REPLACE INTO category_budgets (user_id, month, category, amount) VALUES (?, ?, ?, ?)', (session['user_id'], month, cat, amt))
        return redirect(url_for('budget_status', month=month))
    return render_template('set_budget.html')

@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        with get_db_connection() as conn:
            conn.execute('INSERT INTO expenses (user_id, title, amount, category, date) VALUES (?, ?, ?, ?, ?)',
                         (session['user_id'], request.form['title'], request.form['amount'], request.form['category'], request.form['date']))
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/history')
def history():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    expenses = conn.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('history.html', expenses=expenses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (request.form['username'],)).fetchone()
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (request.form['username'], generate_password_hash(request.form['password'])))
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    with get_db_connection() as conn:
        conn.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (id, session['user_id']))
    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(debug=True)