import 'package:shared_preferences/shared_preferences.dart';

class SettingsService {
  static const _kApiBaseUrl = 'api_base_url';
  static const _kSyncToken = 'sync_api_token';
  static const _kSelectedBusinessId = 'selected_business_id';
  static const _kCompanyId = 'company_id';

  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  SharedPreferences get _p {
    final prefs = _prefs;
    if (prefs == null) {
      throw StateError('SettingsService not initialized. Call init() first.');
    }
    return prefs;
  }

  String get apiBaseUrl => _p.getString(_kApiBaseUrl) ?? '';
  Future<void> setApiBaseUrl(String value) => _p.setString(_kApiBaseUrl, value.trim());

  String get syncToken => _p.getString(_kSyncToken) ?? '';
  Future<void> setSyncToken(String value) => _p.setString(_kSyncToken, value.trim());

  String get selectedBusinessId => _p.getString(_kSelectedBusinessId) ?? '';
  Future<void> setSelectedBusinessId(String value) => _p.setString(_kSelectedBusinessId, value.trim());

  String get companyId => _p.getString(_kCompanyId) ?? '';
  Future<void> setCompanyId(String value) => _p.setString(_kCompanyId, value.trim());
}
