#!/usr/bin/env python3
"""
Simple web dashboard for SCRAP3R error monitoring
"""

from flask import Flask, render_template_string, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SCRAP3R Error Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            background: #0a0a0a;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #4CAF50;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }
        .status {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status.healthy {
            border-color: #4CAF50;
        }
        .status.error {
            border-color: #f44336;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        .healthy .status-indicator {
            background: #4CAF50;
            box-shadow: 0 0 10px #4CAF50;
        }
        .error .status-indicator {
            background: #f44336;
            box-shadow: 0 0 10px #f44336;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            50% { opacity: 0.5; }
        }
        .error-list {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
        }
        .error-item {
            background: #0f0f0f;
            border: 1px solid #222;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .error-item.critical {
            border-color: #f44336;
            background: #1a0f0f;
        }
        .error-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .error-type {
            color: #ff9800;
            font-weight: bold;
        }
        .error-time {
            color: #666;
            font-size: 0.9em;
        }
        .error-message {
            color: #e0e0e0;
            margin-bottom: 10px;
            word-wrap: break-word;
        }
        .error-context {
            color: #888;
            font-size: 0.9em;
        }
        .error-traceback {
            background: #000;
            border: 1px solid #333;
            border-radius: 4px;
            padding: 10px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.85em;
            overflow-x: auto;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #45a049;
        }
        .refresh-info {
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .no-errors {
            text-align: center;
            color: #666;
            padding: 40px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 SCRAP3R Error Monitor</h1>
        
        <div id="status" class="status">
            <span class="status-indicator"></span>
            <span id="status-text">Loading...</span>
        </div>
        
        <div class="stats" id="stats">
            <!-- Stats will be populated by JavaScript -->
        </div>
        
        <div style="margin-bottom: 20px;">
            <button onclick="refreshData()">Refresh</button>
            <button onclick="clearErrors()" style="background: #f44336; margin-left: 10px;">Clear Errors</button>
            <button onclick="downloadLogs()" style="background: #ff9800; margin-left: 10px;">Download Logs</button>
        </div>
        
        <div class="error-list">
            <h2>Recent Errors</h2>
            <div id="errors">Loading...</div>
        </div>
        
        <div class="refresh-info">
            Auto-refresh every 30 seconds. Last update: <span id="last-update">Never</span>
        </div>
    </div>

    <script>
        let autoRefresh;
        
        async function fetchData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Failed to fetch data:', error);
            }
        }
        
        function updateDashboard(data) {
            // Update status
            const statusEl = document.getElementById('status');
            const statusTextEl = document.getElementById('status-text');
            
            if (data.status.healthy) {
                statusEl.className = 'status healthy';
                statusTextEl.textContent = '✓ System is healthy';
            } else {
                statusEl.className = 'status error';
                statusTextEl.textContent = '⚠️ System has errors';
            }
            
            // Update stats
            const statsEl = document.getElementById('stats');
            const uptime = calculateUptime(data.status.start_time);
            statsEl.innerHTML = `
                <div class="stat-box">
                    <div class="stat-value">${data.status.error_count}</div>
                    <div class="stat-label">Total Errors</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${data.errors.filter(e => e.critical).length}</div>
                    <div class="stat-label">Critical Errors</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${uptime}</div>
                    <div class="stat-label">Uptime</div>
                </div>
            `;
            
            // Update errors
            const errorsEl = document.getElementById('errors');
            if (data.errors.length === 0) {
                errorsEl.innerHTML = '<div class="no-errors">🎉 No errors logged</div>';
            } else {
                errorsEl.innerHTML = data.errors.reverse().map(error => `
                    <div class="error-item ${error.critical ? 'critical' : ''}">
                        <div class="error-header">
                            <span class="error-type">${error.critical ? '🔴 CRITICAL' : '⚠️'} ${error.type}</span>
                            <span class="error-time">${formatTime(error.timestamp)}</span>
                        </div>
                        <div class="error-message">${escapeHtml(error.message)}</div>
                        ${error.context ? `<div class="error-context">📍 ${escapeHtml(error.context)}</div>` : ''}
                        ${error.traceback ? `<div class="error-traceback">${escapeHtml(error.traceback)}</div>` : ''}
                    </div>
                `).join('');
            }
            
            // Update last refresh time
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
        }
        
        function calculateUptime(startTime) {
            const start = new Date(startTime);
            const now = new Date();
            const diff = now - start;
            
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            
            if (hours > 24) {
                const days = Math.floor(hours / 24);
                return `${days}d ${hours % 24}h`;
            }
            return `${hours}h ${minutes}m`;
        }
        
        function formatTime(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleString();
        }
        
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
        
        function refreshData() {
            fetchData();
        }
        
        async function clearErrors() {
            if (confirm('Are you sure you want to clear all error logs?')) {
                try {
                    await fetch('/api/clear', { method: 'POST' });
                    fetchData();
                } catch (error) {
                    alert('Failed to clear errors');
                }
            }
        }
        
        function downloadLogs() {
            window.location.href = '/api/download';
        }
        
        // Initial load
        fetchData();
        
        // Auto-refresh every 30 seconds
        autoRefresh = setInterval(fetchData, 30000);
        
        // Stop auto-refresh when page is hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearInterval(autoRefresh);
            } else {
                fetchData();
                autoRefresh = setInterval(fetchData, 30000);
            }
        });
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Serve the dashboard HTML"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status')
def api_status():
    """Get current status and errors"""
    try:
        # Load error log
        log_file = "data/error_log.json"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                data = json.load(f)
                return jsonify({
                    'status': data.get('status', {'healthy': True}),
                    'errors': data.get('errors', [])
                })
        else:
            return jsonify({
                'status': {
                    'healthy': True,
                    'error_count': 0,
                    'start_time': datetime.now().isoformat()
                },
                'errors': []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear all errors"""
    try:
        log_file = "data/error_log.json"
        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                json.dump({
                    'status': {
                        'healthy': True,
                        'error_count': 0,
                        'start_time': datetime.now().isoformat()
                    },
                    'errors': []
                }, f)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download')
def api_download():
    """Download error logs"""
    try:
        log_file = "data/error_log.json"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Format as a text file for easy sharing
            data = json.loads(content)
            text_content = f"SCRAP3R Error Log\n"
            text_content += f"Generated: {datetime.now()}\n"
            text_content += f"Total Errors: {data['status']['error_count']}\n"
            text_content += "=" * 80 + "\n\n"
            
            for error in data.get('errors', []):
                text_content += f"Time: {error['timestamp']}\n"
                text_content += f"Type: {error['type']}\n"
                text_content += f"Critical: {error['critical']}\n"
                text_content += f"Message: {error['message']}\n"
                if error.get('context'):
                    text_content += f"Context: {error['context']}\n"
                if error.get('traceback'):
                    text_content += f"Traceback:\n{error['traceback']}\n"
                text_content += "-" * 80 + "\n\n"
            
            return text_content, 200, {
                'Content-Type': 'text/plain',
                'Content-Disposition': f'attachment; filename=scrap3r_errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            }
        else:
            return "No error logs found", 404
    except Exception as e:
        return str(e), 500


if __name__ == '__main__':
    # Use environment variable for port, default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)