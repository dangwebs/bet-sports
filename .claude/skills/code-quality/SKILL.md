---
name: code-quality
description: "Cross-cutting code quality skill. Covers Clean Code, SOLID, design patterns, error handling, security, testing, typing, formatting, and commit conventions. ALWAYS activate when writing or modifying code."
---

# Code Quality Skill

This skill is cross-cutting and applies to **ALL** code written or modified. It merges Clean Code, SOLID, design patterns, security, testing, and formatting into a single always-on reference.

## 1. Clean Code Fundamentals

### Meaningful Names

- **Reveal intent**: A name should answer — what does it do? Why does it exist?
- **Avoid noise words**: `DataObject`, `InfoManager`, `ProcessorHelper` say nothing.
- **Pronounceable names**: `genDtaForMdy` → `generateReportForDate`.
- **Searchable names**: Avoid magic numbers. `MAX_RETRY_COUNT` beats `5`.
- **Classes are nouns**: `UserService`, `OrderRepository`, `PaymentGateway`.
- **Functions are verbs**: `createUser()`, `validateToken()`, `scheduleTask()`.
- **Booleans read as assertions**: `isActive`, `hasPermission`, `canExecute`.

```typescript
// ❌ Bad
const d = new Date();
function proc(u: any) {}

// ✅ Good
const registrationDate = new Date();
function deactivateUser(user: User): Promise<void> {}
```

### Functions

- **Do one thing**: If you need "and" to describe it, it does too much.
- **Small**: Under 20 lines ideal. Over 50 is a mandatory refactor.
- **One level of abstraction**: Don't mix high-level orchestration with low-level details.
- **Avoid flag arguments**: `createUser(isAdmin: boolean)` → `createAdmin()` + `createRegularUser()`.
- **Fewer arguments**: 0–2 ideal. 3 acceptable. 4+ requires a params object.
- **Command-Query Separation**: A function either does something OR returns something. Not both.

```typescript
// ❌ Bad — does too many things, flag argument
function processUser(user: User, sendEmail: boolean) {
  user.updatedAt = new Date();
  this.repository.save(user);
  if (sendEmail) this.mailer.sendWelcome(user.email);
}

// ✅ Good — separated concerns
async function updateUser(user: User): Promise<User> {
  return this.repository.save({ ...user, updatedAt: new Date() });
}

async function sendWelcomeEmail(email: string): Promise<void> {
  await this.mailer.sendWelcome(email);
}
```

### Comments

> "The best comment is a well-named function or variable."

- **Don't comment bad code — rewrite it.**
- **Allowed**: Legal notices, intent explanations for complex algorithms, TODO with ticket ref, JSDoc for public APIs.
- **Never**: Commented-out dead code — delete it, version control remembers.
- **Never**: Redundant comments that restate what the code already says.

```typescript
// ❌ Redundant
// Get the user by id
const user = await this.repository.findById(id);

// ✅ Explains WHY, not WHAT
// TTL is 5 min because the token refresh window is 4m 50s
const SESSION_TTL_SECONDS = 300;
```

### Classes & Objects

- **Small classes**: One responsibility. If it has unrelated sections of logic, split it.
- **Hide data**: Expose behavior, not raw fields. Don't add getters/setters for every property.
- **Composition over inheritance**: Inherit only for true is-a relationships. Use interfaces and composition for reuse.

## 2. SOLID Principles

| Principle | Rule | Example |
|---|---|---|
| **S** Single Responsibility | One class = one reason to change | `UserService` handles users; `MailService` handles mail |
| **O** Open/Closed | Open for extension, closed for modification | Add strategies, don't add `if/switch` chains |
| **L** Liskov Substitution | Subtypes must be usable in place of base types | `AdminUser extends User` must work wherever `User` is expected |
| **I** Interface Segregation | Small, specific interfaces over fat ones | `Readable`, `Writable` instead of `ReadWriteAll` |
| **D** Dependency Inversion | Depend on abstractions, not concretions | Inject `IUserRepository`, not `PostgresUserRepository` |

## 3. Engineering Principles

- **DRY (Don't Repeat Yourself)**: If you copy-paste logic, extract it into a shared utility or function.
- **YAGNI (You Aren't Gonna Need It)**: Don't build features "just in case". Build only what is explicitly required now.
- **KISS (Keep It Simple)**: The simplest solution that works is almost always the right one. No clever tricks.

## 4. Design Patterns

> **Rule**: Is this solving a real current problem? If there is no observable code smell, do NOT force a pattern — KISS takes priority. Patterns are medicine, not vitamins.

### When to Consider a Pattern

| Smell | Pattern Candidate |
|---|---|
| `if/switch` branching on the same condition repeatedly | **Strategy** |
| One change requires modifying many classes | **Observer** or **Facade** |
| Direct instantiation of concrete classes everywhere | **Factory** or **DI** |
| Adding behavior without modifying existing code | **Decorator** |
| Complex object construction with many optional params | **Builder** |
| Duplicated algorithms with slight variations | **Template Method** |
| Multiple clients depending on a fat interface | **Adapter** + Interface Segregation |

### Creational Patterns

| Pattern | When to Use | Example |
|---|---|---|
| **Factory** | Object creation varies by type or needs encapsulation | `createNotification('email')` returns the right class |
| **Builder** | Many optional parameters in construction | Building a complex query or config object step-by-step |
| **Singleton** | Exactly one instance globally (use sparingly!) | Connection pool, logger instance |

```typescript
// Factory
interface Notification {
  send(to: string, message: string): Promise<void>;
}
class EmailNotification implements Notification { /* ... */ }
class SmsNotification implements Notification { /* ... */ }

function createNotification(channel: 'email' | 'sms'): Notification {
  const map = { email: EmailNotification, sms: SmsNotification };
  return new map[channel]();
}

// Builder
class QueryBuilder {
  private filters: Record<string, unknown> = {};
  withOwner(ownerId: string) { this.filters.ownerId = ownerId; return this; }
  withStatus(status: string) { this.filters.status = status; return this; }
  activeOnly() { this.filters.isActive = true; return this; }
  build() { return this.filters; }
}
```

### Structural Patterns

| Pattern | When to Use | Example |
|---|---|---|
| **Adapter** | Third-party interface doesn't match your domain | Wrapping a payment SDK behind your own interface |
| **Decorator** | Adding behavior (logging, caching) without modifying the target | Interceptors, middleware wrappers |
| **Facade** | Simplifying a complex subsystem into one clean interface | A `NotificationService` coordinating email + SMS + push |
| **Composite** | Treating individual objects and groups uniformly | Nested permissions, recursive UI trees |

```typescript
// Adapter
interface PaymentGateway {
  charge(amount: number, currency: string, token: string): Promise<string>;
}

class StripeAdapter implements PaymentGateway {
  constructor(private readonly client: StripeClient) {}
  async charge(amount: number, currency: string, token: string): Promise<string> {
    const result = await this.client.createPayment({ amount, currency, method: token });
    return result.id;
  }
}

// Facade
class NotificationFacade {
  constructor(
    private readonly emailService: EmailService,
    private readonly smsService: SmsService,
  ) {}
  async notifyUser(userId: string, message: string, channels: string[]): Promise<void> {
    await Promise.all(channels.map(ch =>
      ch === 'email'
        ? this.emailService.send(userId, message)
        : this.smsService.send(userId, message)
    ));
  }
}
```

### Behavioral Patterns

| Pattern | When to Use | Example |
|---|---|---|
| **Strategy** | Multiple algorithms swappable at runtime | Pricing calculations, execution modes |
| **Observer** | One event triggers reactions in multiple places | Event emitters, webhooks, real-time updates |
| **Repository** | Abstracting data access from business logic | `UserRepository.findById(id)` hides the data source |
| **Middleware / Chain of Responsibility** | Processing through a pipeline of steps | Auth → Validation → Rate Limit → Handler |

```typescript
// Strategy
interface PricingStrategy {
  calculate(order: Order): number;
}
class StandardPricing implements PricingStrategy { /* ... */ }
class DiscountPricing implements PricingStrategy { /* ... */ }

class OrderService {
  private strategies = new Map<string, PricingStrategy>();
  calculateTotal(order: Order, plan: string): number {
    const strategy = this.strategies.get(plan);
    if (!strategy) throw new Error(`Unknown pricing plan: ${plan}`);
    return strategy.calculate(order);
  }
}

// Repository interface
interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findAll(filters: UserFilters): Promise<User[]>;
  save(user: User): Promise<User>;
  delete(id: string): Promise<void>;
}
```

### Frontend-Specific Patterns

| Pattern | When to Use | Example |
|---|---|---|
| **Container / Presentational** | Separating data-fetching from rendering | `UserListContainer` fetches, `UserList` renders |
| **Custom Hook / Composable** | Reusing stateful logic across components | `useAuth()`, `usePagination()`, `useDebounce()` |
| **Render Props / Slots** | Component delegates rendering to the consumer | `<DataTable renderRow={(row) => ...}>` |
| **Higher-Order Component** | Wrapping with cross-cutting behavior (prefer hooks) | `withAuth(Component)`, `withTheme(Component)` |

## 5. Error Handling

- **Fail fast**: Validate inputs at the entry point (controller, handler, resolver) before processing.
- **Exceptions over return codes**: Don't return `null` or `-1` to signal errors. Throw meaningful exceptions.
- **Provide context**: Error messages must include what operation failed and why — not just "error".
- **Structured errors**: Return `{ code, message, details? }` shapes to API consumers.
- **Don't return null** for expected values: Return empty arrays, throw, or use Option/Result types.
- **Never ignore catches**: Every `catch` must log, re-throw, or return a meaningful error.
- **Never expose internals**: Stack traces and database errors must never reach the API client.

```typescript
// ❌ Bad — swallows the error
async function getUser(id: string) {
  try { return await this.repo.findById(id); }
  catch (e) { return null; }
}

// ✅ Good — fails with context
async function getUser(id: string): Promise<User> {
  const user = await this.repo.findById(id);
  if (!user) throw new NotFoundException(`User ${id} not found`);
  return user;
}
```

## 6. Security Baseline

- **Validate at boundaries**: All incoming data (HTTP body, message payload, event data) must be validated before use.
- **Least privilege**: Each service, function, and user should have only the minimum access it needs.
- **Sanitize output**: Never expose internal fields (passwords, tokens, internal IDs) in API responses.
- **Parameterize queries**: Never concatenate user input into queries or shell commands.
- **Rotate secrets**: Keys and secrets must be environment variables, never committed to source control.

## 7. Performance Defaults

- **Lazy loading**: Don't fetch data you don't need. Use projections and field selection.
- **Pagination**: Every list endpoint must be paginated — never return unbounded arrays.
- **Cache correctly**: Cache frequently-read, rarely-mutated data. Invalidate on writes.
- **Avoid N+1**: Use batch loading or eager fetching for related data — never loop + query.
- **Async all the way**: Never block the event loop with synchronous I/O.

## 8. Testing

- **Test behavior, not implementation**: Assert outcomes, not internal method calls.
- **AAA pattern**: Arrange → Act → Assert in every test.
- **One assertion per test** (ideally): Each test verifies exactly one thing.
- **FIRST**: Fast, Independent, Repeatable, Self-Validating, Timely.
- **Mock at the boundary**: Mock infrastructure (DB, HTTP, external APIs) — never the unit under test.
- **Readable names**: `should throw NotFoundException when user does not exist`.
- **No magic numbers**: Use named constants for expected values in tests.

## 9. API Design

- **Consistent response shape**: All responses follow `{ data, pagination?, error? }`.
- **Idempotent mutations**: Write operations should be safe to retry without side effects where possible.
- **Versioning**: Breaking changes require API versioning.
- **Pagination**: Use cursor-based or offset pagination consistently across all list endpoints.
- **Filtering**: Accept filter params as a structured object, not scattered individual query params.

## 10. Strict Typing

- **Zero `any`**: Using `any` is strictly prohibited. Use `unknown` when the type is truly unknown, or define generics.
- **Interfaces for shapes**: Prefer `interface` for object shapes and `type` for unions or primitive aliases.
- **Type annotations**: Every function must have explicit argument and return types.
- **Boundary validation**: Use schema validation libraries (Zod, class-validator, Joi, etc.) at system boundaries.

## 11. Import Management

Organize imports in this order, separated by blank lines:

1. **External libraries** (framework core, third-party packages).
2. **Internal shared libraries** (monorepo shared code, workspace aliases).
3. **Local modules** (relative imports from the same project).
4. **Assets / styles** (CSS, images — frontend only).

> Discover the project's actual alias patterns (`@/`, `@repo/`, `~/`, etc.) from existing files before imposing any convention.

## 12. Linting & Formatting ("Perfect Save")

Your work is **NOT DONE** until the code complies with all formatting and linter rules.

- **Discover the project's config first**: Check for `.prettierrc`, `.eslintrc`, `biome.json`, `.editorconfig`, `pyproject.toml`, or similar. Follow whatever exists.
- **If no config exists**, apply sensible defaults: single quotes, trailing semicolons, 2-space indent for TS/JS; PEP 8 / Black-style for Python.
- **Dead code cleanup**: Remove unused variables, functions, and imports.
- **Never override team rules**: Follow the project's config. Never add per-file overrides.

## 13. Conventional Commits

**Format**: `<type>(<optional scope>): <description>`

| Type | Use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring (no behavior change) |
| `style` | Formatting only (no logic change) |
| `docs` | Documentation changes |
| `chore` | Build, tooling, dependencies |
| `test` | Adding or fixing tests |
| `perf` | Performance improvement |
| `ci` | CI/CD pipeline changes |

Rules: lowercase, imperative mood, no trailing period.

## 14. Documentation

- **Public APIs need JSDoc**: Every exported function, class, and interface should have a brief `@description`.
- **Why, not what**: Comments explain reasoning — `// Retry 3x because upstream API times out under load`.
- **README per service/package**: Purpose, environment variables, and how to run.
- **ADRs for big decisions**: Record significant architectural decisions in `docs/adr/`.
