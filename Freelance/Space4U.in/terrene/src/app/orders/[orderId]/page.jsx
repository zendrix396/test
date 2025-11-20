"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";
import "../orders.css";
import "./order-detail.css";

const OrderDetailPage = () => {
  const { orderId } = useParams();
  const { user } = useUser();
  const [order, setOrder] = useState(null);
  const [trackingData, setTrackingData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTrackingLoading, setIsTrackingLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDownloadingInvoice, setIsDownloadingInvoice] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  useEffect(() => {
    if (!user || !orderId) {
      setIsLoading(false);
      return;
    }

    const fetchOrder = async () => {
      try {
        const data = await fetchApi(`/commerce/orders/${orderId}/`);
        setOrder(data);
      } catch (err) {
        setError(err.message || "Failed to fetch order.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrder();
  }, [user, orderId]);

  useEffect(() => {
    if (order && order.shipment_info?.has_shipment) {
      fetchTracking();
    }
  }, [order]);

  const fetchTracking = async () => {
    if (!orderId) return;
    
    setIsTrackingLoading(true);
    try {
      const data = await fetchApi(`/shipping/order-tracking/${orderId}/`);
      setTrackingData(data);
    } catch (err) {
      console.error("Failed to fetch tracking:", err);
      // Don't set error, tracking is optional
    } finally {
      setIsTrackingLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    try {
      return new Date(dateString).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return "N/A";
    try {
      return new Date(dateString).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateString;
    }
  };

  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase() || "";
    if (statusLower.includes("delivered") || statusLower.includes("completed")) {
      return "status-success";
    }
    if (statusLower.includes("pending") || statusLower.includes("manifested")) {
      return "status-pending";
    }
    if (statusLower.includes("transit") || statusLower.includes("shipped")) {
      return "status-in-transit";
    }
    if (statusLower.includes("cancelled") || statusLower.includes("failed")) {
      return "status-error";
    }
    return "status-info";
  };

  const handleDownloadInvoice = async () => {
    if (isDownloadingInvoice || !order) return;
    
    try {
      setIsDownloadingInvoice(true);
      const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
      if (!token) {
        alert('Please login to download invoice');
        setIsDownloadingInvoice(false);
        return;
      }

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
      const response = await fetch(`${API_BASE_URL}/commerce/invoices/pdf/${order.id}/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to download invoice');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice_${order.order_number || order.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      alert(e?.message || 'Could not download invoice');
    } finally {
      setIsDownloadingInvoice(false);
    }
  };

  const handleCancelOrder = async () => {
    if (!order || isCancelling) return;
    
    if (!confirm('Are you sure you want to cancel this order? This action cannot be undone.')) {
      return;
    }

    try {
      setIsCancelling(true);
      await fetchApi('/commerce/orders/cancel/', {
        method: 'POST',
        body: JSON.stringify({ order_id: order.id }),
      });
      
      // Refresh order data
      const updatedOrder = await fetchApi(`/commerce/orders/${orderId}/`);
      setOrder(updatedOrder);
      alert('Order cancelled successfully');
    } catch (e) {
      alert(e?.message || 'Could not cancel order');
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) {
    return (
      <>
        <div className="page orders-page">
          <div className="container">
            <p>Loading order details...</p>
          </div>
        </div>
      </>
    );
  }

  if (error || !order) {
    return (
      <>
        <div className="page orders-page">
          <div className="container">
            <p className="error">{error || "Order not found"}</p>
          </div>
        </div>
      </>
    );
  }

  const hasShipment = order.shipment_info?.has_shipment;
  const trackingHistory = trackingData?.tracking_history || [];
  
  // Check if order has been shipped (cannot be cancelled)
  // This checks both order status and shipment status from Shiprocket/Delhivery
  const isShipped = () => {
    // Check order status first
    if (order.status === 'SHIPPED' || order.status === 'COMPLETED') {
      return true;
    }
    
    // Check shipment status from Shiprocket/Delhivery
    const shipmentStatus = (order.shipment_info?.status || '').toLowerCase();
    const trackingStatus = (trackingData?.shipment?.status || '').toLowerCase();
    const combinedStatus = `${shipmentStatus} ${trackingStatus}`.toLowerCase();
    
    // Statuses that indicate the order has been physically shipped/picked up
    // Note: "manifested" means label created but NOT yet shipped, so we exclude it
    const shippedStatuses = [
      'shipped',
      'dispatched',
      'in transit',
      'in_transit',
      'out for delivery',
      'out_for_delivery',
      'delivered',
      'picked',
      'picked up',
      'picked_up',
      'rto', // Return to Origin - means it was shipped
      'undelivered', // Means it was shipped but couldn't be delivered
      'delivery attempted',
      'delivery_attempted',
    ];
    
    // Check if any shipped status is present
    return shippedStatuses.some(status => combinedStatus.includes(status));
  };
  
  const orderIsShipped = isShipped();

  return (
    <>
      <div className="page orders-page order-detail-page">
        <div className="container">
          <Link href="/orders" style={{ display: "inline-block", marginBottom: "2rem", color: "rgba(242, 237, 230, 0.8)", textDecoration: "none" }}>
            ← Back to Orders
          </Link>
          
          <div className="order-detail-header">
            <h1>Order #{order.order_number || order.id}</h1>
            <span className={`order-status is-${order.status.toLowerCase()}`}>
              {order.status.replace(/_/g, " ")}
            </span>
          </div>

          {/* Order Action Buttons */}
          <div className="order-actions">
            {(order.can_cancel || (order.status === 'PENDING_PAYMENT' || order.status === 'PROCESSING' || order.status === 'PAID')) && !orderIsShipped && (
              <button
                onClick={handleCancelOrder}
                disabled={isCancelling || orderIsShipped}
                className="order-action-button danger"
                title={orderIsShipped ? 'Order has been shipped and cannot be cancelled' : ''}
              >
                {isCancelling ? 'Cancelling...' : 'Cancel Order'}
              </button>
            )}
            {orderIsShipped && (
              <div style={{ 
                padding: '0.75rem 1.5rem', 
                borderRadius: '0.9rem',
                background: 'rgba(242, 84, 91, 0.1)',
                border: '1px solid rgba(242, 84, 91, 0.2)',
                color: 'rgba(242, 84, 91, 0.9)',
                fontSize: '0.9rem',
                fontWeight: 500
              }}>
                Order has been shipped and cannot be cancelled
              </div>
            )}
            <button
              onClick={handleDownloadInvoice}
              disabled={isDownloadingInvoice}
              className="order-action-button success"
            >
              {isDownloadingInvoice ? '⏳ Generating Invoice...' : '📄 Download Invoice'}
            </button>
          </div>

          {/* Shipment Tracking Section */}
          {hasShipment && (
            <div className="tracking-section">
              <h2>Delivery Tracking</h2>
              
              <div className="tracking-summary">
                <div className="tracking-summary-item">
                  <span className="tracking-label">Tracking Number</span>
                  <span className="tracking-value">{order.tracking_number || order.shipment_info?.waybill_number || "N/A"}</span>
                </div>
                <div className="tracking-summary-item">
                  <span className="tracking-label">Courier</span>
                  <span className="tracking-value">{order.courier_name || "Delhivery"}</span>
                </div>
                <div className="tracking-summary-item">
                  <span className="tracking-label">Shipping Mode</span>
                  <span className="tracking-value">{order.shipment_info?.shipping_mode || "Standard"}</span>
                </div>
                {trackingData?.shipment?.expected_delivery_date && (
                  <div className="tracking-summary-item">
                    <span className="tracking-label">Expected Delivery</span>
                    <span className="tracking-value expected-delivery">
                      {formatDate(trackingData.shipment.expected_delivery_date)}
                    </span>
                  </div>
                )}
              </div>

              <div className="current-status">
                <h3>Current Status</h3>
                <div className={`status-badge ${getStatusColor(trackingData?.shipment?.status || order.shipment_info?.status)}`}>
                  {trackingData?.shipment?.status || order.shipment_info?.status || "Processing"}
                </div>
              </div>

              {/* Tracking Timeline */}
              {isTrackingLoading ? (
                <div className="tracking-loading">Loading tracking history...</div>
              ) : trackingHistory.length > 0 ? (
                <div className="tracking-timeline">
                  <h3>Tracking History</h3>
                  <div className="timeline">
                    {trackingHistory.map((entry, index) => (
                      <div key={entry.id || index} className="timeline-item">
                        <div className="timeline-marker"></div>
                        <div className="timeline-content">
                          <div className="timeline-status">{entry.status}</div>
                          {entry.location && (
                            <div className="timeline-location">📍 {entry.location}</div>
                          )}
                          <div className="timeline-date">
                            {formatDateTime(entry.scan_date_time)}
                          </div>
                          {entry.instructions && (
                            <div className="timeline-instructions">{entry.instructions}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="tracking-no-history">
                  <p>Tracking information will be available once the shipment is processed.</p>
                </div>
              )}
            </div>
          )}

          {/* Order Items Section */}
          <div className="order-items-section">
            <h2>Order Items</h2>
            <div className="order-items-list">
              {order.items?.map((item) => (
                <div key={item.id} className="order-item-card">
                  <div className="order-item-info">
                    <h4>{item.variant?.product?.name || "Product"}</h4>
                    {item.variant?.sku && (
                      <p className="item-sku">SKU: {item.variant.sku}</p>
                    )}
                    <p className="item-quantity">Quantity: {item.quantity}</p>
                    <p className="item-price">₹{item.line_total}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Order Summary */}
          <div className="order-summary-section">
            <h2>Order Summary</h2>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-label">Order Date</span>
                <span className="summary-value">{formatDate(order.created_at)}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Payment Method</span>
                <span className="summary-value">{order.payment_method}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Subtotal</span>
                <span className="summary-value">₹{order.subtotal}</span>
              </div>
              {order.discount_amount > 0 && (
                <div className="summary-item">
                  <span className="summary-label">Discount</span>
                  <span className="summary-value discount">-₹{order.discount_amount}</span>
                </div>
              )}
              <div className="summary-item total">
                <span className="summary-label">Total</span>
                <span className="summary-value">₹{order.total_cost}</span>
              </div>
            </div>
            
            {/* Download Invoice Button in Summary Section */}
            <div style={{ marginTop: '1.5rem' }}>
              <button
                onClick={handleDownloadInvoice}
                disabled={isDownloadingInvoice}
                className="order-action-button success"
                style={{ width: '100%' }}
              >
                {isDownloadingInvoice ? '⏳ Generating Invoice...' : '📄 Download Invoice PDF'}
              </button>
            </div>
          </div>

          {/* Shipping Address */}
          <div className="shipping-address-section">
            <h2>Shipping Address</h2>
            <div className="address-card">
              <p><strong>{order.full_name}</strong></p>
              <p>{order.address_line1}</p>
              {order.address_line2 && <p>{order.address_line2}</p>}
              <p>
                {order.city}, {order.state} {order.postal_code}
              </p>
              <p>{order.country}</p>
              {order.phone && <p>Phone: {order.phone}</p>}
              {order.email && <p>Email: {order.email}</p>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default OrderDetailPage;

