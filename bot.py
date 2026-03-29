# ==============================
# 📌 Telegram Study Bot (Termux 최적화, 버튼 제거)
# ==============================

import os, json, asyncio
from datetime import datetime, timedelta
from telegram import Update
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
# 시작 메시지 (버튼 제거, 텍스트 안내)
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 버튼 대신 안내 메시지
    await update.message.reply_text(
        "기록 입력은 아래 형식으로 해주세요:\n"
        "온라인 입력 → o 10/2/1/0\n"
        "대면 입력 → f 10/2/1/0"
    )

# 버튼 처리 함수 제거
# async def handle_button(...) 제거

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
# 기록 입력
# ==============================
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    uid = str(update.message.from_user.id)
    data = load_data()
    if uid not in data.get("users", {}):
        await update.message.reply_text("먼저 /register 조 이름 입력해주세요")
        return
    try:
        mode, val = update.message.text.split(" ",1)
        if mode not in ("o","f"): raise Exception
        values = list(map(int, val.split("/")))
        if len(values) != 4: raise Exception
    except:
        await update.message.reply_text("형식이 잘못되었습니다.\n예시: o 10/2/1/0")
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
# 기존 함수 그대로 유지
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

    # 핸들러 등록
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("teamstats", team_stats))
    app.add_handler(CommandHandler("allview", all_view))
    app.add_handler(CommandHandler("weeklychart", weekly_chart))
    # 기록 입력만 처리
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))

    # 스케줄러 시작
    start_scheduler(app)

    # 봇 실행 (폴링)
    await app.run_polling()

if __name__=="__main__":
    asyncio.run(main())
