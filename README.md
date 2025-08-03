# Mobile EPUB Editor

[![PyPI version](https://badge.fury.io/py/android-termux-epub-editor-pro.svg)](https://badge.fury.io/py/android-termux-epub-editor-pro)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/android-termux-epub-editor-pro.svg)](https://pypi.org/project/android-termux-epub-editor-pro/)

A feature-rich, terminal-based EPUB editor, specifically optimized for use on Android with Termux.

This tool provides a fast, keyboard-driven, and intuitive Text-based User Interface (TUI) for performing advanced search and replace operations on EPUB files without needing a graphical environment. It is designed to be efficient on mobile devices, with a responsive layout and a Material Design inspired look-and-feel.

While its primary target is **Android (Unrooted Termux)**, it is also fully compatible with standard Linux, macOS, and Windows (via WSL) terminals.

---

### Key Features

*   **Advanced Search**: Full regular expression (regex), case-sensitivity, and whole-word search across all content files in an EPUB.
*   **Powerful Replace**: Perform individual or batch replacements with regex support and smart-pattern matching.
*   **Mobile-First TUI**: A responsive, card-based layout inspired by Material Design that adapts to both portrait and landscape orientations.
*   **Safe Operations**: Atomic file saving ensures your EPUBs are never corrupted, with automatic backup creation before any changes are written.
*   **Efficient Core**: Built from the ground up to be memory-efficient and performant on mobile CPUs, with multi-threaded searching.
*   **Broad Compatibility**: Supports both EPUB 2 and EPUB 3 formats.

### Requirements

*   Python 3.8+
*   A terminal that supports `curses` (most modern terminals).
    *   **Primary Target**: Termux on Android 14+
    *   **Secondary Targets**: Linux, macOS, Windows (WSL)

### Installation

Install the package directly from PyPI:

```bash
pip install mobile-epubedit
```

### Usage

After installation, you can run the application from anywhere in your terminal by simply typing:

```bash
mepubedit
```

The application will launch, and all user data (history, logs, backups) will be stored in a dedicated directory within your home folder (`~/.config/epub_editor_pro/`).

### Source Code & Issues

The full source code, issue tracker, and contribution guidelines are available on our [GitHub Repository](https://github.com/GoldDevs/Epub-Tools).
