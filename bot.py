# ==============================
# 📌 Telegram Study Bot (Termux 최적화 버전)
# ==============================

import os, json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv
from openpyxl import Workbook

# ==============================
# 환경 변수
# ==============================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x]
LEADER_IDS = [int(x) for x in os.getenv("LEADER_IDS","").split(",") if x]
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))
DATA_FILE = os.path.join(os.getcwd(), "data.json")
NAMES_FILE = os.path.join(os.getcwd(), "names.xlsx")  # 매일 리셋용 등록 이름 파일

# ==============================
# 데이터 처리 함수
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
# 유저 등록
# ==============================
def register(update, context):
    if not is_allowed(update): return
    try:
        team = context.args[0]
        name = context.args[1]
    except:
        try:
            team = context.args[0]
            name = update.message.from_user.first_name
        except:
            update.message.reply_text("/register 1 홍길동")
            return
    uid = str(update.message.from_user.id)
    data = load_data()
    data.setdefault("users", {})
    data.setdefault("names", {})
    data["users"][uid] = team
    data["names"][uid] = name
    save_data(data)
    update.message.reply_text(f"✅ 등록 완료\n조: {team}\n이름: {name}")
    save_names_excel(data)  # 이름 파일 갱신

# ==============================
# 이름 5열씩 엑셀 저장 (매일 리셋)
# ==============================
def save_names_excel(data):
    wb = Workbook()
    ws = wb.active
    ws.title = "등록유저"
    names = list(data.get("names", {}).values())
    row = 1
    col = 1
    for idx, name in enumerate(names):
        ws.cell(row=row, column=col, value=name)
        col += 1
        if (idx+1) % 5 == 0:
            row += 1
            col = 1
    wb.save(NAMES_FILE)

# ==============================
# 기록 입력
# ==============================
def record(update, context):
    if not is_allowed(update): return
    uid = str(update.message.from_user.id)
    data = load_data()
    if uid not in data.get("users", {}):
        update.message.reply_text("먼저 /register 조 이름 입력해주세요")
        return
    try:
        mode, val = update.message.text.split(" ",1)
        values = list(map(int, val.split("/")))
        if len(values) != 4: raise Exception
    except:
        update.message.reply_text("o 10/2/1/0 형식으로 입력해주세요")
        return

    cats = ["말하기","쓰기","읽기","강의"]
    day = get_day()
    data.setdefault("records", {})
    data["records"].setdefault(uid, {})
    data["records"][uid].setdefault(day, {})
    key = "online" if mode=="o" else "offline"
    data["records"][uid][day][key] = dict(zip(cats, values))
    save_data(data)

    # 누적 합계 계산
    total = sum(values)
    label = "온라인" if mode=="o" else "대면"
    update.message.reply_text(f"✅ 저장 완료 ({label}) 총합: {total}")

# ==============================
# 조장 조회
# ==============================
def team_stats(update, context):
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
    update.message.reply_text(msg)

# ==============================
# 관리자 전체 조회
# ==============================
def all_view(update, context):
    if update.message.from_user.id not in ADMIN_IDS: return
    if not is_allowed(update): return
    data = load_data()
    msg = ""

    # 하루치 온라인/오프라인 누적
    online_count = 0
    offline_count = 0

    for uid, team in data.get("users", {}).items():
        name = data["names"][uid]
        rec = data.get("records", {}).get(uid, {}).get(get_day(), {})
        if "online" in rec:
            o = rec["online"]
            online_count += sum(o.values())
        if "offline" in rec:
            f = rec["offline"]
            offline_count += sum(f.values())

    msg += f"📊 온라인 총합: {online_count}\n"
    msg += f"📊 대면 총합: {offline_count}\n\n"

    # 하루치 입력 데이터 표시
    for uid, team in data.get("users", {}).items():
        name = data["names"][uid]
        rec = data.get("records", {}).get(uid, {}).get(get_day(), {})
        msg += f"{name}: "
        if "online" in rec:
            o = rec["online"]
            msg += f"O {o['말하기']}/{o['쓰기']}/{o['읽기']}/{o['강의']} "
        if "offline" in rec:
            f = rec["offline"]
            msg += f"F {f['말하기']}/{f['쓰기']}/{f['읽기']}/{f['강의']}"
        msg += "\n"
    update.message.reply_text(msg)

# ==============================
# 메인 실행
# ==============================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # 핸들러 등록
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("teamstats", team_stats))
    dp.add_handler(CommandHandler("allview", all_view))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, record))

    # 폴링 시작
    updater.start_polling()

if __name__=="__main__":
    main()
