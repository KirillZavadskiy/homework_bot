import logging
import os

import requests
import sys
import telegram
import tg_logger
import time

from dotenv import load_dotenv
from logging import Formatter, StreamHandler

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

logging.basicConfig(
    format='[%(asctime)s : %(levelname)s] - %(message)s',
    level=logging.DEBUG,
    filename='main.log'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(
    Formatter(fmt='[%(asctime)s : %(levelname)s] - %(message)s')
)
tg_logger.setup(logger, token=TELEGRAM_TOKEN, users=[TELEGRAM_CHAT_ID])
logger.addHandler(handler)


def check_tokens():
    '''Проверяет доступность переменных окружения.'''
    if TELEGRAM_TOKEN is None:
        logging.critical('No variable TELEGRAM_TOKEN.')
        sys.exit()
    elif PRACTICUM_TOKEN is None:
        logging.critical('No variable PRACTICUM_TOKEN.')
        sys.exit()
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('No variable TELEGRAM_CHAT_ID.')
        sys.exit()


def send_message(bot, message):
    '''Отправляет сообщение в Telegram чат.'''
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Message sent')
    except Exception as error:
        logging.error(f'Crash when sending message to Telegram: {error}')
        logger.error(f'Crash when sending message to Telegram: {error}')


def get_api_answer(timestamp):
    '''Делает запрос к эндпоинту API-сервиса.'''
    payload = {'from_date': timestamp}
    try:
        hw_status = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if hw_status.status_code != 200:
            logger.error('ENDPOINT inaccessible')
            logging.error('ENDPOINT inaccessible')
            raise ConnectionError('ENDPOINT inaccessible')
        return hw_status.json()
    except requests.RequestException:
        print('Message not sent')


def check_response(response):
    '''Проверяет ответ API на соответствие документации.'''
    if not isinstance(response, dict):
        logger.error('Tyrpe of response not dict')
        logging.error('Tyrpe of response not dict')
        raise TypeError('Tyrpe of response not dict')
    if 'homeworks' not in response:
        logger.error('No key "homeworks"')
        logging.error('No key "homeworks"')
        raise ConnectionError('No key "homeworks"')
    check_api = response['homeworks']
    if not isinstance(check_api, list):
        logging.error('Error in request API')
        logger.error('Error in request API')
        raise TypeError('Error in request API')
    logging.debug('Successful check API')
    return check_api


def parse_status(homework):
    '''Извлекает из информации о конкретной домашней работе статус работы.'''
    if 'homework_name' not in homework or 'status' not in homework:
        logging.error('Missing expected keys in API')
        logger.error('Missing expected keys in API')
        raise ConnectionError('Missing expected keys in API')
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status not in HOMEWORK_VERDICTS:
        logging.error('Unexpected status of homework')
        logger.error('Unexpected status of homework')
        raise ConnectionError('Unexpected status of homework')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Work harder')
    timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
            else:
                message = 'Статус проверки не изменился.'
            if message != last_message:
                send_message(bot, message)
                last_message = message
            else:
                logging.debug('No new statuses in response')
                time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
