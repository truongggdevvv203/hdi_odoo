/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ShippingDashboardComponent extends Component {
    static template = "hdi_sale.ShippingDashboard";

    setup() {
        this.orm = useService("orm");
        this.bus = useService("bus_service");
        this.notification = useService("notification");
        
        this.state = useState({
            dashboardData: {
                total_orders: 0,
                delivered_orders: 0,
                pending_orders: 0,
                cancelled_orders: 0,
                success_rate: 0,
                waiting_pickup_orders: 0,
                in_transit_orders: 0,
                return_orders: 0,
                forwarded_orders: 0,
                chart_data: '{"pie_data": [], "total": 0}'
            },
            loading: true
        });

        onWillStart(async () => {
            await this.loadDashboardData();
            this.subscribeToUpdates();
        });

        onMounted(() => {
            this.renderChart();
        });

        onWillUnmount(() => {
            this.unsubscribeFromUpdates();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            
            // Create a new dashboard record to get computed values
            const dashboardId = await this.orm.create("shipping.order.dashboard", {});
            const data = await this.orm.read("shipping.order.dashboard", [dashboardId], [
                'total_orders', 'delivered_orders', 'pending_orders', 'cancelled_orders',
                'success_rate', 'waiting_pickup_orders', 'in_transit_orders', 
                'return_orders', 'forwarded_orders', 'chart_data'
            ]);
            
            if (data.length > 0) {
                this.state.dashboardData = data[0];
            }
            
            // Clean up the temporary record
            await this.orm.unlink("shipping.order.dashboard", [dashboardId]);
            
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add(_t("Error loading dashboard data"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    subscribeToUpdates() {
        // Subscribe to shipping order updates for current user
        const userId = this.env.services.user.userId;
        this.bus.subscribe(`shipping_order_update_${userId}`, (notification) => {
            this.handleRealtimeUpdate(notification.detail);
        });
    }

    unsubscribeFromUpdates() {
        const userId = this.env.services.user.userId;
        this.bus.unsubscribe(`shipping_order_update_${userId}`);
    }

    async handleRealtimeUpdate(notification) {
        // Reload dashboard data when receiving real-time updates
        await this.loadDashboardData();
        this.renderChart();
        
        // Show a brief notification about the update
        const message = notification.message || _t("Dashboard updated");
        this.notification.add(message, { 
            type: "info", 
            sticky: false,
            timeout: 3000
        });
    }

    renderChart() {
        const chartContainer = document.getElementById('realtimePieChart');
        if (!chartContainer || this.state.loading) return;

        try {
            const chartData = JSON.parse(this.state.dashboardData.chart_data || '{"pie_data": [], "total": 0}');
            
            if (chartData.pie_data && chartData.pie_data.length > 0) {
                // Create a simple HTML pie chart representation
                let chartHtml = '<div class="chart-legend">';
                chartData.pie_data.forEach(item => {
                    if (item.value > 0) {
                        const percentage = chartData.total > 0 ? (item.value / chartData.total * 100).toFixed(1) : 0;
                        chartHtml += `
                            <div class="legend-item mb-2" style="display: flex; align-items: center;">
                                <div style="width: 16px; height: 16px; background-color: ${item.color}; margin-right: 8px; border-radius: 2px;"></div>
                                <span style="flex: 1;">${item.label}</span>
                                <strong>${item.value} (${percentage}%)</strong>
                            </div>
                        `;
                    }
                });
                chartHtml += '</div>';
                
                chartContainer.innerHTML = chartHtml;
            } else {
                chartContainer.innerHTML = '<p class="text-muted text-center">Chưa có dữ liệu</p>';
            }
        } catch (error) {
            console.error("Error rendering chart:", error);
            chartContainer.innerHTML = '<p class="text-danger text-center">Lỗi hiển thị biểu đồ</p>';
        }
    }

    async onRefreshClick() {
        await this.loadDashboardData();
        this.renderChart();
        this.notification.add(_t("Dashboard refreshed"), { type: "success", timeout: 2000 });
    }

    // Drill-down actions
    onViewAllOrders() {
        this.env.services.action.doAction({
            name: _t("All Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "tree,form",
            domain: [['sender_id', '=', this.env.services.user.userId]],
        });
    }

    onViewDeliveredOrders() {
        this.env.services.action.doAction({
            name: _t("Delivered Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "tree,form",
            domain: [['sender_id', '=', this.env.services.user.userId], ['state', '=', 'delivered']],
        });
    }

    onViewPendingOrders() {
        this.env.services.action.doAction({
            name: _t("Pending Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "tree,form",
            domain: [['sender_id', '=', this.env.services.user.userId], ['state', 'in', ['waiting_pickup', 'in_transit', 'forwarded']]],
        });
    }

    onViewCancelledOrders() {
        this.env.services.action.doAction({
            name: _t("Cancelled Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "tree,form",
            domain: [['sender_id', '=', this.env.services.user.userId], ['state', '=', 'cancelled']],
        });
    }
}

registry.category("actions").add("hdi_sale.dashboard_action", ShippingDashboardComponent);