// core/static/core/js/loyalty_cards.js

let codeReader = null;
let scannedData = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
    initializeEventListeners();
});

// Initialize all event listeners
function initializeEventListeners() {
    // Add card buttons (desktop + FAB mobile)
    const addCardBtn = document.getElementById('add-card-btn');
    const addCardBtnFab = document.getElementById('add-card-btn-fab');
    const addFirstCardBtn = document.getElementById('add-first-card-btn');

    if (addCardBtn) addCardBtn.addEventListener('click', openAddModal);
    if (addCardBtnFab) addCardBtnFab.addEventListener('click', openAddModal);
    if (addFirstCardBtn) addFirstCardBtn.addEventListener('click', openAddModal);

    // Modal close buttons
    const closeModalBtn = document.getElementById('close-modal-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    if (closeModalBtn) closeModalBtn.addEventListener('click', closeAddModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeAddModal);

    // Save card button
    const saveCardBtn = document.getElementById('save-card-btn');
    if (saveCardBtn) saveCardBtn.addEventListener('click', saveCard);

    // Tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            switchTab(this.dataset.tab);
        });
    });

    // Card items - click to view
    const cardItems = document.querySelectorAll('.card-item');
    cardItems.forEach(function(item) {
        item.addEventListener('click', function() {
            viewBarcode(this.dataset.cardId);
        });
    });
}

// Modal management
function openAddModal() {
    document.getElementById('addCardModal').classList.remove('hidden');
    lucide.createIcons();
}

function closeAddModal() {
    document.getElementById('addCardModal').classList.add('hidden');
    resetForms();
    stopScanner();
}

// Tab switching
function switchTab(tab) {
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
        startScanner();
    }

    lucide.createIcons();
}

// Auto-detect barcode type from card number
function detectBarcodeType(code) {
    code = code.trim().replace(/\s/g, '');
    const isNumeric = /^\d+$/.test(code);

    if (isNumeric) {
        if (code.length === 13) return 'ean13';
        if (code.length === 8)  return 'ean8';
        if (code.length === 12) return 'upca';
        if (code.length % 2 === 0) return 'itf';
    }
    return 'code128';
}

// Scanner functions
async function startScanner() {
    if (!codeReader) {
        codeReader = new ZXing.BrowserMultiFormatReader();
    }

    try {
        const videoInputDevices = await codeReader.listVideoInputDevices();

        if (videoInputDevices.length === 0) {
            alert('No camera available');
            return;
        }

        // Use back camera if available
        const selectedDevice = videoInputDevices.find(function(device) {
            return device.label.toLowerCase().includes('back');
        }) || videoInputDevices[0];

        codeReader.decodeFromVideoDevice(
            selectedDevice.deviceId,
            'scanner-video',
            function(result, err) {
                if (result) onBarcodeScanned(result);
            }
        );

    } catch (error) {
        console.error('Scanner error:', error);
        alert('Error starting scanner');
    }
}

function stopScanner() {
    if (codeReader) codeReader.reset();
}

function onBarcodeScanned(result) {
    scannedData = {
        text: result.text,
        format: result.format.toLowerCase()
    };

    stopScanner();

    document.getElementById('scanned-code').textContent = result.text;
    document.getElementById('scanner-result').classList.remove('hidden');
    document.getElementById('scanner-info').classList.add('hidden');
    document.getElementById('scanForm').classList.remove('hidden');

    lucide.createIcons();
}

// View barcode
function viewBarcode(cardId) {
    window.location.href = '/loyalty-cards/' + cardId + '/';
}

// Reset forms
function resetForms() {
    document.getElementById('addCardForm').reset();
    document.getElementById('scanForm').reset();
    document.getElementById('scanForm').classList.add('hidden');
    document.getElementById('scanner-result').classList.add('hidden');
    document.getElementById('scanner-info').classList.remove('hidden');
    scannedData = null;
}

// Get CSRF token from meta tag
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
        return meta.getAttribute('content');
    }
    console.error('CSRF meta tag not found!');
    return null;
}

// Save card
async function saveCard() {
    const activeTab = document.getElementById('manual-pane').classList.contains('hidden') ? 'scan' : 'manual';
    let data;

    if (activeTab === 'manual') {
        const cardNumber = document.getElementById('cardNumber').value;
        data = {
            store_name: document.getElementById('storeName').value,
            card_number: cardNumber,
            barcode_type: detectBarcodeType(cardNumber),
            notes: document.getElementById('notes').value
        };
    } else {
        if (!scannedData) {
            alert('Please scan a barcode first');
            return;
        }
        data = {
            store_name: document.getElementById('storeNameScan').value,
            card_number: scannedData.text,
            barcode_type: detectBarcodeType(scannedData.text),
            notes: document.getElementById('notesScan').value
        };
    }

    if (!data.store_name || !data.card_number) {
        alert('Please fill in all required fields');
        return;
    }

    const csrfToken = getCsrfToken();
    if (!csrfToken) {
        alert('Page error. Please refresh and try again.');
        return;
    }

    try {
        const response = await fetch('/loyalty-cards/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            alert('Card added successfully!');
            location.reload();
        } else {
            alert('Error: ' + result.error);
        }

    } catch (error) {
        console.error('Fetch error:', error);
        alert('Error saving card');
    }
}