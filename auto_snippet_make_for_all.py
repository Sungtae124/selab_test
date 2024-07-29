import os
import time
import openai
import paramiko
import json
import socket
from dotenv import load_dotenv
from abc import ABC
import re
import bug_list


class OpenAIEngine(ABC):
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def get_LLM_response(self, **kwargs):
        for _ in range(5):
            try:
                response = openai.ChatCompletion.create(**kwargs)
                return response
            except Exception as e:
                save_err = e
                if isinstance(e, openai.error.ServiceUnavailableError):
                    time.sleep(1)
                elif "The server had an error processing your request." in str(e):
                    time.sleep(1)
                else:
                    break
        raise save_err


def load_server_info():
    load_dotenv()
    server_info = {
        "hostname": os.getenv('HOSTNAME'),
        "port": int(os.getenv('PORT')),
        "username": os.getenv('USERNAME'),
        "password": os.getenv('PASSWORD')
    }
    return server_info


def list_remote_files(directory, server_info):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_info["hostname"], server_info["port"], server_info["username"], server_info["password"])
        sftp = ssh.open_sftp()
        try:
            file_list = sftp.listdir(directory)
        except FileNotFoundError:
            print(f"FileNotFoundError: The directory {directory} does not exist.")
            raise
        sftp.close()
        ssh.close()
        return file_list
    except socket.gaierror as e:
        print(f"Socket error: {e}. Please check the server hostname.")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


def select_test_path(bug_id):
    match bug_id:
        case "Chart-2" | "Chart-4" | "Chart-14" | "Chart-16":
            return "/fixed/tests"
        case "Cli-5" | "Codec-5" | "JxPath-1" | "Lang-39" | "Lang-47" | "Lang-57":
            return "/fixed/src/test"
        case "Closure-2" | "Closure-171" | "Mockito-4" | "Mockito-18" | "Mockito-29" | "Mockito-36" | "Mockito-38":
            return "/fixed/test"
        case "Gson-6" | "Gson-9":
            return "/fixed/gson/src/test/java"
        case _:
            return "/fixed/src/test/java"


def read_remote_file(file_path, server_info):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_info["hostname"], server_info["port"], server_info["username"], server_info["password"])
        sftp = ssh.open_sftp()
        remote_file = sftp.open(file_path, 'r')
        content = remote_file.read().decode('utf-8')
        remote_file.close()
        sftp.close()
        ssh.close()
        return content
    except FileNotFoundError as e:
        print(f"FileNotFoundError: The file {file_path} does not exist.")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


def extract_field_info(file_lines, class_name, src_path):
    fields = []
    for i, line in enumerate(file_lines):
        if "public static final" in line or "private static final" in line:
            snippet = line.strip()
            j = i + 1
            while not file_lines[j].strip().endswith(";"):
                snippet += "\n" + file_lines[j].strip()
                j += 1
            snippet += "\n" + file_lines[j].strip()
            fields.append({
                "class_name": class_name,
                "src_path": src_path,
                "signature": " ".join(snippet.split()[:3]),
                "snippet": snippet,
                "begin_line": i + 1,
                "end_line": j + 1,
                "comment": extract_comments(file_lines[max(0, i - 5):i])  # 주석 추출
            })
    return fields


def extract_comments(file_lines):
    comments = []
    for line in file_lines:
        if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
            comments.append(line.strip())
    return '\n'.join(comments)


def extract_child_ranges(snippet):
    child_ranges = []
    lines = snippet.split('\n')
    for line_num, line in enumerate(lines, start=1):
        matches = re.finditer(r'\S+', line)
        for match in matches:
            start_col = match.start() + 1
            end_col = match.end()
            child_ranges.append(f"(line {line_num},col {start_col})-(line {line_num},col {end_col})")
    return child_ranges


def generate_script_from_prompt(prompt, engine):
    response = engine.get_LLM_response(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000,
        temperature=0.7,
    )
    return response['choices'][0]['message']['content']


def check_script_for_bugs(prompt, engine):
    response = engine.get_LLM_response(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.5,
    )
    return response['choices'][0]['message']['content']


def main():
    server_info = load_server_info()
    openai_engine = OpenAIEngine()

    bug_ids = bug_list.get_d4j_bug_list()
    os.makedirs('scripts', exist_ok=True)

    for bug_id in bug_ids:
        try:
            remote_dir = f'/data/bug_db/subjects/defects4j/{bug_id}'
            result_dir = f'{remote_dir}/result'

            # Dynamic test directory discovery
            test_dir_rel = select_test_path(bug_id)
            if test_dir_rel:
                test_dir = f'{remote_dir}/{test_dir_rel}'
            else:
                raise Exception(f"Test directory not found for {bug_id}")

            # Fetch and list files in result directory
            result_files = list_remote_files(result_dir, server_info)
            print(f"Files in {result_dir}: {result_files}")

            # Fetch and list files in test directory
            test_files = list_remote_files(test_dir, server_info)
            print(f"Files in {test_dir}: {test_files}")

            # Generate script based on the prompt
            prompt = (
                f"Given the following directories and files from the defect4j dataset {bug_id}:\n"
                f"Result directory files: {result_files}\n"
                f"Test directory files: {test_files}\n"
                f"Write a Python script that reads the following relevant files from the server: diff_{bug_id}.txt, coverage.json, npe.traces.json, tests.json, and files in the result directory.\n"
                f"The script must process these files and generate three json files, snippet.json, field_snippet.json, and test_snippet.json. "
                f"Ensure that the script correctly handles different directory structures and filenames. "
                f"Additionally, read and process test files in the test directory to extract relevant information for test_snippet.json.\n"
                f"Here is an example script that reads server information from a file and reads remote files using paramiko:\n\n"
                f"Write the script similarly to the example code. Load the necessary files, modify the code based on the comments, and generate the JSON files.\n"
                f"Keep this in mind. You must implement the entire code!\n"
                f"```python\n"
                f"# Example script to generate json files.\n"
                f"import paramiko\n"
                f"import json\n"
                f"import socket\n"
                f"import re\n\n"
                f"# Server connection info\n"
                f"def load_server_info(file_path='server_info.txt'):\n"
                f"    server_info = {{}}\n"
                f"    with open(file_path, 'r') as file:\n"
                f"        lines = file.readlines()\n"
                f"        for line in lines:\n"
                f"            key, value = line.strip().split('=')\n"
                f"            server_info[key] = value\n"
                f"    server_info['port'] = int(server_info['port'])\n"
                f"    return server_info\n\n"
                f"# Load server info\n"
                f"server_info = load_server_info()\n"
                f"hostname = server_info['hostname']\n"
                f"port = server_info['port']\n"
                f"username = server_info['username']\n"
                f"password = server_info['password']\n\n"
                f"# Note that 'Lang-47' can be replaced with another bug data directory\n"
                f"remote_dir = '/data/bug_db/subjects/defects4j/Lang-47'\n"
                f"# Note that this test directory can be replaced with another directory\n"
                f"test_dir = f'{{{{remote_dir}}}}/buggy/src/test/org/apache/commons/lang'\n\n"
                f"def read_remote_file(filename, hostname, port, username, password):\n"
                f"    try:\n"
                f"        ssh = paramiko.SSHClient()\n"
                f"        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())\n"
                f"        ssh.connect(hostname, port, username, password)\n"
                f"        sftp = ssh.open_sftp()\n"
                f"        remote_file_path = filename\n"
                f"        print(f'Reading file: {{{{remote_file_path}}}}')\n"
                f"        try:\n"
                f"            remote_file = sftp.open(remote_file_path, 'r')\n"
                f"            content = remote_file.read().decode('utf-8')\n"
                f"            remote_file.close()\n"
                f"        except FileNotFoundError:\n"
                f"            print(f'FileNotFoundError: The file {{{{remote_file_path}}}} does not exist.')\n"
                f"            raise\n"
                f"        sftp.close()\n"
                f"        ssh.close()\n"
                f"        return content\n"
                f"    except socket.gaierror as e:\n"
                f"        print(f'Socket error: {{{{e}}}}. Please check the server hostname.')\n"
                f"        raise\n"
                f"    except Exception as e:\n"
                f"        print(f'An error occurred: {{{{e}}}}')\n"
                f"        raise\n\n"
                f"def list_remote_files(directory):\n"
                f"    try:\n"
                f"        ssh = paramiko.SSHClient()\n"
                f"        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())\n"
                f"        ssh.connect(hostname, port, username, password)\n"
                f"        sftp = ssh.open_sftp()\n"
                f"        try:\n"
                f"            file_list = sftp.listdir(directory)\n"
                f"        except FileNotFoundError:\n"
                f"            print(f'FileNotFoundError: The directory {{{{directory}}}} does not exist.')\n"
                f"            raise\n"
                f"        sftp.close()\n"
                f"        ssh.close()\n"
                f"        return file_list\n"
                f"    except socket.gaierror as e:\n"
                f"        print(f'Socket error: {{{{e}}}}. Please check the server hostname.')\n"
                f"        raise\n"
                f"    except Exception as e:\n"
                f"        print(f'An error occurred: {{{{e}}}}')\n"
                f"        raise\n\n"
                f"# JSON Data Load\n"
                f"# Note that below files can be replaced with another bug data files. You have to find proper files!\n"
                f"try:\n"
                f"    diff_data_content = read_remote_file(f'{{{{remote_dir}}}}/diff_Lang-47.txt', hostname, port, username, password)\n"
                f"    buggy_file_content = read_remote_file(f'{{{{remote_dir}}}}/buggy/src/java/org/apache/commons/lang/text/StrBuilder.java', hostname, port, username, password)\n"
                f"    fixed_file_content = read_remote_file(f'{{{{remote_dir}}}}/fixed/src/java/org/apache/commons/lang/text/StrBuilder.java', hostname, port, username, password)\n"
                f"    tests_content = read_remote_file(f'{{{{remote_dir}}}}/tests.json', hostname, port, username, password)\n"
                f"    npe_traces_content = read_remote_file(f'{{{{remote_dir}}}}/npe.traces.json', hostname, port, username, password)\n"
                f"    coverage_content = read_remote_file(f'{{{{remote_dir}}}}/coverage.json', hostname, port, username, password)\n\n"
                f"    diff_data = diff_data_content.splitlines()\n"
                f"    buggy_file_lines = buggy_file_content.splitlines()\n"
                f"    fixed_file_lines = fixed_file_content.splitlines()\n"
                f"    tests_data = json.loads(tests_content)\n"
                f"    npe_traces = json.loads(npe_traces_content)\n"
                f"    coverage = json.loads(coverage_content)\n"
                f"except FileNotFoundError as e:\n"
                f"    print(f'Error loading files: {{{{e}}}}')\n"
                f"    exit(1)\n"
                f"except Exception as e:\n"
                f"    print(f'An error occurred: {{{{e}}}}')\n"
                f"    exit(1)\n\n"
                f"target_traces = [trace for trace in npe_traces['npe.traces'] if any(t['is_target'] for t in trace['traces'])]\n"
                f"coverage_lines = coverage['coverage'][0]['covered']\n"
                f"failed_tests = {{{{test['name']: test for test in tests_data['failed.tests']}}}}\n\n"
                f"snippets = []\n"
                f"for trace in target_traces:\n"
                f"    for t in trace['traces']:\n"
                f"        if t['line'] in coverage_lines:\n"
                f"            test_method = trace['test.method']\n"
                f"            is_bug = test_method in failed_tests\n"
                f"            snippet = {{\n"
                f"                'name': f'{{{{t['class']}}}}.join#{{{{t['line']}}}}',\n"
                f"                'is_bug': is_bug,\n"
                f"                'src_path': 'src/java/org/apache/commons/lang/text/StrBuilder.java',\n"
                f"                'class_name': t['class'],\n"
                f"                'signature': f'{{{{t['class']}}}}.join(...)',\n"
                f"                'snippet': '',\n"
                f"                'begin_line': t['line'],\n"
                f"                'end_line': t['line'] + 1,\n"
                f"                'comment': '',\n"
                f"                'resolved_comments': {{}},\n"
                f"                'susp': {{'ochiai_susp': 0.5}},\n"
                f"                'num_failing_tests': 0 if is_bug else 1\n"
                f"            }}\n"
                f"            for diff_snippet in diff_snippets:\n"
                f"                if diff_snippet['begin_line'] <= t['line'] < diff_snippet['begin_line'] + len(diff_snippet['lines']):\n"
                f"                    snippet['snippet'] = extract_snippet(diff_snippet, 0, len(diff_snippet['lines']))\n"
                f"                    snippet['end_line'] = diff_snippet['begin_line'] + len(diff_snippet['lines'])\n"
                f"                    snippet['comment'] = extract_comments(diff_snippet['lines'])\n"
                f"                    break\n"
                f"            snippets.append(snippet)\n\n"
                f"with open('snippet.json', 'w') as f:\n"
                f"    json.dump(snippets, f, indent=4)\n"
                f"print('snippet.json file generated.')\n\n"
                f"# Note that below files can be replaced with another bug data files. You have to find proper files!\n"
                f"field_snippets = extract_field_info(buggy_file_lines, 'org.apache.commons.lang.text.StrBuilder', 'src/java/org/apache/commons/lang/text/StrBuilder.java') + extract_field_info(fixed_file_lines, 'org/apache/commons/lang/text/StrBuilder.java')\n"
                f"with open('field_snippet.json', 'w') as f:\n"
                f"    json.dump(field_snippets, f, indent=4)\n"
                f"print('field_snippet.json file generated.')\n\n"
                f"test_files = list_remote_files(test_dir)\n"
                f"test_files = [f for f in test_files if f.endswith('Test.java')]\n\n"
                f"test_snippets = []\n"
                f"for test_file in test_files:\n"
                f"    try:\n"
                f"        test_file_path = f'{{{{test_dir}}}}/{{{{test_file}}}}'\n"
                f"        test_file_content = read_remote_file(test_file_path, hostname, port, username, password)\n"
                f"        test_file_lines = test_file_content.splitlines()\n\n"
                f"        for i, line in enumerate(test_file_lines):\n"
                f"            if 'public void' in line or 'public class' in line:\n"
                f"                method_name = re.search(r'public void (\\w+)\\(', line)\n"
                f"                if method_name:\n"
                f"                    method_name = method_name.group(1)\n"
                f"                    begin_line = i + 1\n"
                f"                    end_line = begin_line + 1\n"
                f"                    snippet = '\\n'.join(test_file_lines[begin_line-1:end_line])\n"
                f"                    test_snippets.append({{\n"
                f"                        'class_name': test_file.replace('.java', ''),\n"
                f"                        'child_classes': [],\n"
                f"                        'src_path': test_file_path,\n"
                f"                        'signature': f'{{{{test_file.replace('.java', '')}}}}.{{{{method_name}}}}()',\n"
                f"                        'snippet': snippet,\n"
                f"                        'begin_line': begin_line,\n"
                f"                        'end_line': end_line,\n"
                f"                        'comment': '',\n"
                f"                        'child_ranges': extract_child_ranges(snippet)\n"
                f"                    }})\n"
                f"    except Exception as e:\n"
                f"        print(f'Error processing file {{{{test_file}}}}: {{{{e}}}}')\n\n"
                f"with open('test_snippet.json', 'w') as f:\n"
                f"    json.dump(test_snippets, f, indent=4)\n"
                f"print('test_snippet.json file generated.')\n"
                f"```\n"
                f"Please provide the actual script below and make sure to comment out any non-code parts."
            )

            script_content = generate_script_from_prompt(prompt, openai_engine)

            # Extract the actual code from the response
            code_lines = []
            is_code_block = False
            for line in script_content.split('\n'):
                if line.strip().startswith('```python'):
                    is_code_block = True
                    continue
                elif line.strip().startswith('```'):
                    is_code_block = False
                    continue

                if is_code_block:
                    code_lines.append(line)

            final_script = '\n'.join(code_lines)

            # Check the script for bugs
            check_prompt = (
                f"Please check the following script for bugs and suggest any necessary corrections:\n\n"
                f"```python\n{final_script}\n```"
            )
            bug_check_response = check_script_for_bugs(check_prompt, openai_engine)

            print("Bug Check Response:")
            print(bug_check_response)

            # Save the generated script to a file
            script_filename = f'scripts/generated_script_for_{bug_id}.py'
            with open(script_filename, 'w') as script_file:
                script_file.write(final_script)

            print(f"Generated script saved to {script_filename}")

        except Exception as e:
            print(f"Error processing bug {bug_id}: {e}")


if __name__ == "__main__":
    main()
