# ReproLab 复现报告

source.mean([]) 应返回 0，非空输入返回算术平均值。当前空列表会失败，请生成测试。
这是受控恢复演示：已有 test_reproducer.py 被人为注入导入错误。请先使用 failure-triage 的 scripts/summarize.py 归纳已有日志，再覆盖同名测试文件，完成真实缺陷复现。

任务 `818e7c767f8f` · 状态 `completed` · 模式 `live`

仓库 `fixture/empty-mean` · 缺陷版本 `0bb06820d5dbd4aeeba094a435744772a2a76f51`

验收修复版本 `50a825ee574abf95dd1ba5bb3a70bbb55a7fd307`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `247ffc4974931ff0fc44d9e7bbb3b03e99bf63c9a67e4ca9da257c0d367a5f9d`

## 使用的 Skills

- `failure-triage` · 已有测试存在人为注入的导入错误，需先分类归纳日志 · 内容 `0054d049cb53fab292aef2cadb078f1970e1240b8093ac6eca2d8e1408237936`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "归纳已有导入错误日志（failure-triage scripts/summarize.py）",
      "status": "done",
      "evidence": [
        "ar-55244c48e65b8effc7d0",
        "ar-5e719ebba4efd4717004"
      ]
    },
    {
      "task": "定位 source.mean 真实实现与包导入路径",
      "status": "done",
      "evidence": [
        "ar-fb3288d78f1cf6580224"
      ]
    },
    {
      "task": "覆盖 test_reproducer.py 编写空列表与非空列表断言",
      "status": "done",
      "evidence": [
        "ar-ec548d548586ef0c11e8"
      ]
    },
    {
      "task": "运行测试确认目标缺陷复现并提交",
      "status": "done",
      "evidence": [
        "ar-ec548d548586ef0c11e8",
        "ar-b5411099d96b6ab94852"
      ]
    }
  ],
  "hypotheses": [
    {
      "id": "h1",
      "claim": "source.py 只定义 mean(values)，旧测试导入 average 导致收集期 ImportError；改为 from source import mean 后，空列表会因 sum([])/len([]) 抛 ZeroDivisionError，违反“空输入返回 0”契约。",
      "expected": "空列表断言 mean([]) == 0 失败（ZeroDivisionError）；非空列表 mean([1,2,3]) == 2 通过。",
      "status": "supported",
      "evidence": [
        "ar-55244c48e65b8effc7d0",
        "ar-fb3288d78f1cf6580224",
        "ar-ec548d548586ef0c11e8",
        "ar-b5411099d96b6ab94852"
      ],
      "next_action": "目标行为已复现（1 failed / 4 passed，失败为 source.py:2 ZeroDivisionError），提交复现测试。"
    },
    {
      "id": "initial",
      "claim": "初始测试导入可能不正确",
      "expected": "观察导入错误并定位正确函数",
      "status": "active",
      "evidence": [],
      "next_action": "运行已有测试"
    }
  ]
}
```

## 实验

- `ex-a8daaf59e1f5` · 假设 `initial` · import_error · 日志 `ar-55244c48e65b8effc7d0`
- `ex-fb979a1d7748` · 假设 `h1` · assertion_failure · 日志 `ar-ec548d548586ef0c11e8`

## 调用统计

```json
{
  "model_calls": 9,
  "input_tokens": 50188,
  "output_tokens": 1737,
  "estimated_cost_cny": 0.13713,
  "global_accounted_cny": 4.665886,
  "global_unconfirmed_calls": 0,
  "price_date": "2026-11-13",
  "input_cny_per_million": 2.4,
  "output_cny_per_million": 9.6,
  "usd_conversion": 8
}
```

## 验证边界

- 双版本差异及静态规则提供复现依据，测试语义仍需结合原始问题审查。
- 普通容器提供受约束执行，适用范围为受控的纯 Python 项目。
