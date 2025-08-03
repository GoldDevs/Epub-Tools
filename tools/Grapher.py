#!/usr/bin/env python3

import os
import argparse
import fnmatch
from pathlib import Path

# --- ASCII Art Configuration ---
# You can change these characters to customize the look of the tree.
PREFIX_MIDDLE = "├── "
PREFIX_LAST = "└── "
PREFIX_PASS = "│   "
PREFIX_EMPTY = "    "

# --- Default Ignore Patterns ---
# A set of common files/directories to ignore by default.
# Wildcards like '*' and '?' are supported.
DEFAULT_IGNORE = {
    '.git',
    '__pycache__',
    '.vscode',
    'node_modules',
    '.DS_Store',
    '*.pyc',
    '*.egg-info'
}

class TreeGrapher:
    """
    A class to generate an ASCII graph of a project folder structure.
    """
    def __init__(self, root_dir, max_depth=None, ignore_patterns=None):
        self.root_dir = Path(root_dir).resolve()
        self.max_depth = max_depth
        # Combine default ignore patterns with any user-provided ones
        self.ignore_patterns = DEFAULT_IGNORE.union(set(ignore_patterns or []))
        self.dir_count = 0
        self.file_count = 0

    def generate(self):
        """Generates the full directory tree as a list of strings."""
        if not self.root_dir.is_dir():
            return [f"Error: Directory not found at '{self.root_dir}'"]

        tree_lines = [f"{self.root_dir.name}"]
        tree_lines.extend(self._build_tree(self.root_dir))
        return tree_lines

    def _is_ignored(self, name):
        """Checks if a file or directory name matches any ignore patterns."""
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _build_tree(self, current_path, prefix="", level=0):
        """
        Recursively builds the directory tree structure.
        This is a generator that yields each line of the tree.
        """
        # Stop if max depth is reached
        if self.max_depth is not None and level >= self.max_depth:
            return

        # Get directory contents, filter ignored items, and sort
        try:
            entries = [entry for entry in os.listdir(current_path) if not self._is_ignored(entry.name if isinstance(entry, Path) else entry)]
            entries.sort()
        except PermissionError:
            yield f"{prefix}{PREFIX_LAST}[Error: Permission Denied]"
            return

        # Iterate through entries to build the tree
        for i, entry_name in enumerate(entries):
            entry_path = current_path / entry_name
            is_last = (i == len(entries) - 1)

            # Determine the connector and prefix for the current item
            connector = PREFIX_LAST if is_last else PREFIX_MIDDLE
            yield f"{prefix}{connector}{entry_name}"

            # If it's a directory, recurse into it
            if entry_path.is_dir():
                self.dir_count += 1
                # The prefix for child items depends on whether this was the last item
                child_prefix = prefix + (PREFIX_EMPTY if is_last else PREFIX_PASS)
                yield from self._build_tree(entry_path, prefix=child_prefix, level=level + 1)
            else:
                self.file_count += 1

def main():
    """Parses command-line arguments and runs the grapher."""
    parser = argparse.ArgumentParser(
        description="Generate an ASCII graph of a project folder.",
        epilog="Example: python grapher.py ./my_project --depth 3 --ignore *.tmp"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="The path to the directory to graph. Defaults to the current directory."
    )
    parser.add_argument(
        "-d", "--depth",
        type=int,
        help="Maximum depth to traverse the directory tree."
    )
    parser.add_argument(
        "-i", "--ignore",
        nargs='*',
        help="Space-separated list of file/directory patterns to ignore (e.g., venv *.log build)."
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0'
    )

    args = parser.parse_args()

    # Create and run the grapher
    grapher = TreeGrapher(
        root_dir=args.path,
        max_depth=args.depth,
        ignore_patterns=args.ignore
    )

    tree_lines = grapher.generate()

    # Print the results
    for line in tree_lines:
        print(line)

    # Print the summary
    print(f"\n{grapher.dir_count} directories, {grapher.file_count} files")


if __name__ == "__main__":
    main()