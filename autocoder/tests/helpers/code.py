import tempfile
import os
from autocoder.helpers.code import (
    contains_function_definition,
    file_exists,
    has_functions_called,
    is_runnable,
    count_lines,
    organize_imports,
    validate_file,
    validate_code,
    save_code,
    run_code,
    run_code_tests,
)


def test_is_runnable_success():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(b"print('Hello, world!')")
    assert is_runnable(tmp.name) == True
    os.remove(tmp.name)


def test_is_runnable_failure():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(b"\n()prin('Hello, world!asdfs)asdfsafsa\ndfgs\n")
        tmp.flush()
        tmp.close()

    assert is_runnable(tmp.name) == False
    os.remove(tmp.name)


def test_contains_function_definition_true():
    code = """
def hello():
    print('Hello, world!')
hello()
    """
    assert contains_function_definition(code) == True


def test_has_functions_called_true():
    code = """
print('Hello, world!')
    """
    assert has_functions_called(code) == True


def test_has_functions_called_false():
    code = """
def hello():
    print('Hello, world!')
    """
    assert has_functions_called(code) == False


def test_file_exists_true():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"print('Hello, world!')")
    assert file_exists(tmp.name) == True
    os.remove(tmp.name)


def test_file_exists_false():
    assert file_exists("/path/to/nonexistent/file") == False


def test_count_lines_with_comments_and_empty_lines():
    code = """
# This is a comment
print('Hello, world!')  # This is another comment

# This is yet another comment
"""
    assert count_lines(code) == 1


def test_count_lines_without_comments_and_empty_lines():
    code = """
# This is a comment
print('Hello, world!')  # This is another comment

# This is yet another comment
"""
    assert (
        count_lines(code, exclude_comments=True, exclude_empty_lines=True) == 1
    ), "Should be 1 line but is {}".format(
        count_lines(code, exclude_comments=True, exclude_empty_lines=True)
    )


def test_validate_code_success():
    code = """
    import os

    def hello():
        print('Hello, world!')

    hello()
    """
    assert validate_code(code) == {"success": True, "error": None}


def test_validate_code_failure():
    code = """
    import os
    TODO: Implement function here
    """
    result = validate_code(code)
    assert result["success"] == False


def test_save_code():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        code = 'print("Hello, world!"")'
        save_code(code, tmp.name)
    with open(tmp.name, "r") as f:
        new_code = f.read()
        assert new_code == code
    os.remove(tmp.name)


def test_run_code_success():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(b"print('Hello, world!')")
    result = run_code(tmp.name)
    assert result["success"] == True
    assert result["error"] == None
    assert result["output"].strip() == "Hello, world!"
    os.remove(tmp.name)


def test_run_code_failure():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(b"aprint(foo)a")
    result = run_code(tmp.name)
    assert result["success"] == False
    os.remove(tmp.name)


def test_contains_function_definition_false():
    code = """
def hello():
    print('Hello, world!')
    """
    assert contains_function_definition(code) == True


def test_validate_file_success():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(
            b"import os\ndef hello():\n\tprint('Hello, world!')\nhello()\n\ndef goodbye():\n\tprint('Goodbye, world!')\ngoodbye()"
        )
    output = validate_file(tmp.name)
    assert validate_file(tmp.name) == {"success": True, "error": None}
    os.remove(tmp.name)


def test_validate_file_failure():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(b"print('Hello, world!")
    assert validate_file(tmp.name) == {
        "success": False,
        "error": "The file is not runnable, or didn't compile.",
    }
    os.remove(tmp.name)


def test_test_code_success():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(
            b"""
def test_hello():
    assert 'Hello, world!' == 'Hello, world!'
test_hello()
    """
        )
    result = run_code_tests(tmp.name)
    assert result["success"] == True
    # assert "1 passed" in result["output"]
    # assert result["error"] == ""
    os.remove(tmp.name)


def test_organize_imports():
    expected_output = """\
import os
import sys
from random import randint
from random import randint, shuffle


def foo():
    return randint(1, 10)


print(foo())
"""
    to_test = ""
    # get the first two lines of expected_output and add to to_test
    for line in expected_output.split("\n")[:2]:
        to_test += line + "\n"
    # now add all of expected_output to to_test to simulate doubled imports
    to_test += expected_output
    actual_output = organize_imports(to_test)
    assert expected_output.strip() == actual_output.strip()
