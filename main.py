import os
import io
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from PIL import Image, ImageDraw
import google.generativeai as genai

# ==========================================
# 1. RENDER UCHUN HTTP PORT BINDING (WEBSERVER)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Math Bot is alive!")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Web server {port}-portda ishga tushdi...")
    server.serve_forever()

# Render portini alohida potokda band qilamiz
threading.Thread(target=start_health_server, daemon=True).start()

# ==========================================
# 2. BOT VA GEMINI SOZLAMALARI
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8905569753:AAFVb80abOaCuBNN_5gipxntB3SDxEz96lE")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def text_to_image(text_content, title="Dekart Koordinatalari — Yechim"):
    width = 1000
    padding = 40
    line_height = 32
    
    lines = text_content.split("\n")
    height = max(600, padding * 2 + len(lines) * line_height + 100)
    
    image = Image.new("RGB", (width, height), color="#1e1e2e")
    draw = ImageDraw.Draw(image)
    
    draw.text((padding, padding), title, fill="#89b4fa")
    draw.line([(padding, padding + 40), (width - padding, padding + 40)], fill="#585b70", width=2)
    
    y = padding + 60
    for line in lines:
        draw.text((padding, y), line, fill="#cdd6f4")
        y += line_height
        
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Assalomu alaykum! 👋\n\n"
        "Men Dekart koordinatalar sistemasi va matematik masalalarni yechuvchi botman.\n"
        "📷 Menga 1 yoki 2 ta rasm va masalaga oid yozuv / savolingizni yuboring.\n"
        "🖼 Javobni aniq qilib **rasm ko'rinishida** tayyorlab beraman!"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['photo', 'text'])
def handle_message(message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {'photos': [], 'caption': ''}

    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        img = Image.open(io.BytesIO(downloaded_file))
        user_data[user_id]['photos'].append(img)
        
        if message.caption:
            user_data[user_id]['caption'] += " " + message.caption

        bot.reply_to(
            message, 
            f"📸 Rasm qabul qilindi ({len(user_data[user_id]['photos'])}/2).\n"
            "Yana rasm yoki qo'shimcha matn yuborishingiz mumkin.\n"
            "Yechishni boshlash uchun **/yech** buyrug'ini bosing!"
        )

    elif message.content_type == 'text':
        if message.text == '/yech':
            process_solution(message)
        else:
            user_data[user_id]['caption'] += " " + message.text
            bot.reply_to(
                message, 
                "✍️ Matn qabul qilindi. /yech buyrug'ini bosing yoki rasm yuboring."
            )

def process_solution(message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {'photos': [], 'caption': ''})
    
    photos = data['photos']
    caption = data['caption'].strip()

    if not photos and not caption:
        bot.reply_to(message, "Iltimos, avval rasm yoki masala matnini yuboring!")
        return

    status_msg = bot.reply_to(message, "🧠 Masala tahlil qilinmoqda va yechim rasmga tushirilmoqda...")

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        system_prompt = (
            "Siz Dekart koordinatalar sistemasi va funksiyalar bo'yicha mutaxassissiz. "
            "Foydalanuvchi yuborgan rasm(lar) va/yoki matndagi masalani aniq va qadamma-qadam yeching. "
            "Javob o'zbek tilida, tushunarli, aniq va ixcham bo'lsin. "
            "Nuqtalar koordinatalari, funksiya tenglamalari va grafik bo'yicha barcha xulosalarni aniq keltiring."
        )

        prompt_contents = [system_prompt]
        prompt_contents.extend(photos[:2])
        if caption:
            prompt_contents.append(f"Foydalanuvchi izohi: {caption}")

        response = model.generate_content(prompt_contents)
        solution_text = response.text

        result_image_stream = text_to_image(solution_text)

        bot.send_photo(
            message.chat.id, 
            photo=result_image_stream, 
            caption="✅ Masala yechimi rasmda tayyorlandi!"
        )
        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos, Render Environment Variables qismida GEMINI_API_KEY o'rnatilganini tekshiring.", 
            message.chat.id, 
            status_msg.message_id
        )

    user_data[user_id] = {'photos': [], 'caption': ''}

if __name__ == '__main__':
    print("Bot ishga tushmoqda...")
    bot.infinity_polling()
