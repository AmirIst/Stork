import 'ast.dart';
import 'environment.dart';

class Evaluator {
  dynamic evaluate(Expr expr, Environment env) {
    try {

      if (expr is IntLit) return expr.value;
      if (expr is BoolLit) return expr.value;
      if (expr is StringLit) return expr.value;
      
      if (expr is Comment) return null; // Comments evaluate to nothing
      
      if (expr is Var) {
        // Built-in functions
        if (expr.name == "print") {
          return (dynamic value) {
            print(value);
            return value;
          };
        }
        
        if (expr.name == "length") {
          return (dynamic value) {
            if (value is List) {
              return value.length;
            }
            throw Exception('TypeError: length() expects a list at ${expr.line}:${expr.column}');
          };
        }

        if (expr.name == "map") {
          return (dynamic f) {
            return (dynamic list) {
              if (list is List && f is Function) {
                final result = <dynamic>[];
                for (final item in list) {
                  result.add(f(item));
                }
                return result;
              }
              throw Exception('TypeError: map expects function and list');
            };
          };
        }

        if (expr.name == "fold") {
          return (dynamic f) {
            return (dynamic initial) {
              return (dynamic list) {
                if (list is List && f is Function) {
                  dynamic result = initial;
                  for (final item in list) {
                    result = f(result)(item);
                  }
                  return result;
                }
                throw Exception('TypeError: fold expects function, initial value, and list');
              };
            };
          };
        }

        if (expr.name == "strlen") {
          return (dynamic str) {
            if (str is String) {
              return str.length;
            }
            throw Exception('TypeError: strlen expects string');
          };
        }

        if (expr.name == "not") {
          return (dynamic b) {
            if (b is bool) {
              return !b;
            }
            throw Exception('TypeError: not expects boolean');
          };
        }

        if (expr.name == "filter") {
          return (dynamic f) {
            return (dynamic list) {
              if (list is List && f is Function) {
                final result = <dynamic>[];
                for (final item in list) {
                  if (f(item) == true) {
                    result.add(item);
                  }
                }
                return result;
              }
              throw Exception('TypeError: filter expects function and list');
            };
          };
        }

        if (expr.name == "range") {
          return (dynamic start) {
            return (dynamic end) {
              if (start is int && end is int) {
                final result = <int>[];
                for (int i = start; i <= end; i++) {
                  result.add(i);
                }
                return result;
              }
              throw Exception('TypeError: range expects integers');
            };
          };
        }

        if (expr.name == "sqr") {
          return (dynamic n) {
            if (n is int) {
              return (n * n);
            }
            throw Exception('TypeError: sqr expects integer');
          };
        }

        
        // Handle regular variable lookup
        final value = env.lookup(expr.name);
        if (value == null) {
          throw Exception('Error[line ${expr.line}:${expr.column}]: Unbound variable "${expr.name}"');
        }
        return value;
      }

      if (expr is Let) {
        final value = evaluate(expr.value, env);
        final newEnv = env.createChild();
        newEnv.bind(expr.varName, value);
        return evaluate(expr.body, newEnv);
      }
      
      if (expr is ReplLet) {
        final value = evaluate(expr.value, env);
        env.bind(expr.varName, value);
        return value;
      }

      // Case for recursion
      if (expr is Rec) {
        // Create a recursive function using fixed-point combinator
        dynamic recursiveFunc;
        recursiveFunc = (dynamic arg) {
          final newEnv = env.createChild();
          newEnv.bind(expr.funcName, recursiveFunc);
          newEnv.bind(expr.param, arg);
          return evaluate(expr.body, newEnv);
        };
        
        final newEnv = env.createChild();
        newEnv.bind(expr.funcName, recursiveFunc);
        return evaluate(expr.inExpr, newEnv);
      }
      
      if (expr is Lambda) {
        return (dynamic arg) {
          final newEnv = env.createChild();
          newEnv.bind(expr.param, arg);
          return evaluate(expr.body, newEnv);
        };
      }
      
      if (expr is Apply) {
        final function = evaluate(expr.function, env);
        final argument = evaluate(expr.argument, env);
        if (function is Function) {
          return function(argument);
        }
        throw Exception('TypeError: $function is not callable at ${expr.line}:${expr.column}');
      }
      
      if (expr is If) {
        final condition = evaluate(expr.condition, env);
        if (condition == true) {
          return evaluate(expr.thenBranch, env);
        } else {
          return evaluate(expr.elseBranch, env);
        }
      }
      
      if (expr is BinaryOp) {
        final left = evaluate(expr.left, env);
        final right = evaluate(expr.right, env);
        
        switch (expr.operator) {
          case '+': 
            if (left is int && right is int) return left + right;
            if (left is String && right is String) return left + right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '-': 
            if (left is int && right is int) return left - right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '*': 
            if (left is int && right is int) return left * right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '/': 
            if (left is int && right is int) {
              if (right == 0) throw Exception('MathError: Division by zero at ${expr.line}:${expr.column}');
              return left ~/ right; // Integer division
            }
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '%': 
            if (left is int && right is int) {
              if (right == 0) throw Exception('MathError: Modulo by zero at ${expr.line}:${expr.column}');
              return left % right;
            }
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '==': return left == right;
          case '!=': return left != right;
          case '<': 
            if (left is int && right is int) return left < right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '>': 
            if (left is int && right is int) return left > right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '<=': 
            if (left is int && right is int) return left <= right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          case '>=': 
            if (left is int && right is int) return left >= right;
            throw Exception('Error at line ${expr.line}:${expr.column}: Operator ${expr.operator} requires both integers or both strings, got ${left.runtimeType} and ${right.runtimeType}');
          default: throw Exception('Unknown operator: "${expr.operator}"');
        }
      }
      

      // CASES FOR PAIRS AND LISTS
      if (expr is Pair) {
        final firstVal = evaluate(expr.first, env);
        final secondVal = evaluate(expr.second, env);
        return [firstVal, secondVal];
      }
      
      if (expr is First) {
        final pair = evaluate(expr.pair, env);
        if (pair is List && pair.length == 2) {
          return pair[0];
        }
        throw Exception('Error[line ${expr.line}:${expr.column}]: Expected pair type');
      }
      
      if (expr is Second) {
        final pair = evaluate(expr.pair, env);
        if (pair is List && pair.length == 2) {
          return pair[1];
        }
        throw Exception('Error[line ${expr.line}:${expr.column}]: Expected pair type');
      }
      
      if (expr is Nil) {
        return [];
      }
      
      if (expr is Cons) {
        final headVal = evaluate(expr.head, env);
        final tailVal = evaluate(expr.tail, env);
        if (tailVal is List) {
          return [headVal, ...tailVal];
        }
        throw Exception('TypeError: Expected list in cons() at ${expr.line}:${expr.column}');
      }
      
      if (expr is Head) {
        final list = evaluate(expr.list, env);
        if (list is List && list.isNotEmpty) {
          return list[0];
        }
        throw Exception('Error[line ${expr.line}:${expr.column}]: Expected list type');
      }
      
      if (expr is Tail) {
        final list = evaluate(expr.list, env);
        if (list is List && list.isNotEmpty) {
          return list.sublist(1);
        }
        throw Exception('Error[line ${expr.line}:${expr.column}]: Expected list type');
      }

      if (expr is Tuple) {
        final elements = <dynamic>[];
        for (final elementExpr in expr.elements) {
          elements.add(evaluate(elementExpr, env));
        }
        return elements;
      }

      if (expr is TupleAccess) {
        final tuple = evaluate(expr.tuple, env);
        if (tuple is List && expr.index - 1 < tuple.length) {
          return tuple[expr.index - 1];
        }
        throw Exception('Tuple access out of bounds');
      }

      if (expr is Record) {
        final record = <String, dynamic>{};
        for (final entry in expr.fields.entries) {
          record[entry.key] = evaluate(entry.value, env);
        }
        return record;
      }

      if (expr is RecordAccess) {
        final record = evaluate(expr.record, env);
        if (record is Map && record.containsKey(expr.fieldName)) {
          return record[expr.fieldName];
        }
        throw Exception('Record field not found: ${expr.fieldName}');
      }

      // In the Left case:
      if (expr is Left) {
        final value = evaluate(expr.value, env);
        return 'left($value)';
      }

      // In the Right case:
      if (expr is Right) {
        final value = evaluate(expr.value, env);
        return 'right($value)';
      }

      if (expr is Match) {
        final target = evaluate(expr.target, env);
        if (target is String && target.startsWith('left(')) {
          // Extract value from left(value)
          final value = target.substring(5, target.length - 1); // Remove 'left(' and ')'
          final newEnv = env.createChild();
          newEnv.bind(expr.leftVar, value);
          return evaluate(expr.leftBranch, newEnv);
        } else if (target is String && target.startsWith('right(')) {
          // Extract value from right(value)  
          final value = target.substring(6, target.length - 1); // Remove 'right(' and ')'
          final newEnv = env.createChild();
          newEnv.bind(expr.rightVar, value);
          return evaluate(expr.rightBranch, newEnv);
        }
        throw Exception('Match target is not a sum type');
      }

      if (expr is WhileLoop) {
        dynamic result;
        while (evaluate(expr.condition, env) == true) {
          result = evaluate(expr.body, env);
        }
        return result;
      }

      if (expr is ForLoop) {
        final startVal = evaluate(expr.start, env);
        final endVal = evaluate(expr.end, env);
        
        if (startVal is! int || endVal is! int) {
          throw Exception('For loop requires integer bounds');
        }
        
        dynamic result;
        for (int i = startVal; i <= endVal; i++) {
          final newEnv = env.createChild();
          newEnv.bind(expr.variable, i);
          result = evaluate(expr.body, newEnv);
        }
        return result;
      }

      if (expr is TypeDeclaration) {
        // Store type definition in environment
        env.bind("__type_${expr.typeName}", expr);
        return "Type ${expr.typeName} defined with constructors: ${expr.constructors.map((c) => c.name).join(', ')}";
      }

      if (expr is ConstructorCall) {
        // Simple constructor - just return a formatted string
        final args = expr.arguments.map((arg) => evaluate(arg, env)).toList();
        return "${expr.constructor}(${args.join(', ')})";
      }

      if (expr is TypeMatch) {
        final target = evaluate(expr.target, env);
        // Simple string-based pattern matching
        for (final case_ in expr.cases) {
          if (target.startsWith("${case_.constructor}(")) {
            final newEnv = env.createChild();
            // Extract argument (simplified)
            if (case_.parameters.isNotEmpty) {
              final arg = target.substring(case_.constructor.length + 1, target.length - 1);
              newEnv.bind(case_.parameters[0], arg);
            }
            return evaluate(case_.body, newEnv);
          }
        }
        throw Exception('No matching pattern found');
      }
      
      throw Exception('Unknown expression type: ${expr.runtimeType}');
    } catch (e) {
      throw Exception('Evaluation error at ${expr.runtimeType}: $e');
    }
  }
}