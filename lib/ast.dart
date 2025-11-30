// AST for expressions
abstract class Expr {
  int get line;
  int get column;
}

class IntLit extends Expr {
  final int value;
  final int line;
  final int column;
  IntLit(this.value, this.line, this.column);
}

class BoolLit extends Expr {
  final bool value;
  final int line;
  final int column;
  BoolLit(this.value, this.line, this.column);
}

class Var extends Expr {
  final String name;
  final int line;
  final int column;
  Var(this.name, this.line, this.column);
}

class Let extends Expr {
  final String varName;
  final Expr value;
  final Expr body;
  final int line;
  final int column;
  Let(this.varName, this.value, this.body, this.line, this.column);
}

class Lambda extends Expr {
  final String param;
  final Expr body;
  final int line;
  final int column;
  Lambda(this.param, this.body, this.line, this.column);
}

class Apply extends Expr {
  final Expr function;
  final Expr argument;
  final int line;
  final int column;
  Apply(this.function, this.argument, this.line, this.column);
}

class If extends Expr {
  final Expr condition;
  final Expr thenBranch;
  final Expr elseBranch;
  final int line;
  final int column;
  If(this.condition, this.thenBranch, this.elseBranch, this.line, this.column);
}

class BinaryOp extends Expr {
  final String operator;
  final Expr left;
  final Expr right;
  final int line;
  final int column;
  BinaryOp(this.operator, this.left, this.right, this.line, this.column);
}

class StringLit extends Expr {
  final String value;
  final int line;
  final int column;
  StringLit(this.value, this.line, this.column);
}

class ReplLet extends Expr {
  final String varName;
  final Expr value;
  final int line;
  final int column;
  ReplLet(this.varName, this.value, this.line, this.column);
}

// BONUS: Comments (100 points!)
class Comment extends Expr {
  final String text;
  final int line;
  final int column;
  Comment(this.text, this.line, this.column);
}

class Pair extends Expr {
  final Expr first;
  final Expr second;
  final int line;
  final int column;
  Pair(this.first, this.second, this.line, this.column);
}

class First extends Expr {
  final Expr pair;
  final int line;
  final int column;
  First(this.pair, this.line, this.column);
}

class Second extends Expr {
  final Expr pair;
  final int line;
  final int column;
  Second(this.pair, this.line, this.column);
}

class Nil extends Expr {
  final int line;
  final int column;
  Nil(this.line, this.column);
}

class Cons extends Expr {
  final Expr head;
  final Expr tail;
  final int line;
  final int column;
  Cons(this.head, this.tail, this.line, this.column);
}

class Head extends Expr {
  final Expr list;
  final int line;
  final int column;
  Head(this.list, this.line, this.column);
}

class Rec extends Expr {
  final String funcName;
  final String param;
  final Expr body;
  final Expr inExpr;
  final int line;
  final int column;
  Rec(this.funcName, this.param, this.body, this.inExpr, this.line, this.column);
}

class Tail extends Expr {
  final Expr list;
  final int line;
  final int column;
  Tail(this.list, this.line, this.column);
}

class Left extends Expr {
  final Expr value;
  final int line;
  final int column;
  Left(this.value, this.line, this.column);
}

class Right extends Expr {
  final Expr value;
  final int line;
  final int column;
  Right(this.value, this.line, this.column);
}

class Match extends Expr {
  final Expr target;
  final String leftVar;
  final Expr leftBranch;
  final String rightVar;
  final Expr rightBranch;
  final int line;
  final int column;
  Match(this.target, this.leftVar, this.leftBranch, this.rightVar, this.rightBranch, this.line, this.column);
}

class Tuple extends Expr {
  final List<Expr> elements;
  final int line;
  final int column;
  Tuple(this.elements, this.line, this.column);
}

class TupleAccess extends Expr {
  final Expr tuple;
  final int index;
  final int line;
  final int column;
  TupleAccess(this.tuple, this.index, this.line, this.column);
}

class Record extends Expr {
  final Map<String, Expr> fields;
  final int line;
  final int column;
  Record(this.fields, this.line, this.column);
}

class RecordAccess extends Expr {
  final Expr record;
  final String fieldName;
  final int line;
  final int column;
  RecordAccess(this.record, this.fieldName, this.line, this.column);
}

class DataConstructor extends Expr {
  final String name;
  final List<Expr> arguments;
  final int line;
  final int column;
  DataConstructor(this.name, this.arguments, this.line, this.column);
}

class DataMatch extends Expr {
  final Expr target;
  final List<MatchCase> cases;
  final int line;
  final int column;
  DataMatch(this.target, this.cases, this.line, this.column);
}

class MatchCase {
  final String constructor;
  final List<String> parameters;
  final Expr body;
  MatchCase(this.constructor, this.parameters, this.body);
}

class WhileLoop extends Expr {
  final Expr condition;
  final Expr body;
  final int line;
  final int column;
  WhileLoop(this.condition, this.body, this.line, this.column);
}

class ForLoop extends Expr {
  final String variable;
  final Expr start;
  final Expr end;
  final Expr body;
  final int line;
  final int column;
  ForLoop(this.variable, this.start, this.end, this.body, this.line, this.column);
}

class DataTypeDeclaration extends Expr {
  final String name;
  final List<String> constructors;
  final int line;
  final int column;
  DataTypeDeclaration(this.name, this.constructors, this.line, this.column);
}

class TypeDeclaration extends Expr {
  final String typeName;
  final List<ConstructorDef> constructors;
  final int line;
  final int column;
  TypeDeclaration(this.typeName, this.constructors, this.line, this.column);
}

class ConstructorDef {
  final String name;
  final List<String> parameters;
  ConstructorDef(this.name, this.parameters);
}

class ConstructorCall extends Expr {
  final String constructor;
  final List<Expr> arguments;
  final int line;
  final int column;
  ConstructorCall(this.constructor, this.arguments, this.line, this.column);
}

class TypeMatch extends Expr {
  final Expr target;
  final List<TypeCase> cases;
  final int line;
  final int column;
  TypeMatch(this.target, this.cases, this.line, this.column);
}

class TypeCase {
  final String constructor;
  final List<String> parameters;
  final Expr body;
  TypeCase(this.constructor, this.parameters, this.body);
}