#!/usr/bin/env python3
"""
验证 DashScope API Key 是否正确配置
"""

import os
import sys

def check_api_key():
    """检查 API Key 配置"""
    
    print("=" * 60)
    print("验证 DashScope API Key 配置")
    print("=" * 60)
    
    # 从环境变量获取
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    if not api_key:
        print("\n❌ DASHSCOPE_API_KEY 未配置")
        print("\n请检查：")
        print("1. ~/.zshrc 中是否配置了 export DASHSCOPE_API_KEY=...")
        print("2. 是否执行了 source ~/.zshrc")
        print("3. 当前终端是否已重启")
        return False
    
    print(f"\n✅ DASHSCOPE_API_KEY 已配置")
    print(f"   长度: {len(api_key)} 字符")
    print(f"   前缀: {api_key[:8]}***")
    
    # 导入配置检查
    print("\n验证应用配置...")
    try:
        from app.core.config import settings
        
        if settings.DASHSCOPE_API_KEY:
            print(f"✅ 应用配置正确读取到 API Key")
            print(f"   长度: {len(settings.DASHSCOPE_API_KEY)} 字符")
            return True
        else:
            print("❌ 应用配置未读取到 API Key")
            return False
            
    except Exception as e:
        print(f"❌ 导入配置失败: {e}")
        return False

if __name__ == "__main__":
    success = check_api_key()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 配置验证通过，可以正常使用 AI 功能")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 配置验证失败，请检查环境变量")
        print("=" * 60)
    
    sys.exit(0 if success else 1)
