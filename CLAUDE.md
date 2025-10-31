# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fast Fixup Finder is a comprehensive Python tool for intelligent fixup commit management. It provides CLI and interactive interfaces to automatically identify fixup targets and create fixup commits based on current changes. It uses git blame to trace modified lines back to their original commits, intelligent classification to distinguish fixups from new features, and groups changes appropriately.

**Note:** This package is not published to PyPI. Installation is from GitHub or local repository only.

## Commands

### Development Setup
```bash
# Clone repository and set up development environment
git clone https://github.com/klausgerlicher/fastfixupfinder.git
cd fastfixupfinder

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies (recommended)
pip install -e ".[dev]"

# Or use Makefile for convenience
make install-dev  # Sets up venv and installs with dev dependencies
```

### Running the Tool
```bash
# Show potential fixup targets (smart filtering)
fastfixupfinder status
fastfixupfinder status --detailed         # Detailed analysis
fastfixupfinder status --fixups-only      # Only high-confidence fixups
fastfixupfinder status --include-all      # All changes, no filtering

# Create fixup commits
fastfixupfinder create                    # Create all automatically
fastfixupfinder create -i                 # Interactive mode with selection
fastfixupfinder create -i --oneline       # Compact interactive mode
fastfixupfinder create --dry-run          # Preview without changes
fastfixupfinder create --limit <sha>      # Limit to commits after SHA1

# Utilities
fastfixupfinder resquash <sha>            # Convert fixup! to squash! with editing
fastfixupfinder restore                   # Restore from automatic backup
fastfixupfinder help-usage                # Show usage examples
```

### Testing and Code Quality
```bash
# Code formatting (PEP 8 compliance)
black .                                   # Format all Python files
black fastfixupfinder/                    # Format specific module

# Linting and error detection
flake8 .                                  # Check code style and errors
flake8 --count --statistics               # Show detailed statistics

# Type checking
mypy .                                    # Full type checking
mypy fastfixupfinder/cli.py               # Type check specific file

# Run all quality checks
black --check .  # Check formatting without changes
flake8 . && mypy . && echo "✓ All checks passed"
```

### Testing and Demonstration
```bash
# Run test suite (requires pytest installation)
pytest                                    # Run all tests
pytest -v                                 # Verbose output
pytest fastfixupfinder/test_*.py          # Run specific test file
pytest -k "test_name"                     # Run tests matching pattern

# Direct tool testing
fastfixupfinder status                    # Test status command
fastfixupfinder create --dry-run          # Test create with preview
fastfixupfinder create -i                 # Test interactive mode
```

## Architecture

### Data Flow

```
git diff (working directory)
       ↓
[ChangedLine: file, line_no, operation, content]
       ↓
git blame (trace original commits)
       ↓
[BlameInfo: commit_hash, author, date]
       ↓
Classification heuristics (LIKELY/POSSIBLE/UNLIKELY)
       ↓
[FixupTarget: commit_hash, message, grouped changes]
       ↓
User interface (CLI / Interactive)
       ↓
Create fixup! commits + automatic backup tag
```

### Core Modules

**`git_analyzer.py`** - Analysis engine (~700 lines)
- `GitAnalyzer`: Main analysis class with diff parsing and blame tracing
- `ChangedLine`: Dataclass for individual line changes (file, line_no, operation, content)
- `BlameInfo`: Dataclass for git blame information (commit, author, date)
- `FixupTarget`: Dataclass for grouped changes targeting a commit
- `FilterMode` (enum): SMART_DEFAULT, FIXUPS_ONLY, INCLUDE_ALL
- `ClassifyResult` (enum): Classification outcomes for heuristics

Key methods:
- `find_fixup_targets(filter_mode)`: Main entry point, returns list of FixupTarget
- `_parse_git_diff()`: Parse working directory changes
- `_get_blame_info()`: Trace lines to original commits
- `_classify_changes()`: Apply intelligence heuristics
- `filter_targets_by_organization()`: Email-based filtering

**`fixup_creator.py`** - Commit creation (~2000 lines)
- `FixupCreator`: High-level interface for creating fixup commits
- `InteractiveSelector`: User selection logic (targets and lines)
- `Colors`: Terminal color management

Key methods:
- `create_fixup_commits()`: Main entry for automatic creation
- `interactive_create_fixup_commits()`: Interactive target/line selection
- `_stage_changes_for_target()`: Stage lines for specific commit
- `_create_backup()`: Git stash backup creation
- `_suggest_rebase_command()`: Calculate appropriate rebase range

**`cli.py`** - Command-line interface (~400 lines)
- Click-based CLI with subcommands: status, create, resquash, restore, help-usage
- Option handling for filtering, dry-run, interactive, oneline, org-email, limit-sha
- Output formatting and progress callbacks

### Key Design Decisions

1. **Git blame as single source of truth**: Each modified line is traced to its original commit. Lines not in version control (new files) are handled separately.

2. **Classification heuristics**: Rather than ML, uses pattern matching:
   - Likely fixups: Typos, comments, small string changes
   - Possible fixups: Mixed changes that could go either way
   - Unlikely fixups: New functions, large logic changes, imports

3. **Two interfaces**:
   - **CLI**: Fastest, scriptable, best for automation
   - **Interactive**: Balance between speed and control

4. **Safety-first backup strategy**: Automatic git stash before creating commits (can be skipped with --no-backup)

5. **FilterMode pattern**: Smart defaults that filter noise while interactive mode shows all options

### Data Flow During Commit Creation

1. Get all changed lines via `git diff`
2. For each line, run `git blame` to find original commit
3. Group lines by target commit
4. For non-interactive mode: auto-assign all lines, create fixup commits
5. For interactive mode: present targets → user selects → present lines → user selects → create commits

### Important Implementation Details

- **Line number tracking**: Works with both staged and unstaged changes via diff parsing
- **Blame context**: For newly added lines, uses surrounding context to infer likely target
- **Whitespace handling**: Changes in whitespace only are marked but filtered by default
- **Organization filtering**: Applied after classification, not during initial analysis
- **Dry-run mode**: Prints git commands that would be executed, doesn't modify state

## Development Workflow

### Before Making Changes
1. Check current status: `git status`
2. Review recent commits to understand context
3. Install dev dependencies: `pip install -e ".[dev]"`

### While Working
1. Format code as you go: `black fastfixupfinder/`
2. Run type checker on modified files: `mypy fastfixupfinder/your_file.py`
3. Test manually with: `fastfixupfinder status` and `fastfixupfinder create --dry-run`
4. Test interactive mode: `fastfixupfinder create -i`

### Before Committing
1. Run full quality checks:
   ```bash
   black --check . && flake8 . && mypy . && echo "✓ All checks passed"
   ```
2. Format if needed: `black .`
3. Test with tool commands: `fastfixupfinder status`, `fastfixupfinder create --dry-run`
4. Verify no breaking changes to CLI interface

### Testing Strategy
- Test CLI commands directly: status, create (--dry-run), create (-i)
- Create isolated test scenarios for edge cases
- Dry-run mode (`--dry-run`) is your friend for validation

## Important Notes

- **Git blame accuracy**: Tool relies on clean git history. Rebasing can affect blame results.
- **Windows compatibility**: Code uses pathlib for cross-platform paths; test Windows behavior when dealing with file operations.
- **Performance**: For large repos with many changes, progress callbacks show status during git blame operations
- **Color output**: Terminal color codes are managed by `Colors` class in fixup_creator.py