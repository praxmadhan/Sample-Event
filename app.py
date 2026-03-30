"""
Smart College Event Management System
--------------------------------------
Full-stack Flask application for managing college events.
Features: Authentication, Event CRUD, Registration, Payments,
Email notifications, Excel export, Analytics dashboard.
"""

import os
import uuid
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import qrcode
from PIL import Image

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# App Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload size

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mail Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', '')

# Initialize Flask-Mail (graceful fallback if not configured)
try:
    from flask_mail import Mail, Message as MailMessage
    mail = Mail(app)
    MAIL_ENABLED = True
except ImportError:
    MAIL_ENABLED = False
    print("[!] Flask-Mail not installed. Email features will be simulated.")

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def allowed_file(filename):
    """Check if uploaded file has an allowed extension (jpg, jpeg, png)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all database tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    # Users table – stores students and admins
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'student',
        department TEXT DEFAULT '',
        batch TEXT DEFAULT '',
        college_name TEXT DEFAULT ''
    )''')

    # Events table – stores all event details
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT NOT NULL,
        description TEXT,
        date TEXT,
        time TEXT,
        venue TEXT,
        poster TEXT,
        limit_enabled INTEGER DEFAULT 0,
        max_participants INTEGER,
        is_paid INTEGER DEFAULT 0,
        price INTEGER,
        upi_id TEXT,
        payment_qr TEXT
    )''')

    # Registrations table – tracks which students registered for which events
    c.execute('''CREATE TABLE IF NOT EXISTS registrations (
        reg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_id INTEGER NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (event_id) REFERENCES events(event_id)
    )''')

    # Migrate existing users table – add new columns if missing
    try:
        c.execute('ALTER TABLE users ADD COLUMN department TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE users ADD COLUMN batch TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE users ADD COLUMN college_name TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    # Password resets table – stores reset tokens with expiry
    c.execute('''CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        token TEXT NOT NULL,
        expiry_time TEXT NOT NULL
    )''')

    conn.commit()
    conn.close()


def send_email(to, subject, body):
    """Send email using Flask-Mail. Falls back to console logging if not configured."""
    if not MAIL_ENABLED or not app.config['MAIL_USERNAME']:
        print(f"[EMAIL] (simulated) to {to}")
        print(f"   Subject: {subject}")
        return False
    try:
        msg = MailMessage(subject=subject, recipients=[to], html=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[ERROR] Email error: {e}")
        return False


def generate_upi_qr(upi_id, payee_name, amount, event_id):
    """Auto-generate a UPI QR code image from UPI ID and save to static/images."""
    # UPI deep link format
    upi_url = f"upi://pay?pa={upi_id}&pn={payee_name}&am={amount}&cu=INR&tn=Event_Registration_{event_id}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1e293b", back_color="white").convert('RGB')

    # Save to static/images
    filename = f"upi_qr_{event_id}_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(filepath)
    return filename


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Route Protection Decorators
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def login_required(f):
    """Decorator: Require student/admin login to access route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: Require admin login to access route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Context Processor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.context_processor
def inject_user():
    """Inject user session info into all templates automatically."""
    if 'user_id' in session:
        return {
            'logged_in': True,
            'user_name': session.get('user_name', ''),
            'user_role': session.get('role', 'student')
        }
    return {'logged_in': False, 'user_name': '', 'user_role': ''}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Home Page
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/')
def index():
    """Landing page – shows all upcoming events."""
    conn = get_db()
    events = conn.execute('SELECT * FROM events ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('index.html', events=events)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Student Authentication
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Student registration page."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        department = request.form.get('department', '').strip()
        batch = request.form.get('batch', '').strip()
        college_name = request.form.get('college_name', '').strip()

        # Validate required fields
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('signup'))

        # Check for duplicate email
        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

        if existing:
            flash('Email already registered.', 'danger')
            conn.close()
            return redirect(url_for('signup'))

        # Create account with hashed password
        hashed = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (name, email, password, role, department, batch, college_name) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (name, email, hashed, 'student', department, batch, college_name)
        )
        conn.commit()
        conn.close()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Student login page."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND role = ?',
            (email, 'student')
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['role'] = 'student'
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('events'))

        flash('Invalid email or password.', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Admin Authentication
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    """Admin registration page – requires admin registration code."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        admin_code = request.form.get('admin_code', '')

        # Verify admin registration code
        if admin_code != 'ADMIN2024':
            flash('Invalid admin registration code.', 'danger')
            return redirect(url_for('admin_signup'))

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_signup'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin_signup'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('admin_signup'))

        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

        if existing:
            flash('Email already registered.', 'danger')
            conn.close()
            return redirect(url_for('admin_signup'))

        hashed = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
            (name, email, hashed, 'admin')
        )
        conn.commit()
        conn.close()

        flash('Admin account created! Please login.', 'success')
        return redirect(url_for('admin_login'))

    return render_template('admin_signup.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND role = ?',
            (email, 'admin')
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['role'] = 'admin'
            flash(f'Welcome, Admin {user["name"]}!', 'success')
            return redirect(url_for('admin_dashboard'))

        flash('Invalid admin credentials.', 'danger')
        return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


@app.route('/logout')
def logout():
    """Clear session and logout."""
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Events – Browse & View
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/events')
def events():
    """Browse all events with registration status."""
    conn = get_db()
    all_events = conn.execute('SELECT * FROM events ORDER BY date DESC').fetchall()

    # Build registration counts and track which events the user has registered for
    event_reg_counts = {}
    registered_events = set()
    reg_statuses = {}  # Track payment status per event for current user

    for event in all_events:
        count = conn.execute(
            'SELECT COUNT(*) as cnt FROM registrations WHERE event_id = ?',
            (event['event_id'],)
        ).fetchone()['cnt']
        event_reg_counts[event['event_id']] = count

        # Check if current logged-in user is registered
        if 'user_id' in session:
            reg = conn.execute(
                'SELECT reg_id, payment_status FROM registrations WHERE user_id = ? AND event_id = ?',
                (session['user_id'], event['event_id'])
            ).fetchone()
            if reg:
                registered_events.add(event['event_id'])
                reg_statuses[event['event_id']] = reg['payment_status']

    conn.close()
    return render_template(
        'events.html',
        events=all_events,
        reg_counts=event_reg_counts,
        registered=registered_events,
        reg_statuses=reg_statuses
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Registration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/register-event/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    """Register the currently logged-in student for an event."""
    conn = get_db()

    # Prevent duplicate registration
    existing = conn.execute(
        'SELECT reg_id FROM registrations WHERE user_id = ? AND event_id = ?',
        (session['user_id'], event_id)
    ).fetchone()
    if existing:
        flash('You are already registered for this event.', 'warning')
        conn.close()
        return redirect(url_for('events'))

    # Verify event exists
    event = conn.execute(
        'SELECT * FROM events WHERE event_id = ?', (event_id,)
    ).fetchone()
    if not event:
        flash('Event not found.', 'danger')
        conn.close()
        return redirect(url_for('events'))

    # Enforce participant limit
    if event['limit_enabled']:
        count = conn.execute(
            'SELECT COUNT(*) as cnt FROM registrations WHERE event_id = ?',
            (event_id,)
        ).fetchone()['cnt']
        if count >= event['max_participants']:
            flash('Registration is full for this event.', 'danger')
            conn.close()
            return redirect(url_for('events'))

    # For paid events, require payment confirmation checkbox
    # Payment will be PENDING until admin verifies
    payment_status = 'not_required'
    if event['is_paid']:
        payment_confirmed = request.form.get('payment_confirmed')
        if not payment_confirmed:
            flash('Please confirm payment before registering.', 'danger')
            conn.close()
            return redirect(url_for('events'))
        payment_status = 'pending'  # Admin must verify before confirmed

    # Insert registration record
    conn.execute(
        'INSERT INTO registrations (user_id, event_id, payment_status) VALUES (?, ?, ?)',
        (session['user_id'], event_id, payment_status)
    )
    conn.commit()

    # Send confirmation email
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    email_body = f"""
    <div style="font-family:'Inter',sans-serif;max-width:600px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#4f46e5,#06b6d4);padding:30px;border-radius:12px 12px 0 0;">
            <h2 style="color:white;margin:0;">🎉 Registration Confirmed!</h2>
        </div>
        <div style="background:#ffffff;padding:30px;border:1px solid #e2e8f0;">
            <p>Dear <strong>{user['name']}</strong>,</p>
            <p>You have successfully registered for:</p>
            <div style="background:#f0f4ff;padding:20px;border-radius:8px;margin:15px 0;border-left:4px solid #4f46e5;">
                <h3 style="color:#4f46e5;margin-top:0;">{event['event_name']}</h3>
                <p>📅 <strong>Date:</strong> {event['date']}</p>
                <p>🕐 <strong>Time:</strong> {event['time']}</p>
                <p>📍 <strong>Venue:</strong> {event['venue']}</p>
            </div>
            <p>Thank you for registering! We look forward to seeing you there.</p>
        </div>
        <div style="background:#1e293b;padding:15px;border-radius:0 0 12px 12px;text-align:center;">
            <p style="color:#94a3b8;margin:0;font-size:12px;">College Event Management System</p>
        </div>
    </div>
    """
    send_email(user['email'], f"Registration Confirmed – {event['event_name']}", email_body)

    conn.close()
    if event['is_paid']:
        flash('Registration submitted! Payment is pending admin verification.', 'info')
    else:
        flash('Successfully registered for the event!', 'success')
    return redirect(url_for('events'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Admin – Event Management (CRUD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/add-event', methods=['GET', 'POST'])
@admin_required
def add_event():
    """Create a new event (admin only)."""
    if request.method == 'POST':
        event_name = request.form.get('event_name', '').strip()
        description = request.form.get('description', '').strip()
        date = request.form.get('date', '')
        time = request.form.get('time', '')
        venue = request.form.get('venue', '').strip()
        limit_enabled = 1 if request.form.get('limit_enabled') else 0
        max_participants = request.form.get('max_participants', 0, type=int)
        is_paid = 1 if request.form.get('is_paid') else 0
        price = request.form.get('price', 0, type=int)
        upi_id = request.form.get('upi_id', '').strip()

        if not event_name:
            flash('Event name is required.', 'danger')
            return redirect(url_for('add_event'))

        # Handle poster image upload
        poster_filename = None
        if 'poster' in request.files:
            poster = request.files['poster']
            if poster and poster.filename and allowed_file(poster.filename):
                poster_filename = secure_filename(f"{uuid.uuid4().hex}_{poster.filename}")
                poster.save(os.path.join(app.config['UPLOAD_FOLDER'], poster_filename))

        # Handle payment QR image upload
        qr_filename = None
        if 'payment_qr' in request.files:
            qr = request.files['payment_qr']
            if qr and qr.filename and allowed_file(qr.filename):
                qr_filename = secure_filename(f"{uuid.uuid4().hex}_{qr.filename}")
                qr.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_filename))

        conn = get_db()
        conn.execute('''INSERT INTO events
            (event_name, description, date, time, venue, poster,
             limit_enabled, max_participants, is_paid, price, upi_id, payment_qr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (event_name, description, date, time, venue, poster_filename,
             limit_enabled, max_participants, is_paid, price, upi_id, qr_filename))
        conn.commit()

        # Auto-generate UPI QR code if paid event with UPI ID
        if is_paid and upi_id:
            event_row = conn.execute('SELECT event_id FROM events ORDER BY event_id DESC LIMIT 1').fetchone()
            if event_row:
                qr_file = generate_upi_qr(upi_id, event_name, price, event_row['event_id'])
                conn.execute('UPDATE events SET payment_qr = ? WHERE event_id = ?',
                            (qr_file, event_row['event_id']))
                conn.commit()

        conn.close()

        flash('Event created successfully! 🎉', 'success')
        return redirect(url_for('manage_events'))

    return render_template('add_event.html')


@app.route('/edit-event/<int:event_id>', methods=['GET', 'POST'])
@admin_required
def edit_event(event_id):
    """Edit an existing event (admin only)."""
    conn = get_db()

    if request.method == 'POST':
        event_name = request.form.get('event_name', '').strip()
        description = request.form.get('description', '').strip()
        date = request.form.get('date', '')
        time = request.form.get('time', '')
        venue = request.form.get('venue', '').strip()
        limit_enabled = 1 if request.form.get('limit_enabled') else 0
        max_participants = request.form.get('max_participants', 0, type=int)
        is_paid = 1 if request.form.get('is_paid') else 0
        price = request.form.get('price', 0, type=int)
        upi_id = request.form.get('upi_id', '').strip()

        # Keep existing files unless new ones are uploaded
        poster_filename = request.form.get('existing_poster', '')
        if 'poster' in request.files:
            poster = request.files['poster']
            if poster and poster.filename and allowed_file(poster.filename):
                poster_filename = secure_filename(f"{uuid.uuid4().hex}_{poster.filename}")
                poster.save(os.path.join(app.config['UPLOAD_FOLDER'], poster_filename))

        qr_filename = request.form.get('existing_qr', '')
        if 'payment_qr' in request.files:
            qr = request.files['payment_qr']
            if qr and qr.filename and allowed_file(qr.filename):
                qr_filename = secure_filename(f"{uuid.uuid4().hex}_{qr.filename}")
                qr.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_filename))

        conn.execute('''UPDATE events SET
            event_name=?, description=?, date=?, time=?, venue=?, poster=?,
            limit_enabled=?, max_participants=?, is_paid=?, price=?, upi_id=?, payment_qr=?
            WHERE event_id=?''',
            (event_name, description, date, time, venue, poster_filename,
             limit_enabled, max_participants, is_paid, price, upi_id, qr_filename, event_id))
        conn.commit()

        # Auto-regenerate UPI QR code if paid event with UPI ID
        if is_paid and upi_id:
            qr_file = generate_upi_qr(upi_id, event_name, price, event_id)
            conn.execute('UPDATE events SET payment_qr = ? WHERE event_id = ?', (qr_file, event_id))
            conn.commit()

        conn.close()

        flash('Event updated successfully!', 'success')
        return redirect(url_for('manage_events'))

    event = conn.execute('SELECT * FROM events WHERE event_id = ?', (event_id,)).fetchone()
    conn.close()

    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('manage_events'))

    return render_template('add_event.html', event=event, editing=True)


@app.route('/delete-event/<int:event_id>', methods=['POST'])
@admin_required
def delete_event(event_id):
    """Delete an event and all its registrations (admin only)."""
    conn = get_db()
    conn.execute('DELETE FROM registrations WHERE event_id = ?', (event_id,))
    conn.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event deleted successfully.', 'info')
    return redirect(url_for('manage_events'))


@app.route('/manage-events')
@admin_required
def manage_events():
    """Admin page to view and manage all events."""
    conn = get_db()
    all_events = conn.execute('SELECT * FROM events ORDER BY date DESC').fetchall()

    event_reg_counts = {}
    for event in all_events:
        count = conn.execute(
            'SELECT COUNT(*) as cnt FROM registrations WHERE event_id = ?',
            (event['event_id'],)
        ).fetchone()['cnt']
        event_reg_counts[event['event_id']] = count

    conn.close()
    return render_template('manage_events.html', events=all_events, reg_counts=event_reg_counts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Participants – View & Export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/participants/<int:event_id>')
@admin_required
def participants(event_id):
    """View all participants registered for a specific event."""
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE event_id = ?', (event_id,)).fetchone()
    participant_list = conn.execute('''
        SELECT u.name, u.email, u.department, u.batch, u.college_name,
               r.payment_status, r.reg_id
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
        ORDER BY r.reg_id ASC
    ''', (event_id,)).fetchall()
    conn.close()
    return render_template('participants.html', event=event, participants=participant_list)


@app.route('/download-participants/<int:event_id>')
@admin_required
def download_participants(event_id):
    """Export participant list as an Excel file using pandas + openpyxl."""
    conn = get_db()
    event = conn.execute('SELECT * FROM events WHERE event_id = ?', (event_id,)).fetchone()
    participant_list = conn.execute('''
        SELECT u.name as "Student Name", u.email as "Email",
               u.department as "Department", u.batch as "Batch",
               u.college_name as "College",
               e.event_name as "Event Name", e.date as "Date",
               r.payment_status as "Payment Status"
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        JOIN events e ON r.event_id = e.event_id
        WHERE r.event_id = ?
    ''', (event_id,)).fetchall()
    conn.close()

    # Convert rows to list of dicts for pandas
    data = [dict(p) for p in participant_list]
    df = pd.DataFrame(data) if data else pd.DataFrame(
        columns=["Student Name", "Email", "Department", "Batch", "College",
                 "Event Name", "Date", "Payment Status"]
    )

    # Generate Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Participants')
    output.seek(0)

    safe_name = event['event_name'].replace(' ', '_').replace('/', '_')
    filename = f"participants_{safe_name}.xlsx"
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Student Profile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and edit student profile, view registered events."""
    conn = get_db()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        batch = request.form.get('batch', '').strip()
        college_name = request.form.get('college_name', '').strip()
        new_password = request.form.get('new_password', '')
        current_password = request.form.get('current_password', '')

        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        # Verify current password before allowing changes
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.', 'danger')
            conn.close()
            return redirect(url_for('profile'))

        if name:
            conn.execute('UPDATE users SET name = ? WHERE id = ?', (name, session['user_id']))
            session['user_name'] = name

        conn.execute('UPDATE users SET department = ?, batch = ?, college_name = ? WHERE id = ?',
                    (department, batch, college_name, session['user_id']))

        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                conn.close()
                return redirect(url_for('profile'))
            hashed = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, session['user_id']))

        conn.commit()
        conn.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Fetch user details and registered events
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    registrations = conn.execute('''
        SELECT e.* FROM registrations r
        JOIN events e ON r.event_id = e.event_id
        WHERE r.user_id = ?
        ORDER BY e.date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('profile.html', user=user, registrations=registrations)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Password Reset
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Send a password reset link to user's email."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        # Validate that an email was actually provided
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('forgot_password'))

        conn = get_db()
        try:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

            if user:
                # Generate a secure token with 1-hour expiry
                token = uuid.uuid4().hex
                expiry = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

                # Remove any existing reset tokens for this email before inserting a new one
                conn.execute('DELETE FROM password_resets WHERE email = ?', (email,))
                conn.execute(
                    'INSERT INTO password_resets (email, token, expiry_time) VALUES (?, ?, ?)',
                    (email, token, expiry)
                )
                conn.commit()

                # Build and send the reset email (send_email never raises – it catches internally)
                reset_link = url_for('reset_password', token=token, _external=True)
                email_body = f"""
                <div style="font-family:'Inter',sans-serif;max-width:600px;margin:0 auto;">
                    <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:30px;border-radius:12px 12px 0 0;">
                        <h2 style="color:white;margin:0;">🔒 Password Reset</h2>
                    </div>
                    <div style="background:#ffffff;padding:30px;border:1px solid #e2e8f0;">
                        <p>Dear <strong>{user['name']}</strong>,</p>
                        <p>We received a request to reset your password. Click the button below:</p>
                        <div style="text-align:center;margin:25px 0;">
                            <a href="{reset_link}" style="display:inline-block;padding:14px 32px;
                               background:linear-gradient(135deg,#4f46e5,#7c3aed);color:white;
                               text-decoration:none;border-radius:8px;font-weight:600;">
                               Reset My Password
                            </a>
                        </div>
                        <p style="color:#64748b;font-size:13px;">
                            ⏰ This link expires in <strong>1 hour</strong>.<br>
                            If you didn't request this, please ignore this email.
                        </p>
                    </div>
                    <div style="background:#1e293b;padding:15px;border-radius:0 0 12px 12px;text-align:center;">
                        <p style="color:#94a3b8;margin:0;font-size:12px;">College Event Management System</p>
                    </div>
                </div>
                """
                send_email(email, "Password Reset – College Event System", email_body)

            # Always show the same message to avoid leaking whether an email is registered
            flash('If this email is registered, a password reset link has been sent.', 'info')
        except Exception as e:
            print(f"[ERROR] forgot_password: {e}")
            flash('An error occurred. Please try again later.', 'danger')
        finally:
            conn.close()

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using a valid token from email."""
    # Validate token exists and is not expired before doing anything else
    conn = get_db()
    try:
        reset = conn.execute(
            'SELECT * FROM password_resets WHERE token = ?', (token,)
        ).fetchone()

        if not reset:
            flash('Invalid or expired reset link.', 'danger')
            return redirect(url_for('forgot_password'))

        # Safely parse expiry – guard against malformed values in the DB
        try:
            expiry = datetime.strptime(reset['expiry_time'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            conn.execute('DELETE FROM password_resets WHERE token = ?', (token,))
            conn.commit()
            flash('Invalid reset link. Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))

        if datetime.now() > expiry:
            conn.execute('DELETE FROM password_resets WHERE token = ?', (token,))
            conn.commit()
            flash('Reset link has expired. Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            password = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')

            if not password:
                flash('Password cannot be empty.', 'danger')
                return redirect(url_for('reset_password', token=token))

            if password != confirm:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('reset_password', token=token))

            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return redirect(url_for('reset_password', token=token))

            # Update the user's password and invalidate the token
            hashed = generate_password_hash(password)
            conn.execute('UPDATE users SET password = ? WHERE email = ?', (hashed, reset['email']))
            conn.execute('DELETE FROM password_resets WHERE token = ?', (token,))
            conn.commit()

            flash('Password reset successful! Please login with your new password.', 'success')
            return redirect(url_for('login'))

    except Exception as e:
        print(f"[ERROR] reset_password: {e}")
        flash('An error occurred. Please try again later.', 'danger')
        return redirect(url_for('forgot_password'))
    finally:
        conn.close()

    return render_template('reset_password.html', token=token)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Admin Dashboard & Analytics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with analytics overview."""
    conn = get_db()

    total_events = conn.execute('SELECT COUNT(*) as cnt FROM events').fetchone()['cnt']
    total_students = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE role = 'student'"
    ).fetchone()['cnt']
    total_registrations = conn.execute('SELECT COUNT(*) as cnt FROM registrations').fetchone()['cnt']
    total_admins = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'"
    ).fetchone()['cnt']

    recent_events = conn.execute(
        'SELECT * FROM events ORDER BY event_id DESC LIMIT 5'
    ).fetchall()

    conn.close()
    return render_template(
        'admin_dashboard.html',
        total_events=total_events,
        total_students=total_students,
        total_registrations=total_registrations,
        total_admins=total_admins,
        recent_events=recent_events
    )


@app.route('/api/chart-data')
@admin_required
def chart_data():
    """JSON API endpoint providing chart data for the admin dashboard."""
    conn = get_db()

    # Participants per event (for bar chart and pie chart)
    events_data = conn.execute('''
        SELECT e.event_name, COUNT(r.reg_id) as participants
        FROM events e
        LEFT JOIN registrations r ON e.event_id = r.event_id
        GROUP BY e.event_id
        ORDER BY participants DESC
    ''').fetchall()

    conn.close()

    return jsonify({
        'labels': [e['event_name'] for e in events_data],
        'participants': [e['participants'] for e in events_data]
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Payment Verification (Admin)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/verify-payment/<int:reg_id>', methods=['POST'])
@admin_required
def verify_payment(reg_id):
    """Admin verifies a student's payment – marks registration as confirmed."""
    conn = get_db()
    conn.execute(
        'UPDATE registrations SET payment_status = ? WHERE reg_id = ?',
        ('verified', reg_id)
    )
    conn.commit()

    # Send confirmation email to student
    reg = conn.execute('''
        SELECT u.name, u.email, e.event_name, e.date, e.time, e.venue
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        JOIN events e ON r.event_id = e.event_id
        WHERE r.reg_id = ?
    ''', (reg_id,)).fetchone()

    if reg:
        email_body = f"""
        <div style="font-family:'Inter',sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:linear-gradient(135deg,#10b981,#06b6d4);padding:30px;border-radius:12px 12px 0 0;">
                <h2 style="color:white;margin:0;">Payment Verified!</h2>
            </div>
            <div style="background:#ffffff;padding:30px;border:1px solid #e2e8f0;">
                <p>Dear <strong>{reg['name']}</strong>,</p>
                <p>Your payment for <strong>{reg['event_name']}</strong> has been <span style="color:#10b981;font-weight:700;">verified</span> by the admin.</p>
                <p>You are now officially registered!</p>
                <div style="background:#f0f4ff;padding:20px;border-radius:8px;margin:15px 0;border-left:4px solid #10b981;">
                    <p>Date: {reg['date']}</p>
                    <p>Time: {reg['time']}</p>
                    <p>Venue: {reg['venue']}</p>
                </div>
            </div>
        </div>
        """
        send_email(reg['email'], f"Payment Verified - {reg['event_name']}", email_body)

    event_id = conn.execute('SELECT event_id FROM registrations WHERE reg_id = ?', (reg_id,)).fetchone()
    conn.close()
    flash('Payment verified successfully!', 'success')
    return redirect(url_for('participants', event_id=event_id['event_id']))


@app.route('/reject-payment/<int:reg_id>', methods=['POST'])
@admin_required
def reject_payment(reg_id):
    """Admin rejects a student's payment – removes registration."""
    conn = get_db()

    # Get event_id before deleting
    reg = conn.execute('SELECT event_id FROM registrations WHERE reg_id = ?', (reg_id,)).fetchone()
    event_id = reg['event_id'] if reg else None

    conn.execute('UPDATE registrations SET payment_status = ? WHERE reg_id = ?', ('rejected', reg_id))
    conn.commit()
    conn.close()
    flash('Payment rejected. Student has been notified.', 'warning')
    return redirect(url_for('participants', event_id=event_id))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Error Handlers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.errorhandler(404)
def not_found(e):
    flash('Page not found.', 'warning')
    return redirect(url_for('index'))


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 2MB.', 'danger')
    return redirect(request.url)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Startup Initialisation (runs under gunicorn and direct exec)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Ensure upload directory exists and DB tables are created regardless
# of how the app is launched (gunicorn does NOT run __main__ block).
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_db()

if __name__ == '__main__':
    print("=== Smart College Event Management System ===")
    print("    Running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
