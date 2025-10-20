// NATGAS TRADER Dashboard - JavaScript

class TradingDashboard {
        constructor() {
            this.socket = null;
            this.signalChart = null;
            
            this.boilData = {
                labels: [],
                datasets: [{
                    label: 'BOIL Price ($)',
                    data: [],
                    borderColor: 'rgba(230, 56, 56)',   // Red for BOIL
                    backgroundColor: 'rgba(230, 56, 56, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            };
            
            this.koldData = {
                labels: [],
                datasets: [{
                    label: 'KOLD Price ($)',
                    data: [],
                    borderColor: 'rgba(15, 124, 191)',   // Blue for KOLD
                    backgroundColor: 'rgba(15, 124, 191, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            };
            
            this.storageData = {
                labels: [],
                datasets: [{
                    label: 'Natural Gas Storage (BCF)',
                    data: [],
                    borderColor: 'rgba(255, 255, 255)',   // White
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            };
            
            this.temperatureData = {
                labels: [],
                datasets: []
            };
            
            this.stormData = {
                labels: [],
                datasets: [{
                    label: 'Storm Alerts',
                    data: [],
                    borderColor: 'rgba(255, 165, 0)',   // Orange
                    backgroundColor: 'rgba(255, 165, 0, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            };
            
        this.currentTimePeriod = '1year'; // Default to last year
        this.isLoading = false; // Track loading state
        
        this.init();
        }
    
    init() {
        this.initSocket();
        this.initChart();
        this.loadInitialData();
        this.setupEventListeners();
        
        // Add callback methods for new charts
        this.loadTemperatureDataWithCallback = this.createCallbackWrapper(this.loadTemperatureData.bind(this));
        this.loadStormDataWithCallback = this.createCallbackWrapper(this.loadStormData.bind(this));
        
        // Load initial logs
        this.loadLogs();
        
        // Update strategy info
        this.updateStrategyInfo();
        
        // Load positions (with delay to ensure DOM is ready)
        setTimeout(() => {
            this.loadPositions();
        }, 100);
        
        // Make loadPositions available globally for debugging
        window.testPositions = () => {
            console.log('Manual test of loadPositions');
            this.loadPositions();
        };
        
        // Set up log refresh interval
        this.logRefreshInterval = setInterval(() => {
            this.loadLogs();
        }, 2000); // Refresh logs every 2 seconds
        
        // Auto-refresh every 5 minutes (300,000 milliseconds)
        setInterval(() => {
            console.log('Auto-refreshing dashboard...');
            window.location.reload();
        }, 300000);
    }
    
    initSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to dashboard server');
            this.updateStatus('connected', 'Connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from dashboard server');
            this.updateStatus('disconnected', 'Disconnected');
        });
        
        this.socket.on('data_update', (data) => {
            this.updateDashboard(data);
        });
        
        this.socket.on('status_update', (data) => {
            this.updateStatus(data.status, data.status.charAt(0).toUpperCase() + data.status.slice(1));
        });
        
        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
            this.addLog('error', `Socket error: ${error}`);
        });
    }
    
        initChart() {
            // Initialize BOIL Chart
            const boilCtx = document.getElementById('boilChart').getContext('2d');
            this.boilChart = new Chart(boilCtx, {
                type: 'line',
                data: this.boilData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        }
                    },
                    elements: {
                        point: {
                            radius: 3,
                            hoverRadius: 6
                        }
                    }
                }
            });
            
            // Initialize KOLD Chart
            const koldCtx = document.getElementById('koldChart').getContext('2d');
            this.koldChart = new Chart(koldCtx, {
                type: 'line',
                data: this.koldData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        }
                    },
                    elements: {
                        point: {
                            radius: 3,
                            hoverRadius: 6
                        }
                    }
                }
            });
            
            // Initialize Storage Chart
            const storageCtx = document.getElementById('storageChart').getContext('2d');
            this.storageChart = new Chart(storageCtx, {
                type: 'line',
                data: this.storageData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        }
                    },
                    elements: {
                        point: {
                            radius: 3,
                            hoverRadius: 6
                        }
                    }
                }
            });
            
            // Initialize Temperature Chart
            const tempCtx = document.getElementById('temperatureChart').getContext('2d');
            this.temperatureChart = new Chart(tempCtx, {
                type: 'bar',
                data: this.temperatureData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        }
                    }
                }
            });
            
            // Initialize Storm Chart
            const stormCtx = document.getElementById('stormChart').getContext('2d');
            this.stormChart = new Chart(stormCtx, {
                type: 'bar',
                data: this.stormData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#b0b0b0'
                            },
                            grid: {
                                color: '#333333'
                            }
                        }
                    },
                    elements: {
                        point: {
                            radius: 3,
                            hoverRadius: 6
                        }
                    }
                }
            });
        }
    
    loadInitialData() {
        // Load initial data from API
        fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                this.updateDashboard(data);
            })
            .catch(error => {
                console.error('Error loading initial data:', error);
                this.addLog('error', `Failed to load initial data: ${error.message}`);
            });
        
        // Load chart data
        this.loadChartData();
    }
    
    // Strategy management
    switchStrategy() {
        const selector = document.getElementById('strategySelector');
        const strategy = selector.value;
        
        fetch('/api/strategy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ strategy: strategy })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`Strategy switched to: ${strategy}`);
                // Update UI to reflect strategy change
                this.updateStrategyInfo();
            } else {
                console.error('Failed to switch strategy:', data.error);
                alert(`Failed to switch strategy: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error switching strategy:', error);
            alert('Error switching strategy');
        });
    }
    
    updateStrategyInfo() {
        fetch('/api/strategy')
        .then(response => response.json())
        .then(data => {
            // Update strategy selector to reflect current strategy
            const selector = document.getElementById('strategySelector');
            if (selector && data.strategy_name) {
                selector.value = data.strategy_name;
            }
            
            // Log strategy info
            console.log('Current strategy:', data.strategy_name);
            console.log('Strategy description:', data.description);
        })
        .catch(error => {
            console.error('Error getting strategy info:', error);
        });
    }
    
    // Positions management
    loadPositions() {
        console.log('Loading positions...');
        
        // Simple fallback - just show a basic message first
        const positionsList = document.getElementById('positionsList');
        if (positionsList) {
            positionsList.innerHTML = '<div class="no-positions">Loading positions...</div>';
        }
        
        fetch('/api/portfolio')
        .then(response => {
            console.log('Portfolio API response:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Portfolio data received:', data);
            if (data && data.positions) {
                this.updatePositions(data.positions);
            } else {
                console.log('No positions data found');
                this.updatePositions([]);
            }
        })
        .catch(error => {
            console.error('Error loading positions:', error);
            this.updatePositions([]);
        });
    }
    
    updatePositions(positions) {
        console.log('updatePositions called with:', positions);
        
        const positionsList = document.getElementById('positionsList');
        if (!positionsList) {
            console.error('Positions list element not found');
            return;
        }
        
        console.log('Updating positions:', positions);
        
        if (!positions || positions.length === 0) {
            positionsList.innerHTML = '<div class="no-positions">No positions</div>';
            console.log('No positions to display');
            return;
        }
        
        try {
            // Simple test - just show basic info first
            let positionsHTML = '<div style="color: white; padding: 10px;">';
            positionsHTML += `<h4>Found ${positions.length} positions:</h4>`;
            
            positions.forEach((position, index) => {
                console.log(`Processing position ${index}:`, position);
                positionsHTML += `<div style="margin: 10px 0; padding: 10px; border: 1px solid #333;">`;
                positionsHTML += `<strong>${position.symbol}</strong><br>`;
                positionsHTML += `Quantity: ${position.qty}<br>`;
                positionsHTML += `Value: $${position.market_value}<br>`;
                positionsHTML += `P&L: $${position.unrealized_pl}<br>`;
                positionsHTML += `</div>`;
            });
            
            positionsHTML += '</div>';
            positionsList.innerHTML = positionsHTML;
            console.log('Positions updated successfully');
        } catch (error) {
            console.error('Error updating positions:', error);
            positionsList.innerHTML = '<div class="no-positions">Error loading positions: ' + error.message + '</div>';
        }
    }
    
    loadChartData() {
        // Load BOIL data with current time period
        this.loadBoilData();
        
        // Load KOLD data with current time period
        this.loadKoldData();
        
        // Load storage data with current time period
        this.loadStorageData();
        
        // Load temperature data
        this.loadTemperatureData();
        
        // Load storm data
        this.loadStormData();
    }
    
        loadStorageData() {
            // Show loading animation
            this.showLoading();
            
            const url = `/api/storage-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading storage data:', data.error);
                    } else {
                        this.updateStorageChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading storage data:', error);
                })
                .finally(() => {
                    // Hide loading animation
                    this.hideLoading();
                });
        }
        
        loadBoilData() {
            const url = `/api/boil-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading BOIL data:', data.error);
                    } else {
                        this.updateBoilChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading BOIL data:', error);
                });
        }
        
        loadBoilDataWithCallback(callback) {
            const url = `/api/boil-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading BOIL data:', data.error);
                    } else {
                        this.updateBoilChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading BOIL data:', error);
                })
                .finally(() => {
                    if (callback) callback();
                });
        }
        
        loadKoldData() {
            const url = `/api/kold-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading KOLD data:', data.error);
                    } else {
                        this.updateKoldChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading KOLD data:', error);
                });
        }
        
        loadKoldDataWithCallback(callback) {
            const url = `/api/kold-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading KOLD data:', data.error);
                    } else {
                        this.updateKoldChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading KOLD data:', error);
                })
                .finally(() => {
                    if (callback) callback();
                });
        }
        
        loadStorageDataWithCallback(callback) {
            const url = `/api/storage-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading storage data:', data.error);
                    } else {
                        this.updateStorageChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading storage data:', error);
                })
                .finally(() => {
                    if (callback) callback();
                });
        }
        
        loadHistoricalSignals() {
            const url = `/api/historical-signals?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading historical signals:', data.error);
                    } else {
                        // Signal chart removed - no longer updating
                    }
                })
                .catch(error => {
                    console.error('Error loading historical signals:', error);
                });
        }
        
        loadHistoricalSignalsWithCallback(callback) {
            const url = `/api/historical-signals?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading historical signals:', data.error);
                    } else {
                        // Signal chart removed - no longer updating
                    }
                })
                .catch(error => {
                    console.error('Error loading historical signals:', error);
                })
                .finally(() => {
                    if (callback) callback();
                });
        }
        
        loadTemperatureData() {
            const url = `/api/temperature-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading temperature data:', data.error);
                    } else {
                        this.updateTemperatureChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading temperature data:', error);
                });
        }
        
        loadTemperatureDataWithCallback(callback) {
            const url = `/api/temperature-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading temperature data:', data.error);
                    } else {
                        this.updateTemperatureChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading temperature data:', error);
                })
                .finally(() => {
                    if (callback) callback();
                });
        }
        
        loadStormData() {
            const url = `/api/storm-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading storm data:', data.error);
                    } else {
                        this.updateStormChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading storm data:', error);
                });
        }
        
        loadStormDataWithCallback(callback) {
            const url = `/api/storm-data?period=${this.currentTimePeriod}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error loading storm data:', data.error);
                    } else {
                        this.updateStormChart(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading storm data:', error);
                })
                .finally(() => {
                    if (callback) callback();
                });
        }
    
    selectTimePeriod(period) {
        // Don't allow changing if already loading
        if (this.isLoading) {
            return;
        }
        
        // Show loading animation
        this.showLoading();
        
        // Update active button across ALL charts (BOIL, KOLD, EIA, Signal, Temperature, Storm)
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll(`[data-period="${period}"]`).forEach(btn => {
            btn.classList.add('active');
        });
        
        // Update current period
        this.currentTimePeriod = period;
        
        // Track completed requests
        let completedRequests = 0;
        const totalRequests = 6; // BOIL, KOLD, EIA, Signal, Temperature, Storm
        
        const checkAllComplete = () => {
            completedRequests++;
            if (completedRequests === totalRequests) {
                this.hideLoading();
            }
        };
        
        // Reload all chart data
        this.loadBoilDataWithCallback(checkAllComplete);
        this.loadKoldDataWithCallback(checkAllComplete);
        this.loadStorageDataWithCallback(checkAllComplete);
        this.loadHistoricalSignalsWithCallback(checkAllComplete);
        this.loadTemperatureDataWithCallback(checkAllComplete);
        this.loadStormDataWithCallback(checkAllComplete);
    }
    
    showLoading() {
        this.isLoading = true;
        
        // Show loading for all charts except signal chart
        const storageLoading = document.getElementById('storageChartLoading');
        const boilLoading = document.getElementById('boilChartLoading');
        const koldLoading = document.getElementById('koldChartLoading');
        const temperatureLoading = document.getElementById('temperatureChartLoading');
        const stormLoading = document.getElementById('stormChartLoading');
        
        if (storageLoading) storageLoading.style.display = 'flex';
        if (boilLoading) boilLoading.style.display = 'flex';
        if (koldLoading) koldLoading.style.display = 'flex';
        if (temperatureLoading) temperatureLoading.style.display = 'flex';
        if (stormLoading) stormLoading.style.display = 'flex';
        
        // Disable all time period buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.disabled = true;
        });
    }
    
    hideLoading() {
        this.isLoading = false;
        
        // Hide loading for all charts except signal chart
        const storageLoading = document.getElementById('storageChartLoading');
        const boilLoading = document.getElementById('boilChartLoading');
        const koldLoading = document.getElementById('koldChartLoading');
        const temperatureLoading = document.getElementById('temperatureChartLoading');
        const stormLoading = document.getElementById('stormChartLoading');
        
        if (storageLoading) storageLoading.style.display = 'none';
        if (boilLoading) boilLoading.style.display = 'none';
        if (koldLoading) koldLoading.style.display = 'none';
        if (temperatureLoading) temperatureLoading.style.display = 'none';
        if (stormLoading) stormLoading.style.display = 'none';
        
        // Re-enable all time period buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.disabled = false;
        });
    }
    
    updateDashboard(data) {
        // Update signals
        if (data.signals && data.signals.length > 0) {
            const latestSignal = data.signals[data.signals.length - 1];
            this.updateSignals(latestSignal);
            // Signal chart removed - no longer updating
        }
        
        // Update data charts
        if (data.storage_data) {
            this.updateStorageChart(data.storage_data);
        }
        
        if (data.temperature_data) {
            this.updateTemperatureChart(data.temperature_data);
        }
        
        if (data.storm_data) {
            this.updateStormChart(data.storm_data);
        }
        
        // Update portfolio
        if (data.portfolio) {
            this.updatePortfolio(data.portfolio);
        }
        
        // Update trades
        if (data.trades) {
            this.updateTrades(data.trades);
        }
        
        // Update logs
        if (data.logs) {
            this.updateLogs(data.logs);
        }
        
        // Update last update time
        if (data.last_update) {
            document.getElementById('signalUpdate').textContent = 
                `Last update: ${new Date(data.last_update).toLocaleTimeString()}`;
        }
    }
    
    updateSignals(signal) {
        document.getElementById('tempSignal').textContent = signal.temperature_signal.toFixed(3);
        document.getElementById('inventorySignal').textContent = signal.inventory_signal.toFixed(3);
        document.getElementById('stormSignal').textContent = signal.storm_signal.toFixed(3);
        document.getElementById('totalSignal').textContent = signal.total_signal.toFixed(3);
        
        // Update action badge with BULL/BEAR terminology
        const actionBadge = document.getElementById('actionBadge');
        if (signal.action === 'BUY' && signal.symbol) {
            if (signal.symbol === 'BOIL') {
                actionBadge.textContent = 'BULL';
                actionBadge.className = 'action-badge bull';
            } else if (signal.symbol === 'KOLD') {
                actionBadge.textContent = 'BEAR';
                actionBadge.className = 'action-badge bear';
            } else {
                actionBadge.textContent = `BUY ${signal.symbol}`;
                actionBadge.className = 'action-badge buy';
            }
        } else {
            actionBadge.textContent = signal.action;
            actionBadge.className = `action-badge ${signal.action.toLowerCase()}`;
        }
        
        // Add color coding to signal values
        this.colorCodeSignal('tempSignal', signal.temperature_signal);
        this.colorCodeSignal('inventorySignal', signal.inventory_signal);
        this.colorCodeSignal('stormSignal', signal.storm_signal);
        this.colorCodeSignal('totalSignal', signal.total_signal);
        
        // Update signal boundaries with current thresholds
        this.updateSignalBoundaries();
    }
    
    colorCodeSignal(elementId, value) {
        const element = document.getElementById(elementId);
        element.style.color = value > 0 ? '#00ff00' : value < 0 ? '#ff0000' : '#888888';
    }
    
    updateSignalBoundaries() {
        // Update threshold values from config (these would come from the backend)
        const bullThreshold = 0.3;
        const bearThreshold = -0.3;
        
        // Update threshold displays if elements exist
        const configBuyElement = document.getElementById('configBuyThreshold');
        const configSellElement = document.getElementById('configSellThreshold');
        
        if (configBuyElement) {
            configBuyElement.textContent = bullThreshold;
        }
        if (configSellElement) {
            configSellElement.textContent = bearThreshold;
        }
    }
    
    updatePortfolio(portfolio) {
        document.getElementById('totalValue').textContent = 
            `$${portfolio.total_value?.toLocaleString() || '--'}`;
        document.getElementById('cashValue').textContent = 
            `$${portfolio.cash?.toLocaleString() || '--'}`;
        document.getElementById('buyingPower').textContent = 
            `$${portfolio.buying_power?.toLocaleString() || '--'}`;
        document.getElementById('positionCount').textContent = 
            portfolio.positions?.length || '0';
    }
    
    updateTrades(trades) {
        const tradesList = document.getElementById('tradesList');
        
        if (trades.length === 0) {
            tradesList.innerHTML = '<div class="no-trades">No trades yet</div>';
            return;
        }
        
        tradesList.innerHTML = trades.slice(-10).reverse().map(trade => `
            <div class="trade-item ${trade.side}">
                <div class="trade-symbol">${trade.symbol}</div>
                <div class="trade-details">
                    <div>${trade.side.toUpperCase()} ${trade.qty} shares</div>
                    <div>Status: ${trade.status}</div>
                    <div>${new Date(trade.submitted_at).toLocaleString()}</div>
                </div>
            </div>
        `).join('');
    }
    
    updateLogs(logs) {
        const logsList = document.getElementById('logsList');
        
        if (logs.length === 0) {
            logsList.innerHTML = '<div class="no-logs">No logs yet</div>';
            return;
        }
        
        logsList.innerHTML = logs.slice(-20).reverse().map(log => `
            <div class="log-item ${log.level || 'info'}">
                <span class="log-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
    }
    
    updateStatus(status, text) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        statusDot.className = `status-dot ${status}`;
        statusText.textContent = text;
    }
    
    addLog(level, message) {
        // Log functionality removed - no longer displaying logs in UI
        console.log(`[${level.toUpperCase()}] ${message}`);
    }
    
    
    loadLogs() {
        fetch('/api/logs')
            .then(response => response.json())
            .then(logs => {
                if (logs.error) {
                    console.error('Error loading logs:', logs.error);
                } else {
                    this.updateLogs(logs);
                }
            })
            .catch(error => {
                console.error('Error loading logs:', error);
            });
    }
    
    updateLogs(logs) {
        // Log functionality removed - no longer displaying logs in UI
        console.log('Logs updated:', logs.length, 'entries');
    }
    
    setupEventListeners() {
        // Time period selector buttons
        const timeButtons = document.querySelectorAll('.time-btn');
        timeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const period = e.target.getAttribute('data-period');
                this.selectTimePeriod(period);
            });
        });
        
        // Auto-refresh portfolio every 30 seconds
        setInterval(() => {
            this.refreshPortfolio();
            this.loadPositions(); // Also refresh positions
        }, 30000);
        
        // Request update every 10 seconds
        setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.socket.emit('request_update');
            }
        }, 10000);
    }
    
    updateStorageChart(storageData) {
        if (!this.storageChart || !storageData) return;
        
        // Process storage data
        const labels = storageData.map(item => new Date(item.period).toLocaleDateString());
        const values = storageData.map(item => item.value);
        
        this.storageChart.data.labels = labels;
        this.storageChart.data.datasets[0].data = values;
        this.storageChart.update();
    }
    
    updateBoilChart(boilData) {
        if (!this.boilChart || !boilData) return;
        
        // Process BOIL price data
        const labels = boilData.map(item => new Date(item.date).toLocaleDateString());
        const values = boilData.map(item => item.price);
        
        this.boilChart.data.labels = labels;
        this.boilChart.data.datasets[0].data = values;
        this.boilChart.update();
    }
    
    updateKoldChart(koldData) {
        if (!this.koldChart || !koldData) return;
        
        // Process KOLD price data
        const labels = koldData.map(item => new Date(item.date).toLocaleDateString());
        const values = koldData.map(item => item.price);
        
        this.koldChart.data.labels = labels;
        this.koldChart.data.datasets[0].data = values;
        this.koldChart.update();
    }
    
    updateTemperatureChart(temperatureData) {
        if (!this.temperatureChart || !temperatureData) return;
        
        // Process temperature data as time series with all regions
        const labels = temperatureData.map(item => new Date(item.timestamp).toLocaleDateString());
        
        // Get all unique regions from the first data point
        const regions = temperatureData.length > 0 ? Object.keys(temperatureData[0].regional_hdd) : [];
        
        // Create datasets for each region
        const datasets = [];
        
        // Add average HDD dataset
        const avgHddValues = temperatureData.map(item => item.avg_hdd);
        datasets.push({
            label: 'Average HDD',
            data: avgHddValues,
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 3,
            fill: false,
            tension: 0.1,
            pointRadius: 3
        });
        
        // Add regional HDD datasets with city names
        const colors = [
            'rgba(230, 56, 56, 0.6)',      // Red
            'rgba(15, 124, 191, 0.6)',     // Blue
            'rgba(255, 165, 0, 0.6)',      // Orange
            'rgba(153, 102, 255, 0.6)',    // Purple
            'rgba(255, 159, 64, 0.6)'      // Orange
        ];
        
        // Map coordinates to city names
        const regionNames = {
            '39.9526,-75.1652': 'Philadelphia',
            '40.7128,-74.0060': 'New York',
            '41.8781,-87.6298': 'Chicago',
            '42.3314,-83.0458': 'Detroit',
            '42.3601,-71.0589': 'Boston'
        };
        
        regions.forEach((region, index) => {
            const regionValues = temperatureData.map(item => item.regional_hdd[region]);
            const cityName = regionNames[region] || `Region ${region}`;
            datasets.push({
                label: cityName,
                data: regionValues,
                backgroundColor: colors[index % colors.length],
                borderColor: colors[index % colors.length].replace('0.6', '1'),
                borderWidth: 1,
                fill: false,
                tension: 0.1,
                pointRadius: 2
            });
        });
        
        this.temperatureChart.data.labels = labels;
        this.temperatureChart.data.datasets = datasets;
        this.temperatureChart.update();
    }
    
    updateStormChart(stormData) {
        if (!this.stormChart || !stormData) return;
        
        // Process storm data as time series
        const labels = stormData.map(item => new Date(item.timestamp).toLocaleDateString());
        const values = stormData.map(item => item.signal);
        
        // Create enhanced labels with location info for non-zero signals
        const enhancedLabels = stormData.map(item => {
            const date = new Date(item.timestamp).toLocaleDateString();
            if (item.signal > 0) {
                return `${date} (${item.location}, ${item.state})`;
            }
            return date;
        });
        
        this.stormChart.data.labels = enhancedLabels;
        this.stormChart.data.datasets = [{
            label: 'Storm Signal',
            data: values,
            backgroundColor: 'rgba(255, 193, 7, 0.8)',
            borderColor: 'rgba(255, 193, 7, 1)',
            borderWidth: 1
        }];
        
        // Update chart options to show location info in tooltips
        this.stormChart.options.plugins.tooltip = {
            callbacks: {
                title: function(context) {
                    const dataIndex = context[0].dataIndex;
                    const item = stormData[dataIndex];
                    return `${new Date(item.timestamp).toLocaleDateString()} - ${item.location}, ${item.state}`;
                },
                label: function(context) {
                    const dataIndex = context.dataIndex;
                    const item = stormData[dataIndex];
                    return [
                        `Event: ${item.event}`,
                        `Severity: ${item.severity}`,
                        `Signal: ${item.signal.toFixed(3)}`,
                        `Location: ${item.location}, ${item.state}`
                    ];
                }
            }
        };
        
        this.stormChart.update();
    }
}

// Global functions
function refreshPortfolio() {
    fetch('/api/portfolio')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                dashboard.addLog('error', `Portfolio error: ${data.error}`);
            } else {
                dashboard.updatePortfolio(data);
                dashboard.addLog('info', 'Portfolio refreshed');
            }
        })
        .catch(error => {
            console.error('Error refreshing portfolio:', error);
            dashboard.addLog('error', `Failed to refresh portfolio: ${error.message}`);
        });
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new TradingDashboard();
});
