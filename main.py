import os
import asyncio
import logging
import json
import re
import pytz
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import sympy as sp
import matplotlib
matplotlib.use('Agg') # Serverda grafik chiqarish uchun
import matplotlib.pyplot as plt
import numpy as np

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Sozlamalari
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8772192229:AAGP_TiLNzROuCW2n_CvDcDTeTVieSSiwxs")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 8715668931))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Foydalanuvchilar bazasi
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users_db = load_users()

# ==========================================
# 1. MATEMATIKA VA GRAFIK CHIZISH (X, Y O'QLARI)
# ==========================================

def solve_and_plot_math(expr_str):
    x = sp.Symbol('x')
    clean_expr = expr_str.replace("y =", "").replace("f(x) =", "").strip()
    
    # SymPy yordamida tenglamani tahlil qilish
    expr = sp.sympify(clean_expr)
    derivative = sp.diff(expr, x)
    roots = sp.solve(expr, x)

    # Grafikni chizish
    f = sp.lambdify(x, expr, modules=['numpy'])
    x_vals = np.linspace(-10, 10, 400)
    
    try:
        y_vals = f(x_vals)
        if np.isscalar(y_vals):
            y_vals = np.full_like(x_vals, y_vals)
    except Exception:
        y_vals = np.zeros_like(x_vals)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(x_vals, y_vals, label=f"y = {clean_expr}", color='blue', linewidth=2)

    # X va Y o'qlarini markazdan o'tkazish
    ax.axhline(0, color='black', linewidth=1.2) # X o'qi
    ax.axvline(0, color='black', linewidth=1.2) # Y o'qi

    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_xlabel('X o\'qi', fontsize=12)
    ax.set_ylabel('Y o\'qi', fontsize=12)
    ax.set_title(f"Funksiya Grafigi: y = {clean_expr}", fontsize=14)
    ax.legend()

    img_path = "math_graph.png"
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()

    res_text = (
        f"📐 **Matematik Yechim:**\n\n"
        f"🔹 **Funksiya:** `y = {clean_expr}`\n"
        f"🔹 **Hosilasi (y'):** `{derivative}`\n"
        f"🔹 **Ildizlari (y=0):** `{roots}`\n"
    )
    return res_text, img_path

# ==========================================
# 2. KIMYO MASALALARI (Molyar massa)
# ==========================================

PERIODIC_TABLE = {
    'H': 1.008, 'He': 4.0026, 'Li': 6.94, 'Be': 9.0122, 'B': 10.81, 'C': 12.011,
    'N': 14.007, 'O': 15.999, 'F': 18.998, 'Na': 22.990, 'Mg': 24.305, 'Al': 26.982,
    'Si': 28.085, 'P': 30.974, 'S': 32.06, 'Cl': 35.45, 'K': 39.098, 'Ca': 40.078,
    'Fe': 55.845, 'Cu': 63.546, 'Zn': 65.38, 'Ag': 107.87, 'I': 126.90, 'Ba': 137.33
}

def calculate_molar_mass(formula):
    # Oddiy formulalarni analiz qilish (Masalan: H2SO4, CaCO3)
    matches = re.findall(r'([A-Z][a-z]?)([0-9]*)', formula)
    if not matches:
        return None, "Formula noto'g'ri kiritildi."

    total_mass = 0
    details = []

    for elem, count in matches:
        if elem not in PERIODIC_TABLE:
            return None, f"⚠️ '{elem}' elementi davriy sistemada topilmadi."
        cnt = int(count) if count else 1
        mass = PERIODIC_TABLE[elem] * cnt
        total_mass += mass
        details.append(f"• {elem}: {cnt} ta × {PERIODIC_TABLE[elem]} = {mass:.2f} g/mol")

    res = f"🧪 **Kimyoviy Formula:** `{formula}`\n\n"
    res += "\n".join(details)
    res += f"\n\n⚖️ **Umumiy Molyar Massa:** `{total_mass:.2f} g/mol`"
    return res

# ==========================================
# 3. BIOLOGIYA MASALALARI (DNK va ATF)
# ==========================================

def solve_biology_dna(dna_seq):
    dna = dna_seq.upper().replace(" ", "")
    comp_dna = ""
    rna = ""

    pairs = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
    rna_pairs = {'A': 'U', 'T': 'A', 'G': 'C', 'C': 'G'}

    for nuc in dna:
        if nuc not in pairs:
            return "❌ Noto'g'ri DNK ketma-ketligi! Faqat A, T, G, C harflaridan foydalaning."
        comp_dna += pairs[nuc]
        rna += rna_pairs[nuc]

    length = len(dna)
    a_cnt, t_cnt = dna.count('A'), dna.count('T')
    g_cnt, c_cnt = dna.count('G'), dna.count('C')

    res = (
        f"🧬 **Biologik DNK Yechimi:**\n\n"
        f"🔹 **Siz kiritgan zanjir:** `{dna}`\n"
        f"🔹 **Komplementar zanjir:** `{comp_dna}`\n"
        f"🔹 **i-RNK (Transkripsiya):** `{rna}`\n\n"
        f"📊 **Statistika:**\n"
        f"• Umumiy nukleotidlar: {length} ta\n"
        f"• A: {a_cnt} ta | T: {t_cnt} ta | G: {g_cnt} ta | C: {c_cnt} ta\n"
        f"• Uzunligi: {length * 0.34:.2f} nm\n"
    )
    return res

def solve_biology_atp(glucose_moles):
    # 1 mol glyukoza to'liq parchalansa 38 mol ATF, 2800 kDJ energiya beradi
    atp = glucose_moles * 38
    energy = glucose_moles * 2800
    res = (
        f"⚡️ **Energiya Almashinuvi (ATF) Yechimi:**\n\n"
        f"🔹 **Glyukoza miqdori:** {glucose_moles} mol\n"
        f"🔹 **Hosil bo'lgan ATF:** {atp} mol ATF\n"
        f"🔹 **Ajralib chiqqan energiya:** {energy} kDJ\n"
        f"• Arotik (Glyukoliz): {glucose_moles * 2} mol ATF\n"
        f"• Aerob (Nafas olish): {glucose_moles * 36} mol ATF\n"
    )
    return res

# ==========================================
# 4. BOT HANDLERLARI VA ADMIN PANEL
# ==========================================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = str(message.chat.id)
    if user_id not in users_db:
        users_db[user_id] = {"name": message.from_user.full_name}
        save_users(users_db)

    text = (
        f"Xush kelibsiz, **{message.from_user.first_name}**! 🎓\n\n"
        f"Men Matematika, Kimyo va Biologiya masalalarini yechuvchi aqlli botman!\n\n"
        f"📌 **Qanday foydalanish kerak?**\n"
        f"1️⃣ **Matematika:** Funksiyani yozing (masalan: `y = x^2 - 4x + 3`). Bot yechimni va **X/Y grafigini** chizib beradi.\n"
        f"2️⃣ **Kimyo:** Formulani yozing (masalan: `H2SO4` yoki `CaCO3`). Bot molyar massasini hisoblaydi.\n"
        f"3️⃣ **Biologiya:** \n"
        f"   • DNK ketma-ketligini yozing (masalan: `DNK: ATGCGA`)\n"
        f"   • ATF hisoblash uchun: `ATF: 3` (3 mol glyukoza uchun)\n"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("users"))
async def admin_users_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruqdan foydalanish huquqi yo'q! ❌")
        return

    count = len(users_db)
    text = f"📊 **Bot foydalanuvchilari soni:** {count} ta\n\n**ID Ro'yxati:**\n"
    for i, (uid, uinfo) in enumerate(users_db.items(), 1):
        text += f"{i}. `{uid}` - {uinfo.get('name', 'Noma\'lum')}\n"
        if i >= 40:
            text += "...va boshqalar."
            break

    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text)
async def academic_solver_handler(message: types.Message):
    text = message.text.strip()

    # Biologiya: DNK
    if text.upper().startswith("DNK:"):
        dna_str = text.split(":", 1)[1]
        res = solve_biology_dna(dna_str)
        await message.answer(res, parse_mode="Markdown")
        return

    # Biologiya: ATF
    if text.upper().startswith("ATF:"):
        try:
            moles = float(text.split(":", 1)[1])
            res = solve_biology_atp(moles)
            await message.answer(res, parse_mode="Markdown")
        except ValueError:
            await message.answer("❌ Mollar sonini to'g'ri raqamda kiriting. Masalan: `ATF: 2`")
        return

    # Matematika (Funksiyalar va tenglamalar)
    if "x" in text or "=" in text or "y" in text:
        msg = await message.answer("📐 Matematik misol va grafik hisoblanmoqda...")
        try:
            res_text, img_path = await asyncio.to_thread(solve_and_plot_math, text)
            graph_file = FSInputFile(img_path)
            await message.answer_photo(photo=graph_file, caption=res_text, parse_mode="Markdown")
            await msg.delete()
            if os.path.exists(img_path):
                os.remove(img_path)
            return
        except Exception as e:
            logger.error(f"Math Error: {e}")
            await msg.edit_text("❌ Matematik ifodada xatolik. Masalan: `y = x^2 - 4` ko'rinishida yozing.")
            return

    # Kimyo (Formulalar)
    res_chem = calculate_molar_mass(text)
    if res_chem:
        await message.answer(res_chem, parse_mode="Markdown")
    else:
        await message.answer("❌ Noma'lum buyruq. Funksiya (`y = x^2`), kimyoviy formula (`H2SO4`) yoki DNK (`DNK: ATGC`) kiriting.")

# ==========================================
# 5. SERVER WA WEB-RUNNER
# ==========================================

async def main():
    logger.info("Akademik bot ishga tushmoqda...")

    async def handle(request):
        return web.Response(text="Academic Bot Active!")

    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
