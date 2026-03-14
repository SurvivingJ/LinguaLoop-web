/**
 * StatsDashboard - Fetches and renders the stats dashboard screen.
 */
class StatsDashboard {
    constructor() {
        this.loaded = false;
    }

    /**
     * Load and render stats when the stats screen is shown.
     */
    async load() {
        if (!profileManager.isTracking()) return;

        const loading = document.getElementById('stats-loading');
        const content = document.getElementById('stats-content');
        loading.style.display = 'block';
        content.style.display = 'none';

        try {
            const response = await fetch(`/api/profile/${profileManager.activeProfile}/stats`);
            if (!response.ok) throw new Error('Failed to load stats');
            const stats = await response.json();

            this.renderOverall(stats.overall);
            this.renderOpBars(stats.operation_accuracy);
            this.renderTagList('stats-weakest', stats.weakest_tags, 'weak');
            this.renderTagList('stats-strongest', stats.strongest_tags, 'strong');
            await this.renderFocus();
            this.renderSessions(stats.recent_sessions);

            loading.style.display = 'none';
            content.style.display = 'block';
            this.loaded = true;
        } catch (e) {
            console.error('Failed to load stats:', e);
            loading.textContent = 'FAILED TO LOAD STATS';
        }
    }

    renderOverall(overall) {
        const el = document.getElementById('stats-overall');
        if (!overall || overall.total_problems === 0) {
            el.innerHTML = '<div class="stats-empty">NO DATA YET — PLAY SOME GAMES!</div>';
            return;
        }
        const acc = overall.total_problems > 0
            ? Math.round(overall.total_correct / overall.total_problems * 100)
            : 0;
        const avgTime = overall.avg_time_ms > 0
            ? (overall.avg_time_ms / 1000).toFixed(1)
            : '—';

        el.innerHTML = `
            <div class="stats-overall-grid">
                <div class="stats-overall-item">
                    <div class="stats-overall-value">${overall.total_problems}</div>
                    <div class="stats-overall-label">PROBLEMS</div>
                </div>
                <div class="stats-overall-item">
                    <div class="stats-overall-value">${acc}%</div>
                    <div class="stats-overall-label">ACCURACY</div>
                </div>
                <div class="stats-overall-item">
                    <div class="stats-overall-value">${avgTime}s</div>
                    <div class="stats-overall-label">AVG TIME</div>
                </div>
            </div>
        `;
    }

    renderOpBars(opAccuracy) {
        const el = document.getElementById('stats-op-bars');
        const ops = [
            { key: 'op:add', label: 'ADD', symbol: '+' },
            { key: 'op:sub', label: 'SUB', symbol: '−' },
            { key: 'op:mul', label: 'MUL', symbol: '×' },
            { key: 'op:div', label: 'DIV', symbol: '÷' }
        ];

        let html = '';
        for (const op of ops) {
            const data = opAccuracy[op.key];
            if (!data) {
                html += `
                    <div class="stats-bar-row">
                        <div class="stats-bar-label">${op.symbol} ${op.label}</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill" style="width:0%"></div></div>
                        <div class="stats-bar-value">—</div>
                    </div>`;
                continue;
            }
            const color = data.pct >= 80 ? 'var(--accent)' : data.pct >= 60 ? '#f0c030' : '#ff4444';
            html += `
                <div class="stats-bar-row">
                    <div class="stats-bar-label">${op.symbol} ${op.label}</div>
                    <div class="stats-bar-track">
                        <div class="stats-bar-fill" style="width:${data.pct}%; background:${color}"></div>
                    </div>
                    <div class="stats-bar-value">${data.pct}% <span class="stats-bar-count">(${data.attempts})</span></div>
                </div>`;
        }
        el.innerHTML = html;
    }

    renderTagList(containerId, tags, type) {
        const el = document.getElementById(containerId);
        if (!tags || tags.length === 0) {
            el.innerHTML = '<div class="stats-empty">NOT ENOUGH DATA YET</div>';
            return;
        }

        let html = '';
        const maxToShow = 7;
        for (const tag of tags.slice(0, maxToShow)) {
            const color = type === 'weak'
                ? (tag.accuracy < 50 ? '#ff4444' : '#f0c030')
                : (tag.accuracy >= 90 ? 'var(--accent)' : '#88ff88');
            const timeStr = tag.avg_time_ms > 0 ? `${(tag.avg_time_ms / 1000).toFixed(1)}s` : '';
            html += `
                <div class="stats-tag-row">
                    <div class="stats-tag-name">${this.formatTag(tag.tag)}</div>
                    <div class="stats-tag-acc" style="color:${color}">${tag.accuracy}%</div>
                    <div class="stats-tag-meta">${tag.attempts} tries${timeStr ? ' · ' + timeStr : ''}</div>
                </div>`;
        }
        el.innerHTML = html;
    }

    async renderFocus() {
        const el = document.getElementById('stats-focus');
        const focusTags = await profileManager.getFocusTags();
        if (!focusTags || focusTags.length === 0) {
            el.innerHTML = '<div class="stats-empty">PLAY MORE TO GET RECOMMENDATIONS</div>';
            return;
        }
        const tagLabels = focusTags.map(t => `<span class="stats-focus-tag">${this.formatTag(t)}</span>`);
        el.innerHTML = `<div class="stats-focus-list">${tagLabels.join('')}</div>`;
    }

    renderSessions(sessions) {
        const el = document.getElementById('stats-sessions');
        if (!sessions || sessions.length === 0) {
            el.innerHTML = '<div class="stats-empty">NO SESSIONS RECORDED YET</div>';
            return;
        }

        let html = '<div class="stats-session-table">';
        // Show newest first
        for (const s of [...sessions].reverse()) {
            const date = new Date(s.date);
            const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
            const acc = s.problems_attempted > 0
                ? Math.round(s.correct / s.problems_attempted * 100)
                : 0;
            const durStr = s.duration_s >= 60
                ? `${Math.floor(s.duration_s / 60)}m${s.duration_s % 60}s`
                : `${s.duration_s}s`;
            const mode = (s.mode || 'unknown').replace(/_/g, ' ').toUpperCase();

            html += `
                <div class="stats-session-row">
                    <div class="stats-session-date">${dateStr}</div>
                    <div class="stats-session-mode">${mode}</div>
                    <div class="stats-session-acc">${acc}%</div>
                    <div class="stats-session-meta">${s.problems_attempted} Qs · ${durStr}</div>
                </div>`;
        }
        html += '</div>';
        el.innerHTML = html;
    }

    formatTag(tag) {
        return tag.replace(/:/g, ': ').replace(/_/g, ' ').toUpperCase();
    }
}

const statsDashboard = new StatsDashboard();
