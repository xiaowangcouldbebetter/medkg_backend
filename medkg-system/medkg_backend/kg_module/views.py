from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging

from .neo4j_client import Neo4jClient
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    client = Neo4jClient(**settings.NEO4J_CONFIG)
    logger.info("知识图谱模块初始化成功")
except Exception as e:
    logger.error(f"知识图谱模块初始化失败: {str(e)}")
    client = None

@api_view(['GET'])
def get_graph_data(request):
    """获取可视化所需的图谱数据"""
    try:
        if client is None:
            return Response({
                'success': False,
                'message': '知识图谱服务未正确初始化'
            }, status=500)
        
        entity_name = request.query_params.get('entity')
        depth = int(request.query_params.get('depth', 1))
        limit = int(request.query_params.get('limit', 20))
        
        # 验证参数
        if not entity_name:
            return Response({
                'success': False,
                'message': '缺少实体名称参数'
            }, status=400)
            
        if depth < 1 or depth > 3:
            depth = 1  # 限制深度范围
        
        if limit < 1 or limit > 50:
            limit = 20  # 限制结果数量
        
        # 根据实体名称查询图谱数据
        cypher = """
        MATCH path = (m)-[r*0..{0}]-(n)
        WHERE m.name = $name
        RETURN path
        LIMIT {1}
        """.format(depth, limit)
        
        # 执行查询
        with client._driver.session() as session:
            result = session.run(cypher, {"name": entity_name})
            graph_data = process_graph_result(result)
        
        return Response({
            'success': True,
            'data': graph_data
        })
        
    except Exception as e:
        logger.exception(f"获取图谱数据失败: {str(e)}")
        return Response({
            'success': False,
            'message': f'获取图谱数据失败: {str(e)}'
        }, status=500)

def process_graph_result(result):
    """处理图谱查询结果为前端可用的格式"""
    nodes = {}
    relationships = {}
    
    for record in result:
        path = record["path"]
        
        # 处理路径中的所有节点
        for node in path.nodes:
            # 避免重复节点
            if node.id not in nodes:
                # 提取节点属性
                node_props = dict(node.items())
                node_label = list(node.labels)[0] if node.labels else "Unknown"
                
                nodes[node.id] = {
                    "id": str(node.id),
                    "label": node_props.get("name", ""),
                    "type": node_label,
                    "properties": node_props
                }
        
        # 处理路径中的所有关系
        for rel in path.relationships:
            # 避免重复关系
            if rel.id not in relationships:
                # 提取关系属性
                rel_props = dict(rel.items())
                rel_type = rel.type
                
                relationships[rel.id] = {
                    "id": str(rel.id),
                    "source": str(rel.start_node.id),
                    "target": str(rel.end_node.id),
                    "type": rel_type,
                    "properties": rel_props
                }
    
    # 转换为列表
    return {
        "nodes": list(nodes.values()),
        "relationships": list(relationships.values())
    }

@api_view(['GET'])
def entity_search(request):
    """
    搜索知识图谱实体API
    
    参数:
        keyword: 搜索关键词
        entity_type: 实体类型 (可选)
    """
    try:
        keyword = request.query_params.get('keyword', '')
        entity_type = request.query_params.get('entity_type', None)
        
        if not keyword:
            return Response({'success': False, 'message': '缺少关键词参数'}, status=400)
            
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 执行搜索
        results = client.get_entity_by_name(keyword, entity_type)
        
        return Response({
            'success': True,
            'message': '搜索成功',
            'data': results
        })
        
    except Exception as e:
        logger.exception(f"实体搜索失败: {str(e)}")
        return Response({'success': False, 'message': f'搜索失败: {str(e)}'}, status=500)

@api_view(['GET'])
def entity_relations(request):
    """
    获取实体关系API
    
    参数:
        name: 实体名称
        relation_type: 关系类型 (可选)
        entity_type: 实体类型 (可选)
    """
    try:
        name = request.query_params.get('name', '')
        relation_type = request.query_params.get('relation_type', None)
        entity_type = request.query_params.get('entity_type', None)
        
        if not name:
            return Response({'success': False, 'message': '缺少实体名称参数'}, status=400)
            
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 执行查询
        results = client.get_entity_relations(name, relation_type, entity_type)
        
        return Response({
            'success': True,
            'message': '查询成功',
            'data': results
        })
        
    except Exception as e:
        logger.exception(f"实体关系查询失败: {str(e)}")
        return Response({'success': False, 'message': f'查询失败: {str(e)}'}, status=500)
        
@api_view(['GET'])
def disease_info(request):
    """
    获取疾病详情API
    
    参数:
        name: 疾病名称
    """
    try:
        name = request.query_params.get('name', '')
        
        if not name:
            return Response({'success': False, 'message': '缺少疾病名称参数'}, status=400)
            
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 执行查询
        result = client.get_disease_info(name)
        
        if not result:
            return Response({
                'success': False,
                'message': f'未找到疾病: {name}'
            }, status=404)
        
        return Response({
            'success': True,
            'message': '查询成功',
            'data': result
        })
        
    except Exception as e:
        logger.exception(f"疾病信息查询失败: {str(e)}")
        return Response({'success': False, 'message': f'查询失败: {str(e)}'}, status=500)

@api_view(['GET'])
def similar_diseases(request):
    """
    获取相似疾病API
    
    参数:
        name: 疾病名称
        limit: 结果数量限制(可选)
    """
    try:
        name = request.query_params.get('name', '')
        limit = request.query_params.get('limit', 10)
        
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
            
        if not name:
            return Response({'success': False, 'message': '缺少疾病名称参数'}, status=400)
            
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 执行查询
        results = client.get_similar_diseases(name, limit)
        
        return Response({
            'success': True,
            'message': '查询成功',
            'data': results
        })
        
    except Exception as e:
        logger.exception(f"相似疾病查询失败: {str(e)}")
        return Response({'success': False, 'message': f'查询失败: {str(e)}'}, status=500)

@api_view(['GET'])
def entity_types(request):
    """
    获取实体类型API
    """
    try:
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 返回所有实体类型
        return Response({
            'success': True,
            'message': '查询成功',
            'data': client.ENTITY_TYPES
        })
        
    except Exception as e:
        logger.exception(f"实体类型查询失败: {str(e)}")
        return Response({'success': False, 'message': f'查询失败: {str(e)}'}, status=500)

@api_view(['GET'])
def relation_types(request):
    """
    获取关系类型API
    """
    try:
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 返回所有关系类型
        return Response({
            'success': True,
            'message': '查询成功',
            'data': client.RELATION_TYPES
        })
        
    except Exception as e:
        logger.exception(f"关系类型查询失败: {str(e)}")
        return Response({'success': False, 'message': f'查询失败: {str(e)}'}, status=500)

@api_view(['GET'])
def entity_statistics(request):
    """
    获取实体统计信息API
    """
    try:
        # 获取Neo4j客户端
        from kg_module.neo4j_client import Neo4jClient
        client = Neo4jClient(**settings.NEO4J_CONFIG)
        
        # 获取统计信息
        stats = client.get_entity_count_by_type()
        
        # 添加中文名称
        for entity_type, count in stats.items():
            stats[entity_type] = {
                'count': count,
                'name': client.ENTITY_TYPES.get(entity_type, '未知类型')
            }
        
        return Response({
            'success': True,
            'message': '查询成功',
            'data': stats
        })
        
    except Exception as e:
        logger.exception(f"实体统计查询失败: {str(e)}")
        return Response({'success': False, 'message': f'查询失败: {str(e)}'}, status=500) 