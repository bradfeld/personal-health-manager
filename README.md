# Personal Health Manager

A Django application that integrates with various health and fitness services.

## Setup

1. Create virtual environment:

```bash
python -m venv .venv
```

2. Activate virtual environment:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run migrations:

```bash
python manage.py migrate
```

5. Run the development server:

```bash
python manage.py runserver
```

6. Access the application:

```bash
http://localhost:8000
```

7. Run Celery worker:

```bash
celery -A health_manager worker -l info
```

8. Run Celery beat:

```bash
celery -A health_manager beat -l info
```

9. Run Celery flower:

```bash
celery -A health_manager flower --port=5555 --broker=redis://localhost:6379/0                           
``` 

10. Run Redis:

```bash
redis-server
``` 

