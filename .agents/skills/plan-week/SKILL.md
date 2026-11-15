---
name: plan-week
description: Ask what the user wants to eat this week, plan the requested days and meals, and calculate a private shopping list with portions, leftovers, and pantry stock.
---

Read `.profile/preferences.json` from the repository root and `../../../docs/weekly-planning.md` relative to this skill's directory. If allergies or dietary restrictions are unknown, finish that part of `shopping-profile` first.

Ask which meals or dishes the user wants this week, any meals away from home, and pantry/freezer food to use. Resolve the week to explicit dates in the user's timezone. Offer suggestions only for gaps; mark those suggestions as assumptions until the user selects them or delegates meal choice. The user's requested meals already authorize planning them; avoid a redundant approval gate.

Respect the private profile's planning anchor. When coverage starts with a cooking batch, begin at that batch's first available meal, without inventing an earlier meal. For rolling coverage, use `start_meal_slot`/`end_meal_slot` and the number of calendar dates touched; set same-day batch `available_from_slot` as needed. State the resulting end date so the coverage remains clear.

Create `.profile/weeks/YYYY-MM-DD/plan.json` with `scripts/shop.py new-week YYYY-MM-DD --days N` for one to seven consecutive days. Without `--days`, the private profile's coverage length is used, falling back to seven. Preserve an existing week's work. Record every requested meal slot, including away meals within the requested period; do not classify unrequested days as away meals. Model cooking batches separately from meal allocations so leftovers are counted once. Distinguish raw/cooked and dry/drained quantities, keep incompatible units separate, and subtract only pantry amounts confirmed for this shop.

Run `scripts/shop.py list YYYY-MM-DD`. Resolve coverage or quantity errors. Review the actual recipes for preferences and allergies; the arithmetic helper does not assess ingredient safety or nutrition. Ensure storage/reheating plans are realistic; if giving specific food-safety time limits, consult a current authoritative source.

Save the menu, recipe sources or estimated recipe assumptions, net ingredient needs, budget, and notes privately. Set `user_choices_recorded` once the user's choices/delegation are captured. Then proceed to [shop](../shop/SKILL.md) within the existing authorization to prepare a basket. Ask only about material missing choices or changes to the agreed plan.
