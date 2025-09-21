"""Command-line interface for Fast Fixup Finder."""

import sys
from pathlib import Path

import click

from .fixup_creator import FixupCreator


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
def create(repo, dry_run, interactive):
    """Create fixup commits for identified targets."""
    try:
        creator = FixupCreator(repo)
        
        if interactive:
            created_commits = creator.interactive_fixup_selection()
        else:
            created_commits = creator.create_fixup_commits(dry_run)
        
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
            click.echo("No fixup targets found.")
            return
        
        click.echo(f"Detailed analysis of {len(targets)} fixup targets:")
        click.echo()
        
        for i, target in enumerate(targets, 1):
            click.echo(f"{i}. Target Commit: {target.commit_hash}")
            click.echo(f"   Message: {target.commit_message}")
            click.echo(f"   Author: {target.author}")
            click.echo(f"   Affected files: {len(target.files)}")
            
            for file_path in sorted(target.files):
                file_changes = [line for line in target.changed_lines if line.file_path == file_path]
                click.echo(f"     {file_path} ({len(file_changes)} changes)")
                
                for change in file_changes[:5]:  # Show first 5 changes per file
                    change_symbol = {
                        'added': '+',
                        'deleted': '-',
                        'modified': '~'
                    }.get(change.change_type, '?')
                    click.echo(f"       {change_symbol} Line {change.line_number}: {change.content[:50]}...")
                
                if len(file_changes) > 5:
                    click.echo(f"       ... and {len(file_changes) - 5} more changes")
            
            click.echo()
            
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