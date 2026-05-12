import pytest
from output import sanitize_ben_for_sheet, assign_sheet_names


def test_sanitize_strips_prohibited_chars():
    assert sanitize_ben_for_sheet("ABC[123]") == "DIFF_ABC123"
    assert sanitize_ben_for_sheet("A:B/C") == "DIFF_ABC"
    assert sanitize_ben_for_sheet("X*Y?Z") == "DIFF_XYZ"
    assert sanitize_ben_for_sheet(r"A\B") == "DIFF_AB"


def test_sanitize_truncates_ben_to_26_chars():
    long_ben = "A" * 50
    name = sanitize_ben_for_sheet(long_ben)
    assert len(name) == 31  # DIFF_ (5) + 26
    assert name.startswith("DIFF_")


def test_sanitize_short_ben_not_truncated():
    name = sanitize_ben_for_sheet("T1")
    assert name == "DIFF_T1"
    assert len(name) <= 31


def test_sanitize_result_always_within_31_chars():
    for ben in ["A" * 30, "B:C[D]" * 10, "X" * 26]:
        name = sanitize_ben_for_sheet(ben)
        assert len(name) <= 31, f"Name too long: {name!r}"


def test_assign_sheet_names_no_collision():
    bens = ["TOOL_A", "TOOL_B", "TOOL_C"]
    mapping = assign_sheet_names(bens)
    sheet_names = list(mapping.values())
    assert len(set(sheet_names)) == 3
    assert all(n.startswith("DIFF_") for n in sheet_names)


def test_assign_sheet_names_resolves_collision():
    # Two BENs that differ only after 26 chars will collide after truncation
    ben1 = "A" * 26 + "EXTRA1"
    ben2 = "A" * 26 + "EXTRA2"
    mapping = assign_sheet_names([ben1, ben2])
    sheet_names = list(mapping.values())
    assert len(set(sheet_names)) == 2
    assert all(len(n) <= 31 for n in sheet_names)


def test_assign_sheet_names_maps_original_ben():
    bens = ["MY_TOOL"]
    mapping = assign_sheet_names(bens)
    assert "MY_TOOL" in mapping
    assert mapping["MY_TOOL"] == "DIFF_MY_TOOL"
