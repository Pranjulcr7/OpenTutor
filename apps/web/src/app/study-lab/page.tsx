"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MarkdownRenderer } from "@/components/shared/markdown-renderer";
import { API_BASE, buildSecureRequestInit, parseApiError, request } from "@/lib/api/client";
import { t } from "@/lib/i18n";

type Message = { role: "user" | "assistant"; content: string };
type Evidence = { citation: string; title: string; source: string; page: number | null; content: string; quality_flags: string[]; truncated: boolean };
type Result = {
  review?: { model?: string; estimated_input_tokens?: number; usage?: {input_tokens?: number; output_tokens?: number}; status: string; reason?: string; scope?: string; claims: { claim: string; verdict: string; citation: string; quote: string; reason: string }[] };
  answer: string; evidence: Evidence[]; usage: { input_tokens?: number; output_tokens?: number };
  audit: { estimated_input_tokens: number; evidence_tokens: number; history_messages_omitted: number; documents_omitted: number; output_truncated?: boolean; unknown_citations: string[] };
};

export default function StudyLab() {
  const [courses, setCourses] = useState<{ id: string; name: string }[]>([]);
  const [course, setCourse] = useState("");
  const [goal, setGoal] = useState("");
  const [mode, setMode] = useState("explain");
  const [review, setReview] = useState(false);
  const [budget, setBudget] = useState(2000);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<Message[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { request<{ id: string; name: string }[]>("/courses/").then(setCourses).catch(() => setError(t("study.courseError"))); }, []);
  function reset() { setHistory([]); setResult(null); setError(""); }
  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true); setError("");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 435000);
    try {
      const response = await fetch(`${API_BASE}/study-lab/turn`, buildSecureRequestInit({
        method: "POST", signal: controller.signal,
        body: JSON.stringify({ question, goal, mode, review, course_id: course || null, evidence_budget: budget, history: history.slice(-24) }),
      }));
      if (!response.ok) throw await parseApiError(response);
      const data: Result = await response.json();
      if (!data.answer?.trim()) throw new Error(t("study.emptyAnswer"));
      setHistory(prev => [...prev, { role: "user", content: question }, { role: "assistant", content: data.answer }]);
      setResult(data); setQuestion("");
    } catch (err) { setError(err instanceof Error ? err.message : t("study.error")); }
    finally { clearTimeout(timer); setBusy(false); }
  }
  const field = "block w-full rounded-xl border bg-background p-3 mt-2";
  return <main className="min-h-screen bg-background px-5 py-10 text-foreground">
    <div className="mx-auto max-w-6xl space-y-8">
      <nav className="flex justify-between text-sm"><Link href="/">← {t("study.workspace")}</Link><Link href="/experiments">{t("experiments.title")} →</Link></nav>
      <header><p className="text-sm uppercase tracking-widest text-muted-foreground">OpenTutor · {t("study.experimental")}</p><h1 className="mt-3 text-4xl font-semibold">{t("study.title")}</h1><p className="mt-3 max-w-2xl text-muted-foreground">{t("study.subtitle")}</p></header>
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-5 rounded-2xl border p-5 self-start">
          <Link className="block text-sm underline" href="/settings">{t("study.modelSettings")}</Link>
          <label className="block text-sm">{t("study.course")}<select className={field} value={course} disabled={busy} onChange={e => { setCourse(e.target.value); reset(); }}><option value="">{t("study.noCourse")}</option>{courses.map(c => <option value={c.id} key={c.id}>{c.name}</option>)}</select></label>
          <Link className="block text-sm underline" href={course ? `/course/${course}` : "/"}>{t("study.upload")}</Link>
          <label className="block text-sm">{t("study.mode")}<select className={field} value={mode} disabled={busy} onChange={e => setMode(e.target.value)}>{["explain", "practice", "interview", "review"].map(m => <option key={m} value={m}>{t(`study.${m}`)}</option>)}</select></label>
          <label className="block text-sm">{t("study.goal")}<textarea className={field} value={goal} disabled={busy} maxLength={1000} rows={3} onChange={e => setGoal(e.target.value)} placeholder={t("study.goalHint")} /></label>
          <label className="block text-sm">{t("study.budget")}: {budget}<input className="mt-3 w-full" type="range" min={400} max={4000} step={100} value={budget} disabled={busy} onChange={e => setBudget(Number(e.target.value))} /></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={review} disabled={busy} onChange={e => setReview(e.target.checked)} />{t("study.enableReview")}</label>
          <p className="text-xs text-muted-foreground">{t("study.memory")}</p>
          <button className="rounded-lg border px-3 py-2 text-sm" disabled={busy} onClick={reset}>{t("study.reset")}</button>
        </aside>
        <section className="space-y-5">
          <div className="min-h-64 rounded-2xl border p-6 space-y-6" aria-live="polite">
            {!history.length && <div className="py-8"><h2 className="text-xl font-medium">{t("study.start")}</h2><p className="mt-3 text-muted-foreground">{t("study.startHint")}</p><div className="mt-5 flex flex-wrap gap-2">{["attention", "dsa"].map(example => <button key={example} disabled={busy} type="button" className="rounded-xl border px-3 py-2 text-sm" onClick={() => setQuestion(t(`study.example.${example}`))}>{t(`study.exampleLabel.${example}`)}</button>)}</div></div>}
            {history.map((message, i) => <article className={message.role === "user" ? "rounded-xl bg-muted p-4" : "p-1"} key={i}><p className="mb-2 text-xs uppercase text-muted-foreground">{t(`study.${message.role}`)}</p><MarkdownRenderer content={message.content} /></article>)}
            {busy && <p role="status">{t("study.thinking")}</p>}
          </div>
          <form onSubmit={send} className="space-y-3"><label className="block">{t("study.question")}<textarea required maxLength={4000} rows={3} className={field} value={question} disabled={busy} onChange={e => setQuestion(e.target.value)} /></label><button type="submit" disabled={busy || !question.trim()} className="rounded-xl bg-primary px-5 py-3 text-primary-foreground disabled:opacity-50">{t("study.send")}</button></form>
          {error && <p role="alert" className="rounded-xl border border-destructive p-4">{error}</p>}
          {result && <section className="rounded-2xl border p-5 space-y-4">
            <h2 className="font-semibold">{t("study.audit")}</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm"><div><dt>{t("study.estimated")}</dt><dd className="text-2xl">{result.audit.estimated_input_tokens}</dd></div><div><dt>{t("study.provider")}</dt><dd className="text-2xl">{result.usage.input_tokens ?? "—"} / {result.usage.output_tokens ?? "—"}</dd></div></dl>
            <p className="text-xs text-muted-foreground">{t("study.estimateNote")} {t("study.omitted")}: {result.audit.history_messages_omitted} / {result.audit.documents_omitted}</p>
            {result.audit.output_truncated && <p role="alert">{t("study.truncatedAnswer")}</p>}
            {!!result.audit.unknown_citations.length && <p role="alert">{t("study.badCitations")}: {result.audit.unknown_citations.join(", ")}</p>}
            {result.review && <div className="space-y-3 border-t pt-4"><h3 className="font-medium">{t("study.reviewer")}: {t(`study.${result.review.status}`)}</h3><p className="text-xs text-muted-foreground">{t("study.reviewLimit")}</p>{result.review.usage && <p className="text-sm">{t("study.reviewerTokens")}: {result.review.usage.input_tokens ?? "—"} / {result.review.usage.output_tokens ?? "—"} · {result.review.model}</p>}{result.review.reason && <p>{t(`study.reason.${result.review.reason}`)}</p>}{result.review.claims.map((claim, i) => <div key={i} className="rounded-xl bg-muted p-3 text-sm"><strong>{t(`study.${claim.verdict}`)}</strong><p className="mt-2">{claim.claim}</p><blockquote className="my-2 border-l-2 pl-3">[{claim.citation}] {claim.quote}</blockquote><p>{claim.reason}</p></div>)}</div>}
            <h3 className="font-medium">{t("study.sources")}</h3>
            {!result.evidence.length && <p className="text-sm">{t("study.noEvidence")}</p>}
            {result.evidence.map(source => <details key={source.citation} className="rounded-xl bg-muted p-3 text-sm"><summary className="cursor-pointer">[{source.citation}] {source.title} {source.page && `· ${t("study.page")} ${source.page}`}</summary><p className="mt-2 text-xs">{source.source} · {source.quality_flags.join(", ")} {source.truncated && t("study.truncated")}</p><p className="mt-3 whitespace-pre-wrap">{source.content}</p></details>)}
          </section>}
        </section>
      </div>
    </div>
  </main>;
}
