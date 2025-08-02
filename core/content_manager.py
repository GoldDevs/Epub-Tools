import re
import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from xml.etree import ElementTree as ET

class ContentManager:
    def __init__(self):
        self.content_map: Dict[str, str] = {}          # File path → content
        self.original_content: Dict[str, str] = {}     # Original content copies
        self.modified_files: Set[str] = set()          # Track modified files
        self.change_history: Dict[str, List[Tuple]] = defaultdict(list)  # File path → [(old_text, new_text)]
        self.file_index: Dict[str, List[Tuple]] = defaultdict(list)      # Word → [(file_path, line_num, position)]
        self.encoding = 'utf-8'
        self.stats = {
            'total_files': 0,
            'total_words': 0,
            'total_chars': 0,
            'modified_count': 0
        }

    def add_file(self, file_path: str, content: str) -> bool:
        """Add file content to manager with validation"""
        if not self._validate_content(content):
            return False
            
        self.content_map[file_path] = content
        self.original_content[file_path] = content
        self._update_stats_add(content)
        self._index_content(file_path, content)
        return True

    def get_content(self, file_path: str) -> Optional[str]:
        """Get content for a file"""
        return self.content_map.get(file_path)

    def update_content(self, file_path: str, new_content: str) -> bool:
        """Update file content with change tracking"""
        if file_path not in self.content_map:
            return False
            
        if not self._validate_content(new_content):
            return False
            
        old_content = self.content_map[file_path]
        
        # Only track if content actually changed
        if old_content != new_content:
            self.content_map[file_path] = new_content
            if file_path not in self.modified_files:
                self.modified_files.add(file_path)
                self.stats['modified_count'] = len(self.modified_files)

            self.change_history[file_path].append((old_content, new_content))
            self._reindex_file(file_path, old_content, new_content)
            return True
        return False

    def get_modified_files(self) -> List[str]:
        """Get list of modified files"""
        return list(self.modified_files)

    def has_modifications(self) -> bool:
        """Check if any modifications exist"""
        return len(self.modified_files) > 0

    def rollback_file(self, file_path: str, steps: int = 1) -> bool:
        """Revert file changes"""
        if file_path not in self.change_history or not self.change_history[file_path] or steps < 1:
            return False
            
        current_content = self.content_map.get(file_path)
        # Rollback through history steps
        for _ in range(min(steps, len(self.change_history[file_path]))):
            old_content, _ = self.change_history[file_path].pop()
            
        # The content to revert to is the "old_content" of the last popped history item
        # If history becomes empty, we revert to original content
        if not self.change_history[file_path]:
            new_content = self.original_content[file_path]
            self.modified_files.discard(file_path)
            self.stats['modified_count'] = len(self.modified_files)
        else:
            # The new "current" content is the "old" content from the last undone change
            new_content = self.change_history[file_path][-1][0]

        self.content_map[file_path] = new_content
        self._reindex_file(file_path, current_content, new_content)
        return True

    def get_content_hash(self, file_path: str) -> str:
        """Get SHA256 hash of file content"""
        content = self.content_map.get(file_path, '')
        return hashlib.sha256(content.encode(self.encoding)).hexdigest()

    def search_index(self, word: str) -> List[Tuple]:
        """Find positions of a word using the index"""
        return self.file_index.get(word.lower(), [])

    def _validate_content(self, content: str) -> bool:
        """Validate content before storing. Keep it simple and fast."""
        # Check for null bytes which can cause issues with C libraries and string manipulation.
        if '\x00' in content:
            return False
        return True

    def _update_stats_add(self, content: str) -> None:
        """Update statistics counters when adding a new file"""
        self.stats['total_files'] += 1
        self.stats['total_chars'] += len(content)
        self.stats['total_words'] += len(re.findall(r'\w+', content))

    def _update_stats_modify(self, old_content: str, new_content: str) -> None:
        """Update statistics counters when modifying content"""
        self.stats['total_chars'] += len(new_content) - len(old_content)
        self.stats['total_words'] += len(re.findall(r'\w+', new_content)) - len(re.findall(r'\w+', old_content))

    def _index_content(self, file_path: str, content: str) -> None:
        """Index content for fast searching"""
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Using finditer is more efficient as it gives both word and position in one pass
            for match in re.finditer(r'\w+', line.lower()):
                word = match.group(0)
                pos = match.start()
                self.file_index[word].append((file_path, line_num, pos))

    def _reindex_file(self, file_path: str, old_content: str, new_content: str) -> None:
        """
        Efficiently update index after content change.
        This is a critical performance optimization.
        """
        # 1. Get unique words from old and new content
        old_words = set(re.findall(r'\w+', old_content.lower()))
        new_words = set(re.findall(r'\w+', new_content.lower()))
        
        # 2. Words to remove from index for this file
        words_to_remove = old_words - new_words
        for word in words_to_remove:
            if word in self.file_index:
                self.file_index[word] = [entry for entry in self.file_index[word] if entry[0] != file_path]
                if not self.file_index[word]:
                    del self.file_index[word]
        
        # 3. Words to add/update in the index
        words_to_update = new_words
        # First, clear previous entries for the file for words that are being re-indexed
        for word in words_to_update.intersection(old_words):
             if word in self.file_index:
                self.file_index[word] = [entry for entry in self.file_index[word] if entry[0] != file_path]

        # Now, re-index the new content for all words it contains
        lines = new_content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(r'\w+', line.lower()):
                word = match.group(0)
                pos = match.start()
                self.file_index[word].append((file_path, line_num, pos))

        # 4. Update statistics
        self._update_stats_modify(old_content, new_content)


    def get_memory_usage(self) -> int:
        """Estimate memory usage in bytes using a more accurate method."""
        total_size = sum(sys.getsizeof(c) for c in self.content_map.values())
        total_size += sum(sys.getsizeof(c) for c in self.original_content.values())
        total_size += sys.getsizeof(self.file_index)
        return total_size

    def get_file_stats(self, file_path: str) -> Dict:
        """Get statistics for a specific file"""
        content = self.content_map.get(file_path, '')
        return {
            'size': len(content),
            'lines': content.count('\n') + 1,
            'words': len(re.findall(r'\w+', content)),
            'modifications': len(self.change_history.get(file_path, []))
        }