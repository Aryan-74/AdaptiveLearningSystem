// Render interactive Chart.js visualizations for the Student Profile Dashboard
function renderStudentProfileCharts(data) {
    if (!data) return;

    // 1. VARK Modality Radar Chart
    const varkCtx = document.getElementById('varkRadarChart');
    if (varkCtx && data.psychological) {
        new Chart(varkCtx, {
            type: 'radar',
            data: {
                labels: ['Visual', 'Aural', 'Read/Write', 'Kinesthetic'],
                datasets: [{
                    label: 'VARK Score (0-1)',
                    data: [
                        data.psychological.vark_visual,
                        data.psychological.vark_aural,
                        data.psychological.vark_read_write,
                        data.psychological.vark_kinesthetic
                    ],
                    backgroundColor: 'rgba(79, 70, 229, 0.2)',
                    borderColor: '#4f46e5',
                    pointBackgroundColor: '#4f46e5',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#4f46e5',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: '#e2e8f0' },
                        grid: { color: '#e2e8f0' },
                        suggestedMin: 0,
                        suggestedMax: 1,
                        ticks: { stepSize: 0.2, backdropColor: 'transparent' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 2. Motivation & Self-Regulation Bar Chart
    const psychoCtx = document.getElementById('psychologicalBarChart');
    if (psychoCtx && data.psychological) {
        new Chart(psychoCtx, {
            type: 'bar',
            data: {
                labels: [
                    'Intrinsic Mot.', 'Extrinsic Mot.', 'Goal Orient.', 'Task Value',
                    'Goal Setting', 'Planning', 'Self-Monitor', 'Revision'
                ],
                datasets: [{
                    label: 'Normalized Score',
                    data: [
                        data.psychological.intrinsic_motivation,
                        data.psychological.extrinsic_motivation,
                        data.psychological.learning_goal_orientation,
                        data.psychological.task_value,
                        data.psychological.goal_setting,
                        data.psychological.planning,
                        data.psychological.self_monitoring,
                        data.psychological.revision_behavior
                    ],
                    backgroundColor: [
                        '#6366f1', '#6366f1', '#6366f1', '#6366f1',
                        '#0ea5e9', '#0ea5e9', '#0ea5e9', '#0ea5e9'
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 1,
                        ticks: { stepSize: 0.2 },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 3. Topic-wise Performance Chart
    const topicCtx = document.getElementById('topicPerformanceChart');
    if (topicCtx && data.knowledge && data.knowledge.topic_scores) {
        const topicLabels = Object.keys(data.knowledge.topic_scores).map(t => {
            return t.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        });
        const topicValues = Object.values(data.knowledge.topic_scores).map(v => Math.round(v * 100));

        new Chart(topicCtx, {
            type: 'bar',
            data: {
                labels: topicLabels,
                datasets: [{
                    label: 'Accuracy (%)',
                    data: topicValues,
                    backgroundColor: topicValues.map(v => v >= 70 ? '#10b981' : (v >= 40 ? '#f59e0b' : '#ef4444')),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { stepSize: 20, callback: v => v + '%' },
                        grid: { color: '#f1f5f9' }
                    },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 4. Knowledge Component (KC) Performance Chart
    const kcCtx = document.getElementById('kcPerformanceChart');
    if (kcCtx && data.knowledge && data.knowledge.kc_scores && data.kc_names) {
        const kcLabels = [];
        const kcValues = [];

        for (const [kcid, score] of Object.entries(data.knowledge.kc_scores)) {
            const name = data.kc_names[kcid] || kcid;
            kcLabels.push(name);
            kcValues.push(Math.round(score * 100));
        }

        new Chart(kcCtx, {
            type: 'bar',
            indexAxis: 'y',
            data: {
                labels: kcLabels,
                datasets: [{
                    label: 'KC Accuracy (%)',
                    data: kcValues,
                    backgroundColor: kcValues.map(v => v >= 70 ? '#10b981' : (v >= 40 ? '#f59e0b' : '#ef4444')),
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        min: 0,
                        max: 100,
                        ticks: { stepSize: 20, callback: v => v + '%' },
                        grid: { color: '#f1f5f9' }
                    },
                    y: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}
