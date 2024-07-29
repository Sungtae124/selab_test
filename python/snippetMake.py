import json
import paramiko
import socket

# 서버 접속 정보 설정
hostname = 
port = 
username = 
password = 
remote_dir = '/data/bug_db/subjects/defects4j/Lang-47'

def read_remote_file(filename):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)

        sftp = ssh.open_sftp()
        remote_file_path = f"{remote_dir}/{filename}"
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

def extract_comments(diff_snippet):
    comments = []
    for line in diff_snippet['lines']:
        if line.startswith(' '):
            comments.append(line.strip())
    return '\n'.join(comments)

# JSON 데이터 로드
try:
    npe_traces_content = read_remote_file('npe.traces.json')
    coverage_content = read_remote_file('coverage.json')
    diff_data_content = read_remote_file('diff_Lang-47.txt')
    tests_content = read_remote_file('tests.json')

    npe_traces = json.loads(npe_traces_content)
    coverage = json.loads(coverage_content)
    diff_data = diff_data_content.splitlines()
    tests_data = json.loads(tests_content)
except Exception as e:
    print(f"Error loading files: {e}")
    exit(1)

# 필요한 데이터 필터링
def filter_target_traces(traces):
    target_traces = []
    for trace in traces['npe.traces']:
        filtered_traces = [t for t in trace['traces'] if t['is_target']]
        target_traces.append({
            "test.method": trace['test.method'],
            "test.class": trace['test.class'],
            "traces": filtered_traces
        })
    return target_traces

target_traces = filter_target_traces(npe_traces)

# coverage 데이터 활용
coverage_lines = coverage['coverage'][0]['covered']

# diff 데이터 활용
diff_snippets = parse_diff(diff_data)

# failed tests 정보 활용
failed_tests = {test['name']: test for test in tests_data['failed.tests']}

# snippet.json 생성
snippets = []
for trace in target_traces:
    for t in trace['traces']:
        if t['line'] in coverage_lines:
            test_method = trace['test.method']
            is_bug = test_method in failed_tests
            snippet = {
                "name": f"{t['class']}.join#{t['line']}",
                "is_bug": is_bug,
                "src_path": "src/main/java/org/apache/commons/lang/StringUtils.java",
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
                    snippet["comment"] = extract_comments(diff_snippet)
                    break
            snippets.append(snippet)

# JSON 파일 저장
with open('snippet.json', 'w') as f:
    json.dump(snippets, f, indent=4)

print("snippet.json 파일이 생성되었습니다.")
