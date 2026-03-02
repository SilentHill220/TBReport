let isAuthenticated = false;
let helpDocsTree = [];
let allDocsFlat = [];

marked.setOptions({
    highlight: function (code, lang) {
        // Simple highlight placeholder or use HLJS if available
        // Return code as is for now or wrap in spans if we added a highlighter library
        return code;
    },
    breaks: true
});

document.addEventListener('DOMContentLoaded', async () => {
    // Initial load
    const path = window.location.pathname;
    // Check if direct link to doc
    const currentDoc = (path.startsWith('/help/') && path.length > 6) ? path.substring(6) : null;

    await loadHelpDocs();

    if (currentDoc) {
        loadHelpDocEntry(currentDoc);
    } else {
        showAllHelpDocs();
    }

    // History handling
    window.addEventListener('popstate', (e) => {
        const path = window.location.pathname;
        if (path === '/help') {
            showAllHelpDocs();
        } else if (path.startsWith('/help/')) {
            loadHelpDocEntry(path.substring(6));
        }
    });

    // Handle global clicks
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-overlay')) {
            closeModal();
        }
    });
});

async function loadHelpDocs() {
    try {
        const resp = await fetch('/api/help-docs/index');
        if (resp.ok) {
            const data = await resp.json(); // Expect structured tree or raw list?
            // The API currently returns raw content of index.md? 
            // Or if we fix the backend, it might return JSON. 
            // Let's assume the previous logic: parse index.md content for now.

            // Wait, previous logic in docs.html was:
            // const text = await resp.text();
            // helpDocsTree = parseHelpDocsIndex(text);

            // Checking previous `docs.html` content...
            // It was `const text = await resp.text();`

            const text = await resp.text();
            helpDocsTree = parseHelpDocsIndex(text);
            renderHelpDocsList(helpDocsTree);

            // Flatten for search
            flattenDocs(helpDocsTree);

        } else {
            console.error("Failed to load help docs index");
            document.getElementById('sidebarContent').innerHTML = '<div style="padding:16px;color:var(--text-secondary);">加载失败</div>';
        }
    } catch (e) {
        console.error("Error loading help docs", e);
    }
}

function parseHelpDocsIndex(markdown) {
    const lines = markdown.split('\n');
    const tree = [];
    const stack = [{ level: 0, children: tree }];

    lines.forEach(line => {
        const match = line.match(/^(\s*)-\s+\[(.*?)\]\((.*?)\)/);
        if (match) {
            const indent = match[1].length;
            const title = match[2];
            let link = match[3]; // e.g., "manual/overview.md"

            // Normalize link
            link = link.replace(/^\//, '').replace(/\.md$/, '');

            const node = { title, link, children: [] };

            // Determine level (assume 2 spaces = 1 level)
            const level = indent / 2 + 1;

            while (stack.length > level) stack.pop();

            // Add to parent
            const parent = stack[stack.length - 1];
            parent.children.push(node);

            stack.push({ level: level, children: node.children });
        } else {
            // Maybe a category header without link? "- Category"
            const catMatch = line.match(/^(\s*)-\s+(.*)/);
            if (catMatch && !line.includes('](')) {
                const indent = catMatch[1].length;
                const title = catMatch[2];
                const node = { title, link: null, children: [] };

                const level = indent / 2 + 1;
                while (stack.length > level) stack.pop();

                const parent = stack[stack.length - 1];
                parent.children.push(node);

                stack.push({ level: level, children: node.children });
            }
        }
    });

    return tree;
}

function flattenDocs(tree) {
    allDocsFlat = [];
    function recurse(nodes) {
        nodes.forEach(node => {
            if (node.link) allDocsFlat.push(node);
            if (node.children) recurse(node.children);
        });
    }
    recurse(tree);
}

function renderHelpDocsList(tree, container = null) {
    const target = container || document.getElementById('sidebarContent');
    if (!container) target.innerHTML = '';

    tree.forEach(node => {
        if (node.children && node.children.length > 0) {
            // Category
            const div = document.createElement('div');
            // Check if it should be a group or just loose items

            // Header
            const header = document.createElement('div');
            header.className = 'tree-category';
            header.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
                <span>${node.title}</span>
            `;
            header.onclick = () => {
                header.classList.toggle('collapsed');
            };

            const group = document.createElement('div');
            group.className = 'tree-group';

            div.appendChild(header);
            div.appendChild(group);
            target.appendChild(div);

            renderHelpDocsList(node.children, group);
        } else {
            // Leaf item
            const item = document.createElement('a');
            item.className = 'tree-item';
            if (container) item.classList.add('tree-sub-item'); // Indent sub items
            // Assuming 2 levels max for simplicity in CSS, or class handles padding
            // CSS `tree-item` has left padding, nesting usually done via container padding
            // Lets stick to basic structure

            item.textContent = node.title;
            // Store link
            item.dataset.link = node.link;

            item.onclick = () => {
                // Highlight active
                document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');

                if (node.link) {
                    loadHelpDocEntry(node.link);
                }
            };

            target.appendChild(item);
        }
    });
}

function renderHelpDocsListOld(tree) {
    // Legacy function replaced by the one above which handles DOM elements better than raw HTML strings to avoid malformed tags
    // Keeping logic concept: categories vs items
}


async function loadHelpDocEntry(docPath) {
    // Logic to fetch doc content
    // API: /api/help-docs/<doc_name> e.g. /api/help-docs/manual/overview.md

    // Scroll to top
    document.querySelector('.docs-main').scrollTop = 0;

    const container = document.getElementById('mainContent');
    container.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-secondary);">加载文档中...</div>';

    // Update URL
    if (window.location.pathname !== '/help/' + docPath) {
        history.pushState({ doc: docPath }, '', '/help/' + docPath);
    }

    try {
        // Ensure extension
        const fetchPath = docPath.endsWith('.md') ? docPath : docPath + '.md';
        const resp = await fetch(`/api/help-docs/${fetchPath}`);

        if (resp.ok) {
            const text = await resp.text();

            // Pre-process local images: ![alt](./images/foo.png) -> /api/help-docs/images/foo.png? or similar?
            // Actually usually served via static.
            // Let's assume images are handled or relative links work if base is set?
            // Since we serve Markdown content dynamically, relative links might break if not handled.
            // Simple replace for known pattern:
            const processed = text.replace(/!\[(.*?)\]\(\.\/images\/(.*?)\)/g, '![$1](/help-docs/assets/$2)');

            container.innerHTML = `
                <div class="markdown-body">
                    ${marked.parse(processed)}
                </div>
            `;

            // Highlight sidebar item
            // docPath might differ slightly from node.link
            document.querySelectorAll('.tree-item').forEach(el => {
                if (el.dataset.link === docPath) el.classList.add('active');
                else el.classList.remove('active');
            });

        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <h2>文档加载失败</h2>
                    <p>找不到文档: ${docPath}</p>
                    <button class="login-btn" onclick="showAllHelpDocs()" style="margin-top:20px;">返回目录</button>
                </div>
            `;
        }
    } catch (e) {
        console.error(e);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <h2>发生错误</h2>
                <p>${e.message}</p>
            </div>
        `;
    }
}

function showAllHelpDocs() {
    const container = document.getElementById('mainContent');

    if (allDocsFlat.length === 0) {
        showEmptyHelpDoc();
        return;
    }

    // Render grid of all top level or important docs
    // Use allDocsFlat for now

    const html = `
        <div style="margin-bottom:32px;">
            <h1 style="font-size:2rem; color:var(--text-primary); margin-bottom:12px;">帮助文档中心</h1>
            <p style="color:var(--text-secondary);">选择左侧栏目或直接浏览下方文档。</p>
        </div>
        <div class="help-doc-grid">
            ${allDocsFlat.map(doc => `
                <div class="help-doc-card" onclick="loadHelpDocEntry('${doc.link}')">
                    <div class="help-doc-icon">📄</div>
                    <div class="help-doc-title">${doc.title}</div>
                    <div class="help-doc-desc">点击查看详细内容...</div>
                </div>
            `).join('')}
        </div>
     `;

    container.innerHTML = html;

    // Reset sidebar active
    document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('active'));

    if (window.location.pathname !== '/help') {
        history.pushState(null, '', '/help');
    }
}

function showEmptyHelpDoc() {
    const container = document.getElementById('mainContent');
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">📚</div>
            <h2>欢迎使用帮助文档</h2>
            <p>请在左侧选择要查看的文档章节。</p>
        </div>
    `;
}


function handleSearch() {
    const query = document.getElementById('searchInput').value.toLowerCase();

    // Filter sidebar?
    // Or drop down?
    // Let's filter sidebar visibility

    const items = document.querySelectorAll('.tree-item');
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(query)) {
            item.style.display = 'block';
            // expand parents
            let parent = item.parentElement;
            while (parent && !parent.classList.contains('docs-sidebar')) {
                if (parent.style.display === 'none') parent.style.display = 'block';
                // If it's a group, uncollapse category?
                if (parent.classList.contains('tree-group')) {
                    const header = parent.previousElementSibling;
                    if (header && header.classList.contains('tree-category')) {
                        header.classList.remove('collapsed');
                    }
                }
                parent = parent.parentElement;
            }
        } else {
            item.style.display = 'none';
        }
    });
}

// Auth mock
function requestLogin() {
    if (isAuthenticated) {
        alert("已登录");
    } else {
        document.getElementById('loginModal').classList.add('active');
    }
}

function verifyCode() {
    const code = document.getElementById('verifyCode').value;
    if (code === '666666') {
        isAuthenticated = true;
        closeModal();
        const btn = document.querySelector('.header-actions .login-btn');
        if (btn) btn.textContent = '已登录';
    } else {
        alert('验证码错误');
    }
}

function closeModal() {
    document.getElementById('loginModal').classList.remove('active');
    document.getElementById('verifyCode').value = '';
}
