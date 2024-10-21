// Initialize editor variable to store the TinyMCE editor instance
let editor;

// Initialize TurndownService with custom settings for Markdown conversion
const turndownService = new TurndownService({
    headingStyle: 'atx',           // Use # style headings
    codeBlockStyle: 'fenced',      // Use ``` for code blocks
    emDelimiter: '*',              // Use * for italics
    strongDelimiter: '**',         // Use ** for bold
    bulletListMarker: '-',         // Use - for unordered lists
    linkStyle: 'inlined',          // Use [text](url) style links
    linkReferenceStyle: 'full'     // Use [text][id] with full reference links
});

// Custom rule to handle inline styles for bold and italic
turndownService.addRule('inlineStyles', {
   filter: function (node, options) {
       return (
           node.nodeName === 'SPAN' &&
           node.style &&
           (node.style.fontWeight === 'bold' || node.style.fontWeight === '700' ||
            node.style.fontStyle === 'italic')
       );
   },
   replacement: function (content, node, options) {
       const isBold = node.style.fontWeight === 'bold' || node.style.fontWeight === '700';
       const isItalic = node.style.fontStyle === 'italic';
       if (isBold && isItalic) {
           return `***${content}***`;
       } else if (isBold) {
           return `**${content}**`;
       } else if (isItalic) {
           return `*${content}*`;
       }
       return content;
   }
});

// Custom rule for handling lists (both ordered and unordered)
turndownService.addRule('lists', {
    filter: ['ul', 'ol'],
    replacement: function (content, node) {
        const isOrdered = node.nodeName === 'OL';
        const listItems = content.trim().split('\n');
        return listItems.map((item, index) => {
            const prefix = isOrdered ? `${index + 1}. ` : '- ';
            return prefix + item.trim();
        }).join('\n') + '\n\n';  // Add extra newline for spacing between lists
    }
});

// Custom rule for handling list items with proper indentation
turndownService.addRule('listItems', {
    filter: 'li',
    replacement: function (content, node) {
        content = content.trim();
        let prefix = '';
        
        // Calculate the nesting level of the list item
        let level = 0;
        let parent = node.parentNode;
        while (parent && (parent.nodeName === 'UL' || parent.nodeName === 'OL')) {
            level++;
            parent = parent.parentNode;
        }
        
        // Add indentation based on nesting level
        prefix = '  '.repeat(level - 1);
        
        return prefix + content + '\n';
    }
});

// Function to send the converted Markdown value to Streamlit
function sendValue(value) {
    console.log('Sending value to Streamlit:', value);
    Streamlit.setComponentValue(value);
}

// Function to initialize the TinyMCE editor
function initializeEditor() {
    console.log('Initializing editor');
    tinymce.init({
        // Select the editor container
        selector: '#editor-container',
        // Set editor height
        height: '100%',
        // Disable menu bar
        menubar: false,
        // Enable necessary plugins
        plugins: [
            'advlist autolink lists link image charmap print preview anchor',
            'searchreplace visualblocks code fullscreen',
            'insertdatetime media table code help wordcount'
        ],
        // Configure toolbar
        toolbar: 'undo redo | formatselect | ' +
            'bold italic backcolor | alignleft aligncenter ' +
            'alignright alignjustify | bullist numlist outdent indent | ' +
            'removeformat | image | help',
        // Set content style
        content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:14px }',
        // Allow pasting of images
        paste_data_images: true,
        // Setup editor events
        setup: function(ed) {
            editor = ed;
            // Add listener for input and change events
            ed.on('input change', debounce(function(e) {
                console.log('Editor content changed');
                let content = ed.getContent();
                console.log('Raw content:', content);
                // Convert HTML to Markdown
                let markdown = turndownService.turndown(content);
                console.log('Converted to Markdown:', markdown);
                // Send Markdown to Streamlit
                sendValue(markdown);
            }, 300)); // Debounce for 300ms to reduce unnecessary conversions
        },
    });
}

// Debounce function to limit the rate of function calls
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Function to handle render event from Streamlit
function onRender(event) {
    console.log('Render event received');
    const {theme} = event.detail.args;
    // Apply theme if provided
    if (theme) {
        applyTheme(theme);
    }
}

// Function to apply theme to the editor
function applyTheme(theme) {
    document.body.style.color = theme.textColor;
    document.body.style.backgroundColor = theme.backgroundColor;
    // You can add more theme-related styling here if needed
}

// Wait for the DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', (event) => {
    console.log('DOM fully loaded');
    initializeEditor();
    Streamlit.setComponentReady();
});

// Add listener for Streamlit render event
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
