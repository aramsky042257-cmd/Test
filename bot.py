# ==============================
# 📌 Telegram Study Bot (Termux 최적화 버전)
# ==============================

import os, json, asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
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
# 기본 데이터 함수
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

def get_week_key():
    now = datetime.now()
    year, month = now.year, now.month
    first_day = datetime(year, month, 1)
    first_sunday = first_day
    while first_sunday.weekday() != 6:
        first_sunday += timedelta(days=1)
    if now < first_sunday:
        week = 1
    else:
        diff = (now - first_sunday).days
        week = (diff // 7) + 1
    return f"{year}-{month:02d} {week}주"

# ==============================
# 시작 / 버튼 UI
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["온라인 입력", "대면 입력"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("입력 버튼입니다", reply_markup=reply_markup)

# ==============================
# 버튼 처리 함수 (mode 저장)
# ==============================
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "온라인 입력":
        context.user_data["mode"] = "o"  # 온라인 모드 저장
        await update.message.reply_text("온라인 입력 모드입니다.\n예시: 10/2/1/0 (말하기/쓰기/읽기/강의)")
        return
    elif text == "대면 입력":
        context.user_data["mode"] = "f"  # 대면 모드 저장
        await update.message.reply_text("대면 입력 모드입니다.\n예시: 10/2/1/0 (말하기/쓰기/읽기/강의)")
        return
    # 버튼 아닌 텍스트는 record에서 처리

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
# 기록 입력 함수 수정 (mode 자동 처리)
# ==============================
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    uid = str(update.message.from_user.id)
    data = load_data()
    if uid not in data.get("users", {}):
        await update.message.reply_text("먼저 /register 조 이름 입력해주세요")
        return

    mode = context.user_data.get("mode")  # 버튼에서 선택한 모드 가져오기
    if not mode:
        await update.message.reply_text("먼저 '온라인 입력' 또는 '대면 입력' 버튼을 눌러주세요")
        return

    try:
        # 이제 메시지에는 숫자만 입력 (예: 10/2/1/0)
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

    context.user_data.pop("mode")  # 기록 후 모드 초기화

# ==============================
# 조장 조회
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
# 관리자 전체 조회
# ==============================
async def all_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS: return
    if not is_allowed(update): return
    data = load_data()
    teams = {}
    for uid, team in data.get("users", {}).items():
        name = data["names"][uid]
        rec = data.get("records", {}).get(uid, {}).get(get_day(), {})
        teams.setdefault(team, []).append((name, rec))
    msg = ""
    for team in sorted(teams):
        msg += f"{team}조\n"
        for name, rec in teams[team]:
            msg += f"{name}\n"
            if "online" in rec:
                o = rec["online"]
                msg += f"O {o['말하기']}/{o['쓰기']}/{o['읽기']}/{o['강의']}\n"
            if "offline" in rec:
                f = rec["offline"]
                msg += f"F {f['말하기']}/{f['쓰기']}/{f['읽기']}/{f['강의']}\n"
            msg += "\n"
        msg += "\n"
    await update.message.reply_text(msg)

# ==============================
# 엑셀 관련 함수
# ==============================
# (함수 내용 그대로 유지)
# create_weekly_table_excel(), create_weekly_chart_excel(), save_weekly_summary()

# ==============================
# 리포트
# ==============================
async def send_weekly_report(app):
    save_weekly_summary()
    table_file = create_weekly_table_excel()
    chart_file = create_weekly_chart_excel()
    for admin_id in ADMIN_IDS:
        await app.bot.send_message(admin_id, "📊 주간 리포트")
        await app.bot.send_document(admin_id, open(table_file,"rb"))
        await app.bot.send_document(admin_id, open(chart_file,"rb"))
    os.remove(table_file)
    os.remove(chart_file)

async def weekly_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS: return
    file = create_weekly_chart_excel()
    await update.message.reply_document(open(file,"rb"))
    os.remove(file)

# ==============================
# 스케줄러 시작 함수
# ==============================
scheduler = AsyncIOScheduler()

def start_scheduler(app):
    scheduler.add_job(lambda: asyncio.create_task(send_weekly_report(app)), "cron", day_of_week="sun", hour=23)
    scheduler.start()

# ==============================
# 메인 실행
# ==============================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # 커맨드 핸들러
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("teamstats", team_stats))
    app.add_handler(CommandHandler("allview", all_view))
    app.add_handler(CommandHandler("weeklychart", weekly_chart))

    # ✅ 버튼 메시지 핸들러 먼저 등록
    app.add_handler(MessageHandler(filters.TEXT, handle_button))
    
    # ✅ 기록 입력 핸들러는 그 다음에 등록
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))

    # 스케줄러 시작
    start_scheduler(app)

    # 봇 실행
    await app.run_polling()

if __name__=="__main__":
    asyncio.run(main())
