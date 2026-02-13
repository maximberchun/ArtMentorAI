class UserExceptionError(Exception):
    """
    Custom exception intended to be shown directly to end users.

    This exception type is meant to represent user-facing errors,
    such as configuration mistakes, invalid inputs, or missing environment variables.
    It can be caught and logged or displayed in a human-readable way.

    Attributes:
        message (str): A human-readable message to show to the user.
        exit_code (int): The exit code the application should return. Defaults to 2.

    """

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message
