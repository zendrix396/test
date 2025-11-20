"use client";
import "./Footer.css";

import { useRef } from "react";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import { useViewTransition } from "@/hooks/useViewTransition";
import { useUser } from "@/lib/hooks";
import Copy from "../Copy/Copy";
import fetchApi from "@/lib/api";
import { useState, useEffect } from "react";

import { RiLinkedinBoxLine } from "react-icons/ri";
import { RiInstagramLine } from "react-icons/ri";
import { RiDribbbleLine } from "react-icons/ri";
import { RiYoutubeLine } from "react-icons/ri";

gsap.registerPlugin(ScrollTrigger);

const Footer = () => {
  const { navigateWithTransition } = useViewTransition();
  const { user } = useUser();
  const socialIconsRef = useRef(null);
  const [leaderboard, setLeaderboard] = useState([]);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const data = await fetchApi("/auth/leaderboard/");
        if (data && Array.isArray(data)) {
          setLeaderboard(data.slice(0, 10)); // Top 10 for footer
        }
      } catch (error) {
        console.error("Failed to fetch leaderboard:", error);
      }
    };
    fetchLeaderboard();
  }, []);

  useGSAP(
    () => {
      if (!socialIconsRef.current) return;

      const icons = socialIconsRef.current.querySelectorAll(".icon");
      gsap.set(icons, { opacity: 0, x: -40 });

      ScrollTrigger.create({
        trigger: socialIconsRef.current,
        start: "top 90%",
        once: true,
        animation: gsap.to(icons, {
          opacity: 1,
          x: 0,
          duration: 0.8,
          stagger: -0.1,
          ease: "power3.out",
        }),
      });
    },
    { scope: socialIconsRef }
  );

  return (
    <div className="footer">
      <div className="footer-meta">
        <div className="container footer-meta-header">
          <div className="footer-meta-col">
            <div className="footer-meta-block">
              <div className="footer-meta-logo">
                <Copy delay={0.1}>
                  <h3 className="lg">SPACE4U</h3>
                </Copy>
              </div>
              <Copy delay={0.2}>
                <h2>Your Otaku Haven — Exclusive merchandise for every fan.</h2>
              </Copy>
            </div>
          </div>
          <div className="footer-meta-col">
            <div className="footer-nav-links">
              <Copy delay={0.1}>
                <a
                  href="/"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/");
                  }}
                >
                  <h3>Home</h3>
                </a>
                <a
                  href="/shop"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/shop");
                  }}
                >
                  <h3>Shop</h3>
                </a>
                <a
                  href="/wishlist"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/wishlist");
                  }}
                >
                  <h3>Wishlist</h3>
                </a>
                <a
                  href="/cart"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/cart");
                  }}
                >
                  <h3>Cart</h3>
                </a>
                {user ? (
                  <>
                    <a
                      href="/orders"
                      onClick={(e) => {
                        e.preventDefault();
                        navigateWithTransition("/orders");
                      }}
                    >
                      <h3>Orders</h3>
                </a>
                <a
                  href="/profile"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/profile");
                  }}
                >
                  <h3>Profile</h3>
                </a>
                  </>
                ) : (
                  <a
                    href="/login"
                    onClick={(e) => {
                      e.preventDefault();
                      navigateWithTransition("/login");
                    }}
                  >
                    <h3>Login</h3>
                  </a>
                )}
                <a
                  href="/connect"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/connect");
                  }}
                >
                  <h3>Support</h3>
                </a>
              </Copy>
            </div>
          </div>
        </div>
        <div className="container footer-socials">
          <div className="footer-meta-col">
            <div className="footer-socials-wrapper" ref={socialIconsRef}>
              <div className="icon">
                <RiLinkedinBoxLine />
              </div>
              <div className="icon">
                <RiInstagramLine />
              </div>
              <div className="icon">
                <RiDribbbleLine />
              </div>
              <div className="icon">
                <RiYoutubeLine />
              </div>
            </div>
          </div>
          <div className="footer-meta-col">
            <Copy delay={0.1}>
              <p>
                Discover exclusive anime merchandise and collectibles from beloved franchises, 
                all at competitive prices. Join our community of passionate fans today!
              </p>
            </Copy>
            <div style={{ marginTop: '2rem', marginLeft: '1rem' }}>
              <Copy delay={0.15}>
                <a
                  href="/leaderboard"
                  onClick={(e) => {
                    e.preventDefault();
                    navigateWithTransition("/leaderboard");
                  }}
                  style={{ 
                    color: 'var(--base-100)', 
                    fontSize: '1.1rem',
                    fontWeight: 600,
                    textDecoration: 'none',
                    transition: 'color 0.25s ease',
                  }}
                  onMouseEnter={(e) => e.target.style.color = 'rgba(242, 84, 91, 0.9)'}
                  onMouseLeave={(e) => e.target.style.color = 'var(--base-100)'}
                >
                  Show full leaderboard →
                </a>
              </Copy>
            </div>
          </div>
        </div>
      </div>
      <div className="footer-outro">
        <div className="container">
          <div className="footer-header">
            <img src="/logos/terrene-footer-logo.svg" alt="SPACE4U" />
          </div>
          <div className="footer-copyright">
            <p>
              © 2025. All rights reserved.
            </p>
            <p>This website is using cookies.</p>
            <p>SPACE4U | Your Otaku Haven</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Footer;
