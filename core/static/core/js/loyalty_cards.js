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

// Card search with autocomplete
function initCardSearch() {
    var input = document.getElementById('card-search');
    if (!input) return;

    var list      = document.getElementById('card-autocomplete');
    var clearBtn  = document.getElementById('card-search-clear');
    var noResults = document.getElementById('no-search-results');
    var grid      = document.getElementById('cards-grid');
    var items     = Array.from(document.querySelectorAll('.card-item')).map(function(el) {
        return { el: el, name: el.dataset.storeName || '' };
    });

    function filterCards(query) {
        var q = query.trim().toLowerCase();
        var visible = 0;
        items.forEach(function(item) {
            var match = !q || item.name.toLowerCase().indexOf(q) !== -1;
            item.el.style.display = match ? '' : 'none';
            if (match) visible++;
        });
        if (noResults) noResults.classList.toggle('hidden', visible > 0 || !q);
        if (grid)      grid.classList.toggle('hidden', visible === 0 && !!q);
        if (clearBtn)  clearBtn.classList.toggle('hidden', !q);
    }

    function buildSuggestions(query) {
        var q = query.trim().toLowerCase();
        list.innerHTML = '';
        if (!q) { list.classList.add('hidden'); return; }
        var seen = {};
        var matches = items.filter(function(item) {
            var n = item.name.toLowerCase();
            if (n.indexOf(q) !== -1 && !seen[n]) { seen[n] = true; return true; }
            return false;
        });
        if (!matches.length) { list.classList.add('hidden'); return; }
        matches.forEach(function(item) {
            var li      = document.createElement('li');
            var lc      = item.name.toLowerCase();
            var idx     = lc.indexOf(q);
            var before  = item.name.slice(0, idx);
            var match   = item.name.slice(idx, idx + q.length);
            var after   = item.name.slice(idx + q.length);
            li.className = 'px-4 py-2.5 flex items-center gap-2.5 cursor-pointer hover:bg-gray-50 text-sm text-gray-700 transition-colors';
            li.innerHTML = '<i data-lucide="credit-card" class="w-3.5 h-3.5 text-blue-500 flex-shrink-0"></i>'
                + '<span>' + before + '<strong class="text-blue-600">' + match + '</strong>' + after + '</span>';
            li.addEventListener('mousedown', function(e) {
                e.preventDefault();
                input.value = item.name;
                list.classList.add('hidden');
                filterCards(item.name);
            });
            list.appendChild(li);
        });
        lucide.createIcons();
        list.classList.remove('hidden');
    }

    input.addEventListener('input', function() {
        filterCards(input.value);
        buildSuggestions(input.value);
    });
    input.addEventListener('focus', function() {
        if (input.value.trim()) buildSuggestions(input.value);
    });
    input.addEventListener('blur', function() {
        setTimeout(function() { list.classList.add('hidden'); }, 150);
    });
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            input.value = '';
            filterCards('');
            list.classList.add('hidden');
        }
    });
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            input.value = '';
            filterCards('');
            list.classList.add('hidden');
            input.focus();
        });
    }
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

    initCardSearch();
});