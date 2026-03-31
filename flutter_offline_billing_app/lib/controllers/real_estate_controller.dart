import 'package:get/get.dart';

import '../services/real_estate_service.dart';

class RealEstateController extends GetxController {
  RealEstateController({
    required RealEstateService service,
  }) : _service = service;

  final RealEstateService _service;

  final RxBool isLoading = true.obs;
  final RxBool isRefreshing = false.obs;
  final RxString error = ''.obs;
  final RxString message = ''.obs;

  final RxMap<String, dynamic> me = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> summary = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> dashboard = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> wallet = <String, dynamic>{}.obs;

  final RxList<Map<String, dynamic>> leads = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> properties = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> wishlist = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> visits = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> agents = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> transactions = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> withdrawRequests = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> plans = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> subscriptions = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> notifications = <Map<String, dynamic>>[].obs;

  String get roleGroup {
    final role = (me['role'] ?? '').toString().toLowerCase();
    final isAdmin = me['is_superuser'] == true ||
        me['is_staff'] == true ||
        role == 'super_admin' ||
        role == 'state_admin' ||
        role == 'district_admin' ||
        role == 'area_admin';
    if (isAdmin) return 'admin';
    if (role == 'agent' || role == 'super_agent') return 'agent';
    return 'customer';
  }

  Future<T> _safe<T>(Future<T> Function() task, T fallback) async {
    try {
      return await task();
    } catch (_) {
      return fallback;
    }
  }

  Future<void> loadWorkspace({bool silent = false}) async {
    if (silent) {
      isRefreshing.value = true;
    } else {
      isLoading.value = true;
    }
    error.value = '';

    try {
      final responses = await Future.wait<dynamic>([
        _service.fetchMe(),
        _safe(_service.fetchSummary, <String, dynamic>{}),
        _safe(_service.fetchLeadDashboard, <String, dynamic>{}),
        _safe(_service.fetchLeads, <Map<String, dynamic>>[]),
        _safe(_service.fetchProperties, <Map<String, dynamic>>[]),
        _safe(_service.fetchWishlist, <Map<String, dynamic>>[]),
        _safe(_service.fetchVisits, <Map<String, dynamic>>[]),
        _safe(_service.fetchAgents, <Map<String, dynamic>>[]),
        _safe(_service.fetchWallets, <Map<String, dynamic>>[]),
        _safe(_service.fetchTransactions, <Map<String, dynamic>>[]),
        _safe(_service.fetchWithdrawRequests, <Map<String, dynamic>>[]),
        _safe(_service.fetchPlans, <Map<String, dynamic>>[]),
        _safe(_service.fetchSubscriptions, <Map<String, dynamic>>[]),
        _safe(_service.fetchNotifications, <Map<String, dynamic>>[]),
      ]);

      me.assignAll(Map<String, dynamic>.from(responses[0] as Map<String, dynamic>));
      summary.assignAll(Map<String, dynamic>.from(responses[1] as Map<String, dynamic>));
      dashboard.assignAll(Map<String, dynamic>.from(responses[2] as Map<String, dynamic>));
      leads.assignAll(List<Map<String, dynamic>>.from(responses[3] as List));
      properties.assignAll(List<Map<String, dynamic>>.from(responses[4] as List));
      wishlist.assignAll(List<Map<String, dynamic>>.from(responses[5] as List));
      visits.assignAll(List<Map<String, dynamic>>.from(responses[6] as List));
      agents.assignAll(List<Map<String, dynamic>>.from(responses[7] as List));
      final wallets = List<Map<String, dynamic>>.from(responses[8] as List);
      wallet.assignAll(wallets.isNotEmpty ? wallets.first : <String, dynamic>{});
      transactions.assignAll(List<Map<String, dynamic>>.from(responses[9] as List));
      withdrawRequests.assignAll(List<Map<String, dynamic>>.from(responses[10] as List));
      plans.assignAll(List<Map<String, dynamic>>.from(responses[11] as List));
      subscriptions.assignAll(List<Map<String, dynamic>>.from(responses[12] as List));
      notifications.assignAll(List<Map<String, dynamic>>.from(responses[13] as List));

      if (silent) {
        message.value = 'Workspace refreshed.';
      }
    } catch (e) {
      error.value = e.toString();
    } finally {
      isLoading.value = false;
      isRefreshing.value = false;
    }
  }

  void clearState() {
    me.clear();
    summary.clear();
    dashboard.clear();
    wallet.clear();
    leads.clear();
    properties.clear();
    wishlist.clear();
    visits.clear();
    agents.clear();
    transactions.clear();
    withdrawRequests.clear();
    plans.clear();
    subscriptions.clear();
    notifications.clear();
    message.value = '';
    error.value = '';
    isLoading.value = false;
    isRefreshing.value = false;
  }

  Future<void> _runAction(Future<void> Function() task, String successMessage) async {
    error.value = '';
    try {
      await task();
      message.value = successMessage;
      await loadWorkspace(silent: true);
    } catch (e) {
      error.value = e.toString();
    }
  }

  Future<void> createLead(Map<String, Object?> payload) async {
    await _runAction(() => _service.createLead(payload), 'Lead captured successfully.');
  }

  Future<void> updateLeadStatus(String leadId, String status) async {
    await _runAction(() => _service.updateLeadStatus(leadId, status), 'Lead updated.');
  }

  Future<void> createProperty(Map<String, Object?> payload) async {
    await _runAction(() => _service.createProperty(payload), 'Property submitted.');
  }

  Future<void> toggleWishlist(String propertyId) async {
    await _runAction(() => _service.toggleWishlist(propertyId), 'Wishlist updated.');
  }

  Future<void> scheduleVisit(String propertyId, {String notes = ''}) async {
    await _runAction(() => _service.scheduleVisit(propertyId, notes: notes), 'Visit scheduled.');
  }

  Future<void> requestWithdrawal(String amount) async {
    await _runAction(() => _service.requestWithdrawal(amount), 'Withdrawal request created.');
  }

  Future<void> subscribeToPlan(String planId) async {
    await _runAction(() => _service.subscribeToPlan(planId), 'Subscription updated.');
  }

  Future<void> activateFreePlan() async {
    await _runAction(_service.activateFreePlan, 'Free plan activated.');
  }

  Future<void> markAllNotificationsRead() async {
    await _runAction(_service.markAllNotificationsRead, 'Notifications marked as read.');
  }
}
