# ==============================
# 📌 Telegram Study Bot (Termux 안전버전)
# ==============================

import os, json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from openpyxl import Workbook
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==============================
# 환경 변수
# ==============================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x]
LEADER_IDS = [int(x) for x in os.getenv("LEADER_IDS","").split(",") if x]
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))
DATA_FILE = os.path.join(os.getcwd(), "data.json")

# ==============================
# 데이터 로드/저장
# ==============================
def load_data():
    try:
        with open(DATA_FILE,"r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE,"w") as f:
        json.dump(data,f,ensure_ascii=False, indent=4)

def is_allowed(update):
    return update.message.chat.id == ALLOWED_CHAT_ID

def get_day():
    return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][datetime.now().weekday()]

# ==============================
# 시작 / 버튼 UI
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["온라인 입력", "대면 입력"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("입력 버튼입니다", reply_markup=reply_markup)

# ==============================
# 버튼 선택 처리
# ==============================
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "온라인 입력":
        context.user_data["mode"] = "o"
        await update.message.reply_text("온라인 입력 모드입니다.\n예시: 10/2/1/0 (말하기/쓰기/읽기/강의)")
    elif text == "대면 입력":
        context.user_data["mode"] = "f"
        await update.message.reply_text("대면 입력 모드입니다.\n예시: 10/2/1/0 (말하기/쓰기/읽기/강의)")

# ==============================
# 기록 입력
# ==============================
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    uid = str(update.message.from_user.id)
    data = load_data()
    if uid not in data.get("users", {}):
        await update.message.reply_text("먼저 /register 조 이름 입력해주세요")
        return

    mode = context.user_data.get("mode")
    if not mode:
        await update.message.reply_text("먼저 '온라인 입력' 또는 '대면 입력' 버튼을 눌러주세요")
        return

    try:
        values = list(map(int, update.message.text.split("/")))
        if len(values) != 4: raise Exception
    except:
        await update.message.reply_text("형식이 잘못되었습니다. 예시: 10/2/1/0")
        return

    cats = ["말하기","쓰기","읽기","강의"]
    day = get_day()
    data.setdefault("records", {})
    data["records"].setdefault(uid, {})
    data["records"][uid].setdefault(day, {})
    key = "online" if mode=="o" else "offline"
    data["records"][uid][day][key] = dict(zip(cats, values))
    save_data(data)

    label = "온라인" if mode=="o" else "대면"
    await update.message.reply_text(f"✅ 저장 완료 ({label})")

    context.user_data.pop("mode")

# ==============================
# 유저 등록
# ==============================
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    try:
        team = context.args[0]
        name = context.args[1]
    except:
        try:
            team = context.args[0]
            name = update.message.from_user.first_name
        except:
            await update.message.reply_text("/register 1 홍길동")
            return
    uid = str(update.message.from_user.id)
    data = load_data()
    data.setdefault("users", {})
    data.setdefault("names", {})
    data["users"][uid] = team
    data["names"][uid] = name
    save_data(data)
    await update.message.reply_text(f"✅ 등록 완료\n조: {team}\n이름: {name}")

# ==============================
# 단순 조회 예시 (조장/관리자)
# ==============================
async def team_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in LEADER_IDS: return
    if not is_allowed(update): return
    uid = str(update.message.from_user.id)
    data = load_data()
    my_team = data.get("users", {}).get(uid)
    msg = f"{my_team}조\n\n"
    for user_id, team in data.get("users", {}).items():
        if team != my_team: continue
        name = data["names"][user_id]
        rec = data.get("records", {}).get(user_id, {}).get(get_day(), {})
        msg += f"{name}\n"
        if "online" in rec:
            o = rec["online"]
            msg += f"O {o['말하기']}/{o['쓰기']}/{o['읽기']}/{o['강의']}\n"
        if "offline" in rec:
            f = rec["offline"]
            msg += f"F {f['말하기']}/{f['쓰기']}/{f['읽기']}/{f['강의']}\n"
        msg += "\n"
    await update.message.reply_text(msg)

# ==============================
# APScheduler 안전 실행
# ==============================
scheduler = AsyncIOScheduler()
async def send_weekly_report(app):
    # 실제 리포트 함수 구현 필요
    await asyncio.sleep(0.1)
    print("주간 리포트 전송")

def start_scheduler(app):
    scheduler.add_job(lambda: asyncio.create_task(send_weekly_report(app)), "cron", day_of_week="sun", hour=23)
    scheduler.start()

# ==============================
# 메인 실행
# ==============================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # 커맨드 핸들러
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("teamstats", team_stats))

    # ✅ 버튼 핸들러 (텍스트 필터 제한)
    app.add_handler(MessageHandler(filters.Regex("^(온라인 입력|대면 입력)$"), handle_button))

    # ✅ 기록 핸들러
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))

    # 스케줄러
    start_scheduler(app)

    # 실행
    app.run_polling()

if __name__=="__main__":
    main()
