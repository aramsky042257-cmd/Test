import os, json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

# ==============================
# 환경 변수
# ==============================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x]
LEADER_IDS = [int(x) for x in os.getenv("LEADER_IDS","").split(",") if x]
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))
DATA_FILE = os.path.join(os.getcwd(), "data.json")
NAME_FILE = os.path.join(os.getcwd(), "names_daily.json")  # 하루치 이름 리스트

# ==============================
# 데이터 함수
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

def load_names():
    try:
        with open(NAME_FILE,"r") as f:
            return json.load(f)
    except:
        return []

def save_names(names):
    with open(NAME_FILE,"w") as f:
        json.dump(names,f,ensure_ascii=False, indent=4)

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

# ==============================
# 기록 입력 (온라인/대면)
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

    # 이름 리스트 업데이트 (매일 리셋)
    names = load_names()
    if update.message.from_user.first_name not in names:
        names.append(update.message.from_user.first_name)
        save_names(names)

    label = "온라인" if mode=="o" else "대면"
    update.message.reply_text(f"✅ 저장 완료 ({label})")

# ==============================
# 이름 리스트 보기 (5열씩)
# ==============================
def show_names(update, context):
    names = load_names()
    if not names:
        update.message.reply_text("등록된 이름이 없습니다")
        return
    msg = ""
    for i, n in enumerate(names):
        msg += n + " "
        if (i+1) % 5 == 0:
            msg += "\n"
    update.message.reply_text(msg)

# ==============================
# 팀별 조회 (조장용)
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
# 전체 조회 (관리자용)
# ==============================
def all_view(update, context):
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
    update.message.reply_text(msg)

# ==============================
# 메인
# ==============================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("봇 실행됨")))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("teamstats", team_stats))
    dp.add_handler(CommandHandler("allview", all_view))
    dp.add_handler(CommandHandler("names", show_names))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, record))

    updater.start_polling()
    updater.idle()

if __name__=="__main__":
    main()
