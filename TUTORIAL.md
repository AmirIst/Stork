
# StorkLang Tutorial

## 2.1 Language Tour

### Basic Values and Arithmetic

```rust
5                    // Integer: 5
true                 // Boolean: true
false                // Boolean: false
"hello"              // String: "hello"

5 + 3                // 8
10 - 4               // 6
6 * 7                // 42
15 / 3               // 5
10 % 3               // 1
```

### Variables and Scoping
```rust
// REPL-style (persists in environment)
let x = 5            // Binds x to 5
x * 2                // 10

// Expression-style (local scope)
let x = 5 in x * 2   // Returns 10, x not saved

// Multiple bindings
let x = 5
let y = 10
x + y                // 15
```
### Functions
```rust
// Lambda functions
fn x => x + 1

// Function application
(fn x => x * 2)(5)   // 10

// Named functions
let double = fn x => x * 2
double(10)           // 20

// Currying (multiple arguments)
let add = fn x => fn y => x + y
add(5)(3)            // 8
```

### Conditionals
```rust
// Basic conditionals
if true then 5 else 3               // 5
if 10 > 5 then "yes" else "no"      // "yes"

// Practical examples
let abs = fn x => if x >= 0 then x else -x
abs(-5)                             // 5

let max = fn a => fn b => if a > b then a else b
max(10)(15)                         // 15
```

### Lists
```rust
// List construction
[]
[1, 2, 3]
[true, false]

// List operations
let numbers = [1, 2, 3, 4, 5] in
let double = fn x => x * 2 in
let rec map = fn f => fn list =>
  if list == [] then []
  else cons(f(head(list)))(map(f)(tail(list)))
in map(double)(numbers)             // [2, 4, 6, 8, 10]
```

### Pairs and Tuples
```rust
// Pairs
let point = (,3,4) in
let x = first(point) in
let y = second(point) in
x * x + y * y                       // 25

// Tuples
(1, 2, 3)
let point = (3, 4, 5) in
_1(point) + _2(point)               // 7
```

### Records
```rust
// Record construction
{name: "Alice", age: 30}

// Record access
let person = {name: "John", age: 30} in
person.name                         // "John"
```

### Higher-Order Functions
```rust
// Map - transform elements
let numbers = [1, 2, 3] in
let double = fn x => x * 2 in
map(double)(numbers)                // [2, 4, 6]

// Filter - select elements
let numbers = [1, 2, 3, 4, 5] in
let isEven = fn x => (x % 2) == 0 in
filter(isEven)(numbers)             // [2, 4]

// Built-in functions
print "Hello"                       // prints "Hello"
let mylist = [1, 2, 3] in
length(mylist)                      // 3
```

### Recursion
```rust
// Recursive factorial
let rec fact = fn n => if n == 0 then 1 else n * fact(n - 1) in fact(5)     // 120
```

### Loops
```rust
// while loop
let condition = true in
while condition do print "Variable condition works" // ctrl + c to stop

// while loop
for i from 1 to 3 do
for j from 1 to 3 do
  print (i * j)                     // 9
```
### for more examples look /programs/
## 2.2 Exercises

Try solving these problems to practice StorkLang programming. Solutions are provided below.

## Exercise 1: Triple Function
Write a function that triples a number.

**Example:** `triple(4)` should return `12`

## Exercise 2: Minimum Function  
Write a function that returns the smaller of two numbers.

**Example:** `min(5, 3)` should return `3`

## Exercise 3: Even Check
Write a function that checks if a number is even.

**Example:** `isEven(4)` should return `true`, `isEven(5)` should return `false`

## Exercise 4: Square Function
Write a function that calculates the square of a number.

**Example:** `square(5)` should return `25`

## Exercise 5: Absolute Value
Write a function that returns the absolute value of a number.

**Example:** `abs(-7)` should return `7`

---

# Solutions

## Solution 1: Triple Function
```rust
// 1 Triple Function
let triple = fn x => x * 3 in triple(4)

// 2 Minimum Function
let min = fn a => fn b => if a < b then a else b in min(5)(3)

// 3 Even Check
let isEven = fn x => (x % 2) == 0 in isEven(5)

// 4 Square Function
let square = fn x => x * x in square(5)

// 5 Absolute Value

let abs = fn x => if x >= 0 then x else -x in abs(-7)
