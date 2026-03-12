// Smart Traffic Surveillance frontend logic

const BACKEND_URL = "http://127.0.0.1:5000";

let currentPage = 'upload';
let selectedFiles = [];
let vehicleData = [];
let filteredVehicles = [];

let currentAnalysis = {
    isVideo: false,
    processedVideoName: null,
    vehiclesDetected: 0,
    platesDetected: 0,
    violationsDetected: 0,
    avgSpeed: 0
};

document.addEventListener('DOMContentLoaded', function () {
    initNavigation();
    initUpload();
    initProcessing();
    initOutputPage();
    initReportPage();
    initDashboard();
    initModals();

    const today = new Date().toISOString().split('T')[0];
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    document.getElementById('date-to').value = today;
    document.getElementById('date-from').value = thirtyDaysAgo.toISOString().split('T')[0];
});

// Navigation
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page');

    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const pageId = this.getAttribute('data-page');

            navLinks.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');

            pages.forEach(page => page.classList.remove('active'));
            document.getElementById(`${pageId}-page`).classList.add('active');

            currentPage = pageId;

            if (pageId === 'output') {
                updateVehicleDisplay();
            } else if (pageId === 'dashboard') {
                updateDashboard();
            }
        });
    });
}

// Upload
function initUpload() {
    const uploadArea = document.getElementById('upload-area');
    const browseBtn = document.getElementById('browse-btn');
    const fileInput = document.getElementById('file-input');
    const filePreview = document.getElementById('file-preview');
    const filesList = document.getElementById('files-list');
    const startProcessingBtn = document.getElementById('start-processing');
    const clearFilesBtn = document.getElementById('clear-files');
    const optionCards = document.querySelectorAll('.option-card');

    optionCards.forEach(card => {
        card.addEventListener('click', function () {
            optionCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
        });
    });

    browseBtn.addEventListener('click', function () {
        fileInput.click();
    });

    uploadArea.addEventListener('click', function () {
        fileInput.click();
    });

    fileInput.addEventListener('change', function () {
        if (this.files && this.files.length > 0) {
            handleFiles(this.files);
        }
    });

    uploadArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        this.style.borderColor = 'var(--primary-color)';
        this.style.backgroundColor = 'rgba(37, 99, 235, 0.02)';
    });

    uploadArea.addEventListener('dragleave', function (e) {
        e.preventDefault();
        this.style.borderColor = 'var(--gray-light)';
        this.style.backgroundColor = '';
    });

    uploadArea.addEventListener('drop', function (e) {
        e.preventDefault();
        this.style.borderColor = 'var(--gray-light)';
        this.style.backgroundColor = '';

        if (e.dataTransfer.files.length) {
            handleFiles(e.dataTransfer.files);
        }
    });

    startProcessingBtn.addEventListener('click', function () {
        if (selectedFiles.length === 0) {
            alert('Please select files to process.');
            return;
        }

        const file = selectedFiles[0];

        showLoading();
        document.querySelector('.nav-link[data-page="processing"]').click();
        startBackendProcessing(file);
    });

    clearFilesBtn.addEventListener('click', function () {
        selectedFiles = [];
        filesList.innerHTML = '';
        filePreview.style.display = 'none';
        fileInput.value = '';
    });

    function handleFiles(files) {
        for (let i = 0; i < files.length; i++) {
            const file = files[i];

            if (file.size > 2 * 1024 * 1024 * 1024) {
                alert(`File "${file.name}" exceeds 2GB limit. Please select a smaller file.`);
                continue;
            }

            const validTypes = [
                'video/mp4',
                'video/avi',
                'video/mov',
                'video/quicktime',
                'image/jpeg',
                'image/jpg',
                'image/png'
            ];
            if (!validTypes.includes(file.type)) {
                alert(`File "${file.name}" is not a supported format. Please select a video or image file.`);
                continue;
            }

            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        }
        updateFilesList();
    }

    function updateFilesList() {
        filesList.innerHTML = '';

        if (selectedFiles.length === 0) {
            filePreview.style.display = 'none';
            return;
        }

        filePreview.style.display = 'block';

        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';

            const fileIcon = file.type.startsWith('video') ? 'fas fa-video' : 'fas fa-image';
            const fileSize = formatFileSize(file.size);

            fileItem.innerHTML = `
                <div class="file-info-small">
                    <i class="${fileIcon}"></i>
                    <div class="file-details">
                        <h4>${file.name}</h4>
                        <p>${fileSize} • ${file.type}</p>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn-icon" onclick="removeFile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            filesList.appendChild(fileItem);
        });
    }

    window.formatFileSize = function (bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    window.removeFile = function (index) {
        selectedFiles.splice(index, 1);
        updateFilesList();
    };
}

async function startBackendProcessing(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const isImage = file.type.startsWith('image/');
        const endpoint = isImage ? '/analyze_image' : '/analyze_video';

        document.getElementById('current-file').textContent = file.name;
        document.getElementById('start-time').textContent = new Date().toLocaleTimeString();

        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }

        const data = await response.json();
        hideLoading();

        currentAnalysis.isVideo = !isImage;
        currentAnalysis.processedVideoName = data.processed_video_path || null;
        currentAnalysis.vehiclesDetected = data.vehicles_detected || (data.vehicles ? data.vehicles.length : 0);
        currentAnalysis.platesDetected = data.plates_detected || currentAnalysis.vehiclesDetected;
        currentAnalysis.violationsDetected = data.violations_detected || (data.vehicles ? data.vehicles.filter(v => v.violation).length : 0);

        vehicleData = mapBackendVehiclesToFrontend(data, isImage);
        filteredVehicles = [...vehicleData];

        document.getElementById('vehicles-count').textContent = currentAnalysis.vehiclesDetected;
        document.getElementById('plates-count').textContent = currentAnalysis.platesDetected;
        document.getElementById('violations-count').textContent = currentAnalysis.violationsDetected;

        const avgSpeed = vehicleData.length
            ? Math.round(vehicleData.reduce((s, v) => s + (v.speed || 0), 0) / vehicleData.length)
            : 0;
        currentAnalysis.avgSpeed = avgSpeed;
        document.getElementById('avg-speed').textContent = `${avgSpeed} km/h`;

        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('progress-percent').textContent = '100%';

        const resultsBtn = document.getElementById('results-btn');
        resultsBtn.disabled = false;
        resultsBtn.style.opacity = '1';

        showProcessedMedia(data, isImage);
    } catch (err) {
        console.error(err);
        hideLoading();
        alert('An error occurred while processing the media.');
    }
}

function mapBackendVehiclesToFrontend(data, isImage) {
    const backendVehicles = data.vehicles || [];
    return backendVehicles.map((v, idx) => {
        const id = v.vehicle_id ?? idx;
        const type = v.vehicle_type || v.type || 'car';
        const violation = v.violation === true;
        const speed = v.speed ?? v.avg_speed ?? 0;
        const speedLimit = v.speed_limit ?? 60;

        return {
            id,
            plate: v.plate || 'UNKNOWN',
            type,
            typeName: type.charAt(0).toUpperCase() + type.slice(1),
            color: violation ? 'Red' : 'Green',
            speed,
            speedLimit,
            violations: violation ? [v.violation_type || 'Speeding'] : [],
            timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
            location: 'Camera 1',
            image: '',
            status: violation ? 'violation' : 'normal',
            make: 'Unknown',
            model: '',
            year: ''
        };
    });
}

function showProcessedMedia(data, isImage) {
    const container = document.getElementById('processed-media');
    const img = document.getElementById('processed-image');
    const video = document.getElementById('processed-video');

    container.style.display = 'block';
    img.style.display = 'none';
    video.style.display = 'none';

    if (isImage && data.processed_image) {
        img.src = `data:image/jpeg;base64,${data.processed_image}`;
        img.style.display = 'block';
    } else if (!isImage && data.processed_video_path) {
        video.src = `${BACKEND_URL}/videos/${data.processed_video_path}`;
        video.style.display = 'block';
    }
}

// Processing page
function initProcessing() {
    const stopBtn = document.getElementById('stop-processing');
    const resultsBtn = document.getElementById('results-btn');

    stopBtn.addEventListener('click', function () {
        if (confirm('Are you sure you want to stop processing?')) {
            document.getElementById('progress-fill').style.width = '0%';
            document.getElementById('progress-percent').textContent = '0%';
            document.getElementById('timer').textContent = '00:00';

            document.getElementById('vehicles-count').textContent = '0';
            document.getElementById('plates-count').textContent = '0';
            document.getElementById('violations-count').textContent = '0';
            document.getElementById('avg-speed').textContent = '0 km/h';

            document.querySelector('.nav-link[data-page="upload"]').click();
        }
    });

    resultsBtn.addEventListener('click', function () {
        document.querySelector('.nav-link[data-page="output"]').click();
    });
}

// Output page
function initOutputPage() {
    const searchInput = document.getElementById('search-vehicle');
    const filterType = document.getElementById('filter-type');
    const filterViolation = document.getElementById('filter-violation');
    const speedSlider = document.getElementById('speed-slider');
    const speedValue = document.getElementById('speed-value');
    const applyFiltersBtn = document.getElementById('apply-filters');
    const exportBtn = document.getElementById('export-btn');
    const viewButtons = document.querySelectorAll('.view-btn');
    const closeDetailsBtn = document.getElementById('close-details');

    searchInput.addEventListener('input', filterVehicles);
    filterType.addEventListener('change', filterVehicles);
    filterViolation.addEventListener('change', filterVehicles);

    speedSlider.addEventListener('input', function () {
        speedValue.textContent = `0-${this.value} km/h`;
        filterVehicles();
    });

    applyFiltersBtn.addEventListener('click', filterVehicles);

    exportBtn.addEventListener('click', function () {
        const dataStr = JSON.stringify(filteredVehicles, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `vehicle-data-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });

    viewButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            viewButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            const view = this.getAttribute('data-view');
            const vehiclesGrid = document.getElementById('vehicles-grid');

            if (view === 'list') {
                vehiclesGrid.classList.add('list-view');
            } else {
                vehiclesGrid.classList.remove('list-view');
            }
        });
    });

    closeDetailsBtn.addEventListener('click', function () {
        document.getElementById('vehicle-details').classList.remove('active');
    });

    updateVehicleDisplay();
}

function filterVehicles() {
    const searchTerm = document.getElementById('search-vehicle').value.toLowerCase();
    const filterType = document.getElementById('filter-type').value;
    const filterViolation = document.getElementById('filter-violation').value;
    const maxSpeed = parseInt(document.getElementById('speed-slider').value, 10);

    filteredVehicles = vehicleData.filter(vehicle => {
        if (searchTerm && !vehicle.plate.toLowerCase().includes(searchTerm)) {
            return false;
        }

        if (filterType !== 'all' && vehicle.type !== filterType) {
            return false;
        }

        if (filterViolation === 'violation' && vehicle.violations.length === 0) {
            return false;
        }
        if (filterViolation === 'clean' && vehicle.violations.length > 0) {
            return false;
        }

        if ((vehicle.speed || 0) > maxSpeed) {
            return false;
        }

        return true;
    });

    updateVehicleDisplay();
}

function updateVehicleDisplay() {
    const vehiclesGrid = document.getElementById('vehicles-grid');
    const totalVehicles = document.getElementById('total-vehicles');
    const violationStat = document.querySelector('.violation-stat');

    vehiclesGrid.innerHTML = '';

    totalVehicles.textContent = filteredVehicles.length;

    const violationsCount = filteredVehicles.filter(v => v.violations.length > 0).length;
    violationStat.textContent = violationsCount;

    if (filteredVehicles.length > 0) {
        const avgSpeed = filteredVehicles.reduce((sum, v) => sum + (v.speed || 0), 0) / filteredVehicles.length;
        document.querySelectorAll('.stat-value')[2].textContent = `${Math.round(avgSpeed)} km/h`;
    }

    filteredVehicles.forEach(vehicle => {
        const vehicleCard = createVehicleCard(vehicle);
        vehiclesGrid.appendChild(vehicleCard);
    });

    if (filteredVehicles.length === 0) {
        vehiclesGrid.innerHTML = `
            <div class="no-results">
                <i class="fas fa-car"></i>
                <h3>No Vehicles Found</h3>
                <p>Try adjusting your filters or search terms.</p>
            </div>
        `;
    }
}

function createVehicleCard(vehicle) {
    const card = document.createElement('div');
    card.className = `vehicle-card ${vehicle.status}`;

    const violationBadge = vehicle.violations.length > 0
        ? `<div class="violation-badge">${vehicle.violations.length} violation${vehicle.violations.length > 1 ? 's' : ''}</div>`
        : '';

    const iconClass = getVehicleIcon(vehicle.type);

    card.innerHTML = `
        <div class="vehicle-image" style="background: ${getVehicleColor(vehicle.color)}">
            <i class="${iconClass}"></i>
        </div>
        <div class="vehicle-info">
            <div class="vehicle-header">
                <div class="vehicle-plate">${vehicle.plate}</div>
                <div class="vehicle-type">${vehicle.typeName}</div>
            </div>
            <div class="vehicle-details-list">
                <div class="detail-row">
                    <span class="detail-label">Color</span>
                    <span class="detail-value">${vehicle.color}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Speed</span>
                    <span class="detail-value ${vehicle.speed > vehicle.speedLimit ? 'violation-stat' : ''}">
                        ${vehicle.speed} km/h
                    </span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Limit</span>
                    <span class="detail-value">${vehicle.speedLimit} km/h</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time</span>
                    <span class="detail-value">${vehicle.timestamp.split(' ')[1]}</span>
                </div>
            </div>
            ${violationBadge}
            <div class="vehicle-actions">
                <button class="btn btn-secondary btn-sm" onclick="showVehicleDetails(${vehicle.id})">
                    <i class="fas fa-info-circle"></i> Details
                </button>
                <button class="btn btn-primary btn-sm" onclick="downloadVehicleReport(${vehicle.id})">
                    <i class="fas fa-file-alt"></i> Report
                </button>
            </div>
        </div>
    `;

    return card;
}

function getVehicleIcon(type) {
    const icons = {
        car: 'fas fa-car',
        suv: 'fas fa-truck',
        truck: 'fas fa-truck-moving',
        motorcycle: 'fas fa-motorcycle',
        bus: 'fas fa-bus',
        van: 'fas fa-shuttle-van'
    };
    return icons[type] || 'fas fa-car';
}

function getVehicleColor(color) {
    const colors = {
        Blue: 'linear-gradient(45deg, #3b82f6 0%, #1d4ed8 100%)',
        Black: 'linear-gradient(45deg, #4b5563 0%, #1f2937 100%)',
        Red: 'linear-gradient(45deg, #ef4444 0%, #dc2626 100%)',
        White: 'linear-gradient(45deg, #f3f4f6 0%, #d1d5db 100%)',
        Gray: 'linear-gradient(45deg, #9ca3af 0%, #6b7280 100%)',
        Silver: 'linear-gradient(45deg, #e5e7eb 0%, #9ca3af 100%)',
        Green: 'linear-gradient(45deg, #10b981 0%, #059669 100%)',
        Yellow: 'linear-gradient(45deg, #fbbf24 0%, #d97706 100%)'
    };
    return colors[color] || 'linear-gradient(45deg, #3b82f6 0%, #1d4ed8 100%)';
}

window.showVehicleDetails = function (vehicleId) {
    const vehicle = vehicleData.find(v => v.id === vehicleId);
    if (!vehicle) return;

    const detailsContent = document.getElementById('details-content');
    const violationsList = vehicle.violations.map(v => `<li>${v}</li>`).join('');

    detailsContent.innerHTML = `
        <div class="vehicle-detail-header">
            <div class="detail-plate">${vehicle.plate}</div>
            <div class="detail-type">${vehicle.typeName}</div>
        </div>
        <div class="detail-section">
            <h4>Vehicle Information</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Make</span>
                    <span class="detail-value">${vehicle.make}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Model</span>
                    <span class="detail-value">${vehicle.model}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Year</span>
                    <span class="detail-value">${vehicle.year}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Color</span>
                    <span class="detail-value">${vehicle.color}</span>
                </div>
            </div>
        </div>
        <div class="detail-section">
            <h4>Detection Details</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Detected Speed</span>
                    <span class="detail-value ${vehicle.speed > vehicle.speedLimit ? 'violation-stat' : ''}">
                        ${vehicle.speed} km/h
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Speed Limit</span>
                    <span class="detail-value">${vehicle.speedLimit} km/h</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Over Speed</span>
                    <span class="detail-value ${vehicle.speed > vehicle.speedLimit ? 'violation-stat' : ''}">
                        ${vehicle.speed - vehicle.speedLimit} km/h
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Detection Time</span>
                    <span class="detail-value">${vehicle.timestamp}</span>
                </div>
                <div class="detail-item full-width">
                    <span class="detail-label">Location</span>
                    <span class="detail-value">${vehicle.location}</span>
                </div>
            </div>
        </div>
        <div class="detail-section">
            <h4>Violations</h4>
            ${vehicle.violations.length > 0
                ? `<ul class="violations-list">${violationsList}</ul>`
                : '<p class="no-violations">No violations detected</p>'}
        </div>
        <div class="detail-actions">
            <button class="btn btn-primary" onclick="downloadVehicleReport(${vehicle.id})">
                <i class="fas fa-file-archive"></i> Download Report
            </button>
        </div>
    `;

    document.getElementById('vehicle-details').classList.add('active');
};

// Report page
function initReportPage() {
    const searchReportBtn = document.getElementById('search-report');
    const reportPlateInput = document.getElementById('report-plate');
    const printReportBtn = document.getElementById('print-report');
    const exportReportBtn = document.getElementById('export-report');
    const emailReportBtn = document.getElementById('email-report');

    searchReportBtn.addEventListener('click', function () {
        const plate = reportPlateInput.value.trim().toUpperCase();
        if (plate) {
            generateReport(plate);
        } else {
            alert('Please enter a license plate number.');
        }
    });

    reportPlateInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            searchReportBtn.click();
        }
    });

    printReportBtn.addEventListener('click', function () {
        window.print();
    });

    exportReportBtn.addEventListener('click', function () {
        window.location.href = `${BACKEND_URL}/export_report`;
    });

    emailReportBtn.addEventListener('click', function () {
        const email = prompt('Enter email address to send the report:');
        if (email) {
            alert(`Report would be sent to ${email} (backend email sending not implemented).`);
        }
    });
}

function generateReport(plate) {
    const reportContent = document.getElementById('report-content');
    const noResults = document.getElementById('no-results');
    const reportResults = document.getElementById('report-results');

    const matchingVehicles = vehicleData.filter(vehicle =>
        vehicle.plate.toUpperCase().includes(plate.toUpperCase())
    );

    if (matchingVehicles.length === 0) {
        reportContent.style.display = 'none';
        noResults.style.display = 'block';
        return;
    }

    const totalDetections = matchingVehicles.length;
    const totalViolations = matchingVehicles.reduce((sum, vehicle) => sum + vehicle.violations.length, 0);
    const speedingCount = matchingVehicles.filter(v => v.violations.includes("Speeding")).length;
    const avgSpeed = matchingVehicles.reduce((sum, vehicle) => sum + (vehicle.speed || 0), 0) / matchingVehicles.length;

    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;

    reportContent.innerHTML = `
        <div class="report-header">
            <h2>Vehicle Traffic Report</h2>
            <div class="report-plate">${plate}</div>
            <p>Report Period: ${dateFrom} to ${dateTo}</p>
        </div>
        <div class="report-stats">
            <div class="report-stat-card">
                <i class="fas fa-search"></i>
                <div class="report-stat-value">${totalDetections}</div>
                <div class="report-stat-label">Total Detections</div>
            </div>
            <div class="report-stat-card">
                <i class="fas fa-exclamation-triangle"></i>
                <div class="report-stat-value">${totalViolations}</div>
                <div class="report-stat-label">Total Violations</div>
            </div>
            <div class="report-stat-card">
                <i class="fas fa-tachometer-alt"></i>
                <div class="report-stat-value">${Math.round(avgSpeed)}</div>
                <div class="report-stat-label">Avg Speed (km/h)</div>
            </div>
            <div class="report-stat-card">
                <i class="fas fa-percentage"></i>
                <div class="report-stat-value">${Math.round((speedingCount / totalDetections) * 100)}%</div>
                <div class="report-stat-label">Speeding Rate</div>
            </div>
        </div>
        <div class="violations-list">
            <h3>Violation History</h3>
            ${matchingVehicles.filter(v => v.violations.length > 0).map(vehicle => `
                <div class="violation-item">
                    <div class="violation-header">
                        <span class="violation-type">${vehicle.violations.join(', ')}</span>
                        <span class="violation-time">${vehicle.timestamp}</span>
                    </div>
                    <p>Location: ${vehicle.location} | Speed: ${vehicle.speed} km/h (Limit: ${vehicle.speedLimit} km/h)</p>
                </div>
            `).join('')}
            ${matchingVehicles.filter(v => v.violations.length === 0).length > 0 ?
                `<p class="no-violations-msg">${matchingVehicles.filter(v => v.violations.length === 0).length} detections with no violations</p>`
                : ''}
        </div>
        <div class="detection-history">
            <h3>Detection History</h3>
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Date & Time</th>
                            <th>Location</th>
                            <th>Speed</th>
                            <th>Violations</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${matchingVehicles.map(vehicle => `
                            <tr>
                                <td>${vehicle.timestamp}</td>
                                <td>${vehicle.location}</td>
                                <td>${vehicle.speed} km/h</td>
                                <td>${vehicle.violations.length > 0 ? vehicle.violations.join(', ') : 'None'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    reportContent.style.display = 'block';
    noResults.style.display = 'none';
    reportResults.scrollIntoView({ behavior: 'smooth' });
}

// Dashboard (Chart.js)
function initDashboard() {
    updateDashboard();
}

let speedChartInstance;
let violationsTimelineInstance;

async function updateDashboard() {
    try {
        const res = await fetch(`${BACKEND_URL}/dashboard_stats`);
        const stats = await res.json();

        buildSpeedChart(stats.speed_distribution || []);
        buildViolationsTimelineChart(stats.violations_timeline || []);

        const violatorsTable = document.getElementById('violators-table');
        const topPlates = stats.top_violating_plates || [];
        violatorsTable.innerHTML = topPlates.map(v => `
            <tr>
                <td>${v.plate}</td>
                <td>${v.count} violations</td>
                <td>-</td>
                <td><span class="status-badge status-warning">Active</span></td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Failed to load dashboard stats', err);
    }
}

function buildSpeedChart(speedDistribution) {
    const canvas = document.getElementById('speed-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const labels = speedDistribution.map(b => b.range);
    const counts = speedDistribution.map(b => b.count);

    if (speedChartInstance) speedChartInstance.destroy();
    speedChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Vehicles',
                data: counts,
                backgroundColor: 'rgba(37, 99, 235, 0.7)'
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } }
        }
    });
}

function buildViolationsTimelineChart(timeline) {
    const canvas = document.getElementById('violations-timeline-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const labels = timeline.map(p => `${p.hour}:00`);
    const counts = timeline.map(p => p.count);

    if (violationsTimelineInstance) violationsTimelineInstance.destroy();
    violationsTimelineInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Violations',
                data: counts,
                borderColor: 'rgba(239, 68, 68, 0.9)',
                backgroundColor: 'rgba(239, 68, 68, 0.3)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true
        }
    });
}

// Modals & loading
function initModals() {
    const closeModalBtn = document.getElementById('close-modal');
    const modal = document.getElementById('image-modal');

    closeModalBtn.addEventListener('click', function () {
        modal.classList.remove('active');
    });

    modal.addEventListener('click', function (e) {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });
}

window.showVehicleImage = function (plate) {
    const vehicle = vehicleData.find(v => v.plate === plate);
    if (!vehicle) return;

    const modal = document.getElementById('image-modal');
    const modalImage = document.getElementById('modal-image');
    const modalInfo = document.getElementById('modal-info');

    modalImage.src = `https://via.placeholder.com/600x400/3b82f6/FFFFFF?text=${vehicle.plate}+${vehicle.typeName}`;
    modalInfo.innerHTML = `
        <h4>${vehicle.plate} - ${vehicle.typeName}</h4>
        <p>Color: ${vehicle.color} | Speed: ${vehicle.speed} km/h</p>
        <p>Detected: ${vehicle.timestamp}</p>
        <p>Location: ${vehicle.location}</p>
    `;

    modal.classList.add('active');
};

function showLoading() {
    document.getElementById('loading-spinner').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-spinner').classList.remove('active');
}

// Per-vehicle report
window.downloadVehicleReport = function (vehicleId) {
    window.location.href = `${BACKEND_URL}/vehicle_report/${vehicleId}`;
};
