// Theme toggle functionality
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    const themeIcon = themeToggle.querySelector('.theme-icon');
    
    // Check for saved theme preference or respect OS preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light');
    
    // Apply initial theme
    if (initialTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeIcon.textContent = '☀️';
    } else {
        themeIcon.textContent = '🌙';
    }
    
    // Toggle theme on button click
    themeToggle.addEventListener('click', () => {
        const isDarkMode = document.body.classList.toggle('dark-mode');
        
        // Update icon and save preference
        if (isDarkMode) {
            themeIcon.textContent = '☀️';
            localStorage.setItem('theme', 'dark');
        } else {
            themeIcon.textContent = '🌙';
            localStorage.setItem('theme', 'light');
        }
    });
}

// Documentation navigation and content loading (uses docs from docs/*.md built by CI)
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();

    const docFiles = window.DOCS_LIST || [
        { id: 'getting_started', title: 'Getting Started' },
        { id: 'setup', title: 'Setup' },
        { id: 'cli', title: 'CLI Reference' },
        { id: 'architecture', title: 'Architecture' },
        { id: 'deployment', title: 'Deployment' },
        { id: 'api', title: 'API Docs' },
        { id: 'enhancement_summary', title: 'Enhancement Summary' },
        { id: 'cli_styling', title: 'CLI Styling' }
    ];

    const docNav = document.getElementById('doc-navigation');
    if (docNav) {
        let navHTML = '<ul>';
        docFiles.forEach(doc => {
            navHTML += `<li><a href="#" data-doc="${doc.id}">${doc.title}</a></li>`;
        });
        navHTML += '</ul>';
        docNav.innerHTML = navHTML;

        docNav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const docId = this.getAttribute('data-doc');
                loadDocumentation(docId);
                docNav.querySelectorAll('a').forEach(a => a.classList.remove('active'));
                this.classList.add('active');
            });
        });

        if (docFiles.length > 0) {
            loadDocumentation(docFiles[0].id);
            docNav.querySelector('a').classList.add('active');
        }
    }

    function loadDocumentation(docId) {
        const docContent = document.getElementById('doc-content');
        if (!docContent) return;

        docContent.innerHTML = '<p class="doc-loading">Loading…</p>';

        fetch(`docs/${docId}.html`)
            .then(function(res) {
                if (!res.ok) throw new Error('Not found');
                return res.text();
            })
            .then(function(html) {
                docContent.innerHTML = html;
            })
            .catch(function() {
                docContent.innerHTML = '<p>Documentation not available here. On the published site, docs are built from the <code>docs/</code> folder.</p>';
            });
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
});