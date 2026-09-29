import os
import secrets
import sqlite3

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'users.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
KEY_PATH = os.path.join(BASE_DIR, '.secret_key')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB upload limit

# Persist the session key so logins survive Apache restarts
if not os.path.exists(KEY_PATH):
    with open(KEY_PATH, 'w') as f:
        f.write(secrets.token_hex(32))
with open(KEY_PATH) as f:
    app.secret_key = f.read().strip()

os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL,
                            firstname TEXT NOT NULL,
                            lastname TEXT NOT NULL,
                            email TEXT NOT NULL,
                            address TEXT NOT NULL,
                            filename TEXT,
                            wordcount INTEGER)''')


init_db()


def save_upload(username, file):
    """Store an uploaded .txt file and return (stored_name, word_count)."""
    if not file or not file.filename:
        return None, None
    if not file.filename.lower().endswith('.txt'):
        raise ValueError('Please upload a .txt file.')
    stored_name = secure_filename(f'{username}_{file.filename}')
    path = os.path.join(UPLOAD_DIR, stored_name)
    file.save(path)
    with open(path, encoding='utf-8', errors='ignore') as f:
        word_count = len(f.read().split())
    return stored_name, word_count


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('profile'))
    return render_template('register.html', form={})


@app.route('/register', methods=['POST'])
def register():
    form = request.form
    fields = ['username', 'password', 'firstname', 'lastname', 'email', 'address']
    values = {f: form.get(f, '').strip() for f in fields}
    if not all(values.values()):
        flash('All fields are required.', 'error')
        return render_template('register.html', form=values), 400

    with get_db() as conn:
        exists = conn.execute('SELECT 1 FROM users WHERE username = ?',
                              (values['username'],)).fetchone()
    if exists:
        flash('That username is already taken.', 'error')
        return render_template('register.html', form=values), 400

    try:
        filename, wordcount = save_upload(values['username'], request.files.get('file'))
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('register.html', form=values), 400

    with get_db() as conn:
        conn.execute('''INSERT INTO users (username, password, firstname, lastname,
                                           email, address, filename, wordcount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (values['username'], generate_password_hash(values['password']),
                      values['firstname'], values['lastname'], values['email'],
                      values['address'], filename, wordcount))

    session['username'] = values['username']
    flash('Registration successful!', 'success')
    return redirect(url_for('profile'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?',
                                (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash(f'Welcome back, {user["firstname"]}!', 'success')
            return redirect(url_for('profile'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?',
                            (session['username'],)).fetchone()
    if user is None:
        session.clear()
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)


@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        filename, wordcount = save_upload(session['username'], request.files.get('file'))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('profile'))
    if filename:
        with get_db() as conn:
            conn.execute('UPDATE users SET filename = ?, wordcount = ? WHERE username = ?',
                         (filename, wordcount, session['username']))
        flash('File uploaded.', 'success')
    else:
        flash('Please choose a file first.', 'error')
    return redirect(url_for('profile'))


@app.route('/download')
def download():
    if 'username' not in session:
        return redirect(url_for('login'))
    with get_db() as conn:
        user = conn.execute('SELECT filename FROM users WHERE username = ?',
                            (session['username'],)).fetchone()
    if not user or not user['filename']:
        abort(404)
    original = user['filename'].split('_', 1)[-1]
    return send_from_directory(UPLOAD_DIR, user['filename'],
                               as_attachment=True, download_name=original)


@app.errorhandler(413)
def too_large(_):
    flash('File is too large (2 MB max).', 'error')
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
