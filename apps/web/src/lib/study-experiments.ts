export function softmax(scores: number[], temperature: number): number[] {
  if (!scores.length || !Number.isFinite(temperature) || temperature <= 0 || scores.some(x => !Number.isFinite(x))) throw new Error("Invalid softmax input");
  const max = Math.max(...scores);
  const values = scores.map(score => Math.exp((score - max) / temperature));
  const total = values.reduce((a, b) => a + b, 0);
  return values.map(v => v / total);
}

export function posterior(prior: number, truePositive: number, falsePositive: number): number | null {
  if ([prior, truePositive, falsePositive].some(x => !Number.isFinite(x) || x < 0 || x > 1)) throw new Error("Probabilities must be in [0,1]");
  const numerator = prior * truePositive;
  const denominator = numerator + (1 - prior) * falsePositive;
  return denominator === 0 ? null : numerator / denominator;
}
