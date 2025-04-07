"""
知识图谱更新模块
负责从网络爬取医疗数据，清洗数据，更新知识图谱
"""
import os
import time
import logging
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from .neo4j_client import Neo4jClient
from accounts.views import log_system_event
from django.conf import settings
import traceback
from datetime import datetime

class KnowledgeGraphUpdater:
    """知识图谱更新器，用于爬取医疗数据并更新到知识图谱"""
    
    def __init__(self):
        # 初始化时不创建Neo4j客户端，会在update_knowledge_graph方法中使用传入的客户端或创建新的
        self.neo4j_client = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.logger = logging.getLogger(__name__)
    
    def crawl_medical_data(self, source_url):
        """
        爬取医疗数据
        :param source_url: 数据源URL
        :return: 爬取到的原始数据
        """
        try:
            log_system_event("INFO", "KG_Updater", f"开始从{source_url}爬取医疗数据")
            
            response = requests.get(source_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 记录成功日志
            log_system_event("INFO", "KG_Updater", f"成功爬取数据，状态码: {response.status_code}, 数据大小: {len(response.text)}字节")
            
            return response.text
        except Exception as e:
            error_msg = f"爬取医疗数据失败: {str(e)}"
            self.logger.error(error_msg)
            log_system_event("ERROR", "KG_Updater", error_msg, trace=str(e))
            return None
    
    def clean_data(self, raw_data, data_type="html"):
        """
        清洗数据
        :param raw_data: 原始数据
        :param data_type: 数据类型 (html, json, xml等)
        :return: 清洗后的结构化数据
        """
        try:
            log_system_event("INFO", "KG_Updater", f"开始清洗{data_type}类型数据")
            
            if data_type == "html":
                # 使用BeautifulSoup解析HTML
                soup = BeautifulSoup(raw_data, 'html.parser')
                
                # 示例：提取所有疾病名称和描述
                # 实际实现需要根据目标网站的HTML结构调整
                diseases = []
                
                disease_elements = soup.find_all('div', class_='disease-item')
                for element in disease_elements:
                    name = element.find('h3').text.strip()
                    description = element.find('p', class_='description').text.strip()
                    symptoms = [li.text.strip() for li in element.find_all('li', class_='symptom')]
                    
                    diseases.append({
                        'name': name,
                        'description': description,
                        'symptoms': symptoms
                    })
                
                log_system_event("INFO", "KG_Updater", f"数据清洗完成，提取了{len(diseases)}个疾病信息")
                return diseases
            
            elif data_type == "json":
                # 处理JSON数据
                import json
                data = json.loads(raw_data)
                # TODO: 根据具体数据结构进行清洗
                return data
            
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")
                
        except Exception as e:
            error_msg = f"数据清洗失败: {str(e)}"
            self.logger.error(error_msg)
            log_system_event("ERROR", "KG_Updater", error_msg, trace=str(e))
            return None
    
    def update_knowledge_graph(self, search_term):
        """
        更新知识图谱，根据搜索词爬取医疗数据并添加到知识图谱
        
        Args:
            search_term: 搜索关键词
            
        Returns:
            dict: 更新结果统计
        """
        # 如果没有neo4j_client，则创建一个
        if not self.neo4j_client:
            self.neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
            
        start_time = datetime.now()
        print(f"[{start_time}] 开始更新知识图谱，搜索关键词: {search_term}")
        
        # 爬取医学百科数据
        try:
            search_url = f"https://www.baike.com/query?word={search_term}"
            baike_data = self._scrape_baike(search_url, search_term)
            
            # 处理数据并更新到知识图谱
            nodes_added = 0
            relations_added = 0
            
            if baike_data:
                # 添加疾病节点
                self._add_disease_node(search_term, baike_data)
                nodes_added += 1
                
                # 添加症状节点和关系
                if 'symptoms' in baike_data and baike_data['symptoms']:
                    for symptom in baike_data['symptoms']:
                        self._add_symptom_node(symptom)
                        self._add_relation(search_term, 'HAS_SYMPTOM', symptom)
                        nodes_added += 1
                        relations_added += 1
                
                # 添加治疗方法节点和关系
                if 'treatments' in baike_data and baike_data['treatments']:
                    for treatment in baike_data['treatments']:
                        self._add_treatment_node(treatment)
                        self._add_relation(search_term, 'HAS_TREATMENT', treatment)
                        nodes_added += 1
                        relations_added += 1
                
                # 添加药物节点和关系
                if 'medications' in baike_data and baike_data['medications']:
                    for medication in baike_data['medications']:
                        self._add_medication_node(medication)
                        self._add_relation(search_term, 'TREATS_WITH', medication)
                        nodes_added += 1
                        relations_added += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{end_time}] 知识图谱更新完成，耗时: {duration}秒")
            print(f"添加节点: {nodes_added}, 添加关系: {relations_added}")
            
            return {
                'success': True,
                'search_term': search_term,
                'nodes_added': nodes_added,
                'relations_added': relations_added,
                'duration': duration
            }
            
        except Exception as e:
            print(f"更新知识图谱失败: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'nodes_added': 0,
                'relations_added': 0
            }
    
    def run_update(self, source_url, data_type="html"):
        """
        运行完整的更新流程
        :param source_url: 数据源URL
        :param data_type: 数据类型
        :return: 更新结果
        """
        # 记录开始时间
        start_time = time.time()
        log_system_event("INFO", "KG_Updater", f"开始知识图谱更新流程，数据源: {source_url}")
        
        # 爬取数据
        raw_data = self.crawl_medical_data(source_url)
        if not raw_data:
            return {"success": False, "message": "爬取数据失败"}
        
        # 清洗数据
        cleaned_data = self.clean_data(raw_data, data_type)
        if not cleaned_data:
            return {"success": False, "message": "数据清洗失败"}
        
        # 更新知识图谱
        result = self.update_knowledge_graph(cleaned_data)
        
        # 记录耗时
        elapsed_time = time.time() - start_time
        log_system_event(
            "INFO" if result["success"] else "ERROR",
            "KG_Updater",
            f"知识图谱更新流程完成，耗时: {elapsed_time:.2f}秒，结果: {result['message']}"
        )
        
        return result 