import random
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8391943092:AAHx2XPe7sMteKpBvb9PJEDyHMbovtVrJWY"

games = {}
active_chats = set()

UTC8 = timezone(timedelta(hours=8))


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


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎰 CASINO BOT\n\n"
        "/smart - 开始游戏\n"
        "/open - 立即开奖\n"
        "/stop - 停止游戏\n"
        "/help - 帮助\n\n"
        "下注方式：\n"
        "Tài / Xỉu"
    )


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    active_chats.add(chat_id)

    if chat_id in games:
        await update.message.reply_text("⚠️ Casino正在运行")
        return

    games[chat_id] = {
        "bets": {},
        "round": 0,
        "countdown": 60,
        "force_open": False,
        "manual": True
    }

    await update.message.reply_text("🎰 CASINO 已开启")

    context.application.create_task(game_loop(context, chat_id))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if chat_id in games:
        games.pop(chat_id)

        await update.message.reply_text("🛑 CASINO 已停止")


async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if chat_id in games:
        games[chat_id]["force_open"] = True

        await update.message.reply_text("⚡ 即将开奖")


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

    await update.message.reply_text(f"✅ {name} 已下注 {choice}")


async def game_loop(context: ContextTypes.DEFAULT_TYPE, chat_id):

    chat = await context.bot.get_chat(chat_id)
    private_mode = chat.type == "private"

    while chat_id in games:

        game = games[chat_id]

        if not game.get("manual",False):

            if not auto_time_allowed():

                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏰ Casino已关闭"
                )

                games.pop(chat_id)
                return


        game["round"] += 1
        game["bets"] = {}
        game["countdown"] = 60
        game["force_open"] = False


        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎲 第 {game['round']} 局\n\n开始下注"
        )


        while game["countdown"] > 0:

            if game["force_open"]:
                break

            if game["countdown"] % 10 == 0:

                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg.message_id,
                        text=f"🎲 第 {game['round']} 局\n\n⏳ 剩余 {game['countdown']} 秒"
                    )
                except:
                    pass

            await asyncio.sleep(1)

            game["countdown"] -= 1

            if chat_id not in games:
                return


        await context.bot.send_message(
            chat_id=chat_id,
            text="🔒 已封盘\n🎲 正在摇骰子..."
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
🎲 开奖结果

🎯 骰子: {d1} - {d2} - {d3}
🔢 总数: {total}
📢 结果: {result}
"""


        if winners:

            message += "\n🏆 赢家:\n"

            message += "\n".join(winners)


        await context.bot.send_message(chat_id=chat_id,text=message)


        await asyncio.sleep(8)


        # 私聊只运行一局
        if private_mode:

            games.pop(chat_id)

            return


async def auto_scheduler(context: ContextTypes.DEFAULT_TYPE):

    while True:

        for chat_id in list(active_chats):

            chat = await context.bot.get_chat(chat_id)

            # 私聊禁止自动
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
                        text="🎰 CASINO 自动开启"
                    )

                    context.application.create_task(
                        game_loop(context,chat_id)
                    )

            else:

                if chat_id in games and not games[chat_id].get("manual",False):

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏰ Casino时间结束"
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


    print("Bot casino running...")


    app.job_queue.run_once(auto_scheduler,5)


    app.run_polling()


if __name__ == "__main__":
    main()
