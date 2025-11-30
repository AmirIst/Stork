# StorkLang 🦢 - Functional Programming Language
**By Amirbek Istamov 103536471**

StorkLang is a functional programming language with static type safety features. It supports first-class functions, algebraic data types, and immutable data structures.

**Key Features:**
- Functional programming paradigm
- First-class functions and closures
- Lists, tuples, records, and pairs
- Higher-order functions (map, fold, filter)
- REPL with persistent environment

## 🚀 Quick Start


# Run the interpreter
```bash
dart run storklang
```

# Execute a file
```bash
dart run storklang program.stork
```

# Start REPL with preloaded file
```bash
dart run storklang --repl lib.stork
```

## Running the Project

### Prerequisites
- Dart SDK 3.0+ installed

### Installation & Execution

1. **Extract project files**

2. **Install dependencies:**
```bash
dart pub get
```
3. **Run the REPL (Interactive Shell):**
```bash
dart run bin/storklang.dart
```

4. **Execute a StorkLang file:**
```bash
dart run bin/storklang.dart examples/hello.slk
```
### Quick Start Examples
**Try these in the REPL:**

##### Basic arithmetic
```bash
5 + 3
```

##### Variables
```bash
let x = 5
x * 2
```

##### Functions
```bash
fn x => x + 1
```

##### Conditionals
```bash
if 5 > 3 then "yes" else "no"
```

### Project Structure
bin/storklang.dart - Main REPL

lib/ - Language implementation

programs/ - Sample programs

README.md - This file

TUTORIAL.md - Language tutorial
