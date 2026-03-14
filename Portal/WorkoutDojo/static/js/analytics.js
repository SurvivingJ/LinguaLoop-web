// static/js/analytics.js — WorkoutOS Analytics Charts (S25)
// Requires: Chart.js loaded from CDN before this file.
// Expects global: ANALYTICS_DATA = { bodyWeightHistory, rollingAvg, recentSessions }

document.addEventListener('DOMContentLoaded', () => {

    // ---------------------------------------------------------------------------
    // Body weight chart
    // ---------------------------------------------------------------------------

    const bwCtx = document.getElementById('bodyWeightChart');
    if (bwCtx && ANALYTICS_DATA.bodyWeightHistory && ANALYTICS_DATA.bodyWeightHistory.length) {
        new Chart(bwCtx, {
            type: 'line',
            data: {
                labels: ANALYTICS_DATA.bodyWeightHistory.map(d => d.date),
                datasets: [
                    {
                        label: 'Body Weight (kg)',
                        data: ANALYTICS_DATA.bodyWeightHistory.map(d => d.weight_kg),
                        borderColor: '#6c63ff',
                        backgroundColor: 'rgba(108, 99, 255, 0.1)',
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#6c63ff',
                        fill: true,
                    },
                    {
                        label: '7-Day Average',
                        data: (ANALYTICS_DATA.rollingAvg || []).map(d => ({ x: d.date, y: d.avg_weight })),
                        borderColor: '#48c774',
                        borderDash: [5, 5],
                        tension: 0.3,
                        pointRadius: 0,
                        backgroundColor: 'transparent',
                        fill: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: {
                        labels: { color: '#ffffff', font: { size: 12 } },
                    },
                    tooltip: {
                        backgroundColor: '#22222e',
                        titleColor: '#ffffff',
                        bodyColor: '#a0a0b8',
                        borderColor: '#2e2e3e',
                        borderWidth: 1,
                        callbacks: {
                            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y} kg`,
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: { color: '#a0a0b8', maxTicksLimit: 8, font: { size: 11 } },
                        grid:  { color: '#2e2e3e' },
                    },
                    y: {
                        ticks: {
                            color: '#a0a0b8',
                            font: { size: 11 },
                            callback: (v) => `${v} kg`,
                        },
                        grid: { color: '#2e2e3e' },
                    },
                },
            },
        });
    }

    // ---------------------------------------------------------------------------
    // Exercise strength history chart (estimated 1RM — loaded on demand)
    // ---------------------------------------------------------------------------

    const exerciseSelect = document.getElementById('exercise-select');
    const exerciseCtx    = document.getElementById('exerciseChart');
    let exerciseChart    = null;

    if (exerciseSelect) {
        // Populate exercise dropdown via /api/exercises
        fetch('/api/exercises')
            .then(r => r.json())
            .then(exercises => {
                // Sort alphabetically
                exercises.sort((a, b) => a.name.localeCompare(b.name));
                exercises.forEach(ex => {
                    const opt = document.createElement('option');
                    opt.value       = ex.id;
                    opt.textContent = ex.name;
                    exerciseSelect.appendChild(opt);
                });
            })
            .catch(err => console.warn('Failed to load exercises for analytics:', err));

        exerciseSelect.addEventListener('change', async () => {
            const id = exerciseSelect.value;
            if (!id) return;

            // Show loading state
            const chartWrap = exerciseCtx?.closest('.card, .chart-wrap');
            if (chartWrap) chartWrap.style.opacity = '0.5';

            try {
                const sets = await fetch(`/api/exercises/${id}/history`).then(r => r.json());

                // Group by session, compute estimated 1RM per session (Epley: 1RM = w * (1 + reps/30))
                const sessions = {};
                sets
                    .filter(s => !s.is_warmup && s.weight_kg > 0)
                    .forEach(s => {
                        const est1rm = s.weight_kg * (1 + s.reps / 30);
                        const date   = (s.timestamp || '').split('T')[0];
                        if (!sessions[s.session_id] || est1rm > sessions[s.session_id].est1rm) {
                            sessions[s.session_id] = { date, est1rm };
                        }
                    });

                const sorted = Object.values(sessions)
                    .filter(s => s.date)
                    .sort((a, b) => a.date.localeCompare(b.date));

                if (exerciseChart) {
                    exerciseChart.destroy();
                    exerciseChart = null;
                }

                if (!sorted.length) {
                    showNoDataMessage(exerciseCtx, 'No working sets logged for this exercise yet.');
                    return;
                }

                exerciseChart = new Chart(exerciseCtx, {
                    type: 'line',
                    data: {
                        labels: sorted.map(s => s.date),
                        datasets: [
                            {
                                label: 'Estimated 1RM (kg)',
                                data:  sorted.map(s => Math.round(s.est1rm * 10) / 10),
                                borderColor: '#ffb700',
                                backgroundColor: 'rgba(255, 183, 0, 0.1)',
                                tension: 0.3,
                                pointRadius: 5,
                                pointBackgroundColor: '#ffb700',
                                fill: true,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        interaction: {
                            intersect: false,
                            mode: 'index',
                        },
                        plugins: {
                            legend: {
                                labels: { color: '#ffffff', font: { size: 12 } },
                            },
                            tooltip: {
                                backgroundColor: '#22222e',
                                titleColor: '#ffffff',
                                bodyColor: '#a0a0b8',
                                borderColor: '#2e2e3e',
                                borderWidth: 1,
                                callbacks: {
                                    label: (ctx) => ` Estimated 1RM: ${ctx.parsed.y} kg`,
                                },
                            },
                        },
                        scales: {
                            x: {
                                ticks: { color: '#a0a0b8', maxTicksLimit: 8, font: { size: 11 } },
                                grid:  { color: '#2e2e3e' },
                            },
                            y: {
                                ticks: {
                                    color: '#a0a0b8',
                                    font: { size: 11 },
                                    callback: (v) => `${v} kg`,
                                },
                                grid: { color: '#2e2e3e' },
                                beginAtZero: false,
                            },
                        },
                    },
                });

            } catch (err) {
                console.error('Failed to load exercise history:', err);
                showNoDataMessage(exerciseCtx, 'Could not load exercise history.');
            } finally {
                if (chartWrap) chartWrap.style.opacity = '';
            }
        });
    }

    // ---------------------------------------------------------------------------
    // Recent sessions table (if element exists)
    // ---------------------------------------------------------------------------

    const sessionsTable = document.getElementById('recent-sessions-table');
    if (sessionsTable && ANALYTICS_DATA.recentSessions?.length) {
        const tbody = sessionsTable.querySelector('tbody') || sessionsTable;
        ANALYTICS_DATA.recentSessions.forEach(session => {
            const row = document.createElement('tr');
            const date     = (session.started_at || '').split('T')[0];
            const planName = session.plan_name || '—';
            const sets     = session.total_sets || 0;
            const vol      = session.total_volume_kg ? `${Math.round(session.total_volume_kg)} kg` : '—';
            const dur      = session.duration_seconds ? formatDuration(session.duration_seconds) : '—';

            row.innerHTML = `
                <td style="padding:10px 8px;font-size:13px;color:var(--text-secondary)">${escHtml(date)}</td>
                <td style="padding:10px 8px;font-size:13px;font-weight:600">${escHtml(planName)}</td>
                <td style="padding:10px 8px;font-size:13px;text-align:right">${sets}</td>
                <td style="padding:10px 8px;font-size:13px;text-align:right">${vol}</td>
                <td style="padding:10px 8px;font-size:13px;text-align:right;color:var(--text-secondary)">${dur}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // ---------------------------------------------------------------------------
    // Volume over time chart (if element exists)
    // ---------------------------------------------------------------------------

    const volumeCtx = document.getElementById('volumeChart');
    if (volumeCtx && ANALYTICS_DATA.recentSessions?.length) {
        const sessions = [...ANALYTICS_DATA.recentSessions]
            .filter(s => s.total_volume_kg)
            .sort((a, b) => (a.started_at || '').localeCompare(b.started_at || ''));

        if (sessions.length > 1) {
            new Chart(volumeCtx, {
                type: 'bar',
                data: {
                    labels: sessions.map(s => (s.started_at || '').split('T')[0]),
                    datasets: [
                        {
                            label: 'Session Volume (kg)',
                            data:  sessions.map(s => Math.round(s.total_volume_kg || 0)),
                            backgroundColor: 'rgba(108, 99, 255, 0.6)',
                            borderColor: '#6c63ff',
                            borderWidth: 1,
                            borderRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            labels: { color: '#ffffff', font: { size: 12 } },
                        },
                        tooltip: {
                            backgroundColor: '#22222e',
                            titleColor: '#ffffff',
                            bodyColor: '#a0a0b8',
                            borderColor: '#2e2e3e',
                            borderWidth: 1,
                            callbacks: {
                                label: (ctx) => ` Volume: ${ctx.parsed.y} kg`,
                            },
                        },
                    },
                    scales: {
                        x: {
                            ticks: { color: '#a0a0b8', maxTicksLimit: 10, font: { size: 11 } },
                            grid:  { color: '#2e2e3e' },
                        },
                        y: {
                            ticks: {
                                color: '#a0a0b8',
                                font: { size: 11 },
                                callback: (v) => `${v} kg`,
                            },
                            grid: { color: '#2e2e3e' },
                            beginAtZero: true,
                        },
                    },
                },
            });
        }
    }

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    function showNoDataMessage(canvas, message) {
        if (!canvas) return;
        const wrap = canvas.closest('.card, .chart-wrap') || canvas.parentElement;
        if (!wrap) return;
        let msg = wrap.querySelector('.no-data-msg');
        if (!msg) {
            msg = document.createElement('p');
            msg.className = 'no-data-msg';
            msg.style.cssText = 'text-align:center;color:var(--text-secondary);font-size:13px;padding:20px;';
            wrap.appendChild(msg);
        }
        msg.textContent = message;
        canvas.style.display = 'none';
    }

    function formatDuration(seconds) {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function escHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
});
