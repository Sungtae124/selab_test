import os
import bug_list
from server import Server


def main():
    bug_ids = bug_list.get_d4j_bug_list()
    server = Server()

    for bug_id in bug_ids:
        try:
            print(f"Processing bug {bug_id}...", end='')

            remote_dir = f'/data/bug_db/subjects/defects4j/{bug_id}'

            failing_tests = ""

            if 'stack_traces.txt' in server.list_remote_files(f'{remote_dir}'):
                stack_traces = server.read_remote_file(f'{remote_dir}/stack_traces.txt').split('\n\n')
                for stack_trace in stack_traces:
                    if not stack_trace.strip():
                        continue
                    first_line = stack_trace.split('\n')[0]
                    test_method, test_class = first_line[:first_line.find(')')].split('(')
                    failing_tests += f'--- {test_class}::{test_method}\n'
                    lines = stack_trace.split('\n')[1:]
                    start_line = 0
                    for i in range(len(lines)):
                        if 'NullPointerException' in lines[i]:
                            start_line = i + 1
                            failing_tests += 'java.lang.NullPointerException\n'
                            break

                    for i in range(start_line, len(lines)):
                        failing_tests += f'{lines[i]}\n'

            if not os.path.exists(f'./rst/{bug_id}'):
                os.makedirs(f'./rst/{bug_id}')

            with open(f'./rst/{bug_id}/failed_tests', 'w') as f:
                f.write(failing_tests)

            print("Done.")

        except Exception as e:
            print(f"An error occurred: {e}")
            raise


if __name__ == '__main__':
    main()
