class EmptyResponseApi(Exception):
    """Пустой ответ АПИ."""

    pass


class UnexpectedStatusCode(Exception):
    """Неожиданный статус-код."""

    pass


class NoVariableToken(Exception):
    """Отсутствуют переменные окружения."""

    pass
