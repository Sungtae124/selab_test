import json
import re
import os
from server import Server
import bug_list
from collections import deque

# 주석 추출 함수
def extract_comments(lines, m_line_idx):
    comments = deque()
    inside_comment = False
    for i in range(m_line_idx - 1, -1, -1):
        line = lines[i]
        if line.strip().endswith("*/") or line.strip().startswith("//"):
            inside_comment = True
        if inside_comment:
            comments.appendleft(line.replace("/**", "").replace("*/", "").replace("//", ""))
        if line.strip().startswith("/*") or line.strip().startswith("//"):
            break
    return "\n".join(comments)

# 커버된 라인에서 스니펫 추출
def extract_field_snippets(file_lines, class_name, src_path, covered_lines):
    fields = []
    field_pattern = re.compile(r'^\s*(public|protected|private)?\s*(static|final)?\s*[\w\<\>\[\]]+\s+\w+\s*=\s*.*;')
    i = 0
    while i < len(file_lines):
        line = file_lines[i]
        match = field_pattern.match(line)
        if match:
            begin_line = i + 1
            snippet = line.strip()
            i += 1
            while i < len(file_lines) and not file_lines[i].strip().endswith(";"):
                snippet += "\n" + file_lines[i].strip()
                i += 1
            if i < len(file_lines):
                snippet += "\n" + file_lines[i].strip()
                end_line = i + 1
                if any(begin_line <= line <= end_line for line in covered_lines):
                    field = {
                        "class_name": class_name,
                        "src_path": src_path,
                        "signature": match.group(0).split("=")[0].strip(),
                        "snippet": snippet,
                        "begin_line": begin_line,
                        "end_line": end_line,
                        "comment": extract_comments(file_lines, begin_line)
                    }
                    fields.append(field)
        i += 1
    return fields

# coverage.json 파일을 분석하여 관련 파일 및 라인 정보를 추출
def analyze_coverage(coverage_data):
    snippets_info = []
    for entry in coverage_data:
        class_name = entry['className']
        covered_lines = sorted(entry['covered'])
        snippets_info.append({
            "class_name": class_name,
            "covered_lines": covered_lines
        })
    return snippets_info

# 경로 내에서 특정 파일을 찾는 함수
def find_java_file(base_path, class_name):
    parts = class_name.split('.')
    file_name = parts[-1] + ".java"
    for root, dirs, files in os.walk(base_path):
        if file_name in files:
            return os.path.join(root, file_name)
    return None

def select_src_path(bug_id, class_name, server, remote_dir):
    # 기본 경로 설정
    default_path = f"{remote_dir}/result/src/{class_name.replace('.', '/')}.java"
    try:
        server.read_remote_file(default_path)
        return default_path
    except FileNotFoundError:
        pass
    
    # result, fixed, buggy 디렉토리의 모든 하위 디렉토리 탐색
    for sub_dir in ['result', 'fixed', 'buggy']:
        base_path = os.path.join(remote_dir, sub_dir)
        src_path = find_java_file(base_path, class_name)
        if src_path:
            return src_path
    
    raise FileNotFoundError(f"Source file for {class_name} in bug {bug_id} not found in any of the paths.")

if __name__ == '__main__':
    bug_id_list = bug_list.get_d4j_bug_list()
    server = Server()

    for bug_id in bug_id_list:
        print(f"Generating field snippets for {bug_id}...", end='')

        remote_dir = f'/data/bug_db/subjects/defects4j/{bug_id}'
        
        try:
            # coverage.json 파일 읽기
            coverage_path = f'{remote_dir}/coverage.json'
            coverage_content = server.read_remote_file(coverage_path)
            coverage_data = json.loads(coverage_content)["coverage"]

            # coverage.json 분석하여 관련 파일 및 라인 정보 추출
            snippets_info = analyze_coverage(coverage_data)

            field_snippets = []
            for info in snippets_info:
                src_path = select_src_path(bug_id, info['class_name'], server, remote_dir)
                if src_path:
                    print(f"Java file found: {src_path}")  # 로그로 파일 경로 출력

                    file_content = server.read_remote_file(src_path)
                    file_lines = file_content.splitlines()

                    class_name = info['class_name']
                    covered_lines = info['covered_lines']
                    field_snippets_data = extract_field_snippets(file_lines, class_name, src_path, covered_lines)

                    field_snippets.extend(field_snippets_data)

            # JSON 파일 저장
            output_path = f'field_snippet_{bug_id}.json'
            with open(output_path, 'w') as f:
                json.dump(field_snippets, f, indent=4)

            print(f"Field snippets for {bug_id} generated.")

        except FileNotFoundError as e:
            print(f"Error loading files for {bug_id}: {e}")
        except Exception as e:
            print(f"An error occurred for {bug_id}: {e}")