"""Automated fixup commit creation functionality."""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional

import git
from tabulate import tabulate

from .git_analyzer import FixupTarget, GitAnalyzer, ChangeClassification

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
    
    def __init__(self, repo_path: str = ".", org_email_pattern: Optional[str] = None):
        """Initialize with repository path and optional organization email pattern.
        
        Args:
            repo_path: Path to the git repository
            org_email_pattern: Regex pattern to match organization emails. Only commits by authors 
                              matching this pattern will be considered for fixups.
        """
        self.repo = git.Repo(repo_path)
        self.repo_path = Path(repo_path)
        self.analyzer = GitAnalyzer(repo_path)
        self.org_email_pattern = org_email_pattern
    
    def create_fixup_commits(self, dry_run: bool = False, auto_backup: bool = True, limit_sha: Optional[str] = None) -> List[str]:
        """Create fixup commits for all identified targets.

        This method creates only fixup commits. To convert fixups to squash with
        message editing, use the resquash command after creation:
            fastfixupfinder resquash <commit-sha>

        Args:
            dry_run: If True, show what would be done without making changes
            auto_backup: If True, create automatic git stash backup
            limit_sha: Optional SHA1 to limit creation to commits after this point
        """
        # Get all fixup targets first
        all_fixup_targets = self.analyzer.find_fixup_targets(limit_sha=limit_sha)  # Uses SMART_DEFAULT
        created_commits = []
        git_commands = []  # Track git commands for display

        # Apply organization filtering if specified
        if self.org_email_pattern:
            fixup_targets = self.analyzer.filter_targets_by_organization(all_fixup_targets, self.org_email_pattern)
            if not fixup_targets:
                if all_fixup_targets:
                    print(Colors.colorize(f"🔍 Found {len(all_fixup_targets)} fixup targets, but none match organization email pattern '{self.org_email_pattern}'.", Colors.YELLOW))
                else:
                    print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                    print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
                return created_commits
        else:
            fixup_targets = all_fixup_targets
            if not fixup_targets:
                print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
                return created_commits

        # Show targets in table format (like status command)
        self._show_diff_table(fixup_targets, context_lines=4)

        if not dry_run:
            # Store target commits for later rebase suggestion
            self._target_commits = [target.commit_hash for target in fixup_targets]

            # Create automatic backup of HEAD (not working directory) before making changes
            if auto_backup:
                self._create_head_backup()

            print()
            print(Colors.colorize("🚀 Creating fixup commits...", Colors.WHITE, bold=True))
            print()

            for target in fixup_targets:
                commit_hash, commands = self.create_fixup_commit(target, dry_run, commit_type="fixup", custom_message=None)
                if commit_hash:
                    created_commits.append(commit_hash)
                git_commands.extend(commands)

        # For dry-run, collect commands from all targets
        if dry_run:
            for target in fixup_targets:
                _, commands = self.create_fixup_commit(target, dry_run, commit_type="fixup", custom_message=None)
                git_commands.extend(commands)

        # Show git commands table at the end
        if git_commands:
            self._show_git_commands_table(git_commands, dry_run)

        # Suggest resquash workflow
        if created_commits and not dry_run:
            print()
            print(Colors.colorize("💡 Tip: To convert any fixup to squash with message editing:", Colors.CYAN))
            print(Colors.colorize("   fastfixupfinder resquash <commit-sha>", Colors.WHITE, bold=True))

        return created_commits
    
    def create_fixup_commit(
        self,
        target: FixupTarget,
        dry_run: bool = False,
        commit_type: str = "fixup",
        custom_message: Optional[str] = None
    ) -> tuple[Optional[str], list[str]]:
        """Create a single fixup or squash commit for the given target.

        Args:
            target: The fixup target
            dry_run: If True, only show what would be done
            commit_type: 'fixup' or 'squash'
            custom_message: Custom message for squash commits (without 'squash!' prefix)

        Returns:
            tuple: (commit_hash, git_commands_list)
        """
        commands = []
        try:
            # Prepare for fixup commit creation
            short_hash = target.commit_hash[:8]
            
            if dry_run:
                # Capture commands that would be executed with line-level precision
                for file_path in target.files:
                    # Get target lines for this file
                    target_lines = [cl.line_number for cl in target.changed_lines if cl.file_path == file_path]
                    if target_lines:
                        line_info = f"lines {sorted(target_lines)}"
                        commands.append(f"git add --patch {file_path}  # auto-select {line_info}")

                # Add commit command based on type
                if commit_type == "squash":
                    message_to_use = custom_message or target.commit_message
                    commands.append(f'git commit --squash {target.commit_hash} -m "{message_to_use}" --no-verify')
                else:
                    commands.append(f'git commit --fixup {target.commit_hash} --no-verify')
                return None, commands
            
            # Stage only the specific lines related to this target using --patch
            staged_files = []
            for file_path in target.files:
                if (self.repo_path / file_path).exists():
                    success = self._stage_lines_for_target(target, file_path, commands)
                    if success:
                        staged_files.append(file_path)
            
            if not staged_files:
                target_hash = Colors.colorize(short_hash, Colors.BRIGHT_CYAN, bold=True)
                print(Colors.colorize(f"⚠️  No files to stage for target {target_hash}", Colors.YELLOW))
                return None, commands
            
            # Create the fixup or squash commit
            if commit_type == "squash":
                message_to_use = custom_message or target.commit_message
                commands.append(f'git commit --squash {target.commit_hash} -m "{message_to_use}" --no-verify')
                # Git automatically adds 'squash!' prefix
                self.repo.git.commit(
                    f'--squash={target.commit_hash}',
                    '-m', message_to_use,
                    '--no-verify'
                )
                commit_type_display = "squash"
            else:
                commands.append(f'git commit --fixup {target.commit_hash} --no-verify')
                self.repo.git.commit(f'--fixup={target.commit_hash}', '--no-verify')
                commit_type_display = "fixup"

            # Get the hash of the newly created commit
            commit_hash = self.repo.head.commit.hexsha
            new_hash = Colors.colorize(commit_hash[:8], Colors.BRIGHT_GREEN, bold=True)
            target_hash = Colors.colorize(short_hash, Colors.BRIGHT_CYAN, bold=True)
            print(f"✅ Created {commit_type_display} commit {new_hash} for {target_hash}")

            return commit_hash, commands
            
        except Exception as e:
            target_hash = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)
            error_msg = Colors.colorize(f"❌ Error creating fixup commit for {target_hash}: {e}", Colors.BRIGHT_RED)
            print(error_msg)
            return None, commands
    
    def interactive_fixup_selection(self, compact_mode: bool = False, dry_run: bool = False, limit_sha: Optional[str] = None) -> List[str]:
        """Interactively select which fixup commits to create with streamlined workflow.

        Simplified workflow:
        1. Select targets from list (with 'info' command for details)
        2. Show auto-assigned lines (what will be committed)
        3. Create all fixup commits

        Note: To convert fixup to squash with message editing, use the resquash command:
          fastfixupfinder resquash <commit-sha>

        Args:
            compact_mode: If True, use compact output display
            dry_run: If True, show what would be done without making changes
            limit_sha: Optional SHA1 to limit to commits after this point
        """
        # Get all fixup targets first
        all_fixup_targets = self.analyzer.find_fixup_targets(limit_sha=limit_sha)  # Uses SMART_DEFAULT
        created_commits = []

        # Apply organization filtering if specified
        if self.org_email_pattern:
            fixup_targets = self.analyzer.filter_targets_by_organization(all_fixup_targets, self.org_email_pattern)
            if not fixup_targets:
                if all_fixup_targets:
                    print(Colors.colorize(f"🔍 Found {len(all_fixup_targets)} fixup targets, but none match organization email pattern '{self.org_email_pattern}'.", Colors.YELLOW))
                else:
                    print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                    print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
                return created_commits
        else:
            fixup_targets = all_fixup_targets
            if not fixup_targets:
                print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
                return created_commits

        count_text = Colors.colorize(str(len(fixup_targets)), Colors.BRIGHT_GREEN, bold=True)
        print()
        print(Colors.colorize("🧠 Interactive Mode", Colors.WHITE, bold=True))
        print(f"Found {count_text} potential fixup target{'s' if len(fixup_targets) != 1 else ''}")

        # Step 1: Select targets with iterative display
        selected_targets = self._iterative_target_selection(fixup_targets)
        if not selected_targets:
            return created_commits

        # Step 2: Show auto-assigned lines (what will be committed)
        print()
        print(Colors.colorize("━" * 80, Colors.CYAN))
        print(Colors.colorize("🔍 Line Assignment Summary", Colors.WHITE, bold=True))
        print(Colors.colorize("All lines auto-assigned based on git blame analysis", Colors.DIM))
        print()
        for i, target in enumerate(selected_targets, 1):
            file_summary = {}
            for cl in target.changed_lines:
                file_summary[cl.file_path] = file_summary.get(cl.file_path, 0) + 1

            print(f"  {Colors.colorize(f'{i}.', Colors.BRIGHT_MAGENTA, bold=True)} {Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)}")
            for file_path, count in sorted(file_summary.items()):
                print(f"     📁 {Colors.colorize(file_path, Colors.BRIGHT_BLUE)}: {count} lines")

        # Step 3: Create all fixup commits
        print()
        print(Colors.colorize("━" * 80, Colors.CYAN))
        print(Colors.colorize("🚀 Creating fixup commits...", Colors.WHITE, bold=True))
        print()

        # Store target commits for later rebase suggestion
        self._target_commits = [target.commit_hash for target in selected_targets]

        for i, target in enumerate(selected_targets, 1):
            commit_hash, _ = self.create_fixup_commit(target, dry_run, commit_type="fixup", custom_message=None)
            if commit_hash:
                created_commits.append(commit_hash)

        # Summary
        print()
        print(Colors.colorize("━" * 80, Colors.CYAN))
        summary = f"✅ Created {len(created_commits)} fixup commit(s)"
        print(Colors.colorize(summary, Colors.BRIGHT_GREEN, bold=True))

        # Suggest resquash workflow
        if created_commits:
            print()
            print(Colors.colorize("💡 Tip: To convert any fixup to squash with message editing:", Colors.CYAN))
            print(Colors.colorize("   fastfixupfinder resquash <commit-sha>", Colors.WHITE, bold=True))

        return created_commits
    
    def _interactive_line_classification_DEPRECATED(self, target: FixupTarget, compact_mode: bool = False) -> Optional[FixupTarget]:
        """Interactive classification control for individual lines within a target.
        
        Args:
            target: The fixup target to review
            compact_mode: Use compact output for better readability
        """
        if compact_mode:
            header = f"🔍 {target.commit_hash[:8]}: {target.commit_message[:40]}..."
            print(Colors.colorize(header, Colors.WHITE, bold=True))
        else:
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
            if compact_mode:
                file_header = Colors.colorize(f"📄 {file_path}", Colors.BLUE, bold=True)
                print(file_header)
            else:
                file_header = Colors.colorize(f"📄 {file_path}", Colors.BLUE, bold=True)
                print(file_header)
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
    
    def _create_head_backup(self) -> None:
        """Create automatic backup tag pointing to current HEAD before making changes."""
        try:
            # Create a tag with timestamp pointing to current HEAD
            timestamp = subprocess.run(
                ["date", "+%Y%m%d_%H%M%S"],
                capture_output=True,
                text=True
            ).stdout.strip()

            tag_name = f"fastfixupfinder_backup_{timestamp}"

            # Create tag pointing to current HEAD
            self.repo.git.tag(tag_name)
            print(f"🛡️  Safety backup created: {tag_name}")
            print(f"   To restore if needed: git reset --hard {tag_name}")

        except Exception as e:
            print(f"⚠️  Warning: Could not create safety backup: {e}")
            print("   Consider creating manual backup before proceeding")

    def _create_safety_backup(self) -> None:
        """Legacy method - redirects to head backup."""
        self._create_head_backup()
    
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
    
    def status(self, show_diff: bool = False, context_lines: int = 4) -> None:
        """Show current status of potential fixup targets.
        
        Args:
            show_diff: Whether to show diff context for each target
            context_lines: Number of context lines to show around changes in diff
        """
        # Get all fixup targets first
        all_fixup_targets = self.analyzer.find_fixup_targets()  # Uses SMART_DEFAULT
        
        # Apply organization filtering if specified
        if self.org_email_pattern:
            fixup_targets = self.analyzer.filter_targets_by_organization(all_fixup_targets, self.org_email_pattern)
            if not fixup_targets:
                if all_fixup_targets:
                    print(Colors.colorize(f"🔍 Found {len(all_fixup_targets)} fixup targets, but none match organization email pattern '{self.org_email_pattern}'.", Colors.YELLOW))
                else:
                    print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                    print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
                return
        else:
            fixup_targets = all_fixup_targets
            if not fixup_targets:
                print(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                print(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
                return
        
        if show_diff:
            # Show diff table format
            self._show_diff_table(fixup_targets, context_lines)
        else:
            # Show regular format
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
    
    def _show_diff_table(self, fixup_targets: List[FixupTarget], context_lines: int = 4) -> None:
        """Show fixup targets in a table format with diff context."""
        if not fixup_targets:
            return
        
        # Get terminal width for diff column truncation
        terminal_width = shutil.get_terminal_size().columns
        
        # First pass: collect all data to analyze content lengths
        table_data = []
        max_subject_len = 0
        
        for i, target in enumerate(fixup_targets, 1):
            # Get commit subject (first line only) - don't truncate yet
            subject = target.commit_message.split('\n')[0]
            max_subject_len = max(max_subject_len, len(subject))
            
            # Generate compact diff for this target (with generous width for now)
            diff_content = self._get_compact_diff(target, 200, context_lines)
            
            table_data.append([
                str(i),
                target.commit_hash[:8],
                subject,
                diff_content
            ])
        
        # Calculate dynamic column widths based on content and terminal width
        index_width = max(3, len(str(len(fixup_targets))))  # Width needed for index numbers
        sha_width = 8  # SHA is always 8 chars
        borders_padding = 12  # Approximate space for table borders and padding
        
        # Reserve space for fixed columns and borders
        fixed_space = index_width + sha_width + borders_padding
        available_space = max(100, terminal_width - fixed_space)
        
        # Dynamically split between subject and diff based on content
        # Give subject minimum 20 chars, maximum 50 chars or 30% of available space
        min_subject = 20
        max_subject = min(50, int(available_space * 0.3))
        optimal_subject = min(max_subject, max(min_subject, max_subject_len + 5))
        
        subject_width = optimal_subject
        diff_width = available_space - subject_width
        
        # Second pass: apply truncation with calculated widths
        for i, row in enumerate(table_data):
            if len(row[2]) > subject_width:
                table_data[i][2] = row[2][:subject_width-3] + "..."
            
            # Regenerate diff with proper width
            target = fixup_targets[i]
            table_data[i][3] = self._get_compact_diff(target, diff_width, context_lines)
        
        # Create colored headers
        headers = [
            Colors.colorize("Index", Colors.BRIGHT_MAGENTA, bold=True),
            Colors.colorize("SHA", Colors.BRIGHT_CYAN, bold=True),
            Colors.colorize("Subject", Colors.WHITE, bold=True),
            Colors.colorize("Diff", Colors.BRIGHT_YELLOW, bold=True)
        ]
        
        # Print header
        count_text = Colors.colorize(str(len(fixup_targets)), Colors.BRIGHT_GREEN, bold=True)
        print(f"🎯 Found {count_text} potential fixup target{'s' if len(fixup_targets) != 1 else ''}:")
        print()
        
        # Print table with dynamic column width limits based on content
        max_col_widths = [index_width, sha_width, subject_width, diff_width]
        
        # Multi-line diff content is now properly handled by tabulate with disable_numparse=True
        
        # Enable proper multi-line cell handling - remove maxcolwidths to preserve newlines
        table_output = tabulate(table_data, headers=headers, tablefmt="fancy_grid", stralign="left", 
                               disable_numparse=True)
        print(table_output)
    
    def _get_compact_diff(self, target: FixupTarget, max_width: int, context_lines: int = 4) -> str:
        """Generate a compact diff representation for table display with context lines."""
        diff_lines = []
        
        
        # Use the changed lines that are already part of this target
        target_changes = target.changed_lines
        
        if not target_changes:
            return "No changes"
        
        # Group changes by file
        by_file = {}
        for change in target_changes:
            if change.file_path not in by_file:
                by_file[change.file_path] = []
            by_file[change.file_path].append(change)
        
        # Generate compact diff representation with context
        seen_lines = set()  # Track already seen diff lines to avoid duplicates
        
        for file_path, changes in sorted(by_file.items()):
            file_name = Path(file_path).name
            
            # Read current file content for context
            try:
                full_path = self.repo_path / file_path
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    file_lines = f.readlines()
            except (FileNotFoundError, UnicodeDecodeError) as e:
                # Fallback to simple format if file can't be read
                unique_changes = []
                for change in changes:
                    change_key = (change.file_path, change.line_number, change.change_type, change.content.strip())
                    if change_key not in seen_lines:
                        seen_lines.add(change_key)
                        unique_changes.append(change)
                
                for change in unique_changes[:2]:  # Limit to 2 when no context
                    symbol = "+" if change.change_type == "added" else "-" if change.change_type == "deleted" else "~"
                    symbol = Colors.colorize(symbol, Colors.BRIGHT_GREEN if change.change_type == "added" else Colors.BRIGHT_RED if change.change_type == "deleted" else Colors.BRIGHT_YELLOW, bold=True)
                    line_ref = Colors.colorize(f"{file_name}:{change.line_number}", Colors.CYAN)
                    content = change.content.strip()
                    available_for_content = max_width - len(f"{file_name}:{change.line_number} ") - 5
                    if len(content) > available_for_content:
                        content = content[:available_for_content-3] + "..."
                    diff_lines.append(f"{symbol} {line_ref} {content}")
                continue
            
            # Deduplicate changes
            unique_changes = []
            for change in changes:
                change_key = (change.file_path, change.line_number, change.change_type, change.content.strip())
                if change_key not in seen_lines:
                    seen_lines.add(change_key)
                    unique_changes.append(change)
            
            # Show filename header once and build context diff for all changes
            if unique_changes:
                # Build compact diff block
                diff_block = []
                
                # Add filename header as first line of diff block  
                file_header = Colors.colorize(file_name, Colors.BRIGHT_BLUE, bold=True)
                diff_block.append(file_header)
                
                # Get all line numbers that have changes
                changed_line_numbers = {change.line_number for change in unique_changes}
                
                # Calculate the range to show all changes with context
                all_line_nums = [change.line_number for change in unique_changes]
                min_line = min(all_line_nums)
                max_line = max(all_line_nums)
                
                # Expand context around the range
                start_line = max(0, min_line - 1 - context_lines)
                end_line = min(len(file_lines), max_line - 1 + context_lines + 1)
                
                # Build context lines with all changes highlighted
                for i in range(start_line, end_line):
                    current_line = file_lines[i].rstrip()
                    line_number = i + 1
                    
                    # Determine if this is a changed line and what type
                    symbol = " "  # Default context line
                    if line_number in changed_line_numbers:
                        # Find the change type for this line
                        for change in unique_changes:
                            if change.line_number == line_number:
                                if change.change_type == "added":
                                    symbol = Colors.colorize("+", Colors.BRIGHT_GREEN, bold=True)
                                elif change.change_type == "deleted":
                                    symbol = Colors.colorize("-", Colors.BRIGHT_RED, bold=True)
                                else:  # modified
                                    symbol = Colors.colorize("~", Colors.BRIGHT_YELLOW, bold=True)
                                break
                    
                    line_ref = Colors.colorize(f"{line_number:>3}", Colors.CYAN)
                    
                    # Truncate content to fit in available space
                    available_for_content = max_width - 8  # 3 for line number + 5 for symbols/padding
                    if len(current_line) > available_for_content:
                        content = current_line[:available_for_content-3] + "..."
                    else:
                        content = current_line
                    
                    diff_block.append(f"{symbol} {line_ref} │ {content}")
                
                # Add this file's diff block to main diff lines
                diff_lines.extend(diff_block)
        
        # Join all diff lines - show full context without truncation
        result = "\n".join(diff_lines)
        
        # Result contains proper newlines for multi-line table cell display
        
        return result
    
    def get_changed_lines(self) -> List['ChangedLine']:
        """Get current changed lines from analyzer."""
        return self.analyzer.get_changed_lines()
    
    def status_oneline(self) -> None:
        """Show current status of potential fixup targets in compact one-line format."""
        # Get all fixup targets first
        all_fixup_targets = self.analyzer.find_fixup_targets()  # Uses SMART_DEFAULT
        
        # Apply organization filtering if specified
        if self.org_email_pattern:
            fixup_targets = self.analyzer.filter_targets_by_organization(all_fixup_targets, self.org_email_pattern)
            if not fixup_targets:
                if all_fixup_targets:
                    print(Colors.colorize(f"Found {len(all_fixup_targets)} fixup targets, but none match organization email pattern '{self.org_email_pattern}'.", Colors.YELLOW))
                else:
                    print(Colors.colorize("No fixup targets found.", Colors.YELLOW))
                return
        else:
            fixup_targets = all_fixup_targets
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

    def _show_git_commands_table(self, git_commands: List[str], dry_run: bool = False) -> None:
        """Show git commands in a table format."""
        if not git_commands:
            return
        
        print()  # Add spacing before the table
        
        # Prepare table data
        table_data = []
        for i, command in enumerate(git_commands, 1):
            table_data.append([str(i), command])
        
        # Create colored headers
        headers = [
            Colors.colorize("Step", Colors.BRIGHT_MAGENTA, bold=True),
            Colors.colorize("Git Command", Colors.BRIGHT_GREEN, bold=True)
        ]
        
        # Print header
        if dry_run:
            title = Colors.colorize("🔍 Git commands that would be executed:", Colors.BRIGHT_CYAN, bold=True)
        else:
            title = Colors.colorize("✅ Git commands executed:", Colors.BRIGHT_GREEN, bold=True)
        
        print(title)
        print()
        
        # Print table with git commands
        table_output = tabulate(table_data, headers=headers, tablefmt="fancy_grid", stralign="left", 
                               disable_numparse=True)
        print(table_output)
        
        # Add note about line-level staging
        note = Colors.colorize("ℹ️  Using automated git add --patch for precise line-level staging", Colors.CYAN)
        print()
        print(note)
    
    def _stage_lines_for_target(self, target: FixupTarget, file_path: str, commands: list) -> bool:
        """Stage only the specific lines that belong to this fixup target using git add --patch.
        
        Args:
            target: The fixup target containing the lines to stage
            file_path: Path to the file to stage from
            commands: List to append git commands to
            
        Returns:
            bool: True if staging was successful, False otherwise
        """
        import subprocess
        import tempfile
        
        # Get the line numbers that belong to this target
        target_lines = set()
        for changed_line in target.changed_lines:
            if changed_line.file_path == file_path:
                target_lines.add(changed_line.line_number)
        
        if not target_lines:
            return False
        
        try:
            # First, get the current diff for this file to understand the hunks
            diff_result = subprocess.run(
                ['git', 'diff', '--no-color', file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not diff_result.stdout.strip():
                return False  # No changes to stage
            
            # Parse the diff to understand which hunks contain our target lines
            hunks_to_accept = self._parse_diff_for_target_lines(diff_result.stdout, target_lines)
            
            if not hunks_to_accept:
                return False
            
            # Create automated responses for git add --patch
            # 'y' = yes to stage this hunk, 'n' = no to skip this hunk
            responses = []
            for i, accept_hunk in enumerate(hunks_to_accept):
                if accept_hunk:
                    responses.append('y')
                else:
                    responses.append('n')
            
            # Add final 'q' to quit the interactive session
            responses.append('q')
            response_input = '\n'.join(responses) + '\n'
            
            # Run git add --patch with automated responses
            patch_result = subprocess.run(
                ['git', 'add', '--patch', file_path],
                cwd=self.repo_path,
                input=response_input,
                text=True,
                capture_output=True
            )
            
            if patch_result.returncode == 0:
                # Record the command that was executed
                hunk_info = f"hunks {[i+1 for i, accept in enumerate(hunks_to_accept) if accept]}"
                commands.append(f"git add --patch {file_path}  # accepted {hunk_info}")
                return True
            else:
                return False
                
        except subprocess.CalledProcessError as e:
            print(Colors.colorize(f"⚠️  Error staging {file_path}: {e}", Colors.YELLOW))
            return False
    
    def _parse_diff_for_target_lines(self, diff_output: str, target_lines: set) -> list:
        """Parse git diff output to determine which hunks contain target lines.
        
        Args:
            diff_output: Output from git diff
            target_lines: Set of line numbers that belong to the target
            
        Returns:
            list: Boolean list indicating which hunks to accept
        """
        lines = diff_output.split('\n')
        hunks_to_accept = []
        current_hunk_has_target = False
        in_hunk = False
        
        for line in lines:
            # Start of new hunk
            if line.startswith('@@'):
                # If we were in a previous hunk, record the decision
                if in_hunk:
                    hunks_to_accept.append(current_hunk_has_target)
                
                # Parse hunk header to get line numbers
                # Format: @@ -old_start,old_count +new_start,new_count @@
                parts = line.split()
                if len(parts) >= 3:
                    new_range = parts[2]  # +new_start,new_count
                    if ',' in new_range:
                        new_start = int(new_range.split(',')[0][1:])  # Remove '+'
                    else:
                        new_start = int(new_range[1:])  # Remove '+'
                    
                    # Check if any target lines fall in this hunk range
                    # This is a simplified check - we'll refine based on actual diff content
                    current_hunk_has_target = any(
                        abs(line_num - new_start) < 10  # rough proximity check
                        for line_num in target_lines
                    )
                else:
                    current_hunk_has_target = False
                
                in_hunk = True
            
            # More precise check: if we see a specific line change that matches our targets
            elif line.startswith(('+', '-', ' ')) and in_hunk:
                # This is a rough implementation - in practice, we'd need more sophisticated
                # line tracking to match exact line numbers from our analysis
                pass
        
        # Don't forget the last hunk
        if in_hunk:
            hunks_to_accept.append(current_hunk_has_target)

        return hunks_to_accept

    def _ask_commit_type(self) -> str:
        """Ask user whether to create fixup or squash commit.

        Returns:
            'fixup' or 'squash'
        """
        while True:
            response = input("🔧 Commit type [f]ixup or [s]quash?: ").strip().lower()
            if response == 'f' or response == 'fixup':
                return 'fixup'
            elif response == 's' or response == 'squash':
                return 'squash'
            else:
                print(Colors.colorize("Invalid choice. Please enter 'f' or 's'", Colors.YELLOW))

    def _edit_commit_message_in_editor(self, prefill_message: str) -> str:
        """Open editor for user to edit commit message.

        Args:
            prefill_message: Initial message to prefill

        Returns:
            Edited message (without 'squash!' prefix)
        """
        import tempfile
        import os

        try:
            # Create temporary file with prefilled message
            with tempfile.NamedTemporaryFile(
                mode='w+',
                suffix='.txt',
                delete=False,
                encoding='utf-8'
            ) as f:
                temp_path = f.name
                f.write(prefill_message)
                f.flush()

            # Get editor from environment
            editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'nano'))

            # Open editor
            result = subprocess.run([editor, temp_path])

            if result.returncode != 0:
                print(Colors.colorize("Editor exited with error, using original message", Colors.YELLOW))
                os.unlink(temp_path)
                return prefill_message

            # Read edited content
            with open(temp_path, 'r', encoding='utf-8') as f:
                edited_message = f.read().strip()

            # Cleanup
            os.unlink(temp_path)

            # Validate not empty
            if not edited_message:
                print(Colors.colorize("Empty message, using original", Colors.YELLOW))
                return prefill_message

            return edited_message

        except Exception as e:
            print(Colors.colorize(f"Error opening editor: {e}", Colors.YELLOW))
            print(Colors.colorize("Falling back to inline editing...", Colors.DIM))

            # Fallback to inline
            print(f"\n📝 Edit message (or press Enter to keep original):")
            print(f"   Original: {prefill_message}")
            edited = input("> ").strip()
            return edited if edited else prefill_message

    def _display_targets_compact(
        self,
        targets: List[FixupTarget],
        selected_indices: Optional[set] = None
    ):
        """Display targets in a compact numbered list format.

        Args:
            targets: List of fixup targets
            selected_indices: Set of selected indices (1-based)
        """
        for i, target in enumerate(targets, 1):
            # Checkbox
            if selected_indices is not None:
                if i in selected_indices:
                    checkbox = Colors.colorize("[✓]", Colors.BRIGHT_GREEN, bold=True)
                else:
                    checkbox = Colors.colorize("[ ]", Colors.DIM)
            else:
                checkbox = "   "

            # Number
            number = Colors.colorize(f"{i}.", Colors.BRIGHT_MAGENTA, bold=True)

            # SHA
            sha = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)

            # Truncate message to fit nicely
            clean_message = ' '.join(target.commit_message.split())
            max_msg_len = 50
            message = clean_message[:max_msg_len] + "..." if len(clean_message) > max_msg_len else clean_message

            # File and line count
            num_files = len(target.files)
            num_lines = len(target.changed_lines)
            file_str = "file" if num_files == 1 else "files"
            line_str = "line" if num_lines == 1 else "lines"
            summary = Colors.colorize(f"({num_files} {file_str}, {num_lines} {line_str})", Colors.BRIGHT_BLUE)

            # Print the line
            print(f"  {checkbox} {number} {sha}  {message} {summary}")

    def _show_target_info(self, target: FixupTarget, index: int):
        """Show detailed information about a target."""
        print()
        print(Colors.colorize("━" * 80, Colors.CYAN))
        print(Colors.colorize(f"Target {index}: {target.commit_hash}", Colors.WHITE, bold=True))
        print(Colors.colorize("━" * 80, Colors.CYAN))
        print(f"\n{Colors.colorize('Commit Message:', Colors.WHITE, bold=True)}")
        print(f"  {target.commit_message}")
        print(f"\n{Colors.colorize('Author:', Colors.WHITE, bold=True)}")
        print(f"  {target.author}")
        print(f"\n{Colors.colorize('Files Changed:', Colors.WHITE, bold=True)}")
        for file_path in sorted(target.files):
            file_lines = [cl for cl in target.changed_lines if cl.file_path == file_path]
            print(f"  📁 {Colors.colorize(file_path, Colors.BRIGHT_BLUE)} ({len(file_lines)} lines)")
            for cl in file_lines[:5]:  # Show first 5 lines
                change_symbol = {"added": "+", "modified": "~", "deleted": "-"}.get(cl.change_type, "?")
                symbol_color = {"added": Colors.GREEN, "modified": Colors.YELLOW, "deleted": Colors.RED}.get(cl.change_type, Colors.WHITE)
                print(f"     {Colors.colorize(change_symbol, symbol_color)} L{cl.line_number}: {cl.content[:60]}...")
            if len(file_lines) > 5:
                print(f"     ... and {len(file_lines) - 5} more lines")
        print(Colors.colorize("━" * 80, Colors.CYAN))
        print()

    def _parse_selection(self, response: str, max_index: int) -> set:
        """Parse user selection input into set of indices.

        Supports: numbers (1), ranges (1-3), comma-separated (1,3,5)

        Args:
            response: User input string
            max_index: Maximum valid index

        Returns:
            Set of selected indices (1-based)
        """
        selected = set()
        parts = response.replace(' ', '').split(',')

        for part in parts:
            if '-' in part:
                # Range: 1-3
                try:
                    start, end = part.split('-')
                    start_idx = int(start)
                    end_idx = int(end)
                    if 1 <= start_idx <= max_index and 1 <= end_idx <= max_index:
                        selected.update(range(start_idx, end_idx + 1))
                    else:
                        print(Colors.colorize(f"⚠️  Invalid range: {part}", Colors.YELLOW))
                except ValueError:
                    print(Colors.colorize(f"⚠️  Invalid range format: {part}", Colors.YELLOW))
            else:
                # Single number
                try:
                    idx = int(part)
                    if 1 <= idx <= max_index:
                        selected.add(idx)
                    else:
                        print(Colors.colorize(f"⚠️  Invalid index: {idx}", Colors.YELLOW))
                except ValueError:
                    print(Colors.colorize(f"⚠️  Invalid number: {part}", Colors.YELLOW))

        return selected

    def _iterative_target_selection(self, targets: List[FixupTarget]) -> List[FixupTarget]:
        """Interactive selection of targets with persistent display.

        Args:
            targets: List of available fixup targets

        Returns:
            List of selected targets
        """
        selected = set()

        while True:
            # Display header with selection count
            print()
            print(Colors.colorize("━" * 80, Colors.CYAN))
            if selected:
                header = f"🎯 Target Selection ({len(selected)} of {len(targets)} selected)"
            else:
                header = "🎯 Target Selection"
            print(Colors.colorize(header, Colors.WHITE, bold=True))
            print(Colors.colorize("━" * 80, Colors.CYAN))
            print()

            # Display targets in compact format
            self._display_targets_compact(targets, selected_indices=selected)

            # Commands help
            print()
            print(Colors.colorize("Commands: 1,3,5 | 1-3 (range) | all | info N | done", Colors.DIM))

            # Prompt
            response = input(Colors.colorize("→ ", Colors.BRIGHT_CYAN)).strip()

            if not response:
                continue

            if response.lower() == 'done':
                if selected:
                    break
                else:
                    print(Colors.colorize("⚠️  No targets selected. Please select at least one target.", Colors.YELLOW))
                    continue

            if response.lower() == 'all':
                selected = set(range(1, len(targets) + 1))
                print(Colors.colorize(f"✅ Selected all {len(targets)} targets", Colors.GREEN))
                continue

            # Check for info command
            if response.lower().startswith('info '):
                try:
                    idx = int(response.split()[1])
                    if 1 <= idx <= len(targets):
                        self._show_target_info(targets[idx - 1], idx)
                        # Wait for user to press enter before showing list again
                        input(Colors.colorize("\n[Press Enter to continue]", Colors.DIM))
                    else:
                        print(Colors.colorize(f"⚠️  Invalid index: {idx}", Colors.YELLOW))
                except (ValueError, IndexError):
                    print(Colors.colorize("⚠️  Usage: info <number>", Colors.YELLOW))
                continue

            # Parse and update selections
            new_selected = self._parse_selection(response, len(targets))
            if new_selected:
                selected.update(new_selected)
                print(Colors.colorize(f"✅ Added {len(new_selected)} target(s), total: {len(selected)}", Colors.GREEN))

        return [targets[i - 1] for i in sorted(selected)]

    def resquash_commit(self, commit_sha: str) -> bool:
        """Convert a fixup! commit to a squash! commit with message editing.

        Args:
            commit_sha: SHA of the fixup commit to convert

        Returns:
            True if successful, False otherwise
        """
        import os

        try:
            # Get the commit object
            try:
                commit = self.repo.commit(commit_sha)
            except Exception as e:
                print(Colors.colorize(f"❌ Error: Could not find commit {commit_sha[:8]}", Colors.BRIGHT_RED))
                print(Colors.colorize(f"   {e}", Colors.DIM))
                return False

            commit_message = commit.message.strip()

            # Check if it's a fixup commit
            if not commit_message.startswith('fixup! '):
                print(Colors.colorize(f"❌ Error: Commit {commit_sha[:8]} is not a fixup! commit", Colors.BRIGHT_RED))
                print(Colors.colorize(f"   Message: {commit_message[:60]}...", Colors.DIM))
                return False

            # Extract the fixup target message (remove 'fixup! ' prefix)
            fixup_target_subject = commit_message[7:]  # Remove 'fixup! '

            # Find the actual target commit by searching for a commit with matching subject
            target_commit = None
            target_commit_message = None

            # Search through ancestor commits to find the target
            for ancestor in self.repo.iter_commits(f'{commit.hexsha}~1', max_count=100):
                ancestor_subject = ancestor.message.split('\n')[0].strip()
                if ancestor_subject == fixup_target_subject:
                    target_commit = ancestor
                    target_commit_message = ancestor.message.strip()
                    break

            if not target_commit:
                # Fallback: use the fixup target subject as the message
                print(Colors.colorize(f"⚠️  Warning: Could not find target commit for 'fixup! {fixup_target_subject[:40]}...'", Colors.YELLOW))
                print(Colors.colorize(f"   Using fixup target subject as message", Colors.DIM))
                target_commit_message = fixup_target_subject

            print()
            print(Colors.colorize("━" * 80, Colors.CYAN))
            print(Colors.colorize(f"🔄 Converting fixup to squash: {commit_sha[:8]}", Colors.WHITE, bold=True))
            print(Colors.colorize("━" * 80, Colors.CYAN))
            print(f"\nFixup commit: fixup! {fixup_target_subject[:60]}{'...' if len(fixup_target_subject) > 60 else ''}")
            if target_commit:
                print(f"Target commit: {Colors.colorize(target_commit.hexsha[:8], Colors.BRIGHT_CYAN, bold=True)}")
            print()

            # Edit the message - prefill with the ACTUAL target commit's full message
            print(Colors.colorize("✏️  Opening editor to edit commit message...", Colors.CYAN))
            print(Colors.colorize("   The target commit's full message is prefilled for editing", Colors.DIM))
            edited_message = self._edit_commit_message_in_editor(target_commit_message)

            if not edited_message:
                print(Colors.colorize("❌ Empty message, aborting", Colors.YELLOW))
                return False

            print()
            print(Colors.colorize(f"✅ New message: {edited_message[:60]}{'...' if len(edited_message) > 60 else ''}", Colors.GREEN))
            print()

            # Confirm before making changes
            confirm = input(Colors.colorize("Convert fixup to squash? [Y/n]: ", Colors.BRIGHT_YELLOW)).strip().lower()
            if confirm and confirm not in ['y', 'yes']:
                print(Colors.colorize("❌ Aborted", Colors.YELLOW))
                return False

            print()
            print(Colors.colorize("🔄 Rewriting commit...", Colors.CYAN))

            # Create the squash! message format that git rebase understands
            squash_message = f"squash! {edited_message}"

            # Use git filter-repo or commit --amend in a detached HEAD state
            # Save current state
            original_branch = None
            original_head = self.repo.head.commit.hexsha

            try:
                # Check if we're on a branch
                try:
                    original_branch = self.repo.active_branch.name
                except:
                    # Already in detached HEAD state
                    pass

                # Find parent of the commit
                parent_commit = commit.parents[0] if commit.parents else None
                if not parent_commit:
                    print(Colors.colorize("❌ Cannot rewrite root commit", Colors.BRIGHT_RED))
                    return False

                # Checkout the parent commit
                self.repo.git.checkout(parent_commit.hexsha)

                # Cherry-pick the fixup commit with the new message
                try:
                    self.repo.git.cherry_pick('-n', commit.hexsha)  # -n means --no-commit
                    self.repo.git.commit('-m', squash_message, '--no-verify', '--author', f'{commit.author.name} <{commit.author.email}>')
                    new_commit = self.repo.head.commit

                    # Now replay all commits that came after the fixup commit
                    commits_to_replay = []
                    for c in self.repo.iter_commits(f'{commit.hexsha}..{original_head}'):
                        commits_to_replay.insert(0, c)

                    for c in commits_to_replay:
                        try:
                            self.repo.git.cherry_pick(c.hexsha)
                        except Exception as e:
                            print(Colors.colorize(f"❌ Conflict replaying commit {c.hexsha[:8]}: {e}", Colors.BRIGHT_RED))
                            print(Colors.colorize("Please resolve conflicts and run: git cherry-pick --continue", Colors.YELLOW))
                            print(Colors.colorize("Then manually update your branch", Colors.YELLOW))
                            return False

                    new_head = self.repo.head.commit.hexsha

                    # Update the original branch to point to the new HEAD
                    if original_branch:
                        self.repo.git.checkout(original_branch)
                        self.repo.git.reset('--hard', new_head)

                    new_hash_display = Colors.colorize(new_commit.hexsha[:8], Colors.BRIGHT_GREEN, bold=True)
                    print()
                    print(Colors.colorize("━" * 80, Colors.CYAN))
                    print(f"✅ Successfully converted to squash commit: {new_hash_display}")
                    print(Colors.colorize("━" * 80, Colors.CYAN))
                    print()
                    print(Colors.colorize("The commit message has been rewritten to:", Colors.WHITE, bold=True))
                    print(f"  {squash_message}")
                    print()
                    print(Colors.colorize("Next steps:", Colors.WHITE, bold=True))
                    print("  Use git rebase -i --autosquash to apply the squash")
                    print()

                    return True

                except Exception as e:
                    print(Colors.colorize(f"❌ Error cherry-picking: {e}", Colors.BRIGHT_RED))
                    # Abort cherry-pick if needed
                    try:
                        self.repo.git.cherry_pick('--abort')
                    except:
                        pass
                    raise

            except Exception as e:
                print(Colors.colorize(f"❌ Error rewriting commit: {e}", Colors.BRIGHT_RED))
                # Restore original state
                try:
                    if original_branch:
                        self.repo.git.checkout(original_branch)
                    else:
                        self.repo.git.checkout(original_head)
                    print(Colors.colorize("Repository restored to original state", Colors.YELLOW))
                except:
                    print(Colors.colorize("⚠️  Warning: Could not restore original state", Colors.BRIGHT_RED))
                return False

        except Exception as e:
            print(Colors.colorize(f"❌ Error during resquash: {e}", Colors.BRIGHT_RED))
            import traceback
            traceback.print_exc()
            return False