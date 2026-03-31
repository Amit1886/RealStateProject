import '../database/local_db.dart';
import '../database/tables.dart';
import '../models/party_model.dart';
import 'id_service.dart';

class PartyService {
  PartyService(this._db);

  final LocalDb _db;

  Future<List<PartyModel>> list({
    required String businessId,
    String? type, // customer | supplier | null (all)
    String? query,
  }) async {
    final where = <String>['business_id = ?', 'is_deleted = 0'];
    final args = <Object?>[businessId];
    if (type != null && type.isNotEmpty) {
      where.add('type = ?');
      args.add(type);
    }
    if (query != null && query.trim().isNotEmpty) {
      where.add('name LIKE ?');
      args.add('%${query.trim()}%');
    }
    final rows = await _db.query(
      Tables.parties,
      where: where.join(' AND '),
      whereArgs: args,
      orderBy: 'updated_at DESC',
      limit: 500,
    );
    return rows.map(PartyModel.fromMap).toList();
  }

  Future<PartyModel> create({
    required String businessId,
    required String type,
    required String name,
    String? phone,
    String? address,
    String? gstin,
    double openingBalance = 0,
  }) async {
    final now = DateTime.now();
    final party = PartyModel(
      id: IdService.newId(),
      businessId: businessId,
      type: type,
      name: name.trim(),
      phone: phone?.trim().isEmpty ?? true ? null : phone?.trim(),
      address: address?.trim().isEmpty ?? true ? null : address?.trim(),
      gstin: gstin?.trim().isEmpty ?? true ? null : gstin?.trim(),
      openingBalance: openingBalance,
      createdAt: now,
      updatedAt: now,
      isSynced: false,
      isDeleted: false,
    );
    await _db.upsert(Tables.parties, party.toMap());
    return party;
  }

  Future<void> update(PartyModel party) async {
    final updated = party.copyWith(updatedAt: DateTime.now(), isSynced: false);
    await _db.upsert(Tables.parties, updated.toMap());
  }

  Future<void> delete({required String partyId}) async {
    await _db.softDeleteById(Tables.parties, partyId);
  }
}

