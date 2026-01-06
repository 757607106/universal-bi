"""
测试多轮推理和中间 SQL 处理功能

这个测试脚本验证 VannaManager 的新功能：
1. 检测和提取中间 SQL
2. 识别澄清请求
3. 多轮推理流程
"""
from app.services.vanna_manager import VannaManager


def test_extract_intermediate_sql():
    """测试中间 SQL 提取功能"""
    print("=" * 80)
    print("测试 1: 中间 SQL 提取")
    print("=" * 80)
    
    # 场景 1: 显式 intermediate_sql 标记
    response1 = """我不确定"大客户"的定义，让我先查询有哪些客户类型：
    
intermediate_sql:
SELECT DISTINCT type FROM users;

请问大客户是指哪种类型？"""
    
    result1 = VannaManager._extract_intermediate_sql(response1)
    print(f"\n场景 1 - 显式标记:")
    print(f"输入: {response1[:80]}...")
    print(f"提取结果: {result1}")
    print(f"是否成功: {'✓' if 'SELECT DISTINCT type FROM users' in result1 else '✗'}")
    
    # 场景 2: 隐式模式（不确定 + DISTINCT 查询）
    response2 = """我不太确定大客户的具体定义。让我先查询数据库中有哪些客户类型：

SELECT DISTINCT type FROM customers;

根据查询结果，请告诉我大客户是指哪种类型？"""
    
    result2 = VannaManager._extract_intermediate_sql(response2)
    print(f"\n场景 2 - 隐式模式:")
    print(f"输入: {response2[:80]}...")
    print(f"提取结果: {result2}")
    print(f"是否成功: {'✓' if 'SELECT DISTINCT type FROM customers' in result2 else '✗'}")
    
    # 场景 3: 正常 SQL（无中间查询）
    response3 = """SELECT name, total_amount 
FROM customers 
WHERE total_amount > 10000
ORDER BY total_amount DESC;"""
    
    result3 = VannaManager._extract_intermediate_sql(response3)
    print(f"\n场景 3 - 正常 SQL:")
    print(f"输入: {response3[:80]}...")
    print(f"提取结果: {result3}")
    print(f"是否成功: {'✓' if result3 == '' else '✗'}")
    

def test_is_clarification_request():
    """测试澄清请求识别功能"""
    print("\n" + "=" * 80)
    print("测试 2: 澄清请求识别")
    print("=" * 80)
    
    # 场景 1: 明确的澄清请求（无 SQL）
    response1 = "我无法确定'大客户'的具体含义，请问您是指消费额超过1万元的客户吗？"
    result1 = VannaManager._is_clarification_request(response1)
    print(f"\n场景 1 - 无 SQL 的澄清:")
    print(f"输入: {response1}")
    print(f"识别结果: {result1}")
    print(f"是否成功: {'✓' if result1 else '✗'}")
    
    # 场景 2: 带 SQL 的澄清请求
    response2 = """我不确定大客户的定义，是指消费额还是消费次数？
SELECT type FROM customers;
请明确一下条件。"""
    result2 = VannaManager._is_clarification_request(response2)
    print(f"\n场景 2 - 带 SQL 的澄清:")
    print(f"输入: {response2[:80]}...")
    print(f"识别结果: {result2}")
    print(f"是否成功: {'✓' if result2 else '✗'}")
    
    # 场景 3: 正常 SQL 查询（非澄清）
    response3 = """SELECT COUNT(*) as vip_count 
FROM customers 
WHERE type = 'VIP';"""
    result3 = VannaManager._is_clarification_request(response3)
    print(f"\n场景 3 - 正常查询:")
    print(f"输入: {response3}")
    print(f"识别结果: {result3}")
    print(f"是否成功: {'✓' if not result3 else '✗'}")
    
    # 场景 4: 数据未找到
    response4 = "没有找到关于'大客户'的定义，数据库中也没有相关字段。"
    result4 = VannaManager._is_clarification_request(response4)
    print(f"\n场景 4 - 数据未找到:")
    print(f"输入: {response4}")
    print(f"识别结果: {result4}")
    print(f"是否成功: {'✓' if result4 else '✗'}")


def test_clean_sql():
    """测试 SQL 清洗功能"""
    print("\n" + "=" * 80)
    print("测试 3: SQL 清洗")
    print("=" * 80)
    
    # 场景 1: Markdown 代码块
    sql1 = """```sql
SELECT * FROM users WHERE type = 'VIP';
```"""
    result1 = VannaManager._clean_sql(sql1)
    print(f"\n场景 1 - Markdown 代码块:")
    print(f"输入: {sql1}")
    print(f"清洗结果: {result1}")
    print(f"是否成功: {'✓' if '```' not in result1 else '✗'}")
    
    # 场景 2: 纯 SQL
    sql2 = "SELECT COUNT(*) FROM customers;"
    result2 = VannaManager._clean_sql(sql2)
    print(f"\n场景 2 - 纯 SQL:")
    print(f"输入: {sql2}")
    print(f"清洗结果: {result2}")
    print(f"是否成功: {'✓' if result2 == sql2 else '✗'}")
    
    # 场景 3: 带空格和换行
    sql3 = """
    
    SELECT name, age 
    FROM users 
    WHERE active = 1;
    
    """
    result3 = VannaManager._clean_sql(sql3)
    print(f"\n场景 3 - 带空格换行:")
    print(f"输入: {repr(sql3)}")
    print(f"清洗结果: {result3}")
    print(f"是否成功: {'✓' if result3.startswith('SELECT') else '✗'}")


def print_workflow_summary():
    """打印工作流程摘要"""
    print("\n" + "=" * 80)
    print("多轮推理工作流程")
    print("=" * 80)
    print("""
工作流程：

1. 第一轮生成
   - 用户提问："查询大客户数量"
   - LLM 返回：不确定"大客户"定义 + intermediate_sql
   
2. 检测中间 SQL
   - _extract_intermediate_sql() 提取：SELECT DISTINCT type FROM users
   
3. 执行中间查询
   - 获取结果：['VIP', 'Normal', 'Enterprise']
   
4. 第二轮生成
   - 构造 Prompt："原始问题 + 中间结果值列表"
   - LLM 返回：SELECT COUNT(*) FROM users WHERE type = 'VIP'
   
5. 执行最终查询
   - 如果成功 → 返回数据
   - 如果失败 → 进入自愈流程（已有功能）
   
6. 澄清对话处理
   - 如果 LLM 无法生成有效 SQL
   - _is_clarification_request() 检测是否在请求澄清
   - 返回特殊格式：chart_type = "clarification" + answer_text

特性：
✓ 自动检测中间 SQL（两种模式）
✓ 多轮推理（最多 2 轮）
✓ 澄清对话支持
✓ 与现有自愈机制兼容
✓ 完整的执行步骤追踪
    """)


if __name__ == "__main__":
    print("\n" + "🚀 " * 40)
    print("VannaManager 多轮推理功能测试")
    print("🚀 " * 40)
    
    try:
        test_extract_intermediate_sql()
        test_is_clarification_request()
        test_clean_sql()
        print_workflow_summary()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)
        print("\n提示：要测试完整的多轮推理流程，请：")
        print("1. 启动后端：cd backend && uvicorn app.main:app --reload")
        print("2. 在前端 Chat 界面提问：'查询大客户数量'")
        print("3. 观察浏览器控制台和后端日志中的 execution_steps")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
