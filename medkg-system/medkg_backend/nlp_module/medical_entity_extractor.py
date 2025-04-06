# nlp_module/medical_entity_extractor.py
import re
import jieba
import jieba.posseg as pseg
from typing import Dict, List, Set
import logging
import os

logger = logging.getLogger(__name__)

# 加载医学词典
def load_medical_dict(dict_dir='dict'):
    """
    加载医疗词典
    
    Args:
        dict_dir: 词典目录路径
    """
    # 获取当前文件所在目录(nlp_module)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建词典路径 - 首选当前目录下的dict
    dict_path = os.path.join(current_dir, dict_dir)
    
    if not os.path.exists(dict_path):
        logger.error(f"无法找到词典目录: {dict_path}")
        return {}
    
    medical_dict = {}
    # 遍历词典目录下的所有文件
    try:
        for file in os.listdir(dict_path):
            if file.endswith('.txt'):
                entity_type = file.split('.')[0]
                file_path = os.path.join(dict_path, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    words = [line.strip() for line in f if line.strip()]
                    medical_dict[entity_type] = set(words)
                    logger.info(f"已加载{entity_type}词典，共{len(words)}个词")
    except Exception as e:
        logger.error(f"加载医学词典失败: {str(e)}")
    
    return medical_dict

# 全局词典
MEDICAL_DICT = load_medical_dict()

# 添加词典到jieba
for entity_type, words in MEDICAL_DICT.items():
    for word in words:
        jieba.add_word(word, freq=100)

def extract_medical_entities(text: str) -> Dict[str, List[str]]:
    """提取文本中的医学实体
    
    Args:
        text: 需要提取实体的文本
    
    Returns:
        包含实体及其类型的字典，格式为 {实体: [类型]}
    """
    if not text:
        return {}
    
    # 分词
    words_pos = pseg.cut(text)
    words = [word for word, pos in words_pos]
    
    # 提取实体
    entities = {}
    for entity_type, entity_set in MEDICAL_DICT.items():
        # 查找文本中包含的实体
        found_entities = []
        for entity in entity_set:
            if entity in text:
                found_entities.append(entity)
        
        # 如果找到实体，添加到结果中
        if found_entities:
            for entity in found_entities:
                if entity not in entities:
                    entities[entity] = []
                entities[entity].append(entity_type)
    
    return entities

# 测试用主函数
if __name__ == "__main__":
    test_sentences = [
        "高血压有哪些症状？",
        "感冒应该吃什么药？",
        "糖尿病患者应该忌口什么食物？"
    ]
    
    for sentence in test_sentences:
        entities = extract_medical_entities(sentence)
        print(f"原始文本: {sentence}")
        print(f"提取实体: {entities}")
        print() 