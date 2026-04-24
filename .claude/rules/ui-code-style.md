---
paths:
  - "ui/**/*.ts"
  - "ui/**/*.tsx"
---

## UI code style

Most rules below are enforced by ESLint (`ui/eslint.config.js`) — run `npm run lint:fix` from `ui/` on files you touched before handing off (or `npm run lint` to check without modifying).

Test files (`**/__tests__/**`, `**/*.test.{ts,tsx}`, `**/*.spec.{ts,tsx}`) and `e2e/**` have relaxed rules — see the test blocks in `eslint.config.js` before assuming every rule below applies.

### Components
- **Use UI library primitives, not raw HTML.** In `src/pages/` and `src/components/layout/`, replace raw `<button>`, `<input>`, `<select>`, `<textarea>`, `<a>`, and `react-router-dom`'s `<Link>` with `<Button>`, `<Input>`, `<Select>`, `<Textarea>`, and `<AppLink>` from `@/components/ui`. The same rule applies inside `src/components/ui/`, with the primitive files themselves (Button, Input, Select, Textarea) as the only exception.
- **Merge class names with `cn()`.** Components that accept a `className` prop pass it through `cn()` from `@/lib/utils`.
- **Named components use `function` declarations.** `forwardRef` primitives (Button, Input, Select, Textarea) take an anonymous function, so they write as `export const Name = forwardRef<...>((...) => ...)` — this is the ESLint config's unnamed-component path, not a custom exemption.

### Styling
- **Semantic design tokens only.** Use `bg-primary`, `text-muted-foreground`, `border-border` — not raw Tailwind colors like `bg-blue-500`. Add new tokens in `ui/src/index.css`; see CLAUDE.md for the four-step recipe.
- **Icons are Lucide React SVG components.** No emoji in UI code.

### Imports
- **Absolute `@/` imports, never `../..`.** Relative parent paths are an ESLint error.
- **Type-only imports use `import type`.** Enforced by `@typescript-eslint/consistent-type-imports`.

### Generated code
- **Never edit `ui/src/api/generated/`.** It is codegen output. When backend endpoints change, update `ui/openapi.json` and regenerate (command in CLAUDE.md).