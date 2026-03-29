import os, json
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ==============================
# 환경 변수
# ==============================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x]
LEADER_IDS = [int(x) for x in os.getenv("LEADER_IDS","").split(",") if x]
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))
DATA_FILE = os.path.join(os.getcwd(), "data.json")
NAMES_FILE = os.path.join(os.getcwd(), "names.txt")

# ==============================
# 데이터 처리
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
# 이름 파일 처리 (온라인/오프라인 섹션)
# ==============================
def reset_names_file():
    if not os.path.exists(NAMES_FILE):
        with open(NAMES_FILE,"w",encoding="utf-8") as f:
            f.write("[Online Users]\n\n[Offline Users]\n\n")

def add_name_to_file(mode, name):
    reset_names_file()
    section = "[Online Users]" if mode=="o" else "[Offline Users]"

    with open(NAMES_FILE,"r",encoding="utf-8") as f:
        lines = f.readlines()

    # 섹션 시작 인덱스 찾기
    try:
        idx = lines.index(section+"\n") + 1
    except ValueError:
        lines.append(section+"\n")
        idx = len(lines)

    # 섹션 안의 기존 이름 가져오기
    section_names = []
    i = idx
    while i < len(lines) and not lines[i].startswith("[") and lines[i].strip():
        section_names += lines[i].strip().split()
        i += 1

    if name in section_names:  # 섹션 내 중복 방지
        return

    section_names.append(name)

    # 5개씩 끊어서 작성
    new_lines = []
    for i in range(0,len(section_names),5):
        new_lines.append("\t".join(section_names[i:i+5]) + "\n")

    lines[idx:i] = new_lines

    with open(NAMES_FILE,"w",encoding="utf-8") as f:
        f.writelines(lines)

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
# 기록 입력 (온라인/오프라인)
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
        values = list(map(int,val.split("/")))
        if len(values)!=4: raise Exception
    except:
        await update.message.reply_text("o 10/2/1/0 형식으로 입력해주세요")
        return

    cats = ["말하기","쓰기","읽기","강의"]
    day = get_day()
    data.setdefault("records", {})
    data["records"].setdefault(uid, {})
    data["records"][uid].setdefault(day, {})
    key = "online" if mode=="o" else "offline"
    data["records"][uid][day][key] = dict(zip(cats,values))
    save_data(data)

    # 이름 파일에 추가
    name = data["names"][uid]
    add_name_to_file(mode,name)

    await update.message.reply_text(f"✅ 저장 완료 ({'온라인' if mode=='o' else '대면'})")

# ==============================
# 조장 조회 (하루치)
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
# 관리자 전체 조회 (하루치)
# ==============================
async def all_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS: return
    if not is_allowed(update): return
    data = load_data()
    teams = {}
    names_today = []

    for uid, team in data.get("users", {}).items():
        name = data["names"][uid]
        rec = data.get("records", {}).get(uid, {}).get(get_day(), {})
        teams.setdefault(team, []).append((name, rec))
        names_today.append(name)

    # names.txt 저장 (5열씩)
    with open(NAMES_FILE,"w",encoding="utf-8") as f:
        for i, name in enumerate(names_today):
            f.write(name)
            if (i+1)%5==0:
                f.write("\n")
            else:
                f.write(" ")
        f.write("\n")

    # 메시지 작성
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
    await update.message.reply_text(msg)

# ==============================
# 메인 실행
# ==============================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("teamstats", team_stats))
    app.add_handler(CommandHandler("allview", all_view))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record))
    app.run_polling()  # Termux 환경에 맞게 asyncio 루프 자동 처리

if __name__ == "__main__":
    main()
