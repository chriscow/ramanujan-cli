import os
from dotenv import load_dotenv

load_dotenv()

# Broker settings.
broker_url = os.getenv('CELERY_BROKER_URL')

# List of modules to import when the Celery worker starts.
imports = ('jobs',)

## Using the database to store task state and results.
result_backend = os.getenv('CELERY_BACKEND_URL')