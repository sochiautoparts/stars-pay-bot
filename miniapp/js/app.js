/**
 * StarsPay Mini App — Telegram Web App
 * Serves as payment interface for multiple projects
 */
(function() {
    'use strict';

    // Telegram Web App SDK
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#1a1a2e');
        tg.setBackgroundColor('#1a1a2e');
    }

    // Product catalog (mirrors bot config)
    const PRODUCTS = {
        "gitmoji-ai": {
            name: "GitMoji AI Pro",
            icon: "🤖",
            description: "Полная версия GitMoji AI с ИИ-подсказками и автокоммитами",
            plans: {
                month: { price: 149, label: "1 месяц", days: 30 },
                year: { price: 999, label: "1 год", days: 365 },
                lifetime: { price: 2999, label: "Навсегда", days: 0 },
            }
        }
    };

    // DOM elements
    const projectsList = document.getElementById('projects-list');
    const myLicenses = document.getElementById('my-licenses');
    const projectsView = document.getElementById('projects-view');
    const projectView = document.getElementById('project-view');
    const successView = document.getElementById('success-view');
    const projectDetail = document.getElementById('project-detail');

    // ─── Render Projects List ───

    function renderProjects() {
        projectsList.innerHTML = '';
        Object.entries(PRODUCTS).forEach(([id, product]) => {
            const minPrice = Math.min(...Object.values(product.plans).map(p => p.price));
            const card = document.createElement('div');
            card.className = 'project-card';
            card.onclick = () => showProject(id);
            card.innerHTML = `
                <div class="card-icon">${product.icon}</div>
                <div class="card-title">${product.name}</div>
                <div class="card-desc">${product.description}</div>
                <div class="card-price">от ${minPrice} ⭐</div>
            `;
            projectsList.appendChild(card);
        });
    }

    // ─── Show Project Detail ───

    function showProject(projectId) {
        const product = PRODUCTS[projectId];
        if (!product) return;

        // Determine popular plan (year or month)
        const planIds = Object.keys(product.plans);
        const popularId = product.plans.year ? 'year' : planIds[Math.floor(planIds.length / 2)];

        let plansHTML = '';
        Object.entries(product.plans).forEach(([planId, plan]) => {
            const isPopular = planId === popularId;
            const perDay = plan.days > 0 ? (plan.price / plan.days).toFixed(1) : null;
            const perDayText = perDay ? `${perDay} ⭐/день` : 'Лучшая цена';

            plansHTML += `
                <div class="plan-card ${isPopular ? 'popular' : ''}">
                    <div class="plan-name">${plan.label}</div>
                    <div class="plan-price">${plan.price} <span class="stars">⭐</span></div>
                    <div class="plan-per-day">${perDayText}</div>
                    <button class="btn btn-primary" onclick="buyProduct('${projectId}', '${planId}')">
                        Купить за ${plan.price} ⭐
                    </button>
                </div>
            `;
        });

        projectDetail.innerHTML = `
            <div class="project-header" style="text-align:center; margin-bottom:24px;">
                <div style="font-size:48px; margin-bottom:8px;">${product.icon}</div>
                <h2 style="margin-bottom:6px;">${product.name}</h2>
                <p style="color:var(--tg-theme-hint-color); font-size:14px;">${product.description}</p>
            </div>
            ${plansHTML}
        `;

        switchView('project');
    }

    // ─── Buy Product ───

    window.buyProduct = function(projectId, planId) {
        if (!tg) {
            // Fallback: open bot with deep link
            window.open(`https://t.me/allstarspay_bot?start=buy_${projectId}_${planId}`, '_blank');
            return;
        }

        // Send data to bot via Telegram Web App
        tg.sendData(JSON.stringify({
            action: 'buy',
            project: projectId,
            plan: planId
        }));

        // Also try opening bot with deep link as fallback
        setTimeout(() => {
            tg.openTelegramLink(`https://t.me/allstarspay_bot?start=buy_${projectId}_${planId}`);
        }, 500);
    };

    // ─── Switch Views ───

    function switchView(viewName) {
        [projectsView, projectView, successView].forEach(v => v.classList.remove('active'));
        const view = document.getElementById(viewName + '-view');
        if (view) view.classList.add('active');
    }

    window.showProjects = function() {
        switchView('projects');
    };

    // ─── Show Payment Success ───

    function showSuccess(data) {
        document.getElementById('success-details').innerHTML = `
            <p style="margin-bottom:12px;"><strong>${data.project_name}</strong> — ${data.plan_label}</p>
            <div class="license-key-box" id="license-key-text">${data.license_key}</div>
            <button class="copy-btn" onclick="copyKey()">📋 Скопировать ключ</button>
            ${data.expires_at > 0 ? `<p style="margin-top:12px; font-size:13px; color:var(--tg-theme-hint-color);">Действует до: ${new Date(data.expires_at * 1000).toLocaleDateString('ru-RU')}</p>` : '<p style="margin-top:12px; font-size:13px; color:var(--success-color);">♾ Бессрочная лицензия</p>'}
        `;
        switchView('success');
    }

    window.copyKey = function() {
        const keyEl = document.getElementById('license-key-text');
        if (keyEl) {
            navigator.clipboard.writeText(keyEl.textContent).then(() => {
                if (tg) tg.HapticFeedback.notificationOccurred('success');
            });
        }
    };

    // ─── Handle Telegram Web App Events ───

    if (tg) {
        // Main button
        tg.MainButton.setParams({
            text: '🛒 Открыть магазин',
            color: '#7c3aed',
        });

        tg.onEvent('mainButtonClicked', () => {
            switchView('projects');
            tg.MainButton.hide();
        });

        // Handle data from bot
        tg.onEvent('dataReceived', (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.action === 'payment_success') {
                    showSuccess(data);
                }
            } catch (e) {
                console.error('Failed to parse data:', e);
            }
        });

        // Show Main Button if on success view
        tg.MainButton.show();
    }

    // ─── Initialize ───

    renderProjects();

    // Try to load user's licenses if authenticated
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        myLicenses.innerHTML = `
            <div class="license-card">
                <div class="lic-project">👤 ${user.first_name}</div>
                <div class="lic-expire">Загрузка лицензий...</div>
            </div>
        `;
    }

})();
