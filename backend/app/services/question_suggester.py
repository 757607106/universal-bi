"""
问题推荐服务 - 输入联想和猜你想问功能

提供两种核心能力：
1. 输入联想：基于用户输入的关键词，AI生成相关问题
2. 猜你想问：基于查询结果或数据集特征，推荐后续问题
"""
import json
import re
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.logger import get_logger
from app.core.redis import get_redis_client
from app.models.metadata import Dataset, ChatMessage
from app.services.vanna import VannaInstanceManager
from app.services.db_inspector import DBInspector

logger = get_logger(__name__)


class QuestionSuggester:
    """问题推荐服务类"""
    
    # 缓存过期时间（秒）
    INPUT_SUGGESTION_CACHE_TTL = 3600  # 1小时
    POPULAR_QUESTIONS_CACHE_TTL = 86400  # 24小时
    
    @staticmethod
    def get_input_suggestions(
        dataset_id: int,
        keyword: str,
        db_session: Session,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        基于用户输入的关键词，生成相关问题建议
        
        Args:
            dataset_id: 数据集ID
            keyword: 用户输入的关键词（2-20字）
            db_session: 数据库会话
            max_suggestions: 最多返回的建议数量
            
        Returns:
            List[str]: 推荐的问题列表
        """
        if not keyword or len(keyword) < 2:
            return []
            
        # 清理关键词
        keyword = keyword.strip()[:50]
        
        # 尝试从缓存获取
        cache_key = f"suggestion:input:{dataset_id}:{keyword}"
        redis_client = get_redis_client()
        
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Input suggestion cache hit for keyword: {keyword}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # 获取数据集信息
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.datasource:
            logger.warning(f"Dataset {dataset_id} not found or no datasource")
            return QuestionSuggester._get_fallback_suggestions(keyword)
        
        # 获取表结构信息
        try:
            schema_info = DBInspector.get_dataset_schema_summary(
                dataset_id=dataset_id,
                db_session=db_session
            )
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            schema_info = "数据表结构暂不可用"
        
        # 调用LLM生成问题
        suggestions = QuestionSuggester._generate_questions_by_llm(
            keyword=keyword,
            schema_info=schema_info,
            dataset_id=dataset_id,
            max_count=max_suggestions
        )
        
        # 缓存结果
        if redis_client and suggestions:
            try:
                redis_client.setex(
                    cache_key,
                    QuestionSuggester.INPUT_SUGGESTION_CACHE_TTL,
                    json.dumps(suggestions, ensure_ascii=False)
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return suggestions
    
    @staticmethod
    def _generate_questions_by_llm(
        keyword: str,
        schema_info: str,
        dataset_id: int,
        max_count: int = 5
    ) -> List[str]:
        """
        使用LLM生成问题建议
        
        Args:
            keyword: 关键词
            schema_info: 表结构信息
            dataset_id: 数据集ID
            max_count: 最多生成数量
            
        Returns:
            List[str]: 生成的问题列表
        """
        system_prompt = """你是一个数据分析问题生成助手。
基于用户输入的关键词和数据表结构，生成具体的数据分析问题。

要求：
1. 问题要具体、可执行、符合业务分析场景
2. 问题应该是可以用SQL查询回答的
3. 结合表结构中的字段名生成问题
4. 每个问题控制在30字以内
5. 返回纯JSON数组格式，不要任何其他文字

示例输出格式：
["统计各产品类别的销售额", "查询本月新增用户数量", "分析订单金额的分布情况"]
"""
        
        user_prompt = f"""关键词：{keyword}

数据表结构：
{schema_info}

请生成{max_count}个相关的数据分析问题（JSON数组格式）："""
        
        try:
            # 获取Vanna实例
            vn = VannaInstanceManager.get_instance(dataset_id)
            
            # 调用LLM
            response = vn.submit_prompt(
                prompt=user_prompt,
                system_message=system_prompt
            )
            
            logger.info(f"LLM response for keyword '{keyword}': {response[:200]}")
            
            # 解析响应
            questions = QuestionSuggester._parse_llm_response(response)
            
            if not questions:
                logger.warning(f"LLM returned no valid questions for keyword: {keyword}")
                return QuestionSuggester._get_fallback_suggestions(keyword)
            
            return questions[:max_count]
            
        except Exception as e:
            logger.error(f"LLM question generation failed: {e}", exc_info=True)
            return QuestionSuggester._get_fallback_suggestions(keyword)
    
    @staticmethod
    def _parse_llm_response(response: str) -> List[str]:
        """
        解析LLM返回的JSON数组
        
        Args:
            response: LLM响应文本
            
        Returns:
            List[str]: 解析出的问题列表
        """
        try:
            # 尝试直接解析JSON
            questions = json.loads(response)
            if isinstance(questions, list):
                return [q for q in questions if isinstance(q, str) and len(q) > 0]
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON数组部分
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            try:
                questions = json.loads(json_match.group(0))
                if isinstance(questions, list):
                    return [q for q in questions if isinstance(q, str) and len(q) > 0]
            except json.JSONDecodeError:
                pass
        
        # 尝试按行分割（如果LLM没有返回JSON格式）
        lines = response.strip().split('\n')
        questions = []
        for line in lines:
            # 清理行首的序号、引号、破折号等
            cleaned = re.sub(r'^[\d\.\-\*\"\'\[\]]+\s*', '', line.strip())
            cleaned = cleaned.strip('"\'')
            if cleaned and len(cleaned) > 5:
                questions.append(cleaned)
        
        return questions
    
    @staticmethod
    def _get_fallback_suggestions(keyword: str) -> List[str]:
        """
        当LLM调用失败时，返回兜底的模板问题
        
        Args:
            keyword: 关键词
            
        Returns:
            List[str]: 模板问题列表
        """
        templates = [
            f"统计{keyword}的总数",
            f"查询{keyword}的最新记录",
            f"分析{keyword}的趋势变化",
            f"按类别汇总{keyword}数据",
            f"查找{keyword}的前10名"
        ]
        return templates
    
    @staticmethod
    def get_next_questions(
        dataset_id: int,
        question: str,
        sql: str,
        chart_type: str,
        result_summary: Optional[str] = None,
        db_session: Session = None,
        max_suggestions: int = 4
    ) -> List[str]:
        """
        基于当前查询结果，推荐后续问题
        
        Args:
            dataset_id: 数据集ID
            question: 当前问题
            sql: 当前SQL
            chart_type: 图表类型
            result_summary: 结果摘要（可选）
            db_session: 数据库会话
            max_suggestions: 最多返回的建议数量
            
        Returns:
            List[str]: 推荐的后续问题列表
        """
        system_prompt = """你是一个数据分析对话助手。
基于用户刚才的问题和查询结果，推荐后续可能感兴趣的分析问题。

推荐策略：
1. 深入分析：对当前结果进行更细致的拆解
2. 横向对比：从不同维度查看相同指标
3. 时间对比：增加时间维度的分析
4. 原因探索：探究数据背后的原因

要求：
1. 每个问题要具体、可操作
2. 问题应该是当前问题的自然延伸
3. 控制在25字以内
4. 返回纯JSON数组格式

示例输出：
["按产品类别拆解销售额", "对比去年同期的数据", "查看销售额的增长趋势"]
"""
        
        user_prompt = f"""用户刚才的问题：{question}

生成的SQL：
{sql[:500]}

图表类型：{chart_type}
"""
        
        if result_summary:
            user_prompt += f"\n结果摘要：{result_summary}\n"
        
        user_prompt += f"\n请推荐{max_suggestions}个后续分析问题（JSON数组格式）："
        
        try:
            # 获取Vanna实例
            vn = VannaInstanceManager.get_instance(dataset_id)
            
            # 调用LLM
            response = vn.submit_prompt(
                prompt=user_prompt,
                system_message=system_prompt
            )
            
            logger.info(f"Next questions LLM response: {response[:200]}")
            
            # 解析响应
            questions = QuestionSuggester._parse_llm_response(response)
            
            if not questions:
                return QuestionSuggester._get_fallback_next_questions(chart_type)
            
            return questions[:max_suggestions]
            
        except Exception as e:
            logger.error(f"Next questions generation failed: {e}", exc_info=True)
            return QuestionSuggester._get_fallback_next_questions(chart_type)
    
    @staticmethod
    def _get_fallback_next_questions(chart_type: str) -> List[str]:
        """
        当LLM调用失败时，返回兜底的后续问题
        
        Args:
            chart_type: 图表类型
            
        Returns:
            List[str]: 模板问题列表
        """
        if chart_type in ['line', 'bar']:
            return [
                "查看更长时间范围的趋势",
                "对比不同类别的数据",
                "找出最高和最低的时间点",
                "计算增长率或变化率"
            ]
        elif chart_type == 'pie':
            return [
                "查看排名前10的详细数据",
                "分析最大占比的具体构成",
                "对比不同时期的占比变化",
                "查看具体数值分布"
            ]
        else:
            return [
                "换一个维度查看数据",
                "增加筛选条件细化分析",
                "查看数据的时间趋势",
                "统计数据的汇总指标"
            ]
    
    @staticmethod
    def get_popular_questions(
        dataset_id: int,
        db_session: Session,
        max_questions: int = 6
    ) -> List[str]:
        """
        获取数据集的热门问题
        
        优先级：
        1. 从历史聊天记录中统计高频问题
        2. 如果历史数据不足，使用LLM生成通用模板问题
        
        Args:
            dataset_id: 数据集ID
            db_session: 数据库会话
            max_questions: 最多返回的问题数量
            
        Returns:
            List[str]: 热门问题列表
        """
        # 尝试从缓存获取
        cache_key = f"suggestion:popular:{dataset_id}"
        redis_client = get_redis_client()
        
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Popular questions cache hit for dataset {dataset_id}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # 从数据库查询高频问题
        try:
            popular = db_session.query(
                ChatMessage.question,
                func.count(ChatMessage.id).label('count')
            ).filter(
                ChatMessage.dataset_id == dataset_id,
                ChatMessage.question.isnot(None),
                ChatMessage.sql.isnot(None)  # 只统计成功生成SQL的问题
            ).group_by(
                ChatMessage.question
            ).order_by(
                desc('count')
            ).limit(max_questions).all()
            
            if popular and len(popular) >= 3:
                questions = [q.question for q in popular]
                
                # 缓存结果
                if redis_client:
                    try:
                        redis_client.setex(
                            cache_key,
                            QuestionSuggester.POPULAR_QUESTIONS_CACHE_TTL,
                            json.dumps(questions, ensure_ascii=False)
                        )
                    except Exception as e:
                        logger.warning(f"Redis cache write failed: {e}")
                
                return questions
        except Exception as e:
            logger.error(f"Failed to query popular questions: {e}")
        
        # 历史数据不足，生成通用模板问题
        questions = QuestionSuggester._generate_template_questions(
            dataset_id=dataset_id,
            db_session=db_session,
            max_count=max_questions
        )
        
        # 缓存结果（较短过期时间）
        if redis_client and questions:
            try:
                redis_client.setex(
                    cache_key,
                    3600,  # 1小时后重试
                    json.dumps(questions, ensure_ascii=False)
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return questions
    
    @staticmethod
    def _generate_template_questions(
        dataset_id: int,
        db_session: Session,
        max_count: int = 6
    ) -> List[str]:
        """
        基于数据集表结构，生成通用模板问题
        
        Args:
            dataset_id: 数据集ID
            db_session: 数据库会话
            max_count: 最多生成数量
            
        Returns:
            List[str]: 生成的问题列表
        """
        # 获取数据集信息
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.datasource:
            return [
                "统计总记录数",
                "查询最新的10条数据",
                "分析数据分布情况"
            ]
        
        # 获取表结构信息
        try:
            schema_info = DBInspector.get_dataset_schema_summary(
                dataset_id=dataset_id,
                db_session=db_session
            )
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            schema_info = "数据表结构暂不可用"
        
        # 使用LLM生成模板问题
        system_prompt = """你是一个数据分析助手。
基于数据表结构，生成通用的数据分析问题模板。

要求：
1. 问题要涵盖不同的分析场景（统计、排序、趋势、对比）
2. 问题要具体、易懂、可执行
3. 充分利用表中的字段名
4. 控制在30字以内
5. 返回纯JSON数组格式

示例输出：
["统计各类别的销售总额", "查询本月订单量前10名", "分析用户消费金额分布"]
"""
        
        user_prompt = f"""数据表结构：
{schema_info}

请生成{max_count}个通用的分析问题（JSON数组格式）："""
        
        try:
            vn = VannaInstanceManager.get_instance(dataset_id)
            response = vn.submit_prompt(
                prompt=user_prompt,
                system_message=system_prompt
            )
            
            questions = QuestionSuggester._parse_llm_response(response)
            
            if questions and len(questions) >= 3:
                return questions[:max_count]
        except Exception as e:
            logger.error(f"Template questions generation failed: {e}")
        
        # 兜底问题
        return [
            "统计数据总量",
            "查询最新的记录",
            "分析数据分布情况",
            "查找排名前10的数据",
            "按类别汇总统计",
            "查看数据的时间趋势"
        ]
