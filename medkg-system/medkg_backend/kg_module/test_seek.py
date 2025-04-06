from neo4j import GraphDatabase

# 数据库配置
NEO4J_CONFIG = {
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': '012134whz'  # 修改为实际密码
}


class Neo4jClient:
    def __init__(self, uri, user, password):
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
        # 关闭数据库连接
        self._driver.close()

    def query_disease_symptom(self, disease_name):
        # 查询指定疾病的名称和治疗方式
        with self._driver.session() as session:
            # 正确的参数化查询语句
            query = (
                "MATCH (m:Disease {name: $disease_name}) "
                "RETURN m.name as name, m.cure_way as cure_way"
            )
            result = session.run(query, disease_name=disease_name)
            return [dict(record) for record in result]

# 创建 Neo4j 客户端实例
client = Neo4jClient(**NEO4J_CONFIG)

# 定义疾病名称变量
disease_name = "肺气肿"

# 调用查询函数
results = client.query_disease_symptom(disease_name)

# 输出查询结果
if results:
    for result in results:
        print(f"疾病名称: {result['name']}, 治疗方式: {result['cure_way']}")
else:
    print(f"未找到疾病 '{disease_name}' 的相关信息。")


# 关闭数据库连接
client.close()