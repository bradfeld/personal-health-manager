#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing system dependencies..."
apt-get update
apt-get install -y libpq-dev python3-dev

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating logs directory..."
mkdir -p logs

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Applying database migrations..."
python manage.py migrate

echo "Build completed successfully!" 