import sys
import os
import json
import re
import sqlite3
import mimetypes
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QTabWidget, QFileDialog,
    QMessageBox, QTreeView, QSplitter, QWidget, QVBoxLayout,
    QToolBar, QStatusBar, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QDialog, QTextEdit, QCheckBox, QSpinBox,
    QComboBox, QDialogButtonBox, QPlainTextEdit, QInputDialog,
    QListWidget, QListWidgetItem, QMenu
)
from PyQt6.QtCore import Qt, QDir, QProcess, QSize, QRect, QTimer, QByteArray
from PyQt6.QtGui import (
    QFont, QColor, QTextFormat, QPainter, QTextCharFormat,
    QSyntaxHighlighter, QTextCursor, QKeySequence, QAction,
    QFileSystemModel, QTextOption, QIcon, QPixmap
)


# ===================== SETTINGS =====================
class SettingsManager:
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.recent_file = os.path.join(self.config_dir, "recent.json")
        self.defaults = {
            "theme": "dark",
            "font_size": 14,
            "tab_size": 4,
            "word_wrap": False,
            "line_numbers": True,
            "python_path": "python",
            "auto_save": False,
            "auto_save_interval": 60,
            "encoding": "utf-8",
            "show_whitespace": False,
            "minimap": False,
            "recent_files_count": 10
        }
        self.settings = {}
        self.recent_files = []
        self.load()

    def _get_config_dir(self):
        if os.name == "nt":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        else:
            base = os.path.expanduser("~")
        config_dir = os.path.join(base, ".mini-code-editor")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def load(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings = {**self.defaults, **loaded}
            else:
                self.settings = dict(self.defaults)
                self.save()
        except Exception:
            self.settings = dict(self.defaults)

        try:
            if os.path.exists(self.recent_file):
                with open(self.recent_file, "r", encoding="utf-8") as f:
                    self.recent_files = json.load(f)
        except Exception:
            self.recent_files = []

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def save_recent(self):
        try:
            with open(self.recent_file, "w", encoding="utf-8") as f:
                json.dump(self.recent_files, f, indent=4)
        except Exception:
            pass

    def add_recent_file(self, path):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        max_files = self.settings.get("recent_files_count", 10)
        self.recent_files = self.recent_files[:max_files]
        self.save_recent()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value


# ===================== HIGHLIGHTERS =====================
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "return", "if", "elif", "else", "for", "while",
                     "import", "from", "as", "try", "except", "finally", "with",
                     "lambda", "pass", "break", "continue", "in", "not", "and", "or",
                     "is", "None", "True", "False", "yield", "global", "raise", "del"]
        for word in keywords:
            self.rules.append((rf"\b{word}\b", keyword_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r'"[^"\\]*(?:\\.[^"\\]*)*"', string_format))
        self.rules.append((r"'[^'\\]*(?:\\.[^'\\]*)*'", string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"#[^\n]*", comment_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.rules.append((r"\b[0-9]+\b", number_format))
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa"))
        self.rules.append((r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()", function_format))
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#d7ba7d"))
        self.rules.append((r"@[A-Za-z_][A-Za-z0-9_]*", decorator_format))
        self.rules.append((r"\b(self|cls)\b", function_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class JavaScriptHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["var", "let", "const", "function", "return", "if", "else",
                     "for", "while", "do", "switch", "case", "break", "continue",
                     "new", "class", "extends", "super", "this", "typeof", "instanceof",
                     "try", "catch", "finally", "throw", "async", "await", "import",
                     "export", "default", "null", "undefined", "true", "false", "of", "in"]
        for word in keywords:
            self.rules.append((rf"\b{word}\b", keyword_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r'"[^"\\]*(?:\\.[^"\\]*)*"', string_format))
        self.rules.append((r"'[^'\\]*(?:\\.[^'\\]*)*'", string_format))
        self.rules.append((r"`[^`]*`", string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"//[^\n]*", comment_format))
        self.rules.append((r"/\*.*?\*/", comment_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.rules.append((r"\b[0-9]+\b", number_format))
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa"))
        self.rules.append((r"\b[A-Za-z_$][A-Za-z0-9_$]*(?=\s*\()", function_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class HTMLHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor("#569cd6"))
        self.rules.append((r"</?[a-zA-Z][a-zA-Z0-9-]*", tag_format))
        attr_format = QTextCharFormat()
        attr_format.setForeground(QColor("#9cdcfe"))
        self.rules.append((r"[a-zA-Z-]+(?=\s*=)", attr_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r'"[^"]*"', string_format))
        self.rules.append((r"'[^']*'", string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"<!--.*?-->", comment_format))
        entity_format = QTextCharFormat()
        entity_format.setForeground(QColor("#d7ba7d"))
        self.rules.append((r"&[a-zA-Z]+;", entity_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class CSSHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        selector_format = QTextCharFormat()
        selector_format.setForeground(QColor("#d7ba7d"))
        self.rules.append((r"[.#]?[a-zA-Z][a-zA-Z0-9_-]*", selector_format))
        property_format = QTextCharFormat()
        property_format.setForeground(QColor("#9cdcfe"))
        self.rules.append((r"[a-zA-Z-]+(?=\s*:)", property_format))
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#ce9178"))
        self.rules.append((r":\s*[^;{}]+", value_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"/\*.*?\*/", comment_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.rules.append((r"\b[0-9]+(\.[0-9]+)?(px|em|rem|%|vh|vw|pt)?\b", number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class CHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["int", "float", "double", "char", "void", "return", "if", "else",
                     "for", "while", "do", "switch", "case", "break", "continue",
                     "struct", "union", "enum", "typedef", "sizeof", "const", "static",
                     "extern", "register", "volatile", "unsigned", "signed", "long",
                     "short", "include", "define", "NULL", "true", "false"]
        for word in keywords:
            self.rules.append((rf"\b{word}\b", keyword_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r'"[^"\\]*(?:\\.[^"\\]*)*"', string_format))
        self.rules.append((r"'[^'\\]*(?:\\.[^'\\]*)*'", string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"//[^\n]*", comment_format))
        self.rules.append((r"/\*.*?\*/", comment_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.rules.append((r"\b[0-9]+\b", number_format))
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa"))
        self.rules.append((r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()", function_format))
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(QColor("#c586c0"))
        self.rules.append((r"^#\s*[a-zA-Z]+", preprocessor_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class CppHighlighter(CHighlighter):
    def __init__(self, document):
        super().__init__(document)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        cpp_keywords = ["class", "namespace", "template", "typename", "public", "private",
                         "protected", "virtual", "override", "final", "new", "delete",
                         "this", "friend", "operator", "inline", "using", "std", "cout",
                         "cin", "endl", "string", "vector", "map", "auto", "nullptr",
                         "constexpr", "static_cast", "dynamic_cast", "reinterpret_cast"]
        for word in cpp_keywords:
            self.rules.append((rf"\b{word}\b", keyword_format))


class JSONHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#9cdcfe"))
        self.rules.append((r'"[^"]*"\s*:', key_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r'"[^"]*"', string_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.rules.append((r"\b[0-9]+(\.[0-9]+)?\b", number_format))
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#569cd6"))
        self.rules.append((r"\b(true|false|null)\b", bool_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        heading_format = QTextCharFormat()
        heading_format.setForeground(QColor("#569cd6"))
        heading_format.setFontWeight(QFont.Weight.Bold)
        self.rules.append((r"^#{1,6}\s.*", heading_format))
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Weight.Bold)
        self.rules.append((r"\*\*[^*]+\*\*", bold_format))
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self.rules.append((r"\*[^*]+\*", italic_format))
        code_format = QTextCharFormat()
        code_format.setForeground(QColor("#ce9178"))
        code_format.setFont(QFont("Consolas", 10))
        self.rules.append((r"`[^`]+`", code_format))
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("#3794ff"))
        link_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        self.rules.append((r"\[.*?\]\(.*?\)", link_format))
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#d7ba7d"))
        self.rules.append((r"^[\s]*[-*+]\s", list_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class SQLHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE",
                     "TABLE", "INTO", "VALUES", "SET", "ALTER", "DROP", "INDEX", "VIEW",
                     "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND", "OR", "NOT",
                     "IN", "LIKE", "BETWEEN", "ORDER", "BY", "GROUP", "HAVING", "LIMIT",
                     "OFFSET", "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MAX", "MIN",
                     "NULL", "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CASCADE",
                     "INTEGER", "TEXT", "REAL", "BLOB", "BOOLEAN", "DATE", "TIMESTAMP"]
        for word in keywords:
            self.rules.append((rf"\b{word}\b", keyword_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r"'[^']*'", string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"--[^\n]*", comment_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.rules.append((r"\b[0-9]+\b", number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class BashHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["if", "then", "else", "elif", "fi", "for", "while", "do", "done",
                     "case", "esac", "function", "return", "exit", "export", "source",
                     "echo", "read", "cd", "ls", "rm", "cp", "mv", "mkdir", "chmod"]
        for word in keywords:
            self.rules.append((rf"\b{word}\b", keyword_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.rules.append((r'"[^"]*"', string_format))
        self.rules.append((r"'[^']*'", string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        comment_format.setFontItalic(True)
        self.rules.append((r"#[^\n]*", comment_format))
        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor("#9cdcfe"))
        self.rules.append((r"\$[A-Za-z_][A-Za-z0-9_]*", variable_format))
        self.rules.append((r"\$\{[^}]+\}", variable_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ====================== LINE NUMBER AREA =====================
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


# ====================== SEARCH BAR =====================
class SearchBar(QWidget):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._search)
        self.search_input.returnPressed.connect(self._search_next)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace...")
        self.replace_input.setFixedWidth(150)
        self.replace_input.returnPressed.connect(self._replace_all)

        self.next_btn = QPushButton("▼")
        self.next_btn.setFixedWidth(28)
        self.next_btn.clicked.connect(self._search_next)

        self.prev_btn = QPushButton("▲")
        self.prev_btn.setFixedWidth(28)
        self.prev_btn.clicked.connect(self._search_prev)

        self.replace_btn = QPushButton("R")
        self.replace_btn.setFixedWidth(28)
        self.replace_btn.setToolTip("Replace current")
        self.replace_btn.clicked.connect(self._replace_current)

        self.replace_all_btn = QPushButton("RA")
        self.replace_all_btn.setFixedWidth(30)
        self.replace_all_btn.setToolTip("Replace all")
        self.replace_all_btn.clicked.connect(self._replace_all)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedWidth(28)
        self.close_btn.clicked.connect(self.hide)

        self.match_label = QLabel("")
        self.match_label.setFixedWidth(70)

        layout.addWidget(self.search_input)
        layout.addWidget(self.replace_input)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.replace_btn)
        layout.addWidget(self.replace_all_btn)
        layout.addWidget(self.match_label)
        layout.addStretch()
        layout.addWidget(self.close_btn)

        self.setLayout(layout)
        self.hide()

    def show(self):
        super().show()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _search(self):
        text = self.search_input.text()
        if not text:
            self.match_label.setText("")
            return

        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)

        found = self.editor.find(text)
        if found:
            count = 1
            while self.editor.find(text):
                count += 1
            self.match_label.setText(f"{count} matches")
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text)
        else:
            self.match_label.setText("No matches")

    def _search_next(self):
        text = self.search_input.text()
        if text:
            self.editor.find(text)

    def _search_prev(self):
        text = self.search_input.text()
        if text:
            self.editor.find(text, QTextDocument.FindFlag.FindBackward)

    def _replace_current(self):
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if search_text and self.editor.textCursor().hasSelection():
            cursor = self.editor.textCursor()
            if cursor.selectedText() == search_text:
                cursor.insertText(replace_text)
                self._search_next()

    def _replace_all(self):
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if not search_text:
            return

        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)

        count = 0
        while self.editor.find(search_text):
            cursor = self.editor.textCursor()
            cursor.insertText(replace_text)
            count += 1

        self.match_label.setText(f"Replaced {count}")


# ====================== CODE EDITOR =====================
class CodeEditor(QPlainTextEdit):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings = settings_manager
        self.file_path = None
        self.highlighter = None
        self.auto_save_timer = None
        self.encoding = self.settings.get("encoding", "utf-8")

        self.line_number_area = LineNumberArea(self)
        self.search_bar = SearchBar(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(self._update_status)

        self.apply_settings()
        self.highlight_current_line()
        self._setup_auto_save()

    def _setup_auto_save(self):
        if self.settings.get("auto_save", False):
            interval = self.settings.get("auto_save_interval", 60) * 1000
            self.auto_save_timer = QTimer(self)
            self.auto_save_timer.timeout.connect(self._auto_save)
            self.auto_save_timer.start(interval)

    def _auto_save(self):
        if self.file_path and self.document().isModified():
            try:
                with open(self.file_path, "w", encoding=self.encoding) as f:
                    f.write(self.toPlainText())
                self.document().setModified(False)
            except Exception:
                pass

    def _update_status(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        chars = len(self.toPlainText())
        lines = self.blockCount()
        if hasattr(self, 'parent') and hasattr(self.parent(), 'status_label'):
            self.parent().status_label.setText(
                f"Ln {line}, Col {col} | {chars} chars, {lines} lines | {self.encoding}"
            )

    def set_file_path(self, path):
        self.file_path = path
        self._setup_highlighter(path)
        if path:
            self.settings.add_recent_file(path)

    def get_file_path(self):
        return self.file_path

    def set_encoding(self, encoding):
        self.encoding = encoding

    def get_encoding(self):
        return self.encoding

    def _setup_highlighter(self, path):
        if self.highlighter:
            self.highlighter.setDocument(None)
            self.highlighter.deleteLater()
            self.highlighter = None

        if not path:
            return
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        doc = self.document()
        if ext == "py":
            self.highlighter = PythonHighlighter(doc)
        elif ext == "js":
            self.highlighter = JavaScriptHighlighter(doc)
        elif ext == "html" or ext == "htm":
            self.highlighter = HTMLHighlighter(doc)
        elif ext == "css":
            self.highlighter = CSSHighlighter(doc)
        elif ext == "c":
            self.highlighter = CHighlighter(doc)
        elif ext == "cpp" or ext == "cc" or ext == "cxx":
            self.highlighter = CppHighlighter(doc)
        elif ext == "json":
            self.highlighter = JSONHighlighter(doc)
        elif ext == "md" or ext == "markdown":
            self.highlighter = MarkdownHighlighter(doc)
        elif ext == "sql":
            self.highlighter = SQLHighlighter(doc)
        elif ext == "sh" or ext == "bash":
            self.highlighter = BashHighlighter(doc)

    def apply_settings(self):
        font_size = self.settings.get("font_size", 14)
        font = QFont("Consolas", font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        tab_size = self.settings.get("tab_size", 4)
        self.setTabStopDistance(tab_size * self.fontMetrics().horizontalAdvance(" "))

        self.setWordWrapMode(
            QTextOption.WrapMode.WidgetWidth if self.settings.get("word_wrap", False)
            else QTextOption.WrapMode.NoWrap
        )

        self.line_number_area.setVisible(self.settings.get("line_numbers", True))

        theme = self.settings.get("theme", "dark")
        if theme == "dark":
            self.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: none;
                    selection-background-color: #264f78;
                }
            """)
        else:
            self.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: none;
                    selection-background-color: #add6ff;
                }
            """)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _=0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )
        self.search_bar.setGeometry(
            cr.right() - 450, cr.top(), 450, 30
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        theme = self.settings.get("theme", "dark")
        if theme == "dark":
            painter.fillRect(event.rect(), QColor("#252526"))
            color = QColor("#858585")
        else:
            painter.fillRect(event.rect(), QColor("#f3f3f3"))
            color = QColor("#666666")

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(color)
                painter.drawText(
                    0, top, self.line_number_area.width() - 5,
                    self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1)
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2a2d2e") if self.settings.get("theme", "dark") == "dark" else QColor("#e8f0fe")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def zoom_in(self):
        font = self.font()
        font.setPointSize(font.pointSize() + 1)
        self.setFont(font)
        self.update_line_number_area_width()

    def zoom_out(self):
        font = self.font()
        if font.pointSize() > 8:
            font.setPointSize(font.pointSize() - 1)
            self.setFont(font)
            self.update_line_number_area_width()

    def zoom_reset(self):
        font_size = self.settings.get("font_size", 14)
        font = QFont("Consolas", font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.update_line_number_area_width()

    def toggle_comment(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            text = self.toPlainText()
            lines = text[start:end].split('\n')
            commented = all(line.strip().startswith('#') for line in lines if line.strip())
            new_lines = []
            for line in lines:
                if commented:
                    new_lines.append(line.lstrip('#').lstrip())
                else:
                    new_lines.append('# ' + line)
            new_text = '\n'.join(new_lines)
            cursor.beginEditBlock()
            cursor.removeSelectedText()
            cursor.insertText(new_text)
            cursor.endEditBlock()
        else:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            line = self.textCursor().block().text()
            if line.strip().startswith('#'):
                new_line = line.lstrip('#').lstrip()
            else:
                new_line = '# ' + line
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(new_line)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.search_bar.show()
        elif event.key() == Qt.Key.Key_Slash and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_comment()
        else:
            super().keyPressEvent(event)


# ===================== DATABASE VIEWER =====================
class DatabaseViewer(QDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle(f"Database: {os.path.basename(db_path)}")
        self.setGeometry(200, 200, 800, 600)
        self._setup_ui()
        self._load_tables()

    def _setup_ui(self):
        layout = QHBoxLayout()

        self.table_list = QListWidget()
        self.table_list.setFixedWidth(200)
        self.table_list.itemClicked.connect(self._load_table_data)
        layout.addWidget(self.table_list)

        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.data_display)

        self.setLayout(layout)

    def _load_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                self.table_list.addItem(QListWidgetItem(table[0]))
            conn.close()
        except Exception as e:
            self.data_display.setText(f"Error loading database:\n{e}")

    def _load_table_data(self, item):
        table_name = item.text()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 100;")
            rows = cursor.fetchall()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [col[1] for col in cursor.fetchall()]

            output = f"Table: {table_name}\n"
            output += f"Columns: {', '.join(columns)}\n"
            output += "-" * 80 + "\n"
            for row in rows:
                output += str(row) + "\n"
            output += f"\nTotal rows shown: {len(rows)}"

            self.data_display.setText(output)
            conn.close()
        except Exception as e:
            self.data_display.setText(f"Error loading table:\n{e}")


# ===================== TERMINAL =====================
class TerminalWidget(QWidget):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings = settings_manager
        self.process = None
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 4)
        title = QLabel("TERMINAL")
        title.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.setFixedHeight(24)
        self.clear_btn.clicked.connect(self.clear_output)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.clear_btn)
        layout.addLayout(header)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output)

        self.setLayout(layout)

    def _apply_theme(self):
        theme = self.settings.get("theme", "dark")
        if theme == "dark":
            self.setStyleSheet("""
                TerminalWidget {
                    background-color: #1e1e1e;
                    border-top: 1px solid #3d3d3d;
                }
                QLabel { color: #cccccc; }
                QPushButton {
                    background-color: #0e639c; color: white;
                    border: none; border-radius: 3px; font-size: 11px;
                }
                QPushButton:hover { background-color: #1177bb; }
            """)
            self.output.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e; color: #d4d4d4;
                    border: none; border-top: 1px solid #3d3d3d;
                }
            """)
        else:
            self.setStyleSheet("""
                TerminalWidget {
                    background-color: #ffffff;
                    border-top: 1px solid #cccccc;
                }
                QLabel { color: #333333; }
                QPushButton {
                    background-color: #007acc; color: white;
                    border: none; border-radius: 3px; font-size: 11px;
                }
                QPushButton:hover { background-color: #1a8ad4; }
            """)
            self.output.setStyleSheet("""
                QTextEdit {
                    background-color: #f5f5f5; color: #000000;
                    border: none; border-top: 1px solid #cccccc;
                }
            """)

    def clear_output(self):
        self.output.clear()

    def append_output(self, text, error=False):
        color = "#f44747" if error else "#d4d4d4"
        self.output.setTextColor(QColor(color))
        self.output.append(text)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output.setTextCursor(cursor)

    def _check_file_access(self, file_path):
        reply = QMessageBox.question(
            self, "File Access Permission",
            f"Do you allow this code to access:\n{file_path}\n\n"
            "This code may read, modify, or delete files on your system.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def run_python(self, file_path):
        if not os.path.exists(file_path):
            self.append_output(f"Error: File not found - {file_path}", error=True)
            return

        if not self._check_file_access(file_path):
            self.append_output(">>> Execution cancelled by user (file access denied)", error=True)
            return

        self.clear_output()
        self.append_output(f">>> Running: {os.path.basename(file_path)}")
        self.append_output(f">>> Path: {file_path}")
        self.append_output("")

        python_path = self.settings.get("python_path", "python")

        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_process_error)

        self.process.setWorkingDirectory(os.path.dirname(file_path))
        self.process.start(python_path, [file_path])

    def run_database(self, db_path):
        if not os.path.exists(db_path):
            self.append_output(f"Error: Database file not found - {db_path}", error=True)
            return

        if not self._check_file_access(db_path):
            self.append_output(">>> Database access denied by user", error=True)
            return

        try:
            viewer = DatabaseViewer(db_path, self.window())
            viewer.exec()
        except Exception as e:
            self.append_output(f"Error opening database: {e}", error=True)

    def _on_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        self.append_output(text.rstrip())

    def _on_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        self.append_output(text.rstrip(), error=True)

    def _on_finished(self, exit_code, exit_status):
        self.append_output("")
        if exit_code == 0:
            self.append_output(f">>> Process finished with exit code {exit_code}")
        else:
            self.append_output(f">>> Process finished with exit code {exit_code} (error)", error=True)

    def _on_process_error(self, error):
        self.append_output(f"Process error: {error}", error=True)


# ===================== SETTINGS DIALOG =====================
class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 450)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout()

        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 30)
        font_layout.addWidget(self.font_spin)
        layout.addLayout(font_layout)

        tab_layout = QHBoxLayout()
        tab_layout.addWidget(QLabel("Tab Size:"))
        self.tab_spin = QSpinBox()
        self.tab_spin.setRange(2, 8)
        tab_layout.addWidget(self.tab_spin)
        layout.addLayout(tab_layout)

        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(QLabel("Encoding:"))
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "utf-16", "ascii", "latin-1", "cp1256"])
        encoding_layout.addWidget(self.encoding_combo)
        layout.addLayout(encoding_layout)

        self.wrap_check = QCheckBox("Word Wrap")
        layout.addWidget(self.wrap_check)

        self.line_check = QCheckBox("Line Numbers")
        layout.addWidget(self.line_check)

        self.auto_save_check = QCheckBox("Auto Save")
        self.auto_save_check.toggled.connect(self._toggle_auto_save_interval)
        layout.addWidget(self.auto_save_check)

        auto_save_interval_layout = QHBoxLayout()
        auto_save_interval_layout.addWidget(QLabel("Auto Save Interval (seconds):"))
        self.auto_save_interval_spin = QSpinBox()
        self.auto_save_interval_spin.setRange(10, 600)
        self.auto_save_interval_spin.setValue(60)
        auto_save_interval_layout.addWidget(self.auto_save_interval_spin)
        layout.addLayout(auto_save_interval_layout)

        python_layout = QHBoxLayout()
        python_layout.addWidget(QLabel("Python Path:"))
        self.python_edit = QLineEdit()
        python_layout.addWidget(self.python_edit)
        layout.addLayout(python_layout)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _toggle_auto_save_interval(self, checked):
        self.auto_save_interval_spin.setEnabled(checked)

    def _load_settings(self):
        self.theme_combo.setCurrentText(self.settings.get("theme", "dark"))
        self.font_spin.setValue(self.settings.get("font_size", 14))
        self.tab_spin.setValue(self.settings.get("tab_size", 4))
        self.encoding_combo.setCurrentText(self.settings.get("encoding", "utf-8"))
        self.wrap_check.setChecked(self.settings.get("word_wrap", False))
        self.line_check.setChecked(self.settings.get("line_numbers", True))
        self.auto_save_check.setChecked(self.settings.get("auto_save", False))
        self.auto_save_interval_spin.setValue(self.settings.get("auto_save_interval", 60))
        self.auto_save_interval_spin.setEnabled(self.settings.get("auto_save", False))
        self.python_edit.setText(self.settings.get("python_path", "python"))

    def _save_settings(self):
        self.settings.set("theme", self.theme_combo.currentText())
        self.settings.set("font_size", self.font_spin.value())
        self.settings.set("tab_size", self.tab_spin.value())
        self.settings.set("encoding", self.encoding_combo.currentText())
        self.settings.set("word_wrap", self.wrap_check.isChecked())
        self.settings.set("line_numbers", self.line_check.isChecked())
        self.settings.set("auto_save", self.auto_save_check.isChecked())
        self.settings.set("auto_save_interval", self.auto_save_interval_spin.value())
        self.settings.set("python_path", self.python_edit.text())
        self.settings.save()
        self.accept()


# ===================== MAIN WINDOW =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
        self.untitled_count = 0
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._apply_theme()

    def _setup_ui(self):
        self.setWindowTitle("Mini Code Editor Pro")
        self.setGeometry(100, 100, 1300, 850)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # File explorer
        self.explorer = QTreeView()
        self.explorer.setMinimumWidth(200)
        self.explorer.setMaximumWidth(400)
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.explorer.setModel(self.model)
        self.explorer.setRootIndex(self.model.index(QDir.currentPath()))
        self.explorer.hideColumn(1)
        self.explorer.hideColumn(2)
        self.explorer.hideColumn(3)
        self.explorer.doubleClicked.connect(self._open_file_from_explorer)
        self.explorer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.explorer.customContextMenuRequested.connect(self._explorer_context_menu)

        # Editor + Terminal splitter
        self.editor_terminal_splitter = QSplitter(Qt.Orientation.Vertical)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)

        self.terminal = TerminalWidget(self.settings)

        self.editor_terminal_splitter.addWidget(self.tab_widget)
        self.editor_terminal_splitter.addWidget(self.terminal)
        self.editor_terminal_splitter.setStretchFactor(0, 3)
        self.editor_terminal_splitter.setStretchFactor(1, 1)

        self.splitter.addWidget(self.explorer)
        self.splitter.addWidget(self.editor_terminal_splitter)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)

        self.setCentralWidget(self.splitter)

        self.status = QStatusBar()
        self.status_label = QLabel("Ready")
        self.status.addPermanentWidget(self.status_label)
        self.setStatusBar(self.status)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        open_folder_action = QAction("Open &Folder...", self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_folder_action.triggered.connect(self._open_folder)
        file_menu.addAction(open_folder_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Recent files submenu
        self.recent_menu = QMenu("&Recent Files", self)
        file_menu.addMenu(self.recent_menu)
        self._update_recent_menu()

        file_menu.addSeparator()

        open_db_action = QAction("Open &Database...", self)
        open_db_action.setShortcut(QKeySequence("Ctrl+D"))
        open_db_action.triggered.connect(self._open_database)
        file_menu.addAction(open_db_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        find_action = QAction("&Find...", self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self._show_search)
        edit_menu.addAction(find_action)

        comment_action = QAction("Toggle &Comment", self)
        comment_action.setShortcut(QKeySequence("Ctrl+/"))
        comment_action.triggered.connect(self._toggle_comment)
        edit_menu.addAction(comment_action)

        edit_menu.addSeparator()

        change_encoding_action = QAction("Change &Encoding...", self)
        change_encoding_action.triggered.connect(self._change_encoding)
        edit_menu.addAction(change_encoding_action)

        edit_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self._open_settings)
        edit_menu.addAction(settings_action)

        run_menu = menubar.addMenu("&Run")

        run_action = QAction("&Run Python File", self)
        run_action.setShortcut(QKeySequence("F5"))
        run_action.triggered.connect(self._run_file)
        run_menu.addAction(run_action)

        view_menu = menubar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence("Ctrl+="))
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)

        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset_action.triggered.connect(self._zoom_reset)
        view_menu.addAction(zoom_reset_action)

        view_menu.addSeparator()

        fullscreen_action = QAction("&Fullscreen", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

    def _setup_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)

        new_btn = toolbar.addAction("New")
        new_btn.triggered.connect(self._new_file)

        open_btn = toolbar.addAction("Open")
        open_btn.triggered.connect(self._open_file)

        save_btn = toolbar.addAction("Save")
        save_btn.triggered.connect(self._save_file)

        toolbar.addSeparator()

        run_btn = toolbar.addAction("Run")
        run_btn.triggered.connect(self._run_file)

        toolbar.addSeparator()

        db_btn = toolbar.addAction("Database")
        db_btn.triggered.connect(self._open_database)

    def _update_recent_menu(self):
        self.recent_menu.clear()
        for path in self.settings.recent_files:
            if os.path.exists(path):
                action = QAction(path, self)
                action.triggered.connect(lambda checked, p=path: self._open_file_in_editor(p))
                self.recent_menu.addAction(action)
        if not self.settings.recent_files:
            action = QAction("No recent files", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)

    def _explorer_context_menu(self, pos):
        index = self.explorer.indexAt(pos)
        if not index.isValid():
            return
        file_path = self.model.filePath(index)
        menu = QMenu()
        if os.path.isfile(file_path):
            open_action = menu.addAction("Open")
            open_action.triggered.connect(lambda: self._open_file_from_explorer(index))
            copy_path_action = menu.addAction("Copy Path")
            copy_path_action.triggered.connect(lambda: QApplication.clipboard().setText(file_path))
            if file_path.endswith(('.db', '.sqlite')):
                db_action = menu.addAction("Open as Database")
                db_action.triggered.connect(lambda: self.terminal.run_database(file_path))
        else:
            open_action = menu.addAction("Open Folder")
            open_action.triggered.connect(lambda: self.explorer.setRootIndex(index))
        menu.exec(self.explorer.viewport().mapToGlobal(pos))

    def _apply_theme(self):
        theme = self.settings.get("theme", "dark")
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #252526;
                }
                QMenuBar {
                    background-color: #3c3c3c;
                    color: #cccccc;
                }
                QMenuBar::item:selected {
                    background-color: #094771;
                }
                QMenu {
                    background-color: #3c3c3c;
                    color: #cccccc;
                }
                QMenu::item:selected {
                    background-color: #094771;
                }
                QToolBar {
                    background-color: #3c3c3c;
                    border: none;
                    spacing: 4px;
                }
                QStatusBar {
                    background-color: #007acc;
                    color: white;
                }
                QTabWidget::pane {
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #969696;
                    padding: 6px 12px;
                    border: none;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QTreeView {
                    background-color: #252526;
                    color: #cccccc;
                    border: none;
                }
                QTreeView::item:selected {
                    background-color: #094771;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f3f3f3;
                }
                QMenuBar {
                    background-color: #ffffff;
                    color: #333333;
                }
                QMenuBar::item:selected {
                    background-color: #e8f0fe;
                }
                QMenu {
                    background-color: #ffffff;
                    color: #333333;
                }
                QMenu::item:selected {
                    background-color: #e8f0fe;
                }
                QToolBar {
                    background-color: #ffffff;
                    border: none;
                    spacing: 4px;
                }
                QStatusBar {
                    background-color: #007acc;
                    color: white;
                }
                QTabWidget::pane {
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #ececec;
                    color: #666666;
                    padding: 6px 12px;
                    border: none;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    color: #000000;
                }
                QTreeView {
                    background-color: #f3f3f3;
                    color: #333333;
                    border: none;
                }
                QTreeView::item:selected {
                    background-color: #e8f0fe;
                }
            """)

    def _get_current_editor(self):
        if self.tab_widget.count() > 0:
            return self.tab_widget.currentWidget()
        return None

    def _new_file(self):
        editor = CodeEditor(self.settings)
        self.untitled_count += 1
        index = self.tab_widget.addTab(editor, f"untitled-{self.untitled_count}")
        self.tab_widget.setCurrentIndex(index)

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "All Files (*);;Python (*.py);;JavaScript (*.js);;HTML (*.html);;CSS (*.css);;C (*.c);;C++ (*.cpp);;JSON (*.json);;Markdown (*.md);;SQL (*.sql);;Bash (*.sh);;Database (*.db *.sqlite)"
        )
        if file_path:
            self._open_file_in_editor(file_path)

    def _open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder_path:
            self.explorer.setRootIndex(self.model.index(folder_path))
            self.status_label.setText(f"Folder: {folder_path}")

    def _open_file_from_explorer(self, index):
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
            if ext in ["db", "sqlite"]:
                self.terminal.run_database(file_path)
            else:
                self._open_file_in_editor(file_path)

    def _open_file_in_editor(self, file_path):
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor.get_file_path() == file_path:
                self.tab_widget.setCurrentIndex(i)
                return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")
            return

        editor = CodeEditor(self.settings)
        editor.set_file_path(file_path)
        editor.setPlainText(content)
        editor.document().setModified(False)
        self.tab_widget.addTab(editor, os.path.basename(file_path))
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        self.status_label.setText(f"Opened: {file_path}")
        self._update_recent_menu()

    def _open_database(self):
        db_path, _ = QFileDialog.getOpenFileName(
            self, "Open Database", "",
            "Database Files (*.db *.sqlite);;All Files (*)"
        )
        if db_path:
            self.terminal.run_database(db_path)

    def _save_file(self):
        editor = self._get_current_editor()
        if not editor:
            return False

        file_path = editor.get_file_path()
        if not file_path:
            return self._save_file_as()

        try:
            with open(file_path, "w", encoding=editor.get_encoding()) as f:
                f.write(editor.toPlainText())
            editor.document().setModified(False)
            self.status_label.setText(f"Saved: {file_path}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")
            return False

    def _save_file_as(self):
        editor = self._get_current_editor()
        if not editor:
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", "",
            "All Files (*);;Python (*.py);;JavaScript (*.js);;HTML (*.html);;CSS (*.css);;C (*.c);;C++ (*.cpp);;JSON (*.json);;Markdown (*.md);;SQL (*.sql);;Bash (*.sh)"
        )
        if not file_path:
            return False

        editor.set_file_path(file_path)
        try:
            with open(file_path, "w", encoding=editor.get_encoding()) as f:
                f.write(editor.toPlainText())
            editor.document().setModified(False)
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_path))
            self.status_label.setText(f"Saved: {file_path}")
            self._update_recent_menu()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")
            return False

    def _close_tab(self, index):
        editor = self.tab_widget.widget(index)
        if editor.document().isModified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before closing?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentIndex(index)
                if not self._save_file():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.tab_widget.removeTab(index)

    def _run_file(self):
        editor = self._get_current_editor()
        if not editor:
            return

        file_path = editor.get_file_path()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please save the file first.")
            return

        if editor.document().isModified():
            if not self._save_file():
                return

        self.terminal.run_python(file_path)

    def _show_search(self):
        editor = self._get_current_editor()
        if editor:
            editor.search_bar.show()

    def _toggle_comment(self):
        editor = self._get_current_editor()
        if editor:
            editor.toggle_comment()

    def _change_encoding(self):
        editor = self._get_current_editor()
        if not editor:
            return
        encoding, ok = QInputDialog.getItem(
            self, "Change Encoding",
            "Select encoding:",
            ["utf-8", "utf-16", "ascii", "latin-1", "cp1256"],
            0, False
        )
        if ok and encoding:
            editor.set_encoding(encoding)
            self.status_label.setText(f"Encoding changed to: {encoding}")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _undo(self):
        editor = self._get_current_editor()
        if editor:
            editor.undo()

    def _redo(self):
        editor = self._get_current_editor()
        if editor:
            editor.redo()

    def _zoom_in(self):
        editor = self._get_current_editor()
        if editor:
            editor.zoom_in()

    def _zoom_out(self):
        editor = self._get_current_editor()
        if editor:
            editor.zoom_out()

    def _zoom_reset(self):
        editor = self._get_current_editor()
        if editor:
            editor.zoom_reset()

    def _open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for i in range(self.tab_widget.count()):
                editor = self.tab_widget.widget(i)
                editor.apply_settings()
            self._apply_theme()
            self.terminal._apply_theme()
            self.status_label.setText("Settings updated")


# ===================== MAIN =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
