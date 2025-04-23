"""
知识图谱视图模块
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import logging
import traceback
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
        # 获取限制参数和实体类型
        limit = request.GET.get('limit', 25)
        entity_type = request.GET.get('entity_type', 'Disease')
        query_type = request.GET.get('query_type', 'basic')
        
        try:
            limit = int(limit)
        except:
            limit = 25
            
        neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 根据查询类型构建不同的查询
        if query_type == 'disease_only':
            # 只返回疾病节点
            query = f"""
            MATCH (n:Disease) 
            RETURN n 
            LIMIT {limit}
            """
            
            # 执行查询
            with neo4j_client._driver.session() as session:
                result = session.run(query).data()
                
                # 处理结果，构建可视化所需的数据格式
                nodes = []
                for item in result:
                    node = item['n']
                    if 'name' in node:
                        nodes.append({
                            'id': node['name'],
                            'label': node['name'],
                            'group': 'Disease'
                        })
                
                # 构建响应数据
                data = {
                    'nodes': nodes,
                    'links': []
                }
        else:
            # 基本关系查询
            query = f"""
            MATCH (m:{entity_type})-[r]->(n)
            RETURN m.name as source, type(r) as relation, n.name as target, labels(m)[0] as sourceType, labels(n)[0] as targetType
            LIMIT {limit}
            """
            
            # 执行查询
            with neo4j_client._driver.session() as session:
                result = session.run(query).data()
                
                # 处理结果，构建可视化所需的数据格式
                nodes_dict = {}
                links = []
                
                for item in result:
                    source = item['source']
                    target = item['target']
                    relation = item['relation']
                    source_type = item['sourceType']
                    target_type = item['targetType']
                    
                    if source and target:  # 确保源和目标都有值
                        # 添加节点到字典
                        if source not in nodes_dict:
                            nodes_dict[source] = {'id': source, 'label': source, 'group': source_type}
                        if target not in nodes_dict:
                            nodes_dict[target] = {'id': target, 'label': target, 'group': target_type}
                        
                        # 添加关系
                        links.append({
                            'source': source,
                            'target': target,
                            'relation': relation
                        })
                
                # 为节点构建对象
                nodes = list(nodes_dict.values())
                
                # 构建响应数据
                data = {
                    'nodes': nodes,
                    'links': links
                }
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        # 记录错误到系统日志
        error_msg = f'获取知识图谱可视化数据失败: {str(e)}'
        SystemLog.objects.create(
            level='ERROR',
            module='kg_visualization',
            message=error_msg,
            trace=traceback.format_exc()
        )
        return JsonResponse({'success': False, 'message': error_msg}, status=500)

# 更新知识图谱
@csrf_exempt
@require_http_methods(['POST'])
def kg_update_view(request):
    """更新知识图谱的视图函数"""
    try:
        # 检查是否有文件上传
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            
            # 检查文件类型
            if not uploaded_file.name.endswith(('.json', '.csv', '.txt')):
                return JsonResponse({
                    'success': False,
                    'message': '不支持的文件格式，请上传JSON、CSV或TXT格式的文件'
                }, status=400)
                
            # 保存上传的文件到临时位置
            import os
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            file_path = default_storage.save(f'kg_upload/{uploaded_file.name}', ContentFile(uploaded_file.read()))
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
            
            # 创建知识图谱更新器并处理文件
            updater = KnowledgeGraphUpdater()
            updater.neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
            
            # 根据文件类型不同调用不同的处理函数
            if uploaded_file.name.endswith('.json'):
                result = updater.process_json_file(file_path)
            elif uploaded_file.name.endswith('.csv'):
                result = updater.process_csv_file(file_path)
            else:
                result = updater.process_txt_file(file_path)
                
            # 记录更新信息
            SystemLog.objects.create(
                level='INFO',
                module='kg_update',
                message=f'通过文件更新知识图谱成功，文件名: {uploaded_file.name}, 添加节点: {result["nodes_added"]}, 添加关系: {result["relations_added"]}'
            )
            
            return JsonResponse({
                'success': True,
                'message': '文件处理成功，已更新知识图谱',
                'data': {
                    'filename': uploaded_file.name,
                    'nodes_added': result['nodes_added'],
                    'relations_added': result['relations_added']
                }
            })
            
        else:
            # 解析JSON请求数据
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