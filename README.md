# Personal Health Manager

A Django application to track and visualize health data from Strava and Whoop.

## Features

- Integration with Strava for activity tracking
- Integration with Whoop for health metrics
- Monthly view of activities and health metrics
- Automatic data synchronization

## Deployment on Render

This application is configured for easy deployment on Render.

### One-Click Deployment

1. Fork this repository to your GitHub account
2. Sign up for a Render account at [render.com](https://render.com)
3. From your Render dashboard, click "New" and select "Blueprint"
4. Connect your GitHub account and select this repository
5. Render will automatically create the web service and database

### Manual Deployment

1. Sign up for a Render account at [render.com](https://render.com)
2. From your Render dashboard, click "New" and select "Web Service"
3. Connect your GitHub repository
4. Use the following settings:
   - **Name**: personal-health-manager
   - **Environment**: Python
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn health_manager.wsgi:application`
5. Add the following environment variables:
   - `SECRET_KEY`: (generate a secure random string)
   - `DEBUG`: False
   - `STRAVA_CLIENT_ID`: (your Strava API client ID)
   - `STRAVA_CLIENT_SECRET`: (your Strava API client secret)
   - `WHOOP_CLIENT_ID`: (your Whoop API client ID)
   - `WHOOP_CLIENT_SECRET`: (your Whoop API client secret)
   - `RENDER`: True
6. Create a PostgreSQL database from the Render dashboard
7. Link the database to your web service

## Local Development

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with the required environment variables
6. Run migrations: `python manage.py migrate`
7. Start the development server: `python manage.py runserver`

## Environment Variables

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to 'True' for development, 'False' for production
- `STRAVA_CLIENT_ID`: Your Strava API client ID
- `STRAVA_CLIENT_SECRET`: Your Strava API client secret
- `WHOOP_CLIENT_ID`: Your Whoop API client ID
- `WHOOP_CLIENT_SECRET`: Your Whoop API client secret
- `DATABASE_URL`: Automatically set by Render for PostgreSQL
- `REDIS_URL`: URL for Redis (for Celery tasks)
