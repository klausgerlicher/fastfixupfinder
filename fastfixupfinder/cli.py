"""Command-line interface for Fast Fixup Finder."""

import sys
from pathlib import Path

import click

from .fixup_creator import FixupCreator, Colors


@click.group()
@click.version_option()
def main():
    """Fast Fixup Finder - Automatically identify and create fixup commits."""
    pass


@main.command()
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
def status(repo):
    """Show current fixup targets without making any changes."""
    try:
        creator = FixupCreator(repo)
        creator.status()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--interactive', '-i', is_flag=True, help='Interactively select targets')
@click.option('--no-backup', is_flag=True, help='Skip automatic safety backup')
def create(repo, dry_run, interactive, no_backup):
    """Create fixup commits for identified targets."""
    try:
        creator = FixupCreator(repo)
        
        if interactive:
            created_commits = creator.interactive_fixup_selection()
        else:
            created_commits = creator.create_fixup_commits(dry_run, auto_backup=not no_backup)
        
        if created_commits and not dry_run:
            click.echo(f"Created {len(created_commits)} fixup commits.")
            creator.suggest_rebase_command(created_commits)
        elif dry_run:
            click.echo("Dry run completed. Use --interactive or remove --dry-run to create commits.")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--repo', default='.', help='Path to git repository (default: current directory)')
def analyze(repo):
    """Analyze the repository and show detailed fixup target information."""
    try:
        creator = FixupCreator(repo)
        targets = creator.analyzer.find_fixup_targets()
        
        if not targets:
            click.echo(Colors.colorize("🔬 No fixup targets found for detailed analysis.", Colors.YELLOW))
            click.echo(Colors.colorize("   Working directory is clean or no blame information available.", Colors.DIM))
            return
        
        # Header with emoji and color
        count_text = Colors.colorize(str(len(targets)), Colors.BRIGHT_GREEN, bold=True)
        header = f"🔬 Detailed analysis of {count_text} fixup target{'s' if len(targets) != 1 else ''}:"
        click.echo(Colors.colorize(header, Colors.WHITE, bold=True))
        click.echo()
        
        for i, target in enumerate(targets, 1):
            # Target number and commit hash
            target_num = Colors.colorize(f"{i}.", Colors.BRIGHT_MAGENTA, bold=True)
            commit_hash = Colors.colorize(target.commit_hash, Colors.BRIGHT_CYAN, bold=True)
            click.echo(f"{target_num} 🎯 Target Commit: {commit_hash}")
            
            # Commit message
            message = Colors.colorize(f"   💬 Message: {target.commit_message}", Colors.WHITE, bold=True)
            click.echo(message)
            
            # Author
            author = Colors.colorize(f"   👤 Author: {target.author}", Colors.DIM)
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
            click.echo("✓ Backup restored successfully")
        else:
            click.echo("✗ Failed to restore backup")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
def help_usage():
    """Show usage examples and workflow guidance."""
    help_text = """
Fast Fixup Finder Usage Examples:

1. Check what fixup targets are available:
   fastfixupfinder status

2. See detailed analysis of potential targets:
   fastfixupfinder analyze

3. Preview what fixup commits would be created:
   fastfixupfinder create --dry-run

4. Interactively select and create fixup commits:
   fastfixupfinder create --interactive

5. Automatically create all fixup commits:
   fastfixupfinder create

Typical Workflow:
1. Make changes to your files
2. Run 'fastfixupfinder status' to see potential targets
3. Run 'fastfixupfinder create --interactive' to selectively create fixups
4. Use the suggested 'git rebase -i --autosquash' command to apply fixups

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