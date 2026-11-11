import { useState } from "react";
import { KeyRound, ArrowRight } from "lucide-react";
import { Shell, Card, Metrics, Json, ErrorBox, Empty, Badge } from "./ui";
export default function App() {
  const [tool, setTool] = useState("notes.write"),
    [path, setPath] = useState("reports/security-review.md"),
    [content, setContent] = useState(
      "# Security review\nThe tool boundary has been inspected.",
    ),
    [agent, setAgent] = useState("local-demo-agent"),
    [reviewer, setReviewer] = useState("local-demo-reviewer"),
    [proposal, setProposal] = useState<any>(null),
    [result, setResult] = useState<any>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function request(endpoint: string, body: unknown, role: string) {
    const r = await fetch("/api" + endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        [role === "agent" ? "X-Agent-Key" : "X-Reviewer-Key"]:
          role === "agent" ? agent : reviewer,
      },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail);
    return d;
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell
      title="Agent Permit"
      subtitle="让 Agent 的每次行动都受约束。独立审批、参数绑定、一次性能力令牌和事务级幂等执行。"
      number="03"
    >
      <Metrics
        items={[
          ["权限模型", "Deny by default"],
          ["授权有效期", "300 seconds"],
          ["执行介质", "SQLite notes"],
        ]}
      />
      <ErrorBox error={error} />
      <div className="columns">
        <div>
          <Card title="工具调用提案" kicker="01 / PROPOSE">
            <div className="samples">
              <button
                onClick={() => {
                  setTool("notes.write");
                  setPath("reports/security-review.md");
                }}
              >
                需审批写入
              </button>
              <button
                onClick={() => {
                  setTool("notes.read");
                  setPath("reports/security-review.md");
                }}
              >
                范围内读取
              </button>
              <button
                onClick={() => {
                  setTool("notes.read");
                  setPath("reports/../secret.md");
                }}
              >
                路径越权
              </button>
              <button onClick={() => setTool("shell")}>未授权工具</button>
            </div>
            <label htmlFor="tool">工具名称</label>
            <select
              id="tool"
              value={tool}
              onChange={(e) => setTool(e.target.value)}
            >
              <option>notes.write</option>
              <option>notes.read</option>
              <option>shell</option>
            </select>
            <label htmlFor="path">资源路径</label>
            <input
              id="path"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
            {tool === "notes.write" && (
              <>
                <label htmlFor="content">写入内容</label>
                <textarea
                  id="content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </>
            )}
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                action(async () => {
                  setResult(null);
                  setProposal(
                    await request(
                      "/proposals",
                      {
                        tool,
                        arguments:
                          tool === "notes.write" ? { path, content } : { path },
                      },
                      "agent",
                    ),
                  );
                })
              }
            >
              <KeyRound size={16} />
              {busy ? "处理中…" : "检查并提交提案"}
              <ArrowRight size={16} />
            </button>
            <p className="note">
              notes 是真实持久化的 SQLite
              笔记工具，路径是逻辑命名空间。系统不执行 shell 或外部网络请求。
            </p>
          </Card>
          <Card title="独立角色凭据" kicker="LOCAL DEMO">
            <label htmlFor="agent">Agent key</label>
            <input
              type="password"
              id="agent"
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
            />
            <label htmlFor="reviewer">Reviewer key</label>
            <input
              type="password"
              id="reviewer"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
            />
            <p className="note">
              预填的是公开的本地演示凭据。部署时分别设置 AGENT_API_KEY 与
              REVIEWER_API_KEY，并隔离审批界面。
            </p>
          </Card>
        </div>
        <Card title="授权状态机" kicker="02 / AUTHORIZE">
          {proposal ? (
            <>
              <div className="result-head">
                <Badge
                  good={
                    proposal.state === "approved" ||
                    proposal.state === "executed"
                  }
                >
                  {proposal.state.toUpperCase()}
                </Badge>
              </div>
              <p className="answer">{proposal.reason}</p>
              {[
                "Proposal created",
                "Policy evaluated",
                "Reviewer approved",
                "Capability consumed",
              ].map((step, i) => (
                <div className="step" key={step}>
                  <b>
                    0{i + 1} / {step}
                  </b>
                  <span>
                    {i < 2
                      ? "COMPLETE"
                      : i === 2
                        ? proposal.state === "approved" || result
                          ? "COMPLETE"
                          : "WAITING"
                        : result
                          ? "COMPLETE"
                          : "WAITING"}
                  </span>
                </div>
              ))}
              <p className="note">参数摘要：{proposal.argument_digest}</p>
              {proposal.state === "pending" && (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    action(async () =>
                      setProposal({
                        ...proposal,
                        ...(await request(
                          "/proposals/" + proposal.id + "/approve",
                          {},
                          "reviewer",
                        )),
                      }),
                    )
                  }
                >
                  以 Reviewer 身份批准这组参数
                </button>
              )}
              {proposal.capability && (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      setResult(
                        await request(
                          "/proposals/" + proposal.id + "/execute",
                          {
                            capability: proposal.capability,
                            idempotency_key: "ui-" + proposal.id,
                          },
                          "agent",
                        ),
                      );
                      setProposal({ ...proposal, state: "executed" });
                    })
                  }
                >
                  {result ? "重试同一请求，验证幂等" : "使用能力令牌执行"}
                </button>
              )}
              {result && (
                <>
                  <h3>执行回执</h3>
                  <div className="token-output">
                    {JSON.stringify(result.output, null, 2)}
                  </div>
                  <p className="note">
                    {result.replayed
                      ? "幂等重放：返回原结果，未重复写入。"
                      : "事务已提交，令牌已消费。"}
                  </p>
                  <Json value={result} />
                </>
              )}
              <Json
                value={{
                  ...proposal,
                  capability: proposal.capability ? "[REDACTED]" : null,
                }}
              />
            </>
          ) : (
            <Empty text="提交提案后查看权限决策与审批路径。" />
          )}
        </Card>
      </div>
    </Shell>
  );
}
