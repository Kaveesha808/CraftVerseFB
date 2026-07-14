// CraftReel AI Agent Frontend Application

let currentSelectedReelId = null;
let pollingInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initHlsPlayer();
    fetchStatus();
    fetchReelsQueue();
    bindEventListeners();

    // Poll status every 2 seconds for real-time agent & pipeline updates
    pollingInterval = setInterval(fetchStatus, 2000);
});

function initHlsPlayer() {
    const video = document.getElementById('hlsPlayer');
    const streamUrl = 'https://soul-5mincrafteng-rakuten.amagi.tv/playlist.m3u8';

    if (Hls.isSupported()) {
        const hls = new Hls();
        hls.loadSource(streamUrl);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
            video.play().catch(() => {
                logMessage('info', '[Stream] Click to unmute/play live stream preview.');
            });
        });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = streamUrl;
        video.addEventListener('loadedmetadata', () => {
            video.play();
        });
    }
}

function logMessage(type, message) {
    const terminal = document.getElementById('terminalLog');
    if (!terminal) return;
    const div = document.createElement('div');
    div.className = `log-line ${type}`;
    div.textContent = message;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

function bindEventListeners() {
    document.getElementById('btnGenerateNow').addEventListener('click', async () => {
        logMessage('info', '[Trigger] Initiating Reel Capture & AI Edit Pipeline...');
        try {
            const res = await fetch('/api/reels/generate-now', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'started') {
                logMessage('success', `[Pipeline] Job #${data.job_id} started! Capturing HLS stream...`);
                fetchStatus();
            } else {
                logMessage('error', `[Pipeline] ${data.message}`);
            }
        } catch (e) {
            logMessage('error', `[Error] Failed to start pipeline: ${e.message}`);
        }
    });

    document.getElementById('btnToggleAgent').addEventListener('click', async () => {
        try {
            const res = await fetch('/api/agent/toggle', { method: 'POST' });
            const data = await res.json();
            logMessage('system', `[Agent] ${data.message}`);
            fetchStatus();
        } catch (e) {
            logMessage('error', `[Agent] Toggle failed: ${e.message}`);
        }
    });

    document.getElementById('btnApplyHeader').addEventListener('click', async () => {
        const headerText = document.getElementById('headerText').value;
        const duration = document.getElementById('clipDuration').value;
        const resSettings = await fetch('/api/settings');
        const settings = await resSettings.json();
        settings.header_text = headerText;
        settings.clip_duration = duration;

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        logMessage('success', '[Config] Header banner text and clip duration updated!');
    });

    // Settings Modal
    const modal = document.getElementById('settingsModal');
    document.getElementById('btnOpenSettings').addEventListener('click', async () => {
        const res = await fetch('/api/settings');
        const s = await res.json();
        document.getElementById('setStreamUrl').value = s.stream_url || '';
        document.getElementById('setPageId').value = s.fb_page_id || '';
        document.getElementById('setAccessToken').value = s.fb_access_token || '';
        document.getElementById('setGeminiKey').value = s.gemini_api_key || '';
        document.getElementById('setGroqKey').value = s.groq_api_key || '';
        document.getElementById('setAutoUpload').value = s.auto_upload || 'false';
        document.getElementById('setDailyTarget').value = s.daily_target_videos || '3';
        document.getElementById('setAgentInterval').value = s.agent_schedule_interval_minutes || '60';
        modal.classList.add('open');
    });

    document.getElementById('btnCloseSettings').addEventListener('click', () => {
        modal.classList.remove('open');
    });

    document.getElementById('btnTestFb').addEventListener('click', async () => {
        const pageId = document.getElementById('setPageId').value;
        const token = document.getElementById('setAccessToken').value;
        const resultBox = document.getElementById('testFbResult');
        resultBox.textContent = 'Verifying with Facebook Graph API...';
        
        try {
            const res = await fetch('/api/settings/test-fb', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fb_page_id: pageId, fb_access_token: token })
            });
            const data = await res.json();
            if (data.valid) {
                resultBox.style.color = '#10b981';
                resultBox.textContent = `✅ Connected to Page: ${data.message}`;
            } else {
                resultBox.style.color = '#ef4444';
                resultBox.textContent = `❌ ${data.message}`;
            }
        } catch (e) {
            resultBox.style.color = '#ef4444';
            resultBox.textContent = `❌ Connection Error`;
        }
    });

    document.getElementById('btnSaveSettings').addEventListener('click', async () => {
        const payload = {
            stream_url: document.getElementById('setStreamUrl').value,
            clip_duration: document.getElementById('clipDuration').value,
            header_text: document.getElementById('headerText').value,
            auto_upload: document.getElementById('setAutoUpload').value,
            fb_page_id: document.getElementById('setPageId').value,
            fb_access_token: document.getElementById('setAccessToken').value,
            gemini_api_key: document.getElementById('setGeminiKey').value,
            groq_api_key: document.getElementById('setGroqKey').value,
            groq_model: 'llama-3.3-70b-versatile',
            daily_target_videos: document.getElementById('setDailyTarget').value,
            agent_schedule_interval_minutes: document.getElementById('setAgentInterval').value,
            agent_enabled: 'false'
        };

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        modal.classList.remove('open');
        logMessage('success', '[Settings] Saved successfully.');
    });

    // Studio Buttons
    document.getElementById('btnSaveCaption').addEventListener('click', async () => {
        if (!currentSelectedReelId) return;
        await fetch(`/api/reels/${currentSelectedReelId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                caption_en: document.getElementById('editCaptionEn').value,
                caption_si: '',
                hashtags: document.getElementById('editHashtags').value
            })
        });
        logMessage('success', '[Reel Studio] Caption & hashtags saved.');
        fetchReelsQueue();
    });

    document.getElementById('btnPublishFB').addEventListener('click', async () => {
        if (!currentSelectedReelId) return;
        logMessage('info', `[FB Upload] Publishing Reel #${currentSelectedReelId} to Facebook Page...`);
        try {
            const res = await fetch(`/api/reels/${currentSelectedReelId}/publish`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                logMessage('success', `[FB Upload] Published to Facebook! Video ID: ${data.fb_video_id}`);
                fetchReelsQueue();
            } else {
                logMessage('error', `[FB Upload] Failed: ${data.message}`);
            }
        } catch (e) {
            logMessage('error', `[FB Upload] Error: ${e.message}`);
        }
    });

    document.getElementById('btnDeleteReel').addEventListener('click', async () => {
        if (!currentSelectedReelId) return;
        await fetch(`/api/reels/${currentSelectedReelId}`, { method: 'DELETE' });
        logMessage('info', `[Reel Studio] Deleted Reel #${currentSelectedReelId}.`);
        currentSelectedReelId = null;
        document.getElementById('phonePlaceholder').style.display = 'flex';
        fetchReelsQueue();
    });

    document.getElementById('btnRefreshQueue').addEventListener('click', fetchReelsQueue);
}

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        // Agent Badge
        const badge = document.getElementById('agentBadge');
        const statusText = document.getElementById('agentStatusText');
        if (data.agent_enabled) {
            badge.classList.add('active');
            statusText.textContent = 'Agent: ACTIVE AUTO';
        } else {
            badge.classList.remove('active');
            statusText.textContent = 'Agent: STANDBY';
        }

        // Latest Job Progress
        const job = data.latest_job;
        if (job) {
            updatePipelineVisuals(job);
        }
    } catch (e) {}
}

function updatePipelineVisuals(job) {
    const badge = document.getElementById('jobStatusBadge');
    const nameSpan = document.getElementById('currentStepName');
    const percentSpan = document.getElementById('progressPercent');
    const fill = document.getElementById('progressFill');

    badge.textContent = job.status.toUpperCase();
    nameSpan.textContent = job.step_name || 'Idle';
    percentSpan.textContent = `${job.progress}%`;
    fill.style.width = `${job.progress}%`;

    // Step highlight logic
    const s1 = document.getElementById('step1');
    const s2 = document.getElementById('step2');
    const s3 = document.getElementById('step3');
    const s4 = document.getElementById('step4');

    [s1, s2, s3, s4].forEach(el => {
        el.classList.remove('active', 'completed');
    });

    if (job.progress > 0 && job.progress < 40) {
        s1.classList.add('active');
    } else if (job.progress >= 40 && job.progress < 70) {
        s1.classList.add('completed');
        s2.classList.add('active');
    } else if (job.progress >= 70 && job.progress < 90) {
        s1.classList.add('completed');
        s2.classList.add('completed');
        s3.classList.add('active');
    } else if (job.progress >= 90 && job.progress < 100) {
        s1.classList.add('completed');
        s2.classList.add('completed');
        s3.classList.add('completed');
        s4.classList.add('active');
    } else if (job.progress === 100) {
        [s1, s2, s3, s4].forEach(el => el.classList.add('completed'));
        // Refresh queue when complete
        fetchReelsQueue();
    }
}

async function fetchReelsQueue() {
    try {
        const res = await fetch('/api/reels');
        const reels = await res.json();
        const grid = document.getElementById('reelsGrid');
        grid.innerHTML = '';

        if (reels.length === 0) {
            grid.innerHTML = '<p style="color: var(--text-secondary); grid-column: 1/-1;">No Reels generated yet. Click "Capture & Create Reel Now" above!</p>';
            return;
        }

        reels.forEach(r => {
            const card = document.createElement('div');
            card.className = 'reel-card';
            
            const badgeClass = r.status === 'published' ? 'badge-published' : 'badge-ready';
            const thumbHtml = r.thumb_url
                ? `<img src="${r.thumb_url}" alt="Reel thumb">`
                : `<div style="width:100%;height:100%;background:#1e2538;display:flex;align-items:center;justify-content:center;color:#94a3b8;">🎬</div>`;

            card.innerHTML = `
                <div class="reel-thumb-box">
                    ${thumbHtml}
                    <span class="reel-badge ${badgeClass}">${r.status}</span>
                </div>
                <div class="reel-content">
                    <div class="reel-title">${r.title || '9:16 Viral Craft Reel'}</div>
                    <div class="reel-caption-preview">${r.caption_si || r.caption_en || ''}</div>
                    <div class="reel-card-buttons">
                        <button class="btn btn-outline full-width" onclick="selectReelForStudio(${r.id})">
                            ▶ Preview in Studio
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {}
}

async function selectReelForStudio(reelId) {
    currentSelectedReelId = reelId;
    document.getElementById('currentReelId').textContent = `Reel #${reelId}`;
    
    try {
        const res = await fetch(`/api/reels/${reelId}`);
        const r = await res.json();

        const player = document.getElementById('reelVideoPlayer');
        const placeholder = document.getElementById('phonePlaceholder');

        if (r.video_url) {
            player.src = r.video_url;
            player.style.display = 'block';
            placeholder.style.display = 'none';
            player.play().catch(() => {});
        }

        document.getElementById('editCaptionEn').value = r.caption_en || '';
        document.getElementById('editHashtags').value = r.hashtags || '';

        logMessage('info', `[Reel Studio] Loaded Reel #${reelId} into 9:16 mobile mockup player.`);
    } catch (e) {
        logMessage('error', `[Reel Studio] Failed to load Reel #${reelId}`);
    }
}
