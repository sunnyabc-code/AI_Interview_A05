from rest_framework.response import Response


class APIResponse:
    @staticmethod
    def success(data=None, message="success", code=200):
        return Response({
            "code": code,
            "message": message,
            "data": data
        }, status=code)
    
    @staticmethod
    def error(message="error", code=400, errors=None):
        return Response({
            "code": code,
            "message": message,
            "errors": errors
        }, status=code)
    
    @staticmethod
    def paginated(items, pagination, message="success", code=200):
        return Response({
            "code": code,
            "message": message,
            "data": {
                "items": items,
                "pagination": pagination
            }
        }, status=code)
