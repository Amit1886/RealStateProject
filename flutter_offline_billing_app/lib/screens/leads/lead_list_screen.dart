import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../controllers/lead_controller.dart';

class LeadListScreen extends GetView<LeadController> {
  const LeadListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isBusy.value) {
        return const Center(child: CircularProgressIndicator());
      }
      if (controller.error.value.isNotEmpty) {
        return Center(child: Text(controller.error.value));
      }
      final leads = controller.leads;
      if (leads.isEmpty) {
        return const Center(child: Text('No leads found'));
      }
      return RefreshIndicator(
        onRefresh: controller.load,
        child: ListView.separated(
          padding: const EdgeInsets.all(12),
          itemCount: leads.length,
          separatorBuilder: (_, __) => const Divider(height: 0),
          itemBuilder: (context, index) {
            final lead = leads[index];
            return ListTile(
              leading: const Icon(Icons.person),
              title: Text(lead['name'] ?? '-'),
              subtitle: Text('${lead['status'] ?? ''} | Rs ${lead['budget'] ?? 0}'),
              trailing: Text(lead['preferred_location'] ?? ''),
            );
          },
        ),
      );
    });
  }
}
