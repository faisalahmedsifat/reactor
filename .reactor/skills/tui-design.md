---
name: tui-dev
description: Text User Interface development with focus on beautiful, modern, sleek and minimalistic design using Textual framework
version: 2.0
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
Guidelines and best practices for building beautiful, modern, sleek and minimalistic Text User Interfaces (TUIs) using the Textual Python framework. This guide emphasizes contemporary design aesthetics that make terminal applications feel premium and polished.

## Modern Design Philosophy

### The "Terminal-Native Luxury" Approach
Modern TUIs should feel like premium desktop applications while embracing terminal constraints. Think of apps like `lazygit`, `k9s`, or `btop` - they prove terminals can be gorgeous.

**Core Aesthetic Principles:**
- **Minimalism with Purpose**: Every element earns its place
- **Breathing Room**: Generous whitespace makes UIs feel premium
- **Visual Hierarchy**: Guide the eye through size, color, and spacing
- **Subtle Elegance**: Refinement over decoration
- **Information Density Balance**: Dense enough to be useful, spacious enough to be comfortable

### Modern Color Psychology

```tcss
/* Modern Dark Theme - Default (Sophisticated) */
* {
    /* Primary palette - Deep blues with high contrast */
    $primary: #60A5FA;        /* Bright blue - primary actions */
    $primary-dark: #3B82F6;   /* Deeper blue - hover states */
    $primary-muted: #1E3A5F;  /* Subtle blue - backgrounds */
    
    /* Semantic colors - Clear but not garish */
    $success: #34D399;        /* Mint green - success states */
    $warning: #FBBF24;        /* Warm amber - warnings */
    $error: #F87171;          /* Soft red - errors */
    $info: #60A5FA;           /* Blue - information */
    
    /* Neutral palette - Rich blacks, not pure */
    $background: #0F172A;     /* Deep slate - main background */
    $surface: #1E293B;        /* Elevated slate - cards/panels */
    $surface-light: #334155;  /* Lighter slate - hover */
    
    /* Text hierarchy - Subtle variations */
    $text-primary: #F1F5F9;   /* Almost white - headings */
    $text-secondary: #CBD5E1; /* Light gray - body text */
    $text-muted: #64748B;     /* Medium gray - labels */
    $text-disabled: #475569;  /* Dark gray - disabled */
    
    /* Borders and dividers - Subtle separation */
    $border: #334155;         /* Medium slate */
    $border-subtle: #1E293B;  /* Barely visible */
    $border-focus: #60A5FA;   /* Bright on focus */
    
    /* Accent gradients for special elements */
    $accent-gradient: linear-gradient(135deg, #60A5FA, #A78BFA);
    
    /* Shadows (using background tint) */
    $shadow: #0A0F1A 60%;
}

/* Modern Light Theme - Optional (Clean) */
*.light-mode {
    $primary: #2563EB;
    $primary-dark: #1D4ED8;
    $primary-muted: #DBEAFE;
    
    $success: #10B981;
    $warning: #F59E0B;
    $error: #EF4444;
    
    $background: #FFFFFF;
    $surface: #F8FAFC;
    $surface-light: #F1F5F9;
    
    $text-primary: #0F172A;
    $text-secondary: #334155;
    $text-muted: #64748B;
    
    $border: #E2E8F0;
    $border-subtle: #F1F5F9;
}
```

## Visual Design Patterns

### 1. Modern Card-Based Layouts

```tcss
/* Elevated card with subtle shadow effect */
.card {
    background: $surface;
    border: none;  /* Modern UIs minimize borders */
    border-radius: 2;  /* Subtle rounding (if terminal supports) */
    padding: 2 3;
    margin: 1;
    
    /* Simulate shadow with darker background behind */
    box-sizing: border-box;
}

.card:hover {
    background: $surface-light;
    transition: background 200ms;
}

/* Card with border accent - minimalist highlight */
.card-accent {
    border-left: solid $primary;
    border-right: none;
    border-top: none;
    border-bottom: none;
}

/* Glassmorphism effect (subtle transparency) */
.glass-card {
    background: $surface 80%;
    border: solid $border-subtle;
}
```

### 2. Sophisticated Typography Hierarchy

```tcss
/* Display text - Hero headings */
.display {
    text-style: bold;
    color: $text-primary;
    padding-bottom: 1;
}

/* Heading levels with clear hierarchy */
.h1 {
    text-style: bold;
    color: $text-primary;
    padding: 1 0;
}

.h2 {
    text-style: bold;
    color: $text-secondary;
    padding: 1 0 0 0;
}

.h3 {
    color: $text-secondary;
    text-style: underline;
}

/* Body text - optimal readability */
.body {
    color: $text-secondary;
    line-height: 1.5;  /* If supported */
}

/* Labels and metadata - subtle */
.label {
    color: $text-muted;
    text-style: none;
}

/* Monospace for data - clear distinction */
.code, .data {
    text-style: none;
    color: $primary;
    background: $primary-muted;
    padding: 0 1;
}

/* Emphasis without being loud */
.emphasis {
    color: $primary;
    text-style: none;  /* Color is enough */
}
```

### 3. Modern Spacing System

Use a consistent spacing scale (based on terminal rows/cols):

```tcss
/* Spacing scale: 0, 1, 2, 3, 4, 6, 8, 12 */

/* Compact spacing for dense info */
.tight {
    padding: 0;
    margin: 0;
}

/* Standard spacing - most common */
.normal {
    padding: 1 2;
    margin: 1;
}

/* Comfortable spacing - premium feel */
.comfortable {
    padding: 2 3;
    margin: 2;
}

/* Generous spacing - hero sections */
.spacious {
    padding: 3 4;
    margin: 3;
}

/* Section separators - clear visual breaks */
.section {
    padding-top: 3;
    margin-top: 2;
    border-top: solid $border-subtle;
}
```

### 4. Modern Component Styles

```tcss
/* Buttons - Clear hierarchy */
Button {
    width: auto;
    min-width: 12;
    height: 3;
    padding: 0 3;
    background: transparent;
    border: solid $border;
    color: $text-secondary;
}

Button:hover {
    background: $surface-light;
    border: solid $border-focus;
    color: $text-primary;
}

Button:focus {
    border: double $primary;
    text-style: bold;
}

/* Primary button - clear call to action */
Button.-primary {
    background: $primary;
    border: none;
    color: $background;
    text-style: bold;
}

Button.-primary:hover {
    background: $primary-dark;
}

/* Ghost button - subtle presence */
Button.-ghost {
    background: transparent;
    border: none;
    color: $text-muted;
}

Button.-ghost:hover {
    color: $text-primary;
    background: $surface;
}

/* Input fields - clean and modern */
Input {
    border: solid $border;
    background: $background;
    color: $text-primary;
    padding: 0 2;
}

Input:focus {
    border: solid $primary;
    background: $surface;
}

Input.-error {
    border: solid $error;
}

/* Select/Dropdown - consistent with inputs */
Select {
    border: solid $border;
    background: $surface;
    padding: 0 2;
}

Select:focus {
    border: solid $primary;
}

/* Modern list items - clean separation */
ListItem {
    padding: 1 2;
    background: transparent;
}

ListItem:hover {
    background: $surface;
}

.list-item-selected {
    background: $primary-muted;
    border-left: solid $primary;
    color: $primary;
}

/* Progress indicators - sleek */
ProgressBar {
    height: 1;
    background: $surface;
}

ProgressBar > .bar {
    background: $primary;
}

/* Modern tabs - minimal and clear */
Tabs {
    background: transparent;
    border-bottom: solid $border;
}

Tab {
    background: transparent;
    border: none;
    color: $text-muted;
    padding: 1 2;
}

Tab:hover {
    color: $text-secondary;
}

Tab.-active {
    color: $primary;
    border-bottom: solid $primary;
    text-style: bold;
}
```

### 5. Sophisticated Layouts

```python
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, Header, Footer

class ModernLayout(Container):
    """A modern, card-based layout with sophisticated spacing."""
    
    DEFAULT_CSS = """
    ModernLayout {
        background: $background;
        padding: 2;
    }
    
    .hero {
        height: auto;
        padding: 4 3;
        background: $surface;
        margin-bottom: 3;
    }
    
    .hero-title {
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }
    
    .hero-subtitle {
        color: $text-muted;
    }
    
    .content-grid {
        layout: grid;
        grid-size: 3;
        grid-gutter: 2;
        margin-top: 2;
    }
    
    .stat-card {
        background: $surface;
        padding: 2 3;
        height: auto;
        border-left: solid $primary;
    }
    
    .stat-value {
        text-style: bold;
        color: $primary;
        padding: 1 0;
    }
    
    .stat-label {
        color: $text-muted;
    }
    """
    
    def compose(self) -> ComposeResult:
        # Hero section with generous spacing
        with Container(classes="hero"):
            yield Static("Dashboard", classes="hero-title")
            yield Static("Overview of your data", classes="hero-subtitle")
        
        # Grid of stat cards
        with Grid(classes="content-grid"):
            yield self._create_stat_card("1,234", "Total Users")
            yield self._create_stat_card("56", "Active Now")
            yield self._create_stat_card("89%", "Success Rate")
    
    def _create_stat_card(self, value: str, label: str) -> Container:
        card = Container(classes="stat-card")
        card.compose_add_child(Static(value, classes="stat-value"))
        card.compose_add_child(Static(label, classes="stat-label"))
        return card
```

### 6. Modern Header/Footer Design

```python
class ModernHeader(Static):
    """A sleek, minimal header."""
    
    DEFAULT_CSS = """
    ModernHeader {
        dock: top;
        height: 3;
        background: $surface;
        color: $text-primary;
        padding: 0 3;
        border-bottom: solid $border-subtle;
    }
    
    .header-content {
        layout: horizontal;
        height: 100%;
        align: center middle;
    }
    
    .header-title {
        text-style: bold;
        color: $primary;
        width: 1fr;
    }
    
    .header-status {
        color: $text-muted;
        width: auto;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="header-content"):
            yield Static("MyApp", classes="header-title")
            yield Static("● Connected", classes="header-status")

class ModernFooter(Static):
    """A clean, informative footer."""
    
    DEFAULT_CSS = """
    ModernFooter {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 2;
    }
    
    .footer-content {
        layout: horizontal;
    }
    
    .shortcut {
        color: $primary;
        padding-right: 1;
    }
    
    .shortcut-label {
        color: $text-muted;
        padding-right: 3;
    }
    """
    
    def render(self) -> str:
        return "[blue]?[/] Help  [blue]q[/] Quit  [blue]⌘k[/] Commands"
```

## Modern UI Patterns

### Pattern 1: Dashboard with Key Metrics

```python
class DashboardScreen(Screen):
    """Modern dashboard with card-based metrics."""
    
    DEFAULT_CSS = """
    DashboardScreen {
        background: $background;
    }
    
    .dashboard-container {
        padding: 3;
    }
    
    .metric-grid {
        layout: grid;
        grid-size: 4;
        grid-gutter: 2 3;
        margin: 2 0;
    }
    
    .metric-card {
        background: $surface;
        padding: 3;
        height: 8;
        border-left: solid $primary;
    }
    
    .metric-card.-warning {
        border-left: solid $warning;
    }
    
    .metric-card.-error {
        border-left: solid $error;
    }
    
    .metric-label {
        color: $text-muted;
        padding-bottom: 1;
    }
    
    .metric-value {
        text-style: bold;
        color: $text-primary;
        padding: 1 0;
    }
    
    .metric-change {
        color: $success;
    }
    
    .metric-change.-negative {
        color: $error;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(classes="dashboard-container"):
            yield Static("Overview", classes="h1")
            with Grid(classes="metric-grid"):
                yield self._metric_card("Total Revenue", "$45,231", "+12.5%")
                yield self._metric_card("Active Users", "2,345", "+5.2%")
                yield self._metric_card("Conversion", "3.2%", "-0.3%", negative=True)
                yield self._metric_card("Avg. Session", "8m 32s", "+1.2%")
    
    def _metric_card(self, label: str, value: str, change: str, negative: bool = False) -> Container:
        card = Container(classes="metric-card")
        card.compose_add_child(Static(label, classes="metric-label"))
        card.compose_add_child(Static(value, classes="metric-value"))
        change_class = "metric-change" + (" -negative" if negative else "")
        card.compose_add_child(Static(change, classes=change_class))
        return card
```

### Pattern 2: Modern Data Table

```python
from textual.widgets import DataTable

class ModernDataTable(DataTable):
    """A sleek, readable data table."""
    
    DEFAULT_CSS = """
    ModernDataTable {
        background: $surface;
        border: none;
    }
    
    /* Header row - clear hierarchy */
    ModernDataTable > .datatable--header {
        background: $background;
        color: $text-muted;
        text-style: bold;
        height: 2;
        border-bottom: solid $border;
    }
    
    /* Data rows - comfortable spacing */
    ModernDataTable > .datatable--row {
        height: 2;
        padding: 0 2;
    }
    
    ModernDataTable > .datatable--row:hover {
        background: $surface-light;
    }
    
    /* Selected row - clear but subtle */
    ModernDataTable > .datatable--row-selected {
        background: $primary-muted;
        color: $primary;
    }
    
    /* Alternating rows for readability */
    ModernDataTable > .datatable--row:nth-child(even) {
        background: $background;
    }
    
    /* Column dividers - very subtle */
    ModernDataTable .datatable--cell {
        border-right: solid $border-subtle;
    }
    """
```

### Pattern 3: Command Palette (Modern)

```python
class ModernCommandPalette(Screen):
    """Sleek command palette like in modern editors."""
    
    DEFAULT_CSS = """
    ModernCommandPalette {
        align: center top;
        background: $background 60%;  /* Dim backdrop */
    }
    
    .palette-container {
        width: 70;
        height: auto;
        margin-top: 5;
        background: $surface;
        border: solid $primary;
        border-radius: 2;
        padding: 2;
    }
    
    .palette-input {
        border: none;
        background: $background;
        padding: 1 2;
        margin-bottom: 2;
    }
    
    .palette-results {
        height: auto;
        max-height: 20;
    }
    
    .palette-item {
        padding: 1 2;
        background: transparent;
    }
    
    .palette-item:hover {
        background: $primary-muted;
        color: $primary;
    }
    
    .palette-item-icon {
        color: $text-muted;
        padding-right: 2;
    }
    
    .palette-item-shortcut {
        color: $text-muted;
        text-align: right;
    }
    """
```

### Pattern 4: Sidebar Navigation

```python
class ModernSidebar(Container):
    """Modern sidebar with clear active states."""
    
    DEFAULT_CSS = """
    ModernSidebar {
        width: 20;
        background: $surface;
        border-right: solid $border-subtle;
        padding: 2 0;
    }
    
    .nav-item {
        padding: 1 3;
        color: $text-secondary;
        background: transparent;
    }
    
    .nav-item:hover {
        background: $background;
        color: $text-primary;
    }
    
    .nav-item.-active {
        background: $primary-muted;
        color: $primary;
        border-left: solid $primary;
        text-style: bold;
    }
    
    .nav-icon {
        padding-right: 2;
    }
    
    .nav-section {
        color: $text-muted;
        padding: 2 3 1 3;
        text-style: bold;
    }
    """
```

### Pattern 5: Modern Modal/Dialog

```python
from textual.screen import ModalScreen

class ModernModal(ModalScreen):
    """Beautiful modal dialog with backdrop blur effect."""
    
    DEFAULT_CSS = """
    ModernModal {
        align: center middle;
        background: $background 80%;  /* Semi-transparent backdrop */
    }
    
    .modal-container {
        width: 60;
        height: auto;
        background: $surface;
        border: solid $border;
        border-radius: 2;
        padding: 0;
    }
    
    .modal-header {
        background: $background;
        padding: 2 3;
        border-bottom: solid $border-subtle;
    }
    
    .modal-title {
        text-style: bold;
        color: $text-primary;
    }
    
    .modal-body {
        padding: 3;
        color: $text-secondary;
    }
    
    .modal-footer {
        padding: 2 3;
        border-top: solid $border-subtle;
        layout: horizontal;
        align: right middle;
    }
    
    .modal-footer Button {
        margin-left: 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(classes="modal-container"):
            with Container(classes="modal-header"):
                yield Static("Confirm Action", classes="modal-title")
            with Container(classes="modal-body"):
                yield Static("Are you sure you want to proceed?")
            with Container(classes="modal-footer"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Confirm", variant="primary", id="confirm")
```

## Animation and Transitions

While terminal animations are limited, subtle effects improve perceived performance:

```tcss
/* Smooth hover transitions */
Button {
    transition: background 150ms, color 150ms;
}

Button:hover {
    background: $surface-light;
}

/* Loading state animations */
.loading {
    text-style: blink;  /* Use sparingly */
}

/* Fade-in for new content */
.fade-in {
    opacity: 0;
    transition: opacity 300ms;
}

.fade-in.-visible {
    opacity: 100%;
}
```

## Accessibility with Style

Modern design shouldn't compromise accessibility:

```tcss
/* High contrast mode support */
*.high-contrast {
    $border: #FFFFFF;
    $text-primary: #FFFFFF;
    $background: #000000;
}

/* Focus indicators must be visible */
*:focus {
    outline: solid $primary;
    outline-offset: 1;
}

/* Ensure text contrast ratios */
.low-contrast-text {
    color: $text-muted;  /* At least 4.5:1 ratio */
}

/* Alternative to color-only indicators */
.status-success::before {
    content: "✓ ";
}

.status-error::before {
    content: "✗ ";
}
```

## Design System Guidelines

### Consistency Checklist

**Spacing:**
- [ ] Using consistent spacing scale (0, 1, 2, 3, 4, 6, 8)
- [ ] Padding and margins follow the scale
- [ ] Visual rhythm is maintained

**Typography:**
- [ ] Clear hierarchy (3-4 text sizes maximum)
- [ ] Consistent font weights
- [ ] Proper line height for readability

**Color:**
- [ ] Limited palette (8-12 colors max)
- [ ] Semantic colors used correctly
- [ ] Sufficient contrast (4.5:1 minimum)

**Components:**
- [ ] Consistent button styles
- [ ] Uniform input field appearance
- [ ] Similar spacing in similar components

**Layout:**
- [ ] Consistent card styling
- [ ] Grid alignment maintained
- [ ] Proper visual hierarchy

## Before/After Examples

### ❌ Dated Design

```tcss
/* Old style - cluttered and dated */
Container {
    background: blue;
    border: solid yellow;
    padding: 0;
}

Button {
    background: green;
    color: white;
    text-style: bold underline;
}

.title {
    color: red;
    text-style: bold italic underline;
}
```

### ✅ Modern Design

```tcss
/* Modern style - clean and sophisticated */
Container {
    background: $surface;
    border: none;
    padding: 2 3;
}

Button {
    background: transparent;
    border: solid $border;
    color: $text-secondary;
    transition: all 150ms;
}

Button:hover {
    background: $surface-light;
    border: solid $primary;
    color: $text-primary;
}

.title {
    color: $text-primary;
    text-style: bold;
    padding-bottom: 2;
}
```

## Modern Design Recipes

### Recipe 1: Status Badge

```python
class StatusBadge(Static):
    """Modern status indicator."""
    
    DEFAULT_CSS = """
    StatusBadge {
        width: auto;
        height: 1;
        padding: 0 2;
        background: $surface-light;
        color: $text-muted;
        border-radius: 1;
    }
    
    StatusBadge.-success {
        background: $success 30%;
        color: $success;
    }
    
    StatusBadge.-warning {
        background: $warning 30%;
        color: $warning;
    }
    
    StatusBadge.-error {
        background: $error 30%;
        color: $error;
    }
    """
    
    def __init__(self, status: str, text: str):
        super().__init__(f"● {text}")
        self.add_class(f"-{status}")
```

### Recipe 2: Loading Skeleton

```python
class LoadingSkeleton(Static):
    """Skeleton loader for async content."""
    
    DEFAULT_CSS = """
    LoadingSkeleton {
        height: 3;
        background: $surface;
        color: $surface-light;
        text-style: blink;
    }
    
    .skeleton-line {
        height: 1;
        background: $surface-light;
        margin: 1 0;
    }
    """
    
    def render(self) -> str:
        return "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
```

### Recipe 3: Empty State

```python
class EmptyState(Container):
    """Beautiful empty state placeholder."""
    
    DEFAULT_CSS = """
    EmptyState {
        align: center middle;
        padding: 8;
    }
    
    .empty-icon {
        color: $text-muted;
        text-align: center;
        padding-bottom: 2;
    }
    
    .empty-title {
        color: $text-secondary;
        text-style: bold;
        text-align: center;
        padding-bottom: 1;
    }
    
    .empty-description {
        color: $text-muted;
        text-align: center;
        max-width: 40;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("📭", classes="empty-icon")
        yield Static("No items yet", classes="empty-title")
        yield Static("Get started by creating your first item", classes="empty-description")
```

## Quality Standards

### Visual Quality Checklist

**Before shipping, verify:**

1. **Spacing & Layout**
   - [ ] Consistent padding across similar components
   - [ ] No cramped sections (minimum 1 unit padding)
   - [ ] Visual breathing room around important elements
   - [ ] Grid alignment is perfect

2. **Typography**
   - [ ] Clear hierarchy (can you tell what's important?)
   - [ ] No more than 3 font weights used
   - [ ] Text is easily readable
   - [ ] No unnecessary text styles (bold + italic + underline = bad)

3. **Color & Contrast**
   - [ ] Limited color palette
   - [ ] Semantic colors used appropriately
   - [ ] Text readable on all backgrounds
   - [ ] Focus states are obvious

4. **Interaction States**
   - [ ] Hover states exist and are visible
   - [ ] Focus states are clear
   - [ ] Active/selected states are obvious
   - [ ] Disabled states look disabled

5. **Consistency**
   - [ ] Similar components look similar
   - [ ] Button styles are consistent
   - [ ] Card styles match throughout
   - [ ] Spacing follows system

## Resources for Inspiration

**Modern Terminal Apps to Study:**
- `lazygit` - Beautiful git interface
- `k9s` - Kubernetes TUI
- `btop` - System monitor
- `spotify-tui` - Music player
- `gitui` - Git interface
- `bottom` - System monitor

**Design Systems to Reference:**
- Tailwind CSS color system
- Material Design spacing
- GitHub Primer design system
- Carbon Design System

**Key Resources:**
- Textual Documentation: https://textual.textualize.io
- Widget Gallery: https://textual.textualize.io/widget_gallery/
- Discord Community: https://discord.gg/Enf6Z3qhVr
- Design Inspiration: https://github.com/rothgar/awesome-tuis

## Summary: Building Beautiful TUIs

**The Golden Rules:**
1. **Less is More**: Remove until it hurts, then add back one element
2. **Whitespace is Your Friend**: Give elements room to breathe
3. **Consistency Beats Perfection**: A consistent mediocre design beats inconsistent great design
4. **Hierarchy Guides the Eye**: Make important things obvious
5. **Subtle > Flashy**: Refinement over decoration
6. **Test in Real Terminals**: What looks good in one terminal might not in another

**Start Here:**
1. Define your color system (use the modern palette above)
2. Establish spacing scale (stick to 0, 1, 2, 3, 4, 6, 8)
3. Create 3-4 text styles (display, heading, body, label)
4. Design your primary components (button, input, card)
5. Build a single screen to perfection
6. Use it as a template for others

**Remember:** Modern terminal design is about making something feel premium and polished while embracing constraints. Think "clean and purposeful" not "sparse and empty."