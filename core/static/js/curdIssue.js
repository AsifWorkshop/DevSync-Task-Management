document.addEventListener('DOMContentLoaded', () => {
    const issueForm = document.getElementById('issueForm');

    if (issueForm) {
        issueForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const issueSlug = issueForm.getAttribute('data-issue-slug');
            const taskSlug = issueForm.getAttribute('data-task-slug');
            const action = issueForm.getAttribute('data-action');

            const titleValue = document.getElementById('title').value.trim();
            const descriptionValue = document.getElementById('description').value;
            const targetUrl = `/Issue/${issueSlug}/${taskSlug}/${action}/`;

            try {
                const response = await fetch(targetUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        'title': titleValue,
                        'description': descriptionValue
                    })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    sessionStorage.setItem('refresh_issue_board', 'true');
                    window.history.back();
                } else {
                    alert('Action Failed: ' + (data.error || 'Unknown application error occurred.'));
                }

            } catch (error) {
                console.error('Fetch operation fault:', error);
                alert('A network communication error occurred.');
            }
        });
    }
});

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