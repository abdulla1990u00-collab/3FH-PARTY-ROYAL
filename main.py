"""
=====================================================================
   3FH PARTY ROYAL - Discord Bot
   بوت متكامل: ترحيب + نظام تذاكر + اقتراحات + إعلانات + بنك الصور المطور
   Python 3.12  |  discord.py 2.x
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
import glob
from datetime import datetime, timezone, timedelta

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops, features

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_display
    HAS_AR_LIBS = True
except Exception:
    HAS_AR_LIBS = False

# =====================================================================
#                        ⚙️  الإعدادات العامة (IDs)
# =====================================================================
load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
OWNER_ROLE_ID = int(os.getenv("OWNER_ROLE_ID", "0"))

WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
WELCOME_ROLE_ID = int(os.getenv("AUTO_ROLE_ID", "0"))
WELCOME_FONT_PATH = os.getenv("WELCOME_FONT_PATH", "")

DEFAULT_WELCOME_POSITION = {
    "avatar_x": 150, "avatar_y": 150, "avatar_size": 180,
    "text_x": 500, "text_y": 130, "text_size": 48, "text_color": "#FFFFFF",
}

TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))
TICKET_PANEL_CHANNEL_ID = int(os.getenv("TICKET_PANEL_CHANNEL_ID", "0"))
TICKET_LOG_CHANNEL_ID = int(os.getenv("TICKET_LOG_CHANNEL_ID", "0"))
TICKET_BANNER_URL = os.getenv("TICKET_BANNER_URL", "")

STAFF_ROLE_IDS = [int(x) for x in os.getenv("STAFF_ROLE_IDS", "").split(",") if x.strip().isdigit()]
SUGGESTIONS_CHANNEL_ID = int(os.getenv("SUGGESTION_CHANNEL_ID", "0"))

GENERAL_CHAT_ID = int(os.getenv("GENERAL_CHAT_ID", "0"))
MEMBER_ROLE_ID = int(os.getenv("MEMBER_ROLE_ID", "0"))
CORRECTIONS_CHANNEL_ID = int(os.getenv("CORRECTIONS_CHANNEL_ID", "0"))

LEVEL_UP_CHANNEL_ID = int(os.getenv("LEVEL_UP_CHANNEL_ID", "0"))
XP_MIN_PER_MESSAGE, XP_MAX_PER_MESSAGE, XP_COOLDOWN_SECONDS = 15, 25, 60

ATHKAR_CHANNEL_ID = int(os.getenv("ATHKAR_CHANNEL_ID", "0"))

BANK_CHANNEL_ID = int(os.getenv("BANK_CHANNEL_ID", "0"))
STARTING_BALANCE = 1000
MINES_GRID_SIZE = 9
MINES_MULTIPLIER_STEP = 0.3
MINES_BASE_REWARD = 100

BANK_COOLDOWNS = {
    "راتب": 86400, "بخشيش": 300, "حظ": 180, "روليت": 300, "نهب": 600,
    "رهان": 30, "استثمار": 291, "تداول": 255, "قمار": 60, "نرد": 274,
    "لعبه": 0, "لون": 0, "فواكه": 0, "تسريع": 0, "بيع": 0, "شراء": 0, "ألغام": 300
}
BANK_STATUS_ORDER = [
    "راتب", "بخشيش", "حظ", "روليت", "نهب", "رهان",
    "استثمار", "تداول", "قمار", "نرد", "ألغام", "لعبه", "لون", "فواكه",
    "تسريع", "بيع", "شراء"
]

SALARY_AMOUNT = 2000
TIP_MIN, TIP_MAX = 200, 900
LUCK_MIN, LUCK_MAX = -400, 700

ROULETTE_PRIZES = [
    (1500, 22), (6000, 18), (9000, 15), (12000, 12), (15000, 9),
    (19000, 7), (50000, 4), (100000, 2), ("gold:5", 7), ("gold:10", 4),
]

ROB_SUCCESS_CHANCE, ROB_PERCENT, ROB_FAIL_FINE = 0.65, 0.01, 500
PROTECTION_HOURS, PROTECTION_COST = 5, 2000
INVEST_MIN_PCT, INVEST_MAX_PCT = -0.35, 0.90
TRADE_MIN_PCT, TRADE_MAX_PCT = -0.55, 1.35
DICE_MIN_BET = GAMBLE_MIN_BET = BET_MIN_BET = TRADE_MIN_BET = INVEST_MIN_BET = 100
SPEEDUP_GOLD_COST = 30

PAY_CARD_NAME = "96Pay"
BANK_BRAND_NAME = "🏦 3FH BANK"
BANK_FOOTER_TEXT = "3FH PARTY ROYAL"
BANK_OWNER_ROLE_ID = int(os.getenv("BANK_OWNER_ROLE_ID", "0"))
BANK_WHEEL_SLICE_COLORS = [(56, 60, 68, 255), (38, 41, 47, 255)]

PROPERTY_CATALOG = {
    "car": {"name": "سياره", "emoji": "🚗", "price": 3000},
    "house": {"name": "بيت", "emoji": "🏠", "price": 5000},
    "land": {"name": "اراضي", "emoji": "🗺️", "price": 10000},
    "store": {"name": "متجر", "emoji": "🏪", "price": 8000},
    "building": {"name": "مبنى", "emoji": "🏢", "price": 20000},
    "company": {"name": "شركه", "emoji": "🏭", "price": 50000},
}
PROPERTY_SELL_RATIO, STOCK_PRICE = 0.6, 500

MAIN_COLOR, SUCCESS_COLOR, DANGER_COLOR, WELCOME_COLOR = 0x2F3136, 0x57F287, 0xED4245, 0xF1C40F

# =====================================================================
#                     💾  قاعدة بيانات محلية (JSON)
# =====================================================================
DATA_DIR = os.getenv("DATA_DIR", "data")
DB_FILE = os.path.join(DATA_DIR, "database.json")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
BANNERS_DIR = os.path.join(DATA_DIR, "banners")
FILES_DIR = os.path.join(DATA_DIR, "files")

def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    os.makedirs(BANNERS_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    if not os.path.exists(DB_FILE):
        default_db = {
            "ticket_counter": 0, "open_tickets": {}, "tickets": {},
            "suggestions": {}, "ratings": {}, "corrections": {},
            "auto_replies": {}, "levels": {}, "economy": {}, "gold": {},
            "properties": {}, "protection": {}, "bank_cooldowns": {},
            "bank_history": {}, "settings": {
                "ticket_banner_path": None, "suggestion_banner_path": None,
                "welcome_template_path": None, "welcome_position": dict(DEFAULT_WELCOME_POSITION),
                "ticket_allowed_roles": [], "custom_messages": {}
            }
        }
        save_db(default_db)

def load_db() -> dict:
    ensure_data_files()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("economy", {})
    data.setdefault("gold", {})
    data.setdefault("properties", {})
    data.setdefault("protection", {})
    data.setdefault("bank_cooldowns", {})
    data.setdefault("bank_history", {})
    return data

def save_db(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# =====================================================================
#                         🤖  إعداد البوت
# =====================================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

def get_balance(user_id: int) -> int:
    db = load_db()
    uid = str(user_id)
    if uid not in db["economy"]:
        db["economy"][uid] = STARTING_BALANCE
        save_db(db)
    return db["economy"][uid]

def update_balance(user_id: int, delta: int) -> int:
    db = load_db()
    uid = str(user_id)
    current = db["economy"].get(uid, STARTING_BALANCE)
    new_balance = max(0, current + delta)
    db["economy"][uid] = new_balance
    save_db(db)
    return new_balance

def get_gold(user_id: int) -> int:
    return load_db()["gold"].get(str(user_id), 0)

def update_gold(user_id: int, delta: int) -> int:
    db = load_db()
    uid = str(user_id)
    current = db["gold"].get(uid, 0)
    new_amount = max(0, current + delta)
    db["gold"][uid] = new_amount
    save_db(db)
    return new_amount

def get_cooldown_remaining(user_id: int, action: str) -> float:
    duration = BANK_COOLDOWNS.get(action, 0)
    if duration <= 0: return 0.0
    ready_at = load_db()["bank_cooldowns"].get(str(user_id), {}).get(action, 0)
    return max(0.0, ready_at - datetime.now(timezone.utc).timestamp())

def set_cooldown(user_id: int, action: str) -> None:
    duration = BANK_COOLDOWNS.get(action, 0)
    if duration <= 0: return
    db = load_db()
    db["bank_cooldowns"].setdefault(str(user_id), {})[action] = datetime.now(timezone.utc).timestamp() + duration
    save_db(db)

def clear_cooldowns(user_id: int) -> None:
    db = load_db()
    db["bank_cooldowns"][str(user_id)] = {}
    save_db(db)

def format_bank_duration(seconds: float) -> str:
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours: return f"{hours} ساعة {minutes} دقيقة"
    if minutes: return f"{minutes} دقائق {secs} ثانية"
    return f"{secs} ثانية"

def parse_amount_arg(arg: str | None, balance: int) -> int | None:
    if not arg: return None
    arg = arg.strip()
    if arg in ("كامل", "الكل", "كل"): return balance
    if arg in ("نص", "نصف"): return balance // 2
    if arg in ("ربع",): return balance // 4
    digits = re.sub(r"[^\d]", "", arg)
    return int(digits) if digits.isdigit() and digits else None

# =====================================================================
#            🖼️  محرك الخطوط ومولد العجلات والشارتات
# =====================================================================
_font_cache = {}

def _load_bank_font(size: int):
    key = size
    if key in _font_cache: return _font_cache[key]
    font = None
    if WELCOME_FONT_PATH and os.path.exists(WELCOME_FONT_PATH):
        try: font = ImageFont.truetype(WELCOME_FONT_PATH, size)
        except Exception: pass
    if font is None:
        try: font = ImageFont.load_default(size=size)
        except Exception: font = ImageFont.load_default()
    _font_cache[key] = font
    return font

def render_roulette_wheel(prize_labels: list[str], winning_index: int, avatar_bytes: bytes | None = None) -> discord.File:
    size = 640
    center = size // 2
    radius = size // 2 - 24
    n = max(1, len(prize_labels))
    sector_angle = 360 / n
    final_rotation = -(winning_index * sector_angle) - sector_angle / 2
    total_spin_extra = 3 * 360
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
        except Exception: pass

    def render_frame(rotation: float, highlight: bool) -> Image.Image:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for i, label in enumerate(prize_labels):
            start = rotation + i * sector_angle
            end = start + sector_angle
            is_winner = highlight and i == winning_index
            color = (241, 196, 15, 255) if is_winner else BANK_WHEEL_SLICE_COLORS[i % 2]
            draw.pieslice((center - radius, center - radius, center + radius, center + radius), start, end, fill=color, outline=(15, 15, 17, 255), width=2)
            mid_angle = math.radians((start + end) / 2)
            tx = center + (radius * 0.68) * math.cos(mid_angle)
            ty = center + (radius * 0.68) * math.sin(mid_angle)
            text_color = (20, 20, 20, 255) if is_winner else (241, 196, 15, 255)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((tx - tw / 2, ty - th / 2), label, font=font, fill=text_color)
        draw.ellipse((center - radius, center - radius, center + radius, center + radius), outline=(241, 196, 15, 255), width=6)
        draw.polygon([(size - 4, center - 20), (size - 4, center + 20), (size - 36, center)], fill=(241, 196, 15, 255))
        if avatar_layer:
            av_img, av_sz = avatar_layer
            image.paste(av_img, (center - av_sz // 2, center - av_sz // 2), av_img)
            draw.ellipse((center - av_sz // 2, center - av_sz // 2, center + av_sz // 2, center + av_sz // 2), outline=(241, 196, 15, 255), width=4)
        return image.convert("RGB")

    frame_count = 20
    frames, durations = [], []
    for f in range(frame_count):
        t = f / (frame_count - 1)
        eased = 1 - (1 - t) ** 3
        rotation = final_rotation - (1 - eased) * total_spin_extra
        frames.append(render_frame(rotation, f == frame_count - 1))
        durations.append(int(35 + t * 170))
    frames.append(render_frame(final_rotation, True))
    durations.append(2500)

    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=durations, loop=1)
    buffer.seek(0)
    return discord.File(buffer, filename="roulette.gif")

# =====================================================================
#                     🎮  أوامر البنك المكتوبة بروم الشات
# =====================================================================
BANK_KEYWORDS = {
    "راتب", "بخشيش", "حظ", "روليت", "نهب", "حماية", "رهان",
    "استثمار", "تداول", "قمار", "نرد", "تسريع", "وقت", "اغنى", "اوامر"
}

async def handle_bank_text_command(message: discord.Message) -> bool:
    content = message.content.strip()
    if not content: return False
    parts = content.split(maxsplit=1)
    keyword = parts[0].strip()
    arg = parts[1].strip() if len(parts) > 1 else None

    if keyword not in BANK_KEYWORDS: return False

    rem = get_cooldown_remaining(message.author.id, keyword)
    if rem > 0:
        await message.reply(f"⏳ لا تعيدها عاد، تعال بعد **{format_bank_duration(rem)}**", mention_author=False)
        return True

    if keyword == "راتب":
        set_cooldown(message.author.id, "راتب")
        new_bal = update_balance(message.author.id, SALARY_AMOUNT)
        await message.reply(f"💵 تم إيداع راتبك: **{SALARY_AMOUNT:,}$** | رصيدك الحالي: **{new_bal:,}$**", mention_author=False)

    elif keyword == "بخشيش":
        set_cooldown(message.author.id, "بخشيش")
        tip = random.randint(TIP_MIN, TIP_MAX)
        new_bal = update_balance(message.author.id, tip)
        await message.reply(f"💵 حصلت على بخشيش: **{tip:,}$** | رصيدك: **{new_bal:,}$**", mention_author=False)

    elif keyword == "حظ":
        set_cooldown(message.author.id, "حظ")
        luck = random.randint(LUCK_MIN, LUCK_MAX)
        new_bal = update_balance(message.author.id, luck)
        msg = f"🎉 ربحت **{luck:,}$**" if luck >= 0 else f"📉 خسرت **{abs(luck):,}$**"
        await message.reply(f"{msg} | رصيدك الحالي: **{new_bal:,}$**", mention_author=False)

    elif keyword == "روليت":
        set_cooldown(message.author.id, "روليت")
        prizes = [p for p, _ in ROULETTE_PRIZES]
        weights = [w for _, w in ROULETTE_PRIZES]
        idx = random.choices(range(len(prizes)), weights=weights, k=1)[0]
        prize = prizes[idx]
        labels = [f"G x{p.split(':')[1]}" if isinstance(p, str) and p.startswith("gold:") else f"${p:,}" for p in prizes]

        try:
            av_bytes = await message.author.display_avatar.read()
            gif_file = render_roulette_wheel(labels, idx, av_bytes)
            if isinstance(prize, str) and prize.startswith("gold:"):
                amt = int(prize.split(":")[1])
                new_g = update_gold(message.author.id, amt)
                txt = f"🎡 مبروك! العجلة وقفت على **Gold x{amt}** 🥇 | ذهبك: **{new_g}**"
            else:
                new_bal = update_balance(message.author.id, prize)
                txt = f"🎡 مبروك! العجلة وقفت على **${prize:,}** 💵 | رصيدك: **${new_bal:,}**"
            await message.reply(content=txt, file=gif_file, mention_author=False)
        except Exception as e:
            await message.reply(f"🎡 تم إجراء الروليت وحصلت على الجائزة!", mention_author=False)

    elif keyword == "تسريع":
        gold = get_gold(message.author.id)
        if gold < SPEEDUP_GOLD_COST:
            await message.reply(f"❌ تحتاج **Gold x{SPEEDUP_GOLD_COST}** لتسريع الأوامر (عندك **{gold}**).", mention_author=False)
        else:
            update_gold(message.author.id, -SPEEDUP_GOLD_COST)
            clear_cooldowns(message.author.id)
            await message.reply(f"⚡ تم خصم **Gold x{SPEEDUP_GOLD_COST}** وتصفير جميع أوقات الانتظار بنجاح!", mention_author=False)

    return True

# =====================================================================
#                        💬  الأحداث العامة (Events)
# =====================================================================
@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول باسم: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم مزامنة {len(synced)} أمر سلاش.")
    except Exception as e:
        print(f"❌ خطأ أثناء المزامنة: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    
    # معالجة أوامر البنك النصية
    if (not BANK_CHANNEL_ID) or message.channel.id == BANK_CHANNEL_ID:
        if await handle_bank_text_command(message): return

    await bot.process_commands(message)

# =====================================================================
#                          ▶️  تشغيل البوت
# =====================================================================
if __name__ == "__main__":
    ensure_data_files()
    if not TOKEN:
        raise SystemExit("❌ التوكن غير موجود بملف .env!")
    bot.run(TOKEN)