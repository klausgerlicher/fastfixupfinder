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

# Smart filtering (default) - excludes obvious new features
fastfixupfinder status

# Only show high-confidence fixup targets
fastfixupfinder status --fixups-only

# Include all changes (no filtering)
fastfixupfinder status --include-all

# Preview what fixup commits would be created
fastfixupfinder create --dry-run

# Interactively select which fixups to create with line-level control
fastfixupfinder create --interactive

# Use compact output in interactive mode (for many changes)
fastfixupfinder create --interactive --oneline

# Launch visual GUI for drag-and-drop assignment
fastfixupfinder gui

# Install shell tab completion
fastfixupfinder install-completion

# Create all fixup commits automatically
fastfixupfinder create
```

## Commands

| Command | Description | Best For |
|---------|-------------|----------|
| `status` | Show potential fixup targets (smart filtering) | Quick overview, daily workflow |
| `status --oneline` | Show compact one-line output per target | Scripts, CI/CD, quick scans |
| `status --detailed` | Show detailed analysis with line-by-line breakdown | Code review, verification |
| `status --fixups-only` | Only show high-confidence fixup targets | Focused workflow, avoiding noise |
| `status --include-all` | Include all changes regardless of likelihood | Manual review, debugging |
| `create` | Create fixup commits automatically | Simple cases, trusted automation |
| `create --dry-run` | Preview what would be created | Safety, verification before commit |
| `create --interactive` | Line-level control with detailed output | Precise control, complex assignments |
| `create --interactive --oneline` | Compact interactive mode | Many changes, reduced clutter |
| `gui` | **Visual drag-and-drop interface** | **Complex workflows, visual users** |
| `install-completion` | Install shell tab completion | Enhanced productivity, frequent users |
| `create --no-backup` | Skip automatic safety backup | Advanced users, CI environments |
| `restore` | Restore from automatic safety backup | Error recovery, undo operations |
| `help-usage` | Show detailed usage examples | Learning, reference |

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

## 🧠 Intelligent Filtering

Fast Fixup Finder uses smart heuristics to distinguish between actual fixups and new feature development:

### **Smart Classification**
- **Likely Fixups**: Typos, comments, small fixes, string changes
- **Possible Fixups**: Could be either fixups or small features  
- **Unlikely Fixups**: Large changes, new functions, complex logic
- **New Files**: Completely new files (filtered by default)

### **Filtering Modes**
- **Smart Default** (default): Excludes obvious new features, includes likely fixups
- **Fixups Only** (`--fixups-only`): Strict mode, only high-confidence fixups
- **Include All** (`--include-all`): No filtering, show everything for manual review

### **Example Classifications**
```bash
# These would be classified as LIKELY_FIXUP:
"fix typo in comment"
"update error message"  
'logging' → 'logger'

# These would be classified as UNLIKELY_FIXUP:
def new_function():
import pandas as pd
class NewFeature:

# These would be filtered out by default:
new_module.py (NEW_FILE)
Large architectural changes
```

## 🧠 Enhanced Interactive Mode

The interactive mode (`--interactive`) now provides line-level classification control:

### **Line-Level Selection**
- **Visual Classification**: Each line shows its automatic classification with color coding
  - 🟢 **LIKELY_FIXUP** (green) - Typos, comments, small fixes
  - 🟡 **POSSIBLE_FIXUP** (yellow) - Could be fixups or small features
  - 🔴 **UNLIKELY_FIXUP** (red) - Large changes, new functions
  - 🟣 **NEW_FILE** (magenta) - Completely new files

### **Flexible Selection Syntax**
- **Individual lines**: `1,3,5` - Select specific line numbers
- **Ranges**: `1-5` - Select line ranges
- **Keywords**:
  - `auto` - Use automatic classification (includes likely + possible fixups)
  - `all` - Include all lines in the file
  - `none` - Skip this file entirely

### **File-by-File Organization**
- Changes grouped by file for better review
- Color-coded change types: `+` (added), `-` (deleted), `~` (modified)
- Content preview with line numbers
- Final selection summary with totals

### **Example Sessions**

**🎨 Visual GUI Mode (Recommended for Complex Cases):**
```bash
$ fastfixupfinder gui

# Visual interface opens with:
# • Left panel: All changes grouped by file with color-coded classifications
# • Right panel: Fixup targets with assignment counts
# • TAB to switch panels, ↑↓ to navigate, ENTER to assign
# • Real-time visual feedback and assignment tracking
# • Press 'c' to create fixup commits when ready
```

**📝 Interactive CLI Mode (Full Control):**
```bash
$ fastfixupfinder create --interactive

🧠 Enhanced interactive mode with line-level classification control
Found 2 potential fixup targets:

1. a1b2c3d4: Add user authentication feature
   👤 Author: John Doe <john@example.com>
   📁 Files: auth.py, models.py
   📝 Changed lines: 5

🎯 Select targets (comma-separated numbers, 'all', or 'none'): 1

🔍 Reviewing lines for target a1b2c3d4: Add user authentication feature...

📄 auth.py

  1. + Line 15: def authenticate_user(username, password):
     Classification: Unlikely Fixup
  2. ~ Line 23: return validate_credentials(user)  # Fix typo
     Classification: Likely Fixup
  3. + Line 31: # TODO: Add proper error handling
     Classification: Likely Fixup

🎯 Select lines from auth.py (numbers, 'all', 'none', or 'auto'): 2,3
  ✅ Selected 2 lines

✅ Final selection: 2 lines across 1 files
```

## 🎨 Visual GUI Mode

For the ultimate user experience, Fast Fixup Finder includes a visual ncurses-based GUI:

```bash
# Launch the visual interface
$ fastfixupfinder gui
```

### **GUI Features**
- **🖱️ Drag-and-drop assignment** - Move changes from left panel to fixup targets on right
- **🎨 Color-coded classifications** - Visual indicators for LIKELY/POSSIBLE/UNLIKELY fixups
- **📋 Real-time assignment tracking** - See assignments as you make them
- **🔍 Live preview panel** - Shows selected assignments and commands that will be executed
- **⌨️ Keyboard navigation** - Full keyboard control with intuitive hotkeys
- **📊 Assignment statistics** - Live counts of assigned/unassigned changes

### **GUI Layout**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fast Fixup Finder - Visual Assignment Mode                    [q]uit [h]elp │
├──────────────────────────────┬──────────────────────────────────────────────┤
│ CHANGES (Unassigned)         │ FIXUP TARGETS                                │
│ ┌─ File: auth.py ──────────┐ │ ┌─ Target: a1b2c3d4 ─────────────────────┐   │
│ │ ○ + L15: def authenticate │ │ │ Add user authentication feature         │   │
│ │   [UNLIKELY] 🔴           │ │ │ Author: John Doe                        │   │
│ │ ● ~ L23: fix typo         │ │ │ 📋 Assigned: auth.py:23, utils.py:45   │   │
│ │   [LIKELY] 🟢             │ │ └─────────────────────────────────────────┘   │
│ └──────────────────────────┘ │                                              │
├──────────────────────────────┴──────────────────────────────────────────────┤
│ PREVIEW - Selected Assignments & Commands                                   │
│ 📋 2 changes assigned to 1 targets:                                         │
│   • a1b2c3d4: Add user authentication... (2 changes)                       │
│ 🚀 Commands that will be executed:                                          │
│   1. git add .                                                               │
│   2. git commit -m 'fixup! <target_message>' (×1)                          │
│   3. git rebase -i --autosquash <base_commit>                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Status: 3 unassigned, 2 assigned, 1 targets  [c]reate [r]eset [s]ave [q]uit │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **Keyboard Shortcuts**
- `TAB` - Switch between changes and targets panels
- `↑↓` - Navigate within panels
- `ENTER` - Assign selected change to selected target
- `SPACE` - Quick-assign to suggested target
- `DEL` - Remove assignment
- `c` - Create fixup commits from assignments
- `r` - Reset all assignments
- `q` - Quit GUI

The GUI provides an intuitive visual workflow that makes managing complex fixup assignments effortless!

## ⚡ Tab Completion

Fast Fixup Finder includes intelligent shell tab completion for enhanced productivity:

### **Installation**
```bash
# Install tab completion for your shell
fastfixupfinder install-completion

# The command will detect your shell and provide setup instructions
```

### **Completion Features**
- **🔤 Command completion** - Tab complete all commands (`status`, `create`, `gui`, etc.)
- **📁 Repository paths** - Smart completion for `--repo` option (shows Git repositories)
- **🚩 Flag completion** - Complete all option flags (`--oneline`, `--dry-run`, etc.)
- **🔄 Backup names** - Complete backup names from git stash for restore command
- **📂 Context-aware** - Only shows relevant completions based on current command

### **Supported Shells**
- **Bash** - Most common Linux/macOS shell
- **Zsh** - Enhanced shell with better completion
- **Fish** - Modern shell with built-in completion support

### **Example Usage**
```bash
# Type and press TAB for completion
fastfixupfinder <TAB>          # Shows: create, gui, status, restore, etc.
fastfixupfinder status --<TAB>  # Shows: --oneline, --detailed, --fixups-only
fastfixupfinder --repo <TAB>    # Shows: ../other-repo/, ./current-repo/
fastfixupfinder restore --<TAB> # Shows: stash@{0}, stash@{1}, etc.
```

After installation, restart your terminal and enjoy faster, error-free command typing!

**📝 Interactive CLI Mode (Compact):**
```bash
$ fastfixupfinder create --interactive --oneline

🧠 Enhanced interactive mode with line-level classification control
Found 1 potential fixup target:

1. a1b2c3d4: Add user authentication feature

🎯 Select targets: 1

🔍 Reviewing lines for target a1b2c3d4...

📄 auth.py
  5 lines: 2 likely 1 possible 2 unlikely
  1. + L15: def authenticate_user(username,... [Unlikely]
  2. ~ L23: return validate_credentials(user)... [Likely]
  3. + L31: # TODO: Add proper error handling [Likely]
  ... and 2 more lines

🎯 Select from auth.py (#s, 'all', 'none', 'auto'): auto
  ✅ Auto-selected 2 lines based on classification

✅ Final selection: 2 lines across 1 files
```

## 🛡️ Safety Features

Fast Fixup Finder includes built-in safety features:

- **Automatic backups** - Creates git stash before making changes
- **Dry-run mode** - Preview changes without modifying repository  
- **Interactive selection** - Choose exactly which fixups to create
- **Visual GUI mode** - Drag-and-drop interface for intuitive assignment
- **Tab completion** - Shell completion for commands, paths, and options
- **Backup restoration** - Easy recovery from automatic backups

See [SAFETY.md](SAFETY.md) for comprehensive safety strategies and emergency recovery procedures.

## Typical Workflows

### 🎨 **Visual Workflow (Recommended)**
```mermaid
graph LR
    A[Make changes] --> B[fastfixupfinder gui]
    B --> C[Drag changes to targets]
    C --> D[Press 'c' to create fixups]
    D --> E[git rebase -i --autosquash]
    E --> F[Clean history]
```

1. **Make changes** to your files across the project
2. **Launch GUI** with `fastfixupfinder gui`
3. **Visually assign** changes by navigating and pressing ENTER
4. **Create fixups** by pressing 'c' in the GUI
5. **Apply** with the suggested rebase command

### 📝 **CLI Workflow (Quick)**
```mermaid
graph LR
    A[Make changes] --> B[fastfixupfinder status]
    B --> C{Review targets}
    C --> D[fastfixupfinder create]
    D --> E[git rebase -i --autosquash]
    E --> F[Clean history]
```

1. **Make changes** to your files
2. **Check status** with `fastfixupfinder status`
3. **Auto-create** with `fastfixupfinder create` (or `--interactive` for control)
4. **Apply** with the suggested rebase command

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
- 🎨 **Complex fixup scenarios** where visual assignment is helpful
- ⚡ **Large codebases** with many interconnected changes

## Options

### Global Options
- `--repo PATH` - Specify repository path (default: current directory)

### Status Command Options
- `--oneline` - Show compact one-line output per target
- `--detailed` - Show detailed analysis of changes and target commits
- `--fixups-only` - Only show high-confidence fixup targets
- `--include-all` - Include all changes regardless of fixup likelihood

### Create Command Options
- `--dry-run` - Show what would be done without making changes
- `--interactive, -i` - Interactively select targets with line-level classification control
- `--oneline` - Use compact output in interactive mode (reduces screen clutter)

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