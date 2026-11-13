# 第三方来源与许可

ReproLab 使用 MIT 许可证。运行依赖保留各自许可证，具体安装版本由 uv.lock 记录。

mini-swe-agent 参考版本为 2.4.6，源码基线为 04d809ceab9df28f9adaed044884180159172930。ReproLab 运行时继承 DefaultAgent，复用 step、query、serialize 与组件协议，扩展执行生命周期、MCP 动作、恢复和复现验证。适用 MIT 声明随项目保存。 [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) · [MIT 声明](licenses/mini-swe-agent-MIT.txt)

MCP Python SDK、OpenAI Python SDK 与 pytest 作为运行或测试依赖使用，均按上游发布的许可证分发。 [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) · [OpenAI SDK](https://github.com/openai/openai-python) · [pytest](https://github.com/pytest-dev/pytest)

Skills 格式与渐进加载方式参考 Agent Skills 规范。内置 Skill 的中文指令、模板及脚本由本项目编写。规范仓库代码为 Apache-2.0，文档为 CC-BY-4.0。 [Agent Skills](https://github.com/agentskills/agentskills)

真实题目使用 more-itertools 的公开历史版本。运行时下载的源码保持其 MIT 许可，公开示例保存来源链接、版本与生成测试。其修复提交仅由宿主验收器读取。 [more-itertools](https://github.com/more-itertools/more-itertools) · [上游许可证](https://github.com/more-itertools/more-itertools/blob/master/LICENSE)

双版本验收方法参考 SWE-bench 的失败转通过与回归检查思想。ReproLab 使用独立题集，测试结果描述对应本题集。 [SWE-bench](https://github.com/SWE-bench/SWE-bench)

Docker 基础镜像使用 Python 官方镜像的 AWS Public ECR 镜像地址，固定多平台 digest。运行环境中的 Python 和安装包保留其各自许可。 [Python 官方镜像](https://github.com/docker-library/python)
