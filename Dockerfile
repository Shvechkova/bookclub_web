# Сайт клуба в рабочем режиме: uvicorn без --reload.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Сначала только зависимости: слой пересобирается, лишь когда меняется
# pyproject.toml. Сам пакет потом снимаем — приложение ищет шаблоны, данные
# и игру относительно исходников, поэтому запускается из /srv, а не из
# site-packages.
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py \
    && pip install . \
    && pip uninstall -y bookclub-web \
    && rm -rf app build *.egg-info

COPY app/ app/
COPY data/ data/
COPY vendor/tyzharchitector/index.html vendor/tyzharchitector/style.css vendor/tyzharchitector/
COPY vendor/tyzharchitector/src/ vendor/tyzharchitector/src/

RUN useradd --system --no-create-home --uid 10001 club
USER club

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"]

CMD ["uvicorn", "app.web.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
