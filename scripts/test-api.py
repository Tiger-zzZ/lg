#!/usr/bin/env python3

"""
LG Platform API 快速测试脚本
测试核心功能的可用性
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

class LGPlatformTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.access_token = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_health(self) -> bool:
        """测试健康检查端点"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 健康检查通过: {data.get('status')}")
                    return True
                else:
                    print(f"❌ 健康检查失败: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False

    async def test_metrics(self) -> bool:
        """测试监控指标端点"""
        try:
            async with self.session.get(f"{self.base_url}/metrics") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 监控指标获取成功, 系统运行时间: {data.get('system', {}).get('uptime', 0):.2f}秒")
                    return True
                else:
                    print(f"❌ 监控指标获取失败: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 监控指标异常: {e}")
            return False

    async def test_register_user(self) -> bool:
        """测试用户注册"""
        user_data = {
            "email": "test@lgplatform.com",
            "username": "testuser",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }

        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=user_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 用户注册成功: {data.get('username')}")
                    return True
                elif response.status == 400:
                    # 用户可能已存在，这也是正常情况
                    print("ℹ️  用户可能已存在，继续测试登录")
                    return True
                else:
                    print(f"❌ 用户注册失败: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 用户注册异常: {e}")
            return False

    async def test_login_user(self) -> bool:
        """测试用户登录"""
        login_data = {
            "email": "test@lgplatform.com",
            "password": "testpassword123"
        }

        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get('access_token')
                    print(f"✅ 用户登录成功，获取到token")
                    return True
                else:
                    error_data = await response.json()
                    print(f"❌ 用户登录失败: {response.status} - {error_data.get('detail')}")
                    return False
        except Exception as e:
            print(f"❌ 用户登录异常: {e}")
            return False

    async def test_get_agent_types(self) -> bool:
        """测试获取Agent类型"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/agents/types") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 获取Agent类型成功: {list(data.keys())}")
                    return True
                else:
                    print(f"❌ 获取Agent类型失败: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 获取Agent类型异常: {e}")
            return False

    async def test_create_agent(self) -> str:
        """测试创建Agent"""
        if not self.access_token:
            print("❌ 无访问token，跳过Agent创建测试")
            return None

        agent_data = {
            "type": "research",
            "name": "测试研究Agent"
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/agents/create",
                json=agent_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    agent_id = data.get('id')
                    print(f"✅ Agent创建成功: {data.get('name')} (ID: {agent_id[:8]}...)")
                    return agent_id
                else:
                    error_data = await response.json()
                    print(f"❌ Agent创建失败: {response.status} - {error_data.get('detail')}")
                    return None
        except Exception as e:
            print(f"❌ Agent创建异常: {e}")
            return None

    async def test_execute_agent(self, agent_id: str) -> bool:
        """测试执行Agent"""
        if not self.access_token or not agent_id:
            print("❌ 无访问token或Agent ID，跳过Agent执行测试")
            return False

        execute_data = {
            "messages": ["请研究一下人工智能的发展历程"],
            "metadata": {"test": True}
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/agents/{agent_id}/execute",
                json=execute_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Agent执行成功: {data.get('status')} (耗时: {data.get('duration', 0):.3f}秒)")
                    print(f"📝 执行结果预览: {data.get('result', '')[:100]}...")
                    return True
                else:
                    error_data = await response.json()
                    print(f"❌ Agent执行失败: {response.status} - {error_data.get('detail')}")
                    return False
        except Exception as e:
            print(f"❌ Agent执行异常: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始LG Platform API测试...")
        print("=" * 50)

        tests = [
            ("健康检查", self.test_health()),
            ("监控指标", self.test_metrics()),
            ("用户注册", self.test_register_user()),
            ("用户登录", self.test_login_user()),
            ("获取Agent类型", self.test_get_agent_types()),
        ]

        results = []
        for test_name, test_coro in tests:
            print(f"\n🧪 测试: {test_name}")
            result = await test_coro
            results.append((test_name, result))

        # 如果登录成功，继续测试Agent功能
        if self.access_token:
            print(f"\n🧪 测试: 创建Agent")
            agent_id = await self.test_create_agent()
            results.append(("创建Agent", agent_id is not None))

            if agent_id:
                print(f"\n🧪 测试: 执行Agent")
                execute_result = await self.test_execute_agent(agent_id)
                results.append(("执行Agent", execute_result))

        # 输出测试总结
        print("\n" + "=" * 50)
        print("📊 测试结果总结:")

        passed = 0
        total = len(results)

        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1

        print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")

        if passed == total:
            print("🎉 所有测试通过！LG Platform运行正常！")
            return True
        else:
            print("⚠️  部分测试失败，请检查系统状态")
            return False

async def main():
    """主函数"""
    print("LG Platform API 功能测试工具")
    print("确保后端服务正在 http://localhost:8000 上运行")
    print()

    async with LGPlatformTester() as tester:
        success = await tester.run_all_tests()

        if success:
            print(f"\n✨ 测试完成！您可以访问:")
            print(f"  - API文档: http://localhost:8000/docs")
            print(f"  - 健康检查: http://localhost:8000/health")
            print(f"  - 监控指标: http://localhost:8000/metrics")

        return success

if __name__ == "__main__":
    asyncio.run(main())