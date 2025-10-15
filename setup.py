# file: setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# Hàm để tìm tất cả các file .py trong dự án
def find_py_files(path):
    py_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

# Danh sách các thư mục chứa mã nguồn của bạn
source_folders = ['core', 'gui', 'utils']
all_source_files = []
for folder in source_folders:
    all_source_files.extend(find_py_files(folder))

# Thêm file app_lite.py vào danh sách cần biên dịch
all_source_files.append('app_lite.py')

# Tạo danh sách các Extension module cho Cython
extensions = [
    Extension(
        name=os.path.splitext(file.replace(os.path.sep, '.'))[0],
        sources=[file]
    )
    for file in all_source_files
]

# Cấu hình setup
setup(
    name="Shooting App Modules",
    ext_modules=cythonize(
        extensions,
        compiler_directives={'language_level': "3"}
    )
)