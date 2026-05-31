/**
 * CouponAI - Main Application JavaScript
 * Vanilla JS with modern patterns
 */

const API_BASE = '/api/v1';

// --- Auth State ---
const Auth = {
    getToken() {
        return localStorage.getItem('access_token');
    },
    getUser() {
        const u = localStorage.getItem('user');
        return u ? JSON.parse(u) : null;
    },
    setAuth(data) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user', JSON.stringify(data.user));
    },
    clear() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },
    isLoggedIn() {
        return !!this.getToken();
    },
    isAdmin() {
        const u = this.getUser();
        return u && (u.role === 'super_admin' || u.role === 'admin');
    }
};

// --- API Client ---
const api = {
    async request(method, path, body = null, requireAuth = true) {
        const headers = { 'Content-Type': 'application/json' };
        if (requireAuth && Auth.getToken()) {
            headers['Authorization'] = `Bearer ${Auth.getToken()}`;
        }
        const opts = { method, headers };
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(`${API_BASE}${path}`, opts);
        if (res.status === 401 && requireAuth) {
            // Try refresh
            const refreshed = await this.refreshToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${Auth.getToken()}`;
                const retry = await fetch(`${API_BASE}${path}`, { ...opts, headers });
                return retry.json();
            }
            Auth.clear();
            window.location.href = '/login';
            return null;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Request failed');
        }
        return res.json();
    },

    async refreshToken() {
        const rt = localStorage.getItem('refresh_token');
        if (!rt) return false;
        try {
            const res = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: rt }),
            });
            if (res.ok) {
                const data = await res.json();
                Auth.setAuth(data);
                return true;
            }
        } catch (e) {}
        return false;
    },

    get(path, auth = true) { return this.request('GET', path, null, auth); },
    post(path, body, auth = true) { return this.request('POST', path, body, auth); },
    put(path, body, auth = true) { return this.request('PUT', path, body, auth); },
    del(path, auth = true) { return this.request('DELETE', path, null, auth); },
};

// --- Toast Notifications ---
const Toast = {
    container: null,
    init() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    },
    show(message, type = 'info', duration = 4000) {
        if (!this.container) this.init();
        const colors = {
            success: 'border-left: 4px solid var(--success)',
            error: 'border-left: 4px solid var(--error)',
            warning: 'border-left: 4px solid var(--warning)',
            info: 'border-left: 4px solid var(--info)',
        };
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = colors[type] || colors.info;
        toast.textContent = message;
        this.container.appendChild(toast);
        setTimeout(() => toast.remove(), duration);
    },
    success(msg) { this.show(msg, 'success'); },
    error(msg) { this.show(msg, 'error'); },
    warning(msg) { this.show(msg, 'warning'); },
    info(msg) { this.show(msg, 'info'); },
};



// --- Search Module ---
const Search = {
    async execute(query, options = {}) {
        try {
            const result = await api.post('/search', {
                query,
                merchant: options.merchant || null,
                coupon_type: options.coupon_type || null,
                sort_by: options.sort_by || null,
                limit: options.limit || 20,
                offset: options.offset || 0,
            });
            return result;
        } catch (err) {
            Toast.error(err.message);
            return null;
        }
    },

    async quickSearch(query) {
        try {
            const res = await fetch(`${API_BASE}/search/quick?q=${encodeURIComponent(query)}&limit=5`);
            return await res.json();
        } catch (e) {
            return { hits: [] };
        }
    },

    renderResults(results, container) {
        if (!results || !results.results || results.results.length === 0) {
            container.innerHTML = `
                <div style="text-align:center;padding:60px 20px;color:var(--text-muted);">
                    <svg width="64" height="64" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin-bottom:16px;opacity:0.5">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                    <p style="font-size:16px;">No coupons found</p>
                    <p style="font-size:13px;margin-top:8px;">Try a different search query</p>
                </div>`;
            return;
        }

        const meta = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:0 4px;">
                <div>
                    <span style="color:var(--text-secondary);font-size:13px;">
                        ${results.total_hits} results in ${results.response_time_ms}ms
                    </span>
                    ${results.corrected_query ? `<span style="color:var(--accent);font-size:13px;margin-left:12px;">Showing results for: "${results.corrected_query}"</span>` : ''}
                    ${results.merchant_detected ? `<span class="badge badge-info" style="margin-left:8px;">${results.merchant_detected}</span>` : ''}
                </div>
            </div>`;

        const cards = results.results.map(c => this.renderCouponCard(c)).join('');
        container.innerHTML = meta + `<div class="grid grid-2">${cards}</div>`;
    },

    renderCouponCard(coupon) {
        const confidence = Math.round((coupon.final_confidence || 0.5) * 100);
        const confidenceClass = confidence >= 70 ? 'success' : confidence >= 40 ? 'warning' : 'error';
        return `
        <div class="coupon-card" data-id="${coupon.id}">
            <div style="display:flex;justify-content:space-between;align-items:start;">
                <span class="merchant">${coupon.merchant_name || 'Unknown'}</span>
                <span class="badge badge-${confidenceClass}">${confidence}% match</span>
            </div>
            <div class="title">${coupon.title || ''}</div>
            ${coupon.description ? `<p style="color:var(--text-secondary);font-size:13px;margin:4px 0;">${coupon.description.substring(0, 100)}</p>` : ''}
            ${coupon.code ? `
            <div class="code-box">
                <span class="code">${coupon.code}</span>
                <button class="copy-btn" onclick="Search.copyCode('${coupon.code}')">Copy</button>
            </div>` : `
            <div style="margin:12px 0;"><a href="${coupon.url || '#'}" target="_blank" class="btn btn-primary" style="font-size:12px;padding:8px 16px;">Get Deal</a></div>`}
            <div class="meta">
                ${coupon.discount_value ? `<span>💰 ${coupon.discount_value}${coupon.discount_unit === 'percent' ? '%' : '$'} off</span>` : ''}
                ${coupon.expires_at ? `<span>⏰ Expires: ${new Date(coupon.expires_at).toLocaleDateString()}</span>` : ''}
                ${coupon.is_verified ? '<span>✓ Verified</span>' : ''}
            </div>
        </div>`;
    },

    copyCode(code) {
        navigator.clipboard.writeText(code).then(() => {
            Toast.success(`Code "${code}" copied!`);
        }).catch(() => {
            Toast.error('Failed to copy');
        });
    }
};

// --- Command Palette (Ctrl+K) ---
const CommandPalette = {
    isOpen: false,
    init() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.toggle();
            }
            if (e.key === 'Escape' && this.isOpen) this.close();
        });
    },
    toggle() { this.isOpen ? this.close() : this.open(); },
    open() {
        if (document.getElementById('cmd-palette')) return;
        const el = document.createElement('div');
        el.id = 'cmd-palette';
        el.innerHTML = `
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9998;backdrop-filter:blur(4px);" onclick="CommandPalette.close()"></div>
            <div style="position:fixed;top:20%;left:50%;transform:translateX(-50%);width:560px;max-width:90vw;z-index:9999;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;box-shadow:var(--shadow-lg);">
                <input type="text" placeholder="Search coupons, merchants..." style="width:100%;padding:18px 20px;background:transparent;border:none;border-bottom:1px solid var(--border);color:var(--text-primary);font-size:16px;outline:none;" autofocus id="cmd-input" oninput="CommandPalette.onInput(this.value)">
                <div id="cmd-results" style="max-height:300px;overflow-y:auto;padding:8px;"></div>
            </div>`;
        document.body.appendChild(el);
        this.isOpen = true;
        document.getElementById('cmd-input').focus();
    },
    close() {
        const el = document.getElementById('cmd-palette');
        if (el) el.remove();
        this.isOpen = false;
    },
    async onInput(value) {
        if (value.length < 2) return;
        const container = document.getElementById('cmd-results');
        const data = await Search.quickSearch(value);
        if (data.hits && data.hits.length > 0) {
            container.innerHTML = data.hits.map(h => `
                <div style="padding:10px 14px;border-radius:8px;cursor:pointer;transition:all 0.15s;" onmouseenter="this.style.background='var(--bg-tertiary)'" onmouseleave="this.style.background='transparent'">
                    <div style="font-size:14px;font-weight:500;">${h.title || ''}</div>
                    <div style="font-size:12px;color:var(--text-muted);">${h.merchant_name || ''} ${h.code ? '• ' + h.code : ''}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">No results</p>';
        }
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    Toast.init();
    CommandPalette.init();
});
