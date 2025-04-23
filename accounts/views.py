# accounts/views.py

import json
import datetime
import logging
import traceback

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils.rsa_handler import decrypt_password, PUBLIC_KEY
from utils.auth import generate_token, token_required
from .models import User, Admin, UserLog, SystemLog, UserBug

logger = logging.getLogger('accounts')


@csrf_exempt
@require_http_methods(['POST', 'GET'])
def public_key(request):
    """获取RSA公钥接口"""
    return JsonResponse({'code': 0, 'data': PUBLIC_KEY})


@csrf_exempt
@require_http_methods(['POST','GET'])
def verify(request):
    """密码验证接口"""
    try:
        data = json.loads(request.body) # 修改这里
        print("接收到的数据", data)
        # 增加参数校验
        if 'password' not in data:
            return JsonResponse({'code': 400, 'msg': '缺少password参数'})

        # 解密密码
        password = data['password']
        decrypted = decrypt_password(password)
        print("解密结果", decrypted)

        if decrypted == '123':
            print('密码验证成功')
            return JsonResponse({'code': 0, 'data': 'VALID_TOKEN'})
        return JsonResponse({'code': 401, 'msg': '密码验证失败'})
    except Exception as e:
        print(f'验证异常: {str(e)}')  # 增加错误日志
        return JsonResponse({'code': 500, 'msg': '服务器异常'})


@csrf_exempt
@require_http_methods(['POST','OPTIONS'])
def login(request):
    """用户登录接口"""
    # 处理CORS预检请求
    if request.method == 'OPTIONS':
        response = JsonResponse({'code': 200, 'msg': 'OK'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
        return response
        
    try:
        # 修复请求体解析错误
        data = json.loads(request.body)
        print("接收到的登录数据", data)
        
        # 必要参数验证
        if not all(k in data for k in ['name', 'password']):
            return JsonResponse({'code': 400, 'msg': '缺少必要参数: name或password'})
            
        user_name = data['name']
        
        # 从数据库查询用户
        user_query = User.objects.filter(name=user_name).first()
        admin_query = Admin.objects.filter(name=user_name).first()
        
        if not (user_query or admin_query):
            return JsonResponse({'code': 403, 'msg': '用户不存在'})
            
        user = user_query or admin_query
            
        # 解密并验证密码
        try:
            decrypted_password = decrypt_password(data['password'])
            
            # 使用模型的密码检查方法
            if not user.check_password(decrypted_password):
                return JsonResponse({'code': 401, 'msg': '密码不正确'})
                
        except Exception as e:
            print(f"密码解密错误: {str(e)}")
            return JsonResponse({'code': 400, 'msg': '密码格式不正确'})
            
        # 生成JWT令牌
        user_type = 'admin' if admin_query else 'user'
        token = generate_token(user.id, user_type)
        
        # 更新用户的最后登录时间
        user.last_login = timezone.now()
        user.save()
        
        # 构造响应
        response_data = {
            'code': 0,
            'data': {
                'token': token,
                'userType': user_type,
                'name': user_name,
                'email': user.email,
                'expires': (timezone.now() + datetime.timedelta(hours=24)).isoformat()
            },
            'msg': '登录成功'
        }
        
        # 返回成功响应
        response = JsonResponse(response_data)
        response['Access-Control-Allow-Origin'] = '*'
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '无效的JSON格式'})
    except KeyError as e:
        return JsonResponse({'code': 400, 'msg': f'缺少必要参数: {str(e)}'})
    except Exception as e:
        print(f"登录异常: {str(e)}")
        return JsonResponse({'code': 500, 'msg': '服务器内部错误'})


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def register(request):
    """用户注册接口"""
    # 处理CORS预检请求
    if request.method == 'OPTIONS':
        response = JsonResponse({'code': 200, 'msg': 'OK'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
        return response
        
    try:
        data = json.loads(request.body)
        
        # 参数验证
        required_fields = ['name', 'email', 'password']
        if not all(field in data for field in required_fields):
            return JsonResponse({'code': 400, 'msg': '缺少必要注册信息'})
            
        # 检查用户是否已存在
        if User.objects.filter(email=data['email']).exists():
            return JsonResponse({'code': 409, 'msg': '该邮箱已被注册'})
            
        if User.objects.filter(name=data['name']).exists():
            return JsonResponse({'code': 409, 'msg': '该用户名已被使用'})
            
        # 解密密码
        try:
            decrypted_password = decrypt_password(data['password'])
        except Exception as e:
            print(f"密码解密错误: {str(e)}")
            return JsonResponse({'code': 400, 'msg': '密码格式不正确'})
            
        # 创建新用户
        new_user = User(
            name=data['name'],
            email=data['email'],
        )
        # 使用模型方法设置密码
        new_user.set_password(decrypted_password)
        new_user.save()
        
        # 自动登录生成令牌
        token = generate_token(new_user.id, 'user')
        
        return JsonResponse({
            'code': 0,
            'msg': '注册成功',
            'data': {
                'name': data['name'],
                'email': data['email'],
                'token': token,
                'userType': 'user'
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '无效的JSON格式'})
    except Exception as e:
        print(f"注册异常: {str(e)}")
        return JsonResponse({'code': 500, 'msg': '服务器内部错误'})


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def logout(request):
    """用户退出登录接口"""
    # 处理CORS预检请求
    if request.method == 'OPTIONS':
        response = JsonResponse({'code': 200, 'msg': 'OK'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
        return response
        
    try:
        # 在实际应用中，我们可以维护一个黑名单来存储已退出的令牌
        # 这里简化处理，直接返回成功结果
        
        return JsonResponse({
            'code': 0,
            'msg': '退出登录成功'
        })
        
    except Exception as e:
        print(f"退出登录异常: {str(e)}")
        return JsonResponse({'code': 500, 'msg': '服务器内部错误'})


@csrf_exempt
@token_required
def user_info(request):
    """获取用户信息接口"""
    if request.method == 'OPTIONS':
        response = JsonResponse({'code': 200, 'msg': 'OK'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
        return response
        
    # request.user 由 token_required 装饰器添加
    user = request.user
    
    return JsonResponse({
        'code': 0,
        'data': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'userType': request.user_type,
            'lastLogin': user.last_login.isoformat() if user.last_login else None,
            'createdAt': user.created_at.isoformat() if user.created_at else None
        }
    })

# 管理员登录
@api_view(['POST'])
def admin_login(request):
    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')
    
    try:
        admin = Admin.objects.get(email=email)
        if admin.check_password(password):
            # 更新最后登录时间
            admin.last_login = timezone.now()
            admin.save()
            
            return Response({
                'success': True,
                'message': '登录成功',
                'admin': {
                    'id': admin.id,
                    'name': admin.name,
                    'email': admin.email
                }
            })
        else:
            return Response({
                'success': False,
                'message': '密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)
    except Admin.DoesNotExist:
        return Response({
            'success': False,
            'message': '管理员账号不存在'
        }, status=status.HTTP_404_NOT_FOUND)

# 获取用户日志
@api_view(['GET'])
def get_user_logs(request):
    status_filter = request.GET.get('status', None)
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    
    logs_query = UserLog.objects.all().order_by('-created_at')
    
    if status_filter:
        logs_query = logs_query.filter(status=status_filter)
    
    total = logs_query.count()
    logs = logs_query[offset:offset+limit]
    
    return Response({
        'success': True,
        'total': total,
        'logs': [
            {
                'id': log.id,
                'user': log.user.name if log.user else '匿名用户',
                'question': log.question,
                'answer': log.answer,
                'status': log.status,
                'created_at': log.created_at,
            } for log in logs
        ]
    })

# 获取系统日志
@api_view(['GET'])
def get_system_logs(request):
    level_filter = request.GET.get('level', None)
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    
    logs_query = SystemLog.objects.all().order_by('-created_at')
    
    if level_filter:
        logs_query = logs_query.filter(level=level_filter)
    
    total = logs_query.count()
    logs = logs_query[offset:offset+limit]
    
    return Response({
        'success': True,
        'total': total,
        'logs': [
            {
                'id': log.id,
                'level': log.level,
                'module': log.module,
                'message': log.message,
                'created_at': log.created_at,
                'trace': log.trace
            } for log in logs
        ]
    })

# 用于记录系统日志的函数
def log_system_event(level, module, message, trace=None):
    try:
        SystemLog.objects.create(
            level=level,
            module=module,
            message=message,
            trace=trace
        )
    except Exception as e:
        print(f"记录系统日志失败: {str(e)}")

# 记录用户聊天日志
@csrf_exempt
@api_view(['POST'])
def record_chat_log(request):
    """记录用户聊天日志的API接口"""
    try:
        data = request.data
        question = data.get('question', '')
        answer = data.get('answer', '')
        status = data.get('status', 'success')
        
        # 获取用户信息（如果已登录）
        user = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        
        # 获取IP地址
        ip_address = get_client_ip(request)
        
        # 创建日志记录
        UserLog.objects.create(
            user=user,
            question=question,
            answer=answer,
            status=status,
            ip_address=ip_address
        )
        
        return Response({'success': True, 'message': '日志记录成功'})
    except Exception as e:
        error_msg = f"记录用户聊天日志失败: {str(e)}"
        log_system_event("ERROR", "ChatLog", error_msg, trace=traceback.format_exc())
        return Response({
            'success': False,
            'message': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 辅助函数：获取客户端IP地址
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# 用户反馈提交
@csrf_exempt
@require_http_methods(['POST'])
def submit_feedback(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        title = data.get('title', '')
        content = data.get('content', '')
        bug_type = data.get('type', 'other')
        user_id = data.get('user_id')
        
        # 验证数据
        if not title or not content:
            return JsonResponse({
                'success': False,
                'message': '反馈标题和内容不能为空'
            }, status=400)
            
        # 获取用户（如果登录）
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
                
        # 创建反馈记录
        UserBug.objects.create(
            user=user,
            title=title,
            content=content,
            bug_type=bug_type,
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            'success': True,
            'message': '反馈提交成功，感谢您的建议！'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的请求数据格式'
        }, status=400)
        
    except Exception as e:
        error_msg = f"处理用户反馈失败: {str(e)}"
        log_system_event("ERROR", "ACCOUNTS", error_msg, trace=traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误，请稍后再试'
        }, status=500)


# 管理员获取用户反馈列表
@csrf_exempt
@require_http_methods(['GET'])
def admin_feedback_list(request):
    try:
        # 权限验证可以在这里添加
        
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        status_filter = request.GET.get('status', None)
        
        # 查询数据
        query = UserBug.objects.all().order_by('-created_at')
        
        # 应用过滤
        if status_filter:
            query = query.filter(status=status_filter)
        
        # 计算总数
        total = query.count()
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        feedbacks = query[start:end]
        
        # 格式化数据
        result = []
        for feedback in feedbacks:
            result.append({
                'id': feedback.id,
                'title': feedback.title,
                'content': feedback.content,
                'bug_type': feedback.bug_type,
                'status': feedback.status,
                'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'user_name': feedback.user.name if feedback.user else '匿名用户',
                'ip_address': feedback.ip_address,
                'admin_remarks': feedback.admin_remarks
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'results': result
            }
        })
        
    except Exception as e:
        error_msg = f"获取用户反馈列表失败: {str(e)}"
        log_system_event("ERROR", "ACCOUNTS", error_msg, trace=traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误，请稍后再试'
        }, status=500)


# 管理员更新反馈状态
@csrf_exempt
@require_http_methods(['PUT','GET','POST'])
def update_feedback_status(request, feedback_id):
    try:
        data = json.loads(request.body.decode('utf-8'))
        status = data.get('status')
        admin_remarks = data.get('admin_remarks', '')
        
        # 验证数据
        if not status:
            return JsonResponse({
                'success': False,
                'message': '状态不能为空'
            }, status=400)
            
        # 查找并更新
        feedback = UserBug.objects.get(id=feedback_id)
        feedback.status = status
        if admin_remarks:
            feedback.admin_remarks = admin_remarks
        feedback.save()
        
        return JsonResponse({
            'success': True,
            'message': '反馈状态更新成功'
        })
        
    except UserBug.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '未找到指定的反馈记录'
        }, status=404)
        
    except Exception as e:
        error_msg = f"更新反馈状态失败: {str(e)}"
        log_system_event("ERROR", "ACCOUNTS", error_msg, trace=traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': '服务器内部错误，请稍后再试'
        }, status=500)
