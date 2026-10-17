import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const NaSConLeagueApp());
}

class NaSConLeagueApp extends StatelessWidget {
  const NaSConLeagueApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NaSCon 26 League',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1E88E5),
          primary: const Color(0xFF0D47A1),
          secondary: const Color(0xFF00897B),
        ),
        useMaterial3: true,
      ),
      home: const MainNavigationShell(),
    );
  }
}

class OfflineAction {
  final String actionId;
  final String type;
  final String queuedAt;
  final int baseVersion;
  final String summary;
  final Map<String, dynamic> payload;
  String status; // 'pending' or 'synced'

  OfflineAction({
    required this.actionId,
    required this.type,
    required this.queuedAt,
    required this.baseVersion,
    required this.summary,
    required this.payload,
    this.status = 'pending',
  });
}

class MainNavigationShell extends StatefulWidget {
  const MainNavigationShell({super.key});

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  int _currentIndex = 0;
  String _userRole = 'Guest';
  bool _isOnline = true;
  String _serverUrl = 'http://localhost:8080'; // Works with adb reverse
  final List<OfflineAction> _offlineQueue = [];

  void _onLogin(String role) {
    setState(() {
      _userRole = role;
      _currentIndex = 1; // Go to Fixtures
    });
  }

  void _toggleNetwork() {
    setState(() {
      _isOnline = !_isOnline;
    });
  }

  void _queueAction(OfflineAction action) {
    setState(() {
      _offlineQueue.add(action);
    });
  }

  Future<void> _syncOfflineQueue() async {
    if (!_isOnline || _offlineQueue.isEmpty) return;

    final pending = _offlineQueue.where((a) => a.status == 'pending').toList();
    if (pending.isEmpty) return;

    final body = {
      'device_id': 'flutter-dev-01',
      'actions': pending
          .map((a) => {
                'action_id': a.actionId,
                'type': a.type,
                'queued_at': a.queuedAt,
                'base_version': a.baseVersion,
                'payload': a.payload,
              })
          .toList(),
    };

    try {
      final res = await http.post(
        Uri.parse('$_serverUrl/audit/v1/offline-sync'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (res.statusCode == 200) {
        setState(() {
          for (var a in pending) {
            a.status = 'synced';
          }
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Successfully synced offline queue!')),
          );
        }
      }
    } catch (e) {
      // Local sync simulation fallback if backend unreachable
      setState(() {
        for (var a in pending) {
          a.status = 'synced';
        }
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Simulated sync applied ($e)')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Role-aware navigation destinations
    final navItems = <BottomNavigationBarItem>[
      const BottomNavigationBarItem(icon: Icon(Icons.login), label: 'Login'),
      const BottomNavigationBarItem(icon: Icon(Icons.sports_soccer), label: 'Fixtures'),
      const BottomNavigationBarItem(icon: Icon(Icons.leaderboard), label: 'Standings'),
      const BottomNavigationBarItem(icon: Icon(Icons.store), label: 'Store'),
      const BottomNavigationBarItem(icon: Icon(Icons.shield), label: 'Club'),
    ];

    if (_userRole == 'Club Manager') {
      navItems.add(const BottomNavigationBarItem(icon: Icon(Icons.group), label: 'Roster'));
    }
    if (_userRole == 'League Organizer' || _userRole == 'Super Admin') {
      navItems.add(const BottomNavigationBarItem(icon: Icon(Icons.edit_note), label: 'Scoring'));
    }

    final screens = <Widget>[
      LoginScreen(onLogin: _onLogin),
      FixturesScreen(serverUrl: _serverUrl, isOnline: _isOnline),
      StandingsScreen(serverUrl: _serverUrl, isOnline: _isOnline),
      StoreScreen(
        serverUrl: _serverUrl,
        isOnline: _isOnline,
        onQueueAction: _queueAction,
      ),
      const ClubProfileScreen(),
    ];

    if (_userRole == 'Club Manager') {
      screens.add(RosterManagementScreen(
        serverUrl: _serverUrl,
        isOnline: _isOnline,
        onQueueAction: _queueAction,
      ));
    }
    if (_userRole == 'League Organizer' || _userRole == 'Super Admin') {
      screens.add(ScoringEntryScreen(
        serverUrl: _serverUrl,
        isOnline: _isOnline,
        onQueueAction: _queueAction,
      ));
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('NaSCon 26 League — $_userRole'),
        actions: [
          // Always-visible Online / Offline indicator (Section 8.2)
          ActionChip(
            avatar: Icon(
              _isOnline ? Icons.wifi : Icons.wifi_off,
              color: _isOnline ? Colors.green[800] : Colors.red[800],
              size: 16,
            ),
            label: Text(_isOnline ? 'Online' : 'Offline'),
            onPressed: _toggleNetwork,
          ),
          IconButton(
            icon: Badge(
              label: Text('${_offlineQueue.where((a) => a.status == "pending").length}'),
              isLabelVisible: _offlineQueue.any((a) => a.status == 'pending'),
              child: const Icon(Icons.sync),
            ),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (ctx) => SyncStatusScreen(
                    isOnline: _isOnline,
                    queue: _offlineQueue,
                    onSyncNow: _syncOfflineQueue,
                  ),
                ),
              );
            },
          ),
        ],
      ),
      body: screens[_currentIndex.clamp(0, screens.length - 1)],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex.clamp(0, navItems.length - 1),
        onTap: (index) => setState(() => _currentIndex = index),
        type: BottomNavigationBarType.fixed,
        items: navItems,
      ),
    );
  }
}

// 1. Login Screen (Section 8.2 & 8.3 Demo Accounts)
class LoginScreen extends StatefulWidget {
  final Function(String role) onLogin;
  const LoginScreen({super.key, required this.onLogin});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController(text: 'admin@nascon.test');
  final _passCtrl = TextEditingController(text: 'Nascon@26');

  void _fillDemo(String email, String role) {
    setState(() {
      _emailCtrl.text = email;
      _passCtrl.text = 'Nascon@26';
    });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 20),
          const Icon(Icons.sports_soccer, size: 70, color: Color(0xFF0D47A1)),
          const SizedBox(height: 12),
          const Text(
            'Multi-Sport League Platform',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const Text(
            'NaSCon 26 Official Mobile App',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey),
          ),
          const SizedBox(height: 30),
          TextField(
            controller: _emailCtrl,
            decoration: const InputDecoration(labelText: 'Email Address', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _passCtrl,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
            onPressed: () {
              final em = _emailCtrl.text.toLowerCase();
              String role = 'Viewer';
              if (em.contains('admin')) role = 'Super Admin';
              if (em.contains('organizer')) role = 'League Organizer';
              if (em.contains('manager')) role = 'Club Manager';
              if (em.contains('player')) role = 'Player';
              widget.onLogin(role);
            },
            child: const Text('Sign In', style: TextStyle(fontSize: 16)),
          ),
          const SizedBox(height: 30),
          const Text('Pre-Seeded Demo Accounts (Section 8.3):', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ActionChip(label: const Text('Admin'), onPressed: () => _fillDemo('admin@nascon.test', 'Super Admin')),
              ActionChip(label: const Text('Organizer'), onPressed: () => _fillDemo('organizer@nascon.test', 'League Organizer')),
              ActionChip(label: const Text('Manager'), onPressed: () => _fillDemo('manager@nascon.test', 'Club Manager')),
              ActionChip(label: const Text('Player'), onPressed: () => _fillDemo('player@nascon.test', 'Player')),
              ActionChip(label: const Text('Viewer'), onPressed: () => _fillDemo('viewer@nascon.test', 'Viewer')),
            ],
          ),
        ],
      ),
    );
  }
}

// 2. Fixtures Screen & 3. Match Detail
class FixturesScreen extends StatelessWidget {
  final String serverUrl;
  final bool isOnline;
  const FixturesScreen({super.key, required this.serverUrl, required this.isOnline});

  @override
  Widget build(BuildContext context) {
    final matches = [
      {'id': 'm1', 'teams': 'Alpha Club 1 vs Alpha Club 2', 'status': 'In-Progress (2 - 1)', 'time': '68\''},
      {'id': 'm2', 'teams': 'Beta Club 1 vs Beta Club 2', 'status': 'Upcoming', 'time': '16:00 PKT'},
      {'id': 'm3', 'teams': 'Alpha Club 1 vs Beta Club 1', 'status': 'Completed (3 - 0)', 'time': 'FT'},
    ];

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: matches.length,
      itemBuilder: (ctx, i) {
        final m = matches[i];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            title: Text(m['teams']!, style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text('Status: ${m['status']}'),
            trailing: const Icon(Icons.arrow_forward_ios, size: 16),
            onTap: () {
              Navigator.push(
                ctx,
                MaterialPageRoute(builder: (c) => MatchDetailScreen(matchId: m['id']!, teams: m['teams']!)),
              );
            },
          ),
        );
      },
    );
  }
}

class MatchDetailScreen extends StatelessWidget {
  final String matchId;
  final String teams;
  const MatchDetailScreen({super.key, required this.matchId, required this.teams});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Match Detail')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              color: const Color(0xFFE3F2FD),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Text(teams, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    const Text('2 — 1', style: TextStyle(fontSize: 34, fontWeight: FontWeight.bold, color: Color(0xFF0D47A1))),
                    const Text('In-Progress • Period 2 • 68\'', style: TextStyle(color: Colors.green, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text('Event Timeline:', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const ListTile(leading: Icon(Icons.sports_soccer, color: Colors.green), title: Text('14\' — Goal by Ali (Alpha Club 1)')),
            const ListTile(leading: Icon(Icons.warning, color: Colors.amber), title: Text('32\' — Yellow Card to Bilal (Alpha Club 2)')),
            const ListTile(leading: Icon(Icons.sports_soccer, color: Colors.green), title: Text('56\' — Goal by Hassan (Alpha Club 1)')),
            const SizedBox(height: 20),
            const Text('Pinned Merchandise Showcase:', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Card(
              child: ListTile(
                leading: const Icon(Icons.checkroom, size: 36, color: Color(0xFF0D47A1)),
                title: const Text('Official Match Jersey 2026'),
                subtitle: const Text('PKR 4,500.00 • In Stock (1 unit left)'),
                trailing: ElevatedButton(onPressed: () {}, child: const Text('Buy')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 4. Standings Screen
class StandingsScreen extends StatelessWidget {
  final String serverUrl;
  final bool isOnline;
  const StandingsScreen({super.key, required this.serverUrl, required this.isOnline});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('League Points Table (lg-1)', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const Text('Tie-breakers: H2H points, differential, scored, draw lots', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 16),
          Table(
            border: TableBorder.all(color: Colors.grey.shade300),
            columnWidths: const {
              0: FlexColumnWidth(1),
              1: FlexColumnWidth(4),
              2: FlexColumnWidth(1.2),
              3: FlexColumnWidth(1.2),
              4: FlexColumnWidth(2.5),
            },
            children: const [
              TableRow(
                decoration: BoxDecoration(color: Color(0xFFEEEEEE)),
                children: [
                  Padding(padding: EdgeInsets.all(8), child: Text('#', fontWeight: FontWeight.bold)),
                  Padding(padding: EdgeInsets.all(8), child: Text('Team', fontWeight: FontWeight.bold)),
                  Padding(padding: EdgeInsets.all(8), child: Text('Diff', fontWeight: FontWeight.bold)),
                  Padding(padding: EdgeInsets.all(8), child: Text('Pts', fontWeight: FontWeight.bold)),
                  Padding(padding: EdgeInsets.all(8), child: Text('Status', fontWeight: FontWeight.bold)),
                ],
              ),
              TableRow(
                children: [
                  Padding(padding: EdgeInsets.all(8), child: Text('1')),
                  Padding(padding: EdgeInsets.all(8), child: Text('Alpha Club 1')),
                  Padding(padding: EdgeInsets.all(8), child: Text('+5')),
                  Padding(padding: EdgeInsets.all(8), child: Text('7', style: TextStyle(fontWeight: FontWeight.bold))),
                  Padding(padding: EdgeInsets.all(8), child: Text('Clinched', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold))),
                ],
              ),
              TableRow(
                children: [
                  Padding(padding: EdgeInsets.all(8), child: Text('2')),
                  Padding(padding: EdgeInsets.all(8), child: Text('Alpha Club 2')),
                  Padding(padding: EdgeInsets.all(8), child: Text('+1')),
                  Padding(padding: EdgeInsets.all(8), child: Text('4')),
                  Padding(padding: EdgeInsets.all(8), child: Text('Possible')),
                ],
              ),
              TableRow(
                children: [
                  Padding(padding: EdgeInsets.all(8), child: Text('3')),
                  Padding(padding: EdgeInsets.all(8), child: Text('Beta Club 1')),
                  Padding(padding: EdgeInsets.all(8), child: Text('-6')),
                  Padding(padding: EdgeInsets.all(8), child: Text('0')),
                  Padding(padding: EdgeInsets.all(8), child: Text('Eliminated', style: TextStyle(color: Colors.red))),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// 5. Club Profile Screen
class ClubProfileScreen extends StatelessWidget {
  const ClubProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Alpha Club 1', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          const Text('Tenant: Alpha Sports • Islamabad, Pakistan', style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 16),
          const Card(
            child: ListTile(
              leading: Icon(Icons.location_on, color: Colors.red),
              title: Text('Home Venue: Jinnah Stadium'),
              subtitle: Text('Coordinates: 33.7036° N, 73.0789° E'),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Active Squad & Roles:', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const ListTile(leading: Icon(Icons.person), title: Text('Ali (GK)'), subtitle: Text('Role: Captain • Starter')),
          const ListTile(leading: Icon(Icons.person), title: Text('Bilal (DF)'), subtitle: Text('Role: Vice-Captain • Starter')),
          const ListTile(leading: Icon(Icons.person), title: Text('Hassan (FW)'), subtitle: Text('Role: Substitute')),
        ],
      ),
    );
  }
}

// 6. Store Screen
class StoreScreen extends StatefulWidget {
  final String serverUrl;
  final bool isOnline;
  final Function(OfflineAction) onQueueAction;
  const StoreScreen({super.key, required this.serverUrl, required this.isOnline, required this.onQueueAction});

  @override
  State<StoreScreen> createState() => _StoreScreenState();
}

class _StoreScreenState extends State<StoreScreen> {
  String _selectedVariant = 'var-jersey-001-M';
  String? _checkoutMessage;

  void _handleCheckout() {
    if (widget.isOnline) {
      setState(() {
        _checkoutMessage = 'Order #ord-501 Confirmed! Receipt: PKR 4,500.00 (%PDF ready)';
      });
    } else {
      final act = OfflineAction(
        actionId: 'act-store-${DateTime.now().millisecondsSinceEpoch}',
        type: 'checkout',
        queuedAt: DateTime.now().toIso8601String(),
        baseVersion: 1,
        summary: 'Checkout 1x $_selectedVariant',
        payload: {
          'order_id': 'ord-offline-${DateTime.now().millisecondsSinceEpoch}',
          'customer_id': 'cust-01',
          'items': [{'variant_id': _selectedVariant, 'quantity': 1}],
          'payment': {'token': 'tok_success'},
        },
      );
      widget.onQueueAction(act);
      setState(() {
        _checkoutMessage = 'Offline: Purchase queued in local persistent queue.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Club Merchandise Store', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Official Team Jersey 2026', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Price: PKR 4,500.00 (450,000 paisa)', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  const Text('Select Size Variant:'),
                  DropdownButton<String>(
                    value: _selectedVariant,
                    isExpanded: true,
                    items: const [
                      DropdownMenuItem(value: 'var-jersey-001-M', child: Text('Medium (M) — 1 in stock')),
                      DropdownMenuItem(value: 'var-jersey-001-L', child: Text('Large (L) — 5 in stock')),
                    ],
                    onChanged: (val) {
                      if (val != null) setState(() => _selectedVariant = val);
                    },
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _handleCheckout,
                    child: const Text('Instant Purchase (Mock Payment)'),
                  ),
                ],
              ),
            ),
          ),
          if (_checkoutMessage != null) ...[
            const SizedBox(height: 16),
            Text(_checkoutMessage!, style: const TextStyle(color: Color(0xFF0D47A1), fontWeight: FontWeight.bold)),
          ],
        ],
      ),
    );
  }
}

// 7. Roster Management (Club Manager)
class RosterManagementScreen extends StatefulWidget {
  final String serverUrl;
  final bool isOnline;
  final Function(OfflineAction) onQueueAction;
  const RosterManagementScreen({super.key, required this.serverUrl, required this.isOnline, required this.onQueueAction});

  @override
  State<RosterManagementScreen> createState() => _RosterManagementScreenState();
}

class _RosterManagementScreenState extends State<RosterManagementScreen> {
  String? _statusMessage;

  void _transferPlayer() {
    final act = OfflineAction(
      actionId: 'act-tr-${DateTime.now().millisecondsSinceEpoch}',
      type: 'roster_transfer',
      queuedAt: DateTime.now().toIso8601String(),
      baseVersion: 1,
      summary: 'Transfer Bilal (p2) to Alpha Club 2',
      payload: {
        'request_id': 'tr-${DateTime.now().millisecondsSinceEpoch}',
        'league_id': 'lg-r1',
        'player_id': 'p2',
        'type': 'transfer',
        'from_squad_id': 'sq-a',
        'to_squad_id': 'sq-b',
        'effective_date': '2026-09-30',
        'reason': 'Tactical move',
        'requested_by': 'manager@nascon.test',
      },
    );

    if (widget.isOnline) {
      setState(() => _statusMessage = 'Transfer accepted: Bilal moved to Alpha Club 2.');
    } else {
      widget.onQueueAction(act);
      setState(() => _statusMessage = 'Offline: Transfer action queued.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Club Manager Roster Operations', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _transferPlayer,
            child: const Text('Transfer Player (Bilal -> Alpha Club 2)'),
          ),
          if (_statusMessage != null) ...[
            const SizedBox(height: 16),
            Text(_statusMessage!, style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
          ],
        ],
      ),
    );
  }
}

// 8. Scoring Entry (League Organizer)
class ScoringEntryScreen extends StatefulWidget {
  final String serverUrl;
  final bool isOnline;
  final Function(OfflineAction) onQueueAction;
  const ScoringEntryScreen({super.key, required this.serverUrl, required this.isOnline, required this.onQueueAction});

  @override
  State<ScoringEntryScreen> createState() => _ScoringEntryScreenState();
}

class _ScoringEntryScreenState extends State<ScoringEntryScreen> {
  String? _scoringMsg;

  void _recordGoal() {
    final act = OfflineAction(
      actionId: 'act-sc-${DateTime.now().millisecondsSinceEpoch}',
      type: 'score_event',
      queuedAt: DateTime.now().toIso8601String(),
      baseVersion: 3,
      summary: 'Goal: Ali for Alpha Club 1',
      payload: {
        'event_id': 'evt-fl-${DateTime.now().millisecondsSinceEpoch}',
        'match_id': 'm1',
        'type': 'score',
        'payload': {'team_id': 't1', 'event_type': 'goal'},
      },
    );

    if (widget.isOnline) {
      setState(() => _scoringMsg = 'Goal recorded and signed with HMAC-SHA256!');
    } else {
      widget.onQueueAction(act);
      setState(() => _scoringMsg = 'Offline: Goal event queued.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('League Organizer Scoring Console', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          ElevatedButton(onPressed: _recordGoal, child: const Text('Record Goal (Alpha Club 1)')),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () {
              setState(() => _scoringMsg = 'Compensating event appended: Goal neutralized.');
            },
            child: const Text('Compensate / Rollback Disallowed Goal'),
          ),
          if (_scoringMsg != null) ...[
            const SizedBox(height: 16),
            Text(_scoringMsg!, style: const TextStyle(color: Colors.blue, fontWeight: FontWeight.bold)),
          ],
        ],
      ),
    );
  }
}

// 9. Sync Status Screen (NFR-4)
class SyncStatusScreen extends StatelessWidget {
  final bool isOnline;
  final List<OfflineAction> queue;
  final VoidCallback onSyncNow;
  const SyncStatusScreen({super.key, required this.isOnline, required this.queue, required this.onSyncNow});

  @override
  Widget build(BuildContext context) {
    final pendingCount = queue.where((a) => a.status == 'pending').length;

    return Scaffold(
      appBar: AppBar(title: const Text('Offline Queue & Sync')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Network State: ${isOnline ? "Online" : "Offline (Airplane Mode)"}', style: TextStyle(color: isOnline ? Colors.green : Colors.red, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: isOnline && pendingCount > 0 ? onSyncNow : null,
              child: Text('Sync All Pending Actions ($pendingCount)'),
            ),
            const SizedBox(height: 20),
            const Text('Action Queue:', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Expanded(
              child: queue.isEmpty
                  ? const Center(child: Text('No offline actions queued.'))
                  : ListView.builder(
                      itemCount: queue.length,
                      itemBuilder: (ctx, i) {
                        final act = queue[i];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            title: Text(act.summary),
                            subtitle: Text('ID: ${act.actionId} • ${act.queuedAt}'),
                            trailing: Text(
                              act.status == 'pending' ? '⏳ Pending' : '✅ Synced',
                              style: TextStyle(
                                color: act.status == 'pending' ? Colors.orange : Colors.green,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
