import os
from dotenv import load_dotenv
load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT'))

# You can also specify the Redis DB to use
# REDIS_DB = os.getenv('WORK_QUEUE_DB')
# REDIS_PASSWORD = 'very secret'

# Queues to listen on
QUEUES = ['high_priority', 'default', 'low_priority']
