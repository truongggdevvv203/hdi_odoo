"""
Response formatter chung cho tất cả API
Cung cấp các method để tạo response với format chuẩn
"""
import json
from odoo.http import Response


class ResponseFormatter:
    """Class để format response với format chuẩn cho API"""
    
    # HTTP Status Codes
    HTTP_OK = 200
    HTTP_CREATED = 201
    HTTP_BAD_REQUEST = 400
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_NOT_FOUND = 404
    HTTP_INTERNAL_ERROR = 500
    
    # Status strings
    STATUS_SUCCESS = 'Success'
    STATUS_ERROR = 'Error'

    @staticmethod
    def success(message, data=None, code=HTTP_OK):
        """
        Tạo response thành công
        
        Args:
            message (str): Thông báo thành công
            data (dict): Dữ liệu trả về (mặc định: {})
            code (int): HTTP status code (mặc định: 200)
        
        Returns:
            dict: Response object với format chuẩn
        """
        return {
            'code': code,
            'status': ResponseFormatter.STATUS_SUCCESS,
            'message': message,
            'data': data or {}
        }

    @staticmethod
    def error(message, code=HTTP_BAD_REQUEST, data=None):
        """
        Tạo response lỗi
        
        Args:
            message (str): Thông báo lỗi
            code (int): HTTP status code (mặc định: 400)
            data (dict): Dữ liệu bổ sung (mặc định: {})
        
        Returns:
            dict: Response object với format chuẩn
        """
        return {
            'code': code,
            'status': ResponseFormatter.STATUS_ERROR,
            'message': message,
            'data': data or {}
        }

    @staticmethod
    def make_response(response_dict, status_code=200):
        """
        Tạo HTTP Response object từ dict
        
        Args:
            response_dict (dict): Response dict (từ success() hoặc error())
            status_code (int): HTTP status code
        
        Returns:
            Response: Odoo Response object với JSON content
        """
        return Response(
            json.dumps(response_dict, ensure_ascii=False),
            status=status_code,
            mimetype='application/json',
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )

    @staticmethod
    def success_response(message, data=None, status_code=HTTP_OK):
        """
        Tạo success response và return HTTP Response object
        
        Args:
            message (str): Thông báo thành công
            data (dict): Dữ liệu trả về
            status_code (int): HTTP status code
        
        Returns:
            Response: Odoo Response object
        """
        response_dict = ResponseFormatter.success(message, data, status_code)
        return ResponseFormatter.make_response(response_dict, status_code)

    @staticmethod
    def error_response(message, status_code=HTTP_BAD_REQUEST, data=None):
        """
        Tạo error response và return HTTP Response object
        
        Args:
            message (str): Thông báo lỗi
            status_code (int): HTTP status code
            data (dict): Dữ liệu bổ sung
        
        Returns:
            Response: Odoo Response object
        """
        response_dict = ResponseFormatter.error(message, status_code, data)
        return ResponseFormatter.make_response(response_dict, status_code)
