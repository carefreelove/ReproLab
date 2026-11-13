# ReproLab 复现报告

more_itertools.numeric_range 的等值比较和 hash 应支持元素数量超过 sys.maxsize 的有效范围，与内置 range 行为一致。numeric_range(10**30) 的比较和哈希当前抛出 OverflowError；显式 len() 仍可抛出 OverflowError。

任务 `09c0a152402a` · 状态 `completed` · 模式 `live`

仓库 `more-itertools/more-itertools` · 缺陷版本 `08dca284ba5446a026afdc34067b658f9da989eb`

验收修复版本 `f42daddf205f335fea6e200dad46049f33e71221`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `956be75f0fec991b91573feb1bdbf835a08ffa3ff41c4bd64116ce7d7d4dc35f`

## 使用的 Skills

- `boundary-analysis` · 缺陷涉及超过 sys.maxsize 的大数边界 · 内容 `9fdd5d488abcb74e2bbf0fcbe0ae89363135a7af187052c509d8c5a928a04e53`
- `pytest-reproduction` · 需要构造 pytest 复现测试 · 内容 `1454c3bfcc04589d58f88c486053dadcd71730623505543cae57a414894eb618`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 numeric_range 的 __eq__/__hash__/__len__ 实现",
      "status": "done",
      "evidence": [
        "ar-064cf53d4dfa4c8c073d"
      ]
    },
    {
      "task": "激活 boundary-analysis 与 pytest-reproduction 技能",
      "status": "done",
      "evidence": []
    },
    {
      "task": "编写复现测试：numeric_range(10**30) 的 == 与 hash 不应抛 OverflowError，len() 仍抛",
      "status": "done",
      "evidence": []
    },
    {
      "task": "运行测试并确认错误类别，更新假设证据",
      "status": "done",
      "evidence": [
        "ar-918d704a4788160b5da3"
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
      "claim": "numeric_range.__eq__ 与 __hash__ 直接调用 len(self)，而 __len__ 返回 _len；当元素数量超过 sys.maxsize 时，Sequence/len 协议抛出 OverflowError，导致 == 与 hash 失败。内置 range 的 == 与 hash 不依赖 len()，因此不抛异常。",
      "expected": "numeric_range(10**30) == numeric_range(10**30) 返回 True，hash(numeric_range(10**30)) 返回 int 且与等值对象一致；len(numeric_range(10**30)) 抛 OverflowError。",
      "status": "supported",
      "evidence": [
        "ar-918d704a4788160b5da3"
      ],
      "next_action": "已确认：4 个目标用例在 more.py:2379/2414 抛 OverflowError，小范围与 len() 用例通过。提交复现。"
    },
    {
      "id": "h2",
      "claim": "修正为位置参数后，numeric_range(10**30) 的 ==、!=、hash、dict 键均在 more.py:2379/2414 的 len(self) 处抛 OverflowError；小范围基线与 len() 抛 OverflowError 的用例通过，说明缺陷定位在 __eq__/__hash__ 依赖 len() 而非 self._len。",
      "expected": "4 个目标用例失败于 OverflowError，2 个对照用例通过。",
      "status": "supported",
      "evidence": [
        "ar-0a12216b4828754d2545",
        "ar-1eda8c6f3cf0e8628510"
      ],
      "next_action": "目标行为已触发，提交复现。"
    }
  ]
}
```

## 实验

- `ex-b63285d6e55b` · 假设 `h2` · target_exception · 日志 `ar-0a12216b4828754d2545`
- `ex-c87ce2ea340b` · 假设 `h1` · target_exception · 日志 `ar-918d704a4788160b5da3`

## 调用统计

```json
{
  "model_calls": 21,
  "input_tokens": 228227,
  "output_tokens": 4086,
  "estimated_cost_cny": 0.58698,
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
