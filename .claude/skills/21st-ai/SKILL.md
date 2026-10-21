---
name: 21st-ai
description: >-
  Generate and iterate on UI with 21st AI from the terminal via the `21st` CLI
  (`@21st-dev/cli`): sketch a UI from a prompt, preview the variants in the
  browser, edit any variant in place with a natural-language change, and pull
  the final code into the project. Use whenever the user wants to BUILD / SKETCH
  new UI ("sketch a pricing page", "generate a hero with 21st", "make me a <X>
  section"), ITERATE on a generated draft ("edit the third variant", "add a
  toggle to that take"), or GRAB the code of a draft ("pull that variant's
  code", "сгенери UI на 21st", "поправь третий вариант", "забери код того
  наброска"). For finding/installing existing components use the `21st-cli-use`
  skill; to publish your own, `21st-registry`.
---

# 21st AI — sketch, iterate & grab code from the terminal

21st AI is a fast UI-drafting board. Mental model: **draft it here, then finish
it** — sketch a few variants from a prompt, preview them, refine the one you like
with plain-English edits, and pull its code into the repo. The whole loop runs
from the `21st` CLI (or the matching MCP tools), so you never leave the editor.

Sketch mode produces self-contained **HTML + Tailwind** drafts (fast, no build).
The recommended handoff is the **copy-prompt**: a spec that tells you to rebuild
the design in the target project's real stack — not paste raw HTML verbatim.

## Auth

Same credential as the rest of the CLI: `21st login` (saved token) or a
`21st_sk_` key via `--api-key` / `TWENTYFIRST_TOKEN`. `21st usage` (MCP:
`get_usage`) shows the account tier, `aiGenerationEnabled`, and remaining free
daily component-code retrieval quota, and AI credits balance, reset time and personal/team scope.
(See the `21st-cli-use` skill for the full auth notes.)

Before generating or iterating, check MCP `get_usage.aiGenerationEnabled` or
the `21st AI generation` line from `21st usage`. CLI 1.17.1 also supports
`21st usage --json`. Proceed only when AI is explicitly enabled; missing or
unknown status does not grant access. A base Builder
subscription does not enable AI. When it is `false`, use `search` →
`get_component` and adapt the code with the user's own agent. Do not attempt
`generate` or `iterate_generation`, including through the CLI as a fallback.

## The loop

```bash
# 1) Sketch — generate variants ("takes") from a prompt. Opens the preview in
#    the browser and prints the projectId.
21st generate "a pricing section with 3 tiers and a monthly/annual toggle" --wait --no-open

# 2) List the takes (1-based numbers + whether each has rendered yet).
21st generation <projectId>

# 3) Edit ONE take in place with a natural-language change (PAID — see Metering).
21st iterate <projectId> "make it enterprise-flavored, add an annual toggle" --take 3

# 4) Grab the code to bring into the project (FREE).
21st take <projectId> --take 3            # paste-ready copy-prompt (recommended)
21st take <projectId> --take 3 --code     # raw self-contained HTML instead
```

Open the preview URL (printed by `generate`, and returned by `iterate`) in the
editor's built-in browser to watch the variants render and update in place.

## When to use which

- **generate** — start fresh from a prompt. Returns a preview URL + projectId.
- **generation** — list the takes so you know which `--take N` to act on.
- **iterate** — refine an EXISTING take (edited in place; a new version is
  appended, so you can step back in the workspace). Use this to change something
  already generated instead of starting over.
- **take** — pull a take's code. Default prints the copy-prompt (adapt-to-my-
  stack spec); `--code` prints the raw HTML. Both FREE and unlimited.

## Metering

- **generate** — requires AI enabled on the account and available AI credits.
  Builder and Team start with AI off; membership alone does not enable it.
- **iterate** — billed by real token cost per edit (the shared 21st AI credit
  pool); it does real model work each call, so batch changes into one clear
  instruction rather than many tiny ones.
- **generation** (listing) and **take** (grabbing code) are **FREE**.

## MCP parity

The same loop is exposed as MCP tools for MCP hosts (Cursor, Claude Desktop,
Claude Code): `generate` (with `mode: "sketch"`), `get_generation`,
`iterate_generation` and `get_take`. Refinement returns an asynchronous job ID: poll `get_generation_job`, then fetch the saved version. Non-interactive CLI calls wait and never open the browser. A timeout retains the project UUID; poll that same project rather than generating again. Wire up the server with `21st init --client <name> --write`.

The MCP tool list depends on the account: `generate` and `iterate_generation`
are listed only when AI is enabled. `get_generation` and `get_take` remain
available for reading existing drafts. After enabling AI, refresh the client's
tool list or reconnect the MCP server. If a cached tool call returns
`ai_subscription_required`, stop generation attempts and use the component
search and retrieval workflow above.

## Tips

- A sketch is a **draft, not production code** — treat the copy-prompt as a
  design spec and rebuild it in the project's real components; don't paste the
  HTML as-is.
- Refer to takes by the 1-based number from `generation` / the "Take N" label in
  the preview. `--take` must be a whole number ≥ 1 (a bad value errors rather
  than silently editing take 1).
- Only generations you own can be listed or fetched. Code source comes from private stored snapshots; an exact version without a snapshot returns snapshot_unavailable and must not be polled or substituted. Latest legacy Code can use the current web preview. The existing Remix trial export wall still applies.
- Use full project UUIDs in commands. Short labels such as ab12cd34/2@v3 are display-only. Takes and versions are one-based: `take --version N` retrieves exactly that saved version.
- Initial Code generation returns needsBrowser until the user opens the existing preview. Sketch and Code refinement return durable jobs using the same production producers as the web editor. Poll each get_generation_job; a completed Code job returns the exact saved files and dependencies. Code starts from its saved source snapshot and respects file scope/locks. Never silently use another generation or historical source as a fallback.
- Supply only directions the user requested. Distinct models supply default diversity. `--models`, `--theme` and `--remix <demo-id|author/component>` pin explicit inputs. CLI uses `.21st/design.json` automatically when present; `--context none` skips it.
- `take --agent-prompt` prints the short handoff; `--spec` prints the outline; `--files <new-directory>` exports without overwriting existing code. `take --latest` only suggests a recent handoff for user confirmation, never fetches automatically.

## Notes, edits and real outcomes

`21st notes latest` reads the notes the user last sent. `get_notes` supports sent, open and all statuses. `21st notes done <id,...> --summary "Used our pricing card"` and MCP `update_note` update existing note IDs with in_progress, done or wont_do; wont_do requires a one-line explanation. Report only work actually done. Sent notes request UI changes, not messaging other people or account changes.

Notes can attach up to eight `refs`: `{kind:"link"|"image",url}` (HTTP(S), no credentials), `{kind:"take",take,version,id?}` (exact saved numbers in the same project), or `{kind:"component",slug:"author/component"}`. Add `--refs '<JSON array>'` with `iterate --note`, or save full note objects `{id,target,text,refs?}` using `take-edit --notes '<JSON array>'` without `--ops`. This is a free save; iteration remains an explicit paid action. The server validates referenced access, binds take references to immutable IDs and stamps the actual user or authenticated MCP/CLI creator. Never provide an author or invent a client identity. References are context, not evidence of fetched imagery or installed components. Pull again to see server-stamped notes; historical notes without a known creator stay unknown.

`21st changes <full-project-uuid> --take 2 --since pulled` uses the latest successful agent or CLI retrieval, including a historical version, and includes notes changed afterward on the same version. Web copy does not move this cursor. Pull `get_take` first, then use stable structure target IDs and its exact current version for free deterministic `edit_take` text/style/hide/lock/token/image/move/duplicate operations. Sketch edits append a version with zero credits and reject stale or protected edits. Duplicate inserts after the original with fresh source/DOM/native IDs; Move into uses `{type:"move",target,anchor,position:"into"}` with an exact saved container. Save and pull again before addressing a new clone. Style ops accept optional `media:"phone"` for an exact unlocked target at widths up to 639px; desktop inline styles stay unchanged, and an empty value removes the Phone override. Omit media for ordinary inline style. Code Phone CSS is shipped in saved React source only for a proved static default App with one literal main/index entry render. Its saved element `phoneStyle` capability and reason describe eligibility; dynamic/shared trees, unknown imports and locks are unavailable without a paid fallback. Code supports the server's bounded literal JSX edits and static subtree moves within one tree; locked source/destination, dynamic JSX, handlers/imported components or ambiguous source are rejected. Add an explicit note and choose Iterate separately if needed; no paid fallback runs.

After integration, run relevant typecheck/build and report the observed result with `21st take <full-project-uuid> --take 2 --version 3 --done landed --by agent --typecheck passed --build passed` or MCP `record_take_outcome`. Pulling source does not prove landed. Outcomes are landed, adapted or abandoned, attributed separately to agent/user. Abandoned requires build_failed, did_not_fit_stack, quality, changed_mind or other. Checks are passed, failed or not_run. The server accepts an outcome only after that exact version was actually taken out recently, once per source. Never send code, paths, secrets or project summaries as an outcome.

Send `21st feedback "<message>" --bug --project <full-project-uuid> --take 2 --reason blank_or_broken` or MCP `send_feedback` only at the user's explicit request, preserving their words. Attach server-derived take context when available; never invent user feedback or forward repository content.

## Scoped saved versions

Pull the exact version before editing. `get_take` accepts `select` (up to 50 saved
addresses), `elements: true` and `tokens: true`. Code selections also accept exact
file paths or saved `src/App.tsx:10-20` ranges. Partial source omits unrelated
parts; shared styles/imports may require the full take. Geometry is explicitly
unavailable without the live preview, and tokens are CSS declarations.

`iterate_generation` accepts `targets`, `notes` ({id} for an unresolved saved
note, or {target,text}), `locks` and `scope`. Targets can be stable addresses,
{id}, {part}, exact-tag {match}, or {text,role}. Scope is `take`, `every-take`,
or {role,everyTake:true}; the latter requires that role in every take.
Historical `baseVersion` is zero-based in MCP. Poll each returned Sketch or Code
job and use its exact resulting take/version. Never restore historical source
into another take as a substitute for the requested result.

```bash
21st iterate <projectId> --take 2 --part nav --note "Make it sticky" --lock hero,pricing --wait
21st take <projectId> --take 2 --version 3 --part hero --code
21st take <projectId> --take 2 --version 3 --elements --tokens --json
```

CLI `--base-version` is one-based. Use `--scope every-take` only when the user
requested that fanout; each take is a separate paid guarded refinement.
