import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jaistech_billing_mobile_app/core/theme/app_theme.dart';

void main() {
  testWidgets('App theme builds', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: const Scaffold(body: SizedBox()),
      ),
    );

    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
