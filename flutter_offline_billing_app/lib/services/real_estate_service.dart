import 'api_service.dart';

class RealEstateService {
  RealEstateService(this._api);

  final ApiService _api;

  List<Map<String, dynamic>> _list(dynamic payload) {
    if (payload is List) {
      return payload.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
    }
    if (payload is Map<String, dynamic>) {
      final results = payload['results'];
      if (results is List) {
        return results.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
      }
      final items = payload['items'];
      if (items is List) {
        return items.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
      }
      final data = payload['data'];
      if (data is List) {
        return data.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
      }
    }
    return <Map<String, dynamic>>[];
  }

  Map<String, dynamic> _map(dynamic payload) {
    if (payload is Map<String, dynamic>) return payload;
    return <String, dynamic>{};
  }

  Future<Map<String, dynamic>> fetchMe() async => _map(await _api.getAny('/api/v1/users/me/'));
  Future<Map<String, dynamic>> fetchSummary() async => _map(await _api.getAny('/api/v1/reports/summary/'));
  Future<Map<String, dynamic>> fetchLeadDashboard() async => _map(await _api.getAny('/api/v1/leads/leads/dashboard_summary/'));
  Future<List<Map<String, dynamic>>> fetchLeads() async => _list(await _api.getAny('/api/v1/leads/leads/'));
  Future<List<Map<String, dynamic>>> fetchProperties() async => _list(await _api.getAny('/api/v1/leads/properties/'));
  Future<List<Map<String, dynamic>>> fetchWishlist() async => _list(await _api.getAny('/api/v1/leads/properties/my_wishlist/'));
  Future<List<Map<String, dynamic>>> fetchVisits() async => _list(await _api.getAny('/api/v1/visits/visits/'));
  Future<List<Map<String, dynamic>>> fetchAgents() async => _list(await _api.getAny('/api/v1/agents/agents/'));
  Future<List<Map<String, dynamic>>> fetchWallets() async => _list(await _api.getAny('/api/v1/wallet/wallets/'));
  Future<List<Map<String, dynamic>>> fetchTransactions() async => _list(await _api.getAny('/api/v1/wallet/transactions/'));
  Future<List<Map<String, dynamic>>> fetchWithdrawRequests() async => _list(await _api.getAny('/api/v1/wallet/withdraw-requests/'));
  Future<List<Map<String, dynamic>>> fetchPlans() async => _list(await _api.getAny('/api/v1/subscription/plans/'));
  Future<List<Map<String, dynamic>>> fetchSubscriptions() async => _list(await _api.getAny('/api/v1/subscription/subscriptions/'));
  Future<List<Map<String, dynamic>>> fetchNotifications() async => _list(await _api.getAny('/api/v1/notifications/notifications/'));

  Future<void> createLead(Map<String, Object?> payload) async {
    await _api.postAny('/api/v1/leads/leads/', payload);
  }

  Future<void> updateLeadStatus(String leadId, String status) async {
    await _api.postAny(
      '/api/v1/leads/leads/$leadId/status/',
      {'status': status},
    );
  }

  Future<void> createProperty(Map<String, Object?> payload) async {
    await _api.postAny('/api/v1/leads/properties/', payload);
  }

  Future<void> toggleWishlist(String propertyId) async {
    await _api.postAny('/api/v1/leads/properties/$propertyId/wishlist/', const <String, Object?>{});
  }

  Future<void> scheduleVisit(String propertyId, {String notes = ''}) async {
    final visitDate = DateTime.now().add(const Duration(days: 1)).toIso8601String();
    await _api.postAny(
      '/api/v1/leads/properties/$propertyId/schedule_visit/',
      {
        'visit_date': visitDate,
        'notes': notes,
      },
    );
  }

  Future<void> requestWithdrawal(String amount) async {
    await _api.postAny(
      '/api/v1/wallet/withdraw-requests/',
      {'amount': amount},
    );
  }

  Future<void> subscribeToPlan(String planId) async {
    await _api.postAny(
      '/api/v1/subscription/subscriptions/',
      {'plan': planId},
    );
  }

  Future<void> activateFreePlan() async {
    await _api.postAny('/api/v1/subscription/subscriptions/free/', const <String, Object?>{});
  }

  Future<void> markAllNotificationsRead() async {
    await _api.postAny('/api/v1/notifications/notifications/mark_all_read/', const <String, Object?>{});
  }
}
