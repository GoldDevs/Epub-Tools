import os
import zipfile
import shutil
import tempfile
import re
import hashlib
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from .content_manager import ContentManager

class EPUBSaver:
    def __init__(self, content_manager: ContentManager):
        self.content_manager = content_manager
        self.backup_dir = "backups"
        self.max_backups = 5  # Mobile storage optimization
        self.compression_level = zipfile.ZIP_DEFLATED

    def save_epub(
        self, 
        original_path: Path, 
        output_path: Optional[Path] = None, 
        create_backup: bool = True
    ) -> Tuple[bool, str]:
        """Save modified EPUB with validation and backup. This is the main save function."""
        if not output_path:
            output_path = original_path
        
        # In-place save requires a backup.
        if output_path == original_path and create_backup:
            backup_path_str = self._create_backup(original_path)
            if not backup_path_str:
                return False, "Backup creation failed"
        else:
            backup_path_str = "No backup created for 'Save As'."

        # Use a private method for the core saving logic
        success, message = self._write_epub(original_path, output_path)

        if success:
            # Clear modified flags only on successful save to the original path
            if output_path == original_path:
                self.content_manager.modified_files.clear()
            return True, f"Saved successfully. {backup_path_str}"
        
        return False, message

    def _write_epub(self, source_path: Path, target_path: Path) -> Tuple[bool, str]:
        """Core logic to write content to an EPUB file."""
        # Use a temporary file for atomic saving
        temp_dir = tempfile.mkdtemp()
        temp_file_path = Path(temp_dir) / target_path.name
        
        try:
            with zipfile.ZipFile(source_path, 'r') as source_zip:
                with zipfile.ZipFile(temp_file_path, 'w', self.compression_level) as target_zip:
                    # **EPUB Spec Requirement**: mimetype must be the first file and uncompressed.
                    # We get it from the original file to be safe.
                    mimetype_content = source_zip.read('mimetype')
                    target_zip.writestr('mimetype', mimetype_content, compress_type=zipfile.ZIP_STORED)

                    # Now write the rest of the files
                    for item in source_zip.infolist():
                        file_name = item.filename
                        if file_name == 'mimetype':
                            continue # Already written
                        
                        # Use normalized path for lookup in content_manager
                        normalized_path = file_name.replace('\\', '/')

                        if normalized_path in self.content_manager.content_map:
                            # Write modified content from manager
                            modified_content = self.content_manager.get_content(normalized_path)
                            target_zip.writestr(item, modified_content.encode('utf-8'))
                        else:
                            # Copy unchanged file directly from source
                            target_zip.writestr(item, source_zip.read(file_name))
            
            # Validate the new EPUB before replacing the original
            if not self._validate_epub(temp_file_path):
                return False, "Validation failed after saving. Save operation aborted."
                
            # Atomically move the temporary file to the final destination
            shutil.move(temp_file_path, target_path)
            return True, "EPUB written successfully."

        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as e:
            return False, f"Save error: {str(e)}"
        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _create_backup(self, epub_path: Path) -> Optional[str]:
        """Create a backup with rotation and return the backup path string."""
        if not epub_path.exists():
            return None
            
        backup_dir = epub_path.parent / self.backup_dir
        backup_dir.mkdir(exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_name = f"{epub_path.stem}_{timestamp}.bak"
        backup_path = backup_dir / backup_name
        
        try:
            shutil.copy2(epub_path, backup_path)
            self._rotate_backups(backup_dir)
            return f"Backup created at: {backup_path}"
        except OSError:
            return None

    def _rotate_backups(self, backup_dir: Path) -> None:
        """Rotate backups to prevent storage overflow."""
        try:
            backups = sorted(
                [p for p in backup_dir.glob("*.bak") if p.is_file()],
                key=os.path.getmtime
            )
            
            while len(backups) > self.max_backups:
                oldest_backup = backups.pop(0)
                oldest_backup.unlink()
        except OSError:
            # Ignore errors during rotation (e.g., file locked)
            pass

    def _validate_epub(self, epub_path: Path) -> bool:
        """Basic EPUB validation focused on the mimetype file."""
        if not epub_path.exists():
            return False
            
        try:
            with zipfile.ZipFile(epub_path, 'r') as test_zip:
                infolist = test_zip.infolist()
                # Check required files
                if not infolist or 'META-INF/container.xml' not in test_zip.namelist():
                    return False
                    
                # Check mimetype is first and uncompressed
                mimetype_info = infolist[0]
                if mimetype_info.filename != 'mimetype' or mimetype_info.compress_type != zipfile.ZIP_STORED:
                    return False
                    
                if test_zip.read('mimetype') != b'application/epub+zip':
                    return False
                    
            return True
        except (zipfile.BadZipFile, KeyError, IndexError):
            return False

    def optimize_epub(self, epub_path: Path) -> Tuple[bool, str]:
        """
        Re-save the EPUB with maximum compression.
        Warning: This is a simple implementation and might not be safe for all EPUBs.
        A more advanced version would need to respect original compression types for certain files.
        """
        original_size = epub_path.stat().st_size
        
        # Use a high compression level
        self.compression_level = zipfile.ZIP_DEFLATED
        os.environ['DEFLATE_LEVEL'] = '9' # Hint for zlib if supported

        success, message = self._write_epub(epub_path, epub_path)
        
        # Reset compression level
        del os.environ['DEFLATE_LEVEL']

        if not success:
            return False, f"Optimization failed: {message}"

        optimized_size = epub_path.stat().st_size
        if optimized_size < original_size:
            return True, f"Optimized: {original_size / 1024:.1f} KB → {optimized_size / 1024:.1f} KB"
        else:
            return False, "No significant size reduction achieved."

    def verify_integrity(self, epub_path: Path) -> Dict[str, List[str]]:
        """Verify content integrity between manager and the source EPUB file."""
        results = {
            'missing_from_epub': [],
            'missing_from_manager': [],
            'mismatched_content': []
        }
        
        if not epub_path.exists():
            return {'error': ['EPUB file does not exist.']}

        try:
            with zipfile.ZipFile(epub_path, 'r') as epub_zip:
                epub_files = {item.filename.replace('\\', '/') for item in epub_zip.infolist()}
                manager_files = set(self.content_manager.content_map.keys())
                
                results['missing_from_epub'] = list(manager_files - epub_files)
                results['missing_from_manager'] = list(epub_files - manager_files)
                
                # Check content mismatches for files present in both
                for file_name in manager_files.intersection(epub_files):
                    try:
                        zip_content_bytes = epub_zip.read(file_name)
                        zip_content = zip_content_bytes.decode('utf-8')
                        manager_content = self.content_manager.get_content(file_name)
                        
                        if manager_content != zip_content:
                            results['mismatched_content'].append(file_name)
                    except (KeyError, UnicodeDecodeError):
                        # Could not read or decode file from zip, consider it a mismatch
                        results['mismatched_content'].append(file_name)

            return results
        except (OSError, zipfile.BadZipFile):
            return {'error': ['Failed to read EPUB file.']}