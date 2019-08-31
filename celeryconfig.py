# Broker settings.
broker_url = 'redis://localhost:6379/15'

# List of modules to import when the Celery worker starts.
imports = ('jobs',)

## Using the database to store task state and results.
result_backend = 'redis://localhost:6379/15'