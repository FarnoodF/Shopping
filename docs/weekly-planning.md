# Weekly quantities

`config/week.template.json` is a blank structure, not a suggested personal plan. Each private plan covers one to seven consecutive days, as requested by the user. `people` is the portion count per meal and `meal_slots` lists the slots to shop for, such as `["dinner"]`. Represent special smaller portions by adjusting the agreed portion model, not by silently leaving people unfed. Days outside the requested period are simply out of scope.

List `meal_slots` in chronological order. Optional `start_meal_slot` and `end_meal_slot` bound the first and last calendar dates; omitted boundaries include all slots. `days` counts calendar dates touched, so a rolling five-day interval beginning at dinner can touch six dates and end at lunch. Include only the meals inside that window. A batch can specify `available_from_slot` on its preparation date to prevent allocating a lunch to food first cooked for dinner. Follow the private profile's planning anchor, including first-cooking-batch preferences, instead of automatically inserting meals before cooking starts.

Each recipe has an `id`, `yield_servings`, and `ingredients`. An ingredient has a stable `key`, display `name`, numeric `quantity`, and `unit` (`g`, `kg`, `ml`, `l`, or `each`). Use distinct keys for raw/cooked, dry/canned, and incompatible products. No mass/volume or cups conversion is guessed.

Each batch has an `id`, `recipe_id`, `prepare_on` date, and total `servings`. Preparation can precede the first requested day, but cannot follow a consuming meal or the end of the planning period. Review storage separately; accepting a date is not a shelf-life check. Ingredients scale from recipe yield to batch servings. Each scheduled meal has `date`, `slot`, `batch_id`, and `servings`, or `away: true`. A meal consumes a batch without creating another shopping requirement. Combine main and side dishes in the recipe's ingredient list, or model them as one composed recipe.

`pantry` entries use the ingredient shape plus `confirmed: true`; amounts mean usable stock available for this specific plan. `extras` use the same ingredient shape for snacks, drinks, or household groceries. Stock is subtracted once from the combined requirements, never separately for every recipe. Unallocated batch servings are surfaced for freezer/leftover planning.

The compiler verifies arithmetic and coverage, not nutritional adequacy, cooking safety, allergens, prices, or shelf life. The agent reviews those against the profile and actual product labels. It rejects incomplete plans rather than claiming enough meals exist.

```sh
.venv/bin/python -I scripts/shop.py new-week YYYY-MM-DD
# Optional: add --days N to override the private profile's coverage length.
# Populate .profile/weeks/YYYY-MM-DD/plan.json from the conversation.
.venv/bin/python -I scripts/shop.py list YYYY-MM-DD
```

Choose products for `to_buy` quantities, rounding net needs up to actual package sizes. Keep expected surplus explicit. Set `user_choices_recorded` only after recording the user's selected dishes or their instruction to choose for them.
