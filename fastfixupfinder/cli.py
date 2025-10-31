"""Command-line interface for Fast Fixup Finder."""

import sys
from pathlib import Path
import re

import click
from tabulate import tabulate

from .fixup_creator import FixupCreator, Colors
from .git_analyzer import FilterMode


def get_version() -> str:
    """Get version from package metadata or pyproject.toml."""
    # Try importlib.metadata first (standard Python way)
    try:
        from importlib.metadata import version
        return version("fastfixupfinder")
    except Exception:
        pass

    # Fallback to reading pyproject.toml for development installs
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "r") as f:
            content = f.read()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    except Exception:
        pass

    return "unknown"


@click.group()
@click.version_option(version=get_version())
def main():
    """Fast Fixup Finder - Automatically identify and create fixup commits."""
    pass


# Enable shell completion
if __name__ == '__main__':
    main()


@main.command()
@click.option('--repo', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.', help='Path to git repository (default: current directory)')
@click.option('--oneline', is_flag=True, help='Show compact one-line output per target')
@click.option('--detailed', is_flag=True, help='Show detailed analysis of changes and target commits')
@click.option('--fixups-only', is_flag=True, help='Only show high-confidence fixup targets')
@click.option('--include-all', is_flag=True, help='Include all changes regardless of fixup likelihood')
@click.option('--org-email', type=str, default='.*@intel.com', help='Regex pattern to match organization emails (default: .*@intel.com)')
@click.option('--limit', type=str, help='Limit search to commits after this SHA1 (commit hash)')
def status(repo, oneline, detailed, fixups_only, include_all, org_email, limit):
    """Show current fixup targets without making any changes."""
    try:
        # Determine filter mode from flags
        if fixups_only and include_all:
            click.echo(Colors.colorize("❌ Error: Cannot use both --fixups-only and --include-all", Colors.BRIGHT_RED), err=True)
            sys.exit(1)
        elif fixups_only:
            filter_mode = FilterMode.FIXUPS_ONLY
        elif include_all:
            filter_mode = FilterMode.INCLUDE_ALL
        else:
            filter_mode = FilterMode.SMART_DEFAULT
        
        creator = FixupCreator(repo, org_email_pattern=org_email)

        # Display filter settings
        if not oneline:
            filter_info = f"📧 Filtering by org email: {org_email}"
            if limit:
                filter_info += f" | 📍 Limit: {limit[:8]}..."
            click.echo(Colors.colorize(filter_info, Colors.DIM))

        # Create progress callback for non-oneline mode
        def progress_callback(message):
            if not oneline:
                click.echo(f"\r{Colors.colorize(message, Colors.CYAN)}" + " " * 10, nl=False)

        # Get all targets
        all_targets = creator.analyzer.find_fixup_targets(filter_mode, progress_callback if not oneline else None, limit_sha=limit)

        # Apply organization filtering
        targets = creator.analyzer.filter_targets_by_organization(all_targets, org_email)

        # Clear progress indicator
        if not oneline:
            click.echo("\r" + " " * 50 + "\r", nl=False)  # Clear the progress line

        if not targets:
            if oneline:
                click.echo(Colors.colorize("No fixup targets found.", Colors.YELLOW))
            else:
                click.echo(Colors.colorize("🔍 No fixup targets found.", Colors.YELLOW))
                click.echo(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
            return
        
        if detailed:
            # Detailed analysis (former analyze command)
            if oneline:
                # Simple header for oneline mode
                count_text = Colors.colorize(str(len(targets)), Colors.BRIGHT_GREEN, bold=True)
                click.echo(f"Found {count_text} fixup targets:")
            else:
                # Header with emoji and color
                count_text = Colors.colorize(str(len(targets)), Colors.BRIGHT_GREEN, bold=True)
                header = f"🔬 Detailed analysis of {count_text} fixup target{'s' if len(targets) != 1 else ''}:"
                click.echo(Colors.colorize(header, Colors.WHITE, bold=True))
                click.echo()
            
            if oneline:
                # Create table data for compact format
                table_data = []
                for target in targets:
                    short_hash = target.commit_hash[:8]
                    
                    # Truncate message for table display and clean up
                    # Remove newlines and extra whitespace
                    clean_message = ' '.join(target.commit_message.split())
                    max_message_len = 55
                    if len(clean_message) > max_message_len:
                        message = clean_message[:max_message_len-3] + "..."
                    else:
                        message = clean_message
                    
                    files_count = len(target.files)
                    lines_count = len(target.changed_lines)
                    
                    table_data.append([short_hash, message, files_count, lines_count])
                
                # Create table with colored headers
                headers = [
                    Colors.colorize("Hash", Colors.BRIGHT_CYAN, bold=True),
                    Colors.colorize("Commit Message", Colors.WHITE, bold=True),
                    Colors.colorize("Files", Colors.BRIGHT_BLUE, bold=True),
                    Colors.colorize("Lines", Colors.BRIGHT_YELLOW, bold=True)
                ]
                
                # Color the data
                colored_data = []
                for row in table_data:
                    colored_row = [
                        Colors.colorize(row[0], Colors.BRIGHT_CYAN, bold=True),  # hash
                        row[1],  # message (no color for readability)
                        Colors.colorize(str(row[2]), Colors.BRIGHT_BLUE),  # files
                        Colors.colorize(str(row[3]), Colors.BRIGHT_YELLOW)  # lines
                    ]
                    colored_data.append(colored_row)
                
                # Print table
                table_output = tabulate(colored_data, headers=headers, tablefmt="simple", stralign="left")
                click.echo(table_output)
            
            else:
                # Full detailed format
                for i, target in enumerate(targets, 1):
                    target_num = Colors.colorize(f"{i}.", Colors.BRIGHT_MAGENTA, bold=True)
                    commit_hash = Colors.colorize(target.commit_hash, Colors.BRIGHT_CYAN, bold=True)
                    click.echo(f"{target_num} 🎯 Target Commit: {commit_hash}")
                    
                    # Commit message
                    # Commit message with wrapping for long messages
                    message_header = Colors.colorize("   💬 Message: ", Colors.WHITE, bold=True)
                    if len(target.commit_message) > 80:
                        # Split long messages across multiple lines
                        first_line = target.commit_message[:77] + "..."
                        click.echo(f"{message_header}{first_line}")
                        if len(target.commit_message) > 150:
                            second_line = "" + target.commit_message[77:150] + "..."
                        else:
                            second_line = "" + target.commit_message[77:]
                        if second_line.strip():
                            click.echo(Colors.colorize(f"   {second_line}", Colors.WHITE))
                    else:
                        click.echo(f"{message_header}{target.commit_message}")
                    
                    # Author (truncate if too long)
                    author_text = target.author[:50] + "..." if len(target.author) > 50 else target.author
                    author = Colors.colorize(f"   👤 Author: {author_text}", Colors.DIM)
                    click.echo(author)
                    
                    # File count
                    file_count = Colors.colorize(str(len(target.files)), Colors.BRIGHT_YELLOW)
                    click.echo(f"   📁 Affected files: {file_count}")
                    
                    for file_path in sorted(target.files):
                        file_changes = [line for line in target.changed_lines if line.file_path == file_path]
                        change_count = Colors.colorize(str(len(file_changes)), Colors.BRIGHT_BLUE)
                        file_name = Colors.colorize(file_path, Colors.BLUE, bold=True)
                        click.echo(f"     📄 {file_name} ({change_count} changes)")
                        
                        for change in file_changes[:5]:  # Show first 5 changes per file
                            change_type = change.change_type
                            if change_type == 'added':
                                symbol = Colors.colorize("+ ", Colors.BRIGHT_GREEN, bold=True)
                            elif change_type == 'deleted':
                                symbol = Colors.colorize("- ", Colors.BRIGHT_RED, bold=True)
                            else:  # modified
                                symbol = Colors.colorize("~ ", Colors.BRIGHT_YELLOW, bold=True)
                            
                            line_num = Colors.colorize(f"Line {change.line_number}", Colors.CYAN)
                            content_preview = change.content[:50] + "..." if len(change.content) > 50 else change.content
                            content = Colors.colorize(content_preview, Colors.WHITE)
                            click.echo(f"       {symbol}{line_num}: {content}")
                        
                        if len(file_changes) > 5:
                            more_text = Colors.colorize(f"       ... and {len(file_changes) - 5} more changes", Colors.DIM)
                            click.echo(more_text)
                    
                    click.echo()
        else:
            # Brief status (original status command)
            if oneline:
                # Create table data for compact format
                table_data = []
                for target in targets:
                    short_hash = target.commit_hash[:8]
                    
                    # Truncate message for table display and clean up
                    # Remove newlines and extra whitespace
                    clean_message = ' '.join(target.commit_message.split())
                    max_message_len = 55
                    if len(clean_message) > max_message_len:
                        message = clean_message[:max_message_len-3] + "..."
                    else:
                        message = clean_message
                    
                    files_count = len(target.files)
                    lines_count = len(target.changed_lines)
                    
                    table_data.append([short_hash, message, files_count, lines_count])
                
                # Create table with colored headers
                headers = [
                    Colors.colorize("Hash", Colors.BRIGHT_CYAN, bold=True),
                    Colors.colorize("Commit Message", Colors.WHITE, bold=True),
                    Colors.colorize("Files", Colors.BRIGHT_BLUE, bold=True),
                    Colors.colorize("Lines", Colors.BRIGHT_YELLOW, bold=True)
                ]
                
                # Color the data
                colored_data = []
                for row in table_data:
                    colored_row = [
                        Colors.colorize(row[0], Colors.BRIGHT_CYAN, bold=True),  # hash
                        row[1],  # message (no color for readability)
                        Colors.colorize(str(row[2]), Colors.BRIGHT_BLUE),  # files
                        Colors.colorize(str(row[3]), Colors.BRIGHT_YELLOW)  # lines
                    ]
                    colored_data.append(colored_row)
                
                # Print table
                count_text = Colors.colorize(str(len(targets)), Colors.BRIGHT_GREEN, bold=True)
                click.echo(f"Found {count_text} fixup targets:")
                table_output = tabulate(colored_data, headers=headers, tablefmt="simple", stralign="left")
                click.echo(table_output)
            else:
                creator.status()
            
    except Exception as e:
        error_msg = Colors.colorize(f"❌ Error: {e}", Colors.BRIGHT_RED)
        click.echo(error_msg, err=True)
        sys.exit(1)


@main.command()
@click.option('--repo', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.', help='Path to git repository (default: current directory)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--interactive', '-i', is_flag=True, help='Interactively select targets with line-level control')
@click.option('--oneline', is_flag=True, help='Use compact output in interactive mode')
@click.option('--no-backup', is_flag=True, help='Skip automatic safety backup')
@click.option('--org-email', type=str, default='.*@intel.com', help='Regex pattern to match organization emails (default: .*@intel.com)')
@click.option('--limit', type=str, help='Limit creation to commits after this SHA1 (commit hash)')
def create(repo, dry_run, interactive, oneline, no_backup, org_email, limit):
    """Create fixup commits for identified targets."""
    try:
        creator = FixupCreator(repo, org_email_pattern=org_email)

        # Display filter settings
        filter_info = f"📧 Filtering by org email: {org_email}"
        if limit:
            filter_info += f" | 📍 Limit: {limit[:8]}..."
        click.echo(Colors.colorize(filter_info, Colors.DIM))

        if interactive:
            created_commits = creator.interactive_fixup_selection(compact_mode=oneline, dry_run=dry_run, limit_sha=limit)
        else:
            created_commits = creator.create_fixup_commits(dry_run, auto_backup=not no_backup, limit_sha=limit)
        
        if created_commits and not dry_run:
            count_text = Colors.colorize(str(len(created_commits)), Colors.BRIGHT_GREEN, bold=True)
            success_msg = f"✅ Created {count_text} fixup commit{'s' if len(created_commits) != 1 else ''}."
            click.echo(Colors.colorize(success_msg, Colors.WHITE, bold=True))
            creator.suggest_rebase_command(created_commits)
        elif dry_run:
            dry_run_msg = Colors.colorize("🔍 Dry run completed.", Colors.BRIGHT_CYAN, bold=True)
            if interactive:
                hint_msg = Colors.colorize("Remove --dry-run to create commits.", Colors.DIM)
            else:
                hint_msg = Colors.colorize("Use --interactive or remove --dry-run to create commits.", Colors.DIM)
            click.echo(f"{dry_run_msg} {hint_msg}")
        
    except Exception as e:
        error_msg = Colors.colorize(f"❌ Error: {e}", Colors.BRIGHT_RED)
        click.echo(error_msg, err=True)
        sys.exit(1)



@main.command()
@click.option('--repo', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.', help='Path to git repository (default: current directory)')
@click.option('--backup-name', type=str, help='Specific backup name to restore')
def restore(repo, backup_name):
    """Restore from a safety backup created by fastfixupfinder."""
    try:
        creator = FixupCreator(repo)
        success = creator.restore_from_backup(backup_name)
        
        if success:
            success_msg = Colors.colorize("✅ Backup restored successfully", Colors.BRIGHT_GREEN, bold=True)
            click.echo(success_msg)
        else:
            error_msg = Colors.colorize("❌ Failed to restore backup", Colors.BRIGHT_RED, bold=True)
            click.echo(error_msg)
            sys.exit(1)
            
    except Exception as e:
        error_msg = Colors.colorize(f"❌ Error: {e}", Colors.BRIGHT_RED)
        click.echo(error_msg, err=True)
        sys.exit(1)


@main.command()
@click.argument('commit_sha')
@click.option('--repo', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.', help='Path to git repository (default: current directory)')
def resquash(commit_sha, repo):
    """Convert a fixup! commit to squash! with message editing.

    This command allows you to convert an already created fixup! commit
    into a squash! commit with the ability to edit the commit message.

    Usage:
      fastfixupfinder resquash <commit-sha>

    The command will:
    1. Verify the commit is a fixup! commit
    2. Extract the original target commit message
    3. Open your editor to edit the message
    4. Convert fixup! to squash! with your edited message

    Note: You must be at the commit (HEAD) or in an interactive rebase.
    """
    try:
        creator = FixupCreator(repo)
        success = creator.resquash_commit(commit_sha)

        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(Colors.colorize(f"❌ Error: {e}", Colors.BRIGHT_RED), err=True)
        sys.exit(1)


@main.command()
def help_usage():
    """Show usage examples and workflow guidance."""
    help_text = """
Fast Fixup Finder Usage Examples:

1. Check what fixup targets are available:
   fastfixupfinder status

2. Show compact one-line format:
   fastfixupfinder status --oneline

3. See detailed analysis of potential targets:
   fastfixupfinder status --detailed

4. Preview what fixup commits would be created:
   fastfixupfinder create --dry-run

5. Interactively select and create fixup commits with line-level control:
   fastfixupfinder create --interactive

6. Use compact output in interactive mode (for many changes):
   fastfixupfinder create --interactive --oneline

7. Launch visual GUI for drag-and-drop assignment:
   fastfixupfinder gui

8. Automatically create all fixup commits:
   fastfixupfinder create

Typical Workflow:
1. Make changes to your files
2. Run 'fastfixupfinder status' to see potential targets
3. Run 'fastfixupfinder status --detailed' for in-depth analysis
4. Run 'fastfixupfinder create --interactive' for line-level fixup control
5. Use the suggested 'git rebase -i --autosquash' command to apply fixups

The tool works by:
- Analyzing your current changes (staged and unstaged)
- Using git blame to find which commits originally created the modified lines
- Grouping changes by their target commits
- Creating appropriately named fixup commits
- Suggesting the rebase command to apply them

Note: This tool works best when you have a clean commit history where
each commit represents a logical change.
"""
    click.echo(help_text)


if __name__ == '__main__':
    main()
