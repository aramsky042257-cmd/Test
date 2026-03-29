# ==============================
# 📌 Telegram Study Bot (완전체 + UX + 안전 스케줄러)
# ==============================

import json, os, asyncio
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
DATA_FILE = "data.json"

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
    """월 기준, 일요일 시작 주차"""
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

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "온라인 입력":
        await update.message.reply_text("온라인 입력입니다\n예시: o 10/2/1/0")
    elif text == "대면 입력":
        await update.message.reply_text("대면 입력입니다\n예시: f 10/2/1/0")

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
        values = list(map(int, val.split("/")))
        if len(values) != 4: raise Exception
    except:
        await update.message.reply_text("o 10/2/1/0 형식으로 입력해주세요")
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
# 주간 엑셀 테이블
# ==============================
def create_weekly_table_excel():
    data = load_data()
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    wb = Workbook()
    ws = wb.active
    ws.append(["조","이름"] + days)
    for uid, team in data.get("users", {}).items():
        name = data["names"][uid]
        recs = data.get("records", {}).get(uid, {})
        row = [team, name]
        for d in days:
            r = recs.get(d)
            if r:
                parts=[]
                for typ in ["online","offline"]:
                    if typ in r:
                        v = r[typ]
                        parts.append(f"{'O' if typ=='online' else 'F'} {v['말하기']}/{v['쓰기']}/{v['읽기']}/{v['강의']}")
                row.append("\n".join(parts))
            else:
                row.append("-")
        ws.append(row)
    file="weekly_table.xlsx"
    wb.save(file)
    return file

# ==============================
# 주간 그래프
# ==============================
def create_weekly_chart_excel():
    data = load_data()
    wb = Workbook()
    ws = wb.active
    ws.append(["주차","총합","온라인","대면"])
    weekly = data.get("weekly_stats", {})
    for w in sorted(weekly):
        ws.append([w, weekly[w]["total"], weekly[w]["online"], weekly[w]["offline"]])
    chart = LineChart()
    data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(weekly)+1)
    cats = Reference(ws, min_col=1, min_row=2, max_row=len(weekly)+1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, "E2")
    file="weekly_chart.xlsx"
    wb.save(file)
    return file

# ==============================
# 주간 요약
# ==============================
def save_weekly_summary():
    data = load_data()
    key = get_week_key()
    total = online = offline = 0
    for uid, recs in data.get("records", {}).items():
        for d, val in recs.items():
            for typ in ["online","offline"]:
                if typ in val:
                    for k in ["말하기","쓰기","읽기","강의"]:
                        total += val[typ][k]
                        if typ=="online": online+=val[typ][k]
                        else: offline+=val[typ][k]
    data.setdefault("weekly_stats",{})
    data["weekly_stats"][key] = {"total":total,"online":online,"offline":offline}
    save_data(data)

# ==============================
# 자동 리포트
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

# ==============================
# 수동 그래프
# ==============================
async def weekly_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS: return
    file = create_weekly_chart_excel()
    await update.message.reply_document(open(file,"rb"))
    os.remove(file)

# ==============================
# 메인 실행
# ==============================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # 핸들러
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("teamstats", team_stats))
    app.add_handler(CommandHandler("allview", all_view))
    app.add_handler(CommandHandler("weeklychart", weekly_chart))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))
    app.add_handler(MessageHandler(filters.TEXT, handle_button))

    # 스케줄러 (이벤트 루프 안에서 시작)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(send_weekly_report(app)),
                      "cron", day_of_week="sun", hour=23)
    scheduler.start()

    await app.run_polling()

if __name__=="__main__":
    asyncio.run(main())
