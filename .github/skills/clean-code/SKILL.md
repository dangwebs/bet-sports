---
name: clean-code
description: "Clean Code principles from Robert C. Martin. Activate when writing, reviewing, or refactoring any code. Covers naming, functions, comments, error handling, formatting, and class design."
---

# Clean Code Skill

Apply the following principles to **every line of code** written or modified. This is non-negotiable for all TypeScript files in this project.

## 1. Meaningful Names

- **Reveal intent**: Name should answer — What does it do? Why does it exist? How is it used?
- **Avoid noise words**: `DataObject`, `InfoManager`, `ProcessorHelper` say nothing. Drop the suffix.
- **Use pronounceable names**: `genDtaForMdy` → `generateReportForDate`.
- **Searchable names**: Avoid single-letter variables outside loop counters. `MAX_BOT_RETRY_COUNT` beats `5`.
- **Classes are nouns**: `UserService`, `BotRepository`, `TenantModule`.
- **Functions are verbs**: `createUser()`, `validateToken()`, `scheduleBot()`.
- **Booleans read as assertions**: `isActive`, `hasPermission`, `canExecute`.

```typescript
// ❌ Bad
const d = new Date(); // What is d?
function proc(u: any) {} // What does proc do?

// ✅ Good
const registrationDate = new Date();
function deactivateUser(user: User): Promise<void> {}
```

## 2. Functions

- **Do one thing**: If you have to use "and" to describe what a function does, it does too much.
- **Small**: Aim for under 20 lines. 30 is a warning sign. Over 50 is a mandatory refactor.
- **One level of abstraction per function**: Don't mix `getHtml()` calls with string manipulation.
- **Avoid flag arguments**: `createUser(isAdmin: boolean)` → `createAdmin()` and `createRegularUser()`.
- **Prefer fewer arguments**: Ideal is 0–2. 3 is acceptable. 4+ requires a params object.
- **Command-Query Separation**: A function either does something (command) or returns something (query). Not both.

```typescript
// ❌ Bad — does too many things, has flag arg
function processUser(user: User, sendEmail: boolean) {
  user.updatedAt = new Date();
  this.repository.save(user);
  if (sendEmail) this.mailer.sendWelcome(user.email);
}

// ✅ Good — separated concerns
async function updateUser(user: User): Promise<User> {
  return this.userRepository.save({ ...user, updatedAt: new Date() });
}

async function sendWelcomeEmail(user: User): Promise<void> {
  await this.mailer.sendWelcome(user.email);
}
```

## 3. Comments

> "The best comment is a well-named function or variable."

- **Don't comment bad code — rewrite it**.
- **Allowed comments**: Legal notices, intent explanations for complex algorithms, TODO (with ticket ref), API documentation (`@param`, `@returns`).
- **Never**: Commented-out dead code. Delete it — git remembers.
- **Never**: Redundant comments that only repeat the code.

```typescript
// ❌ Bad
// Get the user by id
const user = await this.userRepository.findById(id);

// ✅ Good (no comment needed — the code reads naturally)
const user = await this.userRepository.findById(id);

// ✅ Acceptable — explains WHY, not WHAT
// Redis TTL is 5 minutes because the auth token refresh window is 4m 50s
const SESSION_TTL_SECONDS = 300;
```

## 4. Error Handling

- **Use exceptions, not return codes**: Don't return `null` or `-1` to signal errors.
- **Provide context**: Error messages must include what the operation was and what failed, not just "error".
- **Don't return null**: Return empty arrays, empty strings, or throw — never null for expected values.
- **Don't ignore caught exceptions**: Every `catch` block must act: log, re-throw, or return a meaningful error.

```typescript
// ❌ Bad
async function getUser(id: string) {
  try {
    return await this.repo.findById(id);
  } catch (e) {
    return null; // caller has no idea what went wrong
  }
}

// ✅ Good
async function getUser(id: string): Promise<User> {
  const user = await this.repo.findById(id);
  if (!user) throw new NotFoundException(`User ${id} not found`);
  return user;
}
```

## 5. Classes & Objects

- **Small classes**: A class should do one thing. If it needs multiple sections of unrelated logic, split it.
- **Hide data**: Prefer exposing behavior over raw data. Don't just add getters/setters for every field.
- **Prefer composition over inheritance**: Inherit only for true is-a relationships. Use interfaces and composition for code reuse.

## 6. Formatting

- **Vertical distance**: Related code should be near each other. Callers above callees.
- **Team rules**: Always follow the project's `.prettierrc` / ESLint config. Never override per-file.
- **Consistent indentation**: 2 spaces for TypeScript/JavaScript; 4 spaces for Python. Never mix tabs and spaces.

## 7. Tests

Clean code requires clean tests:

- **One assert per test** (ideally).
- **FIRST**: Fast, Independent, Repeatable, Self-Validating, Timely.
- **Readable**: Test names describe the scenario: `should throw when user is inactive`.
- **No magic numbers in tests**: Use named constants for expected values.
