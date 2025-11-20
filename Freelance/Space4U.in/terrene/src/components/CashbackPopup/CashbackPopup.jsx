"use client";

import { useEffect, useState } from "react";
import { useViewTransition } from "@/hooks/useViewTransition";
import "./CashbackPopup.css";

/**
 * Cashback popup shown after successful payment
 */
export default function CashbackPopup({ cashbackAmount, onClose }) {
  const [isVisible, setIsVisible] = useState(false);
  const { navigateWithTransition } = useViewTransition();

  useEffect(() => {
    // Animate in
    setTimeout(() => setIsVisible(true), 100);
  }, []);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(() => {
      if (onClose) onClose();
    }, 300);
  };

  const handleViewWallet = () => {
    handleClose();
    setTimeout(() => {
      navigateWithTransition("/profile");
    }, 300);
  };

  if (!cashbackAmount || parseFloat(cashbackAmount) <= 0) {
    return null;
  }

  return (
    <div className={`cashback-popup-overlay ${isVisible ? 'is-visible' : ''}`} onClick={handleClose}>
      <div className="cashback-popup" onClick={(e) => e.stopPropagation()}>
        <button className="cashback-popup-close" onClick={handleClose} aria-label="Close">
          ×
        </button>
        <div className="cashback-popup-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <h2>🎉 Cashback Credited!</h2>
        <p className="cashback-popup-amount">
          ₹{parseFloat(cashbackAmount).toFixed(2)}
        </p>
        <p className="cashback-popup-message">
          Great news! Your cashback has been added to your wallet. 
          You can use it on your next purchase or redeem it anytime.
        </p>
        <div className="cashback-popup-actions">
          <button className="cashback-popup-button primary" onClick={handleViewWallet}>
            View Wallet
          </button>
          <button className="cashback-popup-button secondary" onClick={handleClose}>
            Continue Shopping
          </button>
        </div>
      </div>
    </div>
  );
}

