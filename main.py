import os
import re
import json
import io
import logging
import asyncio
import random
import sqlite3
import string
import telethon
from datetime import datetime, timedelta
import aiosqlite
from telethon import TelegramClient, events, functions, types, Button

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
LOG_CHANNEL_ID = -1003559645437

REQUIRED_CHANNELS = [
    {"id": -1003985304953, "link": "https://t.me/yagamicorporation"},
]       

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

client = TelegramClient('movie_quad_session', API_ID, API_HASH)

PAGINATION_CACHE = {}
CAPTCHA_CACHE = {}
COUPON_INPUT_CACHE = {}
BACKUP_ABORT_SIGNAL = {"abort": False}

# ====================================================================
#                   🗄️ QUAD DATABASE MANAGEMENT ENGINE
# ====================================================================
class DatabaseManager:
    @staticmethod
    async def initialize():
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
            
            try:
                await db.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
                await db.commit()
            except sqlite3.OperationalError: pass

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
                logger.info("🔧 Migration Patch Applied: 'expiry_date' safely structuralized inside coupons schema.")
            except sqlite3.OperationalError: pass
            
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
            
        logger.info("⚡ Live 5-Engine Storage Clusters successfully mounted and synchronized.")

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
            
            await db.execute("""
                INSERT INTO users (user_id, username, plan, searches_today, max_limit, referral_count, referred_by, last_reset_date, banned, premium_expiry, verified)
                VALUES (?, ?, 'Free', 0, 5, 0, ?, ?, 0, 'Never', 0)
            """, (user_id, username, referrer_id, today))
            await db.commit()
            return True

    @staticmethod
    async def set_verified(user_id: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    @staticmethod
    async def apply_referral_credit(referrer_id: str):
        async with aiosqlite.connect(DB_CORE) as db:
            await db.execute("UPDATE users SET max_limit = max_limit + 5, referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
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
                        res = await fresh_cursor.fetchone()
                        return dict(res) if res else None
                return None

    @staticmethod
    async def verify_daily_reset(user_id: str):
        today = str(datetime.now().date())
        async with aiosqlite.connect(DB_CORE) as db:
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
        async with aiosqlite.connect(DB_CORE) as db:
            async with db.execute("SELECT plan, premium_expiry FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != 'Free' and row[1] != 'Never':
                    try:
                        expiry = datetime.strptime(row[1], "%Y-%m-%d").date()
                        if datetime.now().date() > expiry:
                            await db.execute("UPDATE users SET plan = 'Free', max_limit = 5, premium_expiry = 'Never' WHERE user_id = ?", (user_id,))
                            await db.commit()
                    except Exception: pass

    @staticmethod
    async def increment_search(user_id: str):
        if int(user_id) == ADMIN_ID: return
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
    async def create_coupon(code: str, quota: int, max_uses: int, expiry_days: int = 365):
        async with aiosqlite.connect(DB_CORE) as db:
            exp_str = str((datetime.now() + timedelta(days=expiry_days)).date())
            await db.execute("""
                INSERT OR REPLACE INTO coupons (code, quota_reward, max_uses, current_uses, expiry_date)
                VALUES (?, ?, ?, 0, ?)
            """, (code, quota, max_uses, exp_str))
            await db.commit()

    @staticmethod
    async def redeem_coupon(user_id: str, code: str):
        async with aiosqlite.connect(DB_CORE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM coupons WHERE code = ?", (code,)) as cursor:
                coupon = await cursor.fetchone()
                if not coupon: return "INVALID"
                
            today = datetime.now().date()
            if coupon['expiry_date']:
                try:
                    if datetime.strptime(coupon['expiry_date'], "%Y-%m-%d").date() < today:
                        return "EXPIRED"
                except Exception: pass
                
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

async def forward_to_log_channel(html_text: str):
    try:
        await client.send_message(LOG_CHANNEL_ID, html_text, parse_mode='html')
    except Exception as e:
        logger.error(f"Failed to transmit log dispatch vector: {e}")

async def scheduled_file_destruction(chat_id, raw_file_msg, alert_notice_msg):
    await asyncio.sleep(60)
    try:
        await client.delete_messages(chat_id, [raw_file_msg.id, alert_notice_msg.id])
    except Exception:
        pass

# ====================================================================
#               ⌨️ PERSISTENT REPLY KEYBOARD INTERFACE MAP
# ====================================================================
def generate_keyboard_workspace_layout():
    return types.ReplyKeyboardMarkup(
        rows=[
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="🔗 Generate Affiliate Link"),
                types.KeyboardButton(text="📖 System Instructions Manual")
            ]),
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="👤 Profile Metrics"),
                types.KeyboardButton(text="🎁 Free Daily Token")
            ]),
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="🎟️ Redeem Coupon Voucher"),
                types.KeyboardButton(text="👑 Upgrade Premium Tiers")
            ])
        ],
        resize=True,
        persistent=True
    )

# ====================================================================
#                      🤖 CAPTCHA & USER ROUTING
# ====================================================================
def generate_math_captcha():
    n1 = random.randint(1, 9)
    n2 = random.randint(1, 9)
    return n1, n2, n1 + n2

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
        n1, n2, answer = generate_math_captcha()
        CAPTCHA_CACHE[user_id] = {"answer": answer, "ref": referrer_id, "username": username}
        
        captcha_ui = (
            f"🛡️ *SECURITY VERIFICATION REQUIRED*\n\n"
            f"To access the clustered systems infrastructure, prove you are human.\n"
            f"Solve: `{n1} + {n2} = ?`"
        )
        await event.reply(captcha_ui, parse_mode='markdown')
        return

    await send_advanced_dashboard(event.chat_id, user_id)

async def send_advanced_dashboard(chat_id, user_id, confirmation_msg=None):
    user_data = await DatabaseManager.get_user(user_id)
    if not user_data: return

    is_admin = int(user_id) == ADMIN_ID
    usage_text = "♾️ Unlimited Tokens" if is_admin else f"⚡ `{user_data['searches_today']}` / `{user_data['max_limit']}` Searches"

    welcome_ui = (
        f"💎 *QUAD-ENGINE INTERLINKED STREAM CORE v3.5* 💎\n"
        f"━━━━━━━⚙️ Account Framework ⚙️━━━━━━━\n"
        f"🎖️ **Tier Status** :  👑 `{user_data['plan'] if not is_admin else 'Executive Admin'}`\n"
        f"📊 **Usage Token**:  {usage_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 **Instructions**: Send any media title down below to scan files across multiple structural data servers.\n\n"
        f"🕹️ *All functional operational triggers are available directly at the side of your keyboard panel container bellow.*"
    )

    await client.send_message(
        chat_id, 
        welcome_ui, 
        buttons=generate_keyboard_workspace_layout(), 
        parse_mode='markdown'
    )

@client.on(events.NewMessage(pattern='/menu'))
async def on_menu_command(event):
    user_id = str(event.sender_id)
    user_data = await DatabaseManager.get_user(user_id)
    if user_data and user_data['verified'] == 1:
        await send_advanced_dashboard(event.chat_id, user_id)

# ====================================================================
#             ⚙️ HARDWARE KEYBOARD EVENT HANDLING SYSTEM
# ====================================================================
@client.on(events.NewMessage)
async def process_keyboard_menu_commands(event):
    if not event.text: return
    user_id = str(event.sender_id)
    user_data = await DatabaseManager.get_user(user_id)
    if not user_data or user_data['banned'] == 1 or user_data['verified'] == 0: return

    action_text = event.text.strip()

    if action_text == "🔗 Generate Affiliate Link":
        bot_identity = await client.get_me()
        ref_link = f"https://t.me/{bot_identity.username}?start={user_id}"
        ref_ui = (
            f"🔗 *YOUR AFFILIATE REFERRAL LINK*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`{ref_link}`\n\n"
            f"👥 **Current Network Connections**: `{user_data['referral_count']}` Users Joined.\n"
            f"🎁 **Reward Multiplier**: Earn `+5` search query credits permanently for each valid human node verified using your identifier link container!"
        )
        await event.reply(ref_ui, parse_mode='markdown')

    elif action_text == "📖 System Instructions Manual":
        instructions_ui = (
            f"📖 *STREAM CORE OPERATIONAL WORKSPACE INSTRUCTIONS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"1️⃣ **Searching Files**: Simply type the name of the movie or media text pattern string into the entry layout context window container and press send.\n\n"
            f"2️⃣ **Dynamic Extraction**: The system queries 5 unified data cluster storage units. Click the item button inside the menu pagination system to stream the data packet vector.\n\n"
            f"3️⃣ **Cache Purging**: To ensure optimized network performance arrays, dispatched file vectors self-destruct within 60 seconds. Forward them to private storage configurations immediately."
        )
        await event.reply(instructions_ui, parse_mode='markdown')

    elif action_text == "👤 Profile Metrics":
        is_admin = int(user_id) == ADMIN_ID
        usage_text = "♾️ Unlimited Balance" if is_admin else f"`{user_data['searches_today']}` / `{user_data['max_limit']}` Tokens Used"
        profile_ui = (
            f"👤 *USER INFRASTRUCTURE METRICS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 **Unique Reference ID** : `{user_id}`\n"
            f"🏅 **System Rank Tier**    : `★ {user_data['plan'] if not is_admin else 'Executive Admin'}`\n"
            f"⚡ **Token Performance**   : {usage_text}\n"
            f"🤝 **Affiliate Count**    : `{user_data['referral_count']}` Node connections\n"
            f"⏳ **Subscription Cycle**  : `{user_data['premium_expiry']}`"
        )
        await event.reply(profile_ui, parse_mode='markdown')

    elif action_text == "🎁 Free Daily Token":
        now = datetime.now()
        can_claim = True
        if user_data['last_reward_time']:
            try:
                last_claim = datetime.strptime(user_data['last_reward_time'], "%Y-%m-%d %H:%M:%S")
                if now - last_claim < timedelta(hours=24):
                    can_claim = False
                    rem = timedelta(hours=24) - (now - last_claim)
                    hours, remainder = divmod(rem.seconds, 3600)
                    await event.reply(f"🔒 **Quota Locked!** Daily rewards bundle cycle resets in `{hours}` hours manually.")
            except Exception: pass
            
        if can_claim:
            bonus = random.randint(1, 5)
            await DatabaseManager.update_user_reward(user_id, bonus, now.strftime("%Y-%m-%d %H:%M:%S"))
            await event.reply(f"🎁 **Bonus Granted Successfully!** Loaded `+{bonus}` permanent queries balance onto your core layer structure.")

    elif action_text == "🎟️ Redeem Coupon Voucher":
        COUPON_INPUT_CACHE[user_id] = True
        await event.reply("🎟️ **Enter Voucher Code**:\n\nType or paste your alphanumeric coupon token vector directly into the active text input layout manual workspace box below:")

    elif action_text == "👑 Upgrade Premium Tiers":
        upgrade_ui = (
            f"💎 *PREMIUM SERVICE TIERS & DEPLOYMENTS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🥈 **Silver Pass Variant** - 30 Search allocations/Day\n"
            f"💰 Cost Parameters: `₹29 INR` / `50 Telegram Stars` per 30 days\n\n"
            f"🥇 **Gold Pass Variant** - 60 Search allocations/Day\n"
            f"💰 Cost Parameters: `₹49 INR` / `100 Telegram Stars` per 30 days\n\n"
            f"👑 **Elite Mega Pass** - 300 Search allocations/Day\n"
            f"💰 Cost Parameters: `₹149 INR` / `250 Telegram Stars` per 30 days\n\n"
            f"👉 *Tap any inline trigger asset down below to open structural checkout interfaces instantly:*"
        )
        buttons = [
            [Button.inline("🥈 Silver (₹29)", b"pay_Silver_29"), Button.inline("⭐️ Silver (50★)", b"stars_Silver_50")],
            [Button.inline("🥇 Gold (₹49)", b"pay_Gold_49"), Button.inline("⭐️ Gold (100★)", b"stars_Gold_100")],
            [Button.inline("👑 Elite (₹149)", b"pay_Elite_149"), Button.inline("⭐️ Elite (250★)", b"stars_Elite_250")]
        ]
        await event.reply(upgrade_ui, buttons=buttons, parse_mode='markdown')

# ====================================================================
#                   🎛️ INLINE CALLBACK ACTIONS ROUTER
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
            f"⭐ *TELEGRAM STARS SECURE INBOUND PAYMENT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Selected Plan Package**: `{tier} Account Tier Upgrade`\n"
            f"💰 **Total Asset Value**     : `{stars_cost} Telegram Stars`\n\n"
            f"👉 Click the secure button below to route into **@Gopalji_choubey**. "
            f"Send the specified number of stars and attach a confirmation screenshot to trigger manual validation pipelines! 🎉"
        )
        buttons = [Button.url("💬 Send Stars to Admin", "https://t.me/Gopalji_choubey")]
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
                caption=f"📲 *DYNAMIC INTEGRATED UPI INBOUND GATEWAY*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🏅 **Target Tier Pass**: `{plan} Premium Access Bundle` \n"
                        f"💰 **Transaction Fee**  : `₹{price} INR` \n\n"
                        f"🤳 Scan the matrix payload image above with your payment app. Once paid, **REPLY** to this image message container with your confirmation screenshot!",
            )
        except ModuleNotFoundError:
            await event.reply(f"⚠️ **UPI Engine Failure.** Alternative raw payload string:\n`{payload}`")

    elif action.startswith(b'get_file_'):
        parsed_args = action.decode('utf-8').split('_')
        db_flag = parsed_args[2]
        msg_id = int(parsed_args[3])
        
        is_admin = int(user_id) == ADMIN_ID
        if not is_admin and user_data['searches_today'] >= user_data['max_limit']:
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
            await event.answer("📦 File dispatched seamlessly!", alert=False)
            
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
        
        quota = 30
        if pass_tier == "Gold": quota = 60
        elif pass_tier == "Elite": quota = 300
        
        if res == "app":
            await DatabaseManager.update_premium_plan(target_uid, pass_tier, quota, 30)
            await DatabaseManager.update_payment_status(target_uid, pass_tier, "Approved")
            try: await client.send_message(int(target_uid), f"✅ *TRANSACTION VERIFIED SUCCESSFUL!*\nYour profile has been elevated to the premium **{pass_tier} Upgrade Tier Pass**.")
            except Exception: pass
            await event.edit(f"🟢 **RESOLVED**: Verified User `{target_uid}` into `{pass_tier}`.")
            
            await forward_to_log_channel(
                f"👑 <b>PREMIUM PURCHASE ACTIVATED</b>\n"
                f"👤 <b>User ID</b>: <code>{target_uid}</code>\n"
                f"🎖️ <b>Plan Upgraded</b>: {pass_tier}\n"
                f"⚡ <b>New Base Allocation</b>: {quota} Daily Queries"
            )
        else:
            await DatabaseManager.update_payment_status(target_uid, pass_tier, "Declined")
            try: await client.send_message(int(target_uid), "🔴 *TRANSACTION VERIFICATION AUDIT FAILURE EXCEPTION*")
            except Exception: pass
            await event.edit(f"🔴 **DECLINED**: Blocked order pipeline sequence for user `{target_uid}`.")

    elif action == b'verify_subscription':
        if await check_membership(event.sender_id):
            await event.answer("✅ Subscriptions synchronized!", alert=True)
            await send_advanced_dashboard(event.chat_id, user_id)
        else:
            await event.answer("❌ Subscriptions mismatch verification checks.", alert=True)

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
        f"📂 *MULTIPLE CROSS-CHANNEL INDEX SERVERS ACTIVE*\n"
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
        pass
    except Exception:
        try: await client.send_message(event.chat_id, catalog_ui, buttons=buttons, parse_mode='markdown')
        except Exception: pass

# ====================================================================
#                     🎯 ROUTING & DISPATCH CONTROLLER
# ====================================================================
@client.on(events.NewMessage)
async def core_search_router(event):
    if event.text and (event.text.startswith('/') or event.text.strip() in [
        "🔗 Generate Affiliate Link", "📖 System Instructions Manual", 
        "👤 Profile Metrics", "🎁 Free Daily Token", 
        "🎟️ Redeem Coupon Voucher", "👑 Upgrade Premium Tiers"
    ]): return

    user_id = str(event.sender_id)
    
    # Check Captcha Validation Flow
    if user_id in CAPTCHA_CACHE:
        user_input = event.text.strip()
        cached = CAPTCHA_CACHE[user_id]
        if user_input.isdigit() and int(user_input) == cached["answer"]:
            await DatabaseManager.set_verified(user_id)
            del CAPTCHA_CACHE[user_id]
            await event.reply("✅ *Verification Successful! Access Granted.*")
            
            if cached["ref"]:
                await DatabaseManager.apply_referral_credit(cached["ref"])
                try: 
                    await client.send_message(
                        int(cached["ref"]), 
                        f"🔔 *Affiliate System Alert!*\n\nA new user (@{cached['username'] or 'Anonymous'}) joined using your node link identifier!\n➕5 Daily Token limits successfully credited to your account profile."
                    )
                except Exception: pass
                
                try:
                    await event.reply(f"🎉 *Welcome Packet Active!*\nYou were successfully invited to our cloud network workspace system framework by user node profile sequence: `{cached['ref']}`.")
                except Exception: pass
            
            await forward_to_log_channel(
                f"👤 <b>NEW SYSTEM NODE LINK SYNCHRONIZED</b>\n"
                f"🆔 <b>User Target ID</b>: <code>{user_id}</code>\n"
                f"🏷️ <b>Username Tag</b>: @{cached['username']}\n"
                f"🔗 <b>Affiliate Parent Origin Node</b>: <code>{cached['ref'] or 'Organic Unreferenced Node'}</code>\n"
                f"🛰️ <b>Status</b>: Active Linked Sync Verification Complete"
            )
            await send_advanced_dashboard(event.chat_id, user_id)
        else:
            n1, n2, answer = generate_math_captcha()
            CAPTCHA_CACHE[user_id]["answer"] = answer
            await event.reply(f"❌ *Incorrect Answer.* Try again:\nSolve: `{n1} + {n2} = ?`", parse_mode='markdown')
        return

    user_data = await DatabaseManager.get_user(user_id)
    if not user_data or user_data['banned'] == 1: return

    # Check Coupon Collection Routing Mode
    if user_id in COUPON_INPUT_CACHE:
        voucher_input = event.text.strip()
        del COUPON_INPUT_CACHE[user_id]
        
        status = await DatabaseManager.redeem_coupon(user_id, voucher_input)
        if status == "INVALID":
            await event.reply("❌ *Invalid Voucher Code Structure.*")
        elif status == "EXPIRED":
            await event.reply("❌ *This voucher code lifecycle milestone has expired.*")
        elif status == "MAXED":
            await event.reply("❌ *Maximum redundancy limits reached for this coupon payload.*")
        elif status == "ALREADY_USED":
            await event.reply("❌ *You have already claimed this token voucher pack structural allocation.*")
        else:
            await event.reply(f"🎉 *Success! Voucher Activated.*\n`+{status}` extra search tokens permanently added to your ceiling!")
            await forward_to_log_channel(
                f"🎟️ <b>COUPON REDEEMED VALIDATION RECORD</b>\n"
                f"👤 <b>User ID</b>: <code>{user_id}</code>\n"
                f"🔑 <b>Code String</b>: <code>{voucher_input}</code>\n"
                f"🎁 <b>Credit Dispatched</b>: +{status} Quota Tokens"
            )
        return

    if event.message.photo:
        await client.send_message(
            ADMIN_ID, f"📥 *INBOUND FINANCIAL TRANSACTION RECEIPT AUDIT*\n👤 **User Reference Account**: `{user_id}`",
            file=event.message.photo,
            buttons=[
                [Button.inline("🥈 Verify Silver", f"adm_app_{user_id}_Silver"), Button.inline("🥇 Verify Gold", f"adm_app_{user_id}_Gold")],
                [Button.inline("👑 Verify Elite (₹149)", f"adm_app_{user_id}_Elite")],
                [Button.inline("❌ Terminate Request Order", f"adm_dec_{user_id}_None")]
            ]
        )
        await event.reply("📨 *Receipt forwarded to manual validation logs.* An admin will review your payment shortly.")
        return

    if not await check_membership(event.sender_id):
        lockout_ui = "⚠️ *SUBSCRIPTION REQUIRED AREA*\nYou must join our official updates channels to access the bot's features:"
        buttons = [[Button.url(f"📢 Join Channel Asset", c['link'])] for c in REQUIRED_CHANNELS]
        buttons.append([Button.inline("🔄 Re-Verify Joining Status", b"verify_subscription")])
        await event.reply(lockout_ui, buttons=buttons, parse_mode='markdown')
        return

    is_admin = int(user_id) == ADMIN_ID
    if not is_admin and user_data['searches_today'] >= user_data['max_limit']:
        over_limit_ui = f"🚨 *DAILY SERVICE ALLOCATION CEILING REACHED!*\nYour account limits are currently saturated at (`{user_data['searches_today']}/{user_data['max_limit']}`)."
        await event.reply(over_limit_ui, parse_mode='markdown')
        return

    query = event.text.strip() if event.text else ""
    if len(query) < 2: return

    # --- CINEMATIC ANIMATED SEQUENCE ---
    ticker = await event.respond("🔍 **SEARCHING MOVIE IN DATABASE CLUSTERS...**")
    await asyncio.sleep(0.6)
    await ticker.edit("⏳ **[░░░░░░░░░░] 10% Mapping Vector Paths...**")
    await asyncio.sleep(0.4)
    await ticker.edit("⏳ **[████░░░░░░] 45% Index Sync Matrices...**")
    await asyncio.sleep(0.4)
    await ticker.edit("⏳ **[██████████] 100% Core Matrix Synced Successfully!**")
    await asyncio.sleep(0.3)

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
@client.on(events.NewMessage(pattern=r'/make_coupon\s+(\d+)\s+(\d+)'))
async def admin_create_coupon_handler(event):
    if event.sender_id != ADMIN_ID: return
    try:
        quota = int(event.pattern_match.group(1))
        quantity = int(event.pattern_match.group(2))
        
        generated_vouchers = []
        
        # Generates exact X individual single-use unique voucher arrays cleanly
        for _ in range(quantity):
            raw_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            code = f"GC_{raw_token}"
            await DatabaseManager.create_coupon(code, quota, max_uses=1, expiry_days=365)
            generated_vouchers.append(code)
            
        compiled_list_text = "\n".join([f"🎫 `{v_code}`" for v_code in generated_vouchers])
        
        await event.reply(
            f"🎟️ **BULK SINGLE-USE VOUCHERS DEPLOYED**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **Yield Value Each** : `+{quota} Limit Credit`\n"
            f"📊 **Total Generated** : `{quantity} Single-Use Vouchers` \n\n"
            f"📋 **Active Coupon Code Array List:**\n{compiled_list_text}"
        )
    except Exception as e:
        await event.reply(f"❌ *Syntax Error*: `{e}`\nUsage: `/make_coupon <SEARCH_QUOTA> <QUANTITY>`")

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
                                  f"ℹ️ Send `/adminGC cancelbackup` to interrupt stream."),
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
    
    panel = (
        f"👑 *SYSTEM MANAGEMENT EXECUTIVE LAYER v3.5* (`/adminGC`)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ **QUAD-CLUSTER STORAGE MATRIX STATUS**\n"
        f"👥 Logged Profiles (CORE)      : `{u_c}` accounts\n"
        f"💎 Premium Rank Access         : `{prem_c}` profiles\n"
        f"📂 Engine [A] sourcechannel    : `{m_a}` documents\n"
        f"📂 Engine [B] allanimedb        : `{m_b}` documents\n"
        f"📂 Engine [C] ritsam1           : `{m_c}` documents\n"
        f"📂 Engine [D] ritsam3           : `{m_d}` documents\n"
        f"📂 Engine [E] ritsam48          : `{m_e}` documents\n"
        f"🚫 Intercepted Banned Blocks   : `{b_c}` nodes\n"
        f"⏳ Unresolved Pending Invoices : `{p_c}` invoices\n\n"
        f"🛠️ **ADMIN ACTIONS CONSOLE**\n"
        f"🔹 `/make_coupon <quota> <quantity>`\n"
        f"🔹 `/adminGC ban <user_id>`\n"
        f"🔹 `/adminGC unban <user_id>`\n"
        f"🔹 `/adminGC addquota <user_id> <amount>`\n"
        f"🔹 `/adminGC reset` (Resets daily use metrics)\n"
        f"🔹 `/adminGC cancelbackup` (Force abort database backups)\n"
        f"🔹 `/adminGC broadcast <text message>`\n\n"
        f"📤 **EXPORT OPTIONS**\n"
        f"Syntax: `/exportdb CORE` | `A` | `B` | `C` | `D` | `E`"
    )
    
    if len(args) == 1:
        await event.reply(panel, parse_mode='markdown')
        return
        
    cmd = args[1].lower()
    
    if cmd == "cancelbackup":
        BACKUP_ABORT_SIGNAL["abort"] = True
        await event.reply("🛑 *Abort flag dispatched to live thread routines.*")

    elif cmd == "ban" and len(args) > 2:
        await DatabaseManager.set_user_ban_status(args[2], 1)
        await event.reply(f"🚫 Connection block applied to User `{args[2]}`.")
        
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
        for uid in users:
            try:
                await client.send_message(int(uid), f"📢 *GLOBAL SYSTEM ANNOUNCEMENT*\n\n{msg}")
                success += 1
                await asyncio.sleep(0.04)
            except Exception: pass
        await status.edit(f"✅ Transmission loop complete. Sent to `{success}` users.")

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
    await client.start(bot_token=BOT_TOKEN)
    await DatabaseManager.initialize()
    logger.info("⚡ Advanced 5-Database Production Engine Bootstrapped Successfully.")

if __name__ == '__main__':
    print("---------------------------------------------------------")
    print("🚀 Running Advanced 5-Database UX Production Architecture...")
    print("🚀 Persistent Keyboard Controls Array Enabled.")
    print("---------------------------------------------------------")
    client.loop.run_until_complete(main_environment_bootstrap())
    client.run_until_disconnected()
