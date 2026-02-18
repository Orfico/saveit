// core/static/core/js/loyalty_cards.js

// Open modal
function openAddModal() {
    document.getElementById('addCardModal').classList.remove('hidden');
    lucide.createIcons();
}

// Close modal
function closeAddModal() {
    document.getElementById('addCardModal').classList.add('hidden');
    resetForm();
}

// Save card
function saveCard() {
    const saveBtn = document.getElementById('save-card-btn');
    const storeName = document.getElementById('storeName').value.trim();
    const cardNumber = document.getElementById('cardNumber').value.trim();
    const notes = document.getElementById('notes').value.trim();
    
    if (!storeName || !cardNumber) {
        showNotification('Please fill in store name and card number', 'error');
        return;
    }
    
    const barcodeType = detectBarcodeType(cardNumber);
    
    const data = {
        store_name: storeName,
        card_number: cardNumber,
        barcode_type: barcodeType,
        notes: notes
    };
    
    // Loading state
    saveBtn.disabled = true;
    const originalHTML = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Saving...';
    lucide.createIcons();
    
    fetch('/loyalty-cards/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(data)
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        if (data.success) {
            showNotification('Card added successfully!', 'success');
            closeAddModal();
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        } else {
            showNotification(data.error || 'Failed to add card', 'error');
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalHTML;
            lucide.createIcons();
        }
    })
    .catch(function(error) {
        console.error('Error:', error);
        showNotification('An error occurred', 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalHTML;
        lucide.createIcons();
    });
}

// Detect barcode type
function detectBarcodeType(code) {
    code = code.trim();
    
    if (/^\d{13}$/.test(code)) return 'ean13';
    if (/^\d{8}$/.test(code)) return 'ean8';
    if (/^\d{12}$/.test(code)) return 'upca';
    if (/^\d+$/.test(code) && code.length % 2 === 0) return 'itf';
    
    return 'code128';
}

// Reset form
function resetForm() {
    document.getElementById('storeName').value = '';
    document.getElementById('cardNumber').value = '';
    document.getElementById('notes').value = '';
}

// Get CSRF token
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Show notification
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ' + 
        (type === 'success' ? 'bg-green-500' : 'bg-red-500') + ' text-white';
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(function() {
        notification.remove();
    }, 3000);
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
    
    // Open modal buttons
    const addBtn = document.getElementById('add-card-btn');
    const addBtnFab = document.getElementById('add-card-btn-fab');
    
    if (addBtn) {
        addBtn.addEventListener('click', openAddModal);
    }
    
    if (addBtnFab) {
        addBtnFab.addEventListener('click', openAddModal);
    }
    
    // Card click handlers
    const cards = document.querySelectorAll('.card-item');
    cards.forEach(function(card) {
        card.addEventListener('click', function() {
            const cardId = this.dataset.cardId;
            window.location.href = '/loyalty-cards/' + cardId + '/';
        });
    });
    
    // Close modal on outside click
    document.getElementById('addCardModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeAddModal();
        }
    });
});