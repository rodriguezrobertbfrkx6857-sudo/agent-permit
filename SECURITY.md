# Security model

## Intended scope

Agent Permit is a single-user, local research workbench. Bind to loopback. Code publication on GitHub does not deploy a public service. Host/origin checks reduce browser-to-local attacks but do not provide user authentication. Except for Agent Permit's role-separated routes, APIs are local and unauthenticated. Before shared deployment, add identity, authorization, TLS, quotas, retention and tenant isolation.

## Trust boundaries

| Boundary | Control | Residual risk |
| --- | --- | --- |
| Browser → API | Local binding, trusted Host and Origin, strict body schema, 128 KiB limit | Local programs can still call the API; no global rate limit |
| Untrusted text → HTML | React text rendering; no raw HTML injection | Dependencies and browser extensions remain trusted |
| API → SQLite | Parameterized SQL, WAL, explicit write transactions | Local operator can read/modify DB; no at-rest encryption |
| Audit events → evidence | Metadata-only records, SHA256 chaining | No external anchor; truncation and complete rewrite undetectable |
| Server → optional model | Operator-controlled endpoint, bounded timeout, no redirects | Misconfigured endpoint or malicious provider still matters |

`TRUSTED_HOSTS` is an operator environment setting, comma-separated; defaults to localhost, 127.0.0.1 and testserver. Do not set a wildcard for a shared deployment. `APP_DB` chooses a local database path. Keep `data/`, `.env`, session capabilities and reviewer keys out of Git.

## Project-specific assumptions

- 本地 UI 同时展示两个角色以便演示；生产必须拆分审批入口并使用真实身份提供方。
- 默认演示凭据是公开的 local-demo-agent / local-demo-reviewer，只允许本地演示。
- 笔记路径是 SQLite 内的逻辑命名空间，不是宿主机文件系统沙箱。
- 能力令牌是 bearer secret；持有者可执行获批的这一次调用，需使用 TLS 与安全传递通道。
- 数据库写入和能力消费在同一事务中；额外审计链追加在事务之后，进程崩溃可能导致审计缺口。

## Reporting

Use GitHub private vulnerability reporting if enabled. Otherwise open an issue containing only a minimal synthetic reproduction, never real secrets or customer data. This project does not claim production readiness or comprehensive LLM safety guarantees.
