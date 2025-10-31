"""Git analysis functionality for finding fixup targets."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import difflib
import threading
import time
import sys

import git


class _ProgressBar:
    """Simple progress bar for showing progress during author scanning."""
    
    def __init__(self, message: str, total: int, width: int = 40):
        self.message = message
        self.total = total
        self.width = width
        self.current = 0
    
    def update(self, current: int):
        """Update the progress bar."""
        self.current = current
        if self.total == 0:
            percent = 100
        else:
            percent = int((current / self.total) * 100)
        
        filled = int((current / self.total) * self.width) if self.total > 0 else self.width
        bar = '█' * filled + '░' * (self.width - filled)
        
        sys.stdout.write(f'\r{self.message} [{bar}] {current}/{self.total} ({percent}%)')
        sys.stdout.flush()
    
    def finish(self):
        """Complete the progress bar and add newline."""
        self.update(self.total)
        sys.stdout.write('\n')
        sys.stdout.flush()


class ChangeClassification(Enum):
    """Classification of change types."""
    LIKELY_FIXUP = "likely_fixup"          # Small fixes, typos, style changes
    POSSIBLE_FIXUP = "possible_fixup"       # Could be fixup or small feature
    UNLIKELY_FIXUP = "unlikely_fixup"       # Large additions, new features
    NEW_FILE = "new_file"                   # Completely new files


class FilterMode(Enum):
    """Filtering modes for change analysis."""
    SMART_DEFAULT = "smart_default"         # Use heuristics to filter likely fixups
    FIXUPS_ONLY = "fixups_only"            # Only show high-confidence fixups
    INCLUDE_ALL = "include_all"             # Show all changes regardless


@dataclass(frozen=True)
class ChangedLine:
    """Represents a changed line in a file."""
    file_path: str
    line_number: int
    content: str
    change_type: str  # 'added', 'modified', 'deleted'
    classification: ChangeClassification = ChangeClassification.POSSIBLE_FIXUP
    context_lines: Optional[List[str]] = None  # Surrounding lines for better analysis


@dataclass(frozen=True)
class BlameInfo:
    """Information from git blame for a specific line."""
    commit_hash: str
    commit_message: str
    author: str
    line_content: str


@dataclass
class FixupTarget:
    """A target commit for creating fixups."""
    commit_hash: str
    commit_message: str
    author: str
    changed_lines: List[ChangedLine]
    files: Set[str]


class ChangeClassifier:
    """Classifies changes to determine fixup likelihood."""
    
    def __init__(self, repo: git.Repo):
        self.repo = repo
    
    def classify_change(self, change: ChangedLine, target_commit_hash: str = None) -> ChangeClassification:
        """Classify a change based on multiple heuristics."""
        # Check if it's a new file
        if self._is_new_file(change.file_path):
            return ChangeClassification.NEW_FILE
        
        # Content-based heuristics
        if self._is_likely_fixup_content(change):
            return ChangeClassification.LIKELY_FIXUP
        
        # Size-based heuristics
        if self._is_large_change(change):
            return ChangeClassification.UNLIKELY_FIXUP
        
        # Time-based heuristics (if target commit provided)
        if target_commit_hash and self._is_old_commit(target_commit_hash):
            return ChangeClassification.UNLIKELY_FIXUP
        
        # Structure-based heuristics
        if self._adds_new_structure(change):
            return ChangeClassification.UNLIKELY_FIXUP
        
        return ChangeClassification.POSSIBLE_FIXUP
    
    def _is_new_file(self, file_path: str) -> bool:
        """Check if this is a completely new file."""
        try:
            # Try to get the file from HEAD
            self.repo.git.show(f"HEAD:{file_path}")
            return False
        except git.exc.GitCommandError:
            return True
    
    def _is_likely_fixup_content(self, change: ChangedLine) -> bool:
        """Check if content suggests this is likely a fixup."""
        content = change.content.strip().lower()
        
        # Typo fixes and small corrections
        fixup_patterns = [
            r'\b(fix|correct|update)\b',  # Fix/correct/update
            r'\b(typo|spelling|grammar)\b',  # Typo fixes
            r'\b(format|style|indent)\b',  # Style fixes
            r'^\s*(#|//|\*)',  # Comment changes
            r'^[^a-zA-Z]*$',  # Only symbols/numbers (formatting)
            r'^\s*["\'].*["\'][\s,;]*$',  # String literal changes
        ]
        
        for pattern in fixup_patterns:
            if re.search(pattern, content):
                return True
        
        # Small single-character or word changes
        if len(content) < 10:
            return True
        
        return False
    
    def _is_large_change(self, change: ChangedLine) -> bool:
        """Check if this is a large change suggesting new feature."""
        content = change.content.strip()
        
        # Long lines suggest substantial additions
        if len(content) > 100:
            return True
        
        # Complex expressions suggest new logic
        complexity_indicators = [
            r'def\s+\w+\s*\(',  # New function definition
            r'class\s+\w+',     # New class definition
            r'import\s+\w+',    # New imports
            r'if\s+.*:\s*$',    # New conditional blocks
            r'for\s+.*:\s*$',   # New loops
            r'while\s+.*:\s*$', # New while loops
        ]
        
        for pattern in complexity_indicators:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _is_old_commit(self, commit_hash: str, days_threshold: int = 30) -> bool:
        """Check if the target commit is old (less likely to need fixups)."""
        try:
            commit = self.repo.commit(commit_hash)
            commit_date = datetime.fromtimestamp(commit.committed_date)
            age = datetime.now() - commit_date
            return age > timedelta(days=days_threshold)
        except:
            return False
    
    def _adds_new_structure(self, change: ChangedLine) -> bool:
        """Check if change adds new structural elements."""
        content = change.content.strip()
        
        # Look for new structural additions
        structure_patterns = [
            r'^\s*def\s+\w+',      # New function
            r'^\s*class\s+\w+',    # New class  
            r'^\s*if\s+__name__',  # New main block
            r'^\s*@\w+',           # New decorator
            r'^\s*from\s+\w+\s+import',  # New imports
        ]
        
        for pattern in structure_patterns:
            if re.search(pattern, content):
                return True
        
        return False


class GitAnalyzer:
    """Analyzes git repository to find fixup targets."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize with repository path."""
        self.repo = git.Repo(repo_path)
        self.repo_path = Path(repo_path)
        self.classifier = ChangeClassifier(self.repo)
    
    def get_changed_lines(self) -> List[ChangedLine]:
        """Get all changed lines in the working directory."""
        changed_lines = []
        
        # Get unstaged changes
        diff = self.repo.git.diff('HEAD', unified=0)
        changed_lines.extend(self._parse_diff(diff, 'unstaged'))
        
        # Get staged changes
        diff = self.repo.git.diff('--cached', unified=0)
        changed_lines.extend(self._parse_diff(diff, 'staged'))
        
        # Post-process to detect delete/add pairs as modifications
        enhanced_lines = self._enhance_change_detection(changed_lines)
        
        # Classify all changes for fixup likelihood
        classified_lines = self._classify_changes(enhanced_lines)
        
        return classified_lines
    
    def _parse_diff(self, diff_output: str, change_source: str) -> List[ChangedLine]:
        """Parse git diff output to extract changed lines."""
        changed_lines = []
        current_file = None
        
        for line in diff_output.split('\n'):
            if line.startswith('diff --git'):
                # Extract file path from: diff --git a/path/file.c b/path/file.c
                match = re.search(r'diff --git a/(.+) b/(.+)$', line)
                if match:
                    # Use the 'b/' path (destination) as it's more reliable
                    current_file = match.group(2)
            elif line.startswith('@@'):
                # Parse hunk header to get line numbers
                match = re.search(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match and current_file:
                    old_start = int(match.group(1))
                    new_start = int(match.group(3))
                    # We'll track line numbers as we process the hunk
                    old_line_num = old_start
                    new_line_num = new_start
            elif line.startswith('-') and not line.startswith('---'):
                # Deleted line
                if current_file:
                    changed_lines.append(ChangedLine(
                        file_path=current_file,
                        line_number=old_line_num,
                        content=line[1:],
                        change_type='deleted'
                    ))
                    old_line_num += 1
            elif line.startswith('+') and not line.startswith('+++'):
                # Added line
                if current_file:
                    changed_lines.append(ChangedLine(
                        file_path=current_file,
                        line_number=new_line_num,
                        content=line[1:],
                        change_type='added'
                    ))
                    new_line_num += 1
            elif line.startswith(' '):
                # Unchanged line (context)
                old_line_num += 1
                new_line_num += 1
        
        return changed_lines
    
    def _enhance_change_detection(self, changed_lines: List[ChangedLine]) -> List[ChangedLine]:
        """Enhance change detection by pairing similar delete/add operations as modifications."""
        # Group lines by file and line numbers that are close to each other
        file_groups = {}
        for line in changed_lines:
            if line.file_path not in file_groups:
                file_groups[line.file_path] = []
            file_groups[line.file_path].append(line)
        
        enhanced_lines = []
        
        for file_path, lines in file_groups.items():
            # Separate deleted and added lines
            deleted_lines = [l for l in lines if l.change_type == 'deleted']
            added_lines = [l for l in lines if l.change_type == 'added']
            other_lines = [l for l in lines if l.change_type not in ['deleted', 'added']]
            
            # Keep track of which lines we've paired
            used_deleted = set()
            used_added = set()
            
            # Try to pair deleted and added lines that are similar
            for del_line in deleted_lines:
                if del_line in used_deleted:
                    continue
                    
                best_match = None
                best_similarity = 0.0
                
                for add_line in added_lines:
                    if add_line in used_added:
                        continue
                    
                    # Check if lines are close in location (within ~5 lines)
                    line_distance = abs(add_line.line_number - del_line.line_number)
                    if line_distance > 5:
                        continue
                    
                    # Calculate content similarity
                    similarity = self._calculate_similarity(del_line.content, add_line.content)
                    
                    # Consider it a match if similarity > 60% and they're close
                    if similarity > 0.6 and similarity > best_similarity:
                        best_match = add_line
                        best_similarity = similarity
                
                if best_match:
                    # Create a modified line using the deleted line's position for blame
                    modified_line = ChangedLine(
                        file_path=del_line.file_path,
                        line_number=del_line.line_number,  # Use original line number for blame
                        content=best_match.content,        # New content
                        change_type='modified'             # Mark as modification
                    )
                    enhanced_lines.append(modified_line)
                    used_deleted.add(del_line)
                    used_added.add(best_match)
                else:
                    # No match found, keep as deleted
                    enhanced_lines.append(del_line)
            
            # Add remaining unmatched lines
            for del_line in deleted_lines:
                if del_line not in used_deleted:
                    enhanced_lines.append(del_line)
            
            for add_line in added_lines:
                if add_line not in used_added:
                    enhanced_lines.append(add_line)
            
            # Add other line types unchanged
            enhanced_lines.extend(other_lines)
        
        return enhanced_lines
    
    def _classify_changes(self, changed_lines: List[ChangedLine]) -> List[ChangedLine]:
        """Classify all changes for fixup likelihood."""
        classified_lines = []
        
        for line in changed_lines:
            classification = self.classifier.classify_change(line)
            
            # Create new ChangedLine with classification
            classified_line = ChangedLine(
                file_path=line.file_path,
                line_number=line.line_number,
                content=line.content,
                change_type=line.change_type,
                classification=classification,
                context_lines=line.context_lines
            )
            classified_lines.append(classified_line)
        
        return classified_lines
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using difflib."""
        # Remove leading/trailing whitespace for comparison
        str1 = str1.strip()
        str2 = str2.strip()
        
        if not str1 or not str2:
            return 0.0
        
        # Use difflib's SequenceMatcher to calculate similarity
        matcher = difflib.SequenceMatcher(None, str1, str2)
        return matcher.ratio()
    
    def get_blame_info(self, file_path: str, line_number: int) -> Optional[BlameInfo]:
        """Get blame information for a specific line."""
        try:
            blame_output = self.repo.git.blame(
                'HEAD',
                file_path,
                L=f'{line_number},{line_number}',
                porcelain=True
            )
            
            lines = blame_output.strip().split('\n')
            if not lines:
                return None
            
            # Parse porcelain format
            first_line = lines[0]
            commit_hash = first_line.split()[0]
            
            # Extract commit info
            commit = self.repo.commit(commit_hash)
            
            # Find the actual line content
            line_content = ""
            for line in lines:
                if line.startswith('\t'):
                    line_content = line[1:]
                    break
            
            return BlameInfo(
                commit_hash=commit_hash,
                commit_message=commit.message.strip(),
                author=f"{commit.author.name} <{commit.author.email}>",
                line_content=line_content
            )
        
        except git.exc.GitCommandError:
            return None
    
    def find_fixup_targets(self, filter_mode: FilterMode = FilterMode.SMART_DEFAULT, progress_callback=None, limit_sha: Optional[str] = None) -> List[FixupTarget]:
        """Find all potential fixup targets based on current changes.

        Args:
            filter_mode: How to filter the results (SMART_DEFAULT, FIXUPS_ONLY, INCLUDE_ALL)
            progress_callback: Optional callback function for progress updates
            limit_sha: Optional SHA1 to limit search to commits after this point
        """
        if progress_callback:
            progress_callback("🔄 Getting changed lines...")
        changed_lines = self.get_changed_lines()
        
        # Group changed lines by their original commits
        commit_groups: Dict[str, List[ChangedLine]] = {}
        
        if progress_callback:
            progress_callback(f"🔍 Analyzing {len(changed_lines)} changed lines...")
        
        for i, changed_line in enumerate(changed_lines):
            # Update progress every 10 lines for larger changes
            if progress_callback and len(changed_lines) > 20 and i % 10 == 0:
                progress_callback(f"🔍 Processing line {i+1}/{len(changed_lines)}...")
            # For deleted/modified lines, find the original commit
            if changed_line.change_type in ['deleted', 'modified']:
                blame_info = self.get_blame_info(
                    changed_line.file_path, 
                    changed_line.line_number
                )
                if blame_info:
                    commit_hash = blame_info.commit_hash
                    if commit_hash not in commit_groups:
                        commit_groups[commit_hash] = []
                    commit_groups[commit_hash].append(changed_line)
            
            # For added lines, we need to find the context
            elif changed_line.change_type == 'added':
                # Find the commit of nearby lines for context
                context_commits = self._find_context_commits(
                    changed_line.file_path, 
                    changed_line.line_number
                )
                if context_commits:
                    # Use the most recent context commit
                    commit_hash = context_commits[0]
                    if commit_hash not in commit_groups:
                        commit_groups[commit_hash] = []
                    commit_groups[commit_hash].append(changed_line)
        
        # Convert to FixupTarget objects
        fixup_targets = []
        for commit_hash, lines in commit_groups.items():
            try:
                commit = self.repo.commit(commit_hash)
                files = {line.file_path for line in lines}
                
                fixup_targets.append(FixupTarget(
                    commit_hash=commit_hash,
                    commit_message=commit.message.strip(),
                    author=f"{commit.author.name} <{commit.author.email}>",
                    changed_lines=lines,
                    files=files
                ))
            except git.exc.BadName:
                continue
        
        # Apply filtering based on filter mode
        if progress_callback:
            progress_callback("🎯 Applying filters...")
        filtered_targets = self._filter_targets_by_mode(fixup_targets, filter_mode)

        # Filter by limit_sha if provided
        if limit_sha:
            try:
                # Get the short SHA for comparison
                limit_short = limit_sha[:7] if len(limit_sha) >= 7 else limit_sha

                # Only keep targets that are at or after the limit SHA
                # Get the list of commits after limit_sha
                try:
                    commits_after = self.repo.git.rev_list(f"{limit_sha}...HEAD").split('\n')
                    commits_after_set = set(c[:7] for c in commits_after if c)
                    commits_after_set.add(limit_short)  # Include the limit SHA itself

                    filtered_targets = [t for t in filtered_targets if t.commit_hash[:7] in commits_after_set]
                except git.exc.GitCommandError:
                    raise ValueError(f"Invalid SHA1 limit: {limit_sha}")
            except Exception as e:
                raise ValueError(f"Error filtering by limit SHA '{limit_sha}': {e}")

        if progress_callback:
            progress_callback("✅ Analysis complete")

        return filtered_targets
    
    def filter_targets_by_organization(self, targets: List[FixupTarget], org_email_pattern: str) -> List[FixupTarget]:
        """Filter targets to only include commits by authors matching the organization email pattern.
        
        Args:
            targets: List of fixup targets to filter
            org_email_pattern: Regex pattern to match against author email addresses
            
        Returns:
            Filtered list containing only targets where author email matches the pattern
            
        Raises:
            ValueError: If email pattern is invalid or matches no authors in repository
        """
        try:
            pattern = re.compile(org_email_pattern, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Invalid email pattern '{org_email_pattern}': {e}")
        
        # Note: We don't validate if the pattern matches any authors here anymore.
        # The CLI will handle showing appropriate messages about unmatched patterns.
        
        filtered_targets = []
        for target in targets:
            # Extract email from author string (format is usually "Name <email>")
            author_email = self._extract_email_from_author(target.author)
            if author_email and pattern.search(author_email):
                filtered_targets.append(target)
        
        return filtered_targets
    
    def _extract_email_from_author(self, author_str: str) -> Optional[str]:
        """Extract email address from author string.
        
        Author strings are typically in format "Name <email>" or just "email".
        
        Args:
            author_str: Author string from git commit
            
        Returns:
            Email address if found, None otherwise
        """
        # Match email in angle brackets: "Name <email@domain.com>"
        email_match = re.search(r'<([^>]+)>', author_str)
        if email_match:
            return email_match.group(1)
        
        # If no angle brackets, check if the whole string looks like an email
        if '@' in author_str and '.' in author_str:
            # Simple check if it's just an email address
            email_match = re.search(r'\S+@\S+\.\S+', author_str)
            if email_match:
                return email_match.group(0)
        
        return None
    
    def get_diff_context(self, target: 'FixupTarget', context_lines: int = 3) -> Optional[str]:
        """Get diff context showing what changes would fix in the target commit.
        
        Args:
            target: The fixup target to show context for
            context_lines: Number of context lines to show around changes
            
        Returns:
            Formatted diff string showing the changes, or None if unable to generate
        """
        try:
            # Get the diff for files that have changes in both current working dir and target commit
            target_files = target.files
            current_changes = self.get_changed_lines()
            current_files = {change.file_path for change in current_changes if change.file_path in target_files}
            
            if not current_files:
                return None
            
            diff_output = []
            diff_output.append(f"📋 Diff context for fixup target {target.commit_hash[:8]}:")
            diff_output.append(f"📝 Target commit: {target.commit_message}")
            diff_output.append("")
            
            for file_path in sorted(current_files):
                # Get the version of the file at the target commit
                try:
                    target_commit = self.repo.commit(target.commit_hash)
                    target_blob = target_commit.tree[file_path]
                    target_content = target_blob.data_stream.read().decode('utf-8', errors='replace')
                except (KeyError, UnicodeDecodeError):
                    continue
                
                # Get current working directory version
                try:
                    with open(self.repo_path / file_path, 'r', encoding='utf-8', errors='replace') as f:
                        current_content = f.read()
                except (FileNotFoundError, UnicodeDecodeError):
                    continue
                
                # Generate unified diff
                target_lines = target_content.splitlines(keepends=True)
                current_lines = current_content.splitlines(keepends=True)
                
                diff_lines = list(difflib.unified_diff(
                    target_lines,
                    current_lines,
                    fromfile=f"a/{file_path} (target commit {target.commit_hash[:8]})",
                    tofile=f"b/{file_path} (current changes)",
                    n=context_lines
                ))
                
                if diff_lines:
                    diff_output.append(f"🔍 {file_path}:")
                    for line in diff_lines[2:]:  # Skip the file headers
                        diff_output.append(f"    {line.rstrip()}")
                    diff_output.append("")
            
            return '\n'.join(diff_output) if len(diff_output) > 3 else None
            
        except Exception:
            return None
    
    def _filter_targets_by_mode(self, targets: List[FixupTarget], filter_mode: FilterMode) -> List[FixupTarget]:
        """Filter fixup targets based on the specified filter mode."""
        if filter_mode == FilterMode.INCLUDE_ALL:
            return targets
        
        filtered_targets = []
        for target in targets:
            # Analyze the classification of changes in this target
            classifications = [line.classification for line in target.changed_lines]
            
            if filter_mode == FilterMode.FIXUPS_ONLY:
                # Only include targets with mostly likely fixups
                likely_count = classifications.count(ChangeClassification.LIKELY_FIXUP)
                total_count = len(classifications)
                if likely_count / total_count >= 0.5:  # At least 50% likely fixups
                    filtered_targets.append(target)
            
            elif filter_mode == FilterMode.SMART_DEFAULT:
                # Exclude targets that are clearly new features
                new_file_count = classifications.count(ChangeClassification.NEW_FILE)
                unlikely_count = classifications.count(ChangeClassification.UNLIKELY_FIXUP)
                total_count = len(classifications)
                
                # Skip if most changes are new files or unlikely fixups
                if (new_file_count + unlikely_count) / total_count < 0.7:  # Less than 70% unlikely
                    filtered_targets.append(target)
        
        return filtered_targets
    
    def _find_context_commits(self, file_path: str, line_number: int) -> List[str]:
        """Find commits of nearby lines for context."""
        context_commits = []
        
        # Check lines before and after for context
        for offset in [-2, -1, 1, 2]:
            target_line = line_number + offset
            if target_line > 0:
                blame_info = self.get_blame_info(file_path, target_line)
                if blame_info:
                    context_commits.append(blame_info.commit_hash)
        
        # Return unique commits, most recent first
        unique_commits = list(dict.fromkeys(context_commits))
        return unique_commits