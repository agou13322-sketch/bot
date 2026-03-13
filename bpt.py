import random
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8391943092:AAHx2XPe7sMteKpBvb9PJEDyHMbovtVrJWY"

GROUP_FILE = "groups.json"

games = {}

UTC8 = timezone(timedelta(hours=8))


def load_groups():
    if os.path.exists(GROUP_FILE):
        with open(GROUP_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_groups():
    with open(GROUP_FILE, "w") as f:
        json.dump(list(active_chats), f)


active_chats = load_groups()


def roll_dice():
    return random.randint(1,6), random.randint(1,6), random.randint(1,6)


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


async def is_admin(update, context):

    chat = update.effective_chat

    if chat.type == "private":
        return True

    member = await context.bot.get_chat_member(chat.id, update.effective_user.id)

    return member.status in ["administrator","creator"]


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    active_chats.add(chat_id)
    save_groups()

    await update.message.reply_text(
        "🎰 BOT CASINO TÀI XỈU\n\n"
        "/smart - Mở bàn casino\n"
        "/open - Mở kết quả ngay\n"
        "/stop - Dừng casino\n"
        "/help - Trợ giúp"
    )


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if not await is_admin(update,context):
        await update.message.reply_text("❌ Chỉ admin mới được mở casino")
        return

    active_chats.add(chat_id)
    save_groups()

    if chat_id in games:
        await update.message.reply_text("⚠️ Casino đang hoạt động")
        return

    games[chat_id] = {
        "bets": {},
        "round": 0,
        "countdown": 60,
        "force_open": False,
        "manual": True
    }

    await update.message.reply_text("🎰 CASINO ĐÃ MỞ")

    context.application.create_task(game_loop(context, chat_id))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if not await is_admin(update,context):
        await update.message.reply_text("❌ Chỉ admin mới được dừng casino")
        return

    if chat_id in games:
        games.pop(chat_id)

        await update.message.reply_text("🛑 CASINO ĐÃ DỪNG")


async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if not await is_admin(update,context):
        await update.message.reply_text("❌ Chỉ admin mới được mở kết quả")
        return

    if chat_id in games:
        games[chat_id]["force_open"] = True

        await update.message.reply_text("⚡ Sắp mở kết quả")


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if chat_id not in games:
        return

    text = update.message.text.lower()

    if text not in ["tài","xỉu","tai","xiu"]:
        return

    user_id = update.effective_user.id
    name = update.effective_user.first_name

    choice = "Tài" if text in ["tài","tai"] else "Xỉu"

    games[chat_id]["bets"][user_id] = (name,choice)

    await update.message.reply_text(f"✅ {name} cược {choice}")


async def game_loop(context: ContextTypes.DEFAULT_TYPE, chat_id):

    chat = await context.bot.get_chat(chat_id)

    private_mode = chat.type == "private"

    while chat_id in games:

        game = games[chat_id]

        if not game.get("manual",False):

            if not auto_time_allowed():

                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏰ Casino đã đóng"
                )

                games.pop(chat_id)
                return


        game["round"] += 1
        game["bets"] = {}
        game["countdown"] = 60
        game["force_open"] = False


        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎲 BÀN #{game['round']}\n\n⏳ Còn 60 giây"
        )


        while game["countdown"] > 0:

            if game["force_open"]:
                break

            if game["countdown"] % 10 == 0:

                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg.message_id,
                        text=f"🎲 BÀN #{game['round']}\n\n⏳ Còn {game['countdown']} giây"
                    )
                except:
                    pass

            await asyncio.sleep(1)

            game["countdown"] -= 1

            if chat_id not in games:
                return


        await context.bot.send_message(
            chat_id=chat_id,
            text="🔒 ĐÃ KHÓA CƯỢC\n🎲 Đang lắc..."
        )

        await asyncio.sleep(2)


        d1,d2,d3 = roll_dice()

        total = d1 + d2 + d3

        result = get_result(total)


        winners = []

        for uid,(name,choice) in game["bets"].items():

            if choice == result:
                winners.append(name)


        message = f"""
🎲 KẾT QUẢ

🎯 Xúc xắc: {d1} - {d2} - {d3}
🔢 Tổng: {total}
📢 Kết quả: {result}
"""


        if winners:

            message += "\n🏆 Người thắng:\n"

            message += "\n".join(winners)


        await context.bot.send_message(chat_id=chat_id,text=message)


        await asyncio.sleep(8)


        if private_mode:

            games.pop(chat_id)

            return


async def auto_scheduler(context: ContextTypes.DEFAULT_TYPE):

    while True:

        for chat_id in list(active_chats):

            chat = await context.bot.get_chat(chat_id)

            if chat.type == "private":
                continue


            if auto_time_allowed():

                if chat_id not in games:

                    games[chat_id] = {
                        "bets": {},
                        "round": 0,
                        "countdown": 60,
                        "force_open": False,
                        "manual": False
                    }

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🎰 CASINO TỰ ĐỘNG MỞ"
                    )

                    context.application.create_task(
                        game_loop(context,chat_id)
                    )

            else:

                if chat_id in games and not games[chat_id].get("manual",False):

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏰ HẾT GIỜ CASINO"
                    )

                    games.pop(chat_id)


        await asyncio.sleep(60)


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("smart",smart))
    app.add_handler(CommandHandler("help",help))
    app.add_handler(CommandHandler("open",open_now))
    app.add_handler(CommandHandler("stop",stop))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,bet))

    print("Casino bot running...")

    app.job_queue.run_once(auto_scheduler,5)

    app.run_polling()


if __name__ == "__main__":
    main()
