class DynamoDuplicatedError(Exception):
    """
    DynamoDB에서 이미 앞서 처리한 결과물이 있을 때 raise하는 Exception 입니다.
    """
    def __init__(self, message):
        super().__init__(message)


class DynamoOperationError(Exception):
    """
    DynamoDB에서 알 수 없는 이유로 raise되는 Exception 입니다.
    """
    def __init__(self, message):
        super().__init__(message)
