# config.py
import os

# --- ⚙️ PRODUCTION CREDENTIALS ---
API_ID = 35485985              
API_HASH = '5441c09a9c8bf58374e1f8f227b95794'     
BOT_TOKEN = '8791980160:AAGU4JwkQXL1dxgRqVUxgeARJROwLfL19g4'   
ADMIN_ID = 7952327997                 
LOG_CHANNEL_ID = -1003559645437

# --- 📢 TARGET CHANNEL CHANNELS ---
REQUIRED_CHANNELS = [
    {"id": -1003985304953, "link": "https://t.me/yagamicorporation"},
    {"id": -1002304109021, "link": "https://t.me/+7q9n0MEJ0Jk1N2U1"},
]       

CHANNEL_A_ID = -1002107962104
CHANNEL_B_ID = -1003943845412
CHANNEL_C_ID = -1002488275573
CHANNEL_D_ID = -1002296093247
CHANNEL_E_ID = -1002394593898

# --- 🗄️ STORAGE SYSTEM SNAPSHOT PATHS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_CORE = os.path.join(SCRIPT_DIR, "alldata.db")             
DB_ENGINE_A = os.path.join(SCRIPT_DIR, "sourcechannel.db")     
DB_ENGINE_B = os.path.join(SCRIPT_DIR, "animehubinfinite.db")  
DB_ENGINE_C = os.path.join(SCRIPT_DIR, "ritsamhub1.db")  
DB_ENGINE_D = os.path.join(SCRIPT_DIR, "ritsamhub3.db")  
DB_ENGINE_E = os.path.join(SCRIPT_DIR, "ritsamhub48.db")  

# --- 🧠 GLOBAL RUNTIME SYSTEMS STATE ---
PAGINATION_CACHE = {}
CAPTCHA_CACHE = {}
COUPON_INPUT_CACHE = {}
BACKUP_ABORT_SIGNAL = {"abort": False}
