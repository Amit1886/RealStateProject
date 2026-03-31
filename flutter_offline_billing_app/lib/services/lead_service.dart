import 'api_service.dart';

class LeadService {
  LeadService(this._api);

  final ApiService _api;

  Future<List<Map<String, dynamic>>> fetchLeads() async {
    final payload = await _api.getAny('/api/v1/leads/leads/');
    if (payload is List) {
      return payload.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
    }
    if (payload is Map<String, dynamic> && payload['results'] is List) {
      return (payload['results'] as List)
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }
    return <Map<String, dynamic>>[];
  }
}
