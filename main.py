import os
import io
import json
import asyncio
import logging
import sqlite3
from aiohttp import web
from PIL import Image, ImageDraw
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import google.generativeai as genai

# ==========================================
# 1. SOZLAMALAR (Tokeningiz joylashtirildi)
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8745387169:AAFgM6SQCt6cheZwmben1R6MDct6W-aUIdo")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# 2. MA'LUMOTLAR BAZASI (SQLITE)
# ==========================================
DB_FILE = "pubg_game.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            hp INTEGER DEFAULT 100,
            armor INTEGER DEFAULT 75,
            kills INTEGER DEFAULT 0,
            alive INTEGER DEFAULT 98,
            weapon TEXT DEFAULT 'M416 (30/90)',
            inventory TEXT DEFAULT '["🩹 Medkit x2", "💣 Granata x1", "🎒 Level 2 Sumka"]',
            story TEXT DEFAULT 'Siz Pochinki zonasiga parashyutda tushdingiz. Bino ichida qadam tovushlari eshitilmoqda...',
            choices TEXT DEFAULT '["🏠 Bino ichiga kirib loot qilish", "🚗 Atrofda mashina izlash", "🎯 Tomga chiqib atroflarni kuzatish"]'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_player(user_id, name="Survivor"):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, hp, armor, kills, alive, weapon, inventory, story, choices FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO players (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        cursor.execute("SELECT user_id, name, hp, armor, kills, alive, weapon, inventory, story, choices FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    conn.close()
    
    return {
        "user_id": row[0], "name": row[1], "hp": row[2], "armor": row[3],
        "kills": row[4], "alive": row[5], "weapon": row[6],
        "inventory": json.loads(row[7]), "story": row[8],
        "choices": json.loads(row[9])
    }

def update_player(user_id, hp, armor, kills, alive, weapon, inventory, story, choices):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players 
        SET hp = ?, armor = ?, kills = ?, alive = ?, weapon = ?, inventory = ?, story = ?, choices = ?
        WHERE user_id = ?
    ''', (hp, armor, kills, alive, weapon, json.dumps(inventory, ensure_ascii=False), story, json.dumps(choices, ensure_ascii=False), user_id))
    conn.commit()
    conn.close()

# ==========================================
# 3. PUBG GRAFIKA VA HUD GENERATORI (PILLOW)
# ==========================================
def create_pubg_hud_image(p):
    W, H = 1000, 650
    img = Image.new("RGB", (W, H), color="#0f141d")
    draw = ImageDraw.Draw(img)
    
    # Grid va Taktiki ramka
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill="#1a2332", width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill="#1a2332", width=1)
        
    # Yuqori HUD paneli
    draw.rectangle([(20, 20), (W - 20, 70)], fill="#182232", outline="#f39c12", width=2)
    draw.text((35, 33), f"📍 COMPASS: NW 315°  |  ZONE: 00:45  |  👥 ALIVE: {p['alive']}/100  |  KILLS: {p['kills']}", fill="#f1c40f")
    
    # Asosiy Voqea Ramkasi
    draw.rectangle([(20, 85), (W - 20, 430)], fill="#141c2b", outline="#34495e", width=2)
    draw.rectangle([(25, 90), (W - 25, 125)], fill="#f39c12")
    draw.text((35, 97), "ZONA VIZUAL TAHLILI VA VAZIYAT", fill="#000000")
    
    # Matnni qatorlarga bo'lish
    words = p['story'].split(" ")
    lines, current_line = [], ""
    for w in words:
        if len(current_line + " " + w) < 65:
            current_line += " " + w
        else:
            lines.append(current_line.strip())
            current_line = w
    if current_line:
        lines.append(current_line.strip())
        
    y_text = 145
    for line in lines:
        draw.text((40, y_text), line, fill="#ecf0f1")
        y_text += 28
        
    # Pastki Taktik Panel (HP, Armor, Weapon)
    draw.rectangle([(20, 445), (W - 20, 630)], fill="#182232", outline="#2c3e50", width=2)
    
    # Health Bar (Qizil)
    draw.text((40, 460), "HEALTH (HP):", fill="#e74c3c")
    draw.rectangle([(160, 460), (460, 480)], fill="#2c3e50")
    hp_width = int(300 * (max(0, p['hp']) / 100))
    if hp_width > 0:
        draw.rectangle([(160, 460), (160 + hp_width, 480)], fill="#e74c3c")
    draw.text((470, 460), f"{p['hp']}/100", fill="#ffffff")
    
    # Armor Bar (Ko'k)
    draw.text((40, 495), "ARMOR (VEST):", fill="#3498db")
    draw.rectangle([(160, 495), (460, 515)], fill="#2c3e50")
    armor_width = int(300 * (max(0, p['armor']) / 100))
    if armor_width > 0:
        draw.rectangle([(160, 495), (160 + armor_width, 515)], fill="#3498db")
    draw.text((470, 495), f"{p['armor']}/100", fill="#ffffff")
    
    # Weapon & Inventory
    draw.text((560, 460), f"QUROL: {p['weapon']}", fill="#f1c40f")
    inv_str = ", ".join(p['inventory']) if p['inventory'] else "Puch (Bo'sh)"
    draw.text((560, 495), f"ANJOMLAR: {inv_str[:35]}...", fill="#bdc3c7")
    
    # Bezash liniyalari
    draw.line([(20, 20), (50, 20)], fill="#f39c12", width=4)
    draw.line([(20, 20), (20, 50)], fill="#f39c12", width=4)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()

# ==========================================
# 4. AI VA SSENARIY GENERATORI
# ==========================================
async def generate_pubg_chapter(player, action):
    if not GEMINI_API_KEY:
        return {
            "story": f"Siz '{action}' harakatini bajardingiz! Dushmanlar tomondan o'q uzildi va pozitsiya o'zgardi.",
            "hp_change": -10, "armor_change": -5, "kills_change": 0, "alive_change": -2,
            "new_weapon": None,
            "choices": ["🚀 Otishmaga kirishish", "🏃 Bino orqasiga yashirinish", "🚗 Mashinada qochish"]
        }

    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Siz PUBG Mobile o'yinining dinamik sistemasiz.
Player: HP={player['hp']}, Armor={player['armor']}, Kills={player['kills']}, Alive={player['alive']}, Weapon={player['weapon']}
Action: "{action}"

Shu harakatga mos dynamic ssenariy yarating. FAQAT JSON formatida javob bering:
{{
  "story": "Voqea tasviri (3 jumla, o'zbekcha)",
  "hp_change": -15,
  "armor_change": -10,
  "kills_change": 1,
  "alive_change": -4,
  "new_weapon": null,
  "choices": ["Tanlov 1", "Tanlov 2", "Tanlov 3"]
}}"""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        txt = response.text.strip()
        if txt.startswith("```json"): txt = txt[7:-3].strip()
        elif txt.startswith("```"): txt = txt[3:-3].strip()
        return json.loads(txt)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return {
            "story": f"Dushmanlar pistirmasiga duch kedingiz! O'qlar har tomondan uchmoqda.",
            "hp_change": -15, "armor_change": -10, "kills_change": 0, "alive_change": -3,
            "new_weapon": None,
            "choices": ["🎯 Qarshi o'q uzish", "💣 Granata otish", "🩹 Qochib medkit ishlatish"]
        }

# ==========================================
# 5. HANDLERLAR
# ==========================================
def get_game_keyboard(choices):
    buttons = []
    for idx, choice in enumerate(choices):
        buttons.append([InlineKeyboardButton(text=f"🎯 {choice}", callback_data=f"act_{idx}")])
    buttons.append([InlineKeyboardButton(text="🔄 Yangi O'yin", callback_data="restart")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_game(message: types.Message):
    user_id = message.from_user.id
    player = get_player(user_id, message.from_user.first_name)
    
    img_bytes = create_pubg_hud_image(player)
    photo = BufferedInputFile(img_bytes, filename="pubg_hud.png")
    kb = get_game_keyboard(player['choices'])
    
    await message.answer_photo(
        photo=photo,
        caption="🪂 <b>PUBG BATTLE ROYALE: ZONA SURVIVAL</b>\nTaktik harakatingizni tanlang:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("act_"))
async def handle_game_action(call: types.CallbackQuery):
    user_id = call.from_user.id
    player = get_player(user_id, call.from_user.first_name)
    
    if player['hp'] <= 0:
        await call.answer("☠️ Siz halok bo'lgansiz! Yangi o'yin bosing.", show_alert=True)
        return

    idx = int(call.data.split("_")[1])
    action_text = player['choices'][idx]
    await call.answer("⚡ Bajarilmoqda...")
    
    res = await generate_pubg_chapter(player, action_text)
    
    new_hp = max(0, min(100, player['hp'] + res.get('hp_change', 0)))
    new_armor = max(0, min(100, player['armor'] + res.get('armor_change', 0)))
    new_kills = player['kills'] + res.get('kills_change', 0)
    new_alive = max(1, player['alive'] + res.get('alive_change', -2))
    weapon = res.get('new_weapon') if res.get('new_weapon') else player['weapon']
    story = res.get('story', '')
    choices = res.get('choices', ["Oldinga yurish", "Poylash", "Mavqeni o'zgartirish"])
    
    if new_hp <= 0:
        story += "\n\n☠️ <b>Siz jang maydonida halok bo'ldingiz!</b>"
        choices = ["Qaytadan sakrash"]

    update_player(user_id, new_hp, new_armor, new_kills, new_alive, weapon, player['inventory'], story, choices)
    updated_player = get_player(user_id)
    
    img_bytes = create_pubg_hud_image(updated_player)
    photo = BufferedInputFile(img_bytes, filename="pubg_hud.png")
    kb = get_game_keyboard(updated_player['choices'])
    
    try:
        await call.message.delete()
    except:
        pass
        
    await call.message.answer_photo(
        photo=photo,
        caption="🪂 <b>PUBG BATTLE ROYALE</b>\nKeyingi taktika:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(F.data == "restart")
async def restart(call: types.CallbackQuery):
    user_id = call.from_user.id
    update_player(
        user_id, 100, 75, 0, 98, 'M416 (30/90)',
        ["🩹 Medkit x2", "💣 Granata x1", "🎒 Level 2 Sumka"],
        'Siz Pochinki zonasiga parashyutda tushdingiz. Bino ichida qadam tovushlari eshitilmoqda...',
        ["🏠 Bino ichiga kirib loot qilish", "🚗 Atrofda mashina izlash", "🎯 Tomga chiqib atroflarni kuzatish"]
    )
    
    player = get_player(user_id)
    img_bytes = create_pubg_hud_image(player)
    photo = BufferedInputFile(img_bytes, filename="pubg_hud.png")
    kb = get_game_keyboard(player['choices'])
    
    try:
        await call.message.delete()
    except:
        pass
    
    await call.message.answer_photo(
        photo=photo,
        caption="🪂 <b>Yangi jang boshlandi!</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

# ==========================================
# 6. SERVER RUNNER
# ==========================================
async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="PUBG Bot is Running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
