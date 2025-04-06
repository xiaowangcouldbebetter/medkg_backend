# nlp_module/bert_classifier.py
import torch
from transformers import BertTokenizer, BertForSequenceClassification
import logging
import os
import numpy as np
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

class BertQuestionClassifier:
    """基于BERT的问题分类器"""
    
    def __init__(self, model_path=None):
        try:
            # 设置默认模型路径
            if model_path is None:
                model_path = os.path.join(os.path.dirname(__file__), 'models', 'bert-base-chinese-medical')
            
            # 检查模型是否存在
            if not os.path.exists(model_path):
                logger.warning(f"BERT模型路径不存在: {model_path}，将使用规则分类器")
                self.model = None
                self.tokenizer = None
                return
            
            # 加载分词器和模型
            self.tokenizer = BertTokenizer.from_pretrained(model_path)
            self.model = BertForSequenceClassification.from_pretrained(model_path)
            
            # 使用GPU加速（如果可用）
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(self.device)
            self.model.eval()
            
            # 问题类型映射
            self.id2label = {
                0: 'disease_symptom',
                1: 'symptom_disease', 
                2: 'disease_cause',
                3: 'disease_acompany',
                4: 'disease_not_food',
                5: 'disease_do_food',
                6: 'disease_drug',
                7: 'disease_check',
                8: 'disease_prevent',
                9: 'disease_lasttime',
                10: 'disease_cureway',
                11: 'disease_cureprob',
                12: 'disease_easyget',
                13: 'disease_desc'
            }
            
            logger.info("BERT问题分类器初始化成功")
        except Exception as e:
            logger.error(f"BERT模型加载失败: {str(e)}")
            self.model = None
            self.tokenizer = None
    
    def classify(self, question: str) -> List[str]:
        """使用BERT模型对问题进行分类"""
        if self.model is None or self.tokenizer is None:
            return []
        
        try:
            # 对问题进行编码
            inputs = self.tokenizer(
                question,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 模型推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                
            # 获取预测结果
            probabilities = torch.nn.functional.softmax(logits, dim=1)
            confidence, predictions = torch.max(probabilities, dim=1)
            
            # 转换为问题类型
            question_type = self.id2label[predictions.item()]
            confidence_value = confidence.item()
            
            logger.debug(f"BERT分类结果: {question_type} (置信度: {confidence_value:.4f})")
            
            # 只有当置信度超过阈值时才返回预测类型
            if confidence_value >= 0.7:
                return [question_type]
            else:
                return []
                
        except Exception as e:
            logger.error(f"BERT分类过程出错: {str(e)}")
            return []

# 示例用法
if __name__ == "__main__":
    # 注意: 这里需要事先准备好模型文件
    classifier = BertQuestionClassifier()
    
    test_questions = [
        "高血压有哪些症状？",
        "感冒应该吃什么药？",
        "糖尿病患者应该忌口什么食物？"
    ]
    
    for question in test_questions:
        result = classifier.classify(question)
        print(f"问题: {question}")
        print(f"分类结果: {result}")
        print() 