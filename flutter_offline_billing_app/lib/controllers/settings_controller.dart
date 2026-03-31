import 'package:get/get.dart';

import '../services/settings_service.dart';

class SettingsController extends GetxController {
  SettingsController(this._settings);

  final SettingsService _settings;

  final RxString apiBaseUrl = ''.obs;
  final RxString companyId = ''.obs;

  @override
  void onInit() {
    super.onInit();
    apiBaseUrl.value = _settings.apiBaseUrl;
    companyId.value = _settings.companyId;
  }

  Future<void> save({
    required String baseUrl,
    required String company,
  }) async {
    await _settings.setApiBaseUrl(baseUrl);
    await _settings.setCompanyId(company);
    apiBaseUrl.value = _settings.apiBaseUrl;
    companyId.value = _settings.companyId;
  }
}
