"""
=====================================================================
   3FH PARTY ROYAL - Discord Bot
   بوت متكامل: ترحيب + نظام تذاكر + اقتراحات + إعلانات + ردود آلية
   Python 3.12  |  discord.py 2.x
=====================================================================
طريقة التشغيل محلياً:
   1) pip install -r requirements.txt
   2) عدّل ملف .env وضع فيه التوكن وجميع الـ IDs
   3) python main.py

طريقة التشغيل على Railway:
   1) ارفع المشروع (main.py + requirements.txt + Procfile) على GitHub وربطه بـ Railway
      أو ارفعه مباشرة عبر Railway CLI.
   2) من تبويب Variables بمشروع Railway ضيف نفس متغيرات ملف .env
      (TOKEN, GUILD_ID, ...إلخ) - بدون رفع ملف .env نفسه.
   3) (اختياري لكن يُنصح فيه) أضف Volume من تبويب Settings وحط مساره
      بمتغير DATA_DIR (مثلاً /data) عشان قاعدة البيانات والبنرات
      ما تنمسح مع كل ريديبلوي - الفولدر الافتراضي "data" مؤقت وينمسح.
   4) Railway بيشغل العملية تلقائياً حسب سطر "worker: python main.py"
      الموجود بملف Procfile.
=====================================================================
"""

import os
import json
import re
import random
import io
import math
import asyncio
import functools
import glob
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops, features

# =====================================================================
#                        ⚙️  الإعدادات العامة (IDs)
#   كل الـ IDs تُقرأ من ملف .env - لا تكتب أي معرف داخل الكود مباشرة
# =====================================================================
load_dotenv()

TOKEN = os.getenv("TOKEN")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# --- رتبة الإدارة العليا (تُستخدم مع صاحب السيرفر للأوامر الحساسة زي متتبع الصوتيات) ---
OWNER_ROLE_ID = int(os.getenv("OWNER_ROLE_ID", "0"))

# --- نظام الترحيب ---
# ملاحظة: إحداثيات صورة العضو واسمه بالبطاقة صارت تُضبط من ديسكورد مباشرة بأمر /set_welcome_position
# (تُحفظ بقاعدة البيانات) بدل ملف .env - شوف أمر /test_welcome للمعاينة بعد كل تعديل.
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
WELCOME_ROLE_ID = int(os.getenv("AUTO_ROLE_ID", "0"))
WELCOME_FONT_PATH = os.getenv("WELCOME_FONT_PATH", "")  # مسار ملف خط .ttf (اختياري)

# القيم الافتراضية لإحداثيات البطاقة (تُستخدم أول مرة قبل أي تعديل بأمر /set_welcome_position)
DEFAULT_WELCOME_POSITION = {
    "avatar_x": 150,
    "avatar_y": 150,
    "avatar_size": 180,
    "text_x": 500,
    "text_y": 130,
    "text_size": 48,
    "text_color": "#FFFFFF",
}

# --- نظام التذاكر ---
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))
TICKET_PANEL_CHANNEL_ID = int(os.getenv("TICKET_PANEL_CHANNEL_ID", "0"))
TICKET_LOG_CHANNEL_ID = int(os.getenv("TICKET_LOG_CHANNEL_ID", "0"))
TICKET_BANNER_URL = os.getenv("TICKET_BANNER_URL", "")

# رتب الإدارة التي تستطيع رؤية واستلام التذاكر (عدة رتب مفصولة بفاصلة في .env)
# مثال: STAFF_ROLE_IDS=111111111111111111,222222222222222222,333333333333333333
STAFF_ROLE_IDS = [int(x) for x in os.getenv("STAFF_ROLE_IDS", "").split(",") if x.strip().isdigit()]

# --- نظام الاقتراحات ---
SUGGESTIONS_CHANNEL_ID = int(os.getenv("SUGGESTION_CHANNEL_ID", "0"))

# --- الردود الآلية ---
# لو تُرك = 0 فالردود الآلية تعمل في كل الرومات
GENERAL_CHAT_ID = int(os.getenv("GENERAL_CHAT_ID", "0"))
MEMBER_ROLE_ID = int(os.getenv("MEMBER_ROLE_ID", "0"))  # لو تركته 0 فالردود الآلية تعمل للجميع
CORRECTIONS_CHANNEL_ID = int(os.getenv("CORRECTIONS_CHANNEL_ID", "0"))  # روم التصحيح الإملائي

# --- نظام اللفلات (XP) ---
LEVEL_UP_CHANNEL_ID = int(os.getenv("LEVEL_UP_CHANNEL_ID", "0"))  # لو تركته 0 يُعلن بنفس روم الرسالة
XP_MIN_PER_MESSAGE = 15
XP_MAX_PER_MESSAGE = 25
XP_COOLDOWN_SECONDS = 60  # أقل مدة بين كل XP وثانية لنفس العضو (يمنع تكرار الرسائل لتجميع XP)

# --- الأذكار ---
ATHKAR_CHANNEL_ID = int(os.getenv("ATHKAR_CHANNEL_ID", "0"))  # لو تركته 0 يرسل بنفس الروم اللي كتب فيه الأمر

# --- لعبة البنك (Mines) ---
BANK_CHANNEL_ID = int(os.getenv("BANK_CHANNEL_ID", "0"))  # لو تركته 0 تشتغل بكل الرومات
STARTING_BALANCE = 1000       # الرصيد الابتدائي لأي عضو جديد
MINES_GRID_SIZE = 9           # عدد المربعات بالشبكة (3x3)
MINES_BOMB_COUNT = 1          # عدد القنابل المخفية
MINES_MULTIPLIER_STEP = 0.3   # مقدار زيادة الأرباح بكل مربع آمن
MINES_BASE_REWARD = 100        # المكافأة الأساسية - لا يوجد رهان ولا خصم عند الخسارة

# --- ثيم 3FH BANK (يُطبّق على كل إيمبدات وصور نظام البنك) ---
BANK_BRAND_NAME = "🏦 3FH BANK"
BANK_FOOTER_TEXT = "3FH PARTY ROYAL"
BANK_WHEEL_SLICE_COLORS = [(56, 60, 68, 255), (38, 41, 47, 255)]

# --- نظام البنك الموسّع (بدون سلاش - تكتب الكلمة بروم البنك وتشتغل لحالها) ---
# مدة الكولداون لكل أمر بالثواني - 0 = جاهز دائمًا بدون انتظار
BANK_COOLDOWNS = {
    "راتب": 86400,     # مرة كل 24 ساعة
    "بخشيش": 300,      # 5 دقائق
    "حظ": 180,         # 3 دقائق
    "روليت": 300,      # 5 دقائق
    "نهب": 600,        # 10 دقائق
    "رهان": 30,        # نصف دقيقة
    "استثمار": 291,    # ~4:51 دقيقة (نفس التوقيت اللي بصور السيرفر المرجعي)
    "تداول": 255,      # ~4:15 دقيقة
    "قمار": 60,        # دقيقة وحدة
    "نرد": 274,        # ~4:34 دقيقة
    "لعبه": 0,
    "لون": 0,
    "فواكه": 0,
    "تسريع": 0,
    "بيع": 0,
    "شراء": 0,
    "سوق": 0,
}
# ترتيب عرض حالة الأوامر بأمر "وقت" (نفس ترتيب صور السيرفر المرجعي)
BANK_STATUS_ORDER = [
    "راتب", "بخشيش", "حظ", "روليت", "نهب", "رهان",
    "استثمار", "تداول", "قمار", "نرد", "لعبه", "لون", "فواكه",
    "تسريع", "بيع", "شراء", "سوق",
]

SALARY_AMOUNT = 2000
TIP_MIN, TIP_MAX = 200, 900
LUCK_MIN, LUCK_MAX = -400, 700

ROULETTE_PRIZES = [  # (القيمة أو "gold:عدد", الوزن الاحتمالي)
    (1500, 22), (6000, 18), (9000, 15), (12000, 12), (15000, 9),
    (19000, 7), (50000, 4), (100000, 2), ("gold:5", 7), ("gold:10", 4),
]

ROB_SUCCESS_CHANCE = 0.65
ROB_PERCENT = 0.01            # نسبة السرقة من رصيد الضحية (1%)
ROB_FAIL_FINE = 500  # غرامة فشل السرقة (مبلغ ثابت)

PROTECTION_HOURS = 5
PROTECTION_COST = 2000

INVEST_MIN_PCT, INVEST_MAX_PCT = -0.35, 0.90   # استثمار: مخاطرة أقل ومدى أوسع
TRADE_MIN_PCT, TRADE_MAX_PCT = -0.55, 1.35     # تداول: مخاطرة أعلى وعائد أسرع وأسرع رجعية

DICE_MIN_BET = GAMBLE_MIN_BET = BET_MIN_BET = 100
TRADE_MIN_BET, INVEST_MIN_BET = 200, 200

SPEEDUP_GOLD_COST = 30   # تكلفة "تسريع" بالذهب - يشيل كل الكولداونات الحالية دفعة وحدة

# --- كرت العمليات (إيداع/خصم) الموحّد ---
PAY_CARD_NAME = "96Pay"
BANK_OWNER_ROLE_ID = int(os.getenv("BANK_OWNER_ROLE_ID", "0"))  # اختياري - رتبة تُعتبر "المالك" (شيخ)

# --- متجر الممتلكات (بيع / شراء) ---
PROPERTY_CATALOG = {
    "car": {"name": "سياره", "emoji": "🚗", "price": 3000},
    "house": {"name": "بيت", "emoji": "🏠", "price": 5000},
    "land": {"name": "اراضي", "emoji": "🗺️", "price": 10000},
    "store": {"name": "متجر", "emoji": "🏪", "price": 8000},
    "building": {"name": "مبنى", "emoji": "🏢", "price": 20000},
    "company": {"name": "شركه", "emoji": "🏭", "price": 50000},
}
PROPERTY_SELL_RATIO = 0.6   # يُباع كل عنصر بـ 60% من سعر الشراء
STOCK_PRICE = 500           # سعر السهم الواحد (ثابت ومبسط)

# --- ألوان الإمبيدات ---
MAIN_COLOR = 0x2F3136
SUCCESS_COLOR = 0x57F287
DANGER_COLOR = 0xED4245
WELCOME_COLOR = 0xF1C40F  # ذهبي يطابق هوية 3FH PARTY ROYAL


# =====================================================================
#                     💾  قاعدة بيانات محلية (JSON)
#   تُستخدم لحفظ: رقم آخر تذكرة - التذاكر المفتوحة - بيانات كل تذكرة
#   - الأصوات على الاقتراحات - التقييمات (كل هذا يبقى بعد إعادة التشغيل)
# =====================================================================
DATA_DIR = os.getenv("DATA_DIR", "data")  # لو ثبّت Volume براي لواي، حط مساره هنا عشان بياناتك ما تروح مع كل ريديبلوي
DB_FILE = os.path.join(DATA_DIR, "database.json")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
BANNERS_DIR = os.path.join(DATA_DIR, "banners")
FILES_DIR = os.path.join(DATA_DIR, "files")  # ملفات/صور عامة تُرفع عبر /save_file و/list_files


def ensure_data_files():
    """التأكد من وجود مجلد وملف قاعدة البيانات، وإنشائهم إذا لم يكونا موجودين."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    os.makedirs(BANNERS_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    if not os.path.exists(DB_FILE):
        default_db = {
            "ticket_counter": 0,       # آخر رقم تذكرة تم استخدامه
            "open_tickets": {},        # {user_id: channel_id} - لمنع فتح أكثر من تذكرة
            "tickets": {},             # {channel_id: {...بيانات التذكرة...}}
            "suggestions": {},         # {message_id: {"up": [], "down": []}}
            "ratings": {},             # {ticket_number: {"stars": int, "user_id": int}}
            "corrections": {},         # {الكلمة_الخطأ: الكلمة_الصح} - نظام التصحيح الإملائي
            "dot_sent_users": [],      # قائمة آيديات الأعضاء اللي سبق أرسلوا "." (لتمييز أول مرة عن المرات اللي بعدها)
            "auto_replies": {},        # {الكلمة_المحفزة: {"response": الرد, "role_id": رتبة اختيارية أو None}} - ردود آلية مخصصة تُضاف من ديسكورد
            "levels": {},              # {user_id: {"xp": int, "level": int}} - نظام اللفلات
            "economy": {},              # {user_id: الرصيد} - نظام البنك
            "gold": {},                 # {user_id: كمية الذهب} - عملة ثانوية (تسريع...)
            "properties": {},           # {user_id: {"car":0,"house":0,...,"stocks":0}} - ممتلكات البنك
            "protection": {},           # {user_id: timestamp انتهاء الحماية من السرقة}
            "bank_cooldowns": {},       # {user_id: {اسم_الأمر: timestamp الجاهزية}}
            "bank_history": {},         # {user_id: {"استثمار":[أرصدة سابقة],"تداول":[...]}} - لرسم الشارت
            "color_game": {},           # {user_id: {"count": محاولات متبقية, "reset_at": وقت التجديد}} - لعبة لون
            "dm_broadcast_progress": None,  # حالة رسالة الخاص الجماعية الجارية (لو انقطعت يقدر البوت يكملها بعد إعادة التشغيل)
            "bot_voice_uptime": {       # مدة بقاء البوت نفسه بروم صوتي (يحدده الأونر/الإدارة العليا)
                "voice_channel_id": None,
                "connected_since": None,   # timestamp لحظة بداية الجلسة الحالية (None = مو متصل حالياً)
                "total_seconds": 0,        # إجمالي الوقت المتراكم من كل الجلسات السابقة
            },
            "settings": {              # إعدادات قابلة للتغيير من ديسكورد مباشرة (بدون تعديل .env)
                "ticket_banner_path": None,
                "suggestion_banner_path": None,
                "welcome_template_path": None,
                "welcome_position": dict(DEFAULT_WELCOME_POSITION),
                "ticket_allowed_roles": [],   # فاضية = فتح التذاكر متاح للجميع
                "custom_messages": {},        # {مفتاح_الرسالة: {الحقل: القيمة}} - تعديلات /edit_message
            },
        }
        save_db(default_db)


def load_db() -> dict:
    """قراءة قاعدة البيانات من ملف JSON، مع ترقيع تلقائي لأي حقول ناقصة بالقواعد القديمة."""
    ensure_data_files()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("bot_voice_uptime", {
        "voice_channel_id": None, "connected_since": None, "total_seconds": 0,
    })
    if "settings" not in data:
        data["settings"] = {
            "ticket_banner_path": None,
            "suggestion_banner_path": None,
            "welcome_template_path": None,
            "welcome_position": dict(DEFAULT_WELCOME_POSITION),
            "ticket_allowed_roles": [],
            "custom_messages": {},
        }
    else:
        data["settings"].setdefault("ticket_banner_path", None)
        data["settings"].setdefault("suggestion_banner_path", None)
        data["settings"].setdefault("welcome_template_path", None)
        data["settings"].setdefault("welcome_position", dict(DEFAULT_WELCOME_POSITION))
        data["settings"].setdefault("ticket_allowed_roles", [])
        data["settings"].setdefault("custom_messages", {})
        # تنظيف أي بقايا من نظام الرومات المؤقتة القديم
        data["settings"].pop("temp_voice_hubs", None)
        data["settings"].pop("temp_voice_hub_id", None)
        data["settings"].pop("temp_voice_category_id", None)
        data["settings"].pop("temp_voice_name_template", None)
        data["settings"].pop("antinuke", None)
        data["settings"].pop("dashboard_secret", None)
        data["settings"].pop("welcome_banner_path", None)
        data["settings"].pop("announcement_banner_path", None)
    data.setdefault("corrections", {})
    data.setdefault("dot_sent_users", [])
    data.setdefault("auto_replies", {})
    data.setdefault("levels", {})
    data.setdefault("economy", {})
    data.setdefault("gold", {})
    data.setdefault("properties", {})
    data.setdefault("protection", {})
    data.setdefault("bank_cooldowns", {})
    data.setdefault("bank_history", {})
    data.setdefault("market", {"stock_price": STOCK_PRICE, "updated_at": 0, "last_change_pct": 0.0, "history": [STOCK_PRICE]})
    data.setdefault("color_game", {})
    data.setdefault("dm_broadcast_progress", None)
    return data


def save_db(data: dict) -> None:
    """حفظ قاعدة البيانات في ملف JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# =====================================================================
#                         🤖  إعداد البوت
# =====================================================================
intents = discord.Intents.default()
intents.members = True          # مطلوب لنظام الترحيب (فعّله من Developer Portal أيضاً)
intents.message_content = True  # مطلوب لقراءة الردود الآلية
intents.presences = True        # مطلوب لمعرفة تواجد الإدارة أونلاين (فعّله من Developer Portal أيضاً - Presence Intent)

bot = commands.Bot(command_prefix="!", intents=intents)

# متغير عام يتتبع مهمة استكمال رسالة الخاص الجماعية (لو انقطعت) - يمنع تكرارها لو on_ready صار أكثر من مرة
_dm_broadcast_task: asyncio.Task | None = None


# كاش للويبهوكات حتى لا ننشئ ويبهوك جديد بكل رسالة (نحتفظ بواحد لكل روم)
_webhook_cache: dict[int, discord.Webhook] = {}


async def get_channel_webhook(channel: discord.TextChannel) -> discord.Webhook:
    """يرجع ويبهوك خاص بهذا الروم (ينشئه لو مو موجود) - يُستخدم لإرسال رسائل بمظهر العضو نفسه."""
    if channel.id in _webhook_cache:
        return _webhook_cache[channel.id]

    webhooks = await channel.webhooks()
    webhook = discord.utils.get(webhooks, name="3FH-Corrections")
    if webhook is None:
        webhook = await channel.create_webhook(name="3FH-Corrections")

    _webhook_cache[channel.id] = webhook
    return webhook


def is_staff(member: discord.Member) -> bool:
    """التحقق إن كان العضو يملك إحدى رتب الإدارة المحددة أو صلاحية Administrator."""
    if member.guild_permissions.administrator:
        return True
    member_role_ids = {r.id for r in member.roles}
    return any(rid in member_role_ids for rid in STAFF_ROLE_IDS)


def any_staff_available(guild: discord.Guild) -> bool:
    """يتحقق إذا فيه أي عضو إدارة متواجد أونلاين أو خامل حالياً (يحتاج Presence Intent مفعّل)."""
    for member in guild.members:
        if member.bot:
            continue
        if not is_staff(member):
            continue
        if member.status in (discord.Status.online, discord.Status.idle):
            return True
    return False


def get_balance(user_id: int) -> int:
    """جلب رصيد العضو، وإنشاء رصيد ابتدائي له لو أول مرة."""
    db = load_db()
    uid = str(user_id)
    if uid not in db["economy"]:
        db["economy"][uid] = STARTING_BALANCE
        save_db(db)
    return db["economy"][uid]


def update_balance(user_id: int, delta: int) -> int:
    """تعديل رصيد العضو بمقدار delta (موجب أو سالب) وإرجاع الرصيد الجديد."""
    db = load_db()
    uid = str(user_id)
    current = db["economy"].get(uid, STARTING_BALANCE)
    new_balance = max(0, current + delta)
    db["economy"][uid] = new_balance
    save_db(db)
    return new_balance


# =====================================================================
#            🏦  دوال مساعدة لنظام البنك الموسّع (بدون سلاش)
# =====================================================================
def format_amount(n: int) -> str:
    """يهيّئ رقم كبير بصيغة مختصرة (زي 55e86) عشان الأرقام الضخمة تظل قابلة للقراءة."""
    n = int(n)
    if n < 100_000:
        return f"{n:,}"
    s = str(abs(n))
    mantissa = s[:2]
    exponent = len(s) - 2
    sign = "-" if n < 0 else ""
    return f"{sign}{mantissa}e{exponent}"


def get_gold(user_id: int) -> int:
    db = load_db()
    return db["gold"].get(str(user_id), 0)


def update_gold(user_id: int, delta: int) -> int:
    db = load_db()
    uid = str(user_id)
    current = db["gold"].get(uid, 0)
    new_amount = max(0, current + delta)
    db["gold"][uid] = new_amount
    save_db(db)
    return new_amount


def get_properties(user_id: int) -> dict:
    db = load_db()
    uid = str(user_id)
    props = db["properties"].get(uid)
    if not props:
        props = {key: 0 for key in PROPERTY_CATALOG}
        props["stocks"] = 0
        db["properties"][uid] = props
        save_db(db)
    else:
        for key in PROPERTY_CATALOG:
            props.setdefault(key, 0)
        props.setdefault("stocks", 0)
    return props


def update_property(user_id: int, key: str, delta: int) -> int:
    db = load_db()
    uid = str(user_id)
    props = db["properties"].setdefault(uid, {k: 0 for k in PROPERTY_CATALOG})
    props.setdefault("stocks", 0)
    props[key] = max(0, props.get(key, 0) + delta)
    save_db(db)
    return props[key]


MARKET_UPDATE_SECONDS = 300
MARKET_MIN_PRICE = 100
MARKET_MAX_PRICE = 5000

def get_stock_market(update_if_due: bool = True) -> dict:
    """سوق أسهم افتراضي محفوظ، يتغير سعره كل خمس دقائق."""
    db = load_db()
    market = db.setdefault("market", {"stock_price": STOCK_PRICE, "updated_at": 0, "last_change_pct": 0.0, "history": [STOCK_PRICE]})
    market.setdefault("stock_price", STOCK_PRICE)
    market.setdefault("updated_at", 0)
    market.setdefault("last_change_pct", 0.0)
    market.setdefault("history", [market["stock_price"]])
    now = datetime.now(timezone.utc).timestamp()
    if update_if_due and now - float(market.get("updated_at", 0)) >= MARKET_UPDATE_SECONDS:
        old_price = max(MARKET_MIN_PRICE, int(market.get("stock_price", STOCK_PRICE)))
        new_price = int(max(MARKET_MIN_PRICE, min(MARKET_MAX_PRICE, old_price * (1 + random.uniform(-0.08, 0.08)))))
        market["stock_price"] = new_price
        market["last_change_pct"] = ((new_price - old_price) / old_price) * 100 if old_price else 0.0
        market["updated_at"] = now
        history = market.setdefault("history", [])
        history.append(new_price)
        del history[:-12]
        db["market"] = market
        save_db(db)
    return market

def current_stock_price() -> int:
    return int(get_stock_market().get("stock_price", STOCK_PRICE))

def net_worth(user_id: int) -> int:
    """إجمالي الثروة: الكاش + الممتلكات + الأسهم بسعر السوق الحالي."""
    cash = get_balance(user_id)
    props = get_properties(user_id)
    props_value = sum(props.get(k, 0) * PROPERTY_CATALOG[k]["price"] for k in PROPERTY_CATALOG)
    stocks_value = props.get("stocks", 0) * current_stock_price()
    return cash + props_value + stocks_value


def is_protected(user_id: int) -> float:
    """يرجع 0 لو مو محمي، أو عدد الثواني المتبقية للحماية."""
    db = load_db()
    until = db["protection"].get(str(user_id), 0)
    remaining = until - datetime.now(timezone.utc).timestamp()
    return max(0.0, remaining)


def set_protection(user_id: int, hours: float) -> None:
    db = load_db()
    db["protection"][str(user_id)] = datetime.now(timezone.utc).timestamp() + hours * 3600
    save_db(db)


def get_cooldown_remaining(user_id: int, action: str) -> float:
    duration = BANK_COOLDOWNS.get(action, 0)
    if duration <= 0:
        return 0.0
    db = load_db()
    ready_at = db["bank_cooldowns"].get(str(user_id), {}).get(action, 0)
    remaining = ready_at - datetime.now(timezone.utc).timestamp()
    return max(0.0, remaining)


def set_cooldown(user_id: int, action: str) -> None:
    duration = BANK_COOLDOWNS.get(action, 0)
    if duration <= 0:
        return
    db = load_db()
    uid = str(user_id)
    db["bank_cooldowns"].setdefault(uid, {})[action] = datetime.now(timezone.utc).timestamp() + duration
    save_db(db)


def clear_cooldowns(user_id: int) -> None:
    """يشيل كل الكولداونات الحالية لعضو (تُستخدم بأمر تسريع)."""
    db = load_db()
    db["bank_cooldowns"][str(user_id)] = {}
    save_db(db)


def format_bank_duration(seconds: float) -> str:
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours} ساعة {minutes} دقيقة"
    if minutes:
        return f"{minutes} دقائق {secs} ثانية"
    return f"{secs} ثانية"


def parse_amount_arg(arg: str | None, balance: int) -> int | None:
    """يحوّل نص زي 'نص'/'كامل'/'ربع'/رقم إلى مبلغ فعلي حسب رصيد اللاعب."""
    if not arg:
        return None
    arg = arg.strip()
    if arg in ("كامل", "الكل", "كل"):
        return balance
    if arg in ("نص", "نصف"):
        return balance // 2
    if arg in ("ربع",):
        return balance // 4
    digits = re.sub(r"[^\d]", "", arg)
    if digits.isdigit() and digits:
        return int(digits)
    return None


def push_bank_history(user_id: int, game: str, balance_after: int) -> list:
    db = load_db()
    uid = str(user_id)
    history = db["bank_history"].setdefault(uid, {}).setdefault(game, [])
    history.append(balance_after)
    del history[:-8]  # نحتفظ بآخر 8 نتائج بس (نفس عدد النقاط بالشارت المرجعي)
    save_db(db)
    return history


def make_growth_chart(history: list, won: bool, avatar_bytes: bytes | None = None, delta_label: str | None = None) -> discord.File:
    """يرسم شارت بسيط لآخر نتائج استثمار/تداول العضو، بنفس روح الشارت المرجعي (منطقة مملوءة + خط + أفتار العضو + رقم عائم)."""
    width, height = 700, 320
    line_color = (87, 242, 135) if won else (237, 66, 69)
    fill_color = (*line_color, 60)

    base = Image.new("RGBA", (width, height), (47, 49, 54, 255))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    values = history if len(history) >= 2 else [0] + history
    min_v, max_v = min(values), max(values)
    span = max(1, max_v - min_v)
    pad_x, pad_y = 40, 30
    step_x = (width - 2 * pad_x) / max(1, len(values) - 1)

    points = []
    for i, v in enumerate(values):
        x = pad_x + i * step_x
        y = height - pad_y - ((v - min_v) / span) * (height - 2 * pad_y)
        points.append((x, y))

    polygon = points + [(points[-1][0], height - pad_y), (points[0][0], height - pad_y)]
    draw.polygon(polygon, fill=fill_color)
    draw.line(points, fill=line_color, width=4, joint="curve")
    for x, y in points:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=line_color)

    # فقاعة أفتار العضو على آخر نقطة + رقم عائم يمينها (بنفس روح الشارت المرجعي)
    last_x, last_y = points[-1]
    if avatar_bytes:
        try:
            avatar_size = 56
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
            avatar_img.putalpha(mask)
            overlay.paste(avatar_img, (int(last_x - avatar_size / 2), int(last_y - avatar_size / 2)), avatar_img)
            draw.ellipse(
                (last_x - avatar_size / 2, last_y - avatar_size / 2, last_x + avatar_size / 2, last_y + avatar_size / 2),
                outline=line_color, width=3,
            )
        except Exception:
            pass

    if delta_label:
        font = _load_bank_font(30)
        badge_x = last_x + 40
        badge_y = last_y - 18
        bbox = draw.textbbox((0, 0), delta_label, font=font)
        tw = bbox[2] - bbox[0]
        if badge_x + tw > width - 10:
            badge_x = width - 10 - tw
        draw.text((badge_x, badge_y), delta_label, font=font, fill=line_color)

    final_image = Image.alpha_composite(base, overlay).convert("RGB")
    buffer = io.BytesIO()
    final_image.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="chart.png")


# =====================================================================
#                  📈  نظام اللفلات (XP والمستويات)
# =====================================================================
def xp_needed_for_level(level: int) -> int:
    """معادلة حساب الـ XP المطلوب للوصول لمستوى معين."""
    return 5 * (level ** 2) + 50 * level + 100


# تتبع آخر وقت حصل فيه كل عضو على XP (بالذاكرة فقط - يكفي لمنع السبام، ما يحتاج حفظ دائم)
_last_xp_time: dict[int, float] = {}


async def add_message_xp(member: discord.Member, channel: discord.abc.Messageable):
    """يضيف XP للعضو عند إرسال رسالة (مع مهلة بين كل XP وثانية)، ويعلن لو صعد مستوى."""
    now = asyncio.get_event_loop().time()
    last_time = _last_xp_time.get(member.id, 0)
    if now - last_time < XP_COOLDOWN_SECONDS:
        return
    _last_xp_time[member.id] = now

    db = load_db()
    uid = str(member.id)
    user_data = db["levels"].get(uid, {"xp": 0, "level": 0})

    user_data["xp"] += random.randint(XP_MIN_PER_MESSAGE, XP_MAX_PER_MESSAGE)

    leveled_up = False
    while user_data["xp"] >= xp_needed_for_level(user_data["level"] + 1):
        user_data["xp"] -= xp_needed_for_level(user_data["level"] + 1)
        user_data["level"] += 1
        leveled_up = True

    db["levels"][uid] = user_data
    save_db(db)

    if leveled_up:
        target_channel = channel
        if LEVEL_UP_CHANNEL_ID:
            level_channel = member.guild.get_channel(LEVEL_UP_CHANNEL_ID)
            if level_channel:
                target_channel = level_channel
        try:
            await target_channel.send(
                f"🎉 مبروك {member.mention}! وصلت للمستوى **{user_data['level']}** 🆙"
            )
        except Exception:
            pass


# =====================================================================
#           🖼️  توليد بطاقة الترحيب (قالب + صورة العضو + اسمه)
# =====================================================================
def _generate_welcome_card_sync(template_path: str, avatar_bytes: bytes, display_name: str, position: dict) -> io.BytesIO:
    """يشتغل بخيط منفصل (CPU-bound) - يركب صورة العضو واسمه فوق قالب الترحيب الجاهز."""
    avatar_size = position["avatar_size"]
    base = Image.open(template_path).convert("RGBA")

    # --- قص صورة العضو دائريًا وتصغيرها ---
    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar_img = avatar_img.resize((avatar_size, avatar_size))

    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar_img.putalpha(mask)

    paste_x = position["avatar_x"] - avatar_size // 2
    paste_y = position["avatar_y"] - avatar_size // 2
    base.paste(avatar_img, (paste_x, paste_y), avatar_img)

    # --- كتابة اسم العضو ---
    draw = ImageDraw.Draw(base)
    text_size = position["text_size"]
    font = None
    if WELCOME_FONT_PATH and os.path.exists(WELCOME_FONT_PATH):
        try:
            font = ImageFont.truetype(WELCOME_FONT_PATH, text_size)
        except Exception:
            font = None
    if font is None:
        try:
            font = ImageFont.load_default(size=text_size)
        except Exception:
            font = ImageFont.load_default()

    draw.text((position["text_x"], position["text_y"]), display_name, font=font, fill=position["text_color"])

    buffer = io.BytesIO()
    base.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


async def generate_welcome_card(template_path: str, member: discord.Member) -> discord.File:
    """يجلب صورة العضو ويولّد بطاقة الترحيب النهائية، ويرجعها كملف جاهز للإرسال."""
    db = load_db()
    position = {**DEFAULT_WELCOME_POSITION, **db.get("settings", {}).get("welcome_position", {})}
    avatar_bytes = await member.display_avatar.replace(size=256, format="png").read()
    loop = asyncio.get_event_loop()
    buffer = await loop.run_in_executor(
        None, _generate_welcome_card_sync, template_path, avatar_bytes, member.display_name, position
    )
    return discord.File(buffer, filename="welcome_card.png")


# =====================================================================
#                    🎫  إعدادات أنواع التذاكر
# =====================================================================
TICKET_TYPES = {
    "general": {
        "label": "استفسار",
        "emoji": "💬",
        "description": "لأي استفسار عام يخص السيرفر",
    },
    "complaint": {
        "label": "شكوى",
        "emoji": "🚨",
        "description": "تقديم شكوى رسمية",
    },
    "help": {
        "label": "مساعدة",
        "emoji": "🆘",
        "description": "طلب مساعدة عامة",
    },
}


# =====================================================================
#         ✏️  سجل الرسائل القابلة للتعديل من ديسكورد (/edit_message)
#   أي رسالة أو نص هنا تقدر تعدله من ديسكورد مباشرة بدون لمس الكود.
#   لإضافة رسالة جديدة قابلة للتعديل مستقبلاً: زد عنصر جديد بهذا القاموس
#   وحط دالة get_custom_message("المفتاح", "الحقل") مكان النص الثابت بالكود.
# =====================================================================
MESSAGE_REGISTRY = {
    "ticket_panel": {
        "label": "🎫 لوحة التذاكر",
        "fields": {
            "title": {"label": "العنوان", "style": "short", "default": "🎫 3FH PARTY ROYAL"},
            "description": {
                "label": "الوصف (نص المقدمة فقط - أنواع التذاكر تُضاف تلقائياً بالأسفل)",
                "style": "long",
                "default": (
                    "مرحباً بك في نظام الدعم الخاص بنا!\n\n"
                    "لفتح تذكرة جديدة، الرجاء اختيار نوع طلبك من القائمة أدناه.\n"
                    "سيقوم فريق الإدارة بالرد عليك في أقرب وقت ممكن."
                ),
            },
            "footer": {"label": "التذييل (أسفل الرسالة)", "style": "short", "default": "اختر نوع التذكرة من القائمة أسفل الرسالة"},
        },
    },
    "suggestion_panel": {
        "label": "💡 لوحة الاقتراحات",
        "fields": {
            "title": {"label": "العنوان", "style": "short", "default": "💡 3FH PARTY ROYAL - صندوق الاقتراحات"},
            "description": {
                "label": "الوصف",
                "style": "long",
                "default": (
                    "عندك فكرة تطوّر فيها السيرفر؟ شاركنا إياها!\n\n"
                    "اضغط الزر بالأسفل وشارك اقتراحك، وراح يوصل مباشرة لهذا الروم "
                    "ليصوّت عليه بقية الأعضاء 👍👎"
                ),
            },
            "footer": {"label": "التذييل (أسفل الرسالة)", "style": "short", "default": "اضغط (اقتراح جديد) بالأسفل لإرسال اقتراحك"},
        },
    },
    "dm_broadcast": {
        "label": "📩 رسالة الخاص الجماعية",
        "fields": {
            "text": {
                "label": "نص الرسالة (تُرسل لكل أعضاء السيرفر بالخاص)",
                "style": "long",
                "default": "مرحباً بك 👋\n\nهذي رسالة من إدارة 3FH PARTY ROYAL.",
            },
            "invite_url": {
                "label": "رابط دعوة مخصص (اختياري - اتركه فاضي عشان يتولد تلقائي)",
                "style": "short",
                "default": "",
                "required": False,
            },
        },
    },
}


def get_custom_message(key: str, field: str) -> str:
    """يرجع النص الحالي لحقل رسالة معينة: المعدَّل من ديسكورد لو موجود، وإلا القيمة الافتراضية بالكود."""
    db = load_db()
    saved = db.get("settings", {}).get("custom_messages", {}).get(key, {})
    if field in saved and saved[field].strip():
        return saved[field]
    return MESSAGE_REGISTRY[key]["fields"][field]["default"]


def resolve_ticket_banner():
    """يحدد مصدر بنر التذاكر: بنر مرفوع بالأمر له الأولوية، ثم رابط .env.
    يرجع (image_url_for_embed, discord.File أو None)."""
    db = load_db()
    uploaded_path = db.get("settings", {}).get("ticket_banner_path")
    if uploaded_path and os.path.exists(uploaded_path):
        filename = os.path.basename(uploaded_path)
        return f"attachment://{filename}", discord.File(uploaded_path, filename=filename)
    if TICKET_BANNER_URL:
        return TICKET_BANNER_URL, None
    return None, None


def resolve_suggestion_banner():
    """يحدد مصدر صورة الاقتراحات المرفوعة بالأمر /set_suggestion_banner.
    يرجع (image_url_for_embed, discord.File أو None)."""
    db = load_db()
    uploaded_path = db.get("settings", {}).get("suggestion_banner_path")
    if uploaded_path and os.path.exists(uploaded_path):
        filename = os.path.basename(uploaded_path)
        return f"attachment://{filename}", discord.File(uploaded_path, filename=filename)
    return None, None


def is_owner_or_senior_admin():
    """صلاحية مخصصة: يمرّ منها بس صاحب السيرفر (Owner) أو صاحب رتبة الإدارة العليا (OWNER_ROLE_ID بالـ .env)."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True
        if OWNER_ROLE_ID and any(r.id == OWNER_ROLE_ID for r in getattr(interaction.user, "roles", [])):
            return True
        raise app_commands.MissingPermissions(["administrator"])
    return app_commands.check(predicate)


def build_ticket_embed(ticket_number: str, ticket_type_key: str, opener: discord.Member,
                        status: str = "غير مستلمة", claimed_by: str | None = None,
                        banner_url: str | None = None) -> discord.Embed:
    """بناء إمبيد معلومات التذكرة (يُستخدم عند الفتح وعند التحديث)."""
    t = TICKET_TYPES[ticket_type_key]
    embed = discord.Embed(
        title=f"{t['emoji']} تذكرة #{ticket_number} - {t['label']}",
        description=(
            "مرحبًا بك في تذكرة إدارة **3FH PARTY ROYAL**! 👋\n\n"
            "يسعدنا مساعدتك، يرجى توضيح سبب فتح التذكرة بشكل واضح ومختصر، "
            "مع إرفاق أي صور أو مقاطع أو أدلة إن وجدت.\n\n"
            "**يرجى تضمين المعلومات التالية:**\n"
            "📌 اسمك داخل اللعبة\n"
            "📎 سبب فتح التذكرة\n"
            "📎 أي أدلة أو معلومات إضافية تساعد الإدارة على مراجعة طلبك\n\n"
            "**⚠️ يرجى الالتزام بالتالي:**\n"
            "• عدم عمل منشن للإدارة أو إرسال رسائل متكررة\n"
            "• عدم فتح أكثر من تذكرة لنفس الموضوع\n"
            "• التحلي بالاحترام أثناء التواصل\n"
            "• استخدام التذكرة للغرض المخصص لها فقط\n\n"
            "⏳ سيتم مراجعة طلبك والرد عليك من قبل أحد أفراد الإدارة في أقرب وقت ممكن.\n\n"
            "شكرًا لتعاونك، ونتمنى لك تجربة ممتعة في **3FH PARTY ROYAL** 💙"
        ),
        color=MAIN_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    if banner_url:
        embed.set_image(url=banner_url)

    embed.add_field(name="👤 صاحب التذكرة", value=opener.mention, inline=True)
    embed.add_field(name="📌 النوع", value=t["label"], inline=True)
    embed.add_field(name="📊 الحالة", value=status, inline=True)
    embed.add_field(
        name="🕐 وقت الفتح",
        value=discord.utils.format_dt(datetime.now(timezone.utc), style="F"),
        inline=False,
    )
    if claimed_by:
        embed.add_field(name="🧑‍💼 تم الاستلام بواسطة", value=claimed_by, inline=False)

    # نخزن رقم التذكرة داخل الفوتر حتى نتمكن من قراءته لاحقاً (بعد إعادة التشغيل مثلاً)
    embed.set_footer(text=f"ticket:{ticket_number}")
    return embed


# =====================================================================
#                  📜  توليد نسخة (Transcript) للتذكرة
# =====================================================================
async def generate_transcript(channel: discord.TextChannel) -> str:
    """قراءة جميع رسائل التذكرة وحفظها في ملف نصي، وإرجاع مسار الملف."""
    lines = []
    async for msg in channel.history(limit=None, oldest_first=True):
        time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        content = msg.content or "[بدون نص]"
        if msg.embeds:
            content += " [يحتوي على Embed]"
        if msg.attachments:
            content += " [مرفقات: " + ", ".join(a.url for a in msg.attachments) + "]"
        lines.append(f"[{time_str}] {msg.author}: {content}")

    path = os.path.join(TRANSCRIPTS_DIR, f"{channel.name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) if lines else "لا توجد رسائل في هذه التذكرة.")
    return path


# =====================================================================
#              🔒  إغلاق التذكرة (Transcript + تقييم + حذف)
# =====================================================================
async def close_ticket(channel: discord.TextChannel, closer: discord.Member, ticket: dict):
    db = load_db()
    channel_id = str(channel.id)

    # 1) إنشاء الـ Transcript
    transcript_path = await generate_transcript(channel)

    # 2) تحديث حالة التذكرة في قاعدة البيانات
    ticket["status"] = "مغلقة"
    ticket["closed_by"] = closer.id
    db["tickets"][channel_id] = ticket
    opener_id_str = str(ticket["opener_id"])
    if db["open_tickets"].get(opener_id_str) == channel.id:
        del db["open_tickets"][opener_id_str]
    save_db(db)

    # 3) إرسال الـ Transcript + سجل الإغلاق إلى روم اللوقز
    log_channel = channel.guild.get_channel(TICKET_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title=f"🔒 تم إغلاق التذكرة #{ticket['number']}",
            color=DANGER_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="👤 صاحب التذكرة", value=f"<@{ticket['opener_id']}>", inline=True)
        embed.add_field(name="🔒 أغلقها", value=closer.mention, inline=True)
        embed.add_field(name="📌 النوع", value=TICKET_TYPES[ticket["type"]]["label"], inline=True)
        try:
            await log_channel.send(embed=embed, file=discord.File(transcript_path))
        except Exception:
            await log_channel.send(embed=embed)

    # 4) إرسال طلب تقييم الخدمة عبر الخاص لصاحب التذكرة
    opener = channel.guild.get_member(int(ticket["opener_id"]))
    if opener:
        try:
            rate_embed = discord.Embed(
                title="⭐ قيّم تجربتك معنا",
                description=f"كيف كانت جودة الخدمة في التذكرة #{ticket['number']}؟\nاختر عدد النجوم من 1 إلى 5.",
                color=MAIN_COLOR,
            )
            rate_embed.set_footer(text=f"ticket:{ticket['number']}")
            await opener.send(embed=rate_embed, view=RatingView())
        except Exception:
            pass  # قد يكون العضو مغلق الخاص

    # 5) رسالة إغلاق وحذف القناة
    await channel.send("✅ تم إغلاق التذكرة، سيتم حذف القناة خلال 5 ثوانٍ...")
    await asyncio.sleep(5)
    try:
        await channel.delete(reason="إغلاق التذكرة")
    except Exception:
        pass


# =====================================================================
#                  ✅❌  فيو تأكيد إغلاق التذكرة
# =====================================================================
class ConfirmCloseView(discord.ui.View):
    """فيو مؤقت (غير دائم) لتأكيد إغلاق التذكرة - يظهر لمدة دقيقتين."""

    def __init__(self, ticket: dict):
        super().__init__(timeout=120)
        self.ticket = ticket
        self.message: discord.InteractionMessage | None = None

    async def on_timeout(self):
        # نعطل الأزرار ونوضح للمستخدم إن المهلة انتهت بدل ما تختفي الرسالة بصمت
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content="⌛ انتهت مهلة التأكيد. اضغط زر (إغلاق التذكرة) 🔒 مرة ثانية لو لسا تبي تغلقها.",
                    embed=None, view=self,
                )
            except Exception:
                pass

    @discord.ui.button(label="نعم، إغلاق", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔒 جاري إغلاق التذكرة...", embed=None, view=None)
        try:
            await close_ticket(interaction.channel, interaction.user, self.ticket)
        except Exception as e:
            import traceback
            print("========== خطأ أثناء إغلاق التذكرة ==========")
            traceback.print_exc()
            print("===============================================")
            try:
                await interaction.channel.send(f"⚠️ صار خطأ أثناء إغلاق التذكرة: {e}\nتقدر تحاول تضغط زر الإغلاق مرة ثانية.")
            except Exception:
                pass

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="تم إلغاء عملية الإغلاق.", embed=None, view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print("========== خطأ داخل فيو تأكيد الإغلاق ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("=================================================")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ حدث خطأ: {error}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ حدث خطأ: {error}", ephemeral=True)
        except Exception:
            pass


# =====================================================================
#              ✋🔒  أزرار التحكم داخل التذكرة (دائمة)
# =====================================================================
class TicketControlView(discord.ui.View):
    """فيو دائم (Persistent) يحتوي على زري Claim و Close - يعمل حتى بعد إعادة تشغيل البوت."""

    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print("========== خطأ داخل أزرار التذكرة (استلام/إغلاق) ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("=============================================================")
        msg = f"❌ حدث خطأ غير متوقع: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass

    @discord.ui.button(label="استلام التذكرة", emoji="✋",
                        style=discord.ButtonStyle.primary, custom_id="ticket_claim_btn")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = load_db()
        channel_id = str(interaction.channel.id)
        ticket = db["tickets"].get(channel_id)
        if ticket is None:
            return await interaction.response.send_message("⚠️ لم يتم العثور على بيانات هذه التذكرة.", ephemeral=True)

        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ هذا الزر مخصص لفريق الإدارة فقط.", ephemeral=True)

        if ticket.get("claimed_by"):
            return await interaction.response.send_message(
                f"⚠️ تم استلام هذه التذكرة مسبقاً بواسطة <@{ticket['claimed_by']}>.", ephemeral=True
            )

        ticket["claimed_by"] = interaction.user.id
        ticket["status"] = "تم الاستلام"
        db["tickets"][channel_id] = ticket
        save_db(db)

        opener = interaction.guild.get_member(int(ticket["opener_id"]))
        banner_url, _ = resolve_ticket_banner()
        new_embed = build_ticket_embed(
            ticket["number"], ticket["type"], opener,
            status="✅ تم الاستلام", claimed_by=interaction.user.mention,
            banner_url=banner_url,
        )

        button.disabled = True
        button.label = "تم الاستلام"
        await interaction.response.edit_message(embed=new_embed, view=self)

        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"✋ تم استلام التذكرة `#{ticket['number']}` بواسطة {interaction.user.mention}")

    @discord.ui.button(label="إغلاق التذكرة", emoji="🔒",
                        style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = load_db()
        channel_id = str(interaction.channel.id)
        ticket = db["tickets"].get(channel_id)
        if ticket is None:
            return await interaction.response.send_message("⚠️ لم يتم العثور على بيانات هذه التذكرة.", ephemeral=True)

        is_opener = interaction.user.id == int(ticket["opener_id"])
        if not (is_staff(interaction.user) or is_opener):
            return await interaction.response.send_message("❌ لا تملك صلاحية إغلاق هذه التذكرة.", ephemeral=True)

        confirm_embed = discord.Embed(
            title="⚠️ تأكيد الإغلاق",
            description="هل أنت متأكد من إغلاق هذه التذكرة؟ لا يمكن التراجع عن هذا الإجراء.",
            color=DANGER_COLOR,
        )
        confirm_view = ConfirmCloseView(ticket)
        await interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
        confirm_view.message = await interaction.original_response()


# =====================================================================
#                  ⭐  فيو تقييم الخدمة (دائم)
# =====================================================================
class RatingView(discord.ui.View):
    """فيو دائم لتقييم الخدمة من 1 إلى 5 نجوم - يُرسل عبر الخاص بعد إغلاق التذكرة."""

    def __init__(self):
        super().__init__(timeout=None)

    async def _rate(self, interaction: discord.Interaction, stars: int):
        footer_text = interaction.message.embeds[0].footer.text if interaction.message.embeds else ""
        ticket_number = footer_text.replace("ticket:", "") if footer_text and footer_text.startswith("ticket:") else "unknown"

        db = load_db()
        db["ratings"][ticket_number] = {"stars": stars, "user_id": interaction.user.id}
        save_db(db)

        for child in self.children:
            child.disabled = True

        stars_display = "⭐" * stars + "☆" * (5 - stars)
        thanks_embed = discord.Embed(
            title="✅ شكراً لتقييمك",
            description=f"تقييمك للتذكرة #{ticket_number}: {stars_display}",
            color=SUCCESS_COLOR,
        )
        await interaction.response.edit_message(embed=thanks_embed, view=self)

    @discord.ui.button(emoji="1️⃣", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def rate1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._rate(interaction, 1)

    @discord.ui.button(emoji="2️⃣", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def rate2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._rate(interaction, 2)

    @discord.ui.button(emoji="3️⃣", style=discord.ButtonStyle.secondary, custom_id="rate_3")
    async def rate3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._rate(interaction, 3)

    @discord.ui.button(emoji="4️⃣", style=discord.ButtonStyle.secondary, custom_id="rate_4")
    async def rate4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._rate(interaction, 4)

    @discord.ui.button(emoji="5️⃣", style=discord.ButtonStyle.secondary, custom_id="rate_5")
    async def rate5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._rate(interaction, 5)


# =====================================================================
#            📩  إنشاء تذكرة جديدة عند الاختيار من القائمة
# =====================================================================
async def create_ticket(interaction: discord.Interaction, ticket_type_key: str, extra_info: dict | None = None):
    guild = interaction.guild
    user = interaction.user
    db = load_db()

    # منع فتح أكثر من تذكرة بنفس الوقت لنفس العضو
    existing_channel_id = db["open_tickets"].get(str(user.id))
    if existing_channel_id and guild.get_channel(existing_channel_id):
        return await interaction.response.send_message(
            f"⚠️ لديك تذكرة مفتوحة بالفعل: <#{existing_channel_id}>", ephemeral=True
        )

    await interaction.response.send_message("⏳ جاري إنشاء تذكرتك...", ephemeral=True)

    category = guild.get_channel(TICKET_CATEGORY_ID)
    if category is None:
        return await interaction.edit_original_response(
            content="❌ لم يتم العثور على قسم (Category) التذاكر. تأكد أن `TICKET_CATEGORY_ID` بملف `.env` صحيح ويشير لقسم موجود بالسيرفر."
        )
    if not isinstance(category, discord.CategoryChannel):
        return await interaction.edit_original_response(
            content="❌ الآيدي الموجود بـ `TICKET_CATEGORY_ID` لا يشير إلى قسم (Category) بل لروم عادي. غيّره لآيدي قسم صحيح."
        )

    # ترقيم تلقائي للتذكرة (يُحفظ بشكل دائم في قاعدة البيانات)
    db["ticket_counter"] += 1
    ticket_number = str(db["ticket_counter"])

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, attach_files=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        ),
    }
    # إعطاء صلاحية رؤية التذكرة لكل رتب الإدارة المحددة
    staff_mentions = []
    for role_id in STAFF_ROLE_IDS:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
            staff_mentions.append(role.mention)

    try:
        channel = await guild.create_text_channel(
            name=f"🎫・{ticket_number}",
            category=category,
            overwrites=overwrites,
            reason=f"تذكرة جديدة بواسطة {user}",
        )
    except discord.Forbidden:
        db["ticket_counter"] -= 1  # نرجع الرقم لأن الإنشاء فشل
        save_db(db)
        return await interaction.edit_original_response(
            content="❌ البوت لا يملك صلاحية `Manage Channels` لإنشاء رومات التذاكر. أعط البوت هذي الصلاحية من إعدادات السيرفر أو الرتبة."
        )
    except Exception as e:
        db["ticket_counter"] -= 1
        save_db(db)
        print(f"❌ خطأ أثناء إنشاء التذكرة: {e}")
        return await interaction.edit_original_response(content=f"❌ حدث خطأ أثناء إنشاء التذكرة: {e}")

    try:
        ticket_data = {
            "number": ticket_number,
            "type": ticket_type_key,
            "opener_id": user.id,
            "status": "غير مستلمة",
            "claimed_by": None,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        db["tickets"][str(channel.id)] = ticket_data
        db["open_tickets"][str(user.id)] = channel.id
        save_db(db)

        banner_url, banner_file = resolve_ticket_banner()
        embed = build_ticket_embed(ticket_number, ticket_type_key, user, banner_url=banner_url)
        if extra_info:
            for field_name, field_value in extra_info.items():
                embed.add_field(name=f"📌 {field_name}", value=field_value, inline=False)
        mention_line = f"{user.mention} {' '.join(staff_mentions)}"
        if banner_file:
            await channel.send(content=mention_line, embed=embed, view=TicketControlView(), file=banner_file)
        else:
            await channel.send(content=mention_line, embed=embed, view=TicketControlView())

        # تنبيه لصاحب التذكرة إذا محد من الإدارة متواجد أونلاين حالياً
        if STAFF_ROLE_IDS and not any_staff_available(guild):
            availability_embed = discord.Embed(
                title="⏰ الإدارة غير متاحة حالياً",
                description=(
                    "فريق الدعم مو متواجد أونلاين هالوقت، بس تم تسجيل تذكرتك وبيوصلها إشعار.\n"
                    "الرد ممكن ياخذ وقت أطول من المعتاد، شكراً لصبرك 🙏"
                ),
                color=MAIN_COLOR,
            )
            await channel.send(embed=availability_embed)

        await interaction.edit_original_response(content=f"✅ تم إنشاء تذكرتك بنجاح: {channel.mention}")
    except Exception as e:
        import traceback
        print("========== خطأ بعد إنشاء روم التذكرة ==========")
        traceback.print_exc()
        print("=================================================")
        try:
            await interaction.edit_original_response(
                content=f"⚠️ تم إنشاء الروم لكن صار خطأ أثناء إعداد التذكرة: {e}\nتقدر تكمل يدويًا بالروم: {channel.mention}"
            )
        except Exception:
            pass
        return

    log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
    if log_channel:
        t = TICKET_TYPES[ticket_type_key]
        await log_channel.send(
            f"📩 تذكرة جديدة `#{ticket_number}` ({t['label']}) بواسطة {user.mention} - {channel.mention}"
        )


# =====================================================================
#                  🎫  لوحة التذاكر (قائمة الاختيار - دائمة)
# =====================================================================
class TicketInfoModal(discord.ui.Modal, title="📋 فتح تذكرة جديدة"):
    """نافذة تجمع معلومات الطلب من العضو قبل إنشاء روم التذكرة."""

    def __init__(self, ticket_type_key: str):
        super().__init__()
        self.ticket_type_key = ticket_type_key

    game_name = discord.ui.TextInput(
        label="اسمك داخل اللعبة",
        placeholder="اكتب اسمك داخل اللعبة...",
        max_length=100,
        required=True,
    )
    reason = discord.ui.TextInput(
        label="سبب فتح التذكرة",
        style=discord.TextStyle.paragraph,
        placeholder="اشرح طلبك أو مشكلتك بالتفصيل...",
        max_length=1000,
        required=True,
    )
    evidence = discord.ui.TextInput(
        label="أي أدلة أو معلومات إضافية (اختياري)",
        style=discord.TextStyle.paragraph,
        placeholder="روابط صور/فيديو إن وجدت (تقدر ترفع الصور داخل التذكرة بعد فتحها)",
        max_length=500,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(
            interaction, self.ticket_type_key,
            extra_info={
                "اسم اللعبة": str(self.game_name),
                "السبب": str(self.reason),
                "أدلة إضافية": str(self.evidence) if self.evidence.value else "لا يوجد",
            },
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        import traceback
        print("========== خطأ داخل نافذة فتح التذكرة ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("=================================================")
        msg = f"❌ حدث خطأ غير متوقع: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=v["label"], value=k, emoji=v["emoji"], description=v["description"])
            for k, v in TICKET_TYPES.items()
        ]
        super().__init__(
            placeholder="Make a Selection | اختر نوع التذكرة",
            options=options,
            custom_id="ticket_panel_select",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        db = load_db()
        allowed_role_ids = db.get("settings", {}).get("ticket_allowed_roles", [])
        if allowed_role_ids:
            member_role_ids = {r.id for r in interaction.user.roles}
            has_access = bool(member_role_ids & set(allowed_role_ids)) or interaction.user.guild_permissions.administrator
            if not has_access:
                return await interaction.response.send_message(
                    "❌ ما تملك الصلاحية الكافية لفتح تذكرة.", ephemeral=True
                )
        await interaction.response.send_modal(TicketInfoModal(self.values[0]))


class TicketPanelView(discord.ui.View):
    """فيو دائم للوحة التذاكر - يحتوي فقط على قائمة الاختيار."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print("========== خطأ داخل لوحة التذاكر ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("============================================")
        msg = f"❌ حدث خطأ غير متوقع أثناء فتح التذكرة: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


# =====================================================================
#              👍👎  نظام التصويت على الاقتراحات (دائم)
# =====================================================================
class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _vote(self, interaction: discord.Interaction, vote_type: str):
        db = load_db()
        msg_id = str(interaction.message.id)
        record = db["suggestions"].setdefault(msg_id, {"up": [], "down": []})
        user_id = interaction.user.id
        other = "down" if vote_type == "up" else "up"

        if user_id in record[vote_type]:
            msg = "⚠️ لقد قمت بالتصويت بهذا الخيار مسبقاً."
            if interaction.response.is_done():
                return await interaction.followup.send(msg, ephemeral=True)
            return await interaction.response.send_message(msg, ephemeral=True)

        if user_id in record[other]:
            record[other].remove(user_id)
        record[vote_type].append(user_id)
        db["suggestions"][msg_id] = record
        save_db(db)

        new_content = re.sub(
            r"👍 \d+\s+👎 \d+",
            f"👍 {len(record['up'])}    👎 {len(record['down'])}",
            interaction.message.content,
        )

        try:
            if interaction.response.is_done():
                # الإنتراكشن انأجاب عليه مسبقاً (مثلاً ضغط سريع متكرر) - نعدّل الرسالة مباشرة بدل الرد عليه
                await interaction.message.edit(content=new_content)
            else:
                await interaction.response.edit_message(content=new_content)
        except discord.HTTPException as e:
            print(f"⚠️ خطأ أثناء تحديث تصويت الاقتراح: {e}")

    @discord.ui.button(emoji="👍", style=discord.ButtonStyle.success, custom_id="suggest_up")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._vote(interaction, "up")

    @discord.ui.button(emoji="👎", style=discord.ButtonStyle.danger, custom_id="suggest_down")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._vote(interaction, "down")


# =====================================================================
#           💡  نافذة كتابة الاقتراح (Modal) ولوحة الإرسال
# =====================================================================
class SuggestionModal(discord.ui.Modal, title="💡 إضافة اقتراح جديد"):
    """نافذة تظهر للعضو عند الضغط على زر (اقتراح جديد) ليكتب اقتراحه."""

    suggestion_text = discord.ui.TextInput(
        label="اكتب اقتراحك",
        style=discord.TextStyle.paragraph,
        placeholder="اكتب اقتراحك هنا بالتفصيل...",
        max_length=1000,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(SUGGESTIONS_CHANNEL_ID) or interaction.channel

        content_text = (
            f"💡 **اقتراح جديد من {interaction.user.mention}**\n\n"
            f"{self.suggestion_text}\n\n"
            "👍 0    👎 0"
        )

        _, banner_file = resolve_suggestion_banner()

        try:
            if banner_file:
                msg = await channel.send(content=content_text, view=SuggestionView(), file=banner_file)
            else:
                msg = await channel.send(content=content_text, view=SuggestionView())
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ البوت لا يملك صلاحية الإرسال بروم الاقتراحات. بلّغ الإدارة عن هذا الخطأ.", ephemeral=True
            )

        db = load_db()
        db["suggestions"][str(msg.id)] = {"up": [], "down": []}
        save_db(db)

        await interaction.response.send_message(f"✅ تم إرسال اقتراحك بنجاح في {channel.mention}", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        import traceback
        print("========== خطأ داخل نافذة الاقتراح ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("==============================================")
        msg = f"❌ حدث خطأ غير متوقع: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


class SuggestionPanelView(discord.ui.View):
    """فيو دائم للوحة الاقتراحات - يحتوي على زر (اقتراح جديد) يفتح نافذة الكتابة."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="اقتراح جديد", emoji="➕",
                        style=discord.ButtonStyle.primary, custom_id="suggestion_panel_btn")
    async def new_suggestion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print("========== خطأ داخل لوحة الاقتراحات ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("===============================================")
        msg = f"❌ حدث خطأ غير متوقع: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass



# =====================================================================
#              🎛️  لوحة التحكم (أزرار سريعة للإدارة)
# =====================================================================
class PollView(discord.ui.View):
    """فيو استطلاع رأي بأزرار - كل عضو يصوت مرة وحدة (يقدر يغيّر صوته)."""

    def __init__(self, options: list[str]):
        super().__init__(timeout=None)
        self.options = options
        self.votes: dict[int, int] = {}  # {user_id: index_الخيار}
        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=option[:80], style=discord.ButtonStyle.primary, custom_id=f"poll_option_{i}"
            )
            button.callback = self._make_callback(i)
            self.add_item(button)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            self.votes[interaction.user.id] = index
            await interaction.response.edit_message(embed=self._build_embed(interaction.message.embeds[0]))
        return callback

    def _build_embed(self, original_embed: discord.Embed) -> discord.Embed:
        counts = [0] * len(self.options)
        for choice in self.votes.values():
            counts[choice] += 1
        total = sum(counts) or 1

        lines = []
        for i, option in enumerate(self.options):
            percent = int(counts[i] / total * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            lines.append(f"**{option}**\n{bar} {counts[i]} صوت ({percent}%)")

        embed = discord.Embed(
            title=original_embed.title,
            description="\n\n".join(lines),
            color=MAIN_COLOR,
        )
        embed.set_footer(text=f"إجمالي الأصوات: {sum(counts)}")
        return embed



HELP_CATEGORIES = {
    "tickets": {
        "label": "🎫 التذاكر",
        "emoji": "🎫",
        "commands": [
            ("/ticket_panel", "إرسال لوحة فتح التذاكر بهذا الروم"),
            ("/set_ticket_banner", "ضبط صورة بنر التذاكر"),
            ("/set_ticket_role", "تحديد الرتب المسموح لها فتح تذكرة"),
        ],
    },
    "welcome": {
        "label": "🎉 الترحيب",
        "emoji": "🎉",
        "commands": [
            ("/set_welcome_template", "رفع قالب بطاقة الترحيب"),
            ("/set_welcome_position", "تحديد مكان صورة العضو واسمه بالبطاقة"),
            ("/test_welcome", "معاينة بطاقة الترحيب بحسابك الحالي"),
        ],
    },
    "suggestions": {
        "label": "💡 الاقتراحات",
        "emoji": "💡",
        "commands": [
            ("/suggestion_panel", "إرسال لوحة إضافة اقتراح بهذا الروم"),
            ("/set_suggestion_banner", "ضبط أيقونة الاقتراحات الافتراضية"),
        ],
    },
    "voice": {
        "label": "🎙️ الصوت",
        "emoji": "🎙️",
        "commands": [
            ("/voice_join", "دخول البوت لروم صوتي معين (الأونر والإدارة العليا بس)"),
            ("/voice_leave", "خروج البوت من الروم الصوتي (الأونر والإدارة العليا بس)"),
            ("/voice_uptime", "عرض كم صار للبوت قاعد بالروم الصوتي"),
        ],
    },
    "fun": {
        "label": "🎮 الترفيه والتفاعل",
        "emoji": "🎮",
        "commands": [
            ("/poll", "إنشاء استطلاع رأي بأزرار (حتى 4 خيارات)"),
            ("/athkar", "إرسال ذِكر عشوائي"),
            ("/rank", "عرض مستواك ونقاط خبرتك الحالية"),
            ("/leaderboard", "عرض أعلى 10 أعضاء بنقاط الخبرة"),
            ("/balance", "عرض رصيدك الحالي بالبنك"),
            ("/mines", "لعبة الألغام واربح مكافأة"),
            ("/control_panel", "إرسال لوحة التحكم العامة بهذا الروم"),
        ],
    },
    "bank": {
        "label": "🏦 البنك (بروم البنك - تكتب الكلمة وتشتغل، بدون سلاش)",
        "emoji": "🏦",
        "commands": [
            ("راتب", "استلام راتبك (مرة كل 24 ساعة)"),
            ("بخشيش", "بخشيش عشوائي صغير"),
            ("حظ", "جرب حظك - ربح أو خسارة صغيرة"),
            ("روليت", "عجلة حظ فيها جوائز كاش وذهب"),
            ("نهب", "حاول تسرق أغنى عضو متاح حاليًا"),
            ("حماية", "فعّل حماية 5 ساعات من السرقة"),
            ("رهان <مبلغ/نص/كامل>", "راهن ضد البنك (فرصة 48%)"),
            ("قمار <مبلغ/نص/كامل>", "لعبة رصيد افتراضي بمضاعف عشوائي - بدون أموال حقيقية"),
            ("نرد <مبلغ/نص/كامل>", "نرد ضد البنك - الأعلى يفوز"),
            ("استثمار <مبلغ/نص/كامل>", "استثمر بمخاطرة أقل، مع شارت أداء"),
            ("تداول <مبلغ/نص/كامل>", "تداول بمخاطرة أعلى وربح أسرع"),
            ("لعبه / لون / فواكه", "ألعاب سريعة بدون كولداون"),
            ("تسريع", f"يشيل كل الكولداونات مقابل Gold x{SPEEDUP_GOLD_COST}"),
            ("شراء / بيع", "متجر الممتلكات والأسهم والذهب"),
            ("سوق", "عرض سعر السهم المتغير وحركة السوق"),
            ("ممتلكات", "عرض ممتلكاتك وإجمالي ثروتك"),
            ("وقت", "حالة جاهزية كل أوامر البنك"),
            ("اغنى", "أغنى 10 أعضاء بالسيرفر"),
        ],
    },
    "admin": {
        "label": "⚙️ إدارة عامة",
        "emoji": "⚙️",
        "commands": [
            ("/clear", "حذف رسائل بهذا الروم أو كل رومات السيرفر"),
            ("/add_auto_reply", "إضافة رد آلي مخصص"),
            ("/remove_auto_reply", "حذف رد آلي مخصص"),
            ("/list_auto_replies", "عرض كل الردود الآلية المضافة"),
            ("/edit_message dm_broadcast", "تحديد نص رسالة الخاص الجماعية"),
            ("/send_dm_all", "إرسال رسالة خاصة لكل أعضاء السيرفر (مع صورة أو فيديو اختياري)"),
            ("/save_file", "رفع ملف أو صورة وحفظه مع إرجاع مساره"),
            ("/list_files", "عرض الملفات المحفوظة ومساراتها"),
            ("/delete_file", "حذف ملف محفوظ عبر /save_file"),
        ],
    },
}


class HelpCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat["label"], value=key, emoji=cat["emoji"])
            for key, cat in HELP_CATEGORIES.items()
        ]
        super().__init__(placeholder="اختر قسم لعرض أوامره...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        category = HELP_CATEGORIES[self.values[0]]
        lines = [f"**{category['label']}**\n"]
        for cmd, desc in category["commands"]:
            lines.append(f"`{cmd}` — {desc}")
        content = "\n".join(lines)
        await interaction.response.edit_message(content=content, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpCategorySelect())


class ControlPanelView(discord.ui.View):
    """فيو دائم - لوحة تحكم تثبّتها بأي روم، وتشغّل منها أوامر البوت بضغطة زر بدل الكتابة."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="لوحة التذاكر", emoji="🎫",
                        style=discord.ButtonStyle.primary, custom_id="control_ticket_panel", row=0)
    async def send_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ هذا الزر مخصص لفريق الإدارة فقط.", ephemeral=True)
        await send_ticket_panel_message(interaction.channel)
        await interaction.response.send_message("✅ تم إرسال لوحة التذاكر بهذا الروم.", ephemeral=True)

    @discord.ui.button(label="لوحة الاقتراحات", emoji="💡",
                        style=discord.ButtonStyle.primary, custom_id="control_suggestion_panel", row=0)
    async def send_suggestion_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ هذا الزر مخصص لفريق الإدارة فقط.", ephemeral=True)
        await send_suggestion_panel_message(interaction.channel)
        await interaction.response.send_message("✅ تم إرسال لوحة الاقتراحات بهذا الروم.", ephemeral=True)

    @discord.ui.button(label="مسح 50 رسالة هنا", emoji="🗑️",
                        style=discord.ButtonStyle.danger, custom_id="control_clear_50", row=1)
    async def clear_here(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ هذا الزر مخصص للأونر/الإدارة العليا فقط.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=50)
            await interaction.followup.send(f"✅ تم حذف {len(deleted)} رسالة من هذا الروم.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ البوت لا يملك صلاحية `Manage Messages` بهذا الروم.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print("========== خطأ داخل لوحة التحكم ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("============================================")
        msg = f"❌ حدث خطأ غير متوقع: {error}"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass



# =====================================================================
#                        🚀  حدث جاهزية البوت
# =====================================================================
@tasks.loop(minutes=5)
async def bank_market_updater():
    """تحديث سعر السهم الافتراضي كل خمس دقائق حتى دون فتح لوحة السوق."""
    try:
        get_stock_market(update_if_due=True)
    except Exception as exc:
        print(f"⚠️ تعذّر تحديث سوق البنك: {exc}")


@bot.event
async def on_ready():
    if not bank_market_updater.is_running():
        bank_market_updater.start()

    # تسجيل الفيوهات الدائمة حتى تعمل الأزرار بعد إعادة تشغيل البوت
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(SuggestionView())
    bot.add_view(SuggestionPanelView())
    bot.add_view(ControlPanelView())
    bot.add_view(RatingView())

    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)

            # الترتيب الصحيح: أول ننسخ الأوامر العامة (وهي محفوظة محليًا بالذاكرة) لهذا السيرفر ونزامنها
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)

            # وبعدين بس نمسح أي نسخة عالمية (Global) قديمة من ديسكورد لمنع ظهور أوامر مكررة
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
        else:
            synced = await bot.tree.sync()
        print(f"✅ تم تسجيل {len(synced)} أمر Slash بنجاح")
    except Exception as e:
        print(f"❌ خطأ أثناء مزامنة الأوامر: {e}")

    print(f"✅ تم تسجيل الدخول باسم {bot.user} - البوت جاهز الآن")

    # --- إعادة الاتصال التلقائي بالروم الصوتي بعد أي إعادة تشغيل (مهم لـ Railway لأنه يعيد تشغيل البوت أحياناً) ---
    # لو كان البوت متصل بروم صوتي قبل إعادة التشغيل (عبر /voice_join)، يرجع له تلقائياً
    # بدل ما يضل خارج الروم لين حد يسوي /voice_join يدوياً من جديد.
    try:
        db = load_db()
        tracker = db.get("bot_voice_uptime", {"voice_channel_id": None, "connected_since": None, "total_seconds": 0})
        channel_id = tracker.get("voice_channel_id")
        if channel_id and not (bot.guilds and any(g.voice_client for g in bot.guilds)):
            channel = bot.get_channel(channel_id)
            if isinstance(channel, discord.VoiceChannel):
                try:
                    await channel.connect(reconnect=True)
                    print(f"🔁 تم إعادة الاتصال تلقائياً بالروم الصوتي «{channel.name}» بعد إعادة التشغيل")
                except Exception as e:
                    print(f"⚠️ ما قدرت أرجع للروم الصوتي تلقائياً: {e}")
            else:
                print("⚠️ الروم الصوتي المحفوظ سابقاً ما عاد موجود أو البوت ما يشوفه.")
    except Exception as e:
        print(f"⚠️ خطأ أثناء محاولة إعادة الاتصال التلقائي بالصوت: {e}")

    # --- تشخيص مؤقت: التأكد من توفر مكتبة davey لدعم الصوت (DAVE E2EE) ---
    try:
        import davey  # noqa: F401
        print(f"✅ [تشخيص] davey متوفرة ومستوردة بنجاح - إصدار: {getattr(davey, '__version__', 'غير معروف')}")
    except Exception as e:
        print(f"❌ [تشخيص] فشل استيراد davey: {type(e).__name__}: {e}")

    try:
        print(f"🔎 [تشخيص] discord.py الإصدار: {discord.__version__} | has_dave داخل discord.py: {getattr(discord.voice_client, 'has_dave', 'غير معروف')}")
    except Exception as e:
        print(f"❌ [تشخيص] تعذر فحص has_dave: {e}")

    # --- استكمال أي رسالة خاص جماعية انقطعت أثناء الإرسال (بسبب ريديبلوي/كراش) ---
    # on_ready ممكن يتكرر لو صار انقطاع مؤقت بالاتصال بديسكورد، فنتأكد ما فيه مهمة استكمال شغالة أصلاً
    global _dm_broadcast_task
    if _dm_broadcast_task is None or _dm_broadcast_task.done():
        db = load_db()
        if db.get("dm_broadcast_progress"):
            print("🔁 لقيت رسالة خاص جماعية متوقفة من قبل - جاري استكمالها تلقائياً...")
            _dm_broadcast_task = asyncio.create_task(run_dm_broadcast())


# =====================================================================
#                    🎉  نظام الترحيب بالأعضاء الجدد
# =====================================================================
@bot.event
async def on_member_join(member: discord.Member):
    if GUILD_ID and member.guild.id != GUILD_ID:
        return

    if member.bot:
        return

    # إعطاء رتبة الدخول تلقائياً
    role = member.guild.get_role(WELCOME_ROLE_ID)
    if role:
        try:
            await member.add_roles(role, reason="رتبة تلقائية عند دخول السيرفر")
        except Exception as e:
            print(f"⚠️ تعذر إعطاء الرتبة للعضو {member}: {e}")

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    db = load_db()
    template_path = db.get("settings", {}).get("welcome_template_path")

    banner_file = None
    if template_path and os.path.exists(template_path):
        try:
            banner_file = await generate_welcome_card(template_path, member)
        except Exception as e:
            print(f"❌ خطأ أثناء توليد بطاقة الترحيب: {e}")
            banner_file = None

    # نفس ستايل SKYE bot: سطر عنوان بولد+مائل، وسطر عدد الأعضاء بحجم عنوان كبير، والبطاقة تحتهم
    content_lines = [
        f"_**#Welcome To Party Royale 3FH {member.mention}**_",
        f"# {member.guild.member_count} : عدد اعضاء السيرفر",
    ]
    if TICKET_PANEL_CHANNEL_ID:
        content_lines.append(f"و أي استفسار تفضل: <#{TICKET_PANEL_CHANNEL_ID}>")
    content_text = "\n".join(content_lines)

    if banner_file:
        await channel.send(content=content_text, file=banner_file)
    else:
        await channel.send(content=content_text)


@bot.event
async def on_member_remove(member: discord.Member):
    if GUILD_ID and member.guild.id != GUILD_ID:
        return

    if member.bot:
        return

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    # رسالة نصية بس (بدون صورة) - نفس ستايل SKYE bot
    content_text = (
        "**Member Left**\n"
        f"{member.guild.member_count} : عدد اعضاء السيرفر   {member.mention}\n"
        "Party Royale 3FH"
    )
    try:
        await channel.send(content=content_text)
    except Exception as e:
        print(f"❌ خطأ أثناء إرسال رسالة مغادرة العضو: {e}")


# =====================================================================
#            🎙️  وقت تواجد البوت نفسه بروم صوتي (Bot Voice Uptime)
# =====================================================================
def format_duration(total_seconds) -> str:
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours and minutes:
        return f"{hours} ساعة و {minutes} دقيقة"
    elif hours:
        return f"{hours} ساعة"
    elif minutes:
        return f"{minutes} دقيقة"
    return "أقل من دقيقة"


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # --- تتبع وقت تواجد البوت نفسه (الكود الأصلي) ---
    if member.id == bot.user.id:
        db = load_db()
        tracker = db.get("bot_voice_uptime", {"voice_channel_id": None, "connected_since": None, "total_seconds": 0})
        now = datetime.now(timezone.utc).timestamp()

        if after.channel and not before.channel:
            # البوت دخل روم صوتي
            tracker["voice_channel_id"] = after.channel.id
            tracker["connected_since"] = now
        elif before.channel and not after.channel:
            # البوت طلع/انقطع من الروم - نضيف مدة هذي الجلسة للإجمالي
            started = tracker.get("connected_since")
            if started:
                tracker["total_seconds"] = tracker.get("total_seconds", 0) + max(0, now - started)
            tracker["connected_since"] = None

        db["bot_voice_uptime"] = tracker
        save_db(db)
        return


# =====================================================================
#                        💬  الردود الآلية
# =====================================================================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # نظام اللفلات - يشتغل بكل الرومات (خارج أي قيود روم/رتبة)
    if isinstance(message.author, discord.Member):
        await add_message_xp(message.author, message.channel)

    # نظام البنك الموسّع - أوامر نصية بدون سلاش (تشتغل بس بروم البنك لو محدد)
    if (not BANK_CHANNEL_ID) or message.channel.id == BANK_CHANNEL_ID:
        handled = await handle_bank_text_command(message)
        if handled:
            return

    # الردود الآلية تعمل فقط في روم الشات العام (لو تم تحديده)
    channel_ok = (not GENERAL_CHAT_ID) or (message.channel.id == GENERAL_CHAT_ID)

    # الردود الآلية المخصصة (مُضافة عبر /add_auto_reply) - كل رد ممكن تحدد له رتبة معينة تشتغل عليها بس
    if channel_ok:
        db = load_db()
        auto_replies = db.get("auto_replies", {})
        trigger_text = message.content.strip()
        entry = auto_replies.get(trigger_text)
        if entry is not None:
            # دعم الصيغة القديمة (نص فقط بدون رتبة) بالإضافة للصيغة الجديدة (قاموس فيه رتبة اختيارية)
            if isinstance(entry, str):
                response_text, role_id = entry, None
            else:
                response_text, role_id = entry.get("response", ""), entry.get("role_id")

            allowed = True
            if role_id:
                allowed = isinstance(message.author, discord.Member) and any(
                    r.id == role_id for r in message.author.roles
                )
            elif MEMBER_ROLE_ID and isinstance(message.author, discord.Member):
                allowed = any(r.id == MEMBER_ROLE_ID for r in message.author.roles)

            if allowed and response_text:
                await message.reply(response_text, mention_author=False)

    # نظام التصحيح الإملائي - يعمل فقط بروم مخصص (CORRECTIONS_CHANNEL_ID)
    # نظام الكلجات - العضو يمنشن صاحب الغلطة ثم يكتب "الصح=الخطأ" (بدون قيد على طول الكلمة/الجملة)
    if CORRECTIONS_CHANNEL_ID and message.mentions:
        text_without_mentions = message.content
        for m in message.mentions:
            text_without_mentions = text_without_mentions.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
        text_without_mentions = text_without_mentions.strip()

        match = re.match(r"^(.+)=(.+)$", text_without_mentions)
        if match:
            correct_word, wrong_word = match.group(1).strip(), match.group(2).strip()
            culprit = message.mentions[0]  # العضو صاحب الغلطة (اللي حطه المُبلّغ بالمنشن)
            corrections_channel = message.guild.get_channel(CORRECTIONS_CHANNEL_ID) if message.guild else None
            if corrections_channel:
                correction_line = f"✅ {correct_word} ❌ {wrong_word}"
                try:
                    webhook = await get_channel_webhook(corrections_channel)
                    await webhook.send(
                        content=correction_line,
                        username=culprit.display_name,
                        avatar_url=culprit.display_avatar.url,
                    )
                except discord.Forbidden:
                    await corrections_channel.send(f"{culprit.mention} {correction_line}")
                except Exception as e:
                    print(f"❌ خطأ أثناء إرسال التصحيح عبر الويبهوك: {e}")
                    await corrections_channel.send(f"{culprit.mention} {correction_line}")

                # نحذف الرسالة الأصلية من الروم اللي كتبها فيه العضو بعد ما انتقلت لروم الكلجات
                try:
                    await message.delete()
                except discord.Forbidden:
                    print(f"⚠️ ما قدرت أحذف رسالة الكلجة الأصلية - البوت يحتاج صلاحية Manage Messages بروم {message.channel.name}")
                except Exception as e:
                    print(f"❌ خطأ أثناء حذف رسالة الكلجة الأصلية: {e}")

            await bot.process_commands(message)
            return

    await bot.process_commands(message)


# =====================================================================
#                  🎮  لعبة البنك (Mines) - لعبة حظ بسيطة
# =====================================================================
class MinesGameView(discord.ui.View):
    """لعبة ألغام بسيطة: شبكة 3x3، مربع واحد قنبلة، الباقي آمن.
    لا يوجد رهان أو خصم - كل مربع آمن يكبر مكافأة مجانية، وفيه زر لسحبها بأي وقت.
    لو وقعت بالقنبلة تخسر المكافأة فقط (بدون أي خصم من رصيدك الأصلي)."""

    def __init__(self, player: discord.Member):
        super().__init__(timeout=120)
        self.player = player
        self.multiplier = 1.0
        self.bomb_index = random.randint(0, MINES_GRID_SIZE - 1)
        self.game_over = False
        self.safe_clicks = 0

        for i in range(MINES_GRID_SIZE):
            self.add_item(self._make_tile_button(i))

        self.cash_out_button = discord.ui.Button(
            label="💰 اسحب مكافأتك", style=discord.ButtonStyle.success, row=3, disabled=True
        )
        self.cash_out_button.callback = self.cash_out
        self.add_item(self.cash_out_button)

    def _make_tile_button(self, index: int) -> discord.ui.Button:
        button = discord.ui.Button(label="❔", style=discord.ButtonStyle.secondary, row=index // 3)

        async def tile_callback(interaction: discord.Interaction):
            await self._on_tile_click(interaction, button, index)

        button.callback = tile_callback
        return button

    async def _on_tile_click(self, interaction: discord.Interaction, button: discord.ui.Button, index: int):
        if interaction.user.id != self.player.id:
            return await bank_interaction_card(interaction, "هذه اللعبة ليست لك", "افتح اللعبة من لوحة البنك الخاصة بك.", DANGER_COLOR)
        if self.game_over:
            return await interaction.response.send_message("⚠️ اللعبة خلصت.", ephemeral=True)

        if index == self.bomb_index:
            # انفجرت القنبلة - يخسر المكافأة المحتملة فقط، بدون أي خصم من رصيده
            self.game_over = True
            for child in self.children:
                child.disabled = True
            button.label = "💣"
            button.style = discord.ButtonStyle.danger
            embed = bank_embed(interaction,
                title="💥 ما في مكافأة هالمرة!",
                description="وقعت بالقنبلة. رصيدك ما تأثر، جرب حظك مرة ثانية لاحقًا! 🍀",
                color=DANGER_COLOR,
            )
            await edit_bank_interaction_card(interaction, embed, view=self)
            return

        # مربع آمن
        self.safe_clicks += 1
        self.multiplier += MINES_MULTIPLIER_STEP
        button.label = "💎"
        button.style = discord.ButtonStyle.success
        button.disabled = True
        self.cash_out_button.disabled = False

        potential_win = int(MINES_BASE_REWARD * self.multiplier)
        embed = bank_embed(interaction,
            title="⛏️ لعبة البنك - Mines",
            description=(
                f"اللاعب: {self.player.mention}\n"
                f"المضاعف الحالي: **x{self.multiplier:.1f}**\n"
                f"لو سحبت الحين تاخذ: **{potential_win}** عملة (مكافأة، بدون أي رهان)"
            ),
            color=SUCCESS_COLOR,
        )
        await edit_bank_interaction_card(interaction, embed, view=self)

    async def cash_out(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.id:
            return await bank_interaction_card(interaction, "هذه اللعبة ليست لك", "افتح اللعبة من لوحة البنك الخاصة بك.", DANGER_COLOR)
        if self.game_over:
            return await interaction.response.send_message("⚠️ اللعبة خلصت.", ephemeral=True)

        self.game_over = True
        winnings = int(MINES_BASE_REWARD * self.multiplier)
        new_balance = update_balance(self.player.id, winnings)

        for child in self.children:
            child.disabled = True

        embed = bank_embed(interaction,
            title="✅ سحبت مكافأتك!",
            description=(
                f"ربحت **{winnings}** عملة (مضاعف x{self.multiplier:.1f})\n"
                f"رصيدك الحالي: **{new_balance}** عملة"
            ),
            color=SUCCESS_COLOR,
        )
        await edit_bank_interaction_card(interaction, embed, view=self)

    async def on_timeout(self):
        if not self.game_over:
            # لو انتهت المهلة بدون سحب، ما فيه أي خصم - فقط تنتهي الجولة
            for child in self.children:
                child.disabled = True


# =====================================================================
#         🏦  نظام البنك الموسّع - أوامر نصية بدون سلاش ولا شرطة
#   تكتب الكلمة بروم البنك (BANK_CHANNEL_ID) وتشتغل لحالها فورًا
# =====================================================================
BANK_KEYWORDS = {
    "راتب", "بخشيش", "حظ", "روليت", "نهب", "حماية", "رهان",
    "استثمار", "تداول", "قمار", "نرد", "لعبه", "لون", "فواكه",
    "تسريع", "بيع", "شراء", "سوق", "ممتلكات", "وقت", "اغنى", "اوامر", "بنك", "تحويل", "رصيدي",
}


# محرك بطاقات البنك المصورة المسترجع من النظام الأول
BANK_BRAND = os.getenv("BANK_BRAND", "3FH BANK")
# =====================================================================
#            🖼️  محرك صور البنك (كروت + جداول + بنر النرد)
#   كل شي يُرسم بالكود (Pillow) - بدون أي قوالب جاهزة.
# =====================================================================
import glob

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_display
    HAS_AR_LIBS = True
except Exception:  # المكتبات غير مثبتة - نرجع لدعم Raqm لو متوفر
    HAS_AR_LIBS = False

BRAND_BROWN = (148, 74, 40)
GREEN = (91, 175, 106)
RED = (192, 84, 84)
GOLD = (240, 200, 70)
SS = 2                  # تكبير داخلي لتنعيم الحواف ثم تصغير
CARD_FINAL_W = 1200
_AR_RE = re.compile(r"[\u0600-\u06FF]")
_font_cache: dict = {}
_font_paths_cache: dict = {}


def _has_ar(text: str) -> bool:
    return bool(_AR_RE.search(text))


def _prep(text: str) -> str:
    """تجهيز النص العربي للرسم (ربط الحروف + ترتيب اتجاه RTL)."""
    if HAS_AR_LIBS and _has_ar(text):
        return _bidi_display(arabic_reshaper.reshape(text))
    return text


def _first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def _supports_arabic(path) -> bool:
    """يتأكد إن الخط فيه حروف عربية فعلاً (مو مربعات)."""
    if not path or not os.path.exists(path):
        return False
    try:
        f = ImageFont.truetype(path, 40, layout_engine=ImageFont.Layout.BASIC)
        def render(ch):
            img = Image.new("L", (90, 90), 0)
            ImageDraw.Draw(img).text((10, 10), ch, font=f, fill=255)
            return img.tobytes()
        arabic = render("\u0628")      # حرف ب
        missing = render("\uFFFF")     # حرف غير موجود = شكل المربع
        return arabic != missing and any(arabic)
    except Exception:
        return False


def _resolve_font_paths() -> dict:
    if _font_paths_cache:
        return _font_paths_cache
    custom = []
    for pattern in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
        custom += sorted(glob.glob(os.path.join(FILES_DIR, "fonts", pattern)))
    ar_candidates = [os.getenv("BANK_FONT_AR"), WELCOME_FONT_PATH] + custom + [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    ar = next((p for p in ar_candidates if _supports_arabic(p)), None)
    _font_paths_cache["ar_ok"] = ar is not None
    _font_paths_cache["ar"] = ar or _first_existing(ar_candidates)
    _font_paths_cache["en"] = _first_existing(
        [os.getenv("BANK_FONT_EN"),
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "C:/Windows/Fonts/arialbd.ttf",
         "/Library/Fonts/Arial Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         _font_paths_cache["ar"]])
    return _font_paths_cache


_FONT_DOWNLOAD_URLS = [
    "https://github.com/google/fonts/raw/main/ofl/lalezar/Lalezar-Regular.ttf",
    "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Bold.ttf",
    "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bslnt%2Cwght%5D.ttf",
]


async def ensure_arabic_font():
    """لو ما فيه أي خط عربي صالح على السيرفر، ينزّل خط عربي تلقائياً من Google Fonts."""
    _resolve_font_paths()
    if _font_paths_cache.get("ar_ok"):
        return
    print("⚠️ [البنك] ما لقيت خط عربي على السيرفر - جاري تنزيل خط تلقائياً...")
    folder = os.path.join(FILES_DIR, "fonts")
    os.makedirs(folder, exist_ok=True)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for url in _FONT_DOWNLOAD_URLS:
                try:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.read()
                    path = os.path.join(folder, "bank_" + url.rsplit("/", 1)[-1].replace("%5B", "[").replace("%2C", ",").replace("%5D", "]"))
                    with open(path, "wb") as f:
                        f.write(data)
                    if _supports_arabic(path):
                        _font_paths_cache.clear()
                        _font_cache.clear()
                        print(f"✅ [البنك] تم تنزيل الخط العربي: {os.path.basename(path)}")
                        return
                    os.remove(path)
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ [البنك] فشل تنزيل الخط: {e}")
    print("❌ [البنك] ما قدرت أجيب خط عربي. ارفع خط (ttf) بـ /save_file في folder: fonts أو حدد BANK_FONT_AR.")


def _font(kind: str, size: int):
    size = max(8, int(size))
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    path = _resolve_font_paths().get(kind)
    font = None
    if path:
        try:
            if HAS_AR_LIBS:
                engine = ImageFont.Layout.BASIC          # التشكيل يتم عبر arabic_reshaper
            else:
                engine = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
            font = ImageFont.truetype(path, size, layout_engine=engine)
        except Exception:
            font = None
    if font is None:
        try:
            font = ImageFont.load_default(size=size)
        except Exception:
            font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def _font_for(text: str, size: int):
    return _font("ar" if _has_ar(text) else "en", size)


def _text(d, xy, text, size, fill, anchor="la", **kw):
    d.text(xy, _prep(text), font=_font_for(text, size), fill=fill, anchor=anchor, **kw)


def _text_w(text, size) -> float:
    return _font_for(text, size).getlength(_prep(text))


def _text_fit(d, xy, text, size, fill, anchor, max_w):
    """يصغّر الخط تلقائياً لين يدخل النص بالعرض المسموح."""
    while size > 14 and _text_w(text, size) > max_w:
        size = int(size * 0.93)
    _text(d, xy, text, size, fill, anchor)


def _trunc(text: str, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


class _Ref:
    """يحوّل إحداثيات التصميم المرجعي (صورة 2020 بكسل) إلى إحداثيات الرسم الفعلي."""

    def __init__(self, ref_w, ref_h, ox=0, oy=0, final_w=CARD_FINAL_W):
        self.k = final_w * SS / ref_w
        self.ox, self.oy = ox, oy
        self.size = (int(ref_w * self.k), int(ref_h * self.k))
        self.final = (final_w, int(round(ref_h * final_w / ref_w)))

    def x(self, v): return (v - self.ox) * self.k
    def y(self, v): return (v - self.oy) * self.k
    def n(self, v): return v * self.k
    def box(self, x0, y0, x1, y1): return (self.x(x0), self.y(y0), self.x(x1), self.y(y1))


def _to_png(img: Image.Image, final_size) -> io.BytesIO:
    out = img.resize(final_size, Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _draw_icon(d, R, icon: str):
    W = (255, 255, 255, 235)
    hole = BRAND_BROWN + (70,)
    if icon == "coins":
        for yy in (150, 188, 226):
            d.ellipse(R.box(1732, yy, 1840, yy + 46), fill=W)
        d.ellipse(R.box(1788, 198, 1892, 302), fill=W)
        _text(d, (R.x(1840), R.y(252)), "$", int(R.n(72)), hole, "mm")
    elif icon in ("chart_up", "chart_down"):
        for bx, top in ((1736, 205), (1778, 232), (1820, 215), (1862, 250)):
            d.rectangle(R.box(bx, top, bx + 30, 290), fill=W)
        d.rectangle(R.box(1730, 292, 1892, 302), fill=W)
        if icon == "chart_down":
            d.line([(R.x(1735), R.y(145)), (R.x(1860), R.y(205))], fill=W, width=int(R.n(10)))
            d.polygon([(R.x(1892), R.y(222)), (R.x(1830), R.y(215)), (R.x(1872), R.y(168))], fill=W)
        else:
            d.line([(R.x(1735), R.y(195)), (R.x(1860), R.y(135))], fill=W, width=int(R.n(10)))
            d.polygon([(R.x(1892), R.y(118)), (R.x(1830), R.y(125)), (R.x(1872), R.y(172))], fill=W)
    elif icon == "transfer":
        d.line([(R.x(1740), R.y(190)), (R.x(1860), R.y(190))], fill=W, width=int(R.n(16)))
        d.polygon([(R.x(1896), R.y(190)), (R.x(1850), R.y(152)), (R.x(1850), R.y(228))], fill=W)
        d.line([(R.x(1880), R.y(260)), (R.x(1760), R.y(260))], fill=W, width=int(R.n(16)))
        d.polygon([(R.x(1724), R.y(260)), (R.x(1770), R.y(222)), (R.x(1770), R.y(298))], fill=W)


def _smooth(points, steps=10):
    """منحنى ناعم (Catmull-Rom) يمر بكل النقاط."""
    if len(points) < 3:
        return points
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                       + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                for j in (0, 1)))
    out.append(points[-1])
    return out


def _draw_chart(d, R, values, up: bool, tag: str, pct_text: str):
    """رسم بياني أعمدة + منحنى + فقاعة (ربح/خسارة) - نفس ستايل بطاقة الاستثمار."""
    B = BRAND_BROWN
    color = GREEN if up else RED
    n = len(values)
    x0, x1, base, top_limit = 137, 1172, 966, 700
    slot = (x1 - x0) / n
    bw = slot * 0.72
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    tops = []
    for i, v in enumerate(values):
        h = 30 + (v - lo) / span * (base - top_limit - 30)
        left = x0 + i * slot
        d.rectangle(R.box(left, base - h, left + bw, base), fill=B + (255,))
        tops.append((left + bw / 2, base - h))
    curve_pts = [(x, y - 45) for x, y in tops]
    curve = _smooth([(R.x(x), R.y(y)) for x, y in curve_pts])
    d.line(curve, fill=color + (255,), width=int(R.n(6)), joint="curve")
    # نقطة + فقاعة عند أعلى قمة
    peak_i = min(range(n), key=lambda i: curve_pts[i][1])
    px, py = curve_pts[peak_i]
    d.ellipse((R.x(px) - R.n(11), R.y(py) - R.n(11), R.x(px) + R.n(11), R.y(py) + R.n(11)), fill=color + (255,))
    tw = _text_w(tag, int(R.n(40)))
    bx0, bx1 = R.x(px) - tw / 2 - R.n(18), R.x(px) + tw / 2 + R.n(18)
    by1 = R.y(py) - R.n(26)
    by0 = by1 - R.n(64)
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=R.n(18), fill=color + (255,))
    d.polygon([(R.x(px) - R.n(10), by1 - 1), (R.x(px) + R.n(6), by1 - 1), (R.x(px) + R.n(10), by1 + R.n(20))], fill=color + (255,))
    _text(d, ((bx0 + bx1) / 2, (by0 + by1) / 2), tag, int(R.n(40)), (255, 255, 255, 255), "mm")
    _text(d, (R.x(x1 + 22), R.y(tops[-1][1] - 30)), pct_text, int(R.n(58)), color + (255,), "lm")


def _render_card_sync(avatar_bytes, name, title, main_text, amount=None, side=None,
                      icon="coins", footer=True, chart=None, lines=None) -> io.BytesIO:
    """بطاقة البنك الأساسية (كشف حساب / تحويل / شراء / نتيجة استثمار...)."""
    R = _Ref(1900, 904, 60, 90)
    B = BRAND_BROWN
    WHITE = (255, 255, 255, 255)
    img = Image.new("RGBA", R.size, B + (0,))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle(R.box(69, 98, 1950, 984), radius=R.n(50), fill=B + (255,))
    d.rounded_rectangle(R.box(386, 113, 1935, 322), radius=R.n(38), fill=B + (36,))
    d.rounded_rectangle(R.box(85, 337, 1935, 969), radius=R.n(40), fill=B + (92,))
    d.rectangle(R.box(69, 98, 386, 418), fill=B + (255,))

    try:
        av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((int(R.n(290)), int(R.n(290))), Image.LANCZOS)
        av = Image.alpha_composite(Image.new("RGBA", av.size, B + (255,)), av)
        img.paste(av, (int(R.x(85)), int(R.y(115))))
    except Exception:
        pass

    _text_fit(d, (R.x(422), R.y(213)), _trunc(name, 18), int(R.n(62)), WHITE, "lm", R.n(620))
    _text(d, (R.x(1680), R.y(212)), title, int(R.n(66)), WHITE, "rm")
    _draw_icon(d, R, icon)

    if "\n" in str(main_text):
        card_lines = [line.strip() for line in str(main_text).splitlines() if line.strip()][:5]
        for line_index, line in enumerate(card_lines):
            _text_fit(d, (R.x(1878), R.y(420 + line_index * 92)), line, int(R.n(53)), WHITE, "rm", R.n(1700))
    else:
        _text_fit(d, (R.x(1878), R.y(470)), main_text, int(R.n(68)), WHITE, "rm", R.n(1700))

    if chart:
        _draw_chart(d, R, chart["values"], chart["up"], chart["tag"], chart["pct_text"])
    if lines:
        # كل سطر = (تسمية عربية، قيمة لاتينية/أرقام، لون القيمة، y) - نرسمهم منفصلين عشان ما ينقلب $ مع العربي
        for label, value, color, yy in lines:
            size = int(R.n(56))
            _text(d, (R.x(1878), R.y(yy)), label, size, (255, 255, 255, 255), "rm")
            _text(d, (R.x(1878) - _text_w(label, size) - R.n(22), R.y(yy)), value, size, tuple(color) + (255,), "rm")
    if amount:
        _text(d, (R.x(162), R.y(708)), amount, int(R.n(84)), WHITE, "lm")
    if side:
        _text_fit(d, (R.x(1878), R.y(708)), side, int(R.n(50)), (255, 255, 255, 235), "rm", R.n(1000))
    if footer and not chart:
        brand_size = int(R.n(80))
        d.text((R.x(162), R.y(848)), BANK_BRAND, font=_font("en", brand_size), fill=B + (255,), anchor="lm")
        bw = _font("en", brand_size).getlength(BANK_BRAND)
        d.text((R.x(162) + bw + R.n(24), R.y(848)), "Pay", font=_font("en", brand_size), fill=WHITE, anchor="lm")

    return _to_png(img, R.final)


def _render_table_sync(title, headers, rows, note=None, icon="chart_up") -> io.BytesIO:
    """جدول بنفس ستايل البطاقة (للسوق والمحفظة). rows = [(عمود1, عمود2, عمود3, لون3, عريض?)]"""
    n = len(rows)
    row_h = 92
    body_top = 337
    body_bottom = body_top + 95 + n * row_h + (120 if note else 40)
    outer_bottom = body_bottom + 15
    R = _Ref(1900, outer_bottom + 10 - 90, 60, 90)
    B = BRAND_BROWN
    WHITE = (255, 255, 255, 255)
    img = Image.new("RGBA", R.size, B + (0,))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle(R.box(69, 98, 1950, outer_bottom), radius=R.n(50), fill=B + (255,))
    d.rounded_rectangle(R.box(85, 113, 1935, 322), radius=R.n(38), fill=B + (36,))
    d.rounded_rectangle(R.box(85, body_top, 1935, body_bottom), radius=R.n(40), fill=B + (92,))

    _text(d, (R.x(1680), R.y(212)), title, int(R.n(66)), WHITE, "rm")
    _draw_icon(d, R, icon)
    _text(d, (R.x(130), R.y(213)), BANK_BRAND, int(R.n(56)), WHITE, "lm")

    col_x = (1850, 1180, 640)
    for cx, h in zip(col_x, headers):
        _text(d, (R.x(cx), R.y(body_top + 55)), h, int(R.n(44)), (255, 255, 255, 190), "rm")
    d.line([(R.x(120), R.y(body_top + 95)), (R.x(1900), R.y(body_top + 95))], fill=WHITE[:3] + (60,), width=int(R.n(3)))

    for i, row in enumerate(rows):
        c1, c2, c3, color3 = row[:4]
        bold = row[4] if len(row) > 4 else False
        cy = body_top + 95 + i * row_h + row_h // 2
        if bold:
            d.rectangle(R.box(110, cy - row_h // 2 + 6, 1910, cy + row_h // 2 - 6), fill=B + (70,))
        _text_fit(d, (R.x(col_x[0]), R.y(cy)), c1, int(R.n(56)), WHITE, "rm", R.n(620))
        _text_fit(d, (R.x(col_x[1]), R.y(cy)), c2, int(R.n(56)), WHITE, "rm", R.n(520))
        _text_fit(d, (R.x(col_x[2]), R.y(cy)), c3, int(R.n(56)), tuple(color3 or (255, 255, 255)) + (255,), "rm", R.n(470))
        if i < n - 1:
            d.line([(R.x(120), R.y(cy + row_h // 2)), (R.x(1900), R.y(cy + row_h // 2))], fill=WHITE[:3] + (28,), width=int(R.n(2)))
    if note:
        _text_fit(d, (R.x(1010), R.y(body_bottom - 55)), note, int(R.n(40)), (255, 255, 255, 200), "mm", R.n(1750))

    return _to_png(img, R.final)


# ---------------------------------------------------------------------
#                       🎲  بنر النرد (كله مرسوم)
# ---------------------------------------------------------------------
_PIPS = {
    1: [(0, 0)],
    2: [(-1, -1), (1, 1)],
    3: [(-1, -1), (0, 0), (1, 1)],
    4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
    5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
    6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)],
}


def _circle_avatar(avatar_bytes, diameter) -> Image.Image:
    av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter - 1, diameter - 1), fill=255)
    av.putalpha(mask)
    return av


def _render_dice_sync(bot_avatar, user_avatar, bot_roll, user_roll, outcome, result_text, bet_text) -> io.BytesIO:
    """outcome: win / lose / tie  (من منظور اللاعب)"""
    W, H = 1524, 572
    k = SS
    B = BRAND_BROWN
    WHITE = (255, 255, 255, 255)
    img = Image.new("RGBA", (W * k, H * k), B + (0,))

    # خلفية: صورة البوت مكبّرة ومغبّشة ومظلّلة (بدل قالب جاهز)
    try:
        bg = Image.open(io.BytesIO(bot_avatar)).convert("RGB")
        side = max(W * k, H * k)
        bg = bg.resize((side, side), Image.LANCZOS).filter(ImageFilter.GaussianBlur(9 * k))
        left, top = (side - W * k) // 2, (side - H * k) // 2
        bg = bg.crop((left, top, left + W * k, top + H * k))
    except Exception:
        bg = Image.new("RGB", (W * k, H * k), (60, 40, 30))
    bg = ImageEnhance.Brightness(bg).enhance(0.42).convert("RGBA")
    img.paste(bg, (0, 0))

    # اسم اللعبة (مائل) خلف النرد
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((W * k * 0.66, 168 * k), "PARTY ROYALE", font=_font("en", 92 * k), fill=(205, 205, 205, 235),
            anchor="mm", stroke_width=5 * k, stroke_fill=(110, 60, 40, 255))
    ld.text((W * k * 0.66, 292 * k), "3FH", font=_font("en", 190 * k), fill=(232, 205, 70, 235),
            anchor="mm", stroke_width=6 * k, stroke_fill=(120, 70, 30, 255))
    s, cy = 0.22, 230 * k
    layer = layer.transform(layer.size, Image.AFFINE, (1, s, -s * cy, 0, 1, 0), resample=Image.BICUBIC)
    layer = ImageEnhance.Brightness(layer).enhance(0.8)
    img.alpha_composite(layer)

    d = ImageDraw.Draw(img)
    stroke = 14 * k
    # إطار + ساقين الأفاتار
    d.rounded_rectangle((stroke // 2, stroke // 2, W * k - stroke // 2, H * k - stroke // 2),
                        radius=70 * k, outline=B + (255,), width=stroke)
    for sx in (215, 1305):
        d.line([(sx * k, 300 * k), (sx * k, H * k)], fill=B + (255,), width=stroke)

    # أفاتارات + خطوط ربط + نرد
    av_r = 125
    centers = {"bot": (345, 297), "user": (1178, 297)}
    dice_c = {"bot": (616, 295), "user": (906, 295)}
    win_side = "user" if outcome == "win" else "bot" if outcome == "lose" else None
    for who, avb in (("bot", bot_avatar), ("user", user_avatar)):
        cx, cyy = centers[who]
        ring = GOLD if win_side == who else B
        d.ellipse(((cx - av_r - 14) * k, (cyy - av_r - 14) * k, (cx + av_r + 14) * k, (cyy + av_r + 14) * k), fill=ring + (255,))
        try:
            av = _circle_avatar(avb, av_r * 2 * k)
            img.alpha_composite(av, ((cx - av_r) * k, (cyy - av_r) * k))
        except Exception:
            pass
        dx, dy = dice_c[who]
        edge_x = cx + av_r + 12 if who == "bot" else cx - av_r - 12
        d.line([(edge_x * k, dy * k), (dx * k, dy * k)], fill=B + (255,), width=12 * k)

    for who, roll in (("bot", bot_roll), ("user", user_roll)):
        dx, dy = dice_c[who]
        half = 59
        d.rounded_rectangle(((dx - half - 8) * k, (dy - half - 8) * k, (dx + half + 8) * k, (dy + half + 8) * k),
                            radius=24 * k, fill=B + (255,))
        d.rounded_rectangle(((dx - half) * k, (dy - half) * k, (dx + half) * k, (dy + half) * k),
                            radius=16 * k, fill=WHITE)
        for px, py in _PIPS[roll]:
            ccx, ccy = (dx + px * 30) * k, (dy + py * 30) * k
            d.ellipse((ccx - 11 * k, ccy - 11 * k, ccx + 11 * k, ccy + 11 * k), fill=B + (255,))

    _text(d, (W * k * 0.5, 78 * k), result_text, 62 * k, WHITE, "mm", stroke_width=3 * k, stroke_fill=(0, 0, 0, 255))
    tone = GREEN if outcome == "win" else RED if outcome == "lose" else (230, 230, 230)
    _text(d, (W * k * 0.5, 470 * k), bet_text, 66 * k, tone + (255,), "mm", stroke_width=4 * k, stroke_fill=(0, 0, 0, 255))

    # قص الزوايا الخارجية بشكل دائري شفاف
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W * k - 1, H * k - 1), radius=70 * k, fill=255)
    img.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
    return _to_png(img, (W, H))


# =====================================================================
#          📈  السوق العالمي (أسعار حقيقية تتحدث تلقائياً)
#   المصدر: Yahoo Finance (بدون مفتاح API). لو فشل جلب أصل معين يستمر
#   بسعر تقديري متحرك بسيط لين يرجع الاتصال، ولا يوقف البوت.
# =====================================================================

def _load_bank_font(size: int) -> ImageFont.FreeTypeFont:
    """نفس منطق تحميل خط كرت الترحيب - يستخدم بكل صور نظام البنك."""
    if WELCOME_FONT_PATH and os.path.exists(WELCOME_FONT_PATH):
        try:
            return ImageFont.truetype(WELCOME_FONT_PATH, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _resolve_bank_identity(ctx):
    """يرجع (guild, user, رابط أفتار البوت) سواء كان ctx رسالة عادية أو Interaction سلاش."""
    guild = getattr(ctx, "guild", None)
    user = getattr(ctx, "author", None) or getattr(ctx, "user", None)
    bot_avatar = None
    if guild and guild.me:
        bot_avatar = guild.me.display_avatar.url
    elif bot.user:
        bot_avatar = bot.user.display_avatar.url
    return guild, user, bot_avatar


def bank_embed(ctx, *, title: str, description: str, color: int, thumbnail_user=None) -> discord.Embed:
    """إيمبد موحّد بثيم 3FH BANK - يُستخدم بكل أوامر البنك (النصية والسلاش)."""
    guild, user, bot_avatar = _resolve_bank_identity(ctx)
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name=BANK_BRAND_NAME, icon_url=bot_avatar)
    target_user = thumbnail_user or user
    if target_user:
        embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.set_footer(text=BANK_FOOTER_TEXT, icon_url=bot_avatar)
    return embed


_BANK_AVATAR_CACHE: dict[str, bytes] = {}

async def _bank_avatar_bytes(user) -> bytes:
    url = user.display_avatar.replace(size=256, format="png").url
    if url not in _BANK_AVATAR_CACHE:
        _BANK_AVATAR_CACHE[url] = await user.display_avatar.replace(size=256, format="png").read()
        if len(_BANK_AVATAR_CACHE) > 250:
            _BANK_AVATAR_CACHE.pop(next(iter(_BANK_AVATAR_CACHE)))
    return _BANK_AVATAR_CACHE[url]


def _clean_card_text(value: str, guild=None) -> str:
    value = str(value or "")
    def replace_mention(match):
        try:
            member = guild.get_member(int(match.group(1))) if guild else None
            return "@" + (member.display_name if member else "عضو")
        except Exception:
            return "عضو"
    value = re.sub(r"<@!?(\d+)>", replace_mention, value)
    value = re.sub(r"<@&(\d+)>", "رتبة", value)
    value = re.sub(r"<#[0-9]+>", "روم", value)
    value = re.sub(r"```|`|\*\*|__|~~|\*", "", value)
    value = re.sub(r"https?://\S+", "", value)
    lines = [" ".join(line.split()).strip() for line in value.splitlines() if line.strip()]
    if not lines:
        lines = ["تمت العملية بنجاح"]
    wrapped = []
    for line in lines:
        words = line.split()
        current = ""
        for word in words:
            if current and len(current) + len(word) + 1 > 48:
                wrapped.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            wrapped.append(current)
    return "\n".join(wrapped[:5])


async def _bank_embed_card(user, embed) -> discord.File:
    raw_title = getattr(embed, "title", None) or BANK_BRAND
    title = _clean_card_text(raw_title, getattr(user, "guild", None)).replace("\n", " ")
    raw_description = getattr(embed, "description", None) or ""
    for field in getattr(embed, "fields", []) or []:
        raw_description += f"\n{field.name}: {field.value}"
    description = _clean_card_text(raw_description, getattr(user, "guild", None))
    # أمر الأوامر يظهر كجدول صورة كامل، بدل اختصار القائمة داخل بطاقة واحدة.
    if "أوامر البنك" in title and "BANK_HELP_LINES" in globals():
        rows = []
        for command_name, command_desc in BANK_HELP_LINES:
            rows.append((str(command_name)[:30], str(command_desc)[:55], "", (255, 255, 255), False))
        buf = await asyncio.get_running_loop().run_in_executor(
            None, functools.partial(_render_table_sync, "أوامر البنك", ["الأمر", "الشرح", ""], rows,
                                    note="كل الأرصدة افتراضية ولا قيمة لها خارج اللعبة.", icon="coins")
        )
    else:
        avatar = await _bank_avatar_bytes(user)
        buf = await asyncio.get_running_loop().run_in_executor(
            None, functools.partial(_render_card_sync, avatar, user.display_name, title, description)
        )
    return discord.File(buf, filename="bank-card.png")


async def send_bank_reply(message, *, embed=None, file=None, files=None, view=None,
                          mention_author=False, content=None, **kwargs):
    """يحوّل مخرجات البنك إلى بطاقة PNG؛ وتبقى ملفات GIF/الألعاب والأزرار شغالة."""
    user = getattr(message, "author", None) or getattr(message, "user", None)
    if embed is None or user is None:
        return await message.reply(content=content, embed=embed, file=file, files=files,
                                   view=view, mention_author=mention_author, **kwargs)
    card = await _bank_embed_card(user, embed)
    attachments = [card]
    if file is not None:
        attachments.append(file)
    if files:
        attachments.extend(files)
    return await message.reply(content=content, files=attachments, view=view,
                               mention_author=mention_author, **kwargs)


async def edit_bank_interaction_card(interaction: discord.Interaction, embed, view=None):
    """يحدّث نتيجة لعبة البنك كصورة بدل إيمبد، مع الإبقاء على أزرار الجولة."""
    card = await _bank_embed_card(interaction.user, embed)
    return await interaction.response.edit_message(content=None, embed=None, attachments=[card], view=view)


async def bank_interaction_card(interaction: discord.Interaction, title: str, description: str,
                                color: int = MAIN_COLOR, ephemeral: bool = True):
    embed = bank_embed(interaction, title=title, description=description, color=color)
    card = await _bank_embed_card(interaction.user, embed)
    if not interaction.response.is_done():
        return await interaction.response.send_message(file=card, ephemeral=ephemeral)
    return await interaction.followup.send(file=card, ephemeral=ephemeral)


def pay_card_embed(ctx, *, operation: str, subtitle: str, amount_line: str, color: int) -> discord.Embed:
    """كرت عملية موحّد (إيداع/خصم) بنفس روح كرت 'Pay' المرجعي - بدون أي نص عربي داخل صورة (كله نص ديسكورد حقيقي)."""
    guild, user, bot_avatar = _resolve_bank_identity(ctx)
    embed = discord.Embed(
        title=f"🏦 {PAY_CARD_NAME}",
        description=f"**{operation}**\n{subtitle}\n\n{amount_line}",
        color=color,
    )
    if user:
        embed.set_footer(text=user.display_name, icon_url=user.display_avatar.url)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def get_job_title(member) -> str:
    """يحدد المسمى الوظيفي حسب الرول: مالك السيرفر أو رتبة BANK_OWNER_ROLE_ID = شيخ، غير كذا = عامل."""
    if not isinstance(member, discord.Member) or not member.guild:
        return "عامل"
    if member.id == member.guild.owner_id:
        return "شيخ"
    role_names = {r.name.strip() for r in member.roles}
    if BANK_OWNER_ROLE_ID and any(r.id == BANK_OWNER_ROLE_ID for r in member.roles):
        return "شيخ"
    if role_names & {"Owner", "owner", "المالك", "مالك", "اونر"}:
        return "شيخ"
    return "عامل"


def render_roulette_wheel(prize_labels: list[str], winning_index: int, avatar_bytes: bytes | None = None) -> discord.File:
    """يرسم عجلة روليت متحركة فعليًا (تدور قدامك وتوقف بالتدريج على القطاع الفائز) بثيم ذهبي/داكن."""
    size = 640
    center = size // 2
    radius = size // 2 - 24

    n = max(1, len(prize_labels))
    sector_angle = 360 / n
    # الزاوية النهائية اللي تخلي القطاع الفائز يوقف بالضبط عند المؤشر (يمين العجلة = 0 درجة)
    final_rotation = -(winning_index * sector_angle) - sector_angle / 2
    total_spin_extra = 3 * 360  # 3 لفات كاملة قبل ما تستقر

    font = _load_bank_font(24)

    avatar_layer = None
    if avatar_bytes:
        try:
            avatar_size = int(radius * 0.55)
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
            avatar_img.putalpha(mask)
            avatar_layer = (avatar_img, avatar_size)
        except Exception:
            avatar_layer = None

    def render_frame(rotation: float, highlight: bool) -> Image.Image:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for i, label in enumerate(prize_labels):
            start = rotation + i * sector_angle
            end = start + sector_angle
            is_winner = highlight and i == winning_index
            color = (241, 196, 15, 255) if is_winner else BANK_WHEEL_SLICE_COLORS[i % 2]
            draw.pieslice(
                (center - radius, center - radius, center + radius, center + radius),
                start, end, fill=color, outline=(15, 15, 17, 255), width=2,
            )
            mid_angle = math.radians((start + end) / 2)
            text_r = radius * 0.68
            tx = center + text_r * math.cos(mid_angle)
            ty = center + text_r * math.sin(mid_angle)
            text_color = (20, 20, 20, 255) if is_winner else (241, 196, 15, 255)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((tx - tw / 2, ty - th / 2), label, font=font, fill=text_color)

        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            outline=(241, 196, 15, 255), width=6,
        )
        pointer = [(size - 4, center - 20), (size - 4, center + 20), (size - 36, center)]
        draw.polygon(pointer, fill=(241, 196, 15, 255))

        if avatar_layer:
            avatar_img, avatar_size = avatar_layer
            image.paste(avatar_img, (center - avatar_size // 2, center - avatar_size // 2), avatar_img)
            draw.ellipse(
                (center - avatar_size // 2, center - avatar_size // 2, center + avatar_size // 2, center + avatar_size // 2),
                outline=(241, 196, 15, 255), width=4,
            )
        return image.convert("RGB")

    frame_count = 22
    frames = []
    durations = []
    for f in range(frame_count):
        t = f / (frame_count - 1)
        eased = 1 - (1 - t) ** 3  # تباطؤ تدريجي (ease-out) - نفس إحساس عجلة حقيقية
        rotation = final_rotation - (1 - eased) * total_spin_extra
        highlight = f == frame_count - 1
        frames.append(render_frame(rotation, highlight))
        durations.append(int(35 + t * 170))
    # وقفة أطول على النتيجة النهائية
    frames.append(render_frame(final_rotation, True))
    durations.append(2500)

    buffer = io.BytesIO()
    frames[0].save(
        buffer, format="GIF", save_all=True, append_images=frames[1:],
        duration=durations, optimize=False,
    )
    buffer.seek(0)
    return discord.File(buffer, filename="roulette.gif")


def _ask_amount_embed(message: discord.Message, action: str) -> discord.Embed:
    return bank_embed(message,
        title="❓ حدد المبلغ",
        description=f"اكتب المبلغ بعد الأمر، مثال:\n`{action} 5000` أو `{action} نص` أو `{action} كامل`",
        color=MAIN_COLOR,
    )


def _min_bet_embed(message: discord.Message, min_amount: int) -> discord.Embed:
    return bank_embed(message,
        title="❌ المبلغ قليل",
        description=f"أقل مبلغ مسموح به هنا: **{format_amount(min_amount)}** 💵",
        color=DANGER_COLOR,
    )


def _not_enough_embed(message: discord.Message, balance: int) -> discord.Embed:
    return bank_embed(message,
        title="❌ رصيدك ما يكفي",
        description=f"رصيدك الحالي: **{format_amount(balance)}** 💵",
        color=DANGER_COLOR,
    )


async def _check_cooldown(message: discord.Message, action: str) -> bool:
    remaining = get_cooldown_remaining(message.author.id, action)
    if remaining > 0:
        embed = bank_embed(message,
            title=None,
            description=f"🕐 لا تعيدها عاد تعال بعد {format_bank_duration(remaining)}",
            color=DANGER_COLOR,
        )
        await send_bank_reply(message, embed=embed, mention_author=False)
        return False
    return True


# --- راتب / بخشيش / حظ ---
class _BankMessageProxy:
    """محول صغير حتى تقدر أزرار البنك تشغّل نفس أوامر الرسائل بدون تكرار منطق الاقتصاد."""
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.author = interaction.user
        self.guild = interaction.guild
        self.channel = interaction.channel
        self.mentions = []
        self.content = ""

    async def reply(self, content=None, *, embed=None, file=None, files=None, view=None,
                    mention_author=False, ephemeral=True, **kwargs):
        payload = {}
        if content is not None: payload["content"] = content
        if embed is not None: payload["embed"] = embed
        if file is not None: payload["file"] = file
        if files is not None: payload["files"] = files
        if view is not None: payload["view"] = view
        payload["ephemeral"] = ephemeral
        if not self.interaction.response.is_done():
            return await self.interaction.response.send_message(**payload)
        return await self.interaction.followup.send(**payload)


async def bank_cmd_balance(message):
    balance = get_balance(message.author.id)
    embed = pay_card_embed(message, operation="كشف حساب", subtitle="هذا رصيدك الحالي في البنك الافتراضي",
        amount_line=f"الرصيد: {format_amount(balance)}", color=MAIN_COLOR)
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_transfer(message: discord.Message, arg: str | None):
    receiver = message.mentions[0] if getattr(message, "mentions", None) else None
    parts = (arg or "").split()
    if receiver is None and parts:
        first = re.sub(r"[<@!> ]", "", parts[0])
        if first.isdigit() and message.guild:
            receiver = message.guild.get_member(int(first))
        if receiver and len(parts) > 1:
            parts = parts[1:]
    amount_text = parts[-1] if parts else ""
    if receiver is None or not amount_text:
        embed = bank_embed(message, title="تحويل رصيد", description="الاستخدام: تحويل @العضو المبلغ", color=DANGER_COLOR)
        return await send_bank_reply(message, embed=embed, mention_author=False)
    if receiver.bot or receiver.id == message.author.id:
        embed = bank_embed(message, title="تعذر التحويل", description="اختر عضوًا آخر غير البوت أو نفسك.", color=DANGER_COLOR)
        return await send_bank_reply(message, embed=embed, mention_author=False)
    amount = parse_amount_arg(amount_text, get_balance(message.author.id))
    balance = get_balance(message.author.id)
    if amount is None or amount <= 0:
        embed = bank_embed(message, title="تعذر التحويل", description="اكتب مبلغًا صحيحًا أكبر من صفر.", color=DANGER_COLOR)
        return await send_bank_reply(message, embed=embed, mention_author=False)
    if amount > balance:
        embed = bank_embed(message, title="رصيد غير كافٍ", description=f"رصيدك {format_amount(balance)} ولا يكفي لتحويل {format_amount(amount)}.", color=DANGER_COLOR)
        return await send_bank_reply(message, embed=embed, mention_author=False)
    update_balance(message.author.id, -amount)
    receiver_balance = update_balance(receiver.id, amount)
    embed = bank_embed(message, title="تم التحويل بنجاح",
        description=f"تم التحويل إلى {receiver.display_name}\nالمبلغ: {format_amount(amount)}\nرصيد المستلم: {format_amount(receiver_balance)}",
        color=SUCCESS_COLOR)
    await send_bank_reply(message, embed=embed, mention_author=False)


class BankGamesView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def _run(self, interaction, action, *args):
        if interaction.user.id != self.owner_id:
            return await bank_interaction_card(interaction, "لوحة البنك", "افتح لوحة البنك من حسابك لاستخدام هذه الأزرار.", DANGER_COLOR)
        proxy = _BankMessageProxy(interaction)
        await action(proxy, *args)

    @discord.ui.button(label="الروليت", emoji="🎡", style=discord.ButtonStyle.primary, row=0)
    async def roulette(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_roulette)

    @discord.ui.button(label="الفواكه", emoji="🍒", style=discord.ButtonStyle.primary, row=0)
    async def fruits(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_fruits)

    @discord.ui.button(label="حجرة ورقة مقص", emoji="🎮", style=discord.ButtonStyle.secondary, row=0)
    async def rps(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_rps)


class BankHomeView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    async def _run(self, interaction, action, *args):
        if interaction.user.id != self.owner_id:
            return await bank_interaction_card(interaction, "لوحة البنك", "هذه اللوحة لصاحبها؛ اكتب بنك لفتح لوحتك.", DANGER_COLOR)
        await action(_BankMessageProxy(interaction), *args)

    @discord.ui.button(label="رصيدي", emoji="💰", style=discord.ButtonStyle.success, row=0)
    async def balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_balance)

    @discord.ui.button(label="استلام الراتب", emoji="💵", style=discord.ButtonStyle.success, row=0)
    async def salary(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_salary)

    @discord.ui.button(label="السوق", emoji="📈", style=discord.ButtonStyle.primary, row=0)
    async def market(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_stock_market)

    @discord.ui.button(label="الألعاب", emoji="🎰", style=discord.ButtonStyle.primary, row=1)
    async def games(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await bank_interaction_card(interaction, "لوحة البنك", "هذه اللوحة لصاحبها؛ اكتب بنك لفتح لوحتك.", DANGER_COLOR)
        embed = bank_embed(interaction, title="ألعاب البنك", description="اختر اللعبة من الأزرار بالأسفل.", color=MAIN_COLOR)
        card = await _bank_embed_card(interaction.user, embed)
        await interaction.response.send_message(file=card, view=BankGamesView(self.owner_id), ephemeral=True)

    @discord.ui.button(label="الممتلكات", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)
    async def properties(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_properties)

    @discord.ui.button(label="أوامر البنك", emoji="📜", style=discord.ButtonStyle.secondary, row=1)
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_help)

    @discord.ui.button(label="تحويل", emoji="💸", style=discord.ButtonStyle.secondary, row=2)
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await bank_interaction_card(interaction, "لوحة البنك", "هذه اللوحة لصاحبها؛ اكتب بنك لفتح لوحتك.", DANGER_COLOR)
        await interaction.response.send_modal(BankTransferModal())

    @discord.ui.button(label="استثمار", emoji="🌱", style=discord.ButtonStyle.success, row=2)
    async def invest(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await bank_interaction_card(interaction, "لوحة البنك", "هذه اللوحة لصاحبها؛ اكتب بنك لفتح لوحتك.", DANGER_COLOR)
        await interaction.response.send_modal(BankAmountModal("استثمار"))

    @discord.ui.button(label="تداول", emoji="📊", style=discord.ButtonStyle.primary, row=2)
    async def trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await bank_interaction_card(interaction, "لوحة البنك", "هذه اللوحة لصاحبها؛ اكتب بنك لفتح لوحتك.", DANGER_COLOR)
        await interaction.response.send_modal(BankAmountModal("تداول"))

    @discord.ui.button(label="شراء", emoji="🛒", style=discord.ButtonStyle.secondary, row=3)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_buy)

    @discord.ui.button(label="بيع", emoji="💰", style=discord.ButtonStyle.secondary, row=3)
    async def sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, bank_cmd_sell)


class BankAmountModal(discord.ui.Modal):
    def __init__(self, action: str):
        super().__init__(title=f"{action} رصيد افتراضي")
        self.action = action
        self.amount = discord.ui.TextInput(label="المبلغ", placeholder="مثال: 500 أو نص أو كامل", required=True, max_length=20)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        proxy = _BankMessageProxy(interaction)
        await bank_cmd_market(proxy, str(self.amount.value), self.action)


class BankTransferModal(discord.ui.Modal, title="تحويل رصيد افتراضي"):
    member_id = discord.ui.TextInput(label="معرّف العضو أو منشنه", placeholder="مثال: 123456789012345678", required=True, max_length=30)
    amount = discord.ui.TextInput(label="المبلغ", placeholder="مثال: 500 أو نص أو كامل", required=True, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.member_id.value).strip()
        match = re.search(r"\d{15,22}", raw)
        receiver = interaction.guild.get_member(int(match.group())) if match and interaction.guild else None
        if not receiver:
            embed = bank_embed(interaction, title="تعذر التحويل", description="ما قدرت ألقى العضو؛ استخدم معرّفه الصحيح أو منشنه.", color=DANGER_COLOR)
            return await interaction.response.send_message(file=await _bank_embed_card(interaction.user, embed), ephemeral=True)
        proxy = _BankMessageProxy(interaction)
        proxy.mentions = [receiver]
        await bank_cmd_transfer(proxy, f"{self.amount.value}")


async def bank_cmd_panel(message):
    embed = bank_embed(message, title="3FH BANK", description="مرحبًا بك في البنك الافتراضي. استخدم الأزرار للتنقل بين الخدمات، وكل النتائج تظهر كبطاقات صور.", color=MAIN_COLOR)
    card = await _bank_embed_card(message.author, embed)
    await message.reply(file=card, view=BankHomeView(message.author.id), mention_author=False)


async def bank_cmd_salary(message: discord.Message):
    if not await _check_cooldown(message, "راتب"):
        return
    set_cooldown(message.author.id, "راتب")
    job_title = get_job_title(message.author)
    new_balance = update_balance(message.author.id, SALARY_AMOUNT)
    embed = pay_card_embed(message,
        operation="عملية ايداع",
        subtitle=f"تم ايداع مبلغ راتب, الوظيفة : {job_title}",
        amount_line=f"💵 {format_amount(SALARY_AMOUNT)}\nرصيدك الحالي: **{format_amount(new_balance)}**",
        color=SUCCESS_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_tip(message: discord.Message):
    if not await _check_cooldown(message, "بخشيش"):
        return
    set_cooldown(message.author.id, "بخشيش")
    amount = random.randint(TIP_MIN, TIP_MAX)
    new_balance = update_balance(message.author.id, amount)
    embed = pay_card_embed(message,
        operation="عملية ايداع",
        subtitle="تم ايداع مبلغ حساب المواطن",
        amount_line=f"💵 {format_amount(amount)}\nرصيدك الحالي: **{format_amount(new_balance)}**",
        color=SUCCESS_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_luck(message: discord.Message):
    if not await _check_cooldown(message, "حظ"):
        return
    set_cooldown(message.author.id, "حظ")
    amount = random.randint(LUCK_MIN, LUCK_MAX)
    new_balance = update_balance(message.author.id, amount)
    won = amount >= 0
    embed = pay_card_embed(message,
        operation="عملية ايداع" if won else "عملية خصم",
        subtitle="حظك هالوقت 🍀" if won else "حظك نحس هالمرة 😬",
        amount_line=f"💵 {format_amount(abs(amount))}\nرصيدك الحالي: **{format_amount(new_balance)}**",
        color=SUCCESS_COLOR if won else DANGER_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


# --- روليت ---
async def bank_cmd_roulette(message: discord.Message):
    if not await _check_cooldown(message, "روليت"):
        return
    set_cooldown(message.author.id, "روليت")
    prizes = [p for p, _ in ROULETTE_PRIZES]
    weights = [w for _, w in ROULETTE_PRIZES]
    winning_index = random.choices(range(len(prizes)), weights=weights, k=1)[0]
    prize = prizes[winning_index]
    labels = [
        f"G x{p.split(':')[1]}" if isinstance(p, str) and p.startswith("gold:") else format_amount(p)
        for p in prizes
    ]

    if isinstance(prize, str) and prize.startswith("gold:"):
        amount = int(prize.split(":")[1])
        new_gold = update_gold(message.author.id, amount)
        embed = bank_embed(message,
            title="🎡 روليت الحظ",
            description=f"مبروك! ربحت **Gold x{amount}** 🥇\nذهبك الحالي: **{new_gold}**",
            color=SUCCESS_COLOR,
        )
    else:
        new_balance = update_balance(message.author.id, prize)
        embed = bank_embed(message,
            title="🎡 روليت الحظ",
            description=f"مبروك! ربحت **{format_amount(prize)}** 💵\nرصيدك الحالي: **{format_amount(new_balance)}**",
            color=SUCCESS_COLOR,
        )

    try:
        avatar_bytes = await message.author.display_avatar.read()
        wheel_file = render_roulette_wheel(labels, winning_index, avatar_bytes)
        embed.set_image(url="attachment://roulette.gif")
        await send_bank_reply(message, embed=embed, file=wheel_file, mention_author=False)
    except Exception as e:
        print(f"⚠️ تعذّر رسم عجلة الروليت: {e}")
        await send_bank_reply(message, embed=embed, mention_author=False)


# --- نهب / حماية ---
async def bank_cmd_rob(message: discord.Message):
    if not await _check_cooldown(message, "نهب"):
        return
    set_cooldown(message.author.id, "نهب")

    db = load_db()
    economy = db.get("economy", {})
    protection = db.get("protection", {})
    now = datetime.now(timezone.utc).timestamp()
    ranked = sorted(economy.items(), key=lambda kv: kv[1], reverse=True)

    target_id = None
    for uid, bal in ranked:
        if uid == str(message.author.id):
            continue
        if bal <= 0:
            continue
        if protection.get(uid, 0) > now:
            continue
        target_id = uid
        break

    if not target_id:
        embed = bank_embed(message,
            title="🕵️ ما فيه هدف مناسب",
            description="كل الأعضاء إما محميين أو رصيدهم صفر حاليًا.",
            color=DANGER_COLOR,
        )
        return await send_bank_reply(message, embed=embed, mention_author=False)

    target_member = message.guild.get_member(int(target_id)) if message.guild else None
    target_mention = target_member.mention if target_member else f"<@{target_id}>"

    if random.random() < ROB_SUCCESS_CHANCE:
        target_balance = economy.get(target_id, 0)
        stolen = max(1, int(target_balance * ROB_PERCENT))
        update_balance(int(target_id), -stolen)
        new_balance = update_balance(message.author.id, stolen)
        embed = pay_card_embed(message,
            operation="تمت السرقة بنجاح !!",
            subtitle=f"نهبت {target_mention} - انتبه لحسابك يا {target_mention} لا يصيدك أحد ثاني!",
            amount_line=f"💵 {format_amount(stolen)}\nرصيدك الحالي: **{format_amount(new_balance)}**",
            color=SUCCESS_COLOR,
        )
    else:
        new_balance = update_balance(message.author.id, -ROB_FAIL_FINE)
        embed = pay_card_embed(message,
            operation="عملية خصم",
            subtitle=f"حاولت تسرق {target_mention} بس مسكوك متلبس! دفعت غرامة",
            amount_line=f"💵 {format_amount(ROB_FAIL_FINE)}\nرصيدك الحالي: **{format_amount(new_balance)}**",
            color=DANGER_COLOR,
        )
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_protection(message: discord.Message):
    remaining = is_protected(message.author.id)
    if remaining > 0:
        embed = bank_embed(message,
            title="🛡️ عندك حماية شغالة",
            description=f"باقي على انتهائها: **{format_bank_duration(remaining)}**",
            color=MAIN_COLOR,
        )
        return await send_bank_reply(message, embed=embed, mention_author=False)

    balance = get_balance(message.author.id)
    if balance < PROTECTION_COST:
        embed = bank_embed(message,
            title="❌ رصيدك ما يكفي",
            description=f"تفعيل الحماية يكلف **{format_amount(PROTECTION_COST)}** 💵",
            color=DANGER_COLOR,
        )
        return await send_bank_reply(message, embed=embed, mention_author=False)

    new_balance = update_balance(message.author.id, -PROTECTION_COST)
    set_protection(message.author.id, PROTECTION_HOURS)
    embed = bank_embed(message,
        title="🛡️ تم تفعيل الحماية",
        description=(
            f"محمي من السرقة لمدة **{PROTECTION_HOURS} ساعات** ⏳\n"
            f"رصيدك الحالي: **{format_amount(new_balance)}**"
        ),
        color=SUCCESS_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


# --- رهان / قمار / نرد (ضد البنك) ---
GAMBLE_OUTCOMES = [(0.0, 20), (0.5, 20), (1.5, 25), (2.0, 20), (3.0, 10), (5.0, 5)]


async def bank_cmd_bet(message: discord.Message, arg: str | None):
    if not await _check_cooldown(message, "رهان"):
        return
    balance = get_balance(message.author.id)
    amount = parse_amount_arg(arg, balance)
    if amount is None:
        return await send_bank_reply(message, embed=_ask_amount_embed(message, "رهان"), mention_author=False)
    if amount < BET_MIN_BET:
        return await send_bank_reply(message, embed=_min_bet_embed(message, BET_MIN_BET), mention_author=False)
    if amount > balance or amount <= 0:
        return await send_bank_reply(message, embed=_not_enough_embed(message, balance), mention_author=False)

    set_cooldown(message.author.id, "رهان")
    won = random.random() < 0.48
    delta = amount if won else -amount
    new_balance = update_balance(message.author.id, delta)
    embed = pay_card_embed(message,
        operation="عملية ايداع" if won else "عملية خصم",
        subtitle="ربحت الرهان 🎯" if won else "خسرت الرهان 💸",
        amount_line=f"💵 {format_amount(amount)}\nرصيدك الحالي: **{format_amount(new_balance)}**",
        color=SUCCESS_COLOR if won else DANGER_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_gamble(message: discord.Message, arg: str | None):
    if not await _check_cooldown(message, "قمار"):
        return
    balance = get_balance(message.author.id)
    amount = parse_amount_arg(arg, balance)
    if amount is None:
        return await send_bank_reply(message, embed=_ask_amount_embed(message, "قمار"), mention_author=False)
    if amount < GAMBLE_MIN_BET:
        return await send_bank_reply(message, embed=_min_bet_embed(message, GAMBLE_MIN_BET), mention_author=False)
    if amount > balance or amount <= 0:
        return await send_bank_reply(message, embed=_not_enough_embed(message, balance), mention_author=False)

    set_cooldown(message.author.id, "قمار")
    multipliers = [m for m, _ in GAMBLE_OUTCOMES]
    weights = [w for _, w in GAMBLE_OUTCOMES]
    multiplier = random.choices(multipliers, weights=weights, k=1)[0]
    profit = int(amount * multiplier) - amount
    new_balance = update_balance(message.author.id, profit)
    won = profit >= 0
    embed = pay_card_embed(message,
        operation="عملية ايداع" if won else "عملية خصم",
        subtitle=f"القمار طلع لك مضاعف x{multiplier} 🎰",
        amount_line=f"💵 {format_amount(abs(profit))}\nرصيدك الحالي: **{format_amount(new_balance)}**",
        color=SUCCESS_COLOR if won else DANGER_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_dice(message: discord.Message, arg: str | None):
    if not await _check_cooldown(message, "نرد"):
        return
    balance = get_balance(message.author.id)
    amount = parse_amount_arg(arg, balance)
    if amount is None:
        return await send_bank_reply(message, embed=_ask_amount_embed(message, "نرد"), mention_author=False)
    if amount < DICE_MIN_BET:
        return await send_bank_reply(message, embed=_min_bet_embed(message, DICE_MIN_BET), mention_author=False)
    if amount > balance or amount <= 0:
        return await send_bank_reply(message, embed=_not_enough_embed(message, balance), mention_author=False)

    set_cooldown(message.author.id, "نرد")
    player_roll = random.randint(1, 6)
    house_roll = random.randint(1, 6)
    if player_roll > house_roll:
        delta, result_text, operation, color = amount, "فزت عليّ! 🎉", "عملية ايداع", SUCCESS_COLOR
    elif player_roll < house_roll:
        delta, result_text, operation, color = -amount, "فزت عليك! 😈", "عملية خصم", DANGER_COLOR
    else:
        delta, result_text, operation, color = 0, "تعادل - رجع لك مبلغك بدون ربح أو خسارة", "بدون تغيير", MAIN_COLOR
    new_balance = update_balance(message.author.id, delta)
    embed = pay_card_embed(message,
        operation=operation,
        subtitle=f"نردك: 🎲{player_roll} | نرد البنك: 🎲{house_roll}\n{result_text}",
        amount_line=f"💵 {format_amount(abs(delta))}\nرصيدك الحالي: **{format_amount(new_balance)}**",
        color=color,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


# --- استثمار / تداول (مع شارت أداء بسيط) ---
async def bank_cmd_market(message: discord.Message, arg: str | None, game: str):
    if not await _check_cooldown(message, game):
        return
    balance = get_balance(message.author.id)
    amount = parse_amount_arg(arg, balance)
    min_bet = INVEST_MIN_BET if game == "استثمار" else TRADE_MIN_BET
    if amount is None:
        return await send_bank_reply(message, embed=_ask_amount_embed(message, game), mention_author=False)
    if amount < min_bet:
        return await send_bank_reply(message, embed=_min_bet_embed(message, min_bet), mention_author=False)
    if amount > balance or amount <= 0:
        return await send_bank_reply(message, embed=_not_enough_embed(message, balance), mention_author=False)

    set_cooldown(message.author.id, game)
    min_pct, max_pct = (INVEST_MIN_PCT, INVEST_MAX_PCT) if game == "استثمار" else (TRADE_MIN_PCT, TRADE_MAX_PCT)
    pct = random.uniform(min_pct, max_pct)
    profit = int(amount * pct)
    new_balance = update_balance(message.author.id, profit)
    history = push_bank_history(message.author.id, game, new_balance)
    won = profit >= 0

    embed = bank_embed(message,
        title=f"{'📈' if won else '📉'} {game}",
        description=(
            f"المبلغ: **{format_amount(amount)}**\n"
            f"النتيجة: {'ربحت' if won else 'خسرت'} **{format_amount(abs(profit))}** ({pct * 100:+.1f}%)\n"
            f"رصيدك الحالي: **{format_amount(new_balance)}**"
        ),
        color=SUCCESS_COLOR if won else DANGER_COLOR,
    )
    try:
        avatar_bytes = await message.author.display_avatar.read()
        delta_label = f"+{round(pct * 100)}" if won else f"{round(pct * 100)}"
        chart_file = make_growth_chart(history, won, avatar_bytes=avatar_bytes, delta_label=delta_label)
        embed.set_image(url="attachment://chart.png")
        await send_bank_reply(message, embed=embed, file=chart_file, mention_author=False)
    except Exception as e:
        print(f"⚠️ تعذّر رسم شارت {game}: {e}")
        await send_bank_reply(message, embed=embed, mention_author=False)


# --- لعبه: حجرة ورقة مقص ضد البنك ---
RPS_CHOICES = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


class RPSView(discord.ui.View):
    def __init__(self, owner: discord.Member):
        super().__init__(timeout=30)
        self.owner = owner
        for key, emoji in RPS_CHOICES.items():
            button = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.secondary)
            button.callback = self._make_callback(key)
            self.add_item(button)

    def _make_callback(self, key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await bank_interaction_card(interaction, "هذه اللعبة ليست لك", "افتح اللعبة من لوحة البنك الخاصة بك.", DANGER_COLOR)
            bot_choice = random.choice(list(RPS_CHOICES.keys()))
            if key == bot_choice:
                result_text, amount, operation, color = "تعادل 🤝", 0, "بدون تغيير", MAIN_COLOR
            elif RPS_BEATS[key] == bot_choice:
                amount = random.randint(150, 400)
                result_text, operation, color = "فزت! 🎉", "عملية ايداع", SUCCESS_COLOR
            else:
                amount = -random.randint(100, 300)
                result_text, operation, color = "خسرت 😬", "عملية خصم", DANGER_COLOR
            new_balance = update_balance(interaction.user.id, amount)
            for child in self.children:
                child.disabled = True
            embed = pay_card_embed(interaction,
                operation=operation,
                subtitle=f"اخترت {RPS_CHOICES[key]} — البنك اختار {RPS_CHOICES[bot_choice]}\n{result_text}",
                amount_line=f"💵 {format_amount(abs(amount))}\nرصيدك الحالي: **{format_amount(new_balance)}**",
                color=color,
            )
            await edit_bank_interaction_card(interaction, embed, view=self)
        return callback

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


async def bank_cmd_rps(message: discord.Message):
    view = RPSView(message.author)
    embed = bank_embed(message, title="🎮 حجرة ورقة مقص", description="اختر سلاحك 👇", color=MAIN_COLOR)
    await send_bank_reply(message, embed=embed, view=view, mention_author=False)


# --- فواكه: سلوت GIF متحرك يتوقف على النتيجة النهائية ---
FRUIT_EMOJIS = ["🍒", "🍋", "🍇", "🍉", "🍓", "⭐"]


def render_fruit_slot_gif(final_reels: list[str]) -> discord.File:
    """يرسم ماكينة فواكه متحركة؛ تتوقف البكرات بالتتابع وتبقى النتيجة النهائية ظاهرة."""
    width, height = 900, 360
    gold = (241, 196, 15)
    bg = (22, 24, 30)
    font_title = _load_bank_font(30)
    font_label = _load_bank_font(18)

    def draw_symbol(draw, cx, cy, symbol):
        if symbol == "🍒":
            draw.line((cx - 8, cy - 4, cx - 20, cy - 30), fill=(75, 190, 95), width=7)
            draw.line((cx + 8, cy - 4, cx + 22, cy - 28), fill=(75, 190, 95), width=7)
            draw.ellipse((cx - 38, cy - 6, cx - 2, cy + 30), fill=(220, 48, 62), outline=(255, 120, 130), width=3)
            draw.ellipse((cx + 2, cy - 6, cx + 38, cy + 30), fill=(220, 48, 62), outline=(255, 120, 130), width=3)
        elif symbol == "🍋":
            draw.ellipse((cx - 42, cy - 24, cx + 42, cy + 24), fill=(250, 218, 55), outline=(255, 244, 150), width=4)
            draw.ellipse((cx - 31, cy - 13, cx + 31, cy + 13), outline=(255, 240, 130), width=3)
        elif symbol == "🍇":
            for dx, dy in [(-20,-15),(0,-20),(20,-15),(-30,5),(-10,5),(10,5),(30,5),(0,25)]:
                draw.ellipse((cx+dx-13, cy+dy-13, cx+dx+13, cy+dy+13), fill=(133, 82, 210), outline=(196, 155, 255), width=2)
            draw.line((cx, cy-35, cx+10, cy-49), fill=(90, 190, 100), width=6)
        elif symbol == "🍉":
            draw.pieslice((cx-48,cy-42,cx+48,cy+48), 0, 180, fill=(62,180,85), outline=(145,230,130), width=3)
            draw.pieslice((cx-38,cy-32,cx+38,cy+38), 0, 180, fill=(240,70,82))
            for dx,dy in [(-20,-5),(0,2),(20,-5)]: draw.ellipse((cx+dx-3,cy+dy-3,cx+dx+3,cy+dy+3),fill=(35,35,40))
        elif symbol == "🍓":
            draw.polygon([(cx,cy+38),(cx-36,cy-8),(cx-28,cy-28),(cx,cy-35),(cx+28,cy-28),(cx+36,cy-8)], fill=(230,45,75), outline=(255,120,140))
            draw.polygon([(cx-24,cy-25),(cx-5,cy-42),(cx+5,cy-25),(cx+25,cy-38),(cx+22,cy-18)], fill=(70,190,85))
            for dx,dy in [(-15,-5),(0,-10),(15,-5),(-8,12),(10,12),(0,26)]: draw.ellipse((cx+dx-2,cy+dy-2,cx+dx+2,cy+dy+2),fill=(255,220,90))
        else:
            pts=[]
            for i in range(10):
                a=-math.pi/2+i*math.pi/5
                r=42 if i%2==0 else 19
                pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r))
            draw.polygon(pts,fill=(255,205,45),outline=(255,245,155))

    def make_frame(symbols, highlight=False):
        image=Image.new("RGB",(width,height),bg)
        d=ImageDraw.Draw(image)
        d.rounded_rectangle((12,12,width-12,height-12),radius=26,fill=(32,35,43),outline=gold,width=5)
        d.text((width//2,35),"3FH FRUIT SLOTS",font=font_title,fill=gold,anchor="mm")
        labels=["CHERRY","LEMON","GRAPES","MELON","BERRY","STAR"]
        for i,symbol in enumerate(symbols):
            x=110+i*0 if False else 180+i*270
            box=(x-105,82,x+105,300)
            d.rounded_rectangle(box,radius=22,fill=(245,245,238),outline=gold if highlight else (85,91,103),width=5)
            draw_symbol(d,x,180,symbol)
            d.text((x,265),labels[FRUIT_EMOJIS.index(symbol)],font=font_label,fill=(40,43,50),anchor="mm")
        return image

    frames=[]; durations=[]
    for i in range(16):
        reels=[]
        for j in range(3):
            if i >= (8 + j*3):
                reels.append(final_reels[j])
            else:
                reels.append(random.choice(FRUIT_EMOJIS))
        frames.append(make_frame(reels, highlight=(i==15)))
        durations.append(75 if i<10 else 130)
    for _ in range(3):
        frames.append(make_frame(final_reels, highlight=True)); durations.append(700)
    buffer=io.BytesIO()
    frames[0].save(buffer,format="GIF",save_all=True,append_images=frames[1:],duration=durations,optimize=False)
    buffer.seek(0)
    return discord.File(buffer,filename="fruits.gif")


async def bank_cmd_fruits(message: discord.Message):
    final_reels = [random.choice(FRUIT_EMOJIS) for _ in range(3)]
    await asyncio.sleep(0.45)
    line = " | ".join(final_reels)
    if final_reels[0] == final_reels[1] == final_reels[2]:
        amount, result_text, operation, color = 1500, "ثلاثي مطابق!", "عملية إيداع", SUCCESS_COLOR
    elif len(set(final_reels)) == 2:
        amount, result_text, operation, color = 300, "ثنائي متطابق", "عملية إيداع", SUCCESS_COLOR
    else:
        amount, result_text, operation, color = -150, "لم يحالفك الحظ هذه المرة", "عملية خصم", DANGER_COLOR
    new_balance = update_balance(message.author.id, amount)
    embed = pay_card_embed(message, operation=operation,
        subtitle=f"الفواكه: {line} — {result_text}",
        amount_line=f"المبلغ: {format_amount(abs(amount))} | رصيدك: {format_amount(new_balance)}",
        color=color)
    fruit_file = render_fruit_slot_gif(final_reels)
    await send_bank_reply(message, embed=embed, file=fruit_file, mention_author=False)


# --- لون: نفس فكرة الصورة المرجعية - شبكة مربعات ملونة + 25 محاولة يومية ---
COLOR_CHOICES = {
    "red": "🟥",
    "blue": "🟦",
    "orange": "🟧",
    "purple": "🟪",
    "green": "🟩",
}
COLOR_MAX_ATTEMPTS = 25
COLOR_RESET_HOURS = 24


def get_color_attempts(user_id: int) -> dict:
    db = load_db()
    uid = str(user_id)
    now = datetime.now(timezone.utc).timestamp()
    rec = db.setdefault("color_game", {}).get(uid)
    if not rec or rec.get("reset_at", 0) <= now:
        rec = {"count": COLOR_MAX_ATTEMPTS, "reset_at": now + COLOR_RESET_HOURS * 3600}
        db["color_game"][uid] = rec
        save_db(db)
    return rec


def consume_color_attempt(user_id: int) -> int:
    db = load_db()
    uid = str(user_id)
    now = datetime.now(timezone.utc).timestamp()
    rec = db.setdefault("color_game", {}).get(uid)
    if not rec or rec.get("reset_at", 0) <= now:
        rec = {"count": COLOR_MAX_ATTEMPTS, "reset_at": now + COLOR_RESET_HOURS * 3600}
    rec["count"] = max(0, rec["count"] - 1)
    db["color_game"][uid] = rec
    save_db(db)
    return rec["count"]


def render_color_grid(rows: int = 8, cols: int = 9) -> str:
    squares = list(COLOR_CHOICES.values())
    return "\n".join("".join(random.choice(squares) for _ in range(cols)) for _ in range(rows))


class ColorGameView(discord.ui.View):
    def __init__(self, owner: discord.Member, target_key: str):
        super().__init__(timeout=60)
        self.owner = owner
        self.target_key = target_key
        for key, emoji in COLOR_CHOICES.items():
            button = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.secondary)
            button.callback = self._make_callback(key)
            self.add_item(button)

    def _make_callback(self, key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await bank_interaction_card(interaction, "هذه اللعبة ليست لك", "افتح اللعبة من لوحة البنك الخاصة بك.", DANGER_COLOR)
            remaining = consume_color_attempt(interaction.user.id)
            for child in self.children:
                child.disabled = True
            if key == self.target_key:
                amount = random.randint(500, 1500)
                new_balance = update_balance(interaction.user.id, amount)
                embed = pay_card_embed(interaction,
                    operation="عملية ايداع",
                    subtitle="🎯 صح! اخترت اللون الصحيح",
                    amount_line=f"💵 {format_amount(amount)}\nرصيدك الحالي: **{format_amount(new_balance)}**",
                    color=SUCCESS_COLOR,
                )
            else:
                target_emoji = COLOR_CHOICES[self.target_key]
                embed = bank_embed(interaction,
                    title="🎨 خمن اللون",
                    description=f"❌ غلط، اللون الصح كان {target_emoji}\nالمحاولات المتبقية: **{remaining}/{COLOR_MAX_ATTEMPTS}**",
                    color=DANGER_COLOR,
                )
            await edit_bank_interaction_card(interaction, embed, view=self)
        return callback

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


async def bank_cmd_colors(message: discord.Message):
    rec = get_color_attempts(message.author.id)
    if rec["count"] <= 0:
        remaining_time = rec["reset_at"] - datetime.now(timezone.utc).timestamp()
        embed = bank_embed(message,
            title="🎨 خمن اللون",
            description=f"خلصت محاولاتك اليوم ({COLOR_MAX_ATTEMPTS}/{COLOR_MAX_ATTEMPTS})\nترجع لك بعد {format_bank_duration(remaining_time)}",
            color=DANGER_COLOR,
        )
        return await send_bank_reply(message, embed=embed, mention_author=False)

    target_key = random.choice(list(COLOR_CHOICES.keys()))
    grid = render_color_grid()
    view = ColorGameView(message.author, target_key)
    embed = bank_embed(message,
        title="🎨 خمن اللون",
        description=f"{grid}\n\nالمحاولات: **{COLOR_MAX_ATTEMPTS - rec['count']}/{COLOR_MAX_ATTEMPTS}**\nاختر لون 👇",
        color=MAIN_COLOR,
    )
    await send_bank_reply(message, embed=embed, view=view, mention_author=False)



# --- تسريع (يشيل كل الكولداونات مقابل ذهب) ---
async def bank_cmd_speedup(message: discord.Message):
    gold = get_gold(message.author.id)
    if gold < SPEEDUP_GOLD_COST:
        embed = bank_embed(message,
            title="❌ ذهبك ما يكفي",
            description=f"تحتاج **Gold x{SPEEDUP_GOLD_COST}** لتفعيل التسريع (عندك **{gold}**).",
            color=DANGER_COLOR,
        )
        return await send_bank_reply(message, embed=embed, mention_author=False)

    new_gold = update_gold(message.author.id, -SPEEDUP_GOLD_COST)
    clear_cooldowns(message.author.id)
    embed = bank_embed(message,
        title="⚡ عملية تسريع",
        description=(
            f"تم خصم **Gold x{SPEEDUP_GOLD_COST}** من ممتلكاتك من الذهب\n"
            f"تم إزالة جميع الأوقات من حسابك ✅\n"
            f"ذهبك الحالي: **{new_gold}**"
        ),
        color=SUCCESS_COLOR,
    )
    await send_bank_reply(message, embed=embed, mention_author=False)


# --- المتجر: شراء / بيع ---
class PropertyBuyView(discord.ui.View):
    def __init__(self, owner: discord.Member):
        super().__init__(timeout=120)
        self.owner = owner
        for key, info in PROPERTY_CATALOG.items():
            self.add_item(self._make_buy_button(key, info))

        gold_button = discord.ui.Button(label="🥇 Gold x5 (1000)", style=discord.ButtonStyle.secondary)
        gold_button.callback = self._buy_gold
        self.add_item(gold_button)

        stock_button = discord.ui.Button(label=f"📈 سهم ({format_amount(current_stock_price())})", style=discord.ButtonStyle.secondary)
        stock_button.callback = self._buy_stock
        self.add_item(stock_button)

    def _make_buy_button(self, key: str, info: dict) -> discord.ui.Button:
        button = discord.ui.Button(
            label=f"{info['emoji']} {info['name']} ({format_amount(info['price'])})",
            style=discord.ButtonStyle.primary,
        )

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await bank_interaction_card(interaction, "تعذر تنفيذ العملية", "هذه الأزرار ليست متجرك.", DANGER_COLOR)
            balance = get_balance(interaction.user.id)
            if balance < info["price"]:
                return await bank_interaction_card(interaction, "رصيد غير كافٍ", "رصيدك الحالي لا يكفي لإتمام العملية.", DANGER_COLOR)
            new_balance = update_balance(interaction.user.id, -info["price"])
            count = update_property(interaction.user.id, key, 1)
            await bank_interaction_card(interaction, "تم الشراء بنجاح",
                f"تم شراء {info['emoji']} {info['name']}\nالكمية: {count}\nرصيدك الحالي: {format_amount(new_balance)}", SUCCESS_COLOR)

        button.callback = callback
        return button

    async def _buy_gold(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner.id:
            return await bank_interaction_card(interaction, "تعذر تنفيذ العملية", "هذه الأزرار ليست متجرك.", DANGER_COLOR)
        price = 1000
        balance = get_balance(interaction.user.id)
        if balance < price:
            return await bank_interaction_card(interaction, "رصيد غير كافٍ", "رصيدك الحالي لا يكفي لإتمام العملية.", DANGER_COLOR)
        update_balance(interaction.user.id, -price)
        new_gold = update_gold(interaction.user.id, 5)
        await bank_interaction_card(interaction, "تم شراء الذهب", f"اشتريت Gold x5\nالذهب الحالي: {new_gold}", SUCCESS_COLOR)

    async def _buy_stock(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner.id:
            return await bank_interaction_card(interaction, "تعذر تنفيذ العملية", "هذه الأزرار ليست متجرك.", DANGER_COLOR)
        balance = get_balance(interaction.user.id)
        price = current_stock_price()
        if balance < price:
            return await bank_interaction_card(interaction, "رصيد غير كافٍ", f"رصيدك لا يكفي لشراء السهم. السعر الحالي: {format_amount(price)}", DANGER_COLOR)
        update_balance(interaction.user.id, -price)
        count = update_property(interaction.user.id, "stocks", 1)
        await bank_interaction_card(interaction, "تم شراء السهم", f"سعر السهم: {format_amount(price)}\nعدد الأسهم: {count}\nرصيدك الحالي: {format_amount(get_balance(interaction.user.id))}", SUCCESS_COLOR)


class PropertySellView(discord.ui.View):
    def __init__(self, owner: discord.Member):
        super().__init__(timeout=120)
        self.owner = owner
        for key, info in PROPERTY_CATALOG.items():
            self.add_item(self._make_sell_button(key, info))

        sell_stock_price = current_stock_price()
        stock_button = discord.ui.Button(label=f"📉 بيع سهم ({format_amount(sell_stock_price)})", style=discord.ButtonStyle.secondary)
        stock_button.callback = self._sell_stock
        self.add_item(stock_button)

    def _make_sell_button(self, key: str, info: dict) -> discord.ui.Button:
        sell_price = int(info["price"] * PROPERTY_SELL_RATIO)
        button = discord.ui.Button(
            label=f"{info['emoji']} بيع {info['name']} ({format_amount(sell_price)})",
            style=discord.ButtonStyle.danger,
        )

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await bank_interaction_card(interaction, "تعذر تنفيذ العملية", "هذه الأزرار ليست متجرك.", DANGER_COLOR)
            props = get_properties(interaction.user.id)
            if props.get(key, 0) <= 0:
                return await bank_interaction_card(interaction, "تعذر البيع", "ما عندك وحدة من هذا الغرض تبيعها.", DANGER_COLOR)
            update_property(interaction.user.id, key, -1)
            new_balance = update_balance(interaction.user.id, sell_price)
            await bank_interaction_card(interaction, "تم البيع بنجاح",
                f"تم بيع {info['emoji']} {info['name']}\nالمبلغ: {format_amount(sell_price)}\nرصيدك الحالي: {format_amount(new_balance)}", SUCCESS_COLOR)

        button.callback = callback
        return button

    async def _sell_stock(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner.id:
            return await bank_interaction_card(interaction, "تعذر تنفيذ العملية", "هذه الأزرار ليست متجرك.", DANGER_COLOR)
        props = get_properties(interaction.user.id)
        if props.get("stocks", 0) <= 0:
            return await bank_interaction_card(interaction, "تعذر البيع", "ما عندك أسهم تبيعها.", DANGER_COLOR)
        update_property(interaction.user.id, "stocks", -1)
        sell_price = current_stock_price()
        new_balance = update_balance(interaction.user.id, sell_price)
        await bank_interaction_card(interaction, "تم بيع السهم",
            f"المبلغ: {format_amount(sell_price)}\nرصيدك الحالي: {format_amount(new_balance)}", SUCCESS_COLOR)


async def bank_cmd_stock_market(message: discord.Message):
    market = get_stock_market()
    price = int(market.get("stock_price", STOCK_PRICE))
    change = float(market.get("last_change_pct", 0.0))
    history = market.get("history", [price])[-8:]
    arrow = "📈" if change > 0 else "📉" if change < 0 else "➖"
    spark = " → ".join(format_amount(int(value)) for value in history)
    embed = bank_embed(
        message,
        title="📊 3FH BANK — سوق الأسهم الافتراضي",
        description=(
            f"**سعر السهم الحالي:** {format_amount(price)} 💵\n"
            f"**آخر تغيّر:** {arrow} {change:+.2f}%\n"
            f"**حركة الأسعار الأخيرة:**\n`{spark}`\n\n"
            "يتحدّث السعر تلقائيًا كل 5 دقائق، ويرتفع أو ينخفض ضمن نطاق افتراضي.\n"
            "استخدم `شراء` لشراء سهم، و`بيع` لبيعه بسعر السوق الحالي.\n"
            "*كل الأرصدة افتراضية ولا قيمة لها خارج اللعبة.*"
        ),
        color=SUCCESS_COLOR if change > 0 else DANGER_COLOR if change < 0 else MAIN_COLOR,
    )
    embed.set_thumbnail(url=message.author.display_avatar.url)
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_buy(message: discord.Message):
    view = PropertyBuyView(message.author)
    embed = bank_embed(message,title="🛒 المتجر - شراء", description="اختر شي تشتريه من الأزرار تحت 👇", color=MAIN_COLOR)
    await send_bank_reply(message, embed=embed, view=view, mention_author=False)


async def bank_cmd_sell(message: discord.Message):
    view = PropertySellView(message.author)
    embed = bank_embed(message,title="💰 المتجر - بيع", description="اختر شي تبيعه من الأزرار تحت 👇", color=MAIN_COLOR)
    await send_bank_reply(message, embed=embed, view=view, mention_author=False)


# --- ممتلكات / وقت / أغنى ---
async def bank_cmd_properties(message: discord.Message):
    props = get_properties(message.author.id)
    gold = get_gold(message.author.id)
    worth = net_worth(message.author.id)
    lines = [f"{info['emoji']} {info['name']}: **{props.get(key, 0)}**" for key, info in PROPERTY_CATALOG.items()]
    lines.append(f"🥇 ذهب: **{gold}**")
    lines.append(f"📈 أسهم: **{props.get('stocks', 0)}**")
    embed = bank_embed(message,title=f"💼 ممتلكات {message.author.display_name}", description="\n".join(lines), color=MAIN_COLOR)
    embed.add_field(name="💰 إجمالي الثروة", value=f"**{format_amount(worth)}**", inline=False)
    embed.set_thumbnail(url=message.author.display_avatar.url)
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_status(message: discord.Message):
    lines = []
    for action in BANK_STATUS_ORDER:
        remaining = get_cooldown_remaining(message.author.id, action)
        if remaining > 0:
            lines.append(f"⏳ {action} : باقي {format_bank_duration(remaining)}")
        else:
            lines.append(f"🟢 {action} : جاهز للعب")
    embed = bank_embed(message,title="⏱️ حالة أوامر البنك", description="\n".join(lines), color=MAIN_COLOR)
    await send_bank_reply(message, embed=embed, mention_author=False)


async def bank_cmd_richest(message: discord.Message):
    db = load_db()
    economy = db.get("economy", {})
    if not economy:
        embed = bank_embed(message,title="🏆 أغنى الأعضاء", description="ما فيه بيانات كافية بعد.", color=MAIN_COLOR)
        return await send_bank_reply(message, embed=embed, mention_author=False)

    ranked = sorted(((uid, net_worth(int(uid))) for uid in economy.keys()), key=lambda kv: kv[1], reverse=True)[:10]
    lines = []
    for i, (uid, worth) in enumerate(ranked, start=1):
        member = message.guild.get_member(int(uid)) if message.guild else None
        name = member.mention if member else f"<@{uid}>"
        lines.append(f"#{i} {name} — **{format_amount(worth)}** 💵")
    embed = bank_embed(message,title="🏆 قائمة أغنى الأعضاء بالسيرفر", description="\n".join(lines), color=WELCOME_COLOR)
    await send_bank_reply(message, embed=embed, mention_author=False)


BANK_HELP_LINES = [
    ("بنك", "فتح لوحة البنك المصورة التفاعلية بالأزرار"),
    ("تحويل @عضو مبلغ", "تحويل رصيد افتراضي إلى عضو وتظهر بطاقة نجاح بالصورة"),
    ("راتب", "استلام راتبك (كل 24 ساعة، يتحدد حسب رتبتك)"),
    ("بخشيش", "بخشيش عشوائي صغير"),
    ("حظ", "جرب حظك - ربح أو خسارة صغيرة"),
    ("روليت", "عجلة حظ متحركة فيها جوائز كاش وذهب"),
    ("نهب", "حاول تسرق أغنى عضو متاح حاليًا"),
    ("حماية", "فعّل حماية 5 ساعات من السرقة"),
    ("رهان <مبلغ/نص/كامل>", "لعبة رصيد افتراضي ضد البنك - بدون أموال حقيقية"),
    ("قمار <مبلغ/نص/كامل>", "لعبة رصيد افتراضي بمضاعف عشوائي - بدون أموال حقيقية"),
    ("نرد <مبلغ/نص/كامل>", "نرد ضد البنك"),
    ("استثمار <مبلغ/نص/كامل>", "استثمر بمخاطرة أقل + شارت أداء"),
    ("تداول <مبلغ/نص/كامل>", "تداول بمخاطرة أعلى + شارت أداء"),
    ("لعبه", "حجرة ورقة مقص ضد البنك"),
    ("فواكه", "عجلة سلوت فواكه"),
    ("لون", "خمن اللون (25 محاولة يوميًا)"),
    ("تسريع", f"يشيل كل الكولداونات مقابل Gold x{SPEEDUP_GOLD_COST}"),
    ("شراء / بيع", "متجر الممتلكات والأسهم والذهب"),
    ("سوق", "عرض سعر السهم المتغير وحركة السوق كل 5 دقائق"),
    ("ممتلكات", "عرض ممتلكاتك وإجمالي ثروتك"),
    ("وقت", "حالة جاهزية كل الأوامر"),
    ("اغنى", "أغنى 10 أعضاء بالسيرفر"),
    ("اوامر", "عرض هذي القائمة"),
]


async def bank_cmd_help(message: discord.Message):
    lines = [f"**{cmd}** — {desc}" for cmd, desc in BANK_HELP_LINES]
    embed = bank_embed(message, title="📜 أوامر البنك المتاحة", description="\n".join(lines), color=MAIN_COLOR)
    await send_bank_reply(message, embed=embed, mention_author=False)


async def handle_bank_text_command(message: discord.Message) -> bool:
    """يفحص هل الرسالة أمر بنك نصي (بدون سلاش)، ولو كذا ينفذه ويرجع True.
    غير كذا يرجع False فورًا بدون أي تأثير على باقي أنظمة البوت."""
    content = message.content.strip()
    if not content:
        return False

    parts = content.split(maxsplit=1)
    keyword = parts[0].strip()
    arg = parts[1].strip() if len(parts) > 1 else None

    if keyword not in BANK_KEYWORDS:
        return False

    if keyword == "بنك":
        await bank_cmd_panel(message)
    elif keyword == "تحويل":
        await bank_cmd_transfer(message, arg)
    elif keyword == "رصيدي":
        await bank_cmd_balance(message)
    elif keyword == "راتب":
        await bank_cmd_salary(message)
    elif keyword == "بخشيش":
        await bank_cmd_tip(message)
    elif keyword == "حظ":
        await bank_cmd_luck(message)
    elif keyword == "روليت":
        await bank_cmd_roulette(message)
    elif keyword == "نهب":
        await bank_cmd_rob(message)
    elif keyword == "حماية":
        await bank_cmd_protection(message)
    elif keyword == "رهان":
        await bank_cmd_bet(message, arg)
    elif keyword == "قمار":
        await bank_cmd_gamble(message, arg)
    elif keyword == "نرد":
        await bank_cmd_dice(message, arg)
    elif keyword in ("استثمار", "تداول"):
        await bank_cmd_market(message, arg, keyword)
    elif keyword == "لعبه":
        await bank_cmd_rps(message)
    elif keyword == "فواكه":
        await bank_cmd_fruits(message)
    elif keyword == "لون":
        await bank_cmd_colors(message)
    elif keyword == "تسريع":
        await bank_cmd_speedup(message)
    elif keyword == "بيع":
        await bank_cmd_sell(message)
    elif keyword == "شراء":
        await bank_cmd_buy(message)
    elif keyword == "سوق":
        await bank_cmd_stock_market(message)
    elif keyword == "ممتلكات":
        await bank_cmd_properties(message)
    elif keyword == "وقت":
        await bank_cmd_status(message)
    elif keyword == "اغنى":
        await bank_cmd_richest(message)
    elif keyword == "اوامر":
        await bank_cmd_help(message)

    return True


# =====================================================================
#                     🧩  الأوامر الأساسية (Slash Commands)
# =====================================================================

@bot.tree.command(name="set_welcome_template", description="رفع قالب بطاقة الترحيب (يحتوي دائرة فاضية لصورة العضو) - للإدارة فقط")
@app_commands.describe(image="صورة القالب الجاهزة (بدون صورة عضو - البوت يضيفها تلقائيًا)")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_template(interaction: discord.Interaction, image: discord.Attachment):
    if not (image.content_type and image.content_type.startswith("image/")):
        return await interaction.response.send_message("❌ الملف اللي رفعته مو صورة. ارفع ملف PNG أو JPG.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    ext = os.path.splitext(image.filename)[1] or ".png"
    save_path = os.path.join(BANNERS_DIR, f"welcome_template{ext}")

    try:
        for old_file in os.listdir(BANNERS_DIR):
            if old_file.startswith("welcome_template"):
                os.remove(os.path.join(BANNERS_DIR, old_file))
        await image.save(save_path)
    except Exception as e:
        return await interaction.followup.send(f"❌ حدث خطأ أثناء حفظ الصورة: {e}", ephemeral=True)

    db = load_db()
    db["settings"]["welcome_template_path"] = save_path
    save_db(db)

    await interaction.followup.send(
        "✅ تم رفع قالب الترحيب بنجاح!\n"
        "جرب أمر `/test_welcome` عشان تشوف شكل البطاقة النهائية، وتحكم بمكان صورة العضو واسمه بأمر `/set_welcome_position`.",
        ephemeral=True,
    )


@bot.tree.command(name="test_welcome", description="معاينة بطاقة الترحيب باستخدام حسابك الحالي (للإدارة فقط)")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    db = load_db()
    template_path = db.get("settings", {}).get("welcome_template_path")
    if not template_path or not os.path.exists(template_path):
        return await interaction.response.send_message(
            "❌ ما فيه قالب ترحيب مرفوع بعد. ارفعه أول بأمر `/set_welcome_template`.", ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)
    try:
        card_file = await generate_welcome_card(template_path, interaction.user)
        await interaction.followup.send(content="📋 هذي معاينة بطاقة الترحيب:", file=card_file, ephemeral=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"❌ صار خطأ أثناء توليد البطاقة: {e}", ephemeral=True)


@bot.tree.command(name="set_welcome_position", description="تحكم بمكان صورة العضو واسمه فوق قالب الترحيب - للإدارة فقط")
@app_commands.describe(
    avatar_x="الإحداثية الأفقية (X) لمنتصف صورة العضو",
    avatar_y="الإحداثية الرأسية (Y) لمنتصف صورة العضو",
    avatar_size="قطر صورة العضو بالبكسل",
    text_x="الإحداثية الأفقية (X) لبداية اسم العضو",
    text_y="الإحداثية الرأسية (Y) لبداية اسم العضو",
    text_size="حجم خط اسم العضو",
    text_color="لون خط اسم العضو (كود Hex مثل #FFFFFF)",
)
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_position(
    interaction: discord.Interaction,
    avatar_x: int = None,
    avatar_y: int = None,
    avatar_size: int = None,
    text_x: int = None,
    text_y: int = None,
    text_size: int = None,
    text_color: str = None,
):
    db = load_db()
    position = {**DEFAULT_WELCOME_POSITION, **db["settings"].get("welcome_position", {})}

    if avatar_x is not None:
        position["avatar_x"] = avatar_x
    if avatar_y is not None:
        position["avatar_y"] = avatar_y
    if avatar_size is not None:
        position["avatar_size"] = max(1, avatar_size)
    if text_x is not None:
        position["text_x"] = text_x
    if text_y is not None:
        position["text_y"] = text_y
    if text_size is not None:
        position["text_size"] = max(1, text_size)
    if text_color is not None:
        if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", text_color):
            return await interaction.response.send_message(
                "❌ صيغة اللون غير صحيحة. استخدم كود Hex مثل `#FFFFFF`.", ephemeral=True
            )
        position["text_color"] = text_color if text_color.startswith("#") else f"#{text_color}"

    db["settings"]["welcome_position"] = position
    save_db(db)

    summary = (
        f"📍 صورة العضو: X={position['avatar_x']} | Y={position['avatar_y']} | القطر={position['avatar_size']}\n"
        f"✏️ اسم العضو: X={position['text_x']} | Y={position['text_y']} | الحجم={position['text_size']} | اللون={position['text_color']}"
    )
    await interaction.response.send_message(
        f"✅ تم تحديث إعدادات بطاقة الترحيب:\n{summary}\n\nجرب `/test_welcome` عشان تعاين النتيجة.",
        ephemeral=True,
    )


class ConfirmClearAllView(discord.ui.View):
    """فيو تأكيد لعملية خطيرة: مسح رسائل من كل رومات السيرفر دفعة وحدة."""

    def __init__(self, amount: int):
        super().__init__(timeout=60)
        self.amount = amount

    @discord.ui.button(label="نعم، امسح كل الرومات", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🗑️ جاري المسح من كل الرومات... قد يستغرق وقت حسب عدد الرسائل والرومات.",
            embed=None, view=self,
        )

        total_deleted = 0
        failed_channels = []
        for channel in interaction.guild.text_channels:
            try:
                deleted = await channel.purge(limit=self.amount)
                total_deleted += len(deleted)
            except discord.Forbidden:
                failed_channels.append(channel.mention)
            except Exception as e:
                print(f"❌ خطأ أثناء مسح روم {channel.name}: {e}")
                failed_channels.append(channel.mention)

        summary = f"✅ تم حذف **{total_deleted}** رسالة إجمالاً من رومات السيرفر."
        if failed_channels:
            shown = ", ".join(failed_channels[:10])
            extra = " وغيرها..." if len(failed_channels) > 10 else ""
            summary += f"\n⚠️ تعذر الحذف من: {shown}{extra}"

        await interaction.followup.send(summary, ephemeral=True)

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="تم إلغاء عملية المسح.", embed=None, view=self)


@bot.tree.command(name="clear", description="حذف عدد من الرسائل - بهذا الروم أو بكل رومات السيرفر (للإدارة فقط)")
@app_commands.describe(
    amount="عدد الرسائل المطلوب حذفها من كل روم (أقصى حد 1000)",
    all_channels="امسح من كل رومات السيرفر بدل هذا الروم بس (خطير - يحتاج تأكيد)",
)
@app_commands.checks.has_permissions(administrator=True)
async def clear(interaction: discord.Interaction, amount: int, all_channels: bool = False):
    if amount <= 0:
        return await interaction.response.send_message("❌ العدد لازم يكون أكبر من صفر.", ephemeral=True)

    if amount > 1000:
        amount = 1000  # أقصى حد مسموح بالأمر

    if all_channels:
        warning_embed = discord.Embed(
            title="⚠️ تأكيد المسح الجماعي",
            description=(
                f"بتحذف حتى **{amount}** رسالة من **كل رومات السيرفر** دفعة وحدة.\n"
                "هذا الإجراء لا يمكن التراجع عنه. هل أنت متأكد؟"
            ),
            color=DANGER_COLOR,
        )
        return await interaction.response.send_message(
            embed=warning_embed, view=ConfirmClearAllView(amount), ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ تم حذف {len(deleted)} رسالة من هذا الروم.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ البوت لا يملك صلاحية `Manage Messages` بهذا الروم.", ephemeral=True
        )
    except Exception as e:
        print(f"❌ خطأ أثناء مسح الرسائل: {e}")
        await interaction.followup.send(f"❌ حدث خطأ أثناء الحذف: {e}", ephemeral=True)




@bot.tree.command(name="add_auto_reply", description="إضافة رد آلي جديد - إذا كتب أحد الكلمة المحددة يرد البوت تلقائيًا (للإدارة فقط)")
@app_commands.describe(
    trigger="الكلمة أو الجملة اللي تشغّل الرد (يجب تطابق تام)",
    response="الرد اللي يرسله البوت",
    role="اختياري: خصص الرد لهذي الرتبة بس - لو ما اخترت رتبة يشتغل الرد للجميع",
)
@app_commands.checks.has_permissions(administrator=True)
async def add_auto_reply(interaction: discord.Interaction, trigger: str, response: str, role: discord.Role = None):
    db = load_db()
    db["auto_replies"][trigger] = {"response": response, "role_id": role.id if role else None}
    save_db(db)
    role_line = f"\n🎯 مخصص لرتبة: {role.mention}" if role else "\n🎯 يشتغل لجميع الأعضاء"
    await interaction.response.send_message(
        f"✅ تم إضافة الرد الآلي:\nلو حد كتب: `{trigger}`\nيرد البوت: {response}{role_line}", ephemeral=True
    )


@bot.tree.command(name="remove_auto_reply", description="حذف رد آلي مخصص (للإدارة فقط)")
@app_commands.describe(trigger="الكلمة أو الجملة اللي تبي تحذف الرد المرتبط فيها")
@app_commands.checks.has_permissions(administrator=True)
async def remove_auto_reply(interaction: discord.Interaction, trigger: str):
    db = load_db()
    if trigger not in db["auto_replies"]:
        return await interaction.response.send_message(f"⚠️ ما فيه رد آلي مسجل بهذا النص: `{trigger}`", ephemeral=True)
    del db["auto_replies"][trigger]
    save_db(db)
    await interaction.response.send_message(f"✅ تم حذف الرد الآلي لـ: `{trigger}`", ephemeral=True)


@bot.tree.command(name="list_auto_replies", description="عرض كل الردود الآلية المخصصة المضافة (للإدارة فقط)")
@app_commands.checks.has_permissions(administrator=True)
async def list_auto_replies(interaction: discord.Interaction):
    db = load_db()
    auto_replies = db.get("auto_replies", {})
    if not auto_replies:
        return await interaction.response.send_message("⚠️ ما فيه أي ردود آلية مخصصة مضافة بعد.", ephemeral=True)

    lines = []
    for trigger, entry in auto_replies.items():
        if isinstance(entry, str):
            response_text, role_id = entry, None
        else:
            response_text, role_id = entry.get("response", ""), entry.get("role_id")
        role_tag = ""
        if role_id:
            role_obj = interaction.guild.get_role(role_id)
            role_tag = f" 🎯`{role_obj.name if role_obj else role_id}`"
        lines.append(f"**{trigger}** ← {response_text}{role_tag}")

    embed = discord.Embed(
        title="📋 الردود الآلية المخصصة",
        description="\n".join(lines)[:4000],
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =====================================================================
#           📩  إرسال رسالة خاصة جماعية لكل أعضاء السيرفر
#   نص الرسالة يُضبط من /edit_message (اختر "رسالة الخاص الجماعية")
#   ودعوة السيرفر اختيارية تُحدَّد وقت الإرسال نفسه.
#   العملية قابلة للاستكمال: تقدمها يُحفظ بقاعدة البيانات أول بأول، فلو
#   انقطع البوت (ريديبلوي/كراش) أثناء الإرسال، يكمل تلقائياً من نفس النقطة
#   عند إعادة التشغيل بدل ما يبدأ من الصفر أو يضيع التقدم بصمت.
# =====================================================================
BROADCAST_MEDIA_DIR = os.path.join(DATA_DIR, "tmp_broadcast")


async def run_dm_broadcast():
    """يبدأ أو يكمل إرسال رسالة الخاص الجماعية حسب db['dm_broadcast_progress']."""
    db = load_db()
    progress = db.get("dm_broadcast_progress")
    if not progress:
        return

    guild = bot.get_guild(progress["guild_id"])
    if guild is None:
        # السيرفر مو موجود بكاش البوت (نادر جداً) - نلغي العملية المعلقة عشان ما تعلق للأبد
        db["dm_broadcast_progress"] = None
        save_db(db)
        return

    remaining_ids = list(progress["remaining_ids"])
    sent = progress.get("sent", 0)
    failed = progress.get("failed", 0)
    total = progress.get("total", len(remaining_ids) + sent + failed)
    text = progress["text"]
    media_path = progress.get("media_path")
    media_filename = progress.get("media_filename")
    requester_id = progress.get("requester_id")
    channel_id = progress.get("channel_id")
    is_resume = sent > 0 or failed > 0

    requester = guild.get_member(requester_id) if requester_id else None
    if requester is None and requester_id:
        requester = bot.get_user(requester_id)

    status_message = None
    if requester:
        try:
            status_message = await requester.send(
                f"📤 {'تكملة' if is_resume else 'جاري'} إرسال رسالة الخاص الجماعية"
                f"{' بعد إعادة تشغيل البوت' if is_resume else ''}... ({sent + failed} / {total})"
            )
        except Exception as e:
            print(f"⚠️ [DM Broadcast] فشل إرسال رسالة التقدم لصاحب الطلب ({requester_id}): {type(e).__name__}: {e}")

    media_bytes = None
    if media_path and os.path.exists(media_path):
        with open(media_path, "rb") as f:
            media_bytes = f.read()

    error_summary: dict[str, int] = {}
    processed_since_save = 0
    for member_id in list(remaining_ids):
        member = guild.get_member(member_id)
        if member and not member.bot:
            try:
                files = (
                    [discord.File(io.BytesIO(media_bytes), filename=media_filename)]
                    if media_bytes else []
                )
                await member.send(text, files=files)
                sent += 1
            except Exception as e:
                failed += 1
                key = f"{type(e).__name__}: {e}"
                error_summary[key] = error_summary.get(key, 0) + 1
                if error_summary[key] <= 3:  # نطبع أول 3 حالات بس من كل نوع خطأ عشان ما تفيض اللوقز
                    print(f"❌ [DM Broadcast] فشل الإرسال للعضو {member_id}: {key}")
        # لو العضو غادر السيرفر (member is None) نتجاوزه بصمت بدون ما نعده فشل

        remaining_ids.remove(member_id)
        processed_since_save += 1

        # نحفظ التقدم كل 10 أعضاء عشان لو صار انقطاع (ريديبلوي/كراش) يكمل قريب من نفس
        # النقطة بعد إعادة التشغيل، بدون ما نكتب على القرص بكل رسالة (تخفيف الحمل)
        if processed_since_save % 10 == 0 or not remaining_ids:
            db = load_db()
            db["dm_broadcast_progress"] = {
                **progress, "remaining_ids": remaining_ids,
                "sent": sent, "failed": failed, "total": total,
            }
            save_db(db)

        if status_message and (processed_since_save % 50 == 0 or not remaining_ids):
            try:
                await status_message.edit(
                    content=f"📤 جاري إرسال رسالة الخاص الجماعية... ({sent + failed} / {total})"
                )
            except Exception:
                pass

        await asyncio.sleep(1.2)  # تفادي حدود ريت-ليمت الديسكورد عند إرسال جماعي

    if error_summary:
        print("📊 [DM Broadcast] ملخص أنواع الأخطاء: " + ", ".join(f"{k} × {v}" for k, v in error_summary.items()))

    # خلصت العملية - ننظف كل شي (قاعدة البيانات + ملف الميديا المؤقت)
    db = load_db()
    db["dm_broadcast_progress"] = None
    save_db(db)
    if media_path and os.path.exists(media_path):
        try:
            os.remove(media_path)
        except Exception:
            pass

    report = (
        f"✅ خلصت! تم الإرسال لـ **{sent}** عضو.\n"
        f"❌ فشل الإرسال لـ **{failed}** عضو (خاصهم مقفول، حاظرين البوت، أو غادروا السيرفر أثناء الإرسال)."
    )
    if status_message:
        try:
            await status_message.edit(content=report)
            return
        except Exception:
            pass
    if requester:
        try:
            await requester.send(report)
            return
        except Exception:
            pass
    # لو ما قدرنا نوصل لصاحب الطلب بالخاص إطلاقاً، آخر حل نرسل بنفس الروم اللي بدأ منه الأمر
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel:
        try:
            await channel.send(report)
        except Exception:
            pass


class DMBroadcastConfirmView(discord.ui.View):
    """زر تأكيد قبل إرسال الرسالة لكل الأعضاء - لتفادي أي إرسال بالغلط."""

    def __init__(
        self,
        requester_id: int,
        members: list[discord.Member],
        text: str,
        invite_url: str | None,
        media_path: str | None = None,
        media_filename: str | None = None,
    ):
        super().__init__(timeout=60)
        self.requester_id = requester_id
        self.members = members
        self.text = text
        self.invite_url = invite_url
        self.media_path = media_path
        self.media_filename = media_filename
        self.done = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("❌ هذا التأكيد مو لك.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        # لو ما ضغط تأكيد ولا إلغاء خلال المهلة، ننظف ملف الميديا المؤقت عشان ما يتراكم بالقرص
        if self.media_path and os.path.exists(self.media_path):
            try:
                os.remove(self.media_path)
            except Exception:
                pass

    @discord.ui.button(label="✅ تأكيد الإرسال", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.done = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=(
                f"⏳ جاري الإرسال لـ {len(self.members)} عضو... "
                "راح أرسل تقرير التقدم لخاصك أنت (قد ياخذ وقت حسب عدد الأعضاء)."
            ),
            view=self,
        )

        full_text = self.text
        if self.invite_url:
            full_text = f"{full_text}\n\n🔗 دعوة السيرفر: {self.invite_url}"

        # نسجل بداية العملية بقاعدة البيانات قبل أول رسالة، عشان لو صار انقطاع
        # (ريديبلوي أو كراش) أثناء الإرسال، run_dm_broadcast تقدر تكمل من نفس النقطة
        # تلقائياً عند إعادة تشغيل البوت (شوف on_ready) بدل ما تبدأ من الصفر.
        db = load_db()
        db["dm_broadcast_progress"] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "requester_id": self.requester_id,
            "text": full_text,
            "media_path": self.media_path,
            "media_filename": self.media_filename,
            "remaining_ids": [m.id for m in self.members],
            "sent": 0,
            "failed": 0,
            "total": len(self.members),
        }
        save_db(db)

        await run_dm_broadcast()
        self.stop()

    @discord.ui.button(label="❌ إلغاء", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🚫 تم إلغاء الإرسال.", view=self)
        if self.media_path and os.path.exists(self.media_path):
            try:
                os.remove(self.media_path)
            except Exception:
                pass
        self.stop()


@bot.tree.command(
    name="send_dm_all",
    description="إرسال رسالة خاصة لكل أعضاء السيرفر (النص يُضبط من /edit_message) - للإدارة فقط",
)
@app_commands.describe(
    include_invite="هل تبي ترفق رابط دعوة للسيرفر مع الرسالة؟ (اختياري)",
    media="صورة أو فيديو اختياري يُرفق مع الرسالة لكل الأعضاء",
)
@app_commands.checks.has_permissions(administrator=True)
async def send_dm_all(interaction: discord.Interaction, include_invite: bool = False, media: discord.Attachment = None):
    await interaction.response.defer(ephemeral=True)

    if media and not (media.content_type and (media.content_type.startswith("image/") or media.content_type.startswith("video/"))):
        return await interaction.followup.send("❌ الملف اللي رفعته لازم يكون صورة أو فيديو.", ephemeral=True)

    # الحد الأقصى لحجم المرفق يعتمد على مستوى بوست السيرفر (25 ميجا عادي، ويزيد مع البوست)
    max_size = interaction.guild.filesize_limit
    if media and media.size > max_size:
        return await interaction.followup.send(
            f"❌ حجم الملف كبير جداً. الحد الأقصى المسموح بسيرفرك حالياً: **{max_size // (1024 * 1024)} ميجابايت**.",
            ephemeral=True,
        )

    text = get_custom_message("dm_broadcast", "text")

    # نتأكد إن كاش الأعضاء مكتمل قبل ما نبني القائمة، وإلا العدد يطلع أقل من العدد الحقيقي
    if not interaction.guild.chunked:
        try:
            await interaction.guild.chunk()
        except Exception as e:
            print(f"⚠️ [send_dm_all] فشل تحميل كامل كاش الأعضاء: {e}")

    members = [m for m in interaction.guild.members if not m.bot]

    if not members:
        return await interaction.followup.send("⚠️ ما فيه أعضاء بالسيرفر لإرسال الرسالة لهم.", ephemeral=True)

    invite_url = None
    if include_invite:
        # لو حاطط رابط دعوة مخصص من /edit_message نستخدمه، وإلا نسوي رابط تلقائي
        saved_invite = get_custom_message("dm_broadcast", "invite_url").strip()
        if saved_invite:
            invite_url = saved_invite
        else:
            invite_channel = (
                interaction.channel
                if interaction.channel.permissions_for(interaction.guild.me).create_instant_invite
                else None
            )
            if invite_channel is None:
                invite_channel = next(
                    (
                        ch for ch in interaction.guild.text_channels
                        if ch.permissions_for(interaction.guild.me).create_instant_invite
                    ),
                    None,
                )
            if invite_channel is None:
                return await interaction.followup.send(
                    "❌ ما قدرت أسوي رابط دعوة - البوت يحتاج صلاحية (Create Invite) بأي روم نصي.",
                    ephemeral=True,
                )
            try:
                invite = await invite_channel.create_invite(max_age=0, max_uses=0, unique=False, reason="رسالة خاصة جماعية")
                invite_url = invite.url
            except Exception as e:
                return await interaction.followup.send(f"❌ فشل إنشاء رابط الدعوة: {e}", ephemeral=True)

    media_path = None
    media_filename = None
    if media:
        os.makedirs(BROADCAST_MEDIA_DIR, exist_ok=True)
        safe_name = re.sub(r"[^\w\u0600-\u06FF.\-]", "_", media.filename)
        media_path = os.path.join(BROADCAST_MEDIA_DIR, f"{interaction.id}_{safe_name}")
        # نحفظ المرفق كملف على القرص (مو بالذاكرة بس) عشان يضل موجود ويقدر البوت
        # يكمل الإرسال منه حتى لو انقطع البوت وأعاد التشغيل قبل ما تخلص العملية
        await media.save(media_path)
        media_filename = media.filename

    preview = text if len(text) <= 800 else text[:800] + "…"
    invite_line = f"\n🔗 راح يترفق رابط دعوة: {invite_url}" if invite_url else "\n🔗 بدون رابط دعوة"
    if media_filename:
        media_kind = "🎥 فيديو" if media.content_type.startswith("video/") else "🖼️ صورة"
        media_line = f"\n{media_kind}: {media_filename}"
    else:
        media_line = "\n🖼️ بدون مرفق"
    view = DMBroadcastConfirmView(interaction.user.id, members, text, invite_url, media_path, media_filename)
    await interaction.followup.send(
        f"📩 بترسل هذي الرسالة لـ **{len(members)}** عضو بالخاص:\n\n{preview}{invite_line}{media_line}\n\n"
        "اضغط تأكيد للإرسال (العملية قد تاخذ وقت حسب عدد الأعضاء).",
        view=view,
        ephemeral=True,
    )


# =====================================================================
#        📁  حفظ ملفات/صور عامة والحصول على مسارها (للإدارة فقط)
# =====================================================================
def _safe_folder_name(name: str) -> str:
    """يحول اسم مجلد فرعي لصيغة آمنة للاستخدام كمسار (يمنع .. وحروف خطيرة)."""
    cleaned = re.sub(r"[^\w\u0600-\u06FF\-]", "_", name.strip())
    return cleaned[:50] or "misc"


@bot.tree.command(name="save_file", description="ارفع أي ملف أو صورة والبوت يحفظه ويرجعلك مساره الكامل - للإدارة فقط")
@app_commands.describe(
    file="الملف أو الصورة اللي تبي تحفظها",
    folder="اسم مجلد فرعي اختياري لتنظيم الملفات (مثال: designs) - لو تركته فاضي يحفظ بمجلد عام",
)
@app_commands.checks.has_permissions(administrator=True)
async def save_file(interaction: discord.Interaction, file: discord.Attachment, folder: str = None):
    await interaction.response.defer(ephemeral=True)

    target_dir = os.path.join(FILES_DIR, _safe_folder_name(folder)) if folder else FILES_DIR
    os.makedirs(target_dir, exist_ok=True)

    safe_name = re.sub(r"[^\w\u0600-\u06FF.\-]", "_", file.filename)
    save_path = os.path.join(target_dir, safe_name)

    # لو فيه ملف بنفس الاسم، نضيف رقم بدل ما نستبدله
    base, ext = os.path.splitext(save_path)
    counter = 1
    while os.path.exists(save_path):
        save_path = f"{base}_{counter}{ext}"
        counter += 1

    try:
        await file.save(save_path)
    except Exception as e:
        return await interaction.followup.send(f"❌ حدث خطأ أثناء حفظ الملف: {e}", ephemeral=True)

    absolute_path = os.path.abspath(save_path)
    print(f"📁 [save_file] تم حفظ ملف جديد بواسطة {interaction.user} — المسار: {absolute_path}")

    await interaction.followup.send(
        f"✅ تم حفظ الملف بنجاح!\n📁 المسار: `{save_path}`\n"
        "تقدر تستخدم هذا المسار داخل الكود (مثلاً كـ default لصورة أو بنر).\n"
        "(تم طباعة نفس المسار بالتيرمنال حق البوت كمان)",
        ephemeral=True,
    )


@bot.tree.command(name="list_files", description="عرض الملفات المحفوظة عبر /save_file مع مساراتها - للإدارة فقط")
@app_commands.describe(folder="اسم المجلد الفرعي اللي تبي تعرض ملفاته - اتركه فاضي لعرض المجلد العام")
@app_commands.checks.has_permissions(administrator=True)
async def list_files(interaction: discord.Interaction, folder: str = None):
    target_dir = os.path.join(FILES_DIR, _safe_folder_name(folder)) if folder else FILES_DIR

    if not os.path.isdir(target_dir):
        return await interaction.response.send_message("⚠️ ما فيه ملفات محفوظة بهذا المجلد.", ephemeral=True)

    entries = sorted(os.listdir(target_dir))
    if not entries:
        return await interaction.response.send_message("⚠️ المجلد فاضي، ما فيه ملفات محفوظة.", ephemeral=True)

    print(f"📁 [list_files] طلب {interaction.user} عرض ملفات مجلد: {os.path.abspath(target_dir)}")
    for name in entries:
        print(f"   - {os.path.abspath(os.path.join(target_dir, name))}")

    lines = [f"`{os.path.join(target_dir, name)}`" for name in entries]
    embed = discord.Embed(
        title=f"📁 الملفات المحفوظة{f' - {folder}' if folder else ''}",
        description="\n".join(lines)[:4000],
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="delete_file", description="حذف ملف محفوظ عبر /save_file - للإدارة فقط")
@app_commands.describe(
    filename="اسم الملف بالضبط كما يظهر بأمر /list_files (مثال: video-output-xxxx.mov)",
    folder="اسم المجلد الفرعي اللي فيه الملف - اتركه فاضي لو الملف بالمجلد العام",
)
@app_commands.checks.has_permissions(administrator=True)
async def delete_file(interaction: discord.Interaction, filename: str, folder: str = None):
    target_dir = os.path.join(FILES_DIR, _safe_folder_name(folder)) if folder else FILES_DIR
    target_dir_abs = os.path.abspath(target_dir)

    # نمنع أي محاولة للخروج من مجلد الملفات (زي ../../ بالاسم) لحماية باقي ملفات النظام
    safe_filename = os.path.basename(filename.strip())
    file_path = os.path.abspath(os.path.join(target_dir, safe_filename))

    if not file_path.startswith(target_dir_abs + os.sep) and file_path != target_dir_abs:
        return await interaction.response.send_message("❌ اسم ملف غير صالح.", ephemeral=True)

    if not os.path.isfile(file_path):
        return await interaction.response.send_message(
            f"❌ ما لقيت ملف بهذا الاسم. تأكد من الاسم بالضبط عبر `/list_files`"
            f"{f' folder:{folder}' if folder else ''}.",
            ephemeral=True,
        )

    try:
        os.remove(file_path)
    except Exception as e:
        return await interaction.response.send_message(f"❌ حدث خطأ أثناء حذف الملف: {e}", ephemeral=True)

    print(f"🗑️ [delete_file] تم حذف الملف بواسطة {interaction.user} — المسار: {file_path}")
    await interaction.response.send_message(f"✅ تم حذف الملف `{safe_filename}` بنجاح.", ephemeral=True)


@bot.tree.command(name="poll", description="إنشاء استطلاع رأي بأزرار (حتى 4 خيارات)")
@app_commands.describe(
    question="سؤال الاستطلاع",
    option1="الخيار الأول", option2="الخيار الثاني",
    option3="الخيار الثالث (اختياري)", option4="الخيار الرابع (اختياري)",
)
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str,
                option3: str = None, option4: str = None):
    options = [o for o in [option1, option2, option3, option4] if o]

    embed = discord.Embed(title=f"📊 {question}", color=MAIN_COLOR)
    for option in options:
        embed.add_field(name=option, value="لا يوجد أصوات بعد", inline=False)
    embed.set_footer(text=f"طرحه: {interaction.user}")

    view = PollView(options)
    # نبني الإمبيد الأولي بنفس شكل التصويت (0 صوت لكل خيار) عشان يكون متطابق من البداية
    initial_embed = view._build_embed(embed)
    await interaction.response.send_message(embed=initial_embed, view=view)


ATHKAR_LIST = [
    "سُبْحَانَ اللهِ وَبِحَمْدِهِ، سُبْحَانَ اللهِ الْعَظِيمِ 🤍",
    "لَا إِلَهَ إِلَّا اللهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ 🤍",
    "أَسْتَغْفِرُ اللهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ 🤍",
    "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللهِ 🤍",
    "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ 🤍",
    "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ ﷺ 🤍",
    "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ 🤍",
    "حَسْبُنَا اللهُ وَنِعْمَ الْوَكِيلُ 🤍",
    "اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ 🤍",
    "سُبْحَانَ اللهِ، وَالْحَمْدُ لِلَّهِ، وَلَا إِلَهَ إِلَّا اللهُ، وَاللهُ أَكْبَرُ 🤍",
]


@bot.tree.command(name="help", description="عرض قائمة أوامر البوت مبوّبة حسب القسم")
async def help_command(interaction: discord.Interaction):
    intro = (
        "📖 **مركز مساعدة 3FH PARTY ROYAL**\n"
        "اختر قسم من القائمة تحت عشان تشوف أوامره 👇"
    )
    await interaction.response.send_message(content=intro, view=HelpView(), ephemeral=True)


@bot.tree.command(name="athkar", description="إرسال ذِكر عشوائي")
async def athkar(interaction: discord.Interaction):
    target_channel = interaction.channel
    if ATHKAR_CHANNEL_ID:
        configured_channel = interaction.guild.get_channel(ATHKAR_CHANNEL_ID)
        if configured_channel:
            target_channel = configured_channel

    embed = discord.Embed(description=random.choice(ATHKAR_LIST), color=WELCOME_COLOR)
    await target_channel.send(embed=embed)

    if target_channel.id != interaction.channel.id:
        await interaction.response.send_message(f"✅ تم الإرسال بروم {target_channel.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("✅ تم الإرسال", ephemeral=True)


@bot.tree.command(name="set_level", description="تحديد مستوى عضو معين يدويًا - للإدارة فقط")
@app_commands.describe(member="العضو اللي تبي تغيّر مستواه", level="المستوى الجديد (يصفّر نقاط الخبرة الحالية)")
@app_commands.checks.has_permissions(administrator=True)
async def set_level(interaction: discord.Interaction, member: discord.Member, level: app_commands.Range[int, 0, 1000]):
    db = load_db()
    uid = str(member.id)
    db["levels"][uid] = {"xp": 0, "level": level}
    save_db(db)
    await interaction.response.send_message(
        f"✅ تم تحديد مستوى {member.mention} إلى **{level}**.", ephemeral=True
    )


@bot.tree.command(name="rank", description="عرض مستواك ونقاط خبرتك الحالية")
async def rank(interaction: discord.Interaction):
    db = load_db()
    uid = str(interaction.user.id)
    user_data = db["levels"].get(uid, {"xp": 0, "level": 0})

    needed = xp_needed_for_level(user_data["level"] + 1)
    percent = int(user_data["xp"] / needed * 100)
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)

    embed = discord.Embed(title=f"📈 مستوى {interaction.user.display_name}", color=MAIN_COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="المستوى الحالي", value=f"**{user_data['level']}**", inline=True)
    embed.add_field(name="نقاط الخبرة", value=f"{user_data['xp']} / {needed}", inline=True)
    embed.add_field(name="التقدم", value=f"{bar} {percent}%", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="leaderboard", description="عرض أعلى 10 أعضاء بنقاط الخبرة")
async def leaderboard(interaction: discord.Interaction):
    db = load_db()
    levels = db.get("levels", {})
    if not levels:
        return await interaction.response.send_message("⚠️ ما فيه أي بيانات مستويات بعد.", ephemeral=True)

    def total_xp(data):
        # نحسب XP الكلي التقريبي لغرض الترتيب (المستوى أهم من الباقي)
        return data["level"] * 100000 + data["xp"]

    sorted_users = sorted(levels.items(), key=lambda item: total_xp(item[1]), reverse=True)[:10]

    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_users):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"عضو مغادر ({uid})"
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} **{name}** — المستوى {data['level']} ({data['xp']} XP)")

    embed = discord.Embed(title="🏆 لوحة الصدارة", description="\n".join(lines), color=MAIN_COLOR)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="balance", description="عرض رصيدك الحالي في البنك")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    gold = get_gold(interaction.user.id)
    embed = bank_embed(
        interaction,
        title="🏦 رصيدك",
        description=f"معك حاليًا: **{format_amount(bal)}** 💵\nذهبك: **{gold}** 🥇",
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(file=await _bank_embed_card(interaction.user, embed), ephemeral=True)


@bot.tree.command(name="mines", description="العب لعبة الألغام واربح مكافأة (بدون رهان)")
async def mines(interaction: discord.Interaction):
    if BANK_CHANNEL_ID and interaction.channel.id != BANK_CHANNEL_ID:
        embed = bank_embed(interaction, title="لعبة البنك", description=f"اللعبة تشتغل فقط في روم البنك <#{BANK_CHANNEL_ID}>.", color=DANGER_COLOR)
        return await interaction.response.send_message(file=await _bank_embed_card(interaction.user, embed), ephemeral=True)

    view = MinesGameView(interaction.user)
    embed = bank_embed(
        interaction,
        title="⛏️ لعبة البنك - Mines",
        description=(
            f"اللاعب: {interaction.user.mention}\n"
            f"فيه قنبلة وحدة مخفية بين 9 مربعات 💣\n"
            "اضغط على مربع تفتحه، وكل ما فتحت أكثر كبرت مكافأتك المحتملة!\n"
            "(مافيه رهان - لو انفجرت القنبلة رصيدك ما يتأثر)"
        ),
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(file=await _bank_embed_card(interaction.user, embed), view=view)


async def send_suggestion_panel_message(channel: discord.TextChannel):
    """إرسال لوحة الاقتراحات لروم معين - تُستخدم من الأمر ومن لوحة التحكم."""
    embed = discord.Embed(
        title=get_custom_message("suggestion_panel", "title"),
        description=get_custom_message("suggestion_panel", "description"),
        color=MAIN_COLOR,
    )
    if TICKET_BANNER_URL:
        embed.set_image(url=TICKET_BANNER_URL)
    embed.set_footer(text=get_custom_message("suggestion_panel", "footer"))
    await channel.send(embed=embed, view=SuggestionPanelView())


async def send_ticket_panel_message(channel: discord.TextChannel):
    """إرسال لوحة التذاكر لروم معين - تُستخدم من الأمر ومن لوحة التحكم."""
    embed = discord.Embed(
        title=get_custom_message("ticket_panel", "title"),
        description=(
            get_custom_message("ticket_panel", "description") + "\n\n"
            "**الأنواع المتاحة:**\n"
            + "\n".join(f"{v['emoji']} {v['label']}" for v in TICKET_TYPES.values())
        ),
        color=MAIN_COLOR,
    )
    banner_url, banner_file = resolve_ticket_banner()
    if banner_url:
        embed.set_image(url=banner_url)
    embed.set_footer(text=get_custom_message("ticket_panel", "footer"))

    if banner_file:
        await channel.send(embed=embed, view=TicketPanelView(), file=banner_file)
    else:
        await channel.send(embed=embed, view=TicketPanelView())


@bot.tree.command(name="control_panel", description="إرسال لوحة التحكم بهذا الروم (للإدارة فقط) - ثبّتها لسهولة الوصول")
@app_commands.checks.has_permissions(administrator=True)
async def control_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎛️ لوحة تحكم 3FH PARTY ROYAL",
        description="اضغط أي زر بالأسفل لتنفيذ الأمر مباشرة بهذا الروم بدون كتابة أوامر.",
        color=MAIN_COLOR,
    )
    await interaction.channel.send(embed=embed, view=ControlPanelView())
    await interaction.response.send_message(
        "✅ تم إرسال لوحة التحكم. ينصح تثبّتها (Pin) بأعلى الروم لسهولة الوصول.", ephemeral=True
    )


@bot.tree.command(name="suggestion_panel", description="إرسال لوحة الاقتراحات في هذا الروم (للإدارة فقط)")
@app_commands.checks.has_permissions(administrator=True)
async def suggestion_panel(interaction: discord.Interaction):
    """إرسال لوحة الاقتراحات الاحترافية بزر (اقتراح جديد)."""
    await send_suggestion_panel_message(interaction.channel)
    await interaction.response.send_message("✅ تم إرسال لوحة الاقتراحات بنجاح.", ephemeral=True)


@bot.tree.command(name="ticket_panel", description="إرسال لوحة التذاكر في هذا الروم (للإدارة فقط)")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    """إرسال لوحة التذاكر الاحترافية مع البنر والعنوان والقائمة."""
    await send_ticket_panel_message(interaction.channel)
    await interaction.response.send_message("✅ تم إرسال لوحة التذاكر بنجاح.", ephemeral=True)


@bot.tree.command(name="set_ticket_banner", description="ضبط صورة بنر التذاكر (ارفع صورة مباشرة) - للإدارة فقط")
@app_commands.describe(image="الصورة اللي تبي تستخدمها كبنر للتذاكر ولوحة التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket_banner(interaction: discord.Interaction, image: discord.Attachment):
    if not (image.content_type and image.content_type.startswith("image/")):
        return await interaction.response.send_message("❌ الملف اللي رفعته مو صورة. ارفع ملف PNG أو JPG.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    ext = os.path.splitext(image.filename)[1] or ".png"
    save_path = os.path.join(BANNERS_DIR, f"ticket_banner{ext}")

    try:
        for old_file in os.listdir(BANNERS_DIR):
            if old_file.startswith("ticket_banner"):
                os.remove(os.path.join(BANNERS_DIR, old_file))
        await image.save(save_path)
    except Exception as e:
        return await interaction.followup.send(f"❌ حدث خطأ أثناء حفظ الصورة: {e}", ephemeral=True)

    db = load_db()
    db["settings"]["ticket_banner_path"] = save_path
    save_db(db)

    await interaction.followup.send(
        "✅ تم ضبط بنر التذاكر بنجاح! أرسل لوحة تذاكر جديدة بـ `/ticket_panel` عشان يظهر البنر الجديد.",
        ephemeral=True,
    )


@bot.tree.command(name="set_ticket_role", description="تحديد الرتب المسموح لها تفتح تذاكر - للإدارة فقط")
@app_commands.describe(action="نوع العملية", role="الرتبة (مطلوبة مع إضافة/إزالة)")
@app_commands.choices(action=[
    app_commands.Choice(name="➕ إضافة رتبة", value="add"),
    app_commands.Choice(name="➖ إزالة رتبة", value="remove"),
    app_commands.Choice(name="📋 عرض القائمة الحالية", value="list"),
    app_commands.Choice(name="🗑️ مسح الكل (يرجع فتح التذاكر متاح للجميع)", value="clear"),
])
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket_role(interaction: discord.Interaction, action: app_commands.Choice[str], role: discord.Role = None):
    db = load_db()
    allowed_roles = db["settings"].setdefault("ticket_allowed_roles", [])

    if action.value == "add":
        if not role:
            return await interaction.response.send_message("❌ لازم تحدد رتبة مع خيار الإضافة.", ephemeral=True)
        if role.id not in allowed_roles:
            allowed_roles.append(role.id)
            save_db(db)
        return await interaction.response.send_message(
            f"✅ تم السماح لرتبة {role.mention} بفتح التذاكر.", ephemeral=True
        )

    if action.value == "remove":
        if not role:
            return await interaction.response.send_message("❌ لازم تحدد رتبة مع خيار الإزالة.", ephemeral=True)
        if role.id in allowed_roles:
            allowed_roles.remove(role.id)
            save_db(db)
        return await interaction.response.send_message(
            f"✅ تم إزالة رتبة {role.mention} من قائمة فتح التذاكر.", ephemeral=True
        )

    if action.value == "clear":
        db["settings"]["ticket_allowed_roles"] = []
        save_db(db)
        return await interaction.response.send_message(
            "✅ تم المسح - فتح التذاكر صار متاح لجميع الأعضاء.", ephemeral=True
        )

    # action.value == "list"
    if not allowed_roles:
        return await interaction.response.send_message(
            "📋 ما فيه قيود حالياً - فتح التذاكر متاح لجميع الأعضاء.", ephemeral=True
        )
    mentions = "\n".join(f"• <@&{rid}>" for rid in allowed_roles)
    await interaction.response.send_message(f"📋 الرتب المسموح لها فتح تذاكر حالياً:\n{mentions}", ephemeral=True)


@bot.tree.command(name="voice_join", description="يخلي البوت يدخل ويقعد بروم صوتي معين ويبدأ يحسب وقته فيه - للأونر والإدارة العليا بس")
@app_commands.describe(voice_channel="الروم الصوتي اللي تبي البوت يدخله ويقعد فيه")
@is_owner_or_senior_admin()
async def voice_join(interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
    await interaction.response.defer(ephemeral=True)

    existing_vc = interaction.guild.voice_client
    try:
        if existing_vc:
            await existing_vc.move_to(voice_channel)
        else:
            await voice_channel.connect()
    except Exception as e:
        return await interaction.followup.send(f"❌ ما قدرت أدخل الروم: {e}", ephemeral=True)

    await interaction.followup.send(f"✅ دخلت روم {voice_channel.mention} وبدأت أحسب وقتي فيه.", ephemeral=True)


@bot.tree.command(name="voice_leave", description="يخلي البوت يطلع من الروم الصوتي - للأونر والإدارة العليا بس")
@is_owner_or_senior_admin()
async def voice_leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if not voice_client:
        return await interaction.response.send_message("❌ البوت مو داخل أي روم صوتي حالياً.", ephemeral=True)

    await voice_client.disconnect()
    await interaction.response.send_message("✅ طلعت من الروم الصوتي.", ephemeral=True)


@bot.tree.command(name="voice_uptime", description="عرض كم صار للبوت قاعد بالروم الصوتي")
async def voice_uptime(interaction: discord.Interaction):
    db = load_db()
    tracker = db.get("bot_voice_uptime", {"voice_channel_id": None, "connected_since": None, "total_seconds": 0})

    total_seconds = tracker.get("total_seconds", 0)
    connected_since = tracker.get("connected_since")
    channel_id = tracker.get("voice_channel_id")
    channel = interaction.guild.get_channel(channel_id) if channel_id else None

    if connected_since:
        live_seconds = total_seconds + max(0, datetime.now(timezone.utc).timestamp() - connected_since)
        status_line = f"🟢 متصل الآن بروم {channel.mention if channel else '—'}"
    else:
        live_seconds = total_seconds
        status_line = "🔴 غير متصل حالياً"

    await interaction.response.send_message(
        f"{status_line}\n⏱️ إجمالي الوقت المتراكم: **{format_duration(live_seconds)}**", ephemeral=True
    )


@bot.tree.command(name="set_suggestion_banner", description="ضبط صورة الاقتراحات الافتراضية (تظهر كمربع صغير بالزاوية) - للإدارة فقط")
@app_commands.describe(image="الصورة اللي تبي تستخدمها كأيقونة افتراضية لكل الاقتراحات")
@app_commands.checks.has_permissions(administrator=True)
async def set_suggestion_banner(interaction: discord.Interaction, image: discord.Attachment):
    if not (image.content_type and image.content_type.startswith("image/")):
        return await interaction.response.send_message("❌ الملف اللي رفعته مو صورة. ارفع ملف PNG أو JPG.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    ext = os.path.splitext(image.filename)[1] or ".png"
    save_path = os.path.join(BANNERS_DIR, f"suggestion_banner{ext}")

    try:
        for old_file in os.listdir(BANNERS_DIR):
            if old_file.startswith("suggestion_banner"):
                os.remove(os.path.join(BANNERS_DIR, old_file))
        await image.save(save_path)
    except Exception as e:
        return await interaction.followup.send(f"❌ حدث خطأ أثناء حفظ الصورة: {e}", ephemeral=True)

    db = load_db()
    db["settings"]["suggestion_banner_path"] = save_path
    save_db(db)

    await interaction.followup.send(
        "✅ تم ضبط صورة الاقتراحات بنجاح! كل اقتراح جديد بيظهر فيه هذي الصورة تلقائيًا كمربع صغير بالزاوية.",
        ephemeral=True,
    )


# =====================================================================
#      ✏️  تعديل أي رسالة/نص بالبوت من ديسكورد مباشرة (بدون كود)
# =====================================================================
class EditMessageModal(discord.ui.Modal):
    """نافذة تعديل ديناميكية - تُبنى تلقائياً حسب حقول الرسالة المختارة من MESSAGE_REGISTRY."""

    def __init__(self, message_key: str):
        config = MESSAGE_REGISTRY[message_key]
        super().__init__(title=config["label"][:45])
        self.message_key = message_key
        self.field_inputs: dict[str, discord.ui.TextInput] = {}

        for field_key, field_conf in config["fields"].items():
            current_value = get_custom_message(message_key, field_key)
            text_input = discord.ui.TextInput(
                label=field_conf["label"][:45],
                style=discord.TextStyle.paragraph if field_conf["style"] == "long" else discord.TextStyle.short,
                default=current_value[:4000],
                required=field_conf.get("required", True),
                max_length=4000 if field_conf["style"] == "long" else 256,
            )
            self.field_inputs[field_key] = text_input
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        db = load_db()
        custom_messages = db["settings"].setdefault("custom_messages", {})
        saved_entry = custom_messages.setdefault(self.message_key, {})
        for field_key, text_input in self.field_inputs.items():
            saved_entry[field_key] = str(text_input.value)
        save_db(db)

        note = ""
        if self.message_key in ("ticket_panel", "suggestion_panel"):
            panel_cmd = "/ticket_panel" if self.message_key == "ticket_panel" else "/suggestion_panel"
            note = f"\n\n📌 أرسل `{panel_cmd}` من جديد بالروم المناسب عشان التعديل يظهر باللوحة."

        await interaction.response.send_message(
            f"✅ تم حفظ التعديل بنجاح!{note}", ephemeral=True
        )


@bot.tree.command(name="edit_message", description="عدّل أي رسالة أو رد تلقائي بالبوت من ديسكورد مباشرة - بدون لمس الكود (للإدارة فقط)")
@app_commands.describe(message="اختر الرسالة اللي تبي تعدلها")
@app_commands.choices(message=[
    app_commands.Choice(name=v["label"], value=k) for k, v in MESSAGE_REGISTRY.items()
])
@app_commands.checks.has_permissions(administrator=True)
async def edit_message(interaction: discord.Interaction, message: app_commands.Choice[str]):
    modal = EditMessageModal(message.value)
    await interaction.response.send_modal(modal)


@bot.tree.command(name="reset_message", description="رجّع رسالة معينة لنصها الافتراضي الأصلي (يلغي أي تعديل سابق) - للإدارة فقط")
@app_commands.describe(message="اختر الرسالة اللي تبي ترجعها للوضع الافتراضي")
@app_commands.choices(message=[
    app_commands.Choice(name=v["label"], value=k) for k, v in MESSAGE_REGISTRY.items()
])
@app_commands.checks.has_permissions(administrator=True)
async def reset_message(interaction: discord.Interaction, message: app_commands.Choice[str]):
    db = load_db()
    custom_messages = db["settings"].setdefault("custom_messages", {})
    custom_messages.pop(message.value, None)
    save_db(db)
    await interaction.response.send_message(
        f"✅ تم إرجاع «{message.name}» لنصها الافتراضي.", ephemeral=True
    )


# =====================================================================
#                    ⚠️  معالج الأخطاء العام للأوامر
# =====================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ لا تملك الصلاحية الكافية لاستخدام هذا الأمر."
    else:
        msg = f"⚠️ حدث خطأ غير متوقع: {error}"
        # نطبع الخطأ الكامل بالترمينال لتسهيل معرفة السبب الحقيقي
        import traceback
        print("========== خطأ بأمر Slash ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("=====================================")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


# =====================================================================
#                          ▶️  تشغيل البوت
# =====================================================================
if __name__ == "__main__":
    ensure_data_files()
    if not TOKEN:
        raise SystemExit("❌ لم يتم العثور على التوكن! تأكد من ضبط متغير TOKEN داخل ملف .env بشكل صحيح.")
    bot.run(TOKEN)
