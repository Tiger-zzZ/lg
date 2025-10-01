"""
测试配置驱动的Agent实现

验证所有Agent类型都能正常工作并保持向后兼容性。
"""

import asyncio
import sys
import os

# 添加父目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.agents.manager import agent_manager
from app.agents.config import config_manager


async def test_agent_types():
    """测试所有Agent类型"""
    print("=" * 60)
    print("配置驱动Agent架构测试")
    print("=" * 60)

    # 获取所有Agent类型
    agent_types = agent_manager.get_available_types()
    print(f"\n✅ 发现 {len(agent_types)} 种Agent类型:")
    for agent_type, description in agent_types.items():
        print(f"  • {agent_type}: {description}")

    print("\n" + "=" * 60)
    print("测试Agent创建和基本功能")
    print("=" * 60)

    # 测试每种Agent类型
    test_messages = {
        "chat": "你好，请介绍一下你自己",
        "search": "Python编程",
        "coding": "如何写一个快速排序函数？",
        "writing": "帮我写一篇关于AI的文章",
        "research": "人工智能的发展历史",
        "rag": "什么是机器学习？",
    }

    results = {}

    for agent_type in ["chat", "search", "coding", "writing", "research", "rag"]:
        print(f"\n{'—' * 60}")
        print(f"📋 测试 Agent类型: {agent_type}")
        print(f"{'—' * 60}")

        try:
            # 创建Agent
            agent = agent_manager.create_agent(agent_type)
            print(f"✅ Agent创建成功")
            print(f"   • ID: {agent.id}")
            print(f"   • 名称: {agent.name}")
            print(f"   • 描述: {agent.description}")

            # 获取配置信息
            config = config_manager.get_config(agent_type)
            print(f"   • Emoji: {config.emoji}")
            print(f"   • 温度: {config.llm_config.temperature}")
            print(f"   • 最大Token: {config.llm_config.max_tokens}")
            print(f"   • 能力: {[c.value for c in config.capabilities]}")

            results[agent_type] = {
                "status": "success",
                "agent_id": agent.id,
                "name": agent.name
            }

            print(f"✅ {agent_type} 测试通过")

        except Exception as e:
            print(f"❌ {agent_type} 测试失败: {str(e)}")
            results[agent_type] = {
                "status": "failed",
                "error": str(e)
            }

    # 测试自定义配置
    print(f"\n{'=' * 60}")
    print("测试自定义配置")
    print(f"{'=' * 60}")

    try:
        custom_config = {
            "llm_config": {
                "temperature": 0.5,
                "max_tokens": 1500
            }
        }

        agent = agent_manager.create_agent("chat", custom_config=custom_config)
        config = config_manager.get_config("chat", custom_config)

        print("✅ 自定义配置测试通过")
        print(f"   • 自定义温度: {config.llm_config.temperature}")
        print(f"   • 自定义最大Token: {config.llm_config.max_tokens}")

        results["custom_config"] = {"status": "success"}

    except Exception as e:
        print(f"❌ 自定义配置测试失败: {str(e)}")
        results["custom_config"] = {"status": "failed", "error": str(e)}

    # 测试向后兼容性
    print(f"\n{'=' * 60}")
    print("测试向后兼容性（使用旧实现）")
    print(f"{'=' * 60}")

    try:
        agent = agent_manager.create_agent("data_analyst", use_legacy=True)
        print("✅ 向后兼容性测试通过")
        print(f"   • DataAnalystAgent仍可使用")
        print(f"   • Agent名称: {agent.name}")

        results["backward_compat"] = {"status": "success"}

    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {str(e)}")
        results["backward_compat"] = {"status": "failed", "error": str(e)}

    # 总结
    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")

    success_count = sum(1 for r in results.values() if r["status"] == "success")
    total_count = len(results)

    print(f"\n总测试数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {total_count - success_count}")

    if success_count == total_count:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print("\n⚠️  部分测试失败")
        for test_name, result in results.items():
            if result["status"] == "failed":
                print(f"  • {test_name}: {result.get('error', 'Unknown error')}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_agent_types())
    sys.exit(0 if success else 1)
