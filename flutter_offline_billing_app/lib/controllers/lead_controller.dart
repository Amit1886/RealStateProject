import 'package:get/get.dart';

import '../services/lead_service.dart';

class LeadController extends GetxController {
  LeadController({required this.service});

  final LeadService service;

  final leads = <Map<String, dynamic>>[].obs;
  final isBusy = false.obs;
  final error = ''.obs;

  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    try {
      isBusy.value = true;
      error.value = '';
      final data = await service.fetchLeads();
      leads.assignAll(data);
    } catch (e) {
      error.value = e.toString();
    } finally {
      isBusy.value = false;
    }
  }
}
