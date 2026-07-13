import os
import re
import json
import io
import logging
import asyncio
import random
import sqlite3
import datetime
from datetime import datetime, timedelta
import aiosqlite
import telethon
from telethon import TelegramClient, events, functions, types, Button
from telethon.errors import FloodWaitError

# --- 🔍 FUZZY MATCHING LOGIC & STRING UTILS 🔍 ---
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

def format_size(bytes_size):
    if not bytes_size: return "Unknown Size"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

# --- 📝 LOGGING FRAMEWORK 📝 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_runtime.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MovieQuadEngineBot")

# ====================================================================
#              ⚙️ HARDCODED PRODUCTION VALUES & PATHS
# ====================================================================
API_ID = 35485985              
API_HASH = '5441c09a9c8bf58374e1f8f227b95794'     
BOT_TOKEN = '8791980160:AAGU4JwkQXL1dxgRqVUxgeARJROwLfL19g4'   
ADMIN_ID = 7952327997                 

REQUIRED_CHANNELS = [
    {"id": -1003985304953, "link": "https://t.me/yagamicorporation"},
]       

LOG_CHANNEL_ID = -1003559645437
LOG_CHANNEL_INVITE = "https://t.me/+szJCMQ1z5d0wNTdl"

CHANNEL_A_ID = -1002107962104
CHANNEL_B_ID = -1003943845412
CHANNEL_C_ID = -1002488275573
CHANNEL_D_ID = -1002296093247
CHANNEL_E_ID = -1002394593898

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_CORE = os.path.join(SCRIPT_DIR, "alldata.db")             
DB_ENGINE_A = os.path.join(SCRIPT_DIR, "sourcechannel.db")     
DB_ENGINE_B = os.path.join(SCRIPT_DIR, "animehubinfinite.db")  
DB_ENGINE_C = os.path.join(SCRIPT_DIR, "ritsamhub1.db")  
DB_ENGINE_D = os.path.join(SCRIPT_DIR, "ritsamhub3.db")  
DB_ENGINE_E = os.path.join(SCRIPT_DIR, "ritsamhub48.db")  

client = TelegramClient('movie_quad_session', API_ID, API_HASH, receive_updates=False)

PAGINATION_CACHE = {}
BACKUP_ABORT_SIGNAL = {"abort": False}
CAPTCHA_SESSIONS = {}
COUPON_INPUT_STATE = set()

CAPTCHA_POOL = [
    {"q": "8 * 1", "a": "8"},
    {"q": "12 / 4", "a": "3"},
    {"q": "9 + 5", "a": "14"},
    {"q": "15 - 7", "a": "8"},
    {"q": "6 * 2", "a": "12"},
    {"q": "20 / 5", "a": "4"},
    {"q": "14 + 6", "a": "20"},
    {"q": "18 - 9", "a": "9"},
    {"q": "7 * 3", "a": "21"},
    {"q": "16 / 2", "a": "8"}
]

def update_filesystem_heartbeat(status_message):
    try:
        progress_path = os.path.join(SCRIPT_DIR, "progress.txt")
        with open(progress_path, "w", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {status_message}\n")
    except Exception as e:
        logger.error(f"Failed to update progress filesystem metrics: {e}")

async def dispatch_log(text):
    try:
        await client.send_message(LOG_CHANNEL_ID, f"📢 **SYSTEM AUDIT LOG**\n⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{text}")
    except Exception as e:
        logger.error(f"Failed dispatching audit stream to log channel: {e}")

# ====================================================================
#                   🗄️ QUAD DATABASE MANAGEMENT ENGINE
# ====================================================================
class DatabaseManager:
    @staticmethod
    async def initialize():
        update_filesystem_heartbeat("Initializing Cluster Core Storage Map")
        async with aiosqlite.connect(DB_CORE) as db:
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
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    val TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS coupons (
                    code TEXT PRIMARY KEY,
                    max_uses INTEGER,
                    current_uses INTEGER DEFAULT 0,
                    quota_reward INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS coupon_history (
                    user_id TEXT,
                    code TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (user_id, code)
                )
            """)
            
            # Seed configurations
            configs = [
                ('price_Silver', '29'), ('price_Gold', '49'), ('price_Elite', '149'),
                ('limit_Free', '5'), ('limit_Silver', '30'), ('limit_Gold', '60'), ('limit_Elite', '300')
            ]
            for k, v in configs:
                await db.execute("INSERT OR IGNORE INTO system_config (key, val) VALUES (?, ?)", (k, v))
                
            await db.commit()

        channel_dbs = [DB_ENGINE_A, DB_ENGINE_B, DB_ENGINE_C, DB_ENGINE_D, DB_ENGINE_E]
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
            
        logger.info("⚡ Live 5-Engine Storage Clusters successfully mounted and fully synchronized.")
        update_filesystem_heartbeat("Databases Mount Completed Successfully")

    @staticmethod
    async def get_config(key: str, default: str) -> str:
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT val FROM system_config WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default

    @staticmethod
    async def set_config(key: str, val: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("INSERT OR REPLACE INTO system_config (key, val) VALUES (?, ?)", (key, val))
            await db.commit()

    @staticmethod
    async def register_user(user_id: str, username: str, referrer_id: str = None):
        async with aiosqlite.connect(DB_CORE) as db:
            today = str(datetime.now().date())
            async with db.execute("SELECT user_id, banned, verified FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    if row[1] == 1: return "BANNED"
                    await DatabaseManager.verify_daily_reset(user_id)
                    return False
            
            free_baseline = int(await DatabaseManager.get_config('limit_Free', '5'))
            await db.execute("""
                INSERT INTO users (user_id, username, plan, searches_today, max_limit, referral_count, referred_by, last_reset_date, banned, premium_expiry, verified)
                VALUES (?, ?, 'Free', 0, ?, 0, ?, ?, 0, 'Never', 0)
            """, (user_id, username, free_baseline, referrer_id, today))
            if referrer_id:
                await db.execute("UPDATE users SET max_limit = max_limit + 5, referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
            await db.commit()
            return True

    @staticmethod
    async def verify_user_captcha(user_id: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    @staticmethod
    async def get_user(user_id: str):
        async with aiosqlite.connect(DB_CORE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    await DatabaseManager.verify_daily_reset(user_id)
                    await DatabaseManager.check_premium_expiry(user_id)
                    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as fresh_cursor:
                        return await fresh_cursor.fetchone()
                return None

    @staticmethod
    async def verify_daily_reset(user_id: str):
        today = str(datetime.now().date())
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT last_reset_date, plan FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != today:
                    plan = row[1]
                    base_limit = int(await DatabaseManager.get_config(f'limit_{plan}', '5'))
                    await db.execute("UPDATE users SET searches_today = 0, last_reset_date = ?, max_limit = MAX(max_limit, ?) WHERE user_id = ?", (today, base_limit, user_id))
                    await db.commit()

    @staticmethod
    async def check_premium_expiry(user_id: str):
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT plan, premium_expiry FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != 'Free' and row[1] != 'Never':
                    try:
                        expiry = datetime.strptime(row[1], "%Y-%m-%d").date()
                        if datetime.now().date() > expiry:
                            free_baseline = int(await DatabaseManager.get_config('limit_Free', '5'))
                            await db.execute("UPDATE users SET plan = 'Free', max_limit = ?, premium_expiry = 'Never' WHERE user_id = ?", (free_baseline, user_id))
                            await db.commit()
                            await dispatch_log(f"📉 **Plan Expired**: User `{user_id}` reverted back to Free rank.")
                    except Exception: pass

    @staticmethod
    async def increment_search(user_id: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET searches_today = searches_today + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    @staticmethod
    async def update_premium_plan(user_id: str, plan_name: str, allocated_limit: int, duration_days: int = 30):
        async with aiosqlite.connect(DB_CORE) as db:
            expiry_str = 'Never' if plan_name == 'Free' else str((datetime.now() + timedelta(days=duration_days)).date())
            await db.execute("UPDATE users SET plan = ?, max_limit = MAX(max_limit, ?), premium_expiry = ? WHERE user_id = ?", (plan_name, allocated_limit, expiry_str, user_id))
            await db.commit()

    @staticmethod
    async def update_user_reward(user_id: str, added_quota: int, timestamp_str: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET max_limit = max_limit + ?, last_reward_time = ? WHERE user_id = ?", (added_quota, timestamp_str, user_id))
            await db.commit()

    @staticmethod
    async def log_payment_attempt(user_id: str, plan_name: str, price: str):
        async with aiosqlite.connect(DB_CORE) as db:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("INSERT INTO payments (user_id, plan_name, price, status, timestamp) VALUES (?, ?, ?, 'Pending', ?)", (user_id, plan_name, price, now_str))
            await db.commit()

    @staticmethod
    async def update_payment_status(user_id: str, plan_name: str, status: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE payments SET status = ? WHERE user_id = ? AND plan_name = ? AND status = 'Pending'", (status, user_id, plan_name))
            await db.commit()

    @staticmethod
    async def cache_movie(msg_id: int, name: str, size: int, source_channel: int):
        if source_channel == CHANNEL_A_ID: target_db = DB_ENGINE_A
        elif source_channel == CHANNEL_B_ID: target_db = DB_ENGINE_B
        elif source_channel == CHANNEL_C_ID: target_db = DB_ENGINE_C
        elif source_channel == CHANNEL_D_ID: target_db = DB_ENGINE_D
        elif source_channel == CHANNEL_E_ID: target_db = DB_ENGINE_E
        else: return None 
        
        async with aiosqlite.connect(target_db) as db:
            vector = clean_string(name)
            await db.execute("""
                INSERT OR REPLACE INTO movies (msg_id, file_name, file_size, search_vector, search_count)
                VALUES (?, ?, ?, ?, COALESCE((SELECT search_count FROM movies WHERE msg_id = ?), 0))
            """, (msg_id, name, size, vector, msg_id))
            await db.commit()
        return target_db

    @staticmethod
    async def query_movie_catalog(query_string: str):
        async def search_in_db(db_path):
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                clean_input = clean_string(query_string)
                tokens = [t for t in clean_input.split() if len(t) > 1] or [clean_input]
                
                sql_conditions = ["(file_name LIKE ? OR search_vector LIKE ?)" for _ in tokens[:3]]
                sql_parameters = []
                for token in tokens[:3]:
                    sql_parameters.extend([f"%{token}%", f"%{token}%"])
                
                if not sql_conditions: return []
                query = f"SELECT * FROM movies WHERE {' OR '.join(sql_conditions)} LIMIT 150"
                async with db.execute(query, sql_parameters) as cursor:
                    rows = await cursor.fetchall()
                
                subset = []
                for row in rows:
                    score = max(calculate_similarity(query_string, row['file_name']), calculate_similarity(query_string, row['search_vector'] or ""))
                    if score >= 0.32:
                        subset.append((score, dict(row), db_path))
                return subset

        results = []
        for db_engine in [DB_ENGINE_A, DB_ENGINE_B, DB_ENGINE_C, DB_ENGINE_D, DB_ENGINE_E]:
            results.extend(await search_in_db(db_engine))
            
        results.sort(key=lambda x: x[0], reverse=True)
        return [dict(item, origin_db=origin) for score, item, origin in results]

    @staticmethod
    async def get_trending_movies():
        trending_pool = []
        for db_engine in [DB_ENGINE_A, DB_ENGINE_B, DB_ENGINE_C, DB_ENGINE_D, DB_ENGINE_E]:
            async with aiosqlite.connect(db_engine) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM movies WHERE search_count > 0 ORDER BY search_count DESC LIMIT 3") as cursor:
                    for r in await cursor.fetchall():
                        trending_pool.append(dict(r, origin_db=db_engine))
        trending_pool.sort(key=lambda x: x['search_count'], reverse=True)
        return trending_pool[:5]

    @staticmethod
    async def increment_movie_download(msg_id: int, origin_db: str):
        async with aiosqlite.connect(origin_db) as db:
            await db.execute("UPDATE movies SET search_count = search_count + 1 WHERE msg_id = ?", (msg_id,))
            await db.commit()

    @staticmethod
    async def get_system_stats():
        async with aiosqlite.connect(DB_CORE) as db_core:
            async with db_core.execute("SELECT COUNT(*) FROM users") as c1: total_u = (await c1.fetchone())[0]
            async with db_core.execute("SELECT COUNT(*) FROM users WHERE banned = 1") as c2: ban_u = (await c2.fetchone())[0]
            async with db_core.execute("SELECT COUNT(*) FROM payments WHERE status = 'Pending'") as c3: pend_p = (await c3.fetchone())[0]
            async with db_core.execute("SELECT COUNT(*) FROM users WHERE plan != 'Free'") as c4: prem_u = (await c4.fetchone())[0]
            
        async with aiosqlite.connect(DB_ENGINE_A) as db_a:
            async with db_a.execute("SELECT COUNT(*) FROM movies") as c5: movies_a = (await c5.fetchone())[0]
        async with aiosqlite.connect(DB_ENGINE_B) as db_b:
            async with db_b.execute("SELECT COUNT(*) FROM movies") as c6: movies_b = (await c6.fetchone())[0]
        async with aiosqlite.connect(DB_ENGINE_C) as db_c:
            async with db_c.execute("SELECT COUNT(*) FROM movies") as c7: movies_c = (await c7.fetchone())[0]
        async with aiosqlite.connect(DB_ENGINE_D) as db_d:
            async with db_d.execute("SELECT COUNT(*) FROM movies") as c8: movies_d = (await c8.fetchone())[0]
        async with aiosqlite.connect(DB_ENGINE_E) as db_e:
            async with db_e.execute("SELECT COUNT(*) FROM movies") as c9: movies_e = (await c9.fetchone())[0]
            
        return total_u, movies_a, movies_b, movies_c, movies_d, movies_e, ban_u, pend_p, prem_u

    @staticmethod
    async def get_top_referrers():
        async with aiosqlite.connect(DB_CORE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT username, user_id, referral_count FROM users ORDER BY referral_count DESC LIMIT 5") as cursor:
                return await cursor.fetchall()

    @staticmethod
    async def set_user_ban_status(user_id: str, status: int):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (status, user_id))
            await db.commit()

    @staticmethod
    async def reset_all_daily_quotas():
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET searches_today = 0")
            await db.commit()

    @staticmethod
    async def get_all_user_ids():
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT user_id FROM users WHERE banned = 0") as cursor:
                return [r[0] for r in await cursor.fetchall()]

async def check_membership(user_id: int) -> bool:
    for ch in REQUIRED_CHANNELS:
        try:
            await client(functions.channels.GetParticipantRequest(channel=ch['id'], participant=user_id))
        except Exception:
            return False
    return True

async def scheduled_file_destruction(chat_id, raw_file_msg, alert_notice_msg):
    await asyncio.sleep(60)
    try:
        await client.delete_messages(chat_id, [raw_file_msg.id, alert_notice_msg.id])
    except Exception:
        pass

# ====================================================================
#                      🤖 USER CONTROLLER COMMANDS
# ====================================================================
def build_main_keyboard():
    return [
        ['🔍 Search Movies', '👥 Invite Friends'],
        ['🛒 Buy Premium', '🎫 Redeem Token'],
        ['👤 View Profile', '📖 Instruction Guide']
    ]

@client.on(events.NewMessage(pattern='/start'))
async def on_start_command(event):
    user_id = str(event.sender_id)
    username = event.sender.username or "Anonymous"
    payload = event.message.message.split(' ')
    referrer_id = payload[1] if len(payload) > 1 and payload[1].isdigit() else None
    if referrer_id == user_id: referrer_id = None
        
    reg_status = await DatabaseManager.register_user(user_id, username, referrer_id)
    if reg_status == "BANNED":
        await event.reply("⚠️ *Access Denied: Your account configuration profile is locked down.*")
        return
    
    user_data = await DatabaseManager.get_user(user_id)
    if user_data and user_data['verified'] == 0:
        captcha_obj = random.choice(CAPTCHA_POOL)
        CAPTCHA_SESSIONS[user_id] = captcha_obj['a']
        await event.reply(
            f"🛡️ **SECURITY GATEWAY INTEGRITY VERIFICATION**\n\n"
            f"Solve the mathematical matrix task expression below to unlock full client options:\n"
            f"👉 **Question**: `{captcha_obj['q']} = ?`",
            parse_mode='markdown'
        )
        return

    if reg_status and referrer_id:
        try: 
            await client.send_message(int(referrer_id), f"🔔 *Referral Event!*\n\nA new node registered via your affiliate link.\n➕5 Token Limits permanently credited!")
            await dispatch_log(f"👥 **Referral Chain Linked**: User `{user_id}` joined under Referrer `{referrer_id}`.")
        except Exception: pass
    elif reg_status:
        await dispatch_log(f"🆕 **Organic Node Entry**: User `{user_id}` (@{username}) logged into CORE system storage.")

    await show_dashboard(event.chat_id, user_id)

async def show_dashboard(chat_id, user_id):
    user_data = await DatabaseManager.get_user(user_id)
    dashboard_ui = (
        f"💎 **ULTIMATE SYSTEM HUBCONSOLE v3.0** 💎\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎖️ **Tier Privilege Status** : 👑 `{user_data['plan']}`\n"
        f"📊 **Usage Token Loadout**: ⚡ `{user_data['searches_today']}` / `{user_data['max_limit']}` Allocations\n"
        f"⏳ **Limit Resets**: 🔄 Automatic Daily Refresh Control Sequence\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **Dynamic Actions Ready**: Interact with the Control Matrix Keyboard underneath."
    )
    await client.send_message(chat_id, dashboard_ui, buttons=build_main_keyboard(), parse_mode='markdown')

# ====================================================================
#                   ⚡ TEXT MATRIX KEYBOARD INTERCEPTOR
# ====================================================================
@client.on(events.NewMessage)
async def keyboard_text_router(event):
    if not event.text or event.text.startswith('/'): return
    user_id = str(event.sender_id)
    
    # Captcha interception check
    if user_id in CAPTCHA_SESSIONS:
        expected = CAPTCHA_SESSIONS[user_id]
        if event.text.strip() == expected:
            del CAPTCHA_SESSIONS[user_id]
            await DatabaseManager.verify_user_captcha(user_id)
            await event.reply("✅ **Verification Passed Successfully!** Access initialized.")
            await show_dashboard(event.chat_id, user_id)
        else:
            captcha_obj = random.choice(CAPTCHA_POOL)
            CAPTCHA_SESSIONS[user_id] = captcha_obj['a']
            await event.reply(f"❌ **Incorrect Verification Matrix!** Try again:\n👉 **Question**: `{captcha_obj['q']} = ?`")
        return

    user_data = await DatabaseManager.get_user(user_id)
    if not user_data: return
    if user_data['banned'] == 1: return
    if user_data['verified'] == 0: return

    # Coupon entry interceptor logic
    if user_id in COUPON_INPUT_STATE:
        COUPON_INPUT_STATE.remove(user_id)
        entered_code = event.text.strip()
        
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT max_uses, current_uses, quota_reward FROM coupons WHERE code = ?", (entered_code,)) as c:
                coupon = await c.fetchone()
                
            if not coupon:
                await event.reply("❌ **Invalid Token / Coupon Code Structure. Transaction aborted.**")
                return
                
            max_u, curr_u, reward = coupon
            if curr_u >= max_u:
                await event.reply("⏳ **This coupon code allocation ceiling has expired.**")
                await dispatch_log(f"⚠️ **Expired Coupon Attempt**: User `{user_id}` hit dead code `{entered_code}`.")
                return
                
            async with db.execute("SELECT 1 FROM coupon_history WHERE user_id = ? AND code = ?", (user_id, entered_code)) as h:
                if await h.fetchone():
                    await event.reply("🔒 **Identity Validation Error: You have already redeemed this promo block resource node.**")
                    return
                    
            # Process redeem action
            await db.execute("UPDATE coupons SET current_uses = current_uses + 1 WHERE code = ?", (entered_code,))
            await db.execute("INSERT INTO coupon_history (user_id, code, timestamp) VALUES (?, ?, ?)", (user_id, entered_code, datetime.now().isoformat()))
            await db.commit()
            
            await DatabaseManager.update_user_reward(user_id, reward, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            await event.reply(f"🎉 **Coupon Code Redeemed Successfully!**\n⚡ `+{reward}` Search tokens permanently injected into your core profile layer capacity!")
            await dispatch_log(f"🎫 **Coupon Redeemed**: User `{user_id}` optimized profile using coupon `{entered_code}` (+{reward} capacity).")
            return

    # Native control route redirection
    selection = event.text
    if selection == '🔍 Search Movies':
        await event.reply("💡 **Catalog Search Prompt**: Simply send your clear search keyword text phrase right into this layout console space container!")
        
    elif selection == '👥 Invite Friends':
        bot_identity = await client.get_me()
        ref_link = f"https://t.me/{bot_identity.username}?start={user_id}"
        invite_ui = (
            f"🤝 **AFFILIATE TRACK & NODE REVENUE INTERFACE**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 Share your structural node access entry point string with colleagues:\n"
            f"`{ref_link}`\n\n"
            f"🎁 Earn **+5 Search limits** instantly inside system core parameters for each validated user registration pass."
        )
        await event.reply(invite_ui, parse_mode='markdown')

    elif selection == '🛒 Buy Premium':
        s_price = await DatabaseManager.get_config('price_Silver', '29')
        g_price = await DatabaseManager.get_config('price_Gold', '49')
        e_price = await DatabaseManager.get_config('price_Elite', '149')
        
        upgrade_ui = (
            f"💎 **PREMIUM ALLOCATION TIERS & SERVICE passes**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🥈 **Silver Pass Variant Bundle**\n"
            f"💰 Investment Value: `₹{s_price} INR` / `50 Telegram Stars` per 30 Days\n\n"
            f"🥇 **Gold Pass Variant Bundle**\n"
            f"💰 Investment Value: `₹{g_price} INR` / `100 Telegram Stars` per 30 Days\n\n"
            f"👑 **Elite Mega Pass Bundle**\n"
            f"💰 Investment Value: `₹{e_price} INR` / `250 Telegram Stars` per 30 Days\n"
        )
        buttons = [
            [Button.inline(f"🥈 Silver (₹{s_price})", f"pay_Silver_{s_price}"), Button.inline("⭐️ Silver (50★)", b"stars_Silver_50")],
            [Button.inline(f"🥇 Gold (₹{g_price})", f"pay_Gold_{g_price}"), Button.inline("⭐️ Gold (100★)", b"stars_Gold_100")],
            [Button.inline(f"👑 Elite (₹{e_price})", f"pay_Elite_{e_price}"), Button.inline("⭐️ Elite (250★)", b"stars_Elite_250")]
        ]
        await event.reply(upgrade_ui, buttons=buttons, parse_mode='markdown')

    elif selection == '🎫 Redeem Token':
        # Fetch last structural execution token code entry parameters for safety confirmation metrics
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT code, timestamp FROM coupon_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,)) as c:
                last_node = await c.fetchone()
        
        history_str = f"`{last_node[0]}` (Executed: {last_node[1]})" if last_node else "_No historical coupon transactions located._"
        COUPON_INPUT_STATE.add(user_id)
        await event.reply(
            f"🎫 **PROMO RESOURCE COUPON FORGE PIPELINE**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏮️ **Last Verified Action**: {history_str}\n\n"
            f"✍️ **Action Required**: Please write/input your alphanumeric token sequence key here down below now:"
        )

    elif selection == '👤 View Profile':
        profile_ui = (
            f"👤 **USER STRUCTURAL METRICS PROFILED**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 **Unique Reference Key ID** : `{user_id}`\n"
            f"🏅 **System Priority Rank**   : `★ {user_data['plan']} Plan Tier`\n"
            f"⚡ **Token Performance Density**: `{user_data['searches_today']}` / `{user_data['max_limit']}` Loads Exhausted\n"
            f"🤝 **Affiliate Vector Connections**: `{user_data['referral_count']}` Node Links\n"
            f"⏳ **Subscription End Line**  : `{user_data['premium_expiry']}`"
        )
        await event.reply(profile_ui, parse_mode='markdown')

    elif selection == '📖 Instruction Guide':
        guide_ui = (
            f"📖 **OPERATIONAL BLUEPRINT ENGINE USER GUIDE**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"1️⃣ Input explicit movie phrases inside global channel search space inputs.\n"
            f"2️⃣ Trigger pagination navigational grids instantly using inline interfaces.\n"
            f"3️⃣ Download operations stream direct system payloads seamlessly on demand.\n"
            f"4️⃣ Internal media items execute cloud cache automated elimination rules inside 60 seconds."
        )
        await event.reply(guide_ui, parse_mode='markdown')

# ====================================================================
#                   🎛️ INTERACTIVE UI CALLBACK ROUTER
# ====================================================================
@client.on(events.CallbackQuery)
async def on_interactive_callback(event):
    action = event.data
    user_id = str(event.sender_id)
    user_data = await DatabaseManager.get_user(user_id)
    
    if user_data and user_data['banned'] == 1:
        await event.answer("⚠️ Session Terminated.", alert=True)
        return
        
    if action.startswith(b'stars_'):
        _, tier, stars_cost = action.decode('utf-8').split('_')
        stars_ui = (
            f"⭐ **TELEGRAM STARS SECURE INBOUND PAYMENT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Selected Plan Package**: `{tier} Account Tier Upgrade`\n"
            f"💰 **Total Asset Value**     : `{stars_cost} Telegram Stars`\n\n"
            f"👉 Click the secure button below to route into **@Gopalji_chouney**. "
            f"Send the specified number of stars and attach a confirmation screenshot to trigger manual validation pipelines! 🎉"
        )
        buttons = [
            [Button.url("💬 Send Stars to Admin", "https://t.me/Gopalji_chouney")]
        ]
        await event.edit(stars_ui, buttons=buttons, parse_mode='markdown')

    elif action.startswith(b'pay_'):
        _, plan, price = action.decode('utf-8').split('_')
        target_merchant_upi = "8368680967@fam"  
        payload = f"upi://pay?pa={target_merchant_upi}&pn=MovieEngineHub&am={price}&cu=INR&tn=Pay_{plan}_{user_id}"
        
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(payload)
            qr.make(fit=True)
            bio = io.BytesIO()
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(bio, format="PNG")
            bio.seek(0)
            bio.name = "payment_qr.png"
            
            await DatabaseManager.log_payment_attempt(user_id, plan, price)
            await event.delete()
            
            await client.send_file(
                event.chat_id, file=bio,
                caption=f"📲 **DYNAMIC INTEGRATED UPI INBOUND GATEWAY**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🏅 **Target Tier Pass**: `{plan} Premium Access Bundle` \n"
                        f"💰 **Transaction Fee**  : `₹{price} INR` \n\n"
                        f"🤳 Scan the matrix payload image above with your payment app. Once paid, **REPLY** to this image message container with your confirmation screenshot!"
            )
        except ModuleNotFoundError:
            await event.reply(
                "⚠️ **UPI Dynamic Asset Engine Failure.**\n"
                "Please run `pip install qrcode pillow` on the deployment machine to render instant image structures.\n\n"
                f"Alternative raw payload copy variant string:\n`{payload}`"
            )

    elif action.startswith(b'get_file_'):
        parsed_args = action.decode('utf-8').split('_')
        db_flag = parsed_args[2]
        msg_id = int(parsed_args[3])
        
        if user_data['searches_today'] >= user_data['max_limit']:
            await event.answer("⚠️ Limit Saturated! Unlock access tiers for more bandwidth.", alert=True)
            return
            
        if db_flag == 'a': target_ch, target_db = CHANNEL_A_ID, DB_ENGINE_A
        elif db_flag == 'b': target_ch, target_db = CHANNEL_B_ID, DB_ENGINE_B
        elif db_flag == 'c': target_ch, target_db = CHANNEL_C_ID, DB_ENGINE_C
        elif db_flag == 'd': target_ch, target_db = CHANNEL_D_ID, DB_ENGINE_D
        else: target_ch, target_db = CHANNEL_E_ID, DB_ENGINE_E
        
        try:
            source_messages = await client.get_messages(target_ch, ids=msg_id)
            if not source_messages or not source_messages.file:
                await event.answer("❌ File source object is missing or deleted from database cluster.", alert=True)
                return

            dispatched_file = await client.send_file(
                event.chat_id, 
                file=source_messages.media, 
                caption=f"🎬 **File Asset**: `{source_messages.file.name or 'Clean Stream Document'}`"
            )
            
            warning_notice = await client.send_message(
                event.chat_id, 
                "⚠️ *SECURE DELETION TIMEOUT TRIGGERED*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⏳ **Notice**: Save/Forward this movie file *anywhere else immediately*. "
                "This file container will self-destruct from this environment in exactly **1 minute** due to cloud cache space optimizations."
            )
            
            await DatabaseManager.increment_search(user_id)
            await DatabaseManager.increment_movie_download(msg_id, target_db)
            await event.answer("📦 File dispatched seamlessly! Auto-destruction sequence engaged.", alert=False)
            
            asyncio.create_task(scheduled_file_destruction(event.chat_id, dispatched_file, warning_notice))
            
        except Exception:
            await event.answer("❌ Stream connection to source channel timed out.", alert=True)

    elif action.startswith(b'page_'):
        _, targeted_p_str = action.decode('utf-8').split('_')
        t_page = int(targeted_p_str)
        if user_id in PAGINATION_CACHE:
            cached_session = PAGINATION_CACHE[user_id]
            cached_session['current_page'] = t_page
            await RenderPaginationView(event, cached_session['query'], cached_session['matches'], t_page)
        else:
            await event.answer("⏳ Session data dropped. Please perform a fresh content request.", alert=True)

    elif action.startswith(b'adm_app_') or action.startswith(b'adm_dec_'):
        p_args = action.decode('utf-8').split('_')
        res, target_uid, pass_tier = p_args[1], p_args[2], p_args[3]
        
        quota = int(await DatabaseManager.get_config(f'limit_{pass_tier}', '30'))
        
        if res == "app":
            await DatabaseManager.update_premium_plan(target_uid, pass_tier, quota, 30)
            await DatabaseManager.update_payment_status(target_uid, pass_tier, "Approved")
            try: await client.send_message(int(target_uid), f"✅ *TRANSACTION VERIFIED SUCCESSFUL!*\nYour profile has been elevated to the premium **{pass_tier} Upgrade Tier Pass**.")
            except Exception: pass
            await event.edit(f"🟢 **RESOLVED**: Verified User `{target_uid}` into `{pass_tier}`.")
            await dispatch_log(f"💰 **Subscription Upgrade Handshake Approved**: User `{target_uid}` assigned rank tier status `{pass_tier}` via Admin confirmation loops.")
        else:
            await DatabaseManager.update_payment_status(target_uid, pass_tier, "Declined")
            try: await client.send_message(int(target_uid), "🔴 *TRANSACTION VERIFICATION AUDIT FAILURE EXCEPTION*")
            except Exception: pass
            await event.edit(f"🔴 **DECLINED**: Blocked order pipeline sequence for user `{target_uid}`.")

# ====================================================================
#               📊 PAGINATION VIEW VISUAL UI RENDER ENGINE
# ====================================================================
async def RenderPaginationView(event, query, matches, page=1):
    items_per_page = 8
    total_m = len(matches)
    total_p = (total_m + items_per_page - 1) // items_per_page
    
    if page < 1: page = 1
    if page > total_p: page = total_p
    
    start = (page - 1) * items_per_page
    end = start + items_per_page
    view_slice = matches[start:end]
    
    catalog_ui = (
        f"📂 **MULTIPLE CROSS-CHANNEL INDEX SERVERS ACTIVE**\n"
        f"━━━━━━━🔍 Catalog Matches 🔍━━━━━━━\n"
        f"🎯 **Query Parameter** : `{query}`\n"
        f"📊 **Located Entities** : `{total_m} Files Linked` | **Page Index**: `{page}` / `{total_p}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Tap a button to forward the file directly:* "
    )
    
    buttons = []
    for row in view_slice:
        sz = format_size(row['file_size'])
        lbl = f"🎬 {row['file_name']} [{sz}]"
        if row['origin_db'] == DB_ENGINE_A: flag = 'a'
        elif row['origin_db'] == DB_ENGINE_B: flag = 'b'
        elif row['origin_db'] == DB_ENGINE_C: flag = 'c'
        elif row['origin_db'] == DB_ENGINE_D: flag = 'd'
        else: flag = 'e'
        
        buttons.append([Button.inline(lbl, f"get_file_{flag}_{row['msg_id']}".encode('utf-8'))])
        
    nav = []
    if page > 1:
        nav.append(Button.inline("⏮️ Previous", f"page_{page-1}".encode('utf-8')))
    if page < total_p:
        nav.append(Button.inline("Next ⏭️", f"page_{page+1}".encode('utf-8')))
        
    if nav: buttons.append(nav)
        
    try:
        if isinstance(event, events.CallbackQuery.Event):
            await event.edit(catalog_ui, buttons=buttons, parse_mode='markdown')
        else:
            await client.send_message(event.chat_id, catalog_ui, buttons=buttons, parse_mode='markdown')
    except telethon.errors.rpcerrorlist.MessageNotModifiedError:
        if isinstance(event, events.CallbackQuery.Event):
            await event.answer("ℹ️ Already displaying this page view.", alert=False)
    except Exception:
        try: await client.send_message(event.chat_id, catalog_ui, buttons=buttons, parse_mode='markdown')
        except Exception: pass

# ====================================================================
#                     🎯 ROUTING & DISPATCH CONTROLLER
# ====================================================================
@client.on(events.NewMessage)
async def core_search_router(event):
    if event.text and event.text.startswith('/'): return

    user_id = str(event.sender_id)
    user_data = await DatabaseManager.get_user(user_id)
    if not user_data or user_data['banned'] == 1 or user_data['verified'] == 0: return
    if user_id in COUPON_INPUT_STATE: return

    # Intercept system dashboard strings to lock search loops out from executing them as film text strings
    if event.text in ['🔍 Search Movies', '👥 Invite Friends', '🛒 Buy Premium', '🎫 Redeem Token', '👤 View Profile', '📖 Instruction Guide']:
        return

    if event.message.photo:
        await client.send_message(
            ADMIN_ID, f"📥 *INBOUND FINANCIAL TRANSACTION RECEIPT AUDIT*\n👤 **User Reference Account**: `{user_id}`",
            file=event.message.photo,
            buttons=[
                [Button.inline("🥈 Verify Silver", f"adm_app_{user_id}_Silver"), Button.inline("🥇 Verify Gold", f"adm_app_{user_id}_Gold")],
                [Button.inline("👑 Verify Elite", f"adm_app_{user_id}_Elite")],
                [Button.inline("❌ Terminate Request Order", f"adm_dec_{user_id}_None")]
            ]
        )
        await event.reply("📨 *Receipt forwarded to manual validation logs.* An admin will review your payment shortly.")
        return

    if not await check_membership(event.sender_id):
        lockout_ui = "⚠️ *SUBSCRIPTION REQUIRED AREA*\nYou must join our official updates channels to access the bot's features:"
        buttons = [[Button.url(f"📢 Join Channel Asset", c['link'])] for c in REQUIRED_CHANNELS]
        await event.reply(lockout_ui, buttons=buttons, parse_mode='markdown')
        return

    if user_data['searches_today'] >= user_data['max_limit']:
        over_limit_ui = f"🚨 *DAILY SERVICE ALLOCATION CEILING REACHED!*\nYour account limits are currently saturated at (`{user_data['searches_today']}/{user_data['max_limit']}`)."
        await event.reply(over_limit_ui, parse_mode='markdown')
        return

    query = event.text.strip() if event.text else ""
    if len(query) < 2: return

    ticker = await event.respond("⚡ _Scanning clustered index vectors across all 5 source channels..._")
    matches = await DatabaseManager.query_movie_catalog(query)

    if not matches:
        await ticker.edit("❌ *No file matches found matching your query.* Try alternative title variations.")
        return

    PAGINATION_CACHE[user_id] = {
        "query": query,
        "matches": matches,
        "current_page": 1
    }

    await ticker.delete()
    await RenderPaginationView(event, query, matches, page=1)

# ====================================================================
#               👑 HIGH-TIER EXECUTION TERMINAL HANDLERS
# ====================================================================
@client.on(events.NewMessage(pattern=r'/exportdb\s*(.*)'))
async def admin_export_database(event):
    if event.sender_id != ADMIN_ID: return
    
    choice = event.pattern_match.group(1).strip().upper()
    if choice not in ['CORE', 'A', 'B', 'C', 'D', 'E']:
        await event.reply("⚠️ **Missing Database Identifier Target!**\nUsage Syntax: `/exportdb CORE` | `A` | `B` | `C` | `D` | `E`")
        return
        
    if choice == 'CORE': target_path = DB_CORE
    elif choice == 'A': target_path = DB_ENGINE_A
    elif choice == 'B': target_path = DB_ENGINE_B
    elif choice == 'C': target_path = DB_ENGINE_C
    elif choice == 'D': target_path = DB_ENGINE_D
    else: target_path = DB_ENGINE_E
    
    progress = await event.reply(f"⚙️ *Starting Live Database Extraction Pipeline for Engine [{choice}]...*")
    backup_file = os.path.join(SCRIPT_DIR, f"backup_snapshot_engine_{choice}.db")
    
    BACKUP_ABORT_SIGNAL["abort"] = False
    
    try:
        last_pct = -1
        def progress_callback(status, remaining, total):
            nonlocal last_pct
            if BACKUP_ABORT_SIGNAL["abort"]:
                raise Exception("BACKUP_ABORT_SIGNAL_TRIGGERED")
                
            comp = total - remaining
            pct = (comp / total) * 100 if total > 0 else 100
            
            if int(pct) != last_pct:
                last_pct = int(pct)
                asyncio.run_coroutine_threadsafe(
                    progress.edit(f"📤 *Live Storage Dump Progress Engine [{choice}]:*\n"
                                  f"▓▓▓▓▓▓▓░░░ {pct:.1f}%\n"
                                  f"📂 **Streaming Blocks**: `{comp}` / `{total}` disk pages\n"
                                  f"ℹ️ Send `/adminGC cancelbackup` to interrupt execution stream immediately."),
                    client.loop
                )

        src = sqlite3.connect(target_path)
        dst = sqlite3.connect(backup_file)
        with dst:
            src.backup(dst, pages=5, progress=progress_callback)
        dst.close(); src.close()
        
        await progress.edit("📤 *Data package compiled safely. Transmitting binary asset data...*")
        await client.send_file(
            event.chat_id, file=backup_file,
            caption=f"📋 *SQLITE STRUCTURE PACK COMPILATION COMPLETE*\n\n📅 **Timestamp**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n🏅 **Target Core**: Engine Database Vector `{choice}`",
            force_document=True
        )
        await progress.delete()
    except Exception as e:
        if str(e) == "BACKUP_ABORT_SIGNAL_TRIGGERED":
            await progress.edit(f"🛑 *Backup Cancelled by Admin.* Interrupted safely at standard block boundaries.")
        else:
            await progress.edit(f"❌ *Export pipeline runtime error exception:* `{str(e)}`")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@client.on(events.NewMessage(pattern=r'/importdb\s*(.*)'))
async def admin_import_database(event):
    if event.sender_id != ADMIN_ID: return
    
    choice = event.pattern_match.group(1).strip().upper()
    if choice not in ['CORE', 'A', 'B', 'C', 'D', 'E']:
        await event.reply("⚠️ **Missing Overwrite Destination Target!**\nUsage: Reply to a `.db` file using `/importdb CORE` | `A` | `B` | `C` | `D` | `E`")
        return
        
    if not event.is_reply:
        await event.reply("⚠️ *Target input error. You must reply directly to a valid database file.*")
        return
        
    reply = await event.get_reply_message()
    if not reply or not reply.file or not reply.file.name.endswith('.db'):
        await event.reply("⚠️ *Security format validation exception. Target file must end with `.db`*")
        return
        
    if choice == 'CORE': target_path = DB_CORE
    elif choice == 'A': target_path = DB_ENGINE_A
    elif choice == 'B': target_path = DB_ENGINE_B
    elif choice == 'C': target_path = DB_ENGINE_C
    elif choice == 'D': target_path = DB_ENGINE_D
    else: target_path = DB_ENGINE_E
    
    progress = await event.reply(f"📥 *Downloading binary package stream for Engine [{choice}]... 0%*")
    temp_import = os.path.join(SCRIPT_DIR, "temp_incoming_payload.db")
    
    try:
        last_percent = -1
        async def download_callback(received, total):
            nonlocal last_percent
            pct = (received / total) * 100 if total else 0
            if int(pct) != last_percent:
                last_percent = int(pct)
                try:
                    await progress.edit(f"📥 *Downloading Data Stream payload for Engine [{choice}]:*\n⚙️ **Progress Metric**: `{pct:.1f}%` checked")
                except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                    pass

        await client.download_media(reply, file=temp_import, progress_callback=download_callback)
        await progress.edit("⚙️ *Validating structural parameters...*")
        
        check_c = sqlite3.connect(temp_import)
        cursor = check_c.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        check_c.close()
        
        if choice == 'CORE' and 'users' not in tables:
            await progress.edit("❌ *Import Rejected! Missing critical 'users' table map inside Core template.*")
            os.remove(temp_import)
            return
        elif choice in ['A', 'B', 'C', 'D', 'E'] and 'movies' not in tables:
            await progress.edit(f"❌ *Import Rejected! Missing critical 'movies' table inside layout system index model [{choice}].*")
            os.remove(temp_import)
            return
            
        await progress.edit(f"🔄 *Hot-swapping active data loops for Engine [{choice}]...*")
        if os.path.exists(target_path): os.remove(target_path)
        os.rename(temp_import, target_path)
        
        await DatabaseManager.initialize()
        await progress.edit(f"✅ *Database Sync Engine Array [{choice}] Overwritten into System Storage Layer!*")
    except Exception as e:
        await progress.edit(f"❌ *Critical system parser processing failure:* `{str(e)}`")
        if os.path.exists(temp_import): os.remove(temp_import)

@client.on(events.NewMessage(pattern='/adminGC'))
async def admin_central_terminal_cmd(event):
    if event.sender_id != ADMIN_ID: return
    args = event.text.split(" ")
    u_c, m_a, m_b, m_c, m_d, m_e, b_c, p_c, prem_c = await DatabaseManager.get_system_stats()
    
    s_price = await DatabaseManager.get_config('price_Silver', '29')
    g_price = await DatabaseManager.get_config('price_Gold', '49')
    e_price = await DatabaseManager.get_config('price_Elite', '149')
    
    f_lim = await DatabaseManager.get_config('limit_Free', '5')
    s_lim = await DatabaseManager.get_config('limit_Silver', '30')
    g_lim = await DatabaseManager.get_config('limit_Gold', '60')
    e_lim = await DatabaseManager.get_config('limit_Elite', '300')

    panel = (
        f"👑 **SYSTEM EXECUTIVE CONFIG CONSOLE** (`/adminGC`)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Logged Profiles (CORE) : `{u_c}` | 💎 Premium Rank Access: `{prem_c}`\n"
        f"📂 Engine A: `{m_a}` | B: `{m_b}` | C: `{m_c}` | D: `{m_d}` | E: `{m_e}`\n"
        f"🚫 Banned Nodes: `{b_c}` | ⏳ Pending Invoices: `{p_c}`\n\n"
        f"⚙️ **DYNAMIC SYSTEM PRICE CONFIG MATRIX**\n"
        f"🥈 Silver Pass Price: `₹{s_price}` | 🥇 Gold Pass: `₹{g_price}` | 👑 Elite Pass: `₹{e_price}`\n"
        f"⚡ Quotas Max/Day -> Free:`{f_lim}` | Silv:`{s_lim}` | Gold:`{g_lim}` | Elite:`{e_lim}`\n\n"
        f"🛠️ **ADMIN MANAGEMENT CAPABILITIES**\n"
        f"🔹 `/adminGC setprice <Silver/Gold/Elite> <Value>`\n"
        f"🔹 `/adminGC setlimit <Free/Silver/Gold/Elite> <Amount>`\n"
        f"🔹 `/adminGC coupon create <CODE> <MAX_USES> <REWARD>`\n"
        f"🔹 `/adminGC ban/unban <user_id>`\n"
        f"🔹 `/adminGC addquota <user_id> <amount>`\n"
        f"🔹 `/adminGC reset` | `/adminGC cancelbackup`\n"
        f"🔹 `/adminGC broadcast <text message>`"
    )
    
    if len(args) == 1:
        await event.reply(panel, parse_mode='markdown')
        return
        
    cmd = args[1].lower()
    
    if cmd == "setprice" and len(args) > 3:
        target_tier = args[2].capitalize()
        new_val = args[3]
        if target_tier in ['Silver', 'Gold', 'Elite']:
            await DatabaseManager.set_config(f'price_{target_tier}', new_val)
            await event.reply(f"✅ Pricing parameter matrix modified: Premium tier bundle **{target_tier}** adjusted to **₹{new_val}**.")
            
    elif cmd == "setlimit" and len(args) > 3:
        target_tier = args[2].capitalize()
        new_val = args[3]
        if target_tier in ['Free', 'Silver', 'Gold', 'Elite']:
            await DatabaseManager.set_config(f'limit_{target_tier}', new_val)
            await event.reply(f"✅ Daily performance metrics adjusted: Allocation threshold limit for **{target_tier}** scaled to **{new_val}** daily tokens.")

    elif cmd == "coupon" and len(args) > 5 and args[2].lower() == "create":
        code = args[3].upper()
        max_u = int(args[4])
        reward = int(args[5])
        
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("INSERT OR REPLACE INTO coupons (code, max_uses, current_uses, quota_reward) VALUES (?, ?, 0, ?)", (code, max_u, reward))
            await db.commit()
            
        await event.reply(f"🎫 **PROMO NODECODE FORGED SUCCESSFULLY**\n\n🔑 Code: `{code}`\n👥 Capacity: `{max_u} users` \n⚡ Bonus Value: `+{reward} limits` per claim pass.")
        await dispatch_log(f"🎫 **New System Coupon Forged**: Code `{code}` ({max_u} max claims, +{reward} quota) constructed.")

    elif cmd == "cancelbackup":
        BACKUP_ABORT_SIGNAL["abort"] = True
        await event.reply("🛑 *Abort flag dispatched to live thread routines.*")

    elif cmd == "ban" and len(args) > 2:
        await DatabaseManager.set_user_ban_status(args[2], 1)
        await event.reply(f"🚫 Connection block applied to User `{args[2]}`.")
        await dispatch_log(f"🚫 **Node Banned**: User account reference `{args[2]}` terminated by security layer.")
        
    elif cmd == "unban" and len(args) > 2:
        await DatabaseManager.set_user_ban_status(args[2], 0)
        await event.reply(f"🟢 Connection block dropped for User `{args[2]}`.")

    elif cmd == "addquota" and len(args) > 3:
        target = args[2]
        amt = int(args[3])
        data = await DatabaseManager.get_user(target)
        if data:
            await DatabaseManager.update_premium_plan(target, data['plan'], data['max_limit'] + amt, 30)
            await event.reply(f"⚡ Added `+{amt}` search allocations to User `{target}`.")
            
    elif cmd == "reset":
        await DatabaseManager.reset_all_daily_quotas()
        await event.reply("🔄 Reset complete: All user daily search limits returned to baseline configurations.")
        
    elif cmd == "broadcast" and len(args) > 2:
        msg = event.text.split("broadcast ", 1)[1]
        users = await DatabaseManager.get_all_user_ids()
        status = await event.reply(f"📢 Transmitting broadcast stream into {len(users)} endpoint nodes...")
        
        success = 0
        update_filesystem_heartbeat(f"Broadcasting to {len(users)} users initiated")
        
        for uid in users:
            try:
                await client.send_message(int(uid), f"📢 *GLOBAL SYSTEM ANNOUNCEMENT*\n\n{msg}")
                success += 1
                await asyncio.sleep(1.0)
            except FloodWaitError as flood:
                logger.warning(f"Hit structural flood limits. Pausing execution pipeline for {flood.seconds} seconds.")
                await asyncio.sleep(flood.seconds)
            except Exception: 
                pass
                
        await status.edit(f"✅ Transmission loop complete. Sent to `{success}` users.")
        update_filesystem_heartbeat("Global System Announcement Dispatched Complete")

@client.on(events.NewMessage)
async def admin_manual_forward_indexer(event):
    if event.sender_id != ADMIN_ID: return
    if event.message.fwd_from and event.message.file:
        post_id = event.message.fwd_from.channel_post or event.message.fwd_from.saved_from_msg_id or event.message.id
        src_chat = event.message.fwd_from.from_id.channel_id if hasattr(event.message.fwd_from.from_id, 'channel_id') else 0
        actual_ch_id = int(f"-100{src_chat}") if not str(src_chat).startswith("-100") else src_chat
        
        name = event.message.file.name or "Unnamed FileAsset"
        size = event.message.file.size or 0
        
        assigned_target_db = await DatabaseManager.cache_movie(post_id, name, size, actual_ch_id)
        
        if assigned_target_db:
            db_filename = os.path.basename(assigned_target_db)
            await event.reply(f"📥 File captured successfully! Written down inside structural node: `{db_filename}`.")
        else:
            await event.reply("⚠️ *Forward ignored.* The origin channel identity did not match any of your 5 configured source channel mappings.")

# ====================================================================
#                     🚀 BOT INITIALIZER ENGINE
# ====================================================================
async def main_environment_bootstrap():
    update_filesystem_heartbeat("Starting Client Lifecycle Bootloader")
    await client.start(bot_token=BOT_TOKEN)
    await DatabaseManager.initialize()
    logger.info("⚡ Advanced 5-Database Production Engine Bootstrapped Successfully.")
    update_filesystem_heartbeat("System Engine Online and Fully Operable")

if __name__ == '__main__':
    print("---------------------------------------------------------")
    print("🚀 Running Advanced 5-Database UX Production Architecture...")
    print("🚀 Main Config DB  Instance File: alldata.db")
    print("🚀 Engine DB Channels Mounted   : A, B, C, D, E configurations active.")
    print("---------------------------------------------------------")
    client.loop.run_until_complete(main_environment_bootstrap())
    client.run_until_disconnected()
