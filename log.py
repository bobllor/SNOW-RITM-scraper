import logging

def logger(exception_msg):
    logging.basicConfig(filename=r'.\logs\errors.log', level=logging.ERROR,
                        format='%(asctime)s | %(name)s: %(message)s')
    
    logging.critical(exception_msg)