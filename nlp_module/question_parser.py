class QuestionPaser:
    # 问题类型到实体类型的映射关系
    QUESTION_MAPPING = {
        'disease_symptom': 'disease',
        'symptom_disease': 'symptom',
        'disease_cause': 'disease',
        'disease_acompany': 'disease',
        'disease_not_food': 'disease',
        'disease_do_food': 'disease',
        'food_not_disease': 'food',
        'food_do_disease': 'food',
        'disease_drug': 'disease',
        'drug_disease': 'drug',
        'disease_check': 'disease',
        'check_disease': 'check',
        'disease_prevent': 'disease',
        'disease_lasttime': 'disease',
        'disease_cureway': 'disease',
        'disease_cureprob': 'disease',
        'disease_easyget': 'disease',
        'disease_desc': 'disease',
        'disease_department': 'disease'
    }

    # Cypher查询模板配置
    SQL_TEMPLATES = {
        'disease_cause': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.cause",
        'disease_prevent': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.prevent",
        'disease_lasttime': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.cure_lasttime",
        'disease_cureprob': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.cured_prob",
        'disease_cureway': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.cure_way",
        'disease_easyget': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.easy_get",
        'disease_desc': "MATCH (m:Disease) WHERE m.name = '{0}' RETURN m.name, m.desc",
        'disease_symptom': "MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) WHERE m.name = '{0}' RETURN m.name, r.name, n.name",
        'symptom_disease': "MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) WHERE n.name = '{0}' RETURN m.name, r.name, n.name",
        'disease_acompany': [
            "MATCH (m:Disease)-[r:acompany_with]->(n:Disease) WHERE m.name = '{0}'",
            "MATCH (m:Disease)<-[r:acompany_with]-(n:Disease) WHERE m.name = '{0}'"
        ],
        'disease_not_food': "MATCH (m:Disease)-[r:no_eat]->(n:Food) WHERE m.name = '{0}' RETURN m.name, r.name, n.name",
        'disease_do_food': [
            "MATCH (m:Disease)-[r:do_eat]->(n:Food) WHERE m.name = '{0}'",
            "MATCH (m:Disease)-[r:recommand_eat]->(n:Food) WHERE m.name = '{0}'"
        ],
        'food_not_disease': "MATCH (m:Disease)-[r:no_eat]->(n:Food) WHERE n.name = '{0}' RETURN m.name, r.name, n.name",
        'food_do_disease': [
            "MATCH (m:Disease)-[r:do_eat]->(n:Food) WHERE n.name = '{0}'",
            "MATCH (m:Disease)-[r:recommand_eat]->(n:Food) WHERE n.name = '{0}'"
        ],
        'disease_drug': [
            "MATCH (m:Disease)-[r:common_drug]->(n:Drug) WHERE m.name = '{0}'",
            "MATCH (m:Disease)-[r:recommand_drug]->(n:Drug) WHERE m.name = '{0}'"
        ],
        'drug_disease': [
            "MATCH (m:Disease)-[r:common_drug]->(n:Drug) WHERE n.name = '{0}'",
            "MATCH (m:Disease)-[r:recommand_drug]->(n:Drug) WHERE n.name = '{0}'"
        ],
        'disease_check': "MATCH (m:Disease)-[r:need_check]->(n:Check) WHERE m.name = '{0}' RETURN m.name, r.name, n.name",
        'check_disease': "MATCH (m:Disease)-[r:need_check]->(n:Check) WHERE n.name = '{0}' RETURN m.name, r.name, n.name",
        'disease_department': "MATCH (m:Disease)-[r:belong_to]->(n:Department) WHERE m.name = '{0}' RETURN m.name, r.name, n.name"
    }

    def build_entitydict(self, args: dict) -> dict:
        """构建实体词典"""
        entity_dict = {}
        for arg, types in args.items():
            for type_ in types:
                entity_dict.setdefault(type_, []).append(arg)
        return entity_dict

    def parser_main(self, res_classify: dict) -> list:
        """主解析方法"""
        if not res_classify:
            return []
            
        entity_dict = self.build_entitydict(res_classify.get('args', {}))
        sql_results = []

        for q_type in res_classify.get('question_types', []):
            entity_type = self.QUESTION_MAPPING.get(q_type)
            if not entity_type or (entities := entity_dict.get(entity_type)) is None:
                continue

            if sql := self.sql_transfer(q_type, entities):
                sql_results.append({
                    'question_type': q_type,
                    'sql': sql
                })

        return sql_results

    def sql_transfer(self, question_type: str, entities: list) -> list:
        """生成Cypher查询语句"""
        if not entities or (templates := self.SQL_TEMPLATES.get(question_type)) is None:
            return []

        # 处理复合查询模板
        if isinstance(templates, list):
            sql_list = []
            for template in templates:
                for entity in entities:
                    # 确保查询语句包含完整的RETURN子句
                    if "RETURN" not in template:
                        sql = f"{template} RETURN m.name, r.name, n.name"
                    else:
                        sql = template
                    sql_list.append(sql.format(entity))
            return sql_list

        # 处理简单查询模板
        return [templates.format(entity) for entity in entities]


# 以下是新的问题解析器实现，可以完全替代上面的代码
class QuestionParser:
    def __init__(self):
        """初始化问题解析器"""
        pass
        
    def parser_main(self, classify_result):
        """问题解析主函数"""
        if not classify_result:
            return []
            
        args = classify_result.get('args', {})
        question_types = classify_result.get('question_types', [])
        
        # 生成查询语句
        queries = []
        for question_type in question_types:
            if question_type == 'disease_symptom':
                queries.extend(self.disease_symptom(args))
            elif question_type == 'symptom_disease':
                queries.extend(self.symptom_disease(args))
            elif question_type == 'disease_cause':
                queries.extend(self.disease_cause(args))
            elif question_type == 'disease_acompany':
                queries.extend(self.disease_acompany(args))
            elif question_type == 'disease_not_food':
                queries.extend(self.disease_not_food(args))
            elif question_type == 'disease_do_food':
                queries.extend(self.disease_do_food(args))
            elif question_type == 'food_not_disease':
                queries.extend(self.food_not_disease(args))
            elif question_type == 'food_do_disease':
                queries.extend(self.food_do_disease(args))
            elif question_type == 'disease_drug':
                queries.extend(self.disease_drug(args))
            elif question_type == 'drug_disease':
                queries.extend(self.drug_disease(args))
            elif question_type == 'disease_check':
                queries.extend(self.disease_check(args))
            elif question_type == 'check_disease':
                queries.extend(self.check_disease(args))
            elif question_type == 'disease_prevent':
                queries.extend(self.disease_prevent(args))
            elif question_type == 'disease_lasttime':
                queries.extend(self.disease_lasttime(args))
            elif question_type == 'disease_cureway':
                queries.extend(self.disease_cureway(args))
            elif question_type == 'disease_cureprob':
                queries.extend(self.disease_cureprob(args))
            elif question_type == 'disease_easyget':
                queries.extend(self.disease_easyget(args))
            elif question_type == 'disease_department':
                queries.extend(self.disease_department(args))
            elif question_type == 'disease_desc':
                queries.extend(self.disease_desc(args))
                
        return queries
        
    def disease_symptom(self, args):
        """疾病症状查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_symptom',
                    'sql': [
                        f"MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def symptom_disease(self, args):
        """症状疾病查询"""
        queries = []
        for symptom in args.keys():
            if 'symptom' in args[symptom]:
                query = {
                    'question_type': 'symptom_disease',
                    'sql': [
                        f"MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) WHERE n.name = '{symptom}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_cause(self, args):
        """疾病病因查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_cause',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.cause"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_acompany(self, args):
        """疾病并发症查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_acompany',
                    'sql': [
                        f"MATCH (m:Disease)-[r:acompany_with]->(n:Disease) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_not_food(self, args):
        """疾病忌口查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_not_food',
                    'sql': [
                        f"MATCH (m:Disease)-[r:not_eat]->(n:Food) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_do_food(self, args):
        """疾病宜吃食物查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_do_food',
                    'sql': [
                        f"MATCH (m:Disease)-[r:do_eat]->(n:Food) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name",
                        f"MATCH (m:Disease)-[r:recommand_eat]->(n:Food) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def food_not_disease(self, args):
        """食物忌吃疾病查询"""
        queries = []
        for food in args.keys():
            if 'food' in args[food]:
                query = {
                    'question_type': 'food_not_disease',
                    'sql': [
                        f"MATCH (m:Disease)-[r:not_eat]->(n:Food) WHERE n.name = '{food}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def food_do_disease(self, args):
        """食物宜吃疾病查询"""
        queries = []
        for food in args.keys():
            if 'food' in args[food]:
                query = {
                    'question_type': 'food_do_disease',
                    'sql': [
                        f"MATCH (m:Disease)-[r:do_eat]->(n:Food) WHERE n.name = '{food}' RETURN m.name, r.name, n.name",
                        f"MATCH (m:Disease)-[r:recommand_eat]->(n:Food) WHERE n.name = '{food}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_drug(self, args):
        """疾病用药查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_drug',
                    'sql': [
                        f"MATCH (m:Disease)-[r:common_drug]->(n:Drug) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name",
                        f"MATCH (m:Disease)-[r:recommand_drug]->(n:Drug) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def drug_disease(self, args):
        """药品治疗疾病查询"""
        queries = []
        for drug in args.keys():
            if 'drug' in args[drug]:
                query = {
                    'question_type': 'drug_disease',
                    'sql': [
                        f"MATCH (m:Disease)-[r:common_drug]->(n:Drug) WHERE n.name = '{drug}' RETURN m.name, r.name, n.name",
                        f"MATCH (m:Disease)-[r:recommand_drug]->(n:Drug) WHERE n.name = '{drug}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_check(self, args):
        """疾病检查查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_check',
                    'sql': [
                        f"MATCH (m:Disease)-[r:need_check]->(n:Check) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def check_disease(self, args):
        """检查疾病查询"""
        queries = []
        for check in args.keys():
            if 'check' in args[check]:
                query = {
                    'question_type': 'check_disease',
                    'sql': [
                        f"MATCH (m:Disease)-[r:need_check]->(n:Check) WHERE n.name = '{check}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_prevent(self, args):
        """疾病预防查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_prevent',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.prevent"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_lasttime(self, args):
        """疾病治疗周期查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_lasttime',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.cure_lasttime"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_cureway(self, args):
        """疾病治疗方法查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_cureway',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.cure_way"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_cureprob(self, args):
        """疾病治愈率查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_cureprob',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.cured_prob"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_easyget(self, args):
        """疾病易感人群查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_easyget',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.easy_get"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_department(self, args):
        """疾病所属科室查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_department',
                    'sql': [
                        f"MATCH (m:Disease)-[r:belong_to]->(n:Department) WHERE m.name = '{disease}' RETURN m.name, r.name, n.name"
                    ]
                }
                queries.append(query)
        return queries
        
    def disease_desc(self, args):
        """疾病描述查询"""
        queries = []
        for disease in args.keys():
            if 'disease' in args[disease]:
                query = {
                    'question_type': 'disease_desc',
                    'sql': [
                        f"MATCH (m:Disease) WHERE m.name = '{disease}' RETURN m.name, m.desc"
                    ]
                }
                queries.append(query)
        return queries

# 保留现有名称以兼容性，但使用新实现
QuestionPaser = QuestionParser

if __name__ == '__main__':
    # 测试代码
    parser = QuestionParser()
    test_data = {
        'args': {'糖尿病': ['disease']},
        'question_types': ['disease_symptom']
    }
    result = parser.parser_main(test_data)
    print(result)
