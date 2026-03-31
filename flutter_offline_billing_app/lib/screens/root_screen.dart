import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../controllers/auth_controller.dart';
import 'auth/login_screen.dart';
import 'home/home_shell.dart';

class RootScreen extends GetView<AuthController> {
  const RootScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isBusy.value) {
        return const _Splash();
      }
      if (controller.error.value.isNotEmpty) {
        return _Fatal(error: controller.error.value);
      }
      if (controller.currentUser.value == null) {
        return const LoginScreen();
      }
      return const HomeShell();
    });
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.home_work_rounded, size: 58, color: scheme.primary),
            const SizedBox(height: 12),
            Text(
              'PropFlow Mobile',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              'Loading workspace...',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _Fatal extends StatelessWidget {
  const _Fatal({required this.error});

  final String error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Startup Error')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(error),
      ),
    );
  }
}
