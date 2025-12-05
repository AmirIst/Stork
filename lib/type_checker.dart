// Replace your type_checker.dart with this
import 'ast.dart';

class TypeError implements Exception {
  final String message;
  final int line;
  final int column;
  
  TypeError(this.message, this.line, this.column);
  
  @override
  String toString() => 'TypeError[line ${line + 1}:${column + 1}]: $message';
}

class Type {
  const Type();
  
  static const Type intType = _IntType();
  static const Type boolType = _BoolType();
  static const Type stringType = _StringType();
  static const Type unitType = _UnitType();
  
  String get name => runtimeType.toString();
  
  @override
  bool operator ==(Object other) => runtimeType == other.runtimeType;
  
  @override
  int get hashCode => runtimeType.hashCode;
}

class _IntType extends Type {
  const _IntType();
  @override
  String toString() => 'Int';
}

class _BoolType extends Type {
  const _BoolType();
  @override
  String toString() => 'Bool';
}

class _StringType extends Type {
  const _StringType();
  @override
  String toString() => 'String';
}

class _UnitType extends Type {
  const _UnitType();
  @override
  String toString() => 'Unit';
}

class FunctionType extends Type {
  final Type parameter;
  final Type returnType;
  
  FunctionType(this.parameter, this.returnType);
  
  @override
  bool operator ==(Object other) {
    return other is FunctionType && 
           parameter == other.parameter && 
           returnType == other.returnType;
  }
  
  @override
  int get hashCode => parameter.hashCode ^ returnType.hashCode;
  
  @override
  String toString() => '($parameter -> $returnType)';
}

class PairType extends Type {
  final Type first;
  final Type second;
  
  PairType(this.first, this.second);
  
  @override
  bool operator ==(Object other) {
    return other is PairType && 
           first == other.first && 
           second == other.second;
  }
  
  @override
  int get hashCode => first.hashCode ^ second.hashCode;
  
  @override
  String toString() => '($first * $second)';
}

class ListType extends Type {
  final Type element;
  
  ListType(this.element);
  
  @override
  bool operator ==(Object other) {
    return other is ListType && element == other.element;
  }
  
  @override
  int get hashCode => element.hashCode;
  
  @override
  String toString() => '[$element]';
}

class TypeEnv {
  final Map<String, Type> bindings;
  
  TypeEnv(this.bindings);
  
  TypeEnv createChild() {
    return TypeEnv(Map.from(bindings));
  }
  
  void bind(String name, Type type) {
    bindings[name] = type;
  }
  
  Type? lookup(String name) {
    return bindings[name];
  }
}

class TypeChecker {
  // Create initial environment with built-ins
  TypeEnv createInitialEnv() {
    return TypeEnv({
      // Built-in functions
      'print': FunctionType(Type.intType, Type.intType),
      'length': FunctionType(ListType(Type.intType), Type.intType),
      'map': FunctionType(
        FunctionType(Type.intType, Type.intType),
        FunctionType(ListType(Type.intType), ListType(Type.intType))
      ),
      'strlen': FunctionType(Type.stringType, Type.intType),
      'not': FunctionType(Type.boolType, Type.boolType),
      'filter': FunctionType(
        FunctionType(Type.intType, Type.boolType),
        FunctionType(ListType(Type.intType), ListType(Type.intType))
      ),
      'range': FunctionType(Type.intType, FunctionType(Type.intType, ListType(Type.intType))),
      'sqr': FunctionType(Type.intType, Type.intType),
      
      // List operations - CRITICAL!
      'cons': FunctionType(Type.intType, FunctionType(ListType(Type.intType), ListType(Type.intType))),
      'nil': ListType(Type.intType),
      'head': FunctionType(ListType(Type.intType), Type.intType),
      'tail': FunctionType(ListType(Type.intType), ListType(Type.intType)),
      
      // Pair operations
      'first': FunctionType(PairType(Type.intType, Type.intType), Type.intType),
      'second': FunctionType(PairType(Type.intType, Type.intType), Type.intType),
    });
  }
  
  Type inferType(Expr expr, TypeEnv env) {
    // Handle IntLit
    if (expr is IntLit) {
      return Type.intType;
    }
    
    // Handle BoolLit
    if (expr is BoolLit) {
      return Type.boolType;
    }
    
    // Handle StringLit
    if (expr is StringLit) {
      return Type.stringType;
    }
    
    // Handle Var
    if (expr is Var) {
      final type = env.lookup(expr.name);
      if (type == null) {
        throw TypeError('Unbound variable "${expr.name}"', expr.line, expr.column);
      }
      return type;
    }
    
    // Handle Let
    if (expr is Let) {
      final valueType = inferType(expr.value, env);
      final newEnv = env.createChild();
      newEnv.bind(expr.varName, valueType);
      return inferType(expr.body, newEnv);
    }
    
    // Handle Lambda
    if (expr is Lambda) {
      // Create a fresh type variable (for now, use int)
      final paramType = Type.intType;
      final newEnv = env.createChild();
      newEnv.bind(expr.param, paramType);
      final bodyType = inferType(expr.body, newEnv);
      return FunctionType(paramType, bodyType);
    }
    
    // Handle Apply
    if (expr is Apply) {
      final funcType = inferType(expr.function, env);
      final argType = inferType(expr.argument, env);
      
      if (funcType is! FunctionType) {
        throw TypeError('Expected function type, got $funcType', expr.line, expr.column);
      }
      
      if (funcType.parameter != argType) {
        throw TypeError('Type mismatch: expected ${funcType.parameter}, got $argType', expr.line, expr.column);
      }
      
      return funcType.returnType;
    }
    
    // Handle If
    if (expr is If) {
      final condType = inferType(expr.condition, env);
      if (condType != Type.boolType) {
        throw TypeError('Condition must be Bool, got $condType', expr.line, expr.column);
      }
      
      final thenType = inferType(expr.thenBranch, env);
      final elseType = inferType(expr.elseBranch, env);
      
      if (thenType != elseType) {
        throw TypeError('Branches must have same type: $thenType vs $elseType', expr.line, expr.column);
      }
      
      return thenType;
    }
    
    // Handle BinaryOp
    if (expr is BinaryOp) {
      final leftType = inferType(expr.left, env);
      final rightType = inferType(expr.right, env);
      
      // Check arithmetic operators
      if (['+', '-', '*', '/', '%'].contains(expr.operator)) {
        if (leftType != Type.intType || rightType != Type.intType) {
          throw TypeError('Operator ${expr.operator} requires Int, got $leftType and $rightType', expr.line, expr.column);
        }
        return Type.intType;
      }
      
      // Check comparison operators
      if (['==', '!=', '<', '>', '<=', '>='].contains(expr.operator)) {
        if (leftType != rightType) {
          throw TypeError('Operator ${expr.operator} requires same types, got $leftType and $rightType', expr.line, expr.column);
        }
        return Type.boolType;
      }
      
      throw TypeError('Unknown operator: ${expr.operator}', expr.line, expr.column);
    }
    
    // Handle Pair
    if (expr is Pair) {
      final firstType = inferType(expr.first, env);
      final secondType = inferType(expr.second, env);
      return PairType(firstType, secondType);
    }
    
    // Handle First
    if (expr is First) {
      final pairType = inferType(expr.pair, env);
      if (pairType is! PairType) {
        throw TypeError('Expected pair type, got $pairType', expr.line, expr.column);
      }
      return pairType.first;
    }
    
    // Handle Second
    if (expr is Second) {
      final pairType = inferType(expr.pair, env);
      if (pairType is! PairType) {
        throw TypeError('Expected pair type, got $pairType', expr.line, expr.column);
      }
      return pairType.second;
    }
    
    // Handle Nil
    if (expr is Nil) {
      return ListType(Type.intType);
    }
    
    // Handle Cons
    if (expr is Cons) {
      final headType = inferType(expr.head, env);
      final tailType = inferType(expr.tail, env);
      
      if (tailType is! ListType) {
        throw TypeError('Expected list type for tail, got $tailType', expr.line, expr.column);
      }
      
      if (headType != tailType.element) {
        throw TypeError('List element type mismatch: $headType vs ${tailType.element}', expr.line, expr.column);
      }
      
      return ListType(headType);
    }
    
    // Handle Head
    if (expr is Head) {
      final listType = inferType(expr.list, env);
      if (listType is! ListType) {
        throw TypeError('Expected list type, got $listType', expr.line, expr.column);
      }
      return listType.element;
    }
    
    // Handle Tail
    if (expr is Tail) {
      final listType = inferType(expr.list, env);
      if (listType is! ListType) {
        throw TypeError('Expected list type, got $listType', expr.line, expr.column);
      }
      return listType;
    }
    
    // Handle ReplLet
    if (expr is ReplLet) {
      final valueType = inferType(expr.value, env);
      return valueType;
    }
    
    // Handle Comment
    if (expr is Comment) {
      return Type.intType; // Comments have no real type
    }
    
    // Handle Rec
    if (expr is Rec) {
      // For recursive functions, we need to handle the recursion
      final paramType = Type.intType;
      final newEnv = env.createChild();
      // First bind the function name with a placeholder type
      newEnv.bind(expr.funcName, FunctionType(paramType, Type.intType));
      newEnv.bind(expr.param, paramType);
      
      // Now infer the body type
      final bodyType = inferType(expr.body, newEnv);
      
      // Update the function type with the actual return type
      newEnv.bind(expr.funcName, FunctionType(paramType, bodyType));
      
      return inferType(expr.inExpr, newEnv);
    }
    
    // For any other expression type, return a default type
    return Type.intType;
  }
  
  void checkProgram(Expr expr) {
    final env = createInitialEnv();
    inferType(expr, env);
  }
}