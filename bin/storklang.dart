#!/usr/bin/env dart
import 'dart:io';
import '../lib/ast.dart';
import '../lib/simple_parser.dart';
import '../lib/evaluator.dart';
import '../lib/environment.dart';
import '../lib/type_checker.dart';
import '../lib/file_runner.dart';
import '../lib/compiler.dart';

void main(List<String> args) {
  if (args.isNotEmpty) {
    if (args[0] == '--compile' && args.length > 1) {
      // Compile mode
      final compiler = Compiler();
      final file = File(args[1]);
      final content = file.readAsStringSync();
      final parser = SimpleParser();
      final expr = parser.parse(content);
      final dartCode = compiler.compileToDart(expr);
      print('// Generated Dart code:');
      print(dartCode);
      return;
        } else if (args[0] == '--typecheck' && args.length > 1) {
      // Type checking mode only
      final file = File(args[1]);
      final content = file.readAsStringSync();
      final parser = SimpleParser();
      final typeChecker = TypeChecker();
      
      try {
        final expr = parser.parse(content);
        typeChecker.checkProgram(expr);
        final type = typeChecker.inferType(expr, typeChecker.createInitialEnv());
        print('✅ Type check PASSED');
        print('📝 Inferred type: $type');
      } on TypeError catch (e) {
        print('❌ Static type error: $e');
        exit(1);
      } catch (e) {
        print('💥 Error: $e');
        exit(1);
      }
      return;
    } else {
      // Normal file execution with type checking
      FileRunner.runFile(args[0]);
      
      print('\n=== File execution complete ===');
      print('Press Enter to to exit.');
      stdin.readLineSync();
      
      return;
    }
  }
  
  startRepl();
}
  

void startRepl() {
  final parser = SimpleParser();
  final evaluator = Evaluator();
  final typeChecker = TypeChecker();
  final env = Environment();
  
  print('╔══════════════════════════════════════════╗');
  print('║           StorkLang REPL v1.0            ║');
  print('║     With Static Type Checking System     ║');
  print('║       By Amirbek Istamov 103536471       ║');
  print('╚══════════════════════════════════════════╝');
  print('');
  print('📋 Commands:');
  print('  :quit   - Exit REPL');
  print('  :env    - Show current environment');
  print('  :reset  - Clear environment');
  print('  :help   - Show this help');
  print('  :types  - Show type checking info');
  print('');
  print('🔧 Two let styles supported:');
  print('  let x = 5           (REPL style - binds to environment)');
  print('  let x = 5 in x + 1  (Expression style)');
  print('');
  print('✅ Static type checking is ENABLED');
  print('   Type errors will be caught before evaluation');
  print('');
  
  while (true) {
    stdout.write('stork> ');
    final input = stdin.readLineSync()?.trim();
    
    if (input == null || input == ':quit') {
      print('👋 Goodbye!');
      break;
    }
    
    // Handle REPL commands
    if (input == ':env') {
      print('📦 Environment bindings:');
      env.bindings.forEach((key, value) {
        print('  $key = $value');
      });
      if (env.bindings.isEmpty) {
        print('  (empty)');
      }
      continue;
    }
    if (input == ':reset') {
      env.bindings.clear();
      print('🧹 Environment cleared');
      continue;
    }
    if (input == ':help') {
      print('''
📚 StorkLang Help:
  Basic types: Int, Bool, String
  Functions: λx. x + 1
  Pairs: (1, 2)
  Lists: cons 1 (cons 2 nil)
  Tuples: (1, true, "hello")
  Records: {name: "Alice", age: 25}
  Sum types: left(5), right("error")
  
  Type checking examples:
    5 + 3          ✅ Int
    true + 5       ❌ Type error
    (λx. x + 1) 5  ✅ Int
    5 10           ❌ Not a function
      ''');
      continue;
    }
    if (input == ':types') {
      print('''
🎯 Type System Information:
  - Static type checking enabled
  - Type inference for all expressions
  - Type errors caught before execution
  - Supports: Int, Bool, String, Functions, Pairs, Lists, Tuples, Records
  - Built-in type checking for all operations
      ''');
      continue;
    }
    if (input.isEmpty) continue;
    
    try {
      final expr = parser.parse(input);
      
      // 1. TYPE CHECKING (Static)
      print('🔍 Running type check...');
      try {
        final type = typeChecker.inferType(expr, TypeEnv({}));
        print('✅ Type check PASSED');
        print('📝 Inferred type: $type');
      } on TypeError catch (e) {
        print('❌ STATIC TYPE ERROR: $e');
        print('💥 Evaluation cancelled due to type error');
        continue;
      }
      
      // 2. EVALUATION (Runtime)
      final result = evaluator.evaluate(expr, env, checkTypes: false);
      if (result != null) {
        print('🎯 Result: $result');
        
        // Auto-bind the result to _ for most expressions
        if (expr is ReplLet || expr is Lambda || expr is IntLit || 
            expr is BoolLit || expr is StringLit || expr is Var) {
          env.bind('_', result);
          print('📌 (Also bound to _)');
        }
        
        // Show what was bound for ReplLet
        if (expr is ReplLet) {
          print('📌 (Bound ${expr.varName} to $result)');
        }
      }
    } catch (e) {
      print('💥 Runtime error: $e');
    }
    
    print(''); // Empty line for readability
  }
}