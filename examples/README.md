# 公开开发集（5 套输入）

招聘题给定的 5 个公开调试输入，格式均为 `{topic, brief, audience}`。
`make demo` 用这 5 套产出 `.pptx`（默认 mock 离线、零成本、可复现）。

| 文件 | topic | 受众 | 推断 deck_type |
|---|---|---|---|
| `python_intro.json` | Python 入门 30 分钟 | 编程零基础 | teaching |
| `annual_review.json` | 2025 我的年度复盘 | 朋友圈分享 | review |
| `coffee_beans.json` | 如何挑选一款适合自己的咖啡豆 | 咖啡新手 | consumer |
| `rust_order_system.json` | 用 Rust 重写订单系统 | 非技术 CEO | tech / exec |
| `kyoto_weekend.json` | 周末两天玩遍京都 | 第一次去日本的游客 | travel |

> 同一套系统对不同输入推断出不同的 `deck_type` 与主题，产出“同系统、不同长相”——
> 多样性设计见 `../DESIGN.md` §4，真实成本/时延见 §5。
