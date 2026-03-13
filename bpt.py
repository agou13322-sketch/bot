import random
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8391943092:AAHx2XPe7sMteKpBvb9PJEDyHMbovtVrJWY"
GROUP_ID = -1003325553073

UTC8 = timezone(timedelta(hours=8))

game_running = False
round_number = 0


def roll_dice():
    return random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)


def get_result(total):
    return "Tài" if total >= 11 else "Xỉu"


def auto_time_allowed():

    now = datetime.now(UTC8)
    hour = now.hour

    if 15 <= hour < 16:
        return True

    if 22 <= hour < 24:
        return True

    return False


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global game_running

    if update.effective_chat.id != GROUP_ID:
        return

    if not game_running:
        return

    text = update.message.text.lower()

    if text not in ["tài", "xỉu", "tai", "xiu"]:
        return

    name = update.effective_user.first_name
    choice = "Tài" if text in ["tài", "tai"] else "Xỉu"

    await update.message.reply_text(f"✅ {name} đã cược {choice}")


async def game_loop(context: ContextTypes.DEFAULT_TYPE):

    global game_running
    global round_number

    while game_running:

        round_number += 1
        countdown = 60

        msg = await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🎲 BÀN #{round_number}\n\n⏳ Còn {countdown} giây để cược"
        )

        while countdown > 0 and game_running:

            await asyncio.sleep(1)
            countdown -= 1

            if countdown % 10 == 0:

                try:
                    await context.bot.edit_message_text(
                        chat_id=GROUP_ID,
                        message_id=msg.message_id,
                        text=f"🎲 BÀN #{round_number}\n\n⏳ Còn {countdown} giây để cược"
                    )
                except:
                    pass

        if not game_running:
            break

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="🔒 ĐÃ KHÓA CƯỢC\nĐang lắc xúc xắc..."
        )

        await asyncio.sleep(2)

        d1, d2, d3 = roll_dice()
        total = d1 + d2 + d3
        result = get_result(total)

        message = f"""
🎲 KẾT QUẢ

🎯 Xúc xắc: {d1} - {d2} - {d3}
🔢 Tổng: {total}
📢 Kết quả: {result}
"""

        await context.bot.send_message(chat_id=GROUP_ID, text=message)

        await asyncio.sleep(8)


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global game_running

    if update.effective_chat.id != GROUP_ID:
        return

    if game_running:
        await update.message.reply_text("⚠️ Casino đang chạy.")
        return

    game_running = True

    await update.message.reply_text("🎰 CASINO ĐÃ MỞ (Manual)")

    context.application.create_task(game_loop(context))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global game_running

    if update.effective_chat.id != GROUP_ID:
        return

    if not game_running:
        await update.message.reply_text("⚠️ Casino chưa chạy.")
        return

    game_running = False

    await update.message.reply_text("🛑 CASINO ĐÃ DỪNG")


async def scheduler(context: ContextTypes.DEFAULT_TYPE):

    global game_running

    if auto_time_allowed():

        if not game_running:

            game_running = True

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text="🎰 CASINO TỰ ĐỘNG MỞ"
            )

            context.application.create_task(game_loop(context))

    else:

        if game_running:

            game_running = False

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text="⏰ CASINO ĐÃ ĐÓNG"
            )


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("smart", smart))
    app.add_handler(CommandHandler("stop", stop))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet))

    app.job_queue.run_repeating(
        scheduler,
        interval=60,
        first=5
    )

    print("Bot casino đang chạy...")

    app.run_polling()


if __name__ == "__main__":
    main()
