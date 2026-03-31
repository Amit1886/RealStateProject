import 'dart:math';

/// Generates stable offline IDs without needing internet/server.
/// Using string IDs avoids conflicts during sync.
class IdService {
  IdService._();

  static final _rand = Random.secure();

  static String newId() {
    final ts = DateTime.now().microsecondsSinceEpoch;
    final r1 = _rand.nextInt(1 << 32).toRadixString(16).padLeft(8, '0');
    final r2 = _rand.nextInt(1 << 32).toRadixString(16).padLeft(8, '0');
    return '$ts-$r1$r2';
  }
}

