import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../controllers/settings_controller.dart';
import '../../widgets/custom_button.dart';
import '../../widgets/custom_textfield.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _baseUrl;
  late final TextEditingController _companyId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final controller = Get.find<SettingsController>();
    _baseUrl = TextEditingController(text: controller.apiBaseUrl.value);
    _companyId = TextEditingController(text: controller.companyId.value);
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _companyId.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await Get.find<SettingsController>().save(
        baseUrl: _baseUrl.text,
        company: _companyId.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mobile API settings saved')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('App Settings')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Connect the mobile app to your Django server.',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 16),
                    CustomTextField(
                      controller: _baseUrl,
                      label: 'API Base URL',
                      hintText: 'http://192.168.1.10:8000',
                      prefixIcon: Icons.link,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'On a phone, use your computer LAN IP. Example: http://192.168.x.x:8000',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    CustomTextField(
                      controller: _companyId,
                      label: 'Company ID',
                      hintText: 'Optional tenant/company id',
                      prefixIcon: Icons.apartment,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'If your account belongs to a tenant, this value can also be set automatically after login.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 18),
                    Align(
                      alignment: Alignment.centerRight,
                      child: CustomButton(
                        label: 'Save Settings',
                        icon: Icons.save,
                        loading: _saving,
                        onPressed: _save,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
