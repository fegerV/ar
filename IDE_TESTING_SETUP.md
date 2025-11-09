# 🛠️ Настройка IDE для тестирования Vertex AR

Руководство по настройке популярных IDE и редакторов для удобного запуска и отладки тестов.

---

## 📋 Содержание

1. [VS Code](#vs-code)
2. [PyCharm](#pycharm)
3. [Vim/Neovim](#vimneovim)
4. [Sublime Text](#sublime-text)
5. [Terminal-based testing](#terminal-based-testing)

---

## 🔵 VS Code

### Установка расширений

Рекомендуемые расширения:

```bash
# Python
code --install-extension ms-python.python

# Test Explorer
code --install-extension littlefoxteam.vscode-python-test-adapter

# Coverage Gutters (показывает покрытие в редакторе)
code --install-extension ryanluker.vscode-coverage-gutters
```

### Настройка settings.json

Откройте `.vscode/settings.json` и добавьте:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    ".",
    "-v",
    "--tb=short",
    "--disable-warnings"
  ],
  "python.testing.autoTestDiscoverOnSaveEnabled": true,
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "coverage-gutters.coverageFileNames": [
    ".coverage",
    "coverage.xml",
    "lcov.info"
  ],
  "coverage-gutters.showLineCoverage": true,
  "coverage-gutters.showRulerCoverage": true
}
```

### Создание launch.json для отладки

Создайте `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "vertex-ar.app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Debug Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-vv",
        "-s",
        "${file}"
      ],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: Debug Current Test",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-vv",
        "-s",
        "${file}::${selectedText}"
      ],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

### Создание tasks.json для быстрых задач

Создайте `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run All Tests",
      "type": "shell",
      "command": "pytest -v",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Run Tests with Coverage",
      "type": "shell",
      "command": "pytest --cov=vertex-ar --cov-report=html",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Run Quick Tests",
      "type": "shell",
      "command": "./quick_test.sh quick",
      "group": "test"
    },
    {
      "label": "Run Demo",
      "type": "shell",
      "command": "./quick_test.sh demo",
      "group": "test"
    },
    {
      "label": "Start FastAPI Server",
      "type": "shell",
      "command": "cd vertex-ar && uvicorn app.main:app --reload",
      "isBackground": true,
      "problemMatcher": {
        "pattern": {
          "regexp": "."
        },
        "background": {
          "activeOnStart": true,
          "beginsPattern": "Started server process",
          "endsPattern": "Application startup complete"
        }
      }
    }
  ]
}
```

### Использование в VS Code

**Запуск тестов:**
1. Откройте тестовый файл
2. Нажмите на иконку "Testing" в боковой панели
3. Увидите дерево всех тестов
4. Запустите отдельный тест кликом на ▶️
5. Или запустите все: `Ctrl+Shift+P` → "Test: Run All Tests"

**Отладка теста:**
1. Установите breakpoint (красная точка слева от номера строки)
2. Правый клик на тесте → "Debug Test"
3. Используйте панель отладки для Step Over/Into/Out

**Просмотр покрытия:**
1. Запустите: `pytest --cov=vertex-ar --cov-report=xml`
2. Нажмите `Ctrl+Shift+P` → "Coverage Gutters: Display Coverage"
3. Увидите цветные полосы слева (зелёный = покрыт, красный = нет)

**Горячие клавиши:**
- `Ctrl+Shift+P` → "Test: Run All Tests"
- `Ctrl+Shift+P` → "Test: Run Failed Tests"
- `F5` → Start Debugging

---

## 🟢 PyCharm

### Настройка интерпретатора

1. `File` → `Settings` → `Project` → `Python Interpreter`
2. Добавьте интерпретатор из `.venv/bin/python`
3. Убедитесь что все пакеты из `requirements-dev.txt` установлены

### Настройка pytest

1. `File` → `Settings` → `Tools` → `Python Integrated Tools`
2. В разделе "Testing":
   - Default test runner: `pytest`
3. Примените изменения

### Создание Run Configuration для тестов

**Для всех тестов:**
1. `Run` → `Edit Configurations`
2. `+` → `Python tests` → `pytest`
3. Настройте:
   - Name: `All Tests`
   - Target: `Script path` → выберите корень проекта
   - Options: `-v --tb=short`
   - Working directory: корень проекта
4. Apply

**Для быстрых тестов:**
1. Создайте новую конфигурацию как выше
2. Name: `Quick Tests`
3. Options: `-v -m "not slow"`

**Для тестов с покрытием:**
1. Создайте конфигурацию
2. Options: `--cov=vertex-ar --cov-report=html`

### Создание Run Configuration для FastAPI

1. `Run` → `Edit Configurations`
2. `+` → `Python`
3. Настройте:
   - Name: `FastAPI Server`
   - Module name: `uvicorn`
   - Parameters: `app.main:app --reload --host 0.0.0.0 --port 8000`
   - Working directory: `vertex-ar/`
   - Environment variables: загрузите из `.env`
4. Apply

### Использование в PyCharm

**Запуск тестов:**
1. Правый клик на тестовом файле → `Run 'pytest in test_*.py'`
2. Или правый клик на папке `tests` → `Run 'pytest in tests'`
3. Или используйте зелёную стрелку ▶️ рядом с тестом

**Отладка:**
1. Установите breakpoint (клик слева от номера строки)
2. Правый клик на тесте → `Debug 'test_name'`
3. Используйте панель отладки

**Просмотр покрытия:**
1. `Run` → `Run 'All Tests' with Coverage`
2. PyCharm автоматически покажет покрытие в редакторе
3. Откройте Coverage Tool Window для детального отчёта

**Горячие клавиши:**
- `Ctrl+Shift+F10` → Run test under cursor
- `Shift+F10` → Run last configuration
- `Shift+F9` → Debug last configuration
- `Ctrl+Shift+F9` → Debug test under cursor

### Полезные плагины для PyCharm

- **Requirements** - подсветка requirements.txt
- **Markdown** - preview для .md файлов
- **.env files support** - поддержка .env файлов

---

## 🟣 Vim/Neovim

### Установка плагинов (vim-plug)

Добавьте в `.vimrc` или `init.vim`:

```vim
call plug#begin()

" Python support
Plug 'davidhalter/jedi-vim'
Plug 'dense-analysis/ale'  " Linting
Plug 'vim-test/vim-test'   " Test runner

" Optional but recommended
Plug 'preservim/nerdtree'
Plug 'tpope/vim-fugitive'  " Git integration

call plug#end()
```

Установите плагины:
```vim
:PlugInstall
```

### Настройка vim-test

Добавьте в `.vimrc`:

```vim
" Test strategy
let test#strategy = "neovim"  " or "vimterminal" for vim
let test#python#runner = 'pytest'

" Test shortcuts
nmap <silent> <leader>t :TestNearest<CR>
nmap <silent> <leader>T :TestFile<CR>
nmap <silent> <leader>a :TestSuite<CR>
nmap <silent> <leader>l :TestLast<CR>
nmap <silent> <leader>g :TestVisit<CR>

" Pytest options
let test#python#pytest#options = '-v --tb=short'
```

### Настройка ALE (linting)

```vim
" ALE configuration
let g:ale_linters = {
\   'python': ['flake8', 'mypy'],
\}
let g:ale_fixers = {
\   'python': ['black', 'isort'],
\}
let g:ale_fix_on_save = 1
```

### Использование

**Запуск тестов:**
- `<leader>t` → Run nearest test
- `<leader>T` → Run all tests in file
- `<leader>a` → Run all tests
- `<leader>l` → Run last test

**Навигация:**
- `:NERDTree` → Открыть дерево файлов
- `/` в NERDTree → Поиск файла

**Команды:**
```vim
:terminal pytest -v
:terminal ./quick_test.sh demo
```

---

## 🟠 Sublime Text

### Установка Package Control

1. `Ctrl+Shift+P` → `Install Package Control`
2. Перезапустите Sublime

### Установка пакетов

`Ctrl+Shift+P` → `Package Control: Install Package`

Установите:
- **Anaconda** - Python IDE features
- **Python Test** - Test runner
- **SublimeLinter** - Linting framework
- **SublimeLinter-flake8** - Python linting

### Настройка проекта

Создайте файл `vertex-ar.sublime-project`:

```json
{
  "folders": [
    {
      "path": "."
    }
  ],
  "settings": {
    "python_interpreter": ".venv/bin/python",
    "test_command": "pytest -v",
    "anaconda_linting": true,
    "pep8": true
  },
  "build_systems": [
    {
      "name": "Run Tests",
      "shell_cmd": "pytest -v",
      "working_dir": "${project_path}"
    },
    {
      "name": "Run Quick Tests",
      "shell_cmd": "./quick_test.sh quick",
      "working_dir": "${project_path}"
    },
    {
      "name": "FastAPI Server",
      "shell_cmd": "cd vertex-ar && uvicorn app.main:app --reload",
      "working_dir": "${project_path}"
    }
  ]
}
```

Откройте проект: `Project` → `Open Project` → выберите `.sublime-project`

### Использование

**Запуск тестов:**
1. `Ctrl+B` → выберите "Run Tests"
2. Результаты появятся в нижней панели

**Быстрая сборка:**
- `Ctrl+Shift+B` → выберите build систему
- `Ctrl+B` → запустит последнюю выбранную

---

## 💻 Terminal-based testing

### Настройка tmux для эффективного тестирования

Создайте `.tmux.conf`:

```bash
# ~/.tmux.conf

# Split panes using | and -
bind | split-window -h
bind - split-window -v

# Quick pane switching
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# Enable mouse
set -g mouse on

# Start window numbering at 1
set -g base-index 1

# Reload config
bind r source-file ~/.tmux.conf
```

### Рабочий процесс с tmux

```bash
# Создайте новую сессию
tmux new -s vertexar

# Разделите окно:
# Ctrl+b |  - вертикально
# Ctrl+b -  - горизонтально

# Пример layout:
# ┌─────────────┬──────────────┐
# │             │              │
# │   Editor    │   Server     │
# │             │              │
# ├─────────────┼──────────────┤
# │             │              │
# │   Tests     │   Logs       │
# │             │              │
# └─────────────┴──────────────┘

# В панели Server:
cd vertex-ar && uvicorn app.main:app --reload

# В панели Tests:
watch -n 2 'pytest -v --tb=line'

# В панели Logs:
tail -f logs/app.log
```

### Настройка watch для автоматического перезапуска

```bash
# Установите entr
sudo apt install entr  # Ubuntu/Debian
brew install entr      # macOS

# Автоматический запуск тестов при изменении файлов
find vertex-ar -name "*.py" | entr pytest -v

# Или используйте pytest-watch
pip install pytest-watch
ptw -- -v
```

### Полезные alias'ы для .bashrc/.zshrc

```bash
# Добавьте в ~/.bashrc или ~/.zshrc

# Vertex AR aliases
alias venv='source .venv/bin/activate'
alias vtest='pytest -v'
alias vtest-quick='pytest -m "not slow" -v'
alias vtest-cov='pytest --cov=vertex-ar --cov-report=html'
alias vtest-watch='ptw -- -v'
alias vrun='cd vertex-ar && uvicorn app.main:app --reload'
alias vdemo='./quick_test.sh demo'
alias vclean='./quick_test.sh clean'

# Fast navigation
alias vcd='cd /path/to/vertex-ar'
alias vtests='cd /path/to/vertex-ar/vertex-ar/tests'
```

Примените изменения:
```bash
source ~/.bashrc  # или source ~/.zshrc
```

---

## 🚀 Интеграция с Git

### Pre-commit hooks

Создайте `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Pre-commit hook для Vertex AR

echo "Running pre-commit checks..."

# Активируйте виртуальное окружение
source .venv/bin/activate

# Форматирование
echo "Formatting code with black..."
black vertex-ar/ --check --quiet
if [ $? -ne 0 ]; then
    echo "❌ Code formatting failed. Run 'black vertex-ar/'"
    exit 1
fi

# Импорты
echo "Checking imports with isort..."
isort vertex-ar/ --check-only --quiet
if [ $? -ne 0 ]; then
    echo "❌ Import sorting failed. Run 'isort vertex-ar/'"
    exit 1
fi

# Линтинг
echo "Linting with flake8..."
flake8 vertex-ar/ --count --select=E9,F63,F7,F82 --show-source --statistics
if [ $? -ne 0 ]; then
    echo "❌ Linting failed"
    exit 1
fi

# Быстрые тесты
echo "Running quick tests..."
pytest -m "not slow" -q
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

echo "✅ All checks passed!"
exit 0
```

Сделайте исполняемым:
```bash
chmod +x .git/hooks/pre-commit
```

Или используйте pre-commit framework:
```bash
pip install pre-commit
pre-commit install
```

---

## 📊 Continuous Testing

### Настройка pytest-watch

```bash
pip install pytest-watch

# Базовое использование
ptw

# С дополнительными опциями
ptw -- -v --tb=short

# Игнорировать определённые файлы
ptw --ignore ./migrations --ignore ./docs
```

### Настройка Guard (Ruby tool, но очень мощный)

```bash
# Установите Ruby и Guard
gem install guard guard-shell

# Создайте Guardfile
guard init shell

# Отредактируйте Guardfile
```

Пример `Guardfile`:

```ruby
guard :shell do
  watch(%r{vertex-ar/.*\.py$}) do |m|
    `pytest #{m[0]} -v`
  end
  
  watch(%r{vertex-ar/tests/.*\.py$}) do |m|
    `pytest #{m[0]} -v`
  end
end
```

---

## 🎯 Рекомендации по рабочему процессу

### Workflow 1: TDD (Test-Driven Development)

```bash
# 1. Откройте два окна/панели:
#    - Слева: редактор
#    - Справа: terminal с pytest-watch

# В правом окне:
ptw -- -v

# 2. Напишите тест (он упадёт - red)
# 3. Напишите минимальный код для прохождения (green)
# 4. Рефакторинг (refactor)
# 5. Повторите
```

### Workflow 2: Quick Feedback Loop

```bash
# Terminal 1: Приложение
cd vertex-ar && uvicorn app.main:app --reload

# Terminal 2: Автоматические тесты
find . -name "*.py" | entr pytest -v

# Terminal 3: Ручные запросы
# curl/httpie команды
```

### Workflow 3: Coverage-Driven

```bash
# 1. Запустите тесты с покрытием
pytest --cov=vertex-ar --cov-report=html

# 2. Откройте отчёт
open htmlcov/index.html

# 3. Найдите непокрытые строки
# 4. Напишите тесты для них
# 5. Повторите
```

---

## 🛠️ Debugging Tips

### VS Code debugging tricks

```python
# Используйте условные breakpoints
# Правый клик на breakpoint → Edit Breakpoint → Expression
# Например: user.id == 123

# Используйте logpoints (не останавливают выполнение)
# Правый клик → Add Logpoint
# Сообщение: User: {user.username}

# Debug Console
# Во время остановки на breakpoint можно выполнять код:
print(user.__dict__)
len(clients)
```

### PyCharm debugging tricks

```python
# Evaluate Expression: Alt+F8
# Смотрите значения переменных во время отладки

# Watches
# Добавьте выражения для постоянного мониторинга

# Drop Frame
# Вернуться на фрейм назад в стеке вызовов
```

### Terminal debugging with pdb

```python
# В коде теста:
def test_something():
    result = some_function()
    
    # Остановка здесь
    import pdb; pdb.set_trace()
    
    assert result == expected

# Команды pdb:
# n - next line
# s - step into
# c - continue
# l - list code
# p variable - print variable
# pp variable - pretty print
# q - quit
```

---

## 📚 Дополнительные ресурсы

- [VS Code Python Testing](https://code.visualstudio.com/docs/python/testing)
- [PyCharm Testing](https://www.jetbrains.com/help/pycharm/testing-your-first-python-application.html)
- [vim-test documentation](https://github.com/vim-test/vim-test)
- [tmux Cheat Sheet](https://tmuxcheatsheet.com/)

---

**Выберите свой инструмент и начните тестировать эффективно! 🚀**
