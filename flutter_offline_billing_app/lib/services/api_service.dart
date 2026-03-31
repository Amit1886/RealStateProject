import 'dart:convert';

import 'package:http/http.dart' as http;

import 'secure_storage_service.dart';
import 'settings_service.dart';

class ApiException implements Exception {
  ApiException({
    required this.method,
    required this.url,
    required this.statusCode,
    required this.body,
  });

  final String method;
  final Uri url;
  final int statusCode;
  final String body;

  @override
  String toString() => 'API $method $url failed ($statusCode): $body';
}

/// HTTP API client.
///
/// - Uses `SettingsService.apiBaseUrl`
/// - Adds `Authorization` header when token is available
/// - Supports both:
///   - Bearer <accessToken>  (JWT)
///   - Token <syncToken>     (shared-token sync, if enabled)
class ApiService {
  ApiService({
    required SettingsService settings,
    required SecureStorageService secure,
  })  : _settings = settings,
        _secure = secure;

  final SettingsService _settings;
  final SecureStorageService _secure;

  Uri _uri(String path, [Map<String, String>? query]) {
    final baseUrl = _settings.apiBaseUrl.trim();
    if (baseUrl.isEmpty) {
      throw StateError('API base URL is empty. Set it in Settings.');
    }
    final clean = path.startsWith('/') ? path : '/$path';
    final parsed = Uri.parse(baseUrl);
    return parsed.replace(path: '${parsed.path}$clean', queryParameters: query);
  }

  Future<Map<String, String>> _headers({String? tokenOverride, bool useSyncToken = false}) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    final companyId = _settings.companyId;
    if (companyId.isNotEmpty) {
      headers['X-Company-ID'] = companyId;
    }

    final token = tokenOverride ??
        (useSyncToken ? _settings.syncToken : await _secure.getAccessToken());
    if (token.isEmpty) return headers;

    if (useSyncToken) {
      headers['Authorization'] = 'Token $token';
      return headers;
    }
    headers['Authorization'] = 'Bearer $token';
    return headers;
  }

  Future<dynamic> getAny(
    String path, {
    Map<String, String>? query,
    String? tokenOverride,
    bool useSyncToken = false,
  }) async {
    final url = _uri(path, query);
    final res = await http
        .get(url, headers: await _headers(tokenOverride: tokenOverride, useSyncToken: useSyncToken))
        .timeout(const Duration(seconds: 20));
    return _decodeOrThrowAny(method: 'GET', url: url, res: res);
  }

  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, String>? query,
    String? tokenOverride,
    bool useSyncToken = false,
  }) async {
    final payload = await getAny(
      path,
      query: query,
      tokenOverride: tokenOverride,
      useSyncToken: useSyncToken,
    );
    if (payload is Map<String, dynamic>) return payload;
    throw ApiException(
      method: 'GET',
      url: _uri(path, query),
      statusCode: 200,
      body: 'Response is not a JSON object',
    );
  }

  Future<dynamic> postAny(
    String path,
    Map<String, Object?> body, {
    String? tokenOverride,
    bool useSyncToken = false,
  }) async {
    final url = _uri(path);
    final res = await http
        .post(
          url,
          headers: await _headers(tokenOverride: tokenOverride, useSyncToken: useSyncToken),
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 25));
    return _decodeOrThrowAny(method: 'POST', url: url, res: res);
  }

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, Object?> body, {
    String? tokenOverride,
    bool useSyncToken = false,
  }) async {
    final payload = await postAny(
      path,
      body,
      tokenOverride: tokenOverride,
      useSyncToken: useSyncToken,
    );
    if (payload is Map<String, dynamic>) return payload;
    throw ApiException(
      method: 'POST',
      url: _uri(path),
      statusCode: 200,
      body: 'Response is not a JSON object',
    );
  }

  Future<Map<String, dynamic>> putJson(
    String path,
    Map<String, Object?> body, {
    String? tokenOverride,
    bool useSyncToken = false,
  }) async {
    final url = _uri(path);
    final res = await http
        .put(
          url,
          headers: await _headers(tokenOverride: tokenOverride, useSyncToken: useSyncToken),
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 25));
    return _decodeOrThrow(method: 'PUT', url: url, res: res);
  }

  Future<Map<String, dynamic>> deleteJson(
    String path, {
    String? tokenOverride,
    bool useSyncToken = false,
  }) async {
    final url = _uri(path);
    final res = await http
        .delete(
          url,
          headers: await _headers(tokenOverride: tokenOverride, useSyncToken: useSyncToken),
        )
        .timeout(const Duration(seconds: 25));
    return _decodeOrThrow(method: 'DELETE', url: url, res: res);
  }

  dynamic _decodeOrThrowAny({required String method, required Uri url, required http.Response res}) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException(method: method, url: url, statusCode: res.statusCode, body: res.body);
    }
    if (res.body.trim().isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(res.body);
    if (decoded is Map<String, dynamic> || decoded is List) return decoded;
    return decoded;
  }

  Map<String, dynamic> _decodeOrThrow({required String method, required Uri url, required http.Response res}) {
    final decoded = _decodeOrThrowAny(method: method, url: url, res: res);
    if (decoded is Map<String, dynamic>) return decoded;
    throw ApiException(method: method, url: url, statusCode: res.statusCode, body: 'Response is not a JSON object');
  }
}
