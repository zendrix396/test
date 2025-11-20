"use client";

import "./login.css";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Nav from "@/components/Nav/Nav";
import ConditionalFooter from "@/components/ConditionalFooter/ConditionalFooter";
import fetchApi from "@/lib/api";
import { useUser } from "@/lib/hooks";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { FiArrowRight } from "react-icons/fi";
import { FcGoogle } from "react-icons/fc";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

const LoginPage = () => {
  const router = useRouter();
  const { user, isLoading, mutate } = useUser();
  const heroRef = useRef(null);
  const cardRef = useRef(null);

  const searchParams = useSearchParams();
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [status, setStatus] = useState({ type: null, message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [needsUsername, setNeedsUsername] = useState(false);
  const [usernameInput, setUsernameInput] = useState("");

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/profile");
    }
  }, [isLoading, user, router]);

  // Handle Google OAuth callback - only run once
  useEffect(() => {
    const googleOAuth = searchParams?.get("google_oauth");
    const accessToken = searchParams?.get("access_token");
    const refreshToken = searchParams?.get("refresh_token");
    const needsUsernameParam = searchParams?.get("needs_username");

    if (googleOAuth === "success" && accessToken && refreshToken) {
      // Store tokens
      if (typeof window !== "undefined") {
        localStorage.setItem("accessToken", accessToken);
        localStorage.setItem("refreshToken", refreshToken);
      }

      // Clean up URL parameters immediately to prevent re-triggering
      router.replace("/login", { scroll: false });

      // Check if username is needed
      if (needsUsernameParam === "true") {
        setNeedsUsername(true);
        setStatus({
          type: "info",
          message: "Please choose a username to complete your account setup.",
        });
      } else {
        // Fetch user profile and redirect immediately
        fetchApi("/auth/me/")
          .then((profile) => {
            mutate(profile);
            // Redirect immediately without delay
            router.push("/profile");
          })
          .catch((error) => {
            setStatus({
              type: "error",
              message: "Failed to load profile. Please try again.",
            });
          });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount, not on every searchParams change

  // Check for error parameters from OAuth redirect
  useEffect(() => {
    const error = searchParams?.get("error");
    if (error === "google_not_configured") {
      setStatus({
        type: "error",
        message: "Google login is not configured. Please use email/password login or contact support.",
      });
    } else if (error === "oauth_error") {
      setStatus({
        type: "error",
        message: "An error occurred during Google login. Please try again or use email/password login.",
      });
    }
  }, [searchParams]);

  useGSAP(
    () => {
      if (!heroRef.current || !cardRef.current) return;
      gsap.fromTo(
        heroRef.current.querySelectorAll(".login-animate"),
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 1,
          stagger: 0.12,
          ease: "power3.out",
        }
      );
      gsap.fromTo(
        cardRef.current,
        { y: 60, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 1,
          delay: 0.4,
          ease: "power3.out",
        }
      );
    },
    { scope: heroRef }
  );

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
      setStatus({ type: "success", message: "Welcome back! Redirecting…" });
      setTimeout(() => router.push("/profile"), 400);
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

  const handleSetUsername = async (e) => {
    e.preventDefault();
    if (!usernameInput.trim() || usernameInput.trim().length < 3) {
      setStatus({
        type: "error",
        message: "Username must be at least 3 characters long.",
      });
      return;
    }

    try {
      setIsSubmitting(true);
      const response = await fetchApi("/auth/set-username/", {
        method: "POST",
        body: JSON.stringify({ username: usernameInput.trim() }),
      });

      if (response.message) {
        // Fetch updated profile
        const profile = await fetchApi("/auth/me/");
        mutate(profile);
        setNeedsUsername(false);
        setStatus({ type: "success", message: "Username set! Redirecting…" });
        setTimeout(() => router.push("/profile"), 400);
      }
    } catch (error) {
      setStatus({
        type: "error",
        message: error?.message || "Failed to set username. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Nav />
      <div className="page login-page">
        <div className="container login-wrapper" ref={heroRef}>
          <div className="login-panel">
            <span className="login-animate hero-pill">Return to your fandom arsenal</span>
            <h1 className="login-animate">Sign in to continue the hunt</h1>
            <p className="login-animate lead">
              Access exclusive drops, unlock loyalty streaks, track delivery rituals, and stay ahead on every release.
            </p>
            <div className="login-animate login-cta-group">
              <span className="hero-pill">Earn loyalty rewards</span>
              <span className="hero-pill">Track live orders</span>
              <span className="hero-pill">Join leaderboard</span>
            </div>
            <div className="login-animate login-showcase">
              <img src="/home/hero.jpg" alt="" />
              <div className="login-showcase-caption">
                <span>Community spotlight</span>
                <h3>Space4U Collectors Vanguard</h3>
                <p>Join thousands of otakus trading boss loot for bragging rights and leaderboard glory.</p>
              </div>
            </div>
          </div>

          <div className="login-card" ref={cardRef}>
            <header>
              <h2>{needsUsername ? "Choose a username" : "Log back in"}</h2>
              <p>
                {needsUsername
                  ? "Complete your account setup by choosing a unique username."
                  : "Keep your streak alive. Two steps & you are home."}
              </p>
            </header>
            {needsUsername ? (
              <form className="login-form" onSubmit={handleSetUsername}>
                <label htmlFor="username-input">
                  Username
                  <input
                    id="username-input"
                    name="username"
                    type="text"
                    autoComplete="username"
                    placeholder="Choose a username (min. 3 characters)"
                    value={usernameInput}
                    onChange={(e) => setUsernameInput(e.target.value)}
                    disabled={isSubmitting}
                    required
                    minLength={3}
                  />
                </label>
                <div className="actions">
                  <button className="primary" type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Setting username…" : (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "0.75rem" }}>
                        Continue <FiArrowRight />
                      </span>
                    )}
                  </button>
                </div>
                {status.message && (
                  <p className={`status-text ${status.type === "error" ? "is-error" : status.type === "success" ? "is-success" : ""}`}>
                    {status.message}
                  </p>
                )}
              </form>
            ) : (
              <form className="login-form" onSubmit={handleSubmit}>
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
                  {isSubmitting ? "Authenticating…" : (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "0.75rem" }}>
                      Continue <FiArrowRight />
                    </span>
                  )}
                </button>
                <button
                  className="secondary"
                  type="button"
                  onClick={handleGoogleLogin}
                  disabled={isSubmitting}
                >
                  <FcGoogle size={22} /> Login with Google
                </button>
              </div>
              <div className="login-meta">
                <span>Forgot password?</span>
                <a href="/connect">Ping support</a>
              </div>
              {status.message && (
                <p className={`status-text ${status.type === "error" ? "is-error" : "is-success"}`}>
                  {status.message}
                </p>
              )}
              </form>
            )}
          </div>
        </div>
      </div>
      <ConditionalFooter />
    </>
  );
};

export default LoginPage;
