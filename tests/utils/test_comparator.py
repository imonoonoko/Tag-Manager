from modules.spec_checker.comparator import SpecComparator

def test_compare_functions():
    spec = {"mod": {"foo", "bar"}}
    actual = {"mod": {"foo", "baz"}}
    comp = SpecComparator()
    result = comp.compare_functions(spec, actual)
    assert result["mod"]["missing"] == {"bar"}
    assert result["mod"]["undocumented"] == {"baz"} 