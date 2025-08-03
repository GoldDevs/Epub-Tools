import re
import time
from typing import List, Dict, Tuple, Optional, Generator
from concurrent.futures import ThreadPoolExecutor
from .content_manager import ContentManager

class SearchResult:
    __slots__ = ('file_path', 'line_number', 'start_pos', 'end_pos', 'match_text', 'context_before', 'context_after')
    
    def __init__(self, file_path: str, line_number: int, start_pos: int, end_pos: int, 
                 match_text: str, context_before: str, context_after: str):
        self.file_path = file_path
        self.line_number = line_number
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.match_text = match_text
        self.context_before = context_before
        self.context_after = context_after

class SearchEngine:
    def __init__(self, content_manager: ContentManager):
        self.content_manager = content_manager
        self.search_cache: Dict[str, List[SearchResult]] = {}
        self.last_search_stats = {
            'pattern': '',
            'time_taken': 0,
            'results_count': 0,
            'files_searched': 0,
            'options': {}
        }
        self.executor = ThreadPoolExecutor(max_workers=4)  # Optimized for mobile CPUs

    def search(
        self, 
        pattern: str, 
        case_sensitive: bool = False, 
        regex_mode: bool = False,
        whole_word: bool = False,
        context_size: int = 30
    ) -> List[SearchResult]:
        """Perform search across all content with various options"""
        start_time = time.time()
        cache_key = self._generate_cache_key(pattern, case_sensitive, regex_mode, whole_word)
        
        # Check cache first
        if cache_key in self.search_cache:
            results = self.search_cache[cache_key]
            self.last_search_stats = {
                'pattern': pattern,
                'time_taken': 0,  # Not actual search time but useful for UI
                'results_count': len(results),
                'files_searched': len(self.content_manager.content_map),
                'options': {
                    'case_sensitive': case_sensitive,
                    'regex_mode': regex_mode,
                    'whole_word': whole_word
                }
            }
            return results
        
        # Build regex pattern based on options
        search_regex = self._build_search_regex(pattern, case_sensitive, regex_mode, whole_word)
        if not search_regex:
            return []
        
        # Search all files in parallel
        results = []
        files = list(self.content_manager.content_map.keys())
        self.last_search_stats['files_searched'] = len(files)
        
        # Use ThreadPoolExecutor for parallel searching
        future_results = [
            self.executor.submit(
                self._search_file, 
                file_path, 
                search_regex, 
                context_size
            ) for file_path in files
        ]
        
        for future in future_results:
            try:
                results.extend(future.result())
            except Exception as e:
                # Log or handle errors from individual file searches to prevent crashing the entire operation
                print(f"Warning: Could not search a file due to an error: {e}")
        
        # Update cache and stats
        self.search_cache[cache_key] = results
        self.last_search_stats.update({
            'pattern': pattern,
            'time_taken': time.time() - start_time,
            'results_count': len(results),
            'options': {
                'case_sensitive': case_sensitive,
                'regex_mode': regex_mode,
                'whole_word': whole_word
            }
        })
        
        return results

    def _build_search_regex(
        self, 
        pattern: str, 
        case_sensitive: bool, 
        regex_mode: bool,
        whole_word: bool
    ) -> Optional[re.Pattern]:
        """Compile regex pattern based on search options"""
        flags = 0 if case_sensitive else re.IGNORECASE
        
        if regex_mode:
            try:
                return re.compile(pattern, flags)
            except re.error:
                return None
        else:
            # Escape special characters for literal search
            escaped_pattern = re.escape(pattern)
            if whole_word:
                return re.compile(r'\b' + escaped_pattern + r'\b', flags)
            return re.compile(escaped_pattern, flags)

    def _search_file(
        self, 
        file_path: str, 
        search_regex: re.Pattern, 
        context_size: int
    ) -> List[SearchResult]:
        """Search within a single file"""
        content = self.content_manager.get_content(file_path)
        if not content:
            return []
        
        results = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for match in search_regex.finditer(line):
                start, end = match.span()
                match_text = match.group()
                
                # Extract context
                context_start = max(0, start - context_size)
                context_end = min(len(line), end + context_size)
                context_before = line[context_start:start]
                context_after = line[end:context_end]
                
                results.append(SearchResult(
                    file_path=file_path,
                    line_number=line_num,
                    start_pos=start,
                    end_pos=end,
                    match_text=match_text,
                    context_before=context_before,
                    context_after=context_after
                ))
        
        return results

    def _generate_cache_key(
        self, 
        pattern: str, 
        case_sensitive: bool, 
        regex_mode: bool,
        whole_word: bool
    ) -> str:
        """Generate unique cache key for search parameters"""
        return f"{pattern}|{int(case_sensitive)}|{int(regex_mode)}|{int(whole_word)}"

    def get_search_history(self, max_items: int = 10) -> List[Dict]:
        """Get recent search patterns"""
        # Simple implementation - real system would persist history
        return [
            {'pattern': key.split('|')[0], 'count': len(results)}
            for key, results in list(self.search_cache.items())[-max_items:]
        ]

    def fuzzy_search(self, pattern: str, max_distance: int = 2, context_size: int = 30) -> List[SearchResult]:
        """
        Approximate/fuzzy search (simplified implementation).
        NOTE: This implementation is much more performant than the original, but the core
        `_find_closest_match` still uses a brute-force sliding window, which can be slow on very long lines.
        For typical EPUB content, this should be acceptable.
        This fuzzy search is always case-insensitive.
        """
        results = []
        pattern_lower = pattern.lower()
        
        for file_path, content in self.content_manager.content_map.items():
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                pos_in_line = 0
                while pos_in_line < len(line_lower):
                    match_start = self._find_closest_match(line_lower, pattern_lower, pos_in_line, max_distance)
                    
                    if match_start == -1:
                        break

                    match_end = match_start + len(pattern)
                    match_text = line[match_start:match_end]

                    # Extract context
                    context_start = max(0, match_start - context_size)
                    context_end = min(len(line), match_end + context_size)
                    context_before = line[context_start:match_start]
                    context_after = line[match_end:context_end]

                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=line_num,
                        start_pos=match_start,
                        end_pos=match_end,
                        match_text=match_text,
                        context_before=context_before,
                        context_after=context_after
                    ))
                    
                    pos_in_line = match_end
        
        return results

    def _find_closest_match(self, text: str, pattern: str, start_pos: int, max_distance: int) -> int:
        """Find closest approximate match position in a string, starting from start_pos."""
        pattern_len = len(pattern)
        for i in range(start_pos, len(text) - pattern_len + 1):
            substring = text[i:i+pattern_len]
            if self._levenshtein_distance(substring, pattern) <= max_distance:
                return i
        return -1

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings (space-optimized)."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def clear_cache(self) -> None:
        """Clear search cache to free memory"""
        self.search_cache.clear()

    def get_last_search_stats(self) -> Dict:
        """Get statistics from last search operation"""
        return self.last_search_stats