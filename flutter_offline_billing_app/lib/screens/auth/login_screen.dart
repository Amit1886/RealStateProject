import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../controllers/auth_controller.dart';
import '../../screens/settings/settings_screen.dart';
import '../../widgets/custom_button.dart';
import '../../widgets/custom_textfield.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _hide = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final auth = Get.find<AuthController>();
    try {
      await auth.login(username: _email.text, password: _password.text);
    } catch (_) {
      if (!mounted) return;
      final message = auth.error.value.isNotEmpty ? auth.error.value : 'Login failed';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Get.find<AuthController>();
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(28),
                gradient: LinearGradient(
                  colors: [
                    scheme.primaryContainer,
                    scheme.tertiaryContainer,
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.location_city, size: 42, color: scheme.onPrimaryContainer),
                  const SizedBox(height: 14),
                  Text(
                    'PropFlow Mobile',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: scheme.onPrimaryContainer,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Real estate CRM, property marketplace, visits, wallet, and lead actions for agents and customers.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: scheme.onPrimaryContainer.withValues(alpha: 0.86),
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 22),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Sign in',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 16),
                    CustomTextField(
                      controller: _email,
                      label: 'Email',
                      hintText: 'agent@example.com',
                      keyboardType: TextInputType.emailAddress,
                      prefixIcon: Icons.alternate_email,
                    ),
                    const SizedBox(height: 12),
                    CustomTextField(
                      controller: _password,
                      label: 'Password',
                      hintText: 'Enter password',
                      obscureText: _hide,
                      prefixIcon: Icons.lock_outline,
                      suffixIcon: _hide ? Icons.visibility : Icons.visibility_off,
                      onSuffixTap: () => setState(() => _hide = !_hide),
                    ),
                    const SizedBox(height: 16),
                    Obx(
                      () => CustomButton(
                        label: 'Enter Workspace',
                        icon: Icons.login,
                        loading: auth.isBusy.value,
                        onPressed: _submit,
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextButton.icon(
                      onPressed: () => Get.to(() => const SettingsScreen()),
                      icon: const Icon(Icons.settings),
                      label: const Text('Server Settings'),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Phone se connect karte waqt 127.0.0.1 ke jagah PC ka LAN IP use karo, for example http://192.168.1.10:8000',
                      style: Theme.of(context).textTheme.bodySmall,
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
