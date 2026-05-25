document.addEventListener('DOMContentLoaded', () => {
    const taskSlug = document.body.getAttribute('data-task-slug');
    
    if (taskSlug) {
        initializeIssueSocket(taskSlug);
    } else {
        console.error("WebSocket Error: 'data-task-slug' attribute is empty on the body tag. Verify your board view context passes task_slug.");
    }

    setupDeleteButtons();
});

window.addEventListener('pageshow', (event) => {
    const isBackNavigation = event.persisted || 
        (window.performance && window.performance.getEntriesByType("navigation")?.type === "back_forward");
    
    if (isBackNavigation || sessionStorage.getItem('refresh_issue_board') === 'true') {
        sessionStorage.removeItem('refresh_issue_board'); 
        window.location.reload(); 
    }
});

function initializeIssueSocket(taskSlug) {
    const wsScheme = window.location.protocol === "https:" ? "wss://" : "ws://";
    const socketUrl = `${wsScheme}${window.location.host}/ws/issue/${taskSlug}/`;
    
    const issueSocket = new WebSocket(socketUrl);

    issueSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.action) {
            window.location.reload();
        }
    };

    issueSocket.onclose = function(e) {
        console.log('Issue WebSocket disconnected. Retrying connection structure...');
        setTimeout(() => initializeIssueSocket(taskSlug), 2000);
    };
}

function setupDeleteButtons() {
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
            if (!confirm('Are you sure you want to delete this issue?')) return;
            
            const issueSlug = button.getAttribute('data-issue_slug');
            const taskSlug = button.getAttribute('data-task_slug');
            const targetUrl = `/Issue/${issueSlug}/${taskSlug}/delete/`;

            try {
                const response = await fetch(targetUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    alert('Delete invocation failed: ' + (data.error || 'Server rejected request.'));
                }
            } catch (err) {
                console.error('Delete network failure:', err);
            }
        });
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}