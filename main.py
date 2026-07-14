# main.py
import io
import logging
import asyncio
import random
import telethon
from datetime import datetime, timedelta
from telethon import TelegramClient, events, functions, types, Button

from config import *
from database import DatabaseManager, format_size
from admin import register_admin_handlers

# --- 📝 LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_runtime.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MovieQuadEngineBot")

client = TelegramClient('movie_quad_session', API_ID, API_HASH)

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
#               ⌨️ PERSISTENT KEYBOARD INTERFACE MAP
# ====================================================================
def generate_keyboard_workspace_layout():
    """
    Generates structured physical keyboards mapped logically.
    Buttons are labeled using concise, clean text tags.
    """
    return types.ReplyKeyboardMarkup(
        rows=[
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="🔍 Start Search"),
                types.KeyboardButton(text="🔗 Refer Link")
            ]),
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="👤 Profile"),
                types.KeyboardButton(text="🎁 Daily Token")
            ]),
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="🎟️ Redeem Code"),
                types.KeyboardButton(text="👑 Upgrade")
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
            f"🛡️ *SECURITY VERIFICATION*\n\n"
            f"To access the clustered storage infrastructure, solve:\n"
            f"👉 `{n1} + {n2} = ?`"
        )
        await event.reply(captcha_ui, parse_mode='markdown')
        return

    await send_advanced_dashboard(event.chat_id, user_id)

async def send_advanced_dashboard(chat_id, user_id):
    user_data = await DatabaseManager.get_user(user_id)
    if not user_data: return

    is_admin = int(user_id) == ADMIN_ID
    usage_text = "♾️ Unlimited Balance" if is_admin else f"⚡ `{user_data['searches_today']}` / `{user_data['max_limit']}` Queries Used"

    welcome_ui = (
        f"💎 *QUAD-ENGINE INTERLINKED STREAM CORE v3.5* 💎\n\n"
        f"🏅 **Plan Tier** :  `★ {user_data['plan'] if not is_admin else 'Executive Admin'}`\n"
        f"📊 **Searches**  :  {usage_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Send any media title down below to instantly scan 5 connected file server clusters.\n\n"
        f"👉 *All functional tools are pinned to your keyboard layout below!*"
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

    if action_text == "🔍 Start Search":
        await event.reply("🔍 *Active Search Session Ready!*\n\nSimply drop your film name or key index text directly in the chat input below:")

    elif action_text == "🔗 Refer Link":
        bot_identity = await client.get_me()
        ref_link = f"https://t.me/{bot_identity.username}?start={user_id}"
        ref_ui = (
            f"🔗 *AFFILIATE REFERRAL HUB*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`{ref_link}`\n\n"
            f"👥 **Total Joins** : `{user_data['referral_count']}` connections.\n"
            f"🎁 **Reward Bonus** : Earn `+5` daily query limits permanently for each verified user node joining via your link!"
        )
        await event.reply(ref_ui, parse_mode='markdown')

    elif action_text == "👤 Profile":
        is_admin = int(user_id) == ADMIN_ID
        usage_text = "♾️ Unlimited Balance" if is_admin else f"`{user_data['searches_today']}` / `{user_data['max_limit']}` Tokens Used"
        profile_ui = (
            f"👤 *USER PERFORMANCE AUDIT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 **Reference ID**     : `{user_id}`\n"
            f"🏅 **System Status**    : `{user_data['plan'] if not is_admin else 'Executive Admin'}`\n"
            f"⚡ **Usage Metrics**    : {usage_text}\n"
            f"🤝 **Affiliate Nodes**   : `{user_data['referral_count']}` Users Linked\n"
            f"⏳ **Subscription Cycle**: `{user_data['premium_expiry']}`"
        )
        await event.reply(profile_ui, parse_mode='markdown')

    elif action_text == "🎁 Daily Token":
        now = datetime.now()
        can_claim = True
        if user_data['last_reward_time']:
            try:
                last_claim = datetime.strptime(user_data['last_reward_time'], "%Y-%m-%d %H:%M:%S")
                if now - last_claim < timedelta(hours=24):
                    can_claim = False
                    rem = timedelta(hours=24) - (now - last_claim)
                    hours, remainder = divmod(rem.seconds, 3600)
                    await event.reply(f"🔒 **Quota Locked!** Daily rewards bundle cycle resets in `{hours}` hours.")
            except Exception: 
                pass
            
        if can_claim:
            bonus = random.randint(1, 5)
            await DatabaseManager.update_user_reward(user_id, bonus, now.strftime("%Y-%m-%d %H:%M:%S"))
            await event.reply(f"🎁 **Bonus Claimed!** Added `+{bonus}` searches to your permanent ceiling balance.")

    elif action_text == "🎟️ Redeem Code":
        COUPON_INPUT_CACHE[user_id] = True
        await event.reply("🎟️ **Redeem Voucher Code**:\n\nType or paste your alphanumeric code string directly into the text field below:")

    elif action_text == "👑 Upgrade":
        upgrade_ui = (
            f"💎 *PREMIUM CLOUD ACCESS TIERS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🥈 **Silver Plan** — 30 Daily Searches\n"
            f"💰 `₹29 INR` / `50 Telegram Stars` per month\n\n"
            f"🥇 **Gold Plan** — 60 Daily Searches\n"
            f"💰 `₹49 INR` / `100 Telegram Stars` per month\n\n"
            f"👑 **Elite Plan** — 300 Daily Searches\n"
            f"💰 `₹149 INR` / `250 Telegram Stars` per month\n\n"
            f"👉 *Tap any inline trigger asset below to initiate secure checkout:* "
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
            f"⭐ *TELEGRAM STARS SECURE CHECKOUT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Plan Package** : `{tier} Account Tier`\n"
            f"💰 **Total Price**   : `{stars_cost} Stars`\n\n"
            f"👉 Click below to route to **@Gopalji_choubey**. Send the specified stars and attach a receipt screenshot for instant verification! 🎉"
        )
        buttons = [Button.url("💬 Pay via @Gopalji_choubey", "https://t.me/Gopalji_choubey")]
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
                caption=f"📲 *UPI SECURE INBOUND PAYMENT GATEWAY*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🏅 **Plan Variant**   : `{plan} Premium` \n"
                        f"💰 **Total Amount**  : `₹{price} INR` \n\n"
                        f"🤳 Scan this QR code with your payment app. Once paid, **REPLY** to this image message with your confirmation screenshot!",
            )
        except ModuleNotFoundError:
            await event.reply(f"⚠️ **UPI Engine Failure.** Alternative payment payload link:\n`{payload}`")

    elif action.startswith(b'get_file_'):
        parsed_args = action.decode('utf-8').split('_')
        db_flag = parsed_args[2]
        msg_id = int(parsed_args[3])
        
        is_admin = int(user_id) == ADMIN_ID
        if not is_admin and user_data['searches_today'] >= user_data['max_limit']:
            await event.answer("⚠️ Limit reached! Upgrade premium tiers to bypass.", alert=True)
            return
            
        if db_flag == 'a': target_ch, target_db = CHANNEL_A_ID, DB_ENGINE_A
        elif db_flag == 'b': target_ch, target_db = CHANNEL_B_ID, DB_ENGINE_B
        elif db_flag == 'c': target_ch, target_db = CHANNEL_C_ID, DB_ENGINE_C
        elif db_flag == 'd': target_ch, target_db = CHANNEL_D_ID, DB_ENGINE_D
        else: target_ch, target_db = CHANNEL_E_ID, DB_ENGINE_E
        
        try:
            source_messages = await client.get_messages(target_ch, ids=msg_id)
            if not source_messages or not source_messages.file:
                await event.answer("❌ Source file is missing or deleted from server index.", alert=True)
                return

            dispatched_file = await client.send_file(
                event.chat_id, 
                file=source_messages.media, 
                caption=f"🎬 **File Asset**: `{source_messages.file.name or 'Clean Stream Document'}`"
            )
            
            warning_notice = await client.send_message(
                event.chat_id, 
                "⚠️ *SECURE DELETION TIMEOUT TRIGGERED*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⏳ **Notice**: Forward or Save this file *anywhere else immediately*. "
                "It will self-destruct from this chat environment in **1 minute** to optimize cloud cache storage."
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
            await event.answer("⏳ Session dropped. Please initiate a new query search request.", alert=True)

    elif action.startswith(b'adm_app_') or action.startswith(b'adm_dec_'):
        p_args = action.decode('utf-8').split('_')
        res, target_uid, pass_tier = p_args[1], p_args[2], p_args[3]
        
        quota = 30
        if pass_tier == "Gold": quota = 60
        elif pass_tier == "Elite": quota = 300
        
        if res == "app":
            await DatabaseManager.update_premium_plan(target_uid, pass_tier, quota, 30)
            await DatabaseManager.update_payment_status(target_uid, pass_tier, "Approved")
            try: await client.send_message(int(target_uid), f"✅ *TRANSACTION VERIFIED!*\nYour profile has been elevated to the **{pass_tier} Premium Tier**.")
            except Exception: pass
            await event.edit(f"🟢 **RESOLVED**: Activated User `{target_uid}` into `{pass_tier}`.")
            
            await forward_to_log_channel(
                f"👑 <b>PREMIUM PURCHASE ACTIVATED</b>\n"
                f"👤 <b>User ID</b>: <code>{target_uid}</code>\n"
                f"🎖️ <b>Plan Upgraded</b>: {pass_tier}\n"
                f"⚡ <b>New Base Allocation</b>: {quota} Daily Queries"
            )
        else:
            await DatabaseManager.update_payment_status(target_uid, pass_tier, "Declined")
            try: await client.send_message(int(target_uid), "🔴 *PAYMENT AUDIT VERIFICATION FAILURE*")
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
        f"📂 *CROSS-CHANNEL CLUSTER RESULTS* 📂\n"
        f"━━━━━━━🔍 Index Matches 🔍━━━━━━━\n"
        f"🎯 **Query**   : `{query}`\n"
        f"📊 **Located** : `{total_m} Files` | **Page**: `{page}` / `{total_p}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Select your item to get the file instantly:* "
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
        "🔍 Start Search", "🔗 Refer Link", 
        "👤 Profile", "🎁 Daily Token", 
        "🎟️ Redeem Code", "👑 Upgrade"
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
        over_limit_ui = f"🚨 *DAILY LIMIT REACHED!*\nYour account search limits are currently saturated at (`{user_data['searches_today']}/{user_data['max_limit']}`)."
        await event.reply(over_limit_ui, parse_mode='markdown')
        return

    query = event.text.strip() if event.text else ""
    if len(query) < 2: return

    # --- CINEMATIC ANIMATED SEQUENCE ---
    ticker = await event.respond("🔍 **SEARCHING CLUSTERS...**")
    await asyncio.sleep(0.5)
    await ticker.edit("⏳ **[████░░░░░░] 45% Searching...**")
    await asyncio.sleep(0.4)
    await ticker.edit("⏳ **[██████████] 100% Core Matrix Synced!**")
    await asyncio.sleep(0.3)

    matches = await DatabaseManager.query_movie_catalog(query)

    if not matches:
        await ticker.edit("❌ *No matches found.* Please try an alternative title search pattern.")
        return

    PAGINATION_CACHE[user_id] = {
        "query": query,
        "matches": matches,
        "current_page": 1
    }

    await ticker.delete()
    await RenderPaginationView(event, query, matches, page=1)

# ====================================================================
#                     🚀 BOT INITIALIZER ENGINE
# ====================================================================
async def main_environment_bootstrap():
    await client.start(bot_token=BOT_TOKEN)
    await DatabaseManager.initialize()
    register_admin_handlers(client)
    logger.info("⚡ Advanced 5-Database Production Engine Bootstrapped Successfully.")

if __name__ == '__main__':
    print("---------------------------------------------------------")
    print("🚀 Running Advanced 5-Database UX Production Architecture...")
    print("🚀 Persistent Keyboard Controls Array Enabled.")
    print("---------------------------------------------------------")
    client.loop.run_until_complete(main_environment_bootstrap())
    client.run_until_disconnected()
