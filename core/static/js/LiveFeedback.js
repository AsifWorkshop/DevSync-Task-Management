const activeSockets = {};
function toggleCommentSection(issueSlug) {
    const thread = document.getElementById(`commentThread-${issueSlug}`);
    const addCommentBox = document.getElementById(`addComment-${issueSlug}`);
    const toggleBtn = document.getElementById(`toggleCommentBtn-${issueSlug}`);

    thread.classList.toggle('collapsed');
    addCommentBox.classList.toggle('collapsed');

    const isExpanded = !thread.classList.contains('collapsed');
    toggleBtn.textContent = isExpanded ? 'Hide Feedbacks' : 'Show Feedbacks';

    if (isExpanded) {
        if (!activeSockets[issueSlug]) {
            connectIssueWebSocket(issueSlug);
        }
    } else {
        if (activeSockets[issueSlug]) {
            console.log(`Safely closed connection pool for slug lane: ${issueSlug}`);
            activeSockets[issueSlug].close();
            delete activeSockets[issueSlug];
        }
    }
}

function connectIssueWebSocket(issueSlug) {
    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsUrl = `${wsProtocol}${window.location.host}/ws/comments/${issueSlug}/`;

    console.log(`Connecting network socket for issue: ${issueSlug}`);
    const socket = new WebSocket(wsUrl);
    activeSockets[issueSlug] = socket;

    socket.onopen = function(e) {
        console.log(`Connection established safely for: ${issueSlug}`);
        document.getElementById(`commentsArea-${issueSlug}`).innerHTML = '';
        showNotification("Discussion thread synchronized.", "success");
    };

    socket.onmessage = function(e) {
        const payload = JSON.parse(e.data);

        if (payload.type === "initial_comments") {
            payload.comments.forEach(commentData => {
                renderSingleNode(issueSlug, commentData);
            });
            bindDynamicReplyListeners(issueSlug);
            return;
        }

        if (payload.type === "comment_broadcast") {
            renderSingleNode(issueSlug, payload);
            bindDynamicReplyListeners(issueSlug);
        }
    };

    socket.onerror = function(e) {
        console.error(`WebSocket error encountered on lane (${issueSlug}):`, e);
    };

    socket.onclose = function(e) {
        console.warn(`WebSocket connection closed for lane: ${issueSlug}`);
        if (activeSockets[issueSlug]) {
            delete activeSockets[issueSlug];
        }
    };
}

function renderSingleNode(issueSlug, data) {
    const nodeMarkup = buildCommentMarkupNode(issueSlug, data.id, data.parent_id, data.author, data.content, data.initials);

    if (!data.parent_id) {
        const targetContainer = document.getElementById(`commentsArea-${issueSlug}`);
        targetContainer.insertAdjacentHTML('beforeend', nodeMarkup);
    } else {
        const childrenContainer = document.getElementById(`children-${issueSlug}-${data.parent_id}`);
        if (childrenContainer) {
            childrenContainer.insertAdjacentHTML('beforeend', nodeMarkup);
        }
    }
}

function submitMainComment(issueSlug) {
    const input = document.getElementById(`mainCommentInput-${issueSlug}`);
    const text = input.value.trim();
    const socket = activeSockets[issueSlug];

    if (!text) {
        showNotification('Please write a comment before posting', 'error');
        return;
    }

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            'content': text,
            'parent_id': null
        }));
        input.value = '';
    }
}

function submitReply(issueSlug, parentId) {
    const replyForm = document.getElementById(`reply-form-${issueSlug}-${parentId}`);
    const textarea = replyForm.querySelector('textarea');
    const text = textarea.value.trim();
    const socket = activeSockets[issueSlug];

    if (!text) {
        showNotification('Please write a comment before posting', 'error');
        return;
    }

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            'content': text,
            'parent_id': parseInt(parentId)
        }));
        textarea.value = '';
        replyForm.classList.remove('active');
    }
}

function toggleCommentBranch(issueSlug, commentId, event) {
    event.stopPropagation();
    const childrenContainer = document.getElementById(`children-${issueSlug}-${commentId}`);
    const collapseBtn = event.target;

    if (childrenContainer) {
        childrenContainer.classList.toggle('collapsed-content');
        collapseBtn.textContent = childrenContainer.classList.contains('collapsed-content') ? '+' : '−';
    }
}

function toggleFullCommentBody(issueSlug, commentId, event) {
    if (event.target.closest('button') || event.target.closest('.reply-form') || event.target.closest('textarea')) {
        return;
    }

    const contentWrapper = document.getElementById(`content-wrapper-${issueSlug}-${commentId}`);
    const commentItem = document.getElementById(`comment-${issueSlug}-${commentId}`);
    const collapseBtn = commentItem.querySelector('.collapse-btn');

    if (contentWrapper) {
        contentWrapper.classList.toggle('collapsed-content');
        collapseBtn.textContent = contentWrapper.classList.contains('collapsed-content') ? '+' : '−';
    }
}

function bindDynamicReplyListeners(issueSlug) {
    const scopeContainer = document.getElementById(`commentThread-${issueSlug}`);
    scopeContainer.querySelectorAll('.reply-btn').forEach(btn => {
        btn.removeEventListener('click', handleReplyToggleClick);
        btn.addEventListener('click', handleReplyToggleClick);
    });
}

function handleReplyToggleClick(e) {
    e.stopPropagation();
    const issueSlug = this.dataset.slug;
    const parentId = this.dataset.parent;
    const replyForm = document.getElementById(`reply-form-${issueSlug}-${parentId}`);
    
    replyForm.classList.toggle('active');
    if (replyForm.classList.contains('active')) {
        replyForm.querySelector('textarea').focus();
    }
}

function cancelMainComment(issueSlug) {
    document.getElementById(`mainCommentInput-${issueSlug}`).value = '';
}

function cancelReply(issueSlug, parentId) {
    const replyForm = document.getElementById(`reply-form-${issueSlug}-${parentId}`);
    replyForm.classList.remove('active');
    replyForm.querySelector('textarea').value = '';
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification show notification-${type}`;
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function buildCommentMarkupNode(issueSlug, commentId, parentId, author, content, initials) {
    const colors = ['avatar-color-1', 'avatar-color-2', 'avatar-color-3', 'avatar-color-4', 'avatar-color-5'];
    const randomColor = colors[Math.floor(Math.random() * colors.length)];
    const nestedCommentClass = parentId ? 'nested-comment' : '';

    return `
        <div class="comment-item ${nestedCommentClass}" id="comment-${issueSlug}-${commentId}" onclick="toggleFullCommentBody('${issueSlug}', '${commentId}', event)">
            <button class="collapse-btn" onclick="toggleCommentBranch('${issueSlug}', '${commentId}', event)">−</button>
            <div class="comment-avatar ${randomColor}">${escapeHtml(initials)}</div>
            
            <div class="comment-content-wrapper" id="content-wrapper-${issueSlug}-${commentId}">
                <div class="comment-header">
                    <span class="comment-author">${escapeHtml(author)}</span>
                    <span class="comment-time">just now</span>
                </div>
                <div class="comment-body">${escapeHtml(content)}</div>
                <div class="comment-actions">
                    <button class="comment-action-btn reply-btn" data-slug="${issueSlug}" data-parent="${commentId}">Reply</button>
                </div>

                <div class="reply-form" id="reply-form-${issueSlug}-${commentId}">
                    <textarea class="reply-textarea" placeholder="Write a reply..."></textarea>
                    <div class="reply-actions">
                        <button class="btn-secondary" onclick="cancelReply('${issueSlug}', '${commentId}')">Cancel</button>
                        <button class="btn-primary" onclick="submitReply('${issueSlug}', '${commentId}')">Reply</button>
                    </div>
                </div>

                <div class="comment-children" id="children-${issueSlug}-${commentId}"></div>
            </div>
        </div>
    `;
}