"""Точка входа для рабочего режима.

    uvicorn app.web.asgi:app --host 0.0.0.0 --port 8000

Путь к файлу данных берётся из переменной `CLUB_DATA`, по умолчанию —
`data/club.yaml`. Если данные не проходят проверку, приложение не поднимается:
лучше явная ошибка при старте, чем страница, где половина блоков молча пуста.
"""

import os

from app.web import seo
from app.web.app import create_app

# Коды подтверждения прав в поисковиках — те же переменные, что у выгрузки.
app = create_app(verification=seo.verification_from_env(os.environ))
