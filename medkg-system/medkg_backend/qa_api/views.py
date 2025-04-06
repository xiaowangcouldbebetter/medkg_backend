from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import logging
import time

from kg_module.neo4j_client import Neo4jClient
from nlp_module.question_classifier import QuestionClassifier
from nlp_module.question_parser import QuestionPaser
from utils.cache_manager import CacheManager
from utils.performance_monitor import time_function

# 设置日志记录器
logger = logging.getLogger(__name__)

# 初始化组件
try:
    client = Neo4jClient(**settings.NEO4J_CONFIG)
    classifier = QuestionClassifier()
    parser = QuestionPaser()
    logger.info("问答系统组件初始化成功")
    
    # 尝试初始化BERT分类器(可选)
    try:
        from nlp_module.bert_classifier import BertQuestionClassifier
        bert_classifier = BertQuestionClassifier()
        if bert_classifier.model:
            logger.info("BERT分类器初始化成功")
        else:
            bert_classifier = None
            logger.warning("BERT模型不可用，将仅使用规则分类器")
    except Exception as e:
        logger.warning(f"BERT分类器初始化失败，将仅使用规则分类器: {str(e)}")
        bert_classifier = None
        
except Exception as e:
    logger.error(f"问答系统组件初始化失败: {str(e)}")
    client = classifier = parser = bert_classifier = None

@api_view(['GET', 'POST'])
@time_function
def medical_qa(request):
    """医疗问答API端点"""
    if not all([client, classifier, parser]):
        return Response({
            'success': False,
            'code': 500,
            'message': '问答系统组件未正确初始化',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    try:
        # 获取原始问题
        if request.method == 'POST':
            question = request.data.get('question', '')
        else:  # GET
            question = request.query_params.get('question', '')
        
        # 记录输入
        logger.info(f"收到问题: {question}")
        
        if not question:
            return Response({
                'success': False,
                'code': 400,
                'message': '缺少问题参数',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 处理问题
        result = process_question(question)
        
        # 返回结果
        return Response({
            'success': True,
            'code': 200,
            'message': '请求成功',
            'data': {
                'question': question,
                'results': result
            }
        })
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        return Response({
            'success': False,
            'code': 400,
            'message': '请求参数格式错误',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.exception(f"处理问题时发生异常: {str(e)}")
        return Response({
            'success': False,
            'code': 500,
            'message': '服务器内部错误',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@time_function
def process_question(question):
    """处理问题的核心逻辑（带缓存和BERT支持）"""
    # 首先尝试从缓存获取结果
    try:
        cached_result = CacheManager.get_cached_result(question)
        if cached_result:
            return cached_result
    except Exception as e:
        logger.warning(f"获取缓存失败: {str(e)}")
    
    # 问题分类
    classify_result = classifier.classify(question)
    logger.debug(f"规则分类结果: {classify_result}")
    
    # 如果规则分类没有识别到实体或问题类型
    if not classify_result or not classify_result.get('question_types'):
        # 尝试使用BERT分类
        if bert_classifier and bert_classifier.model:
            bert_types = bert_classifier.classify(question)
            if bert_types:
                logger.info(f"使用BERT识别问题类型: {bert_types}")
                # 重新构建分类结果
                if not classify_result:
                    # 如果规则分类完全失败，我们需要手动提取可能的实体
                    from nlp_module.medical_entity_extractor import extract_medical_entities
                    entities = extract_medical_entities(question)
                    if entities:
                        classify_result = {
                            'args': entities,
                            'question_types': bert_types
                        }
                else:
                    # 如果有实体但没有类型，补充BERT识别的类型
                    classify_result['question_types'] = bert_types
    
    # 如果仍然没有识别结果，返回空
    if not classify_result or not classify_result.get('question_types'):
        logger.info(f"未能识别问题: {question}")
        return []
    
    # 生成Cypher查询
    cypher_queries = parser.parser_main(classify_result)
    if not cypher_queries:
        logger.info(f"未能生成有效的查询语句: {question}")
        return []
    
    # 记录查询语句
    for i, query in enumerate(cypher_queries, 1):
        logger.debug(f"查询{i} ({query.get('question_type', 'unknown')}): {query.get('sql', [])}")
    
    # 执行查询
    final_results = client.execute_query_set(cypher_queries)
    logger.debug(f"查询结果数量: {len(final_results)}")
    
    # 缓存结果
    try:
        CacheManager.cache_result(question, final_results)
    except Exception as e:
        logger.warning(f"缓存结果失败: {str(e)}")
    
    return final_results

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@time_function
def feedback_api(request):
    """用户反馈API"""
    try:
        data = request.data
        message_id = data.get('messageId')
        is_helpful = data.get('isHelpful')
        session_id = data.get('sessionId')
        user = request.user.username
        
        # 这里添加保存反馈到数据库的逻辑
        logger.info(f"用户 {user} 提交反馈: 消息ID={message_id}, 有帮助={is_helpful}, 会话ID={session_id}")

        return Response({
            'success': True,
            'message': '反馈已提交，谢谢!'
        })
        
    except Exception as e:
        logger.exception(f"保存反馈时发生错误: {str(e)}")
        return Response({
            'success': False,
            'message': '保存反馈失败'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
