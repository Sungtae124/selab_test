import paramiko
import json
import socket

# 서버 접속 정보 설정
hostname = 
port = 
username = 
password = 
remote_dir = '/data/bug_db/subjects/defects4j/Lang-47'


# 서버 접속 및 파일 읽기 함수
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

# JSON 데이터 로드
try:
    diff_data_content = read_remote_file('diff_Lang-47.txt')
    buggy_file_content = read_remote_file('buggy/src/main/java/org/apache/commons/lang/StringUtils.java')
    fixed_file_content = read_remote_file('fixed/src/main/java/org/apache/commons/lang/StringUtils.java')
    diff_data = diff_data_content.splitlines()
    buggy_file_lines = buggy_file_content.splitlines()
    fixed_file_lines = fixed_file_content.splitlines()
except FileNotFoundError as e:
    print(f"Error loading files: {e}")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)

# 필드 정보 추출 함수
def extract_field_info(file_lines):
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
                "class_name": "org.apache.commons.lang3.StringUtils",
                "src_path": "src/main/java/org/apache/commons/lang/StringUtils.java",
                "signature": " ".join(snippet.split()[:3]),
                "snippet": snippet,
                "begin_line": i + 1,
                "end_line": j + 1,
                "comment": extract_comments(file_lines[max(0, i-5):i])  # 주석 추출
            })
    return fields

# 주석 추출 함수
def extract_comments(lines):
    comments = []
    inside_comment = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("//"):
            inside_comment = True
        if inside_comment:
            comments.append(stripped)
        if stripped.endswith("*/") or stripped.startswith("//"):
            inside_comment = False
    return "\n".join(comments)

# 필드 정보 추출
field_snippets = extract_field_info(buggy_file_lines) + extract_field_info(fixed_file_lines)

# JSON 파일 저장
with open('field_snippet.json', 'w') as f:
    json.dump(field_snippets, f, indent=4)

print("field_snippet.json 파일이 생성되었습니다.")
