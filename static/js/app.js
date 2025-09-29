// Twitter Bot Dashboard JavaScript

// SECURITY: Secure CSRF Token setup for AJAX requests
// Fetch CSRF token from secure endpoint instead of meta tag
let csrfToken = null;

// Get CSRF token securely from server
async function fetchCSRFToken() {
    try {
        const response = await fetch('/csrf-token', {
            method: 'GET',
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            csrfToken = data.csrf_token;
            return csrfToken;
        } else {
            console.error('Failed to fetch CSRF token');
            return null;
        }
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        return null;
    }
}

// Initialize CSRF token on page load
document.addEventListener('DOMContentLoaded', async function() {
    await fetchCSRFToken();
});

// Setup CSRF token for all AJAX requests
$.ajaxSetup({
    beforeSend: async function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            // Ensure we have a valid CSRF token
            if (!csrfToken) {
                await fetchCSRFToken();
            }
            
            if (csrfToken) {
                xhr.setRequestHeader("X-CSRFToken", csrfToken);
            } else {
                console.error('No CSRF token available for request');
            }
        }
    }
});

// Global variables
let refreshInterval;
let countdownInterval;
let socket;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    initializeWebSocket();
});

function initializeApp() {
    console.log('Twitter Bot Dashboard initialized');
    
    // Start auto-refresh for dashboard
    if (window.location.pathname === '/') {
        startAutoRefresh();
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    // Add loading states to forms
    addFormLoadingStates();
    
    // Initialize real-time features
    initializeRealTimeUpdates();
}

// Auto-refresh functionality
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        if (document.visibilityState === 'visible') {
            updateDashboardStatus();
        }
    }, 5000); // Refresh every 5 seconds
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
}

// Update dashboard status
function updateDashboardStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateBotStatus(data.running);
            updateStats(data.stats);
        })
        .catch(error => {
            console.error('Status update failed:', error);
        });
}

function updateBotStatus(isRunning) {
    const statusElement = document.querySelector('.bot-status');
    const controlButton = document.querySelector('.bot-control-btn');
    
    if (statusElement) {
        statusElement.innerHTML = isRunning 
            ? '<i class="fas fa-play"></i> Çalışıyor'
            : '<i class="fas fa-stop"></i> Durduruldu';
        statusElement.className = isRunning 
            ? 'badge bg-success fs-6 bot-status'
            : 'badge bg-danger fs-6 bot-status';
    }
    
    if (controlButton) {
        controlButton.innerHTML = isRunning
            ? '<i class="fas fa-stop"></i> Durdur'
            : '<i class="fas fa-play"></i> Başlat';
        controlButton.className = isRunning
            ? 'btn btn-danger bot-control-btn'
            : 'btn btn-success bot-control-btn';
        controlButton.onclick = () => controlBot(isRunning ? 'stop' : 'start');
    }
}

function updateStats(stats) {
    // Check if stats exists
    if (!stats) return;

    // Update various stats on the dashboard
    if (stats.daily_tweets !== undefined) {
        const dailyElement = document.querySelector('.daily-tweets');
        if (dailyElement) dailyElement.textContent = stats.daily_tweets;
    }

    if (stats.total_tweets !== undefined) {
        const totalElement = document.querySelector('.total-tweets');
        if (totalElement) totalElement.textContent = stats.total_tweets;
    }
}

// Bot control functions
function controlBot(action) {
    const button = event.target;
    const originalText = button.innerHTML;
    
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + 
        (action === 'start' ? 'Başlatılıyor...' : 'Durduruluyor...');
    button.disabled = true;
    
    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Hata: ' + data.message, 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        showNotification('Bağlantı hatası: ' + error.message, 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Notification system
function showNotification(message, type = 'info') {
    const toast = createToastElement(message, type);
    document.body.appendChild(toast);
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}

function createToastElement(message, type) {
    const toastId = 'toast-' + Date.now();
    const iconClass = {
        'success': 'fas fa-check-circle text-success',
        'error': 'fas fa-exclamation-circle text-danger',
        'warning': 'fas fa-exclamation-triangle text-warning',
        'info': 'fas fa-info-circle text-info'
    }[type] || 'fas fa-info-circle text-info';
    
    const toastHTML = `
        <div class="toast" id="${toastId}" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 1050;">
            <div class="toast-header">
                <i class="${iconClass} me-2"></i>
                <strong class="me-auto">Twitter Bot</strong>
                <small class="text-muted">şimdi</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = toastHTML;
    return tempDiv.firstElementChild;
}

// Form utilities
function addFormLoadingStates() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gönderiliyor...';
                submitButton.disabled = true;
                
                // Re-enable after 5 seconds if not handled elsewhere
                setTimeout(() => {
                    if (submitButton.disabled) {
                        submitButton.innerHTML = originalText;
                        submitButton.disabled = false;
                    }
                }, 5000);
            }
        });
    });
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// WebSocket initialization and real-time updates
function initializeWebSocket() {
    socket = io();
    
    // Connection events
    socket.on('connect', function() {
        console.log('WebSocket connected');
        // showNotification('Gerçek zamanlı bağlantı kuruldu', 'success'); // Disabled - too annoying
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
        // showNotification('Gerçek zamanlı bağlantı kesildi', 'warning'); // Disabled - too annoying
    });
    
    // Bot status updates
    socket.on('bot_status', function(data) {
        updateBotStatus(data.running);
        updateStats(data.stats);
    });
    
    // New tweet notifications
    socket.on('new_tweet', function(data) {
        showNotification(`Yeni tweet gönderildi: ${data.tweet.substring(0, 50)}...`, 
                        data.status ? 'success' : 'error');
        
        // Update stats if on dashboard
        if (window.location.pathname === '/') {
            setTimeout(updateDashboardStatus, 1000);
        }
    });
    
    // Console log updates for monitoring page
    socket.on('console_log', function(data) {
        if (window.location.pathname === '/monitoring') {
            addConsoleLogRealTime(data.type, data.message, data.timestamp);
        }
    });
    
    // Request initial status
    socket.emit('request_status');
}

function initializeRealTimeUpdates() {
    console.log('Real-time updates initialized via WebSocket');
    
    // Send periodic status requests
    setInterval(() => {
        if (socket && socket.connected) {
            socket.emit('request_status');
        }
    }, 10000); // Every 10 seconds
}

// Tweet utilities
function validateTweet(text) {
    if (!text || text.trim().length === 0) {
        return { valid: false, message: 'Tweet içeriği boş olamaz' };
    }
    
    if (text.length > 280) {
        return { valid: false, message: 'Tweet 280 karakteri geçemez' };
    }
    
    return { valid: true, message: 'Tweet geçerli' };
}

function formatTweetText(text) {
    // Add basic formatting for URLs, mentions, hashtags
    return text
        .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-primary">$1</a>')
        .replace(/@(\w+)/g, '<span class="text-info">@$1</span>')
        .replace(/#(\w+)/g, '<span class="text-success">#$1</span>');
}

// Configuration utilities
function serializeFormData(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        if (data[key]) {
            // Handle multiple values (like checkboxes)
            if (Array.isArray(data[key])) {
                data[key].push(value);
            } else {
                data[key] = [data[key], value];
            }
        } else {
            data[key] = value;
        }
    }
    
    return data;
}

// API utilities
function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    return fetch(endpoint, { ...defaultOptions, ...options })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + R: Refresh dashboard
    if ((e.ctrlKey || e.metaKey) && e.key === 'r' && window.location.pathname === '/') {
        e.preventDefault();
        updateDashboardStatus();
        showNotification('Dashboard yenilendi', 'info');
    }
    
    // Ctrl/Cmd + T: Go to manual tweet
    if ((e.ctrlKey || e.metaKey) && e.key === 't') {
        e.preventDefault();
        window.location.href = '/manual';
    }
});

// Page visibility handling
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // Resume updates when page becomes visible
        if (window.location.pathname === '/') {
            updateDashboardStatus();
        }
    }
});

// Error handling for uncaught errors
window.addEventListener('error', function(e) {
    console.error('Uncaught error:', e.error);
    showNotification('Beklenmeyen bir hata oluştu', 'error');
});

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'az önce';
    if (diffInSeconds < 3600) return Math.floor(diffInSeconds / 60) + ' dakika önce';
    if (diffInSeconds < 86400) return Math.floor(diffInSeconds / 3600) + ' saat önce';
    return Math.floor(diffInSeconds / 86400) + ' gün önce';
}

// Real-time console log for monitoring page
function addConsoleLogRealTime(type, message, timestamp) {
    const consoleOutput = document.getElementById('console-output');
    if (!consoleOutput) return;
    
    const typeColors = {
        'INFO': 'text-info',
        'WARN': 'text-warning', 
        'ERROR': 'text-danger',
        'SUCCESS': 'text-success'
    };
    
    const newLine = document.createElement('div');
    newLine.className = 'console-line';
    newLine.innerHTML = `
        <span class="text-success">[${timestamp}]</span> 
        <span class="${typeColors[type]}">[${type}]</span> 
        ${message}
    `;
    
    consoleOutput.appendChild(newLine);
    
    // Auto-scroll if enabled
    const autoScroll = document.getElementById('auto-scroll');
    if (autoScroll && autoScroll.checked) {
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }
    
    // Limit console lines to 100
    const lines = consoleOutput.querySelectorAll('.console-line');
    if (lines.length > 100) {
        lines[0].remove();
    }
}

// Export functions for global access
window.TwitterBotDashboard = {
    controlBot,
    showNotification,
    updateDashboardStatus,
    validateTweet,
    formatTweetText,
    apiCall,
    addConsoleLogRealTime
};