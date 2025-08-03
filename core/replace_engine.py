import re
import difflib
from typing import Dict, List, Tuple, Optional
from .content_manager import ContentManager
from .search_engine import SearchResult

class ReplacementStats:
    __slots__ = ('total_replacements', 'files_modified', 'failed_files', 'characters_changed')
    
    def __init__(self):
        self.total_replacements = 0
        self.files_modified = 0
        self.failed_files = 0
        self.characters_changed = 0
        
    def __str__(self):
        return (f"Replacements: {self.total_replacements}, "
                f"Files Modified: {self.files_modified}, "
                f"Chars Changed: {self.characters_changed}")

class ReplaceEngine:
    def __init__(self, content_manager: ContentManager):
        self.content_manager = content_manager
        # History stores (file_path, line_number, original_line_content)
        self.replacement_history: List[Tuple[str, int, str]] = []
        self.max_history = 50  # Limit for mobile devices

    def replace(
        self,
        file_path: str,
        line_number: int,
        start_pos: int,
        end_pos: int,
        new_text: str
    ) -> bool:
        """Replace specific text in a file at a specific location."""
        content = self.content_manager.get_content(file_path)
        if content is None:
            return False
            
        lines = content.split('\n')
        if not (1 <= line_number <= len(lines)):
            return False
            
        line_index = line_number - 1
        original_line = lines[line_index]
        if not (0 <= start_pos <= end_pos <= len(original_line)):
            return False
            
        # Create new line content
        new_line = original_line[:start_pos] + new_text + original_line[end_pos:]
        lines[line_index] = new_line
        new_content = '\n'.join(lines)
        
        # Update content and track history
        if self.content_manager.update_content(file_path, new_content):
            self.replacement_history.append((
                file_path,
                line_number,
                original_line  # Store the entire original line for robust undo
            ))
            # Limit history size
            if len(self.replacement_history) > self.max_history:
                self.replacement_history.pop(0)
            return True
        return False

    def pattern_replace(
        self,
        pattern: str,
        replacement: str,
        case_sensitive: bool = False,
        regex_mode: bool = False,
        whole_word: bool = False,
        files_to_process: Optional[List[str]] = None
    ) -> ReplacementStats:
        """Replace all occurrences of a pattern across specified files, or all files if None."""
        stats = ReplacementStats()
        
        if files_to_process is None:
            files_to_process = list(self.content_manager.content_map.keys())
        
        # Compile pattern
        search_regex = self._compile_pattern(pattern, case_sensitive, regex_mode, whole_word)
        if not search_regex:
            return stats
            
        modified_files_in_batch = set()

        # Process each file
        for file_path in files_to_process:
            content = self.content_manager.get_content(file_path)
            if content is None:
                continue
                
            # Perform replacement and get count in one go
            new_content, num_replacements = self._replace_in_content(content, search_regex, replacement)
            
            if num_replacements > 0:
                if self.content_manager.update_content(file_path, new_content):
                    stats.total_replacements += num_replacements
                    stats.characters_changed += len(new_content) - len(content)
                    modified_files_in_batch.add(file_path)
                else:
                    stats.failed_files += 1
        
        stats.files_modified = len(modified_files_in_batch)
        return stats

    def undo_last_replacement(self) -> bool:
        """Undo the last replacement operation. This is more robust as it restores the whole line."""
        if not self.replacement_history:
            return False
            
        # Get last replacement
        file_path, line_number, original_line = self.replacement_history.pop()
        
        # Get current content
        content = self.content_manager.get_content(file_path)
        if content is None:
            return False
            
        lines = content.split('\n')
        if not (1 <= line_number <= len(lines)):
            # History is out of sync with content, can't undo
            return False
        
        # Undo the replacement by restoring the original line
        line_index = line_number - 1
        lines[line_index] = original_line
        new_content = '\n'.join(lines)
        
        # We call update_content which handles re-indexing and change history
        return self.content_manager.update_content(file_path, new_content)

    def _compile_pattern(
        self,
        pattern: str,
        case_sensitive: bool,
        regex_mode: bool,
        whole_word: bool
    ) -> Optional[re.Pattern]:
        """Compile a regex pattern for replacement"""
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            if regex_mode:
                return re.compile(pattern, flags)
            else:
                escaped = re.escape(pattern)
                if whole_word:
                    return re.compile(r'\b' + escaped + r'\b', flags)
                return re.compile(escaped, flags)
        except re.error:
            return None

    def _replace_in_content(
        self,
        content: str,
        pattern: re.Pattern,
        replacement: str
    ) -> Tuple[str, int]:
        """Replace all matches in content and count replacements using re.subn for efficiency."""
        # re.subn returns a tuple: (new_string, number_of_subs_made)
        new_content, num_replacements = pattern.subn(replacement, content)
        return new_content, num_replacements

    def get_replacement_history(self, max_items: int = 10) -> List[Tuple]:
        """Get recent replacement history"""
        return list(self.replacement_history[-max_items:])
    
    def replace_by_results(self, results_to_replace: List[SearchResult], new_text: str) -> ReplacementStats:
        """
        Safely replaces text for a given list of SearchResult objects.
        It processes results grouped by file and in reverse line/column order to avoid index corruption.
        """
        stats = ReplacementStats()
        # Group results by file
        grouped_results: Dict[str, List[SearchResult]] = {}
        for res in results_to_replace:
            if res.file_path not in grouped_results:
                grouped_results[res.file_path] = []
            grouped_results[res.file_path].append(res)
        
        for file_path, results in grouped_results.items():
            # IMPORTANT: Sort results in reverse order to prevent index invalidation
            results.sort(key=lambda r: (r.line_number, r.start_pos), reverse=True)
            
            content = self.content_manager.get_content(file_path)
            if not content: continue
    
            lines = content.split('\n')
            file_replacements = 0
            
            for res in results:
                line_idx = res.line_number - 1
                if 0 <= line_idx < len(lines):
                    line = lines[line_idx]
                    # Double-check that the original text is still there before replacing
                    if line[res.start_pos:res.end_pos] == res.match_text:
                        lines[line_idx] = line[:res.start_pos] + new_text + line[res.end_pos:]
                        file_replacements += 1
    
            if file_replacements > 0:
                new_content = '\n'.join(lines)
                if self.content_manager.update_content(file_path, new_content):
                    stats.total_replacements += file_replacements
                    stats.files_modified += 1
    
        return stats