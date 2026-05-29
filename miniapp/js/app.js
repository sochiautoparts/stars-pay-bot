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

    // Partner Mini Apps
    const PARTNERS = [
        {
            name: "РосЗап — Автозапчасти",
            icon: "🛠",
            url: "https://t.me/rosskozap_bot/zap",
            desc: "Огромное наличие автозапчастей",
            tag: "Авто"
        },
        {
            name: "Шины и Диски 24",
            icon: "🛞",
            url: "https://t.me/tires24_bot/tires",
            desc: "Шины и диски с доставкой",
            tag: "Авто"
        },
        {
            name: "ЛУКОЙЛ Магазин",
            icon: "🛢",
            url: "https://t.me/Lukoiloil_bot/oil",
            desc: "Масла и товары ЛУКОЙЛ с доставкой",
            tag: "Авто"
        },
        {
            name: "Автокод Про",
            icon: "🔍",
            url: "https://t.me/autokod_pro_bot/pro",
            desc: "Проверка авто по базам ГИБДД, ДТП, залогов",
            tag: "Авто"
        },
        {
            name: "КолесоПро",
            icon: "🔩",
            url: "https://t.me/kolesopro_bot/pro",
            desc: "Продажа шин и дисков",
            tag: "Авто"
        },
        {
            name: "Recars — Прокат авто",
            icon: "🌍",
            url: "https://t.me/recars_bot/pro",
            desc: "Прокат автомобилей по всему миру",
            tag: "Путешествия"
        },
        {
            name: "Activ Global",
            icon: "⛷",
            url: "https://t.me/activglobal_bot/pro",
            desc: "Техника для активного отдыха и спорта",
            tag: "Спорт"
        },
        {
            name: "Авиабилеты",
            icon: "✈️",
            url: "https://t.me/bilet_avia_bot/pro",
            desc: "Быстрый поиск дешёвых авиабилетов",
            tag: "Путешествия"
        }
    ];

    // DOM elements
    const projectsList = document.getElementById('projects-list');
    const myLicenses = document.getElementById('my-licenses');
    const partnersList = document.getElementById('partners-list');
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

    // ─── Render Partners ───

    function renderPartners() {
        partnersList.innerHTML = '';
        PARTNERS.forEach(partner => {
            const card = document.createElement('a');
            card.className = 'partner-card';
            card.href = partner.url;
            card.target = '_blank';
            card.onclick = function(e) {
                e.preventDefault();
                if (tg) {
                    tg.openTelegramLink(partner.url);
                } else {
                    window.open(partner.url, '_blank');
                }
            };
            card.innerHTML = `
                <div class="partner-icon">${partner.icon}</div>
                <div class="partner-info">
                    <div class="partner-name">${partner.name}</div>
                    <div class="partner-desc">${partner.desc}</div>
                </div>
                <span class="partner-tag">${partner.tag}</span>
            `;
            partnersList.appendChild(card);
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
            window.open(`https://t.me/allstarspay_bot?start=buy_${projectId}_${planId}`, '_blank');
            return;
        }

        tg.sendData(JSON.stringify({
            action: 'buy',
            project: projectId,
            plan: planId
        }));

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
        tg.MainButton.setParams({
            text: '🛒 Открыть магазин',
            color: '#7c3aed',
        });

        tg.onEvent('mainButtonClicked', () => {
            switchView('projects');
            tg.MainButton.hide();
        });

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

        tg.MainButton.show();
    }

    // ─── Initialize ───

    renderProjects();
    renderPartners();

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
