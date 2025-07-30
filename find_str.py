import os

def search_string_in_folder(folder_path, target_string):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, start=1):
                        if target_string in line:
                            print(f"[{file_path}] Line {line_num}: {line.strip()}")
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Failed to Open File: {file_path} - {e}")

folder_path = '/home/nokdujeon/kangseok/ILLIXR/build/_deps'
target_string = '[TIME'

search_string_in_folder(folder_path, target_string)

