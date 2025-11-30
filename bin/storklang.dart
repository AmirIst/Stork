#!/usr/bin/env dart
import 'dart:io';
import '../lib/simple_parser.dart';
import '../lib/evaluator.dart';
import '../lib/environment.dart';
import '../lib/ast.dart';
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
    } else {
      // Normal file execution
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
  final env = Environment();
  
  print('=== StorkLang REPL ===');
  print('=== By Amirbek Istamov 103536471 ===');
  print('Type :quit to exit, :env to see bindings');
  print('Type :reset to clear environment');
  print('Type :help for commands');
  print('Two let styles supported:');
  print('let x = 5           (REPL style - binds to environment)');
  print('let x = 5 in x + 1  (Expression style)');
  print('');
  
  while (true) {
    stdout.write('> ');
    final input = stdin.readLineSync();
    
    if (input == null || input == ':quit') break;
    
    // Handle REPL commands
    if (input == ':env') {
      print('Environment: ${env.bindings}');
      continue;
    }
    if (input == ':reset') {
      env.bindings.clear();
      print('Environment cleared');
      continue;
    }
    if (input == ':help') {
      print('Commands:');
      print('  :quit   - Exit REPL');
      print('  :env    - Show current environment');
      print('  :reset  - Clear environment');
      print('  :help   - Show this help');
      print('');
      print('Let expression styles:');
      print('  let x = 5           - Binds x to 5 in environment');
      print('  let x = 5 in x + 1  - Returns 6, x not saved');
      continue;
    }
    if (input.isEmpty) continue;
    
    try {
      final expr = parser.parse(input);
      final result = evaluator.evaluate(expr, env);
      if (result != null) {
        print('Result: $result');
        
        // Auto-bind the result to _ for most expressions
        if (expr is ReplLet || expr is Lambda || expr is IntLit || 
            expr is BoolLit || expr is StringLit || expr is Var) {
          env.bind('_', result);
          print('(Also bound to _)');
        }
        
        // Show what was bound for ReplLet
        if (expr is ReplLet) {
          print('(Bound ${expr.varName} to $result)');
        }
      }
    } catch (e) {
      print('Error: $e');
    }
  }
}