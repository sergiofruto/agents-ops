# LinkedIn Article Draft
**Title:** What I learned building streaming UI for multi-agent systems
**Target length:** ~600 words (long enough to show depth, short enough to read in 3 min)
**Goal:** Inbound from AI product startups. Signal: I've built this in production, not read about it.
**Tone:** Practitioner writing for practitioners. No hype. Specific.

---

# What I learned building streaming UI for multi-agent systems

Most streaming UI tutorials show you the same thing: connect to an endpoint, append tokens to a div, done.

That works for a single model call. It falls apart the second you have multiple agents running in parallel, tool calls happening mid-response, and a user who needs to understand what's happening — not just see text appear.

Here's what I actually learned building it.

---

## The illusion of simplicity

A single `ReadableStream` piped to the client feels clean. You open the connection, tokens arrive, you render them. The hard part isn't the stream — it's everything around it.

In my agents-op platform I have a coordinator that dispatches work to multiple agents simultaneously: a market analyzer, a signal scorer, a synthesizer that waits for both. From the user's perspective, something should be happening on screen the entire time. But what? And how do you represent "three things running in parallel" without making the UI look like a loading spinner graveyard?

That's the real problem. Not the stream. The mental model you're building for the user while the agents work.

---

## Typing indicators lie

The first thing I shipped was a typing indicator — the classic three dots. It felt right. It was wrong.

A typing indicator implies one agent, one response, coming soon. When you have a coordinator running parallel tasks, the typing indicator becomes noise. It doesn't tell the user *what* is happening, only that *something* is. For a tool where users are making decisions based on the output, "something is happening" isn't enough.

I replaced it with per-agent status labels: **"Analyzing markets…"**, **"Scoring signals…"**, **"Generating brief…"** Each one updates as its agent transitions through states. The user can see the pipeline, not just the spinner.

This sounds obvious in retrospect. It wasn't obvious at 11pm debugging why the UI felt wrong even though the code was correct.

---

## Three stream states that aren't "loading"

Real streaming has at least five states most tutorials ignore:

1. **Waiting for first token** — the model is thinking. Nothing has arrived yet.
2. **Streaming** — tokens are arriving. Render them.
3. **Tool call in progress** — the model paused to call a tool. This is not loading. This is work happening.
4. **Resuming after tool call** — the model got the tool result and is continuing.
5. **Done** — stream closed cleanly.

Plus two failure modes: **stream error mid-response** (you have partial text and an error) and **timeout** (the model never responded).

Each of these needs a different UI treatment. Collapsing them all into `isLoading: true` is how you end up with a spinner that sits there for 30 seconds with no information.

For tool calls specifically — this was the biggest UI insight — I show a small inline indicator: *"Fetching price data…"* right where the model paused. When the tool returns, the indicator disappears and the stream continues. The user sees the agent working, not a black box.

---

## Don't re-render the world on every token

This one is purely technical but it matters for perceived performance.

If your streaming message component re-renders on every token, and your message list re-renders with it, you're doing work proportional to (tokens × message count) on every chunk. In a long session with 50 messages, that's 50 full re-renders per token.

The fix: isolate the streaming region. Memoize everything above it. Only the active streaming message should update. By the time a message finishes streaming and joins the history, it's a static node — it should never re-render again.

I use a `useStreamingMessage` hook that accumulates chunks in a ref (not state) and only commits to state on meaningful boundaries — end of sentence, tool call boundary, or stream close. The UI stays smooth even when the model is outputting fast.

---

## What this taught me about AI product design

The best streaming UI isn't the one that shows the most information. It's the one that shows the *right* information at the *right* moment — enough to keep the user oriented, not so much that the interface becomes the thing they're thinking about instead of the output.

The AI is doing complex work. The user shouldn't have to think about that complexity. That's the job.

---

*I build production agentic systems and the UIs that make them usable. Currently based in Buenos Aires, open to senior full-stack / AI product roles with remote-friendly US teams.*

*→ agents-op on GitHub: github.com/sergiofruto/agents-op*

---

## Publishing Notes

**Best time to post:** Tuesday or Wednesday, 9–11am ART
**Hashtags:** `#React` `#NextJS` `#AIEngineering` `#FullStack` `#AgenticAI` `#StreamingUI` `#BuildInPublic`

**Hook variants (test one as the opening line):**

Option A (current — problem-first):
> Most streaming UI tutorials show you the same thing: connect to an endpoint, append tokens to a div, done.

Option B (contrarian):
> Streaming UI is not hard. Streaming UI for multi-agent systems is a completely different problem.

Option C (specific):
> I spent a week debugging why my streaming UI felt wrong — even though the code was technically correct. Here's what I missed.

**Follow-up post ideas (build a series):**
1. "The 5 loading states your AI UI is missing" — expand the 5-state section into a visual post
2. "Why I chose SSE over WebSockets for my AI platform" — technical comparison post
3. "Building a multi-agent coordinator from scratch" — architecture deep-dive

---
*Saved: 2026-05-23*
