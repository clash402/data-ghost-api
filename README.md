# Data Ghost

**Decision Intelligence Layer for Analytics**
An AI-powered decision intelligence layer that sits between business users and analytical systems, enabling natural-language exploration, explanation, and reasoning over real data — without replacing human judgment.

---

## 1. Elevator Pitch

**Data Ghost** is a decision intelligence layer that allows business users to ask questions in natural language and receive grounded, explainable insights backed by real data.  
It translates ambiguous questions into structured analytical workflows, executes them safely, and explains _why_ numbers changed — not just _what_ changed.

👉 **Demo / Docs:** _Coming soon_
👉 **Web repo:** <https://github.com/clash402/data-ghost-web>

---

## 2. What This Is

Data Ghost is **not a dashboard** and **not a BI replacement**.

It is a **thin, intelligent layer** that:

- Interprets natural-language analytical questions
- Plans and executes structured data queries
- Applies guardrails to prevent hallucinated insights
- Produces explanations aligned with the underlying data

Conceptually, it acts as a **translator and reasoning layer** between:

- Business users (ambiguous intent)
- Analytical systems (precise, structured data)

---

## 3. Why This Exists (Impact & Use Cases)

Most organizations struggle with a gap between:

- _What business users want to know_
- _What analytical systems can safely answer_

This gap results in:

- Over-reliance on dashboards
- Bottlenecks on analysts
- Misinterpretation of metrics
- AI tools that sound confident but are wrong

### Data Ghost addresses this by

- Reducing friction between questions and analysis
- Preserving analytical rigor
- Making uncertainty explicit
- Keeping humans in the decision loop

### Example Use Cases

- "Why did revenue drop last week?"
- "Which customer segment is driving churn?"
- "What changed in conversion after feature X launched?"
- "Is this trend real or just noise?"

### A Concrete Example

A typical interaction looks like this:

1. A user uploads a CSV containing weekly sales data.
2. The user asks: “Why did revenue drop last week?”
3. Data Ghost:
   - Interprets the intent (metric, timeframe, comparison)
   - Plans multiple analyses (traffic, conversion, order value)
   - Executes structured queries against the dataset
   - Validates results against historical variance
4. The system returns:
   - A clear explanation of the primary drivers
   - Supporting numbers for each factor
   - Confidence notes and caveats where applicable

The result is not just an answer, but a **reasoned explanation grounded in the underlying data**.

---

## 4. What This Is _Not_ (Non-Goals)

To maintain clarity and safety, Data Ghost explicitly does **not**:

- Replace analysts or business judgment
- Automatically make decisions
- Train custom ML models
- Generate insights without verifiable data
- Optimize for fully autonomous operation

Data Ghost is designed to **augment reasoning**, not automate accountability.

---

## 5. System Overview

At a high level, Data Ghost operates as a multi-step reasoning pipeline:

1. **Intent Interpretation** – Parse the user’s question
2. **Query Planning** – Decide which analyses are required
3. **Execution** – Run structured queries against real data
4. **Validation** – Check results for plausibility and completeness
5. **Explanation** – Translate results into human-readable insight

### System Flow Overview

```text
User Question
     ↓
Intent Parser
     ↓
Analytical Plan
     ↓
Query Executor
     ↓
Result Validator
     ↓
Explanation Layer
```

Each step is explicit, inspectable, and logged.

---

## 6. Example Execution Trace

**User:** "Why did weekly revenue drop?"

1. Detect metric: revenue
2. Detect timeframe: weekly
3. Identify possible drivers:
   - traffic
   - conversion
   - average order value
4. Generate queries for each factor
5. Compare week-over-week deltas
6. Validate against historical variance
7. Produce explanation with confidence notes

The system surfaces _why_ revenue changed — not just the delta.

---

## 7. Safety, Guardrails & Failure Modes

### Guardrails

- No insight without executed queries
- No extrapolation beyond available data
- Explicit confidence indicators
- Clear distinction between facts and interpretation

### Known Failure Modes

- Ambiguous questions may require clarification
- Poor data quality limits insight quality
- Sparse datasets reduce explanatory power

These limitations are surfaced to the user — not hidden.

---

## 8. Tradeoffs & Design Decisions

### Key Tradeoffs

- **Accuracy over fluency** – Safer than persuasive hallucinations
- **Transparency over magic** – Users can inspect reasoning
- **Human-in-the-loop over autonomy** – Accountability preserved

Rejected alternatives include:

- End-to-end LLM-generated analysis
- Black-box insight generation
- Fully autonomous decision engines

(See ADRs for detailed rationale.)

---

## 9. Cost & Resource Controls

Data Ghost is designed to be cost-aware by default:

- Token usage tracking per request
- Model routing (cheap vs expensive models)
- Hard budget caps
- Query execution limits

Costs are observable and predictable — not accidental.

### Example Cost Trace

Each request is instrumented with explicit token and cost reporting:

```text
[INFO] Prompt tokens: 372
[INFO] Completion tokens: 911
[INFO] Model: gpt-4.x
[INFO] Estimated cost: $0.0178
```

Cost visibility is treated as a first-class concern to prevent accidental spend and to support predictable operation at scale.

---

## 10. Reusability & Extension Points

Data Ghost is built as a **platform component**, not a monolith.

Extension points include:

- Custom intent parsers
- Pluggable query backends
- Domain-specific explanation modules
- Organization-specific guardrails

Teams can extend functionality without modifying core logic.

### Optional Retrieval-Augmented Context (RAG)

Data Ghost can optionally incorporate retrieval-augmented context from external reference material
(e.g., PDFs, documentation, business logic notes) to ground analytical reasoning.

This is particularly useful when:

- Metrics depend on domain-specific definitions
- Business logic lives outside the raw dataset
- Context is required to interpret results correctly

RAG is treated as a **supporting signal**, not a replacement for executed queries.

---

## 11. Evolution Path

### Short-Term

- Improved explanation quality
- Richer confidence scoring
- Expanded analytical patterns

### Mid-Term

- Multi-dataset reasoning
- User-specific context
- Analyst feedback loops

### Long-Term

- Organization-wide decision memory
- Cross-system analytical orchestration
- Deeper integration with planning tools

Backward compatibility and migration paths are explicitly considered.

---

## 12. Requirements & Building Blocks

- Python 3.10+
- FastAPI
- SQL-compatible data source
- Vector store (for context, optional)
- LLM provider (configurable)

This system is backend-first by design.

---

## 13. Developer Guide

Detailed setup, configuration, and API usage are documented separately.

👉 See `/docs` for:

- Setup instructions
- Environment variables
- API overview
- Project structure

---

## 14. Principal-Level Case Study (Cross-Project)

Data Ghost is one layer in a broader intelligent systems stack:

- **Taskflow** – Agentic control plane for orchestration
- **Data Ghost** – Decision intelligence layer
- **Echo Notes** – Knowledge and memory substrate

Together, these systems demonstrate how intelligent infrastructure can:

- Coordinate reasoning
- Preserve human accountability
- Scale across teams and time

A full architectural case study is available in the primary repository.

---

## 15. Author & Intent

Built by **Josh Courtney** as a build-to-learn exploration of:

- Decision intelligence systems
- Agent-assisted analytical reasoning
- Platform-oriented AI design

This project is intentionally opinionated and designed to spark discussion around how AI should support — not replace — human decision-making.
