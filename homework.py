from http import HTTPStatus
import logging
import os
import sys
import time

import requests
import telegram.error
from dotenv import load_dotenv
from telegram import Bot

from exceptions import AccessError, EmptyResponseFromAPI

load_dotenv()

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
    # не понял как получить имя переменной, поэтому сделал словарь
    env_variables = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID
    }
    variables_exist = True
    for name, variable in env_variables.items():
        if not variable:
            logging.critical(f'Отсутствует переменная окружения'
                             f' {name}.')
            variables_exist = False
    return variables_exist


def send_message(bot, message):
    """Отправка сообщений посредством бота."""
    chat_id = TELEGRAM_CHAT_ID
    try:
        logger.debug(f'Отправляем сообщение "{message}".')
        bot.send_message(chat_id, message)
    except telegram.error.TelegramError as error:
        logger.error(f'Сообщение для id {chat_id}'
                     f' не было доставлено. {error}')
        return False
    else:
        logger.debug(f'Сообщение "{message}" было успешно отправлено.')
        return True


def get_api_answer(timestamp):
    """Получение данных от api."""
    payload = {'from_date': timestamp}
    request_args = {
        'url': ENDPOINT,
        'params': payload,
        'headers': HEADERS,
    }
    logger.debug(
        'Начали запрос с аргументами '
        'url={0}, params={1}, headers={2}'.format(
            *request_args.values()
        ))
    try:
        homework_statuses = requests.get(**request_args)
    except Exception as error:
        # logger.exception(f'Эндпоинт не доступен. {error}')
        raise ConnectionError('Эндпоинт не доступен.'
                              ' url={0}, params={1}, headers={2}'
                              .format(*request_args.values()))
    if homework_statuses.status_code != HTTPStatus.OK:
        error_msg = (f"Ошибка. Код -{homework_statuses.status_code}, "
                     f"Причина - {homework_statuses.reason}"
                     f"Текст - {homework_statuses.text}")
        logger.error(error_msg)
        raise AccessError(error_msg)
    return homework_statuses.json()


def check_response(response):
    """Проверка изменения запроса."""
    if not isinstance(response, dict):
        raise TypeError(f'Тип {type(response)} не соответствует'
                        f' ожидаемому {type(dict())}')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(f'Тип {type(response)} не соответствует'
                        f' ожидаемому {type(list())})')
    if len(homeworks) > 0 and homeworks[0].get('homework_name') is None:
        raise EmptyResponseFromAPI(f'Поле homework_name отсутствует.')
    return homeworks


def parse_status(homework):
    """Получение статуса проверки домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Отсутствует ключ homework_name')
    if homework.get('status') not in HOMEWORK_VERDICTS:
        raise ValueError(f"Неожиданный статус {homework.get('status')}")
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    assert check_tokens()

    timestamp = 0
    bot = Bot(token=TELEGRAM_TOKEN)

    HOMEWORK_INDEX = 0

    current_report = {
        'name': 'name',
        'message': 'messages'
    }
    prev_report = {
        'name': '',
        'message': ''
    }

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                current_report['name'] = homework.get('homework_name')
                current_report['message'] = parse_status(homework)
            else:
                current_report['message'] = 'Нет новых статусов.'
            if current_report != prev_report:
                assert send_message(bot, current_report.get('message'))
                prev_report = current_report.copy()
                timestamp = response.get('current_date')
            else:
                logger.info('Нет новых статусов.')
        except EmptyResponseFromAPI as error:
            logger.exception('Необходимое поле отсутствует.')
        except Exception as error:
            error_msg = f'Произошла непредвиденная ошибка. {error}'
            current_report['message'] = error_msg
            logger.exception(error_msg)
            if current_report != prev_report:
                assert send_message(bot, error_msg)
                prev_report = current_report.copy()
            return
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    file_handler = logging.FileHandler(f'{__file__[:__file__.find(".")]}.log')
    format = ('(%(asctime)s | %(funcName)s | '
              '%(lineno)d) - [%(levelname)s]'
              ' - %(message)s')
    stream_handler.setFormatter(logging.Formatter(fmt=format))
    file_handler.setFormatter(logging.Formatter(fmt=format))
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    main()
