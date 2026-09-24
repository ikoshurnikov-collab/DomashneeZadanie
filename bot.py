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
        "schedule": {
            0: [406, 2, 5, 1, 13, 579],
            1: [2, 5, 1, 8, 12],
            2: [1, 5, 8, 10, 3],
            3: [81, 5, 1, 2, 12],
            4: [2, 1, 11, 3, 400, 414, 411]
        }
    },
    "Никиты": {
        "student_id": "4722",
        "cls_id": "1088",
        "cookie": "ys-userId=n%3A4184; ys-user=s%3A%u041A%u043E%u0448%u0443%u0440%u043D%u0438%u043A%u043E%u0432; ys-password=s%3A0f4db6388746b33422d5ced1af1b979273a40257",
        "cache_file": "hw_cache_nikita.json",
        "schedule": {
            0: [406, 5, 1, 414, 2, 13],
            1: [5, 1, 2, 10, 3],
            2: [12, 2, 5, 1, 8, 579],
            3: [3, 5, 1, 81, 411],
            4: [1, 12, 8, 2, 11]
        }
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="ДЗ Кирилла"), KeyboardButton(text="ДЗ Никиты")]
    ],
    resize_keyboard=True
)

def get_next_lesson_date(subject_id: int, current_date: datetime, schedule: dict) -> str:
    current_weekday = current_date.weekday()
    for i in range(1, 15):
        next_date = current_date + timedelta(days=i)
        next_weekday = next_date.weekday()
        if next_weekday in schedule and subject_id in schedule[next_weekday]:
            return next_date.strftime("%d.%m.%Y")
    return "Дата неизвестна"

def fetch_current_homework(student_name: str):
    student_data = STUDENTS[student_name]
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    payload_data = {
        "pClassesIds": "",
        "student": student_data["student_id"],
        "cls": student_data["cls_id"],
        "begin_dt": start_of_week.strftime("%d.%m.%Y"),
        "end_dt": end_of_week.strftime("%d.%m.%Y")
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": student_data["cookie"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = requests.post(DATA_URL, data=payload_data, headers=headers, timeout=10)
        logging.info(f"Статус запроса данных ({student_name}): {response.status_code}")
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
            logging.error(f"Финальная ошибка парсинга ({student_name}): {e}")
            return None

    current_hw = {}
    
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
        homework = lesson[4]
        
        if homework and homework.strip():
            next_date = get_next_lesson_date(subject_id, lesson_date, student_data["schedule"])
            subj_name = SUBJECTS.get(subject_id, f"Предмет {subject_id}")
            hw_key = f"{lesson_date.strftime('%Y-%m-%d')}_{subject_id}"
            
            current_hw[hw_key] = {
                "given_date": lesson_date.strftime("%d.%m.%Y"),
                "due_date": next_date,
                "subject": subj_name,
                "text": homework.strip()
            }
            
    return current_hw

def get_new_entries(student_name: str):
    current_hw = fetch_current_homework(student_name)
    if current_hw is None:
        return []

    cache_file = STUDENTS[student_name]["cache_file"]

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            try:
                cached_hw = json.load(f)
            except json.JSONDecodeError:
                cached_hw = {}
    else:
        cached_hw = {}

    new_entries = []
    for hw_key, hw_data in current_hw.items():
        if hw_key not in cached_hw or cached_hw[hw_key]["text"] != hw_data["text"]:
            new_entries.append(hw_data)

    if new_entries:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(current_hw, f, ensure_ascii=False, indent=4)

    return new_entries

def format_message(new_entries, title):
    if not new_entries:
        return ""
    
    grouped = {}
    for entry in new_entries:
        d_date = entry["due_date"]
        if d_date not in grouped:
            grouped[d_date] = []
        grouped[d_date].append(entry)
    
    def parse_date(d):
        try:
            return datetime.strptime(d, "%d.%m.%Y")
        except ValueError:
            return datetime.max
            
    sorted_dates = sorted(grouped.keys(), key=parse_date)
    
    msg = f"{title}\n\n"
    for d_date in sorted_dates:
        msg += f"<b>На {d_date}:</b>\n"
        for item in grouped[d_date]:
            msg += f"- {item['subject']}:\n{item['text']}\n\n"
    return msg.strip()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in USER_IDS:
        return
    await message.answer("Бот запущен. Выберите действие на клавиатуре.", reply_markup=main_menu)

@dp.message(F.text.in_({"ДЗ Кирилла", "ДЗ Никиты"}))
async def force_check(message: types.Message):
    if message.from_user.id not in USER_IDS:
        return
        
    student_name = message.text.replace("ДЗ ", "")
    await message.answer(f"Собираю данные для {student_name}...")
    
    current_hw = fetch_current_homework(student_name)
    
    if not current_hw:
        await message.answer(f"Заданий на эту неделю для {student_name} пока нет или дневник пуст.")
        return

    entries = list(current_hw.values())
    report = format_message(entries, title=f"Текущие задания ({student_name}):")
    await message.answer(report, parse_mode="HTML")

async def check_and_send():
    for student_name in STUDENTS:
        new_entries = get_new_entries(student_name)
        if new_entries:
            report = format_message(new_entries, title=f"Внимание, появились новые записи ({student_name}).")
            for user_id in USER_IDS:
                try:
                    await bot.send_message(chat_id=user_id, text=report, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Ошибка отправки пользователю {user_id}: {e}")
        await asyncio.sleep(5)

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_send, "cron", hour="13-20", minute=0)
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
