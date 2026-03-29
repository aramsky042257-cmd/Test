# bot.py (최종 통합본, .env 유지, 주석/안내 포함)

import json
import os
import shutil
import threading
import time
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ==============================
# 📌 Load environment variables
# ==============================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")        # 봇 토큰
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",")]  # 관리자의 Telegram ID, 쉼표로 구분
LEADER_IDS = [int(x) for x in os.getenv("LEADER_IDS","").split(",")] # 조장 ID
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))                   # 허용 그룹 채팅 ID

DATA_FILE = "data.json"
LOG_FILE = "log.json"

# ==============================
# 📌 기본 함수
# ==============================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_log():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=4)

def is_allowed(update):
    return update.message.chat.id == ALLOWED_CHAT_ID

def get_day():
    return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][datetime.now().weekday()]

def is_valid_time():
    return datetime.now().hour < 23

# ==============================
# 💾 백업 (시간별 저장)
# ==============================
def backup():
    try:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if os.path.exists(DATA_FILE):
            shutil.copy(DATA_FILE, f"backup_data_{now}.json")
        if os.path.exists(LOG_FILE):
            shutil.copy(LOG_FILE, f"backup_log_{now}.json")
    except Exception as e:
        print("Backup error:", e)

def auto_backup():
    while True:
        backup()
        time.sleep(3600)

threading.Thread(target=auto_backup, daemon=True).start()

# ==============================
# 📌 Register user to a team
# ==============================
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    try:
        team, name = context.args[0], context.args[1]  # /register 3 아람
    except:
        await update.message.reply_text("사용법: /register <조번호> <이름> (예: /register 3 아람)")
        return

    user_id = str(update.message.from_user.id)
    data = load_data()
    data.setdefault("users", {})
    data.setdefault("names", {})

    data["users"][user_id] = team
    data["names"][user_id] = name
    save_data(data)

    await update.message.reply_text(f"{name}님이 {team}조로 등록되었습니다!")

# ==============================
# 📌 Record user activity (말하기/쓰기/읽기/강의)
# ==============================
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if not is_valid_time():
        await update.message.reply_text("23시 이후에는 입력할 수 없습니다.")
        return

    user_id = str(update.message.from_user.id)
    name = update.message.from_user.first_name
    text = update.message.text

    try:
        # 입력 형식: 말하기/쓰기/읽기/강의 숫자순으로, 예: 1/0/0/2
        values = list(map(int, text.split("/")))
        if len(values) != 4:
            raise ValueError
    except:
        await update.message.reply_text("잘못된 형식입니다! 예시: 1/0/0/2 (말하기/쓰기/읽기/강의)")
        return

    categories = ["말하기","쓰기","읽기","강의"]
    data = load_data()
    day = get_day()
    region = "기본지역"

    data.setdefault("records", {})
    data.setdefault("names", {})

    data["names"][user_id] = name
    data["records"].setdefault(user_id, {})
    data["records"][user_id][day] = {cat: val for cat, val in zip(categories, values)}

    save_data(data)

    # 로그 기록
    log = load_log()
    log.append({
        "user": name,
        "action": f"{text}",
        "day": day,
        "region": region,
        "time": str(datetime.now())
    })
    save_log(log)

    await update.message.reply_text(f"기록 완료! ({'/'.join(categories)} = {text})")

# ==============================
# 📌 Show my record (이름 포함)
# ==============================
async def my_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    user_id = str(update.message.from_user.id)
    data = load_data()
    day = get_day()

    try:
        r = data["records"][user_id][day]
        name = data["names"].get(user_id, "알수없음")
        msg = f"📊 오늘 기록\n이름: {name}\n"
        for k in ["말하기","쓰기","읽기","강의"]:
            msg += f"{k}: {r.get(k,0)}\n"
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("기록이 없습니다.")

# ==============================
# 📌 Team stats (조장용)
# ==============================
async def team_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if update.message.from_user.id not in LEADER_IDS:
        await update.message.reply_text("조장 전용 명령어입니다.")
        return

    data = load_data()
    day = get_day()
    team_members = {uid: name for uid, name in data.get("users", {}).items() if name == data["users"].get(str(uid))}
    result = {}

    # 팀별 합계 계산
    for uid, team in data.get("users", {}).items():
        if uid not in data.get("records", {}): 
            continue
        if day not in data["records"][uid]:
            continue
        if team not in result:
            result[team] = {"말하기":0,"쓰기":0,"읽기":0,"강의":0,"members":{}}
        for k in ["말하기","쓰기","읽기","강의"]:
            val = data["records"][uid][day].get(k,0)
            result[team][k] += val
            result[team]["members"][uid] = data["records"][uid][day]

    # 메시지 작성
    msg = f"📊 [{day} 팀별 기록]\n\n"
    for t, v in result.items():
        msg += f"{t}조 팀 합계:\n"
        for k in ["말하기","쓰기","읽기","강의"]:
            msg += f"  {k}: {v[k]}\n"
        msg += "팀원 개별 기록:\n"
        for uid, rec in v["members"].items():
            name = data["names"].get(uid,"알수없음")
            msg += f"  {name}: " + "/".join(str(rec[k]) for k in ["말하기","쓰기","읽기","강의"]) + "\n"
        msg += "\n"
    await update.message.reply_text(msg)

# ==============================
# 📌 Admin view (관리자용)
# ==============================
async def all_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("관리자 전용 명령어입니다.")
        return

    data = load_data()
    day = get_day()
    msg = f"📊 [{day} 전체 사용자 기록]\n\n"
    for uid, rec in data.get("records", {}).items():
        name = data["names"].get(uid,"알수없음")
        team = data["users"].get(uid,"")
        msg += f"{name} ({team}조)\n"
        for k in ["말하기","쓰기","읽기","강의"]:
            msg += f"  {k}: {rec.get(day, {}).get(k,0)}\n"
        msg += "\n"
    await update.message.reply_text(msg)

# ==============================
# 📌 Set region (관리자용)
# ==============================
async def set_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("관리자 전용 명령어입니다.")
        return
    await update.message.reply_text("지역 변경 기능은 준비중입니다.")

# ==============================
# 📌 Excel export (관리자용)
# ==============================
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Excel 내보내기 기능은 준비중입니다.")

# ==============================
# 📌 Admin menu
# ==============================
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if update.message.from_user.id not in ADMIN_IDS:
        return

    keyboard = [
        ["📊 All View", "📈 Team Stats"],
        ["📥 Excel", "🔄 Reset"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("관리자 메뉴", reply_markup=reply_markup)

# ==============================
# 📌 Reset (관리자용, 숨김처리)
# ==============================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if update.message.from_user.id not in ADMIN_IDS:
        return
    save_data({})
    await update.message.reply_text("모든 데이터 초기화 완료")

# ==============================
# 📌 Build bot
# ==============================
app = ApplicationBuilder().token(TOKEN).build()

# CommandHandlers
app.add_handler(CommandHandler("register", register))   # 유저 등록
app.add_handler(CommandHandler("myrecord", my_record))  # 자기 기록 확인
app.add_handler(CommandHandler("teamstats", team_stats)) # 조장
app.add_handler(CommandHandler("allview", all_view))    # 관리자
app.add_handler(CommandHandler("setregion", set_region))# 관리자
app.add_handler(CommandHandler("excel", export_excel))  # 관리자
app.add_handler(CommandHandler("adminmenu", admin_menu))# 관리자 메뉴
app.add_handler(CommandHandler("reset", reset))         # 관리자 숨김 초기화

# Record messages
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))

# Start bot
app.run_polling()
