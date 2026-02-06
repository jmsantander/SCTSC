# Documentation Guide

This document describes the documentation standards used throughout the SCT Camera Slow Control visualization codebase.

## Overview

All visualization code includes comprehensive documentation following industry best practices:

- **JavaScript**: JSDoc format with `@param`, `@returns`, `@example` tags
- **Python**: Google-style docstrings with type hints
- **Inline comments**: Explanations for complex logic
- **Module headers**: High-level descriptions and usage examples

## JavaScript Documentation (JSDoc)

### File Headers

Every JavaScript file begins with a module-level documentation block:

```javascript
/**
 * Module Name
 * 
 * Brief description of what this module does.
 * 
 * @module ModuleName
 * @author SCT Camera Team
 * @version 1.0.0
 * 
 * @example
 * // Usage example
 * const instance = new ClassName();
 * instance.someMethod();
 */
```

### Class Documentation

```javascript
/**
 * Brief class description.
 * 
 * Detailed explanation of what the class manages,
 * how it works, and when to use it.
 */
class ClassName {
    /**
     * Constructor description.
     * 
     * @param {type} paramName - Parameter description
     * 
     * @example
     * const obj = new ClassName('value');
     */
    constructor(paramName) {
        // ...
    }
}
```

### Method Documentation

```javascript
/**
 * Method description.
 * 
 * Detailed explanation of what this method does,
 * including any side effects or important notes.
 * 
 * @param {type} paramName - Parameter description
 * @param {type} [optionalParam] - Optional parameter (note the brackets)
 * @returns {type} Return value description
 * 
 * @example
 * // Example usage
 * const result = obj.methodName(value);
 * console.log(result);
 */
methodName(paramName, optionalParam) {
    // ...
}
```

### JSDoc Tags Used

- `@module` - Module identification
- `@author` - Author information
- `@version` - Version number
- `@param` - Function/method parameters with types
- `@returns` - Return value with type
- `@example` - Usage examples
- `@type` - Variable type
- `@private` - Private method indicator

## Python Documentation (Docstrings)

### Module Headers

Every Python file begins with a module docstring:

```python
"""
Module Name

Brief description of module purpose.

Detailed explanation including:
    - Key features
    - Usage patterns
    - Important notes

Author: SCT Camera Team
Version: 1.0.0

Example:
    >>> from module import Class
    >>> instance = Class()
    >>> result = instance.method()
    >>> print(result)
"""
```

### Class Documentation

```python
class ClassName:
    """
    Brief class description.
    
    Detailed explanation of the class purpose, behavior,
    and usage patterns.
    
    Attributes:
        attribute1 (type): Description of attribute
        attribute2 (type): Description of attribute
    
    Example:
        >>> obj = ClassName()
        >>> obj.method()
    """
```

### Method Documentation

```python
def method_name(self, param1: int, param2: str = 'default') -> dict:
    """
    Brief method description.
    
    Detailed explanation of what this method does,
    including any side effects or important notes.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter. Default is 'default'.
    
    Returns:
        Dictionary containing:
            key1 (type): Description
            key2 (type): Description
    
    Raises:
        ValueError: When parameter is invalid
        TypeError: When type is incorrect
    
    Example:
        >>> obj = ClassName()
        >>> result = obj.method_name(42, 'value')
        >>> print(result['key1'])
    """
    pass
```

### Docstring Sections

- **Brief description**: One-line summary
- **Detailed description**: Multiple paragraphs if needed
- **Args**: Parameter descriptions with types
- **Returns**: Return value structure and types
- **Raises**: Exceptions that may be raised
- **Example**: Usage examples with `>>>` prompts
- **Note**: Important notes or warnings
- **Todo**: Future improvements

## Inline Comments

### When to Use

Inline comments explain **why**, not **what**:

```javascript
// GOOD: Explains reasoning
// Use exponential moving average to prevent jarring temperature jumps
this.temperatures[i] = this.temperatures[i] * 0.9 + temp * 0.1;

// BAD: States the obvious
// Multiply by 0.9 and add temp times 0.1
this.temperatures[i] = this.temperatures[i] * 0.9 + temp * 0.1;
```

### Comment Style

```javascript
// Single-line comments use double slash

/**
 * Multi-line comments for complex logic
 * use JSDoc format even if not documenting
 * a function or class.
 */
```

## Code Examples in Documentation

### Example Guidelines

1. **Show real usage**: Examples should demonstrate actual use cases
2. **Include output**: Show expected results when helpful
3. **Keep simple**: Focus on the feature being documented
4. **Be complete**: Include necessary imports/setup

### JavaScript Examples

```javascript
/**
 * @example
 * // Initialize visualization
 * const viz = new CameraVisualization('canvas');
 * 
 * // Enable simulation
 * viz.toggleSimulation();
 * 
 * // Change color scale
 * viz.setColorScale('hot');
 * 
 * // Select module 112 (center of center backplane)
 * viz.selectModule(112);
 */
```

### Python Examples

```python
"""
Example:
    >>> # Initialize API
    >>> api = CameraAPI()
    >>> 
    >>> # Get module info
    >>> info = api.get_module_info(112)
    >>> print(f"Temperature: {info['temperature']:.2f}°C")
    Temperature: 22.35°C
    >>> 
    >>> # Get all modules in backplane
    >>> modules = api.get_backplane_modules(4)
    >>> print(f"Found {len(modules)} modules")
    Found 25 modules
"""
```

## Documentation Standards by File

### camera_viz.js

**Documentation includes:**
- Module header with SCT structure overview
- Class-level documentation
- All methods documented with `@param`, `@returns`
- Complex algorithms explained inline
- Usage examples for key methods
- Global functions documented

**Key features documented:**
- Module ID to position mapping
- Canvas coordinate system
- Color scale algorithms
- Temperature simulation physics
- Event handling

### monitoring.js

**Documentation includes:**
- Module dependencies (Plotly, Chart.js)
- Data structure descriptions
- Time-series buffering logic
- Gauge configuration options
- Simulation data generation

**Key features documented:**
- Plotly plot initialization
- Chart.js gauge creation
- Data point management
- Update mechanisms

### camera_api.py

**Documentation includes:**
- Module-level docstring with API overview
- Type hints for all methods
- Comprehensive parameter descriptions
- Return value structures
- Error handling patterns
- Flask route documentation

**Key features documented:**
- Module numbering scheme
- API endpoint specifications
- Data retrieval patterns
- Test pattern generation

## Generating Documentation

### JSDoc

Generate HTML documentation from JavaScript:

```bash
# Install JSDoc
npm install -g jsdoc

# Generate documentation
jsdoc camera_viz.js monitoring.js -d ./docs/js
```

### Python Docstrings

Generate HTML documentation from Python:

```bash
# Install pdoc
pip install pdoc3

# Generate documentation
pdoc --html camera_api.py -o ./docs/python
```

### Sphinx (Advanced)

For comprehensive documentation site:

```bash
# Install Sphinx
pip install sphinx sphinx-rtd-theme

# Initialize Sphinx
sphinx-quickstart docs

# Build documentation
cd docs
make html
```

## IDE Integration

### Visual Studio Code

**Extensions:**
- **Better Comments**: Color-coded comment highlighting
- **Document This**: Auto-generate JSDoc comments
- **Python Docstring Generator**: Auto-generate Python docstrings

**Settings:**
```json
{
  "editor.suggest.showReferences": true,
  "editor.quickSuggestions": {
    "comments": true
  }
}
```

### PyCharm / IntelliJ

- Ctrl+Q (Windows/Linux) or F1 (Mac) shows quick documentation
- Alt+Insert generates docstring templates
- Type hints provide inline documentation

## Documentation Checklist

Before committing code, verify:

- [ ] Module header with description and examples
- [ ] All classes documented
- [ ] All public methods/functions documented
- [ ] Parameters include types and descriptions
- [ ] Return values documented
- [ ] Complex logic has inline comments
- [ ] Examples provided for key functionality
- [ ] Error cases documented
- [ ] No spelling errors in comments

## Best Practices

### DO:

✅ Write documentation as you code
✅ Include examples for complex features
✅ Update docs when code changes
✅ Use consistent formatting
✅ Explain the "why" not just the "what"
✅ Include type information
✅ Document edge cases and errors

### DON'T:

❌ State the obvious (`i++; // increment i`)
❌ Leave outdated documentation
❌ Write paragraphs where one line suffices
❌ Document every single line
❌ Use unclear variable names instead of comments
❌ Forget to document public APIs

## Template Files

### JavaScript Template

```javascript
/**
 * Module Name
 * 
 * Module description.
 * 
 * @module ModuleName
 * @author SCT Camera Team
 * @version 1.0.0
 */

/**
 * Class description.
 */
class ClassName {
    /**
     * Constructor.
     * @param {type} param - Description
     */
    constructor(param) {
        this.param = param;
    }
    
    /**
     * Method description.
     * @param {type} arg - Description
     * @returns {type} Description
     */
    method(arg) {
        return arg;
    }
}
```

### Python Template

```python
"""
Module Name

Module description.

Author: SCT Camera Team
Version: 1.0.0
"""

from typing import Dict, Any

class ClassName:
    """
    Class description.
    
    Attributes:
        attr (type): Description
    """
    
    def __init__(self, param: str):
        """Initialize.
        
        Args:
            param: Description
        """
        self.attr = param
    
    def method(self, arg: int) -> Dict[str, Any]:
        """Method description.
        
        Args:
            arg: Description
        
        Returns:
            Description of return value
        """
        return {'result': arg}
```

## Resources

### JavaScript
- [JSDoc Official Guide](https://jsdoc.app/)
- [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html)
- [Clean Code JavaScript](https://github.com/ryanmcdermott/clean-code-javascript)

### Python
- [PEP 257 - Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Type Hints (PEP 484)](https://www.python.org/dev/peps/pep-0484/)

### General
- [Write the Docs](https://www.writethedocs.org/)
- [The Documentation System](https://documentation.divio.com/)

## Conclusion

Good documentation is essential for:
- **Maintainability**: Future developers understand the code
- **Collaboration**: Team members work together effectively
- **Onboarding**: New contributors get up to speed quickly
- **Debugging**: Issues are easier to diagnose
- **API Usage**: Users know how to integrate the code

Invest time in documentation now to save hours of confusion later!
