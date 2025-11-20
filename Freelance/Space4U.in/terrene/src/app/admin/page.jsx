"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import fetchApi from "@/lib/api";
import "./admin.css";

const AdminLoginPage = () => {
  const router = useRouter();
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [status, setStatus] = useState({ type: null, message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Check if already logged in as superuser
    const checkAuth = async () => {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
        if (token) {
          const check = await fetchApi("/admin/check-superuser/");
          if (check.is_superuser) {
            router.push("/admin/dashboard");
          }
        }
      } catch (e) {
        // Not authenticated or not superuser
      }
    };
    checkAuth();
  }, [router]);

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

      // Check if user is superuser
      const check = await fetchApi("/admin/check-superuser/");
      if (!check.is_superuser) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("accessToken");
          localStorage.removeItem("refreshToken");
        }
        throw new Error("Access denied. Superuser privileges required.");
      }

      setStatus({ type: "success", message: "Welcome! Redirecting…" });
      setTimeout(() => router.push("/admin/dashboard"), 400);
    } catch (error) {
      setStatus({
        type: "error",
        message: error?.message || "We couldn't log you in. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="admin-login-page">
      <div className="admin-login-wrapper">
        <div className="admin-login-panel">
          <h1 className="admin-login-animate">Admin Portal</h1>
          <p className="admin-login-animate lead">
            Access the administrative dashboard to manage orders, products, users, and more.
          </p>
        </div>

        <div className="admin-login-card">
          <header>
            <h2>Superuser Login</h2>
            <p>Enter your credentials to access the admin panel.</p>
          </header>
          <form className="admin-login-form" onSubmit={handleSubmit} method="POST">
            <label htmlFor="username">
              Username
              <input
                id="username"
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
            <label htmlFor="password">
              Password
              <input
                id="password"
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
            <div className="actions">
              <button className="primary" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Authenticating…" : "Sign In"}
              </button>
            </div>
            {status.message && (
              <p className={`status-text ${status.type === "error" ? "is-error" : "is-success"}`}>
                {status.message}
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

export default AdminLoginPage;

