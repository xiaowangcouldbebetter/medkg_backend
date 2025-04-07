from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json

from kg_module.neo4j_client import Neo4jClient
from nlp_module.question_classifier import QuestionClassifier
from nlp_module.question_parser import QuestionPaser

client = Neo4jClient(**settings.NEO4J_CONFIG)
classifier = QuestionClassifier()
parser = QuestionPaser()

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def medical_qa(request):
    try:
        # 获取原始问题
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            question = data.get('question', '')
        elif request.method == 'GET':
            question = request.GET.get('question', '')

        print(f"\n=== 原始问题 ===\n{question}")

        if not question:
            return JsonResponse({'error': 'Missing question'}, status=400)

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

        # 结构化响应格式
        return JsonResponse({
            'success': True,
            'code': 200,
            'message': '请求成功',
            'data': {
                'question': question,
                'results': processed_results
            }
        })

    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'code': 400,
            'message': '请求参数格式错误',
            'error': str(e)
        }, status=400)

    except Exception as e:
        print(f"\n!!! 处理异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'code': 500,
            'message': '服务器内部错误',
            'error': str(e)
        }, status=500)
