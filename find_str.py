import os

# Check strings in certain folders
def search_string_in_folder(folder_path, target_string):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # Only search cases for extension .cpp and .hpp.
            # if not (file.endswith(".cpp")):
            #   continue
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

# Select folder path
folder_path = '/home/nokdujeon/kangseok/ILLIXR'
# folder_path = '/home/nokdujeon/Downloads/godot-4.4.1-stable'

target_string = 'log_frame_time_diff'

search_string_in_folder(folder_path, target_string)
