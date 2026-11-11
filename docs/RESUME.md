# 简历与面试讲解

## 可验证项目描述

**Agent Permit — Agent 工具能力授权与审批控制面**  
技术栈：Python / FastAPI / SQLite / React / TypeScript / pytest / Playwright / GitHub Actions。

设计 Agent 工具授权控制面，采用默认拒绝策略、独立审批凭据、参数摘要绑定与过期能力令牌；在 SQLite 事务中实现工具执行、令牌消费和幂等重试，并验证并发重放与路径越权。

English summary: A capability-based tool control plane with independent reviewer credentials, immutable argument digests, expiry and transactional idempotency.

## 讲解顺序

1. 先展示一个失败或攻击场景，说明受保护的资产与信任边界。
2. 运行成功与拒绝路径，展示 API 响应和原始证据。
3. 打开核心模块，解释算法、状态或事务如何保证约束。
4. 展示测试及真实限制，并提出下一步实验。

## 常见追问

### 为什么有了提示词防护还要做权限？

检测器有漏报，授权必须独立于模型意图。最小权限与执行边界可以在模型决策失败时限制实际损失。

### 幂等如何应对并发？

BEGIN IMMEDIATE 串行化写事务，同一次执行的副作用与结果状态一起提交。第二个请求读取已保存结果。

### 如何迁移到外部支付或邮件工具？

本地数据库事务无法覆盖远端系统，需要远端幂等键、outbox 与补偿语义，不能声称端到端 exactly-once。

## 诚实使用

- 项目属于 AI 应用安全与 Agent 安全工程，不等同于大模型预训练、对齐或安全研究成果。
- 可以写真实实现和通过的测试数量；不能虚构用户量、生产 QPS、降低风险百分比或企业落地经历。
- 此初版使用 AI 辅助开发。亲自复现、修改并解释关键模块后再作为自己的面试项目展开。
- 性能或防御效果必须带上数据集版本、样本数、运行环境与测量方法。
