import os
import hashlib
import redis
import logging
import utils
from datetime import datetime

from mpmath import mpf

log = logging.getLogger(__name__)

class SequenceCache():

    def __init__(self, redis_pool):
        self.redis = redis.Redis(connection_pool=redis_pool)

    def generate(self, generator, gen_args):
        # Generate the sequences
        hash = self.hash(generator, gen_args)

        seq = self.redis.get(hash)

        if seq is None:
            start = datetime.now()
            logging.debug(f"Generating sequence {generator.__name__} {gen_args}")
            seq = generator(*gen_args)
            self.redis.set(hash, repr(seq))
            logging.debug(f"Generation complete in {(datetime.now() - start).total_seconds()} sec. {generator.__name__} {gen_args}")
        else:
            logging.debug(f'Using cached sequence')

        return hash

    def get(self, hash):
        return eval(self.redis.get(hash))
        
    def hash(self, generator, gen_args):
        # b = hashlib.sha256(bytes(repr(gen_args), 'utf-8')).hexdigest()
        return "seq:" + generator.__name__ + ":" + repr(gen_args)

