
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
    user_data.setdefault(user_id, {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0})
    await update.message.reply_text("출석 등록 완료!")

async def speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /speak <횟수>")
        return
    user_data.setdefault(user_id, {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0})
    user_data[user_id]['말하기'] += count
    await update.message.reply_text(f"말하기 기록 +{count}")

async def write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /write <횟수>")
        return
    user_data.setdefault(user_id, {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0})
    user_data[user_id]['쓰기'] += count
    await update.message.reply_text(f"쓰기 기록 +{count}")

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /read <횟수>")
        return
    user_data.setdefault(user_id, {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0})
    user_data[user_id]['읽기'] += count
    await update.message.reply_text(f"읽기 기록 +{count}")

async def lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        count = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("사용법: /lecture <횟수>")
        return
    user_data.setdefault(user_id, {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0})
    user_data[user_id]['강의하기'] += count
    await update.message.reply_text(f"강의하기 기록 +{count}")

async def myrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    record = user_data.get(user_id, {'말하기':0, '쓰기':0, '읽기':0, '강의하기':0})
    msg = f"📊 당신 기록:\n말하기: {record['말하기']}\n쓰기: {record['쓰기']}\n읽기: {record['읽기']}\n강의하기: {record['강의하기']}"
    await update.message.reply_text(msg)

# --- 관리자 명령어 ---
async def allrecords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능")
        return
    msg = "📊 전체 기록:\n"
    for uid, rec in user_data.items():
        msg += f"{uid}: {rec}\n"
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
