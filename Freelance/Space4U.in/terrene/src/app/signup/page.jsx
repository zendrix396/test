"use client";

import "./signup.css";

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

const SignupPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading, mutate } = useUser();
  const heroRef = useRef(null);
  const cardRef = useRef(null);

  const referralCode = searchParams?.get("ref") || "";

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    password2: "",
  });
  const [status, setStatus] = useState({ type: null, message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidReferral, setIsValidReferral] = useState(false);
  const [isCheckingReferral, setIsCheckingReferral] = useState(false);

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/profile");
    }
  }, [isLoading, user, router]);

  // Validate referral code when it's present in URL
  useEffect(() => {
    const validateReferralCode = async () => {
      if (!referralCode) {
        setIsValidReferral(false);
        return;
      }

      setIsCheckingReferral(true);
      try {
        const validation = await fetchApi(`/auth/validate-referral-code/?code=${encodeURIComponent(referralCode)}`);
        setIsValidReferral(validation.valid === true && validation.enabled === true);
      } catch (error) {
        console.error("Failed to validate referral code", error);
        setIsValidReferral(false);
      } finally {
        setIsCheckingReferral(false);
      }
    };

    validateReferralCode();
  }, [referralCode]);

  useGSAP(
    () => {
      if (!heroRef.current || !cardRef.current) return;
      gsap.fromTo(
        heroRef.current.querySelectorAll(".signup-animate"),
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

    if (!formData.username.trim() || !formData.email.trim() || !formData.password.trim()) {
      setStatus({ type: "error", message: "All fields are required." });
      return;
    }

    if (formData.password !== formData.password2) {
      setStatus({ type: "error", message: "Passwords do not match." });
      return;
    }

    if (formData.password.length < 8) {
      setStatus({ type: "error", message: "Password must be at least 8 characters long." });
      return;
    }

    try {
      setIsSubmitting(true);
      const payload = {
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        password2: formData.password2,
      };

      // Include referral code only if it's valid
      if (referralCode && isValidReferral) {
        payload.referral_code = referralCode;
      }

      const response = await fetchApi("/auth/register/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      // After successful registration, log the user in
      const tokens = await fetchApi("/auth/jwt/create/", {
        method: "POST",
        body: JSON.stringify({
          username: formData.username.trim(),
          password: formData.password,
        }),
      });

      if (!tokens?.access || !tokens?.refresh) {
        throw new Error("Registration successful, but login failed. Please log in manually.");
      }

      if (typeof window !== "undefined") {
        localStorage.setItem("accessToken", tokens.access);
        localStorage.setItem("refreshToken", tokens.refresh);
      }

      const profile = await fetchApi("/auth/me/");
      mutate(profile);
      
      const successMessage = (referralCode && isValidReferral)
        ? "Account created! Referral bonus applied. Redirecting…"
        : "Account created! Redirecting…";
      
      setStatus({ type: "success", message: successMessage });
      setTimeout(() => router.push("/profile"), 400);
    } catch (error) {
      setStatus({
        type: "error",
        message: error?.message || "We couldn't create your account. Please try again.",
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

  return (
    <>
      <Nav />
      <div className="page signup-page">
        <div className="container signup-wrapper" ref={heroRef}>
          <div className="signup-panel">
            <span className="signup-animate hero-pill">Join the collector's vanguard</span>
            <h1 className="signup-animate">Start your fandom journey</h1>
            <p className="signup-animate lead">
              Create your account to unlock exclusive drops, earn loyalty rewards, track orders, and compete on the leaderboard.
            </p>
            {isCheckingReferral && referralCode && (
              <div className="signup-animate referral-badge" style={{ background: "rgba(255, 255, 255, 0.05)", borderColor: "rgba(255, 255, 255, 0.1)" }}>
                <span>Checking referral code...</span>
              </div>
            )}
            {!isCheckingReferral && isValidReferral && referralCode && (
              <div className="signup-animate referral-badge">
                <span>🎁 Referral code detected! You'll earn bonus points on signup.</span>
              </div>
            )}
            <div className="signup-animate signup-cta-group">
              <span className="hero-pill">Earn loyalty rewards</span>
              <span className="hero-pill">Track live orders</span>
              <span className="hero-pill">Join leaderboard</span>
            </div>
            <div className="signup-animate signup-showcase">
              <img src="/home/hero.jpg" alt="" />
              <div className="signup-showcase-caption">
                <span>Community spotlight</span>
                <h3>Space4U Collectors Vanguard</h3>
                <p>Join thousands of otakus trading boss loot for bragging rights and leaderboard glory.</p>
              </div>
            </div>
          </div>

          <div className="signup-card" ref={cardRef}>
            <header>
              <h2>Create account</h2>
              <p>Two minutes to unlock your collector's arsenal.</p>
            </header>
            <form className="signup-form" onSubmit={handleSubmit}>
              <label htmlFor="username">
                Username
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  placeholder="Choose a username"
                  value={formData.username}
                  onChange={handleInputChange}
                  disabled={isSubmitting}
                  required
                />
              </label>
              <label htmlFor="email">
                Email
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="your@email.com"
                  value={formData.email}
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
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                  value={formData.password}
                  onChange={handleInputChange}
                  disabled={isSubmitting}
                  required
                  minLength={8}
                />
              </label>
              <label htmlFor="password2">
                Confirm Password
                <input
                  id="password2"
                  name="password2"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  value={formData.password2}
                  onChange={handleInputChange}
                  disabled={isSubmitting}
                  required
                  minLength={8}
                />
              </label>
              <div className="actions">
                <button className="primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Creating account…" : (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "0.75rem" }}>
                      Sign up <FiArrowRight />
                    </span>
                  )}
                </button>
                <button
                  className="secondary"
                  type="button"
                  onClick={handleGoogleLogin}
                  disabled={isSubmitting}
                >
                  <FcGoogle size={22} /> Sign up with Google
                </button>
              </div>
              <div className="signup-meta">
                <span>Already have an account?</span>
                <a href="/login">Sign in</a>
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
      <ConditionalFooter />
    </>
  );
};

export default SignupPage;

