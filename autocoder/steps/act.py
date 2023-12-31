import os
import re
from easycompletion import compose_function, compose_prompt, openai_function_call
from autocoder.helpers.code import save_code
from autocoder.helpers.context import handle_packages

from autocoder.helpers.files import get_full_path
from agentlogger import log

create_prompt = """Task: Create a Python module that meets the stated goals, along with a set of tests for that module.

This is my project goal:
{{goal}}

Write the main.py with code and tests to complete this goal. You should include the following details:
- Reasoning: Explain your approach
- Code: The full code for main.py, including all imports and code
    - There should be a main function which is called if __name__ == '__main__' (which should be located at the bottom of the script)
    - Use a functional style, avoid classes unless necessary
- Test: The code for main_test.py, including all imports and functions. Tests should use a functional style with the assert keyword and run with pytest
    - All tests should be in their own functions and have setup and teardown so that they are isolated from each other
    - There should be multiple tests for each function, including tests for edge cases, different argument cases and failure cases
    - Do not use fixtures or anything else that is not a standard part of pytest"""

edit_prompt = """{{available_actions}}
Notes:
- Use a functional style for code and tests
- Do not include line numbers [#] at the beginning of the lines in your response
- Include the correct tabs at the beginning of lines in your response
- main.py must contain a main function which is called if __name__ == '__main__' (at the bottom of the file)
- Replace broken code. If my code is really broken, write the code again in its entirety
- For something small like an import, just insert the import
- When rewriting the code, include the complete script, including all imports and code
- Do NOT shorten or abbreviate anything, DO NOT use "..." or "# Rest of the code" - ALWAYS put the complete code in your response



This is my project goal:
{{goal}}

{{reasoning}}
{{project_code_formatted}}
{{errors_formatted}}
{{available_action_names}}

Task:
- First reason out loud about what you are going to do
- Based on your reasoning, choose a function by name
- Then choose which file to edit. You can also create or remove a file if necessary
- Respond with the function, code, reasoning and necessary inputs to call the function
- 

"""

create_function = compose_function(
    name="create",
    description="Create a new script called main.py, as well as a test for main.py named main_test.py.",
    properties={
        "reasoning": {
            "type": "string",
            "description": "Explain your reasoning step-by-step.",
        },
        "code": {
            "type": "string",
            "description": "The full code for main.py, including all imports and code, with no abbreviations.",
        },
        "test": {
            "type": "string",
            "description": "The full code for main_test.py, including all imports and code, with no abbreviations and compatible with pytest.",
        },
    },
    required_properties=["reasoning", "code", "test"],
)


def create_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"

    reasoning = arguments["reasoning"]
    code = arguments["code"]
    test = arguments["test"]

    project_dir = context["project_dir"]

    log(
        f"Creating main.py in {project_dir}"
        + f"\n\nReasoning:\n{reasoning}"
        + f"\n\nCode:\n{code}"
        + f"\n\nTest:\n{test}",
        title="action",
        type="create",
        log=should_log,
    )

    save_code(code, f"{project_dir}/main.py")
    save_code(test, f"{project_dir}/main_test.py")

    return context


def remove_line_numbers(text):
    # Regular expression pattern to match '[n]' at the beginning of a line
    pattern = r"^\s*\[\d+\]\s*"

    # Split the text into lines
    lines = text.split("\n")

    # Remove the pattern from each line
    cleaned_lines = [re.sub(pattern, "", line) for line in lines]

    # Join the cleaned lines back into a single string
    cleaned_text = "\n".join(cleaned_lines)

    return cleaned_text


def write_complete_script_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"
    reasoning = arguments["reasoning"]
    code = remove_line_numbers(arguments["code"])

    filepath = arguments["filepath"]
    write_path = get_full_path(filepath, context["project_dir"])

    log(
        f"Writing complete script to {write_path}"
        + f"\n\nReasoning:\n{reasoning}"
        + f"\n\nCode:\n{code}",
        title="action",
        type="write",
        log=should_log,
    )

    save_code(code, write_path)
    return context


def insert_code_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"
    reasoning = arguments["reasoning"]
    code = arguments["code"]
    start_line = arguments["start_line"]
    filepath = arguments["filepath"]
    write_path = get_full_path(filepath, context["project_dir"])

    log(
        f"Inserting code into {write_path} at line {start_line}"
        + f"\n\nReasoning:\n{reasoning}"
        + f"\n\nCode:\n{code}",
        title="action",
        type="insert",
        log=should_log,
    )

    with open(write_path, "r") as f:
        text = f.read()
    lines = text.split("\n")
    lines.insert(start_line, code)
    text = "\n".join(lines)

    log(f"New code:\n{text}", title="action", type="insert", log=should_log)

    save_code(text, write_path)
    return context


def edit_code_handler(arguments, context):
    edit_type = arguments["edit_type"]
    if edit_type == "insert":
        return insert_code_handler(arguments, context)
    elif edit_type == "replace":
        return replace_code_handler(arguments, context)
    elif edit_type == "remove":
        return remove_code_handler(arguments, context)


def replace_code_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"
    reasoning = arguments["reasoning"]
    code = arguments["code"]
    start_line = int(arguments["start_line"])
    end_line = int(arguments["end_line"])
    filepath = arguments["filepath"]
    write_path = get_full_path(filepath, context["project_dir"])

    log(
        f"Replacing code in {write_path} from line {start_line} to {end_line}"
        + f"\n\nReasoning:\n{reasoning}"
        + f"\n\nCode:\n{code}",
        title="action",
        type="replace",
        log=should_log,
    )

    # floor start_line to 1
    if start_line < 1:
        start_line = 1

    # Replace the code between start_lines and end_lines with new code
    with open(write_path, "r") as f:
        text = f.read()
    lines = text.split("\n")
    lines[start_line - 1 : end_line] = [code]  # python's list indices start at 0
    text = "\n".join(lines)

    log(f"New code:\n{lines}", title="action", type="replace", log=should_log)

    save_code(text, write_path)

    return context


def remove_code_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"
    reasoning = arguments["reasoning"]
    start_line = int(arguments["start_line"])
    end_line = int(arguments["end_line"])
    filepath = arguments["filepath"]
    write_path = get_full_path(filepath, context["project_dir"])

    log(
        f"Removing code in {write_path} from line {start_line} to {end_line}"
        + f"\n\nReasoning:\n{reasoning}",
        title="action",
        type="remove",
        log=should_log,
    )

    # Remove the code between start_lines and end_lines
    with open(write_path, "r") as f:
        text = f.read()
    lines = text.split("\n")
    del lines[start_line - 1 : end_line]  # python's list indices start at 0

    lines = "\n".join(lines)

    log(f"New code:\n{lines}", title="action", type="remove", log=should_log)

    save_code(lines, write_path)

    return context


def create_new_file_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"
    reasoning = arguments["reasoning"]
    filepath = arguments["filepath"]
    code = arguments["code"]
    test = arguments["test"]

    log(
        f"Creating new file {filepath}"
        + f"\n\nReasoning:\n{reasoning}"
        + f"\n\nCode:\n{code}"
        + f"\n\nTest:\n{test}",
        title="action",
        type="create",
        log=should_log,
    )

    # Create a new file at filepath with code
    write_path = get_full_path(filepath, context["project_dir"])
    save_code(code, write_path)

    # Create a new file at filepath_test.py with test
    test_path = get_full_path(
        f"{os.path.splitext(filepath)[0]}_test.py", context["project_dir"]
    )
    save_code(test, test_path)

    return context


def delete_file_handler(arguments, context):
    should_log = context.get("log_level", "normal") != "quiet"
    reasoning = arguments["reasoning"]
    filepath = arguments["filepath"]

    if "main.py" in filepath or "main_test.py" in filepath:
        log(
            f"File {filepath} contains main.py or main_test.py, so it will not be deleted",
            title="action",
            type="warning",
            log=should_log,
        )
        return context

    log(
        f"Deleting file {filepath}" + f"\n\nReasoning:\n{reasoning}",
        title="action",
        type="delete",
        log=should_log,
    )

    # Delete the file at filepath
    file_path = get_full_path(filepath, context["project_dir"])
    # check if the file exists
    if os.path.exists(file_path):
        os.remove(file_path)
        # if file_path didn't contain _test.py, then delete the _test.py file
        if "_test.py" not in file_path:
            test_path = get_full_path(
                f"{os.path.splitext(filepath)[0]}_test.py", context["project_dir"]
            )
            if os.path.exists(test_path):
                os.remove(test_path)
    else:
        log(
            f"File {filepath} does not exist",
            title="action",
            type="warning",
            log=should_log,
        )

    return context


def get_actions():
    return [
        # {
        #     "function": compose_function(
        #         name="create_new_file",
        #         description="Create a Python file",
        #         properties={
        #             "reasoning": {
        #                 "type": "string",
        #                 "description": "Explain your reasoning step-by-step.",
        #             },
        #             "filepath": {
        #                 "type": "string",
        #                 "description": "The path of the file to create.",
        #             },
        #             "code": {
        #                 "type": "string",
        #                 "description": "The full code for the module, including all imports and code, with no abbreviations",
        #             },
        #             "test": {
        #                 "type": "string",
        #                 "description": "A set of functional pytest-compatible tests for the module code.",
        #             },
        #         },
        #         required_properties=[
        #             "reasoning",
        #             "filepath",
        #             "code",
        #             "test",
        #         ],
        #     ),
        #     "handler": create_new_file_handler,
        # },
        # {
        #     "function": compose_function(
        #         name="delete_file",
        #         description="Delete a file that is unnecessary or contains duplicate functionality",
        #         properties={
        #             "reasoning": {
        #                 "type": "string",
        #                 "description": "Why are we deleting this file? Explain step-by-step.",
        #             },
        #             "filepath": {
        #                 "type": "string",
        #                 "description": "The path of the file to delete.",
        #             },
        #         },
        #         required_properties=["reasoning", "filepath"],
        #     ),
        #     "handler": delete_file_handler,
        # },
        # {
        #     "function": compose_function(
        #         name="edit_code",
        #         description="Insert, replace or remove code. Insert: adds a line or more of code at start_line. Replace: replace broken code with new code, from start_line through end_line. Remove: removes start_line through end_line.",
        #         properties={
        #             "reasoning": {
        #                 "type": "string",
        #                 "description": "Explain your reasoning step-by-step.",
        #             },
        #             "filepath": {
        #                 "type": "string",
        #                 "description": "The path of the file to edit.",
        #             },
        #             "edit_type": {
        #                 "type": "string",
        #                 "enum": ["insert", "replace", "remove"],
        #                 "description": "The type of edit to perform.",
        #             },
        #             "code": {
        #                 "type": "string",
        #                 "description": "The new code to insert or replace existing code with.",
        #             },
        #             "start_line": {
        #                 "type": "number",
        #                 "description": "The start line number where code is being inserted, replaced or removed.",
        #             },
        #             "end_line": {
        #                 "type": "number",
        #                 "description": "The end line number where code is being replaced. Required for replace and remove, ignored for insert (set to -1).",
        #             },
        #         },
        #         required_properties=[
        #             "reasoning",
        #             "filepath",
        #             "edit_type",
        #             "code",
        #             "start_line",
        #             "end_line",
        #         ],
        #     ),
        #     "handler": edit_code_handler,
        # },
        {
            "function": compose_function(
                name="replace_code",
                description="Replace some of the existing code with new code, from start_line through end_line. Replace with an emptry string to remove lines, or insert new lines by setting start_line and end_line to the same line number.",
                properties={
                    "reasoning": {
                        "type": "string",
                        "description": "Explain your reasoning step-by-step.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "The path of the file to edit.",
                    },
                    "code": {
                        "type": "string",
                        "description": "The new code to insert or replace existing code with.",
                    },
                    "start_line": {
                        "type": "number",
                        "description": "The start line number where code is being inserted, replaced or removed.",
                    },
                    "end_line": {
                        "type": "number",
                        "description": "The end line number where code is being replaced. Required for replace and remove, ignored for insert (set to -1).",
                    },
                },
                required_properties=[
                    "reasoning",
                    "filepath",
                    "code",
                    "start_line",
                    "end_line",
                ],
            ),
            "handler": replace_code_handler,
        },
        {
            "function": compose_function(
                name="write_code",
                description="Write all of the code for the module, including imports and functions. No snippets, abbreviations or single lines. Must be a complete code file with the structure 'imports', 'functions', and 'main entry' for main.py -- where main entry is called if __name__ == '__main__'.",
                properties={
                    "reasoning": {
                        "type": "string",
                        "description": "Explain your reasoning step-by-step.",
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to where the file will be written (usually just filename).",
                    },
                    "code": {
                        "type": "string",
                        "description": "The full code for the module, including all imports and code, with no abbreviations.",
                    },
                },
                required_properties=["reasoning", "filepath", "code"],
            ),
            "handler": write_complete_script_handler,
        },
    ]


def step(context):
    """
    This function serves as the 'Act' stage in the OODA loop. It executes the selected action from the 'Decide' stage.

    Args:
        context (dict): The dictionary containing data about the current state of the system, including the selected action to be taken.

    Returns:
        dict: The updated context dictionary after the 'Act' stage, which will be used in the next iteration of the OODA loop.
    """

    if context["running"] == False:
        return context

    should_log = context.get("log_level", "normal") != "quiet"
    debug = context.get("log_level", "normal") == "debug"

    log(
        "Act Step Started",
        title="step",
        type="info",
        log=should_log,
    )

    prompt = edit_prompt
    actions = get_actions()

    # each entry in functions is a dict
    # # get the "fuction" value from each entry in the function list
    functions = [f["function"] for f in actions]

    if context["file_count"] == 0:
        prompt = create_prompt
        functions = [create_function]

    context["available_actions"] = "Available functions:\n"
    for fn in actions:
        context[
            "available_actions"
        ] += f"{fn['function']['name']}: {fn['function']['description']}\n"
        # include properties and descriptions
        for prop, details in fn["function"]["parameters"]["properties"].items():
            context["available_actions"] += f"  {prop}: {details['description']}\n"
        context["available_actions"] += "\n"

    context["available_action_names"] = "Available functions: " + ", ".join(
        [fn["function"]["name"] for fn in actions]
    )

    if context.get("reasoning") is None:
        # find {{reasoning}} in prompt and replace with empty string
        prompt = prompt.replace("{{reasoning}}", "")
    else:
        log(
            f"Reasoning:\n{context['reasoning']}",
            title="action",
            type="reasoning",
            log=should_log,
        )

    text = compose_prompt(prompt, context)

    response = openai_function_call(
        text=text,
        functions=functions,
        debug=debug,
        model=context.get("model", "gpt-3.5-turbo-0613"),
    )

    # find the function in functions with the name that matches response["function_name"]
    # then call the handler with the arguments and context
    function_name = response["function_name"]

    # if function_name is create, then we need to create a new file
    if function_name == "create":
        create_handler(response["arguments"], context)
        return context

    arguments = response["arguments"]
    action = None

    for f in actions:
        if f["function"]["name"] == function_name:
            action = f
            break

    args_str = "\n".join(
        f"*** {key} ***\n{str(value)}"
        if "\n" in str(value)
        else f"*** {key}: {str(value)}"
        for key, value in arguments.items()
    )

    log(
        f"Running action {function_name} with arguments:\n{args_str}",
        title="action",
        type="handler",
        log=debug,
    )

    # call the handler with the arguments and context
    context = action["handler"](arguments, context)

    # install any new imports if there are any
    context = handle_packages(context)

    return context
