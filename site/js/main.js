// Documentation navigation and content loading
document.addEventListener('DOMContentLoaded', function() {
    // DOCS_DATA_PLACEHOLDER
    // Sample documentation files - in a real implementation, these would be generated from the docs folder
    const docFiles = [
        { id: 'getting_started', title: 'Getting Started', file: 'getting_started.md' },
        { id: 'setup', title: 'Setup Guide', file: 'setup.md' },
        { id: 'cli', title: 'CLI Reference', file: 'cli.md' },
        { id: 'architecture', title: 'Architecture', file: 'architecture.md' },
        { id: 'deployment', title: 'Deployment', file: 'deployment.md' },
        { id: 'api', title: 'API Docs', file: 'api.md' },
        { id: 'enhancement_summary', title: 'Enhancements', file: 'enhancement_summary.md' },
        { id: 'cli_styling', title: 'CLI Styling', file: 'cli_styling.md' }
    ];

    // Generate documentation navigation
    const docNav = document.getElementById('doc-navigation');
    if (docNav) {
        let navHTML = '<ul>';
        docFiles.forEach(doc => {
            navHTML += `<li><a href="#" data-doc="${doc.id}">${doc.title}</a></li>`;
        });
        navHTML += '</ul>';
        docNav.innerHTML = navHTML;

        // Add click handlers for documentation links
        docNav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const docId = this.getAttribute('data-doc');
                loadDocumentation(docId);
                
                // Update active state
                docNav.querySelectorAll('a').forEach(a => a.classList.remove('active'));
                this.classList.add('active');
            });
        });

        // Load the first documentation by default
        if (docFiles.length > 0) {
            loadDocumentation(docFiles[0].id);
            docNav.querySelector('a').classList.add('active');
        }
    }

    // Function to load documentation content
    function loadDocumentation(docId) {
        const docContent = document.getElementById('doc-content');
        if (!docContent) return;

        // In a real implementation, this would fetch and convert Markdown to HTML
        // For now, we'll simulate with sample content
        const doc = docFiles.find(d => d.id === docId);
        if (doc) {
            docContent.innerHTML = `
                <h2>${doc.title}</h2>
                <p>Documentation content for ${doc.title} would be displayed here.</p>
                <p>In the live site, this content would be automatically generated from <code>docs/${doc.file}</code>.</p>
                <p>The GitHub Action workflow automatically compiles all Markdown files in the docs folder into this documentation section, ensuring it's always up-to-date with the latest changes.</p>
            `;
        } else {
            docContent.innerHTML = '<p>Documentation not found.</p>';
        }
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