"""Test real tutor delivery through a running Study Lab UI proxy.

No keys, prompts, answers or provider error bodies are printed. This tests
availability and visible answer delivery, not correctness or learning quality.
"""

import argparse
import os
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3001/api")
    args = parser.parse_args()
    headers = {}
    token = os.environ.get("OPENTUTOR_TEST_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    questions = [
        (
            "attention",
            "Explain attention in a Transformer with one small example. Keep it under 150 words.",
        ),
        (
            "binary_search",
            "Given nums=[5,7,7,8,8,10] and target=8, find the first and last indices in O(log n). Give one hint, not the full solution.",
        ),
        ("followup", "Why would we need two binary searches?"),
    ]
    history = []
    with httpx.Client(
        base_url=args.base_url.rstrip("/") + "/",
        timeout=435,
        headers=headers,
        trust_env=False,
    ) as client:
        try:
            # A normal GET establishes CSRF cookies; health is exempt.
            client.get("preferences/runtime/llm")
            csrf = client.cookies.get("csrf_token")
            if csrf:
                client.headers["X-CSRF-Token"] = csrf
            for label, question in questions:
                if label == "binary_search":
                    history = []
                start = time.monotonic()
                response = client.post(
                    "study-lab/turn",
                    json={
                        "question": question,
                        "mode": "explain",
                        "review": False,
                        "history": history,
                    },
                )
                if response.status_code != 200:
                    print(
                        f"{label}: FAIL HTTP {response.status_code}; inspect the app for a safe error message."
                    )
                    return 1
                body = response.json()
                answer = body.get("answer", "")
                if not isinstance(answer, str) or not answer.strip():
                    print(f"{label}: FAIL empty answer")
                    return 1
                usage, audit = body.get("usage", {}), body.get("audit", {})
                print(
                    f"{label}: PASS {time.monotonic() - start:.1f}s; chars={len(answer)}; input={usage.get('input_tokens', 'unknown')}; output={usage.get('output_tokens', 'unknown')}; truncated={bool(audit.get('output_truncated'))}; unknown_citations={len(audit.get('unknown_citations', []))}"
                )
                history += [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            print(
                f"FAIL {type(exc).__name__}; verify that the app and model server are running."
            )
            return 1
    print(
        "Delivery checks passed. Review answer quality manually; this is not an accuracy benchmark."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
