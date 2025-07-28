from modules.spec_checker.reporter import ReportGenerator

def test_generate_function_report():
    compare_result = {"mod": {"missing": {"foo"}, "undocumented": {"bar"}}}
    reporter = ReportGenerator()
    report = reporter.generate_function_report(compare_result)
    assert "未実装関数" in report
    assert "仕様書未記載関数" in report 