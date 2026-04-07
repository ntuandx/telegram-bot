import telebot
import requests
import time
import threading
import json
import os
from datetime import datetime, timedelta
from flask import Flask, request

TOKEN = "8515982394:AAGhiw2HqZNkxj_KAZYyXsmmWYexHMjEiis"
ADMIN_ID = 5936960352
API_URL = "https://living-telecommunications-start-consoles.trycloudflare.com/api/txmd5"
KEY_FILE = "keys.json"

bot = telebot.TeleBot(TOKEN)
activated_users = {}
app = Flask(__name__)

# ================== QUẢN LÝ KEY ==================
def load_keys():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_keys(keys):
    with open(KEY_FILE, "w") as f:
        json.dump(keys, f, indent=4)

keys_db = load_keys()
if not keys_db:
    keys_db = {
        "VIP123456": {"expiry": None, "usage": 0},
        "TAIXIU2026": {"expiry": (datetime.now() + timedelta(days=365)).isoformat(), "usage": 0}
    }
    save_keys(keys_db)

def is_admin(chat_id):
    return chat_id == ADMIN_ID

def is_key_valid(key):
    if key not in keys_db:
        return False, "Key không tồn tại"
    expiry = keys_db[key].get("expiry")
    if expiry is None:
        return True, "Vĩnh viễn"
    if datetime.now() > datetime.fromisoformat(expiry):
        return False, "Key đã hết hạn"
    return True, "Còn dùng"

def add_new_key(key, days):
    keys_db[key] = {
        "expiry": (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None,
        "usage": 0
    }
    save_keys(keys_db)
    return True

def del_key(key):
    if key in keys_db:
        del keys_db[key]
        save_keys(keys_db)
        return True
    return False

# ================== GỬI DỮ LIỆU ==================
def send_data(chat_id, key):
    last_session = None
    while chat_id in activated_users:
        try:
            r = requests.get(API_URL, timeout=10)
            if r.status_code == 200:
                data = r.json()
                betting = data.get("betting_info", {})
                current_session = betting.get("phien_cuoc", data.get("phien"))
                ket_qua = data.get("ket_qua")
                
                if current_session and current_session != last_session:
                    last_session = current_session
                    if ket_qua == "Tài":
                        result_text = "🟢 TÀI"
                    elif ket_qua == "Xỉu":
                        result_text = "🔴 XỈU"
                    else:
                        result_text = "⏳ Chờ"
                    msg = f"🎲 TÀI XỈU MD5\n🔢 PHIÊN: #{current_session}\n🎯 KẾT QUẢ: {result_text}"
                    bot.send_message(chat_id, msg)
                    if key in keys_db:
                        keys_db[key]["usage"] += 1
                        save_keys(keys_db)
            time.sleep(3)
        except:
            time.sleep(5)

# ====================== LỆNH BOT ======================
@bot.message_handler(commands=['start'])
def start(m):
    if is_admin(m.chat.id):
        if m.chat.id not in activated_users:
            activated_users[m.chat.id] = "ADMIN"
            bot.reply_to(m, "👑 Admin đã kích hoạt!")
            threading.Thread(target=send_data, args=(m.chat.id, "ADMIN"), daemon=True).start()
        return
    bot.reply_to(m, "🎲 TÀI XỈU MD5\n\nGửi KEY để kích hoạt.\nKEY mẫu: VIP123456")

@bot.message_handler(commands=['stop'])
def stop(m):
    if m.chat.id in activated_users:
        del activated_users[m.chat.id]
        bot.reply_to(m, "⛔ Đã dừng!")

@bot.message_handler(commands=['addkey'])
def addkey(m):
    if not is_admin(m.chat.id):
        bot.reply_to(m, "Không có quyền!")
        return
    try:
        parts = m.text.split()
        if len(parts) < 3:
            bot.reply_to(m, "Cách dùng: /addkey TENKEY SO_NGAY")
            return
        key = parts[1]
        days = int(parts[2])
        if key in keys_db:
            bot.reply_to(m, f"Key {key} đã tồn tại!")
            return
        add_new_key(key, days)
        bot.reply_to(m, f"✅ Đã thêm key: {key}, hạn {days} ngày")
    except:
        bot.reply_to(m, "Lỗi!")

@bot.message_handler(commands=['delkey'])
def delkey(m):
    if not is_admin(m.chat.id):
        bot.reply_to(m, "Không có quyền!")
        return
    try:
        parts = m.text.split()
        if len(parts) < 2:
            bot.reply_to(m, "Cách dùng: /delkey TENKEY")
            return
        key = parts[1]
        if del_key(key):
            bot.reply_to(m, f"✅ Đã xóa key: {key}")
        else:
            bot.reply_to(m, f"Key {key} không tồn tại")
    except:
        bot.reply_to(m, "Lỗi!")

@bot.message_handler(commands=['listkey'])
def listkey(m):
    if not is_admin(m.chat.id):
        bot.reply_to(m, "Không có quyền!")
        return
    if not keys_db:
        bot.reply_to(m, "Chưa có key")
        return
    msg = "📋 DANH SÁCH KEY:\n"
    for k, v in keys_db.items():
        expiry = v.get("expiry")
        expiry_str = "Vĩnh viễn" if not expiry else datetime.fromisoformat(expiry).strftime("%d/%m/%Y")
        msg += f"- {k} (Hạn: {expiry_str}) - Dùng: {v.get('usage',0)}\n"
    bot.reply_to(m, msg)

@bot.message_handler(commands=['users'])
def users(m):
    if not is_admin(m.chat.id):
        bot.reply_to(m, "Không có quyền!")
        return
    if not activated_users:
        bot.reply_to(m, "Không có user")
        return
    msg = "👥 USER ĐANG DÙNG:\n"
    for uid, key in activated_users.items():
        msg += f"- {uid} (Key: {key})\n"
    bot.reply_to(m, msg)

@bot.message_handler(commands=['stats'])
def stats(m):
    if not is_admin(m.chat.id):
        bot.reply_to(m, "Không có quyền!")
        return
    msg = f"📊 THỐNG KÊ:\nTổng key: {len(keys_db)}\nUser đang dùng: {len(activated_users)}\nTổng lượt dùng: {sum(v.get('usage',0) for v in keys_db.values())}"
    bot.reply_to(m, msg)

@bot.message_handler(func=lambda m: True)
def handle(m):
    if is_admin(m.chat.id):
        return
    key = m.text.strip()
    if key.startswith('/'):
        return
    valid, msg = is_key_valid(key)
    if valid:
        if m.chat.id not in activated_users:
            activated_users[m.chat.id] = key
            bot.reply_to(m, f"✅ Kích hoạt thành công! Key: {key}")
            threading.Thread(target=send_data, args=(m.chat.id, key), daemon=True).start()
    else:
        bot.reply_to(m, f"❌ {msg}")

# ================== WEBHOOK CHO RENDER ==================
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

@app.route('/')
def home():
    return 'Bot is running!'

def run_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f'https://telegram-bot.onrender.com/webhook/{TOKEN}')
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    run_webhook()