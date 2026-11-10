import pytest

from app.compatibility import evaluate
from app.models import Component


def part(category: str, **fields) -> Component:
    base = {"category": category, "brand": "Test", "model": f"{category}-model", "price_rub": 1000}
    return Component(**{**base, **fields})


@pytest.fixture
def base_set() -> list[tuple[Component, int]]:
    return [
        (part("cpu", model="CPU", socket="AM5", tdp_w=65, price_rub=20000), 1),
        (
            part(
                "motherboard",
                model="MB",
                socket="AM5",
                memory_type="DDR5",
                form_factor="ATX",
                price_rub=15000,
            ),
            1,
        ),
        (part("ram", model="RAM", memory_type="DDR5", capacity_gb=16, price_rub=5000), 2),
        (part("gpu", model="GPU", tdp_w=115, length_mm=260, price_rub=30000), 1),
        (part("psu", model="PSU", wattage_w=650, price_rub=6000), 1),
        (
            part(
                "case",
                model="CASE",
                supported_form_factors="ATX,mATX,Mini-ITX",
                max_gpu_length_mm=380,
                price_rub=4000,
            ),
            1,
        ),
        (part("cooler", model="COOLER", supported_sockets="AM4,AM5,LGA1700", price_rub=2000), 1),
    ]


def codes(report) -> set[str]:
    return {issue.code for issue in report.errors}


def test_valid_build_passes(base_set):
    report = evaluate(base_set)

    assert report.ok, report.errors
    assert report.estimated_power_w == 240
    assert report.recommended_psu_w == 350


def test_totals_include_quantities(base_set):
    report = evaluate(base_set)

    assert report.total_price_rub == 20000 + 15000 + 2 * 5000 + 30000 + 6000 + 4000 + 2000


def test_socket_mismatch_blocks_build(base_set):
    base_set[1] = (
        part("motherboard", model="B550", socket="AM4", memory_type="DDR4", form_factor="mATX"),
        1,
    )

    assert "socket_mismatch" in codes(evaluate(base_set))


def test_memory_type_mismatch_blocks_build(base_set):
    base_set[2] = (part("ram", model="DDR4-16", memory_type="DDR4", capacity_gb=16), 1)

    assert "memory_type_mismatch" in codes(evaluate(base_set))


def test_gpu_bigger_than_case_blocks_build(base_set):
    base_set[3] = (part("gpu", model="BIG", tdp_w=220, length_mm=440), 1)

    assert "gpu_too_long" in codes(evaluate(base_set))


def test_weak_psu_blocks_build(base_set):
    base_set[4] = (part("psu", model="WEAK", wattage_w=200), 1)

    assert "psu_too_weak" in codes(evaluate(base_set))


def test_psu_with_low_headroom_warns_only(base_set):
    base_set[4] = (part("psu", model="SMALL", wattage_w=300), 1)

    report = evaluate(base_set)

    assert report.ok
    assert "psu_headroom_low" in {issue.code for issue in report.warnings}


def test_missing_category_blocks_build(base_set):
    report = evaluate(base_set[:4])

    assert "missing_category" in codes(report)
    assert any("case" in issue.message for issue in report.errors)


def test_quantity_limit_blocks_build(base_set):
    base_set[0] = (base_set[0][0], 2)

    assert "quantity_exceeded" in codes(evaluate(base_set))


def test_cooler_socket_must_match(base_set):
    base_set[6] = (part("cooler", model="AMD-only", supported_sockets="AM4,AM5"), 1)
    base_set[0] = (part("cpu", model="INTEL", socket="LGA1700", tdp_w=65), 1)
    base_set[1] = (
        part("motherboard", model="H610", socket="LGA1700", memory_type="DDR4", form_factor="mATX"),
        1,
    )
    base_set[2] = (part("ram", model="DDR4", memory_type="DDR4", capacity_gb=16), 1)

    assert "cooler_socket_unsupported" in codes(evaluate(base_set))


def test_form_factor_must_be_supported(base_set):
    base_set[5] = (
        part("case", model="TINY", supported_form_factors="mATX", max_gpu_length_mm=380),
        1,
    )

    assert "form_factor_not_supported" in codes(evaluate(base_set))


def test_build_without_gpu_is_allowed(base_set):
    rows = [row for row in base_set if row[0].category != "gpu"]

    report = evaluate(rows)

    assert report.ok, report.errors
    assert report.estimated_power_w == 125
    assert report.recommended_psu_w == 200
