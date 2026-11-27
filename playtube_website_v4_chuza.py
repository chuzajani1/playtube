# ============================================
# Playza v4 (Chuza Edition) - Video Downloader with AI Assistant
# Created by: Chuza
# Copyright © 2026. All Rights Reserved.
# Unauthorized copying or distribution prohibited.
# ============================================
"""
Playza - All in One Video Downloader
Copyright (c) 2026 Chuza

This software is protected. Unauthorized reproduction or
distribution is strictly prohibited.

Contact: chuzajani1@gmail.com
"""
from flask import Flask, request, jsonify, send_file, render_template_string, Response, stream_with_context, session, redirect, url_for
import yt_dlp


# --- TLS bundle shim (v2) ---
try:
    import certifi as _certifi
    _orig_certifi_where = _certifi.where
    def _pt_where(*a, **k):
        return os.environ.get("SSL_CERT_FILE") or _orig_certifi_where(*a, **k)
    _certifi.where = _pt_where
except Exception:
    pass
import os
import tempfile
import requests
import re
import json
import time
import threading
import hashlib
import html
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
import subprocess
import shutil
from collections import defaultdict
from functools import wraps
import sqlite3
import base64
import random
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# YouTube API Key (Fallback ke liye)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def search_youtube_api(query, max_results=50):
    """YouTube API se search karo - kabhi error nahi"""
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'maxResults': max_results,
            'q': query,
            'type': 'video',
            'key': YOUTUBE_API_KEY,
            'safeSearch': 'none'
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if 'items' in data and len(data['items']) > 0:
            return data['items']
        else:
            return None
    except:
        return None


def search_youtube_web(query, max_results=20):
    """YouTube website se direct scrape karo"""
    try:
        import urllib.parse

        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        response = requests.get(search_url, headers=headers, timeout=10)
        html = response.text

        # Extract video IDs from ytInitialData
        video_ids = re.findall(r'"videoId":"([^"]+)"', html)

        # Remove duplicates
        video_ids = list(dict.fromkeys(video_ids))

        items = []
        for vid in video_ids[:max_results]:
            if vid and len(vid) == 11:
                items.append({
                    'id': {'videoId': vid},
                    'snippet': {
                        'title': f'Video {vid}',
                        'channelTitle': 'YouTube',
                        'channelId': '',
                        'thumbnails': {
                            'high': {'url': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg'},
                            'medium': {'url': f'https://i.ytimg.com/vi/{vid}/mqdefault.jpg'},
                            'default': {'url': f'https://i.ytimg.com/vi/{vid}/default.jpg'}
                        }
                    }
                })

        return items if items else None
    except:
        return None


APP_VERSION = 53  # Update 82: har update par +1 — More page par dikhta hai

# Cache system
search_cache = {}
CACHE_DURATION = 1800

# Watch history storage
watch_history = []

# Popular videos fallback
POPULAR_VIDEOS = [
    {"id": {"videoId": "dQw4w9WgXcQ"}, "snippet": {"title": "Rick Astley - Never Gonna Give You Up", "channelTitle": "Rick Astley",
        "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}}}},
    {"id": {"videoId": "kJQP7kiw5Fk"}, "snippet": {"title": "Luis Fonsi - Despacito ft. Daddy Yankee", "channelTitle": "Luis Fonsi",
        "channelId": "UCxoq-PAQeAdk_zyg8YS0JqA", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg"}}}},
    {"id": {"videoId": "JGwWNGJdvx8"}, "snippet": {"title": "Ed Sheeran - Shape of You", "channelTitle": "Ed Sheeran",
        "channelId": "UC0C-w0YjGpqDXGB8IHb662A", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/JGwWNGJdvx8/hqdefault.jpg"}}}},
    {"id": {"videoId": "9bZkp7q19f0"}, "snippet": {"title": "PSY - GANGNAM STYLE", "channelTitle": "officialpsy",
        "channelId": "UCrDkAvwZum-UTjHmzDI2iIw", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg"}}}},
    {"id": {"videoId": "hT_nvWreIhg"}, "snippet": {"title": "OneRepublic - Counting Stars", "channelTitle": "OneRepublic",
        "channelId": "UCG7WdmLGzacESLc9DMyZb-A", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/hT_nvWreIhg/hqdefault.jpg"}}}},
    {"id": {"videoId": "YQHsXMglC9A"}, "snippet": {"title": "Adele - Hello", "channelTitle": "Adele",
        "channelId": "UCU0vOVvBIKl9h7rYH0KvTVA", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/YQHsXMglC9A/hqdefault.jpg"}}}},
    {"id": {"videoId": "7wtfhZwyrcc"}, "snippet": {"title": "Imagine Dragons - Believer", "channelTitle": "Imagine Dragons",
        "channelId": "UCdKlJbQ5vKkK7pYn0LDwMxQ", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/7wtfhZwyrcc/hqdefault.jpg"}}}},
    {"id": {"videoId": "OPf0YbXqDm0"}, "snippet": {"title": "Mark Ronson - Uptown Funk", "channelTitle": "Mark Ronson",
        "channelId": "UCt9v9nFv6K-3Lb6Bq3M2j5Q", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/OPf0YbXqDm0/hqdefault.jpg"}}}},
    {"id": {"videoId": "2Vv-BfVoq4g"}, "snippet": {"title": "Ed Sheeran - Perfect", "channelTitle": "Ed Sheeran",
        "channelId": "UC0C-w0YjGpqDXGB8IHb662A", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/2Vv-BfVoq4g/hqdefault.jpg"}}}},
    {"id": {"videoId": "60ItHLz5WEA"}, "snippet": {"title": "Alan Walker - Faded", "channelTitle": "Alan Walker",
        "channelId": "UCJrOtniJ0-NWz37R30urifQ", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/60ItHLz5WEA/hqdefault.jpg"}}}},
    {"id": {"videoId": "RgKAFK5djSk"}, "snippet": {"title": "Wiz Khalifa - See You Again ft. Charlie Puth", "channelTitle": "Wiz Khalifa",
        "channelId": "UCq4qiWaCq4J6s1J1J6k1J2A", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/RgKAFK5djSk/hqdefault.jpg"}}}},
    {"id": {"videoId": "fJ9rUzIMcZQ"}, "snippet": {"title": "Queen - Bohemian Rhapsody", "channelTitle": "Queen",
        "channelId": "UCiMhD4jzUQK2K2K2K2K2K2KQ", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg"}}}},
    {"id": {"videoId": "lp-EO5I60KA"}, "snippet": {"title": "Ed Sheeran - Thinking Out Loud", "channelTitle": "Ed Sheeran",
        "channelId": "UC0C-w0YjGpqDXGB8IHb662A", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/lp-EO5I60KA/hqdefault.jpg"}}}},
    {"id": {"videoId": "kXYiU_JCYtU"}, "snippet": {"title": "Linkin Park - Numb", "channelTitle": "Linkin Park",
        "channelId": "UCZU9T1ceaOgwfLRq7OKFU4Q", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/kXYiU_JCYtU/hqdefault.jpg"}}}},
    {"id": {"videoId": "uelHwf8o7_U"}, "snippet": {"title": "Eminem - Love The Way You Lie ft. Rihanna", "channelTitle": "EminemMusic",
        "channelId": "UCfM3zsQsOnfWNUppiycmBuw", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/uelHwf8o7_U/hqdefault.jpg"}}}},
    {"id": {"videoId": "e-ORhEE9VVg"}, "snippet": {"title": "Taylor Swift - Blank Space", "channelTitle": "Taylor Swift",
        "channelId": "UCqECaJ8Gagnn7YCbPEzWH6g", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/e-ORhEE9VVg/hqdefault.jpg"}}}},
    {"id": {"videoId": "nfWlot6h_JM"}, "snippet": {"title": "Taylor Swift - Shake It Off", "channelTitle": "Taylor Swift",
        "channelId": "UCqECaJ8Gagnn7YCbPEzWH6g", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/nfWlot6h_JM/hqdefault.jpg"}}}},
    {"id": {"videoId": "pRpeEdMmmQ0"}, "snippet": {"title": "Shakira - Waka Waka", "channelTitle": "Shakira",
        "channelId": "UCGnPYuGQwQwQwQwQwQwQwQA", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/pRpeEdMmmQ0/hqdefault.jpg"}}}},
    {"id": {"videoId": "hTWKbfoikeg"}, "snippet": {"title": "Nirvana - Smells Like Teen Spirit", "channelTitle": "Nirvana",
        "channelId": "UCiQ3Q3Q3Q3Q3Q3Q3Q3Q4Q0Q", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/hTWKbfoikeg/hqdefault.jpg"}}}},
    {"id": {"videoId": "4NRXx6U8ABQ"}, "snippet": {"title": "The Weeknd - Blinding Lights", "channelTitle": "The Weeknd",
        "channelId": "UCiQ3Q3Q3Q3Q3Q3Q3Q3Q4Q3Q", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg"}}}},
    {"id": {"videoId": "yJ6jT2nC0jM"}, "snippet": {"title": "BTS - Dynamite", "channelTitle": "BTS",
        "channelId": "UCiQ3Q3Q3Q3Q3Q3Q3Q3Q5Q0Q", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/yJ6jT2nC0jM/hqdefault.jpg"}}}},
    {"id": {"videoId": "9h30Bx4Klxg"}, "snippet": {"title": "Adele - Rolling in the Deep", "channelTitle": "Adele",
        "channelId": "UCU0vOVvBIKl9h7rYH0KvTVA", "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/9h30Bx4Klxg/hqdefault.jpg"}}}},
]

# Database setup — persistent data directory (Update 31).
# PLAYTUBE_DATA_DIR env se badla ja sakta hai (Railway par volume ka path);
# default: script ke sath 'playtube_data' folder. /tmp NAHI — wo har
# restart/redeploy par ur jata tha, users aur counts reset ho jate the.
import os
DATA_DIR = os.environ.get('PLAYTUBE_DATA_DIR') or os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'playtube_data')
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = "/tmp"
DB_FILE = os.path.join(DATA_DIR, "playtube_users.db")
try:
    _legacy_db = os.path.join("/tmp", "playtube_users.db")
    if not os.path.exists(DB_FILE) and os.path.exists(_legacy_db):
        shutil.copyfile(_legacy_db, DB_FILE)
except Exception:
    pass
# ============ GMAIL VERIFICATION SYSTEM ============
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL", "chuzajani1@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

verification_codes = {}

# v4: pending codes (signup + password reset) disk par bhi save hote hain,
# taake server restart par bhi code valid rahe.
PENDING_CODES_FILE = os.path.join(os.path.expanduser("~"), "Downloads",
                                  "Playza", "pending_codes.json")
reset_codes = {}


def _save_pending_codes():
    try:
        os.makedirs(os.path.dirname(PENDING_CODES_FILE), exist_ok=True)
        with open(PENDING_CODES_FILE, 'w') as _f:
            json.dump({'signup': verification_codes, 'reset': reset_codes}, _f)
    except Exception:
        pass


def _load_pending_codes():
    try:
        if os.path.exists(PENDING_CODES_FILE):
            with open(PENDING_CODES_FILE) as _f:
                _d = json.load(_f)
            verification_codes.update(_d.get('signup') or {})
            reset_codes.update(_d.get('reset') or {})
    except Exception:
        pass


_load_pending_codes()


def _send_via_brevo(email, subject, body):
    """Brevo HTTPS API se email (Railway par SMTP ports band hain,
    is liye ye pehla rasta hai). Sirf BREVO_API_KEY env se key ati hai."""
    import urllib.request
    payload = json.dumps({
        'sender': {'name': 'Playza', 'email': GMAIL_EMAIL},
        'to': [{'email': email}],
        'subject': subject,
        'textContent': body,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.brevo.com/v3/smtp/email', data=payload, method='POST')
    req.add_header('api-key', os.environ.get('BREVO_API_KEY'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status in (200, 201, 204)


def send_verification_email(email, code, purpose='Verification'):
    """Best-effort email. Sirf tab True jab mail asal me chali jaye.

    Pehla rasta Brevo HTTPS API (BREVO_API_KEY) — Railway SMTP ports
    block karta hai. Dusra rasta Gmail SMTP (GMAIL_APP_PASSWORD).
    Koi password/key code me nahi hai — sab env se ate hain.
    """
    subject = f"Playza - {purpose} Code"
    body = (f"Hello!\n\nYour Playza {purpose.lower()} code is: {code}\n\n"
            f"This code will expire in 10 minutes.\n\n- Playza Team\n")
    if os.environ.get('BREVO_API_KEY'):
        try:
            return _send_via_brevo(email, subject, body)
        except Exception as e:
            print(f"Brevo email error: {e}")
            return False
    if not os.environ.get('GMAIL_APP_PASSWORD'):
        print('[Playza] Email not configured (BREVO_API_KEY / GMAIL_APP_PASSWORD missing) - code stored, email not sent.')
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(GMAIL_EMAIL, os.environ.get('GMAIL_APP_PASSWORD'))
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


@app.route('/api/send-verification-code', methods=['POST'])
def send_verification_code():
    if not feature_enabled('signup_enabled'):
        return jsonify({'error': 'Signup abhi band hai (admin ne off kiya hai)',
                        'signup_disabled': True}), 403
    data = request.json
    email = data.get('email', '').strip()

    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Email already registered!'}), 400
    conn.close()

    code = str(random.randint(100000, 999999))

    verification_codes[email] = {
        'code': code,
        'timestamp': time.time()
    }
    _save_pending_codes()

    sent = send_verification_email(email, code)
    return jsonify({'success': True, 'mail_sent': sent,
                    'message': 'Verification code sent!' if sent else
                               'Code tayyar hai lekin email abhi nahi bheja ja saka (mail setup pending hai).'})


@app.route('/api/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()

    if email not in verification_codes:
        return jsonify({'error': 'Send code first!'}), 400

    saved = verification_codes[email]

    if time.time() - saved['timestamp'] > 600:
        del verification_codes[email]
        return jsonify({'error': 'Code expired!'}), 400

    if saved['code'] != code:
        return jsonify({'error': 'Invalid code!'}), 400

    del verification_codes[email]
    _save_pending_codes()
    session['pt_verified_email'] = email
    session['pt_verified_at'] = time.time()
    return jsonify({'success': True, 'message': 'Email verified!'})


@app.route('/api/signup-start', methods=['POST'])
def signup_start():
    """Update 21: signup ka pehla step — details lo, Gmail par code bhejo.
    Account abhi NAHI banta; code verify hone par banta hai."""
    if not feature_enabled('signup_enabled'):
        return jsonify({'error': 'Signup abhi band hai (admin ne off kiya hai)',
                        'signup_disabled': True}), 403
    data = request.json or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?',
                   (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Username or email already exists'}), 400
    conn.close()

    code = str(random.randint(100000, 999999))
    verification_codes[email] = {'code': code, 'timestamp': time.time(),
                                 'username': username,
                                 'password_hash': hash_password(password)}
    _save_pending_codes()
    sent = send_verification_email(email, code)
    return jsonify({'success': True, 'mail_sent': sent,
                    'message': 'Verification code aap ki Gmail par bheja gaya hai.' if sent else
                               'Code tayyar hai lekin email abhi nahi bheja ja saka (mail setup pending hai).'})


@app.route('/api/signup-verify', methods=['POST'])
def signup_verify():
    """Update 21: code verify karo — account banta hai + login ho jata hai."""
    data = request.json or {}
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    saved = verification_codes.get(email)
    if not saved or 'password_hash' not in saved:
        return jsonify({'error': 'Pehle account ki request bhejein (code mangwayein)'}), 400
    if time.time() - saved['timestamp'] > 600:
        del verification_codes[email]
        _save_pending_codes()
        return jsonify({'error': 'Code expired!'}), 400
    if saved['code'] != code:
        return jsonify({'error': 'Invalid code!'}), 400

    username = saved['username']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?',
                   (username, email))
    if cursor.fetchone():
        conn.close()
        del verification_codes[email]
        _save_pending_codes()
        return jsonify({'error': 'Username or email already exists'}), 400
    try:
        cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                       (username, email, saved['password_hash']))
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    conn.close()

    del verification_codes[email]
    _save_pending_codes()
    session.permanent = True
    session['user_id'] = user_id
    session['username'] = username
    return jsonify({'success': True,
                    'user': {'id': user_id, 'username': username, 'email': email}})


@app.route('/api/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    """Update 22: code verify karke NAYA password set karo."""
    data = request.json or {}
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    saved = reset_codes.get(email)
    if not saved:
        return jsonify({'error': 'Pehle code mangwayein'}), 400
    if time.time() - saved['timestamp'] > 600:
        del reset_codes[email]
        _save_pending_codes()
        return jsonify({'error': 'Code expired!'}), 400
    if saved['code'] != code:
        return jsonify({'error': 'Invalid code!'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?',
                   (hash_password(new_password), email))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    del reset_codes[email]
    _save_pending_codes()
    if not changed:
        return jsonify({'error': 'Email not found!'}), 404
    return jsonify({'success': True,
                    'message': 'Password badal gaya hai - ab naye password se sign in karein.'})


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            theme TEXT DEFAULT 'dark',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Visitor counting (Update 31) — database mein, JSON file mein nahi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_visits (
            day TEXT PRIMARY KEY,
            opens INTEGER NOT NULL DEFAULT 0,
            uniq INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_visit_ips (
            day TEXT NOT NULL,
            ip TEXT NOT NULL,
            PRIMARY KEY (day, ip)
        )
    ''')
    # Guest free downloads (Update 44) — per-device ginti, database mein
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guest_downloads (
            device_id TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0,
            updated TEXT
        )
    ''')

    conn.commit()
    conn.close()


init_db()

# ============ PAKISTAN PREMIUM SYSTEM TABLES ============


def init_premium_system():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS premium_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            plan_type TEXT DEFAULT 'monthly',
            is_active INTEGER DEFAULT 1,
            start_date TIMESTAMP,
            expiry_date TIMESTAMP,
            payment_method TEXT,
            transaction_id TEXT,
            amount_paid REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pakistan_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payment_method TEXT,
            sender_account TEXT,
            transaction_id TEXT,
            amount_pkr REAL,
            plan_type TEXT,
            status TEXT DEFAULT 'pending',
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()


init_premium_system()

# ============ SITE SETTINGS (persistent) ============
# Payment accounts are NOT hard-coded. The admin saves them from the
# Admin Panel and they persist in playtube_settings.json.
try:
    SETTINGS_FILE = os.path.join(DATA_DIR, 'playtube_settings.json')
    _legacy_settings = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'playtube_settings.json')
    if not os.path.exists(SETTINGS_FILE) and os.path.exists(_legacy_settings):
        shutil.copyfile(_legacy_settings, SETTINGS_FILE)
    with open(SETTINGS_FILE, 'a'):
        pass
except Exception:
    SETTINGS_FILE = os.path.join("/tmp", "playtube_settings.json")

PAYMENT_METHOD_META = {
    'jazzcash': {'name': 'JazzCash', 'icon': 'fa-wallet', 'color': '#e60000'},
    'easypaisa': {'name': 'EasyPaisa', 'icon': 'fa-mobile', 'color': '#009900'}
}


def load_site_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_site_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def _rebuild_payment_accounts():
    """PAKISTAN_PAYMENTS only contains methods the admin has actually saved."""
    settings = load_site_settings()
    accounts = settings.get('payment_accounts', {})
    rebuilt = {}
    for method, meta in PAYMENT_METHOD_META.items():
        acc = accounts.get(method) or {}
        number = str(acc.get('account_number', '')).strip()
        if number:
            rebuilt[method] = {
                'name': meta['name'],
                'account_number': number,
                'account_title': acc.get('account_title', 'Playza Premium'),
                'icon': meta['icon'],
                'color': meta['color']
            }
    PAKISTAN_PAYMENTS.clear()
    PAKISTAN_PAYMENTS.update(rebuilt)



# ============ FEATURE TOGGLES + ANNOUNCEMENT (v4 Admin Panel) ============
FEATURE_DEFAULTS = {'ai_enabled': True, 'downloads_enabled': True,
                    'premium_enabled': True, 'social_enabled': True,
                    'signup_enabled': True, 'floating_enabled': True,
                    'maintenance_mode': False, 'hd_premium_only': True,
                    'shorts_enabled': True, 'music_enabled': True,
                    'guest_downloads_enabled': True,
                    'storage_autoclean': True}


def get_feature_toggles():
    _s = load_site_settings()
    _t = dict(FEATURE_DEFAULTS)
    _t.update(_s.get('feature_toggles') or {})
    return _t


def feature_enabled(name):
    return bool(get_feature_toggles().get(name, FEATURE_DEFAULTS.get(name, True)))


# ============ GUEST FREE DOWNLOADS (Update 44) ============
def get_guest_limit():
    """Bina account kitni free downloads — admin ki setting, default 10.
    Update 122: Admin ka 'Guest downloads' master switch OFF ho to
    limit 0 — bina account download bilkul band (sab checks isi
    function se guzarte hain)."""
    try:
        if not feature_enabled('guest_downloads_enabled'):
            return 0
        return max(0, int(load_site_settings().get('guest_download_limit', 10)))
    except (TypeError, ValueError):
        return 10


def _guest_device_id():
    did = request.cookies.get('pt_guest')
    if did:
        return did[:64]
    import hashlib
    raw = (request.remote_addr or '') + '|' + (request.headers.get('User-Agent') or '')
    return 'h_' + hashlib.md5(raw.encode()).hexdigest()


def _guest_count(device_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT count FROM guest_downloads WHERE device_id = ?',
                    (device_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _guest_inc(device_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO guest_downloads (device_id, count, updated) '
                    'VALUES (?, 1, ?) ON CONFLICT(device_id) DO UPDATE SET '
                    'count = count + 1, updated = excluded.updated',
                    (device_id, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()


guest_pending = {}


@app.after_request
def _pt_guest_cookie(resp):
    try:
        if not request.cookies.get('pt_guest'):
            import uuid
            resp.set_cookie('pt_guest', uuid.uuid4().hex,
                            max_age=365 * 24 * 3600, httponly=True,
                            samesite='Lax')
    except Exception:
        pass
    return resp


def get_announcement():
    return (load_site_settings().get('announcement') or '').strip()


# ============ HOT DEALS (Update 32 — More tab, admin-managed) ============
# Products admin panel se change hote hain. Default products ke links
# KHALI hain (purane Daraz links kisi aur ke affiliate the) — admin
# apne links khud lagata hai; link na ho to Buy button nahi dikhta.
DEFAULT_DEALS = [
    {'name': 'Sneakers', 'emoji': '👟', 'old_price': 2499, 'new_price': 1299, 'badge': '48%', 'link': ''},
    {'name': 'Earbuds', 'emoji': '🎧', 'old_price': 3000, 'new_price': 729, 'badge': '76%', 'link': ''},
    {'name': 'P47 Headphone', 'emoji': '🎧', 'old_price': 1999, 'new_price': 834, 'badge': '58%', 'link': ''},
    {'name': 'MIC', 'emoji': '🎤', 'old_price': 1748, 'new_price': 999, 'badge': '43%', 'link': ''},
    {'name': 'Nightwear', 'emoji': '👚', 'old_price': 2000, 'new_price': 790, 'badge': '61%', 'link': ''},
    {'name': 'Scrubber', 'emoji': '🚿', 'old_price': 207, 'new_price': 179, 'badge': '14%', 'link': ''},
    {'name': 'Wallet', 'emoji': '👝', 'old_price': 600, 'new_price': 253, 'badge': '58%', 'link': ''},
    {'name': 'Phone', 'emoji': '📱', 'old_price': 0, 'new_price': 15999, 'badge': 'HOT', 'link': ''},
]


def get_deals():
    d = load_site_settings().get('deals')
    if isinstance(d, list):
        return d
    return [dict(x) for x in DEFAULT_DEALS]


_MAINTENANCE_EXEMPT = ('/admin', '/api/admin', '/api/user-info', '/api/site-config',
                       '/sw.js', '/manifest.json', '/app-icon.svg', '/playtube.apk',
                       '/api/apk-status')


@app.before_request
def _v4_maintenance_gate():
    try:
        if not feature_enabled('maintenance_mode'):
            return None
        if session.get('pt_admin') or _is_owner_session():
            return None
        _p = request.path or '/'
        if any(_p.startswith(_x) for _x in _MAINTENANCE_EXEMPT):
            return None
        if _p.startswith('/api/'):
            return jsonify({'error': 'Site maintenance me hai - thodi der baad try karein',
                            'maintenance': True}), 503
        return ('<!DOCTYPE html><html><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>Playza - Maintenance</title></head>'
                '<body style="background:#12101f;color:#eceaf6;font-family:sans-serif;'
                'display:flex;align-items:center;justify-content:center;min-height:100vh;'
                'margin:0;text-align:center;padding:20px"><div>'
                '<h1 style="color:#8b6dff">Playza</h1>'
                '<p>' + (html.escape(load_site_settings().get(
                    'maintenance_message') or '')
                    or 'Site abhi maintenance me hai. Thodi der baad dobara try karein.') + '</p>'
                '</div></body></html>'), 503
    except Exception:
        return None


# ============ PAKISTAN PAYMENT METHODS (dynamic, admin-managed) ============
PAKISTAN_PAYMENTS = {}
_rebuild_payment_accounts()

# ============ PREMIUM PLANS (PKR) ============
PREMIUM_PLANS_PKR = {
    'weekly': {'name': 'Weekly', 'price': 200, 'days': 7},
    'monthly': {'name': 'Monthly', 'price': 500, 'days': 30},
    'yearly': {'name': 'Yearly', 'price': 3000, 'days': 365}
}


# v4: admin-set premium prices (site settings me saved) startup par apply
try:
    _sp = load_site_settings().get('premium_prices') or {}
    for _pk in PREMIUM_PLANS_PKR:
        if _pk in _sp:
            PREMIUM_PLANS_PKR[_pk]['price'] = int(_sp[_pk])
except Exception:
    pass


def is_premium_user(user_id):
    if not user_id:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM premium_users WHERE user_id = ? AND is_active = 1 AND expiry_date > datetime("now")', (user_id,))
        premium = cursor.fetchone()
        conn.close()

        if premium:
            return True
        else:
            # Premium expired - deactivate
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE premium_users SET is_active = 0 WHERE user_id = ? AND expiry_date < datetime("now")', (user_id,))
            conn.commit()
            conn.close()
            return False
    except:
        return False


# Download directories
# Update 67: downloads hamesha save — asal jagah persistent DATA_DIR
# (Railway par /data volume) hai, taake website update/restart par
# downloads aur un ki list na ure. PLAYTUBE_DL_LEGACY=1 ho to purani
# home wali jagah istemal hoti hai.
if os.environ.get('PLAYTUBE_DL_LEGACY'):
    DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Playza")
else:
    DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

MP3_DIR = os.path.join(DOWNLOAD_DIR, "MP3")
MP4_DIR = os.path.join(DOWNLOAD_DIR, "MP4")
SOCIAL_DIR = os.path.join(DOWNLOAD_DIR, "Social")
DOCS_DIR = os.path.join(DOWNLOAD_DIR, "Documents")
UPLOADS_DIR = os.path.join(DOWNLOAD_DIR, "Uploads")
THUMBNAIL_DIR = os.path.join(DOWNLOAD_DIR, "Thumbnails")
SUBTITLE_DIR = os.path.join(DOWNLOAD_DIR, "Subtitles")

for dir_path in [MP3_DIR, MP4_DIR, SOCIAL_DIR, DOCS_DIR, UPLOADS_DIR, THUMBNAIL_DIR, SUBTITLE_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# Download management
download_progress = defaultdict(dict)
download_meta = {}
download_control = {}
_META_FILE = os.path.join(DOWNLOAD_DIR, 'download_meta.json')


def _save_download_meta():
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        with open(_META_FILE, 'w', encoding='utf-8') as _f:
            json.dump(download_meta, _f)
    except Exception:
        pass


def _load_download_meta():
    try:
        with open(_META_FILE, encoding='utf-8') as _f:
            return json.load(_f) or {}
    except Exception:
        return {}
downloaded_files = {}

DOWNLOADS_DB_FILE = os.path.join(DOWNLOAD_DIR, "downloads_db.json")


def load_downloads_db():
    try:
        if os.path.exists(DOWNLOADS_DB_FILE):
            with open(DOWNLOADS_DB_FILE, 'r') as f:
                return json.load(f)
    except:
        return {}
    return {}


def save_downloads_db():
    try:
        with open(DOWNLOADS_DB_FILE, 'w') as f:
            json.dump(downloaded_files, f, indent=2)
    except:
        pass


downloaded_files = load_downloads_db()

# ============ STORAGE AUTO-CLEANUP (Update 82 / v8) ============
# User ka rule: server ki jagah 80% bhar jaye to sab se PURANI mukammal
# downloads khud delete hoti rahen. Private folder wali aur chalti hui
# downloads kabhi auto-delete nahi hoti.
# Update 122 (user policy 2026-11-27): "800 MB ho to old 500 MB auto saf"
# — is chhote volume par wahi hisaab: 80% par safai shuru, 40% tak saaf,
# taake storage KABHI full na ho (97.8% wala haal dobara nahi).
STORAGE_LIMIT_PCT = 80.0
STORAGE_TARGET_PCT = 40.0


def _storage_info():
    try:
        _u = shutil.disk_usage(DATA_DIR)
        total, used, free = _u.total, _u.used, _u.free
    except Exception:
        total = used = free = 0
    dl_bytes = 0
    dl_count = 0
    for _v in downloaded_files.values():
        if _v.get('status', 'completed') == 'completed':
            dl_count += 1
            try:
                dl_bytes += int(_v.get('file_size') or 0)
            except Exception:
                pass
    pct = round(used * 100.0 / total, 1) if total else 0.0
    # Update 123: asal hisaab — volume par hai kya, folder/file ke
    # hisaab se; taake "0 downloads par itne MB kyun" khud dikh jaye.
    _bd = []
    _disk_dl_bytes = 0
    _disk_dl_files = 0
    try:
        for _name in os.listdir(DATA_DIR):
            _p = os.path.join(DATA_DIR, _name)
            _sz = 0
            if os.path.isfile(_p):
                try:
                    _sz = os.path.getsize(_p)
                except Exception:
                    _sz = 0
            elif os.path.isdir(_p):
                for _root, _dirs, _files in os.walk(_p):
                    for _f in _files:
                        try:
                            _sz += os.path.getsize(os.path.join(_root, _f))
                        except Exception:
                            pass
            if _name == 'downloads':
                _disk_dl_bytes = _sz
            if _sz > 0:
                _bd.append({'name': _name, 'mb': round(_sz / 1048576, 1)})
        _bd.sort(key=lambda x: -x['mb'])
        if os.path.isdir(DOWNLOAD_DIR):
            for _root, _dirs, _files in os.walk(DOWNLOAD_DIR):
                for _f in _files:
                    if not _f.endswith('.json'):
                        _disk_dl_files += 1
    except Exception:
        pass
    return {'total_mb': round(total / 1048576, 1), 'used_mb': round(used / 1048576, 1),
            'free_mb': round(free / 1048576, 1), 'used_pct': pct,
            'downloads_mb': round(dl_bytes / 1048576, 1), 'downloads_count': dl_count,
            'disk_downloads_mb': round(_disk_dl_bytes / 1048576, 1),
            'disk_files': _disk_dl_files, 'breakdown': _bd[:8]}


def _storage_cleanup(force=False):
    """80% se zyada bharne par sab se purani completed downloads delete
    karo jab tak istemal TARGET (40%) se neeche na aa jaye; sath mein
    record ke baghair padi purani files (orphans) bhi saaf hoti hain.
    (freed_mb, removed)."""
    if not force and not feature_enabled('storage_autoclean'):
        return (0, 0)
    freed = 0
    removed = 0
    try:
        info = _storage_info()
        if not info['total_mb'] or info['used_pct'] < STORAGE_LIMIT_PCT:
            return (0, 0)
        cands = []
        for _did, _v in downloaded_files.items():
            if _v.get('status', 'completed') != 'completed':
                continue
            if _v.get('private'):
                continue
            if not _v.get('file_path'):
                continue
            cands.append((str(_v.get('timestamp', '')), _did))
        cands.sort()
        for _ts, _did in cands:
            if _storage_info()['used_pct'] < STORAGE_TARGET_PCT:
                break
            _v = downloaded_files.get(_did)
            if not _v:
                continue
            _fp = _v.get('file_path')
            _sz = 0
            if _fp and os.path.exists(_fp):
                try:
                    _sz = os.path.getsize(_fp)
                    os.remove(_fp)
                except Exception:
                    pass
            downloaded_files.pop(_did, None)
            download_progress.pop(_did, None)
            if _did in download_meta:
                del download_meta[_did]
            freed += _sz
            removed += 1
        # Update 122: record ke baghair padi purani files (orphans)
        # bhi saaf — "0 files par volume full" wali halat dobara na ho.
        try:
            _known = set()
            for _v2 in downloaded_files.values():
                if _v2.get('file_path'):
                    _known.add(os.path.abspath(_v2['file_path']))
            _now = time.time()
            for _sub in ('', 'MP4', 'MP3', 'Social', 'Documents',
                         'Thumbnails', 'Subtitles', 'Uploads'):
                _dir = (os.path.join(DOWNLOAD_DIR, _sub)
                        if _sub else DOWNLOAD_DIR)
                if not os.path.isdir(_dir):
                    continue
                for _fn in os.listdir(_dir):
                    if _fn.endswith('.json'):
                        continue
                    _fp2 = os.path.join(_dir, _fn)
                    if not os.path.isfile(_fp2):
                        continue
                    if os.path.abspath(_fp2) in _known:
                        continue
                    _need = 86400 if _fn.endswith(('.part', '.ytdl',
                                                   '.tmp')) else 3600
                    try:
                        if _now - os.path.getmtime(_fp2) < _need:
                            continue
                        _sz2 = os.path.getsize(_fp2)
                        os.remove(_fp2)
                        freed += _sz2
                        removed += 1
                    except Exception:
                        pass
        except Exception:
            pass
        if removed:
            save_downloads_db()
            _save_download_meta()
            print('[Playza] Storage cleanup: %d purani downloads delete, %s MB khaali'
                  % (removed, round(freed / 1048576, 1)))
    except Exception as _e:
        print('[Playza] Storage cleanup error: %s' % _e)
    return (round(freed / 1048576, 1), removed)


def _storage_deep_clean():
    """Manual 'Abhi safai karein' (Update 123): jo kuch saaf ho
    sakta hai SAB — downloads ki files (Private aur chal rahi
    downloads ke siwa), bina-record files (har umar ki), purani
    versions ki bachi-khuchi media/temp files, OCR temp. Lazmi
    data (accounts DB, settings, cookies) ko haath nahi lagta.
    (freed_mb, removed)."""
    freed = 0
    removed = 0
    try:
        for _did in list(downloaded_files.keys()):
            _v = downloaded_files.get(_did) or {}
            if _v.get('private'):
                continue
            if str(_v.get('status', 'completed')).lower() in (
                    'downloading', 'processing', 'pending', 'queued'):
                continue
            _fp = _v.get('file_path')
            if _fp and os.path.exists(_fp):
                try:
                    freed += os.path.getsize(_fp)
                    os.remove(_fp)
                    removed += 1
                except Exception:
                    pass
            downloaded_files.pop(_did, None)
            download_progress.pop(_did, None)
            if _did in download_meta:
                del download_meta[_did]
        _known = set()
        for _v2 in downloaded_files.values():
            if _v2.get('file_path'):
                _known.add(os.path.abspath(_v2['file_path']))
        _media = ('.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.3gp',
                  '.mov', '.avi', '.part', '.ytdl', '.tmp', '.opus',
                  '.ogg', '.wav', '.flac')
        if os.path.isdir(DOWNLOAD_DIR):
            for _root, _dirs, _files in os.walk(DOWNLOAD_DIR):
                for _f in _files:
                    if _f.endswith('.json'):
                        continue
                    _fp2 = os.path.join(_root, _f)
                    if os.path.abspath(_fp2) in _known:
                        continue
                    try:
                        freed += os.path.getsize(_fp2)
                        os.remove(_fp2)
                        removed += 1
                    except Exception:
                        pass
        _keep = {'playtube_users.db', 'playtube_settings.json',
                 'yt_cookies.txt', 'ai_context.json'}
        for _name in os.listdir(DATA_DIR):
            if _name in _keep or _name == 'downloads':
                continue
            _p = os.path.join(DATA_DIR, _name)
            try:
                if os.path.isfile(_p):
                    if _name.lower().endswith(_media):
                        freed += os.path.getsize(_p)
                        os.remove(_p)
                        removed += 1
                elif os.path.isdir(_p):
                    _img_ok = (_name == 'ocr_tmp')
                    for _root, _dirs, _files in os.walk(_p):
                        for _f in _files:
                            _low = _f.lower()
                            if _low.endswith(_media) or (
                                    _img_ok and _low.endswith(
                                        ('.png', '.jpg', '.jpeg'))):
                                _fp3 = os.path.join(_root, _f)
                                freed += os.path.getsize(_fp3)
                                os.remove(_fp3)
                                removed += 1
            except Exception:
                pass
        save_downloads_db()
        _save_download_meta()
        print('[Playza] Deep clean: %d files delete, %s MB khaali'
              % (removed, round(freed / 1048576, 1)))
    except Exception as _e:
        print('[Playza] Deep clean error: %s' % _e)
    return (round(freed / 1048576, 1), removed)


def _storage_watch():
    while True:
        time.sleep(900)
        try:
            _storage_cleanup()
        except Exception:
            pass


try:
    _storage_cleanup()
except Exception:
    pass
threading.Thread(target=_storage_watch, daemon=True).start()


# Helper functions


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip('. ')
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def format_speed(speed_bytes):
    if speed_bytes > 1024 * 1024:
        return f"{speed_bytes / (1024 * 1024):.1f} MB/s"
    elif speed_bytes > 1024:
        return f"{speed_bytes / 1024:.1f} KB/s"
    else:
        return f"{speed_bytes} B/s"
# HTML Template
HTML = '''
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playza - All in One Downloader</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#4f46e5">
    <style>
        /* Playza base: purana interface code se bilkul delete ho chuka hai (v6) */
        html{background:#12101f}
        body{margin:0;padding:0}
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
</head>
<body>
    <!-- Visitor Counter -->
    <div style="text-align:center; padding:15px; background:#1a1a1a; margin-top:30px; border-top:1px solid #333;">
        <p style="color:#aaa; margin:0;">
            👥 Total Visits: <span id="visitorCount" style="color:#4CAF50; font-weight:bold;">0</span>
            <span style="color:#555; margin:0 6px;">|</span>
            🕒 <span id="liveClock" style="color:#4CAF50; font-weight:bold;">--:--:--</span>
        </p>
        <p style="color:#666; margin:5px 0 0; font-size:0.8rem;">
            © 2026 Playza - Coded by Chuza
        </p>
    </div>

    <script>
    (function(){ function tick(){ var el = document.getElementById('liveClock'); if(el){ el.textContent = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'}); } } tick(); setInterval(tick, 1000); })();
    </script>
    <script>
    fetch('/api/visitor-stats')
        .then(res => res.json())
        .then(data => {
            document.getElementById(
                'visitorCount').innerText = data.total_visitors;
        })
        .catch(err => {
            document.getElementById('visitorCount').innerText = '...';
        });
    </script>
<style id="v4-css">
  html,body{overflow-x:hidden!important;max-width:100%;color:var(--v4text);background:var(--v4bg)}
  :root{
    --v4bg:#12101f; --v4card:#1a1730; --v4border:#2c2852; --v4violet:#7c5cff;
    --v4violet2:#8b6dff; --v4teal:#14b8a6; --v4text:#eceaf6; --v4muted:#a49ec4;
    --v4nav:#17142c; --v4danger:#f87171;
  }
  #v4app{
    --v4bg:#12101f; --v4card:#1a1730; --v4border:#2c2852; --v4violet:#7c5cff;
    --v4violet2:#8b6dff; --v4teal:#14b8a6; --v4text:#eceaf6; --v4muted:#a49ec4;
    --v4nav:#17142c; --v4danger:#f87171;
    background:var(--v4bg); color:var(--v4text); min-height:100vh;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  }
  html[data-theme="light"] #v4app, html[data-theme="light"]{
    --v4bg:#f4f2fa; --v4card:#ffffff; --v4border:#cfc9e8; --v4text:#17142a;
    --v4muted:#453f63; --v4nav:#ffffff; --v4danger:#cf222e;
  }
  html[data-theme="light"] .v4-h{background:none;-webkit-text-fill-color:#5a3ee0;color:#5a3ee0}
  html[data-theme="light"] .v4-sect{color:#43307e}
  html[data-theme="light"] .v4-chip{color:#2e2a4a;border-color:#cfc9e8}
  html[data-theme="light"] .v4-tool .td{color:#453f63}
  #v4app *{box-sizing:border-box;max-width:100%}
  #v4app img{max-width:100%}
  .v4-head{display:flex;align-items:center;gap:8px;padding:12px 14px 4px;max-width:1100px;margin:0 auto}
  .v4-logo{font-size:24px;font-weight:800;background:linear-gradient(90deg,var(--v4violet2),var(--v4teal));-webkit-background-clip:text;background-clip:text;color:transparent;flex:1}
  .v4-iconbtn{background:var(--v4card);border:1px solid var(--v4border);color:var(--v4text);border-radius:999px;padding:7px 12px;font-size:12px;cursor:pointer}
  #v4-toptabs{position:sticky;top:0;z-index:50;display:flex;background:var(--v4bg);border-bottom:1px solid var(--v4border);max-width:1100px;margin:0 auto}
  #v4-toptabs button{flex:1;background:none;border:none;border-bottom:2px solid transparent;color:var(--v4muted);font-size:13px;padding:12px 2px;cursor:pointer;min-width:0}
  #v4-toptabs button.active{color:var(--v4text);font-weight:700;border-bottom:2px solid var(--v4violet)}
  #v4-main{padding:12px 12px 96px;max-width:1100px;margin:0 auto}
  .v4-view{display:none}
  .v4-view.active{display:block}
  .v4-searchrow{display:flex;align-items:center;background:var(--v4card);border:1px solid var(--v4border);border-radius:999px;padding:4px 4px 4px 14px;margin-bottom:14px}
  .v4-searchrow input{flex:1;background:none;border:none;outline:none;color:var(--v4text);font-size:14px;min-width:0}
  .v4-searchbtn{background:linear-gradient(135deg,var(--v4violet),#5a3ee0);color:#fff;border:none;width:38px;height:38px;border-radius:50%;cursor:pointer;font-size:15px;flex:none}
  .v4-h{font-size:15px;font-weight:800;margin:8px 2px 10px;background:linear-gradient(90deg,#a78bfa,#2dd4bf);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
  .v4-muted{color:var(--v4muted);font-size:12px}
  .v4-vcard{background:var(--v4card);border:1px solid var(--v4border);border-radius:14px;overflow:hidden;margin-bottom:12px}
  .v4-thumb{position:relative;aspect-ratio:16/9;background:#26224a;cursor:pointer}
  .v4-thumb img{width:100%;height:100%;object-fit:cover;display:block}
  .v4-dur{position:absolute;bottom:6px;right:8px;background:rgba(0,0,0,.85);color:#fff;font-size:11px;padding:1px 6px;border-radius:4px}
  .v4-vrow{display:flex;gap:10px;align-items:center;padding:10px 12px}
  .v4-vtexts{flex:1;min-width:0;cursor:pointer}
  .v4-vtitle{font-size:13.5px;font-weight:600;line-height:1.35}
  .v4-vmeta{font-size:11.5px;color:var(--v4muted);margin-top:3px}
  .v4-dlbtn{flex:none;width:40px;height:40px;border-radius:50%;background:var(--v4teal);color:#06231f;border:none;font-size:18px;font-weight:800;cursor:pointer}
  #v4-bottomnav{position:fixed;left:0;right:0;bottom:0;z-index:60;display:flex;background:var(--v4nav);border-top:1px solid var(--v4border);padding:6px 2px 8px}
  #v4-bottomnav button{flex:1;background:none;border:none;color:var(--v4muted);font-size:10px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;min-width:0;position:relative}
  #v4-bottomnav button i{font-size:18px}
  #v4-bottomnav button.active{color:var(--v4violet2);font-weight:700}
  .v4-badge{position:absolute;top:-2px;right:calc(50% - 20px);background:var(--v4teal);color:#06231f;font-size:9px;font-weight:800;border-radius:999px;padding:1px 5px;display:none}
  @media (min-width:1024px){
    #v4app{padding-left:212px}
    #v4-bottomnav{top:0;bottom:0;left:0;right:auto;width:212px;flex-direction:column;justify-content:flex-start;padding:76px 10px 10px;gap:6px;border-top:none;border-right:1px solid var(--v4border)}
    #v4-bottomnav button{flex:none;flex-direction:row;gap:10px;font-size:13px;padding:12px;border-radius:10px;width:100%}
    #v4-bottomnav button.active{background:rgba(124,92,255,.12)}
    #v4-main{padding-bottom:30px}
    .v4-feedgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .v4-feedgrid .v4-vcard{margin-bottom:0}
  }
  .v4-announce{background:linear-gradient(135deg,rgba(124,92,255,.25),rgba(20,184,166,.18));border:1px solid var(--v4violet);border-radius:12px;padding:10px 12px;font-size:13px;margin-bottom:12px;display:none}
  /* sheet + modal */
  .v4-wrap{position:fixed;inset:0;z-index:200;display:none;background:rgba(3,2,8,.9)}
  .v4-wrap.open{display:block}
  .v4-overlay{position:absolute;inset:0;background:rgba(4,2,16,.86)}
  .v4-sheet{position:absolute;left:0;right:0;bottom:0;min-height:44vh;max-height:84vh;overflow-y:auto;overscroll-behavior:contain;background:#0b0916;border-radius:18px 18px 0 0;padding:14px 16px 18px;max-width:560px;margin:0 auto;border:1px solid var(--v4border)}
  .v4-modalpanel{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:92%;max-width:420px;max-height:88vh;overflow-y:auto;background:var(--v4bg);border:1px solid var(--v4border);border-radius:16px;padding:18px 16px}
  .v4-fmtrow{display:flex;align-items:center;gap:11px;padding:11px 10px;cursor:pointer;border-radius:12px;border-left:4px solid transparent;margin:2px 0}
  .v4-fmtrow.sel{background:linear-gradient(90deg,rgba(124,92,255,.30),rgba(20,184,166,.20));border-left:4px solid var(--v4teal)}
  .v4-fmtrow.sel .nm{font-weight:800;color:#fff}
  .v4-fmtrow.sel .sz{color:#fff;font-weight:700}
  .v4-fmtrow .ic{width:34px;height:34px;border-radius:9px;background:#1a1730;border:1px solid var(--v4border);display:flex;align-items:center;justify-content:center;font-size:14px;flex:none}
  .v4-fmtrow.sel .ic{background:rgba(124,92,255,.35);border-color:var(--v4violet)}
  .v4-fmtrow .tx{flex:1;display:flex;flex-direction:column;gap:1px;min-width:0}
  .v4-fmtrow .nm{font-size:14px;font-weight:600}
  .v4-fmtrow .hint{font-size:11.5px;color:var(--v4muted)}
  .v4-fmtrow.sel .hint{color:#cfc9ee}
  .v4-fmtrow .sz{font-size:12.5px;color:var(--v4muted)}
  .v4-radio{width:22px;height:22px;border-radius:50%;border:2px solid #4a4570;flex:none;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:transparent}
  .v4-fmtrow.sel .v4-radio{background:linear-gradient(135deg,var(--v4violet),var(--v4teal));border-color:transparent;color:#fff}
  #v4-sheet-download{background:linear-gradient(90deg,var(--v4violet),var(--v4teal));border-radius:999px;font-size:16px;padding:15px;box-shadow:0 8px 22px rgba(124,92,255,.35)}
  .v4-sect{font-size:11px;font-weight:700;color:var(--v4violet2);letter-spacing:.6px;margin:14px 0 2px}
  .v4-dlstats{margin-top:10px;padding:10px 14px;border-radius:14px;background:linear-gradient(135deg,rgba(124,58,237,.22),rgba(13,148,136,.18));border:1px solid rgba(124,58,237,.35);font-weight:700;font-size:.9rem;color:var(--v4text)}
  .v4-empty{text-align:center;padding:34px 18px 26px;border:1px dashed rgba(148,140,255,.35);border-radius:18px;margin-top:8px;background:rgba(124,58,237,.05)}
  .v4-empty-ic{width:74px;height:74px;margin:0 auto 12px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#0d9488);display:flex;align-items:center;justify-content:center;font-size:34px}
  .v4-empty-t{font-size:1.05rem;font-weight:800;margin-bottom:4px}
  .v4-check{width:26px;height:26px;border-radius:50%;border:2px solid rgba(148,140,255,.55);display:flex;align-items:center;justify-content:center;color:transparent;font-size:.8rem;flex:none}
  .v4-check.on{background:#0d9488;border-color:#0d9488;color:#fff}
  .v4-dlrow.sel{outline:1px solid rgba(13,148,136,.75);background:rgba(13,148,136,.09)}
  .v4-selbar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:10px;padding:8px 10px;border-radius:14px;background:rgba(13,148,136,.12);border:1px solid rgba(13,148,136,.45)}
  .v4-admincard{background:var(--v4card);border:1px solid var(--v4border);border-radius:16px;padding:14px;margin-top:14px}
  .v4-filterpop{position:absolute;top:calc(100% + 6px);right:0;z-index:70;background:var(--v4card);border:1px solid var(--v4border);border-radius:14px;padding:6px;min-width:196px;box-shadow:0 14px 34px rgba(0,0,0,.45)}
  .v4-poprow{display:flex;width:100%;text-align:left;background:none;border:0;color:var(--v4text);padding:10px 12px;border-radius:10px;font-size:.9rem;cursor:pointer}
  .v4-poprow.on{background:rgba(124,58,237,.18);font-weight:700}
  .v4-bigbtn{display:block;width:100%;background:linear-gradient(135deg,var(--v4violet),#5a3ee0);color:#fff;text-align:center;font-weight:700;font-size:14px;border:none;border-radius:12px;padding:13px;cursor:pointer;margin-top:14px}
  .v4-bigbtn[disabled]{opacity:.45;cursor:not-allowed}
  .v4-btn2{display:inline-block;background:var(--v4card);border:1px solid var(--v4border);color:var(--v4text);border-radius:10px;padding:9px 14px;font-size:13px;cursor:pointer;text-decoration:none}
  .v4-input{width:100%;background:var(--v4card);border:1px solid var(--v4border);border-radius:10px;color:var(--v4text);padding:11px 12px;font-size:14px;margin-bottom:10px;outline:none}
  select.v4-input{appearance:auto}
  .v4-authtabs{display:flex;gap:8px;margin-bottom:14px}
  .v4-authtabs button{flex:1;padding:10px;border-radius:10px;border:1px solid var(--v4border);background:var(--v4card);color:var(--v4muted);cursor:pointer;font-size:13px}
  .v4-authtabs button.active{background:linear-gradient(135deg,var(--v4violet),#5a3ee0);color:#fff;font-weight:700}
  .v4-msg{font-size:12.5px;border-radius:10px;padding:9px 11px;margin-bottom:10px;display:none}
  .v4-msg.err{display:block;background:rgba(248,113,113,.14);color:var(--v4danger)}
  .v4-msg.ok{display:block;background:rgba(20,184,166,.14);color:var(--v4teal)}
  /* downloads */
  .v4-dlrow{display:flex;gap:10px;align-items:center;background:var(--v4card);border:1px solid var(--v4border);border-radius:12px;padding:9px 10px;margin-bottom:8px}
  .v4-dlrow2{display:flex;gap:11px;align-items:center;background:var(--v4card);border:1px solid var(--v4border);border-radius:14px;padding:9px 10px;margin-bottom:9px}
  .v4-dlrow2.sel{border-color:var(--v4teal)}
  .v4-dlthumb{position:relative;width:104px;height:60px;flex:none;border-radius:10px;overflow:hidden;background:#26224a;cursor:pointer}
  .v4-dlthumb img{width:100%;height:100%;object-fit:cover;display:block}
  .v4-dlthumb.music{width:58px;height:58px;border-radius:50%}
  .v4-playdot{position:absolute;right:5px;bottom:5px;width:24px;height:24px;border-radius:50%;background:rgba(0,0,0,.55);color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;border:1px solid rgba(255,255,255,.55)}
  .v4-dlthumb.music .v4-playdot{right:50%;bottom:50%;transform:translate(50%,50%)}
  .v4-dlinfo{flex:1;min-width:0;cursor:pointer}
  .v4-dltitle{font-size:13.5px;font-weight:600;line-height:1.32;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .v4-dlmeta{font-size:11.5px;color:var(--v4muted);margin-top:3px}
  .v4-dotbtn{background:none;border:none;color:var(--v4text);font-size:22px;line-height:1;padding:10px 7px;cursor:pointer;flex:none}
  .v4-menurow{display:flex;align-items:center;gap:12px;width:100%;padding:13px 4px;background:none;border:none;border-bottom:1px solid var(--v4border);color:var(--v4text);font-size:14px;cursor:pointer;text-align:left;text-decoration:none;box-sizing:border-box}
  /* Playza ka apna player frame (Update 59) */
  /* Shorts — Reels style, Playza design (Update 65) */
#v4-shorts{position:fixed;top:0;left:0;right:0;bottom:62px;background:#000;z-index:1200;display:none;overscroll-behavior:contain}
#v4-shorts.open{display:block}
#v4-shorts-track{height:100%;background:#000;overflow-y:auto;scroll-snap-type:y mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none;overscroll-behavior:contain;touch-action:pan-y}
#v4-shorts-track::-webkit-scrollbar{display:none}
#v4app{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
#v4app input,#v4app textarea{-webkit-user-select:text;user-select:text}
.v4-short{position:relative;height:100%;max-width:430px;margin:0 auto;scroll-snap-align:start;scroll-snap-stop:always;background:#000;overflow:hidden}
.v4-short img.bg,.v4-short video,.v4-short iframe{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border:0}
.v4-shorts-top{position:absolute;top:0;left:50%;transform:translateX(-50%);width:100%;max-width:430px;display:flex;align-items:center;padding:12px 14px;z-index:5;background:linear-gradient(180deg,rgba(0,0,0,.55),transparent);box-sizing:border-box}
.v4-shorts-logo{font-weight:800;font-size:17px;background:linear-gradient(90deg,var(--v4violet2),var(--v4teal));-webkit-background-clip:text;background-clip:text;color:transparent}
.v4-shorts-close{margin-left:auto;background:rgba(20,18,40,.55);border:1px solid var(--v4border);color:#fff;width:36px;height:36px;border-radius:50%;font-size:15px;cursor:pointer}
.v4-short-rail{position:absolute;right:10px;bottom:96px;display:flex;flex-direction:column;gap:15px;z-index:4;align-items:center}
.v4-sbtn{display:flex;flex-direction:column;align-items:center;gap:3px;background:none;border:0;cursor:pointer;color:#fff;font-size:11px;padding:0}
.v4-sbtn .ic{width:47px;height:47px;border-radius:50%;background:rgba(18,16,31,.55);border:1px solid rgba(255,255,255,.25);display:flex;align-items:center;justify-content:center;font-size:20px}
.v4-sbtn.liked .ic{background:linear-gradient(135deg,#e0245e,#ff5c8a);border-color:transparent}
.v4-short-meta{position:absolute;left:12px;right:78px;bottom:18px;z-index:4;color:#fff}
.v4-short-chan{display:flex;align-items:center;gap:8px;font-weight:700;font-size:14.5px;margin-bottom:7px;text-shadow:0 1px 6px rgba(0,0,0,.7)}
.v4-short-ava{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--v4violet),var(--v4teal));display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid rgba(255,255,255,.65);flex:none}
.v4-short-title{font-size:13.5px;line-height:1.45;text-shadow:0 1px 6px rgba(0,0,0,.7);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.v4-short-prog{position:absolute;top:0;left:0;height:3px;background:linear-gradient(90deg,var(--v4violet),var(--v4teal));z-index:6;width:0}
.v4-short-hint{position:absolute;left:50%;bottom:120px;transform:translateX(-50%);background:rgba(18,16,31,.8);border:1px solid var(--v4border);color:#fff;padding:7px 14px;border-radius:999px;font-size:12.5px;z-index:5;white-space:nowrap}
#v4-view-auth .v4-authpanel{margin:12px auto}
#v4-searchwrap{top:0;left:0;right:0;bottom:62px;background:#0b0916;z-index:300;overflow-y:auto}
.v4-authpanel{background:#12101f;border:1px solid #2c2852;border-radius:20px;max-width:400px}
.v4-authlogo{text-align:center;font-weight:800;font-size:21px;background:linear-gradient(90deg,#8b6dff,#14b8a6);-webkit-background-clip:text;background-clip:text;color:transparent}
.v4-authpill{background:rgba(20,184,166,.12);border:1px solid rgba(20,184,166,.45);color:#99f6e4;font-size:12.5px;line-height:1.45;padding:9px 12px;border-radius:12px;text-align:center;margin:10px 0 12px}
.v4-flabel{font-size:10.5px;font-weight:800;letter-spacing:.8px;color:var(--v4muted);margin:10px 0 5px}
.v4-seg{display:flex;background:#1a1730;border:1px solid var(--v4border);border-radius:999px;padding:4px}
.v4-seg button{flex:1;border:0;background:none;border-radius:999px;padding:9px 0;color:var(--v4muted);font-size:13px;cursor:pointer}
.v4-seg button.active{background:linear-gradient(90deg,var(--v4violet),var(--v4teal));color:#fff;font-weight:800}
.v4-codeboxes{display:flex;gap:7px;justify-content:center;margin:14px 0 4px}
.v4-cbox{width:42px;height:50px;text-align:center;font-size:20px;font-weight:800;background:#0b0916;border:1px solid var(--v4border);border-radius:12px;color:var(--v4text)}
.v4-cbox:focus{border-color:var(--v4teal);outline:none}
.v4-srow{grid-column:1 / -1;margin:2px 0 6px}
.v4-srow-h{font-size:14px;font-weight:800;margin:4px 0 8px}
.v4-srow-track{display:flex;gap:10px;overflow-x:auto;padding-bottom:6px;scrollbar-width:none}
.v4-srow-track::-webkit-scrollbar{display:none}
.v4-scard{flex:0 0 108px;cursor:pointer}
.v4-scard .im{position:relative;border-radius:12px;overflow:hidden;aspect-ratio:9/14;background:#26224a}
.v4-scard img{width:100%;height:100%;object-fit:cover;display:block}
.v4-scard .du{position:absolute;right:5px;bottom:5px;background:rgba(0,0,0,.65);color:#fff;font-size:10px;padding:1px 6px;border-radius:99px}
.v4-scard .ti{font-size:11.5px;line-height:1.3;margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.v4-scard .vw{font-size:10.5px;color:var(--v4muted)}
.v4-sbar{display:flex;gap:7px;flex-wrap:wrap;margin:8px 0 2px}
.v4-sbar button{padding:7px 13px;border-radius:999px;background:#1a1730;border:1px solid var(--v4border);color:var(--v4muted);font-size:12.5px;cursor:pointer}
.v4-sbar button.active{background:linear-gradient(90deg,var(--v4violet),var(--v4teal));color:#fff;font-weight:700;border-color:transparent}
.v4-sugrow{display:flex;align-items:center;gap:11px;padding:11px 4px;border-bottom:1px solid #211d42;cursor:pointer;font-size:14px}
.v4-sugrow .ic{color:var(--v4muted);font-size:13px}
.v4-sugrow b{color:#5eead4}
.v4-ailist{margin-top:8px;background:#17142e;color:#eceaf6;border:1px solid var(--v4border);border-radius:14px;padding:10px}
.v4-cand-box{max-height:300px;overflow-y:auto;border:1px solid var(--v4border);border-radius:10px;padding:2px 8px;margin-top:8px;background:rgba(0,0,0,.14);scrollbar-width:thin;scrollbar-color:#7c5cff #262250}
.v4-cand-box::-webkit-scrollbar{width:5px}
.v4-cand-box::-webkit-scrollbar-thumb{background:#7c5cff;border-radius:99px}
.v4-cand-box::-webkit-scrollbar-track{background:#262250;border-radius:99px}
.v4-job-box{max-height:320px}
.v4-cand-player{position:relative;margin-top:8px;border-radius:12px;overflow:hidden;background:#000;aspect-ratio:16/9}
.v4-cand-player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.v4-cand-player .v4-pband{position:absolute;top:6px;right:6px;z-index:2}
.v4-fixchips{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 8px}
.v4-bubble.v4-showalert{border:1.5px solid var(--v4teal)}
.v4-ailist-h{display:flex;align-items:center;gap:8px}
.v4-ailist-h .t{font-size:13.5px;font-weight:800;flex:1}
.v4-ailist-h .cnt{font-size:11.5px;font-weight:800;color:#5eead4;background:rgba(20,184,166,.13);border:1px solid rgba(20,184,166,.45);padding:3px 9px;border-radius:999px}
.v4-sabband{font-size:11.5px;font-weight:800;color:#fda4af;background:rgba(244,63,94,.12);border:1px solid rgba(244,63,94,.45);padding:4px 10px;border-radius:999px;cursor:pointer}
.v4-ai-row{margin-top:8px;background:#12101f;border:1px solid var(--v4border);border-radius:11px;padding:9px 10px}
.v4-ai-row.act{border-color:var(--v4violet)}
.v4-ai-r1{display:flex;align-items:center;gap:9px}
.v4-ai-ic{width:22px;height:22px;flex:none;border-radius:50%;background:#262250;color:#a49ec4;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800}
.v4-ai-ic.ok{background:var(--v4teal);color:#06231f}
.v4-ai-ic.dl{background:linear-gradient(135deg,var(--v4violet),var(--v4teal));color:#fff}
.v4-ai-ic.bad{background:rgba(244,63,94,.2);color:#fda4af}
.v4-ai-ic.stop{background:rgba(244,63,94,.15);color:#fda4af}
.v4-ai-t{flex:1;font-size:12.5px;font-weight:600;line-height:1.35;white-space:normal}
.v4-ai-r1 .pct{font-size:11px;color:#c4b0ff;font-weight:700}
.v4-ai-stop{width:26px;height:26px;flex:none;border-radius:50%;background:rgba(244,63,94,.15);border:1px solid rgba(244,63,94,.55);color:#fda4af;display:flex;align-items:center;justify-content:center;font-size:11px}
.v4-ai-bar{height:5px;border-radius:99px;background:#262250;margin-top:7px}
.v4-ai-bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--v4violet),var(--v4teal))}
.v4-short-spin{position:absolute;inset:0;display:none;align-items:center;justify-content:center;z-index:3}
.v4-short-spin i{width:40px;height:40px;border-radius:50%;border:3px solid rgba(255,255,255,.25);border-top-color:var(--v4teal);animation:v4spin .8s linear infinite}
  .v4-frame{margin-top:10px;border-radius:16px;padding:2px;background:linear-gradient(135deg,var(--v4violet),var(--v4teal));box-shadow:0 12px 34px rgba(0,0,0,.45)}
  body.v4-mini-on #v4-view-watch{display:block !important;position:fixed;right:10px;bottom:74px;left:auto;top:auto;width:200px;z-index:1350;padding:0;margin:0;background:transparent;pointer-events:none}
  body.v4-mini-on #v4-view-watch>*{display:none !important}
  body.v4-mini-on #v4-view-watch>#v4-frame{display:block !important;pointer-events:auto;margin-top:0}
  body.v4-mini-on #v4-mini-bar{display:flex !important}
  body.v4-mini-on #v4-view-watch .v4-fbadge{display:none !important}
  /* Update 132: mini ki asal geometry — 224px chaura, 16:9
     height fix; pehle frame lamba kala box banta tha aur
     video upar chhoti strip mein fasi nazar ati thi. */
  body.v4-mini-on #v4-view-watch{width:224px}
  body.v4-mini-on #v4-frame{height:128px}
  body.v4-mini-on #v4-frame .v4-framein{height:100%;aspect-ratio:auto}
  .v4-frow{display:flex;align-items:center;gap:8px;margin-bottom:10px}
  .v4-fact{font-size:11px;color:var(--v4teal)}
  .v4-fchip2{font-size:11px;background:var(--v4card);border:1px solid var(--v4border);color:var(--v4text);border-radius:999px;padding:6px 10px;cursor:pointer}
  .v4-fchip2.on{background:linear-gradient(135deg,#7c5cff,#5a3ee0);color:#fff;border-color:transparent;font-weight:700}
  .v4-fgroup{font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--v4muted);margin:12px 0 7px}
  .v4-dlfolder{border:1px solid var(--v4border);border-radius:14px;background:var(--v4card);overflow:hidden;margin-bottom:10px}
  .v4-dlf-head{display:flex;gap:10px;align-items:center;padding:10px;cursor:pointer}
  .v4-dlf-head .tt{flex:1;min-width:0}
  .v4-dlf-head .t1{font-weight:700;font-size:14px}
  .v4-dlf-head .t2{font-size:11px;color:var(--v4muted);margin-top:2px}
  .v4-dlf-th img{width:64px;height:36px;object-fit:cover;border-radius:8px;display:block}
  .v4-dlf-body{border-top:1px solid var(--v4border);padding:8px 10px 2px}
  .v4-framein{position:relative;border-radius:14px;overflow:hidden;aspect-ratio:16/9;background:#000}
  .v4-frame video{position:absolute;inset:0;width:100%;height:100%;background:#000}
  .v4-frame iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
  .v4-fbadge{position:absolute;top:10px;left:10px;background:rgba(0,0,0,.55);color:#fff;font-size:11px;font-weight:800;padding:5px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.35);pointer-events:none;z-index:3}
  .v4-fbig{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:64px;height:64px;border-radius:50%;border:none;background:linear-gradient(135deg,var(--v4violet),var(--v4teal));color:#fff;font-size:24px;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;transition:opacity .25s;z-index:3}
  .v4-fctrls{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:center;gap:9px;padding:8px 10px;background:linear-gradient(transparent,rgba(0,0,0,.78));transition:opacity .25s;z-index:3}
  .v4-fctrls.hide,.v4-fbig.hide{opacity:0;pointer-events:none}
  .v4-fbtn{background:none;border:none;color:#fff;font-size:16px;cursor:pointer;padding:4px 6px;flex:none}
  .v4-ftime{color:#fff;font-size:11px;flex:none;min-width:78px;text-align:center}
  #v4-fseek{flex:1;accent-color:var(--v4teal);height:4px;cursor:pointer}
  .v4-fspin{position:absolute;left:50%;top:50%;width:42px;height:42px;margin:-21px 0 0 -21px;border-radius:50%;border:4px solid rgba(255,255,255,.25);border-top-color:var(--v4teal);animation:v4spin .8s linear infinite;display:none;z-index:3}
  @keyframes v4spin{to{transform:rotate(360deg)}}
  .v4-footlinks{margin-top:24px;padding:16px 6px 6px;border-top:1px solid var(--v4border);text-align:center}
  .v4-footlinks a{color:var(--v4muted);text-decoration:none;font-size:12.5px;margin:0 8px}
  .v4-footlinks span{color:var(--v4border)}
  .v4-footlinks p{color:var(--v4muted);font-size:11.5px;margin:9px 0 0}
  .v4-dlrow img{width:64px;height:40px;object-fit:cover;border-radius:8px;flex:none;background:#26224a}
  .v4-dlrow .tt{flex:1;min-width:0}
  .v4-dlrow .t1{font-size:12.5px;font-weight:600}
  .v4-dlrow .t2{font-size:10.5px;color:var(--v4muted);margin-top:2px}
  .v4-bar{height:5px;border-radius:3px;background:var(--v4border);margin-top:6px}
  .v4-bar i{display:block;height:5px;border-radius:3px;background:linear-gradient(90deg,var(--v4violet),var(--v4teal))}
  .v4-roundbtn{flex:none;width:34px;height:34px;border-radius:50%;border:2px solid var(--v4violet);background:none;color:var(--v4text);display:inline-flex;align-items:center;justify-content:center;font-size:12px;cursor:pointer;text-decoration:none}
  .v4-roundbtn.teal{background:var(--v4teal);border-color:var(--v4teal);color:#06231f}
  /* tools / profile / admin rows */
  .v4-tools{display:flex;flex-direction:column;gap:8px}
  .v4-tool{display:grid;grid-template-columns:auto 1fr auto;grid-template-areas:"ic tn ch" "ic td ch";align-items:center;column-gap:11px;background:var(--v4card);border:1px solid var(--v4border);border-radius:13px;padding:8px 12px;cursor:pointer;text-align:left}
  .v4-tool .ic{grid-area:ic;width:37px;height:37px;border-radius:11px;background:linear-gradient(135deg,rgba(124,58,237,.35),rgba(13,148,136,.30));display:flex;align-items:center;justify-content:center;font-size:18px}
  .v4-tool .tn{grid-area:tn;font-size:13.5px;font-weight:700}
  .v4-tool .td{grid-area:td;font-size:11px;color:var(--v4muted);margin-top:0}
  .v4-tool::after{content:'›';grid-area:ch;font-size:21px;color:var(--v4muted);font-weight:700}
  .v4-row{display:flex;align-items:center;gap:10px;padding:12px 2px;border-bottom:1px solid var(--v4border);font-size:13.5px}
  .v4-row .grow{flex:1;min-width:0}
  .v4-row .val{font-size:12.5px;color:var(--v4teal)}
  .v4-switch{width:40px;height:23px;border-radius:999px;background:var(--v4border);position:relative;flex:none;cursor:pointer;border:none}
  .v4-switch i{position:absolute;top:3px;left:3px;width:17px;height:17px;border-radius:50%;background:var(--v4muted);transition:left .15s}
  .v4-switch.on{background:var(--v4violet)}
  .v4-switch.on i{left:20px;background:#fff}
  .v4-badge2{display:inline-block;font-size:10px;border-radius:999px;padding:2px 9px;background:var(--v4border);color:var(--v4muted)}
  .v4-badge2.owner{background:var(--v4violet);color:#fff;font-weight:700}
  .v4-badge2.prem{background:var(--v4teal);color:#06231f;font-weight:700}
  .v4-stats{display:flex;gap:8px;margin:8px 0 4px}
  .v4-stat{flex:1;background:var(--v4card);border:1px solid var(--v4border);border-radius:12px;padding:10px;text-align:center}
  .v4-stat b{font-size:17px;display:block}
  .v4-stat span{font-size:10px;color:var(--v4muted)}
  /* AI */
  .v4-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
  .v4-chip{font-size:11px;background:var(--v4card);border:1px solid var(--v4border);color:var(--v4text);border-radius:999px;padding:6px 10px;cursor:pointer}
  .v4-fchip.on{background:linear-gradient(135deg,#7c5cff,#5a3ee0);color:#fff;border-color:transparent;font-weight:700}
  .v4-dchip.on,.v4-mchip.on,.v4-kchip.on{background:linear-gradient(135deg,#7c5cff,#5a3ee0);color:#fff;border-color:transparent;font-weight:700}
  .v4-plbadge{position:absolute;left:8px;bottom:8px;background:rgba(124,92,255,.94);color:#fff;font-size:10.5px;font-weight:700;border-radius:999px;padding:3px 9px}
  .v4-bubble{max-width:88%;font-size:13px;border-radius:14px;padding:10px 12px;margin-bottom:10px;line-height:1.45}
  .v4-bubble.me{background:linear-gradient(135deg,var(--v4violet),#5a3ee0);color:#fff;margin-left:auto;border-bottom-right-radius:4px}
  .v4-bubble.ai{background:var(--v4card);border:1px solid var(--v4border);border-bottom-left-radius:4px}
  .v4-ep{display:flex;align-items:center;gap:7px;padding:6px 0;border-bottom:1px solid var(--v4border);font-size:12.5px}
  .v4-ep:last-child{border-bottom:none}
  .v4-ep .st{margin-left:auto;font-size:11px;color:var(--v4muted);text-align:right}
  .v4-airow{display:flex;align-items:center;background:var(--v4card);border:1px solid var(--v4border);border-radius:999px;padding:4px 4px 4px 14px;margin-top:6px}
  .v4-airow input{flex:1;background:none;border:none;outline:none;color:var(--v4text);font-size:13.5px;min-width:0}
  #v4-toast{position:fixed;bottom:92px;left:50%;transform:translateX(-50%);background:#26224a;color:#fff;font-size:13px;padding:10px 16px;border-radius:999px;z-index:300;display:none;max-width:92%;text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.4)}
  @media (min-width:1024px){ #v4-toast{bottom:30px} }
  .v4-plats{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .v4-plat{background:var(--v4card);border:1px solid var(--v4border);border-radius:12px;padding:12px;font-size:13px;cursor:pointer}
  .v4-deals{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .v4-deal{position:relative;background:var(--v4card);border:1px solid var(--v4border);border-radius:14px;padding:14px 12px;text-align:center}
  .v4-deal .em{font-size:34px;display:block}
  .v4-deal .nm{font-weight:700;font-size:13.5px;margin-top:6px}
  .v4-deal .old{opacity:.55;text-decoration:line-through;font-size:11.5px;display:block;margin-top:4px}
  .v4-deal .new{color:#2fe6c8;font-weight:800;font-size:14.5px;display:block}
  .v4-deal .bdg{position:absolute;top:8px;right:8px;background:#e63946;color:#fff;font-size:10px;font-weight:800;border-radius:999px;padding:2px 7px}
  .v4-deal .buy{display:block;margin-top:9px;background:linear-gradient(135deg,#7c5cff,#5a3ee0);color:#fff;border-radius:9px;padding:8px;font-size:12.5px;font-weight:700;text-decoration:none}
  .v4-ratecard{margin-top:22px;text-align:center;padding:20px 16px;border-radius:16px;background:linear-gradient(160deg,rgba(124,92,255,.16),rgba(20,184,166,.10));border:1px solid var(--v4border)}
  .v4-rate-t{font-size:16px;font-weight:800}
  .v4-rate-sub{margin:8px 4px 4px;font-size:12.5px;line-height:1.55}
  .v4-stars{font-size:34px;letter-spacing:6px;cursor:pointer;color:#4a4570;line-height:1.35;user-select:none}
  .v4-stars .on{color:#ffc93c;text-shadow:0 0 14px rgba(255,201,60,.45)}
  .v4-rate-msg{color:#2fe6c8;font-size:13px;min-height:18px;margin:6px 0 0;font-weight:600}
</style>

<div id="v4app">
  <div class="v4-head">
    <div class="v4-logo">Playza</div>
    <button class="v4-iconbtn" onclick="v4ToggleLang()" id="v4-langbtn">اردو</button>
    <button class="v4-iconbtn" onclick="v4ToggleTheme()" id="v4-themebtn">☀️ Light</button>
  </div>

  <nav id="v4-toptabs">
    <button data-tt="search" class="active" onclick="v4TopTab('search')">Search</button>
    <button data-tt="youtube" onclick="v4TopTab('youtube')">YouTube</button>
    <button data-tt="music" onclick="v4TopTab('music')">Music</button>
    <button data-tt="social" id="v4-tt-social" onclick="v4TopTab('social')">Social</button>
    <button data-tt="more" onclick="v4TopTab('more')">More</button>
  </nav>

  <main id="v4-main">
    <section id="v4-view-home" class="v4-view active">
      <div id="v4-announce" class="v4-announce"></div>
      <form class="v4-searchrow" onsubmit="v4HomeSearch(event)">
        <input id="v4-q-home" placeholder="Video dhundein ya link paste karein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit"><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>
      <div class="v4-chips">
        <button class="v4-chip v4-fchip on" data-w="home" data-t="all" onclick="v4SetFilter(this)">All</button>
        <button class="v4-chip v4-fchip" data-w="home" data-t="videos" onclick="v4SetFilter(this)">Videos</button>
        <button class="v4-chip v4-fchip" data-w="home" data-t="playlists" onclick="v4SetFilter(this)">Playlists</button>
        <button class="v4-chip v4-fchip" data-w="home" data-t="shorts" onclick="v4SetFilter(this)">Shorts</button>
        <button class="v4-chip v4-fchip" data-w="home" data-t="dramas" onclick="v4SetFilter(this)">🎭 Dramas</button>
        <button class="v4-chip v4-fchip" data-w="home" data-t="movies" onclick="v4SetFilter(this)">🎬 Movies</button>
        <button class="v4-chip v4-fchip" data-w="home" data-t="kids" onclick="v4SetFilter(this)">🧒 Kids</button>
      </div>
      <div class="v4-chips" id="v4-sub-home" style="display:none">
        <button class="v4-chip v4-dchip on" data-w="home" data-s="all" onclick="v4SetDramaSub(this)">All</button>
        <button class="v4-chip v4-dchip" data-w="home" data-s="pakistani" onclick="v4SetDramaSub(this)">🇵🇰 Pakistani</button>
        <button class="v4-chip v4-dchip" data-w="home" data-s="indian" onclick="v4SetDramaSub(this)">🇮🇳 Indian</button>
        <button class="v4-chip v4-dchip" data-w="home" data-s="turkish" onclick="v4SetDramaSub(this)">🇹🇷 Turkish</button>
        <button class="v4-chip v4-dchip" data-w="home" data-s="dubbed" onclick="v4SetDramaSub(this)">🌐 Dubbed</button>
      </div>
      <div class="v4-chips" id="v4-subm-home" style="display:none">
        <button class="v4-chip v4-mchip on" data-w="home" data-s="all" onclick="v4SetMovieSub(this)">All</button>
        <button class="v4-chip v4-mchip" data-w="home" data-s="indian" onclick="v4SetMovieSub(this)">🇮🇳 Indian</button>
        <button class="v4-chip v4-mchip" data-w="home" data-s="pakistani" onclick="v4SetMovieSub(this)">🇵🇰 Pakistani</button>
        <button class="v4-chip v4-mchip" data-w="home" data-s="punjabi" onclick="v4SetMovieSub(this)">🎬 Punjabi</button>
        <button class="v4-chip v4-mchip" data-w="home" data-s="english" onclick="v4SetMovieSub(this)">🇬🇧 English Hindi Dubbed</button>
        <button class="v4-chip v4-mchip" data-w="home" data-s="dubbed" onclick="v4SetMovieSub(this)">🎙️ Hindi Dubbed</button>
        <button class="v4-chip v4-mchip" data-w="home" data-s="south" onclick="v4SetMovieSub(this)">🎬 South Indian</button>
      </div>
      <div class="v4-chips" id="v4-subk-home" style="display:none">
        <button class="v4-chip v4-kchip on" data-w="home" data-s="all" onclick="v4SetKidsSub(this)">All</button>
        <button class="v4-chip v4-kchip" data-w="home" data-s="motupatlu" onclick="v4SetKidsSub(this)">🧒 Motu Patlu</button>
        <button class="v4-chip v4-kchip" data-w="home" data-s="cocomelon" onclick="v4SetKidsSub(this)">👶 Cocomelon</button>
        <button class="v4-chip v4-kchip" data-w="home" data-s="doraemon" onclick="v4SetKidsSub(this)">🤖 Doraemon</button>
        <button class="v4-chip v4-kchip" data-w="home" data-s="peppa" onclick="v4SetKidsSub(this)">🐷 Peppa Pig</button>
        <button class="v4-chip v4-kchip" data-w="home" data-s="tomjerry" onclick="v4SetKidsSub(this)">🐱 Tom & Jerry</button>
      </div>
      <div class="v4-frow"><span class="v4-fact" id="v4-fact-home"></span><button class="v4-chip" style="margin-left:auto" onclick="v4OpenFilters('home')">⛃ Filters</button></div>
      <div class="v4-h" id="v4-home-heading">Trending Videos</div>
      <div id="v4-searchbar" style="display:none"></div>
      <div id="v4-home-feed" class="v4-feedgrid"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-youtube" class="v4-view">
      <form class="v4-searchrow" onsubmit="v4FeedSearch(event,'youtube')">
        <input id="v4-q-youtube" placeholder="YouTube par search karein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit"><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>
      <div class="v4-chips">
        <button class="v4-chip v4-fchip on" data-w="youtube" data-t="all" onclick="v4SetFilter(this)">All</button>
        <button class="v4-chip v4-fchip" data-w="youtube" data-t="videos" onclick="v4SetFilter(this)">Videos</button>
        <button class="v4-chip v4-fchip" data-w="youtube" data-t="playlists" onclick="v4SetFilter(this)">Playlists</button>
        <button class="v4-chip v4-fchip" data-w="youtube" data-t="shorts" onclick="v4SetFilter(this)">Shorts</button>
        <button class="v4-chip v4-fchip" data-w="youtube" data-t="dramas" onclick="v4SetFilter(this)">🎭 Dramas</button>
        <button class="v4-chip v4-fchip" data-w="youtube" data-t="movies" onclick="v4SetFilter(this)">🎬 Movies</button>
        <button class="v4-chip v4-fchip" data-w="youtube" data-t="kids" onclick="v4SetFilter(this)">🧒 Kids</button>
      </div>
      <div class="v4-chips" id="v4-sub-youtube" style="display:none">
        <button class="v4-chip v4-dchip on" data-w="youtube" data-s="all" onclick="v4SetDramaSub(this)">All</button>
        <button class="v4-chip v4-dchip" data-w="youtube" data-s="pakistani" onclick="v4SetDramaSub(this)">🇵🇰 Pakistani</button>
        <button class="v4-chip v4-dchip" data-w="youtube" data-s="indian" onclick="v4SetDramaSub(this)">🇮🇳 Indian</button>
        <button class="v4-chip v4-dchip" data-w="youtube" data-s="turkish" onclick="v4SetDramaSub(this)">🇹🇷 Turkish</button>
        <button class="v4-chip v4-dchip" data-w="youtube" data-s="dubbed" onclick="v4SetDramaSub(this)">🌐 Dubbed</button>
      </div>
      <div class="v4-chips" id="v4-subm-youtube" style="display:none">
        <button class="v4-chip v4-mchip on" data-w="youtube" data-s="all" onclick="v4SetMovieSub(this)">All</button>
        <button class="v4-chip v4-mchip" data-w="youtube" data-s="indian" onclick="v4SetMovieSub(this)">🇮🇳 Indian</button>
        <button class="v4-chip v4-mchip" data-w="youtube" data-s="pakistani" onclick="v4SetMovieSub(this)">🇵🇰 Pakistani</button>
        <button class="v4-chip v4-mchip" data-w="youtube" data-s="punjabi" onclick="v4SetMovieSub(this)">🎬 Punjabi</button>
        <button class="v4-chip v4-mchip" data-w="youtube" data-s="english" onclick="v4SetMovieSub(this)">🇬🇧 English Hindi Dubbed</button>
        <button class="v4-chip v4-mchip" data-w="youtube" data-s="dubbed" onclick="v4SetMovieSub(this)">🎙️ Hindi Dubbed</button>
        <button class="v4-chip v4-mchip" data-w="youtube" data-s="south" onclick="v4SetMovieSub(this)">🎬 South Indian</button>
      </div>
      <div class="v4-chips" id="v4-subk-youtube" style="display:none">
        <button class="v4-chip v4-kchip on" data-w="youtube" data-s="all" onclick="v4SetKidsSub(this)">All</button>
        <button class="v4-chip v4-kchip" data-w="youtube" data-s="motupatlu" onclick="v4SetKidsSub(this)">🧒 Motu Patlu</button>
        <button class="v4-chip v4-kchip" data-w="youtube" data-s="cocomelon" onclick="v4SetKidsSub(this)">👶 Cocomelon</button>
        <button class="v4-chip v4-kchip" data-w="youtube" data-s="doraemon" onclick="v4SetKidsSub(this)">🤖 Doraemon</button>
        <button class="v4-chip v4-kchip" data-w="youtube" data-s="peppa" onclick="v4SetKidsSub(this)">🐷 Peppa Pig</button>
        <button class="v4-chip v4-kchip" data-w="youtube" data-s="tomjerry" onclick="v4SetKidsSub(this)">🐱 Tom & Jerry</button>
      </div>
      <div class="v4-frow"><span class="v4-fact" id="v4-fact-youtube"></span><button class="v4-chip" style="margin-left:auto" onclick="v4OpenFilters('youtube')">⛃ Filters</button></div>
      <div class="v4-h">YouTube Videos</div>
      <div id="v4-youtube-feed" class="v4-feedgrid"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-music" class="v4-view">
      <form class="v4-searchrow" onsubmit="v4FeedSearch(event,'music')">
        <input id="v4-q-music" placeholder="Gana / naat / song search karein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit"><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>
      <div class="v4-chips">
        <button class="v4-chip v4-fchip on" data-w="music" data-t="all" onclick="v4SetFilter(this)">All</button>
        <button class="v4-chip v4-fchip" data-w="music" data-t="videos" onclick="v4SetFilter(this)">Videos</button>
        <button class="v4-chip v4-fchip" data-w="music" data-t="mp3" onclick="v4SetFilter(this)">🎵 MP3</button>
        <button class="v4-chip v4-fchip" data-w="music" data-t="playlists" onclick="v4SetFilter(this)">Playlists</button>
        <button class="v4-chip v4-fchip" data-w="music" data-t="naat" onclick="v4SetFilter(this)">🌙 Naat</button>
      </div>
      <div class="v4-frow"><span class="v4-fact" id="v4-fact-music"></span><button class="v4-chip" style="margin-left:auto" onclick="v4OpenFilters('music')">⛃ Filters</button></div>
      <div class="v4-h">Music</div>
      <div id="v4-music-feed" class="v4-feedgrid"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-social" class="v4-view">
      <div class="v4-h">Social Media Downloader</div>
      <p class="v4-muted" style="margin:0 2px 10px">Kisi bhi app ka video link paste karein — Facebook, Instagram, TikTok, X, Pinterest waghera.</p>
      <form class="v4-searchrow" onsubmit="v4SocialFetch(event)">
        <input id="v4-social-url" placeholder="Video ka link yahan paste karein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit"><i class="fa-solid fa-link"></i></button>
      </form>
      <div id="v4-social-result"></div>
      <div class="v4-h" style="margin-top:16px">Platforms</div>
      <div class="v4-plats" id="v4-plat-list"><div class="v4-plat" data-p="YouTube" onclick="v4PlatClick(this)">YouTube<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Facebook" onclick="v4PlatClick(this)">Facebook<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Instagram" onclick="v4PlatClick(this)">Instagram<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="TikTok" onclick="v4PlatClick(this)">TikTok<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="WhatsApp Status" onclick="v4PlatClick(this)">WhatsApp Status<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Pinterest" onclick="v4PlatClick(this)">Pinterest<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Twitter / X" onclick="v4PlatClick(this)">Twitter / X<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="SnapChat" onclick="v4PlatClick(this)">SnapChat<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Threads" onclick="v4PlatClick(this)">Threads<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="DailyMotion" onclick="v4PlatClick(this)">DailyMotion<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="SoundCloud" onclick="v4PlatClick(this)">SoundCloud<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Vimeo" onclick="v4PlatClick(this)">Vimeo<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Reddit" onclick="v4PlatClick(this)">Reddit<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="LinkedIn" onclick="v4PlatClick(this)">LinkedIn<div class="v4-muted">Link paste karein</div></div><div class="v4-plat" data-p="Twitch" onclick="v4PlatClick(this)">Twitch<div class="v4-muted">Link paste karein</div></div></div>
    </section>

    <section id="v4-view-more" class="v4-view">
      <div class="v4-h">More</div>
      <div class="v4-row" onclick="v4Show('app')"><span>📱</span><div class="grow">Download App (Android / PC)</div><span>›</span></div>
      <div class="v4-row" onclick="v4Show('premium')"><span>👑</span><div class="grow">Premium</div><span>›</span></div>
      <div class="v4-row" onclick="v4Show('favorites')"><span>⭐</span><div class="grow">Favorites</div><span>›</span></div>
      <div class="v4-row" onclick="v4Show('history')"><span>🕘</span><div class="grow">Watch History</div><span>›</span></div>
      <div class="v4-row" onclick="window.location.href='/about'"><span>ℹ️</span><div class="grow">About Playza</div><span>›</span></div>
      <div class="v4-row" onclick="window.location.href='/contact'"><span>✉️</span><div class="grow">Contact</div><span>›</span></div>
      <div class="v4-ratecard">
        <div class="v4-rate-t">⭐ Playza ko Rate karein</div>
        <p class="v4-muted v4-rate-sub">Agar Playza aap ko pasand aya hai to stars de kar hamari hosla-afzai karein — aap ki rating se hi Playza aur behtar banta hai. Shukriya!</p>
        <div class="v4-stars" id="v4-stars"><span onclick="v4Rate(1)">★</span><span onclick="v4Rate(2)">★</span><span onclick="v4Rate(3)">★</span><span onclick="v4Rate(4)">★</span><span onclick="v4Rate(5)">★</span></div>
        <p class="v4-rate-msg" id="v4-rate-msg"></p>
      </div>
      <div class="v4-ratecard" id="v4-aboutcard">
        <div style="text-align:center;font-weight:800;font-size:20px;background:linear-gradient(90deg,#8b6dff,#14b8a6);-webkit-background-clip:text;background-clip:text;color:transparent">▶ Playza</div>
        <p class="v4-muted" style="text-align:center;margin-top:6px">All in One Video Downloader</p>
        <div class="v4-row"><span>🔢</span><div class="grow">Version</div><span class="val" id="v4-ver">53</span></div>
        <div class="v4-row"><span>👨‍💻</span><div class="grow">Developer</div><span class="val">Chuza</span></div>
        <div class="v4-row"><span>🌐</span><div class="grow">Website</div><span class="val">playza.up.railway.app</span></div>
        <div class="v4-row"><span>💻</span><div class="grow">PC App</div><span class="val">Chrome / Edge → Install</span></div>
        <p class="v4-muted" style="text-align:center">PC par Playza app: Chrome ya Edge mein ye website kholein → address bar mein Install (⊕) icon ya menu (⋮) → <b>Install Playza</b> dabayein. Desktop par Playza ki app ban jayegi — downloads seedha PC par honge.</p>
      </div>
      <div class="v4-footlinks">
        <a href="/privacy-policy">Privacy Policy</a><span>|</span><a href="/terms-of-service">Terms of Service</a><span>|</span><a href="/about">About</a><span>|</span><a href="/contact">Contact</a>
        <p>© 2026 Playza - All Rights Reserved</p>
      </div>
    </section>

    <section id="v4-view-watch" class="v4-view">
      <button class="v4-btn2" onclick="v4Back()">← Back</button>
      <div class="v4-frame" id="v4-frame"><div class="v4-framein">
        <iframe id="v4-player" src="about:blank" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen style="position:absolute;inset:0;width:100%;height:100%;border:0"></iframe>
        <div class="v4-fbadge">▶ Playza</div>
        <div class="v4-fbadge" style="left:auto;right:10px">HD</div>
        <div id="v4-mini-bar" style="display:none;position:absolute;top:6px;right:6px;gap:6px;z-index:8"><button class="v4-iconbtn" style="width:30px;height:30px;font-size:13px;padding:0" onclick="event.stopPropagation();v4Show('watch')">⤢</button><button class="v4-iconbtn" style="width:30px;height:30px;font-size:13px;padding:0" onclick="event.stopPropagation();v4MiniClose()">✕</button></div>
      </div></div>
      <div class="v4-h" id="v4-watch-title" style="margin-top:12px"></div>
      <p class="v4-muted" id="v4-watch-channel"></p>
      <div style="display:flex;gap:8px;align-items:stretch;margin-top:10px"><button class="v4-bigbtn" style="flex:1;margin:0" onclick="v4WatchDownload()">⬇ Download</button><button class="v4-iconbtn" id="v4-watch-fav" style="border-radius:999px;padding:0 16px;font-size:16px" onclick="v4WatchFav()">♡</button><button class="v4-iconbtn" style="border-radius:999px;padding:0 16px;font-size:16px" onclick="v4WatchShare()">↗</button><button class="v4-btn2" id="v4-watch-float" style="display:none;border-radius:999px" onclick="v4FloatPlay()">📺 Floating</button></div>
      <div id="v4-watch-msg" class="v4-muted" style="display:none;margin-top:10px"></div>
      <div class="v4-h" style="margin-top:18px">Related Videos</div>
      <div id="v4-related" class="v4-feedgrid"></div>
    </section>

    <section id="v4-view-downloads" class="v4-view">
      <div id="v4-dl-filterwrap" style="display:flex;align-items:center;gap:8px;position:relative">
        <div class="v4-h" style="flex:1;margin:4px 2px">Downloads</div>
        <button class="v4-iconbtn" onclick="v4DlFilterToggle()" title="Type ke hisab se filter karein"><i class="fa-solid fa-filter"></i> Filter</button>
        <button class="v4-iconbtn" onclick="v4DlSelectMode()" title="Kai videos ek sath chunein — select mode">🗑</button>
        <div id="v4-dl-typechips" class="v4-filterpop" style="display:none"></div>
      </div>
      <div id="v4-dl-selbar" class="v4-selbar" style="display:none"></div>
      <div class="v4-searchrow" style="margin-top:6px">
        <input id="v4-dl-filter" placeholder="Downloads me dhundein..." oninput="v4RenderDownloads()" autocomplete="off">
        <button class="v4-searchbtn" type="button"><i class="fa-solid fa-magnifying-glass"></i></button>
      </div>
      <div id="v4-dl-stats" class="v4-dlstats" style="display:none"></div>
      <div class="v4-sect">DOWNLOADING <span id="v4-dl-actcount"></span></div>
      <div id="v4-phone-active"></div>
      <div id="v4-dl-active"><p class="v4-muted">Koi download nahi chal raha</p></div>
      <div class="v4-sect">DOWNLOADED</div>
      <div id="v4-phone-done"></div>
      <div id="v4-dl-done"><p class="v4-muted">Abhi tak koi download nahi</p></div>
    </section>

    <section id="v4-view-failed" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">❌ Fail Hui <span id="v4-dl-failcount"></span></div>
      <p class="v4-muted">Jo downloads kisi wajah se fail ho gayin, wo yahan hain — dobara try ya delete yahin se ho ga. Downloads page par sirf mukammal (complete) downloads dikhti hain.</p>
      <div id="v4-phone-failed"></div>
      <div id="v4-dl-failed"><p class="v4-muted">Koi fail download nahi</p></div>
    </section>

    <section id="v4-view-ai" class="v4-view">
      <div class="v4-h">✦ AI Assistant</div>
      <div class="v4-chips" id="v4-ai-chips">
        <button class="v4-chip" onclick="v4AiChip(this)">Motu Patlu episode 1, 3GP download karo</button>
        <button class="v4-chip" onclick="v4AiChip(this)">Naat sharif MP3 320K me download karo</button>
        <button class="v4-chip" onclick="v4AiChip(this)">Drama episode 1 to 3, 360p download karo</button>
        <button class="v4-chip" onclick="v4AiChip(this)">Sab se chhoti quality me gana download karo</button>
      </div>
      <p class="v4-muted" id="v4-ai-tip" style="margin:2px 0 8px"></p>
      <div class="v4-fixchips" id="v4-ai-fixchips">
        <button class="v4-chip" type="button" onclick="v4AiTazaOpen()">🆕 Aaj ki taza</button>
        <button class="v4-chip" type="button" onclick="v4AiShowsPanel()">📺 Mere Shows</button>
        <button class="v4-chip" type="button" onclick="v4AiChannelPanel()">📂 Channel mode</button>
      </div>
      <div id="v4-ai-msgs">
        <div class="v4-bubble ai">Assalam-o-Alaikum! Main Playza AI hoon. Bas command likhein — masalan kisi drama ke episodes, gana, ya quality bata kar download karwayein. Downloads background me one by one chalte rahen ge, aur tayyar videos Downloads me milen ge.</div>
      </div>
      <form class="v4-airow" onsubmit="v4AiSend(event)">
        <button class="v4-searchbtn" type="button" title="Pic bhejein — AI parh kar download kare ga" onclick="v4$('v4-ai-file').click()">📎</button>
        <input id="v4-ai-input" placeholder="AI ko command likhein, link ya pic bhejein..." autocomplete="off">
        <input type="file" id="v4-ai-file" accept="image/*" style="display:none" onchange="v4AiImage(this)">
        <button class="v4-searchbtn" type="button" id="v4-ai-mic" title="Bol kar command dein" style="display:none" onclick="v4AiMic()">🎤</button>
        <button class="v4-searchbtn" type="submit">➤</button>
      </form>
    </section>

    <section id="v4-view-playlist" class="v4-view">
      <button class="v4-btn2" onclick="v4Back()">← Back</button>
      <div class="v4-h" id="v4-playlist-title" style="margin-top:10px">Playlist</div>
      <p class="v4-muted" id="v4-playlist-count"></p>
      <div id="v4-playlist-feed" class="v4-feedgrid"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>
    <section id="v4-view-tools" class="v4-view">
      <div class="v4-h">Tools</div>
      <div class="v4-tools">
        <div class="v4-tool" onclick="v4Show('social')"><div class="ic">💬</div><div class="tn">Status Saver</div><div class="td">WhatsApp / social status link se</div></div>
        <div class="v4-tool" onclick="v4Show('favorites')"><div class="ic">⭐</div><div class="tn">Favorites</div><div class="td">Pasandeeda videos</div></div>
        <div class="v4-tool" onclick="v4Show('history')"><div class="ic">🕘</div><div class="tn">Watch History</div><div class="td">Dekhi hui videos</div></div>
        <div class="v4-tool" id="v4-tool-premium" onclick="v4Show('premium')"><div class="ic">👑</div><div class="tn">Premium</div><div class="td">HD quality + plans</div></div>
        <div class="v4-tool" onclick="v4Show('app')"><div class="ic">📱</div><div class="tn">Download App</div><div class="td">Android APK + PC</div></div>
        <div class="v4-tool" onclick="v4ShareApp()"><div class="ic">🔗</div><div class="tn">Share App</div><div class="td">Doston ko bhejein</div></div>
        <div class="v4-tool" onclick="v4Show('settings')"><div class="ic">⚙️</div><div class="tn">Settings</div><div class="td">Folder, quality, language, theme</div></div>
        <div class="v4-tool" onclick="window.location.href='/contact'"><div class="ic">✉️</div><div class="tn">Contact</div><div class="td">Madad aur rabta</div></div>
        <div class="v4-tool" onclick="v4Show('private')"><div class="ic">🔒</div><div class="tn">Private Folder</div><div class="td">PIN ke peeche chhupi downloads</div></div>
        <div class="v4-tool" onclick="v4Show('failed')"><div class="ic">❌</div><div class="tn">Fail Hui Downloads</div><div class="td">Fail hui — dobara try / delete</div></div>
        <div class="v4-tool" onclick="v4Show('compress')"><div class="ic">🗜️</div><div class="tn">Video Compressor</div><div class="td">Quality wohi — sirf size kam</div></div>
        <div class="v4-tool" onclick="v4Show('sysclean')"><div class="ic">🧹</div><div class="tn">System clean</div><div class="td">Playza ka apna kachra saaf karein</div></div>
        <div class="v4-tool" onclick="v4Show('ytaccount')"><div class="ic">▶️</div><div class="tn">YouTube account</div><div class="td">Apna YouTube link karein — History, Playlists, Watch later</div></div>
      </div>
    </section>

    <section id="v4-view-compress" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">🗜️ Video Compressor</div>
      <p class="v4-muted">Video ki quality aur HD bilkul wohi rahe gi — sirf file ka size kam hoga, taake storage bache aur bhejni asan ho. Nayi chhoti file Downloads mein "(Chhoti)" naam se aye gi; purani file bhi rahe gi.</p>
      <div id="v4-cmp-list"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-sysclean" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">🧹 System clean</div>
      <p class="v4-muted">Ye sirf Playza ka apna kachra saaf karta hai — cache, purani AI chat, aur server par padi Playza ki temp files. Aap ki downloads aur dusri apps ko haath nahi lagta.</p>
      <div id="v4-clean-body"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-ytaccount" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">▶️ YouTube account</div>
      <div id="v4-yt-body"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-private" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">🔒 Private Folder</div>
      <div id="v4-priv-body"></div>
    </section>

    <section id="v4-view-settings" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">Settings</div>
      <div class="v4-sect">DOWNLOAD</div>
      <div class="v4-row"><div class="grow">Download folder<div class="v4-muted">Phone me is naam ke folder me jayengi (app me)</div></div><input id="v4-set-folder" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"></div>
      <div class="v4-row" id="v4-set-dlpath-row" style="display:none"><div class="grow">Download folder (APK)<div class="v4-muted" id="v4-set-dlpath">Downloads/Playza</div></div><button class="v4-btn2" onclick="v4PickFolder()">Folder chunein</button></div>
      <div class="v4-row"><div class="grow">Default quality</div><select id="v4-set-quality" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"><option>144p</option><option>240p</option><option>360p</option><option>480p</option><option>720p</option><option>3gp</option></select></div>
      <div class="v4-row"><div class="grow">Ek sath downloads</div><select id="v4-set-conc" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"><option>1</option><option>2</option><option>3</option><option>5</option></select></div>
      <div class="v4-row"><div class="grow">Speed limit</div><select id="v4-set-speed" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"><option>Unlimited</option><option>1 MB/s</option><option>2 MB/s</option><option>5 MB/s</option></select></div>
      <div class="v4-row"><div class="grow">Sirf Wi-Fi par download</div><button class="v4-switch" id="v4-set-wifi" onclick="v4ToggleSetting('wifiOnly',this)"><i></i></button></div>
      <div class="v4-row"><div class="grow">Download in background<div class="v4-muted">Off ho to app peeche jane par nayi downloads start nahi hongi aur HD (merge) downloads ruk jayengi</div></div><button class="v4-switch" id="v4-set-bgdl" onclick="v4ToggleSetting('bgDl',this)"><i></i></button></div>
      <div class="v4-sect">APP</div>
      <div class="v4-row"><div class="grow">Language</div><span class="val" id="v4-set-lang">English</span><button class="v4-btn2" onclick="v4ToggleLang()">Badlein</button></div>
      <div class="v4-row"><div class="grow">Theme</div><span class="val" id="v4-set-theme">Dark</span><button class="v4-btn2" onclick="v4ToggleTheme()">Badlein</button></div>
      <div class="v4-row"><div class="grow">Download mukammal ho to batao<div class="v4-muted">Notification ke liye</div></div><button class="v4-switch" id="v4-set-notify" onclick="v4ToggleSetting('notify',this)"><i></i></button></div>
      <div class="v4-row"><div class="grow">Auto Miniplayer<div class="v4-muted">Video chalti ho aur aap dusre page par jayen to chhota player neeche set ho jata hai (AI tab mein nahi)</div></div><button class="v4-switch" id="v4-set-mini" onclick="v4ToggleSetting('autoMini',this)"><i></i></button></div>
      <div class="v4-row" id="v4-set-floating-row" style="display:none"><div class="grow">Floating Button (sirf APK app me)<div class="v4-muted" id="v4-set-floating-note">Dusri apps ke upar Playza bubble - tap karne par clipboard link ka download page khulta hai</div></div><button class="v4-switch" id="v4-set-floating" onclick="v4ToggleFloating(this)"><i></i></button></div>
    </section>

    <section id="v4-view-profile" class="v4-view">
      <div class="v4-h">Profile</div>
      <div id="v4-profile-body"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-admin" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('profile')">← Profile</button>
      <div class="v4-h" style="margin-top:10px">Admin Panel <span class="v4-badge2 owner">Owner</span></div>
      <div id="v4-admin-body"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-favorites" class="v4-view">
      <div class="v4-h">⭐ Favorites</div>
      <div id="v4-fav-list" class="v4-feedgrid"></div>
    </section>

    <section id="v4-view-history" class="v4-view">
      <div style="display:flex;align-items:center;gap:8px">
        <div class="v4-h" style="flex:1;margin:4px 2px">Watch History</div>
        <button class="v4-iconbtn" onclick="v4ClearHistory()">🗑 Clear</button>
      </div>
      <div id="v4-history-list" class="v4-feedgrid"></div>
    </section>

    <section id="v4-view-premium" class="v4-view">
      <div class="v4-h">👑 Playza Premium</div>
      <div id="v4-premium-body"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-app" class="v4-view">
      <div class="v4-h">Download Playza App</div>
      <div class="v4-vcard" style="padding:16px">
        <div style="font-size:28px">📱</div>
        <div class="v4-h" style="margin:8px 0 4px">Android App</div>
        <p class="v4-muted">Playza ko phone ki home screen par app ki tarah lagayein — full-screen, saare features ke sath.</p>
        <button class="v4-bigbtn" onclick="v4InstallPWA()">Install App (PWA)</button>
        <div id="v4-apk-area" style="margin-top:10px"><p class="v4-muted">APK check ho raha hai...</p></div>
      </div>
      <div class="v4-vcard" style="padding:16px">
        <div style="font-size:28px">💻</div>
        <div class="v4-h" style="margin:8px 0 4px">PC (Windows) App</div>
        <p class="v4-muted">PC par Playza install karein — desktop icon banega aur apni window me khule ga (Chrome / Edge).</p>
        <button class="v4-bigbtn" onclick="v4InstallPC()">Install for PC</button>
      </div>
    </section>
<!-- Auth view (v9: page ke andar hi, alag layer nahi) -->
<section id="v4-view-auth" class="v4-view">
  <div class="v4-modalpanel v4-authpanel">
    <div class="v4-authlogo">▶ Playza</div>
    <div style="display:flex;align-items:center">
      <div class="v4-h" style="flex:1;margin:0;text-align:center" id="v4-auth-heading">Create Account</div>
      <button class="v4-iconbtn" onclick="v4CloseAuth()">✕</button>
    </div>
    <div class="v4-authpill" id="v4-auth-pill">Video dekhne aur download karne ke liye pehle account banayein ya sign in karein.</div>
    <div id="v4-auth-msg" class="v4-msg"></div>
    <div class="v4-authtabs v4-seg">
      <button id="v4-tab-signin" class="active" onclick="v4AuthTab('signin')">Sign In</button>
      <button id="v4-tab-signup" onclick="v4AuthTab('signup')">Create Account</button>
    </div>

    <form id="v4-form-signin" onsubmit="v4SignIn(event)">
      <div class="v4-flabel">GMAIL</div>
      <input class="v4-input" id="v4-li-email" placeholder="Email ya username" autocomplete="username">
      <div class="v4-flabel">PASSWORD</div>
      <input class="v4-input" id="v4-li-pass" type="password" placeholder="Password" autocomplete="current-password">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Sign In</button>
      <p style="text-align:center;margin-top:10px"><a href="#" onclick="v4ShowForgot(event)" style="color:var(--v4violet2);font-size:12.5px">Password bhool gaye?</a></p>
    </form>

    <form id="v4-form-signup" style="display:none" onsubmit="v4SignUpStart(event)">
      <div class="v4-flabel">USERNAME</div>
      <input class="v4-input" id="v4-su-name" placeholder="Username" autocomplete="username">
      <div class="v4-flabel">GMAIL</div>
      <input class="v4-input" id="v4-su-email" placeholder="Gmail (email)" autocomplete="email">
      <div class="v4-flabel">PASSWORD</div>
      <input class="v4-input" id="v4-su-pass" type="password" placeholder="Password (kam se kam 6)" autocomplete="new-password">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Gmail par Code Bhejein</button>
    </form>
    <form id="v4-form-verify" style="display:none" onsubmit="v4SignUpVerify(event)">
      <div class="v4-authpill">📧 Code bheja gaya: <b id="v4-verify-email"></b></div>
      <div class="v4-codeboxes">
        <input class="v4-cbox" id="v4-cb0" inputmode="numeric" autocomplete="one-time-code">
        <input class="v4-cbox" id="v4-cb1" inputmode="numeric">
        <input class="v4-cbox" id="v4-cb2" inputmode="numeric">
        <input class="v4-cbox" id="v4-cb3" inputmode="numeric">
        <input class="v4-cbox" id="v4-cb4" inputmode="numeric">
        <input class="v4-cbox" id="v4-cb5" inputmode="numeric">
      </div>
      <p class="v4-muted" id="v4-code-timer" style="text-align:center">Code khatam honay mein: 10:00</p>
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Verify — Account Banayein</button>
      <p class="v4-muted" style="text-align:center;margin-top:10px">Code nahi aya? <a href="#" onclick="v4ResendCode();return false;">Dobara bhejein</a></p>
      <p class="v4-muted" style="text-align:center;margin-top:2px"><a href="#" onclick="v4BackToSignup();return false;">← Wapas — details badlein</a></p>
    </form>

    <form id="v4-form-forgot" style="display:none" onsubmit="v4ForgotStart(event)">
      <p class="v4-muted">Apni Gmail likhein — password reset code bheja jaye ga.</p>
      <input class="v4-input" id="v4-fg-email" placeholder="Gmail (email)" autocomplete="email">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Code Bhejein</button>
    </form>
    <form id="v4-form-reset" style="display:none" onsubmit="v4ForgotReset(event)">
      <div class="v4-codeboxes">
        <input class="v4-cbox" id="v4-rb0" inputmode="numeric" autocomplete="one-time-code">
        <input class="v4-cbox" id="v4-rb1" inputmode="numeric">
        <input class="v4-cbox" id="v4-rb2" inputmode="numeric">
        <input class="v4-cbox" id="v4-rb3" inputmode="numeric">
        <input class="v4-cbox" id="v4-rb4" inputmode="numeric">
        <input class="v4-cbox" id="v4-rb5" inputmode="numeric">
      </div>
      <div class="v4-flabel">NAYA PASSWORD</div>
      <input class="v4-input" id="v4-fg-pass" type="password" placeholder="Naya password (kam se kam 6)" autocomplete="new-password">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Password Badlein</button>
    </form>
  </div>
</section>

  </main>

  <button id="v4-refresh-btn" title="Refresh — nayi videos" onclick="v4RefreshCurrent()" style="display:none;position:fixed;right:14px;bottom:84px;z-index:65;width:46px;height:46px;border-radius:50%;border:1px solid var(--v4border);background:linear-gradient(135deg,#7c5cff,#14b8a6);color:#fff;font-size:20px;box-shadow:0 6px 18px rgba(0,0,0,.45);cursor:pointer">↻</button>
  <nav id="v4-bottomnav">
    <button data-bn="home" class="active" onclick="v4Show('home')"><i class="fa-solid fa-house"></i>Home</button>
    <button data-bn="downloads" onclick="v4Show('downloads')"><i class="fa-solid fa-download"></i>Downloads<span class="v4-badge" id="v4-dl-badge">0</span></button>
    <button data-bn="ai" id="v4-bn-ai" onclick="v4Show('ai')"><i class="fa-solid fa-robot"></i>AI Assistant</button>
    <button data-bn="tools" onclick="v4Show('tools')"><i class="fa-solid fa-screwdriver-wrench"></i>Tools</button>
    <button data-bn="profile" onclick="v4Show('profile')"><i class="fa-solid fa-user"></i>Profile</button>
  </nav>
</div>

<!-- Download sheet -->
<div id="v4-searchwrap" class="v4-wrap">
  <div style="max-width:640px;margin:0 auto;padding:12px">
    <div style="display:flex;align-items:center;gap:9px;background:#17142e;border:1px solid #2c2852;border-radius:12px;padding:4px 8px 4px 4px">
      <button class="v4-iconbtn" onclick="v4CloseSearch()">←</button>
      <input id="v4-sq" placeholder="Video ka naam likhein..." autocomplete="off" style="flex:1;background:none;border:0;color:var(--v4text);font-size:15px;padding:9px 2px;outline:none">
      <button class="v4-iconbtn" onclick="v4ClearSearchInput()">✕</button>
    </div>
    <div id="v4-sugg"></div>
  </div>
</div>

<div id="v4-filterwrap" class="v4-wrap">
  <div class="v4-overlay" onclick="v4CloseFilters()"></div>
  <div class="v4-sheet">
    <div class="v4-h" style="margin-top:0">Filters</div>
    <div class="v4-fgroup">Type</div>
    <div class="v4-chips" style="margin-bottom:0">
      <button class="v4-fchip2" data-fg="type" data-fv="all" onclick="v4FilterPick(this)">All</button>
      <button class="v4-fchip2" data-fg="type" data-fv="videos" onclick="v4FilterPick(this)">Videos</button>
      <button class="v4-fchip2" data-fg="type" data-fv="shorts" onclick="v4FilterPick(this)">Shorts</button>
      <button class="v4-fchip2" data-fg="type" data-fv="playlists" onclick="v4FilterPick(this)">Playlists</button>
      <button class="v4-fchip2" data-fg="type" data-fv="movies" onclick="v4FilterPick(this)">Movies</button>
    </div>
    <div class="v4-fgroup">Upload date</div>
    <div class="v4-chips" style="margin-bottom:0">
      <button class="v4-fchip2" data-fg="date" data-fv="any" onclick="v4FilterPick(this)">Anytime</button>
      <button class="v4-fchip2" data-fg="date" data-fv="today" onclick="v4FilterPick(this)">Today</button>
      <button class="v4-fchip2" data-fg="date" data-fv="week" onclick="v4FilterPick(this)">This week</button>
      <button class="v4-fchip2" data-fg="date" data-fv="month" onclick="v4FilterPick(this)">This month</button>
      <button class="v4-fchip2" data-fg="date" data-fv="year" onclick="v4FilterPick(this)">This year</button>
    </div>
    <div class="v4-fgroup">Duration</div>
    <div class="v4-chips" style="margin-bottom:0">
      <button class="v4-fchip2" data-fg="dur" data-fv="any" onclick="v4FilterPick(this)">Any</button>
      <button class="v4-fchip2" data-fg="dur" data-fv="short" onclick="v4FilterPick(this)">Under 3 min</button>
      <button class="v4-fchip2" data-fg="dur" data-fv="mid" onclick="v4FilterPick(this)">3–20 min</button>
      <button class="v4-fchip2" data-fg="dur" data-fv="long" onclick="v4FilterPick(this)">Over 20 min</button>
    </div>
    <div class="v4-fgroup">Sort by</div>
    <div class="v4-chips" style="margin-bottom:0">
      <button class="v4-fchip2" data-fg="sort" data-fv="rel" onclick="v4FilterPick(this)">Relevance</button>
      <button class="v4-fchip2" data-fg="sort" data-fv="pop" onclick="v4FilterPick(this)">Popularity</button>
      <button class="v4-fchip2" data-fg="sort" data-fv="new" onclick="v4FilterPick(this)">Newest</button>
    </div>
    <div class="v4-fgroup">Features</div>
    <div class="v4-chips" style="margin-bottom:0">
      <button class="v4-fchip2" data-fg="feat" data-fv="live" onclick="v4FilterPick(this)">Live</button>
      <button class="v4-fchip2" data-fg="feat" data-fv="4k" onclick="v4FilterPick(this)">4K</button>
      <button class="v4-fchip2" data-fg="feat" data-fv="hd" onclick="v4FilterPick(this)">HD</button>
      <button class="v4-fchip2" data-fg="feat" data-fv="cc" onclick="v4FilterPick(this)">Subtitles</button>
    </div>
    <div style="display:flex;gap:8px;margin-top:16px">
      <button class="v4-btn2" style="flex:1" onclick="v4FilterClear()">Clear</button>
      <button class="v4-bigbtn" style="flex:2;margin:0" onclick="v4FilterApply()">Apply</button>
    </div>
  </div>
</div>

<div id="v4-sheetwrap" class="v4-wrap">
  <div class="v4-overlay" onclick="v4CloseSheet()"></div>
  <div class="v4-sheet">
    <div style="display:flex;gap:10px;align-items:center">
      <img id="v4-sheet-thumb" style="width:76px;height:46px;object-fit:cover;border-radius:8px;background:#26224a" alt="">
      <div style="flex:1;min-width:0">
        <div id="v4-sheet-title" style="font-size:13.5px;font-weight:600"></div>
        <div id="v4-sheet-channel" class="v4-muted"></div>
      </div>
      <button class="v4-iconbtn" onclick="v4CloseSheet()">✕</button>
    </div>
    <div class="v4-h" style="margin-top:12px">Download karein</div>
    <div id="v4-sheet-list"><p class="v4-muted">Formats load ho rahe hain...</p></div>
    <button class="v4-bigbtn" id="v4-sheet-download" onclick="v4SheetDownload()">Download</button>
  </div>
</div>

<!-- Downloads 3-dot menu (Update 51/58) -->
<div id="v4-dlmenuwrap" class="v4-wrap">
  <div class="v4-overlay" onclick="v4CloseDlMenu()"></div>
  <div class="v4-sheet">
    <div style="display:flex;gap:10px;align-items:center">
      <img id="v4-dlmenu-thumb" style="width:76px;height:46px;object-fit:cover;border-radius:8px;background:#26224a" alt="">
      <div style="flex:1;min-width:0">
        <div id="v4-dlmenu-title" style="font-size:13.5px;font-weight:600"></div>
        <div id="v4-dlmenu-meta" class="v4-muted"></div>
      </div>
      <button class="v4-iconbtn" onclick="v4CloseDlMenu()">✕</button>
    </div>
    <div id="v4-dlmenu-list" style="margin-top:8px"></div>
  </div>
</div>

<!-- Downloaded file ka player (Update 57) -->
<div id="v4-audiobar" style="display:none;position:fixed;left:8px;right:8px;bottom:76px;z-index:950;background:#17142e;border:1px solid #2c2852;border-radius:14px;padding:9px 11px;box-shadow:0 12px 32px rgba(0,0,0,.55)">
  <div style="display:flex;align-items:center;gap:10px">
    <button id="v4-abtn" onclick="v4AudioToggle()" style="width:42px;height:42px;flex:none;border:0;border-radius:50%;background:linear-gradient(135deg,#7c5cff,#14b8a6);color:#fff;font-size:15px;cursor:pointer">▶</button>
    <div style="flex:1;min-width:0">
      <div id="v4-atitle" style="color:#eceaf6;font-size:13.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Audio song</div>
      <div id="v4-astat" style="color:#a49ec4;font-size:11.5px">Load ho raha hai...</div>
    </div>
    <button onclick="v4AudioDownload()" title="Download" style="width:38px;height:38px;flex:none;border:1px solid #2c2852;border-radius:50%;background:#1a1730;color:#eceaf6;font-size:15px;cursor:pointer">⬇</button>
    <button onclick="v4AudioClose()" title="Band karein" style="width:38px;height:38px;flex:none;border:1px solid #2c2852;border-radius:50%;background:#1a1730;color:#eceaf6;font-size:14px;cursor:pointer">✕</button>
  </div>
  <audio id="v4-audio" preload="auto"></audio>
</div>
<div id="v4-shorts">
  <div id="v4-shorts-track"></div>
  <div class="v4-shorts-top"><span class="v4-shorts-logo">▶ Playza Shorts</span><button class="v4-shorts-close" onclick="v4CloseShorts()">✕</button></div>
</div>
<div id="v4-playerwrap" class="v4-wrap">
  <div class="v4-overlay" onclick="v4ClosePlayer()"></div>
  <div class="v4-modalpanel" style="max-width:640px;width:94%">
    <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
      <div id="v4-player-title" style="flex:1;font-size:13.5px;font-weight:600"></div>
      <button class="v4-iconbtn" onclick="v4ClosePlayer()">✕</button>
    </div>
    <video id="v4-filevideo" controls playsinline style="width:100%;max-height:64vh;border-radius:12px;background:#000"></video>
  </div>
</div>

<div id="v4-toast"></div>

<script id="v4-js">
/* ================= Playza v4 UI logic ================= */
const v4State = {user:null, config:null, view:'home',
  settings:{folder:'Playza', defQuality:'360p', maxConc:3, speed:'Unlimited', wifiOnly:false, notify:true, bgDl:true, autoMini:true},
  loadedYt:0, loadedMu:0, platsDone:0};
try{ const _s = JSON.parse(localStorage.getItem('pt_v4_settings') || 'null'); if(_s) v4State.settings = Object.assign(v4State.settings, _s); }catch(e){}
const v4Videos = {};
let v4Pending = null, v4SignupEmail = '', v4Current = null, v4PrevView = 'home';
let v4AuthReturn = 'home';
let v4DlData = {progress:{}, list:[]};
let v4Sheet = {id:null, sel:null};
let v4SocialInfo = null;
const v4JobTimers = {};

function v4$(id){ return document.getElementById(id); }
function v4Esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
async function v4Fetch(url, opts){ const c = new AbortController(); const t = setTimeout(function(){ c.abort(); }, 30000); const o = Object.assign({}, opts || {}, {signal: c.signal}); try{ const r = await fetch(url, o); let d = null; try{ d = await r.json(); }catch(e){} clearTimeout(t); return {ok:r.ok, status:r.status, data:d}; }catch(e){ clearTimeout(t); return {ok:false, status:0, data:null}; } }
function v4Post(url, body){ return v4Fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body || {})}); }
function v4Toast(msg){ const t = v4$('v4-toast'); t.textContent = msg; t.style.display = 'block'; clearTimeout(t._h); t._h = setTimeout(function(){ t.style.display = 'none'; }, 3400); }
function v4Dur(s){ if(!s) return ''; s = parseInt(s); if(!s || s < 0) return ''; const m = Math.floor(s/60), ss = s % 60, h = Math.floor(m/60); if(h) return h + ':' + String(m%60).padStart(2,'0') + ':' + String(ss).padStart(2,'0'); return m + ':' + String(ss).padStart(2,'0'); }
function v4Views(n){ if(!n) return ''; n = parseInt(n); if(!n) return ''; if(n >= 1000000) return (n/1000000).toFixed(1).replace('.0','') + 'M views'; if(n >= 1000) return (n/1000).toFixed(1).replace('.0','') + 'K views'; return n + ' views'; }
function v4MB(b){ if(!b) return ''; return (b/(1024*1024)).toFixed(1) + ' MB'; }
function v4Img(id){ return '<img loading="lazy" src="https://i.ytimg.com/vi/' + id + '/hqdefault.jpg" data-vid="' + id + '" data-stage="0" onerror="v4ImgFb(this)" alt="">'; }
function v4ImgFb(img){ const id = img.getAttribute('data-vid'); const st = parseInt(img.getAttribute('data-stage') || '0'); if(st === 0){ img.setAttribute('data-stage','1'); img.src = 'https://i.ytimg.com/vi/' + id + '/mqdefault.jpg'; } else if(st === 1){ img.setAttribute('data-stage','2'); img.src = 'https://i.ytimg.com/vi/' + id + '/default.jpg'; } else { img.onerror = null; img.style.opacity = '0.25'; } }

/* ---------- navigation ---------- */
const V4_TTMAP = {home:'search', youtube:'youtube', music:'music', social:'social', more:'more'};
const V4_BNMAP = {home:'home', watch:'home', downloads:'downloads', ai:'ai', tools:'tools', settings:'tools', favorites:'tools', history:'tools', premium:'tools', app:'tools', profile:'profile', admin:'profile', auth:'profile'};
function v4RefreshCurrent(){
  const map = {home:'v4-home-feed', youtube:'v4-youtube-feed', music:'v4-music-feed'};
  const feedId = map[v4State.view]; if(!feedId) return;
  v4FeedSession = Math.random().toString(36).slice(2, 10);
  const st = v4FeedState[feedId];
  const q = (st && st.q) || (v4State.view === 'youtube' ? 'trending videos' : (v4State.view === 'music' ? 'trending songs' : 'trending'));
  const t = (st && st.type) || 'videos';
  const sb = (st && st.sub) || '';
  v4Toast('Refresh ho raha hai — nayi videos aa rahi hain');
  /* Update 129: refresh usi option ke ANDAR — sub (masalan
     Dramas > Pakistani) bhi sath jata hai, back nahi hota. */
  v4LoadFeed(feedId, q, t, sb);
  window.scrollTo(0, 0);
}
function v4CloseAllOverlays(){ try{ v4CloseShorts(); }catch(e){} try{ v4CloseSearch(); }catch(e){} try{ v4CloseSheet(); }catch(e){} try{ v4ClosePlayer(); }catch(e){} try{ v4CloseDlMenu(); }catch(e){} }
function v4MiniOn(){ document.body.classList.add('v4-mini-on'); }
function v4MiniOff(){ document.body.classList.remove('v4-mini-on'); }
function v4MiniClose(){ v4MiniOff(); v4FrameStop(); }
function v4Show(view){
  v4CloseAllOverlays();
  /* Update 122: Auto Miniplayer — watch se dusre page par jane par
     video band nahi hoti; chhota player neeche set ho jata hai.
     AI tab mein miniplayer NAHI (user) — wahan video band hoti hai. */
  if(view !== 'watch'){
    if(v4FrameId && v4State.view === 'watch' && view !== 'ai' && v4State.settings.autoMini !== false) v4MiniOn();
    else { v4MiniOff(); v4FrameStop(); }
  } else v4MiniOff();
  if(view === 'home' && v4State.view === 'home'){ v4FeedSession = Math.random().toString(36).slice(2, 10); const hh = v4$('v4-home-heading'); if(hh) hh.textContent = 'Trending Videos'; v4SearchState.q = ''; v4RenderSearchBar(); v4SetSearchBoxes(''); v4LoadFeed('v4-home-feed', 'trending'); }
  const rb = v4$('v4-refresh-btn'); if(rb) rb.style.display = (view === 'home' || view === 'youtube' || view === 'music') ? 'block' : 'none';
  document.querySelectorAll('.v4-view').forEach(function(s){ s.classList.remove('active'); });
  const el = v4$('v4-view-' + view); if(el) el.classList.add('active');
  v4State.view = view;
  document.querySelectorAll('#v4-toptabs button').forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-tt') === (V4_TTMAP[view] || '')); });
  document.querySelectorAll('#v4-bottomnav button').forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-bn') === (V4_BNMAP[view] || '')); });
  if(view === 'ai'){ const _sb109 = function(){ window.scrollTo(0, document.body.scrollHeight); }; setTimeout(_sb109, 50); setTimeout(_sb109, 400); }
  else window.scrollTo(0, 0);
  if(view === 'downloads' || view === 'failed'){ v4LoadDownloads(); try{ v4PhoneDlRender(); v4PhonePollStart(); }catch(e){} } else v4PhonePollStop();
  if(view === 'ai'){ v4RenderAiChips(); v4AiShowCheck(); }
  if(view === 'private') v4RenderPrivate();
  if(view === 'compress') v4RenderCompress();
  if(view === 'sysclean') v4RenderSysClean();
  if(view === 'ytaccount') v4RenderYtAccount();
  if(view === 'profile') v4RenderProfile();
  if(view === 'admin') v4RenderAdmin();
  if(view === 'favorites') v4RenderFavs();
  if(view === 'history') v4LoadHistory();
  if(view === 'premium') v4RenderPremium();
  if(view === 'app') v4CheckApk();
  if(view === 'settings') v4FillSettings();
  if(view === 'youtube' && !v4State.loadedYt){ v4State.loadedYt = 1; v4LoadFeed('v4-youtube-feed', 'trending videos'); }
  if(view === 'music' && !v4State.loadedMu){ v4State.loadedMu = 1; v4LoadFeed('v4-music-feed', 'trending songs'); }
  if((view === 'social' || view === 'more') && !v4State.platsDone) v4RenderPlats();
}
function v4TopTab(t){ if(t === 'search'){ v4Show('home'); v4OpenSearch(); return; } v4Show(t); }

/* ---------- feeds & cards (ONE renderer — Bug #1/#2) ---------- */
function v4AgeText(it){ if(!it) return ''; if(it.age_text) return String(it.age_text).replace('Streamed ', ''); const ts = it.age_ts; if(ts){ const s = Math.max(0, Math.floor(Date.now() / 1000) - Number(ts)); if(s < 3600) return Math.max(1, Math.floor(s / 60)) + ' minutes ago'; if(s < 86400) return Math.floor(s / 3600) + ' hours ago'; if(s < 2592000) return Math.floor(s / 86400) + ' days ago'; if(s < 31536000) return Math.floor(s / 2592000) + ' months ago'; return Math.floor(s / 31536000) + ' years ago'; } return ''; }
function v4Norm(item){ const id = (item.id && item.id.videoId) || item.id || item.video_id || ''; const sn = item.snippet || {}; return {videoId:id, title:sn.title || item.title || '', channel:sn.channelTitle || item.channel || '', duration:item.duration || '', views:item.view_count || '', age:v4AgeText(item), live: !!item.live}; }
let v4AudioCards = false;
let v4AudioId = '';
let v4AudioWired = false;
let v4NaActive = false;
let v4NaPoll = null;
function v4NativeAudio(){ return !!(window.PlayTubeApp && PlayTubeApp.playAudio); }
function v4NaStopPoll(){ if(v4NaPoll){ clearInterval(v4NaPoll); v4NaPoll = null; } }
function v4NaStartPoll(){
  v4NaStopPoll();
  v4NaPoll = setInterval(function(){
    if(!v4NaActive || !v4AudioId){ v4NaStopPoll(); return; }
    let s = null;
    try{ s = JSON.parse(PlayTubeApp.audioState()); }catch(e){}
    if(!s) return;
    if(s.playing){ v4$('v4-astat').textContent = 'Chal raha hai 🎵'; v4$('v4-abtn').textContent = '❚❚'; }
    else if(s.ended){ v4$('v4-abtn').textContent = '▶'; v4$('v4-astat').textContent = 'Khatam ho gaya'; }
    else if(s.ready){ v4$('v4-abtn').textContent = '▶'; v4$('v4-astat').textContent = 'Ruka hua hai'; }
  }, 700);
}
function v4PlayAudio(id){
  const v = v4Videos[id] || {videoId:id, title:''};
  v4AudioId = id;
  const bar2 = v4$('v4-audiobar'); if(!bar2) return;
  bar2.style.display = '';
  v4$('v4-atitle').textContent = v.title || 'Audio song';
  v4$('v4-astat').textContent = 'Load ho raha hai...';
  v4$('v4-abtn').textContent = '❚❚';
  if(v4NativeAudio()){
    v4NaActive = true;
    try{ const _su = location.origin + '/api/stream/' + id; const _st = 'https://i.ytimg.com/vi/' + id + '/hqdefault.jpg'; if(PlayTubeApp.playAudio2) PlayTubeApp.playAudio2(_su, v.title || 'Audio song', _st); else PlayTubeApp.playAudio(_su, v.title || 'Audio song'); }catch(e){}
    v4NaStartPoll();
    return;
  }
  v4NaActive = false;
  const au = v4$('v4-audio');
  if(!v4AudioWired){
    v4AudioWired = true;
    au.addEventListener('playing', function(){ v4$('v4-astat').textContent = 'Chal raha hai 🎵'; v4$('v4-abtn').textContent = '❚❚'; });
    au.addEventListener('waiting', function(){ v4$('v4-astat').textContent = 'Load ho raha hai...'; });
    au.addEventListener('pause', function(){ v4$('v4-abtn').textContent = '▶'; });
    au.addEventListener('ended', function(){ v4$('v4-abtn').textContent = '▶'; v4$('v4-astat').textContent = 'Khatam ho gaya'; });
    au.addEventListener('error', function(){ if(v4AudioId){ const vid = v4AudioId; const vv = v4Videos[vid] || {videoId:vid, title:'', channel:''}; v4AudioClose(); v4Toast('Ye song seedha nahi chala — player mein khul raha hai'); v4OpenWatch(vv); } });
  }
  au.src = '/api/stream/' + id;
  const p = au.play(); if(p && p.catch) p.catch(function(){});
}
function v4AudioToggle(){ if(v4NaActive){ let s = null; try{ s = JSON.parse(PlayTubeApp.audioState()); }catch(e){} if(s && s.playing){ try{ PlayTubeApp.pauseAudio(); }catch(e){} v4$('v4-abtn').textContent = '▶'; } else if(s && s.ended){ v4PlayAudio(v4AudioId); } else { try{ PlayTubeApp.resumeAudio(); }catch(e){} v4$('v4-abtn').textContent = '❚❚'; } return; } const au = v4$('v4-audio'); if(!au || !v4AudioId) return; if(au.paused){ const p = au.play(); if(p && p.catch) p.catch(function(){}); } else au.pause(); }
function v4AudioClose(){ if(v4NaActive){ try{ PlayTubeApp.stopAudio(); }catch(e){} v4NaActive = false; v4NaStopPoll(); } const au = v4$('v4-audio'); if(au){ try{ au.pause(); au.removeAttribute('src'); au.load(); }catch(e){} } const b3 = v4$('v4-audiobar'); if(b3) b3.style.display = 'none'; v4AudioId = ''; }
function v4AudioDownload(){ if(v4AudioId) v4OpenSheet(v4AudioId, true); }
function v4SheetAudio(ev, id){ if(ev) ev.stopPropagation(); v4OpenSheet(id, true); }
function v4Mp3Click(id){ v4PlayAudio(id); }
function v4CardHTML(v){
  /* Update 141: LIVE video par views wala number asal
     mein dekhne walon (watching) ki tadaad hoti hai —
     YouTube bhi waisa hi likhta hai; aam video par asal
     views + age, jo na mile wo hissa hi nahi dikhta. */
  const meta = v.live
    ? [v4Esc(v.channel), v.views ? (v4Views(v.views).replace(' views', '') + ' watching') : '🔴 Live'].filter(Boolean).join(' • ')
    : [v4Esc(v.channel), v4Views(v.views), v4Esc(v.age || '')].filter(Boolean).join(' • ');
  const tap = v4AudioCards ? 'v4Mp3Click' : 'v4WatchClick';
  const badge = v4AudioCards ? '<span class=\"v4-dur\" style=\"left:6px;right:auto\">🎵 MP3</span>' : (v.live ? '<span class=\"v4-dur\" style=\"left:6px;right:auto;background:#dc2626;color:#fff\">🔴 LIVE</span>' : '');
  return '<div class=\"v4-vcard\"><div class=\"v4-thumb\" data-id=\"' + v.videoId + '\" onclick=\"' + tap + '(this.dataset.id)\">' + v4Img(v.videoId) + badge + (v.duration ? '<span class=\"v4-dur\">' + v4Dur(v.duration) + '</span>' : '') + '</div>' +
    '<div class=\"v4-vrow\"><div class=\"v4-vtexts\" data-id=\"' + v.videoId + '\" onclick=\"' + tap + '(this.dataset.id)\"><div class=\"v4-vtitle\">' + v4Esc(v.title) + '</div>' + (meta ? '<div class=\"v4-vmeta\">' + meta + '</div>' : '') + '</div>' +
    '<button class=\"v4-dlbtn\" title=\"Download\" data-id=\"' + v.videoId + '\" onclick=\"' + (v4AudioCards ? 'v4SheetAudio' : 'v4DlClick') + '(event, this.dataset.id)\">' + (v4AudioCards ? '🎵' : '↓') + '</button></div></div>';
}
const v4StripRaw = {};
let v4ShortsSeedItems = null, v4ShortsSeedStart = '';
function v4OpenShortFromStrip(el){
  const id = el.getAttribute('data-id'); if(!id) return;
  const track0 = el.closest('.v4-srow-track');
  const items = [];
  if(track0){ track0.querySelectorAll('.v4-scard').forEach(function(c){ const cid = c.getAttribute('data-id'); if(cid && v4StripRaw[cid]) items.push(v4StripRaw[cid]); }); }
  if(!items.length && v4StripRaw[id]) items.push(v4StripRaw[id]);
  v4ShortsSeedItems = items; v4ShortsSeedStart = id;
  v4OpenShorts(v4SearchState.q || '');
  const track = v4$('v4-shorts-track');
  if(track && v4ShortsSeedItems){
    v4ShortsSeedItems.forEach(function(it){
      if(!it.id || !it.id.videoId) return;
      v4ShortsItems[it.id.videoId] = it;
      if(track.querySelector('[data-vid="' + it.id.videoId + '"]')) return;
      const div = document.createElement('div'); div.innerHTML = v4ShortCard(it);
      const sec = div.firstChild; track.appendChild(sec);
      if(v4ShortsObs) v4ShortsObs.observe(sec);
    });
    const sec0 = track.querySelector('[data-vid="' + v4ShortsSeedStart + '"]');
    if(sec0){ track.scrollTop = sec0.offsetTop; v4ShortActivate(sec0); }
  }
  v4ShortsSeedItems = null;
}
function v4ShortStripHTML(items){
  if(!items || !items.length) return '';
  let h = '<div class="v4-srow"><div class="v4-srow-h">⚡ Shorts</div><div class="v4-srow-track">';
  items.forEach(function(it){ const v = v4Norm(it); if(!v.videoId) return; v4Videos[v.videoId] = v; v4StripRaw[v.videoId] = it; h += '<div class="v4-scard" data-id="' + v.videoId + '" onclick="v4OpenShortFromStrip(this)"><div class="im"><img loading="lazy" src="https://i.ytimg.com/vi/' + v.videoId + '/hqdefault.jpg" alt="">' + (v.duration ? '<span class="du">' + v4Dur(v.duration) + '</span>' : '') + '</div><div class="ti">' + v4Esc(v.title) + '</div><div class="vw">' + v4Views(v.views) + '</div></div>'; });
  return h + '</div></div>';
}
function v4RenderCards(elId, items){
  const el = v4$(elId);
  if(!items || !items.length){ el.innerHTML = '<p class="v4-muted">Kuch nahi mila — dobara try karein.</p>'; return; }
  v4AudioCards = (elId === 'v4-music-feed' && v4FeedState[elId] && v4FeedState[elId].type === 'mp3');
  el.innerHTML = items.map(function(it){ const v = v4Norm(it); if(!v.videoId) return ''; v4Videos[v.videoId] = v; return v4CardHTML(v); }).join('');
  v4AudioCards = false;
}
/* ---------- infinite feed (Update 33): scroll = nayi videos ---------- */
/* ---------- v9: global seen — jo dikh/dekh liya wo dobara nahi ---------- */
function v4SeenGet(){ try{ return JSON.parse(localStorage.getItem('pt_seen') || '[]'); }catch(e){ return []; } }
function v4SeenAdd(ids){ if(!ids || !ids.length) return; const now = Date.now(); const drop = {}; ids.forEach(function(id){ if(id) drop[id] = 1; }); const cur = v4SeenGet().filter(function(x){ return x && x.id && !drop[x.id]; }); ids.forEach(function(id){ if(id) cur.unshift({id:id, ts:now}); }); try{ localStorage.setItem('pt_seen', JSON.stringify(cur.slice(0, 3000))); }catch(e){} }
function v4SeenParam(){ return v4SeenGet().slice(0, 200).map(function(x){ return x.id; }).join(','); }
/* Update 127: YouTube model — sirf HAAL ki dikhi hui (recent
   window) refresh par nahi atin; us se purani mix mein wapis
   aa sakti hain, is liye list kabhi khatam nahi hoti aur har
   refresh ka mix alag hota hai. */
function v4RecentSet(n){ const s = {}; v4SeenGet().slice(0, n || 150).forEach(function(x){ if(x && x.id) s[x.id] = 1; }); return s; }
/* ---------- Update 130: diversity + filters + sync ---------- */
const v4Filters = {type:'all', date:'any', dur:'any', sort:'rel', feat:[]};
let v4FilterView = 'home';
function v4FilterActive(){ return v4Filters.type !== 'all' || v4Filters.date !== 'any' || v4Filters.dur !== 'any' || v4Filters.sort !== 'rel' || v4Filters.feat.length > 0; }
function v4DurSec(v){
  const d = v ? v.duration : '';
  if(typeof d === 'number') return d;
  if(!d) return 0;
  const p = ('' + d).split(':').map(function(x){ return parseInt(x, 10) || 0; });
  if(p.length === 3) return p[0] * 3600 + p[1] * 60 + p[2];
  if(p.length === 2) return p[0] * 60 + p[1];
  return p[0] || 0;
}
function v4ViewsNum(v){
  const x = v ? v.views : '';
  if(typeof x === 'number') return x;
  if(!x) return 0;
  const m = ('' + x).replace(/,/g, '').match(/([\d.]+)\s*([MK])?/i);
  if(!m) return 0;
  let n = parseFloat(m[1]) || 0;
  if(m[2]) n *= (m[2].toUpperCase() === 'M') ? 1e6 : 1e3;
  return n;
}
function v4AgeDays(v){
  const a = (v && v.age) ? ('' + v.age).toLowerCase() : '';
  const m = a.match(/([\d.]+)\s*(minute|hour|day|week|month|year)/);
  if(!m) return null;
  const n = parseFloat(m[1]) || 0;
  const u = m[2];
  if(u === 'minute') return n / 1440;
  if(u === 'hour') return n / 24;
  if(u === 'day') return n;
  if(u === 'week') return n * 7;
  if(u === 'month') return n * 30;
  return n * 365;
}
function v4FilterTest(v){
  const F = v4Filters;
  const d = v4DurSec(v);
  if(F.type === 'videos' && d > 0 && d <= 70) return false;
  if(F.type === 'movies' && d > 0 && d < 1500) return false;
  if(F.date !== 'any'){
    const days = v4AgeDays(v);
    if(days != null){
      if(F.date === 'today' && days >= 1) return false;
      if(F.date === 'week' && days > 7) return false;
      if(F.date === 'month' && days > 31) return false;
      if(F.date === 'year' && days > 366) return false;
    }
  }
  if(F.dur !== 'any' && d > 0){
    if(F.dur === 'short' && d >= 180) return false;
    if(F.dur === 'mid' && (d < 180 || d > 1200)) return false;
    if(F.dur === 'long' && d <= 1200) return false;
  }
  if(F.feat.indexOf('live') >= 0 && !(/\blive\b/i.test(v.title || '') || (v.age || '').indexOf('watching') >= 0)) return false;
  return true;
}
function v4ApplyFilters(list, st){
  if(!v4FilterActive() || !list || !list.length) return list || [];
  let out = list.filter(v4FilterTest);
  if(v4Filters.sort === 'pop') out = out.slice().sort(function(a, b){ return v4ViewsNum(b) - v4ViewsNum(a); });
  if(v4Filters.sort === 'new') out = out.slice().sort(function(a, b){ const x = v4AgeDays(a), y = v4AgeDays(b); return (x == null ? 9999 : x) - (y == null ? 9999 : y); });
  return out;
}
/* Diversity: padosi videos ek jaisi NAHI — channel + show
   dono pichli se alag hon to pehle wo; YouTube jaisa mix. */
function v4ShowKey(v){
  const t = (v.title || '').toLowerCase().replace(/[^\p{L}\p{N} ]/gu, ' ').split(/\s+/).filter(function(w){ return w.length > 2; }).slice(0, 2).join(' ');
  return t + '|' + (v.channel || '').toLowerCase();
}
function v4Diverse(list){
  if(!list || list.length < 3) return list || [];
  /* Update 142: sliding window — ek show ya channel ki
     item pichli 4 mein dobara nahi aati; jo takraye wo
     peeche chali jati hai (list ke aakhir mein). */
  const out = [], hold = [], win = [];
  list.forEach(function(v){
    const k = v4ShowKey(v), c = (v.channel || '').toLowerCase();
    let clash = false;
    for(let i = Math.max(0, win.length - 4); i < win.length; i++){
      if(win[i].k === k || (c && win[i].c === c)){ clash = true; break; }
    }
    if(clash) hold.push(v);
    else { out.push(v); win.push({k:k, c:c}); }
  });
  return out.concat(hold);
}
/* Update 142: app khulne par pehli video pichli dafa
   wali na ho — wahi first item ho to list ghuma do. */
function v4RotateFirst(elId, list){
  if(!list || list.length < 5) return list;
  try{
    const key = 'pt_last_first_' + elId;
    const last = localStorage.getItem(key) || '';
    let out = list;
    if(last && list[0].videoId === last) out = list.slice(3).concat(list.slice(0, 3));
    localStorage.setItem(key, out[0].videoId);
    return out;
  }catch(e){ return list; }
}
function v4FilterSyncUI(){
  document.querySelectorAll('.v4-fchip2').forEach(function(b){
    const g = b.getAttribute('data-fg'), val = b.getAttribute('data-fv');
    const on = (g === 'feat') ? (v4Filters.feat.indexOf(val) >= 0) : (v4Filters[g] === val);
    b.classList.toggle('on', !!on);
  });
}
function v4FilterBars(){
  const L = {videos:'Videos', movies:'Movies', shorts:'Shorts', playlists:'Playlists', today:'Today', week:'This week', month:'This month', year:'This year', short:'Under 3 min', mid:'3-20 min', long:'Over 20 min', pop:'Popularity', new:'Newest', live:'Live', '4k':'4K', hd:'HD', cc:'Subtitles'};
  const parts = [];
  if(v4Filters.type !== 'all') parts.push(L[v4Filters.type] || v4Filters.type);
  if(v4Filters.date !== 'any') parts.push(L[v4Filters.date] || v4Filters.date);
  if(v4Filters.dur !== 'any') parts.push(L[v4Filters.dur] || v4Filters.dur);
  if(v4Filters.sort !== 'rel') parts.push(L[v4Filters.sort] || v4Filters.sort);
  v4Filters.feat.forEach(function(f){ parts.push(L[f] || f); });
  ['home', 'youtube', 'music'].forEach(function(w){
    const el = v4$('v4-fact-' + w); if(!el) return;
    el.innerHTML = parts.length ? ('Filters: ' + parts.join(' • ') + ' &nbsp;<a href="#" onclick="v4FilterClearAll();return false" style="color:inherit;text-decoration:underline">✕ hatayein</a>') : '';
  });
}
function v4OpenFilters(w){
  v4FilterView = w || v4State.view || 'home';
  v4FilterSyncUI();
  const wr = v4$('v4-filterwrap'); if(wr) wr.classList.add('open');
  v4Lock(true);
}
function v4CloseFilters(){ const wr = v4$('v4-filterwrap'); if(wr) wr.classList.remove('open'); v4Lock(false); }
function v4FilterPick(btn){
  const g = btn.getAttribute('data-fg'), val = btn.getAttribute('data-fv');
  if(g === 'feat'){ const i = v4Filters.feat.indexOf(val); if(i >= 0) v4Filters.feat.splice(i, 1); else v4Filters.feat.push(val); }
  else v4Filters[g] = val;
  v4FilterSyncUI();
}
function v4FilterClear(){
  v4Filters.type = 'all'; v4Filters.date = 'any'; v4Filters.dur = 'any'; v4Filters.sort = 'rel'; v4Filters.feat = [];
  v4FilterSyncUI(); v4FilterBars();
}
function v4FilterClearAll(){
  v4FilterClear();
  const w = v4State.view;
  if(w === 'home' || w === 'youtube' || w === 'music'){ const fid = 'v4-' + w + '-feed'; const st = v4FeedState[fid]; if(st) v4LoadFeed(fid, st.q, st.type, st.sub); }
}
function v4FilterApply(){
  v4CloseFilters(); v4FilterBars();
  const w = v4FilterView, fid = 'v4-' + w + '-feed';
  const st = v4FeedState[fid];
  const q = st ? st.q : (w === 'youtube' ? 'trending videos' : (w === 'music' ? 'trending songs' : 'trending'));
  if(v4Filters.type === 'shorts'){ v4OpenShorts((q === 'trending' || q === 'trending videos' || q === 'trending songs') ? '' : q); return; }
  if(v4Filters.type === 'playlists'){ v4LoadFeed(fid, q, 'playlists'); return; }
  if(st) v4LoadFeed(fid, st.q, st.type, st.sub);
  else v4LoadFeed(fid, q, 'all');
}
/* Account sync: YouTube account link ho to Home/YouTube ki
   pehli list UN KE YouTube home jaisi (bridge ytHomeFeed —
   un ke apne signed-in session se live). Na mile to aam
   mix wala rasta khud chal jata hai. */
let v4YtHomeWait = null;
function v4YtHomeResult(jsonStr){ const w = v4YtHomeWait; v4YtHomeWait = null; if(!w) return; if(!jsonStr){ w(null); return; } try{ w(JSON.parse(jsonStr)); }catch(e){ w(null); } }
function v4YtHomeCall(){
  return new Promise(function(res){
    if(!(window.PlayTubeApp && PlayTubeApp.ytHomeFeed)){ res(null); return; }
    v4YtHomeWait = res;
    try{ PlayTubeApp.ytHomeFeed(); }catch(e){ v4YtHomeWait = null; res(null); return; }
    setTimeout(function(){ if(v4YtHomeWait === res){ v4YtHomeWait = null; res(null); } }, 9000);
  });
}
async function v4SyncFeedTry(elId, st, gen){
  try{
    if(elId !== 'v4-home-feed' && elId !== 'v4-youtube-feed') return false;
    if((st.type || 'videos') !== 'all') return false;
    let linked = ''; try{ linked = localStorage.getItem('pt_yt_linked') || ''; }catch(e){}
    if(linked !== '1') return false;
    if(!(window.PlayTubeApp && PlayTubeApp.ytHomeFeed)) return false;
    const data = await v4YtHomeCall();
    if(v4FeedGen[elId] !== gen || v4FeedState[elId] !== st) return true;
    if(!data || !data.videos || !data.videos.length) return false;
    const el = v4$(elId); if(!el) return false;
    let html = '';
    const shorts = (data.shorts || []).map(function(s){ return {id:{videoId:s.id}, snippet:{title:s.title || '', channelTitle:s.channel || ''}, view_count:s.views || ''}; });
    if(shorts.length >= 3) html += v4ShortStripHTML(shorts);
    let n = 0;
    data.videos.forEach(function(sv){
      const v = {videoId:sv.id, title:sv.title || '', channel:sv.channel || '', duration:sv.dur || '', views:sv.views || '', age:sv.age || ''};
      if(!v.videoId || st.seen[v.videoId]) return;
      st.seen[v.videoId] = 1; v4FeedShown[v.videoId] = 1; v4Videos[v.videoId] = v; html += v4CardHTML(v); n++; v4SeenAdd([v.videoId]);
    });
    if(!n) return false;
    el.innerHTML = html;
    st.phonePg = null; st.done = false; st._sync = 1;
    el.insertAdjacentHTML('beforeend', v4FeedSentinelHTML(elId));
    const sn = el.querySelector('.v4-more'); if(sn && v4FeedObs) v4FeedObs.observe(sn);
    return true;
  }catch(e){ return false; }
}
/* Phone path par Shorts ki row (Home/YouTube ke andar, line
   mein) — server path par ye pehle se ati hai. */
async function v4StripPhone(elId, st){
  try{
    if(elId !== 'v4-home-feed' && elId !== 'v4-youtube-feed') return;
    const t = st.type || 'videos';
    if(t !== 'all' && t !== 'videos') return;
    const items = await v4PhoneBridge('phoneSearch', 'trending shorts');
    if(!items || !items.length) return;
    const el = v4$(elId); if(!el || v4FeedState[elId] !== st) return;
    if(el.querySelector('.v4-srow')) return;
    const raw = [];
    items.forEach(function(it){ if(it.duration > 0 && it.duration <= 70 && raw.length < 10) raw.push({id:{videoId: it.id}, snippet:{title: it.title || '', channelTitle: it.channel || ''}, duration: it.duration, view_count: (it.views != null && it.views >= 0) ? it.views : ''}); });
    if(raw.length < 3) return;
    const strip = v4ShortStripHTML(raw);
    const cards = el.querySelectorAll('.v4-vcard');
    if(cards.length >= 5) cards[3].insertAdjacentHTML('afterend', strip);
    else el.insertAdjacentHTML('afterbegin', strip);
  }catch(e){}
}
/* Floating player (APK v3.5): phone stream wali video dusri
   apps ke UPAR chhoti window mein — move/resize system PiP. */
function v4FloatPlay(){
  if(!v4FrameId) return;
  if(!(window.PlayTubeApp && PlayTubeApp.openFloatPlayer)){ v4Toast('Floating player sirf nayi app (v3.5+) mein hai'); return; }
  v4Toast('Floating player load ho raha hai...');
  try{ PlayTubeApp.openFloatPlayer(v4FrameId, (v4Current && v4Current.title) || ''); }catch(e){ v4Toast('Floating player nahi khula'); }
}
function v4FloatResult(ok){ if(!ok) v4Toast('Is video ka floating player nahi ban saka — ye video phone stream se nahi mili'); }
/* App wapas khule (kaafi der baad) to feed khud fresh —
   24h sync wali feeling: har open par YouTube jaisa taza. */
let _v4HiddenAt = 0;
document.addEventListener('visibilitychange', function(){
  if(document.hidden){ _v4HiddenAt = Date.now(); return; }
  if(_v4HiddenAt && Date.now() - _v4HiddenAt > 60000){
    _v4HiddenAt = 0;
    const vw = v4State.view;
    if(vw === 'home' || vw === 'youtube' || vw === 'music'){
      const fid = 'v4-' + vw + '-feed'; const st = v4FeedState[fid];
      if(st && !st.loading) v4LoadFeed(fid, st.q, st.type, st.sub);
    }
  }
});

const v4FeedState = {};
let v4FeedSession = Math.random().toString(36).slice(2, 10);
/* ---------- personalization (Update 34): jo zyada search/watch, waisa feed ---------- */
function v4Interest(){ try{ return JSON.parse(localStorage.getItem('pt_interest') || '{}'); }catch(e){ return {}; } }
function v4InterestAdd(phrase, w){
  if(!phrase) return;
  phrase = ('' + phrase).trim().toLowerCase().slice(0, 60);
  if(phrase.length < 3) return;
  const it = v4Interest(); it[phrase] = (it[phrase] || 0) + (w || 1);
  const keys = Object.keys(it);
  if(keys.length > 40){ keys.sort(function(a, b){ return it[a] - it[b]; }); keys.slice(0, keys.length - 40).forEach(function(k){ delete it[k]; }); }
  try{ localStorage.setItem('pt_interest', JSON.stringify(it)); }catch(e){}
}
function v4InterestTop(n){
  const it = v4Interest();
  return Object.keys(it).sort(function(a, b){ return it[b] - it[a]; }).slice(0, n || 5);
}
const v4FeedObs = ('IntersectionObserver' in window) ? new IntersectionObserver(function(entries){
  entries.forEach(function(en){ if(en.isIntersecting) v4FeedMore(en.target.getAttribute('data-feed')); });
}, {rootMargin: '700px'}) : null;
function v4FeedSentinelHTML(elId){
  return '<div class="v4-more" data-feed="' + elId + '" style="grid-column:1 / -1;text-align:center;padding:16px"><span class="v4-muted">Aur videos load ho rahi hain...</span></div>';
}
const v4FeedGen = {};
/* Update 123: is session mein kisi bhi feed ke pehle page par
   dikh chuki videos — dusri tab/chip par wahi video dobara sab se
   pehle nahi ayegi ('baar baar same video' wala masla). */
const v4FeedShown = {};
/* Update 116: APK mein server fail ho to PHONE se search/trending —
   NewPipe bridge (phoneSearch/phoneTrending). Browser mein bridge
   nahi hota, wahan purana flow hi chalta hai. */
let v4PhoneSearchWait = null;
function v4PhoneSearchResult(jsonStr, errStr){ const w = v4PhoneSearchWait; v4PhoneSearchWait = null; if(!w) return; if(!jsonStr){ w(null); return; } try{ w(JSON.parse(jsonStr)); }catch(e){ w(null); } }
function v4PhoneBridge(method, arg){
  return new Promise(function(res){
    if(!(window.PlayTubeApp && PlayTubeApp[method])){ res(null); return; }
    v4PhoneSearchWait = res;
    try{ if(arg != null) PlayTubeApp[method](arg); else PlayTubeApp[method](); }catch(e){ v4PhoneSearchWait = null; res(null); return; }
    setTimeout(function(){ if(v4PhoneSearchWait === res){ v4PhoneSearchWait = null; res(null); } }, 30000);
  });
}
/* Update 121: chip/type/sub se ASAL search query — server wale
   /api/feed ke naqshe ki copy, taake phone wala rasta bhi har chip
   ki APNI talash kare (ek hi trending list har jagah wala bug
   yahin se khatam hota hai). '' mile to matlab trending hai;
   null mile to is type ke liye phone rasta nahi (playlists). */
function v4FeedQuery(st){
  const q = (st.q || '').trim();
  const t = (st.type || 'videos'), sub = (st.sub || 'all');
  const trend = (!q || /^trend/i.test(q));
  const D = {pakistani:'pakistani drama episode', indian:'indian drama serial', turkish:'turkish drama in urdu', dubbed:'korean drama hindi dubbed', webseries:'web series hindi dubbed'};
  const M = {indian:'indian full movie hindi', pakistani:'pakistani full movie', punjabi:'punjabi full movie', english:'hollywood hindi dubbed full movie', dubbed:'hollywood movie hindi dubbed full', south:'south indian movie hindi dubbed'};
  const K = {motupatlu:'motu patlu cartoon hindi', cocomelon:'cocomelon nursery rhymes', doraemon:'doraemon cartoon hindi', peppa:'peppa pig full episodes', tomjerry:'tom and jerry cartoon'};
  const DS = {pakistani:' pakistani drama', indian:' indian drama serial', turkish:' turkish drama urdu dubbed', dubbed:' hindi dubbed drama', webseries:' web series'};
  const MS = {indian:' indian full movie', pakistani:' pakistani full movie', punjabi:' punjabi full movie', english:' hollywood hindi dubbed movie', dubbed:' hindi dubbed full movie', south:' south indian hindi dubbed movie'};
  const KS = {motupatlu:' motu patlu', cocomelon:' cocomelon', doraemon:' doraemon hindi', peppa:' peppa pig', tomjerry:' tom and jerry'};
  if(t === 'playlists') return null;
  if(t === 'dramas'){ if(!trend) return q + (DS[sub] || ' drama episode'); return D[sub] || 'pakistani drama episode'; }
  if(t === 'movies'){ if(!trend) return q + (MS[sub] || ' full movie'); return M[sub] || 'full movie hindi'; }
  if(t === 'kids'){ if(!trend) return q + (KS[sub] || ' for kids'); return K[sub] || 'kids cartoon hindi'; }
  if(t === 'mp3') return trend ? 'new songs official audio' : (q + ' official audio');
  if(t === 'naat') return trend ? 'naat sharif' : q;
  if(t === 'shorts') return trend ? 'trending shorts' : (q + ' shorts');
  if(t === 'live') return trend ? 'live stream' : (q + ' live stream');
  if(/^trending songs/i.test(q)) return 'latest songs official video';
  if(trend) return '';
  /* Update 130: Features (4K/Subtitles) search mein query
     hint ban kar jate hain — YouTube bhi aise hi talashta hai. */
  const fh = (v4Filters.feat.indexOf('4k') >= 0 ? ' 4K' : '') + (v4Filters.feat.indexOf('cc') >= 0 ? ' subtitles' : '');
  return q + fh;
}
/* Update 139: Search ke options (Nayi / Lambi) ka asal
   filter — pehle ye sirf server ko jata tha, phone wali
   list par kuch nahi hota tha (Nayi par 5 saal purani
   video bhi aa jati thi). Nayi = sirf pichle ~3 mahine,
   sab se nayi pehle; Lambi = sirf minDur se lambi. */
function v4ApplySearchOpts(list, st){
  let out = list || [];
  if(st && st.minDur){ out = out.filter(function(v){ return v4DurSec(v) >= st.minDur; }); }
  if(st && st.sort === 'date'){
    out = out.filter(function(v){ const d = v4AgeDays(v); return d >= 0 && d <= 92; });
    out.sort(function(a, b){ return v4AgeDays(a) - v4AgeDays(b); });
  }
  return out;
}
async function v4PhoneFeedFallback(elId, st){
  try{
    if(!(window.PlayTubeApp && PlayTubeApp.phoneSearch)) return false;
    const q = v4FeedQuery(st);
    if(q === null) return false;
    /* Update 125: rotation har load par nayi jagah se shuru —
       har open/refresh ka pehla batch mukhtalif. */
    if(st.phoneRot == null) st.phoneRot = (Math.random() * 16) | 0;
    let items = null;
    if(q === ''){
      /* Trending satahein: Home = asal YouTube trending; YouTube
         tab ki pehli list pool-rotation se — warna dono par wahi
         pehli video khadi rehti thi. */
      /* Update 142: pehli list TEEN alag rotation queries
         se (parallel) — ek hi topic (bayan/cartoon/drama)
         ki poori list nahi banti; global chart sirf
         aakhri fallback hai. */
      const _r0 = st.phoneRot || 0;
      const _qs = [v4PhoneRotQuery(st)];
      st.phoneRot = _r0 + 1; _qs.push(v4PhoneRotQuery(st));
      st.phoneRot = _r0 + 2; _qs.push(v4PhoneRotQuery(st));
      st.phoneRot = _r0 + 2;
      const _rs = await Promise.all(_qs.map(function(x){ return v4PhoneBridge('phoneSearch', x); }));
      items = [];
      const _seenQ = {};
      _rs.forEach(function(r){ (r || []).forEach(function(it){ if(it && it.id && !_seenQ[it.id]){ _seenQ[it.id] = 1; items.push(it); } }); });
      if(!items.length && PlayTubeApp.phoneTrending) items = await v4PhoneBridge('phoneTrending', null);
    }
    if(!items || !items.length) items = await v4PhoneBridge('phoneSearch', q || 'trending');
    if(!items || !items.length) return false;
    const el = v4$(elId); if(!el) return false;
    const norm = [];
    items.forEach(function(it){
      const v = v4Norm({id:{videoId: it.id}, snippet:{title: it.title || '', channelTitle: it.channel || ''}, duration: (it.duration > 0) ? it.duration : '', view_count: (it.views != null && it.views >= 0) ? it.views : '', age_text: it.age || '', age_ts: it.age_ts || 0, live: it.live || false});
      if(v.videoId) norm.push(v);
    });
    if(!norm.length) return false;
    /* Update 127 (YouTube model): is feed/session mein dikhi
       hui + HAAL ki 150 purani — ye refresh par nahi atin.
       Us se purani videos mix mein aa sakti hain (YouTube par
       bhi aisa hi hota hai) — is liye har refresh alag mix,
       aur list kabhi khatam nahi hoti. */
    const seenP = v4RecentSet(150);
    let ordered = norm.filter(function(v){ return !st.seen[v.videoId] && !v4FeedShown[v.videoId] && !seenP[v.videoId]; });
    ordered = v4ApplySearchOpts(ordered, st);
    /* Update 125: pehli list mein NAYI (kabhi na dekhi) videos
       6 se kam hon to phone se aur bharo — har open / refresh
       par har jagah sar naya, purani video kahin nahi. */
    let _unseen = 0;
    ordered.forEach(function(v){ if(!v4FeedShown[v.videoId] && !seenP[v.videoId]) _unseen++; });
    for(let _tx = 0; _tx < 4 && _unseen < 8; _tx++){
      let _more = null;
      if(q !== '' && window.PlayTubeApp && PlayTubeApp.phoneSearchMore) _more = await v4PhoneBridge('phoneSearchMore', q);
      if(!_more || !_more.length){ st.phoneRot = (st.phoneRot || 0) + 1; _more = await v4PhoneBridge('phoneSearch', (q === '') ? v4PhoneRotQuery(st) : (q + (st.sort === 'date' ? ' new' : '') + v4_FEED_VARIANTS[st.phoneRot % v4_FEED_VARIANTS.length])); }
      if(!_more || !_more.length) break;
      const _have = {}; ordered.forEach(function(v){ _have[v.videoId] = 1; });
      const _add = [];
      _more.forEach(function(it){
        const v = v4Norm({id:{videoId: it.id}, snippet:{title: it.title || '', channelTitle: it.channel || ''}, duration: (it.duration > 0) ? it.duration : '', view_count: (it.views != null && it.views >= 0) ? it.views : '', age_text: it.age || '', age_ts: it.age_ts || 0, live: it.live || false});
        if(v.videoId && !_have[v.videoId] && !st.seen[v.videoId] && !v4FeedShown[v.videoId] && !seenP[v.videoId]){ _have[v.videoId] = 1; _add.push(v); }
      });
      _add = v4ApplySearchOpts(_add, st);
      if(!_add.length) continue;
      ordered = _add.concat(ordered);
      _unseen += _add.length;
    }
    if(!ordered.length && (!st.q || /trend/i.test(st.q))){
      /* Update 142: browse feed KABHI 'khatam' nahi —
         dekhi-hui window chhoti karke dobara; phir bhi
         na mile to jo hasil hai wahi dikha do. */
      const seen40 = v4RecentSet(40);
      ordered = norm.filter(function(v){ return !st.seen[v.videoId] && !seen40[v.videoId]; });
      if(!ordered.length) ordered = norm.filter(function(v){ return !st.seen[v.videoId]; });
    }
    ordered = v4ApplyFilters(ordered, st);
    ordered = v4ApplySearchOpts(ordered, st);
    if(st.sort !== 'date') ordered = v4Diverse(ordered);
    if(!st.q || /trend/i.test(st.q)) ordered = v4RotateFirst(elId, ordered);
    if(!ordered.length) return false;
    let html = '', n = 0;
    ordered.forEach(function(v){
      st.seen[v.videoId] = 1; v4FeedShown[v.videoId] = 1; v4Videos[v.videoId] = v; html += v4CardHTML(v); n++; v4SeenAdd([v.videoId]);
    });
    if(!n) return false;
    el.innerHTML = html;
    v4StripPhone(elId, st);
    /* Update 124: phone wali feed bhi UNLIMITED — done NAHI;
       scroll par v4FeedMore phone ki agli page layega, phone
       thak jaye to server wala rasta. */
    st.phonePg = 0;
    st.phoneQ = q;
    st.done = false;
    v4FeedArm(elId);
    return true;
  }catch(e){ return false; }
}
/* Update 124: server wale FEED_TRENDING_POOL ki copy — trending
   satahon ki agli pages inhi seeds ko ghuma kar aati hain, user ki
   pasand (interests) beech mein mili hui. Khatam honay ka sawal
   hi nahi: seeds x variants x agli search pages. */
const v4_TREND_POOL = ['trending videos', 'viral videos today', 'trending naat', 'pakistani drama latest episode', 'funny comedy videos', 'trending songs', 'kids cartoon hindi', 'cricket highlights', 'motu patlu new episode', 'pubg gameplay', 'cooking recipes viral', 'tech news today', 'islamic bayan', 'punjabi songs new', 'bollywood songs', 'pakistan vlogs'];
const v4_FEED_VARIANTS = [' latest', ' new', '', ' viral', ' best', ' 2026'];
function v4PhoneRotQuery(st){
  const ints = v4InterestTop(3);
  const mixed = [];
  v4_TREND_POOL.forEach(function(s, i){ mixed.push(s); if(ints.length && i % 5 === 2) mixed.push(ints[((i / 5) | 0) % ints.length]); });
  const idx = st.phoneRot || 0;
  return mixed[idx % mixed.length] + v4_FEED_VARIANTS[((idx / mixed.length) | 0) % v4_FEED_VARIANTS.length];
}
function v4FeedArm(elId){
  const el = v4$(elId); if(!el) return;
  const old = el.querySelector('.v4-more'); if(old) old.remove();
  el.insertAdjacentHTML('beforeend', v4FeedSentinelHTML(elId));
  const s = el.querySelector('.v4-more');
  if(s && v4FeedObs) v4FeedObs.observe(s);
  if(s){ const rc = s.getBoundingClientRect(); if(rc.top < window.innerHeight + 700){ const st = v4FeedState[elId]; if(st && !st.loading && !st.done) v4FeedMore(elId); } }
}
async function v4PhoneFeedMore(elId, st){
  try{
    if(!(window.PlayTubeApp && PlayTubeApp.phoneSearch)) return false;
    const el = v4$(elId); if(!el) return false;
    const seenP = v4RecentSet(150);
    for(let attempt = 0; attempt < 2; attempt++){
      let items = null;
      if(st.phoneQ){
        /* Asal search: extractor ki agli page (APK v3.3 bridge);
           na mile to usi query ka variant — nayi list. */
        if(PlayTubeApp.phoneSearchMore) items = await v4PhoneBridge('phoneSearchMore', st.phoneQ);
        if(!items || !items.length){ st.phoneRot = (st.phoneRot || 0) + 1; items = await v4PhoneBridge('phoneSearch', st.phoneQ + v4_FEED_VARIANTS[st.phoneRot % v4_FEED_VARIANTS.length]); }
      } else {
        /* Update 142: agli page bhi DO alag topics se —
           ek hi search ki gehrai nahi. */
        st.phoneRot = (st.phoneRot || 0) + 1;
        const _q1 = v4PhoneRotQuery(st);
        st.phoneRot = (st.phoneRot || 0) + 1;
        const _q2 = v4PhoneRotQuery(st);
        const _rr = await Promise.all([v4PhoneBridge('phoneSearch', _q1), v4PhoneBridge('phoneSearch', _q2)]);
        items = (_rr[0] || []).concat(_rr[1] || []);
      }
      if(!items || !items.length) continue;
      let batch = [];
      items.forEach(function(it){
        const v = v4Norm({id:{videoId: it.id}, snippet:{title: it.title || '', channelTitle: it.channel || ''}, duration: (it.duration > 0) ? it.duration : '', view_count: (it.views != null && it.views >= 0) ? it.views : '', age_text: it.age || '', age_ts: it.age_ts || 0, live: it.live || false});
        if(v.videoId && !st.seen[v.videoId] && !v4FeedShown[v.videoId] && !seenP[v.videoId]){ st.seen[v.videoId] = 1; batch.push(v); }
      });
      batch = v4ApplySearchOpts(v4ApplyFilters(batch, st), st);
      if(st.sort !== 'date') batch = v4Diverse(batch);
      let html = '', n = 0;
      batch.forEach(function(v){ v4FeedShown[v.videoId] = 1; v4Videos[v.videoId] = v; html += v4CardHTML(v); n++; v4SeenAdd([v.videoId]); });
      if(!n) continue;
      const old = el.querySelector('.v4-more'); if(old) old.remove();
      el.insertAdjacentHTML('beforeend', html);
      v4FeedArm(elId);
      return true;
    }
    return false;
  }catch(e){ return false; }
}
function v4FeedRetry(btn){ const elId = btn.getAttribute('data-feed'); const st = v4FeedState[elId]; if(!st) return; v4LoadFeed(elId, st.q, st.type, st.sub, {sort: st.sort, minDur: st.minDur}); }
async function v4LoadFeed(elId, q, type, sub, opts){
  const el = v4$(elId); if(!el) return;
  const gen = (v4FeedGen[elId] = (v4FeedGen[elId] || 0) + 1);
  v4FeedState[elId] = {q:q, type:(type || 'videos'), sub:(sub || ''), page:0, seen:{}, loading:false, done:false, sort:(opts && opts.sort) || '', minDur:(opts && opts.minDur) || 0, gen:gen, _retry:(opts && opts._retry) || 0};
  el.innerHTML = '<p class="v4-muted">Load ho raha hai...</p>';
  /* Update 130: account link ho to pehle UN KE YouTube home
     ki sync list (Home/YouTube ke All par) — na mile to neeche
     wala aam rasta khud chal jata hai. */
  if(await v4SyncFeedTry(elId, v4FeedState[elId], gen)) return;
  /* Update 121: APK mein PHONE PEHLE — har chip/search ki asal
     talash phone se hoti hai; server sirf tab jab phone kuch na de.
     (Browser mein bridge nahi hota — wahan purana server flow hi.) */
  if(window.PlayTubeApp && PlayTubeApp.phoneSearch && (type || 'videos') !== 'playlists'){
    const okP = await v4PhoneFeedFallback(elId, v4FeedState[elId]);
    if(okP) return;
    if(v4FeedGen[elId] !== gen) return;
    el.innerHTML = '<p class="v4-muted">Load ho raha hai...</p>';
  }
  await v4FeedMore(elId, true);
}
async function v4FeedMore(elId, first){
  const st = v4FeedState[elId]; const el = v4$(elId);
  if(!st || !el || st.loading || st.done) return;
  st.loading = true;
  const gen = st.gen || 0;
  /* Update 124: APK mein pehle PHONE ki agli page — feed khatam
     nahi hoti; phone thak jaye to neeche server wala rasta hai. */
  if(st.phonePg != null && window.PlayTubeApp && PlayTubeApp.phoneSearch){
    const okM = await v4PhoneFeedMore(elId, st);
    if(v4FeedGen[elId] !== gen || v4FeedState[elId] !== st){ st.loading = false; return; }
    if(okM){ st.loading = false; return; }
    st.phonePg = null;
  }
  let added = 0, tries = 0, failed = false;
  let stripHtml = '';
  const maxTries = (st.sort === 'date' || st.minDur) ? 8 : 5;
  while(tries < maxTries && added < 8 && !st.done){
    tries++;
    const r = await v4Fetch('/api/feed?q=' + encodeURIComponent(st.q) + '&page=' + st.page + '&type=' + (st.type || 'videos') + (st.sub ? '&sub=' + st.sub : '') + (st.sort ? '&sort=' + st.sort : '') + (st.minDur ? '&min_dur=' + st.minDur : '') + '&seen=' + encodeURIComponent(v4SeenParam()) + '&r=' + v4FeedSession + '&int=' + encodeURIComponent(v4InterestTop(5).join('|')));
    if(v4FeedGen[elId] !== gen || v4FeedState[elId] !== st){ st.loading = false; return; }
    if(!(r.ok && r.data && r.data.items)){ failed = true; break; }
    if(first && !stripHtml && r.data.shorts_row){ stripHtml = v4ShortStripHTML(r.data.shorts_row); v4SeenAdd(r.data.shorts_row.map(function(x){ return (x.id && x.id.videoId) || ''; }).filter(Boolean)); }
    st.page++;
    if(r.data.has_more === false){
      /* Update 127: browse feed par 'Bas' NAHI — pool khatam ho
         to naya session ghuma kar dobara (window purani videos
         ko foran wapis nahi ane deta). Playlist is se bahir
         hai — wo asal mein khatam hoti hai. */
      if(!st._cycled && st.type !== 'playlists'){ st._cycled = 1; v4FeedSession = Math.random().toString(36).slice(2, 10); st.page = 0; }
      else st.done = true;
    }
    v4AudioCards = (elId === 'v4-music-feed' && st.type === 'mp3');
    let pageHtml = '', pageCount = 0;
    const pageVs = [];
    r.data.items.forEach(function(it){
      if(it.kind === 'playlist'){
        const pid = (it.id && it.id.playlistId) || '';
        if(pid && !st.seen['pl:' + pid]){ st.seen['pl:' + pid] = 1; pageHtml += v4PlaylistCardHTML(it); pageCount++; }
      } else {
        const v = v4Norm(it);
        if(v.videoId && !st.seen[v.videoId]){ st.seen[v.videoId] = 1; pageVs.push(v); }
      }
    });
    let pageVs2 = (st.type === 'playlists') ? pageVs : v4ApplyFilters(pageVs, st);
    if(st.type !== 'playlists'){ pageVs2 = v4ApplySearchOpts(pageVs2, st); if(st.sort !== 'date') pageVs2 = v4Diverse(pageVs2); }
    pageVs2.forEach(function(v){ v4Videos[v.videoId] = v; pageHtml += v4CardHTML(v); pageCount++; v4SeenAdd([v.videoId]); });
    v4AudioCards = false;
    if(pageCount){
      if(first && added === 0) el.innerHTML = stripHtml + pageHtml;
      else { const old = el.querySelector('.v4-more'); if(old) old.remove(); el.insertAdjacentHTML('beforeend', pageHtml); }
      added += pageCount;
    }
    if(!r.data.items.length) break;
  }
  if(v4FeedGen[elId] !== gen || v4FeedState[elId] !== st) return;
  const oldS = el.querySelector('.v4-more'); if(oldS) oldS.remove();
  st.loading = false;
  if(added > 0){ st.empty = 0; st._cycled = 0; } else { st.empty = (st.empty || 0) + 1; if(st.empty >= 2) st.done = true; }
  if(first && !added){
    /* Update 121: 'Server slow hai' wala khud-bakhud loop KHATAM.
       Pehle phone fallback (asal query ke sath), warna khamosh msg
       aur hath se dobara wala button — baar baar wahi error nahi. */
    if(window.PlayTubeApp && PlayTubeApp.phoneSearch){
      const okF = await v4PhoneFeedFallback(elId, st);
      if(okF) return;
    }
    el.innerHTML = failed ? '<p class="v4-muted">Results load nahi ho sake — net check karke dobara try karein.</p><div style="text-align:center;padding:6px"><button class="v4-btn2" data-feed="' + elId + '" onclick="v4FeedRetry(this)">↻ Dobara try karein</button></div>' : (v4FilterActive() ? '<p class="v4-muted">In filters ke sath nayi videos nahi milin.</p><div style="text-align:center;padding:6px"><button class="v4-btn2" onclick="v4FilterClearAll();v4FilterApply()">Filters hatayein</button></div>' : (st.sort === 'date' ? '<p class="v4-muted">Is topic par nayi (haal ki) videos nahi milin — Sab wale option par saari results hain.</p>' : ((!st.q || /trend/i.test(st.q)) ? '<p class="v4-muted">Videos load nahi ho sakin — dobara try karein.</p><div style="text-align:center;padding:6px"><button class="v4-btn2" data-feed="' + elId + '" onclick="v4FeedRetry(this)">↻ Dobara try karein</button></div>' : '<p class="v4-muted">Is topic ki saari videos aap pehle dekh chuke hain — is liye dobara nahi dikhayi gayin. Koi aur topic ya search try karein 🌟</p>')));
    return;
  }
  if(st.done){
    el.insertAdjacentHTML('beforeend', '<p class="v4-muted" style="grid-column:1 / -1;text-align:center;padding:12px">Bas — filhal itni hi videos hain.</p>');
    return;
  }
  el.insertAdjacentHTML('beforeend', v4FeedSentinelHTML(elId));
  const s = el.querySelector('.v4-more');
  if(s && v4FeedObs) v4FeedObs.observe(s);
  if(s){ const rc = s.getBoundingClientRect(); if(rc.top < window.innerHeight + 700) v4FeedMore(elId); }
}
function v4HomeSearch(e){ e.preventDefault(); const q = v4$('v4-q-home').value.trim(); if(!q) return; if(q.indexOf('http') === 0){ v4SmartLink(q); return; } v4RunSearch(q); }
async function v4SmartLink(q){
  const r = await v4Post('/api/smart-link', {url:q});
  if(r.ok && r.data){
    if(r.data.type === 'youtube'){ const v = {videoId:r.data.video_id, title:'', channel:''}; v4Videos[v.videoId] = v; v4DlClick(null, v.videoId); return; }
    if(r.data.type === 'social'){ v4Show('social'); v4$('v4-social-url').value = q; v4SocialFetch(null); return; }
    if(r.data.type === 'playlist'){ v4Toast('Playlist link mila — AI Assistant me command de kar download karein'); return; }
  }
  v4LoadFeed('v4-home-feed', q);
}
function v4FeedSearch(e, which){ e.preventDefault(); const q = v4$('v4-q-' + which).value.trim(); if(q){ v4InterestAdd(q, 2); v4LoadFeed('v4-' + which + '-feed', q, 'all'); } }

/* ---------- watch (Update 42: play sab ke liye khula, bina account) ---------- */
function v4WatchClick(id){
  if(!id || id === 'undefined'){ v4Toast('Video ID nahi mili — dobara try karein'); return; }
  const v = v4Videos[id] || {videoId:id, title:'', channel:''};
  v4OpenWatch(v);
}
/* ---------- Watch player (v9: purana tareeqa wapas — bahir Playza ka frame,
   andar wahi purana player jo har video chalata hai: chhoti ho ya lambi) ---------- */
let v4FrameId = '';
function v4FrameSetup(id){
  v4FrameId = id;
  const fr = v4$('v4-player');
  if(fr) fr.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0&playsinline=1&modestbranding=1&enablejsapi=1';
  const wm = v4$('v4-watch-msg'); if(wm){ wm.style.display = 'none'; wm.textContent = ''; }
  if(window._v4ft) clearTimeout(window._v4ft);
  if(fr) fr.onload = function(){ if(window._v4ft){ clearTimeout(window._v4ft); window._v4ft = null; } };
  /* Update 132: 'Phone se play karein' BUTTON khatam — embed
     12s mein load na ho to phone wala rasta KHUD try hota
     hai; wo bhi na mile to saaf message (net ka ilzaam nahi). */
  window._v4ft = setTimeout(function(){
    if(v4FrameId !== id) return;
    if(v4NativeMode() && window.PlayTubeApp && PlayTubeApp.nativePlay) v4NativePlay(true);
    else v4WatchMsg();
  }, 12000);
  const fb = v4$('v4-watch-fav');
  if(fb){ let favs = []; try{ favs = JSON.parse(localStorage.getItem('pt_favs') || '[]'); }catch(e){} fb.textContent = favs.some(function(f){ return f.id === id; }) ? '♥' : '♡'; }
}
function v4FrameStop(){
  const fr = v4$('v4-player');
  if(fr && v4FrameId){ fr.src = 'about:blank'; v4FrameId = ''; }
}
function v4WatchMsg(){
  const wm = v4$('v4-watch-msg'); if(!wm) return;
  wm.innerHTML = 'Ye video filhal yahan nahi chal pa rahi — thodi der baad dobara try karein. <a href="https://www.youtube.com/watch?v=' + v4FrameId + '" target="_blank" rel="noopener" style="color:var(--v4teal)">YouTube par kholein ↗</a>';
  wm.style.display = '';
}
function v4NativePlay(silent){
  if(!v4FrameId || !v4NativeMode() || !PlayTubeApp.nativePlay){ if(!silent) v4Toast('Ye option sirf app mein hai'); return; }
  if(!silent) v4Toast('Phone se video load ho rahi hai...');
  window._v4npWait = true;
  try{ PlayTubeApp.nativePlay(v4FrameId); }catch(e){ window._v4npWait = false; if(!silent) v4Toast('Phone se play nahi ho saka'); else v4WatchMsg(); return; }
  setTimeout(function(){ if(window._v4npWait){ window._v4npWait = false; v4WatchMsg(); } }, 30000);
}
function v4NativePlayResult(url){
  window._v4npWait = false;
  if(!url){ v4WatchMsg(); return; }
  const vid = v4$('v4-filevideo'); if(!vid) return;
  v4$('v4-player-title').textContent = (v4Current && v4Current.title) || '';
  vid.src = url;
  v4$('v4-playerwrap').classList.add('open'); v4Lock(true);
  const p = vid.play(); if(p && p.catch) p.catch(function(){});
}
function v4WatchFav(){
  if(!v4Current) return;
  let favs = []; try{ favs = JSON.parse(localStorage.getItem('pt_favs') || '[]'); }catch(e){}
  const i = favs.findIndex(function(f){ return f.id === v4Current.videoId; });
  const fb = v4$('v4-watch-fav');
  if(i >= 0){ favs.splice(i, 1); if(fb) fb.textContent = '♡'; v4Toast('Favorites se hata diya'); }
  else { favs.unshift({id:v4Current.videoId, title:v4Current.title || '', channel:v4Current.channel || ''}); if(fb) fb.textContent = '♥'; v4Toast('Favorites mein save ho gayi'); }
  try{ localStorage.setItem('pt_favs', JSON.stringify(favs.slice(0, 200))); }catch(e){}
}
function v4WatchShare(){
  if(!v4Current) return;
  const txt = (v4Current.title || 'Video') + '\\nhttps://www.youtube.com/watch?v=' + v4Current.videoId + '\\n\\nPlayza par dekhein / download karein: ' + window.location.origin + '/';
  if(navigator.share){ navigator.share({title: v4Current.title || 'Playza', text: txt}).catch(function(){}); }
  else if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(txt).then(function(){ v4Toast('Link copy ho gaya'); }); }
  else v4Toast('Share is browser mein nahi ho saka');
}

/* ---------- Shorts: Reels style, Playza design (Update 65) ---------- */
let v4ShortsPage = 0, v4ShortsLoading = false, v4ShortsDone = false, v4ShortsObs = null, v4ShortsMuted = (localStorage.getItem('pt_short_muted') === '1'), v4ShortsSeq = 0, v4ShortsQuery = 'trending shorts';
const v4ShortsItems = {};
function v4FmtCount(n){ n = Number(n) || 0; if(n >= 1e6) return (n / 1e6).toFixed(1).replace('.0', '') + 'M'; if(n >= 1e3) return (n / 1e3).toFixed(1).replace('.0', '') + 'K'; return '' + n; }
function v4ShortCard(it){
  const id = it.id.videoId, sn = it.snippet || {};
  const ava = (sn.channelTitle || '?').trim().charAt(0).toUpperCase();
  return '<section class="v4-short" data-vid="' + id + '">' +
    '<img class="bg" src="https://i.ytimg.com/vi/' + id + '/hqdefault.jpg" alt="">' +
    '<div class="v4-short-prog"></div><div class="v4-short-spin"><i></i></div>' +
    '<div class="v4-short-rail">' +
      '<button class="v4-sbtn" data-act="like"><span class="ic">❤</span><span>' + v4FmtCount(it.view_count) + '</span></button>' +
      '<button class="v4-sbtn" data-act="mute"><span class="ic">' + (v4ShortsMuted ? '🔇' : '🔊') + '</span><span>Sound</span></button>' +
      '<button class="v4-sbtn" data-act="share"><span class="ic">⤴</span><span>Share</span></button>' +
      '<button class="v4-sbtn" data-act="dl"><span class="ic">⬇</span><span>Save</span></button>' +
    '</div>' +
    '<div class="v4-short-meta"><div class="v4-short-chan"><span class="v4-short-ava">' + v4Esc(ava) + '</span>' + v4Esc(sn.channelTitle || '') + '</div>' +
    '<div class="v4-short-title">' + v4Esc(sn.title || '') + '</div></div></section>';
}
/* Update 142: shorts ka embed fallback — enablejsapi ke
   sath, playVideo command se khud chal pare (tap na
   karna pare). */
function v4ShortForceEmbed(sec, v, spin){
  if(!sec || sec.dataset.fbk) return;
  sec.dataset.fbk = '1';
  const vid = sec.getAttribute('data-vid');
  try{ if(v) v.pause(); }catch(e){}
  if(v && v.parentNode) v.remove();
  const ifr = document.createElement('iframe');
  ifr.src = 'https://www.youtube-nocookie.com/embed/' + vid + '?autoplay=1&enablejsapi=1&rel=0&playsinline=1&modestbranding=1';
  ifr.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture; fullscreen');
  ifr.setAttribute('allowfullscreen', '');
  ifr.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:0';
  sec.insertBefore(ifr, sec.children[1] || null);
  const kick = function(){ try{ ifr.contentWindow.postMessage('{"event":"command","func":"playVideo","args":""}', '*'); }catch(e){} };
  ifr.addEventListener('load', function(){ kick(); setTimeout(kick, 1200); });
  if(spin) spin.style.display = 'none';
  const bg2 = sec.querySelector('img.bg'); if(bg2) bg2.style.display = 'none';
}
function v4ShortActivate(sec){
  const vid = sec.getAttribute('data-vid');
  if(vid) v4SeenAdd([vid]);
  const _sit = v4ShortsItems[vid]; if(_sit && _sit.snippet && _sit.snippet.title) v4InterestAdd(_sit.snippet.title.replace(/[^a-zA-Z0-9 ]/g, ' ').split(/\s+/).filter(function(w){ return w.length > 2; }).slice(0, 3).join(' '), 1);
  if(sec.dataset.fbk) return;
  if(sec.querySelector('video')) return;
  const spin = sec.querySelector('.v4-short-spin'); if(spin){ if(spin.dataset.fail){ spin.innerHTML = ''; delete spin.dataset.fail; } spin.style.display = 'flex'; }
  const v = document.createElement('video');
  v.setAttribute('playsinline', ''); v.loop = true; v.muted = v4ShortsMuted;
  v.poster = 'https://i.ytimg.com/vi/' + vid + '/hqdefault.jpg';
  /* Update 121: APK mein short PHONE ki direct stream se chalti hai
     (server wala intezar-page sirf fallback); agli short ki stream
     pehle se mangwa lete hain taake swipe par foran chale. */
  v4ShortPreloadNext(sec);
  const _cachedUrl = v4StreamCache[vid];
  if(_cachedUrl){ v.src = _cachedUrl; }
  else if(window.PlayTubeApp && PlayTubeApp.phoneStream){
    /* Update 142: phone stream 4s mein na aye to SEEDHA
       embed — beech wala sust server-stream intezar
       khatam. Fail-cache wali par intezar hi nahi. */
    if(v4StreamFail[vid] && (Date.now() - v4StreamFail[vid] < 120000)){
      setTimeout(function(){ if(sec.contains(v)) v4ShortForceEmbed(sec, v, spin); }, 60);
    } else {
      let _got = false;
      v4PhoneStreamGet(vid).then(function(url){
        if(!sec.contains(v)) return;
        if(url){ _got = true; if(!(v.getAttribute('src') && v.readyState >= 2)){ v.src = url; const p3 = v.play(); if(p3 && p3.catch) p3.catch(function(){ v.muted = true; const p4 = v.play(); if(p4 && p4.catch) p4.catch(function(){}); }); } }
        else if(!v.getAttribute('src')){ v4ShortForceEmbed(sec, v, spin); }
      });
      setTimeout(function(){ if(sec.contains(v) && !_got && !v.getAttribute('src')) v4ShortForceEmbed(sec, v, spin); }, 4000);
    }
  }
  else { setTimeout(function(){ if(sec.contains(v)) v4ShortForceEmbed(sec, v, spin); }, 60); }
  /* Update 139: latki hui stream par pehle watchdog ek
     hi dafa chalta tha — ab har koshish ki apni 7s ghari
     hai aur 16s ki HARD deadline par embed lazmi khulta
     hai. Kaali screen par latakna khatam. */
  let attempts = 0, dead = false, wdT = null;
  const forceEmbed = function(){
    if(sec.dataset.fbk) return;
    sec.dataset.fbk = '1';
    try{ v.pause(); }catch(e){}
    if(v.parentNode) v.remove();
    const ifr = document.createElement('iframe');
    ifr.src = 'https://www.youtube-nocookie.com/embed/' + vid + '?autoplay=1&rel=0&playsinline=1&modestbranding=1';
    ifr.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture; fullscreen');
    ifr.setAttribute('allowfullscreen', '');
    ifr.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:0';
    sec.insertBefore(ifr, sec.children[1] || null);
    if(spin) spin.style.display = 'none';
    const bg2 = sec.querySelector('img.bg'); if(bg2) bg2.style.display = 'none';
  };
  const armWd = function(){ clearTimeout(wdT); wdT = setTimeout(function(){ if(sec.contains(v) && !dead && v.readyState < 3) retry(); }, 7000); };
  const retry = function(){
    if(!sec.contains(v) || dead) return;
    attempts++;
    dead = true; clearTimeout(wdT); v4ShortForceEmbed(sec, v, spin);
  };
  armWd();
  setTimeout(function(){ if(sec.contains(v) && v.readyState < 3) v4ShortForceEmbed(sec, v, spin); }, 10000);
  v.addEventListener('playing', function(){ clearTimeout(wdT); if(spin) spin.style.display = 'none'; const bg = sec.querySelector('img.bg'); if(bg) bg.style.display = 'none'; });
  v.addEventListener('error', function(){ if(sec.contains(v)) v4ShortForceEmbed(sec, v, spin); });
  const prog = sec.querySelector('.v4-short-prog');
  v.addEventListener('timeupdate', function(){ if(v.duration) prog.style.width = (v.currentTime / v.duration * 100) + '%'; });
  sec.insertBefore(v, sec.children[1] || null);
  const p = v.play(); if(p && p.catch) p.catch(function(){});
}
function v4ShortDeactivate(sec){
  const v = sec.querySelector('video');
  if(v){ try{ v.pause(); v.removeAttribute('src'); v.load(); }catch(e){} v.remove(); }
  const ifr = sec.querySelector('iframe'); if(ifr) ifr.remove(); if(sec.dataset.fbk) delete sec.dataset.fbk;
  const bg = sec.querySelector('img.bg'); if(bg) bg.style.display = '';
  const prog = sec.querySelector('.v4-short-prog'); if(prog) prog.style.width = '0';
  const spin = sec.querySelector('.v4-short-spin'); if(spin) spin.style.display = 'none';
}
function v4FetchT(url, ms){ const c = new AbortController(); const t = setTimeout(function(){ c.abort(); }, ms || 30000); return fetch(url, {signal: c.signal}).then(function(r){ clearTimeout(t); return r; }, function(e){ clearTimeout(t); throw e; }); }
function v4ShortsRenderItems(items, hasMore){
  const track = v4$('v4-shorts-track'); if(!track) return;
  items.forEach(function(it){
    v4ShortsItems[it.id.videoId] = it;
    if(track.querySelector('[data-vid="' + it.id.videoId + '"]')) return;
    const div = document.createElement('div'); div.innerHTML = v4ShortCard(it);
    const sec = div.firstChild; track.appendChild(sec);
    if(v4ShortsObs) v4ShortsObs.observe(sec);
  });
  v4SeenAdd(items.map(function(it){ return it.id.videoId; }));
  v4ShortsSeenAdd(items.map(function(it){ return it.id.videoId; }));
  v4ShortsPage++;
  if(!hasMore) v4ShortsDone = true;
  /* Update 142: pehli 3 shorts ki stream pehle se garam —
     khulte/swipe par intezar nahi. */
  items.slice(0, 3).forEach(function(it){ if(it.id && it.id.videoId) v4PhoneStreamGet(it.id.videoId); });
}
/* Update 125: Shorts bhi har dafa NAYI — dikhi hui shorts
   localStorage mein yaad (500 tak), agli list un ke baghair;
   seeds (server wale FEED_SHORTS_POOL ki copy) rotation se. */
const v4_SHORTS_SEEDS = ['trending shorts #shorts', 'viral shorts #shorts', 'funny shorts #shorts', 'comedy shorts hindi #shorts', 'cricket shorts #shorts', 'pakistani drama shorts #shorts', 'dance shorts #shorts', 'naat shorts #shorts', 'motu patlu shorts #shorts', 'pubg shorts #shorts', 'movie shorts #shorts', 'poetry shorts #shorts'];
let v4ShortsRot = (Math.random() * 12) | 0;
function v4ShortsSeenParam(){
  const a = v4SeenParam() ? v4SeenParam().split(',') : [];
  const b = v4ShortsSeenGet().slice(-200);
  const seen = {}; const out = [];
  a.concat(b).forEach(function(x){ if(x && !seen[x]){ seen[x] = 1; out.push(x); } });
  return out.join(',');
}
function v4ShortsSeenGet(){ try{ return JSON.parse(localStorage.getItem('pt_shorts_seen') || '[]'); }catch(e){ return []; } }
function v4ShortsSeenAdd(ids){
  try{
    let a = v4ShortsSeenGet();
    const have = {}; a.forEach(function(x){ have[x] = 1; });
    ids.forEach(function(id){ if(id && !have[id]){ a.push(id); have[id] = 1; } });
    if(a.length > 500) a = a.slice(a.length - 500);
    localStorage.setItem('pt_shorts_seen', JSON.stringify(a));
  }catch(e){}
}
function v4ShortsSeedNext(){
  const ints = v4InterestTop(3);
  const mixed = [];
  v4_SHORTS_SEEDS.forEach(function(s, i){ mixed.push(s); if(ints.length && i % 4 === 3) mixed.push(ints[((i / 4) | 0) % ints.length] + ' shorts'); });
  v4ShortsRot++;
  return mixed[v4ShortsRot % mixed.length];
}
async function v4ShortsPhoneLoad(){
  try{
    if(!(window.PlayTubeApp && PlayTubeApp.phoneSearch)) return false;
    const seenS = {}; v4ShortsSeenGet().forEach(function(x){ seenS[x] = 1; });
    let q = v4ShortsQuery || 'trending shorts';
    if(q.toLowerCase().indexOf('shorts') < 0) q += ' shorts';
    /* Pehle asal query (agli page bhi), phir rotation seeds —
       jab tak 10 NAYI shorts na mil jayein; dikhi hui kabhi
       dobara nahi, list khatam bhi nahi (hasMore=true). */
    const got = [];
    const have = {};
    for(let round = 0; round < 3 && got.length < 10; round++){
      let items = null;
      if(round === 0){
        if(v4ShortsPage > 0 && PlayTubeApp.phoneSearchMore) items = await v4PhoneBridge('phoneSearchMore', q);
        if(!items || !items.length) items = await v4PhoneBridge('phoneSearch', q);
      } else {
        items = await v4PhoneBridge('phoneSearch', v4ShortsSeedNext());
      }
      if(!items || !items.length) continue;
      items.forEach(function(it){
        if(!it.id || have[it.id] || seenS[it.id]) return;
        const _sd = it.duration || 0; if(_sd <= 0 || _sd > 70) return;
        have[it.id] = 1;
        got.push({id:{videoId: it.id}, snippet:{title: it.title || '', channelTitle: it.channel || ''}, view_count: (it.views != null && it.views >= 0) ? it.views : 0, duration: it.duration || 0});
      });
    }
    if(!got.length) return false;
    v4ShortsRenderItems(got, true);
    return true;
  }catch(e){ return false; }
}
async function v4ShortsLoad(){
  if(v4ShortsLoading || v4ShortsDone) return;
  v4ShortsLoading = true;
  /* Update 121: APK mein shorts ki list bhi PHONE se pehle */
  if(window.PlayTubeApp && PlayTubeApp.phoneSearch){
    const okP = await v4ShortsPhoneLoad();
    v4ShortsLoading = false;
    if(okP) return;
  }
  v4FetchT('/api/feed?q=' + encodeURIComponent(v4ShortsQuery) + '&type=shorts&page=' + v4ShortsPage + '&r=sh' + v4ShortsSeq + '&seen=' + encodeURIComponent(v4ShortsSeenParam()) + '&int=' + encodeURIComponent(v4InterestTop(5).join('|')), 30000)
    .then(function(x){ return x.json(); })
    .then(function(d){
      v4ShortsLoading = false;
      const items = (d.items || []).filter(function(it){ return it.id && it.id.videoId; });
      if(!items.length){ v4ShortsPhoneLoad().then(function(ok){ if(!ok) v4ShortsDone = true; }); return; }
      v4ShortsRenderItems(items, !!d.has_more);
    })
    .catch(function(){ v4ShortsLoading = false; v4ShortsPhoneLoad(); });
}
/* Update 121: phone ki direct stream (Shorts ke liye) — cache +
   waiter; Java v4PhoneStreamResult se jawab deta hai. */
const v4StreamCache = {};
const v4StreamWait = {};
const v4StreamFail = {};
function v4PhoneStreamResult(vid, url){
  if(url) v4StreamCache[vid] = url;
  else if(vid) v4StreamFail[vid] = Date.now();
  const w = v4StreamWait[vid]; delete v4StreamWait[vid];
  if(w) w(url || null);
}
function v4PhoneStreamGet(vid){
  if(v4StreamCache[vid]) return Promise.resolve(v4StreamCache[vid]);
  if(!(window.PlayTubeApp && PlayTubeApp.phoneStream)) return Promise.resolve(null);
  return new Promise(function(res){
    if(v4StreamWait[vid]){ const old = v4StreamWait[vid]; v4StreamWait[vid] = function(u){ old(u); res(u); }; return; }
    v4StreamWait[vid] = res;
    try{ PlayTubeApp.phoneStream(vid); }catch(e){ delete v4StreamWait[vid]; res(null); return; }
    setTimeout(function(){ if(v4StreamWait[vid] === res){ delete v4StreamWait[vid]; res(null); } }, 25000);
  });
}
function v4ShortPreloadNext(sec){
  try{
    const nxt = sec.nextElementSibling;
    if(nxt && nxt.getAttribute('data-vid')) v4PhoneStreamGet(nxt.getAttribute('data-vid'));
  }catch(e){}
}
function v4OpenShorts(query){
  v4MiniClose();
  const ov = v4$('v4-shorts'); const _wasOpen = ov.classList.contains('open'); ov.classList.add('open'); v4Lock(true);
  const _q = (query && String(query).trim()) ? String(query).trim() : 'trending shorts';
  /* Update 125: Shorts har OPEN par nayi list (band karke khola
     to fresh) — dikhi hui seen-store se kat jati hain. */
  if(!_wasOpen || _q !== v4ShortsQuery){ v4ShortsQuery = _q; v4ShortsPage = 0; v4ShortsDone = false; v4ShortsSeq = Date.now(); const _tr = v4$('v4-shorts-track'); if(_tr) _tr.innerHTML = ''; ov.removeAttribute('data-init'); }
  if(!v4ShortsObs){
    v4ShortsObs = new IntersectionObserver(function(es){
      es.forEach(function(en){
        if(en.intersectionRatio >= 0.6) v4ShortActivate(en.target);
        else v4ShortDeactivate(en.target);
      });
    }, {root: v4$('v4-shorts-track'), threshold: [0, 0.6]});
    v4$('v4-shorts-track').addEventListener('scroll', function(){
      const t = v4$('v4-shorts-track');
      if(t.scrollTop + t.clientHeight > t.scrollHeight - 900) v4ShortsLoad();
    });
    v4$('v4-shorts-track').addEventListener('click', function(e){
      const sec = e.target.closest('.v4-short'); if(!sec) return;
      const vid = sec.getAttribute('data-vid'); const it = v4ShortsItems[vid];
      const btn = e.target.closest('.v4-sbtn');
      if(btn){
        const act = btn.getAttribute('data-act');
        if(act === 'like'){ btn.classList.toggle('liked'); }
        else if(act === 'mute'){ v4ShortsMuted = !v4ShortsMuted; localStorage.setItem('pt_short_muted', v4ShortsMuted ? '1' : '0'); document.querySelectorAll('#v4-shorts-track video').forEach(function(v){ v.muted = v4ShortsMuted; }); document.querySelectorAll('.v4-sbtn[data-act="mute"] .ic').forEach(function(s){ s.textContent = v4ShortsMuted ? '🔇' : '🔊'; }); }
        else if(act === 'dl'){ v4CloseShorts(); v4OpenSheet(vid); }
        else if(act === 'share'){
          const url = 'https://www.youtube.com/watch?v=' + vid;
          const sn = (it && it.snippet) || {};
          if(navigator.share){ navigator.share({title: sn.title || 'Playza Short', url: url}).catch(function(){}); }
          else if(navigator.clipboard){ navigator.clipboard.writeText(url); v4Toast('Link copy ho gaya'); }
        }
        return;
      }
      const v = sec.querySelector('video');
      if(v){
        if(v.paused){ const p = v.play(); if(p && p.catch) p.catch(function(){}); }
        else v.pause();
      } else {
        v4ShortActivate(sec);
      }
    });
  }
  if(!ov.getAttribute('data-init')){ ov.setAttribute('data-init', '1'); v4ShortsSeq = Date.now(); v4ShortsLoad(); }
  /* Update 139: list bilkul khali rahe to kaali screen
     nahi — saaf paigham + dobara wala button. */
  setTimeout(function(){
    const tr = v4$('v4-shorts-track');
    if(ov.classList.contains('open') && tr && !tr.querySelector('.v4-short') && !tr.querySelector('.v4-shorts-msg')){
      tr.innerHTML = '<div class="v4-shorts-msg" style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#fff;padding:24px;text-align:center"><div>Shorts load nahi ho sakin</div><button class="v4-btn2" onclick="v4ShortsRetry()">↻ Dobara try karein</button></div>';
    }
  }, 12000);
}
function v4ShortsRetry(){
  const tr = v4$('v4-shorts-track'); if(tr) tr.innerHTML = '';
  v4ShortsDone = false; v4ShortsPage = 0; v4ShortsSeq = Date.now();
  v4ShortsLoad();
}
function v4CloseShorts(){
  v4$('v4-shorts').classList.remove('open'); v4Lock(false);
  document.querySelectorAll('.v4-short').forEach(function(s){ v4ShortDeactivate(s); });
}

async function v4LoadRelated(v){
  const el = v4$('v4-related'); if(!el) return;
  const cands = [];
  const kw = (v.title || '').split(' ').slice(0, 4).join(' ').trim();
  if(kw) cands.push(kw);
  if(v.channel && cands.indexOf(v.channel) < 0) cands.push(v.channel);
  const top = v4InterestTop(1)[0];
  if(top && cands.indexOf(top) < 0) cands.push(top);
  cands.push('trending');
  for(let i = 0; i < cands.length; i++){
    await v4LoadFeed('v4-related', cands[i]);
    if(el.querySelectorAll('img').length) return;
  }
}
function v4OpenWatch(v){
  v4Current = v;
  if(v && v.videoId) v4SeenAdd([v.videoId]);
  if(v.channel) v4InterestAdd(v.channel, 1);
  if(v.title) v4InterestAdd(v.title.replace(/[^\p{L}\p{N} ]/gu, ' ').split(/\s+/).filter(function(w){ return w.length > 2; }).slice(0, 3).join(' '), 1);
  if(v4State.view !== 'watch') v4PrevView = v4State.view;
  v4FrameSetup(v.videoId);
  const _fl = v4$('v4-watch-float'); if(_fl) _fl.style.display = v4NativeMode() ? '' : 'none';
  v4$('v4-watch-title').textContent = v.title || '';
  v4$('v4-watch-channel').textContent = v.channel || '';
  v4Show('watch');
  v4Post('/api/add-history', {video_id:v.videoId, title:v.title || '', channel:v.channel || ''});
  v4LoadRelated(v);
}
function v4Back(){
  const vd = v4$('v4-video');
  if(vd){ try{ vd.pause(); vd.removeAttribute('src'); vd.load(); }catch(e){} }
  v4Show(v4PrevView || 'home');
}
function v4WatchDownload(){ if(v4Current) v4OpenSheet(v4Current.videoId); }

/* ---------- download sheet ---------- */
function v4DlClick(ev, id){
  if(ev) ev.stopPropagation();
  if(!id || id === 'undefined'){ v4Toast('Video ID nahi mili — dobara try karein'); return; }
  /* Update 44: guest bhi sheet khol sakta hai — limit server bataye ga */
  v4OpenSheet(id);
}
function v4FmtHint(f){
  if(f.format === 'm4a') return 'Asal quality awaz';
  if(f.format === 'mp3') return 'Sab devices par chalta hai';
  const h = {'3GP':'Sab se chhoti file, sab se tez','144p':'Bohat halki quality','240p':'Halki file, jaldi download','360p':'Normal saaf quality','480p':'Achi quality, darmiyani size','720p HD':'Bilkul saaf HD quality','1080p HD':'Full HD, bari screen ke liye','1440p (2K)':'2K, bohat saaf','2160p (4K)':'4K, sab se best quality','4320p (8K)':'8K, sab se best quality'};
  if(h[f.label]) return h[f.label];
  /* Update 138: label ki shakl mukhtalif ho sakti hai
     ('720p • HD', '720p • MP4') — unchai nikaal kar hint
     har surat milega, row kabhi khali nahi rahegi. */
  const m = String(f.quality || f.label || '').match(/(\d{3,4})p/);
  const ht = m ? parseInt(m[1]) : 0;
  if(ht >= 2160) return '4K, sab se best quality';
  if(ht >= 1440) return '2K, bohat saaf';
  if(ht >= 1080) return 'Full HD, bari screen ke liye';
  if(ht >= 720) return 'Bilkul saaf HD quality';
  if(ht >= 480) return 'Achi quality, darmiyani size';
  if(ht >= 360) return 'Normal saaf quality';
  if(ht >= 240) return 'Halki file, jaldi download';
  if(ht > 0) return 'Bohat halki quality';
  if(/3gp/i.test(f.label || '')) return 'Sab se chhoti file, sab se tez';
  return 'Video file';
}
/* Update 138: ek jaisi rows (masalan do MP3 128) merge —
   jis ke paas size ho wo rehti hai. */
function v4DedupeFmts(arr){
  const seen = {}, out = [];
  (arr || []).forEach(function(f){
    const k = (f.format || '') + '|' + (f.quality || f.label || '');
    if(seen[k] !== undefined){
      if(out[seen[k]].size_mb == null && f.size_mb != null) out[seen[k]] = f;
      return;
    }
    seen[k] = out.length; out.push(f);
  });
  return out;
}
function v4FriendlyErr(e){ const s = String(e || ''); if(/sign in to confirm|not a bot|bot-check/i.test(s)) return 'YouTube ne server ko kuch der ke liye roka hai — ye rukawat khud khatam ho jati hai, 10-15 minute baad dobara try karein'; if(/timed out|timeout|network|failed to fetch/i.test(s)) return 'Network masla — net check karke dobara try karein'; return s; }
function v4NativeMode(){ try{ return !!(window.PlayTubeApp && PlayTubeApp.nativeAvailable && PlayTubeApp.nativeAvailable()); }catch(e){ return false; } }
let v4NativeFmtWait = null;
function v4NativeFormatsResult(jsonStr, errStr){ window._v4NativeErr = errStr || ''; const w = v4NativeFmtWait; v4NativeFmtWait = null; if(!w) return; if(!jsonStr){ w(null); return; } try{ w(JSON.parse(jsonStr)); }catch(e){ w(null); } }
function v4NativeFormats(id){ return new Promise(function(res){ v4NativeFmtWait = res; try{ PlayTubeApp.nativeFormats(id); }catch(e){ v4NativeFmtWait = null; res(null); return; } setTimeout(function(){ if(v4NativeFmtWait === res){ v4NativeFmtWait = null; res(null); } }, 25000); }); }
async function v4OpenSheet(id, audioOnly){
  const v = v4Videos[id] || {videoId:id, title:'', channel:''};
  v4Sheet = {id:id, sel:null, audioOnly: !!audioOnly};
  v4$('v4-sheet-thumb').src = 'https://i.ytimg.com/vi/' + id + '/hqdefault.jpg';
  v4$('v4-sheet-title').textContent = v.title || '';
  v4$('v4-sheet-channel').textContent = v.channel || '';
  v4$('v4-sheet-list').innerHTML = '<p class="v4-muted">Formats load ho rahe hain...</p>';
  v4$('v4-sheetwrap').classList.add('open');
  v4Lock(true);
  const pl = v4$('v4-player');
  if(pl && pl.contentWindow){ try{ pl.contentWindow.postMessage('{"event":"command","func":"pauseVideo","args":""}', '*'); }catch(e){} }
  const vd0 = v4$('v4-video');
  if(vd0 && !vd0.paused){ try{ vd0.pause(); }catch(e){} }
  const btn = v4$('v4-sheet-download');
  if(v4State.config && v4State.config.toggles && v4State.config.toggles.downloads_enabled === false){ btn.disabled = true; btn.textContent = 'Downloads band hain'; }
  else { btn.disabled = false; btn.textContent = 'Download'; }
  const list = v4$('v4-sheet-list');
  let d = null;
  window._v4NativeErr = '';
  let _srvWhy = '';
  const tryServer = async function(){
    const r = await v4Fetch('/api/formats/' + id);
    if(r.ok && r.data && !r.data.error){ if(window._v4NativeErr) r.data.nativeErr = window._v4NativeErr; return r.data; }
    _srvWhy = (r.data && r.data.error) ? v4FriendlyErr(r.data.error) : 'Server se jawab nahi aya — net bohat slow hai ya server busy hai';
    return null;
  };
  const tryNative = async function(){
    if(!v4NativeMode()) return null;
    const nd = await v4NativeFormats(id);
    if(nd && !nd.error){ nd.nativeMode = true; return nd; }
    return null;
  };
  d = await tryNative();
  if(!d) d = await tryServer();
  if(!d){
    /* Update 126: ek nakami par error NAHI — 2 second ruk kar
       dono raste DOBARA try hote hain (server ki bot-lehar aur
       phone ki UNPLAYABLE aksar kuch hi seconds mein theek ho
       jati hai). Error sirf doosri nakami par. */
    list.innerHTML = '<p class="v4-muted">Formats late a rahe hain — dobara koshish ho rahi hai...</p>';
    await new Promise(function(res){ setTimeout(res, 2000); });
    d = await tryNative();
    if(!d) d = await tryServer();
  }
  if(!d){
    const nerr = window._v4NativeErr ? ' Phone se bhi nahi mila: ' + v4Esc(window._v4NativeErr) : '';
    list.innerHTML = '<p class="v4-muted">Formats nahi mil sake: ' + v4Esc(_srvWhy) + nerr + '</p>' +
      '<button data-id="' + id + '" onclick="v4OpenSheet(this.dataset.id)" style="margin-top:10px;padding:10px 22px;border:none;border-radius:999px;background:linear-gradient(90deg,#7c3aed,#06b6d4);color:#fff;font-weight:700;font-size:15px;cursor:pointer">↻ Dobara try karein</button>';
    return;
  }
  if(d.title) v4$('v4-sheet-title').textContent = d.title;
  if(d.channel) v4$('v4-sheet-channel').textContent = d.channel;
  const row = function(f){ const music = (f.format === 'mp3' || f.format === 'm4a'); return '<div class="v4-fmtrow" data-fmt="' + f.format + '" data-q="' + (f.quality || '') + '" data-nk="' + (f.native_key || '') + '" onclick="v4PickFmt(this)"><span class="ic">' + (music ? '🎵' : '▶') + '</span><span class="tx"><span class="nm">' + v4Esc(f.label) + '</span><span class="hint">' + v4FmtHint(f) + '</span></span>' + (f.size_mb != null ? '<span class="sz">' + (f.size_est ? '≈ ' : '') + f.size_mb + ' MB</span>' : '') + '<span class="v4-radio">✓</span></div>'; };
  const modeNote = d.nativeMode
    ? '<div class="v4-sect" style="color:#2dd4bf">📱 Phone se formats — download phone se hoga, server wala bot-error nahi ayega</div>'
    : (window.PlayTubeApp ? '<div class="v4-sect" style="color:#fbbf24">⚠ Ye formats SERVER se aye hain' + (d.nativeErr ? ' — phone wala rasta fail hua: ' + v4Esc(String(d.nativeErr).slice(0, 120)) : ' — phone download ke liye naya APK (v2.0+) install karein') + '</div>' : '');
  list.innerHTML = modeNote + '<div class="v4-sect">MUSIC / AUDIO</div>' + v4DedupeFmts(d.music).map(row).join('') + (v4Sheet.audioOnly ? '' : '<div class="v4-sect">VIDEO</div>' + v4DedupeFmts(d.video).map(row).join(''));
  let target = null;
  list.querySelectorAll('.v4-fmtrow').forEach(function(el){ if(el.getAttribute('data-q') === v4State.settings.defQuality) target = el; });
  if(!target) list.querySelectorAll('.v4-fmtrow').forEach(function(el){ if(el.getAttribute('data-q') === '360p') target = el; });
  if(!target && v4Sheet.audioOnly) target = list.querySelector('.v4-fmtrow');
  if(target) target.click();
}
function v4PickFmt(el){
  document.querySelectorAll('#v4-sheet-list .v4-fmtrow').forEach(function(x){ x.classList.remove('sel'); });
  el.classList.add('sel');
  v4Sheet.sel = {format: el.getAttribute('data-fmt'), quality: el.getAttribute('data-q') || null, nk: el.getAttribute('data-nk') || ''};
}
function v4CloseSheet(){ v4$('v4-sheetwrap').classList.remove('open'); v4Lock(false); }
function v4SheetDownload(){
  if(!v4Sheet.sel){ v4Toast('Pehle ek quality chunein'); return; }
  if(v4NativeMode() && v4Sheet.sel.nk && !v4GuestGate()){ v4CloseSheet(); v4OpenAuth('signin', false, 'limit'); v4Toast('Guest limit khatam — pehle account banayein'); return; }
  if(v4NativeMode() && v4Sheet.sel.nk){ try{ PlayTubeApp.nativeDownload(v4Sheet.id, v4Sheet.sel.nk, v4$('v4-sheet-title').textContent || ''); v4CloseSheet(); }catch(e){ v4Toast('Phone download shuru nahi ho saka'); } return; }
  const params = {video_id: v4Sheet.id, format: v4Sheet.sel.format, quality: v4Sheet.sel.quality, title: v4$('v4-sheet-title').textContent || ''};
  v4StartDownload(params);
}
async function v4StartDownload(params){
  if(params && params.video_id) v4SeenAdd([params.video_id]);
  if(params && params.title) v4InterestAdd(params.title.replace(/[^a-zA-Z0-9 ]/g, ' ').split(/\s+/).filter(function(w){ return w.length > 2; }).slice(0, 3).join(' '), 1);
  const body = Object.assign({}, params, {download_id: 'v4_' + Date.now()});
  const r = await v4Post('/api/start-download', body);
  if(r.ok && r.data && r.data.success){ if(r.data.already){ v4CloseSheet(); v4Toast('Ye video pehle se Downloads mein hai'); v4LoadDownloads(); return; } v4CloseSheet(); if(r.data.guest_remaining != null){ const left = Math.max(0, r.data.guest_remaining - 1); v4Toast(left > 0 ? ('Download shuru — guest ke ab ' + left + ' free downloads baqi hain') : 'Download shuru — ye guest ka akhri free download hai, agli ke liye account banayein'); } else v4Toast('Download shuru ho gaya — Downloads me dekhein'); v4LoadDownloads(); return; }
  const d = r.data || {};
  if(d.login_required){ v4Pending = {type:'start', params:params}; v4CloseSheet(); v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); return; }
  if(d.premium_required){ v4CloseSheet(); v4Toast('HD quality ke liye Premium chahiye'); v4Show('premium'); return; }
  v4Toast(v4FriendlyErr(d.error) || 'Download start nahi ho saka');
}

/* ---------- downloads view (unified registry — Bug #3/#9) ---------- */
function v4PhonePollStart(){ v4PhonePollStop(); window._v4phPoll = setInterval(function(){ try{ v4PhoneDlRender(); }catch(e){} }, 2500); }
function v4PhonePollStop(){ if(window._v4phPoll){ clearInterval(window._v4phPoll); window._v4phPoll = null; } }
/* Update 135: Downloads page par bhi EK folder — head
   (pic/name) par click se khulta/band hota hai; andar
   downloading pehle, waiting (paused) neeche. */
function v4PhoneFolderHtml(active){
  const run = active.filter(function(p){ return p.status === 'running' || p.status === 'starting'; });
  const wait = active.filter(function(p){ return p.status === 'paused'; });
  const ordered = run.concat(wait);
  const first = ordered[0] || {};
  const open = window._v4DlFolderOpen !== false;
  return '<div class="v4-dlfolder"><div class="v4-dlf-head" onclick="v4DlFolderToggle()">'
    + (first.videoId ? '<span class="v4-dlf-th">' + v4Img(first.videoId) + '</span>' : '<span style="font-size:22px">📥</span>')
    + '<div class="tt"><div class="t1">📥 Downloads</div><div class="t2">' + run.length + ' downloading • ' + wait.length + ' waiting — kul ' + active.length + '</div></div>'
    + '<span style="margin-left:auto;font-size:15px">' + (open ? '▾' : '▸') + '</span></div>'
    + (open ? '<div class="v4-dlf-body">' + ordered.map(v4PhoneRowHtml).join('') + '</div>' : '')
    + '</div>';
}
function v4DlFolderToggle(){ window._v4DlFolderOpen = (window._v4DlFolderOpen === false); window._v4phSig = ''; v4PhoneDlRender(); }
function v4SrvFolderToggle(){ window._v4SrvFolderOpen = (window._v4SrvFolderOpen === false); v4RenderDownloads(); }
function v4PhoneRowHtml(p){
  const th = p.videoId ? v4Img(p.videoId) : '<span style="width:64px;text-align:center;font-size:22px">📱</span>';
  let t2 = '', btns = '';
  const pid = v4Esc(p.id || '');
  if(p.status === 'running'){
    t2 = '<span data-pdmb>' + v4Esc(p.doneMB || '0') + ' / ' + v4Esc(p.totalMB || '?') + ' MB</span> • <span data-pdsp>' + v4Esc(p.speed || '') + '</span> • <span data-pdpct>' + (p.percent || 0) + '%</span>' + (p.quality ? ' • ' + v4Esc(p.quality) : '');
    btns = '<button class="v4-roundbtn" title="Pause" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="pause">❚❚</button><button class="v4-roundbtn" title="Band karein" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="cancel">✕</button>';
  } else if(p.status === 'paused'){
    t2 = '⏸ Pause hai — ' + v4Esc(p.doneMB || '0') + ' / ' + v4Esc(p.totalMB || '?') + ' MB' + (p.quality ? ' • ' + v4Esc(p.quality) : '');
    btns = '<button class="v4-roundbtn teal" title="Dobara chalayein" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="resume">▶</button><button class="v4-roundbtn" title="Hata dein" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="remove">🗑</button>';
  } else if(p.status === 'starting'){
    t2 = 'Shuru ho raha hai...' + (p.quality ? ' • ' + v4Esc(p.quality) : '');
    btns = '<button class="v4-roundbtn" title="Band karein" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="cancel">✕</button>';
  } else if(p.status === 'failed'){
    t2 = '<span style="color:var(--v4danger)">Fail ho gaya — sheet se dobara try karein</span>';
    btns = '<button class="v4-roundbtn" title="Hata dein" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="remove">🗑</button>';
  } else {
    t2 = 'Band kar diya';
    btns = '<button class="v4-roundbtn" title="Hata dein" data-pid="' + pid + '" onclick="v4PhoneAct(this)" data-act="remove">🗑</button>';
  }
  const bar = (p.status === 'running' || p.status === 'paused') ? '<div class="v4-bar"><i data-pdbar style="width:' + (p.percent || 0) + '%"></i></div>' : '';
  return '<div class="v4-dlrow" data-prow="' + pid + '">' + th + '<div class="tt"><div class="t1">' + v4Esc(p.title || '') + '</div>' + bar + '<div class="t2">' + t2 + '</div></div>' + btns + '</div>';
}
/* Update 137: complete video ki pic ya naam par click —
   wahi downloaded file player mein khulti hai (us player
   mein download option nahi, sirf play). */
function v4PlayStored(el){
  const fn = el.getAttribute('data-fn') || '', t = el.getAttribute('data-t') || '';
  if(window.PlayTubeApp && PlayTubeApp.playDownloaded){ PlayTubeApp.playDownloaded(fn, t); }
  else v4Toast('Downloaded video sirf Playza app mein chalti hai');
}
function v4LocalPlayResult(ok){ if(!ok) v4Toast('Video ki file phone mein nahi mili — shayad delete ho gayi hai'); }
function v4PhoneStoredRow(s){
  const th = s.videoId ? v4Img(s.videoId) : '<span style="width:64px;text-align:center;font-size:22px">📱</span>';
  const meta = [s.quality || '', s.totalMB ? s.totalMB + ' MB' : '', '✓ Phone ke Playza folder mein hai'].filter(Boolean).join(' • ');
  const attrs = ' data-fn="' + v4Esc(s.fileName || '') + '" data-t="' + v4Esc(s.title || '') + '" onclick="v4PlayStored(this)"';
  return '<div class="v4-dlrow"><span' + attrs + ' style="position:relative;display:block;cursor:pointer;flex:none">' + th + '<span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:20px;color:#fff;text-shadow:0 1px 6px rgba(0,0,0,.85)">▶</span></span><div class="tt"><div class="t1"' + attrs + ' style="cursor:pointer">' + v4Esc(s.title || '') + '</div><div class="t2">' + v4Esc(meta) + '</div></div><button class="v4-roundbtn" title="List se hata dein" data-t="' + v4Esc(s.title || '') + '" data-q="' + v4Esc(s.quality || '') + '" onclick="v4PhoneStoredDel(this)">🗑</button></div>';
}
function v4PhoneAct(btn){
  const id = btn.getAttribute('data-pid'), act = btn.getAttribute('data-act');
  if(!id || !window.PlayTubeApp) return;
  try{
    if(act === 'pause' && PlayTubeApp.phoneDlPause) PlayTubeApp.phoneDlPause(id);
    else if(act === 'resume' && PlayTubeApp.phoneDlResume) PlayTubeApp.phoneDlResume(id);
    else if(act === 'cancel' && PlayTubeApp.phoneDlCancel) PlayTubeApp.phoneDlCancel(id);
    else if(act === 'remove' && PlayTubeApp.phoneDlRemove) PlayTubeApp.phoneDlRemove(id);
  }catch(e){}
  window._v4phSig = '';
  setTimeout(function(){ try{ v4PhoneDlRender(); }catch(e){} }, 400);
}
function v4PhoneStoredDel(btn){
  const t = btn.getAttribute('data-t') || '', q = btn.getAttribute('data-q') || '';
  try{
    if(window.PlayTubeApp && PlayTubeApp.phoneDlState && PlayTubeApp.phoneDlRemove){
      const live = JSON.parse(PlayTubeApp.phoneDlState() || '[]');
      live.forEach(function(p){ if(p.status === 'done' && (p.title || '') === t && (p.quality || '') === q){ try{ PlayTubeApp.phoneDlRemove(p.id); }catch(e){} } });
    }
  }catch(e){}
  let stored = []; try{ stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]'); }catch(e){}
  stored = stored.filter(function(s){ return !((s.title || '') === t && (s.quality || '') === q); });
  try{ localStorage.setItem('pt_phone_dl', JSON.stringify(stored)); }catch(e){}
  window._v4phSig = '';
  v4PhoneDlRender();
}
function v4DlEmptyFix(){
  const pa = v4$('v4-phone-active'), pdn = v4$('v4-phone-done');
  const da = v4$('v4-dl-active'), dd = v4$('v4-dl-done');
  if(da && pa && pa.children.length && da.querySelector('.v4-muted')) da.innerHTML = '';
  if(dd && pdn && pdn.children.length && (dd.querySelector('.v4-muted') || dd.querySelector('.v4-empty'))) dd.innerHTML = '';
}
function v4PhoneDlRender(){
  const boxA = v4$('v4-phone-active'); if(!boxA) return;
  const boxD = v4$('v4-phone-done'); if(!boxD) return;
  let live = [];
  if(v4NativeMode() && window.PlayTubeApp && PlayTubeApp.phoneDlState){
    try{ live = JSON.parse(PlayTubeApp.phoneDlState() || '[]'); }catch(e){}
  }
  let stored = []; try{ stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]'); }catch(e){}
  let changed = false;
  live.forEach(function(p){
    if(p.status === 'done'){
      const k = (p.title || '') + '|' + (p.quality || '');
      if(!stored.some(function(s){ return ((s.title || '') + '|' + (s.quality || '')) === k; })){ stored.unshift({title: p.title || '', quality: p.quality || '', videoId: p.videoId || '', totalMB: p.totalMB || '', fileName: p.fileName || '', ts: Date.now()}); changed = true; v4GuestPhoneDone(p.videoId || ''); }
    }
  });
  if(changed){ try{ localStorage.setItem('pt_phone_dl', JSON.stringify(stored.slice(0, 50))); }catch(e){} }
  const liveKeys = {}; live.forEach(function(p){ if(p.status !== 'done') liveKeys[(p.title || '') + '|' + (p.quality || '')] = 1; });
  const active = live.filter(function(p){ return p.status === 'running' || p.status === 'paused' || p.status === 'starting'; });
  const bad = live.filter(function(p){ return p.status === 'failed' || p.status === 'stopped'; });
  const sig = live.map(function(p){ return p.id + ':' + p.status; }).join(',') + '#' + stored.length + (window._v4DlFolderOpen === false ? '#c' : '#o');
  if(sig !== window._v4phSig){
    window._v4phSig = sig;
    boxA.innerHTML = active.length ? v4PhoneFolderHtml(active) : '';
    const boxF = v4$('v4-phone-failed');
    if(boxF) boxF.innerHTML = bad.map(v4PhoneRowHtml).join('');
    let doneHtml = '';
    stored.forEach(function(s){ if(liveKeys[(s.title || '') + '|' + (s.quality || '')]) return; doneHtml += v4PhoneStoredRow(s); });
    boxD.innerHTML = doneHtml;
  } else {
    live.forEach(function(p){
      if(p.status !== 'running') return;
      const row = boxA.querySelector('[data-prow="' + p.id + '"]'); if(!row) return;
      const b = row.querySelector('[data-pdbar]'); if(b) b.style.width = (p.percent || 0) + '%';
      const m = row.querySelector('[data-pdmb]'); if(m) m.textContent = (p.doneMB || '0') + ' / ' + (p.totalMB || '?') + ' MB';
      const sp = row.querySelector('[data-pdsp]'); if(sp) sp.textContent = p.speed || '';
      const pc = row.querySelector('[data-pdpct]'); if(pc) pc.textContent = (p.percent || 0) + '%';
    });
  }
  const acEl2 = v4$('v4-dl-actcount');
  if(acEl2){ const tot = (window._v4srvAct || 0) + active.length; acEl2.textContent = tot ? '(' + tot + ')' : ''; }
  v4DlEmptyFix();
  v4FailSectSync();
}
async function v4LoadDownloads(){
  try{
    const res = await Promise.all([v4Fetch('/api/download-progress'), v4Fetch('/api/downloads-list')]);
    if(res[0].ok) v4DlData.progress = res[0].data || {};
    if(res[1].ok && res[1].data) v4DlData.list = res[1].data.downloads || []; window._v4DlCache = v4DlData.list;
    v4RenderDownloads(); v4UpdateBadge();
  }catch(e){}
}
function v4UpdateBadge(){
  let n = 0;
  Object.values(v4DlData.progress || {}).forEach(function(s){ if(['starting','downloading','processing'].indexOf(s.status) >= 0) n++; });
  const b = v4$('v4-dl-badge'); if(b){ b.textContent = n; b.style.display = n ? 'inline-block' : 'none'; }
}
let v4DlType = 'all';
function v4DlFilterToggle(){
  const el = v4$('v4-dl-typechips'); if(!el) return;
  const show = el.style.display === 'none';
  if(show){ v4RenderDlTypeChips(); el.style.display = ''; } else el.style.display = 'none';
}
function v4RenderDlTypeChips(){
  const el = v4$('v4-dl-typechips'); if(!el) return;
  const opts = [['all', '📋 Sab'], ['video', '🎬 Sirf Videos'], ['music', '🎵 Sirf Music'], ['failed', '⚠ Fail hui']];
  el.innerHTML = opts.map(function(o){ return '<button class="v4-poprow' + (v4DlType === o[0] ? ' on' : '') + '" data-t="' + o[0] + '" onclick="v4DlSetType(this.dataset.t)">' + o[1] + (v4DlType === o[0] ? ' ✓' : '') + '</button>'; }).join('');
}
function v4DlSetType(t){ v4DlType = t; const el = v4$('v4-dl-typechips'); if(el) el.style.display = 'none'; v4RenderDownloads(); }
document.addEventListener('click', function(e){
  const p = v4$('v4-dl-typechips');
  if(p && p.style.display !== 'none' && !e.target.closest('#v4-dl-filterwrap')) p.style.display = 'none';
});
function v4DlTypeMatch(d){
  if(v4DlType === 'all') return true;
  if(v4DlType === 'failed') return d.status === 'failed';
  const fm = (d.format || '').toUpperCase();
  if(v4DlType === 'music') return (fm === 'MP3' || fm === 'M4A') && d.status === 'completed';
  return ['MP4', '3GP', 'MKV', 'WEBM'].indexOf(fm) >= 0 && d.status === 'completed';
}
let v4DlSel = {on: false, set: {}};
let v4DlMap = {};
let v4MenuId = null;
function v4Lock(on){ try{ document.body.style.overflow = on ? 'hidden' : ''; document.documentElement.style.overflow = on ? 'hidden' : ''; }catch(e){} }
function v4DlSelectMode(){ v4DlSel.on = !v4DlSel.on; if(!v4DlSel.on) v4DlSel.set = {}; v4RenderDownloads(); }
function v4DlToggleSel(id){ if(v4DlSel.set[id]) delete v4DlSel.set[id]; else v4DlSel.set[id] = 1; v4RenderDownloads(); }
function v4DlSelectAll(){
  const ids = (v4DlData.list || []).map(function(d){ return d.downloadId; });
  Object.keys(v4DlData.progress || {}).forEach(function(id){ const s = v4DlData.progress[id]; if(['starting','downloading','processing','paused'].indexOf(s.status) >= 0 && ids.indexOf(id) < 0) ids.push(id); });
  const allOn = ids.length && ids.every(function(id){ return v4DlSel.set[id]; });
  v4DlSel.set = {}; if(!allOn) ids.forEach(function(id){ v4DlSel.set[id] = 1; });
  v4RenderDownloads();
}
async function v4DlBulkPrivate(){
  const ids = Object.keys(v4DlSel.set); if(!ids.length){ v4Toast('Pehle videos select karein'); return; }
  for(let i = 0; i < ids.length; i++){ await v4Post('/api/downloads/private', {download_id: ids[i], private: true}); }
  v4DlSel = {on: false, set: {}}; v4LoadDownloads(); v4Toast(ids.length + ' videos Private folder mein chali gayin');
}
async function v4DlBulkDelete(){
  const ids = Object.keys(v4DlSel.set); if(!ids.length){ v4Toast('Pehle videos select karein'); return; }
  if(!confirm(ids.length + ' select ki hui downloads delete kar dein?')) return;
  for(let i = 0; i < ids.length; i++){ await v4Fetch('/api/delete-download/' + ids[i], {method: 'DELETE'}); }
  v4DlSel = {on: false, set: {}}; v4LoadDownloads(); v4Toast(ids.length + ' downloads delete ho gayin');
}
/* Update 51/57/58: Downloads ki nayi rows — bari thumbnail, play button
   thumbnail ke andar, baqi saare options ⋮ menu mein. Play dabane par
   downloaded file hi chalti hai, dobara download nahi hoti. */
function v4DlRowHtml(d, selOn){
  const vid = d.videoId || '';
  const isSel = selOn && !!v4DlSel.set[d.downloadId];
  const isMusic = ['MP3','M4A'].indexOf((d.format || '').toUpperCase()) >= 0;
  const failed = d.status === 'failed';
  const playAttr = failed ? '' : ' data-id="' + d.downloadId + '" onclick="v4PlayFile(this.dataset.id)"';
  const thumb = '<div class="v4-dlthumb' + (isMusic ? ' music' : '') + '"' + playAttr + '>' + (vid ? v4Img(vid) : '') + (failed ? '' : '<span class="v4-playdot">▶</span>') + '</div>';
  const meta = failed
    ? '<div class="v4-dlmeta" style="color:var(--v4danger)">Fail ho gaya: ' + v4Esc(d.error || 'error') + '</div>'
    : '<div class="v4-dlmeta">' + v4Esc([d.quality || d.format || '', v4MB(d.file_size)].filter(Boolean).join(' • ')) + '</div>';
  const info = '<div class="v4-dlinfo"' + playAttr + '><div class="v4-dltitle">' + v4Esc(d.title || '') + '</div>' + meta + '</div>';
  if(selOn) return '<div class="v4-dlrow2' + (isSel ? ' sel' : '') + '" data-id="' + d.downloadId + '" onclick="v4DlToggleSel(this.dataset.id)"><span class="v4-check' + (isSel ? ' on' : '') + '">✓</span>' + thumb + info + '</div>';
  const retryBtn = (failed && vid && !(d.platform && d.platform !== 'YouTube')) ? '<button class="v4-roundbtn teal" title="Retry — dobara download" data-id="' + d.downloadId + '" onclick="event.stopPropagation();v4RetryDl(this.dataset.id)">↻</button>' : '';
  return '<div class="v4-dlrow2">' + thumb + info + retryBtn + '<button class="v4-dotbtn" data-id="' + d.downloadId + '" onclick="v4DlMenu(this.dataset.id)">⋮</button></div>';
}
function v4PlayFile(id){
  const d = v4DlMap[id] || {};
  v4$('v4-player-title').textContent = d.title || '';
  const vid = v4$('v4-filevideo');
  vid.src = '/api/download-file/' + id + '?play=1';
  v4$('v4-playerwrap').classList.add('open'); v4Lock(true);
  if(vid.play){ const p = vid.play(); if(p && p.catch) p.catch(function(){}); }
}
function v4ClosePlayer(){
  const vid = v4$('v4-filevideo');
  try{ vid.pause(); vid.removeAttribute('src'); vid.load(); }catch(e){}
  v4$('v4-playerwrap').classList.remove('open'); v4Lock(false);
}
function v4DlMenu(id){
  const d = v4DlMap[id]; if(!d) return;
  v4MenuId = id;
  v4$('v4-dlmenu-thumb').src = d.videoId ? ('https://i.ytimg.com/vi/' + d.videoId + '/hqdefault.jpg') : '';
  v4$('v4-dlmenu-title').textContent = d.title || '';
  v4$('v4-dlmenu-meta').textContent = [d.quality || d.format || '', v4MB(d.file_size), d.platform || 'YouTube'].filter(Boolean).join(' • ');
  let h = '';
  if(d.status === 'failed'){
    if(d.videoId) h += '<button class="v4-menurow" data-vid="' + d.videoId + '" onclick="v4MenuRetry(this)">↻ Dobara try karein</button>';
  } else {
    h += '<button class="v4-menurow" onclick="v4MenuPlay()">▶ Play karein</button>';
    h += '<a class="v4-menurow" href="javascript:void(0)" data-id="' + id + '" onclick="v4MenuSavePhone(this.dataset.id)">⬇ Phone mein save karo</a>';
    h += '<button class="v4-menurow" onclick="v4MenuShare()">📤 Share karein</button>';
    h += '<button class="v4-menurow" onclick="v4MenuPrivate()">' + (d.private ? '🔓 Private se nikalo' : '🔒 Private Folder mein daalo') + '</button>';
  }
  h += '<button class="v4-menurow" style="color:var(--v4danger)" onclick="v4MenuDelete()">🗑 Delete file</button>';
  v4$('v4-dlmenu-list').innerHTML = h;
  v4$('v4-dlmenuwrap').classList.add('open'); v4Lock(true);
}
function v4CloseDlMenu(){ v4$('v4-dlmenuwrap').classList.remove('open'); v4Lock(false); }
function v4MenuPlay(){ const id = v4MenuId; v4CloseDlMenu(); v4PlayFile(id); }
function v4MenuShare(){ const d = v4DlMap[v4MenuId] || {}; const id = v4MenuId; v4CloseDlMenu(); v4ShareDl(id, d.title || '', d.format || 'MP4'); }
function v4MenuPrivate(){ const d = v4DlMap[v4MenuId] || {}; const id = v4MenuId; v4CloseDlMenu(); v4PrivToggle(id, !d.private); }
function v4MenuDelete(){ const id = v4MenuId; v4CloseDlMenu(); v4DeleteDl(id); }
function v4MenuRetry(el){ const vid = el.getAttribute('data-vid'); v4CloseDlMenu(); v4OpenSheet(vid); }
function v4FailSectSync(){
  const a = v4$('v4-dl-failed'), b = v4$('v4-phone-failed');
  const n = (a ? a.querySelectorAll('.v4-dlrow').length : 0) + (b ? b.children.length : 0);
  const fc = v4$('v4-dl-failcount'); if(fc) fc.textContent = n ? '(' + n + ')' : '';
}
function v4RenderDownloads(){
  const fEl = v4$('v4-dl-filter'); if(!fEl) return;
  const f = (fEl.value || '').toLowerCase();
  const selbar = v4$('v4-dl-selbar');
  if(selbar){
    if(v4DlSel.on){
      const n = Object.keys(v4DlSel.set).length;
      selbar.style.display = '';
      selbar.innerHTML = '<b style="flex:1">' + n + ' select hain</b>' +
        '<button class="v4-iconbtn" onclick="v4DlSelectAll()">☑ Sab select</button>' +
        '<button class="v4-iconbtn" onclick="v4DlBulkPrivate()">🔒 Private</button>' +
        '<button class="v4-iconbtn" onclick="v4DlBulkDelete()">🗑 Delete</button>' +
        '<button class="v4-iconbtn" onclick="v4DlSelectMode()">✕</button>';
    } else selbar.style.display = 'none';
  }
  const act = [];
  Object.keys(v4DlData.progress || {}).forEach(function(id){ const s = v4DlData.progress[id]; if(['starting','downloading','processing','paused'].indexOf(s.status) >= 0) act.push({id:id, s:s}); });
  const actIds = {}; act.forEach(function(a){ actIds[a.id] = 1; });
  const rowAct = function(a){
    const s = a.s, vid = s.video_id || '', title = s.title || vid || a.id;
    if(f && title.toLowerCase().indexOf(f) < 0) return '';
    const pct = s.percent || 0;
    const meta = [s.quality || s.format_type || '', s.status === 'paused' ? 'Ruka hua' : (pct + '%'), s.speed || ''].filter(Boolean).join(' • ');
    const btn = s.status === 'paused'
      ? '<button class="v4-roundbtn teal" title="Resume" data-id="' + a.id + '" onclick="event.stopPropagation();v4ResumeDl(this.dataset.id)">▶</button>'
      : '<button class="v4-roundbtn" title="Pause" data-id="' + a.id + '" onclick="event.stopPropagation();v4PauseDl(this.dataset.id)">❚❚</button>';
    const del = '<button class="v4-roundbtn" title="Delete" data-id="' + a.id + '" onclick="event.stopPropagation();v4DeleteActiveDl(this.dataset.id)">🗑</button>';
    const rst = s.status === 'paused' ? '' : '<button class="v4-roundbtn" title="Restart — dobara start" data-id="' + a.id + '" onclick="event.stopPropagation();v4RestartDl(this.dataset.id)">↻</button>';
    const isSelA = v4DlSel.on && !!v4DlSel.set[a.id];
    const chk = v4DlSel.on ? '<span class="v4-check' + (isSelA ? ' on' : '') + '">✓</span>' : '';
    const rowClk = v4DlSel.on ? ' data-id="' + a.id + '" onclick="v4DlToggleSel(this.dataset.id)"' : '';
    return '<div class="v4-dlrow' + (isSelA ? ' sel' : '') + '"' + rowClk + '>' + chk + (vid ? v4Img(vid) : '<span style="width:64px"></span>') + '<div class="tt"><div class="t1">' + v4Esc(title) + '</div><div class="v4-bar"><i style="width:' + pct + '%"></i></div><div class="t2">' + v4Esc(meta) + '</div></div>' + btn + rst + del + '</div>';
  };
  const acEl = v4$('v4-dl-actcount'); if(acEl) acEl.textContent = act.length ? '(' + act.length + ')' : ''; window._v4srvAct = act.length;
  if(act.length){
    const sOpen = window._v4SrvFolderOpen !== false;
    const sRun = act.filter(function(a){ return a.s.status !== 'paused'; }).length;
    const sWait = act.length - sRun;
    const fvid = (act[0].s && act[0].s.video_id) || '';
    v4$('v4-dl-active').innerHTML = '<div class="v4-dlfolder"><div class="v4-dlf-head" onclick="v4SrvFolderToggle()">' + (fvid ? '<span class="v4-dlf-th">' + v4Img(fvid) + '</span>' : '<span style="font-size:22px">📥</span>') + '<div class="tt"><div class="t1">📥 Downloads</div><div class="t2">' + sRun + ' downloading • ' + sWait + ' waiting — kul ' + act.length + '</div></div><span style="margin-left:auto;font-size:15px">' + (sOpen ? '▾' : '▸') + '</span></div>' + (sOpen ? '<div class="v4-dlf-body">' + act.map(rowAct).join('') + '</div>' : '') + '</div>';
  } else v4$('v4-dl-active').innerHTML = '<p class="v4-muted">Koi download nahi chal raha</p>';
  const rowDone = function(d){
    const title = d.title || ''; if(f && title.toLowerCase().indexOf(f) < 0) return '';
    v4DlMap[d.downloadId] = d;
    return v4DlRowHtml(d, v4DlSel.on);
  };
  const doneList = (v4DlData.list || []).filter(function(d){ return !actIds[d.downloadId] && v4DlTypeMatch(d); });
  const statsEl = v4$('v4-dl-stats');
  if(statsEl){
    const comp = doneList.filter(function(d){ return d.status === 'completed'; });
    if(comp.length && !f){
      let tot = 0; comp.forEach(function(d){ tot += (d.file_size || 0); });
      statsEl.style.display = '';
      statsEl.textContent = '📥 ' + comp.length + ' downloads • Kul size: ' + v4MB(tot);
    } else statsEl.style.display = 'none';
  }
  const compList = doneList.filter(function(d){ return d.status === 'completed'; });
  const failList = doneList.filter(function(d){ return d.status !== 'completed'; });
  const rendered = compList.map(rowDone).join('');
  const failRendered = failList.map(rowDone).join('');
  const dfEl = v4$('v4-dl-failed'); if(dfEl) dfEl.innerHTML = failRendered;
  if(rendered) v4$('v4-dl-done').innerHTML = rendered;
  else if(f || v4DlType !== 'all') v4$('v4-dl-done').innerHTML = '<p class="v4-muted">Is filter mein koi download nahi mili</p>';
  else if(act.length) v4$('v4-dl-done').innerHTML = '<p class="v4-muted">Abhi tak koi download mukammal nahi</p>';
  else v4$('v4-dl-done').innerHTML = '<div class="v4-empty"><div class="v4-empty-ic">🎬</div><div class="v4-empty-t">Abhi tak koi download nahi</div><p class="v4-muted">Jo videos aap download karein ge, wo yahan mehfooz milengi — baghair internet ke dekhne ke liye.</p><button class="v4-bigbtn" style="max-width:240px;margin:10px auto 0" data-v="home" onclick="v4Show(this.dataset.v)">Videos dekhein</button></div>';
  v4DlEmptyFix();
  v4FailSectSync();
}
let v4AutoSaveBase = false;
function v4SaveFileName(it){
  let t = String((it && it.title) || 'Video').replace(/[\\/:*?"<>|\\n\\r\\t]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 100);
  const f = String((it && it.format) || '').toUpperCase();
  const ext = f === 'MP3' ? '.mp3' : (f === 'M4A' ? '.m4a' : (f === 'IMAGE' ? '.jpg' : '.mp4'));
  return (t || 'Video') + ext;
}
function v4PhoneSave(it){
  if(!it || !it.downloadId) return false;
  if(window.PlayTubeApp && PlayTubeApp.saveNamed){
    try{ PlayTubeApp.saveNamed(location.origin + '/api/download-file/' + it.downloadId, v4SaveFileName(it)); return true; }catch(e){}
  }
  return false;
}
function v4MenuSavePhone(id){
  const it = (v4DlData.list || []).find(function(x){ return x && x.downloadId === id; }) || {downloadId:id, title:'Video', format:'MP4'};
  if(v4PhoneSave(it)){ v4Toast('📥 Phone mein save ho raha hai: ' + (it.title || 'Video')); return; }
  const a = document.createElement('a');
  a.href = '/api/download-file/' + id; a.setAttribute('download', '');
  document.body.appendChild(a); a.click(); a.remove();
}
function v4AutoSaveOnce(){
  if(!window.PlayTubeApp) return;
  let saved = {};
  try{ saved = JSON.parse(localStorage.getItem('pt_autosaved') || '{}'); }catch(e){}
  const now = Date.now();
  Object.keys(saved).forEach(function(k){ if(now - saved[k] > 30 * 24 * 3600 * 1000) delete saved[k]; });
  (v4DlData.list || []).forEach(function(it){
    if(!it || it.status !== 'completed' || !it.downloadId || it.private) return;
    if(saved[it.downloadId]) return;
    saved[it.downloadId] = now;
    if(!v4AutoSaveBase) return; /* pehli list = purani downloads, inhe auto-save nahi karna */
    if(!v4PhoneSave(it)){
      try{
        const a = document.createElement('a');
        a.href = '/api/download-file/' + it.downloadId; a.setAttribute('download', '');
        document.body.appendChild(a); a.click(); a.remove();
      }catch(e){}
    }
    if(PlayTubeApp.notifyDone){ try{ PlayTubeApp.notifyDone(it.title || 'Video'); }catch(e){} }
    v4Toast('📥 Auto-save: ' + (it.title || 'Video'));
  });
  try{ localStorage.setItem('pt_autosaved', JSON.stringify(saved)); }catch(e){}
  v4AutoSaveBase = true;
}
const _v4RenderDlOrig = v4RenderDownloads;
v4RenderDownloads = function(){ _v4RenderDlOrig(); try{ v4AutoSaveOnce(); }catch(e){} };
async function v4PauseDl(id){ await v4Post('/api/cancel-download/' + id, {}); v4LoadDownloads(); }
async function v4ResumeDl(id){ const r = await v4Post('/api/resume-download/' + id, {}); if(!r.ok) v4Toast((r.data && r.data.error) || 'Resume nahi ho saka'); v4LoadDownloads(); }
async function v4RestartDl(id){ const r = await v4Post('/api/restart-download/' + id, {}); if(r.ok && r.data && r.data.success){ v4Toast('Download dobara start ho gaya'); } else v4Toast((r.data && r.data.error) || 'Restart nahi ho saka'); v4LoadDownloads(); }
function v4RetryDl(id){ const d = v4DlMap[id]; if(!d || !d.videoId){ v4Toast('Is video ki maloomat nahi mili'); return; } const isMusic = ['MP3','M4A'].indexOf((d.format || '').toUpperCase()) >= 0; let q = String(d.quality || ''); if(isMusic){ const m = /(\d{2,3})/.exec(q); q = m ? m[1] : '128'; } else if(!(/^\d+p$/.test(q) || /^3gp$/i.test(q))) q = '360p'; v4Toast('Dobara download shuru ho raha hai...'); v4StartDownload({video_id:d.videoId, format: isMusic ? 'mp3' : 'mp4', quality:q, title:d.title || ''}); }
async function v4DeleteActiveDl(id){ if(!confirm('Ye downloading video delete kar dein? Download ruk jayegi aur aadhi file saaf ho jayegi.')) return; await v4Fetch('/api/delete-download/' + id, {method:'DELETE'}); v4Toast('Download delete ho gaya'); v4LoadDownloads(); }
async function v4DeleteDl(id){ if(!confirm('Ye download delete kar dein?')) return; await v4Fetch('/api/delete-download/' + id, {method:'DELETE'}); v4LoadDownloads(); }
async function v4DeleteAll(){ if(!confirm('Saare downloads delete kar dein?')) return; await v4Fetch('/api/delete-all-downloads', {method:'DELETE'}); v4LoadDownloads(); v4Toast('Saare downloads delete ho gaye'); }
function v4Tick(){
  v4Fetch('/api/download-progress').then(function(r){
    if(!r.ok) return;
    v4DlData.progress = r.data || {}; v4UpdateBadge();
    if(v4State.view === 'downloads'){
      v4Fetch('/api/downloads-list').then(function(l){ if(l.ok && l.data){ v4DlData.list = l.data.downloads || []; v4RenderDownloads(); } });
    }
  });
}

/* ---------- AI assistant ---------- */
function v4AiChip(el){ v4$('v4-ai-input').value = el.textContent.trim(); v4AiSend(null); }
/* ---------- AI suggestions LIVE (Update 40): har dafa naye chips ----------
   User ki apni zyada use ki hui commands + us ki pasand + random naye pool se */
const V4_AI_POOL = ['Motu Patlu episode 1, 3GP download karo', 'Naat sharif MP3 320K me download karo', 'Drama episode 1 to 3, 360p download karo', 'Sab se chhoti quality me gana download karo', 'Coke Studio gana 720p download karo', 'Cartoon episode 5, 360p download karo', 'Islami bayan MP3 me download karo', 'Punjabi gana 320K MP3 download karo', 'Comedy video 360p download karo', 'Qawwali MP3 download karo', 'Hindi gana 720p download karo', 'Kids cartoon episode 1 download karo', 'Tilawat Quran MP3 download karo', 'Funny video sab se chhoti quality me download karo'];
const V4_AI_TIPS = ['Tip: Quality bhi likhein — 3GP, 360p, 720p ya MP3 320K', 'Tip: Episode range bhi chalti hai — "episode 1 to 5"', 'Tip: Waqt bhi de sakte hain — "10 minute baad download karo"', 'Tip: Sirf awaz chahiye to MP3 likh dein', 'Tip: Playlist ka link paste kar dein, saari videos aa jayengi'];
function v4AiCmds(){ try{ return JSON.parse(localStorage.getItem('pt_ai_cmds') || '{}'); }catch(e){ return {}; } }
function v4AiCmdRecord(text){
  const it = v4AiCmds(); const k = ('' + text).trim().slice(0, 80); if(k.length < 4) return;
  it[k] = (it[k] || 0) + 1;
  const keys = Object.keys(it);
  if(keys.length > 20){ keys.sort(function(a, b){ return it[a] - it[b]; }); keys.slice(0, keys.length - 20).forEach(function(x){ delete it[x]; }); }
  try{ localStorage.setItem('pt_ai_cmds', JSON.stringify(it)); }catch(e){}
}
function v4RenderAiChips(){
  const box = v4$('v4-ai-chips'); if(!box) return;
  const picks = [];
  const mine = v4AiCmds();
  Object.keys(mine).sort(function(a, b){ return mine[b] - mine[a]; }).slice(0, 2).forEach(function(cmd){ if(picks.indexOf(cmd) < 0) picks.push(cmd); });
  const top = v4InterestTop(1)[0];
  if(top && picks.length < 3){ const sug = top.charAt(0).toUpperCase() + top.slice(1) + ' ki video 360p download karo'; if(picks.indexOf(sug) < 0) picks.push(sug); }
  const pool = V4_AI_POOL.slice();
  for(let i = pool.length - 1; i > 0; i--){ const j = Math.floor(Math.random() * (i + 1)); const tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp; }
  for(let i = 0; i < pool.length && picks.length < 4; i++){ if(picks.indexOf(pool[i]) < 0) picks.push(pool[i]); }
  box.innerHTML = picks.map(function(cmd){ return '<button class="v4-chip" onclick="v4AiChip(this)">' + v4Esc(cmd) + '</button>'; }).join('');
  const tip = v4$('v4-ai-tip');
  if(tip) tip.textContent = '💡 ' + V4_AI_TIPS[Math.floor(Math.random() * V4_AI_TIPS.length)];
}
function v4AiStore(entry){
  try{ const a = JSON.parse(localStorage.getItem('pt_ai_chat') || '[]'); a.push(entry); while(a.length > 200) a.shift(); localStorage.setItem('pt_ai_chat', JSON.stringify(a)); }catch(e){}
}
function v4AiBubble(text, me, store){
  const d = document.createElement('div');
  d.className = 'v4-bubble ' + (me ? 'me' : 'ai');
  d.textContent = text;
  d.setAttribute('data-ts', String(Date.now()));
  v4$('v4-ai-msgs').appendChild(d);
  window.scrollTo(0, document.body.scrollHeight);
  if(store) v4AiStore({t:Date.now(), kind:(me ? 'me' : 'ai'), text:text});
  return d;
}
function v4AiRestore(){
  const box = v4$('v4-ai-msgs'); if(!box || box.getAttribute('data-restored')) return;
  box.setAttribute('data-restored', '1');
  v4AiPrune();
  let a = [];
  try{ a = JSON.parse(localStorage.getItem('pt_ai_chat') || '[]'); }catch(e){}
  const cut = Date.now() - 24 * 3600 * 1000;
  a.filter(function(en){ return en.t > cut; }).forEach(function(en){
    if(en.kind === 'folder'){
      window._v4Restoring = true;
      const _fkey = en.key || ('cmd:' + (en.title || 'Downloads'));
      const _ff = v4AiFolderGet(_fkey, en.title || 'Downloads');
      window._v4Restoring = false;
      if(_ff && _ff.el) _ff.el.setAttribute('data-ts', String(en.t));
      if(_ff) v4AiFolderRender(_ff.key);
    } else if(en.kind === 'job'){
      const b = v4AiBubble(en.text || '', false);
      b.setAttribute('data-ts', String(en.t)); b.setAttribute('data-jid', en.job_id);
      const holder = document.createElement('div'); holder.id = 'v4-job-' + en.job_id; b.appendChild(holder);
      v4PollJob(en.job_id);
    } else {
      const b = v4AiBubble(en.text || '', en.kind === 'me');
      b.setAttribute('data-ts', String(en.t));
    }
  });
  v4AiFolderRefill();
}
function v4AiPrune(){
  const cut = Date.now() - 24 * 3600 * 1000;
  try{ const a = JSON.parse(localStorage.getItem('pt_ai_chat') || '[]'); const b = a.filter(function(en){ return en.t > cut; }); if(b.length !== a.length) localStorage.setItem('pt_ai_chat', JSON.stringify(b)); }catch(e){}
  document.querySelectorAll('#v4-ai-msgs .v4-bubble').forEach(function(el){ const ts = Number(el.getAttribute('data-ts') || '0'); if(ts && ts < cut) el.remove(); });
}
function v4AiQuickSend(text){ const inp = v4$('v4-ai-input'); if(inp) inp.value = text; v4AiSend(null); }
async function v4AiSend(e, _sendText, _dispText){
  if(e) e.preventDefault();
  const inp = v4$('v4-ai-input'); const text = ((_sendText != null ? _sendText : inp.value) || '').trim(); if(!text) return;
  inp.value = '';
  v4AiCmdRecord(text);
  window._v4LastAiCmd = text; window._v4AttachCtx = null;
  v4AiBubble(_dispText || text, true, true);
  const r = await v4Post('/api/ai/command', {command:text, phone_mode: v4PhoneAiOk()});
  const d = r.data || {};
  if(!r.ok){ if(d.login_required){ v4Pending = {type:'ai', text:text}; v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); return; } v4AiBubble(d.error || 'Command nahi chali — dobara try karein'); return; }
  if(d.intent === 'search'){
    const b = v4AiBubble(d.message || 'Results mil gaye:');
    (d.results || []).forEach(function(it){
      const v = {videoId:it.video_id, title:it.title || '', channel:''}; v4Videos[v.videoId] = v;
      const row = document.createElement('div'); row.className = 'v4-ep';
      const nm = document.createElement('span'); nm.style.flex = '1'; nm.textContent = v.title; row.appendChild(nm);
      const btn = document.createElement('button'); btn.className = 'v4-btn2'; btn.textContent = 'Download';
      btn.onclick = function(ev){ v4DlClick(ev, v.videoId); };
      row.appendChild(btn); b.appendChild(row);
    });
    return;
  }
  if(d.intent === 'candidates'){
    const b = v4AiBubble(d.message || 'Results mil gaye — jin par select karein, wahi download hongi:');
    const ctx = v4RenderCandidates(b, d.candidates || [], {quality:(d.parsed && d.parsed.quality) || '360p', format:(d.parsed && d.parsed.format) || 'mp4', qexp: !!d.qexp, show: d.show || '', category: (d.parsed && d.parsed.category) || '', kind: d.kind || '', src: d.src || ''});
    window._v4CandCtx = ctx;
    v4AiCandTrack(b, ctx);
    setTimeout(function(){ window.scrollTo(0, document.body.scrollHeight); }, 60);
    return;
  }
  if(d.intent === 'phone_job'){
    v4PhoneJobStart(d.items || [], (d.parsed && d.parsed.quality) || '360p', (d.parsed && d.parsed.format) || 'mp4', d.message, '');
    return;
  }
  if(d.url){
    const b = v4AiBubble(d.message || 'Tayyar hai');
    b.appendChild(document.createElement('br'));
    const a = document.createElement('a'); a.href = d.url; a.className = 'v4-btn2'; a.textContent = 'Download karein'; a.style.marginTop = '8px'; b.appendChild(a);
    return;
  }
  const b = v4AiBubble(d.message || 'Job shuru ho gaya');
  if(d.options && d.options.length){
    const orow = document.createElement('div');
    orow.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px';
    d.options.forEach(function(op){
      const ob = document.createElement('button');
      ob.className = 'v4-btn2'; ob.textContent = op;
      ob.onclick = function(){ v4AiQuickSend(op); };
      orow.appendChild(ob);
    });
    b.appendChild(orow);
  }
  if(d.job_id){ v4AiAttachJob(d.job_id); }
}
/* Update 109: candidates renderer — scroll-box (5 jitni rows dikhti
   hain), pic tap = USI bubble ke upar inline player (ek waqt me ek),
   har row mein channel • duration • views • time + ↗ Isi jaisi aur.
   Har bubble ka apna context — tap par global ctx usi ka ho jata hai. */
function v4CandPlay(ctx, vid){
  if(!ctx || !ctx.playerBox) return;
  const box = ctx.playerBox;
  box.innerHTML = '';
  const wrap = document.createElement('div'); wrap.className = 'v4-cand-player';
  const fr = document.createElement('iframe');
  fr.src = 'https://www.youtube.com/embed/' + vid + '?autoplay=1&rel=0';
  fr.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture');
  fr.setAttribute('allowfullscreen', '');
  wrap.appendChild(fr);
  const band = document.createElement('button'); band.className = 'v4-btn2 v4-pband'; band.textContent = '✕ Band';
  band.onclick = function(ev){ ev.stopPropagation(); box.innerHTML = ''; };
  wrap.appendChild(band);
  box.appendChild(wrap);
}
function v4AiCandTrack(b, ctx){
  /* Update 120: list card bhi singleton jaisa — nayi list ane par
     purani UNUSED list (jis se download start nahi hua) replace ho
     jati hai; istemal shuda list history mein rehti hai. */
  const prev = window._v4CandBubble;
  if(prev && prev.el && prev.el !== b && prev.el.parentNode && !(prev.ctx && prev.ctx._started)) prev.el.remove();
  window._v4CandBubble = {el: b, ctx: ctx};
}
function v4RenderCandidates(b, candidates, opts){
  opts = opts || {};
  const ctx = {quality: opts.quality || '360p', format: opts.format || 'mp4', qexp: !!opts.qexp, show: opts.show || '', category: opts.category || '', kind: opts.kind || '', src: opts.src || '', items: candidates || [], sel: {}};
  const player = document.createElement('div'); b.appendChild(player); ctx.playerBox = player;
  const box = document.createElement('div'); box.className = 'v4-cand-box'; b.appendChild(box);
  (candidates || []).forEach(function(c, ix){
    const v = {videoId:c.video_id, title:c.title || '', channel:c.channel || ''}; v4Videos[v.videoId] = v;
    const row = document.createElement('div'); row.className = 'v4-ep'; row.style.cssText = 'align-items:center;gap:8px;cursor:pointer';
    const chk = document.createElement('span'); chk.className = 'v4-candchk'; chk.textContent = '☐'; chk.style.cssText = 'font-size:19px;flex:none;width:22px;text-align:center'; row.appendChild(chk);
    const im = document.createElement('img'); im.src = 'https://i.ytimg.com/vi/' + c.video_id + '/mqdefault.jpg'; im.alt = '▶'; im.style.cssText = 'width:86px;height:48px;object-fit:cover;border-radius:8px;flex:none';
    im.setAttribute('data-vid', c.video_id);
    im.onclick = function(ev){ ev.stopPropagation(); v4CandPlay(ctx, this.getAttribute('data-vid')); };
    row.appendChild(im);
    const tx = document.createElement('div'); tx.style.flex = '1';
    const t1 = document.createElement('div'); t1.textContent = c.title || ''; t1.style.cssText = 'font-size:13px;font-weight:600;line-height:1.3'; tx.appendChild(t1);
    const meta = [c.channel || '', c.duration ? v4Dur(c.duration) : '', c.view_count ? v4FmtCount(c.view_count) + ' views' : '', c.age || ''].filter(Boolean).join(' • ');
    const t2 = document.createElement('div'); t2.textContent = meta; t2.style.cssText = 'font-size:11px;opacity:.75;margin-top:2px'; tx.appendChild(t2);
    row.appendChild(tx);
    const sim = document.createElement('button'); sim.className = 'v4-btn2'; sim.textContent = '↗ Isi jaisi aur'; sim.style.cssText = 'font-size:10.5px;padding:4px 7px;flex:none';
    sim.onclick = function(ev){ ev.stopPropagation(); v4AiSimilar(c); };
    row.appendChild(sim);
    row.setAttribute('data-ix', ix);
    row.onclick = function(){ window._v4CandCtx = ctx; v4CandToggle(this); };
    box.appendChild(row);
  });
  const go = document.createElement('button'); go.className = 'v4-bigbtn'; go.textContent = '⬇ Download karein (0 select)'; go.disabled = true; go.style.marginTop = '10px'; go.style.opacity = '.55';
  go.onclick = function(){ window._v4CandCtx = ctx; v4CandGo(this); };
  ctx.goBtn = go;
  b.appendChild(go);
  const hint = document.createElement('div'); hint.className = 'v4-muted'; hint.style.marginTop = '6px'; hint.textContent = 'Video par tap = select • pic par tap = wahin play • ↗ = isi jaisi aur videos';
  b.appendChild(hint);
  b._candCtx = ctx;
  return ctx;
}
async function v4AiSimilar(c){
  const b = v4AiBubble('↗ "' + (c.title || 'video') + '" jaisi aur videos dhoondh raha hoon...');
  const r = await v4Post('/api/ai/command', {similar:{id:c.video_id, channel:c.channel || '', title:c.title || ''}});
  const d = r.data || {};
  if(!r.ok || !d.candidates || !d.candidates.length){ b.textContent = '😔 Is jaisi aur videos nahi mil sakein.'; return; }
  b.textContent = '↗ "' + (c.title || '') + '" jaisi aur videos — select karke download karein:';
  const ctx = v4RenderCandidates(b, d.candidates, {quality:'360p', format:'mp4', qexp:false, show:'', category:'', src:'↗ Isi jaisi aur'});
  window._v4CandCtx = ctx;
  v4AiCandTrack(b, ctx);
}
/* Update 105: candidates multi-select — tap = select, sirf select
   ki hui hi download hongi (3-5 ya jitni chaahein) */
function v4CandToggle(el){
  const ctx = window._v4CandCtx || {}; const ix = el.getAttribute('data-ix');
  const chk = el.querySelector('.v4-candchk');
  if(ctx.sel && ctx.sel[ix]){ delete ctx.sel[ix]; if(chk) chk.textContent = '☐'; el.style.background = ''; }
  else { if(!ctx.sel) ctx.sel = {}; ctx.sel[ix] = 1; if(chk) chk.textContent = '☑'; el.style.background = 'rgba(124,92,255,.20)'; }
  const n = Object.keys(ctx.sel || {}).length;
  if(ctx.goBtn){ ctx.goBtn.disabled = !n; ctx.goBtn.style.opacity = n ? '1' : '.55'; ctx.goBtn.textContent = '⬇ Download karein (' + n + ' select)'; }
}
function v4CandGo(el){
  const ctx = window._v4CandCtx || {};
  const items = Object.keys(ctx.sel || {}).map(function(ix){ const c = (ctx.items || [])[+ix]; return c ? {video_id:c.video_id, title:c.title} : null; }).filter(Boolean);
  if(!items.length) return;
  ctx.selItems = items;
  if(ctx.format === 'mp3'){ v4CandStart('192', 'mp3'); return; }
  if(ctx.qexp){ v4CandStart(ctx.quality || '360p', 'mp4'); return; }
  /* Update 120: quality card EK hi banti hai — dobara puche to
     purani card replace hokar chat ke aakhir (neeche) aa jati hai,
     duplicate bubbles nahi bante. '✔ select ho gayin' wali alag
     bubble bhi khatam — wohi baat card ke andar hai. */
  const _sig = items.map(function(x){ return x.video_id; }).join(',');
  const _oldQ = document.getElementById('v4-ai-quality');
  if(_oldQ && _oldQ.getAttribute('data-sig') === _sig){ v4$('v4-ai-msgs').appendChild(_oldQ); window.scrollTo(0, document.body.scrollHeight); return; }
  if(_oldQ) _oldQ.remove();
  const b = v4AiBubble('✔ ' + items.length + ' videos select ho gayin — Kis quality mein download karun?');
  b.id = 'v4-ai-quality'; b.setAttribute('data-sig', _sig);
  const row = document.createElement('div'); row.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px';
  const _qopts109 = ctx.kind === 'songs' ? [['MP3','mp3'],['360p','mp4'],['720p','mp4'],['1080p','mp4']] : [['360p','mp4'],['720p','mp4'],['1080p','mp4'],['MP3','mp3']];
  _qopts109.forEach(function(qo){
    const ob = document.createElement('button'); ob.className = 'v4-btn2'; ob.textContent = qo[0];
    ob.setAttribute('data-q', qo[0]); ob.setAttribute('data-f', qo[1]);
    ob.onclick = function(){ window._v4CandCtx = ctx; const f = this.getAttribute('data-f'); v4CandStart(f === 'mp3' ? '192' : this.getAttribute('data-q'), f); };
    row.appendChild(ob);
  });
  b.appendChild(row);
}
async function v4CandStart(quality, format){
  const ctx = window._v4CandCtx || {};
  ctx._started = true;
  const _qc = document.getElementById('v4-ai-quality'); if(_qc) _qc.remove();
  window._v4AttachCtx = ctx;
  const items = ctx.selItems || [];
  if(!items.length) return;
  if(v4PhoneAiOk()){
    v4PhoneJobStart(items, quality, format, '📱 ' + items.length + ' videos phone par download ho rahi hain — one by one:', ctx.show || '', {key:v4AiFolderKeyFor(ctx), title:v4AiFolderTitleFor(ctx)});
    return;
  }
  const submit = async function(){
    const r = await v4Post('/api/ai/pick-many', {items:items, quality:quality, format:format, show:ctx.show || ''});
    const d = r.data || {};
    if(!r.ok){ if(d.login_required){ v4Pending = {type:'ai'}; v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); v4AiBubble('Limit khatam — pehle account banayein.'); return; } v4AiBubble(d.error || 'Download start nahi ho saka'); return; }
    const b = v4AiBubble(d.message || 'Download start ho gayi');
    if(d.job_id){ v4AiAttachJob(d.job_id); }
  };
  v4SrvEnqueue(items, submit);
}
async function v4AiDoPick(vid, title, quality, format){
  const ctx = window._v4CandCtx || {};
  if(!ctx.show && window._v4AttachCtx && window._v4AttachCtx.show) ctx.show = window._v4AttachCtx.show;
  window._v4AttachCtx = ctx;
  if(v4PhoneAiOk()){
    v4PhoneJobStart([{video_id:vid, title:title}], quality, format, '✅ Yahi phone par download ho rahi hai: ' + title, ctx.show || '', {key:v4AiFolderKeyFor(ctx), title:v4AiFolderTitleFor(ctx)});
    return;
  }
  const submit = async function(){
    const r = await v4Post('/api/ai/pick', {video_id:vid, title:title, quality:quality, format:format, show:ctx.show || '', category:ctx.category || ''});
    const d = r.data || {};
    if(!r.ok){ if(d.login_required){ v4Pending = {type:'ai'}; v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); v4AiBubble('Limit khatam — pehle account banayein.'); return; } v4AiBubble(d.error || 'Download start nahi ho saka'); return; }
    const b = v4AiBubble(d.message || 'Download start ho gayi');
    if(d.job_id){ v4AiAttachJob(d.job_id); }
  };
  v4SrvEnqueue([{video_id:vid, title:title}], submit);
}
async function v4AiEpisodes(el){
  const show = el.getAttribute('data-show'); el.disabled = true;
  const b = v4AiBubble('📂 "' + show + '" ki episodes dhoondh raha hoon...');
  const r = await v4Post('/api/ai/episodes', {show:show});
  const d = r.data || {};
  if(!r.ok || !d.episodes || !d.episodes.length){ b.textContent = '😔 "' + show + '" ki episodes nahi mil sakein — naam check karke dobara try karein.'; return; }
  window._v4EpItems = d.episodes;
  b._epItems = d.episodes; b._epShow = show; b._baqi = false;
  b.textContent = '📂 "' + show + '" — ' + d.episodes.length + ' episodes mil gayi. Jo chahiye us par tap karein, ya sab ek sath download karein:';
  const all = document.createElement('button'); all.className = 'v4-btn2'; all.textContent = '⬇ Sab episodes download karein'; all.style.margin = '8px 0';
  all.onclick = function(){ v4AiPickAll(this); };
  b.appendChild(document.createElement('br')); b.appendChild(all);
  const tg = document.createElement('button'); tg.className = 'v4-btn2'; tg.textContent = '🎯 Sirf baqi: OFF'; tg.style.margin = '8px 0 8px 6px';
  tg.onclick = function(){ b._baqi = !b._baqi; this.textContent = '🎯 Sirf baqi: ' + (b._baqi ? 'ON' : 'OFF'); v4RenderEpRows(b); };
  b.appendChild(tg);
  const box = document.createElement('div'); box.className = 'v4-cand-box'; b.appendChild(box); b._epBox = box;
  v4RenderEpRows(b);
  v4EnsureDlCache(function(){ if(b._baqi) v4RenderEpRows(b); });
}
function v4RenderEpRows(b){
  const box = b._epBox; if(!box) return;
  const got = b._baqi ? v4DownloadedEps(b._epShow || '') : {};
  box.innerHTML = '';
  let shown = 0;
  (b._epItems || []).forEach(function(ep){
    if(b._baqi && got[ep.episode]) return;
    shown++;
    const row = document.createElement('div'); row.className = 'v4-ep'; row.style.cssText = 'align-items:center;gap:8px;cursor:pointer';
    const nm = document.createElement('span'); nm.style.flex = '1'; nm.style.fontSize = '13px'; nm.textContent = 'Episode ' + ep.episode + ' — ' + (ep.title || ''); row.appendChild(nm);
    const dl = document.createElement('span'); dl.textContent = '⬇'; row.appendChild(dl);
    row.setAttribute('data-vid', ep.video_id); row.setAttribute('data-title', ep.title || '');
    row.onclick = function(){ const c2 = window._v4CandCtx || {}; window._v4AttachCtx = {show: b._epShow || ''}; v4AiBubble('✔ Episode ' + ep.episode, true, true); v4AiDoPick(this.getAttribute('data-vid'), this.getAttribute('data-title'), c2.qexp ? (c2.quality || '360p') : '360p', 'mp4'); };
    box.appendChild(row);
  });
  if(!shown){ const p = document.createElement('div'); p.className = 'v4-muted'; p.style.padding = '8px 2px'; p.textContent = '✓ Saari episodes pehle hi download ho chuki hain — baqi koi nahi.'; box.appendChild(p); }
}
/* Update 109: download ho chuki episodes ka set — phone (pt_phone_dl)
   + server downloads (cache/list) se, show ke naam + episode number par */
function v4DownloadedEps(show){
  const set = {};
  const sl = (show || '').toLowerCase();
  const first = sl.split(/[^a-z0-9]+/).filter(function(w){ return w.length >= 3; })[0] || sl;
  function scan(title){
    if(!title) return;
    const t = String(title).toLowerCase();
    if(sl && t.indexOf(sl) < 0 && (!first || t.indexOf(first) < 0)) return;
    let m = /episode\s*#?\s*(\d+)/.exec(t);
    if(!m){ const mm = /(^|[^a-z])ep\s*#?\s*(\d+)/.exec(t); if(mm) m = [mm[0], mm[2]]; }
    if(m) set[+m[1]] = 1;
  }
  try{ (JSON.parse(localStorage.getItem('pt_phone_dl') || '[]')).forEach(function(s){ scan(s.title); }); }catch(e){}
  (window._v4DlCache || []).forEach(function(x){ if(x.status === 'completed' || !x.status) scan(x.title); });
  (v4DlData.list || []).forEach(function(x){ if(x.status === 'completed') scan(x.title); });
  return set;
}
function v4EnsureDlCache(cb){
  if(window._v4DlCache){ if(cb) cb(); return; }
  v4Fetch('/api/downloads-list').then(function(r){
    window._v4DlCache = (r.ok && r.data && r.data.downloads) || [];
    if(cb) cb();
  }).catch(function(){ window._v4DlCache = []; if(cb) cb(); });
}
async function v4AiPickAll(el){
  el.disabled = true;
  const _epshow = (el.parentNode && el.parentNode._epShow) || '';
  const items = (window._v4EpItems || []).map(function(ep){ return {video_id:ep.video_id, title:ep.title}; });
  if(!items.length) return;
  if(v4PhoneAiOk()){
    const cx = window._v4CandCtx || {};
    v4PhoneJobStart(items, cx.qexp ? (cx.quality || '360p') : '360p', 'mp4', '📱 ' + items.length + ' episodes phone par download ho rahi hain — one by one:', _epshow, {key: _epshow ? ('show:' + _epshow.toLowerCase()) : v4AiFolderKeyFor(cx), title: _epshow ? ('📂 ' + _epshow) : v4AiFolderTitleFor(cx)});
    return;
  }
  const ctx = window._v4CandCtx || {};
  window._v4AttachCtx = _epshow ? {show:_epshow} : ctx;
  const submit = async function(){
    const r = await v4Post('/api/ai/pick-many', {items:items, quality: ctx.qexp ? (ctx.quality || '360p') : '360p', format:'mp4', show: _epshow || ctx.show || ''});
    const d = r.data || {};
    if(!r.ok){ if(d.login_required){ v4Pending = {type:'ai'}; v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); } v4AiBubble(d.error || 'Download start nahi ho saka'); return; }
    const b = v4AiBubble(d.message || 'Sab episodes download start');
    if(d.job_id){ v4AiAttachJob(d.job_id); }
  };
  v4SrvEnqueue(items, submit);
}

/* Update 103: AI jobs APK mein PHONE par — server bot-check se mehfooz */
function v4PhoneAiOk(){ try{ return !!(window.PlayTubeApp && PlayTubeApp.phoneDlStart); }catch(e){ return false; } }
/* Update 122 (user policy 2026-11-27): APK ki download limit bhi
   WOHI jo website ki hai — bina account, admin ki set ki hui ginati
   (default 10). Play unlimited hai; ginati sirf download par hai,
   aur sirf mukammal (done) downloads par lagti hai. */
function v4GuestPhoneUsed(){
  let local = 0;
  try{ local = parseInt(localStorage.getItem('pt_guest_phone_dl') || '0', 10) || 0; }catch(e){}
  const srv = (v4State.config && v4State.config.guest_used) || 0;
  return local + (srv || 0);
}
function v4GuestGate(){
  if(v4State.user) return true;
  const lim = (v4State.config && v4State.config.guest_limit != null) ? v4State.config.guest_limit : 10;
  if(lim <= 0) return false;
  return v4GuestPhoneUsed() < lim;
}
function v4GuestPhoneDone(vid){
  if(v4State.user || !vid) return;
  try{
    const counted = JSON.parse(localStorage.getItem('pt_guest_counted') || '[]');
    if(counted.indexOf(vid) >= 0) return;
    counted.push(vid);
    localStorage.setItem('pt_guest_counted', JSON.stringify(counted.slice(-200)));
    const n = (parseInt(localStorage.getItem('pt_guest_phone_dl') || '0', 10) || 0) + 1;
    localStorage.setItem('pt_guest_phone_dl', String(n));
  }catch(e){}
}
let v4PhoneJobSeq = 0;
function v4PhoneJobStart(items, quality, format, msg, show, opts){
  if(!items || !items.length) return;
  if(!v4GuestGate()){ v4Pending = {type:'ai'}; v4OpenAuth('signin', false, 'limit'); v4AiBubble('Limit khatam — pehle account banayein.'); return; }
  const job = {id: ++v4PhoneJobSeq, items: items, quality: quality || '360p', format: format || 'mp4', idx: 0, userStopped: false, done: 0, failed: 0};
  job.key = 'pj' + job.id; (window._v4PhoneJobs = window._v4PhoneJobs || {})[job.key] = job;
  /* Update 114 (corrected): phone job apne naye bubble mein nahi —
     apne kaam/show ke FOLDER mein add hota hai. */
  const _kf = (opts && opts.key) ? {key: opts.key, title: opts.title || '📥 Downloads'} : v4AiFolderKeyOf({show: show}, items);
  const _fk = _kf.key, _ft = _kf.title;
  const _F = v4AiFolderGet(_fk, _ft);
  job.folderKey = _F.key; job.folderTitle = _F.title;
  _F.phoneJobs[job.key] = job;
  v4AiFolderRender(_fk);
  window.scrollTo(0, document.body.scrollHeight);
  v4PhoneJobNext(job);
}
function v4PhoneJobDeleteAll(job){
  job.userStopped = true;
  if(job._timer) clearInterval(job._timer);
  (job.items || []).forEach(function(it){ if(it._timer){ clearInterval(it._timer); it._timer = null; } if(it._st === 'starting' || it._st === 'downloading') it._st = 'deleted'; });
  const vids = {};
  (job.items || []).forEach(function(it){ if(it.video_id) vids[it.video_id] = 1; });
  try{
    if(window.PlayTubeApp && PlayTubeApp.phoneDlState && PlayTubeApp.phoneDlRemove){
      const live = JSON.parse(PlayTubeApp.phoneDlState() || '[]');
      live.forEach(function(p){ if(vids[p.videoId]){ try{ PlayTubeApp.phoneDlRemove(p.id); }catch(e){} } });
    }
  }catch(e){}
  try{
    let stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]');
    stored = stored.filter(function(s){ return !vids[s.videoId]; });
    localStorage.setItem('pt_phone_dl', JSON.stringify(stored));
  }catch(e){}
  if(job.stopBtn) job.stopBtn.style.display = 'none';
  if(job.delBtn) job.delBtn.style.display = 'none';
  if(job.holder) job.holder.innerHTML = '<div style="font-size:13px">🗑 Poori list delete ho gayi — phone se files bhi hata di gayin.</div>';
  window._v4phSig = '';
  try{ v4PhoneDlRender(); }catch(e){}
  v4Toast('Poori list delete ho gayi');
}
function v4PhoneJobRender(job){
  if(job.folderKey){ v4AiFolderRender(job.folderKey); return; }
  if(!job.holder) return;
  const total = job.items.length;
  const head = '<div class="v4-ailist-h"><span class="t">📥 ' + total + ' videos</span><span class="cnt">' + job.done + ' / ' + total + '</span></div>';
  const rows = job.items.map(function(it, i){
    let st = '⏳', pct = '';
    if(it._st === 'done') st = '✓';
    else if(it._st === 'deleted') st = '🗑';
    else if(it._st === 'failed') st = '✗';
    else if(i === job.idx && !job.userStopped){ st = '⬇'; if(it._pct != null) pct = ' ' + it._pct + '%'; }
    if(job.userStopped && !it._st) st = '⏹';
    let btn = '';
    if(it._st === 'done') btn = '<span class="v4-ai-stop" data-job="' + job.key + '" data-idx="' + i + '" onclick="event.stopPropagation();v4PhoneJobDelItem(this)" title="Delete">🗑</span>';
    else if(it._st !== 'deleted') btn = '<span class="v4-ai-stop" data-job="' + job.key + '" data-idx="' + i + '" onclick="event.stopPropagation();v4PhoneJobDelItem(this)" title="Band + delete">✕</span>';
    return '<div class="v4-ep"><span style="flex:1;font-size:13px">' + st + ' ' + v4Esc(it.title || '') + pct + '</span>' + btn + '</div>';
  }).join('');
  job.holder.innerHTML = head + '<div class="v4-cand-box v4-job-box">' + rows + '</div>' + '<div style="font-size:12px;opacity:.8;margin-top:4px">' + job.done + ' / ' + total + ' ho gayi' + (job.failed ? ' • ' + job.failed + ' fail' : '') + ' — Downloads page mein live progress bhi chal raha hai</div>';
}
/* Update 109: phone job ki ek row ka ✕ = band + DELETE (galti se lagi
   download ek tap mein saaf). Chalti hui ho to cancel + partial remove
   karke runner aage barhta hai; line wali sirf skip ho jati hai. */
function v4PhoneJobDelItem(el){
  const job = (window._v4PhoneJobs || {})[el.getAttribute('data-job')];
  if(!job) return;
  const idx = Number(el.getAttribute('data-idx'));
  const it = job.items[idx]; if(!it || it._st === 'deleted') return;
  if(it._st === 'done'){
    try{
      if(window.PlayTubeApp && PlayTubeApp.phoneDlState && PlayTubeApp.phoneDlRemove){
        const live = JSON.parse(PlayTubeApp.phoneDlState() || '[]');
        live.forEach(function(p){ if(p.videoId === it.video_id){ try{ PlayTubeApp.phoneDlRemove(p.id); }catch(e){} } });
      }
      let stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]');
      stored = stored.filter(function(s){ return s.videoId !== it.video_id; });
      localStorage.setItem('pt_phone_dl', JSON.stringify(stored));
    }catch(e){}
    it._st = 'deleted'; if(job.done > 0) job.done--;
    window._v4phSig = '';
    try{ v4PhoneDlRender(); }catch(e){}
    v4PhoneJobRender(job);
    return;
  }
  if(it._st === 'starting' || it._st === 'downloading'){
    try{
      let live = [];
      try{ live = JSON.parse(PlayTubeApp.phoneDlState() || '[]'); }catch(e){}
      const ent = (it._entId && live.filter(function(x){ return x.id === it._entId; })[0]) || live.filter(function(x){ return x.videoId === it.video_id && !(it._preIds && it._preIds[x.id]); })[0] || live.filter(function(x){ return x.videoId === it.video_id; })[0];
      if(ent){
        if(PlayTubeApp.phoneDlCancel && ent.status === 'running'){ try{ PlayTubeApp.phoneDlCancel(ent.id); }catch(e){} }
        if(PlayTubeApp.phoneDlRemove){ try{ PlayTubeApp.phoneDlRemove(ent.id); }catch(e){} }
      }
    }catch(e){}
    if(it._timer){ clearInterval(it._timer); it._timer = null; }
    it._st = 'deleted';
    v4PhoneJobRender(job);
    v4FolderSched();
    return;
  }
  it._st = 'deleted';
  v4PhoneJobRender(job);
}
/* Update 118: PHONE runner — folder-level scheduler. Ek waqt mein
   utni hi downloads jitni Settings ki 'Ek sath downloads' limit
   (v4State.settings.maxConc, default 3) — phone + server mila kar.
   Har item SIRF apni fresh entry se bandhta hai (snapshot + claim);
   purani 'stopped' entry kabhi nahi bandhti, aur 'stopped' sirf
   user ke stop se banta hai (item._st = 'ustop'). */
function v4DlLimit(){
  const n = parseInt((v4State.settings && v4State.settings.maxConc) || 3, 10);
  return (n >= 1 && n <= 5) ? n : 3;
}
function v4PhoneActiveCount(){
  let n = 0;
  const F = (window._v4Folders || {})[V4_FOLDER_KEY]; if(!F) return 0;
  Object.keys(F.phoneJobs || {}).forEach(function(jk){
    (F.phoneJobs[jk].items || []).forEach(function(it){ if(it._st === 'starting' || it._st === 'downloading') n++; });
  });
  return n;
}
function v4SrvActiveCount(){
  let n = 0;
  const F = (window._v4Folders || {})[V4_FOLDER_KEY]; if(!F) return 0;
  Object.keys(F.serverJobs || {}).forEach(function(jid){
    const job = F.serverData[jid];
    if(!job){ n += 1; return; }
    (job.episodes_status || []).forEach(function(es){ if(es.status === 'downloading' || es.status === 'searching') n++; });
  });
  return n;
}
function v4PhoneSched(){
  const F = (window._v4Folders || {})[V4_FOLDER_KEY]; if(!F) return;
  let active = v4PhoneActiveCount() + v4SrvActiveCount();
  const lim = v4DlLimit();
  const jobs = Object.keys(F.phoneJobs || {}).map(function(jk){ return F.phoneJobs[jk]; }).sort(function(a, b){ return a.id - b.id; });
  for(let ji = 0; ji < jobs.length; ji++){
    const job = jobs[ji];
    if(job.userStopped) continue;
    for(let ii = 0; ii < job.items.length; ii++){
      if(active >= lim) return;
      const it = job.items[ii];
      if(!it._st && !it._hold){ v4PhoneItemStart(job, it); if(it._st === 'starting' || it._st === 'downloading') active++; }
    }
  }
}
function v4PhoneItemStart(job, it){
  it._err = ''; it._entId = null; it._wait = 0; it._gone = 0;
  it._preIds = {};
  try{ JSON.parse(PlayTubeApp.phoneDlState() || '[]').forEach(function(x){ if(x.videoId === it.video_id) it._preIds[x.id] = 1; }); }catch(e){}
  it._st = 'starting';
  try{ PlayTubeApp.phoneDlStart(it.video_id, job.quality, job.format, it.title || ''); }
  catch(e){ it._st = 'failed'; it._err = 'Download start nahi hua — ↻ se dobara try karein'; job.failed++; v4PhoneJobRender(job); return; }
  if(it._timer) clearInterval(it._timer);
  it._timer = setInterval(function(){ v4PhoneItemPoll(job, it); }, 1500);
}
function v4PhoneItemPoll(job, it){
  if(it._st !== 'starting' && it._st !== 'downloading'){ if(it._timer) clearInterval(it._timer); return; }
  let live = null;
  try{ live = JSON.parse(PlayTubeApp.phoneDlState() || '[]'); }catch(e){ live = null; }
  if(!live) return;
  let ent = null;
  if(it._entId){
    ent = live.filter(function(x){ return x.id === it._entId; })[0] || null;
    if(!ent){
      /* Bandhi hui entry list se gayab (app restart / remove) —
         stopped NAHI, fail + wajah + retry. */
      it._gone = (it._gone || 0) + 1;
      if(it._gone >= 5) v4PhoneItemFinish(job, it, 'failed', 'Download list se gayab ho gaya — ↻ se dobara try karein');
      return;
    }
  } else {
    const claims = (window._v4EntClaim = window._v4EntClaim || {});
    const cand = live.filter(function(x){ return x.videoId === it.video_id && !(it._preIds && it._preIds[x.id]) && (!claims[x.id] || claims[x.id] === job.key); });
    /* List nayi-pehle tartib mein hai; hamari entry is start ki SAB
       SE PURANI unclaimed hai (FIFO) — dusre job ki nayi entry
       galti se nahi bandhti. */
    ent = cand.length ? cand[cand.length - 1] : null;
    if(ent){ it._entId = ent.id; claims[ent.id] = job.key; it._st = 'downloading'; }
    else {
      it._wait = (it._wait || 0) + 1;
      if(it._wait > 40) v4PhoneItemFinish(job, it, 'failed', 'Download start nahi hua — ↻ se dobara try karein');
      return;
    }
  }
  if(ent.status === 'done'){ v4ShowTrackTitle(it.title || ''); it._pct = 100; v4PhoneItemFinish(job, it, 'done', ''); return; }
  if(ent.status === 'failed'){ v4PhoneItemFinish(job, it, 'failed', ent.error || 'Download fail ho gaya — ↻ se dobara try karein'); return; }
  if(ent.status === 'stopped'){
    if(it._wantStop){ it._wantStop = false; it._hold = true; v4PhoneItemFinish(job, it, 'ustop', ''); return; }
    /* Apni entry par baghair user-stop ke 'stopped' — ye fail hai;
       'stopped' kabhi khud nahi banta. */
    v4PhoneItemFinish(job, it, 'failed', 'Download ruk gaya — ↻ se dobara try karein'); return;
  }
  it._pct = ent.percent; v4PhoneJobRender(job);
}
function v4PhoneItemFinish(job, it, st, err){
  if(it._timer){ clearInterval(it._timer); it._timer = null; }
  it._st = st; if(err) it._err = err;
  if(st === 'done'){ job.done++; v4GuestPhoneDone(it.video_id || ''); } else if(st === 'failed') job.failed++;
  v4PhoneJobRender(job);
  v4FolderSched();
}
function v4PhoneJobNext(job){ v4PhoneSched(); }
/* Server picks ki line: limit bhar jaye to pick-many/pick ki
   submission ruk jati hai (items folder mein 'line mein' dikhte
   hain); slot khali hote hi khud submit ho jati hai. */
function v4SrvEnqueue(items, submitFn){
  const F = v4AiFolderGet(V4_FOLDER_KEY, '📥 Downloads');
  if(!F.pendingSrv) F.pendingSrv = [];
  (items || []).forEach(function(it){ F.pendingSrv.push({title: it.title || '', video_id: it.video_id || ''}); });
  (window._v4SrvQueue = window._v4SrvQueue || []).push({items: items, fn: submitFn});
  v4AiFolderRender(F.key);
  v4FolderSched();
  v4SrvTimerStart();
}
function v4SrvTimerStart(){
  if(window._v4SrvTimer) return;
  window._v4SrvTimer = setInterval(function(){
    if(!(window._v4SrvQueue || []).length){ clearInterval(window._v4SrvTimer); window._v4SrvTimer = null; return; }
    v4FolderSched();
  }, 2500);
}
function v4SrvPendDel(el){
  const F = (window._v4Folders || {})[V4_FOLDER_KEY]; if(!F || !F.pendingSrv) return;
  const ix = Number(el.getAttribute('data-idx'));
  const p = F.pendingSrv[ix]; if(!p) return;
  F.pendingSrv.splice(ix, 1);
  (window._v4SrvQueue || []).forEach(function(q){
    for(let i = 0; i < q.items.length; i++){ if(q.items[i].video_id === p.video_id){ q.items.splice(i, 1); break; } }
  });
  window._v4SrvQueue = (window._v4SrvQueue || []).filter(function(q){ return q.items.length; });
  v4AiFolderRender(F.key);
}
function v4FolderSched(){
  v4PhoneSched();
  const q = window._v4SrvQueue || [];
  if(!q.length) return;
  const F = (window._v4Folders || {})[V4_FOLDER_KEY]; if(!F) return;
  let active = v4PhoneActiveCount() + v4SrvActiveCount();
  while(q.length && active < v4DlLimit()){
    const job = q.shift();
    if(F.pendingSrv){
      job.items.forEach(function(sit){
        for(let i = 0; i < F.pendingSrv.length; i++){ if(F.pendingSrv[i].video_id === sit.video_id){ F.pendingSrv.splice(i, 1); break; } }
      });
    }
    active += 1;
    try{ job.fn(); }catch(e){}
  }
  v4AiFolderRender(F.key);
}
function v4PhoneJobCancelCurrent(job){
  (job.items || []).forEach(function(it){
    if(it._st !== 'starting' && it._st !== 'downloading') return;
    if(it._timer){ clearInterval(it._timer); it._timer = null; }
    let live = [];
    try{ live = JSON.parse(PlayTubeApp.phoneDlState() || '[]'); }catch(e){}
    const ent = (it._entId && live.filter(function(x){ return x.id === it._entId; })[0]) || live.filter(function(x){ return x.videoId === it.video_id && x.status === 'running'; })[0];
    if(ent && PlayTubeApp.phoneDlCancel){ try{ PlayTubeApp.phoneDlCancel(ent.id); }catch(e){} }
    it._st = 'ustop';
  });
}
/* Update 118: fail hui phone row ka ↻ — wohi item dobara start,
   usi (ek hi) folder mein; purani fail row hat jati hai. */
function v4PhoneJobRetryItem(el){
  const job = (window._v4PhoneJobs || {})[el.getAttribute('data-job')]; if(!job) return;
  const idx = Number(el.getAttribute('data-idx'));
  const it = job.items[idx]; if(!it || it._st !== 'failed') return;
  it._st = 'deleted'; it._err = '';
  v4PhoneJobStart([{video_id: it.video_id, title: it.title}], job.quality, job.format, '', '', {key: job.folderKey, title: job.folderTitle});
  if(job.folderKey) v4AiFolderRender(job.folderKey);
}

/* ---------- Update 109: Mere Shows / Nayi Episode Check / Channel
   Mode / Aaj Ki Taza / Bol Kar Command ---------- */
const V4_CH_DRAMA_PK = ['ARY Digital', 'Hum TV', 'Geo TV', 'Har Pal Geo', 'Green TV', 'Express Entertainment', 'PTV Home', 'Urdu1', 'ARY Zindagi', 'Bol Entertainment', 'Aan TV'];
const V4_CH_DRAMA_IN = ['Star Plus', 'Colors TV', 'Zee TV', 'Dangal TV', 'Sony SAB'];
const V4_CH_YT = ['Coke Studio', '8XM', 'T-Series', 'ARY Musik'];
function v4ShowsGet(){ try{ return JSON.parse(localStorage.getItem('pt_ai_shows') || '[]'); }catch(e){ return []; } }
function v4ShowsSet(a){ try{ localStorage.setItem('pt_ai_shows', JSON.stringify(a)); }catch(e){} }
function v4ShowSaved(name){ const l = (name || '').toLowerCase(); return v4ShowsGet().some(function(s){ return (s.name || '').toLowerCase() === l; }); }
function v4ShowToggle(name){
  let a = v4ShowsGet(); const l = name.toLowerCase();
  if(a.some(function(s){ return (s.name || '').toLowerCase() === l; })) a = a.filter(function(s){ return (s.name || '').toLowerCase() !== l; });
  else a.push({name:name, lastEp:0});
  v4ShowsSet(a);
}
function v4ShowTrackTitle(title){
  if(!title) return;
  const m = /episode\s*#?\s*(\d+)/i.exec(title); if(!m) return;
  const ep = +m[1]; const tl = String(title).toLowerCase();
  const a = v4ShowsGet(); let ch = false;
  a.forEach(function(s){ if(s.name && tl.indexOf(s.name.toLowerCase()) >= 0 && ep > (s.lastEp || 0)){ s.lastEp = ep; ch = true; } });
  if(ch) v4ShowsSet(a);
}
function v4ShowChip(name){
  const btn = document.createElement('button'); btn.className = 'v4-chip'; btn.type = 'button';
  const paint = function(){ const on = v4ShowSaved(name); btn.textContent = name + (on ? ' ✓' : ' +'); btn.style.borderColor = on ? '#14b8a6' : ''; btn.style.color = on ? '#5eead4' : ''; };
  paint();
  btn.onclick = function(){ v4ShowToggle(name); paint(); };
  return btn;
}
function v4RenderShowsPanel(b){
  b.innerHTML = '';
  const hd = document.createElement('div'); hd.textContent = '📺 Mere Shows — save kiye hue channel/show ki nayi episode ane par AI kholte hi upar bata dega. Jis par ✓ hai wo save hai:'; b.appendChild(hd);
  const mk = function(label, names){
    const h = document.createElement('div'); h.style.cssText = 'font-size:12px;font-weight:800;margin-top:9px;opacity:.9'; h.textContent = label; b.appendChild(h);
    const row = document.createElement('div'); row.className = 'v4-chips'; row.style.margin = '4px 0 6px';
    names.forEach(function(n){ row.appendChild(v4ShowChip(n)); });
    b.appendChild(row);
  };
  mk('🎭 Drama Channels — Pakistani', V4_CH_DRAMA_PK);
  mk('🇮🇳 Drama Channels — Indian', V4_CH_DRAMA_IN);
  mk('▶️ YouTube Channels', V4_CH_YT);
  const h2 = document.createElement('div'); h2.style.cssText = 'font-size:12px;font-weight:800;margin-top:9px;opacity:.9'; h2.textContent = '➕ Apna show / channel (koi bhi)'; b.appendChild(h2);
  const row = document.createElement('div'); row.style.cssText = 'display:flex;gap:6px;margin-top:4px';
  const inp = document.createElement('input'); inp.className = 'v4-input'; inp.placeholder = 'Show ya channel ka naam likhein...'; inp.style.flex = '1';
  const add = document.createElement('button'); add.className = 'v4-btn2'; add.textContent = '+ Save';
  add.onclick = function(){
    const nm = inp.value.trim(); if(!nm) return;
    if(!v4ShowSaved(nm)) v4ShowToggle(nm);
    v4Toast('✓ "' + nm + '" save ho gaya');
    v4RenderShowsPanel(b);
  };
  row.appendChild(inp); row.appendChild(add); b.appendChild(row);
}
function v4AiShowsPanel(){ const b = v4AiBubble('📺 Mere Shows'); v4RenderShowsPanel(b); }
async function v4AiShowCheck(){
  const shows = v4ShowsGet(); if(!shows.length) return;
  let last = 0; try{ last = Number(localStorage.getItem('pt_ai_show_check_ts') || '0'); }catch(e){}
  if(Date.now() - last < 30 * 60 * 1000) return;
  try{ localStorage.setItem('pt_ai_show_check_ts', String(Date.now())); }catch(e){}
  const r = await v4Post('/api/ai/show-check', {shows: shows.map(function(s){ return s.name; })});
  const d = r.data || {}; if(!r.ok || !d.results) return;
  const box = v4$('v4-ai-msgs'); if(!box) return;
  window._v4ShowAlerts = window._v4ShowAlerts || {};
  d.results.forEach(function(res){
    const a = v4ShowsGet();
    const s = a.filter(function(x){ return (x.name || '').toLowerCase() === (res.show || '').toLowerCase(); })[0];
    if(!s) return;
    if(!(s.lastEp > 0)){ s.lastEp = res.ep; v4ShowsSet(a); return; }
    if(res.ep > s.lastEp && !window._v4ShowAlerts[res.show]){
      window._v4ShowAlerts[res.show] = 1;
      const card = document.createElement('div'); card.className = 'v4-bubble ai v4-showalert'; card.setAttribute('data-ts', String(Date.now()));
      const tx = document.createElement('div'); tx.textContent = '📺 ' + res.show + ' ki nayi Episode ' + res.ep + ' aa gayi hai!'; card.appendChild(tx);
      if(res.title){ const t2 = document.createElement('div'); t2.className = 'v4-muted'; t2.textContent = res.title; card.appendChild(t2); }
      const row = document.createElement('div'); row.style.cssText = 'display:flex;gap:6px;margin-top:8px';
      const dl = document.createElement('button'); dl.className = 'v4-btn2'; dl.textContent = '⬇ Download karein';
      dl.onclick = function(){ v4AiQuickSend(res.show + ' episode ' + res.ep); };
      const later = document.createElement('button'); later.className = 'v4-btn2'; later.textContent = 'Baad mein';
      later.onclick = function(){
        const a2 = v4ShowsGet(); a2.forEach(function(x){ if((x.name || '').toLowerCase() === (res.show || '').toLowerCase()) x.lastEp = res.ep; }); v4ShowsSet(a2);
        card.remove();
      };
      row.appendChild(dl); row.appendChild(later); card.appendChild(row);
      box.insertBefore(card, box.firstChild);
    }
  });
}
function v4AiChannelPanel(){
  const b = v4AiBubble('📂 Channel Mode — channel chunein, us ki latest 50 videos ki list aa jayegi:');
  const mk = function(label, names){
    const h = document.createElement('div'); h.style.cssText = 'font-size:12px;font-weight:800;margin-top:9px;opacity:.9'; h.textContent = label; b.appendChild(h);
    const row = document.createElement('div'); row.className = 'v4-chips'; row.style.margin = '4px 0 6px';
    names.forEach(function(n){
      const btn = document.createElement('button'); btn.className = 'v4-chip'; btn.type = 'button'; btn.textContent = n;
      btn.onclick = function(){ v4AiChannelGo(n); };
      row.appendChild(btn);
    });
    b.appendChild(row);
  };
  mk('🎭 Drama — Pakistani', V4_CH_DRAMA_PK);
  mk('🇮🇳 Drama — Indian', V4_CH_DRAMA_IN);
  mk('▶️ YouTube Channels', V4_CH_YT);
  const row = document.createElement('div'); row.style.cssText = 'display:flex;gap:6px;margin-top:6px';
  const inp = document.createElement('input'); inp.className = 'v4-input'; inp.placeholder = 'Koi aur channel likhein...'; inp.style.flex = '1';
  const go = document.createElement('button'); go.className = 'v4-btn2'; go.textContent = 'List lao';
  go.onclick = function(){ const nm = inp.value.trim(); if(nm) v4AiChannelGo(nm); };
  row.appendChild(inp); row.appendChild(go); b.appendChild(row);
}
function v4AiChannelGo(name){ v4AiSend(null, 'channel:' + name, '📂 ' + name); }
function v4AiTazaOpen(){
  const b = v4AiBubble('🆕 Aaj Ki Taza — kya dekhna hai? Upar se chunein, list isi box mein badlegi:');
  const opts = [['drama', '🎭 Aaj ki nayi drama episodes'], ['teaser', '🎬 Aaj ke naye Teaser / Trailer'], ['songs', '🎵 Aaj ke naye ganay'], ['mine', '📺 Mere save channels se'], ['mix', '🌐 Sab kuch mix']];
  const orow = document.createElement('div'); orow.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px';
  const holder = document.createElement('div');
  const btns = [];
  opts.forEach(function(o){
    const ob = document.createElement('button'); ob.className = 'v4-btn2'; ob.textContent = o[1];
    ob.onclick = function(){
      btns.forEach(function(x){ x.style.background = ''; x.style.color = ''; });
      ob.style.background = '#7c5cff'; ob.style.color = '#fff';
      v4AiTazaLoad(holder, o[0]);
    };
    btns.push(ob); orow.appendChild(ob);
  });
  b.appendChild(orow); b.appendChild(holder);
}
async function v4AiTazaLoad(holder, kind){
  holder.innerHTML = '';
  const load = document.createElement('div'); load.className = 'v4-muted'; load.style.marginTop = '8px'; load.textContent = 'Load ho raha hai...'; holder.appendChild(load);
  const shows = v4ShowsGet().map(function(s){ return s.name; });
  const r = await v4Post('/api/ai/taza', {kind: kind, shows: shows});
  const d = r.data || {};
  holder.innerHTML = '';
  if(!r.ok || !d.candidates || !d.candidates.length){
    const p = document.createElement('div'); p.className = 'v4-muted'; p.style.marginTop = '8px';
    p.textContent = (kind === 'mine' && !shows.length) ? 'Pehle 📺 Mere Shows mein koi channel save karein.' : (kind === 'teaser' ? 'Aaj koi naya teaser / trailer nahi mila — thodi dair baad try karein.' : 'Aaj ki koi nayi video nahi mili — thodi dair baad try karein.');
    holder.appendChild(p); return;
  }
  const hd = document.createElement('div'); hd.style.marginTop = '8px'; hd.textContent = '🆕 ' + d.candidates.length + ' nayi videos mili — select karke download karein:'; holder.appendChild(hd);
  const ctx = v4RenderCandidates(holder, d.candidates, {quality:'360p', format:'mp4', qexp:false, show:'', category:'', kind: kind === 'songs' ? 'songs' : '', src:'🆕 Aaj Ki Taza'});
  window._v4CandCtx = ctx;
}
function v4AiMicInit(){
  const btn = v4$('v4-ai-mic'); if(!btn) return;
  if(window.SpeechRecognition || window.webkitSpeechRecognition) btn.style.display = '';
}
function v4AiMic(){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR){ v4Toast('Is phone/browser mein voice support nahi'); return; }
  let rec;
  try{ rec = new SR(); }catch(e){ v4Toast('Mic start nahi ho saka'); return; }
  rec.lang = 'ur-PK'; rec.interimResults = false; rec.maxAlternatives = 1;
  const inp = v4$('v4-ai-input'); if(!inp) return;
  const old = inp.placeholder; inp.placeholder = '🎤 Sun raha hoon… bolein';
  let retried = false;
  rec.onresult = function(ev){
    const t = (ev.results && ev.results[0] && ev.results[0][0] && ev.results[0][0].transcript) || '';
    inp.placeholder = old;
    if(t){ inp.value = t; v4AiSend(null); }
  };
  rec.onerror = function(ev){
    if(ev && ev.error === 'not-allowed'){ inp.placeholder = old; v4Toast('Mic ki ijazat dein — phir bol kar command chalega'); return; }
    if(!retried && rec.lang === 'ur-PK'){ retried = true; try{ rec.lang = 'en-US'; rec.start(); return; }catch(e){} }
    inp.placeholder = old;
    v4Toast('Awaz samajh nahi ayi — dobara try karein');
  };
  rec.onend = function(){ if(inp.placeholder.indexOf('Sun raha') >= 0) inp.placeholder = old; };
  try{ rec.start(); }catch(e){ inp.placeholder = old; v4Toast('Mic start nahi ho saka'); }
}
/* Update 43: AI ko pic bhejo — parh kar khud download start */
function v4AiImage(input){
  const file = input.files && input.files[0];
  input.value = '';
  if(!file) return;
  const rd = new FileReader();
  rd.onload = function(){
    const img = new Image();
    img.onload = function(){
      const max = 1280;
      let w = img.width, h = img.height;
      if(w > max || h > max){ const s = max / Math.max(w, h); w = Math.round(w * s); h = Math.round(h * s); }
      const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
      cv.getContext('2d').drawImage(img, 0, 0, w, h);
      const dataUrl = cv.toDataURL('image/jpeg', 0.85);
      const ub = v4AiBubble('🖼 Pic bheji', true);
      const im = document.createElement('img'); im.src = dataUrl; im.style.cssText = 'max-width:200px;border-radius:10px;display:block;margin-top:6px'; ub.appendChild(im);
      const b = v4AiBubble('🤖 Pic parh raha hoon...');
      v4Post('/api/ai/image', {image: dataUrl}).then(function(r){
        const d = r.data || {};
        if(!r.ok || !d.success){ if(d.login_required){ v4Pending = {type:'ai'}; v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); b.textContent = 'Limit khatam — pehle account banayein.'; return; } b.textContent = d.message || d.error || 'Pic se download nahi ho saka — naam likh kar try karein'; return; }
        b.textContent = d.message;
        window._v4AttachCtx = {src:'🖼 Pic — ' + (d.title || 'video')}; if(d.job_id){ v4AiAttachJob(d.job_id); }
      });
    };
    img.src = rd.result;
  };
  rd.readAsDataURL(file);
}
/* Update 45: Private Folder (PIN) */
async function v4RenderPrivate(){
  const body = v4$('v4-priv-body'); if(!body) return;
  const st = await v4Fetch('/api/private/status');
  const d = (st && st.data) || {};
  if(!d.pin_set){
    body.innerHTML = '<p class="v4-muted">Pehli dafa apna PIN banayein (4-6 numbers). Isi PIN se private folder khule ga — PIN bhool na jana.</p>' +
      '<input class="v4-input" id="v4-priv-newpin" type="password" inputmode="numeric" maxlength="6" placeholder="Naya PIN">' +
      '<button class="v4-bigbtn" onclick="v4PrivSetPin()">PIN bana kar kholein</button>';
    return;
  }
  if(!d.unlocked){
    body.innerHTML = '<p class="v4-muted">Apna PIN likhein, private downloads dekhne ke liye.</p>' +
      '<input class="v4-input" id="v4-priv-pin" type="password" inputmode="numeric" maxlength="6" placeholder="PIN">' +
      '<button class="v4-bigbtn" onclick="v4PrivVerify()">Kholein</button>';
    return;
  }
  body.innerHTML = '<p class="v4-muted">Ye downloads aam Downloads list mein NAHI aati. <button class="v4-btn2" onclick="v4PrivLock()">🔒 Band kar dein</button></p><div id="v4-priv-list"><p class="v4-muted">Load ho raha hai...</p></div>';
  const r = await v4Fetch('/api/downloads-list?scope=private');
  const list = (r.data && r.data.downloads) || [];
  const box = v4$('v4-priv-list'); if(!box) return;
  if(!list.length){ box.innerHTML = '<p class="v4-muted">Abhi koi private download nahi. Downloads mein kisi video par 🔒 dabakar yahan chhupayein.</p>'; return; }
  box.innerHTML = list.map(function(x){
    v4DlMap[x.downloadId] = x;
    return v4DlRowHtml(x, false);
  }).join('');
}
async function v4PrivSetPin(){ const pin = v4$('v4-priv-newpin').value.trim(); const r = await v4Post('/api/private/set-pin', {pin:pin}); if(r.ok && r.data.success){ v4Toast('PIN ban gaya — folder khul gaya'); v4RenderPrivate(); } else v4Toast((r.data && r.data.error) || 'PIN nahi bana'); }
async function v4PrivVerify(){ const pin = v4$('v4-priv-pin').value.trim(); const r = await v4Post('/api/private/verify', {pin:pin}); if(r.ok && r.data.success){ v4RenderPrivate(); } else v4Toast('Galat PIN'); }
async function v4PrivLock(){ await v4Post('/api/private/lock', {}); v4RenderPrivate(); }
async function v4PrivToggle(id, make){ const r = await v4Post('/api/downloads/private', {download_id:id, private:make}); if(r.ok && r.data.success){ v4Toast(make ? 'Private folder mein chhupa di' : 'Private se bahar nikaal di'); v4LoadDownloads(); if(v4State.view === 'private') v4RenderPrivate(); } else v4Toast((r.data && r.data.error) || 'Nahi ho saka'); }
/* Update 49: Share — video file + message ke sath website link */
async function v4ShareDl(id, title, fmt){
  const url = window.location.origin + '/';
  const msg = '🎬 ' + (title || 'Video') + '\\n\\nYe video Playza se download ki hai — aap bhi free mein download karein:\\n' + url;
  v4Toast('Share tayyar ho raha hai...');
  try{
    const resp = await fetch('/api/download-file/' + id);
    if(resp.ok){
      const blob = await resp.blob();
      const badc = [92, 47, 58, 42, 63, 34, 60, 62, 124];
      let fname = (title || 'video').split('').filter(function(ch){ return badc.indexOf(ch.charCodeAt(0)) < 0; }).join('').trim().slice(0, 120) || 'video';
      const ext = (fmt || '').toUpperCase() === 'MP3' ? '.mp3' : '.mp4';
      const file = new File([blob], fname + ext, {type: blob.type || 'video/mp4'});
      if(navigator.canShare && navigator.canShare({files: [file]})){
        await navigator.share({files: [file], text: msg});
        return;
      }
    }
  }catch(e){ /* file share nahi ho saka — neeche link wala tareeqa */ }
  if(navigator.share){
    try{ await navigator.share({title: title || 'Playza Video', text: msg, url: url}); return; }catch(e){}
  }
  try{ await navigator.clipboard.writeText(msg); v4Toast('Message + website link copy ho gaya — WhatsApp par paste kar dein. Video gallery ke Playza folder se bhej dein.'); }
  catch(e){ v4Toast('Share is device par support nahi'); }
}
/* Update 45: Video Compressor — quality wohi, size kam */
async function v4RenderCompress(){
  const box = v4$('v4-cmp-list'); if(!box) return;
  const r = await v4Fetch('/api/downloads-list');
  const list = ((r.data && r.data.downloads) || []).filter(function(d){ return d.status === 'completed' && ['MP4','MKV','WEBM','3GP'].indexOf((d.format || '').toUpperCase()) >= 0 && (d.title || '').indexOf('(Chhoti)') < 0; });
  if(!list.length){ box.innerHTML = '<p class="v4-muted">Abhi koi mukammal video download nahi — pehle koi video download karein.</p>'; return; }
  box.innerHTML = list.map(function(d){
    return '<div class="v4-dlrow">' + (d.videoId ? v4Img(d.videoId) : '<span style="width:64px"></span>') + '<div class="tt"><div class="t1">' + v4Esc(d.title || '') + '</div><div class="t2">' + v4Esc([d.quality || '', v4MB(d.file_size)].filter(Boolean).join(' • ')) + '</div></div>' +
      '<button class="v4-roundbtn teal" title="Size kam karo" data-id="' + d.downloadId + '" onclick="v4CompressGo(this)">🗜</button></div>';
  }).join('');
}
async function v4CompressGo(btn){
  const id = btn.getAttribute('data-id');
  btn.disabled = true; btn.textContent = '◌';
  const r = await v4Post('/api/compress', {download_id: id});
  if(r.ok && r.data.success){ v4Toast('Compress shuru — Downloads mein progress dekhein'); v4Show('downloads'); }
  else { v4Toast((r.data && r.data.error) || 'Compress start nahi ho saka'); btn.disabled = false; btn.textContent = '🗜'; }
}
function v4PollJob(jobId){
  const tick = async function(){
    const r = await v4Fetch('/api/ai/jobs/' + jobId);
    if(!r.ok || !r.data || !r.data.job){ if(r.status === 404){ const _fk = v4AiFolderKeyOfJob(jobId); if(_fk){ const _F = (window._v4Folders || {})[_fk]; if(_F){ delete _F.serverJobs[jobId]; delete _F.serverData[jobId]; v4AiFolderJobsSave(); v4AiFolderRender(_fk); } if(v4JobTimers[jobId]){ clearInterval(v4JobTimers[jobId]); delete v4JobTimers[jobId]; } } else { const h = v4$('v4-job-' + jobId); if(h && h.parentNode) h.parentNode.style.display = 'none'; } } return; }
    const job = r.data.job;
    v4RenderJob(jobId, job);
    if(['completed','partial','failed','interrupted'].indexOf(job.status) >= 0){ clearInterval(v4JobTimers[jobId]); delete v4JobTimers[jobId]; v4LoadDownloads(); }
  };
  tick();
  v4JobTimers[jobId] = setInterval(tick, 3000);
}
function v4AiStopItem(el){
  const jid = el.getAttribute('data-job'); const idx = el.getAttribute('data-idx');
  v4Post('/api/ai/jobs/' + jid + '/stop-item', {index:Number(idx)}).then(function(){ v4Fetch('/api/ai/jobs/' + jid).then(function(r){ if(r.ok && r.data && r.data.job) v4RenderJob(jid, r.data.job); }); });
}
function v4AiStopAll(el){
  const jid = el.getAttribute('data-job');
  v4Post('/api/ai/jobs/' + jid + '/stop-all', {}).then(function(){ v4Fetch('/api/ai/jobs/' + jid).then(function(r){ if(r.ok && r.data && r.data.job) v4RenderJob(jid, r.data.job); }); });
}
function v4AiRetryItem(el){
  const jid = el.getAttribute('data-job'); const idx = el.getAttribute('data-idx');
  v4Post('/api/ai/jobs/' + jid + '/retry-item', {index:Number(idx)}).then(function(r){
    if(r.ok && r.data && r.data.success){ v4Toast('Dobara download shuru ho gaya'); if(!v4JobTimers[jid]) v4PollJob(jid); else v4Fetch('/api/ai/jobs/' + jid).then(function(rr){ if(rr.ok && rr.data && rr.data.job) v4RenderJob(jid, rr.data.job); }); }
    else v4Toast((r.data && r.data.error) || 'Retry nahi ho saka');
  });
}
function v4AiDeleteItem(el){
  const jid = el.getAttribute('data-job'); const idx = el.getAttribute('data-idx');
  v4Post('/api/ai/jobs/' + jid + '/delete-item', {index:Number(idx)}).then(function(r){
    if(r.ok && r.data && r.data.success){ v4Toast('Delete ho gaya'); v4Fetch('/api/ai/jobs/' + jid).then(function(rr){ if(rr.ok && rr.data && rr.data.job) v4RenderJob(jid, rr.data.job); }); v4LoadDownloads(); }
    else v4Toast((r.data && r.data.error) || 'Delete nahi ho saka');
  });
}
function v4AiDeleteAll(el){
  const jid = el.getAttribute('data-job'); if(!jid) return;
  el.disabled = true; el.textContent = 'Delete ho raha hai...';
  v4Post('/api/ai/jobs/' + jid + '/delete-all', {}).then(function(r){
    if(r.ok && r.data && r.data.success){
      if(v4JobTimers[jid]){ clearInterval(v4JobTimers[jid]); delete v4JobTimers[jid]; }
      try{ const a = JSON.parse(localStorage.getItem('pt_ai_chat') || '[]'); localStorage.setItem('pt_ai_chat', JSON.stringify(a.filter(function(e){ return e.job_id !== jid; }))); }catch(e){}
      const holder = v4$('v4-job-' + jid);
      if(holder && holder.parentNode) holder.parentNode.innerHTML = '<span>🗑 Poori list delete ho gayi — files bhi hata di gayin.</span>';
      v4Toast('Poori list delete ho gayi');
      v4LoadDownloads();
    } else {
      el.disabled = false; el.textContent = '🗑 All delete';
      v4Toast((r.data && r.data.error) || 'Delete nahi ho saka');
    }
  });
}
function v4RenderJob(jobId, job){
  const _fk = v4AiFolderKeyOfJob(jobId);
  if(_fk){ const _F = (window._v4Folders || {})[_fk]; if(_F){ _F.serverData[jobId] = job; v4AiFolderRender(_fk); v4FolderSched(); return; } }
  const holder = v4$('v4-job-' + jobId); if(!holder) return;
  const eps = job.episodes_status || [];
  const vis = eps.filter(function(e){ return e.status !== 'deleted'; });
  if(!vis.length){ holder.innerHTML = ''; return; }
  const total = vis.length;
  const done = vis.filter(function(e){ return e.status === 'completed'; }).length;
  let h = '<div class="v4-ailist"><div class="v4-ailist-h"><span class="t">📥 ' + total + ' videos</span><span class="cnt">' + done + ' / ' + total + '</span><button class="v4-sabband" data-job="' + jobId + '" onclick="v4AiStopAll(this)">⏹ All Stop</button><button class="v4-sabband" data-job="' + jobId + '" onclick="v4AiDeleteAll(this)">🗑 All delete</button></div><div class="v4-cand-box v4-job-box">';
  eps.forEach(function(es, i){
    if(es.status === 'deleted') return;
    const name = es.title || (es.episode != null ? ('Episode ' + es.episode) : ('Video ' + (i + 1)));
    if(es.status === 'completed') v4ShowTrackTitle(name);
    let icon, right = '', bar = '';
    if(es.status === 'completed') icon = '<span class="v4-ai-ic ok">✓</span>';
    else if(es.status === 'downloading'){ icon = '<span class="v4-ai-ic dl">⬇</span>'; right = '<span class="pct">' + (es.percent || 0) + '%</span><span class="v4-ai-stop" data-job="' + jobId + '" data-idx="' + i + '" onclick="event.stopPropagation();v4AiDeleteItem(this)" title="Band + delete">✕</span>'; bar = '<div class="v4-ai-bar"><i style="width:' + (es.percent || 0) + '%"></i></div>'; }
    else if(es.status === 'searching'){ icon = '<span class="v4-ai-ic dl">⬇</span>'; right = '<span class="pct">…</span>'; }
    else if(es.status === 'failed'){ icon = '<span class="v4-ai-ic bad">✗</span>'; right = '<span class="v4-ai-stop" style="background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.55);color:#5eead4;cursor:pointer" data-job="' + jobId + '" data-idx="' + i + '" onclick="event.stopPropagation();v4AiRetryItem(this)">↻</span>'; }
    else if(es.status === 'stopped'){ icon = '<span class="v4-ai-ic stop">⏹</span>'; right = '<span class="v4-ai-stop" style="background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.55);color:#5eead4;cursor:pointer" data-job="' + jobId + '" data-idx="' + i + '" onclick="event.stopPropagation();v4AiRetryItem(this)">↻</span>'; }
    else icon = '<span class="v4-ai-ic">' + (i + 1) + '</span>';
    const tap = (es.status === 'downloading' || es.status === 'searching') ? ' data-job="' + jobId + '" data-idx="' + i + '" onclick="v4AiDeleteItem(this)" style="cursor:pointer"' : '';
    const _delIc = (es.status === 'completed' || es.status === 'failed' || es.status === 'stopped') ? '🗑' : '✕';
    right += '<span class="v4-ai-stop" data-job="' + jobId + '" data-idx="' + i + '" onclick="event.stopPropagation();v4AiDeleteItem(this)" title="Delete">' + _delIc + '</span>';
    h += '<div class="v4-ai-row' + (es.status === 'downloading' ? ' act' : '') + '"' + tap + '><div class="v4-ai-r1">' + icon + '<span class="v4-ai-t">' + v4Esc(name) + '</span>' + right + '</div>' + bar + '</div>';
  });
  holder.innerHTML = h + '</div></div>';
}
/* ---------- Update 114 (corrected): AI downloads ke PER-PURPOSE
   folders — har show/kaam ka apna folder; usi kaam ki nayi downloads
   USI folder mein add hoti hain (naya folder sirf naye kaam par),
   folder har update par chat ke aakhir mein aa jata hai. ---------- */
let v4AiFolderSeq = 0;
/* Update 118 (user override 20:49): AI ki SAARI downloads EK hi
   folder mein jati hain — per-show/per-surface folders khatam.
   Nayi download (koi bhi surface: search, episodes, similar, taza,
   channel, playlist, link, pic — phone ho ya server) isi ek folder
   mein add hoti hai; andar nayi/running item sab se UPAR rehti hai. */
const V4_FOLDER_KEY = 'downloads';
function v4AiFolderKeyOf(c, items){ return {key: V4_FOLDER_KEY, title: '📥 Downloads'}; }
function v4AiFolderKeyFor(c){ return V4_FOLDER_KEY; }
function v4AiFolderTitleFor(c){ return '📥 Downloads'; }
function v4AiFolderGet(key, title){
  /* Update 118: purana jo bhi key aye (v38 ke per-purpose folders),
     card EK hi banta hai — baqi sab isi mein merge ho jate hain. */
  key = V4_FOLDER_KEY; title = '📥 Downloads';
  const F = (window._v4Folders = window._v4Folders || {});
  const box = v4$('v4-ai-msgs');
  let f = F[key];
  if(f && f.el){
    if(box) box.appendChild(f.el);
    return f;
  }
  const el = document.createElement('div');
  el.className = 'v4-bubble ai';
  el.setAttribute('data-ts', String(Date.now()));
  if(box) box.appendChild(el);
  f = F[key] = {key:key, title:title || 'Downloads', el:el, fid:'f' + (++v4AiFolderSeq), phoneJobs:{}, serverJobs:{}, serverData:{}, restoredDone:[]};
  if(!window._v4Restoring) v4AiStore({t:Date.now(), kind:'folder', key:key, title:f.title});
  return f;
}
function v4AiFolderByFid(fid){
  const F = window._v4Folders || {};
  for(const k in F){ if(F[k].fid === fid) return F[k]; }
  return null;
}
function v4AiFolderJobsSave(){
  try{
    const m = {};
    const F = window._v4Folders || {};
    Object.keys(F).forEach(function(k){ const j = Object.keys(F[k].serverJobs || {}); if(j.length) m[k] = j; });
    localStorage.setItem('pt_ai_folder_jobs', JSON.stringify(m));
  }catch(e){}
}
function v4AiFolderKeyOfJob(jobId){
  const F = window._v4Folders || {};
  for(const k in F){ if(F[k].serverJobs && F[k].serverJobs[jobId]) return k; }
  return '';
}
function v4AiFolderAddServerJob(key, title, jobId){
  const f = v4AiFolderGet(key, title);
  f.serverJobs[jobId] = 1;
  if(!f.jobSeq) f.jobSeq = {};
  if(!f.jobSeq[jobId]) f.jobSeq[jobId] = ++v4AiFolderSeq;
  v4AiFolderJobsSave();
  v4AiFolderRender(f.key);
  v4PollJob(jobId);
}
function v4AiAttachJob(jobId){
  const c = window._v4AttachCtx || {};
  v4AiFolderAddServerJob(v4AiFolderKeyFor(c), v4AiFolderTitleFor(c), jobId);
}
function v4AiFolderRowHtml(F, r){
  let icon, right = '', bar = '';
  const st = r.status;
  if(st === 'completed') icon = '<span class="v4-ai-ic ok">✓</span>';
  else if(st === 'downloading'){ icon = '<span class="v4-ai-ic dl">⬇</span>'; right = '<span class="pct">' + (r.pct || 0) + '%</span>'; bar = '<div class="v4-ai-bar"><i style="width:' + (r.pct || 0) + '%"></i></div>'; }
  else if(st === 'searching'){ icon = '<span class="v4-ai-ic dl">⬇</span>'; right = '<span class="pct">…</span>'; }
  else if(st === 'failed') icon = '<span class="v4-ai-ic bad">✗</span>';
  else if(st === 'stopped') icon = '<span class="v4-ai-ic stop">⏹</span>';
  else icon = '<span class="v4-ai-ic">•</span>';
  if(r.kind === 'server'){
    if(st === 'completed') v4ShowTrackTitle(r.title || '');
    if(st === 'failed' || st === 'stopped') right += '<span class="v4-ai-stop" style="background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.55);color:#5eead4;cursor:pointer" data-job="' + r.jobId + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4AiRetryItem(this)">↻</span>';
    const delIc = (st === 'completed' || st === 'failed' || st === 'stopped') ? '🗑' : '✕';
    right += '<span class="v4-ai-stop" data-job="' + r.jobId + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4AiDeleteItem(this)" title="Delete">' + delIc + '</span>';
  } else if(r.kind === 'phone'){
    if(st === 'failed') right += '<span class="v4-ai-stop" style="background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.55);color:#5eead4;cursor:pointer" data-job="' + r.jobKey + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4PhoneJobRetryItem(this)">↻</span>';
    const delIc2 = (st === 'completed') ? '🗑' : '✕';
    right += '<span class="v4-ai-stop" data-job="' + r.jobKey + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4PhoneJobDelItem(this)" title="Delete">' + delIc2 + '</span>';
  } else if(r.kind === 'srvpend'){
    right += '<span class="v4-ai-stop" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4SrvPendDel(this)" title="Line se hata dein">✕</span>';
  } else {
    right += '<span class="v4-ai-stop" data-fid="' + F.fid + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4AiFolderDelStored(this)" title="Delete">🗑</span>';
  }
  /* Update 120: har row ka APNA start/stop (bayan taraf) — click
     khamosh hai, koi bubble nahi; All-Stop halat mein ek item
     chalane se sirf wohi chalti hai. */
  let left = '';
  if(r.kind === 'phone'){
    if(st === 'downloading') left = '<span class="v4-ai-stop" data-job="' + r.jobKey + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4PhoneItemToggle(this)" title="Sirf ye rokein">⏸</span>';
    else if(st === 'stopped') left = '<span class="v4-ai-stop" style="background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.55);color:#5eead4" data-job="' + r.jobKey + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4PhoneItemToggle(this)" title="Sirf ye chalain">▶</span>';
    else if(st === 'pending') left = '<span class="v4-ai-stop" data-job="' + r.jobKey + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4PhoneItemToggle(this)" title="Line mein rokein">⏸</span>';
  } else if(r.kind === 'server'){
    if(st === 'downloading' || st === 'searching') left = '<span class="v4-ai-stop" data-job="' + r.jobId + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4SrvItemToggle(this)" title="Sirf ye rokein">⏸</span>';
    else if(st === 'stopped') left = '<span class="v4-ai-stop" style="background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.55);color:#5eead4" data-job="' + r.jobId + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4SrvItemToggle(this)" title="Sirf ye chalain">▶</span>';
    else if(st === 'pending' || st === 'queued') left = '<span class="v4-ai-stop" data-job="' + r.jobId + '" data-idx="' + r.idx + '" onclick="event.stopPropagation();v4SrvItemToggle(this)" title="Line mein rokein">⏸</span>';
  }
  return '<div class="v4-ai-row' + (st === 'downloading' ? ' act' : '') + '"><div class="v4-ai-r1">' + left + icon + '<span class="v4-ai-t">' + v4Esc(r.title || '') + '</span>' + right + '</div>' + (r.err && st === 'failed' ? '<div style="font-size:11px;color:#f87171;margin-top:2px">' + v4Esc(r.err) + '</div>' : '') + bar + '</div>';
}
function v4AiFolderRender(key){
  const F = (window._v4Folders || {})[key]; if(!F || !F.el) return;
  const rows = [];
  Object.keys(F.phoneJobs || {}).forEach(function(jk){
    const job = F.phoneJobs[jk]; if(!job) return;
    (job.items || []).forEach(function(it, i){
      if(it._st === 'deleted') return;
      let st = 'pending';
      if(it._st === 'done') st = 'completed';
      else if(it._st === 'failed') st = 'failed';
      else if(it._st === 'starting' || it._st === 'downloading') st = 'downloading';
      else if(it._st === 'ustop' || it._hold || job.userStopped) st = 'stopped';
      rows.push({title: it.title || '', status: st, pct: it._pct || 0, kind:'phone', jobKey: jk, idx: i, ord: rows.length, seq: job.id || 0, err: it._err || ''});
    });
  });
  Object.keys(F.serverJobs || {}).forEach(function(jid){
    const job = F.serverData[jid]; if(!job) return;
    (job.episodes_status || []).forEach(function(es, i){
      if(es.status === 'deleted') return;
      rows.push({title: es.title || (es.episode != null ? ('Episode ' + es.episode) : ''), status: es.status, pct: es.percent || 0, kind:'server', jobId: jid, idx: i, ord: rows.length, seq: (F.jobSeq && F.jobSeq[jid]) || 0, err: es.error || ''});
    });
  });
  (F.pendingSrv || []).forEach(function(p, i){ rows.push({title: p.title || '', status:'pending', pct: 0, kind:'srvpend', idx: i, ord: rows.length, seq: 1000000 - i, err: ''}); });
  (F.restoredDone || []).forEach(function(rd, i){ rows.push({title: rd.title || '', status:'completed', pct:100, kind:'stored', idx: i, ord: rows.length}); });
  const rank = {downloading:0, searching:1, pending:2, queued:2, failed:3, stopped:3, completed:4};
  rows.sort(function(a, b){
    const ra = (rank[a.status] != null) ? rank[a.status] : 2;
    const rb = (rank[b.status] != null) ? rank[b.status] : 2;
    if(ra !== rb) return ra - rb;
    /* Update 118: nayi download hamesha UPAR — pehle naye kaam ki bari */
    const sa = a.seq || 0, sb = b.seq || 0;
    if(sa !== sb) return sb - sa;
    if(ra === 4) return b.ord - a.ord;
    return a.ord - b.ord;
  });
  const total = rows.length;
  const done = rows.filter(function(r){ return r.status === 'completed'; }).length;
  /* Update 118 addendum: All Stop <-> All Start EK hi toggle button —
     label folder ki asal halat se banta hai, har render par fresh. */
  let anyActive = false, anyResumable = false;
  rows.forEach(function(r){ if(r.status === 'downloading' || r.status === 'searching' || r.status === 'pending' || r.status === 'queued') anyActive = true; if(r.status === 'stopped') anyResumable = true; });
  const tglMode = anyActive ? 'stop' : (anyResumable ? 'start' : 'stop');
  const tglLbl = (tglMode === 'start') ? '▶ All Start' : '⏹ All Stop';
  let h = '<div class="v4-ailist"><div class="v4-ailist-h"><span class="t">' + v4Esc(F.title) + '</span><span class="cnt">' + done + ' / ' + total + '</span><button class="v4-sabband" data-fid="' + F.fid + '" data-mode="' + tglMode + '" onclick="v4AiFolderToggleAll(this)">' + tglLbl + '</button><button class="v4-sabband" data-fid="' + F.fid + '" onclick="v4AiFolderDeleteAll(this)">🗑 All delete</button></div><div class="v4-cand-box v4-job-box">';
  if(!total) h += '<div class="v4-ep"><span style="flex:1;font-size:13px">Load ho raha hai...</span></div>';
  rows.forEach(function(r){ h += v4AiFolderRowHtml(F, r); });
  h += '</div></div>';
  F.el.innerHTML = h;
  const box = v4$('v4-ai-msgs'); if(box && F.el.parentNode === box) box.appendChild(F.el);
}
function v4PhoneItemToggle(el){
  /* Update 120: phone row ka apna start/stop — khamosh click. */
  const job = (window._v4PhoneJobs || {})[el.getAttribute('data-job')]; if(!job) return;
  const idx = Number(el.getAttribute('data-idx'));
  const it = job.items[idx]; if(!it || it._st === 'deleted' || it._st === 'done') return;
  if(it._st === 'starting' || it._st === 'downloading'){
    it._wantStop = true; it._hold = true;
    try{
      let live = [];
      try{ live = JSON.parse(PlayTubeApp.phoneDlState() || '[]'); }catch(e){}
      const ent = (it._entId && live.filter(function(x){ return x.id === it._entId; })[0]) || live.filter(function(x){ return x.videoId === it.video_id && !(it._preIds && it._preIds[x.id]); })[0];
      if(ent && PlayTubeApp.phoneDlCancel){ try{ PlayTubeApp.phoneDlCancel(ent.id); }catch(e){} }
      else if(!it._entId){
        setTimeout(function(){
          try{
            const live2 = JSON.parse(PlayTubeApp.phoneDlState() || '[]');
            const claims = window._v4EntClaim || {};
            live2.forEach(function(x){ if(x.videoId === it.video_id && x.status === 'running' && !claims[x.id] && !(it._preIds && it._preIds[x.id])){ try{ PlayTubeApp.phoneDlCancel(x.id); }catch(e){} } });
          }catch(e){}
        }, 4000);
      }
    }catch(e){}
    if(it._timer){ clearInterval(it._timer); it._timer = null; }
    it._st = 'ustop';
    v4PhoneJobRender(job); v4FolderSched();
    return;
  }
  if(it._st === 'failed') return;
  /* start — sirf ye item; All-Stop halat mein baqi sab ruki rehti hain */
  if(job.userStopped){
    job.userStopped = false;
    (job.items || []).forEach(function(o){ if(o !== it && !o._st) o._hold = true; });
  }
  it._hold = false; it._wantStop = false;
  it._st = undefined;
  v4PhoneJobRender(job); v4FolderSched();
}
function v4SrvItemToggle(el){
  /* Update 120: server row ka apna start/stop — khamosh, maujooda
     stop-item / retry-item raste se, koi bubble/toast nahi. */
  const jid = el.getAttribute('data-job'); const idx = Number(el.getAttribute('data-idx'));
  const F = (window._v4Folders || {})[V4_FOLDER_KEY];
  const job = F && F.serverData[jid];
  const es = job && (job.episodes_status || [])[idx];
  if(!es) return;
  const start = (es.status === 'stopped');
  v4Post('/api/ai/jobs/' + jid + (start ? '/retry-item' : '/stop-item'), {index: idx}).then(function(){
    v4Fetch('/api/ai/jobs/' + jid).then(function(r){ if(r.ok && r.data && r.data.job) v4RenderJob(jid, r.data.job); });
  });
}
function v4AiFolderStopAll(el){
  const F = v4AiFolderByFid(el.getAttribute('data-fid')); if(!F) return;
  Object.keys(F.phoneJobs || {}).forEach(function(jk){ const job = F.phoneJobs[jk]; if(job){ job.userStopped = true; v4PhoneJobCancelCurrent(job); } });
  window._v4SrvQueue = [];
  if(F.pendingSrv && F.pendingSrv.length) F.pendingSrv = [];
  Object.keys(F.serverJobs || {}).forEach(function(jid){
    v4Post('/api/ai/jobs/' + jid + '/stop-all', {}).then(function(){ v4Fetch('/api/ai/jobs/' + jid).then(function(r){ if(r.ok && r.data && r.data.job) v4RenderJob(jid, r.data.job); }); });
  });
  v4AiFolderRender(F.key);
  v4Toast('Is folder ki sab downloads band kar di gayin');
}
function v4AiFolderToggleAll(el){
  const F = v4AiFolderByFid(el.getAttribute('data-fid')); if(!F) return;
  if(el.getAttribute('data-mode') === 'start'){ v4AiFolderStartAll(F); return; }
  v4AiFolderStopAll(el);
}
function v4AiFolderStartAll(F){
  /* Toggle ka dusra rukh: user ki roki hui downloads dobara chalti
     hain — phone items runner mein wapas, server ki stopped rows
     maujooda retry-item raste se. */
  Object.keys(F.phoneJobs || {}).forEach(function(jk){
    const job = F.phoneJobs[jk]; if(!job) return;
    job.userStopped = false;
    (job.items || []).forEach(function(it){ it._hold = false; it._wantStop = false; if(it._st === 'ustop') it._st = undefined; });
  });
  Object.keys(F.serverJobs || {}).forEach(function(jid){
    const job = F.serverData[jid]; if(!job) return;
    (job.episodes_status || []).forEach(function(es, i){ if(es.status === 'stopped'){ v4Post('/api/ai/jobs/' + jid + '/retry-item', {index: i}); } });
  });
  v4AiFolderRender(F.key);
  v4FolderSched();
  v4Toast('Sab downloads dobara start kar di gayin');
}
function v4AiFolderDeleteAll(el){
  const F = v4AiFolderByFid(el.getAttribute('data-fid')); if(!F) return;
  el.disabled = true;
  Object.keys(F.phoneJobs || {}).forEach(function(jk){ const job = F.phoneJobs[jk]; if(job) v4PhoneJobDeleteAll(job); delete F.phoneJobs[jk]; });
  const jids = Object.keys(F.serverJobs || {});
  jids.forEach(function(jid){
    if(v4JobTimers[jid]){ clearInterval(v4JobTimers[jid]); delete v4JobTimers[jid]; }
    v4Post('/api/ai/jobs/' + jid + '/delete-all', {});
    delete F.serverJobs[jid]; delete F.serverData[jid];
  });
  if(F.restoredDone && F.restoredDone.length){
    try{
      const vids = {}; F.restoredDone.forEach(function(rd){ if(rd.videoId) vids[rd.videoId] = 1; });
      let stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]');
      stored = stored.filter(function(s){ return !vids[s.videoId]; });
      localStorage.setItem('pt_phone_dl', JSON.stringify(stored));
      if(window.PlayTubeApp && PlayTubeApp.phoneDlState && PlayTubeApp.phoneDlRemove){
        const live = JSON.parse(PlayTubeApp.phoneDlState() || '[]');
        live.forEach(function(p){ if(vids[p.videoId]){ try{ PlayTubeApp.phoneDlRemove(p.id); }catch(e){} } });
      }
    }catch(e){}
    F.restoredDone = [];
  }
  v4AiFolderJobsSave();
  try{ const a = JSON.parse(localStorage.getItem('pt_ai_chat') || '[]'); localStorage.setItem('pt_ai_chat', JSON.stringify(a.filter(function(e){ return e.kind !== 'folder' && jids.indexOf(e.job_id) < 0; }))); }catch(e){}
  if(F.el && F.el.parentNode) F.el.parentNode.removeChild(F.el);
  delete (window._v4Folders || {})[F.key];
  window._v4phSig = '';
  try{ v4PhoneDlRender(); }catch(e){}
  v4LoadDownloads();
  v4Toast('Poora folder delete ho gaya');
}
function v4AiFolderDelStored(el){
  const F = v4AiFolderByFid(el.getAttribute('data-fid')); if(!F) return;
  const idx = Number(el.getAttribute('data-idx'));
  const rd = (F.restoredDone || [])[idx]; if(!rd) return;
  try{
    if(rd.videoId){
      if(window.PlayTubeApp && PlayTubeApp.phoneDlState && PlayTubeApp.phoneDlRemove){
        const live = JSON.parse(PlayTubeApp.phoneDlState() || '[]');
        live.forEach(function(p){ if(p.videoId === rd.videoId){ try{ PlayTubeApp.phoneDlRemove(p.id); }catch(e){} } });
      }
      let stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]');
      stored = stored.filter(function(s){ return s.videoId !== rd.videoId; });
      localStorage.setItem('pt_phone_dl', JSON.stringify(stored));
    }
  }catch(e){}
  F.restoredDone.splice(idx, 1);
  window._v4phSig = '';
  try{ v4PhoneDlRender(); }catch(e){}
  v4AiFolderRender(F.key);
}
function v4AiFolderRefill(){
  /* Update 118 migration: v38 ke per-purpose folders ka saara data
     (server job ids + phone ki mukammal downloads) EK hi folder
     mein merge — purane alag cards wapas nahi bante. */
  const F = (window._v4Folders || {})[V4_FOLDER_KEY];
  if(!F) return;
  try{
    const m = JSON.parse(localStorage.getItem('pt_ai_folder_jobs') || '{}');
    Object.keys(m).forEach(function(k){
      (m[k] || []).forEach(function(jid){ if(!F.serverJobs[jid]){ F.serverJobs[jid] = 1; if(!F.jobSeq) F.jobSeq = {}; if(!F.jobSeq[jid]) F.jobSeq[jid] = ++v4AiFolderSeq; v4PollJob(jid); } });
    });
    v4AiFolderJobsSave();
  }catch(e){}
  try{
    const stored = JSON.parse(localStorage.getItem('pt_phone_dl') || '[]');
    const have = {}; (F.restoredDone || []).forEach(function(rd){ have[rd.videoId] = 1; });
    stored.forEach(function(s){ if(s.title && !have[s.videoId]) F.restoredDone.push({title: s.title, videoId: s.videoId}); });
    if(F.restoredDone.length) v4AiFolderRender(V4_FOLDER_KEY);
  }catch(e){}
}

/* ---------- Update 122: System clean (Tools) — sirf Playza ka
   apna kachra: browser cache, AI chat, server ki temp files. */
function v4LSSize(){ let n = 0; try{ for(let i = 0; i < localStorage.length; i++){ const k = localStorage.key(i); n += (k || '').length + (localStorage.getItem(k) || '').length; } }catch(e){} return n; }
async function v4RenderSysClean(){
  const box = v4$('v4-clean-body'); if(!box) return;
  let cacheN = 0, est = '';
  try{ if(window.caches){ const ks = await caches.keys(); cacheN = ks.length; } }catch(e){}
  try{ if(navigator.storage && navigator.storage.estimate){ const e2 = await navigator.storage.estimate(); if(e2 && e2.usage) est = ' • kul istemal ~' + (e2.usage / 1048576).toFixed(1) + ' MB'; } }catch(e){}
  const lsKb = Math.round(v4LSSize() / 102.4) / 10;
  box.innerHTML =
    '<div class="v4-row"><div class="grow">Playza cache (app/browser)<div class="v4-muted">' + cacheN + ' cache dabbe' + est + '</div></div><button class="v4-btn2" onclick="v4CleanCache()">Saaf karein</button></div>' +
    '<div class="v4-row"><div class="grow">Save shuda data (settings, AI chat, lists)<div class="v4-muted">~' + lsKb + ' KB — AI chat ki purani baatein yahin se saaf hongi</div></div><button class="v4-btn2" onclick="v4CleanAiChat()">AI chat saaf</button></div>' +
    '<div class="v4-row"><div class="grow">Server par Playza ki temp files<div class="v4-muted">Pic-pehchan (OCR) ki temp + record ke baghair padi purani files</div></div><button class="v4-btn2" onclick="v4CleanServer(this)">Server saaf karein</button></div>' +
    '<p class="v4-muted" style="margin-top:8px">Aap ki mukammal downloads, account aur dusri apps is se bilkul mehfooz hain.</p>';
}
async function v4CleanCache(){
  try{ if(window.caches){ const ks = await caches.keys(); for(const k of ks) await caches.delete(k); } }catch(e){}
  v4Toast('Cache saaf ho gaya'); v4RenderSysClean();
}
function v4CleanAiChat(){
  try{ localStorage.removeItem('pt_ai_chat'); }catch(e){}
  const box = v4$('v4-ai-msgs'); if(box){ box.innerHTML = ''; box.removeAttribute('data-restored'); }
  window._v4Folders = {}; window._v4CandBubble = null;
  v4Toast('AI chat saaf ho gayi'); v4RenderSysClean();
}
async function v4CleanServer(btn){
  if(btn) btn.disabled = true;
  const r = await v4Post('/api/system-clean', {});
  if(r.ok && r.data && r.data.success) v4Toast('Server se ' + (r.data.freed_mb || 0) + ' MB kachra saaf — ab ' + (r.data.free_mb || 0) + ' MB khaali');
  else v4Toast('Server safai nahi ho saki');
  if(btn) btn.disabled = false;
  v4RenderSysClean();
}

/* ---------- Update 122: YouTube account (Tools) — SnapTube wala
   tareeqa: sign-in Google ke apne page par (APK mein alag page),
   andar YouTube ki apni History/Playlists/Watch later khulti hain.
   Password Playza ko kabhi nahi milta. ---------- */
function v4YtLinked(){ try{ return localStorage.getItem('pt_yt_linked') === '1'; }catch(e){ return false; } }
function v4YtLinkResult(ok){
  try{ if(ok) localStorage.setItem('pt_yt_linked', '1'); else localStorage.removeItem('pt_yt_linked'); }catch(e){}
  if(ok) v4Toast('YouTube account link ho gaya ✓');
  if(v4State.view === 'ytaccount') v4RenderYtAccount();
}
function v4YtOpen(url){
  if(window.PlayTubeApp && PlayTubeApp.ytOpen){ try{ PlayTubeApp.ytOpen(url); return; }catch(e){} }
  window.open(url, '_blank');
}
function v4YtOpenEl(el){ v4YtOpen(el.getAttribute('data-url')); }
function v4YtSignIn(){
  v4YtOpen('https://accounts.google.com/ServiceLogin?service=youtube&continue=' + encodeURIComponent('https://www.youtube.com/signin'));
  if(!(window.PlayTubeApp && PlayTubeApp.ytOpen)){ try{ localStorage.setItem('pt_yt_linked', '1'); }catch(e){} setTimeout(function(){ v4RenderYtAccount(); }, 500); }
}
function v4YtSignOut(){
  try{ localStorage.removeItem('pt_yt_linked'); }catch(e){}
  if(window.PlayTubeApp && PlayTubeApp.ytSignOut){ try{ PlayTubeApp.ytSignOut(); }catch(e){} }
  else window.open('https://accounts.google.com/Logout', '_blank');
  v4RenderYtAccount();
  v4Toast('Sign out ho gaya');
}
function v4RenderYtAccount(){
  const box = v4$('v4-yt-body'); if(!box) return;
  if(!v4YtLinked()){
    box.innerHTML =
      '<div style="text-align:center;padding:14px 6px"><div style="font-size:30px">▶️</div>' +
      '<div style="font-weight:800;font-size:16px;margin-top:6px">Get all YouTube features on Playza</div>' +
      '<p class="v4-muted">Apna YouTube account link karein — phir aap ki Subscriptions, Library, History aur Watch later yahin se khulengi; videos dekhna aur subscribe karna bhi wahin hoga.</p></div>' +
      '<div class="v4-row"><span>🔄</span><div class="grow">Sync your YouTube Library</div></div>' +
      '<div class="v4-row"><span>🕐</span><div class="grow">History and Watch Later</div></div>' +
      '<div class="v4-row"><span>🔔</span><div class="grow">Subscribe to new channels</div></div>' +
      '<button class="v4-bigbtn" style="margin-top:12px" onclick="v4YtSignIn()">Sign in</button>' +
      '<p class="v4-muted" style="margin-top:8px">Sign in Google ke apne page par hoga — aap ka password Playza ko kabhi nahi milta.</p>';
    return;
  }
  box.innerHTML =
    '<div style="display:flex;flex-direction:column;align-items:center;padding:10px 0 12px"><div style="width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#db2777);display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:#fff">Y</div>' +
    '<div style="font-weight:700;margin-top:8px">Mera YouTube account</div>' +
    '<div style="background:#123a34;border:1px solid #1f8a70;color:#4ade80;font-size:11.5px;font-weight:700;border-radius:999px;padding:5px 12px;margin-top:8px">✓ Link hai</div></div>' +
    '<button class="v4-bigbtn" data-url="https://www.youtube.com/" onclick="v4YtOpenEl(this)">▶ Mera YouTube kholein</button>' +
    '<div style="margin-top:12px">' +
    '<div class="v4-row" data-url="https://www.youtube.com/feed/history" onclick="v4YtOpenEl(this)"><span>🕐</span><div class="grow">History</div><span>›</span></div>' +
    '<div class="v4-row" data-url="https://www.youtube.com/feed/playlists" onclick="v4YtOpenEl(this)"><span>📋</span><div class="grow">Playlists</div><span>›</span></div>' +
    '<div class="v4-row" data-url="https://www.youtube.com/playlist?list=WL" onclick="v4YtOpenEl(this)"><span>⏰</span><div class="grow">Watch later</div><span>›</span></div>' +
    '<div class="v4-row" data-url="https://www.youtube.com/feed/subscriptions" onclick="v4YtOpenEl(this)"><span>🔔</span><div class="grow">Subscriptions</div><span>›</span></div>' +
    '<div class="v4-row" data-url="https://www.youtube.com/account" onclick="v4YtOpenEl(this)"><span>🛡</span><div class="grow">Restricted mode<div class="v4-muted">YouTube ki apni setting se on/off hoga</div></div><span>›</span></div>' +
    '<div class="v4-row" data-url="https://accounts.google.com/AccountChooser?continue=https%3A%2F%2Fwww.youtube.com%2F" onclick="v4YtOpenEl(this)"><span>🔄</span><div class="grow">Switch Account</div><span>›</span></div>' +
    '<div class="v4-row" onclick="v4YtSignOut()"><span>🚪</span><div class="grow" style="color:#ff8fa8">Sign out</div></div>' +
    '</div>';
}

/* ---------- search screen (Update 79: SnapTube-style alag page) ---------- */
let v4SearchState = {q:'', filter:'all', platform:'all'};
let v4SuggTimer = null;
const V4_HOT = ['new song', 'new drama', 'pakistani drama episode', 'motu patlu new episode', 'naat sharif 2026', 'punjabi song', 'hindi full movie', 'ertugrul urdu dubbed', 'funny shorts', 'coke studio season'];
function v4RecentGet(){ try{ return JSON.parse(localStorage.getItem('pt_recent') || '[]'); }catch(e){ return []; } }
function v4RecentAdd(q){ if(!q) return; let r = v4RecentGet().filter(function(x){ return x.toLowerCase() !== q.toLowerCase(); }); r.unshift(q); r = r.slice(0, 12); try{ localStorage.setItem('pt_recent', JSON.stringify(r)); }catch(e){} }
function v4RecentRemove(q){ const r = v4RecentGet().filter(function(x){ return x !== q; }); try{ localStorage.setItem('pt_recent', JSON.stringify(r)); }catch(e){} v4SuggRender(); }
function v4RecentClear(){ try{ localStorage.removeItem('pt_recent'); }catch(e){} v4SuggRender(); }
function v4OpenSearch(){
  const w = v4$('v4-searchwrap'); if(!w) return;
  w.classList.add('open'); v4Lock(true);
  const inp = v4$('v4-sq'); inp.value = '';
  v4SuggRender();
  setTimeout(function(){ inp.focus(); }, 80);
}
function v4CloseSearch(){ const w = v4$('v4-searchwrap'); if(w) w.classList.remove('open'); v4Lock(false); }
function v4ClearSearchInput(){ const inp = v4$('v4-sq'); inp.value = ''; v4SuggRender(); inp.focus(); }
function v4SuggHi(text, q){
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if(i < 0) return v4Esc(text);
  return v4Esc(text.slice(0, i)) + '<b>' + v4Esc(text.slice(i, i + q.length)) + '</b>' + v4Esc(text.slice(i + q.length));
}
function v4SuggRender(){
  const box = v4$('v4-sugg'); if(!box) return;
  const q = v4$('v4-sq').value.trim();
  if(!q){
    let h = '';
    const rec = v4RecentGet();
    if(rec.length){
      h += '<div style="display:flex;align-items:center;margin-top:16px"><span style="font-size:13px;font-weight:800;flex:1">Recent searches</span><span style="cursor:pointer" onclick="v4RecentClear()">🗑</span></div><div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px">' + rec.map(function(x){ return '<span class="v4-chip" style="cursor:pointer" data-q="' + v4Esc(x) + '" onclick="v4SuggPick(this)">' + v4Esc(x) + '</span>'; }).join('') + '</div>';
    }
    h += '<div style="font-size:13px;font-weight:800;margin-top:17px">Hot searches</div><div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px">' + V4_HOT.map(function(x){ return '<span class="v4-chip" style="cursor:pointer" data-q="' + v4Esc(x) + '" onclick="v4SuggPick(this)">' + v4Esc(x) + '</span>'; }).join('') + '</div>';
    box.innerHTML = h;
    return;
  }
  const rec = v4RecentGet().filter(function(x){ return x.toLowerCase().indexOf(q.toLowerCase()) >= 0; });
  box.innerHTML = rec.map(function(x){ return '<div class="v4-sugrow" data-q="' + v4Esc(x) + '"><span class="ic">🕐</span><span style="flex:1" onclick="v4SuggPick(this.parentNode)">' + v4SuggHi(x, q) + '</span><span data-q="' + v4Esc(x) + '" onclick="v4RecentRemove(this.dataset.q)">✕</span></div>'; }).join('') + '<div id="v4-sugg-live"></div>';
  clearTimeout(v4SuggTimer);
  v4SuggTimer = setTimeout(async function(){
    const r = await v4Fetch('/api/suggest?q=' + encodeURIComponent(q));
    const live = v4$('v4-sugg-live'); if(!live) return;
    const list = (r.data && r.data.suggestions) || [];
    live.innerHTML = list.map(function(x){ return '<div class="v4-sugrow" data-q="' + v4Esc(x) + '" onclick="v4SuggPick(this)"><span class="ic">🔍</span><span style="flex:1">' + v4SuggHi(x, q) + '</span></div>'; }).join('');
  }, 220);
}
function v4SuggPick(el){ const q = el.getAttribute('data-q'); if(q) v4RunSearch(q); }
function v4SetSearchBoxes(q){ ['v4-q-home','v4-q-youtube','v4-q-music'].forEach(function(id){ const el = v4$(id); if(el) el.value = q; }); }
function v4RunSearch(q){
  q = (q || '').trim(); if(!q) return;
  v4RecentAdd(q);
  v4CloseSearch();
  v4Show('home');
  v4SearchState = {q:q, filter:'all', platform:'all'};
  v4RenderSearchBar();
  v4SetSearchBoxes(q);
  v4$('v4-home-heading').textContent = 'Results: ' + q;
  v4InterestAdd(q, 2);
  v4LoadFeed('v4-home-feed', q, 'all');
}
function v4RenderSearchBar(){
  const bar = v4$('v4-searchbar'); if(!bar) return;
  if(!v4SearchState.q){ bar.style.display = 'none'; bar.innerHTML = ''; return; }
  bar.style.display = '';
  const pf = v4SearchState.platform, f = v4SearchState.filter;
  const pb = function(id, label){ return '<button data-pf="' + id + '" class="' + (pf === id ? 'active' : '') + '" onclick="v4SearchPlatform(this)">' + label + '</button>'; };
  const fb = function(id, label){ return '<button data-f="' + id + '" class="' + (f === id ? 'active' : '') + '" onclick="v4SearchFilter(this)">' + label + '</button>'; };
  bar.innerHTML = '<div class="v4-sbar">' + pb('all', 'All') + pb('youtube', 'YouTube') + pb('instagram', 'Instagram') + pb('facebook', 'Facebook') + '</div>' +
    '<div class="v4-sbar">' + fb('all', 'Sab') + fb('date', '🆕 Nayi') + fb('long', '⏱ Lambi') + fb('shorts', '⚡ Shorts') + '</div>';
}
function v4SearchPlatform(el){
  const pf = el.getAttribute('data-pf'); v4SearchState.platform = pf; v4RenderSearchBar();
  if(pf === 'all' || pf === 'youtube'){ v4LoadFeed('v4-home-feed', v4SearchState.q, 'all'); return; }
  v4Show('social');
  const inp = v4$('v4-social-url'); if(inp){ inp.placeholder = (pf === 'instagram' ? 'Instagram' : 'Facebook') + ' ka link yahan paste karein...'; inp.focus(); }
}
function v4SearchFilter(el){
  const f = el.getAttribute('data-f'); v4SearchState.filter = f; v4RenderSearchBar();
  const q = v4SearchState.q;
  if(f === 'shorts'){ v4OpenShorts(q); return; }
  if(f === 'date'){ v4LoadFeed('v4-home-feed', q, 'all', '', {sort:'date'}); return; }
  if(f === 'long'){ v4LoadFeed('v4-home-feed', q, 'videos', '', {minDur:1200}); return; }
  v4LoadFeed('v4-home-feed', q, 'all');
}

/* ---------- social / more ---------- */
const V4_PLATFORMS = ['YouTube','Facebook','Instagram','TikTok','WhatsApp Status','Pinterest','Twitter / X','SnapChat','Threads','DailyMotion','SoundCloud','Vimeo','Reddit','LinkedIn','Twitch'];
function v4RenderPlats(){
  v4State.platsDone = 1;
  const h = V4_PLATFORMS.map(function(p){ return '<div class="v4-plat" data-p="' + p + '" onclick="v4PlatClick(this)">' + p + '<div class="v4-muted">Link paste karein</div></div>'; }).join('');
  v4$('v4-plat-list').innerHTML = h;
}
function v4PlatClick(el){ v4Show('social'); const inp = v4$('v4-social-url'); inp.placeholder = el.getAttribute('data-p') + ' ka link yahan paste karein...'; inp.focus(); }
function v4PlaylistCardHTML(it){
  const pid = (it.id && it.id.playlistId) || '';
  const sn = it.snippet || {};
  const thumb = it.thumb_video ? v4Img(it.thumb_video) : '<div style="width:100%;height:100%;background:linear-gradient(135deg,#7c5cff,#14b8a6)"></div>';
  return '<div class="v4-vcard"><div class="v4-thumb" data-pid="' + pid + '" data-title="' + v4Esc(sn.title || '') + '" onclick="v4OpenPlaylist(this.dataset.pid, this.dataset.title)">' + thumb + '<span class="v4-plbadge">📋 Playlist' + (it.video_count ? ' • ' + it.video_count + ' videos' : '') + '</span></div>' +
    '<div class="v4-vrow"><div class="v4-vtexts"><div class="v4-vtitle">' + v4Esc(sn.title || '') + '</div>' + (sn.channelTitle ? '<div class="v4-vmeta">' + v4Esc(sn.channelTitle) + '</div>' : '') + '</div></div></div>';
}
async function v4OpenPlaylist(pid, title){
  if(!pid) return;
  v4PrevView = v4State.view;
  v4Show('playlist');
  v4$('v4-playlist-title').textContent = title || 'Playlist';
  v4$('v4-playlist-count').textContent = '';
  const grid = v4$('v4-playlist-feed');
  grid.innerHTML = '<p class="v4-muted">Load ho raha hai...</p>';
  const r = await v4Fetch('/api/playlist?id=' + encodeURIComponent(pid));
  if(r.ok && r.data && r.data.items){
    if(r.data.title) v4$('v4-playlist-title').textContent = r.data.title;
    v4$('v4-playlist-count').textContent = (r.data.count || 0) + ' videos — kisi video par tap karke download karein';
    v4RenderCards('v4-playlist-feed', r.data.items);
  } else grid.innerHTML = '<p class="v4-muted">Playlist load nahi ho saki — dobara try karein.</p>';
}
function v4SetFilter(btn){
  const w = btn.getAttribute('data-w'), t = btn.getAttribute('data-t');
  document.querySelectorAll('.v4-fchip[data-w="' + w + '"]').forEach(function(b){ b.classList.toggle('on', b === btn); });
  /* Update 130: Videos option ke andar 'Trending Videos'
     NAHI — sirf 'Videos' (heading har chip ke naam par). */
  if(w === 'home'){ const hd = v4$('v4-home-heading'); if(hd){ const names = {all:'Trending Videos', videos:'Videos', playlists:'Playlists', dramas:'Dramas', movies:'Movies', kids:'Kids'}; hd.textContent = names[t] || 'Trending Videos'; } }
  const feedId = 'v4-' + w + '-feed';
  const st = v4FeedState[feedId];
  const q = (st && st.q) || (w === 'youtube' ? 'trending videos' : (w === 'music' ? 'trending songs' : 'trending'));
  if(t === 'shorts'){ const _dq = (q === 'trending' || q === 'trending videos' || q === 'trending songs') ? '' : q; v4OpenShorts(_dq); return; }
  const rows = {dramas: 'v4-sub-' + w, movies: 'v4-subm-' + w, kids: 'v4-subk-' + w};
  Object.keys(rows).forEach(function(k){ const r2 = v4$(rows[k]); if(r2) r2.style.display = (k === t) ? '' : 'none'; });
  if(rows[t]){
    let cur = 'all';
    const row = v4$(rows[t]);
    if(row){ const onB = row.querySelector('[data-s].on'); if(onB) cur = onB.getAttribute('data-s') || 'all'; }
    v4LoadFeed(feedId, q, t, cur);
  } else v4LoadFeed(feedId, q, t);
}
function v4SubGo(btn, type){
  const w = btn.getAttribute('data-w'), s = btn.getAttribute('data-s');
  btn.parentElement.querySelectorAll('[data-s]').forEach(function(b){ b.classList.toggle('on', b === btn); });
  const feedId = 'v4-' + w + '-feed';
  const st = v4FeedState[feedId];
  const q = (st && st.q) || (w === 'youtube' ? 'trending videos' : 'trending');
  v4LoadFeed(feedId, q, type, s);
}
function v4SetMovieSub(btn){ v4SubGo(btn, 'movies'); }
function v4SetKidsSub(btn){ v4SubGo(btn, 'kids'); }
function v4SetDramaSub(btn){
  const w = btn.getAttribute('data-w'), s = btn.getAttribute('data-s');
  document.querySelectorAll('.v4-dchip[data-w="' + w + '"]').forEach(function(b){ b.classList.toggle('on', b === btn); });
  const feedId = 'v4-' + w + '-feed';
  const st = v4FeedState[feedId];
  const q = (st && st.q) || (w === 'youtube' ? 'trending videos' : 'trending');
  v4LoadFeed(feedId, q, 'dramas', s);
}
function v4RenderDeals(deals){
  const box = v4$('v4-deals'); if(!box) return;
  if(!deals || !deals.length){ box.innerHTML = '<p class="v4-muted">Abhi koi deal nahi hai</p>'; return; }
  box.innerHTML = deals.map(function(d){
    return '<div class="v4-deal">' + (d.badge ? '<span class="bdg">' + v4Esc(d.badge) + '</span>' : '') +
      '<span class="em">' + v4Esc(d.emoji || '🛒') + '</span><div class="nm">' + v4Esc(d.name || '') + '</div>' +
      (d.old_price ? '<span class="old">Rs. ' + Number(d.old_price).toLocaleString('en-PK') + '</span>' : '') +
      '<span class="new">Rs. ' + Number(d.new_price || 0).toLocaleString('en-PK') + '</span>' +
      (d.link ? '<a class="buy" href="' + v4Esc(d.link) + '" target="_blank" rel="noopener">Buy</a>' : '') + '</div>';
  }).join('');
}
function v4RateShow(n){
  const box = v4$('v4-stars'); if(!box) return;
  const stars = box.children;
  for(let i = 0; i < stars.length; i++){ stars[i].className = (i < n) ? 'on' : ''; }
  if(n > 0){ const m = v4$('v4-rate-msg'); if(m) m.innerText = 'Shukriya! Aap ne ' + n + ' stars diye ❤'; }
}
function v4Rate(n){
  try{ localStorage.setItem('pt_rating', String(n)); }catch(e){}
  v4RateShow(n);
}
function v4SocialPlatformName(url){
  const u = String(url || '').toLowerCase();
  const map = {'instagram.com':'Instagram','facebook.com':'Facebook','fb.watch':'Facebook','tiktok.com':'TikTok','twitter.com':'Twitter/X','x.com':'Twitter/X','youtube.com':'YouTube','youtu.be':'YouTube','snapchat.com':'SnapChat','pinterest.com':'Pinterest','threads.net':'Threads','dailymotion.com':'DailyMotion','vimeo.com':'Vimeo','soundcloud.com':'SoundCloud','reddit.com':'Reddit','linkedin.com':'LinkedIn','twitch.tv':'Twitch'};
  for(const k in map){ if(u.indexOf(k) >= 0) return map[k]; }
  return 'Social';
}
let v4SocialPhone = null;
async function v4SocialFetch(e){
  if(e) e.preventDefault();
  const url = v4$('v4-social-url').value.trim();
  const box = v4$('v4-social-result');
  if(!url){ v4Toast('Pehle link paste karein'); return; }
  /* Update 136: download card FORAN khulta hai — info
     peeche aati rehti hai, page pehle khul jata hai. */
  box.innerHTML = '<div class="v4-dlrow"><span style="width:64px;text-align:center;font-size:22px">🔗</span><div class="tt"><div class="t1">' + v4Esc(v4SocialPlatformName(url)) + ' video</div><div class="t2">Info aa rahi hai...</div></div></div>';
  v4SocialInfo = {url:url, info:null};
  const r = await v4Post('/api/fetch-social-info', {url:url});
  if(!r.ok || !r.data || !r.data.info){
    const srvErr = (r.data && r.data.error) || '';
    /* Phone wala rasta: app ke apne net se page ki info —
       server IP par lage blocks yahan nahi lagte. */
    if(window.PlayTubeApp && PlayTubeApp.socialPageInfo){
      window._v4SocialWait = {url:url, srvErr:srvErr};
      try{ PlayTubeApp.socialPageInfo(url); }catch(e2){ window._v4SocialWait = null; }
      if(window._v4SocialWait){
        box.innerHTML = '<div class="v4-dlrow"><span style="width:64px;text-align:center;font-size:22px">📱</span><div class="tt"><div class="t1">' + v4Esc(v4SocialPlatformName(url)) + ' video</div><div class="t2">Phone se info aa rahi hai...</div></div></div>';
        return;
      }
    }
    box.innerHTML = '<p class="v4-muted">' + v4Esc(srvErr || 'Info nahi mil saki') + '</p>';
    return;
  }
  v4SocialInfo = {url:url, info:r.data.info};
  const inf = r.data.info;
  box.innerHTML = '<div class="v4-dlrow"><img src="' + v4Esc(inf.thumbnail || '') + '" onerror="this.style.opacity=0.25"><div class="tt"><div class="t1">' + v4Esc(inf.title || '') + '</div><div class="t2">' + v4Esc(inf.platform || '') + ' • ' + v4Esc(inf.uploader || '') + '</div></div></div>' +
    '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="v4-bigbtn" style="margin-top:4px" data-f="video" onclick="v4SocialDownload(this.dataset.f)">⬇ Video Download</button><button class="v4-bigbtn" style="margin-top:4px;background:var(--v4card);border:1px solid var(--v4border)" data-f="audio" onclick="v4SocialDownload(this.dataset.f)">🎵 Audio (MP3)</button>' + ((inf.is_image || (inf.ext && ['jpg','jpeg','png','webp'].indexOf(String(inf.ext).toLowerCase()) >= 0)) ? '<button class="v4-bigbtn" style="margin-top:4px;background:var(--v4card);border:1px solid var(--v4border)" data-f="image" onclick="v4SocialDownload(this.dataset.f)">🖼 Picture</button>' : '') + '</div>';
}
function v4SocialPhoneResult(jsonStr){
  const w = window._v4SocialWait; window._v4SocialWait = null;
  const box = v4$('v4-social-result'); if(!box || !w) return;
  let d = null; try{ d = jsonStr ? JSON.parse(jsonStr) : null; }catch(e){}
  if(!d || !d.video){
    box.innerHTML = '<p class="v4-muted">' + v4Esc(w.srvErr || 'Is link se video nahi mil saki — video private ho sakti hai ya platform login maang raha ho ga') + '</p>';
    return;
  }
  v4SocialPhone = {url:w.url, video:d.video, title:d.title || ''};
  box.innerHTML = '<div class="v4-dlrow">' + (d.thumb ? '<img src="' + v4Esc(d.thumb) + '" onerror="this.style.opacity=0.25">' : '<span style="width:64px;text-align:center;font-size:22px">🎬</span>') + '<div class="tt"><div class="t1">' + v4Esc(d.title || 'Video') + '</div><div class="t2">' + v4Esc(v4SocialPlatformName(w.url)) + ' • Phone se mili</div></div></div>' +
    '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="v4-bigbtn" style="margin-top:4px" onclick="v4SocialPhoneDl()">⬇ Video Download</button></div>';
}
function v4SocialPhoneDl(){
  if(!v4SocialPhone) return;
  if(!v4GuestGate()){ v4OpenAuth('signin', false, 'limit'); v4Toast('Guest limit khatam — pehle account banayein'); return; }
  let t = (v4SocialPhone.title || 'video').replace(/[\/:*?"<>|]/g, ' ').trim().slice(0, 80);
  if(!t) t = 'playza_video';
  try{ PlayTubeApp.saveNamed(v4SocialPhone.video, t + '.mp4'); v4Toast('Download shuru ho gaya — Downloads me dekhein'); }
  catch(e){ v4Toast('Download shuru nahi ho saka'); }
}
async function v4SocialDownload(fmt){
  if(!v4SocialInfo) return;
  const r = await v4Post('/api/download-social', {url:v4SocialInfo.url, format:fmt, direct_url:(v4SocialInfo.info && v4SocialInfo.info.direct_url) || '', title:(v4SocialInfo.info && v4SocialInfo.info.title) || ''});
  if(r.ok && r.data && r.data.success){ v4Toast('Download shuru ho gaya — Downloads me dekhein'); v4LoadDownloads(); return; }
  const d = r.data || {};
  if(d.login_required){ v4Pending = {type:'social', url:v4SocialInfo.url, format:fmt}; v4OpenAuth('signin', false, d.guest_limit ? 'limit' : ''); return; }
  v4Toast(v4FriendlyErr(d.error) || 'Download start nahi ho saka');
}

/* ---------- tools / settings ---------- */
function v4DlPathLabel(){ const el = v4$('v4-set-dlpath'); if(el && window.PlayTubeApp && window.PlayTubeApp.getDownloadFolderLabel) el.textContent = window.PlayTubeApp.getDownloadFolderLabel(); }
function v4PickFolder(){ if(window.PlayTubeApp && window.PlayTubeApp.pickFolder){ window.PlayTubeApp.pickFolder(); setTimeout(v4DlPathLabel, 1000); setTimeout(v4DlPathLabel, 2500); } }
function v4ShareApp(){
  const url = window.location.origin + '/';
  if(navigator.share){ navigator.share({title:'Playza', text:'Playza — All in One Downloader', url:url}).catch(function(){}); }
  else if(navigator.clipboard){ navigator.clipboard.writeText(url); v4Toast('App ka link copy ho gaya'); }
  else v4Toast(url);
}
function v4SwitchUI(id, on){ const el = v4$(id); if(el) el.classList.toggle('on', !!on); }
function v4FillSettings(){
  const s = v4State.settings;
  v4$('v4-set-folder').value = s.folder;
  v4$('v4-set-quality').value = s.defQuality;
  v4$('v4-set-conc').value = String(s.maxConc);
  v4$('v4-set-speed').value = s.speed;
  v4SwitchUI('v4-set-wifi', s.wifiOnly);
  v4SwitchUI('v4-set-notify', s.notify);
  v4SwitchUI('v4-set-bgdl', s.bgDl !== false);
  v4SwitchUI('v4-set-mini', s.autoMini !== false);
  const fr = v4$('v4-set-floating-row');
  if(fr && window.PlayTubeApp){
    fr.style.display = 'flex';
    const masterOff = v4State.config && v4State.config.toggles && v4State.config.toggles.floating_enabled === false;
    const sw = v4$('v4-set-floating');
    if(masterOff){
      sw.style.opacity = '0.45'; sw.style.pointerEvents = 'none';
      const nt = v4$('v4-set-floating-note'); if(nt) nt.textContent = 'Admin ne Floating Button band kiya hai';
      v4SwitchUI('v4-set-floating', false);
    } else {
      sw.style.opacity = ''; sw.style.pointerEvents = '';
      v4SwitchUI('v4-set-floating', !!window.PlayTubeApp.isFloatingEnabled());
    }
  }
  v4$('v4-set-lang').textContent = (localStorage.getItem('pt_lang') === 'ur') ? 'اردو' : 'English';
  v4$('v4-set-theme').textContent = (document.documentElement.getAttribute('data-theme') === 'light') ? 'Light' : 'Dark';
}
function v4ToggleSetting(key, el){ v4State.settings[key] = !v4State.settings[key]; el.classList.toggle('on', v4State.settings[key]); v4SaveSettings(true); if(key === 'bgDl') v4PhoneSyncBg(); }
function v4PhoneSyncBg(){ try{ if(window.PlayTubeApp && PlayTubeApp.phoneSetBgDl) PlayTubeApp.phoneSetBgDl(v4State.settings.bgDl !== false); }catch(e){} }
function v4SaveSettings(silent){
  const s = v4State.settings;
  const f = v4$('v4-set-folder'); if(f) s.folder = f.value || 'Playza';
  const q = v4$('v4-set-quality'); if(q) s.defQuality = q.value;
  const c = v4$('v4-set-conc'); if(c) s.maxConc = parseInt(c.value);
  const sp = v4$('v4-set-speed'); if(sp) s.speed = sp.value;
  try{ localStorage.setItem('pt_v4_settings', JSON.stringify(s)); }catch(e){}
  if(!silent) v4Toast('Settings save ho gayi');
}
function v4SyncThemeBtn(){
  const b = v4$('v4-themebtn'); if(b) b.textContent = (document.documentElement.getAttribute('data-theme') === 'light') ? '🌙 Dark' : '☀️ Light';
  const lb = v4$('v4-langbtn'); if(lb) lb.textContent = (localStorage.getItem('pt_lang') === 'ur') ? 'English' : 'اردو';
}
function v4ToggleTheme(){
  if(typeof toggleTheme === 'function') toggleTheme();
  else { const cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light'; document.documentElement.setAttribute('data-theme', cur); try{ localStorage.setItem('pt_theme', cur); }catch(e){} }
  v4SyncThemeBtn();
  if(v4State.view === 'settings') v4FillSettings();
}
function v4ToggleLang(){
  if(typeof toggleLang === 'function') toggleLang();
  else { const cur = localStorage.getItem('pt_lang') === 'ur' ? 'en' : 'ur'; try{ localStorage.setItem('pt_lang', cur); }catch(e){} }
  v4SyncThemeBtn();
  if(v4State.view === 'settings') v4FillSettings();
}

/* ---------- floating button bridge (Update 26/27, sirf APK) ---------- */
function v4ToggleFloating(el){
  if(!window.PlayTubeApp) return;
  if(v4State.config && v4State.config.toggles && v4State.config.toggles.floating_enabled === false){ v4Toast('Admin ne Floating Button band kiya hai'); return; }
  const on = !window.PlayTubeApp.isFloatingEnabled();
  window.PlayTubeApp.setFloatingEnabled(on);
  v4Toast(on ? 'Floating button ON - pehli dafa overlay permission dena hoga' : 'Floating button OFF');
  setTimeout(function(){ v4SwitchUI('v4-set-floating', !!(window.PlayTubeApp && window.PlayTubeApp.isFloatingEnabled())); }, 700);
}

/* ---------- favorites / history ---------- */
function v4RenderFavs(){
  let favs = []; try{ favs = JSON.parse(localStorage.getItem('pt_favs') || '[]'); }catch(e){}
  const el = v4$('v4-fav-list');
  if(!favs.length){ el.innerHTML = '<p class="v4-muted">Abhi koi favorite nahi</p>'; return; }
  el.innerHTML = favs.map(function(f){ const v = {videoId:f.id, title:f.title || '', channel:f.channel || ''}; if(v.videoId) v4Videos[v.videoId] = v; return v.videoId ? v4CardHTML(v) : ''; }).join('');
}
async function v4LoadHistory(){
  const el = v4$('v4-history-list');
  const r = await v4Fetch('/api/history');
  const items = (r.ok && r.data) ? (r.data.history || []) : [];
  if(!items.length){ el.innerHTML = '<p class="v4-muted">Abhi koi history nahi — video dekhein to yahan aayegi.</p>'; return; }
  el.innerHTML = items.map(function(h){ const v = {videoId:h.video_id, title:h.title || '', channel:h.channel || ''}; if(v.videoId) v4Videos[v.videoId] = v; return v.videoId ? v4CardHTML(v) : ''; }).join('');
}
async function v4ClearHistory(){ await v4Fetch('/api/clear-history', {method:'DELETE'}); v4LoadHistory(); }

/* ---------- profile ---------- */
async function v4RenderProfile(){
  const body = v4$('v4-profile-body'); if(!body) return;
  const r = await v4Fetch('/api/user-info');
  v4State.user = (r.ok && r.data) ? r.data.user : null;
  const adm = await v4Fetch('/api/admin/session');
  const isAdmin = !!(adm.ok && adm.data && adm.data.admin);
  const adminRow = '<div class="v4-row" data-view="admin" onclick="v4Show(this.dataset.view)"><span>🛠️</span><div class="grow">' + (isAdmin ? 'Admin Panel' : 'Admin Login (Owner)') + '</div>' + (isAdmin ? '<span class="v4-badge2 owner">ON</span>' : '') + '<span>›</span></div>';
  if(!v4State.user){
    body.innerHTML = '<div style="text-align:center;padding:14px 0"><div style="font-size:44px">👤</div><div class="v4-h">Guest</div><p class="v4-muted">Video dekhne aur download karne ke liye login lazmi hai.</p>' +
      '<button class="v4-bigbtn" data-tab="signin" onclick="v4OpenAuth(this.dataset.tab)">Sign In</button>' +
      '<button class="v4-bigbtn" style="background:var(--v4card);border:1px solid var(--v4border)" data-tab="signup" onclick="v4OpenAuth(this.dataset.tab)">Create Account</button></div>' + adminRow;
    return;
  }
  const u = v4State.user;
  const pr = await v4Fetch('/api/premium/status');
  const isPrem = !!(pr.ok && pr.data && pr.data.is_premium);
  const isOwner = (u.email === 'chuzajani1@gmail.com');
  const badge = isOwner ? '<span class="v4-badge2 owner">Owner</span>' : (isPrem ? '<span class="v4-badge2 prem">Premium</span>' : '<span class="v4-badge2">Free Account</span>');
  let h = '<div style="display:flex;align-items:center;gap:12px;margin:10px 0 6px"><div style="width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,var(--v4violet),var(--v4teal));display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:#fff;flex:none">' + v4Esc((u.username || 'U').charAt(0).toUpperCase()) + '</div><div><div style="font-size:15px;font-weight:700">' + v4Esc(u.username) + '</div><div class="v4-muted">' + v4Esc(u.email) + '</div><div style="margin-top:4px">' + badge + '</div></div></div>';
  if(!isOwner && !isPrem && (!v4State.config || !v4State.config.toggles || v4State.config.toggles.premium_enabled !== false))
    h += '<div class="v4-row" data-view="premium" onclick="v4Show(this.dataset.view)"><span>👑</span><div class="grow">Premium lein</div><span>›</span></div>';
  h += adminRow;
  h += '<div class="v4-row" data-view="downloads" onclick="v4Show(this.dataset.view)"><span>⬇️</span><div class="grow">Mere Downloads</div><span>›</span></div>';
  h += '<div class="v4-row" data-view="favorites" onclick="v4Show(this.dataset.view)"><span>⭐</span><div class="grow">Favorites</div><span>›</span></div>';
  h += '<div class="v4-row" onclick="v4OpenAuthForgot()"><span>🔒</span><div class="grow">Password badlein</div><span>›</span></div>';
  h += '<div class="v4-row" onclick="v4Logout()"><span>🚪</span><div class="grow" style="color:var(--v4danger)">Logout</div></div>';
  body.innerHTML = h;
}
async function v4Logout(){ await v4Post('/api/logout', {}); v4State.user = null; v4Toast('Logout ho gaya'); v4RenderProfile(); }

/* ---------- admin panel ---------- */
async function v4RenderAdmin(){
  const body = v4$('v4-admin-body'); if(!body) return;
  const s = await v4Fetch('/api/admin/session');
  if(!(s.ok && s.data && s.data.admin)){
    body.innerHTML = '<p class="v4-muted">Ye sirf website ke owner ke liye hai. Admin key darj karein:</p><input class="v4-input" id="v4-admin-key" type="password" placeholder="Admin key"><button class="v4-bigbtn" onclick="v4AdminLogin()">Admin Login</button>';
    return;
  }
  const res = await Promise.all([v4Fetch('/api/admin/v4-settings'), v4Fetch('/api/admin/v4-stats'), v4Fetch('/api/admin/v4-users'), v4Fetch('/api/admin/pending-payments-list')]);
  const cfg = res[0].data || {}, t = cfg.toggles || {}, ss = res[1].data || {};
  const tog = function(key, label){ return '<div class="v4-row"><div class="grow">' + label + '</div><button class="v4-switch' + (t[key] ? ' on' : '') + '" data-key="' + key + '" onclick="v4AdminToggle(this)"><i></i></button></div>'; };
  let h = '<div class="v4-stats"><div class="v4-stat"><b>' + (ss.total_users || 0) + '</b><span>Total Users</span></div><div class="v4-stat"><b>' + (ss.downloads_today || 0) + '</b><span>Aaj ke Downloads</span></div><div class="v4-stat"><b>' + (ss.pending_premium_requests || 0) + '</b><span>Premium Requests</span></div></div>';
  h += '<div class="v4-stats"><div class="v4-stat"><b>' + (ss.total_visits || 0) + '</b><span>Total Visits</span></div><div class="v4-stat"><b>' + (ss.today_visits || 0) + '</b><span>Aaj ke Visits</span></div><div class="v4-stat"><b>' + (ss.today_unique || 0) + '</b><span>Aaj ke Visitors (alag log)</span></div></div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">💾 STORAGE (SERVER)</div><div id="v4-storage-box" class="v4-muted">Loading...</div></div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">🍪 YOUTUBE COOKIES</div><div id="v4-cookies-box" class="v4-muted">Loading...</div></div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">WEBSITE ON / OFF</div>';
  h += tog('ai_enabled', 'AI Assistant') + tog('downloads_enabled', 'Downloads') + tog('premium_enabled', 'Premium System') + tog('social_enabled', 'Social Tab') + tog('shorts_enabled', 'Shorts') + tog('music_enabled', 'Music Tab') + tog('signup_enabled', 'Naya Signup (registration)') + tog('floating_enabled', 'Floating Button (APK)') + tog('maintenance_mode', 'Maintenance (site band)') + '</div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">ELAAN (ANNOUNCEMENT)</div><input class="v4-input" id="v4-adm-ann" placeholder="Home par sab ko dikhne wala message" value="' + v4Esc(cfg.announcement || '') + '"><button class="v4-btn2" onclick="v4AdminSaveAnn()">Save Elaan</button></div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">MAINTENANCE MESSAGE</div><input class="v4-input" id="v4-adm-maintmsg" placeholder="Maintenance on ho to ye message dikhe ga" value="' + v4Esc(cfg.maintenance_message || '') + '"><button class="v4-btn2" onclick="v4AdminSaveMaintMsg()">Message Save karein</button></div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">DOWNLOADS SETTING</div>';
  h += tog('hd_premium_only', 'HD (720p+) sirf Premium ke liye') + '<div class="v4-muted">Ye off karein to HD quality sab ke liye free ho jayegi</div>';
  h += tog('guest_downloads_enabled', 'Guest downloads (bina account)') + '<div class="v4-muted">Off karein to bina account download bilkul band ho jayega — guest limit se alag ye master switch hai (website + APK dono par)</div>';
  h += tog('storage_autoclean', 'Storage auto-safai') + '<div class="v4-muted">On ho to server ki jagah 80% bharne par purani downloads khud saaf hoti hain (40% tak) — storage kabhi full nahi hota</div>';
  h += '<div class="v4-row" style="margin-top:10px"><div class="grow">Guest free downloads (bina account)<div class="v4-muted">0 likhein to guest download band — sab ko account banana pare ga</div></div><input class="v4-input" style="width:110px;margin:0" id="v4-adm-guest-limit" type="number" min="0" max="1000" value="' + (cfg.guest_download_limit != null ? cfg.guest_download_limit : 10) + '"></div><button class="v4-btn2" onclick="v4AdminSaveGuestLimit()">Guest Limit Save karein</button></div>';
  const pr = cfg.prices || {};
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">PREMIUM PRICES (Rs)</div>';
  h += '<div class="v4-row"><div class="grow">Weekly</div><input class="v4-input" style="width:110px;margin:0" id="v4-pr-weekly" type="number" value="' + (pr.weekly || 200) + '"></div>';
  h += '<div class="v4-row"><div class="grow">Monthly</div><input class="v4-input" style="width:110px;margin:0" id="v4-pr-monthly" type="number" value="' + (pr.monthly || 500) + '"></div>';
  h += '<div class="v4-row"><div class="grow">Yearly</div><input class="v4-input" style="width:110px;margin:0" id="v4-pr-yearly" type="number" value="' + (pr.yearly || 3000) + '"></div>';
  h += '<button class="v4-btn2" onclick="v4AdminSavePrices()" style="margin-top:8px">Prices Save karein</button></div>';
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">PAYMENT NUMBERS</div>';
  const pa = cfg.payment_accounts || {};
  ['jazzcash','easypaisa'].forEach(function(m){
    const a = pa[m] || {};
    h += '<div class="v4-row"><div class="grow" style="text-transform:capitalize">' + m + '<div class="v4-muted">Khaali chhor dein to remove ho jayega</div></div></div>' +
      '<input class="v4-input" id="v4-pa-' + m + '-num" placeholder="Account number" value="' + v4Esc(a.account_number || '') + '">' +
      '<input class="v4-input" id="v4-pa-' + m + '-title" placeholder="Account title" value="' + v4Esc(a.account_title || '') + '">' +
      '<button class="v4-btn2" data-m="' + m + '" onclick="v4AdminSaveAccount(this.dataset.m)">Save ' + m + '</button>';
  });
  h += '</div>';
  const plist = (res[3].data && res[3].data.payments) || [];
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">PREMIUM REQUESTS</div>';
  if(!plist.length) h += '<p class="v4-muted">Koi pending request nahi</p>';
  plist.forEach(function(p){
    h += '<div class="v4-dlrow"><div class="tt"><div class="t1">' + v4Esc(p.username || '') + ' — ' + v4Esc(p.plan_type || '') + ' (Rs ' + v4Esc(p.amount_pkr || '') + ')</div><div class="t2">' + v4Esc(p.payment_method || '') + ' • Txn: ' + v4Esc(p.transaction_id || '') + '</div></div>' +
      '<button class="v4-roundbtn teal" title="Approve" data-pid="' + p.id + '" data-ap="1" onclick="v4AdminPay(this)">✓</button>' +
      '<button class="v4-roundbtn" title="Reject" data-pid="' + p.id + '" data-ap="0" onclick="v4AdminPay(this)">✕</button></div>';
  });
  h += '</div>';
  const ulist = (res[2].data && res[2].data.users) || [];
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">USERS</div>';
  ulist.forEach(function(u){
    h += '<div class="v4-row"><div class="grow">' + v4Esc(u.username) + ' <span class="v4-muted">' + v4Esc(u.email) + '</span><div class="v4-muted">Join: ' + v4Esc((u.created_at || '').slice(0, 10)) + ' • ID ' + u.id + '</div></div>' +
      (u.is_owner ? '<span class="v4-badge2 owner">Owner</span>'
        : (u.is_premium ? '<span class="v4-badge2 prem">Premium</span><button class="v4-btn2" data-uid="' + u.id + '" data-grant="0" onclick="v4AdminUserPrem(this)">Band karein</button>'
                       : '<button class="v4-btn2" data-uid="' + u.id + '" data-grant="1" onclick="v4AdminUserPrem(this)">Premium dein</button>')) + '</div>';
  });
  h += '</div>';
  /* Update 122: Hot Deals KHATAM (user 2026-11-27) — admin card bhi hata diya. */
  h += '<div class="v4-admincard"><div class="v4-sect" style="margin-top:0">PRIVATE FOLDER</div><div class="v4-row"><div class="grow">PIN ki halat<div class="v4-muted">' + (cfg.pin_set ? 'PIN set hai' : 'Abhi PIN set nahi hai') + '</div></div>' + (cfg.pin_set ? '<button class="v4-btn2" onclick="v4AdminResetPin()">PIN Reset karein</button>' : '') + '</div><div class="v4-muted">PIN bhool jayein to yahan se reset karein — phir naya PIN banana pare ga.</div></div>';
  h += '<button class="v4-bigbtn" style="background:var(--v4card);border:1px solid var(--v4border)" onclick="v4AdminLogout()">Admin Logout</button>';
  body.innerHTML = h;
  v4LoadStorage(); v4LoadCookies();
}
async function v4LoadStorage(){ const box = v4$('v4-storage-box'); if(!box) return; const r = await v4Fetch('/api/admin/storage'); if(!r.ok || !r.data){ box.textContent = 'Storage ki maloomat nahi mil sakin'; return; } const d = r.data; const pct = Math.min(100, d.used_pct || 0); const col = pct >= 80 ? '#f87171' : (pct >= 60 ? '#fbbf24' : '#14b8a6'); let h = '<div class="v4-row"><div class="grow">Istemaal shuda jagah</div><b>' + d.used_mb + ' / ' + d.total_mb + ' MB (' + pct + '%)</b></div>'; h += '<div style="height:10px;border-radius:99px;background:var(--v4border);overflow:hidden;margin:6px 0"><div style="height:100%;width:' + pct + '%;background:' + col + '"></div></div>'; h += '<div class="v4-muted">Khaali jagah: ' + d.free_mb + ' MB - Downloads folder: ' + (d.disk_files || 0) + ' files (' + (d.disk_downloads_mb != null ? d.disk_downloads_mb : d.downloads_mb) + ' MB)</div>'; if(d.breakdown && d.breakdown.length){ h += '<div class="v4-muted" style="margin-top:4px">Volume par hai kya:<br>' + d.breakdown.map(function(b){ return '• ' + b.name + ': ' + b.mb + ' MB'; }).join('<br>') + '</div>'; } h += '<div class="v4-muted" style="margin-top:4px">Auto rule: jagah 80% bharne par sab se purani downloads khud delete hoti hain jab tak 40% na reh jaye (Private folder wali kabhi nahi) — storage kabhi full nahi hota.</div>'; h += '<button class="v4-btn2" style="margin-top:8px" onclick="v4AdminCleanup()">Abhi safai karein</button>'; box.innerHTML = h; }
async function v4LoadCookies(){ const box = v4$('v4-cookies-box'); if(!box) return; const r = await v4Fetch('/api/admin/cookies-status'); const on = r.ok && r.data && r.data.active; box.innerHTML = '<div class="v4-muted">' + (on ? '✅ Cookies lagi hui hain' + (r.data.size_kb ? ' (' + r.data.size_kb + ' KB)' : '') + ' — downloads mazboot hain, bot-check wala issue nahi ayega.' : '⚠ Cookies nahi lagin — YouTube kabhi kabhi server ko rok deta hai (bot-check), tab downloads fail hoti hain. Spare Google account ki cookies.txt yahan lagayein to ye rukawat khatam ho jayegi.') + '</div><label class="v4-btn2" style="display:inline-block;margin-top:8px;cursor:pointer">🍪 Cookies file chunein<input type="file" accept=".txt" style="display:none" onchange="v4AdminCookiesUpload(this)"></label>'; }
async function v4AdminCookiesUpload(inp){ const f = inp.files && inp.files[0]; if(!f) return; const fd = new FormData(); fd.append('file', f); v4Toast('Cookies lag rahi hain...'); try{ const r = await fetch('/api/admin/cookies', {method:'POST', body:fd}); const d = await r.json(); if(d && d.success){ v4Toast('✅ Cookies lag gayin'); v4LoadCookies(); } else v4Toast((d && d.error) || 'Cookies nahi lag sakin'); }catch(e){ v4Toast('Upload fail ho gaya'); } }
async function v4AdminCleanup(){ const r = await v4Post('/api/admin/storage-cleanup', {}); if(r.ok && r.data){ if(r.data.removed) v4Toast(r.data.removed + ' files delete — ' + r.data.freed_mb + ' MB khaali; ab sirf website ka apna data bacha hai'); else v4Toast('Sab pehle se saaf hai — saaf karne ko kuch nahi bacha'); v4LoadStorage(); } else v4Toast('Safai nahi ho saki'); }
function v4DealRowDel(btn){ const r = btn.closest('.v4-dealrow'); if(r) r.remove(); }
function v4DealRow(d){
  d = d || {};
  return '<div class="v4-dealrow" style="border:1px solid var(--v4border);border-radius:12px;padding:10px;margin-bottom:8px">' +
    '<div style="display:flex;gap:6px"><input class="v4-input dl-em" style="width:56px;margin:0" placeholder="🛒" value="' + v4Esc(d.emoji || '') + '"><input class="v4-input dl-nm" style="flex:1;margin:0" placeholder="Product ka naam" value="' + v4Esc(d.name || '') + '"><button class="v4-btn2" onclick="v4DealRowDel(this)">✕</button></div>' +
    '<div style="display:flex;gap:6px;margin-top:6px"><input class="v4-input dl-old" type="number" style="flex:1;margin:0" placeholder="Purani price" value="' + (d.old_price || '') + '"><input class="v4-input dl-new" type="number" style="flex:1;margin:0" placeholder="Nayi price" value="' + (d.new_price || '') + '"><input class="v4-input dl-bdg" style="width:76px;margin:0" placeholder="Badge %" value="' + v4Esc(d.badge || '') + '"></div>' +
    '<input class="v4-input dl-lnk" style="margin-top:6px" placeholder="Buy link (https://...)" value="' + v4Esc(d.link || '') + '"></div>';
}
function v4DealAdd(){ const box = v4$('v4-deals-edit'); if(box) box.insertAdjacentHTML('beforeend', v4DealRow({})); }
async function v4AdminSaveDeals(){
  const rows = document.querySelectorAll('#v4-deals-edit .v4-dealrow'); const deals = [];
  rows.forEach(function(r){
    const nm = r.querySelector('.dl-nm').value.trim(); if(!nm) return;
    deals.push({name: nm, emoji: r.querySelector('.dl-em').value.trim() || '🛒', old_price: parseInt(r.querySelector('.dl-old').value) || 0, new_price: parseInt(r.querySelector('.dl-new').value) || 0, badge: r.querySelector('.dl-bdg').value.trim(), link: r.querySelector('.dl-lnk').value.trim()});
  });
  const r = await v4Post('/api/admin/v4-settings', {deals: deals});
  if(r.ok){ v4Toast('Deals save ho gayi'); v4LoadConfig(); } else v4Toast('Save nahi ho saki');
}
async function v4AdminLogin(){ const key = v4$('v4-admin-key').value; const r = await v4Post('/api/admin/login', {key:key}); if(r.ok && r.data && r.data.success){ v4Toast('Admin login ho gaya'); v4RenderAdmin(); } else v4Toast('Galat admin key'); }
async function v4AdminLogout(){ await v4Post('/api/admin/logout', {}); v4RenderAdmin(); }
async function v4AdminToggle(el){ const key = el.getAttribute('data-key'); const on = !el.classList.contains('on'); el.classList.toggle('on', on); const body = {toggles:{}}; body.toggles[key] = on; const r = await v4Post('/api/admin/v4-settings', body); if(r.ok){ v4Toast('Setting save ho gayi'); v4LoadConfig(); } else { el.classList.toggle('on', !on); v4Toast('Save nahi ho saki'); } }
async function v4AdminSaveAnn(){ const r = await v4Post('/api/admin/v4-settings', {announcement: v4$('v4-adm-ann').value}); if(r.ok){ v4Toast('Elaan save ho gaya'); v4LoadConfig(); } }
async function v4AdminSaveMaintMsg(){ const r = await v4Post('/api/admin/v4-settings', {maintenance_message: v4$('v4-adm-maintmsg').value}); if(r.ok) v4Toast('Maintenance message save ho gaya'); else v4Toast('Save nahi ho saka'); }
async function v4AdminResetPin(){ if(!confirm('Private Folder ka PIN reset kar dein? Phir naya PIN banana pare ga.')) return; const r = await v4Post('/api/admin/v4-settings', {reset_private_pin: true}); if(r.ok){ v4Toast('PIN reset ho gaya'); v4RenderAdmin(); } else v4Toast('Reset nahi ho saka'); }
async function v4AdminSaveGuestLimit(){ const n = parseInt(v4$('v4-adm-guest-limit').value, 10); if(isNaN(n) || n < 0){ v4Toast('Sahi number likhein (0 ya zyada)'); return; } const r = await v4Post('/api/admin/v4-settings', {guest_download_limit: n}); if(r.ok){ v4Toast('Guest limit save ho gayi: ' + n + ' free downloads'); v4LoadConfig(); } else v4Toast('Save nahi ho saki'); }
async function v4AdminSavePrices(){ const p = {weekly: parseInt(v4$('v4-pr-weekly').value), monthly: parseInt(v4$('v4-pr-monthly').value), yearly: parseInt(v4$('v4-pr-yearly').value)}; const r = await v4Post('/api/admin/v4-settings', {prices:p}); if(r.ok) v4Toast('Prices save ho gayi'); }
async function v4AdminSaveAccount(m){ const body = {payment_accounts:{}}; body.payment_accounts[m] = {account_number: v4$('v4-pa-' + m + '-num').value, account_title: v4$('v4-pa-' + m + '-title').value}; const r = await v4Post('/api/admin/v4-settings', body); if(r.ok) v4Toast(m + ' account save ho gaya'); }
async function v4AdminPay(el){ const id = el.getAttribute('data-pid'); const approve = el.getAttribute('data-ap') === '1'; const r = await v4Post('/api/admin/' + (approve ? 'approve' : 'reject') + '-payment/' + id, {}); if(r.ok){ v4Toast(approve ? 'Premium approve ho gaya' : 'Request reject ho gayi'); v4RenderAdmin(); } else v4Toast('Action nahi ho saka'); }
async function v4AdminUserPrem(el){ const uid = el.getAttribute('data-uid'); const grant = el.getAttribute('data-grant') === '1'; const r = await v4Post('/api/admin/v4-users/' + uid + '/premium', {grant:grant}); if(r.ok){ v4Toast(grant ? 'Premium de diya gaya' : 'Premium band kar diya'); v4RenderAdmin(); } }

/* ---------- premium view ---------- */
async function v4RenderPremium(){
  const body = v4$('v4-premium-body'); if(!body) return;
  if(v4State.config && v4State.config.toggles && v4State.config.toggles.premium_enabled === false){ body.innerHTML = '<p class="v4-muted">Premium abhi band hai.</p>'; return; }
  const res = await Promise.all([v4Fetch('/api/premium/plans'), v4Fetch('/api/premium/status')]);
  const plans = (res[0].data && res[0].data.plans) || {};
  const pays = (res[0].data && res[0].data.payments) || {};
  let h = '';
  if(res[1].data && res[1].data.is_premium) h += '<p class="v4-msg ok" style="display:block">Aap Premium hain — Plan: ' + v4Esc(res[1].data.plan || '') + ' • Expiry: ' + v4Esc(res[1].data.expiry || '') + '</p>';
  h += '<div class="v4-stats">';
  ['weekly','monthly','yearly'].forEach(function(k){ const p = plans[k]; if(p) h += '<div class="v4-stat"><b>Rs ' + p.price + '</b><span>' + v4Esc(p.name) + ' (' + p.days + ' din)</span></div>'; });
  h += '</div>';
  const methods = Object.keys(pays);
  if(!v4State.user){ h += '<p class="v4-muted">Premium lene ke liye pehle sign in karein.</p><button class="v4-bigbtn" data-tab="signin" onclick="v4OpenAuth(this.dataset.tab)">Sign In</button>'; body.innerHTML = h; return; }
  if(!methods.length){ h += '<p class="v4-muted">Abhi koi payment account add nahi hai — admin se rabta karein.</p>'; body.innerHTML = h; return; }
  h += '<div class="v4-sect">PAYMENT SUBMIT KAREIN</div>';
  h += '<select class="v4-input" id="v4-pm-plan">' + ['weekly','monthly','yearly'].map(function(k){ return plans[k] ? '<option value="' + k + '">' + v4Esc(plans[k].name) + ' — Rs ' + plans[k].price + '</option>' : ''; }).join('') + '</select>';
  h += '<select class="v4-input" id="v4-pm-method">' + methods.map(function(m){ return '<option value="' + m + '">' + v4Esc(pays[m].name) + ' — ' + v4Esc(pays[m].account_number) + ' (' + v4Esc(pays[m].account_title) + ')</option>'; }).join('') + '</select>';
  h += '<input class="v4-input" id="v4-pm-sender" placeholder="Aap ka account number jis se bheja">';
  h += '<input class="v4-input" id="v4-pm-txn" placeholder="Transaction ID">';
  h += '<button class="v4-bigbtn" onclick="v4PremiumSubmit()">Submit karein</button>';
  body.innerHTML = h;
}
async function v4PremiumSubmit(){
  const body = {plan_type: v4$('v4-pm-plan').value, payment_method: v4$('v4-pm-method').value, sender_account: v4$('v4-pm-sender').value, transaction_id: v4$('v4-pm-txn').value};
  const r = await v4Post('/api/premium/submit', body);
  if(r.ok && r.data && r.data.success) v4Toast('Payment submit ho gaya — verify hone par Premium active ho jayega');
  else v4Toast((r.data && r.data.error) || 'Submit nahi ho saka');
}

/* ---------- download app view ---------- */
async function v4CheckApk(){
  const area = v4$('v4-apk-area'); if(!area) return;
  const r = await v4Fetch('/api/apk-status');
  if(r.ok && r.data && r.data.available) area.innerHTML = '<a class="v4-bigbtn" style="background:var(--v4teal);color:#06231f;text-decoration:none" href="/playtube.apk">⬇ Download APK</a>';
  else area.innerHTML = '<p class="v4-muted">🚧 APK tayyar ho raha hai — filhal PWA install karein.</p>';
}
/* ---------- App install (v4 native — purana code delete) ---------- */
let v4InstallPrompt = null;
window.addEventListener('beforeinstallprompt', function(e){ e.preventDefault(); v4InstallPrompt = e; });
async function installPlayTubeApp(){
  if(v4InstallPrompt){ v4InstallPrompt.prompt(); const ch = await v4InstallPrompt.userChoice; v4Toast(ch.outcome === 'accepted' ? '📲 App install ho raha hai!' : 'Install cancel ho gaya'); v4InstallPrompt = null; }
  else window.location.href = '/playtube.apk';
}
async function installPlayTubeAppPC(){
  if(v4InstallPrompt){ v4InstallPrompt.prompt(); const ch = await v4InstallPrompt.userChoice; v4Toast(ch.outcome === 'accepted' ? '💻 Playza PC par install ho raha hai!' : 'Install cancel ho gaya'); v4InstallPrompt = null; }
  else v4Toast('Browser menu se "Install app" chunein');
}
function v4InstallPWA(){ if(typeof installPlayTubeApp === 'function') installPlayTubeApp(); else v4Toast('Browser menu se "Install app" / "Add to Home screen" chunein'); }
function v4InstallPC(){ if(typeof installPlayTubeAppPC === 'function') installPlayTubeAppPC(); else if(typeof installPlayTubeApp === 'function') installPlayTubeApp(); else v4Toast('Chrome/Edge menu se "Install Playza" chunein'); }

/* ---------- auth modal (Update 21/22) ---------- */
function v4OpenAuth(tab, forgot, reason){
  if(v4State.view !== 'auth') v4AuthReturn = v4State.view || 'home';
  v4Show('auth');
  v4AuthMsg('', '');
  const pill = v4$('v4-auth-pill');
  if(pill) pill.textContent = (reason === 'limit') ? 'Aap ke free downloads mukammal ho gaye hain. Aage download karne ke liye account banayein ya sign in karein.' : 'Video dekhne aur download karne ke liye pehle account banayein ya sign in karein.';
  if(forgot){ v4ShowForgot(); return; }
  v4AuthTab(tab || 'signin');
}
function v4OpenAuthForgot(){ v4OpenAuth('signin', true); }
function v4CloseAuth(){ v4Show(v4AuthReturn || 'home'); }
function v4AuthMsg(txt, kind){ const m = v4$('v4-auth-msg'); m.className = 'v4-msg' + (kind ? ' ' + kind : ''); m.textContent = txt || ''; }
function v4AuthForms(show){
  ['v4-form-signin','v4-form-signup','v4-form-verify','v4-form-forgot','v4-form-reset'].forEach(function(id){ v4$(id).style.display = (id === show) ? 'block' : 'none'; });
}
function v4AuthTab(t){
  v4AuthForms(t === 'signup' ? 'v4-form-signup' : 'v4-form-signin');
  v4$('v4-tab-signin').classList.toggle('active', t !== 'signup');
  v4$('v4-tab-signup').classList.toggle('active', t === 'signup');
  v4$('v4-auth-heading').textContent = (t === 'signup') ? 'Create Account' : 'Sign In';
}
function v4ShowForgot(e){
  if(e) e.preventDefault();
  v4AuthForms('v4-form-forgot');
  v4$('v4-auth-heading').textContent = 'Password Reset';
}
let v4SignupBody = null, v4CodeTimer = null;
function v4CodeBoxesVal(p){ let s = ''; for(let i = 0; i < 6; i++){ const b = v4$(p + i); s += b ? b.value.trim() : ''; } return s; }
function v4CodeBoxesClear(p){ for(let i = 0; i < 6; i++){ const b = v4$(p + i); if(b) b.value = ''; } const f = v4$(p + '0'); if(f) setTimeout(function(){ f.focus(); }, 60); }
function v4CodeBoxesWire(p){
  for(let i = 0; i < 6; i++){
    const b = v4$(p + i); if(!b || b.getAttribute('data-wired')) continue; b.setAttribute('data-wired', '1');
    b.addEventListener('input', function(){ b.value = b.value.replace(/[^0-9]/g, '').slice(0, 1); if(b.value && i < 5){ const n = v4$(p + (i + 1)); if(n) n.focus(); } });
    b.addEventListener('keydown', function(e){ if(e.key === 'Backspace' && !b.value && i > 0){ const pv = v4$(p + (i - 1)); if(pv){ pv.focus(); pv.value = ''; } } });
    b.addEventListener('paste', function(e){ e.preventDefault(); let t = ''; try{ t = (e.clipboardData || window.clipboardData).getData('text') || ''; }catch(err){} t = t.replace(/[^0-9]/g, '').slice(0, 6); for(let k = 0; k < 6; k++){ const bb = v4$(p + k); if(bb) bb.value = t[k] || ''; } const nx = v4$(p + Math.min(5, t.length)); if(nx) nx.focus(); });
  }
}
function v4CodeTimerStart(){
  if(v4CodeTimer) clearInterval(v4CodeTimer);
  let left = 600;
  const el = v4$('v4-code-timer');
  const show = function(){ if(el) el.textContent = 'Code khatam honay mein: ' + Math.floor(left / 60) + ':' + String(left % 60).padStart(2, '0'); };
  show();
  v4CodeTimer = setInterval(function(){ left--; if(left <= 0){ clearInterval(v4CodeTimer); v4CodeTimer = null; if(el) el.textContent = 'Code ka time khatam — Dobara bhejein'; return; } show(); }, 1000);
}
async function v4ResendCode(){
  if(!v4SignupBody){ v4AuthTab('signup'); return; }
  const r = await v4Post('/api/signup-start', v4SignupBody);
  if(r.ok && r.data && r.data.success){ v4AuthMsg('Naya code bhej diya gaya hai — Gmail check karein.', 'ok'); v4CodeBoxesClear('v4-cb'); v4CodeTimerStart(); }
  else v4AuthMsg((r.data && r.data.error) || 'Code nahi bheja ja saka', 'err');
}
function v4BackToSignup(){ v4AuthTab('signup'); }
async function v4SignIn(e){
  e.preventDefault();
  const r = await v4Post('/api/login', {email: v4$('v4-li-email').value.trim(), password: v4$('v4-li-pass').value});
  if(r.ok && r.data && r.data.success){ v4State.user = r.data.user; v4CloseAuth(); v4Toast('Welcome, ' + (r.data.user.username || '')); v4AfterAuth(); }
  else v4AuthMsg((r.data && r.data.error) || 'Sign in nahi ho saka', 'err');
}
async function v4SignUpStart(e){
  e.preventDefault();
  const body = {username: v4$('v4-su-name').value.trim(), email: v4$('v4-su-email').value.trim(), password: v4$('v4-su-pass').value};
  const r = await v4Post('/api/signup-start', body);
  if(r.ok && r.data && r.data.success){
    v4SignupEmail = body.email;
    v4SignupBody = body;
    v4AuthForms('v4-form-verify');
    v4$('v4-auth-heading').textContent = 'Code Verify karein';
    const _ve = v4$('v4-verify-email'); if(_ve) _ve.textContent = body.email;
    v4CodeBoxesClear('v4-cb');
    v4CodeTimerStart();
    if(r.data.mail_sent === false){
      v4AuthMsg('Code tayyar hai, lekin email bhejna abhi setup nahi hai.', 'err');
    } else v4AuthMsg('Code bhej diya gaya hai — apni Gmail check karein.', 'ok');
  } else v4AuthMsg((r.data && r.data.error) || 'Account nahi ban saka', 'err');
}
async function v4SignUpVerify(e){
  e.preventDefault();
  const r = await v4Post('/api/signup-verify', {email: v4SignupEmail, code: v4CodeBoxesVal('v4-cb')});
  if(r.ok && r.data && r.data.success){ v4State.user = r.data.user; v4CloseAuth(); v4Toast('Account ban gaya — Welcome, ' + (r.data.user.username || '')); v4AfterAuth(); }
  else v4AuthMsg((r.data && r.data.error) || 'Code ghalat hai', 'err');
}
async function v4ForgotStart(e){
  e.preventDefault();
  const email = v4$('v4-fg-email').value.trim();
  const r = await v4Post('/api/forgot-password', {email: email});
  if(r.ok && r.data && r.data.success){
    v4SignupEmail = email;
    v4AuthForms('v4-form-reset');
    v4CodeBoxesClear('v4-rb');
    v4AuthMsg(r.data.mail_sent === false ? 'Code tayyar hai, lekin email bhejna abhi setup nahi hai.' : 'Reset code bhej diya gaya hai — Gmail check karein.', r.data.mail_sent === false ? 'err' : 'ok');
  } else v4AuthMsg((r.data && r.data.error) || 'Code nahi bheja ja saka', 'err');
}
async function v4ForgotReset(e){
  e.preventDefault();
  const body = {email: v4SignupEmail, code: v4CodeBoxesVal('v4-rb'), new_password: v4$('v4-fg-pass').value};
  const r = await v4Post('/api/forgot-password/reset', body);
  if(r.ok && r.data && r.data.success){
    v4AuthMsg('Password badal gaya hai — ab sign in karein.', 'ok');
    v4AuthTab('signin');
  } else v4AuthMsg((r.data && r.data.error) || 'Password reset nahi ho saka', 'err');
}
function v4AfterAuth(){
  const p = v4Pending; v4Pending = null;
  if(v4State.view === 'profile') v4RenderProfile();
  if(!p) return;
  if(p.type === 'watch'){ const v = v4Videos[p.id] || {videoId:p.id, title:'', channel:''}; v4OpenWatch(v); }
  else if(p.type === 'sheet'){ v4OpenSheet(p.id); }
  else if(p.type === 'start'){ v4StartDownload(p.params); }
  else if(p.type === 'social'){ v4SocialInfo = {url:p.url, info:{}}; v4SocialDownload(p.format); }
  else if(p.type === 'ai'){ v4Show('ai'); if(p.text){ v4$('v4-ai-input').value = p.text; v4AiSend(null); } }
}

/* ---------- shared link + clipboard (Update 25) ---------- */
async function v4HandleShared(url){
  if(!url) return;
  /* Update 134: YouTube link ki pehchan LOCAL hai — share karte
     hi download sheet foran khulti hai, server ke jawab ka
     intezar nahi (Snaptube wali tez flow). */
  const ym = url.match(/(?:youtube\.com\/(?:watch\?[^ ]*v=|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  if(ym){ const v = {videoId: ym[1], title:'', channel:''}; v4Videos[v.videoId] = v; v4DlClick(null, v.videoId); return; }
  const r = await v4Post('/api/smart-link', {url:url});
  if(r.ok && r.data && r.data.type === 'youtube'){
    const v = {videoId:r.data.video_id, title:'', channel:''};
    v4Videos[v.videoId] = v;
    v4DlClick(null, v.videoId);
    return;
  }
  v4Show('social');
  v4$('v4-social-url').value = url;
  setTimeout(function(){ v4SocialFetch(null); }, 400);
}
function v4FindUrl(t){
  const i = t.indexOf('http');
  if(i < 0) return '';
  let u = '';
  for(let k = i; k < t.length; k++){ const c = t.charCodeAt(k); if(c <= 32) break; u += t[k]; }
  return u.length > 10 ? u : '';
}
async function v4ClipCheck(){
  try{
    if(!navigator.clipboard || !navigator.clipboard.readText) return;
    const t = await navigator.clipboard.readText();
    if(!t) return;
    const url = v4FindUrl(t);
    if(!url) return;
    let seen = '';
    try{ seen = sessionStorage.getItem('pt_clip_seen') || ''; }catch(e){}
    if(seen === url) return;
    try{ sessionStorage.setItem('pt_clip_seen', url); }catch(e){}
    v4HandleShared(url);
  }catch(e){}
}

/* ---------- config + init ---------- */
async function v4LoadConfig(){
  const r = await v4Fetch('/api/site-config');
  if(!(r.ok && r.data)) return;
  v4State.config = r.data;
  const ann = (r.data.announcement || '').trim();
  const el = v4$('v4-announce');
  if(ann){ el.textContent = '📢 ' + ann; el.style.display = 'block'; } else el.style.display = 'none';
  const _ver = v4$('v4-ver'); if(_ver && r.data.version) _ver.textContent = r.data.version;
  const t = r.data.toggles || {};
  if(t.social_enabled === false){ const b = v4$('v4-tt-social'); if(b) b.style.display = 'none'; }
  if(t.ai_enabled === false){ const b = v4$('v4-bn-ai'); if(b) b.style.display = 'none'; }
  if(t.music_enabled === false){ const b = document.querySelector('#v4-toptabs [data-tt="music"]'); if(b) b.style.display = 'none'; }
  if(t.shorts_enabled === false){ document.querySelectorAll('[data-t="shorts"]').forEach(function(b){ b.style.display = 'none'; }); try{ v4CloseShorts(); }catch(e){} }
  v4PhoneSyncBg();
}
(function v4Init(){
  try{ const _th = localStorage.getItem('pt_theme'); if(_th) document.documentElement.setAttribute('data-theme', _th); }catch(e){}
  v4CodeBoxesWire('v4-cb'); v4CodeBoxesWire('v4-rb');
  const _sq = v4$('v4-sq'); if(_sq){ _sq.addEventListener('input', v4SuggRender); _sq.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); v4RunSearch(_sq.value); } }); }
  ['v4-q-home','v4-q-youtube','v4-q-music'].forEach(function(id){ const _el = v4$(id); if(_el) _el.addEventListener('focus', function(){ v4OpenSearch(); }); });
  v4AiRestore();
  v4AiMicInit();
  setInterval(v4AiPrune, 60000);
  const _dpr = v4$('v4-set-dlpath-row'); if(_dpr && window.PlayTubeApp && window.PlayTubeApp.pickFolder){ _dpr.style.display = ''; v4DlPathLabel(); }
  v4LoadConfig();
  v4Fetch('/api/user-info').then(function(r){ v4State.user = (r.ok && r.data) ? r.data.user : null; });
  v4LoadFeed('v4-home-feed', 'trending');
  const rb0 = v4$('v4-refresh-btn'); if(rb0) rb0.style.display = 'block';
  v4SyncThemeBtn();
  try{ const sr = parseInt(localStorage.getItem('pt_rating') || '0'); if(sr > 0) v4RateShow(sr); }catch(e){}
  const sp = new URLSearchParams(window.location.search).get('shared');
  if(sp){ setTimeout(function(){ v4HandleShared(sp); }, 500); }
  else { setTimeout(v4ClipCheck, 1500); }
  window.addEventListener('focus', function(){ setTimeout(v4ClipCheck, 300); });
  setInterval(v4Tick, 4000);
})();
</script>
<script>
/* Update 128: PC/mobile par Playza APP (PWA) — service worker
   register ho tab hi Chrome/Edge Install deta hai. */
if('serviceWorker' in navigator){ window.addEventListener('load', function(){ navigator.serviceWorker.register('/sw.js').catch(function(){}); }); }
</script>
<!-- ================== /PLAYTUBE v4 UI LAYER ================== -->

    </body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/search')
def api_search():
    query = request.args.get('q', 'trending')
    max_results = int(request.args.get('max', 50))

    query = query.strip()
    if not query:
        query = 'trending'

    cache_key = f"{query}_{max_results}"
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return jsonify(cached_data)

    # Method 1 (PRIMARY): yt-dlp search - NO API key, NO daily quota (unlimited design)
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'no_check_certificate': True,
            'extract_flat': True,
            'skip_download': True,
            'ignoreerrors': True,
        }

        info = _extract_with_clients(
            f"ytsearch{max_results}:{query}", ydl_opts)

        if True:
            if info and 'entries' in info:
                items = []
                for entry in info['entries']:
                    if entry and entry.get('id'):
                        items.append({
                            'id': {'videoId': entry['id']},
                            'snippet': {
                                'title': entry.get('title', 'Unknown'),
                                'channelTitle': (entry.get('channel') or entry.get('uploader') or 'Unknown'),
                                'channelId': entry.get('channel_id', ''),
                                'thumbnails': {
                                    'high': {'url': entry.get('thumbnail', '')},
                                    'medium': {'url': entry.get('thumbnail', '')},
                                    'default': {'url': entry.get('thumbnail', '')}
                                }
                            },
                            'duration': entry.get('duration'),
                            'view_count': entry.get('view_count')
                        })

                if items:
                    data = {'items': items}
                    search_cache[cache_key] = (data, time.time())
                    return jsonify(data)
    except Exception:
        pass

    # Method 2: YouTube Web Scrape (no API key needed)
    items = search_youtube_web(query, max_results)

    if items:
        data = {'items': items}
        search_cache[cache_key] = (data, time.time())
        return jsonify(data)

    # Method 3: YouTube Data API - ONLY if a key is configured (helper/backup)
    if YOUTUBE_API_KEY:
        items = search_youtube_api(query, max_results)
        if items:
            data = {'items': items}
            _enrich_channels(data.get('items'))
            search_cache[cache_key] = (data, time.time())
            return jsonify(data)

    # Method 4: Fallback
    data = {'items': POPULAR_VIDEOS[:max_results]}
    _enrich_channels(data.get('items'))
    return jsonify(data)


# ============ INFINITE FEED (Update 33) ============
# YouTube-style feed: har page par NAYI videos. Trending ke liye topic
# pool ghoomta hai aur har topic ke variants bhi — is liye wohi purani
# 20 videos bar bar nahi atin. Frontend duplicates khud bhi rokta hai.
FEED_TRENDING_POOL = [
    'trending videos', 'viral videos today', 'trending naat',
    'pakistani drama latest episode', 'funny comedy videos',
    'trending songs', 'kids cartoon hindi', 'cricket highlights',
    'motu patlu new episode', 'pubg gameplay', 'cooking recipes viral',
    'tech news today', 'islamic bayan', 'punjabi songs new',
    'bollywood songs', 'pakistan vlogs',
]
FEED_MUSIC_POOL = [
    'trending songs', 'viral songs', 'new songs', 'punjabi songs new',
    'bollywood songs new', 'naat sharif new', 'qawwali best',
    'hindi songs new', 'urdu songs new',
]
FEED_NAAT_POOL = ['naat sharif', 'new naat 2026', 'beautiful urdu naat', 'madina naat', 'punjabi naat', 'owais raza qadri naat', 'ramadan naat']
FEED_DRAMA_POOL = ['pakistani drama episode', 'hindi drama serial new episode', 'turkish drama urdu dubbed', 'korean drama hindi dubbed', 'english web series hindi dubbed', 'new drama 2026 episode', 'hum tv drama', 'indian tv serial']
FEED_KIDS_POOL = ['kids cartoon', 'motu patlu cartoon', 'kids rhymes', 'cocomelon', 'baby shark', 'kids learning videos', 'peppa pig', 'cartoon for kids']
FEED_SHORTS_POOL = [
    'trending shorts #shorts', 'viral shorts #shorts',
    'funny shorts #shorts', 'tiktok viral #shorts',
    'instagram reels shorts #shorts', 'reels funny #shorts',
    'comedy shorts hindi #shorts', 'dance shorts #shorts',
    'cricket shorts #shorts', 'pakistani drama shorts #shorts',
    'movie shorts #shorts', 'bollywood shorts #shorts',
    'naat shorts #shorts', 'islamic shorts #shorts',
    'poetry shorts #shorts', 'motu patlu shorts #shorts',
    'pubg shorts #shorts', 'tiktok funny #shorts',
    'funny tiktok #shorts', 'sad shorts #shorts',
]
FEED_VARIANTS = [' latest', ' new', '', ' viral', ' best', ' 2026']
# v10: lambe scroll par naye cycle — feed/search kabhi khatam nahi hoti
FEED_CYCLES = ['', ' 2025', ' hd', ' part 2', ' new season', ' special']


def _shorts_seeds_for(text):
    """Shorts line hamesha USI type ki jis ki search/feed hai."""
    t = (text or '').lower()
    if 'cartoon' not in t and any(w in t for w in ('drama', 'serial', 'qist')):
        return ['pakistani drama shorts #shorts', 'drama shorts #shorts',
                'hindi drama shorts #shorts']
    if any(w in t for w in ('movie', 'film')):
        return ['movie shorts #shorts', 'bollywood shorts #shorts',
                'movie scenes shorts #shorts']
    if any(w in t for w in ('song', 'gana', 'geet', 'music')):
        return ['song shorts #shorts', 'bollywood song shorts #shorts',
                'punjabi song shorts #shorts']
    if 'naat' in t or 'islamic' in t:
        return ['naat shorts #shorts', 'islamic shorts #shorts']
    if any(w in t for w in ('cartoon', 'motu', 'doraemon', 'kids')):
        return ['motu patlu shorts #shorts', 'cartoon shorts #shorts',
                'doraemon shorts #shorts']
    return FEED_SHORTS_POOL


_feed_refreshing = set()


def _feed_refresh_async(query, n, cache_key):
    """Update 105: purana cache refresh background mein — user ko
    slow extraction ka wait nahi karna padta."""
    if cache_key in _feed_refreshing:
        return
    _feed_refreshing.add(cache_key)

    def _run():
        try:
            _stale = search_cache.get(cache_key)
            search_cache.pop(cache_key, None)
            _fresh = _feed_search_items(query, n)
            if not _fresh and _stale:
                search_cache[cache_key] = _stale
        except Exception:
            pass
        finally:
            _feed_refreshing.discard(cache_key)

    threading.Thread(target=_run, daemon=True).start()


def _feed_age_map(query):
    """Update 108: YouTube results page se {video_id: '3 days ago'} —
    card ki line ke liye ASAL upload time. yt-dlp flat results mein
    timestamp nahi ata, isiliye ye alag se liya jata hai. Fail/block
    ho to khali dict — koi andazay wala time kabhi nahi lagta."""
    try:
        _dated = _dated_search_items(query, 30)
    except Exception:
        return {}
    _map = {}
    for _it in _dated or []:
        _vid = ((_it.get('id') or {}).get('videoId') or '')
        _age = _it.get('age_text') or ''
        if _vid and _age:
            _map[_vid] = _age
    return _map


def _feed_search_items(query, n=30):
    cache_key = f"feed_{query}_{n}"
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return cached_data
        # Update 105: stale data fauran wapas, refresh peeche chalega
        _feed_refresh_async(query, n, cache_key)
        return cached_data
    items = []
    _age_holder = {}
    def _age_run():
        try:
            _age_holder.update(_feed_age_map(query))
        except Exception:
            pass
    _age_th = threading.Thread(target=_age_run, daemon=True)
    _age_th.start()
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'no_check_certificate': True,
            'extract_flat': True,
            'skip_download': True,
            'ignoreerrors': True,
        }
        info = _extract_with_clients(f"ytsearch{n}:{query}", ydl_opts)
        if info and 'entries' in info:
            for entry in info['entries']:
                if entry and entry.get('id'):
                    items.append({
                        'id': {'videoId': entry['id']},
                        'snippet': {
                            'title': entry.get('title', 'Unknown'),
                            'channelTitle': (entry.get('channel')
                                             or entry.get('uploader')
                                             or 'Unknown'),
                            'channelId': entry.get('channel_id', ''),
                            'thumbnails': {
                                'high': {'url': entry.get('thumbnail', '')},
                                'medium': {'url': entry.get('thumbnail', '')},
                                'default': {'url': entry.get('thumbnail', '')}
                            }
                        },
                        'duration': entry.get('duration'),
                        'view_count': entry.get('view_count'),
                        'age_ts': (entry.get('timestamp')
                                   or entry.get('release_timestamp'))
                    })
    except Exception:
        pass
    if not items:
        try:
            items = search_youtube_web(query, n) or []
        except Exception:
            items = []
    if items:
        try:
            _age_th.join(timeout=6)
            if _age_holder:
                for _it in items:
                    if not _it.get('age_text') and not _it.get('age_ts'):
                        _vid = ((_it.get('id') or {}).get('videoId')
                                or '')
                        if _vid and _vid in _age_holder:
                            _it['age_text'] = _age_holder[_vid]
        except Exception:
            pass
        try:
            _q = (query or '').strip().lower()
            _words = [w for w in _q.split() if len(w) > 2]
            if len(_words) >= 2:
                def _rel_score(_it):
                    _t = ((_it.get('snippet') or {}).get('title') or '').lower()
                    return sum(1 for _w in _words if _w in _t)
                _sc = [(_it, _rel_score(_it)) for _it in items]
                if sum(1 for _x in _sc if _x[1] >= 1) >= 5:
                    _sc = [_x for _x in _sc if _x[1] >= 1]
                _sc.sort(key=lambda _x: (
                    0 if _q in ((_x[0].get('snippet') or {}).get('title') or '').lower() else 1,
                    -_x[1]))
                items = [_it for _it, _s in _sc]
            elif len(_words) == 1:
                items = sorted(items, key=lambda _it: (
                    0 if _q in ((_it.get('snippet') or {}).get('title') or '').lower() else 1))
        except Exception:
            pass
        search_cache[cache_key] = (items, time.time())
    return items


def _shorts_search_items(query, n=20):
    """YouTube search SHORTS filter ke sath (sp=EgIYAQ) — asal shorts
    milte hain, asal titles/durations ke sath. (Update 65)"""
    cache_key = f"shorts_{query}_{n}"
    if cache_key in search_cache:
        _cd, _ts = search_cache[cache_key]
        if time.time() - _ts < CACHE_DURATION:
            return _cd
    items = []
    try:
        import urllib.parse as _up
        _url = ("https://www.youtube.com/results?search_query="
                + _up.quote(query) + "&sp=EgIYAQ%3D%3D")
        _headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        _html = requests.get(_url, headers=_headers, timeout=10).text
        _m = re.search(r'var ytInitialData = (\{.*?\});</script>',
                       _html, re.S)
        if _m:
            _data = json.loads(_m.group(1))
            _secs = (_data.get('contents', {})
                     .get('twoColumnSearchResultsRenderer', {})
                     .get('primaryContents', {})
                     .get('sectionListRenderer', {})
                     .get('contents', []))
            _vrs = []
            for _sec in _secs:
                for _c in (_sec.get('itemSectionRenderer', {})
                           .get('contents', [])):
                    if 'videoRenderer' in _c:
                        _vrs.append(_c['videoRenderer'])
            for _vr in _vrs[:n]:
                _vid = _vr.get('videoId')
                if not _vid:
                    continue
                _title = ''.join(_r.get('text', '') for _r in
                                 _vr.get('title', {}).get('runs', []))
                _chan = ''
                _runs = _vr.get('longBylineText', {}).get('runs', [])
                if _runs:
                    _chan = _runs[0].get('text', '')
                _dur = None
                _lt = (_vr.get('lengthText', {}) or {}).get('simpleText')
                if _lt:
                    try:
                        _parts = [int(_p) for _p in _lt.split(':')]
                        _dur = 0
                        for _p in _parts:
                            _dur = _dur * 60 + _p
                    except Exception:
                        _dur = None
                _vc = None
                _vct = (_vr.get('viewCountText', {}) or {}).get('simpleText', '')
                if _vct:
                    _mm = re.match(r'([\d.]+)\s*([KMB]?)', _vct.replace(',', ''))
                    if _mm:
                        _mult = {'K': 1e3, 'M': 1e6, 'B': 1e9}.get(_mm.group(2), 1)
                        _vc = int(float(_mm.group(1)) * _mult)
                _live = 'watching' in _vct.lower()
                _age = ((_vr.get('publishedTimeText', {}) or {})
                        .get('simpleText') or '')
                items.append({
                    'id': {'videoId': _vid},
                    'snippet': {
                        'title': _title or f'Video {_vid}',
                        'channelTitle': _chan or 'YouTube',
                        'channelId': '',
                        'thumbnails': {
                            'high': {'url': f'https://i.ytimg.com/vi/{_vid}/hqdefault.jpg'},
                            'medium': {'url': f'https://i.ytimg.com/vi/{_vid}/mqdefault.jpg'},
                            'default': {'url': f'https://i.ytimg.com/vi/{_vid}/default.jpg'},
                        },
                    },
                    'duration': _dur,
                    'view_count': _vc,
                    'live': _live,
                    'age_text': _age,
                })
    except Exception:
        items = []
    if items:
        search_cache[cache_key] = (items, time.time())
    return items


def _shorts_feed_items(query, n=20):
    """Shorts ke liye pehle dedicated Shorts-filter search; na mile to
    aam feed search mein se <=65s wali."""
    _items = _shorts_search_items(query, n)
    _short = [it for it in _items
              if it.get('duration') is None or it['duration'] <= 65]
    if _short:
        return _short
    # Scrape khali ya sirf lambi videos de to yt-dlp search zyada
    # results me se asal shorts chuno (v7 fix: pehle n chhota tha,
    # is liye Home ki Shorts line khali reh jati thi)
    return [it for it in _feed_search_items(query, max(n, 60))
            if it.get('duration') and it['duration'] <= 65]


def search_playlists_web(query, max_results=12):
    """YouTube search (playlist filter) — playlists: naam, channel, count.
    (Update 36)"""
    cache_key = f"pl_{query}_{max_results}"
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return cached_data
    items = []
    try:
        import urllib.parse as _up
        url = ('https://www.youtube.com/results?search_query='
               + _up.quote(query) + '&sp=EgIQAw%3D%3D')
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9'}, timeout=12)
        m = re.search(r'var ytInitialData = (\{.*?\});</script>',
                      resp.text, re.S)
        if m:
            data = json.loads(m.group(1))
            renderers = []
            lockups = []

            def _walk(node):
                if isinstance(node, dict):
                    pr = node.get('playlistRenderer')
                    if pr and pr.get('playlistId'):
                        renderers.append(pr)
                    lv = node.get('lockupViewModel')
                    if lv and lv.get('contentId'):
                        lockups.append(lv)
                    for v in node.values():
                        _walk(v)
                elif isinstance(node, list):
                    for v in node:
                        _walk(v)
            _walk(data)
            seen_pl = set()

            def _add(pid, title, channel, vc, thumb_vid):
                if not pid or pid in seen_pl or len(items) >= max_results:
                    return
                seen_pl.add(pid)
                items.append({
                    'kind': 'playlist',
                    'id': {'playlistId': pid},
                    'snippet': {'title': title or '',
                                'channelTitle': channel or ''},
                    'video_count': vc,
                    'thumb_video': thumb_vid or ''})

            for pr in renderers:
                t_obj = pr.get('title') or {}
                title = t_obj.get('simpleText') or ''.join(
                    r.get('text', '') for r in (t_obj.get('runs') or []))
                vc = pr.get('videoCount') or ''
                if not vc:
                    vct = (pr.get('videoCountText') or {}).get(
                        'simpleText', '')
                    vc = re.sub(r'[^0-9]', '', vct)
                byline = (pr.get('longBylineText')
                          or pr.get('shortBylineText') or {})
                bruns = byline.get('runs') or []
                channel = bruns[0].get('text', '') if bruns else ''
                thumb_vid = ''
                for t in ((pr.get('thumbnail') or {}).get('thumbnails')
                          or []):
                    mm = re.search(r'/vi/([^/]+)/', t.get('url', ''))
                    if mm:
                        thumb_vid = mm.group(1)
                        break
                _add(pr.get('playlistId'), title, channel,
                     int(vc) if str(vc).isdigit() else None, thumb_vid)

            for lv in lockups:
                if lv.get('contentType') != 'LOCKUP_CONTENT_TYPE_PLAYLIST':
                    continue
                md = ((lv.get('metadata') or {})
                      .get('lockupMetadataViewModel') or {})
                title = ((md.get('title') or {}).get('content')) or ''
                channel = ''
                vc = None
                rows = (((md.get('metadata') or {})
                         .get('contentMetadataViewModel') or {})
                        .get('metadataRows') or [])
                for ri, row in enumerate(rows):
                    parts = [((pt.get('text') or {}).get('content') or '')
                             for pt in (row.get('metadataParts') or [])]
                    if ri == 0 and parts:
                        channel = parts[0]
                    for part in parts:
                        mm = re.match(r'^([\d,]+)\s+videos$',
                                      part.strip())
                        if mm:
                            vc = int(mm.group(1).replace(',', ''))
                if vc is None:
                    mm = re.search(r'"content":\s*"([\d,]+) videos"',
                                   json.dumps(lv))
                    if mm:
                        vc = int(mm.group(1).replace(',', ''))
                vids = re.findall(r'/vi/([^/]+)/',
                                  json.dumps(lv.get('contentImage') or {}))
                _add(lv.get('contentId'), title, channel, vc,
                     vids[0] if vids else '')
    except Exception:
        pass
    if items:
        search_cache[cache_key] = (items, time.time())
    return items


@app.route('/api/playlist')
def api_playlist():
    pid = (request.args.get('id', '') or '').strip()
    if not pid:
        return jsonify({'error': 'Playlist id chahiye'}), 400
    cache_key = f"plfull_{pid}"
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return jsonify(cached_data)
    items = []
    title = ''
    try:
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
            'extract_flat': True, 'skip_download': True,
            'ignoreerrors': True, 'playlistend': 100,
        }
        info = _extract_with_clients(
            f"https://www.youtube.com/playlist?list={pid}", ydl_opts)
        if info:
            title = info.get('title') or ''
            for entry in (info.get('entries') or []):
                if entry and entry.get('id'):
                    items.append({
                        'id': {'videoId': entry['id']},
                        'snippet': {
                            'title': entry.get('title', 'Unknown'),
                            'channelTitle': (entry.get('channel')
                                             or entry.get('uploader')
                                             or 'Unknown'),
                        },
                        'duration': entry.get('duration'),
                        'view_count': entry.get('view_count')
                    })
    except Exception:
        pass
    data = {'title': title, 'items': items, 'count': len(items)}
    if items:
        search_cache[cache_key] = (data, time.time())
    return jsonify(data)


def _age_minutes(text):
    """'3 days ago' jaisi text ko takreeban minutes me badlo (freshness sort)."""
    if not text:
        return None
    t = str(text).lower()
    if 'just now' in t:
        return 0
    # Update 112: YouTube ab aksar MUKHTASAR text deta hai ('19h ago',
    # '1d ago') — purana parser sirf '19 hours ago' samajhta tha, to
    # age_min None reh jata tha aur Aaj Ki Taza sab kuch gira deti
    # thi. Ab dono shaklein chalti hain ('mo' = month, 'm' = minute).
    m = re.search(r'(\d+)\s*(seconds?|secs?|months?|mo|minutes?|mins?|'
                  r'hours?|hrs?|days?|weeks?|years?|[smhdwy])\b', t)
    if not m:
        return None
    _u = m.group(2)
    if _u.startswith('s'):
        return 0
    if _u == 'mo' or _u.startswith('month'):
        _mult = 43200
    elif _u.startswith('mi') or _u == 'm':
        _mult = 1
    elif _u.startswith('h'):
        _mult = 60
    elif _u.startswith('d'):
        _mult = 1440
    elif _u.startswith('w'):
        _mult = 10080
    elif _u.startswith('y'):
        _mult = 525600
    else:
        return None
    return int(m.group(1)) * _mult


def _dated_search_items(query, n=30):
    """Aam YouTube search — published time ke sath, SAB SE NAYI pehle.
    (Update 79: search freshness rule — nayi videos upar.)"""
    cache_key = f"dated_{query}_{n}"
    if cache_key in search_cache:
        _cd, _ts = search_cache[cache_key]
        if time.time() - _ts < 600:
            return _cd
    items = []
    try:
        import urllib.parse as _up
        _url = ("https://www.youtube.com/results?search_query="
                + _up.quote(query))
        _headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        _html = requests.get(_url, headers=_headers, timeout=10).text
        _m = re.search(r'var ytInitialData = (\{.*?\});</script>',
                       _html, re.S)
        if _m:
            _data = json.loads(_m.group(1))
            _secs = (_data.get('contents', {})
                     .get('twoColumnSearchResultsRenderer', {})
                     .get('primaryContents', {})
                     .get('sectionListRenderer', {})
                     .get('contents', []))
            _vrs = []
            for _sec in _secs:
                for _c in (_sec.get('itemSectionRenderer', {})
                           .get('contents', [])):
                    if 'videoRenderer' in _c:
                        _vrs.append(_c['videoRenderer'])
            for _vr in _vrs[:n]:
                _vid = _vr.get('videoId')
                if not _vid:
                    continue
                _title = ''.join(_r.get('text', '') for _r in
                                 _vr.get('title', {}).get('runs', []))
                _chan = ''
                _runs = _vr.get('longBylineText', {}).get('runs', [])
                if _runs:
                    _chan = _runs[0].get('text', '')
                _dur = None
                _lt = (_vr.get('lengthText', {}) or {}).get('simpleText')
                if _lt:
                    try:
                        _parts = [int(_p) for _p in _lt.split(':')]
                        _dur = 0
                        for _p in _parts:
                            _dur = _dur * 60 + _p
                    except Exception:
                        _dur = None
                _vc = None
                _vct = (_vr.get('viewCountText', {}) or {}).get('simpleText', '')
                if _vct:
                    _mm = re.match(r'([\d.]+)\s*([KMB]?)', _vct.replace(',', ''))
                    if _mm:
                        _mult = {'K': 1e3, 'M': 1e6, 'B': 1e9}.get(_mm.group(2), 1)
                        _vc = int(float(_mm.group(1)) * _mult)
                _live = 'watching' in _vct.lower()
                _age = ((_vr.get('publishedTimeText', {}) or {})
                        .get('simpleText') or '')
                items.append({
                    'id': {'videoId': _vid},
                    'snippet': {
                        'title': _title or f'Video {_vid}',
                        'channelTitle': _chan or 'YouTube',
                        'channelId': '',
                        'thumbnails': {
                            'high': {'url': f'https://i.ytimg.com/vi/{_vid}/hqdefault.jpg'},
                            'medium': {'url': f'https://i.ytimg.com/vi/{_vid}/mqdefault.jpg'},
                            'default': {'url': f'https://i.ytimg.com/vi/{_vid}/default.jpg'},
                        },
                    },
                    'duration': _dur,
                    'view_count': _vc,
                    'live': _live,
                    'age_text': _age,
                    'age_min': _age_minutes(_age),
                })
    except Exception:
        items = []
    if items:
        items.sort(key=lambda it: (it.get('age_min') is None,
                                   it.get('age_min') or 0))
        search_cache[cache_key] = (items, time.time())
    return items


@app.route('/api/suggest')
def api_suggest():
    """Search screen ke live suggestions (YouTube autocomplete)."""
    q = (request.args.get('q', '') or '').strip()
    if not q:
        return jsonify({'suggestions': []})
    out = []
    try:
        import urllib.parse as _up2
        _u = ('https://suggestqueries.google.com/complete/search'
              '?client=firefox&ds=yt&q=' + _up2.quote(q))
        _r = requests.get(_u, headers={'User-Agent': 'Mozilla/5.0'},
                          timeout=5)
        _d = _r.json()
        if isinstance(_d, list) and len(_d) > 1 and isinstance(_d[1], list):
            out = [str(x) for x in _d[1]][:10]
    except Exception:
        out = []
    if not out:
        _base = ['new song', 'new drama', 'pakistani drama', 'motu patlu',
                 'naat sharif', 'punjabi song', 'hindi movie', 'cartoon hindi',
                 'ertugrul urdu', 'funny video', 'coke studio', 'qawwali',
                 'new movie', 'kids cartoon', 'islamic bayan']
        out = [b for b in _base if q.lower() in b][:8]
    return jsonify({'suggestions': out})


_OE_CACHE = {}


def _oembed_channel(_vid):
    if _vid in _OE_CACHE:
        return _OE_CACHE[_vid]
    _name = None
    try:
        _r = requests.get(
            'https://www.youtube.com/oembed',
            params={'url': f'https://www.youtube.com/watch?v={_vid}',
                    'format': 'json'},
            headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if _r.status_code == 200:
            _name = (_r.json() or {}).get('author_name') or None
    except Exception:
        _name = None
    if len(_OE_CACHE) > 3000:
        _OE_CACHE.clear()
    _OE_CACHE[_vid] = _name
    return _name


def _enrich_channels(_items):
    """v18: jin items ka channel 'Unknown'/khali hai, un ka asal channel
    naam YouTube oEmbed se lao (cache ke sath) — cards par asal naam."""
    try:
        _missing = []
        for _it in _items or []:
            if not isinstance(_it, dict):
                continue
            _sn = _it.get('snippet')
            _holder = _sn if isinstance(_sn, dict) else _it
            _ch = _holder.get('channelTitle') or _holder.get('channel') or ''
            if _ch and _ch != 'Unknown':
                continue
            _idv = _it.get('id')
            _vid = (_idv.get('videoId') if isinstance(_idv, dict) else None) \
                or _it.get('video_id') \
                or (_idv if isinstance(_idv, str) else '')
            if _vid:
                _missing.append((_holder, _vid))
        if not _missing:
            return
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as _ex:
            _names = list(_ex.map(lambda _t: _oembed_channel(_t[1]), _missing))
        for (_holder, _vid), _nm in zip(_missing, _names):
            if _nm:
                _holder['channelTitle'] = _nm
                if 'channel' in _holder or _holder is not _it:
                    _holder['channel'] = _nm
    except Exception:
        pass


@app.route('/api/feed')
def api_feed():
    q = (request.args.get('q', 'trending') or 'trending').strip()
    try:
        page = max(0, min(500, int(request.args.get('page', 0))))
    except (TypeError, ValueError):
        page = 0
    # Session token (r): har app-open / refresh par naya — feed ka
    # starting point badal jata hai, is liye har dafa nayi videos.
    sess = (request.args.get('r', '') or '').strip()
    offset = 0
    if sess:
        offset = int(hashlib.md5(sess.encode('utf-8')).hexdigest()[:6], 16)
    # Personalization (Update 34): user ki top searches/watches (int)
    raw_int = (request.args.get('int', '') or '')[:600]
    interests = [p.strip()[:60] for p in raw_int.split('|')
                 if len(p.strip()) >= 3][:6]
    ql = q.lower()
    if 'trend' in ql and 'song' not in ql and 'music' not in ql:
        if interests:
            pool = []
            ti = 0
            for i, tseed in enumerate(FEED_TRENDING_POOL):
                if i % 2 == 0 and ti < len(interests) * 2:
                    pool.append(interests[ti % len(interests)])
                    ti += 1
                pool.append(tseed)
            while ti < len(interests) * 2:
                pool.append(interests[ti % len(interests)])
                ti += 1
        else:
            pool = list(FEED_TRENDING_POOL)
    elif ql in ('new songs', 'songs', 'music', 'trending songs',
                'viral songs'):
        pool = list(FEED_MUSIC_POOL)
    else:
        pool = [q]
    ftype = (request.args.get('type', 'all') or 'all').strip().lower()
    if ftype not in ('all', 'videos', 'playlists', 'shorts', 'live', 'movies', 'mp3', 'naat', 'dramas', 'kids'):
        ftype = 'all'
    if ftype == 'shorts' and not feature_enabled('shorts_enabled'):
        return jsonify({'items': [], 'page': page, 'has_more': False})
    shorts_pool_mode = False
    # Update 79: TikTok / reels / shorts — ek hi matlab, vertical shorts
    _synq = ql.replace(' ', '')
    if _synq in ('tiktok', 'reels', 'reel', 'shorts', 'short',
                 'tiktokvideos', 'reelsvideos', 'shortsvideos',
                 'tiktokshorts', 'tiktokreels', 'tiktokvideo',
                 'instagramreels', 'ytshorts') and ftype in ('all', 'videos'):
        ftype = 'shorts'
        pool = list(FEED_SHORTS_POOL)
        shorts_pool_mode = True
    if ftype == 'shorts' and ('trend' in ql or ql == 'shorts'):
        pool = list(FEED_SHORTS_POOL)
        shorts_pool_mode = True
    if shorts_pool_mode and interests:
        # v11: Shorts bhi user ki pasand se — interest topics pehle
        pool = [i + ' shorts' for i in interests[:3]] + pool
    if ftype == 'naat':
        pool = list(FEED_NAAT_POOL)
    # Update 79: seen-filter (session me dikh chuki dobara nahi),
    # sort=date (nayi pehle), min_dur (lambi videos wala filter)
    _seen_ids = set(x for x in (request.args.get('seen', '') or '')
                    .split(',') if x)
    _sort = (request.args.get('sort', '') or '').strip().lower()
    try:
        _min_dur = int(request.args.get('min_dur', 0))
    except (TypeError, ValueError):
        _min_dur = 0

    def _R(_items, _hm, _sr=True):
        if _seen_ids:
            _items = [it for it in _items
                      if (((it.get('id') or {}).get('videoId')
                           or (it.get('id') or {}).get('playlistId')
                           or '') not in _seen_ids)]
        if _min_dur:
            _items = [it for it in _items
                      if (it.get('duration') or 0) >= _min_dur]
        _resp = {'items': _items, 'page': page, 'has_more': _hm}
        # Har feed/search ke sath usi type ki Shorts ki 1 line (page 0)
        if _sr and page == 0 and ftype not in ('shorts', 'playlists') \
                and _items:
            try:
                # v10: seed session ke hisab se ghumao + dekhi hui shorts
                # dobara nahi + line hamesha USI type ki jis ki feed/search
                # hai (drama search -> sirf drama shorts).
                _off = (sum(ord(c) for c in
                             (request.args.get('r', '') or 'x'))
                        % len(pool)) if len(pool) > 1 else 0
                _srq = (q if len(pool) <= 1 else pool[_off]) + ' shorts'
                _srow = _shorts_feed_items(_srq, 10)
                if len(_srow) < 4 and len(pool) <= 1:
                    _have0 = set()
                    for _x in _srow:
                        _have0.add((_x.get('id') or {}).get('videoId') or '')
                    for _it in _shorts_feed_items(q + ' #shorts', 10):
                        _v0 = (_it.get('id') or {}).get('videoId') or ''
                        if _v0 and _v0 not in _have0:
                            _srow.append(_it)
                            _have0.add(_v0)
                if _seen_ids:
                    _srow = [it for it in _srow
                             if (((it.get('id') or {}).get('videoId')
                                  or '') not in _seen_ids)]
                if len(_srow) < 4:
                    _have = set()
                    for _x in _srow:
                        _have.add((_x.get('id') or {}).get('videoId') or '')
                    for _sq in _shorts_seeds_for(_srq + ' ' + q):
                        for _it in _shorts_feed_items(_sq, 10):
                            _v = (_it.get('id') or {}).get('videoId') or ''
                            if _v and _v not in _have and _v not in _seen_ids:
                                _srow.append(_it)
                                _have.add(_v)
                            if len(_srow) >= 10:
                                break
                        if len(_srow) >= 10:
                            break
                if _srow:
                    _resp['shorts_row'] = _srow[:10]
            except Exception:
                pass
        _enrich_channels(_resp.get('items'))
        _enrich_channels(_resp.get('shorts_row'))
        return jsonify(_resp)

    eff = page + offset
    seed = pool[eff % len(pool)]
    variant = FEED_VARIANTS[(eff // len(pool)) % len(FEED_VARIANTS)]
    _cyc = FEED_CYCLES[(eff // (len(pool) * len(FEED_VARIANTS)))
                       % len(FEED_CYCLES)]
    seed_q = (seed + variant + _cyc).strip()
    total_pages = len(pool) * len(FEED_VARIANTS) * len(FEED_CYCLES)
    if len(pool) <= 1 and ftype in ('all', 'videos'):
        # Update 102: SEARCH seedha chale — variant/cycle wali drift
        # NAHI (search ki videos ke baad ajnabi videos nahi ghusti),
        # aur global seen-filter search ko khali nahi karta (user ne
        # khud dhoonda hai — wahi mile ga, chahe Home par dekhi ho).
        # Pages ek hi bari list ke hisse hain; khatam hon to khatam.
        if _sort == 'date':
            _all = _dated_search_items(q, 60) \
                or _feed_search_items(q, 60)
        else:
            _all = _feed_search_items(q, 60)
        _per = 20
        _chunk = _all[page * _per:(page + 1) * _per]
        _hm = (page + 1) * _per < len(_all)
        _seen_save = _seen_ids
        _seen_ids = set()
        _resp2 = _R(_chunk, _hm)
        _seen_ids = _seen_save
        return _resp2
    if ftype == 'playlists':
        items = search_playlists_web(seed_q, 12)
        return _R(items, page < 6, False)
    if ftype == 'all' and page % 3 == 2:
        items = search_playlists_web(seed_q, 6)
        if items:
            return _R(items, page < total_pages - 1, False)
    if ftype == 'shorts':
        # Sirf ASAL shorts (duration <= 65s) — lambi "shorts" naam wali
        # compilations nahi. Kai seeds mila kar dhoondte hain.
        merged = []
        seen_ids = set()
        tries = 6 if shorts_pool_mode else 4
        for k in range(tries):
            s_k = pool[(eff + k) % len(pool)]
            if shorts_pool_mode:
                q_k = s_k
            else:
                q_k = (s_k + FEED_VARIANTS[k % len(FEED_VARIANTS)]).strip()
            for it in _shorts_feed_items(q_k, 24):
                vid = (it.get('id') or {}).get('videoId')
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    merged.append(it)
            real_so_far = [it for it in merged
                           if it.get('duration') is None or it['duration'] <= 65]
            if len(real_so_far) >= 24:
                break
        items = [it for it in merged
                 if it.get('duration') is None or it['duration'] <= 65]
        return _R(items, page < total_pages - 1, False)
    if ftype == 'live':
        # Update 71: Live chip — 'live stream' talash, live-lagti
        # videos pehle (duration None/0 ya title mein live)
        merged = []
        seen_ids = set()
        for k in range(3):
            s_k = pool[(eff + k) % len(pool)]
            q_k = s_k if 'live' in s_k.lower() else (s_k + ' live stream').strip()
            for it in _feed_search_items(q_k, 20):
                vid = (it.get('id') or {}).get('videoId')
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    merged.append(it)
            if len(merged) >= 24:
                break

        def _is_live(it):
            if it.get('duration') in (None, 0):
                return True
            return 'live' in ((it.get('snippet') or {}).get('title') or '').lower()

        live_first = [it for it in merged if _is_live(it)]
        rest = [it for it in merged if not _is_live(it)]
        return _R((live_first + rest)[:30], page < total_pages - 1)
    if ftype == 'movies':
        # Update 71/77: Movies chip — 'full movie' talash, lambi videos
        # (40+ minute) pehle; andar sub-options (Indian/Pakistani/
        # English/Hindi Dubbed/South)
        _MOVIE_SUBS = {
            'indian': (['indian full movie hindi', 'bollywood full movie', 'hindi movie full hd', 'new indian movie full'], ' indian full movie'),
            'pakistani': (['pakistani full movie', 'lollywood full movie', 'pakistani film full'], ' pakistani full movie'),
            'punjabi': (['punjabi full movie', 'new punjabi movie full', 'punjabi film full movie'], ' punjabi full movie'),
            'english': (['hollywood hindi dubbed full movie', 'english movie hindi dubbed', 'hollywood movie hindi dubbed full'], ' hollywood hindi dubbed movie'),
            'dubbed': (['hollywood movie hindi dubbed full', 'english movie hindi dubbed', 'action movie hindi dubbed full'], ' hindi dubbed full movie'),
            'south': (['south indian movie hindi dubbed', 'south movie hindi dubbed full', 'allu arjun movie hindi dubbed'], ' south indian hindi dubbed movie'),
        }
        _msub = (request.args.get('sub', 'all') or 'all').strip().lower()
        if _msub in _MOVIE_SUBS:
            _mp, _msuffix = _MOVIE_SUBS[_msub]
            pool = list(_mp) if ('trend' in ql or not ql) else [q + _msuffix]
        merged = []
        seen_ids = set()
        for k in range(3):
            s_k = pool[(eff + k) % len(pool)]
            q_k = s_k if 'movie' in s_k.lower() else (s_k + ' full movie').strip()
            for it in _feed_search_items(q_k, 20):
                vid = (it.get('id') or {}).get('videoId')
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    merged.append(it)
            longs = [it for it in merged if (it.get('duration') or 0) >= 2400]
            if len(longs) >= 12:
                break
        longs = [it for it in merged if (it.get('duration') or 0) >= 2400]
        items = longs if len(longs) >= 6 else sorted(
            merged, key=lambda x: -(x.get('duration') or 0))
        return _R(items[:30], page < total_pages - 1)
    if ftype == 'mp3':
        # Update 72: Music > MP3 — sirf audio songs ('official audio'
        # talash, kai seeds mila kar)
        merged = []
        seen_ids = set()
        for k in range(3):
            s_k = pool[(eff + k) % len(pool)]
            q_k = s_k if 'audio' in s_k.lower() else (s_k + ' official audio').strip()
            for it in _feed_search_items(q_k, 20):
                vid = (it.get('id') or {}).get('videoId')
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    merged.append(it)
            if len(merged) >= 24:
                break
        return _R(merged[:30], page < total_pages - 1)
    if ftype in ('dramas', 'kids'):
        # Update 74: Dramas / Kids chips — generic feed par apna pool,
        # search par wohi lafz + category
        if ftype == 'dramas':
            # Update 75: Dramas ke andar 6 sub-options
            _DRAMA_SUBS = {
                'pakistani': (['pakistani drama episode', 'hum tv drama', 'ary digital drama', 'geo tv drama', 'green tv drama', 'new pakistani drama 2026'], ' pakistani drama'),
                'indian': (['indian drama serial', 'hindi tv serial', 'star plus drama', 'zee tv serial', 'colors tv drama', 'indian serial episode'], ' indian drama serial'),
                'turkish': (['turkish drama in urdu', 'turkish drama hindi dubbed', 'ertugrul in urdu', 'kurulus osman urdu dubbed', 'turkish serial urdu dubbed'], ' turkish drama urdu dubbed'),
                'dubbed': (['korean drama hindi dubbed', 'chinese drama hindi dubbed', 'kdrama hindi dubbed', 'thai drama hindi dubbed', 'dubbed drama hindi urdu'], ' hindi dubbed drama'),
                'webseries': (['netflix series hindi dubbed', 'english web series trending', 'amazon prime series hindi dubbed', 'mx player web series', 'best web series hindi dubbed'], ' web series'),
            }
            _sub = (request.args.get('sub', 'all') or 'all').strip().lower()
            if _sub in _DRAMA_SUBS:
                _pool, _suffix = _DRAMA_SUBS[_sub]
                base_pool = list(_pool) if ('trend' in ql or not ql) else [q + _suffix]
            else:
                base_pool = list(FEED_DRAMA_POOL) if ('trend' in ql or not ql) else [q + ' drama episode']
        else:
            # Update 77: Kids ke andar famous naam wale options
            _KIDS_SUBS = {
                'motupatlu': (['motu patlu', 'motu patlu cartoon hindi', 'motu patlu new episode'], ' motu patlu'),
                'cocomelon': (['cocomelon', 'cocomelon nursery rhymes', 'cocomelon songs'], ' cocomelon'),
                'doraemon': (['doraemon cartoon hindi', 'doraemon new episodes hindi', 'doraemon movie hindi'], ' doraemon hindi'),
                'peppa': (['peppa pig', 'peppa pig full episodes', 'peppa pig cartoon'], ' peppa pig'),
                'tomjerry': (['tom and jerry', 'tom and jerry cartoon', 'tom and jerry hindi'], ' tom and jerry'),
            }
            _ksub = (request.args.get('sub', 'all') or 'all').strip().lower()
            if _ksub in _KIDS_SUBS:
                _kp, _ksuffix = _KIDS_SUBS[_ksub]
                base_pool = list(_kp) if ('trend' in ql or not ql) else [q + _ksuffix]
            else:
                base_pool = list(FEED_KIDS_POOL) if ('trend' in ql or not ql) else [q + ' for kids']
        merged = []
        seen_ids = set()
        for k in range(3):
            s_k = base_pool[(eff + k) % len(base_pool)]
            if len(base_pool) <= 1:
                q_k = (s_k + FEED_VARIANTS[(eff + k) % len(FEED_VARIANTS)]).strip()
            else:
                q_k = s_k
            for it in _feed_search_items(q_k, 20):
                vid = (it.get('id') or {}).get('videoId')
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    merged.append(it)
            if len(merged) >= 24:
                break
        return _R(merged[:30], page < total_pages - 1)
    has_more = page < (total_pages - 1)
    if len(pool) <= 1:
        if _sort == 'date':
            items = _dated_search_items(seed_q, 30)
            if not items:
                items = _feed_search_items(seed_q, 30)
        else:
            items = _feed_search_items(seed_q, 30)
        if _sort != 'date' and q:
            _ql2 = q.lower()
            _w2 = [w for w in _ql2.split() if len(w) > 2]
            def _exact_rank(it):
                _t = (((it.get('snippet') or {}).get('title') or '').lower())
                if _ql2 in _t:
                    return 0
                if _w2 and all(w in _t for w in _w2):
                    return 1
                return 2
            items = sorted(items, key=_exact_rank)
        return _R(items, has_more)
    # Update 64: MIXED feed — har page 3 alag seeds se round-robin mila
    # kar banta hai, taake ek hi topic ki videos na bharein. Ek channel
    # ki zyada se zyada 4 videos per page, duplicate bilkul nahi.
    _base = eff % len(pool)
    _step = max(1, len(pool) // 3)
    _seeds = []
    for _k in range(3):
        _s = pool[(_base + _k * _step) % len(pool)]
        _v = FEED_VARIANTS[(eff + _k) % len(FEED_VARIANTS)]
        _seeds.append((_s + _v + _cyc).strip())
    try:
        from concurrent.futures import ThreadPoolExecutor as _TPE
        with _TPE(max_workers=3) as _ex:
            _buckets = list(_ex.map(
                lambda _sq: _feed_search_items(_sq, 12), _seeds))
    except Exception:
        _buckets = [_feed_search_items(_sq, 12) for _sq in _seeds]
    items, _seen, _chan = [], set(), {}
    _idx = 0
    while len(items) < 30:
        _progressed = False
        for _b in _buckets:
            if _idx < len(_b):
                _progressed = True
                _it = _b[_idx]
                _vid = (_it.get('id') or {}).get('videoId')
                _ch = ((_it.get('snippet') or {}).get('channelTitle') or '')
                if _vid and _vid not in _seen and _chan.get(_ch, 0) < 4:
                    _seen.add(_vid)
                    _chan[_ch] = _chan.get(_ch, 0) + 1
                    items.append(_it)
                if len(items) >= 30:
                    break
        _idx += 1
        if not _progressed:
            break
    return _R(items, has_more)


# v17: social downloads — Chrome pehchan (impersonation) + saaf errors.
try:
    import curl_cffi  # noqa: F401
    _HAS_CFFI = True
except Exception:
    _HAS_CFFI = False

_SOCIAL_UA = ('Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36')


def _social_opts(extra=None):
    o = {'http_headers': {'User-Agent': _SOCIAL_UA},
         'extractor_retries': 3, 'socket_timeout': 25}
    if _HAS_CFFI:
        o['impersonate'] = 'chrome'
    if extra:
        o.update(extra)
    return o


def _social_friendly_err(e, platform='Social'):
    m = re.sub(r'\x1b\[[0-9;]*m', '', str(e or '')).lower()
    if '429' in m or 'too many requests' in m or 'rate limit' in m \
            or 'rate-limit' in m:
        return (f'{platform} ne is waqt server ki requests rok di hain '
                '(bohat zyada load). Ye aam tor par khud theek ho jata '
                'hai — 2-3 minute baad dobara try karein.')
    if 'login' in m or 'cookie' in m or 'sign in' in m \
            or 'authentication' in m:
        return (f'Is video ke liye {platform} login maang raha hai — '
                'bina login ke sirf public videos download hoti hain. '
                'Koi public video ka link try karein.')
    if 'private' in m or 'unavailable' in m or 'not available' in m \
            or 'removed' in m or 'deleted' in m:
        return ('Ye video private hai, delete ho gayi hai, ya is link '
                'par available nahi hai.')
    if 'unsupported url' in m or 'no video' in m \
            or 'unable to extract' in m:
        return (f'{platform} ki is link se video nahi mil saki — '
                'link check karke dobara try karein.')
    return (f'{platform} se download nahi ho saka — net ya link ka '
            'masla ho sakta hai, thodi dair baad dobara try karein.')


def _social_og_info(url, platform):
    """Update 136: yt-dlp fail ho to page ke og: tags se
    seedhi video link — public posts par aksar mil jati
    hai. Na mile to None."""
    for _ua in ('facebookexternalhit/1.1 '
                '(+http://www.facebook.com/externalhit_uatext.php)',
                _SOCIAL_UA):
        try:
            _r = requests.get(
                url, headers={'User-Agent': _ua,
                              'Accept-Language': 'en-US,en;q=0.9'},
                timeout=15, allow_redirects=True)
            _h = _r.text or ''
        except Exception:
            continue
        if not _h:
            continue

        def _og(prop):
            _m = re.search(
                r'property=["\']' + re.escape(prop)
                + r'["\']\s+content=["\']([^"\']+)', _h)
            if not _m:
                _m = re.search(
                    r'content=["\']([^"\']+)["\']\s+property=["\']'
                    + re.escape(prop) + r'["\']', _h)
            if not _m:
                _m = re.search(
                    r'name=["\']' + re.escape(prop)
                    + r'["\']\s+content=["\']([^"\']+)', _h)
            return html.unescape(_m.group(1)) if _m else ''

        _vid = (_og('og:video:secure_url') or _og('og:video')
                or _og('twitter:player:stream'))
        if _vid:
            return {'title': _og('og:title') or f'{platform} video',
                    'thumbnail': _og('og:image'),
                    'duration': 0, 'uploader': '',
                    'platform': platform, 'ext': 'mp4',
                    'is_image': False, 'formats_available': 1,
                    'direct_url': _vid}
    return None


@app.route('/api/fetch-social-info', methods=['POST'])
def fetch_social_info():
    data = request.json
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        ydl_opts = _social_opts({
            'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'skip_download': True, 'no_check_certificate': True,
            'retries': 2})
        info = None
        _last_e = None
        for _att in range(2):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as _ydl:
                    info = _ydl.extract_info(url, download=False)
                if info:
                    break
            except Exception as _e:
                _last_e = _e
                if _att == 0:
                    time.sleep(3)
        if not info:
            raise _last_e or Exception('no info')

        if True:
            if info:
                platform = detect_platform(url)
                return jsonify({
                    "info": {
                        "title": info.get('title', 'Unknown'),
                        "thumbnail": info.get('thumbnail', ''),
                        "duration": info.get('duration', 0),
                        "uploader": info.get('uploader', info.get('channel', '')),
                        "platform": platform,
                        "ext": info.get('ext', 'mp4'),
                        "is_image": str(info.get('ext', '')).lower() in ('jpg', 'jpeg', 'png', 'webp'),
                        "formats_available": len(info.get('formats', [])) if 'formats' in info else 0
                    }
                })
    except Exception as e:
        try:
            _og = _social_og_info(url, detect_platform(url))
        except Exception:
            _og = None
        if _og:
            return jsonify({"info": _og})
        return jsonify({"error": _social_friendly_err(e, detect_platform(url))}), 400

    return jsonify({"error": "Could not fetch video information"}), 400


@app.route('/api/download-social', methods=['POST'])
def download_social_media():
    try:
        _storage_cleanup()
    except Exception:
        pass
    data = request.json
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    download_id = data.get('download_id', '')
    direct_url = data.get('direct_url', '').strip()
    title_hint = data.get('title', '').strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not download_id:
        download_id = f"social_{int(time.time())}_{random.randint(1000, 9999)}"

    platform = detect_platform(url)

    # Update 79: social download par bhi wohi shared guest limit
    if not session.get('user_id'):
        _gl2 = get_guest_limit()
        if _gl2 <= 0:
            return jsonify({'error': 'Login required to download!',
                            'login_required': True}), 403
        _soc_guest = _guest_device_id()
        if _guest_count(_soc_guest) >= _gl2:
            return jsonify({'error': f'Guest ke {_gl2} free downloads pure ho gaye — ab account banayein!',
                            'login_required': True, 'guest_limit': True,
                            'limit': _gl2}), 403
        guest_pending[download_id] = _soc_guest

    download_progress[download_id] = {
        'status': 'starting', 'percent': 0, 'speed': '',
        'error': None, 'format': format_type, 'platform': platform
    }

    thread = threading.Thread(target=download_social_in_background, args=(
        url, format_type, platform, download_id, direct_url, title_hint))
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "download_id": download_id, "platform": platform, "format": format_type})


def detect_platform(url):
    url = url.lower()
    platforms = {
        'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
        'facebook.com': 'Facebook', 'fb.watch': 'Facebook',
        'instagram.com': 'Instagram',
        'twitter.com': 'Twitter/X', 'x.com': 'Twitter/X',
        'tiktok.com': 'TikTok',
        'reddit.com': 'Reddit',
        'pinterest.com': 'Pinterest',
        'vimeo.com': 'Vimeo',
        'soundcloud.com': 'SoundCloud',
        'dailymotion.com': 'Dailymotion',
        'linkedin.com': 'LinkedIn',
        'twitch.tv': 'Twitch',
        'snapchat.com': 'Snapchat', 'threads.net': 'Threads',
        'whatsapp.com': 'WhatsApp'
    }
    for domain, platform in platforms.items():
        if domain in url:
            return platform
    return "Social Media"


def download_social_in_background(url, format_type, platform, download_id,
                                  direct_url='', title_hint=''):
    if direct_url and format_type == 'video':
        # Update 136: og: se mili seedhi file — bina yt-dlp ke
        try:
            _title = sanitize_filename(title_hint or f'{platform} video') or 'video'
            _path = os.path.join(SOCIAL_DIR, f'{_title}.mp4')
            _n = 1
            while os.path.exists(_path):
                _n += 1
                _path = os.path.join(SOCIAL_DIR, f'{_title} ({_n}).mp4')
            _t0 = time.time()
            with requests.get(direct_url, headers={'User-Agent': _SOCIAL_UA},
                              stream=True, timeout=30) as _r:
                _r.raise_for_status()
                _total = int(_r.headers.get('Content-Length') or 0)
                _done = 0
                with open(_path, 'wb') as _f:
                    for _chunk in _r.iter_content(262144):
                        if not _chunk:
                            continue
                        _f.write(_chunk)
                        _done += len(_chunk)
                        _el = max(time.time() - _t0, 0.1)
                        download_progress[download_id] = {
                            'status': 'downloading',
                            'percent': int(100 * _done / _total) if _total else 0,
                            'speed': format_speed(_done / _el),
                            'error': None, 'format': format_type,
                            'platform': platform}
            _size = os.path.getsize(_path)
            downloaded_files[download_id] = {
                'downloadId': download_id, 'videoId': download_id,
                'title': _title, 'format': 'MP4', 'quality': 'Best',
                'platform': platform, 'file_path': _path,
                'file_size': _size, 'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }
            save_downloads_db()
            _gd = guest_pending.pop(download_id, None)
            if _gd:
                _guest_inc(_gd)
            download_progress[download_id] = {
                'status': 'completed', 'percent': 100, 'speed': '',
                'error': None, 'file_path': _path, 'title': _title,
                'format': format_type, 'platform': platform,
                'file_size': _size}
        except Exception as _e:
            download_progress[download_id] = {
                'status': 'failed', 'percent': 0, 'speed': '',
                'error': _social_friendly_err(_e, platform),
                'format': format_type, 'platform': platform}
        return
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            speed = d.get('speed', 0)
            speed_str = format_speed(speed) if speed else ''

            download_progress[download_id] = {
                'status': 'downloading', 'percent': percent, 'speed': speed_str,
                'error': None, 'format': format_type, 'platform': platform
            }
        elif d['status'] == 'finished':
            download_progress[download_id] = {
                'status': 'processing', 'percent': 100, 'speed': '',
                'error': None, 'format': format_type, 'platform': platform
            }

    try:
        if format_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                'outtmpl': os.path.join(SOCIAL_DIR, '%(title)s.%(ext)s'),
                'quiet': True, 'no_warnings': True, 'noplaylist': True,
                'progress_hooks': [progress_hook], 'ignoreerrors': True,
                'no_check_certificate': True, 'prefer_insecure': True,
                'retries': 6, 'fragment_retries': 6,
            }
        elif format_type == 'image':
            ydl_opts = {
                'format': 'best/best',
                'outtmpl': os.path.join(SOCIAL_DIR, '%(title)s.%(ext)s'),
                'quiet': True, 'no_warnings': True, 'noplaylist': True,
                'progress_hooks': [progress_hook], 'ignoreerrors': True,
                'no_check_certificate': True, 'prefer_insecure': True,
                'retries': 3, 'fragment_retries': 3,
            }
        else:
            ydl_opts = {
                'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                'outtmpl': os.path.join(SOCIAL_DIR, '%(title)s.%(ext)s'),
                'quiet': True, 'no_warnings': True, 'noplaylist': True,
                'progress_hooks': [progress_hook], 'ignoreerrors': True,
                'no_check_certificate': True, 'prefer_insecure': True,
                'merge_output_format': 'mp4', 'retries': 3, 'fragment_retries': 3,
            }

        ydl_opts.update(_social_opts())
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = sanitize_filename(info.get('title', 'video'))
                _is_image = (format_type == 'image')

                if format_type == 'audio':
                    file_path = os.path.join(SOCIAL_DIR, f"{title}.mp3")
                    if not os.path.exists(file_path):
                        mp3_files = [f for f in os.listdir(
                            SOCIAL_DIR) if f.endswith('.mp3')]
                        if mp3_files:
                            mp3_files.sort(key=lambda x: os.path.getmtime(
                                os.path.join(SOCIAL_DIR, x)), reverse=True)
                            file_path = os.path.join(SOCIAL_DIR, mp3_files[0])
                            title = os.path.splitext(mp3_files[0])[0]
                else:
                    file_path = os.path.join(SOCIAL_DIR, f"{title}.mp4")
                    if not os.path.exists(file_path):
                        video_files = [f for f in os.listdir(SOCIAL_DIR) if f.endswith(
                            ('.mp4', '.mkv', '.webm', '.mov'))]
                        if video_files:
                            video_files.sort(key=lambda x: os.path.getmtime(
                                os.path.join(SOCIAL_DIR, x)), reverse=True)
                            file_path = os.path.join(
                                SOCIAL_DIR, video_files[0])
                            title = os.path.splitext(video_files[0])[0]
                        if not os.path.exists(file_path):
                            img_files = [f for f in os.listdir(SOCIAL_DIR)
                                         if f.endswith(('.jpg', '.jpeg',
                                                        '.png', '.webp'))]
                            if img_files:
                                img_files.sort(key=lambda x: os.path.getmtime(
                                    os.path.join(SOCIAL_DIR, x)), reverse=True)
                                file_path = os.path.join(
                                    SOCIAL_DIR, img_files[0])
                                title = os.path.splitext(img_files[0])[0]
                                _is_image = True

                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    final_format = 'MP3' if format_type == 'audio' else (
                        'IMAGE' if _is_image else 'MP4')

                    downloaded_files[download_id] = {
                        'downloadId': download_id, 'videoId': download_id, 'title': title,
                        'format': final_format,
                        'quality': 'Picture' if _is_image else 'Best',
                        'platform': platform,
                        'file_path': file_path, 'file_size': file_size,
                        'status': 'completed', 'timestamp': datetime.now().isoformat()
                    }
                    save_downloads_db()

                    _gd = guest_pending.pop(download_id, None)
                    if _gd:
                        _guest_inc(_gd)

                    download_progress[download_id] = {
                        'status': 'completed', 'percent': 100, 'speed': '',
                        'error': None, 'file_path': file_path, 'title': title,
                        'format': format_type, 'platform': platform, 'file_size': file_size
                    }
                else:
                    raise Exception("Download completed but file not found")
    except Exception as e:
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
    # Update 79 fix: kamyabi par neeche wala error block NA chale
    if download_progress.get(download_id, {}).get('status') == 'completed':
        return
    guest_pending.pop(download_id, None)
    error_msg = _social_friendly_err(error_msg, platform)

    download_progress[download_id] = {
        'status': 'error',
        'percent': 0,
        'speed': '',
        'error': error_msg[:150],
        'format': format_type,
        'platform': platform
    }
# Authentication routes


@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not feature_enabled('signup_enabled'):
        return jsonify({'error': 'Signup abhi band hai (admin ne off kiya hai)',
                        'signup_disabled': True}), 403

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username or email already exists"}), 400

    _ve = session.get('pt_verified_email')
    _vt = session.get('pt_verified_at', 0)
    if _ve != email or (time.time() - _vt) > 600:
        conn.close()
        return jsonify({'error': 'Pehle email verify karein - verification code se.',
                        'verification_required': True}), 403

    password_hash = hash_password(password)

    try:
        cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                       (username, email, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        session['user_id'] = user_id
        session['username'] = username

        return jsonify({"success": True, "user": {"id": user_id, "username": username, "email": email}})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM users WHERE email = ? OR username = ?', (email, email))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user['password_hash'] != hash_password(password):
        return jsonify({"error": "Invalid password"}), 401

    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({"success": True, "user": {"id": user['id'], "username": user['username'], "email": user['email']}})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})
    # ============ LEGAL PAGES ============


@app.route('/privacy-policy')
def privacy_policy():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Privacy Policy - Playza</title>
        <style>
            body { background: #0f0f0f; color: #fff; padding: 50px; font-family: Arial; line-height: 1.8; }
            h1 { color: #ff0000; }
            h2 { color: #ff0000; margin-top: 30px; }
            p { color: #aaa; }
            a { color: #ff0000; }
            .container { max-width: 800px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Privacy Policy</h1>
            <p>Last updated: 2024</p>

            <h2>1. Information We Collect</h2>
            <p>When you register on Playza, we collect your username and email address. We do not collect any payment information directly.</p>

            <h2>2. How We Use Your Information</h2>
            <p>Your information is used to manage your account, provide download services, and process premium subscriptions.</p>

            <h2>3. Cookies</h2>
            <p>We use cookies for session management to keep you logged in.</p>

            <h2>4. Third-Party Services</h2>
            <p>We may use Google AdSense for advertisements. Google may use cookies to serve personalized ads.</p>

            <h2>5. Data Security</h2>
            <p>Your passwords are encrypted using SHA-256 hashing. We do not store plain text passwords.</p>

            <h2>6. Contact Us</h2>
            <p>Email: chuzajani1@gmail.com</p>

            <p><a href="/">← Back to Playza</a></p>
        </div>
    </body>
    </html>
    '''


@app.route('/terms-of-service')
def terms_of_service():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terms of Service - Playza</title>
        <style>
            body { background: #0f0f0f; color: #fff; padding: 50px; font-family: Arial; line-height: 1.8; }
            h1 { color: #ff0000; }
            h2 { color: #ff0000; margin-top: 30px; }
            p { color: #aaa; }
            a { color: #ff0000; }
            .container { max-width: 800px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Terms of Service</h1>
            <p>Last updated: 2026</p>

            <h2>1. Acceptance of Terms</h2>
            <p>By accessing and using Playza, you agree to be bound by these Terms of Service.</p>

            <h2>2. Description of Service</h2>
            <p>Playza is a video downloading tool that allows users to download videos from various platforms for personal use only.</p>

            <h2>3. User Accounts</h2>
            <p>You are responsible for maintaining the confidentiality of your account credentials.</p>

            <h2>4. Premium Subscriptions</h2>
            <p>Premium plans provide additional features. Payments are processed via JazzCash and EasyPaisa. All sales are final.</p>

            <h2>5. Acceptable Use</h2>
            <p>You agree not to use Playza for any illegal or unauthorized purpose.</p>

            <h2>6. Intellectual Property</h2>
            <p>All downloaded content belongs to their respective owners. Playza does not claim ownership.</p>

            <h2>7. Refund Policy</h2>
            <p>Due to the digital nature of our service, we do not offer refunds for premium subscriptions.</p>

            <h2>8. Contact</h2>
            <p>Email: chuzajani1@gmail.com</p>

            <p><a href="/">← Back to Playza</a></p>
        </div>
    </body>
    </html>
    '''


@app.route('/about')
def about():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>About - Playza</title>
        <style>
            body { background: #0f0f0f; color: #fff; padding: 50px; font-family: Arial; line-height: 1.8; }
            h1 { color: #ff0000; }
            h2 { color: #ff0000; margin-top: 30px; }
            p { color: #aaa; }
            a { color: #ff0000; }
            .box { background: #1a1a1a; padding: 20px; border-radius: 10px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>About Playza</h1>

        <div class="box">
            <h2>🎬 What is Playza?</h2>
            <p>Playza is a free video downloader that allows users to download videos from YouTube and other social media platforms. We provide high-quality MP3 and MP4 downloads for personal use.</p>
        </div>

        <div class="box">
            <h2>⚡ Our Features</h2>
            <p>✅ YouTube Video Download (MP3/MP4)</p>
            <p>✅ Social Media Downloader</p>
            <p>✅ Playlist Download (Premium)</p>
            <p>✅ Batch Download (Premium)</p>
            <p>✅ HD Quality Downloads</p>
            <p>✅ Thumbnail Download</p>
            <p>✅ Subtitle Download</p>
        </div>

        <div class="box">
            <h2>💎 Premium Plans</h2>
            <p>Weekly: Rs. 200</p>
            <p>Monthly: Rs. 500</p>
            <p>Yearly: Rs. 3000</p>
        </div>

        <div class="box">
            <h2>📞 Contact Us</h2>
            <p>Email: chuzajani1@gmail.com</p>
            <p>JazzCash: No account added yet</p>
            <p>EasyPaisa: No account added yet</p>
        </div>

        <p><a href="/">← Back to Playza</a></p>
    </body>
    </html>
    '''


@app.route('/developer')
def developer():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Developer - Playza</title>
        <style>
            body { background: #0f0f0f; color: #fff; padding: 50px; font-family: Arial; line-height: 1.8; text-align: center; }
            h1 { color: #ff0000; }
            h2 { color: #ff0000; margin-top: 30px; }
            p { color: #aaa; }
            a { color: #ff0000; }
            .box { background: #1a1a1a; padding: 30px; border-radius: 15px; margin: 20px auto; max-width: 500px; }
            .avatar { width: 100px; height: 100px; border-radius: 50%; background: #ff0000; margin: 0 auto; display: flex; align-items: center; justify-content: center; font-size: 3rem; }
            .social-links { display: flex; gap: 15px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
            .social-btn { padding: 10px 20px; border-radius: 25px; text-decoration: none; color: #fff; }
        </style>
    </head>
    <body>
        <h1>👨‍💻 Developer Info</h1>

        <div class="box">
            <div class="avatar">👨‍💻</div>
            <h2 style="margin-top:20px;">Chuza</h2>
            <p>Full Stack Developer & Creator of Playza</p>
            <p>📍 Pakistan</p>
            <p>📧 chuzajani1@gmail.com</p>
        </div>

        <div class="box">
            <h2>🛠️ Skills</h2>
            <p>✅ Python (Flask)</p>
            <p>✅ Web Development</p>
            <p>✅ Video Downloading Systems</p>
            <p>✅ Payment Integration</p>
            <p>✅ API Development</p>
        </div>

        <div class="box">
            <h2>📱 Contact</h2>
            <p>📱 JazzCash: No account added yet</p>
            <p>📱 EasyPaisa: No account added yet</p>
        </div>

        <div class="social-links">
            <a href="#" target="_blank" class="social-btn" style="background:#25d366;">WhatsApp</a>
            <a href="mailto:chuzajani1@gmail.com" class="social-btn" style="background:#ff0000;">Email</a>
        </div>

        <p style="margin-top:30px; color:#666;">Coded by Chuza © 2026</p>
        <p><a href="/">← Back to Playza</a></p>
            <!-- Quick Links -->
    <div style="text-align:center; padding:20px;">
        <a href="/about" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="about">About</a>
        <span style="color:#666;">|</span>
        <a href="/contact" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="contact">Contact</a>
        <span style="color:#666;">|</span>
        <a href="/developer" style="color:#aaa; margin:0 10px; text-decoration:none;">Developer</a>
        <span style="color:#666;">|</span>
        <a href="/privacy-policy" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="privacy">Privacy Policy</a>
        <span style="color:#666;">|</span>
        <a href="/terms-of-service" style="color:#aaa; margin:0 10px; text-decoration:none;">Terms</a>
    </div>
</body>
    </body>
    </html>
    '''


@app.route('/contact')
def contact():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Contact - Playza</title>
        <style>
            body { background: #0f0f0f; color: #fff; padding: 50px; font-family: Arial; }
            h1 { color: #ff0000; }
            a { color: #ff0000; }
            .box { background: #1a1a1a; padding: 20px; border-radius: 10px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>📞 Contact Us</h1>
        <div class="box">
            <p>📧 Email: chuzajani1@gmail.com</p>
            <p>📱 JazzCash: No account added yet</p>
            <p>📱 EasyPaisa: No account added yet</p>
        </div>
        <p><a href="/">← Back to Playza</a></p>
    </body>
    </html>
    '''

@app.route('/channel/<channel_id>')
def channel_page(channel_id):
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/channel/{channel_id}", download=False)
            
            videos = []
            for entry in info.get('entries', [])[:50]:
                if entry and entry.get('id'):
                    videos.append({
                        'id': entry['id'],
                        'title': entry.get('title', 'Unknown'),
                        'thumbnail': entry.get('thumbnail', '')
                    })
            
            channel_name = info.get('channel', info.get('uploader', 'Channel'))
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{channel_name} - Playza</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ background: #0f0f0f; color: #fff; font-family: Arial; padding: 20px; margin: 0; }}
                    h1 {{ color: #ff0000; }}
                    .back-btn {{ color: #fff; text-decoration: none; background: #333; padding: 10px 20px; border-radius: 20px; display: inline-block; margin-bottom: 20px; }}
                    .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; margin-top: 20px; }}
                    .video-card {{ background: #1a1a1a; border-radius: 10px; overflow: hidden; cursor: pointer; border: 1px solid #333; }}
                    .video-card:hover {{ border-color: #ff0000; }}
                    .video-card img {{ width: 100%; height: 100px; object-fit: cover; }}
                    .video-card p {{ padding: 10px; font-size: 0.75rem; margin: 0; min-height: 35px; }}
                    .channel-info {{ background: #1a1a1a; padding: 20px; border-radius: 15px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <a href="/" class="back-btn">← Back to Playza</a>
                <div class="channel-info">
                    <h1>{channel_name}</h1>
                    <p>{len(videos)} videos available</p>
                </div>
                <div class="video-grid">
                    {''.join(f'<div class="video-card" onclick="window.location.href=\'/?video={v["id"]}&title={v["title"]}\'"><img src="{v["thumbnail"]}" onerror="this.src=\'https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg\'"><p>{v["title"]}</p></div>' for v in videos)}
                </div>
            </body>
            </html>
            '''
    except:
        return "Channel not found or no videos available", 404
@app.route('/api/user-info')
def user_info():
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, username, email FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({"user": {"id": user['id'], "username": user['username'], "email": user['email']}})

    return jsonify({"user": None})


    # ============ SECRET ADMIN PANEL ============
ADMIN_SECRET_KEY = "Chuza-Playza-_nyDbqU9aci8uRBCIzhbFiAK"  # Apna secret key yahan daalo


@app.route('/admin/<secret_key>')
def admin_panel(secret_key):
    if secret_key != ADMIN_SECRET_KEY:
        return "Access Denied", 403

    session['pt_admin'] = True

    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Playza Admin</title>
        <style>
            body { background: #0f0f0f; color: #fff; font-family: Arial; padding: 20px; }
            .payment-card { background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #333; }
            .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; font-weight: bold; }
            .approve { background: #4CAF50; color: #fff; }
            .reject { background: #ff0000; color: #fff; }
            h1 { color: #ff0000; }
            p { color: #aaa; }
        </style>
    </head>
    <body>
        <h1>🔐 Playza Admin Panel</h1>
        <div style="background:#1a1a1a; padding:20px; border-radius:10px; margin-bottom:20px;">
    <h3 style="color:#4CAF50;">📊 Visitor Stats</h3>
    <p>Total Visitors: <span id="totalVisitors" style="color:#fff;">Loading...</span></p>
    <p>Today Visitors: <span id="todayVisitors" style="color:#fff;">Loading...</span></p>
</div>

<script>
fetch('/api/visitor-stats')
    .then(res => res.json())
    .then(data => {
        document.getElementById(
            'totalVisitors').innerText = data.total_visitors;
        document.getElementById(
            'todayVisitors').innerText = data.today_visitors;
    });
</script>
<div style="background:#1a1a1a; padding:20px; border-radius:10px; margin-bottom:20px; border:1px solid #4f46e5;">
    <h3 style="color:#2dd4bf;">💳 Payment Accounts (JazzCash / EasyPaisa)</h3>
    <p style="color:#aaa;">Yahan apna account number add karein — website par sirf wahi number show hoga jo yahan save ho. Koi account save na ho to website par koi number nahi dikhe ga.</p>
    <div style="display:flex; gap:10px; flex-wrap:wrap; margin:10px 0;">
        <select id="accMethod" style="padding:10px; border-radius:6px; background:#272727; color:#fff; border:1px solid #444;">
            <option value="jazzcash">JazzCash</option>
            <option value="easypaisa">EasyPaisa</option>
        </select>
        <input type="text" id="accNumber" placeholder="Account Number (e.g. 03xx-xxxxxxx)" style="flex:1; min-width:180px; padding:10px; border-radius:6px; background:#272727; color:#fff; border:1px solid #444;">
        <input type="text" id="accTitle" placeholder="Account Title (name)" style="flex:1; min-width:150px; padding:10px; border-radius:6px; background:#272727; color:#fff; border:1px solid #444;">
        <button class="btn" style="background:#4f46e5; color:#fff;" onclick="saveAccount()">💾 Save Account</button>
    </div>
    <div id="accList" style="color:#fff;"></div>
    <script>
        const ADMIN_KEY = location.pathname.split('/').filter(Boolean).pop();
        async function loadAccounts() {
            const res = await fetch('/api/admin/payment-accounts/' + ADMIN_KEY);
            const data = await res.json();
            const list = document.getElementById('accList');
            const accs = data.accounts || {};
            const keys = Object.keys(accs);
            if (!keys.length) { list.innerHTML = '<p style="color:#FF9800;">⚠️ No account added yet — website par koi number show nahi ho raha.</p>'; return; }
            list.innerHTML = keys.map(k => `<p>✅ <b>${k.toUpperCase()}</b>: ${accs[k].account_number} (${accs[k].account_title || ''}) <button class="btn reject" onclick="removeAccount('${k}')">Remove</button></p>`).join('');
        }
        async function saveAccount() {
            const method = document.getElementById('accMethod').value;
            const number = document.getElementById('accNumber').value.trim();
            const title = document.getElementById('accTitle').value.trim();
            if (!number) { alert('Account number likhein'); return; }
            const res = await fetch('/api/admin/payment-accounts/' + ADMIN_KEY, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({method: method, account_number: number, account_title: title})});
            const data = await res.json();
            alert(data.error || 'Account save ho gaya!');
            loadAccounts();
        }
        async function removeAccount(method) {
            if (!confirm('Ye account remove kar dein?')) return;
            await fetch('/api/admin/payment-accounts/' + ADMIN_KEY + '/' + method, {method:'DELETE'});
            loadAccounts();
        }
        loadAccounts();
    </script>
</div>
        <p>Payment Verification - Secret Access Only</p>
        <div id="payments"></div>
        <script>
            async function loadPayments() {
                const res = await fetch('/api/admin/pending-payments-list');
                const data = await res.json();
                const container = document.getElementById('payments');
                container.innerHTML = '';

                if (data.payments && data.payments.length > 0) {
                    data.payments.forEach(p => {
                        const card = document.createElement('div');
                        card.className = 'payment-card';
                        card.innerHTML = `
                            <h3>👤 ${p.username} - <span style="color:#4CAF50;">Rs. ${p.amount_pkr}</span></h3>
                            <p>📱 Method: ${p.payment_method}</p>
                            <p>📱 Sender: ${p.sender_account}</p>
                            <p>🔢 Transaction ID: ${p.transaction_id}</p>
                            <p>📅 Plan: ${p.plan_type}</p>
                            <p>🕐 Date: ${p.created_at}</p>
                            <button class="btn approve" onclick="approve(${p.id})">✓ Approve</button>
                            <button class="btn reject" onclick="reject(${p.id})">✗ Reject</button>
                        `;
                        container.appendChild(card);
                    });
                } else {
                    container.innerHTML = '<p style="color:#4CAF50;">✅ No pending payments</p>';
                }
            }

            async function approve(id) {
                if (!confirm("Approve this payment?")) return;
                const res = await fetch(`/api/admin/approve-payment/${id}`, {method: 'POST'});
                const data = await res.json();
                alert(data.message || 'Approved!');
                loadPayments();
            }

            async function reject(id) {
                if (!confirm("Reject this payment?")) return;
                const res = await fetch(`/api/admin/reject-payment/${id}`, {method: 'POST'});
                const data = await res.json();
                alert(data.message || 'Rejected!');
                loadPayments();
            }

            loadPayments();
        </script>
    </body>
    </html>
    '''


@app.route('/api/admin/pending-payments-list')
def admin_pending_payments_list():
    if not _admin_ok():
        return jsonify({'error': 'Admin login required'}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.username, u.email
        FROM pakistan_payments p
        JOIN users u ON p.user_id = u.id
        WHERE p.status = 'pending'
        ORDER BY p.created_at DESC
    ''')
    payments = cursor.fetchall()
    conn.close()

    return jsonify({'payments': [dict(p) for p in payments]})


@app.route('/api/admin/approve-payment/<payment_id>', methods=['POST'])
def admin_approve_payment(payment_id):
    if not _admin_ok():
        return jsonify({'error': 'Admin login required'}), 403
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT * FROM pakistan_payments WHERE id = ?', (payment_id,))
    payment = cursor.fetchone()

    if not payment:
        conn.close()
        return jsonify({'error': 'Payment not found'}), 404

    plan = PREMIUM_PLANS_PKR[payment['plan_type']]
    start_date = datetime.now()
    expiry_date = start_date + timedelta(days=plan['days'])

    cursor.execute('''
        INSERT INTO premium_users (user_id, plan_type, start_date, expiry_date, payment_method, transaction_id, amount_paid)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            plan_type = ?, start_date = ?, expiry_date = ?,
            payment_method = ?, transaction_id = ?, amount_paid = ?,
            is_active = 1
    ''', (payment['user_id'], payment['plan_type'], start_date, expiry_date,
          payment['payment_method'], payment['transaction_id'], payment['amount_pkr'],
          payment['plan_type'], start_date, expiry_date,
          payment['payment_method'], payment['transaction_id'], payment['amount_pkr']))

    cursor.execute(
        'UPDATE pakistan_payments SET status = "verified", verified = 1 WHERE id = ?', (payment_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Payment approved! Premium activated!'})


@app.route('/api/admin/reject-payment/<payment_id>', methods=['POST'])
def admin_reject_payment(payment_id):
    if not _admin_ok():
        return jsonify({'error': 'Admin login required'}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE pakistan_payments SET status = "rejected" WHERE id = ?', (payment_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Payment rejected!'})
# ============ PREMIUM API ROUTES ============


@app.route('/api/premium/status')
def premium_status():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'is_premium': False})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM premium_users WHERE user_id = ? AND is_active = 1', (user_id,))
    premium = cursor.fetchone()
    conn.close()

    if premium:
        return jsonify({
            'is_premium': True,
            'plan': premium['plan_type'],
            'expiry': premium['expiry_date']
        })

    return jsonify({'is_premium': False})


@app.route('/api/premium/plans')
def get_plans():
    return jsonify({
        'plans': PREMIUM_PLANS_PKR,
        'payments': PAKISTAN_PAYMENTS
    })


@app.route('/api/premium/submit', methods=['POST'])
@login_required
def submit_premium():
    data = request.json
    if not feature_enabled('premium_enabled'):
        return jsonify({'error': 'Premium abhi band hai (admin ne off kiya hai)',
                        'premium_disabled': True}), 403
    plan_type = data.get('plan_type')
    payment_method = data.get('payment_method')
    sender_account = data.get('sender_account')
    transaction_id = data.get('transaction_id')

    if plan_type not in PREMIUM_PLANS_PKR:
        return jsonify({'error': 'Invalid plan'}), 400

    if payment_method not in PAKISTAN_PAYMENTS:
        return jsonify({'error': 'Invalid payment method'}), 400

    if not sender_account or not transaction_id:
        return jsonify({'error': 'Please fill all fields'}), 400

    plan = PREMIUM_PLANS_PKR[plan_type]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pakistan_payments (user_id, payment_method, sender_account, transaction_id, amount_pkr, plan_type)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], payment_method, sender_account, transaction_id, plan['price'], plan_type))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Payment submitted! Premium will activate after verification.'})


@app.route('/api/admin/pending-payments')
def admin_pending_payments():
    if session.get('username') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.username, u.email
        FROM pakistan_payments p
        JOIN users u ON p.user_id = u.id
        WHERE p.status = 'pending'
        ORDER BY p.created_at DESC
    ''')
    payments = cursor.fetchall()
    conn.close()

    return jsonify({'pending_payments': [dict(p) for p in payments]})


@app.route('/api/admin/verify-payment/<payment_id>', methods=['POST'])
def verify_payment(payment_id):
    if session.get('username') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    action = data.get('action')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT * FROM pakistan_payments WHERE id = ?', (payment_id,))
    payment = cursor.fetchone()

    if not payment:
        conn.close()
        return jsonify({'error': 'Payment not found'}), 404

    if action == 'approve':
        plan = PREMIUM_PLANS_PKR[payment['plan_type']]
        start_date = datetime.now()
        expiry_date = start_date + timedelta(days=plan['days'])

        cursor.execute('''
            INSERT INTO premium_users (user_id, plan_type, start_date, expiry_date, payment_method, transaction_id, amount_paid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_type = ?, start_date = ?, expiry_date = ?,
                payment_method = ?, transaction_id = ?, amount_paid = ?,
                is_active = 1
        ''', (payment['user_id'], payment['plan_type'], start_date, expiry_date,
              payment['payment_method'], payment['transaction_id'], payment['amount_pkr'],
              payment['plan_type'], start_date, expiry_date,
              payment['payment_method'], payment['transaction_id'], payment['amount_pkr']))

        cursor.execute(
            'UPDATE pakistan_payments SET status = "verified", verified = 1 WHERE id = ?', (payment_id,))
        conn.commit()

    elif action == 'reject':
        cursor.execute(
            'UPDATE pakistan_payments SET status = "rejected" WHERE id = ?', (payment_id,))
        conn.commit()

    conn.close()
    return jsonify({'success': True})

# YouTube Download routes


def _find_duplicate(video_id, format_type, quality):
    """Wohi video + format (+ quality) pehle se complete ho to entry."""
    if not video_id:
        return None
    _f = (format_type or 'mp4').upper()
    _q = str(quality or '').lower()
    for _e in downloaded_files.values():
        if _e.get('status') != 'completed' or _e.get('videoId') != video_id:
            continue
        if (_e.get('format') or '').upper() != _f:
            continue
        _eq = str(_e.get('quality') or '').lower()
        if _f == 'MP4':
            if _q and _eq and _q != _eq and _q != 'best' and _eq != 'best':
                continue
        elif _f in ('MP3', 'M4A'):
            _d1 = ''.join(c for c in _q if c.isdigit())
            _d2 = ''.join(c for c in _eq if c.isdigit())
            if _d1 and _d2 and _d1 != _d2:
                continue
        if _e.get('file_path') and os.path.exists(_e['file_path']):
            return _e
    return None


def _find_active_download(video_id, format_type):
    """Wohi video abhi download ho rahi ho to us ki dl_id (double rokne ko)."""
    if not video_id:
        return None
    _f = (format_type or 'mp4').lower()
    for _did, _st in list(download_progress.items()):
        if _st.get('status') not in ('starting', 'downloading', 'processing'):
            continue
        _m = download_meta.get(_did, {})
        if _m.get('video_id') == video_id and \
                (_m.get('format_type') or 'mp4').lower() == _f:
            return _did
    return None


@app.route('/api/start-download', methods=['POST'])
def start_download():
    data = request.json or {}
    video_id = data.get('video_id')
    format_type = data.get('format', 'mp3')
    quality = data.get('quality')
    download_id = data.get('download_id')
    clip_start = data.get('clip_start')
    clip_end = data.get('clip_end')
    user_id = session.get('user_id')

    # Clip validation (v3): both ends required, end must be after start
    if clip_start is not None or clip_end is not None:
        try:
            clip_start = float(clip_start)
            clip_end = float(clip_end)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid clip time"}), 400
        if clip_start < 0 or clip_end <= clip_start:
            return jsonify({"error": "Clip end must be after start"}), 400

    if not video_id:
        return jsonify({"error": "Video ID missing"}), 400

    _dup = _find_duplicate(video_id, format_type, quality)
    if _dup:
        return jsonify({'success': True, 'already': True,
                        'download_id': _dup.get('downloadId'),
                        'message': 'Ye video is quality mein pehle se '
                                   'Downloads mein hai'})

    # Update 44: bina account ke guest ko admin ki set ki hui tadad
    # (default 10) tak free downloads; ginti sirf COMPLETE hone par
    # badhti hai — fail ho jaye to guest ka number zaya nahi hota.
    guest_device = None
    guest_limit = get_guest_limit()
    if not session.get('user_id'):
        if guest_limit <= 0:
            return jsonify({
                'error': 'Login required to download!',
                'login_required': True
            }), 403
        guest_device = _guest_device_id()
        if _guest_count(guest_device) >= guest_limit:
            return jsonify({
                'error': f'Guest ke {guest_limit} free downloads pure ho gaye — ab account banayein!',
                'login_required': True, 'guest_limit': True,
                'limit': guest_limit
            }), 403

    if not feature_enabled('downloads_enabled'):
        return jsonify({'error': 'Downloads abhi band hain (admin ne off kiya hai)',
                        'downloads_disabled': True}), 403

    # Free qualities: all low/mid video qualities, 3GP, MP3 bitrates, M4A.
    # Only HD video (720p and up) is a Premium feature.
    FREE_QUALITIES = [None, 'best', '3gp', '144p', '240p', '360p', '480p',
                      '70', '128', '160', '320', '70k', '128k', '160k', '320k']
    if format_type in ('mp3', 'm4a'):
        pass  # audio is free at every bitrate
    elif quality not in FREE_QUALITIES:
        if feature_enabled('hd_premium_only') and not is_premium_user(session.get('user_id')):
            return jsonify({
                'error': 'HD quality requires Premium!',
                'premium_required': True
            }), 403

    if not download_id:
        download_id = f"{video_id}_{int(time.time())}"

    download_progress[download_id] = {
        'status': 'starting', 'percent': 0, 'speed': '', 'error': None}
    download_meta[download_id] = {'video_id': video_id, 'format_type': format_type,
                                  'quality': quality, 'clip_start': clip_start,
                                  'clip_end': clip_end,
                                  'title': data.get('title', '')}
    _save_download_meta()

    thread = threading.Thread(target=download_in_background, args=(
        video_id, format_type, quality, download_id, user_id, clip_start, clip_end))
    thread.daemon = True
    thread.start()

    if guest_device:
        guest_pending[download_id] = guest_device
        return jsonify({"success": True, "download_id": download_id,
                        "guest_remaining": guest_limit - _guest_count(guest_device)})
    return jsonify({"success": True, "download_id": download_id})


# ============ YT-DLP BOT-BLOCK RETRY HELPER (v4, Bug #5) ============
# YouTube kabhi kabhi server IP ko "Sign in to confirm you're not a bot"
# keh kar block kar deta hai. Aisi surat me extraction/download mukhtalif
# player clients (android, ios, tv, web_safari, mweb) se dobara try hota
# hai. YT_COOKIES_PATH env me cookies file ho to wo bhi istemal hoti hai.
_YT_CLIENTS = [None, 'android', 'ios', 'tv', 'web_safari', 'mweb']


def _is_bot_block(err):
    _s = str(err).lower()
    return ('sign in to confirm' in _s or 'not a bot' in _s or
            'video is not available' in _s or 'video unavailable' in _s or
            'requested format is not available' in _s or
            'use --cookies' in _s or 'http error 403' in _s)


def _yt_cookies_path():
    _p = os.environ.get('YT_COOKIES_PATH', '')
    if _p and os.path.exists(_p):
        return _p
    _d = os.path.join(DATA_DIR, 'yt_cookies.txt')
    return _d if os.path.exists(_d) else ''


def _ydl_opts_with_client(base_opts, client):
    opts = dict(base_opts or {})
    _ck = _yt_cookies_path()
    if _ck:
        opts['cookiefile'] = _ck
    if client:
        _ea = dict(opts.get('extractor_args') or {})
        _yt = dict(_ea.get('youtube') or {})
        _yt['player_client'] = [client]
        _ea['youtube'] = _yt
        opts['extractor_args'] = _ea
    return opts


def _extract_with_clients(url, base_opts, download=False):
    """yt-dlp extract_info - bot-block par agle player client se retry."""
    last_err = None
    for _client in _YT_CLIENTS:
        _opts = _ydl_opts_with_client(base_opts, _client)
        try:
            with yt_dlp.YoutubeDL(_opts) as _ydl:
                _info = _ydl.extract_info(url, download=download)
            if _info:
                if _client:
                    print(f"[Playza] yt-dlp player_client '{_client}' worked for {str(url)[:70]}")
                return _info
            last_err = Exception('No info returned')
        except Exception as e:
            last_err = e
            if _is_bot_block(e):
                continue
            raise
    if last_err:
        raise last_err
    return None


def _extract_formats_info(url):
    """Formats ke liye: jo client SAB SE ZYADA asal qualities de, usi ka
    result — warna android client sirf 360p de kar baqi qualities chupa
    deta tha. (Update 66)"""
    _base = {'quiet': True, 'no_warnings': True,
             'no_check_certificate': True, 'skip_download': True}
    if _HAS_CFFI:
        _base['impersonate'] = 'chrome'
    _best = None
    _best_score = (-1, -1)
    _last_err = None
    for _client in _YT_CLIENTS:
        _opts = _ydl_opts_with_client(_base, _client)
        try:
            with yt_dlp.YoutubeDL(_opts) as _ydl:
                _info = _ydl.extract_info(url, download=False)
        except Exception as e:
            # Formats ke liye har client try karna hai — ek fail ho to
            # agla; sirf tab fail jab koi bhi info na de.
            _last_err = e
            continue
        if not _info:
            continue
        _fmts = _info.get('formats', []) or []
        _maxh = max([f.get('height') or 0 for f in _fmts] or [0])
        _score = (_maxh, len(_fmts))
        if _score > _best_score:
            _best_score = _score
            _best = _info
        if _maxh >= 2160 or len(_fmts) >= 25:
            break
    if _best:
        return _best
    if _last_err:
        raise _last_err
    return None


# ============ SPEED SETTINGS (Update 9 - VIP) ============
# Parallel fragment downloads + big chunks + aria2c (16 connections) when available.
def _speed_opts():
    opts = {
        'concurrent_fragment_downloads': 16,
        'http_chunk_size': 10 * 1024 * 1024,
        'buffer_size': 1024 * 1024,
        'retries': 10,
        'fragment_retries': 10,
        'file_access_retries': 5,
        'socket_timeout': 30,
    }
    try:
        if shutil.which('aria2c'):
            opts['external_downloader'] = 'aria2c'
            opts['external_downloader_args'] = {
                'aria2c': ['-x', '16', '-s', '16', '-k', '1M',
                           '--file-allocation=none', '--summary-interval=0']}
    except Exception:
        pass
    return opts


def download_in_background(video_id, format_type, quality, download_id, user_id=None,
                           clip_start=None, clip_end=None, _client_idx=0, title_hint=None,
                           _retry_pass=0):
    try:
        _storage_cleanup()
    except Exception:
        pass
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    started_at = time.time()

    _m = download_meta.get(download_id, {})
    _m.update({'video_id': video_id, 'format_type': format_type, 'quality': quality,
               'clip_start': clip_start, 'clip_end': clip_end})
    if title_hint and not _m.get('title'):
        _m['title'] = title_hint
    download_meta[download_id] = _m
    _save_download_meta()

    if format_type in ('mp3', 'm4a'):
        download_dir = MP3_DIR
    else:
        download_dir = MP4_DIR

    def progress_hook(d):
        if download_control.get(download_id, {}).get('cancel'):
            raise Exception('__PAUSED__')
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            speed = d.get('speed', 0)
            speed_str = format_speed(speed) if speed else ''

            download_progress[download_id] = {
                'status': 'downloading', 'percent': percent, 'speed': speed_str,
                'speed_bytes': speed or 0, 'error': None,
                'filename': d.get('filename')}
        elif d['status'] == 'finished':
            download_progress[download_id] = {
                'status': 'processing', 'percent': 100, 'speed': '', 'error': None}

    error_msg = ''
    quality_label = str(quality or '')
    try:
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'progress_hooks': [progress_hook], 'ignoreerrors': True,
            'no_check_certificate': True, 'prefer_insecure': True,
        }
        ydl_opts.update(_speed_opts())
        _ck = _yt_cookies_path()
        if _ck:
            ydl_opts['cookiefile'] = _ck
        if 0 < _client_idx < len(_YT_CLIENTS):
            ydl_opts['extractor_args'] = {'youtube': {'player_client': [_YT_CLIENTS[_client_idx]]}}

        # Clip download (Update 8): only a section of the video, via ffmpeg
        if clip_start is not None and clip_end is not None:
            try:
                from yt_dlp.utils import download_range_func
                ydl_opts['download_ranges'] = download_range_func(
                    None, [(float(clip_start), float(clip_end))])
                ydl_opts['force_keyframes_at_cuts'] = True
            except Exception:
                pass

        if format_type == 'mp3':
            bitrate = '192'
            if quality:
                q = str(quality).lower().replace('k', '')
                if q in ('70', '128', '160', '320'):
                    bitrate = q
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio',
                                           'preferredcodec': 'mp3',
                                           'preferredquality': bitrate}]
            quality_label = f"MP3 {bitrate}K"
        elif format_type == 'm4a':
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio',
                                           'preferredcodec': 'm4a',
                                           'preferredquality': '128'}]
            quality_label = 'M4A 128K'
        elif quality == '3gp':
            # Smallest format - feature-phone (button mobile) friendly 3GP.
            # Many videos have no combined low format, so merged fallbacks are
            # included, and the result is converted to a real .3gp file.
            ydl_opts['format'] = ('17/worst[ext=3gp]/worstvideo[height<=176]+worstaudio/'
                                  'worstvideo+worstaudio/best')
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor',
                                           'preferedformat': '3gp'}]
            quality_label = '3GP (Lowest)'
        else:
            if quality and quality != 'best':
                height = str(quality).replace('p', '')
                ydl_opts['format'] = (
                    f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/'
                    f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/'
                    f'bestvideo+bestaudio/best')
                quality_label = quality
            else:
                ydl_opts['format'] = 'best[ext=mp4]/bestvideo+bestaudio/best'
                quality_label = 'Best'
            ydl_opts['merge_output_format'] = 'mp4'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            if not info:
                # ignoreerrors ki wajah se bot-block par exception nahi
                # banta, info None reh jata hai — agle client se retry
                # karo, warna asal wajah batao (Update 40)
                if _client_idx < len(_YT_CLIENTS) - 1:
                    print(f"[Playza] Empty extraction on download {download_id} - retry with client #{_client_idx + 1}")
                    download_progress[download_id] = {'status': 'starting', 'percent': 0,
                                                      'speed': '', 'error': None}
                    return download_in_background(video_id, format_type, quality, download_id,
                                                  user_id, clip_start, clip_end,
                                                  _client_idx + 1, title_hint, _retry_pass)
                error_msg = 'YouTube bot-check: is server se download roka gaya - kuch der baad dobara try karein'
            if info:
                title = sanitize_filename(info.get('title', 'video'))
                file_path = None

                # Most reliable: the filepath yt-dlp actually produced
                try:
                    req = info.get('requested_downloads') or []
                    if req and req[0].get('filepath') and os.path.exists(req[0]['filepath']):
                        file_path = req[0]['filepath']
                except Exception:
                    file_path = None

                if not file_path:
                    # Tay-shuda naam (outtmpl title-based hai) se dhoondo
                    try:
                        _exp = ydl.prepare_filename(info)
                        _base = os.path.splitext(_exp)[0]
                        for _e2 in ('.mp4', '.mkv', '.webm', '.3gp',
                                    '.mp3', '.m4a'):
                            _c = _base + _e2
                            if os.path.exists(_c) and os.path.getsize(_c) > 0:
                                file_path = _c
                                break
                    except Exception:
                        file_path = None
                if not file_path:
                    # Aakhri sahara: sirf WAHI file jis ka naam is video ke
                    # title se BILKUL milta ho aur jo is download ke shuru
                    # hone ke baad bani ho. Folder ki sab se nayi file utha
                    # lena (purana tareeqa) dusri download ki file is video
                    # ke naam par save kar deta tha — wahi asal bug tha.
                    exts = ('.mp3', '.m4a') if format_type in ('mp3', 'm4a') else \
                           ('.mp4', '.mkv', '.webm', '.3gp')
                    _want = re.sub(r'[^a-z0-9]+', '', (title or '').lower())
                    if _want:
                        for _f in os.listdir(download_dir):
                            if not _f.endswith(exts):
                                continue
                            _stem = os.path.splitext(_f)[0]
                            if re.sub(r'[^a-z0-9]+', '', _stem.lower()) != _want:
                                continue
                            _fp = os.path.join(download_dir, _f)
                            try:
                                if os.path.getmtime(_fp) >= started_at - 5 \
                                        and os.path.getsize(_fp) > 0:
                                    file_path = _fp
                                    break
                            except Exception:
                                pass

                # 3GP fallback: if conversion did not produce a .3gp, do it
                # directly with ffmpeg (h263 + aac, 176px wide - feature phones)
                if quality == '3gp' and file_path and os.path.exists(file_path) \
                        and not file_path.lower().endswith('.3gp'):
                    try:
                        target = os.path.splitext(file_path)[0] + '.3gp'
                        r = subprocess.run(
                            ['ffmpeg', '-y', '-i', file_path, '-vf', 'scale=176:144',
                             '-r', '15', '-vcodec', 'h263', '-acodec', 'aac',
                             '-ar', '8000', '-ac', '1', target],
                            capture_output=True, timeout=600)
                        if r.returncode == 0 and os.path.exists(target) \
                                and os.path.getsize(target) > 0:
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                            file_path = target
                    except Exception:
                        pass

                if file_path and os.path.exists(file_path) \
                        and os.path.getsize(file_path) <= 0:
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                    file_path = None
                    _dl_error_hint = ('Khali file aayi (0 byte) - '
                                      'dobara try karein')
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    elapsed = max(time.time() - started_at, 0.01)
                    avg_mbps = (file_size / (1024 * 1024)) / elapsed

                    downloaded_files[download_id] = {
                        'downloadId': download_id, 'videoId': video_id, 'title': title,
                        'format': format_type.upper(), 'quality': quality_label,
                        'file_path': file_path, 'file_size': file_size,
                        'status': 'completed', 'timestamp': datetime.now().isoformat(),
                        'download_seconds': round(elapsed, 2),
                        'avg_speed_mbps': round(avg_mbps, 2)
                    }
                    save_downloads_db()

                    # Update 44: guest ki ginti sirf complete hone par
                    _gd = guest_pending.pop(download_id, None)
                    if _gd:
                        _guest_inc(_gd)

                    download_progress[download_id] = {
                        'status': 'completed', 'percent': 100, 'speed': '',
                        'error': None, 'file_path': file_path, 'title': title,
                        'format': format_type, 'quality': quality_label,
                        'file_size': file_size,
                        'download_seconds': round(elapsed, 2),
                        'avg_speed_mbps': round(avg_mbps, 2)
                    }
                    return
                error_msg = (_dl_error_hint if '_dl_error_hint' in locals()
                             else 'Download failed - no file produced')
    except Exception as e:
        if download_control.get(download_id, {}).get('deleted'):
            download_progress.pop(download_id, None)
            download_control.pop(download_id, None)
            if download_id in download_meta:
                del download_meta[download_id]
                _save_download_meta()
            return
        if download_control.get(download_id, {}).get('cancel'):
            _pp = download_progress.get(download_id, {})
            download_progress[download_id] = {'status': 'paused',
                                              'percent': _pp.get('percent', 0),
                                              'speed': '', 'error': None}
            return
        if (_is_bot_block(e) or 'timed out' in str(e).lower()
                or 'urlopen error' in str(e).lower()
                or 'connection' in str(e).lower()) \
                and _client_idx < len(_YT_CLIENTS) - 1:
            print(f"[Playza] Bot-block on download {download_id} - retry with client #{_client_idx + 1}")
            download_progress[download_id] = {'status': 'starting', 'percent': 0,
                                              'speed': '', 'error': None}
            return download_in_background(video_id, format_type, quality, download_id,
                                          user_id, clip_start, clip_end,
                                          _client_idx + 1, title_hint, _retry_pass)
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))

    if download_control.get(download_id, {}).get('deleted'):
        download_progress.pop(download_id, None)
        download_control.pop(download_id, None)
        if download_id in download_meta:
            del download_meta[download_id]
            _save_download_meta()
        return
    if download_control.get(download_id, {}).get('cancel'):
        _pp = download_progress.get(download_id, {})
        download_progress[download_id] = {'status': 'paused',
                                          'percent': _pp.get('percent', 0),
                                          'speed': '', 'error': None}
        return

    # Bot-block par saare clients fail ho jayein to ek akhri koshish:
    # thodi dair ruk kar pehle client se dobara (Update 41 — fail na ho)
    if _retry_pass < 2 and ('bot-check' in error_msg or _is_bot_block(error_msg)):
        download_progress[download_id] = {'status': 'starting', 'percent': 0,
                                          'speed': '', 'error': None}
        time.sleep(15 if _retry_pass == 0 else 30)
        return download_in_background(video_id, format_type, quality, download_id,
                                      user_id, clip_start, clip_end, 0, title_hint,
                                      _retry_pass + 1)

    # Friendly errors
    if not error_msg:
        error_msg = 'Download fail ho gaya - dobara try karein'
    if 'bot-check' in error_msg or 'Sign in to confirm' in error_msg:
        error_msg = 'YouTube bot-check: is server se download roka gaya - kuch der baad dobara try karein'
    elif 'Video unavailable' in error_msg:
        error_msg = 'Video unavailable'
    elif 'Private video' in error_msg:
        error_msg = 'Private video'
    elif 'Sign in' in error_msg:
        error_msg = 'Login required'
    elif 'age' in error_msg.lower():
        error_msg = 'Age-restricted'
    elif 'copyright' in error_msg.lower():
        error_msg = 'Copyright issue'
    elif 'region' in error_msg.lower():
        error_msg = 'Not available in your region'
    elif 'network' in error_msg.lower():
        error_msg = 'Network error - try again'
    elif 'ffmpeg' in error_msg.lower():
        error_msg = 'Processing error'

    # Unified registry (Bug #3): failed downloads bhi usi store me jate
    # hain jahan se Downloads page padhta hai.
    if download_id not in downloaded_files:
        _meta = download_meta.get(download_id, {})
        downloaded_files[download_id] = {
            'downloadId': download_id, 'videoId': video_id,
            'title': _meta.get('title') or video_id,
            'format': (format_type or '').upper(), 'quality': quality_label,
            'file_path': None, 'file_size': 0, 'status': 'failed',
            'error': error_msg[:150], 'timestamp': datetime.now().isoformat(),
            'user_id': user_id}
        save_downloads_db()

    guest_pending.pop(download_id, None)
    download_progress[download_id] = {
        'status': 'error',
        'percent': 0,
        'speed': '',
        'error': error_msg[:150]
    }

# Playlist Download
# ============ DOWNLOAD PAUSE / RESUME (v4) ============
@app.route('/api/cancel-download/<download_id>', methods=['POST'])
def cancel_download(download_id):
    download_control[download_id] = {'cancel': True}
    _st = download_progress.get(download_id, {})
    download_progress[download_id] = {'status': 'paused',
                                      'percent': _st.get('percent', 0),
                                      'speed': '', 'error': None}
    return jsonify({'success': True})


@app.route('/api/resume-download/<download_id>', methods=['POST'])
def resume_download(download_id):
    if not feature_enabled('downloads_enabled'):
        return jsonify({'error': 'Downloads abhi band hain (admin ne off kiya hai)',
                        'downloads_disabled': True}), 403
    meta = download_meta.get(download_id) or _load_download_meta().get(download_id)
    if not meta:
        return jsonify({'error': 'Download ki info nahi mili - dobara start karein'}), 404
    download_control.pop(download_id, None)
    download_progress[download_id] = {'status': 'starting', 'percent': 0,
                                      'speed': '', 'error': None}
    th = threading.Thread(target=download_in_background,
                          args=(meta.get('video_id'), meta.get('format_type'),
                                meta.get('quality'), download_id, session.get('user_id'),
                                meta.get('clip_start'), meta.get('clip_end')),
                          kwargs={'title_hint': meta.get('title')})
    th.daemon = True
    th.start()
    return jsonify({'success': True})



@app.route('/api/restart-download/<download_id>', methods=['POST'])
def restart_download(download_id):
    """v9: ruki/atki hui download ko naye sire se dobara start karna."""
    if not feature_enabled('downloads_enabled'):
        return jsonify({'error': 'Downloads abhi band hain (admin ne off kiya hai)',
                        'downloads_disabled': True}), 403
    meta = download_meta.get(download_id) or _load_download_meta().get(download_id)
    if not meta or not meta.get('video_id'):
        return jsonify({'error': 'Download ki info nahi mili'}), 404
    download_control[download_id] = {'cancel': True, 'deleted': True}
    download_progress.pop(download_id, None)
    new_id = f"{meta['video_id']}_{int(time.time())}"
    download_progress[new_id] = {'status': 'starting', 'percent': 0,
                                 'speed': '', 'error': None}
    download_meta[new_id] = {'video_id': meta['video_id'],
                             'format_type': meta.get('format_type'),
                             'quality': meta.get('quality'),
                             'clip_start': meta.get('clip_start'),
                             'clip_end': meta.get('clip_end'),
                             'title': meta.get('title', '')}
    _save_download_meta()

    def _go():
        time.sleep(2)
        download_in_background(meta['video_id'], meta.get('format_type'),
                               meta.get('quality'), new_id,
                               session.get('user_id'), meta.get('clip_start'),
                               meta.get('clip_end'), 0, meta.get('title'))
    th = threading.Thread(target=_go)
    th.daemon = True
    th.start()
    return jsonify({'success': True, 'download_id': new_id})

@app.route('/api/download-playlist', methods=['POST'])
def download_playlist():
    data = request.json or {}
    playlist_url = data.get('playlist_url')
    format_type = data.get('format', 'mp3')
    # Range selection (Update 8): 1-based item range inside the playlist
    start_index = data.get('start_index')
    end_index = data.get('end_index')

    # ============ PREMIUM CHECK ============
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Login required for playlist download!', 'login_required': True}), 403

    if not is_premium_user(user_id):
        return jsonify({
            'error': 'Playlist download is a Premium feature! Upgrade to Premium.',
            'premium_required': True
        }), 403
    if not playlist_url:
        return jsonify({"error": "Playlist URL is required"}), 400

    download_id = f"playlist_{int(time.time())}_{random.randint(1000, 9999)}"
    download_progress[download_id] = {
        'status': 'starting', 'percent': 0, 'speed': '',
        'error': None, 'format': format_type, 'type': 'playlist'
    }

    thread = threading.Thread(target=download_playlist_in_background,
                            args=(playlist_url, format_type, download_id,
                                  start_index, end_index))
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "download_id": download_id})


def download_playlist_in_background(playlist_url, format_type, download_id,
                                    start_index=None, end_index=None):
    try:
        download_dir = MP3_DIR if format_type == 'mp3' else MP4_DIR

        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                percent = int((downloaded / total) * 100) if total > 0 else 0
                speed = d.get('speed', 0)
                speed_str = format_speed(speed) if speed else ''

                download_progress[download_id] = {
                    'status': 'downloading', 'percent': percent, 'speed': speed_str,
                    'error': None, 'format': format_type, 'type': 'playlist'
                }

        ydl_opts = {
            'format': 'bestaudio/best' if format_type == 'mp3' else 'best[ext=mp4]/bestvideo+bestaudio/best',
            'outtmpl': os.path.join(download_dir, '%(playlist_title)s/%(title)s.%(ext)s'),
            'quiet': True, 'no_warnings': True,
            'progress_hooks': [progress_hook],
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
        }
        ydl_opts.update(_speed_opts())
        if start_index:
            ydl_opts['playliststart'] = int(start_index)
        if end_index:
            ydl_opts['playlistend'] = int(end_index)

        if format_type == 'mp3':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=True)

            if info:
                playlist_title = sanitize_filename(info.get('title', 'Playlist'))
                download_progress[download_id] = {
                    'status': 'completed', 'percent': 100, 'speed': '',
                    'error': None, 'title': playlist_title,
                    'format': format_type, 'type': 'playlist'
                }
    except Exception as e:
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
        download_progress[download_id] = {
            'status': 'error', 'percent': 0, 'speed': '',
            'error': error_msg, 'format': format_type, 'type': 'playlist'
        }

# Batch Download
@app.route('/api/batch-download', methods=['POST'])
def batch_download_videos():
    data = request.json
    video_ids = data.get('video_ids', [])
    format_type = data.get('format', 'mp3')
    
    # ============ PREMIUM CHECK ============
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Login required for batch download!', 'login_required': True}), 403
    
    if not is_premium_user(user_id):
        return jsonify({
            'error': 'Batch download is a Premium feature! Upgrade to Premium.',
            'premium_required': True
        }), 403 
    if not video_ids:
        return jsonify({"error": "No video IDs provided"}), 400
    
    batch_id = f"batch_{int(time.time())}_{random.randint(1000, 9999)}"
    download_progress[batch_id] = {
        'status': 'starting', 'percent': 0, 'speed': '',
        'error': None, 'total': len(video_ids), 'completed': 0,
        'type': 'batch'
    }
    
    thread = threading.Thread(target=batch_download_in_background, 
                            args=(video_ids, format_type, batch_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "batch_id": batch_id})

def batch_download_in_background(video_ids, format_type, batch_id):
    total = len(video_ids)
    completed = 0
    
    for video_id in video_ids:
        try:
            download_id = f"{batch_id}_{video_id}"
            download_in_background(video_id, format_type, None, download_id)
            
            while True:
                progress = download_progress.get(download_id, {})
                if progress.get('status') in ['completed', 'error']:
                    break
                time.sleep(1)
            
            if progress.get('status') == 'completed':
                completed += 1
            
            download_progress[batch_id] = {
                'status': 'downloading', 
                'percent': int((completed / total) * 100),
                'completed': completed,
                'total': total,
                'error': None,
                'type': 'batch'
            }
        except Exception as e:
            pass
    
    download_progress[batch_id] = {
        'status': 'completed', 
        'percent': 100,
        'completed': completed,
        'total': total,
        'error': None,
        'type': 'batch'
    }

# Video Info API
@app.route('/api/video-info/<video_id>')
def get_video_details(video_id):
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            return jsonify({
                "title": info.get('title', ''),
                "duration": info.get('duration', 0),
                "view_count": info.get('view_count', 0),
                "like_count": info.get('like_count', 0),
                "uploader": info.get('uploader', ''),
                "upload_date": info.get('upload_date', ''),
                "description": info.get('description', '')[:500],
                "thumbnail": info.get('thumbnail', ''),
                "categories": info.get('categories', []),
                "tags": info.get('tags', [])[:10],
                "formats": [
                    {
                        "format_id": f.get('format_id', ''),
                        "ext": f.get('ext', ''),
                        "resolution": f.get('resolution', ''),
                        "filesize": f.get('filesize', 0),
                        "format_note": f.get('format_note', '')
                    }
                    for f in info.get('formats', [])[:20]
                ]
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Thumbnail Download
@app.route('/api/download-thumbnail/<video_id>')
def download_thumbnail(video_id):
    qualities = ['maxresdefault', 'sddefault', 'hqdefault', 'mqdefault', 'default']
    
    for quality in qualities:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        try:
            response = requests.get(thumbnail_url, timeout=5)
            if response.status_code == 200 and len(response.content) > 1000:
                file_path = os.path.join(THUMBNAIL_DIR, f"{video_id}_{quality}.jpg")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                return send_file(file_path, as_attachment=True, download_name=f"{video_id}_{quality}.jpg")
        except:
            continue
    
    return jsonify({"error": "Thumbnail not found"}), 404

# Subtitle Download
@app.route('/api/download-subtitles', methods=['POST'])
def download_subtitles():
    data = request.json
    video_id = data.get('video_id')
    lang = data.get('lang', 'en')
    
    if not video_id:
        return jsonify({"error": "Video ID is required"}), 400
    
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'quiet': True, 'no_warnings': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang],
            'subtitlesformat': 'srt',
        }
        
        # Client rotation ke sath (bot-block par dusra tareeqa — Update 45)
        info = _extract_with_clients(youtube_url, ydl_opts)
        if info:
            subtitles = info.get('subtitles', {}).get(lang, [])
            auto_subtitles = info.get('automatic_captions', {}).get(lang, [])

            all_subtitles = subtitles + auto_subtitles
            if all_subtitles:
                sub_url = all_subtitles[0].get('url', '')
                if sub_url:
                    response = requests.get(sub_url, timeout=15)
                    if response.status_code == 200:
                        file_path = os.path.join(SUBTITLE_DIR, f"{video_id}_{lang}.srt")
                        with open(file_path, 'wb') as f:
                            f.write(response.content)

                        return send_file(file_path, as_attachment=True, download_name=f"{video_id}_{lang}.srt")

            return jsonify({"error": "No subtitles found for this language"}), 404
        return jsonify({"error": "Video ki maloomat nahi mil sakin — dobara try karein"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Channel Info API
@app.route('/api/channel-info/<channel_id>')
def get_channel_details(channel_id):
    try:
        channel_url = f"https://www.youtube.com/channel/{channel_id}"
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            return jsonify({
                "channel_name": info.get('channel', info.get('uploader', '')),
                "channel_url": info.get('channel_url', ''),
                "description": info.get('description', ''),
                "subscriber_count": info.get('channel_follower_count', 0),
                "video_count": len(info.get('entries', [])),
                "videos": [
                    {
                        "id": entry.get('id', ''),
                        "title": entry.get('title', ''),
                        "thumbnail": entry.get('thumbnail', '')
                    }
                    for entry in info.get('entries', [])[:30]
                ]
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# File Management APIs
@app.route('/api/files')
def list_files():
    files = []
    for root, dirs, filenames in os.walk(DOWNLOAD_DIR):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files.append({
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            })
    
    return jsonify({"files": files})

@app.route('/api/open-folder')
def open_download_folder():
    try:
        if os.name == 'nt':
            os.startfile(DOWNLOAD_DIR)
        elif os.name == 'posix':
            if sys.platform == 'darwin':
                subprocess.run(['open', DOWNLOAD_DIR])
            else:
                subprocess.run(['xdg-open', DOWNLOAD_DIR])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Stats API
@app.route('/api/stats')
def get_stats():
    total_downloads = len(downloaded_files)
    total_size = sum(info.get('file_size', 0) for info in downloaded_files.values())
    
    format_stats = {}
    for info in downloaded_files.values():
        fmt = info.get('format', 'unknown')
        format_stats[fmt] = format_stats.get(fmt, 0) + 1
    
    platform_stats = {}
    for info in downloaded_files.values():
        platform = info.get('platform', 'YouTube')
        platform_stats[platform] = platform_stats.get(platform, 0) + 1
    
    return jsonify({
        "total_downloads": total_downloads,
        "total_size": total_size,
        "format_stats": format_stats,
        "platform_stats": platform_stats
    })

# Watch History APIs
@app.route('/api/add-history', methods=['POST'])
def add_to_history():
    data = request.json
    video_id = data.get('video_id')
    title = data.get('title', '')
    channel = data.get('channel', '')
    
    if not video_id:
        return jsonify({"error": "Video ID is required"}), 400
    
    history_entry = {
        'video_id': video_id,
        'title': title,
        'channel': channel,
        'timestamp': datetime.now().isoformat()
    }
    
    watch_history.insert(0, history_entry)
    
    if len(watch_history) > 100:
        watch_history.pop()
    
    return jsonify({"success": True})

@app.route('/api/history')
def get_history():
    return jsonify({"history": watch_history})

@app.route('/api/clear-history', methods=['DELETE'])
def clear_history():
    watch_history.clear()
    return jsonify({"success": True, "message": "History cleared!"})

@app.route('/api/download-progress')
def get_download_progress():
    merged = {}
    for _did, _st in download_progress.items():
        _m = dict(download_meta.get(_did, {}))
        _m.update(_st or {})
        merged[_did] = _m
    return jsonify(merged)

@app.route('/api/download-file/<download_id>')
def download_file(download_id):
    if download_id in downloaded_files:
        file_path = downloaded_files[download_id].get('file_path')
    else:
        progress = download_progress.get(download_id)
        file_path = progress.get('file_path') if progress else None
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    filename = os.path.basename(file_path)
    # v16: save hone wali file ka naam hamesha ORIGINAL YouTube title ho
    # (pehle ai_job_... jese andar ke naam ate thay).
    _rec = downloaded_files.get(download_id) or {}
    _ttl = (_rec.get('title') or '').strip()
    if _ttl:
        _clean = re.sub(r'[\\/:*?"<>|\n\r\t]', ' ', _ttl)
        _clean = re.sub(r'\s+', ' ', _clean).strip()[:100].strip()
        if _clean:
            filename = _clean + os.path.splitext(file_path)[1]

    # Update 57: ?play=1 par file browser/app ke andar PLAY hoti hai
    # (inline + asal video/audio type) — dobara download nahi hoti.
    if request.args.get('play'):
        _ext = os.path.splitext(file_path)[1].lower()
        _mt = {'.mp4': 'video/mp4', '.3gp': 'video/3gpp',
               '.mkv': 'video/x-matroska', '.webm': 'video/webm',
               '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4'}.get(
                   _ext, 'application/octet-stream')
        try:
            return send_file(file_path, as_attachment=False,
                             download_name=filename, mimetype=_mt)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    try:
        return send_file(file_path, as_attachment=True, download_name=filename, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ APNA PLAYER STREAM (Update 59) ============
_stream_cache = {}
_stream_qcache = {}
_stream_fail_until = 0.0


def _combined_formats(info):
    """{height: url} — sirf combined (awaz+video ek sath) formats,
    har height par mp4 ko tarjeeh. Player ki quality settings ke liye."""
    best = {}
    for f in (info.get('formats') or []):
        if not f.get('url'):
            continue
        if f.get('vcodec') in (None, 'none') or f.get('acodec') in (None, 'none'):
            continue
        h = f.get('height') or 0
        if not h:
            continue
        mp = 1 if f.get('ext') == 'mp4' else 0
        if h not in best or mp > best[h][0]:
            best[h] = (mp, f['url'])
    return {h: u for h, (mp, u) in best.items()}


def _pick_combined_url(info):
    """Update 70: halki quality pehle (<=480p, mp4 tarjeeh) taake slow
    internet par bhi play foran shuru ho; na mile to <=720p."""
    best_low = None
    best_any = None
    for f in (info.get('formats') or []):
        if not f.get('url'):
            continue
        if f.get('vcodec') in (None, 'none') or f.get('acodec') in (None, 'none'):
            continue
        h = f.get('height') or 0
        if h > 720:
            continue
        score = (1 if f.get('ext') == 'mp4' else 0, h)
        if best_any is None or score > best_any[0]:
            best_any = (score, f['url'])
        if h <= 480 and (best_low is None or score > best_low[0]):
            best_low = (score, f['url'])
    pick = best_low or best_any
    return pick[1] if pick else None


def _resolve_stream_url(video_id, height=None):
    """Watch ke liye seedha play URL. Har player client ko bari bari
    azmata hai aur usi ka result leta hai jis mein audio+video wala
    (combined) format mile — taake video awaz ke sath chale.
    Result 30 min cache — googlevideo links expire hote hain."""
    global _stream_fail_until
    _key = video_id if not height else f'{video_id}@{height}'
    _c = _stream_cache.get(_key)
    if _c and time.time() - _c[1] < 1800:
        return _c[0]
    if time.time() < _stream_fail_until:
        return None
    watch_url = 'https://www.youtube.com/watch?v=' + video_id
    fallback = None
    closest = None
    for _client in _YT_CLIENTS:
        try:
            _opts = _ydl_opts_with_client(
                {'quiet': True, 'no_warnings': True, 'skip_download': True},
                _client)
            with yt_dlp.YoutubeDL(_opts) as _ydl:
                _info = _ydl.extract_info(watch_url, download=False)
        except Exception:
            continue
        if not _info:
            continue
        if height:
            _fmts = _combined_formats(_info)
            if height in _fmts:
                _stream_cache[_key] = (_fmts[height], time.time())
                _stream_fail_until = 0.0
                return _fmts[height]
            if _fmts and closest is None:
                _hs = sorted(_fmts)
                _lower = [h for h in _hs if h < height]
                closest = _fmts[_lower[-1] if _lower else _hs[0]]
        else:
            _u = _pick_combined_url(_info)
            if _u:
                _stream_cache[_key] = (_u, time.time())
                return _u
        if fallback is None and _info.get('url'):
            fallback = _info['url']
    if height and closest:
        _stream_cache[_key] = (closest, time.time())
        _stream_fail_until = 0.0
        return closest
    if fallback:
        _stream_cache[_key] = (fallback, time.time())
        _stream_fail_until = 0.0
    else:
        # Saare clients fail — 2 min ke liye foran fail, taake player
        # har video par 8 second na latke (backup player foran khule).
        _stream_fail_until = time.time() + 120
    return fallback


@app.route('/api/stream/<video_id>')
def api_stream(video_id):
    """Playza ke apne player ke liye video stream — server se hokar
    jati hai, Range support ke sath taake seek chal sake."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', video_id or ''):
        return jsonify({'error': 'bad id'}), 400
    try:
        url = _resolve_stream_url(video_id, request.args.get('q', type=int))
    except Exception:
        url = None
    if not url:
        return jsonify({'error': 'stream nahi mila'}), 503
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/124.0 Safari/537.36'}
    rng = request.headers.get('Range')
    if rng:
        headers['Range'] = rng
    try:
        up = requests.get(url, headers=headers, stream=True, timeout=30)
    except Exception:
        return jsonify({'error': 'stream fail'}), 502
    if up.status_code not in (200, 206):
        try:
            up.close()
        except Exception:
            pass
        return jsonify({'error': 'stream fail'}), 502
    resp_headers = {'Content-Type': up.headers.get('Content-Type', 'video/mp4'),
                    'Accept-Ranges': 'bytes'}
    for _h in ('Content-Length', 'Content-Range'):
        if up.headers.get(_h):
            resp_headers[_h] = up.headers[_h]

    def _gen():
        try:
            for chunk in up.iter_content(chunk_size=256 * 1024):
                if chunk:
                    yield chunk
        finally:
            try:
                up.close()
            except Exception:
                pass

    return Response(stream_with_context(_gen()), status=up.status_code,
                    headers=resp_headers)

@app.route('/api/stream-qualities/<video_id>')
def api_stream_qualities(video_id):
    """Update 73: player ki settings ke liye is video ki asal combined
    qualities (jo seedha awaz ke sath play ho sakti hain)."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', video_id or ''):
        return jsonify({'error': 'bad id'}), 400
    _qc = _stream_qcache.get(video_id)
    if _qc and time.time() - _qc[1] < 1800:
        return jsonify({'qualities': _qc[0]})
    watch_url = 'https://www.youtube.com/watch?v=' + video_id
    _hset = set()
    for _client in _YT_CLIENTS:
        try:
            _opts = _ydl_opts_with_client(
                {'quiet': True, 'no_warnings': True, 'skip_download': True},
                _client)
            with yt_dlp.YoutubeDL(_opts) as _ydl:
                _info = _ydl.extract_info(watch_url, download=False)
        except Exception:
            continue
        if not _info:
            continue
        _hset.update(_combined_formats(_info).keys())
        if len(_hset) >= 6:
            break
    heights = sorted(_hset)
    out = [{'height': h,
            'label': (str(h) + 'p' + (' HD' if h >= 720 else ''))}
           for h in heights]
    if out:
        _stream_qcache[video_id] = (out, time.time())
    return jsonify({'qualities': out})


@app.route('/api/downloads-list')
def get_downloads_list():
    # Update 45: Private Folder — private downloads aam list me nahi,
    # sirf PIN khulne par scope=private me milti hain
    scope = request.args.get('scope')
    if scope == 'private' and not session.get('pt_private'):
        return jsonify({"downloads": [], "locked": True})
    downloads = []
    for download_id, info in downloaded_files.items():
        is_priv = bool(info.get('private'))
        if scope == 'private' and not is_priv:
            continue
        if scope != 'private' and is_priv:
            continue
        downloads.append({
            'downloadId': download_id,
            'videoId': info.get('videoId', ''),
            'title': info.get('title', 'Unknown'),
            'format': info.get('format', 'unknown').upper(),
            'quality': info.get('quality', 'Best'),
            'platform': info.get('platform', 'YouTube'),
            'status': info.get('status', 'completed'),
            'error': info.get('error'),
            'private': is_priv,
            'file_size': info.get('file_size', 0),
            'timestamp': info.get('timestamp', datetime.now().isoformat())
        })

    downloads.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return jsonify({"downloads": downloads})


@app.route('/api/private/status')
def api_private_status():
    return jsonify({'pin_set': bool(load_site_settings().get('private_pin_hash')),
                    'unlocked': bool(session.get('pt_private'))})


@app.route('/api/private/set-pin', methods=['POST'])
def api_private_set_pin():
    pin = str((request.json or {}).get('pin') or '').strip()
    if not (pin.isdigit() and 4 <= len(pin) <= 6):
        return jsonify({'error': 'PIN 4 se 6 numbers ka hona chahiye'}), 400
    settings = load_site_settings()
    if settings.get('private_pin_hash'):
        return jsonify({'error': 'PIN pehle se set hai'}), 400
    import hashlib
    settings['private_pin_hash'] = hashlib.sha256(pin.encode()).hexdigest()
    save_site_settings(settings)
    session['pt_private'] = True
    return jsonify({'success': True})


@app.route('/api/private/verify', methods=['POST'])
def api_private_verify():
    pin = str((request.json or {}).get('pin') or '').strip()
    import hashlib
    want = load_site_settings().get('private_pin_hash')
    if want and hashlib.sha256(pin.encode()).hexdigest() == want:
        session['pt_private'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Galat PIN'}), 403


@app.route('/api/private/lock', methods=['POST'])
def api_private_lock():
    session.pop('pt_private', None)
    return jsonify({'success': True})


def _compress_worker(download_id, cmp_id):
    """Smart compression (Update 45): resolution/quality wohi, size kam."""
    rec = downloaded_files.get(download_id) or {}
    src = rec.get('file_path')
    label = (rec.get('title') or 'Video') + ' (Chhoti)'
    try:
        if not src or not os.path.exists(src):
            download_progress[cmp_id] = {'status': 'error', 'percent': 0,
                                         'speed': '', 'error': 'File nahi mili'}
            return
        base = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(MP4_DIR, base + ' (Chhoti).mp4')
        dur = 0.0
        try:
            pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                 'format=duration', '-of', 'csv=p=0', src],
                                capture_output=True, text=True, timeout=30)
            dur = float((pr.stdout or '0').strip() or 0)
        except Exception:
            dur = 0.0
        download_progress[cmp_id] = {'status': 'processing', 'percent': 0,
                                     'speed': '', 'error': None,
                                     'title': label,
                                     'video_id': rec.get('videoId', '')}
        cmd = ['ffmpeg', '-y', '-i', src, '-c:v', 'libx264', '-crf', '27',
               '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '96k',
               '-movflags', '+faststart', '-progress', 'pipe:1',
               '-nostats', out]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True)
        for line in p.stdout:
            if line.startswith('out_time_ms=') and dur > 0:
                try:
                    ms = int(line.strip().split('=')[1])
                    download_progress[cmp_id] = {
                        'status': 'processing',
                        'percent': min(99, int((ms / 1000000.0) / dur * 100)),
                        'speed': '', 'error': None, 'title': label,
                        'video_id': rec.get('videoId', '')}
                except Exception:
                    pass
        p.wait()
        if p.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            new_size = os.path.getsize(out)
            downloaded_files[cmp_id] = {
                'downloadId': cmp_id, 'videoId': rec.get('videoId', ''),
                'title': label, 'format': 'MP4',
                'quality': rec.get('quality', 'Best'), 'file_path': out,
                'file_size': new_size, 'status': 'completed',
                'timestamp': datetime.now().isoformat()}
            save_downloads_db()
            download_progress[cmp_id] = {
                'status': 'completed', 'percent': 100, 'speed': '',
                'error': None, 'file_path': out, 'title': label,
                'format': 'mp4', 'quality': rec.get('quality', 'Best'),
                'file_size': new_size}
        else:
            download_progress[cmp_id] = {'status': 'error', 'percent': 0,
                                         'speed': '',
                                         'error': 'Compress nahi ho saka'}
    except Exception as e:
        download_progress[cmp_id] = {'status': 'error', 'percent': 0,
                                     'speed': '',
                                     'error': (str(e) or 'Compress error')[:120]}


@app.route('/api/compress', methods=['POST'])
def api_compress():
    data = request.json or {}
    did = data.get('download_id')
    rec = downloaded_files.get(did)
    if not rec or rec.get('status') != 'completed' or not rec.get('file_path'):
        return jsonify({'error': 'Sirf mukammal downloads compress hoti hain'}), 400
    if str(rec.get('format', '')).upper() not in ('MP4', 'MKV', 'WEBM', '3GP'):
        return jsonify({'error': 'Ye sirf videos ke liye hai'}), 400
    cmp_id = f"cmp_{int(time.time())}_{random.randint(100, 999)}"
    download_progress[cmp_id] = {'status': 'processing', 'percent': 0,
                                 'speed': '', 'error': None,
                                 'title': (rec.get('title') or 'Video') + ' (Chhoti)',
                                 'video_id': rec.get('videoId', '')}
    th = threading.Thread(target=_compress_worker, args=(did, cmp_id))
    th.daemon = True
    th.start()
    return jsonify({'success': True, 'compress_id': cmp_id})


@app.route('/api/downloads/private', methods=['POST'])
def api_downloads_private():
    data = request.json or {}
    did = data.get('download_id')
    make = bool(data.get('private'))
    if did not in downloaded_files:
        return jsonify({'error': 'Download nahi mili'}), 404
    if not make and not session.get('pt_private'):
        return jsonify({'error': 'Private se nikalne ke liye pehle PIN kholein',
                        'locked': True}), 403
    downloaded_files[did]['private'] = make
    save_downloads_db()
    return jsonify({'success': True})

@app.route('/api/delete-download/<download_id>', methods=['DELETE'])
def delete_download(download_id):
    # Update 69: chalti hui (downloading/paused) download bhi delete —
    # cancel+deleted flag se thread ruk jata hai, progress/meta aur
    # aadhi (.part) file bhi saaf hoti hai.
    _prog = download_progress.get(download_id) or {}
    _partfile = _prog.get('filename')
    if download_id in download_progress or download_id in download_meta:
        download_control[download_id] = {'cancel': True, 'deleted': True}
        download_progress.pop(download_id, None)
        if download_id in download_meta:
            del download_meta[download_id]
            _save_download_meta()
    if _partfile:
        import glob as _glob
        try:
            for _pf in _glob.glob(_glob.escape(_partfile) + '.part*'):
                try:
                    os.remove(_pf)
                except Exception:
                    pass
        except Exception:
            pass
    file_path = None

    if download_id in downloaded_files:
        file_path = downloaded_files[download_id].get('file_path')
        del downloaded_files[download_id]
        save_downloads_db()
    
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass
    
    return jsonify({"success": True})
    # ============ REMEMBER ME ============
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
# ============ FORGOT PASSWORD ============
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Update 22: Gmail par reset code bhejo (purana temporary-password
    wala tareeqa — jo password response me wapas bhejta tha — khatam)."""
    data = request.json or {}
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'error': 'Email required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Email not found!'}), 404

    code = str(random.randint(100000, 999999))
    reset_codes[email] = {'code': code, 'timestamp': time.time()}
    _save_pending_codes()
    sent = send_verification_email(email, code, purpose='Password Reset')
    return jsonify({'success': True, 'mail_sent': sent,
                    'message': 'Password reset code aap ki Gmail par bheja gaya hai.' if sent else
                               'Code tayyar hai lekin email abhi nahi bheja ja saka (mail setup pending hai).'})


    # ============ USER PROFILE ============
@app.route('/api/profile')
@login_required
def user_profile():
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, created_at FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    cursor.execute('SELECT * FROM premium_users WHERE user_id = ? AND is_active = 1', (user_id,))
    premium = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'user': dict(user) if user else None,
        'premium': dict(premium) if premium else None
    })
    # ============ ERROR LOGGING ============
import logging

logging.basicConfig(
    filename='playtube_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.errorhandler(500)
def server_error(e):
    logging.error(f"500 Error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404
    # ============ RATE LIMITING ============
request_counts = defaultdict(list)

@app.before_request
def rate_limit():
    ip = request.remote_addr
    now = time.time()
    
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 60]
    
    if len(request_counts[ip]) > 600:
        return jsonify({'error': 'Too many requests! Slow down!'}), 429
    
    request_counts[ip].append(now)
    # ============ ADMIN STATS ============
@app.route('/api/admin/stats')
def admin_stats():
    if not _admin_ok():
        return jsonify({'error': 'Admin login required'}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total_users FROM users')
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as premium_users FROM premium_users WHERE is_active = 1')
    premium_count = cursor.fetchone()['premium_users']
    
    cursor.execute('SELECT COUNT(*) as total_payments FROM pakistan_payments WHERE status = "verified"')
    total_payments = cursor.fetchone()['total_payments']
    
    cursor.execute('SELECT SUM(amount_pkr) as total_earnings FROM pakistan_payments WHERE status = "verified"')
    total_earnings = cursor.fetchone()['total_earnings'] or 0
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'premium_users': premium_count,
        'total_payments': total_payments,
        'total_earnings': total_earnings,
        'total_downloads': len(downloaded_files)
    })
    # ============ USER ACTIVITY LOG ============
ACTIVITY_LOG_FILE = os.path.join(os.path.expanduser("~"), "activity_log.json")

def log_activity(user_id, action, details=""):
    try:
        logs = []
        if os.path.exists(ACTIVITY_LOG_FILE):
            with open(ACTIVITY_LOG_FILE, 'r') as f:
                logs = json.load(f)
        
        logs.append({
            'user_id': user_id,
            'action': action,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep last 1000 logs
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        with open(ACTIVITY_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
    except:
        pass

@app.route('/api/log-activity', methods=['POST'])
def log_user_activity():
    data = request.json
    action = data.get('action', '')
    details = data.get('details', '')
    user_id = session.get('user_id')
    
    log_activity(user_id, action, details)
    return jsonify({'success': True})
    # ============ BULK DELETE ============
@app.route('/api/delete-all-downloads', methods=['DELETE'])
def delete_all_downloads():
    for download_id in list(downloaded_files.keys()):
        file_path = downloaded_files[download_id].get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        del downloaded_files[download_id]
    
    save_downloads_db()
    return jsonify({'success': True, 'message': 'All downloads deleted!'})
    # ============ SYSTEM INFO ============
@app.route('/api/system-info')
def system_info():
    return jsonify({
        'version': '1.0.0',
        'app_name': 'Playza',
        'developer': 'Chuza',
        'total_users': 0,  # Update from DB
        'total_downloads': len(downloaded_files),
        'premium_price': 'Rs. 500/month',
        'contact': 'chuzajani1@gmail.com'
    })
# ============ VISITOR TRACKING (database - Update 31) ============
# Har asal page-open gina jata hai aur SQLite database mein save hota
# hai (purana visitors.json tareeqa khatam - wo reset ho jata tha).
# Sirf dekhne ane wale sirf visit count mein add hote hain, user nahi bante.
def _record_visit(ip):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('INSERT INTO site_visits(day, opens, uniq) VALUES (?, 1, 0) '
                'ON CONFLICT(day) DO UPDATE SET opens = opens + 1', (today,))
    cur.execute('INSERT OR IGNORE INTO site_visit_ips(day, ip) VALUES (?, ?)',
                (today, ip or ''))
    if cur.rowcount:
        cur.execute('UPDATE site_visits SET uniq = uniq + 1 WHERE day = ?',
                    (today,))
    conn.commit()
    conn.close()


def _visit_totals():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT COALESCE(SUM(opens), 0) FROM site_visits')
    total = cur.fetchone()[0] or 0
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute('SELECT opens, uniq FROM site_visits WHERE day = ?', (today,))
    row = cur.fetchone()
    conn.close()
    return {'total': total,
            'today_opens': row[0] if row else 0,
            'today_uniq': row[1] if row else 0,
            'date': today}


# Purani visitors.json ka total ek dafa database mein le ao (migration)
try:
    _vf = os.path.join(os.path.expanduser("~"), "visitors.json")
    if os.path.exists(_vf):
        with open(_vf, 'r') as _f:
            _vd = json.load(_f)
        if int(_vd.get('total', 0)) > 0:
            _c = sqlite3.connect(DB_FILE)
            _c.execute('INSERT INTO site_visits(day, opens, uniq) VALUES (?, ?, ?) '
                       'ON CONFLICT(day) DO UPDATE SET opens = opens + excluded.opens',
                       (_vd.get('date') or datetime.now().strftime('%Y-%m-%d'),
                        int(_vd.get('total', 0)), int(_vd.get('today', 0))))
            _c.commit()
            _c.close()
        os.rename(_vf, _vf + '.imported')
except Exception:
    pass


@app.before_request
def track_visitor():
    try:
        if request.method != 'GET':
            return
        p = request.path or '/'
        if p.startswith('/api/') or p.startswith('/static/'):
            return
        last = p.rsplit('/', 1)[-1]
        if '.' in last and not p.endswith('.html'):
            return  # assets / apk / manifest / sw - page open nahi
        if p != '/' and 'text/html' not in (request.headers.get('Accept') or ''):
            return
        _record_visit(request.remote_addr)
    except Exception:
        pass


@app.route('/api/visitor-stats')
def visitor_stats():
    v = _visit_totals()
    return jsonify({
        'total_visitors': v['total'],
        'total_visits': v['total'],
        'today_visitors': v['today_uniq'],
        'today_visits': v['today_opens'],
        'date': v['date']
    })
# ============================================================
# ============ PLAYTUBE v2 (CHUZA) NEW FEATURES ==============
# AI Assistant - More Formats - PWA - Smart Link - Settings API
# ============================================================

# ---------- Payment accounts: public + admin APIs ----------
@app.route('/api/payment-accounts')
def public_payment_accounts():
    """Only accounts the admin has saved. Empty dict = no account added yet."""
    return jsonify({'accounts': PAKISTAN_PAYMENTS})


@app.route('/api/admin/payment-accounts/<secret_key>', methods=['GET', 'POST'])
def admin_payment_accounts(secret_key):
    if secret_key != ADMIN_SECRET_KEY:
        return jsonify({'error': 'Access Denied'}), 403
    settings = load_site_settings()
    if request.method == 'POST':
        data = request.json or {}
        method = str(data.get('method', '')).lower()
        if method not in PAYMENT_METHOD_META:
            return jsonify({'error': 'Invalid method'}), 400
        accounts = settings.get('payment_accounts', {})
        number = str(data.get('account_number', '')).strip()
        if number:
            accounts[method] = {
                'account_number': number,
                'account_title': str(data.get('account_title', 'Playza Premium')).strip()
                or 'Playza Premium'
            }
        else:
            accounts.pop(method, None)  # empty number = remove account
        settings['payment_accounts'] = accounts
        save_site_settings(settings)
        _rebuild_payment_accounts()
    return jsonify({'accounts': settings.get('payment_accounts', {}),
                    'active': PAKISTAN_PAYMENTS})


@app.route('/api/admin/payment-accounts/<secret_key>/<method>', methods=['DELETE'])
def admin_payment_account_delete(secret_key, method):
    if secret_key != ADMIN_SECRET_KEY:
        return jsonify({'error': 'Access Denied'}), 403
    settings = load_site_settings()
    accounts = settings.get('payment_accounts', {})
    accounts.pop(str(method).lower(), None)
    settings['payment_accounts'] = accounts
    save_site_settings(settings)
    _rebuild_payment_accounts()
    return jsonify({'success': True, 'active': PAKISTAN_PAYMENTS})


# ---------- More Formats API (Update 2) ----------
def _fmt_size_mb(fmt):
    size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
    return round(size / (1024 * 1024), 1) if size else None


@app.route('/api/formats/<video_id>')
def api_formats(video_id):
    try:
        info = _extract_formats_info(
            f"https://www.youtube.com/watch?v={video_id}")
    except Exception as e:
        _em = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
        if 'Sign in to confirm' in _em or 'not a bot' in _em:
            _em = ('YouTube ne server ko kuch der ke liye roka hai — '
                   '10-15 minute baad dobara try karein')
        return jsonify({'error': _em[:150]}), 400
    if not info:
        return jsonify({'error': 'Video info nahi mili'}), 400

    formats = info.get('formats', []) or []
    duration = info.get('duration') or 0

    audio_fmts = [f for f in formats if f.get('acodec') not in (None, 'none')
                  and f.get('vcodec') in (None, 'none')]
    best_audio = max(audio_fmts, key=lambda f: f.get('filesize')
                     or f.get('filesize_approx') or 0, default=None)
    best_audio_size = ((best_audio.get('filesize') or best_audio.get('filesize_approx'))
                       if best_audio else None)

    def combined_size_mb(fmt):
        # Merged download (video+audio) ka asal size; data na ho to None —
        # size kabhi invent nahi kiya jata.
        vs = fmt.get('filesize') or fmt.get('filesize_approx')
        if not vs:
            return None
        total = vs
        if fmt.get('acodec') in (None, 'none') and best_audio_size:
            total += best_audio_size
        return round(total / (1024 * 1024), 1)

    def _fmt_size_est(fmt):
        # (mb, is_est): asal filesize ho to wahi; warna tbr
        # (kbps) x duration se andaza — row khali nahi rehti.
        vs = fmt.get('filesize') or fmt.get('filesize_approx')
        if vs:
            total = vs
            if fmt.get('acodec') in (None, 'none') and best_audio_size:
                total += best_audio_size
            return round(total / (1024 * 1024), 1), False
        tbr = fmt.get('tbr') or fmt.get('vbr') or 0
        if fmt.get('acodec') in (None, 'none') and best_audio:
            tbr = tbr + (best_audio.get('tbr') or best_audio.get('abr') or 128)
        if tbr and duration:
            return round(tbr * 1000 / 8 * duration / (1024 * 1024), 1), True
        return None, False

    video_group = []
    # 3GP / lowest first - button-mobile friendly (generated option, as before)
    gp = [f for f in formats if f.get('ext') == '3gp']
    worst = min(formats, key=lambda f: (f.get('filesize') or f.get('filesize_approx')
                                        or 10 ** 12)) if formats else None
    gp_fmt = gp[0] if gp else worst
    if gp_fmt:
        video_group.append({'label': '3GP', 'format': 'mp4', 'quality': '3gp',
                            'size_mb': _fmt_size_mb(gp_fmt)})

    # Video ki har asal quality tier, us ke apne maximum tak (2K/4K bhi)
    _STANDARDS = [(144, '144p'), (240, '240p'), (360, '360p'), (480, '480p'),
                  (720, '720p HD'), (1080, '1080p HD'), (1440, '1440p (2K)'),
                  (2160, '2160p (4K)'), (4320, '4320p (8K)')]
    _prev_h = 0
    for _h, _label in _STANDARDS:
        _cands = [f for f in formats if f.get('height') and _prev_h < f['height'] <= _h
                  and f.get('vcodec') not in (None, 'none')]
        if not _cands:
            continue
        _cands.sort(key=lambda f: (f.get('height', 0),
                                   1 if f.get('ext') == 'mp4' else 0,
                                   f.get('filesize') or f.get('filesize_approx') or 0))
        _best = _cands[-1]
        _prev_h = _best.get('height', _h)
        _smb, _sest = _fmt_size_est(_best)
        video_group.append({'label': _label, 'format': 'mp4', 'quality': f'{_h}p',
                            'size_mb': _smb, 'size_est': _sest})

    music_group = [{'label': 'M4A (128K)', 'format': 'm4a', 'quality': None,
                    'size_mb': _fmt_size_mb(best_audio) if best_audio else None}]
    for br in (70, 128, 160, 320):
        est = round(duration * br * 1000 / 8 / (1024 * 1024), 1) if duration else None
        music_group.append({'label': f'MP3 ({br}K)', 'format': 'mp3',
                            'quality': str(br), 'size_mb': est})

    return jsonify({
        'video_id': video_id,
        'title': info.get('title', ''),
        'channel': info.get('channel', info.get('uploader', '')),
        'duration': duration,
        'music': music_group,
        'video': video_group
    })


# ---------- Smart Link Paste (Update 8) ----------
@app.route('/api/smart-link', methods=['POST'])
def api_smart_link():
    data = request.json or {}
    url = str(data.get('url', '')).strip()
    if not url:
        return jsonify({'error': 'Link required'}), 400
    yt_match = re.search(r'(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})', url)
    if 'list=' in url and 'youtube' in url:
        return jsonify({'type': 'playlist', 'url': url})
    if yt_match:
        return jsonify({'type': 'youtube', 'video_id': yt_match.group(1), 'url': url})
    if re.search(r'(youtube\.com|youtu\.be)', url):
        return jsonify({'type': 'playlist', 'url': url})
    return jsonify({'type': 'social', 'platform': detect_platform(url), 'url': url})


# ============================================================
# ==================== AI ASSISTANT ==========================
# ============================================================
AI_JOBS_FILE = os.path.join(DOWNLOAD_DIR, 'ai_jobs.json')
ai_jobs = {}
ai_jobs_lock = threading.Lock()


def _save_ai_jobs():
    try:
        with open(AI_JOBS_FILE, 'w') as f:
            json.dump(ai_jobs, f, indent=2)
    except Exception:
        pass


def _load_ai_jobs():
    global ai_jobs
    try:
        if os.path.exists(AI_JOBS_FILE):
            with open(AI_JOBS_FILE, 'r') as f:
                ai_jobs = json.load(f)
    except Exception:
        ai_jobs = {}
    # Jobs that were mid-run when the server stopped can never finish;
    # mark them honestly instead of leaving them "running" forever.
    # ('scheduled' jobs are kept - the scheduler will still run them.)
    for _job in ai_jobs.values():
        if _job.get('status') in ('running', 'queued'):
            _job['status'] = 'interrupted'
            _job['note'] = 'Server restart ke waqt ye job chal raha tha'
    # Update 109: 24 ghante se purani jobs khud saaf (chat bhi 24 ghante me saaf hoti hai)
    try:
        _cut = time.time() - 24 * 3600
        for _jid in list(ai_jobs.keys()):
            try:
                _ts = datetime.fromisoformat(
                    ai_jobs[_jid].get('created_at') or '').timestamp()
            except Exception:
                _ts = 0
            if _ts and _ts < _cut:
                del ai_jobs[_jid]
    except Exception:
        pass


_load_ai_jobs()

_AI_FILLER = [
    'download kar do', 'download kardo', 'download karo', 'download kar',
    'download kr do', 'download krdo', 'download kr', 'download',
    'kar do', 'kardo', 'kar dein', 'kar de', 'kr do', 'krdo',
    'mujhe', 'mujhy', 'please', 'plz', 'yeh', 'ye', 'wala', 'wali',
    'drama', 'serial', 'series', 'video', 'song', 'movie', 'film',
    'mein', 'me', 'mai', 'par', 'ko', 'ka', 'ki', 'ke', 'ho', 'hai',
    'chahiye', 'chahye', 'lagao', 'laga do', 'bana do', 'de do',
    'in', 'quality', 'karo', 'kr', 'hd', 'full', 'the', 'a',
    'trending', 'viral', 'latest',
]


def ai_parse_command(text):
    """Robust rule-based parser - Roman Urdu + English."""
    raw = (text or '').strip()
    t = ' ' + raw.lower() + ' '
    parsed = {'raw': raw, 'intent': 'download', 'title': '', 'episodes': [],
              'quality': '360p', 'format': 'mp4', 'schedule_at': None,
              'schedule_in_seconds': None, 'category': None,
              'count': None, 'lang': None, 'latest_count': None}

    # ---- schedule ----
    iso = re.search(r'(\d{4}-\d{2}-\d{2})[ t](\d{2}:\d{2})', t)
    if iso:
        parsed['schedule_at'] = f"{iso.group(1)}T{iso.group(2)}:00"
        t = t.replace(iso.group(0), ' ')
    rel = re.search(r'(\d+)\s*(minute|min|ghant|hour|hr)s?\s*(baad|after|later)?', t)
    rel_ur = re.search(r'(\d+)\s*(minute|ghante|ghanta)\s*baad', t)
    if rel_ur or (rel and ('baad' in t or 'after' in t or 'later' in t or ' in ' in t)):
        m = rel_ur or rel
        n = int(m.group(1))
        unit = m.group(2)
        parsed['schedule_in_seconds'] = n * (3600 if unit.startswith('ghant')
                                             or unit.startswith('hour')
                                             or unit == 'hr' else 60)
        t = t.replace(m.group(0), ' ')

    # ---- quality / format ----
    if '3gp' in t:
        parsed['quality'] = '3gp'
        t = t.replace('3gp', ' ')
    low_words = ['sab se chhoti', 'sabse chhoti', 'sab say chhoti', 'lowest',
                 'chhoti quality', 'kam quality', 'smallest']
    if any(w in t for w in low_words):
        parsed['quality'] = '3gp'
        for w in low_words:
            t = t.replace(w, ' ')
    qm = re.search(r'(\d{3,4})\s*p\b', t)
    if qm and parsed['quality'] != '3gp':
        parsed['quality'] = qm.group(1) + 'p'
        t = t.replace(qm.group(0), ' ')
    mp3m = re.search(r'mp3\s*(\d{2,3})\s*k?', t)
    if 'mp3' in t or mp3m:
        parsed['format'] = 'mp3'
        parsed['quality'] = mp3m.group(1) if mp3m else '192'
        t = re.sub(r'mp3\s*\d{0,3}\s*k?', ' ', t)
    elif 'm4a' in t:
        parsed['format'] = 'm4a'
        parsed['quality'] = None
        t = t.replace('m4a', ' ')
    if 'audio' in t or 'sirf awaz' in t or 'gana sunna' in t:
        if parsed['format'] == 'mp4':
            parsed['format'] = 'mp3'
            parsed['quality'] = '192'

    # ---- episodes ----
    rng = re.search(r'(?:episode|ep|qist)\s*(\d+)\s*(?:to|se|sy|say|tak|-|–)\s*(\d+)(?:\s*(?:tak|tk))?', t)
    if rng:
        a, b = int(rng.group(1)), int(rng.group(2))
        parsed['episodes'] = list(range(min(a, b), max(a, b) + 1))
        t = t.replace(rng.group(0), ' ')
    else:
        cnt = re.search(r'(\d+)\s*(?:episodes?|eps?|qistein|qistain|qist)', t)
        single = re.search(r'(?:episode|ep|qist)\s*(\d+)', t)
        _lst = re.search(r'(?:episodes?|eps?|qist)\s+((?:\d+[\s,]+){1,}\d+)', t)
        _lnums = []
        if _lst:
            _lnums = [int(x) for x in re.findall(r'\d+', _lst.group(1))
                      if int(x) <= 500]
        if _lnums and max(_lnums) - min(_lnums) <= 200:
            parsed['episodes'] = sorted(set(_lnums))[:100]
            t = t.replace(_lst.group(0), ' ')
        elif cnt:
            n = int(cnt.group(1))
            if re.search(r'\b(latest|new|naye|nayi|taza)\b', t):
                parsed['latest_count'] = n
            else:
                parsed['episodes'] = list(range(1, n + 1))
            t = t.replace(cnt.group(0), ' ')
        elif single:
            parsed['episodes'] = [int(single.group(1))]
            t = t.replace(single.group(0), ' ')
        else:
            allep = re.search(r'(?:saari|saare|sari|saray|all|puri|poori)\s+'
                              r'(?:episodes?|qistein|eps?)', t)
            if allep:
                parsed['episodes'] = list(range(1, 11))  # default: first 10
                t = t.replace(allep.group(0), ' ')
    t = re.sub(r'\b(episodes?|eps?|qistein|qist)\b', ' ', t)

    # ---- count (v9): '10 songs / 5 gaane / 3 movies' = utni videos ki list ----
    _cnt_span = None
    cntm = re.search(r'(\d+)\s+(?:[a-z]+\s+){0,3}?(songs?|gana|gaane|geet|movies?|films?|videos?|naats?|dramas?|cartoons?|shorts?|reels?|tiktoks?)\b', t)
    if not cntm:
        cntm = re.search(r'(songs?|movies?|naats?|dramas?|cartoons?|shorts?|reels?|tiktoks?)\s+(\d+)\b', t)
        if cntm:
            _cnt_span = cntm.group(0)
            cntm = (cntm.group(2), cntm.group(1))
    else:
        _cnt_span = cntm.group(0)
        cntm = (cntm.group(1), cntm.group(2))
    if cntm:
        parsed['count'] = max(1, min(100, int(cntm[0])))
        _noun2cat = {'song': 'song', 'songs': 'song', 'gana': 'song',
                     'gaane': 'song', 'geet': 'song', 'movie': 'movie',
                     'movies': 'movie', 'film': 'movie', 'films': 'movie',
                     'naat': 'naat', 'naats': 'naat', 'drama': 'drama',
                     'dramas': 'drama', 'cartoon': 'cartoon',
                     'cartoons': 'cartoon', 'short': 'shorts',
                     'shorts': 'shorts', 'reel': 'shorts', 'reels': 'shorts',
                     'tiktok': 'shorts', 'tiktoks': 'shorts',
                     'video': 'video', 'videos': 'video'}
        if not parsed.get('category'):
            parsed['category'] = _noun2cat.get(cntm[1])
        if _cnt_span:
            t = t.replace(_cnt_span, ' ', 1)
        t = re.sub(r'\b' + re.escape(str(parsed['count'])) + r'\s+(?:new\s+|latest\s+)?' + cntm[1] + r'\b', ' ', t, count=1)
        t = re.sub(r'\b' + cntm[1] + r'\s+' + re.escape(str(parsed['count'])) + r'\b', ' ', t, count=1)

    # ---- intent ----
    if 'thumbnail' in t:
        parsed['intent'] = 'thumbnail'
    elif 'subtitle' in t or 'caption' in t:
        parsed['intent'] = 'subtitles'
    elif 'playlist' in t:
        parsed['intent'] = 'playlist'
    elif ('search' in t or 'dhund' in t or 'dhoond' in t or 'talash' in t) \
            and 'download' not in raw.lower():
        parsed['intent'] = 'search'

    # ---- category / type (Update 40): movie manga to movie hi mile,
    # gana manga to gana — type title se alag pehchano ----
    if 'tiktok' in t or 'reel' in t or 'shorts' in t:
        parsed['category'] = 'shorts'
    elif 'naat' in t:
        parsed['category'] = 'naat'
    elif 'cartoon' in t:
        parsed['category'] = 'cartoon'
    elif 'bayan' in t or 'lecture' in t:
        parsed['category'] = 'bayan'
    elif 'movie' in t or 'film' in t:
        parsed['category'] = 'movie'
    elif 'drama' in t or 'serial' in t:
        parsed['category'] = 'drama'
    elif 'song' in t or 'gana' in t or 'geet' in t:
        parsed['category'] = 'song'

    # ---- title cleanup (punctuation first, so "kar do," matches "kar do") ----
    title = re.sub(r'[^a-z0-9 ]', ' ', t)
    title = ' ' + re.sub(r'\s+', ' ', title).strip() + ' '
    for phrase in _AI_FILLER:
        title = title.replace(' ' + phrase + ' ', ' ')
    title = re.sub(r'\s+', ' ', title).strip()
    if title:
        parsed['title'] = title.title()
    else:
        # No name given (e.g. "ye drama download kar do") - fall back to a
        # cleaned version of the raw command instead of the raw text itself.
        fb = re.sub(r'[^a-z0-9 ]', ' ', raw.lower())
        fb = re.sub(r'\b(episode|episodes|download|kar|karo|do|kr|me|mein|\d+p|\d+)\b', ' ', fb)
        parsed['title'] = re.sub(r'\s+', ' ', fb).strip().title() or 'Video'
    # v9: generic lafz (new/latest/top...) aur akeli language (hindi/urdu)
    # title NAHI bante — ye category/intent hain, naam nahi.
    _GEN = {'new', 'latest', 'top', 'best', 'superhit', 'hit', 'fresh',
            'naya', 'nayi', 'naye', 'purana', 'purani', 'viral',
            'kro', 'karo', 'please', 'chahiye', 'video', 'videos',
            'aur', 'or'}
    _LANG = {'hindi', 'urdu', 'english', 'punjabi', 'bengali', 'tamil',
             'telugu', 'dubbed'}
    _toks = (parsed.get('title') or '').lower().split()
    if _toks:
        _keep = []
        for _w in _toks:
            if _w in _GEN:
                continue
            if _w.isdigit() and (parsed.get('count') or parsed.get('category')):
                continue
            _keep.append(_w)
        if len(_keep) < len(_toks):
            parsed['title'] = ' '.join(_keep).title()
        if _keep and all(_w.isdigit() for _w in _keep):
            parsed['title'] = ''
    if parsed.get('title') and parsed.get('category'):
        _lt = parsed['title'].lower().split()
        if _lt and all(_w in _LANG for _w in _lt):
            parsed['lang'] = _lt[0]
            parsed['title'] = ''
    return parsed


def _ai_search_first(query):
    """First yt-dlp search result (no API key needed)."""
    try:
        info = _extract_with_clients(
            f"ytsearch1:{query}",
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'extract_flat': True, 'skip_download': True,
             'ignoreerrors': True, 'socket_timeout': 20,
             'retries': 2, 'extractor_retries': 2})
        entries = (info or {}).get('entries') or []
        if entries and entries[0].get('id'):
            return entries[0]['id'], entries[0].get('title', query)
    except Exception:
        pass
    return None, None


def _ai_pick_entry(parsed):
    """Single (non-episode) download ke liye BEHTREEN match (Update 40).

    Pehla search result andha-dhund nahi uthaya jata — keywords aur
    type (movie/song/naat...) ki jaanch hoti hai. Ghalat type (movie ki
    jagah songs playlist waghera) reject ho jati hai; kuch qualify na
    kare to (None, None) — ghalat video download nahi hoti.
    """
    title = parsed.get('title') or ''
    cat = parsed.get('category')
    cat_word = {'movie': 'movie', 'song': 'song', 'naat': 'naat',
                'drama': 'drama', 'cartoon': 'cartoon',
                'bayan': 'bayan', 'shorts': 'shorts'}.get(cat or '', '')
    query = title
    if cat_word and cat_word not in title.lower():
        query = (title + ' ' + cat_word).strip()
    if (parsed.get('category') or '') == 'shorts':
        _skws = [w for w in re.findall(r'[a-z0-9]+', title.lower())
                 if len(w) >= 3 and w not in ('the', 'new', 'video',
                                              'videos', 'full')]
        _sbest = None
        for _it in _shorts_feed_items(query, 20):
            _vid = (_it.get('id') or {}).get('videoId')
            if not _vid:
                continue
            _sn = _it.get('snippet') or {}
            _ttl = _sn.get('title') or ''
            _hit = sum(1 for k in _skws if k in _ttl.lower()) if _skws else 1
            if _skws and _hit < max(1, int(len(_skws) * 0.6)):
                continue
            if _sbest is None or _hit > _sbest[0]:
                _sbest = (_hit, _vid, _ttl, _it)
        if _sbest:
            _it = _sbest[3]
            _sn = _it.get('snippet') or {}
            return _sbest[1], _sbest[2], {
                'channel': _sn.get('channelTitle') or '',
                'duration': _it.get('duration'),
                'view_count': _it.get('view_count')}
        return None, None, None
    try:
        info = _extract_with_clients(
            f"ytsearch12:{query}",
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'extract_flat': True, 'skip_download': True,
             'ignoreerrors': True, 'socket_timeout': 20,
             'retries': 2, 'extractor_retries': 2})
    except Exception:
        return None, None, None
    entries = [e for e in ((info or {}).get('entries') or [])
               if e and e.get('id')]
    if not entries:
        return None, None, None
    _stop = {'tv', 'hd', 'full', 'new', 'official', 'the', 'a', 'an',
             'hai', 'aur', 'video', 'videos'}
    kws = [w for w in re.findall(r'[a-z0-9]+', title.lower())
           if len(w) >= 3 and w not in _stop]

    def _score(e):
        tl = (e.get('title') or '').lower()
        dur = e.get('duration') or 0
        s = 0
        if kws:
            hit = sum(1 for k in kws if k in tl)
            if hit < max(1, int(len(kws) * 0.6)):
                return -999
            s += hit * 3
        if 'playlist' in tl:
            s -= 6
        if 'jukebox' in tl or 'compilation' in tl:
            s -= 5
        if cat == 'movie':
            if 'song' in tl or 'audio' in tl:
                s -= 6
            if dur >= 1200:
                s += 3
            elif dur and dur < 300:
                s -= 4
        elif cat == 'song':
            if dur and 60 <= dur <= 600:
                s += 2
            if 'full movie' in tl or 'full episode' in tl:
                s -= 5
        elif cat == 'naat':
            if 'naat' in tl:
                s += 3
        elif cat == 'drama':
            if 'episode' in tl or 'drama' in tl:
                s += 2
        if cat_word and cat_word in tl:
            s += 2
        return s

    best = None
    for e in entries:
        sc = _score(e)
        if sc <= -999:
            continue
        if best is None or sc > best[0]:
            best = (sc, e)
    if best is None:
        return None, None, None
    if kws and best[0] < 3:
        return None, None, None
    return best[1]['id'], best[1].get('title', query), best[1]


def _ai_pick_best(parsed):
    _vid, _vt, _e = _ai_pick_entry(parsed)
    return _vid, _vt


def _video_meta(vid):
    """Ek video ka title (flat extraction, tez)."""
    try:
        info = _extract_with_clients(
            f"https://www.youtube.com/watch?v={vid}",
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'extract_flat': True, 'skip_download': True, 'ignoreerrors': True,
             'socket_timeout': 20, 'retries': 2, 'extractor_retries': 2})
        if info:
            return info.get('title')
    except Exception:
        pass
    return None


def _playlist_items(pid, vid=None):
    """Playlist ki videos ki list [{video_id, title}] (Update 43)."""
    if pid.startswith('RD') and vid:
        _url = f"https://www.youtube.com/watch?v={vid}&list={pid}"
    else:
        _url = f"https://www.youtube.com/playlist?list={pid}"
    try:
        info = _extract_with_clients(
            _url,
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'extract_flat': 'in_playlist', 'skip_download': True,
             'ignoreerrors': True, 'socket_timeout': 25,
             'retries': 2, 'extractor_retries': 2, 'playlistend': 60})
        items = []
        for e in (info or {}).get('entries') or []:
            if e and e.get('id'):
                items.append({'video_id': e['id'],
                              'title': e.get('title') or 'Video'})
        return items
    except Exception:
        return []


_TEASER_RE = re.compile(
    r'\b(teaser|trailer|promo|first look|coming soon)\b', re.I)


def _ai_is_teaser(title):
    """Teaser/trailer/promo wali video asal episode NAHI hoti —
    episode lists mein kabhi nahi ayegi; un ka apna alag Taza
    option hai (user, 2026-11-27)."""
    return bool(_TEASER_RE.search(title or ''))


def _ai_find_episode(show_title, ep):
    """Episode search + title matching (Bug #6 fix).

    Sirf wahi result chuna jata hai jis ke title me show ke saare main
    keywords AUR episode number dono hon. Kuch qualify na kare to
    (None, None, False) - koi unrelated video kabhi nahi uthai jati.
    """
    query = f"{show_title} episode {ep}"
    try:
        info = _extract_with_clients(
            f"ytsearch10:{query}",
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'extract_flat': True, 'skip_download': True,
             'ignoreerrors': True, 'socket_timeout': 20,
             'retries': 2, 'extractor_retries': 2})
    except Exception:
        return None, None, False
    entries = (info or {}).get('entries') or []
    _stop = {'tv', 'hd', 'full', 'new', 'official', 'the', 'a', 'an', 'hai', 'aur'}
    kws = [w for w in re.findall(r'[a-z0-9]+', (show_title or '').lower())
           if len(w) >= 3 and w not in _stop]
    if not kws:
        kws = [w for w in re.findall(r'[a-z0-9]+', (show_title or '').lower()) if w]
    ep_patterns = [rf'episode\s*#?\s*{ep}\b', rf'\bep\.?\s*#?\s*{ep}\b',
                   rf'\bpart\s*#?\s*{ep}\b', rf'\bqist\s*#?\s*{ep}\b']

    def _ep_ok(tl):
        if any(re.search(p, tl) for p in ep_patterns):
            return 2
        if re.search(rf'(?<![0-9]){ep}(?![0-9])', tl):
            return 1
        return 0

    best = None
    for e in entries:
        if not e or not e.get('id'):
            continue
        tl = (e.get('title') or '').lower()
        if _ai_is_teaser(tl):
            continue
        if kws and not all(k in tl for k in kws):
            continue
        sc = _ep_ok(tl)
        if not sc:
            continue
        if best is None or sc > best[0]:
            best = (sc, e['id'], e.get('title', query))
    if best:
        return best[1], best[2], True
    return None, None, False


def _enrich_ai_job(job):
    """AI job episodes me live download percent joro (sachai wali halat)."""
    try:
        for es in job.get('episodes_status', []):
            dl = es.get('download_id')
            if dl and es.get('status') in ('downloading', 'searching', 'starting'):
                st = download_progress.get(dl, {})
                if st:
                    es['percent'] = st.get('percent', 0)
                    es['speed'] = st.get('speed', '')
    except Exception:
        pass
    return job

def _ai_wait_download(download_id, timeout=3600):
    start = time.time()
    while time.time() - start < timeout:
        if download_control.get(download_id, {}).get('cancel'):
            return False, {'error': 'Stopped'}
        st = download_progress.get(download_id, {})
        if st.get('status') == 'completed':
            return True, st
        if st.get('status') == 'error':
            return False, st
        time.sleep(2)
    return False, {'error': 'Timeout'}


def _ai_run_job(job_id, only_idx=None):
    try:
        _storage_cleanup()
    except Exception:
        pass
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return
        job['status'] = 'running'
        _save_ai_jobs()
    parsed = job['parsed']
    episodes = parsed.get('episodes') or [None]
    direct_items = job.get('direct_items') or []
    if direct_items:
        episodes = [None] * len(direct_items)
    if only_idx is not None and not direct_items:
        episodes = [_es.get('episode')
                    for _es in (job.get('episodes_status') or [])] or episodes
    # v17: "latest N episodes" — pehle asal latest episode numbers
    # search se nikalo, phir wahi download hon ge (quality parsed wali).
    if parsed.get('latest_count') and not direct_items and only_idx is None:
        _want = int(parsed['latest_count'])
        _found_eps = []
        try:
            _info = _extract_with_clients(
                f"ytsearch30:{parsed['title']} episode",
                {'quiet': True, 'no_warnings': True,
                 'no_check_certificate': True, 'extract_flat': True,
                 'skip_download': True, 'ignoreerrors': True,
                 'socket_timeout': 20, 'retries': 2,
                 'extractor_retries': 2})
            _nums = set()
            for _e in (_info or {}).get('entries') or []:
                if not _e:
                    continue
                _tl2 = (_e.get('title') or '').lower()
                _m = re.search(r'episode\s*#?\s*(\d+)', _tl2) or \
                    re.search(r'\bep\.?\s*#?\s*(\d+)', _tl2) or \
                    re.search(r'\bpart\s*#?\s*(\d+)', _tl2)
                if _m:
                    _nums.add(int(_m.group(1)))
            _found_eps = sorted(_nums)[-_want:]
        except Exception:
            _found_eps = []
        if not _found_eps:
            _found_eps = list(range(1, _want + 1))
        episodes = _found_eps
        with ai_jobs_lock:
            job['episodes_status'] = [{'episode': _ep, 'status': 'pending'}
                                       for _ep in episodes]
            job['total_count'] = len(episodes)
            job['completed_count'] = 0
            _save_ai_jobs()
    done = 0
    if only_idx is not None:
        done = sum(1 for _i, _es in enumerate(job.get('episodes_status') or [])
                   if _i != only_idx and _es.get('status') == 'completed')
    for idx, ep in enumerate(episodes):
        if only_idx is not None and idx != only_idx:
            continue
        with ai_jobs_lock:
            _stop_all = bool(job.get('stop_all'))
            _gdev = job.get('guest_device')
            if _stop_all:
                job['episodes_status'][idx]['status'] = 'stopped'
                _save_ai_jobs()
        if _stop_all:
            continue
        if _gdev and _guest_count(_gdev) >= get_guest_limit():
            with ai_jobs_lock:
                job['episodes_status'][idx]['status'] = 'failed'
                job['episodes_status'][idx]['error'] = 'Guest limit khatam'
                _save_ai_jobs()
            continue
        if direct_items:
            query = direct_items[idx]['title']
        elif ep:
            query = f"{parsed['title']} episode {ep}"
        else:
            query = parsed['title']
        with ai_jobs_lock:
            job['episodes_status'][idx] = {'episode': ep, 'query': query,
                                           'status': 'searching', 'attempts': 0}
            _save_ai_jobs()
        ok = False
        last_err = ''
        _stopped = False
        for attempt in range(1, 4):  # 1 try + up to 2 auto-retries
            if direct_items:
                vid, vtitle = (direct_items[idx]['video_id'],
                               direct_items[idx]['title'])
            elif ep:
                vid, vtitle, _found = _ai_find_episode(parsed['title'], ep)
                if not _found:
                    last_err = f"Episode {ep} nahi mila - koi sahi result nahi aaya"
                    break
            else:
                vid, vtitle = _ai_pick_best(parsed)
            if not vid:
                last_err = 'Search me sahi video nahi mili — naam thoda aur saaf likh kar try karein'
                continue
            _dup = _find_duplicate(vid, parsed['format'],
                                   parsed.get('quality'))
            if _dup:
                with ai_jobs_lock:
                    job['episodes_status'][idx].update(
                        {'video_id': vid, 'title': vtitle,
                         'status': 'completed',
                         'file_path': _dup.get('file_path'),
                         'note': 'Pehle se downloaded tha'})
                    _save_ai_jobs()
                ok = True
                break
            if attempt > 1 and locals().get('_prev_dl'):
                # Pichli attempt ab bhi zinda ho to pehle use band karo —
                # do zinda downloads ek hi video ki do files bana deti theen.
                download_control[_prev_dl] = {'cancel': True, 'deleted': True}
                for _w in range(15):
                    if download_progress.get(_prev_dl, {}).get('status') in (None, 'error', 'paused'):
                        break
                    time.sleep(1)
            _act = _find_active_download(vid, parsed['format'])
            if _act:
                # Wohi video pehle se download ho rahi hai — usi ka
                # intezaar karo, dusri copy mat chalao.
                with ai_jobs_lock:
                    job['episodes_status'][idx].update(
                        {'video_id': vid, 'title': vtitle, 'download_id': _act,
                         'status': 'downloading', 'attempts': attempt})
                    _save_ai_jobs()
                ok, st = _ai_wait_download(_act)
                if ok and _act not in downloaded_files:
                    ok = False
                    st = {'error': 'File registry me nahi mili'}
                with ai_jobs_lock:
                    if job['episodes_status'][idx].get('status') != 'deleted':
                        job['episodes_status'][idx].update(
                            {'attempts': attempt, 'video_id': vid,
                             'title': vtitle,
                             'status': 'downloading' if not ok else 'completed',
                             'file_path': st.get('file_path'),
                             'error': st.get('error')})
                    _save_ai_jobs()
                if ok:
                    break
                last_err = st.get('error') or 'Failed'
                continue
            dl_id = f"ai_{job_id}_{idx}_{attempt}_{int(time.time())}"
            download_progress[dl_id] = {'status': 'starting', 'percent': 0,
                                        'speed': '', 'error': None}
            if job.get('guest_device'):
                guest_pending[dl_id] = job['guest_device']
            th = threading.Thread(target=download_in_background,
                                  args=(vid, parsed['format'], parsed['quality'],
                                        dl_id, None),
                                  kwargs={'title_hint': vtitle})
            th.daemon = True
            th.start()
            _prev_dl = dl_id
            with ai_jobs_lock:
                job['episodes_status'][idx].update(
                    {'video_id': vid, 'title': vtitle, 'download_id': dl_id,
                     'status': 'downloading', 'attempts': attempt})
                _save_ai_jobs()
            ok, st = _ai_wait_download(dl_id)
            if ok and dl_id not in downloaded_files:
                ok = False
                st = {'error': 'File registry me nahi mili'}
            with ai_jobs_lock:
                if job['episodes_status'][idx].get('user_stopped') \
                        or job.get('stop_all'):
                    _stopped = True
            if _stopped:
                break
            with ai_jobs_lock:
                if job['episodes_status'][idx].get('status') != 'deleted':
                    job['episodes_status'][idx].update(
                        {'attempts': attempt, 'video_id': vid,
                         'title': vtitle, 'status': 'downloading' if not ok else 'completed',
                         'file_path': st.get('file_path'), 'error': st.get('error')})
                _save_ai_jobs()
            if ok:
                break
            last_err = st.get('error') or 'Failed'
        with ai_jobs_lock:
            if _stopped:
                if job['episodes_status'][idx].get('status') != 'deleted':
                    job['episodes_status'][idx]['status'] = 'stopped'
                job['episodes_status'][idx].pop('error', None)
            else:
                if job['episodes_status'][idx].get('status') != 'deleted':
                    job['episodes_status'][idx]['status'] = 'completed' if ok else 'failed'
                if not ok:
                    job['episodes_status'][idx]['error'] = last_err
            if ok:
                done += 1
            job['completed_count'] = done
            _save_ai_jobs()
    with ai_jobs_lock:
        total = len(episodes)
        job['status'] = 'completed' if done == total else (
            'partial' if done else 'failed')
        job['finished_at'] = datetime.now().isoformat()
        _save_ai_jobs()


def _ai_scheduler_loop():
    while True:
        try:
            now = time.time()
            due = []
            with ai_jobs_lock:
                for jid, job in ai_jobs.items():
                    if job.get('status') == 'scheduled' and \
                            job.get('run_at_epoch', 0) <= now:
                        job['status'] = 'queued'
                        due.append(jid)
                if due:
                    _save_ai_jobs()
            for jid in due:
                th = threading.Thread(target=_ai_run_job, args=(jid,))
                th.daemon = True
                th.start()
        except Exception:
            pass
        time.sleep(5)


_ai_scheduler_started = False


def _ai_start_scheduler():
    global _ai_scheduler_started
    if not _ai_scheduler_started:
        _ai_scheduler_started = True
        th = threading.Thread(target=_ai_scheduler_loop)
        th.daemon = True
        th.start()


_ai_start_scheduler()


_AI_CTX_FILE = os.path.join(DATA_DIR, 'ai_context.json')


def _ai_ctx_get(key):
    try:
        with open(_AI_CTX_FILE, encoding='utf-8') as _f:
            return (json.load(_f) or {}).get(key) or {}
    except Exception:
        return {}


def _ai_ctx_set(key, ctx):
    try:
        try:
            with open(_AI_CTX_FILE, encoding='utf-8') as _f:
                _all = json.load(_f) or {}
        except Exception:
            _all = {}
        _all[key] = ctx
        with open(_AI_CTX_FILE, 'w', encoding='utf-8') as _f:
            json.dump(_all, _f)
    except Exception:
        pass


def _ai_age_str(ts):
    # Update 109: epoch timestamp se '5h ago' / '2d ago' / '3w ago'
    # jaisi mukhtasar age. Timestamp na ho to khali string — nakli
    # time kabhi nahi lagta.
    try:
        ts = int(ts or 0)
    except Exception:
        ts = 0
    if ts <= 0:
        return ''
    _s = int(time.time()) - ts
    if _s < 0:
        _s = 0
    if _s < 90:
        return 'just now'
    if _s < 3600:
        return f"{max(1, _s // 60)}m ago"
    if _s < 86400:
        return f"{_s // 3600}h ago"
    if _s < 7 * 86400:
        return f"{_s // 86400}d ago"
    if _s < 30 * 86400:
        return f"{_s // (7 * 86400)}w ago"
    if _s < 365 * 86400:
        return f"{_s // (30 * 86400)}mo ago"
    return f"{_s // (365 * 86400)}y ago"


def _ai_fill_ages(out, query):
    # Update 110: yt-dlp flat entries mein timestamp nahi ata (sab 0
    # rehta hai), isiliye AI rows ka time YouTube results page ke
    # ASAL published text se bharta hai — feed cards wala hi
    # tareeqa (Update 108). Sirf khali age wale bharte hain; fail
    # ho to list jaisi hai waisi — nakli time kabhi nahi lagta.
    try:
        if not out or not query:
            return out
        _map = _feed_age_map(query)
        if _map:
            for _c in out:
                if not _c.get('age') and _c.get('video_id') in _map:
                    _c['age'] = _map[_c['video_id']]
    except Exception:
        pass
    return out


def _ai_candidates(parsed, query=None):
    """Update 102/105: naam se top-20 umeedwar videos — user khud
    chunta hai, AI khud se koi video download nahi karta."""
    title = parsed.get('title') or ''
    eps = parsed.get('episodes') or []
    if not query:
        query = title
        if eps:
            query = f"{title} episode {eps[0]}"
    _age_warm = threading.Thread(
        target=lambda: _dated_search_items(query, 30), daemon=True)
    _age_warm.start()
    try:
        info = _extract_with_clients(
            f"ytsearch60:{query}",
            {'quiet': True, 'no_warnings': True,
             'no_check_certificate': True, 'extract_flat': True,
             'skip_download': True, 'ignoreerrors': True,
             'socket_timeout': 20, 'retries': 2,
             'extractor_retries': 2})
    except Exception:
        return []
    entries = [e for e in ((info or {}).get('entries') or [])
               if e and e.get('id')]
    _stop = {'tv', 'hd', 'full', 'new', 'official', 'the', 'a', 'an',
             'hai', 'aur', 'video', 'videos'}
    kws = [w for w in re.findall(r'[a-z0-9]+', title.lower())
           if len(w) >= 3 and w not in _stop]
    _ep_intent = bool(eps) or 'episode' in (query or '').lower()
    out = []
    for e in entries:
        tl = (e.get('title') or '').lower()
        if _ep_intent and _ai_is_teaser(tl):
            continue
        if kws:
            hit = sum(1 for k in kws if k in tl)
            if hit < max(1, int(len(kws) * 0.6)):
                continue
        out.append({'video_id': e['id'],
                    'title': e.get('title') or query,
                    'channel': e.get('channel') or e.get('uploader') or '',
                    'duration': e.get('duration'),
                    'view_count': e.get('view_count'),
                    'timestamp': (e.get('timestamp')
                                  or e.get('release_timestamp') or 0),
                    'age': _ai_age_str(e.get('timestamp')
                                       or e.get('release_timestamp') or 0)})
        if len(out) >= 50:
            break
    if eps:
        _pat = f"episode {eps[0]}"
        out.sort(key=lambda x: 0 if _pat in (x.get('title') or '').lower()
                 else 1)
    else:
        # Update 105: latest pehle (jahan date mile) — user ki demand
        # "latest 20 video ani chiya".
        out.sort(key=lambda x: -(x.get('timestamp') or 0))
    _ai_fill_ages(out, query)
    return out


def _ai_episode_candidates(parsed):
    """Update 105: range / latest commands ke liye bhi pehle LIST —
    har episode number resolve karke candidates ki shakal mein.
    Kuch resolve na ho to khali list (caller search par girta hai)."""
    title = parsed.get('title') or ''
    eps = list(parsed.get('episodes') or [])
    if parsed.get('latest_count'):
        _want = int(parsed['latest_count'])
        _nums = set()
        try:
            _info = _extract_with_clients(
                f"ytsearch30:{title} episode",
                {'quiet': True, 'no_warnings': True,
                 'no_check_certificate': True, 'extract_flat': True,
                 'skip_download': True, 'ignoreerrors': True,
                 'socket_timeout': 20, 'retries': 2,
                 'extractor_retries': 2})
            for _e in (_info or {}).get('entries') or []:
                if not _e:
                    continue
                _tl2 = (_e.get('title') or '').lower()
                _m = re.search(r'episode\s*#?\s*(\d+)', _tl2) or \
                    re.search(r'\bep\.?\s*#?\s*(\d+)', _tl2) or \
                    re.search(r'\bpart\s*#?\s*(\d+)', _tl2)
                if _m:
                    _nums.add(int(_m.group(1)))
        except Exception:
            _nums = set()
        eps = sorted(_nums)[-_want:] if _nums \
            else list(range(1, _want + 1))
    out = []
    for _ep in eps:
        _v, _t, _f = _ai_find_episode(title, _ep)
        if _v:
            out.append({'video_id': _v,
                        'title': _t or f"{title} Episode {_ep}",
                        'channel': '', 'duration': None,
                        'view_count': None, 'timestamp': 0, 'age': ''})
    return out


def _ai_episode_list(show):
    """Update 102/113: ek show ki episodes (number ke sath, tartib
    mein) — AI chat ke folder ke liye. Update 113: Dangal-style
    titles ('Ep. 15', '| Episode 15', 'Part 15', naam ke baad seedha
    number) bhi pakro; pehli search se kam milein to aur queries
    bhi try karo (Rimjhim miss fix)."""
    _stop = {'tv', 'hd', 'full', 'new', 'official', 'the', 'a', 'an',
             'hai', 'aur', 'video', 'videos', 'drama'}
    kws = [w for w in re.findall(r'[a-z0-9]+', (show or '').lower())
           if len(w) >= 3 and w not in _stop]
    found = {}

    def _scan(entries):
        for e in entries or []:
            if not e or not e.get('id'):
                continue
            t = e.get('title') or ''
            tl = t.lower()
            if kws:
                hit = sum(1 for k in kws if k in tl)
                if hit < max(1, int(len(kws) * 0.6)):
                    continue
            m = re.search(r'episode\s*#?\s*(\d{1,3})', tl) or \
                re.search(r'\bep\.?\s*#?\s*(\d{1,3})\b', tl) or \
                re.search(r'\bpart\s*#?\s*(\d{1,3})\b', tl) or \
                re.search(r'\bqist\s*#?\s*(\d{1,3})\b', tl) or \
                re.search(r'(?:^|[|\-\u2013\u2014\u2022:])\s*(\d{1,3})\s*(?:$|[|\-\u2013\u2014\u2022:])', tl)
            if not m:
                continue
            n = int(m.group(1))
            if n < 1 or n > 500 or n in found:
                continue
            found[n] = {'episode': n, 'video_id': e['id'], 'title': t,
                        'duration': e.get('duration')}

    for _q in (f"ytsearch40:{show} episode", f"ytsearch40:{show} ep",
               f"ytsearch40:{show}"):
        try:
            info = _extract_with_clients(
                _q,
                {'quiet': True, 'no_warnings': True,
                 'no_check_certificate': True, 'extract_flat': True,
                 'skip_download': True, 'ignoreerrors': True,
                 'socket_timeout': 25, 'retries': 2,
                 'extractor_retries': 2})
        except Exception:
            info = None
        _scan((info or {}).get('entries') or [])
        if len(found) >= 5:
            break
    return [found[n] for n in sorted(found)][:80]


def _ai_create_direct_job(items, parsed_like, guest_device,
                          command_text=''):
    """Tay-shuda video_ids ki job — koi search nahi, wohi download hongi
    jin par user ne click kiya."""
    _jid = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
    _job = {'job_id': _jid, 'command': command_text,
            'parsed': parsed_like, 'status': 'queued',
            'run_at_epoch': time.time(),
            'created_at': datetime.now().isoformat(),
            'direct_items': items, 'guest_device': guest_device,
            'episodes_status': [{'episode': None, 'status': 'pending',
                                 'title': _it['title']} for _it in items],
            'completed_count': 0, 'total_count': len(items)}
    with ai_jobs_lock:
        ai_jobs[_jid] = _job
        _save_ai_jobs()
    _th = threading.Thread(target=_ai_run_job, args=(_jid,))
    _th.daemon = True
    _th.start()
    return _jid


def _ai_guest_guard():
    """Pick endpoints ke liye wohi shartein jo command par hain.
    (error_tuple_or_None, guest_device) deta hai."""
    if not feature_enabled('ai_enabled'):
        return (jsonify({'error': 'AI Assistant abhi band hai (admin ne off kiya hai)',
                         'ai_disabled': True}), 403), None
    if session.get('user_id'):
        return None, None
    _gl = get_guest_limit()
    if _gl <= 0:
        return (jsonify({'error': 'Download ke liye pehle account banayein / sign in karein',
                         'login_required': True}), 403), None
    _gdev = _guest_device_id()
    if _guest_count(_gdev) >= _gl:
        return (jsonify({'error': f'Guest ke {_gl} free downloads pure ho gaye — ab account banayein!',
                         'login_required': True, 'guest_limit': True,
                         'limit': _gl}), 403), None
    return None, _gdev


@app.route('/api/ai/pick', methods=['POST'])
def api_ai_pick():
    """Update 102: user ne candidate par click kiya — SIRF wahi video
    download hogi (koi search/pick khud se nahi)."""
    data = request.json or {}
    vid = (data.get('video_id') or '').strip()
    title = (data.get('title') or 'Video').strip()[:200]
    if not vid:
        return jsonify({'error': 'video_id chahiye'}), 400
    _err, _gdev = _ai_guest_guard()
    if _err:
        return _err
    fmt = (data.get('format') or 'mp4').strip().lower()
    if fmt not in ('mp4', 'mp3', 'm4a'):
        fmt = 'mp4'
    quality = str(data.get('quality') or '360p').strip()
    if fmt == 'mp3' and not quality.isdigit():
        quality = '192'
    show = (data.get('show') or '').strip()[:120]
    _parsed = {'title': show or title, 'quality': quality, 'format': fmt,
               'episodes': [], 'category': data.get('category'),
               'count': None, 'latest_count': None}
    _jid = _ai_create_direct_job(
        [{'video_id': vid, 'title': title}], _parsed, _gdev,
        f'pick: {title}')
    _q = quality if fmt == 'mp4' else 'MP3'
    return jsonify({'success': True, 'job_id': _jid, 'show': show,
                    'message': (f"✅ Yahi download ho rahi hai: '{title}' "
                                f"— {_q} mein. Job ID: {_jid}")})


@app.route('/api/ai/pick-many', methods=['POST'])
def api_ai_pick_many():
    """Update 102: folder se chuni hui saari episodes ek job mein —
    sirf wahi video_ids download hongi."""
    data = request.json or {}
    items = []
    for _it in (data.get('items') or [])[:100]:
        if isinstance(_it, dict) and _it.get('video_id'):
            items.append({'video_id': str(_it['video_id']),
                          'title': str(_it.get('title') or 'Video')[:200]})
    if not items:
        return jsonify({'error': 'items chahiye'}), 400
    _err, _gdev = _ai_guest_guard()
    if _err:
        return _err
    quality = str(data.get('quality') or '360p').strip()
    show = (data.get('show') or '').strip()[:120]
    _parsed = {'title': show or 'Episodes', 'quality': quality,
               'format': 'mp4', 'episodes': [], 'category': None,
               'count': None, 'latest_count': None}
    _jid = _ai_create_direct_job(items, _parsed, _gdev,
                                 f'pick-many: {show}')
    return jsonify({'success': True, 'job_id': _jid,
                    'message': (f"✅ {len(items)} episodes download start "
                                f"kar di hain — one by one hongi. "
                                f"Job ID: {_jid}")})


@app.route('/api/ai/episodes', methods=['POST'])
def api_ai_episodes():
    """Update 102: show ki episodes ki list (folder) — sirf search,
    koi download nahi."""
    if not feature_enabled('ai_enabled'):
        return jsonify({'error': 'AI Assistant abhi band hai',
                        'ai_disabled': True}), 403
    data = request.json or {}
    show = (data.get('show') or '').strip()[:120]
    if not show:
        return jsonify({'error': 'show ka naam chahiye'}), 400
    return jsonify({'success': True, 'show': show,
                    'episodes': _ai_episode_list(show)})


# Update 109: ready channel lists (Mere Shows / Channel Mode / Taza)
_AI_CHANNELS_PK = ['ARY Digital', 'Hum TV', 'Geo TV', 'Har Pal Geo',
                   'Green TV', 'Express Entertainment', 'PTV Home',
                   'Urdu1', 'ARY Zindagi', 'Bol Entertainment', 'Aan TV']
_AI_CHANNELS_IN = ['Star Plus', 'Colors TV', 'Zee TV', 'Dangal TV',
                   'Sony SAB']
_AI_CHANNELS_YT = ['Coke Studio', '8XM', 'T-Series', 'ARY Musik']
_AI_CHANNELS_ALL = _AI_CHANNELS_PK + _AI_CHANNELS_IN + _AI_CHANNELS_YT


def _ai_cand_from_entries(entries, cap=50):
    # yt-dlp flat entries -> candidate dicts (age ke sath)
    out = []
    for e in entries or []:
        if not e or not e.get('id'):
            continue
        _ts = e.get('timestamp') or e.get('release_timestamp') or 0
        out.append({'video_id': e['id'],
                    'title': e.get('title') or '',
                    'channel': e.get('channel') or e.get('uploader') or '',
                    'duration': e.get('duration'),
                    'view_count': e.get('view_count'),
                    'timestamp': _ts,
                    'age': _ai_age_str(_ts)})
        if len(out) >= cap:
            break
    return out


def _ai_playlist_candidates(pid, vid=None):
    """Update 113: playlist ki videos CANDIDATES ki shakal mein —
    user khud select karega, auto-download NAHI hoga."""
    if pid.startswith('RD') and vid:
        _url = f"https://www.youtube.com/watch?v={vid}&list={pid}"
    else:
        _url = f"https://www.youtube.com/playlist?list={pid}"
    try:
        info = _extract_with_clients(
            _url,
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'extract_flat': 'in_playlist', 'skip_download': True,
             'ignoreerrors': True, 'socket_timeout': 25,
             'retries': 2, 'extractor_retries': 2, 'playlistend': 60})
    except Exception:
        return None
    entries = [e for e in ((info or {}).get('entries') or [])
               if e and e.get('id')]
    if not entries:
        return None
    out = _ai_cand_from_entries(entries, 50)
    if not out:
        return None
    _t = (info or {}).get('title') or ''
    _ai_fill_ages(out, _t or 'playlist')
    return out, _t


def _ai_channel_candidates(channel):
    # Update 109: Channel Mode — channel ki latest videos (nayi pehle)
    try:
        info = _extract_with_clients(
            f"ytsearch60:{channel}",
            {'quiet': True, 'no_warnings': True,
             'no_check_certificate': True, 'extract_flat': True,
             'skip_download': True, 'ignoreerrors': True,
             'socket_timeout': 20, 'retries': 2,
             'extractor_retries': 2})
    except Exception:
        return []
    entries = [e for e in ((info or {}).get('entries') or [])
               if e and e.get('id')]
    out = _ai_cand_from_entries(entries, 50)
    out.sort(key=lambda x: -(x.get('timestamp') or 0))
    _ai_fill_ages(out, channel)
    return out


def _ai_similar_candidates(sim):
    # Update 109: 'Isi jaisi aur' — channel + title keywords se milti
    # julti videos; asal video khud list se bahar rehti hai.
    _sid = (sim or {}).get('id') or ''
    _chan = ((sim or {}).get('channel') or '').strip()
    _title = ((sim or {}).get('title') or '').strip()
    _clean = re.sub(r'\b(episode|ep)\s*#?\s*\d+\b', ' ', _title.lower())
    _clean = re.sub(r'[\[\](){}|.,:;!?/\\-]+', ' ', _clean)
    _stop = {'tv', 'hd', 'full', 'new', 'official', 'the', 'a', 'an',
             'hai', 'aur', 'video', 'videos', 'part', 'ost'}
    _kws = [w for w in re.findall(r'[a-z0-9]+', _clean)
            if len(w) >= 3 and w not in _stop][:5]
    _q = ' '.join(([_chan] if _chan else []) + _kws).strip() \
        or (_title or _chan)
    if not _q:
        return []
    try:
        info = _extract_with_clients(
            f"ytsearch40:{_q}",
            {'quiet': True, 'no_warnings': True,
             'no_check_certificate': True, 'extract_flat': True,
             'skip_download': True, 'ignoreerrors': True,
             'socket_timeout': 20, 'retries': 2,
             'extractor_retries': 2})
    except Exception:
        return []
    entries = [e for e in ((info or {}).get('entries') or [])
               if e and e.get('id') and e.get('id') != _sid]
    out = _ai_cand_from_entries(entries, 50)
    out.sort(key=lambda x: -(x.get('view_count') or 0))
    _ai_fill_ages(out, _q)
    return out


@app.route('/api/ai/show-check', methods=['POST'])
def api_ai_show_check():
    # Update 109: Nayi Episode Check — har save show ki sab se bari
    # episode number wali video. Ek show fail ho to baqi phir bhi
    # ate hain; poora endpoint kabhi 500 nahi hota.
    if not feature_enabled('ai_enabled'):
        return jsonify({'error': 'AI Assistant abhi band hai',
                        'ai_disabled': True}), 403
    data = request.json or {}
    shows = [str(s).strip()[:80] for s in (data.get('shows') or [])
             if str(s).strip()][:8]
    results = []
    _lock = threading.Lock()

    def _one(_show):
        try:
            info = _extract_with_clients(
                f"ytsearch10:{_show} latest episode",
                {'quiet': True, 'no_warnings': True,
                 'no_check_certificate': True, 'extract_flat': True,
                 'skip_download': True, 'ignoreerrors': True,
                 'socket_timeout': 15, 'retries': 1,
                 'extractor_retries': 1})
        except Exception:
            return
        _best = None
        for _e in ((info or {}).get('entries') or []):
            if not _e or not _e.get('id'):
                continue
            _m = re.search(r'episode\s*#?\s*(\d{1,3})',
                           (_e.get('title') or '').lower())
            if not _m:
                continue
            _n = int(_m.group(1))
            if _best is None or _n > _best[0]:
                _ts = (_e.get('timestamp')
                       or _e.get('release_timestamp') or 0)
                _best = (_n, {'show': _show, 'ep': _n,
                              'id': _e['id'],
                              'title': _e.get('title') or '',
                              'thumb': ('https://i.ytimg.com/vi/'
                                        + _e['id'] + '/mqdefault.jpg'),
                              'duration': _e.get('duration'),
                              'views': _e.get('view_count'),
                              'age': _ai_age_str(_ts)})
        if _best:
            with _lock:
                results.append(_best[1])

    _ths = [threading.Thread(target=_one, args=(s,), daemon=True)
            for s in shows]
    for _t in _ths:
        _t.start()
    _deadline = time.time() + 25
    for _t in _ths:
        _left = _deadline - time.time()
        if _left <= 0:
            break
        _t.join(timeout=_left)
    return jsonify({'success': True, 'results': results})


@app.route('/api/ai/taza', methods=['POST'])
def api_ai_taza():
    # Update 109: Aaj Ki Taza — pichle ~30 ghante ki nayi uploads
    # (drama / songs / mere save channels / mix). Candidate dicts
    # wapas jate hain taake aam select -> quality -> download flow
    # hi chale.
    if not feature_enabled('ai_enabled'):
        return jsonify({'error': 'AI Assistant abhi band hai',
                        'ai_disabled': True}), 403
    data = request.json or {}
    kind = (data.get('kind') or 'mix').strip().lower()
    _mine = [str(s).strip()[:80] for s in (data.get('shows') or [])
             if str(s).strip()][:8]
    _dch = ['ARY Digital', 'Hum TV', 'Geo TV', 'Har Pal Geo',
            'Star Plus', 'Colors TV']
    # mode: 'hide' = teaser bahir (episode lists), 'only' = sirf
    # teaser (alag option), 'keep' = sab (ganay).
    _queries = []
    if kind in ('drama', 'mix'):
        _queries += [(f"{c} new episode", 'hide') for c in _dch]
    if kind in ('songs', 'mix'):
        _queries += [(f"{c} new song", 'keep') for c in
                     ['Coke Studio', 'T-Series', '8XM', 'ARY Musik']]
    if kind == 'mine':
        _queries += [(f"{s} new", 'hide') for s in _mine]
    if kind == 'teaser':
        _queries += [(f"{c} teaser", 'only') for c in _dch + _mine[:4]]
        _queries += [(f"{c} trailer", 'only') for c in _dch]
    if not _queries:
        return jsonify({'success': True, 'kind': kind, 'candidates': []})
    _found = {}
    _lock = threading.Lock()

    _sem = threading.Semaphore(2)

    def _one(_q, _mode='keep'):
        # Update 111: ek sath 6-10 page-bursts par YouTube aksar
        # khali page de deta hai (taza live par 0 araha tha) — is
        # liye ek waqt mein 2 se zyada fetch nahi, n=30 (feed wali
        # cache share hoti hai), aur khali jawab par ek dobara
        # koshish.
        with _sem:
            try:
                _items = _dated_search_items(_q, 30)
                if not _items:
                    time.sleep(1.5)
                    _items = _dated_search_items(_q, 30)
            except Exception:
                return
        with _lock:
            for _it in _items or []:
                _am = _it.get('age_min')
                if _am is None or _am > 30 * 60:
                    continue
                _vid = ((_it.get('id') or {}).get('videoId') or '')
                if not _vid or _vid in _found:
                    continue
                _sn = _it.get('snippet') or {}
                _ttl = _sn.get('title') or ''
                if _mode == 'hide' and _ai_is_teaser(_ttl):
                    continue
                if _mode == 'only' and not _ai_is_teaser(_ttl):
                    continue
                _found[_vid] = {
                    'video_id': _vid,
                    'title': _sn.get('title') or '',
                    'channel': _sn.get('channelTitle') or '',
                    'duration': _it.get('duration'),
                    'view_count': _it.get('view_count'),
                    'timestamp': 0,
                    'age': _it.get('age_text') or '',
                    '_amin': _am}

    _ths = [threading.Thread(target=_one, args=_qm, daemon=True)
            for _qm in _queries]
    for _t in _ths:
        _t.start()
    for _t in _ths:
        _t.join(timeout=45)
    _out = sorted(_found.values(), key=lambda x: x.get('_amin') or 0)[:50]
    for _o in _out:
        _o.pop('_amin', None)
    return jsonify({'success': True, 'kind': kind, 'candidates': _out})


@app.route('/api/ai/command', methods=['POST'])
def api_ai_command():
    data = request.json or {}
    # Update 109: '↗ Isi jaisi aur' — text command nahi, seedha data
    if data.get('similar'):
        if not feature_enabled('ai_enabled'):
            return jsonify({'error': 'AI Assistant abhi band hai (admin ne off kiya hai)',
                            'ai_disabled': True}), 403
        _sc = _ai_similar_candidates(data.get('similar') or {})
        return jsonify({'success': True, 'intent': 'candidates',
                        'parsed': {'quality': '360p', 'format': 'mp4',
                                   'category': ''},
                        'candidates': _sc, 'qexp': False, 'show': '',
                        'message': 'Milti julti videos:'})
    text = data.get('command') or data.get('text') or ''
    if not text.strip():
        return jsonify({'error': 'Command required'}), 400
    if not feature_enabled('ai_enabled'):
        return jsonify({'error': 'AI Assistant abhi band hai (admin ne off kiya hai)',
                        'ai_disabled': True}), 403
    parsed = ai_parse_command(text)

    # v9: pehle CHAT — salam / shukriya / madad par dostana jawab, job nahi.
    _low = ' ' + re.sub(r'\s+', ' ', text.lower().strip()) + ' '
    _chat = None
    if any(w in _low for w in (' shukriya ', ' shukria ', ' thanks ', ' thank you ')):
        _chat = 'Bohat khushi hui madad karke! 😊 Aur kuch download karna ho to bas naam likh dein.'
    elif any(p in _low for p in ('madad', ' help ', 'kya kar sakte', 'kya kar sakta', 'tum kon', 'tum kaun', 'kaun ho', 'kon ho', 'naam kya', 'how to', 'kaise kar')):
        _chat = ('Main ye kar sakta hun:\n'
                 '• Naam bolne par video / gana / drama / movie download\n'
                 '• Episodes ki poori list — jaise "Shiva 10 episodes"\n'
                 '• MP3 gana — naam ke sath "mp3" likhein\n'
                 '• Episode range — "Bano episode 1 sy 20 tk"\n'
                 '• Latest episodes — "Shiva ki latest 20 episodes"\n'
                 '• Naam adhoora ho to main khud sawal kar lunga 👍\n'
                 '• YouTube link bhejne par seedha wahi video\n'
                 'Bas naam likh dein, baqi mera kaam hai. 👍')
    elif any(w in _low for w in (' salam ', ' assalamualaikum ', ' assalam ', ' hello ', ' hi ', ' hey ', ' aoa ')) and len(_low.split()) <= 5 and not parsed.get('category') and not parsed.get('episodes'):
        _chat = 'Wa-alaikum assalam! 👋 Main Playza ka AI hun. Koi video, gana, drama ya movie download karni ho to bas naam likh dein — jaise "Motu Patlu episode 5" ya "new punjabi songs 5". 😊'
    if _chat:
        return jsonify({'success': True, 'intent': 'chat', 'message': _chat})

    # Update 79: AI par bhi wohi shared guest limit jo har download par
    # hai — limit baqi ho to bina account ke download hoga; limit khatam
    # ho tab hi sign-in manga jayega. (Purana "AI = account lazmi" khatam)
    _ai_guest_device = None
    if parsed['intent'] in ('download', 'playlist') and not session.get('user_id'):
        _gl = get_guest_limit()
        if _gl <= 0:
            return jsonify({'error': 'Download ke liye pehle account banayein / sign in karein',
                            'login_required': True}), 403
        _ai_guest_device = _guest_device_id()
        if _guest_count(_ai_guest_device) >= _gl:
            return jsonify({'error': f'Guest ke {_gl} free downloads pure ho gaye — ab account banayein!',
                            'login_required': True, 'guest_limit': True,
                            'limit': _gl}), 403

    # Update 109: Channel Mode — 'channel:<naam>' ya ready list ke
    # channel ka EXACT naam = us channel ki latest 50 ki list.
    _ch_name = None
    if text.lower().startswith('channel:'):
        _ch_name = text.split(':', 1)[1].strip()
    elif text.strip().lower() in {c.lower() for c in _AI_CHANNELS_ALL}:
        _ch_name = text.strip()
    if _ch_name:
        _cc = _ai_channel_candidates(_ch_name)
        if _cc:
            return jsonify({
                'success': True, 'intent': 'candidates',
                'parsed': {'quality': '360p', 'format': 'mp4',
                           'category': '', 'title': _ch_name},
                'candidates': _cc, 'qexp': False, 'show': '', 'src': '📂 ' + _ch_name,
                'message': (f"📂 {_ch_name} — latest {len(_cc)} videos "
                            f"— jin par ✓ select karein ge, sirf wahi "
                            f"download hongi:")})
        return jsonify({'success': False,
                        'message': (f"😔 '{_ch_name}' ki videos abhi nahi "
                                    f"mil sakein — thodi dair baad try "
                                    f"karein.")})

    # Update 43: AI ko LINK do to search ghumaye baghair seedha download —
    # video link = wohi video, playlist link = poori playlist (pehli 50)
    _urlm = re.search(r'https?://\S+', text)
    if _urlm and parsed['intent'] in ('download', 'playlist'):
        _url = _urlm.group(0).rstrip('.,)')
        _vidm = re.search(r'(?:v=|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})', _url)
        _listm = re.search(r'[?&]list=([A-Za-z0-9_-]+)', _url)
        _want_pl = bool(_listm) and (parsed['intent'] == 'playlist'
                                     or 'playlist' in _url or not _vidm)
        if _want_pl:
            _pl = _ai_playlist_candidates(_listm.group(1),
                                          _vidm.group(1) if _vidm else None)
            if _pl:
                _cands, _pl_title = _pl
                parsed['title'] = _pl_title or 'Playlist'
                parsed['episodes'] = []
                return jsonify({'success': True, 'intent': 'candidates',
                                'parsed': parsed, 'candidates': _cands,
                                'qexp': False, 'show': '', 'kind': 'playlist',
                                'src': '🔗 ' + (_pl_title or 'Playlist'),
                                'message': (f"🔗 Playlist '{_pl_title or ''}' — "
                                            f"{len(_cands)} videos mil gayin. "
                                            f"Jin par ✓ select karein ge, sirf "
                                            f"wahi download hongi:")})
            return jsonify({'success': False, 'parsed': parsed,
                            'message': '😔 Playlist khul nahi saki — link check karke dobara bhejein.'})
        _direct = None
        if _vidm:
            _t = _video_meta(_vidm.group(1))
            _direct = [{'video_id': _vidm.group(1), 'title': _t or 'Video'}]
            parsed['title'] = _direct[0]['title']
        if _direct:
            parsed['episodes'] = []
            _jid = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
            _job = {'job_id': _jid, 'command': text, 'parsed': parsed,
                    'status': 'queued', 'run_at_epoch': time.time(),
                    'created_at': datetime.now().isoformat(),
                    'direct_items': _direct,
                    'guest_device': _ai_guest_device,
                    'episodes_status': [{'episode': None, 'status': 'pending',
                                         'title': _it['title']} for _it in _direct],
                    'completed_count': 0, 'total_count': len(_direct)}
            with ai_jobs_lock:
                ai_jobs[_jid] = _job
                _save_ai_jobs()
            _th = threading.Thread(target=_ai_run_job, args=(_jid,))
            _th.daemon = True
            _th.start()
            _q = parsed['quality'] if parsed['format'] == 'mp4' else 'MP3'
            return jsonify({'success': True, 'intent': 'download',
                            'job_id': _jid, 'parsed': parsed,
                            'message': (f"🔗 Link mil gaya! '{parsed['title']}' ki "
                                        f"{len(_direct)} video(s) {_q} me download start kar di hain. "
                                        f"Background me one by one hongi. Job ID: {_jid}")})

    # Non-download intents handled instantly
    if parsed['intent'] == 'search':
        items = []
        try:
            info = _extract_with_clients(
                f"ytsearch10:{parsed['title']}",
                {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
                 'extract_flat': True, 'skip_download': True,
                 'ignoreerrors': True})
            for e in (info or {}).get('entries') or []:
                if e and e.get('id'):
                    items.append({'video_id': e['id'],
                                  'title': e.get('title', '')})
        except Exception:
            pass
        return jsonify({'success': True, 'intent': 'search', 'parsed': parsed,
                        'results': items,
                        'message': f"🔎 '{parsed['title']}' ke {len(items)} results mil gaye."})
    if parsed['intent'] in ('thumbnail', 'subtitles'):
        vid, vtitle = _ai_search_first(parsed['title'])
        if not vid:
            return jsonify({'success': False, 'parsed': parsed,
                            'message': '😔 Video search me nahi mila. Naam dobara likh kar try karein.'})
        kind = 'thumbnail' if parsed['intent'] == 'thumbnail' else 'subtitles'
        return jsonify({'success': True, 'intent': kind, 'parsed': parsed,
                        'video_id': vid, 'title': vtitle,
                        'url': f'/api/download-{kind}/{vid}',
                        'message': f"✅ Mil gaya: {vtitle}. {kind.title()} ka link tayyar hai."})
    if parsed['intent'] == 'playlist':
        urlm = re.search(r'https?://\S+', text)
        if urlm:
            did = f"playlist_{int(time.time())}_{random.randint(1000, 9999)}"
            download_progress[did] = {'status': 'starting', 'percent': 0,
                                      'speed': '', 'error': None, 'type': 'playlist'}
            th = threading.Thread(target=download_playlist_in_background,
                                  args=(urlm.group(0), parsed['format'], did))
            th.daemon = True
            th.start()
            return jsonify({'success': True, 'intent': 'playlist',
                            'download_id': did, 'parsed': parsed,
                            'message': '▶️ Playlist download background me start kar di hai.'})
        # no URL: treat as normal series download below
        parsed['intent'] = 'download'



    # Update 102/105: PEHLE DIKHAO, PHIR DOWNLOAD — HAR command par
    # AI khud video NAHI chunta. Latest 20 results user ko dikhaye
    # jate hain; user jin par select kare SIRF wahi download hoti
    # hain (auto-download ka khatma — count / range / latest bhi
    # pehle list dikhate hain). Sirf link aur schedule purane flow
    # par chalte hain.
    def _cand_response():
        _eps = parsed.get('episodes') or []
        if len(_eps) > 1 or parsed.get('latest_count'):
            _cands = _ai_episode_candidates(parsed)
            if not _cands:
                _cands = _ai_candidates(parsed)
        elif parsed.get('title') and parsed.get('title') != 'Video':
            _cands = _ai_candidates(parsed)
        else:
            _catw = {'movie': 'full movie', 'song': 'song',
                     'naat': 'naat', 'drama': 'drama episode',
                     'cartoon': 'cartoon episode', 'bayan': 'bayan',
                     'shorts': 'shorts',
                     'video': ''}.get(parsed.get('category') or '', 'video')
            _q2 = ' '.join(x for x in [parsed.get('lang') or '',
                                       _catw, 'new latest'] if x).strip()
            _cands = _ai_candidates(parsed, query=_q2)
        if not _cands:
            return None
        _qexp2 = bool(re.search(
            r'\d{3,4}\s*p\b|3gp|\bmp3\b|\bm4a\b', text.lower()))
        _lbl = parsed.get('title') or parsed.get('category') or ''
        return jsonify({
            'success': True, 'intent': 'candidates',
            'parsed': parsed, 'candidates': _cands,
            'qexp': _qexp2, 'show': parsed.get('title') or '',
            'message': (f"🔎 '{_lbl}' ke ye {len(_cands)} results mile "
                        f"— jin par ✓ select karein ge, sirf wahi "
                        f"download hongi:")})

    if parsed['intent'] == 'download' and not _urlm \
            and not parsed.get('schedule_at') \
            and not parsed.get('schedule_in_seconds') \
            and (parsed.get('title') or parsed.get('category')):
        # Sawal pehle se pending ho to ye text us ka jawab ho sakta
        # hai — us surat mein purana sawal-wala flow hi chale.
        _fk2 = (f"u{session.get('user_id')}" if session.get('user_id')
                else _guest_device_id())
        import hashlib as _hl2
        _hk2 = 'h_' + _hl2.md5(((request.remote_addr or '') + '|'
                                + (request.headers.get('User-Agent')
                                   or '')).encode()).hexdigest()
        _has_pend = any((_ai_ctx_get(_k) or {}).get('pending')
                        for _k in {_fk2, _hk2})
        if not _has_pend:
            _cr = _cand_response()
            if _cr is not None:
                return _cr
            return jsonify({
                'success': False, 'parsed': parsed,
                'message': (f"😔 '{parsed.get('title') or ''}' ke liye "
                            f"koi result nahi mila — naam thoda badal "
                            f"kar try karein.")})

    # v16: SAWAL WALA FLOW — naam / count / quality adhoora ho to AI
    # pehle SAWAL kare ga; khud se ghalat (fake) cheez download nahi hogi.
    _flow_done = False
    if parsed['intent'] == 'download' and not parsed.get('schedule_at') \
            and not parsed.get('schedule_in_seconds') and not _urlm:
        _fk = (f"u{session.get('user_id')}" if session.get('user_id')
               else _guest_device_id())
        _qexp = bool(re.search(r'\d{3,4}\s*p\b|3gp|\bmp3\b|\bm4a\b',
                               text.lower()))
        # pt_guest cookie pehli response par set hota hai — us se pehle
        # wala hash-key pending bhi parhna hai, warna flow toot jata hai.
        import hashlib as _hl
        _hkey = 'h_' + _hl.md5(((request.remote_addr or '') + '|'
                                + (request.headers.get('User-Agent')
                                   or '')).encode()).hexdigest()
        _keys = [_fk] + ([_hkey] if _hkey != _fk else [])

        def _clear_pend_all():
            for _k in _keys:
                _c = _ai_ctx_get(_k) or {}
                if 'pending' in _c:
                    _c.pop('pending', None)
                    _ai_ctx_set(_k, _c)

        def _ask(step, msg, p, options=None):
            _c = _ai_ctx_get(_fk) or {}
            _c['pending'] = {'step': step, 'title': p.get('title') or '',
                             'category': p.get('category'),
                             'count': p.get('count'),
                             'latest_count': p.get('latest_count'),
                             'episodes': p.get('episodes') or [],
                             'quality': p.get('quality') or '360p',
                             'format': p.get('format') or 'mp4',
                             'lang': p.get('lang'), 'qexp': _qexp}
            _ai_ctx_set(_fk, _c)
            _r = {'success': True, 'intent': 'question', 'message': msg,
                  'parsed': p}
            if options:
                _r['options'] = options
            return jsonify(_r)

        def _next_q(p, qexp):
            _cat = p.get('category')
            _catw2 = {'tiktok', 'tiktoks', 'short', 'shorts', 'reel',
                      'reels', 'drama', 'serial', 'series', 'movie',
                      'film', 'song', 'songs', 'gana', 'gaane', 'naat',
                      'cartoon', 'video', 'videos', 'bayan'}
            _has = bool([w for w in re.findall(
                r'[a-z0-9]+', (p.get('title') or '').lower())
                if w not in _catw2])
            if not _has and not p.get('episodes'):
                if _cat in ('shorts', 'drama', 'cartoon', 'movie', 'naat',
                            'bayan', None):
                    return 'name'
                return None
            if _cat == 'shorts' and not p.get('count') \
                    and not p.get('episodes'):
                return 'count'
            if _cat == 'shorts' and not qexp:
                return 'quality'
            if _cat in ('drama', 'cartoon') and _has \
                    and not p.get('episodes') and not p.get('count') \
                    and not p.get('latest_count'):
                return 'episodes'
            return None

        def _qtext(step, p):
            _t = p.get('title') or ''
            if step == 'name':
                if p.get('category') == 'shorts':
                    return ('Kis ke TikTok / Shorts download karun? '
                            'Naam batayein — jaise kisi cartoon, actor ya '
                            'topic ka naam likh dein.'), None
                if p.get('category') == 'drama':
                    return ('Kis drama ke download karun? '
                            'Drama ka naam batayein.'), None
                if p.get('category') == 'movie':
                    return 'Kis movie ka naam hai? Naam batayein.', None
                if p.get('category') == 'cartoon':
                    return 'Kis cartoon ke download karun? Naam batayein.', None
                return ('Download ke liye naam batayein — kis video, '
                        'gane, drama ya cartoon ka naam hai?'), None
            if step == 'count':
                return (f"'{_t}' ke kitne chahiye?",
                        ['10', '20', '50', '100'])
            if step == 'quality':
                return ('Kis quality mein download karun?',
                        ['360p', '720p', '1080p'])
            return (f"'{_t}' ki kaunsi episodes chahiye? Episode number "
                    'likh dein — jaise: 10 11 12 13 14 — ya kitni videos '
                    'chahiye, wo number likh dein.',
                    ['Episode 1', '5 episodes', '10 episodes'])

        _pend = None
        for _k in _keys:
            _c0 = _ai_ctx_get(_k) or {}
            if _c0.get('pending'):
                _pend = _c0['pending']
                break
        if _pend:
            _ans = ai_parse_command(text)
            _new_cmd = bool(_ans.get('title')) \
                and _ans['title'] != 'Video' \
                and bool(re.search(r'[a-zA-Z]', _ans['title'])) \
                and (bool(_ans.get('episodes')) or bool(_ans.get('count'))) \
                and _pend.get('step') != 'name' \
                and (_ans['title'].lower()
                     not in (_pend.get('title') or '').lower())
            if _new_cmd:
                _clear_pend_all()
                _pend = None
            else:
                _mg = {'raw': text, 'intent': 'download',
                       'title': _pend.get('title') or '',
                       'episodes': list(_pend.get('episodes') or []),
                       'quality': _pend.get('quality') or '360p',
                       'format': _pend.get('format') or 'mp4',
                       'schedule_at': None, 'schedule_in_seconds': None,
                       'category': _pend.get('category'),
                       'count': _pend.get('count'),
                       'latest_count': _pend.get('latest_count'),
                       'lang': _pend.get('lang')}
                if _ans.get('title') and _ans['title'] != 'Video' \
                        and re.search(r'[a-zA-Z]', _ans['title']):
                    _mg['title'] = _ans['title']
                if _ans.get('episodes'):
                    _mg['episodes'] = _ans['episodes']
                if _ans.get('count'):
                    _mg['count'] = _ans['count']
                if _ans.get('latest_count'):
                    _mg['latest_count'] = _ans['latest_count']
                if _ans.get('category'):
                    _mg['category'] = _ans['category']
                if _ans.get('lang'):
                    _mg['lang'] = _ans['lang']
                if _qexp:
                    _mg['quality'] = _ans.get('quality') or _mg['quality']
                    if _ans.get('format'):
                        _mg['format'] = _ans['format']
                _nums = [int(x) for x in re.findall(r'\d+', text)]
                if _pend.get('step') == 'count' and _nums \
                        and not _mg.get('count'):
                    _mg['count'] = max(1, min(100, _nums[0]))
                if _pend.get('step') == 'episodes' and _nums \
                        and not _mg.get('episodes') \
                        and not _mg.get('count'):
                    if len(_nums) >= 2 and max(_nums) - min(_nums) <= 200:
                        _mg['episodes'] = sorted(set(_nums))[:100]
                    else:
                        _mg['episodes'] = _nums[:1]
                if _pend.get('step') == 'quality' and _nums and not _qexp:
                    if 100 <= _nums[0] <= 4320:
                        _mg['quality'] = f"{_nums[0]}p"
                parsed = _mg
                _qexp = _qexp or bool(_pend.get('qexp'))
                _escape = _pend.get('step') == 'name' and (
                    not parsed.get('title') or parsed['title'] == 'Video')
                if _escape:
                    # naam ki jagah aam jawab (jaise "viral wale") — aam
                    # category batch chala do, sawal ka chakkar khatam.
                    parsed['title'] = ''
                    if not parsed.get('count'):
                        parsed['count'] = 10
                    _step = None
                else:
                    _step = _next_q(parsed, _qexp)
                _changed = (_mg.get('title') or '') != (_pend.get('title') or '') \
                    or (_mg.get('episodes') or []) != list(_pend.get('episodes') or []) \
                    or (_mg.get('category') or '') != (_pend.get('category') or '')
                if _step and _step == _pend.get('step') and not _changed:
                    # wohi sawal dobara — default maan kar aage barho
                    if _step == 'count':
                        parsed['count'] = parsed.get('count') or 10
                    elif _step == 'episodes':
                        parsed['count'] = parsed.get('count') or 10
                    elif _step == 'quality':
                        _qexp = True
                    _step = _next_q(parsed, _qexp)
                    if _step == _pend.get('step'):
                        _step = None
                if _step:
                    _m, _o = _qtext(_step, parsed)
                    return _ask(_step, _m, parsed, _o)
                _clear_pend_all()
                _flow_done = True
        if not _flow_done and not _pend:
            _step = _next_q(parsed, _qexp)
            if _step:
                _m, _o = _qtext(_step, parsed)
                return _ask(_step, _m, parsed, _o)

    # v11: follow-up context — "50 kro", "aur 20", "720p mein karo"
    # pichle topic par hi lagein, nayi search na bane.
    _ai_key = (f"u{session.get('user_id')}" if session.get('user_id')
               else _guest_device_id())
    _ctx = _ai_ctx_get(_ai_key)
    if _ctx and not _flow_done and parsed.get('intent') == 'download' \
            and not parsed.get('episodes') and not parsed.get('schedule') \
            and not _urlm:
        _fill = {'kro', 'karo', 'kar', 'do', 'download', 'aur', 'or',
                 'please', 'ab', 'phir', 'mein', 'me', 'bhi', 'toh',
                 'song', 'songs', 'gana', 'gaane', 'geet', 'movie',
                 'movies', 'film', 'films', 'video', 'videos', 'naat',
                 'naats', 'drama', 'dramas', 'cartoon', 'cartoons',
                 'short', 'shorts', 'reel', 'reels', 'tiktok', 'tiktoks',
                 'mp3', 'mp4', '3gp'}
        _toks = re.findall(r'[a-z0-9]+', text.lower())
        _rest = [w for w in _toks if w not in _fill and not w.isdigit()
                 and not re.fullmatch(r'\d{3,4}p', w)]
        if not _rest and len(_toks) <= 6:
            _nums = [w for w in _toks if w.isdigit()]
            if _nums:
                parsed['count'] = max(1, min(100, int(_nums[0])))
            elif not parsed.get('count'):
                parsed['count'] = _ctx.get('count')
            if not parsed.get('title') or parsed.get('title') == 'Video':
                parsed['title'] = _ctx.get('title') or parsed.get('title')
            if not parsed.get('category'):
                parsed['category'] = _ctx.get('category')
            if _ctx.get('quality') and not re.search(
                    r'\d{3,4}p|3gp', text.lower()):
                parsed['quality'] = _ctx['quality']
            if _ctx.get('format'):
                parsed['format'] = _ctx['format']

    # Update 105: sawal-wale flow ya follow-up ("50 kro") se poori
    # hui command bhi pehle LIST dikhayegi — auto job nahi banegi.
    if parsed['intent'] == 'download' and not _urlm \
            and not parsed.get('schedule_at') \
            and not parsed.get('schedule_in_seconds') \
            and (parsed.get('title') or parsed.get('category')):
        _cr2 = _cand_response()
        if _cr2 is not None:
            return _cr2
        return jsonify({
            'success': False, 'parsed': parsed,
            'message': (f"😔 '{parsed.get('title') or ''}' ke liye koi "
                        f"result nahi mila — naam thoda badal kar try "
                        f"karein.")})

    # v9: count / category-only requests — seedhi list (direct items).
    if parsed['intent'] == 'download' and parsed.get('category') \
            and (parsed.get('count') or not parsed.get('title')):
        _catw = {'movie': 'full movie', 'song': 'song', 'naat': 'naat',
                 'drama': 'drama episode', 'cartoon': 'cartoon episode',
                 'bayan': 'bayan', 'shorts': 'shorts',
                 'video': ''}.get(parsed['category'], 'video')
        _q = ' '.join(x for x in [parsed.get('lang') or '',
                                  parsed.get('title') or '', _catw,
                                  '' if parsed.get('title') else 'new latest'] if x).strip()
        _want = parsed.get('count') or 10
        _items = []
        if parsed.get('category') == 'shorts':
            for _e in _shorts_feed_items(_q, _want):
                _vid = (_e.get('id') or {}).get('videoId')
                if _vid:
                    _items.append({'video_id': _vid,
                                   'title': ((_e.get('snippet') or {})
                                             .get('title') or _q)})
                if len(_items) >= _want:
                    break
        else:
            try:
                _info = _extract_with_clients(
                    f"ytsearch{max(_want, 10)}:{_q}",
                    {'quiet': True, 'no_warnings': True,
                     'no_check_certificate': True, 'extract_flat': True,
                     'skip_download': True, 'ignoreerrors': True})
                for _e in (_info or {}).get('entries') or []:
                    if _e and _e.get('id'):
                        _items.append({'video_id': _e['id'],
                                       'title': _e.get('title', _q)})
                    if len(_items) >= _want:
                        break
            except Exception:
                _items = []
        if _items:
            _dd = set()
            _items = [x for x in _items
                      if not (x['video_id'] in _dd or _dd.add(x['video_id']))]
        # v16: STRICT match — naam diya ho to sirf wahi items download hon
        # jin ke title mein naam ke alfaaz hon. Ghalat (fake) cheez nahi.
        _tkws = [w for w in re.findall(r'[a-z0-9]+',
                                       (parsed.get('title') or '').lower())
                 if len(w) >= 3 and w not in ('the', 'new', 'video',
                                              'videos', 'full', 'episode',
                                              'episodes')]
        if _tkws and _items:
            _need = max(1, int(len(_tkws) * 0.6))
            _items = [x for x in _items
                      if sum(1 for k in _tkws
                             if k in (x.get('title') or '').lower()) >= _need]
        if not _items:
            return jsonify({'success': False, 'parsed': parsed,
                            'message': f"😔 '{_q}' ke liye kuch nahi mila — naam thoda badal kar try karein."})
        if data.get('phone_mode'):
            # Update 103: APK mein ye videos PHONE par utarti hain —
            # server wala bot-check in par nahi lagta.
            return jsonify({'success': True, 'intent': 'phone_job',
                            'parsed': parsed, 'items': _items,
                            'message': (f"🎵 '{_q}' ki {len(_items)} videos "
                                        f"phone par download start kar di "
                                        f"hain — one by one hongi.")})
        _jid = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
        _job = {'job_id': _jid, 'command': text, 'parsed': parsed,
                'status': 'queued', 'run_at_epoch': time.time(),
                'created_at': datetime.now().isoformat(),
                'direct_items': _items,
                'guest_device': _ai_guest_device,
                'episodes_status': [{'episode': None, 'status': 'pending',
                                     'title': _it['title']} for _it in _items],
                'completed_count': 0, 'total_count': len(_items)}
        with ai_jobs_lock:
            ai_jobs[_jid] = _job
            _save_ai_jobs()
        _th = threading.Thread(target=_ai_run_job, args=(_jid,))
        _th.daemon = True
        _th.start()
        _ai_ctx_set(_ai_key, {'title': parsed.get('title') or '', 'category': parsed.get('category'), 'quality': parsed.get('quality'), 'format': parsed.get('format'), 'count': parsed.get('count')})
        return jsonify({'success': True, 'intent': 'download',
                        'job_id': _jid, 'parsed': parsed,
                        'message': (f"🎵 '{_q}' ki {len(_items)} videos download start kar di hain. "
                                    f"Pehli: '{_items[0]['title']}' — baqi one by one hongi. Job ID: {_jid}")})

    # v9: single download — pehle dhoond kar DETAILS ke sath jawab;
    # mili hui video hi job mein jati hai (ghalat video nahi utarti).
    if parsed['intent'] == 'download' and not parsed.get('episodes') \
            and not parsed.get('latest_count') \
            and not parsed.get('schedule_at') \
            and not parsed.get('schedule_in_seconds') and parsed.get('title') \
            and parsed.get('title') != 'Video':
        _vid, _vt, _entry = _ai_pick_entry(parsed)
        if _vid:
            _direct = [{'video_id': _vid, 'title': _vt or parsed['title']}]
            _jid = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
            _job = {'job_id': _jid, 'command': text, 'parsed': parsed,
                    'status': 'queued', 'run_at_epoch': time.time(),
                    'created_at': datetime.now().isoformat(),
                    'direct_items': _direct,
                    'guest_device': _ai_guest_device,
                    'episodes_status': [{'episode': None, 'status': 'pending',
                                         'title': _direct[0]['title']}],
                    'completed_count': 0, 'total_count': 1}
            with ai_jobs_lock:
                ai_jobs[_jid] = _job
                _save_ai_jobs()
            _th = threading.Thread(target=_ai_run_job, args=(_jid,))
            _th.daemon = True
            _th.start()
            _ai_ctx_set(_ai_key, {'title': parsed.get('title') or '', 'category': parsed.get('category'), 'quality': parsed.get('quality'), 'format': parsed.get('format'), 'count': parsed.get('count')})
            _entry = _entry or {}
            _ch = _entry.get('channel') or _entry.get('uploader') or ''
            _dur = int(_entry.get('duration') or 0)
            _durt = ''
            if _dur:
                _durt = (f"{_dur // 3600}:{(_dur % 3600) // 60:02d}:{_dur % 60:02d}"
                         if _dur >= 3600 else f"{_dur // 60}:{_dur % 60:02d}")
            _det = ' • '.join(x for x in [_ch, _durt] if x)
            _q = parsed['quality'] if parsed['format'] == 'mp4' else 'MP3'
            return jsonify({'success': True, 'intent': 'download',
                            'job_id': _jid, 'parsed': parsed,
                            'message': (f"🤖 Mil gayi! '{_direct[0]['title']}'"
                                        + (f" ({_det})" if _det else '')
                                        + f" — {_q} mein download start kar di hai. Job ID: {_jid}")})

    # v9: naam hi nahi diya — job nahi, rehnumai wala jawab.
    if parsed['intent'] == 'download' and not parsed.get('category') \
            and not parsed.get('count') and not parsed.get('episodes') \
            and (not parsed.get('title') or parsed.get('title') == 'Video'):
        return jsonify({'success': True, 'intent': 'chat',
                        'message': 'Samajh nahi aya — download ke liye video ka naam likhein, jaise "Ertugrul episode 1", "Atif Aslam new song" ya "Hindi full movie".'})

    # Update 103: APK mein downloads PHONE par — episodes pehle yahin
    # resolve karke list wapas; server job nahi banti (bot-check se
    # phone wali downloads mehfooz hain). Schedule ho to purana rasta.
    if data.get('phone_mode') and not parsed.get('schedule_at') \
            and not parsed.get('schedule_in_seconds'):
        _peps = list(parsed.get('episodes') or [None])
        if parsed.get('latest_count'):
            _want2 = int(parsed['latest_count'])
            _nums2 = set()
            try:
                _info2 = _extract_with_clients(
                    f"ytsearch30:{parsed['title']} episode",
                    {'quiet': True, 'no_warnings': True,
                     'no_check_certificate': True, 'extract_flat': True,
                     'skip_download': True, 'ignoreerrors': True,
                     'socket_timeout': 20, 'retries': 2,
                     'extractor_retries': 2})
                for _e2 in (_info2 or {}).get('entries') or []:
                    if not _e2:
                        continue
                    _m2 = re.search(r'episode\s*#?\s*(\d+)',
                                    (_e2.get('title') or '').lower())
                    if _m2:
                        _nums2.add(int(_m2.group(1)))
            except Exception:
                _nums2 = set()
            _peps = sorted(_nums2)[-_want2:] if _nums2 \
                else list(range(1, _want2 + 1))
        _pitems = []
        for _ep2 in _peps:
            if _ep2:
                _v2, _t2, _f2 = _ai_find_episode(parsed.get('title') or '', _ep2)
            else:
                _v2, _t2, _e3 = _ai_pick_entry(parsed)
            if _v2:
                _pitems.append({'video_id': _v2,
                                'title': _t2 or parsed.get('title')
                                or 'Video'})
        if _pitems:
            return jsonify({'success': True, 'intent': 'phone_job',
                            'parsed': parsed, 'items': _pitems,
                            'message': (f"📱 {len(_pitems)} videos phone "
                                        f"par download start kar di hain "
                                        f"— one by one hongi.")})

    # Download job (episodes, one by one, background)
    job_id = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
    run_at = time.time()
    when_text = 'abhi'
    if parsed.get('schedule_at'):
        try:
            run_at = datetime.fromisoformat(parsed['schedule_at']).timestamp()
            when_text = parsed['schedule_at'].replace('T', ' ')
        except Exception:
            pass
    if parsed.get('schedule_in_seconds'):
        run_at = time.time() + parsed['schedule_in_seconds']
        when_text = f"{parsed['schedule_in_seconds'] // 60} minute baad"
    episodes = parsed.get('episodes') or [None]
    job = {
        'job_id': job_id, 'command': text, 'parsed': parsed,
        'status': 'scheduled' if run_at > time.time() + 5 else 'queued',
        'run_at_epoch': run_at, 'created_at': datetime.now().isoformat(),
        'episodes_status': [{'episode': ep, 'status': 'pending'} for ep in episodes],
        'guest_device': _ai_guest_device,
        'completed_count': 0, 'total_count': len(episodes)
    }
    with ai_jobs_lock:
        ai_jobs[job_id] = job
        _save_ai_jobs()
    if job['status'] == 'queued':
        th = threading.Thread(target=_ai_run_job, args=(job_id,))
        th.daemon = True
        th.start()

    if parsed.get('latest_count'):
        ep_text = f"latest {parsed['latest_count']} episodes"
    else:
        ep_text = (f"episodes {episodes[0]} to {episodes[-1]}" if len(episodes) > 1
                   else (f"episode {episodes[0]}" if episodes[0] else 'video'))
    q_text = parsed['quality'] if parsed['format'] == 'mp4' else (
        f"MP3 {parsed['quality']}K" if parsed['format'] == 'mp3' else 'M4A')
    msg = (f"🤖 Samajh gaya! '{parsed['title']}' ki {ep_text} "
           f"{q_text} me download {'schedule kar di hai (' + when_text + ')' if job['status'] == 'scheduled' else 'start kar di hai'}. "
           f"Background me one by one chalti rahe gi. Job ID: {job_id}")
    _ai_ctx_set(_ai_key, {'title': parsed.get('title') or '', 'category': parsed.get('category'), 'quality': parsed.get('quality'), 'format': parsed.get('format'), 'count': parsed.get('count')})
    return jsonify({'success': True, 'intent': 'download', 'job_id': job_id,
                    'parsed': parsed, 'message': msg})


def _ocr_image(path):
    """Tesseract se pic ka text parho. Binary na ho to None."""
    try:
        r = subprocess.run(['tesseract', path, 'stdout', '--psm', '6'],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return r.stdout or ''
    except Exception:
        pass
    return None


def _ocr_pick_title(ocr_text):
    """OCR text se video ke title jaisi line chuno (Update 43)."""
    lines = []
    for ln in (ocr_text or '').splitlines():
        ln = re.sub(r'\s+', ' ', ln).strip(' |•·-–—')
        if len(ln) >= 4 and re.search(r'[A-Za-z]', ln):
            lines.append(ln)
    if not lines:
        return ''
    # UI junk lines hatao (views / subscribe / time waghera)
    junk = ('views', 'subscribe', 'watching', 'premiered', 'streamed',
            'subscribers', 'like', 'share', 'download')
    good = [l for l in lines if not any(j in l.lower() for j in junk)]
    pick = (good or lines)[:2]
    title = ' '.join(pick)
    title = re.sub(r'[^A-Za-z0-9 ]', ' ', title)
    return re.sub(r'\s+', ' ', title).strip()


@app.route('/api/ai/image', methods=['POST'])
def api_ai_image():
    """Update 43/115: AI ko pic do — title parh kar khud download start.
    Update 115: poora handler mehfooz — kabhi khaam 500 nahi; OCR temp
    DATA_DIR mein na likh sakay to system temp par girta hai; jagah
    50MB se kam ho to pehle storage cleanup ek dafa."""
    _img_guest_device = None
    if not session.get('user_id'):
        _gl = get_guest_limit()
        if _gl <= 0:
            return jsonify({'error': 'Download ke liye pehle account banayein / sign in karein',
                            'login_required': True}), 403
        _img_guest_device = _guest_device_id()
        if _guest_count(_img_guest_device) >= _gl:
            return jsonify({'error': f'Guest ke {_gl} free downloads pure ho gaye — ab account banayein!',
                            'login_required': True, 'guest_limit': True,
                            'limit': _gl}), 403
    if not feature_enabled('ai_enabled'):
        return jsonify({'error': 'AI Assistant abhi band hai (admin ne off kiya hai)'}), 403
    try:
        data = request.json or {}
        b64 = (data.get('image') or '').split(',')[-1]
        if not b64:
            return jsonify({'success': False, 'message': 'Pic mili nahi — dobara bhejein.'}), 400
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return jsonify({'success': False, 'message': 'Pic sahi nahi ayi — dobara bhejein.'}), 400
        if len(raw) > 7 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'Pic bohat bari hai — chhoti pic bhejein.'}), 400
        try:
            if shutil.disk_usage(DATA_DIR).free < 50 * 1024 * 1024:
                _storage_cleanup()
        except Exception:
            pass
        path = None
        try:
            _td = os.path.join(DATA_DIR, 'ocr_tmp')
            os.makedirs(_td, exist_ok=True)
            _tf = tempfile.NamedTemporaryFile(delete=False, dir=_td, suffix='.jpg')
            _tf.write(raw)
            _tf.close()
            path = _tf.name
        except OSError:
            try:
                _tf = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                _tf.write(raw)
                _tf.close()
                path = _tf.name
            except Exception:
                path = None
        if not path:
            return jsonify({'success': False,
                            'message': 'Pic save nahi ho saki — server ki jagah ka masla hai, thodi dair baad try karein.'})
        try:
            try:
                text = _ocr_image(path)
            except Exception:
                text = None
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
        if text is None:
            return jsonify({'success': False,
                            'message': 'Pic parhne wala system (OCR) abhi server par available nahi hai — video ka naam likh kar command dein.'})
        cand = _ocr_pick_title(text)
        if len(cand.split()) < 2:
            return jsonify({'success': False,
                            'message': 'Pic se video ka naam saaf nahi parha ja saka — naam wali jagah saaf dikh rahi ho to dobara try karein, warna naam likh dein.'})
        parsed = {'raw': cand, 'intent': 'download', 'title': cand.title(),
                  'episodes': [], 'quality': str(data.get('quality') or '360p'),
                  'format': 'mp3' if data.get('format') == 'mp3' else 'mp4',
                  'schedule_at': None, 'schedule_in_seconds': None, 'category': None}
        vid, vtitle = _ai_pick_best(parsed)
        if not vid:
            return jsonify({'success': False,
                            'message': f"🖼 Pic se ye parha: '{cand}' — lekin is naam ki video nahi mili. Naam likh kar try karein."})
        parsed['title'] = vtitle
        jid = f"job_{int(time.time())}_{random.randint(1000, 9999)}"
        job = {'job_id': jid, 'command': 'pic: ' + cand, 'parsed': parsed,
               'status': 'queued', 'run_at_epoch': time.time(),
               'created_at': datetime.now().isoformat(),
               'direct_items': [{'video_id': vid, 'title': vtitle}],
               'guest_device': _img_guest_device,
               'episodes_status': [{'episode': None, 'status': 'pending', 'title': vtitle}],
               'completed_count': 0, 'total_count': 1}
        with ai_jobs_lock:
            ai_jobs[jid] = job
            _save_ai_jobs()
        th = threading.Thread(target=_ai_run_job, args=(jid,))
        th.daemon = True
        th.start()
        return jsonify({'success': True, 'job_id': jid, 'title': vtitle,
                        'read_text': cand,
                        'message': (f"🖼 Pic parh li! '{cand}' — video mil gayi: '{vtitle}'. "
                                    f"Download start kar di hai. Job ID: {jid}")})
    except Exception:
        return jsonify({'success': False,
                        'message': '😔 Pic parhne mein masla aa gaya — dobara try karein, ya video ka naam likh kar command dein.'})


@app.route('/api/ai/jobs/<job_id>/stop-item', methods=['POST'])
def api_ai_stop_item(job_id):
    """Update 79: AI list me ek video par tap = sirf wohi ruk jaye."""
    data = request.json or {}
    try:
        idx = int(data.get('index'))
    except (TypeError, ValueError):
        return jsonify({'error': 'index missing'}), 400
    dl = None
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job nahi mila'}), 404
        eps = job.get('episodes_status') or []
        if idx < 0 or idx >= len(eps):
            return jsonify({'error': 'index ghalat'}), 400
        eps[idx]['user_stopped'] = True
        if eps[idx].get('status') in ('downloading', 'searching',
                                      'starting', 'pending'):
            eps[idx]['status'] = 'stopped'
        dl = eps[idx].get('download_id')
        _save_ai_jobs()
    if dl:
        download_control[dl] = {'cancel': True}
    return jsonify({'success': True})


@app.route('/api/ai/jobs/<job_id>/stop-all', methods=['POST'])
def api_ai_stop_all(job_id):
    """Update 79: 'Sab band' — poori list ki downloads ek sath ruk jayen."""
    dls = []
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job nahi mila'}), 404
        job['stop_all'] = True
        for es in job.get('episodes_status') or []:
            if es.get('status') in ('downloading', 'searching', 'starting'):
                es['user_stopped'] = True
                es['status'] = 'stopped'
                if es.get('download_id'):
                    dls.append(es['download_id'])
            elif es.get('status') == 'pending':
                es['status'] = 'stopped'
        _save_ai_jobs()
    for dl in dls:
        download_control[dl] = {'cancel': True}
    return jsonify({'success': True})



@app.route('/api/ai/jobs/<job_id>/retry-item', methods=['POST'])
def api_ai_retry_item(job_id):
    """v9: AI list mein fail/ruki hui ek video ko dobara start karna."""
    data = request.json or {}
    try:
        idx = int(data.get('index'))
    except (TypeError, ValueError):
        return jsonify({'error': 'index missing'}), 400
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job nahi mila'}), 404
        eps = job.get('episodes_status') or []
        if idx < 0 or idx >= len(eps):
            return jsonify({'error': 'index ghalat'}), 400
        if job.get('status') == 'running':
            return jsonify({'error': 'Job abhi chal raha hai — pehle rukne dein'}), 400
        if eps[idx].get('status') not in ('failed', 'stopped'):
            return jsonify({'error': 'Ye video ho chuki hai ya chal rahi hai'}), 400
        eps[idx]['status'] = 'pending'
        eps[idx].pop('error', None)
        eps[idx].pop('user_stopped', None)
        job['stop_all'] = False
        job['status'] = 'running'
        _save_ai_jobs()
    th = threading.Thread(target=_ai_run_job, args=(job_id, idx))
    th.daemon = True
    th.start()
    return jsonify({'success': True})


@app.route('/api/ai/jobs/<job_id>/delete-item', methods=['POST'])
def api_ai_delete_item(job_id):
    data = request.json or {}
    try:
        idx = int(data.get('index'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Bad index'}), 400
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job nahi mila'}), 404
        eps = job.get('episodes_status') or []
        if idx < 0 or idx >= len(eps):
            return jsonify({'success': False, 'error': 'Bad index'}), 400
        _it = eps[idx]
        if _it.get('status') == 'deleted':
            return jsonify({'success': True})
        _dl = _it.get('download_id')
        _was_done = _it.get('status') == 'completed'
        _it['status'] = 'deleted'
        _it['user_stopped'] = True
        _it.pop('error', None)
        if _was_done:
            job['completed_count'] = max(
                0, (job.get('completed_count') or 0) - 1)
        job['total_count'] = max(
            0, (job.get('total_count') or len(eps)) - 1)
        _save_ai_jobs()
    if _dl:
        try:
            delete_download(_dl)
        except Exception:
            pass
    return jsonify({'success': True})


@app.route('/api/ai/jobs/<job_id>/delete-all', methods=['POST'])
def api_ai_delete_all(job_id):
    """Update 106: 'All delete' — poori list ek sath delete: chal
    rahi downloads cancel, bani hui files delete, saari rows khatam.
    'Sab band' ke sath ye button har AI list par ata hai."""
    dls = []
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job nahi mila'}), 404
        job['stop_all'] = True
        job['status'] = 'cancelled'
        for es in job.get('episodes_status') or []:
            if es.get('status') != 'deleted':
                if es.get('download_id'):
                    dls.append(es['download_id'])
                es['status'] = 'deleted'
                es['user_stopped'] = True
                es.pop('error', None)
        job['completed_count'] = 0
        job['total_count'] = 0
        _save_ai_jobs()
    for dl in dls:
        download_control[dl] = {'cancel': True}
        try:
            delete_download(dl)
        except Exception:
            pass
    return jsonify({'success': True})


@app.route('/api/ai/jobs')
def api_ai_jobs():
    with ai_jobs_lock:
        jobs = sorted(ai_jobs.values(), key=lambda j: j.get('created_at', ''),
                      reverse=True)
    return jsonify({'jobs': [_enrich_ai_job(j) for j in jobs[:50]]})


@app.route('/api/ai/jobs/<job_id>')
def api_ai_job(job_id):
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify({'job': _enrich_ai_job(job)})


# ============================================================
# ============================================================
# ============ V4 ADMIN PANEL (Profile ke andar) =============
# ============================================================
OWNER_EMAIL = 'chuzajani1@gmail.com'


def _is_owner_session():
    """Update 117: logged-in OWNER (email match) khud hi admin hai —
    alag Admin key ki zaroorat nahi. Key wala rasta backup ke tor
    par waisa hi chalta rahe ga."""
    try:
        uid = session.get('user_id')
        if not uid:
            return False
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT email FROM users WHERE id = ?', (uid,))
        row = cur.fetchone()
        conn.close()
        return bool(row) and (row['email'] or '').strip().lower() == OWNER_EMAIL
    except Exception:
        return False


def _admin_ok():
    return bool(session.get('pt_admin')) or _is_owner_session()


def _v4_admin_guard():
    if not _admin_ok():
        return jsonify({'error': 'Admin login required'}), 403
    return None


@app.route('/api/site-config')
def api_site_config():
    return jsonify({
        'toggles': get_feature_toggles(),
        'announcement': get_announcement(),
        'prices': {k: v['price'] for k, v in PREMIUM_PLANS_PKR.items()},
        'apk_available': os.path.exists(_apk_file_path()),
        'deals': get_deals(),
        'guest_limit': get_guest_limit(),
        'version': APP_VERSION,
        'guest_used': (None if session.get('user_id')
                       else _guest_count(_guest_device_id())),
    })


@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.json or {}
    if str(data.get('key', '')) == ADMIN_SECRET_KEY:
        session['pt_admin'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Galat admin key'}), 403


@app.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    session.pop('pt_admin', None)
    return jsonify({'success': True})


@app.route('/api/admin/session')
def api_admin_session():
    return jsonify({'admin': _admin_ok(), 'owner': _is_owner_session()})


@app.route('/api/admin/v4-settings', methods=['GET', 'POST'])
def api_admin_v4_settings():
    guard = _v4_admin_guard()
    if guard:
        return guard
    settings = load_site_settings()
    if request.method == 'POST':
        data = request.json or {}
        if isinstance(data.get('toggles'), dict):
            t = dict(FEATURE_DEFAULTS)
            t.update(settings.get('feature_toggles') or {})
            for k, v in data['toggles'].items():
                if k in FEATURE_DEFAULTS:
                    t[k] = bool(v)
            settings['feature_toggles'] = t
        if 'announcement' in data:
            settings['announcement'] = str(data.get('announcement') or '')[:300]
        if 'maintenance_message' in data:
            settings['maintenance_message'] = str(
                data.get('maintenance_message') or '')[:200]
        if data.get('reset_private_pin'):
            settings.pop('private_pin_hash', None)
            session.pop('pt_private', None)
        if 'guest_download_limit' in data:
            try:
                settings['guest_download_limit'] = min(
                    1000, max(0, int(data['guest_download_limit'])))
            except (TypeError, ValueError):
                pass
        if isinstance(data.get('prices'), dict):
            prices = dict(settings.get('premium_prices') or {})
            for k in ('weekly', 'monthly', 'yearly'):
                if k in data['prices']:
                    try:
                        prices[k] = int(data['prices'][k])
                        PREMIUM_PLANS_PKR[k]['price'] = prices[k]
                    except (TypeError, ValueError):
                        pass
            settings['premium_prices'] = prices
        if isinstance(data.get('payment_accounts'), dict):
            accounts = settings.get('payment_accounts', {})
            for method, acc in data['payment_accounts'].items():
                method = str(method).lower()
                if method not in PAYMENT_METHOD_META:
                    continue
                if acc and str(acc.get('account_number', '')).strip():
                    accounts[method] = {
                        'account_number': str(acc['account_number']).strip(),
                        'account_title': str(acc.get('account_title', 'Playza Premium')).strip()
                        or 'Playza Premium'}
                else:
                    accounts.pop(method, None)
            settings['payment_accounts'] = accounts
        if isinstance(data.get('deals'), list):
            def _deal_int(v):
                try:
                    return max(0, int(v))
                except (TypeError, ValueError):
                    return 0
            clean_deals = []
            for it in data['deals'][:24]:
                if not isinstance(it, dict):
                    continue
                dname = str(it.get('name', '')).strip()[:60]
                if not dname:
                    continue
                dlink = str(it.get('link', '')).strip()[:500]
                if dlink and not (dlink.startswith('http://')
                                  or dlink.startswith('https://')):
                    dlink = ''
                clean_deals.append({
                    'name': dname,
                    'emoji': (str(it.get('emoji', '🛒')).strip()[:8] or '🛒'),
                    'old_price': _deal_int(it.get('old_price')),
                    'new_price': _deal_int(it.get('new_price')),
                    'badge': str(it.get('badge', '')).strip()[:10],
                    'link': dlink})
            settings['deals'] = clean_deals
        save_site_settings(settings)
        _rebuild_payment_accounts()
        settings = load_site_settings()
    return jsonify({
        'toggles': get_feature_toggles(),
        'announcement': settings.get('announcement', ''),
        'prices': {k: v['price'] for k, v in PREMIUM_PLANS_PKR.items()},
        'payment_accounts': settings.get('payment_accounts', {}),
        'deals': get_deals(),
        'guest_download_limit': get_guest_limit(),
        'maintenance_message': settings.get('maintenance_message', ''),
        'pin_set': bool(settings.get('private_pin_hash')),
    })


@app.route('/api/admin/v4-stats')
def api_admin_v4_stats():
    guard = _v4_admin_guard()
    if guard:
        return guard
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) AS c FROM users')
    total_users = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) AS c FROM pakistan_payments WHERE status = 'pending'")
    pending = cursor.fetchone()['c']
    conn.close()
    today = datetime.now().date().isoformat()
    downloads_today = sum(1 for v in downloaded_files.values()
                          if v.get('status', 'completed') == 'completed'
                          and str(v.get('timestamp', '')).startswith(today))
    visits = _visit_totals()
    return jsonify({'total_users': total_users, 'downloads_today': downloads_today,
                    'pending_premium_requests': pending,
                    'total_visits': visits['total'],
                    'today_visits': visits['today_opens'],
                    'today_unique': visits['today_uniq']})


@app.route('/api/admin/cookies', methods=['POST'])
def api_admin_cookies_upload():
    _g = _v4_admin_guard()
    if _g:
        return _g
    f = request.files.get('file')
    if not f:
        return jsonify({'success': False, 'error': 'File nahi mili'}), 400
    _data = f.read()
    if len(_data) < 50 or b'youtube.com' not in _data:
        return jsonify({'success': False,
                        'error': 'Ye YouTube cookies wali file nahi lagti'}), 400
    with open(os.path.join(DATA_DIR, 'yt_cookies.txt'), 'wb') as _f:
        _f.write(_data)
    return jsonify({'success': True,
                    'message': 'Cookies lag gayi hain — ab downloads dobara try karein'})


@app.route('/api/admin/cookies-status')
def api_admin_cookies_status():
    _g = _v4_admin_guard()
    if _g:
        return _g
    _p = _yt_cookies_path()
    _kb = 0
    if _p:
        try:
            _kb = int(os.path.getsize(_p) / 1024)
        except Exception:
            _kb = 0
    return jsonify({'active': bool(_p), 'size_kb': _kb})


@app.route('/api/system-clean', methods=['POST'])
def api_system_clean():
    """Update 122: Tools > System clean ka server hissa — sirf Playza
    ka apna kachra: OCR temp files + storage cleanup (purani mukammal
    downloads/orphans, maujooda usool ke mutabiq). User ki chalti hui
    ya private downloads ko haath nahi lagta."""
    freed = 0
    removed = 0
    try:
        _tmp = os.path.join(DATA_DIR, 'ocr_tmp')
        if os.path.isdir(_tmp):
            for _fn in os.listdir(_tmp):
                _p = os.path.join(_tmp, _fn)
                try:
                    if os.path.isfile(_p):
                        freed += os.path.getsize(_p)
                        os.remove(_p)
                        removed += 1
                except Exception:
                    pass
    except Exception:
        pass
    try:
        _f2, _r2 = _storage_cleanup(force=True)
        freed += int(_f2 * 1048576)
        removed += _r2
    except Exception:
        pass
    info = _storage_info()
    return jsonify({'success': True,
                    'freed_mb': round(freed / 1048576, 1),
                    'removed': removed, 'used_pct': info['used_pct'],
                    'free_mb': info['free_mb']})


@app.route('/api/admin/storage')
def api_admin_storage():
    guard = _v4_admin_guard()
    if guard:
        return guard
    info = _storage_info()
    info['success'] = True
    return jsonify(info)


@app.route('/api/admin/storage-cleanup', methods=['POST'])
def api_admin_storage_cleanup():
    guard = _v4_admin_guard()
    if guard:
        return guard
    freed, removed = _storage_deep_clean()
    info = _storage_info()
    info.update({'success': True, 'freed_mb': freed, 'removed': removed})
    return jsonify(info)


@app.route('/api/admin/v4-users')
def api_admin_v4_users():
    guard = _v4_admin_guard()
    if guard:
        return guard
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, created_at FROM users ORDER BY id DESC LIMIT 200')
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for u in users:
        u['is_premium'] = is_premium_user(u['id'])
        u['is_owner'] = (u['email'] == 'chuzajani1@gmail.com')
    return jsonify({'users': users})


@app.route('/api/admin/v4-users/<int:user_id>/premium', methods=['POST'])
def api_admin_v4_user_premium(user_id):
    guard = _v4_admin_guard()
    if guard:
        return guard
    data = request.json or {}
    grant = bool(data.get('grant'))
    conn = get_db_connection()
    cursor = conn.cursor()
    if grant:
        start = datetime.now()
        expiry = start + timedelta(days=30)
        cursor.execute('''
            INSERT INTO premium_users (user_id, plan_type, start_date, expiry_date, payment_method, transaction_id, amount_paid)
            VALUES (?, 'monthly', ?, ?, 'admin', 'admin-grant', 0)
            ON CONFLICT(user_id) DO UPDATE SET plan_type='monthly', start_date=?, expiry_date=?, is_active=1
        ''', (user_id, start, expiry, start, expiry))
    else:
        cursor.execute('UPDATE premium_users SET is_active = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'is_premium': is_premium_user(user_id)})


# ==================== PWA (Update 6) ========================
# ============================================================
_APP_ICON_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>
<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
<stop offset='0' stop-color='#4f46e5'/><stop offset='1' stop-color='#0d9488'/>
</linearGradient></defs>
<rect width='512' height='512' rx='110' fill='url(#g)'/>
<path d='M205 165 L380 256 L205 347 Z' fill='#ffffff'/>
</svg>"""


import base64 as _pwa_b64
_ICON192_PNG = _pwa_b64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAGnklEQVR42u3dV3NUdRjH8d/Z2RvL2JKNI4xeeOGNL4FAhBAC6YU0CI5trAghIYEEoyimkkAMyEvQsSt2ETXtJSCCGqQkSIhYxnJHvNhEJHX77jnP9zOzd5SZf57feZ5nz9mNoyQoXjc2JWCWD75Y7iT6/0zIf1icQ8EjgkAci38gHIoelsMQ03+0hKJHArwfwzD4KH64TSxrLeoklVL4SKL3ouwGPoofbhZtDUaUnjIKHyno3Qi6gY/ih1dEUpthJaZ8LcWP1PfOl6F3Ah/FD68Jp1ZDSspGih8u9HYIncBZuvjHKX64OATLnIgDUEHxwwPeWiQEPo4Hli2YjEqu/vCQNxfoAj6KHxYsVNP+ef805Q+rI1BVNld/eNcbx68fhXwUPyyZXeP+kDZiwKN4GxTsAJJUw/gDQ16f3gXoADDNf60VsAHA6Ai0ac1Fxh+Y89pXdzn+6xYBwBh2ALAD0AFgdgeoZf6H5Q7A1R/sAAAdALC4BLMBgBEIYAQCDI5A3AUAHQBgBwDoAAAdADDTAbgPADoAwA4A0AEAOgBABwDoAIC3A8CzQLAdAO4DgBEIYAkG6AAAHQCgAwB0AIAOAHi3A0xJvOZ/Hfkmg3Pw+IsOsIQjAxmSpGeyJjgMdgC7Xp0OAjy3A9ADwg3B1qzLHAYdwK7DAwEdHghwEF4IgKPg86C85r5CCQLn5O4XHSBKhwYCOkQ3cPMOgFgFQZK2sR+4bAfgveCFXxHoHwhwbi56MQLFQf9gQP2DjEWMQARBkrR9FWNR6o5AiLtX6AZ0AEIQDEEd3YAOYFnfYEB9dITUCQA3QyK/ERZtEDjj5L/4XqAkOjjdCXasmuQwkrYD8L1AKRCEdElS/UqCwA5g2IGhdA6Bd4EIgSQ10A3oAJb1DqWrl47Au0BefRconCDws+BxaNN6htLVQzdgByAIwRA0sh+wA1i2n24Quw7A7wdwdwgaM+kGjECWgzAcDEITQWAEsqx7mLEowg5AD/BaCHZl/sJh0AHs6hpOU9dwGgcRSgC4GZLaN8KiDQI/R26EmdY5nKZOusFiOwCsBEGSmtkPZu0AfDdMTL8XKNV1DKfxc+X3A9jWMRLsBi0r6AbsAIa1j6SpfcT2fsC7QB5+FyicIPAuEExrG0lTm8FuwA6AOUGQpOeM7Ad0AMzrZSPdgGeBsGQIWldc8W4ArvKBACxgj4ExyD/FN2NhHi2ZkybeCvNPMQHhf5pnPm9spC7oAJAk7Z752nZjF0T/VQJgWlPWhMnCZwSCGh+YMP/l4IxABu1cfcn0VZ8OYFTDGgqfDmBUffbPFD5LsD11ay9y1V+0A3AGnrR9pvDBCGTJtpxxrvgswTY9u26cwqcD2LM1d4yrPkuwPU+vv0DhMwLZ9NSGCxQ+I5A9T+ad56pPAOx5Iv8chc8IZM/jBRQ+S7BRjxWepfDpAPY8WnSWq37CAsCH4lPGI0U/cQgswTY9XHyGKz4jkD0PlZxh3GEJtufB0lEKnw5g05ayUQqfHcCe2vIfueoTAHs2b/yBwk/dHYBDiJeaCgqfDmBUdeX3FD4BsKeq6jRXfXcFgEOIhcpqCt+dAeBRiKhVVJ/iEFiC7SmvOcVVnx3AnrJN31H4BMCe0s0nKXyWYJtKak9S+HQAe4q3fMtV38Ocgi0nSADoAAABAFiCAUsB4E4wLAeAj0SCEQhgCQboAAAdAGAJBhiBAEYggA4AsAMAnusAPAoBRiCAJRggAICxJZhDAB0AYAkG6AAAAQBYggE6AODtAHAGoAMANjmSdH/TECmAOSe6Vzp+SWIRhtkRSJIYg0AAAKs7gCTd1zJACmDG6fYs578OQBeA6RGIRRjmRyBJurf1a9oAPG9032pnTgeQJD4gD7MjUHAP4EBgeASSpHteOE4bgGedezHbWTQAknT3XkIA7zm/N9tZdAS6NgpR/zA6As1Y/tIxUgDPGHs+xwkrAJK0bB8hgPuNt+YsWOf+xf4iX5wLsyPQjDvbPicFcK1Le3KdqAIgSRnthADuM9GSu2R9h3zrK9DxGSGAa1xuXh9SbYd17zedEMAFJkMs/rADIEl3dH5KCJCyruzeEFZNR/T0z+1dnxACpJxfd+WFXc9RPf52WzdBQPL91pQXcR1H/fznrfs/JgRImt8b86Oq4Zg9AH1LD0FA4vyxMz8mtRvTTwDc3PsRIUDc/dlQELO6jdtHYG468CFhQMz8VV8Yl1pNyGfAbjxIGBC+v3cUxr0+k/IhyBv6jhIIzPFPXVHC6/Ffm7zDZJ123WIAAAAASUVORK5CYII=')
_ICON512_PNG = _pwa_b64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAARdklEQVR42u3dZ5OV5R0G8PucOS9STQyLiZoySSZ5kZl8AmmCIBZEURAR0rsVBFFKbIAiKEZNPkImMaZ3SxJc+ASZGKOxCzY0vbzbvOAsoe6e3T3PeZ77/v9+r4hOxt17hr2ucz1lW4m+Wbxg34hTAKjOjx86veUU+sNBTjTk5wt5gEaWg4eVAwVA2AOgFCgAAh8AhUABEPoAhC8DIb95oQ9A9DIQ6hu+UPADMIYfBSoCxX+jQh8AZSBQARD8ACgCgQqA4AdAEQhUAAQ/AIpAoAIg+AFQBAIVgIsEPwAN8MNMi0Bb+ANAvExqOWQAiLcGZPGFCn4AFIH+avwlAOEPQG5yyK62AwSAeBnWyIliieAHoCA/aOAlgcYtAMIfgNI0MdvaDggA4mVcy6EAwGA14ZJA7V/AkrOEPwABS8Aj9ZaAWv/jFwt/AAL7fo0loLZ7AIQ/ANHVmYXtaN8wACgBNRQA4Q8A9Wdju/RvEACUgBoLgPAHgOZk5UDuPrxE+ANAzx4cwNMBlS8Awh8Amped7dy/AQBQAiauVd0Xvl/4A8AUPfjIaZVkdSULgPAHgGZnatvRAkA8fZ8Vlvr0DwB9970+Xwro6wIg/AGgGv3O2HZTvzAAoLqsdQ8AAATUlwLg0z8A5LUCTPmGgmXCHwAG7oEp3hQ4pQVA+ANAPaaawe4BAICAJj0fLJvn0z8A1O2BRyd3KcACAAABTaoA+PQPAM0w2Uye8GxwqfAHgMb57gQvBbgEAAABTagA+PQPAM000Yy2AACABcCnfwCIsAJYAAAgoJ7uGFzu0z8AZOM7PTwRYAEAgIDGLQA+/QNAXnrJbgsAAFgAfPoHgAgrQGesf9lyfgAQbwEAAIIVgMvM/wCQtbGy3AIAABYAn/4BIMIKYAEAgICO+xSAu/8BoGzHZP2KeS+b/wGgMN9+9NTW2AuA+AeA4rkHAACiF4AVc83/AFCiozPeAgAAAR1xD4C7/wEgBgsAAEQuAJe7/g8ARTs86y0AABB5AQAA4jh0E6AbAAHAAgAAlF4AVroBEABCGM18CwAARF0AAAAFAAAoXCclTwAAgAUAAFAAAIDytFZ5BBAALAAAgAIAABSo03IBAAAsAACAAgAAKAAAgAIAACgAAEAeOn4PAABYAAAABQAAUAAAgCJ0UnIXAACEKwDiHwDicQkAABQAAEABAAAUAABAAQAAMuUpAACwAAAACgAAoAAAAGXopBGHAAAWAACg/AXAUwAAYAEAABQAAEABAAAUAAAgT24CBAALAACgAAAACgAAoAAAAAoAAJALTwEAgAUAAFAAAAAFAABQAAAABQAAyIWnAADAAgAAhFgAUrIBAEC8AjDiEAAgGpcAACDiAuACAABYAAAABQAAUAAAAAUAAFAAAIBMeAoAACwAAIACAAAoAACAAgAAKAAAQC48BQAAFgAAQAEAABQAAEABAAAy5SZAALAAAAAhFoA04hAAwAIAACgAAIACANn71u5THAIQnqcACF0Crpj9msMALAAQzTetAYACAHFLgCIAKACgCAAoABCxCAAoAGANAChOp5U8BwDjrQFXzn7dYQAWAIjm/t3T0/27pzsIQAGAqEUAQAEAawCAAgCKAEAevAoY+lAErnKTIGABgHju2z093WcNABQAUAQAFAAIWAQAFACwBgAoAKAIANSr0xpxCDCoInD1LE8LABYACOfex6anex+zBgAKACgCAAoAxCsCAAoAWAMAFABQBACq4XcBQAOLQEopXeOJAcACAPF8wxoAKAAQtwQoAoACAIoAgAIAEYsAgAIA1gCASfEUAGS+BlzraQHAAgDx3GMNABQAiFsCFAFAAQBFAEABgIhFAGAsbgKEwkvAajcJAhYAiGfXY9PTLosAoACAIgCgAEDAIgDQScldABC1BKyedcBhQNgCMOIQIG4RGDpYBGYqAhCuAPj8D+waHkprlAAIxT0AQEoppbuHh9Ldw0MOAhQAQBEAFAAgXBEAFADAGgAoAIAiAOTMUwDAhIrAdZ4WAAsAEM9dw0PpLmsAKACAIgAoAEDAIgAoAIA1AMiAmwCBvq8Ba90oCBYAIJ6dw0Npp0UAFAAgbhEAFADAGgAoAIAiACgAQJgiANTPUwBAbSVgnacFwAIAxLNjeCjtsAiAAgDELQLAYHXSiEMAmlMC1s1wWQAsAEC8IrBnKO3YYxEABQAIWwSA6ngKAGh8CbjeZQGwAADx3LlnKN1pEQAFAIhbBAAFALAGAAoAoAgAvXITIJB9EUgppfVuFAQLABDPdmsATGwBSMkGAJRVAtbPeMNhgAUAiFcEpqXte6Y5CFAAgKhFAFAAAGsA0OUpACDUGnCD+wPAAgDEc4c1ABQAIG4JUARQAAAUAVAAACIWAVAAAKwBUDxPAQAcZw240dMClF4A0ohDADja7aNF4AxFgDK5BAAwVhHY67IACgBA2BKgCKAAACgCkD03AQJMoghscG8AFgCAeLbtnZa2WQNQAAAUAVAAAAIWAVAAAKwBoAAAKALQLJ4CAKiwCGz0tAAWAIB4tu6dlrZaA1AAABQBUAAAAhYBUAAArAGgAAAoAjAYngIAaEARSCmlTZ4YwAIAEM8WawAKAEDcEqAIoAAAKAKgAABELAJQhU4ruQ0QIIcSsPmMNx0G/SsAI2nEKQA0mKcDqIJLAADCn5ALgCsAAI2zcUY3+P2MpqoC4AgAGhj8UPkC4B4AgNptmHHAITDgBcC8BFBv+M88YOqnjgUAgDrcONOnfupcAAAQ/ARcAFo2AIBBuWHW6+Z+LAAAoYIfFAAAwQ+1FgAvAgKoxvrZ5n4sAACxgh8avwB4ERBAX1w/+zWHQEYLgHkKYGrBP6cb/H6ektcCAMBkrZvjUz+5LgAACH4CLgBeBATQs7VnvnrwD+Z+Mtd2BAATDH8oYgFwBgBjuk7wU2IBMGMBnCD455r7KbkAeA8AwFHB/4pDoPwCIP4B/m+N8CfMAmDaAkhr5nWD389ELAAA5Vs9zyd+YvIYICD8IeQC4EVAQDDXnvXywT+Y+4lcABwBEC74AfcAADFcI/zhqAXABAaUHPzzzf1wggXABgCU5+r5+x0CjLkAAAh+CFgAzGJAKeG/YL+pH3otAC4AALm7aoFP/TDxBcA9AEC2wb/PIcCkFwBzGZChK8/eZ+6HqS0AAJkFP9CHBcAZABm4QvBDnxcAExrQ5OBf2A1+P6ug3wuADQBopq8tfMkhQGULAIDgh4ALgFkNaIivntMNfj+XoHJtRwA0KvyBwSwAXgQE1Bv8LzoEqKMAuAQA1OEr53aD388gqIVLAEB94Q/UuAA4A2BAviz4oTkFILVUAKDi4D/vhYN/MPeDBQAo35dGgx9oHPcAAMIfQi4AJjmgj754vrkfsigAjgDoa/ADuSwA7gIApuYLi573iR8sAECo4AcUAEDwA5kUADcBAr36/AXd4PdzA0pYANwDAPQS/s85BChqAXAGwBg+J/ih0AXAlAccL/gXd4PfzwiwAAAxfHaxT/1Q/gLgHgDgUPA/6xAgzAJg3oPwPnNhN/j9PIAw/DIgEP4OASIuAI4ABD8QsAC4BACxfPoicz/gJkAIFPzPOATgsAXAGUDxPiX8gWMWADMglBv8S7rB7+85YAGA8q1a4hM/MN4C4B4AKCz8n3YIQA8LgGkQirDy4m7w+zsN9LYAAEUEP8CEFgBnAFm6XPADU1oAWioAZBf+l/zZ1A9MsQAAeQU/QD8KgM//0HwrBD/Q9wXAjAjNDv+l5n7AAgBhXLbUp36gygXAi4CgYcH/lEMABrAAmBahMZYve8rcDwxqAQAaEfwAA10AnAHU5lLBD9S2AHgREAw++C998uAfzP2ABQBiWDYa/gC1LgCA4AcCFgATJFQb/MvN/UADC8CI9wBAZZYu/5NDABq6AACCHwi4AJgloW8uuawb/P5eARYACBT8ANksAM4ApuRi4Q9kuQB4ERBMLvhXPHHwD+Z+wAIA5VsyGvwAGWs7AhD+QMQFwHwJ47rocnM/UFgBSF4EBGME/x8dAlAklwBA+AMRFwCXAOBIF67sBr+/G0DJBcARwFHBDxBiAXAPAMEtXvm4QwACLgBmTiKH/6rHTf1A1AUA4rlglU/9QGytRav+oAMAgAUAACi+AHgREABEXADcAAUA4XgTIAAoAABABJ2RlnsAAMACAAAEWACcAQDEKwBegwoAIRcAGwAAROMeAAAIuQC4BAAAFgAAIMIC4AwAIF4BSF4EBADhuAQAABEXAJ//ASBgAfAiIAAIuQDYAAAgGvcAAEDIBcAlAACwAAAAERYA9wAAQLwC4CkAAIjHJQAAiLgAuAAAAAELgEsAABByAbABAEA07gEAgJALgEsAAGABAAAiLADuAQCAeAXAUwAAEHIBAACicQ8AAERcAFLLBgAA4QqA+AeAeFwCAICQC4CnAADAAgAARFgAvAgIAOIVAC8CAoCQCwAAEI17AAAg5ALgRUAAYAEAABQAAKBAXgQEABELQPIeAAAIuAA4AwAIuAC4BAAAFgAAwAIAAJS5ANgAACAa7wEAgJALgEsAAGABAAACLABeBAQAAQuASwAAEI9LAAAQcgFwBgAQrwCklgoAABYAAKB47gEAgJALgKcAAMACAABEWAC8CAgA4hUAvw4YAOJxCQAAAmqllNIn1+51HQAAgvj9zjNanYM1QP4DQCSdlPw+QACIxj0AABB2AfAkAADEKwAuAgBAxAXAOQBAKIfG/0+sH9YDAKBwj2+f2Tq0AFgBACAWTwEAQECHFgAvAwKAgAVA/ANAHIcuATxxxyxvAwCAgh2e9Z3D/4UXAgFADJ0j/6cLAQAQrgCIfwCI4ZjR/+MbdusBAFCYJ7fNbp1wAbACAEAMnWP/kQoAAKU77n3/H9v4Oy0AAArx1NY5rR4WABsAAJTO7wIAgIBO+Oqfj25yGQAAcvf0ljnHzfrOif8v8h8Awi0AKaX0kU2/1QIAIFPPbDnzhDnfmXw9AAByNWYB8PEfAMo07mf8D2/+jR4AAJl59ra5rUkvACn5FcEAUKJx3wPw3K1zVQAAyEgv2e1FQAAQUM+f7j9006PuBQCAhnv+lnk9ZbsFAAAsAGP74M1WAABoqhduntdzrlsAAMACML4PWAEAoHFenMCn/5R6eA/AsZVB/gNAuAUgpZTef8sjWgAANMRLN5014TxvD+o/BAA0I/xTmswlgC6vCAaAfE0pxk+/9WGXAgCgJvu+Pn/SOe4xQACwAEzcabdZAQBg0PZvnj+lDG/X/QUAAIPP3r6F96m3PWQJAICKvbx5QV+yu9O3r8gOAADZ6Gtsv2+LFQAAqvLKpgV9y+12U78wAKC6jK0ksN+71RIAAP3y6sb+f8DuVPOlyn8AaLLKJvtTtv5aCwCAKXpt49mVZHWl1+xP2aYEAMCkw3/D2ZXldDvXLxwAhH9DF4BR07f9yhIAAD16fcPCyvN5YJ/Qp9+uBADAuOF/48KBZPNAJ/ohJQAATujAgMI/pQH/OuBBfmMAIPwbsgCMmnbHLy0BAND1xg3nDDyP21G+UQAQ/jUvAKPeYwkAILA3a/xAXPsn8fdsVwIACBj+6+tdwxsxxZ+sBAAQyF/W138pvFHX4k/e/gtFAICCg//cxuRu427GO/lOJQCAAsP/+nMblbmNvBv/3UoAAAX5a8PCv7EFQBEAQPAHLgAppfSuHT9XAgDIzt/WndfojG07QACIl11ZhetJ1gAAGuzvGX1ozfLT9Uk7FQEAGhT8a/Nbq7Od19+582dKAAC1+8fa87PM0uyvrysCAAj+gAVg1DvuUgQAqN4/rzu/iOws7g57RQAAwR+wACgCAAj+wAVg1Nvv/qkiAMCE/WvNoqIzMtRLdpQBACKHftgCMOptigAAh/l3oOAPXQCOKAO7lAGAkKG/elHoDPSe/cO8dddPlAGAgv1n9QVyTwFQCAAEvgJAj95yj1IA0ET/vVbYKwDKAYCQZ0z/A/emA4S4S5ClAAAAAElFTkSuQmCC')


@app.route('/icon-192.png')
def pwa_icon_192():
    return Response(_ICON192_PNG, mimetype='image/png')


@app.route('/icon-512.png')
def pwa_icon_512():
    return Response(_ICON512_PNG, mimetype='image/png')


@app.route('/app-icon.svg')
def app_icon_svg():
    return Response(_APP_ICON_SVG, mimetype='image/svg+xml')


@app.route('/manifest.json')
def pwa_manifest():
    return jsonify({
        'name': 'Playza - All in One Downloader',
        'short_name': 'Playza',
        'description': 'Playza by Chuza - videos, dramas and music downloads with AI assistant',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#12102e',
        'theme_color': '#4f46e5',
        'icons': [
            {'src': '/icon-192.png', 'sizes': '192x192', 'type': 'image/png',
             'purpose': 'any'},
            {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png',
             'purpose': 'any'},
            {'src': '/app-icon.svg', 'sizes': 'any', 'type': 'image/svg+xml',
             'purpose': 'any'}
        ]
    })


@app.route('/sw.js')
def pwa_service_worker():
    js = """
const CACHE = 'playtube-v4';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(clients.claim()); });
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return; // API always live network
  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(()=>{});
      return r;
    }).catch(() => caches.match(e.request))
  );
});
"""
    return Response(js, mimetype='application/javascript')



# ============================================================
# ============ DOWNLOAD APP: APK FILE (v3) ===================
# ============================================================
def _apk_file_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playtube.apk')


@app.route('/playtube.apk')
def playtube_apk_file():
    apk_path = _apk_file_path()
    if os.path.exists(apk_path):
        return send_file(apk_path, as_attachment=True,
                         download_name='Playza.apk',
                         mimetype='application/vnd.android.package-archive')
    return jsonify({'error': 'APK coming soon after launch'}), 404


@app.route('/api/apk-status')
def api_apk_status():
    return jsonify({'available': os.path.exists(_apk_file_path()),
                    'url': '/playtube.apk'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))