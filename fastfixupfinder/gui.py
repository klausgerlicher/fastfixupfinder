"""Rich + Textual-based GUI for visual fixup assignment."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button, DataTable, Footer, Header, Label, ListItem, ListView, 
    Static, TabbedContent, TabPane
)
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from rich.text import Text
from rich.console import Console
from rich.table import Table as RichTable

from .git_analyzer import GitAnalyzer, FixupTarget, ChangedLine, ChangeClassification
from .fixup_creator import FixupCreator


@dataclass
class Assignment:
    """Represents a change assigned to a fixup target."""
    change: ChangedLine
    target_hash: str


class ChangeItem(ListItem):
    """Custom list item for displaying changes."""
    
    def __init__(self, change: ChangedLine, *args, **kwargs):
        self.change = change
        
        # Create the display text
        display_text = self._create_display_text()
        
        # Create a label with the formatted text
        label = Label(display_text, markup=True)
        super().__init__(label, *args, **kwargs)
    
    def _create_display_text(self) -> str:
        """Create the display text for this change."""
        # Change type symbol
        symbol_map = {
            "added": "[green]+[/green]",
            "deleted": "[red]-[/red]", 
            "modified": "[yellow]~[/yellow]"
        }
        
        # Classification color mapping
        classification_colors = {
            ChangeClassification.LIKELY_FIXUP: "green",
            ChangeClassification.POSSIBLE_FIXUP: "yellow", 
            ChangeClassification.UNLIKELY_FIXUP: "red",
            ChangeClassification.NEW_FILE: "magenta"
        }
        
        symbol = symbol_map.get(self.change.change_type, "?")
        color = classification_colors.get(self.change.classification, "white")
        
        # Format the display text
        file_path = Path(self.change.file_path).name  # Just filename
        content_preview = self.change.content[:50] + "..." if len(self.change.content) > 50 else self.change.content
        
        classification_text = self.change.classification.value.replace('_', ' ').title()
        
        return f"{symbol} [cyan]{file_path}:{self.change.line_number}[/cyan] {content_preview} [bold {color}][{classification_text}][/bold {color}]"


class TargetItem(ListItem):
    """Custom list item for displaying fixup targets."""
    
    def __init__(self, target: FixupTarget, assignment_count: int = 0, *args, **kwargs):
        self.target = target
        self.assignment_count = assignment_count
        
        # Create the display text
        display_text = self._create_display_text()
        
        # Create a label with the formatted text
        label = Label(display_text, markup=True)
        super().__init__(label, *args, **kwargs)
    
    def _create_display_text(self) -> str:
        """Create the display text for this target."""
        # Truncate long commit messages
        message = self.target.commit_message
        if len(message) > 60:
            message = message[:57] + "..."
        
        # Format the display text
        if self.assignment_count > 0:
            count_text = f"[green]({self.assignment_count} assigned)[/green]"
        else:
            count_text = f"[dim]({len(self.target.changed_lines)} changes)[/dim]"
        
        return f"[bright_cyan bold]{self.target.commit_hash[:8]}[/bright_cyan bold] [white bold]{message}[/white bold] {count_text}"


class PreviewPanel(Static):
    """Panel showing current assignments and preview of commands."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assignments: List[Assignment] = []
    
    def update_assignments(self, assignments: List[Assignment]):
        """Update the assignments and refresh display."""
        self.assignments = assignments
        self.update_display()
    
    def update_display(self):
        """Update the preview display."""
        if not self.assignments:
            self.update("No assignments yet. Select changes and press 'a' to assign to selected target.")
            return
        
        # Group assignments by target
        by_target: Dict[str, List[Assignment]] = {}
        for assignment in self.assignments:
            if assignment.target_hash not in by_target:
                by_target[assignment.target_hash] = []
            by_target[assignment.target_hash].append(assignment)
        
        # Create preview text
        console = Console()
        with console.capture() as capture:
            console.print("📋 [bold white]Current Assignments:[/bold white]")
            console.print()
            
            for target_hash, target_assignments in by_target.items():
                files = set(a.change.file_path for a in target_assignments)
                console.print(f"🎯 [bright_cyan]{target_hash[:8]}[/bright_cyan]: [green]{len(target_assignments)}[/green] changes in [blue]{len(files)}[/blue] files")
                
                # Show files
                for file_path in sorted(files):
                    file_assignments = [a for a in target_assignments if a.change.file_path == file_path]
                    console.print(f"  📄 [cyan]{Path(file_path).name}[/cyan]: {len(file_assignments)} changes")
            
            console.print()
            console.print("🚀 [bold white]Commands that will be run:[/bold white]")
            for target_hash in by_target.keys():
                console.print(f"  git commit --fixup {target_hash[:8]}")
        
        self.update(capture.get())


class FixupGUI(App):
    """Textual-based GUI for visual fixup assignment."""
    
    CSS = """
    #left-panel {
        width: 1fr;
        border: solid $primary;
    }
    
    #right-panel {
        width: 1fr;
        border: solid $secondary;
    }
    
    #preview-panel {
        height: 30%;
        border: solid $accent;
    }
    
    #main-container {
        height: 70%;
    }
    
    ListView {
        border: solid $surface;
    }
    
    .focused {
        border: solid $warning;
    }
    
    .section-header {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-align: center;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "switch_focus", "Switch Panel"),
        Binding("a", "assign", "Assign to Target"),
        Binding("u", "unassign", "Unassign"),
        Binding("c", "create_commits", "Create Fixup Commits"),
        Binding("r", "refresh", "Refresh Data"),
    ]
    
    def __init__(self, repo_path: str = ".", **kwargs):
        super().__init__(**kwargs)
        self.repo_path = repo_path
        self.analyzer = GitAnalyzer(repo_path)
        self.creator = FixupCreator(repo_path)
        
        # Data
        self.changes: List[ChangedLine] = []
        self.targets: List[FixupTarget] = []
        self.assignments: List[Assignment] = []
        
        # UI state
        self.focused_panel = "changes"  # "changes" or "targets"
    
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        
        with Container(id="main-container"):
            with Horizontal():
                with Vertical(id="left-panel"):
                    yield Label("📝 Changes", classes="section-header")
                    yield ListView(id="changes-list")
                
                with Vertical(id="right-panel"):
                    yield Label("🎯 Fixup Targets", classes="section-header")
                    yield ListView(id="targets-list")
        
        with Container(id="preview-panel"):
            yield Label("👁️ Preview", classes="section-header")
            yield PreviewPanel(id="preview")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        self.load_data()
        self.update_ui()
        self.focus_changes_panel()
    
    def load_data(self) -> None:
        """Load changes and targets from the repository."""
        # Get all changes (not just fixup targets)
        self.targets = self.analyzer.find_fixup_targets()
        
        # Get all changed lines
        all_changes = []
        for target in self.targets:
            all_changes.extend(target.changed_lines)
        
        # Remove duplicates (can happen with overlapping targets)
        seen = set()
        self.changes = []
        for change in all_changes:
            key = (change.file_path, change.line_number, change.content)
            if key not in seen:
                seen.add(key)
                self.changes.append(change)
    
    def update_ui(self) -> None:
        """Update all UI elements with current data."""
        self.update_changes_list()
        self.update_targets_list()
        self.update_preview()
    
    def update_changes_list(self) -> None:
        """Update the changes list view."""
        changes_list = self.query_one("#changes-list", ListView)
        changes_list.clear()
        
        # Group changes by file
        by_file: Dict[str, List[ChangedLine]] = {}
        for change in self.changes:
            if change.file_path not in by_file:
                by_file[change.file_path] = []
            by_file[change.file_path].append(change)
        
        # Add file headers and changes
        for file_path, file_changes in sorted(by_file.items()):
            # File header
            file_header = ListItem(Label(f"📄 {file_path} ({len(file_changes)} changes)", 
                                       markup=True), classes="file-header")
            changes_list.append(file_header)
            
            # Changes in this file
            for change in file_changes:
                changes_list.append(ChangeItem(change))
    
    def update_targets_list(self) -> None:
        """Update the targets list view."""
        targets_list = self.query_one("#targets-list", ListView)
        targets_list.clear()
        
        for target in self.targets:
            # Count assignments for this target
            assignment_count = sum(1 for a in self.assignments if a.target_hash == target.commit_hash)
            targets_list.append(TargetItem(target, assignment_count))
    
    def update_preview(self) -> None:
        """Update the preview panel."""
        preview = self.query_one("#preview", PreviewPanel)
        preview.update_assignments(self.assignments)
    
    def focus_changes_panel(self) -> None:
        """Focus the changes panel."""
        self.focused_panel = "changes"
        changes_list = self.query_one("#changes-list", ListView)
        changes_list.focus()
        changes_list.add_class("focused")
        
        targets_list = self.query_one("#targets-list", ListView)
        targets_list.remove_class("focused")
    
    def focus_targets_panel(self) -> None:
        """Focus the targets panel."""
        self.focused_panel = "targets"
        targets_list = self.query_one("#targets-list", ListView)
        targets_list.focus()
        targets_list.add_class("focused")
        
        changes_list = self.query_one("#changes-list", ListView)
        changes_list.remove_class("focused")
    
    def action_switch_focus(self) -> None:
        """Switch focus between panels."""
        if self.focused_panel == "changes":
            self.focus_targets_panel()
        else:
            self.focus_changes_panel()
    
    def action_assign(self) -> None:
        """Assign selected change to selected target."""
        if self.focused_panel != "changes":
            return
        
        changes_list = self.query_one("#changes-list", ListView)
        targets_list = self.query_one("#targets-list", ListView)
        
        if changes_list.index is None or targets_list.index is None:
            return
        
        # Get selected items
        selected_change_item = changes_list.children[changes_list.index]
        selected_target_item = targets_list.children[targets_list.index]
        
        # Skip file headers
        if not isinstance(selected_change_item, ChangeItem) or not isinstance(selected_target_item, TargetItem):
            return
        
        change = selected_change_item.change
        target = selected_target_item.target
        
        # Check if already assigned
        existing = next((a for a in self.assignments 
                        if a.change == change and a.target_hash == target.commit_hash), None)
        if existing:
            return
        
        # Create assignment
        assignment = Assignment(change=change, target_hash=target.commit_hash)
        self.assignments.append(assignment)
        
        # Update UI
        self.update_targets_list()
        self.update_preview()
    
    def action_unassign(self) -> None:
        """Unassign selected change."""
        if self.focused_panel != "changes":
            return
        
        changes_list = self.query_one("#changes-list", ListView)
        if changes_list.index is None:
            return
        
        selected_item = changes_list.children[changes_list.index]
        if not isinstance(selected_item, ChangeItem):
            return
        
        change = selected_item.change
        
        # Remove assignments for this change
        self.assignments = [a for a in self.assignments if a.change != change]
        
        # Update UI
        self.update_targets_list()
        self.update_preview()
    
    def action_create_commits(self) -> None:
        """Create fixup commits from current assignments."""
        if not self.assignments:
            return
        
        # Group assignments by target
        by_target: Dict[str, List[Assignment]] = {}
        for assignment in self.assignments:
            if assignment.target_hash not in by_target:
                by_target[assignment.target_hash] = []
            by_target[assignment.target_hash].append(assignment)
        
        # Create modified targets with only assigned changes
        modified_targets = []
        for target_hash, target_assignments in by_target.items():
            # Find the original target
            original_target = next((t for t in self.targets if t.commit_hash == target_hash), None)
            if not original_target:
                continue
            
            # Create new target with only assigned changes
            assigned_changes = [a.change for a in target_assignments]
            modified_target = FixupTarget(
                commit_hash=original_target.commit_hash,
                commit_message=original_target.commit_message,
                author=original_target.author,
                changed_lines=assigned_changes,
                files=list(set(change.file_path for change in assigned_changes))
            )
            modified_targets.append(modified_target)
        
        # Create commits
        created_commits = []
        for target in modified_targets:
            commit_hash = self.creator.create_fixup_commit(target)
            if commit_hash:
                created_commits.append(commit_hash)
        
        # Exit after creating commits
        if created_commits:
            self.exit(message=f"✅ Created {len(created_commits)} fixup commits.")
        else:
            self.exit(message="❌ No fixup commits created.")
    
    def action_refresh(self) -> None:
        """Refresh data from repository."""
        self.assignments.clear()
        self.load_data()
        self.update_ui()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def run_gui(repo_path: str = ".") -> None:
    """Run the Textual-based GUI."""
    app = FixupGUI(repo_path=repo_path)
    app.run()