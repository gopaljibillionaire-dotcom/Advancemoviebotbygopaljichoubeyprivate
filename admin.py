# admin.py
import os
import random
import string
import asyncio
import sqlite3
import telethon
from telethon import events, Button, types
from datetime import datetime

from config import *
from database import DatabaseManager

def register_admin_handlers(client: telethon.TelegramClient):
    
    @client.on(events.NewMessage(pattern=r'/make_coupon\s+(\d+)\s+(\d+)'))
    async def admin_create_coupon_handler(event):
        if event.sender_id != ADMIN_ID: return
        try:
            quota = int(event.pattern_match.group(1))
            quantity = int(event.pattern_match.group(2))
            generated_vouchers = []
            
            for _ in range(quantity):
                raw_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                code = f"GC_{raw_token}"
                await DatabaseManager.create_coupon(code, quota, max_uses=1, expiry_days=365)
                generated_vouchers.append(code)
                
            compiled_list_text = "\n".join([f"🎫 `{v_code}`" for v_code in generated_vouchers])
            
            admin_ui = (
                f"🎟️ *BULK SINGLE-USE VOUCHERS DEPLOYED*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ **Yield Value Each** : `+{quota} Limit Credit`\n"
                f"📊 **Total Generated** : `{quantity} Single-Use Vouchers` \n\n"
                f"📋 **Active Coupon Code Array List:**\n{compiled_list_text}"
            )
            await event.reply(admin_ui, parse_mode='markdown')
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
                except Exception: 
                    pass
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
