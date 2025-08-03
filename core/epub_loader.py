import zipfile
import re
import shutil
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from xml.etree import ElementTree as ET

class EPUBLoader:
    def __init__(self):
        self.epub_path: Optional[Path] = None
        self.content_map: Dict[str, str] = {}
        self.metadata: Dict[str, any] = {}
        self.structure: Dict[str, list] = {}
        self.progress_callback = None
        self.manifest: Dict[str, str] = {}
        self.spine: List[str] = []

    def validate_epub(self, file_path: Path) -> bool:
        """Validate EPUB file structure"""
        if not file_path.exists() or file_path.suffix.lower() != '.epub':
            return False
        
        try:
            with zipfile.ZipFile(file_path, 'r') as epub:
                # Check essential files
                if 'mimetype' not in epub.namelist() or 'META-INF/container.xml' not in epub.namelist():
                    return False
                
                # Check mimetype is first and uncompressed
                mimetype_info = epub.infolist()[0]
                if mimetype_info.filename != 'mimetype' or mimetype_info.compress_type != zipfile.ZIP_STORED:
                    return False

                if epub.read('mimetype') != b'application/epub+zip':
                    return False
            return True
        except (zipfile.BadZipFile, KeyError, OSError, IndexError):
            return False

    def load_epub(
        self, 
        file_path: Path, 
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Load EPUB content efficiently with progress tracking"""
        self.progress_callback = progress_callback
        self.epub_path = file_path
        
        if not self.validate_epub(file_path):
            return False

        try:
            with zipfile.ZipFile(file_path, 'r') as epub:
                opf_path = self._get_opf_path(epub)
                if not opf_path:
                    return False
                
                opf_dir = Path(opf_path).parent
                self._parse_opf(epub, opf_path, opf_dir)

                total_files = len(self.manifest)
                for i, (item_id, href) in enumerate(self.manifest.items()):
                    file_path_in_zip = str(opf_dir / href).replace('\\', '/')
                    
                    if self.progress_callback:
                        self.progress_callback(i, total_files, f"Loading {file_path_in_zip}")
                    
                    try:
                        content = epub.read(file_path_in_zip)
                        if self._is_content_file(href):
                            encoding = self._detect_encoding(content)
                            self.content_map[file_path_in_zip] = content.decode(encoding)
                        else:
                            # For binary files, we could store them as bytes or ignore
                            pass
                    except (KeyError, UnicodeDecodeError):
                        # File in manifest but not in zip, or not text; skip.
                        continue
                
                self._analyze_structure()
                return True
        except (zipfile.BadZipFile, OSError, ET.ParseError):
            return False

    def _get_opf_path(self, epub: zipfile.ZipFile) -> Optional[str]:
        """Parse container.xml to find the .opf file path"""
        try:
            container_data = epub.read('META-INF/container.xml')
            root = ET.fromstring(container_data)
            # Namespace for container.xml
            ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = root.find('c:rootfiles/c:rootfile', ns)
            if rootfile is not None:
                return rootfile.get('full-path')
            return None
        except (KeyError, ET.ParseError):
            return None

    def _parse_opf(self, epub: zipfile.ZipFile, opf_path: str, opf_dir: Path):
        """Parse the .opf file for manifest, spine, and metadata."""
        opf_data = epub.read(opf_path)
        root = ET.fromstring(opf_data)
        
        # Namespaces are crucial for parsing .opf files
        ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

        # Parse manifest
        for item in root.findall('opf:manifest/opf:item', ns):
            item_id = item.get('id')
            href = item.get('href')
            if item_id and href:
                self.manifest[item_id] = href
        
        # Parse spine (reading order)
        for itemref in root.findall('opf:spine/opf:itemref', ns):
            idref = itemref.get('idref')
            if idref and idref in self.manifest:
                # Store the href (actual file path) in the spine
                self.spine.append(str(opf_dir / self.manifest[idref]).replace('\\', '/'))

        # Parse metadata
        metadata_elem = root.find('opf:metadata', ns)
        if metadata_elem is not None:
            for child in metadata_elem:
                tag = child.tag.split('}')[-1]
                # Handle attributes, e.g., opf:role on dc:creator
                attribs = {key.split('}')[-1]: value for key, value in child.attrib.items()}
                
                if tag not in self.metadata:
                    self.metadata[tag] = []
                
                self.metadata[tag].append({
                    'text': child.text,
                    'attrib': attribs
                })

    def _is_content_file(self, file_name: str) -> bool:
        """Check if file is text-based content"""
        return any(file_name.lower().endswith(ext) for ext in 
                ['.html', '.xhtml', '.xml', '.opf', '.ncx', '.css', '.js', '.txt'])

    def _detect_encoding(self, content: bytes) -> str:
        """Detect text encoding"""
        if content.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig' # More specific for BOM
        if content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
            return 'utf-16'
        
        try:
            # Check XML declaration, a more robust way
            match = re.search(br'^\s*<\?xml[^>]+encoding="([^"]+)"', content)
            if match:
                return match.group(1).decode('ascii')
        except (re.error, IndexError):
            pass
        
        # Default to UTF-8 as per EPUB spec for files without BOM or declaration
        return 'utf-8'

    def _analyze_structure(self) -> None:
        """Analyze file relationships and structure from the manifest."""
        file_list = list(self.content_map.keys())
        self.structure = {
            'html': [], 'styles': [], 'metadata_files': [], 'images': [], 'fonts': [], 'other': []
        }
        for file_path in file_list:
            if file_path.lower().endswith(('.html', '.xhtml')):
                self.structure['html'].append(file_path)
            elif file_path.lower().endswith('.css'):
                self.structure['styles'].append(file_path)
            elif file_path.lower().endswith(('.opf', '.ncx')):
                self.structure['metadata_files'].append(file_path)
            elif re.search(r'\.(jpg|jpeg|png|gif|svg|webp)$', file_path, re.I):
                self.structure['images'].append(file_path)
            elif re.search(r'\.(ttf|otf|woff|woff2)$', file_path, re.I):
                self.structure['fonts'].append(file_path)
            else:
                self.structure['other'].append(file_path)

    def create_backup(self, backup_path: Path) -> bool:
        """Create backup of original EPUB"""
        if not self.epub_path or not self.epub_path.exists():
            return False
        try:
            shutil.copy2(self.epub_path, backup_path)
            return True
        except OSError:
            return False