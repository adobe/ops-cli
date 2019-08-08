from ops.hierarchical.composition_config_generator import CompositionSorter


def test_composition_discovery():
    expected_order = ["comp1", "compB", "comp3"]
    composition_sorter = CompositionSorter(composition_order=expected_order)
    assert composition_sorter.get_sorted_compositions(["comp3", "comp1", "compB"]) == expected_order


def test_unknown_composition_is_ignored():
    expected_order = ["comp1", "comp2"]
    composition_sorter = CompositionSorter(composition_order=expected_order)
    assert composition_sorter.get_sorted_compositions(["comp2", "comp1", "unknown_composition"]) == expected_order


def test_reverse_order():
    expected_order = ["comp1", "comp2"]
    composition_sorter = CompositionSorter(composition_order=expected_order)
    assert composition_sorter.get_sorted_compositions(["comp1", "comp2"], reverse=True) == ("comp2", "comp1")
