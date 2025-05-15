from a2a.types import (
    ContentTypeNotSupportedError,
    InternalError,
    InvalidAgentResponseError,
    InvalidParamsError,
    InvalidRequestError,
    JSONParseError,
    JSONRPCError,
    MethodNotFoundError,
    PushNotificationNotSupportedError,
    TaskNotCancelableError,
    TaskNotFoundError,
    UnsupportedOperationError,
)


class A2AServerError(Exception):
    """Base exception for A2A Server errors."""


class MethodNotImplementedError(A2AServerError):
    """Exception for Unimplemented methods."""

    def __init__(
        self, message: str = 'This method is not implemented by the server'
    ):
        self.message = message
        super().__init__(f'Not Implemented operation Error: {message}')


class ServerError(Exception):
    def __init__(
        self,
        error: (
            JSONRPCError
            | JSONParseError
            | InvalidRequestError
            | MethodNotFoundError
            | InvalidParamsError
            | InternalError
            | TaskNotFoundError
            | TaskNotCancelableError
            | PushNotificationNotSupportedError
            | UnsupportedOperationError
            | ContentTypeNotSupportedError
            | InvalidAgentResponseError
            | None
        ),
    ):
        self.error = error
