# Fast Fixup Finder

A tool to automatically identify fixup targets and create fixup commits based on your current changes.

## What it does

When you edit files in a project, those changes often touch lines that were created in different commits. This tool:

1. **Analyzes** your current changes (staged and unstaged)
2. **Traces** each modified line back to its original commit using `git blame`
3. **Groups** changes by their target commits
4. **Creates** appropriately named fixup commits
5. **Suggests** the rebase command to apply them

## Quick Start

### Installation

#### Option 1: Using Virtual Environment (Recommended)

```bash
# Clone the repository
git clone https://github.com/kgerlich/fastfixupfinder.git
cd fastfixupfinder

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

### Basic Usage

```bash
# Check what fixup targets are available
fastfixupfinder status

# See detailed analysis of your changes
fastfixupfinder analyze

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
| `analyze` | Show detailed analysis of changes and their target commits |
| `create` | Create fixup commits for identified targets |
| `create --dry-run` | Preview what would be created without making changes |
| `create --interactive` | Interactively select which targets to create fixups for |
| `help-usage` | Show detailed usage examples and workflow guidance |

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

```bash
cd testcase
./demo.sh  # Run the demonstration
```

## Requirements

- **Python 3.10+**
- **Git repository** with existing commits
- **GitPython library** (automatically installed)

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

### Create Command Options
- `--dry-run` - Show what would be done without making changes
- `--interactive, -i` - Interactively select targets

## Troubleshooting

### Common Issues

1. **"No fixup targets found"** - Ensure you have uncommitted changes and the files have git history
2. **Module not found** - Run with `PYTHONPATH=. python -m fastfixupfinder.cli` if not installed, or activate your virtual environment
3. **Permission errors** - Ensure you have write access to the git repository
4. **Command not found after installation** - Make sure your virtual environment is activated or the installation path is in your PATH

### Debug Mode

For troubleshooting, you can run commands with increased verbosity by examining the tool's output in detail with the `analyze` command.