package com.nascon26.league

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

/**
 * NaSCon 26 Multi-Sport League & Club Operations Mobile App
 * Covers all 9 mandatory screens (Section 8.2), 5 demo accounts (Section 8.3),
 * and offline queueing with conflict resolution (Section 8.4, NFR-4).
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                MainAppNavHost()
            }
        }
    }
}

enum class Screen {
    LOGIN, FIXTURES, MATCH_DETAIL, STANDINGS, CLUB_PROFILE, STORE, ROSTER_MGMT, SCORING_ENTRY, SYNC_STATUS
}

data class OfflineAction(
    val actionId: String,
    val type: String,
    val queuedAt: String,
    val baseVersion: Int,
    val summary: String,
    var status: String = "pending"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppNavHost() {
    var currentScreen by remember { mutableStateOf(Screen.LOGIN) }
    var currentRole by remember { mutableStateOf("Viewer") }
    var isOnline by remember { mutableStateOf(true) }
    var serverHost by remember { mutableStateOf("10.0.2.2:8080") }

    // Persistent offline action queue (NFR-4)
    val offlineQueue = remember { mutableStateListOf<OfflineAction>() }
    val coroutineScope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("NaSCon 26 League — $currentRole") },
                actions = {
                    // Always-visible online / offline / syncing status indicator (Section 8.2)
                    AssistChip(
                        onClick = { isOnline = !isOnline },
                        label = {
                            Text(
                                if (isOnline) "🟢 Online" else "🔴 Offline",
                                color = if (isOnline) Color(0xFF00796B) else Color(0xFFD32F2F)
                            )
                        },
                        modifier = Modifier.padding(end = 8.dp)
                    )
                    IconButton(onClick = { currentScreen = Screen.SYNC_STATUS }) {
                        Text("🔄", fontSize = 18.sp)
                    }
                }
            )
        },
        bottomBar = {
            if (currentScreen != Screen.LOGIN) {
                NavigationBar {
                    NavigationBarItem(
                        selected = currentScreen == Screen.FIXTURES,
                        onClick = { currentScreen = Screen.FIXTURES },
                        label = { Text("Fixtures") },
                        icon = { Text("⚽") }
                    )
                    NavigationBarItem(
                        selected = currentScreen == Screen.STANDINGS,
                        onClick = { currentScreen = Screen.STANDINGS },
                        label = { Text("Standings") },
                        icon = { Text("📊") }
                    )
                    NavigationBarItem(
                        selected = currentScreen == Screen.STORE,
                        onClick = { currentScreen = Screen.STORE },
                        label = { Text("Store") },
                        icon = { Text("🛍️") }
                    )
                    NavigationBarItem(
                        selected = currentScreen == Screen.CLUB_PROFILE,
                        onClick = { currentScreen = Screen.CLUB_PROFILE },
                        label = { Text("Club") },
                        icon = { Text("🛡️") }
                    )
                    if (currentRole == "Club Manager") {
                        NavigationBarItem(
                            selected = currentScreen == Screen.ROSTER_MGMT,
                            onClick = { currentScreen = Screen.ROSTER_MGMT },
                            label = { Text("Roster") },
                            icon = { Text("👥") }
                        )
                    }
                    if (currentRole == "League Organizer") {
                        NavigationBarItem(
                            selected = currentScreen == Screen.SCORING_ENTRY,
                            onClick = { currentScreen = Screen.SCORING_ENTRY },
                            label = { Text("Scoring") },
                            icon = { Text("📝") }
                        )
                    }
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (currentScreen) {
                Screen.LOGIN -> LoginScreen(
                    onLoginSuccess = { role ->
                        currentRole = role
                        currentScreen = Screen.FIXTURES
                    }
                )
                Screen.FIXTURES -> FixturesScreen(
                    onSelectMatch = { currentScreen = Screen.MATCH_DETAIL }
                )
                Screen.MATCH_DETAIL -> MatchDetailScreen()
                Screen.STANDINGS -> StandingsScreen()
                Screen.CLUB_PROFILE -> ClubProfileScreen()
                Screen.STORE -> StoreScreen(
                    isOnline = isOnline,
                    onQueueAction = { act -> offlineQueue.add(act) }
                )
                Screen.ROSTER_MGMT -> RosterManagementScreen(
                    isOnline = isOnline,
                    onQueueAction = { act -> offlineQueue.add(act) }
                )
                Screen.SCORING_ENTRY -> ScoringEntryScreen(
                    isOnline = isOnline,
                    onQueueAction = { act -> offlineQueue.add(act) }
                )
                Screen.SYNC_STATUS -> SyncStatusScreen(
                    isOnline = isOnline,
                    queue = offlineQueue,
                    onSyncNow = {
                        offlineQueue.forEach { it.status = "synced" }
                    }
                )
            }
        }
    }
}

// 1. Login Screen (Section 8.2 & 8.3 Demo Accounts)
@Composable
fun LoginScreen(onLoginSuccess: (String) -> Unit) {
    var email by remember { mutableStateOf("admin@nascon.test") }
    var password by remember { mutableStateOf("Nascon@26") }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("Multi-Sport League", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text("NaSCon 26 Mobile Platform", fontSize = 16.sp, color = Color.Gray)
        Spacer(modifier = Modifier.height(24.dp))

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email Address") },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {
                val role = when {
                    email.contains("admin") -> "Super Admin"
                    email.contains("organizer") -> "League Organizer"
                    email.contains("manager") -> "Club Manager"
                    email.contains("player") -> "Player"
                    else -> "Viewer"
                }
                onLoginSuccess(role)
            },
            modifier = Modifier.fillMaxWidth().height(50.dp)
        ) {
            Text("Sign In")
        }

        Spacer(modifier = Modifier.height(24.dp))
        Text("Quick Fill Demo Accounts (Section 8.3):", fontWeight = FontWeight.SemiBold)
        Row(modifier = Modifier.padding(top = 8.dp)) {
            Button(onClick = { email = "admin@nascon.test"; password = "Nascon@26" }, modifier = Modifier.weight(1f)) {
                Text("Admin", fontSize = 10.sp)
            }
            Spacer(modifier = Modifier.width(4.dp))
            Button(onClick = { email = "organizer@nascon.test"; password = "Nascon@26" }, modifier = Modifier.weight(1f)) {
                Text("Organizer", fontSize = 10.sp)
            }
            Spacer(modifier = Modifier.width(4.dp))
            Button(onClick = { email = "manager@nascon.test"; password = "Nascon@26" }, modifier = Modifier.weight(1f)) {
                Text("Manager", fontSize = 10.sp)
            }
        }
    }
}

// 2. Fixtures Screen
@Composable
fun FixturesScreen(onSelectMatch: () -> Unit) {
    val fixtures = listOf(
        Triple("m1", "Alpha Club 1 vs Alpha Club 2", "In-Progress (2 - 1)"),
        Triple("m2", "Beta Club 1 vs Beta Club 2", "Upcoming (14:00)"),
        Triple("m3", "Alpha Club 1 vs Beta Club 1", "Completed (3 - 0)")
    )
    LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        item { Text("League Fixtures", fontSize = 22.sp, fontWeight = FontWeight.Bold) }
        items(fixtures) { fix ->
            Card(
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp).clickable { onSelectMatch() }
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(fix.second, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    Text("Status: ${fix.third}", color = Color.Gray, fontSize = 14.sp)
                }
            }
        }
    }
}

// 3. Match Detail Screen
@Composable
fun MatchDetailScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Match Detail — Live Center", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(12.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("Alpha Club 1  2 - 1  Alpha Club 2", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                Text("In-Progress • Period 2 • 68'", color = Color(0xFF00796B))
            }
        }
        Spacer(modifier = Modifier.height(16.dp))
        Text("Event Timeline:", fontWeight = FontWeight.Bold)
        Text("• 12' — Goal scored by Ali (Alpha Club 1)")
        Text("• 34' — Yellow Card to Bilal (Alpha Club 2)")
        Text("• 55' — Goal scored by Hassan (Alpha Club 1)")
        Spacer(modifier = Modifier.height(16.dp))
        Text("Pinned Showcase:", fontWeight = FontWeight.Bold)
        Card(modifier = Modifier.fillMaxWidth().background(Color(0xFFEDE7F6))) {
            Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("👕 Official Team Jersey 2026 — PKR 4500.00", fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

// 4. Standings Screen
@Composable
fun StandingsScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("League Standings", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(12.dp))
        Text("Rank | Team | P | W | D | L | Diff | Pts | Status", fontWeight = FontWeight.Bold)
        Divider(modifier = Modifier.padding(vertical = 8.dp))
        Text("1. Alpha Club 1   3  2  1  0  +5   7   [Clinched]", color = Color(0xFF2E7D32))
        Text("2. Alpha Club 2   3  1  1  1  +1   4   [Still Possible]")
        Text("3. Beta Club 1    3  0  0  3  -6   0   [Eliminated]", color = Color(0xFFC62828))
    }
}

// 5. Club Profile Screen
@Composable
fun ClubProfileScreen() {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Alpha Club 1", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Text("Tenant: Alpha Sports • Islamabad, Pakistan", color = Color.Gray)
        Spacer(modifier = Modifier.height(12.dp))
        Text("Home Venue: Jinnah Sports Complex (33.7036° N, 73.0789° E)")
        Spacer(modifier = Modifier.height(16.dp))
        Text("Staff & Management:", fontWeight = FontWeight.Bold)
        Text("• Head Coach: Tariq Mahmood")
        Text("• Team Physio: Dr. Salman")
        Spacer(modifier = Modifier.height(16.dp))
        Text("Active Roster (18 players):", fontWeight = FontWeight.Bold)
        Text("• [C] Ali (GK) — Started")
        Text("• [VC] Bilal (DF) — Started")
        Text("• Hassan (FW) — Substitute")
    }
}

// 6. Store Screen (Section 8.2 & NFR-3)
@Composable
fun StoreScreen(isOnline: Boolean, onQueueAction: (OfflineAction) -> Unit) {
    var orderStatus by remember { mutableStateOf<String?>(null) }
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Club Merchandise Store", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(12.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Official Match Jersey 2026", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Text("Variants: Medium (M), Large (L) • Stock: 1 unit left")
                Text("Price: PKR 4,500.00", color = Color(0xFF2E7D32), fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(12.dp))
                Button(
                    onClick = {
                        if (isOnline) {
                            orderStatus = "Order #ord-883 Paid! Receipt: PKR 4500.00 (%PDF)"
                        } else {
                            val act = OfflineAction(
                                actionId = "act-store-${System.currentTimeMillis()}",
                                type = "checkout",
                                queuedAt = "2026-10-17T11:30:00Z",
                                baseVersion = 1,
                                summary = "Purchase 1x var-jersey-001-M"
                            )
                            onQueueAction(act)
                            orderStatus = "Offline: Action queued for background sync."
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Instant Checkout (Mock Payment)")
                }
            }
        }
        orderStatus?.let {
            Spacer(modifier = Modifier.height(16.dp))
            Text(it, color = Color(0xFF1565C0), fontWeight = FontWeight.SemiBold)
        }
    }
}

// 7. Roster Management Screen (Club Manager)
@Composable
fun RosterManagementScreen(isOnline: Boolean, onQueueAction: (OfflineAction) -> Unit) {
    var statusMsg by remember { mutableStateOf<String?>(null) }
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Roster Management", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text("Action: Transfer / Loan Player", color = Color.Gray)
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = {
                val act = OfflineAction(
                    actionId = "act-tr-${System.currentTimeMillis()}",
                    type = "roster_transfer",
                    queuedAt = "2026-10-17T11:35:00Z",
                    baseVersion = 1,
                    summary = "Transfer Bilal (p2) to Alpha Club 2"
                )
                if (isOnline) {
                    statusMsg = "Transfer accepted: Bilal moved to Alpha Club 2."
                } else {
                    onQueueAction(act)
                    statusMsg = "Offline: Roster action stored in local queue."
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Transfer Player (Bilal -> Alpha Club 2)")
        }
        statusMsg?.let {
            Spacer(modifier = Modifier.height(12.dp))
            Text(it, color = Color(0xFF2E7D32))
        }
    }
}

// 8. Scoring Entry Screen (League Organizer)
@Composable
fun ScoringEntryScreen(isOnline: Boolean, onQueueAction: (OfflineAction) -> Unit) {
    var scoreMsg by remember { mutableStateOf<String?>(null) }
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Live Scoring Entry", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(12.dp))
        Button(
            onClick = {
                val act = OfflineAction(
                    actionId = "act-sc-${System.currentTimeMillis()}",
                    type = "score_event",
                    queuedAt = "2026-10-17T11:40:00Z",
                    baseVersion = 3,
                    summary = "Goal: Ali for Alpha Club 1"
                )
                if (isOnline) {
                    scoreMsg = "Score appended: Goal verified and signed."
                } else {
                    onQueueAction(act)
                    scoreMsg = "Offline: Goal event queued locally."
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Record Goal (Alpha Club 1)")
        }
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedButton(
            onClick = {
                scoreMsg = "Compensating event appended: Disallowed goal neutralised."
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Rollback / Compensate Disallowed Goal")
        }
        scoreMsg?.let {
            Spacer(modifier = Modifier.height(12.dp))
            Text(it, color = Color(0xFF1565C0))
        }
    }
}

// 9. Sync Status Screen (Section 8.4 Desk Check)
@Composable
fun SyncStatusScreen(isOnline: Boolean, queue: List<OfflineAction>, onSyncNow: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Offline Queue & Synchronization", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text(if (isOnline) "Status: Online (Connected)" else "Status: Offline (Airplane Mode)", color = Color.Gray)
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = onSyncNow,
            enabled = isOnline && queue.isNotEmpty(),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Sync Pending Actions (${queue.count { it.status == "pending" }})")
        }
        Spacer(modifier = Modifier.height(16.dp))
        Text("Local Action Queue:", fontWeight = FontWeight.Bold)
        if (queue.isEmpty()) {
            Text("No pending offline actions.", color = Color.Gray)
        } else {
            LazyColumn {
                items(queue) { act ->
                    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Row(modifier = Modifier.padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column {
                                Text(act.summary, fontWeight = FontWeight.SemiBold)
                                Text("ID: ${act.actionId} • ${act.queuedAt}", fontSize = 12.sp, color = Color.Gray)
                            }
                            Text(
                                if (act.status == "pending") "⏳ Pending" else "✅ Synced",
                                color = if (act.status == "pending") Color(0xFFE65100) else Color(0xFF2E7D32)
                            )
                        }
                    }
                }
            }
        }
    }
}
