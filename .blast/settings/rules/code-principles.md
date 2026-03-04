# Code Principles — blast Development Standards

> Source of truth for coding philosophy enforced across all blast phases.
> Referenced by: `design-principles.md`, `tasks-generation.md`, agent prompts.

## 1. Clean Code

### Readability First
- Code is read 10x more than written — optimize for the reader
- Meaningful names: variables, functions, and classes reveal intent
- Small functions: each does one thing, does it well, does it only
- Comments explain **why**, not **what** — the code itself explains what
- Consistent formatting within the project (enforced by linters/formatters)

### Code Smells to Eliminate
- Long methods (>20 lines is a warning sign)
- Deep nesting (>3 levels — refactor to early returns or extract)
- Magic numbers and strings — use named constants
- God classes/modules — split by responsibility
- Dead code — delete it, version control remembers

## 2. SOLID Principles

### Single Responsibility (SRP)
- One class/module = one reason to change
- If you need "and" to describe what it does, split it
- Applies to functions, classes, modules, and services

### Open/Closed (OCP)
- Open for extension, closed for modification
- Use abstractions (interfaces, protocols, base classes) to allow new behavior
- Prefer composition and strategy patterns over modifying existing code

### Liskov Substitution (LSP)
- Subtypes must be substitutable for their base types
- Don't override methods to throw "not implemented"
- Preconditions cannot be strengthened, postconditions cannot be weakened

### Interface Segregation (ISP)
- Many small, focused interfaces over one large interface
- Clients should not depend on methods they don't use
- Split fat interfaces by consumer needs

### Dependency Inversion (DIP)
- High-level modules should not depend on low-level modules — both depend on abstractions
- Inject dependencies, don't instantiate them internally
- Configuration and wiring happen at composition root

## 3. KISS — Keep It Simple, Stupid

- Simplest solution that meets the requirements wins
- Before adding complexity, ask: "Can I solve this without it?"
- Clever code is bad code — straightforward code is maintainable code
- If a junior developer can't understand it in 5 minutes, simplify
- Prefer standard library solutions over custom implementations

### Practical KISS Checks
- Can you explain the approach in one sentence?
- Are there fewer than 3 abstraction layers for this feature?
- Would removing any part break functionality? (if not, remove it)

## 4. DRY — Don't Repeat Yourself

- Every piece of knowledge has a single, authoritative representation
- Extract shared logic into reusable functions/modules
- **But**: Avoid premature abstraction — duplicate first, abstract second (Rule of Three)
- DRY applies to logic, not just code — config, schemas, and contracts too

### When Duplication is OK
- Two similar blocks serving different domains (they'll diverge)
- Test code — clarity over DRY in tests
- Prototyping phase — clean up before merge

## 5. YAGNI — You Aren't Gonna Need It

- Don't build features "just in case"
- Don't add abstractions for hypothetical future requirements
- Don't over-generalize when a specific solution works
- Every line of speculative code is maintenance debt

### YAGNI Decision Framework
- Is this requirement in the current spec? → Build it
- Is this a known upcoming requirement with a deadline? → Note it, don't build it yet
- "We might need this someday" → Don't build it
- Exception: Foundational architecture decisions (DB schema, API versioning) where retrofitting is 10x harder

## 6. Design Patterns — Use Wisely

### When to Apply Patterns
- When you recognize a recurring problem the pattern was designed to solve
- When the pattern simplifies the code (not complicates it)
- When it improves testability or extensibility for a real need

### When NOT to Apply Patterns
- Don't use a pattern just because you know it
- Don't force a pattern where a simple function call suffices
- Don't use Factory when a constructor works fine
- Don't use Observer when a direct call is clearer

### Preferred Patterns by Context
- **Creational**: Factory Method (when type varies), Builder (complex construction)
- **Structural**: Adapter (integrations), Composite (tree structures), Decorator (cross-cutting)
- **Behavioral**: Strategy (swappable algorithms), Observer (event systems), Command (undo/queue)
- **Architectural**: Repository (data access), Middleware (request pipeline), Module (bounded contexts)

### Pattern Red Flags
- Pattern adds more code than it removes complexity
- You need to explain the pattern to every new team member
- The pattern introduces indirection with no testability or flexibility benefit

## 7. No Overengineering

### Signs of Overengineering
- Building a "framework" when you need a "feature"
- Abstract base classes with only one implementation
- Configuration systems for things that never change
- Generic solutions for problems that exist in exactly one place
- Microservices for a 3-page app

### Prevention Rules
- Start concrete, abstract only when forced by a second use case
- Prototype → validate → refine (not: architect → build → hope)
- Measure complexity: if the solution is harder to understand than the problem, simplify
- Time-box design: if you've been designing for longer than it would take to build v1, stop designing

### The Simplicity Test
Ask before every architectural decision:
1. What's the simplest thing that could work?
2. What's the cost of changing this later?
3. Is the added complexity justified by a real (not imagined) requirement?

## 8. SOTA — State of the Art Solutions

### Stay Current
- Use modern language features and idioms (not legacy patterns)
- Prefer current ecosystem standards (e.g., `fetch` over `axios` when appropriate, `Bun`/`Deno` where suitable)
- Follow framework best practices for the current major version
- Use built-in solutions before reaching for libraries

### Evaluate New Tools Critically
- Maturity: Is it production-ready? (GitHub stars alone don't count)
- Maintenance: Active maintainers? Regular releases? Responsive issues?
- Community: Documentation quality? Stack Overflow coverage? Migration guides?
- Fit: Does it solve YOUR problem, or a different one?

### SOTA Decision Process
1. Check if the standard library / framework already solves it
2. Check if a well-established library exists (>2 years, active maintenance)
3. Only then consider newer alternatives — with explicit risk assessment
4. Document the choice and rationale in `research.md`

## Cross-Cutting Rules

### Testing Alignment
- Every principle above must be testable: if you can't test it, you've overcomplicated it
- TDD naturally enforces KISS, SRP, and DIP — use it
- Tests are documentation: they show intended behavior

### Code Review Checklist (derived from these principles)
- [ ] Does it do one thing well? (SRP, KISS)
- [ ] Is there duplication that should be extracted? (DRY)
- [ ] Is there abstraction that isn't needed yet? (YAGNI)
- [ ] Can I understand it without the author explaining? (Clean Code)
- [ ] Are dependencies injected, not hardcoded? (DIP)
- [ ] Is the pattern justified by a real problem? (No Overengineering)
- [ ] Are we using current best practices? (SOTA)
