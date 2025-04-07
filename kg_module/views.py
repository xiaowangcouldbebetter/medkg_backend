"""
知识图谱视图模块
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from .neo4j_client import Neo4jClient
from .knowledge_graph_updater import KnowledgeGraphUpdater
from accounts.views import log_system_event
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from accounts.models import SystemLog

# 获取知识图谱统计信息
@csrf_exempt
@require_http_methods(['GET'])
def kg_statistics_view(request):
    """获取知识图谱统计信息的视图函数"""
    try:
        neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 获取实体数量查询
        entity_count_query = "MATCH (n) RETURN count(n) as entityCount"
        
        # 获取关系数量查询
        relation_count_query = "MATCH ()-[r]->() RETURN count(r) as relationCount"
        
        # 获取实体类型及其数量查询
        entity_types_query = """
        MATCH (n)
        WITH labels(n) as entityType, count(n) as count
        RETURN entityType, count
        ORDER BY count DESC
        """
        
        # 获取关系类型及其数量查询
        relation_types_query = """
        MATCH ()-[r]->()
        WITH type(r) as relationType, count(r) as count
        RETURN relationType, count
        ORDER BY count DESC
        """
        
        # 执行查询并获取结果
        with neo4j_client._driver.session() as session:
            entity_count = session.run(entity_count_query).single()['entityCount']
            relation_count = session.run(relation_count_query).single()['relationCount']
            
            entity_types_result = session.run(entity_types_query).data()
            entity_types = [{'type': r['entityType'][0], 'count': r['count']} for r in entity_types_result]
            
            relation_types_result = session.run(relation_types_query).data()
            relation_types = [{'type': r['relationType'], 'count': r['count']} for r in relation_types_result]
        
        # 构建响应数据
        data = {
            'entityCount': entity_count,
            'relationCount': relation_count,
            'entityTypes': entity_types,
            'relationTypes': relation_types
        }
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        # 记录错误到系统日志
        SystemLog.objects.create(
            level='ERROR',
            module='kg_statistics',
            message=f'获取知识图谱统计信息失败: {str(e)}',
            trace=traceback.format_exc()
        )
        return JsonResponse({'success': False, 'message': f'获取知识图谱统计信息失败: {str(e)}'}, status=500)

# 获取可视化数据
@csrf_exempt
@require_http_methods(['GET'])
def kg_visualization_view(request):
    """获取知识图谱可视化数据的视图函数"""
    try:
        # 获取限制参数，默认为50
        limit = request.GET.get('limit', 50)
        try:
            limit = int(limit)
        except:
            limit = 50
        
        neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 基本查询，获取节点和关系
        query = f"""
        MATCH (m)-[r]->(n)
        RETURN m.name as source, type(r) as relation, n.name as target
        LIMIT {limit}
        """
        
        # 执行查询
        with neo4j_client._driver.session() as session:
            result = session.run(query).data()
            
            # 处理结果，构建可视化所需的数据格式
            nodes = set()
            links = []
            
            for item in result:
                source = item['source']
                target = item['target']
                relation = item['relation']
                
                if source and target:  # 确保源和目标都有值
                    nodes.add(source)
                    nodes.add(target)
                    links.append({
                        'source': source,
                        'target': target,
                        'relation': relation
                    })
            
            # 为节点构建对象
            nodes_data = [{'id': node, 'label': node} for node in nodes]
        
        # 构建响应数据
        data = {
            'nodes': nodes_data,
            'links': links
        }
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        # 记录错误到系统日志
        SystemLog.objects.create(
            level='ERROR',
            module='kg_visualization',
            message=f'获取知识图谱可视化数据失败: {str(e)}',
            trace=traceback.format_exc()
        )
        return JsonResponse({'success': False, 'message': f'获取知识图谱可视化数据失败: {str(e)}'}, status=500)

# 更新知识图谱
@csrf_exempt
@require_http_methods(['POST'])
def kg_update_view(request):
    """更新知识图谱的视图函数"""
    try:
        # 解析请求数据
        data = json.loads(request.body)
        search_term = data.get('search_term')
        
        if not search_term:
            return JsonResponse({'success': False, 'message': '搜索关键词不能为空'}, status=400)
        
        # 创建并初始化知识图谱更新器
        updater = KnowledgeGraphUpdater()
        # 使用配置创建Neo4j客户端
        updater.neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 执行更新操作
        result = updater.update_knowledge_graph(search_term)
        
        # 记录更新信息到系统日志
        SystemLog.objects.create(
            level='INFO',
            module='kg_update',
            message=f'知识图谱更新成功，关键词: {search_term}, 添加节点: {result["nodes_added"]}, 添加关系: {result["relations_added"]}'
        )
        
        return JsonResponse({
            'success': True, 
            'message': '知识图谱更新成功', 
            'data': {
                'search_term': search_term,
                'nodes_added': result['nodes_added'],
                'relations_added': result['relations_added']
            }
        })
    except Exception as e:
        error_msg = f'更新知识图谱失败: {str(e)}'
        
        # 记录错误到系统日志
        SystemLog.objects.create(
            level='ERROR',
            module='kg_update',
            message=error_msg,
            trace=traceback.format_exc()
        )
        
        return JsonResponse({'success': False, 'message': error_msg}, status=500)

# 知识图谱搜索
@api_view(['GET'])
def search_knowledge_graph(request):
    """在知识图谱中搜索"""
    try:
        keyword = request.GET.get('keyword', '')
        if not keyword:
            return Response({
                'success': False,
                'message': '搜索关键词不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        neo4j_client = Neo4jClient()
        
        # 基于关键词搜索节点
        query = """
        MATCH (n)
        WHERE 
          n.name CONTAINS $keyword OR
          n.description CONTAINS $keyword
        RETURN n
        LIMIT 20
        """
        
        results = neo4j_client.execute_query(query, {"keyword": keyword})
        
        # 准备搜索结果
        search_results = []
        for record in results:
            node = record['n']
            search_results.append({
                'id': node['id'] if 'id' in node else id(node),
                'label': list(node.labels)[0],
                'properties': dict(node),
            })
        
        return Response({
            'success': True,
            'results': search_results,
            'count': len(search_results)
        })
    except Exception as e:
        error_msg = f"知识图谱搜索失败: {str(e)}"
        log_system_event("ERROR", "KG_API", error_msg, trace=str(e))
        return Response({
            'success': False,
            'message': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 