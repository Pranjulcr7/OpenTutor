import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StudyLab from "./page";

vi.mock("@/components/shared/markdown-renderer", () => ({ MarkdownRenderer: ({ content }: {content: string}) => <div>{content}</div> }));
vi.mock("@/lib/api/client", () => ({
  API_BASE: "/api", request: vi.fn(async () => [{ id: "course-a", name: "Algorithms" }]),
  buildSecureRequestInit: (options: RequestInit) => options,
  parseApiError: async () => new Error("Server unavailable"),
}));

describe("Study Lab", () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  it("renders evidence and clears conversation on course change", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ok: true, json: async () => ({ answer: "Source answer", usage: {input_tokens: 120}, evidence: [{citation: "S1", title: "Lecture", source: "notes.pdf", page: 2, content: "Quoted evidence", quality_flags: [], truncated: false}], audit: {estimated_input_tokens: 100, history_messages_omitted: 0, documents_omitted: 0, unknown_citations: []}, review: {status: "not_checked", reason: "disabled", claims: []} })})));
    render(<StudyLab />);
    fireEvent.change(screen.getByLabelText("Your question or answer"), {target: {value: "Explain"}});
    fireEvent.click(screen.getByRole("button", {name: "Send"}));
    expect(await screen.findByText("Source answer")).toBeInTheDocument();
    expect(screen.getByText(/Lecture/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Source course"), {target: {value: "course-a"}});
    expect(screen.queryByText("Source answer")).not.toBeInTheDocument();
  });
  it("shows a request failure without retrying a model call", async () => {
    const fetcher = vi.fn(async () => ({ ok: false })); vi.stubGlobal("fetch", fetcher);
    render(<StudyLab />);
    fireEvent.change(screen.getByLabelText("Your question or answer"), {target: {value: "Explain"}});
    fireEvent.click(screen.getByRole("button", {name: "Send"}));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Server unavailable"));
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});

it("keeps a question when a provider returns empty answer text", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ok: true,json: async () => ({answer: "  "})})));
  render(<StudyLab />);
  fireEvent.change(screen.getByLabelText("Your question or answer"),{target:{value:"Teach me attention"}});
  fireEvent.click(screen.getByRole("button",{name:"Send"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("no answer text");
  expect(screen.getByLabelText("Your question or answer")).toHaveValue("Teach me attention");
});
