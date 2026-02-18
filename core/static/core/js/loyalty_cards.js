// core/static/core/js/loyalty_cards.js

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('add-card-modal');
    const openModalBtn = document.getElementById('open-modal-btn');
    const openModalFab = document.getElementById('open-modal-fab');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const manualTabBtn = document.getElementById('manual-tab-btn');
    const scanTabBtn = document.getElementById('scan-tab-btn');
    const manualForm = document.getElementById('manual-form');
    const scanForm = document.getElementById('scan-form');
    const saveCardBtn = document.getElementById('save-card-btn');
    const cardNumberInput = document.getElementById('card-number');
    
    let codeReader = null;
    let isScanning = false;

    // Open modal
    if (openModalBtn) {
        openModalBtn.addEventListener('click', function() {
            modal.classList.remove('hidden');
        });
    }
    
    if (openModalFab) {
        openModalFab.addEventListener('click', function() {
            modal.classList.remove('hidden');
        });
    }

    // Close modal
    closeModalBtn.addEventListener('click', function() {
        modal.classList.add('hidden');
        stopScanner();
        resetForm();
    });

    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.add('hidden');
            stopScanner();
            resetForm();
        }
    });

    // Tab switching
    manualTabBtn.addEventListener('click', function() {
        manualTabBtn.classList.add('border-indigo-500', 'text-indigo-600');
        manualTabBtn.classList.remove('border-transparent', 'text-gray-500');
        scanTabBtn.classList.remove('border-indigo-500', 'text-indigo-600');
        scanTabBtn.classList.add('border-transparent', 'text-gray-500');
        
        manualForm.classList.remove('hidden');
        scanForm.classList.add('hidden');
        
        stopScanner();
    });

    scanTabBtn.addEventListener('click', function() {
        scanTabBtn.classList.add('border-indigo-500', 'text-indigo-600');
        scanTabBtn.classList.remove('border-transparent', 'text-gray-500');
        manualTabBtn.classList.remove('border-indigo-500', 'text-indigo-600');
        manualTabBtn.classList.add('border-transparent', 'text-gray-500');
        
        scanForm.classList.remove('hidden');
        manualForm.classList.add('hidden');
        
        initScanner();
    });

    // Initialize barcode scanner
    function initScanner() {
        if (isScanning) return;
        
        const videoElement = document.getElementById('scanner-video');
        const scanResult = document.getElementById('scan-result');
        const scanResultText = document.getElementById('scan-result-text');
        
        // Hide result initially
        scanResult.classList.add('hidden');
        
        // Use ZXing browser library
        codeReader = new ZXingBrowser.BrowserMultiFormatReader();
        
        console.log('Starting scanner...');
        
        codeReader.decodeFromVideoDevice(null, videoElement, function(result, error) {
            if (result) {
                // ✅ BARCODE DECODED!
                console.log('Barcode decoded:', result.text);
                
                // Show result in scan tab
                scanResultText.textContent = result.text;
                scanResult.classList.remove('hidden');
                
                // Fill the card number field in manual form
                cardNumberInput.value = result.text;
                
                // Stop scanner
                stopScanner();
                
                // Switch to manual tab after a short delay
                setTimeout(function() {
                    manualTabBtn.click();
                    showNotification('Barcode scanned: ' + result.text, 'success');
                }, 500);
            }
            
            // Ignore NotFoundException (means no barcode in frame yet)
            if (error && error.name !== 'NotFoundException') {
                console.error('Scanner error:', error);
            }
        }).then(function() {
            isScanning = true;
            console.log('Scanner started successfully');
        }).catch(function(err) {
            console.error('Failed to start scanner:', err);
            showNotification('Failed to access camera. Please check permissions.', 'error');
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
        
        const scanResult = document.getElementById('scan-result');
        if (scanResult) {
            scanResult.classList.add('hidden');
        }
    }

    // Detect barcode type from number
    function detectBarcodeType(code) {
        code = code.trim();
        
        if (/^\d{13}$/.test(code)) return 'ean13';
        if (/^\d{8}$/.test(code)) return 'ean8';
        if (/^\d{12}$/.test(code)) return 'upca';
        if (/^\d+$/.test(code) && code.length % 2 === 0) return 'itf';
        
        return 'code128';
    }

    // Save card
    saveCardBtn.addEventListener('click', function() {
        saveCard();
    });

    function saveCard() {
        const storeName = document.getElementById('store-name').value.trim();
        const cardNumber = cardNumberInput.value.trim();
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
        
        // Disable button during save
        saveCardBtn.disabled = true;
        saveCardBtn.textContent = 'Saving...';
        
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
                modal.classList.add('hidden');
                resetForm();
                setTimeout(function() {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(data.error || 'Failed to add card', 'error');
                saveCardBtn.disabled = false;
                saveCardBtn.textContent = 'Save Card';
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
            saveCardBtn.disabled = false;
            saveCardBtn.textContent = 'Save Card';
        });
    }

    // Reset form
    function resetForm() {
        document.getElementById('store-name').value = '';
        cardNumberInput.value = '';
        document.getElementById('notes').value = '';
        document.getElementById('scan-result').classList.add('hidden');
        saveCardBtn.disabled = false;
        saveCardBtn.textContent = 'Save Card';
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

    // Card click handler
    const cards = document.querySelectorAll('.loyalty-card');
    cards.forEach(function(card) {
        card.addEventListener('click', function() {
            const cardId = this.dataset.cardId;
            window.location.href = '/loyalty-cards/' + cardId + '/';
        });
    });
});