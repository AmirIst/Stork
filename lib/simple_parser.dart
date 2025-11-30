import 'ast.dart';

class MatchCase {
  final String constructor;
  final List<String> parameters;
  final Expr body;
  MatchCase(this.constructor, this.parameters, this.body);
}

class SimpleParser {
  int _pos = 0;
  String _input = '';
  List<String> _tokens = [];
  int _currentLine = 1;
  int _currentColumn = 1;

  Expr parse(String input) {
    _input = input.trim();
    _pos = 0;
    _tokenize();
    return _parseExpr();
  }

  Expr _parseMatch() {
  // Parse: match <target> with left <var> => <expr> right <var> => <expr>
    final target = _parseExpr();
    
    // Skip 'with' if present
    if (_peek() == 'with') {
      _consume();
    }
    
    // Parse left case: left x => ...
    if (_peek() != 'left') {
      throw FormatException('Expected "left" after match target, got ${_peek()}');
    }
    _consume(); // consume 'left'
    
    final leftVar = _consume(); // variable name
    if (!_match('=>')) throw FormatException('Expected => after left variable');
    final leftBranch = _parseExpr();
    
    // Parse right case: right y => ...
    if (_peek() != 'right') {
      throw FormatException('Expected "right" after left branch, got ${_peek()}');
    }
    _consume(); // consume 'right'
    
    final rightVar = _consume(); // variable name
    if (!_match('=>')) throw FormatException('Expected => after right variable');
    final rightBranch = _parseExpr();
    
    return Match(target, leftVar, leftBranch, rightVar, rightBranch, 0, 0);
  }

  void _tokenize() {
    _tokens = [];
    final buffer = StringBuffer();
    _currentLine = 1;   
    _currentColumn = 1;  
    
    int i = 0;
    while (i < _input.length) {
      final char = _input[i];
      
      // Track newlines for line numbers
      if (char == '\n') {
        _currentLine++;
        _currentColumn = 1;
      } else {
        _currentColumn++;
      }
      
      if (_isWhitespace(char)) {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        i++;
        continue;
      }
      
      // Handle single-line comments
      if (char == '/' && i + 1 < _input.length && _input[i + 1] == '/') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        // Skip to end of line
        while (i < _input.length && _input[i] != '\n') {
          i++;
        }
        continue;
      }
      
      // Handle multi-line comments
      if (char == '/' && i + 1 < _input.length && _input[i + 1] == '*') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        // Skip until */
        i += 2; // Skip '/*'
        while (i < _input.length - 1 && !(_input[i] == '*' && _input[i + 1] == '/')) {
          i++;
        }
        if (i < _input.length - 1) {
          i += 2; // Skip '*/'
        } else {
          throw FormatException('Unterminated multi-line comment');
        }
        continue;
      }
      
      // Handle strings
      if (char == '"') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        i++; // Skip opening quote
        final stringBuffer = StringBuffer();
        while (i < _input.length && _input[i] != '"') {
          stringBuffer.write(_input[i]);
          i++;
        }
        if (i < _input.length) {
          _tokens.add('"${stringBuffer.toString()}"');
          i++; // Skip closing quote
        } else {
          throw FormatException('Unterminated string');
        }
        continue;
      }
      
      // Handle lists - don't split on commas inside them
      if (char == '[') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        
        // Parse entire list as one token
        final listToken = _parseBracketToken(i, '[', ']');
        _tokens.add(listToken);
        i += listToken.length;
        continue;
      }
      
      // Handle pairs - look for (, pattern
      if (char == '(' && i + 1 < _input.length && _input[i + 1] == ',') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        
        // Parse pair as one token
        final pairToken = _parseBracketToken(i, '(', ')');
        _tokens.add(pairToken);
        i += pairToken.length;
        continue;
      }
      
      // Handle multi-character operators like '=>', '==', '!='
      if (i + 1 < _input.length) {
        final twoChar = _input.substring(i, i + 2);
        if (_isTwoCharOperator(twoChar)) {
          if (buffer.isNotEmpty) {
            _tokens.add(buffer.toString());
            buffer.clear();
          }
          _tokens.add(twoChar);
          i += 2; // Skip both characters
          continue;
        }
      }

      // Handle tuples - look for ( without , after
      if (char == '(' && i + 1 < _input.length && _input[i + 1] != ',') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        
        // Check if it's a tuple by looking for multiple elements
        final tupleToken = _parseBracketToken(i, '(', ')');
        final content = tupleToken.substring(1, tupleToken.length - 1).trim();
        if (content.split(',').length > 1) {
          _tokens.add(tupleToken);
          i += tupleToken.length;
          continue;
        }
      }

      // Handle records - look for { pattern
      if (char == '{') {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        
        final recordToken = _parseBracketToken(i, '{', '}');
        _tokens.add(recordToken);
        i += recordToken.length;
        continue;
      }
      
      if (_isSpecialChar(char)) {
        if (buffer.isNotEmpty) {
          _tokens.add(buffer.toString());
          buffer.clear();
        }
        _tokens.add(char);
        i++;
        continue;
      }
      
      buffer.write(char);
      i++;
    }
    
    if (buffer.isNotEmpty) {
      _tokens.add(buffer.toString());
    }
  }

  String _parseBracketToken(int start, String open, String close) {
    final buffer = StringBuffer();
    buffer.write(_input[start]); // Write opening bracket
    int i = start + 1;
    int bracketCount = 1;
    
    while (i < _input.length && bracketCount > 0) {
      final char = _input[i];
      buffer.write(char);
      
      if (char == open) bracketCount++;
      if (char == close) bracketCount--;
      
      i++;
    }
    
    return buffer.toString();
  }

  bool _isWhitespace(String char) {
    return char == ' ' || char == '\t' || char == '\n' || char == '\r';
  }

  bool _isSpecialChar(String char) {
    return '()+-*/%=<>!&|;'.contains(char);
  }

  bool _isTwoCharOperator(String op) {
    return const {'=>', '==', '!=', '<=', '>=', '%='}.contains(op);
  }

  String _peek() {
    if (_pos >= _tokens.length) return '';
    return _tokens[_pos];
  }

  String _consume() {
    if (_pos >= _tokens.length) return '';
    return _tokens[_pos++];
  }

  bool _match(String expected) {
    if (_peek() == expected) {
      _consume();
      return true;
    }
    return false;
  }

  Expr _parseExpr() {
    if (_peek() == 'type') {
      return _parseTypeDeclaration();
    }
    if (_peek() == 'match' && _pos == 0) {
      return _parseMatch();
    }
    return _parseLoop();
  }

  Expr _parseLet() {
    if (_match('let')) {
      // Check for recursive let (let rec)
      if (_peek() == 'rec') {
        _consume(); // consume 'rec'
        final funcName = _consume();
        if (!_match('=')) throw FormatException('Expected = after recursive function name');
        final value = _parseExpr(); // This will parse the lambda
        
        if (!_match('in')) throw FormatException('Expected in after recursive function');
        final body = _parseExpr();
        
        // Extract param and body from the lambda
        if (value is Lambda) {
          return Rec(funcName, value.param, value.body, body, 0, 0);
        } else {
          throw FormatException('Recursive binding must be a function');
        }
      }
      
      // Normal let (non-recursive)
      final varName = _consume();
      if (!_match('=')) throw FormatException('Expected = after variable name');
      final value = _parseExpr();
      
      // Check if this is REPL mode (no 'in')
      if (_pos >= _tokens.length) {
        return ReplLet(varName, value, _currentLine, _currentColumn);
      }
      
      // Check for 'in' keyword
      if (_peek() == 'in') {
        _consume(); // consume 'in'
        final body = _parseExpr();
        return Let(varName, value, body, _currentLine, _currentColumn);
      } else {
        // No 'in' - REPL mode
        return ReplLet(varName, value, _currentLine, _currentColumn);
      }
    }
    return _parseFunction();
  }

  Expr _parseFunction() {
    if (_match('fn')) {
      final param = _consume();
      if (!_match('=>')) throw FormatException('Expected => after parameter');
      final body = _parseExpr();
      return Lambda(param, body, _currentLine, _currentColumn);
    }
    return _parseIf();
  }

  Expr _parseIf() {
    if (_match('if')) {
      final condition = _parseLogical();
      if (!_match('then')) throw FormatException('Expected then after condition');
      final thenBranch = _parseExpr();
      if (!_match('else')) throw FormatException('Expected else after then branch');
      final elseBranch = _parseExpr();
      return If(condition, thenBranch, elseBranch, _currentLine, _currentColumn);
    }
    return _parseLogical();
  }

  Expr _parseLogical() {
    var expr = _parseComparison();
    
    while (_isLogicalOperator(_peek())) {
      final op = _consume();
      final right = _parseComparison();
      expr = BinaryOp(op, expr, right, _currentLine, _currentColumn);
    }
    
    return expr;
  }

  Expr _parseAdditive() {
    var expr = _parseMultiplicative();
    
    while (_peek() == '+' || _peek() == '-') {
      final op = _consume();
      final right = _parseMultiplicative();
      expr = BinaryOp(op, expr, right, _currentLine, _currentColumn);
    }
    
    return expr;
  }

  Expr _parseMultiplicative() {
    var expr = _parseApplication();
    
    while (_peek() == '*' || _peek() == '/' || _peek() == '%') {
      final op = _consume();
      final right = _parseApplication();
      expr = BinaryOp(op, expr, right, _currentLine, _currentColumn);
    }
    
    return expr;
  }

  Expr _parseApplication() {
    var expr = _parseAtomic();
    
    // Handle function application
    while (_pos < _tokens.length && 
           _peek() != ')' && 
           _peek() != 'in' && 
           _peek() != 'then' && 
           _peek() != 'else' &&
           !_isOperator(_peek())) {
      final next = _parseAtomic();
      expr = Apply(expr, next, _currentLine, _currentColumn);
    }
    
    return expr;
  }

  Expr _parseAtomic() {
    // Check for unary minus
    if (_peek() == '-') {
      _consume(); // consume the '-'
      final expr = _parseAtomic();
      // Create a unary minus operation: -expr = 0 - expr
      return BinaryOp('-', IntLit(0, _currentLine, _currentColumn), expr, _currentLine, _currentColumn);
    }
    
    final token = _consume();
    
    if (token.isEmpty) {
      throw FormatException('Unexpected end of input');
    }
    
    // Check for lists and pairs
    if (token.startsWith('[') && token.endsWith(']')) {
      return _parseListFromToken(token);
    }
    
    if (token.startsWith('(,') && token.endsWith(')')) {
      return _parsePairFromToken(token);
    }

    // Check for tuples
    if (token.startsWith('(') && token.endsWith(')') && !token.startsWith('(,')) {
      final content = token.substring(1, token.length - 1).trim();
      if (content.contains(',')) {
        return _parseTupleFromToken(token);
      }
    }

    // Check for tuple access
    if (token == '_1' || token == '_2' || token == '_3') {
      final index = int.parse(token.substring(1));
      final tuple = _parseAtomic();
      return TupleAccess(tuple, index, 0, 0);
    }

    // Check for records
    if (token.startsWith('{') && token.endsWith('}')) {
      return _parseRecordFromToken(token);
    }

    // Check for record access
    if (token.contains('.')) {
      final parts = token.split('.');
      if (parts.length == 2) {
        final recordParser = SimpleParser();
        final record = recordParser.parse(parts[0]);
        return RecordAccess(record, parts[1], 0, 0);
      }
    }

    if (token == 'left') {
      final value = _parseAtomic();
      return Left(value, _currentLine, _currentColumn);
    }
    if (token == 'right') {
      final value = _parseAtomic();
      return Left(value, _currentLine, _currentColumn);
    }
    
    // Check for first, second, head, tail operations
    if (token == 'first') {
      final pair = _parseAtomic();
      return First(pair, _currentLine, _currentColumn);
    }
    if (token == 'second') {
      final pair = _parseAtomic();
      return Second(pair, _currentLine, _currentColumn);
    }
    if (token == 'head') {
      final list = _parseAtomic();
      return Head(list, _currentLine, _currentColumn);
    }
    if (token == 'tail') {
      final list = _parseAtomic();
      return Tail(list, _currentLine, _currentColumn);
    }
    
    // Check if it's a string
    if (token.startsWith('"') && token.endsWith('"')) {
      return StringLit(token.substring(1, token.length - 1), _currentLine, _currentColumn);
    }
    
    // Check if it's an integer
    final intValue = int.tryParse(token);
    if (intValue != null) {
      return IntLit(intValue, _currentLine, _currentColumn);
    }
    
    // Check if it's a boolean
    if (token == 'true') {
      return BoolLit(true, _currentLine, _currentColumn);
    }
    if (token == 'false') {
      return BoolLit(false, _currentLine, _currentColumn);
    }
    
    // Check if it's a parenthesized expression
    if (token == '(') {
      final expr = _parseExpr();
      if (!_match(')')) throw FormatException('Expected )');
      return expr;
    }

    // Check if token looks like a list pattern
    if (token.startsWith('[') || (_pos > 0 && _tokens[_pos - 1] == '[')) {
      // Try to parse as list
      try {
        final listParser = SimpleParser();
        return listParser.parse(token);
      } catch (e) {
        // If parsing fails, continue as variable
      }
    }
    
    // Otherwise it's a variable
    return Var(token, _currentLine, _currentColumn);
  }

  Expr _parseListFromToken(String token) {
    // Remove brackets and parse content
    final content = token.substring(1, token.length - 1).trim();
    if (content.isEmpty) {
      return Nil(_currentLine, _currentColumn);
    }
    
    // Simple parsing for now - just split by commas
    final elements = content.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    
    // Build list from right to left
    Expr list = Nil(0, 0);
    for (int i = elements.length - 1; i >= 0; i--) {
      // Create a temporary parser to parse each element
      final elementParser = SimpleParser();
      final elementExpr = elementParser.parse(elements[i]);
      list = Cons(elementExpr, list, _currentLine, _currentColumn);
    }
    
    return list;
  }

  Expr _parsePairFromToken(String token) {
    // Remove parentheses and parse content: (, a, b) -> a, b
    final content = token.substring(2, token.length - 1).trim();
    final parts = content.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    
    if (parts.length != 2) {
      throw FormatException('Pair must have exactly two elements');
    }
    
    final firstParser = SimpleParser();
    final secondParser = SimpleParser();
    
    final first = firstParser.parse(parts[0]);
    final second = secondParser.parse(parts[1]);
    
    return Pair(first, second, _currentLine, _currentColumn);
  }

  Expr _parseTupleFromToken(String token) {
    final content = token.substring(1, token.length - 1).trim();
    final elements = content.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    
    final elementExprs = <Expr>[];
    for (final element in elements) {
      final elementParser = SimpleParser();
      final elementExpr = elementParser.parse(element);
      elementExprs.add(elementExpr);
    }
    
    return Tuple(elementExprs, _currentLine, _currentColumn);
  }

  Expr _parseRecordFromToken(String token) {
    final content = token.substring(1, token.length - 1).trim();
    final fields = <String, Expr>{};
    
    if (content.isNotEmpty) {
      final fieldPairs = content.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
      for (final pair in fieldPairs) {
        final colonIndex = pair.indexOf(':');
        if (colonIndex == -1) throw FormatException('Record field must have :');
        
        final fieldName = pair.substring(0, colonIndex).trim();
        final fieldValue = pair.substring(colonIndex + 1).trim();
        
        final valueParser = SimpleParser();
        final valueExpr = valueParser.parse(fieldValue);
        
        fields[fieldName] = valueExpr;
      }
    }
    
    return Record(fields, _currentLine, _currentColumn);
  }

  Expr _parseLoop() {
    if (_match('while')) {
      String conditionToken = _consume();
      
      // Handle boolean literals
      if (conditionToken == 'true') {
        if (!_match('do')) throw FormatException('Expected "do"');
        final body = _parseExpr();
        return WhileLoop(BoolLit(true, _currentLine, _currentColumn), body, _currentLine, _currentColumn);
      }
      else if (conditionToken == 'false') {
        if (!_match('do')) throw FormatException('Expected "do"');
        final body = _parseExpr();
        return WhileLoop(BoolLit(false, _currentLine, _currentColumn), body, _currentLine, _currentColumn);
      }
      // Handle variables as conditions
      else {
        if (!_match('do')) throw FormatException('Expected "do"');
        final body = _parseExpr();
        return WhileLoop(Var(conditionToken, _currentLine, _currentColumn), body, _currentLine, _currentColumn);
      }
    }
    
    if (_match('for')) {
      final variable = _consume();
      if (!_match('from')) throw FormatException('Expected "from" after for variable');
      
      // Parse start value
      String startToken = _consume();
      final start = IntLit(int.parse(startToken), _currentLine, _currentColumn);
      
      if (!_match('to')) throw FormatException('Expected "to" after start value');
      
      // Parse end value  
      String endToken = _consume();
      final end = IntLit(int.parse(endToken), _currentLine, _currentColumn);
      
      if (!_match('do')) throw FormatException('Expected "do" after for range');
      final body = _parseExpr();
      
      return ForLoop(variable, start, end, body, _currentLine, _currentColumn);
    }
    
    return _parseLet();
  }

  Expr _parseComparison() {
    var expr = _parseAdditive();
    
    while (_isComparisonOperator(_peek())) {
      final op = _consume();
      final right = _parseAdditive();
      expr = BinaryOp(op, expr, right, _currentLine, _currentColumn);
    }
    
    return expr;
  }

  Expr _parseTypeDeclaration() {
    if (_match('type')) {
      final typeName = _consume();
      if (!_match('=')) throw FormatException('Expected = after type name');
      
      final constructors = <ConstructorDef>[];
      do {
        final constrName = _consume();
        final parameters = <String>[];
        
        // Parse parameters until we hit | or end
        while (_pos < _tokens.length && _peek() != '|' && _peek() != '') {
          parameters.add(_consume());
        }
        
        constructors.add(ConstructorDef(constrName, parameters));
      } while (_match('|'));
      
      return TypeDeclaration(typeName, constructors, _currentLine, _currentColumn);
    }
    return _parseLoop();
  }

  bool _isComparisonOperator(String token) {
    return const {'==', '!=', '<', '>', '<=', '>='}.contains(token);
  }

  bool _isOperator(String token) {
    return const {'+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', '=>'}.contains(token);
  }

  bool _isLogicalOperator(String token) {
    return const {'==', '!=', '<', '>', '<=', '>='}.contains(token);
  }
}