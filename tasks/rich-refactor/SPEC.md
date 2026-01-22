# Rich Library Refactoring Task

Refactor the `rich` Python library by extracting text sizing operations from `rich/text.py` into a new `rich/text_operations.py` module.

## Background

The `rich` library is a popular Python library for rich text and beautiful formatting in the terminal. The `Text` class in `rich/text.py` has grown to over 1300 lines and contains multiple responsibilities.

Your task is to extract text sizing/fitting operations into a separate module while preserving all existing behavior.

## Requirements

### 1. Create `rich/text_operations.py`

Create a new module containing these functions extracted from the `Text` class:

| Function | Original Method | Description |
|----------|-----------------|-------------|
| `truncate(text, max_width, *, overflow=None, pad=False)` | `Text.truncate()` | Truncate text if longer than max_width |
| `pad(text, count, character=" ")` | `Text.pad()` | Pad left and right with characters |
| `pad_left(text, count, character=" ")` | `Text.pad_left()` | Pad the left side |
| `pad_right(text, count, character=" ")` | `Text.pad_right()` | Pad the right side |
| `align(text, align_method, width, character=" ")` | `Text.align()` | Align text to a given width |
| `set_length(text, new_length)` | `Text.set_length()` | Set text length via padding or cropping |

Each function should:
- Take a `Text` instance as its first argument
- Mutate the `Text` instance in place (matching original behavior)
- Preserve exact behavior including edge cases

### 2. Update `Text` class methods

Convert the original methods to thin wrappers that delegate to the new functions:

```python
# Example pattern (in text.py)
from .text_operations import truncate as _truncate

class Text:
    def truncate(self, max_width, *, overflow=None, pad=False):
        """Truncate text if it is longer that a given width.
        
        [Keep original docstring]
        """
        _truncate(self, max_width, overflow=overflow, pad=pad)
```

### 3. Avoid Import Cycles

Use the `TYPE_CHECKING` pattern to avoid circular imports:

```python
# In text_operations.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .text import Text

def truncate(text: "Text", max_width: int, ...) -> None:
    ...
```

### 4. All Tests Must Pass

The existing test suite must continue to pass without modification:

```bash
pytest tests/test_text.py
```

## Constraints

1. **Behavior Preservation**: The refactoring must not change any observable behavior
2. **No New Dependencies**: Do not add any new external dependencies
3. **Preserve Internal Invariants**: 
   - `_length` must be kept in sync with actual text length
   - Span trimming/shifting must work correctly
   - Use existing helpers like `cell_len`, `set_cell_size`
4. **Keep Public API Stable**: All existing `Text` methods must remain callable with the same signatures

## Verification

Your refactoring will be verified by:

1. **Structural checks**:
   - `rich/text_operations.py` exists
   - Required functions are defined in the new module
   - `text.py` imports from `text_operations`
   - No import cycles (can import `rich.text` without error)

2. **Behavioral checks**:
   - All existing tests pass
   - New structural verification tests pass

## Hints

- Look at how `_wrap.py` is structured for a similar extraction pattern
- The `Span` class has helper methods like `move()` and `right_crop()` - use these instead of constructing new `Span` objects to avoid needing to import `Span`
- Be careful with methods that modify `self.plain` - this triggers the `plain` setter which has side effects
- `truncate()` has subtle ordering: it computes `length` before potentially modifying `self.plain`

## Files to Modify

- `rich/text.py` - Update methods to be wrappers
- `rich/text_operations.py` - Create this new file with extracted functions

## Success Criteria

1. ✅ `rich/text_operations.py` exists with all 6 required functions
2. ✅ `Text` methods delegate to `text_operations` functions  
3. ✅ `python -c "from rich.text import Text"` works (no import cycles)
4. ✅ `pytest tests/test_text.py` passes
5. ✅ Structural verification tests pass
