# kg_module/neo4j_client.py

from neo4j import GraphDatabase

class Neo4jClient:
    def __init__(self, uri, user, password):
        # 初始化Neo4j客户端，连接到指定的Neo4j数据库
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            # 验证连接是否成功
            with self._driver.session() as session:
                result = session.run("RETURN 1")
                if result.single().value() == 1:
                    print("Connected to Neo4j database at", uri)
        except Exception as e:
            # 如果连接失败，打印错误信息并抛出异常
            print("Failed to connect to Neo4j database at", uri)
            raise Exception("Neo4j连接失败: ", e)


    def close(self):
        # 关闭Neo4j客户端连接，释放资源，打印出来提示信息
        print("Closing Neo4j database connection...")
        self._driver.close()
        print("Connection closed.")

    def execute_query(self, query, parameters=None):
        """执行单个Cypher查询"""
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return result.data()

    def execute_query_set(self, query_set):
        """执行查询集合"""
        results = []
        with self._driver.session() as session:
            for query_group in query_set:
                for cypher in query_group.get('sql', []):
                    try:
                        result = session.run(cypher).data()
                        results.extend(result)
                    except Exception as e:
                        print(f"执行查询失败: {cypher}\n错误信息: {str(e)}")
                        continue
        return self._format_results(results)

    def create_entity(self, label, properties):
        """创建实体节点"""
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """
        return self.execute_query(query, {"properties": properties})
        
    def create_relation(self, start_label, start_props, end_label, end_props, rel_type, rel_props=None):
        """创建实体关系"""
        query = f"""
        MATCH (a:{start_label}), (b:{end_label})
        WHERE a.name = $start_name AND b.name = $end_name
        CREATE (a)-[r:{rel_type} $rel_props]->(b)
        RETURN a, r, b
        """
        return self.execute_query(query, {
            "start_name": start_props["name"],
            "end_name": end_props["name"],
            "rel_props": rel_props or {}
        })

    def _format_results(self, raw_data):
        """统一格式化查询结果
        返回结构：
        {
            'main_entity': 主实体名称,
            'relations': 关系数据列表,
            'properties': 实体属性字典
        }
        """
        formatted = []
        for item in raw_data:
            # 提取主实体名称（m开头的节点）
            main_entity = item.get('m.name', '') or item.get('name', '')

            # 动态收集所有m.开头的属性
            properties = {
                key.split('.')[1]: value
                for key, value in item.items()
                if key.startswith('m.') and key != 'm.name'
            }

            # 收集关系数据
            relations = {
                'source': main_entity,
                'relation': item.get('r.name', ''),
                'target': item.get('n.name', '')
            } if 'r.name' in item and 'n.name' in item else None

            formatted.append({
                'main_entity': main_entity,
                'relations': relations if relations and relations['target'] else None,
                'properties': properties if properties else None
            })

        return formatted
