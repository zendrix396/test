"use client";

import "./checkout.css";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import Copy from "@/components/Copy/Copy";
import AnimatedButton from "@/components/AnimatedButton/AnimatedButton";

import { useCartContext } from "@/context/CartContext";
import { useCurrencyContext } from "@/context/CurrencyContext";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";
import CashbackPopup from "@/components/CashbackPopup/CashbackPopup";
import LoginModal from "@/components/LoginModal/LoginModal";

const initialFormState = {
  full_name: "",
  email: "",
  phone: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "India",
};

const CheckoutPage = () => {
  const router = useRouter();
  const { cart, isLoading: isCartLoading, applyCoupon, removeCoupon, setGiftWrap, refresh } = useCartContext();
  const { formatCurrency } = useCurrencyContext();
  const { user } = useUser();

  const [formData, setFormData] = useState(initialFormState);
  const [paymentMethod, setPaymentMethod] = useState("RAZORPAY");
  const [status, setStatus] = useState({ type: null, message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [couponInput, setCouponInput] = useState("");
  const [couponError, setCouponError] = useState("");
  const [suggested, setSuggested] = useState([]);
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(true);
  const [showCashbackPopup, setShowCashbackPopup] = useState(false);
  const [cashbackAmount, setCashbackAmount] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [savedAddresses, setSavedAddresses] = useState([]);
  const [useDefaultAddress, setUseDefaultAddress] = useState(false);
  const [saveAddress, setSaveAddress] = useState(false);
  const [isLoadingAddresses, setIsLoadingAddresses] = useState(false);

  const totals = useMemo(() => {
    if (!cart) {
      return {
        subtotal: 0,
        discount: 0,
        giftWrap: 0,
        total: 0,
      };
    }

    const subtotalValue = Number(cart.subtotal || 0);
    const discountValue = Number(cart.discount_amount || 0);
    const giftWrapValue = cart.gift_wrap ? Number(cart.gift_wrap_amount || 0) : 0;
    const payable = Number(cart.total_payable || subtotalValue - discountValue + giftWrapValue);

    return {
      subtotal: subtotalValue,
      discount: discountValue,
      giftWrap: giftWrapValue,
      total: payable,
    };
  }, [cart]);


  // Load saved addresses for logged in users
  useEffect(() => {
    const loadAddresses = async () => {
      if (!user) {
        setSavedAddresses([]);
        return;
      }
      setIsLoadingAddresses(true);
      try {
        const addresses = await fetchApi("/auth/addresses/");
        setSavedAddresses(Array.isArray(addresses) ? addresses : []);
        // Auto-select default address if available
        const defaultAddr = addresses?.find((addr) => addr.is_default);
        if (defaultAddr && !formData.full_name) {
          setUseDefaultAddress(true);
          setFormData({
            full_name: defaultAddr.full_name || "",
            email: defaultAddr.email || user.email || "",
            phone: defaultAddr.phone || user.phone_number || "",
            address_line1: defaultAddr.address_line1 || "",
            address_line2: defaultAddr.address_line2 || "",
            city: defaultAddr.city || "",
            state: defaultAddr.state || "",
            postal_code: defaultAddr.postal_code || "",
            country: defaultAddr.country || "India",
          });
        }
      } catch (error) {
        console.error("Failed to load addresses", error);
      } finally {
        setIsLoadingAddresses(false);
      }
    };
    loadAddresses();
  }, [user]);

  useEffect(() => {
    if (user && !useDefaultAddress) {
      setFormData((prev) => ({
        ...prev,
        full_name: prev.full_name || user.full_name || `${user.first_name || ""} ${user.last_name || ""}`.trim(),
        email: prev.email || user.email || "",
        phone: prev.phone || user.phone_number || "",
      }));
    }
  }, [user, useDefaultAddress]);

  useEffect(() => {
    let isMounted = true;
    const loadSuggestions = async () => {
      try {
        const response = await fetchApi("/products/?page_size=4&ordering=-created_at");
        if (!isMounted) return;
        const items = Array.isArray(response.results) ? response.results : response;
        setSuggested((items || []).slice(0, 4));
      } catch (error) {
        console.error("Failed to load suggested products", error);
      } finally {
        if (isMounted) setIsFetchingSuggestions(false);
      }
    };

    loadSuggestions();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.Razorpay) return;
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handleFieldChange = useCallback((event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleApplyCoupon = useCallback(async () => {
    if (!couponInput.trim()) return;
    try {
      setCouponError("");
      await applyCoupon(couponInput.trim());
      setStatus({ type: "success", message: "Coupon applied to your cart." });
      setCouponInput("");
    } catch (error) {
      setCouponError(error?.message || "Unable to apply coupon." );
    }
  }, [couponInput, applyCoupon]);

  const handleRemoveCoupon = useCallback(async () => {
    try {
      await removeCoupon();
      setStatus({ type: "info", message: "Coupon removed." });
    } catch (error) {
      setStatus({ type: "danger", message: error?.message || "Unable to remove coupon." });
    }
  }, [removeCoupon]);

  const handleGiftWrapToggle = useCallback(async () => {
    try {
      await setGiftWrap(!cart?.gift_wrap);
      setStatus({
        type: "info",
        message: cart?.gift_wrap ? "Gift wrap removed." : "Gift wrap added.",
      });
    } catch (error) {
      setStatus({ type: "danger", message: error?.message || "Unable to update gift wrap." });
    }
  }, [cart?.gift_wrap, setGiftWrap]);

  const openRazorpayCheckout = useCallback(
    (paymentPayload, orderDetails) => {
      if (typeof window === "undefined" || !window.Razorpay) {
        setStatus({ type: "danger", message: "Payment gateway is unavailable. Please try COD or retry later." });
        return;
      }

      const options = {
        key: paymentPayload.key,
        amount: paymentPayload.amount,
        currency: paymentPayload.currency,
        name: "Space4U",
        description: `Order #${orderDetails.id}`,
        order_id: paymentPayload.razorpay_order_id,
        prefill: {
          name: formData.full_name,
          email: formData.email,
          contact: formData.phone,
        },
        notes: {
          order_id: orderDetails.id,
        },
        theme: {
          color: "#f2545b",
        },
        handler: async (response) => {
          try {
            const verifyResponse = await fetchApi("/commerce/orders/verify-payment/", {
              method: "POST",
              body: JSON.stringify({
                order_id: orderDetails.id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });
            setStatus({ type: "success", message: "Payment successful! Your order is confirmed." });
            refresh();
            
            // Show cashback popup if cashback was applied
            if (verifyResponse?.cashback_amount && parseFloat(verifyResponse.cashback_amount) > 0) {
              setCashbackAmount(verifyResponse.cashback_amount);
              setShowCashbackPopup(true);
            } else {
              router.push("/orders");
            }
          } catch (error) {
            setStatus({ type: "danger", message: error?.message || "Payment verification failed." });
          }
        },
        modal: {
          ondismiss: () => {
            setStatus({ type: "warning", message: "Payment cancelled. You can retry or choose Cash on Delivery." });
          },
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    },
    [formData, refresh, router]
  );

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      if (!cart || !cart.items?.length) {
        setStatus({ type: "warning", message: "Your cart is empty. Add items before checking out." });
        return;
      }

      setIsSubmitting(true);
      setStatus({ type: null, message: "" });

      try {
        const orderPayload = {
          ...formData,
          payment_method: paymentMethod,
        };

        const order = await fetchApi("/commerce/orders/create/", {
          method: "POST",
          body: JSON.stringify({
            ...orderPayload,
            save_address: saveAddress && user ? true : false,
          }),
        });

        if (!order?.id) {
          // If order is null due to auth error, return early
          if (!order) return;
          throw new Error("Unable to create order. Please try again.");
        }

        if (paymentMethod === "COD") {
          await fetchApi("/commerce/orders/create-payment/", {
            method: "POST",
            body: JSON.stringify({ order_id: order.id, payment_method: "COD" }),
          });
          
          setStatus({ type: "success", message: "Order placed! You'll pay upon delivery." });
          refresh();
          if (user) {
            router.push("/orders");
          } else {
            router.push(`/orders?order_id=${order.id}`);
          }
          return;
        }

        const paymentIntent = await fetchApi("/commerce/orders/create-payment/", {
          method: "POST",
          body: JSON.stringify({ order_id: order.id, payment_method: paymentMethod }),
        });
        
        openRazorpayCheckout(paymentIntent, order);
      } catch (error) {
        console.error("Checkout failed", error);
        setStatus({ type: "danger", message: error?.message || "Checkout failed. Please retry." });
      } finally {
        setIsSubmitting(false);
      }
    },
    [cart, formData, paymentMethod, openRazorpayCheckout, refresh, router, saveAddress, user]
  );

  const loginPrompt = useMemo(() => {
    if (user) return null;
    return (
      <div className="checkout-login-prompt">
        <div>
          <span>Returning customer?</span>
          <strong>Log in for perks like loyalty points, leaderboard access, and faster checkout.</strong>
        </div>
        <button type="button" onClick={() => router.push("/login")}>Continue</button>
      </div>
    );
  }, [user, router]);

  return (
    <>
      <div className="page checkout">
        <section className="checkout-hero">
          <div className="container">
            <Copy delay={0.1}>
              <h1>Complete your order</h1>
            </Copy>
            <Copy delay={0.18}>
              <p>Secure your merch, choose how you pay, and get ready for delivery.</p>
            </Copy>
          </div>
        </section>

        <section className="checkout-content">
          <div className="container">
            {status.message && (
              <div className={`checkout-status is-${status.type || "default"}`}>
                {status.message}
              </div>
            )}

            <div className="checkout-grid">
              <div className="checkout-form-card">
                {loginPrompt}
                {user && savedAddresses.length > 0 && (
                  <div className="checkout-default-address">
                    <label className="checkout-default-address-toggle">
                      <input
                        type="checkbox"
                        checked={useDefaultAddress}
                        onChange={(e) => {
                          setUseDefaultAddress(e.target.checked);
                          if (e.target.checked) {
                            const defaultAddr = savedAddresses.find((addr) => addr.is_default) || savedAddresses[0];
                            if (defaultAddr) {
                              setFormData({
                                full_name: defaultAddr.full_name || "",
                                email: defaultAddr.email || user.email || "",
                                phone: defaultAddr.phone || user.phone_number || "",
                                address_line1: defaultAddr.address_line1 || "",
                                address_line2: defaultAddr.address_line2 || "",
                                city: defaultAddr.city || "",
                                state: defaultAddr.state || "",
                                postal_code: defaultAddr.postal_code || "",
                                country: defaultAddr.country || "India",
                              });
                            }
                          }
                        }}
                      />
                      <span>Use default address</span>
                    </label>
                    {useDefaultAddress && savedAddresses.find((addr) => addr.is_default) && (
                      <div className="checkout-address-preview">
                        <p><strong>{savedAddresses.find((addr) => addr.is_default).full_name}</strong></p>
                        <p>{savedAddresses.find((addr) => addr.is_default).phone}</p>
                        <p>
                          {savedAddresses.find((addr) => addr.is_default).address_line1}
                          {savedAddresses.find((addr) => addr.is_default).address_line2 && `, ${savedAddresses.find((addr) => addr.is_default).address_line2}`}
                        </p>
                        <p>
                          {savedAddresses.find((addr) => addr.is_default).city}, {savedAddresses.find((addr) => addr.is_default).state} {savedAddresses.find((addr) => addr.is_default).postal_code}
                        </p>
                      </div>
                    )}
                  </div>
                )}
                <form onSubmit={handleSubmit} className="checkout-form">
                  {!useDefaultAddress && (
                    <>
                  <div className="checkout-field-row">
                    <label>
                      Full name
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleFieldChange}
                        required
                        placeholder="e.g. Jonathan Joestar"
                      />
                    </label>
                    <label>
                      Email
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleFieldChange}
                        required
                        placeholder="you@example.com"
                      />
                    </label>
                  </div>

                  <div className="checkout-field-row">
                    <label>
                      Phone
                      <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleFieldChange}
                        placeholder="Optional contact"
                      />
                    </label>
                    <label>
                      Postal code
                      <input
                        type="text"
                        name="postal_code"
                        value={formData.postal_code}
                        onChange={handleFieldChange}
                        required
                        placeholder="e.g. 560001"
                      />
                    </label>
                  </div>

                  <label>
                    Address line 1
                    <input
                      type="text"
                      name="address_line1"
                      value={formData.address_line1}
                      onChange={handleFieldChange}
                      required
                      placeholder="House number, street"
                    />
                  </label>
                  <label>
                    Address line 2
                    <input
                      type="text"
                      name="address_line2"
                      value={formData.address_line2}
                      onChange={handleFieldChange}
                      placeholder="Landmark, apartment, etc."
                    />
                  </label>

                  <div className="checkout-field-row">
                    <label>
                      City
                      <input
                        type="text"
                        name="city"
                        value={formData.city}
                        onChange={handleFieldChange}
                        required
                      />
                    </label>
                    <label>
                      State
                      <input
                        type="text"
                        name="state"
                        value={formData.state}
                        onChange={handleFieldChange}
                        placeholder="Optional"
                      />
                    </label>
                  </div>
                  </>
                  )}

                  {user && !useDefaultAddress && (
                    <label className="checkout-save-address">
                      <input
                        type="checkbox"
                        checked={saveAddress}
                        onChange={(e) => setSaveAddress(e.target.checked)}
                      />
                      <span>Save this address for future orders</span>
                    </label>
                  )}

                  <div className="checkout-payment">
                    <p>Payment method</p>
                    <div className="checkout-payment-options">
                      <label className={paymentMethod === "RAZORPAY" ? "is-active" : ""}>
                        <input
                          type="radio"
                          name="payment_method"
                          value="RAZORPAY"
                          checked={paymentMethod === "RAZORPAY"}
                          onChange={(event) => setPaymentMethod(event.target.value)}
                        />
                        <span>Pay Online (UPI / Cards)</span>
                      </label>
                      <label className={paymentMethod === "COD" ? "is-active" : ""}>
                        <input
                          type="radio"
                          name="payment_method"
                          value="COD"
                          checked={paymentMethod === "COD"}
                          onChange={(event) => setPaymentMethod(event.target.value)}
                        />
                        <span>Cash on Delivery</span>
                      </label>
                    </div>
                  </div>

                  <div className="checkout-actions">
                    <AnimatedButton
                      label={isSubmitting ? "Processing…" : paymentMethod === "COD" ? "Place COD order" : "Pay securely"}
                      animate={false}
                      disabled={isSubmitting || !cart?.items?.length}
                      extraClasses="checkout-button"
                    />
                  </div>
                </form>
              </div>

              <aside className="checkout-summary">
                <div className="checkout-summary-card">
                  <div className="checkout-summary-header">
                    <h3>Order summary</h3>
                    <button type="button" onClick={handleGiftWrapToggle}>
                      {cart?.gift_wrap ? "Remove gift wrap" : "Add gift wrap"}
                    </button>
                  </div>

                  {isCartLoading ? (
                    <p className="checkout-summary-empty">Loading cart…</p>
                  ) : !cart?.items?.length ? (
                    <p className="checkout-summary-empty">Your cart is empty.</p>
                  ) : (
                    <ul className="checkout-summary-items">
                      {cart.items.map((item) => (
                        <li key={item.id}>
                          <div>
                            <p className="checkout-summary-name">{item.product?.name || item.variant?.name}</p>
                            <span className="checkout-summary-meta">Qty {item.quantity}</span>
                          </div>
                          <span>{formatCurrency((item.variant?.discount_price || item.variant?.price || 0) * item.quantity)}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="checkout-summary-coupon">
                    {cart?.applied_coupon ? (
                      <div className="checkout-summary-coupon-active">
                        <span>Coupon <strong>{cart.applied_coupon.code}</strong> applied</span>
                        <button type="button" onClick={handleRemoveCoupon}>Remove</button>
                      </div>
                    ) : (
                      <div className="checkout-summary-coupon-form">
                        <input
                          type="text"
                          placeholder="Coupon code"
                          value={couponInput}
                          onChange={(event) => setCouponInput(event.target.value)}
                        />
                        <button type="button" onClick={handleApplyCoupon}>Apply</button>
                      </div>
                    )}
                    {couponError && <p className="checkout-summary-error">{couponError}</p>}
                  </div>

                  <dl className="checkout-summary-totals">
                    <div>
                      <dt>Subtotal</dt>
                      <dd>{formatCurrency(totals.subtotal)}</dd>
                    </div>
                    {totals.discount > 0 && (
                      <div>
                        <dt>Discount</dt>
                        <dd>-{formatCurrency(totals.discount)}</dd>
                      </div>
                    )}
                    {totals.giftWrap > 0 && (
                      <div>
                        <dt>Gift wrap</dt>
                        <dd>{formatCurrency(totals.giftWrap)}</dd>
                      </div>
                    )}
                    <div className="checkout-summary-total">
                      <dt>Total payable</dt>
                      <dd>{formatCurrency(totals.total)}</dd>
                    </div>
                  </dl>
                </div>

                <div className="checkout-suggested">
                  <h4>Suggested for you</h4>
                  {isFetchingSuggestions ? (
                    <p className="checkout-summary-empty">Loading recommendations…</p>
                  ) : suggested.length === 0 ? (
                    <p className="checkout-summary-empty">Stay tuned for more drops.</p>
                  ) : (
                    <div className="checkout-suggested-grid">
                      {suggested.map((item) => {
                        const highlight = item.slug || item.sku || item.id;
                        const target = highlight
                          ? `/shop?highlight=${encodeURIComponent(highlight)}`
                          : "/shop";
                        return (
                          <button
                            key={item.id || item.sku}
                            type="button"
                            className="checkout-suggested-card"
                            onClick={() => router.push(target)}
                          >
                          {item.image && <img src={item.image} alt={item.name} loading="lazy" />}
                          <div>
                            <p>{item.name}</p>
                            <span>{formatCurrency(item.discount_price || item.price || 0)}</span>
                          </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </aside>
            </div>
          </div>
        </section>
      </div>
      {showCashbackPopup && (
        <CashbackPopup 
          cashbackAmount={cashbackAmount} 
          onClose={() => {
            setShowCashbackPopup(false);
            router.push("/orders");
          }} 
        />
      )}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => {
          setShowLoginModal(false);
          setIsSubmitting(false);
        }}
        onLoginSuccess={() => {
          // Retry the checkout submission after successful login
          setIsSubmitting(true);
          setTimeout(() => {
            const form = document.querySelector('.checkout-form');
            if (form) {
              form.requestSubmit();
            }
          }, 500);
        }}
      />
    </>
  );
};

export default CheckoutPage;

