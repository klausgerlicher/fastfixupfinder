# Fast Fixup Finder

A tool to automatically identify fixup targets and create fixup commits based on your current changes.

## What it does

When you edit files in a project, those changes often touch lines that were created in different commits. This tool:

1. **Analyzes** your current changes (staged and unstaged)
2. **Traces** each modified line back to its original commit using `git blame`
3. **Groups** changes by their target commits
4. **Creates** appropriately named fixup commits
5. **Suggests** the rebase command to apply them

## Prerequisites

Before installing Fast Fixup Finder, ensure you have:

### System Requirements
- **Python 3.10 or higher** - Check with `python3 --version`
- **Git** - Check with `git --version`
- **pip** - Modern version recommended, upgrade with `pip install --upgrade pip`

### Repository Requirements
- **Git repository** with existing commits and history
- **Uncommitted changes** in your working directory to analyze
- **Write access** to the repository for creating commits

### Quick Check
```bash
# Verify prerequisites
python3 --version  # Should show 3.10+
git --version      # Should show git version
pip --version      # Upgrade if old: pip install --upgrade pip
git status         # Should show you're in a git repository
```

## Quick Start

### Installation

#### Option 1: Using Virtual Environment (Recommended)

```bash
# Clone the repository
git clone https://github.com/kgerlich/fastfixupfinder.git
cd fastfixupfinder

# Initialize the testcase submodule (for demo)
git submodule update --init --recursive

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the tool
pip install .

# Or install in development mode
pip install -e .
```

#### Option 2: Global Installation

```bash
# Clone the repository
git clone https://github.com/kgerlich/fastfixupfinder.git
cd fastfixupfinder

# Install globally (requires appropriate permissions)
pip install .
```

#### Option 3: User Installation

```bash
# Install to user directory (no virtual env needed)
pip install --user .
```

**What this does:**
- Installs the package to your user Python directory (`~/.local/lib/python3.x/site-packages/`)
- Creates executable script at `~/.local/bin/fastfixupfinder`
- The script allows you to run `fastfixupfinder` from anywhere (if PATH is configured)

**Automatic PATH Configuration:**

Run the automatic setup script to configure your PATH:

```bash
# Linux/macOS
./setup_path.sh

# Windows (run in Command Prompt or PowerShell)
setup_path.bat

# Or run directly with Python (all platforms)
python3 setup_path.py
```

The setup script will:
- ✅ Detect your user binary installation path (`~/.local/bin`)
- ✅ Check if PATH is already configured  
- ✅ Add `~/.local/bin` to your shell's PATH (.bashrc, .zshrc, etc.)
- ✅ Fix executable permissions if needed (`chmod +x ~/.local/bin/fastfixupfinder`)
- ✅ Provide manual instructions as fallback
- ✅ Test the installation

**Manual PATH Configuration (if automatic setup fails):**

```bash
# Check where pip installed the binary
python3 -m site --user-base

# Add to PATH (Linux/macOS - add to ~/.bashrc, ~/.zshrc, or ~/.profile)
export PATH="$PATH:$(python3 -m site --user-base)/bin"

# Windows: Add to environment variables
# %APPDATA%\Python\Python3x\Scripts
```

**Verify installation:**
```bash
# After setup and restarting terminal
fastfixupfinder --version

# Check the installed script (should show executable file)
ls -la ~/.local/bin/fastfixupfinder

# If permission denied error, fix permissions:
./fix_permissions.sh

# If command not found, use module syntax as fallback
python3 -m fastfixupfinder.cli --help
```

**Understanding the installation:**
- The `fastfixupfinder` script is a Python entry point that calls `fastfixupfinder.cli:main`
- It's installed to `~/.local/bin/` which needs to be in your PATH
- The script is essentially equivalent to running `python3 -m fastfixupfinder.cli`

### Basic Usage

```bash
# Check what fixup targets are available
fastfixupfinder status

# See detailed analysis of your changes
fastfixupfinder status --detailed

# Show compact one-line output
fastfixupfinder status --oneline

# Preview what fixup commits would be created
fastfixupfinder create --dry-run

# Interactively select which fixups to create
fastfixupfinder create --interactive

# Create all fixup commits automatically
fastfixupfinder create
```

## Commands

| Command | Description |
|---------|-------------|
| `status` | Show potential fixup targets without making changes |
| `status --oneline` | Show compact one-line output per target |
| `status --detailed` | Show detailed analysis of changes and their target commits |
| `create` | Create fixup commits for identified targets |
| `create --dry-run` | Preview what would be created without making changes |
| `create --interactive` | Interactively select which targets to create fixups for |
| `create --no-backup` | Skip automatic safety backup (not recommended) |
| `restore` | Restore from automatic safety backup |
| `help-usage` | Show detailed usage examples and workflow guidance |

### Command Details

#### `status` Command Modes

**`fastfixupfinder status`** - Quick overview (default)
```bash
Found 2 potential fixup targets:

• a1b2c3d4: Add user authentication feature
  Author: John Doe <john@example.com>  
  Files: auth.py, models.py
  Changed lines: 5

• e5f6g7h8: Fix validation logic
  Author: Jane Smith <jane@example.com>
  Files: validators.py
  Changed lines: 2
```

**`fastfixupfinder status --detailed`** - Detailed breakdown
```bash
Detailed analysis of 2 fixup targets:

1. Target Commit: a1b2c3d4567890abcdef1234567890abcdef1234
   Message: Add user authentication feature
   Author: John Doe <john@example.com>
   Affected files: 2
     auth.py (3 changes)
       + Line 15: def authenticate_user(username, password):...
       ~ Line 23:     return validate_credentials(user)...
       - Line 31:     # TODO: Add logging...

     models.py (2 changes)
       + Line 45: class UserSession:...
       + Line 67:     def is_valid(self):...
```

**Compact Output (`--oneline` flag)**
```bash
Found 2 fixup targets:
a1b2c3d4 Add user authentication feature (2 files, 5 lines)
e5f6g7h8 Fix validation logic (1 files, 2 lines)
```

**When to use:**
- **`status`** - Quick check before creating fixups, get overview of targets
- **`status --oneline`** - Even more compact output for scripts or quick scans
- **`status --detailed`** - Detailed review of exact changes, verify detection accuracy

## 🛡️ Safety Features

Fast Fixup Finder includes built-in safety features:

- **Automatic backups** - Creates git stash before making changes
- **Dry-run mode** - Preview changes without modifying repository  
- **Interactive selection** - Choose exactly which fixups to create
- **Backup restoration** - Easy recovery from automatic backups

See [SAFETY.md](SAFETY.md) for comprehensive safety strategies and emergency recovery procedures.

## Typical Workflow

```mermaid
graph LR
    A[Make changes to files] --> B[fastfixupfinder status]
    B --> C{Review targets}
    C --> D[fastfixupfinder create -i]
    D --> E[git rebase -i --autosquash]
    E --> F[Clean commit history]
```

1. **Make changes** to your files across the project
2. **Run** `fastfixupfinder status` to see potential targets
3. **Review** which commits your changes would fix up
4. **Run** `fastfixupfinder create --interactive` to selectively create fixups
5. **Apply** fixups with the suggested `git rebase -i --autosquash` command

## Example Session

```bash
$ fastfixupfinder status
Found 2 potential fixup targets:

• a1b2c3d4: Add user authentication feature
  Author: John Doe <john@example.com>
  Files: auth.py, models.py
  Changed lines: 5

• e5f6g7h8: Fix validation logic
  Author: Jane Smith <jane@example.com>
  Files: validators.py
  Changed lines: 2

$ fastfixupfinder create --interactive
Found 2 potential fixup targets:

1. a1b2c3d4: Add user authentication feature
   Author: John Doe <john@example.com>
   Files: auth.py, models.py
   Changed lines: 5

2. e5f6g7h8: Fix validation logic
   Author: Jane Smith <jane@example.com>
   Files: validators.py
   Changed lines: 2

Select targets (comma-separated numbers, 'all', or 'none'): 1,2

Created fixup commit 12345678 for a1b2c3d4
Created fixup commit 87654321 for e5f6g7h8

To apply the fixup commits, run:
git rebase -i --autosquash HEAD~5
```

## Testing

The repository includes a complete test case in the `testcase/` directory. See [TESTCASE.md](TESTCASE.md) for details.

### Interactive Demo

```bash
# Run the interactive demonstration (recommended)
./run_demo.sh

# Or run the basic demo in the testcase directory
cd testcase
./demo.sh
```

The interactive demo provides a guided walkthrough with:
- 🎯 Step-by-step explanations
- 🔍 Repository exploration
- 🧪 Live tool demonstration  
- 💾 Optional fixup commit creation
- 🎨 Colorized output for better readability


## How it works

The tool uses git's built-in `blame` and `diff` functionality to:

1. **Parse** your working directory changes (both staged and unstaged)
2. **Trace** each modified line to its original commit using `git blame`
3. **Group** related changes by their target commits
4. **Create** fixup commits with the standard `fixup!` prefix
5. **Suggest** the appropriate rebase command for applying changes

## Use Cases

This tool is particularly useful when:

- 🔄 **Working on multiple features** simultaneously
- 🐛 **Finding small bugs** or improvements while working on something else
- 📝 **Improving documentation** or comments in existing code
- 🧹 **Maintaining clean commit history** without manual rebasing
- 👥 **Collaborating** with teams that value atomic commits

## Options

### Global Options
- `--repo PATH` - Specify repository path (default: current directory)

### Status Command Options
- `--oneline` - Show compact one-line output per target
- `--detailed` - Show detailed analysis of changes and target commits

### Create Command Options
- `--dry-run` - Show what would be done without making changes
- `--interactive, -i` - Interactively select targets

## Troubleshooting

### Common Issues

1. **"No fixup targets found"** - Ensure you have uncommitted changes and the files have git history

2. **"fastfixupfinder: command not found"** - PATH configuration needed:
   ```bash
   # Find user installation path
   python3 -m site --user-base
   
   # Add to your shell profile (~/.bashrc, ~/.zshrc, ~/.profile)
   export PATH="$PATH:$(python3 -m site --user-base)/bin"
   
   # Reload shell or restart terminal
   source ~/.bashrc  # or ~/.zshrc
   
   # Alternative: use module syntax
   python3 -m fastfixupfinder.cli status
   ```

3. **"Permission denied"** - Executable permissions issue:
   ```bash
   # Fix executable permissions (common with pip --user installs)
   chmod +x ~/.local/bin/fastfixupfinder
   
   # Or run the setup script which fixes this automatically
   python3 setup_path.py
   
   # Test after fixing
   fastfixupfinder --version
   ```

4. **Module not found** - Installation or environment issue:
   ```bash
   # Check if installed
   pip list | grep fastfixupfinder
   
   # Reinstall if needed
   pip install --user .
   
   # Or use development mode
   PYTHONPATH=. python3 -m fastfixupfinder.cli
   ```

5. **Package installs as "UNKNOWN"** - Older pip version issue:
   ```bash
   # Upgrade pip to latest version
   pip install --upgrade pip
   
   # Clean and reinstall
   pip uninstall UNKNOWN -y
   rm -rf *.egg-info build dist
   pip install --user .
   ```

6. **Permission errors** - Ensure you have write access to the git repository

7. **Virtual environment issues** - Make sure your virtual environment is activated:
   ```bash
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

### Debug Mode

For troubleshooting, you can run commands with increased verbosity by examining the tool's output in detail with the `analyze` command.