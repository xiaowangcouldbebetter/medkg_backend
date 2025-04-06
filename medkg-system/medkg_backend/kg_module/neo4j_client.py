# kg_module/neo4j_client.py

from neo4j import GraphDatabase
import logging
from functools import lru_cache, wraps
from typing import List, Dict, Any, Optional, Union, Tuple
import time
from neo4j.exceptions import ServiceUnavailable, ClientError
from django.conf import settings
from utils.performance_monitor import time_function

logger = logging.getLogger(__name__)

# 方便重用的类型定义
QueryResult = Dict[str, Any]
QueryParams = Dict[str, Any]

def retry_on_connection_error(max_retries=3, delay=1):
    """Neo4j连接错误重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(self, *args, **kwargs)
                except (ServiceUnavailable, ConnectionError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"连接Neo4j失败，已达到最大重试次数: {str(e)}")
                        raise
                    logger.warning(f"连接Neo4j失败，{delay}秒后重试 ({retries}/{max_retries}): {str(e)}")
                    time.sleep(delay)
                    # 重新初始化连接
                    self._initialize_driver()
        return wrapper
    return decorator

class Neo4jClient:
    """Neo4j图数据库客户端"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        """
        初始化Neo4j客户端
        
        Args:
            uri: Neo4j数据库URI
            user: 用户名
            password: 密码
            database: 数据库名称
        """
        # 单例初始化保护
        if self._initialized:
            return
            
        # 设置属性
        self.uri = uri or getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
        self.user = user or getattr(settings, 'NEO4J_USER', 'neo4j')
        self.password = password or getattr(settings, 'NEO4J_PASSWORD', 'neo4j')
        self.database = database or getattr(settings, 'NEO4J_DATABASE', None)
        
        # 初始化驱动
        self.driver = None
        self._initialize_driver()
        
        # 完成初始化
        self._initialized = True
    
    def _initialize_driver(self):
        """初始化Neo4j驱动"""
        try:
            # 关闭现有驱动
            if self.driver:
                try:
                    self.driver.close()
                except Exception as e:
                    logger.warning(f"关闭Neo4j驱动出错: {str(e)}")
            
            # 创建新驱动
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password),
                max_connection_lifetime=3600,  # 连接最长生命周期1小时
                max_connection_pool_size=50,   # 连接池大小
                connection_acquisition_timeout=60  # 获取连接超时时间
            )
            
            # 验证连接
            self._verify_connectivity()
            logger.info(f"连接到Neo4j数据库: {self.uri}" + 
                       (f", 数据库: {self.database}" if self.database else ""))
                       
        except Exception as e:
            logger.error(f"Neo4j初始化失败: {str(e)}")
            self.driver = None
            raise
    
    def _verify_connectivity(self):
        """验证Neo4j连接有效性"""
        if not self.driver:
            raise ConnectionError("Neo4j驱动未初始化")
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record.get("test") == 1:
                    return True
                raise ConnectionError("Neo4j连接测试失败")
        except Exception as e:
            logger.error(f"Neo4j连接验证失败: {str(e)}")
            raise ConnectionError(f"Neo4j连接验证失败: {str(e)}")
    
    def close(self):
        """关闭Neo4j连接"""
        if self.driver:
            try:
                self.driver.close()
                logger.info("Neo4j连接已关闭")
            except Exception as e:
                logger.error(f"关闭Neo4j连接出错: {str(e)}")
            finally:
                self.driver = None
    
    @retry_on_connection_error()
    @time_function
    def execute_query(self, query: str, params: Optional[Dict] = None, timeout: int = 30) -> List[Dict]:
        """
        执行Neo4j查询
        
        Args:
            query: Cypher查询语句
            params: 查询参数
            timeout: 查询超时时间(秒)
            
        Returns:
            查询结果列表
        """
        if not self.driver:
            logger.error("Neo4j驱动未初始化，无法执行查询")
            return []
            
        start_time = time.time()
        results = []
        
        try:
            with self.driver.session(database=self.database) as session:
                # 添加超时参数
                if timeout:
                    # 使用apoc.util.sleep(0)触发超时并限制结果数量
                    # 注意：这依赖APOC插件
                    full_query = f"CALL apoc.util.sleep(0) WITH 1 as dummy CALL {{ {query} }} WITH * LIMIT 1000"
                else:
                    full_query = query
                    
                result = session.run(full_query, params, timeout=timeout)
                
                # 处理结果
                for record in result:
                    results.append(dict(record))
                    
            elapsed_time = time.time() - start_time
            logger.debug(f"Neo4j查询执行时间: {elapsed_time:.4f}秒，返回 {len(results)} 条结果")
            
            return results
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Neo4j查询失败 ({elapsed_time:.4f}秒): {str(e)}\n查询: {query}\n参数: {params}")
            return []
    
    @retry_on_connection_error()
    @time_function
    def execute_query_set(self, query_set: List[Dict]) -> List[Dict]:
        """
        执行一组查询
        
        Args:
            query_set: 查询集合，每个元素包含sql和question_type
            
        Returns:
            所有查询结果的合并列表
        """
        if not query_set:
            return []
            
        results = []
        
        for query_item in query_set:
            query = query_item.get('sql')
            if not query:
                continue
                
            query_type = query_item.get('question_type', '')
            logger.debug(f"执行查询 - 类型: {query_type}")
            
            # 获取查询参数
            params = query_item.get('params', {})
            
            # 执行查询
            query_results = self.execute_query(query, params)
            
            if query_results:
                # 转换和合并结果
                formatted_results = self._format_results(query_results, query_type)
                results.extend(formatted_results)
                
        return results
    
    def _format_results(self, results: List[Dict], question_type: str) -> List[Dict]:
        """
        格式化Neo4j查询结果
        
        Args:
            results: 原始查询结果
            question_type: 问题类型
            
        Returns:
            格式化后的结果列表
        """
        formatted_results = []
        entity_results = {}  # 用于合并同一实体的结果
        
        # 不同问题类型的格式化逻辑
        if question_type.endswith('_symptom'):
            # 疾病症状
            for record in results:
                disease = record.get('n', {}).get('name', '')
                symptom = record.get('m', {}).get('name', '')
                
                if disease not in entity_results:
                    entity_results[disease] = {
                        'main_entity': disease,
                        'properties': {},
                        'relations': []
                    }
                
                if symptom:
                    entity_results[disease]['relations'].append({
                        'source': disease,
                        'relation': '症状',
                        'target': symptom
                    })
                    
        elif question_type.endswith('_cause'):
            # 疾病病因
            for record in results:
                disease = record.get('n', {}).get('name', '')
                cause = record.get('m', {}).get('cause', '')
                
                if disease not in entity_results:
                    entity_results[disease] = {
                        'main_entity': disease,
                        'properties': {},
                        'relations': []
                    }
                    
                if cause:
                    entity_results[disease]['properties']['病因'] = cause
                    
        # 通用结果处理逻辑
        else:
            for record in results:
                # 提取主实体
                main_entity = None
                for key, value in record.items():
                    if isinstance(value, dict) and 'name' in value:
                        main_entity = value.get('name', '')
                        break
                
                if not main_entity:
                    continue
                
                # 如果是新实体，创建结果项
                if main_entity not in entity_results:
                    entity_results[main_entity] = {
                        'main_entity': main_entity,
                        'properties': {},
                        'relations': []
                    }
                
                # 处理所有关系
                for key, value in record.items():
                    if key == 'r' and isinstance(value, dict):
                        # 关系属性
                        rel_type = value.get('type', '关联')
                        start_node = None
                        end_node = None
                        
                        # 找出关系的起止节点
                        for node_key, node_val in record.items():
                            if isinstance(node_val, dict) and 'name' in node_val:
                                if node_key != 'm':  # 假设m是目标节点
                                    start_node = node_val.get('name', '')
                                else:
                                    end_node = node_val.get('name', '')
                        
                        if start_node and end_node:
                            entity_results[main_entity]['relations'].append({
                                'source': start_node,
                                'relation': rel_type,
                                'target': end_node
                            })
                    
                    # 处理节点属性
                    elif isinstance(value, dict):
                        for prop_key, prop_val in value.items():
                            if prop_key != 'name' and prop_val:
                                entity_results[main_entity]['properties'][prop_key] = prop_val
        
        # 将字典转换为列表
        for entity, result in entity_results.items():
            formatted_results.append(result)
        
        return formatted_results
    
    # 实体类型常量定义
    ENTITY_TYPES = {
        'Disease': '疾病',
        'Symptom': '疾病症状',
        'Check': '诊断检查项目',
        'Department': '医疗科目',
        'Drug': '药品',
        'Food': '食物',
        'Producer': '在售药品'
    }
    
    # 关系类型常量定义
    RELATION_TYPES = {
        'belongs_to': '属于',
        'common_drug': '疾病常用药品',
        'do_eat': '疾病宜吃食物',
        'drugs_of': '药品在售药品',
        'need_check': '疾病所需检查',
        'no_eat': '疾病忌吃食物',
        'recommand_drug': '疾病推荐药品',
        'recommand_eat': '疾病推荐食谱',
        'has_symptom': '疾病症状',
        'acompany_with': '疾病并发疾病'
    }
    
    # 属性类型常量定义
    PROPERTY_TYPES = {
        'name': '疾病名称',
        'desc': '疾病简介',
        'cause': '疾病病因',
        'prevent': '预防措施',
        'cure_lasttime': '治疗周期',
        'cure_way': '治疗方式',
        'cured_prob': '治愈概率',
        'easy_get': '疾病易感人群'
    }

    @retry_on_connection_error()
    @time_function
    def get_entity_by_name(self, name: str, entity_type: str = None) -> List[Dict]:
        """
        根据实体名称获取实体信息
        
        Args:
            name: 实体名称或关键词
            entity_type: 实体类型，可选 Disease/Symptom/Check/Department/Drug/Food/Producer
            
        Returns:
            符合条件的实体列表
        """
        if entity_type and entity_type not in self.ENTITY_TYPES:
            logger.warning(f"无效的实体类型: {entity_type}")
            return []
            
        if entity_type:
            # 查询特定类型的实体
            query = f"""
            MATCH (n:{entity_type})
            WHERE n.name CONTAINS $name
            RETURN n
            LIMIT 20
            """
        else:
            # 查询所有类型的实体
            query = """
            MATCH (n)
            WHERE n.name CONTAINS $name
            RETURN n, labels(n) as types
            LIMIT 20
            """
            
        params = {'name': name}
        results = self.execute_query(query, params)
        
        return results
    
    @retry_on_connection_error()
    @time_function
    def get_entity_relations(self, entity_name: str, relation_type: str = None, entity_type: str = None) -> List[Dict]:
        """
        获取实体的关系
        
        Args:
            entity_name: 实体名称
            relation_type: 关系类型，如belongs_to, common_drug等
            entity_type: 实体类型，如Disease, Drug等
            
        Returns:
            实体关系列表
        """
        if relation_type and relation_type not in self.RELATION_TYPES:
            logger.warning(f"无效的关系类型: {relation_type}")
            return []

        if entity_type and entity_type not in self.ENTITY_TYPES:
            logger.warning(f"无效的实体类型: {entity_type}")
            return []
            
        # 构建查询条件
        entity_condition = ""
        if entity_type:
            entity_condition = f":{entity_type}"
            
        relation_condition = ""
        if relation_type:
            relation_condition = f":{relation_type}"
        
        # 查询实体的所有关系
        query = f"""
        MATCH (n{entity_condition} {{name: $name}})-[r{relation_condition}]->(m)
        RETURN n.name as source, type(r) as relation, m.name as target, labels(m) as target_type
        UNION
        MATCH (m)-[r{relation_condition}]->(n{entity_condition} {{name: $name}})
        RETURN m.name as source, type(r) as relation, n.name as target, labels(n) as target_type
        LIMIT 100
        """
        
        params = {'name': entity_name}
        results = self.execute_query(query, params)
        
        return results
    
    @retry_on_connection_error()
    @time_function
    def get_disease_info(self, disease_name: str) -> Dict:
        """
        获取疾病的详细信息，包括症状、治疗方式、检查等
        
        Args:
            disease_name: 疾病名称
            
        Returns:
            疾病信息字典
        """
        query = """
        MATCH (d:Disease {name: $name})
        OPTIONAL MATCH (d)-[:has_symptom]->(s:Symptom)
        OPTIONAL MATCH (d)-[:need_check]->(c:Check)
        OPTIONAL MATCH (d)-[:recommand_drug]->(drug:Drug)
        OPTIONAL MATCH (d)-[:acompany_with]->(disease:Disease)
        OPTIONAL MATCH (d)-[:recommand_eat]->(food:Food)
        OPTIONAL MATCH (d)-[:no_eat]->(nofood:Food)
        RETURN d,
            collect(distinct s.name) as symptoms,
            collect(distinct c.name) as checks,
            collect(distinct drug.name) as drugs,
            collect(distinct disease.name) as related_diseases,
            collect(distinct food.name) as recommended_foods,
            collect(distinct nofood.name) as avoid_foods
        """
        
        params = {'name': disease_name}
        results = self.execute_query(query, params)
        
        if not results:
            return {}
            
        # 提取结果并格式化
        result = results[0]
        disease_info = dict(result['d'])
        
        disease_info.update({
            'symptoms': result.get('symptoms', []),
            'checks': result.get('checks', []),
            'drugs': result.get('drugs', []),
            'related_diseases': result.get('related_diseases', []),
            'recommended_foods': result.get('recommended_foods', []),
            'avoid_foods': result.get('avoid_foods', [])
        })
        
        return disease_info
    
    @retry_on_connection_error()
    @time_function
    def search_entity_by_type(self, keyword: str, entity_types: List[str] = None, limit: int = 20) -> List[Dict]:
        """
        按类型搜索实体
        
        Args:
            keyword: 搜索关键词
            entity_types: 实体类型列表，为空则搜索所有类型
            limit: 结果数量限制
            
        Returns:
            搜索结果列表
        """
        if entity_types:
            # 验证实体类型
            valid_types = [t for t in entity_types if t in self.ENTITY_TYPES]
            if not valid_types:
                logger.warning(f"无有效的实体类型: {entity_types}")
                return []
                
            # 构建类型条件
            type_conditions = " OR ".join([f"n:{t}" for t in valid_types])
            
            query = f"""
            MATCH (n)
            WHERE ({type_conditions}) AND n.name CONTAINS $keyword
            RETURN n.name as name, labels(n) as types
            LIMIT {limit}
            """
        else:
            # 搜索所有类型
            query = f"""
            MATCH (n)
            WHERE n.name CONTAINS $keyword
            RETURN n.name as name, labels(n) as types
            LIMIT {limit}
            """
            
        params = {'keyword': keyword}
        results = self.execute_query(query, params)
        
        # 格式化结果
        formatted_results = []
        for record in results:
            entity_type = record['types'][0] if record.get('types') else "Unknown"
            formatted_results.append({
                'name': record['name'],
                'type': entity_type,
                'type_cn': self.ENTITY_TYPES.get(entity_type, "未知类型")
            })
            
        return formatted_results
    
    @retry_on_connection_error()
    @time_function
    def get_similar_diseases(self, disease_name: str, limit: int = 10) -> List[Dict]:
        """
        获取相似疾病，基于共同症状和并发关系
        
        Args:
            disease_name: 疾病名称
            limit: 结果数量限制
            
        Returns:
            相似疾病列表
        """
        query = """
        MATCH (d:Disease {name: $name})-[:has_symptom]->(s:Symptom)<-[:has_symptom]-(similar:Disease)
        WHERE similar.name <> $name
        WITH similar, count(s) as common_symptoms
        ORDER BY common_symptoms DESC
        LIMIT $limit
        RETURN similar.name as disease, common_symptoms,
               'symptom' as similarity_type
        
        UNION
        
        MATCH (d:Disease {name: $name})-[:acompany_with]-(similar:Disease)
        WHERE similar.name <> $name
        RETURN similar.name as disease, 1 as common_symptoms,
               'acompany' as similarity_type
        LIMIT $limit
        """
        
        params = {'name': disease_name, 'limit': limit}
        results = self.execute_query(query, params)
        
        return results
        
    @retry_on_connection_error()
    @time_function
    def get_entity_count_by_type(self) -> Dict[str, int]:
        """
        获取各类型实体的数量
        
        Returns:
            各类型实体数量字典
        """
        # 构建查询
        entity_types = list(self.ENTITY_TYPES.keys())
        queries = []
        
        for entity_type in entity_types:
            queries.append(f"MATCH (n:{entity_type}) RETURN '{entity_type}' as type, count(n) as count")
            
        query = " UNION ".join(queries)
        
        # 执行查询
        results = self.execute_query(query)
        
        # 格式化结果
        count_dict = {}
        for record in results:
            entity_type = record['type']
            count = record['count']
            count_dict[entity_type] = count
            
        return count_dict
