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
import json
import csv
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
        
    def process_json_file(self, file_path):
        """
        处理JSON格式的文件，更新知识图谱
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            dict: 更新结果统计
        """
        try:
            # 确保neo4j_client已初始化
            if not self.neo4j_client:
                self.neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
                
            start_time = datetime.now()
            print(f"[{start_time}] 开始处理JSON文件: {file_path}")
            
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 统计添加的节点和关系数量
            nodes_added = 0
            relations_added = 0
            
            # 处理数据，更新知识图谱
            # 假设JSON文件包含一个疾病列表，每个疾病包含症状、药物等信息
            for item in data:
                # 提取实体名称
                if 'name' not in item:
                    continue
                    
                entity_name = item['name']
                entity_type = item.get('type', 'Disease')  # 默认为疾病类型
                
                # 提取实体属性
                properties = {k: v for k, v in item.items() if k not in ['name', 'type', 'relations']}
                
                # 创建节点
                self._create_entity(entity_type, entity_name, properties)
                nodes_added += 1
                
                # 处理关系
                if 'relations' in item and isinstance(item['relations'], list):
                    for relation in item['relations']:
                        if 'target' in relation and 'type' in relation:
                            target_name = relation['target']
                            relation_type = relation['type']
                            target_type = relation.get('target_type', 'Entity')
                            
                            # 创建目标节点
                            target_props = {}
                            if 'target_properties' in relation and isinstance(relation['target_properties'], dict):
                                target_props = relation['target_properties']
                                
                            self._create_entity(target_type, target_name, target_props)
                            nodes_added += 1
                            
                            # 创建关系
                            self._create_relation(entity_type, entity_name, target_type, target_name, relation_type)
                            relations_added += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{end_time}] JSON文件处理完成，耗时: {duration}秒")
            print(f"添加节点: {nodes_added}, 添加关系: {relations_added}")
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added,
                'duration': duration
            }
            
        except Exception as e:
            print(f"处理JSON文件失败: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'nodes_added': 0,
                'relations_added': 0
            }
    
    def process_csv_file(self, file_path):
        """
        处理CSV格式的文件，更新知识图谱
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            dict: 更新结果统计
        """
        try:
            # 确保neo4j_client已初始化
            if not self.neo4j_client:
                self.neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
                
            start_time = datetime.now()
            print(f"[{start_time}] 开始处理CSV文件: {file_path}")
            
            # 使用pandas读取CSV文件
            df = pd.read_csv(file_path)
            
            # 统计添加的节点和关系数量
            nodes_added = 0
            relations_added = 0
            
            # 假设CSV的前两列是实体和关系，后面的列是属性
            if len(df.columns) < 3:
                raise ValueError("CSV文件格式不正确，至少需要3列: 源实体, 关系类型, 目标实体")
                
            # 提取列名
            source_col = df.columns[0]
            relation_col = df.columns[1]
            target_col = df.columns[2]
            
            # 遍历每一行，创建节点和关系
            for _, row in df.iterrows():
                source = row[source_col]
                relation = row[relation_col]
                target = row[target_col]
                
                if pd.isna(source) or pd.isna(target) or pd.isna(relation):
                    continue
                    
                # 创建源节点和目标节点（如果不存在）
                source_type = "Entity"
                if "source_type" in df.columns and not pd.isna(row["source_type"]):
                    source_type = row["source_type"]
                    
                target_type = "Entity"
                if "target_type" in df.columns and not pd.isna(row["target_type"]):
                    target_type = row["target_type"]
                    
                # 提取源节点属性
                source_props = {}
                for col in df.columns:
                    if col.startswith("source_prop_") and not pd.isna(row[col]):
                        prop_name = col.replace("source_prop_", "")
                        source_props[prop_name] = row[col]
                        
                # 提取目标节点属性
                target_props = {}
                for col in df.columns:
                    if col.startswith("target_prop_") and not pd.isna(row[col]):
                        prop_name = col.replace("target_prop_", "")
                        target_props[prop_name] = row[col]
                
                # 创建节点
                self._create_entity(source_type, source, source_props)
                nodes_added += 1
                
                self._create_entity(target_type, target, target_props)
                nodes_added += 1
                
                # 创建关系
                self._create_relation(source_type, source, target_type, target, relation)
                relations_added += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{end_time}] CSV文件处理完成，耗时: {duration}秒")
            print(f"添加节点: {nodes_added}, 添加关系: {relations_added}")
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added,
                'duration': duration
            }
            
        except Exception as e:
            print(f"处理CSV文件失败: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'nodes_added': 0,
                'relations_added': 0
            }
    
    def process_txt_file(self, file_path):
        """
        处理TXT格式的文件，更新知识图谱
        
        Args:
            file_path: TXT文件路径
            
        Returns:
            dict: 更新结果统计
        """
        try:
            # 确保neo4j_client已初始化
            if not self.neo4j_client:
                self.neo4j_client = Neo4jClient(**settings.NEO4J_CONFIG)
                
            start_time = datetime.now()
            print(f"[{start_time}] 开始处理TXT文件: {file_path}")
            
            # 统计添加的节点和关系数量
            nodes_added = 0
            relations_added = 0
            
            # 读取TXT文件，假设每行是一个三元组：源实体,关系类型,目标实体
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    parts = line.split(',')
                    if len(parts) < 3:
                        print(f"警告: 忽略无效行: {line}")
                        continue
                        
                    source = parts[0].strip()
                    relation = parts[1].strip()
                    target = parts[2].strip()
                    
                    # 提取实体类型（如果有）
                    source_type = "Entity"
                    target_type = "Entity"
                    
                    if len(parts) > 3 and parts[3].strip():
                        source_type = parts[3].strip()
                    if len(parts) > 4 and parts[4].strip():
                        target_type = parts[4].strip()
                    
                    # 创建节点
                    self._create_entity(source_type, source, {})
                    nodes_added += 1
                    
                    self._create_entity(target_type, target, {})
                    nodes_added += 1
                    
                    # 创建关系
                    self._create_relation(source_type, source, target_type, target, relation)
                    relations_added += 1
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{end_time}] TXT文件处理完成，耗时: {duration}秒")
            print(f"添加节点: {nodes_added}, 添加关系: {relations_added}")
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added,
                'duration': duration
            }
            
        except Exception as e:
            print(f"处理TXT文件失败: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'nodes_added': 0,
                'relations_added': 0
            }
    
    def _create_entity(self, entity_type, entity_name, properties):
        """
        创建实体节点
        
        Args:
            entity_type: 实体类型
            entity_name: 实体名称
            properties: 实体属性
        """
        # 确保name属性存在
        props = {'name': entity_name}
        props.update(properties)
        
        # 创建Cypher查询
        query = f"""
        MERGE (n:{entity_type} {{name: $name}})
        SET n += $properties
        RETURN n
        """
        
        # 执行查询
        self.neo4j_client.execute_query(query, {
            'name': entity_name,
            'properties': props
        })
    
    def _create_relation(self, source_type, source_name, target_type, target_name, relation_type):
        """
        创建实体关系
        
        Args:
            source_type: 源实体类型
            source_name: 源实体名称
            target_type: 目标实体类型
            target_name: 目标实体名称
            relation_type: 关系类型
        """
        # 创建Cypher查询
        query = f"""
        MATCH (a:{source_type} {{name: $source_name}}), (b:{target_type} {{name: $target_name}})
        MERGE (a)-[r:{relation_type}]->(b)
        RETURN a, r, b
        """
        
        # 执行查询
        self.neo4j_client.execute_query(query, {
            'source_name': source_name,
            'target_name': target_name
        }) 