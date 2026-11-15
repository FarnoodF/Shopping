# Preference interview

The conversation should feel like learning a household's routine, not a long mandatory form. Ask about three related topics at a time; accept free-form answers and persist partial progress.

1. **Household and coverage:** how many people/portions, which breakfasts/lunches/dinners to cover, regular meals away from home. Ask explicitly about allergies and dietary restrictions, including none.
2. **Taste:** favorite everyday dishes and cuisines, disliked ingredients/textures, spice tolerance, preferred proteins and vegetables, usual breakfasts, snacks and drinks. Ask for a few real meals they enjoy instead of an exhaustive food inventory.
3. **Cooking rhythm:** weekday cooking time, cooking frequency, willingness to batch cook/eat leftovers, equipment, freezer/storage space, convenience-food preferences.
4. **Shopping:** preferred store and pickup/delivery, weekly budget and whether it includes fees, shopping day/frequency, brands worth paying extra for, organic/value preferences, acceptable substitutions, bulk buying and waste tolerance.

Some answers may already appear in the current chat or an observed store setting. Treat an observed setting as a suggestion to confirm, not a permanent preference. Never infer an allergy from an alternative milk purchase. Do not import unrelated health or account information merely because a connector is available.

When the user authorizes using a connected food diary, read its confirmed planning preferences and a recent representative window before asking the same questions. Follow pagination, distinguish entries from full meals, and inspect ingredient details for representative recurring dishes. Food history can reveal meal formats, recurring ingredients and repetition; it cannot reliably establish cooking time, equipment, budget, who prepared the meal, or the tastes of another household member. Do not request body measurements or energy expenditure for this purpose.

Save minimal food evidence with source dates and record IDs under `.profile/`. Keep recurring dishes and inferred habits separate from explicit favorites or confirmed constraints. Do not convert cooked logged portions into raw purchase weights without a recipe/yield basis. Ask only about consequential gaps, then move to weekly dish selection.

Store durable answers in `.profile/preferences.json`. Put this week's inventory, exceptions, and recipes in `.profile/weeks/<start-date>/`. Store minimal workflow state in `.profile/workflow.json`: current phase, completed steps, unanswered questions, active week, next action. Use `null` for unknowns, `[]` for confirmed none, and include `updated_at` when saving answers.

Once sufficient preferences are known, ask: “Which meals would you like to make for [explicit date range]? I can suggest the remaining meals based on your preferences. What food do you already have to use up?” Continue directly into weekly planning.
