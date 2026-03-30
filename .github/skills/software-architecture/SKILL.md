---
name: software-architecture
description: "Software architecture principles: Clean Architecture, Hexagonal, DDD, CQRS, microservices patterns, event-driven design, and service boundary decisions. Activate when designing new services, defining boundaries, or evaluating system structure."
---

# Software Architecture Skill

## This Project's Architecture

HyperGenIA is a **microservices** platform with the following structure:

```
Client (Next.js)
    │ GraphQL (HTTP/WS)
    ▼
API Gateway (NestJS + Apollo)
    │ gRPC
    ▼
Domain Services:
  auth-svc │ user-svc │ tenant-svc │ bot-svc │ billing-svc
  notify-svc │ file-svc │ orchestrator-svc │ player-svc
  modeler-svc │ transaction-svc │ audit-svc │ ...
    │
    ▼ (each service has its own)
  MongoDB + Redis
```

**Rule**: Never propose architectural changes that deviate from this topology without explicit user approval.

---

## Clean Architecture (Applied to Each Service)

Each microservice follows Clean Architecture internally:

```
┌─────────────────────────────────────────┐
│  Frameworks & Drivers (outermost layer) │
│  NestJS, Mongoose, gRPC, Redis          │
├─────────────────────────────────────────┤
│  Interface Adapters                     │
│  Controllers, Resolvers, Repositories,  │
│  DTOs, Mappers                          │
├─────────────────────────────────────────┤
│  Application (Use Cases)                │
│  Services — orchestrate domain logic    │
├─────────────────────────────────────────┤
│  Domain (innermost layer)               │
│  Entities, Value Objects, Domain Rules  │
└─────────────────────────────────────────┘
```

**Dependency Rule**: Source code dependencies ONLY point inward. Domain knows nothing about NestJS.

### Layer Responsibilities

| Layer | Files | Allowed To Import |
|---|---|---|
| Domain | `*.entity.ts`, `*.value-object.ts` | Nothing from outer layers |
| Application | `*.service.ts` | Domain, Repository interfaces |
| Interface Adapters | `*.controller.ts`, `*.resolver.ts`, `*.repository.ts`, `*.dto.ts` | Application, Domain |
| Frameworks | `*.module.ts`, Mongoose schemas, gRPC client setup | Everything |

---

## Hexagonal Architecture (Ports & Adapters)

Think of each service as a hexagon:

```
         [gRPC Adapter]
              │
[MongoDB] ──[Service Core]── [Redis]
              │
         [Event Adapter]
```

- **Ports**: Interfaces defined in the Application layer (`IUserRepository`, `IMailPort`).
- **Adapters**: Concrete implementations (`MongoUserRepository`, `SendGridMailAdapter`).
- **Rule**: The core service NEVER imports a concrete adapter. It imports the interface.

```typescript
// ✅ Port (defined in Application layer)
export interface IBotRepository {
  findById(id: string): Promise<Bot | null>;
  save(bot: Bot): Promise<Bot>;
}

// ✅ Adapter (Frameworks layer — can import Mongoose)
@Injectable()
export class MongoBotRepository implements IBotRepository {
  constructor(@InjectModel(Bot.name) private model: Model<BotDocument>) {}
  ...
}

// ✅ Service depends on the port, not the adapter
@Injectable()
export class BotService {
  constructor(
    @Inject(BOT_REPOSITORY_TOKEN) private repo: IBotRepository,
  ) {}
}
```

---

## Domain-Driven Design (DDD) — Key Concepts

Apply DDD within individual services when the domain is complex:

| Concept | Definition | Example in HyperGenIA |
|---|---|---|
| **Entity** | Object with a unique identity that persists over time | `User`, `Bot`, `Tenant` |
| **Value Object** | Immutable, no identity, defined by its attributes | `Email`, `BotSchedule`, `MoneyAmount` |
| **Aggregate** | Cluster of entities/VOs treated as a single unit | `BotExecution` aggregate (Bot + Steps + Logs) |
| **Aggregate Root** | The entry point for operations on an aggregate | `BotExecution` (access Steps only through it) |
| **Domain Service** | Business logic that doesn't belong to a single entity | `BotConflictChecker` (checks schedule overlaps) |
| **Repository** | Collection-like interface for aggregates | `IBotRepository` |
| **Domain Event** | Something significant that happened in the domain | `BotExecutionCompleted`, `UserDeactivated` |

### Bounded Contexts in HyperGenIA

Each microservice represents a bounded context:

| Service | Bounded Context | Core Entities |
|---|---|---|
| `auth-svc` | Identity & Security | `AuthSession`, `RefreshToken` |
| `user-svc` | User Management | `User`, `UserProfile` |
| `tenant-svc` | Multi-tenancy | `Tenant`, `TenantConfig` |
| `bot-svc` | Bot Management | `Bot`, `BotVersion` |
| `orchestrator-svc` | Workflow | `Workflow`, `WorkflowNode` |
| `player-svc` | Execution | `BotExecution`, `ExecutionStep` |
| `billing-svc` | Billing | `Subscription`, `Invoice` |
| `audit-svc` | Audit Trail | `AuditEntry` |

---

## CQRS (Command Query Responsibility Segregation)

Apply when **read patterns differ significantly from write patterns**:

```typescript
// ✅ Command side — validates, mutates, emits event
@CommandHandler(CreateBotCommand)
export class CreateBotHandler {
  async execute(command: CreateBotCommand): Promise<string> {
    const bot = Bot.create(command.dto);
    await this.botRepo.save(bot);
    this.eventBus.publish(new BotCreatedEvent(bot.id));
    return bot.id;
  }
}

// ✅ Query side — optimized read, no side effects
@QueryHandler(GetBotDetailsQuery)
export class GetBotDetailsHandler {
  async execute(query: GetBotDetailsQuery): Promise<BotDetailsDto> {
    return this.botReadRepo.getWithStats(query.botId);
  }
}
```

**Use when**: A service has complex reporting/dashboards that are separate from the mutation operations.  
**Don't use when**: Simple CRUD — CQRS adds overhead not justified by simple domains.

---

## Event-Driven Architecture

HyperGenIA uses events for cross-service side effects:

### Within a service: NestJS EventEmitter
```typescript
// Fire-and-forget domain events within same process
this.eventEmitter.emit('bot.deactivated', new BotDeactivatedEvent(botId));
```

### Cross-service: gRPC (synchronous) vs Events (async)
| Use Case | Pattern |
|---|---|
| Real-time response required | gRPC (sync call) |
| Side effects (audit, notify) | Domain events → event streaming |
| Long-running tasks | Command Queue |

### Event Naming Convention
```
<aggregate>.<past-tense-verb>
bot.created
user.deactivated
bot-execution.completed
invoice.payment-failed
```

---

## Service Boundary Rules

A **new service** is justified when:
- [ ] It has its own data domain (own MongoDB collections, not shared with other services)
- [ ] It scales independently from other services
- [ ] It has clear ownership by a team or developer
- [ ] It represents a distinct bounded context

A new **module within an existing service** is sufficient when:
- [ ] It shares data with the parent service
- [ ] It doesn't need independent scaling
- [ ] It's managed by the same team

---

## Anti-Patterns — This Project

1. **Shared database**: Service A must NEVER read Service B's MongoDB collection directly.
2. **Circular gRPC calls**: Service A calls B which calls A = deadlock risk. Redesign with events.
3. **Fat API Gateway**: The API Gateway is a router/translator only — no business logic lives there.
4. **Skipping DTOs at service boundaries**: All gRPC inputs/outputs must have typed proto-generated or manual DTO classes.
5. **Mega-service**: If a service has > 10 modules and > 20 entities, consider splitting by bounded context.
6. **Synchronous chains**: A → B → C → D gRPC calls create fragile chains. Prefer async events for non-critical paths.
