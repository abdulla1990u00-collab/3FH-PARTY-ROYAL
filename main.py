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
MINES_BOMB_COUNT = 1          # عدد القنابل المخفية
MINES_MULTIPLIER_STEP = 0.3   # مقدار زيادة الأرباح بكل مربع آمن
MINES_BASE_REWARD = 100        # المكافأة الأساسية - لا يوجد رهان ولا خصم عند الخسارة

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


def _resolve_font_paths() -> dict:
    if _font_paths_cache:
        return _font_paths_cache
    custom = []
    for pattern in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
        custom += sorted(glob.glob(os.path.join(FILES_DIR, "fonts", pattern)))
    _font_paths_cache["ar"] = _first_existing(
        [os.getenv("BANK_FONT_AR"), WELCOME_FONT_PATH] + custom + [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ])
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
    "تحويل": "transfer", "نرد": "dice", "الغام": "mines", "ألغام": "mines", "شراء": "buy", "اشتري": "buy", "بيع": "sell",
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
    action = BANK_TEXT_TRIGGERS.get(parts[0]) if parts else None
    if not action:
        return False

    rest = [p for p in parts[1:] if not re.fullmatch(r"<@!?\d+>", p)]
    amount = parse_amount(" ".join(rest))
    mention = next((m for m in message.mentions if isinstance(m, discord.Member) and not m.bot), None)
    author = message.author

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
            elif action == "mines":
                await message.reply(
                    f"⛏️ **Mines** • {author.mention}\n"
                    "فيه قنبلة وحدة مخفية بين 9 مربعات 💣 — كل مربع آمن يكبّر مكافأتك، وتقدر تسحبها بأي وقت.\n"
                    "(مافيه رهان - لو انفجرت القنبلة رصيدك ما يتأثر)",
                    view=MinesGameView(author), mention_author=False)
                return True
            elif action == "dice":
                if amount is None:
                    err, res = "الاستخدام: `نرد 100`", None
                else:
                    err, res = await act_dice(author, amount)
            elif action in ("buy", "sell"):
                key = find_asset_key(rest)
                if not key:
                    err, res = f"الاستخدام: `{parts[0]} ذهب 500` — الأصول: " + "، ".join(a["name"] for a in ASSETS.values()), None
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

    def progress_text(self) -> str:
        potential_win = int(MINES_BASE_REWARD * self.multiplier)
        return (
            f"⛏️ **Mines** • {self.player.mention}\n"
            f"المضاعف: **x{self.multiplier:.1f}** • لو سحبت الحين تاخذ: **{fmt_money(potential_win)}**"
        )

    async def _finish(self, interaction: discord.Interaction, main_text: str, amount: str, side=None):
        for child in self.children:
            child.disabled = True
        await interaction.response.defer()
        bal = get_balance(self.player.id)
        file = await make_card(self.player, "لعبة الألغام", main_text, amount=amount, side=side, icon="coins")
        await interaction.edit_original_response(content=f"💵 **{fmt_money(bal)}**", attachments=[file], view=self)

    async def _on_tile_click(self, interaction: discord.Interaction, button: discord.ui.Button, index: int):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
        if self.game_over:
            return await interaction.response.send_message("⚠️ اللعبة خلصت.", ephemeral=True)

        if index == self.bomb_index:
            self.game_over = True
            button.label = "💣"
            button.style = discord.ButtonStyle.danger
            return await self._finish(interaction, "انفجرت القنبلة ! ما حصلت مكافأة", "$0", side="رصيدك ما تأثر")

        self.safe_clicks += 1
        self.multiplier += MINES_MULTIPLIER_STEP
        button.label = "💎"
        button.style = discord.ButtonStyle.success
        button.disabled = True
        self.cash_out_button.disabled = False
        await interaction.response.edit_message(content=self.progress_text(), view=self)

    async def cash_out(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
        if self.game_over:
            return await interaction.response.send_message("⚠️ اللعبة خلصت.", ephemeral=True)

        self.game_over = True
        winnings = int(MINES_BASE_REWARD * self.multiplier)
        update_balance(self.player.id, winnings)
        await self._finish(interaction, "سحبت مكافأتك بنجاح", f"+{fmt_money(winnings)}", side=f"المضاعف x{self.multiplier:.1f}")

    async def on_timeout(self):
        if not self.game_over:
            for child in self.children:
                child.disabled = True


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
