"""Tab completion support for Fast Fixup Finder."""

import os
import click
from click.shell_completion import CompletionItem


def complete_repo_paths(ctx, param, incomplete):
    """Complete repository paths - directories containing .git folder."""
    if incomplete.startswith('/'):
        # Absolute path
        base_dir = '/'
        search_term = incomplete[1:]
    elif incomplete.startswith('~/'):
        # Home directory path
        base_dir = os.path.expanduser('~')
        search_term = incomplete[2:]
    elif '/' in incomplete:
        # Relative path with directory
        base_dir = os.path.dirname(incomplete)
        search_term = os.path.basename(incomplete)
    else:
        # Current directory
        base_dir = '.'
        search_term = incomplete

    try:
        items = []
        for item in os.listdir(base_dir):
            if item.startswith('.') and not search_term.startswith('.'):
                continue
            
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                # Check if it's a git repository or contains potential git repos
                is_git_repo = os.path.exists(os.path.join(item_path, '.git'))
                
                if item.startswith(search_term):
                    if is_git_repo:
                        items.append(CompletionItem(
                            item + '/',
                            help="Git repository"
                        ))
                    else:
                        items.append(CompletionItem(
                            item + '/',
                            help="Directory"
                        ))
        
        return items
    except (OSError, PermissionError):
        return []


def complete_filter_modes(ctx, param, incomplete):
    """Complete filter mode values."""
    modes = ['smart', 'fixups-only', 'include-all']
    return [
        CompletionItem(mode) 
        for mode in modes 
        if mode.startswith(incomplete.lower())
    ]


def complete_backup_names(ctx, param, incomplete):
    """Complete backup names from git stash list."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'stash', 'list', '--format=%gd:%s'],
            capture_output=True,
            text=True,
            cwd='.'
        )
        
        if result.returncode == 0:
            items = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    stash_ref, message = line.split(':', 1)
                    if 'fastfixupfinder-backup' in message:
                        if stash_ref.startswith(incomplete):
                            items.append(CompletionItem(
                                stash_ref,
                                help=message.strip()
                            ))
            return items
    except:
        pass
    return []


def install_completion():
    """Generate and display shell completion installation commands."""
    shell = os.environ.get('SHELL', '').split('/')[-1]
    
    completion_commands = {
        'bash': {
            'command': 'eval "$(_FASTFIXUPFINDER_COMPLETE=bash_source fastfixupfinder)"',
            'file': '~/.bashrc',
            'note': 'Add to ~/.bashrc and restart terminal'
        },
        'zsh': {
            'command': 'eval "$(_FASTFIXUPFINDER_COMPLETE=zsh_source fastfixupfinder)"',
            'file': '~/.zshrc', 
            'note': 'Add to ~/.zshrc and restart terminal'
        },
        'fish': {
            'command': '_FASTFIXUPFINDER_COMPLETE=fish_source fastfixupfinder | source',
            'file': '~/.config/fish/completions/fastfixupfinder.fish',
            'note': 'Save the output to the fish completions directory'
        }
    }
    
    print("🚀 Fast Fixup Finder Tab Completion Setup")
    print("=" * 50)
    print()
    
    # Check if fastfixupfinder command is available
    import shutil
    if not shutil.which('fastfixupfinder'):
        print("⚠️  WARNING: 'fastfixupfinder' command not found in PATH")
        print("   Tab completion requires the package to be properly installed.")
        print("   Please run: pip install -e . (or pip install .)")
        print("   Then restart this command.")
        print()
        return
    
    if shell in completion_commands:
        cmd_info = completion_commands[shell]
        print(f"📋 Detected shell: {shell}")
        print()
        print("🔧 Installation command:")
        print(f"   {cmd_info['command']}")
        print()
        print(f"📁 Add to: {cmd_info['file']}")
        print(f"💡 Note: {cmd_info['note']}")
        print()
        
        if shell == 'fish':
            print("🐟 For Fish shell, run:")
            print(f"   mkdir -p ~/.config/fish/completions")
            print(f"   {cmd_info['command']} > ~/.config/fish/completions/fastfixupfinder.fish")
            print()
    else:
        print("🤔 Shell not detected or unsupported")
        print("Supported shells: bash, zsh, fish")
        print()
        print("🔧 Try one of these commands:")
        for shell_name, cmd_info in completion_commands.items():
            print(f"   {shell_name}: {cmd_info['command']}")
        print()
    
    print("✨ Available completions:")
    print("   • Command names (status, create, gui, restore)")
    print("   • Repository paths (directories with .git)")
    print("   • Flag options (--oneline, --dry-run, --interactive)")
    print("   • Filter modes (smart, fixups-only, include-all)")
    print("   • Backup names (from git stash)")
    print()
    print("🔄 After setup, restart your terminal or source your shell config")
    print("📝 Test with: fastfixupfinder <TAB>")


# Custom parameter types with completion
class RepoPath(click.Path):
    """Path parameter with git repository completion."""
    
    def shell_complete(self, ctx, param, incomplete):
        return complete_repo_paths(ctx, param, incomplete)


class FilterMode(click.Choice):
    """Filter mode choice with completion."""
    
    def __init__(self):
        super().__init__(['smart', 'fixups-only', 'include-all'])
    
    def shell_complete(self, ctx, param, incomplete):
        return complete_filter_modes(ctx, param, incomplete)


class BackupName(click.ParamType):
    """Backup name parameter with git stash completion."""
    name = "backup_name"
    
    def shell_complete(self, ctx, param, incomplete):
        return complete_backup_names(ctx, param, incomplete)