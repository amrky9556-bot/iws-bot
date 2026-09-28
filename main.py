import asyncio
import random
from datetime import datetime, timedelta
import aiosqlite

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
MAIN_BOT_TOKEN = "8832916717:AAFPgUThMSZuI1qGpjJehSgvAMNz2Xh_35o"
CHANNEL_USERNAME = "IWs_Source"       # معرف القناة بدون @
LEGENDARY_DEV_ID = 7551922713         # المطور الأسطوري
DISABLE_CODE = "AS22nnj0bbiit"        # كود التعطيل السري

DB_NAME = "iws_system_war.db"

# ==========================================
# 2. قواعد البيانات الشاملة (اقتصاد + حرب)
# ==========================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS created_bots (
                token TEXT PRIMARY KEY,
                owner_id INTEGER,
                expire_date TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        # جدول الاقتصاد والأصول الحربية
        await db.execute('''
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER PRIMARY KEY,
                vault_type TEXT,
                coins INTEGER DEFAULT 0,
                last_salary TEXT,
                shield INTEGER DEFAULT 0,
                soldiers INTEGER DEFAULT 0,
                tanks INTEGER DEFAULT 0,
                planes INTEGER DEFAULT 0,
                bombs INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS group_roles (
                chat_id INTEGER,
                user_id INTEGER,
                role TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS custom_replies (
                chat_id INTEGER,
                trigger TEXT,
                response TEXT,
                PRIMARY KEY (chat_id, trigger)
            )
        ''')
        await db.commit()

# ==========================================
# 3. مساعدات الرتب
# ==========================================
ROLE_HIERARCHY = {
    "المطور الاسطوري": 7,
    "مالك اساسي": 6,
    "مالك": 5,
    "منشئ": 4,
    "مدير": 3,
    "ادمن": 2,
    "مميز": 1,
    "عضو": 0
}

async def get_user_role(chat_id: int, user_id: int) -> str:
    if user_id == LEGENDARY_DEV_ID:
        return "المطور الاسطوري"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT role FROM group_roles WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "عضو"

async def set_user_role(chat_id: int, user_id: int, role: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO group_roles (chat_id, user_id, role) VALUES (?, ?, ?)", (chat_id, user_id, role))
        await db.commit()

# ==========================================
# 4. معالجة النظام الحربي والاقتصادي
# ==========================================
WAR_ITEMS = {
    "جندي": {"price": 10, "power": 1, "col": "soldiers"},
    "دبابة": {"price": 100, "power": 12, "col": "tanks"},
    "طائرة": {"price": 500, "power": 65, "col": "planes"},
    "قنبلة": {"price": 250, "power": 30, "col": "bombs"},
    "درع": {"price": 300, "power": 0, "col": "shield"}
}

async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()
    reply_to = update.message.reply_to_message

    user_role = await get_user_role(chat_id, user_id)
    user_level = ROLE_HIERARCHY.get(user_role, 0)

    # 1. تفعيل البوت
    if text in ["تفعيل البوت", "تفعيل"]:
        await set_user_role(chat_id, user_id, "مالك اساسي")
        chat_link = await context.bot.export_chat_invite_link(chat_id) if update.effective_chat.username is None else f"https://t.me/{update.effective_chat.username}"
        await update.message.reply_text(
            f"شكرا على تفعيل عزيزي المالك @{update.effective_user.username or user_id}\n"
            f"تم رفعك تلقائي كمالك اساسي\n"
            f"رابط القروب: {chat_link}"
        )
        return

    # 2. الخزينة والأوامر الاقتصادية
    if text in ["فلوسي", "خزينه"]:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT vault_type, coins FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await update.message.reply_text(
                        "اختر خزينه للبدء:\n\n"
                        "`خزينه سورلوث 🏦`\n"
                        "`خزينه محمداي`\n"
                        "`خزينه كورزذوس`",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(f"💰 رصيدك الحالي في {row[0]}: **{row[1]} كوينز**.")
        return

    if text in ["خزينه سورلوث 🏦", "خزينه محمداي", "خزينه كورزذوس"]:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT OR REPLACE INTO economy (user_id, vault_type, coins, last_salary, shield, soldiers, tanks, planes, bombs) VALUES (?, ?, 111, '', 0, 0, 0, 0, 0)", (user_id, text))
            await db.commit()
        await update.message.reply_text("تم تحويل 111 كوينز لحسابك للاستثمار والبدء!")
        return

    # 3. طرق جمع الكوينز
    if text == "راتبي":
        today = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT coins, last_salary FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await update.message.reply_text("⚠️ يجب عليك اختيار خزينة أولاً بواسطة كتابة `خزينه`.")
                    return
                if row[1] == today:
                    await update.message.reply_text("❌ لقد استلمت راتبك اليومي بالفعل! عد غداً.")
                    return
                
                reward = random.randint(50, 200)
                new_coins = row[0] + reward
                await db.execute("UPDATE economy SET coins = ?, last_salary = ? WHERE user_id = ?", (new_coins, today, user_id))
                await db.commit()
                await update.message.reply_text(f"💵 تم استلام راتبك اليومي بنجاح: **+{reward} كوينز**!\nرصيدك الآن: {new_coins} كوينز.")
        return

    if text == "حفر":
        found = random.randint(5, 40)
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT coins FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    new_coins = row[0] + found
                    await db.execute("UPDATE economy SET coins = ? WHERE user_id = ?", (new_coins, user_id))
                    await db.commit()
                    await update.message.reply_text(f"⛏️ قمت بالحفر ووجدت **{found} كوينز**!")
        return

    # 4. المتجر والمتجر الحربي
    if text in ["المتجر", "متجر الحرب"]:
        await update.message.reply_text(
            "🛒 **متجر الأسلحة والعتاد الحربي:**\n"
            "───────────────\n"
            "• `شراء جندي` 🥊 - السعر: 10 كوينز\n"
            "• `شراء دبابة` 🚜 - السعر: 100 كوينز\n"
            "• `شراء قنبلة` 💣 - السعر: 250 كوينز\n"
            "• `شراء طائرة` ✈️ - السعر: 500 كوينز\n"
            "• `شراء درع` 🛡️ - السعر: 300 كوينز (حماية من الهجوم)\n"
            "───────────────\n"
            "💡 للإنشاء والشراء ارسل الأمر كما هو أعلاه.",
            parse_mode="Markdown"
        )
        return

    if text.startswith("شراء "):
        item_name = text.replace("شراء ", "").strip()
        if item_name not in WAR_ITEMS:
            await update.message.reply_text("❌ العنصر غير موجود في المتجر! اكتب `متجر الحرب` لعرض العناصر.")
            return

        info = WAR_ITEMS[item_name]
        price = info["price"]
        col = info["col"]

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT coins, " + col + " FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row or row[0] < price:
                    await update.message.reply_text(f"❌ رصيدك غير كافٍ! تحتاج إلى **{price} كوينز**.")
                    return
                
                new_coins = row[0] - price
                new_count = row[1] + 1
                await db.execute(f"UPDATE economy SET coins = ?, {col} = ? WHERE user_id = ?", (new_coins, new_count, user_id))
                await db.commit()
                await update.message.reply_text(f"✅ تم شراء **{item_name}** بنجاح!\nالمتبقي من رصيدك: {new_coins} كوينز.")
        return

    # 5. عرض الجيش وقوة العتاد
    if text in ["جيشي", "الجيش"]:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT soldiers, tanks, planes, bombs, shield FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await update.message.reply_text("⚠️ ليس لديك جيش بعد! انشئ خزينة واشترِ من `متجر الحرب`.")
                    return
                
                total_power = (row[0]*1) + (row[1]*12) + (row[2]*65) + (row[3]*30)
                await update.message.reply_text(
                    f"⚔️ **قواتك وعتادك العسكري:**\n\n"
                    f"🥊 **جنود:** {row[0]}\n"
                    f"🚜 **دبابات:** {row[1]}\n"
                    f"✈️ **طائرات:** {row[2]}\n"
                    f"💣 **قنابل:** {row[3]}\n"
                    f"🛡️ **حالة الدرع:** {'مفعل' if row[4] > 0 else 'غير مفعل'}\n"
                    f"───────────────\n"
                    f"🔥 **القوة العسكرية الإجمالية:** {total_power}",
                    parse_mode="Markdown"
                )
        return

    # 6. الهجوم والحروب بين الأعضاء
    if text == "هجوم" and reply_to:
        target_id = reply_to.from_user.id
        if target_id == user_id:
            await update.message.reply_text("❌ لا يمكنك الهجوم على نفسك!")
            return

        async with aiosqlite.connect(DB_NAME) as db:
            # جلب قوة المهاجم
            async with db.execute("SELECT coins, soldiers, tanks, planes, bombs FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                attacker = await cursor.fetchone()
            # جلب قوة المدافع
            async with db.execute("SELECT coins, soldiers, tanks, planes, bombs, shield FROM economy WHERE user_id = ?", (target_id,)) as cursor:
                defender = await cursor.fetchone()

            if not attacker or not defender:
                await update.message.reply_text("⚠️ يجب أن يملك الطرفان خزينة وجيش للبدء بالمعركة!")
                return

            if defender[5] > 0: # مفعل درع
                await db.execute("UPDATE economy SET shield = 0 WHERE user_id = ?", (target_id,))
                await db.commit()
                await update.message.reply_text(f"🛡️ تصدى الدرع الخاص بـ @{reply_to.from_user.username or target_id} للهجوم وتم تحطيمه!")
                return

            att_power = (attacker[1]*1) + (attacker[2]*12) + (attacker[3]*65) + (attacker[4]*30)
            def_power = (defender[1]*1) + (defender[2]*12) + (defender[3]*65) + (defender[4]*30)

            if att_power > def_power:
                stolen = min(defender[0], random.randint(30, 100))
                await db.execute("UPDATE economy SET coins = coins + ? WHERE user_id = ?", (stolen, user_id))
                await db.execute("UPDATE economy SET coins = coins - ? WHERE user_id = ?", (stolen, target_id))
                await db.commit()
                await update.message.reply_text(f"🚀 **انتصار ساحق!**\nقمت بالهجوم على @{reply_to.from_user.username or target_id} ونهبت منه **{stolen} كوينز**!")
            else:
                await update.message.reply_text(f"🛡️ **خسرت المعركة!** دفاعات @{reply_to.from_user.username or target_id} كانت أقوى من قواتك.")
        return

    # 7. تحويل الكوينز بين الأعضاء
    if text.startswith("تحويل ") and reply_to:
        amount_str = text.replace("تحويل ", "").strip()
        if amount_str.isdigit():
            amount = int(amount_str)
            target_id = reply_to.from_user.id
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT coins FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row or row[0] < amount:
                        await update.message.reply_text("❌ ليس لديك كوينز كافية للتحويل!")
                        return
                
                await db.execute("UPDATE economy SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
                await db.execute("INSERT OR IGNORE INTO economy (user_id, coins) VALUES (?, 0)", (target_id,))
                await db.execute("UPDATE economy SET coins = coins + ? WHERE user_id = ?", (amount, target_id))
                await db.commit()
                await update.message.reply_text(f"💸 تم تحويل **{amount} كوينز** بنجاح إلى @{reply_to.from_user.username or target_id}.")
        return

    # 8. الاستثمار في المجالات
    if text.startswith("استثمار "):
        field = text.replace("استثمار ", "")
        profit = random.randint(-20, 50)
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT coins FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    new_balance = max(0, row[0] + profit)
                    await db.execute("UPDATE economy SET coins = ? WHERE user_id = ?", (new_balance, user_id))
                    await db.commit()
                    msg = f"📈 استثمرت في {field} وربحت {profit} كوينز!" if profit >= 0 else f"📉 استثمرت في {field} وخسرت {abs(profit)} كوينز!"
                    await update.message.reply_text(f"{msg}\nرصيدك الجديد: **{new_balance} كوينز**.")
        return

# ==========================================
# 5. تشغيل النظام
# ==========================================
async def main():
    await init_db()
    print("⚡ تم تشغيل النظام الحربي والاقتصادي بالسورس بنجاح!")

    app = Application.builder().token(MAIN_BOT_TOKEN).connect_timeout(60.0).read_timeout(60.0).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
