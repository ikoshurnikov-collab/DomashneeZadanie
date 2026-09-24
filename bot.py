import ast
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta

import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

BOT_TOKEN = "8856676116:AAFaydzhS9EGQ2WS-vPnzpuwKLeq8XDgq0o"
DATA_URL = "https://journal.school28-kirov.ru/act/GET_STUDENT_DAIRY"

USER_IDS = [134892480, 10083432]

STUDENTS = {
    "Кирилла": {
        "student_id": "5201",
        "cls_id": "1073",
        "cookie": "ys-userId=n%3A6260; ys-user=s%3A%u041A%u043E%u0448%u0443%u0440%u043D%u0438%u043A%u043E%u0432; ys-password=s%3A253a2b69242b3f68978ba08ccce989b9575fc27e",
        "cache_file": "hw_cache_kirill.json",
        "grades_cache_file": "grades_cache_kirill.json",
        "schedule": {
            0: [406, 2, 5, 1, 13, 579],
            1: [2, 5, 1, 8, 12],
            2: [1, 5, 8, 10, 3],
            3: [81, 5, 1, 2, 12],
            4: [2, 1, 11, 3, 400, 414, 411]
        },
        "allowed_teachers": {
            3: 4233
        }
    },
    "Никиты": {
        "student_id": "4722",
        "cls_id": "1088",
        "cookie": "ys-userId=n%3A4184; ys-user=s%3A%u041A%u043E%u0448%u0443%u0440%u043D%u0438%u043A%u043E%u0432; ys-password=s%3A0f4db6388746b33422d5ced1af1b979273a40257",
        "cache_file": "hw_cache_nikita.json",
        "grades_cache_file": "grades_cache_nikita.json",
        "schedule": {
            0: [406, 5, 1, 414, 2, 13],
            1: [5, 1, 2, 10, 3],
            2: [12, 2, 5, 1, 8, 579],
            3: [3, 5, 1, 81, 411],
            4: [1, 12, 8, 2, 11]
        },
        "allowed_teachers": {}
    }
}

SUBJECTS = {
    1: "Русский язык",
    2: "Литературное чтение",
    3: "Иностранный язык",
    5: "Математика",
    8: "Окружающий мир",
    10: "Музыка",
    11: "Изобразительное искусство",
    12: "Физическая культура",
    13: "Труд (технология)",
    81: "Информатика и ИКТ",
    400: "Основы религиозных культур и светской этики",
    406: "Разговоры о важном",
    411: "Функциональная грамотность",
    414: "Робототехника",
    579: "Орлята России"
}

# --- Состояния и клавиатуры ---
class GradesState(StatesGroup):
    choosing_action = State()
    waiting_for_start = State()
    waiting_for_end = State()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="ДЗ Кирилла"), KeyboardButton(text="ДЗ Никиты")],
        [KeyboardButton(text="Оценки Кирилла"), KeyboardButton(text="Оценки Никиты")]
    ],
    resize_keyboard=True
)

grades_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отчет за неделю"), KeyboardButton(text="Выбранный период")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

back_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Назад")]],
    resize_keyboard=True
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_next_lesson_date(subject_id: int, current_date: datetime, schedule: dict) -> str:
    current_weekday = current_date.weekday()
    for i in range(1, 15):
        next_date = current_date + timedelta(days=i)
        next_weekday = next_date.weekday()
        if next_weekday in schedule and subject_id in schedule[next_weekday]:
            return next_date.strftime("%d.%m.%Y")
    return "Дата неизвестна"

def validate_date(date_text: str):
    try:
        return datetime.strptime(date_text, "%d.%m.%Y").strftime("%d.%m.%Y")
    except ValueError:
        return None

def fetch_data(student_name: str, start_dt_str: str = None, end_dt_str: str = None):
    student_data = STUDENTS[student_name]
    
    if not start_dt_str or not end_dt_str:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_dt_str = start_of_week.strftime("%d.%m.%Y")
        end_dt_str = end_of_week.strftime("%d.%m.%Y")

    payload_data = {
        "pClassesIds": "",
        "student": student_data["student_id"],
        "cls": student_data["cls_id"],
        "begin_dt": start_dt_str,
        "end_dt": end_dt_str
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": student_data["cookie"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = requests.post(DATA_URL, data=payload_data, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        logging.error(f"Сетевая ошибка ({student_name}): {e}")
        return None
    
    clean_text = re.sub(r'new Date\((.*?)\)', r'"\1"', response.text)
    clean_text = clean_text.replace('\n', ' ').replace('\r', '')
    clean_text = re.sub(r',\s*]', ']', clean_text)
    
    try:
        lessons = json.loads(clean_text, strict=False)
    except json.JSONDecodeError:
        try:
            eval_text = re.sub(r'\bnull\b', 'None', clean_text)
            eval_text = re.sub(r'\btrue\b', 'True', eval_text)
            eval_text = re.sub(r'\bfalse\b', 'False', eval_text)
            lessons = ast.literal_eval(eval_text)
        except Exception as e:
            logging.error(f"Ошибка парсинга ({student_name}): {e}")
            return None

    current_hw = {}
    current_grades = {}
    
    for lesson in lessons:
        date_str_parts = lesson[0].split(",")
        if len(date_str_parts) >= 3:
            year = int(date_str_parts[0])
            month = int(date_str_parts[1]) + 1
            day = int(date_str_parts[2])
            lesson_date = datetime(year, month, day)
        else:
            continue

        subject_id = lesson[2]
        homework = lesson[4] if len(lesson) > 4 else None
        grade = lesson[5] if len(lesson) > 5 else None
        teacher_id = lesson[9] if len(lesson) > 9 else None
        
        allowed_teachers = student_data.get("allowed_teachers", {})
        safe_allowed = {str(k): str(v) for k, v in allowed_teachers.items()}
        str_subj = str(subject_id)
        
        if str_subj in safe_allowed:
            if str(teacher_id) != safe_allowed[str_subj]:
                continue
                
        subj_name = SUBJECTS.get(subject_id, f"Предмет {subject_id}")
        hw_key = f"{lesson_date.strftime('%Y-%m-%d')}_{subject_id}"
        
        if homework and str(homework).strip():
            next_date = get_next_lesson_date(subject_id, lesson_date, student_data["schedule"])
            current_hw[hw_key] = {
                "given_date": lesson_date.strftime("%d.%m.%Y"),
                "due_date": next_date,
                "subject": subj_name,
                "text": str(homework).strip()
            }
            
        if grade and str(grade).strip():
            if hw_key in current_grades:
                current_grades[hw_key]["grade"] += f" / {str(grade).strip()}"
            else:
                current_grades[hw_key] = {
                    "date": lesson_date.strftime("%d.%m.%Y"),
                    "subject": subj_name,
                    "grade": str(grade).strip()
                }
            
    return current_hw, current_grades

def get_new_updates(student_name: str):
    data = fetch_data(student_name)
    if data is None: return [], []
        
    current_hw, current_grades = data
    student_data = STUDENTS[student_name]

    hw_cache_file = student_data["cache_file"]
    if os.path.exists(hw_cache_file):
        with open(hw_cache_file, "r", encoding="utf-8") as f:
            try: cached_hw = json.load(f)
            except json.JSONDecodeError: cached_hw = {}
    else: cached_hw = {}

    gr_cache_file = student_data["grades_cache_file"]
    if os.path.exists(gr_cache_file):
        with open(gr_cache_file, "r", encoding="utf-8") as f:
            try: cached_grades = json.load(f)
            except json.JSONDecodeError: cached_grades = {}
    else: cached_grades = {}

    new_hw = []
    for hw_key, hw_data in current_hw.items():
        if hw_key not in cached_hw or cached_hw[hw_key]["text"] != hw_data["text"]:
            new_hw.append(hw_data)

    new_grades = []
    for gr_key, gr_data in current_grades.items():
        if gr_key not in cached_grades or cached_grades[gr_key]["grade"] != gr_data["grade"]:
            new_grades.append(gr_data)

    if new_hw:
        with open(hw_cache_file, "w", encoding="utf-8") as f:
            json.dump(current_hw, f, ensure_ascii=False, indent=4)
            
    if new_grades:
        with open(gr_cache_file, "w", encoding="utf-8") as f:
            json.dump(current_grades, f, ensure_ascii=False, indent=4)

    return new_hw, new_grades

def format_hw_message(entries, title):
    if not entries: return ""
    grouped = {}
    for entry in entries:
        d_date = entry["due_date"]
        if d_date not in grouped: grouped[d_date] = []
        grouped[d_date].append(entry)
        
    def parse_date(d):
        try: return datetime.strptime(d, "%d.%m.%Y")
        except ValueError: return datetime.max
        
    sorted_dates = sorted(grouped.keys(), key=parse_date)
    msg = f"{title}\n\n"
    for d_date in sorted_dates:
        msg += f"<b>На {d_date}:</b>\n"
        for item in grouped[d_date]:
            msg += f"- {item['subject']}:\n{item['text']}\n\n"
    return msg.strip()

def format_grades_message(entries, title):
    if not entries: return ""
    grouped = {}
    for entry in entries:
        d_date = entry["date"]
        if d_date not in grouped: grouped[d_date] = []
        grouped[d_date].append(entry)
        
    def parse_date(d):
        try: return datetime.strptime(d, "%d.%m.%Y")
        except ValueError: return datetime.max
        
    sorted_dates = sorted(grouped.keys(), key=parse_date)
    msg = f"{title}\n\n"
    for d_date in sorted_dates:
        msg += f"<b>За {d_date}:</b>\n"
        for item in grouped[d_date]:
            msg += f"- {item['subject']}: {item['grade']}\n"
    return msg.strip()

# --- Хэндлеры навигации ---
@dp.message(F.text == "Назад")
async def btn_back(message: types.Message, state: FSMContext):
    if message.from_user.id not in USER_IDS: return
    current_state = await state.get_state()
    
    if current_state in (GradesState.waiting_for_start, GradesState.waiting_for_end):
        await state.set_state(GradesState.choosing_action)
        await message.answer("Меню оценок. Выбери действие:", reply_markup=grades_menu)
    else:
        await state.clear()
        await message.answer("Главное меню", reply_markup=main_menu)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in USER_IDS: return
    await state.clear()
    await message.answer("Бот запущен. Выбери действие.", reply_markup=main_menu)

# --- Хэндлеры домашнего задания ---
@dp.message(F.text.in_({"ДЗ Кирилла", "ДЗ Никиты"}))
async def get_hw(message: types.Message):
    if message.from_user.id not in USER_IDS: return
    student_name = message.text.replace("ДЗ ", "")
    await message.answer(f"Собираю ДЗ для {student_name}...")
    
    data = fetch_data(student_name)
    if not data:
        await message.answer("Не удалось получить данные.")
        return
        
    current_hw, _ = data
    if not current_hw:
        await message.answer(f"Заданий на эту неделю для {student_name} пока нет.")
        return
        
    report_hw = format_hw_message(list(current_hw.values()), f"Текущие задания ({student_name}):")
    await message.answer(report_hw, parse_mode="HTML")

# --- Хэндлеры оценок ---
@dp.message(F.text.in_({"Оценки Кирилла", "Оценки Никиты"}))
async def open_grades_menu(message: types.Message, state: FSMContext):
    if message.from_user.id not in USER_IDS: return
    student_name = message.text.replace("Оценки ", "")
    await state.update_data(student_name=student_name)
    await state.set_state(GradesState.choosing_action)
    await message.answer(f"Меню оценок для {student_name}. Выбери действие:", reply_markup=grades_menu)

@dp.message(GradesState.choosing_action, F.text == "Отчет за неделю")
async def grades_week(message: types.Message, state: FSMContext):
    data = await state.get_data()
    student_name = data.get("student_name")
    await message.answer(f"Собираю оценки за текущую неделю для {student_name}...")
    
    parsed_data = fetch_data(student_name)
    if not parsed_data:
        await message.answer("Не удалось получить данные.")
        return
        
    _, current_grades = parsed_data
    if not current_grades:
        await message.answer("Оценок за эту неделю пока нет.")
        return
        
    report = format_grades_message(list(current_grades.values()), f"Оценки за неделю ({student_name}):")
    await message.answer(report, parse_mode="HTML")

@dp.message(GradesState.choosing_action, F.text == "Выбранный период")
async def grades_custom_period(message: types.Message, state: FSMContext):
    await state.set_state(GradesState.waiting_for_start)
    await message.answer("Введи начальную дату в формате ДД.ММ.ГГГГ (например, 01.09.2026):", reply_markup=back_menu)

@dp.message(GradesState.waiting_for_start)
async def process_start_date(message: types.Message, state: FSMContext):
    date_str = validate_date(message.text.strip())
    if not date_str:
        await message.answer("Неверный формат. Введи дату как ДД.ММ.ГГГГ:")
        return
        
    await state.update_data(start_date=date_str)
    await state.set_state(GradesState.waiting_for_end)
    await message.answer("Теперь введи конечную дату в формате ДД.ММ.ГГГГ:")

@dp.message(GradesState.waiting_for_end)
async def process_end_date(message: types.Message, state: FSMContext):
    end_date = validate_date(message.text.strip())
    if not end_date:
        await message.answer("Неверный формат. Введи дату как ДД.ММ.ГГГГ:")
        return
        
    user_data = await state.get_data()
    start_date = user_data['start_date']
    student_name = user_data['student_name']
    
    await message.answer(f"Собираю оценки с {start_date} по {end_date}...")
    parsed_data = fetch_data(student_name, start_date, end_date)
    
    if not parsed_data:
        await message.answer("Не удалось получить данные.")
    else:
        _, current_grades = parsed_data
        if not current_grades:
            await message.answer(f"За период с {start_date} по {end_date} оценок нет.")
        else:
            report = format_grades_message(list(current_grades.values()), f"Оценки с {start_date} по {end_date} ({student_name}):")
            await message.answer(report, parse_mode="HTML")
            
    await state.set_state(GradesState.choosing_action)
    await message.answer("Выбери действие:", reply_markup=grades_menu)

# --- Фоновая рассылка ---
async def check_and_send():
    for student_name in STUDENTS:
        new_hw, new_grades = get_new_updates(student_name)
        
        if new_hw:
            report_hw = format_hw_message(new_hw, f"Внимание, новые задания ({student_name}).")
            for user_id in USER_IDS:
                try: await bot.send_message(chat_id=user_id, text=report_hw, parse_mode="HTML")
                except Exception as e: logging.error(f"Ошибка ДЗ {user_id}: {e}")
                
        if new_grades:
            report_gr = format_grades_message(new_grades, f"Внимание, новые оценки ({student_name}).")
            for user_id in USER_IDS:
                try: await bot.send_message(chat_id=user_id, text=report_gr, parse_mode="HTML")
                except Exception as e: logging.error(f"Ошибка оценок {user_id}: {e}")
                
        await asyncio.sleep(5)

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(check_and_send, "cron", hour="13-20", minute=0)
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
