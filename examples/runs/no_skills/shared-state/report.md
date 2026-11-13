# ReproLab 复现报告

source.Bucket 的不同实例应拥有独立的 items 列表。调用 add(value) 后另一个实例也出现了数据。

任务 `62af73fb0a05` · 状态 `completed` · 模式 `live`

仓库 `fixture/shared-state` · 缺陷版本 `76bd021083c1d479ddea1694a62cb2fd82fa4433`

验收修复版本 `fd9adfe6843405e6b6a8e59204702f2bfa71d233`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `9660940e7161eb33c9f0898e0ec0f04c94273b3fda7ac35facceea16fdb8fab1`

## 使用的 Skills


## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 source.Bucket 类定义与 items 初始化方式",
      "status": "done",
      "evidence": [
        "ar-2af5a23e11ad64ba7a1a"
      ]
    },
    {
      "task": "记录假设：items 为类级可变默认值导致实例共享",
      "status": "done",
      "evidence": [
        "ar-812b746081ea3e0295f9"
      ]
    },
    {
      "task": "编写复现测试：两个实例 add 后互不影响",
      "status": "done",
      "evidence": []
    },
    {
      "task": "运行测试并核对错误类别，更新假设证据",
      "status": "done",
      "evidence": [
        "ar-812b746081ea3e0295f9",
        "ar-6b4641d0300981ce182b"
      ]
    },
    {
      "task": "提交复现",
      "status": "in_progress",
      "evidence": []
    }
  ],
  "hypotheses": [
    {
      "id": "h1",
      "claim": "source.Bucket 的 items 是类级可变列表，add() 通过 self.items.append 修改类属性，导致所有实例共享同一列表",
      "expected": "两个独立实例分别 add 后，各自 items 只包含自己的值；缺陷版本中 b2.items 会包含 b1 添加的值",
      "status": "supported",
      "evidence": [
        "ar-812b746081ea3e0295f9",
        "ar-6b4641d0300981ce182b"
      ],
      "next_action": "证据已足：两个测试均 assertion_failure，b1.items 为 [1,2]、新实例 items 为 [1,2,'x']，确认类级共享；提交复现"
    }
  ]
}
```

## 实验

- `ex-e03dd496f22e` · 假设 `h1` · assertion_failure · 日志 `ar-812b746081ea3e0295f9`

## 调用统计

```json
{
  "model_calls": 7,
  "input_tokens": 27087,
  "output_tokens": 1390,
  "estimated_cost_cny": 0.078356,
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
