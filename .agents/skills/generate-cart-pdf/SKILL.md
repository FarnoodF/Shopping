---
name: generate-cart-pdf
description: Turn a verified grocery cart and meal plan into a shareable PDF with product photos, brand and package details, meal-by-meal costs, shared-item splits and a General section for household groceries.
---

# Generate a cart PDF by meal

Use the full account-cart readback that `shop` just verified. For a standalone request about the current cart, first save a fresh cart readback using the store’s reviewed tools. Use the basket record and meal plan when available. If there is no meal plan, put the verified groceries in **General**. When refreshing a previous layout, drop removed codes, update changed quantities and package labels, and assign additions or replacements to their meals. Take prices and totals from the same readback. Respect a superseding order when the shopper asks for the placed order. Keep the layout, readback, previews and PDF in the private week directory and write private JSON with `shopping_agent.private.write_json`. Exporting is read-only at the retailer.

## Assign the groceries

- Match each verified product code to its ingredient key(s), then to the recipes in the actual cooking batches. Scale recipe amounts by batch servings divided by recipe yield. Repeated leftover meals consume those batches only once.
- Give a purchase used for one dish to that dish, including the full package cost. Put snacks, household supplies and other unassigned purchases in **General**. Omit empty sections. Pantry ingredients carry no cart charge.
- For a shared item, allocate the purchased contents across the dishes using their planned proportions after pantry deductions. Where the plan explicitly reserves part of a purchase for general use, give that portion to General. Use a common physical unit, or exact fractions of a pack when its usable weight is unknown. Keep the purchase allocation distinct from a recipe's serving amount. Explain any material assumption in the PDF's optional note.
- Take photos from the verified product's retailer image or an exact local product photo. Keep product names, brands, quantities, currency, estimate markers and costs visible. Exclude account identifiers, address and payment details.

## Render

Prepare a private layout JSON beside the verified cart. It contains `period` (human-readable dates), `groups` (dish names in display order), optional `note`, and `items` (one object per verified product code, keyed by code).

Each item has `name`, `packs` (verified retailer quantity), and `amount` (short display text for the entire purchase, optionally two lines separated by a newline). Add `group` for a single use. For split use, supply `shares` mapping section names to positive amounts, `unit`, and `total_amount` for the entire purchase in that unit. Numeric strings can be exact fractions. Use `General` for unassigned groceries. Optional `photo` names an image in the private layout directory. The renderer takes brands, line prices, taxes and totals from the verified cart.

From the repo root, run the following with a Python interpreter that has Pillow and ReportLab. Both are available in the Codex workspace runtime.

```sh
python3 .agents/skills/generate-cart-pdf/scripts/render.py "$layout" "$cart_readback" "$output_pdf"
```

Pass the private layout, the verified retailer cart (raw or MCP envelope), and a private PDF output path. The renderer checks every product and pack count, divides line prices proportionally in integer cents, and reconciles section totals before writing. If the retailer has a separate cart-wide subtotal adjustment, verify it and include its signed CAD value in `subtotal_adjustment`. Inspect any unexplained mismatch before exporting.

For updates, render to the existing PDF path. The renderer keeps prepared product thumbnails under `.profile/cache/cart-pdf-photos/`, covered by the repository’s existing Git ignore rule. Unchanged photos are reused across shops. New products, changed retailer image URLs, changed local photo contents and damaged cache entries are refreshed automatically. Removed items disappear from the PDF. If the shopper requests fresh photos, append `--refresh-photos` to replace the current cart’s thumbnails even when their URLs are unchanged. Only a completed render replaces the PDF.

Preserve the forest-green masthead, pale-green table bands, white product photos, brand under the item name, and right-aligned prices. Render and inspect every PDF page at phone-readable size. Check the displayed section subtotals, any basket-level charges and the final total against the saved cart. Deliver the PDF in the chat.
