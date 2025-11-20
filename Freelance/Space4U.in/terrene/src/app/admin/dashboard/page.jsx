"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import fetchApi from "@/lib/api";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import AdminSidebar from "@/components/AdminSidebar/AdminSidebar";
import "../admin.css";
import "./dashboard.css";

const fetcher = (url) => fetchApi(url);

const AdminDashboard = () => {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("overview");
  const [user, setUser] = useState(null);
  const [auditPage, setAuditPage] = useState(1);

  // Auth check
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
      if (!token) {
        router.push("/admin");
        return;
      }
      const check = await fetchApi("/admin/check-superuser/");
      if (!check.is_superuser) {
        router.push("/admin");
        return;
      }
      setUser(check);
    } catch (e) {
      router.push("/admin");
    }
  };

  // Data fetching with SWR
  const { data: stats, error: statsError } = useSWR(
    user ? "/admin/dashboard-stats/" : null,
    fetcher,
    { refreshInterval: 30000 }
  );

  const { data: ordersData } = useSWR(
    user && (activeTab === "orders" || activeTab === "overview") ? "/admin/orders/?page_size=10" : null,
    fetcher
  );

  const { data: usersData } = useSWR(
    user && activeTab === "users" ? "/admin/users/?page_size=10" : null,
    fetcher
  );

  const { data: productsData } = useSWR(
    user && activeTab === "products" ? "/admin/products/?page_size=10" : null,
    fetcher
  );

  const { data: auditData } = useSWR(
    user && activeTab === "audit" ? `/admin/audit-log/?page=${auditPage}&page_size=100` : null,
    fetcher
  );

  const orders = ordersData?.results || [];
  const users = usersData?.results || [];
  const products = productsData?.results || [];
  const auditLogs = auditData?.results || [];
  const auditTotal = auditData?.total || 0;
  const isLoading = !stats && !statsError;

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
    }
    router.push("/admin");
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="admin-dashboard-loading">
          <p>Loading...</p>
        </div>
      );
    }

    if (statsError) {
      return (
        <div className="admin-dashboard-error">
          <p>Failed to load dashboard data. Please try refreshing.</p>
        </div>
      );
    }

    return (
      <>
        <div className="admin-dashboard-tabs">
          <button
            className={activeTab === "overview" ? "active" : ""}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          <button
            className={activeTab === "orders" ? "active" : ""}
            onClick={() => setActiveTab("orders")}
          >
            Orders
          </button>
          <button
            className={activeTab === "users" ? "active" : ""}
            onClick={() => setActiveTab("users")}
          >
            Users
          </button>
          <button
            className={activeTab === "products" ? "active" : ""}
            onClick={() => setActiveTab("products")}
          >
            Products
          </button>
          <button
            className={activeTab === "analytics" ? "active" : ""}
            onClick={() => setActiveTab("analytics")}
          >
            Analytics
          </button>
          <button
            className={activeTab === "audit" ? "active" : ""}
            onClick={() => setActiveTab("audit")}
          >
            Audit Log
          </button>
        </div>

        <div className="admin-dashboard-content">
          {activeTab === "overview" && stats && (
            <div className="admin-overview">
              <div className="admin-stats-grid">
                <div className="admin-stat-card">
                  <div className="admin-stat-label">Total Orders</div>
                  <div className="admin-stat-value">{stats.orders.total}</div>
                  <div className="admin-stat-change">
                    <span className="positive">+{stats.orders.today} today</span>
                  </div>
                </div>
                <div className="admin-stat-card">
                  <div className="admin-stat-label">Total Revenue</div>
                  <div className="admin-stat-value">₹{parseFloat(stats.revenue.total).toLocaleString()}</div>
                  <div className="admin-stat-change">
                    <span className="positive">₹{parseFloat(stats.revenue.today).toLocaleString()} today</span>
                  </div>
                </div>
                <div className="admin-stat-card">
                  <div className="admin-stat-label">Total Users</div>
                  <div className="admin-stat-value">{stats.users.total}</div>
                  <div className="admin-stat-change">
                    <span className="positive">+{stats.users.today} today</span>
                  </div>
                </div>
                <div className="admin-stat-card">
                  <div className="admin-stat-label">Total Products</div>
                  <div className="admin-stat-value">{stats.products.total}</div>
                  <div className="admin-stat-change">
                    <span>{stats.products.published} published</span>
                  </div>
                </div>
              </div>

              <div className="admin-overview-sections">
                <div className="admin-section-card">
                  <h2>Recent Orders</h2>
                  <div className="admin-table-container">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Order #</th>
                          <th>User</th>
                          <th>Status</th>
                          <th>Amount</th>
                          <th>Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.orders.recent.map((order) => (
                          <tr key={order.id}>
                            <td>{order.order_number || `#${order.id}`}</td>
                            <td>{order.user__username || "Guest"}</td>
                            <td>
                              <span className={`admin-status-badge status-${order.status.toLowerCase()}`}>
                                {order.status}
                              </span>
                            </td>
                            <td>₹{parseFloat(order.total_cost).toLocaleString()}</td>
                            <td>{new Date(order.created_at).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="admin-section-card">
                  <h2>Orders by Status</h2>
                  <div className="admin-status-list">
                    {stats.orders.by_status.map((item) => (
                      <div key={item.status} className="admin-status-item">
                        <span className="admin-status-name">{item.status}</span>
                        <span className="admin-status-count">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {stats.carts && (
                  <div className="admin-section-card">
                    <h2>Cart Analytics</h2>
                    <div className="admin-stats-grid">
                      <div className="admin-stat-card">
                        <div className="admin-stat-label">Abandoned Carts</div>
                        <div className="admin-stat-value">{stats.carts.abandoned_count}</div>
                        <div className="admin-stat-change">
                          <span>Value: ₹{parseFloat(stats.carts.abandoned_value).toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="admin-stat-card">
                        <div className="admin-stat-label">Repeat Customers</div>
                        <div className="admin-stat-value">{stats.carts.repeat_customers}</div>
                        <div className="admin-stat-change">
                          <span>Customers with 2+ orders</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "orders" && (
            <div className="admin-orders">
              <div className="admin-section-card">
                <h2>All Orders</h2>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Order #</th>
                        <th>User</th>
                        <th>Status</th>
                        <th>Amount</th>
                        <th>Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.map((order) => (
                        <tr key={order.id}>
                          <td>{order.order_number || `#${order.id}`}</td>
                          <td>{order.user__username || "Guest"}</td>
                          <td>
                            <span className={`admin-status-badge status-${order.status.toLowerCase()}`}>
                              {order.status}
                            </span>
                          </td>
                          <td>₹{parseFloat(order.total_cost).toLocaleString()}</td>
                          <td>{new Date(order.created_at).toLocaleDateString()}</td>
                          <td>
                            <button
                              className="admin-action-btn"
                              onClick={() => router.push(`/admin/order/${order.id}`)}
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === "users" && (
            <div className="admin-users">
              <div className="admin-section-card">
                <h2>All Users</h2>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Loyalty Points</th>
                        <th>Tier</th>
                        <th>Joined</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id}>
                          <td>{user.username}</td>
                          <td>{user.email}</td>
                          <td>{user.loyalty_points}</td>
                          <td>
                            <span className="admin-tier-badge">{user.loyalty_tier}</span>
                          </td>
                          <td>{new Date(user.date_joined).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === "products" && (
            <div className="admin-products">
              <div className="admin-section-card">
                <h2>All Products</h2>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>SKU</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Variants</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.map((product) => (
                        <tr key={product.id}>
                          <td>{product.name}</td>
                          <td>{product.sku}</td>
                          <td>{product.category || "N/A"}</td>
                          <td>
                            <span className={`admin-status-badge status-${product.status.toLowerCase()}`}>
                              {product.status}
                            </span>
                          </td>
                          <td>{product.variants_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === "analytics" && stats && (
            <div className="admin-analytics">
              <div className="admin-section-card">
                <h2>Real-Time Sales Dashboard</h2>
                <div className="admin-analytics-grid">
                  <div className="admin-analytics-item">
                    <div className="admin-analytics-label">Today</div>
                    <div className="admin-analytics-value">₹{parseFloat(stats.revenue.today).toLocaleString()}</div>
                  </div>
                  <div className="admin-analytics-item">
                    <div className="admin-analytics-label">This Week</div>
                    <div className="admin-analytics-value">₹{parseFloat(stats.revenue.this_week).toLocaleString()}</div>
                  </div>
                  <div className="admin-analytics-item">
                    <div className="admin-analytics-label">This Month</div>
                    <div className="admin-analytics-value">₹{parseFloat(stats.revenue.this_month).toLocaleString()}</div>
                  </div>
                </div>
                {stats.sales_data && stats.sales_data.length > 0 && (
                  <div className="admin-chart-container">
                    <h3 style={{ marginBottom: '1rem', color: 'var(--base-200)' }}>Last 7 Days Revenue</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={stats.sales_data.map(item => ({
                        date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                        revenue: parseFloat(item.revenue),
                        orders: item.orders
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="date" stroke="var(--base-200)" />
                        <YAxis yAxisId="left" stroke="var(--base-200)" />
                        <YAxis yAxisId="right" orientation="right" stroke="var(--base-200)" />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: 'rgba(20, 19, 19, 0.95)', 
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            borderRadius: '0.9rem',
                            color: 'var(--base-100)'
                          }} 
                        />
                        <Line yAxisId="left" type="monotone" dataKey="revenue" stroke="rgba(122, 231, 128, 0.8)" strokeWidth={2} name="Revenue (₹)" />
                        <Line yAxisId="right" type="monotone" dataKey="orders" stroke="rgba(135, 206, 235, 0.8)" strokeWidth={2} name="Orders" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
                <div className="admin-chart-container" style={{ marginTop: '2rem' }}>
                  <h3 style={{ marginBottom: '1rem', color: 'var(--base-200)' }}>Revenue Comparison</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={[
                      { name: 'Today', revenue: parseFloat(stats.revenue.today) },
                      { name: 'This Week', revenue: parseFloat(stats.revenue.this_week) },
                      { name: 'This Month', revenue: parseFloat(stats.revenue.this_month) },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                      <XAxis dataKey="name" stroke="var(--base-200)" />
                      <YAxis stroke="var(--base-200)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(20, 19, 19, 0.95)', 
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '0.9rem',
                          color: 'var(--base-100)'
                        }} 
                      />
                      <Bar dataKey="revenue" fill="rgba(242, 237, 230, 0.6)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="admin-section-card">
                <h2>User Growth</h2>
                <div className="admin-analytics-grid">
                  <div className="admin-analytics-item">
                    <div className="admin-analytics-label">Today</div>
                    <div className="admin-analytics-value">+{stats.users.today}</div>
                  </div>
                  <div className="admin-analytics-item">
                    <div className="admin-analytics-label">This Week</div>
                    <div className="admin-analytics-value">+{stats.users.this_week}</div>
                  </div>
                  <div className="admin-analytics-item">
                    <div className="admin-analytics-label">This Month</div>
                    <div className="admin-analytics-value">+{stats.users.this_month}</div>
                  </div>
                </div>
                <div className="admin-chart-container">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={[
                      { name: 'Today', users: stats.users.today },
                      { name: 'This Week', users: stats.users.this_week },
                      { name: 'This Month', users: stats.users.this_month },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                      <XAxis dataKey="name" stroke="var(--base-200)" />
                      <YAxis stroke="var(--base-200)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(20, 19, 19, 0.95)', 
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '0.9rem',
                          color: 'var(--base-100)'
                        }} 
                      />
                      <Line type="monotone" dataKey="users" stroke="rgba(122, 231, 128, 0.8)" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="admin-section-card">
                <h2>Orders by Status</h2>
                <div className="admin-chart-container">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={stats.orders.by_status.map(item => ({
                      name: item.status.replace(/_/g, ' '),
                      count: item.count
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                      <XAxis dataKey="name" stroke="var(--base-200)" />
                      <YAxis stroke="var(--base-200)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(20, 19, 19, 0.95)', 
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '0.9rem',
                          color: 'var(--base-100)'
                        }} 
                      />
                      <Bar dataKey="count" fill="rgba(135, 206, 235, 0.6)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {activeTab === "audit" && (
            <div className="admin-audit">
              <div className="admin-section-card">
                <h2>Admin Activity Log</h2>
                <div className="admin-audit-info">
                  <p>Total Activities: {auditTotal}</p>
                </div>
                <div className="admin-table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>User</th>
                        <th>Action</th>
                        <th>Object</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.length === 0 ? (
                        <tr>
                          <td colSpan="5" style={{ textAlign: 'center', padding: '2rem' }}>
                            No audit logs found
                          </td>
                        </tr>
                      ) : (
                        auditLogs.map((log) => (
                          <tr key={log.id}>
                            <td>{new Date(log.action_time).toLocaleString()}</td>
                            <td>{log.user}</td>
                            <td>
                              <span className={`admin-status-badge status-${log.action_name.toLowerCase()}`}>
                                {log.action_name}
                              </span>
                            </td>
                            <td>
                              {log.content_type ? `${log.content_type} #${log.object_id}` : 'N/A'}
                            </td>
                            <td className="admin-audit-message">{log.change_message || log.object_repr}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
                {auditTotal > 0 && (
                  <div className="admin-pagination">
                    <button
                      className="admin-action-btn"
                      onClick={() => setAuditPage(Math.max(1, auditPage - 1))}
                      disabled={auditPage === 1}
                    >
                      Previous
                    </button>
                    <span>Page {auditPage} of {Math.ceil(auditTotal / 100)}</span>
                    <button
                      className="admin-action-btn"
                      onClick={() => setAuditPage(auditPage + 1)}
                      disabled={auditPage >= Math.ceil(auditTotal / 100)}
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </>
    );
  };

  if (isLoading && !stats) {
    return (
      <div className="admin-dashboard-page">
        <div className="admin-dashboard-loading">
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard-page">
      <AdminSidebar />
      <main className="admin-main-content">
        <div className="admin-dashboard-header">
          <div className="admin-dashboard-header-content">
            <h1>Admin Dashboard</h1>
            <div className="admin-dashboard-header-actions">
              <span className="admin-user-info">Welcome, {user?.username}</span>
              <button onClick={handleLogout} className="admin-logout-btn">Logout</button>
            </div>
          </div>
        </div>

        {/* Page content */}
        <div className="admin-dashboard-content">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default AdminDashboard;

