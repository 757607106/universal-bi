"""
聊天接口全面测试

测试各种查询场景，确保系统能够：
1. 处理正常查询
2. 识别不存在的列并给出合理响应
3. 处理复杂查询
4. 处理多表查询
"""

import asyncio
import sys
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.vanna.sql_generator import VannaSqlGenerator

async def run_test(name: str, question: str, dataset_id: int = 1, expect_success: bool = True):
    """运行单个测试"""
    db: Session = SessionLocal()
    try:
        print(f"\n{'=' * 70}")
        print(f"测试: {name}")
        print(f"问题: {question}")
        print(f"{'=' * 70}")
        
        result = await VannaSqlGenerator.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            use_cache=False
        )
        
        # 显示结果
        chart_type = result.get('chart_type')
        has_data = result.get('rows') is not None and len(result.get('rows', [])) > 0
        has_sql = result.get('sql') is not None
        
        print(f"\n图表类型: {chart_type}")
        print(f"有SQL: {has_sql}")
        print(f"有数据: {has_data}")
        
        if has_sql:
            print(f"SQL: {result['sql'][:150]}{'...' if len(result['sql']) > 150 else ''}")
        
        if has_data:
            print(f"返回行数: {len(result['rows'])}")
            print(f"列: {result.get('columns', [])}")
        elif result.get('answer_text'):
            print(f"回答: {result['answer_text'][:200]}...")
        
        # 验证预期
        if expect_success:
            if has_sql and (has_data or chart_type == 'clarification'):
                print("\n✓ 通过")
                return True
            else:
                print("\n✗ 失败: 预期成功但未生成有效结果")
                return False
        else:
            if chart_type == 'clarification':
                print("\n✓ 通过: 正确识别无法处理的查询")
                return True
            else:
                print("\n✗ 失败: 应该返回澄清但返回了其他结果")
                return False
                
    except Exception as e:
        print(f"\n✗ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

async def main():
    print("=" * 70)
    print("聊天接口全面测试")
    print("=" * 70)
    
    tests = [
        # === 基础查询测试 ===
        ("基础查询: 查询所有产品", "查询所有产品", 1, True),
        ("基础查询: 统计产品数量", "统计产品数量", 1, True),
        ("基础查询: 查询所有订单", "查询所有订单", 1, True),
        
        # === 条件查询测试 ===
        ("条件查询: 价格过滤", "查询价格大于100的产品", 1, True),
        ("条件查询: 分类过滤", "查询食品类产品", 1, True),
        ("条件查询: 日期范围", "查询最近30天的订单", 1, True),
        
        # === 聚合查询测试 ===
        ("聚合查询: 按类别统计", "按产品类别统计数量", 1, True),
        ("聚合查询: 计算总销售额", "计算总销售额", 1, True),
        ("聚合查询: 平均订单金额", "计算平均订单金额", 1, True),
        
        # === 排序查询测试 ===
        ("排序查询: 价格最高的产品", "查询价格最高的10个产品", 1, True),
        ("排序查询: 销售额最高的订单", "查询销售额最高的订单", 1, True),
        
        # === 不存在列的查询测试（核心修复验证）===
        ("不存在列: 库存量查询", "查询库存量少于100的产品", 1, False),
        ("不存在列: 评分查询", "查询评分最高的产品", 1, False),
        ("不存在列: 供应商查询", "查询供应商为XX的产品", 1, False),
        
        # === 多表关联查询测试 ===
        ("多表查询: 用户订单", "查询每个用户的订单总数", 1, True),
        ("多表查询: 产品销售", "查询每个产品的销售总额", 1, True),
        
        # === 复杂查询测试 ===
        ("复杂查询: 最高和最低", "查询价格最高和最低的产品", 1, True),
        ("复杂查询: TOP和BOTTOM", "查询销售额前5名和后5名的产品", 1, True),
        
        # === 模糊查询测试 ===
        ("模糊查询: 产品名称包含", "查询产品名称包含'手机'的产品", 1, True),
        ("模糊查询: 用户城市", "查询来自北京的用户", 1, True),
    ]
    
    results = []
    for test_case in tests:
        result = await run_test(*test_case)
        results.append((test_case[0], result))
        await asyncio.sleep(0.5)  # 避免请求过快
    
    # 显示总结
    print("\n\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed / total * 100:.1f}%")
    
    print("\n详细结果:")
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    # 返回状态码
    if passed == total:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
