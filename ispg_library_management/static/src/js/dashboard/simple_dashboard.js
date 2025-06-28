/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

class SimpleLibraryDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            dashboardData: null,
            chartData: null,
            loading: true,
        });
        
        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            const [dashboardData, chartData] = await Promise.all([
                this.orm.call("library.dashboard", "get_dashboard_data", []),
                this.orm.call("library.dashboard", "get_chart_data", [])
            ]);
            
            this.state.dashboardData = dashboardData;
            this.state.chartData = chartData;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.loading = false;
        }
    }

    async refreshData() {
        this.state.loading = true;
        await this.loadDashboardData();
    }

    getStatusColor(status) {
        const colors = {
            'active': 'success',
            'expired': 'danger',
            'pending': 'warning',
            'borrowed': 'info',
            'returned': 'success',
            'overdue': 'danger'
        };
        return colors[status] || 'secondary';
    }

    getStatusIcon(status) {
        const icons = {
            'active': 'fa-check-circle',
            'expired': 'fa-times-circle',
            'pending': 'fa-clock-o',
            'borrowed': 'fa-book',
            'returned': 'fa-check',
            'overdue': 'fa-exclamation-triangle'
        };
        return icons[status] || 'fa-circle';
    }

    calculatePercentage(value, total) {
        if (total === 0) return 0;
        return Math.round((value / total) * 100);
    }

    formatNumber(num) {
        return num.toLocaleString();
    }
}

SimpleLibraryDashboard.template = "simple_library_dashboard";
SimpleLibraryDashboard.components = { Layout };

// Dashboard template
registry.category("actions").add("simple_library_dashboard", SimpleLibraryDashboard);

export default SimpleLibraryDashboard; 