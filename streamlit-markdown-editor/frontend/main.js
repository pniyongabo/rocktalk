const pasteArea = document.getElementById('paste-area');
const turndownService = new TurndownService({
    headingStyle: 'atx',
    codeBlockStyle: 'fenced',
    emDelimiter: '*',
    strongDelimiter: '**'
});

// Custom rule to handle bold and italic
turndownService.addRule('boldAndItalic', {
    filter: ['strong', 'b', 'em', 'i'],
    replacement: function (content, node, options) {
        if (node.nodeName === 'STRONG' || node.nodeName === 'B') {
            return node.parentNode.nodeName === 'EM' || node.parentNode.nodeName === 'I'
                ? `***${content}***`  // Bold and italic
                : `**${content}**`;   // Just bold
        }
        if (node.nodeName === 'EM' || node.nodeName === 'I') {
            return node.parentNode.nodeName === 'STRONG' || node.parentNode.nodeName === 'B'
                ? `***${content}***`  // Bold and italic
                : `*${content}*`;     // Just italic
        }
    }
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

function sendValue(value) {
    Streamlit.setComponentValue(value);
}

function updateMarkdown() {
    const html = pasteArea.innerHTML;
    const markdown = turndownService.turndown(html);
    console.log("Sending markdown:", markdown);
    sendValue(markdown);
}

pasteArea.addEventListener('paste', function(e) {
    e.preventDefault();
    
    let paste = (e.clipboardData || window.clipboardData).getData('text/html');
    
    if (!paste) {
        paste = (e.clipboardData || window.clipboardData).getData('text/plain');
        paste = paste.replace(/\n/g, '<br>');
    }
    
    console.log("Pasted content:", paste);
    
    const sanitizedHtml = DOMPurify.sanitize(paste);
    
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        range.deleteContents();
        const fragment = range.createContextualFragment(sanitizedHtml);
        range.insertNode(fragment);
    } else {
        pasteArea.innerHTML += sanitizedHtml;
    }
    
    updateMarkdown();
});

pasteArea.addEventListener('input', updateMarkdown);

function onRender(event) {
    const {theme} = event.detail.args;
    if (theme) {
        pasteArea.style.color = theme.textColor;
        pasteArea.style.backgroundColor = theme.backgroundColor;
    }
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);

// Initialize the component
updateMarkdown();
Streamlit.setComponentReady();