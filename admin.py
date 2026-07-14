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

# --- IN-MEMORY ADMIN CONTEXT STATE MANAGER ---
class AdminState:
    PENDING_QUOTA_USER = {}     # {admin_id: target_user_id}
    PENDING_BAN_USER = {}       # {admin_id: "BAN" or "UNBAN"}
    PENDING_COUPON_QUOTA = {}   # {admin_id: quota_value}
    ACTIVE_BROADCAST_TYPE = {}  # {admin_id: "TEXT" or "FORWARD" or "PREVIEW"}
    BROADCAST_DRAFT = {}        # {admin_id: MessageObject}

logger = logging.getLogger("AdminTerminal")

# Helper to verify DB tables structurally
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
        
        # Clear any dangling states on initial load
        AdminState.PENDING_QUOTA_USER.pop(event.sender_id, None)
        AdminState.PENDING_COUPON_QUOTA.pop(event.sender_id, None)
        AdminState.ACTIVE_BROADCAST_TYPE.pop(event.sender_id, None)
        AdminState.BROADCAST_DRAFT.pop(event.sender_id, None)

        await send_admin_dashboard(event)

    async def send_admin_dashboard(event, edit_message=None):
        try:
            # Gather metrics
            u_c, m_a, m_b, m_c, m_d, m_e, b_c, p_c, prem_c = await DatabaseManager.get_system_stats()
        except Exception as e:
            u_c, m_a, m_b, m_c, m_d, m_e, b_c, p_c, prem_c = (0, 0, 0, 0, 0, 0, 0, 0, 0)
            logger.error(f"Failed to fetch system statistics: {e}")

        panel_text = (
            f"👑 **SYSTEM MANAGEMENT EXECUTIVE TERMINAL v4.0**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💻 **CORE STORAGE CLUSTER STATUS**\n"
            f" ├─ Profiles (CORE)      : `{u_c}` accounts\n"
            f" ├─ Premium Rank Level   : `{prem_c}` active VIPs\n"
            f" ├─ Banned Blacklist Nodes: `{b_c}` accounts\n"
            f" └─ Unresolved Invoices  : `{p_c}` pending\n\n"
            f"📁 **ENGINE MAPPING METRIC VALUES**\n"
            f" ├─ Cluster [A] (sourcechannel) : `{m_a}` files\n"
            f" ├─ Cluster [B] (allanimedb)    : `{m_b}` files\n"
            f" ├─ Cluster [C] (ritsam1)       : `{m_c}` files\n"
            f" ├─ Cluster [D] (ritsam3)       : `{m_d}` files\n"
            f" └─ Cluster [E] (ritsam48)      : `{m_e}` files\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *Interactive Dashboard console loaded successfully.*"
        )

        buttons = [
            [
                Button.inline("📢 Global Broadcast", data="menu_broadcast"),
                Button.inline("🎟️ Mint Vouchers", data="menu_vouchers")
            ],
            [
                Button.inline("👤 Adjust Quota", data="menu_quota"),
                Button.inline("🚫 Ban/Unban Nodes", data="menu_ban_status")
            ],
            [
                Button.inline("📥 Overwrite Sync DB", data="menu_import"),
                Button.inline("📤 Snapshot Engine DB", data="menu_export")
            ],
            [
                Button.inline("🔄 Clean Global Limits", data="btn_reset_daily"),
                Button.inline("🛑 Cancel Backup", data="btn_kill_backup")
            ]
        ]

        if edit_message:
            await edit_message.edit(panel_text, buttons=buttons, parse_mode='markdown')
        else:
            await event.reply(panel_text, buttons=buttons, parse_mode='markdown')

    # ==========================================
    # 2. CALL_BACK ROUTER FOR INLINE DECK EVENTS
    # ==========================================
    @client.on(events.CallbackQuery)
    async def admin_callback_dispatcher(event):
        if event.sender_id != ADMIN_ID:
            await event.answer("⚠️ Access Denied: Administrator Credentials Required.", alert=True)
            return

        data = event.data.decode('utf-8')

        # Back to Main Menu
        if data == "main_menu":
            await event.answer("Returning to central terminal...")
            await send_admin_dashboard(event, edit_message=event)

        # Reset daily quotas
        elif data == "btn_reset_daily":
            await DatabaseManager.reset_all_daily_quotas()
            await event.answer("🟢 System daily limit counters set back to default profiles successfully!", alert=True)
            await send_admin_dashboard(event, edit_message=event)

        # Cancel Live Backup
        elif data == "btn_kill_backup":
            BACKUP_ABORT_SIGNAL["abort"] = True
            await event.answer("🚨 Kill signal dispatched to active backup streams.", alert=True)
            await send_admin_dashboard(event, edit_message=event)

        # Ban / Unban Menu View
        elif data == "menu_ban_status":
            await event.answer("User Restriction Engine active.")
            text = (
                "🔒 **USER BAN / UNBAN TERMINAL CONTROL**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Allows you to toggle restriction levels on any target profile. "
                "Banned users will lose connection routes to all active search engines.\n\n"
                "👉 Please click one of the option channels below:"
            )
            buttons = [
                [Button.inline("🚫 Ban a User ID", data="act_ban_user")],
                [Button.inline("🟢 Unban a User ID", data="act_unban_user")],
                [Button.inline("⬅️ Return to Main Control Deck", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        # Quota Modification Menu
        elif data == "menu_quota":
            await event.answer("Search Quota Manager loaded.")
            text = (
                "⚡ **INTERACTIVE QUOTA INJECTION PROTOCOL**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Allows you to add search credits dynamically to any user's profile.\n\n"
                "👉 Press the button below to start entering data manually."
            )
            buttons = [
                [Button.inline("⚙️ Modify Allocation Pool", data="act_quota_start")],
                [Button.inline("⬅️ Back to Main Menu", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        # Voucher Generation Menu
        elif data == "menu_vouchers":
            await event.answer("Coupon Terminal loaded.")
            text = (
                "🎟️ **VOUCHER & PROMO ENGINE INTERACTIVE SUITE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Create unique authorization codes that users can redeem to increase "
                "their search balances. All generated coupons are set to a 365-day lifetime.\n\n"
                "👉 Select an allocation size limit below:"
            )
            buttons = [
                [
                    Button.inline("🎟️ +10 limit", data="coup_val_10"),
                    Button.inline("🎟️ +50 limit", data="coup_val_50"),
                    Button.inline("🎟️ +100 limit", data="coup_val_100")
                ],
                [Button.inline("⚙️ Create Custom Voucher Quota", data="coup_val_custom")],
                [Button.inline("⬅️ Back to Main Menu", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        # DB Export Menu Selection
        elif data == "menu_export":
            await event.answer("Database Snapshot pipeline ready.")
            text = (
                "📤 **SNAPSHOT ENGINE DB EXTRACTION PIPELINE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Extract any system cluster database dynamically. The backup runs inside "
                "a background stream so that user queries do not lock during processing.\n\n"
                "👉 Choose the target cluster database database format below:"
            )
            buttons = [
                [Button.inline("📦 CORE (Users & Logs)", data="export_run_CORE")],
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

        # DB Import Overwrite Menu Selection
        elif data == "menu_import":
            await event.answer("Database write engine loaded.")
            text = (
                "📥 **DATABASE HOT-SWAP OVERWRITE MODULE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ **WARNING:** This will completely replace the target active database!\n\n"
                "👉 Select the system cluster destination database path you wish to overwrite:"
            )
            buttons = [
                [Button.inline("⚠️ Overwrite CORE DB", data="import_prep_CORE")],
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

        # Broadcast Selector (The Dropdown implementation)
        elif data == "menu_broadcast":
            await event.answer("Configuring campaign parameters.")
            text = (
                "📢 **SYSTEM CAMPAIGN BROADCAST COMPILER**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Configure how you want to broadcast announcements to your active user base.\n\n"
                "👉 **Choose an execution mode below:**"
            )
            buttons = [
                [Button.inline("📝 Plain Text/HTML Broadcast", data="bc_mode_text")],
                [Button.inline("🔄 Reply-Message Forward", data="bc_mode_forward")],
                [Button.inline("⬅️ Return to Main Menu", data="main_menu")]
            ]
            await event.edit(text, buttons=buttons, parse_mode='markdown')

        # ==========================================
        # 3. INTERACTIVE CALLBACK TRANSITIONS (BAN/UNBAN/QUOTA)
        # ==========================================
        elif data in ["act_ban_user", "act_unban_user"]:
            action_type = "BAN" if data == "act_ban_user" else "UNBAN"
            AdminState.PENDING_BAN_USER[event.sender_id] = action_type
            await event.answer("Listening for input...")
            await event.edit(
                f"🛡️ **{action_type} SYSTEM ROUTINE ENABLED**\n\n"
                "👉 *Please type the numeric Telegram User ID of the target user node now:*",
                buttons=[[Button.inline("❌ Cancel Action", data="main_menu")]]
            )

        elif data == "act_quota_start":
            AdminState.PENDING_QUOTA_USER[event.sender_id] = "AWAITING_ID"
            await event.answer("System tracking enabled.")
            await event.edit(
                "⚡ **USER SEARCH VALUE PROFILES**\n\n"
                "👉 *Please type the Target Telegram User ID of the recipient:*",
                buttons=[[Button.inline("❌ Cancel Action", data="main_menu")]]
            )

        # Voucher presets
        elif data.startswith("coup_val_"):
            val_type = data.split("_")[2]
            if val_type == "custom":
                AdminState.PENDING_COUPON_QUOTA[event.sender_id] = "AWAITING_VALUE"
                await event.edit(
                    "🎟️ **CUSTOM VOUCHER DISPATCH**\n\n"
                    "👉 *Please type the custom numeric search allocation value to assign each coupon:*",
                    buttons=[[Button.inline("❌ Cancel Action", data="main_menu")]]
                )
            else:
                quota = int(val_type)
                AdminState.PENDING_COUPON_QUOTA[event.sender_id] = quota
                await event.edit(
                    f"🎟️ **MINT VOUCHERS: ALLOCATION LIMIT `+{quota}`**\n\n"
                    "👉 *Now type the Quantity (number of unique vouchers to generate, e.g., 5):*",
                    buttons=[[Button.inline("❌ Cancel Action", data="main_menu")]]
                )

        # ==========================================
        # 4. DATABASE ACTION INTERACTIVE PIPELINES
        # ==========================================
        elif data.startswith("export_run_"):
            choice = data.split("_")[2]
            await event.answer(f"Launching Stream snapshot on Engine [{choice}]...")
            await event.delete()
            await trigger_live_export_pipeline(event, choice, client)

        elif data.startswith("import_prep_"):
            choice = data.split("_")[2]
            await event.answer("Listening for binary package imports.")
            await event.edit(
                f"📥 **HOT-SWAP PREPARATION LAYER ENGINE: [{choice}]**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Please perform the following steps carefully:*\n"
                f"1. Reply directly to this message.\n"
                f"2. Attach a valid `.db` SQLite database asset.\n"
                f"3. Put this command text in the comment box: `/importdb {choice}`",
                buttons=[[Button.inline("❌ Cancel Import Action", data="main_menu")]]
            )

        # ==========================================
        # 5. BROADCAST SELECTION INLINE PROCESSORS
        # ==========================================
        elif data == "bc_mode_text":
            AdminState.ACTIVE_BROADCAST_TYPE[event.sender_id] = "TEXT"
            await event.edit(
                "📝 **DRAFT BROADCAST ENGINE: HTML TEXT MODE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Please reply by writing out your exact message content now.*\n\n"
                "💡 *Tip: You can use HTML styling tags such as `<b>`, `<i>`, or inline links.*",
                buttons=[[Button.inline("❌ Abort Broadcast", data="main_menu")]]
            )

        elif data == "bc_mode_forward":
            AdminState.ACTIVE_BROADCAST_TYPE[event.sender_id] = "FORWARD"
            await event.edit(
                "🔄 **DRAFT BROADCAST ENGINE: FORWARD POSTING MODE**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Please forward any message, photo, video, or files directly into this chat terminal.*",
                buttons=[[Button.inline("❌ Abort Broadcast", data="main_menu")]]
            )

        elif data == "bc_confirm_send":
            await event.answer("Broadcast sequence initiated!", alert=True)
            await event.delete()
            await trigger_broadcaster_task(event, client)


    # ==========================================
    # 6. CONVERSATION STATE PARSERS (TEXT INPUT)
    # ==========================================
    @client.on(events.NewMessage)
    async def admin_text_input_pipeline_handler(event):
        if event.sender_id != ADMIN_ID:
            return
        
        # Check if user commands starting with slash are processed first
        if event.text and event.text.startswith('/'):
            return

        admin_id = event.sender_id

        # --- A. BAN ROUTINE PIPELINE ---
        if admin_id in AdminState.PENDING_BAN_USER:
            action = AdminState.PENDING_BAN_USER.pop(admin_id)
            target_user = event.text.strip()
            status_msg = await event.reply("⚙️ Updating secure user connection layer nodes...")
            try:
                target_user_id = int(target_user)
                status_bit = 1 if action == "BAN" else 0
                await DatabaseManager.set_user_ban_status(str(target_user_id), status_bit)
                
                status_emoji = "🚫 Banned from platform" if status_bit == 1 else "🟢 Connection path restored"
                await status_msg.edit(
                    f"✅ **DATABASE RECORD MODIFIED SUCCESSFULLY**\n"
                    f"👥 **User Identity**: `{target_user_id}`\n"
                    f"🛡️ **Current Status**: {status_emoji}",
                    buttons=[[Button.inline("⬅️ Return to Central Console", data="main_menu")]]
                )
            except ValueError:
                await status_msg.edit("❌ *Input formatting error! You must enter a numeric user identifier.*", 
                                      buttons=[[Button.inline("❌ Go Back", data="menu_ban_status")]])

        # --- B. QUOTA INJECTION PROCESSOR ---
        elif admin_id in AdminState.PENDING_QUOTA_USER:
            state = AdminState.PENDING_QUOTA_USER[admin_id]
            
            if state == "AWAITING_ID":
                target_user = event.text.strip()
                try:
                    target_user_id = int(target_user)
                    data = await DatabaseManager.get_user(str(target_user_id))
                    if not data:
                        await event.reply("❌ *User ID not found in Local Database core nodes!* Please try again.",
                                          buttons=[[Button.inline("❌ Cancel", data="menu_quota")]])
                        return
                    
                    # Transition to quota value input
                    AdminState.PENDING_QUOTA_USER[admin_id] = {"target_id": str(target_user_id), "existing_limit": data['max_limit'], "plan": data['plan']}
                    await event.reply(
                        f"🎯 **USER RECORD SECURED**\n"
                        f"👥 **User ID**: `{target_user_id}`\n"
                        f"📊 **Current Search Limit**: `{data['max_limit']}`\n\n"
                        f"👉 *Type the numerical count of credits to ADD (e.g. 50):*",
                        buttons=[[Button.inline("❌ Cancel", data="main_menu")]]
                    )
                except ValueError:
                    await event.reply("❌ *Input validation failure. Target ID must be a numeric value.*",
                                      buttons=[[Button.inline("❌ Cancel", data="menu_quota")]])

            elif isinstance(state, dict):
                # We have saved the dictionary data payload
                user_meta = AdminState.PENDING_QUOTA_USER.pop(admin_id)
                try:
                    quota_to_add = int(event.text.strip())
                    new_limit = user_meta['existing_limit'] + quota_to_add
                    await DatabaseManager.update_premium_plan(user_meta['target_id'], user_meta['plan'], new_limit, 30)
                    
                    await event.reply(
                        f"✅ **USER ALLOCATION UPDATED**\n"
                        f"👤 **Target User ID**: `{user_meta['target_id']}`\n"
                        f"📈 **Previous Limit**: `{user_meta['existing_limit']}`\n"
                        f"⚡ **Assigned limit**: `+{quota_to_add}` credits\n"
                        f"📊 **New Adjusted Limit**: `{new_limit}` active paths",
                        buttons=[[Button.inline("⬅️ Return to Central Console", data="main_menu")]]
                    )
                except ValueError:
                    await event.reply("❌ *Invalid numeric quantity entered! Transaction aborted.*",
                                      buttons=[[Button.inline("⬅️ Exit Engine Menu", data="main_menu")]])

        # --- C. VOUCHER CREATION PROCESSOR ---
        elif admin_id in AdminState.PENDING_COUPON_QUOTA:
            state = AdminState.PENDING_COUPON_QUOTA[admin_id]
            
            if state == "AWAITING_VALUE":
                try:
                    quota_val = int(event.text.strip())
                    AdminState.PENDING_COUPON_QUOTA[admin_id] = quota_val
                    await event.reply(
                        f"🎟️ **VOUCHER PROTOCOL - MINT LIMIT**: `+{quota_val}`\n\n"
                        f"👉 *Now please type the absolute numerical Quantity of codes to generate (e.g., 5):*",
                        buttons=[[Button.inline("❌ Cancel", data="main_menu")]]
                    )
                except ValueError:
                    await event.reply("❌ *Numeric verification failure.* Voucher values must be an integer.",
                                      buttons=[[Button.inline("❌ Cancel", data="main_menu")]])
            
            elif isinstance(state, int):
                # The state contains the quota size, the message is the quantity
                quota_size = AdminState.PENDING_COUPON_QUOTA.pop(admin_id)
                try:
                    quantity = int(event.text.strip())
                    vouchers = []
                    
                    for _ in range(quantity):
                        raw_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        code = f"GC_{raw_token}"
                        await DatabaseManager.create_coupon(code, quota_size, max_uses=1, expiry_days=365)
                        vouchers.append(code)
                        
                    vouchers_joined = "\n".join([f"🎫 `{v_code}`" for v_code in vouchers])
                    
                    yield_info = (
                        f"🎟️ **VOUCHER GENERATION SEQUENCE COMPLETED**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ **Credit Value Each** : `+{quota_size} Searches`\n"
                        f"📊 **Count Issued**      : `{quantity} Unique Codes` \n\n"
                        f"📋 **Redeemable Code Inventory:**\n{vouchers_joined}"
                    )
                    await event.reply(yield_info, parse_mode='markdown', buttons=[[Button.inline("⬅️ Back to Deck Menu", data="main_menu")]])
                except Exception as e:
                    await event.reply(f"❌ *Failed to generate voucher entities:* `{e}`",
                                      buttons=[[Button.inline("⬅️ Return to Main Control Deck", data="main_menu")]])

        # --- D. BROADCAST PROCESSOR ---
        elif admin_id in AdminState.ACTIVE_BROADCAST_TYPE:
            bc_type = AdminState.ACTIVE_BROADCAST_TYPE[admin_id]
            
            if bc_type in ["TEXT", "FORWARD"]:
                AdminState.BROADCAST_DRAFT[admin_id] = event.message
                
                # Show preview to avoid global errors before pushing to production
                await event.reply("🔎 **DRAFT PREVIEW RENDER GENERATED SUCCESSFULLY**")
                
                if bc_type == "TEXT":
                    await client.send_message(event.chat_id, event.message.text, parse_mode='html')
                else:
                    await client.send_message(event.chat_id, event.message)
                    
                preview_panel = (
                    "⚠️ **CONFIRM CAMPAIGN DISPATCH PARAMETERS**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Your message is ready to be delivered to all user profiles stored in the CORE DB.\n\n"
                    "👉 **Click an action button below:**"
                )
                buttons = [
                    [Button.inline("🚀 Broadcast Now", data="bc_confirm_send")],
                    [Button.inline("❌ Discard Campaign", data="main_menu")]
                ]
                await event.reply(preview_panel, buttons=buttons, parse_mode='markdown')


    # ==========================================
    # 7. ASYNC PIPELINE DRIVER OPERATIONS
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
                caption=f"📋 *SQLITE COMPILATION DISPATCHED*\n\n📅 **Timestamp**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n🏅 **Target Core**: Engine Database Vector `{choice}`",
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
            # Re-send dashboard
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
                # Anti-flood rate throttling
                await asyncio.sleep(0.05)
                
                # Periodically update dashboard
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
                
        await status_info.edit(
            f"✅ **GLOBAL BROADCAST DISPATCH COMPLETED**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **Completion Time**  : `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🟢 Delivery Completed : `{success}` profiles reached\n"
            f"🔴 Transmission Failed: `{failed}` profiles skipped\n"
            f"⚙️ Action logging closed automatically.",
            buttons=[[Button.inline("⬅️ Return to Dashboard Control Deck", data="main_menu")]]
        )

    # ==========================================
    # 8. LEGACY COMPATIBILITY SLASH PARSER
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
            
            # Structural Validations using helper
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
