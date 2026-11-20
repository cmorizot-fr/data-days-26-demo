# Hexagone — Design System (`DESIGN.md`)

> Stitch-ready visual & component specification for **Hexagone** (Banque Hexagone) — modern French neo-bank mobile experience powered by Google's Agentic Data Cloud (AlloyDB + BigQuery TimesFM + ADK).

## 1. Visual Identity & Brand Atmosphere
- **Brand Name**: **Hexagone** (institutional full name: *Banque Hexagone*, compact mark: `HX` inside an open-faceted geometric hexagon).
- **Personality**: Sharp, transparent, modern fintech (Revolut-grade clarity & speed, zero visual clutter, French banking trust).
- **Signature Visual Motif**: *Scattered fragments → One clean hexagon* — representing 12 legacy banking silos converging into one clear, real-time personal finance experience.
- **Two UI States for Keynote Contrast (Light Stage Edition)**:
  - **Shared Light Shell (Projector-First)**: Both Before and After use the **exact same clean Light Paper (`#FAFAFA`) shell**, crisp `#FFFFFF` cards (`1px solid #E5E7EB`), `#11131A` Ink typography, identical header (`Hexagone` + `LM`), identical hero balance (`6 892,00 €` + `Virement` / `RIB`), and identical `Dernières opérations` list — maximizing projector readability and making the Swarm diff unmistakable.
  - **"Before" (Starter App)**: Just the clean light Hexagone shell (balance + `Dernières opérations`, zero AI/forecast/offers).
  - **"After" (Upgraded Agentic App)**: The exact same light shell with ONLY the 3 crisp new features slotted cleanly between the balance and the transaction list: (1) **Budget Insight** card (*Depuis votre dernière connexion*), (2) **Conseil Épargne** card (`ACPR 2024-R-01` + 1-click CTA), and (3) floating **Coach IA** pill.

## 2. Color Palette & Semantic Tokens

| Token | Hex (Light) | Hex (Dark) | Usage |
| :--- | :--- | :--- | :--- |
| `Ink` (Primary Text / Dark Surface) | `#11131A` | `#FAFAFA` | Primary headlines, balances, dark action buttons |
| `Paper` (Light Canvas) | `#FAFAFA` | `#161822` | App background, light cards |
| `Night` (Dark Canvas) | `#0A0B0F` | `#0A0B0F` | Keynote dark-mode app shell, hero balance card |
| `Indigo` (Primary Brand Accent) | `#4F46E5` | `#818CF8` | Budget Insight agent, primary interactive focus, forecast curve |
| `Coral` (Secondary Brand Accent) | `#FF6B4A` | `#FF876C` | Conseil Offres agent, proactive highlights, call-to-action accents |
| `Signature` (Brand Gradient) | `linear-gradient(110deg, #4F46E5 0%, #8B5CF6 48%, #FF6B4A 100%)` | Same | Wordmark accent, AI coach orb/badge, hero insight card border |
| `Savings / Positive` | `#10B981` | `#34D399` | Projected surplus (`+300,00 €`), CPAM refund (`+42,00 €`), ACPR compliance badge |
| `Alert / Hike` | `#EF4444` | `#F87171` | Subscription price hike (`STRMFLIX DIGITAL +4,00 €`) |
| `Muted` | `#6B7280` | `#9CA3AF` | Secondary labels, dates, subtitles |

## 3. Typography
- **Display & UI Sans**: `Inter` / `SF Pro Display` / geometric sans-serif.
  - Hero Balance: `36px–40px`, `font-weight: 800`, `letter-spacing: -0.04em`, `font-variant-numeric: tabular-nums`.
  - Section Headings: `18px–20px`, `font-weight: 700`, `letter-spacing: -0.025em`.
  - Micro Labels (ALL CAPS): `11px`, `font-weight: 600`, `letter-spacing: 0.12em`.
- **Monospace**: `JetBrains Mono` / `SF Mono` for currency deltas, account IDs (`ACC00002026`), latency telemetry (`< 15 ms`), and ADK agent tags.

## 4. Layout, Geometry & Components
- **Mobile Viewport**: `390 × 844` (iPhone 15 Pro frame) centered on a dark keynote canvas (`#0A0B0F`) with optional live telemetry pill (`AlloyDB · 0.1 ms`) for stage presenters.
- **Border Radius**: Generous neo-bank geometry — `20px` for hero cards, `16px` for list/insight cards, `999px` (pill) for action buttons, agent chips, and status tags.
- **Elevation**: Crisp hairline borders (`1px solid rgba(17,19,26,0.08)` in light, `1px solid rgba(255,255,255,0.08)` in dark) rather than heavy drop shadows.
- **Core Agent Components**:
  1. **Budget Insight Card** (*"Depuis votre dernière connexion"*): Indigo accent indicator, 3 concise rows (STRMFLIX `+4,00 €`, CPAM `+42,00 €`, TimesFM surplus `+300,00 €`), plus conversational ADK chat drawer.
  2. **Conseil Offres Card** (*ACPR 2024-R-01*): Coral accent pill, `200,00 €` recommended transfer, `100 €` safety cushion indicator, choice between `Livret A (3,00 %)` and `Livret Boost Maison (3,50 % sur 3 mois)`.
  3. **Action 1-Clic Confirmation Sheet**: High-contrast bottom sheet showing source (`ACC00002026`), destination offer, amount (`200,00 €`), and explicit *"Confirmer le virement"* CTA writing directly to AlloyDB `savings_transfers`.
