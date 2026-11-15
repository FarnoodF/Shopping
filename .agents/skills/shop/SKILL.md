---
name: shop
description: Fill, update, or show a grocery cart at a supported store. Present the verified cart using generate-cart-pdf alongside an itemized table.
---

## Choose the store

Use the retailer named in the request. Otherwise use the retailer for the current shop or the saved `shopping.retailer` preference. If the choice is still unclear, ask which retailer to use. If the chosen retailer is unsupported, explain which stores are available and leave the store choice to the shopper.

Read the selected store’s reference before connecting. Each reference describes its tools, account-cart setup, quantity semantics, verification and fallback.

- [Provigo](references/provigo.md)

To add a supported retailer, document its working integration in `references/<retailer>.md` and link it here.

## Prepare and verify the basket

For a request to show or review an existing cart, read the full signed-in cart using the store reference and go directly to **Present the cart**. Keep this operation read-only, including when the store reports no open cart.

Load the private preferences, weekly plan and shopping list. Verify the intended store and fulfillment method. Read and save the starting account cart before updating it. Preserve unrelated items and count existing matching quantities toward the target.

For each net ingredient need, search, compare unit prices and usable package sizes, check stock and mandatory dietary constraints, and choose products within the user's brand, budget, and substitution rules. Check product labels for allergies; never infer suitability from a search title alone. Round up to whole packs only after subtracting pantry stock. Track the recipe requirement separately from the retailer quantity, especially for variable-weight produce/meat.

Follow the store reference to reach the intended quantities. After a timeout or ambiguous write, inspect the current cart before retrying. After the last change, read the entire signed-in basket again. Reconcile every requested ingredient, including sauces, herbs and garnishes, with the actual products, quantities and subtotal. Leave checkout to the user unless separately requested.

Record `.profile/weeks/YYYY-MM-DD/basket.json` with product codes/URLs, retailer-reported brands, pack sizes, planned amounts, before/after quantities, observed prices, substitutions, unavailable items, and estimated fees. Stay within the agreed budget; resolve substantial cost overruns or substitutions with the user. Stock and estimates can change before fulfillment.

## Present the cart

Every time you present a cart, run [generate-cart-pdf](../generate-cart-pdf/SKILL.md) using the latest verified cart readback. This applies to read-only views and to the result of every creation, update or correction. Deliver the generated PDF, inline itemized table and cart review link together. If generation fails, report the specific failure and identify the PDF as pending.

Use the same readback for the **Item | Brand | Amount in cart | Line price (currency)** table. Show package size and pack count or the number of individual items. Mark variable weights and prices as estimates. Use **Not listed** for a missing brand. For corrections, identify this turn’s changes and show the complete current basket, distinguishing unrelated pre-existing items. Include the subtotal, known fees and taxes, total or estimated total, pending charges, meal coverage and gaps. When computer use changes the basket, save a screenshot under `.profile/` and embed it alongside the table.
