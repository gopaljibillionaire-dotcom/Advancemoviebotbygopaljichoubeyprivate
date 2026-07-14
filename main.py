
import io
import os
import sys
import math
import time
import json
import logging
import asyncio
import random
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Union

# Third-Party Asynchronous Telegram Telephony Libraries
import telethon
from telethon import TelegramClient, events, functions, types, Button
from telethon.errors import (
    MessageNotModifiedError,
    FloodWaitError,
    UserIsBlockedError,
    PeerIdInvalidError,
    MessageDeleteForbiddenError
)

# Core Local Application Module Dependencies
try:
    from config import (
        API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, LOG_CHANNEL_ID, REQUIRED_CHANNELS,
        DB_ENGINE_A, DB_ENGINE_B, DB_ENGINE_C, DB_ENGINE_D, DB_ENGINE_E,
        CHANNEL_A_ID, CHANNEL_B_ID, CHANNEL_C_ID, CHANNEL_D_ID, CHANNEL_E_ID,
        CAPTCHA_CACHE, COUPON_INPUT_CACHE, PAGINATION_CACHE
    )
    from database import DatabaseManager, format_size
    from admin import register_admin_handlers
except ImportError as dependency_error:
    print(f"[-] CRITICAL FAILURE: Inbound dependency structural architecture missing components: {dependency_error}")
    sys.exit(1)

# ====================================================================
#                      📊 RIGOROUS RUNTIME DIAGNOSTICS
# ====================================================================
class PremiumLogFormatter(logging.Formatter):
    """Custom high-visibility ANSI layout formatter for mission-critical runtime logging."""
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    log_format = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + log_format + reset,
        logging.INFO: grey + log_format + reset,
        logging.WARNING: yellow + log_format + reset,
        logging.ERROR: red + log_format + reset,
        logging.CRITICAL: bold_red + log_format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

# Instantiating the underlying diagnostic pipeline filesystem channels
runtime_log_handler_file = logging.FileHandler("bot_runtime.log", encoding="utf-8")
runtime_log_handler_file.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'))

runtime_log_handler_stream = logging.StreamHandler(sys.stdout)
runtime_log_handler_stream.setFormatter(PremiumLogFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[runtime_log_handler_file, runtime_log_handler_stream]
)
logger = logging.getLogger("MovieQuadEngineCore")

# Initialize Global Cache Safeguards to handle isolated application memory state securely
STATE_CLEANUP_THRESHOLD_SECONDS = 3600
ACTIVE_USER_INTERACTION_SEMAPHORES: Dict[str, asyncio.Semaphore] = {}

# ====================================================================
#               🚀 TELETHON INFRASTRUCTURE ENGINE CLIENT
# ====================================================================
logger.info("[+] Instantiating high-capacity Telethon network gateway client endpoint...")
try:
    client = TelegramClient('movie_quad_session', API_ID, API_HASH, connection_retries=15, auto_reconnect=True)
except Exception as client_init_error:
    logger.critical(f"[-] Client initialization failed catastrophically: {client_init_error}")
    sys.exit(1)

# ====================================================================
#               🛡️ MEMORY SANITIZATION ENGINE (THREAD-SAFE)
# ====================================================================
async def background_memory_sanitizer_daemon():
    """Asynchronous infinite loops checking for structural cache leakage over time bounds."""
    logger.info("[+] Activating core background memory sanitization engine daemon routine...")
    while True:
        try:
            await asyncio.sleep(STATE_CLEANUP_THRESHOLD_SECONDS)
            current_epoch_time = time.time()
            cleaned_nodes_count = 0
            
            # Sanitizing structural context allocations from memory frames
            for cache_store in [CAPTCHA_CACHE, COUPON_INPUT_CACHE, PAGINATION_CACHE]:
                stale_keys = []
                for node_key, node_value in list(cache_store.items()):
                    if isinstance(node_value, dict) and "timestamp" in node_value:
                        if current_epoch_time - node_value["timestamp"] > STATE_CLEANUP_THRESHOLD_SECONDS:
                            stale_keys.append(node_key)
                for targets in stale_keys:
                    try:
                        del cache_store[targets]
                        cleaned_nodes_count += 1
                    except KeyError:
                        pass
            if cleaned_nodes_count > 0:
                logger.info(f"[🧹] Automated memory sweeping operation dropped {cleaned_nodes_count} idle interface states.")
        except Exception as sweeping_error:
            logger.error(f"[-] Garbage collection daemon encountered an anomaly: {sweeping_error}")

# ====================================================================
#             ⚙️ INTERCONNECTED SECURITY CONCURRENCY FILTERS
# ====================================================================
def acquire_user_interaction_lock(user_id: Union[str, int]) -> asyncio.Semaphore:
    """Acquires or maps a unique asynchronous semaphore lock preventing double actions."""
    uid_str = str(user_id)
    if uid_str not in ACTIVE_USER_INTERACTION_SEMAPHORES:
        ACTIVE_USER_INTERACTION_SEMAPHORES[uid_str] = asyncio.Semaphore(1)
    return ACTIVE_USER_INTERACTION_SEMAPHORES[uid_str]

async def check_membership(user_id: int) -> bool:
    """Scans all strict criteria configurations to ensure explicit cluster workspace permissions."""
    if not REQUIRED_CHANNELS:
        return True
    for current_channel_node in REQUIRED_CHANNELS:
        try:
            await client(functions.channels.GetParticipantRequest(
                channel=current_channel_node['id'], 
                participant=user_id
            ))
        except telethon.errors.rpcerrorlist.UserNotParticipantError:
            logger.warning(f"[-] Mandatory verification checkpoint failed for Entity ID: {user_id} on Node: {current_channel_node['id']}")
            return False
        except Exception as verification_pipeline_exception:
            logger.error(f"[-] Channel structural inspection entity mismatch check error: {verification_pipeline_exception}")
            # Fault-tolerant baseline design: pass verification if API error is localized inside Telegram servers
            continue
    return True

async def forward_to_log_channel(html_text: str):
    """Dispatches high-priority formatted administrative records into isolated channel backbones."""
    try:
        await client.send_message(LOG_CHANNEL_ID, html_text, parse_mode='html', link_preview=False)
    except Exception as log_dispatch_exception:
        logger.error(f"[-] Critical failure: Unable to transmit log dispatch vector safely: {log_dispatch_exception}")

async def scheduled_file_destruction(chat_id: int, raw_file_msg: Any, alert_notice_msg: Any, destruction_delay: int = 60):
    """Executes atomic secure content zeroization sequence down specified channel corridors."""
    await asyncio.sleep(destruction_delay)
    try:
        await client.delete_messages(chat_id, [raw_file_msg.id, alert_notice_msg.id])
        logger.info(f"[🔒] Scheduled self-destruct cycle completed successfully for Chat: {chat_id}")
    except MessageDeleteForbiddenError:
        logger.error(f"[-] Permissions exception: Cannot enforce message erasure on Chat Axis: {chat_id}")
    except Exception as automated_wipe_anomaly:
        logger.error(f"[-] File purge routine caught a suppression sequence exception: {automated_wipe_anomaly}")

# ====================================================================
#         ⌨️ PROFESSIONAL INTERACTIVE KEYBOARD INFRASTRUCTURE
# ====================================================================
def generate_keyboard_workspace_layout() -> types.ReplyKeyboardMarkup:
    """
    Constructs a clean, high-visibility layout using clear unicode markers.
    The layout fits standard mobile screens seamlessly.
    """
    return types.ReplyKeyboardMarkup(
        rows=[
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="🔍 Start Search"),
                types.KeyboardButton(text="🔗 Refer Link")
            ]),
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="👤 Profile Summary"),
                types.KeyboardButton(text="🎁 Daily Reward Token")
            ]),
            types.KeyboardButtonRow(buttons=[
                types.KeyboardButton(text="🎟️ Redeem Voucher"),
                types.KeyboardButton(text="👑 Premium Upgrade Upgrade Upgrade")
            ])
        ],
        resize=True,
        persistent=True
    )

# ====================================================================
#                      🤖 ADVANCED SECURITY CAPTCHA
# ====================================================================
def generate_math_captcha() -> Tuple[int, int, int]:
    """Generates unpredictable, complex equation sets preventing API request farming structures."""
    first_random_integer = random.randint(11, 89)
    second_random_integer = random.randint(5, 9)
    algebraic_summation_product = first_random_integer + second_random_integer
    return first_random_integer, second_random_integer, algebraic_summation_product

# ====================================================================
#             🛡️ INTERACTIVE CONTROL EVENT DISPATCHERS
# ====================================================================
@client.on(events.NewMessage(pattern='/start'))
async def on_start_command(event: events.NewMessage.Event):
    """Handles new user entries and referral tracking setups securely."""
    if not event.sender_id:
        return
        
    user_id_string = str(event.sender_id)
    account_username_handle = event.sender.username or "Anonymous Node"
    user_display_name = f"{event.sender.first_name or ''} {event.sender.last_name or ''}".strip() or "Valued Explorer"
    
    # Isolate payload strings to discover hidden deep-linked references
    parsed_command_arguments = event.message.message.split(' ')
    detected_referrer_node_id = None
    
    if len(parsed_command_arguments) > 1:
        potential_referrer_argument = parsed_command_arguments[1].strip()
        if potential_referrer_argument.isdigit() and potential_referrer_argument != user_id_string:
            detected_referrer_node_id = potential_referrer_argument

    async with acquire_user_interaction_lock(user_id_string):
        try:
            registration_database_handshake_status = await DatabaseManager.register_user(
                user_id_string, account_username_handle, detected_referrer_node_id
            )
            
            if registration_database_handshake_status == "BANNED":
                ban_notification_interface = (
                    "❖ ══════════════════════ ❖\n"
                    "   🚨  ACCESS REGISTRATION TERMINATED  🚨\n"
                    "❖ ══════════════════════ ❖\n\n"
                    "Your unique authentication signature profile has been hard-locked by administrative command structures.\n\n"
                    "📌 **Reason Matrix:** Violation of terms regarding structural multi-accounting protocols.\n"
                    "✉️ **Support Desk:** Reach out to corporate admins if this flag constitutes a false positive."
                )
                await event.reply(ban_notification_interface, parse_mode='markdown')
                return
            
            extracted_user_profile_data = await DatabaseManager.get_user(user_id_string)
            
            if extracted_user_profile_data and extracted_user_profile_data.get('verified', 0) == 0:
                left_operand, right_operand, matching_solution = generate_math_captcha()
                
                CAPTCHA_CACHE[user_id_string] = {
                    "answer": matching_solution,
                    "ref": detected_referrer_node_id,
                    "username": account_username_handle,
                    "timestamp": time.time()
                }
                
                captcha_visual_interface = (
                    "✨ ══════════════════════ ✨\n"
                    "      🛡️ AUTOMATED GATEWAY PROTECTION\n"
                    "✨ ══════════════════════ ✨\n\n"
                    "Welcome to the **Quad-Engine Interlinked Stream Core**. "
                    "To initialize connection pipelines and verify you are a live user, please solve this verification equation:\n\n"
                    "📝 **Verification Equation:**\n"
                    f"👉 `{left_operand} + {right_operand} = ?`\n\n"
                    "⚡ *Type the exact numeric solution text down below to clear authentication checklines instantly:* "
                )
                await event.reply(captcha_visual_interface, parse_mode='markdown')
                return

            await send_advanced_dashboard(event.chat_id, user_id_string, user_display_name)
            
        except Exception as registration_layer_fault:
            logger.error(f"[-] Exception trapped inside onboarding router workflow: {registration_layer_fault}")
            traceback.print_exc()

async def send_advanced_dashboard(chat_id: int, user_id_string: str, custom_name: str = "Explorer"):
    """Generates the primary premium dashboard system for authentic users."""
    try:
        user_database_metrics_profile = await DatabaseManager.get_user(user_id_string)
        if not user_database_metrics_profile:
            return

        is_system_administrator = int(user_id_string) == ADMIN_ID
        
        if is_system_administrator:
            quota_status_micro_meter = "👑 Executive Administrator Balance (♾️)"
            current_plan_tier_label = "Executive Root Operator Tier"
        else:
            daily_used_tokens = user_database_metrics_profile.get('searches_today', 0)
            maximum_allowed_tokens = user_database_metrics_profile.get('max_limit', 10)
            quota_status_micro_meter = f"⚡ `{daily_used_tokens}` / `{maximum_allowed_tokens}` Token Pools Exhausted"
            current_plan_tier_label = f"★ {user_database_metrics_profile.get('plan', 'Standard Core Free')}"

        # Building out dynamic high-end UI dashboards
        premium_dashboard_render_string = (
            "💎 ══════════════════════════════ 💎\n"
            "   🎬 QUAD-ENGINE ENTERPRISE STREAM BOT v5.0\n"
            "💎 ══════════════════════════════ 💎\n\n"
            f"👋 Welcome back online, **{custom_name}**\n\n"
            f"⚜️ ─── SYSTEM PROFILE MATRICES ─── ⚜️\n"
            f"◆ **Subscription Tier** : `{current_plan_tier_label}`\n"
            f"◆ **Operational Quota** : {quota_status_micro_meter}\n"
            f"◆ **Cluster Connection** : `5 Mainframes Online` (Stable)\n"
            "⚙️ ───────────────────────────── ⚙️\n\n"
            "💬 **Global Catalog Scan Trigger Ready:**\n"
            "Simply send the exact file name or movie title below. The engine will scan all connected data clusters simultaneously.\n\n"
            "📌 **Quick Options:** Use the permanent keyboard interface below for account management:"
        )

        await client.send_message(
            chat_id,
            premium_dashboard_render_string,
            buttons=generate_keyboard_workspace_layout(),
            parse_mode='markdown'
        )
    except Exception as dashboard_generation_anomaly:
        logger.error(f"[-] UI Dashboard compilation failure reported: {dashboard_generation_anomaly}")

@client.on(events.NewMessage(pattern='/menu'))
async def on_menu_command(event: events.NewMessage.Event):
    """Enforces instantaneous re-routing pathways back to terminal controls dashboard."""
    if not event.sender_id:
        return
    user_id_string = str(event.sender_id)
    user_display_name = f"{event.sender.first_name or ''} {event.sender.last_name or ''}".strip() or "Explorer"
    
    user_profile_data_record = await DatabaseManager.get_user(user_id_string)
    if user_profile_data_record and user_profile_data_record.get('verified', 0) == 1:
        await send_advanced_dashboard(event.chat_id, user_id_string, user_display_name)

# ====================================================================
#             ⚙️ INTERACTION ROUTING & LAYOUT OPERATIONS
# ====================================================================
@client.on(events.NewMessage)
async def process_keyboard_menu_commands(event: events.NewMessage.Event):
    """Monitors standard interactive UI command operations from persistent buttons."""
    if not event.text or not event.sender_id:
        return
        
    user_id_string = str(event.sender_id)
    user_profile_record = await DatabaseManager.get_user(user_id_string)
    
    # Security screening layers
    if not user_profile_record:
        return
    if user_profile_record.get('banned', 0) == 1 or user_profile_record.get('verified', 0) == 0:
        return

    requested_action_label = event.text.strip()

    # 🔍 INTERACTION PARSER MATRIX - START SEARCH
    if requested_action_label == "🔍 Start Search":
        search_session_primed_view = (
            "🔍 ══════════════════════ 🔍\n"
            "       ACTIVE SEARCH MAIN LINK ESTABLISHED\n"
            "🔍 ══════════════════════ 🔍\n\n"
            "The cluster query engines are primed and ready for ingestion.\n\n"
            "👇 **Instructions:**\n"
            "Type your film title, series sequence keywords, or digital database token index below:\n\n"
            "💡 *Tip: Check spelling accuracy for optimal database retrieval matches!*"
        )
        await event.reply(search_session_primed_view, parse_mode='markdown')

    # 🔗 INTERACTION PARSER MATRIX - REFERRAL NODE GENERATION
    elif requested_action_label == "🔗 Refer Link":
        try:
            bot_identity_profile_cache = await client.get_me()
            affiliate_deep_link_url = f"https://t.me/{bot_identity_profile_cache.username}?start={user_id_string}"
            
            affiliate_hub_premium_view = (
                "🔗 ══════════════════════════════ 🔗\n"
                "       ENTERPRISE AFFILIATE REFERRAL CORE\n"
                "🔗 ══════════════════════════════ 🔗\n\n"
                "Expand the cloud network cluster matrix and secure matching reward points permanently!\n\n"
                "📋 **Your Unique Invitation Link:**\n"
                f"`{affiliate_deep_link_url}`\n\n"
                "📊 **Live Affiliate Balance:**\n"
                f"◆ **Active Referred Nodes** : `{user_profile_record.get('referral_count', 0)}` Connected Devices\n"
                f"◆ **Bonus Rate Allocation** : `+5` Permanent Daily Queries per node\n\n"
                "🎉 *Share this link to claim bonuses instantly when new users pass verification checkpoints!*"
            )
            await event.reply(affiliate_hub_premium_view, parse_mode='markdown')
        except Exception as referral_generation_error:
            logger.error(f"[-] Referral linkage mapping collapsed: {referral_generation_error}")

    # 👤 INTERACTION PARSER MATRIX - PROFILE METRIC MONITORING
    elif requested_action_label == "👤 Profile Summary":
        is_system_administrator = int(user_id_string) == ADMIN_ID
        quota_metric_string = "♾️ Unlimited Balance Framework" if is_system_administrator else f"`{user_profile_record.get('searches_today', 0)}` / `{user_profile_record.get('max_limit', 10)}` Available Quota Units"
        
        premium_expiry_date = user_profile_record.get('premium_expiry', 'Non-Expiring Lifetime Standard Cycle')
        
        account_audit_premium_view = (
            "👤 ══════════════════════════════ 👤\n"
            "       ENTERPRISE USER PROFILE AUDIT METRICS\n"
            "👤 ══════════════════════════════ 👤\n\n"
            f"◆ **Network Reference ID** : `{user_id_string}`\n"
            f"◆ **System Rank Status**    : `{user_profile_record.get('plan', 'Standard Base Free User') if not is_system_administrator else 'Executive Infrastructure Admin'}`\n"
            f"◆ **Usage Performance**    : {quota_metric_string}\n"
            f"◆ **Affiliate Linked Nodes** : `{user_profile_record.get('referral_count', 0)}` Nodes Registered\n"
            f"◆ **Subscription Lifespan**: `{premium_expiry_date}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💎 *Status Profile verification tag authenticated via distributed cluster keys.*"
        )
        await event.reply(account_audit_premium_view, parse_mode='markdown')

    # 🎁 INTERACTION PARSER MATRIX - DAILY CEILING TOKENS
    elif requested_action_label == "🎁 Daily Reward Token":
        current_time_marker = datetime.now()
        eligibility_state_flag = True
        
        if user_profile_record.get('last_reward_time'):
            try:
                parsed_last_claim_epoch = datetime.strptime(user_profile_record['last_reward_time'], "%Y-%m-%d %H:%M:%S")
                if current_time_marker - parsed_last_claim_epoch < timedelta(hours=24):
                    eligibility_state_flag = False
                    remaining_lockout_duration = timedelta(hours=24) - (current_time_marker - parsed_last_claim_epoch)
                    hours_left, sub_minutes_remainder = divmod(remaining_lockout_duration.seconds, 3600)
                    minutes_left, _ = divmod(sub_minutes_remainder, 60)
                    
                    quota_locked_premium_view = (
                        "🔒 ══════════════════════ 🔒\n"
                        "       DAILY REWARD SYSTEM QUOTA LOCKED\n"
                        "🔒 ══════════════════════ 🔒\n\n"
                        "Your account has already claimed its daily token bundle within this 24-hour cycle.\n\n"
                        f"⏳ **Cooldown Window Remaining:** `{hours_left} Hours and {minutes_left} Minutes`"
                    )
                    await event.reply(quota_locked_premium_view, parse_mode='markdown')
            except Exception as daily_time_parse_fault: 
                logger.error(f"[-] Timing engine parsing error: {daily_time_parse_fault}")
                
        if eligibility_state_flag:
            async with acquire_user_interaction_lock(user_id_string):
                random_bonus_token_yield = random.randint(2, 7)
                await DatabaseManager.update_user_reward(
                    user_id_string, random_bonus_token_yield, current_time_marker.strftime("%Y-%m-%d %H:%M:%S")
                )
                
                reward_granted_premium_view = (
                    "🎁 ══════════════════════ 🎁\n"
                    "       DAILY QUOTA BONUS BUNDLE GRANTED\n"
                    "🎁 ══════════════════════ 🎁\n\n"
                    "Authentication node balance validated successfully!\n\n"
                    f"🎉 **Reward Dispatched:** Added `+{random_bonus_token_yield}` permanent daily query tokens to your ceiling limits profile."
                )
                await event.reply(reward_granted_premium_view, parse_mode='markdown')

    # 🎟️ INTERACTION PARSER MATRIX - VOUCHER DEPLOYMENTS
    elif requested_action_label == "🎟️ Redeem Voucher":
        COUPON_INPUT_CACHE[user_id_string] = {
            "active": True,
            "timestamp": time.time()
        }
        voucher_request_premium_view = (
            "🎟️ ══════════════════════ 🎟️\n"
            "       PROMOTIONAL INBOUND VOUCHER ACTIVATION\n"
            "🎟️ ══════════════════════ 🎟️\n\n"
            "Please paste or type your alphanumeric code sequence directly into the chat input below:\n\n"
            "⚠️ *Notice: Alphanumeric voucher tokens are single-use parameters.*"
        )
        await event.reply(voucher_request_premium_view, parse_mode='markdown')

    # 👑 INTERACTION PARSER MATRIX - CLOUD ACCESS TIERS
    elif requested_action_label == "👑 Premium Upgrade Upgrade Upgrade":
        upgrade_catalog_premium_view = (
            "👑 ══════════════════════════════ 👑\n"
            "        ULTRA-PREMIUM HIGH-SPEED CLOUD TIERS\n"
            "👑 ══════════════════════════════ 👑\n\n"
            "Unlock instant access, remove limits, and get fast search streams across 5 database clusters.\n\n"
            "🥈 ─── SILVER VIP PASS MAINLINE ───\n"
            "◆ **Daily Token Ceiling** : 30 High-Speed Scans\n"
            "◆ **Financial Pipeline**  : `₹29 INR` OR `50 Telegram Stars` Monthly\n\n"
            "🥇 ─── GOLD EXCLUSIVE HUB ───\n"
            "◆ **Daily Token Ceiling** : 60 Ultra-Speed Scans\n"
            "◆ **Financial Pipeline**  : `₹49 INR` OR `100 Telegram Stars` Monthly\n\n"
            "👑 ─── ELITE EXECUTIVE SYSTEM ───\n"
            "◆ **Daily Token Ceiling** : 300 Unrestricted Scans\n"
            "◆ **Financial Pipeline**  : `₹149 INR` OR `250 Telegram Stars` Monthly\n\n"
            "✨ *Tap a checkout method below to initiate immediate payment processing:* "
        )
        
        interactive_checkout_button_matrix = [
            [
                Button.inline("🥈 Silver (₹29)", b"pay_Silver_29"), 
                Button.inline("⭐ Silver (50★)", b"stars_Silver_50")
            ],
            [
                Button.inline("🥇 Gold (₹49)", b"pay_Gold_49"), 
                Button.inline("⭐ Gold (100★)", b"stars_Gold_100")
            ],
            [
                Button.inline("👑 Elite (₹149)", b"pay_Elite_149"), 
                Button.inline("⭐ Elite (250★)", b"stars_Elite_250")
            ]
        ]
        await event.reply(upgrade_catalog_premium_view, buttons=interactive_checkout_button_matrix, parse_mode='markdown')

# ====================================================================
#               🎛️ SECURE INLINE INTERACTION ROUTER
# ====================================================================
@client.on(events.CallbackQuery)
async def on_interactive_callback(event: events.CallbackQuery.Event):
    """Processes interactive callback actions from inline button matrices securely."""
    action_byte_sequence = event.data
    user_id_string = str(event.sender_id)
    user_profile_dataset = await DatabaseManager.get_user(user_id_string)
    
    if user_profile_dataset and user_profile_dataset.get('banned', 0) == 1:
        await event.answer("⚠️ Operational Error: Interaction sequence cancelled by server.", alert=True)
        return

    # 🌟 STAR CHECKOUT GATEWAY ROUTING INTERFACE
    if action_byte_sequence.startswith(b'stars_'):
        try:
            _, selected_tier_label, dynamic_stars_valuation = action_byte_sequence.decode('utf-8').split('_')
            
            telegram_stars_checkout_interface = (
                "⭐️ ══════════════════════════════ ⭐️\n"
                "        TELEGRAM STARS AUTOMATED HUB ESCROW\n"
                "⭐️ ══════════════════════════════ ⭐️\n\n"
                f"◆ **Selected Framework Package** : `{selected_tier_label} Pro VIP`\n"
                f"◆ **Escrow Transaction Fee**     : `{dynamic_stars_valuation} Telegram Stars`\n\n"
                "📌 **Activation Steps:**\n"
                "1. Tap the contact link button below to open a private message window with **@Gopalji_choubey**.\n"
                "2. Send the exact matching stars value payload.\n"
                "3. Attach a clear screenshot of the transaction receipt.\n\n"
                "🚀 *Manual verification agents will activate your subscription tier within minutes!*"
            )
            
            contact_support_routing_matrix = [
                [Button.url("💬 Open Secure Escrow via @Gopalji_choubey", "https://t.me/Gopalji_choubey")]
            ]
            await event.edit(telegram_stars_checkout_interface, buttons=contact_support_routing_matrix, parse_mode='markdown')
        except Exception as stars_routing_anomaly:
            logger.error(f"[-] Telegram star deployment system structural failure: {stars_routing_anomaly}")

    # 📲 FIAT CASH UPI RUNTIME QR CODE ENGINE
    elif action_byte_sequence.startswith(b'pay_'):
        try:
            _, target_plan_variant, localized_fiat_cost = action_byte_sequence.decode('utf-8').split('_')
            target_merchant_upi_string = "8368680967@fam"  
            
            formatted_upi_payload_vector = (
                f"upi://pay?pa={target_merchant_upi_string}"
                f"&pn=MovieEngineHub"
                f"&am={localized_fiat_cost}"
                f"&cu=INR"
                f"&tn=Pay_{target_plan_variant}_{user_id_string}"
            )
            
            await DatabaseManager.log_payment_attempt(user_id_string, target_plan_variant, localized_fiat_cost)
            
            try:
                import qrcode
                qr_matrix_generator = qrcode.QRCode(version=1, box_size=10, border=4)
                qr_matrix_generator.add_data(formatted_upi_payload_vector)
                qr_matrix_generator.make(fit=True)
                
                in_memory_image_stream = io.BytesIO()
                compiled_qr_image = qr_matrix_generator.make_image(fill_color="black", back_color="white")
                compiled_qr_image.save(in_memory_image_stream, format="PNG")
                in_memory_image_stream.seek(0)
                in_memory_image_stream.name = f"payment_matrix_allocation_{user_id_string}.png"
                
                await event.delete()
                
                fiat_payment_invoice_interface = (
                    "📲 ══════════════════════════════ 📲\n"
                    "        UPI AUTOMATED INSTANT PAYMENT INVOICE\n"
                    "📲 ══════════════════════════════ 📲\n\n"
                    f"◆ **Premium Account Variant**   : `{target_plan_variant} Cloud Edition` \n"
                    f"◆ **Total Inbound Fee Charge**  : `₹{localized_fiat_cost} INR` \n\n"
                    "📌 **Instructions:**\n"
                    "1. Scan the attached high-definition QR code using any banking app (GPay, PhonePe, Paytm).\n"
                    "2. Complete the transfer without modifying the transaction notes.\n"
                    "3. **IMPORTANT:** Take a screenshot of the confirmation page and **REPLY** directly to this image message with it.\n\n"
                    "⚠️ *Our validation engine automatically processes arrivals via structural matching filters.*"
                )
                
                await client.send_file(
                    event.chat_id, 
                    file=in_memory_image_stream,
                    caption=fiat_payment_invoice_interface,
                    parse_mode='markdown'
                )
            except ModuleNotFoundError:
                logger.warning("[-] Python-qrcode module not found. Falling back to alternative link delivery.")
                fallback_link_interface = (
                    "⚠️ ══════════════════════ ⚠️\n"
                    "      INBOUND PAYMENT ENGINE DEGRADED\n"
                    "⚠️ ══════════════════════ ⚠️\n\n"
                    "The local matrix was unable to render the QR binary stream. "
                    "Please use this direct link connection to complete checkout:\n\n"
                    f"`{formatted_upi_payload_vector}`\n\n"
                    "Once paid, send the receipt screenshot to administration channels."
                )
                await event.reply(fallback_link_interface, parse_mode='markdown')
        except Exception as pay_routing_anomaly:
            logger.error(f"[-] Payment gateway initialization routine failure: {pay_routing_anomaly}")

    # 🎬 FILE EXTRACTION MAIN CONTROL SYSTEM
    elif action_byte_sequence.startswith(b'get_file_'):
        async with acquire_user_interaction_lock(user_id_string):
            try:
                separated_callback_arguments = action_byte_sequence.decode('utf-8').split('_')
                database_source_flag = separated_callback_arguments[2]
                target_message_index_id = int(separated_callback_arguments[3])
                
                is_system_administrator = int(user_id_string) == ADMIN_ID
                
                if not is_system_administrator and user_profile_dataset['searches_today'] >= user_profile_dataset['max_limit']:
                    await event.answer("🚨 Quota Saturation Warning: Please upgrade to higher VIP plans to continue.", alert=True)
                    return
                    
                if database_source_flag == 'a': 
                    target_channel_id, targeted_engine_label = CHANNEL_A_ID, DB_ENGINE_A
                elif database_source_flag == 'b': 
                    target_channel_id, targeted_engine_label = CHANNEL_B_ID, DB_ENGINE_B
                elif database_source_flag == 'c': 
                    target_channel_id, targeted_engine_label = CHANNEL_C_ID, DB_ENGINE_C
                elif database_source_flag == 'd': 
                    target_channel_id, targeted_engine_label = CHANNEL_D_ID, DB_ENGINE_D
                else: 
                    target_channel_id, targeted_engine_label = CHANNEL_E_ID, DB_ENGINE_E
                
                await event.answer("📡 Connecting to file server cluster...", alert=False)
                
                extracted_source_file_message = await client.get_messages(target_channel_id, ids=target_message_index_id)
                if not extracted_source_file_message or not extracted_source_file_message.file:
                    await event.answer("❌ Error: The file asset is missing or has been removed from the server index.", alert=True)
                    return

                isolated_file_title_string = extracted_source_file_message.file.name or 'Premium_Stream_Document.mp4'
                
                dispatched_file_media_node = await client.send_file(
                    event.chat_id, 
                    file=extracted_source_file_message.media, 
                    caption=(
                        "❖ ════════════════════════ ❖\n"
                        "    💎 PREMIUM STREAM LINK CONNECTED 💎\n"
                        "❖ ════════════════════════ ❖\n\n"
                        f"🎬 **File Asset:** `{isolated_file_title_string}`\n"
                        f"📊 **Data Volume:** `{format_size(extracted_source_file_message.file.size)}`"
                    ),
                    parse_mode='markdown'
                )
                
                automated_self_destruct_notice_node = await client.send_message(
                    event.chat_id, 
                    "⏳ ════════════════════════ ⏳\n"
                    "      SECURE DELETION TIMEOUT TRIGGERED\n"
                    "⏳ ════════════════════════ ⏳\n\n"
                    "⚠️ **Important Security Notice:**\n"
                    "Forward or save this file to your Saved Messages **immediately**.\n\n"
                    "This file will self-destruct from this chat environment in **1 minute** to optimize cloud cache storage."
                )
                
                await DatabaseManager.increment_search(user_id_string)
                await DatabaseManager.increment_movie_download(target_message_index_id, targeted_engine_label)
                
                asyncio.create_task(scheduled_file_destruction(
                    event.chat_id, dispatched_file_media_node, automated_self_destruct_notice_node, 60
                ))
                
            except Exception as file_dispatch_critical_failure:
                logger.error(f"[-] Catalog file dispatcher pipeline crashed: {file_dispatch_critical_failure}")
                await event.answer("❌ Server Error: Stream connection to source channel timed out.", alert=True)

    # 📊 PAGINATION VIEW INTERFACE NAVIGATOR
    elif action_byte_sequence.startswith(b'page_'):
        try:
            _, targeted_page_numerical_string = action_byte_sequence.decode('utf-8').split('_')
            requested_target_page = int(targeted_page_numerical_string)
            
            if user_id_string in PAGINATION_CACHE:
                cached_pagination_session_context = PAGINATION_CACHE[user_id_string]
                cached_pagination_session_context['current_page'] = requested_target_page
                
                await RenderPaginationView(
                    event, 
                    cached_pagination_session_context['query'], 
                    cached_pagination_session_context['matches'], 
                    requested_target_page
                )
            else:
                await event.answer("⏳ Session dropped. Please initiate a new query search request.", alert=True)
        except Exception as pagination_routing_fault:
            logger.error(f"[-] Pagination event router failed: {pagination_routing_fault}")

    # 👑 MANUAL ADMIN AUDITING ACTIONS GATEWAY
    elif action_byte_sequence.startswith(b'adm_app_') or action_byte_sequence.startswith(b'adm_dec_'):
        try:
            parsed_administrative_arguments = action_byte_sequence.decode('utf-8').split('_')
            administrative_resolution_flag = parsed_administrative_arguments[1]
            target_user_id_parameter = parsed_administrative_arguments[2]
            assigned_premium_tier_tier = parsed_administrative_arguments[3]
            
            calculated_daily_quota_allowance = 30
            if assigned_premium_tier_tier == "Gold": 
                calculated_daily_quota_allowance = 60
            elif assigned_premium_tier_tier == "Elite": 
                calculated_daily_quota_allowance = 300
            
            if administrative_resolution_flag == "app":
                await DatabaseManager.update_premium_plan(
                    target_user_id_parameter, assigned_premium_tier_tier, calculated_daily_quota_allowance, 30
                )
                await DatabaseManager.update_payment_status(target_user_id_parameter, assigned_premium_tier_tier, "Approved")
                
                try: 
                    success_notification_direct_message = (
                        "✅ ══════════════════════ ✅\n"
                        "       TRANSACTION VERIFIED BY NETWORK ADMIN\n"
                        "✅ ══════════════════════ ✅\n\n"
                        f"Your profile status has been elevated to the premium **{assigned_premium_tier_tier} Tier**.\n\n"
                        f"⚡ **New Limit:** `{calculated_daily_quota_allowance}` daily searches have been successfully credited."
                    )
                    await client.send_message(int(target_user_id_parameter), success_notification_direct_message, parse_mode='markdown')
                except Exception: 
                    pass
                    
                await event.edit(f"🟢 **RESOLVED**: Activated User `{target_user_id_parameter}` into `{assigned_premium_tier_tier}`.")
                
                audit_log_telemetry_html = (
                    f"👑 <b>PREMIUM PURCHASE ACTIVATED</b>\n"
                    f"👤 <b>User ID Node</b>: <code>{target_user_id_parameter}</code>\n"
                    f"🎖️ <b>Plan Level</b>: {assigned_premium_tier_tier}\n"
                    f"⚡ <b>Allocated Token Quota</b>: {calculated_daily_quota_allowance} Daily Queries"
                )
                await forward_to_log_channel(audit_log_telemetry_html)
            else:
                await DatabaseManager.update_payment_status(target_user_id_parameter, assigned_premium_tier_tier, "Declined")
                try: 
                    failure_notification_direct_message = (
                        "🔴 ══════════════════════ 🔴\n"
                        "       PAYMENT TRANSACTION AUDIT REJECTED\n"
                        "🔴 ══════════════════════ 🔴\n\n"
                        "Our auditing team could not verify your payment receipt image.\n\n"
                        "📌 **Possible Issues:** Blacked-out transaction identifiers, incorrect amounts, or mismatched reference labels. Please resubmit if this was a mistake."
                    )
                    await client.send_message(int(target_user_id_parameter), failure_notification_direct_message, parse_mode='markdown')
                except Exception: 
                    pass
                await event.edit(f"🔴 **DECLINED**: Blocked order pipeline sequence for user `{target_user_id_parameter}`.")
        except Exception as administrative_callback_processing_anomaly:
            logger.error(f"[-] Administrative inline processing function execution error: {administrative_callback_processing_anomaly}")

    # 🔄 SUBSCRIPTION JOIN VERIFICATION INTERACTION PROTOCOL
    elif action_byte_sequence == b'verify_subscription':
        try:
            user_display_name = f"{event.sender.first_name or ''} {event.sender.last_name or ''}".strip() or "Explorer"
            if await check_membership(event.sender_id):
                await event.answer("✅ Subscriptions synchronized! Access granted.", alert=True)
                await send_advanced_dashboard(event.chat_id, user_id_string, user_display_name)
            else:
                await event.answer("❌ Verification Failed: You must join the required channels to clear the access criteria.", alert=True)
        except Exception as explicit_sync_error:
            logger.error(f"[-] Explicit channel membership check failed: {explicit_sync_error}")

# ====================================================================
#               📊 PAGINATION VIEW RENDER COREENGINE
# ====================================================================
async def RenderPaginationView(event: Any, query: str, matches: List[Dict[str, Any]], page: int = 1):
    """Compiles a responsive grid array layout presenting targeted search hits cleanly."""
    items_per_page = 8
    total_matches_count = len(matches)
    calculated_total_pages = (total_matches_count + items_per_page - 1) // items_per_page
    
    if page < 1: 
        page = 1
    if page > calculated_total_pages: 
        page = calculated_total_pages
    
    slice_start_index = (page - 1) * items_per_page
    slice_end_index = slice_start_index + items_per_page
    active_view_dataset_slice = matches[slice_start_index:slice_end_index]
    
    catalog_display_interface_ui = (
        "📂 ══════════════════════════════ 📂\n"
        "        CROSS-CHANNEL DATA CLUSTER SEARCH MATCHES\n"
        "📂 ══════════════════════════════ 📂\n\n"
        f"🎯 **Target Query Key** : `{query}`\n"
        f"📊 **Located Hits**     : `{total_matches_count} Assets` | **Page Matrix**: `{page}` / `{calculated_total_pages}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Select your item from the list below to retrieve the file immediately:* "
    )
    
    interactive_inline_layout_matrix = []
    for asset_row in active_view_dataset_slice:
        readable_data_volume_size = format_size(asset_row['file_size'])
        sanitized_filename_label = asset_row['file_name']
        
        # Clean string length to prevent inline rendering overflows
        if len(sanitized_filename_label) > 42:
            sanitized_filename_label = sanitized_filename_label[:39] + "..."
            
        compiled_button_label_tag = f"🎬 {sanitized_filename_label} [{readable_data_volume_size}]"
        
        if asset_row['origin_db'] == DB_ENGINE_A: 
            database_location_flag = 'a'
        elif asset_row['origin_db'] == DB_ENGINE_B: 
            database_location_flag = 'b'
        elif asset_row['origin_db'] == DB_ENGINE_C: 
            database_location_flag = 'c'
        elif asset_row['origin_db'] == DB_ENGINE_D: 
            database_location_flag = 'd'
        else: 
            database_location_flag = 'e'
        
        callback_payload_string = f"get_file_{database_location_flag}_{asset_row['msg_id']}"
        interactive_inline_layout_matrix.append([Button.inline(compiled_button_label_tag, callback_payload_string.encode('utf-8'))])
        
    navigation_control_row = []
    if page > 1:
        navigation_control_row.append(Button.inline("⏮️ Previous Page", f"page_{page-1}".encode('utf-8')))
    if page < calculated_total_pages:
        navigation_control_row.append(Button.inline("Next Page ⏭️", f"page_{page+1}".encode('utf-8')))
        
    if navigation_control_row: 
        interactive_inline_layout_matrix.append(navigation_control_row)
        
    try:
        if isinstance(event, events.CallbackQuery.Event):
            await event.edit(catalog_display_interface_ui, buttons=interactive_inline_layout_matrix, parse_mode='markdown')
        else:
            await client.send_message(event.chat_id, catalog_display_interface_ui, buttons=interactive_inline_layout_matrix, parse_mode='markdown')
    except MessageNotModifiedError:
        pass
    except Exception as render_layer_exception:
        logger.warning(f"[-] Interface update conflict bypassed: {render_layer_exception}")
        try: 
            await client.send_message(event.chat_id, catalog_display_interface_ui, buttons=interactive_inline_layout_matrix, parse_mode='markdown')
        except Exception as ultimate_fallback_failure:
            logger.error(f"[-] Failed to execute fallback UI message routing: {ultimate_fallback_failure}")

# ====================================================================
#              🎯 CORE STREAM ROUTING TERMINAL SYSTEM
# ====================================================================
@client.on(events.NewMessage)
async def core_search_router(event: events.NewMessage.Event):
    """The central message processing pipeline that routes user queries and verifies captchas."""
    if not event.text or not event.sender_id:
        return
        
    user_input_raw_text = event.text.strip()
    
    # Intercept commands to keep the search stream clean
    if user_input_raw_text.startswith('/') or user_input_raw_text in [
        "🔍 Start Search", "🔗 Refer Link", "👤 Profile Summary", 
        "🎁 Daily Reward Token", "🎟️ Redeem Voucher", "👑 Premium Upgrade Upgrade Upgrade"
    ]: 
        return

    user_id_string = str(event.sender_id)
    user_display_name = f"{event.sender.first_name or ''} {event.sender.last_name or ''}".strip() or "Explorer"
    
    # ─── SECTION 1: SECURITY CAPTCHA INTERCEPTION ROUTE ───
    if user_id_string in CAPTCHA_CACHE:
        async with acquire_user_interaction_lock(user_id_string):
            cached_captcha_dictionary = CAPTCHA_CACHE[user_id_string]
            
            if user_input_raw_text.isdigit() and int(user_input_raw_text) == cached_captcha_dictionary["answer"]:
                await DatabaseManager.set_verified(user_id_string)
                del CAPTCHA_CACHE[user_id_string]
                
                success_clearance_interface = (
                    "✅ ══════════════════════ ✅\n"
                    "      SECURITY AUTHENTICATION CLEARANCE COMPLETE\n"
                    "✅ ══════════════════════ ✅\n\n"
                    "Access authorized. Your hardware configuration has been registered to the cloud storage infrastructure."
                )
                await event.reply(success_clearance_interface, parse_mode='markdown')
                
                if cached_captcha_dictionary["ref"]:
                    await DatabaseManager.apply_referral_credit(cached_captcha_dictionary["ref"])
                    try: 
                        referral_success_alert_string = (
                            "🔔 ══════════════════════ 🔔\n"
                            "       AFFILIATE SYSTEM INBOUND NODE NOTIFICATION\n"
                            "🔔 ══════════════════════ 🔔\n\n"
                            f"A new user node (`@{cached_captcha_dictionary['username']}`) cleared validation checks using your referral link.\n\n"
                            "➕ **Credit Applied:** `+5` daily query limits permanently added to your account ceiling balance."
                        )
                        await client.send_message(int(cached_captcha_dictionary["ref"]), referral_success_alert_string, parse_mode='markdown')
                    except Exception as parent_notification_anomaly:
                        logger.error(f"[-] Referral notice delivery failed: {parent_notification_anomaly}")
                    
                    try:
                        await event.reply(f"🎉 **Affiliate Packet Active:** Linked successfully under network workspace profile: `{cached_captcha_dictionary['ref']}`.")
                    except Exception: 
                        pass
                
                admin_telemetry_html_log = (
                    f"👤 <b>NEW SYSTEM NODE LINK SYNCHRONIZED</b>\n"
                    f"🆔 <b>User Target ID</b>: <code>{user_id_string}</code>\n"
                    f"🏷️ <b>Username Handle</b>: @{cached_captcha_dictionary['username']}\n"
                    f"🔗 <b>Affiliate Parent Origin</b>: <code>{cached_captcha_dictionary['ref'] or 'Organic Unreferenced Entry'}</code>\n"
                    f"🛰️ <b>Status</b>: Verification Complete"
                )
                await forward_to_log_channel(admin_telemetry_html_log)
                await send_advanced_dashboard(event.chat_id, user_id_string, user_display_name)
            else:
                left_operand, right_operand, new_matching_solution = generate_math_captcha()
                CAPTCHA_CACHE[user_id_string]["answer"] = new_matching_solution
                
                captcha_retry_interface = (
                    "❌ ══════════════════════ ❌\n"
                    "      VERIFICATION INCORRECT - TRY AGAIN\n"
                    "❌ ══════════════════════ ❌\n\n"
                    "The text input did not match the validation formula solution.\n\n"
                    f"👉 Solve: `{left_operand} + {right_operand} = ?`"
                )
                await event.reply(captcha_retry_interface, parse_mode='markdown')
            return

    user_profile_dataset_record = await DatabaseManager.get_user(user_id_string)
    if not user_profile_dataset_record or user_profile_dataset_record.get('banned', 0) == 1: 
        return

    # ─── SECTION 2: PROMOTIONAL VOUCHER DEPLOYMENT STREAM ───
    if user_id_string in COUPON_INPUT_CACHE:
        async with acquire_user_interaction_lock(user_id_string):
            targeted_voucher_code_input = user_input_raw_text.upper()
            del COUPON_INPUT_CACHE[user_id_string]
            
            coupon_redemption_transaction_status = await DatabaseManager.redeem_coupon(user_id_string, targeted_voucher_code_input)
            
            if coupon_redemption_transaction_status == "INVALID":
                await event.reply("❌ **Redemption Refused:** The voucher code structure is unrecognized or corrupt.", parse_mode='markdown')
            elif coupon_redemption_transaction_status == "EXPIRED":
                await event.reply("❌ **Redemption Refused:** This promotion code lifecycle milestone has expired.", parse_mode='markdown')
            elif coupon_redemption_transaction_status == "MAXED":
                await event.reply("❌ **Redemption Refused:** Maximum usage redundancy limits reached for this coupon payload.", parse_mode='markdown')
            elif coupon_redemption_transaction_status == "ALREADY_USED":
                await event.reply("❌ **Redemption Refused:** You have already claimed this token voucher pack structural allocation.", parse_mode='markdown')
            else:
                coupon_success_interface = (
                    "🎉 ══════════════════════ 🎉\n"
                    "       VOUCHER SYSTEM PROCESSED SUCCESSFULLY\n"
                    "🎉 ══════════════════════ 🎉\n\n"
                    f"Voucher code successfully applied to your account profile.\n\n"
                    f"🎁 **Reward Allocated:** `+{coupon_redemption_transaction_status}` extra permanent search tokens added to your balance."
                )
                await event.reply(coupon_success_interface, parse_mode='markdown')
                
                coupon_log_telemetry_html = (
                    f"🎟️ <b>COUPON REDEEMED VALIDATION RECORD</b>\n"
                    f"👤 <b>User Node ID</b>: <code>{user_id_string}</code>\n"
                    f"🔑 <b>Code String</b>: <code>{targeted_voucher_code_input}</code>\n"
                    f"🎁 <b>Credit Dispatched</b>: +{coupon_redemption_transaction_status} Quota Tokens"
                )
                await forward_to_log_channel(coupon_log_telemetry_html)
            return

    # ─── SECTION 3: INBOUND FINANCIAL TRANSACTION SCREENSHOT AUDITING ───
    if event.message.photo:
        try:
            receipt_forwarding_confirmation_interface = (
                "📥 ══════════════════════ 📥\n"
                "       FINANCIAL AUDIT DISPATCH COMPLETED\n"
                "📥 ══════════════════════ 📥\n\n"
                "Your payment receipt screenshot has been safely routed to manual verification logs.\n\n"
                "⏳ **Audit Status:** Pending Review\n"
                "An administrator will audit the transaction details shortly. Thank you for your patience!"
            )
            
            admin_receipt_routing_dashboard = (
                f"📥 <b>INBOUND AUDIT PAYMENT SCREENSHOT RECEIPT</b>\n"
                f"👤 <b>User Reference Account</b>: <code>{user_id_string}</code>\n"
                f"🏷️ <b>Username Node</b>: @{event.sender.username or 'No Handle'}"
            )
            
            admin_interactive_inline_audit_controls = [
                [
                    Button.inline("🥈 Verify Silver", f"adm_app_{user_id_string}_Silver"), 
                    Button.inline("🥇 Verify Gold", f"adm_app_{user_id_string}_Gold")
                ],
                [
                    Button.inline("👑 Verify Elite (₹149)", f"adm_app_{user_id_string}_Elite")
                ],
                [
                    Button.inline("❌ Reject Payment Request", f"adm_dec_{user_id_string}_None")
                ]
            ]
            
            await client.send_message(
                ADMIN_ID, 
                admin_receipt_routing_dashboard, 
                file=event.message.photo, 
                buttons=admin_interactive_inline_audit_controls,
                parse_mode='html'
            )
            await event.reply(receipt_forwarding_confirmation_interface, parse_mode='markdown')
        except Exception as receipt_forwarding_anomaly:
            logger.error(f"[-] Failed to forward incoming payment screenshot to admin: {receipt_forwarding_anomaly}")
        return

    # ─── SECTION 4: MANDATORY SUBSCRIPTION ENFORCEMENT AUDITS ───
    if not await check_membership(event.sender_id):
        lockout_enforcement_interface = (
            "⚠️ ══════════════════════ ⚠️\n"
            "       MANDATORY SUBSCRIPTION LINKAGE REQUIRED\n"
            "⚠️ ══════════════════════ ⚠️\n\n"
            "To access our high-speed search database clusters, you must join our official updates channels first.\n\n"
            "📢 **Please join the channel nodes listed below:**"
        )
        
        subscription_channel_link_matrix = [[Button.url(f"📢 Join Channel Asset Node", current_channel_item['link'])] for current_channel_item in REQUIRED_CHANNELS]
        subscription_channel_link_matrix.append([Button.inline("🔄 Re-Verify Joining Status", b"verify_subscription")])
        
        await event.reply(lockout_enforcement_interface, buttons=subscription_channel_link_matrix, parse_mode='markdown')
        return

    # ─── SECTION 5: ACCOUNT DAILY RATELIMIT CONTROLS ───
    is_system_administrator = int(user_id_string) == ADMIN_ID
    if not is_system_administrator and user_profile_dataset_record['searches_today'] >= user_profile_dataset_record['max_limit']:
        over_limit_warning_interface = (
            "🚨 ══════════════════════ 🚨\n"
            "       DAILY SEARCH LIMIT CEILING SATURATED\n"
            "🚨 ══════════════════════ 🚨\n\n"
            f"Your account search limits are currently saturated at (`{user_profile_dataset_record['searches_today']}/{user_profile_dataset_record['max_limit']}`).\n\n"
            "💎 **Unlock Unlimited Access:**\n"
            "Tap the upgrade button on the menu below to unlock higher daily ceilings and ultra-premium speeds."
        )
        await event.reply(over_limit_warning_interface, parse_mode='markdown')
        return

    # ─── SECTION 6: HIGH-CAPACITY CROSS-CHANNEL CATALOG SEARCH QUERY EXECUTOR ───
    targeted_search_query_key = event.text.strip()
    if len(targeted_search_query_key) < 2: 
        return

    try:
        # Visual transition animations to create a premium feel
        dynamic_animated_ticker_node = await event.respond("🔍 **INITIALIZING QUAD-ENGINE SEARCH MAINFRAME...**")
        await asyncio.sleep(0.4)
        await dynamic_animated_ticker_node.edit("⏳ **[████░░░░░░░░░░░] 35% Scanning Cluster File Servers...**")
        await asyncio.sleep(0.3)
        await dynamic_animated_ticker_node.edit("⏳ **[██████████░░░░░] 70% Aggregating Index Registries...**")
        await asyncio.sleep(0.2)
        await dynamic_animated_ticker_node.edit("⏳ **[███████████████] 100% Core Matrix Synced! Compiling UI...**")
        
        located_catalog_index_matches = await DatabaseManager.query_movie_catalog(targeted_search_query_key)

        if not located_catalog_index_matches:
            no_matches_found_interface = (
                "❌ ══════════════════════ ❌\n"
                "       ZERO INDEX MATCHES LOCATED IN CLUSTERS\n"
                "❌ ══════════════════════ ❌\n\n"
                f"The system scanned all 5 database nodes but found no matching records for: `{targeted_search_query_key}`.\n\n"
                "💡 **Recommendations:**\n"
                "◆ Double check for spelling typos.\n"
                "◆ Try searching with a broader keyword (e.g., search 'Batman' instead of 'Batman Begins 2005 Bluray')."
            )
            await dynamic_animated_ticker_node.edit(no_matches_found_interface, parse_mode='markdown')
            return

        # Cache the current search context to handle pagination queries
        PAGINATION_CACHE[user_id_string] = {
            "query": targeted_search_query_key,
            "matches": located_catalog_index_matches,
            "current_page": 1,
            "timestamp": time.time()
        }

        await dynamic_animated_ticker_node.delete()
        await RenderPaginationView(event, targeted_search_query_key, located_catalog_index_matches, page=1)
        
    except Exception as query_routing_system_failure:
        logger.error(f"[-] Central search query handler collapsed: {query_routing_system_failure}")
        traceback.print_exc()

# ====================================================================
#               🚀 INFRASTRUCTURE SYSTEM INITIALIZATION
# ====================================================================
async def main_environment_bootstrap():
    """Validates structural tokens, runs backend setups, and brings the engine online."""
    logger.info("⚡ =================================================== ⚡")
    logger.info("[+] Starting the Quad-Engine Enterprise System...")
    logger.info("⚡ =================================================== ⚡")
    
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("[+] Telethon client authenticated successfully.")
        
        await DatabaseManager.initialize()
        logger.info("[+] Distributed database architectures verified.")
        
        register_admin_handlers(client)
        logger.info("[+] Administrative system handlers active.")
        
        # Start the background service worker loop
        asyncio.create_task(background_memory_sanitizer_daemon())
        
        bot_system_user_profile = await client.get_me()
        logger.info(f"[🚀] Ultra-Premium Engine Online: @{bot_system_user_profile.username} is fully operational.")
    except Exception as bootstrap_critical_fault:
        logger.critical(f"[-] Bootstrap failed during initialization sequence: {bootstrap_critical_fault}")
        sys.exit(1)

if __name__ == '__main__':
    # Set execution parameters cleanly across platforms
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        client.loop.run_until_complete(main_environment_bootstrap())
        client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info("[!] System shutdown command received via hardware keyboard loop.")
    finally:
        logger.info("[⚠️] Infrastructure engine offline. Connection sockets safely closed.")
# ====================================================================
#                     🏁 END OF PRODUCTION CORE FILE
# ====================================================================
