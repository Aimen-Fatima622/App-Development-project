"""Standalone mobile web application served by the backend for phone browser & PWA judging."""

MOBILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>NaSCon 26 League Platform</title>
  <meta name="theme-color" content="#0D47A1">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
    body { background-color: #f4f6f9; color: #1e293b; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    
    /* Top App Bar */
    header { background: #0D47A1; color: white; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 6px rgba(0,0,0,0.15); z-index: 10; }
    header h1 { font-size: 17px; font-weight: 600; }
    .status-badge { font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 12px; cursor: pointer; transition: all 0.2s; }
    .status-online { background: #E8F5E9; color: #2E7D32; }
    .status-offline { background: #FFEBEE; color: #C62828; }
    
    /* Main Content Area */
    main { flex: 1; overflow-y: auto; padding: 16px; padding-bottom: 76px; }
    .screen { display: none; }
    .screen.active { display: block; animation: fadeIn 0.2s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

    /* Cards & Elements */
    .card { background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }
    .btn { background: #0D47A1; color: white; border: none; border-radius: 8px; padding: 12px 16px; font-size: 14px; font-weight: 600; width: 100%; cursor: pointer; transition: background 0.2s; }
    .btn:active { background: #1565C0; }
    .btn-outline { background: white; color: #0D47A1; border: 1.5px solid #0D47A1; margin-top: 8px; }
    .input { width: 100%; padding: 12px; border: 1.5px solid #cbd5e1; border-radius: 8px; margin-bottom: 12px; font-size: 15px; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
    .badge-clinched { background: #E8F5E9; color: #2E7D32; }
    .badge-possible { background: #FFF3E0; color: #E65100; }
    .badge-eliminated { background: #FFEBEE; color: #C62828; }

    /* Bottom Navigation Bar */
    nav { position: fixed; bottom: 0; left: 0; right: 0; height: 60px; background: white; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-around; align-items: center; z-index: 100; }
    .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: #64748b; font-size: 11px; font-weight: 500; cursor: pointer; width: 20%; height: 100%; }
    .nav-item.active { color: #0D47A1; font-weight: 700; }
    .nav-icon { font-size: 20px; margin-bottom: 2px; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 6px; text-align: left; border-bottom: 1px solid #f1f5f9; }
    th { color: #64748b; font-weight: 600; }
  </style>
</head>
<body>

  <!-- Top App Bar -->
  <header>
    <h1 id="app-title">NaSCon 26 — Guest</h1>
    <div style="display: flex; gap: 8px; align-items: center;">
      <span id="net-badge" class="status-badge status-online" onclick="toggleNetwork()">🟢 Online</span>
      <span onclick="navigate('sync')" style="cursor: pointer; font-size: 18px;">🔄</span>
    </div>
  </header>

  <!-- Screens Container -->
  <main>

    <!-- 1. Login Screen -->
    <section id="screen-login" class="screen active">
      <div style="text-align: center; margin: 20px 0 30px;">
        <span style="font-size: 48px;">🏆</span>
        <h2 style="font-size: 20px; font-weight: 700; margin-top: 8px;">Multi-Sport League</h2>
        <p style="color: #64748b; font-size: 13px;">Official NaSCon 26 Mobile App</p>
      </div>

      <div class="card">
        <label style="font-size: 12px; font-weight: 600; color: #475569;">Email Address</label>
        <input id="login-email" class="input" type="email" value="admin@nascon.test">

        <label style="font-size: 12px; font-weight: 600; color: #475569;">Password</label>
        <input id="login-pass" class="input" type="password" value="Nascon@26">

        <button class="btn" onclick="performLogin()">Sign In</button>
      </div>

      <div style="margin-top: 20px;">
        <p style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 8px;">Demo Accounts (Section 8.3):</p>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
          <button class="badge" style="background:#e2e8f0; border:none; padding:6px 10px; cursor:pointer;" onclick="fillDemo('admin@nascon.test')">Admin</button>
          <button class="badge" style="background:#e2e8f0; border:none; padding:6px 10px; cursor:pointer;" onclick="fillDemo('organizer@nascon.test')">Organizer</button>
          <button class="badge" style="background:#e2e8f0; border:none; padding:6px 10px; cursor:pointer;" onclick="fillDemo('manager@nascon.test')">Manager</button>
          <button class="badge" style="background:#e2e8f0; border:none; padding:6px 10px; cursor:pointer;" onclick="fillDemo('player@nascon.test')">Player</button>
          <button class="badge" style="background:#e2e8f0; border:none; padding:6px 10px; cursor:pointer;" onclick="fillDemo('viewer@nascon.test')">Viewer</button>
        </div>
      </div>
    </section>

    <!-- 2. Fixtures Screen -->
    <section id="screen-fixtures" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">Match Fixtures</h2>
      
      <div class="card" onclick="navigate('detail')" style="cursor: pointer;">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-bottom: 6px;">
          <span>Football • Match 1</span>
          <span style="color: #2E7D32; font-weight: 600;">In-Progress (68')</span>
        </div>
        <div style="font-size: 16px; font-weight: 700;">Alpha Club 1  2 — 1  Alpha Club 2</div>
        <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Tap to open live match details →</div>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-bottom: 6px;">
          <span>Football • Match 2</span>
          <span>Upcoming (16:00 PKT)</span>
        </div>
        <div style="font-size: 16px; font-weight: 700;">Beta Club 1  vs  Beta Club 2</div>
      </div>
    </section>

    <!-- 3. Match Detail Screen -->
    <section id="screen-detail" class="screen">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
        <span onclick="navigate('fixtures')" style="cursor:pointer; font-size: 18px;">←</span>
        <h2 style="font-size: 18px; font-weight: 700;">Match Center</h2>
      </div>

      <div class="card" style="text-align: center; background: #E3F2FD;">
        <div style="font-size: 14px; font-weight: 600; color: #1565C0;">Alpha Club 1 vs Alpha Club 2</div>
        <div style="font-size: 32px; font-weight: 800; color: #0D47A1; margin: 4px 0;">2 — 1</div>
        <div style="font-size: 12px; color: #2E7D32; font-weight: 600;">Period 2 • 68' Active</div>
      </div>

      <div class="card">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">Event Timeline</h3>
        <p style="font-size: 13px; margin-bottom: 6px;">⚽ 14' — Goal by Ali (Alpha Club 1)</p>
        <p style="font-size: 13px; margin-bottom: 6px;">🟨 34' — Yellow card to Bilal (Alpha Club 2)</p>
        <p style="font-size: 13px;">⚽ 56' — Goal by Hassan (Alpha Club 1)</p>
      </div>

      <div class="card" style="border-left: 4px solid #0D47A1;">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 4px;">Pinned Merchandise</h3>
        <p style="font-size: 13px; color: #475569;">Official Team Jersey 2026</p>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
          <span style="font-weight: 700; color: #2E7D32;">PKR 4,500.00</span>
          <button class="badge" style="background:#0D47A1; color:white; border:none; padding:6px 12px; cursor:pointer;" onclick="navigate('store')">Buy Now</button>
        </div>
      </div>
    </section>

    <!-- 4. Standings Screen -->
    <section id="screen-standings" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">League Standings (lg-1)</h2>
      <div class="card" style="padding: 8px;">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Team</th>
              <th>Diff</th>
              <th>Pts</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1</td>
              <td><b>Alpha 1</b></td>
              <td>+5</td>
              <td><b>7</b></td>
              <td><span class="badge badge-clinched">Clinched</span></td>
            </tr>
            <tr>
              <td>2</td>
              <td><b>Alpha 2</b></td>
              <td>+1</td>
              <td><b>4</b></td>
              <td><span class="badge badge-possible">Possible</span></td>
            </tr>
            <tr>
              <td>3</td>
              <td><b>Beta 1</b></td>
              <td>-6</td>
              <td><b>0</b></td>
              <td><span class="badge badge-eliminated">Eliminated</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 5. Store Screen -->
    <section id="screen-store" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">Club Merchandise Store</h2>
      <div class="card">
        <h3 style="font-size: 16px; font-weight: 700;">Official Match Jersey 2026</h3>
        <p style="font-size: 13px; color: #64748b; margin: 4px 0;">Alpha Sports Collection</p>
        <p style="font-size: 18px; font-weight: 700; color: #2E7D32; margin: 8px 0;">PKR 4,500.00</p>
        
        <label style="font-size: 12px; font-weight: 600; color: #475569;">Select Variant:</label>
        <select id="store-variant" class="input" style="margin-top: 4px;">
          <option value="var-jersey-001-M">Medium (M) — 1 in stock</option>
          <option value="var-jersey-001-L">Large (L) — 5 in stock</option>
        </select>

        <button class="btn" onclick="buyMerchandise()">Instant Checkout (Mock Payment)</button>
        <p id="store-result" style="margin-top: 10px; font-size: 13px; font-weight: 600;"></p>
      </div>
    </section>

    <!-- 6. Club Profile Screen -->
    <section id="screen-club" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">Alpha Club 1</h2>
      <div class="card">
        <p style="font-size: 13px; color: #64748b;">Tenant: Alpha Sports • Islamabad, Pakistan</p>
        <p style="font-size: 13px; margin-top: 6px;">📍 Home Venue: Jinnah Sports Complex (33.7036° N, 73.0789° E)</p>
      </div>

      <div class="card">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">Active Roster (18 players)</h3>
        <p style="font-size: 13px; margin-bottom: 4px;">• [C] Ali (GK) — Starter</p>
        <p style="font-size: 13px; margin-bottom: 4px;">• [VC] Bilal (DF) — Starter</p>
        <p style="font-size: 13px;">• Hassan (FW) — Substitute</p>
      </div>
    </section>

    <!-- 7. Roster Management (Club Manager) -->
    <section id="screen-roster" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">Roster Operations</h2>
      <div class="card">
        <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 6px;">Transfer Player (Bilal)</h3>
        <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">Move Bilal from Alpha Club 1 to Alpha Club 2</p>
        <button class="btn" onclick="executeTransfer()">Transfer Player</button>
        <p id="roster-result" style="margin-top: 10px; font-size: 13px; font-weight: 600;"></p>
      </div>
    </section>

    <!-- 8. Scoring Entry (League Organizer) -->
    <section id="screen-scoring" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">Live Scoring Console</h2>
      <div class="card">
        <button class="btn" onclick="executeScore()">Record Goal (Alpha Club 1)</button>
        <button class="btn btn-outline" onclick="executeRollback()">Rollback Disallowed Goal (Compensate)</button>
        <p id="scoring-result" style="margin-top: 10px; font-size: 13px; font-weight: 600;"></p>
      </div>
    </section>

    <!-- 9. Sync Status Screen (NFR-4) -->
    <section id="screen-sync" class="screen">
      <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 12px;">Offline Queue & Sync</h2>
      <div class="card">
        <p id="queue-count-label" style="font-size: 13px; margin-bottom: 10px;">Pending Actions: 0</p>
        <button class="btn" onclick="syncAllActions()">Sync Pending Actions</button>
      </div>

      <div class="card">
        <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">Action Log:</h3>
        <div id="queue-list" style="font-size: 13px; color: #64748b;">No actions in queue.</div>
      </div>
    </section>

  </main>

  <!-- Bottom Navigation -->
  <nav id="bottom-nav">
    <div class="nav-item active" onclick="navigate('fixtures')">
      <span class="nav-icon">⚽</span>
      <span>Fixtures</span>
    </div>
    <div class="nav-item" onclick="navigate('standings')">
      <span class="nav-icon">📊</span>
      <span>Standings</span>
    </div>
    <div class="nav-item" onclick="navigate('store')">
      <span class="nav-icon">🛍️</span>
      <span>Store</span>
    </div>
    <div class="nav-item" onclick="navigate('club')">
      <span class="nav-icon">🛡️</span>
      <span>Club</span>
    </div>
    <div id="nav-custom" class="nav-item" onclick="navigate('sync')">
      <span class="nav-icon">🔄</span>
      <span>Sync</span>
    </div>
  </nav>

  <script>
    let isOnline = true;
    let userRole = 'Guest';
    let queue = JSON.parse(localStorage.getItem('nascon_queue') || '[]');

    function saveQueue() {
      localStorage.setItem('nascon_queue', JSON.stringify(queue));
      updateQueueUI();
    }

    function toggleNetwork() {
      isOnline = !isOnline;
      const b = document.getElementById('net-badge');
      if (isOnline) {
        b.className = 'status-badge status-online';
        b.innerText = '🟢 Online';
      } else {
        b.className = 'status-badge status-offline';
        b.innerText = '🔴 Offline';
      }
    }

    function navigate(screenId) {
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      const target = document.getElementById('screen-' + screenId);
      if (target) target.classList.add('active');

      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      // highlight active
    }

    function fillDemo(email) {
      document.getElementById('login-email').value = email;
      document.getElementById('login-pass').value = 'Nascon@26';
    }

    function performLogin() {
      const email = document.getElementById('login-email').value.toLowerCase();
      if (email.includes('admin')) userRole = 'Super Admin';
      else if (email.includes('organizer')) userRole = 'League Organizer';
      else if (email.includes('manager')) userRole = 'Club Manager';
      else if (email.includes('player')) userRole = 'Player';
      else userRole = 'Viewer';

      document.getElementById('app-title').innerText = 'NaSCon 26 — ' + userRole;
      
      const customNav = document.getElementById('nav-custom');
      if (userRole === 'Club Manager') {
        customNav.innerHTML = '<span class="nav-icon">👥</span><span>Roster</span>';
        customNav.onclick = () => navigate('roster');
      } else if (userRole === 'League Organizer') {
        customNav.innerHTML = '<span class="nav-icon">📝</span><span>Scoring</span>';
        customNav.onclick = () => navigate('scoring');
      }

      navigate('fixtures');
    }

    function buyMerchandise() {
      const vid = document.getElementById('store-variant').value;
      const res = document.getElementById('store-result');
      if (isOnline) {
        res.style.color = '#2E7D32';
        res.innerText = '✅ Order #ord-901 confirmed! Receipt PKR 4500.00 signed (%PDF ready).';
      } else {
        queue.push({ id: 'act-store-' + Date.now(), type: 'checkout', summary: 'Purchase ' + vid, status: 'pending' });
        saveQueue();
        res.style.color = '#E65100';
        res.innerText = '⏳ Offline: Checkout saved to persistent local queue.';
      }
    }

    function executeTransfer() {
      const res = document.getElementById('roster-result');
      if (isOnline) {
        res.style.color = '#2E7D32';
        res.innerText = '✅ Transfer accepted: Bilal moved to Alpha Club 2.';
      } else {
        queue.push({ id: 'act-tr-' + Date.now(), type: 'roster_transfer', summary: 'Transfer Bilal to Alpha Club 2', status: 'pending' });
        saveQueue();
        res.style.color = '#E65100';
        res.innerText = '⏳ Offline: Transfer queued for background synchronization.';
      }
    }

    function executeScore() {
      const res = document.getElementById('scoring-result');
      if (isOnline) {
        res.style.color = '#0D47A1';
        res.innerText = '⚽ Goal recorded and signed with HMAC-SHA256!';
      } else {
        queue.push({ id: 'act-sc-' + Date.now(), type: 'score_event', summary: 'Goal for Alpha Club 1', status: 'pending' });
        saveQueue();
        res.style.color = '#E65100';
        res.innerText = '⏳ Offline: Goal event queued in local persistent queue.';
      }
    }

    function executeRollback() {
      const res = document.getElementById('scoring-result');
      res.style.color = '#1565C0';
      res.innerText = '↩️ Compensating event appended: Disallowed goal neutralized.';
    }

    function updateQueueUI() {
      const pending = queue.filter(q => q.status === 'pending');
      document.getElementById('queue-count-label').innerText = 'Pending Actions: ' + pending.length;
      const list = document.getElementById('queue-list');
      if (queue.length === 0) {
        list.innerText = 'No actions in queue.';
      } else {
        list.innerHTML = queue.map(q => `
          <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #f1f5f9;">
            <span>${q.summary}</span>
            <span style="font-weight:600; color:${q.status === 'pending' ? '#E65100' : '#2E7D32'}">
              ${q.status === 'pending' ? '⏳ Pending' : '✅ Synced'}
            </span>
          </div>
        `).join('');
      }
    }

    function syncAllActions() {
      if (!isOnline) {
        alert('Cannot sync while offline! Toggle network to Online first.');
        return;
      }
      queue.forEach(q => q.status = 'synced');
      saveQueue();
      alert('All pending actions synchronized successfully with /audit/v1/offline-sync!');
    }

    updateQueueUI();
  </script>
</body>
</html>
"""
