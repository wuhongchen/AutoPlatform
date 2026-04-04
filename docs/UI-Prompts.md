# UI Prototype Prompts: Multi-Account WeChat Content Operating System

## 1. Design Direction

### Product Type
- Web application
- Admin dashboard
- Content operations system for multi-account WeChat publishing
- Conversational operations assistant embedded in OpenClaw-like runtime

### Target Users
- Individual content operators managing 1-3 public accounts
- Content teams and agencies managing multiple accounts
- OpenClaw automation users who need visible control, tracking, and repair

### Recommended Style
- Primary recommendation: Clean Professional + Editorial Dashboard
- Reason:
  - This is not a generic finance SaaS.
  - It needs both operational clarity and content-production atmosphere.
  - The UI should feel like a mix of a publishing desk, a workflow center, and a repair console.
  - The dialogue entry should feel like an operational copilot, not a casual consumer chatbot.

### Color System
- Primary: deep cobalt blue `#2457FF`
- Secondary: ink navy `#182848`
- Background: mist gray `#F4F7FB`
- Surface: pure white `#FFFFFF`
- Accent: warm amber `#FFB547`
- Success: fresh green `#18A66A`
- Danger: vivid red `#E34D59`
- Info highlight: pale blue `#EAF1FF`

### Typography and Mood
- Professional, polished, editorial, operational, high-clarity
- Strong hierarchy, bold section headers, compact data panels, soft rounded cards
- Prefer readable Chinese admin UI with distinct title bands and status chips

## 2. Global Style Prompt

Use this as the base prompt before each screen prompt:

```text
High-quality web admin dashboard and conversational operations workspace, 1920x1080, 16:9 aspect ratio, professional polished interface for a multi-account WeChat content operating system, clean professional editorial dashboard style, deep cobalt blue and ink navy color system, mist gray background, white cards, warm amber accents, refined typography, strong information hierarchy, rounded cards, subtle shadows, clear status chips, elegant data tables, modern Chinese SaaS back office, intuitive layout, user-friendly, seamless workflow, high readability, desktop-first with mobile adaptation hints, structured AI assistant panel instead of casual chat aesthetics
```

## 3. Visual Style Variants

### Version A: Classic Professional
- Keywords: clean professional, structured grid, card-based, operational clarity, light theme
- Use case: first version, safest to implement, suitable for business teams

### Version B: Editorial Control Center
- Keywords: editorial dashboard, magazine-inspired headers, stronger typography, content-first, visual storytelling
- Use case: better for a content product, more distinctive, stronger brand feeling

### Version C: Minimal Ops Console
- Keywords: minimalist, dense but elegant, fewer colors, strong status contrast, low-noise layout
- Use case: suitable for power users and frequent operators

### Version D: Conversational Copilot
- Keywords: structured AI copilot, command center, action confirmation, context cards, operational assistant
- Use case: suitable for OpenClaw-like dialogue entry, recent content querying, safe configuration edits

## 4. Core Screen Prompts

### 4.1 Home Dashboard / Main Overview

#### Version A
```text
Web application dashboard homepage for a multi-account WeChat content operating system, classic professional style, 1920x1080, clean professional editorial dashboard, top header with product name and current active account switcher, left navigation with Overview, Accounts, Inspiration Library, Rewrite Pipeline, Publish Logs, Trace Center, Settings, central hero summary area with four KPI cards showing total inspiration items, pending rewrite items, pending publish items, failed tasks, secondary section with account health summary, scheduler status panel, recent task timeline, recent pipeline records table, right-side alert panel for broken links and failed publish warnings, deep cobalt blue primary buttons, pale blue summary blocks, green success chips, red failure chips, warm amber warning chips, refined typography, rounded white cards, subtle shadows, intuitive professional layout
```

#### Version B
```text
Editorial control center homepage for a WeChat content operations platform, 1920x1080, premium editorial dashboard style, bold Chinese title band, layered white and pale-blue cards, strong typography, active account shown as a branded identity block, top metrics as magazine-like stat panels, center workflow river showing stages from inspiration to publish, visual task heatmap, recent failed items highlighted in amber-red side rail, content-first dashboard blending operational data and publishing mood, sophisticated elegant interface, cobalt blue and ink navy with warm amber accents, high-quality polished web app
```

#### Version C
```text
Minimal ops console homepage for a multi-account publishing admin, 1920x1080, minimalist professional dashboard, reduced visual noise, thin top bar with account selector and run controls, compact metric cards, dense but clean tables, status chips with strong contrast, focus on scanability and operational speed, monochrome base with cobalt blue highlights and controlled green-red alerts, smooth spacing, elegant data dashboard, polished enterprise tool interface
```

### 4.2 Account Settings / Local Database Management

#### Version A
```text
Account settings page for a multi-account WeChat content system, web admin settings interface, 1920x1080, clean professional style, split layout with left account list and right account detail form, account list cards showing account name, account id, enabled status, last run time, right form grouped into sections: basic info, WeChat credentials, Feishu credentials, business tables, pipeline defaults, content direction prompts, readonly metadata fields for created time and updated time, clear labels and helper text below complex fields, FEISHU_APP_TOKEN explained as bitable app token, OPENCLAW prompt fields explained as content direction and WeChat writing direction, top actions for create account, duplicate account, enable, disable, archive, elegant form design, rounded inputs, subtle shadows, blue primary action buttons
```

#### Version B
```text
Premium editorial admin settings page for managing public account profiles, 1920x1080, editorial dashboard style, left account identity rail with avatar-like account blocks, right side layered configuration workspace, strong section headers with colored dividers, account form modules displayed as curated setup panels, one panel for WeChat publish identity, one for Feishu workspace binding, one for AI model and prompt direction, one for lifecycle metadata, elegant Chinese product UI, polished and content-industry oriented, refined typography, pale blue and warm amber accents
```

#### Version C
```text
Minimal admin configuration page for local account database management, 1920x1080, minimalist operations console, left narrow account index, right dense structured form, compact labels, helper tooltips, strong visual grouping using borders and spacing instead of heavy color, highly readable form layout, professional enterprise tool, cobalt blue focus states, low-noise interface optimized for fast repeated editing
```

### 4.3 Inspiration Library / Capture and Analysis Board

#### Version A
```text
Inspiration library management page for a WeChat content platform, 1920x1080, clean professional dashboard, top filter bar with active account, source type, processing status, score range, date range, central content table with columns for title, source url, score, recommendation reason, rewrite direction, original document, status, account, created time, row click opens right-side detail drawer with article summary, key insight, images preview, original document link, sync to pipeline action, table and cards combined layout, high readability, blue filters, pale-blue selected rows, green and amber score markers
```

#### Version B
```text
Editorial inspiration desk interface, 1920x1080, content-first management UI, large top heading, left filter rail, main area with article cards and hybrid table layout, each record shows headline, source snapshot, AI score badge, reason snippet, suggested rewrite angle, document linkage, a right-side article intelligence panel showing key insight, domain tag, original images, sync recommendation, elegant editorial dashboard with publishing newsroom atmosphere, refined typography, subtle card shadows, cobalt blue with amber highlights
```

#### Version C
```text
Minimal inspiration queue page, 1920x1080, minimalist data-centric dashboard, compact sortable table, slim header controls, strong emphasis on scanability, score heat column, quick action buttons for analyze, skip, sync, open original doc, low-noise enterprise interface, monochrome base with blue active states and green-red status chips
```

### 4.4 Rewrite Pipeline / State Machine Board

#### Version A
```text
Rewrite pipeline page for multi-stage WeChat publishing workflow, 1920x1080, professional workflow dashboard, main layout as a safe split view with left internal-scroll kanban board and right fixed detail rail, exact status lanes in order pending rewrite, rewriting, pending review, pending publish, publishing, published, rewrite failed, publish failed, each lane header includes status icon, status name, item count, one-line node description, each task card designed as an article job ticket with strong headline hierarchy, account chip, model chip, role chip, document action button, review or publish hint, failure reason block, last updated time, top toolbar with batch run button, single article action, active account selector, current model and role filter, right panel shows selected task status, chain id, inspiration source, original link, rewritten doc link, quick actions retry rewrite retry publish open doc mark reviewed, clean professional Chinese SaaS design, strong icon system, no overlapping layout, high readability, rounded workflow cards, polished web interface
```

#### Version B
```text
Publishing workflow control board with editorial operations feel, 1920x1080, sophisticated content operations dashboard, visual production chain from inspiration to publish, large lane headers with expressive icons for magnet, pen, review sheet, rocket, publish arrow, success badge, failure alert, cards designed like newsroom article tickets, strong Chinese headline typography, model and role displayed as colored chips, document entry and next-step action displayed as compact buttons instead of text links, review-ready and publish-ready stages highlighted with blue and amber emphasis, failure stages presented as diagnostic amber-red repair zones, right-side inspection panel shows chain relationship between inspiration record, pipeline record, rewritten document and publish action, modern Chinese SaaS style with stronger typography, more iconography, elegant but highly operational
```

#### Version C
```text
Minimal workflow board for content rewrite pipeline, 1920x1080, compact kanban plus detail hybrid, no visual overlap, fixed-width dense status lanes with internal scrolling only, strong status contrast, each lane header includes icon and count, each card keeps only essential information title account model role action state last update, right detail panel for selected task with quick actions retry open doc mark reviewed publish, low-noise ops console, high readability, execution-first enterprise interface with concise icon system
```

### 4.5 Failure Trace Center / Repair Console

#### Version A
```text
Failure diagnostics page for a WeChat content operations system, 1920x1080, professional troubleshooting dashboard, top summary cards for rewrite failures, publish failures, broken document links, missing field issues, central table with columns task id, account, stage, failure reason, related inspiration record, related pipeline record, rewritten doc link, last retry time, right-side trace timeline panel connecting inspiration record to pipeline record to publish log, action buttons for repair link, rebuild trace, retry rewrite, retry publish, clear red and amber highlighting, high-quality polished support console
```

#### Version B
```text
Trace center interface with dark editorial diagnostics mood, 1920x1080, high-contrast operations UI, left failure queue, center chain-of-events diagram, right repair action panel, visual relationship map between original article, Feishu doc, rewrite doc, publish log, timeline-based debugging experience, refined typography, ink navy background with cobalt blue and amber-red nodes, premium technical dashboard
```

#### Version C
```text
Minimal repair console for failed content jobs, 1920x1080, compact enterprise support tool, structured list view with expandable rows, each row shows exact failure stage and recommended repair action, trace links displayed as compact chips, strong red and amber semantics, low-noise layout focused on fast diagnosis and retry
```

### 4.6 Publish Review Detail / Mobile Reading Preview

#### Version A
```text
Publish review detail page for WeChat article approval, 1920x1080, clean editorial review interface, left side document metadata and action controls, center article preview panel showing title, author, intro block, H2 section styling, image placements, ad block insertion preview, right side checklist for title quality, paragraph readability, mobile adaptation, publish readiness, account identity shown clearly, polished professional UI, designed for final human review before publish
```

#### Version B
```text
Editorial proofreading screen for WeChat publishing, 1920x1080, high-end content review layout, full-height article preview styled like a mobile article embedded in desktop review workspace, surrounding panels for metadata, prompt direction, publish target account, failure risks, strong typography hierarchy, elegant newsroom atmosphere
```

#### Version C
```text
Minimal publish approval page, 1920x1080, simple split-screen review interface, mobile article preview on one side, metadata and action checklist on the other, low-noise professional layout, high readability, optimized for quick yes-no review decisions
```

### 4.7 Conversational Operations Assistant / OpenClaw Dialogue Workspace

#### Version A
```text
Conversational operations assistant workspace for a multi-account WeChat content operating system, 1920x1080, clean professional editorial dashboard style, layout split into left recent context rail, center structured dialogue timeline, right action and confirmation panel, top shows active account selector and current assistant mode, center conversation is not casual chat bubbles but structured message blocks with account summary, recent inspiration cards, recent pipeline cards, recent publish records, failed task summaries, inline action chips such as sync to pipeline, retry rewrite, retry publish, open original, open rewritten doc, edit model, edit prompt direction, right panel shows diff preview for configuration changes with before and after values and confirm button, assistant responses formatted as cards with sections account, time range, content summary, recommended next actions, polished Chinese SaaS copilot, cobalt blue primary, amber warning confirmation, green success chips, strong operational clarity
```

#### Version B
```text
OpenClaw-like AI operations copilot console for WeChat publishing system, 1920x1080, premium command center style, deep navy assistant header band, left rail for recent topics and failed jobs, central structured conversational canvas with cards for current account profile, recent inspiration snapshots, rewrite queue summary, publish logs and failure recommendations, right side secure action drawer with confirmation state, change diff, risk level tag, executable fixed actions, interface should feel like an operations robot helping manage system parameters and recent content, not a generic consumer chatbot, rich icon system for account, document, model, publish, failure, repair, sophisticated professional Chinese interface
```

#### Version C
```text
Minimal operations copilot screen for content system, 1920x1080, minimalist enterprise assistant UI, thin top toolbar with active account and mode, central structured conversation stream, each answer rendered as compact data cards and action chips, side panel for task confirmation and execution logs, low-noise design, strong text hierarchy, blue and gray neutral palette with amber warnings, optimized for fast parameter edits and recent content querying
```

### 4.8 Configuration Change Confirmation / Safe Action Preview

#### Version A
```text
Configuration change confirmation modal for a WeChat content operations assistant, 1920x1080 web application component view, professional Chinese SaaS design, central diff panel showing field name, previous value, next value, impacted account, risk level, affected workflow scope, footer actions confirm and cancel, helper notice explaining that publish and delete actions require explicit confirmation, elegant white modal card with cobalt blue confirm button and amber warning strip
```

#### Version B
```text
Secure action confirmation drawer for conversational admin copilot, 1920x1080, right-side slide-over panel with change summary, affected records, account scope, recent content target card, before-after comparison table, red warning for destructive operations, blue primary action for confirm execution, refined enterprise interface with clean shadows and strong hierarchy
```

#### Version C
```text
Minimal diff preview dialog for system parameter edits, 1920x1080 enterprise UI component, compact structured confirmation layout, clear before-after values, scope tag, risk tag, no visual clutter, highly readable and implementation-friendly
```

## 5. Key User Flow Prompts

### 5.1 New Account Setup Flow
```text
Multi-step setup flow for creating a new WeChat publishing account in a web admin system, 1920x1080, clean professional style, steps include account basic info, WeChat credentials, Feishu workspace binding, pipeline defaults, prompt directions, confirmation page, progress indicator at top, helper text for confusing fields like FEISHU_APP_TOKEN and prompt direction differences, polished modern form wizard, cobalt blue active step, white cards, intuitive and user-friendly
```

### 5.2 From Inspiration to Publish Flow
```text
End-to-end workflow screen sequence for a content operations system, showing inspiration record analysis, sync to pipeline, rewrite progress, review ready state, publish ready state, and final publish log, visual continuity across screens, same design system, strong stage identity, editorial dashboard feeling, professional polished UI, suitable for prototype storytelling and product walkthrough
```

### 5.3 Failure Repair Flow
```text
User flow for diagnosing and repairing failed content jobs in an admin dashboard, 1920x1080, professional support console, user selects failed record, views trace chain between inspiration library and pipeline and publish log, sees exact failure cause, suggested repair action, retries task, receives repaired status confirmation, clear step-by-step UI, red and amber alerts, polished repair experience
```

### 5.4 Conversational Query and Action Flow
```text
End-to-end conversational workflow for an OpenClaw-like operations assistant in a WeChat content system, 1920x1080, structured AI copilot interface, user asks for recent inspiration and failed publish jobs, system returns account-aware summary cards, user selects one recent record, system shows original link, rewritten document, failure reason, and recommended next actions, user requests model or prompt direction update, system shows before-after diff preview, user confirms change, system executes and returns structured success result, polished professional Chinese SaaS assistant, strong operational clarity, not casual chat style
```

### 5.5 Recent Content Quick Action Flow
```text
Interaction flow for recent content quick actions in a publishing operations assistant, 1920x1080 web app storyboard, user asks for latest 3 inspiration records, UI presents compact content cards with title, status, account, last updated time, original document, rewritten document, quick action chips, selecting one card opens action panel with sync to pipeline, retry rewrite, retry publish, mark skip, open doc, highly structured operational design, cobalt blue and amber action emphasis
```

## 6. Screen Priority Mapping

High priority screens:
1. Home Dashboard / Main Overview
2. Account Settings / Local Database Management
3. Inspiration Library
4. Rewrite Pipeline / State Machine Board
5. Publish Review Detail
6. Failure Trace Center
7. Conversational Operations Assistant / OpenClaw Dialogue Workspace
8. Configuration Change Confirmation / Safe Action Preview

Medium priority screens:
1. Publish Logs List
2. Scheduler and system settings
3. Account archive / soft delete view
4. Recent content quick action panel

## 7. Notes for Image Generation Tools

1. If using Gemini or Midjourney, generate Version A first for product alignment.
2. Use Version B when you want a more differentiated “content operations platform” feeling.
3. Use Version C when the design goal is implementation efficiency and low noise.
4. Keep Chinese labels visible in the mockups because the target operators are Chinese-speaking teams.
5. Do not generate purple-heavy consumer app aesthetics; this is a serious publishing operations product.
6. For conversational screens, avoid playful chatbot bubbles and emoji-heavy consumer AI styles; keep it structured, operational, and auditable.

## 8. Recommended First Batch

Generate these screens first:
1. Home Dashboard / Main Overview - Version A
2. Account Settings / Local Database Management - Version A
3. Inspiration Library - Version B
4. Rewrite Pipeline / State Machine Board - Version A
5. Failure Trace Center - Version A
6. Conversational Operations Assistant / OpenClaw Dialogue Workspace - Version A
7. Configuration Change Confirmation / Safe Action Preview - Version A

After visual confirmation, continue with:
1. Publish Review Detail - Version B
2. New Account Setup Flow
3. From Inspiration to Publish Flow
4. Conversational Query and Action Flow
