import os
from transformers import AutoTokenizer, BertForTokenClassification
import torch
import torch.optim as optim
import torch.nn as nn
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

from utils.performance_monitor import get_performance_stats, reset_performance_stats, log_performance_summary
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

SKIP_TRAINING = True  # 设置为True跳过训练

def read_text_files(base_path):
    data_dict = {}
    file_names = ["check.txt", "deny.txt", "department.txt", "disease.txt", "drug.txt", "food.txt", "producer.txt", "symptom.txt"]
    for file_name in file_names:
        file_path = os.path.join(base_path, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data_dict[file_name.split('.')[0]] = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            print(f"文件未找到: {file_path}")
            return None
        except Exception as e:
            print(f"读取文件时发生错误: {file_path}, 错误: {e}")
            return None
    return data_dict

def preprocess_data(data_dict, tokenizer):
    all_inputs = []
    all_labels = []
    label_mapping = {
        "check": 0, "deny": 1, "department": 2, "disease": 3,
        "drug": 4, "food": 5, "producer": 6, "symptom": 7
    }

    for entity_type, entities in data_dict.items():
        for entity in entities:
            inputs = tokenizer(entity, return_tensors='pt', padding=True, truncation=True, max_length=512)
            label = label_mapping[entity_type]
            all_inputs.append(inputs)
            all_labels.append(label)

    # 合并所有输入张量
    try:
        all_inputs = {k: torch.cat([d[k] for d in all_inputs], dim=0) for k in all_inputs[0].keys()}
    except Exception as e:
        print(f"合并输入张量时发生错误: {e}")
        for i, inputs in enumerate(all_inputs):
            print(f"张量 {i} 形状: {inputs['input_ids'].shape}")
        return None, None

    all_labels = torch.tensor(all_labels)
    return all_inputs, all_labels

if not SKIP_TRAINING:
    # 设置基本路径
    base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nlp_module', 'dict')

    # 读取文本文件
    data_dict = read_text_files(base_path)
    if data_dict is None:
        print("数据字典读取失败，无法继续执行")
        # 不要exit，避免影响Django启动

    # 打印 data_dict 以验证内容
    print("数据字典内容:")
    for key, value in data_dict.items():
        print(f"{key}: {value[:5]}")  # 打印每个文件的前5行

    # 加载预训练的tokenizer
    try:
        tokenizer_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nlp_module', 'models', 'bert-base-chinese-medical')
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
    except Exception as e:
        print(f"加载tokenizer时发生错误: {e}")
        exit()

    # 预处理数据
    all_inputs, all_labels = preprocess_data(data_dict, tokenizer)
    if all_inputs is None or all_labels is None:
        print("数据预处理失败，无法继续执行")
        exit()

    # 打印 all_inputs 和 all_labels 以验证形状
    print("合并后的输入张量形状:")
    for key, value in all_inputs.items():
        print(f"{key}: {value.shape}")

    print("标签张量形状:")
    print(all_labels.shape)

    # 加载预训练的模型
    try:
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nlp_module', 'models', 'bert-base-chinese-medical')
        model = BertForTokenClassification.from_pretrained(model_path)
    except Exception as e:
        print(f"加载模型时发生错误: {e}")
        exit()

    # 定义优化器和损失函数
    optimizer = optim.AdamW(model.parameters(), lr=5e-5)
    criterion = nn.CrossEntropyLoss()

    # 设置设备（CPU 或 GPU）
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    for k, v in all_inputs.items():
        all_inputs[k] = v.to(device)
    all_labels = all_labels.to(device)

    # 训练循环
    num_epochs = 3
    for epoch in range(num_epochs):
        model.train()
        optimizer.zero_grad()
        try:
            outputs = model(**all_inputs)
            loss = criterion(outputs.logits.view(-1, model.config.num_labels), all_labels)
            loss.backward()
            optimizer.step()
            print(f'Epoch {epoch + 1}, Loss: {loss.item()}')
        except Exception as e:
            print(f"训练过程中发生错误: {e}")
            break

    # 保存训练好的模型
    model.save_pretrained('trained_model')

@staff_member_required
@require_http_methods(["GET"])
def performance_stats(request):
    """
    获取性能统计信息
    仅管理员可访问
    """
    try:
        # 获取性能数据
        stats = get_performance_stats()
        
        # 获取缓存统计
        cache_stats = CacheManager.get_cache_stats()
        
        # 日志摘要
        log_performance_summary()
        
        return JsonResponse({
            'success': True,
            'data': {
                'performance': stats,
                'cache': cache_stats,
                'system_info': {
                    'debug': settings.DEBUG,
                    'cache_enabled': getattr(settings, 'CACHE_ENABLED', True),
                    'bert_enabled': getattr(settings, 'USE_BERT_CLASSIFIER', False)
                }
            }
        })
    except Exception as e:
        logger.exception(f"获取性能统计时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取性能统计失败: {str(e)}'
        }, status=500)

@staff_member_required
@require_http_methods(["POST"])
def reset_stats(request):
    """
    重置性能统计数据
    仅管理员可访问
    """
    try:
        reset_performance_stats()
        
        return JsonResponse({
            'success': True,
            'message': '性能统计数据已重置'
        })
    except Exception as e:
        logger.exception(f"重置性能统计时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'重置性能统计失败: {str(e)}'
        }, status=500)

@staff_member_required
@require_http_methods(["POST"])
def clear_cache(request):
    """
    清空缓存
    仅管理员可访问
    """
    try:
        # 获取请求体
        data = json.loads(request.body.decode('utf-8'))
        prefix = data.get('prefix')
        
        # 清除缓存
        result = CacheManager.invalidate_cache(prefix)
        
        return JsonResponse({
            'success': result,
            'message': '缓存已清空' if result else '缓存清空失败'
        })
    except Exception as e:
        logger.exception(f"清空缓存时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'清空缓存失败: {str(e)}'
        }, status=500)
