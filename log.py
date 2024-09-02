import logging
from pathlib import Path

parent_path = Path(__file__).parent / 'logs'
log_file = parent_path / 'errors.log'

def logger(exception_msg):
    # if the logs folder doesn't exist then make one.
    parent_path.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(filename=log_file, level=logging.ERROR,
                        format='%(asctime)s | %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    logging.critical(exception_msg)