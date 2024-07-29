import paramiko
import json
import socket
import re

# 서버 접속 정보 설정
hostname = 
port = 
username = 
password = 
remote_dir = '/data/bug_db/subjects/defects4j/Lang-47'
test_dir = f'{remote_dir}/buggy/src/test/org/apache/commons/lang'


def read_remote_file(filename, hostname, port, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)
        sftp = ssh.open_sftp()
        remote_file_path = filename
        print(f"Reading file: {remote_file_path}")
        try:
            remote_file = sftp.open(remote_file_path, 'r')
            content = remote_file.read().decode('utf-8')
            remote_file.close()
        except FileNotFoundError:
            print(f"FileNotFoundError: The file {remote_file_path} does not exist.")
            raise
        sftp.close()
        ssh.close()
        return content
    except socket.gaierror as e:
        print(f"Socket error: {e}. Please check the server hostname.")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


def parse_diff(diff_lines):
    snippet_info = []
    current_snippet = None
    for line in diff_lines:
        if line.startswith('@@'):
            if current_snippet:
                snippet_info.append(current_snippet)
            current_snippet = {
                "begin_line": int(line.split()[1].split(',')[0][1:]),
                "lines": []
            }
        elif current_snippet is not None:
            current_snippet["lines"].append(line)
    if current_snippet:
        snippet_info.append(current_snippet)
    return snippet_info


def extract_snippet(diff_snippet, begin_line, end_line):
    snippet_lines = diff_snippet['lines'][begin_line:end_line]
    return '\n'.join(snippet_lines)


def extract_comments(file_lines):
    comments = []
    for line in file_lines:
        if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
            comments.append(line.strip())
    return '\n'.join(comments)


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
                "comment": extract_comments(file_lines[max(0, i-5):i])  # 주석 추출
            })
    return fields


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


def list_remote_files(directory):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)
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


# JSON 데이터 로드
try:
    diff_data_content = read_remote_file(f'{remote_dir}/diff_Lang-47.txt', hostname, port, username, password)
    buggy_file_content = read_remote_file(f'{remote_dir}/buggy/src/java/org/apache/commons/lang/text/StrBuilder.java', hostname, port, username, password)
    fixed_file_content = read_remote_file(f'{remote_dir}/fixed/src/java/org/apache/commons/lang/text/StrBuilder.java', hostname, port, username, password)
    tests_content = read_remote_file(f'{remote_dir}/tests.json', hostname, port, username, password)
    npe_traces_content = read_remote_file(f'{remote_dir}/npe.traces.json', hostname, port, username, password)
    coverage_content = read_remote_file(f'{remote_dir}/coverage.json', hostname, port, username, password)

    diff_data = diff_data_content.splitlines()
    buggy_file_lines = buggy_file_content.splitlines()
    fixed_file_lines = fixed_file_content.splitlines()
    tests_data = json.loads(tests_content)
    npe_traces = json.loads(npe_traces_content)
    coverage = json.loads(coverage_content)
except FileNotFoundError as e:
    print(f"Error loading files: {e}")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)

target_traces = [trace for trace in npe_traces['npe.traces'] if any(t['is_target'] for t in trace['traces'])]
coverage_lines = coverage['coverage'][0]['covered']
diff_snippets = parse_diff(diff_data)
failed_tests = {test['name']: test for test in tests_data['failed.tests']}

snippets = []
for trace in target_traces:
    for t in trace['traces']:
        if t['line'] in coverage_lines:
            test_method = trace['test.method']
            is_bug = test_method in failed_tests
            snippet = {
                "name": f"{t['class']}.join#{t['line']}",
                "is_bug": is_bug,
                "src_path": "src/java/org/apache/commons/lang/text/StrBuilder.java",
                "class_name": t['class'],
                "signature": f"{t['class']}.join(...)",
                "snippet": "",  # 실제 코드 스니펫을 포함해야 함
                "begin_line": t['line'],
                "end_line": t['line'] + 1,  # 실제 끝 라인을 포함해야 함
                "comment": "",  # 주석 추가 필요
                "resolved_comments": {},
                "susp": {
                    "ochiai_susp": 0.5  # 실제 점수 필요
                },
                "num_failing_tests": 0 if is_bug else 1
            }
            for diff_snippet in diff_snippets:
                if diff_snippet["begin_line"] <= t['line'] < diff_snippet["begin_line"] + len(diff_snippet["lines"]):
                    snippet["snippet"] = extract_snippet(diff_snippet, 0, len(diff_snippet["lines"]))
                    snippet["end_line"] = diff_snippet["begin_line"] + len(diff_snippet["lines"])
                    snippet["comment"] = extract_comments(diff_snippet["lines"])
                    break
            snippets.append(snippet)

with open('snippet.json', 'w') as f:
    json.dump(snippets, f, indent=4)
print("snippet.json 파일이 생성되었습니다.")

field_snippets = extract_field_info(buggy_file_lines, "org.apache.commons.lang.text.StrBuilder", "src/java/org/apache/commons/lang/text/StrBuilder.java") + extract_field_info(fixed_file_lines, "org.apache.commons.lang.text.StrBuilder", "src/java/org/apache/commons/lang/text/StrBuilder.java")
with open('field_snippet.json', 'w') as f:
    json.dump(field_snippets, f, indent=4)
print("field_snippet.json 파일이 생성되었습니다.")

test_files = []
try:
    test_files = list_remote_files(test_dir)
    test_files = [f for f in test_files if f.endswith('Test.java')]
except FileNotFoundError:
    print("테스트 파일 디렉토리를 찾을 수 없습니다. 경로를 확인하세요.")

test_snippets = []
for test_file in test_files:
    try:
        test_file_path = f"{test_dir}/{test_file}"
        test_file_content = read_remote_file(test_file_path, hostname, port, username, password)
        test_file_lines = test_file_content.splitlines()

        for i, line in enumerate(test_file_lines):
            if 'public void' in line or 'public class' in line:
                method_name = re.search(r'public void (\w+)\(', line)
                if method_name:
                    method_name = method_name.group(1)
                    begin_line = i + 1
                    end_line = begin_line + 1
                    snippet = "\n".join(test_file_lines[begin_line-1:end_line])
                    test_snippets.append({
                        "class_name": test_file.replace('.java', ''),
                        "child_classes": [],
                        "src_path": test_file_path,
                        "signature": f"{test_file.replace('.java', '')}.{method_name}()",
                        "snippet": snippet,
                        "begin_line": begin_line,
                        "end_line": end_line,
                        "comment": "",  # 주석을 추출하려면 추가적인 분석 필요
                        "child_ranges": extract_child_ranges(snippet)
                    })
    except Exception as e:
        print(f"Error processing file {test_file}: {e}")

with open('test_snippet.json', 'w') as f:
    json.dump(test_snippets, f, indent=4)
print("test_snippet.json 파일이 생성되었습니다.")
