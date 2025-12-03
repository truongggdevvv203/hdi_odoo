/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ShippingDashboardComponent extends Component {
    static template = "hdi_sale.ShippingDashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        // Try to get bus and action services, but don't fail if unavailable
        try {
            this.bus = useService("bus_service");
        } catch (e) {
            this.bus = null;
            console.warn("bus_service not available");
        }

        try {
            this.action = useService("action");
        } catch (e) {
            this.action = null;
            console.warn("action service not available");
        }

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
            loading: true,
            userId: null
        });

        onWillStart(async () => {
            try {
                // Get user ID using orm call to custom method
                await this.loadUserId();

                console.log("User ID loaded:", this.state.userId);

                if (!this.state.userId) {
                    this.notification.add(_t("Unable to identify user session"), { type: "warning" });
                    this.state.loading = false;
                    return;
                }

                await this.loadDashboardData();
                if (this.bus && this.state.userId) {
                    this.subscribeToUpdates();
                }
            } catch (error) {
                console.error("Error in onWillStart:", error);
                this.notification.add(_t("Error initializing dashboard: ") + error.message, { type: "danger" });
                this.state.loading = false;
            }
        });

        onMounted(() => {
            this.renderChart();
        });

        onWillUnmount(() => {
            if (this.bus && this.state.userId) {
                this.unsubscribeFromUpdates();
            }
        });
    }

    async loadUserId() {
        try {
            // Call custom method on res.users to get current user ID
            const userId = await this.orm.call("res.users", "get_current_user_id", []);
            if (userId) {
                this.state.userId = userId;
                console.log("User ID from orm.call:", this.state.userId);
            } else {
                console.error("get_current_user_id returned null or undefined");
            }
        } catch (error) {
            console.error("Error loading user ID:", error);
            // Try alternative method - search for current user
            try {
                const users = await this.orm.searchRead("res.users", [], ["id"], { limit: 1 });
                if (users && users.length > 0) {
                    this.state.userId = users[0].id;
                    console.log("User ID from searchRead:", this.state.userId);
                }
            } catch (fallbackError) {
                console.error("Fallback method also failed:", fallbackError);
            }
        }
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;

            if (!this.state.userId) {
                this.notification.add(_t("User not identified"), { type: "warning" });
                return;
            }

            console.log("Loading dashboard data for user:", this.state.userId);

            // Create a new dashboard record to get computed values
            // orm.create returns an array of IDs
            const dashboardIds = await this.orm.create("shipping.order.dashboard", [{}]);
            const dashboardId = dashboardIds[0]; // Get the first ID from the array

            console.log("Dashboard ID created:", dashboardId);

            const data = await this.orm.read("shipping.order.dashboard", [dashboardId], [
                'total_orders', 'delivered_orders', 'pending_orders', 'cancelled_orders',
                'success_rate', 'waiting_pickup_orders', 'in_transit_orders',
                'return_orders', 'forwarded_orders', 'chart_data'
            ]);

            if (data && data.length > 0) {
                this.state.dashboardData = data[0];
                console.log("Dashboard data loaded:", this.state.dashboardData);
            }

            // Clean up the temporary record
            await this.orm.unlink("shipping.order.dashboard", [dashboardId]);

        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add(_t("Error loading dashboard data: ") + error.message, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    subscribeToUpdates() {
        if (!this.bus || !this.state.userId) return;

        try {
            // Subscribe to shipping order updates for current user
            this.bus.addEventListener("notification", (notification) => {
                if (notification.payload &&
                    notification.payload.type === "shipping_order_update" &&
                    notification.payload.userId === this.state.userId) {
                    this.handleRealtimeUpdate(notification.payload);
                }
            });
            console.log("Subscribed to bus updates for user:", this.state.userId);
        } catch (error) {
            console.warn("Error subscribing to updates:", error);
        }
    }

    unsubscribeFromUpdates() {
        if (!this.bus || !this.state.userId) return;

        try {
            // Cleanup will be handled automatically by OWL lifecycle
            console.log("Unsubscribing from bus updates");
        } catch (error) {
            console.warn("Error unsubscribing from updates:", error);
        }
    }

    async handleRealtimeUpdate(payload) {
        // Reload dashboard data when receiving real-time updates
        await this.loadDashboardData();
        this.renderChart();

        // Show a brief notification about the update
        const message = payload.message || _t("Dashboard updated");
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
        if (!this.action || !this.state.userId) return;

        this.action.doAction({
            name: _t("All Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "list,form",
            domain: [['sender_id', '=', this.state.userId]],
        });
    }

    onViewDeliveredOrders() {
        if (!this.action || !this.state.userId) return;

        this.action.doAction({
            name: _t("Delivered Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "list,form",
            domain: [['sender_id', '=', this.state.userId], ['state', '=', 'delivered']],
        });
    }

    onViewPendingOrders() {
        if (!this.action || !this.state.userId) return;

        this.action.doAction({
            name: _t("Pending Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "list,form",
            domain: [['sender_id', '=', this.state.userId], ['state', 'in', ['waiting_pickup', 'in_transit', 'forwarded']]],
        });
    }

    onViewCancelledOrders() {
        if (!this.action || !this.state.userId) return;

        this.action.doAction({
            name: _t("Cancelled Orders"),
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "list,form",
            domain: [['sender_id', '=', this.state.userId], ['state', '=', 'cancelled']],
        });
    }
}

registry.category("actions").add("hdi_sale.dashboard_action", ShippingDashboardComponent);