import 'package:get/get.dart';

import '../../controllers/auth_controller.dart';
import '../../controllers/real_estate_controller.dart';
import '../../controllers/settings_controller.dart';
import '../../services/auth_service.dart';
import '../../services/real_estate_service.dart';
import '../../services/settings_service.dart';

class AppBinding extends Bindings {
  @override
  void dependencies() {
    Get.put(SettingsController(Get.find<SettingsService>()), permanent: true);
    Get.put(
      AuthController(auth: Get.find<AuthService>()),
      permanent: true,
    );
    Get.put(
      RealEstateController(service: Get.find<RealEstateService>()),
      permanent: true,
    );
  }
}
