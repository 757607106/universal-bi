"""
查询重写服务 - 支持多轮对话上下文理解
"""
from typing import List, Dict, Optional
from openai import OpenAI as OpenAIClient
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class QueryRewriter:
    """查询重写器 - 将省略主语的追问补全为完整查询"""
    
    @staticmethod
    def rewrite_query(
        current_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        基于对话历史重写当前查询
        
        Args:
            current_query: 当前用户问题
            conversation_history: 对话历史 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            
        Returns:
            str: 重写后的完整查询
        """
        # 如果没有历史或历史很短，直接返回原查询
        if not conversation_history or len(conversation_history) < 2:
            return current_query
        
        # 如果当前查询很长（>15字），可能是独立问题，不需要重写
        if len(current_query.strip()) > 15:
            return current_query
        
        # 检查是否包含明确的追问词
        follow_up_keywords = [
            '再', '还', '另外', '此外', '然后', '接着', '继续',
            '详细', '具体', '展开', '拆分', '按', '分组', '排序',
            '前', '后', 'top', '最', '高', '低'
        ]
        
        has_follow_up = any(keyword in current_query for keyword in follow_up_keywords)
        
        # 如果没有追问词，可能是独立问题
        if not has_follow_up:
            return current_query
        
        try:
            # 调用LLM进行查询重写
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 构建上下文提示
            context_messages = []
            
            # 添加系统提示
            system_prompt = """你是一个对话理解助手，专门负责将省略主语的追问补全为完整的查询。

任务：
1. 理解对话历史中的上下文
2. 将当前的省略查询补全为完整、独立的查询
3. 保留原始意图和细节要求

输出要求：
- 只输出补全后的查询，不要添加解释
- 使用自然的中文表达
- 确保查询可以独立理解

示例：
对话历史：
用户："查询上个月的销售额"
助手："[返回了销售额数据]"

当前查询："按城市拆分"

补全后："查询上个月的销售额，按城市拆分"
"""
            context_messages.append({"role": "system", "content": system_prompt})
            
            # 添加对话历史（最近3轮）
            recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            for msg in recent_history:
                context_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            # 添加当前查询
            context_messages.append({
                "role": "user",
                "content": f"请将以下追问补全为完整的独立查询：\n{current_query}"
            })
            
            # 调用LLM
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=context_messages,
                temperature=0.3,
                max_tokens=200
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            
            # 移除可能的前缀
            prefixes = ["补全后：", "重写后：", "完整查询：", "查询："]
            for prefix in prefixes:
                if rewritten_query.startswith(prefix):
                    rewritten_query = rewritten_query[len(prefix):].strip()
            
            # 移除引号
            rewritten_query = rewritten_query.strip('"\'""''')
            
            logger.info(
                "Query rewritten successfully",
                original=current_query,
                rewritten=rewritten_query,
                history_length=len(conversation_history)
            )
            
            return rewritten_query
            
        except Exception as e:
            logger.error(
                "Query rewriting failed",
                error=str(e),
                original_query=current_query,
                exc_info=True
            )
            # 失败时返回原查询
            return current_query
    
    @staticmethod
    def should_rewrite(query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        判断是否需要重写查询
        
        Args:
            query: 当前查询
            conversation_history: 对话历史
            
        Returns:
            bool: 是否需要重写
        """
        # 没有历史，不需要重写
        if not conversation_history or len(conversation_history) < 2:
            return False
        
        # 查询太长，可能是独立问题
        if len(query.strip()) > 20:
            return False
        
        # 包含明确的实体（表名、字段名等），可能是独立问题
        entity_keywords = ['用户', '订单', '产品', '客户', '销售', '表', '数据', '总计', '汇总']
        if any(keyword in query for keyword in entity_keywords):
            # 有实体但也有追问词，需要重写
            follow_up_keywords = ['按', '拆分', '分组', '排序', '详细', '具体']
            if any(keyword in query for keyword in follow_up_keywords):
                return True
            return False
        
        # 包含追问词
        follow_up_keywords = [
            '再', '还', '另外', '此外', '然后', '接着', '继续',
            '详细', '具体', '展开', '拆分', '按', '分组', '排序',
            '前', '后', 'top', '最', '高', '低', '大', '小'
        ]
        
        return any(keyword in query for keyword in follow_up_keywords)

