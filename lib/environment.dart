class Environment {
  final Map<String, dynamic> bindings;
  final Environment? parent;

  Environment({this.parent}) : bindings = {};

  void bind(String name, dynamic value) {
    bindings[name] = value;
  }

  dynamic lookup(String name) {
    if (bindings.containsKey(name)) {
      return bindings[name];
    }
    if (parent != null) {
      return parent!.lookup(name);
    }
    throw Exception('Unbound variable: $name');
  }

  Environment createChild() {
    return Environment(parent: this);
  }
}