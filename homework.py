import logging
import os
import sys
import time
from http import HTTPStatus
from logging import Formatter, StreamHandler

import requests
import telegram
from dotenv import load_dotenv

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


class EmptyResponseApi(Exception):
    pass


class UnexpectedStatusCode(Exception):
    pass


class NoVariableToken(Exception):
    pass


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
            logging.error('Status code not 200.OK')
            raise UnexpectedStatusCode('Status code not 200.OK')
        return hw_status.json()
    except requests.RequestException:
        logging.error('Response fail')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('Type of response not dict')
        raise TypeError('Type of response not dict')
    if 'homeworks' not in response:
        logging.error('No key "homeworks"')
        raise EmptyResponseApi('No key "homeworks"')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        logging.error('Error in request API')
        raise TypeError('Error in request API')
    logging.debug('Successful check API')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    if 'homework_name' not in homework or 'status' not in homework:
        logger.error('Missing expected keys in API')
        raise KeyError('Missing expected keys in API')
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status not in HOMEWORK_VERDICTS:
        logging.error('Unexpected status of homework')
        logger.error('Unexpected status of homework')
        raise ValueError('Unexpected status of homework')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Work harder')
    timestamp = 0
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
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
        except Exception as error:
            logging.error('Program fail')
            if message != last_message:
                message = f'Сбой в работе программы: {error}'
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
