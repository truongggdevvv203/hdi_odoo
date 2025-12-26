/** @odoo-module **/

// Attendance Kiosk JavaScript
// Kiosk form view logic

function initKioskClock() {
    function updateClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('vi-VN');
        const clockDisplay = document.getElementById('clock-display');
        if (clockDisplay) {
            clockDisplay.textContent = timeStr;
        }
    }
    updateClock();
    setInterval(updateClock, 1000);
}

async function loadKioskStatus() {
    try {
        const response = await fetch('/kiosk/api/status', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            updateKioskStatusUI(data);
            updateKioskWorkedHours();
            setTimeout(loadKioskStatus, 5000);
        }
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

function updateKioskStatusUI(status) {
    const nameEl = document.getElementById('employee-name-display');
    const msgEl = document.getElementById('status-message-display');
    const checkInBtn = document.getElementById('check-in-btn-kiosk');
    const checkOutBtn = document.getElementById('check-out-btn-kiosk');

    if (!nameEl || !msgEl || !checkInBtn || !checkOutBtn) return;

    nameEl.textContent = status.employee_name || 'Loading...';
    msgEl.textContent = status.message || '';

    const checkInDetail = document.getElementById('check-in-detail');
    const checkOutDetail = document.getElementById('check-out-detail');
    const workedHoursDetail = document.getElementById('worked-hours-detail');

    if (checkInDetail) checkInDetail.style.display = 'none';
    if (checkOutDetail) checkOutDetail.style.display = 'none';
    if (workedHoursDetail) workedHoursDetail.style.display = 'none';

    if (status.status === 'not_checked_in') {
        checkInBtn.disabled = false;
        checkOutBtn.disabled = true;
        checkInBtn.style.opacity = '1';
        checkOutBtn.style.opacity = '0.5';
    } else if (status.status === 'checked_in') {
        checkInBtn.disabled = true;
        checkOutBtn.disabled = false;
        checkInBtn.style.opacity = '0.5';
        checkOutBtn.style.opacity = '1';

        if (checkInDetail) {
            checkInDetail.style.display = 'block';
            const checkInTimeDisplay = document.getElementById('check-in-time-display');
            if (checkInTimeDisplay) {
                checkInTimeDisplay.textContent = new Date(status.check_in_time).toLocaleTimeString('vi-VN');
            }
        }
    } else if (status.status === 'checked_out') {
        checkInBtn.disabled = false;
        checkOutBtn.disabled = true;
        checkInBtn.style.opacity = '1';
        checkOutBtn.style.opacity = '0.5';

        if (checkInDetail) checkInDetail.style.display = 'block';
        if (checkOutDetail) checkOutDetail.style.display = 'block';
        if (workedHoursDetail) workedHoursDetail.style.display = 'block';

        const checkInTimeDisplay = document.getElementById('check-in-time-display');
        const checkOutTimeDisplay = document.getElementById('check-out-time-display');
        const workedHoursDisplay = document.getElementById('worked-hours-display');

        if (checkInTimeDisplay) {
            checkInTimeDisplay.textContent = new Date(status.check_in_time).toLocaleTimeString('vi-VN');
        }
        if (checkOutTimeDisplay) {
            checkOutTimeDisplay.textContent = new Date(status.check_out_time).toLocaleTimeString('vi-VN');
        }
        if (workedHoursDisplay) {
            workedHoursDisplay.textContent = status.worked_hours + ' giờ';
        }
    }
}

async function updateKioskWorkedHours() {
    try {
        const response = await fetch('/kiosk/api/today-worked-hours', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            const todayHoursDisplay = document.getElementById('today-hours-display');
            if (todayHoursDisplay) {
                todayHoursDisplay.textContent = data.total_worked_hours.toFixed(1) + ' giờ';
            }
        }
    } catch (error) {
        console.error('Error updating hours:', error);
    }
}

async function performCheckIn() {
    try {
        const btn = document.getElementById('check-in-btn-kiosk');
        if (!btn) return;
        
        btn.disabled = true;

        const payload = {};
        if (navigator.geolocation) {
            await new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        payload.in_latitude = pos.coords.latitude;
                        payload.in_longitude = pos.coords.longitude;
                        resolve();
                    },
                    () => resolve()
                );
            });
        }

        const response = await fetch('/kiosk/api/check-in', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        showKioskMessage(data.message, data.success);

        if (data.success) {
            setTimeout(loadKioskStatus, 500);
        } else {
            btn.disabled = false;
        }
    } catch (error) {
        showKioskMessage('Lỗi: ' + error.message, false);
        const btn = document.getElementById('check-in-btn-kiosk');
        if (btn) btn.disabled = false;
    }
}

async function performCheckOut() {
    try {
        const btn = document.getElementById('check-out-btn-kiosk');
        if (!btn) return;
        
        btn.disabled = true;

        const payload = {};
        if (navigator.geolocation) {
            await new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        payload.out_latitude = pos.coords.latitude;
                        payload.out_longitude = pos.coords.longitude;
                        resolve();
                    },
                    () => resolve()
                );
            });
        }

        const response = await fetch('/kiosk/api/check-out', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        showKioskMessage(data.message, data.success);

        if (data.success) {
            setTimeout(loadKioskStatus, 500);
        } else {
            btn.disabled = false;
        }
    } catch (error) {
        showKioskMessage('Lỗi: ' + error.message, false);
        const btn = document.getElementById('check-out-btn-kiosk');
        if (btn) btn.disabled = false;
    }
}

function showKioskMessage(message, success) {
    const msgEl = document.getElementById('result-message-kiosk');
    if (!msgEl) return;
    
    msgEl.textContent = message;
    msgEl.style.background = success ? 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)' : 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)';
    msgEl.style.color = success ? '#1e5631' : '#d62828';
    msgEl.style.border = success ? '2px solid #52b788' : '2px solid #f77f00';
    msgEl.style.display = 'block';

    setTimeout(() => {
        msgEl.style.display = 'none';
    }, 3000);
}

// Auto-init when DOM loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('clock-display')) {
        initKioskClock();
        loadKioskStatus();
    }
});

// Make functions globally available for onclick handlers
window.performCheckIn = performCheckIn;
window.performCheckOut = performCheckOut;
