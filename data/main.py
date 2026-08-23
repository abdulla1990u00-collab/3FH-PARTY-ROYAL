"""
=====================================================================
   3FH PARTY ROYAL - Discord Bot
   بوت متكامل: ترحيب + نظام تذاكر + اقتراحات + إعلانات + ردود آلية
   Python 3.13  |  discord.py 2.x
=====================================================================
طريقة التشغيل:
   1) pip install -r requirements.txt
   2) عدّل ملف .env وضع فيه التوكن وجميع الـ IDs
   3) python main.py
=====================================================================
"""

import os
import json
import re
import random
import io
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

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
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "database.json")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
BANNERS_DIR = os.path.join(DATA_DIR, "banners")


def ensure_data_files():
    """التأكد من وجود مجلد وملف قاعدة البيانات، وإنشائهم إذا لم يكونا موجودين."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    os.makedirs(BANNERS_DIR, exist_ok=True)
    if not os.path.exists(DB_FILE):
        default_db = {
            "ticket_counter": 0,       # آخر رقم تذكرة تم استخدامه
            "open_tickets": {},        # {user_id: channel_id} - لمنع فتح أكثر من تذكرة
            "tickets": {},             # {channel_id: {...بيانات التذكرة...}}
            "suggestions": {},         # {message_id: {"up": [], "down": []}}
            "ratings": {},             # {ticket_number: {"stars": int, "user_id": int}}
            "corrections": {},         # {الكلمة_الخطأ: الكلمة_الصح} - نظام التصحيح الإملائي
            "dot_sent_users": [],      # قائمة آيديات الأعضاء اللي سبق أرسلوا "." (لتمييز أول مرة عن المرات اللي بعدها)
            "auto_replies": {},        # {الكلمة_المحفزة: الرد} - ردود آلية مخصصة تُضاف من ديسكورد
            "levels": {},              # {user_id: {"xp": int, "level": int}} - نظام اللفلات
            "economy": {},              # {user_id: الرصيد} - نظام البنك
            "temp_voice_channels": {},  # {channel_id: owner_id} - الرومات الصوتية المؤقتة الحالية
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
                "temp_voice_hub_id": None,    # الروم الصوتي "➕ إنشاء روم" - يُضبط بأمر /voice_setup
                "temp_voice_category_id": None,  # الكاتيجوري اللي تُنشأ فيه الرومات المؤقتة (فاضي = نفس كاتيجوري الهَب)
                "temp_voice_name_template": "روم {user}",  # قالب اسم الروم المؤقت الجديد
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
            "temp_voice_hub_id": None,
            "temp_voice_category_id": None,
            "temp_voice_name_template": "روم {user}",
        }
    else:
        data["settings"].setdefault("ticket_banner_path", None)
        data["settings"].setdefault("suggestion_banner_path", None)
        data["settings"].setdefault("welcome_template_path", None)
        data["settings"].setdefault("welcome_position", dict(DEFAULT_WELCOME_POSITION))
        data["settings"].setdefault("ticket_allowed_roles", [])
        data["settings"].setdefault("custom_messages", {})
        data["settings"].setdefault("temp_voice_hub_id", None)
        data["settings"].setdefault("temp_voice_category_id", None)
        data["settings"].setdefault("temp_voice_name_template", "روم {user}")
        data["settings"].pop("antinuke", None)
        data["settings"].pop("dashboard_secret", None)
        data["settings"].pop("welcome_banner_path", None)
        data["settings"].pop("announcement_banner_path", None)
    data.setdefault("corrections", {})
    data.setdefault("dot_sent_users", [])
    data.setdefault("auto_replies", {})
    data.setdefault("levels", {})
    data.setdefault("economy", {})
    data.setdefault("temp_voice_channels", {})
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

bot = commands.Bot(command_prefix="!", intents=intents)

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
    "salam_reply": {
        "label": "💬 رد السلام عليكم",
        "fields": {
            "text": {"label": "الرد", "style": "short", "default": "وعليكم السلام ورحمة الله وبركاته ❤️"},
        },
    },
    "dot_reply_new": {
        "label": "🔵 رد (.) - أول مرة (أعضاء عاديين)",
        "fields": {
            "text": {"label": "الرد", "style": "short", "default": "م بغيت تطول وينك"},
        },
    },
    "dot_reply_repeat": {
        "label": "🔵 رد (.) - المرات اللي بعدها (أعضاء عاديين)",
        "fields": {
            "text": {"label": "الرد", "style": "short", "default": "يليل النشبه فكنا واا"},
        },
    },
    "dot_reply_admin": {
        "label": "🟡 ردود (.) للإدارة - كل رد بسطر لحاله",
        "fields": {
            "text": {
                "label": "الردود (كل رد بسطر منفصل - يُختار وحد عشوائي)",
                "style": "long",
                "default": "يلبيه وينك من اول 👑\nيليل النشبه فكنا\nاشتقنا لك لا تطول الغيبات🫣",
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
            ("/voice_setup", "تحديد روم الهَب للرومات الصوتية المؤقتة (الأونر والإدارة العليا بس)"),
            ("🎧 الرومات المؤقتة", "أي عضو يدخل روم الهَب يتنشأ له روم خاص فيه لوحة تحكم بالأزرار (قفل/فتح/تسمية/حد أعضاء/طرد/سماح/منع/استلام)"),
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
    "admin": {
        "label": "⚙️ إدارة عامة",
        "emoji": "⚙️",
        "commands": [
            ("/clear", "حذف رسائل بهذا الروم أو كل رومات السيرفر"),
            ("/add_auto_reply", "إضافة رد آلي مخصص"),
            ("/remove_auto_reply", "حذف رد آلي مخصص"),
            ("/list_auto_replies", "عرض كل الردود الآلية المضافة"),
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


class TempVoiceRenameModal(discord.ui.Modal, title="✏️ تغيير اسم الروم"):
    name = discord.ui.TextInput(label="الاسم الجديد", placeholder="مثال: قهوة الصباح ☕", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await channel.edit(name=str(self.name)[:100], reason=f"إعادة تسمية بواسطة {interaction.user}")
        await interaction.response.send_message(f"✅ صار اسم الروم: **{str(self.name)[:100]}**", ephemeral=True)


class TempVoiceLimitModal(discord.ui.Modal, title="👥 تحديد أقصى عدد أعضاء"):
    limit = discord.ui.TextInput(label="العدد (0 = بلا حد)", placeholder="مثال: 5", max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        try:
            limit_value = max(0, min(int(str(self.limit)), 99))
        except ValueError:
            return await interaction.response.send_message("❌ اكتب رقم صحيح بس.", ephemeral=True)
        await channel.edit(user_limit=limit_value, reason=f"تحديد حد الأعضاء بواسطة {interaction.user}")
        await interaction.response.send_message(
            f"✅ صار حد الأعضاء: **{limit_value if limit_value else 'بلا حد'}**", ephemeral=True
        )


def _check_temp_voice_ownership(interaction: discord.Interaction):
    """يتأكد أن الروم اللي فيه اللوحة هو روم مؤقت والعضو ضاغط الزر هو مالكه (أو إدارة). يرجع (channel, رسالة_خطأ)."""
    channel = interaction.channel
    if not isinstance(channel, discord.VoiceChannel):
        return None, "❌ هذي اللوحة تشتغل بس داخل روم صوتي مؤقت."
    db = load_db()
    temp_channels = db.get("temp_voice_channels", {})
    owner_id = temp_channels.get(str(channel.id))
    if owner_id is None:
        return None, "❌ هذا الروم مو روم صوتي مؤقت."
    if owner_id != interaction.user.id and not interaction.user.guild_permissions.manage_channels:
        return None, "❌ بس صاحب الروم يقدر يستخدم هذي اللوحة."
    return channel, None


class TempVoiceControlView(discord.ui.View):
    """لوحة تحكم دائمة تُرسل تلقائياً داخل كل روم صوتي مؤقت - تحكم كامل بضغطة زر بدل الأوامر."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="قفل", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="tempvoice_lock", row=0)
    async def lock_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await channel.set_permissions(interaction.guild.default_role, connect=False, reason=f"قفل الروم بواسطة {interaction.user}")
        await interaction.response.send_message("🔒 تم قفل الروم.", ephemeral=True)

    @discord.ui.button(label="فتح", emoji="🔓", style=discord.ButtonStyle.secondary, custom_id="tempvoice_unlock", row=0)
    async def unlock_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await channel.set_permissions(interaction.guild.default_role, connect=True, reason=f"فتح الروم بواسطة {interaction.user}")
        await interaction.response.send_message("🔓 تم فتح الروم.", ephemeral=True)

    @discord.ui.button(label="تسمية", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="tempvoice_rename", row=0)
    async def rename_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.send_modal(TempVoiceRenameModal())

    @discord.ui.button(label="الحد الأقصى", emoji="👥", style=discord.ButtonStyle.secondary, custom_id="tempvoice_limit", row=0)
    async def limit_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.send_modal(TempVoiceLimitModal())

    @discord.ui.button(label="استلام الملكية", emoji="👑", style=discord.ButtonStyle.primary, custom_id="tempvoice_claim", row=1)
    async def claim_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.VoiceChannel):
            return await interaction.response.send_message("❌ هذي اللوحة تشتغل بس داخل روم صوتي مؤقت.", ephemeral=True)
        db = load_db()
        temp_channels = db.get("temp_voice_channels", {})
        owner_id = temp_channels.get(str(channel.id))
        if owner_id is None:
            return await interaction.response.send_message("❌ هذا الروم مو روم صوتي مؤقت.", ephemeral=True)
        owner_still_here = any(m.id == owner_id for m in channel.members)
        if owner_still_here and owner_id != interaction.user.id:
            return await interaction.response.send_message("❌ صاحب الروم الأصلي لسا موجود بالروم.", ephemeral=True)
        temp_channels[str(channel.id)] = interaction.user.id
        db["temp_voice_channels"] = temp_channels
        save_db(db)
        try:
            await channel.set_permissions(
                interaction.user, manage_channels=True, move_members=True, mute_members=True, deafen_members=True,
                connect=True, speak=True, reason="استلام ملكية الروم المؤقت",
            )
        except Exception as e:
            print(f"❌ خطأ أثناء ضبط صلاحيات مالك الروم الجديد: {e}")
        await interaction.response.send_message("✅ صرت صاحب هذا الروم الآن.", ephemeral=True)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="👢 اطرد عضو من الروم", custom_id="tempvoice_kick_select", row=2)
    async def kick_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        member = select.values[0]
        if not isinstance(member, discord.Member) or not member.voice or member.voice.channel != channel:
            return await interaction.response.send_message("❌ هذا العضو مو داخل الروم.", ephemeral=True)
        await member.move_to(None, reason=f"طرد من الروم المؤقت بواسطة {interaction.user}")
        await interaction.response.send_message(f"✅ تم طرد {member.mention} من الروم.", ephemeral=True)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="✅ سماح لعضو بالدخول", custom_id="tempvoice_permit_select", row=3)
    async def permit_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        member = select.values[0]
        await channel.set_permissions(member, connect=True, reason=f"سماح دخول بواسطة {interaction.user}")
        await interaction.response.send_message(f"✅ صار {member.mention} يقدر يدخل الروم.", ephemeral=True)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="🚫 منع عضو من الدخول", custom_id="tempvoice_reject_select", row=4)
    async def reject_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        channel, error = _check_temp_voice_ownership(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        member = select.values[0]
        await channel.set_permissions(member, connect=False, reason=f"منع دخول بواسطة {interaction.user}")
        if isinstance(member, discord.Member) and member.voice and member.voice.channel == channel:
            await member.move_to(None, reason=f"طرد بعد المنع بواسطة {interaction.user}")
        await interaction.response.send_message(f"🚫 صار {member.mention} ما يقدر يدخل الروم.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print("========== خطأ داخل لوحة تحكم الروم الصوتي ==========")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("=======================================================")
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
    bot.add_view(TempVoiceControlView())

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

    # --- نظام الرومات الصوتية المؤقتة ---
    await _handle_temp_voice_state(member, before, after)


async def _handle_temp_voice_state(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """ينشئ روم صوتي مؤقت خاص لأي عضو يدخل روم الهَب، ويحذف أي روم مؤقت يصير فاضي."""
    db = load_db()
    settings = db.get("settings", {})
    hub_id = settings.get("temp_voice_hub_id")
    temp_channels = db.get("temp_voice_channels", {})

    # أول شي: لو العضو طلع من روم مؤقت وصار فاضي، نحذفه (نسويها قبل منطق الإنشاء
    # عشان تشتغل حتى لو العضو انتقل مباشرة من روم مؤقت لروم الهَب بنفس الحدث)
    if before.channel and str(before.channel.id) in temp_channels:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete(reason="روم صوتي مؤقت فاضي")
            except Exception as e:
                print(f"❌ خطأ أثناء حذف روم صوتي مؤقت فاضي: {e}")
            temp_channels.pop(str(before.channel.id), None)
            db["temp_voice_channels"] = temp_channels
            save_db(db)

    # العضو دخل روم الهَب "➕ إنشاء روم"
    if hub_id and after.channel and after.channel.id == hub_id:
        guild = member.guild
        hub_channel = after.channel
        category = guild.get_channel(settings.get("temp_voice_category_id") or 0) or hub_channel.category

        name_template = settings.get("temp_voice_name_template", "روم {user}")
        channel_name = name_template.replace("{user}", member.display_name)[:100]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(),
            member: discord.PermissionOverwrite(
                manage_channels=True, move_members=True, mute_members=True, deafen_members=True, connect=True, speak=True,
            ),
            guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True, move_members=True),
        }
        try:
            new_channel = await guild.create_voice_channel(
                name=channel_name, category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites, reason=f"روم صوتي مؤقت لـ {member}",
            )
            await member.move_to(new_channel, reason="نقل لروم صوتي مؤقت جديد")
            temp_channels[str(new_channel.id)] = member.id
            db["temp_voice_channels"] = temp_channels
            save_db(db)

            panel_embed = discord.Embed(
                title="🎧 روم صوتي خاص فيك",
                description=(
                    f"هذا روم {member.mention} الخاص - تحكم فيه من الأزرار تحت، ما تحتاج تكتب أوامر.\n"
                    "لو طلعت منه، آخر واحد يفضى الروم يُحذف تلقائياً."
                ),
                color=WELCOME_COLOR,
            )
            await new_channel.send(embed=panel_embed, view=TempVoiceControlView())
        except Exception as e:
            print(f"❌ خطأ أثناء إنشاء روم صوتي مؤقت: {e}")


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

    # الردود الآلية تعمل فقط في روم الشات العام (لو تم تحديده) ولمن يملك رتبة العضو (لو تم تحديدها)
    channel_ok = (not GENERAL_CHAT_ID) or (message.channel.id == GENERAL_CHAT_ID)
    role_ok = True
    if MEMBER_ROLE_ID and isinstance(message.author, discord.Member):
        role_ok = any(r.id == MEMBER_ROLE_ID for r in message.author.roles)

    if channel_ok and role_ok:
        text = message.content.strip()

        if text == "السلام عليكم":
            await message.reply(get_custom_message("salam_reply", "text"), mention_author=False)

    # الرد على "." يشتغل لأي عضو بغض النظر عن رتبته (بس نفس قيد الروم لو محدد)
    if channel_ok and message.content.strip() == ".":
        is_admin_member = (
            isinstance(message.author, discord.Member) and message.author.guild_permissions.administrator
        )
        if is_admin_member:
            admin_dot_replies = [
                line.strip() for line in get_custom_message("dot_reply_admin", "text").split("\n") if line.strip()
            ]
            await message.reply(random.choice(admin_dot_replies), mention_author=False)
        else:
            db = load_db()
            sent_before = message.author.id in db["dot_sent_users"]
            if not sent_before:
                db["dot_sent_users"].append(message.author.id)
                save_db(db)
                await message.reply(get_custom_message("dot_reply_new", "text"), mention_author=False)
            else:
                await message.reply(get_custom_message("dot_reply_repeat", "text"), mention_author=False)

    # الردود الآلية المخصصة (مُضافة عبر /add_auto_reply) - تعمل بنفس قيد الروم والرتبة أعلاه
    if channel_ok and role_ok:
        db = load_db()
        auto_replies = db.get("auto_replies", {})
        trigger_text = message.content.strip()
        if trigger_text in auto_replies:
            await message.reply(auto_replies[trigger_text], mention_author=False)

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
            return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
        if self.game_over:
            return await interaction.response.send_message("⚠️ اللعبة خلصت.", ephemeral=True)

        if index == self.bomb_index:
            # انفجرت القنبلة - يخسر المكافأة المحتملة فقط، بدون أي خصم من رصيده
            self.game_over = True
            for child in self.children:
                child.disabled = True
            button.label = "💣"
            button.style = discord.ButtonStyle.danger
            embed = discord.Embed(
                title="💥 ما في مكافأة هالمرة!",
                description="وقعت بالقنبلة. رصيدك ما تأثر، جرب حظك مرة ثانية لاحقًا! 🍀",
                color=DANGER_COLOR,
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        # مربع آمن
        self.safe_clicks += 1
        self.multiplier += MINES_MULTIPLIER_STEP
        button.label = "💎"
        button.style = discord.ButtonStyle.success
        button.disabled = True
        self.cash_out_button.disabled = False

        potential_win = int(MINES_BASE_REWARD * self.multiplier)
        embed = discord.Embed(
            title="⛏️ لعبة البنك - Mines",
            description=(
                f"اللاعب: {self.player.mention}\n"
                f"المضاعف الحالي: **x{self.multiplier:.1f}**\n"
                f"لو سحبت الحين تاخذ: **{potential_win}** عملة (مكافأة، بدون أي رهان)"
            ),
            color=SUCCESS_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def cash_out(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ هذي مو لعبتك!", ephemeral=True)
        if self.game_over:
            return await interaction.response.send_message("⚠️ اللعبة خلصت.", ephemeral=True)

        self.game_over = True
        winnings = int(MINES_BASE_REWARD * self.multiplier)
        new_balance = update_balance(self.player.id, winnings)

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="✅ سحبت مكافأتك!",
            description=(
                f"ربحت **{winnings}** عملة (مضاعف x{self.multiplier:.1f})\n"
                f"رصيدك الحالي: **{new_balance}** عملة"
            ),
            color=SUCCESS_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if not self.game_over:
            # لو انتهت المهلة بدون سحب، ما فيه أي خصم - فقط تنتهي الجولة
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
@app_commands.describe(trigger="الكلمة أو الجملة اللي تشغّل الرد (يجب تطابق تام)", response="الرد اللي يرسله البوت")
@app_commands.checks.has_permissions(administrator=True)
async def add_auto_reply(interaction: discord.Interaction, trigger: str, response: str):
    db = load_db()
    db["auto_replies"][trigger] = response
    save_db(db)
    await interaction.response.send_message(
        f"✅ تم إضافة الرد الآلي:\nلو حد كتب: `{trigger}`\nيرد البوت: {response}", ephemeral=True
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

    lines = [f"**{trigger}** ← {response}" for trigger, response in auto_replies.items()]
    embed = discord.Embed(
        title="📋 الردود الآلية المخصصة",
        description="\n".join(lines)[:4000],
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


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
    embed = discord.Embed(
        title="🏦 رصيدك",
        description=f"معك حاليًا: **{bal}** عملة",
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="mines", description="العب لعبة الألغام واربح مكافأة (بدون رهان)")
async def mines(interaction: discord.Interaction):
    if BANK_CHANNEL_ID and interaction.channel.id != BANK_CHANNEL_ID:
        return await interaction.response.send_message(
            f"❌ هذي اللعبة تشتغل بس بروم <#{BANK_CHANNEL_ID}>.", ephemeral=True
        )

    view = MinesGameView(interaction.user)
    embed = discord.Embed(
        title="⛏️ لعبة البنك - Mines",
        description=(
            f"اللاعب: {interaction.user.mention}\n"
            f"فيه قنبلة وحدة مخفية بين 9 مربعات 💣\n"
            "اضغط على مربع تفتحه، وكل ما فتحت أكثر كبرت مكافأتك المحتملة!\n"
            "(مافيه رهان - لو انفجرت القنبلة رصيدك ما يتأثر)"
        ),
        color=MAIN_COLOR,
    )
    await interaction.response.send_message(embed=embed, view=view)


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


# =====================================================================
#                 🎧  نظام الرومات الصوتية المؤقتة (Temp Voice)
#   عضو يدخل روم "الهَب" فيُنشأ له روم صوتي خاص يتحكم فيه بالكامل،
#   ويُحذف تلقائياً لما يفضى. يُضبط الهَب بأمر /voice_setup (مرة وحدة).
# =====================================================================
@bot.tree.command(name="voice_setup", description="تحديد روم الهَب (➕ إنشاء روم) وكاتيجوري الرومات المؤقتة - للأونر والإدارة العليا بس")
@app_commands.describe(
    hub_channel="الروم الصوتي اللي العضو يدخله عشان يتنشئ له روم خاص",
    category="الكاتيجوري اللي تُنشأ فيها الرومات المؤقتة (افتراضياً: نفس كاتيجوري الهَب)",
    name_template="قالب اسم الروم الجديد - استخدم {user} عشان يتحط اسم العضو مكانها",
)
@is_owner_or_senior_admin()
async def voice_setup(
    interaction: discord.Interaction,
    hub_channel: discord.VoiceChannel,
    category: discord.CategoryChannel = None,
    name_template: str = "روم {user}",
):
    db = load_db()
    db["settings"]["temp_voice_hub_id"] = hub_channel.id
    db["settings"]["temp_voice_category_id"] = category.id if category else None
    db["settings"]["temp_voice_name_template"] = name_template
    save_db(db)
    await interaction.response.send_message(
        f"✅ صار روم {hub_channel.mention} هو هَب الرومات المؤقتة"
        + (f"، وتُنشأ الرومات بكاتيجوري **{category.name}**." if category else "، وتُنشأ الرومات بنفس كاتيجوري الهَب."),
        ephemeral=True,
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
                required=True,
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
