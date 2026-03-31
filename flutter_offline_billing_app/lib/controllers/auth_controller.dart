import 'package:get/get.dart';

import '../models/user_model.dart';
import '../services/auth_service.dart';

class AuthController extends GetxController {
  AuthController({
    required AuthService auth,
  }) : _auth = auth;

  final AuthService _auth;

  final Rxn<UserModel> currentUser = Rxn<UserModel>();
  final RxBool isBusy = false.obs;
  final RxString error = ''.obs;

  @override
  void onInit() {
    super.onInit();
    bootstrap();
  }

  Future<void> bootstrap() async {
    isBusy.value = true;
    error.value = '';
    try {
      currentUser.value = await _auth.bootstrap();
    } catch (e) {
      error.value = e.toString();
    } finally {
      isBusy.value = false;
    }
  }

  Future<void> login({
    required String username,
    required String password,
  }) async {
    isBusy.value = true;
    error.value = '';
    try {
      currentUser.value = await _auth.login(username: username, password: password);
    } catch (e) {
      error.value = e.toString();
      rethrow;
    } finally {
      isBusy.value = false;
    }
  }

  Future<void> logout() async {
    await _auth.logout();
    currentUser.value = null;
  }
}
