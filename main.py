import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8773076449:AAFAPKtwdD0USTWGLL2Wdz5NaxbEVIZDL6E"
DB_PATH = "casino.db"
ADMIN_ID = 1954492027  # ТВІЙ ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    waiting_for_bet = State()
    waiting_for_promo = State()

# ========== БАЗА ДАНИХ ==========
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                promo_azart_used INTEGER DEFAULT 0,
                promo_winbo_used INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await db.execute("INSERT INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
            await db.commit()
            return 0.0
        return row[0]

async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def is_promo_used(user_id: int, promo_type: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        col = "promo_azart_used" if promo_type == "AZART" else "promo_winbo_used"
        cursor = await db.execute(f"SELECT {col} FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return bool(row and row[0])

async def set_promo_used(user_id: int, promo_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        col = "promo_azart_used" if promo_type == "AZART" else "promo_winbo_used"
        await db.execute(f"UPDATE users SET {col} = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def add_referral(user_id: int, referrer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referrals = referrals + 1, referred_by = ? WHERE user_id = ?",
            (referrer_id, user_id)
        )
        await db.commit()

# ========== ГРА ==========
def generate_crash_point() -> float:
    rand = random.random()
    if rand < 0.35:
        return round(random.uniform(1.00, 1.80), 2)
    elif rand < 0.60:
        return round(random.uniform(1.80, 3.00), 2)
    elif rand < 0.78:
        return round(random.uniform(3.00, 5.00), 2)
    elif rand < 0.90:
        return round(random.uniform(5.00, 12.00), 2)
    elif rand < 0.97:
        return round(random.uniform(12.00, 35.00), 2)
    else:
        return round(random.uniform(35.00, 100.00), 2)

active_games = {}

# ========== ГОЛОВНЕ МЕНЮ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != message.from_user.id:
                await add_referral(message.from_user.id, referrer_id)
                ref_balance = await get_balance(referrer_id)
                await update_balance(referrer_id, ref_balance + 100)
                try:
                    await bot.send_message(referrer_id, "🎉 За вашим посиланням приєднався новий гравець! Ви отримали 100 ₴!")
                except:
                    pass
        except:
            pass

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Грати")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💳 Поповнити")],
            [KeyboardButton(text="💸 Вивести"), KeyboardButton(text="👥 Реферали")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🚀 *WINBO CASINO*\n\n"
        "Грай в Crash Rocket та заробляй!\n"
        "Множник росте від x1 до x100!\n\n"
        "🎁 Промокод *WINBO* — +500 на баланс\n"
        "💰 Стартовий баланс: 0 (поповни через промокод)",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "💰 Баланс")
async def balance(message: types.Message):
    balance = await get_balance(message.from_user.id)
    await message.answer(f"💰 *Ваш баланс:* {balance:.2f} ₴", parse_mode="Markdown")

@dp.message(F.text == "💳 Поповнити")
async def deposit_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏦 З карти")],
            [KeyboardButton(text="🎁 Промокод")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer("💳 *ПОПОВНЕННЯ*\n\nОберіть спосіб:", reply_markup=keyboard, parse_mode="Markdown")

@dp.message(F.text == "🏦 З карти")
async def deposit_card(message: types.Message):
    await message.answer(
        "💳 *Поповнення з карти*\n\n"
        "НАПИШІТЬ НАШОМУ МЕНЕДЖЕРУ!\n"
        "https://t.me/dopo21",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🎁 Промокод")
async def promo_enter(message: types.Message, state: FSMContext):
    await state.set_state(GameState.waiting_for_promo)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True
    )
    await message.answer(
        "🎁 Введіть промокод:\n\n• *WINBO* — +500\n• *AZART* — +25",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(GameState.waiting_for_promo)
async def promo_activate(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()

    if code == "🔙 НАЗАД":
        await state.clear()
        await deposit_menu(message)
        return

    if code in ["AZART", "WINBO"]:
        user_id = message.from_user.id
        if await is_promo_used(user_id, code):
            await message.answer(f"❌ Промокод *{code}* вже використано!", parse_mode="Markdown")
            return

        bonus = 25 if code == "AZART" else 500
        balance = await get_balance(user_id)
        new_balance = balance + bonus
        await update_balance(user_id, new_balance)
        await set_promo_used(user_id, code)

        await state.clear()
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚀 Грати")],
                [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💳 Поповнити")],
                [KeyboardButton(text="💸 Вивести"), KeyboardButton(text="👥 Реферали")],
            ],
            resize_keyboard=True
        )
        await message.answer(
            f"🎁 *Промокод {code} активовано!*\n\n+{bonus} ₴\nБаланс: {new_balance:.2f} ₴",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Невірний промокод. Спробуйте *WINBO* або *AZART*", parse_mode="Markdown")

@dp.message(F.text == "💸 Вивести")
async def withdraw(message: types.Message):
    await message.answer(
        "💸 *Вивід коштів*\n\nНАПИШІТЬ НАШОМУ МЕНЕДЖЕРУ!\nhttps://t.me/dopo21",
        parse_mode="Markdown"
    )

@dp.message(F.text == "👥 Реферали")
async def referrals(message: types.Message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    await message.answer(
        f"👥 *РЕФЕРАЛЬНА СИСТЕМА*\n\nЗапроси друга — отримай 100 ₴!\n\n🔗 Твоє посилання:\n`{ref_link}`",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🔙 Назад")
async def back_to_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Грати")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💳 Поповнити")],
            [KeyboardButton(text="💸 Вивести"), KeyboardButton(text="👥 Реферали")],
        ],
        resize_keyboard=True
    )
    await message.answer("🚀 *WINBO CASINO*\nОбери дію:", reply_markup=keyboard, parse_mode="Markdown")

# ========== ГРА ==========
@dp.message(F.text == "🚀 Грати")
async def game_start(message: types.Message):
    balance = await get_balance(message.from_user.id)
    if balance <= 0:
        await message.answer(
            "❌ *Недостатньо коштів!*\nВикористайте промокод *WINBO* (+500) у розділі 💳 Поповнити → 🎁 Промокод",
            parse_mode="Markdown"
        )
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="100"), KeyboardButton(text="200"), KeyboardButton(text="500")],
            [KeyboardButton(text="1000"), KeyboardButton(text="5000")],
            [KeyboardButton(text="✍️ Своя ставка")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"🎯 *СТАВКА*\n\n💰 Баланс: {balance:.2f} ₴\nОбери суму:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "✍️ Своя ставка")
async def custom_bet_prompt(message: types.Message, state: FSMContext):
    await state.set_state(GameState.waiting_for_bet)
    await message.answer("💵 Введи свою ставку (мін. 10 ₴):", reply_markup=ReplyKeyboardRemove())

@dp.message(GameState.waiting_for_bet)
async def custom_bet_amount(message: types.Message, state: FSMContext):
    try:
        bet = int(message.text)
        if bet < 10:
            await message.answer("❌ Мінімальна ставка — 10 ₴.")
            return
        await state.clear()
        await run_game(message, bet)
    except ValueError:
        await message.answer("❌ Введи ціле число.")

@dp.message(F.text.in_(["100", "200", "500", "1000", "5000"]))
async def handle_bet(message: types.Message):
    await run_game(message, int(message.text))

async def run_game(message: types.Message, bet: int):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if bet > balance:
        await message.answer(f"❌ Недостатньо коштів!\nБаланс: {balance:.2f} ₴")
        return

    new_balance = balance - bet
    await update_balance(user_id, new_balance)

    crash_point = generate_crash_point()
    game_id = f"{user_id}_{message.message_id}"
    active_games[game_id] = {
        "cashed_out": False, "mult": 1.00, "bet": bet,
        "user_id": user_id, "crash": crash_point
    }

    game_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛑 ЗАБРАТИ")]],
        resize_keyboard=True
    )
    await message.answer("🎮 Кнопка «ЗАБРАТИ» активна!", reply_markup=game_keyboard)

    game_msg = await message.answer(
        f"🚀 *ПОЛІТ*\n\nСтавка: {bet} ₴\nМножник: x1.00\nВиграш: {bet:.2f} ₴",
        parse_mode="Markdown"
    )
    asyncio.create_task(flight_animation(game_id, game_msg, crash_point, bet, new_balance))

async def flight_animation(game_id, game_msg, crash_point, bet, new_balance):
    phases = [(15.0, 1.0, 2.0, 1.5), (7.0, 2.0, 10.0, 2.0), (5.0, 10.0, 100.0, 2.5)]
    for duration, start_m, end_m, power in phases:
        phase_start = asyncio.get_event_loop().time()
        while True:
            await asyncio.sleep(0.8)
            if game_id not in active_games or active_games[game_id]["cashed_out"]:
                return
            elapsed = asyncio.get_event_loop().time() - phase_start
            progress = min(elapsed / duration, 1.0)
            current_mult = round(start_m + (end_m - start_m) * (progress ** power), 2)
            if current_mult > crash_point:
                current_mult = crash_point
            if game_id in active_games:
                active_games[game_id]["mult"] = current_mult
            if current_mult >= crash_point:
                crash_mult = min(crash_point, current_mult)
                try:
                    await game_msg.delete()
                except:
                    pass
                retry_keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="100"), KeyboardButton(text="200"), KeyboardButton(text="500")],
                        [KeyboardButton(text="1000"), KeyboardButton(text="5000")],
                        [KeyboardButton(text="✍️ Своя ставка")],
                        [KeyboardButton(text="🔙 Назад")],
                    ],
                    resize_keyboard=True
                )
                await bot.send_message(
                    chat_id=game_msg.chat.id,
                    text=f"💥 *БАБАХ!*\n\nРакетка вибухнула на x{crash_mult:.2f}\nСтавка: {bet} ₴ втрачена\nБаланс: {new_balance:.2f} ₴",
                    reply_markup=retry_keyboard, parse_mode="Markdown"
                )
                if game_id in active_games:
                    del active_games[game_id]
                return
            try:
                await game_msg.edit_text(
                    f"🚀 *ПОЛІТ*\n\nСтавка: {bet} ₴\nМножник: x{current_mult:.2f}\nВиграш: {bet * current_mult:.2f} ₴",
                    parse_mode="Markdown"
                )
            except:
                pass
            if progress >= 1.0:
                break

@dp.message(F.text == "🛑 ЗАБРАТИ")
async def cashout_button(message: types.Message):
    user_id = message.from_user.id
    game_id = None
    for gid, game in list(active_games.items()):
        if game["user_id"] == user_id and not game["cashed_out"]:
            game_id = gid
            break
    if not game_id:
        await message.answer("❌ Немає активної гри!")
        return

    game = active_games[game_id]
    game["cashed_out"] = True
    current_mult, bet = game["mult"], game["bet"]
    balance = await get_balance(user_id)
    win_amount = round(bet * current_mult, 2)
    new_balance = balance + win_amount
    await update_balance(user_id, new_balance)

    retry_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="100"), KeyboardButton(text="200"), KeyboardButton(text="500")],
            [KeyboardButton(text="1000"), KeyboardButton(text="5000")],
            [KeyboardButton(text="✍️ Своя ставка")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"🎉 *ЗАБРАНО!*\n\nСтавка: {bet} ₴\nМножник: x{current_mult:.2f}\nВиграш: {win_amount:.2f} ₴\nБаланс: {new_balance:.2f} ₴",
        reply_markup=retry_keyboard, parse_mode="Markdown"
    )
    if game_id in active_games:
        del active_games[game_id]

# ========== АДМІН-КОМАНДИ ==========
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "🔐 *АДМІН-ПАНЕЛЬ*\n\n"
        "`/addbalance ID СУМА` — додати баланс\n"
        "`/setbalance ID СУМА` — встановити баланс\n"
        "`/getuser ID` — інфа про юзера\n"
        "`/broadcast ТЕКСТ` — розсилка\n"
        "`/users` — кількість юзерів\n"
        "`/top` — топ-10 по балансу",
        parse_mode="Markdown"
    )

@dp.message(Command("addbalance"))
async def admin_add_balance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id, amount = int(parts[1]), float(parts[2])
        balance = await get_balance(user_id)
        new_balance = balance + amount
        await update_balance(user_id, new_balance)
        await message.answer(f"✅ Баланс `{user_id}`: +{amount} ₴ → {new_balance:.2f} ₴", parse_mode="Markdown")
        try:
            await bot.send_message(user_id, f"💰 *Поповнення!*\n+{amount} ₴\nБаланс: {new_balance:.2f} ₴", parse_mode="Markdown")
        except:
            pass
    except:
        await message.answer("❌ `/addbalance ID СУМА`")

@dp.message(Command("setbalance"))
async def admin_set_balance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id, amount = int(parts[1]), float(parts[2])
        await update_balance(user_id, amount)
        await message.answer(f"✅ Баланс `{user_id}` = {amount:.2f} ₴", parse_mode="Markdown")
    except:
        await message.answer("❌ `/setbalance ID СУМА`")

@dp.message(Command("getuser"))
async def admin_get_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text.split()[1])
        balance = await get_balance(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
        if row:
            await message.answer(
                f"👤 `{user_id}`\n💰 {balance:.2f} ₴\nAZART: {'так' if row[2] else 'ні'}\nWINBO: {'так' if row[3] else 'ні'}\n👥 Рефералів: {row[4]}",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Не знайдено")
    except:
        await message.answer("❌ `/getuser ID`")

@dp.message(Command("users"))
async def admin_users_count(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = (await cursor.fetchone())[0]
    await message.answer(f"👥 Юзерів: {count}")

@dp.message(Command("top"))
async def admin_top(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
        rows = await cursor.fetchall()
    text = "🏆 *ТОП-10*\n\n" + "\n".join(f"{i}. `{uid}` — {bal:.2f} ₴" for i, (uid, bal) in enumerate(rows, 1))
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def admin_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("❌ `/broadcast ТЕКСТ`")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 {text}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ Розсилка: {sent}/{len(users)}")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())