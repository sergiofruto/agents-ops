# 2-Month Roadmap: $66K → $120-150K
**Created:** 2026-05-23
**Current salary:** ~$66-67K USD
**Target:** $120-150K USD at a startup
**Timeline:** 8 weeks

---

## The Salary Gap Diagnosis

The $66K ceiling is a platform problem, not a skills problem.

Silver.dev, Nearsure, and similar LATAM-focused staffing platforms pay $50-94K by design —
they capture the arbitrage between your cost and US market rates. The closer you get to
hiring directly with US companies, the closer you get to US market rates.

Senior full-stack + AI product experience in the US market pays $140-200K.
The goal of this roadmap is to close that channel gap in 8 weeks.

**The path:** Stop applying through LATAM middlemen. Apply directly to US startups.

---

## Why This Is Achievable

You have three things that are genuinely rare in the LATAM remote market:

1. **Unicorn logos** — Auth0 ($6.5B exit) and Scale AI on your resume. These are
   trust signals that skip the "is this person legit?" filter at US startups.

2. **Production agentic systems** — Most "AI engineers" have integrated an API.
   You've built a coordinator with real outputs running daily. That's a different thing.

3. **Streaming UI experience** — Every AI product startup building a chat/agent interface
   needs someone who's done this. You have. Most candidates haven't.

The market you're targeting exists. The question is pipeline volume and positioning precision.

---

## The Two-Month Plan

### WEEK 1-2 — Foundation
*Goal: Everything a US recruiter sees is ready before you send a single application.*

**LinkedIn (Days 1-3)**
- [ ] Publish the rewritten headline, summary, and experience entries (from `linkedin-article-streaming-ui.md` and `CLAUDE.md`)
- [ ] Add missing skills: `Next.js App Router`, `Streaming UI`, `Server-Sent Events`, `Multi-Agent Systems`, `LLM Orchestration`, `Drizzle ORM`, `shadcn/ui`
- [ ] Update Featured section: pin agents-op GitHub repo + Solaris dashboard screenshot
- [ ] Set "Open to Work" to **recruiters only** (not public — looks desperate)
- [ ] Connect with 20 CTOs/founders of AI startups you'd want to work at (no pitch, just connect)

**GitHub (Days 1-3)**
- [ ] agents-op repo: clean README with architecture diagram, live demo link, and "what it does" in the first 3 lines
- [ ] Pin 3 repos: agents-op, kinesio-study (Next.js + AI), solaris (coordinator dashboard)
- [ ] Make sure every pinned repo has a description and topics (react, nextjs, typescript, AI, agents)

**Publish the LinkedIn article (Day 4-5)**
- [ ] Post "What I learned building streaming UI for multi-agent systems"
- [ ] Use hook Option C: *"I spent a week debugging why my streaming UI felt wrong..."*
- [ ] Engage with every comment for 48h after posting — LinkedIn algorithm rewards this

**Target company list (Days 3-7)**
Build a list of 50 US startups to target. Criteria:
- Series A to Series C (big enough to pay $120K+, small enough to need you)
- AI-native or AI-first product
- Remote-friendly or distributed team
- Engineering team < 30 people (you'll have real impact)

Sources to find them:
- `wellfound.com` → filter: Remote, $120K+, Series A/B/C, Engineering
- `ycombinator.com/jobs` → filter: Full-stack, Remote
- `pallet.xyz` (curated startup job boards)
- `www.workatastartup.com` (YC companies directly)
- LinkedIn: search "CTO" + "Series A" + "AI" + posted about hiring in last 30 days
- Twitter/X: follow YC, a16z, Sequoia portfolio company CTOs

**Output of Week 1-2:** LinkedIn live, GitHub clean, article published, 50-company target list ready.

---

### WEEK 3-4 — Pipeline
*Goal: 30 applications sent. Quality > volume, but volume matters.*

**Application strategy**

Do NOT apply through job boards alone. For each target company, the funnel is:

```
1. Find the CTO or Head of Engineering on LinkedIn
2. Send a genuine connection request (no pitch)
3. Apply through their job board or careers page
4. Send a short DM 3 days after applying:
   "Hey [name] — applied for [role] via your site. I've been building
   multi-agent systems in production for the past year (agents-op on GitHub).
   Would love to be on your radar."
   3 sentences. No ask. No "I'm perfect for this." Just signal.
```

This is not spamming. It's making sure your application isn't lost in 200 others.

**Weekly application targets**
- Week 3: 15 applications (top 15 from your list)
- Week 4: 15 applications (next 15)

**Cover note per application**
Use the job-hunter-agent to generate a tailored cover note for each role.
Each one should:
- Open with Auth0 or Scale AI (name the company, name the acquisition/scale)
- Connect your streaming UI / agentic work to what they're building
- End with a concrete ask (a 20-minute call, not "hope to hear from you")
- Max 200 words

**Channels to prioritize (in order)**
1. **Direct to founder/CTO** — highest conversion, especially at seed/Series A
2. **YC Work at a Startup** — US startups, many hire LATAM, no middleman
3. **Wellfound** — filter salary to $120K+, apply directly
4. **LinkedIn Easy Apply** — low conversion but high volume; use for top-of-funnel only
5. **Contra** — fractional/contract at $80-120/hr; good bridge income while searching

**What NOT to do**
- Don't apply to more silver.dev / Nearsure / staffing agency roles — they cap at $94K
- Don't apply to roles that say "US only" or "must be authorized to work in the US" for FTE
- Don't send the same generic cover note to 30 companies

**Output of Week 3-4:** 30 applications sent, 5-10 recruiter screens booked.

---

### WEEK 5-6 — Interview Execution
*Goal: Convert screens to technical rounds. Convert technical rounds to offers.*

**Recruiter screen (30 min) — what to nail**

The salary question will come up. Script:
> "I'm targeting $120-150K USD. I've been contracting in the LATAM market at rates
> below that, but my experience — Auth0, Scale AI, 12 years, production agentic systems —
> is firmly in that range for a US-market role. I'm flexible on structure
> (contractor invoicing vs. payroll) as long as the economics get there."

Never anchor low. Never say your current salary first. If they push:
> "My current contract rate is below market for what I bring — that's part of why
> I'm making this move."

**System design screen prep**

The most likely prompt for AI product roles:
*"Design the real-time UI for a conversational AI assistant."*

Your answer framework (15 min):
1. Clarify scope (single user? concurrent users? what does the AI do?)
2. Transport choice: SSE vs WebSocket (SSE for AI streaming, explain why)
3. State model: discriminated union of message types
4. Loading states: 5 states, not `isLoading: boolean`
5. Performance: memoization, streaming isolation, virtualization
6. Error recovery: partial response + retry without losing context
7. Accessibility: screen reader support for streaming text

Practice this out loud 3 times before your first system design screen.

**Technical interview prep**

Review these every day in Week 5-6 (30 min/day):
- Next.js App Router: `use client` boundaries, server actions, caching strategies
- React: `useMemo`, `useCallback`, `startTransition`, `Suspense`, `useRef` vs `useState`
- TypeScript: discriminated unions, `z.infer<>`, generic constraints
- One LeetCode medium per day — arrays/strings/hashmaps (not trees/graphs for frontend roles)

**Assessment / take-home**

If you get a take-home, treat it like a product demo, not a test:
- Use Next.js App Router, TypeScript strict, Tailwind, shadcn/ui
- Wire a mock SSE endpoint
- Show loading states for each stream phase
- Write a short README explaining your decisions
- Add Framer Motion for one animation — instant differentiator
- Spend 30% of the time on the README. They read it before the code.

**Output of Week 5-6:** 2-4 offers in flight or imminent.

---

### WEEK 7-8 — Offer & Negotiation
*Goal: Get to $120-150K. Don't leave money on the table.*

**Negotiation principles**

1. **Never accept on the spot.** Always say: *"This is exciting — can I have 48 hours to review?"*

2. **Always counter.** Even if the offer is $130K and your target is $120K, counter at $150K.
   The worst they say is no. Most companies expect a counter.

3. **Negotiate total comp, not just base.**
   - Base salary
   - Equity (ask for the grant size, strike price, last 409A valuation, cliff, vesting schedule)
   - Learning budget ($1K-2K/year is standard)
   - Home office stipend
   - Health insurance (if US company, confirm if they cover international contractors)

4. **Use competing offers as leverage.** If you have two offers, tell both companies.
   *"I have another offer at $X — I'm more excited about your team. Can you get to $Y?"*

5. **The contractor structure question.** Many US startups will hire you as a contractor
   (you invoice them). This means:
   - No withholding, you handle Argentine taxes
   - Easier for them legally than payroll
   - You can negotiate a slightly higher rate to offset benefits you're not getting
   - Ask for $130-140K contractor if the FTE equivalent is $120K

**If offers come in below $120K**

Counter script:
> "I appreciate the offer. Based on my experience at Auth0 and Scale AI, and the
> production AI systems I've shipped, I was expecting to be in the $130-140K range.
> Is there flexibility there? I'm committed to this role — I just want to make sure
> the economics reflect the scope."

Most companies have 10-20% flex above their initial offer. Use it.

**Output of Week 7-8:** Signed offer at $120-150K.

---

## Metrics to Track Weekly

| Metric | Week 3-4 target | Week 5-6 target |
|---|---|---|
| Applications sent | 30 | 40 total |
| Recruiter screens | 5 | 10 total |
| Technical rounds | 1 | 4 total |
| Offers | 0 | 1-2 |
| LinkedIn article views | 500+ | 1,000+ |
| LinkedIn profile views | 2x baseline | 3x baseline |

---

## Where To Find $120-150K Remote Roles (Bookmark These)

| Platform | How to use | Notes |
|---|---|---|
| `wellfound.com` | Filter: Remote + $120K+ + Series A/B + Engineering | Best for direct startup applications |
| `ycombinator.com/jobs` | No filter needed — all YC companies | Many hire LATAM, pay US rates |
| `workatastartup.com` | YC's official job board | Same as above, different UI |
| `pallet.xyz` | Browse curated boards (a16z, YC, Sequoia portfolios) | High signal |
| `contra.com` | Fractional/contract, $80-120/hr | Good bridge income |
| `linkedin.com/jobs` | Filter: Remote + $120K+ + Full-time | High volume, lower signal |
| `arc.dev` | Explicitly for LATAM engineers targeting US rates | Worth trying |
| `toptal.com` | Rigorous vetting but $100-150/hr once in | Long onboarding |

---

## The 10 Companies to Target First

Based on your stack (React/Next.js/TS + AI product + streaming UI), these company types
have the highest probability of paying $120-150K and hiring from Argentina:

1. **AI assistant / copilot startups** (Series A-B) — Prospera AI is a perfect example
2. **Fintech with AI features** — wealth management, expense management, accounting AI
3. **B2B SaaS adding AI workflows** — any vertical SaaS adding an "AI mode"
4. **Developer tools** — Auth0-adjacent: auth, monitoring, observability with AI
5. **Healthcare AI** — clinical decision support, patient communication (streaming UI critical)

Use Wellfound + YC job board to find 2-3 companies in each category.

---

## Weekly Check-In Template

Every Sunday, answer these 5 questions:
1. How many applications went out this week?
2. How many screens/interviews happened?
3. What's the best response I got — what worked?
4. What got no response — why? (stack mismatch? salary too high? wrong channel?)
5. What do I adjust next week?

---

## Files In This Project

```
job-hunter-agent/
├── CLAUDE.md                                    ← Full candidate profile
├── config/
│   └── profile.yml                             ← Machine-readable profile
└── reports/
    ├── roadmap-2month-120k.md                  ← This file
    ├── market-analysis-senior-frontend-2026.md ← 7 roles, salary benchmarks
    ├── prospera-ai-fullstack-frontend.md        ← 10 Qs + model answers
    ├── homevision-sr-frontend-engineer.md       ← 10 Qs + model answers
    └── linkedin-article-streaming-ui.md         ← Article draft + publishing notes
```

---
*Created: 2026-05-23 | Review at end of Week 4 and adjust based on response rates*
