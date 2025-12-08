#!/usr/bin/env python3
"""
Проверка синтаксиса всех Python файлов перед коммитом
"""
import ast
import sys
import os

def check_syntax(file_path):
    """Проверяет синтаксис Python файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError в {file_path}:{e.lineno}: {e.msg}"
    except IndentationError as e:
        return False, f"IndentationError в {file_path}:{e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Ошибка в {file_path}: {str(e)}"

def main():
    """Проверяет все Python файлы в проекте"""
    python_files = [
        'app.py',
        'google_sheets_helper.py',
        'qdrant_helper.py'
    ]
    
    errors = []
    for file_path in python_files:
        if os.path.exists(file_path):
            success, error = check_syntax(file_path)
            if not success:
                errors.append(error)
                print(f"❌ {error}")
            else:
                print(f"✅ {file_path} - синтаксис корректен")
        else:
            print(f"⚠️ {file_path} - файл не найден")
    
    if errors:
        print(f"\n❌ Найдено {len(errors)} ошибок!")
        sys.exit(1)
    else:
        print(f"\n✅ Все файлы синтаксически корректны!")
        sys.exit(0)

if __name__ == "__main__":
    main()
