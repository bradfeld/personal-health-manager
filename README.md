# Personal Health Manager

A Django application that integrates with various health and fitness services.

## Setup

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

python manage.py migrate

python manage.py runserver

http://localhost:8000

celery -A health_manager worker -l info

celery -A health_manager beat -l info

celery -A health_manager flower --port=5555 --broker=redis://localhost:6379/0                           

redis-server

ngrok http 8000
