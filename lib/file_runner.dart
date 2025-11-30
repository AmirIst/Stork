import 'dart:io';
import 'simple_parser.dart';
import 'evaluator.dart';
import 'environment.dart';

class FileRunner {
  static void runFile(String filename) {
    final parser = SimpleParser();
    final evaluator = Evaluator();
    final env = Environment();
    
    try {
      final file = File(filename);
      final content = file.readAsStringSync();
      
      // Remove comments and clean up the content
      final cleanedContent = _removeComments(content);
      
      // Try to parse the entire content as one expression
      try {
        final expr = parser.parse(cleanedContent);
        final result = evaluator.evaluate(expr, env);
        if (result != null) {
          print('Result: $result');
        }
      } catch (e) {
        print('Error parsing as single expression: $e');
        print('Trying statement-by-statement execution...');
        _runStatements(cleanedContent, parser, evaluator, env);
      }
    } catch (e) {
      print('Error reading file: $e');
    }
  }
  
  static String _removeComments(String content) {
    final lines = content.split('\n');
    final cleanedLines = <String>[];
    
    for (final line in lines) {
      var cleaned = line.trim();
      
      // Remove single-line comments
      if (cleaned.contains('//')) {
        cleaned = cleaned.substring(0, cleaned.indexOf('//')).trim();
      }
      
      // Remove empty lines
      if (cleaned.isNotEmpty) {
        cleanedLines.add(cleaned);
      }
    }
    
    return cleanedLines.join(' ');
  }
  
  static void _runStatements(String content, SimpleParser parser, Evaluator evaluator, Environment env) {
    // Split by semicolons or try to split into logical statements
    final statements = _splitStatements(content);
    
    for (final statement in statements) {
      final trimmed = statement.trim();
      if (trimmed.isEmpty) continue;
      
      try {
        final expr = parser.parse(trimmed);
        final result = evaluator.evaluate(expr, env);
        if (result != null) {
          print('>> $result');
        }
      } catch (e) {
        print('Error in statement "$trimmed": $e');
      }
    }
  }
  
  static List<String> _splitStatements(String content) {
    final statements = <String>[];
    var current = '';
    var parenCount = 0;
    var bracketCount = 0;
    
    for (int i = 0; i < content.length; i++) {
      final char = content[i];
      
      if (char == '(') parenCount++;
      if (char == ')') parenCount--;
      if (char == '[') bracketCount++;
      if (char == ']') bracketCount--;
      
      // Split at 'in' keywords that are at top level
      if (char == 'i' && 
          i + 1 < content.length && 
          content[i + 1] == 'n' &&
          parenCount == 0 && 
          bracketCount == 0 &&
          (i == 0 || content[i - 1] == ' ') &&
          (i + 2 >= content.length || content[i + 2] == ' ')) {
        
        if (current.trim().isNotEmpty) {
          statements.add(current.trim());
        }
        current = '';
        i++; // Skip the 'n'
        continue;
      }
      
      current += char;
    }
    
    if (current.trim().isNotEmpty) {
      statements.add(current.trim());
    }
    
    return statements;
  }
}