
// ===== DATA STORE =====
let allEntries = {};
let currentEntry = null;
let isNewEntry = false;
let isAuthenticated = false;

// Global State
let coverImageUrl = '';
let contentImages = [];
let relatedEntries = [];
let iconImageUrl = '';

// Constants
const typeColors = {
    monster: '#ef4444',
    item: '#f59e0b',
    talent: '#3b82f6',
    character: '#10b981',
    lore: '#8b5cf6'
};

const typeIcons = {
    monster: '👹',
    item: '📦',
    talent: '✨',
    character: '👤',
    lore: '📜'
};

const typeNames = {
    monster: '怪物',
    item: '物品',
    talent: '天赋',
    character: '角色',
    lore: '设定'
};

let currentCategoryType = null;
let previousView = 'portal';
let hiddenCategories = []; // Categories hidden from wiki display

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    // Wrap effects in try-catch to prevent blocking core data loading
    try {
        if (typeof initParticles === 'function') initParticles();
        if (typeof initHeroShader === 'function') initHeroShader();
    } catch (e) {
        console.error('Visual effects initialization failed:', e);
    }

    // Load Index
    loadIndex();

    // Setup Marked options
    if (typeof marked !== 'undefined') {
        marked.use({
            breaks: true,
            gfm: true
        });
    }

    // Check URL for direct entry access
    const path = window.location.pathname;
    if (path.startsWith('/wiki/') && path.length > 6) {
        const id = path.substring(6);
        loadEntry(id);
    }

    // Sidebar Counts
    updateSidebarCounts();

    // Setup Search Input
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', handleSearch);
    searchInput.addEventListener('focus', handleSearch);

    // Setup Entry Picker Input
    const pickerInput = document.getElementById('entryPickerInput');
    pickerInput.addEventListener('input', filterEntriesForPicker);
    pickerInput.addEventListener('focus', filterEntriesForPicker);

    // Setup Link Picker Input
    const linkPickerInput = document.getElementById('linkPickerInput');
    linkPickerInput.addEventListener('input', filterLinkPicker);
});

async function loadIndex() {
    try {
        // First load wiki settings to get hidden categories
        const settingsResp = await fetch('/api/wiki-settings');
        const settings = await settingsResp.json();
        hiddenCategories = settings.hidden_categories || [];

        // Apply hidden categories to UI elements
        applyHiddenCategories();

        // Load wiki index
        const resp = await fetch('/api/wiki');
        const data = await resp.json();

        // Filter out hidden category entries
        const rawPages = data.pages || {};
        allEntries = {};
        for (const [id, entry] of Object.entries(rawPages)) {
            if (!hiddenCategories.includes(entry.type)) {
                allEntries[id] = entry;
            }
        }

        updateSidebarCounts();
    } catch (e) {
        console.error('Failed to load wiki index', e);
        showToast('无法连接服务器', true);
    }
}

// Apply hidden categories to sidebar and portal cards
function applyHiddenCategories() {
    const categories = ['monster', 'item', 'talent', 'character', 'lore'];
    categories.forEach(cat => {
        const isHidden = hiddenCategories.includes(cat);

        // Hide sidebar nav items
        const sidebarItem = document.querySelector(`.sidebar-nav-item[data-category="${cat}"]`);
        if (sidebarItem) sidebarItem.style.display = isHidden ? 'none' : '';

        // Hide portal cards
        const portalCard = document.querySelector(`.category-card[data-category="${cat}"]`);
        if (portalCard) portalCard.style.display = isHidden ? 'none' : '';
    });
}

// ===== NAVIGATION =====
function showPortal() {
    document.getElementById('portalView').classList.remove('hidden');
    document.getElementById('categoryListView').classList.remove('active');
    document.getElementById('entryView').classList.remove('active');
    document.getElementById('editView').classList.remove('active');

    // Clear history state
    history.pushState(null, '', '/wiki');
    previousView = 'portal';
}

// Global goBack function
window.goBack = function () {
    if (previousView === 'list' && currentCategoryType) {
        showCategoryList(currentCategoryType);
    } else {
        showPortal();
    }
}

function showCategoryList(type) {
    currentCategoryType = type;
    const container = document.getElementById('categoryListView');
    const titleEl = document.getElementById('categoryListTitle');
    const iconEl = document.getElementById('categoryListIcon');
    const grid = document.getElementById('entryGrid');

    if (!titleEl || !iconEl) {
        console.error('Category list DOM elements missing');
        return;
    }

    titleEl.textContent = typeNames[type] || type;

    // Filter entries
    if (!allEntries) allEntries = {};
    const entries = Object.entries(allEntries).filter(([id, e]) => e && e.type === type);

    // User requested simple Emoji icon ONLY
    iconEl.innerHTML = `<div style="font-size:3rem; filter:drop-shadow(0 0 10px rgba(255,255,255,0.2))">${typeIcons[type] || '📄'}</div>`;

    if (type === 'talent') {
        renderTalentTrees(entries);
    } else {
        renderStandardGrid(entries);
    }

    document.getElementById('portalView').classList.add('hidden');
    container.classList.add('active');
    document.getElementById('entryView').classList.remove('active');
    document.getElementById('editView').classList.remove('active');

    history.pushState({ category: type }, '', '/wiki');
    previousView = 'list';
}

function renderStandardGrid(entries) {
    const grid = document.getElementById('entryGrid');
    grid.style.display = 'grid'; // Reset if it was block for talents
    grid.innerHTML = entries.map(([id, e]) => `
        <div class="entry-card" onclick="loadEntry('${id}')">
            <div class="entry-card-content">
                <div class="entry-card-header">
                    <div class="entry-icon-box">
                        ${(e.icon || e.icon_image || e.cover_image) ?
            `<img src="${e.icon || e.icon_image || e.cover_image}" style="width:100%;height:100%;object-fit:contain;">` :
            `<div class="placeholder">${typeIcons[e.type]}</div>`}
                    </div>
                    <div class="entry-titles">
                        <div class="entry-card-title">${e.title}</div>
                        <div class="entry-card-subtitle">${e.subtitle || id}</div>
                    </div>
                </div>
                <div class="entry-card-tags">
                    ${(e.tags || []).slice(0, 3).map(t => `<span class="entry-tag">${t}</span>`).join('')}
                </div>
            </div>
        </div>
    `).join('');
}


// ===== SKYRIM STYLE TALENT TREE (ORGANIC LAYOUT) =====

let groupAliases = {};
let aliasesFetched = false;

function renameAuthority(groupId, currentName) {
    const newName = prompt(`为权柄 [${groupId}] 设定新名称:`, currentName);
    if (newName !== null) {
        groupAliases[groupId] = newName;
        // Save to server
        fetch('/api/wiki/group-aliases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(groupAliases)
        }).then(() => {
            // Reload current view
            const entry = document.querySelector('.sidebar-nav-item[onclick*="category-talent"]');
            if (entry) entry.click(); // Trigger reload
        });
    }
}

// Helper to calculate tree levels
function calculateTalentLevels(items) {
    const levels = {};
    const idToItem = {};
    items.forEach(it => idToItem[it.id] = it);

    const visiting = new Set();
    const memo = {};

    function getLevel(id) {
        if (memo[id] !== undefined) return memo[id];
        if (visiting.has(id)) return 0;
        visiting.add(id);
        const item = idToItem[id];
        if (!item) { visiting.delete(id); return 0; }

        const parents = (item.talent_meta?.parents || []).map(p => p.startsWith('talent-') ? p : 'talent-' + p).filter(p => idToItem[p]);

        if (parents.length === 0) {
            visiting.delete(id);
            memo[id] = 0;
            return 0;
        }

        // Level is max(parent_level) + 1
        let maxL = 0;
        parents.forEach(p => maxL = Math.max(maxL, getLevel(p) + 1));
        visiting.delete(id);
        memo[id] = maxL;
        return maxL;
    }

    items.forEach(it => getLevel(it.id));
    return memo;
}

function renderTalentTrees(entries) {
    // 防御性检查：确保 entries 是有效数组
    if (!entries || !Array.isArray(entries)) {
        console.warn('renderTalentTrees: entries is invalid, skipping render');
        return;
    }

    const grid = document.getElementById('entryGrid');

    // ★ 关键修复：完全清空 grid 内容，防止 DOM 累积
    grid.innerHTML = '';
    grid.style.display = 'block';

    // 1. 星座图容器
    grid.innerHTML = `<div class="talent-constellation-view" id="constellationView">
        <div class="constellation-map" id="constellationMap">
            <canvas id="talentShaderCanvas" style="position:absolute; inset:0; width:100%; height:100%; z-index:0; pointer-events:none; mix-blend-mode: screen; opacity: 0.6;"></canvas>
            <svg class="talent-svg-layer" id="talentSvgLayer" style="z-index:1; position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none;"></svg>
            <div class="talent-star-layer" id="talentStarLayer" style="z-index:2; position:absolute; top:0; left:0; width:100%; height:100%;"></div>
        </div>
        <div class="constellation-hint">
            <span style="opacity:0.8">↔ 左右滑动切换权柄</span>
            <span style="margin:0 10px; opacity:0.3">|</span>
            <span style="opacity:0.8">点击节点查看详情</span>
        </div>
    </div>`;

    // Init Shader
    if (window.initTalentShader) {
        requestAnimationFrame(() => window.initTalentShader('talentShaderCanvas'));
    }

    // Fetch aliases if not loaded (ONE TIME ONLY)
    if (!aliasesFetched) {
        aliasesFetched = true;
        fetch('/api/wiki/group-aliases')
            .then(r => r.json())
            .then(data => {
                groupAliases = data;
                showCategoryList('talent');
            })
            .catch(e => console.error("Alias fetch failed", e));
        return;
    }

    const view = document.getElementById('constellationView');
    const map = document.getElementById('constellationMap');
    const starLayer = document.getElementById('talentStarLayer');
    const svgLayer = document.getElementById('talentSvgLayer');

    if (!view || !map || !starLayer || !svgLayer) {
        console.error('Talent tree DOM elements not found');
        return;
    }

    // 确定性伪随机函数（基于字符串哈希）
    function seededRandom(seed) {
        let hash = 0;
        for (let i = 0; i < seed.length; i++) {
            hash = ((hash << 5) - hash) + seed.charCodeAt(i);
            hash = hash & hash;
        }
        return ((hash % 1000) / 1000 + 1) % 1;
    }

    // Group Data
    const groups = {};
    entries.forEach(([id, e]) => {
        const meta = e.talent_meta || {};
        const groupId = meta.group_id || 'misc';
        if (!groups[groupId]) groups[groupId] = [];
        groups[groupId].push({ id, ...e });
    });

    const themes = {
        '100001': { name: '贪婪', color: '#f5a623' },
        '10018': { name: '自然', color: '#10b981' },
        '10009': { name: '雷霆', color: '#00d4ff' },
        'misc': { name: '其他', color: '#8b5cf6' }
    };

    const groupIds = Object.keys(groups);
    const groupCount = groupIds.length;

    // 布局配置
    const availableH = view.clientHeight || 800;
    const columnWidth = view.clientWidth || 900;
    const mapWidth = columnWidth * groupCount;
    const mapHeight = availableH;

    // 计算全局最大层级
    let globalMaxLevel = 1;
    Object.values(groups).forEach(items => {
        const lvls = calculateTalentLevels(items);
        const m = Math.max(0, ...Object.values(lvls));
        if (m > globalMaxLevel) globalMaxLevel = m;
    });

    // 布局参数
    const topPadding = 80;
    const bottomPadding = 120;
    const usableHeight = mapHeight - topPadding - bottomPadding;
    const levelHeight = usableHeight / Math.max(1, globalMaxLevel);

    // 设置地图尺寸
    map.style.width = `${mapWidth}px`;
    map.style.height = `${mapHeight}px`;
    map.style.transform = 'none';
    map.style.left = '0';

    // 滚动设置
    view.style.overflowX = 'auto';
    view.style.overflowY = 'hidden';
    view.style.scrollSnapType = 'x mandatory';
    view.style.cursor = 'grab';

    const starPositions = {};

    groupIds.forEach((groupId, index) => {
        const items = groups[groupId];
        const centerX = (index * columnWidth) + (columnWidth / 2);

        // 主题
        const known = themes[groupId] || {};
        const displayName = groupAliases[groupId] || known.name || groupId;
        const themeColor = known.color || '#b4c8ff';

        // ★ 上古卷轴风格：星云背景（更大、更柔和）
        const nebula = document.createElement('div');
        nebula.className = 'authority-nebula';
        nebula.style.cssText = `
            position: absolute;
            left: ${centerX}px;
            top: ${mapHeight / 2}px;
            width: 800px;
            height: 800px;
            background: radial-gradient(ellipse, ${themeColor}22 0%, ${themeColor}08 40%, transparent 70%);
            filter: blur(60px);
            pointer-events: none;
            z-index: 0;
        `;
        map.insertBefore(nebula, svgLayer);

        // Snap 页面标记
        const snapPage = document.createElement('div');
        snapPage.style.cssText = `
            position: absolute;
            left: ${index * columnWidth}px;
            top: 0;
            width: ${columnWidth}px;
            height: 100%;
            scroll-snap-align: center;
            pointer-events: none;
        `;
        map.appendChild(snapPage);

        // 权柄标题（底部）
        const titleContainer = document.createElement('div');
        titleContainer.className = 'authority-title-container';
        titleContainer.style.cssText = `
            position: absolute;
            left: ${centerX}px;
            bottom: 180px;
            transform: translateX(-50%);
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        const title = document.createElement('div');
        title.className = 'authority-title';
        title.textContent = displayName;
        title.style.cssText = `
            color: ${themeColor};
            font-size: 1.8rem;
            font-weight: 600;
            text-shadow: 0 0 30px ${themeColor}88, 0 2px 4px rgba(0,0,0,0.8);
            letter-spacing: 0.15em;
        `;

        const editBtn = document.createElement('span');
        editBtn.innerHTML = '✎';
        editBtn.className = 'authority-edit-btn';
        editBtn.style.cssText = `
            opacity: 0.4;
            cursor: pointer;
            font-size: 1rem;
            transition: opacity 0.2s;
        `;
        editBtn.onmouseenter = () => editBtn.style.opacity = '1';
        editBtn.onmouseleave = () => editBtn.style.opacity = '0.4';
        editBtn.onclick = (e) => {
            e.stopPropagation();
            renameAuthority(groupId, displayName);
        };

        titleContainer.appendChild(title);
        titleContainer.appendChild(editBtn);
        map.appendChild(titleContainer);

        // ★ 计算节点位置（确定性布局，上古卷轴风格垂直树）
        const levels = calculateTalentLevels(items);
        const byLevel = {};
        items.forEach(it => {
            const l = levels[it.id];
            if (!byLevel[l]) byLevel[l] = [];
            byLevel[l].push(it);
        });

        // 对每层内的节点排序（确保顺序一致）
        Object.keys(byLevel).forEach(lv => {
            byLevel[lv].sort((a, b) => a.id.localeCompare(b.id));
        });

        // ★ Upward Growth Layout (Directed Hierarchical)
        const usefulHeight = mapHeight - topPadding - bottomPadding;
        const maxLevel = Math.max(...Object.values(levels), 1);
        const levelSpacing = usefulHeight / (maxLevel + 1);

        Object.keys(byLevel).forEach(lvStr => {
            const lv = parseInt(lvStr);
            const levelNodes = byLevel[lv];
            const nodeCount = levelNodes.length;

            // Growing Upward: Level 0 is at the bottom, Level N is at the top
            // Y = mapHeight - bottomPadding - (lv + 1) * levelSpacing
            const baseY = mapHeight - bottomPadding - (lv + 1) * levelSpacing;

            levelNodes.forEach((item, i) => {
                // Spread horizontally within the columnWidth
                // index * columnWidth is the start of this authority
                const horizontalPadding = 80;
                const innerWidth = columnWidth - horizontalPadding * 2;

                let finalX;
                if (nodeCount === 1) {
                    finalX = (index * columnWidth) + (columnWidth / 2);
                } else {
                    finalX = (index * columnWidth) + horizontalPadding + (i / (nodeCount - 1)) * innerWidth;
                }

                // Add a small deterministic jitter for "organic" feel but maintain structure
                const jitterX = (seededRandom(item.id + '_jx') - 0.5) * 40;
                const jitterY = (seededRandom(item.id + '_jy') - 0.5) * 30;

                starPositions[item.id] = { x: finalX + jitterX, y: baseY + jitterY };

                // Render Star
                const star = document.createElement('div');
                const isRoot = (item.talent_meta?.parents?.length === 0);
                star.className = 'talent-star' + (isRoot ? ' unlocked' : '');
                star.style.cssText = `
                    position: absolute;
                    left: ${finalX + jitterX}px;
                    top: ${baseY + jitterY}px;
                    --auth-color: ${themeColor};
                `;

                // Tooltip events
                star.onmouseenter = (e) => showTooltip(e, item, themeColor);
                star.onmousemove = (e) => moveTooltip(e);
                star.onmouseleave = () => hideTooltip();

                star.innerHTML = `<div class="talent-star-label">${item.title}</div>`;

                star.onclick = (e) => {
                    e.stopPropagation();
                    loadEntry(item.id);
                };

                starLayer.appendChild(star);
            });
        });



    });

    // ★ 绘制连线（上古卷轴风格：细腻的金色/银色线条）

    // ★ 绘画连线（极简稳健版）
    setTimeout(() => {
        const idToItem = {};
        entries.forEach(([id, item]) => idToItem[id] = item);

        // 强制设置 SVG 尺寸和 z-index
        svgLayer.style.display = 'block';
        svgLayer.style.zIndex = '5';

        const totalWidth = Math.max(map.scrollWidth, 3000);
        const totalHeight = Math.max(map.scrollHeight, 1200);

        svgLayer.style.width = totalWidth + 'px';
        svgLayer.style.height = totalHeight + 'px';
        svgLayer.setAttribute("width", totalWidth);
        svgLayer.setAttribute("height", totalHeight);
        svgLayer.setAttribute("viewBox", `0 0 ${totalWidth} ${totalHeight}`);

        // 清空
        while (svgLayer.firstChild) svgLayer.removeChild(svgLayer.firstChild);

        Object.keys(starPositions).forEach(id => {
            const item = idToItem[id];
            if (!item) return;
            const start = starPositions[id];

            const rawParents = item.talent_meta?.parents || [];
            const parents = rawParents.map(rawP => {
                const p = String(rawP);
                if (starPositions[p]) return p;
                const prefixes = ['talent-', 't-', 'node-'];
                for (let pref of prefixes) {
                    if (starPositions[pref + p]) return pref + p;
                }
                return p;
            });

            parents.forEach(pId => {
                const end = starPositions[pId];
                if (end) {
                    const themeId = (item.talent_meta && item.talent_meta.group_id) || 'misc';
                    const color = (themes[themeId] && themes[themeId].color) || '#FFD700';

                    const dy = Math.abs(end.y - start.y);
                    const controlY = dy * 0.5;

                    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                    path.setAttribute("d", `M${Math.round(start.x)},${Math.round(start.y)} C${Math.round(start.x)},${Math.round(start.y + controlY)} ${Math.round(end.x)},${Math.round(end.y - controlY)} ${Math.round(end.x)},${Math.round(end.y)}`);
                    path.setAttribute("fill", "none");
                    path.setAttribute("stroke", color);
                    path.setAttribute("stroke-width", "3");
                    path.setAttribute("stroke-opacity", "0.9");
                    path.style.pointerEvents = "none";

                    svgLayer.appendChild(path);
                }
            });
        });
    }, 400);

    // 鼠标拖拽滑动
    let isDragging = false;
    let startX = 0;
    let scrollStart = 0;

    view.addEventListener('mousedown', (e) => {
        if (e.target.closest('.talent-star')) return;
        isDragging = true;
        startX = e.clientX;
        scrollStart = view.scrollLeft;
        view.style.cursor = 'grabbing';
        view.style.scrollSnapType = 'none';
        e.preventDefault();
    });

    view.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = startX - e.clientX;
        view.scrollLeft = scrollStart + dx;
    });

    view.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            view.style.cursor = 'grab';
            view.style.scrollSnapType = 'x mandatory';
        }
    });

    view.addEventListener('mouseleave', () => {
        if (isDragging) {
            isDragging = false;
            view.style.cursor = 'grab';
            view.style.scrollSnapType = 'x mandatory';
        }
    });

    // 初始滚动
    setTimeout(() => {
        view.scrollLeft = 0;
    }, 100);
}

// Tooltip Helpers
function getTooltip() {
    let tt = document.getElementById('talentTooltip');
    if (!tt) {
        tt = document.createElement('div');
        tt.id = 'talentTooltip';
        document.body.appendChild(tt);
    }
    return tt;
}

function showTooltip(e, item, color) {
    const tt = getTooltip();
    tt.innerHTML = `
        <h4 style="color:${color}">${item.title || item.id}</h4>
        <div class="tt-desc">${item.summary || '暂无描述'}</div>
        <div class="tt-meta">点击查看详情</div>
    `;
    tt.style.borderColor = color;
    tt.style.boxShadow = `0 4px 20px ${color}40`;
    tt.style.opacity = 1;
    moveTooltip(e);
}

function hideTooltip() {
    const tt = getTooltip();
    tt.style.opacity = 0;
}

function moveTooltip(e) {
    const tt = getTooltip();
    tt.style.left = (e.clientX + 15) + 'px';
    tt.style.top = (e.clientY + 15) + 'px';
}


// ===== ENTRY VIEW =====
async function loadEntry(id) {
    // Check if entry exists in index
    if (!allEntries[id]) {
        await loadIndex();
        if (!allEntries[id]) {
            showToast('词条未找到', true);
            showPortal();
            return;
        }
    }

    // Fetch full entry data from API (allEntries only contains metadata)
    try {
        const resp = await fetch('/api/wiki/' + id);
        if (!resp.ok) {
            showToast('加载词条失败', true);
            showPortal();
            return;
        }
        const fullEntryData = await resp.json();
        currentEntry = { id, ...fullEntryData };
    } catch (e) {
        console.error('Failed to load entry:', e);
        showToast('加载词条失败', true);
        showPortal();
        return;
    }

    // Update URL
    if (window.location.pathname !== '/wiki/' + id) {
        history.pushState({ entryId: id }, '', '/wiki/' + id);
    }

    // Populate Breadcrumb
    const typeName = typeNames[currentEntry.type] || currentEntry.type;

    // Use querySelector because the HTML element uses class="breadcrumb" not an ID
    const bcContainer = document.querySelector('.breadcrumb');

    if (bcContainer) {
        // Safe onclick injection using window scope if needed, but local function scope should work if functions are global.
        // Assuming goBack, showPortal, showCategoryList are global functions.
        bcContainer.innerHTML = `
            <span class="bc-link" onclick="goBack()" style="cursor:pointer; color:var(--text-muted); padding:0 5px;">← 返回</span>
            <span class="bc-sep" style="opacity:0.3; margin:0 5px;">/</span>
            <span class="bc-link" onclick="showPortal()" style="cursor:pointer; color:var(--text-muted); padding:0 5px;">首页</span>
            <span class="bc-sep" style="opacity:0.3; margin:0 5px;">/</span>
            <span class="bc-link" onclick="showCategoryList('${currentEntry.type}')" style="cursor:pointer; color:var(--text-muted); padding:0 5px;">${typeName}</span>
            <span class="bc-sep" style="opacity:0.3; margin:0 5px;">/</span>
            <span class="bc-current" style="color:var(--text-bright); padding:0 5px;">${currentEntry.title}</span>
        `;
    }

    // document.getElementById('breadcrumbType').textContent = typeName; 
    // document.getElementById('breadcrumbTitle').textContent = currentEntry.title;    

    // Populate Content

    // Render Cover Image
    const coverEl = document.getElementById('entryCover');
    if (coverEl) {
        if (currentEntry.cover_image) {
            coverEl.innerHTML = `<img src="${currentEntry.cover_image}" alt="Cover Image">`;
            coverEl.style.display = 'block';
        } else {
            coverEl.style.display = 'none';
            coverEl.innerHTML = '';
        }
    }

    document.getElementById('entryTitle').textContent = currentEntry.title;
    document.getElementById('entrySubtitle').textContent = currentEntry.subtitle || currentEntry.id;

    // Render Markdown content
    let contentHtml = '';

    // Priority: render sections if available, fallback to content
    // Render BOTH content (intro) and sections (details)
    if (currentEntry.content) {
        const processed = currentEntry.content.replace(/!\[(.*?)\]\(([^)/]+)\)/g, '![$1](/wiki/assets/$2)');
        contentHtml += marked.parse(processed);
    }

    if (currentEntry.sections && Object.keys(currentEntry.sections).length > 0) {
        // Render each section
        for (const [sectionTitle, sectionContent] of Object.entries(currentEntry.sections)) {
            if (sectionContent) {
                // 使用更宽松的正则，并排除已包含路径的情况
                const processed = sectionContent.replace(/!\[(.*?)\]\(([^)/]+)\)/g, '![$1](/wiki/assets/$2)');
                contentHtml += `<h2 class="section-title">${sectionTitle}</h2>`;
                contentHtml += marked.parse(processed);
            }
        }
    }

    if (!contentHtml) {
        contentHtml = '<p style="color:var(--text-muted)">暂无内容</p>';
    }

    // Generate TOC
    const tocData = generateTableOfContents(contentHtml);
    document.getElementById('entryBody').innerHTML = tocData.content;

    // Render TOC if exists
    const tocContainer = document.getElementById('entryToc');
    if (tocContainer) {
        if (tocData.toc) {
            tocContainer.innerHTML = tocData.toc;
            tocContainer.style.display = 'block';
        } else {
            tocContainer.style.display = 'none';
        }
    }

    // Render Infobox
    renderInfobox(currentEntry);

    // Switch Views
    document.getElementById('portalView').classList.add('hidden');
    document.getElementById('categoryListView').classList.remove('active');
    document.getElementById('entryView').classList.add('active');
    document.getElementById('editView').classList.remove('active');

    // Scroll to top
    window.scrollTo(0, 0);
}

function renderInfobox(entry) {
    const table = document.getElementById('infoboxTable');
    const infoboxTitle = document.getElementById('infoboxTitle');
    const infoboxType = document.getElementById('infoboxType');
    const infoboxIcon = document.getElementById('infoboxIcon');

    if (infoboxTitle) infoboxTitle.textContent = entry.title;
    if (infoboxType) infoboxType.textContent = typeNames[entry.type] || entry.type;
    if (infoboxIcon) infoboxIcon.textContent = typeIcons[entry.type] || '📄';


    // Add Image to Infobox Header if exists
    // Note: The HTML structure expects an image inside .infobox-header or .infobox-image?
    // Let's modify the infobox header to support image
    // Check if we need to inject image container
    let imgContainer = document.getElementById('infoboxImageContainer');
    if (!imgContainer) {
        imgContainer = document.createElement('div');
        imgContainer.id = 'infoboxImageContainer';
        imgContainer.className = 'infobox-image';
        const header = document.querySelector('.infobox-header');
        header.insertBefore(imgContainer, header.firstChild);
    }

    // Display icon or cover image (prefer icon for infobox)
    const displayImage = entry.icon || entry.cover_image;
    if (displayImage) {
        imgContainer.style.display = 'flex';
        imgContainer.innerHTML = `<img src="${displayImage}" alt="icon" style="max-width:100%;max-height:180px;object-fit:contain;">`;
    } else {
        imgContainer.style.display = 'none';
        imgContainer.innerHTML = '';
    }

    // Dynamic Fields
    let fields = [];

    // Common fields
    if (entry.id) fields.push(['ID', entry.id]);

    // Type specific
    if (entry.data) {
        Object.entries(entry.data).forEach(([k, v]) => {
            fields.push([k, v]);
        });
    }

    table.innerHTML = fields.map(([k, v]) => `
        <div class="infobox-row">
            <span class="infobox-label">${k}</span>
            <span class="infobox-value">${v}</span>
        </div>
    `).join('');

    // Tags
    const tagsContainer = document.getElementById('infoboxTags');
    if (entry.tags && entry.tags.length > 0) {
        tagsContainer.innerHTML = entry.tags.map(t => `<span class="infobox-tag">${t}</span>`).join('');
    } else {
        tagsContainer.innerHTML = '';
    }
}

function goBack() {
    // If we have history, back. Else portal
    if (window.history.length > 1) {
        window.history.back();
    } else {
        showPortal();
    }
}

// ===== SEARCH FUNCTION =====
function handleSearch() {
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    const dropdown = document.getElementById('searchDropdown');

    if (!query) {
        dropdown.classList.remove('active');
        return;
    }

    const matches = Object.values(allEntries).filter(entry =>
        entry.title?.toLowerCase().includes(query) ||
        entry.id?.toLowerCase().includes(query) ||
        entry.subtitle?.toLowerCase().includes(query)
    ).slice(0, 10);

    if (matches.length > 0) {
        dropdown.innerHTML = matches.map(entry => `
            <div class="search-result-item" onclick="loadEntry('${entry.id}'); document.getElementById('searchDropdown').classList.remove('active');">
                <div class="search-result-icon" style="background: ${typeColors[entry.type] || '#444'}22; color: ${typeColors[entry.type] || '#ccc'}">
                    ${typeIcons[entry.type] || '📄'}
                </div>
                <div class="search-result-info">
                    <div class="search-result-title">${entry.title}</div>
                    <div class="search-result-type">${typeNames[entry.type] || entry.type}</div>
                </div>
            </div>
        `).join('');
    } else {
        dropdown.innerHTML = `<div class="search-no-result">无相关结果</div>`;
    }

    dropdown.classList.add('active');
}

function updateSidebarCounts() {
    const counts = { monster: 0, item: 0, talent: 0, character: 0, lore: 0 };

    if (!allEntries) return;

    Object.values(allEntries).forEach(entry => {
        if (counts[entry.type] !== undefined) {
            counts[entry.type]++;
        }
    });

    let total = 0;
    for (const [type, count] of Object.entries(counts)) {
        total += count;
        const el = document.getElementById('count-' + type);
        if (el) el.textContent = count;

        // Also update portal card counts
        const portalEl = document.getElementById('portal-count-' + type);
        if (portalEl) portalEl.textContent = count + ' 条';
    }

    // Update Total Stat
    const totalEl = document.getElementById('statTotal');
    if (totalEl) totalEl.textContent = total;
}


// ===== EDIT SYSTEM =====

function requestEditMode() {
    previousView = 'entry'; // Default assumption

    const portalView = document.getElementById('portalView');
    const categoryListView = document.getElementById('categoryListView');

    // Check classes for visibility
    if (portalView && !portalView.classList.contains('hidden')) {
        previousView = 'portal';
    } else if (categoryListView && categoryListView.classList.contains('active')) {
        previousView = 'list';
    }
    if (portalView && !portalView.classList.contains('hidden')) {
        previousView = 'portal';
    } else if (categoryListView && categoryListView.classList.contains('active')) {
        previousView = 'list';
    }

    if (isAuthenticated) {
        openEditor();
    } else {
        document.getElementById('verifyModal').classList.add('active');
        document.getElementById('verifyCode').focus();
    }
}

async function verifyCode() {
    const code = document.getElementById('verifyCode').value;
    try {
        const resp = await fetch('/api/wiki/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: code })
        });
        const result = await resp.json();
        if (result.success) {
            isAuthenticated = true;
            closeModal();
            openEditor();
            showToast('验证通过');
        } else {
            showToast('验证码错误', true);
        }
    } catch (e) {
        showToast('验证失败', true);
    }
}

function closeModal() {
    document.querySelectorAll('.modal, .modal-overlay').forEach(m => m.classList.remove('active'));
}

function cancelEdit() {
    document.getElementById('editView').classList.remove('active');

    // Restore previous view
    if (previousView === 'portal') {
        showPortal();
    } else if (previousView === 'list' && currentCategoryType) {
        showCategoryList(currentCategoryType);
    } else if (previousView === 'entry' && currentEntry) {
        // Return to entry view
        document.getElementById('entryView').classList.add('active');
    } else {
        // Fallback
        showPortal();
    }
}



function openEditor() {
    document.getElementById('editView').classList.add('active');
    document.getElementById('entryView').classList.remove('active');
    document.getElementById('portalView').classList.add('hidden');
    document.getElementById('categoryListView').classList.remove('active');

    // Populate Fields based on current view/entry
    if (previousView === 'entry' && currentEntry) {
        document.getElementById('editId').value = currentEntry.id;
        document.getElementById('editType').value = currentEntry.type;
        document.getElementById('editTitle').value = currentEntry.title;
        document.getElementById('editSubtitle').value = currentEntry.subtitle || '';
        document.getElementById('editTags').value = (currentEntry.tags || []).join(', ');

        // Init Images
        iconImageUrl = currentEntry.icon || '';
        coverImageUrl = currentEntry.cover_image || '';

        // Render Previews
        renderIconPreview();
        renderCoverPreview();

        // Content
        // Content
        // Content
        // Combine content and sections for editing
        let combinedContent = '';
        if (currentEntry.content) {
            combinedContent += currentEntry.content;
        }

        if (currentEntry.sections && Object.keys(currentEntry.sections).length > 0) {
            let parts = [];
            // Add sections
            for (const [title, text] of Object.entries(currentEntry.sections)) {
                // Determine if we need newlines
                parts.push(`## ${title}\n${text}`);
            }
            if (combinedContent) combinedContent += '\n\n';
            combinedContent += parts.join('\n\n');
        }

        document.getElementById('editContent').value = combinedContent;

        // Restore Images Gallery
        if (currentEntry.images && Array.isArray(currentEntry.images)) {
            contentImages = [...currentEntry.images];
        } else {
            contentImages = [];
        }
        renderContentImagesGallery();

        // Restore Related Entries
        if (currentEntry.related && Array.isArray(currentEntry.related)) {
            relatedEntries = [...currentEntry.related];
        } else {
            relatedEntries = [];
        }
        renderRelatedEntries();

        // Infobox
        updateInfoboxFields(currentEntry.infobox || {});

    } else {
        // Create Mode
        document.getElementById('editId').value = generateId();
        document.getElementById('editType').value = 'monster'; // Default
        document.getElementById('editTitle').value = '';
        document.getElementById('editSubtitle').value = '';
        document.getElementById('editContent').value = '';
        document.getElementById('editTags').value = '';

        iconImageUrl = '';
        coverImageUrl = '';
        renderIconPreview();
        renderCoverPreview();

        // Reset Gallery & Related
        contentImages = [];
        relatedEntries = [];
        renderContentImagesGallery();
        renderRelatedEntries();

        // Init Empty Infobox
        updateInfoboxFields({});
    }
}


function generateId() {
    return Math.floor(10000 + Math.random() * 90000).toString();
}

async function saveEntry() {
    // Collect Infobox Data
    const infobox = {};
    document.querySelectorAll('.infobox-field-row').forEach(row => {
        const key = row.querySelector('.key-input').value;
        const val = row.querySelector('.val-input').value;
        if (key) infobox[key] = val;
    });

    const entry = {
        id: document.getElementById('editId').value,
        type: document.getElementById('editType').value,
        title: document.getElementById('editTitle').value,
        subtitle: document.getElementById('editSubtitle').value,
        tags: document.getElementById('editTags').value.split(',').map(t => t.trim()).filter(t => t),
        content: document.getElementById('editContent').value,

        // Full Data
        icon: iconImageUrl,
        cover_image: coverImageUrl,
        infobox: infobox,
        images: contentImages,
        related: relatedEntries,
        updated_at: new Date().toISOString()
    };

    // Parse Content into Sections
    const rawContent = entry.content;

    // Clear content to avoid duplication (it will be repopulated with just the intro)
    entry.content = '';

    const sections = {};
    let currentSection = null; // null means "Intro/Content" area
    let currentText = [];

    // Split by lines
    const lines = rawContent.split('\n');
    for (let line of lines) {
        // Detect H2 headers as section separators
        if (line.trim().startsWith('## ')) {
            // Save previous block
            if (currentText.length > 0) {
                const textBlock = currentText.join('\n').trim();
                if (currentSection === null) {
                    entry.content = textBlock;
                } else {
                    sections[currentSection] = textBlock;
                }
            }
            // Start new section
            currentSection = line.trim().substring(3).trim();
            currentText = [];
        } else {
            currentText.push(line);
        }
    }
    // Save last block
    if (currentText.length > 0) {
        const textBlock = currentText.join('\n').trim();
        if (currentSection === null) {
            entry.content = textBlock;
        } else {
            sections[currentSection] = textBlock;
        }
    }

    entry.sections = sections;

    if (!entry.id || !entry.title) {
        showToast('ID和标题不能为空', true);
        return;
    }

    try {
        const resp = await fetch('/api/wiki/' + entry.id, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(entry)
        });
        if (resp.ok) {
            showToast('保存成功');
            // Reload index
            await loadIndex();
            // Go to entry
            loadEntry(entry.id);
        } else {
            showToast('保存失败', true);
        }
    } catch (e) {
        console.error(e);
        showToast('保存错误', true);
    }
}

// ===== UI HELPERS =====
function showToast(msg, isError = false) {
    const toast = document.createElement('div');
    toast.className = 'toast' + (isError ? ' error' : '');
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }, 10);
}

// ===== IMAGE UPLOAD FUNCTIONS =====

async function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/api/wiki/upload', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (data.success) {
            return data.url;
        } else {
            showToast('上传失败: ' + data.message, true);
            return null;
        }
    } catch (e) {
        showToast('上传失败', true);
        return null;
    }
}

async function handleContentImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    showToast('正在上传...');
    const url = await uploadImage(file);
    if (url) {
        contentImages.push(url);
        renderContentImagesGallery();
        showToast('图片上传成功');
    }
    event.target.value = '';
}

async function handleIconImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    showToast('正在上传图标...');
    const url = await uploadImage(file);
    if (url) {
        iconImageUrl = url;
        renderIconPreview();
        showToast('图标上传成功');
    }
    event.target.value = '';
}

async function handleCoverImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    showToast('正在上传封面...');
    const url = await uploadImage(file);
    if (url) {
        coverImageUrl = url;
        renderCoverPreview();
        showToast('封面上传成功');
    }
    event.target.value = '';
}

function renderIconPreview() {
    const zone = document.getElementById('iconUploadZone');
    if (iconImageUrl) {
        zone.innerHTML = `<img src="${iconImageUrl}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;">`;
    } else {
        zone.innerHTML = `<div class="icon-upload-placeholder"><span>Upload</span></div>`;
    }
}

function renderCoverPreview() {
    const zone = document.getElementById('coverImageZone');
    // Keep icon text
    if (coverImageUrl) {
        zone.style.backgroundImage = `url('${coverImageUrl}')`;
        zone.style.backgroundSize = 'cover';
        zone.style.backgroundPosition = 'center';
        zone.innerHTML = `<div class="image-upload-text" style="background:rgba(0,0,0,0.5);padding:4px 8px;border-radius:4px;color:white;">点击更换封面</div>`;
    } else {
        zone.style.backgroundImage = '';
        zone.innerHTML = `
            <div class="image-upload-icon">🖼️</div>
            <div class="image-upload-text">点击上传封面图片</div>
        `;
    }
}

// ===== INFOBOX EDITING =====
function updateInfoboxFields(existingData = null) {
    const container = document.getElementById('infoboxFieldsContainer');
    container.innerHTML = ''; // Clear

    const type = document.getElementById('editType').value;

    // Default keys based on type if no existing data
    let data = existingData || {};
    if (!existingData && Object.keys(data).length === 0) {
        if (type === 'monster') data = { '弱点': '', '危险度': '' };
        if (type === 'item') data = { '品质': '', '来源': '' };
        if (type === 'character') data = { '阵营': '', '配音': '' };
    }

    // Header
    const header = document.createElement('div');
    header.className = 'edit-section-title';
    header.innerHTML = `
        <span>ℹ️ 信息栏 (Infobox)</span>
        <button class="btn btn-secondary" style="font-size:12px;padding:2px 8px;margin-left:10px;" onclick="addInfoboxField()">+ 添加字段</button>
    `;
    container.appendChild(header);

    // Render Fields
    Object.entries(data).forEach(([key, val]) => {
        createInfoboxRow(container, key, val);
    });
}

function addInfoboxField() {
    const container = document.getElementById('infoboxFieldsContainer');
    createInfoboxRow(container, '', '');
}

function createInfoboxRow(container, key, val) {
    const row = document.createElement('div');
    row.className = 'infobox-field-row form-group-row';
    row.style.cssText = 'display:flex; gap:10px; margin-bottom:8px; align-items:center;';

    row.innerHTML = `
        <input type="text" class="form-input key-input" placeholder="属性名 (如: 品质)" value="${key}" style="flex:1;">
        <input type="text" class="form-input val-input" placeholder="属性值 (如: Epic)" value="${val}" style="flex:2;">
        <button class="btn btn-secondary" onclick="this.parentElement.remove()" style="color:#ff5555; padding: 0 8px;">×</button>
    `;
    container.appendChild(row);
}


function renderContentImagesGallery() {
    const gallery = document.getElementById('contentImagesGallery');
    let html = contentImages.map((url, idx) => {
        const filename = url.split('/').pop();
        return `
        <div class="gallery-item" title="${filename}">
            <img src="${url}" alt="Image ${idx + 1}" onclick="insertImageAtCursor('${url}')">
            <div class="gallery-actions">
                <button class="gallery-btn insert" onclick="insertImageAtCursor('${url}')" title="插入到正文">➕</button>
                <button class="gallery-btn remove" onclick="removeContentImage(${idx})" title="移除">×</button>
            </div>
            <div class="gallery-caption">${filename.substring(0, 12)}${filename.length > 12 ? '...' : ''}</div>
        </div>
    `}).join('');

    html += `
        <div class="add-image-btn" onclick="document.getElementById('contentImageInput').click()">
            <span style="font-size: 1.5rem;">+</span>
            <span style="font-size: 12px;">上传</span>
        </div>
        <div class="add-image-btn" onclick="openImageLibraryModal()" style="background: var(--bg-deep); border: 1px dashed var(--text-muted);">
             <span style="font-size: 1.5rem;">📂</span>
             <span style="font-size: 12px;">图库</span>
        </div>
    `;
    gallery.innerHTML = html;
}

function removeContentImage(index) {
    contentImages.splice(index, 1);
    renderContentImagesGallery();
}

function insertImageAtCursor(url) {
    const textarea = document.getElementById('editContent');
    const filename = url.split('/').pop();
    // 使用相对路径以便迁移
    const relativePath = url.includes('/wiki/assets/') ? url.split('/wiki/assets/')[1] : filename;
    const syntax = `![${filename}](${relativePath})`;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;

    textarea.value = text.substring(0, start) + syntax + text.substring(end);
    textarea.focus();
    const newCursorPos = start + syntax.length;
    textarea.selectionStart = textarea.selectionEnd = newCursorPos;

    showToast('图片已插入光标处');
}

// ===== EDITOR LINK PICKER =====
function toggleLinkPicker(btn) {
    const dropdown = document.getElementById('linkPickerDropdown');
    const isActive = dropdown.classList.contains('active');

    // Close others
    document.querySelectorAll('.editor-dropdown').forEach(d => d.classList.remove('active'));

    if (!isActive) {
        dropdown.classList.add('active');
        document.getElementById('linkPickerInput').focus();
        filterLinkPicker();
    } else {
        dropdown.classList.remove('active');
    }
}

function filterLinkPicker() {
    const query = document.getElementById('linkPickerInput').value.toLowerCase().trim();
    const list = document.getElementById('linkPickerList');

    let matches = Object.entries(allEntries);

    if (query) {
        matches = matches.filter(([id, entry]) =>
            ((entry.title || '').toLowerCase().includes(query) || id.toLowerCase().includes(query))
        );
    }

    matches = matches.slice(0, 10);

    if (matches.length === 0) {
        list.innerHTML = '<div style="padding: 8px; color: var(--text-muted); text-align: center;">无匹配</div>';
    } else {
        list.innerHTML = matches.map(([id, entry]) => `
            <div class="editor-dropdown-item" onclick="insertLink('${id}', '${entry.title || id}')">
                <span>${entry.icon || typeIcons[entry.type] || '📄'}</span>
                <span>${entry.title || id}</span>
            </div>
        `).join('');
    }
}

function insertLink(id, title) {
    const textarea = document.getElementById('editContent');
    const textToInsert = `[${title}](/wiki/${id})`;

    const startPos = textarea.selectionStart;
    const endPos = textarea.selectionEnd;
    const text = textarea.value;

    textarea.value = text.substring(0, startPos) + textToInsert + text.substring(endPos);

    const newPos = startPos + textToInsert.length;
    textarea.selectionStart = textarea.selectionEnd = newPos;
    textarea.focus();

    document.getElementById('linkPickerDropdown').classList.remove('active');
    document.getElementById('linkPickerInput').value = '';
}

// ===== RELATED ENTRY PICKER =====
function filterEntriesForPicker() {
    const query = document.getElementById('entryPickerInput').value.toLowerCase().trim();
    const dropdown = document.getElementById('entryPickerDropdown');
    const currentId = document.getElementById('editId').value;

    if (!query) {
        dropdown.classList.remove('active');
        return;
    }

    const matches = Object.entries(allEntries).filter(([id, entry]) =>
        id !== currentId &&
        !relatedEntries.includes(id) &&
        ((entry.title || '').toLowerCase().includes(query) || id.toLowerCase().includes(query))
    ).slice(0, 6);

    if (matches.length === 0) {
        dropdown.innerHTML = '<div style="padding: 12px; color: var(--text-muted); text-align: center;">未找到匹配词条</div>';
    } else {
        dropdown.innerHTML = matches.map(([id, entry]) => `
            <div class="entry-picker-item" onclick="addRelatedEntry('${id}')">
                <span class="entry-picker-item-icon">${entry.icon || typeIcons[entry.type] || '📄'}</span>
                <div class="entry-picker-item-info">
                    <div class="entry-picker-item-title">${entry.title || id}</div>
                    <div class="entry-picker-item-type">${typeNames[entry.type] || '未分类'}</div>
                </div>
            </div>
        `).join('');
    }
    dropdown.classList.add('active');
}

function addRelatedEntry(entryId) {
    if (!relatedEntries.includes(entryId)) {
        relatedEntries.push(entryId);
        renderRelatedEntries();
    }
    document.getElementById('entryPickerInput').value = '';
    document.getElementById('entryPickerDropdown').classList.remove('active');
}

function removeRelatedEntry(entryId) {
    relatedEntries = relatedEntries.filter(id => id !== entryId);
    renderRelatedEntries();
}

function renderRelatedEntries() {
    const list = document.getElementById('relatedEntriesList');
    if (relatedEntries.length === 0) {
        list.innerHTML = '<span style="color: var(--text-muted); font-size: 13px;">暂无相关词条</span>';
    } else {
        list.innerHTML = relatedEntries.map(id => {
            const entry = allEntries[id] || {};
            return `
                <div class="related-entry-tag">
                    <span>${entry.icon || '📄'}</span>
                    <span>${entry.title || id}</span>
                    <button class="related-entry-remove" onclick="removeRelatedEntry('${id}')">×</button>
                </div>
            `;
        }).join('');
    }
}

// ===== TABLE OF CONTENTS GENERATOR =====
function generateTableOfContents(html) {
    // Create temp container to parse HTML headings
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // Find h2 and h3
    const headings = tempDiv.querySelectorAll('h2, h3');
    if (headings.length < 2) return { toc: '', content: html }; // Don't show TOC for very short content

    let tocHtml = '<nav class="entry-toc"><div class="toc-title">目录</div><ul>';
    let hasContent = false;

    headings.forEach((h, i) => {
        const id = `heading-${i}`;
        // We modify the original html string by regex replacement later or modify the dom
        // Easier: Modify the DOM in tempDiv then output innerHTML
        h.id = id;

        const level = h.tagName === 'H3' ? 'toc-sub' : '';
        tocHtml += `<li class="${level}"><a href="javascript:void(0)" onclick="document.getElementById('${id}').scrollIntoView({behavior:'smooth'})">${h.textContent}</a></li>`;
        hasContent = true;
    });
    tocHtml += '</ul></nav>';

    return { toc: tocHtml, content: tempDiv.innerHTML };
}

// ===== DELETE FUNCTION =====
function confirmDeleteEntry() {
    const id = document.getElementById('editId').value;
    if (!id) return;

    if (confirm('确定要删除此词条吗？此操作无法撤销。')) {
        deleteEntry(id);
    }
}

async function deleteEntry(id) {
    try {
        const resp = await fetch('/api/wiki/' + id, {
            method: 'DELETE'
        });
        const data = await resp.json();

        if (data.success) {
            showToast('已删除词条');
            document.getElementById('editView').classList.remove('active');

            // Reload index
            await loadIndex();

            // Go back
            showCategoryList(currentEntry?.type || 'monster');
        } else {
            showToast('删除失败: ' + (data.message || ''), true);
        }
    } catch (e) {
        console.error(e);
        showToast('删除请求失败', true);
    }
}

// ===== IMAGE LIBRARY (SERVER ASSETS) =====
function openImageLibraryModal() {
    document.getElementById('imageLibraryModal').classList.add('active');
    loadLibraryImages();
}

function closeImageLibraryModal() {
    document.getElementById('imageLibraryModal').classList.remove('active');
}

async function loadLibraryImages() {
    const grid = document.getElementById('imageLibraryGrid');
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;">加载中...</div>';

    try {
        const resp = await fetch('/api/wiki/assets');
        const data = await resp.json();

        if (data.assets && data.assets.length > 0) {
            grid.innerHTML = data.assets.map(asset => `
                <div class="library-item" onclick="selectLibraryImage('${asset.url}')" style="cursor: pointer; position: relative; border-radius: 4px; overflow: hidden; aspect-ratio: 1;">
                    <img src="${asset.url}" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">
                    <div class="library-item-hover" style="position: absolute; inset: 0; background: rgba(0,0,0,0.5); opacity: 0; transition: opacity 0.2s; display: flex; align-items: center; justify-content: center; color: white;">+</div>
                </div>
            `).join('');

            // Add hover effect via JS or CSS? CSS is better but inline style loop above is messy.
            // Let's rely on simple CSS or just inline.
            // For simplicity in JS-only edit:
            grid.querySelectorAll('.library-item').forEach(el => {
                el.onmouseenter = () => el.querySelector('.library-item-hover').style.opacity = 1;
                el.onmouseleave = () => el.querySelector('.library-item-hover').style.opacity = 0;
            });

        } else {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">无需图片资源</div>';
        }
    } catch (e) {
        console.error(e);
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #ff5555; padding: 20px;">加载失败</div>';
    }
}

function selectLibraryImage(url) {
    if (!contentImages.includes(url)) {
        contentImages.push(url);
        renderContentImagesGallery();
        showToast('已添加图片到图库');
    } else {
        showToast('图片已在图库中');
    }
    closeImageLibraryModal();
}

// 全局点击关闭下拉框
document.addEventListener('click', (e) => {
    if (!e.target.closest('.editor-toolbar-btn') && !e.target.closest('.editor-dropdown')) {
        const lp = document.getElementById('linkPickerDropdown');
        if (lp) lp.classList.remove('active');
    }
    if (!e.target.closest('.entry-picker')) {
        const ep = document.getElementById('entryPickerDropdown');
        if (ep) ep.classList.remove('active');
    }
    // Modal Overlay click to close
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});
