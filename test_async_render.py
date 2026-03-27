# bot_env_final_clean.py
# python-telegram-bot v20+ 기준
# .env 환경변수 사용, async 모든 명령어 포함
# 서버 유지용 HTTP 핑 포함

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# ===== 🔹 .env 파일 읽기 =====
# .env 안에 BOT_TOKEN=xxx, GOOGLE_CREDS=경로/credentials.json 형태
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDS = os.environ.get("GOOGLE_CREDS")

if not BOT_TOKEN:
    raise ValueError("환경변수 BOT_TOKEN이 설정되지 않았습니다.")
if not GOOGLE_CREDS or not os.path.exists(GOOGLE_CREDS):
    raise FileNotFoundError(f"Google credentials 파일이 없습니다: {GOOGLE_CREDS}")

# ===== 🔥 구글 시트 연결 =====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# credentials.json 읽어서 gspread client 생성
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
client = gspread.authorize(creds)
sheet = client.open("출석봇").sheet1  # 🔹 시트 이름 지정

# ===== 🔹 사용자 기록 저장용 딕셔너리 =====
user_data = {}  # {user_id: {team, name, 지역, 날짜, 요일, 말하기, 쓰기, 읽기, 강의하기}}

# ===== 🔹 관리자 / 조장 ID =====
ADMIN_IDS = [419163029, 87654321]  # 실제 관리자 ID
TEAM_LEADERS = {1: 111111111, 2: 222222222, 4: 419163029}  # 실제 조장 ID

# ===== 🔹 시트 관련 함수 =====
def save_to_sheet(user_id, data):
    """새로운 사용자 기록을 시트에 추가"""
    sheet.append_row([
        user_id,
        data['team'],
        data['name'],
        data['지역'],
        data['날짜'],
        data['요일'],
        data['말하기'],
        data['쓰기'],
        data['읽기'],
        data['강의하기']
    ])

def find_user_row(user_id):
    """시트에서 사용자 행 찾기"""
    records = sheet.get_all_values()
    for i, row in enumerate(records):
        if str(row[0]) == str(user_id):
            return i + 1  # 시트는 1부터 시작
    return None

def update_sheet(user_id, data):
    """사용자 기록 업데이트"""
    row = find_user_row(user_id)
    if not row:
        return
    sheet.update(f"B{row}:J{row}", [[
        data['team'],
        data['name'],
        data['지역'],
        data['날짜'],
        data['요일'],
        data['말하기'],
        data['쓰기'],
        data['읽기'],
        data['강의하기']
    ]])

# ===== 🔹 일반 유저 명령어 =====
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자 등록 /register 팀번호 이름 지역"""
    user_id = update.effective_user.id
    if user_id in user_data:
        await update.message.reply_text("이미 등록되어 있습니다!")
        return

    if len(context.args) != 3:
        await update.message.reply_text(
            "사용법: /register 팀번호 이름 지역\n예) /register 1 홍길동 강남"
        )
        return

    try:
        team = int(context.args[0])
        name = context.args[1]
        region = context.args[2]
    except ValueError:
        await update.message.reply_text("팀번호는 숫자로 입력해주세요!\n예) /register 1 홍길동 강남")
        return

    # 🔹 현재 날짜 / 요일
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    weekday = ["월","화","수","목","금","토","일"][now.weekday()]

    # 🔹 사용자 데이터 저장
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

    # 🔥 시트 저장
    save_to_sheet(user_id, user_data[user_id])
    await update.message.reply_text(f"{team}조 {name} 등록 완료!")

async def speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """말하기 기록 추가"""
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
    update_sheet(user_id, user_data[user_id])
    team = user_data[user_id]['team']
    name = user_data[user_id]['name']
    await update.message.reply_text(f"{team}조 {name} 말하기 +{count}")

async def write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """쓰기 기록 추가"""
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
    update_sheet(user_id, user_data[user_id])
    team = user_data[user_id]['team']
    name = user_data[user_id]['name']
    await update.message.reply_text(f"{team}조 {name} 쓰기 +{count}")

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """읽기 기록 추가"""
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
    update_sheet(user_id, user_data[user_id])
    team = user_data[user_id]['team']
    name = user_data[user_id]['name']
    await update.message.reply_text(f"{team}조 {name} 읽기 +{count}")

async def lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """강의 기록 추가"""
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
    update_sheet(user_id, user_data[user_id])
    team = user_data[user_id]['team']
    name = user_data[user_id]['name']
    await update.message.reply_text(f"{team}조 {name} 강의 +{count}")

async def myrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """내 기록 조회"""
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

# ===== 🔹 조별 통계 / 관리자 명령어 =====
async def teamrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """조별 통계 조회 (관리자 전체 / 조장 자기 조)"""
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("/register 먼저 해주세요!")
        return

    is_admin = user_id in ADMIN_IDS
    user_team = user_data[user_id]['team']
    msg = "📊 조별 통계\n\n"

    if is_admin:
        teams = {}
        for data in user_data.values():
            team = data['team']
            teams.setdefault(team, []).append(data)
        for team, members in teams.items():
            msg += f"{team}조\n"
            for m in members:
                msg += f"  {m['name']} - {m['말하기']}/{m['쓰기']}/{m['읽기']}/{m['강의하기']}\n"
            msg += "\n"
    elif TEAM_LEADERS.get(user_team) == user_id:
        msg += f"{user_team}조\n"
        for data in user_data.values():
            if data['team'] == user_team:
                msg += f"  {data['name']} - {data['말하기']}/{data['쓰기']}/{data['읽기']}/{data['강의하기']}\n"
    else:
        await update.message.reply_text("조장만 조회 가능합니다!")
        return

    await update.message.reply_text(msg)

async def weeklystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """주간 상세 통계 (관리자용)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능")
        return

    stats = {}
    for data in user_data.values():
        key = f"{data.get('날짜','-')} | {data.get('요일','-')} | {data.get('지역','-')}"
        team = data['team']
        stats.setdefault(key, {})
        stats[key].setdefault(team, [])
        stats[key][team].append(data)

    msg = "📊 주간 상세 통계\n\n"
    for key, teams in stats.items():
        msg += f"📅 {key}\n"
        for team, members in teams.items():
            msg += f"  👥 {team}조\n"
            for m in members:
                msg += f"    - {m['name']}\n      말:{m['말하기']} 쓰:{m['쓰기']} 읽:{m['읽기']} 강:{m['강의하기']}\n"
        msg += "\n"

    await update.message.reply_text(msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """관리자 전용, 모든 기록 초기화"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능")
        return
    user_data.clear()
    await update.message.reply_text("모든 기록 초기화 완료!")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 테스트용"""
    await update.message.reply_text("봇 응답 정상!")

# ===== 🔹 Application 생성 및 핸들러 등록 =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

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

# 테스트용
app.add_handler(CommandHandler("test", test))

# ===== 🔹 봇 실행 + 서버 유지 =====
app.run_polling()

class Handler(BaseHTTPRequestHandler):
    """서버 유지용 HTTP GET 응답"""
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

# 🔹 서버 스레드로 실행
threading.Thread(target=run_server).start()
