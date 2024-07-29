import json
from server import Server
import bug_list
import re
from collections import deque


# 필드 정보 추출 함수
def extract_field_info(file_lines, class_name, src_path):
    fields = []
    # Regular expression to find method definitions
    method_pattern = re.compile(
        r'^\s*(public|protected|private)?\s*(static)?\s*[\w\<\>\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*\{')

    for i, line in enumerate(file_lines):
        match = method_pattern.match(line)
        if match:
            method_name = f"{match.group(3)}({match.group(4).strip()})"
            snippet = line.strip()
            j = i + 1
            child_range = []
            while file_lines[j].strip().endswith(";") or not file_lines[j].strip():
                snippet += "\n" + file_lines[j].strip()
                start_col = 0
                for k in range(len(file_lines[j])):
                    if file_lines[j][k] != ' ':
                        start_col = k + 1
                        break

                child_range.append(f'(line {j + 1},col {start_col})-(line {j + 1},col {len(file_lines[j])})')
                j += 1
            snippet += "\n" + file_lines[j].strip()
            fields.append({
                "class_name": class_name,
                "child_classes": [],  # TODO: 뭐가 들어가야하는지 잘 모르겠음.
                "src_path": src_path,
                # autoFL에서는 StrBuilderTest(java.lang.String)처럼 파라미터 형식이 들어가는데 어떻게 하는지 모르겠음.
                # 일단 StrBuilderTest(String name)과 같이 그냥 코드 그대로 넣음
                "signature": f'{class_name}.{method_name}',
                "snippet": snippet,
                "begin_line": i + 1,
                "end_line": j + 1,
                "comment": extract_comments(file_lines, i),  # 주석 추출
                "child_ranges": child_range
            })

    return fields


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


if __name__ == '__main__':

    bug_id_list = bug_list.get_d4j_bug_list()

    for bug_id in bug_id_list:
        print(f"Generating field snippet for {bug_id}...", end='')

        # 서버 접속 정보 설정
        remote_dir = f'/data/bug_db/subjects/defects4j/{bug_id}'

        server = Server()

        # JSON 데이터 로드
        try:
            test_path = f'{remote_dir}{select_test_path(bug_id)}'
            npe_traces_content = json.loads(server.read_remote_file(remote_dir + '/npe.traces.json'))
            test_classes = set()
            fields = []
            for trace in npe_traces_content['npe.traces']:
                test_classes.add(trace['test.class'])

            for test_class in test_classes:
                test_file_content = server.read_remote_file(f'{test_path}/{test_class.replace(".", "/")}.java')
                test_file_lines = test_file_content.splitlines()

                fields.append(
                    extract_field_info(test_file_lines, test_class,
                                       f'{test_path}/{test_class.replace(".", "/")}.java'.split('fixed/')[-1]))

            # JSON 파일 저장
            with open(f'../rst/{bug_id}/test_snippet.json', 'w') as f:
                json.dump(fields, f, indent=4)

            print("Done.")

        except FileNotFoundError as e:
            print(f"Error loading files: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
