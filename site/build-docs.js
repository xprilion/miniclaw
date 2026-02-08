const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Ensure site/docs directory exists
const docsDir = path.join(__dirname, 'docs');
if (!fs.existsSync(docsDir)) {
    fs.mkdirSync(docsDir, { recursive: true });
}

// Read all markdown files from the docs directory
const sourceDocsDir = path.join(__dirname, '..', 'docs');
const markdownFiles = fs.readdirSync(sourceDocsDir).filter(file => path.extname(file) === '.md');

// Generate documentation navigation
let docNavHtml = '<ul>\n';
let docLinks = [];

markdownFiles.forEach(file => {
    const fileName = path.basename(file, '.md');
    const title = fileName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    docNavHtml += `  <li><a href="#" data-doc="${fileName}">${title}</a></li>\n`;
    docLinks.push({ id: fileName, title: title, file: file });
    
    // Copy the markdown file to site/docs
    const sourcePath = path.join(sourceDocsDir, file);
    const destPath = path.join(docsDir, file);
    fs.copyFileSync(sourcePath, destPath);
});
docNavHtml += '</ul>';

// Write documentation navigation to a temporary file
fs.writeFileSync(path.join(__dirname, 'doc-nav.html'), docNavHtml);

console.log('Documentation navigation generated:');
console.log(docNavHtml);
console.log('\nDocument links:');
console.log(JSON.stringify(docLinks, null, 2));
console.log('\nDocumentation files copied to site/docs/');