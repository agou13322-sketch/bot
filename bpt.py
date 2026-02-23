import random
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8391943092:AAHx2XPe7sMteKpBvb9PJEDyHMbovtVrJWY"

games = {}


def roll_dice():
    return random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)


def get_result(total):
    return "Tài" if total >= 11 else "Xỉu"


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
        await update.message.reply_text("⚠️ Casino đã đang chạy.")
        return

    games[chat_id] = {
        "running": True,
        "bets": {},
        "round": 0,
        "countdown": 60,
        "force_open": False
    }

    await update.message.reply_text("🎰 CASINO ĐÃ MỞ")

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

        await context.bot.send_message(chat_id=chat_id, text="🔒 ĐÃ KHÓA CƯỢC\nĐang lắc xúc xắc...")

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

🎯 {d1} | {d2} | {d3}
Tổng: {total}

Kết quả: {result}
"""

        if winners:
            message += "\n🏆 NGƯỜI THẮNG:\n"
            message += "\n".join(winners)
        else:
            message += "\nKhông có người thắng."

        await context.bot.send_message(chat_id=chat_id, text=message)

        await asyncio.sleep(8)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("smart", smart))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("open", open_now))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet))

    print("Bot casino đang chạy...")
    app.run_polling()


if __name__ == "__main__":

    main()
