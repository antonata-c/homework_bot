import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from telegram import Bot
from http import HTTPStatus

from exceptions import StatusError, AccessError, TokenError, FieldError

FieldError

load_dotenv()

handler = logging.StreamHandler(stream=sys.stdout)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=(handler,),
)

logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных окружения."""
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        error_msg = 'Отсутствуют необходимые переменные окружения.'
        logging.critical(error_msg)
        raise TokenError(error_msg)


def send_message(bot, message):
    """Отправка сообщений посредством бота."""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    try:
        bot.send_message(chat_id, message)
    except Exception:
        logger.exception(f'Сообщение для id {chat_id} не было доставлено.')
    else:
        logger.debug('Сообщение было успешно отправлено.')


def get_api_answer(timestamp):
    """Получение данных от api."""
    url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    practicum_token = os.getenv('PRACTICUM_TOKEN')
    headers = {'Authorization': f'OAuth {practicum_token}'}
    payload = {'from_date': timestamp}

    try:
        homework_statuses = requests.get(url,
                                         headers=headers,
                                         params=payload)
    except Exception:
        logger.exception('Эндпоинт не доступен.')
    else:
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        else:
            error_msg = (f"Вернулся код {homework_statuses.status_code}, "
                         "ошибка")
            logger.error(error_msg)
            raise AccessError(error_msg)


def check_response(response):
    """Проверка изменения запроса."""
    fields = ['homeworks', 'current_date']
    if not isinstance(response, dict):
        logger.error(f'Тип {type(response)} не соответствует'
                     f' ожидаемому {type(dict())}')
        raise TypeError('Ответ должен быть словарем.')
    elif not isinstance(response.get('homeworks'), list):
        logger.error(f'Тип {type(response)} не соответствует'
                     f' ожидаемому {type(list())})')
        raise TypeError('Домашние задания должны быть списком.')
    else:
        for field in fields:
            if response.get(field) is None:
                error_msg = f'Поле {field} отсутствует.'
                logger.error(error_msg)
                raise FieldError(error_msg)


def parse_status(homework):
    """Получение статуса проверки домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        error_msg = 'Отсутствует ключ homework_name'
        logger.error(error_msg)
        raise KeyError(error_msg)
    if homework.get('status') not in HOMEWORK_VERDICTS:
        error_msg = f"Неожиданный статус {homework.get('status')}"
        logger.error(error_msg)
        raise StatusError(error_msg)
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)

    HOMEWORK_INDEX = 0

    statuses = []

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            status = parse_status(response.get('homeworks')
                                  [HOMEWORK_INDEX])
            if status not in statuses:
                statuses.append(status)
                send_message(bot, status)
        except TypeError as error:
            send_message(bot, error)
            return
        except StatusError as error:
            send_message(bot, error)
            return
        except KeyError as error:
            send_message(bot, error)
            return
        except Exception:
            logger.exception('Произошла непредвиденная ошибка.')
            return
        else:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
