import os
import sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'app.db')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    if not os.path.exists(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        db = sqlite3.connect(DB_PATH)
        c = db.cursor()
        c.execute(
            """CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );"""
        )
        c.execute(
            """CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                done INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );"""
        )
        db.commit()
        db.close()


init_db()


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cur = db.execute(
        'SELECT id, title, description, done FROM assignments WHERE user_id=?',
        (session['user_id'],)
    )
    assignments = cur.fetchall()
    return render_template('dashboard.html', assignments=assignments)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already taken.')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username=?', (username,)
        ).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        flash('Invalid credentials.')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/add', methods=['GET', 'POST'])
def add_assignment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        db = get_db()
        db.execute(
            'INSERT INTO assignments (user_id, title, description) VALUES (?, ?, ?)',
            (session['user_id'], title, description)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('add_assignment.html')


@app.route('/done/<int:assignment_id>')
def mark_done(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute(
        'UPDATE assignments SET done=1 WHERE id=? AND user_id=?',
        (assignment_id, session['user_id'])
    )
    db.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)

