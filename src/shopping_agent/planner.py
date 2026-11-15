"""Scale cooking batches, account for leftovers, and subtract confirmed pantry stock."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

UNITS = {"g": ("g", 1), "kg": ("g", 1000), "ml": ("ml", 1), "l": ("ml", 1000), "each": ("each", 1)}


def number(value, allow_zero=False):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Quantities must be numbers") from None
    if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
        raise ValueError("Quantities must be finite and positive")
    return result


def keyed(items, kind):
    result = {}
    for item in items:
        key = item["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", key) or key in result:
            raise ValueError(f"{kind} IDs must be unique lowercase slugs")
        result[key] = item
    return result


def compile_list(plan):
    start = date.fromisoformat(plan["start_date"])
    if type(plan["days"]) is not int or not 1 <= plan["days"] <= 7:
        raise ValueError("Plan between one and seven consecutive days")
    if type(plan["people"]) is not int or plan["people"] < 1:
        raise ValueError("Plan for a positive whole number of people")
    slots = plan["meal_slots"]
    if not slots or len(slots) != len(set(slots)):
        raise ValueError("Specify the distinct meal slots this shop should cover")
    first_slot = plan.get("start_meal_slot", slots[0])
    last_slot = plan.get("end_meal_slot", slots[-1])
    if first_slot not in slots or last_slot not in slots:
        raise ValueError("Meal window boundaries must be requested meal slots")
    first_index, last_index = slots.index(first_slot), slots.index(last_slot)
    recipes, batches = keyed(plan["recipes"], "Recipe"), keyed(plan["batches"], "Batch")
    days = [(start + timedelta(days=i)).isoformat() for i in range(plan["days"])]
    expected = {(day, slot) for day in days for i, slot in enumerate(slots)
                if not (day == days[0] and i < first_index)
                and not (day == days[-1] and i > last_index)}
    if not expected:
        raise ValueError("Meal window must contain at least one meal")
    for batch in batches.values():
        if batch.get("available_from_slot", slots[0]) not in slots:
            raise ValueError("Batch availability must use a requested meal slot")
    seen, allocated = set(), defaultdict(Decimal)
    for meal in plan["meals"]:
        slot = (meal["date"], meal["slot"])
        if slot not in expected or slot in seen:
            raise ValueError("Meals must cover each requested date/slot exactly once")
        seen.add(slot)
        if meal.get("away") is True:
            if meal.get("batch_id"):
                raise ValueError("An away meal cannot also consume a cooking batch")
            continue
        batch_id = meal["batch_id"]
        if batch_id not in batches:
            raise ValueError("Meal refers to an unknown batch")
        servings = number(meal["servings"])
        if servings < plan["people"]:
            raise ValueError("A meal has fewer servings than people; adjust the plan explicitly")
        allocated[batch_id] += servings
        if date.fromisoformat(batches[batch_id]["prepare_on"]) > date.fromisoformat(meal["date"]):
            raise ValueError("A batch cannot be eaten before it is prepared")
        batch = batches[batch_id]
        if (batch["prepare_on"] == meal["date"] and
                slots.index(meal["slot"]) < slots.index(batch.get("available_from_slot", slots[0]))):
            raise ValueError("A batch cannot be eaten before its first available meal slot")
    missing = sorted(expected - seen)
    if missing:
        raise ValueError(f"Unplanned meals: {', '.join(' '.join(slot) for slot in missing)}")
    totals, pantry = defaultdict(Decimal), defaultdict(Decimal)
    metadata, dimensions = {}, {}

    def add(item, target, scale=Decimal(1), allow_zero=False):
        key = item["key"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", key):
            raise ValueError("Ingredient keys must be lowercase slugs")
        if item["unit"] not in UNITS:
            raise ValueError("Use g, kg, ml, l, or each; no implicit cup or density conversions")
        unit, multiplier = UNITS[item["unit"]]
        if key in dimensions and dimensions[key] != unit:
            raise ValueError(f"Incompatible units for {key}; do not guess density or package size")
        dimensions[key] = unit
        metadata.setdefault(key, {"name": item["name"], "unit": unit})
        target[key] += number(item["quantity"], allow_zero) * multiplier * scale

    leftover_servings = {}
    for batch_id, batch in batches.items():
        if date.fromisoformat(batch["prepare_on"]) > start + timedelta(days=plan["days"] - 1):
            raise ValueError("Prepare batches no later than the planning period ends")
        recipe = recipes[batch["recipe_id"]]
        servings = number(batch["servings"])
        if allocated[batch_id] > servings:
            raise ValueError(f"Not enough portions in batch {batch_id}")
        leftover_servings[batch_id] = float(servings - allocated[batch_id])
        scale = servings / number(recipe["yield_servings"])
        if not recipe["ingredients"]:
            raise ValueError("Recipes need an ingredient list")
        for ingredient in recipe["ingredients"]:
            add(ingredient, totals, scale)
    for item in plan["extras"]:
        add(item, totals)
    for item in plan["pantry"]:
        if item.get("confirmed") is not True:
            raise ValueError("Pantry stock must be confirmed for this shop before subtracting it")
        add(item, pantry, allow_zero=True)
    items = []
    for key in sorted(totals):
        needed = max(Decimal(0), totals[key] - pantry[key])
        items.append({"key": key, **metadata[key], "required": float(totals[key]),
                      "pantry_used": float(min(pantry[key], totals[key])), "to_buy": float(needed)})
    return {"start_date": start.isoformat(), "meal_slots_covered": len(seen),
            "items": items, "unallocated_batch_servings": leftover_servings,
            "package_rounding": "Select retailer pack sizes after compiling; round up only the net amount"}
