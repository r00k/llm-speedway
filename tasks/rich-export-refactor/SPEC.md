# Console Export Refactoring Task

Refactor the `rich` Python library's Console class to extract its export functionality into a separate, cohesive module.

## Background

The `rich` library's `Console` class in `rich/console.py` has grown to over 2,600 lines and handles too many responsibilities. The export functionality (generating text, HTML, and SVG output from recorded console content) is a self-contained subsystem that should be extracted into its own module.

## Requirements

### 1. Identify and Extract Export Functionality

Analyze `rich/console.py` to identify all methods related to exporting recorded console output. Extract this functionality into a new module `rich/console_export.py`.

The extracted module should:
- Handle all export formats (text, HTML, SVG)
- Include both the export functions and their corresponding save-to-file functions
- Be a cohesive unit focused on the single responsibility of export/serialization

### 2. Design Decisions

You must make the following architectural decisions:

1. **Function signatures**: Decide how extracted functions receive the data they need (console instance, record buffer, etc.)
2. **Module structure**: Organize the new module appropriately  
3. **Internal helpers**: Any helper functions nested inside methods should be extracted appropriately

### 3. Maintain All Existing Behavior

- All existing tests must pass without modification
- The public API of the `Console` class must remain unchanged
- Export functionality must work identically

### 4. Handle Dependencies Correctly

The export methods access several Console internals:
- `_record_buffer` - the recorded segments
- `_record_buffer_lock` - thread safety lock  
- `record` - boolean flag
- `width` - console width

Design your extraction to handle these dependencies cleanly. Consider whether functions should receive the console instance or just the specific data they need.

## Constraints

1. **No new external dependencies**
2. **All existing tests must pass** - run `pytest tests/test_console.py -v`
3. **No import cycles** - `from rich.console import Console` must work
4. **Preserve thread safety** - exports use locking that must be maintained

## Verification

Your refactoring will be verified by:

1. **Structural checks**:
   - `rich/console_export.py` exists
   - Export functions are defined in the new module
   - `console.py` imports from `console_export`
   - No import cycles

2. **Behavioral checks**:
   - All existing tests pass: `pytest tests/test_console.py -v`

## Hints

- Study how other modules in Rich are structured (e.g., `_log_render.py`, `_export_format.py`)
- The `export_svg` method has nested helper functions - these need careful handling
- Consider the tradeoff between passing the Console instance vs. passing specific attributes

## Success Criteria

1. ✅ `rich/console_export.py` exists with export functionality
2. ✅ `Console` methods delegate to the new module
3. ✅ `python -c "from rich.console import Console"` works (no import cycles)
4. ✅ `pytest tests/test_console.py` passes
