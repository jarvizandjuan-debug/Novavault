---
name: 21st-video
description: >-
  Create and edit a product, launch, demo, or social video from the current
  project with 21st video MCP tools. Open the editable project alongside the
  chat, apply small revision-aware edits, check rendered frames, offer visual
  variants, and export the result. Use when the user asks for a video, says
  "make a launch video for this repo", "edit this video", or points to a
  selected layer in the 21st video editor. Requires the 21st MCP server.
---

# 21st Video

Create the video with the user's coding agent and the 21st video tools. Keep
the real editor open so the user can see changes and edit the same project by
hand. Use the available tool input schemas as the source of truth for fields,
operation names, limits, and supported formats.

## Start from the product

For a new video, bound the initial inspection to the project's README, a
relevant screen or component, and available brand assets. Read release notes
when needed to support the requested message. Stop once you have the real product name,
one supported benefit, and enough copy for a first draft. Choose an aspect
ratio and a coherent short sequence, such as introduction, benefit, and
closing. Respect a request for a simpler clip; the sequence has no fixed scene
count. Keep deeper story and asset research parallel to refining the visible
draft. Keep claims grounded in the product. Respect project instructions and
any restriction on browser or computer use. Reuse the user's running app;
start a server only when authorized.

Inspect the available `video_*` tools before starting. If they are absent,
report that this connection does not offer video authoring. Use the existing
`21st-cli-use` skill for finding and installing React components; video blocks
use the separate video catalog.

## Create and open the project

For an existing project, call `video_get_doc` first and edit that same project
with its current revision and editor context. Preserve its content and the
user's hand-edited fields. Open its fresh `editorUrl` when requested; creating
a replacement project is not part of an edit.

1. Call `video_list_blocks` or `video_search_blocks` for relevant blocks. Read
   each chosen block's supported sizes and props schema before composing it.
   Each step needs a scene or background base block; element blocks belong
   in layers and cannot serve as the base for scene choices.
   Choose a block for each step that supports three meaningfully different
   layout, local motion, or style combinations while retaining that same
   block and the real content. Use the catalog's `sceneVariantStyleFields`
   with their actual enum options and numeric ranges; empty or insufficient
   style fields do not promise three choices. Check these fields before
   creating the draft; do not rely on a block name or invent unsupported props.
2. Prepare an authored first draft as initial kit ops in `blocks`: a coherent
   sequence with real product copy, explicit on-screen text props, and suitable
   timing. A project title does not replace a block's default text. Use the
   available brand colors and assets; a typographic draft can be useful while
   screenshots or footage are being prepared. Include product proof only when
   supported by real assets or product behavior.
3. Call `video_create_project` with a title, `size` (`16:9`, `9:16`, or `1:1`),
   and those `blocks`. Use `template` or `blockRef` instead when the user
   explicitly asks for a template or a single-block result, supplying real
   props where supported. These three seed fields are mutually exclusive.
   Create an empty project only when the user asks for an empty canvas.
   Retain the returned `projectId`, `rev`, and `editorUrl`.
4. Call `video_get_doc` immediately. Verify that the actual document matches
   the requested seed. An authored draft must contain the intended scenes,
   product copy, and nonzero duration. If the seed is missing content or still
   contains unrelated block defaults, fix it with a
   focused `video_apply_ops` batch using the current revision, then read again.
   Retain its revision and `editorContext` with the user's selection/frame/view
   size.
   For a new video, prepare three style choices for every authored scene and
   submit them together through `video_propose_variants` as described below.
5. Open the fresh `editorUrl` from `video_get_doc` promptly in the host's in-app
   browser. In Codex, use the native browser-opening tool, such as
   `open_in_codex` with a browser URL, when available. The URL already selects
   Codex host mode and includes a short-lived, single-use handoff. Open it intact;
   never print the handoff token or persist that URL to a repo or log. For
   final links, remove the handoff fragment from the project's editor URL. If the
   host cannot open the editor, give the stable link and continue with tools.
   Continue asset preparation and story refinement after this draft is open.
6. Check the first useful preview promptly. Inspect the real editor preview
   where available, and call `video_snapshot` at the first scene's settled
   frame from the block timing metadata. Inspect the returned image with an
   image viewing tool when available. Animated text can be invisible at frame
   zero; a blank entrance frame does not demonstrate the authored result. Use
   the editor's seek/play controls only when available and authorized.
   `video_snapshot` renders an image; it does not move the editor's playhead.
   Confirm that the product message is readable before describing the preview
   as ready, and state any limitation if you could not inspect it.

## Edit in small batches

Apply a few related operations at a time with `video_apply_ops`, supplying
`projectId`, the latest `baseRev`, `ops`, and a short `label` that explains the
user-visible change. Use the shared operation format returned by the tool.
Use block schemas for props and identifiers returned by the document/catalog;
do not invent layer IDs, block refs, or unsupported props.

Inspect `applied`, `kept`, and `errors` after every edit. A batch can keep
hand-edited fields or reject some ops; success does not mean every requested
change applied. Preserve the user's `mine` fields. Use `force` only for the
specific `id.key` fields the user explicitly asked to overwrite.

After a successful edit, retain the new revision and changed IDs. If the tool
reports a revision conflict, inspect its fresh document or call
`video_get_doc`, reconcile with the user's edits, and construct a new batch.
Never replay a stale batch blindly or replace the whole document to bypass a
conflict. Re-read before each later edit, since the user may be editing too.

For "this one", "the selected layer", or a page comment, call `video_get_doc`
and resolve the target from the current selection/frame or the comment's
`data-layer-id`. Use that stable ID for the edit. If no unambiguous target is
available, ask for the target while continuing independent work.

## Add real assets

Use `video_upload_asset` with `projectId`, `kind`, `mime`, and the file's
`bytes` for local logos, screenshots, or footage. PUT the exact file bytes to
the returned `uploadUrl` with its `contentType`. Call `video_finalize_asset`
with `projectId`, `baseRev`, and `assetId`, plus known dimensions or duration
when applicable. It verifies and attaches the uploaded asset, returning a new
revision. On conflict, retry finalization with the fresh revision; no second
upload is needed. Compose with that finalized asset through
`video_apply_ops`. Keep presigned URLs out of chat and logs. Capture a running
app only when browser/computer use is allowed by the user and project
instructions.

## Check the video and offer variants

Call `video_snapshot` with `projectId`, the current `rev`, and a `frame` for
representative frames: the settled frame of each scene, the main product
proof, and any changed or potentially clipped layer.
Inspect the returned image when an image viewing tool is available. Check
readability, contrast, crop, spacing, and timing. Fix issues through
`video_apply_ops`; do not claim a visual check from a tool's success alone.
Snapshots cover individual frames. Review playback separately when available
and do not treat snapshots as full motion or audio verification.

For a new video, offer exactly three versions for every scene or step in one
`video_propose_variants` call. Supply `projectId`, the current `baseRev`, a
short overall `label`, and `groups`: one `{sceneId, label, variants}` entry per
scene, each containing exactly three `{title, note?, ops}` options. Use scene
IDs from the actual document. Omit the root `variants` field for this mode.
Every option must use the same block and preserve the scene's copy, data,
assets, shared brand colors, fonts, logos, duration, clip timing, and
transitions. Vary only supported presentation fields, such as layout,
position, or local motion energy/stagger. Shared brand motion stays fixed.
An empty `ops` option can represent the current style, but all three resolved
styles must differ; renamed duplicates do not count. Do not change copy or
colors to manufacture a visual choice.

Inspect returned `groups` and `dropped`: each valid group has exactly three
options. The editor lets the user choose independently for each scene;
proposing does not apply an option. If a chosen block cannot provide three
real styles under these constraints, select a capable block before creating
a new project. For an existing project, preserve its block and report that
limitation instead of replacing it or supplying duplicate choices.

For an explicit whole-video or copy alternative, the existing generic mode
accepts 2 to 4 root `variants` with distinct `title`, optional `note`, and
`ops` sets. Use either `groups` or root `variants` in a call. Generic invalid
options are dropped; inspect validation details before reporting success.
Wait for the user's pick, then read the current doc/revision before making
further edits; do not silently pick a proposed variant for them.

## Export and deliver

Once the requested video is ready, call `video_export` with `projectId`, the
current `rev`, target `sizes`, and `quality` (`720p` or `1080p`). If the
service requires sign-in or the export quota is exhausted,
report the returned requirement and preserve the editable project. Never
invoke hosted AI generation to work around a video tool or quota failure.

Poll `video_export_status` with `projectId` and reasonable spacing, tracking
the jobs returned by `video_export`, until they complete or report failure.
Use the returned URL only when the export is done. Report the editable
project link, export link, and any
remaining visual/playback limitation briefly. Export renders the video; it
does not publish it to social media.

Local CLI rendering, a fullscreen MCP Apps editor, and public plugin
submission are future options. Do not promise or invoke them as available.
