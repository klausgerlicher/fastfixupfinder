"""Command-line interface for Fast Fixup Finder."""

import sys
from pathlib import Path

import click

from .fixup_creator import FixupCreator, Colors
from .git_analyzer import FilterMode


@click.group()
@click.version_option()
def main():
    """Fast Fixup Finder - Automatically identify and create fixup commits."""
    pass


@main.command()
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
@click.option('--oneline', is_flag=True, help='Show compact one-line output per target')
@click.option('--detailed', is_flag=True, help='Show detailed analysis of changes and target commits')
@click.option('--fixups-only', is_flag=True, help='Only show high-confidence fixup targets')
@click.option('--include-all', is_flag=True, help='Include all changes regardless of fixup likelihood')
def status(repo, oneline, detailed, fixups_only, include_all):
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
        
        creator = FixupCreator(repo)
        targets = creator.analyzer.find_fixup_targets(filter_mode)
        
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
            
            for i, target in enumerate(targets, 1):
                if oneline:
                    # Compact one-line format with proper truncation
                    short_hash = Colors.colorize(target.commit_hash[:8], Colors.BRIGHT_CYAN, bold=True)
                    files_count = Colors.colorize(str(len(target.files)), Colors.BRIGHT_BLUE)
                    lines_count = Colors.colorize(str(len(target.changed_lines)), Colors.BRIGHT_YELLOW)
                    
                    # Calculate available space for message (assuming 80 char terminal)
                    # 8 (hash) + 1 (space) + X (message) + 1 (space) + ~15 (counts) = 80
                    max_message_len = 55
                    if len(target.commit_message) > max_message_len:
                        message = target.commit_message[:max_message_len-3] + "..."
                    else:
                        message = target.commit_message
                    
                    click.echo(f"{short_hash} {message} ({files_count} files, {lines_count} lines)")
                else:
                    # Full detailed format
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
                creator.status_oneline()
            else:
                creator.status()
            
    except Exception as e:
        error_msg = Colors.colorize(f"❌ Error: {e}", Colors.BRIGHT_RED)
        click.echo(error_msg, err=True)
        sys.exit(1)


@main.command()
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--interactive', '-i', is_flag=True, help='Interactively select targets with line-level control')
@click.option('--oneline', is_flag=True, help='Use compact output in interactive mode')
@click.option('--no-backup', is_flag=True, help='Skip automatic safety backup')
def create(repo, dry_run, interactive, oneline, no_backup):
    """Create fixup commits for identified targets."""
    try:
        creator = FixupCreator(repo)
        
        if interactive:
            created_commits = creator.interactive_fixup_selection(compact_mode=oneline)
        else:
            created_commits = creator.create_fixup_commits(dry_run, auto_backup=not no_backup)
        
        if created_commits and not dry_run:
            count_text = Colors.colorize(str(len(created_commits)), Colors.BRIGHT_GREEN, bold=True)
            success_msg = f"✅ Created {count_text} fixup commit{'s' if len(created_commits) != 1 else ''}."
            click.echo(Colors.colorize(success_msg, Colors.WHITE, bold=True))
            creator.suggest_rebase_command(created_commits)
        elif dry_run:
            dry_run_msg = Colors.colorize("🔍 Dry run completed.", Colors.BRIGHT_CYAN, bold=True)
            hint_msg = Colors.colorize("Use --interactive or remove --dry-run to create commits.", Colors.DIM)
            click.echo(f"{dry_run_msg} {hint_msg}")
        
    except Exception as e:
        error_msg = Colors.colorize(f"❌ Error: {e}", Colors.BRIGHT_RED)
        click.echo(error_msg, err=True)
        sys.exit(1)



@main.command()
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
@click.option('--backup-name', help='Specific backup name to restore')
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
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
def gui(repo):
    """Launch visual GUI for drag-and-drop fixup assignment."""
    try:
        from .gui import FixupGUI
        gui_app = FixupGUI(repo)
        gui_app.run()
    except ImportError:
        click.echo(Colors.colorize("❌ Error: GUI requires ncurses support", Colors.BRIGHT_RED), err=True)
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
    main()# final test for rebase command visibility
# Testing classification system
