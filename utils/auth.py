# utils/auth.py
import time
import jwt
from functools import wraps
from django.http import JsonResponse
from django.conf import settings
from accounts.models import User, Admin

# 使用项目的SECRET_KEY作为JWT的密钥
# 在实际项目中，可以为JWT单独设置一个密钥
JWT_SECRET = getattr(settings, 'SECRET_KEY', 'django-insecure-default-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION = 24 * 60 * 60  # 24小时(秒)


def generate_token(user_id, user_type):
    """
    生成JWT令牌
    
    Args:
        user_id: 用户ID
        user_type: 用户类型 ('user' 或 'admin')
        
    Returns:
        str: JWT令牌
    """
    payload = {
        'user_id': user_id,
        'user_type': user_type,
        'exp': int(time.time()) + JWT_EXPIRATION,
        'iat': int(time.time())
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token):
    """
    验证JWT令牌
    
    Args:
        token: JWT令牌
        
    Returns:
        dict: 令牌中的payload数据
        None: 令牌无效或已过期
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # 令牌已过期
        return None
    except jwt.InvalidTokenError:
        # 令牌无效
        return None


def get_user_from_token(token):
    """
    根据令牌获取用户
    
    Args:
        token: JWT令牌
        
    Returns:
        User/Admin: 用户对象
        None: 令牌无效或用户不存在
    """
    payload = verify_token(token)
    if not payload:
        return None
        
    user_id = payload.get('user_id')
    user_type = payload.get('user_type')
    
    if user_type == 'admin':
        return Admin.objects.filter(id=user_id).first()
    else:
        return User.objects.filter(id=user_id).first()


def token_required(view_func):
    """
    验证令牌的装饰器
    
    Example:
        @token_required
        def protected_view(request):
            # 安全的视图逻辑
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 获取Authorization头部
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # 检查头部格式
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'code': 401,
                'msg': '无效的身份验证令牌'
            })
            
        # 提取令牌
        token = auth_header.split(' ')[1]
        
        # 验证令牌
        payload = verify_token(token)
        if not payload:
            return JsonResponse({
                'code': 401,
                'msg': '令牌已过期或无效'
            })
            
        # 获取用户
        user = get_user_from_token(token)
        if not user:
            return JsonResponse({
                'code': 401,
                'msg': '用户不存在'
            })
            
        # 将用户添加到请求对象中
        request.user = user
        request.user_type = payload.get('user_type')
        
        # 调用原始视图
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_required(view_func):
    """
    验证管理员权限的装饰器
    
    Example:
        @admin_required
        def admin_view(request):
            # 管理员视图逻辑
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 先验证令牌
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'code': 401,
                'msg': '无效的身份验证令牌'
            })
            
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if not payload:
            return JsonResponse({
                'code': 401,
                'msg': '令牌已过期或无效'
            })
            
        # 检查用户类型
        if payload.get('user_type') != 'admin':
            return JsonResponse({
                'code': 403,
                'msg': '权限不足'
            })
            
        # 获取管理员
        admin = Admin.objects.filter(id=payload.get('user_id')).first()
        if not admin:
            return JsonResponse({
                'code': 401,
                'msg': '管理员不存在'
            })
            
        # 将管理员添加到请求对象
        request.user = admin
        request.user_type = 'admin'
        
        # 调用原始视图
        return view_func(request, *args, **kwargs)
    
    return wrapper 