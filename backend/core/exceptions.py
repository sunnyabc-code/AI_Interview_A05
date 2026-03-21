from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'code': response.status_code,
            'message': str(exc),
            'errors': response.data
        }
        response.data = custom_response_data
        logger.error(f"API Error: {exc} - Context: {context}")
    else:
        logger.error(f"Unhandled Exception: {exc} - Context: {context}")
        custom_response_data = {
            'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': 'Internal server error',
            'errors': None
        }
        response = Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response


class APIException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = 'API Error'
    
    def __init__(self, message=None, code=None, errors=None):
        if message is None:
            message = self.default_message
        self.message = message
        if code is not None:
            self.status_code = code
        self.errors = errors
        super().__init__(message)
    
    def to_dict(self):
        return {
            'code': self.status_code,
            'message': self.message,
            'errors': self.errors
        }


class ValidationError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = 'Validation error'


class NotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = 'Resource not found'


class PermissionDeniedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = 'Permission denied'


class AuthenticationError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = 'Authentication failed'
