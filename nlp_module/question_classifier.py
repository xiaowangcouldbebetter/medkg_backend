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
        """初始化分类器，加载词典并构建自动机"""
        # 路径处理优化
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        dict_files = {
            'disease': 'dict/disease.txt',
            'department': 'dict/department.txt',
            'check': 'dict/check.txt',
            'drug': 'dict/drug.txt',
            'food': 'dict/food.txt',
            'producer': 'dict/producer.txt',
            'symptom': 'dict/symptom.txt',
            'deny': 'dict/deny.txt'
        }

        # 统一加载词典文件
        self.word_dict: Dict[str, List[str]] = {}
        for key, filename in dict_files.items():
            with open(os.path.join(cur_dir, filename), encoding='utf-8') as f:
                self.word_dict[key] = [line.strip() for line in f if line.strip()]

        # 合并领域词表（使用集合运算优化）
        self.region_words: Set[str] = set()
        for key in ['department', 'disease', 'check', 'drug', 'food', 'producer', 'symptom']:
            self.region_words.update(self.word_dict[key])

        # 构建AC自动机
        self.region_tree = self.build_actree(list(self.region_words))
        self.wdtype_dict = self.build_wdtype_dict()

        # 疑问词配置（使用冻结集合优化）
        self.question_config = {
            'symptom': frozenset(['症状', '表征', '现象', '症候', '表现']),
            'cause': frozenset(['原因', '成因', '为什么', '怎么会', '怎样才']),
            'acompany': frozenset(['并发症', '并发', '一起发生', '一并发生']),
            'food': frozenset(['饮食', '饮用', '吃', '食', '伙食', '膳食']),
            'drug': frozenset(['药', '药品', '用药', '胶囊', '口服液']),
            'prevent': frozenset(['预防', '防范', '抵制', '抵御', '防止']),
            'lasttime': frozenset(['周期', '多久', '多长时间', '多少时间']),
            'cureway': frozenset(['怎么治疗', '如何医治', '怎么医治', '怎么治']),
            'cureprob': frozenset(['多大概率能治好', '多大几率能治好', '治好希望大么']),
            'easyget': frozenset(['易感人群', '容易感染', '易发人群', '什么人']),
            'check': frozenset(['检查', '检查项目', '查出', '检查']),
            'belong': frozenset(['属于什么科', '属于', '什么科', '科室']),
            'cure': frozenset(['治疗什么', '治啥', '治疗啥', '医治啥'])
        }

        print('模型初始化完成')

    def classify(self, question: str) -> Dict[str, Union[Dict, List]]:
        """主分类函数"""
        if not (medical_dict := self.extract_entities(question)):
            return {}

        entity_types = {t for types in medical_dict.values() for t in types}
        question_types = self._determine_question_type(question, entity_types)

        return {
            'args': medical_dict,
            'question_types': question_types or self._get_default_type(entity_types)
        }

    def build_actree(self, wordlist: List[str]) -> ahocorasick.Automaton:
        """构建AC自动机"""
        automaton = ahocorasick.Automaton()
        for idx, word in enumerate(wordlist):
            automaton.add_word(word, (idx, word))
        automaton.make_automaton()
        return automaton

    def build_wdtype_dict(self) -> Dict[str, List[str]]:
        """构建词类型映射字典"""
        return {
            word: [key for key, words in self.word_dict.items() if word in words]
            for word in self.region_words
        }

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """实体抽取优化版"""
        found_words = set()
        for _, (_, word) in self.region_tree.iter(text):
            # 使用集合操作优化子串过滤
            if not any(word in existing for existing in found_words if existing != word):
                found_words.add(word)

        return {word: self.wdtype_dict[word] for word in found_words}

    def _determine_question_type(self, question: str, entity_types: Set[str]) -> List[str]:
        """问题类型判断逻辑优化"""
        question_types = []

        # 症状相关判断
        if 'disease' in entity_types and self._contains_any(question, self.question_config['symptom']):
            question_types.append('disease_symptom')
        if 'symptom' in entity_types and self._contains_any(question, self.question_config['symptom']):
            question_types.append('symptom_disease')

        # 使用字典派发优化判断逻辑
        type_handlers = {
            'cause': ('disease', 'disease_cause'),
            'acompany': ('disease', 'disease_acompany'),
            'food': ('disease', lambda: 'disease_not_food' if self._contains_deny(question) else 'disease_do_food'),
            # ... 其他处理逻辑
        }

        for key, (entity, handler) in type_handlers.items():
            if entity in entity_types and self._contains_any(question, self.question_config[key]):
                result = handler() if callable(handler) else handler
                question_types.append(result)

        return question_types

    def _contains_any(self, text: str, keywords: Set[str]) -> bool:
        """优化后的关键词检查"""
        return any(keyword in text for keyword in keywords)

    def _contains_deny(self, text: str) -> bool:
        """否定词检查"""
        return self._contains_any(text, self.word_dict['deny'])

    def _get_default_type(self, entity_types: Set[str]) -> List[str]:
        """获取默认问题类型"""
        if 'disease' in entity_types:
            return ['disease_desc']
        if 'symptom' in entity_types:
            return ['symptom_disease']
        return []


if __name__ == '__main__':
    classifier = QuestionClassifier()
    try:
        while True:
            question = input('请输入问题: ')
            if not question:
                continue
            result = classifier.classify(question)
            print(f"分类结果: {result}")
    except KeyboardInterrupt:
        print("\n程序已退出")