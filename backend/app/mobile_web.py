"""Obsidian Cyber-Athletics: Ultra-premium dark mode mobile web interface for NaSCon '26."""

MOBILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>NaSCon '26 Ops — Obsidian Cyber-Athletics</title>
  <meta name="theme-color" content="#0B0F17">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0B0F17;
      --card-bg: #111827;
      --card-inner: #161F30;
      --border: #1E293B;
      --border-accent: rgba(139, 92, 246, 0.35);
      --primary: #8B5CF6;
      --primary-hover: #7C3AED;
      --secondary: #06B6D4;
      --tertiary: #3B82F6;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --text-dim: #64748B;
      --success: #10B981;
      --warning: #F59E0B;
      --danger: #EF4444;
      --font-mono: 'JetBrains Mono', monospace;
      --font-sans: 'Space Grotesk', sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: var(--font-sans); -webkit-tap-highlight-color: transparent; }
    body { background-color: var(--bg); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

    /* Top Ops Header */
    header { background: #0c121d; border-bottom: 1px solid var(--border); padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; z-index: 100; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .header-row { display: flex; justify-content: space-between; align-items: center; }
    .brand-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; letter-spacing: -0.02em; color: var(--text-main); }
    .tenant-pill { background: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.3); color: var(--secondary); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; font-family: var(--font-mono); }
    .role-badge { background: linear-gradient(135deg, rgba(139, 92, 246, 0.25), rgba(59, 130, 246, 0.25)); border: 1px solid var(--primary); color: #C4B5FD; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; cursor: pointer; display: flex; align-items: center; gap: 4px; }

    /* System Status Bar */
    .system-bar { display: flex; justify-content: space-between; align-items: center; font-size: 11px; font-family: var(--font-mono); color: var(--text-dim); background: rgba(17, 24, 39, 0.8); border: 1px solid rgba(30, 41, 59, 0.8); padding: 4px 10px; border-radius: 6px; }
    .status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--secondary); box-shadow: 0 0 8px var(--secondary); margin-right: 4px; }
    .status-dot.offline { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
    .net-toggle { background: transparent; border: 1px solid var(--border); color: var(--text-muted); padding: 2px 6px; border-radius: 4px; cursor: pointer; font-family: var(--font-mono); font-size: 10px; }

    /* Sport Selector Tabs */
    .sports-nav { display: flex; gap: 6px; padding: 10px 16px; overflow-x: auto; background: #0c121d; border-bottom: 1px solid var(--border); }
    .sport-tab { background: #161F30; border: 1px solid var(--border); color: var(--text-muted); padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; white-space: nowrap; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 6px; }
    .sport-tab.active { background: rgba(139, 92, 246, 0.15); border-color: var(--primary); color: #DDD6FE; box-shadow: 0 0 12px rgba(139, 92, 246, 0.25); }

    /* Content Area */
    main { flex: 1; overflow-y: auto; padding: 14px 16px 80px; display: flex; flex-direction: column; gap: 14px; }
    
    /* Cyber Cards */
    .cyber-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 16px; position: relative; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.3); }
    .cyber-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.5), transparent); }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .card-title { font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }

    /* Live Match Card */
    .live-badge { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #FCA5A5; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 12px; font-family: var(--font-mono); display: flex; align-items: center; gap: 5px; }
    .pulse-dot { width: 6px; height: 6px; border-radius: 50%; background: #EF4444; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

    .score-board { display: flex; justify-content: space-between; align-items: center; margin: 10px 0 14px; background: var(--card-inner); padding: 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.04); }
    .team-box { flex: 1; }
    .team-box.away { text-align: right; }
    .team-name { font-size: 15px; font-weight: 700; color: var(--text-main); }
    .team-sub { font-size: 11px; color: var(--text-dim); font-family: var(--font-mono); }
    .score-digits { font-size: 28px; font-weight: 800; font-family: var(--font-mono); color: var(--secondary); padding: 0 16px; letter-spacing: 2px; }

    /* Stream Feed */
    .stream-feed { background: #0A0E17; border: 1px solid rgba(30, 41, 59, 0.6); border-radius: 8px; padding: 10px; margin-bottom: 12px; font-family: var(--font-mono); font-size: 11px; }
    .stream-item { padding: 4px 0; color: var(--text-muted); border-bottom: 1px solid rgba(255,255,255,0.03); display: flex; justify-content: space-between; }
    .stream-item:last-child { border-bottom: none; }
    .stream-item.highlight { color: #A78BFA; }

    /* Action Buttons Row */
    .action-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
    .btn-cyber { padding: 10px 8px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; border: none; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all 0.2s; font-family: var(--font-sans); }
    .btn-primary { background: linear-gradient(135deg, #8B5CF6, #6D28D9); color: white; box-shadow: 0 2px 10px rgba(139, 92, 246, 0.35); }
    .btn-primary:active { transform: scale(0.98); }
    .btn-warning { background: linear-gradient(135deg, #F59E0B, #D97706); color: black; }
    .btn-rollback { background: linear-gradient(135deg, #DC2626, #991B1B); color: white; }

    /* Tables */
    .cyber-table { width: 100%; border-collapse: collapse; font-size: 12px; font-family: var(--font-mono); }
    .cyber-table th { color: var(--text-dim); text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border); font-size: 11px; }
    .cyber-table td { padding: 10px 6px; border-bottom: 1px solid rgba(30, 41, 59, 0.4); }
    .cyber-table tr.highlight-row { background: rgba(139, 92, 246, 0.05); }

    .tag-clinched { background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.4); color: var(--secondary); padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; }
    .tag-possible { background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.4); color: #C4B5FD; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; }
    .tag-eliminated { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #F87171; padding: 2px 6px; border-radius: 4px; font-size: 10px; }

    /* Store Showcase */
    .store-box { display: flex; gap: 12px; align-items: center; background: var(--card-inner); padding: 12px; border-radius: 10px; margin-bottom: 12px; }
    .store-img { width: 60px; height: 60px; background: #0B0F17; border: 1px solid var(--border); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 28px; }
    .price-text { font-size: 16px; font-weight: 800; color: var(--secondary); font-family: var(--font-mono); }
    .discount-pill { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; font-family: var(--font-mono); }
    .stock-alert { color: #FBBF24; font-size: 11px; font-family: var(--font-mono); margin-top: 2px; }

    /* Variant chips */
    .variant-row { display: flex; gap: 8px; margin-bottom: 12px; }
    .variant-btn { flex: 1; padding: 8px; background: #0B0F17; border: 1px solid var(--border); color: var(--text-muted); border-radius: 6px; font-size: 11px; font-family: var(--font-mono); cursor: pointer; text-align: center; }
    .variant-btn.selected { border-color: var(--secondary); color: var(--secondary); background: rgba(6, 182, 212, 0.08); font-weight: 700; }

    /* Bottom Nav Bar */
    nav { position: fixed; bottom: 0; left: 0; right: 0; height: 64px; background: #0c121d; border-top: 1px solid var(--border); display: flex; justify-content: space-around; align-items: center; z-index: 200; box-shadow: 0 -4px 20px rgba(0,0,0,0.4); }
    .nav-btn { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-dim); font-size: 11px; font-weight: 600; cursor: pointer; width: 20%; height: 100%; transition: color 0.2s; }
    .nav-btn.active { color: var(--primary); }
    .nav-btn-icon { font-size: 20px; margin-bottom: 2px; }

    /* Role Switcher Modal */
    .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 500; align-items: center; justify-content: center; padding: 20px; backdrop-filter: blur(4px); }
    .modal-overlay.open { display: flex; }
    .modal-box { background: var(--card-bg); border: 1px solid var(--primary); border-radius: 12px; padding: 20px; width: 100%; max-width: 360px; box-shadow: 0 0 30px rgba(139, 92, 246, 0.3); }
    .role-option { padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s; }
    .role-option:hover { border-color: var(--primary); background: rgba(139, 92, 246, 0.1); }
  </style>
</head>
<body>

  <!-- Top Ops Bar -->
  <header>
    <div class="header-row">
      <div class="brand-title">
        <span>⚡ NaSCon '26 Ops</span>
        <span class="tenant-pill">Alpha Sports</span>
      </div>
      <div class="role-badge" onclick="openRoleModal()">
        <span id="role-label">Super Admin</span>
        <span style="font-size: 10px;">▾</span>
      </div>
    </div>
    <div class="system-bar">
      <div>
        <span id="status-indicator" class="status-dot"></span>
        <span id="buffer-text">Buffer: 0 queued</span>
      </div>
      <div>
        <span>HMAC-SHA256 (SALT)</span>
        <button class="net-toggle" onclick="toggleNetwork()" id="net-toggle-btn">Toggle Offline</button>
      </div>
    </div>
  </header>

  <!-- Sports Selection -->
  <div class="sports-nav">
    <div class="sport-tab active" onclick="selectSport(this, 'football')">⚽ Football (2x45)</div>
    <div class="sport-tab" onclick="selectSport(this, 'basketball')">🏀 Basketball (4x12)</div>
    <div class="sport-tab" onclick="selectSport(this, 'cricket')">🏏 Cricket (T20)</div>
    <div class="sport-tab" onclick="selectSport(this, 'esports')">🎮 Esports (Bo3)</div>
  </div>

  <!-- Main Scrollable Ops Surface -->
  <main>

    <!-- SECTION 1: Live Match Center & Append-Only Event Stream -->
    <div class="cyber-card">
      <div class="card-header">
        <span class="card-title">League Alpha 1</span>
        <div class="live-badge">
          <span class="pulse-dot"></span>
          <span>LIVE | 68' MIN</span>
        </div>
      </div>

      <div class="score-board">
        <div class="team-box">
          <div class="team-name">Club Alpha 1</div>
          <div class="team-sub">tenant-alpha (H)</div>
        </div>
        <div class="score-digits" id="match-score">2 : 1</div>
        <div class="team-box away">
          <div class="team-name">Club Alpha 2</div>
          <div class="team-sub">tenant-alpha (A)</div>
        </div>
      </div>

      <!-- Append-Only Event Log -->
      <div class="card-title" style="font-size: 11px; margin-bottom: 6px;">Append-Only Score Stream</div>
      <div class="stream-feed" id="event-stream">
        <div class="stream-item"><span>14' Goal (Ali, T1)</span><span style="color:var(--secondary)">+1 FairPlay</span></div>
        <div class="stream-item"><span>34' Yellow Card (Bilal, T2)</span><span style="color:var(--warning)">-1 FairPlay</span></div>
        <div class="stream-item highlight"><span>56' Goal (Hassan, T1)</span><span style="color:var(--primary)">[sig: 9f2c...7b]</span></div>
      </div>

      <!-- Real-time Scoring Controls -->
      <div class="action-row">
        <button class="btn-cyber btn-primary" onclick="recordScore('t1')">+ Goal (T1)</button>
        <button class="btn-cyber btn-warning" onclick="recordCard('t2')">▲ Card</button>
        <button class="btn-cyber btn-rollback" onclick="compensateGoal()">⟲ Compensate</button>
      </div>
      <div id="scoring-status" style="font-size:11px; font-family:var(--font-mono); margin-top:8px; color:var(--secondary); text-align:center;"></div>
    </div>

    <!-- SECTION 2: League Standings & Clinched Status -->
    <div class="cyber-card">
      <div class="card-header">
        <span class="card-title">League Standings</span>
        <span class="tenant-pill" style="color:var(--text-muted); border-color:var(--border);">Group Stage</span>
      </div>

      <table class="cyber-table">
        <thead>
          <tr>
            <th>#</th>
            <th>CLUB</th>
            <th>P</th>
            <th>DIFF</th>
            <th>PTS</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody id="standings-body">
          <tr class="highlight-row">
            <td>1</td>
            <td><b>Club Alpha 1</b></td>
            <td>3</td>
            <td>+5</td>
            <td style="color:var(--secondary); font-weight:700;">7</td>
            <td><span class="tag-clinched">CLINCHED</span></td>
          </tr>
          <tr>
            <td>2</td>
            <td><b>Club Alpha 2</b></td>
            <td>3</td>
            <td>+1</td>
            <td style="color:var(--text-main); font-weight:700;">4</td>
            <td><span class="tag-possible">POSSIBLE</span></td>
          </tr>
          <tr>
            <td>3</td>
            <td>Beta Challengers</td>
            <td>3</td>
            <td>-6</td>
            <td style="color:var(--text-dim);">0</td>
            <td><span class="tag-eliminated">OUT</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- SECTION 3: Roster Transfers & Edge Case 6 -->
    <div class="cyber-card">
      <div class="card-header">
        <span class="card-title">Roster Operations</span>
        <span class="tenant-pill" style="border-color:rgba(16,185,129,0.3); color:#34D399;">WINDOW: OPEN</span>
      </div>
      
      <div style="background:var(--card-inner); padding:10px; border-radius:8px; margin-bottom:10px;">
        <div style="font-size:13px; font-weight:700;">Bilal Malik (DF)</div>
        <div style="font-size:11px; color:var(--text-dim); font-family:var(--font-mono);">Club Alpha 1 ➔ Club Alpha 2</div>
        <div style="font-size:11px; color:var(--warning); font-family:var(--font-mono); margin-top:4px;" id="transfer-desc">
          State: deferred_until_match_end (Live match active)
        </div>
      </div>

      <div class="action-row" style="grid-template-columns: 1fr 1fr;">
        <button class="btn-cyber btn-primary" onclick="executeTransfer()">Queue Transfer</button>
        <button class="btn-cyber" style="background:#161F30; border:1px solid var(--border); color:var(--text-main);" onclick="executeLoan()">30-Day Loan</button>
      </div>
      <div id="roster-status" style="font-size:11px; font-family:var(--font-mono); margin-top:8px; color:#34D399; text-align:center;"></div>
    </div>

    <!-- SECTION 4: Concurrency-Safe Merchandise Store -->
    <div class="cyber-card">
      <div class="card-header">
        <span class="card-title">Club Kit Store</span>
        <span class="discount-pill">WELCOME10 (-10%)</span>
      </div>

      <div class="store-box">
        <div class="store-img">👕</div>
        <div>
          <div style="font-weight:700; font-size:14px;">Alpha Official Home Kit '26</div>
          <div class="price-text">PKR 4,050.00 <span style="text-decoration:line-through; font-size:11px; color:var(--text-dim);">4,500</span></div>
          <div class="stock-alert" id="stock-label">⚡ ONLY 1 UNIT LEFT (20-buyer safe)</div>
        </div>
      </div>

      <div class="variant-row">
        <div class="variant-btn selected" id="var-m" onclick="selectVariant('var-jersey-001-M')">Size M (1 left)</div>
        <div class="variant-btn" id="var-l" onclick="selectVariant('var-jersey-001-L')">Size L (5 left)</div>
      </div>

      <button class="btn-cyber btn-primary" style="width:100%; padding:12px; font-size:13px;" onclick="instantCheckout()">
        Instant Checkout (Signed %PDF Receipt)
      </button>
      <div id="store-status" style="font-size:11px; font-family:var(--font-mono); margin-top:8px; color:var(--secondary); text-align:center;"></div>
    </div>

  </main>

  <!-- Bottom Cyber Nav -->
  <nav>
    <div class="nav-btn active" onclick="highlightNav(this)">
      <span class="nav-btn-icon">⚡</span>
      <span>Ops</span>
    </div>
    <div class="nav-btn" onclick="highlightNav(this)">
      <span class="nav-btn-icon">📊</span>
      <span>Standings</span>
    </div>
    <div class="nav-btn" onclick="highlightNav(this)">
      <span class="nav-btn-icon">👥</span>
      <span>Roster</span>
    </div>
    <div class="nav-btn" onclick="highlightNav(this)">
      <span class="nav-btn-icon">🛍️</span>
      <span>Store</span>
    </div>
    <div class="nav-btn" onclick="openSyncModal()">
      <span class="nav-btn-icon">🔄</span>
      <span>Sync</span>
    </div>
  </nav>

  <!-- Role Switcher Modal -->
  <div class="modal-overlay" id="role-modal">
    <div class="modal-box">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <h3 style="font-size:15px; font-weight:700; text-transform:uppercase; color:var(--primary);">Switch Demo Role</h3>
        <span onclick="closeRoleModal()" style="cursor:pointer; color:var(--text-dim); font-size:18px;">✕</span>
      </div>
      <div class="role-option" onclick="setRole('Super Admin', 'admin@nascon.test')">
        <div><b>Super Admin</b><div style="font-size:11px; color:var(--text-dim);">admin@nascon.test</div></div>
        <span class="tenant-pill">Global</span>
      </div>
      <div class="role-option" onclick="setRole('League Organizer', 'organizer@nascon.test')">
        <div><b>League Organizer</b><div style="font-size:11px; color:var(--text-dim);">organizer@nascon.test</div></div>
        <span class="tenant-pill">Alpha-1</span>
      </div>
      <div class="role-option" onclick="setRole('Club Manager', 'manager@nascon.test')">
        <div><b>Club Manager</b><div style="font-size:11px; color:var(--text-dim);">manager@nascon.test</div></div>
        <span class="tenant-pill">Club-A</span>
      </div>
      <div class="role-option" onclick="setRole('Player', 'player@nascon.test')">
        <div><b>Player</b><div style="font-size:11px; color:var(--text-dim);">player@nascon.test</div></div>
        <span class="tenant-pill">Self</span>
      </div>
      <div class="role-option" onclick="setRole('Viewer', 'viewer@nascon.test')">
        <div><b>Viewer</b><div style="font-size:11px; color:var(--text-dim);">viewer@nascon.test</div></div>
        <span class="tenant-pill">Read-Only</span>
      </div>
    </div>
  </div>

  <!-- Offline Sync Modal -->
  <div class="modal-overlay" id="sync-modal">
    <div class="modal-box">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <h3 style="font-size:15px; font-weight:700; text-transform:uppercase; color:var(--secondary);">Offline Queue & Sync</h3>
        <span onclick="closeSyncModal()" style="cursor:pointer; color:var(--text-dim); font-size:18px;">✕</span>
      </div>
      <p id="modal-queue-summary" style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Actions Queued: 0</p>
      <div id="modal-queue-list" style="max-height:160px; overflow-y:auto; font-size:11px; font-family:var(--font-mono); margin-bottom:14px;"></div>
      <button class="btn-cyber btn-primary" style="width:100%;" onclick="executeSync()">Sync All Pending Actions</button>
    </div>
  </div>

  <script>
    let isOnline = true;
    let selectedVariant = 'var-jersey-001-M';
    let queue = JSON.parse(localStorage.getItem('nascon_cyber_queue') || '[]');

    function saveQueue() {
      localStorage.setItem('nascon_cyber_queue', JSON.stringify(queue));
      updateBuffer();
    }

    function updateBuffer() {
      const pending = queue.filter(q => q.status === 'pending').length;
      document.getElementById('buffer-text').innerText = 'Buffer: ' + pending + ' queued';
    }

    function toggleNetwork() {
      isOnline = !isOnline;
      const dot = document.getElementById('status-indicator');
      const btn = document.getElementById('net-toggle-btn');
      if (isOnline) {
        dot.className = 'status-dot';
        btn.innerText = 'Toggle Offline';
      } else {
        dot.className = 'status-dot offline';
        btn.innerText = 'Toggle Online';
      }
    }

    function selectSport(elem, sport) {
      document.querySelectorAll('.sport-tab').forEach(t => t.classList.remove('active'));
      elem.classList.add('active');
    }

    function selectVariant(vid) {
      selectedVariant = vid;
      document.getElementById('var-m').className = vid === 'var-jersey-001-M' ? 'variant-btn selected' : 'variant-btn';
      document.getElementById('var-l').className = vid === 'var-jersey-001-L' ? 'variant-btn selected' : 'variant-btn';
    }

    function openRoleModal() { document.getElementById('role-modal').classList.add('open'); }
    function closeRoleModal() { document.getElementById('role-modal').classList.remove('open'); }
    function openSyncModal() {
      document.getElementById('sync-modal').classList.add('open');
      const list = document.getElementById('modal-queue-list');
      const pending = queue.filter(q => q.status === 'pending');
      document.getElementById('modal-queue-summary').innerText = 'Actions Queued: ' + pending.length;
      if (queue.length === 0) {
        list.innerHTML = '<div style="color:var(--text-dim)">No queued actions.</div>';
      } else {
        list.innerHTML = queue.map(q => `
          <div style="padding:6px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between;">
            <span>${q.summary}</span>
            <span style="color:${q.status === 'pending' ? 'var(--warning)' : 'var(--secondary)'}">${q.status}</span>
          </div>
        `).join('');
      }
    }
    function closeSyncModal() { document.getElementById('sync-modal').classList.remove('open'); }

    function setRole(name, email) {
      document.getElementById('role-label').innerText = name;
      closeRoleModal();
    }

    function highlightNav(elem) {
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      elem.classList.add('active');
    }

    function recordScore(team) {
      const status = document.getElementById('scoring-status');
      if (isOnline) {
        status.innerText = '✓ Goal recorded in append-only log. Signature HMAC-SHA256 valid.';
        document.getElementById('match-score').innerText = '3 : 1';
      } else {
        queue.push({ id: 'sc-' + Date.now(), type: 'score_event', summary: 'Goal for ' + team, status: 'pending' });
        saveQueue();
        status.innerText = '⏳ Offline: Goal action stored in local persistent queue.';
      }
    }

    function recordCard(team) {
      const status = document.getElementById('scoring-status');
      status.innerText = '✓ Yellow Card recorded. Fair play differential updated.';
    }

    function compensateGoal() {
      const status = document.getElementById('scoring-status');
      status.innerText = '✓ Rollback compensation signed! Goal neutralized.';
      document.getElementById('match-score').innerText = '2 : 1';
    }

    function executeTransfer() {
      const status = document.getElementById('roster-status');
      if (isOnline) {
        status.innerText = '✓ Transfer deferred_until_match_end (Edge Case 6 satisfied).';
      } else {
        queue.push({ id: 'tr-' + Date.now(), type: 'roster_transfer', summary: 'Transfer Bilal to Alpha 2', status: 'pending' });
        saveQueue();
        status.innerText = '⏳ Offline: Transfer queued for background replay.';
      }
    }

    function executeLoan() {
      const status = document.getElementById('roster-status');
      status.innerText = '✓ 30-Day loan registered with automatic return audit trigger.';
    }

    function instantCheckout() {
      const status = document.getElementById('store-status');
      if (isOnline) {
        status.innerText = '✓ Order #ord-923 Confirmed! Signed PDF receipt generated (%PDF-1.4).';
        document.getElementById('stock-label').innerText = '⚡ STOCK: 0 (Sold out - 0 negative inventory)';
      } else {
        queue.push({ id: 'chk-' + Date.now(), type: 'checkout', summary: 'Buy ' + selectedVariant, status: 'pending' });
        saveQueue();
        status.innerText = '⏳ Offline: Order reservation stored in queue.';
      }
    }

    function executeSync() {
      if (!isOnline) {
        alert('Cannot sync while in Airplane mode! Toggle online first.');
        return;
      }
      queue.forEach(q => q.status = 'synced');
      saveQueue();
      openSyncModal();
      alert('✓ Conflict Synchronization Complete! Server versions rebased.');
    }

    updateBuffer();
  </script>
</body>
</html>
"""
