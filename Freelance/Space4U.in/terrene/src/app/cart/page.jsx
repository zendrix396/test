"use client";

import { useCartContext } from "@/context/CartContext";
import Nav from "@/components/Nav/Nav";
import ConditionalFooter from "@/components/ConditionalFooter/ConditionalFooter";
import AnimatedButton from "@/components/AnimatedButton/AnimatedButton";
import { useRouter } from "next/navigation";
import SakuraPetals from "@/components/SakuraPetals/SakuraPetals";
import "./cart.css";

const CartPage = () => {
  const { cart, isLoading, updateQuantity, removeItem } = useCartContext();
  const router = useRouter();

  const handleCheckout = () => {
    router.push("/checkout");
  };

  return (
    <>
      <SakuraPetals />
      <div className="page cart-page">
        <div className="container">
          <h1>Your Cart</h1>
          {isLoading ? (
            <p>Loading cart...</p>
          ) : !cart || cart.items.length === 0 ? (
            <p>Your cart is empty.</p>
          ) : (
            <div className="cart-layout">
              <div className="cart-items">
                {cart.items.map((item) => (
                  <div key={item.id} className="cart-item">
                    <img src={item.product.image} alt={item.product.name} />
                    <div className="cart-item-info">
                      <h3>{item.product.name}</h3>
                      <p>{item.variant.name}</p>
                      <p>₹{item.variant.deal_price || item.variant.discount_price || item.variant.price}</p>
                    </div>
                    <div className="cart-item-actions">
                      <div className="quantity-control">
                        <button onClick={() => updateQuantity(item.variant.id, item.quantity - 1)} disabled={item.quantity <= 1}>-</button>
                        <span>{item.quantity}</span>
                        <button onClick={() => updateQuantity(item.variant.id, item.quantity + 1)}>+</button>
                      </div>
                      <button className="cart-item-remove-btn" onClick={() => removeItem(item.variant.id)}>Remove</button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="cart-summary">
                <h2>Summary</h2>
                <div className="summary-row">
                  <span>Subtotal</span>
                  <span>₹{cart.subtotal}</span>
                </div>
                {cart.discount_amount > 0 && (
                  <div className="summary-row">
                    <span>Discount</span>
                    <span>-₹{cart.discount_amount}</span>
                  </div>
                )}
                {cart.gift_wrap && (
                    <div className="summary-row">
                        <span>Gift Wrap</span>
                        <span>₹{cart.gift_wrap_amount}</span>
                    </div>
                )}
                <div className="summary-total">
                  <span>Total</span>
                  <span>₹{cart.total_payable}</span>
                </div>
                <AnimatedButton
                  label="Proceed to Checkout"
                  onClick={handleCheckout}
                  animate={false}
                  extraClasses="checkout-button"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default CartPage;
