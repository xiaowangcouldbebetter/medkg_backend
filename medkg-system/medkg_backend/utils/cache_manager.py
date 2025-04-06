import hashlib
import json
import logging
from django.core.cache import cache, caches
from django.conf import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器，负责医疗问答系统的缓存操作"""
    
    @staticmethod
    def get_cache_key(prefix, data):
        """
        生成缓存键
        
        Args:
            prefix: 键前缀
            data: 要哈希的数据
            
        Returns:
            生成的缓存键
        """
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data, sort_keys=True)
            
        # 使用MD5生成唯一键
        hash_obj = hashlib.md5(data_str.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    @staticmethod
    def get_cached_result(question, use_local=True):
        """
        获取缓存的问题结果
        
        Args:
            question: 用户问题
            use_local: 是否优先使用本地内存缓存
            
        Returns:
            缓存的结果或None
        """
        # 直接返回None，禁用缓存功能
        if not settings.CACHE_ENABLED:
            return None
            
        try:
            cache_key = CacheManager.get_cache_key("qa", question)
            
            # 优先检查本地内存缓存
            if use_local:
                local_cache = caches['local']
                result = local_cache.get(cache_key)
                if result:
                    logger.info(f"本地缓存命中: {cache_key}")
                    return result
            
            # 检查默认缓存
            result = cache.get(cache_key)
            if result:
                logger.info(f"缓存命中: {cache_key}")
                return result
                
            logger.info(f"缓存未命中: {cache_key}")
            return None
        except Exception as e:
            logger.warning(f"缓存操作异常: {str(e)}")
            return None
    
    @staticmethod
    def cache_result(question, result, ttl=None):
        """
        缓存问题结果
        
        Args:
            question: 用户问题
            result: 查询结果
            ttl: 缓存时间(秒)，如果为None则使用默认值
        """
        # 直接返回，不执行缓存
        if not settings.CACHE_ENABLED or not result:
            return
            
        try:
            if ttl is None:
                ttl = getattr(settings, 'CACHE_TTL', 86400)  # 默认24小时
                
            cache_key = CacheManager.get_cache_key("qa", question)
            
            # 存入主缓存
            cache.set(cache_key, result, timeout=ttl)
            
            # 同时存入本地内存缓存
            local_cache = caches['local']
            local_cache.set(cache_key, result, timeout=min(300, ttl))  # 本地最多缓存5分钟
            
            logger.debug(f"缓存结果: {cache_key}, TTL={ttl}秒")
        except Exception as e:
            logger.warning(f"缓存结果异常: {str(e)}")
    
    @staticmethod
    def invalidate_cache(prefix=None):
        """
        使缓存失效
        
        Args:
            prefix: 如果提供，则只清除包含此前缀的缓存键
        """
        if not settings.CACHE_ENABLED:
            return True
            
        try:
            if prefix:
                logger.info(f"尝试清除前缀为 {prefix} 的缓存")
            else:
                logger.info("清除所有缓存")
                
            # 清空本地缓存
            caches['local'].clear()
            
            if not prefix:
                # 如果没有指定前缀，清空全部缓存
                cache.clear()
            
            return True
        except Exception as e:
            logger.warning(f"清除缓存异常: {str(e)}")
            return False 