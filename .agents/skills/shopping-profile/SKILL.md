---
name: shopping-profile
description: Interview the user about food tastes, eating patterns, cooking constraints, and grocery habits, saving their answers privately in this Shopping project.
---

Read `../../../docs/preferences-interview.md` and existing `.profile/preferences.json` from the repository root. Run `scripts/shop.py init` if needed. `null` means unknown; an empty list means the user explicitly reported none. Do not infer allergies, restrictions, household size, budget, or long-term preferences from product suggestions or a one-off meal request.

Interview in small rounds, usually three questions per round. Start with household, meal coverage, and allergies/restrictions. Then explore taste and routine, followed by shopping habits. Reuse answers already provided; continue without asking the user to approve saving each answer. Their request to establish this profile authorizes saving it locally.

After each answer, update `.profile/preferences.json` atomically, record the date and any unanswered fields, and update `.profile/workflow.json`. Save ambiguous facts as notes/questions rather than confirmed preferences. Do not require health measurements or medical goals for ordinary meal planning.

Summarize the resulting preferences briefly so the user can correct them. Once sufficient, move directly into `plan-week`: ask what meals they want for the specific week, using their saved preferences to fill gaps when invited. Do not populate a basket with guessed meals while this interview is still pending.
