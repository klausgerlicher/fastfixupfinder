# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fast Fixup Finder is a Python CLI tool that automatically identifies fixup targets and creates fixup commits based on current changes. It uses git blame to trace modified lines back to their original commits and groups changes appropriately.

## Commands

### Development Commands
```bash
# Install in development mode
pip install -e .

# Run the tool
fastfixupfinder status          # Show potential fixup targets
fastfixupfinder analyze         # Detailed analysis
fastfixupfinder create          # Create fixup commits
fastfixupfinder create -i       # Interactive mode
fastfixupfinder create --dry-run # Preview mode

# Testing and linting (when implemented)
pytest                          # Run tests
black .                         # Format code
flake8 .                        # Lint code
mypy .                          # Type checking
```

## Architecture

### Core Components

- **`git_analyzer.py`**: Core analysis engine
  - `GitAnalyzer`: Main class for analyzing repository changes
  - `ChangedLine`: Represents individual line changes
  - `BlameInfo`: Git blame information for lines
  - `FixupTarget`: Grouped changes targeting specific commits

- **`fixup_creator.py`**: Commit creation logic
  - `FixupCreator`: Handles the creation of fixup commits
  - Interactive and automatic modes
  - Staging and commit management

- **`cli.py`**: Command-line interface
  - Click-based CLI with multiple subcommands
  - User interaction and error handling

### Workflow
1. Analyze current working directory changes (staged/unstaged)
2. Parse git diff output to identify changed lines
3. Use git blame to find original commits for each line
4. Group changes by target commit
5. Create fixup commits with appropriate naming
6. Suggest rebase command for applying fixups

### Key Features
- Handles both staged and unstaged changes
- Context-aware grouping for added lines
- Interactive selection of fixup targets
- Dry-run mode for safe preview
- Automatic rebase command suggestion