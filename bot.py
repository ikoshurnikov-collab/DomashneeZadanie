import ast
import asyncio
import html
import json
import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("MAX_BOT_TOKEN") or "ВСТАВЬ_ТОКЕН_В_НАСТРОЙКИ_BOTHOST"
MAX_API_URL = os.getenv("MAX_API_URL", "https://platform-api.max.ru")
GAS_URL = os.getenv(
    "GAS_URL",
    "https://script.google.com/macros/s/AKfycbzotv5RAgo8Emlz8z3MmAmeXYoVd8HIKs4XZZxZnMUZOMh_gEr_tSpWubFKzA4T9wZ75g/exec"
)
GAS_SECRET = os.getenv("GAS_SECRET", "")
DATA_URL = "https://journal.school28-kirov.ru/act/GET_STUDENT_DAIRY"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Две сессии для повторного использования TCP-соединений без конфликта потоков
API_SESSION = requests.Session()
POLL_SESSION = requests.Session()

# ID пользователей в MAX
ID_IGOR = 11423510
ID_KATYA = 169993452
ID_GRANDMA = 221597034
ID_OLYA = 62297217

ID_KIRILL = 207924440
ID_NIKITA = 200548363
ID_ANYA = int(os.getenv("ID_ANYA", "0"))
ID_NASTYA = 66786192

# Права доступа взрослых к ручному просмотру ДЗ и оценок
ADULT_ACCESS = {
    ID_IGOR: ["Кирилла", "Никиты", "Ани", "Насти"],
    ID_KATYA: ["Кирилла", "Никиты"],
    ID_GRANDMA: ["Кирилла", "Никиты"],
    ID_OLYA: ["Ани", "Насти"]
}

# Персональные приветствия для взрослых
ADULT_GREETINGS = {
    ID_IGOR: "Привет, Игорь! 🫡 Главный пульт управления школой на связи. Кого проверяем?",
    ID_KATYA: "Намасте, Катюша! 🌸 Заглянем в дневники наших парней? Выбирай нужный раздел:",
    ID_GRANDMA: "Здравствуйте, бабуля Наташа! 🌺 Спасибо за вашу заботу и помощь с уроками! Выберите, что хотите посмотреть:",
    ID_OLYA: "Привет, Оля! ☀️ Дневники девчонок под строгим депутатским контролем. Выбирай раздел:"
}

STUDENTS = {
    "Кирилла": {
        "key": "kirill",
        "nominative": "Кирилл",
        "gender": "m",
        "child_greeting": "Привет, Кирилл! 🚀 Готов быстро победить уроки и освободить вечер? Выбирай день:",
        "student_id": os.getenv("STUDENT_ID_KIRILL", "5201"),
        "cls_id": os.getenv("CLS_ID_KIRILL", "1073"),
        "cookie": os.getenv(
            "COOKIE_KIRILL",
            "ys-userId=n%3A6260; ys-user=s%3A%u041A%u043E%u0448%u0443%u0440%u043D%u0438%u043A%u043E%u0432; ys-password=s%3A253a2b69242b3f68978ba08ccce989b9575fc27e"
        ),
        "adult_notify": [ID_IGOR, ID_KATYA],
        "child_user_id": ID_KIRILL,
        "can_submit": True,
        "reviewer_id": ID_GRANDMA,
        "schedule": {
            0: [406, 2, 5, 1, 13, 579],
            1: [2, 5, 1, 8, 12],
            2: [1, 5, 8, 10, 3],
            3: [81, 6, 5, 1, 2, 12],
            4: [2, 1, 11, 3, 400, 414, 411]
        },
        "allowed_teachers": {3: 4233}
    },
    "Никиты": {
        "key": "nikita",
        "nominative": "Никита",
        "gender": "m",
        "child_greeting": "Привет, Никита! ⚡️ Время включить суперсилу и разделаться с домашкой, чтобы побыстрее потанцевать и порисовать! Выбирай день:",
        "student_id": os.getenv("STUDENT_ID_NIKITA", "4722"),
        "cls_id": os.getenv("CLS_ID_NIKITA", "1088"),
        "cookie": os.getenv(
            "COOKIE_NIKITA",
            "ys-userId=n%3A4184; ys-user=s%3A%u041A%u043E%u0448%u0443%u0440%u043D%u0438%u043A%u043E%u0432; ys-password=s%3A0f4db6388746b33422d5ced1af1b979273a40257"
        ),
        "adult_notify": [ID_IGOR, ID_KATYA],
        "child_user_id": ID_NIKITA,
        "can_submit": True,
        "reviewer_id": ID_GRANDMA,
        "schedule": {
            0: [406, 5, 1, 414, 2, 13],
            1: [5, 1, 2, 8, 3],
            2: [12, 2, 5, 1, 8, 579],
            3: [3, 10, 81, 6, 1, 411, 413],
            4: [1, 12, 5, 2, 11]
        },
        "allowed_teachers": {}
    },
    "Ани": {
        "key": "anya",
        "nominative": "Анюта",
        "gender": "f",
        "child_greeting": "Привет, Анюта! 🦄 Посмотрим, что интересного задали в школе? Выбирай день:",
        "student_id": os.getenv("STUDENT_ID_ANYA", "4353"),
        "cls_id": os.getenv("CLS_ID_ANYA", "1052"),
        "cookie": os.getenv(
            "COOKIE_ANYA",
            "ys-userId=n%3A3525; ys-user=s%3A%u0422%u044B%u0440%u044B%u043A%u0438%u043D%u0430; ys-password=s%3A92f53cad2d335c9c9129798a493a6b2622a98e0f"
        ),
        "adult_notify": [ID_OLYA],
        "child_user_id": ID_ANYA,
        "can_submit": False,
        "reviewer_id": None,
        "schedule": {
            0: [406, 414, 411, 3, 1, 5, 2],
            1: [2, 8, 1, 6, 81, 10],
            2: [12, 5, 1, 2, 11],
            3: [8, 5, 1, 2, 13],
            4: [5, 12, 3, 1, 579, 413]
        },
        "allowed_teachers": {3: 4233}
    },
    "Насти": {
        "key": "nastya",
        "nominative": "Настя",
        "gender": "f",
        "child_greeting": "Привет, Настя! 🌟 Вот твое расписание домашних заданий. Выбирай нужный день:",
        "student_id": os.getenv("STUDENT_ID_NASTYA", "4039"),
        "cls_id": os.getenv("CLS_ID_NASTYA", "1064"),
        "cookie": os.getenv(
            "COOKIE_NASTYA",
            "ys-userId=n%3A4434; ys-user=s%3A%u0422%u044B%u0440%u044B%u043A%u0438%u043D%u0430; ys-password=s%3A5ae54bef1ea265fe7900f82b07e30c93307ea199"
        ),
        "adult_notify": [ID_OLYA],
        "child_user_id": ID_NASTYA,
        "can_submit": False,
        "reviewer_id": None,
        "schedule": {
            0: [406, 16, 5, 1, 10],
            1: [5, 12, 6, 81, 1, 13],
            2: [7, 20, 5, 1, 16, 3],
            3: [82, 7, 5, 1, 19, 11],
            4: [1, 12, 5, 16, 7, 3]
        },
        "allowed_teachers": {3: 4163}
    }
}

SUBJECTS = {
    1: "✍️ Русский язык",
    2: "📖 Литературное чтение",
    3: "🇬🇧 Иностранный язык",
    5: "📐 Математика",
    6: "💻 Информатика и ИКТ",
    7: "🏛 История",
    8: "🌍 Окружающий мир",
    10: "🎵 Музыка",
    11: "🎨 Изобразительное искусство",
    12: "🏃 Физическая культура",
    13: "🛠 Труд (технология)",
    16: "📚 Литература",
    19: "🗺 География",
    20: "🌿 Биология",
    81: "💻 Информатика и ИКТ",
    82: "🔔 Духовно-нравственная культура России",
    400: "🏛 Основы религиозных культур и светской этики",
    406: "💬 Разговоры о важном",
    411: "🧠 Функциональная грамотность",
    413: "🧭 Мир профессий",
    414: "🤖 Робототехника",
    570: "🌱 Мир вокруг нас",
    579: "🦅 Орлята России",
    601: "🏊 Плавание"
}

WEEKDAYS_ACCUSATIVE = {
    0: "понедельник",
    1: "вторник",
    2: "среду",
    3: "четверг",
    4: "пятницу",
    5: "субботу",
    6: "воскресенье"
}

WEEKDAYS_SHORT = {
    0: "пн",
    1: "вт",
    2: "ср",
    3: "чт",
    4: "пт",
    5: "сб",
    6: "вс"
}

USER_STATES = {}


def get_child_student_name(user_id: int):
    for s_name, s_data in STUDENTS.items():
        if s_data.get("child_user_id") and s_data["child_user_id"] == user_id:
            return s_name
    return None


def is_recent_date(date_str: str, max_days: int = 14) -> bool:
    today = datetime.now(MOSCOW_TZ).date()
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y").date()
        return (today - dt).days <= max_days
    except ValueError:
        return False


# --- РАБОТА С API МЕССЕНДЖЕРА MAX ---

def max_headers():
    return {
        "Authorization": BOT_TOKEN,
        "Content-Type": "application/json"
    }


def make_keyboard(button_rows):
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": button_rows
        }
    }


def cb_btn(text: str, payload: str):
    return {
        "type": "callback",
        "text": str(text)[:60],
        "payload": str(payload)[:128]
    }


def _sync_send_message(user_id: int, text: str, buttons=None, extra_attachments=None):
    attachments = []
    if extra_attachments:
        attachments.extend(extra_attachments)
    if buttons:
        attachments.append(make_keyboard(buttons))

    body = {
        "text": text,
        "format": "html"
    }
    if attachments:
        body["attachments"] = attachments

    try:
        resp = API_SESSION.post(
            f"{MAX_API_URL}/messages",
            params={"user_id": user_id},
            headers=max_headers(),
            json=body,
            timeout=15
        )
        if resp.status_code != 200 and extra_attachments and buttons:
            body_media = {"text": text, "format": "html", "attachments": extra_attachments}
            API_SESSION.post(
                f"{MAX_API_URL}/messages",
                params={"user_id": user_id},
                headers=max_headers(),
                json=body_media,
                timeout=15
            )
            body_kb = {"text": "Выбери действие 👇", "format": "html", "attachments": [make_keyboard(buttons)]}
            API_SESSION.post(
                f"{MAX_API_URL}/messages",
                params={"user_id": user_id},
                headers=max_headers(),
                json=body_kb,
                timeout=15
            )
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения в MAX пользователю {user_id}: {e}")


async def send_max_message(user_id: int, text: str, buttons=None, extra_attachments=None):
    await asyncio.to_thread(_sync_send_message, user_id, text, buttons, extra_attachments)


def _sync_answer_callback(callback_id: str, text: str = None, buttons=None, notification: str = None):
    body = {}
    if notification:
        body["notification"] = notification
    if text is not None:
        msg_obj = {
            "text": text,
            "format": "html",
            "attachments": [make_keyboard(buttons)] if buttons else []
        }
        body["message"] = msg_obj

    try:
        API_SESSION.post(
            f"{MAX_API_URL}/answers",
            params={"callback_id": callback_id},
            headers=max_headers(),
            json=body,
            timeout=15
        )
    except Exception as e:
        logging.error(f"Ошибка ответа на callback в MAX: {e}")


async def answer_max_callback(callback_id: str, text: str = None, buttons=None, notification: str = None):
    await asyncio.to_thread(_sync_answer_callback, callback_id, text, buttons, notification)


# --- РАБОТА С GOOGLE ТАБЛИЦЕЙ (APPS SCRIPT) ---

def _sync_gas_request(payload: dict):
    if GAS_SECRET:
        payload["secret"] = GAS_SECRET
    try:
        resp = API_SESSION.post(GAS_URL, json=payload, timeout=20)
        if resp.status_code != 200:
            logging.error(f"Ошибка HTTP от Google Таблицы: {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка обращения к Google Таблице: {e}")
        return None


async def gas_request(payload: dict):
    return await asyncio.to_thread(_sync_gas_request, payload)


# --- ПАРСИНГ ДНЕВНИКА АВЕРС ---

def get_next_lesson_date(subject_id: int, current_date: datetime, schedule: dict) -> str:
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


def _sync_fetch_avers(student_name: str, start_dt_str: str = None, end_dt_str: str = None):
    student_data = STUDENTS[student_name]

    if not start_dt_str or not end_dt_str:
        today = datetime.now(MOSCOW_TZ).replace(tzinfo=None)
        start_of_week = today - timedelta(days=today.weekday())
        # Захватываем полные 7 дней прошлой недели для предметов, идущих 1 раз в неделю
        begin_dt = start_of_week - timedelta(days=7)
        end_dt = start_of_week + timedelta(days=6)
        start_dt_str = begin_dt.strftime("%d.%m.%Y")
        end_dt_str = end_dt.strftime("%d.%m.%Y")

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
        response = API_SESSION.post(DATA_URL, data=payload_data, headers=headers, timeout=15)
    except requests.exceptions.RequestException as e:
        logging.error(f"Сетевая ошибка Аверс ({student_name}): {e}")
        return None

    if response.status_code != 200 or "login" in response.url.lower():
        logging.error(f"Ошибка доступа к Аверс ({student_name}): статус {response.status_code}, URL {response.url}")
        return None

    clean_text = re.sub(r'new Date\((.*?)\)', r'"\1"', response.text)
    clean_text = re.sub(r',\s*]', ']', clean_text)

    try:
        lessons = json.loads(clean_text, strict=False)
    except json.JSONDecodeError:
        try:
            fallback_text = clean_text.replace('\n', ' ').replace('\r', '')
            eval_text = re.sub(r'\bnull\b', 'None', fallback_text)
            eval_text = re.sub(r'\btrue\b', 'True', eval_text)
            eval_text = re.sub(r'\bfalse\b', 'False', eval_text)
            lessons = ast.literal_eval(eval_text)
        except Exception as e:
            logging.error(f"Ошибка парсинга Аверс ({student_name}): {e}")
            return None

    if not isinstance(lessons, list):
        logging.error(f"Некорректный формат ответа Аверс ({student_name}): ожидался список")
        return None

    current_hw = {}
    current_grades = {}
    s_key = student_data["key"]

    for lesson in lessons:
        if not isinstance(lesson, list) or len(lesson) < 3:
            continue

        date_str_parts = str(lesson[0]).split(",")
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

        subj_name = SUBJECTS.get(subject_id, f"📘 Предмет {subject_id}")
        item_id = f"{s_key}_{lesson_date.strftime('%Y-%m-%d')}_{subject_id}"

        if homework:
            hw_raw = str(homework).strip()
            if hw_raw and hw_raw.lower() not in ["не задано", "нет"]:
                hw_escaped = html.escape(hw_raw)
                topic_raw = str(lesson[3]).strip() if len(lesson) > 3 and lesson[3] else ""
                full_text = ""
                if topic_raw:
                    full_text += f"📌 Тема: {html.escape(topic_raw)}\n"
                full_text += f"📝 ДЗ: {hw_escaped}"

                next_date = get_next_lesson_date(subject_id, lesson_date, student_data["schedule"])
                if item_id in current_hw:
                    # Склейка разных заданий для сдвоенных уроков без дублирования одинакового текста
                    if full_text not in current_hw[item_id]["text"]:
                        current_hw[item_id]["text"] += f"\n\n{full_text}"
                else:
                    current_hw[item_id] = {
                        "id": item_id,
                        "given_date": lesson_date.strftime("%d.%m.%Y"),
                        "due_date": next_date,
                        "subject": subj_name,
                        "text": full_text
                    }

        if grade and str(grade).strip():
            gr_str = html.escape(str(grade).strip())
            if item_id in current_grades:
                current_grades[item_id]["grade"] += f" / {gr_str}"
            else:
                current_grades[item_id] = {
                    "id": item_id,
                    "date": lesson_date.strftime("%d.%m.%Y"),
                    "subject": subj_name,
                    "grade": gr_str
                }

    return list(current_hw.values()), list(current_grades.values())


async def fetch_avers(student_name: str, start_dt_str: str = None, end_dt_str: str = None):
    return await asyncio.to_thread(_sync_fetch_avers, student_name, start_dt_str, end_dt_str)


# --- ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ---

STATUS_LABELS = {
    "new": "🆕 новое",
    "pending": "⏳ на проверке у бабушки",
    "revision": "🛠 на доработке",
    "done": "✅ выполнено"
}


def decorate_grade(grade_str: str) -> str:
    if "5" in grade_str:
        return f"{grade_str} 🌟"
    if "4" in grade_str:
        return f"{grade_str} 👍"
    if "3" in grade_str or "2" in grade_str:
        return f"{grade_str} 👀"
    return grade_str


def format_hw_message(entries, title, show_status=False):
    if not entries:
        return ""
    grouped = {}
    for entry in entries:
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
    msg = f"<b>{title}</b>\n\n"
    for d_date in sorted_dates:
        msg += f"🗓 <b>На {d_date}:</b>\n"
        for item in grouped[d_date]:
            st_str = ""
            if show_status and "status" in item:
                st_label = STATUS_LABELS.get(item["status"], item["status"])
                st_str = f" [{st_label}]"
            msg += f"• <b>{item['subject']}</b>{st_str}:\n{item['text']}\n\n"
    return msg.strip()


def format_grades_message(entries, title):
    if not entries:
        return ""
    grouped = {}
    for entry in entries:
        d_date = entry["date"]
        if d_date not in grouped:
            grouped[d_date] = []
        grouped[d_date].append(entry)

    def parse_date(d):
        try:
            return datetime.strptime(d, "%d.%m.%Y")
        except ValueError:
            return datetime.max

    sorted_dates = sorted(grouped.keys(), key=parse_date)
    msg = f"<b>{title}</b>\n\n"
    for d_date in sorted_dates:
        msg += f"📅 <b>За {d_date}:</b>\n"
        for item in grouped[d_date]:
            nice_grade = decorate_grade(item["grade"])
            msg += f"• {item['subject']}: <b>{nice_grade}</b>\n"
        msg += "\n"
    return msg.strip()


def format_day_button_label(due_date_str: str) -> str:
    today = datetime.now(MOSCOW_TZ).date()
    try:
        dt = datetime.strptime(due_date_str, "%d.%m.%Y").date()
    except ValueError:
        return f"📆 На {due_date_str}"

    diff = (dt - today).days
    wd_acc = WEEKDAYS_ACCUSATIVE.get(dt.weekday(), "")
    wd_short = WEEKDAYS_SHORT.get(dt.weekday(), "")
    short_date = dt.strftime("%d.%m")

    if diff == 0:
        return f"🔥 На сегодня ({wd_short}, {short_date})"
    elif diff == 1:
        return f"📌 На завтра ({wd_short}, {short_date})"
    elif diff == 2:
        return f"⏳ На послезавтра ({wd_short}, {short_date})"
    else:
        return f"📆 На {wd_acc} ({short_date})"


# --- ДЕТСКОЕ МЕНЮ ---

async def get_active_child_hw(student_name: str):
    res = await gas_request({"action": "get_hw", "student": student_name})
    if not res or res.get("status") != "ok":
        return []

    today = datetime.now(MOSCOW_TZ).date()
    active = []
    for item in res.get("items", []):
        status = item.get("status", "new")
        if status not in ("new", "revision"):
            continue

        due_str = item.get("due_date", "")
        try:
            due_dt = datetime.strptime(due_str, "%d.%m.%Y").date()
            if due_dt >= today or status == "revision":
                active.append(item)
        except ValueError:
            # Если дата урока неизвестна, держим задание в списке не дольше 14 дней с даты выдачи
            if status == "revision" or is_recent_date(item.get("given_date", ""), max_days=14):
                active.append(item)

    return active


async def build_child_days_view(student_name: str):
    s_data = STUDENTS[student_name]
    child_name = s_data.get("nominative", "")
    greeting = s_data.get("child_greeting", f"Привет, {child_name}! 👋")

    items = await get_active_child_hw(student_name)
    if not items:
        text = (
            f"🎉 Ура, {child_name}! Все домашние задания выполнены, ты супер-молодец!\n"
            f"Можно смело отдыхать и заниматься любимыми делами 🎮✨"
        )
        return text, [[cb_btn("🔄 Обновить список", "child_days")]]

    dates_set = set(item["due_date"] for item in items)

    def parse_date(d):
        try:
            return datetime.strptime(d, "%d.%m.%Y")
        except ValueError:
            return datetime.max

    sorted_dates = sorted(list(dates_set), key=parse_date)
    buttons = []
    for d_str in sorted_dates:
        label = format_day_button_label(d_str)
        buttons.append([cb_btn(label, f"c_day:{d_str}")])

    return greeting, buttons


async def build_child_subjects_view(student_name: str, due_date_str: str):
    child_name = STUDENTS[student_name].get("nominative", "Котик")
    items = await get_active_child_hw(student_name)
    day_items = [i for i in items if i["due_date"] == due_date_str]

    if not day_items:
        return (
            f"✨ {child_name}, на {due_date_str} все уроки уже сделаны! Отличная работа! 👏",
            [[cb_btn("⬅️ Назад к дням", "child_days")]]
        )

    buttons = []
    for item in day_items:
        subj_title = item["subject"]
        if item.get("status") == "revision":
            subj_title = f"🛠 {subj_title} (доработка)"
        buttons.append([cb_btn(subj_title, f"c_hw:{item['id']}")])

    buttons.append([cb_btn("⬅️ Назад к дням", "child_days")])
    label = format_day_button_label(due_date_str).lower()
    return f"📚 {child_name}, выбери предмет ({label}):", buttons


async def build_child_item_view(student_name: str, hw_id: str):
    res = await gas_request({"action": "get_item", "id": hw_id})
    if not res or res.get("status") != "ok":
        return "😕 Задание не найдено.", [[cb_btn("⬅️ К списку дней", "child_days")]]

    item = res["item"]
    due_date = item["due_date"]
    text = f"<b>{item['subject']}</b> (🗓 на {due_date})\n\n{item['text']}"

    if item.get("status") == "revision" and item.get("comment"):
        safe_comment = html.escape(str(item["comment"]))
        text += f"\n\n💬 <b>Замечание от бабушки Наташи:</b>\n<i>{safe_comment}</i>"

    buttons = []
    if STUDENTS[student_name].get("can_submit"):
        buttons.append([cb_btn("✅ Я завершил!", f"c_done:{hw_id}")])
    buttons.append([cb_btn("⬅️ Назад к предметам", f"c_day:{due_date}")])

    return text, buttons


# --- ВЗРОСЛОЕ МЕНЮ ---

def build_adult_main_menu(user_id: int):
    allowed_students = ADULT_ACCESS.get(user_id, [])
    buttons = []
    for s_name in allowed_students:
        buttons.append([
            cb_btn(f"📚 ДЗ {s_name}", f"a_hw:{s_name}"),
            cb_btn(f"📊 Оценки {s_name}", f"a_gr:{s_name}")
        ])
    greeting = ADULT_GREETINGS.get(user_id, "👋 Главное меню. Выберите нужный раздел:")
    return greeting, buttons


def build_adult_grades_menu(student_name: str):
    buttons = [
        [cb_btn("📅 Отчет за неделю", f"a_gr_week:{student_name}")],
        [cb_btn("🗓 Выбранный период", f"a_gr_per:{student_name}")],
        [cb_btn("🏠 В главное меню", "adult_menu")]
    ]
    return f"📊 <b>Меню оценок ({student_name})</b>\nЗа какой период показать оценки?", buttons


# --- ОБРАБОТКА ВХОДЯЩИХ СОБЫТИЙ MAX ---

async def handle_text_or_media_message(message: dict):
    sender = message.get("sender", {})
    user_id = sender.get("user_id")
    if not user_id:
        return

    body = message.get("body") or {}
    text = (body.get("text") or "").strip()
    attachments = body.get("attachments") or []

    # Сброс зависших состояний при вызове команд старта или отмены
    if text.lower() in ("/start", "старт", "меню", "отмена"):
        USER_STATES.pop(user_id, None)

    # 1. Проверка активных состояний
    if user_id in USER_STATES:
        state_data = USER_STATES[user_id]
        st_type = state_data.get("state")

        # Сценарий: ребенок загружает фотографии выполненной домашки
        if st_type == "waiting_hw_photos":
            hw_id = state_data["hw_id"]
            image_tokens = []
            for att in attachments:
                if att.get("type") == "image" and att.get("payload", {}).get("token"):
                    image_tokens.append(att["payload"]["token"])

            if image_tokens:
                state_data["photos"].extend(image_tokens)
                total = len(state_data["photos"])
                buttons = [
                    [cb_btn(f"🚀 Отправить на проверку ({total} фото)", f"c_submit:{hw_id}")],
                    [cb_btn("❌ Отмена", f"c_hw:{hw_id}")]
                ]
                await send_max_message(
                    user_id,
                    f"📸 Супер, фотография поймана (всего загружено: {total} шт.)!\n"
                    f"Если есть еще страница - присылай следом, а если это всё - жми кнопку отправки 👇",
                    buttons
                )
            else:
                buttons = [[cb_btn("❌ Отмена", f"c_hw:{hw_id}")]]
                await send_max_message(
                    user_id,
                    "📷 Пожалуйста, прикрепи именно фотографию своей тетради!",
                    buttons
                )
            return

        # Сценарий: бабушка Наташа отправляет замечание на доработку (текст или голосовое)
        if st_type == "waiting_gm_comment":
            hw_id = state_data["hw_id"]
            media_to_forward = []
            for att in attachments:
                if att.get("type") in ("audio", "file", "image", "video") and att.get("payload", {}).get("token"):
                    media_to_forward.append({
                        "type": att["type"],
                        "payload": {"token": att["payload"]["token"]}
                    })

            if not text and not media_to_forward:
                await send_max_message(
                    user_id,
                    "✍️ Пожалуйста, напишите текст замечания или запишите голосовое сообщение в чат:",
                    [[cb_btn("❌ Отмена", f"gm_cancel:{hw_id}")]]
                )
                return

            comment_for_sheet = text if text else "🎤 Голосовое сообщение от бабушки"
            res = await gas_request({
                "action": "update_status",
                "id": hw_id,
                "status": "revision",
                "comment": comment_for_sheet
            })
            USER_STATES.pop(user_id, None)

            if res and res.get("status") == "ok":
                item = res["item"]
                student_name = item["student"]
                s_info = STUDENTS.get(student_name, {})
                child_nom = s_info.get("nominative", "Ребенок")
                child_id = s_info.get("child_user_id")
                await send_max_message(
                    user_id,
                    f"📨 Спасибо! Ваше замечание отправлено. Задание по предмету <b>{item['subject']}</b> ({student_name}) возвращено на доработку.",
                    build_adult_main_menu(user_id)[1]
                )
                if child_id:
                    child_msg = (
                        f"🧐 {child_nom}, бабушка Наташа проверила твою работу по предмету <b>{item['subject']}</b> "
                        f"(на {item['due_date']}) и попросила кое-что подправить.\n\n"
                        f"<b>Задание:</b>\n{item['text']}"
                    )
                    if text:
                        child_msg += f"\n\n💬 <b>Замечание бабушки:</b>\n<i>{html.escape(text)}</i>"
                    elif media_to_forward:
                        child_msg += "\n\n🎧 <i>Прослушай голосовое замечание от бабушки во вложении!</i>"

                    await send_max_message(
                        child_id,
                        child_msg,
                        [[cb_btn("🛠 Перейти к исправлению", f"c_hw:{hw_id}")]],
                        extra_attachments=media_to_forward
                    )
            else:
                await send_max_message(user_id, "⚠️ Не удалось обновить статус в таблице. Попробуйте еще раз.")
            return

        # Сценарий: ввод начальной даты для оценок
        if st_type == "waiting_start_date":
            date_str = validate_date(text)
            if not date_str:
                await send_max_message(
                    user_id,
                    "⚠️ Неверный формат даты. Введите начальную дату как ДД.ММ.ГГГГ (например, 01.09.2026):",
                    [[cb_btn("❌ Отмена", "adult_menu")]]
                )
                return
            state_data["start_date"] = date_str
            state_data["state"] = "waiting_end_date"
            await send_max_message(
                user_id,
                "🗓 Отлично! Теперь введите конечную дату в формате ДД.ММ.ГГГГ:",
                [[cb_btn("❌ Отмена", "adult_menu")]]
            )
            return

        # Сценарий: ввод конечной даты для оценок
        if st_type == "waiting_end_date":
            end_date = validate_date(text)
            if not end_date:
                await send_max_message(
                    user_id,
                    "⚠️ Неверный формат даты. Введите конечную дату как ДД.ММ.ГГГГ:",
                    [[cb_btn("❌ Отмена", "adult_menu")]]
                )
                return
            start_date = state_data["start_date"]
            student_name = state_data["student_name"]
            USER_STATES.pop(user_id, None)

            # Автоматическая корректировка порядка дат, если конечная дата раньше начальной
            dt_start = datetime.strptime(start_date, "%d.%m.%Y")
            dt_end = datetime.strptime(end_date, "%d.%m.%Y")
            if dt_end < dt_start:
                start_date, end_date = end_date, start_date

            await send_max_message(user_id, f"⏳ Собираю оценки с {start_date} по {end_date} ({student_name})...")
            parsed = await fetch_avers(student_name, start_date, end_date)
            _, buttons = build_adult_grades_menu(student_name)

            if not parsed:
                await send_max_message(user_id, "😕 Не удалось получить данные из электронного дневника.", buttons)
            else:
                _, grades_list = parsed
                if not grades_list:
                    await send_max_message(user_id, f"📭 За период с {start_date} по {end_date} оценок нет.", buttons)
                else:
                    report = format_grades_message(grades_list, f"📊 Оценки с {start_date} по {end_date} ({student_name}):")
                    await send_max_message(user_id, report, buttons)
            return

    # 2. Стандартный вход без активного состояния
    if user_id in ADULT_ACCESS:
        msg_text, buttons = build_adult_main_menu(user_id)
        await send_max_message(user_id, msg_text, buttons)
        return

    child_student = get_child_student_name(user_id)
    if child_student:
        msg_text, buttons = await build_child_days_view(child_student)
        await send_max_message(user_id, msg_text, buttons)
        return


async def handle_callback_event(update: dict):
    cb = update.get("callback") or {}
    callback_id = cb.get("callback_id")
    payload = cb.get("payload") or ""
    user = cb.get("user") or {}
    user_id = user.get("user_id")

    if not callback_id or not user_id:
        return

    # --- НАВИГАЦИЯ РЕБЕНКА ---
    child_student = get_child_student_name(user_id)
    if child_student:
        s_info = STUDENTS[child_student]
        child_nom = s_info.get("nominative", "Чемпион")
        is_female = s_info.get("gender") == "f"

        if payload == "child_days":
            USER_STATES.pop(user_id, None)
            text, buttons = await build_child_days_view(child_student)
            await answer_max_callback(callback_id, text=text, buttons=buttons)
            return

        if payload.startswith("c_day:"):
            USER_STATES.pop(user_id, None)
            due_date = payload.split(":", 1)[1]
            text, buttons = await build_child_subjects_view(child_student, due_date)
            await answer_max_callback(callback_id, text=text, buttons=buttons)
            return

        if payload.startswith("c_hw:"):
            USER_STATES.pop(user_id, None)
            hw_id = payload.split(":", 1)[1]
            text, buttons = await build_child_item_view(child_student, hw_id)
            await answer_max_callback(callback_id, text=text, buttons=buttons)
            return

        if payload.startswith("c_done:"):
            hw_id = payload.split(":", 1)[1]
            USER_STATES[user_id] = {
                "state": "waiting_hw_photos",
                "hw_id": hw_id,
                "photos": []
            }
            prompt_text = (
                f"📸 Ну-ка, {child_nom}, подгрузи выполненную домашку!\n"
                f"Сфотографируй тетрадь и отправь фото в этот чат (можно несколько страниц подряд).\n\n"
                f"Когда загрузишь все страницы, нажми кнопку отправки на проверку 👇"
            )
            await answer_max_callback(callback_id, text=prompt_text, buttons=[[cb_btn("❌ Отмена", f"c_hw:{hw_id}")]])
            return

        if payload.startswith("c_submit:"):
            hw_id = payload.split(":", 1)[1]
            st_data = USER_STATES.get(user_id)

            # Защита от повторного нажатия кнопки отправки на старых сообщениях
            if not st_data or st_data.get("state") != "waiting_hw_photos" or st_data.get("hw_id") != hw_id:
                text, buttons = await build_child_days_view(child_student)
                await answer_max_callback(
                    callback_id,
                    text=text,
                    buttons=buttons,
                    notification="ℹ️ Это задание уже отправлено на проверку!"
                )
                return

            photos = st_data.get("photos", [])
            if not photos:
                await answer_max_callback(callback_id, notification="📷 Сначала отправь хотя бы одно фото тетради!")
                return

            USER_STATES.pop(user_id, None)
            res = await gas_request({
                "action": "update_status",
                "id": hw_id,
                "status": "pending",
                "photos": json.dumps(photos)
            })

            if not res or res.get("status") != "ok":
                await answer_max_callback(
                    callback_id,
                    text="⚠️ Ошибка сохранения. Попробуй еще раз.",
                    buttons=[[cb_btn("⬅️ Назад", f"c_hw:{hw_id}")]]
                )
                return

            item = res["item"]
            praise_word = "Умница" if is_female else "Красавчик"
            await answer_max_callback(
                callback_id,
                text=(
                    f"🎉 {praise_word}, {child_nom}! Домашка по предмету <b>{item['subject']}</b> "
                    f"улетела бабушке Наташе на проверку. Ждем результат! 🤞"
                ),
                buttons=[[cb_btn("📚 К остальным заданиям", "child_days")]]
            )

            # Пересылка отчета бабушке Наташе
            reviewer_id = s_info.get("reviewer_id")
            if reviewer_id:
                rel_label = "👧 Внучка" if is_female else "👦 Внук"
                gm_text = (
                    f"📬 <b>Бабушка Наташа, прилетела домашка на проверку!</b>\n"
                    f"{rel_label}: <b>{child_nom}</b>\n"
                    f"📖 Предмет: <b>{item['subject']}</b> (на {item['due_date']})\n\n"
                    f"{item['text']}\n\n"
                    f"Посмотрите фотографии ниже и выберите решение 👇"
                )
                img_attachments = [{"type": "image", "payload": {"token": t}} for t in photos[:11]]
                gm_buttons = [[
                    cb_btn("✅ Подтвердить", f"gm_ok:{hw_id}"),
                    cb_btn("✏️ На доработку", f"gm_rev:{hw_id}")
                ]]
                await send_max_message(reviewer_id, gm_text, gm_buttons, extra_attachments=img_attachments)
            return

    # --- НАВИГАЦИЯ ВЗРОСЛЫХ И ПРОВЕРКА БАБУШКОЙ ---
    if user_id in ADULT_ACCESS:
        if payload == "adult_menu":
            USER_STATES.pop(user_id, None)
            text, buttons = build_adult_main_menu(user_id)
            await answer_max_callback(callback_id, text=text, buttons=buttons)
            return

        if payload.startswith("gm_ok:"):
            hw_id = payload.split(":", 1)[1]
            res = await gas_request({"action": "update_status", "id": hw_id, "status": "done"})
            if res and res.get("status") == "ok":
                item = res["item"]
                s_name = item["student"]
                s_info = STUDENTS.get(s_name, {})
                child_nom = s_info.get("nominative", "Ребенок")
                champ_word = "чемпионка" if s_info.get("gender") == "f" else "чемпион"
                await answer_max_callback(
                    callback_id,
                    text=(
                        f"✅ <b>Выполнение подтверждено!</b>\n"
                        f"Предмет: <b>{item['subject']}</b> ({child_nom}, на {item['due_date']}).\n"
                        f"Спасибо за проверку, бабушка Наташа! 🌺"
                    ),
                    buttons=[[cb_btn("🏠 В главное меню", "adult_menu")]]
                )
                child_id = s_info.get("child_user_id")
                if child_id:
                    await send_max_message(
                        child_id,
                        f"🥳 Ура, {child_nom}! Бабушка Наташа проверила и подтвердила твою домашку по предмету <b>{item['subject']}</b>! Так держать, {champ_word}! 🏆",
                        [[cb_btn("📚 К заданиям", "child_days")]]
                    )
            return

        if payload.startswith("gm_rev:"):
            hw_id = payload.split(":", 1)[1]
            USER_STATES[user_id] = {"state": "waiting_gm_comment", "hw_id": hw_id}
            await answer_max_callback(
                callback_id,
                text=(
                    "✍️ Бабушка Наташа, напишите текстом или отправьте голосовое сообщение в этот чат: "
                    "подскажите, что именно нужно исправить или доделать 👇"
                ),
                buttons=[[cb_btn("❌ Отмена", f"gm_cancel:{hw_id}")]]
            )
            return

        if payload.startswith("gm_cancel:"):
            USER_STATES.pop(user_id, None)
            text, buttons = build_adult_main_menu(user_id)
            await answer_max_callback(callback_id, text=text, buttons=buttons)
            return

        if payload.startswith("a_hw:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            await answer_max_callback(callback_id, notification=f"⏳ Загружаю ДЗ ({student_name})...")

            parsed = await fetch_avers(student_name)
            if not parsed:
                await send_max_message(user_id, "😕 Не удалось получить данные из дневника.", build_adult_main_menu(user_id)[1])
                return

            hw_list, grades_list = parsed
            await gas_request({
                "action": "sync",
                "student": student_name,
                "hw_list": hw_list,
                "grades_list": grades_list
            })

            sheet_res = await gas_request({"action": "get_hw", "student": student_name})
            status_map = {}
            if sheet_res and sheet_res.get("status") == "ok":
                for s_item in sheet_res.get("items", []):
                    status_map[s_item["id"]] = s_item.get("status", "new")

            today_start = datetime.now(MOSCOW_TZ).replace(tzinfo=None)
            week_start = (today_start - timedelta(days=today_start.weekday())).date()

            filtered_hw = []
            for h in hw_list:
                h["status"] = status_map.get(h["id"], "new")
                try:
                    g_dt = datetime.strptime(h["given_date"], "%d.%m.%Y").date()
                    d_dt = datetime.strptime(h["due_date"], "%d.%m.%Y").date()
                    if g_dt >= week_start or d_dt >= week_start:
                        filtered_hw.append(h)
                except ValueError:
                    if is_recent_date(h.get("given_date", ""), max_days=14):
                        filtered_hw.append(h)

            show_st = STUDENTS[student_name].get("can_submit", False)
            if not filtered_hw:
                await send_max_message(
                    user_id,
                    f"📭 Заданий на текущую неделю для {student_name} пока нет.",
                    build_adult_main_menu(user_id)[1]
                )
            else:
                report = format_hw_message(filtered_hw, f"📚 Текущие задания ({student_name}):", show_status=show_st)
                await send_max_message(user_id, report, build_adult_main_menu(user_id)[1])
            return

        if payload.startswith("a_gr:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            text, buttons = build_adult_grades_menu(student_name)
            await answer_max_callback(callback_id, text=text, buttons=buttons)
            return

        if payload.startswith("a_gr_week:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            await answer_max_callback(callback_id, notification=f"⏳ Загружаю оценки ({student_name})...")

            today = datetime.now(MOSCOW_TZ).replace(tzinfo=None)
            start_of_week = (today - timedelta(days=today.weekday())).strftime("%d.%m.%Y")
            end_of_week = (today - timedelta(days=today.weekday()) + timedelta(days=6)).strftime("%d.%m.%Y")

            parsed = await fetch_avers(student_name, start_of_week, end_of_week)
            _, buttons = build_adult_grades_menu(student_name)

            if not parsed:
                await send_max_message(user_id, "😕 Не удалось получить данные из дневника.", buttons)
                return

            _, grades_list = parsed
            if not grades_list:
                await send_max_message(user_id, f"📭 Оценок за текущую неделю ({student_name}) пока нет.", buttons)
            else:
                report = format_grades_message(grades_list, f"📊 Оценки за неделю ({student_name}):")
                await send_max_message(user_id, report, buttons)
            return

        if payload.startswith("a_gr_per:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            USER_STATES[user_id] = {"state": "waiting_start_date", "student_name": student_name}
            await answer_max_callback(
                callback_id,
                text=f"🗓 Введите начальную дату для оценок ({student_name}) в формате ДД.ММ.ГГГГ (например, 01.09.2026):",
                buttons=[[cb_btn("❌ Отмена", "adult_menu")]]
            )
            return


# --- ФОНОВАЯ СИНХРОНИЗАЦИЯ И РАССЫЛКА ПО РАСПИСАНИЮ ---

async def check_and_send():
    now_msk = datetime.now(MOSCOW_TZ)
    current_hour = now_msk.hour

    for student_name, student_data in STUDENTS.items():
        parsed = await fetch_avers(student_name)
        if not parsed:
            continue

        hw_list, grades_list = parsed
        sync_res = await gas_request({
            "action": "sync",
            "student": student_name,
            "hw_list": hw_list,
            "grades_list": grades_list
        })

        if not sync_res or sync_res.get("status") != "ok":
            continue

        new_hw = sync_res.get("new_hw", [])
        new_grades = sync_res.get("new_grades", [])
        adult_chats = student_data.get("adult_notify", [])
        child_nom = student_data.get("nominative", "")

        # 1. Взрослым уведомления уходят сразу с 12:00 до 20:00
        if new_hw:
            report_hw = format_hw_message(new_hw, f"📚 Новые домашние задания ({student_name}):")
            for uid in adult_chats:
                await send_max_message(uid, report_hw, build_adult_main_menu(uid)[1])

        if new_grades:
            report_gr = format_grades_message(new_grades, f"🔔 Новые оценки в дневнике ({student_name}):")
            for uid in adult_chats:
                await send_max_message(uid, report_gr, build_adult_main_menu(uid)[1])

        # 2. Детям уведомления уходят только начиная с 14:00
        child_id = student_data.get("child_user_id")
        if child_id and current_hour >= 14:
            unnotified_res = await gas_request({
                "action": "get_hw",
                "student": student_name,
                "only_unnotified": True
            })

            unnotified_items = []
            if unnotified_res and unnotified_res.get("status") == "ok":
                unnotified_items = unnotified_res.get("items", [])

            if current_hour == 14:
                active_items = await get_active_child_hw(student_name)
                if unnotified_items:
                    msg_14 = (
                        f"🐦 Чирик, котик линтеха! {child_nom}, тебе пришла новая домашка, "
                        f"приступишь к выполнению? 💪✨"
                    )
                    await send_max_message(child_id, msg_14, [[cb_btn("🚀 Перейти к заданиям", "child_days")]])
                    ids_to_mark = [i["id"] for i in unnotified_items]
                    await gas_request({"action": "mark_notified", "ids": ids_to_mark})
                elif active_items:
                    msg_rem = (
                        f"🐦 Чирик, котик линтеха! {child_nom}, напоминаю, что у тебя есть "
                        f"невыполненные задания на ближайшие дни. Приступишь к выполнению? 💪✨"
                    )
                    await send_max_message(child_id, msg_rem, [[cb_btn("🚀 Перейти к заданиям", "child_days")]])

            elif current_hour > 14 and unnotified_items:
                msg_late = (
                    f"🔔 Вжух, {child_nom}! Из школы прилетела еще одна новая домашка. "
                    f"Загляни в общий раздел! 👀"
                )
                await send_max_message(child_id, msg_late, [[cb_btn("📂 Перейти к заданиям", "child_days")]])
                ids_to_mark = [i["id"] for i in unnotified_items]
                await gas_request({"action": "mark_notified", "ids": ids_to_mark})

        await asyncio.sleep(3)


# --- ЦИКЛ ПОЛУЧЕНИЯ ОБНОВЛЕНИЙ MAX (LONG POLLING) ---

def _sync_get_updates(marker):
    params = {
        "timeout": 25,
        "types": "message_created,message_callback,bot_started"
    }
    if marker is not None:
        params["marker"] = marker

    try:
        resp = POLL_SESSION.get(f"{MAX_API_URL}/updates", headers=max_headers(), params=params, timeout=35)
        if resp.status_code == 200:
            return resp.json()
        else:
            logging.error(f"Статус ответа /updates: {resp.status_code} - {resp.text}")
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        logging.error(f"Ошибка опроса /updates: {e}")
    return None


async def poll_max_updates():
    marker = None
    logging.info("Запущен опрос событий мессенджера MAX...")

    while True:
        data = await asyncio.to_thread(_sync_get_updates, marker)
        if not data:
            await asyncio.sleep(2)
            continue

        if "marker" in data and data["marker"] is not None:
            marker = data["marker"]

        updates = data.get("updates") or []
        for upd in updates:
            u_type = upd.get("update_type")
            try:
                if u_type == "bot_started":
                    user = upd.get("user") or {}
                    uid = user.get("user_id")
                    if uid:
                        await handle_text_or_media_message({"sender": {"user_id": uid}, "body": {"text": "/start"}})
                elif u_type == "message_created":
                    msg = upd.get("message") or {}
                    await handle_text_or_media_message(msg)
                elif u_type == "message_callback":
                    await handle_callback_event(upd)
            except Exception as e:
                logging.error(f"Ошибка обработки события {u_type}: {e}")


async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(check_and_send, "cron", hour="12-20", minute=0)
    scheduler.start()

    await poll_max_updates()


if __name__ == "__main__":
    asyncio.run(main())
