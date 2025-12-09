---
name: tui-dev
description: Text User Interface development best practices with Textual framework
version: 1.0
author: ReACTOR Team
allowed_tools:
  - read_file_content
  - write_file
  - modify_file
  - search_in_files
working_patterns:
  - "**/*.py"
  - "**/*.tcss"
  - "**/*.css"
  - "**/tests/**/*.py"
---

# TUI Development Skill (Textual Framework)

## Overview
Guidelines and best practices for building Text User Interfaces (TUIs) using the Textual Python framework. Textual is a modern TUI framework that brings web-like design concepts to terminal applications.

## Design Principles

### 1. Terminal-First Mindset
- Design for keyboard-only interaction from the start
- Embrace text-based constraints as features, not limitations
- Consider terminal size variations (minimum 80x24 recommended)
- Support both light and dark themes
- Design for remote access (SSH compatibility)

### 2. Progressive Enhancement
- Start with essential functionality
- Layer on additional features that enhance but don't require specific terminal capabilities
- Gracefully degrade on older terminals
- Test on multiple terminal emulators (iTerm, WezTerm, Windows Terminal, Kitty)

### 3. Minimalism and Clarity
- Less visual clutter improves readability in text environments
- Use whitespace effectively with padding and margins
- Limit color palettes to maintain consistency
- Focus on content hierarchy through layout, not decoration

### 4. Responsive Design
- Build fluid layouts that adapt to terminal resizing
- Use relative units (`fr`, percentages) over fixed sizes
- Test at various terminal dimensions
- Handle dynamic content gracefully

## File Organization

```
project/
├── app.py                 # Main application entry point
├── widgets/
│   ├── __init__.py
│   ├── custom_widget.py   # Custom widget implementations
│   └── components/        # Reusable components
├── screens/
│   ├── __init__.py
│   └── main_screen.py     # Screen definitions
├── styles/
│   ├── app.tcss          # Main application styles
│   └── components.tcss   # Component-specific styles
├── assets/               # Static assets if needed
├── tests/
│   ├── test_widgets.py
│   └── test_app.py
└── README.md
```

## Layout Best Practices

### Sketch First
Before coding, sketch your interface:
1. Draw rectangles for each screen region
2. Annotate with content types and scroll behavior
3. Identify which areas are fixed vs. responsive
4. Plan widget hierarchy

### CSS-Like Layouts
Textual uses CSS-inspired layout system:

```python
# Vertical layout (default)
Container {
    layout: vertical;
    height: 100%;
}

# Horizontal layout
.toolbar {
    layout: horizontal;
    height: 3;
    dock: top;
}

# Grid layout
.dashboard {
    layout: grid;
    grid-size: 3 2;  /* 3 columns, 2 rows */
    grid-gutter: 1;
}
```

### Docking Pattern
Use docking for fixed UI elements:

```python
class Header(Static):
    DEFAULT_CSS = """
    Header {
        height: 3;
        dock: top;
        background: $primary;
    }
    """

class Footer(Static):
    DEFAULT_CSS = """
    Footer {
        height: 1;
        dock: bottom;
    }
    """
```

### Fractional Units
Use `fr` units for flexible, responsive layouts:

```python
.main-content {
    width: 1fr;   /* Takes remaining space */
    height: 1fr;
}

.sidebar {
    width: 30;    /* Fixed 30 columns */
    height: 1fr;
}
```

## Widget Development

### Custom Widget Structure

```python
from textual.reactive import reactive
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static

class StatusWidget(Static):
    """A widget displaying application status."""
    
    # Reactive attributes for automatic updates
    status = reactive("idle")
    count = reactive(0)
    
    DEFAULT_CSS = """
    StatusWidget {
        height: 3;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def render(self) -> str:
        """Return renderable content."""
        return f"Status: {self.status} | Count: {self.count}"
    
    def watch_status(self, new_status: str) -> None:
        """Called when status changes."""
        # Perform side effects when status updates
        if new_status == "error":
            self.add_class("error")
        else:
            self.remove_class("error")
```

### Reactive Programming

#### Key Principles
1. **Reactive attributes**: Auto-refresh on change
2. **Watch methods**: Side effects on attribute changes
3. **Computed properties**: Derived values that update automatically
4. **Minimal explicit refreshes**: Let reactivity handle updates

```python
from textual.reactive import reactive, var
from time import monotonic

class Timer(Widget):
    # reactive() triggers full widget refresh
    elapsed = reactive(0.0)
    
    # var() for manual refresh control
    running = var(False)
    
    def on_mount(self) -> None:
        """Setup on widget mount."""
        self.start_time = monotonic()
        self.update_timer = self.set_interval(0.1, self.update_time)
    
    def update_time(self) -> None:
        """Update elapsed time."""
        if self.running:
            self.elapsed = monotonic() - self.start_time
    
    def watch_elapsed(self, elapsed: float) -> None:
        """Called when elapsed changes."""
        # Update display without manual refresh
        minutes, seconds = divmod(elapsed, 60)
        self.update(f"{minutes:02.0f}:{seconds:05.2f}")
    
    def watch_running(self, running: bool) -> None:
        """Handle start/stop state changes."""
        if running:
            self.start_time = monotonic()
            self.update_timer.resume()
        else:
            self.update_timer.pause()
```

### Computed Properties

```python
from textual.reactive import reactive

class ColorMixer(Widget):
    red = reactive(0)
    green = reactive(0)
    blue = reactive(0)
    
    def compute_color(self) -> str:
        """Computed property - auto-updates when dependencies change."""
        return f"rgb({self.red}, {self.green}, {self.blue})"
    
    def watch_color(self, color: str) -> None:
        """React to computed property changes."""
        self.styles.background = color
```

## Event Handling

### Event Handler Conventions

```python
from textual.app import App
from textual.events import Key, Click
from textual.widgets import Button

class MyApp(App):
    
    # Method 1: Underscore naming convention (Textual-specific)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles all button presses in the app."""
        self.notify(f"Button {event.button.id} pressed")
    
    # Method 2: Decorator pattern (explicit)
    @on(Button.Pressed, "#submit")
    def submit_form(self) -> None:
        """Handle specific button by ID."""
        self.process_form()
    
    # Keyboard events
    def on_key(self, event: Key) -> None:
        """Handle key presses."""
        if event.key == "q":
            self.exit()
        elif event.key == "ctrl+c":
            self.action_quit()
    
    # Mouse events
    def on_click(self, event: Click) -> None:
        """Handle mouse clicks."""
        self.log(f"Clicked at {event.x}, {event.y}")
```

### Actions Pattern

```python
class MyApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "toggle_theme", "Toggle Theme"),
        ("n", "new_item", "New Item"),
    ]
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_toggle_theme(self) -> None:
        """Toggle between dark and light theme."""
        self.dark = not self.dark
    
    def action_new_item(self) -> None:
        """Create a new item."""
        self.push_screen(CreateItemScreen())
```

## Styling (TCSS)

### CSS Variables and Reusability

```tcss
/* Define variables for consistency */
* {
    $primary: #007acc;
    $secondary: #2ecc71;
    $danger: #e74c3c;
    $background: #1e1e1e;
    $surface: #252526;
    $text: #d4d4d4;
    $border: #404040;
}

/* Use variables throughout */
Button {
    background: $primary;
    color: $text;
    border: solid $border;
}

Button:hover {
    background: $primary 120%;
}

Button.-danger {
    background: $danger;
}
```

### Scoped Styling

```python
class CustomWidget(Widget):
    # Scoped by default - only affects this widget and children
    DEFAULT_CSS = """
    CustomWidget {
        background: $surface;
        padding: 1;
    }
    
    CustomWidget > Static {
        color: $text;
    }
    """
    
    # Set to False for global styles
    SCOPED_CSS = False
```

### Responsive Styling Patterns

```tcss
/* Mobile-first approach */
.panel {
    layout: vertical;
    width: 100%;
}

/* Adjust for wider terminals */
.panel {
    layout: horizontal;
    width: 1fr;
    min-width: 80;
}

/* Grid that adapts */
.grid-container {
    layout: grid;
    grid-size: 2;  /* 2 columns on small */
    grid-gutter: 1;
}

/* Use CSS classes for states */
.panel.-collapsed {
    height: 3;
}

.panel.-expanded {
    height: auto;
}
```

## Accessibility & Keyboard Navigation

### Focus Management

```python
class AccessibleWidget(Widget):
    
    # Enable focus
    can_focus = True
    
    def on_focus(self) -> None:
        """Handle focus received."""
        self.add_class("focused")
    
    def on_blur(self) -> None:
        """Handle focus lost."""
        self.remove_class("focused")
```

### Focus Styling

```tcss
/* Always provide visible focus indicators */
Input:focus {
    border: double $primary;
}

Button:focus {
    background: $primary 120%;
    border: solid $secondary;
}

/* Ensure 3:1 contrast ratio minimum */
*:focus {
    outline: solid $accent;
    outline-offset: 1;
}
```

### Logical Tab Order

```python
class FormScreen(Screen):
    def compose(self) -> ComposeResult:
        # Widgets yielded in order become tab order
        yield Input(placeholder="Name", id="name")
        yield Input(placeholder="Email", id="email")
        yield Button("Submit", id="submit")
        yield Button("Cancel", id="cancel")
    
    def on_mount(self) -> None:
        # Set initial focus
        self.query_one("#name").focus()
```

### Keyboard Shortcuts

```python
class MyApp(App):
    BINDINGS = [
        # Key, action, description
        ("q", "quit", "Quit"),
        ("?", "help", "Show Help"),
        ("ctrl+n", "new_item", "New Item"),
        ("escape", "cancel", "Cancel"),
    ]
    
    # Provide visual shortcuts guide
    def action_help(self) -> None:
        """Show keyboard shortcuts."""
        self.push_screen(ShortcutsScreen())
```

## Performance Best Practices

### Avoid Expensive Operations in Compute Methods

```python
class DataWidget(Widget):
    data = reactive([])
    
    # BAD: Expensive operation in compute
    def compute_summary(self) -> str:
        # Don't do heavy processing here
        return expensive_calculation(self.data)
    
    # GOOD: Cache results, update on data change
    def watch_data(self, data: list) -> None:
        self._summary = self.calculate_summary(data)
    
    def render(self) -> str:
        return self._summary
```

### Use Workers for Async Operations

```python
from textual.worker import work

class DataApp(App):
    
    @work(exclusive=True)  # Only one instance runs
    async def fetch_data(self) -> None:
        """Fetch data without blocking UI."""
        self.loading = True
        try:
            data = await api.get_data()
            self.process_data(data)
        finally:
            self.loading = False
    
    def on_mount(self) -> None:
        self.fetch_data()
```

### Efficient Widget Updates

```python
# BAD: Recreating widgets
def update_list(self, items):
    container = self.query_one("#list")
    container.remove_children()
    for item in items:
        container.mount(ItemWidget(item))

# GOOD: Update existing widgets
def update_list(self, items):
    container = self.query_one("#list")
    widgets = container.query(ItemWidget)
    
    for widget, item in zip(widgets, items):
        widget.data = item
    
    # Only mount if needed
    if len(items) > len(widgets):
        for item in items[len(widgets):]:
            container.mount(ItemWidget(item))
```

## Testing

### Unit Testing Widgets

```python
import pytest
from textual.widgets import Button
from myapp.widgets import StatusWidget

def test_status_widget_initial_state():
    """Test widget initializes correctly."""
    widget = StatusWidget()
    assert widget.status == "idle"
    assert widget.count == 0

def test_status_widget_reactive_update():
    """Test reactive attribute updates."""
    widget = StatusWidget()
    widget.status = "active"
    assert widget.status == "active"
    assert "active" in widget.render()
```

### Integration Testing

```python
from textual.pilot import Pilot

async def test_app_interaction():
    """Test full app interaction."""
    app = MyApp()
    async with app.run_test() as pilot:
        # Wait for app to be ready
        await pilot.pause()
        
        # Simulate key press
        await pilot.press("n")
        
        # Check screen changed
        assert isinstance(app.screen, NewItemScreen)
        
        # Type in input
        await pilot.click("#name")
        await pilot.press("T", "e", "s", "t")
        
        # Verify input value
        input_widget = app.query_one("#name")
        assert input_widget.value == "Test"
```

## Development Workflow

### Live Editing

```bash
# Run with live CSS editing
textual run --dev app.py

# Console for debugging
textual console

# In another terminal
python app.py
```

### Debugging Tips

1. **Use logging**: `from textual import log`
   ```python
   from textual import log
   
   def my_function(self):
       log("Debug message")
       log(self.data)
   ```

2. **Devtools**: Press `Ctrl+\` to toggle devtools panel

3. **Console**: Use `textual console` in separate terminal for real-time logs

### Code Quality

```python
# Type hints for better IDE support
from textual.app import ComposeResult
from textual.widgets import Button, Input

def compose(self) -> ComposeResult:
    """Compose widget layout."""
    yield Button("Click Me", id="btn")
    yield Input(placeholder="Enter text")

# Docstrings for clarity
class DataTable(Widget):
    """A custom data table widget.
    
    Args:
        data: List of dictionaries containing row data
        headers: Column headers
        sortable: Enable column sorting
    """
```

## Common Patterns

### Modal Dialogs

```python
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from textual.containers import Vertical

class ConfirmDialog(ModalScreen):
    """A confirmation dialog."""
    
    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    
    Vertical {
        width: 40;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    """
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.message)
            yield Button("Confirm", variant="primary", id="confirm")
            yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

# Usage
async def confirm_action(self):
    result = await self.push_screen_wait(
        ConfirmDialog("Are you sure?")
    )
    if result:
        self.perform_action()
```

### Loading States

```python
class DataWidget(Widget):
    loading = reactive(False)
    
    def watch_loading(self, loading: bool) -> None:
        """Show/hide loading indicator."""
        if loading:
            self.loading_indicator = self.mount(LoadingIndicator())
        else:
            if hasattr(self, 'loading_indicator'):
                self.loading_indicator.remove()
    
    @work
    async def load_data(self):
        self.loading = True
        try:
            data = await fetch_data()
            self.data = data
        finally:
            self.loading = False
```

### Command Palette

```python
from textual.command import Provider, Hit

class MyCommandProvider(Provider):
    """Custom command provider."""
    
    async def search(self, query: str):
        """Search for commands matching query."""
        commands = [
            ("new", "Create New Item"),
            ("open", "Open File"),
            ("save", "Save Changes"),
        ]
        
        matcher = self.matcher(query)
        
        for cmd_id, cmd_name in commands:
            score = matcher.match(cmd_name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(cmd_name),
                    lambda c=cmd_id: self.execute_command(c)
                )
```

## Best Practices Summary

### DO
✅ Use reactive attributes for automatic updates
✅ Separate styling in TCSS files
✅ Provide clear focus indicators
✅ Test on multiple terminal emulators
✅ Use workers for async operations
✅ Implement proper keyboard navigation
✅ Cache expensive computations
✅ Use semantic widget names
✅ Leverage CSS variables for consistency
✅ Document widget APIs with docstrings

### DON'T
❌ Do heavy processing in compute methods
❌ Manually call refresh() unless necessary
❌ Use fixed pixel sizes for layouts
❌ Forget to handle keyboard-only users
❌ Nest widgets too deeply (performance impact)
❌ Ignore terminal resize events
❌ Use positive tabindex values
❌ Rely solely on color for information
❌ Block the UI thread with sync operations
❌ Override CSS with too many inline styles

## Resources

- Official Documentation: https://textual.textualize.io
- Widget Gallery: https://textual.textualize.io/widget_gallery/
- Discord Community: https://discord.gg/Enf6Z3qhVr
- GitHub Repository: https://github.com/Textualize/textual
- Real Python Tutorial: https://realpython.com/python-textual/