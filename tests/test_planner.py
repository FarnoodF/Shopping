from datetime import date, timedelta

import pytest
from shopping_agent.planner import compile_list


def plan():
    return {
        "start_date": "2030-01-07", "days": 7, "people": 2, "meal_slots": ["dinner"],
        "recipes": [{"id": "rice-dish", "yield_servings": 4, "ingredients": [
            {"key": "rice-dry", "name": "Dry rice", "quantity": 0.4, "unit": "kg"}]}],
        "batches": [{"id": "rice-batch", "recipe_id": "rice-dish", "prepare_on": "2030-01-07", "servings": 4}],
        "meals": [{"date": (date(2030, 1, 7) + timedelta(days=i)).isoformat(), "slot": "dinner",
                   **({"batch_id": "rice-batch", "servings": 2} if i < 2 else {"away": True})}
                  for i in range(7)],
        "pantry": [{"key": "rice-dry", "name": "Dry rice", "quantity": 100, "unit": "g", "confirmed": True}],
        "extras": [],
    }


def test_leftovers_not_double_counted_and_pantry_subtracted_once():
    result = compile_list(plan())
    assert result["items"][0] == {
        "key": "rice-dry", "name": "Dry rice", "unit": "g",
        "required": 400.0, "pantry_used": 100.0, "to_buy": 300.0,
    }
    assert result["meal_slots_covered"] == 7


def test_multiple_batches_scale_then_share_pantry():
    data = plan()
    data["batches"].append({**data["batches"][0], "id": "freezer-batch", "servings": 8})
    result = compile_list(data)
    assert result["items"][0]["to_buy"] == 1100
    assert result["unallocated_batch_servings"]["freezer-batch"] == 8


def test_advance_preparation_keeps_requested_meal_coverage_and_quantities():
    data = plan()
    data["batches"][0]["prepare_on"] = "2030-01-06"
    result = compile_list(data)
    assert result["meal_slots_covered"] == 7
    assert result["items"][0]["required"] == 400


def test_cannot_consume_batch_before_preparation():
    data = plan()
    data["batches"][0]["prepare_on"] = "2030-01-08"
    with pytest.raises(ValueError, match="before it is prepared"):
        compile_list(data)


def test_unused_batch_cannot_be_prepared_after_period():
    data = plan()
    data["batches"].append({**data["batches"][0], "id": "future", "prepare_on": "2030-01-14"})
    with pytest.raises(ValueError, match="planning period ends"):
        compile_list(data)


def test_rolling_window_can_start_at_dinner_and_end_at_lunch():
    data = plan()
    data.update(days=6, meal_slots=["lunch", "dinner"], start_meal_slot="dinner", end_meal_slot="lunch")
    data["batches"][0].update(servings=20, available_from_slot="dinner")
    data["meals"] = [
        {"date": (date(2030, 1, 7) + timedelta(days=d)).isoformat(), "slot": slot,
         "batch_id": "rice-batch", "servings": 2}
        for d in range(6) for slot in data["meal_slots"]
        if (d, slot) not in [(0, "lunch"), (5, "dinner")]
    ]
    result = compile_list(data)
    assert result["meal_slots_covered"] == 10
    assert result["items"][0]["required"] == 2000
    assert result["unallocated_batch_servings"]["rice-batch"] == 0
    data["meals"].append({"date": "2030-01-07", "slot": "lunch", "batch_id": "rice-batch", "servings": 2})
    with pytest.raises(ValueError, match="requested date/slot"):
        compile_list(data)


def test_same_day_lunch_cannot_use_evening_cooking_batch():
    data = plan()
    data["meal_slots"] = ["lunch", "dinner"]
    data["batches"][0]["available_from_slot"] = "dinner"
    data["meals"].insert(0, {"date": "2030-01-07", "slot": "lunch", "batch_id": "rice-batch", "servings": 2})
    with pytest.raises(ValueError, match="first available meal slot"):
        compile_list(data)


@pytest.mark.parametrize("boundary", ["start_meal_slot", "end_meal_slot"])
def test_unknown_meal_window_boundary_rejected(boundary):
    data = plan()
    data[boundary] = "snack"
    with pytest.raises(ValueError, match="boundaries"):
        compile_list(data)


def test_reversed_same_day_window_rejected():
    data = plan()
    data.update(days=1, meal_slots=["lunch", "dinner"], start_meal_slot="dinner", end_meal_slot="lunch")
    with pytest.raises(ValueError, match="at least one meal"):
        compile_list(data)


@pytest.mark.parametrize("days", range(1, 8))
def test_only_requested_days_need_coverage(days):
    data = plan()
    data["days"] = days
    data["meals"] = data["meals"][:days]
    result = compile_list(data)
    assert result["meal_slots_covered"] == days
    # Shortening the coverage period does not silently shrink a chosen cooking batch.
    assert result["items"][0]["required"] == 400


@pytest.mark.parametrize("days", [0, 8, 2.5, True])
def test_invalid_coverage_length_rejected(days):
    data = plan()
    data["days"] = days
    with pytest.raises(ValueError, match="one and seven"):
        compile_list(data)


@pytest.mark.parametrize("problem", ["missing_meal", "too_few_portions", "mixed_units", "unknown_pantry", "nan"])
def test_plan_rejects_quantity_and_coverage_errors(problem):
    data = plan()
    if problem == "missing_meal":
        data["meals"].pop()
    elif problem == "too_few_portions":
        data["batches"][0]["servings"] = 2
    elif problem == "mixed_units":
        data["pantry"][0]["unit"] = "ml"
    elif problem == "unknown_pantry":
        data["pantry"][0]["confirmed"] = False
    else:
        data["recipes"][0]["ingredients"][0]["quantity"] = "NaN"
    with pytest.raises(ValueError):
        compile_list(data)
