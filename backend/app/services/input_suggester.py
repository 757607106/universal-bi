"""
输入联想服务 - 基于关键词实时推荐相关问题
"""
from typing import List, Optional
from openai import OpenAI as OpenAIClient
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.core.config import settings
from app.core.redis import redis_service
from app.core.logger import get_logger
from app.models.metadata import Dataset
from app.services.db_inspector import DBInspector

logger = get_logger(__name__)


class InputSuggester:
    """输入联想服务 - 实时推荐相关问题"""
    
    # Redis 缓存配置
    CACHE_TTL = 300  # 5 分钟缓存
    CACHE_PREFIX = "input_suggest"
    
    @classmethod
    async def suggest_questions(
        cls,
        dataset_id: int,
        partial_input: str,
        db_session: Session,
        limit: int = 5
    ) -> List[str]:
        """
        基于部分输入生成问题建议
        
        Args:
            dataset_id: 数据集 ID
            partial_input: 用户部分输入
            db_session: 数据库会话
            limit: 返回建议数量
            
        Returns:
            List[str]: 建议问题列表
        """
        # 输入验证
        partial_input = partial_input.strip()
        if not partial_input or len(partial_input) < 1:
            return []
        
        # 检查缓存
        cache_key = f"{cls.CACHE_PREFIX}:{dataset_id}:{partial_input}:{limit}"
        cached_suggestions = await redis_service.get(cache_key)
        
        if cached_suggestions:
            logger.info(
                "Input suggestions returned from cache",
                dataset_id=dataset_id,
                partial_input=partial_input,
                suggestion_count=len(cached_suggestions)
            )
            return cached_suggestions
        
        try:
            # 获取数据集信息
            stmt = select(Dataset).options(
                selectinload(Dataset.datasource)
            ).where(Dataset.id == dataset_id)
            result = db_session.execute(stmt)
            dataset = result.scalar_one_or_none()
            
            if not dataset or not dataset.datasource:
                logger.warning(
                    "Dataset or datasource not found",
                    dataset_id=dataset_id
                )
                return []
            
            # 获取 schema 信息
            schema_info = cls._get_schema_summary(dataset, db_session)
            
            # 调用 LLM 生成建议
            suggestions = await cls._generate_suggestions_with_llm(
                partial_input=partial_input,
                schema_info=schema_info,
                limit=limit
            )
            
            # 缓存结果
            await redis_service.set(cache_key, suggestions, expire=cls.CACHE_TTL)
            
            logger.info(
                "Input suggestions generated successfully",
                dataset_id=dataset_id,
                partial_input=partial_input,
                suggestion_count=len(suggestions)
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(
                "Failed to generate input suggestions",
                error=str(e),
                dataset_id=dataset_id,
                partial_input=partial_input,
                exc_info=True
            )
            # 降级：返回空列表，不影响主流程
            return []
    
    @classmethod
    def _get_schema_summary(cls, dataset: Dataset, db_session: Session) -> str:
        """
        获取数据集 schema 摘要信息
        
        Args:
            dataset: 数据集对象
            db_session: 数据库会话
            
        Returns:
            str: Schema 摘要文本
        """
        try:
            inspector = DBInspector.get_inspector(dataset.datasource)
            
            # 获取表和字段信息
            tables_info = []
            schema_config = dataset.schema_config or []
            
            for table_name in schema_config[:5]:  # 最多取 5 个表
                try:
                    columns = inspector.get_columns(table_name)
                    column_names = [col['name'] for col in columns[:10]]  # 每个表最多 10 个字段
                    tables_info.append(f"表 {table_name}: {', '.join(column_names)}")
                except Exception as e:
                    logger.warning(f"Failed to get columns for table {table_name}: {e}")
                    continue
            
            if not tables_info:
                return "数据集包含多个业务表"
            
            return "数据集包含以下表和字段：\n" + "\n".join(tables_info)
            
        except Exception as e:
            logger.warning(f"Failed to get schema summary: {e}")
            return "数据集包含多个业务表"
    
    @classmethod
    async def _generate_suggestions_with_llm(
        cls,
        partial_input: str,
        schema_info: str,
        limit: int
    ) -> List[str]:
        """
        使用 LLM 生成问题建议
        
        Args:
            partial_input: 部分输入
            schema_info: Schema 信息
            limit: 建议数量
            
        Returns:
            List[str]: 建议问题列表
        """
        try:
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 构建提示词
            system_prompt = f"""你是一个智能问题联想助手，帮助用户完善数据分析问题。

任务：
1. 基于用户的部分输入和数据集结构，生成 {limit} 个相关的完整问题建议
2. 问题应该具体、可执行，适合数据分析场景
3. 问题应该多样化，覆盖不同的分析角度（趋势、对比、排名、分布等）

输出要求：
- 每行一个问题
- 不要添加序号或其他格式
- 使用自然的中文表达
- 问题长度控制在 10-30 字之间

数据集信息：
{schema_info}

示例：
用户输入：销售
建议问题：
查询上个月的销售额
销售额 TOP10 的产品
各地区销售额对比
销售趋势分析（按月）
销售额同比增长率
"""

            user_prompt = f"用户当前输入：{partial_input}\n\n请生成 {limit} 个相关问题建议："
            
            # 调用 LLM
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # 提高多样性
                max_tokens=150,
                top_p=0.9
            )
            
            # 解析结果
            content = response.choices[0].message.content.strip()
            suggestions = []
            
            for line in content.split('\n'):
                line = line.strip()
                # 移除可能的序号
                line = line.lstrip('0123456789.、- ')
                if line and len(line) >= 3:
                    suggestions.append(line)
            
            # 限制数量
            suggestions = suggestions[:limit]
            
            # 如果没有生成足够的建议，添加默认建议
            if len(suggestions) < 2:
                default_suggestions = cls._get_default_suggestions(partial_input)
                suggestions.extend(default_suggestions[:limit - len(suggestions)])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"LLM suggestion generation failed: {e}", exc_info=True)
            # 降级：返回默认建议
            return cls._get_default_suggestions(partial_input)[:limit]
    
    @classmethod
    def _get_default_suggestions(cls, partial_input: str) -> List[str]:
        """
        获取默认建议（降级方案）
        
        Args:
            partial_input: 部分输入
            
        Returns:
            List[str]: 默认建议列表
        """
        # 基于关键词的简单匹配
        keyword_templates = {
            '销售': [
                '查询销售额总计',
                '销售额 TOP10',
                '销售趋势分析',
                '各地区销售对比',
                '销售额同比增长'
            ],
            '用户': [
                '用户总数统计',
                '新增用户趋势',
                '用户活跃度分析',
                '用户地区分布',
                '用户增长率'
            ],
            '订单': [
                '订单总量统计',
                '订单金额分析',
                '订单状态分布',
                '订单趋势分析',
                'TOP 客户订单量'
            ],
            '产品': [
                '产品销量排名',
                '产品类别分布',
                '热门产品分析',
                '产品库存统计',
                '产品销售趋势'
            ]
        }
        
        # 查找匹配的关键词
        for keyword, templates in keyword_templates.items():
            if keyword in partial_input:
                return templates
        
        # 默认通用建议
        return [
            f'查询{partial_input}相关数据',
            f'{partial_input}趋势分析',
            f'{partial_input}统计汇总',
            f'{partial_input}排名 TOP10',
            f'{partial_input}分布情况'
        ]
