
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

# --- 일반 유저 명령어 ---
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        team = int(context.args[0])  # 조 번호
        name = context.args[1]       # 이름
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /register 1 홍길동")
        return

    # 데이터 저장
    user_data[user_id] = {
        'team': team,
        'name': name,
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

# --- 관리자 명령어 ---
async def allrecords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능")
        return

    team_stats = {}

    # 1️⃣ 유저 데이터 정리
    for uid, data in user_data.items():
        team = data.get('team')
        name = data.get('name')

        if team not in team_stats:
            team_stats[team] = {
                'members': [],
                '합계': {'말하기': 0, '쓰기': 0, '읽기': 0, '강의하기': 0}
            }

        # 개인 기록 추가
        team_stats[team]['members'].append({
            'name': name,
            '말하기': data['말하기'],
            '쓰기': data['쓰기'],
            '읽기': data['읽기'],
            '강의하기': data['강의하기']
        })

        # 합계 계산
        team_stats[team]['합계']['말하기'] += data['말하기']
        team_stats[team]['합계']['쓰기'] += data['쓰기']
        team_stats[team]['합계']['읽기'] += data['읽기']
        team_stats[team]['합계']['강의하기'] += data['강의하기']

    # 2️⃣ 메시지 만들기
    msg = "📊 조별 통계\n\n"

    for team, info in sorted(team_stats.items()):
        msg += f"{team}조\n"

        # 개인별 출력
        for member in info['members']:
            msg += (
                f"{member['name']}: "
                f"말하기 {member['말하기']} / "
                f"쓰기 {member['쓰기']} / "
                f"읽기 {member['읽기']} / "
                f"강의 {member['강의하기']}\n"
            )

        # 합계 출력
        total = info['합계']
        msg += (
            f"👉 합계\n"
            f"말하기: {total['말하기']} / "
            f"쓰기: {total['쓰기']} / "
            f"읽기: {total['읽기']} / "
            f"강의: {total['강의하기']}\n\n"
        )

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
app.add_handler(CommandHandler("allrecords", allrecords))
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
