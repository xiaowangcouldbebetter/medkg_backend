from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import traceback
import logging
from datetime import datetime

from kg_module.neo4j_client import Neo4jClient
from nlp_module.question_classifier import QuestionClassifier
from nlp_module.question_parser import QuestionParser
from accounts.models import UserLog
from accounts.views import log_system_event, get_client_ip

# 创建日志记录器
logger = logging.getLogger('qa_api')

client = Neo4jClient(**settings.NEO4J_CONFIG)
classifier = QuestionClassifier()
parser = QuestionParser()

# 用户问题历史记录（临时存储，生产环境应使用数据库）
user_history = {}

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def medical_qa(request):
    try:
        # 获取原始问题
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            question = data.get('question', '')
            log_query = data.get('log_query', False)  # 是否记录日志的标志
            user_id = data.get('user_id', 'anonymous')
        elif request.method == 'GET':
            question = request.GET.get('question', '')
            log_query = request.GET.get('log_query', 'false').lower() == 'true'
            user_id = request.GET.get('user_id', 'anonymous')

        print(f"\n=== 原始问题 ===\n{question}")

        if not question:
            return JsonResponse({'error': 'Missing question'}, status=400)

        # 记录问题
        logger.info(f"User {user_id} question: {question}")

        # 问题分类处理
        classify_result = classifier.classify(question)
        print(f"\n=== 分类结果 ===\n{classify_result}")

        # 生成Cypher查询
        cypher_queries = parser.parser_main(classify_result)
        print(f"\n=== 生成查询语句 ===")
        for i, query in enumerate(cypher_queries, 1):
            print(f"查询{i}: {query['sql']}")

        # 执行所有查询
        final_results = client.execute_query_set(cypher_queries)
        # 处理并返回结果
        processed_results = []
        for item in final_results:
            if item.get('properties') or item.get('relations'):
                result = {
                    'entity': item.get('main_entity', ''),
                    'properties': item.get('properties', {}),
                    'relations': []
                }

                # 处理关系数据
                if item.get('relations'):
                    # 确保处理多个关系
                    relations = item['relations']
                    if isinstance(relations, list):  # 处理多个关系的情况
                        result['relations'] = [{
                            'source': rel.get('source'),
                            'relation': rel.get('relation'),
                            'target': rel.get('target')
                        } for rel in relations]
                    else:  # 处理单个关系的情况
                        result['relations'].append({
                            'source': relations.get('source'),
                            'relation': relations.get('relation'),
                            'target': relations.get('target')
                        })

                processed_results.append(result)

        print(f"\n=== 最终结果 ===\n{processed_results}")

        # 确定回答状态
        has_results = len(processed_results) > 0
        status = 'success' if has_results else 'not_found'
        
        # 合并最终答案
        if not processed_results:
            final_answer = "未找到相关信息"
        else:
            final_answer = format_results_to_text(processed_results)
        
        # 保存到历史记录
        save_to_history(user_id, question, final_answer)
        
        # 创建响应数据
        response_data = {
            'success': True,
            'code': 200,
            'message': '请求成功',
            'data': {
                'question': question,
                'results': processed_results
            }
        }
        
        # 如果请求指定了记录日志，则自动记录
        if log_query:
            try:
                # 获取用户信息（如果已登录）
                user = None
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user = request.user
                
                # 记录日志
                UserLog.objects.create(
                    user=user,
                    question=question,
                    answer=final_answer,
                    status=status,
                    ip_address=get_client_ip(request)
                )
                
                print(f"\n=== 日志记录成功 ===\n问题: {question}\n状态: {status}")
            except Exception as e:
                error_msg = f"记录用户查询日志失败: {str(e)}"
                log_system_event("ERROR", "QA_API", error_msg, trace=traceback.format_exc())
                print(f"\n!!! 日志记录异常: {str(e)}")
                # 日志记录失败不影响问答服务
        
        # 返回响应
        return JsonResponse(response_data)

    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'code': 400,
            'message': '请求参数格式错误',
            'error': str(e)
        }, status=400)

    except Exception as e:
        error_msg = f"处理医疗问答请求失败: {str(e)}"
        log_system_event("ERROR", "QA_API", error_msg, trace=traceback.format_exc())
        print(f"\n!!! 处理异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'code': 500,
            'message': '服务器内部错误',
            'error': str(e)
        }, status=500)

# 辅助函数：将结果格式化为文本
def format_results_to_text(results):
    """将查询结果转换为文本格式，用于记录日志"""
    text = ""
    for result in results:
        # 添加实体信息
        entity = result.get('entity', '')
        if entity:
            text += f"【{entity}】\n"
        
        # 添加属性信息
        properties = result.get('properties', {})
        if properties:
            text += "属性信息：\n"
            for key, value in properties.items():
                text += f"- {key}: {value}\n"
        
        # 添加关系信息
        relations = result.get('relations', [])
        if relations:
            text += "相关信息：\n"
            relation_groups = {}
            
            # 按关系类型分组
            for rel in relations:
                rel_type = rel.get('relation', '其他')
                if rel_type not in relation_groups:
                    relation_groups[rel_type] = []
                
                target = rel.get('target') or rel.get('source')
                if target:
                    relation_groups[rel_type].append(target)
            
            # 输出分组后的关系
            for rel_type, targets in relation_groups.items():
                text += f"- {rel_type}: {', '.join(targets)}\n"
        
        text += "\n"
    
    return text.strip()

def save_to_history(user_id, question, answer):
    """
    保存用户问答历史
    """
    if user_id not in user_history:
        user_history[user_id] = []
    
    user_history[user_id].append({
        'question': question,
        'answer': answer,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # 只保留最近20条记录
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]

@csrf_exempt
@require_http_methods(["GET"])
def get_history(request):
    """
    获取用户问答历史，支持搜索功能
    """
    try:
        user_id = request.GET.get('user_id', 'anonymous')
        keyword = request.GET.get('keyword', '').strip().lower()
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        
        # 获取用户历史记录
        history = user_history.get(user_id, [])
        
        # 如果有搜索关键词，过滤结果
        if keyword:
            filtered_history = []
            for item in history:
                question = item.get('question', '').lower()
                answer = item.get('answer', '').lower()
                if keyword in question or keyword in answer:
                    filtered_history.append(item)
            history = filtered_history
            
        # 如果有日期筛选
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                filtered_history = []
                for item in history:
                    timestamp = item.get('timestamp', '')
                    if timestamp:
                        item_datetime = datetime.strptime(timestamp.split()[0], '%Y-%m-%d')
                        if item_datetime >= start_datetime:
                            filtered_history.append(item)
                history = filtered_history
            except ValueError:
                # 忽略无效的日期格式
                pass
                
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                filtered_history = []
                for item in history:
                    timestamp = item.get('timestamp', '')
                    if timestamp:
                        item_datetime = datetime.strptime(timestamp.split()[0], '%Y-%m-%d')
                        if item_datetime <= end_datetime:
                            filtered_history.append(item)
                history = filtered_history
            except ValueError:
                # 忽略无效的日期格式
                pass
        
        # 添加ID便于前端操作
        for i, item in enumerate(history):
            item['id'] = i + 1
        
        return JsonResponse({
            "status": "success",
            "data": history,
            "total": len(history),
            "filters": {
                "keyword": keyword,
                "start_date": start_date,
                "end_date": end_date
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"获取历史记录时出错: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def clear_history(request):
    """
    清空用户问答历史
    """
    try:
        user_id = request.GET.get('user_id', 'anonymous')
        
        # 清空用户历史记录
        if user_id in user_history:
            user_history[user_id] = []
        
        return JsonResponse({
            "status": "success",
            "message": "历史记录已清空"
        })
        
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"清空历史记录时出错: {str(e)}"
        }, status=500)
