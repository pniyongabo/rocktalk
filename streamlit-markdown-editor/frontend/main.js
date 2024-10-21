let editor;
const turndownService = new TurndownService({
    headingStyle: 'atx',
    codeBlockStyle: 'fenced',
    emDelimiter: '*',
    strongDelimiter: '**',
    bulletListMarker: '-',
    linkStyle: 'inlined',
    linkReferenceStyle: 'full'
});

function preprocessHtml(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    doc.querySelectorAll('span').forEach(span => {
        const style = span.getAttribute('style') || '';
        if (style.includes('font-weight:700') || style.includes('font-weight:bold')) {
            const strong = doc.createElement('strong');
            strong.innerHTML = span.innerHTML;
            span.parentNode.replaceChild(strong, span);
        } else if (style.includes('font-style:italic')) {
            const em = doc.createElement('em');
            em.innerHTML = span.innerHTML;
            span.parentNode.replaceChild(em, span);
        }
    });

    return doc.body.innerHTML;
}

// Custom rule for lists
turndownService.addRule('lists', {
    filter: ['ul', 'ol'],
    replacement: function (content, node) {
        const isOrdered = node.nodeName === 'OL';
        const listItems = content.trim().split('\n');
        return listItems.map((item, index) => {
            const prefix = isOrdered ? `${index + 1}. ` : '- ';
            return prefix + item.trim();
        }).join('\n') + '\n\n';
    }
});

// Custom rule for list items
turndownService.addRule('listItems', {
    filter: 'li',
    replacement: function (content, node, options) {
        content = content.trim();
        let prefix = '';
        
        // Calculate the nesting level
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

function sendValue(value) {
    console.log('Sending value to Streamlit:', value);
    Streamlit.setComponentValue(value);
}

function initializeEditor() {
    console.log('Initializing editor');
    tinymce.init({
        selector: '#editor-container',
        height: '100%',
        menubar: false,
        plugins: [
            'advlist autolink lists link image charmap print preview anchor',
            'searchreplace visualblocks code fullscreen',
            'insertdatetime media table code help wordcount'
        ],
        toolbar: 'undo redo | formatselect | ' +
            'bold italic backcolor | alignleft aligncenter ' +
            'alignright alignjustify | bullist numlist outdent indent | ' +
            'removeformat | image | help',
        content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:14px }',
        paste_data_images: true,
        paste_preprocess: function(plugin, args) {
            args.content = preprocessHtml(args.content);
        },
        setup: function(ed) {
            editor = ed;
            ed.on('input change', function(e) {
                console.log('Editor content changed');
                let content = ed.getContent();
                console.log('Raw content:', content);
                let markdown = turndownService.turndown(content);
                console.log('Converted to Markdown:', markdown);
                sendValue(markdown);
            });
        },
    });
}

function onRender(event) {
    console.log('Render event received');
    const {theme} = event.detail.args;
    if (theme) {
        document.body.style.color = theme.textColor;
        document.body.style.backgroundColor = theme.backgroundColor;
    }
}

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', (event) => {
    console.log('DOM fully loaded');
    initializeEditor();
    Streamlit.setComponentReady();
});

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
