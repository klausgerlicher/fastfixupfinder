"""Git analysis functionality for finding fixup targets."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import git


@dataclass
class ChangedLine:
    """Represents a changed line in a file."""
    file_path: str
    line_number: int
    content: str
    change_type: str  # 'added', 'modified', 'deleted'


@dataclass
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


class GitAnalyzer:
    """Analyzes git repository to find fixup targets."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize with repository path."""
        self.repo = git.Repo(repo_path)
        self.repo_path = Path(repo_path)
    
    def get_changed_lines(self) -> List[ChangedLine]:
        """Get all changed lines in the working directory."""
        changed_lines = []
        
        # Get unstaged changes
        diff = self.repo.git.diff('HEAD', unified=0)
        changed_lines.extend(self._parse_diff(diff, 'unstaged'))
        
        # Get staged changes
        diff = self.repo.git.diff('--cached', unified=0)
        changed_lines.extend(self._parse_diff(diff, 'staged'))
        
        return changed_lines
    
    def _parse_diff(self, diff_output: str, change_source: str) -> List[ChangedLine]:
        """Parse git diff output to extract changed lines."""
        changed_lines = []
        current_file = None
        
        for line in diff_output.split('\n'):
            if line.startswith('diff --git'):
                # Extract file path
                match = re.search(r'b/(.+)$', line)
                if match:
                    current_file = match.group(1)
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
                author=str(commit.author),
                line_content=line_content
            )
        
        except git.exc.GitCommandError:
            return None
    
    def find_fixup_targets(self) -> List[FixupTarget]:
        """Find all potential fixup targets based on current changes."""
        changed_lines = self.get_changed_lines()
        
        # Group changed lines by their original commits
        commit_groups: Dict[str, List[ChangedLine]] = {}
        
        for changed_line in changed_lines:
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
                    author=str(commit.author),
                    changed_lines=lines,
                    files=files
                ))
            except git.exc.BadName:
                continue
        
        return fixup_targets
    
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