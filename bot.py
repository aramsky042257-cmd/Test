# ==============================
# 📌 Telegram Study Bot (최종 완성)
# ==============================
# ✔ 유저 등록
# ✔ 온라인(o) / 대면(f) 기록
# ✔ 개인 조회
# ✔ 조장 팀 조회 (/teamstats)
# ✔ 관리자 전체 조회 (/allview)
# ✔ 주간 엑셀
# ✔ 주간 그래프 (누적)
# ✔ 지역 설정
# ✔ 주차 = 달력 + 일요일 기준
# ✔ 관리자 / 조장 권한 분리
# ==============================

import json, os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

# ==============================
# 📌 환경 변수
# ==============================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x]
LEADER_IDS = [int(x) for x in os.getenv("LEADER_IDS","").split(",") if x]
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))

DATA_FILE = "data.json"

# ==============================
# 📌 기본 함수
# ==============================
def load_data():
    try:
        with open(DATA_FILE,"r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE,"w") as f:
        json.dump(data,f,ensure_ascii=False,indent=4)

def is_allowed(update):
    return update.message.chat.id == ALLOWED_CHAT_ID

def get_day():
    return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][datetime.now().weekday()]

# ==============================
# 📌 주차 (일요일 기준)
# ==============================
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
# 📌 유저 등록
# ==============================
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return

    try:
        team, name = context.args[0], context.args[1]
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
    await update.message.reply_text("등록 완료")

# ==============================
# 📌 기록 입력
# ==============================
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return

    uid = str(update.message.from_user.id)
    data = load_data()

    if uid not in data.get("users", {}):
        await update.message.reply_text("/register 먼저")
        return

    try:
        mode, val = update.message.text.split(" ",1)
        values = list(map(int, val.split("/")))
    except:
        await update.message.reply_text("o 1/0/0/2 또는 f 1/0/0/2")
        return

    if mode not in ["o","f"]:
        await update.message.reply_text("o 또는 f")
        return

    if any(v<0 or v>100 for v in values):
        await update.message.reply_text("0~100만")
        return

    cats = ["말하기","쓰기","읽기","강의"]
    day = get_day()

    data.setdefault("records", {})
    data["records"].setdefault(uid, {})
    data["records"][uid].setdefault(day, {})

    key = "online" if mode=="o" else "offline"
    data["records"][uid][day][key] = dict(zip(cats,values))

    save_data(data)
    await update.message.reply_text("기록 완료")

# ==============================
# 📌 개인 조회
# ==============================
async def my_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return

    uid = str(update.message.from_user.id)
    data = load_data()

    name = data.get("names",{}).get(uid,"")
    r = data.get("records",{}).get(uid,{}).get(get_day(),{})

    msg = f"{name} 오늘 기록\n"

    for typ in ["online","offline"]:
        if typ in r:
            v = r[typ]
            msg += f"{'온라인' if typ=='online' else '대면'} {v['말하기']}/{v['쓰기']}/{v['읽기']}/{v['강의']}\n"

    await update.message.reply_text(msg)

# ==============================
# 📌 조장 팀 조회 (조장만)
# ==============================
async def team_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in LEADER_IDS:
        return
    if not is_allowed(update): return

    uid = str(update.message.from_user.id)
    data = load_data()

    my_team = data.get("users", {}).get(uid)
    if not my_team:
        return

    msg = f"{my_team}조\n\n"

    total = {"말하기":0,"쓰기":0,"읽기":0,"강의":0}

    for user_id, team in data.get("users", {}).items():
        if team != my_team:
            continue

        name = data["names"].get(user_id,"")
        recs = data.get("records",{}).get(user_id,{}).get(get_day(),{})

        person = {"말하기":0,"쓰기":0,"읽기":0,"강의":0}

        for typ in ["online","offline"]:
            if typ in recs:
                for k in person:
                    person[k] += recs[typ].get(k,0)

        msg += f"{name} {person['말하기']}/{person['쓰기']}/{person['읽기']}/{person['강의']}\n"

        for k in total:
            total[k] += person[k]

    msg += f"\n합계 {total['말하기']}/{total['쓰기']}/{total['읽기']}/{total['강의']}"
    await update.message.reply_text(msg)

# ==============================
# 📌 관리자 전체 조회
# ==============================
async def all_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    if not is_allowed(update): return

    data = load_data()

    teams = {}
    grand = {"말하기":0,"쓰기":0,"읽기":0,"강의":0}

    for uid, team in data.get("users", {}).items():
        name = data["names"].get(uid,"")
        recs = data.get("records",{}).get(uid,{}).get(get_day(),{})

        person = {"말하기":0,"쓰기":0,"읽기":0,"강의":0}

        for typ in ["online","offline"]:
            if typ in recs:
                for k in person:
                    person[k] += recs[typ].get(k,0)

        teams.setdefault(team, []).append((name, person))

    msg = ""

    for team in sorted(teams):
        msg += f"{team}조\n"
        team_total = {"말하기":0,"쓰기":0,"읽기":0,"강의":0}

        for name, r in teams[team]:
            msg += f"{name} {r['말하기']}/{r['쓰기']}/{r['읽기']}/{r['강의']}\n"
            for k in team_total:
                team_total[k] += r[k]

        msg += f"합계 {team_total['말하기']}/{team_total['쓰기']}/{team_total['읽기']}/{team_total['강의']}\n\n"

        for k in grand:
            grand[k] += team_total[k]

    msg += f"전체합계 {grand['말하기']}/{grand['쓰기']}/{grand['읽기']}/{grand['강의']}"
    await update.message.reply_text(msg)

# ==============================
# 📊 주간 그래프 (누적)
# ==============================
def save_weekly_summary():
    data = load_data()
    key = get_week_key()

    total=online=offline=0

    for uid,recs in data.get("records",{}).items():
        for day,val in recs.items():
            for typ in ["online","offline"]:
                if typ in val:
                    for k in ["말하기","쓰기","읽기","강의"]:
                        total+=val[typ][k]
                        if typ=="online": online+=val[typ][k]
                        else: offline+=val[typ][k]

    data.setdefault("weekly_stats",{})
    data["weekly_stats"][key] = {
        "total": total,
        "online": online,
        "offline": offline
    }

    save_data(data)

async def weekly_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    if not is_allowed(update): return

    save_weekly_summary()
    data = load_data()

    wb = Workbook()
    ws = wb.active

    ws.append(["주차","총합","온라인","대면"])

    weekly = data.get("weekly_stats",{})
    for w in sorted(weekly):
        ws.append([w, weekly[w]["total"], weekly[w]["online"], weekly[w]["offline"]])

    chart = LineChart()
    data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(weekly)+1)
    cats = Reference(ws, min_col=1, min_row=2, max_row=len(weekly)+1)

    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats)

    ws.add_chart(chart,"E2")

    file="chart.xlsx"
    wb.save(file)

    with open(file,"rb") as f:
        await update.message.reply_document(f)

    os.remove(file)

# ==============================
# 🚀 실행
# ==============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("register", register))
app.add_handler(CommandHandler("myrecord", my_record))
app.add_handler(CommandHandler("teamstats", team_stats))  # 조장용
app.add_handler(CommandHandler("allview", all_view))      # 관리자용
app.add_handler(CommandHandler("weeklychart", weekly_chart))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))

app.run_polling()
