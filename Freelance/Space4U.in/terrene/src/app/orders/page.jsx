"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav/Nav";
import ConditionalFooter from "@/components/ConditionalFooter/ConditionalFooter";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";
import SakuraPetals from "@/components/SakuraPetals/SakuraPetals";
import "./orders.css";

const OrdersPage = () => {
  const { user } = useUser();
  const [orders, setOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user) {
      setIsLoading(false);
      return;
    }

    const fetchOrders = async () => {
      try {
        const data = await fetchApi("/commerce/orders/");
        setOrders(data);
      } catch (err) {
        setError(err.message || "Failed to fetch orders.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrders();
  }, [user]);

  return (
    <>
      <SakuraPetals />
      <div className="page orders-page">
        <div className="container">
          <h1>My Orders</h1>
          {isLoading && <p>Loading orders...</p>}
          {error && <p className="error">{error}</p>}
          {!isLoading && !error && !user && <p>Please log in to see your orders.</p>}
          {!isLoading && !error && user && orders.length === 0 && <p>You have no orders yet.</p>}
          {!isLoading && !error && user && orders.length > 0 && (
            <div className="orders-list">
              {orders.map((order) => (
                <div key={order.id} className="order-card">
                  <div className="order-card-header">
                    <h3>Order #{order.id}</h3>
                    <span className={`order-status is-${order.status.toLowerCase()}`}>{order.status.replace("_", " ")}</span>
                  </div>
                  <div className="order-card-body">
                    <p><strong>Date:</strong> {new Date(order.created_at).toLocaleDateString()}</p>
                    <p><strong>Total:</strong> ₹{order.total_cost}</p>
                    <p><strong>Payment:</strong> {order.payment_method}</p>
                  </div>
                  <div className="order-card-footer">
                    <a href={`/orders/${order.id}`} style={{ textDecoration: 'none' }}>
                      <button>View Details</button>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default OrdersPage;
