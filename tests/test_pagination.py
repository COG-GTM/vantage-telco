from app.pagination import Page


def test_page_envelope_slices_items_and_includes_metadata():
    assert Page(limit=2, offset=1).envelope(["a", "b", "c"], marker="x") == {
        "items": ["b", "c"],
        "total": 3,
        "limit": 2,
        "offset": 1,
        "marker": "x",
    }
