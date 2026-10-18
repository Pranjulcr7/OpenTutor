"use client";

import { useState } from "react";
import Link from "next/link";
import { softmax, posterior } from "@/lib/study-experiments";
import { t } from "@/lib/i18n";

export default function Experiments() {
  const [scores, setScores] = useState([1, 2, 3]);
  const [temperature, setTemperature] = useState(1);
  const [prior, setPrior] = useState(0.01);
  const [tpr, setTpr] = useState(0.9);
  const [fpr, setFpr] = useState(0.1);
  const weights = softmax(scores, temperature);
  const probability = posterior(prior, tpr, fpr);
  return <main className="min-h-screen bg-background px-5 py-10 text-foreground"><div className="mx-auto max-w-5xl space-y-8">
    <Link className="text-sm" href="/study-lab">← {t("experiments.back")}</Link>
    <header><p className="text-sm uppercase tracking-widest text-muted-foreground">OpenTutor</p><h1 className="mt-3 text-4xl font-semibold">{t("experiments.title")}</h1><p className="mt-3 text-muted-foreground">{t("experiments.subtitle")}</p></header>
    <div className="grid gap-6 md:grid-cols-2">
      <section className="rounded-2xl border p-6 space-y-5"><h2 className="text-xl font-semibold">{t("experiments.softmax")}</h2><p className="text-sm text-muted-foreground">{t("experiments.predictSoftmax")}</p>
        {scores.map((value, i) => <label className="block text-sm" key={i}>{t("experiments.score")} {i + 1}: {value.toFixed(1)}<input type="range" min={-5} max={5} step={0.1} value={value} className="mt-2 w-full" onChange={e => setScores(prev => prev.map((s, j) => i === j ? Number(e.target.value) : s))} /></label>)}
        <label className="block text-sm">{t("experiments.temperature")}: {temperature.toFixed(1)}<input type="range" min={0.1} max={3} step={0.1} value={temperature} className="mt-2 w-full" onChange={e => setTemperature(Number(e.target.value))} /></label>
        <table className="w-full text-sm"><caption className="text-left mb-3">{t("experiments.weights")}</caption><tbody>{weights.map((w, i) => <tr key={i}><th className="pr-3 py-2 text-left">{i + 1}</th><td className="w-full"><progress className="w-full" max={1} value={w} aria-label={`${t("experiments.weight")} ${i + 1}`} /></td><td className="pl-3 tabular-nums">{(100 * w).toFixed(2)}%</td></tr>)}</tbody></table><p className="text-xs text-muted-foreground">{t("experiments.softmaxNote")}</p>
      </section>
      <section className="rounded-2xl border p-6 space-y-5"><h2 className="text-xl font-semibold">{t("experiments.bayes")}</h2><p className="text-sm text-muted-foreground">{t("experiments.predictBayes")}</p>
        {([{label: "prior", value: prior, set: setPrior}, {label: "tpr", value: tpr, set: setTpr}, {label: "fpr", value: fpr, set: setFpr}]).map(item => <label key={item.label} className="block text-sm">{t(`experiments.${item.label}`)}: {(item.value * 100).toFixed(1)}%<input className="mt-2 w-full" type="range" min={0} max={1} step={0.001} value={item.value} onChange={e => item.set(Number(e.target.value))} /></label>)}
        <div className="rounded-xl bg-muted p-5" aria-live="polite"><p className="text-sm">{t("experiments.posterior")}</p><p className="mt-2 text-4xl font-semibold">{probability === null ? t("experiments.undefined") : `${(probability * 100).toFixed(2)}%`}</p></div><p className="text-xs text-muted-foreground">{t("experiments.bayesNote")}</p>
      </section>
    </div>
  </div></main>;
}
