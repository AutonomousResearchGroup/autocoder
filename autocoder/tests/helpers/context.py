import os
import shutil
from pathlib import Path
from autocoder.helpers.code import extract_imports

from autocoder.helpers.context import (
    get_file_count,
    read_and_format_code,
    collect_files,
    validate_files,
    run_tests,
    run_main,
    backup_project,
)
from autocoder.helpers.files import get_full_path

# Assuming you have a directory for testing
TEST_DIR = "test_dir"
PROJECT_NAME = "test_project"


def setup_function():
    # Create a temporary directory for testing if TEST_DIR doesn't exist
    if not Path(TEST_DIR).exists():
        os.mkdir(TEST_DIR)

    # Add some python files
    with open(os.path.join(TEST_DIR, "main.py"), "w") as f:
        f.write('print("Hello, world!")')

    with open(os.path.join(TEST_DIR, "test_main.py"), "w") as f:
        f.write("def test_main(): assert True")


def teardown_function():
    # Remove the directory after test
    shutil.rmtree(TEST_DIR)


def test_get_file_count():
    setup_function()

    context = {"project_dir": TEST_DIR}
    result = get_file_count(context)

    assert "file_count" in result
    assert result["file_count"] == 2  # We've created 2 files in setup

    teardown_function()


def test_read_and_format_code():
    setup_function()

    context = {"project_dir": TEST_DIR}
    context = collect_files(context)
    context = validate_files(context)
    context = run_tests(context)
    context = run_main(context)
    result = read_and_format_code(context)

    assert "project_code_formatted" in result
    assert "Hello, world!" in result["project_code_formatted"]

    teardown_function()


def test_collect_files():
    setup_function()

    context = {"project_dir": TEST_DIR}
    result = collect_files(context)

    assert "filetree" in result
    assert "filetree_formatted" in result
    assert "python_files" in result
    assert "project_code" in result

    teardown_function()


def test_run_main():
    setup_function()

    context = {"project_dir": TEST_DIR}
    context = collect_files(context)
    result = run_main(context)

    assert "main_success" in result
    assert (
        result["main_success"] is True
    )  # main.py just prints a string, so it should succeed

    teardown_function()


def test_backup_project():
    setup_function()

    context = {"project_dir": TEST_DIR, "project_name": PROJECT_NAME}
    result = backup_project(context)

    assert "backup" in result
    assert Path(result["backup"]).exists()  # The backup file should be created

    teardown_function()


def test_validate_files():
    setup_function()

    context = {"project_dir": TEST_DIR}
    context = collect_files(context)
    context = validate_files(context)

    assert "project_code" in context, "project_code should be in the context"
    assert "project_validated" in context, "project_validated should be in the context"
    assert context["project_validated"] is False, "project_validated should be False"

    teardown_function()


def test_run_tests():
    setup_function()

    context = {"project_dir": TEST_DIR}
    context = collect_files(context)
    context = run_tests(context)

    assert "project_tested" in context
    assert context["project_tested"] is False

    teardown_function()


def test_get_full_path():
    project_dir = "./example/project"
    filepath = "subdir/file.txt"
    expected_full_path = os.getcwd() + "/example/project/subdir/file.txt"

    assert get_full_path(filepath, project_dir) == expected_full_path
    # remove ./example and everything inside
    shutil.rmtree("./example")


def test_extract_imports():
    test_cases = [
        # Here you can add more test cases
        (
            "from langchain.llms import OpenAI\nimport langchain.chat_models\nimport numpy as np\nfrom pandas import DataFrame\nimport os\n",
            ["langchain", "numpy", "pandas"],
        ),
        ("import start\n", []),
    ]

    for code, expected_output in test_cases:
        print(extract_imports(code, "."))
        print("expected")
        print(set(expected_output))
        assert set(extract_imports(code, ".")) == set(expected_output)
