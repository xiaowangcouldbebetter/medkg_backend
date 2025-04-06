# accounts/views.py

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from utils.rsa_handler import decrypt_password, PUBLIC_KEY

# 配置日志
logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(['POST', 'GET'])
def public_key(request):
    """获取RSA公钥接口"""
    logger.info("获取公钥请求")
    return JsonResponse({'code': 0, 'data': PUBLIC_KEY})


@csrf_exempt
@require_http_methods(['POST'])
def verify(request):
    """密码验证接口"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        logger.info("接收到验证请求数据")
        # 增加参数校验
        if 'password' not in data:
            logger.warning("缺少password参数")
            return JsonResponse({'code': 400, 'msg': '缺少password参数'})

        # 解密密码
        password = data['password']
        try:
            decrypted = decrypt_password(password)
            logger.info("密码解密成功")

            if decrypted == '123':
                logger.info('密码验证成功')
                return JsonResponse({'code': 0, 'data': 'VALID_TOKEN'})
            logger.warning('密码验证失败')
            return JsonResponse({'code': 401, 'msg': '密码验证失败'})
        except Exception as e:
            logger.error(f"密码解密失败: {str(e)}")
            return JsonResponse({'code': 500, 'msg': '密码解密失败'})
    except json.JSONDecodeError:
        logger.error("JSON解析失败")
        return JsonResponse({'code': 400, 'msg': '无效的JSON数据'})
    except Exception as e:
        logger.error(f'验证异常: {str(e)}')
        return JsonResponse({'code': 500, 'msg': '服务器异常'})


@csrf_exempt
@require_http_methods(['POST'])
def register(request):
    """用户注册接口"""
    try:
        # 解析请求数据
        data = json.loads(request.body.decode('utf-8'))
        logger.info(f"收到注册请求: {data.get('username')}")
        
        # 提取注册信息
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        # 基本参数验证
        if not all([username, password, email]):
            logger.warning("注册信息不完整")
            return JsonResponse({
                'success': False,
                'message': '请提供所有必要信息'
            }, status=400)
            
        # 用户名长度验证
        if len(username) < 3:
            logger.warning(f"用户名长度不足: {username}")
            return JsonResponse({
                'success': False,
                'message': '用户名长度不能少于3个字符'
            }, status=400)
            
        # 密码长度验证
        if len(password) < 6:
            logger.warning("密码长度不足")
            return JsonResponse({
                'success': False,
                'message': '密码长度不能少于6个字符'
            }, status=400)
            
        # 创建用户
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # 生成JWT令牌
            refresh = RefreshToken.for_user(user)
            tokens = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            
            logger.info(f"用户注册成功: {username}")
            return JsonResponse({
                'success': True,
                'message': '注册成功',
                'token': tokens['access']
            })
            
        except IntegrityError:
            # 处理用户名或邮箱已存在的情况
            if User.objects.filter(username=username).exists():
                logger.warning(f"用户名已存在: {username}")
                return JsonResponse({
                    'success': False,
                    'message': '用户名已被注册'
                }, status=400)
            
            if User.objects.filter(email=email).exists():
                logger.warning(f"邮箱已存在: {email}")
                return JsonResponse({
                    'success': False,
                    'message': '邮箱已被注册'
                }, status=400)
                
            logger.warning("用户注册失败: 数据重复")
            return JsonResponse({
                'success': False,
                'message': '注册失败，用户信息重复'
            }, status=400)
            
        except ValidationError as e:
            logger.error(f"用户注册验证错误: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
            
    except json.JSONDecodeError:
        logger.error("注册请求JSON解析失败")
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
        
    except Exception as e:
        logger.error(f"注册异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def login(request):
    """用户登录接口"""
    try:
        # 解析请求数据
        data = json.loads(request.body.decode('utf-8'))
        logger.info("收到登录请求")
        
        # 提取登录信息
        username = data.get('username')
        password = data.get('password')
        
        # 基本参数验证
        if not all([username, password]):
            logger.warning("登录信息不完整")
            return JsonResponse({
                'success': False,
                'message': '请提供用户名和密码'
            }, status=400)
            
        # 验证用户名和密码
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # 生成JWT令牌
            refresh = RefreshToken.for_user(user)
            tokens = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            
            # 更新最后登录时间
            user.save()
            
            logger.info(f"用户登录成功: {username}")
            return JsonResponse({
                'success': True,
                'message': '登录成功',
                'token': tokens['access'],
                'userType': 'admin' if user.is_admin else 'user',
                'username': user.username
            })
        else:
            logger.warning(f"登录失败，用户名或密码错误: {username}")
            return JsonResponse({
                'success': False,
                'message': '用户名或密码错误'
            }, status=401)
            
    except json.JSONDecodeError:
        logger.error("登录请求JSON解析失败")
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
        
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }, status=500)


# 用户信息接口（需要身份验证）
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """获取当前登录用户信息"""
    user = request.user
    logger.info(f"获取用户信息: {user.username}")
    
    return JsonResponse({
        'success': True,
        'data': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'isAdmin': user.is_admin,
            'dateJoined': user.date_joined,
            'lastLogin': user.last_login
        }
    })
