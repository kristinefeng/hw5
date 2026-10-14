import { useEffect, useRef } from "react";
import { AgentIcon, SEATS, toolArgs, toolPhrase } from "../agents";
import type { AgentEvent } from "../types";

function pretty(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

function since(e: AgentEvent, start: number): string {
  const s = Math.max(0, Math.round((Date.parse(e.ts) - start) / 1000));
  return `+${s}s`;
}

// Which events are worth a line in the transcript.
function visible(e: AgentEvent): boolean {
  if (e.kind === "model_response") return e.tools.some((t) => t.tool !== "delegate") || !!e.said;
  return ["run_start", "delegation_sent", "delegation_returned", "delegation_refused", "end", "error"].includes(e.kind);
}

function Body({ e, results }: { e: AgentEvent; results: Map<string, string> }) {
  switch (e.kind) {
    case "run_start": {
      const request = (e.said ?? "").replace(/^Request from the \w+ agent \(ticket \d+\):\s*/, "");
      return e.agent === "boss" ? <p className="muted">Opened the ticket and called the team.</p> : <p className="muted">Picked up: “{request}”</p>;
    }
    case "delegation_sent":
      return (
        <p>
          <span className="handoff" style={{ color: e.to ? SEATS[e.to].ink : undefined }}>
            → {e.to ? SEATS[e.to].name : "?"}
          </span>{" "}
          {(e.said ?? "").replace(/^Asked \w+: /, "")}
        </p>
      );
    case "delegation_returned":
      return (
        <p>
          <span className="handoff" style={{ color: e.from ? SEATS[e.from].ink : undefined }}>
            ← {e.from ? SEATS[e.from].name : "?"}
          </span>{" "}
          {e.summary || "reported back"}
        </p>
      );
    case "end":
      return <p className="muted">{e.agent === "boss" ? "Filed the decision." : "Filed a report."}</p>;
    case "error":
    case "delegation_refused":
      return <p className="bad">{e.said}</p>;
    default:
      return (
        <>
          {e.said && <p>{e.said}</p>}
          <div className="chips">
            {e.tools
              .filter((t) => t.tool !== "delegate")
              .map((t) => (
                <details key={t.tool_call_id} className="chip">
                  <summary title={toolPhrase(t.tool)}>
                    <code>{t.tool}</code>
                    {toolArgs(t.args) && <span>{toolArgs(t.args)}</span>}
                  </summary>
                  <pre>{results.has(t.tool_call_id) ? pretty(results.get(t.tool_call_id)!) : "…waiting for the result"}</pre>
                </details>
              ))}
          </div>
        </>
      );
  }
}

export function Transcript({ events, results, live }: { events: AgentEvent[]; results: Map<string, string>; live: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  const rows = events.filter(visible);
  const start = events.length ? Date.parse(events[0].ts) : 0;

  useEffect(() => {
    if (live) end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [rows.length, live]);

  return (
    <aside className="feed" aria-label="Agent transcript">
      <div className="feed__head">
        <h2>Transcript</h2>
        {live && <span className="live-dot">live</span>}
      </div>
      {rows.length === 0 ? (
        <p className="feed__empty">When the team works a ticket, every hand-off and every tool call shows up here. Click a tool chip to see what came back.</p>
      ) : (
        <ol className="feed__list" aria-live="polite">
          {rows.map((e) => (
            <li key={e.seq} className={`line line--${e.kind}`} style={{ ["--ink" as string]: SEATS[e.agent].ink, ["--wash" as string]: SEATS[e.agent].wash }}>
              <div className="line__who">
                <span className="line__icon">
                  <AgentIcon who={e.agent} size={15} />
                </span>
                <b>{SEATS[e.agent].name}</b>
                <time>{since(e, start)}</time>
              </div>
              <Body e={e} results={results} />
            </li>
          ))}
        </ol>
      )}
      <div ref={end} />
    </aside>
  );
}
