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
test_dir = f'{remote_dir}/buggy/src/test/java/org/apache/commons/lang'


# 서버 접속 및 파일 읽기
def read_remote_file(filename):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)

        sftp = ssh.open_sftp()
        remote_file_path = f"{filename}"
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
    tests_content = read_remote_file(f'{remote_dir}/tests.json')
    diff_data_content = read_remote_file(f'{remote_dir}/diff_Lang-47.txt')
    diff_data = diff_data_content.splitlines()
    tests_data = json.loads(tests_content)
except Exception as e:
    print(f"Error loading files: {e}")
    exit(1)

# diff 데이터 활용
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

diff_snippets = parse_diff(diff_data)

# 주석을 추출하는 함수
def extract_comments(diff_snippet):
    comments = []
    for line in diff_snippet['lines']:
        if line.startswith(' '):
            comments.append(line.strip())
    return '\n'.join(comments)

# 스니펫을 추출하는 함수
def extract_snippet(diff_snippet, start_line, end_line):
    return '\n'.join(diff_snippet["lines"][start_line - diff_snippet["begin_line"]:end_line - diff_snippet["begin_line"]])

# child_ranges를 생성하는 함수
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

# 테스트 파일 목록 가져오기
test_files = []
try:
    test_files = list_remote_files(test_dir)
    test_files = [f for f in test_files if f.endswith('Test.java')]
except FileNotFoundError:
    print("테스트 파일 디렉토리를 찾을 수 없습니다. 경로를 확인하세요.")

# test_snippet.json 생성
test_snippets = []
for test_file in test_files:
    try:
        test_file_path = f"{test_dir}/{test_file}"
        test_file_content = read_remote_file(test_file_path)
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

# JSON 파일 저장
with open('test_snippet.json', 'w') as f:
    json.dump(test_snippets, f, indent=4)

print("test_snippet.json 파일이 생성되었습니다.")
