---
name: design-patterns
description: "Software design patterns: Creational, Structural, and Behavioral (GoF). Activate when identifying code smells, refactoring, or designing components where a pattern improves structure. Includes NestJS and React-specific patterns."
---

# Design Patterns Skill

> **Rule before applying any pattern**: Is this solving a real current problem? If there is no observable code smell or pain point, do NOT force a pattern — KISS takes priority. Patterns are medicine, not vitamins.

## When to Consider a Pattern

Look for these signals:

| Smell | Pattern Candidate |
|---|---|
| `if/switch` branching on the same condition repeatedly | **Strategy** |
| One change requires modifying many classes | **Observer** or **Facade** |
| Direct instantiation of concrete classes everywhere | **Factory** or **DI** |
| Adding behavior without modifying existing code | **Decorator** |
| Complex object construction with many optional params | **Builder** |
| Duplicated algorithms with slight variations | **Template Method** |
| Multiple clients depending on a fat interface | **Adapter** + Interface Segregation |

---

## Creational Patterns

### Factory Method
**When**: Object creation logic varies by type or requires encapsulation.

```typescript
// ✅ NestJS context: notification factory
interface Notification {
  send(to: string, message: string): Promise<void>;
}

class EmailNotification implements Notification { ... }
class WhatsAppNotification implements Notification { ... }

function createNotification(channel: 'email' | 'whatsapp'): Notification {
  const map = { email: EmailNotification, whatsapp: WhatsAppNotification };
  return new map[channel]();
}
```

### Builder
**When**: Constructing complex objects with many optional parameters.

```typescript
// ✅ Query builder for MongoDB filters
class BotQueryBuilder {
  private filters: Record<string, unknown> = {};

  withTenant(tenantId: string) { this.filters.tenantId = tenantId; return this; }
  withStatus(status: BotStatus) { this.filters.status = status; return this; }
  activeOnly() { this.filters.isActive = true; return this; }

  build() { return this.filters; }
}

// Usage
const query = new BotQueryBuilder()
  .withTenant(tenantId)
  .activeOnly()
  .build();
```

### Singleton (Use Sparingly)
**When**: Exactly one instance must exist (loggers, connection pools).  
**In NestJS**: Providers are singletons by default — don't implement it manually.

---

## Structural Patterns

### Adapter
**When**: Integrating a third-party library whose interface doesn't match your domain.

```typescript
// ✅ Wrapping a payment SDK
interface PaymentGateway {
  charge(amount: number, currency: string, token: string): Promise<string>;
}

class StripeAdapter implements PaymentGateway {
  constructor(private readonly stripe: Stripe) {}

  async charge(amount: number, currency: string, token: string): Promise<string> {
    const intent = await this.stripe.paymentIntents.create({ amount, currency, payment_method: token });
    return intent.id;
  }
}
```

### Decorator
**When**: Adding behavior (logging, caching, validation) to an object without modifying it.  
**In NestJS**: Use `@nestjs/common` decorators and Interceptors over manual decorator classes.

```typescript
// ✅ NestJS Interceptor as Decorator pattern
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const start = Date.now();
    return next.handle().pipe(
      tap(() => console.log(`Handler took ${Date.now() - start}ms`))
    );
  }
}
```

### Facade
**When**: Simplifying a complex subsystem behind a single clean interface.

```typescript
// ✅ NotificationFacade hides email + WhatsApp complexity
@Injectable()
export class NotificationFacade {
  constructor(
    private readonly emailService: EmailNotificationService,
    private readonly whatsappService: WhatsAppNotificationService,
  ) {}

  async notifyUser(userId: string, message: string, channels: Channel[]): Promise<void> {
    await Promise.all(
      channels.map(ch => ch === 'email'
        ? this.emailService.send(userId, message)
        : this.whatsappService.send(userId, message)
      )
    );
  }
}
```

---

## Behavioral Patterns

### Strategy
**When**: Multiple algorithms can be swapped at runtime based on context.

```typescript
// ✅ Bot execution strategy
interface ExecutionStrategy {
  execute(bot: Bot, context: ExecutionContext): Promise<ExecutionResult>;
}

class SequentialExecutionStrategy implements ExecutionStrategy { ... }
class ParallelExecutionStrategy implements ExecutionStrategy { ... }

@Injectable()
export class BotExecutionService {
  private strategies = new Map<string, ExecutionStrategy>([
    ['sequential', new SequentialExecutionStrategy()],
    ['parallel', new ParallelExecutionStrategy()],
  ]);

  async execute(bot: Bot, mode: string): Promise<ExecutionResult> {
    const strategy = this.strategies.get(mode);
    if (!strategy) throw new Error(`Unknown execution mode: ${mode}`);
    return strategy.execute(bot, this.buildContext(bot));
  }
}
```

### Observer
**When**: One event needs to trigger reactions in multiple places.  
**In NestJS**: Use `EventEmitter2` or the built-in CQRS `EventBus`.

```typescript
// ✅ Domain event → multiple handlers
export class BotExecutionCompletedEvent {
  constructor(
    public readonly botId: string,
    public readonly tenantId: string,
    public readonly durationMs: number,
  ) {}
}

@EventsHandler(BotExecutionCompletedEvent)
export class SendCompletionNotificationHandler {
  async handle(event: BotExecutionCompletedEvent): Promise<void> {
    await this.notifyService.notifyTenant(event.tenantId, `Bot ${event.botId} finished`);
  }
}

@EventsHandler(BotExecutionCompletedEvent)
export class RecordAuditLogHandler {
  async handle(event: BotExecutionCompletedEvent): Promise<void> {
    await this.auditService.record(event);
  }
}
```

### Repository
**When**: Abstracting data access from business logic.

```typescript
// ✅ Clean repository interface
export interface IBotRepository {
  findById(id: string): Promise<Bot | null>;
  findByTenant(tenantId: string): Promise<Bot[]>;
  save(bot: Bot): Promise<Bot>;
  delete(id: string): Promise<void>;
}
```

---

## React / Frontend Patterns

### Custom Hook
**When**: Reusing stateful logic across multiple components.

```typescript
// ✅ Encapsulate bot list fetching + pagination
function useBotList(tenantId: string) {
  const [page, setPage] = useState(1);
  const { data, loading, error } = useQuery(GET_BOTS, {
    variables: { tenantId, page },
  });
  return { bots: data?.bots ?? [], loading, error, page, setPage };
}
```

### Container / Presentational
**When**: Separating data-fetching logic from rendering.

```typescript
// Container — fetches data, passes to component
function BotListContainer({ tenantId }: { tenantId: string }) {
  const { bots, loading } = useBotList(tenantId);
  if (loading) return <BotListSkeleton />;
  return <BotList bots={bots} />;
}

// Presentational — pure rendering, no data logic
function BotList({ bots }: { bots: Bot[] }) {
  return <ul>{bots.map(b => <BotListItem key={b.id} bot={b} />)}</ul>;
}
```
