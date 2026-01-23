// core/static/core/js/dashboard.js

/**
 * Dashboard Chart Initialization
 */
function initDashboardChart(pieDataJson) {
    const ctx = document.getElementById('pieChart');
    if (!ctx) return;
    
    let pieData;
    try {
        pieData = JSON.parse(pieDataJson);
    } catch (e) {
        console.error('Error parsing chart data:', e);
        return;
    }
    
    if (!pieData || pieData.length === 0) return;
    
    const labels = pieData.map(item => item.category__name);
    const data = pieData.map(item => Math.abs(item.total));
    const colors = pieData.map(item => item.category__color);
    
    // Responsive font size
    const isMobile = window.innerWidth < 640;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0,
                hoverBorderWidth: 2,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { 
                        padding: isMobile ? 12 : 20,
                        usePointStyle: true,
                        font: { 
                            size: isMobile ? 11 : 13, 
                            family: 'system-ui' 
                        },
                        color: '#374151',
                        boxWidth: isMobile ? 8 : 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: €${value.toFixed(2)} (${percentage}%)`;
                        }
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: isMobile ? 8 : 12,
                    cornerRadius: 8,
                    titleFont: { size: isMobile ? 12 : 14, weight: 'bold' },
                    bodyFont: { size: isMobile ? 11 : 13 }
                }
            },
            cutout: '65%'
        }
    });
}

/**
 * Fix Date Inputs - Prevent value clearing
 */
function initDateInputFix() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(input => {
        // Maintain value after selection
        input.addEventListener('change', function(e) {
            const selectedValue = e.target.value;
            setTimeout(() => {
                e.target.value = selectedValue;
            }, 10);
        });
        
        // Prevent reset on blur
        input.addEventListener('blur', function(e) {
            if (e.target.value) {
                const currentValue = e.target.value;
                setTimeout(() => {
                    e.target.value = currentValue;
                }, 10);
            }
        });
    });
}

/**
 * Initialize Dashboard
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Fix date inputs
    initDateInputFix();
    
    // Initialize chart if data exists
    const chartDataElement = document.getElementById('chartData');
    if (chartDataElement) {
        const pieDataJson = chartDataElement.textContent;
        initDashboardChart(pieDataJson);
    }
});