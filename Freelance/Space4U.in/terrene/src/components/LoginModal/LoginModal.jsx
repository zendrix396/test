"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { FiArrowRight, FiX } from "react-icons/fi";
import { FcGoogle } from "react-icons/fc";
import fetchApi from "@/lib/api";
import { useUser } from "@/lib/hooks";
import "./LoginModal.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export default function LoginModal({ isOpen, onClose, onLoginSuccess }) {
  const router = useRouter();
  const { mutate } = useUser();
  const modalRef = useRef(null);
  const contentRef = useRef(null);
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [status, setStatus] = useState({ type: null, message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  useGSAP(() => {
    if (!isOpen || !modalRef.current || !contentRef.current) return;

    // Animate modal in
    gsap.fromTo(
      modalRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.3, ease: "power2.out" }
    );

    gsap.fromTo(
      contentRef.current,
      { y: 30, opacity: 0, scale: 0.95 },
      { y: 0, opacity: 1, scale: 1, duration: 0.4, ease: "power3.out" }
    );
  }, { scope: modalRef, dependencies: [isOpen] });

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;

    setStatus({ type: null, message: "" });

    if (!formData.username.trim() || !formData.password.trim()) {
      setStatus({ type: "error", message: "Username and password are required." });
      return;
    }

    try {
      setIsSubmitting(true);
      const payload = JSON.stringify({
        username: formData.username.trim(),
        password: formData.password,
      });

      const tokens = await fetchApi("/auth/jwt/create/", {
        method: "POST",
        body: payload,
      });

      if (!tokens?.access || !tokens?.refresh) {
        throw new Error("Login response was incomplete. Please try again.");
      }

      if (typeof window !== "undefined") {
        localStorage.setItem("accessToken", tokens.access);
        localStorage.setItem("refreshToken", tokens.refresh);
      }

      const profile = await fetchApi("/auth/me/");
      mutate(profile);
      setStatus({ type: "success", message: "Login successful! Redirecting..." });
      
      // Close modal and trigger success callback
      setTimeout(() => {
        if (onLoginSuccess) {
          onLoginSuccess();
        }
        onClose();
      }, 500);
    } catch (error) {
      setStatus({
        type: "error",
        message: error?.message || "We couldn't log you in. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleLogin = () => {
    const base = API_BASE_URL.replace(/\/api\/?$/, "");
    const googleUrl = `${base}/accounts/google/login/`;
    if (typeof window !== "undefined") {
      window.location.href = googleUrl;
    }
  };

  const handleSignUp = () => {
    onClose();
    router.push("/register");
  };

  if (!isOpen) return null;

  return (
    <div className="login-modal-overlay" ref={modalRef} onClick={onClose}>
      <div className="login-modal-content" ref={contentRef} onClick={(e) => e.stopPropagation()}>
        <button className="login-modal-close" onClick={onClose} aria-label="Close">
          <FiX size={24} />
        </button>

        <div className="login-modal-header">
          <h2>Login to Continue</h2>
          <p>Please login or sign up to place your order and unlock exclusive perks!</p>
        </div>

        <div className="login-modal-perks">
          <div className="login-modal-perk">
            <span className="perk-icon">🎁</span>
            <span>Earn loyalty rewards on every purchase</span>
          </div>
          <div className="login-modal-perk">
            <span className="perk-icon">📦</span>
            <span>Track your live orders in real-time</span>
          </div>
          <div className="login-modal-perk">
            <span className="perk-icon">🏆</span>
            <span>Join the leaderboard and compete with fans</span>
          </div>
          <div className="login-modal-perk">
            <span className="perk-icon">💬</span>
            <span>Join fandom discussions and connect with other fans</span>
          </div>
          <div className="login-modal-perk">
            <span className="perk-icon">⚡</span>
            <span>Faster checkout and order management</span>
          </div>
        </div>

        <form className="login-modal-form" onSubmit={handleSubmit}>
          <label htmlFor="modal-username">
            Username
            <input
              id="modal-username"
              name="username"
              type="text"
              autoComplete="username"
              placeholder="Enter your username"
              value={formData.username}
              onChange={handleInputChange}
              disabled={isSubmitting}
              required
            />
          </label>
          <label htmlFor="modal-password">
            Password
            <input
              id="modal-password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={formData.password}
              onChange={handleInputChange}
              disabled={isSubmitting}
              required
            />
          </label>
          <div className="login-modal-actions">
            <button className="login-modal-btn primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : (
                <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
                  Login <FiArrowRight />
                </span>
              )}
            </button>
            <button
              className="login-modal-btn secondary"
              type="button"
              onClick={handleGoogleLogin}
              disabled={isSubmitting}
            >
              <FcGoogle size={20} /> Login with Google
            </button>
          </div>
          {status.message && (
            <p className={`login-modal-status ${status.type === "error" ? "is-error" : "is-success"}`}>
              {status.message}
            </p>
          )}
          <div className="login-modal-footer">
            <span>Don't have an account?</span>
            <button type="button" onClick={handleSignUp} className="login-modal-link">
              Sign up here
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

