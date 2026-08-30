# Hybrid RAG Document Assistant — Design System

This document defines an original product interface for the workflow:

**Documents → Index → Ask → Grounded Answer → Inspect Evidence**

The system borrows only high-level principles from the Clay, Airtable, and Replicate references: confidence, information clarity, and technical directness. It does not inherit their layouts, components, branding, palettes, typography, or page structures.

## 1. Design philosophy

The interface is a working instrument for understanding documents, not a marketing site, dashboard, chat client, or retrieval visualizer.

Five principles govern every decision:

1. **Evidence is part of the answer.** Provenance is available from the moment a claim appears, without overwhelming the initial reading experience.
2. **The workflow shapes the interface.** Documents, indexing, asking, answering, and inspection are progressive modes—not permanent columns competing for space.
3. **Technical truth stays visible.** Retrieval method, reranking, source identity, and limitations use direct language. The interface never hides uncertainty behind AI decoration.
4. **Density must remain readable.** Information can be compact, but primary text is large, spacing is deliberate, and metadata is disclosed in layers.
5. **Color has a job.** Accent colors identify retrieval signals and active evidence. They are not used to decorate arbitrary containers.

The desktop canvas should feel occupied and intentional at 100% zoom. It may extend to 1600px, with practical outer gutters rather than a narrow centered article column.

## 2. Product personality

The product is:

- Confident without being theatrical.
- Technically credible without resembling a terminal.
- Friendly without becoming playful or toy-like.
- Precise without feeling institutional.
- Distinctive through composition, typography, and evidence behavior—not illustration or visual effects.

The voice is concise and literal. Prefer “3 documents indexed” over “Your knowledge base is ready.” Prefer “Reranked 12 candidates” over “AI found the best sources.” Avoid anthropomorphism, sparkle language, and conversational filler.

The signature visual identity is the combination of:

- substantial **document slabs** during ingestion;
- continuous **claim-aware answer prose** rather than boxed messages;
- a temporary full-width **evidence stage** that opens from the active citation;
- functional signal colors for semantic retrieval, BM25, fusion, and evidence focus.

## 3. Information architecture principles

### Workflow modes

The workspace has three primary modes, reached through the product workflow rather than a global sidebar:

1. **Documents:** ingest files, see extraction/indexing state, inspect document metadata, and remove or reset a corpus.
2. **Ask:** compose a question and read the grounded answer.
3. **Evidence:** inspect the source passage supporting the selected citation or claim.

Documents and Ask may coexist during transition, but they must not become a permanent three-column dashboard. Evidence is a focused state layered into the current task, not an always-open right rail.

### Hierarchy

- The current task receives the largest area.
- Corpus status is persistent but compact after indexing completes.
- The question remains visible while its answer is active.
- The answer is the primary reading surface.
- Evidence takes over meaningful space only after explicit citation selection.
- Retrieval controls and score details remain collapsed by default.

### Desktop composition

- Use the full available width with 32–48px workspace gutters.
- Prefer one dominant working field plus one temporary contextual field.
- Do not divide the application into equal columns.
- Do not reserve large blank margins around a narrow reading measure.
- Keep answer line length comfortable by controlling the prose measure within a wider composition, using surrounding space for question context, source identity, or evidence—not emptiness.

## 4. Typography system

Use **Mona Sans Variable** as the preferred product family. It provides a recognizable technical-product character without borrowing the current frontend typography or the reference families.

Bundle Mona Sans as a local application asset when licensing and build tooling allow it. The implementation must not depend on a runtime font download, external font CDN, or network availability. If Mona Sans cannot be bundled reliably, use the high-quality system fallback without blocking rendering or changing the hierarchy.

Fallback:

`"Mona Sans", "Segoe UI Variable", "Aptos", system-ui, sans-serif`

Monospace is not part of the visual identity. Machine identifiers such as chunk IDs use Mona Sans with tabular numerals. Code-style typography is reserved for actual code only.

| Token | Size | Weight | Line height | Use |
|---|---:|---:|---:|---|
| `type-display` | 42px | 650 | 1.08 | Workspace mode title; never a landing-page hero |
| `type-heading-1` | 32px | 650 | 1.18 | Answer heading, empty-state heading |
| `type-heading-2` | 24px | 650 | 1.25 | Evidence title, document group heading |
| `type-heading-3` | 20px | 600 | 1.3 | Document title, claim focus heading |
| `type-answer` | 21px | 450 | 1.58 | Grounded answer prose |
| `type-body` | 17px | 430 | 1.55 | Default UI copy and passages |
| `type-control` | 16px | 600 | 1.25 | Inputs, buttons, disclosure controls |
| `type-meta` | 14px | 520 | 1.4 | Scores, file type, chunk ID, status |

Rules:

- No essential text below 14px.
- Default editable text is at least 17px.
- Use size and placement before using heavy weight.
- Limit weights to 430, 520, 600, and 650.
- Avoid uppercase paragraphs. Uppercase is allowed only for short, nonessential state labels under 18 characters.
- Use tabular numerals for retrieval scores, chunk counts, percentages, and ranks.
- Do not use giant marketing typography above 48px inside the application.

## 5. Color system

The palette is light-first, cool, and mineral. It deliberately avoids beige, navy-led AI styling, black/gold, and the rejected blue/off-white system.

### Core tokens

| Token | HEX | Role |
|---|---|---|
| `canvas` | `#F2F6F4` | Cool mineral workspace floor |
| `surface` | `#FFFFFF` | Primary readable surface |
| `surface-muted` | `#E6ECE8` | Secondary work band and inactive regions |
| `surface-strong` | `#D5DFD9` | Pressed or grouped structural region |
| `ink` | `#18221F` | Primary text |
| `ink-secondary` | `#43504B` | Supporting text |
| `ink-muted` | `#66736D` | Tertiary metadata; never essential content |
| `border` | `#B5C1BA` | Input and object boundaries |
| `border-strong` | `#74817A` | Active structural boundary |

### Product signal tokens

| Token | HEX | Role |
|---|---|---|
| `action` | `#C63F30` | Primary action and focused claim marker |
| `action-hover` | `#A83226` | Hover/pressed action state |
| `action-soft` | `#F6DAD5` | Selected claim or citation context |
| `semantic` | `#6557C5` | Semantic retrieval signal only |
| `semantic-soft` | `#E8E4FA` | Semantic score track background |
| `bm25` | `#267154` | BM25 retrieval signal only |
| `bm25-soft` | `#DCEDE5` | BM25 score track background |
| `fusion` | `#B56B14` | Hybrid fusion signal only |
| `fusion-soft` | `#F5E6CE` | Fusion score track background |
| `evidence` | `#F1CC48` | Active citation and evidence anchor |
| `evidence-soft` | `#FFF3B9` | Evidence-stage highlight |

### Semantic state tokens

| Token | HEX | Role |
|---|---|---|
| `success` | `#1F7554` | Indexed, completed |
| `warning` | `#946200` | Partial extraction, indexing delay |
| `error` | `#B4232C` | Failed upload, extraction, query, or provider |
| `focus` | `#7147D8` | Keyboard focus ring |
| `disabled` | `#89948F` | Disabled foreground |

Color rules:

- `action` is the only general-purpose accent.
- `semantic`, `bm25`, and `fusion` appear only when explaining retrieval.
- `evidence` identifies provenance, never generic emphasis.
- Do not color every document differently. File type is communicated by icon and label first.
- Never place low-contrast muted text on colored surfaces.
- Avoid decorative gradients. Progress may use a single solid fill.

## 6. Spacing scale

Use a 4px base with a practical product rhythm:

| Token | Value | Use |
|---|---:|---|
| `space-1` | 4px | Tight icon/text adjustment |
| `space-2` | 8px | Inline relationships |
| `space-3` | 12px | Compact metadata groups |
| `space-4` | 16px | Standard control and row gap |
| `space-5` | 24px | Component padding |
| `space-6` | 32px | Workspace group separation |
| `space-7` | 40px | Major internal separation |
| `space-8` | 56px | Mode-level separation |
| `space-9` | 72px | Rare empty-state breathing room |

Rules:

- Desktop workspace gutters: 32px below 1440px, 48px at 1440px and above.
- Mobile gutters: 16px.
- Repeated metadata uses 8–12px gaps; reading content uses 24–32px gaps.
- Avoid universal 1px-rule-and-24px rhythms. Different relationships require visibly different spacing.
- Do not exceed 72px of intentional empty space inside the working viewport unless required for a state transition.

## 7. Surface and border language

The application is built from continuous work fields, not a grid of floating cards.

- `canvas` is the application floor.
- `surface` is used for the active reading or manipulation field.
- `surface-muted` identifies secondary context without simulating elevation.
- Containers exist only for objects users can select, edit, upload, expand, or dismiss.
- Default corner radii are 4px for document objects, 6px for controls, and 10px for temporary sheets/dialogs.
- Pills are prohibited except for unavoidable binary status indicators where the label is under 12 characters.
- Use 1px borders for inputs and discrete document objects; use 2–3px boundaries for selected or error states.
- Do not place hairline dividers between every row or paragraph.
- Prefer background change, spacing, and alignment over borders.
- Shadows are reserved for temporary overlays. Use one restrained elevation: `0 12px 36px rgba(24, 34, 31, 0.16)`.

## 8. Button and input treatment

### Primary button

- Background: `action`.
- Text: white.
- Height: 48px desktop and mobile.
- Horizontal padding: 20px.
- Radius: 6px.
- Label: 16px / 600.
- No icon unless the icon adds information.
- One primary button per local action group.

### Secondary button

- Background: `surface`.
- Text: `ink`.
- Border: 1px `border-strong`.
- Same height and radius as the primary button.

### Quiet action

- No filled container at rest.
- Text: `ink-secondary`.
- Underline or background appears on focus/hover; do not convert it into a pill.

### Inputs

- Background: `surface`.
- Border: 1px `border`; 2px `border-strong` when active.
- Radius: 6px.
- Editable text: 17px minimum.
- Placeholder: `ink-muted`, written as an example rather than an instruction.
- Focus: 3px `focus` ring with 2px canvas offset.
- Errors appear beneath the field in 14px text and do not rely on border color alone.

## 9. Document representation

Documents are represented as **slabs**, not cards, rows, table records, pills, or a permanent rail.

### Document mode

- Each document is a substantial rectangular object with a 4px file edge, filename, explicit type, extraction facts, indexing state, and chunk count.
- Slabs may stack or overlap slightly to imply a corpus, but text must never overlap.
- A document uses one neutral surface. The file edge may encode PDF, DOCX, PPTX, or TXT, but file type must also be written.
- The whole Documents workspace accepts drag-and-drop. Do not place a generic centered upload card in the middle of an empty page.
- “Add documents” remains a clear 48px action in the workspace header.

### Indexed mode

- After indexing, the collection compresses into a concise corpus summary near the workspace title.
- The full document inventory opens on demand as a mode change, not as a persistent sidebar.
- Index state uses text plus a small solid progress edge. Avoid spinners inside every document.

## 10. Question composer treatment

The composer is a command surface, not a chat bubble.

- Place it in the primary workspace band above the active result.
- Use most of the available content width; do not center it inside a narrow column.
- Minimum height: 64px collapsed, expanding to a maximum of five lines.
- Question text: 18px / 450.
- Primary submit action is attached to the composer boundary but remains visually distinct.
- Show corpus scope in plain text: “Asking 3 indexed documents.”
- Example questions are text links beneath the composer, not pills or cards.
- Provider and advanced retrieval controls live under one “Retrieval settings” disclosure.
- Do not display chronological chat bubbles. Previous questions, if retained, appear as a compact activity list in a separate history mode.

## 11. Grounded answer treatment

The grounded answer is continuous prose with explicit claim structure.

- Answer body: `type-answer` at 21px / 1.58.
- Maximum prose measure: 78 characters, positioned within a wider working composition rather than centered with empty margins.
- Claims are semantic spans within the prose, not repeated cards.
- A selected claim receives a full-line `action-soft` background band and a 4px `action` start marker.
- Unselected claims remain visually quiet.
- Claim IDs are available to assistive technology and evidence controls; they do not dominate the reading surface.
- Preserve paragraph structure and lists from the generated answer where useful.
- Unsupported or weakly supported language is labeled directly beside the claim.
- Retrieval-only fallback must be identified as “Retrieved passages” rather than presented as model-generated prose.

## 12. Citation treatment

Citations are compact, square **evidence flags** embedded immediately after the supported statement.

- Minimum visible size: 28px; effective target: 44px.
- Radius: 3px, never pill-shaped.
- Default: `surface-muted` with `ink` text.
- Active: `evidence` with `ink` text and a 2px `ink` boundary.
- Label format: source letter plus passage number, such as `A·18`; do not use unexplained numeric superscripts alone.
- Citation focus selects the associated claim, opens the evidence stage, and focuses the passage heading.
- Multiple citations remain individually selectable.
- Color is reinforced by text, source filename, and focus state.

## 13. Evidence inspection treatment

Evidence opens in a temporary full-width **evidence stage**, not a permanent inspector column.

### Desktop

- The selected claim remains visible in a compact context band.
- The evidence stage occupies roughly 38–52% of the lower workspace, depending on passage length.
- The passage is the largest element: 19–20px with 1.6 line height.
- Filename, file type, chunk ID, and genuine page/slide data appear above the passage.
- Matching terms may receive `evidence-soft` background, but highlighting must not imply unsupported spans.
- Multiple supporting passages use a vertical sequence with one active passage; inactive passages show only source and first two lines.
- Closing the stage returns focus to the citation that opened it.

### Interaction

- Selecting another citation replaces the passage within the same stage.
- Arrow keys may move between citations in the selected claim when the citation group has focus.
- “Open document context” expands surrounding chunk text without changing the answer.
- Do not fabricate page, slide, or paragraph locations.

## 14. Retrieval and reranking disclosure treatment

Retrieval metadata is secondary but explicit.

Default disclosure line:

> Retrieved by semantic + BM25 fusion · reranked #1

Expanded disclosure shows:

- semantic score as a labeled numeric value;
- BM25 score as a labeled numeric value;
- hybrid score as a labeled numeric value;
- configured weights: semantic 0.65 / BM25 0.35;
- rerank position and whether a rerank score is available;
- retrieval-only or provider-fallback status when applicable.

Rules:

- Use readable labels and tabular numerals, not a dense score table.
- Do not place semantic, BM25, hybrid, or reranker values on a shared visual scale unless the backend contract explicitly guarantees that the displayed values are normalized and comparable.
- Prefer labeled numeric values. A score track is allowed only for an individual value whose normalized range is guaranteed by the backend contract; it must name that range and must not imply comparability with another retrieval stage.
- Never show a score without naming its stage.
- Do not imply that scores from different model families are directly comparable unless the backend contract guarantees it.
- The known equal-score normalization behavior may be described in technical help, but the UI must not silently reinterpret it.
- Advanced settings remain collapsed and must not interrupt the default ask flow.

## 15. Loading, indexing, and error states

### Empty corpus

- Use the full Documents workspace as the drop target.
- Heading: “Add documents to build a corpus.”
- Show supported formats and privacy/persistence behavior in plain language.
- Keep “Add documents” prominent; avoid illustrations, giant hero copy, and a centered upload card.

### Upload and extraction

- A new slab appears immediately with filename and file type.
- Status sequence: Uploading → Extracting → Chunking → Indexing → Indexed.
- Show determinate progress only when a real value exists.
- Partial extraction warnings remain attached to the affected document.

### Query loading

- Keep the submitted question visible.
- For the current FastAPI contract, show one truthful generic state: **“Grounding answer…”**
- Do not present Retrieving → Fusing → Reranking → Generating as confirmed live progress because the backend does not expose stage events.
- Detailed stage progress may be added later only when the backend exposes real, ordered progress events and the interface renders those events without inference.
- Use one restrained indeterminate marker, not multiple spinners or skeleton cards.
- Preserve the previous answer until the new result is ready unless the corpus changes.

### Errors

- Place the error at the failed object or stage.
- Use a 3px `error` edge, error icon, plain-language title, and recovery action.
- Preserve successfully indexed documents when one document fails.
- Missing provider keys explain that retrieval-only fallback is being used when that is the actual behavior.
- Never expose raw stack traces, secrets, or provider payloads in the default interface.

## 16. Motion principles

Motion explains state change; it never supplies personality by itself.

| Token | Duration | Use |
|---|---:|---|
| `motion-fast` | 120ms | Press, focus, small state change |
| `motion-standard` | 200ms | Disclosure, document compression |
| `motion-stage` | 280ms | Evidence stage opening or replacing content |

Rules:

- Evidence opens upward from its citation context using opacity plus short translation.
- Selecting a citation gives the source passage one non-looping 500ms emphasis wash.
- Index progress moves linearly and never restarts cosmetically.
- Do not use parallax, floating decoration, looping pulses, sparkle effects, or ambient gradient motion.
- `prefers-reduced-motion` removes translation and uses immediate state changes or short opacity transitions under 100ms.

## 17. Responsive rules

### Wide desktop: 1440px and above

- Workspace uses the full canvas up to 1600px with 48px gutters.
- Documents, answer, and evidence use mode-specific compositions rather than fixed columns.
- Evidence stage may show passage and metadata side by side, with the passage receiving at least 65% of the width.

### Desktop/laptop: 1024–1439px

- Gutters reduce to 32px.
- Answer context moves above the evidence passage if horizontal space becomes tight.
- Document slabs reduce overlap before reducing text size.

### Tablet: 768–1023px

- Modes become vertically sequenced.
- Document slabs use a two-column arrangement only when filenames remain readable; otherwise use one column.
- Evidence stage occupies the lower portion of the screen and may expand to full height.
- Retrieval score tracks remain horizontal and full width.

### Mobile: below 768px

- Use one full-width mode at a time: Documents, Ask/Answer, or Evidence.
- Workspace gutters are 16px.
- Evidence becomes a full-screen sheet with a clear close action and source heading.
- The question composer stays at the top of the Ask mode; do not imitate a messaging app’s sticky chat composer.
- Answer remains at least 18px with 1.55 line height.
- Citation effective targets remain 44px without forcing giant visible badges.
- Never shrink the desktop layout to fit. Reorder, stack, or change modes.

## 18. Accessibility rules

- Meet WCAG 2.2 AA contrast: 4.5:1 for body text, 3:1 for large text and essential graphical controls.
- Maintain a minimum 44×44px effective target for primary controls, citations, document actions, and disclosure triggers.
- Use a visible 3px `focus` ring with 2px offset on every keyboard-focusable element.
- Preserve native tab order and semantic controls.
- Document statuses use text and icons in addition to color.
- Retrieval signals use labels and numeric values in addition to color.
- Announce upload completion, indexing completion, query completion, and errors through appropriate polite live regions; errors requiring action use alerts.
- Do not announce progress on every animation frame.
- Evidence focus must move to the passage heading when opened and return to the initiating citation when closed.
- Support 200% text zoom without clipping, overlap, or loss of essential functionality.
- Respect reduced motion, high-contrast modes, keyboard-only navigation, touch input, and screen readers.
- Never truncate a filename without making the full value available on focus and to assistive technology.
- Avoid relying on hover for essential evidence or score information.

## 19. Explicit anti-patterns

Do not use:

- dashboards, KPI blocks, analytics-card grids, or equal-width status panels;
- a permanent sidebar as the default workspace structure;
- Library | Ask | Evidence as a fixed three-column shell;
- generic chatbot bubbles, assistant avatars, typing dots, or message timestamps;
- terminal styling, green-on-black text, command prompts, or monospace as brand identity;
- beige, cream, parchment, or newspaper/editorial canvas treatments;
- navy-led AI palettes or blue as the general interaction accent;
- black/gold luxury styling;
- glassmorphism, translucent floating panels, backdrop blur, or frosted controls;
- decorative gradients, auroras, sparkles, glowing nodes, or cyberpunk motifs;
- excessive rounded cards, pill buttons, pill tabs, or badge collections;
- a generic centered upload box;
- narrow centered answer columns surrounded by unused desktop margins;
- thin rules between every item;
- source registers or spreadsheet-like document tables as the primary view;
- permanent claim cards or an always-visible evidence inspector;
- giant landing-page hero typography inside the application;
- poster/brutalist experiments that reduce product clarity;
- decorative illustrations that compete with document content;
- fabricated confidence, page numbers, slide numbers, scores, or source locations.

## 20. Rules preventing visual reuse from previous projects

These rules are mandatory acceptance criteria, not aspirations.

1. **New token namespace:** implementation must use this document’s color, spacing, type, radius, and motion tokens. Existing frontend tokens may not be aliased, renamed, or carried forward.
2. **New typography:** do not reuse Commissioner, previous project font stacks, or any reference brand’s licensed/proprietary family. Prefer locally bundled Mona Sans Variable; if reliable bundling is unavailable, use the documented system fallback with no runtime font download.
3. **New composition:** do not reuse the current source rail, narrow answer column, stitched-rule geometry, claim blocks, inline inspector, or three-region workspace.
4. **New component anatomy:** document slabs, evidence flags, and the evidence stage must be implemented from their product behavior—not by restyling existing cards, pills, tables, or panels.
5. **New interaction grammar:** mode changes, document compression, citation focus, and evidence-stage opening define this product. Do not reuse previous navigation, drawer, modal, hover, or animation patterns without a documented accessibility reason.
6. **Functional color audit:** every non-neutral color must map to action, semantic retrieval, BM25, fusion, evidence, or semantic state. Decorative color inheritance from references or prior projects is prohibited.
7. **Reference rejection:** do not introduce Clay’s claymation or multicolor feature-card rhythm, Airtable’s editorial marketing bands or black pill CTA system, or Replicate’s cream/orange/code-well identity.
8. **No visual compatibility layer:** do not retain old CSS classes, old design tokens, or old component wrappers merely to make migration easier. Preserve data and behavior contracts only.
9. **100% zoom review:** the primary desktop viewport must show documents/corpus context, a usable composer, and meaningful answer content without tiny text or large unused margins.
10. **Originality review before acceptance:** reject any implementation that can be described as “the previous UI with new colors.” Structure, typography, spacing, controls, surfaces, document representation, answer treatment, and evidence behavior must all visibly follow this specification.
