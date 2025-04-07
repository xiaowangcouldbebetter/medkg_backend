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
        'disease_desc': 'disease'
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
            "MATCH (m:Disease)-[r:acompany_with]->(n:Disease) WHERE n.name = '{0}'"
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
        'check_disease': "MATCH (m:Disease)-[r:need_check]->(n:Check) WHERE n.name = '{0}' RETURN m.name, r.name, n.name"
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
        entity_dict = self.build_entitydict(res_classify['args'])
        sql_results = []

        for q_type in res_classify['question_types']:
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
            return [
                f"{t.format(entity)} RETURN m.name, r.name, n.name"
                for t in templates
                for entity in entities
            ]

        # 处理简单查询模板
        return [templates.format(entity) for entity in entities]


if __name__ == '__main__':
    handler = QuestionPaser()
