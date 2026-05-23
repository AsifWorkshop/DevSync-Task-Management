let currentTaskSocket = null;
let currentUserRole = 'worker'; 
let new_workspace_slug = "dummy";
const subtaskDebounceTimers = {}; 


function normalizeLaneKey(columnValue) {
    if (!columnValue) return 'todo';

    const normalized = String(columnValue).toLowerCase().replace(/[^a-z]/g, '');

    if (normalized.includes('todo')) return 'todo';
    if (normalized.includes('progress')) return 'progress';
    if (normalized.includes('review')) return 'review';
    if (normalized.includes('issue')) return 'issue';
    if (normalized.includes('done') || normalized.includes('complete')) return 'done';

    return 'todo'; 
}

const COLUMNS_CONFIG = {
    todo: { title: "To Do" },
    progress: { title: "In Progress" },
    review: { title: "Review" },
    issue: { title: "Issue Found" },
    done: { title: "Complete" }
};

let columnsOrder = ['todo', 'progress', 'review', 'issue', 'done'];


function isMoveAllowed(sourceColKey, targetColKey, userRole) {
    if (!userRole) return false;

    const role = String(userRole).toUpperCase();
    const sourceIdx = columnsOrder.indexOf(sourceColKey);
    const targetIdx = columnsOrder.indexOf(targetColKey);

    if (sourceIdx === -1 || targetIdx === -1) return false;
    if (sourceIdx === targetIdx) return false;

    if (role === 'ADMIN') return true;

    if (role === 'WORKER') {
        return (sourceColKey === 'todo' && targetColKey === 'progress') ||
            (sourceColKey === 'progress' && targetColKey === 'review') ||
            (sourceColKey === 'issue' && targetColKey === 'progress') ||
            (sourceColKey === 'issue' && targetColKey === 'todo');
    }

    if (role === 'REVIEWER') {
        return (sourceColKey === 'review' && (targetColKey === 'issue' || targetColKey === 'done'));
    }

    return false;
}

window.toggleSection = function (label, listId) {
    const list = document.getElementById(listId);
    if (list) list.classList.toggle('open');
    if (label) label.classList.toggle('open');
};

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>]/g, function (m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function updateAllCounters() {
    document.querySelectorAll('.column').forEach(col => {
        const cardsContainer = col.querySelector('.cards');
        const countSpan = col.querySelector('.col-count');
        if (countSpan && cardsContainer) {
            countSpan.innerText = cardsContainer.children.length;
        }
    });
}

async function apiCreateSubtask(taskSlug, titleText, onResponseSuccess) {
    console.log(`📡 Initializing POST request for subtask addition under task: ${taskSlug}`);

    try {
        const response = await fetch(`/TaskCard/${taskSlug}/addsubtask/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                'title': titleText,
                'type': 'PRIVATE',
                'workspace_slug': new_workspace_slug,
                'role': currentUserRole,
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Subtask Added Securely:', data);

        if (onResponseSuccess) onResponseSuccess(data);

    } catch (err) {
        console.error("processing failure:", err);
    }
}

async function apiUpdateSubtaskStatus(taskSlug, subtaskId, isChecked) {
    console.log(`📡 Syncing status to database... Subtask ID: ${subtaskId} | Checked: ${isChecked}`);

    try {
        const response = await fetch(`/TaskCard/${taskSlug}/toggle_subtask/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                'subtask_id': subtaskId,
                'checked': isChecked,
                'workspace_slug': new_workspace_slug,
                'role': currentUserRole,
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Subtask toggle sync complete:', data);

    } catch (err) {
        console.error("Subtask status update failure:", err);
    }
}

async function apiUpdateCardMovement(taskSlug, targetColumn) {
    console.log(`Initializing POST request for workflow status update. Card: ${taskSlug} Column: ${targetColumn}`);

    try {
        const response = await fetch(`/TaskCard/${taskSlug}/task_movement/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                'status': targetColumn.toUpperCase(),
                'workspace_slug': new_workspace_slug,
                'role': currentUserRole,
            })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        } else {
            const data = await response.json();
            console.log('Workflow sync completed:', data);
        }
    }
    catch (err) {
        console.error("Movement processing failure:", err);
    }
}

function apiFetchWorkspaceMetadata(workspaceSlug) {
    console.log(`Initializing GET request framework tracking analytics parameters for workspace: ${workspaceSlug}`);
}


function buildEmptyBoardSkeleton(role = 'worker') {
    const boardContainer = document.getElementById('kanbanBoard');
    if (!boardContainer) return;

    const normalizedRole = String(role).toLowerCase().trim();
    if (normalizedRole === 'reviewer') {
        columnsOrder = ['review', 'issue', 'done'];
    } else {
        columnsOrder = ['todo', 'progress', 'review', 'issue', 'done'];
    }

    boardContainer.innerHTML = ''; 

    columnsOrder.forEach(colKey => {
        const colDiv = document.createElement('div');
        colDiv.className = 'column';
        colDiv.setAttribute('data-col', colKey);
        colDiv.innerHTML = `
            <div class="col-header">
                <div class="col-title-wrap">
                    <span class="col-dot"></span>
                    <span class="col-title">${COLUMNS_CONFIG[colKey].title}</span>
                    <span class="col-count">0</span>
                </div>
                <button class="col-add" title="Add task">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                </button>
            </div>
            <div class="cards"></div>
        `;
        boardContainer.appendChild(colDiv);
    });

    if (typeof Sortable !== 'undefined') {
        document.querySelectorAll('.cards').forEach(container => {
            new Sortable(container, {
                group: { name: 'kanban', pull: true, revertClone: false, put: true },
                animation: 200,
                ghostClass: 'sortable-ghost',

                onMove: function (evt) {
                    const sourceColKey = evt.from.closest('.column').getAttribute('data-col');
                    const targetColKey = evt.to.closest('.column').getAttribute('data-col');

                    return isMoveAllowed(sourceColKey, targetColKey, currentUserRole);
                },

                onEnd: function (evt) {
                    document.querySelectorAll('.task-card').forEach(card => initCardInteractions(card));
                    updateAllCounters();

                    if (evt.from !== evt.to) {
                        const cardElement = evt.item;
                        const taskSlug = cardElement.getAttribute('data-task-slug');
                        const targetColKey = evt.to.closest('.column').getAttribute('data-col');

                        apiUpdateCardMovement(taskSlug, targetColKey);
                    }
                }
            });
        });
    }

    document.querySelectorAll('.col-add').forEach(btn => {
        btn.addEventListener('click', () => alert('Add new task to this column (demo modal link)'));
    });
}

function processAndAppendCard(taskPayload) {
    if (!taskPayload) return;

    const targetLaneKey = normalizeLaneKey(taskPayload.column || taskPayload.status);

    const columnCardsContainer = document.querySelector(`.column[data-col="${targetLaneKey}"] .cards`);
    if (!columnCardsContainer) {
        console.log(`Task ignored on UI: Column "${targetLaneKey}" is omitted for this user role.`);
        return;
    }

    const taskSlug = taskPayload.task_slug || taskPayload.slug || taskPayload.id || '';
    if (taskSlug && columnCardsContainer.querySelector(`[data-task-slug="${taskSlug}"]`)) return;

    let extractedSubtasks = [];
    if (Array.isArray(taskPayload.subtasks)) {
        extractedSubtasks = taskPayload.subtasks.map(s => ({
            id: s.id || s.pk || s.subtask_id || '', 
            text: s.text || s.title || '',
            checked: s.checked === true || s.checked === 'True'
        }));
    } else {
        const privateSubs = Array.isArray(taskPayload.subtask_private) ? taskPayload.subtask_private : [];
        const publicSubs = Array.isArray(taskPayload.subtask_public) ? taskPayload.subtask_public : [];
        extractedSubtasks = [
            ...privateSubs.map(s => ({ id: s.id || s.pk || s.subtask_id || '', text: s.title || s.text || '', checked: s.checked === 'True' || s.checked === true })),
            ...publicSubs.map(s => ({ id: s.id || s.pk || s.subtask_id || '', text: s.title || s.text || '', checked: s.checked === 'True' || s.checked === true }))
        ];
    }

    const cardData = {
        task_slug: taskSlug,
        title: taskPayload.title || 'Untitled Task',
        description: taskPayload.description || '',
        priority: String(taskPayload.priority || 'medium').toLowerCase(),
        priorityLabel: taskPayload.priority || 'Medium',
        issue_count: taskPayload.issue_count || 0,
        dueDate: taskPayload.expires_at ? new Date(taskPayload.expires_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : (taskPayload.dueDate || 'No due date'),
        attachments: taskPayload.attachments_count || taskPayload.attachments || 0,
        comments: taskPayload.feedback_count || taskPayload.comments || taskPayload.comments_count || 0,
        subtasks: extractedSubtasks
    };

    const newCardEl = createRichTaskCard(cardData);
    columnCardsContainer.appendChild(newCardEl);
    initCardInteractions(newCardEl);
}

function createRichTaskCard(data) {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.setAttribute('data-task-slug', data.task_slug || '');
    card.innerHTML = `
        <div class="card-header-flex">
            <span class="card-priority priority-${data.priority}">${escapeHtml(data.priorityLabel)}</span>
            <a href="#"><span class="card-issue-badge">issue :${escapeHtml(data.issue_count)}</span></a>
        </div>
        <h3 class="card-main-title">${escapeHtml(data.title)}</h3>
        <div class="card-description-wrap">
            <p class="card-description-text truncate">${escapeHtml(data.description)}</p>
            <button class="desc-toggle-link">[see more]</button>
        </div>
        <div class="subtask-box-container">
            <div class="subtask-box-header"><span>Subtasks <span class="chevron-icon">▼</span></span></div>
            <div class="subtask-box-content">
                <div class="subtask-checklist">
                    ${data.subtasks.map(st => `
                        <label class="subtask-row ${st.checked ? 'checked' : ''}" data-subtask-id="${st.id}">
                            <input type="checkbox" ${st.checked ? 'checked' : ''}>
                            <span class="subtask-label-text">${escapeHtml(st.text)}</span>
                        </label>
                    `).join('')}
                </div>
                <div class="subtask-input-row">
                    <input type="text" placeholder="Add a subtask..." class="subtask-field">
                    <button class="subtask-add-submit">+</button>
                </div>
            </div>
        </div>
        <div class="card-footer-flex">
            <div class="footer-countdown">
                <span>${escapeHtml(data.dueDate)}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
            </div>
            <div class="footer-right-group">
                <a href="#"><div class="footer-icon-pill">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                    </svg><span>${data.attachments}</span>
                </div></a>
                <a href="#"><div class="footer-icon-pill">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg><span>${data.comments}</span>
                </div></a>
            </div>
        </div>
    `;
    return card;
}



function initCardInteractions(cardElement) {
    const descPara = cardElement.querySelector('.card-description-text');
    const toggleBtn = cardElement.querySelector('.desc-toggle-link');
    if (descPara && toggleBtn) {
        const newBtn = toggleBtn.cloneNode(true);
        toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);
        newBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            descPara.classList.toggle('truncate');
            newBtn.textContent = descPara.classList.contains('truncate') ? '[see more]' : '[see less]';
        });
    }

    const subtaskContainer = cardElement.querySelector('.subtask-box-container');
    const header = cardElement.querySelector('.subtask-box-header');
    if (subtaskContainer && header) {
        const newHeader = header.cloneNode(true);
        header.parentNode.replaceChild(newHeader, header);
        newHeader.addEventListener('click', (e) => {
            e.stopPropagation();
            subtaskContainer.classList.toggle('collapsed');
        });
    }

    const addBtn = cardElement.querySelector('.subtask-add-submit');
    const inputField = cardElement.querySelector('.subtask-field');
    const checklist = cardElement.querySelector('.subtask-checklist');
    if (addBtn && inputField && checklist) {
        const newAddBtn = addBtn.cloneNode(true);
        addBtn.parentNode.replaceChild(newAddBtn, addBtn);
        newAddBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const text = inputField.value.trim();
            if (!text) return;

            const taskSlug = cardElement.getAttribute('data-task-slug');

            apiCreateSubtask(taskSlug, text, (data) => { 

                const label = document.createElement('label');
                label.className = 'subtask-row';
                
                const sId = data.subtask.id || data.subtask.pk || data.subtask.subtask_id || '';
                label.setAttribute('data-subtask-id', sId);

                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.className = 'subtask-checkbox';

                const span = document.createElement('span');
                span.className = 'subtask-label-text';
                span.textContent = data.subtask.title || data.subtask.text || ''; 

                label.appendChild(cb);
                label.appendChild(span);
                checklist.appendChild(label);

                attachCheckboxBehavior(label);
                inputField.value = '';
                inputField.focus();
            });
        });
        inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                newAddBtn.click();
            }
        });
    }

    function attachCheckboxBehavior(row) {
        const chk = row.querySelector('input[type="checkbox"]');
        if (!chk) return;
        
        const updateClass = () => {
            if (chk.checked) row.classList.add('checked');
            else row.classList.remove('checked');
        };

        chk.addEventListener('change', () => {
            updateClass(); 

            const subtaskId = row.getAttribute('data-subtask-id');
            const taskSlug = cardElement.getAttribute('data-task-slug');

            if (!subtaskId) {
                console.warn("Skipping network sync: Missing subtask tracking ID on DOM structure.");
                return;
            }

            const isChecked = chk.checked;

            apiUpdateSubtaskStatus(taskSlug, subtaskId, isChecked);
        });

        updateClass();
    }
    cardElement.querySelectorAll('.subtask-row').forEach(row => attachCheckboxBehavior(row));
}



function connectWebSocket(forcedSlug = null) {
    let workspaceSlug = forcedSlug;

    if (!workspaceSlug) {
        const slugElement = document.getElementById('active-workspace-slug');
        if (!slugElement) return;
        workspaceSlug = JSON.parse(slugElement.textContent);
    }

    if (currentTaskSocket) {
        console.log("Closing previous workspace connection...");
        currentTaskSocket.close();
    }

    const wsScheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${wsScheme}${window.location.host}/ws/task/${workspaceSlug}/`;

    currentTaskSocket = new WebSocket(wsUrl);

    currentTaskSocket.onopen = () => console.log(`Live tracking connected dynamically to workspace: ${workspaceSlug}`);

    currentTaskSocket.onmessage = (event) => {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch (e) {
            console.error("Failed to parse incoming JSON payload:", e);
            return;
        }

        console.log("Real-time Payload Received:", data);

        let tasksArray = null;
        if (Array.isArray(data)) {
            tasksArray = data;
        } else if (data && Array.isArray(data.tasks)) {
            tasksArray = data.tasks;
        } else if (data && Array.isArray(data.payload)) {
            tasksArray = data.payload;
        } else if (data && Array.isArray(data.data)) {
            tasksArray = data.data;
        }

        if (data && data.role) {
            currentUserRole = data.role;
        } else if (tasksArray && tasksArray.length > 0 && tasksArray.role) {
            currentUserRole = tasksArray.role;
        } else if (data && data.payload && data.payload.role) {
            currentUserRole = data.payload.role;
        }

        if (tasksArray) {
            buildEmptyBoardSkeleton(currentUserRole);

            tasksArray.forEach(task => processAndAppendCard(task));
            updateAllCounters();
        }
        else if (data && (data.type === 'TASK_CREATED' || data.action === 'create')) {
            const singleTask = data.payload || data.data || data;
            processAndAppendCard(singleTask);
            updateAllCounters();
        }
    };

    currentTaskSocket.onclose = () => {
        console.warn('Synchronization connection closed.');
    };
}

function initSidebarLinks() {
    document.querySelectorAll('.workspace-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const newSlug = this.getAttribute('data-slug');
            new_workspace_slug = newSlug;
            document.querySelectorAll('.project-list li').forEach(li => li.classList.remove('active'));
            this.parentElement.classList.add('active');

            const topbarTitle = document.querySelector('.topbar-title');
            if (topbarTitle) {
                topbarTitle.textContent = `${this.textContent.trim()} · Kanban`;
            }

            if (!document.getElementById('kanbanBoard')) {
                const boardWrap = document.querySelector('.board-wrap');
                if (boardWrap) boardWrap.innerHTML = '<div class="board" id="kanbanBoard"></div>';
            }

            apiFetchWorkspaceMetadata(newSlug);

            buildEmptyBoardSkeleton(currentUserRole);
            connectWebSocket(newSlug);
        });
    });
}


document.addEventListener('DOMContentLoaded', () => {
    initSidebarLinks();

    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('mobileSidebarToggle');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });

        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 900 && sidebar.classList.contains('open') && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    document.getElementById('globalAddTaskBtn')?.addEventListener('click', () => alert('Open creation tracking modal dashboard. Drag cards in the meantime!'));

    if (document.getElementById('active-workspace-slug') || window.location.pathname.includes('/dashboard/')) {
        buildEmptyBoardSkeleton(currentUserRole);
        connectWebSocket();
    }
});

function getCSRFToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}