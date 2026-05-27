import os
import sys
import time
import types
import threading
import inspect
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ─── STUB zlapi VÀ config TRONG BỘ NHỚ (không cần folder) ───────────────────

class _Message:
    def __init__(self, text='', **kwargs):
        self.text = text
        for k, v in kwargs.items():
            setattr(self, k, v)

_zlapi_pkg    = types.ModuleType('zlapi')
_zlapi_models = types.ModuleType('zlapi.models')
_zlapi_models.Message = _Message
_zlapi_pkg.models     = _zlapi_models
sys.modules['zlapi']        = _zlapi_pkg
sys.modules['zlapi.models'] = _zlapi_models

_config_mod        = types.ModuleType('config')
_config_mod.PREFIX = '/'
sys.modules['config'] = _config_mod

os.makedirs(os.path.join(BASE_DIR, 'modules', 'cache'), exist_ok=True)

# ─── IMPORT TOOLS ─────────────────────────────────────────────────────────────

def safe_import(name):
    try:
        import importlib
        mod = importlib.import_module(name)
        print(f'[OK] {name}')
        return mod
    except Exception as e:
        print(f'[WARN] {name}: {e}')
        return None

scll_mod = safe_import('scll')
tt_mod   = safe_import('searchtiktok')
otp_mod  = safe_import('Otp')

otp_functions = []
if otp_mod:
    otp_functions = [
        (name, fn)
        for name, fn in inspect.getmembers(otp_mod, inspect.isfunction)
        if name.startswith('send_otp_via_')
    ]
    print(f'[OK] {len(otp_functions)} OTP functions loaded')

# ─── WEB SERVER ───────────────────────────────────────────────────────────────

from flask import Flask
import telebot

PORT     = int(os.environ.get('PORT', 3000))
SELF_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
TOKEN    = '8604849365:AAGvRZK_KE9Dqa6nqZoE2vr3Sf--OweJn2Y'

app = Flask(__name__)

@app.route('/')
def home():
    return 'xin chào tôi là văn Khánh'

def run_flask():
    app.run(host='0.0.0.0', port=PORT, use_reloader=False, threaded=True)

# ─── BOT ──────────────────────────────────────────────────────────────────────

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

active_ops  = {}
user_states = {}

def footer():
    return '\n\n<i>👤 Admin: @vkhanh3010</i>'

def detect_carrier(phone):
    clean = phone.strip()
    if clean.startswith('+84'):
        clean = '0' + clean[3:]
    elif clean.startswith('84') and len(clean) >= 11:
        clean = '0' + clean[2:]
    if not clean.startswith('0'):
        clean = '0' + clean
    pre = clean[:3]
    table = {
        '🔴 Viettel':      ['032','033','034','035','036','037','038','039','086','096','097','098'],
        '🔵 Mobifone':     ['070','076','077','078','079','089','090','093'],
        '🟢 Vinaphone':    ['081','082','083','084','085','088','091','094'],
        '🟡 Vietnamobile': ['052','056','058','092'],
        '🟠 Gmobile':      ['059','099'],
        '⚪ Reddi':        ['055'],
    }
    for carrier, prefixes in table.items():
        if pre in prefixes:
            return carrier
    return '❓ Không xác định'

def make_otp_status(phone, carrier, count, current, status):
    return (
        f'📱 <b>SĐT:</b> <code>{phone}</code>\n'
        f'📡 <b>Nhà Mạng:</b> {carrier}\n'
        f'🔢 <b>Số Lần:</b> {current}/{count}\n'
        f'✅ <b>Trạng Thái:</b> {status}\n\n'
        f'⛔ <code>/stop</code> để dừng'
        f'{footer()}'
    )

# ─── /start ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    cid  = msg.chat.id
    name = msg.from_user.first_name or 'bạn'
    bot.send_message(cid,
        f'👋 Xin chào <b>{name}</b>!\n\n'
        f'🤖 Tôi là bot đa năng của <b>Văn Khánh</b>.\n'
        f'Hỗ trợ: OTP · TikTok · SoundCloud\n\n'
        f'📋 Gõ /menu để xem toàn bộ lệnh.'
        f'{footer()}'
    )

# ─── /menu ────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['menu'])
def cmd_menu(msg):
    cid = msg.chat.id
    bot.send_message(cid,
        '📋 <b>DANH SÁCH LỆNH ĐẦY ĐỦ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        '📱 <b>OTP TOOL</b>\n'
        '┌ <code>/otp &lt;sdt&gt; &lt;số_lần&gt;</code>\n'
        '└ Ví dụ: <code>/otp 0901234567 20</code>\n'
        '  Hiển thị: SĐT · Nhà mạng · Số lần · Trạng thái\n\n'
        '🎵 <b>SOUNDCLOUD</b>\n'
        '┌ <code>/scl &lt;tên bài hát&gt;</code>\n'
        '└ Ví dụ: <code>/scl shape of you</code>\n'
        '  → Danh sách → gửi số để tải nhạc\n\n'
        '🎬 <b>TIKTOK</b>\n'
        '┌ <code>/tiktok &lt;từ khóa&gt;</code> — Tìm video\n'
        '├ <code>/tiktok &lt;link&gt;</code> — Tải từ link\n'
        '└ Ví dụ: <code>/tiktok mèo cute</code>\n'
        '  → Ảnh danh sách → gửi số để tải\n\n'
        '🛑 <b>ĐIỀU KHIỂN</b>\n'
        '┌ <code>/stop</code> — Dừng tác vụ đang chạy\n'
        '└ <code>/menu</code> — Xem lại danh sách lệnh\n\n'
        '━━━━━━━━━━━━━━━━━━━━━━━━━━'
        f'{footer()}'
    )

# ─── /otp ─────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['otp'])
def cmd_otp(msg):
    cid   = msg.chat.id
    parts = msg.text.strip().split()

    if len(parts) < 3:
        return bot.send_message(cid,
            '❌ <b>Thiếu tham số!</b>\n\n'
            '📌 Cú pháp: <code>/otp &lt;sdt&gt; &lt;số_lần&gt;</code>\n'
            '📌 Ví dụ: <code>/otp 0901234567 20</code>'
            f'{footer()}'
        )

    phone = parts[1]
    try:
        count = int(parts[2])
        if count <= 0 or count > 9999:
            raise ValueError()
    except ValueError:
        return bot.send_message(cid,
            f'❌ Số lần không hợp lệ! Nhập từ 1–9999.{footer()}'
        )

    digits = phone.lstrip('+').replace(' ', '').replace('-', '')
    if not digits.isdigit() or len(digits) < 9:
        return bot.send_message(cid,
            f'❌ Số điện thoại không hợp lệ!{footer()}'
        )

    if cid in active_ops:
        return bot.send_message(cid,
            f'⚠️ Đang có tác vụ chạy! Gõ /stop để dừng trước.{footer()}'
        )

    if not otp_functions:
        return bot.send_message(cid,
            f'❌ OTP module chưa sẵn sàng.{footer()}'
        )

    carrier = detect_carrier(phone)
    sent    = bot.send_message(cid,
        make_otp_status(phone, carrier, count, 0, '⏳ Đang chuẩn bị...')
    )
    mid = sent.message_id

    stop_event        = threading.Event()
    active_ops[cid]   = stop_event

    def otp_worker():
        current = 0
        try:
            while current < count and not stop_event.is_set():
                fn_name, fn = otp_functions[current % len(otp_functions)]
                service     = fn_name.replace('send_otp_via_', '').replace('_', ' ').title()
                try:
                    bot.edit_message_text(
                        make_otp_status(phone, carrier, count, current,
                                        f'📨 Đang gửi qua <b>{service}</b>...'),
                        cid, mid
                    )
                except Exception:
                    pass
                try:
                    fn(phone)
                except Exception:
                    pass
                current += 1
                time.sleep(1.5)

            final = ('🛑 Đã dừng theo yêu cầu!'
                     if stop_event.is_set()
                     else f'✅ Hoàn thành! Đã gửi <b>{current}</b> lần.')
            try:
                bot.edit_message_text(
                    make_otp_status(phone, carrier, count, current, final),
                    cid, mid
                )
            except Exception:
                pass
        finally:
            active_ops.pop(cid, None)

    threading.Thread(target=otp_worker, daemon=True).start()

# ─── /scl ─────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['scl'])
def cmd_scl(msg):
    cid   = msg.chat.id
    parts = msg.text.strip().split(None, 1)

    if len(parts) < 2:
        return bot.send_message(cid,
            '❌ <b>Thiếu tên bài hát!</b>\n\n'
            '📌 Cú pháp: <code>/scl &lt;tên bài hát&gt;</code>\n'
            '📌 Ví dụ: <code>/scl shape of you</code>'
            f'{footer()}'
        )

    if not scll_mod:
        return bot.send_message(cid, f'❌ SoundCloud module chưa sẵn sàng.{footer()}')

    query    = parts[1].strip()
    wait_msg = bot.send_message(cid,
        f'🔍 Đang tìm: <b>{query}</b>...{footer()}'
    )

    def do_search():
        try:
            songs = scll_mod.search_songs(query)
        except Exception as e:
            try:
                bot.edit_message_text(
                    f'❌ Lỗi tìm kiếm: {e}{footer()}', cid, wait_msg.message_id)
            except Exception:
                pass
            return

        if not songs:
            try:
                bot.edit_message_text(
                    f'😔 Không tìm thấy bài nào cho: <b>{query}</b>{footer()}',
                    cid, wait_msg.message_id)
            except Exception:
                pass
            return

        user_states[cid] = {'type': 'scl', 'songs': songs, 'ts': time.time()}

        text = (
            f'🎵 <b>SoundCloud — {len(songs)} bài:</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━━━\n\n'
        )
        for i, (link, title, _) in enumerate(songs[:10], 1):
            text += f'<b>{i}.</b> {title}\n'
        text += (
            f'\n━━━━━━━━━━━━━━━━━━━━━━\n'
            f'💬 Gửi <b>số thứ tự</b> để tải (hết hạn 120 giây)'
            f'{footer()}'
        )

        cover_url = songs[0][2] if songs and songs[0][2] else None
        try:
            bot.delete_message(cid, wait_msg.message_id)
        except Exception:
            pass

        if cover_url:
            try:
                bot.send_photo(cid, cover_url, caption=text)
                return
            except Exception:
                pass
        bot.send_message(cid, text)

    threading.Thread(target=do_search, daemon=True).start()

# ─── /tiktok ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['tiktok'])
def cmd_tiktok(msg):
    cid   = msg.chat.id
    parts = msg.text.strip().split(None, 1)

    if len(parts) < 2:
        return bot.send_message(cid,
            '❌ <b>Thiếu từ khóa hoặc link!</b>\n\n'
            '📌 Tìm: <code>/tiktok &lt;từ khóa&gt;</code>\n'
            '📌 Tải: <code>/tiktok &lt;link&gt;</code>\n'
            '📌 Ví dụ: <code>/tiktok mèo cute</code>'
            f'{footer()}'
        )

    if not tt_mod:
        return bot.send_message(cid, f'❌ TikTok module chưa sẵn sàng.{footer()}')

    query    = parts[1].strip()
    is_url   = 'tiktok.com' in query or query.startswith('http')
    wait_msg = bot.send_message(cid,
        f'🔍 Đang xử lý: <b>{query[:60]}</b>...{footer()}'
    )

    def do_tiktok():
        try:
            bot.delete_message(cid, wait_msg.message_id)
        except Exception:
            pass

        if is_url:
            try:
                data = tt_mod._tikwm_by_url(query)
                if not data or not data.get('data'):
                    bot.send_message(cid, f'❌ Không lấy được thông tin video.{footer()}')
                    return
                item      = data['data']
                info      = tt_mod._parse_item_fields(item)
                video_url = item.get('play') or item.get('hdplay') or ''
                caption   = (
                    f'🎬 <b>{info["title"][:200] or "TikTok Video"}</b>\n'
                    f'👤 {info["nickname"] or "TikTok"}'
                    + (f' (<code>@{info["unique_id"]}</code>)' if info["unique_id"] else '') + '\n'
                    f'👁 {tt_mod._fmt_num(info["play"])}  '
                    f'❤️ {tt_mod._fmt_num(info["like"])}  '
                    f'💬 {tt_mod._fmt_num(info["cmt"])}\n'
                    f'⏱ {info["dur"]}'
                    f'{footer()}'
                )
                if video_url:
                    try:
                        bot.send_video(cid, video_url, caption=caption, supports_streaming=True)
                    except Exception:
                        bot.send_message(cid, f'🔗 Link video:\n{video_url}\n\n{caption}')
                else:
                    bot.send_message(cid, f'❌ Không lấy được link video.{footer()}')
            except Exception as e:
                bot.send_message(cid, f'❌ Lỗi: {e}{footer()}')
        else:
            try:
                data   = tt_mod._tikwm_search(query, count=5)
                videos = tt_mod._get_videos_from_search_payload(data)
                if not videos:
                    bot.send_message(cid,
                        f'😔 Không tìm thấy video cho: <b>{query}</b>{footer()}')
                    return

                user_states[cid] = {'type': 'tiktok', 'videos': videos, 'ts': time.time()}

                text = (
                    f'🎬 <b>TikTok — Kết quả: {query}</b>\n'
                    f'━━━━━━━━━━━━━━━━━━━━━━\n\n'
                )
                for i, v in enumerate(videos[:5], 1):
                    info  = tt_mod._parse_item_fields(v)
                    t     = info['title']
                    short = (t[:55] + '…') if len(t) > 55 else t
                    text += (
                        f'<b>{i}.</b> {short}\n'
                        f'   👁 {tt_mod._fmt_num(info["play"])}  '
                        f'❤️ {tt_mod._fmt_num(info["like"])}  '
                        f'⏱ {info["dur"]}\n\n'
                    )
                text += (
                    f'━━━━━━━━━━━━━━━━━━━━━━\n'
                    f'💬 Gửi <b>số</b> (1–{min(5, len(videos))}) để tải'
                    f'{footer()}'
                )

                list_img_path = None
                try:
                    result = tt_mod._build_list_image(query, videos)
                    if isinstance(result, str) and os.path.exists(result):
                        list_img_path = result
                    elif result and hasattr(result, 'save'):
                        cache_dir = os.path.join(BASE_DIR, 'modules', 'cache')
                        os.makedirs(cache_dir, exist_ok=True)
                        list_img_path = os.path.join(cache_dir, f'list_{int(time.time())}.jpg')
                        result.save(list_img_path)
                except Exception:
                    list_img_path = None

                if list_img_path and os.path.exists(list_img_path):
                    try:
                        with open(list_img_path, 'rb') as f:
                            bot.send_photo(cid, f, caption=text)
                        try:
                            os.remove(list_img_path)
                        except Exception:
                            pass
                        return
                    except Exception:
                        try:
                            os.remove(list_img_path)
                        except Exception:
                            pass

                bot.send_message(cid, text)
            except Exception as e:
                bot.send_message(cid, f'❌ Lỗi tìm kiếm: {e}{footer()}')

    threading.Thread(target=do_tiktok, daemon=True).start()

# ─── /stop ────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['stop'])
def cmd_stop(msg):
    cid = msg.chat.id
    if cid in active_ops:
        active_ops[cid].set()
        bot.send_message(cid, f'🛑 Đã gửi tín hiệu dừng!{footer()}')
    else:
        bot.send_message(cid, f'⚠️ Không có tác vụ nào đang chạy.{footer()}')

# ─── CHỌN SỐ (SoundCloud / TikTok) ───────────────────────────────────────────

@bot.message_handler(content_types=['text'])
def handle_text(msg):
    cid  = msg.chat.id
    text = msg.text.strip()

    if text.startswith('/') or not text.isdigit():
        return

    num   = int(text)
    state = user_states.get(cid)
    if not state:
        return

    if time.time() - state.get('ts', 0) > 120:
        user_states.pop(cid, None)
        return bot.send_message(cid,
            f'⏰ Kết quả đã hết hạn. Vui lòng tìm lại.{footer()}'
        )

    if state['type'] == 'scl':
        songs = state.get('songs', [])
        if num < 1 or num > len(songs):
            return bot.send_message(cid,
                f'❌ Số không hợp lệ. Nhập từ 1 đến {len(songs)}.{footer()}'
            )
        link, title, _ = songs[num - 1]
        user_states.pop(cid, None)
        wait = bot.send_message(cid, f'⏳ Đang tải: <b>{title}</b>...{footer()}')

        def dl_scl():
            try:
                audio_url = scll_mod.get_music_stream_url(link)
                if not audio_url:
                    try:
                        bot.edit_message_text(
                            f'❌ Không thể tải bài này.{footer()}', cid, wait.message_id)
                    except Exception:
                        pass
                    return
                cover_url = scll_mod.get_track_cover(link)
                caption   = f'🎵 <b>{title}</b>\n🔗 {link}{footer()}'
                try:
                    bot.delete_message(cid, wait.message_id)
                except Exception:
                    pass
                if cover_url:
                    try:
                        bot.send_photo(cid, cover_url,
                            caption=f'🎵 <b>{title}</b>{footer()}')
                    except Exception:
                        pass
                try:
                    bot.send_audio(cid, audio_url, title=title, caption=caption)
                except Exception:
                    bot.send_message(cid, f'🔗 Link nhạc:\n{audio_url}\n\n{caption}')
            except Exception as e:
                try:
                    bot.edit_message_text(
                        f'❌ Lỗi tải: {e}{footer()}', cid, wait.message_id)
                except Exception:
                    pass

        threading.Thread(target=dl_scl, daemon=True).start()

    elif state['type'] == 'tiktok':
        if not tt_mod:
            return
        videos = state.get('videos', [])
        if num < 1 or num > len(videos):
            return bot.send_message(cid,
                f'❌ Số không hợp lệ. Nhập từ 1 đến {len(videos)}.{footer()}'
            )
        item      = videos[num - 1]
        user_states.pop(cid, None)
        info      = tt_mod._parse_item_fields(item)
        video_url = item.get('play') or item.get('hdplay') or ''
        caption   = (
            f'🎬 <b>{info["title"][:200] or "TikTok Video"}</b>\n'
            f'👤 {info["nickname"] or "TikTok"}\n'
            f'👁 {tt_mod._fmt_num(info["play"])}  ❤️ {tt_mod._fmt_num(info["like"])}\n'
            f'⏱ {info["dur"]}'
            f'{footer()}'
        )
        wait = bot.send_message(cid, f'⏳ Đang tải video TikTok...{footer()}')

        def dl_tiktok():
            try:
                bot.delete_message(cid, wait.message_id)
            except Exception:
                pass
            if not video_url:
                bot.send_message(cid, f'❌ Không có link video.{footer()}')
                return
            try:
                bot.send_video(cid, video_url, caption=caption, supports_streaming=True)
            except Exception:
                bot.send_message(cid, f'🔗 Link video:\n{video_url}\n\n{caption}')

        threading.Thread(target=dl_tiktok, daemon=True).start()

# ─── AUTO-PING 5 LUỒNG ────────────────────────────────────────────────────────

def ping_worker(worker_id):
    time.sleep(30 + worker_id * 10)
    while True:
        try:
            if SELF_URL:
                requests.get(SELF_URL, timeout=10)
        except Exception:
            pass
        time.sleep(240 + worker_id * 12)

# ─── ĐĂNG KÝ COMMANDS ─────────────────────────────────────────────────────────

bot.set_my_commands([
    telebot.types.BotCommand('/start',  'Bắt đầu bot'),
    telebot.types.BotCommand('/menu',   'Xem toàn bộ lệnh'),
    telebot.types.BotCommand('/otp',    'Gửi OTP: /otp <sdt> <số_lần>'),
    telebot.types.BotCommand('/scl',    'Tải nhạc SoundCloud'),
    telebot.types.BotCommand('/tiktok', 'TikTok tìm kiếm hoặc tải link'),
    telebot.types.BotCommand('/stop',   'Dừng tác vụ đang chạy'),
])

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    print(f'[Flask] Port {PORT}')

    for i in range(5):
        threading.Thread(target=ping_worker, args=(i,), daemon=True).start()
    print('[Ping] 5 threads started')

    print('[Bot] Polling...')
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
