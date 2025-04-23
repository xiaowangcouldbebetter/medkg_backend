#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗问题分类器
使用AC自动机进行快速特征匹配，支持7类医疗实体识别和17种问题分类
"""
import os
import ahocorasick
from typing import Dict, List, Set, Union


class QuestionClassifier:
    def __init__(self):
        """初始化问题分类器"""
        # 加载字典文件
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        dict_files = {
            'disease': os.path.join(cur_dir, 'dict/disease.txt'),
            'department': os.path.join(cur_dir, 'dict/department.txt'),
            'check': os.path.join(cur_dir, 'dict/check.txt'),
            'drug': os.path.join(cur_dir, 'dict/drug.txt'),
            'food': os.path.join(cur_dir, 'dict/food.txt'),
            'producer': os.path.join(cur_dir, 'dict/producer.txt'),
            'symptom': os.path.join(cur_dir, 'dict/symptom.txt'),
            'deny': os.path.join(cur_dir, 'dict/deny.txt')
        }
        
        # 加载词典
        self.word_dict = {}
        for key, file_path in dict_files.items():
            with open(file_path, encoding='utf-8') as f:
                self.word_dict[key] = [line.strip() for line in f if line.strip()]
                
        # 构建领域词表
        self.region_words = set()
        for key in ['department', 'disease', 'check', 'drug', 'food', 'producer', 'symptom']:
            self.region_words.update(self.word_dict[key])
            
        # 构建AC自动机
        self.region_tree = self.build_actree(list(self.region_words))
        self.wdtype_dict = self.build_wdtype_dict()
        
        # 问题类型关键词
        self.question_config = {
            'symptom': set(['症状', '表征', '现象', '症候', '表现']),
            'cause': set(['原因', '成因', '为什么', '怎么会', '怎样才']),
            'acompany': set(['并发症', '并发', '一起发生', '一并发生']),
            'food': set(['饮食', '饮用', '吃', '食', '伙食', '膳食']),
            'drug': set(['药', '药品', '用药', '胶囊', '口服液']),
            'prevent': set(['预防', '防范', '抵制', '抵御', '防止']),
            'lasttime': set(['周期', '多久', '多长时间', '多少时间']),
            'cureway': set(['怎么治疗', '如何医治', '怎么医治', '怎么治']),
            'cureprob': set(['多大概率能治好', '多大几率能治好', '治好希望大么']),
            'easyget': set(['易感人群', '容易感染', '易发人群', '什么人']),
            'check': set(['检查', '检查项目', '查出', '检查']),
            'belong': set(['属于什么科', '属于', '什么科', '科室']),
            'cure': set(['治疗什么', '治啥', '治疗啥', '医治啥'])
        }
        
    def classify(self, question):
        """问题分类主函数"""
        # 提取问题中的实体
        medical_dict = self.extract_entities(question)
        if not medical_dict:
            return {}
            
        # 确定问题类型
        entity_types = {t for types in medical_dict.values() for t in types}
        question_types = self._determine_question_type(question, entity_types)
        
        # 返回分类结果
        return {
            'args': medical_dict,
            'question_types': question_types or self._get_default_type(entity_types)
        }
        
    def build_actree(self, wordlist):
        """构建AC自动机"""
        actree = ahocorasick.Automaton()
        for i, word in enumerate(wordlist):
            actree.add_word(word, (i, word))
        actree.make_automaton()
        return actree
        
    def build_wdtype_dict(self):
        """构建词类型映射字典"""
        wdtype_dict = {}
        for word in self.region_words:
            wdtype_dict[word] = []
            for t, words in self.word_dict.items():
                if word in words:
                    wdtype_dict[word].append(t)
        return wdtype_dict
        
    def extract_entities(self, text):
        """实体抽取"""
        medical_dict = {}
        for end_index, (_, word) in self.region_tree.iter(text):
            if word not in medical_dict:
                medical_dict[word] = self.wdtype_dict[word]
        return medical_dict
        
    def _determine_question_type(self, question, entity_types):
        """确定问题类型"""
        question_types = []
        
        # 症状相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['symptom']):
            question_types.append('disease_symptom')
        if 'symptom' in entity_types and self._contains_any(question, self.question_config['symptom']):
            question_types.append('symptom_disease')
            
        # 病因相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['cause']):
            question_types.append('disease_cause')
            
        # 并发症相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['acompany']):
            question_types.append('disease_acompany')
            
        # 食物相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['food']):
            # 判断是否包含否定词
            if self._contains_any(question, self.word_dict['deny']):
                question_types.append('disease_not_food')
            else:
                question_types.append('disease_do_food')
                
        # 药物相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['drug']):
            question_types.append('disease_drug')
        if 'drug' in entity_types and self._contains_any(question, self.question_config['cure']):
            question_types.append('drug_disease')
            
        # 检查相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['check']):
            question_types.append('disease_check')
        if 'check' in entity_types and self._contains_any(question, self.question_config['cure']):
            question_types.append('check_disease')
            
        # 预防相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['prevent']):
            question_types.append('disease_prevent')
            
        # 治疗周期相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['lasttime']):
            question_types.append('disease_lasttime')
            
        # 治疗方式相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['cureway']):
            question_types.append('disease_cureway')
            
        # 治愈率相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['cureprob']):
            question_types.append('disease_cureprob')
            
        # 易感人群相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['easyget']):
            question_types.append('disease_easyget')
            
        # 科室相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['belong']):
            question_types.append('disease_department')
            
        return question_types
        
    def _contains_any(self, text, keywords):
        """判断文本是否包含关键词"""
        for keyword in keywords:
            if keyword in text:
                return True
        return False
        
    def _get_default_type(self, entity_types):
        """获取默认问题类型"""
        if 'disease' in entity_types:
            return ['disease_desc']
        if 'symptom' in entity_types:
            return ['symptom_disease']
        return []


if __name__ == '__main__':
    classifier = QuestionClassifier()
    question = "高血压的症状有哪些？"
    result = classifier.classify(question)
    print(result)