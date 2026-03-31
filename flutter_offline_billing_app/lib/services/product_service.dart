import '../database/local_db.dart';
import '../database/tables.dart';
import '../models/product_model.dart';
import 'id_service.dart';

class ProductService {
  ProductService(this._db);

  final LocalDb _db;

  Future<List<ProductModel>> list({
    required String businessId,
    String? query,
  }) async {
    final where = <String>['business_id = ?', 'is_deleted = 0'];
    final args = <Object?>[businessId];
    if (query != null && query.trim().isNotEmpty) {
      where.add('name LIKE ?');
      args.add('%${query.trim()}%');
    }
    final rows = await _db.query(
      Tables.products,
      where: where.join(' AND '),
      whereArgs: args,
      orderBy: 'updated_at DESC',
      limit: 800,
    );
    return rows.map(ProductModel.fromMap).toList();
  }

  Future<ProductModel> create({
    required String businessId,
    required String name,
    String? sku,
    String? barcode,
    String? category,
    String? unit,
    double salePrice = 0,
    double purchasePrice = 0,
    double taxPercent = 0,
    double stockQty = 0,
  }) async {
    final trimmedName = name.trim();
    if (trimmedName.isEmpty) throw Exception('Product name is required');
    if (salePrice < 0 || purchasePrice < 0) throw Exception('Price must be >= 0');
    if (taxPercent < 0 || taxPercent > 100) throw Exception('Tax must be between 0 and 100');

    final now = DateTime.now();
    final obj = ProductModel(
      id: IdService.newId(),
      businessId: businessId,
      name: trimmedName,
      sku: sku?.trim().isEmpty ?? true ? null : sku?.trim(),
      barcode: barcode?.trim().isEmpty ?? true ? null : barcode?.trim(),
      category: category?.trim().isEmpty ?? true ? null : category?.trim(),
      unit: unit?.trim().isEmpty ?? true ? null : unit?.trim(),
      salePrice: salePrice,
      purchasePrice: purchasePrice,
      taxPercent: taxPercent,
      stockQty: stockQty,
      createdAt: now,
      updatedAt: now,
      isSynced: false,
      isDeleted: false,
    );
    await _db.upsert(Tables.products, obj.toMap());
    return obj;
  }

  Future<void> update(ProductModel product) async {
    final updated = product.copyWith(updatedAt: DateTime.now(), isSynced: false);
    await _db.upsert(Tables.products, updated.toMap());
  }

  Future<void> delete({required String productId}) async {
    await _db.softDeleteById(Tables.products, productId);
  }
}

