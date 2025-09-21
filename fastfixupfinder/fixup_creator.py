"""Automated fixup commit creation functionality."""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import git

from .git_analyzer import FixupTarget, GitAnalyzer

# Color constants for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Basic colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    
    @staticmethod
    def colorize(text: str, color: str, bold: bool = False) -> str:
        """Apply color and formatting to text."""
        prefix = Colors.BOLD if bold else ""
        return f"{prefix}{color}{text}{Colors.RESET}"


class FixupCreator:
    """Creates fixup commits automatically."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize with repository path."""
        self.repo = git.Repo(repo_path)
        self.repo_path = Path(repo_path)
        self.analyzer = GitAnalyzer(repo_path)
    
    def create_fixup_commits(self, dry_run: bool = False, auto_backup: bool = True) -> List[str]:
        """Create fixup commits for all identified targets."""
        fixup_targets = self.analyzer.find_fixup_targets()  # Uses SMART_DEFAULT
        created_commits = []
        
        if not fixup_targets:
            print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
            print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
            return created_commits
        
        # Store target commits for later rebase suggestion
        self._target_commits = [target.commit_hash for target in fixup_targets]
        
        # Create automatic backup before making changes
        if not dry_run and auto_backup:
            self._create_safety_backup()
        
        # Stage all changes first
        self.repo.git.add('.')
        
        for target in fixup_targets:
            commit_hash = self.create_fixup_commit(target, dry_run)
            if commit_hash:
                created_commits.append(commit_hash)
        
        return created_commits
    
    def create_fixup_commit(self, target: FixupTarget, dry_run: bool = False) -> Optional[str]:
        """Create a single fixup commit for the given target."""
        try:
            # Create commit message
            short_hash = target.commit_hash[:8]
            commit_msg = f"fixup! {target.commit_message}"
            
            if dry_run:
                target_hash = Colors.colorize(short_hash, Colors.BRIGHT_CYAN, bold=True)
                message = Colors.colorize(target.commit_message, Colors.WHITE, bold=True)
                print(f"🔍 Would create fixup commit for {target_hash}: {message}")
                
                files_text = Colors.colorize(', '.join(target.files), Colors.BLUE)
                print(f"  📁 Files: {files_text}")
                
                lines_count = Colors.colorize(str(len(target.changed_lines)), Colors.BRIGHT_YELLOW)
                print(f"  📝 Changed lines: {lines_count}")
                return None
            
            # Stage only the files related to this target
            staged_files = []
            for file_path in target.files:
                if (self.repo_path / file_path).exists():
                    self.repo.git.add(file_path)
                    staged_files.append(file_path)
            
            if not staged_files:
                target_hash = Colors.colorize(short_hash, Colors.BRIGHT_CYAN, bold=True)
                print(Colors.colorize(f"⚠️  No files to stage for target {target_hash}", Colors.YELLOW))
                return None
            
            # Create the fixup commit
            commit = self.repo.index.commit(commit_msg)
            new_hash = Colors.colorize(commit.hexsha[:8], Colors.BRIGHT_GREEN, bold=True)
            target_hash = Colors.colorize(short_hash, Colors.BRIGHT_CYAN, bold=True)
            print(f"✅ Created fixup commit {new_hash} for {target_hash}")
            
            return commit.hexsha
            
        except Exception as e:
            target_hash = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)
            error_msg = Colors.colorize(f"❌ Error creating fixup commit for {target_hash}: {e}", Colors.BRIGHT_RED)
            print(error_msg)
            return None
    
    def interactive_fixup_selection(self, compact_mode: bool = False) -> List[str]:
        """Interactively select which fixup commits to create with line-level control.
        
        Args:
            compact_mode: Use compact output for better readability with many changes
        """
        fixup_targets = self.analyzer.find_fixup_targets()  # Uses SMART_DEFAULT
        created_commits = []
        
        if not fixup_targets:
            print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
            print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
            return created_commits
        
        count_text = Colors.colorize(str(len(fixup_targets)), Colors.BRIGHT_GREEN, bold=True)
        header = f"🧠 Enhanced interactive mode with line-level classification control"
        print(Colors.colorize(header, Colors.WHITE, bold=True))
        print(f"Found {count_text} potential fixup target{'s' if len(fixup_targets) != 1 else ''}:")
        print()
        
        # Get user selection of targets first
        selected_targets = self._interactive_target_selection(fixup_targets)
        if not selected_targets:
            return created_commits
        
        # For each selected target, allow line-level classification control
        final_targets = []
        for target in selected_targets:
            enhanced_target = self._interactive_line_classification(target, compact_mode)
            if enhanced_target and enhanced_target.changed_lines:
                final_targets.append(enhanced_target)
        
        if not final_targets:
            print(Colors.colorize("❌ No lines selected for fixup. Exiting.", Colors.YELLOW))
            return created_commits
        
        # Store target commits for later rebase suggestion
        self._target_commits = [target.commit_hash for target in final_targets]
        
        # Stage all changes first
        self.repo.git.add('.')
        
        # Create selected fixup commits
        for target in final_targets:
            commit_hash = self.create_fixup_commit(target)
            if commit_hash:
                created_commits.append(commit_hash)
        
        return created_commits
    
    def _interactive_target_selection(self, fixup_targets: List[FixupTarget]) -> List[FixupTarget]:
        """Interactive selection of target commits."""
        for i, target in enumerate(fixup_targets, 1):
            target_num = Colors.colorize(f"{i}.", Colors.BRIGHT_MAGENTA, bold=True)
            short_hash = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)
            message = Colors.colorize(target.commit_message, Colors.WHITE, bold=True)
            print(f"{target_num} {short_hash}: {message}")
            
            author = Colors.colorize(f"   👤 Author: {target.author}", Colors.DIM)
            print(author)
            
            files_text = Colors.colorize(', '.join(target.files), Colors.BLUE)
            print(f"   📁 Files: {files_text}")
            
            lines_count = Colors.colorize(str(len(target.changed_lines)), Colors.BRIGHT_YELLOW)
            print(f"   📝 Changed lines: {lines_count}")
            print()
        
        # Get user selection
        while True:
            try:
                prompt = Colors.colorize("🎯 Select targets ", Colors.BRIGHT_CYAN, bold=True)
                options = Colors.colorize("(comma-separated numbers, 'all', or 'none')", Colors.DIM)
                selection = input(f"{prompt}{options}: ").strip()
                
                if selection.lower() == 'none':
                    print(Colors.colorize("❌ No targets selected. Exiting.", Colors.YELLOW))
                    return []
                elif selection.lower() == 'all':
                    return fixup_targets
                else:
                    selected_indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    # Validate indices
                    if all(0 <= i < len(fixup_targets) for i in selected_indices):
                        return [fixup_targets[i] for i in selected_indices]
                    else:
                        error_msg = Colors.colorize("❌ Invalid selection. Please try again.", Colors.BRIGHT_RED)
                        print(error_msg)
                        continue
            except ValueError:
                error_msg = Colors.colorize("❌ Invalid input. Please enter numbers separated by commas.", Colors.BRIGHT_RED)
                print(error_msg)
                continue
    
    def _interactive_line_classification(self, target: FixupTarget, compact_mode: bool = False) -> Optional[FixupTarget]:
        """Interactive classification control for individual lines within a target.
        
        Args:
            target: The fixup target to review
            compact_mode: Use compact output for better readability
        """
        print()
        header = f"🔍 Reviewing lines for target {target.commit_hash[:8]}: {target.commit_message[:50]}..."
        print(Colors.colorize(header, Colors.WHITE, bold=True))
        print()
        
        # Group lines by file for better organization
        files_lines = {}
        for line in target.changed_lines:
            if line.file_path not in files_lines:
                files_lines[line.file_path] = []
            files_lines[line.file_path].append(line)
        
        selected_lines = []
        
        for file_path, lines in files_lines.items():
            file_header = Colors.colorize(f"📄 {file_path}", Colors.BLUE, bold=True)
            print(file_header)
            if not compact_mode:
                print()
            
            # Show line count and summary in compact mode
            if compact_mode:
                total_lines = len(lines)
                likely_count = sum(1 for l in lines if l.classification.value == 'likely_fixup')
                possible_count = sum(1 for l in lines if l.classification.value == 'possible_fixup')
                unlikely_count = sum(1 for l in lines if l.classification.value == 'unlikely_fixup')
                
                summary = f"  {total_lines} lines: "
                if likely_count > 0:
                    summary += Colors.colorize(f"{likely_count} likely", Colors.BRIGHT_GREEN) + " "
                if possible_count > 0:
                    summary += Colors.colorize(f"{possible_count} possible", Colors.BRIGHT_YELLOW) + " "
                if unlikely_count > 0:
                    summary += Colors.colorize(f"{unlikely_count} unlikely", Colors.BRIGHT_RED)
                print(summary.strip())
            
            # Show individual lines (with limits in compact mode)
            display_lines = lines[:10] if compact_mode else lines
            
            for i, line in enumerate(display_lines, 1):
                # Show current classification with color coding
                classification_color = self._get_classification_color(line.classification)
                classification_short = line.classification.value.replace('_fixup', '').replace('_file', '').replace('_', ' ').title()
                
                # Show change type symbol
                if line.change_type == 'added':
                    symbol = Colors.colorize("+", Colors.BRIGHT_GREEN, bold=True)
                elif line.change_type == 'deleted':
                    symbol = Colors.colorize("-", Colors.BRIGHT_RED, bold=True)
                else:  # modified
                    symbol = Colors.colorize("~", Colors.BRIGHT_YELLOW, bold=True)
                
                line_num = Colors.colorize(f"L{line.line_number}", Colors.CYAN)
                
                if compact_mode:
                    # Compact format: shorter content and inline classification
                    content_preview = line.content[:40] + "..." if len(line.content) > 40 else line.content
                    content = Colors.colorize(content_preview.strip(), Colors.WHITE)
                    classification_text = Colors.colorize(f"[{classification_short}]", classification_color)
                    print(f"  {i}. {symbol} {line_num}: {content} {classification_text}")
                else:
                    # Full format: longer content and separate classification line
                    content_preview = line.content[:80] + "..." if len(line.content) > 80 else line.content
                    content = Colors.colorize(content_preview.strip(), Colors.WHITE)
                    classification_text = Colors.colorize(
                        line.classification.value.replace('_', ' ').title(), 
                        classification_color, bold=True
                    )
                    print(f"  {i}. {symbol} Line {line.line_number}: {content}")
                    print(f"     Classification: {classification_text}")
                    print()
            
            # Show truncation notice in compact mode
            if compact_mode and len(lines) > 10:
                remaining = len(lines) - 10
                truncated_msg = Colors.colorize(f"  ... and {remaining} more lines", Colors.DIM)
                print(truncated_msg)
            
            if not compact_mode:
                print()
            
            # Ask user which lines to include
            while True:
                try:
                    if compact_mode:
                        prompt = Colors.colorize(f"🎯 Select from {file_path[:20]}{'...' if len(file_path) > 20 else ''} ", Colors.BRIGHT_CYAN, bold=True)
                        options = Colors.colorize("(#s, 'all', 'none', 'auto')", Colors.DIM)
                    else:
                        prompt = Colors.colorize(f"🎯 Select lines from {file_path} ", Colors.BRIGHT_CYAN, bold=True)
                        options = Colors.colorize("(numbers, 'all', 'none', or 'auto' for current classification)", Colors.DIM)
                    selection = input(f"{prompt}{options}: ").strip()
                    
                    if selection.lower() == 'none':
                        break  # Skip this file
                    elif selection.lower() == 'all':
                        selected_lines.extend(lines)
                        break
                    elif selection.lower() == 'auto':
                        # Use current automatic classification - include likely and possible fixups
                        auto_lines = [l for l in lines if l.classification in [
                            ChangeClassification.LIKELY_FIXUP, 
                            ChangeClassification.POSSIBLE_FIXUP
                        ]]
                        selected_lines.extend(auto_lines)
                        auto_count = Colors.colorize(str(len(auto_lines)), Colors.BRIGHT_GREEN, bold=True)
                        print(f"  ✅ Auto-selected {auto_count} lines based on classification")
                        break
                    else:
                        # Parse line numbers
                        line_indices = []
                        for num_str in selection.split(','):
                            num_str = num_str.strip()
                            if '-' in num_str:  # Range like "1-3"
                                start, end = map(int, num_str.split('-'))
                                line_indices.extend(range(start-1, end))
                            else:
                                line_indices.append(int(num_str) - 1)
                        
                        # Validate indices
                        if all(0 <= i < len(lines) for i in line_indices):
                            selected_lines.extend([lines[i] for i in line_indices])
                            selected_count = Colors.colorize(str(len(line_indices)), Colors.BRIGHT_GREEN, bold=True)
                            print(f"  ✅ Selected {selected_count} lines")
                            break
                        else:
                            error_msg = Colors.colorize("❌ Invalid selection. Please try again.", Colors.BRIGHT_RED)
                            print(error_msg)
                            continue
                except ValueError:
                    error_msg = Colors.colorize("❌ Invalid input. Use numbers, ranges (1-3), or keywords.", Colors.BRIGHT_RED)
                    print(error_msg)
                    continue
            
            print()
        
        if not selected_lines:
            print(Colors.colorize("⚠️  No lines selected for this target.", Colors.YELLOW))
            return None
        
        # Create new target with only selected lines
        selected_files = {line.file_path for line in selected_lines}
        enhanced_target = FixupTarget(
            commit_hash=target.commit_hash,
            commit_message=target.commit_message,
            author=target.author,
            changed_lines=selected_lines,
            files=selected_files
        )
        
        total_selected = Colors.colorize(str(len(selected_lines)), Colors.BRIGHT_GREEN, bold=True)
        total_files = Colors.colorize(str(len(selected_files)), Colors.BRIGHT_BLUE, bold=True)
        print(f"✅ Final selection: {total_selected} lines across {total_files} files")
        
        return enhanced_target
    
    def _get_classification_color(self, classification: 'ChangeClassification') -> str:
        """Get color for classification display."""
        from .git_analyzer import ChangeClassification
        
        color_map = {
            ChangeClassification.LIKELY_FIXUP: Colors.BRIGHT_GREEN,
            ChangeClassification.POSSIBLE_FIXUP: Colors.BRIGHT_YELLOW,
            ChangeClassification.UNLIKELY_FIXUP: Colors.BRIGHT_RED,
            ChangeClassification.NEW_FILE: Colors.BRIGHT_MAGENTA
        }
        return color_map.get(classification, Colors.WHITE)
    
    def suggest_rebase_command(self, created_commits: List[str]) -> None:
        """Suggest the appropriate git rebase command."""
        if not created_commits:
            return
        
        # Use stored target commits from before fixup creation
        target_commits = getattr(self, '_target_commits', [])
        
        if not target_commits:
            # Fallback to generic suggestion
            print()
            header = Colors.colorize("🚀 To apply the fixup commits, run:", Colors.WHITE, bold=True)
            print(header)
            command = Colors.colorize("git rebase -i --autosquash HEAD~<number_of_commits>", Colors.BRIGHT_GREEN, bold=True)
            print(f"    {command}")
            hint = Colors.colorize("    (Replace <number_of_commits> with appropriate count)", Colors.DIM)
            print(hint)
            return
        
        # Find common ancestor or suggest interactive rebase
        try:
            # Get the oldest target commit
            oldest_commit = self.repo.git.merge_base(*target_commits).strip()
            parent_commit = self.repo.git.rev_parse(f"{oldest_commit}^")
            
            print()
            header = Colors.colorize("🚀 To apply the fixup commits, run:", Colors.WHITE, bold=True)
            print(header)
            command = Colors.colorize(f"git rebase -i --autosquash {parent_commit}", Colors.BRIGHT_GREEN, bold=True)
            print(f"    {command}")
            
        except git.exc.GitCommandError:
            print()
            header = Colors.colorize("🚀 To apply the fixup commits, run:", Colors.WHITE, bold=True)
            print(header)
            command = Colors.colorize("git rebase -i --autosquash HEAD~<number_of_commits>", Colors.BRIGHT_GREEN, bold=True)
            print(f"    {command}")
            hint = Colors.colorize("    (Replace <number_of_commits> with appropriate count)", Colors.DIM)
            print(hint)
    
    def _create_safety_backup(self) -> None:
        """Create automatic safety backup before making changes."""
        try:
            # Create a stash with timestamp
            timestamp = subprocess.run(
                ["date", "+%Y%m%d_%H%M%S"], 
                capture_output=True, 
                text=True
            ).stdout.strip()
            
            stash_message = f"fastfixupfinder_backup_{timestamp}"
            
            # Check if there are changes to stash
            status_output = self.repo.git.status("--porcelain")
            if status_output.strip():
                self.repo.git.stash("push", "-m", stash_message)
                print(f"🛡️  Safety backup created: {stash_message}")
                print("   To restore if needed: git stash list && git stash pop")
            else:
                print("ℹ️  No changes to backup")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not create safety backup: {e}")
            print("   Consider creating manual backup before proceeding")
    
    def restore_from_backup(self, backup_name: Optional[str] = None) -> bool:
        """Restore from a safety backup."""
        try:
            if backup_name:
                # Restore specific backup
                self.repo.git.stash("apply", backup_name)
            else:
                # List available backups
                stashes = self.repo.git.stash("list").split('\n')
                fastfixup_stashes = [s for s in stashes if 'fastfixupfinder_backup' in s]
                
                if not fastfixup_stashes:
                    print(Colors.colorize("🔍 No fastfixupfinder backups found", Colors.YELLOW))
                    return False
                
                header = Colors.colorize("📦 Available backups:", Colors.WHITE, bold=True)
                print(header)
                for i, stash in enumerate(fastfixup_stashes[:5]):  # Show last 5
                    backup_num = Colors.colorize(f"  {i}:", Colors.BRIGHT_MAGENTA, bold=True)
                    stash_info = Colors.colorize(stash, Colors.CYAN)
                    print(f"{backup_num} {stash_info}")
                
                prompt = Colors.colorize("🔄 Enter backup number to restore ", Colors.BRIGHT_CYAN, bold=True)
                options = Colors.colorize("(or 'cancel')", Colors.DIM)
                choice = input(f"{prompt}{options}: ")
                if choice.lower() == 'cancel':
                    print(Colors.colorize("❌ Restore cancelled.", Colors.YELLOW))
                    return False
                
                try:
                    idx = int(choice)
                    if 0 <= idx < len(fastfixup_stashes):
                        stash_ref = fastfixup_stashes[idx].split(':')[0]
                        self.repo.git.stash("apply", stash_ref)
                        backup_info = Colors.colorize(fastfixup_stashes[idx], Colors.CYAN)
                        success_msg = Colors.colorize(f"✅ Restored backup: {backup_info}", Colors.BRIGHT_GREEN)
                        print(success_msg)
                        return True
                    else:
                        error_msg = Colors.colorize("❌ Invalid selection", Colors.BRIGHT_RED)
                        print(error_msg)
                        return False
                except ValueError:
                    error_msg = Colors.colorize("❌ Invalid input", Colors.BRIGHT_RED)
                    print(error_msg)
                    return False
                    
        except Exception as e:
            error_msg = Colors.colorize(f"❌ Error restoring backup: {e}", Colors.BRIGHT_RED)
            print(error_msg)
            return False
    
    def status(self) -> None:
        """Show current status of potential fixup targets."""
        fixup_targets = self.analyzer.find_fixup_targets()  # Uses SMART_DEFAULT
        
        if not fixup_targets:
            print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
            print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
            return
        
        # Header with emoji and color
        count_text = Colors.colorize(str(len(fixup_targets)), Colors.BRIGHT_GREEN, bold=True)
        print(f"🎯 Found {count_text} potential fixup target{'s' if len(fixup_targets) != 1 else ''}:")
        print()
        
        for i, target in enumerate(fixup_targets, 1):
            short_hash = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)
            commit_msg = Colors.colorize(target.commit_message, Colors.WHITE, bold=True)
            print(f"• {short_hash}: {commit_msg}")
            
            # Author in dim color
            author_text = Colors.colorize(f"  👤 Author: {target.author}", Colors.DIM)
            print(author_text)
            
            # Files with emoji and count
            files_list = ', '.join(sorted(target.files))
            file_count = len(target.files)
            files_text = Colors.colorize(f"  📁 File{'s' if file_count != 1 else ''}: {files_list}", Colors.BLUE)
            print(files_text)
            
            # Changed lines with emoji
            lines_count = Colors.colorize(str(len(target.changed_lines)), Colors.BRIGHT_YELLOW)
            print(f"  📝 Changed lines: {lines_count}")
            
            # Show some example changes with colored symbols
            if target.changed_lines:
                print(Colors.colorize("  📋 Sample changes:", Colors.MAGENTA))
                for line in target.changed_lines[:3]:  # Show first 3 changes
                    change_type = line.change_type
                    if change_type == "added":
                        symbol = Colors.colorize("+", Colors.BRIGHT_GREEN, bold=True)
                    elif change_type == "deleted":
                        symbol = Colors.colorize("-", Colors.BRIGHT_RED, bold=True)
                    else:  # modified
                        symbol = Colors.colorize("~", Colors.BRIGHT_YELLOW, bold=True)
                    
                    file_line = Colors.colorize(f"{line.file_path}:{line.line_number}", Colors.CYAN)
                    print(f"    {symbol} {file_line}")
                
                if len(target.changed_lines) > 3:
                    more_text = Colors.colorize(f"    ... and {len(target.changed_lines) - 3} more", Colors.DIM)
                    print(more_text)
            
            print()
    
    def status_oneline(self) -> None:
        """Show current status of potential fixup targets in compact one-line format."""
        fixup_targets = self.analyzer.find_fixup_targets()  # Uses SMART_DEFAULT
        
        if not fixup_targets:
            print(Colors.colorize("No fixup targets found.", Colors.YELLOW))
            return
        
        # Simple header for oneline mode
        count_text = Colors.colorize(str(len(fixup_targets)), Colors.BRIGHT_GREEN, bold=True)
        print(f"Found {count_text} fixup targets:")
        
        for target in fixup_targets:
            short_hash = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)
            files_count = Colors.colorize(str(len(target.files)), Colors.BRIGHT_BLUE)
            lines_count = Colors.colorize(str(len(target.changed_lines)), Colors.BRIGHT_YELLOW)
            message = target.commit_message[:60] + "..." if len(target.commit_message) > 60 else target.commit_message
            print(f"{short_hash} {message} ({files_count} files, {lines_count} lines)")