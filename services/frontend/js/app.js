/**
 * METAR Collector Dashboard Application
 */

const API_BASE = '/api/v1';

function dashboard() {
    return {
        // State
        activeTab: 'airports',
        airports: [],
        latestMetars: {},
        history: [],
        historyPage: 1,
        historyPerPage: 20,
        historyTotal: 0,
        selectedAirport: '',
        metrics: {},
        collectionStatus: null,
        healthStatus: 'checking...',
        currentTime: '',
        toasts: [],

        // Forms
        newAirport: {
            icao_code: '',
            name: '',
            latitude: null,
            longitude: null,
            elevation_ft: null
        },
        exportParams: {
            icao: '',
            start_date: '',
            end_date: '',
            format: 'csv'
        },

        // Initialize
        async init() {
            this.updateTime();
            setInterval(() => this.updateTime(), 1000);

            await this.checkHealth();
            await this.loadAirports();
            await this.loadLatestMetars();
            await this.loadMetrics();
            await this.loadCollectionStatus();

            // Refresh data periodically
            setInterval(() => this.refresh(), 60000);
        },

        // Update current time
        updateTime() {
            const now = new Date();
            this.currentTime = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        },

        // Refresh data
        async refresh() {
            await this.loadLatestMetars();
            await this.loadMetrics();
            await this.loadCollectionStatus();
            await this.checkHealth();
        },

        // API calls
        async checkHealth() {
            try {
                const response = await fetch(`${API_BASE}/health`);
                const data = await response.json();
                this.healthStatus = data.status;
            } catch (e) {
                this.healthStatus = 'error';
            }
        },

        async loadAirports() {
            try {
                const response = await fetch(`${API_BASE}/airports`);
                const data = await response.json();
                this.airports = data.airports || [];
            } catch (e) {
                this.showToast('Failed to load airports', 'error');
            }
        },

        async loadLatestMetars() {
            try {
                const response = await fetch(`${API_BASE}/metar/bulk/latest`);
                const data = await response.json();

                // Convert to map for easy lookup
                this.latestMetars = {};
                for (const obs of data.observations || []) {
                    this.latestMetars[obs.icao_code] = obs;
                }
            } catch (e) {
                console.error('Failed to load METARs', e);
            }
        },

        async loadMetrics() {
            try {
                const response = await fetch(`${API_BASE}/metrics`);
                this.metrics = await response.json();
            } catch (e) {
                console.error('Failed to load metrics', e);
            }
        },

        async loadCollectionStatus() {
            try {
                const response = await fetch(`${API_BASE}/collection/status`);
                this.collectionStatus = await response.json();
            } catch (e) {
                console.error('Failed to load collection status', e);
            }
        },

        async loadHistory() {
            if (!this.selectedAirport) {
                this.history = [];
                return;
            }

            try {
                const params = new URLSearchParams({
                    page: this.historyPage,
                    per_page: this.historyPerPage
                });
                const response = await fetch(`${API_BASE}/metar/${this.selectedAirport}/history?${params}`);
                const data = await response.json();
                this.history = data.observations || [];
                this.historyTotal = data.total || 0;
            } catch (e) {
                this.showToast('Failed to load history', 'error');
            }
        },

        async addAirport() {
            if (!this.newAirport.icao_code || this.newAirport.icao_code.length !== 4) {
                this.showToast('ICAO code must be exactly 4 letters', 'error');
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/airports`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        icao_code: this.newAirport.icao_code.toUpperCase(),
                        name: this.newAirport.name || null,
                        latitude: this.newAirport.latitude || null,
                        longitude: this.newAirport.longitude || null,
                        elevation_ft: this.newAirport.elevation_ft || null
                    })
                });

                if (response.ok) {
                    this.showToast(`Airport ${this.newAirport.icao_code.toUpperCase()} added successfully`);
                    this.newAirport = { icao_code: '', name: '', latitude: null, longitude: null, elevation_ft: null };
                    await this.loadAirports();
                    this.activeTab = 'airports';
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || 'Failed to add airport', 'error');
                }
            } catch (e) {
                this.showToast('Failed to add airport', 'error');
            }
        },

        async deleteAirport(icao) {
            if (!confirm(`Are you sure you want to remove ${icao}?`)) {
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/airports/${icao}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    this.showToast(`Airport ${icao} removed`);
                    await this.loadAirports();
                    await this.loadLatestMetars();
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || 'Failed to remove airport', 'error');
                }
            } catch (e) {
                this.showToast('Failed to remove airport', 'error');
            }
        },

        viewHistory(icao) {
            this.selectedAirport = icao;
            this.historyPage = 1;
            this.activeTab = 'history';
            this.loadHistory();
        },

        exportData() {
            const params = new URLSearchParams();
            if (this.exportParams.icao) params.append('icao', this.exportParams.icao);
            if (this.exportParams.start_date) params.append('start_date', this.exportParams.start_date);
            if (this.exportParams.end_date) params.append('end_date', this.exportParams.end_date);

            const url = `${API_BASE}/export/${this.exportParams.format}?${params}`;
            window.open(url, '_blank');
        },

        // Helpers
        getLatestMetar(icao) {
            return this.latestMetars[icao] || null;
        },

        getFlightCategoryClass(category) {
            const classes = {
                'VFR': 'flight-vfr',
                'MVFR': 'flight-mvfr',
                'IFR': 'flight-ifr',
                'LIFR': 'flight-lifr'
            };
            return classes[category] || 'bg-gray-200 text-gray-700';
        },

        formatTime(isoString) {
            if (!isoString) return '-';
            const date = new Date(isoString);
            return date.toISOString().replace('T', ' ').substring(0, 16) + 'Z';
        },

        formatNumber(num) {
            return new Intl.NumberFormat().format(num);
        },

        formatWind(obs) {
            if (!obs.wind) return '-';
            const wind = obs.wind;
            if (wind.is_calm) return 'Calm';

            let result = '';
            if (wind.is_variable) {
                result = `VRB ${wind.speed_kt}kt`;
            } else if (wind.direction_degrees !== null) {
                result = `${String(wind.direction_degrees).padStart(3, '0')}° @ ${wind.speed_kt}kt`;
            }
            if (wind.gust_kt) {
                result += ` G${wind.gust_kt}`;
            }
            return result || '-';
        },

        formatVisibility(obs) {
            if (obs.visibility_statute_mi !== null) {
                return `${obs.visibility_statute_mi} SM`;
            }
            if (obs.visibility_meters !== null) {
                return `${obs.visibility_meters}m`;
            }
            return '-';
        },

        get lastCollectionStatus() {
            const last = this.collectionStatus?.last_collection;
            if (!last) return 'No data';

            const time = this.formatTime(last.completed_at || last.started_at);
            return `${last.status} - ${time}`;
        },

        // Toast notifications
        showToast(message, type = 'success') {
            const id = Date.now();
            const toast = { id, message, type, visible: true };
            this.toasts.push(toast);

            setTimeout(() => {
                const index = this.toasts.findIndex(t => t.id === id);
                if (index !== -1) {
                    this.toasts[index].visible = false;
                    setTimeout(() => {
                        this.toasts = this.toasts.filter(t => t.id !== id);
                    }, 300);
                }
            }, 3000);
        }
    };
}
