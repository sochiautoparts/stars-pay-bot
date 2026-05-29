"""StarsPay Bot Handlers — Telegram Stars payment processing."""
import time
import uuid
import logging
import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, WebAppInfo,
)
from aiogram.filters import Command, CommandStart
# Stars currency is "XTR" string (not in aiogram Currency enum)
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)
router = Router()


# ─── Helper: Build keyboards ───

def projects_keyboard() -> InlineKeyboardMarkup:
    """Main menu with project selection."""
    buttons = []
    for proj_id, proj in config.products.items():
        buttons.append([InlineKeyboardButton(
            text=f"📦 {proj['name']}",
            callback_data=f"project:{proj_id}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔑 Мои лицензии",
        callback_data="my_licenses"
    )])
    buttons.append([InlineKeyboardButton(
        text="👥 Реферальная программа",
        callback_data="referral"
    )])
    buttons.append([InlineKeyboardButton(
        text="🌐 Открыть магазин",
        web_app=WebAppInfo(url=config.miniapp_url)
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def plans_keyboard(project_id: str) -> InlineKeyboardMarkup:
    """Subscription plans for a project."""
    project = config.products.get(project_id)
    if not project:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")
        ]])

    buttons = []
    for plan_id, plan in project["plans"].items():
        buttons.append([InlineKeyboardButton(
            text=f"💰 {plan['label']} — {plan['price']} ⭐",
            callback_data=f"buy:{project_id}:{plan_id}"
        )])
    buttons.append([InlineKeyboardButton(
        text="◀️ Назад", callback_data="back_main"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── /start command ───

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command with optional referral code."""
    args = message.text.split(maxsplit=1)
    ref_code = args[1] if len(args) > 1 else None

    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.language_code or "ru"
    )

    # Process referral
    if ref_code and ref_code != user.get("referral_code"):
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT user_id FROM users WHERE referral_code = ?", (ref_code,)
            )
            referrer = await cursor.fetchone()
            if referrer and referrer[0] != message.from_user.id:
                await db.set_referral(referrer[0], message.from_user.id)

    # Check if start parameter is a buy command
    if ref_code and ref_code.startswith("buy_"):
        parts = ref_code.split("_")
        if len(parts) >= 3:
            project_id = parts[1]
            plan_id = parts[2]
            await _send_invoice(message, project_id, plan_id)
            return

    text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"💎 **StarsPay** — универсальная оплата Telegram Stars\n\n"
        f"Выберите проект для покупки подписки:"
    )
    await message.answer(text, reply_markup=projects_keyboard(), parse_mode="Markdown")


# ─── Project selection ───

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 Выберите проект:",
        reply_markup=projects_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("project:"))
async def cb_project(callback: CallbackQuery):
    project_id = callback.data.split(":")[1]
    project = config.products.get(project_id)
    if not project:
        await callback.answer("Проект не найден", show_alert=True)
        return

    text = (
        f"📦 **{project['name']}**\n\n"
        f"📝 {project['description']}\n\n"
        f"Выберите тариф:"
    )
    await callback.message.edit_text(text, reply_markup=plans_keyboard(project_id), parse_mode="Markdown")
    await callback.answer()


# ─── Purchase flow ───

@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery, bot: Bot):
    """Initiate purchase — send invoice with Stars."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка", show_alert=True)
        return

    project_id, plan_id = parts[1], parts[2]
    project = config.products.get(project_id)
    if not project:
        await callback.answer("Проект не найден", show_alert=True)
        return

    plan = project["plans"].get(plan_id)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    # Check if user already has active license
    check = await db.check_user_license(callback.from_user.id, project_id)
    if check.get("has_license"):
        await callback.answer("У вас уже есть активная подписка!", show_alert=True)
        return

    # Send invoice
    prices = [LabeledPrice(label=plan["label"], amount=plan["price"])]
    payload = f"{project_id}:{plan_id}"

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"{project['name']} — {plan['label']}",
        description=project["description"],
        prices=prices,
        provider_token="",  # Stars payments: empty string
        payload=payload,
        currency="XTR",  # Telegram Stars currency
        start_parameter=f"sp_{project_id}_{plan_id}",
    )
    await callback.answer()


async def _send_invoice(message_or_callback, project_id: str, plan_id: str, bot: Bot = None):
    """Send invoice for a purchase."""
    project = config.products.get(project_id)
    if not project:
        return
    plan = project["plans"].get(plan_id)
    if not plan:
        return

    prices = [LabeledPrice(label=plan["label"], amount=plan["price"])]
    payload = f"{project_id}:{plan_id}"
    chat_id = message_or_callback.from_user.id

    from aiogram import Bot as AiogramBot
    if bot is None:
        bot = AiogramBot(token=config.bot_token)

    await bot.send_invoice(
        chat_id=chat_id,
        title=f"{project['name']} — {plan['label']}",
        description=project["description"],
        prices=prices,
        provider_token="",
        payload=payload,
        currency="XTR",  # Telegram Stars currency
        start_parameter=f"sp_{project_id}_{plan_id}",
    )


# ─── Pre-checkout ───

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    """Confirm pre-checkout query."""
    # Validate payload
    payload = query.invoice_payload
    parts = payload.split(":")
    if len(parts) != 2:
        await query.answer(ok=False, error_message="Ошибка: неверные данные заказа")
        return

    project_id, plan_id = parts
    project = config.products.get(project_id)
    if not project or plan_id not in project["plans"]:
        await query.answer(ok=False, error_message="Ошибка: проект или тариф не найден")
        return

    await query.answer(ok=True)


# ─── Successful payment ───

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    """Handle successful Stars payment."""
    payment = message.successful_payment
    payload = payment.invoice_payload
    parts = payload.split(":")
    if len(parts) != 2:
        return

    project_id, plan_id = parts
    project = config.products.get(project_id)
    if not project:
        return
    plan = project["plans"].get(plan_id)
    if not plan:
        return

    # Calculate expiration
    now = time.time()
    if plan["days"] > 0:
        expires_at = now + (plan["days"] * 86400)
    else:
        expires_at = 0  # Lifetime

    # Create license
    license_key = await db.create_license(
        user_id=message.from_user.id,
        project=project_id,
        plan=plan_id,
        expires_at=expires_at,
    )

    # Record payment
    await db.record_payment(
        user_id=message.from_user.id,
        project=project_id,
        plan=plan_id,
        stars=plan["price"],
        tg_charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id or "",
        license_key=license_key,
    )

    # Process referral bonus
    user = await db.get_or_create_user(message.from_user.id)
    referrer_id = user.get("referred_by")
    if referrer_id:
        # Give bonus stars to referrer (tracked, actual transfer done manually or via bot API)
        await db.set_referral(referrer_id, message.from_user.id)

    # Send license key
    expires_text = (
        f"🔄 Истекает: <code>{time.strftime('%d.%m.%Y', time.localtime(expires_at))}</code>"
        if expires_at > 0
        else "♾ Бессрочная лицензия"
    )

    text = (
        f"✅ Оплата прошла успешно!\n\n"
        f"📦 Проект: <b>{project['name']}</b>\n"
        f"📋 Тариф: <b>{plan['label']}</b>\n"
        f"🔑 Лицензионный ключ:\n<code>{license_key}</code>\n\n"
        f"{expires_text}\n\n"
        f"💡 Используйте этот ключ для активации в проекте.\n"
        f"🔑 Ключ также доступен в разделе «Мои лицензии»"
    )
    await message.answer(text, parse_mode="HTML")


# ─── My licenses ───

@router.callback_query(F.data == "my_licenses")
async def cb_my_licenses(callback: CallbackQuery):
    """Show user's licenses."""
    user = await db.get_or_create_user(callback.from_user.id)
    licenses = await db.check_user_licenses(callback.from_user.id)

    if not licenses:
        text = "🔑 У вас пока нет активных лицензий.\n\nКупите подписку в разделе «Выбрать проект»"
    else:
        lines = ["🔑 **Ваши лицензии:**\n"]
        for lic in licenses:
            project = config.products.get(lic["project"], {})
            project_name = project.get("name", lic["project"])
            plan_info = project.get("plans", {}).get(lic["plan"], {})
            plan_label = plan_info.get("label", lic["plan"])

            if lic["expires_at"] > 0:
                exp = time.strftime("%d.%m.%Y", time.localtime(lic["expires_at"]))
                exp_text = f"до {exp}"
            else:
                exp_text = "бессрочно"

            lines.append(f"• **{project_name}** ({plan_label}) — {exp_text}")
            lines.append(f"  Ключ: `{lic['key']}`\n")

        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")
    ]])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# ─── Referral system ───

@router.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    """Show referral info."""
    user = await db.get_or_create_user(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)

    ref_code = user.get("referral_code", "N/A")
    ref_link = f"https://t.me/allstarspay_bot?start={ref_code}"

    text = (
        f"👥 **Реферальная программа**\n\n"
        f"🔗 Ваша ссылка:\n`{ref_link}`\n\n"
        f"📊 Приглашено: **{stats['referrals']}** пользователей\n"
        f"💎 Бонус: {config.referral_bonus_stars} ⭐ за каждого\n\n"
        f"Отправьте ссылку друзьям — получите звёзды!"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# ─── Admin commands ───

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin statistics."""
    if message.from_user.id not in config.admin_ids:
        return

    stats = await db.get_admin_stats()

    text = (
        f"👑 **StarsPay Admin**\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"🔑 Активных лицензий: {stats['active_licenses']}\n"
        f"⭐ Всего звёзд: {stats['total_stars']}\n\n"
    )
    if stats["by_project"]:
        text += "📊 По проектам:\n"
        for proj, count in stats["by_project"].items():
            name = config.products.get(proj, {}).get("name", proj)
            text += f"  • {name}: {count}\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("addproject"))
async def cmd_addproject(message: Message):
    """Add a new project. Format: /addproject id|Name|Description|prefix"""
    if message.from_user.id not in config.admin_ids:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Формат: `/addproject id|Название|Описание|PREFIX`",
            parse_mode="Markdown"
        )
        return

    parts = args[1].split("|")
    if len(parts) < 4:
        await message.answer("Нужно 4 параметра: id|Название|Описание|PREFIX")
        return

    proj_id, name, description, prefix = [p.strip() for p in parts]
    config.products[proj_id] = {
        "name": name,
        "description": description,
        "plans": {},
        "prefix": prefix,
    }
    await message.answer(f"✅ Проект «{name}» добавлен (id: {proj_id})")


@router.message(Command("addplan"))
async def cmd_addplan(message: Message):
    """Add plan to project. Format: /addplan project_id|plan_id|label|price|days"""
    if message.from_user.id not in config.admin_ids:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: `/addplan project|plan|Название|цена|дни`", parse_mode="Markdown")
        return

    parts = args[1].split("|")
    if len(parts) < 5:
        await message.answer("Нужно 5 параметров: project|plan|Название|цена|дни")
        return

    proj_id, plan_id, label = parts[0].strip(), parts[1].strip(), parts[2].strip()
    price, days = int(parts[3]), int(parts[4])

    if proj_id not in config.products:
        await message.answer(f"Проект {proj_id} не найден")
        return

    config.products[proj_id]["plans"][plan_id] = {
        "price": price,
        "label": label,
        "days": days,
    }
    await message.answer(f"✅ Тариф «{label}» добавлен в {config.products[proj_id]['name']}")


@router.message(Command("genkey"))
async def cmd_genkey(message: Message):
    """Generate a license key manually. Format: /genkey project_id|plan_id|user_id"""
    if message.from_user.id not in config.admin_ids:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: `/genkey project|plan|user_id`", parse_mode="Markdown")
        return

    parts = args[1].split("|")
    if len(parts) < 3:
        await message.answer("Нужно: project|plan|user_id")
        return

    project_id, plan_id = parts[0].strip(), parts[1].strip()
    target_user_id = int(parts[2].strip())

    project = config.products.get(project_id)
    if not project:
        await message.answer(f"Проект {project_id} не найден")
        return
    plan = project["plans"].get(plan_id)
    if not plan:
        await message.answer(f"Тариф {plan_id} не найден")
        return

    now = time.time()
    expires_at = now + (plan["days"] * 86400) if plan["days"] > 0 else 0

    key = await db.create_license(target_user_id, project_id, plan_id, expires_at)
    await message.answer(f"✅ Ключ создан: `{key}`", parse_mode="Markdown")


@router.message(Command("addapikey"))
async def cmd_addapikey(message: Message):
    """Add API key for external project. Format: /addapikey project_id|description"""
    if message.from_user.id not in config.admin_ids:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: `/addapikey project|описание`", parse_mode="Markdown")
        return

    parts = args[1].split("|")
    project_id = parts[0].strip()
    description = parts[1].strip() if len(parts) > 1 else ""

    key = f"sk_{uuid.uuid4().hex[:24]}"
    await db.add_api_key(key, project_id, description)
    await message.answer(
        f"✅ API ключ для **{project_id}**:\n`{key}`",
        parse_mode="Markdown"
    )


# ─── Check user licenses helper ───

async def check_user_licenses_db(user_id: int) -> list:
    """Get all active licenses for a user."""
    licenses = []
    for proj_id in config.products:
        result = await db.check_user_license(user_id, proj_id)
        if result.get("has_license"):
            licenses.append(result["license"])
    return licenses


# Patch the database method
db.check_user_licenses = check_user_licenses_db
