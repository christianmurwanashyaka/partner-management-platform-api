#!/bin/bash

echo "Waiting for database to be ready..."
while ! pg_isready -h db -p 5432 -U $POSTGRES_USER; do
    sleep 1
    echo "Waiting for database connection..."
done

echo "Running database migrations..."
alembic stamp head
alembic revision --autogenerate -m "auto-$(date +%Y%m%d_%H%M%S)"
alembic upgrade head

echo "Starting application..."
python main.py
