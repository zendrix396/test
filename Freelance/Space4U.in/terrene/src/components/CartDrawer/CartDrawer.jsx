"use client";

import "./CartDrawer.css";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { useRouter } from "next/navigation";

import { useCartContext } from "@/context/CartContext";
import { useCurrencyContext } from "@/context/CurrencyContext";

const CartDrawer = () => {
  const {
    cart,
    isOpen,
    isLoading,
    isMutating,
    closeCart,
    updateQuantity,
    removeItem,
    setGiftWrap,
    applyCoupon,
    removeCoupon,
  } = useCartContext();
  const { formatCurrency } = useCurrencyContext();

  const router = useRouter();

  const drawerRef = useRef(null);
  const overlayRef = useRef(null);
  const [shouldRender, setShouldRender] = useState(false);
  const [couponInput, setCouponInput] = useState("");
  const [isApplying, setIsApplying] = useState(false);
  const [couponError, setCouponError] = useState("");

  // Lock body scroll when cart is open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      setShouldRender(true);
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  useEffect(() => {
    if (!shouldRender || !drawerRef.current || !overlayRef.current) return;

    if (isOpen) {
      gsap.set(drawerRef.current, { xPercent: 100, autoAlpha: 1 });
      gsap.to(drawerRef.current, {
        xPercent: 0,
        duration: 0.5,
        ease: "power3.out",
      });
      gsap.to(overlayRef.current, {
        autoAlpha: 1,
        duration: 0.4,
        ease: "power2.out",
      });
    } else {
      const tl = gsap.timeline({
        onComplete: () => setShouldRender(false),
      });
      tl.to(drawerRef.current, {
        xPercent: 100,
        duration: 0.45,
        ease: "power3.in",
      }).to(
        overlayRef.current,
        {
          autoAlpha: 0,
          duration: 0.35,
          ease: "power2.inOut",
        },
        "<"
      );
    }
  }, [isOpen, shouldRender]);

  const handleQuantityChange = useCallback(
    (variantId, delta, currentQty) => {
      if (isMutating) return;
      const nextQty = Math.max(0, currentQty + delta);
      updateQuantity(variantId, nextQty);
    },
    [updateQuantity, isMutating]
  );

  const handleRemove = useCallback((variantId) => {
    if (isMutating) return;
    removeItem(variantId);
  }, [removeItem, isMutating]);

  const handleGiftWrapToggle = useCallback((event) => {
    setGiftWrap(event.target.checked);
  }, [setGiftWrap]);

  const handleApplyCoupon = useCallback(async () => {
    if (!couponInput.trim()) return;
    try {
      setIsApplying(true);
      setCouponError("");
      await applyCoupon(couponInput.trim());
      setCouponInput("");
    } catch (error) {
      setCouponError(error?.message || "Unable to apply coupon.");
    } finally {
      setIsApplying(false);
    }
  }, [couponInput, applyCoupon]);

  const handleProceedToCheckout = useCallback(() => {
    closeCart();
    router.push("/checkout");
  }, [closeCart, router]);

  const hasItems = cart?.items?.length > 0;

  const totals = useMemo(() => {
    if (!cart) {
      return {
        subtotal: "₹0",
        discount: null,
        giftWrap: null,
        total: "₹0",
      };
    }

    const subtotalValue = cart.subtotal ?? 0;
    const discountValue = cart.discount_amount ?? 0;
    const giftWrapValue = cart.gift_wrap ? cart.gift_wrap_amount ?? 0 : 0;
    const totalValue = cart.total_payable ?? subtotalValue - discountValue + giftWrapValue;

    return {
      subtotal: formatCurrency(subtotalValue),
      discount: discountValue > 0 ? formatCurrency(discountValue) : null,
      giftWrap: cart.gift_wrap ? formatCurrency(giftWrapValue) : null,
      total: formatCurrency(totalValue),
    };
  }, [cart]);

  if (!shouldRender) return null;

  return (
    <div className="cart-drawer-root">
      <div
        ref={overlayRef}
        className="cart-drawer-overlay"
        onClick={() => !isMutating && closeCart()}
      />
      <aside ref={drawerRef} className="cart-drawer" aria-hidden={!isOpen}>
        <header className="cart-drawer-header">
          <div>
            <p className="cart-drawer-subtitle">Your Cart</p>
            <h2>
              {cart?.total_items || 0} item{cart?.total_items === 1 ? "" : "s"}
            </h2>
          </div>
          <button type="button" className="cart-drawer-close" onClick={closeCart}>
            <span />
            <span />
          </button>
        </header>

        <div className="cart-drawer-body">
          {isLoading ? (
            <div className="cart-drawer-empty">Loading cart…</div>
          ) : hasItems ? (
            <ul className="cart-drawer-items">
              {cart.items.map((item) => {
                const variant = item.variant || {};
                const product = item.product || {};
                const variantLabel = [variant.name, variant.size, variant.color]
                  .filter(Boolean)
                  .join(" • ");
                const displayPrice = formatCurrency(variant.discount_price || variant.price || 0);
                const productImages = product.images || [];
                const fallbackImage = productImages.length > 0 ? productImages[0]?.image : null;
                const imageSrc =
                  product.image ||
                  fallbackImage ||
                  variant.image ||
                  (variant.product && variant.product.image) ||
                  null;
                const tags = Array.isArray(product.tags)
                  ? product.tags
                  : typeof product.tags === "string"
                  ? product.tags.split(",").map((tag) => tag.trim())
                  : [];

                return (
                  <li key={item.id} className="cart-drawer-item">
                    <div className="cart-drawer-item-media">
                      {imageSrc ? (
                        <img src={imageSrc} alt={product.name || variant.name} />
                      ) : (
                        <div className="cart-drawer-item-placeholder">No image</div>
                      )}
                    </div>
                    <div className="cart-drawer-item-content">
                      <div className="cart-drawer-item-header">
                        <h3>{product.name || variant.name}</h3>
                        <button
                          type="button"
                          className="cart-drawer-item-remove"
                          onClick={() => handleRemove(variant.id)}
                          disabled={isMutating}
                        >
                          Remove
                        </button>
                      </div>
                      {tags.length > 0 && (
                        <div className="cart-drawer-item-tags">
                          {tags.slice(0, 2).map((tag) => (
                            <span key={`${item.id}-${tag}`}>#{tag}</span>
                          ))}
                        </div>
                      )}
                      {variantLabel && <p className="cart-drawer-item-variant">{variantLabel}</p>}
                      <div className="cart-drawer-item-footer">
                        <span className="cart-drawer-item-price">{displayPrice}</span>
                        <div className="cart-drawer-qty">
                          <button
                            type="button"
                            onClick={() => handleQuantityChange(variant.id, -1, item.quantity)}
                            disabled={isMutating}
                          >
                            −
                          </button>
                          <span>{item.quantity}</span>
                          <button
                            type="button"
                            onClick={() => handleQuantityChange(variant.id, 1, item.quantity)}
                            disabled={isMutating}
                          >
                            +
                          </button>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="cart-drawer-empty">
              <p>Your cart is feeling a little lonely.</p>
              <p>Add something legendary to get started!</p>
            </div>
          )}
        </div>

        <div className="cart-drawer-panel">
          <div className="cart-drawer-gift-wrap">
            <label>
              <input
                type="checkbox"
                checked={Boolean(cart?.gift_wrap)}
                onChange={handleGiftWrapToggle}
                disabled={isMutating || !hasItems}
              />
              <span>Add gift wrap</span>
            </label>
            {cart?.gift_wrap_amount > 0 && (
              <span className="cart-drawer-amount">{formatCurrency(cart.gift_wrap_amount)}</span>
            )}
          </div>

          <div className="cart-drawer-coupon">
            {cart?.applied_coupon ? (
              <div className="cart-drawer-coupon-active">
                <span>Coupon <strong>{cart.applied_coupon.code}</strong> applied</span>
                <button type="button" onClick={() => removeCoupon()} disabled={isMutating}>
                  Remove
                </button>
              </div>
            ) : (
              <div className="cart-drawer-coupon-form">
                <input
                  type="text"
                  placeholder="Coupon code"
                  value={couponInput}
                  onChange={(event) => setCouponInput(event.target.value)}
                  disabled={isMutating || !hasItems}
                />
                <button
                  type="button"
                  onClick={handleApplyCoupon}
                  disabled={isMutating || !couponInput.trim() || isApplying || !hasItems}
                >
                  Apply
                </button>
              </div>
            )}
            {couponError && <p className="cart-drawer-error">{couponError}</p>}
          </div>

          <dl className="cart-drawer-totals">
            <div>
              <dt>Subtotal</dt>
              <dd>{totals.subtotal}</dd>
            </div>
            {totals.discount && (
              <div>
                <dt>Discount</dt>
                <dd>-{totals.discount}</dd>
              </div>
            )}
            {totals.giftWrap && (
              <div>
                <dt>Gift wrap</dt>
                <dd>{totals.giftWrap}</dd>
              </div>
            )}
            <div className="cart-drawer-total">
              <dt>Total</dt>
              <dd>{totals.total}</dd>
            </div>
          </dl>

          <button
            type="button"
            className="cart-drawer-checkout"
            onClick={handleProceedToCheckout}
            disabled={!hasItems || isMutating}
          >
            Proceed to checkout
          </button>
        </div>
      </aside>
    </div>
  );
};

export default CartDrawer;

