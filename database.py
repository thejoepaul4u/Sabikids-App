import os
import sqlite3
import hashlib
import hmac
from contextlib import contextmanager

# Production Configuration & Plan Caps
DEFAULT_FREE_SECONDS = 600.0  # 10 Minutes Demo Cap
PLAN_MAX_SECONDS = {
    "Demo": 600.0,
    "24-Hour Active Bundle": 86400.0,   # 24 Hours Active Metered Time (86,400 seconds)
    "7-Day Active Bundle": 604800.0     # 7 Days Active Metered Time (604,800 seconds)
}

DB_NAME = "SabiLearners.db"
# Simple obfuscation example (joins split parts at runtime)
_K1 = b"SabiLearners_"
_K2 = b"Secure_984372901_HMAC_"
_K3 = b"Production_Key_2026"

SECRET_KEY = _K1 + _K2 + _K3

def get_hardware_identifier():
    """Generates a dynamic hardware-derived identifier across supported platforms."""
    try:
        from kivy.utils import platform
        
        # --- ANDROID PLATFORM ---
        if platform == 'android':
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Secure = autoclass('android.provider.Settings$Secure')
            content_resolver = PythonActivity.mActivity.getContentResolver()
            android_id = Secure.getString(content_resolver, Secure.ANDROID_ID)
            if android_id:
                return android_id

        # --- IOS PLATFORM ---
        elif platform == 'ios':
            from pyobjus import autoclass
            UIDevice = autoclass('UIDevice')
            current_device = UIDevice.currentDevice()
            vendor_id = current_device.identifierForVendor.UUIDString().UTF8String()
            if vendor_id:
                return vendor_id.decode('utf-8') if isinstance(vendor_id, bytes) else str(vendor_id)

    except Exception as e:
        print(f"[HW_ID WARNING]: Could not retrieve native identifier: {e}")

    return "SABILEARNERS_STATIC_HW_ID"

@contextmanager
def get_db_connection():
    """Context manager for SQLite connections with a 10s lock timeout and safe closure."""
    conn = sqlite3.connect(DB_NAME, timeout=10.0)
    try:
        yield conn
    finally:
        conn.close()

def compute_hmac(seconds_remaining):
    """Computes HMAC-SHA256 signature for metered seconds balance."""
    hw_id = get_hardware_identifier()
    combined_key = SECRET_KEY + hw_id.encode('utf-8')
    msg = f"{float(seconds_remaining):.2f}".encode('utf-8')
    return hmac.new(combined_key, msg, hashlib.sha256).hexdigest()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. USER PROFILE TABLE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_name TEXT DEFAULT '',
                child_name TEXT DEFAULT '',
                is_verified INTEGER DEFAULT 0,
                chosen_plan_type TEXT DEFAULT 'Demo',
                custom_billing_schedule TEXT DEFAULT 'Monthly',
                custom_max_cap_amount INTEGER DEFAULT 3500,
                parent_pin TEXT DEFAULT '',
                registration_step TEXT DEFAULT 'auth_page',
                is_registered INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'INACTIVE',
                payment_platform TEXT DEFAULT 'NONE',
                is_first_time_login INTEGER DEFAULT 1,
                free_seconds_remaining REAL DEFAULT 600.0,
                demo_seconds_remaining REAL DEFAULT 600.0,
                last_active_timestamp TIMESTAMP DEFAULT NULL,
                is_demo_used INTEGER DEFAULT 0,
                hero_bg_index INTEGER DEFAULT 0,
                hmac_signature TEXT DEFAULT ''
            )
        ''')
        
        # Safeguard migrations for database schemas
        for col, dtype in [
            ("parent_pin", "TEXT DEFAULT ''"),
            ("is_registered", "INTEGER DEFAULT 0"),
            ("subscription_status", "TEXT DEFAULT 'INACTIVE'"),
            ("payment_platform", "TEXT DEFAULT 'NONE'"),
            ("is_first_time_login", "INTEGER DEFAULT 1"),
            ("free_seconds_remaining", f"REAL DEFAULT {DEFAULT_FREE_SECONDS}"),
            ("demo_seconds_remaining", f"REAL DEFAULT {DEFAULT_FREE_SECONDS}"),
            ("last_active_timestamp", "TIMESTAMP DEFAULT NULL"),
            ("is_demo_used", "INTEGER DEFAULT 0"),
            ("hero_bg_index", "INTEGER DEFAULT 0"),
            ("hmac_signature", "TEXT DEFAULT ''")
        ]:
            try:
                cursor.execute(f"ALTER TABLE user_profile ADD COLUMN {col} {dtype}")
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        cursor.execute('SELECT COUNT(*) FROM user_profile')
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO user_profile (parent_name, child_name, chosen_plan_type, subscription_status, free_seconds_remaining, demo_seconds_remaining) VALUES ('', '', 'Demo', 'ACTIVE', 600.0, 600.0)")

        # 2. CLASSROOM SUBJECTS TABLE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                description TEXT,
                card_color TEXT DEFAULT '0.16, 0.50, 0.28, 1'
            )
        ''')

        # 3. CLASSROOM TOPICS TABLE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY(subject_id) REFERENCES subjects(id)
            )
        ''')

        # 4. CLASSROOM LESSONS TABLE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                title TEXT NOT NULL,
                content_type TEXT DEFAULT 'interactive',
                stars_reward INTEGER DEFAULT 5,
                FOREIGN KEY(topic_id) REFERENCES topics(id)
            )
        ''')

        # 5. USER PROGRESS TABLE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER,
                status TEXT DEFAULT 'locked',
                score INTEGER DEFAULT 0,
                stars_earned INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_synced INTEGER DEFAULT 0,
                FOREIGN KEY(lesson_id) REFERENCES lessons(id)
            )
        ''')

        # Seed default classroom subjects if empty
        cursor.execute('SELECT COUNT(*) FROM subjects')
        if cursor.fetchone()[0] == 0:
            default_subjects = [
                ('Mathematics', 'MATH', 'Fun numbers, counting, addition, and logic shapes.', '0.15, 0.65, 0.36, 1'),
                ('Literacy & English', 'ENG', 'Phonics, vocabulary, alphabet adventures, and reading.', '0.90, 0.49, 0.13, 1'),
                ('Elementary Science', 'SCI', 'Explore nature, simple physics, animals, and space.', '0.95, 0.77, 0.06, 1'),
                ('Sabi Logic', 'LOGIC', 'Puzzles, pattern recognition, and critical thinking.', '0.22, 0.71, 1.00, 1')
            ]
            cursor.executemany('''
                INSERT INTO subjects (title, code, description, card_color)
                VALUES (?, ?, ?, ?)
            ''', default_subjects)

        conn.commit()

def init_secure_db():
    """Initializes schema and validates HMAC signature for local database integrity."""
    init_db()
    profile = get_user_profile()
    stored_hmac = profile.get("hmac_signature", "")
    rem_sec = float(profile.get("free_seconds_remaining", DEFAULT_FREE_SECONDS))
    
    if stored_hmac:
        expected_hmac = compute_hmac(rem_sec)
        if not hmac.compare_digest(stored_hmac, expected_hmac):
            print("[SECURITY WARNING]: Database HMAC mismatch detected! Invalidating session.")
            update_user_profile({"free_seconds_remaining": 0.0, "is_demo_used": 1, "subscription_status": "EXPIRED"})
            return False
    else:
        update_user_profile({"hmac_signature": compute_hmac(rem_sec)})
    return True

def get_user_profile():
    """Retrieves current user profile record."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_profile LIMIT 1')
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            if not data.get('child_name') or not str(data.get('child_name')).strip():
                data['child_name'] = 'Champion'
            return data
            
        return {
            "parent_name": "",
            "child_name": "Champion",
            "is_verified": 0,
            "chosen_plan_type": "Demo",
            "subscription_status": "ACTIVE",
            "registration_step": "auth_page",
            "is_demo_used": 0,
            "free_seconds_remaining": DEFAULT_FREE_SECONDS,
            "demo_seconds_remaining": DEFAULT_FREE_SECONDS,
            "hero_bg_index": 0,
            "hmac_signature": ""
        }

def update_user_profile(data_dict):
    """Updates profile attributes and re-computes HMAC if timing balance changes."""
    if "free_seconds_remaining" in data_dict:
        data_dict["hmac_signature"] = compute_hmac(data_dict["free_seconds_remaining"])
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fields = [f"{k} = ?" for k in data_dict.keys()]
        values = list(data_dict.values())
        if fields:
            sql = f"UPDATE user_profile SET {', '.join(fields)} WHERE id = (SELECT id FROM user_profile LIMIT 1)"
            cursor.execute(sql, values)
            conn.commit()

def get_all_subjects():
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subjects')
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def delete_user_account():
    """Wipes user details and progress while preserving the demo timer status on the device."""
    profile = get_user_profile()
    
    current_free_sec = float(profile.get("free_seconds_remaining", DEFAULT_FREE_SECONDS))
    demo_already_used = (
        profile.get("is_demo_used", 0) == 1 or 
        float(profile.get("demo_seconds_remaining", DEFAULT_FREE_SECONDS)) <= 0.0 or
        current_free_sec <= 0.0
    )
    
    # Retain the exact remaining time on this device
    preserved_seconds = current_free_sec
    is_demo_used_flag = 1 if demo_already_used else int(profile.get("is_demo_used", 0))
    sub_status = "EXPIRED" if demo_already_used else profile.get("subscription_status", "ACTIVE")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_progress")
        
        cursor.execute("""
            UPDATE user_profile 
            SET parent_name='', 
                child_name='', 
                is_verified=0, 
                parent_pin='',
                registration_step='auth_page', 
                is_registered=0,
                is_first_time_login=1,
                chosen_plan_type='Demo',
                subscription_status=?, 
                is_demo_used=?, 
                free_seconds_remaining=?, 
                demo_seconds_remaining=?,
                hero_bg_index=0,
                hmac_signature=''
            WHERE id = (SELECT id FROM user_profile LIMIT 1)
        """, (sub_status, is_demo_used_flag, preserved_seconds, preserved_seconds))
        
        conn.commit()

    update_user_profile({"free_seconds_remaining": preserved_seconds})

init_secure_db()