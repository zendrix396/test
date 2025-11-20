"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import fetchApi from "@/lib/api";
import AdminSidebar from "@/components/AdminSidebar/AdminSidebar";
import "../../admin.css";
import "./order-detail.css";

const OrderDetailPage = () => {
  const router = useRouter();
  const params = useParams();
  const orderId = params.id;
  const [order, setOrder] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (user && orderId) {
      loadOrder();
    }
  }, [user, orderId]);

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

  const loadOrder = async () => {
    try {
      setIsLoading(true);
      const data = await fetchApi(`/admin/orders/${orderId}/`);
      setOrder(data);
    } catch (e) {
      console.error("Failed to load order:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      setIsSaving(true);
      await fetchApi(`/admin/orders/${orderId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      await loadOrder();
    } catch (e) {
      console.error("Failed to update order:", e);
      alert("Failed to update order status");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !order) {
    return (
      <div className="admin-order-detail-page">
        <AdminSidebar />
        <main className="admin-main-content">
          <div className="admin-dashboard-loading">
            <p>Loading order...</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="admin-order-detail-page">
      <AdminSidebar />
      <main className="admin-main-content">
        <div className="admin-order-detail-header">
        <button onClick={() => router.push("/admin/order")} className="admin-back-btn">
          ← Back to Orders
        </button>
        <h1>Order {order.order_number || `#${order.id}`}</h1>
      </div>

      <div className="admin-order-detail-content">
        <div className="admin-order-section">
          <h2>Order Information</h2>
          <div className="admin-order-info-grid">
            <div className="admin-order-info-item">
              <label>Status</label>
              <select
                value={order.status}
                onChange={(e) => handleStatusChange(e.target.value)}
                disabled={isSaving}
                className="admin-status-select"
              >
                <option value="PENDING_PAYMENT">Pending Payment</option>
                <option value="PROCESSING">Processing</option>
                <option value="PAID">Paid</option>
                <option value="SHIPPED">Shipped</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
            <div className="admin-order-info-item">
              <label>Total Cost</label>
              <div className="admin-order-value">₹{parseFloat(order.total_cost).toLocaleString()}</div>
            </div>
            <div className="admin-order-info-item">
              <label>Payment Method</label>
              <div>{order.payment_method}</div>
            </div>
            <div className="admin-order-info-item">
              <label>Created At</label>
              <div>{new Date(order.created_at).toLocaleString()}</div>
            </div>
          </div>
        </div>

        <div className="admin-order-section">
          <h2>Customer Information</h2>
          <div className="admin-order-info-grid">
            <div className="admin-order-info-item">
              <label>User</label>
              <div>{order.user?.username || "Guest"}</div>
            </div>
            <div className="admin-order-info-item">
              <label>Email</label>
              <div>{order.user?.email || order.shipping?.email || "N/A"}</div>
            </div>
            <div className="admin-order-info-item">
              <label>Phone</label>
              <div>{order.shipping?.phone || "N/A"}</div>
            </div>
          </div>
        </div>

        <div className="admin-order-section">
          <h2>Shipping Address</h2>
          <div className="admin-order-address">
            <p>{order.shipping?.full_name}</p>
            <p>{order.shipping?.address_line1}</p>
            {order.shipping?.address_line2 && <p>{order.shipping.address_line2}</p>}
            <p>{order.shipping?.city}, {order.shipping?.state} {order.shipping?.postal_code}</p>
            <p>{order.shipping?.country}</p>
            {order.shipping?.courier_name && (
              <div className="admin-order-tracking">
                <p><strong>Courier:</strong> {order.shipping.courier_name}</p>
                {order.shipping.tracking_number && (
                  <p><strong>Tracking:</strong> {order.shipping.tracking_number}</p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="admin-order-section">
          <h2>Order Items</h2>
          <div className="admin-order-items">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Quantity</th>
                  <th>Unit Price</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {order.items?.map((item) => (
                  <tr key={item.id}>
                    <td>{item.variant?.name || "N/A"}</td>
                    <td>{item.variant?.sku || "N/A"}</td>
                    <td>{item.quantity}</td>
                    <td>₹{parseFloat(item.unit_price).toLocaleString()}</td>
                    <td>₹{parseFloat(item.line_total).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="admin-order-section">
          <h2>Financial Details</h2>
          <div className="admin-order-financials">
            <div className="admin-order-financial-item">
              <span>Subtotal</span>
              <span>₹{parseFloat(order.total_cost).toLocaleString()}</span>
            </div>
            {order.discount_amount && parseFloat(order.discount_amount) > 0 && (
              <div className="admin-order-financial-item">
                <span>Discount</span>
                <span>-₹{parseFloat(order.discount_amount).toLocaleString()}</span>
              </div>
            )}
            {order.wallet_applied_amount && parseFloat(order.wallet_applied_amount) > 0 && (
              <div className="admin-order-financial-item">
                <span>Wallet Applied</span>
                <span>-₹{parseFloat(order.wallet_applied_amount).toLocaleString()}</span>
              </div>
            )}
            <div className="admin-order-financial-item admin-order-total">
              <span>Total</span>
              <span>₹{parseFloat(order.total_cost).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>
      </main>
    </div>
  );
};

export default OrderDetailPage;

