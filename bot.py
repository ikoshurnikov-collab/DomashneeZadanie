import ast
import asyncio
import html
import json
import logging
import os
import re
import time
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

DATA_DIR = os.getenv("DATA_DIR", ".")
CACHE_FILE = os.path.join(DATA_DIR, "hw_cache.json")
STATES_FILE = os.path.join(DATA_DIR, "user_states.json")

POLL_SESSION = requests.Session()
GAS_LOCK = asyncio.Lock()

# ID пользователей в MAX
ID_IGOR = 11423510
ID_KATYA = 169993452
ID_GRANDMA = 221597034
ID_OLYA = 62297217

ID_KIRILL = 207924440
ID_NIKITA = 200548363
ID_ANYA = int(os.getenv("ID_ANYA", "0"))
ID_NASTYA = int(os.getenv("ID_NASTYA", "0"))

ADULT_ACCESS = {
    ID_IGOR: ["Кирилла", "Никиты", "Ани", "Насти"],
    ID_KATYA: ["Кирилла", "Никиты"],
    ID_GRANDMA: ["Кирилла", "Никиты"],
    ID_OLYA: ["Ани", "Насти"]
}

ADULT_GREETINGS = {
    ID_IGOR: "Привет, Игорь! 🫡 Главный пульт управления школой на связи. Кого проверяем?",
    ID_KATYA: "Привет, Катюша! 🌸 Заглянем в дневники наших парней? Выбирай нужный раздел:",
    ID_GRANDMA: "Здравствуйте, бабушка Наташа! 🌺 Спасибо за вашу заботу и помощь с уроками! Выберите, что хотите посмотреть:",
    ID_OLYA: "Привет, Оля! ☀️ Дневники девчонок под контролем. Выбирай раздел:"
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
        "child_greeting": "Привет, Никита! ⚡️ Время включить суперсилу и разделаться с домашкой! Выбирай день:",
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

HW_CACHE = {}
USER_STATES = {}


# --- ЛОКАЛЬНЫЙ КЭШ НА ДИСКЕ ---

def load_local_data():
    global HW_CACHE, USER_STATES
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                HW_CACHE = json.load(f)
            logging.info(f"Загружен локальный кэш ДЗ: {len(HW_CACHE)} записей")
        if os.path.exists(STATES_FILE):
            with open(STATES_FILE, "r", encoding="utf-8") as f:
                raw_states = json.load(f)
                USER_STATES = {int(k): v for k, v in raw_states.items()}
    except Exception as e:
        logging.error(f"Ошибка чтения локального кэша: {e}")


def save_hw_cache():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp_path = CACHE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(HW_CACHE, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, CACHE_FILE)
    except Exception as e:
        logging.error(f"Ошибка сохранения кэша ДЗ: {e}")


def save_user_states():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp_path = STATES_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in USER_STATES.items()}, f, ensure_ascii=False)
        os.replace(tmp_path, STATES_FILE)
    except Exception as e:
        logging.error(f"Ошибка сохранения состояний: {e}")


def set_user_state(user_id: int, state_dict: dict):
    USER_STATES[user_id] = state_dict
    save_user_states()


def pop_user_state(user_id: int):
    val = USER_STATES.pop(user_id, None)
    if val is not None:
        save_user_states()
    return val


def merge_avers_into_cache(student_name: str, hw_list: list):
    changed = False
    for h in hw_list:
        hid = h["id"]
        if hid not in HW_CACHE:
            HW_CACHE[hid] = {
                "id": hid,
                "student": student_name,
                "given_date": h["given_date"],
                "due_date": h["due_date"],
                "subject": h["subject"],
                "text": h["text"],
                "status": "new",
                "notified_child": "no",
                "photos": "",
                "comment": ""
            }
            changed = True
        else:
            existing = HW_CACHE[hid]
            if existing.get("text") != h["text"] or existing.get("due_date") != h["due_date"]:
                if existing.get("text") != h["text"]:
                    existing["notified_child"] = "no"
                existing["text"] = h["text"]
                existing["due_date"] = h["due_date"]
                changed = True
    if changed:
        save_hw_cache()


def merge_gas_items_into_cache(items: list):
    if not items:
        return
    for item in items:
        hid = item.get("id")
        if hid:
            HW_CACHE[hid] = item
    save_hw_cache()


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


def split_html_text(text: str, max_len: int = 3800) -> list:
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
                current = ""
            if len(block) <= max_len:
                current = block
            else:
                for line in block.split("\n"):
                    line_cand = f"{current}\n{line}" if current else line
                    if len(line_cand) <= max_len:
                        current = line_cand
                    else:
                        if current:
                            chunks.append(current)
                        while len(line) > max_len:
                            chunks.append(line[:max_len])
                            line = line[max_len:]
                        current = line
    if current:
        chunks.append(current)
    return chunks


def _post_max_raw(user_id: int, body: dict):
    return requests.post(
        f"{MAX_API_URL}/messages",
        params={"user_id": user_id},
        headers=max_headers(),
        json=body,
        timeout=20
    )


def _reupload_media_from_url(media_url: str, media_type: str):
    if not media_url:
        return None
    try:
        file_resp = requests.get(media_url, timeout=20)
        if file_resp.status_code != 200:
            logging.error(f"Не удалось скачать файл для перезагрузки ({file_resp.status_code})")
            return None

        up_type = "image" if media_type == "image" else ("audio" if media_type == "audio" else "file")
        init_resp = requests.post(
            f"{MAX_API_URL}/uploads",
            params={"type": up_type},
            headers={"Authorization": BOT_TOKEN},
            timeout=15
        )
        if init_resp.status_code != 200:
            logging.error(f"Ошибка POST /uploads ({init_resp.status_code}): {init_resp.text}")
            return None

        init_data = init_resp.json()
        upload_url = init_data.get("url")
        pre_token = init_data.get("token")
        if not upload_url:
            return None

        ext = "jpg" if up_type == "image" else ("mp3" if up_type == "audio" else "bin")
        mime = file_resp.headers.get("Content-Type", "application/octet-stream")
        up_resp = requests.post(
            upload_url,
            files={"data": (f"upload.{ext}", file_resp.content, mime)},
            timeout=30
        )
        if up_resp.status_code != 200:
            logging.error(f"Ошибка загрузки файла на CDN MAX ({up_resp.status_code}): {up_resp.text}")
            return None

        if up_type == "audio" and pre_token:
            return {"type": "audio", "payload": {"token": pre_token}}

        up_json = up_resp.json()
        return {"type": up_type, "payload": up_json}
    except Exception as e:
        logging.error(f"Ошибка перезагрузки вложения в MAX: {e}")
        return None


def _send_with_attachment_retry(user_id: int, body: dict) -> bool:
    for attempt in range(3):
        resp = _post_max_raw(user_id, body)
        if resp.status_code == 200:
            return True
        if "attachment.not.ready" in resp.text and attempt < 2:
            time.sleep(1.5 * (attempt + 1))
            continue
        logging.warning(f"MAX отклонил отправку ({resp.status_code}) для {user_id}: {resp.text}")
        return False
    return False


def _sync_send_message(user_id: int, text: str, buttons=None, media_items=None) -> bool:
    chunks = split_html_text(text, max_len=3800)

    try:
        # Отправляем все промежуточные части длинного текста без кнопок
        for part in chunks[:-1]:
            resp = _post_max_raw(user_id, {"text": part, "format": "html"})
            if resp.status_code != 200:
                logging.error(f"Ошибка отправки части сообщения пользователю {user_id} ({resp.status_code}): {resp.text}")

        last_text = chunks[-1]

        # Обычное сообщение без медиафайлов
        if not media_items:
            body = {"text": last_text, "format": "html"}
            if buttons:
                body["attachments"] = [make_keyboard(buttons)]
            resp = _post_max_raw(user_id, body)
            if resp.status_code != 200:
                logging.error(f"Ошибка отправки сообщения пользователю {user_id} ({resp.status_code}): {resp.text}")
                return False
            return True

        # Нормализация списка медиавложений
        normalized = []
        for m in media_items[:11]:
            if isinstance(m, str):
                normalized.append({"type": "image", "token": m, "url": ""})
            elif isinstance(m, dict):
                normalized.append({
                    "type": m.get("type", "image"),
                    "token": m.get("token", ""),
                    "url": m.get("url", "")
                })

        # Попытка 1: отправка по токену вложения
        token_atts = [{"type": m["type"], "payload": {"token": m["token"]}} for m in normalized if m.get("token")]
        if token_atts:
            atts = list(token_atts) + ([make_keyboard(buttons)] if buttons else [])
            if _send_with_attachment_retry(user_id, {"text": last_text, "format": "html", "attachments": atts}):
                return True
            if buttons:
                if _send_with_attachment_retry(user_id, {"text": last_text, "format": "html", "attachments": token_atts}):
                    _post_max_raw(user_id, {"text": "Выберите действие 👇", "format": "html", "attachments": [make_keyboard(buttons)]})
                    return True

        # Попытка 2: отправка изображений напрямую по URL
        url_atts = [{"type": "image", "payload": {"url": m["url"]}} for m in normalized if m["type"] == "image" and m.get("url")]
        if url_atts and len(url_atts) == len(normalized):
            atts = list(url_atts) + ([make_keyboard(buttons)] if buttons else [])
            if _send_with_attachment_retry(user_id, {"text": last_text, "format": "html", "attachments": atts}):
                return True

        # Попытка 3: перезагрузка медиафайлов от имени самого бота через POST /uploads
        reuploaded_atts = []
        for m in normalized:
            re_att = _reupload_media_from_url(m.get("url", ""), m["type"])
            if re_att:
                reuploaded_atts.append(re_att)

        if reuploaded_atts:
            time.sleep(1.0)
            atts = list(reuploaded_atts) + ([make_keyboard(buttons)] if buttons else [])
            if _send_with_attachment_retry(user_id, {"text": last_text, "format": "html", "attachments": atts}):
                return True
            if buttons:
                if _send_with_attachment_retry(user_id, {"text": last_text, "format": "html", "attachments": reuploaded_atts}):
                    _post_max_raw(user_id, {"text": "Выберите действие 👇", "format": "html", "attachments": [make_keyboard(buttons)]})
                    return True

        logging.error(f"Не удалось доставить медиавложения пользователю {user_id} ни одним из способов")
        return False

    except Exception as e:
        logging.error(f"Исключение при отправке в MAX пользователю {user_id}: {e}")
        return False


async def send_max_message(user_id: int, text: str, buttons=None, extra_attachments=None) -> bool:
    return await asyncio.to_thread(_sync_send_message, user_id, text, buttons, extra_attachments)


def _sync_answer_callback(callback_id: str, user_id: int = None, text: str = None, buttons=None, notification: str = None):
    body = {}
    if notification:
        body["notification"] = notification
    if text is not None:
        safe_text = text if len(text) <= 3900 else (text[:3890] + "...")
        body["message"] = {
            "text": safe_text,
            "format": "html",
            "attachments": [make_keyboard(buttons)] if buttons else []
        }

    try:
        resp = requests.post(
            f"{MAX_API_URL}/answers",
            params={"callback_id": callback_id},
            headers=max_headers(),
            json=body,
            timeout=15
        )
        if resp.status_code != 200:
            logging.warning(f"MAX /answers вернул {resp.status_code}: {resp.text}")
            if text is not None and user_id:
                _sync_send_message(user_id, text, buttons=buttons)
    except Exception as e:
        logging.error(f"Ошибка ответа на callback в MAX: {e}")
        if text is not None and user_id:
            _sync_send_message(user_id, text, buttons=buttons)


async def answer_max_callback(callback_id: str, user_id: int = None, text: str = None, buttons=None, notification: str = None):
    await asyncio.to_thread(_sync_answer_callback, callback_id, user_id, text, buttons, notification)


# --- РАБОТА С GOOGLE ТАБЛИЦЕЙ (APPS SCRIPT) ---

def _sync_gas_request(payload: dict, retries: int = 2):
    req_data = dict(payload)
    if GAS_SECRET:
        req_data["secret"] = GAS_SECRET

    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                GAS_URL,
                json=req_data,
                headers={"Connection": "close"},
                timeout=(8, 15)
            )
            if resp.status_code == 200:
                return resp.json()
            logging.error(f"Ошибка HTTP от Google Таблицы: {resp.status_code} (попытка {attempt + 1})")
        except Exception as e:
            logging.warning(f"Сбой связи с Google Таблицей (попытка {attempt + 1}/{retries + 1}): {e}")
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    return None


async def gas_request(payload: dict, retries: int = 2):
    async with GAS_LOCK:
        return await asyncio.to_thread(_sync_gas_request, payload, retries)


async def refresh_hw_cache_from_gas():
    res = await gas_request({"action": "get_hw"}, retries=2)
    if res and res.get("status") == "ok":
        merge_gas_items_into_cache(res.get("items", []))
        return True
    return False


async def bg_update_gas_status(hw_id: str, status: str = None, photos: str = None, comment: str = None):
    payload = {"action": "update_status", "id": hw_id}
    if status is not None:
        payload["status"] = status
    if photos is not None:
        payload["photos"] = photos
    if comment is not None:
        payload["comment"] = comment
    await gas_request(payload, retries=3)


async def bg_sync_student_to_gas(student_name: str, hw_list: list, grades_list: list):
    await gas_request({
        "action": "sync",
        "student": student_name,
        "hw_list": hw_list,
        "grades_list": grades_list
    }, retries=2)


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
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "close"
    }

    response = None
    for attempt in range(2):
        try:
            response = requests.post(DATA_URL, data=payload_data, headers=headers, timeout=15)
            if response.status_code == 200:
                break
            if attempt == 0 and response.status_code >= 500:
                time.sleep(2)
                continue
        except requests.exceptions.RequestException as e:
            logging.error(f"Сетевая ошибка Аверс ({student_name}): {e}")
            if attempt == 0:
                time.sleep(2)
                continue
            return None

    if not response or response.status_code != 200 or "login" in response.url.lower():
        code = response.status_code if response else "no_response"
        url_info = response.url if response else DATA_URL
        logging.error(f"Ошибка доступа к Аверс ({student_name}): статус {code}, URL {url_info}")
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


# --- ДЕТСКОЕ МЕНЮ (МГНОВЕННАЯ РАБОТА ИЗ КЭША) ---

async def get_active_child_hw(student_name: str):
    if not HW_CACHE:
        await refresh_hw_cache_from_gas()

    student_items = [v for v in HW_CACHE.values() if v.get("student") == student_name]
    if not student_items:
        parsed = await fetch_avers(student_name)
        if parsed:
            hw_list, grades_list = parsed
            merge_avers_into_cache(student_name, hw_list)
            asyncio.create_task(bg_sync_student_to_gas(student_name, hw_list, grades_list))
            student_items = [v for v in HW_CACHE.values() if v.get("student") == student_name]

    today = datetime.now(MOSCOW_TZ).date()
    active = []
    for item in student_items:
        status = item.get("status", "new")
        if status not in ("new", "revision"):
            continue

        due_str = item.get("due_date", "")
        try:
            due_dt = datetime.strptime(due_str, "%d.%m.%Y").date()
            if due_dt >= today or status == "revision":
                active.append(item)
        except ValueError:
            if status == "revision" or is_recent_date(item.get("given_date", ""), max_days=14):
                active.append(item)

    return active


async def get_hw_item_fast(hw_id: str):
    if hw_id in HW_CACHE:
        return HW_CACHE[hw_id]
    res = await gas_request({"action": "get_item", "id": hw_id}, retries=1)
    if res and res.get("status") == "ok" and res.get("item"):
        HW_CACHE[hw_id] = res["item"]
        save_hw_cache()
        return res["item"]
    return None


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
    item = await get_hw_item_fast(hw_id)
    if not item:
        return "😕 Задание не найдено.", [[cb_btn("⬅️ К списку дней", "child_days")]]

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

    if text.lower() in ("/start", "старт", "меню", "отмена"):
        pop_user_state(user_id)

    # 1. Проверка активных состояний
    if user_id in USER_STATES:
        state_data = USER_STATES[user_id]
        st_type = state_data.get("state")

        # Сценарий: ребенок загружает фотографии выполненной домашки
        if st_type == "waiting_hw_photos":
            hw_id = state_data["hw_id"]
            found_media = []
            for att in attachments:
                att_type = att.get("type")
                pl = att.get("payload") or {}
                if att_type in ("image", "file") and (pl.get("token") or pl.get("url")):
                    found_media.append({
                        "type": att_type,
                        "token": pl.get("token", ""),
                        "url": pl.get("url", "")
                    })

            if found_media:
                state_data["photos"].extend(found_media)
                save_user_states()
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
                att_type = att.get("type")
                pl = att.get("payload") or {}
                if att_type in ("audio", "file", "image", "video") and (pl.get("token") or pl.get("url")):
                    media_to_forward.append({
                        "type": att_type,
                        "token": pl.get("token", ""),
                        "url": pl.get("url", "")
                    })

            if not text and not media_to_forward:
                await send_max_message(
                    user_id,
                    "✍️ Пожалуйста, напишите текст замечания или запишите голосовое сообщение в чат:",
                    [[cb_btn("❌ Отмена", f"gm_cancel:{hw_id}")]]
                )
                return

            item = await get_hw_item_fast(hw_id)
            if not item:
                await send_max_message(user_id, "⚠️ Не удалось найти задание. Попробуйте снова.")
                return

            comment_for_sheet = text if text else "🎤 Голосовое сообщение от бабушки"
            item["status"] = "revision"
            item["comment"] = comment_for_sheet
            HW_CACHE[hw_id] = item
            save_hw_cache()
            pop_user_state(user_id)

            asyncio.create_task(bg_update_gas_status(hw_id, status="revision", comment=comment_for_sheet))

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
            save_user_states()
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
            pop_user_state(user_id)

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
        has_photo = any(att.get("type") in ("image", "file") for att in attachments)
        msg_text, buttons = await build_child_days_view(child_student)
        if has_photo:
            msg_text = (
                "📸 Вижу фотографию! Чтобы сдать домашку бабушке на проверку, сначала выбери ниже день "
                "и предмет, а внутри него нажми кнопку <b>«Я завершил!»</b> 👇"
            )
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
            pop_user_state(user_id)
            text, buttons = await build_child_days_view(child_student)
            await answer_max_callback(callback_id, user_id=user_id, text=text, buttons=buttons)
            return

        if payload.startswith("c_day:"):
            pop_user_state(user_id)
            due_date = payload.split(":", 1)[1]
            text, buttons = await build_child_subjects_view(child_student, due_date)
            await answer_max_callback(callback_id, user_id=user_id, text=text, buttons=buttons)
            return

        if payload.startswith("c_hw:"):
            pop_user_state(user_id)
            hw_id = payload.split(":", 1)[1]
            text, buttons = await build_child_item_view(child_student, hw_id)
            await answer_max_callback(callback_id, user_id=user_id, text=text, buttons=buttons)
            return

        if payload.startswith("c_done:"):
            hw_id = payload.split(":", 1)[1]
            set_user_state(user_id, {
                "state": "waiting_hw_photos",
                "hw_id": hw_id,
                "photos": []
            })
            prompt_text = (
                f"📸 Ну-ка, {child_nom}, подгрузи выполненную домашку!\n"
                f"Сфотографируй тетрадь и отправь фото в этот чат (можно несколько страниц подряд).\n\n"
                f"Когда загрузишь все страницы, нажми кнопку отправки на проверку 👇"
            )
            await answer_max_callback(callback_id, user_id=user_id, text=prompt_text, buttons=[[cb_btn("❌ Отмена", f"c_hw:{hw_id}")]])
            return

        if payload.startswith("c_submit:"):
            hw_id = payload.split(":", 1)[1]
            st_data = USER_STATES.get(user_id)

            if not st_data or st_data.get("state") != "waiting_hw_photos" or st_data.get("hw_id") != hw_id:
                text, buttons = await build_child_days_view(child_student)
                await answer_max_callback(
                    callback_id,
                    user_id=user_id,
                    text=text,
                    buttons=buttons,
                    notification="ℹ️ Это задание уже отправлено на проверку!"
                )
                return

            photos = st_data.get("photos", [])
            if not photos:
                await answer_max_callback(callback_id, user_id=user_id, notification="📷 Сначала отправь хотя бы одно фото тетради!")
                return

            item = await get_hw_item_fast(hw_id)
            if not item:
                await answer_max_callback(
                    callback_id,
                    user_id=user_id,
                    text="⚠️ Не удалось найти карточку задания. Попробуй открыть предмет заново.",
                    buttons=[[cb_btn("📚 К списку дней", "child_days")]]
                )
                return

            # Сначала отправляем фотографии бабушке Наташе, не стирая их из памяти заранее
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
                gm_buttons = [[
                    cb_btn("✅ Подтвердить", f"gm_ok:{hw_id}"),
                    cb_btn("✏️ На доработку", f"gm_rev:{hw_id}")
                ]]
                sent_ok = await send_max_message(reviewer_id, gm_text, gm_buttons, extra_attachments=photos)
                if not sent_ok:
                    await answer_max_callback(
                        callback_id,
                        user_id=user_id,
                        text="⚠️ Связь на секунду моргнула, фотографии сохранены. Нажми кнопку отправки еще раз 👇",
                        buttons=[
                            [cb_btn(f"🚀 Повторить отправку ({len(photos)} фото)", f"c_submit:{hw_id}")],
                            [cb_btn("❌ Отмена", f"c_hw:{hw_id}")]
                        ]
                    )
                    return

            # Фиксируем сдачу в локальном кэше и очищаем состояние только после доставки
            pop_user_state(user_id)
            photos_tokens = [p["token"] if isinstance(p, dict) else str(p) for p in photos]
            photos_json = json.dumps(photos_tokens, ensure_ascii=False)
            item["status"] = "pending"
            item["photos"] = photos_json
            HW_CACHE[hw_id] = item
            save_hw_cache()

            asyncio.create_task(bg_update_gas_status(hw_id, status="pending", photos=photos_json))

            praise_word = "Умница" if is_female else "Красавчик"
            await answer_max_callback(
                callback_id,
                user_id=user_id,
                text=(
                    f"🎉 {praise_word}, {child_nom}! Домашка по предмету <b>{item['subject']}</b> "
                    f"улетела бабушке Наташе на проверку. Ждем результат! 🤞"
                ),
                buttons=[[cb_btn("📚 К остальным заданиям", "child_days")]]
            )
            return

    # --- НАВИГАЦИЯ ВЗРОСЛЫХ И ПРОВЕРКА БАБУШКОЙ ---
    if user_id in ADULT_ACCESS:
        if payload == "adult_menu":
            pop_user_state(user_id)
            text, buttons = build_adult_main_menu(user_id)
            await answer_max_callback(callback_id, user_id=user_id, text=text, buttons=buttons)
            return

        if payload.startswith("gm_ok:"):
            hw_id = payload.split(":", 1)[1]
            item = await get_hw_item_fast(hw_id)
            if not item:
                await answer_max_callback(callback_id, user_id=user_id, notification="⚠️ Задание не найдено")
                return

            item["status"] = "done"
            HW_CACHE[hw_id] = item
            save_hw_cache()
            asyncio.create_task(bg_update_gas_status(hw_id, status="done"))

            s_name = item["student"]
            s_info = STUDENTS.get(s_name, {})
            child_nom = s_info.get("nominative", "Ребенок")
            champ_word = "чемпионка" if s_info.get("gender") == "f" else "чемпион"

            await answer_max_callback(
                callback_id,
                user_id=user_id,
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
            set_user_state(user_id, {"state": "waiting_gm_comment", "hw_id": hw_id})
            await answer_max_callback(
                callback_id,
                user_id=user_id,
                text=(
                    "✍️ Бабушка Наташа, напишите текстом или отправьте голосовое сообщение в этот чат: "
                    "подскажите, что именно нужно исправить или доделать 👇"
                ),
                buttons=[[cb_btn("❌ Отмена", f"gm_cancel:{hw_id}")]]
            )
            return

        if payload.startswith("gm_cancel:"):
            pop_user_state(user_id)
            text, buttons = build_adult_main_menu(user_id)
            await answer_max_callback(callback_id, user_id=user_id, text=text, buttons=buttons)
            return

        if payload.startswith("a_hw:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            await answer_max_callback(callback_id, user_id=user_id, notification=f"⏳ Загружаю ДЗ ({student_name})...")

            today_start = datetime.now(MOSCOW_TZ).replace(tzinfo=None)
            week_start = (today_start - timedelta(days=today_start.weekday())).date()

            parsed = await fetch_avers(student_name)
            title_prefix = f"📚 Текущие задания ({student_name}):"

            if parsed:
                hw_list, grades_list = parsed
                merge_avers_into_cache(student_name, hw_list)
                asyncio.create_task(bg_sync_student_to_gas(student_name, hw_list, grades_list))
                source_items = [HW_CACHE.get(h["id"], h) for h in hw_list]
            else:
                # Если школьный сайт выдал 502, отдаем задания из локального кэша
                source_items = [v for v in HW_CACHE.values() if v.get("student") == student_name]
                if not source_items:
                    await send_max_message(user_id, "😕 Школьный дневник временно недоступен (ошибка сервера школы).", build_adult_main_menu(user_id)[1])
                    return
                title_prefix = f"⚠️ Дневник временно недоступен, сохраненные задания ({student_name}):"

            filtered_hw = []
            for h in source_items:
                item_copy = dict(h)
                item_copy["status"] = HW_CACHE.get(h["id"], {}).get("status", h.get("status", "new"))
                try:
                    g_dt = datetime.strptime(item_copy["given_date"], "%d.%m.%Y").date()
                    d_dt = datetime.strptime(item_copy["due_date"], "%d.%m.%Y").date()
                    if g_dt >= week_start or d_dt >= week_start:
                        filtered_hw.append(item_copy)
                except ValueError:
                    if is_recent_date(item_copy.get("given_date", ""), max_days=14):
                        filtered_hw.append(item_copy)

            show_st = STUDENTS[student_name].get("can_submit", False)
            if not filtered_hw:
                await send_max_message(
                    user_id,
                    f"📭 Заданий на текущую неделю для {student_name} пока нет.",
                    build_adult_main_menu(user_id)[1]
                )
            else:
                report = format_hw_message(filtered_hw, title_prefix, show_status=show_st)
                await send_max_message(user_id, report, build_adult_main_menu(user_id)[1])
            return

        if payload.startswith("a_gr:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            text, buttons = build_adult_grades_menu(student_name)
            await answer_max_callback(callback_id, user_id=user_id, text=text, buttons=buttons)
            return

        if payload.startswith("a_gr_week:"):
            student_name = payload.split(":", 1)[1]
            if student_name not in ADULT_ACCESS[user_id]:
                return
            await answer_max_callback(callback_id, user_id=user_id, notification=f"⏳ Загружаю оценки ({student_name})...")

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
            set_user_state(user_id, {"state": "waiting_start_date", "student_name": student_name})
            await answer_max_callback(
                callback_id,
                user_id=user_id,
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
        merge_avers_into_cache(student_name, hw_list)

        sync_res = await gas_request({
            "action": "sync",
            "student": student_name,
            "hw_list": hw_list,
            "grades_list": grades_list
        }, retries=2)

        new_hw = []
        new_grades = []
        if sync_res and sync_res.get("status") == "ok":
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

        # 2. Детям уведомления уходят начиная с 14:00
        child_id = student_data.get("child_user_id")
        if child_id and current_hour >= 14:
            unnotified_items = [
                v for v in HW_CACHE.values()
                if v.get("student") == student_name and v.get("notified_child") == "no"
            ]

            if current_hour == 14:
                active_items = await get_active_child_hw(student_name)
                if unnotified_items:
                    msg_14 = (
                        f"🐦 Чирик, котик линтеха! {child_nom}, тебе пришла новая домашка, "
                        f"приступишь к выполнению? 💪✨"
                    )
                    if await send_max_message(child_id, msg_14, [[cb_btn("🚀 Перейти к заданиям", "child_days")]]):
                        ids_to_mark = [i["id"] for i in unnotified_items]
                        for hid in ids_to_mark:
                            if hid in HW_CACHE:
                                HW_CACHE[hid]["notified_child"] = "yes"
                        save_hw_cache()
                        asyncio.create_task(gas_request({"action": "mark_notified", "ids": ids_to_mark}, retries=2))
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
                if await send_max_message(child_id, msg_late, [[cb_btn("📂 Перейти к заданиям", "child_days")]]):
                    ids_to_mark = [i["id"] for i in unnotified_items]
                    for hid in ids_to_mark:
                        if hid in HW_CACHE:
                            HW_CACHE[hid]["notified_child"] = "yes"
                    save_hw_cache()
                    asyncio.create_task(gas_request({"action": "mark_notified", "ids": ids_to_mark}, retries=2))

        await asyncio.sleep(2)

    await refresh_hw_cache_from_gas()


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
        logging.error(f"Статус ответа /updates: {resp.status_code} - {resp.text}")
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        logging.error(f"Ошибка опроса /updates: {e}")
    return None


async def _safe_dispatch(coro, u_type: str):
    try:
        await coro
    except Exception as e:
        logging.error(f"Ошибка обработки события {u_type}: {e}")


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
            if u_type == "bot_started":
                user = upd.get("user") or {}
                uid = user.get("user_id")
                if uid:
                    asyncio.create_task(_safe_dispatch(
                        handle_text_or_media_message({"sender": {"user_id": uid}, "body": {"text": "/start"}}),
                        u_type
                    ))
            elif u_type == "message_created":
                msg = upd.get("message") or {}
                asyncio.create_task(_safe_dispatch(handle_text_or_media_message(msg), u_type))
            elif u_type == "message_callback":
                asyncio.create_task(_safe_dispatch(handle_callback_event(upd), u_type))


async def main():
    load_local_data()
    asyncio.create_task(refresh_hw_cache_from_gas())

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(check_and_send, "cron", hour="12-20", minute=0)
    scheduler.start()

    await poll_max_updates()


if __name__ == "__main__":
    asyncio.run(main())
