import time
import logging
import functools
import threading
import statistics
from typing import Dict, List, Callable, Any
from django.conf import settings

logger = logging.getLogger(__name__)

# 存储性能数据的字典
# 结构: {"function_name": {"times": [执行时间列表], "calls": 调用次数}}
performance_data: Dict[str, Dict[str, Any]] = {}
performance_lock = threading.Lock()

def time_function(func: Callable) -> Callable:
    """
    装饰器：测量函数的执行时间并记录
    
    Args:
        func: 要测量的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # 记录执行时间
        with performance_lock:
            if func.__name__ not in performance_data:
                performance_data[func.__name__] = {"times": [], "calls": 0}
            
            performance_data[func.__name__]["times"].append(elapsed_time)
            performance_data[func.__name__]["calls"] += 1
        
        # 根据设置决定是否记录日志
        should_log = getattr(settings, 'LOG_PERFORMANCE', False)
        if should_log or elapsed_time > 1.0:  # 执行时间超过1秒强制记录
            logger.info(f"性能 - {func.__module__}.{func.__name__} 执行时间: {elapsed_time:.4f}秒")
            
        return result
    return wrapper

def get_performance_stats() -> Dict[str, Dict[str, Any]]:
    """
    获取性能统计数据
    
    Returns:
        包含每个函数执行统计信息的字典
    """
    result = {}
    
    with performance_lock:
        for func_name, data in performance_data.items():
            times = data["times"]
            calls = data["calls"]
            
            if not times:
                continue
                
            stats = {
                "calls": calls,
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_time": sum(times)
            }
            
            # 如果调用次数足够计算标准差
            if len(times) > 1:
                stats["std_dev"] = statistics.stdev(times)
            
            result[func_name] = stats
    
    return result

def reset_performance_stats() -> None:
    """重置性能统计数据"""
    with performance_lock:
        performance_data.clear()
    logger.info("性能统计数据已重置")

def log_performance_summary() -> None:
    """记录性能统计摘要到日志"""
    stats = get_performance_stats()
    if not stats:
        logger.info("没有可用的性能统计数据")
        return
        
    logger.info("===== 性能统计摘要 =====")
    for func_name, data in sorted(
        stats.items(), 
        key=lambda x: x[1]["total_time"], 
        reverse=True
    ):
        logger.info(
            f"{func_name}: "
            f"调用={data['calls']}, "
            f"平均={data['avg_time']:.4f}秒, "
            f"最长={data['max_time']:.4f}秒, "
            f"总计={data['total_time']:.4f}秒"
        )
    logger.info("=========================") 