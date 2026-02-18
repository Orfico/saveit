// core/static/core/js/loyalty_card_detail.js

document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
});

function printBarcode() {
    window.print();
}

function downloadBarcode() {
    const cardData = document.getElementById('card-data');
    if (!cardData) {
        alert('Card data not found');
        return;
    }
    
    const barcodeUrl = cardData.dataset.barcodeUrl;
    const storeName = cardData.dataset.storeName;
    const cardNumber = cardData.dataset.cardNumber;
    
    if (barcodeUrl) {
        const link = document.createElement('a');
        link.href = barcodeUrl;
        link.download = storeName + '_' + cardNumber + '.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } else {
        alert('Barcode not available');
    }
}

async function shareBarcode() {
    const cardData = document.getElementById('card-data');
    if (!cardData) {
        alert('Card data not found');
        return;
    }
    
    const barcodeUrl = cardData.dataset.barcodeUrl;
    const storeName = cardData.dataset.storeName;
    const cardNumber = cardData.dataset.cardNumber;
    
    if (!barcodeUrl) {
        alert('Barcode not available');
        return;
    }
    
    if (navigator.share) {
        try {
            const response = await fetch(barcodeUrl);
            const blob = await response.blob();
            const file = new File([blob], storeName + '.png', { type: 'image/png' });
            
            await navigator.share({
                title: 'Loyalty Card ' + storeName,
                text: 'Card number: ' + cardNumber,
                files: [file]
            });
        } catch (error) {
            console.error('Share error:', error);
            fallbackShare(cardNumber);
        }
    } else {
        fallbackShare(cardNumber);
    }
}

function fallbackShare(cardNumber) {
    navigator.clipboard.writeText(cardNumber).then(function() {
        alert('Code copied to clipboard!');
    }).catch(function(err) {
        console.error('Clipboard error:', err);
        alert('Failed to copy to clipboard');
    });
}

async function deleteCard() {
    if (!confirm('Are you sure you want to delete this loyalty card?')) {
        return;
    }
    
    const cardData = document.getElementById('card-data');
    if (!cardData) {
        alert('Card data not found. Please refresh the page.');
        return;
    }
    
    const cardId = cardData.dataset.cardId;
    
    if (!cardId) {
        alert('Card ID not found. Please refresh the page.');
        return;
    }
    
    // Get CSRF token from meta tag
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (!csrfMeta) {
        alert('Page error. Please refresh and try again.');
        return;
    }
    const csrfToken = csrfMeta.getAttribute('content');
    
    try {
        const response = await fetch('/loyalty-cards/' + cardId + '/delete/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Card deleted successfully');
            window.location.href = '/loyalty-cards/';
        } else {
            alert('Error: ' + result.error);
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting card');
    }
}