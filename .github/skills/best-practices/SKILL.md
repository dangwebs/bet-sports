---
name: best-practices
description: "General engineering best practices: SOLID, DRY, YAGNI, KISS, error handling, security, performance, and API design. Activate alongside any skill that produces code."
---

# Best Practices Skill

These practices apply across all code in the project. They are the baseline for any code that is written or reviewed.

## SOLID

| Principle | Rule | Example |
|---|---|---|
| **S** Single Responsibility | One class = one reason to change | `UserService` handles users; `MailService` handles mail |
| **O** Open/Closed | Open for extension, closed for modification | Add strategies, don't add `if/switch` chains |
| **L** Liskov Substitution | Subtypes must be usable in place of base types | `AdminUser extends User` must work wherever `User` works |
| **I** Interface Segregation | Small, specific interfaces over fat ones | `Readable`, `Writable` instead of `ReadWrite` |
| **D** Dependency Inversion | Depend on abstractions, not concretions | Inject `IUserRepository`, not `MongoUserRepository` |

## DRY, YAGNI, KISS

- **DRY**: If you copy-paste code, extract it. Shared logic belongs in `packages/common` (backend) or `src/lib` (frontend).
- **YAGNI** (You Aren't Gonna Need It): Don't build features "just in case". Build only what is explicitly required now.
- **KISS**: The simplest solution that works is almost always the right one. No clever tricks.

## Error Handling

- **Fail fast**: Validate inputs at the entry point (controller/resolver/DTO) before processing.
- **Propagate errors up**: Throw exceptions at the appropriate abstraction layer, don't swallow them.
- **Structured errors**: Always return structured error objects with `code`, `message`, and optional `details`.
- **Log with context**: Include `userId`, `tenantId`, `requestId` in every error log.
- **Never expose internals**: Stack traces and DB error messages must never reach the API client.

```typescript
// ✅ Structured error with context
throw new BadRequestException({
  code: 'INVALID_SCHEDULE',
  message: 'Bot schedule conflicts with existing execution window',
  botId: dto.botId,
});
```

## Security Baseline

- **Validate everything at boundaries**: All incoming data (HTTP body, gRPC message, event payload) must be validated before use.
- **Principle of Least Privilege**: Each service, function, and user should have only the access it needs.
- **Sanitize output**: Never expose internal fields (passwords, tokens, internal IDs) in API responses.
- **Parameterize queries**: Never concatenate user input into queries or shell commands.
- **Rotate secrets**: JWT secrets and API keys must be environment variables, never committed.

## Performance Defaults

- **Lazy loading**: Don't fetch data you don't need. Use projections/field selection in MongoDB.
- **Pagination**: Every list endpoint must be paginated — never return unbounded arrays.
- **Cache aggressively but correctly**: Use Redis for session/token data. Invalidate on mutation.
- **Avoid N+1**: Use `populate()` or `DataLoader` for related data, never loop+query.
- **Async all the way**: Never block the event loop with synchronous I/O.

## API Design

- **Consistent response shape**: All responses follow `{ data, pagination?, error? }` shape.
- **Idempotent mutations**: POST/PUT mutations should be safe to retry without side effects where possible.
- **Versioning**: Breaking API changes require versioning.
- **Pagination**: Use cursor-based or offset pagination consistently.
- **Filtering**: Accept filter params as a structured object, not individual query params.

## Documentation Defaults

- **Public APIs need JSDoc**: Every exported function, class, and interface should have a one-line `@description`.
- **Why, not what**: Comments explain reasoning — `// Retry 3x because the upstream payment API times out under load`.
- **README for every service**: Each microservice must have a README with: purpose, env vars, and how to run.
- **Keep ADRs**: Significant architectural decisions should be recorded in `docs/adr/`.

## Testing Defaults

- **Test behavior, not implementation**: Tests assert on outcomes, not internal calls.
- **AAA pattern**: Every test follows Arrange → Act → Assert.
- **1 assertion per test** (ideally): Each test verifies exactly one thing.
- **Mock at the boundary**: Mock infrastructure (DB, HTTP, gRPC) — never mock the service under test.
- **Test names describe scenarios**: `should throw NotFoundException when user does not exist`.
