import sqlite3
import aiosqlite
import logging
import re
import math
import os
import asyncio
from datetime import datetime, timedelta
from config import *

logger = logging.getLogger("MovieQuadEngineBot")

# -------------------------------------------------------------
# 0. Structural Absolute Path Matching Alignment
# -------------------------------------------------------------
# This guarantees that the read loop and the write loop target the exact same directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Resolving absolute tracks for all file attachments
ABS_DB_CORE = os.path.abspath(os.path.join(BASE_DIR, DB_CORE))
ABS_DB_ENGINE_A = os.path.abspath(os.path.join(BASE_DIR, DB_ENGINE_A))
ABS_DB_ENGINE_B = os.path.abspath(os.path.join(BASE_DIR, DB_ENGINE_B))
ABS_DB_ENGINE_C = os.path.abspath(os.path.join(BASE_DIR, DB_ENGINE_C))
ABS_DB_ENGINE_D = os.path.abspath(os.path.join(BASE_DIR, DB_ENGINE_D))
ABS_DB_ENGINE_E = os.path.abspath(os.path.join(BASE_DIR, DB_ENGINE_E))

# -------------------------------------------------------------
# 1. Helper Functions (Clean String, Similarity, & format_size)
# -------------------------------------------------------------
def format_size(size_bytes: int) -> str:
    """
    Converts file size in bytes to a human-readable format 
    (e.g., 1024 -> '1.00 KB', 1048576 -> '1.00 MB').
    """
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    try:
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
    except Exception:
        return f"{size_bytes} B"

def clean_string(text):
    text = re.sub(r'[\._\-]', ' ', text.lower())
    return re.sub(r'\s+', ' ', text).strip()

def calculate_similarity(s1, s2):
    s1, s2 = clean_string(s1), clean_string(s2)
    if not s1 or not s2: return 0.0
    if s1 in s2 or s2 in s1: return 0.85
    
    words1, words2 = s1.split(), s2.split()
    matches = sum(1 for w in words1 if any(w in target or target in w for target in words2))
    return matches / max(len(words1), len(words2))

# -------------------------------------------------------------
# 2. Database Manager Class
# -------------------------------------------------------------
class DatabaseManager:
    @staticmethod
    async def initialize():
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    plan TEXT DEFAULT 'Free',
                    searches_today INTEGER DEFAULT 0,
                    max_limit INTEGER DEFAULT 5,
                    referral_count INTEGER DEFAULT 0,
                    referred_by TEXT,
                    last_reset_date TEXT,
                    banned INTEGER DEFAULT 0,
                    premium_expiry TEXT DEFAULT 'Never',
                    last_reward_time TEXT,
                    verified INTEGER DEFAULT 0
                )
            """)
            try:
                await db.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
                await db.commit()
            except sqlite3.OperationalError: 
                pass

            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    plan_name TEXT,
                    price TEXT,
                    status TEXT DEFAULT 'Pending',
                    timestamp TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS coupons (
                    code TEXT PRIMARY KEY,
                    quota_reward INTEGER,
                    max_uses INTEGER,
                    current_uses INTEGER DEFAULT 0,
                    expiry_date TEXT
                )
            """)
            try:
                await db.execute("ALTER TABLE coupons ADD COLUMN expiry_date TEXT")
                await db.commit()
            except sqlite3.OperationalError: 
                pass
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS coupon_logs (
                    user_id TEXT,
                    code TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (user_id, code)
                )
            """)
            await db.execute("CREATE TABLE IF NOT EXISTS android_metadata (locale TEXT)")
            
            async with db.execute("SELECT COUNT(*) FROM android_metadata") as cursor:
                if (await cursor.fetchone())[0] == 0:
                    await db.execute("INSERT INTO android_metadata (locale) VALUES ('en_US')")
            await db.commit()

        channel_dbs = [ABS_DB_ENGINE_A, ABS_DB_ENGINE_B, ABS_DB_ENGINE_C, ABS_DB_ENGINE_D, ABS_DB_ENGINE_E]
        for idx, target_db in enumerate(channel_dbs, 1):
            async with aiosqlite.connect(target_db) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS movies (
                        msg_id INTEGER PRIMARY KEY,
                        file_name TEXT,
                        file_size INTEGER,
                        search_vector TEXT,
                        search_count INTEGER DEFAULT 0
                    )
                """)
                await db.execute(f"CREATE INDEX IF NOT EXISTS idx_movies_vector_{idx} ON movies(search_vector);")
                await db.commit()
            
        logger.info("⚡ Live 5-Engine Storage Clusters successfully mounted and synchronized absolutely.")

    @staticmethod
    async def register_user(user_id: str, username: str, referrer_id: str = None):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            today = str(datetime.now().date())
            async with db.execute("SELECT user_id, banned, verified FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    if row[1] == 1: return "BANNED"
                    await DatabaseManager.verify_daily_reset(user_id)
                    return False
            
            await db.execute("""
                INSERT INTO users (user_id, username, plan, searches_today, max_limit, referral_count, referred_by, last_reset_date, banned, premium_expiry, verified)
                VALUES (?, ?, 'Free', 0, 5, 0, ?, ?, 0, 'Never', 0)
            """, (user_id, username, referrer_id, today))
            await db.commit()
            return True

    @staticmethod
    async def set_verified(user_id: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    @staticmethod
    async def apply_referral_credit(referrer_id: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE users SET max_limit = max_limit + 5, referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
            await db.commit()

    @staticmethod
    async def get_user(user_id: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    await DatabaseManager.verify_daily_reset(user_id)
                    await DatabaseManager.check_premium_expiry(user_id)
                    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as fresh_cursor:
                        res = await fresh_cursor.fetchone()
                        return dict(res) if res else None
                return None

    @staticmethod
    async def verify_daily_reset(user_id: str):
        today = str(datetime.now().date())
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            async with db.execute("SELECT last_reset_date, plan FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != today:
                    base_limit = 5
                    if row[1] == 'Silver': base_limit = 30
                    elif row[1] == 'Gold': base_limit = 60
                    elif row[1] == 'Elite': base_limit = 300
                    await db.execute("UPDATE users SET searches_today = 0, last_reset_date = ?, max_limit = MAX(max_limit, ?) WHERE user_id = ?", (today, base_limit, user_id))
                    await db.commit()

    @staticmethod
    async def check_premium_expiry(user_id: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            async with db.execute("SELECT plan, premium_expiry FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != 'Free' and row[1] != 'Never':
                    try:
                        expiry = datetime.strptime(row[1], "%Y-%m-%d").date()
                        if datetime.now().date() > expiry:
                            await db.execute("UPDATE users SET plan = 'Free', max_limit = 5, premium_expiry = 'Never' WHERE user_id = ?", (user_id,))
                            await db.commit()
                    except Exception: 
                        pass

    @staticmethod
    async def increment_search(user_id: str):
        if int(user_id) == ADMIN_ID: return
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE users SET searches_today = searches_today + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    @staticmethod
    async def update_premium_plan(user_id: str, plan_name: str, allocated_limit: int, duration_days: int = 30):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            expiry_str = 'Never' if plan_name == 'Free' else str((datetime.now() + timedelta(days=duration_days)).date())
            await db.execute("UPDATE users SET plan = ?, max_limit = MAX(max_limit, ?), premium_expiry = ? WHERE user_id = ?", (plan_name, allocated_limit, expiry_str, user_id))
            await db.commit()

    @staticmethod
    async def update_user_reward(user_id: str, added_quota: int, timestamp_str: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE users SET max_limit = max_limit + ?, last_reward_time = ? WHERE user_id = ?", (added_quota, timestamp_str, user_id))
            await db.commit()

    @staticmethod
    async def log_payment_attempt(user_id: str, plan_name: str, price: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("INSERT INTO payments (user_id, plan_name, price, status, timestamp) VALUES (?, ?, ?, 'Pending', ?)", (user_id, plan_name, price, now_str))
            await db.commit()

    @staticmethod
    async def update_payment_status(user_id: str, plan_name: str, status: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE payments SET status = ? WHERE user_id = ? AND plan_name = ? AND status = 'Pending'", (status, user_id, plan_name))
            await db.commit()

    @staticmethod
    async def create_coupon(code: str, quota: int, max_uses: int, expiry_days: int = 365):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            exp_str = str((datetime.now() + timedelta(days=expiry_days)).date())
            await db.execute("""
                INSERT OR REPLACE INTO coupons (code, quota_reward, max_uses, current_uses, expiry_date)
                VALUES (?, ?, ?, 0, ?)
            """, (code, quota, max_uses, exp_str))
            await db.commit()

    @staticmethod
    async def redeem_coupon(user_id: str, code: str):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM coupons WHERE code = ?", (code,)) as cursor:
                coupon = await cursor.fetchone()
                if not coupon: return "INVALID"
                
            today = datetime.now().date()
            if coupon['expiry_date']:
                try:
                    if datetime.strptime(coupon['expiry_date'], "%Y-%m-%d").date() < today:
                        return "EXPIRED"
                except Exception: 
                    pass
                
            if coupon['current_uses'] >= coupon['max_uses']:
                return "MAXED"
                
            async with db.execute("SELECT * FROM coupon_logs WHERE user_id = ? AND code = ?", (user_id, code)) as log_c:
                if await log_c.fetchone(): return "ALREADY_USED"
                
            await db.execute("INSERT INTO coupon_logs (user_id, code, timestamp) VALUES (?, ?, ?)", (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await db.execute("UPDATE coupons SET current_uses = current_uses + 1 WHERE code = ?", (code,))
            await db.execute("UPDATE users SET max_limit = max_limit + ? WHERE user_id = ?", (coupon['quota_reward'], user_id))
            await db.commit()
            return coupon['quota_reward']

    @staticmethod
    async def cache_movie(msg_id: int, name: str, size: int, source_channel: int):
        # Normalize comparison logic to string to circumvent any integer mismatch bugs
        str_src = str(source_channel)
        if str_src == str(CHANNEL_A_ID): target_db = ABS_DB_ENGINE_A
        elif str_src == str(CHANNEL_B_ID): target_db = ABS_DB_ENGINE_B
        elif str_src == str(CHANNEL_C_ID): target_db = ABS_DB_ENGINE_C
        elif str_src == str(CHANNEL_D_ID): target_db = ABS_DB_ENGINE_D
        elif str_src == str(CHANNEL_E_ID): target_db = ABS_DB_ENGINE_E
        else:
            logger.warning(f"⚠️ Unmapped source channel payload encountered: {source_channel}")
            return None 
        
        async with aiosqlite.connect(target_db) as db:
            vector = clean_string(name)
            await db.execute("""
                INSERT OR REPLACE INTO movies (msg_id, file_name, file_size, search_vector, search_count)
                VALUES (?, ?, ?, ?, COALESCE((SELECT search_count FROM movies WHERE msg_id = ?), 0))
            """, (msg_id, name, size, vector, msg_id))
            await db.commit()
        logger.info(f"📥 File captured successfully! Written inside structural node: {os.path.basename(target_db)}")
        return target_db

    @staticmethod
    async def query_movie_catalog(query_string: str):
        async def search_in_db(db_path):
            if not os.path.exists(db_path):
                return []
            try:
                async with aiosqlite.connect(db_path) as db:
                    db.row_factory = aiosqlite.Row
                    clean_input = clean_string(query_string)
                    tokens = [t for t in clean_input.split() if len(t) > 1] or [clean_input]
                    
                    # FIX: Change OR matrix into strict multi-token AND matching to beat boundary truncations
                    sql_conditions = ["(file_name LIKE ? OR search_vector LIKE ?)" for _ in tokens[:4]]
                    sql_parameters = []
                    for token in tokens[:4]:
                        sql_parameters.extend([f"%{token}%", f"%{token}%"])
                    
                    if not sql_conditions: return []
                    query = f"SELECT * FROM movies WHERE {' AND '.join(sql_conditions)} LIMIT 150"
                    async with db.execute(query, sql_parameters) as cursor:
                        rows = await cursor.fetchall()
                    
                    subset = []
                    for row in rows:
                        score = max(calculate_similarity(query_string, row['file_name']), calculate_similarity(query_string, row['search_vector'] or ""))
                        # FIX: Added an inclusion fallback to catch tag variants with poor formula confidence calculations
                        if score >= 0.22 or clean_input in clean_string(row['file_name']):
                            subset.append((score, dict(row), db_path))
                    return subset
            except Exception as e:
                logger.error(f"Error querying cluster node {db_path}: {e}")
                return []

        # Gather results in parallel using our absolute path engine mappings
        db_engines = [ABS_DB_ENGINE_A, ABS_DB_ENGINE_B, ABS_DB_ENGINE_C, ABS_DB_ENGINE_D, ABS_DB_ENGINE_E]
        tasks = [search_in_db(db) for db in db_engines]
        grouped_results = await asyncio.gather(*tasks)
        
        results = []
        for subset in grouped_results:
            results.extend(subset)
            
        results.sort(key=lambda x: x[0], reverse=True)
        return [dict(item, origin_db=origin) for score, item, origin in results]

    @staticmethod
    async def increment_movie_download(msg_id: int, origin_db: str):
        async with aiosqlite.connect(origin_db) as db:
            await db.execute("UPDATE movies SET search_count = search_count + 1 WHERE msg_id = ?", (msg_id,))
            await db.commit()

    @staticmethod
    async def get_system_stats():
        async with aiosqlite.connect(ABS_DB_CORE) as db_core:
            async with db_core.execute("SELECT COUNT(*) FROM users") as c1: total_u = (await c1.fetchone())[0]
            async with db_core.execute("SELECT COUNT(*) FROM users WHERE banned = 1") as c2: ban_u = (await c2.fetchone())[0]
            async with db_core.execute("SELECT COUNT(*) FROM payments WHERE status = 'Pending'") as c3: pend_p = (await c3.fetchone())[0]
            async with db_core.execute("SELECT COUNT(*) FROM users WHERE plan != 'Free'") as c4: prem_u = (await c4.fetchone())[0]
            
        async with aiosqlite.connect(ABS_DB_ENGINE_A) as db_a:
            async with db_a.execute("SELECT COUNT(*) FROM movies") as c5: movies_a = (await c5.fetchone())[0]
        async with aiosqlite.connect(ABS_DB_ENGINE_B) as db_b:
            async with db_b.execute("SELECT COUNT(*) FROM movies") as c6: movies_b = (await c6.fetchone())[0]
        async with aiosqlite.connect(ABS_DB_ENGINE_C) as db_c:
            async with db_c.execute("SELECT COUNT(*) FROM movies") as c7: movies_c = (await c7.fetchone())[0]
        async with aiosqlite.connect(ABS_DB_ENGINE_D) as db_d:
            async with db_d.execute("SELECT COUNT(*) FROM movies") as c8: movies_d = (await c8.fetchone())[0]
        async with aiosqlite.connect(ABS_DB_ENGINE_E) as db_e:
            async with db_e.execute("SELECT COUNT(*) FROM movies") as c9: movies_e = (await c9.fetchone())[0]
            
        return total_u, movies_a, movies_b, movies_c, movies_d, movies_e, ban_u, pend_p, prem_u

    @staticmethod
    async def set_user_ban_status(user_id: str, status: int):
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (status, user_id))
            await db.commit()

    @staticmethod
    async def reset_all_daily_quotas():
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            await db.execute("UPDATE users SET searches_today = 0")
            await db.commit()

    @staticmethod
    async def get_all_user_ids():
        async with aiosqlite.connect(ABS_DB_CORE) as db:
            async with db.execute("SELECT user_id FROM users WHERE banned = 0") as cursor:
                return [r[0] for r in await cursor.fetchall()]
