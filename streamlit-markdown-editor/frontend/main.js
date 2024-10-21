const pasteArea = document.getElementById('paste-area');
const turndownService = new TurndownService();
const showdownConverter = new showdown.Converter();

function sendValue(value) {
    Streamlit.setComponentValue(value);
}

function updateMarkdown() {
    const html = pasteArea.innerHTML;
    const markdown = turndownService.turndown(html);
    console.log("Sending markdown:", markdown);  // Debug log
    sendValue(markdown);
}

pasteArea.addEventListener('paste', function(e) {
    e.preventDefault();
    let html = e.clipboardData.getData('text/html');
    if (!html) {
        html = e.clipboardData.getData('text/plain');
    }
    console.log("Pasted content:", html);  // Debug log
    
    // Convert HTML to Markdown
    const markdown = turndownService.turndown(html);
    
    // Convert Markdown back to HTML for display
    const renderedHtml = showdownConverter.makeHtml(markdown);
    
    // Set the rendered HTML content in the paste area
    pasteArea.innerHTML = renderedHtml;
    
    updateMarkdown();
});

pasteArea.addEventListener('input', updateMarkdown);

function onRender(event) {
    console.log("Render event received", event);  // Debug log
    const {height} = event.detail.args;
    pasteArea.style.height = `${height - 10}px`;  // Subtract 10px for padding
    // You can add any initialization logic here if needed
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
