class QueueEmptyException(Exception):
    def __init__(self, message: str = "Cannot perform operation on empty queue") -> None:
        super().__init__(message)
        self.message = message
