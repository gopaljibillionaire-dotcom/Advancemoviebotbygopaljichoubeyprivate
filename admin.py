# admin.py
import os
import sys
import random
import string
import asyncio
import sqlite3
import logging
import telethon
from telethon import events, Button, types
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError
from datetime import datetime

from config import *
from database import DatabaseManager

# --- INTERACTIVE SESSION MEMORY STATE ---
class AdminState:
    PENDING_BAN_USER = {}       # {admin_id: "BAN" or "UNBAN"}
    PENDING_COUPON_QUOTA = {}   # {admin_id: quota_value}
    ACTIVE_BROADCAST_TYPE = {}  # {admin_id: "TEXT" or "FORWARD"}
    BROADCAST_DRAFT = {}        # {admin_id: MessageObject}

LOG_CHANNEL_ID = -1003559645437
logger = logging.getLogger("AdminTerminal")

def verify_db_tables(filepath: str, expected_table: str) -> bool:
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        return expected_table in tables
    except Exception as e:
        logger.error(f"Error validating database structure: {e}")
        return False

def register_admin_handlers(client: telethon.TelegramClient):

    # ==========================================
    # 1. CORE INTERACTIVE ADMIN PANEL CENTRAL DECK
    # ==========================================
    @client.on(events.NewMessage(pattern=r'^/adminGC$'))
    async def admin_central_terminal_cmd(event):
        if event.sender_id != ADMIN_ID:
            return
        
        # Explicit state flushes
        AdminState.PENDING_BAN_USER.pop(event.sender_id, None)
        AdminState.PENDING_COUPON_QUOTA.pop(event.sender_id, None)
        AdminState.ACTIVE_BROADCAST_TYPE.pop(event.sender_id, None)
        AdminState.BROADCAST_DRAFT.pop(event.sender_id, None)

        await send_admin_dashboard(event)

    async def send_admin_dashboard(event, edit_message=None):
        try:
            u_c, m_a, m_b, m_c, m_d, m_e, b_c, p_c, prem_c = await DatabaseManager.get_system_stats()
        except Exception as e:
            u_c, m_a, m_b, m_c, m_d, m_e, b_c, p_c, prem_c = (0, 0, 0, 0, 0, 0, 0, 0, 0)
            logger.error(f"Failed to fetch system statistics: {e}")

        panel_text = (
            f"👑 **SYSTEM EXECUTIVE CONTROL TERMINAL v4.5**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **CORE MATRIX STATUS METRICS**\n"
            f" ├─ Total Registered Accounts : `{u_c}`\n"
            f" ├─ Active VIP Premium Ranks  : `{prem_c}`\n"
            f" ├─ Blocked/Banned Endpoints  : `{b_c}`\n"
            f" └─ Unresolved Base Invoices  : `{p_c}`\n\n"
            f"📁 **ENGINE DATABASE STORAGE CLUSTERS**\n"
            f" ├─ Cluster [A] (sourcechannel) : `{m_a}` records\n"
            f" ├─ Cluster [B] (allanimedb)    : `{m_b}` records\n"
            f" ├─ Cluster [C] (ritsam1)       : `{m_c}` records\n"
            f" ├─ Cluster [D] (ritsam3)       : `{m_d}` records\n"
            f" └─ Cluster [E] (ritsam48)      : `{m_e}` records\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *Select an administrative task sequence below:* "
        )

        buttons = [
            [
                Button.inline("📢 Launch Global Campaign", data="menu_broadcast"),
                Button.inline("🎟️ Mint Single-Use Vouchers", data="menu_vouchers")
            ],
            [
                Button.inline("🛡️ Block/Unblock Profile", data="menu_ban_status")
            ],
            [
                Button.inline("📥 Overwrite Sync DB", data="menu_import"),
                Button.inline("📤 Snapshot Engine DB", data="menu_export")
            ],
            [
                Button.inline("🔄 Reset Daily Counters", data="btn_reset_daily"),
                Button.inline("🛑 Abort Active Backup", data="btn_kill_backup")
            ]
        ]

        if edit_message:
            await edit_message.edit(panel_text, buttons=buttons, parse_mode='markdown')
        else:
            await event.reply(panel_text, buttons=buttons, parse_mode='markdown')

    # ==========================================
    # 2. CALL_BACK ROUTER FOR INLINE EVENTS
    # ==========================================
    @client.on(events.CallbackQuery)
    async def admin_callback_dispatcher(event):
        if event.sender_id != ADMIN_ID:
            await event.answer("⚠️ Access Denied: Administrator Credentials Required.", alert=True)
            return

        data = event.data.decode('utf-8')

        if data == "main_menu":
            await event.answer("Returning to central terminal...")
            await send_admin_dashboard(event, edit_message=event)

        elif data == "btn_reset_daily":
            await DatabaseManager.reset_all_daily_quotas()
            await event.answer("🟢 System daily limit counters set back to baseline configurations!", alert=True)
            await send_admin_dashboard(event, edit_message=event)

        elif data == "btn_kill_backup":
            BACKUP_ABORT_SIGNAL["abort"] = True
            await event.answer("🚨 Kill signal dispatched to live thread routines.", alert=True)
            await send_admin_dashboard(event, edit_message=event)

        elif data == "menu_ban_status":
            await event.answer("User Restriction Engine active.")
            text = (
                "🔒 **USER CONNECTION BAN & EXCLUSION CONTROL**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Toggle routing security on target user profiles. "
                "Banned users are barred instantly from search queries.\n\n"
                "👉 Please choose a pathway operation:"
            )
            buttons = [
                [Button.inline("🚫 Apply Security Ban Block", data="act_ban_user")],
                [Button.inline("🟢 Drop Security Ban Block", data="act_unban_user")],
                [Button.inline("⬅️ Return to Main Control Deck", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        elif data == "menu_vouchers":
            await event.answer("Token generation matrix loaded.")
            text = (
                "🎟️ **SINGLE-USE VOUCHER CODE SUITE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Generate single-use verification token arrays. When a user redeems a token, "
                "they claim the specified credit capacity exactly once. The code expires immediately afterward.\n\n"
                "👉 **Select a base quota level value per voucher:**"
            )
            buttons = [
                [
                    Button.inline("🎫 +10 Searches", data="coup_val_10"),
                    Button.inline("🎫 +25 Searches", data="coup_val_25"),
                    Button.inline("🎫 +50 Searches", data="coup_val_50")
                ],
                [
                    Button.inline("🎫 +100 Searches", data="coup_val_100"),
                    Button.inline("⚙️ Custom Quota Scale", data="coup_val_custom")
                ],
                [Button.inline("⬅️ Back to Main Terminal", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        elif data == "menu_export":
            await event.answer("Snapshot generation pipeline ready.")
            text = (
                "📤 **LIVE DATABASE ARCHIVAL STORAGE PIPELINE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Extract system datasets safely into standalone snapshot layers without locking database tables.\n\n"
                "👉 **Choose target cluster destination engine:**"
            )
            buttons = [
                [Button.inline("📦 CORE MASTER DATABASE", data="export_run_CORE")],
                [
                    Button.inline("Engine A", data="export_run_A"),
                    Button.inline("Engine B", data="export_run_B"),
                    Button.inline("Engine C", data="export_run_C")
                ],
                [
                    Button.inline("Engine D", data="export_run_D"),
                    Button.inline("Engine E", data="export_run_E")
                ],
                [Button.inline("⬅️ Back to Main Menu", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        elif data == "menu_import":
            await event.answer("Hot-swap array active.")
            text = (
                "📥 **SYSTEM HOT-SWAP DATA OVERWRITE SYSTEM**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ **CRITICAL WARNING:** This operation replaces active system tables directly.\n\n"
                "👉 **Select target system database architecture to overwrite:**"
            )
            buttons = [
                [Button.inline("⚠️ Overwrite CORE DB Structure", data="import_prep_CORE")],
                [
                    Button.inline("Engine A", data="import_prep_A"),
                    Button.inline("Engine B", data="import_prep_B"),
                    Button.inline("Engine C", data="import_prep_C")
                ],
                [
                    Button.inline("Engine D", data="import_prep_D"),
                    Button.inline("Engine E", data="import_prep_E")
                ],
                [Button.inline("⬅️ Back to Main Menu", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        elif data == "menu_broadcast":
            await event.answer("Configuring campaign parameters.")
            text = (
                "📢 **CAMPAIGN BROADCAST COMPILER ENGINE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Dispatch global notifications out to all profile endpoints registered in your CORE network databases.\n\n"
                "👉 **Choose an extraction template structure:**"
            )
            buttons = [
                [Button.inline("📝 Plain Text/HTML Format", data="bc_mode_text")],
                [Button.inline("🔄 Binary Message Forwarding", data="bc_mode_forward")],
                [Button.inline("⬅️ Return to Main Menu", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        # --- ACTIONS TRANSITIONS ---
        elif data in ["act_ban_user", "act_unban_user"]:
            action_type = "BAN" if data == "act_ban_user" else "UNBAN"
            AdminState.PENDING_BAN_USER[event.sender_id] = action_type
            await event.answer("Listening for inputs...")
            await event.edit(
                f"🛡️ **SECURITY ASSIGNMENT LAYER: {action_type}**\n\n"
                "👉 *Please text the absolute numeric Telegram User ID of the profile endpoint now:*",
                buttons=[[Button.inline("❌ Cancel Routine", data="main_menu")]]
            )

        elif data.startswith("coup_val_"):
            val_type = data.split("_")[2]
            if val_type == "custom":
                AdminState.PENDING_COUPON_QUOTA[event.sender_id] = "AWAITING_VALUE"
                await event.edit(
                    "🎟️ **CUSTOM SINGLE-USE VOUCHER GENERATION**\n\n"
                    "👉 *Type the specific search credit count to add per code (e.g., 10):*",
                    buttons=[[Button.inline("❌ Cancel", data="main_menu")]]
                )
            else:
                quota = int(val_type)
                AdminState.PENDING_COUPON_QUOTA[event.sender_id] = quota
                await event.edit(
                    f"🎟️ **MINT VOUCHER CONFIG: `+{quota} Searches per User`**\n\n"
                    "👉 *Please type the absolute Quantity of individual codes to build now (e.g. 25):*",
                    buttons=[[Button.inline("❌ Cancel Sequence", data="main_menu")]]
                )

        elif data.startswith("export_run_"):
            choice = data.split("_")[2]
            await event.answer(f"Launching Snapshot Pipeline on Engine [{choice}]...")
            await event.delete()
            await trigger_live_export_pipeline(event, choice, client)

        elif data.startswith("import_prep_"):
            choice = data.split("_")[2]
            await event.answer("Awaiting raw target binary upload stream.")
            await event.edit(
                f"📥 **HOT-SWAP STORAGE ENGINE INTERACTION CONFIG: [{choice}]**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Please complete the execution steps exactly:*\n"
                "1. Reply directly to this warning statement block.\n"
                "2. Upload a valid, clean, configured `.db` file block map.\n"
                f"3. Insert this text parameter command inside the field: `/importdb {choice}`",
                buttons=[[Button.inline("❌ Kill Overwrite Sequence", data="main_menu")]]
            )

        elif data == "bc_mode_text":
            AdminState.ACTIVE_BROADCAST_TYPE[event.sender_id] = "TEXT"
            await event.edit(
                "📝 **DRAFT LIVE MESSAGE CAMPAIGN: TEXT/HTML**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Please send your message content as a reply text block now.*\n\n"
                "💡 *HTML formatting properties (`<b>`, `<i>`, code brackets) are fully supported.*",
                buttons=[[Button.inline("❌ Drop Campaign", data="main_menu")]]
            )

        elif data == "bc_mode_forward":
            AdminState.ACTIVE_BROADCAST_TYPE[event.sender_id] = "FORWARD"
            await event.edit(
                "🔄 **DRAFT LIVE MESSAGE CAMPAIGN: FORWARD STREAM**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Forward the image, video, document file, or post structure directly into this interface window now.*",
                buttons=[[Button.inline("❌ Drop Campaign", data="main_menu")]]
            )

        elif data == "bc_confirm_send":
            await event.answer("Global transmission loop active!", alert=True)
            await event.delete()
            await trigger_broadcaster_task(event, client)

    # ==========================================
    # 3. TEXT-BASED INPUT MULTI-STAGE STATE CONVERSATIONS
    # ==========================================
    @client.on(events.NewMessage)
    async def admin_text_input_pipeline_handler(event):
        if event.sender_id != ADMIN_ID or (event.text and event.text.startswith('/')):
            return

        admin_id = event.sender_id

        # --- A. ACTION INTERCEPT: SECURITY BAN CHANNELS ---
        if admin_id in AdminState.PENDING_BAN_USER:
            action = AdminState.PENDING_BAN_USER.pop(admin_id)
            target_input = event.text.strip()
            status_msg = await event.reply("⚙️ Modifying user permission values within security core data maps...")
            try:
                target_user_id = int(target_input)
                status_bit = 1 if action == "BAN" else 0
                await DatabaseManager.set_user_ban_status(str(target_user_id), status_bit)
                
                status_label = "🚫 Banned from search routes" if status_bit == 1 else "🟢 Access clearance re-established"
                await status_msg.edit(
                    f"🛡️ **SECURITY MAPPING INTERACTION REPORT**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 **Profile ID Node**: `{target_user_id}`\n"
                    f"⚡ **Assigned State** : {status_label}",
                    buttons=[[Button.inline("⬅️ Return to Control Panel", data="main_menu")]]
                )
            except ValueError:
                await status_msg.edit("❌ *Validation syntax failure. The user index must be purely numeric value profiles.*", 
                                      buttons=[[Button.inline("❌ Go Back", data="menu_ban_status")]])

        # --- B. ACTION INTERCEPT: SINGLE-USE TOKEN VOUCHERS GENERATION ---
        elif admin_id in AdminState.PENDING_COUPON_QUOTA:
            state = AdminState.PENDING_COUPON_QUOTA[admin_id]
            
            if state == "AWAITING_VALUE":
                try:
                    quota_val = int(event.text.strip())
                    AdminState.PENDING_COUPON_QUOTA[admin_id] = quota_val
                    await event.reply(
                        f"🎟️ **VOUCHER PROTOCOL SELECTION DEPLOYED**\n"
                        f"⚡ **Target Yield Unit**: `+{quota_val} Searches per single-use claim` \n\n"
                        f"👉 *Type the absolute quantity of tokens to generate now (e.g., 25):*",
                        buttons=[[Button.inline("❌ Cancel Process", data="main_menu")]]
                    )
                except ValueError:
                    await event.reply("❌ *Numeric parsing failure.* Allocation units must be integer values.",
                                      buttons=[[Button.inline("❌ Cancel", data="main_menu")]])
            
            elif isinstance(state, int):
                quota_size = AdminState.PENDING_COUPON_QUOTA.pop(admin_id)
                try:
                    quantity = int(event.text.strip())
                    vouchers = []
                    
                    # Generate requested unique single-use vouchers
                    for _ in range(quantity):
                        raw_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        code = f"GC_{raw_token}"
                        # max_uses=1 ensures single claim constraint
                        await DatabaseManager.create_coupon(code, quota_size, max_uses=1, expiry_days=365)
                        vouchers.append(code)
                        
                    vouchers_joined = "\n".join([f"🎫 `{v_code}`" for v_code in vouchers])
                    
                    yield_info = (
                        f"🎟️ **AUTHENTIC SINGLE-USE CODES GENERATED SUCCESSFULLY**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ **Credit Value Each** : `+{quota_size} Search Allocations`\n"
                        f"📊 **Volume Created**    : `{quantity} Unique Vouchers` \n"
                        f"🔒 **Usage Restrictions**: Single use per voucher code instance.\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📋 **Redeemable Token Inventory:**\n{vouchers_joined}"
                    )
                    
                    # Deliver list directly to management terminal windows
                    await event.reply(yield_info, parse_mode='markdown', buttons=[[Button.inline("⬅️ Back to Control Deck", data="main_menu")]])
                    
                    # ASYNC PIPELINE DISPATCH LOG TO PRIVATE MONITOR CHANNEL
                    log_template = (
                        f"🛰️ **SECURE AUDIT TRANSACTION LOG: VOUCHER EXECUTED**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📅 **Timestamp**        : `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                        f"👑 **Managing Operator**: Admin Profile Context\n"
                        f"⚡ **Credit Value/Unit** : `+{quota_size} Search Entries`\n"
                        f"📊 **Batch Array Volume** : `{quantity} Single-Use Vouchers Issued`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📋 **Active Code Dataset Array:**\n{vouchers_joined}"
                    )
                    await client.send_message(LOG_CHANNEL_ID, log_template, parse_mode='markdown')
                    
                except Exception as e:
                    await event.reply(f"❌ *Failed to complete cryptographic code generation algorithms:* `{e}`",
                                      buttons=[[Button.inline("⬅️ Return to Main Control Deck", data="main_menu")]])

        # --- C. ACTION INTERCEPT: MASS CAMPAIGN BROADCASTER PREVIEW ---
        elif admin_id in AdminState.ACTIVE_BROADCAST_TYPE:
            bc_type = AdminState.ACTIVE_BROADCAST_TYPE[admin_id]
            
            if bc_type in ["TEXT", "FORWARD"]:
                AdminState.BROADCAST_DRAFT[admin_id] = event.message
                
                await event.reply("🔎 **CAMPAIGN DRAFT PAYLOAD PREVIEW CHANNELS GENERATED**")
                if bc_type == "TEXT":
                    await client.send_message(event.chat_id, event.message.text, parse_mode='html')
                else:
                    await client.send_message(event.chat_id, event.message)
                    
                preview_panel = (
                    "⚠️ **PRODUCTION CAMPAIGN DEPLOYMENT CONFIRMATION**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Your message is formatted and held inside system caches. Ready to stream transmission loops into all profile endpoints inside the CORE database files.\n\n"
                    "👉 **Select the action step below:**"
                )
                buttons = [
                    [Button.inline("🚀 Authorize Production Release", data="bc_confirm_send")],
                    [Button.inline("❌ Clear Cached Draft", data="main_menu")]
                ]
                await event.reply(preview_panel, buttons=buttons, parse_mode='markdown')

    # ==========================================
    # 4. SYSTEM UTILITIES & ASYNC TASK HANDLERS
    # ==========================================
    async def trigger_live_export_pipeline(event, choice: str, client: telethon.TelegramClient):
        if choice == 'CORE': target_path = DB_CORE
        elif choice == 'A': target_path = DB_ENGINE_A
        elif choice == 'B': target_path = DB_ENGINE_B
        elif choice == 'C': target_path = DB_ENGINE_C
        elif choice == 'D': target_path = DB_ENGINE_D
        else: target_path = DB_ENGINE_E

        progress = await client.send_message(event.chat_id, f"⚙️ *Initializing Dynamic Extraction Pipeline on [{choice}]...*")
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
                caption=f"📋 *SQLITE BACKUP SNAPSHOT GENERATED*\n\n📅 **Timestamp**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n🏅 **Target Core**: Engine Database Vector `{choice}`",
                force_document=True
            )
            await progress.delete()
        except Exception as e:
            if str(e) == "BACKUP_ABORT_SIGNAL_TRIGGERED":
                await progress.edit(f"🛑 *Backup Cancelled by Admin.* Interrupted safely at standard block boundaries.")
            else:
                await progress.edit(f"❌ *Export pipeline runtime error exception:* `{str(e)}`")
        finally:
            if os.path.exists(backup_file): 
                os.remove(backup_file)
            await send_admin_dashboard(event)

    async def trigger_broadcaster_task(event, client: telethon.TelegramClient):
        admin_id = event.sender_id
        msg_object = AdminState.BROADCAST_DRAFT.pop(admin_id, None)
        bc_type = AdminState.ACTIVE_BROADCAST_TYPE.pop(admin_id, None)
        
        if not msg_object or not bc_type:
            await client.send_message(event.chat_id, "❌ *System session error context expired. Broadcast operation aborted.*")
            return

        users = await DatabaseManager.get_all_user_ids()
        status_info = await client.send_message(event.chat_id, f"📢 **STARTING SYSTEM BROADCAST**\n\n⚙️ Sending message to `{len(users)}` users...")
        
        success = 0
        failed = 0
        
        for idx, uid in enumerate(users):
            try:
                if bc_type == "TEXT":
                    await client.send_message(int(uid), msg_object.text, parse_mode='html')
                else:
                    await client.send_message(int(uid), msg_object)
                    
                success += 1
                await asyncio.sleep(0.05) # Throttle to prevent FloodWait
                
                if idx % 25 == 0:
                    await status_info.edit(
                        f"📢 **LIVE SYSTEM BROADCAST CAMPAIGN**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔄 **Sending status...**\n"
                        f"🟢 Sent Successfully: `{success}`\n"
                        f"🔴 Errored/Blocked : `{failed}`\n"
                        f"📊 Progress Metric : `{int((idx/len(users))*100)}%` completed"
                    )
            except FloodWaitError as fwe:
                await asyncio.sleep(fwe.seconds + 2)
            except (UserPrivacyRestrictedError, Exception):
                failed += 1
                
        completion_text = (
            f"✅ **GLOBAL BROADCAST DISPATCH COMPLETED**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **Completion Time**  : `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🟢 Delivery Completed : `{success}` profiles reached\n"
            f"🔴 Transmission Failed: `{failed}` profiles skipped\n"
            f"⚙️ Action logging closed automatically."
        )
        
        await status_info.edit(completion_text, buttons=[[Button.inline("⬅Header Main Dashboard", data="main_menu")]])
        
        # Send a summary audit to private monitoring channel
        await client.send_message(
            LOG_CHANNEL_ID, 
            f"🛰️ **CAMPAIGN BROADCAST EXECUTION REPORT**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{completion_text}", 
            parse_mode='markdown'
        )

    # ==========================================
    # 5. LEGACY LAYER COMMAND HANDLERS
    # ==========================================
    @client.on(events.NewMessage(pattern=r'/importdb\s*(.*)'))
    async def admin_import_database(event):
        if event.sender_id != ADMIN_ID: 
            return
        
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
            await progress.edit("⚙️ *Validating structural integrity parameters...*")
            
            if choice == 'CORE':
                valid = verify_db_tables(temp_import, 'users')
                error_msg = "Missing critical 'users' table map inside Core template."
            else:
                valid = verify_db_tables(temp_import, 'movies')
                error_msg = f"Missing critical 'movies' table inside index model [{choice}]."

            if not valid:
                await progress.edit(f"❌ **Import Rejected!** {error_msg}")
                if os.path.exists(temp_import): 
                    os.remove(temp_import)
                return
                
            await progress.edit(f"🔄 *Hot-swapping active data loops for Engine [{choice}]...*")
            if os.path.exists(target_path): 
                os.remove(target_path)
            os.rename(temp_import, target_path)
            
            await DatabaseManager.initialize()
            await progress.edit(f"✅ **Database Sync Engine Array [{choice}] successfully Overwritten!**")
        except Exception as e:
            await progress.edit(f"❌ *Critical system parser processing failure:* `{str(e)}`")
            if os.path.exists(temp_import): 
                os.remove(temp_import)

    @client.on(events.NewMessage)
    async def admin_manual_forward_indexer(event):
        if event.sender_id != ADMIN_ID: 
            return
        if event.message.fwd_from and event.message.file:
            post_id = event.message.fwd_from.channel_post or event.message.fwd_from.saved_from_msg_id or event.message.id
            src_chat = event.message.fwd_from.from_id.channel_id if hasattr(event.message.fwd_from.from_id, 'channel_id') else 0
            actual_ch_id = int(f"-100{src_chat}") if not str(src_chat).startswith("-100") else src_chat
            
            name = event.message.file.name or "Unnamed FileAsset"
            size = event.message.file.size or 0
            
            assigned_target_db = await DatabaseManager.cache_movie(post_id, name, size, actual_ch_id)
            
            if assigned_target_db:
                db_filename = os.path.basename(assigned_target_db)
                await event.reply(f"📥 File captured successfully! Written inside structural node: `{db_filename}`.")
            else:
                await event.reply("⚠️ *Forward ignored.* The origin channel identity did not match any of your 5 configured source channel mappings.")
