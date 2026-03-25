
# ==============================
# 📌 텔레그램 스터디 관리 봇 (최종 완전체)
# ==============================

import json
import os
import shutil
import threading
import time
from datetime import datetime
from openpyxl import Workbook
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes

# ==============================
# 📌 설정
# ==============================

TOKEN = os.getenv("TOKEN")

ADMIN_IDS = [419163029, 111111111, 222222222, 333333333]
ALLOWED_CHAT_ID = -1001234567890

DATA_FILE = "data.json"
LOG_FILE = "log.json"

# 요일 → 지역 매핑
DAY_REGION = {
    "월": "서울",
    "화": "경기",
    "수": "인천",
    "목": "부산",
    "금": "대구",
    "토": "광주",
    "일": "기타"
}

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
    return ["월","화","수","목","금","토","일"][datetime.now().weekday()]

def is_valid_time():
    return datetime.now().hour < 23

# ==============================
# 💾 백업 (시간별 저장)
# ==============================
def backup():
    try:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        shutil.copy(DATA_FILE, f"backup_{now}.json")
        shutil.copy(LOG_FILE, f"backup_log_{now}.json")
    except:
        pass

def auto_backup():
    while True:
        backup()
        time.sleep(3600)

threading.Thread(target=auto_backup, daemon=True).start()

# ==============================
# 📌 조 등록
# ==============================
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    user_id = str(update.message.from_user.id)
    name = update.message.from_user.first_name

    try:
        team = context.args[0]
    except:
        await update.message.reply_text("사용법: /등록 3")
        return

    data = load_data()
    data.setdefault("users", {})
    data.setdefault("names", {})

    data["users"][user_id] = team
    data["names"][user_id] = name

    save_data(data)
    await update.message.reply_text(f"{team}조 등록 완료!")

# ==============================
# 📌 기록
# ==============================
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    if not is_valid_time():
        await update.message.reply_text("23시 이후 입력 불가!")
        return

    user = update.message.from_user
    user_id = str(user.id)
    name = user.first_name
    text = update.message.text

    try:
        category, count = text.split(":")
        count = int(count)
    except:
        return

    if category not in ["말하기","쓰기","읽기","강의"]:
        return

    data = load_data()
    day = get_day()
    region = DAY_REGION.get(day, "기타")

    data.setdefault("records", {})
    data.setdefault("names", {})

    data["names"][user_id] = name

    data["records"].setdefault(user_id, {})
    data["records"][user_id].setdefault(day, {
        "region": region,
        "말하기":0,"쓰기":0,"읽기":0,"강의":0
    })

    data["records"][user_id][day][category] += count
    save_data(data)

    # 로그
    log = load_log()
    log.append({
        "user": name,
        "action": f"{category}+{count}",
        "day": day,
        "region": region,
        "time": str(datetime.now())
    })
    save_log(log)

    await update.message.reply_text(f"{category} +{count} 완료 ({region})")

# ==============================
# 📌 취소
# ==============================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    user_id = str(update.message.from_user.id)

    try:
        category, count = context.args[0].split(":")
        count = int(count)
    except:
        await update.message.reply_text("사용법: /취소 말하기:1")
        return

    data = load_data()
    day = get_day()

    try:
        data["records"][user_id][day][category] -= count
        if data["records"][user_id][day][category] < 0:
            data["records"][user_id][day][category] = 0
        save_data(data)

        await update.message.reply_text("취소 완료")
    except:
        await update.message.reply_text("취소 실패")

# ==============================
# 📌 내 기록
# ==============================
async def my_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    user_id = str(update.message.from_user.id)
    data = load_data()
    day = get_day()

    try:
        r = data["records"][user_id][day]
        msg = f"📊 [{day}요일 ({r['region']})]\n\n"
        for k, v in r.items():
            if k != "region":
                msg += f"{k}: {v}\n"

        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("기록 없음")

# ==============================
# 📊 조 통계
# ==============================
async def team_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    data = load_data()
    day = get_day()
    region = DAY_REGION.get(day)

    result = {}

    for user_id, rec in data.get("records", {}).items():
        team = data.get("users", {}).get(user_id)
        if not team:
            continue

        result.setdefault(team, {"말하기":0,"쓰기":0,"읽기":0,"강의":0})

        if day in rec:
            for k in result[team]:
                result[team][k] += rec[day][k]

    msg = f"📊 [{day}요일 ({region}) 조별 통계]\n\n"

    for t, v in sorted(result.items()):
        msg += f"{t}조\n"
        for k in v:
            msg += f"{k}: {v[k]}\n"
        msg += "\n"

    await update.message.reply_text(msg)

# ==============================
# 📊 전체보기 (관리자)
# ==============================
async def all_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    if not is_allowed(update):
        return

    data = load_data()
    day = get_day()
    region = DAY_REGION.get(day)

    msg = f"📊 [{day}요일 ({region}) 전체]\n\n"

    for user_id, rec in data.get("records", {}).items():
        name = data.get("names", {}).get(user_id, "")
        team = data.get("users", {}).get(user_id, "")

        msg += f"{name} ({team}조)\n"

        if day in rec:
            for k, v in rec[day].items():
                if k != "region":
                    msg += f"  {k}: {v}\n"
        msg += "\n"

    await update.message.reply_text(msg)

# ==============================
# 📥 엑셀
# ==============================
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    if not is_allowed(update):
        return

    data = load_data()
    day = get_day()

    wb = Workbook()
    ws = wb.active

    ws.append(["이름","조","지역","말하기","쓰기","읽기","강의"])

    for user_id, rec in data.get("records", {}).items():
        name = data.get("names", {}).get(user_id, "")
        team = data.get("users", {}).get(user_id, "")

        r = rec.get(day, {"region":"","말하기":0,"쓰기":0,"읽기":0,"강의":0})

        ws.append([name, team, r["region"], r["말하기"], r["쓰기"], r["읽기"], r["강의"]])

    file_name = f"report_{day}.xlsx"
    wb.save(file_name)

    await update.message.reply_document(document=open(file_name, "rb"))

# ==============================
# 🎨 관리자 버튼
# ==============================
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    if not is_allowed(update):
        return

    keyboard = [
        ["📊 전체보기", "📈 조통계"],
        ["📥 엑셀", "🔄 리셋"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("관리자 메뉴", reply_markup=reply_markup)

# ==============================
# 버튼 처리
# ==============================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    text = update.message.text

    if text == "📊 전체보기":
        await all_view(update, context)
    elif text == "📈 조통계":
        await team_stats(update, context)
    elif text == "📥 엑셀":
        await export_excel(update, context)
    elif text == "🔄 리셋":
        await reset(update, context)

# ==============================
# 리셋
# ==============================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    if not is_allowed(update):
        return

    save_data({})
    await update.message.reply_text("전체 리셋 완료")

# ==============================
# 실행
# ==============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("등록", register))
app.add_handler(CommandHandler("취소", cancel))
app.add_handler(CommandHandler("내기록", my_record))
app.add_handler(CommandHandler("조통계", team_stats))
app.add_handler(CommandHandler("전체보기", all_view))
app.add_handler(CommandHandler("엑셀", export_excel))
app.add_handler(CommandHandler("관리자", admin_menu))

app.add_handler(MessageHandler(filters.TEXT, button_handler))
app.add_handler(MessageHandler(filters.TEXT, record))

app.run_polling()
