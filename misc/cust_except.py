class AttemptsException(Exception):
    '''
    Thrown when the attempts exceed the max allowed attempts.
    '''
    def __init__(self, message='The amount of attempts have exceeded the limit.'):
        super().__init__(message)