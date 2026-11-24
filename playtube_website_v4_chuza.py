# ============================================
# PlayTube v4 (Chuza Edition) - Video Downloader with AI Assistant
# Created by: Chuza
# Copyright © 2026. All Rights Reserved.
# Unauthorized copying or distribution prohibited.
# ============================================
"""
PlayTube - All in One Video Downloader
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

# Database setup
# Database setup for Vercel
import os
DB_FILE = os.path.join("/tmp", "playtube_users.db")
# ============ GMAIL VERIFICATION SYSTEM ============
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL", "chuzajani1@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

verification_codes = {}

# v4: pending codes (signup + password reset) disk par bhi save hote hain,
# taake server restart par bhi code valid rahe.
PENDING_CODES_FILE = os.path.join(os.path.expanduser("~"), "Downloads",
                                  "PlayTube", "pending_codes.json")
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


def send_verification_email(email, code, purpose='Verification'):
    """Best-effort email. Sirf tab True jab mail asal me chali jaye.

    SMTP credentials env se aate hain (GMAIL_EMAIL / GMAIL_APP_PASSWORD).
    Agar app password configured nahi hai to ye False return karta hai —
    koi exception nahi — taake caller gracefully degrade kare (code
    server-side store me rehta hai). Koi password code me nahi hai.
    """
    if not os.environ.get('GMAIL_APP_PASSWORD'):
        print('[PlayTube] SMTP not configured (GMAIL_APP_PASSWORD missing) - code stored, email not sent.')
        return False
    try:
        subject = f"PlayTube - {purpose} Code"
        body = (f"Hello!\n\nYour PlayTube {purpose.lower()} code is: {code}\n\n"
                f"This code will expire in 10 minutes.\n\n- PlayTube Team\n")

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
    SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'playtube_settings.json')
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
                'account_title': acc.get('account_title', 'PlayTube Premium'),
                'icon': meta['icon'],
                'color': meta['color']
            }
    PAKISTAN_PAYMENTS.clear()
    PAKISTAN_PAYMENTS.update(rebuilt)



# ============ FEATURE TOGGLES + ANNOUNCEMENT (v4 Admin Panel) ============
FEATURE_DEFAULTS = {'ai_enabled': True, 'downloads_enabled': True,
                    'premium_enabled': True, 'social_enabled': True,
                    'signup_enabled': True, 'floating_enabled': True,
                    'maintenance_mode': False}


def get_feature_toggles():
    _s = load_site_settings()
    _t = dict(FEATURE_DEFAULTS)
    _t.update(_s.get('feature_toggles') or {})
    return _t


def feature_enabled(name):
    return bool(get_feature_toggles().get(name, FEATURE_DEFAULTS.get(name, True)))


def get_announcement():
    return (load_site_settings().get('announcement') or '').strip()


_MAINTENANCE_EXEMPT = ('/admin', '/api/admin', '/api/user-info', '/api/site-config',
                       '/sw.js', '/manifest.json', '/app-icon.svg', '/playtube.apk',
                       '/api/apk-status')


@app.before_request
def _v4_maintenance_gate():
    try:
        if not feature_enabled('maintenance_mode'):
            return None
        if session.get('pt_admin'):
            return None
        _p = request.path or '/'
        if any(_p.startswith(_x) for _x in _MAINTENANCE_EXEMPT):
            return None
        if _p.startswith('/api/'):
            return jsonify({'error': 'Site maintenance me hai - thodi der baad try karein',
                            'maintenance': True}), 503
        return ('<!DOCTYPE html><html><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>PlayTube - Maintenance</title></head>'
                '<body style="background:#12101f;color:#eceaf6;font-family:sans-serif;'
                'display:flex;align-items:center;justify-content:center;min-height:100vh;'
                'margin:0;text-align:center;padding:20px"><div>'
                '<h1 style="color:#8b6dff">PlayTube</h1>'
                '<p>Site abhi maintenance me hai.<br>Thodi der baad dobara try karein.</p>'
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
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "PlayTube")
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
    <title>PlayTube - All in One Downloader</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#4f46e5">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0f0f0f;
            --bg-card: #1a1a1a;
            --bg-hover: #272727;
            --red-primary: #ff0000;
            --text-main: #ffffff;
            --text-sub: #aaaaaa;
            --border-color: #333;
            --success: #4CAF50;
            --warning: #FF9800;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        body {
            background-color: var(--bg-main);
            color: var(--text-main);
        }

        .app-container { display: flex; }

        .sidebar {
            width: 250px;
            background: #000;
            padding: 20px 10px;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            z-index: 100;
            border-right: 1px solid #222;
        }

        .sidebar-brand {
            font-size: 1.8rem;
            font-weight: 900;
            color: var(--red-primary);
            padding: 10px 15px;
            margin-bottom: 15px;
            cursor: pointer;
        }
        .sidebar-brand span { color: var(--text-main); }

        .sidebar-section {
            color: #666;
            font-size: 0.75rem;
            text-transform: uppercase;
            padding: 15px 15px 5px;
            letter-spacing: 1px;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 12px 15px;
            color: var(--text-sub);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .nav-item:hover { background: var(--bg-hover); color: var(--text-main); }
        .nav-item.active { background: var(--bg-hover); color: var(--text-main); }
        .nav-item i { width: 24px; text-align: center; }
        .nav-divider { height: 1px; background: var(--border-color); margin: 10px 15px; }

        .main-content {
            margin-left: 250px;
            flex: 1;
            padding: 20px 30px;
            min-height: 100vh;
        }

        .top-header {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            gap: 20px;
            position: sticky;
            top: 0;
            background: var(--bg-main);
            padding: 10px 0;
            z-index: 50;
            flex-wrap: wrap;
        }

        .search-box {
            display: flex;
            flex: 1;
            max-width: 500px;
            background: var(--bg-card);
            border-radius: 25px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }

        .search-box input {
            flex: 1;
            padding: 12px 20px;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 1rem;
        }

        .search-box button {
            background: var(--red-primary);
            border: none;
            padding: 0 25px;
            color: #fff;
            cursor: pointer;
        }

        .user-menu {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-left: auto;
        }

        .login-btn, .signup-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
        }

        .login-btn { background: transparent; color: var(--text-main); border: 1px solid var(--border-color); }
        .signup-btn { background: var(--red-primary); color: #fff; }

        .user-avatar-menu {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--red-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-weight: bold;
            position: relative;
        }

        .user-dropdown {
            position: absolute;
            top: 50px;
            right: 0;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            min-width: 200px;
            display: none;
            z-index: 1000;
        }

        .user-dropdown.active { display: block; }
        .user-dropdown-item { padding: 12px 20px; cursor: pointer; }
        .user-dropdown-item:hover { background: var(--bg-hover); }

        .auth-modal, .quality-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }

        .auth-modal.active, .quality-modal.active { display: flex; }

        .auth-content, .quality-content {
            background: var(--bg-card);
            padding: 30px;
            border-radius: 20px;
            max-width: 400px;
            width: 90%;
        }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: var(--text-sub); font-size: 0.9rem; }
        .form-group input {
            width: 100%;
            padding: 12px;
            background: var(--bg-hover);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-main);
            outline: none;
        }

        .platform-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .platform-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }

        .platform-card:hover {
            transform: translateY(-5px);
            border-color: var(--red-primary);
            box-shadow: 0 10px 30px rgba(255,0,0,0.2);
        }

        .platform-card i {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .platform-card span {
            display: block;
            font-size: 0.8rem;
            color: var(--text-sub);
            margin-top: 5px;
        }

        .url-download-box {
            display: flex;
            background: var(--bg-card);
            border-radius: 25px;
            overflow: hidden;
            border: 1px solid var(--success);
            margin: 20px 0;
        }

        .url-download-box input {
            flex: 1;
            padding: 15px 20px;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 1rem;
        }

        .url-download-box button {
            background: var(--success);
            border: none;
            padding: 0 30px;
            color: #fff;
            cursor: pointer;
            font-weight: 600;
        }

        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }

        .video-card {
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.3s;
            border: 1px solid var(--border-color);
        }

        .video-card:hover { transform: translateY(-5px); }

        .thumbnail-box {
            position: relative;
            width: 100%;
            padding-top: 56.25%;
            cursor: pointer;
            background: #000;
        }

        .thumbnail-box img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .select-checkbox {
            position: absolute;
            top: 10px;
            left: 10px;
            width: 25px;
            height: 25px;
            cursor: pointer;
            z-index: 10;
        }

        .card-details { padding: 15px; }
        .card-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 8px; cursor: pointer; }
        .card-title:hover { color: var(--red-primary); }
        .card-channel { font-size: 0.8rem; color: var(--text-sub); margin-bottom: 12px; }

        .action-btns { display: flex; gap: 8px; flex-wrap: wrap; }

        .btn {
            flex: 1;
            padding: 9px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            transition: all 0.2s;
            min-width: 40px;
            text-decoration: none;
        }

        .btn-play { background: #fff; color: #000; }
        .btn-download-mp3 { background: var(--red-primary); color: #fff; }
        .btn-download-mp4 { background: #2d5a2d; color: #fff; }
        .btn-quality { background: #444; color: #fff; }

        .download-progress-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 350px;
            max-height: 400px;
            overflow-y: auto;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            z-index: 999;
            display: none;
        }

        .download-progress-panel.active { display: block; }

        .download-progress-header {
            padding: 15px;
            background: var(--bg-hover);
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .download-item { padding: 15px; border-bottom: 1px solid var(--border-color); }
        .download-item-title { font-size: 0.9rem; margin-bottom: 8px; }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-hover);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 5px;
        }

        .progress-fill {
            height: 100%;
            background: var(--red-primary);
            border-radius: 4px;
            transition: width 0.3s;
        }

        .download-item-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-sub);
        }

        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #333;
            color: #fff;
            padding: 15px 25px;
            border-radius: 10px;
            z-index: 10000;
            display: none;
            border-left: 4px solid var(--red-primary);
        }

        .notification.success { border-left-color: var(--success); }
        .notification.warning { border-left-color: var(--warning); }

        .page-view { display: none; }
        .page-view.active { display: block; }
        .page-title { font-size: 1.5rem; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }

        .player-container { max-width: 1000px; margin: 0 auto; }

        .iframe-wrapper {
            position: relative;
            padding-top: 56.25%;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
        }

        .iframe-wrapper iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
        }

        .player-info {
            margin-top: 20px;
            padding: 20px;
            background: var(--bg-card);
            border-radius: 12px;
        }

        .player-title { font-size: 1.3rem; font-weight: 600; margin-bottom: 10px; }
        .player-channel { color: var(--text-sub); margin-bottom: 15px; }
        .player-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }

        .social-result {
            margin-top: 20px;
            padding: 20px;
            background: var(--bg-card);
            border-radius: 12px;
            display: none;
        }

        .social-result.active { display: block; }

        .social-result-info {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }

        .social-result-thumbnail {
            width: 120px;
            height: 68px;
            object-fit: cover;
            border-radius: 8px;
        }

        .social-result-title {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .social-result-meta {
            color: var(--text-sub);
            font-size: 0.8rem;
        }

        .social-download-options {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .social-format-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }

        .social-format-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }

        .social-format-video {
            background: #2d5a2d;
            color: #fff;
        }

        .social-format-audio {
            background: var(--red-primary);
            color: #fff;
        }

        @media (max-width: 768px) {
            .sidebar { width: 60px; padding: 10px 5px; }
            .sidebar-brand { font-size: 1.2rem; padding: 10px 5px; }
            .sidebar-brand span { display: none; }
            .sidebar-section { display: none; }
            .nav-item span { display: none; }
            .nav-item { justify-content: center; padding: 12px 5px; }
            .main-content { margin-left: 60px; padding: 15px; }
            .video-grid { grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }
            .platform-grid { grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); }
        }
    </style>
</head>
<body>

    <div class="auth-modal" id="authModal">
        <div class="auth-content">
            <h3 id="authTitle" data-i18n="login">Login</h3>
            <div id="loginForm">
                <div class="form-group">
                    <label data-i18n="email_or_username">Email or Username</label>
                    <input type="text" id="loginEmail" data-i18n-ph="enter_email_ph" placeholder="Enter email or username">
                </div>
                <div class="form-group">
                    <label data-i18n="password">Password</label>
                    <input type="password" id="loginPassword" data-i18n-ph="enter_password_ph" placeholder="Enter password">
                </div>
                <button class="btn btn-download-mp3" style="width:100%; padding:12px;" onclick="loginUser()" data-i18n="login">Login</button>
                <p style="text-align:center; margin-top:15px; color:#aaa;">
                    <span data-i18n="no_account">Don't have an account?</span> <a href="#" onclick="showSignupForm()" style="color:var(--red-primary);" data-i18n="signup">Sign Up</a>
                </p>
            </div>
            <div id="signupForm" style="display:none;">
                <div class="form-group">
                    <label data-i18n="username">Username</label>
                    <input type="text" id="signupUsername" data-i18n-ph="choose_username_ph" placeholder="Choose username">
                </div>
                <div class="form-group">
                    <label data-i18n="email">Email</label>
                    <input type="email" id="signupEmail" data-i18n-ph="enter_email2_ph" placeholder="Enter email">
                </div>
                <div class="form-group">
                    <label data-i18n="password">Password</label>
                    <input type="password" id="signupPassword" data-i18n-ph="create_password_ph" placeholder="Create password">
                </div>
                <button class="btn btn-download-mp3" style="width:100%; padding:12px;" onclick="signupUser()" data-i18n="signup">Sign Up</button>
                <p style="text-align:center; margin-top:15px; color:#aaa;">
                    <span data-i18n="have_account">Already have an account?</span> <a href="#" onclick="showLoginForm()" style="color:var(--red-primary);" data-i18n="login">Login</a>
                </p>
            </div>
            <button class="btn btn-play" style="width:100%; margin-top:20px;" onclick="closeAuthModal()" data-i18n="cancel">Cancel</button>
        </div>
    </div>

    <div class="quality-modal" id="qualityModal">
        <div class="quality-content">
            <h3 style="margin-bottom:20px;" data-i18n="select_quality">Select Quality</h3>
            <div id="qualityOptions"></div>
            <button class="btn btn-play" style="width:100%; margin-top:20px;" onclick="closeQualityModal()" data-i18n="cancel">Cancel</button>
        </div>
    </div>

    <div class="notification" id="notification">
        <span id="notificationText"></span>
    </div>

    <div class="download-progress-panel" id="downloadProgressPanel">
        <div class="download-progress-header">
            <strong data-i18n="downloads">Downloads</strong>
            <button class="btn btn-play" style="width:auto; padding:5px 10px;" onclick="toggleProgressPanel()">
                <i class="fa-solid fa-minus"></i>
            </button>
        </div>
        <div id="downloadProgressList"></div>
    </div>

    <div class="app-container">
        <div class="sidebar">
            <div class="sidebar-brand" onclick="switchPage('home')">Play<span>Tube</span></div>

            <div class="sidebar-section" data-i18n="main_section">Main</div>
            <a class="nav-item active" data-page="home" onclick="switchPage('home')"><i class="fa-solid fa-house"></i><span data-i18n="home"> Home</span></a>
            <a class="nav-item" data-page="social" onclick="switchPage('social')"><i class="fa-solid fa-globe"></i><span data-i18n="social_download"> Social Download</span></a>
            <a class="nav-item" data-page="trending" onclick="switchPage('trending')"><i class="fa-solid fa-fire"></i><span data-i18n="trending"> Trending</span></a>
            <a class="nav-item" data-page="music" onclick="switchPage('music')"><i class="fa-solid fa-music"></i><span data-i18n="music"> Music</span></a>
            <a class="nav-item" data-page="gaming" onclick="switchPage('gaming')"><i class="fa-solid fa-gamepad"></i><span data-i18n="gaming"> Gaming</span></a>
            <a class="nav-item" data-page="news" onclick="switchPage('news')"><i class="fa-solid fa-newspaper"></i><span data-i18n="news"> News</span></a>
            <a class="nav-item" onclick="downloadPlaylist()"><i class="fa-solid fa-list"></i><span data-i18n="playlist_download"> Playlist Download</span></a>

            <div class="nav-divider"></div>
            <div class="sidebar-section" data-i18n="library">Library</div>
            <a class="nav-item" data-page="history" onclick="switchPage('history')"><i class="fa-solid fa-clock-rotate-left"></i><span data-i18n="history"> History</span></a>
            <a class="nav-item" data-page="downloads" onclick="switchPage('downloads')"><i class="fa-solid fa-download"></i><span data-i18n="downloads"> Downloads</span></a>
            <a class="nav-item" onclick="openDownloadFolder()"><i class="fa-solid fa-folder-open"></i><span data-i18n="open_folder"> Open Folder</span></a>
            <a class="nav-item" onclick="getStats()"><i class="fa-solid fa-chart-simple"></i><span data-i18n="stats"> Stats</span></a>

            <!-- Premium Button -->
            <div class="nav-divider"></div>
            <a class="nav-item" onclick="openPremiumModal()" style="background:#ff0000; color:#fff; margin:10px;">
                <i class="fa-solid fa-crown"></i><span data-i18n="go_premium"> Go Premium</span>
            </a>
        </div>

        <!-- Share Button -->
<div class="nav-divider"></div>
<a class="nav-item" onclick="shareApp()" style="color:#25d366;">
    <i class="fa-brands fa-whatsapp"></i><span data-i18n="share_app"> Share App</span>
</a>

        <div class="main-content">
            <div class="top-header">
                <div class="search-box">
                    <input type="text" id="searchInput" data-i18n-ph="search_ph" placeholder="Search YouTube..." onkeypress="if(event.key==='Enter') searchVideos()">
                    <button onclick="searchVideos()"><i class="fa-solid fa-magnifying-glass"></i></button>
                </div>
                <button class="btn btn-quality" style="width:auto; padding:10px 20px;" onclick="batchDownloadSelected()"><i class="fa-solid fa-download"></i> <span data-i18n="batch_download">Batch Download</span></button>
                <button id="langToggleBtn" class="btn btn-quality" style="width:auto; padding:10px 16px;" onclick="toggleLang()">اردو</button>
                <div class="user-menu" id="userMenu">
                    <button class="login-btn" data-i18n="login" onclick="openAuthModal('login')">Login</button>
                    <button class="signup-btn" data-i18n="signup" onclick="openAuthModal('signup')">Sign Up</button>
                </div>
                <div id="loggedInMenu" style="display:none;" class="user-menu">
                    <div class="user-avatar-menu" onclick="toggleUserDropdown()">
                        <span id="userAvatarText">U</span>
                        <div class="user-dropdown" id="userDropdown">
                            <div class="user-dropdown-item" onclick="logoutUser()"><i class="fa-solid fa-sign-out"></i> <span data-i18n="logout">Logout</span></div>
                        </div>
                    </div>
                </div>
            </div>

       <section id="page-home" class="page-view active">
    <h2 class="page-title"><i class="fa-solid fa-compass"></i> <span data-i18n="recommended">Recommended</span></h2>

    <!-- Premium Banner -->
    <div onclick="openPremiumModal()" style="background:linear-gradient(135deg, #ff0000, #990000); padding:20px; border-radius:15px; margin-bottom:20px; cursor:pointer; text-align:center;">
        <h3 style="color:#fff; font-size:1.3rem;">⚡ PlayTube Premium</h3>
        <p style="color:#fff; margin-top:5px;" data-i18n="premium_banner_sub">Unlimited Downloads | HD Quality | No Ads</p>
        <p style="color:#ffcc00; font-size:1.5rem; font-weight:bold; margin-top:10px;">Rs. 500/month</p>
        <button style="background:#fff; color:#ff0000; border:none; padding:10px 30px; border-radius:25px; font-weight:bold; margin-top:10px; cursor:pointer;" data-i18n="upgrade_now">Upgrade Now</button>
    </div>

    <div id="homeContainer" class="video-grid"></div>
</section>
            <section id="page-social" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-globe"></i> <span data-i18n="social_title">All Social Media Downloader</span></h2>

                <div class="url-download-box">
                    <input type="text" id="socialUrl" data-i18n-ph="social_ph" placeholder="Paste any video URL (YouTube, Facebook, Instagram, TikTok, Twitter, etc.)">
                    <button onclick="fetchSocialMediaInfo()"><i class="fa-solid fa-magnifying-glass"></i> <span data-i18n="fetch_info">Fetch Info</span></button>
                </div>

                <h3 style="margin:20px 0 10px;" data-i18n="select_platform">Select Platform</h3>
                <div class="platform-grid">
                    <div class="platform-card" onclick="setPlatform('YouTube')">
                        <i class="fa-brands fa-youtube" style="color:#ff0000;"></i>
                        <span>YouTube</span>
                        <small style="display:block; color:#666; margin-top:5px;">Video, Audio</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Facebook')">
                        <i class="fa-brands fa-facebook" style="color:#1877f2;"></i>
                        <span>Facebook</span>
                        <small style="display:block; color:#666; margin-top:5px;">Video, Reels</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Instagram')">
                        <i class="fa-brands fa-instagram" style="color:#e4405f;"></i>
                        <span>Instagram</span>
                        <small style="display:block; color:#666; margin-top:5px;">Reels, Posts, Stories</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('TikTok')">
                        <i class="fa-brands fa-tiktok" style="color:#69c9d0;"></i>
                        <span>TikTok</span>
                        <small style="display:block; color:#666; margin-top:5px;">Videos</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Twitter')">
                        <i class="fa-brands fa-twitter" style="color:#1da1f2;"></i>
                        <span>Twitter/X</span>
                        <small style="display:block; color:#666; margin-top:5px;">Videos, GIFs</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Reddit')">
                        <i class="fa-brands fa-reddit" style="color:#ff4500;"></i>
                        <span>Reddit</span>
                        <small style="display:block; color:#666; margin-top:5px;">Videos, Images</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Pinterest')">
                        <i class="fa-brands fa-pinterest" style="color:#e60023;"></i>
                        <span>Pinterest</span>
                        <small style="display:block; color:#666; margin-top:5px;">Images, Videos</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Vimeo')">
                        <i class="fa-brands fa-vimeo" style="color:#1ab7ea;"></i>
                        <span>Vimeo</span>
                        <small style="display:block; color:#666; margin-top:5px;">Videos</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('SoundCloud')">
                        <i class="fa-brands fa-soundcloud" style="color:#ff5500;"></i>
                        <span>SoundCloud</span>
                        <small style="display:block; color:#666; margin-top:5px;">Audio</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Dailymotion')">
                        <i class="fa-solid fa-play" style="color:#0066dc;"></i>
                        <span>Dailymotion</span>
                        <small style="display:block; color:#666; margin-top:5px;">Videos</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('LinkedIn')">
                        <i class="fa-brands fa-linkedin" style="color:#0a66c2;"></i>
                        <span>LinkedIn</span>
                        <small style="display:block; color:#666; margin-top:5px;">Videos</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Twitch')">
                        <i class="fa-brands fa-twitch" style="color:#9146ff;"></i>
                        <span>Twitch</span>
                        <small style="display:block; color:#666; margin-top:5px;">Clips</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('Snapchat')">
                        <i class="fa-brands fa-snapchat" style="color:#fffc00;"></i>
                        <span>Snapchat</span>
                        <small style="display:block; color:#666; margin-top:5px;">Stories</small>
                    </div>
                    <div class="platform-card" onclick="setPlatform('WhatsApp')">
                        <i class="fa-brands fa-whatsapp" style="color:#25d366;"></i>
                        <span>WhatsApp</span>
                        <small style="display:block; color:#666; margin-top:5px;">Status</small>
                    </div>
                </div>

                <div class="social-result" id="socialResult">
                    <div class="social-result-info">
                        <img class="social-result-thumbnail" id="socialThumbnail" src="" alt="">
                        <div>
                            <div class="social-result-title" id="socialTitle"></div>
                            <div class="social-result-meta" id="socialMeta"></div>
                        </div>
                    </div>
                    <div class="social-download-options">
                        <button class="social-format-btn social-format-video" onclick="downloadSocialMedia('video')">
                            <i class="fa-solid fa-video"></i> <span data-i18n="dl_video_mp4">Download Video (MP4)</span>
                        </button>
                        <button class="social-format-btn social-format-audio" onclick="downloadSocialMedia('audio')">
                            <i class="fa-solid fa-music"></i> <span data-i18n="dl_audio_mp3">Download Audio (MP3)</span>
                        </button>
                    </div>
                </div>
            </section>

            <section id="page-trending" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-fire"></i> <span data-i18n="trending">Trending</span></h2>
                <div id="trendingContainer" class="video-grid"></div>
            </section>

            <section id="page-music" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-music"></i> <span data-i18n="music">Music</span></h2>
                <div id="musicContainer" class="video-grid"></div>
            </section>

            <section id="page-gaming" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-gamepad"></i> <span data-i18n="gaming">Gaming</span></h2>
                <div id="gamingContainer" class="video-grid"></div>
            </section>

            <section id="page-news" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-newspaper"></i> <span data-i18n="news">News</span></h2>
                <div id="newsContainer" class="video-grid"></div>
            </section>

            <section id="page-watch" class="page-view">
                <button class="btn btn-play" style="width:auto; padding:10px 20px; margin-bottom:20px;" onclick="goBack()">
                    <i class="fa-solid fa-arrow-left"></i> <span data-i18n="back">Back</span>
                </button>
                <div class="player-container">
                    <div class="iframe-wrapper">
                        <iframe id="youtubePlayer" src="" allowfullscreen allow="autoplay; encrypted-media; picture-in-picture"></iframe>
                    </div>
                    <div class="player-info">
                        <h2 class="player-title" id="playerTitle"></h2>
                        <p class="player-channel" id="playerChannel"></p>
                        <div class="player-actions">
                            <button class="btn btn-quality" onclick="openQualityModal()">
                                <i class="fa-solid fa-gear"></i> <span data-i18n="quality">Quality</span>
                            </button>
                            <button class="btn btn-download-mp3" onclick="downloadFromPlayer('mp3')">
                                <i class="fa-solid fa-music"></i> MP3
                            </button>
                            <button class="btn btn-download-mp4" onclick="downloadFromPlayer('mp4')">
                                <i class="fa-solid fa-video"></i> MP4
                            </button>
                            <button class="btn btn-quality" onclick="openFormats(currentVideoId, currentVideoTitle)">
                                <i class="fa-solid fa-scissors"></i> <span data-i18n="clip">Clip</span>
                            </button>
                            <button class="btn btn-quality" onclick="downloadThumbnail(currentVideoId)">
                                <i class="fa-solid fa-image"></i> <span data-i18n="thumbnail">Thumbnail</span>
                            </button>
                            <button class="btn btn-quality" onclick="downloadSubtitles(currentVideoId)">
                                <i class="fa-solid fa-closed-captioning"></i> <span data-i18n="subtitles">Subtitles</span>
                            </button>
                            <button class="btn btn-quality" onclick="getVideoInfo(currentVideoId)">
                                <i class="fa-solid fa-info"></i> <span data-i18n="info">Info</span>
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            <section id="page-history" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-clock-rotate-left"></i> <span data-i18n="watch_history">Watch History</span></h2>
                <div id="historyContainer"></div>
            </section>

            <section id="page-downloads" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-download"></i> <span data-i18n="downloads">Downloads</span></h2>
                <div id="downloadsContainer"></div>
            </section>

            <section id="page-app" class="page-view">
                <h2 class="page-title"><i class="fa-solid fa-mobile-screen"></i> <span data-i18n="app_page_title">Download PlayTube App</span></h2>
                <div class="app-cards">
                    <div class="app-card">
                        <div class="app-card-icon">📱</div>
                        <h3 data-i18n="android_title">Android App</h3>
                        <p data-i18n="android_desc">Install PlayTube on your Android phone: home-screen icon, full-screen app, all downloads + AI features.</p>
                        <button class="fmt-dl-btn" onclick="installPlayTubeApp()">📲 <span data-i18n="android_install">Install App (PWA)</span></button>
                        <a id="apkDownloadBtn" class="app-apk-btn" href="/playtube.apk" download style="display:none;">⬇️ <span data-i18n="android_apk">Download APK</span></a>
                        <div id="apkSoonNote" class="app-soon">🚧 <span data-i18n="apk_soon">APK coming soon after launch</span></div>
                    </div>
                    <div class="app-card">
                        <div class="app-card-icon">💻</div>
                        <h3 data-i18n="pc_title">PC (Windows) App</h3>
                        <p data-i18n="pc_desc">Install PlayTube on your PC: it adds a desktop icon and opens in its own window, just like a real Windows app (Chrome / Edge).</p>
                        <button class="fmt-dl-btn" onclick="installPlayTubeAppPC()">💻 <span data-i18n="pc_install">Install for PC</span></button>
                    </div>
                </div>
            </section>
        </div>
    </div>
</div>
<!-- Footer -->
<div style="text-align:center; padding:20px; margin-top:30px; border-top:1px solid #333;">
    <a href="/privacy-policy" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="privacy">Privacy Policy</a>
    <span style="color:#666;">|</span>
    <a href="/terms-of-service" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="terms">Terms of Service</a>
    <span style="color:#666;">|</span>
<a href="/about" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="about">About</a>
<span style="color:#666;">|</span>
<a href="/contact" style="color:#aaa; margin:0 10px; text-decoration:none;" data-i18n="contact">Contact</a>
    <p style="color:#666; margin-top:10px; font-size:0.8rem;">© 2026 PlayTube - All Rights Reserved</p>
</div>
<!-- Rating Section -->
<div style="text-align:center; padding:20px; margin-top:20px; background:#1a1a1a; border-radius:10px; max-width:600px; margin:20px auto;">
    <h3 style="color:#fff;">⭐ Rate PlayTube</h3>
    <p style="color:#aaa; margin:10px 0;">Agar aapko app pasand aayi to rate karein!</p>
    <div style="font-size:2rem; cursor:pointer;">
        <span onclick="rateApp(1)">⭐</span>
        <span onclick="rateApp(2)">⭐</span>
        <span onclick="rateApp(3)">⭐</span>
        <span onclick="rateApp(4)">⭐</span>
        <span onclick="rateApp(5)">⭐</span>
    </div>
    <p id="ratingMessage" style="color:#4CAF50; margin-top:10px;"></p>
</div>
    <!-- Premium Modal -->
    <div id="premiumModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:99999; overflow-y:auto; padding:20px;">
        <div style="background:#1a1a1a; padding:30px; border-radius:20px; max-width:500px; margin:20px auto;">
            <h2 style="color:#fff; text-align:center;">⚡ PlayTube Premium</h2>
            <p style="color:#aaa; text-align:center;">Unlock unlimited downloads</p>

            <div style="display:flex; gap:15px; margin:20px 0; flex-wrap:wrap;">
                <div style="flex:1; min-width:130px; background:#272727; padding:20px; border-radius:10px; text-align:center;">
                    <h3 style="color:#ff0000;">Weekly</h3>
                    <p style="font-size:1.8rem; color:#fff;">Rs. 200</p>
                    <p style="color:#aaa; font-size:0.8rem;">7 days</p>
                    <button onclick="selectPremiumPlan('weekly')" style="background:#ff0000; color:#fff; border:none; padding:10px 20px; border-radius:25px; cursor:pointer; width:100%; margin-top:10px;">Select</button>
                </div>
                <div style="flex:1; min-width:130px; background:#272727; padding:20px; border-radius:10px; text-align:center; border:2px solid #ff0000;">
                    <h3 style="color:#ff0000;">Monthly</h3>
                    <p style="font-size:1.8rem; color:#fff;">Rs. 500</p>
                    <p style="color:#aaa; font-size:0.8rem;">30 days</p>
                    <button onclick="selectPremiumPlan('monthly')" style="background:#ff0000; color:#fff; border:none; padding:10px 20px; border-radius:25px; cursor:pointer; width:100%; margin-top:10px;">Select</button>
                </div>
                <div style="flex:1; min-width:130px; background:#272727; padding:20px; border-radius:10px; text-align:center;">
                    <h3 style="color:#ff0000;">Yearly</h3>
                    <p style="font-size:1.8rem; color:#fff;">Rs. 3000</p>
                    <p style="color:#aaa; font-size:0.8rem;">365 days</p>
                    <button onclick="selectPremiumPlan('yearly')" style="background:#ff0000; color:#fff; border:none; padding:10px 20px; border-radius:25px; cursor:pointer; width:100%; margin-top:10px;">Select</button>
                </div>
            </div>

            <div id="paymentMethods" style="display:none;">
                <h3 style="color:#fff; text-align:center; margin:20px 0;">Pay via:</h3>
                <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:10px;">
                    <button onclick="selectPayment('jazzcash')" style="background:#e60000; color:#fff; border:none; padding:15px; border-radius:10px; cursor:pointer; font-size:1rem;">
                        <i class="fa-solid fa-wallet"></i> JazzCash
                    </button>
                    <button onclick="selectPayment('easypaisa')" style="background:#009900; color:#fff; border:none; padding:15px; border-radius:10px; cursor:pointer; font-size:1rem;">
                        <i class="fa-solid fa-mobile"></i> EasyPaisa
                    </button>
                </div>

                <div id="paymentForm" style="display:none; margin-top:20px;">
                    <div style="background:#000; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px;">
                        <p style="color:#fff;">Send <strong id="paymentAmount" style="color:#4CAF50;">Rs. 0</strong> to:</p>
                        <p style="color:#4CAF50; font-size:1.3rem; font-weight:bold;" id="paymentAccount">Account Number</p>
                        <p style="color:#aaa; font-size:0.9rem;" id="paymentTitle">PlayTube Premium</p>
                    </div>
                    <input type="text" id="senderAccount" placeholder="Your account number (e.g., 0300-1234567)" style="width:100%; padding:12px; background:#272727; border:1px solid #444; border-radius:8px; color:#fff; margin-bottom:10px;">
                    <input type="text" id="transactionId" placeholder="Transaction ID (Reference Number)" style="width:100%; padding:12px; background:#272727; border:1px solid #444; border-radius:8px; color:#fff; margin-bottom:10px;">
                    <button onclick="submitPremiumPayment()" style="background:#4CAF50; color:#fff; border:none; padding:12px; border-radius:25px; cursor:pointer; width:100%; font-weight:bold;">Submit Payment</button>
                    <p style="color:#aaa; text-align:center; margin-top:10px; font-size:0.8rem;">Premium activates within 2-4 hours after verification</p>
                </div>
            </div>

            <button onclick="closePremiumModal()" style="background:#444; color:#fff; border:none; padding:10px; border-radius:25px; cursor:pointer; margin-top:15px; width:100%;">Close</button>
        </div>
    </div>

    <script>
        let currentVideoId = null;
        let currentVideoTitle = '';
        let currentChannelId = '';
        let currentChannelTitle = '';
        let selectedVideos = [];
        let downloadsList = [];
        let progressInterval = null;
        let currentUser = null;
        let pendingQualityVideo = null;
        let socialMediaInfo = null;
        let watchHistory = [];
        let selectedPremiumPlan = null;
        let selectedPaymentMethod = null;

        window.addEventListener('DOMContentLoaded', () => {
        // URL se video play karo
const urlParams = new URLSearchParams(window.location.search);
const videoParam = urlParams.get('video');
if (videoParam) {
    const titleParam = urlParams.get('title') || 'Video';
    playVideo(videoParam, titleParam, '', '');
}
            loadVideos('trending', 'homeContainer');
            loadVideos('trending videos', 'trendingContainer');
            loadVideos('music', 'musicContainer');
            loadVideos('gaming', 'gamingContainer');
            loadVideos('news', 'newsContainer');
            loadDownloadsList();
            checkUserSession();
            loadHistory();
        });

        async function checkUserSession() {
            try {
                const res = await fetch('/api/user-info');
                if (res.ok) {
                    const data = await res.json();
                    if (data.user) {
                        currentUser = data.user;
                        updateUserUI();
                    }
                }
            } catch (err) {}
        }

        function updateUserUI() {
            if (currentUser) {
                document.getElementById('userMenu').style.display = 'none';
                document.getElementById('loggedInMenu').style.display = 'flex';
                document.getElementById(
                    'userAvatarText').textContent = currentUser.username[0].toUpperCase();
            } else {
                document.getElementById('userMenu').style.display = 'flex';
                document.getElementById('loggedInMenu').style.display = 'none';
            }
        }

        function openAuthModal(type) {
            document.getElementById('authModal').classList.add('active');
            if (type === 'login') showLoginForm();
            else showSignupForm();
        }

        function closeAuthModal() { document.getElementById('authModal').classList.remove('active'); }
        function showLoginForm() {
            document.getElementById('authTitle').textContent = 'Login';
            document.getElementById('loginForm').style.display = 'block';
            document.getElementById('signupForm').style.display = 'none';
        }
        function showSignupForm() {
            document.getElementById('authTitle').textContent = 'Sign Up';
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('signupForm').style.display = 'block';
        }

        async function loginUser() {
            const email = document.getElementById('loginEmail').value.trim();
            const password = document.getElementById('loginPassword').value;
            if (!email || !password) { showNotification('Please fill in all fields', 'warning'); return; }

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email, password})
                });
                const data = await res.json();
                if (res.ok) {
                    currentUser = data.user;
                    updateUserUI();
                    closeAuthModal();
                    showNotification('Logged in successfully!', 'success');
                } else {
                    showNotification(data.error || 'Login failed', 'warning');
                }
            } catch (err) { showNotification('Error logging in', 'warning'); }
        }

        async function signupUser() {
            const username = document.getElementById('signupUsername').value.trim();
            const email = document.getElementById('signupEmail').value.trim();
            const password = document.getElementById('signupPassword').value;
            if (!username || !email || !password) { showNotification('Please fill in all fields', 'warning'); return; }

            try {
                const res = await fetch('/api/signup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, email, password})
                });
                const data = await res.json();
                if (res.ok) {
                    currentUser = data.user;
                    updateUserUI();
                    closeAuthModal();
                    showNotification(
                        'Account created successfully!', 'success');
                } else {
                    showNotification(data.error || 'Signup failed', 'warning');
                }
            } catch (err) { showNotification('Error creating account', 'warning'); }
        }

        async function logoutUser() {
            try {
                await fetch('/api/logout', {method: 'POST'});
                currentUser = null;
                updateUserUI();
                showNotification('Logged out successfully!', 'success');
            } catch (err) {}
        }

        function toggleUserDropdown() { document.getElementById('userDropdown').classList.toggle('active'); }

        function setPlatform(platform) {
            const input = document.getElementById('socialUrl');
            input.placeholder = `Paste ${platform} URL here...`;
            input.focus();
        }

        async function fetchSocialMediaInfo() {
            const url = document.getElementById('socialUrl').value.trim();
            if (!url) {
                showNotification('Please paste a URL first', 'warning');
                return;
            }

            showNotification('Fetching video information...', 'success');

            try {
                const res = await fetch('/api/fetch-social-info', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                const data = await res.json();

                if (res.ok && data.info) {
                    socialMediaInfo = data.info;

                    document.getElementById('socialResult').classList.add('active');
                    document.getElementById('socialThumbnail').src = data.info.thumbnail || '';
                    document.getElementById('socialTitle').textContent = data.info.title || 'Unknown Title';

                    let metaText = '';
                    if (data.info.platform) metaText += `Platform: ${data.info.platform}`;
                    if (data.info.duration) metaText += ` | Duration: ${Math.floor(data.info.duration / 60)}:${String(Math.floor(data.info.duration % 60)).padStart(2, '0')}`;
                    if (data.info.uploader) metaText += ` | Uploader: ${data.info.uploader}`;
                    document.getElementById(
                        'socialMeta').textContent = metaText;

                    showNotification(
                        'Video information fetched successfully!', 'success');
                } else {
                    showNotification(data.error || 'Failed to fetch video information', 'warning');
                }
            } catch (err) {
                showNotification(
                    'Error fetching video information', 'warning');
            }
        }

        async function downloadSocialMedia(format) {
            const url = document.getElementById('socialUrl').value.trim();
            if (!url) {
                showNotification('Please paste a URL first', 'warning');
                return;
            }

            showNotification(`Starting ${format} download...`, 'success');

            const downloadId = `social_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            addDownloadProgress(downloadId, 'social', format);

            try {
                const res = await fetch('/api/download-social', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(
                        {url: url, format: format, download_id: downloadId})
                });
                const data = await res.json();

                if (!res.ok) {
                    updateDownloadStatus(downloadId, 'error', data.error || 'Download failed');
                    showNotification(data.error || 'Download failed', 'warning');
                }
            } catch (err) {
                updateDownloadStatus(downloadId, 'error', err.message);
                showNotification('Error downloading', 'warning');
            }

            if (!progressInterval) progressInterval = setInterval(updateAllProgress, 1000);
        }

        async function searchVideos() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) return;
            switchPage('home');
            await loadVideos(query, 'homeContainer');
        }

        async function loadVideos(query, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '<div style="text-align:center; padding:40px;"><i class="fa-solid fa-spinner fa-spin"></i><p>Searching...</p></div>';

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&max=50`);
        const data = await res.json();

        if (data.items && data.items.length > 0) {
            renderVideos(data.items, container);
        } else {
            const fallbackRes = await fetch(`/api/search?q=trending&max=30`);
            const fallbackData = await fallbackRes.json();

            if (fallbackData.items && fallbackData.items.length > 0) {
                renderVideos(fallbackData.items, container);
                showNotification('Showing trending videos instead', 'warning');
            } else {
                container.innerHTML = '<div style="text-align:center; padding:40px;"><p>Try different keywords!</p></div>';
            }
        }
    } catch (err) {
        try {
            const fallbackRes = await fetch(`/api/search?q=music&max=20`);
            const fallbackData = await fallbackRes.json();

            if (fallbackData.items && fallbackData.items.length > 0) {
                renderVideos(fallbackData.items, container);
                showNotification('Showing popular videos', 'warning');
            } else {
                container.innerHTML = '<div style="text-align:center; padding:40px;"><p>Connection error. Please try again.</p></div>';
            }
        } catch (err2) {
            container.innerHTML = '<div style="text-align:center; padding:40px;"><p>Connection error. Check your internet.</p></div>';
        }
    }
}
        function renderVideos(items, container) {
    container.innerHTML = '';

    items.forEach(item => {
        const videoId = item.id.videoId || item.id;
        const title = item.snippet.title;
        const channel = item.snippet.channelTitle;
        const channelId = item.snippet.channelId;
        const thumb = item.snippet.thumbnails.high?.url || item.snippet.thumbnails.medium?.url || item.snippet.thumbnails.default?.url || ('https://i.ytimg.com/vi/' + videoId + '/hqdefault.jpg');

        const card = document.createElement('div');
        card.className = 'video-card';
        card.innerHTML = `
            <div class="thumbnail-box">
                <input type="checkbox" class="select-checkbox" onchange="toggleSelect('${videoId}')">
                ${thumb ? `<img src="${thumb}" alt="${escapeHtml(title)}" onclick="playVideo('${videoId}', '${escapeHtml(title)}', '${channelId}', '${escapeHtml(channel)}')">` : '<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:#333;"><i class="fa-solid fa-video" style="font-size:3rem; color:#666;"></i></div>'}
            </div>
            <div class="card-details">
                <div class="card-title" onclick="playVideo('${videoId}', '${escapeHtml(title)}', '${channelId}', '${escapeHtml(channel)}')">${escapeHtml(title)}</div>
                <div class="card-channel" onclick="window.location.href='/channel/${channelId}';" style="cursor:pointer; color:#aaa; font-size:0.8rem; text-decoration:underline;">${escapeHtml(channel)} ✓</div>
                <div class="action-btns">
                    <button class="btn btn-play" onclick="playVideo('${videoId}', '${escapeHtml(title)}', '${channelId}', '${escapeHtml(channel)}')"><i class="fa-solid fa-play"></i></button>
                    <button class="btn btn-quality" onclick="openQualityModal('${videoId}')"><i class="fa-solid fa-gear"></i></button>
                    <button class="btn btn-download-mp3" onclick="downloadVideo('${videoId}', 'mp3', '${escapeHtml(title)}')"><i class="fa-solid fa-music"></i> MP3</button>
                    <button class="btn btn-download-mp4" onclick="downloadVideo('${videoId}', 'mp4', '${escapeHtml(title)}')"><i class="fa-solid fa-video"></i> MP4</button>
                    <button class="btn" onclick="downloadThumbnail('${videoId}')"><i class="fa-solid fa-image"></i></button>
                    <button class="btn" onclick="downloadSubtitles('${videoId}')"><i class="fa-solid fa-closed-captioning"></i></button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

        async function playVideo(videoId, title, channelId, channelTitle) {
    currentVideoId = videoId;
    currentVideoTitle = decodeURIComponent(title);
    currentChannelId = channelId;
    currentChannelTitle = decodeURIComponent(channelTitle);
    
    // Try multiple embed formats
    const embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1`;
    document.getElementById('youtubePlayer').src = embedUrl;
    document.getElementById('playerTitle').innerText = currentVideoTitle;
    document.getElementById('playerChannel').innerHTML = `Channel: ${currentChannelTitle} <a href="/channel/${currentChannelId}" style="color:#ff0000; text-decoration:underline;">Visit Channel</a>`;
    
    addToHistory(videoId, currentVideoTitle, currentChannelTitle);
    
    switchPage('watch');
}

        function openQualityModal(videoId) {
            pendingQualityVideo = videoId;
            const modal = document.getElementById('qualityModal');
            const options = document.getElementById('qualityOptions');

            const qualities = [
                { label: 'Best Available', value: 'best' },
                { label: '4K (2160p)', value: '2160p' },
                { label: 'Full HD (1080p)', value: '1080p' },
                { label: 'HD (720p)', value: '720p' },
                { label: 'SD (480p)', value: '480p' }
            ];

            options.innerHTML = qualities.map(q => `
                <div class="quality-option" onclick="downloadWithQuality('${q.value}')" style="padding:10px; cursor:pointer; border-bottom:1px solid var(--border-color);">
                    <span>${q.label}</span>
                    <i class="fa-solid fa-download"></i>
                </div>
            `).join('');

            modal.classList.add('active');
        }

        function closeQualityModal() { document.getElementById('qualityModal').classList.remove('active'); }

        function downloadWithQuality(quality) {
            closeQualityModal();
            downloadVideo(pendingQualityVideo, 'mp4', '', quality);
        }

        function toggleSelect(videoId) {
            const index = selectedVideos.indexOf(videoId);
            if (index === -1) selectedVideos.push(videoId);
            else selectedVideos.splice(index, 1);
        }

        function downloadVideo(videoId, format, title, quality = null) {
            const downloadId = `${videoId}_${Date.now()}`;
            addDownloadProgress(downloadId, videoId, format, quality);

            fetch(`/api/start-download`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(
                    {video_id: videoId, format: format, quality: quality, download_id: downloadId})
            })
            .then(response => response.json())
            .then(data => { if (data.error) updateDownloadStatus(downloadId, 'error', data.error); })
            .catch(error => { updateDownloadStatus(downloadId, 'error', error.message); });

            if (!progressInterval) progressInterval = setInterval(updateAllProgress, 1000);
        }

        function downloadFromPlayer(format) {
            if (currentVideoId) {
                if (format === 'mp4') openQualityModal(currentVideoId);
                else downloadVideo(currentVideoId, 'mp3', currentVideoTitle);
            }
        }

        async function downloadPlaylist() {
    const url = prompt('Enter playlist URL:');
    if (!url) return;

    const format = confirm('Click OK for MP3, Cancel for MP4') ? 'mp3' : 'mp4';

    try {
        const res = await fetch('/api/download-playlist', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({playlist_url: url, format: format})
        });

        const data = await res.json();

        if (res.ok && data.success) {
            showNotification('Playlist download started!', 'success');
            if (!progressInterval) progressInterval = setInterval(updateAllProgress, 1000);
        } else {
            if (data.premium_required) {
                showNotification(
                    '⚡ Premium required for playlist download!', 'warning');
                openPremiumModal();
            } else if (data.login_required) {
                showNotification('Please login first!', 'warning');
                openAuthModal('login');
            } else {
                showNotification(data.error || 'Error', 'warning');
            }
        }
    } catch (err) {
        showNotification('Error: ' + err.message, 'warning');
    }
}

        async function batchDownloadSelected() {
    if (selectedVideos.length === 0) {
        showNotification('Please select videos first', 'warning');
        return;
    }

    const format = confirm('Click OK for MP3, Cancel for MP4') ? 'mp3' : 'mp4';

    try {
        const res = await fetch('/api/batch-download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({video_ids: selectedVideos, format: format})
        });

        const data = await res.json();

        if (res.ok && data.success) {
            showNotification(`Batch download started for ${selectedVideos.length} videos!`, 'success');
            selectedVideos = [];
            if (!progressInterval) progressInterval = setInterval(updateAllProgress, 1000);
        } else {
            if (data.premium_required) {
                showNotification(
                    '⚡ Premium required for batch download!', 'warning');
                openPremiumModal();
            } else if (data.login_required) {
                showNotification('Please login first!', 'warning');
                openAuthModal('login');
            } else {
                showNotification(data.error || 'Error', 'warning');
            }
        }
    } catch (err) {
        showNotification('Error: ' + err.message, 'warning');
    }
}

        function downloadThumbnail(videoId) {
            if (videoId) {
                window.open(`/api/download-thumbnail/${videoId}`, '_blank');
            }
        }

        function downloadSubtitles(videoId) {
            if (!videoId) return;

            const lang = prompt('Enter language code (e.g., en, hi, es):', 'en');
            if (!lang) return;

            fetch('/api/download-subtitles', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({video_id: videoId, lang: lang})
            })
            .then(res => {
                if (res.ok) return res.blob();
                return res.json().then(data => { throw new Error(data.error || 'Failed to download subtitles'); });
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${videoId}_${lang}.srt`;
                a.click();
                window.URL.revokeObjectURL(url);
                showNotification('Subtitles downloaded!', 'success');
            })
            .catch(err => {
                showNotification(err.message || 'Error downloading subtitles', 'warning');
            });
        }

        async function getVideoInfo(videoId) {
            if (!videoId) return;

            try {
                const res = await fetch(`/api/video-info/${videoId}`);
                const data = await res.json();
                if (res.ok) {
                    showNotification(`Views: ${data.view_count}, Likes: ${data.like_count}, Duration: ${Math.floor(data.duration/60)}:${String(data.duration%60).padStart(2,'0')}`, 'success');
                }
            } catch (err) {
                showNotification('Error fetching video info', 'warning');
            }
        }

        function openDownloadFolder() {
            fetch('/api/open-folder')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showNotification('Folder opened!', 'success');
                }
            });
        }

        async function getStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                showNotification(`Total Downloads: ${data.total_downloads}, Size: ${(data.total_size / (1024*1024)).toFixed(2)} MB`, 'success');
            } catch (err) {}
        }

        async function addToHistory(videoId, title, channel) {
            try {
                await fetch('/api/add-history', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(
                        {video_id: videoId, title: title, channel: channel})
                });
            } catch (err) {}
        }

        async function loadHistory() {
            try {
                const res = await fetch('/api/history');
                const data = await res.json();
                if (data.history) {
                    watchHistory = data.history;
                    updateHistoryUI();
                }
            } catch (err) {}
        }

        function updateHistoryUI() {
            const container = document.getElementById('historyContainer');
            if (!container) return;

            if (!watchHistory || watchHistory.length === 0) {
                container.innerHTML = '<p style="color:#aaa;">No watch history</p>';
                return;
            }

            container.innerHTML = '<div class="video-grid"></div>';
            const grid = container.querySelector('.video-grid');

            watchHistory.forEach(item => {
                const card = document.createElement('div');
                card.className = 'video-card';
                card.innerHTML = `
                    <div class="card-details">
                        <div class="card-title" onclick="playVideo('${item.video_id}', '${escapeHtml(item.title)}', '', '${escapeHtml(item.channel)}')">${escapeHtml(item.title)}</div>
            <div class="card-channel" onclick="window.location.href='/channel/${channelId}';" style="cursor:pointer;color:#aaa;font-size:0.8rem;text-decoration:underline;">${escapeHtml(channel)} ✓</div>
                        <div class="action-btns">
                            <button class="btn btn-play" onclick="playVideo('${item.video_id}', '${escapeHtml(item.title)}', '', '${escapeHtml(item.channel)}')"><i class="fa-solid fa-play"></i></button>
                            <button class="btn btn-download-mp3" onclick="downloadVideo('${item.video_id}', 'mp3', '${escapeHtml(item.title)}')"><i class="fa-solid fa-music"></i> MP3</button>
                            <button class="btn btn-download-mp4" onclick="downloadVideo('${item.video_id}', 'mp4', '${escapeHtml(item.title)}')"><i class="fa-solid fa-video"></i> MP4</button>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function addDownloadProgress(downloadId, videoId, format, quality = null) {
            const panel = document.getElementById('downloadProgressPanel');
            panel.classList.add('active');

            const list = document.getElementById('downloadProgressList');
            const item = document.createElement('div');
            item.className = 'download-item';
            item.id = `download-${downloadId}`;
            item.innerHTML = `
                <div class="download-item-title">Downloading ${format.toUpperCase()}${quality ? ' (' + quality + ')' : ''}...</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div>
                <div class="download-item-info">
                    <span class="download-status">Starting...</span>
                    <span class="download-speed">0%</span>
                </div>
            `;
            list.insertBefore(item, list.firstChild);
        }

        function updateDownloadStatus(downloadId, status, message) {
            const item = document.getElementById(`download-${downloadId}`);
            if (!item) return;

            const statusElement = item.querySelector('.download-status');
            const fillElement = item.querySelector('.progress-fill');

            if (status === 'completed') {
                statusElement.innerText = '✓ Downloaded!';
                item.classList.add('completed');
                fillElement.style.width = '100%';
                showNotification('Download completed!', 'success');
                loadDownloadsList();
            } else if (status === 'error') {
                statusElement.innerText = 'Error: ' + message;
                fillElement.style.background = '#ff0000';
            }
        }

        async function updateAllProgress() {
            try {
                const res = await fetch('/api/download-progress');
                const data = await res.json();

                for (const [downloadId, progress] of Object.entries(data)) {
                    const item = document.getElementById(`download-${downloadId}`);
                    if (!item) continue;

                    const fillElement = item.querySelector('.progress-fill');
                    const statusElement = item.querySelector('.download-status');
                    const speedElement = item.querySelector('.download-speed');
                    const titleElement = item.querySelector('.download-item-title');

                    fillElement.style.width = progress.percent + '%';
                    speedElement.innerText = progress.percent + '%';
                    if (progress.title) titleElement.innerText = progress.title;

                    if (progress.status === 'downloading') {
                        statusElement.innerText = `Downloading... ${progress.speed || ''}`;
                    } else if (progress.status === 'completed') {
                        statusElement.innerText = '✓ Downloaded!';
                        item.classList.add('completed');
                        fillElement.style.width = '100%';
                        loadDownloadsList();
                    } else if (progress.status === 'error') {
                        statusElement.innerText = 'Error: ' + progress.error;
                    }
                }
            } catch (err) {}
        }

        function openProgressPanel() { document.getElementById('downloadProgressPanel').classList.add('active'); }
        function toggleProgressPanel() {
            const panel = document.getElementById('downloadProgressPanel');
            if (panel.classList.contains('active')) panel.classList.remove('active');
            else panel.classList.add('active');
        }

        async function loadDownloadsList() {
            try {
                const res = await fetch('/api/downloads-list');
                const data = await res.json();
                if (data.downloads) {
                    downloadsList = data.downloads;
                    updateDownloadsUI();
                }
            } catch (err) {}
        }

        function updateDownloadsUI() {
            const container = document.getElementById('downloadsContainer');
            if (!container) return;

            if (!downloadsList || downloadsList.length === 0) {
                container.innerHTML = '<p style="color:#aaa;">No downloads yet</p>';
                return;
            }

            container.innerHTML = '<div class="video-grid"></div>';
            const grid = container.querySelector('.video-grid');

            downloadsList.forEach(download => {
                const card = document.createElement('div');
                card.className = 'video-card';
                const fileUrl = `/api/download-file/${download.downloadId}`;
                const isMp3 = download.format === 'MP3';

                card.innerHTML = `
                    <div class="card-details">
                        <div class="card-title">${escapeHtml(download.title || download.videoId)}</div>
                        <div class="card-channel">Format: ${download.format}${download.platform ? ' | Platform: ' + download.platform : ''}</div>
                        ${isMp3 ? `<audio controls style="width:100%; margin-top:10px;"><source src="${fileUrl}" type="audio/mpeg"></audio>` : `<video controls style="width:100%; margin-top:10px;"><source src="${fileUrl}" type="video/mp4"></video>`}
                        <div class="action-btns" style="margin-top:10px;">
                            <a href="${fileUrl}" class="btn btn-download-mp3" download><i class="fa-solid fa-download"></i> Save to Device</a>
                            <button class="btn btn-quality" onclick="deleteDownload('${download.downloadId}')"><i class="fa-solid fa-trash"></i> Delete</button>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        async function deleteDownload(downloadId) {
            if (!confirm('Delete this download?')) return;

            try {
                const res = await fetch(`/api/delete-download/${downloadId}`, {method: 'DELETE'});
                const data = await res.json();
                if (data.success) {
                    showNotification('Download deleted!', 'success');
                    loadDownloadsList();
                }
            } catch (err) {}
        }

        function switchPage(pageId) {
            document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            const pageElement = document.getElementById(`page-${pageId}`);
            if (pageElement) pageElement.classList.add('active');

            const navItem = document.querySelector(`.nav-item[data-page="${pageId}"]`);
            if (navItem) navItem.classList.add('active');

            if (pageId === 'downloads') loadDownloadsList();
            if (pageId === 'history') loadHistory();
            window.scrollTo(0, 0);
        }

        function goBack() {
    document.getElementById('youtubePlayer').src = '';
    switchPage('home');
}

        function showNotification(message, type = '') {
            const notification = document.getElementById('notification');
            document.getElementById('notificationText').innerText = message;
            notification.className = `notification ${type}`;
            notification.style.display = 'block';
            setTimeout(() => { notification.style.display = 'none'; }, 3000);
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Share App
function shareApp() {
    const text = "🎬 PlayTube - Free Video Downloader!%0A%0A✅ YouTube se MP3/MP4 download karo%0A✅ Facebook, Instagram, TikTok se bhi%0A✅ 100% FREE%0A%0A👉 Try now: " + window.location.href;
    window.open('https://wa.me/?text=' + text, '_blank');
}

// Rate App
function rateApp(stars) {
    document.getElementById(
        'ratingMessage').innerText = '✅ Thank you for ' + stars + ' star rating!';
    showNotification('Thanks for rating! ❤️', 'success');
}

// Usage Stats
async function showUsageStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const message = `📊 Total Downloads: ${data.total_downloads}\n💾 Total Size: ${(data.total_size / (1024*1024)).toFixed(2)} MB`;
        showNotification(message, 'success');
    } catch (err) {
        showNotification('Error loading stats', 'warning');
    }
}
        // Premium Functions
        function openPremiumModal() {
            document.getElementById('premiumModal').style.display = 'block';
        }

        function closePremiumModal() {
            document.getElementById('premiumModal').style.display = 'none';
            document.getElementById('paymentMethods').style.display = 'none';
            document.getElementById('paymentForm').style.display = 'none';
        }

        function selectPremiumPlan(plan) {
            selectedPremiumPlan = plan;
            document.getElementById('paymentMethods').style.display = 'block';
            loadPaymentAccounts();
        }

        let paymentAccountsCache = {};
        async function loadPaymentAccounts() {
            try {
                const res = await fetch('/api/premium/plans');
                const data = await res.json();
                paymentAccountsCache = data.payments || {};
            } catch (e) { paymentAccountsCache = {}; }
            return paymentAccountsCache;
        }

        async function selectPayment(method) {
            selectedPaymentMethod = method;
            await loadPaymentAccounts();
            const acc = paymentAccountsCache[method];
            const prices = { weekly: 200, monthly: 500, yearly: 3000 };

            if (!acc || !acc.account_number) {
                document.getElementById('paymentAccount').textContent = 'No account added yet';
                document.getElementById('paymentTitle').textContent = 'Admin ne abhi is method ka account add nahi kiya. Koi aur method try karein ya admin se rabta karein.';
                document.getElementById('paymentAmount').textContent = 'Rs. ' + prices[selectedPremiumPlan];
                document.getElementById('paymentForm').style.display = 'block';
                const btn = document.querySelector('#paymentForm button');
                if (btn) btn.style.display = 'none';
                showNotification('No account added yet for this method', 'warning');
                return;
            }
            const btn2 = document.querySelector('#paymentForm button');
            if (btn2) btn2.style.display = 'block';
            document.getElementById('paymentAccount').textContent = acc.account_number;
            document.getElementById('paymentTitle').textContent = acc.account_title || 'PlayTube Premium';
            document.getElementById('paymentAmount').textContent = 'Rs. ' + prices[selectedPremiumPlan];
            document.getElementById('paymentForm').style.display = 'block';
        }

        async function submitPremiumPayment() {
            const senderAccount = document.getElementById('senderAccount').value.trim();
            const transactionId = document.getElementById('transactionId').value.trim();

            if (!senderAccount || !transactionId) {
                showNotification('Please fill all fields', 'warning');
                return;
            }

            try {
                const res = await fetch('/api/premium/submit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        plan_type: selectedPremiumPlan,
                        payment_method: selectedPaymentMethod,
                        sender_account: senderAccount,
                        transaction_id: transactionId
                    })
                });

                const data = await res.json();

                if (data.success) {
                    showNotification(
                        'Payment submitted! Premium will activate soon.', 'success');
                    closePremiumModal();
                } else {
                    showNotification(data.error || 'Error', 'warning');
                }
            } catch (err) {
                showNotification('Error submitting payment', 'warning');
            }
        }
    </script>
    <!-- Cute Draggable Products - Click + Drag -->
    <style>
        .cute-products {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: center;
            margin: 30px auto;
            padding: 15px;
            max-width: 700px;
            position: relative;
            min-height: 300px;
        }
        .cute-card {
            width: 85px;
            background: #1a1a1a;
            border-radius: 15px;
            padding: 10px 5px;
            text-align: center;
            cursor: pointer;
            position: absolute;
            border: 2px solid #f57224;
            box-shadow: 0 4px 15px rgba(245,114,36,0.3);
            transition: transform 0.2s;
            user-select: none;
            touch-action: none;
            z-index: 10;
        }
        .cute-card:hover {
            transform: scale(1.1);
            border-color: #ff0000;
            box-shadow: 0 8px 25px rgba(255,0,0,0.5);
            z-index: 100;
        }
        .cute-card:active {
            cursor: grabbing;
        }
        .cute-emoji { font-size: 1.8rem; display: block; pointer-events: none; }
        .cute-name {
            color: #fff;
            font-size: 0.6rem;
            margin: 5px 0;
            display: block;
            min-height: 25px;
            pointer-events: none;
        }
        .cute-price { display: block; font-size: 0.65rem; pointer-events: none; }
        .cute-old { color: #666; text-decoration: line-through; display: block; }
        .cute-new { color: #4CAF50; font-weight: bold; display: block; }
        .cute-btn {
            display: block;
            background: #f57224;
            color: #fff;
            padding: 4px;
            border-radius: 15px;
            text-decoration: none;
            font-size: 0.55rem;
            margin-top: 5px;
            pointer-events: auto;
        }
        .discount-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            background: #ff0000;
            color: #fff;
            font-size: 0.5rem;
            padding: 3px 6px;
            border-radius: 10px;
            font-weight: bold;
            animation: pulse 1s infinite;
            pointer-events: none;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
    </style>

    <h3 style="color:#f57224; text-align:center; margin-top:30px; font-size:1.2rem;">🛒 Hot Deals</h3>
    <p style="color:#666; text-align:center; font-size:0.7rem;">👆 Click karo ya Drag karo! ✨</p>

    <div class="cute-products" id="cuteProducts">

        <div class="cute-card" data-link="https://s.daraz.pk/s.XNutK?cc" style="left:10px; top:10px;">
            <span class="discount-badge">48%</span>
            <span class="cute-emoji">👟</span>
            <span class="cute-name">Sneakers</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 2,499</span>
                <span class="cute-new">Rs. 1,299</span>
            </span>
            <a href="https://s.daraz.pk/s.XNutK?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.XNuDU?cc" style="left:105px; top:10px;">
            <span class="discount-badge">76%</span>
            <span class="cute-emoji">🎧</span>
            <span class="cute-name">Earbuds</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 3,000</span>
                <span class="cute-new">Rs. 729</span>
            </span>
            <a href="https://s.daraz.pk/s.XNuDU?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.Xn1PV?cc" style="left:200px; top:10px;">
            <span class="discount-badge">58%</span>
            <span class="cute-emoji">🎧</span>
            <span class="cute-name">P47 Headphone</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 1,999</span>
                <span class="cute-new">Rs. 834</span>
            </span>
            <a href="https://s.daraz.pk/s.Xn1PV?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.XNuyp?cc" style="left:295px; top:10px;">
            <span class="discount-badge">43%</span>
            <span class="cute-emoji">🎤</span>
            <span class="cute-name">MIC</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 1,748</span>
                <span class="cute-new">Rs. 999</span>
            </span>
            <a href="https://s.daraz.pk/s.XNuyp?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.Xn14f?cc" style="left:390px; top:10px;">
            <span class="discount-badge">61%</span>
            <span class="cute-emoji">👚</span>
            <span class="cute-name">Nightwear</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 2,000</span>
                <span class="cute-new">Rs. 790</span>
            </span>
            <a href="https://s.daraz.pk/s.Xn14f?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.XNuze?cc" style="left:485px; top:10px;">
            <span class="discount-badge">14%</span>
            <span class="cute-emoji">🚿</span>
            <span class="cute-name">Scrubber</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 207</span>
                <span class="cute-new">Rs. 179</span>
            </span>
            <a href="https://s.daraz.pk/s.XNuze?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.XNFg7?cc" style="left:580px; top:10px;">
            <span class="discount-badge">58%</span>
            <span class="cute-emoji">👝</span>
            <span class="cute-name">Wallet</span>
            <span class="cute-price">
                <span class="cute-old">Rs. 600</span>
                <span class="cute-new">Rs. 253</span>
            </span>
            <a href="https://s.daraz.pk/s.XNFg7?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

        <div class="cute-card" data-link="https://s.daraz.pk/s.XNuD5?cc" style="left:10px; top:160px;">
            <span class="discount-badge">HOT</span>
            <span class="cute-emoji">📱</span>
            <span class="cute-name">Phone</span>
            <span class="cute-price">
                <span class="cute-new">Rs. 15,999</span>
            </span>
            <a href="https://s.daraz.pk/s.XNuD5?cc" target="_blank" class="cute-btn">Buy</a>
        </div>

    </div>

<script>
let activeCard = null;
let isDragging = false;
let startX = 0;
let startY = 0;
let origX = 0;
let origY = 0;
let moved = false;

document.querySelectorAll('.cute-card').forEach(card => {
    card.addEventListener('mousedown', startDrag);
    card.addEventListener('touchstart', startDrag, {passive: false});
    card.addEventListener('click', function(e) {
        if (!moved) {
            const link = this.getAttribute('data-link');
            if (link) {
                window.open(link, '_blank');
            }
        }
        moved = false;
    });
});

function startDrag(e) {
    e.preventDefault();

    activeCard = this;
    moved = false;

    const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;

    const rect = activeCard.getBoundingClientRect();
    const container = document.getElementById('cuteProducts').getBoundingClientRect();

    startX = clientX;
    startY = clientY;
    origX = rect.left - container.left;
    origY = rect.top - container.top;

    activeCard.style.zIndex = '999';
    activeCard.style.transition = 'none';

    document.addEventListener('mousemove', moveCard);
    document.addEventListener('touchmove', moveCard, {passive: false});
    document.addEventListener('mouseup', stopDrag);
    document.addEventListener('touchend', stopDrag);
}

function moveCard(e) {
    if (!activeCard) return;
    e.preventDefault();

    const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;

    const diffX = Math.abs(clientX - startX);
    const diffY = Math.abs(clientY - startY);

    if (diffX > 5 || diffY > 5) {
        moved = true;
    }

    const newX = origX + (clientX - startX);
    const newY = origY + (clientY - startY);

    activeCard.style.left = newX + 'px';
    activeCard.style.top = newY + 'px';
}

function stopDrag() {
    if (activeCard) {
        activeCard.style.zIndex = '10';
        activeCard.style.transition = 'transform 0.2s';
        activeCard = null;
    }

    document.removeEventListener('mousemove', moveCard);
    document.removeEventListener('touchmove', moveCard);
    document.removeEventListener('mouseup', stopDrag);
    document.removeEventListener('touchend', stopDrag);
}
</script>
    <!-- Visitor Counter -->
    <div style="text-align:center; padding:15px; background:#1a1a1a; margin-top:30px; border-top:1px solid #333;">
        <p style="color:#aaa; margin:0;">
            👥 Visitors Today: <span id="visitorCount" style="color:#4CAF50; font-weight:bold;">0</span>
        </p>
        <p style="color:#666; margin:5px 0 0; font-size:0.8rem;">
            © 2026 PlayTube - Coded by Chuza
        </p>
    </div>

    <script>
    fetch('/api/visitor-stats')
        .then(res => res.json())
        .then(data => {
            document.getElementById(
                'visitorCount').innerText = data.today_visitors;
        })
        .catch(err => {
            document.getElementById('visitorCount').innerText = '...';
        });
    </script>
<!-- ================= PLAYTUBE v3 PREMIUM LAYER (Chuza) ================= -->
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#4f46e5">
<style>
    :root{
        --bg-main:#12102e; --bg-card:rgba(38,34,84,.72); --bg-hover:rgba(79,70,229,.25);
        --red-primary:#6d5df6; --accent:#2dd4bf; --text-main:#f4f2ff; --text-sub:#b6b1d9;
        --border-color:rgba(139,132,255,.28); --success:#34d399; --warning:#fbbf24;
    }
    html[data-theme="light"]{
        --bg-main:#eef0ff; --bg-card:rgba(255,255,255,.85); --bg-hover:#dde1ff;
        --red-primary:#4f46e5; --accent:#0d9488; --text-main:#1c1938; --text-sub:#55517a;
        --border-color:#c9cbef; --success:#059669; --warning:#d97706;
    }
    body{ background:linear-gradient(160deg,var(--bg-main),#1b1650 55%,#0b3b3a 130%) fixed, var(--bg-main); }
    html[data-theme="light"] body{ background:linear-gradient(160deg,#eef0ff,#dfe4ff 60%,#d7f5f0) fixed; }
    .sidebar{ background:linear-gradient(180deg,rgba(24,20,64,.96),rgba(10,40,44,.96)); backdrop-filter:blur(14px); border-right:1px solid var(--border-color); }
    html[data-theme="light"] .sidebar{ background:linear-gradient(180deg,#ffffff,#e6f7f4); }
    .sidebar-brand{ background:linear-gradient(90deg,#a5b4fc,#2dd4bf); -webkit-background-clip:text; background-clip:text; color:transparent !important; letter-spacing:.5px; }
    .sidebar-brand span{ color:var(--accent) !important; -webkit-text-fill-color:var(--accent); }
    .top-header{ background:transparent; backdrop-filter:blur(10px); }
    .video-card{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:16px; overflow:hidden; backdrop-filter:blur(10px); box-shadow:0 10px 28px rgba(5,2,30,.35); transition:transform .18s, box-shadow .18s; }
    .video-card:hover{ transform:translateY(-4px); box-shadow:0 18px 38px rgba(79,70,229,.35); }
    .btn{ border-radius:10px !important; }
    .btn-download-mp4{ background:linear-gradient(90deg,#4f46e5,#7c6cf8) !important; }
    .btn-download-mp3{ background:linear-gradient(90deg,#0d9488,#2dd4bf) !important; color:#062a26 !important; font-weight:700; }
    input, select, textarea{ border-radius:10px !important; }
    .pt2-fab{ position:fixed; right:18px; bottom:18px; z-index:99990; display:flex; flex-direction:column; gap:10px; }
    .pt2-fab button{ width:56px; height:56px; border-radius:50%; border:none; cursor:pointer; font-size:1.25rem; color:#fff; box-shadow:0 10px 24px rgba(0,0,0,.4); }
    #aiFab{ background:linear-gradient(135deg,#4f46e5,#0d9488); }
    #themeFab{ background:linear-gradient(135deg,#312e81,#4f46e5); }
    #aiDrawer{ position:fixed; top:0; right:-430px; width:410px; max-width:94vw; height:100vh; background:var(--bg-card); backdrop-filter:blur(18px); border-left:1px solid var(--border-color); z-index:99995; transition:right .3s; display:flex; flex-direction:column; box-shadow:-16px 0 40px rgba(0,0,0,.45); }
    #aiDrawer.open{ right:0; }
    #aiDrawer header{ padding:16px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); }
    #aiLog{ flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }
    .ai-msg{ padding:10px 12px; border-radius:14px; max-width:92%; white-space:pre-wrap; word-break:break-word; font-size:.92rem; line-height:1.45; }
    .ai-msg.user{ align-self:flex-end; background:linear-gradient(90deg,#4f46e5,#6d5df6); color:#fff; }
    .ai-msg.bot{ align-self:flex-start; background:var(--bg-hover); color:var(--text-main); border:1px solid var(--border-color); }
    .ai-jobbar{ height:8px; background:rgba(127,127,180,.3); border-radius:99px; overflow:hidden; margin-top:6px; }
    .ai-jobbar > div{ height:100%; background:linear-gradient(90deg,#4f46e5,#2dd4bf); width:0%; transition:width .5s; }
    #aiInputRow{ display:flex; gap:8px; padding:12px; border-top:1px solid var(--border-color); }
    #aiInput{ flex:1; padding:12px; background:var(--bg-main); color:var(--text-main); border:1px solid var(--border-color); }
    #aiSend{ padding:12px 18px; border:none; cursor:pointer; color:#fff; font-weight:700; background:linear-gradient(90deg,#4f46e5,#0d9488); border-radius:10px; }
    #formatsModal{ display:none; position:fixed; inset:0; background:rgba(5,3,25,.78); z-index:99996; overflow-y:auto; padding:18px; }
    #formatsModal.open{ display:block; }
    .fmt-sheet{ max-width:560px; margin:24px auto; background:var(--bg-card); backdrop-filter:blur(16px); border:1px solid var(--border-color); border-radius:20px; padding:22px; color:var(--text-main); }
    .fmt-group-title{ color:var(--accent); font-weight:800; margin:16px 0 8px; letter-spacing:.4px; }
    .fmt-row{ display:flex; align-items:center; gap:12px; padding:12px; border:1px solid var(--border-color); border-radius:12px; margin-bottom:8px; cursor:pointer; }
    .fmt-row:hover{ background:var(--bg-hover); }
    .fmt-row.selected{ outline:2px solid var(--accent); background:var(--bg-hover); }
    .fmt-row .grow{ flex:1; }
    .fmt-size{ color:var(--text-sub); font-weight:700; white-space:nowrap; }
    .fmt-dl-btn{ width:100%; padding:15px; border:none; border-radius:99px; font-size:1.05rem; font-weight:800; cursor:pointer; color:#131022; background:linear-gradient(90deg,#fbbf24,#f59e0b); margin-top:14px; }
    .fav-btn.faved{ color:#fbbf24 !important; }
    .smart-box{ display:flex; gap:10px; flex-wrap:wrap; background:var(--bg-card); border:1px solid var(--border-color); border-radius:16px; padding:14px; margin-bottom:18px; backdrop-filter:blur(10px); }
    .smart-box input{ flex:1; min-width:220px; padding:12px; background:var(--bg-main); color:var(--text-main); border:1px solid var(--border-color); }
    .smart-box button{ padding:12px 20px; border:none; cursor:pointer; font-weight:700; color:#fff; background:linear-gradient(90deg,#4f46e5,#0d9488); border-radius:10px; }
    .clip-box{ margin-top:20px; border-top:1px dashed var(--border-color); padding-top:6px; }
    .clip-row{ display:flex; gap:12px; margin:10px 0; }
    .clip-row label{ flex:1; display:flex; flex-direction:column; gap:6px; font-weight:700; color:var(--text-sub); font-size:.9rem; }
    .clip-row input{ padding:12px; background:var(--bg-main); color:var(--text-main); border:1px solid var(--border-color); width:100%; box-sizing:border-box; }
    .clip-btn{ background:linear-gradient(90deg,#0d9488,#2dd4bf) !important; margin-top:4px; }
    .app-cards{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:18px; }
    .app-card{ background:var(--bg-card); border:1px solid var(--border-color); border-radius:18px; padding:26px; text-align:center; backdrop-filter:blur(10px); }
    .app-card-icon{ font-size:3rem; margin-bottom:10px; }
    .app-card h3{ margin-bottom:8px; }
    .app-card p{ color:var(--text-sub); font-size:.95rem; line-height:1.55; min-height:66px; }
    .app-apk-btn{ display:block; width:100%; padding:15px; border-radius:99px; font-size:1.05rem; font-weight:800; color:#fff; text-decoration:none; background:linear-gradient(90deg,#16a34a,#22c55e); margin-top:12px; box-sizing:border-box; }
    .app-soon{ margin-top:12px; padding:13px; border:1px dashed var(--border-color); border-radius:12px; color:var(--warning); font-weight:700; }
    html[dir="rtl"] body{ text-align:right; }
    html[dir="rtl"] input, html[dir="rtl"] textarea{ text-align:right; }
</style>

<div class="pt2-fab">
    <button id="themeFab" title="Dark / Light mode" onclick="toggleTheme()">🌗</button>
    <button id="aiFab" title="AI Assistant" onclick="toggleAiDrawer()">🤖</button>
</div>

<div id="aiDrawer">
    <header>
        <div><strong style="font-size:1.05rem;">🤖 <span data-i18n="ai_title">PlayTube AI Assistant</span></strong><br>
        <small style="color:var(--text-sub);">Bol dein, AI khud download kar de ga — Roman Urdu / English</small></div>
        <button onclick="toggleAiDrawer()" style="background:none;border:none;color:var(--text-main);font-size:1.3rem;cursor:pointer;">✕</button>
    </header>
    <div id="aiLog">
        <div class="ai-msg bot">Assalam-o-Alaikum! 👋 Main PlayTube AI hoon. Misal likhein:
• "Pati Brahmachari episode 1 to 5, 360p me download kar do"
• "ye song mp3 320k me download karo"
• "drama download kar do, sab se chhoti quality me, 10 minute baad"
Downloads background me one by one chalte rahen ge.</div>
    </div>
    <div id="aiInputRow">
        <input id="aiInput" data-i18n-ph="ai_ph" placeholder="Type your command..." onkeydown="if(event.key==='Enter')sendAiCommand()">
        <button id="aiSend" data-i18n="send" onclick="sendAiCommand()">Send</button>
    </div>
</div>

<div id="formatsModal">
    <div class="fmt-sheet">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <h3>⬇️ <span data-i18n="more_formats">More Formats</span></h3>
            <button onclick="closeFormats()" style="background:none;border:none;color:var(--text-main);font-size:1.3rem;cursor:pointer;">✕</button>
        </div>
        <p id="formatsTitle" style="color:var(--text-sub); margin-top:6px;"></p>
        <div id="formatsList"><p style="padding:16px;">Formats load ho rahe hain...</p></div>
        <button class="fmt-dl-btn" onclick="downloadSelectedFormat()"><span data-i18n="download">Download</span></button>

        <div class="clip-box">
            <div class="fmt-group-title">✂️ <span data-i18n="clip_title">Clip Download</span></div>
            <p style="color:var(--text-sub); font-size:.9rem;" data-i18n="clip_hint">Download only part of the video — enter start &amp; end time (mm:ss or seconds). The format selected above will be used.</p>
            <div class="clip-row">
                <label><span data-i18n="clip_start">Start</span>
                    <input type="text" id="clipStart" placeholder="0:30" inputmode="numeric">
                </label>
                <label><span data-i18n="clip_end">End</span>
                    <input type="text" id="clipEnd" placeholder="1:45" inputmode="numeric">
                </label>
            </div>
            <button class="fmt-dl-btn clip-btn" onclick="downloadClip()">✂️ <span data-i18n="clip_download">Download Clip</span></button>
        </div>
    </div>
</div>

<script>
    // ---------- Theme (dark/light) ----------
    (function(){
        const saved = localStorage.getItem('pt_theme');
        if (saved) document.documentElement.setAttribute('data-theme', saved);
    })();
    function toggleTheme(){
        const cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', cur);
        localStorage.setItem('pt_theme', cur);
        showNotification(cur === 'light' ? '☀️ Light mode on' : '🌙 Dark mode on', 'success');
    }

    // ---------- PWA / Download App ----------
    let deferredInstallPrompt = null;
    window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferredInstallPrompt = e; });
    if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js').catch(()=>{}); }
    async function installPlayTubeApp(){
        if (deferredInstallPrompt) {
            deferredInstallPrompt.prompt();
            const choice = await deferredInstallPrompt.userChoice;
            showNotification(choice.outcome === 'accepted' ? '📲 App install ho raha hai!' : 'Install cancel ho gaya', 'success');
            deferredInstallPrompt = null;
        } else {
            showNotification(t('install_manual'), 'warning');
        }
    }

    // ---------- Sidebar extra items ----------
    window.addEventListener('DOMContentLoaded', () => {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            const appItem = document.createElement('a');
            appItem.className = 'nav-item';
            appItem.innerHTML = '<i class="fa-solid fa-mobile-screen"></i><span data-i18n="download_app"> Download App</span>';
            appItem.onclick = () => switchPage('app');
            sidebar.appendChild(appItem);
            const aiItem = document.createElement('a');
            aiItem.className = 'nav-item';
            aiItem.innerHTML = '<i class="fa-solid fa-robot"></i><span data-i18n="ai_assistant"> AI Assistant</span>';
            aiItem.onclick = toggleAiDrawer;
            sidebar.appendChild(aiItem);
            const favItem = document.createElement('a');
            favItem.className = 'nav-item';
            favItem.innerHTML = '<i class="fa-solid fa-star"></i><span data-i18n="favorites"> Favorites</span>';
            favItem.onclick = showFavorites;
            sidebar.appendChild(favItem);
        }
        // Smart Link Paste box on home page
        const home = document.getElementById('page-home');
        if (home && !document.getElementById('smartBox')) {
            const box = document.createElement('div');
            box.className = 'smart-box'; box.id = 'smartBox';
            box.innerHTML = '<input id="smartInput" data-i18n-ph="smart_ph" placeholder="🔗 Smart Link Paste — YouTube / Facebook / TikTok / Instagram link here...">' +
                            '<button onclick="handleSmartLink()">⚡ <span data-i18n="get_video">Get Video</span></button>';
            home.insertBefore(box, home.firstChild);
        }
    });

    async function handleSmartLink(){
        const url = document.getElementById('smartInput').value.trim();
        if (!url) { showNotification('Pehle link paste karein', 'warning'); return; }
        try {
            const res = await fetch('/api/smart-link', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})});
            const data = await res.json();
            if (data.type === 'youtube') { openFormats(data.video_id, ''); }
            else if (data.type === 'playlist') { downloadPlaylistWithRange(url); }
            else { switchPage('social'); const si = document.getElementById('socialUrl'); if (si) { si.value = url; } showNotification('Social link mil gaya — Fetch Info dabayein', 'success'); }
        } catch(e) { showNotification('Link check nahi ho saka', 'warning'); }
    }

    // ---------- Favorites (localStorage) ----------
    function getFavs(){ try { return JSON.parse(localStorage.getItem('pt_favs') || '[]'); } catch(e){ return []; } }
    function isFav(id){ return getFavs().some(f => f.id === id); }
    function toggleFav(id, title, channel, thumb){
        let favs = getFavs();
        if (isFav(id)) { favs = favs.filter(f => f.id !== id); showNotification('⭐ Favorites se hata diya', 'success'); }
        else { favs.push({id, title, channel, thumb}); showNotification('⭐ Favorites me save ho gaya', 'success'); }
        localStorage.setItem('pt_favs', JSON.stringify(favs));
        document.querySelectorAll(`[data-fav="${id}"]`).forEach(b => b.classList.toggle('faved', isFav(id)));
    }
    function showFavorites(){
        const favs = getFavs();
        if (!favs.length) { showNotification('Abhi koi favorite nahi — kisi video par ⭐ dabayein', 'warning'); return; }
        toggleAiDrawer(true);
        const log = document.getElementById('aiLog');
        favs.forEach(f => {
            const d = document.createElement('div');
            d.className = 'ai-msg bot';
            d.innerHTML = '⭐ <b></b><br>';
            d.querySelector('b').textContent = f.title;
            const b1 = document.createElement('button'); b1.textContent = '▶ Play'; b1.style.cssText = 'margin:6px 6px 0 0;padding:6px 12px;border:none;border-radius:8px;cursor:pointer;background:#4f46e5;color:#fff;';
            b1.onclick = () => playVideo(f.id, encodeURIComponent(f.title), '', encodeURIComponent(f.channel || ''));
            const b2 = document.createElement('button'); b2.textContent = '⬇ Formats'; b2.style.cssText = 'margin-top:6px;padding:6px 12px;border:none;border-radius:8px;cursor:pointer;background:#0d9488;color:#fff;';
            b2.onclick = () => openFormats(f.id, f.title);
            d.appendChild(b1); d.appendChild(b2);
            log.appendChild(d);
        });
        log.scrollTop = log.scrollHeight;
    }

    // ---------- Share ----------
    function shareVideo(id, title){
        const url = location.origin + '/?video=' + id;
        if (navigator.share) { navigator.share({title: title, url}).catch(()=>{}); return; }
        const txt = encodeURIComponent('🎬 ' + title + '\\n' + url);
        window.open('https://wa.me/?text=' + txt, '_blank');
    }

    // ---------- Video cards v2 (play on click + side Formats button + fav + share) ----------
    function renderVideos(items, container) {
        container.innerHTML = '';
        items.forEach(item => {
            const videoId = item.id.videoId || item.id;
            const title = item.snippet.title;
            const channel = item.snippet.channelTitle;
            const channelId = item.snippet.channelId;
            const thumb = item.snippet.thumbnails.high?.url || item.snippet.thumbnails.medium?.url || item.snippet.thumbnails.default?.url || ('https://i.ytimg.com/vi/' + videoId + '/hqdefault.jpg');
            const card = document.createElement('div');
            card.className = 'video-card';
            card.innerHTML = `
                <div class="thumbnail-box">
                    <input type="checkbox" class="select-checkbox" onchange="toggleSelect('${videoId}')">
                    ${thumb ? `<img src="${thumb}" alt="" onclick="playVideo('${videoId}', '${escapeHtml(title)}', '${channelId}', '${escapeHtml(channel)}')">` : '<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:#333;"><i class="fa-solid fa-video" style="font-size:3rem; color:#666;"></i></div>'}
                </div>
                <div class="card-details">
                    <div class="card-title" onclick="playVideo('${videoId}', '${escapeHtml(title)}', '${channelId}', '${escapeHtml(channel)}')">${escapeHtml(title)}</div>
                    <div class="card-channel" onclick="window.location.href='/channel/${channelId}';" style="cursor:pointer; color:var(--text-sub); font-size:0.8rem; text-decoration:underline;">${escapeHtml(channel)} ✓</div>
                    <div class="action-btns">
                        <button class="btn btn-play" title="Play" onclick="playVideo('${videoId}', '${escapeHtml(title)}', '${channelId}', '${escapeHtml(channel)}')"><i class="fa-solid fa-play"></i></button>
                        <button class="btn btn-download-mp4" title="More formats (sizes ke sath)" onclick="openFormats('${videoId}', '${escapeHtml(title)}')"><i class="fa-solid fa-download"></i> ${t('formats')}</button>
                        <button class="btn btn-download-mp3" onclick="downloadVideo('${videoId}', 'mp3', '${escapeHtml(title)}')"><i class="fa-solid fa-music"></i> MP3</button>
                        <button class="btn" title="Thumbnail" onclick="downloadThumbnail('${videoId}')"><i class="fa-solid fa-image"></i></button>
                        <button class="btn" title="Subtitles" onclick="downloadSubtitles('${videoId}')"><i class="fa-solid fa-closed-captioning"></i></button>
                        <button class="btn fav-btn ${isFav(videoId) ? 'faved' : ''}" data-fav="${videoId}" title="Favorite" onclick='toggleFav("${videoId}", ${JSON.stringify(title)}, ${JSON.stringify(channel)}, ${JSON.stringify(thumb)})'><i class="fa-solid fa-star"></i></button>
                        <button class="btn" title="Share" onclick='shareVideo("${videoId}", ${JSON.stringify(title)})'><i class="fa-solid fa-share-nodes"></i></button>
                    </div>
                </div>`;
            container.appendChild(card);
        });
    }

    // ---------- More Formats (Update 2) ----------
    let fmtVideoId = null, fmtTitle = '', fmtSelected = null;
    async function openFormats(videoId, title){
        if(!videoId || videoId === 'undefined' || videoId === 'null'){ showNotification('Video ID nahi mili — dobara try karein', 'error'); return; }
        fmtVideoId = videoId; fmtTitle = title || ''; fmtSelected = null;
        document.getElementById('formatsModal').classList.add('open');
        document.getElementById('formatsTitle').textContent = title || '';
        const list = document.getElementById('formatsList');
        list.innerHTML = '<p style="padding:16px;">Formats load ho rahe hain...</p>';
        try {
            const res = await fetch('/api/formats/' + videoId);
            const data = await res.json();
            if (data.error) { list.innerHTML = '<p style="padding:16px;">Formats nahi mil sake: ' + data.error + '</p>'; return; }
            if (!fmtTitle && data.title) { fmtTitle = data.title; document.getElementById('formatsTitle').textContent = data.title; }
            let html = '<div class="fmt-group-title">🎵 ' + t('music') + '</div>';
            data.music.forEach((f, i) => { html += fmtRow(f, 'm' + i); });
            html += '<div class="fmt-group-title">🎬 ' + t('video') + '</div>';
            data.video.forEach((f, i) => { html += fmtRow(f, 'v' + i); });
            list.innerHTML = html;
            const first = list.querySelector('.fmt-row'); if (first) first.click();
        } catch(e) { list.innerHTML = '<p style="padding:16px;">Network error — dobara try karein.</p>'; }
    }
    function fmtRow(f, key){
        const size = (f.size_mb === null || f.size_mb === undefined) ? '— MB' : f.size_mb + ' MB';
        return `<div class="fmt-row" data-key="${key}" onclick='selectFmt(this, ${JSON.stringify(f)})'>
                    <span>${f.format === 'mp4' ? '🎬' : '🎵'}</span>
                    <span class="grow"><b>${f.label}</b>${f.note ? '<br><small style="color:var(--text-sub);">' + f.note + '</small>' : ''}</span>
                    <span class="fmt-size">${size}</span>
                    <span class="fmt-tick">○</span>
                </div>`;
    }
    function selectFmt(el, f){
        fmtSelected = f;
        document.querySelectorAll('.fmt-row').forEach(r => { r.classList.remove('selected'); r.querySelector('.fmt-tick').textContent = '○'; });
        el.classList.add('selected'); el.querySelector('.fmt-tick').textContent = '✅';
    }
    function closeFormats(){ document.getElementById('formatsModal').classList.remove('open'); }
    function downloadSelectedFormat(){
        if (!fmtVideoId) return;
        if (!fmtSelected) { showNotification('Pehle ek format select karein', 'warning'); return; }
        closeFormats();
        downloadVideo(fmtVideoId, fmtSelected.format, fmtTitle, fmtSelected.quality);
    }
    // Old gear/quality button now opens the rich formats list
    function openQualityModal(videoId){ openFormats(videoId, ''); }

    // ---------- Playlist with range (Update 8) ----------
    function downloadPlaylistWithRange(url){
        const format = confirm('Click OK for MP3, Cancel for MP4') ? 'mp3' : 'mp4';
        const range = prompt('Range likhein (misal: 1-10) — khali chhodein to poori playlist:', '');
        let start_index = null, end_index = null;
        if (range) { const m = range.match(/(\d+)\s*-\s*(\d+)/); if (m) { start_index = +m[1]; end_index = +m[2]; } }
        fetch('/api/download-playlist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({playlist_url: url, format, start_index, end_index})})
            .then(r => r.json()).then(data => {
                if (data.success) { showNotification('Playlist download start!', 'success'); if (!progressInterval) progressInterval = setInterval(updateAllProgress, 1000); }
                else if (data.premium_required) { showNotification('⚡ Premium required!', 'warning'); openPremiumModal(); }
                else if (data.login_required) { showNotification('Pehle login karein', 'warning'); }
                else showNotification(data.error || 'Error', 'warning');
            }).catch(() => showNotification('Error', 'warning'));
    }
    function downloadPlaylist(){
        const url = prompt('Enter playlist URL:');
        if (!url) return;
        downloadPlaylistWithRange(url);
    }

    // ---------- AI Assistant ----------
    function toggleAiDrawer(forceOpen){
        const d = document.getElementById('aiDrawer');
        if (forceOpen === true) d.classList.add('open'); else d.classList.toggle('open');
    }
    function aiAddMsg(text, who){
        const log = document.getElementById('aiLog');
        const d = document.createElement('div');
        d.className = 'ai-msg ' + who;
        d.textContent = text;
        log.appendChild(d);
        log.scrollTop = log.scrollHeight;
        return d;
    }
    const aiJobPollers = {};
    async function sendAiCommand(){
        const input = document.getElementById('aiInput');
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        aiAddMsg(text, 'user');
        const wait = aiAddMsg('⏳ Soch raha hoon...', 'bot');
        try {
            const res = await fetch('/api/ai/command', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command: text})});
            const data = await res.json();
            wait.remove();
            if (data.message) aiAddMsg(data.message, 'bot');
            if (data.intent === 'search' && data.results) {
                data.results.slice(0, 8).forEach(r => {
                    const d = aiAddMsg('🎬 ' + r.title, 'bot');
                    const b = document.createElement('button');
                    b.textContent = '⬇ Formats'; b.style.cssText = 'display:block;margin-top:6px;padding:6px 12px;border:none;border-radius:8px;cursor:pointer;background:#0d9488;color:#fff;';
                    b.onclick = () => openFormats(r.video_id, r.title);
                    d.appendChild(b);
                });
            }
            if (data.intent === 'thumbnail' || data.intent === 'subtitles') {
                const d = aiAddMsg('👇 Link:', 'bot');
                const a = document.createElement('a'); a.href = data.url; a.textContent = data.url; a.style.color = '#2dd4bf';
                d.appendChild(a);
            }
            if (data.job_id) pollAiJob(data.job_id);
        } catch(e) { wait.textContent = '❌ Error — dobara try karein.'; }
    }
    function pollAiJob(jobId){
        if (aiJobPollers[jobId]) return;
        const box = aiAddMsg('📥 Job progress: 0%', 'bot');
        const bar = document.createElement('div'); bar.className = 'ai-jobbar';
        const fill = document.createElement('div'); bar.appendChild(fill); box.appendChild(bar);
        aiJobPollers[jobId] = setInterval(async () => {
            try {
                const res = await fetch('/api/ai/jobs/' + jobId);
                const data = await res.json();
                if (!data.job) return;
                const job = data.job;
                const total = job.total_count || 1;
                const doneCount = (job.episodes_status || []).filter(e => e.status === 'completed' || e.status === 'failed').length;
                const pct = Math.round((doneCount / total) * 100);
                fill.style.width = pct + '%';
                box.firstChild.textContent = `📥 ${job.status} — ${doneCount}/${total} episodes complete (${pct}%) `;
                if (['completed', 'partial', 'failed'].includes(job.status)) {
                    clearInterval(aiJobPollers[jobId]); delete aiJobPollers[jobId];
                    const lines = (job.episodes_status || []).map(e => `${e.status === 'completed' ? '✅' : '❌'} Episode ${e.episode ?? ''}: ${e.title || e.query || ''}${e.error ? ' — ' + e.error : ''}`).join('\\n');
                    aiAddMsg((job.status === 'completed' ? '🎉 Sab downloads complete!\\n' : '⚠️ Job khatam (' + job.status + ')\\n') + lines + '\\nFiles Downloads page par milenge.', 'bot');
                }
            } catch(e) {}
        }, 3000);
    }

    // ---------- Clip Download (v3) ----------
    function parseClipTime(v){
        v = String(v || '').trim();
        if (!v) return null;
        if (/^\d+(\.\d+)?$/.test(v)) return parseFloat(v);
        const parts = v.split(':').map(Number);
        if (!parts.length || parts.length > 3 || parts.some(isNaN)) return null;
        return parts.reduce((acc, n) => acc * 60 + n, 0);
    }
    function downloadClip(){
        if (!fmtVideoId) return;
        const s = parseClipTime(document.getElementById('clipStart').value);
        const e = parseClipTime(document.getElementById('clipEnd').value);
        if (s === null || e === null || e <= s) { showNotification(t('clip_invalid'), 'warning'); return; }
        const fmt = fmtSelected || {format: 'mp4', quality: '360p'};
        const vid = fmtVideoId, ttl = fmtTitle;
        closeFormats();
        const downloadId = `${vid}_clip_${Date.now()}`;
        addDownloadProgress(downloadId, vid, fmt.format, (fmt.quality || 'best') + ' clip ' + Math.round(s) + 's-' + Math.round(e) + 's');
        fetch('/api/start-download', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({video_id: vid, format: fmt.format, quality: fmt.quality, download_id: downloadId, clip_start: s, clip_end: e})
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                updateDownloadStatus(downloadId, 'error', data.error);
                if (data.login_required) openAuthModal('login');
                if (data.premium_required) openPremiumModal();
            } else showNotification(t('clip_started'), 'success');
        })
        .catch(err => updateDownloadStatus(downloadId, 'error', err.message));
        if (!progressInterval) progressInterval = setInterval(updateAllProgress, 1000);
    }

    // ---------- Download App: PC install (v3) ----------
    async function installPlayTubeAppPC(){
        if (deferredInstallPrompt) {
            deferredInstallPrompt.prompt();
            const choice = await deferredInstallPrompt.userChoice;
            showNotification(choice.outcome === 'accepted' ? '💻 PlayTube PC par install ho raha hai!' : 'Install cancel ho gaya', 'success');
            deferredInstallPrompt = null;
        } else {
            showNotification(t('pc_manual'), 'warning');
        }
    }

    // ---------- Download App: APK availability (v3) ----------
    async function checkApkStatus(){
        try {
            const res = await fetch('/api/apk-status');
            const data = await res.json();
            const btn = document.getElementById('apkDownloadBtn');
            const note = document.getElementById('apkSoonNote');
            if (data.available) { if (btn) btn.style.display = 'block'; if (note) note.style.display = 'none'; }
            else { if (btn) btn.style.display = 'none'; if (note) note.style.display = 'block'; }
        } catch(e) {}
    }
    window.addEventListener('DOMContentLoaded', checkApkStatus);

    // ---------- Language switch EN / اردو (v3) ----------
    const I18N = {"en": {"main_section": "Main", "library": "Library", "home": " Home", "social_download": " Social Download", "trending": " Trending", "music": " Music", "gaming": " Gaming", "news": " News", "playlist_download": " Playlist Download", "history": " History", "downloads": " Downloads", "open_folder": " Open Folder", "stats": " Stats", "go_premium": " Go Premium", "share_app": " Share App", "download_app": " Download App", "ai_assistant": " AI Assistant", "favorites": " Favorites", "search_ph": "Search YouTube...", "batch_download": "Batch Download", "login": "Login", "signup": "Sign Up", "logout": "Logout", "recommended": "Recommended", "premium_banner_sub": "Unlimited Downloads | HD Quality | No Ads", "upgrade_now": "Upgrade Now", "social_title": "All Social Media Downloader", "social_ph": "Paste any video URL (YouTube, Facebook, Instagram, TikTok, Twitter, etc.)", "fetch_info": "Fetch Info", "select_platform": "Select Platform", "dl_video_mp4": "Download Video (MP4)", "dl_audio_mp3": "Download Audio (MP3)", "watch_history": "Watch History", "back": "Back", "quality": "Quality", "thumbnail": "Thumbnail", "subtitles": "Subtitles", "info": "Info", "clip": "Clip", "select_quality": "Select Quality", "cancel": "Cancel", "email_or_username": "Email or Username", "password": "Password", "enter_email_ph": "Enter email or username", "enter_password_ph": "Enter password", "create_password_ph": "Create password", "no_account": "Don't have an account?", "have_account": "Already have an account?", "username": "Username", "choose_username_ph": "Choose username", "email": "Email", "enter_email2_ph": "Enter email", "privacy": "Privacy Policy", "terms": "Terms of Service", "about": "About", "contact": "Contact", "more_formats": "More Formats", "download": "Download", "formats": "Formats", "video": "Video", "clip_title": "Clip Download", "clip_hint": "Download only part of the video — enter start & end time (mm:ss or seconds). The format selected above will be used.", "clip_start": "Start", "clip_end": "End", "clip_download": "Download Clip", "clip_invalid": "Please enter a valid start and end time (end must be after start).", "clip_started": "✂️ Clip download started!", "app_page_title": "Download PlayTube App", "android_title": "Android App", "android_desc": "Install PlayTube on your Android phone: home-screen icon, full-screen app, all downloads + AI features.", "android_install": "Install App (PWA)", "android_apk": "Download APK", "apk_soon": "APK coming soon after launch", "pc_title": "PC (Windows) App", "pc_desc": "Install PlayTube on your PC: it adds a desktop icon and opens in its own window, just like a real Windows app (Chrome / Edge).", "pc_install": "Install for PC", "pc_manual": "💻 To install on PC: open the Chrome/Edge menu (⋮) and choose \\"Install PlayTube\\" — a desktop icon will be created and the app opens in its own window.", "install_manual": "📲 To install: open the browser menu (⋮) and tap \\"Install app / Add to Home screen\\".", "smart_ph": "🔗 Smart Link Paste — paste a YouTube / Facebook / TikTok / Instagram link here...", "get_video": "Get Video", "ai_title": "PlayTube AI Assistant", "ai_ph": "Type your command...", "send": "Send"}, "ur": {"main_section": "مین", "library": "لائبریری", "home": " ہوم", "social_download": " سوشل ڈاؤن لوڈ", "trending": " ٹرینڈنگ", "music": " موسیقی", "gaming": " گیمنگ", "news": " خبریں", "playlist_download": " پلے لسٹ ڈاؤن لوڈ", "history": " ہسٹری", "downloads": " ڈاؤن لوڈز", "open_folder": " فولڈر کھولیں", "stats": " اعداد و شمار", "go_premium": " پریمیم لیں", "share_app": " ایپ شیئر کریں", "download_app": " ایپ ڈاؤن لوڈ کریں", "ai_assistant": " AI اسسٹنٹ", "favorites": " پسندیدہ", "search_ph": "یوٹیوب تلاش کریں...", "batch_download": "بیچ ڈاؤن لوڈ", "login": "لاگ ان", "signup": "سائن اپ", "logout": "لاگ آؤٹ", "recommended": "تجویز کردہ", "premium_banner_sub": "لامحدود ڈاؤن لوڈز | HD کوالٹی | کوئی اشتہار نہیں", "upgrade_now": "ابھی اپ گریڈ کریں", "social_title": "آل سوشل میڈیا ڈاؤن لوڈر", "social_ph": "کوئی بھی ویڈیو لنک یہاں لگائیں (یوٹیوب، فیس بک، انسٹاگرام، ٹک ٹاک، ٹوئٹر وغیرہ)", "fetch_info": "معلومات لائیں", "select_platform": "پلیٹ فارم منتخب کریں", "dl_video_mp4": "ویڈیو ڈاؤن لوڈ کریں (MP4)", "dl_audio_mp3": "آڈیو ڈاؤن لوڈ کریں (MP3)", "watch_history": "دیکھی گئی ہسٹری", "back": "واپس", "quality": "کوالٹی", "thumbnail": "تھمب نیل", "subtitles": "سب ٹائٹلز", "info": "معلومات", "clip": "کلپ", "select_quality": "کوالٹی منتخب کریں", "cancel": "منسوخ", "email_or_username": "ای میل یا یوزر نیم", "password": "پاس ورڈ", "enter_email_ph": "ای میل یا یوزر نیم لکھیں", "enter_password_ph": "پاس ورڈ لکھیں", "create_password_ph": "پاس ورڈ بنائیں", "no_account": "اکاؤنٹ نہیں ہے؟", "have_account": "پہلے سے اکاؤنٹ ہے؟", "username": "یوزر نیم", "choose_username_ph": "یوزر نیم منتخب کریں", "email": "ای میل", "enter_email2_ph": "ای میل لکھیں", "privacy": "پرائیویسی پالیسی", "terms": "شرائط و ضوابط", "about": "ہمارے بارے میں", "contact": "رابطہ", "more_formats": "مزید فارمیٹس", "download": "ڈاؤن لوڈ", "formats": "فارمیٹس", "video": "ویڈیو", "clip_title": "کلپ ڈاؤن لوڈ", "clip_hint": "ویڈیو کا صرف ایک حصہ ڈاؤن لوڈ کریں — شروع اور آخر کا وقت لکھیں (mm:ss یا سیکنڈز)۔ اوپر منتخب فارمیٹ استعمال ہوگا۔", "clip_start": "شروع", "clip_end": "آخر", "clip_download": "کلپ ڈاؤن لوڈ کریں", "clip_invalid": "درست شروع اور آخر کا وقت لکھیں (آخر، شروع کے بعد ہونا چاہیے)۔", "clip_started": "✂️ کلپ ڈاؤن لوڈ شروع ہو گیا!", "app_page_title": "PlayTube ایپ ڈاؤن لوڈ کریں", "android_title": "اینڈرائیڈ ایپ", "android_desc": "اپنے اینڈرائیڈ فون پر PlayTube انسٹال کریں: ہوم اسکرین آئیکن، فل اسکرین ایپ، تمام ڈاؤن لوڈز + AI فیچرز۔", "android_install": "ایپ انسٹال کریں (PWA)", "android_apk": "APK ڈاؤن لوڈ کریں", "apk_soon": "APK لانچ کے بعد جلد آ رہا ہے", "pc_title": "پی سی (ونڈوز) ایپ", "pc_desc": "اپنے پی سی پر PlayTube انسٹال کریں: ڈیسک ٹاپ پر آئیکن بن جائے گا اور ایپ اپنی الگ ونڈو میں کھلے گی — بالکل اصلی ونڈوز ایپ کی طرح (Chrome / Edge)۔", "pc_install": "پی سی کے لیے انسٹال کریں", "pc_manual": "💻 پی سی پر انسٹال: Chrome/Edge مینو (⋮) سے \\"Install PlayTube\\" دبائیں — ڈیسک ٹاپ پر آئیکن بن جائے گا اور ایپ اپنی ونڈو میں کھلے گی۔", "install_manual": "📲 انسٹال کرنے کے لیے: براؤزر مینو (⋮) کھول کر \\"Install app / Add to Home screen\\" دبائیں۔", "smart_ph": "🔗 سمارٹ لنک — یوٹیوب / فیس بک / ٹک ٹاک / انسٹاگرام کا لنک یہاں لگائیں...", "get_video": "ویڈیو لائیں", "ai_title": "PlayTube AI اسسٹنٹ", "ai_ph": "اپنا کمانڈ لکھیں...", "send": "بھیجیں"}};
    let ptLang = 'en';
    try { ptLang = localStorage.getItem('pt_lang') || 'en'; } catch(e) {}
    if (ptLang !== 'ur') ptLang = 'en';
    function t(key){ return (I18N[ptLang] && I18N[ptLang][key]) || I18N.en[key] || key; }
    function applyLang(){
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const v = t(el.getAttribute('data-i18n'));
            if (v) el.textContent = v;
        });
        document.querySelectorAll('[data-i18n-ph]').forEach(el => {
            const v = t(el.getAttribute('data-i18n-ph'));
            if (v) el.setAttribute('placeholder', v);
        });
        document.documentElement.lang = ptLang === 'ur' ? 'ur' : 'en';
        document.documentElement.dir = ptLang === 'ur' ? 'rtl' : 'ltr';
        const btn = document.getElementById('langToggleBtn');
        if (btn) btn.textContent = ptLang === 'ur' ? 'English' : 'اردو';
    }
    function toggleLang(){
        ptLang = ptLang === 'ur' ? 'en' : 'ur';
        try { localStorage.setItem('pt_lang', ptLang); } catch(e) {}
        applyLang();
        showNotification(ptLang === 'ur' ? '🌐 زبان اردو کر دی گئی' : '🌐 Language set to English', 'success');
    }
    window.addEventListener('DOMContentLoaded', applyLang);
</script>
<!-- ================= /PLAYTUBE v3 PREMIUM LAYER ================= -->

<!-- ==================== PLAYTUBE v4 UI LAYER ==================== -->
<style id="v4-css">
  .app-container{display:none!important}
  #formatsModal,#aiDrawer{display:none!important}
  html,body{overflow-x:hidden!important;max-width:100%}
  #v4app{
    --v4bg:#12101f; --v4card:#1a1730; --v4border:#2c2852; --v4violet:#7c5cff;
    --v4violet2:#8b6dff; --v4teal:#14b8a6; --v4text:#eceaf6; --v4muted:#a49ec4;
    --v4nav:#17142c; --v4danger:#f87171;
    background:var(--v4bg); color:var(--v4text); min-height:100vh;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  }
  html[data-theme="light"] #v4app{
    --v4bg:#f4f2fa; --v4card:#ffffff; --v4border:#ddd8f0; --v4text:#1c1a2e;
    --v4muted:#5d5878; --v4nav:#ffffff;
  }
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
  .v4-h{font-size:15px;font-weight:800;margin:8px 2px 10px}
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
  .v4-wrap{position:fixed;inset:0;z-index:200;display:none}
  .v4-wrap.open{display:block}
  .v4-overlay{position:absolute;inset:0;background:rgba(4,2,16,.72)}
  .v4-sheet{position:absolute;left:0;right:0;bottom:0;max-height:84vh;overflow-y:auto;background:var(--v4bg);border-radius:18px 18px 0 0;padding:14px 16px 18px;max-width:560px;margin:0 auto;border:1px solid var(--v4border)}
  .v4-modalpanel{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:92%;max-width:420px;max-height:88vh;overflow-y:auto;background:var(--v4bg);border:1px solid var(--v4border);border-radius:16px;padding:18px 16px}
  .v4-fmtrow{display:flex;align-items:center;gap:8px;padding:11px 6px;border-bottom:1px solid var(--v4border);cursor:pointer;border-radius:8px}
  .v4-fmtrow.sel{background:rgba(124,92,255,.10)}
  .v4-fmtrow .nm{flex:1;font-size:13.5px}
  .v4-fmtrow .sz{font-size:12px;color:var(--v4muted)}
  .v4-radio{width:17px;height:17px;border-radius:50%;border:2px solid var(--v4muted);flex:none;display:inline-flex;align-items:center;justify-content:center;font-size:10px;color:#06231f}
  .v4-fmtrow.sel .v4-radio{background:var(--v4teal);border-color:var(--v4teal)}
  .v4-sect{font-size:11px;font-weight:700;color:var(--v4violet2);letter-spacing:.6px;margin:14px 0 2px}
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
  .v4-dlrow img{width:64px;height:40px;object-fit:cover;border-radius:8px;flex:none;background:#26224a}
  .v4-dlrow .tt{flex:1;min-width:0}
  .v4-dlrow .t1{font-size:12.5px;font-weight:600}
  .v4-dlrow .t2{font-size:10.5px;color:var(--v4muted);margin-top:2px}
  .v4-bar{height:5px;border-radius:3px;background:var(--v4border);margin-top:6px}
  .v4-bar i{display:block;height:5px;border-radius:3px;background:linear-gradient(90deg,var(--v4violet),var(--v4teal))}
  .v4-roundbtn{flex:none;width:34px;height:34px;border-radius:50%;border:2px solid var(--v4violet);background:none;color:var(--v4text);display:inline-flex;align-items:center;justify-content:center;font-size:12px;cursor:pointer;text-decoration:none}
  .v4-roundbtn.teal{background:var(--v4teal);border-color:var(--v4teal);color:#06231f}
  /* tools / profile / admin rows */
  .v4-tools{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .v4-tool{background:var(--v4card);border:1px solid var(--v4border);border-radius:14px;padding:16px 12px;cursor:pointer}
  .v4-tool .ic{font-size:22px}
  .v4-tool .tn{font-size:13px;font-weight:600;margin-top:8px}
  .v4-tool .td{font-size:10.5px;color:var(--v4muted);margin-top:2px}
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
</style>

<div id="v4app">
  <div class="v4-head">
    <div class="v4-logo">PlayTube</div>
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
      <div class="v4-h" id="v4-home-heading">Trending Videos</div>
      <div id="v4-home-feed" class="v4-feedgrid"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-youtube" class="v4-view">
      <form class="v4-searchrow" onsubmit="v4FeedSearch(event,'youtube')">
        <input id="v4-q-youtube" placeholder="YouTube par search karein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit"><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>
      <div class="v4-h">YouTube Videos</div>
      <div id="v4-youtube-feed" class="v4-feedgrid"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-music" class="v4-view">
      <form class="v4-searchrow" onsubmit="v4FeedSearch(event,'music')">
        <input id="v4-q-music" placeholder="Gana / naat / song search karein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit"><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>
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
      <div class="v4-plats" id="v4-plat-list"></div>
    </section>

    <section id="v4-view-more" class="v4-view">
      <div class="v4-h">More</div>
      <div class="v4-row" onclick="v4Show('app')"><span>📱</span><div class="grow">Download App (Android / PC)</div><span>›</span></div>
      <div class="v4-row" onclick="v4Show('premium')"><span>👑</span><div class="grow">Premium</div><span>›</span></div>
      <div class="v4-row" onclick="v4Show('favorites')"><span>⭐</span><div class="grow">Favorites</div><span>›</span></div>
      <div class="v4-row" onclick="v4Show('history')"><span>🕘</span><div class="grow">Watch History</div><span>›</span></div>
      <div class="v4-row" onclick="window.location.href='/about'"><span>ℹ️</span><div class="grow">About PlayTube</div><span>›</span></div>
      <div class="v4-row" onclick="window.location.href='/contact'"><span>✉️</span><div class="grow">Contact</div><span>›</span></div>
    </section>

    <section id="v4-view-watch" class="v4-view">
      <button class="v4-btn2" onclick="v4Back()">← Back</button>
      <div style="margin-top:10px;border-radius:14px;overflow:hidden;aspect-ratio:16/9;background:#000">
        <iframe id="v4-player" width="100%" height="100%" frameborder="0" allowfullscreen allow="autoplay; encrypted-media" title="PlayTube player"></iframe>
      </div>
      <div class="v4-h" id="v4-watch-title" style="margin-top:12px"></div>
      <p class="v4-muted" id="v4-watch-channel"></p>
      <button class="v4-bigbtn" style="background:var(--v4teal);color:#06231f" onclick="v4WatchDownload()">⬇ Download</button>
      <div class="v4-h" style="margin-top:18px">Related Videos</div>
      <div id="v4-related" class="v4-feedgrid"></div>
    </section>

    <section id="v4-view-downloads" class="v4-view">
      <div style="display:flex;align-items:center;gap:8px">
        <div class="v4-h" style="flex:1;margin:4px 2px">Downloads</div>
        <button class="v4-iconbtn" onclick="v4DeleteAll()" title="Saare downloads delete karein">🗑 Sab delete</button>
      </div>
      <div class="v4-searchrow" style="margin-top:6px">
        <input id="v4-dl-filter" placeholder="Downloads me dhundein..." oninput="v4RenderDownloads()" autocomplete="off">
        <button class="v4-searchbtn" type="button"><i class="fa-solid fa-magnifying-glass"></i></button>
      </div>
      <div class="v4-sect">DOWNLOADING</div>
      <div id="v4-dl-active"><p class="v4-muted">Koi download nahi chal raha</p></div>
      <div class="v4-sect">DOWNLOADED</div>
      <div id="v4-dl-done"><p class="v4-muted">Abhi tak koi download nahi</p></div>
    </section>

    <section id="v4-view-ai" class="v4-view">
      <div class="v4-h">✦ AI Assistant</div>
      <div class="v4-chips">
        <button class="v4-chip" onclick="v4AiChip(this)">Motu Patlu episode 1, 3GP download karo</button>
        <button class="v4-chip" onclick="v4AiChip(this)">Naat sharif MP3 320K me download karo</button>
        <button class="v4-chip" onclick="v4AiChip(this)">Drama episode 1 to 3, 360p download karo</button>
        <button class="v4-chip" onclick="v4AiChip(this)">Sab se chhoti quality me gana download karo</button>
      </div>
      <div id="v4-ai-msgs">
        <div class="v4-bubble ai">Assalam-o-Alaikum! Main PlayTube AI hoon. Bas command likhein — masalan kisi drama ke episodes, gana, ya quality bata kar download karwayein. Downloads background me one by one chalte rahen ge, aur tayyar videos Downloads me milen ge.</div>
      </div>
      <form class="v4-airow" onsubmit="v4AiSend(event)">
        <input id="v4-ai-input" placeholder="AI ko command likhein..." autocomplete="off">
        <button class="v4-searchbtn" type="submit">➤</button>
      </form>
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
      </div>
    </section>

    <section id="v4-view-settings" class="v4-view">
      <button class="v4-btn2" onclick="v4Show('tools')">← Tools</button>
      <div class="v4-h" style="margin-top:10px">Settings</div>
      <div class="v4-sect">DOWNLOAD</div>
      <div class="v4-row"><div class="grow">Download folder<div class="v4-muted">Phone me is naam ke folder me jayengi (app me)</div></div><input id="v4-set-folder" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"></div>
      <div class="v4-row"><div class="grow">Default quality</div><select id="v4-set-quality" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"><option>144p</option><option>240p</option><option>360p</option><option>480p</option><option>720p</option><option>3gp</option></select></div>
      <div class="v4-row"><div class="grow">Ek sath downloads</div><select id="v4-set-conc" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"><option>1</option><option>2</option><option>3</option><option>5</option></select></div>
      <div class="v4-row"><div class="grow">Speed limit</div><select id="v4-set-speed" class="v4-input" style="width:130px;margin:0" onchange="v4SaveSettings()"><option>Unlimited</option><option>1 MB/s</option><option>2 MB/s</option><option>5 MB/s</option></select></div>
      <div class="v4-row"><div class="grow">Sirf Wi-Fi par download</div><button class="v4-switch" id="v4-set-wifi" onclick="v4ToggleSetting('wifiOnly',this)"><i></i></button></div>
      <div class="v4-sect">APP</div>
      <div class="v4-row"><div class="grow">Language</div><span class="val" id="v4-set-lang">English</span><button class="v4-btn2" onclick="v4ToggleLang()">Badlein</button></div>
      <div class="v4-row"><div class="grow">Theme</div><span class="val" id="v4-set-theme">Dark</span><button class="v4-btn2" onclick="v4ToggleTheme()">Badlein</button></div>
      <div class="v4-row"><div class="grow">Download mukammal ho to batao<div class="v4-muted">Notification ke liye</div></div><button class="v4-switch" id="v4-set-notify" onclick="v4ToggleSetting('notify',this)"><i></i></button></div>
      <div class="v4-row" id="v4-set-floating-row" style="display:none"><div class="grow">Floating Button (sirf APK app me)<div class="v4-muted" id="v4-set-floating-note">Dusri apps ke upar PlayTube bubble - tap karne par clipboard link ka download page khulta hai</div></div><button class="v4-switch" id="v4-set-floating" onclick="v4ToggleFloating(this)"><i></i></button></div>
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
      <div class="v4-h">👑 PlayTube Premium</div>
      <div id="v4-premium-body"><p class="v4-muted">Load ho raha hai...</p></div>
    </section>

    <section id="v4-view-app" class="v4-view">
      <div class="v4-h">Download PlayTube App</div>
      <div class="v4-vcard" style="padding:16px">
        <div style="font-size:28px">📱</div>
        <div class="v4-h" style="margin:8px 0 4px">Android App</div>
        <p class="v4-muted">PlayTube ko phone ki home screen par app ki tarah lagayein — full-screen, saare features ke sath.</p>
        <button class="v4-bigbtn" onclick="v4InstallPWA()">Install App (PWA)</button>
        <div id="v4-apk-area" style="margin-top:10px"><p class="v4-muted">APK check ho raha hai...</p></div>
      </div>
      <div class="v4-vcard" style="padding:16px">
        <div style="font-size:28px">💻</div>
        <div class="v4-h" style="margin:8px 0 4px">PC (Windows) App</div>
        <p class="v4-muted">PC par PlayTube install karein — desktop icon banega aur apni window me khule ga (Chrome / Edge).</p>
        <button class="v4-bigbtn" onclick="v4InstallPC()">Install for PC</button>
      </div>
    </section>
  </main>

  <nav id="v4-bottomnav">
    <button data-bn="home" class="active" onclick="v4Show('home')"><i class="fa-solid fa-house"></i>Home</button>
    <button data-bn="downloads" onclick="v4Show('downloads')"><i class="fa-solid fa-download"></i>Downloads<span class="v4-badge" id="v4-dl-badge">0</span></button>
    <button data-bn="ai" id="v4-bn-ai" onclick="v4Show('ai')"><i class="fa-solid fa-robot"></i>AI Assistant</button>
    <button data-bn="tools" onclick="v4Show('tools')"><i class="fa-solid fa-screwdriver-wrench"></i>Tools</button>
    <button data-bn="profile" onclick="v4Show('profile')"><i class="fa-solid fa-user"></i>Profile</button>
  </nav>
</div>

<!-- Download sheet -->
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

<!-- Auth modal (Update 21) -->
<div id="v4-authwrap" class="v4-wrap">
  <div class="v4-overlay" onclick="v4CloseAuth()"></div>
  <div class="v4-modalpanel">
    <div style="display:flex;align-items:center">
      <div class="v4-h" style="flex:1;margin:0" id="v4-auth-heading">Welcome to PlayTube</div>
      <button class="v4-iconbtn" onclick="v4CloseAuth()">✕</button>
    </div>
    <p class="v4-muted" style="margin:6px 0 12px">Video dekhne aur download karne ke liye pehle account banayein ya sign in karein.</p>
    <div id="v4-auth-msg" class="v4-msg"></div>
    <div class="v4-authtabs">
      <button id="v4-tab-signin" class="active" onclick="v4AuthTab('signin')">Sign In</button>
      <button id="v4-tab-signup" onclick="v4AuthTab('signup')">Create Account</button>
    </div>

    <form id="v4-form-signin" onsubmit="v4SignIn(event)">
      <input class="v4-input" id="v4-li-email" placeholder="Email ya username" autocomplete="username">
      <input class="v4-input" id="v4-li-pass" type="password" placeholder="Password" autocomplete="current-password">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Sign In</button>
      <p style="text-align:center;margin-top:10px"><a href="#" onclick="v4ShowForgot(event)" style="color:var(--v4violet2);font-size:12.5px">Password bhool gaye?</a></p>
    </form>

    <form id="v4-form-signup" style="display:none" onsubmit="v4SignUpStart(event)">
      <input class="v4-input" id="v4-su-name" placeholder="Username" autocomplete="username">
      <input class="v4-input" id="v4-su-email" placeholder="Gmail (email)" autocomplete="email">
      <input class="v4-input" id="v4-su-pass" type="password" placeholder="Password (kam se kam 6)" autocomplete="new-password">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Gmail par Code Bhejein</button>
    </form>
    <form id="v4-form-verify" style="display:none" onsubmit="v4SignUpVerify(event)">
      <p class="v4-muted" id="v4-verify-note">Aap ki Gmail par 6-digit code bheja gaya hai — neeche darj karein.</p>
      <input class="v4-input" id="v4-su-code" placeholder="6-digit code" inputmode="numeric" autocomplete="one-time-code">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Verify &amp; Create Account</button>
    </form>

    <form id="v4-form-forgot" style="display:none" onsubmit="v4ForgotStart(event)">
      <p class="v4-muted">Apni Gmail likhein — password reset code bheja jaye ga.</p>
      <input class="v4-input" id="v4-fg-email" placeholder="Gmail (email)" autocomplete="email">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Code Bhejein</button>
    </form>
    <form id="v4-form-reset" style="display:none" onsubmit="v4ForgotReset(event)">
      <input class="v4-input" id="v4-fg-code" placeholder="6-digit code" inputmode="numeric" autocomplete="one-time-code">
      <input class="v4-input" id="v4-fg-pass" type="password" placeholder="Naya password (kam se kam 6)" autocomplete="new-password">
      <button class="v4-bigbtn" type="submit" style="margin-top:2px">Password Badlein</button>
    </form>
  </div>
</div>

<div id="v4-toast"></div>

<script id="v4-js">
/* ================= PlayTube v4 UI logic ================= */
const v4State = {user:null, config:null, view:'home',
  settings:{folder:'PlayTube', defQuality:'360p', maxConc:3, speed:'Unlimited', wifiOnly:false, notify:true},
  loadedYt:0, loadedMu:0, platsDone:0};
try{ const _s = JSON.parse(localStorage.getItem('pt_v4_settings') || 'null'); if(_s) v4State.settings = Object.assign(v4State.settings, _s); }catch(e){}
const v4Videos = {};
let v4Pending = null, v4SignupEmail = '', v4Current = null, v4PrevView = 'home';
let v4DlData = {progress:{}, list:[]};
let v4Sheet = {id:null, sel:null};
let v4SocialInfo = null;
const v4JobTimers = {};

function v4$(id){ return document.getElementById(id); }
function v4Esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
async function v4Fetch(url, opts){ const r = await fetch(url, opts || {}); let d = null; try{ d = await r.json(); }catch(e){} return {ok:r.ok, status:r.status, data:d}; }
function v4Post(url, body){ return v4Fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body || {})}); }
function v4Toast(msg){ const t = v4$('v4-toast'); t.textContent = msg; t.style.display = 'block'; clearTimeout(t._h); t._h = setTimeout(function(){ t.style.display = 'none'; }, 3400); }
function v4Dur(s){ if(!s) return ''; s = parseInt(s); if(!s) return ''; const m = Math.floor(s/60), ss = s % 60, h = Math.floor(m/60); if(h) return h + ':' + String(m%60).padStart(2,'0') + ':' + String(ss).padStart(2,'0'); return m + ':' + String(ss).padStart(2,'0'); }
function v4Views(n){ if(!n) return ''; n = parseInt(n); if(!n) return ''; if(n >= 1000000) return (n/1000000).toFixed(1).replace('.0','') + 'M views'; if(n >= 1000) return (n/1000).toFixed(1).replace('.0','') + 'K views'; return n + ' views'; }
function v4MB(b){ if(!b) return ''; return (b/(1024*1024)).toFixed(1) + ' MB'; }
function v4Img(id){ return '<img loading="lazy" src="https://i.ytimg.com/vi/' + id + '/hqdefault.jpg" data-vid="' + id + '" data-stage="0" onerror="v4ImgFb(this)" alt="">'; }
function v4ImgFb(img){ const id = img.getAttribute('data-vid'); const st = parseInt(img.getAttribute('data-stage') || '0'); if(st === 0){ img.setAttribute('data-stage','1'); img.src = 'https://i.ytimg.com/vi/' + id + '/mqdefault.jpg'; } else if(st === 1){ img.setAttribute('data-stage','2'); img.src = 'https://i.ytimg.com/vi/' + id + '/default.jpg'; } else { img.onerror = null; img.style.opacity = '0.25'; } }

/* ---------- navigation ---------- */
const V4_TTMAP = {home:'search', youtube:'youtube', music:'music', social:'social', more:'more'};
const V4_BNMAP = {home:'home', watch:'home', downloads:'downloads', ai:'ai', tools:'tools', settings:'tools', favorites:'tools', history:'tools', premium:'tools', app:'tools', profile:'profile', admin:'profile'};
function v4Show(view){
  document.querySelectorAll('.v4-view').forEach(function(s){ s.classList.remove('active'); });
  const el = v4$('v4-view-' + view); if(el) el.classList.add('active');
  v4State.view = view;
  document.querySelectorAll('#v4-toptabs button').forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-tt') === (V4_TTMAP[view] || '')); });
  document.querySelectorAll('#v4-bottomnav button').forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-bn') === (V4_BNMAP[view] || '')); });
  window.scrollTo(0, 0);
  if(view === 'downloads') v4LoadDownloads();
  if(view === 'profile') v4RenderProfile();
  if(view === 'admin') v4RenderAdmin();
  if(view === 'favorites') v4RenderFavs();
  if(view === 'history') v4LoadHistory();
  if(view === 'premium') v4RenderPremium();
  if(view === 'app') v4CheckApk();
  if(view === 'settings') v4FillSettings();
  if(view === 'youtube' && !v4State.loadedYt){ v4State.loadedYt = 1; v4LoadFeed('v4-youtube-feed', 'trending videos'); }
  if(view === 'music' && !v4State.loadedMu){ v4State.loadedMu = 1; v4LoadFeed('v4-music-feed', 'new songs'); }
  if((view === 'social' || view === 'more') && !v4State.platsDone) v4RenderPlats();
}
function v4TopTab(t){ v4Show(t === 'search' ? 'home' : t); }

/* ---------- feeds & cards (ONE renderer — Bug #1/#2) ---------- */
function v4Norm(item){ const id = (item.id && item.id.videoId) || item.id || item.video_id || ''; const sn = item.snippet || {}; return {videoId:id, title:sn.title || item.title || '', channel:sn.channelTitle || item.channel || '', duration:item.duration || '', views:item.view_count || ''}; }
function v4CardHTML(v){
  const meta = [v4Esc(v.channel), v4Views(v.views)].filter(Boolean).join(' • ');
  return '<div class="v4-vcard"><div class="v4-thumb" data-id="' + v.videoId + '" onclick="v4WatchClick(this.dataset.id)">' + v4Img(v.videoId) + (v.duration ? '<span class="v4-dur">' + v4Dur(v.duration) + '</span>' : '') + '</div>' +
    '<div class="v4-vrow"><div class="v4-vtexts" data-id="' + v.videoId + '" onclick="v4WatchClick(this.dataset.id)"><div class="v4-vtitle">' + v4Esc(v.title) + '</div>' + (meta ? '<div class="v4-vmeta">' + meta + '</div>' : '') + '</div>' +
    '<button class="v4-dlbtn" title="Download" data-id="' + v.videoId + '" onclick="v4DlClick(event, this.dataset.id)">↓</button></div></div>';
}
function v4RenderCards(elId, items){
  const el = v4$(elId);
  if(!items || !items.length){ el.innerHTML = '<p class="v4-muted">Kuch nahi mila — dobara try karein.</p>'; return; }
  el.innerHTML = items.map(function(it){ const v = v4Norm(it); if(!v.videoId) return ''; v4Videos[v.videoId] = v; return v4CardHTML(v); }).join('');
}
async function v4LoadFeed(elId, q){
  const el = v4$(elId); el.innerHTML = '<p class="v4-muted">Load ho raha hai...</p>';
  const r = await v4Fetch('/api/search?q=' + encodeURIComponent(q) + '&max=20');
  if(r.ok && r.data && r.data.items) v4RenderCards(elId, r.data.items);
  else el.innerHTML = '<p class="v4-muted">Results load nahi ho sake — net check karke dobara try karein.</p>';
}
function v4HomeSearch(e){ e.preventDefault(); const q = v4$('v4-q-home').value.trim(); if(!q) return; if(q.indexOf('http') === 0){ v4SmartLink(q); return; } v4$('v4-home-heading').textContent = 'Results: ' + q; v4LoadFeed('v4-home-feed', q); }
async function v4SmartLink(q){
  const r = await v4Post('/api/smart-link', {url:q});
  if(r.ok && r.data){
    if(r.data.type === 'youtube'){ const v = {videoId:r.data.video_id, title:'', channel:''}; v4Videos[v.videoId] = v; v4DlClick(null, v.videoId); return; }
    if(r.data.type === 'social'){ v4Show('social'); v4$('v4-social-url').value = q; v4SocialFetch(null); return; }
    if(r.data.type === 'playlist'){ v4Toast('Playlist link mila — AI Assistant me command de kar download karein'); return; }
  }
  v4LoadFeed('v4-home-feed', q);
}
function v4FeedSearch(e, which){ e.preventDefault(); const q = v4$('v4-q-' + which).value.trim(); if(q) v4LoadFeed('v4-' + which + '-feed', q); }

/* ---------- watch (auth gate — Update 21) ---------- */
function v4WatchClick(id){
  if(!id || id === 'undefined'){ v4Toast('Video ID nahi mili — dobara try karein'); return; }
  const v = v4Videos[id] || {videoId:id, title:'', channel:''};
  if(!v4State.user){ v4Pending = {type:'watch', id:id}; v4OpenAuth('signin'); return; }
  v4OpenWatch(v);
}
function v4OpenWatch(v){
  v4Current = v;
  if(v4State.view !== 'watch') v4PrevView = v4State.view;
  v4$('v4-player').src = 'https://www.youtube.com/embed/' + v.videoId + '?autoplay=1&rel=0';
  v4$('v4-watch-title').textContent = v.title || '';
  v4$('v4-watch-channel').textContent = v.channel || '';
  v4Show('watch');
  v4Post('/api/add-history', {video_id:v.videoId, title:v.title || '', channel:v.channel || ''});
  const kw = (v.title || '').split(' ').slice(0, 4).join(' ');
  if(kw) v4LoadFeed('v4-related', kw);
}
function v4Back(){ v4$('v4-player').src = ''; v4Show(v4PrevView || 'home'); }
function v4WatchDownload(){ if(v4Current) v4OpenSheet(v4Current.videoId); }

/* ---------- download sheet ---------- */
function v4DlClick(ev, id){
  if(ev) ev.stopPropagation();
  if(!id || id === 'undefined'){ v4Toast('Video ID nahi mili — dobara try karein'); return; }
  if(!v4State.user){ v4Pending = {type:'sheet', id:id}; v4OpenAuth('signin'); return; }
  v4OpenSheet(id);
}
async function v4OpenSheet(id){
  const v = v4Videos[id] || {videoId:id, title:'', channel:''};
  v4Sheet = {id:id, sel:null};
  v4$('v4-sheet-thumb').src = 'https://i.ytimg.com/vi/' + id + '/hqdefault.jpg';
  v4$('v4-sheet-title').textContent = v.title || '';
  v4$('v4-sheet-channel').textContent = v.channel || '';
  v4$('v4-sheet-list').innerHTML = '<p class="v4-muted">Formats load ho rahe hain...</p>';
  v4$('v4-sheetwrap').classList.add('open');
  const btn = v4$('v4-sheet-download');
  if(v4State.config && v4State.config.toggles && v4State.config.toggles.downloads_enabled === false){ btn.disabled = true; btn.textContent = 'Downloads band hain'; }
  else { btn.disabled = false; btn.textContent = 'Download'; }
  const r = await v4Fetch('/api/formats/' + id);
  const list = v4$('v4-sheet-list');
  if(!r.ok || !r.data || r.data.error){ list.innerHTML = '<p class="v4-muted">Formats nahi mil sake: ' + v4Esc((r.data && r.data.error) || 'error') + '</p>'; return; }
  const d = r.data;
  if(d.title) v4$('v4-sheet-title').textContent = d.title;
  if(d.channel) v4$('v4-sheet-channel').textContent = d.channel;
  const row = function(f){ return '<div class="v4-fmtrow" data-fmt="' + f.format + '" data-q="' + (f.quality || '') + '" onclick="v4PickFmt(this)"><span class="nm">' + v4Esc(f.label) + '</span>' + (f.size_mb != null ? '<span class="sz">' + f.size_mb + ' MB</span>' : '') + '<span class="v4-radio">✓</span></div>'; };
  list.innerHTML = '<div class="v4-sect">MUSIC / AUDIO</div>' + (d.music || []).map(row).join('') + '<div class="v4-sect">VIDEO</div>' + (d.video || []).map(row).join('');
  let target = null;
  list.querySelectorAll('.v4-fmtrow').forEach(function(el){ if(el.getAttribute('data-q') === v4State.settings.defQuality) target = el; });
  if(!target) list.querySelectorAll('.v4-fmtrow').forEach(function(el){ if(el.getAttribute('data-q') === '360p') target = el; });
  if(target) target.click();
}
function v4PickFmt(el){
  document.querySelectorAll('#v4-sheet-list .v4-fmtrow').forEach(function(x){ x.classList.remove('sel'); });
  el.classList.add('sel');
  v4Sheet.sel = {format: el.getAttribute('data-fmt'), quality: el.getAttribute('data-q') || null};
}
function v4CloseSheet(){ v4$('v4-sheetwrap').classList.remove('open'); }
function v4SheetDownload(){
  if(!v4Sheet.sel){ v4Toast('Pehle ek quality chunein'); return; }
  const params = {video_id: v4Sheet.id, format: v4Sheet.sel.format, quality: v4Sheet.sel.quality, title: v4$('v4-sheet-title').textContent || ''};
  if(!v4State.user){ v4Pending = {type:'start', params:params}; v4CloseSheet(); v4OpenAuth('signin'); return; }
  v4StartDownload(params);
}
async function v4StartDownload(params){
  const body = Object.assign({}, params, {download_id: 'v4_' + Date.now()});
  const r = await v4Post('/api/start-download', body);
  if(r.ok && r.data && r.data.success){ v4CloseSheet(); v4Toast('Download shuru ho gaya — Downloads me dekhein'); v4LoadDownloads(); return; }
  const d = r.data || {};
  if(d.login_required){ v4Pending = {type:'start', params:params}; v4CloseSheet(); v4OpenAuth('signin'); return; }
  if(d.premium_required){ v4CloseSheet(); v4Toast('HD quality ke liye Premium chahiye'); v4Show('premium'); return; }
  v4Toast(d.error || 'Download start nahi ho saka');
}

/* ---------- downloads view (unified registry — Bug #3/#9) ---------- */
async function v4LoadDownloads(){
  try{
    const res = await Promise.all([v4Fetch('/api/download-progress'), v4Fetch('/api/downloads-list')]);
    if(res[0].ok) v4DlData.progress = res[0].data || {};
    if(res[1].ok && res[1].data) v4DlData.list = res[1].data.downloads || [];
    v4RenderDownloads(); v4UpdateBadge();
  }catch(e){}
}
function v4UpdateBadge(){
  let n = 0;
  Object.values(v4DlData.progress || {}).forEach(function(s){ if(['starting','downloading','processing'].indexOf(s.status) >= 0) n++; });
  const b = v4$('v4-dl-badge'); if(b){ b.textContent = n; b.style.display = n ? 'inline-block' : 'none'; }
}
function v4RenderDownloads(){
  const fEl = v4$('v4-dl-filter'); if(!fEl) return;
  const f = (fEl.value || '').toLowerCase();
  const act = [];
  Object.keys(v4DlData.progress || {}).forEach(function(id){ const s = v4DlData.progress[id]; if(['starting','downloading','processing','paused'].indexOf(s.status) >= 0) act.push({id:id, s:s}); });
  const actIds = {}; act.forEach(function(a){ actIds[a.id] = 1; });
  const rowAct = function(a){
    const s = a.s, vid = s.video_id || '', title = s.title || vid || a.id;
    if(f && title.toLowerCase().indexOf(f) < 0) return '';
    const pct = s.percent || 0;
    const meta = [s.quality || s.format_type || '', s.status === 'paused' ? 'Ruka hua' : (pct + '%'), s.speed || ''].filter(Boolean).join(' • ');
    const btn = s.status === 'paused'
      ? '<button class="v4-roundbtn teal" title="Resume" data-id="' + a.id + '" onclick="v4ResumeDl(this.dataset.id)">▶</button>'
      : '<button class="v4-roundbtn" title="Pause" data-id="' + a.id + '" onclick="v4PauseDl(this.dataset.id)">❚❚</button>';
    return '<div class="v4-dlrow">' + (vid ? v4Img(vid) : '<span style="width:64px"></span>') + '<div class="tt"><div class="t1">' + v4Esc(title) + '</div><div class="v4-bar"><i style="width:' + pct + '%"></i></div><div class="t2">' + v4Esc(meta) + '</div></div>' + btn + '</div>';
  };
  v4$('v4-dl-active').innerHTML = act.length ? act.map(rowAct).join('') : '<p class="v4-muted">Koi download nahi chal raha</p>';
  const rowDone = function(d){
    const title = d.title || ''; if(f && title.toLowerCase().indexOf(f) < 0) return '';
    const vid = d.videoId || '';
    if(d.status === 'failed'){
      return '<div class="v4-dlrow">' + (vid ? v4Img(vid) : '<span style="width:64px"></span>') + '<div class="tt"><div class="t1">' + v4Esc(title) + '</div><div class="t2" style="color:var(--v4danger)">Fail ho gaya: ' + v4Esc(d.error || 'error') + '</div></div>' + (vid ? '<button class="v4-roundbtn" title="Dobara try" data-id="' + vid + '" onclick="v4DlClick(event, this.dataset.id)">↻</button>' : '') + '<button class="v4-roundbtn" title="Delete" data-id="' + d.downloadId + '" onclick="v4DeleteDl(this.dataset.id)">🗑</button></div>';
    }
    return '<div class="v4-dlrow">' + (vid ? v4Img(vid) : '<span style="width:64px"></span>') + '<div class="tt"><div class="t1">' + v4Esc(title) + '</div><div class="t2">' + v4Esc([d.quality || d.format || '', v4MB(d.file_size)].filter(Boolean).join(' • ')) + '</div></div>' +
      '<a class="v4-roundbtn teal" title="Play" href="/api/download-file/' + d.downloadId + '">▶</a>' +
      '<a class="v4-roundbtn" title="Phone me save karein" href="/api/download-file/' + d.downloadId + '" download>⬇</a>' +
      '<button class="v4-roundbtn" title="Delete" data-id="' + d.downloadId + '" onclick="v4DeleteDl(this.dataset.id)">🗑</button></div>';
  };
  const doneList = (v4DlData.list || []).filter(function(d){ return !actIds[d.downloadId]; });
  v4$('v4-dl-done').innerHTML = doneList.length ? doneList.map(rowDone).join('') : '<p class="v4-muted">Abhi tak koi download nahi</p>';
}
async function v4PauseDl(id){ await v4Post('/api/cancel-download/' + id, {}); v4LoadDownloads(); }
async function v4ResumeDl(id){ const r = await v4Post('/api/resume-download/' + id, {}); if(!r.ok) v4Toast((r.data && r.data.error) || 'Resume nahi ho saka'); v4LoadDownloads(); }
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
function v4AiBubble(text, me){
  const d = document.createElement('div');
  d.className = 'v4-bubble ' + (me ? 'me' : 'ai');
  d.textContent = text;
  v4$('v4-ai-msgs').appendChild(d);
  window.scrollTo(0, document.body.scrollHeight);
  return d;
}
async function v4AiSend(e){
  if(e) e.preventDefault();
  const inp = v4$('v4-ai-input'); const text = inp.value.trim(); if(!text) return;
  inp.value = '';
  v4AiBubble(text, true);
  const r = await v4Post('/api/ai/command', {command:text});
  const d = r.data || {};
  if(!r.ok){ v4AiBubble(d.error || 'Command nahi chali — dobara try karein'); return; }
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
  if(d.url){
    const b = v4AiBubble(d.message || 'Tayyar hai');
    b.appendChild(document.createElement('br'));
    const a = document.createElement('a'); a.href = d.url; a.className = 'v4-btn2'; a.textContent = 'Download karein'; a.style.marginTop = '8px'; b.appendChild(a);
    return;
  }
  const b = v4AiBubble(d.message || 'Job shuru ho gaya');
  if(d.job_id){ const holder = document.createElement('div'); holder.id = 'v4-job-' + d.job_id; b.appendChild(holder); v4PollJob(d.job_id); }
}
function v4PollJob(jobId){
  const tick = async function(){
    const r = await v4Fetch('/api/ai/jobs/' + jobId);
    if(!r.ok || !r.data || !r.data.job) return;
    const job = r.data.job;
    v4RenderJob(jobId, job);
    if(['completed','partial','failed','interrupted'].indexOf(job.status) >= 0){ clearInterval(v4JobTimers[jobId]); delete v4JobTimers[jobId]; v4LoadDownloads(); }
  };
  tick();
  v4JobTimers[jobId] = setInterval(tick, 3000);
}
function v4RenderJob(jobId, job){
  const holder = v4$('v4-job-' + jobId); if(!holder) return;
  const icon = function(s){ return s === 'completed' ? '✓' : (s === 'failed' ? '✗' : (s === 'downloading' ? '◌' : '•')); };
  const stat = function(es){
    if(es.status === 'completed') return 'Ho gaya — Downloads mein hai';
    if(es.status === 'failed') return 'Fail: ' + (es.error || '');
    if(es.status === 'downloading') return 'Download ho raha hai' + (es.percent != null ? ' • ' + es.percent + '%' : '');
    if(es.status === 'searching') return 'Dhoondh raha hai...';
    return 'Line mein hai';
  };
  let h = '<div style="margin-top:8px">';
  (job.episodes_status || []).forEach(function(es, i){
    const name = es.title || ('Episode ' + (es.episode != null ? es.episode : (i + 1)));
    h += '<div class="v4-ep"><span>' + icon(es.status) + '</span><span style="flex:1;min-width:0">' + v4Esc(name) + '</span><span class="st">' + v4Esc(stat(es)) + '</span></div>';
  });
  h += '<div class="v4-muted" style="margin-top:6px">Halat: ' + v4Esc(job.status) + ' • ' + (job.completed_count || 0) + '/' + (job.total_count || (job.episodes_status || []).length) + ' ho gaye</div></div>';
  holder.innerHTML = h;
}

/* ---------- social / more ---------- */
const V4_PLATFORMS = ['YouTube','Facebook','Instagram','TikTok','WhatsApp Status','Pinterest','Twitter / X','SnapChat','Threads','DailyMotion','SoundCloud','Vimeo','Reddit','LinkedIn','Twitch'];
function v4RenderPlats(){
  v4State.platsDone = 1;
  const h = V4_PLATFORMS.map(function(p){ return '<div class="v4-plat" data-p="' + p + '" onclick="v4PlatClick(this)">' + p + '<div class="v4-muted">Link paste karein</div></div>'; }).join('');
  v4$('v4-plat-list').innerHTML = h;
}
function v4PlatClick(el){ v4Show('social'); const inp = v4$('v4-social-url'); inp.placeholder = el.getAttribute('data-p') + ' ka link yahan paste karein...'; inp.focus(); }
async function v4SocialFetch(e){
  if(e) e.preventDefault();
  const url = v4$('v4-social-url').value.trim();
  const box = v4$('v4-social-result');
  if(!url){ v4Toast('Pehle link paste karein'); return; }
  box.innerHTML = '<p class="v4-muted">Video ki info aa rahi hai...</p>';
  const r = await v4Post('/api/fetch-social-info', {url:url});
  if(!r.ok || !r.data || !r.data.info){ box.innerHTML = '<p class="v4-muted">' + v4Esc((r.data && r.data.error) || 'Info nahi mil saki') + '</p>'; return; }
  v4SocialInfo = {url:url, info:r.data.info};
  const inf = r.data.info;
  box.innerHTML = '<div class="v4-dlrow"><img src="' + v4Esc(inf.thumbnail || '') + '" onerror="this.style.opacity=0.25"><div class="tt"><div class="t1">' + v4Esc(inf.title || '') + '</div><div class="t2">' + v4Esc(inf.platform || '') + ' • ' + v4Esc(inf.uploader || '') + '</div></div></div>' +
    '<div style="display:flex;gap:8px"><button class="v4-bigbtn" style="margin-top:4px" data-f="video" onclick="v4SocialDownload(this.dataset.f)">⬇ Video Download</button><button class="v4-bigbtn" style="margin-top:4px;background:var(--v4card);border:1px solid var(--v4border)" data-f="audio" onclick="v4SocialDownload(this.dataset.f)">🎵 Audio (MP3)</button></div>';
}
async function v4SocialDownload(fmt){
  if(!v4SocialInfo) return;
  if(!v4State.user){ v4Pending = {type:'social', url:v4SocialInfo.url, format:fmt}; v4OpenAuth('signin'); return; }
  const r = await v4Post('/api/download-social', {url:v4SocialInfo.url, format:fmt});
  if(r.ok && r.data && r.data.success){ v4Toast('Download shuru ho gaya — Downloads me dekhein'); v4LoadDownloads(); }
  else v4Toast((r.data && r.data.error) || 'Download start nahi ho saka');
}

/* ---------- tools / settings ---------- */
function v4ShareApp(){
  const url = window.location.origin + '/';
  if(navigator.share){ navigator.share({title:'PlayTube', text:'PlayTube — All in One Downloader', url:url}).catch(function(){}); }
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
function v4ToggleSetting(key, el){ v4State.settings[key] = !v4State.settings[key]; el.classList.toggle('on', v4State.settings[key]); v4SaveSettings(true); }
function v4SaveSettings(silent){
  const s = v4State.settings;
  const f = v4$('v4-set-folder'); if(f) s.folder = f.value || 'PlayTube';
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
  h += '<div class="v4-sect">WEBSITE ON / OFF</div>';
  h += tog('ai_enabled', 'AI Assistant') + tog('downloads_enabled', 'Downloads') + tog('premium_enabled', 'Premium System') + tog('social_enabled', 'Social Tab') + tog('signup_enabled', 'Naya Signup (registration)') + tog('floating_enabled', 'Floating Button (APK)') + tog('maintenance_mode', 'Maintenance (site band)');
  h += '<div class="v4-sect">ELAAN (ANNOUNCEMENT)</div><input class="v4-input" id="v4-adm-ann" placeholder="Home par sab ko dikhne wala message" value="' + v4Esc(cfg.announcement || '') + '"><button class="v4-btn2" onclick="v4AdminSaveAnn()">Save Elaan</button>';
  const pr = cfg.prices || {};
  h += '<div class="v4-sect">PREMIUM PRICES (Rs)</div>';
  h += '<div class="v4-row"><div class="grow">Weekly</div><input class="v4-input" style="width:110px;margin:0" id="v4-pr-weekly" type="number" value="' + (pr.weekly || 200) + '"></div>';
  h += '<div class="v4-row"><div class="grow">Monthly</div><input class="v4-input" style="width:110px;margin:0" id="v4-pr-monthly" type="number" value="' + (pr.monthly || 500) + '"></div>';
  h += '<div class="v4-row"><div class="grow">Yearly</div><input class="v4-input" style="width:110px;margin:0" id="v4-pr-yearly" type="number" value="' + (pr.yearly || 3000) + '"></div>';
  h += '<button class="v4-btn2" onclick="v4AdminSavePrices()" style="margin-top:8px">Prices Save karein</button>';
  h += '<div class="v4-sect">PAYMENT NUMBERS</div>';
  const pa = cfg.payment_accounts || {};
  ['jazzcash','easypaisa'].forEach(function(m){
    const a = pa[m] || {};
    h += '<div class="v4-row"><div class="grow" style="text-transform:capitalize">' + m + '<div class="v4-muted">Khaali chhor dein to remove ho jayega</div></div></div>' +
      '<input class="v4-input" id="v4-pa-' + m + '-num" placeholder="Account number" value="' + v4Esc(a.account_number || '') + '">' +
      '<input class="v4-input" id="v4-pa-' + m + '-title" placeholder="Account title" value="' + v4Esc(a.account_title || '') + '">' +
      '<button class="v4-btn2" data-m="' + m + '" onclick="v4AdminSaveAccount(this.dataset.m)">Save ' + m + '</button>';
  });
  const plist = (res[3].data && res[3].data.payments) || [];
  h += '<div class="v4-sect">PREMIUM REQUESTS</div>';
  if(!plist.length) h += '<p class="v4-muted">Koi pending request nahi</p>';
  plist.forEach(function(p){
    h += '<div class="v4-dlrow"><div class="tt"><div class="t1">' + v4Esc(p.username || '') + ' — ' + v4Esc(p.plan_type || '') + ' (Rs ' + v4Esc(p.amount_pkr || '') + ')</div><div class="t2">' + v4Esc(p.payment_method || '') + ' • Txn: ' + v4Esc(p.transaction_id || '') + '</div></div>' +
      '<button class="v4-roundbtn teal" title="Approve" data-pid="' + p.id + '" data-ap="1" onclick="v4AdminPay(this)">✓</button>' +
      '<button class="v4-roundbtn" title="Reject" data-pid="' + p.id + '" data-ap="0" onclick="v4AdminPay(this)">✕</button></div>';
  });
  const ulist = (res[2].data && res[2].data.users) || [];
  h += '<div class="v4-sect">USERS</div>';
  ulist.forEach(function(u){
    h += '<div class="v4-row"><div class="grow">' + v4Esc(u.username) + ' <span class="v4-muted">' + v4Esc(u.email) + '</span></div>' +
      (u.is_owner ? '<span class="v4-badge2 owner">Owner</span>'
        : (u.is_premium ? '<span class="v4-badge2 prem">Premium</span><button class="v4-btn2" data-uid="' + u.id + '" data-grant="0" onclick="v4AdminUserPrem(this)">Band karein</button>'
                       : '<button class="v4-btn2" data-uid="' + u.id + '" data-grant="1" onclick="v4AdminUserPrem(this)">Premium dein</button>')) + '</div>';
  });
  h += '<button class="v4-bigbtn" style="background:var(--v4card);border:1px solid var(--v4border)" onclick="v4AdminLogout()">Admin Logout</button>';
  body.innerHTML = h;
}
async function v4AdminLogin(){ const key = v4$('v4-admin-key').value; const r = await v4Post('/api/admin/login', {key:key}); if(r.ok && r.data && r.data.success){ v4Toast('Admin login ho gaya'); v4RenderAdmin(); } else v4Toast('Galat admin key'); }
async function v4AdminLogout(){ await v4Post('/api/admin/logout', {}); v4RenderAdmin(); }
async function v4AdminToggle(el){ const key = el.getAttribute('data-key'); const on = !el.classList.contains('on'); el.classList.toggle('on', on); const body = {toggles:{}}; body.toggles[key] = on; const r = await v4Post('/api/admin/v4-settings', body); if(r.ok){ v4Toast('Setting save ho gayi'); v4LoadConfig(); } else { el.classList.toggle('on', !on); v4Toast('Save nahi ho saki'); } }
async function v4AdminSaveAnn(){ const r = await v4Post('/api/admin/v4-settings', {announcement: v4$('v4-adm-ann').value}); if(r.ok){ v4Toast('Elaan save ho gaya'); v4LoadConfig(); } }
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
function v4InstallPWA(){ if(typeof installPlayTubeApp === 'function') installPlayTubeApp(); else v4Toast('Browser menu se "Install app" / "Add to Home screen" chunein'); }
function v4InstallPC(){ if(typeof installPlayTubeAppPC === 'function') installPlayTubeAppPC(); else if(typeof installPlayTubeApp === 'function') installPlayTubeApp(); else v4Toast('Chrome/Edge menu se "Install PlayTube" chunein'); }

/* ---------- auth modal (Update 21/22) ---------- */
function v4OpenAuth(tab, forgot){
  v4$('v4-authwrap').classList.add('open');
  v4AuthMsg('', '');
  if(forgot){ v4ShowForgot(); return; }
  v4AuthTab(tab || 'signin');
}
function v4OpenAuthForgot(){ v4OpenAuth('signin', true); }
function v4CloseAuth(){ v4$('v4-authwrap').classList.remove('open'); }
function v4AuthMsg(txt, kind){ const m = v4$('v4-auth-msg'); m.className = 'v4-msg' + (kind ? ' ' + kind : ''); m.textContent = txt || ''; }
function v4AuthForms(show){
  ['v4-form-signin','v4-form-signup','v4-form-verify','v4-form-forgot','v4-form-reset'].forEach(function(id){ v4$(id).style.display = (id === show) ? 'block' : 'none'; });
}
function v4AuthTab(t){
  v4AuthForms(t === 'signup' ? 'v4-form-signup' : 'v4-form-signin');
  v4$('v4-tab-signin').classList.toggle('active', t !== 'signup');
  v4$('v4-tab-signup').classList.toggle('active', t === 'signup');
  v4$('v4-auth-heading').textContent = (t === 'signup') ? 'Create Account' : 'Welcome to PlayTube';
}
function v4ShowForgot(e){
  if(e) e.preventDefault();
  v4AuthForms('v4-form-forgot');
  v4$('v4-auth-heading').textContent = 'Password Reset';
}
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
    v4AuthForms('v4-form-verify');
    v4$('v4-auth-heading').textContent = 'Code Verify karein';
    if(r.data.mail_sent === false){
      v4$('v4-verify-note').textContent = 'Note: Email abhi nahi bheja ja saka (mail setup pending hai). Agar code aap ko mila hai to darj karein, warna thodi der baad dobara try karein.';
      v4AuthMsg('Code tayyar hai, lekin email bhejna abhi setup nahi hai.', 'err');
    } else v4AuthMsg('Code bhej diya gaya hai — apni Gmail check karein.', 'ok');
  } else v4AuthMsg((r.data && r.data.error) || 'Account nahi ban saka', 'err');
}
async function v4SignUpVerify(e){
  e.preventDefault();
  const r = await v4Post('/api/signup-verify', {email: v4SignupEmail, code: v4$('v4-su-code').value.trim()});
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
    v4AuthMsg(r.data.mail_sent === false ? 'Code tayyar hai, lekin email bhejna abhi setup nahi hai.' : 'Reset code bhej diya gaya hai — Gmail check karein.', r.data.mail_sent === false ? 'err' : 'ok');
  } else v4AuthMsg((r.data && r.data.error) || 'Code nahi bheja ja saka', 'err');
}
async function v4ForgotReset(e){
  e.preventDefault();
  const body = {email: v4SignupEmail, code: v4$('v4-fg-code').value.trim(), new_password: v4$('v4-fg-pass').value};
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
}

/* ---------- shared link + clipboard (Update 25) ---------- */
async function v4HandleShared(url){
  if(!url) return;
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
  const t = r.data.toggles || {};
  if(t.social_enabled === false){ const b = v4$('v4-tt-social'); if(b) b.style.display = 'none'; }
  if(t.ai_enabled === false){ const b = v4$('v4-bn-ai'); if(b) b.style.display = 'none'; }
}
(function v4Init(){
  v4LoadConfig();
  v4Fetch('/api/user-info').then(function(r){ v4State.user = (r.ok && r.data) ? r.data.user : null; });
  v4LoadFeed('v4-home-feed', 'trending');
  v4SyncThemeBtn();
  const sp = new URLSearchParams(window.location.search).get('shared');
  if(sp){ setTimeout(function(){ v4HandleShared(sp); }, 500); }
  else { setTimeout(v4ClipCheck, 1500); }
  window.addEventListener('focus', function(){ setTimeout(v4ClipCheck, 300); });
  setInterval(v4Tick, 4000);
})();
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
                                'channelTitle': entry.get('channel', entry.get('uploader', 'Unknown')),
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
            search_cache[cache_key] = (data, time.time())
            return jsonify(data)

    # Method 4: Fallback
    data = {'items': POPULAR_VIDEOS[:max_results]}
    return jsonify(data)


@app.route('/api/fetch-social-info', methods=['POST'])
def fetch_social_info():
    data = request.json
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'skip_download': True, 'no_check_certificate': True,
            'prefer_insecure': True, 'retries': 2,
        }

        info = _extract_with_clients(url, ydl_opts)

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
                        "formats_available": len(info.get('formats', [])) if 'formats' in info else 0
                    }
                })
    except Exception as e:
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
        return jsonify({"error": f"Could not fetch video info: {error_msg[:200]}"}), 400

    return jsonify({"error": "Could not fetch video information"}), 400


@app.route('/api/download-social', methods=['POST'])
def download_social_media():
    data = request.json
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    download_id = data.get('download_id', '')

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not download_id:
        download_id = f"social_{int(time.time())}_{random.randint(1000, 9999)}"

    platform = detect_platform(url)

    download_progress[download_id] = {
        'status': 'starting', 'percent': 0, 'speed': '',
        'error': None, 'format': format_type, 'platform': platform
    }

    thread = threading.Thread(target=download_social_in_background, args=(
        url, format_type, platform, download_id))
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
        'snapchat.com': 'Snapchat',
        'whatsapp.com': 'WhatsApp'
    }
    for domain, platform in platforms.items():
        if domain in url:
            return platform
    return "Social Media"


def download_social_in_background(url, format_type, platform, download_id):
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
        else:
            ydl_opts = {
                'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                'outtmpl': os.path.join(SOCIAL_DIR, '%(title)s.%(ext)s'),
                'quiet': True, 'no_warnings': True, 'noplaylist': True,
                'progress_hooks': [progress_hook], 'ignoreerrors': True,
                'no_check_certificate': True, 'prefer_insecure': True,
                'merge_output_format': 'mp4', 'retries': 3, 'fragment_retries': 3,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = sanitize_filename(info.get('title', 'video'))

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

                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    final_format = 'MP3' if format_type == 'audio' else 'MP4'

                    downloaded_files[download_id] = {
                        'downloadId': download_id, 'videoId': download_id, 'title': title,
                        'format': final_format, 'quality': 'Best', 'platform': platform,
                        'file_path': file_path, 'file_size': file_size,
                        'status': 'completed', 'timestamp': datetime.now().isoformat()
                    }
                    save_downloads_db()

                    download_progress[download_id] = {
                        'status': 'completed', 'percent': 100, 'speed': '',
                        'error': None, 'file_path': file_path, 'title': title,
                        'format': format_type, 'platform': platform, 'file_size': file_size
                    }
                else:
                    raise Exception("Download completed but file not found")
    except Exception as e:
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
    if 'Unsupported' in error_msg:
        error_msg = 'URL not supported'
    elif 'not found' in error_msg.lower():
        error_msg = 'Video not found'
    elif 'private' in error_msg.lower():
        error_msg = 'Private video'
    elif 'network' in error_msg.lower():
        error_msg = 'Network error'

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
        <title>Privacy Policy - PlayTube</title>
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
            <p>When you register on PlayTube, we collect your username and email address. We do not collect any payment information directly.</p>

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

            <p><a href="/">← Back to PlayTube</a></p>
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
        <title>Terms of Service - PlayTube</title>
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
            <p>By accessing and using PlayTube, you agree to be bound by these Terms of Service.</p>

            <h2>2. Description of Service</h2>
            <p>PlayTube is a video downloading tool that allows users to download videos from various platforms for personal use only.</p>

            <h2>3. User Accounts</h2>
            <p>You are responsible for maintaining the confidentiality of your account credentials.</p>

            <h2>4. Premium Subscriptions</h2>
            <p>Premium plans provide additional features. Payments are processed via JazzCash and EasyPaisa. All sales are final.</p>

            <h2>5. Acceptable Use</h2>
            <p>You agree not to use PlayTube for any illegal or unauthorized purpose.</p>

            <h2>6. Intellectual Property</h2>
            <p>All downloaded content belongs to their respective owners. PlayTube does not claim ownership.</p>

            <h2>7. Refund Policy</h2>
            <p>Due to the digital nature of our service, we do not offer refunds for premium subscriptions.</p>

            <h2>8. Contact</h2>
            <p>Email: chuzajani1@gmail.com</p>

            <p><a href="/">← Back to PlayTube</a></p>
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
        <title>About - PlayTube</title>
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
        <h1>About PlayTube</h1>

        <div class="box">
            <h2>🎬 What is PlayTube?</h2>
            <p>PlayTube is a free video downloader that allows users to download videos from YouTube and other social media platforms. We provide high-quality MP3 and MP4 downloads for personal use.</p>
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

        <p><a href="/">← Back to PlayTube</a></p>
    </body>
    </html>
    '''


@app.route('/developer')
def developer():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Developer - PlayTube</title>
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
            <p>Full Stack Developer & Creator of PlayTube</p>
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
        <p><a href="/">← Back to PlayTube</a></p>
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
        <title>Contact - PlayTube</title>
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
        <p><a href="/">← Back to PlayTube</a></p>
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
                <title>{channel_name} - PlayTube</title>
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
                <a href="/" class="back-btn">← Back to PlayTube</a>
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
ADMIN_SECRET_KEY = "Chuza-PlayTube-_nyDbqU9aci8uRBCIzhbFiAK"  # Apna secret key yahan daalo


@app.route('/admin/<secret_key>')
def admin_panel(secret_key):
    if secret_key != ADMIN_SECRET_KEY:
        return "Access Denied", 403

    session['pt_admin'] = True

    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PlayTube Admin</title>
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
        <h1>🔐 PlayTube Admin Panel</h1>
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
    if not session.get('pt_admin'):
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
    if not session.get('pt_admin'):
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
    if not session.get('pt_admin'):
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

    # Login check
    if not session.get('user_id'):
        return jsonify({
            'error': 'Login required to download!',
            'login_required': True
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
        if not is_premium_user(session['user_id']):
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


def _ydl_opts_with_client(base_opts, client):
    opts = dict(base_opts or {})
    _ck = os.environ.get('YT_COOKIES_PATH', '')
    if _ck and os.path.exists(_ck):
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
                    print(f"[PlayTube] yt-dlp player_client '{_client}' worked for {str(url)[:70]}")
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


# ============ SPEED SETTINGS (Update 9 - VIP) ============
# Parallel fragment downloads + big chunks + aria2c (16 connections) when available.
def _speed_opts():
    opts = {
        'concurrent_fragment_downloads': 16,
        'http_chunk_size': 10 * 1024 * 1024,
        'buffer_size': 1024 * 16,
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
                           clip_start=None, clip_end=None, _client_idx=0, title_hint=None):
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
                'speed_bytes': speed or 0, 'error': None}
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
        _ck = os.environ.get('YT_COOKIES_PATH', '')
        if _ck and os.path.exists(_ck):
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
                    exts = ('.mp3', '.m4a') if format_type in ('mp3', 'm4a') else \
                           ('.mp4', '.mkv', '.webm', '.3gp')
                    files = [f for f in os.listdir(download_dir) if f.endswith(exts)]
                    if files:
                        files.sort(key=lambda x: os.path.getmtime(
                            os.path.join(download_dir, x)), reverse=True)
                        file_path = os.path.join(download_dir, files[0])
                        title = os.path.splitext(files[0])[0]

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

                    download_progress[download_id] = {
                        'status': 'completed', 'percent': 100, 'speed': '',
                        'error': None, 'file_path': file_path, 'title': title,
                        'format': format_type, 'quality': quality_label,
                        'file_size': file_size,
                        'download_seconds': round(elapsed, 2),
                        'avg_speed_mbps': round(avg_mbps, 2)
                    }
                    return
                error_msg = 'Download failed - no file produced'
    except Exception as e:
        if download_control.get(download_id, {}).get('cancel'):
            _pp = download_progress.get(download_id, {})
            download_progress[download_id] = {'status': 'paused',
                                              'percent': _pp.get('percent', 0),
                                              'speed': '', 'error': None}
            return
        if _is_bot_block(e) and _client_idx < len(_YT_CLIENTS) - 1:
            print(f"[PlayTube] Bot-block on download {download_id} - retry with client #{_client_idx + 1}")
            download_progress[download_id] = {'status': 'starting', 'percent': 0,
                                              'speed': '', 'error': None}
            return download_in_background(video_id, format_type, quality, download_id,
                                          user_id, clip_start, clip_end,
                                          _client_idx + 1, title_hint)
        error_msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e))

    if download_control.get(download_id, {}).get('cancel'):
        _pp = download_progress.get(download_id, {})
        download_progress[download_id] = {'status': 'paused',
                                          'percent': _pp.get('percent', 0),
                                          'speed': '', 'error': None}
        return

    # Friendly errors
    if 'Video unavailable' in error_msg:
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
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
    
    try:
        return send_file(file_path, as_attachment=True, download_name=filename, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/downloads-list')
def get_downloads_list():
    downloads = []
    for download_id, info in downloaded_files.items():
        downloads.append({
            'downloadId': download_id,
            'videoId': info.get('videoId', ''),
            'title': info.get('title', 'Unknown'),
            'format': info.get('format', 'unknown').upper(),
            'quality': info.get('quality', 'Best'),
            'platform': info.get('platform', 'YouTube'),
            'status': info.get('status', 'completed'),
            'error': info.get('error'),
            'file_size': info.get('file_size', 0),
            'timestamp': info.get('timestamp', datetime.now().isoformat())
        })
    
    downloads.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return jsonify({"downloads": downloads})

@app.route('/api/delete-download/<download_id>', methods=['DELETE'])
def delete_download(download_id):
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
    if not session.get('pt_admin'):
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
        'app_name': 'PlayTube',
        'developer': 'Chuza',
        'total_users': 0,  # Update from DB
        'total_downloads': len(downloaded_files),
        'premium_price': 'Rs. 500/month',
        'contact': 'chuzajani1@gmail.com'
    })
    # ============ VISITOR TRACKING ============
VISITORS_FILE = os.path.join(os.path.expanduser("~"), "visitors.json")

def load_visitors():
    try:
        if os.path.exists(VISITORS_FILE):
            with open(VISITORS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'total': 0, 'today': 0, 'date': '', 'ips': []}

def save_visitors(data):
    try:
        with open(VISITORS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

@app.before_request
def track_visitor():
    ip = request.remote_addr
    today = datetime.now().strftime('%Y-%m-%d')
    
    data = load_visitors()
    
    if data['date'] != today:
        data = {'total': data['total'], 'today': 0, 'date': today, 'ips': []}
    
    if ip not in data['ips']:
        data['ips'].append(ip)
        data['today'] += 1
        data['total'] += 1
        save_visitors(data)

@app.route('/api/visitor-stats')
def visitor_stats():
    data = load_visitors()
    return jsonify({
        'total_visitors': data['total'],
        'today_visitors': data['today'],
        'date': data['date']
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
                'account_title': str(data.get('account_title', 'PlayTube Premium')).strip()
                or 'PlayTube Premium'
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
        info = _extract_with_clients(
            f"https://www.youtube.com/watch?v={video_id}",
            {'quiet': True, 'no_warnings': True, 'no_check_certificate': True,
             'skip_download': True})
    except Exception as e:
        return jsonify({'error': re.sub(r'\x1b\[[0-9;]*m', '', str(e))[:150]}), 400
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
                  (2160, '2160p (4K)')]
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
        video_group.append({'label': _label, 'format': 'mp4', 'quality': f'{_h}p',
                            'size_mb': combined_size_mb(_best)})

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
]


def ai_parse_command(text):
    """Robust rule-based parser - Roman Urdu + English."""
    raw = (text or '').strip()
    t = ' ' + raw.lower() + ' '
    parsed = {'raw': raw, 'intent': 'download', 'title': '', 'episodes': [],
              'quality': '360p', 'format': 'mp4', 'schedule_at': None,
              'schedule_in_seconds': None}

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
    rng = re.search(r'(?:episode|ep|qist)\s*(\d+)\s*(?:to|se|-|–|tak)\s*(\d+)', t)
    if rng:
        a, b = int(rng.group(1)), int(rng.group(2))
        parsed['episodes'] = list(range(min(a, b), max(a, b) + 1))
        t = t.replace(rng.group(0), ' ')
    else:
        cnt = re.search(r'(\d+)\s*(?:episodes?|eps?|qistein|qistain|qist)', t)
        single = re.search(r'(?:episode|ep|qist)\s*(\d+)', t)
        if cnt:
            n = int(cnt.group(1))
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
    ep_patterns = [rf'episode\s*#?\s*{ep}\b', rf'\bep\s*#?\s*{ep}\b',
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

def _ai_wait_download(download_id, timeout=1800):
    start = time.time()
    while time.time() - start < timeout:
        st = download_progress.get(download_id, {})
        if st.get('status') == 'completed':
            return True, st
        if st.get('status') == 'error':
            return False, st
        time.sleep(2)
    return False, {'error': 'Timeout'}


def _ai_run_job(job_id):
    with ai_jobs_lock:
        job = ai_jobs.get(job_id)
        if not job:
            return
        job['status'] = 'running'
        _save_ai_jobs()
    parsed = job['parsed']
    episodes = parsed.get('episodes') or [None]
    done = 0
    for idx, ep in enumerate(episodes):
        query = f"{parsed['title']} episode {ep}" if ep else parsed['title']
        with ai_jobs_lock:
            job['episodes_status'][idx] = {'episode': ep, 'query': query,
                                           'status': 'searching', 'attempts': 0}
            _save_ai_jobs()
        ok = False
        last_err = ''
        for attempt in range(1, 4):  # 1 try + up to 2 auto-retries
            if ep:
                vid, vtitle, _found = _ai_find_episode(parsed['title'], ep)
                if not _found:
                    last_err = f"Episode {ep} nahi mila - koi sahi result nahi aaya"
                    break
            else:
                vid, vtitle = _ai_search_first(query)
            if not vid:
                last_err = 'Search me nahi mila'
                continue
            dl_id = f"ai_{job_id}_{idx}_{attempt}_{int(time.time())}"
            download_progress[dl_id] = {'status': 'starting', 'percent': 0,
                                        'speed': '', 'error': None}
            th = threading.Thread(target=download_in_background,
                                  args=(vid, parsed['format'], parsed['quality'],
                                        dl_id, None),
                                  kwargs={'title_hint': vtitle})
            th.daemon = True
            th.start()
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
                job['episodes_status'][idx].update(
                    {'attempts': attempt, 'video_id': vid,
                     'title': vtitle, 'status': 'downloading' if not ok else 'completed',
                     'file_path': st.get('file_path'), 'error': st.get('error')})
                _save_ai_jobs()
            if ok:
                break
            last_err = st.get('error') or 'Failed'
        with ai_jobs_lock:
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


@app.route('/api/ai/command', methods=['POST'])
def api_ai_command():
    data = request.json or {}
    text = data.get('command') or data.get('text') or ''
    if not text.strip():
        return jsonify({'error': 'Command required'}), 400
    if not feature_enabled('ai_enabled'):
        return jsonify({'error': 'AI Assistant abhi band hai (admin ne off kiya hai)',
                        'ai_disabled': True}), 403
    parsed = ai_parse_command(text)

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
        'completed_count': 0, 'total_count': len(episodes)
    }
    with ai_jobs_lock:
        ai_jobs[job_id] = job
        _save_ai_jobs()
    if job['status'] == 'queued':
        th = threading.Thread(target=_ai_run_job, args=(job_id,))
        th.daemon = True
        th.start()

    ep_text = (f"episodes {episodes[0]} to {episodes[-1]}" if len(episodes) > 1
               else (f"episode {episodes[0]}" if episodes[0] else 'video'))
    q_text = parsed['quality'] if parsed['format'] == 'mp4' else (
        f"MP3 {parsed['quality']}K" if parsed['format'] == 'mp3' else 'M4A')
    msg = (f"🤖 Samajh gaya! '{parsed['title']}' ki {ep_text} "
           f"{q_text} me download {'schedule kar di hai (' + when_text + ')' if job['status'] == 'scheduled' else 'start kar di hai'}. "
           f"Background me one by one chalti rahe gi. Job ID: {job_id}")
    return jsonify({'success': True, 'intent': 'download', 'job_id': job_id,
                    'parsed': parsed, 'message': msg})


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
def _v4_admin_guard():
    if not session.get('pt_admin'):
        return jsonify({'error': 'Admin login required'}), 403
    return None


@app.route('/api/site-config')
def api_site_config():
    return jsonify({
        'toggles': get_feature_toggles(),
        'announcement': get_announcement(),
        'prices': {k: v['price'] for k, v in PREMIUM_PLANS_PKR.items()},
        'apk_available': os.path.exists(_apk_file_path()),
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
    return jsonify({'admin': bool(session.get('pt_admin'))})


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
                        'account_title': str(acc.get('account_title', 'PlayTube Premium')).strip()
                        or 'PlayTube Premium'}
                else:
                    accounts.pop(method, None)
            settings['payment_accounts'] = accounts
        save_site_settings(settings)
        _rebuild_payment_accounts()
        settings = load_site_settings()
    return jsonify({
        'toggles': get_feature_toggles(),
        'announcement': settings.get('announcement', ''),
        'prices': {k: v['price'] for k, v in PREMIUM_PLANS_PKR.items()},
        'payment_accounts': settings.get('payment_accounts', {}),
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
    return jsonify({'total_users': total_users, 'downloads_today': downloads_today,
                    'pending_premium_requests': pending})


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


@app.route('/app-icon.svg')
def app_icon_svg():
    return Response(_APP_ICON_SVG, mimetype='image/svg+xml')


@app.route('/manifest.json')
def pwa_manifest():
    return jsonify({
        'name': 'PlayTube - All in One Downloader',
        'short_name': 'PlayTube',
        'description': 'PlayTube by Chuza - videos, dramas and music downloads with AI assistant',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#12102e',
        'theme_color': '#4f46e5',
        'icons': [
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
                         download_name='PlayTube.apk',
                         mimetype='application/vnd.android.package-archive')
    return jsonify({'error': 'APK coming soon after launch'}), 404


@app.route('/api/apk-status')
def api_apk_status():
    return jsonify({'available': os.path.exists(_apk_file_path()),
                    'url': '/playtube.apk'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))