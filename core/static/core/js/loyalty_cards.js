let codeReader = null;
let isScanning = false;
let currentTab = 'manual';

// Open modal
function openAddModal() {
    document.getElementById('addCardModal').classList.remove('hidden');
    lucide.createIcons();
}

// Close modal
function closeAddModal() {
    document.getElementById('addCardModal').classList.add('hidden');
    stopScanner();
    resetForm();
}

// Switch tabs
function switchTab(tab) {
    currentTab = tab;
    
    const manualTab = document.getElementById('tab-manual');
    const scanTab = document.getElementById('tab-scan');
    const manualPane = document.getElementById('manual-pane');
    const scanPane = document.getElementById('scan-pane');
    
    if (tab === 'manual') {
        manualTab.classList.add('border-blue-600', 'text-blue-600');
        manualTab.classList.remove('border-transparent', 'text-gray-600');
        scanTab.classList.remove('border-blue-600', 'text-blue-600');
        scanTab.classList.add('border-transparent', 'text-gray-600');
        
        manualPane.classList.remove('hidden');
        scanPane.classList.add('hidden');
        
        stopScanner();
    } else {
        scanTab.classList.add('border-blue-600', 'text-blue-600');
        scanTab.classList.remove('border-transparent', 'text-gray-600');
        manualTab.classList.remove('border-blue-600', 'text-blue-600');
        manualTab.classList.add('border-transparent', 'text-gray-600');
        
        scanPane.classList.remove('hidden');
        manualPane.classList.add('hidden');
        
        initScanner();
    }
}

// Initialize scanner
function initScanner() {
    if (isScanning) return;
    
    const videoElement = document.getElementById('scanner-video');
    const resultDiv = document.getElementById('scanner-result');
    const scannedCode = document.getElementById('scanned-code');
    const scanForm = document.getElementById('scanForm');
    
    resultDiv.classList.add('hidden');
    scanForm.classList.add('hidden');
    
    codeReader = new ZXingBrowser.BrowserMultiFormatReader();
    
    console.log('Starting scanner...');
    
    codeReader.decodeFromVideoDevice(null, videoElement, function(result, error) {
        if (result) {
            console.log('Barcode decoded:', result.text);
            
            // Show result
            scannedCode.textContent = result.text;
            resultDiv.classList.remove('hidden');
            scanForm.classList.remove('hidden');
            
            // Fill card number in manual form
            document.getElementById('cardNumber').value = result.text;
            
            // Stop scanner
            stopScanner();
            
            // Show notification
            showNotification('Barcode scanned: ' + result.text, 'success');
            
            // Switch to manual tab after delay
            setTimeout(function() {
                switchTab('manual');
            }, 1000);
        }
        
        if (error && error.name !== 'NotFoundException') {
            console.error('Scanner error:', error);
        }
    }).then(function() {
        isScanning = true;
        console.log('Scanner started');
    }).catch(function(err) {
        console.error('Failed to start scanner:', err);
        showNotification('Failed to access camera', 'error');
    });
}

// Stop scanner
function stopScanner() {
    if (codeReader) {
        try {
            codeReader.reset();
            console.log('Scanner stopped');
        } catch (e) {
            console.log('Error stopping scanner:', e);
        }
        codeReader = null;
    }
    isScanning = false;
}

// Save card
function saveCard() {
    const saveBtn = document.getElementById('save-card-btn');
    let storeName, cardNumber, notes;
    
    if (currentTab === 'manual') {
        storeName = document.getElementById('storeName').value.trim();
        cardNumber = document.getElementById('cardNumber').value.trim();
        notes = document.getElementById('notes').value.trim();
    } else {
        storeName = document.getElementById('storeNameScan').value.trim();
        cardNumber = document.getElementById('scanned-code').textContent.trim();
        notes = document.getElementById('notesScan').value.trim();
    }
    
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
    const originalText = saveBtn.innerHTML;
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
            saveBtn.innerHTML = originalText;
            lucide.createIcons();
        }
    })
    .catch(function(error) {
        console.error('Error:', error);
        showNotification('An error occurred', 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
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
    document.getElementById('storeNameScan').value = '';
    document.getElementById('notesScan').value = '';
    document.getElementById('scanner-result').classList.add('hidden');
    document.getElementById('scanForm').classList.add('hidden');
    currentTab = 'manual';
    switchTab('manual');
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
    
    // Save button
    document.getElementById('save-card-btn').addEventListener('click', saveCard);
    
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