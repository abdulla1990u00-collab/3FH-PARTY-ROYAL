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
import time
import functools
from datetime import datetime, timezone, timedelta

import aiohttp
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
MINES_BOMB_COUNT = 3          # عدد القنابل المخفية (شبكة 5x4 = 20 مربع)
MINES_MULTIPLIER_STEP = 0.3   # مقدار زيادة الأرباح بكل مربع آمن
MINES_BASE_REWARD = 100        # المكافأة الأساسية - لا يوجد رهان ولا خصم عند الخسارة

# --- نظام الانتظار (Cooldown) لأوامر البنك ---
# مدة الانتظار بالثواني لكل أمر بعد استخدامه - 0 = جاهز دائماً بدون انتظار
BANK_COOLDOWNS = {
    "نرد": 274,       # ~4:34 دقيقة
    "ألغام": 300,     # 5 دقائق (من بداية الجولة)
    "تحويل": 0,
    "شراء": 0,
    "بيع": 0,
}
# ترتيب ظهور الأوامر بجدول أمر "وقت"
BANK_STATUS_ORDER = ["نرد", "ألغام", "تحويل", "شراء", "بيع"]

# --- أوامر البنك المرجّعة (راتب / روليت / نهب ...) ---
BANK_COOLDOWNS.update({
    "راتب": 86400, "بخشيش": 300, "حظ": 180, "روليت": 300, "نهب": 600, "رهان": 30,
    "استثمار": 291, "تداول": 255, "قمار": 60, "لعبه": 0, "لون": 0, "فواكه": 0, "تسريع": 0,
})
BANK_STATUS_ORDER[:] = [
    "راتب", "بخشيش", "حظ", "روليت", "نهب", "رهان", "استثمار", "تداول", "قمار",
    "نرد", "ألغام", "لعبه", "لون", "فواكه", "تسريع", "بيع", "شراء",
]
SALARY_AMOUNT = 2000
TIP_MIN, TIP_MAX = 200, 900
LUCK_MIN, LUCK_MAX = -400, 700
ROULETTE_PRIZES = [  # (القيمة أو "gold:عدد", الوزن الاحتمالي)
    (1500, 22), (6000, 18), (9000, 15), (12000, 12), (15000, 9),
    (19000, 7), (50000, 4), (100000, 2), ("gold:5", 7), ("gold:10", 4),
]
ROB_SUCCESS_CHANCE = 0.65
ROB_PERCENT = 0.01
ROB_FAIL_FINE = 500
PROTECTION_HOURS = 5
PROTECTION_COST = 2000
INVEST_MIN_PCT, INVEST_MAX_PCT = -0.35, 0.90
TRADE_MIN_PCT, TRADE_MAX_PCT = -0.55, 1.35
BET_MIN_BET = GAMBLE_MIN_BET = 100
INVEST_MIN_BET, TRADE_MIN_BET = 200, 200
MINES_MIN_BET = 100
SPEEDUP_GOLD_COST = 30
BANK_OWNER_ROLE_ID = int(os.getenv("BANK_OWNER_ROLE_ID", "0"))
PROPERTY_CATALOG = {
    "car": {"name": "سياره", "emoji": "🚗", "price": 3000},
    "house": {"name": "بيت", "emoji": "🏠", "price": 5000},
    "land": {"name": "اراضي", "emoji": "🗺️", "price": 10000},
    "store": {"name": "متجر", "emoji": "🏪", "price": 8000},
    "building": {"name": "مبنى", "emoji": "🏢", "price": 20000},
    "company": {"name": "شركه", "emoji": "🏭", "price": 50000},
}
PROPERTY_SELL_RATIO = 0.6
STOCK_PRICE = 500
GOLD_PACK_PRICE, GOLD_PACK_AMOUNT = 1000, 5
GAMBLE_OUTCOMES = [(0.0, 20), (0.5, 20), (1.5, 25), (2.0, 20), (3.0, 10), (5.0, 5)]
COLOR_MAX_ATTEMPTS = 25
COLOR_RESET_HOURS = 24

# --- هوية البنك + السوق العالمي ---
BANK_BRAND = os.getenv("BANK_BRAND", "Party Royale 3FH")   # اسم البنك اللي يظهر بالصور (بدل SKYE)
MARKET_UPDATE_MINUTES = max(1, int(os.getenv("MARKET_UPDATE_MINUTES", "5")))  # كل كم دقيقة تتحدث الأسعار

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
            "portfolio": {},            # {user_id: {asset: {"units": float, "cost": float}}} - استثمارات البنك
            "market": {},               # أسعار السوق العالمي المحفوظة (تتحدث تلقائياً)
            "bank_cooldowns": {},       # {user_id: {اسم_الأمر: timestamp الجاهزية}} - أوقات انتظار أوامر البنك
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
    data.setdefault("portfolio", {})
    data.setdefault("market", {})
    data.setdefault("bank_cooldowns", {})
    data.setdefault("gold", {})
    data.setdefault("protection", {})
    data.setdefault("properties", {})
    data.setdefault("color_game", {})
    data.setdefault("bank_history", {})
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
#              ⏱️  نظام الانتظار (Cooldown) لأوامر البنك
#   الأوقات تُحفظ بقاعدة البيانات كـ timestamp للجاهزية - فما تضيع بإعادة التشغيل.
# =====================================================================
def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def get_cooldown_remaining(user_id: int, action: str) -> float:
    """الثواني المتبقية قبل ما يجهز الأمر للعضو (0 = جاهز)."""
    if BANK_COOLDOWNS.get(action, 0) <= 0:
        return 0.0
    ready_at = load_db()["bank_cooldowns"].get(str(user_id), {}).get(action, 0)
    return max(0.0, ready_at - _now_ts())


def set_cooldown(user_id: int, action: str) -> None:
    duration = BANK_COOLDOWNS.get(action, 0)
    if duration <= 0:
        return
    db = load_db()
    db["bank_cooldowns"].setdefault(str(user_id), {})[action] = _now_ts() + duration
    save_db(db)


def clear_cooldown(user_id: int, action: str) -> None:
    """يلغي انتظار أمر معين (يُستخدم لو فشلت العملية - مثلاً الرصيد ما يكفي)."""
    db = load_db()
    db["bank_cooldowns"].get(str(user_id), {}).pop(action, None)
    save_db(db)


def format_clock(seconds: float) -> str:
    """تنسيق مؤقت احترافي: 04:51 أو 1:05:00 (يقرّب للأعلى عشان ما يظهر 00:00 وهو لسه منتظر)."""
    total = int(seconds) + (1 if seconds % 1 else 0)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def cooldown_notice(user_id: int, action: str):
    """نص تنبيه لو الأمر لسه بالانتظار، أو None لو جاهز."""
    remaining = get_cooldown_remaining(user_id, action)
    if remaining <= 0:
        return None
    ready_ts = int(_now_ts() + remaining)
    return (f"⏳ أمر **{action}** بفترة انتظار • تقدر تستخدمه من جديد <t:{ready_ts}:R> "
            f"(`{format_clock(remaining)}`)\nاكتب `وقت` لعرض حالة كل الأوامر.")


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
            ("تصويت السؤال | خيار1 | خيار2", "إنشاء استطلاع رأي بأزرار (حتى 4 خيارات)"),
            ("/athkar", "إرسال ذِكر عشوائي"),
            ("لفل", "عرض مستواك ونقاط خبرتك الحالية"),
            ("/leaderboard", "عرض أعلى 10 أعضاء بنقاط الخبرة"),
            ("/control_panel", "إرسال لوحة التحكم العامة بهذا الروم"),
        ],
    },
    "bank": {
        "label": "🏦 البنك",
        "emoji": "🏦",
        "commands": [
            ("فلوس", "كشف حسابك بصورة"),
            ("تحويل @عضو 500", "تحويل مبلغ لعضو"),
            ("سوق", "أسعار الذهب والأسهم من السوق العالمي"),
            ("شراء ذهب 500", "شراء أصل بسعر السوق"),
            ("بيع ذهب", "بيع أصل (فاضي = بيع الكل)"),
            ("حصالتي", "حصالتك وأرباحك"),
            ("نرد 100", "تحدّى البوت بالنرد"),
            ("الغام", "لعبة الألغام واربح مكافأة"),
        ],
    },
    "admin": {
        "label": "⚙️ إدارة عامة",
        "emoji": "⚙️",
        "commands": [
            ("مسح 50  (أو: مسح 50 الكل)", "حذف رسائل بهذا الروم أو كل رومات السيرفر"),
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
@bot.event
async def on_ready():
    # تسجيل الفيوهات الدائمة حتى تعمل الأزرار بعد إعادة تشغيل البوت
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(SuggestionView())
    bot.add_view(SuggestionPanelView())
    bot.add_view(ControlPanelView())
    bot.add_view(RatingView())

    # تشغيل تحديث أسعار السوق العالمي (مرة وحدة فقط حتى لو تكرر on_ready)
    if not market_updater.is_running():
        market_updater.start()
    asyncio.create_task(ensure_arabic_font())   # يتأكد من وجود خط عربي لصور البنك

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

    # أوامر البنك النصية (فلوس / تحويل / نرد / سوق ...) - تشتغل بس بروم البنك
    if await handle_text_commands(message):
        return
    if await handle_bank_text(message):
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


# ---- تشكيل عربي احتياطي (لو arabic_reshaper/bidi/Raqm مو متوفرين) - يضمن إن الحروف تنربط ----
_AR_FORMS = {
    "ء": ("ﺀ",), "آ": ("ﺁ", "ﺂ"), "أ": ("ﺃ", "ﺄ"), "ؤ": ("ﺅ", "ﺆ"), "إ": ("ﺇ", "ﺈ"),
    "ئ": ("ﺉ", "ﺊ", "ﺋ", "ﺌ"), "ا": ("ﺍ", "ﺎ"), "ب": ("ﺏ", "ﺐ", "ﺑ", "ﺒ"), "ة": ("ﺓ", "ﺔ"),
    "ت": ("ﺕ", "ﺖ", "ﺗ", "ﺘ"), "ث": ("ﺙ", "ﺚ", "ﺛ", "ﺜ"), "ج": ("ﺝ", "ﺞ", "ﺟ", "ﺠ"),
    "ح": ("ﺡ", "ﺢ", "ﺣ", "ﺤ"), "خ": ("ﺥ", "ﺦ", "ﺧ", "ﺨ"), "د": ("ﺩ", "ﺪ"), "ذ": ("ﺫ", "ﺬ"),
    "ر": ("ﺭ", "ﺮ"), "ز": ("ﺯ", "ﺰ"), "س": ("ﺱ", "ﺲ", "ﺳ", "ﺴ"), "ش": ("ﺵ", "ﺶ", "ﺷ", "ﺸ"),
    "ص": ("ﺹ", "ﺺ", "ﺻ", "ﺼ"), "ض": ("ﺽ", "ﺾ", "ﺿ", "ﻀ"), "ط": ("ﻁ", "ﻂ", "ﻃ", "ﻄ"),
    "ظ": ("ﻅ", "ﻆ", "ﻇ", "ﻈ"), "ع": ("ﻉ", "ﻊ", "ﻋ", "ﻌ"), "غ": ("ﻍ", "ﻎ", "ﻏ", "ﻐ"),
    "ف": ("ﻑ", "ﻒ", "ﻓ", "ﻔ"), "ق": ("ﻕ", "ﻖ", "ﻗ", "ﻘ"), "ك": ("ﻙ", "ﻚ", "ﻛ", "ﻜ"),
    "ل": ("ﻝ", "ﻞ", "ﻟ", "ﻠ"), "م": ("ﻡ", "ﻢ", "ﻣ", "ﻤ"), "ن": ("ﻥ", "ﻦ", "ﻧ", "ﻨ"),
    "ه": ("ﻩ", "ﻪ", "ﻫ", "ﻬ"), "و": ("ﻭ", "ﻮ"), "ى": ("ﻯ", "ﻰ"), "ي": ("ﻱ", "ﻲ", "ﻳ", "ﻴ"),
}
_AR_ALIAS = {"ک": "ك", "ی": "ي", "پ": "ب", "چ": "ج", "گ": "ك", "ڤ": "ف", "ٱ": "ا"}
_LAM_ALEF = {"ا": ("ﻻ", "ﻼ"), "أ": ("ﻷ", "ﻸ"), "إ": ("ﻹ", "ﻺ"), "آ": ("ﻵ", "ﻶ")}
_AR_TASHKEEL = set("ًٌٍَُِّْٰ")


def _ar_shape_fallback(text: str) -> str:
    chars = [_AR_ALIAS.get(c, c) for c in text]
    # حروف + تشكيل: نتجاهل التشكيل بالربط ونرجّعه بعد الحرف
    out, i, n = [], 0, len(chars)
    base = [(c, []) for c in chars if c not in _AR_TASHKEEL]
    # نعيد ربط التشكيل بحرفه
    tmp, last = [], None
    for c in chars:
        if c in _AR_TASHKEEL and tmp:
            tmp[-1][1].append(c)
        else:
            tmp.append((c, []))
    base = tmp

    def joins_next(c):      # الحرف يتصل بما بعده؟ (dual-joining)
        return c in _AR_FORMS and len(_AR_FORMS[c]) == 4
    def joins_prev(c):
        return c in _AR_FORMS and len(_AR_FORMS[c]) >= 2
    shaped = []
    k = 0
    while k < len(base):
        c, marks = base[k]
        if c not in _AR_FORMS:
            shaped.append((c, marks)); k += 1; continue
        prev_c = base[k - 1][0] if k > 0 else ""
        prev_joins = joins_next(prev_c)
        if c == "ل" and k + 1 < len(base) and base[k + 1][0] in _LAM_ALEF:
            lig = _LAM_ALEF[base[k + 1][0]]
            shaped.append((lig[1] if prev_joins else lig[0], marks + base[k + 1][1]))
            k += 2
            continue
        nxt = base[k + 1][0] if k + 1 < len(base) else ""
        next_joins = joins_prev(nxt) and joins_next(c)
        forms = _AR_FORMS[c]
        if len(forms) == 4:
            idx = 3 if (prev_joins and next_joins) else 1 if prev_joins else 2 if next_joins else 0
        elif len(forms) == 2:
            idx = 1 if prev_joins else 0
        else:
            idx = 0
        shaped.append((forms[idx], marks))
        k += 1
    flat = []
    for c, marks in shaped:
        flat.append(c)
        flat.extend(marks)
    # ---- ترتيب بصري RTL (مبسّط) ----
    def kind(ch):
        if "؀" <= ch <= "ۿ" or "ﭐ" <= ch <= "﷿" or "ﹰ" <= ch <= "﻿":
            return "R"
        if ch.isalnum():
            return "L"
        return "N"
    kinds = [kind(ch) for ch in flat]
    first = next((kd for kd in kinds if kd != "N"), "L")
    if first == "L":                       # اتجاه أساسي LTR: نعكس أي مقطع عربي داخلياً بس
        res, run = [], []
        for ch, kd in zip(flat, kinds):
            if kd == "R":
                run.append(ch)
            else:
                res.extend(reversed(run)); run = []
                res.append(ch)
        res.extend(reversed(run))
        return "".join(res)
    resolved = list(kinds)
    for i2, kd in enumerate(kinds):
        if kd == "N":
            lft = next((kinds[j] for j in range(i2 - 1, -1, -1) if kinds[j] != "N"), "R")
            rgt = next((kinds[j] for j in range(i2 + 1, len(kinds)) if kinds[j] != "N"), "R")
            resolved[i2] = "L" if (lft == "L" and rgt == "L") else "R"
    groups = []
    for ch, kd in zip(flat, resolved):
        if groups and groups[-1][0] == kd:
            groups[-1][1].append(ch)
        else:
            groups.append([kd, [ch]])
    return "".join("".join(g[1]) if g[0] == "L" else "".join(reversed(g[1])) for g in reversed(groups))


def _prep(text: str) -> str:
    """تجهيز النص العربي للرسم (ربط الحروف + ترتيب اتجاه RTL)."""
    if not _has_ar(text):
        return text
    if HAS_AR_LIBS:
        return _bidi_display(arabic_reshaper.reshape(text))
    if features.check("raqm"):
        return text                      # Raqm يشكّل ويرتّب لحاله
    return _ar_shape_fallback(text)      # احتياطي مدمج: يضمن اتصال الحروف بدون أي مكتبة


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
        forms = render("\uFE91")       # شكل البداية (مطلوب لربط الحروف بدون Raqm)
        if not (arabic != missing and any(arabic)):
            return False
        if not features.check("raqm") and not (forms != missing and any(forms)):
            return False
        return True
    except Exception:
        return False



# خط عربي مدمج (DejaVu Sans Bold - مقصوص للعربي + اللاتيني) عشان الصور ما تطلع مربعات حتى لو السيرفر ما فيه أي خط
_EMBEDDED_AR_FONT_B64 = (
    "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"
    "VolfiJcMGP/ytfZ18HX19TTD2Lt5d/PV5lvNvza34FI8mWDU39F/3vRZ08mmE03/ajrYtK9pb9MHTTubdjRtadrYtK7pnaYVTcub"
    "ljUtaiq9M/TOkDuD7uTd6Xun189Xb1dcPyp2FmNEuWgnWgtN3CJuITf/9T3h/5N/TvAXziQDL+uRJxqHqtBadBhdQ09YjpWzPmwY"
    "O4SdzNayt1nMRXATuDncV7wl78PH8tn8ML6c3yMohC7CZGGHcEV4KLJAc09xqDhFXCXuEM+IN2TWskhZkWyd7EdZo4Wthb9FqsVo"
    "i1kW71rstvjE4iuLXyweW+jbxbcb125du4vtWiy9LIdazrfcaPmJZYPlXSsvq+5W5VY7rBqs/rbWWPe3nm29xvqI9VXr/7S3ap/Q"
    "Pqt9dft98HfeRrTR2FTb7LU5Zettq7bdYnvLFtvZ2HnarbLbaldv91juKu8tHy5fLT8gPyG/JX9q72efYt/XfpR9hf1e+6P2Z+2/"
    "sb9h/8BB6ZDjMNCh0GGSQ7XDQoc1Dtsc9jl84vCXQ4ujhaOjo69jB8eOjoMcdzgedDzueMHxO8efnSycejkNcRrjVOlU47TUab3T"
    "C2fe2c7Z0znIOdo5yTnbOc95lPMe54+dzzjXO193vu/8HxdblzyXUS6lLjNcFrisdjnncsXltqudq59ruusU17NuHm5d3Sa6zXbb"
    "63bOTece5Z7onune332E+wT3Ge4L3Fe7b3Xf637U/bF7s4ePR6hHjsdAj+MeFzyDPKM9x3tO9Tzp+aXnNc97nv/26uU12+tLr++9"
    "rb37eu/2/sj7ko+nj9onwedtn1U+3/u88PX2Vfmqfaf4LvJd53vI947CR1GoWKs4rrjnZ+PX02+C33K/d/0O+f2i7KTMUE5RzlUu"
    "V76n3KP8WHlGWa+8rryv/I9S72/l7+Kv9I/w7+Sf5t/Hf6T/RP/p/vP9V/lv8d/j/7H/Gf96/+v+D/2fB3ABtgE+AaEBnQLSAvoE"
    "DAsYF3A24JuAnwMaA14E8oF2gZ6BYwOPBp4N/CbwRuCDwKcqRmWtclX5q9Sqzqp0VV9VgapUVavarzqp+jLIOyg8KD4oNah30NCg"
    "oqCyoJlBbwctC1obtDloZ9DvwargIcGFwSXBlaa/ucGLg9cHfxD8SfCXwfdD+JCwkKyQvJDCkEkh1SGLQnaGykOHhZ7p4NRhbIej"
    "He6HdQiLC+sftjLsRNjd8ODw4vA74X+Gv4wQIuQRXhHBEdqIrhE5EQMjCiMmRVRHLIxYE7EtYl/EJxHnIq5E3Iz4PeJvNVK3V7up"
    "A9SR6gR1hrqferi6RF2lnqdeqd6k/lD9L/Up9WX1NfU99b/Vush2kU6RisiwyLjI7pG9IodEjomsjKyJXBq5PvL9yEORn0TZRrlE"
    "+USFRsVGdYvqETU4anRUedSsqMVR70ZtjzoQ9XHUMw2rsdG4awI14ZoqTY1moWaNZptmn+YTzTnNFc1Nze+av6NRdPtot+iA6Mjo"
    "hOiM6MLohdEro9dHvx99KPpY9BfR9dGN0X9HY62l1kHrow3SRmsTtBna3tqh2iJtmXamdpF2rbZWu197TPuF9lvtLe0f2mdaHOMR"
    "o4rRxHSJyYoZEDMyZmLM9Jj5MatitsTsifk45kxMfcz1mPsx/4lpjs2MrYk9H3s19nbsw9jnsfqO6o6dO6Z37NlxdsclHdd13Bpn"
    "E5cXty/uk7hzcVfibsbdi+8Vvz7+UXxTJ7GTfSfvToGdxnaq7fRbpyedcGfLzs6dvTuP7byl84+df+38V+eWBIsExwTfhA4JHRNS"
    "Enom5CcUJ5Qm/JTomNg/cWji2sRDid8n3uoS1aWqy6UuP3S52+Vxl+YkLik5aUtSY9LTrilds7tu7Lqr65Gun3f9quuPXX/t+lfX"
    "lmSLZMfkpOTJ8LcweV3y5eQbyY+SX3az7Kbo1rFbRrfCbtu6fdjtUIptyqCUbd3Z7pbd7bu7d/frntl9UPex3ad1f7v7O903d9/d"
    "/aPup7t/3f2n7r91f9Idp1qmuqeGpManZqeOSa1M3Z56IPXT1POpV1Pvpv4nVZ/mlOaVpk3rmpaTNjCtMG1SWnXawrQ1ad+k3Uh7"
    "kPYinU+3S/dMD0rvmJ6S3jO9IL00fXb6kvR16TvSj6SfTf8u/ef0xvQXGXyGXYZnRlBGdEZSRnZGXsaojNKMGRkLMtZl7Mo4mnE2"
    "45uMGxkPMp5mMpnWma6Z/pnTMg9lPs5szpJlOWT5ZIVmxWZ1y+qRNThrdFZ51qysxVnvZm3POpD1adb5rKtZt7MeZj3P5rJtsz2y"
    "Vdma7G7ZfbJHZpdnz81elb0le0/2x9nf5FjQFboIr+WLhB2wQssYxkGukAco5Ioinmkp5zxa7uG1MpsXT8rEYIZFPlB9vtAAK3c7"
    "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"
    "peaVcINXiISYXnkR4z+amZ8bPf+LQUNefW8eH9azf5eObk9CZjq/v0eHVzYUxUFpju+eMIJHpT/93HoYYGrmjgzUq774HUFu2XnA"
    "dDVvcnq0bgRKh8veiyMVXOWIbMVFUmlU2+S0ru0Ej+qwVuo6nMptP+vqf3x0e5X/xuqJhZnuxGVpoiY2vnf2JR2ujglL1Pm47FRv"
    "9x6p3boltO/C72pnoLrD07sHDL5v2qK5iZxFXBo7ZtTCOV7fvkszhg0yRnbrkTgsjCiXe0esO+uDs+T2WHYSpQULaiGJ5iSyqyAt"
    "+UgqkbdoOStFTtOfMO5Z9x7Xl03bzpf51m2ftszX9N66e4yXRWr7scWzy8akZmamjimbXTyWs/3bNvApOZXLVvjZimWVOVP4hm37"
    "OcubMKDf4Hzf+iX5g/sNmJBnrlWLO+QatbTnYnSCvjkJ1/x62E24kM2NjjJ3zRUWaj/b29uI9P4DxGsBYy6Nsy8fGBO259VWw2cf"
    "Jlsvu6aVD7PZdrFZc+FDsrYMvszPrihX1l66ZubwOxz2XYJ3XXCXXO66oFSltZdkh7WXgd4AB/099tJpHuTqEKPvf26371cBcy9i"
    "Rf/7n151G4/LjOiePi6j4E7O504deMmwX9XOyGsXljo493Av3q3q1E1XlK/M6x2d0DM+LjopIql4Tt+xHRP2bPGzJ2/Xor0pnbos"
    "e8Jm48XcBSNLL+rUktwFU7ZfvtuukX+V/xMjMawN7Vm04imAZ7UJdyU74D+lcc9Iir+B1vxbsdNmfIRDfDtcxi+GkptIexCr1R7E"
    "LBPuSlY29mivBeNDfhQjfmmFiUtLbjR2on4femvqBo3Em4aOPeKbeue8ys3zJvoi+Dz+8CUxSbxCy/W99acrRjzXuzGJ8xT9qqYR"
    "fbJu3CN2SbyYnuzDQ+B0bkpo/zrgW9QMvRxX1WUm3XB/cAqq+xzeG+pA0+8N5h9qKJs1XH2vpkl9sMY4gR+sYfxsjX7MX0ix6GsT"
    "vv68i+/T/cYJ30kANO2ApzONk7Q2bbdPOtBuonRgfzwZjSeNfWKQFpba1dPzJlE9LWlc8tAOyW2TkvHGO9roniD0uOwMlxFjzFvV"
    "uVNym6hsGN4Y81bGYkqP68d8tys62ifws2+8tN/3KZLBw+HpWqDjKniKR/R7tEe7rGcr+IAP0S4rxrn/frR/AL9N4ADDQOB0E/yk"
    "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"
)


def _embedded_font_path():
    """يكتب الخط المدمج كملف مرة وحدة ويرجع مساره (None لو فشل)."""
    try:
        import base64, zlib
        folder = os.path.join(FILES_DIR, "fonts")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "_embedded_ar_bold.ttf")
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            with open(path, "wb") as fh:
                fh.write(zlib.decompress(base64.b64decode(_EMBEDDED_AR_FONT_B64)))
        return path
    except Exception as e:
        print(f"⚠️ [البنك] تعذّر تجهيز الخط المدمج: {e}")
        return None


def _resolve_font_paths() -> dict:
    if _font_paths_cache:
        return _font_paths_cache
    custom = []
    for pattern in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
        custom += sorted(glob.glob(os.path.join(FILES_DIR, "fonts", pattern)))
    ar_candidates = [os.getenv("BANK_FONT_AR"), WELCOME_FONT_PATH] + [p for p in custom if "_embedded_ar_bold" not in p] + [_embedded_font_path()] + [
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
    "https://github.com/dejavu-fonts/dejavu-fonts/raw/version_2_37/ttf/DejaVuSans-Bold.ttf",
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
    d.rounded_rectangle(R.box(386, 113, 1935, 322), radius=R.n(38), corners=(False, True, False, False), fill=B + (36,))
    d.rounded_rectangle(R.box(85, 337, 1935, 969), radius=R.n(40), corners=(False, True, True, True), fill=B + (92,))
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
    d.rounded_rectangle(R.box(85, 113, 1935, 322), radius=R.n(38), corners=(True, True, False, False), fill=B + (36,))
    d.rounded_rectangle(R.box(85, body_top, 1935, body_bottom), radius=R.n(40), corners=(False, False, True, True), fill=B + (92,))

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
ASSETS = {
    "gold":   {"name": "الذهب (جرام)",  "emoji": "🥇", "yahoo": "GC=F",     "div": 31.1035, "alt": "XAU", "fallback": 130.0,
               "aliases": ("ذهب", "الذهب", "gold")},
    "silver": {"name": "الفضة (جرام)",  "emoji": "🥈", "yahoo": "SI=F",     "div": 31.1035, "alt": "XAG", "fallback": 1.6,
               "aliases": ("فضة", "الفضة", "silver")},
    "oil":    {"name": "نفط برنت",      "emoji": "🛢️", "yahoo": "BZ=F",     "div": 1.0, "fallback": 70.0,
               "aliases": ("نفط", "النفط", "برنت", "oil")},
    "btc":    {"name": "بتكوين",        "emoji": "₿",  "yahoo": "BTC-USD",  "div": 1.0, "fallback": 100000.0,
               "aliases": ("بتكوين", "البتكوين", "btc", "bitcoin")},
    "eth":    {"name": "إيثريوم",       "emoji": "💠", "yahoo": "ETH-USD",  "div": 1.0, "fallback": 3500.0,
               "aliases": ("ايثريوم", "إيثريوم", "الايثريوم", "eth")},
    "tsla":   {"name": "تسلا",          "emoji": "🚗", "yahoo": "TSLA",     "div": 1.0, "fallback": 300.0,
               "aliases": ("تسلا", "tesla", "tsla")},
    "aapl":   {"name": "آبل",           "emoji": "🍎", "yahoo": "AAPL",     "div": 1.0, "fallback": 230.0,
               "aliases": ("ابل", "آبل", "apple", "aapl")},
    "nvda":   {"name": "إنفيديا",       "emoji": "🟩", "yahoo": "NVDA",     "div": 1.0, "fallback": 180.0,
               "aliases": ("انفيديا", "إنفيديا", "nvidia", "nvda")},
    "dxy":    {"name": "مؤشر الدولار",  "emoji": "💵", "yahoo": "DX-Y.NYB", "div": 1.0, "fallback": 100.0,
               "aliases": ("دولار", "الدولار", "dxy")},
}
ASSET_CHOICES = [app_commands.Choice(name=f"{a['emoji']} {a['name']}", value=k) for k, a in ASSETS.items()]
_YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=15m&range=1d"
_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def ensure_market(db: dict) -> dict:
    """يضمن وجود هيكل السوق بالداتابيس (أسعار + سعر الإغلاق السابق + بيانات الرسم)."""
    m = db.setdefault("market", {})
    m.setdefault("prices", {})
    m.setdefault("ref", {})
    m.setdefault("spark", {})
    m.setdefault("updated_at", 0)
    m.setdefault("live_keys", [])
    for key, a in ASSETS.items():
        m["prices"].setdefault(key, a["fallback"])
        m["ref"].setdefault(key, m["prices"][key])
        m["spark"].setdefault(key, [])
    return m


def _sample(values: list, n: int) -> list:
    if len(values) <= n:
        return list(values)
    step = (len(values) - 1) / (n - 1)
    return [values[int(round(i * step))] for i in range(n)]


async def _fetch_yahoo(session: aiohttp.ClientSession, symbol: str):
    try:
        async with session.get(_YAHOO_URL.format(sym=symbol), headers=_HTTP_HEADERS) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = float(meta["regularMarketPrice"])
        ref = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
        closes = [c for c in (result.get("indicators", {}).get("quote", [{}])[0].get("close") or []) if c]
        return price, ref, closes
    except Exception:
        return None


async def _fetch_metal_alt(session: aiohttp.ClientSession, code: str):
    """مصدر احتياطي للذهب/الفضة (سعر الأونصة فقط)."""
    try:
        async with session.get(f"https://api.gold-api.com/price/{code}", headers=_HTTP_HEADERS) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
        return float(data["price"])
    except Exception:
        return None


async def refresh_market() -> int:
    """يجلب الأسعار الحالية من السوق العالمي ويحفظها. يرجع عدد الأصول اللي انجلبت فعلياً (حقيقية)."""
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = await asyncio.gather(*[_fetch_yahoo(session, a["yahoo"]) for a in ASSETS.values()])
        alts = {}
        for (key, a), res in zip(ASSETS.items(), results):
            if res is None and a.get("alt"):
                alts[key] = await _fetch_metal_alt(session, a["alt"])

    db = load_db()
    m = ensure_market(db)
    live = []
    for (key, a), res in zip(ASSETS.items(), results):
        div = a.get("div", 1.0)
        if res:
            price, ref, closes = res
            m["prices"][key] = price / div
            m["ref"][key] = ref / div
            m["spark"][key] = [c / div for c in _sample(closes, 15)] + [price / div]
            live.append(key)
        elif alts.get(key):
            m["prices"][key] = alts[key] / div
            m["spark"][key] = (m["spark"][key] + [alts[key] / div])[-16:]
            live.append(key)
        else:
            # ما قدرنا نجيب السعر - حركة تقديرية صغيرة بدل ما يتجمد السوق
            m["prices"][key] = max(0.0001, m["prices"][key] * (1 + random.uniform(-0.004, 0.004)))
            m["spark"][key] = (m["spark"][key] + [m["prices"][key]])[-16:]
    m["live_keys"] = live
    m["updated_at"] = time.time()
    save_db(db)
    return len(live)


@tasks.loop(minutes=MARKET_UPDATE_MINUTES)
async def market_updater():
    try:
        count = await refresh_market()
        print(f"📈 [السوق] تم تحديث الأسعار - {count}/{len(ASSETS)} أصل من السوق العالمي مباشرة")
    except Exception as e:
        print(f"⚠️ [السوق] فشل تحديث الأسعار: {type(e).__name__}: {e}")


# =====================================================================
#                      🧮  أدوات تنسيق + صور البنك
# =====================================================================
def fmt_money(n) -> str:
    n = int(round(n))
    return f"-${abs(n):,}" if n < 0 else f"${n:,}"


def fmt_price(p: float) -> str:
    return f"${p:,.2f}" if p >= 1 else f"${p:,.4f}"


def fmt_pct_num(p: float) -> str:
    s = f"{abs(p):.1f}"
    return s[:-2] if s.endswith(".0") else s


_DIGIT_TABLE = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬،", "01234567890123456789,,")


def parse_amount(text: str):
    m = re.search(r"\d+", text.translate(_DIGIT_TABLE).replace(",", ""))
    return int(m.group()) if m else None


_avatar_cache: dict[str, bytes] = {}


async def _avatar_bytes(user) -> bytes:
    asset = user.display_avatar.replace(size=256, format="png")
    if asset.url in _avatar_cache:
        return _avatar_cache[asset.url]
    data = await asset.read()
    if len(_avatar_cache) > 300:
        _avatar_cache.pop(next(iter(_avatar_cache)))
    _avatar_cache[asset.url] = data
    return data


async def _run_sync(fn, *args, **kwargs):
    return await asyncio.get_running_loop().run_in_executor(None, functools.partial(fn, *args, **kwargs))


async def make_card(user, title, main_text, **kw) -> discord.File:
    avatar = await _avatar_bytes(user)
    buf = await _run_sync(_render_card_sync, avatar, user.display_name, title, main_text, **kw)
    return discord.File(buf, filename="card.png")


# =====================================================================
#            🏦  عمليات البنك (كلها متزامنة = ما يصير تعارض بالرصيد)
#   كل دالة act_* ترجع (خطأ أو None, (نص, ملف صورة) أو None)
# =====================================================================
def _bal(db: dict, uid: int) -> int:
    return db["economy"].get(str(uid), STARTING_BALANCE)


async def act_balance(target: discord.Member):
    bal = get_balance(target.id)
    file = await make_card(target, "كشف حساب", "شكراً لاستعمالكم خدماتنا , رصيدك الحالي هو :", amount=fmt_money(bal))
    return None, (f"💵 **{fmt_money(bal)}**", file)


async def act_market():
    db = load_db()
    m = ensure_market(db)
    rows = []
    for key, a in ASSETS.items():
        price, ref = m["prices"][key], m["ref"][key]
        change = (price - ref) / ref * 100 if ref else 0.0
        rows.append((a["name"], fmt_price(price), f"{change:+.2f}%", GREEN if change >= 0 else RED))
    if not m["updated_at"]:
        note = "جاري تحميل الأسعار من السوق العالمي..."
    else:
        t = datetime.fromtimestamp(m["updated_at"], timezone(timedelta(hours=3))).strftime("%H:%M")
        live = len(m["live_keys"])
        status = ("أسعار مباشرة من السوق العالمي" if live == len(ASSETS)
                  else "بعض الأسعار تقديرية مؤقتاً" if live else "السوق غير متصل - أسعار تقديرية")
        note = f"{status} • آخر تحديث {t} (GMT+3)"
    buf = await _run_sync(_render_table_sync, "أسعار السوق العالمي", ["الأصل", "السعر", "التغيّر اليومي"], rows, note, "chart_up")
    return None, (f"📊 تتحدث الأسعار كل {MARKET_UPDATE_MINUTES} دقايق • للشراء: `شراء ذهب 500` وللبيع: `بيع ذهب`",
                  discord.File(buf, filename="market.png"))


async def act_portfolio(user: discord.Member):
    db = load_db()
    m = ensure_market(db)
    cash = _bal(db, user.id)
    holdings = db["portfolio"].get(str(user.id), {})
    if not holdings:
        file = await make_card(user, "حصالتك", "ما عندك أي استثمارات حالياً , ابدأ بـ: شراء ذهب 500", amount=fmt_money(cash))
        return None, (f"💼 سيولتك: **{fmt_money(cash)}**", file)
    rows, total_value, total_cost = [], 0.0, 0.0
    for key, pos in holdings.items():
        if key not in ASSETS:
            continue
        value = pos["units"] * m["prices"][key]
        pnl = (value - pos["cost"]) / pos["cost"] * 100 if pos["cost"] else 0.0
        total_value += value
        total_cost += pos["cost"]
        rows.append((ASSETS[key]["name"], fmt_money(value), f"{pnl:+.1f}%", GREEN if pnl >= 0 else RED))
    total_pnl = (total_value - total_cost) / total_cost * 100 if total_cost else 0.0
    rows.append(("السيولة (الكاش)", fmt_money(cash), "", None, True))
    rows.append(("الإجمالي", fmt_money(cash + total_value), f"{total_pnl:+.1f}%", GREEN if total_pnl >= 0 else RED, True))
    buf = await _run_sync(_render_table_sync, f"حصالة {_trunc(user.display_name, 14)}",
                          ["الأصل", "القيمة الحالية", "الربح / الخسارة"], rows, None, "coins")
    return None, (f"💼 {user.mention}", discord.File(buf, filename="portfolio.png"))


async def act_buy(user: discord.Member, key: str, amount: int):
    if key not in ASSETS:
        return "❌ هذا الأصل غير موجود. اكتب `سوق` تشوف الأصول المتاحة.", None
    db = load_db()
    m = ensure_market(db)
    bal = _bal(db, user.id)
    if amount < 1:
        return "❌ المبلغ لازم يكون 1$ أو أكثر.", None
    if amount > bal:
        return f"❌ رصيدك ما يكفي! معك {fmt_money(bal)} بس.", None
    price = m["prices"][key]
    units = amount / price
    pos = db["portfolio"].setdefault(str(user.id), {}).setdefault(key, {"units": 0.0, "cost": 0.0})
    pos["units"] += units
    pos["cost"] += amount
    db["economy"][str(user.id)] = bal - amount
    save_db(db)
    a = ASSETS[key]
    file = await make_card(user, "عملية شراء ناجحة", f"اشتريت : {a['name']}", amount=fmt_money(amount),
                           side=None, icon="chart_up", footer=True)
    return None, (f"✅ {fmt_money(amount)} ← {units:,.6g} من {a['name']} بسعر {fmt_price(price)} • رصيدك: **{fmt_money(bal - amount)}**", file)


async def act_sell(user: discord.Member, key: str, amount):
    if key not in ASSETS:
        return "❌ هذا الأصل غير موجود. اكتب `سوق` تشوف الأصول المتاحة.", None
    db = load_db()
    m = ensure_market(db)
    pf = db["portfolio"].get(str(user.id), {})
    pos = pf.get(key)
    if not pos or pos["units"] <= 0:
        return f"❌ ما عندك أي استثمار في {ASSETS[key]['name']}.", None
    price = m["prices"][key]
    value = pos["units"] * price
    if amount is None or amount >= value - 0.5:
        sold_units, cost_part = pos["units"], pos["cost"]
    else:
        if amount < 1:
            return "❌ المبلغ لازم يكون 1$ أو أكثر.", None
        sold_units = amount / price
        cost_part = pos["cost"] * (sold_units / pos["units"])
    proceeds = int(round(sold_units * price))
    pnl = proceeds - cost_part
    pct = pnl / cost_part * 100 if cost_part > 0 else 0.0

    pos["units"] -= sold_units
    pos["cost"] -= cost_part
    if pos["units"] <= 1e-9:
        pf.pop(key, None)
    if not pf:
        db["portfolio"].pop(str(user.id), None)
    new_bal = _bal(db, user.id) + proceeds
    db["economy"][str(user.id)] = new_bal
    save_db(db)

    up = pct >= 0
    spark = list(m["spark"].get(key) or [])
    if len(spark) < 4:
        spark = [price * (1 - 0.01 * (8 - i) * (1 if up else -1)) for i in range(9)]
    chart = {"values": spark, "up": up, "tag": "ربح" if up else "خسارة", "pct_text": f"{fmt_pct_num(pct)}٪"}
    main = f"استثمرت في : {ASSETS[key]['name']} و{'ربحت' if up else 'خسرت'} بنسبة {fmt_pct_num(pct)}٪"
    sign = "+" if pnl >= 0 else "-"
    lines = [("قيمة البيع :", fmt_money(proceeds), (255, 255, 255), 640),
             ("الربح :" if up else "الخسارة :", f"{sign}{fmt_money(abs(pnl))}", GREEN if up else RED, 730)]
    file = await make_card(user, "استثمار رابح" if up else "استثمار خاسر", main,
                           icon="chart_up" if up else "chart_down", chart=chart, lines=lines)
    return None, (f"{'📈' if up else '📉'} رصيدك الحين: **{fmt_money(new_bal)}**", file)


async def act_transfer(sender: discord.Member, receiver: discord.Member, amount: int):
    if receiver.bot:
        return "❌ ما تقدر تحول فلوس لبوت.", None
    if receiver.id == sender.id:
        return "❌ ما تقدر تحول لنفسك!", None
    if amount < 1:
        return "❌ المبلغ لازم يكون 1$ أو أكثر.", None
    db = load_db()
    sender_bal = _bal(db, sender.id)
    if amount > sender_bal:
        return f"❌ رصيدك ما يكفي! معك {fmt_money(sender_bal)} بس.", None
    db["economy"][str(sender.id)] = sender_bal - amount
    db["economy"][str(receiver.id)] = _bal(db, receiver.id) + amount
    save_db(db)
    file = await make_card(sender, "تم التحويل بنجاح", f"تم تحويل المبلغ الى : {receiver.display_name}",
                           amount=fmt_money(amount), icon="transfer")
    return None, (f"💸 {receiver.mention} وصلك تحويل من {sender.mention} • رصيدك الحين: **{fmt_money(sender_bal - amount)}**", file)


async def act_dice(user: discord.Member, bet: int):
    db = load_db()
    bal = _bal(db, user.id)
    if bet < 1:
        return "❌ الرهان لازم يكون 1$ أو أكثر.", None
    if bet > bal:
        return f"❌ رصيدك ما يكفي! معك {fmt_money(bal)} بس.", None
    bot_roll, user_roll = random.randint(1, 6), random.randint(1, 6)
    if user_roll > bot_roll:
        outcome, delta, result_text, bet_text = "win", bet, "فزت علي", f"+{fmt_money(bet)}"
    elif user_roll < bot_roll:
        outcome, delta, result_text, bet_text = "lose", -bet, "فزت عليك", f"-{fmt_money(bet)}"
    else:
        outcome, delta, result_text, bet_text = "tie", 0, "تعادل", "$0"
    new_bal = bal + delta
    db["economy"][str(user.id)] = new_bal
    save_db(db)
    bot_av = await _avatar_bytes(bot.user)
    user_av = await _avatar_bytes(user)
    buf = await _run_sync(_render_dice_sync, bot_av, user_av, bot_roll, user_roll, outcome, result_text, bet_text)
    return None, (f"🎲 {user.mention} • رصيدك: **{fmt_money(new_bal)}**", discord.File(buf, filename="dice.png"))


async def act_status(user: discord.Member):
    """جدول جاهزية أوامر البنك للعضو - مؤقت لكل أمر + أقرب وقت جاهزية."""
    rows, ready, soonest = [], 0, None
    for action in BANK_STATUS_ORDER:
        remaining = get_cooldown_remaining(user.id, action)
        if remaining > 0:
            rows.append((action, "قيد الانتظار", format_clock(remaining), RED))
            soonest = remaining if soonest is None else min(soonest, remaining)
        else:
            ready += 1
            rows.append((action, "جاهز", "00:00", GREEN))
    note = f"{_trunc(user.display_name, 16)} • {ready}/{len(BANK_STATUS_ORDER)} أوامر جاهزة"
    buf = await _run_sync(_render_table_sync, "حالة الأوامر", ["الأمر", "الحالة", "الوقت المتبقي"], rows, note, "coins")
    if soonest is None:
        text = f"✅ {user.mention} • كل أوامرك جاهزة للاستخدام"
    else:
        text = f"⏱️ {user.mention} • أقرب أمر يجهز <t:{int(_now_ts() + soonest)}:R>"
    return None, (text, discord.File(buf, filename="status.png"))


# =====================================================================
#                       📤  إرسال النتائج (سلاش + نص)
# =====================================================================
async def _deliver_interaction(interaction: discord.Interaction, err, result):
    if err:
        try:
            await interaction.delete_original_response()
        except Exception:
            pass
        return await interaction.followup.send(err, ephemeral=True)
    text, file = result
    if file:
        await interaction.followup.send(content=text, file=file)
    else:
        await interaction.followup.send(content=text)


async def _bank_guard(interaction: discord.Interaction) -> bool:
    if BANK_CHANNEL_ID and interaction.channel_id != BANK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ أوامر البنك تشتغل بس بروم <#{BANK_CHANNEL_ID}>.", ephemeral=True)
        return False
    return True


# =====================================================================
#          ⌨️  أوامر نصية بروم البنك (نفس أسلوب: فلوس / تحويل ...)
# =====================================================================
BANK_TEXT_TRIGGERS = {
    "فلوس": "balance", "رصيد": "balance", "رصيدي": "balance",
    "سوق": "market", "اسعار": "market", "أسعار": "market",
    "حصالتي": "portfolio", "حصالة": "portfolio",
    "تحويل": "transfer", "نرد": "dice", "الغام": "mines", "ألغام": "mines", "وقت": "status", "الوقت": "status", "شراء": "buy", "اشتري": "buy", "بيع": "sell",
}


def _norm_word(w: str) -> str:
    w = w.strip().lower()
    return w[2:] if w.startswith("ال") and len(w) > 3 else w


def find_asset_key(words: list[str]):
    for w in words:
        nw = _norm_word(w)
        for key, a in ASSETS.items():
            if nw in {_norm_word(x) for x in a["aliases"]}:
                return key
    return None


async def handle_bank_text(message: discord.Message) -> bool:
    """يرجع True لو الرسالة كانت أمر بنك وتمت معالجتها."""
    if BANK_CHANNEL_ID and message.channel.id != BANK_CHANNEL_ID:
        return False
    if not isinstance(message.author, discord.Member):
        return False
    parts = message.content.strip().split()
    if parts and parts[0] in EXTRA_BANK_ACTIONS:
        rest0 = [p for p in parts[1:] if not re.fullmatch(r"<@!?\d+>", p)]
        return await handle_extra_bank(message, parts[0], rest0)
    action = BANK_TEXT_TRIGGERS.get(parts[0]) if parts else None
    if not action:
        return False

    rest = [p for p in parts[1:] if not re.fullmatch(r"<@!?\d+>", p)]
    amount = parse_amount_ctx(rest, message.author.id)
    mention = next((m for m in message.mentions if isinstance(m, discord.Member) and not m.bot), None)
    author = message.author

    # فحص الانتظار قبل تنفيذ الأوامر اللي لها كولداون
    cd_action = {"dice": "نرد", "mines": "ألغام"}.get(action)
    if cd_action and not (action == "dice" and amount is None):
        notice = cooldown_notice(author.id, cd_action)
        if notice:
            await message.reply(notice, mention_author=False)
            return True

    try:
        async with message.channel.typing():
            if action == "balance":
                err, res = await act_balance(mention or author)
            elif action == "market":
                err, res = await act_market()
            elif action == "portfolio":
                err, res = await act_portfolio(mention or author)
            elif action == "transfer":
                if not mention or amount is None:
                    err, res = "الاستخدام: `تحويل @العضو 500`", None
                else:
                    err, res = await act_transfer(author, mention, amount)
            elif action == "status":
                err, res = await act_status(author)
            elif action == "mines":
                await cmd_mines(message, amount)
                return True
            elif action == "dice":
                if amount is None:
                    err, res = "الاستخدام: `نرد 100`", None
                else:
                    set_cooldown(author.id, "نرد")          # نحجز الانتظار أولاً عشان ما يتخطاه بالرسائل المتتالية
                    err, res = await act_dice(author, amount)
                    if err:
                        clear_cooldown(author.id, "نرد")    # العملية فشلت (رصيد/رهان) = ما نحسب عليه انتظار
            elif action in ("buy", "sell"):
                key = find_asset_key(rest)
                if not key:
                    await cmd_shop(message, sell=(action == "sell"))     # بدون اسم أصل = متجر الممتلكات
                    return True
                elif action == "buy":
                    err, res = (await act_buy(author, key, amount)) if amount else ("الاستخدام: `شراء ذهب 500`", None)
                else:
                    err, res = await act_sell(author, key, amount)
    except Exception as e:
        import traceback
        traceback.print_exc()
        err, res = f"⚠️ صار خطأ بالبنك: {e}", None

    if err:
        await message.reply(err, mention_author=False)
    else:
        text, file = res
        if file:
            await message.reply(content=text, file=file, mention_author=False)
        else:
            await message.reply(content=text, mention_author=False)
    return True


# =====================================================================
#      ⌨️  أوامر نصية بدون سلاش: لفل / مسح / تصويت
# =====================================================================
async def handle_text_commands(message: discord.Message) -> bool:
    if not message.guild or not isinstance(message.author, discord.Member):
        return False
    parts = message.content.strip().split(maxsplit=1)
    word = parts[0] if parts else ""
    if word not in ("لفل", "مسح", "تصويت"):
        return False
    arg = parts[1].strip() if len(parts) > 1 else ""
    author, channel = message.author, message.channel
    reply = lambda *a, **k: message.reply(*a, mention_author=False, **k)

    try:
        if word == "لفل":
            db = load_db()
            data = db["levels"].get(str(author.id), {"xp": 0, "level": 0})
            needed = xp_needed_for_level(data["level"] + 1)
            percent = int(data["xp"] / needed * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            embed = discord.Embed(title=f"📈 مستوى {author.display_name}", color=MAIN_COLOR)
            embed.set_thumbnail(url=author.display_avatar.url)
            embed.add_field(name="المستوى الحالي", value=f"**{data['level']}**", inline=True)
            embed.add_field(name="نقاط الخبرة", value=f"{data['xp']} / {needed}", inline=True)
            embed.add_field(name="التقدم", value=f"{bar} {percent}%", inline=False)
            await reply(embed=embed)

        elif word == "مسح":
            if not author.guild_permissions.administrator:
                await reply("❌ هذا الأمر للإدارة فقط.")
                return True
            amount = parse_amount(arg)
            if not amount or amount <= 0:
                await reply("الاستخدام: `مسح 50` — أو `مسح 50 الكل` لمسح كل رومات السيرفر")
                return True
            amount = min(amount, 1000)
            if "الكل" in arg:
                embed = discord.Embed(
                    title="⚠️ تأكيد المسح الجماعي",
                    description=(f"بتحذف حتى **{amount}** رسالة من **كل رومات السيرفر** دفعة وحدة.\n"
                                 "هذا الإجراء لا يمكن التراجع عنه. هل أنت متأكد؟"),
                    color=DANGER_COLOR)
                await reply(embed=embed, view=ConfirmClearAllView(amount))
            else:
                deleted = await channel.purge(limit=amount + 1)   # +1 لرسالة الأمر نفسها
                await channel.send(f"✅ تم حذف {max(0, len(deleted) - 1)} رسالة من هذا الروم.", delete_after=5)

        elif word == "تصويت":
            items = [x.strip() for x in arg.split("|") if x.strip()]
            if not 3 <= len(items) <= 5:
                await reply("الاستخدام: `تصويت السؤال | خيار1 | خيار2 | خيار3` (من 2 إلى 4 خيارات)")
                return True
            embed = discord.Embed(title=f"📊 {items[0]}", color=MAIN_COLOR)
            embed.set_footer(text=f"طرحه: {author}")
            view = PollView(items[1:])
            await channel.send(embed=view._build_embed(embed), view=view)
    except discord.Forbidden:
        await reply("❌ البوت ما عنده صلاحية كافية لتنفيذ هذا الأمر.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await reply(f"⚠️ صار خطأ: {e}")
    return True


# =====================================================================
#                  🎮  لعبة الألغام (Mines) - النتيجة بصورة
# =====================================================================
#        🍒🎮🎨  رسومات الألعاب (فواكه / حجرة ورقة مقص / لون) + أيقونات إضافية
# =====================================================================
_draw_icon_base = _draw_icon


def _draw_icon(d, R, icon: str):
    W = (255, 255, 255, 235)
    if icon == "shield":
        pts = [(1810, 120), (1880, 150), (1872, 230), (1810, 296), (1748, 230), (1740, 150)]
        d.polygon([(R.x(x), R.y(y)) for x, y in pts], fill=W)
        d.line([(R.x(1778), R.y(205)), (R.x(1802), R.y(232)), (R.x(1846), R.y(172))], fill=BRAND_BROWN + (255,), width=int(R.n(14)), joint="curve")
    elif icon == "bolt":
        pts = [(1826, 112), (1752, 218), (1806, 218), (1790, 306), (1884, 190), (1826, 190)]
        d.polygon([(R.x(x), R.y(y)) for x, y in pts], fill=W)
    elif icon == "gold":
        for bx, by, w in ((1800, 130, 70), (1750, 205, 70), (1850, 205, 70)):
            pts = [(bx - w * .5, by + 62), (bx - w * .38, by), (bx + w * .38, by), (bx + w * .5, by + 62)]
            d.polygon([(R.x(x), R.y(y)) for x, y in pts], fill=W)
    elif icon == "trophy":
        d.rounded_rectangle(R.box(1770, 120, 1850, 215), radius=int(R.n(22)), fill=W)
        d.rectangle(R.box(1802, 215, 1818, 258), fill=W)
        d.rounded_rectangle(R.box(1770, 258, 1850, 282), radius=int(R.n(8)), fill=W)
        d.arc(R.box(1730, 128, 1790, 188), 90, 270, fill=W, width=int(R.n(9)))
        d.arc(R.box(1830, 128, 1890, 188), -90, 90, fill=W, width=int(R.n(9)))
    elif icon == "dice":
        d.rounded_rectangle(R.box(1745, 130, 1875, 260), radius=int(R.n(26)), fill=W)
        for px, py in ((1775, 160), (1845, 160), (1810, 195), (1775, 230), (1845, 230)):
            d.ellipse(R.box(px - 11, py - 11, px + 11, py + 11), fill=BRAND_BROWN + (255,))
    else:
        _draw_icon_base(d, R, icon)


# ------------------------- فواكه -------------------------
FRUIT_NAMES = ["cherry", "lemon", "grape", "melon", "berry", "star"]


def _draw_fruit(d, cx, cy, s, name):
    if name == "cherry":
        d.line([(cx - .14 * s, cy + .12 * s), (cx + .04 * s, cy - .34 * s)], fill=(70, 150, 60, 255), width=max(2, int(s * .045)))
        d.line([(cx + .18 * s, cy + .16 * s), (cx + .04 * s, cy - .34 * s)], fill=(70, 150, 60, 255), width=max(2, int(s * .045)))
        d.ellipse((cx + .04 * s - .1 * s, cy - .4 * s, cx + .04 * s + .26 * s, cy - .2 * s), fill=(80, 170, 70, 255))
        for ox, oy in ((-.17, .18), (.2, .22)):
            x, y, r = cx + ox * s, cy + oy * s, .2 * s
            d.ellipse((x - r, y - r, x + r, y + r), fill=(206, 24, 44, 255), outline=(120, 10, 24, 255), width=max(1, int(s * .02)))
            d.ellipse((x - r * .55, y - r * .6, x - r * .15, y - r * .2), fill=(255, 150, 160, 220))
    elif name == "lemon":
        d.ellipse((cx - .36 * s, cy - .22 * s, cx + .36 * s, cy + .22 * s), fill=(248, 220, 50, 255), outline=(190, 150, 20, 255), width=max(1, int(s * .02)))
        d.polygon([(cx - .36 * s, cy), (cx - .46 * s, cy - .04 * s), (cx - .36 * s, cy + .05 * s)], fill=(248, 220, 50, 255))
        d.polygon([(cx + .36 * s, cy), (cx + .46 * s, cy + .04 * s), (cx + .36 * s, cy - .05 * s)], fill=(248, 220, 50, 255))
        d.ellipse((cx - .2 * s, cy - .16 * s, cx + .02 * s, cy - .06 * s), fill=(255, 250, 170, 200))
        d.ellipse((cx + .02 * s, cy - .34 * s, cx + .28 * s, cy - .2 * s), fill=(80, 170, 70, 255))
    elif name == "grape":
        pos = [(-.2, -.12), (0, -.12), (.2, -.12), (-.1, .06), (.1, .06), (0, .24)]
        for ox, oy in pos:
            x, y, r = cx + ox * s, cy + oy * s, .125 * s
            d.ellipse((x - r, y - r, x + r, y + r), fill=(130, 60, 190, 255), outline=(80, 30, 130, 255), width=max(1, int(s * .015)))
            d.ellipse((x - r * .6, y - r * .65, x - r * .1, y - r * .2), fill=(200, 150, 240, 200))
        d.line([(cx, cy - .24 * s), (cx + .04 * s, cy - .4 * s)], fill=(90, 150, 60, 255), width=max(2, int(s * .05)))
        d.ellipse((cx + .02 * s, cy - .42 * s, cx + .26 * s, cy - .3 * s), fill=(80, 170, 70, 255))
    elif name == "melon":
        r = .38 * s
        d.pieslice((cx - r, cy - r * .7, cx + r, cy + r * 1.3), 0, 180, fill=(40, 130, 60, 255))
        r2 = r * .86
        d.pieslice((cx - r2, cy - r * .7, cx + r2, cy + r * 1.3 - r * .14), 0, 180, fill=(236, 70, 86, 255))
        for ox, oy in ((-.18, .2), (0, .3), (.18, .2), (-.06, .12), (.1, .12)):
            d.ellipse((cx + ox * s - 3, cy + oy * s - 5, cx + ox * s + 3, cy + oy * s + 5), fill=(30, 20, 20, 255))
    elif name == "berry":
        pts = [(cx - .3 * s, cy - .16 * s), (cx + .3 * s, cy - .16 * s), (cx + .2 * s, cy + .12 * s), (cx, cy + .38 * s), (cx - .2 * s, cy + .12 * s)]
        d.polygon(pts, fill=(226, 36, 56, 255), outline=(140, 12, 28, 255))
        d.ellipse((cx - .3 * s, cy - .3 * s, cx + .3 * s, cy - .02 * s), fill=(226, 36, 56, 255))
        for ox, oy in ((-.14, -.04), (.04, -.06), (.16, .04), (-.04, .1), (-.1, .2 - .06), (.06, .22)):
            d.ellipse((cx + ox * s - 2.5, cy + oy * s - 3.5, cx + ox * s + 2.5, cy + oy * s + 3.5), fill=(255, 226, 120, 255))
        d.polygon([(cx - .22 * s, cy - .22 * s), (cx, cy - .12 * s), (cx + .22 * s, cy - .22 * s), (cx + .08 * s, cy - .34 * s), (cx - .08 * s, cy - .34 * s)], fill=(80, 170, 70, 255))
    else:  # star
        pts = []
        for i in range(10):
            rr = .42 * s if i % 2 == 0 else .18 * s
            a = math.radians(-90 + i * 36)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=(255, 208, 50, 255), outline=(190, 130, 20, 255))
        d.polygon([(cx, cy - .3 * s), (cx + .08 * s, cy - .08 * s), (cx - .08 * s, cy - .08 * s)], fill=(255, 240, 150, 255))


def _render_slots_sync(user_avatar, user_name, final, result_text, amount_text, outcome) -> io.BytesIO:
    """GIF: 3 بكرات تدور وتوقف تباعاً. final = 3 أسماء فواكه. outcome: win/lose/jackpot"""
    k = 2
    W, H = 700, 430
    sym_h = 124
    reel_w, reel_h = 170, 150
    xs = [86, 265, 444]
    top = 118
    bg = _radial_gradient((W * k, H * k), (W * k * .5, H * k * .4), [(0, (96, 50, 28)), (W * k * .6, (46, 24, 14)), (W * k, (18, 9, 5))]).convert("RGBA")
    bd = ImageDraw.Draw(bg)
    bd.rounded_rectangle((6 * k, 6 * k, W * k - 6 * k, H * k - 6 * k), radius=34 * k, outline=(224, 186, 90, 255), width=int(3 * k))
    bd.rounded_rectangle((13 * k, 13 * k, W * k - 13 * k, H * k - 13 * k), radius=28 * k, outline=BRAND_BROWN + (255,), width=int(2 * k))
    try:
        av = _circle_avatar(user_avatar, 50 * k)
        bd.ellipse((28 * k - 3 * k, 26 * k - 3 * k, 28 * k + 53 * k, 26 * k + 53 * k), fill=(224, 186, 90, 255))
        bg.alpha_composite(av, (28 * k, 26 * k))
    except Exception:
        pass
    _text_fit(bd, (92 * k, 52 * k), _trunc(user_name, 16), int(22 * k), (255, 255, 255, 255), "lm", 220 * k)
    _text(bd, (W * k - 34 * k, 52 * k), "عجلة الفواكه", int(32 * k), (236, 196, 92, 255), "rm")
    # إطار الماكينة
    bd.rounded_rectangle((60 * k, top * k - 18 * k, 640 * k, (top + reel_h) * k + 18 * k), radius=26 * k, fill=(22, 12, 8, 255), outline=(224, 186, 90, 255), width=int(3 * k))

    def strip_for(i, stop_sym):
        random.seed()
        seq = [random.choice(FRUIT_NAMES) for _ in range(14 + i * 5)] + [stop_sym]
        return seq

    strips = [strip_for(i, final[i]) for i in range(3)]
    stops = [14, 20, 26]
    total = 34
    frames, durs = [], []
    for fi in range(total + 8):
        im = bg.copy()
        d = ImageDraw.Draw(im)
        for i, x in enumerate(xs):
            rx0, ry0 = x * k, top * k
            win = Image.new("RGBA", (reel_w * k, reel_h * k), (250, 244, 228, 255))
            wd = ImageDraw.Draw(win)
            seq = strips[i]
            stopped = fi >= stops[i]
            prog = min(1.0, fi / stops[i])
            ease = 1 - (1 - prog) ** 2.4
            pos = ease * (len(seq) - 1)                       # أي رمز بالمنتصف
            base = int(math.floor(pos))
            frac = pos - base
            for dd in (-1, 0, 1, 2):
                si = base + dd
                if 0 <= si < len(seq):
                    cyy = (reel_h / 2 + (dd - frac) * -sym_h * -1) if False else (reel_h / 2 - (frac - dd) * sym_h)
                    _draw_fruit(wd, reel_w * k / 2, cyy * k, 96 * k, seq[si])
            if not stopped:
                win = Image.blend(win, win.filter(ImageFilter.GaussianBlur(2.4 * k)), .5)
            # ظل علوي/سفلي
            sh = Image.new("RGBA", win.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(sh)
            for yy in range(int(26 * k)):
                a = int(120 * (1 - yy / (26 * k)))
                sd.line([(0, yy), (win.width, yy)], fill=(40, 20, 10, a))
                sd.line([(0, win.height - 1 - yy), (win.width, win.height - 1 - yy)], fill=(40, 20, 10, a))
            win.alpha_composite(sh)
            m = Image.new("L", win.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, win.width - 1, win.height - 1), radius=16 * k, fill=255)
            im.paste(win, (rx0, ry0), m)
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((rx0, ry0, rx0 + reel_w * k, ry0 + reel_h * k), radius=16 * k, outline=(224, 186, 90, 255), width=int(2.5 * k))
        # خط الفوز
        d.line([(66 * k, (top + reel_h / 2) * k), (634 * k, (top + reel_h / 2) * k)], fill=(255, 90, 80, 90), width=int(2 * k))
        done = fi >= stops[2] + 1
        tone = {"win": (110, 220, 140), "jackpot": (255, 214, 80), "lose": (240, 110, 100)}[outcome]
        if done:
            _text(d, (W * k / 2, 345 * k), result_text, int(34 * k), tone + (255,), "mm", stroke_width=int(2 * k), stroke_fill=(0, 0, 0, 255))
            _text(d, (W * k / 2, 390 * k), amount_text, int(30 * k), tone + (255,), "mm", stroke_width=int(2 * k), stroke_fill=(0, 0, 0, 255))
        else:
            _text(d, (W * k / 2, 360 * k), "تدور...", int(30 * k), (236, 196, 92, 255), "mm")
        frames.append(im.resize((W, H), Image.BOX).convert("RGB"))
        durs.append(70 if fi < stops[2] else 90)
    durs[-1] = 60000
    pal = frames[-1].quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    buf = io.BytesIO()
    q[0].save(buf, format="GIF", save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=False, disposal=1)
    buf.seek(0)
    return buf


# ------------------------- حجرة ورقة مقص -------------------------
def _draw_rps(d, cx, cy, s, kind):
    if kind == "rock":
        pts = [(-.34, .1), (-.26, -.18), (-.04, -.32), (.24, -.24), (.36, .02), (.28, .26), (0, .34), (-.26, .28)]
        d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=(150, 154, 164, 255), outline=(70, 72, 82, 255))
        d.polygon([(cx + x * s, cy + y * s) for x, y in [(-.2, -.1), (-.02, -.24), (.14, -.18), (0, -.02)]], fill=(196, 200, 210, 255))
        d.line([(cx - .12 * s, cy + .12 * s), (cx + .06 * s, cy + .24 * s)], fill=(96, 98, 108, 255), width=max(2, int(s * .03)))
    elif kind == "paper":
        d.rounded_rectangle((cx - .26 * s, cy - .36 * s, cx + .26 * s, cy + .36 * s), radius=int(s * .05), fill=(250, 250, 248, 255), outline=(150, 150, 150, 255), width=max(2, int(s * .02)))
        for i in range(5):
            y = cy - .2 * s + i * .11 * s
            d.line([(cx - .16 * s, y), (cx + .16 * s, y)], fill=(170, 190, 220, 255), width=max(2, int(s * .025)))
        d.polygon([(cx + .26 * s, cy - .36 * s), (cx + .26 * s, cy - .18 * s), (cx + .08 * s, cy - .36 * s)], fill=(214, 214, 214, 255))
    else:
        for sgn in (-1, 1):
            blade = [(cx, cy), (cx + sgn * .3 * s, cy - .36 * s), (cx + sgn * .38 * s, cy - .3 * s), (cx + sgn * .08 * s, cy + .02 * s)]
            d.polygon(blade, fill=(216, 220, 230, 255), outline=(90, 94, 106, 255))
            hx, hy = cx - sgn * .17 * s, cy + .27 * s
            d.ellipse((hx - .12 * s, hy - .12 * s, hx + .12 * s, hy + .12 * s), outline=(226, 60, 70, 255), width=max(3, int(s * .06)))
            d.line([(cx, cy), (hx + sgn * .02 * s, hy - .1 * s)], fill=(226, 60, 70, 255), width=max(3, int(s * .05)))
        d.ellipse((cx - .04 * s, cy - .04 * s, cx + .04 * s, cy + .04 * s), fill=(60, 60, 70, 255))


def _render_rps_sync(bot_avatar, user_avatar, user_name, user_pick, bot_pick, outcome, result_text, amount_text) -> io.BytesIO:
    k = 2
    W, H = 760, 400
    bg = _radial_gradient((W * k, H * k), (W * k * .5, H * k * .4), [(0, (96, 50, 28)), (W * k * .6, (46, 24, 14)), (W * k, (18, 9, 5))]).convert("RGBA")
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle((6 * k, 6 * k, W * k - 6 * k, H * k - 6 * k), radius=34 * k, outline=(224, 186, 90, 255), width=int(3 * k))
    d.rounded_rectangle((13 * k, 13 * k, W * k - 13 * k, H * k - 13 * k), radius=28 * k, outline=BRAND_BROWN + (255,), width=int(2 * k))
    win_side = "user" if outcome == "win" else "bot" if outcome == "lose" else None
    for who, cx, av_b, pick, label in (("bot", 180, bot_avatar, bot_pick, "البنك"), ("user", 580, user_avatar, user_pick, _trunc(user_name, 12))):
        ring = GOLD if win_side == who else BRAND_BROWN
        d.rounded_rectangle(((cx - 130) * k, 92 * k, (cx + 130) * k, 322 * k), radius=26 * k, fill=(30, 16, 10, 255), outline=ring + (255,), width=int(3 * k))
        try:
            av = _circle_avatar(av_b, 54 * k)
            d.ellipse(((cx - 27 - 3) * k, 100 * k - 3 * k, (cx + 27 + 3) * k, 154 * k + 3 * k), fill=ring + (255,))
            bg.alpha_composite(av, (int((cx - 27) * k), 100 * k))
            d = ImageDraw.Draw(bg)
        except Exception:
            pass
        _draw_rps(d, cx * k, 235 * k, 150 * k, pick)
        _text_fit(d, (cx * k, 306 * k), label, int(20 * k), (255, 255, 255, 255), "mm", 220 * k)
    _text(d, (W * k / 2, 215 * k), "VS", int(40 * k), (236, 196, 92, 255), "mm", stroke_width=int(2 * k), stroke_fill=(0, 0, 0, 255))
    tone = {"win": GREEN, "lose": RED, "tie": (230, 230, 230)}[outcome]
    _text(d, (W * k / 2, 52 * k), result_text, int(34 * k), (255, 255, 255, 255), "mm", stroke_width=int(3 * k), stroke_fill=(0, 0, 0, 255))
    _text(d, (W * k / 2, 358 * k), amount_text, int(34 * k), tone + (255,), "mm", stroke_width=int(3 * k), stroke_fill=(0, 0, 0, 255))
    return _to_png(bg, (W, H))


# ------------------------- لون (أي لون أكثر بالشبكة؟) -------------------------
COLOR_RGB = {"red": (214, 56, 60), "blue": (58, 108, 224), "orange": (244, 150, 38), "purple": (150, 80, 212), "green": (66, 182, 92)}


def _render_colors_sync(grid, rows, cols, user_name, user_avatar, attempts_text, reveal=None) -> io.BytesIO:
    """grid: قائمة مفاتيح الألوان. reveal: None أو (مفتاح_الصح, اخترت_صح؟, نص_النتيجة, نص_المبلغ)"""
    k = 2
    cell, gap = 52, 8
    gw = cols * cell + (cols - 1) * gap
    gh = rows * cell + (rows - 1) * gap
    W, H = gw + 100, gh + 190
    bg = _radial_gradient((W * k, H * k), (W * k * .5, H * k * .3), [(0, (92, 50, 28)), (W * k * .6, (46, 24, 14)), (W * k, (18, 9, 5))]).convert("RGBA")
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle((6 * k, 6 * k, W * k - 6 * k, H * k - 6 * k), radius=34 * k, outline=(224, 186, 90, 255), width=int(3 * k))
    d.rounded_rectangle((13 * k, 13 * k, W * k - 13 * k, H * k - 13 * k), radius=28 * k, outline=BRAND_BROWN + (255,), width=int(2 * k))
    try:
        av = _circle_avatar(user_avatar, 50 * k)
        d.ellipse((28 * k - 3 * k, 26 * k - 3 * k, 28 * k + 53 * k, 26 * k + 53 * k), fill=(224, 186, 90, 255))
        bg.alpha_composite(av, (28 * k, 26 * k))
        d = ImageDraw.Draw(bg)
    except Exception:
        pass
    _text_fit(d, (92 * k, 52 * k), _trunc(user_name, 14), int(22 * k), (255, 255, 255, 255), "lm", 180 * k)
    _text(d, (W * k - 34 * k, 40 * k), "خمن اللون", int(30 * k), (236, 196, 92, 255), "rm")
    _text(d, (W * k - 34 * k, 70 * k), "أي لون أكثر عدداً بالشبكة؟", int(16 * k), (230, 205, 150, 255), "rm")
    x0, y0 = 50, 100
    for i, ck in enumerate(grid):
        r, c = divmod(i, cols)
        x, y = (x0 + c * (cell + gap)) * k, (y0 + r * (cell + gap)) * k
        col = COLOR_RGB[ck]
        dim = reveal is not None and ck != reveal[0]
        fill = tuple(int(v * (.38 if dim else 1)) for v in col) + (255,)
        d.rounded_rectangle((x, y, x + cell * k, y + cell * k), radius=12 * k, fill=fill, outline=(255, 255, 255, 60 if not dim else 25), width=int(1.4 * k))
        if not dim:
            gl = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle((x + 5 * k, y + 4 * k, x + (cell - 5) * k, y + 20 * k), radius=8 * k, fill=(255, 255, 255, 46))
            bg.alpha_composite(gl)
            d = ImageDraw.Draw(bg)
    fy = (y0 + gh + 40) * k
    if reveal is None:
        _text(d, (W * k / 2, fy), attempts_text, int(20 * k), (232, 210, 160, 255), "mm")
        _text(d, (W * k / 2, fy + 40 * k), "اختر اللون من الأزرار تحت", int(18 * k), (255, 255, 255, 230), "mm")
    else:
        ok = reveal[1]
        tone = GREEN if ok else RED
        _text(d, (W * k / 2, fy - 4 * k), reveal[2], int(28 * k), tone + (255,), "mm", stroke_width=int(2 * k), stroke_fill=(0, 0, 0, 255))
        _text(d, (W * k / 2, fy + 38 * k), reveal[3], int(24 * k), (255, 255, 255, 255), "mm", stroke_width=int(2 * k), stroke_fill=(0, 0, 0, 255))
    return _to_png(bg, (W, H))


# =====================================================================
#        🎡  روليت كازينو واقعي (GIF متحرك: عجلة + كرة فيزيائية)
#   عجلة أوروبية 37 جيب (0-36) بترتيبها الحقيقي - كل جيب مربوط بجائزة
#   (نقطة ملونة بالجيب = فئة الجائزة بالجدول اللي على اليمين)
#   الاحتمالات تُحسب من ROULETTE_PRIZES (الفئة تُختار بالوزن ثم جيب منها)
# =====================================================================
WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24,
               16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
ROULETTE_TIER_COLORS = [
    (150, 160, 170), (96, 182, 120), (70, 170, 200), (80, 120, 220), (150, 110, 225),
    (225, 110, 190), (240, 150, 60), (255, 90, 80), (250, 215, 80), (255, 245, 170),
]
# عدد الجيوب لكل فئة (بنفس ترتيب ROULETTE_PRIZES) - المجموع 37
ROULETTE_POCKET_COUNTS = [6, 6, 5, 5, 4, 3, 2, 1, 3, 2]


def _roulette_pocket_map() -> dict:
    """يوزع الفئات على جيوب العجلة بشكل متباعد: {رقم الجيب: رقم الفئة}."""
    # ترتيب الفئات: الأقوى أولاً (الجاكبوت على صفر الأخضر)
    counts = list(ROULETTE_POCKET_COUNTS)
    jackpot = max(range(len(ROULETTE_PRIZES)), key=lambda i: (
        ROULETTE_PRIZES[i][0] if isinstance(ROULETTE_PRIZES[i][0], int) else 0))
    mapping = {0: jackpot}
    counts[jackpot] -= 1
    order = [i for i in range(len(counts)) if counts[i] > 0]
    pos = 1
    while any(c > 0 for c in counts):
        for i in order:
            if counts[i] > 0 and pos < len(WHEEL_ORDER):
                mapping[WHEEL_ORDER[pos]] = i
                counts[i] -= 1
                pos += 1
    return mapping


ROULETTE_POCKET_TIER = _roulette_pocket_map()


def _prize_label(p) -> str:
    if isinstance(p, str) and p.startswith("gold:"):
        return f"Gold x{p.split(':')[1]}"
    return fmt_money(p)


def _num_color(n: int):
    if n == 0:
        return (30, 140, 70)
    return (196, 36, 40) if n in RED_NUMBERS else (24, 24, 28)


def _polar(cx, cy, r, ang):
    """زاوية بالدرجات: 0 = أعلى، تزيد باتجاه عقارب الساعة."""
    a = math.radians(ang)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def _ring_poly(cx, cy, r0, r1, a0, a1, steps=8):
    pts = [_polar(cx, cy, r1, a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
    pts += [_polar(cx, cy, r0, a1 - (a1 - a0) * i / steps) for i in range(steps + 1)]
    return pts


def _radial_gradient(size, center, r_stops):
    """طبقة تدرج دائري: r_stops = [(نصف_قطر, (r,g,b)), ...] بترتيب تصاعدي."""
    w, h = size
    cx, cy = center
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for (r0, c0), (r1, c1) in zip(r_stops[:-1], r_stops[1:]):
        steps = max(2, int(r1 - r0))
        for s in range(steps, -1, -1):
            t = s / steps
            col = tuple(int(c0[j] + (c1[j] - c0[j]) * t) for j in range(3))
            rr = r0 + (r1 - r0) * t
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    return img


def _build_wheel_layers(k: int, R: int):
    """يرجع (طبقة_ثابتة_RGBA، طبقة_العجلة_الدوّارة_RGBA) بحجم (2R*k)."""
    S = 2 * R * k
    c = S / 2
    # ---------- الطبقة الثابتة: الإطار الخشبي + مسار الكرة ----------
    static = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    wood = _radial_gradient((S, S), (c, c), [(0, (60, 30, 16)), (R * k * 0.80, (96, 52, 26)),
                                              (R * k * 0.93, (128, 72, 36)), (R * k, (58, 30, 16))])
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S - 1, S - 1), fill=255)
    static.paste(wood, (0, 0), mask)
    d = ImageDraw.Draw(static)
    # حلقة ذهبية خارجية رفيعة
    d.ellipse((c - R * k * 0.985, c - R * k * 0.985, c + R * k * 0.985, c + R * k * 0.985),
              outline=(236, 196, 92, 255), width=int(2.4 * k))
    # مسار الكرة (معدن داكن مصقول)
    tr0, tr1 = R * k * 0.80, R * k * 0.935
    track = _radial_gradient((S, S), (c, c), [(tr0, (22, 20, 24)), ((tr0 + tr1) / 2, (58, 56, 64)), (tr1, (30, 28, 32))])
    tm = Image.new("L", (S, S), 0)
    tmd = ImageDraw.Draw(tm)
    tmd.ellipse((c - tr1, c - tr1, c + tr1, c + tr1), fill=255)
    tmd.ellipse((c - tr0, c - tr0, c + tr0, c + tr0), fill=0)
    static.paste(track, (0, 0), tm)
    d = ImageDraw.Draw(static)
    d.ellipse((c - tr1, c - tr1, c + tr1, c + tr1), outline=(210, 214, 222, 255), width=int(1.6 * k))
    d.ellipse((c - tr0, c - tr0, c + tr0, c + tr0), outline=(210, 214, 222, 255), width=int(1.6 * k))
    # عواكس ذهبية (diamonds) على المسار
    for i in range(8):
        a = i * 45 + 22.5
        px, py = _polar(c, c, (tr0 + tr1) / 2, a)
        sz = 6.5 * k
        d.polygon([(px, py - sz), (px + sz * .62, py), (px, py + sz), (px - sz * .62, py)],
                  fill=(238, 200, 96, 255), outline=(120, 80, 20, 255))

    # ---------- طبقة العجلة الدوّارة ----------
    wheel = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wheel)
    r_out, r_in = R * k * 0.775, R * k * 0.50
    step = 360 / 37
    # أرضية الجيوب
    wd.ellipse((c - r_out - 3 * k, c - r_out - 3 * k, c + r_out + 3 * k, c + r_out + 3 * k), fill=(30, 20, 14, 255))
    for i, num in enumerate(WHEEL_ORDER):
        a0, a1 = (i - 0.5) * step, (i + 0.5) * step
        base = _num_color(num)
        wd.polygon(_ring_poly(c, c, r_in, r_out, a0, a1), fill=base + (255,))
        # تظليل بسيط نحو العمق (يعطي إحساس جيب)
        inner_shade = _ring_poly(c, c, r_in, r_in + (r_out - r_in) * 0.22, a0, a1)
        wd.polygon(inner_shade, fill=(0, 0, 0, 70))
        # نقطة فئة الجائزة
        tier = ROULETTE_POCKET_TIER[num]
        px, py = _polar(c, c, r_out - 7.5 * k, i * step)
        rr = 4.0 * k
        wd.ellipse((px - rr, py - rr, px + rr, py + rr), fill=ROULETTE_TIER_COLORS[tier] + (255,),
                   outline=(255, 255, 255, 200), width=max(1, int(0.6 * k)))
    # فواصل الجيوب (معدن فضي)
    for i in range(37):
        a = (i - 0.5) * step
        p0 = _polar(c, c, r_in, a)
        p1 = _polar(c, c, r_out, a)
        wd.line([p0, p1], fill=(214, 218, 226, 255), width=max(2, int(1.4 * k)))
    # الأرقام (تدور مع العجلة، متجهة للمركز)
    f = _font("en", int(13.5 * k))
    for i, num in enumerate(WHEEL_ORDER):
        txt = str(num)
        tw, th = int(f.getlength(txt)) + 8 * k, 20 * k
        lay = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((tw / 2, th / 2), txt, font=f, fill=(255, 255, 255, 255), anchor="mm")
        lay = lay.rotate(180 - i * step, resample=Image.BICUBIC, expand=True)
        px, py = _polar(c, c, r_out - 25 * k, i * step)
        wheel.alpha_composite(lay, (int(px - lay.width / 2), int(py - lay.height / 2)))
    d2 = ImageDraw.Draw(wheel)
    d2.ellipse((c - r_out, c - r_out, c + r_out, c + r_out), outline=(224, 186, 90, 255), width=int(2.2 * k))
    d2.ellipse((c - r_in, c - r_in, c + r_in, c + r_in), outline=(224, 186, 90, 255), width=int(2.2 * k))
    # القمع الداخلي (خشب) + الحلقة
    cone = _radial_gradient((S, S), (c, c), [(0, (36, 18, 10)), (r_in * 0.55, (108, 60, 30)), (r_in, (70, 36, 18))])
    cm = Image.new("L", (S, S), 0)
    ImageDraw.Draw(cm).ellipse((c - r_in + 2 * k, c - r_in + 2 * k, c + r_in - 2 * k, c + r_in - 2 * k), fill=255)
    wheel.paste(cone, (0, 0), cm)
    d2 = ImageDraw.Draw(wheel)
    d2.ellipse((c - r_in * 0.62, c - r_in * 0.62, c + r_in * 0.62, c + r_in * 0.62), outline=(224, 186, 90, 200), width=int(1.4 * k))
    # الأذرع الذهبية + المركز
    for a in (0, 90, 180, 270):
        p0 = _polar(c, c, r_in * 0.10, a)
        p1 = _polar(c, c, r_in * 0.80, a)
        d2.line([p0, p1], fill=(236, 196, 92, 255), width=int(5 * k))
        bx, by = p1
        d2.ellipse((bx - 6.5 * k, by - 6.5 * k, bx + 6.5 * k, by + 6.5 * k), fill=(250, 214, 110, 255), outline=(120, 80, 20, 255))
    cg = _radial_gradient((int(S), int(S)), (c, c), [(0, (255, 244, 190)), (r_in * 0.16, (236, 190, 78)), (r_in * 0.22, (150, 100, 30))])
    cmk = Image.new("L", (S, S), 0)
    ImageDraw.Draw(cmk).ellipse((c - r_in * 0.2, c - r_in * 0.2, c + r_in * 0.2, c + r_in * 0.2), fill=255)
    wheel.paste(cg, (0, 0), cmk)
    return static, wheel


def _ball_sprite(k: int):
    r = 8 * k
    S = r * 6
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    # ظل
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((c - r + 2 * k, c - r + 3 * k, c + r + 2 * k, c + r + 3 * k), fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(2 * k))
    img.alpha_composite(sh)
    ball = _radial_gradient((S, S), (c - r * .3, c - r * .35), [(0, (255, 255, 255)), (r * .9, (226, 226, 232)), (r * 1.9, (140, 140, 150))])
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse((c - r, c - r, c + r, c + r), fill=255)
    img.paste(ball, (0, 0), m)
    return img


def _roulette_panel(d, k, x0, y0, w, h, user_name, tier_idx=None, number=None, phase=0.0):
    """اللوحة اليمنى: اسم اللاعب + جدول الجوائز + الرقم الفائز."""
    B = BRAND_BROWN
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=22 * k, fill=(44, 24, 14, 255), outline=(224, 186, 90, 255), width=int(1.6 * k))
    _text(d, (x0 + w / 2, y0 + 30 * k), "روليت الحظ", int(30 * k), (255, 255, 255, 255), "mm")
    _text_fit(d, (x0 + w / 2, y0 + 58 * k), _trunc(user_name, 18), int(17 * k), (230, 200, 130, 255), "mm", w - 30 * k)
    d.line([(x0 + 16 * k, y0 + 76 * k), (x0 + w - 16 * k, y0 + 76 * k)], fill=(224, 186, 90, 120), width=int(1.2 * k))
    row_h = 29 * k
    top = y0 + 84 * k
    total_w = sum(w_ for _, w_ in ROULETTE_PRIZES)
    for i, (prize, weight) in enumerate(ROULETTE_PRIZES):
        ry = top + i * row_h
        hit = (tier_idx == i)
        if hit:
            glow = 0.5 + 0.5 * math.sin(phase * math.pi * 2)
            d.rounded_rectangle((x0 + 10 * k, ry, x0 + w - 10 * k, ry + row_h - 3 * k), radius=9 * k,
                                fill=(int(214 + 30 * glow), int(168 + 30 * glow), 60, 255))
        col = ROULETTE_TIER_COLORS[i]
        d.ellipse((x0 + w - 28 * k, ry + 6 * k, x0 + w - 14 * k, ry + 20 * k), fill=col + (255,), outline=(255, 255, 255, 220), width=int(.8 * k))
        txt_col = (40, 20, 6, 255) if hit else (255, 255, 255, 255)
        _text(d, (x0 + w - 38 * k, ry + row_h / 2 - 1.5 * k), _prize_label(prize), int(16 * k), txt_col, "rm")
        _text(d, (x0 + 18 * k, ry + row_h / 2 - 1.5 * k), f"{weight * 100 / total_w:.0f}%", int(14 * k),
              (60, 30, 8, 255) if hit else (210, 180, 130, 255), "lm")
    # الرقم الفائز
    by = top + len(ROULETTE_PRIZES) * row_h + 6 * k
    bh = y0 + h - by - 12 * k
    if number is not None:
        nc = _num_color(number)
        d.rounded_rectangle((x0 + 14 * k, by, x0 + w - 14 * k, by + bh), radius=14 * k, fill=nc + (255,), outline=(255, 255, 255, 230), width=int(1.6 * k))
        _text(d, (x0 + w / 2, by + bh / 2), str(number), int(min(bh * .7, 46 * k)), (255, 255, 255, 255), "mm")
    else:
        d.rounded_rectangle((x0 + 14 * k, by, x0 + w - 14 * k, by + bh), radius=14 * k, fill=(30, 16, 10, 255), outline=(224, 186, 90, 160), width=int(1.2 * k))
        _text(d, (x0 + w / 2, by + bh / 2), "تدور...", int(min(bh * .55, 26 * k)), (224, 186, 90, 255), "mm")


_ROUL_CACHE: dict = {}


def _render_roulette_sync(user_avatar, user_name, tier_idx, win_number) -> io.BytesIO:
    """يرسم GIF الروليت كامل (عجلة تدور + كرة تدور بعكس الاتجاه ثم تستقر بالجيب الفائز)."""
    k = 2
    W, H = 760, 470
    R = 222
    cx, cy = 245, H // 2
    if "layers" not in _ROUL_CACHE:
        _ROUL_CACHE["layers"] = _build_wheel_layers(k, R)
        _ROUL_CACHE["ball"] = _ball_sprite(k)
        b = _radial_gradient((W * k, H * k), (W * k * .35, H * k * .5), [(0, (88, 46, 24)), (W * k * .5, (46, 24, 14)), (W * k * .95, (20, 10, 6))]).convert("RGBA")
        b0 = ImageDraw.Draw(b)
        b0.rounded_rectangle((6 * k, 6 * k, W * k - 6 * k, H * k - 6 * k), radius=34 * k, outline=(224, 186, 90, 255), width=int(3 * k))
        b0.rounded_rectangle((13 * k, 13 * k, W * k - 13 * k, H * k - 13 * k), radius=28 * k, outline=BRAND_BROWN + (255,), width=int(2 * k))
        _ROUL_CACHE["bg"] = b
    static, wheel = _ROUL_CACHE["layers"]
    ball_img = _ROUL_CACHE["ball"]
    SW = 2 * R * k
    bg = _ROUL_CACHE["bg"].copy()
    d0 = ImageDraw.Draw(bg)
    # أفاتار اللاعب صغير فوق يسار
    try:
        av = _circle_avatar(user_avatar, 46 * k)
        d0.ellipse((26 * k - 3 * k, 22 * k - 3 * k, 26 * k + 49 * k, 22 * k + 49 * k), fill=(224, 186, 90, 255))
        bg.alpha_composite(av, (26 * k, 22 * k))
    except Exception:
        pass
    panel_x, panel_w = 490 * k, 252 * k
    prox = (cx - R) * k, (cy - R) * k

    # ---- الفيزياء ----
    N_SPIN, N_HOLD = 46, 14
    T = N_SPIN
    pocket_i = WHEEL_ORDER.index(win_number)
    step = 360 / 37
    w_dir = 1
    w_total = 360 * 2.6 + random.uniform(0, 360)            # مجموع دوران العجلة
    ball_dir = -1
    revs = random.choice((6, 7, 8))                          # لفات الكرة قبل الاستقرار
    t_settle = 0.80
    pocket_r = R * k * 0.775 - 15 * k                         # نصف قطر استقرار الكرة (داخل الجيب)
    track_r = R * k * 0.868

    def wheel_angle(t):                                       # t ∈ [0,1]
        return w_dir * w_total * (1 - (1 - min(1.0, t)) ** 2.2)

    frames, durations = [], []
    _base = {}
    total_frames = N_SPIN + N_HOLD
    for fi in range(total_frames):
        t = min(1.0, fi / (T - 1))
        wa = wheel_angle(t)
        # العجلة (مع مزج حركة بسيط وقت السرعة العالية)
        spd = abs(wheel_angle(min(1.0, t + 0.02)) - wa)
        wr = wheel.rotate(-wa, resample=Image.BILINEAR)
        if spd > 11 and fi < N_SPIN:
            wr2 = wheel.rotate(-(wa - w_dir * spd * .5), resample=Image.BILINEAR)
            wr = Image.blend(wr, wr2, .42)
        # زاوية الكرة
        if t < t_settle:
            u = t / t_settle
            g = (1 - u) ** 2
            final_ang = pocket_i * step + wheel_angle(t_settle) * 1.0
            ang = final_ang + ball_dir * 360 * revs * g
            drop = max(0.0, (u - 0.55) / 0.45)               # بداية السقوط للداخل
            r_ball = track_r + (pocket_r - track_r) * (drop ** 1.6)
            if drop > 0:
                r_ball += (6 * k) * math.sin(drop * math.pi * 7) * (1 - drop) ** 1.2
                ang += step * 2.0 * math.cos(drop * math.pi * 6) * (1 - drop) ** 2
        else:
            ang = pocket_i * step + wa
            r_ball = pocket_r
        done = fi >= N_SPIN - 2
        if not done:
            if "spin" not in _base:
                fb = bg.copy()
                _roulette_panel(ImageDraw.Draw(fb), k, panel_x, 22 * k, panel_w, (H - 44) * k, user_name)
                fb.alpha_composite(static, prox)
                _base["spin"] = fb
            frame = _base["spin"].copy()
        else:
            phase = (fi - (N_SPIN - 2)) / 6
            frame = bg.copy()
            _roulette_panel(ImageDraw.Draw(frame), k, panel_x, 22 * k, panel_w, (H - 44) * k, user_name,
                            tier_idx, win_number, phase)
            frame.alpha_composite(static, prox)
        frame.alpha_composite(wr, prox)
        # الكرة
        bx, by = _polar(SW / 2, SW / 2, r_ball, ang)
        frame.alpha_composite(ball_img, (int(prox[0] + bx - ball_img.width / 2), int(prox[1] + by - ball_img.height / 2)))
        out = frame.resize((W, H), Image.BOX).convert("RGB")
        frames.append(out)
        durations.append(60 if fi < N_SPIN - 12 else (80 if fi < N_SPIN else 90))
    durations[-1] = 60000

    # لوحة ألوان موحّدة لكل الفريمات (يقلل الحجم ويمنع الوميض)
    pal_src = frames[-1].quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal_src, dither=Image.Dither.NONE) for f in frames]
    buf = io.BytesIO()
    q[0].save(buf, format="GIF", save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=False, disposal=1)
    buf.seek(0)
    return buf


# =====================================================================
#        💎  ألغام (Mines) احترافية - لوحة مرسومة + حركات (قلب المربع/انفجار)
#   مضاعف حقيقي حسب الاحتمال (مع هامش بنك 3%) بدل زيادة ثابتة.
# =====================================================================
MINES_COLS, MINES_ROWS = 5, 4
MINES_TOTAL = MINES_COLS * MINES_ROWS      # 20 مربع
MINES_EDGE = 0.97                          # نسبة العائد (هامش البنك 3%)


def mines_multiplier(bombs: int, safe_clicks: int) -> float:
    """المضاعف بعد عدد معين من المربعات الآمنة (احتمالي حقيقي)."""
    m = MINES_EDGE
    for i in range(safe_clicks):
        m *= (MINES_TOTAL - i) / (MINES_TOTAL - bombs - i)
    return max(1.0, m) if safe_clicks else 1.0


def mines_safe_chance(bombs: int, safe_clicks: int) -> float:
    left = MINES_TOTAL - safe_clicks
    return (left - bombs) / left * 100 if left > 0 else 0.0


_MINES_BG: dict = {}


def _gem_polys(cx, cy, s):
    """أوجه الألماسة (قمة، تاج، قاعدة) - كل وجه = (نقاط، لون)."""
    t = s * 0.50
    tl, tr = (cx - t * .55, cy - t * .62), (cx + t * .55, cy - t * .62)
    l, r = (cx - t, cy - t * .12), (cx + t, cy - t * .12)
    b = (cx, cy + t * .95)
    ml, mr = (cx - t * .32, cy - t * .12), (cx + t * .32, cy - t * .12)
    return [
        ([tl, tr, mr, ml], (170, 255, 244)),
        ([tl, ml, l], (108, 226, 224)),
        ([tr, mr, r], (86, 200, 214)),
        ([l, ml, b], (46, 168, 206)),
        ([ml, mr, b], (84, 214, 232)),
        ([mr, r, b], (30, 140, 190)),
    ]


def _draw_gem(d, cx, cy, s, alpha=255, glow=False, layer=None):
    if glow and layer is not None:
        g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((cx - s * .62, cy - s * .62, cx + s * .62, cy + s * .62), fill=(90, 255, 230, 110))
        g = g.filter(ImageFilter.GaussianBlur(s * .16))
        layer.alpha_composite(g)
        d = ImageDraw.Draw(layer)
    for pts, col in _gem_polys(cx, cy, s):
        d.polygon(pts, fill=col + (alpha,), outline=(255, 255, 255, int(alpha * .75)))


def _draw_bomb(d, cx, cy, s, alpha=255, boom=False, layer=None):
    r = s * 0.30
    by = cy + s * .05
    if layer is not None:
        lite = 1.5 if alpha < 255 else 1.0
        sph = _radial_gradient((int(r * 2.6), int(r * 2.6)), (r * 1.1, r * 1.0), [(0, (170, 170, 185)), (r * .5, (int(48 * lite), int(48 * lite), int(58 * lite))), (r * 1.45, (int(20 * lite), int(20 * lite), int(26 * lite)))])
        m = Image.new("L", sph.size, 0)
        ImageDraw.Draw(m).ellipse((r * .3, r * .3, r * 2.3, r * 2.3), fill=int(255 * alpha / 255))
        layer.paste(sph, (int(cx - r * 1.3), int(by - r * 1.3)), m)
        d = ImageDraw.Draw(layer)
    d.ellipse((cx - r * .6, by - r * .72, cx - r * .12, by - r * .3), fill=(255, 255, 255, int(alpha * .55)))
    # فتيل
    pts = [(cx + r * .25, by - r * .92), (cx + r * .62, by - r * 1.35), (cx + r * .35, by - r * 1.7), (cx + r * .8, by - r * 2.0)]
    d.line(pts, fill=(196, 150, 90, alpha), width=max(2, int(s * .045)), joint="curve")
    sx, sy = pts[-1]
    for ang in range(0, 360, 45):
        ex, ey = sx + math.cos(math.radians(ang)) * s * .12, sy + math.sin(math.radians(ang)) * s * .12
        d.line([(sx, sy), (ex, ey)], fill=(255, 200, 60, alpha), width=max(1, int(s * .03)))
    d.ellipse((sx - s * .04, sy - s * .04, sx + s * .04, sy + s * .04), fill=(255, 245, 190, alpha))


def _mine_tile(k, size, kind, number=None):
    """يرسم مربع واحد كصورة RGBA بحجم (size*k)."""
    S = int(size * k)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rad = int(S * .17)
    if kind == "hidden":
        top, bot, edge = (176, 98, 56), (118, 58, 30), (214, 150, 96)
    elif kind in ("safe", "safe_dim"):
        top, bot, edge = (28, 78, 92), (14, 40, 52), (96, 220, 226)
    elif kind in ("bomb", "bomb_dim"):
        top, bot, edge = (112, 34, 38), (60, 18, 22), (230, 90, 80)
    else:  # boom
        top, bot, edge = (210, 60, 44), (120, 24, 20), (255, 190, 90)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)], fill=tuple(int(top[j] + (bot[j] - top[j]) * t) for j in range(3)) + (255,))
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, S - 1, S - 1), radius=rad, fill=255)
    img.paste(grad, (0, 0), m)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=rad, outline=edge + (255,), width=max(2, int(S * .03)))
    if kind == "hidden":
        # لمعة علوية + رقم
        gl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(gl).rounded_rectangle((S * .08, S * .06, S * .92, S * .40), radius=int(S * .12), fill=(255, 255, 255, 34))
        img.alpha_composite(gl)
        d = ImageDraw.Draw(img)
        if number is not None:
            _text(d, (S / 2, S / 2 + S * .02), str(number), int(S * .42), (255, 236, 206, 255), "mm")
    elif kind == "safe":
        _draw_gem(d, S / 2, S / 2, S * .78, glow=True, layer=img)
    elif kind == "safe_dim":
        _draw_gem(d, S / 2, S / 2, S * .6, alpha=120)
    elif kind in ("bomb", "boom"):
        _draw_bomb(d, S / 2, S / 2, S * .86, layer=img, boom=kind == "boom")
    elif kind == "bomb_dim":
        _draw_bomb(d, S / 2, S / 2, S * .7, alpha=215, layer=img)
    return img


def _mines_board(k, st, anim=None):
    """st: dict(...) حالة اللعبة. anim: None أو {'idx','kind','p'(0..1),'shake','flash','sparks'}"""
    W, H = 700, 664
    tile, gap = 104, 12
    gx0 = (W - (MINES_COLS * tile + (MINES_COLS - 1) * gap)) // 2
    gy0 = 128
    key = (k,)
    if key not in _MINES_BG:
        bg = _radial_gradient((W * k, H * k), (W * k * .5, H * k * .35), [(0, (92, 50, 28)), (W * k * .55, (48, 26, 16)), (W * k, (20, 10, 6))]).convert("RGBA")
        bd = ImageDraw.Draw(bg)
        bd.rounded_rectangle((6 * k, 6 * k, W * k - 6 * k, H * k - 6 * k), radius=34 * k, outline=(224, 186, 90, 255), width=int(3 * k))
        bd.rounded_rectangle((13 * k, 13 * k, W * k - 13 * k, H * k - 13 * k), radius=28 * k, outline=BRAND_BROWN + (255,), width=int(2 * k))
        _MINES_BG[key] = bg
    img = _MINES_BG[key].copy()
    d = ImageDraw.Draw(img)
    # ---- الهيدر ----
    try:
        av = _circle_avatar(st["avatar"], 64 * k)
        d.ellipse((30 * k - 4 * k, 30 * k - 4 * k, 30 * k + 68 * k, 30 * k + 68 * k), fill=(224, 186, 90, 255))
        img.alpha_composite(av, (30 * k, 30 * k))
    except Exception:
        pass
    _text_fit(d, (112 * k, 52 * k), _trunc(st["name"], 16), int(24 * k), (255, 255, 255, 255), "lm", 230 * k)
    _text(d, (112 * k, 82 * k), st["mode"], int(17 * k), (230, 200, 130, 255), "lm")
    # بطاقة المضاعف (وسط)
    won = st["status"] == "won"
    lost = st["status"] == "lost"
    mc = (96, 214, 130) if not lost else (240, 100, 90)
    d.rounded_rectangle((350 * k, 26 * k, 480 * k, 100 * k), radius=18 * k, fill=(30, 16, 10, 255), outline=mc + (255,), width=int(2 * k))
    _text(d, (415 * k, 44 * k), "المضاعف", int(14 * k), (210, 180, 130, 255), "mm")
    _text(d, (415 * k, 76 * k), f"x{st['mult']:.2f}", int(30 * k), mc + (255,), "mm")
    # بطاقة الربح (يمين)
    d.rounded_rectangle((496 * k, 26 * k, 672 * k, 100 * k), radius=18 * k, fill=(30, 16, 10, 255), outline=(224, 186, 90, 255), width=int(2 * k))
    _text(d, (584 * k, 44 * k), st["reward_label"], int(14 * k), (210, 180, 130, 255), "mm")
    _text_fit(d, (584 * k, 76 * k), st["reward"], int(26 * k), (255, 255, 255, 255), "mm", 160 * k)
    # ---- اللوحة ----
    d.rounded_rectangle((gx0 - 16, gy0 - 16, gx0 + (MINES_COLS * tile + (MINES_COLS - 1) * gap) + 16, gy0 + (MINES_ROWS * tile + (MINES_ROWS - 1) * gap) + 16)
                        if False else (gx0 * k - 16 * k, gy0 * k - 14 * k, (gx0 + MINES_COLS * tile + (MINES_COLS - 1) * gap) * k + 16 * k,
                                       (gy0 + MINES_ROWS * tile + (MINES_ROWS - 1) * gap) * k + 14 * k),
                        radius=24 * k, fill=(26, 14, 8, 200), outline=(224, 186, 90, 90), width=int(1.4 * k))
    shake = (0, 0)
    if anim and anim.get("shake"):
        shake = (random.randint(-7, 7) * k, random.randint(-6, 6) * k)
    revealed, bombs, hit, ended = set(st["revealed"]), set(st.get("bombs") or []), st.get("hit"), st["status"] != "playing"
    for idx in range(MINES_TOTAL):
        r, c = divmod(idx, MINES_COLS)
        x = (gx0 + c * (tile + gap)) * k + shake[0]
        y = (gy0 + r * (tile + gap)) * k + shake[1]
        if anim and anim.get("idx") == idx and anim.get("kind") in ("flip_safe", "flip_bomb"):
            p = anim["p"]
            kind_to = "safe" if anim["kind"] == "flip_safe" else "boom"
            t_img = _mine_tile(k, tile, "hidden" if p < .5 else kind_to, idx + 1)
            sx = abs(math.cos(p * math.pi))
            nw = max(2, int(t_img.width * sx))
            t_img = t_img.resize((nw, t_img.height), Image.BILINEAR)
            lift = int(math.sin(p * math.pi) * 8 * k)
            img.alpha_composite(t_img, (int(x + (tile * k - nw) / 2), int(y - lift)))
            continue
        if idx in revealed:
            kind = "safe"
        elif ended and idx in bombs:
            kind = "boom" if idx == hit else "bomb_dim" if False else ("boom" if idx == hit else "bomb")
        elif ended:
            kind = "safe_dim"
        else:
            kind = "hidden"
        if ended and idx in bombs and idx != hit:
            kind = "bomb_dim"
        img.alpha_composite(_mine_tile(k, tile, kind, idx + 1), (int(x), int(y)))
    # ---- الفوتر ----
    fy = (gy0 + MINES_ROWS * tile + (MINES_ROWS - 1) * gap + 40) * k
    if st["status"] == "playing":
        nxt = mines_multiplier(st["bombs_n"], st["safe"] + 1)
        _text(d, (672 * k, fy), f"التالي x{nxt:.2f}  •  أمان {mines_safe_chance(st['bombs_n'], st['safe']):.0f}٪", int(17 * k), (232, 210, 160, 255), "rm")
    elif won:
        _text(d, (672 * k, fy), "تم سحب المكافأة بنجاح", int(20 * k), (110, 220, 140, 255), "rm")
    else:
        _text(d, (672 * k, fy), "انفجرت القنبلة!", int(20 * k), (240, 110, 100, 255), "rm")
    _text(d, (30 * k, fy), f"💎 {st['safe']}   |   قنابل: {st['bombs_n']}".replace("💎 ", "") if False else f"آمن: {st['safe']}  •  قنابل: {st['bombs_n']}", int(17 * k), (232, 210, 160, 255), "lm")
    # ---- تأثيرات ----
    if anim:
        if anim.get("sparks"):
            idx = anim["idx"]
            r, c = divmod(idx, MINES_COLS)
            cx = (gx0 + c * (tile + gap) + tile / 2) * k
            cy = (gy0 + r * (tile + gap) + tile / 2) * k
            pp = anim["sparks"]
            for i in range(10):
                ang = i * 36 + 12
                dist = (20 + 46 * pp) * k
                px, py = cx + math.cos(math.radians(ang)) * dist, cy + math.sin(math.radians(ang)) * dist
                sz = (7 - 5 * pp) * k
                a = int(255 * (1 - pp))
                d.polygon([(px, py - sz), (px + sz * .4, py), (px, py + sz), (px - sz * .4, py)], fill=(190, 255, 244, a))
        if anim.get("flash"):
            idx = anim["idx"]
            r, c = divmod(idx, MINES_COLS)
            cx = (gx0 + c * (tile + gap) + tile / 2) * k
            cy = (gy0 + r * (tile + gap) + tile / 2) * k
            pp = anim["flash"]
            ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            rr = (30 + 330 * pp) * k
            od.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 150, 40, int(190 * (1 - pp))))
            od.ellipse((cx - rr * .55, cy - rr * .55, cx + rr * .55, cy + rr * .55), fill=(255, 238, 170, int(230 * (1 - pp))))
            od.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 220, 140, int(255 * (1 - pp))), width=int(5 * k * (1 - pp) + 1))
            ov = ov.filter(ImageFilter.GaussianBlur(3 * k))
            img.alpha_composite(ov)
    return img, (W, H)


def _render_mines_sync(st: dict, anim_kind: str | None = None, idx: int | None = None) -> tuple:
    """يرجع (BytesIO, اسم الملف). anim_kind: 'safe' | 'bomb' | None (صورة ثابتة)."""
    k = 2
    if anim_kind is None:
        img, size = _mines_board(k, st)
        buf = io.BytesIO()
        img.resize(size, Image.BOX).convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return buf, "mines.png"
    frames, durs = [], []
    if anim_kind == "safe":
        for i in range(7):
            p = i / 6
            im, size = _mines_board(k, st, {"idx": idx, "kind": "flip_safe", "p": p, "sparks": (p - .6) / .4 if p > .6 else 0})
            frames.append(im.resize(size, Image.BOX).convert("RGB")); durs.append(50)
        im, size = _mines_board(k, st)
        frames.append(im.resize(size, Image.BOX).convert("RGB")); durs.append(60000)
    else:  # bomb
        for i in range(5):
            p = i / 4
            im, size = _mines_board(k, {**st, "status": "playing", "safe": st["safe"]}, {"idx": idx, "kind": "flip_bomb", "p": p})
            frames.append(im.resize(size, Image.BOX).convert("RGB")); durs.append(55)
        for i in range(7):
            p = (i + 1) / 7
            im, size = _mines_board(k, st, {"idx": idx, "flash": p, "shake": i < 5})
            frames.append(im.resize(size, Image.BOX).convert("RGB")); durs.append(55)
        im, size = _mines_board(k, st)
        frames.append(im.resize(size, Image.BOX).convert("RGB")); durs.append(60000)
    pal = frames[-1].quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    buf = io.BytesIO()
    q[0].save(buf, format="GIF", save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=False, disposal=1)
    buf.seek(0)
    return buf, "mines.gif"


# =====================================================================
#        🏦  أوامر البنك المرجّعة بنظام الصور (راتب / روليت / نهب / رهان ...)
# =====================================================================
def parse_amount_ctx(rest: list, user_id: int):
    """يفهم: رقم / نص / نصف / ربع / كامل / الكل - حسب رصيد اللاعب."""
    text = " ".join(rest).strip()
    if not text:
        return None
    first = text.split()[0]
    bal = get_balance(user_id)
    if first in ("كامل", "الكل", "كل", "all"):
        return bal
    if first in ("نص", "نصف"):
        return bal // 2
    if first == "ربع":
        return bal // 4
    return parse_amount(text)


def get_gold(user_id: int) -> int:
    return load_db()["gold"].get(str(user_id), 0)


def update_gold(user_id: int, delta: int) -> int:
    db = load_db()
    uid = str(user_id)
    db["gold"][uid] = max(0, db["gold"].get(uid, 0) + delta)
    save_db(db)
    return db["gold"][uid]


def get_properties(user_id: int) -> dict:
    db = load_db()
    uid = str(user_id)
    props = db["properties"].setdefault(uid, {})
    for key in PROPERTY_CATALOG:
        props.setdefault(key, 0)
    props.setdefault("stocks", 0)
    save_db(db)
    return props


def update_property(user_id: int, key: str, delta: int) -> int:
    db = load_db()
    props = db["properties"].setdefault(str(user_id), {k: 0 for k in PROPERTY_CATALOG})
    props.setdefault("stocks", 0)
    props[key] = max(0, props.get(key, 0) + delta)
    save_db(db)
    return props[key]


def net_worth(user_id: int, db: dict | None = None) -> int:
    db = db or load_db()
    uid = str(user_id)
    cash = db["economy"].get(uid, STARTING_BALANCE)
    props = db["properties"].get(uid, {})
    value = sum(props.get(k, 0) * PROPERTY_CATALOG[k]["price"] for k in PROPERTY_CATALOG)
    return cash + value + props.get("stocks", 0) * STOCK_PRICE


def is_protected(user_id: int) -> float:
    until = load_db()["protection"].get(str(user_id), 0)
    return max(0.0, until - _now_ts())


def set_protection(user_id: int, hours: float) -> None:
    db = load_db()
    db["protection"][str(user_id)] = _now_ts() + hours * 3600
    save_db(db)


def clear_cooldowns(user_id: int) -> None:
    db = load_db()
    db["bank_cooldowns"][str(user_id)] = {}
    save_db(db)


def push_bank_history(user_id: int, game: str, balance_after: int) -> list:
    db = load_db()
    hist = db.setdefault("bank_history", {}).setdefault(str(user_id), {}).setdefault(game, [])
    hist.append(balance_after)
    del hist[:-8]
    save_db(db)
    return hist


def get_job_title(member) -> str:
    if not isinstance(member, discord.Member) or not member.guild:
        return "عامل"
    if member.id == member.guild.owner_id:
        return "شيخ"
    if BANK_OWNER_ROLE_ID and any(r.id == BANK_OWNER_ROLE_ID for r in member.roles):
        return "شيخ"
    if {r.name.strip() for r in member.roles} & {"Owner", "owner", "المالك", "مالك", "اونر"}:
        return "شيخ"
    return "عامل"


def _clean_name(name: str) -> str:
    """يشيل الإيموجي/الزخارف اللي ما يدعمها الخط عشان ما تطلع مربعات بالصورة."""
    out = re.sub(r"[^\w\s\u0600-\u06FF.\-_']", "", str(name))
    out = re.sub(r"\s+", " ", out).strip()
    return out or "عضو"


def _ask_amount(word: str) -> str:
    return f"❌ حدد المبلغ بعد الأمر، مثال: `{word} 5000` أو `{word} نص` أو `{word} كامل`"


def _bet_check(user, amount, min_bet):
    bal = get_balance(user.id)
    if amount is None:
        return None, bal
    if amount < min_bet:
        return f"❌ أقل مبلغ مسموح هنا: **{fmt_money(min_bet)}**", bal
    if amount > bal or amount <= 0:
        return f"❌ رصيدك ما يكفي! معك {fmt_money(bal)} بس.", bal
    return None, bal


def _signed(n: int) -> str:
    return f"+{fmt_money(n)}" if n >= 0 else f"-{fmt_money(abs(n))}"


# ------------------------- راتب / بخشيش / حظ -------------------------
async def act_salary(user, **_):
    set_cooldown(user.id, "راتب")
    job = get_job_title(user)
    nb = update_balance(user.id, SALARY_AMOUNT)
    f = await make_card(user, "عملية ايداع", f"تم ايداع مبلغ راتب , الوظيفة : {job}", amount=_signed(SALARY_AMOUNT),
                        side=f"رصيدك الحالي : {fmt_money(nb)}", icon="coins")
    return None, (f"💵 {user.mention}", f)


async def act_tip(user, **_):
    set_cooldown(user.id, "بخشيش")
    amt = random.randint(TIP_MIN, TIP_MAX)
    nb = update_balance(user.id, amt)
    f = await make_card(user, "عملية ايداع", "تم ايداع مبلغ حساب المواطن", amount=_signed(amt),
                        side=f"رصيدك الحالي : {fmt_money(nb)}", icon="coins")
    return None, (f"💵 {user.mention}", f)


async def act_luck(user, **_):
    set_cooldown(user.id, "حظ")
    amt = random.randint(LUCK_MIN, LUCK_MAX)
    nb = update_balance(user.id, amt)
    won = amt >= 0
    f = await make_card(user, "عملية ايداع" if won else "عملية خصم", "حظك هالوقت حلو" if won else "حظك نحس هالمرة",
                        amount=_signed(amt), side=f"رصيدك الحالي : {fmt_money(nb)}", icon="coins" if won else "chart_down")
    return None, (f"{'🍀' if won else '😬'} {user.mention}", f)


# ------------------------- نهب / حماية -------------------------
async def act_rob(user, **_):
    db = load_db()
    now = _now_ts()
    ranked = sorted(db["economy"].items(), key=lambda kv: kv[1], reverse=True)
    target_id = next((uid for uid, bal in ranked if uid != str(user.id) and bal > 0 and db["protection"].get(uid, 0) <= now), None)
    if not target_id:
        return "🕵️ ما فيه هدف مناسب: كل الأعضاء إما محميين أو رصيدهم صفر حالياً.", None
    set_cooldown(user.id, "نهب")
    guild = getattr(user, "guild", None)
    tm = guild.get_member(int(target_id)) if guild else None
    tname = _clean_name(tm.display_name) if tm else "عضو"
    tmention = tm.mention if tm else f"<@{target_id}>"
    if random.random() < ROB_SUCCESS_CHANCE:
        stolen = max(1, int(db["economy"].get(target_id, 0) * ROB_PERCENT))
        update_balance(int(target_id), -stolen)
        nb = update_balance(user.id, stolen)
        f = await make_card(user, "تمت السرقة بنجاح !!", f"نهبت : {tname}", amount=_signed(stolen),
                            side=f"رصيدك الحالي : {fmt_money(nb)}", icon="coins")
        return None, (f"🕵️ {user.mention} نهب {tmention} - انتبه لحسابك لا يصيدك أحد ثاني!", f)
    nb = update_balance(user.id, -ROB_FAIL_FINE)
    f = await make_card(user, "عملية خصم", f"حاولت تسرق {tname} بس مسكوك! دفعت غرامة", amount=_signed(-ROB_FAIL_FINE),
                        side=f"رصيدك الحالي : {fmt_money(nb)}", icon="chart_down")
    return None, (f"🚔 {user.mention}", f)


async def act_protection(user, **_):
    rem = is_protected(user.id)
    if rem > 0:
        f = await make_card(user, "الحماية شغالة", f"باقي على انتهائها : {format_clock(rem)}", amount="🛡", icon="shield")
        return None, (f"🛡️ {user.mention}", f)
    if get_balance(user.id) < PROTECTION_COST:
        return f"❌ تفعيل الحماية يكلف **{fmt_money(PROTECTION_COST)}** ورصيدك ما يكفي.", None
    nb = update_balance(user.id, -PROTECTION_COST)
    set_protection(user.id, PROTECTION_HOURS)
    f = await make_card(user, "تم تفعيل الحماية", f"محمي من السرقة لمدة {PROTECTION_HOURS} ساعات",
                        amount=_signed(-PROTECTION_COST), side=f"رصيدك الحالي : {fmt_money(nb)}", icon="shield")
    return None, (f"🛡️ {user.mention}", f)


# ------------------------- رهان / قمار -------------------------
async def act_bet(user, amount=None, **_):
    if amount is None:
        return _ask_amount("رهان"), None
    err, bal = _bet_check(user, amount, BET_MIN_BET)
    if err:
        return err, None
    set_cooldown(user.id, "رهان")
    won = random.random() < 0.48
    nb = update_balance(user.id, amount if won else -amount)
    f = await make_card(user, "عملية ايداع" if won else "عملية خصم", "ربحت الرهان" if won else "خسرت الرهان",
                        amount=_signed(amount if won else -amount), side=f"رصيدك الحالي : {fmt_money(nb)}",
                        icon="chart_up" if won else "chart_down")
    return None, (f"{'🎯' if won else '💸'} {user.mention}", f)


async def act_gamble(user, amount=None, **_):
    if amount is None:
        return _ask_amount("قمار"), None
    err, bal = _bet_check(user, amount, GAMBLE_MIN_BET)
    if err:
        return err, None
    set_cooldown(user.id, "قمار")
    mults = [m for m, _ in GAMBLE_OUTCOMES]
    mult = random.choices(mults, weights=[w for _, w in GAMBLE_OUTCOMES], k=1)[0]
    profit = int(amount * mult) - amount
    nb = update_balance(user.id, profit)
    won = profit >= 0
    f = await make_card(user, "عملية ايداع" if won else "عملية خصم", f"القمار طلع لك مضاعف x{mult}",
                        amount=_signed(profit), side=f"رصيدك الحالي : {fmt_money(nb)}", icon="coins" if won else "chart_down")
    return None, (f"🎰 {user.mention}", f)


async def act_invest(user, amount=None, game="استثمار", **_):
    if amount is None:
        return _ask_amount(game), None
    min_bet = INVEST_MIN_BET if game == "استثمار" else TRADE_MIN_BET
    err, bal = _bet_check(user, amount, min_bet)
    if err:
        return err, None
    set_cooldown(user.id, game)
    lo, hi = (INVEST_MIN_PCT, INVEST_MAX_PCT) if game == "استثمار" else (TRADE_MIN_PCT, TRADE_MAX_PCT)
    pct = random.uniform(lo, hi)
    profit = int(amount * pct)
    nb = update_balance(user.id, profit)
    hist = push_bank_history(user.id, game, nb)
    up = profit >= 0
    values = list(hist)
    if len(values) < 4:
        values = [max(1, nb - profit * (1 - i / 7)) for i in range(8)]
    chart = {"values": values, "up": up, "tag": "ربح" if up else "خسارة", "pct_text": f"{fmt_pct_num(pct * 100)}٪"}
    main = f"{game} : {'ربحت' if up else 'خسرت'} بنسبة {fmt_pct_num(pct * 100)}٪"
    lines = [("المبلغ :", fmt_money(amount), (255, 255, 255), 640),
             ("الربح :" if up else "الخسارة :", _signed(profit), GREEN if up else RED, 730)]
    f = await make_card(user, f"{game} رابح" if up else f"{game} خاسر", main, icon="chart_up" if up else "chart_down", chart=chart, lines=lines)
    return None, (f"{'📈' if up else '📉'} رصيدك الحين: **{fmt_money(nb)}**", f)


async def act_speedup(user, **_):
    gold = get_gold(user.id)
    if gold < SPEEDUP_GOLD_COST:
        return f"❌ تحتاج **Gold x{SPEEDUP_GOLD_COST}** للتسريع (عندك **{gold}**).", None
    ng = update_gold(user.id, -SPEEDUP_GOLD_COST)
    clear_cooldowns(user.id)
    f = await make_card(user, "عملية تسريع", "تم إزالة جميع الأوقات من حسابك", amount=f"-Gold x{SPEEDUP_GOLD_COST}",
                        side=f"ذهبك الحالي : {ng}", icon="bolt")
    return None, (f"⚡ {user.mention}", f)


# ------------------------- جداول (ممتلكات / أغنى / أوامر) -------------------------
async def act_properties(user, **_):
    props = get_properties(user.id)
    gold = get_gold(user.id)
    db = load_db()
    rows = [(info["name"], str(props.get(k, 0)), fmt_money(props.get(k, 0) * info["price"]), None) for k, info in PROPERTY_CATALOG.items()]
    rows.append(("أسهم", str(props.get("stocks", 0)), fmt_money(props.get("stocks", 0) * STOCK_PRICE), None))
    rows.append(("ذهب (Gold)", str(gold), "—", None))
    rows.append(("الكاش", "", fmt_money(db["economy"].get(str(user.id), STARTING_BALANCE)), None, True))
    rows.append(("إجمالي الثروة", "", fmt_money(net_worth(user.id, db)), GREEN, True))
    buf = await _run_sync(_render_table_sync, f"ممتلكات {_trunc(_clean_name(user.display_name), 12)}",
                          ["الممتلكات", "العدد", "القيمة"], rows, None, "gold")
    return None, (f"💼 {user.mention}", discord.File(buf, filename="properties.png"))


async def act_richest(user, **_):
    db = load_db()
    if not db["economy"]:
        return "🏆 ما فيه بيانات كافية بعد.", None
    ranked = sorted(((uid, net_worth(int(uid), db)) for uid in db["economy"]), key=lambda kv: kv[1], reverse=True)[:10]
    guild = getattr(user, "guild", None)
    rows = []
    for i, (uid, worth) in enumerate(ranked, 1):
        m = guild.get_member(int(uid)) if guild else None
        name = _trunc(_clean_name(m.display_name), 16) if m else f"عضو {str(uid)[-4:]}"
        col = {1: (255, 214, 80), 2: (214, 218, 226), 3: (226, 150, 90)}.get(i)
        rows.append((name, fmt_money(worth), f"#{i}", col, i <= 3))
    buf = await _run_sync(_render_table_sync, "أغنى الأعضاء", ["العضو", "الثروة", "الترتيب"], rows,
                          "الثروة = الكاش + الممتلكات + الأسهم", "trophy")
    return None, ("🏆 قائمة أغنى 10 أعضاء بالسيرفر", discord.File(buf, filename="richest.png"))


BANK_HELP_LINES = [
    ("راتب", "راتبك اليومي حسب وظيفتك"), ("بخشيش", "بخشيش عشوائي صغير"), ("حظ", "جرب حظك ربح أو خسارة"),
    ("روليت", "روليت كازينو متحرك بجوائز كاش وذهب"), ("نهب", "اسرق أغنى عضو غير محمي"), ("حماية", "حماية 5 ساعات من السرقة"),
    ("رهان / قمار / نرد + مبلغ", "العب ضد البنك (نص / كامل / رقم)"), ("استثمار / تداول + مبلغ", "مخاطرة + شارت أداء"),
    ("الغام [مبلغ]", "ألغام بمضاعف حقيقي (مجاني أو برهان)"), ("لعبه", "حجرة ورقة مقص"), ("فواكه", "ماكينة فواكه متحركة"),
    ("لون", "أي لون أكثر بالشبكة؟ (25 محاولة يومياً)"), ("تسريع", f"يشيل الانتظار مقابل Gold x{SPEEDUP_GOLD_COST}"),
    ("شراء / بيع", "متجر الممتلكات (أو: شراء ذهب 500 للسوق)"), ("سوق / حصالتي", "أسعار السوق ومحفظتك"),
    ("ممتلكات", "ممتلكاتك وثروتك"), ("اغنى", "أغنى 10 أعضاء"), ("فلوس / تحويل", "رصيدك وتحويل الفلوس"), ("وقت", "جاهزية كل الأوامر"),
]


def _render_list_sync(title, rows, note=None, icon="coins") -> io.BytesIO:
    """جدول عمودين (أمر + شرح) بنفس ستايل بطاقات البنك."""
    n = len(rows)
    row_h = 84
    body_top = 337
    body_bottom = body_top + 40 + n * row_h + (90 if note else 30)
    outer_bottom = body_bottom + 15
    R = _Ref(1900, outer_bottom + 10 - 90, 60, 90)
    B = BRAND_BROWN
    WHITE = (255, 255, 255, 255)
    img = Image.new("RGBA", R.size, B + (0,))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(R.box(69, 98, 1950, outer_bottom), radius=R.n(50), fill=B + (255,))
    d.rounded_rectangle(R.box(85, 113, 1935, 322), radius=R.n(38), corners=(True, True, False, False), fill=B + (36,))
    d.rounded_rectangle(R.box(85, body_top, 1935, body_bottom), radius=R.n(40), corners=(False, False, True, True), fill=B + (92,))
    _text(d, (R.x(1680), R.y(212)), title, int(R.n(66)), WHITE, "rm")
    _draw_icon(d, R, icon)
    _text(d, (R.x(130), R.y(213)), BANK_BRAND, int(R.n(56)), WHITE, "lm")
    for i, (cmd, desc) in enumerate(rows):
        cy = body_top + 40 + i * row_h + row_h // 2
        if i % 2 == 0:
            d.rectangle(R.box(110, cy - row_h // 2 + 4, 1910, cy + row_h // 2 - 4), fill=B + (60,))
        _text_fit(d, (R.x(1860), R.y(cy)), cmd, int(R.n(52)), (255, 214, 120, 255), "rm", R.n(760))
        _text_fit(d, (R.x(1060), R.y(cy)), desc, int(R.n(46)), WHITE, "rm", R.n(900))
    if note:
        _text_fit(d, (R.x(1010), R.y(body_bottom - 45)), note, int(R.n(40)), (255, 255, 255, 200), "mm", R.n(1750))
    return _to_png(img, R.final)


async def act_help(user, **_):
    buf = await _run_sync(_render_list_sync, "أوامر البنك", BANK_HELP_LINES, "اكتب الأمر بنفس الروم بدون سلاش", "coins")
    return None, ("📜 أوامر البنك المتاحة", discord.File(buf, filename="help.png"))


# =====================================================================
#                          🎡  روليت
# =====================================================================
async def cmd_roulette(message: discord.Message):
    user = message.author
    set_cooldown(user.id, "روليت")
    weights = [w for _, w in ROULETTE_PRIZES]
    tier = random.choices(range(len(ROULETTE_PRIZES)), weights=weights, k=1)[0]
    prize = ROULETTE_PRIZES[tier][0]
    win_number = random.choice([n for n, t in ROULETTE_POCKET_TIER.items() if t == tier])
    if isinstance(prize, str):
        amount = int(prize.split(":")[1])
        ng = update_gold(user.id, amount)
        result = f"🎡 مبروك {user.mention}! الكرة وقفت على **{win_number}** وربحت **Gold x{amount}** 🥇 • ذهبك: **{ng}**"
    else:
        nb = update_balance(user.id, prize)
        result = f"🎡 مبروك {user.mention}! الكرة وقفت على **{win_number}** وربحت **{fmt_money(prize)}** 💵 • رصيدك: **{fmt_money(nb)}**"
    try:
        av = await _avatar_bytes(user)
        buf = await _run_sync(_render_roulette_sync, av, _clean_name(user.display_name), tier, win_number)
        sent = await message.reply(content=f"🎡 {user.mention} العجلة تدور...", file=discord.File(buf, filename="roulette.gif"), mention_author=False)
        await asyncio.sleep(3.6)
        try:
            await sent.edit(content=result)
        except discord.HTTPException:
            await message.channel.send(result)
    except Exception as e:
        print(f"⚠️ تعذّر رسم الروليت: {e}")
        await message.reply(result, mention_author=False)


# =====================================================================
#                          🍒  فواكه
# =====================================================================
async def cmd_fruits(message: discord.Message):
    user = message.author
    final = [random.choice(FRUIT_NAMES) for _ in range(3)]
    if final[0] == final[1] == final[2]:
        amount, text, outcome = 1500, "ثلاثي مطابق!", "jackpot"
    elif len(set(final)) == 2:
        amount, text, outcome = 300, "ثنائي متطابق", "win"
    else:
        amount, text, outcome = -150, "ما طلع شي..", "lose"
    nb = update_balance(user.id, amount)
    av = await _avatar_bytes(user)
    buf = await _run_sync(_render_slots_sync, av, _clean_name(user.display_name), final, text, _signed(amount), outcome)
    sent = await message.reply(content=f"🎰 {user.mention} الماكينة تدور...", file=discord.File(buf, filename="slots.gif"), mention_author=False)
    await asyncio.sleep(2.6)
    try:
        await sent.edit(content=f"🎰 {user.mention} • رصيدك: **{fmt_money(nb)}**")
    except discord.HTTPException:
        pass


# =====================================================================
#                    🎮  حجرة ورقة مقص (بصور)
# =====================================================================
RPS_CHOICES = {"rock": "✊", "paper": "🖐️", "scissors": "✌️"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


class RPSView(discord.ui.View):
    def __init__(self, owner: discord.Member):
        super().__init__(timeout=45)
        self.owner = owner
        for key, emoji in RPS_CHOICES.items():
            b = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.secondary)
            b.callback = self._cb(key)
            self.add_item(b)

    def _cb(self, key):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
            await interaction.response.defer()
            bot_pick = random.choice(list(RPS_CHOICES))
            if key == bot_pick:
                amount, outcome, text = 0, "tie", "تعادل"
            elif RPS_BEATS[key] == bot_pick:
                amount, outcome, text = random.randint(150, 400), "win", "فزت!"
            else:
                amount, outcome, text = -random.randint(100, 300), "lose", "خسرت"
            nb = update_balance(interaction.user.id, amount)
            for c in self.children:
                c.disabled = True
            bot_av, user_av = await _avatar_bytes(bot.user), await _avatar_bytes(interaction.user)
            buf = await _run_sync(_render_rps_sync, bot_av, user_av, _clean_name(interaction.user.display_name), key, bot_pick,
                                  outcome, text, _signed(amount) if amount else "$0")
            await interaction.edit_original_response(content=f"🎮 {interaction.user.mention} • رصيدك: **{fmt_money(nb)}**",
                                                     attachments=[discord.File(buf, filename="rps.png")], view=self)
        return cb

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True


async def cmd_rps(message: discord.Message):
    f = await make_card(message.author, "حجرة ورقة مقص", "اختر سلاحك من الأزرار تحت", icon="dice")
    await message.reply(content=f"🎮 {message.author.mention}", file=f, view=RPSView(message.author), mention_author=False)


# =====================================================================
#              🎨  لون: أي لون أكثر عدداً بالشبكة؟ (مهارة بدل تخمين أعمى)
# =====================================================================
COLOR_EMOJI = {"red": "🟥", "blue": "🟦", "orange": "🟧", "purple": "🟪", "green": "🟩"}
COLOR_AR = {"red": "الأحمر", "blue": "الأزرق", "orange": "البرتقالي", "purple": "البنفسجي", "green": "الأخضر"}


def get_color_attempts(user_id: int) -> dict:
    db = load_db()
    uid, now = str(user_id), _now_ts()
    rec = db["color_game"].get(uid)
    if not rec or rec.get("reset_at", 0) <= now:
        rec = {"count": COLOR_MAX_ATTEMPTS, "reset_at": now + COLOR_RESET_HOURS * 3600}
        db["color_game"][uid] = rec
        save_db(db)
    return rec


def consume_color_attempt(user_id: int) -> int:
    rec = get_color_attempts(user_id)
    db = load_db()
    rec["count"] = max(0, rec["count"] - 1)
    db["color_game"][str(user_id)] = rec
    save_db(db)
    return rec["count"]


def _make_color_grid(rows=8, cols=9):
    keys = list(COLOR_RGB)
    while True:
        grid = [random.choice(keys) for _ in range(rows * cols)]
        counts = sorted(((grid.count(k), k) for k in keys), reverse=True)
        if counts[0][0] - counts[1][0] >= 2:
            return grid, counts[0][1]


class ColorGameView(discord.ui.View):
    def __init__(self, owner, grid, answer):
        super().__init__(timeout=60)
        self.owner, self.grid, self.answer = owner, grid, answer
        for key, emoji in COLOR_EMOJI.items():
            b = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.secondary)
            b.callback = self._cb(key)
            self.add_item(b)

    def _cb(self, key):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.owner.id:
                return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
            await interaction.response.defer()
            left = consume_color_attempt(interaction.user.id)
            for c in self.children:
                c.disabled = True
            av = await _avatar_bytes(interaction.user)
            if key == self.answer:
                amt = random.randint(500, 1500)
                nb = update_balance(interaction.user.id, amt)
                reveal = (self.answer, True, "صح! اخترت اللون الأكثر", f"{_signed(amt)}  •  المحاولات المتبقية {left}/{COLOR_MAX_ATTEMPTS}")
            else:
                nb = get_balance(interaction.user.id)
                reveal = (self.answer, False, f"غلط! الأكثر كان اللون {COLOR_AR[self.answer]}", f"المحاولات المتبقية {left}/{COLOR_MAX_ATTEMPTS}")
            buf = await _run_sync(_render_colors_sync, self.grid, 8, 9, _clean_name(interaction.user.display_name), av, "", reveal)
            await interaction.edit_original_response(content=f"🎨 {interaction.user.mention} • رصيدك: **{fmt_money(nb)}**",
                                                     attachments=[discord.File(buf, filename="colors.png")], view=self)
        return cb

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True


async def cmd_colors(message: discord.Message):
    user = message.author
    rec = get_color_attempts(user.id)
    if rec["count"] <= 0:
        rem = rec["reset_at"] - _now_ts()
        f = await make_card(user, "خمن اللون", f"خلصت محاولاتك اليوم , ترجع لك بعد {format_clock(rem)}", amount="0/25", icon="dice")
        return await message.reply(content=f"🎨 {user.mention}", file=f, mention_author=False)
    grid, answer = _make_color_grid()
    av = await _avatar_bytes(user)
    used = COLOR_MAX_ATTEMPTS - rec["count"]
    buf = await _run_sync(_render_colors_sync, grid, 8, 9, _clean_name(user.display_name), av, f"المحاولات: {used}/{COLOR_MAX_ATTEMPTS}")
    await message.reply(content=f"🎨 {user.mention}", file=discord.File(buf, filename="colors.png"), view=ColorGameView(user, grid, answer), mention_author=False)


# =====================================================================
#                      🛒  متجر الممتلكات (بصور)
# =====================================================================
async def _shop_reply(interaction, title, main, amount, side, icon="coins"):
    f = await make_card(interaction.user, title, main, amount=amount, side=side, icon=icon)
    await interaction.followup.send(file=f, ephemeral=True)


class PropertyBuyView(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=120)
        self.owner = owner
        for key, info in PROPERTY_CATALOG.items():
            b = discord.ui.Button(label=f"{info['emoji']} {info['name']} ({info['price']:,})", style=discord.ButtonStyle.primary)
            b.callback = self._buy(key, info)
            self.add_item(b)
        g = discord.ui.Button(label=f"🥇 Gold x{GOLD_PACK_AMOUNT} ({GOLD_PACK_PRICE:,})", style=discord.ButtonStyle.secondary)
        g.callback = self._gold
        self.add_item(g)
        s = discord.ui.Button(label=f"📈 سهم ({STOCK_PRICE:,})", style=discord.ButtonStyle.secondary)
        s.callback = self._stock
        self.add_item(s)

    async def _guard(self, interaction):
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("❌ هذا مو متجرك!", ephemeral=True)
            return False
        await interaction.response.defer(ephemeral=True)
        return True

    def _buy(self, key, info):
        async def cb(interaction):
            if not await self._guard(interaction):
                return
            if get_balance(interaction.user.id) < info["price"]:
                return await interaction.followup.send("❌ رصيدك ما يكفي.", ephemeral=True)
            nb = update_balance(interaction.user.id, -info["price"])
            cnt = update_property(interaction.user.id, key, 1)
            await _shop_reply(interaction, "عملية شراء ناجحة", f"اشتريت : {info['name']} (عندك الآن {cnt})",
                              _signed(-info["price"]), f"رصيدك الحالي : {fmt_money(nb)}", "chart_up")
        return cb

    async def _gold(self, interaction):
        if not await self._guard(interaction):
            return
        if get_balance(interaction.user.id) < GOLD_PACK_PRICE:
            return await interaction.followup.send("❌ رصيدك ما يكفي.", ephemeral=True)
        nb = update_balance(interaction.user.id, -GOLD_PACK_PRICE)
        ng = update_gold(interaction.user.id, GOLD_PACK_AMOUNT)
        await _shop_reply(interaction, "عملية شراء ناجحة", f"اشتريت : Gold x{GOLD_PACK_AMOUNT} (عندك {ng})",
                          _signed(-GOLD_PACK_PRICE), f"رصيدك الحالي : {fmt_money(nb)}", "gold")

    async def _stock(self, interaction):
        if not await self._guard(interaction):
            return
        if get_balance(interaction.user.id) < STOCK_PRICE:
            return await interaction.followup.send("❌ رصيدك ما يكفي.", ephemeral=True)
        nb = update_balance(interaction.user.id, -STOCK_PRICE)
        cnt = update_property(interaction.user.id, "stocks", 1)
        await _shop_reply(interaction, "عملية شراء ناجحة", f"اشتريت : سهم (عندك الآن {cnt})",
                          _signed(-STOCK_PRICE), f"رصيدك الحالي : {fmt_money(nb)}", "chart_up")


class PropertySellView(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=120)
        self.owner = owner
        for key, info in PROPERTY_CATALOG.items():
            b = discord.ui.Button(label=f"{info['emoji']} بيع {info['name']} ({int(info['price'] * PROPERTY_SELL_RATIO):,})", style=discord.ButtonStyle.danger)
            b.callback = self._sell(key, info)
            self.add_item(b)
        s = discord.ui.Button(label=f"📉 بيع سهم ({int(STOCK_PRICE * PROPERTY_SELL_RATIO):,})", style=discord.ButtonStyle.secondary)
        s.callback = self._stock
        self.add_item(s)

    async def _guard(self, interaction):
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("❌ هذا مو متجرك!", ephemeral=True)
            return False
        await interaction.response.defer(ephemeral=True)
        return True

    def _sell(self, key, info):
        async def cb(interaction):
            if not await self._guard(interaction):
                return
            if get_properties(interaction.user.id).get(key, 0) <= 0:
                return await interaction.followup.send("❌ ما عندك وحدة من هذي تبيعها.", ephemeral=True)
            price = int(info["price"] * PROPERTY_SELL_RATIO)
            update_property(interaction.user.id, key, -1)
            nb = update_balance(interaction.user.id, price)
            await _shop_reply(interaction, "عملية بيع ناجحة", f"بعت : {info['name']}", _signed(price), f"رصيدك الحالي : {fmt_money(nb)}", "coins")
        return cb

    async def _stock(self, interaction):
        if not await self._guard(interaction):
            return
        if get_properties(interaction.user.id).get("stocks", 0) <= 0:
            return await interaction.followup.send("❌ ما عندك أسهم تبيعها.", ephemeral=True)
        price = int(STOCK_PRICE * PROPERTY_SELL_RATIO)
        update_property(interaction.user.id, "stocks", -1)
        nb = update_balance(interaction.user.id, price)
        await _shop_reply(interaction, "عملية بيع ناجحة", "بعت : سهم", _signed(price), f"رصيدك الحالي : {fmt_money(nb)}", "coins")


async def cmd_shop(message: discord.Message, sell: bool):
    user = message.author
    props = get_properties(user.id)
    rows = []
    for k, info in PROPERTY_CATALOG.items():
        price = int(info["price"] * PROPERTY_SELL_RATIO) if sell else info["price"]
        rows.append((info["name"], fmt_money(price), f"عندك {props.get(k, 0)}", None))
    if sell:
        rows.append(("سهم", fmt_money(int(STOCK_PRICE * PROPERTY_SELL_RATIO)), f"عندك {props.get('stocks', 0)}", None))
    else:
        rows.append((f"Gold x{GOLD_PACK_AMOUNT}", fmt_money(GOLD_PACK_PRICE), f"عندك {get_gold(user.id)}", None))
        rows.append(("سهم", fmt_money(STOCK_PRICE), f"عندك {props.get('stocks', 0)}", None))
    buf = await _run_sync(_render_table_sync, "المتجر - بيع" if sell else "المتجر - شراء",
                          ["الصنف", "سعر البيع" if sell else "السعر", "ممتلكاتك"], rows, "اختر من الأزرار تحت", "gold")
    view = PropertySellView(user) if sell else PropertyBuyView(user)
    await message.reply(content=f"🛒 {user.mention}", file=discord.File(buf, filename="shop.png"), view=view, mention_author=False)


# =====================================================================
#                      💎  ألغام (Mines) الاحترافية
# =====================================================================
class MinesGameView(discord.ui.View):
    """شبكة 5x4 + 3 قنابل + مضاعف احتمالي حقيقي. بدون رهان = مكافأة مجانية (ما تخسر شي).
    برهان = يتخصم الرهان بالبداية ويتضاعف مع كل مربع آمن، وتسحب بأي وقت."""

    def __init__(self, player: discord.Member, avatar: bytes, bet: int = 0):
        super().__init__(timeout=150)
        self.player, self.avatar, self.bet = player, avatar, bet
        self.bombs = random.sample(range(MINES_TOTAL), MINES_BOMB_COUNT)
        self.revealed: list = []
        self.status = "playing"
        self.hit = None
        self.message = None
        self.lock = asyncio.Lock()
        for i in range(MINES_TOTAL):
            b = discord.ui.Button(label=str(i + 1), style=discord.ButtonStyle.secondary, row=i // MINES_COLS)
            b.callback = self._tile_cb(i, b)
            self.add_item(b)
        self.cash_btn = discord.ui.Button(label="💰 اسحب مكافأتك", style=discord.ButtonStyle.success, row=4, disabled=True)
        self.cash_btn.callback = self._cash
        self.add_item(self.cash_btn)

    # ---- حسابات ----
    @property
    def safe(self) -> int:
        return len(self.revealed)

    @property
    def mult(self) -> float:
        return mines_multiplier(MINES_BOMB_COUNT, self.safe)

    def payout(self) -> int:
        base = self.bet if self.bet else MINES_BASE_REWARD
        return int(base * self.mult)

    def state(self) -> dict:
        ended = self.status != "playing"
        if self.status == "lost":
            reward, label, mult = fmt_money(0) if not self.bet else f"-{fmt_money(self.bet)}", "النتيجة", 0.0
        elif self.status == "won":
            reward, label, mult = _signed(self.payout() - (self.bet or 0)) if self.bet else _signed(self.payout()), "الربح", self.mult
        else:
            reward, label, mult = fmt_money(self.payout()), "لو سحبت الحين", self.mult
        return dict(avatar=self.avatar, name=_clean_name(self.player.display_name),
                    mode=(f"رهان {fmt_money(self.bet)}" if self.bet else "بدون رهان • مكافأة مجانية"),
                    status=self.status, revealed=list(self.revealed), bombs=self.bombs if ended else None, hit=self.hit,
                    safe=self.safe, bombs_n=MINES_BOMB_COUNT, mult=mult, reward=reward, reward_label=label)

    def _sync_buttons(self):
        ended = self.status != "playing"
        for i, child in enumerate(self.children[:MINES_TOTAL]):
            if i in self.revealed:
                child.label, child.style, child.disabled = "💎", discord.ButtonStyle.success, True
            elif ended and i in self.bombs:
                child.label, child.style, child.disabled = "💣", (discord.ButtonStyle.danger if i == self.hit else discord.ButtonStyle.secondary), True
            else:
                child.disabled = ended
        self.cash_btn.disabled = ended or self.safe == 0
        if not ended and self.safe:
            self.cash_btn.label = f"💰 اسحب {fmt_money(self.payout())}"

    async def _push(self, interaction, anim_kind, idx, content):
        self._sync_buttons()
        buf, name = await _run_sync(_render_mines_sync, self.state(), anim_kind, idx)
        await interaction.edit_original_response(content=content, attachments=[discord.File(buf, filename=name)], view=self)

    def _tile_cb(self, idx, button):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.player.id:
                return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
            async with self.lock:
                if self.status != "playing" or idx in self.revealed:
                    return await interaction.response.defer()
                await interaction.response.defer()
                if idx in self.bombs:
                    self.status, self.hit = "lost", idx
                    bal = get_balance(self.player.id)
                    await self._push(interaction, "bomb", idx, f"💥 {self.player.mention} انفجرت القنبلة! • رصيدك: **{fmt_money(bal)}**")
                    self.stop()
                    return
                self.revealed.append(idx)
                if self.safe == MINES_TOTAL - MINES_BOMB_COUNT:        # فتح كل الآمن = سحب تلقائي
                    await self._finish_win(interaction, auto=True)
                    return
                await self._push(interaction, "safe", idx, f"💎 {self.player.mention} • لو سحبت الحين: **{fmt_money(self.payout())}** (x{self.mult:.2f})")
        return cb

    async def _finish_win(self, interaction, auto=False):
        self.status = "won"
        pay = self.payout()
        nb = update_balance(self.player.id, pay)
        await self._push(interaction, None, None, f"💰 {self.player.mention} {'فتحت كل المربعات الآمنة! ' if auto else ''}سحبت **{fmt_money(pay)}** • رصيدك: **{fmt_money(nb)}**")
        self.stop()

    async def _cash(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
        async with self.lock:
            if self.status != "playing" or not self.safe:
                return await interaction.response.defer()
            await interaction.response.defer()
            await self._finish_win(interaction)

    async def on_timeout(self):
        async with self.lock:
            if self.status != "playing":
                return
            # انتهى الوقت: برهان = نسحب تلقائي (أو نرجّع الرهان لو ما فتح شي) | بدون رهان = ينتهي
            if self.bet:
                self.status = "won" if self.safe else "lost"
                if self.safe:
                    update_balance(self.player.id, self.payout())
                else:
                    update_balance(self.player.id, self.bet)
                    self.status = "won"
            else:
                self.status = "won" if self.safe else "lost"
                if self.safe:
                    update_balance(self.player.id, self.payout())
            self._sync_buttons()
            for c in self.children:
                c.disabled = True
            try:
                buf, name = await _run_sync(_render_mines_sync, self.state(), None, None)
                await self.message.edit(content=f"⌛ {self.player.mention} انتهى الوقت وانسحبت المكافأة تلقائياً.",
                                        attachments=[discord.File(buf, filename=name)], view=self)
            except Exception:
                pass


async def cmd_mines(message: discord.Message, amount):
    user = message.author
    bet = 0
    if amount is not None:
        err, bal = _bet_check(user, amount, MINES_MIN_BET)
        if err:
            return await message.reply(err, mention_author=False)
        bet = amount
        update_balance(user.id, -bet)
    set_cooldown(user.id, "ألغام")
    av = await _avatar_bytes(user)
    view = MinesGameView(user, av, bet)
    buf, name = await _run_sync(_render_mines_sync, view.state(), None, None)
    intro = (f"⛏️ **Mines** • {user.mention} • رهان **{fmt_money(bet)}** 💣 فيه {MINES_BOMB_COUNT} قنابل — كل مربع آمن يرفع المضاعف، اسحب بأي وقت."
             if bet else f"⛏️ **Mines** • {user.mention} • بدون رهان: لو انفجرت قنبلة رصيدك ما يتأثر 💣 ({MINES_BOMB_COUNT} قنابل)")
    view.message = await message.reply(content=intro, file=discord.File(buf, filename=name), view=view, mention_author=False)


# =====================================================================
#                          🔀  موزّع الأوامر الإضافية
# =====================================================================
EXTRA_BANK_ACTIONS = {
    "راتب": ("salary", "راتب"), "بخشيش": ("tip", "بخشيش"), "حظ": ("luck", "حظ"), "روليت": ("roulette", "روليت"),
    "نهب": ("rob", "نهب"), "حماية": ("protection", None), "رهان": ("bet", "رهان"), "قمار": ("gamble", "قمار"),
    "استثمار": ("invest", "استثمار"), "تداول": ("invest", "تداول"), "لعبه": ("rps", None), "لعبة": ("rps", None),
    "فواكه": ("fruits", None), "لون": ("colors", None), "تسريع": ("speedup", None),
    "ممتلكات": ("properties", None), "اغنى": ("richest", None), "أغنى": ("richest", None),
    "اوامر": ("help", None), "أوامر": ("help", None),
}
_ACT_FUNCS = {
    "salary": act_salary, "tip": act_tip, "luck": act_luck, "rob": act_rob, "protection": act_protection,
    "bet": act_bet, "gamble": act_gamble, "invest": act_invest, "speedup": act_speedup,
    "properties": act_properties, "richest": act_richest, "help": act_help,
}


async def handle_extra_bank(message: discord.Message, word: str, rest: list) -> bool:
    """يعالج أوامر البنك المرجّعة. يرجع True لو الكلمة منها."""
    spec = EXTRA_BANK_ACTIONS.get(word)
    if not spec:
        return False
    action, cd = spec
    user = message.author
    if cd:
        notice = cooldown_notice(user.id, cd)
        if notice:
            await message.reply(notice, mention_author=False)
            return True
    amount = parse_amount_ctx(rest, user.id)
    try:
        async with message.channel.typing():
            if action == "roulette":
                await cmd_roulette(message)
                return True
            if action == "fruits":
                await cmd_fruits(message)
                return True
            if action == "rps":
                await cmd_rps(message)
                return True
            if action == "colors":
                await cmd_colors(message)
                return True
            err, res = await _ACT_FUNCS[action](user, amount=amount, game=word if action == "invest" else None)
    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.reply(f"⚠️ صار خطأ بالبنك: {e}", mention_author=False)
        return True
    if err:
        await message.reply(err, mention_author=False)
    else:
        text, file = res
        await message.reply(content=text, file=file, mention_author=False) if file else await message.reply(content=text, mention_author=False)
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
