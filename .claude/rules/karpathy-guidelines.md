Behavioral guidelines to reduce common LLM coding mistakes.

1. **Think before coding** — state assumptions explicitly. If uncertain, ask. If multiple interpretations exist, present them. Push back when a simpler approach exists.

2. **Simplicity first** — minimum code that solves the problem. No speculative features, no abstractions for single-use code, no error handling for impossible scenarios.

3. **Surgical changes** — touch only what you must. Don't "improve" adjacent code, comments, or formatting. Match existing style. Remove only imports/variables that YOUR changes made unused.

4. **Goal-driven execution** — define verifiable success criteria before implementing. For multi-step tasks, state a brief plan with verification checks.