import random
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8391943092:AAHx2XPe7sMteKpBvb9PJEDyHMbovtVrJWY"

games = {}

UTC8 = timezone(timedelta(hours=8))


def roll_dice():
    return random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)


def get_result(total):
    return "Tài" if total >= 11 else "Xỉu"


def auto_time_allowed():
    now = datetime.now(UTC8)
    hour = now.hour

    if 3 <= hour < 4:
        return True

    if 22 <= hour <= 23:
        return True

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎰 BOT CASINO TÀI XỈU\n\n"
        "/smart - Mở bàn casino\n"
        "/stop - Dừng casino\n"
        "/open - Mở kết quả ngay"
    )


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in games:
        await update.message.reply_text("⚠️ Casino đang chạy.")
        return

    games[chat_id] = {
        "running": True,
        "bets": {},
        "round": 0,
        "countdown": 60,
        "force_open": False,
        "manual": True
    }

    await update.message.reply_text("🎰 CASINO ĐÃ MỞ (Manual)")

    context.application.create_task(game_loop(context, chat_id))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in games:
        games.pop(chat_id)
        await update.message.reply_text("🛑 CASINO ĐÃ DỪNG")


async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in games:
        games[chat_id]["force_open"] = True
        await update.message.reply_text("⚡ SẮP MỞ KẾT QUẢ")


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in games:
        return

    text = update.message.text.lower()

    if text not in ["tài", "xỉu", "tai", "xiu"]:
        return

    user_id = update.effective_user.id
    name = update.effective_user.first_name

    choice = "Tài" if text in ["tài", "tai"] else "Xỉu"

    games[chat_id]["bets"][user_id] = (name, choice)

    await update.message.reply_text(f"✅ {name} đã cược {choice}")


async def game_loop(context: ContextTypes.DEFAULT_TYPE, chat_id):

    while chat_id in games:

        game = games[chat_id]

        if not game.get("manual", False):
            if not auto_time_allowed():
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏰ Ngoài giờ hoạt động, casino tự động đóng."
                )
                games.pop(chat_id)
                return

        game["round"] += 1
        game["bets"] = {}
        game["countdown"] = 60
        game["force_open"] = False

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎲 BÀN #{game['round']}\n\nBắt đầu đặt cược"
        )

        while game["countdown"] > 0:

            if game["force_open"]:
                break

            if game["countdown"] % 10 == 0:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.message_id,
                    text=f"🎲 BÀN #{game['round']}\n\n⏳ Còn {game['countdown']} giây để cược"
                )

            await asyncio.sleep(1)
            game["countdown"] -= 1

            if chat_id not in games:
                return

        await context.bot.send_message(
            chat_id=chat_id,
            text="🔒 ĐÃ KHÓA CƯỢC\nĐang lắc xúc xắc..."
        )

        await asyncio.sleep(2)

        d1, d2, d3 = roll_dice()
        total = d1 + d2 + d3
        result = get_result(total)

        winners = []

        for uid, (name, choice) in game["bets"].items():
            if choice == result:
                winners.append(name)

        message = f"""
🎲 KẾT QUẢ

Kết quả: {result}
"""

        if winners:
            message += "\n🏆 NGƯỜI THẮNG:\n"
            message += "\n".join(winners)

        await context.bot.send_message(chat_id=chat_id, text=message)

        await asyncio.sleep(8)


async def auto_scheduler(context: ContextTypes.DEFAULT_TYPE):

    while True:

        for chat_id in list(games.keys()):

            game = games[chat_id]

            if not game.get("manual", False):

                if not auto_time_allowed():

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏰ Hết giờ casino."
                    )

                    games.pop(chat_id)

        await asyncio.sleep(60)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("smart", smart))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("open", open_now))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet))

    print("Bot casino đang chạy...")

    app.job_queue.run_repeating(auto_scheduler, interval=60, first=10)

    app.run_polling()


if __name__ == "__main__":
    main()
