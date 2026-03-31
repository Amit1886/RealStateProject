import '../models/user_model.dart';
import 'api_service.dart';
import 'secure_storage_service.dart';
import 'settings_service.dart';

class AuthException implements Exception {
  AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

class AuthService {
  AuthService({
    required ApiService api,
    required SecureStorageService secureStorage,
    required SettingsService settings,
  })  : _api = api,
        _secure = secureStorage,
        _settings = settings;

  final ApiService _api;
  final SecureStorageService _secure;
  final SettingsService _settings;

  Future<UserModel?> bootstrap() async {
    final access = await _secure.getAccessToken();
    if (access.isEmpty) return null;

    try {
      final payload = await _api.getAny('/api/v1/users/me/');
      if (payload is! Map<String, dynamic>) {
        throw AuthException('Unexpected user profile response');
      }
      return _persistProfile(
        payload,
        accessToken: access,
        refreshToken: await _secure.getRefreshToken(),
      );
    } catch (_) {
      await logout();
      return null;
    }
  }

  Future<UserModel> login({
    required String username,
    required String password,
  }) async {
    final email = username.trim();
    if (email.isEmpty) throw AuthException('Email is required');
    if (password.isEmpty) throw AuthException('Password is required');

    final tokenPayload = await _api.postAny(
      '/api/auth/token/',
      {
        'email': email,
        'password': password,
      },
    );

    if (tokenPayload is! Map<String, dynamic>) {
      throw AuthException('Login failed: invalid token response');
    }

    final access = (tokenPayload['access'] ?? '').toString();
    final refresh = (tokenPayload['refresh'] ?? '').toString();
    if (access.isEmpty || refresh.isEmpty) {
      throw AuthException('Login failed: access token missing');
    }

    final profilePayload = await _api.getAny(
      '/api/v1/users/me/',
      tokenOverride: access,
    );
    if (profilePayload is! Map<String, dynamic>) {
      throw AuthException('Login failed: user profile missing');
    }

    return _persistProfile(
      profilePayload,
      accessToken: access,
      refreshToken: refresh,
    );
  }

  Future<void> logout() async {
    await _settings.setCompanyId('');
    await _secure.clearSession();
  }

  Future<UserModel> _persistProfile(
    Map<String, dynamic> profile, {
    required String accessToken,
    required String refreshToken,
  }) async {
    final user = UserModel.fromJson(profile);
    final companyId = (profile['company'] ?? '').toString();
    await _settings.setCompanyId(companyId);
    await _secure.setSession(
      accessToken: accessToken,
      refreshToken: refreshToken,
      userId: user.id,
      email: user.email,
      name: user.name,
    );
    return user;
  }
}
