from pathlib import Path
from datetime import datetime


def save_regression_report(results, output_path="artifacts/regression_report.txt"):
    """
    Save regression test results into a text report.

    Parameters:
        results:
            A list of dictionaries. Each dictionary represents one test case.

            Expected structure:
            {
                "name": "TEST1 ...",
                "passed": True,
                "warnings": 0,
                "duration": 1.23,
                "message": "Passed"
            }

        output_path:
            The path where the report file will be saved.

    Returns:
        The Path object of the generated report.
    """

    # Convert output path string to a Path object.
    report_path = Path(output_path)

    # Create the parent folder if it does not exist.
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Count basic test statistics.
    total_count = len(results)
    passed_count = sum(1 for item in results if item.get("passed"))
    failed_count = total_count - passed_count
    warning_count = sum(item.get("warnings", 0) for item in results)

    # Build report content line by line.
    lines = []
    lines.append("Regression Test Report")
    lines.append("=" * 60)
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"Total tests: {total_count}")
    lines.append(f"Passed: {passed_count}")
    lines.append(f"Failed: {failed_count}")
    lines.append(f"Warnings: {warning_count}")
    lines.append("")
    lines.append("Test Details")
    lines.append("-" * 60)

    # Add detail for each test case.
    for index, item in enumerate(results, start=1):
        status = "PASS" if item.get("passed") else "FAIL"
        name = item.get("name", f"TEST{index}")
        duration = item.get("duration", 0.0)
        warnings = item.get("warnings", 0)
        message = item.get("message", "")

        lines.append(f"[{index}] {name}")
        lines.append(f"    Status: {status}")
        lines.append(f"    Duration: {duration:.2f}s")
        lines.append(f"    Warnings: {warnings}")

        if message:
            lines.append(f"    Message: {message}")

        lines.append("")

    # Write report content into the target file.
    report_path.write_text("\n".join(lines), encoding="utf-8-sig")

    return report_path