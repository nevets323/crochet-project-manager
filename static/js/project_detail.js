// Project Detail Page JavaScript

// ============================================
// AJAX Step Toggle (no page reload)
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // Handle step checkbox toggling with AJAX
    const stepCheckboxes = document.querySelectorAll('.step-checkbox');

    stepCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function(e) {
            e.preventDefault();

            const stepId = this.dataset.stepId;
            const stepRow = this.closest('.step-item');
            const instructionsDiv = stepRow.querySelector('.step-instructions');

            // Show loading state
            this.disabled = true;
            stepRow.classList.add('opacity-50');

            // Send AJAX request
            fetch(`/step/${stepId}/toggle`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI based on new state
                    if (data.completed) {
                        instructionsDiv.classList.add('text-decoration-line-through', 'text-muted');
                        this.checked = true;
                    } else {
                        instructionsDiv.classList.remove('text-decoration-line-through', 'text-muted');
                        this.checked = false;
                    }
                } else {
                    // Revert checkbox on error
                    this.checked = !this.checked;
                    showNotification('Error toggling step: ' + (data.error || 'Unknown error'), 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Revert checkbox on error
                this.checked = !this.checked;
                showNotification('Error toggling step. Please try again.', 'danger');
            })
            .finally(() => {
                // Remove loading state
                this.disabled = false;
                stepRow.classList.remove('opacity-50');
            });
        });
    });
});

// ============================================
// Material Search Autocomplete
// ============================================
let searchTimeout;
const materialSearch = document.getElementById('materialSearch');
const materialSuggestions = document.getElementById('materialSuggestions');
const materialTypeId = document.getElementById('materialTypeId');
const addMaterialForm = document.getElementById('addMaterialForm');

if (materialSearch) {
    materialSearch.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) {
            materialSuggestions.style.display = 'none';
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/materials/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(materials => {
                    materialSuggestions.innerHTML = '';
                    materials.forEach(material => {
                        const item = document.createElement('a');
                        item.href = '#';
                        item.className = 'list-group-item list-group-item-action';
                        item.innerHTML = `<strong>${material.brand}</strong> - ${material.name}`;
                        if (material.description) {
                            item.innerHTML += `<br><small class="text-muted">${material.description}</small>`;
                        }

                        item.addEventListener('click', (e) => {
                            e.preventDefault();
                            materialSearch.value = `${material.brand} - ${material.name}`;
                            materialTypeId.value = material.id;
                            materialSuggestions.style.display = 'none';
                        });

                        materialSuggestions.appendChild(item);
                    });

                    if (materials.length > 0) {
                        materialSuggestions.style.display = 'block';
                    } else {
                        materialSuggestions.style.display = 'none';
                    }
                });
        }, 300);
    });

    // Close suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!materialSearch.contains(e.target) && !materialSuggestions.contains(e.target)) {
            materialSuggestions.style.display = 'none';
        }
    });
}

// ============================================
// New Material Modal Handler
// ============================================
function addNewMaterial() {
    const brand = document.getElementById('newMaterialBrand').value;
    const name = document.getElementById('newMaterialName').value;
    const description = document.getElementById('newMaterialDescription').value;

    if (!brand || !name) {
        showNotification('Brand and name are required', 'warning');
        return;
    }

    materialSearch.value = `${brand} - ${name}`;
    materialTypeId.value = '';  // Clear ID to indicate new material

    // Add hidden inputs for the new material
    addMaterialForm.innerHTML += `
        <input type="hidden" name="brand" value="${brand}">
        <input type="hidden" name="name" value="${name}">
        <input type="hidden" name="description" value="${description}">
    `;

    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('newMaterialModal'));
    modal.hide();
}

// ============================================
// Notification System
// ============================================
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}

// ============================================
// Loading Indicator Utility
// ============================================
function showLoadingIndicator(element) {
    const spinner = document.createElement('span');
    spinner.className = 'spinner-border spinner-border-sm ms-2 loading-spinner';
    spinner.role = 'status';
    spinner.setAttribute('aria-hidden', 'true');
    element.appendChild(spinner);
}

function hideLoadingIndicator(element) {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// ============================================
// Inline Step Editing (Double-click to edit)
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // Add double-click to edit functionality for step instructions
    document.querySelectorAll('.step-instructions').forEach(instructionsDiv => {
        instructionsDiv.addEventListener('dblclick', function() {
            enableInlineEdit(this);
        });
        // Add visual hint
        instructionsDiv.style.cursor = 'text';
        instructionsDiv.title = 'Double-click to edit';
    });
});

function enableInlineEdit(instructionsDiv) {
    const stepItem = instructionsDiv.closest('.step-item');
    const editButton = stepItem.querySelector('[data-bs-target^="#editStep"]');

    if (!editButton) return; // No edit button found

    // Extract step ID from modal target (e.g., "#editStep123" -> "123")
    const modalTarget = editButton.dataset.bsTarget;
    const stepId = modalTarget.replace('#editStep', '');

    const currentInstructions = instructionsDiv.textContent.trim();
    const roundNumberLabel = stepItem.querySelector('.form-check-label strong');
    const currentRoundNumber = roundNumberLabel ? roundNumberLabel.textContent.replace(':', '').trim() : '';

    // Create inline edit form
    const editForm = document.createElement('div');
    editForm.className = 'inline-edit-mode';
    editForm.innerHTML = `
        <div class="mb-2">
            <label class="form-label small">Round Number</label>
            <input type="text" class="form-control form-control-sm inline-edit-round" value="${currentRoundNumber}">
        </div>
        <div class="mb-2">
            <label class="form-label small">Instructions</label>
            <textarea class="form-control form-control-sm inline-edit-instructions" rows="2">${currentInstructions}</textarea>
        </div>
        <div class="inline-edit-buttons">
            <button type="button" class="btn btn-sm btn-success save-inline-edit">
                <i class="bi bi-check"></i> Save
            </button>
            <button type="button" class="btn btn-sm btn-secondary cancel-inline-edit">
                <i class="bi bi-x"></i> Cancel
            </button>
        </div>
    `;

    // Replace instructions div with edit form
    const parent = instructionsDiv.parentElement;
    const originalContent = instructionsDiv.cloneNode(true);
    parent.replaceChild(editForm, instructionsDiv);

    // Focus on textarea
    const textarea = editForm.querySelector('.inline-edit-instructions');
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    // Save button handler
    editForm.querySelector('.save-inline-edit').addEventListener('click', function() {
        const newRoundNumber = editForm.querySelector('.inline-edit-round').value.trim();
        const newInstructions = editForm.querySelector('.inline-edit-instructions').value.trim();

        if (!newInstructions) {
            showNotification('Instructions cannot be empty', 'warning');
            return;
        }

        // Show loading
        this.disabled = true;
        showLoadingIndicator(this);

        // Send update request
        fetch(`/step/${stepId}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `round_number=${encodeURIComponent(newRoundNumber)}&instructions=${encodeURIComponent(newInstructions)}`
        })
        .then(response => {
            if (response.ok) {
                // Update UI
                if (roundNumberLabel) {
                    roundNumberLabel.textContent = newRoundNumber + ':';
                }
                originalContent.textContent = newInstructions;
                parent.replaceChild(originalContent, editForm);
                // Re-add double-click listener
                originalContent.addEventListener('dblclick', function() {
                    enableInlineEdit(this);
                });
                originalContent.style.cursor = 'text';
                originalContent.title = 'Double-click to edit';
                showNotification('Step updated successfully!', 'success');
            } else {
                throw new Error('Failed to update step');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error updating step. Please try again.', 'danger');
            hideLoadingIndicator(this);
            this.disabled = false;
        });
    });

    // Cancel button handler
    editForm.querySelector('.cancel-inline-edit').addEventListener('click', function() {
        parent.replaceChild(originalContent, editForm);
    });

    // ESC key to cancel
    editForm.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            parent.replaceChild(originalContent, editForm);
        }
    });
}

// ============================================
// Drag-and-Drop for Parts Reordering
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    const partCards = document.querySelectorAll('[id^="part-"]');

    partCards.forEach(card => {
        card.setAttribute('draggable', 'true');
        card.classList.add('draggable');

        card.addEventListener('dragstart', function(e) {
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', this.innerHTML);
        });

        card.addEventListener('dragend', function(e) {
            this.classList.remove('dragging');
        });

        card.addEventListener('dragover', function(e) {
            e.preventDefault();
            const dragging = document.querySelector('.dragging');
            const afterElement = getDragAfterElement(this.parentElement, e.clientY);

            if (afterElement == null) {
                this.parentElement.appendChild(dragging);
            } else {
                this.parentElement.insertBefore(dragging, afterElement);
            }
        });

        card.addEventListener('drop', function(e) {
            e.preventDefault();
            savePartOrder();
        });
    });
});

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('[id^="part-"]:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;

        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

function savePartOrder() {
    const partCards = document.querySelectorAll('[id^="part-"]');
    const partIds = [];

    partCards.forEach(card => {
        const partId = card.id.replace('part-', '');
        partIds.push(partId);
    });

    // Get project ID from URL
    const projectIdMatch = window.location.pathname.match(/\/project\/(\d+)/);
    if (!projectIdMatch) return;
    const projectId = projectIdMatch[1];

    // Send AJAX request to save new order
    fetch(`/project/${projectId}/reorder_parts`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            part_ids: partIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Parts reordered successfully!', 'success');
        } else {
            showNotification('Error reordering parts: ' + (data.error || 'Unknown error'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error reordering parts. Please refresh the page.', 'danger');
    });
}

// ============================================
// Form Submit Loading States
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // Add loading states to form submissions
    const forms = document.querySelectorAll('form:not(.no-loading)');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton && !submitButton.disabled) {
                submitButton.disabled = true;
                showLoadingIndicator(submitButton);

                // Re-enable after timeout as fallback
                setTimeout(() => {
                    submitButton.disabled = false;
                    hideLoadingIndicator(submitButton);
                }, 10000);
            }
        });
    });
});
