import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'core/bindings/app_binding.dart';
import 'core/theme/app_theme.dart';
import 'screens/root_screen.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';
import 'services/real_estate_service.dart';
import 'services/secure_storage_service.dart';
import 'services/settings_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settings = SettingsService();
  await settings.init();

  final secure = SecureStorageService();
  final api = ApiService(settings: settings, secure: secure);

  Get.put<SettingsService>(settings, permanent: true);
  Get.put<SecureStorageService>(secure, permanent: true);
  Get.put<ApiService>(api, permanent: true);
  Get.put<AuthService>(
    AuthService(api: api, secureStorage: secure, settings: settings),
    permanent: true,
  );
  Get.put<RealEstateService>(RealEstateService(api), permanent: true);

  runApp(const PropFlowMobileApp());
}

class PropFlowMobileApp extends StatelessWidget {
  const PropFlowMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      initialBinding: AppBinding(),
      home: const RootScreen(),
    );
  }
}
