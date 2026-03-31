import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../controllers/auth_controller.dart';
import '../../controllers/real_estate_controller.dart';
import '../settings/settings_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Get.find<RealEstateController>().loadWorkspace();
    });
  }

  String _money(dynamic value) {
    final number = num.tryParse('${value ?? 0}') ?? 0;
    return NumberFormat.currency(locale: 'en_IN', symbol: 'Rs ', decimalDigits: 0).format(number);
  }

  Future<void> _openLeadDialog() async {
    final controller = Get.find<RealEstateController>();
    final name = TextEditingController();
    final phone = TextEditingController();
    final city = TextEditingController();
    await Get.dialog(
      AlertDialog(
        title: const Text('Create Lead'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
            const SizedBox(height: 8),
            TextField(controller: phone, decoration: const InputDecoration(labelText: 'Phone')),
            const SizedBox(height: 8),
            TextField(controller: city, decoration: const InputDecoration(labelText: 'City')),
          ],
        ),
        actions: [
          TextButton(onPressed: Get.back, child: const Text('Cancel')),
          FilledButton(
            onPressed: () async {
              await controller.createLead({
                'name': name.text,
                'phone': phone.text,
                'city': city.text,
                'preferred_location': city.text,
                'source': 'website',
              });
              Get.back();
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Future<void> _openPropertyDialog() async {
    final controller = Get.find<RealEstateController>();
    final title = TextEditingController();
    final price = TextEditingController();
    final city = TextEditingController();
    await Get.dialog(
      AlertDialog(
        title: const Text('Post Property'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
            const SizedBox(height: 8),
            TextField(controller: price, decoration: const InputDecoration(labelText: 'Price')),
            const SizedBox(height: 8),
            TextField(controller: city, decoration: const InputDecoration(labelText: 'City')),
          ],
        ),
        actions: [
          TextButton(onPressed: Get.back, child: const Text('Cancel')),
          FilledButton(
            onPressed: () async {
              await controller.createProperty({
                'title': title.text,
                'price': price.text,
                'city': city.text,
                'listing_type': 'sale',
                'property_type': 'house',
                'status': controller.roleGroup == 'admin' ? 'approved' : 'pending_approval',
              });
              Get.back();
            },
            child: const Text('Publish'),
          ),
        ],
      ),
    );
  }

  Future<void> _openWithdrawDialog() async {
    final controller = Get.find<RealEstateController>();
    final amount = TextEditingController();
    await Get.dialog(
      AlertDialog(
        title: const Text('Request Withdrawal'),
        content: TextField(controller: amount, decoration: const InputDecoration(labelText: 'Amount')),
        actions: [
          TextButton(onPressed: Get.back, child: const Text('Cancel')),
          FilledButton(
            onPressed: () async {
              await controller.requestWithdrawal(amount.text);
              Get.back();
            },
            child: const Text('Submit'),
          ),
        ],
      ),
    );
  }

  Future<void> _openUrl(String? value) async {
    if (value == null || value.isEmpty) return;
    final uri = Uri.tryParse(value);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Widget _banner(String text, Color color, Color foreground) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(18)),
      child: Text(text, style: TextStyle(color: foreground, fontWeight: FontWeight.w600)),
    );
  }

  Widget _homePage(RealEstateController c) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      children: [
        if (c.message.value.isNotEmpty) _banner(c.message.value, scheme.primaryContainer, scheme.onPrimaryContainer),
        if (c.error.value.isNotEmpty) _banner(c.error.value, scheme.errorContainer, scheme.onErrorContainer),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            gradient: LinearGradient(colors: [scheme.primaryContainer, scheme.tertiaryContainer]),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              c.roleGroup == 'customer' ? 'Property Journey' : c.roleGroup == 'agent' ? 'Agent Pipeline' : 'Command Center',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text('${c.me['company_name'] ?? 'Real estate workspace'}'),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              Chip(label: Text('${c.dashboard['total_leads'] ?? c.leads.length} leads')),
              Chip(label: Text('${c.properties.length} listings')),
              Chip(label: Text('${c.visits.length} visits')),
              Chip(label: Text(_money(c.wallet['balance'] ?? c.me['wallet_balance']))),
            ]),
          ]),
        ),
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Wrap(spacing: 10, runSpacing: 10, children: [
              if (c.roleGroup != 'customer') FilledButton.icon(onPressed: _openLeadDialog, icon: const Icon(Icons.person_add_alt_1), label: const Text('Lead')),
              if (c.roleGroup != 'customer') FilledButton.tonalIcon(onPressed: _openPropertyDialog, icon: const Icon(Icons.apartment), label: const Text('Property')),
              FilledButton.tonalIcon(onPressed: () => setState(() => _index = c.roleGroup == 'customer' ? 1 : 2), icon: const Icon(Icons.search), label: const Text('Marketplace')),
              FilledButton.tonalIcon(onPressed: () => setState(() => _index = 3), icon: const Icon(Icons.event), label: const Text('Visits')),
            ]),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Notifications', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              for (final item in c.notifications.take(4))
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(item['read_at'] == null ? Icons.notifications_active : Icons.notifications_none),
                  title: Text('${item['title'] ?? item['level'] ?? 'Notification'}'),
                  subtitle: Text('${item['body'] ?? 'Platform update'}'),
                ),
              if (c.notifications.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('No notifications yet.')),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _leadsPage(RealEstateController c) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('Lead Pipeline', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700))),
                FilledButton.icon(onPressed: _openLeadDialog, icon: const Icon(Icons.add), label: const Text('New')),
              ]),
              const SizedBox(height: 8),
              for (final lead in c.leads)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${lead['name'] ?? 'Lead'}'),
                  subtitle: Text('${lead['city'] ?? lead['preferred_location'] ?? '-'} | ${lead['mobile'] ?? '-'}'),
                  trailing: PopupMenuButton<String>(
                    onSelected: (status) => c.updateLeadStatus('${lead['id']}', status),
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: 'contacted', child: Text('Contacted')),
                      PopupMenuItem(value: 'qualified', child: Text('Qualified')),
                      PopupMenuItem(value: 'closed', child: Text('Closed')),
                      PopupMenuItem(value: 'lost', child: Text('Lost')),
                    ],
                    child: Chip(label: Text('${lead['status'] ?? 'new'}')),
                  ),
                ),
              if (c.leads.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('No leads found.')),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _marketPage(RealEstateController c, {bool wishlistOnly = false}) {
    final items = wishlistOnly
        ? c.wishlist
            .map((item) => item['property_detail'] is Map ? Map<String, dynamic>.from(item['property_detail'] as Map) : <String, dynamic>{})
            .where((item) => item.isNotEmpty)
            .toList()
        : c.properties.toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      children: [
        if (!wishlistOnly && c.roleGroup != 'customer')
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FilledButton.icon(onPressed: _openPropertyDialog, icon: const Icon(Icons.add_business), label: const Text('Post Property')),
          ),
        for (final property in items)
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${property['title'] ?? 'Property'}', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                Text('${property['city'] ?? '-'}, ${property['state'] ?? '-'}'),
                const SizedBox(height: 6),
                Text(_money(property['price'])),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  Chip(label: Text('${property['property_type'] ?? 'property'}')),
                  Chip(label: Text('${property['listing_type'] ?? 'sale'}')),
                  Chip(label: Text('${property['status'] ?? 'pending_approval'}')),
                ]),
                const SizedBox(height: 10),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  FilledButton.tonalIcon(onPressed: () => c.toggleWishlist('${property['id']}'), icon: const Icon(Icons.favorite_border), label: const Text('Wishlist')),
                  FilledButton.icon(onPressed: () => c.scheduleVisit('${property['id']}'), icon: const Icon(Icons.calendar_today), label: const Text('Visit')),
                  if ('${property['whatsapp_link'] ?? ''}'.isNotEmpty)
                    FilledButton.tonalIcon(onPressed: () => _openUrl(property['whatsapp_link']?.toString()), icon: const Icon(Icons.chat_bubble_outline), label: const Text('WhatsApp')),
                ]),
              ]),
            ),
          ),
        if (items.isEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 18), child: Text(wishlistOnly ? 'Wishlist empty.' : 'No properties available.')),
      ],
    );
  }

  Widget _visitsPage(RealEstateController c) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Scheduled Visits', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              for (final visit in c.visits)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.home_work_outlined),
                  title: Text('${visit['lead_name'] ?? 'Visit'}'),
                  subtitle: Text('${visit['location'] ?? '-'} | ${visit['visit_date'] ?? '-'}'),
                  trailing: Chip(label: Text('${visit['status'] ?? 'scheduled'}')),
                ),
              if (c.visits.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('No visits scheduled yet.')),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _walletPage(RealEstateController c) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('Wallet', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700))),
                FilledButton.tonalIcon(onPressed: _openWithdrawDialog, icon: const Icon(Icons.account_balance_wallet), label: const Text('Withdraw')),
              ]),
              const SizedBox(height: 12),
              Text(_money(c.wallet['balance'] ?? c.me['wallet_balance']), style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              for (final item in c.transactions.take(6))
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(_money(item['amount'])),
                  subtitle: Text('${item['source'] ?? item['entry_type'] ?? 'Wallet entry'}'),
                  trailing: Text('${item['entry_type'] ?? ''}'),
                ),
              if (c.transactions.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('No wallet transactions yet.')),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('Plans', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700))),
                TextButton(onPressed: c.activateFreePlan, child: const Text('Free Plan')),
              ]),
              const SizedBox(height: 8),
              for (final plan in c.plans)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${plan['name'] ?? 'Plan'}'),
                  subtitle: Text('${plan['max_leads_per_month'] ?? 0} leads | ${plan['max_property_listings'] ?? 0} listings'),
                  trailing: FilledButton.tonal(onPressed: () => c.subscribeToPlan('${plan['id']}'), child: const Text('Choose')),
                ),
              if (c.plans.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('No plans available.')),
            ]),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Get.find<AuthController>();
    final controller = Get.find<RealEstateController>();
    return Obx(() {
      const customerTabs = [
        ('Home', Icons.dashboard_outlined),
        ('Market', Icons.apartment_outlined),
        ('Wishlist', Icons.favorite_border),
        ('Visits', Icons.event_note_outlined),
        ('Wallet', Icons.account_balance_wallet_outlined),
      ];
      const teamTabs = [
        ('Home', Icons.dashboard_outlined),
        ('Leads', Icons.groups_outlined),
        ('Market', Icons.apartment_outlined),
        ('Visits', Icons.event_note_outlined),
        ('Wallet', Icons.account_balance_wallet_outlined),
      ];
      final tabs = controller.roleGroup == 'customer' ? customerTabs : teamTabs;
      if (controller.isLoading.value && controller.me.isEmpty) {
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      }
      final body = controller.roleGroup == 'customer'
          ? [() => _homePage(controller), () => _marketPage(controller), () => _marketPage(controller, wishlistOnly: true), () => _visitsPage(controller), () => _walletPage(controller)][_index]()
          : [() => _homePage(controller), () => _leadsPage(controller), () => _marketPage(controller), () => _visitsPage(controller), () => _walletPage(controller)][_index]();

      return Scaffold(
        appBar: AppBar(
          title: Text(tabs[_index].$1),
          actions: [
            IconButton(onPressed: controller.isRefreshing.value ? null : () => controller.loadWorkspace(silent: true), icon: const Icon(Icons.refresh)),
            IconButton(onPressed: () => Get.to(() => const SettingsScreen()), icon: const Icon(Icons.settings_outlined)),
            IconButton(
              onPressed: () async {
                controller.clearState();
                await auth.logout();
              },
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: RefreshIndicator(onRefresh: () => controller.loadWorkspace(silent: true), child: body),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (index) => setState(() => _index = index),
          destinations: [for (final tab in tabs) NavigationDestination(icon: Icon(tab.$2), label: tab.$1)],
        ),
      );
    });
  }
}
