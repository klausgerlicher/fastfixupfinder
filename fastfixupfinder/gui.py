"""NCurses-based GUI for visual fixup assignment."""

import curses
import curses.panel
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

from .git_analyzer import GitAnalyzer, FixupTarget, ChangedLine, ChangeClassification
from .fixup_creator import FixupCreator


class Panel(Enum):
    """Active panel in the GUI."""
    CHANGES = "changes"
    TARGETS = "targets"


@dataclass
class Assignment:
    """Represents a change assigned to a fixup target."""
    change: ChangedLine
    target_hash: str


@dataclass
class GUIState:
    """Current state of the GUI."""
    active_panel: Panel = Panel.CHANGES
    selected_change_idx: int = 0
    selected_target_idx: int = 0
    scroll_changes: int = 0
    scroll_targets: int = 0
    assignments: List[Assignment] = None
    expanded_files: Set[str] = None
    expanded_targets: Set[str] = None
    
    def __post_init__(self):
        if self.assignments is None:
            self.assignments = []
        if self.expanded_files is None:
            self.expanded_files = set()
        if self.expanded_targets is None:
            self.expanded_targets = set()


class FixupGUI:
    """NCurses-based GUI for visual fixup assignment."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize the GUI with repository path."""
        self.repo_path = repo_path
        self.analyzer = GitAnalyzer(repo_path)
        self.creator = FixupCreator(repo_path)
        
        # Data
        self.changes: List[ChangedLine] = []
        self.targets: List[FixupTarget] = []
        self.files_changes: Dict[str, List[ChangedLine]] = {}
        
        # GUI state
        self.state = GUIState()
        
        # NCurses objects
        self.stdscr = None
        self.changes_win = None
        self.targets_win = None
        self.status_win = None
        self.changes_panel = None
        self.targets_panel = None
        
        # Colors
        self.colors = {}
        
    def load_data(self):
        """Load changes and fixup targets from the repository."""
        self.changes = self.analyzer.get_changed_lines()
        self.targets = self.analyzer.find_fixup_targets()
        
        # Group changes by file
        self.files_changes = {}
        for change in self.changes:
            if change.file_path not in self.files_changes:
                self.files_changes[change.file_path] = []
            self.files_changes[change.file_path].append(change)
        
        # Expand all files by default
        self.state.expanded_files = set(self.files_changes.keys())
        self.state.expanded_targets = {target.commit_hash for target in self.targets}
    
    def init_colors(self):
        """Initialize color pairs for the GUI."""
        curses.start_color()
        curses.use_default_colors()
        
        # Color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # LIKELY_FIXUP
        curses.init_pair(2, curses.COLOR_YELLOW, -1)   # POSSIBLE_FIXUP
        curses.init_pair(3, curses.COLOR_RED, -1)      # UNLIKELY_FIXUP
        curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # NEW_FILE
        curses.init_pair(5, curses.COLOR_BLUE, -1)     # ASSIGNED
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # HEADER
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)  # SELECTED
        
        self.colors = {
            'likely': curses.color_pair(1),
            'possible': curses.color_pair(2),
            'unlikely': curses.color_pair(3),
            'new_file': curses.color_pair(4),
            'assigned': curses.color_pair(5),
            'header': curses.color_pair(6),
            'selected': curses.color_pair(7),
            'normal': curses.color_pair(0)
        }
    
    def setup_windows(self):
        """Set up the main windows and panels."""
        height, width = self.stdscr.getmaxyx()
        
        # Create windows
        # Header (1 line)
        header_height = 1
        
        # Status bar (2 lines)
        status_height = 2
        
        # Main content area
        content_height = height - header_height - status_height
        content_width = width
        
        # Split content area into two panels
        panel_width = content_width // 2
        
        # Changes panel (left)
        self.changes_win = curses.newwin(
            content_height, panel_width, 
            header_height, 0
        )
        
        # Targets panel (right)
        self.targets_win = curses.newwin(
            content_height, panel_width, 
            header_height, panel_width
        )
        
        # Status window (bottom)
        self.status_win = curses.newwin(
            status_height, width,
            height - status_height, 0
        )
        
        # Create panels for layering
        self.changes_panel = curses.panel.new_panel(self.changes_win)
        self.targets_panel = curses.panel.new_panel(self.targets_win)
        
        # Enable keypad for special keys
        self.changes_win.keypad(True)
        self.targets_win.keypad(True)
        self.stdscr.keypad(True)
    
    def draw_header(self):
        """Draw the header with title and help."""
        height, width = self.stdscr.getmaxyx()
        title = "Fast Fixup Finder - Visual Assignment Mode"
        help_text = "[q]uit [h]elp [TAB] switch [c]reate"
        
        # Clear header area
        self.stdscr.addstr(0, 0, " " * width)
        
        # Title (left)
        self.stdscr.addstr(0, 2, title, self.colors['header'] | curses.A_BOLD)
        
        # Help (right)
        help_x = width - len(help_text) - 2
        if help_x > len(title) + 4:
            self.stdscr.addstr(0, help_x, help_text, self.colors['normal'])
        
        # Separator line
        self.stdscr.hline(1, 0, curses.ACS_HLINE, width)
    
    def draw_changes_panel(self):
        """Draw the left panel with changes."""
        self.changes_win.clear()
        self.changes_win.box()
        
        height, width = self.changes_win.getmaxyx()
        
        # Panel title
        title = "CHANGES (Unassigned)"
        self.changes_win.addstr(0, 2, f" {title} ", self.colors['header'] | curses.A_BOLD)
        
        # Panel highlight if active
        if self.state.active_panel == Panel.CHANGES:
            self.changes_win.attron(curses.A_BOLD)
            self.changes_win.box()
            self.changes_win.attroff(curses.A_BOLD)
        
        # Content area
        content_y = 2
        content_height = height - 3  # Account for box and instructions
        y = content_y
        
        if not self.files_changes:
            self.changes_win.addstr(y, 2, "No changes found", self.colors['normal'])
            self.changes_win.refresh()
            return
        
        # Draw file groups and changes
        current_item = 0
        for file_path, file_changes in self.files_changes.items():
            if y >= content_height + content_y - 1:
                break
            
            # File header
            expanded = file_path in self.state.expanded_files
            expand_char = "▼" if expanded else "▶"
            
            # Highlight if this is the selected item
            attr = self.colors['selected'] if (
                self.state.active_panel == Panel.CHANGES and 
                current_item == self.state.selected_change_idx
            ) else self.colors['header']
            
            file_display = f"{expand_char} File: {Path(file_path).name}"
            if len(file_display) > width - 4:
                file_display = file_display[:width-7] + "..."
            
            self.changes_win.addstr(y, 2, file_display, attr | curses.A_BOLD)
            y += 1
            current_item += 1
            
            # File changes (if expanded)
            if expanded:
                for change in file_changes:
                    if y >= content_height + content_y - 1:
                        break
                    
                    # Check if change is assigned
                    is_assigned = any(a.change == change for a in self.state.assignments)
                    
                    # Classification color
                    if is_assigned:
                        color = self.colors['assigned']
                    else:
                        color_map = {
                            ChangeClassification.LIKELY_FIXUP: self.colors['likely'],
                            ChangeClassification.POSSIBLE_FIXUP: self.colors['possible'],
                            ChangeClassification.UNLIKELY_FIXUP: self.colors['unlikely'],
                            ChangeClassification.NEW_FILE: self.colors['new_file']
                        }
                        color = color_map.get(change.classification, self.colors['normal'])
                    
                    # Highlight if selected
                    if (self.state.active_panel == Panel.CHANGES and 
                        current_item == self.state.selected_change_idx):
                        color = self.colors['selected']
                    
                    # Change type symbol
                    symbol_map = {'+': '+', '-': '-', 'modified': '~', 'added': '+', 'deleted': '-'}
                    symbol = symbol_map.get(change.change_type, '?')
                    
                    # Format change line
                    status_char = "●" if is_assigned else "○"
                    content_preview = change.content.strip()[:width-15] + ("..." if len(change.content.strip()) > width-15 else "")
                    
                    change_line = f"  {status_char} {symbol} L{change.line_number}: {content_preview}"
                    self.changes_win.addstr(y, 2, change_line[:width-4], color)
                    y += 1
                    current_item += 1
        
        # Instructions at bottom
        if y < content_height + content_y - 2:
            instructions = [
                "[ENTER] Assign to target",
                "[TAB] Switch panels", 
                "[↑↓] Navigate"
            ]
            for i, instruction in enumerate(instructions):
                if content_height + content_y - 2 + i < height - 1:
                    self.changes_win.addstr(content_height + content_y - 2 + i, 2, 
                                          instruction, self.colors['normal'])
        
        self.changes_win.refresh()
    
    def draw_targets_panel(self):
        """Draw the right panel with fixup targets."""
        self.targets_win.clear()
        self.targets_win.box()
        
        height, width = self.targets_win.getmaxyx()
        
        # Panel title
        title = "FIXUP TARGETS"
        self.targets_win.addstr(0, 2, f" {title} ", self.colors['header'] | curses.A_BOLD)
        
        # Panel highlight if active
        if self.state.active_panel == Panel.TARGETS:
            self.targets_win.attron(curses.A_BOLD)
            self.targets_win.box()
            self.targets_win.attroff(curses.A_BOLD)
        
        # Content area
        content_y = 2
        content_height = height - 3
        y = content_y
        
        if not self.targets:
            self.targets_win.addstr(y, 2, "No fixup targets found", self.colors['normal'])
            self.targets_win.refresh()
            return
        
        # Draw targets
        for i, target in enumerate(self.targets):
            if y >= content_height + content_y - 1:
                break
            
            # Target header
            expanded = target.commit_hash in self.state.expanded_targets
            expand_char = "▼" if expanded else "▶"
            
            # Highlight if selected
            attr = self.colors['selected'] if (
                self.state.active_panel == Panel.TARGETS and 
                i == self.state.selected_target_idx
            ) else self.colors['header']
            
            # Count assigned changes
            assigned_count = len([a for a in self.state.assignments 
                                if a.target_hash == target.commit_hash])
            
            short_hash = target.commit_hash[:8]
            message = target.commit_message[:width-25] + ("..." if len(target.commit_message) > width-25 else "")
            target_display = f"{expand_char} {short_hash}: {message}"
            
            if assigned_count > 0:
                target_display += f" ({assigned_count})"
            
            self.targets_win.addstr(y, 2, target_display[:width-4], attr | curses.A_BOLD)
            y += 1
            
            # Target details (if expanded)
            if expanded:
                # Author
                if y < content_height + content_y - 1:
                    author_line = f"  👤 {target.author}"
                    self.targets_win.addstr(y, 2, author_line[:width-4], self.colors['normal'])
                    y += 1
                
                # Assigned changes
                if y < content_height + content_y - 1:
                    assigned_changes = [a.change for a in self.state.assignments 
                                      if a.target_hash == target.commit_hash]
                    
                    if assigned_changes:
                        self.targets_win.addstr(y, 2, "  📋 Assigned:", self.colors['normal'])
                        y += 1
                        
                        for change in assigned_changes[:3]:  # Show first 3
                            if y >= content_height + content_y - 1:
                                break
                            change_summary = f"    • {Path(change.file_path).name}:{change.line_number}"
                            self.targets_win.addstr(y, 2, change_summary[:width-4], 
                                                  self.colors['assigned'])
                            y += 1
                        
                        if len(assigned_changes) > 3:
                            if y < content_height + content_y - 1:
                                more_text = f"    ... and {len(assigned_changes) - 3} more"
                                self.targets_win.addstr(y, 2, more_text, self.colors['normal'])
                                y += 1
                    else:
                        self.targets_win.addstr(y, 2, "  📋 (no assignments)", 
                                              self.colors['normal'])
                        y += 1
                
                if y < content_height + content_y - 1:
                    y += 1  # Spacing
        
        self.targets_win.refresh()
    
    def draw_status_bar(self):
        """Draw the status bar with counts and actions."""
        self.status_win.clear()
        height, width = self.status_win.getmaxyx()
        
        # Top border
        self.status_win.hline(0, 0, curses.ACS_HLINE, width)
        
        # Status information
        unassigned_count = len([c for c in self.changes 
                              if not any(a.change == c for a in self.state.assignments)])
        assigned_count = len(self.state.assignments)
        target_count = len(self.targets)
        
        status_left = f"Status: {unassigned_count} unassigned, {assigned_count} assigned, {target_count} targets"
        status_right = "[c]reate fixups [r]eset [s]ave [q]uit"
        
        # Left status
        self.status_win.addstr(1, 2, status_left, self.colors['normal'])
        
        # Right actions
        status_right_x = width - len(status_right) - 2
        if status_right_x > len(status_left) + 4:
            self.status_win.addstr(1, status_right_x, status_right, self.colors['normal'])
        
        self.status_win.refresh()
    
    def get_current_change(self) -> Optional[ChangedLine]:
        """Get the currently selected change."""
        if self.state.active_panel != Panel.CHANGES:
            return None
        
        current_item = 0
        for file_path, file_changes in self.files_changes.items():
            if current_item == self.state.selected_change_idx:
                return None  # Selected file header, not a change
            current_item += 1
            
            if file_path in self.state.expanded_files:
                for change in file_changes:
                    if current_item == self.state.selected_change_idx:
                        return change
                    current_item += 1
        
        return None
    
    def get_current_target(self) -> Optional[FixupTarget]:
        """Get the currently selected target."""
        if (self.state.active_panel != Panel.TARGETS or 
            self.state.selected_target_idx >= len(self.targets)):
            return None
        return self.targets[self.state.selected_target_idx]
    
    def assign_change_to_target(self, change: ChangedLine, target: FixupTarget):
        """Assign a change to a fixup target."""
        # Remove any existing assignment for this change
        self.state.assignments = [a for a in self.state.assignments if a.change != change]
        
        # Add new assignment
        assignment = Assignment(change=change, target_hash=target.commit_hash)
        self.state.assignments.append(assignment)
    
    def handle_key(self, key: int) -> bool:
        """Handle keyboard input. Returns False to quit."""
        if key == ord('q') or key == ord('Q'):
            return False
        
        elif key == ord('h') or key == ord('H'):
            self.show_help()
        
        elif key == ord('\t') or key == 9:  # TAB
            if self.state.active_panel == Panel.CHANGES:
                self.state.active_panel = Panel.TARGETS
                self.state.selected_target_idx = min(self.state.selected_target_idx, 
                                                   len(self.targets) - 1)
            else:
                self.state.active_panel = Panel.CHANGES
        
        elif key == curses.KEY_UP:
            if self.state.active_panel == Panel.CHANGES:
                self.state.selected_change_idx = max(0, self.state.selected_change_idx - 1)
            else:
                self.state.selected_target_idx = max(0, self.state.selected_target_idx - 1)
        
        elif key == curses.KEY_DOWN:
            if self.state.active_panel == Panel.CHANGES:
                # Count total items in changes panel
                total_items = 0
                for file_path, file_changes in self.files_changes.items():
                    total_items += 1  # File header
                    if file_path in self.state.expanded_files:
                        total_items += len(file_changes)
                
                self.state.selected_change_idx = min(total_items - 1, 
                                                   self.state.selected_change_idx + 1)
            else:
                self.state.selected_target_idx = min(len(self.targets) - 1, 
                                                   self.state.selected_target_idx + 1)
        
        elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:  # ENTER
            if self.state.active_panel == Panel.CHANGES:
                change = self.get_current_change()
                if change and self.targets:
                    # Switch to targets panel for assignment
                    self.state.active_panel = Panel.TARGETS
            elif self.state.active_panel == Panel.TARGETS:
                # Assign current change to current target
                change = self.get_current_change()
                target = self.get_current_target()
                if change and target:
                    self.assign_change_to_target(change, target)
        
        elif key == ord(' '):  # SPACE - quick assign
            change = self.get_current_change()
            target = self.get_current_target()
            if change and target:
                self.assign_change_to_target(change, target)
        
        elif key == curses.KEY_DC or key == 127:  # DELETE
            change = self.get_current_change()
            if change:
                # Remove assignment
                self.state.assignments = [a for a in self.state.assignments if a.change != change]
        
        elif key == ord('c') or key == ord('C'):
            self.create_fixups()
        
        elif key == ord('r') or key == ord('R'):
            self.state.assignments.clear()
        
        return True
    
    def show_help(self):
        """Show help dialog."""
        # Simple help - could be enhanced with a proper dialog
        pass
    
    def create_fixups(self):
        """Create fixup commits from current assignments."""
        if not self.state.assignments:
            return
        
        # Group assignments by target
        target_assignments = {}
        for assignment in self.state.assignments:
            if assignment.target_hash not in target_assignments:
                target_assignments[assignment.target_hash] = []
            target_assignments[assignment.target_hash].append(assignment.change)
        
        # Create modified FixupTarget objects with only assigned changes
        assigned_targets = []
        for target in self.targets:
            if target.commit_hash in target_assignments:
                assigned_changes = target_assignments[target.commit_hash]
                assigned_files = {change.file_path for change in assigned_changes}
                
                modified_target = FixupTarget(
                    commit_hash=target.commit_hash,
                    commit_message=target.commit_message,
                    author=target.author,
                    changed_lines=assigned_changes,
                    files=assigned_files
                )
                assigned_targets.append(modified_target)
        
        # Stage all changes first
        self.creator.repo.git.add('.')
        
        # Create fixup commits for assigned targets
        created_commits = []
        for target in assigned_targets:
            commit_hash = self.creator.create_fixup_commit(target, dry_run=False)
            if commit_hash:
                created_commits.append(commit_hash)
        
        # Clear assignments after successful creation
        if created_commits:
            self.state.assignments.clear()
    
    def run(self):
        """Main GUI loop."""
        def main(stdscr):
            self.stdscr = stdscr
            curses.curs_set(0)  # Hide cursor
            
            # Initialize
            self.load_data()
            self.init_colors()
            self.setup_windows()
            
            # Main loop
            while True:
                # Clear and redraw
                self.stdscr.clear()
                self.draw_header()
                self.draw_changes_panel()
                self.draw_targets_panel()
                self.draw_status_bar()
                
                # Update panels
                curses.panel.update_panels()
                curses.doupdate()
                
                # Get input
                key = self.stdscr.getch()
                
                # Handle key
                if not self.handle_key(key):
                    break
        
        curses.wrapper(main)


def main():
    """Entry point for GUI mode."""
    gui = FixupGUI()
    gui.run()


if __name__ == "__main__":
    main()