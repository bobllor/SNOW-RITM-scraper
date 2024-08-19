import logging

def logger(exception_msg, level):
    formatter = logging.Formatter('%(asctime)s | %(name)s %(levelname)s: %(message)s')

    error_handler = logging.getLogger('errors.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    debug_handler = logging.getLogger('debug.log')
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    logger.addHandler(debug_handler)

    if level == 'DEBUG':
        logger.debug(exception_msg)
    
    if level == 'ERROR':
        logger.debug(exception_msg)