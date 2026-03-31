import 'dart:async';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import 'tables.dart';

/// Local offline database (SQFlite).
///
/// Design goals:
/// - App works fully offline.
/// - All write operations are saved locally first.
/// - Each row includes `created_at`, `updated_at`, `is_synced` (and soft delete flag)
///   to support sync.
class LocalDb {
  LocalDb._();

  static final LocalDb instance = LocalDb._();

  static const _dbName = 'jaistech_billing.db';
  static const _dbVersion = 2;

  Database? _db;

  Future<Database> get database async {
    final existing = _db;
    if (existing != null) return existing;
    _db = await _open();
    return _db!;
  }

  Future<Database> _open() async {
    final dir = await getApplicationDocumentsDirectory();
    final path = p.join(dir.path, _dbName);

    return openDatabase(
      path,
      version: _dbVersion,
      onConfigure: (db) async {
        await db.execute('PRAGMA foreign_keys = ON');
      },
      onCreate: (db, version) async {
        await _createTables(db);
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        // Add schema migrations here when bumping `_dbVersion`.
        if (oldVersion < 2) {
          // Offline auth support (local password hash).
          try {
            await db.execute('ALTER TABLE ${Tables.users} ADD COLUMN password_salt TEXT;');
          } catch (_) {}
          try {
            await db.execute('ALTER TABLE ${Tables.users} ADD COLUMN password_hash TEXT;');
          } catch (_) {}
        }
      },
    );
  }

  Future<void> _createTables(Database db) async {
    // Users (cached profile; auth tokens are stored in secure storage).
    await db.execute('''
CREATE TABLE ${Tables.users} (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  password_salt TEXT,
  password_hash TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 1,
  is_deleted INTEGER NOT NULL DEFAULT 0
);
''');

    // Multi-business support.
    await db.execute('''
CREATE TABLE ${Tables.businesses} (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  address TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES ${Tables.users}(id) ON DELETE CASCADE
);
''');
    await db.execute('CREATE INDEX idx_businesses_user ON ${Tables.businesses}(user_id);');

    // Parties (customers + suppliers).
    await db.execute('''
CREATE TABLE ${Tables.parties} (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  type TEXT NOT NULL, /* customer | supplier */
  name TEXT NOT NULL,
  phone TEXT,
  address TEXT,
  gstin TEXT,
  opening_balance REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (business_id) REFERENCES ${Tables.businesses}(id) ON DELETE CASCADE
);
''');
    await db.execute('CREATE INDEX idx_parties_business ON ${Tables.parties}(business_id);');
    await db.execute('CREATE INDEX idx_parties_type ON ${Tables.parties}(type);');

    // Products / Inventory.
    await db.execute('''
CREATE TABLE ${Tables.products} (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  name TEXT NOT NULL,
  sku TEXT,
  barcode TEXT,
  category TEXT,
  unit TEXT,
  sale_price REAL NOT NULL DEFAULT 0,
  purchase_price REAL NOT NULL DEFAULT 0,
  tax_percent REAL NOT NULL DEFAULT 0,
  stock_qty REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (business_id) REFERENCES ${Tables.businesses}(id) ON DELETE CASCADE
);
''');
    await db.execute('CREATE INDEX idx_products_business ON ${Tables.products}(business_id);');
    await db.execute('CREATE INDEX idx_products_barcode ON ${Tables.products}(barcode);');

    // Invoices (sales/purchase).
    await db.execute('''
CREATE TABLE ${Tables.invoices} (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  party_id TEXT NOT NULL,
  type TEXT NOT NULL, /* sale | purchase */
  number TEXT NOT NULL,
  date TEXT NOT NULL,
  status TEXT NOT NULL,
  subtotal REAL NOT NULL,
  discount REAL NOT NULL,
  tax REAL NOT NULL,
  total REAL NOT NULL,
  paid REAL NOT NULL,
  balance REAL NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (business_id) REFERENCES ${Tables.businesses}(id) ON DELETE CASCADE,
  FOREIGN KEY (party_id) REFERENCES ${Tables.parties}(id) ON DELETE RESTRICT
);
''');
    await db.execute('CREATE INDEX idx_invoices_business ON ${Tables.invoices}(business_id);');
    await db.execute('CREATE INDEX idx_invoices_party ON ${Tables.invoices}(party_id);');
    await db.execute('CREATE INDEX idx_invoices_date ON ${Tables.invoices}(date);');

    // Invoice Items.
    await db.execute('''
CREATE TABLE ${Tables.invoiceItems} (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  product_id TEXT,
  name TEXT NOT NULL,
  qty REAL NOT NULL,
  unit_price REAL NOT NULL,
  discount REAL NOT NULL DEFAULT 0,
  tax_percent REAL NOT NULL DEFAULT 0,
  line_total REAL NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (invoice_id) REFERENCES ${Tables.invoices}(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES ${Tables.products}(id) ON DELETE RESTRICT
);
''');
    await db.execute('CREATE INDEX idx_items_invoice ON ${Tables.invoiceItems}(invoice_id);');

    // Transactions (payments in/out, adjustments).
    await db.execute('''
CREATE TABLE ${Tables.transactions} (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  party_id TEXT,
  invoice_id TEXT,
  type TEXT NOT NULL, /* payment_in | payment_out | adjustment */
  amount REAL NOT NULL,
  mode TEXT NOT NULL, /* cash | upi | bank | card | other */
  reference TEXT,
  date TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (business_id) REFERENCES ${Tables.businesses}(id) ON DELETE CASCADE,
  FOREIGN KEY (party_id) REFERENCES ${Tables.parties}(id) ON DELETE SET NULL,
  FOREIGN KEY (invoice_id) REFERENCES ${Tables.invoices}(id) ON DELETE SET NULL
);
''');
    await db.execute('CREATE INDEX idx_txn_business ON ${Tables.transactions}(business_id);');
    await db.execute('CREATE INDEX idx_txn_party ON ${Tables.transactions}(party_id);');
    await db.execute('CREATE INDEX idx_txn_date ON ${Tables.transactions}(date);');

    // Expenses.
    await db.execute('''
CREATE TABLE ${Tables.expenses} (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  category TEXT,
  amount REAL NOT NULL,
  date TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_synced INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (business_id) REFERENCES ${Tables.businesses}(id) ON DELETE CASCADE
);
''');
    await db.execute('CREATE INDEX idx_expenses_business ON ${Tables.expenses}(business_id);');
    await db.execute('CREATE INDEX idx_expenses_date ON ${Tables.expenses}(date);');

    // Sync state key-value store.
    await db.execute('''
CREATE TABLE ${Tables.syncState} (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
''');
  }

  Future<int> upsert(String table, Map<String, Object?> row, {Transaction? txn}) async {
    final db = txn ?? await database;
    return db.insert(table, row, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<int> updateById(String table, String id, Map<String, Object?> values, {Transaction? txn}) async {
    final db = txn ?? await database;
    return db.update(table, values, where: 'id = ?', whereArgs: [id]);
  }

  Future<int> hardDeleteById(String table, String id, {Transaction? txn}) async {
    final db = txn ?? await database;
    return db.delete(table, where: 'id = ?', whereArgs: [id]);
  }

  Future<int> softDeleteById(String table, String id, {Transaction? txn}) async {
    final now = DateTime.now().toIso8601String();
    return updateById(
      table,
      id,
      {
        'is_deleted': 1,
        'is_synced': 0,
        'updated_at': now,
      },
      txn: txn,
    );
  }

  Future<List<Map<String, Object?>>> query(
    String table, {
    String? where,
    List<Object?>? whereArgs,
    String? orderBy,
    int? limit,
  }) async {
    final db = await database;
    return db.query(table, where: where, whereArgs: whereArgs, orderBy: orderBy, limit: limit);
  }

  Future<List<Map<String, Object?>>> rawQuery(String sql, [List<Object?>? args]) async {
    final db = await database;
    return db.rawQuery(sql, args);
  }

  Future<T> transaction<T>(Future<T> Function(Transaction txn) action) async {
    final db = await database;
    return db.transaction(action);
  }

  Future<void> close() async {
    final db = _db;
    _db = null;
    if (db == null) return;
    await db.close();
  }
}
