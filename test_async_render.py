
# bot_async.py
# python-telegram-bot v20+ 기준
# 모든 명령어 async 처리, 메시지 출력 정상화
# 주석 포함

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 사용자 기록 저장용 딕셔너리 예시 ---
user_data = {}  # {user_id: {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0}}

# --- 관리자 ID 리스트 ---
ADMIN_IDS = [419163029, 87654321]  # 실제 관리자 텔레그램 ID 넣기

# --- 조장 ID 리스트 ---
TEAM_LEADERS = {
    1: 111111111,
    2: 222222222,
    4: 419163029
} #실제 조장 텔레그램 ID 넣기

# --- 일반 유저 명령어 ---
# ===== register =====
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🔥 이미 등록된 경우
    if user_id in user_data:
        await update.message.reply_text("이미 등록되어 있습니다!")
        return

    try:
        team = int(context.args[0])
        name = context.args[1]
        region = context.args[2]  # 🔥 지역 추가
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /register 1 홍길동 강남")
        return

    # 🔥 날짜 / 요일 자동 생성
    from datetime import datetime
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    weekday = ["월","화","수","목","금","토","일"][now.weekday()]

    user_data[user_id] = {
        'team': team,
        'name': name,
        '지역': region,
        '날짜': date,
        '요일': weekday,
        '말하기': 0,
        '쓰기': 0,
        '읽기': 0,
        '강의하기': 0
    }

    await update.message.reply_text(f"{team}조 {name} 등록 완료!")

async def speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /speak 2")
        return

    user_data[user_id]['말하기'] += count

    team = user_data[user_id]['team']
    name = user_data[user_id]['name']

    await update.message.reply_text(f"{team}조 {name} 말하기 +{count}")

async def write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /write 2")
        return

    user_data[user_id]['쓰기'] += count

    team = user_data[user_id]['team']
    name = user_data[user_id]['name']

    await update.message.reply_text(f"{team}조 {name} 쓰기 +{count}")

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /read 2")
        return

    user_data[user_id]['읽기'] += count

    team = user_data[user_id]['team']
    name = user_data[user_id]['name']

    await update.message.reply_text(f"{team}조 {name} 읽기 +{count}")

async def lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /lecture 1")
        return

    user_data[user_id]['강의하기'] += count

    team = user_data[user_id]['team']
    name = user_data[user_id]['name']

    await update.message.reply_text(f"{team}조 {name} 강의 +{count}")

async def myrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    data = user_data[user_id]

    msg = (
        f"📊 {data['team']}조 {data['name']} 기록\n"
        f"말하기: {data['말하기']}\n"
        f"쓰기: {data['쓰기']}\n"
        f"읽기: {data['읽기']}\n"
        f"강의하기: {data['강의하기']}"
    )

    await update.message.reply_text(msg)

# 📊 조별 통계 (관리자 전체 / 조장 자기 조)

async def teamrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🔥 타입 맞춤 (int 그대로 사용)
    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    is_admin = user_id in ADMIN_IDS
    user_team = user_data[user_id]['team']

    msg = "📊 조별 통계\n\n"

    # 👑 관리자
    if is_admin:
        teams = {}

        for data in user_data.values():
            team = data['team']
            teams.setdefault(team, []).append(data)

        for team, members in teams.items():
            msg += f"{team}조\n"
            for m in members:
                msg += (
                    f"  {m['name']} - "
                    f"{m['말하기']}/{m['쓰기']}/{m['읽기']}/{m['강의하기']}\n"
                )
            msg += "\n"

    # 👑 조장
    elif TEAM_LEADERS.get(user_team) == user_id:
        msg += f"{user_team}조\n"
        for data in user_data.values():
            if data['team'] == user_team:
                msg += (
                    f"  {data['name']} - "
                    f"{data['말하기']}/{data['쓰기']}/{data['읽기']}/{data['강의하기']}\n"
                )

    else:
        await update.message.reply_text("조장만 조회 가능합니다!")
        return

    await update.message.reply_text(msg)
    
# --- 관리자 명령어 ---
async def weeklystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🔐 관리자 체크
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능")
        return

    stats = {}

    # 🔁 데이터 정리
    for data in user_data.values():
        key = f"{data.get('날짜','-')} | {data.get('요일','-')} | {data.get('지역','-')}"
        team = data['team']

        stats.setdefault(key, {})
        stats[key].setdefault(team, [])

        stats[key][team].append(data)

    # 📊 출력
    msg = "📊 주간 상세 통계\n\n"

    for key, teams in stats.items():
        msg += f"📅 {key}\n"

        for team, members in teams.items():
            msg += f"  👥 {team}조\n"

            for m in members:
                msg += (
                    f"    - {m['name']}\n"
                    f"      말:{m['말하기']} 쓰:{m['쓰기']} 읽:{m['읽기']} 강:{m['강의하기']}\n"
                )

        msg += "\n"

    await update.message.reply_text(msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능")
        return
    user_data.clear()
    await update.message.reply_text("모든 기록 초기화 완료!")

# --- 테스트용 명령어 ---
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("봇 응답 정상!")

# --- Application 생성 및 핸들러 등록 ---
app = ApplicationBuilder().token("8696444829:AAFtF11zvHF_kNM1P9XTufw-iI9ofXD3_0o").build()

# 일반 유저 명령어
app.add_handler(CommandHandler("register", register))
app.add_handler(CommandHandler("speak", speak))
app.add_handler(CommandHandler("write", write))
app.add_handler(CommandHandler("read", read))
app.add_handler(CommandHandler("lecture", lecture))
app.add_handler(CommandHandler("myrecord", myrecord))

# 관리자 명령어
app.add_handler(CommandHandler("teamrecord", teamrecord))
app.add_handler(CommandHandler("weeklystats", weeklystats))
app.add_handler(CommandHandler("reset", reset))

# 테스트
app.add_handler(CommandHandler("test", test))

# --- 봇 실행 ---
app.run_polling()


import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()
