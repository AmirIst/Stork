import 'ast.dart';

class Compiler {
  String compileToDart(Expr expr) {
    return _compileExpr(expr);
  }
  
  String _compileExpr(Expr expr) {
    if (expr is IntLit) return expr.value.toString();
    if (expr is BoolLit) return expr.value.toString();
    if (expr is StringLit) return '"${expr.value}"';
    
    if (expr is Var) {
      return expr.name;
    }
    
    if (expr is Let) {
      return '(() { var ${expr.varName} = ${_compileExpr(expr.value)}; return ${_compileExpr(expr.body)}; })()';
    }
    
    if (expr is ReplLet) {
      return 'var ${expr.varName} = ${_compileExpr(expr.value)};';
    }
    
    if (expr is Lambda) {
      return '(${expr.param}) => ${_compileExpr(expr.body)}';
    }
    
    if (expr is Apply) {
      return '${_compileExpr(expr.function)}(${_compileExpr(expr.argument)})';
    }
    
    if (expr is If) {
      return '${_compileExpr(expr.condition)} ? ${_compileExpr(expr.thenBranch)} : ${_compileExpr(expr.elseBranch)}';
    }
    
    if (expr is BinaryOp) {
      return '(${_compileExpr(expr.left)} ${expr.operator} ${_compileExpr(expr.right)})';
    }
    
    if (expr is Nil) return '[]';
    if (expr is Cons) {
      return '[${_compileExpr(expr.head)}, ...${_compileExpr(expr.tail)}]';
    }
    
    if (expr is Pair) {
      return '[${_compileExpr(expr.first)}, ${_compileExpr(expr.second)}]';
    }
    
    if (expr is Tuple) {
      final elements = expr.elements.map(_compileExpr).join(', ');
      return '[$elements]';
    }
    
    return '/* Unsupported expression: ${expr.runtimeType} */';
  }
}