from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta

from config import STATIONS, DAYS_RU
import storage
from scheduler import generate_schedule
from renderer import render_schedule_image

router = Router()

# ─── FSM States ───────────────────────────────────────────────
class AddEmployee(StatesGroup):
    waiting_name = State()
    waiting_stations = State()

class CreateSchedule(StatesGroup):
    waiting_week_start = State()  # выбор даты начала недели
    waiting_days_off = State()    # собираем выходные для каждого сотрудника

# ─── /start ───────────────────────────────────────────────────
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Бот управления графиком работы</b>\n\n"
        "Команды:\n"
        "➕ /add_employee — добавить сотрудника\n"
        "👥 /employees — список сотрудников\n"
        "🗑 /remove_employee — удалить сотрудника\n"
        "📅 /create_schedule — создать график на неделю",
        parse_mode="HTML"
    )

# ─── Добавление сотрудника ────────────────────────────────────
@router.message(Command("add_employee"))
async def cmd_add_employee(message: Message, state: FSMContext):
    await state.set_state(AddEmployee.waiting_name)
    await message.answer("Введите имя сотрудника:")

@router.message(AddEmployee.waiting_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым, попробуйте снова:")
        return
    await state.update_data(name=name, selected_stations=[])
    await ask_stations(message, state, name)

async def ask_stations(message, state, name):
    await state.set_state(AddEmployee.waiting_stations)
    data = await state.get_data()
    selected = data.get("selected_stations", [])

    builder = InlineKeyboardBuilder()
    for s in STATIONS:
        mark = "✅ " if s in selected else ""
        builder.button(text=f"{mark}{s}", callback_data=f"toggle_station:{s}")
    builder.button(text="💾 Сохранить", callback_data="save_employee")
    builder.adjust(1)

    await message.answer(
        f"Выберите станции для <b>{name}</b> (можно несколько):",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(AddEmployee.waiting_stations, F.data.startswith("toggle_station:"))
async def toggle_station(callback: CallbackQuery, state: FSMContext):
    station = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_stations", [])

    if station in selected:
        selected.remove(station)
    else:
        selected.append(station)

    await state.update_data(selected_stations=selected)

    name = data["name"]
    builder = InlineKeyboardBuilder()
    for s in STATIONS:
        mark = "✅ " if s in selected else ""
        builder.button(text=f"{mark}{s}", callback_data=f"toggle_station:{s}")
    builder.button(text="💾 Сохранить", callback_data="save_employee")
    builder.adjust(1)

    await callback.message.edit_text(
        f"Выберите станции для <b>{name}</b>:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(AddEmployee.waiting_stations, F.data == "save_employee")
async def save_employee(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    selected = data.get("selected_stations", [])

    if not selected:
        await callback.answer("Выберите хотя бы одну станцию!", show_alert=True)
        return

    storage.add_employee(name, selected)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Сотрудник <b>{name}</b> добавлен.\nСтанции: {', '.join(selected)}",
        parse_mode="HTML"
    )
    await callback.answer()

# ─── Список сотрудников ───────────────────────────────────────
@router.message(Command("employees"))
async def cmd_employees(message: Message):
    employees = storage.get_employees()
    if not employees:
        await message.answer("Сотрудников пока нет. Добавьте через /add_employee")
        return

    lines = ["👥 <b>Сотрудники:</b>\n"]
    for name, stations in employees.items():
        lines.append(f"• <b>{name}</b> — {', '.join(stations)}")
    await message.answer("\n".join(lines), parse_mode="HTML")

# ─── Удаление сотрудника ──────────────────────────────────────
@router.message(Command("remove_employee"))
async def cmd_remove_employee(message: Message):
    employees = storage.get_employees()
    if not employees:
        await message.answer("Сотрудников нет.")
        return

    builder = InlineKeyboardBuilder()
    for name in employees:
        builder.button(text=f"🗑 {name}", callback_data=f"remove:{name}")
    builder.adjust(2)
    await message.answer("Кого удалить?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("remove:"))
async def do_remove(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]
    storage.remove_employee(name)
    await callback.message.edit_text(f"🗑 Сотрудник <b>{name}</b> удалён.", parse_mode="HTML")
    await callback.answer()

# ─── Создание графика ─────────────────────────────────────────
def get_next_monday() -> date:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)

@router.message(Command("create_schedule"))
async def cmd_create_schedule(message: Message, state: FSMContext):
    employees = storage.get_employees()
    if not employees:
        await message.answer("Сначала добавьте сотрудников через /add_employee")
        return

    next_monday = get_next_monday()
    label = f"📅 Ближайший понедельник — {next_monday.strftime('%d.%m.%Y')}"

    builder = InlineKeyboardBuilder()
    builder.button(text=label, callback_data=f"week_start:{next_monday.isoformat()}")
    builder.button(text="✏️ Ввести другую дату", callback_data="week_start:custom")
    builder.adjust(1)

    await state.set_state(CreateSchedule.waiting_week_start)
    await message.answer(
        "📅 <b>С какой даты начать неделю?</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(CreateSchedule.waiting_week_start, F.data.startswith("week_start:"))
async def choose_week_start(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]

    if value == "custom":
        await callback.message.edit_text(
            "Введите дату начала недели в формате <b>ДД.ММ.ГГГГ</b>:\n"
            "Например: <code>07.04.2025</code>",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    week_start = date.fromisoformat(value)
    await _start_days_off(callback.message, state, week_start, edit=True)
    await callback.answer()

@router.message(CreateSchedule.waiting_week_start)
async def process_custom_date(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        day, month, year = text.split(".")
        week_start = date(int(year), int(month), int(day))
    except Exception:
        await message.answer(
            "❌ Неверный формат. Введите дату как <b>ДД.ММ.ГГГГ</b>, например: <code>07.04.2025</code>",
            parse_mode="HTML"
        )
        return

    await _start_days_off(message, state, week_start, edit=False)

async def _start_days_off(message_or_obj, state: FSMContext, week_start: date, edit: bool):
    employees = storage.get_employees()
    days_off = {name: [] for name in employees}
    await state.set_state(CreateSchedule.waiting_days_off)
    await state.update_data(
        days_off=days_off,
        current_employee_idx=0,
        week_start=week_start.isoformat()
    )
    employee_names = list(employees.keys())
    await ask_days_off(message_or_obj, state, employee_names[0], edit=edit)

async def ask_days_off(message_or_callback, state: FSMContext, employee_name: str, edit=False):
    data = await state.get_data()
    days_off = data["days_off"]
    selected = days_off.get(employee_name, [])

    week_start = date.fromisoformat(data["week_start"])

    builder = InlineKeyboardBuilder()
    for i, day_ru in enumerate(DAYS_RU):
        day_date = week_start + timedelta(days=i)
        label = f"{day_date.day}.{day_date.month} {day_ru}"
        mark = "🔴 " if i in selected else ""
        builder.button(text=f"{mark}{label}", callback_data=f"toggle_day:{i}")
    builder.button(text="✅ Готово", callback_data="next_employee")
    builder.adjust(2)

    text = f"📅 <b>{employee_name}</b>\nОтметьте выходные дни (🔴 = выходной):"

    if edit:
        target_msg = message_or_callback.message if hasattr(message_or_callback, "message") else message_or_callback
        await target_msg.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(CreateSchedule.waiting_days_off, F.data.startswith("toggle_day:"))
async def toggle_day(callback: CallbackQuery, state: FSMContext):
    day_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    days_off = data["days_off"]
    employees = list(storage.get_employees().keys())
    current_idx = data["current_employee_idx"]
    current_name = employees[current_idx]

    offs = days_off.get(current_name, [])
    if day_idx in offs:
        offs.remove(day_idx)
    else:
        offs.append(day_idx)
    days_off[current_name] = offs
    await state.update_data(days_off=days_off)

    await ask_days_off(callback, state, current_name, edit=True)
    await callback.answer()

@router.callback_query(CreateSchedule.waiting_days_off, F.data == "next_employee")
async def next_employee(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    employees = list(storage.get_employees().keys())
    current_idx = data["current_employee_idx"]
    next_idx = current_idx + 1

    if next_idx < len(employees):
        await state.update_data(current_employee_idx=next_idx)
        await ask_days_off(callback, state, employees[next_idx], edit=True)
        await callback.answer()
    else:
        # Все сотрудники обработаны — генерируем график
        await callback.answer("Генерирую график...")
        await generate_and_send(callback.message, state)

async def generate_and_send(message: Message, state: FSMContext):
    data = await state.get_data()
    days_off = data["days_off"]
    employees = storage.get_employees()
    week_start = date.fromisoformat(data["week_start"])

    schedule = generate_schedule(employees, days_off)

    # Рендерим картинку
    img_path = render_schedule_image(schedule, week_start)

    # Отправляем
    from aiogram.types import FSInputFile
    photo = FSInputFile(img_path)
    
    week_end = week_start + timedelta(days=6)
    caption = (
        f"📅 <b>График на неделю</b>\n"
        f"{week_start.strftime('%d.%m')} – {week_end.strftime('%d.%m.%Y')}"
    )
    
    await message.answer_photo(photo, caption=caption, parse_mode="HTML")
    await state.clear()
