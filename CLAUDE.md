# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fast Fixup Finder is a comprehensive Python tool for intelligent fixup commit management. It provides multiple interfaces (CLI, interactive, and visual GUI) to automatically identify fixup targets and create fixup commits based on current changes. It uses git blame to trace modified lines back to their original commits, intelligent classification to distinguish fixups from new features, and groups changes appropriately.

## Commands

### Development Commands
```bash
# Set up development environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# For user installation PATH setup
python3 setup_path.py        # Automatic PATH configuration
./setup_path.sh              # Unix/Linux script
setup_path.bat               # Windows script

# Run the tool
fastfixupfinder status          # Show potential fixup targets (smart filtering)
fastfixupfinder status --detailed # Detailed analysis (replaces old analyze command)
fastfixupfinder status --fixups-only # Only high-confidence fixups
fastfixupfinder status --include-all # All changes, no filtering
fastfixupfinder create          # Create fixup commits automatically
fastfixupfinder create -i       # Interactive mode with line-level control
fastfixupfinder create -i --oneline # Compact interactive mode
fastfixupfinder create --dry-run # Preview mode
fastfixupfinder gui             # Visual drag-and-drop interface
fastfixupfinder restore         # Restore from automatic backup

# Testing and demonstration
./run_demo.sh                   # Interactive demo walkthrough
cd testcase && ./demo.sh        # Basic demo script

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
  - GUI command integration

- **`gui.py`**: Visual ncurses interface
  - Dual-panel layout for changes and targets
  - Drag-and-drop assignment functionality
  - Color-coded classifications and real-time feedback
  - Keyboard navigation and hotkeys

### Workflow Options

**CLI Workflow:**
1. Analyze current working directory changes (staged/unstaged)
2. Parse git diff output to identify changed lines
3. Use git blame to find original commits for each line
4. Apply intelligent classification (LIKELY/POSSIBLE/UNLIKELY fixups)
5. Group changes by target commit with filtering
6. Create fixup commits with appropriate naming
7. Suggest rebase command for applying fixups

**GUI Workflow:**
1. Load changes and targets into visual interface
2. Display changes (left panel) and targets (right panel)
3. User assigns changes to targets via keyboard navigation
4. Real-time visual feedback and assignment tracking
5. Create fixup commits directly from GUI
6. Automatic rebase command suggestion

### Key Features
- **Intelligent Classification**: Distinguishes fixups from new features using heuristics
- **Multiple Interfaces**: CLI, enhanced interactive, and visual GUI modes
- **Smart Filtering**: LIKELY/POSSIBLE/UNLIKELY classifications with filtering options
- **Line-Level Control**: Precise assignment of individual changes to fixup targets
- **Visual Assignment**: Drag-and-drop GUI for complex workflows
- **Safety Features**: Automatic backups and restore functionality
- **Context-Aware Analysis**: Grouping for added lines using git blame context
- **Flexible Output**: Compact and detailed modes for different use cases

## Best Practices

- Always ask me before a push