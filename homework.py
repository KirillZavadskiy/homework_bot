import logging
import os
import sys
import time
from http import HTTPStatus
from logging import Formatter, StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EmptyResponseApi, NoVariableToken, UnexpectedStatusCode

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_YANDEX')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(
    Formatter(
        fmt='[%(pathname)s : %(asctime)s : %(levelname)s] -'
        '%(message)s, %(module)s'
    )
)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    chek_tokens = []
    for key, value in tokens.items():
        if value is None:
            chek_tokens.append(key)
    if chek_tokens:
        logger.critical(f'No variable: {chek_tokens}')
        raise NoVariableToken(f'No variable: {chek_tokens}')
    logger.debug('Chek tokens - OK')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.debug('Start message sent')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Message sent')
    except telegram.error.TelegramError as error:
        logging.error(f'Crash when sending message to Telegram: {error}')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    payload = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logging.debug(
            'Response start'
            'url: {url},'
            'headers: {headers},'
            'params: {params}'.format(**payload)
        )
        hw_status = requests.get(**payload)
        if hw_status.status_code != HTTPStatus.OK:
            raise UnexpectedStatusCode('Status code not 200.OK')
        return hw_status.json()
    except requests.RequestException:
        raise ConnectionError('Response fail')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Type of response not dict')
    if 'homeworks' not in response:
        raise EmptyResponseApi('No key "homeworks"')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Error in request API')
    logging.debug('Successful check API')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Missing expected keys in API')
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError('Unexpected status of homework')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Статус проверки не изменился.'
            if message != last_message:
                send_message(bot, message)
                last_message = message
            else:
                logging.debug('No new statuses in response')
        except EmptyResponseApi:
            logger.error('Response API is empty')
        except Exception as error:
            logger.error('Program fail')
            message = f'Сбой в работе программы: {error}'
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s : %(levelname)s] - %(message)s',
        level=logging.DEBUG,
        filename='main.log'
    )
    main()
